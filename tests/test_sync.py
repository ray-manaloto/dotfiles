# Copyright (c) 2026 Raymond Manaloto
"""Tests for the devcontainer sync workflow (dotfiles_setup.sync)."""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import sync
from dotfiles_setup.container import Check
from dotfiles_setup.devcontainer_names import resolve_names
from dotfiles_setup.platform_target import published_targets

_WORKSPACE = Path("/workspaces-host/dotfiles")
_NAMES = resolve_names(
    workspace=_WORKSPACE, user="u", platform="linux/amd64/v2", env={}
)
_NAMES_ARM64 = resolve_names(
    workspace=_WORKSPACE, user="u", platform="linux/arm64/v8", env={}
)


@pytest.fixture(autouse=True)
def _isolated_sync_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No test may touch the REAL sync state (defense-in-depth).

    Probe-observed 2026-07-07: before the write_sync_record isolation fix,
    a host pytest run wrote a FIXTURE digest into the user's real
    ~/.local/state/dotfiles record. Redirecting _state_file makes that
    class of pollution impossible for every current and future test here.
    """
    monkeypatch.setattr(
        sync, "_state_file", lambda ref: tmp_path / f"sync-{hash(ref)}.json"
    )


_REPO = "ghcr.io/ray-manaloto/dotfiles-devcontainer"
_REF = f"{_REPO}:dev"
_DIGEST_NEW = "sha256:" + "ce" * 32
_DIGEST_OLD = "sha256:" + "e5" * 32


def _cp(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


def _status(
    *,
    registry: str | None = _DIGEST_NEW,
    local: str | None = _DIGEST_NEW,
    state: sync.ContainerState = "running",
    record: sync.SyncRecord | None = None,
    arch: str = "amd64",
) -> sync.SyncStatus:
    return sync.SyncStatus(
        image_ref=_REF,
        registry_digest=registry,
        local_digests=(local,) if local else (),
        local_image_id="img-1",
        container_state=state,
        synced_state=record,
        arch=arch,
    )


# ---------------------------------------------------------------- staleness


def test_matching_digests_not_stale() -> None:
    assert not _status().stale


def test_diverged_local_tag_is_stale() -> None:
    # The PR #169 promote case: registry :dev moved (retag), the local
    # :dev tag silently kept the pre-merge digest.
    assert _status(local=_DIGEST_OLD).stale


def test_absent_local_tag_is_stale() -> None:
    assert _status(local=None).stale


def test_unreachable_registry_is_not_stale() -> None:
    # A network blip must never tear down a working container.
    assert not _status(registry=None, local=_DIGEST_OLD).stale


# Review finding [0]: buildkit refresh mints a new local manifest digest,
# so convergence is witnessed by the sync record, not RepoDigests.
def test_sync_record_witnesses_refresh_convergence() -> None:
    record = sync.SyncRecord(registry_digest=_DIGEST_NEW, local_image_id="img-1")
    assert not _status(local=_DIGEST_OLD, record=record).stale


def test_sync_record_stale_when_registry_moved_again() -> None:
    record = sync.SyncRecord(registry_digest=_DIGEST_OLD, local_image_id="img-1")
    assert _status(local=_DIGEST_OLD, record=record).stale


def test_sync_record_stale_when_local_image_replaced() -> None:
    record = sync.SyncRecord(registry_digest=_DIGEST_NEW, local_image_id="img-0")
    assert _status(local=_DIGEST_OLD, record=record).stale  # img-1 != img-0


def test_multi_digest_local_tag_matches_any() -> None:
    status = sync.SyncStatus(
        image_ref=_REF,
        registry_digest=_DIGEST_NEW,
        local_digests=(_DIGEST_OLD, _DIGEST_NEW),
        local_image_id="img-1",
        container_state="running",
    )
    assert not status.stale


# Review finding [1]: a running container from an older converge triggers
# rebuild; unknown ids stay non-destructive.
def test_outdated_container_triggers_rebuild() -> None:
    record = sync.SyncRecord(
        registry_digest=_DIGEST_NEW,
        local_image_id="img-1",
        containers={"amd64": "c-old"},
    )
    status = dataclasses.replace(
        _status(record=record, arch="amd64"), container_image_id="c-new"
    )
    assert not status.container_current
    assert sync.decide_action(status, force=False) == "rebuild"


def test_unknown_container_id_is_non_destructive() -> None:
    record = sync.SyncRecord(registry_digest=_DIGEST_NEW, local_image_id="img-1")
    assert _status(record=record).container_current


# ------------------------------------------------- per-architecture record


def test_per_arch_record_isolates_the_other_architecture() -> None:
    """#800: an arm64 container must not be judged against amd64's entry."""
    record = sync.SyncRecord(
        registry_digest=_DIGEST_NEW,
        local_image_id="img-1",
        containers={"amd64": "c-a"},
    )
    arm64 = dataclasses.replace(
        _status(record=record, arch="arm64"), container_image_id="c-b"
    )
    assert not arm64.container_current
    assert sync.decide_action(arm64, force=False) == "rebuild"

    amd64 = dataclasses.replace(
        _status(record=record, arch="amd64"), container_image_id="c-a"
    )
    assert amd64.container_current
    assert sync.decide_action(amd64, force=False) == "verify-only"


