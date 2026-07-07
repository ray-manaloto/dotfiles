"""Tests for the devcontainer sync workflow (dotfiles_setup.sync)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import sync
from dotfiles_setup.container import Check

_WORKSPACE = Path("/workspaces-host/dotfiles")
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
) -> sync.SyncStatus:
    return sync.SyncStatus(
        image_ref=_REF,
        registry_digest=registry,
        local_digest=local,
        container_state=state,
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


# ------------------------------------------------------------- observation


def test_local_digest_matches_repo_not_stage_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # RepoDigests can carry bake-stage aliases (dotfiles-devcontainer-base@…);
    # only the entry whose repo matches the ref counts.
    payload = [
        f"dotfiles-devcontainer-base@{_DIGEST_OLD}",
        f"{_REPO}@{_DIGEST_NEW}",
    ]
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp(json.dumps(payload) + "\n"))
    assert sync.local_digest(_REF) == _DIGEST_NEW


def test_local_digest_absent_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp("", returncode=1))
    assert sync.local_digest(_REF) is None


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
    assert sync.container_state(_WORKSPACE) == "running"


def test_container_state_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp("exited\n"))
    assert sync.container_state(_WORKSPACE) == "stopped"


def test_container_state_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "_run", lambda *_a, **_k: _cp(""))
    assert sync.container_state(_WORKSPACE) == "absent"


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
    monkeypatch.setattr(
        sync, "_stream", lambda cmd, **_k: events.append(" ".join(cmd[:3])) or 0
    )
    monkeypatch.setattr(sync, "verify_latest", lambda *_a, **_k: [])
    assert sync.sync_main(_WORKSPACE) == 0
    assert events == ["refresh", "mise run dev-rebuild"]


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