def test_empty_containers_map_with_running_container_is_not_current() -> None:
    record = sync.SyncRecord(registry_digest=_DIGEST_NEW, local_image_id="img-1")
    status = dataclasses.replace(
        _status(record=record, arch="amd64"), container_image_id="c-a"
    )
    assert not status.container_current


def test_legacy_flat_id_falls_back_when_this_arch_has_no_containers_entry() -> None:
    """#800 F10: a pre-#800 legacy record skips a spurious rebuild.

    The architecture the legacy flat id names is spared; a genuinely
    different id still rebuilds.
    """
    record = sync.SyncRecord(
        registry_digest=_DIGEST_NEW,
        local_image_id="img-1",
        legacy_container_image_id="c-a",
    )
    matching = dataclasses.replace(_status(record=record), container_image_id="c-a")
    assert matching.container_current

    mismatched = dataclasses.replace(_status(record=record), container_image_id="c-b")
    assert not mismatched.container_current


# ------------------------------------------------------------ action matrix


def test_stale_rebuilds_regardless_of_state() -> None:
    for state in ("running", "stopped", "absent"):
        status = _status(local=_DIGEST_OLD, state=state)
        assert sync.decide_action(status, force=False) == "rebuild"


def test_force_rebuilds_even_when_current() -> None:
    assert sync.decide_action(_status(), force=True) == "rebuild"


def test_current_and_running_is_fast_path() -> None:
    assert sync.decide_action(_status(), force=False) == "verify-only"


def test_current_but_not_running_brings_up() -> None:
    assert sync.decide_action(_status(state="stopped"), force=False) == "up"
    assert sync.decide_action(_status(state="absent"), force=False) == "up"


# #800 round 2 F1: a stopped container's overlay id must be checked, not
# auto-blessed by "not running" — the currency check now runs BEFORE the
# state check in decide_action.


def test_stopped_container_with_stale_overlay_is_rebuilt_not_reused() -> None:
    """A stopped container on a superseded base must not be `up`'d (reused)."""
    record = sync.SyncRecord(
        registry_digest=_DIGEST_NEW,
        local_image_id="img-1",
        containers={"amd64": "c-old"},
    )
    status = dataclasses.replace(
        _status(state="stopped", record=record), container_image_id="c-new"
    )
    assert not status.container_current
    assert sync.decide_action(status, force=False) == "rebuild"


def test_stopped_container_matching_the_record_is_reused_via_up() -> None:
    """A stopped container whose overlay id still matches is reused, not rebuilt."""
    record = sync.SyncRecord(
        registry_digest=_DIGEST_NEW,
        local_image_id="img-1",
        containers={"amd64": "c-same"},
    )
    status = dataclasses.replace(
        _status(state="stopped", record=record), container_image_id="c-same"
    )
    assert status.container_current
    assert sync.decide_action(status, force=False) == "up"


def test_absent_container_stays_up_not_rebuild() -> None:
    """A probe that finds nothing (container_image_id None) is non-destructive."""
    record = sync.SyncRecord(
        registry_digest=_DIGEST_NEW,
        local_image_id="img-1",
        containers={"amd64": "c-old"},
    )
    status = _status(state="absent", record=record)
    assert status.container_current
    assert sync.decide_action(status, force=False) == "up"


# #800 round 2 F4: an unreachable registry must never trigger a destructive
# action on currency grounds — same principle as `stale`'s network-blip guard.


def test_registry_unreachable_stays_verify_only_despite_record_mismatch() -> None:
    record = sync.SyncRecord(registry_digest=_DIGEST_OLD, local_image_id="img-0")
    status = dataclasses.replace(
        _status(registry=None, state="running", record=record),
        container_image_id="c-x",
    )
    assert status.container_current
    assert sync.decide_action(status, force=False) == "verify-only"


# ------------------------------------------------------------- observation


def test_local_digests_matches_repo_not_stage_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # RepoDigests can carry bake-stage aliases (dotfiles-devcontainer-base@…);
    # only entries whose repo matches the ref count — ALL of them ([0] sub-point).
    payload = [
        f"dotfiles-devcontainer-base@{_DIGEST_OLD}",
        f"{_REPO}@{_DIGEST_NEW}",
        f"{_REPO}@{_DIGEST_OLD}",
    ]
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp(json.dumps(payload) + "\n"))
    assert sync.local_digests(_REF) == (_DIGEST_NEW, _DIGEST_OLD)


def test_local_digests_absent_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp("", returncode=1))
    assert sync.local_digests(_REF) == ()


def test_registry_digest_parses_json_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp(f'"{_DIGEST_NEW}"\n'))
    assert sync.registry_digest(_REF) == _DIGEST_NEW


def test_registry_digest_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp("", returncode=1))
    assert sync.registry_digest(_REF) is None


def test_container_state_running(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp("running\n"))
    assert sync.container_state(_NAMES) == "running"


def test_container_state_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp("exited\n"))
    assert sync.container_state(_NAMES) == "stopped"


def test_container_state_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp(""))
    assert sync.container_state(_NAMES) == "absent"


def test_container_state_filters_on_both_id_labels_not_local_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#800: filter on the two id labels, not the old folder label.

    Post-#677 containers carry no ``devcontainer.local_folder`` label
    (``--id-label`` replaces the CLI's inferred set) — the lookup must key
    on the two #677 id labels instead, combined with AND. Control:
    reverting the filter to the old bare-folder label fails this assertion.
    """
    captured: list[list[str]] = []

    def _record(cmd: list[str], **_k: object) -> subprocess.CompletedProcess[str]:
        captured.append(cmd)
        return _cp("")

    monkeypatch.setattr(sync, "_run", _record)
    sync.container_state(_NAMES)
    sync.container_image_id(_NAMES)
    assert captured
    for cmd in captured:
        assert f"label={_NAMES.workspace_label}" in cmd
        assert f"label={_NAMES.arch_label}" in cmd
        assert not any("devcontainer.local_folder" in arg for arg in cmd)


# ---------------------------------------------------------- CI awareness


def test_tag_branch_dev_is_main() -> None:
    assert sync.tag_branch("dev") == "main"


def test_tag_branch_pr_resolves_head_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sync,
        "_run",
        lambda *_a, **_k: _cp(json.dumps({"headRefName": "feat/x"})),
    )
    assert sync.tag_branch("pr-169") == "feat/x"


def test_tag_branch_immutable_tags_untracked() -> None:
    assert sync.tag_branch("6a5c92c") is None
    assert sync.tag_branch("dev-3919d689ab92461b") is None


def test_inflight_filters_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    runs = [
        {"databaseId": 1, "status": "completed", "displayTitle": "a", "url": "u1"},
        {"databaseId": 2, "status": "in_progress", "displayTitle": "b", "url": "u2"},
        {"databaseId": 3, "status": "queued", "displayTitle": "c", "url": "u3"},
    ]
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp(json.dumps(runs)))
    assert [r["databaseId"] for r in sync.inflight_ci_runs("main")] == [2, 3]


# ------------------------------------------------------- sync record write


def test_write_sync_record_merges_other_architectures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#800: writing this arch's converge must not drop another entry.

    An entry for another architecture, still witness-current for the same
    ``local_image_id``, must survive the merge.
    """
    current_names = {"names": _NAMES}
    monkeypatch.setattr(sync, "resolve_names", lambda **_kw: current_names["names"])
    monkeypatch.setattr(sync, "local_image_id", lambda _ref: "img-1")

    monkeypatch.setattr(sync, "container_image_id", lambda _n: "c-amd64")
    sync.write_sync_record(_WORKSPACE, _REF, _DIGEST_NEW)
    record = sync.read_sync_record(_REF)
    assert record is not None
    assert record.containers == {"amd64": "c-amd64"}

    current_names["names"] = _NAMES_ARM64
    monkeypatch.setattr(sync, "container_image_id", lambda _n: "c-arm64")
    sync.write_sync_record(_WORKSPACE, _REF, _DIGEST_NEW)
    record = sync.read_sync_record(_REF)
    assert record is not None
    assert record.containers == {"amd64": "c-amd64", "arm64": "c-arm64"}


def test_write_sync_record_starts_fresh_when_local_image_id_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real tag refresh drops OTHER architectures' stale entries.

    A new ``local_image_id`` means the entries describe a now-superseded
    local image and must rebuild once rather than being trusted.
    """
    current_names = {"names": _NAMES}
    monkeypatch.setattr(sync, "resolve_names", lambda **_kw: current_names["names"])
    monkeypatch.setattr(sync, "local_image_id", lambda _ref: "img-1")
    monkeypatch.setattr(sync, "container_image_id", lambda _n: "c-amd64")
    sync.write_sync_record(_WORKSPACE, _REF, _DIGEST_NEW)

    current_names["names"] = _NAMES_ARM64
    monkeypatch.setattr(sync, "local_image_id", lambda _ref: "img-2")
    monkeypatch.setattr(sync, "container_image_id", lambda _n: "c-arm64")
    sync.write_sync_record(_WORKSPACE, _REF, _DIGEST_NEW)

    record = sync.read_sync_record(_REF)
    assert record is not None
    assert record.local_image_id == "img-2"
    assert record.containers == {"arm64": "c-arm64"}


def test_write_sync_record_warns_when_container_probe_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """#800 F7: a dropped architecture entry must not fail silently."""
    monkeypatch.setattr(sync, "resolve_names", lambda **_kw: _NAMES)
    monkeypatch.setattr(sync, "local_image_id", lambda _ref: "img-1")
    monkeypatch.setattr(sync, "container_image_id", lambda _n: None)
    with caplog.at_level("WARNING", logger="dotfiles_setup.sync"):
        sync.write_sync_record(_WORKSPACE, _REF, _DIGEST_NEW)
    assert any("written without a container id" in r.message for r in caplog.records)
    record = sync.read_sync_record(_REF)
    assert record is not None
    assert record.containers == {}


# ------------------------------------------------------- state file robustness


def test_read_sync_record_non_dict_payload_reads_as_none(tmp_path: Path) -> None:
    """#800 F8: a state file holding a bare JSON list must not raise."""
    # Same path formula as the `_isolated_sync_state` autouse fixture above —
    # `tmp_path` is the identical cached fixture instance for this test node.
    (tmp_path / f"sync-{hash(_REF)}.json").write_text(json.dumps([]))
    assert sync.read_sync_record(_REF) is None


def test_read_sync_record_parses_legacy_flat_key(tmp_path: Path) -> None:
    """#800 F10: a genuine pre-#800 record is read, not silently dropped.

    Flat ``container_image_id`` key, no ``containers`` — the value lands in
    ``legacy_container_image_id``.
    """
    (tmp_path / f"sync-{hash(_REF)}.json").write_text(
        json.dumps(
            {
                "registry_digest": _DIGEST_NEW,
                "local_image_id": "img-1",
                "container_image_id": "c-a",
            }
        )
    )
    record = sync.read_sync_record(_REF)
    assert record is not None
    assert record.containers == {}
    assert record.legacy_container_image_id == "c-a"


def test_read_sync_record_non_string_legacy_field_degrades_to_none(
    tmp_path: Path,
) -> None:
    """#800 F8/M7: a corrupt legacy id must not force a spurious rebuild.

    It degrades to ``None`` like the ``containers`` guard, rather than
    comparing unequal against a real container id.
    """
    (tmp_path / f"sync-{hash(_REF)}.json").write_text(
        json.dumps(
            {
                "registry_digest": _DIGEST_NEW,
                "local_image_id": "img-1",
                "container_image_id": 42,
            }
        )
    )
    record = sync.read_sync_record(_REF)
    assert record is not None
    assert record.legacy_container_image_id is None


def test_refresh_local_tag_requests_union_when_both_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#800 F2 (a): local already carries both — refresh both, published order.

    The expected values are derived, not hard-coded — they drift with
    ``platform_target._MICROARCH_LEVEL``.
    """
    amd64, arm64 = (t.platform for t in published_targets())
    captured: dict[str, list[str]] = {}

    def _record(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(sync.subprocess, "run", _record)
    monkeypatch.setattr(sync, "local_platforms", lambda _ref: frozenset({amd64, arm64}))
    monkeypatch.setenv("DOTFILES_PLATFORM", amd64)
    assert sync.refresh_local_tag(_REF)
    platforms = captured["cmd"][captured["cmd"].index("--platform") + 1]
    assert platforms == f"{amd64},{arm64}"
    assert "," in platforms


def test_refresh_local_tag_absent_tag_requests_only_the_pinned_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#800 F2 (b): an absent local tag must not fetch an arch nobody asked for."""
    amd64, _arm64 = (t.platform for t in published_targets())
    captured: dict[str, list[str]] = {}

    def _record(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(sync.subprocess, "run", _record)
    monkeypatch.setattr(sync, "local_platforms", lambda _ref: frozenset())
    monkeypatch.setenv("DOTFILES_PLATFORM", amd64)
    assert sync.refresh_local_tag(_REF)
    platforms = captured["cmd"][captured["cmd"].index("--platform") + 1]
    assert platforms == amd64


def test_refresh_local_tag_union_adds_pinned_platform_to_what_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#800 F2 (c): local carries only arm64, this host pins amd64 — union."""
    amd64, arm64 = (t.platform for t in published_targets())
    captured: dict[str, list[str]] = {}

    def _record(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(sync.subprocess, "run", _record)
    monkeypatch.setattr(sync, "local_platforms", lambda _ref: frozenset({arm64}))
    monkeypatch.setenv("DOTFILES_PLATFORM", amd64)
    assert sync.refresh_local_tag(_REF)
    platforms = captured["cmd"][captured["cmd"].index("--platform") + 1]
    assert platforms == f"{amd64},{arm64}"
    assert "," in platforms


# ------------------------------------------------------------ end-to-end


def test_sync_fast_path_skips_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Current digest + running container → verify only, no mise lifecycle."""
    streamed: list[list[str]] = []
    monkeypatch.setattr(sync, "observe", lambda *_a: _status())
    monkeypatch.setattr(sync, "_report_inflight", lambda *_a, **_k: None)
    monkeypatch.setattr(sync, "_stream", lambda cmd, **_k: streamed.append(cmd) or 0)
    monkeypatch.setattr(sync, "verify_latest", lambda *_a, **_k: [])
    assert sync.sync_main(_WORKSPACE) == 0
    assert streamed == []


def test_sync_stale_refreshes_tag_then_rebuilds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setattr(sync, "observe", lambda *_a: _status(local=_DIGEST_OLD))
    monkeypatch.setattr(sync, "_report_inflight", lambda *_a, **_k: None)
    monkeypatch.setattr(
        sync, "refresh_local_tag", lambda _ref: events.append("refresh") or True
    )
    # write_sync_record must never touch real docker in a unit test
    # (probe-observed: in-container pytest has no docker CLI).
    monkeypatch.setattr(
        sync, "write_sync_record", lambda *_a, **_k: events.append("record")
    )
    monkeypatch.setattr(
        sync, "_stream", lambda cmd, **_k: events.append(" ".join(cmd[:3])) or 0
    )
    monkeypatch.setattr(sync, "verify_latest", lambda *_a, **_k: [])
    assert sync.sync_main(_WORKSPACE) == 0
    assert events == ["refresh", "mise run dev-rebuild", "record"]


def test_sync_check_mode_reports_without_converging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sync, "observe", lambda *_a: _status(local=_DIGEST_OLD))
    monkeypatch.setattr(sync, "_report_inflight", lambda *_a, **_k: None)

    def _boom(*_a: object, **_k: object) -> int:
        msg = "check mode must not run lifecycle commands"
        raise AssertionError(msg)

    monkeypatch.setattr(sync, "_stream", _boom)
    monkeypatch.setattr(sync, "refresh_local_tag", _boom)
    assert sync.sync_main(_WORKSPACE, sync.SyncOptions(check_only=True)) == 1


def test_sync_check_mode_current_rc0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "observe", lambda *_a: _status())
    monkeypatch.setattr(sync, "_report_inflight", lambda *_a, **_k: None)
    assert sync.sync_main(_WORKSPACE, sync.SyncOptions(check_only=True)) == 0


def test_sync_verify_failure_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "observe", lambda *_a: _status())
    monkeypatch.setattr(sync, "_report_inflight", lambda *_a, **_k: None)
    monkeypatch.setattr(
        sync,
        "verify_latest",
        lambda *_a, **_k: [Check("smoke-tiers-1-3", ok=False, detail="boom")],
    )
    assert sync.sync_main(_WORKSPACE) == 1


def test_sync_full_runs_verify_local(monkeypatch: pytest.MonkeyPatch) -> None:
    streamed: list[list[str]] = []
    monkeypatch.setattr(sync, "observe", lambda *_a: _status())
    monkeypatch.setattr(sync, "_report_inflight", lambda *_a, **_k: None)
    monkeypatch.setattr(sync, "_stream", lambda cmd, **_k: streamed.append(cmd) or 0)
    assert sync.sync_main(_WORKSPACE, sync.SyncOptions(full=True)) == 0
    assert ["mise", "run", "verify-local"] in streamed


def test_sync_failed_awaited_run_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    """--wait on a run that concludes non-success must abort the sync."""
    monkeypatch.setattr(sync, "tag_branch", lambda _t: "main")
    monkeypatch.setattr(
        sync,
        "inflight_ci_runs",
        lambda _b: [
            {
                "databaseId": 42,
                "status": "in_progress",
                "displayTitle": "x",
                "url": "u",
            }
        ],
    )
    monkeypatch.setattr(sync, "wait_for_run", lambda _id: False)
    with pytest.raises(SystemExit) as excinfo:
        sync.sync_main(_WORKSPACE, sync.SyncOptions(wait=True))
    assert excinfo.value.code == 1
