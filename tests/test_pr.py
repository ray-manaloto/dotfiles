"""Tests for the ship/land PR workflow (dotfiles_setup.pr)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import pr

if TYPE_CHECKING:
    from dotfiles_setup.sync import SyncOptions

_WORKSPACE = Path("/workspaces-host/dotfiles")


def _cp(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


# ------------------------------------------------------- surface detection


@pytest.mark.parametrize(
    "path",
    [
        ".devcontainer/Dockerfile",
        ".devcontainer/scripts/on-create.sh",
        "docker-bake.hcl",
        "scripts/devcontainer-smoke.sh",
        "python/src/dotfiles_setup/sync.py",
        "python/src/dotfiles_setup/container.py",
        "python/verification/suites.toml",
    ],
)
def test_surface_paths_detected(path: str) -> None:
    assert pr.touches_surface([path])


@pytest.mark.parametrize(
    "path",
    ["AGENTS.md", "hk.pkl", "python/src/dotfiles_setup/audit.py", "tests/test_pr.py"],
)
def test_non_surface_paths_not_detected(path: str) -> None:
    assert not pr.touches_surface([path])


# ------------------------------------------------------------ gate matrix


def test_gate_matrix_always_has_core_gates() -> None:
    names = [g.name for g in pr.gate_matrix(["README.md"])]
    assert names[:3] == ["lint", "pytest", "verify-contracts"]
    assert "sync-full" not in names
    assert "pin-actions" not in names


def test_gate_matrix_gha_adds_pin_actions() -> None:
    names = [g.name for g in pr.gate_matrix([".github/workflows/ci.yml"])]
    assert "pin-actions" in names


def test_gate_matrix_docs_adds_lint_docs() -> None:
    names = [g.name for g in pr.gate_matrix([".claude/rules/do-not.md"])]
    assert "lint-docs" in names
    names = [g.name for g in pr.gate_matrix(["tests/AGENTS.md"])]
    assert "lint-docs" in names


def test_gate_matrix_non_base_surface_adds_full_sync_last() -> None:
    # A surface change that does NOT rebuild the base (validation tooling /
    # overlay) still runs the local container gate last.
    names = [g.name for g in pr.gate_matrix(["scripts/devcontainer-smoke.sh"])]
    assert names[-1] == "sync-full"
    names = [g.name for g in pr.gate_matrix(["python/src/dotfiles_setup/sync.py"])]
    assert names[-1] == "sync-full"


@pytest.mark.parametrize(
    "path",
    [
        ".devcontainer/Dockerfile",
        ".devcontainer/mise-system.toml",
        ".devcontainer/mise-system.lock",
        ".devcontainer/mise-runtime.toml",
        ".devcontainer/mise-runtime.lock",
        ".config/mise/conf.d/shared.toml",
        "hk-common.pkl",
        "hk-image.pkl",
        "docker-bake.hcl",
    ],
)
def test_base_input_changes_detected(path: str) -> None:
    assert pr.changes_base_image_inputs([path])


@pytest.mark.parametrize(
    "path",
    [
        "scripts/devcontainer-smoke.sh",
        "python/src/dotfiles_setup/sync.py",
        "python/src/dotfiles_setup/pr.py",
        "mise.toml",
        ".devcontainer/devcontainer.json",
        "README.md",
    ],
)
def test_non_base_paths_not_base_inputs(path: str) -> None:
    assert not pr.changes_base_image_inputs([path])


def test_gate_matrix_base_input_defers_full_sync() -> None:
    # A base-image build input can only be validated by the PR's own CI
    # (the local :dev base is built from the merge-base), so the local
    # container gate is DEFERRED — not appended — for these changes.
    for path in (".devcontainer/Dockerfile", ".config/mise/conf.d/shared.toml"):
        names = [g.name for g in pr.gate_matrix([path])]
        assert "sync-full" not in names
        assert names[:3] == ["lint", "pytest", "verify-contracts"]


def test_gate_matrix_base_input_wins_over_non_base_surface() -> None:
    # When a diff touches BOTH a base input and a non-base surface path,
    # the base-input deferral wins (the container still can't converge).
    names = [
        g.name
        for g in pr.gate_matrix(
            [".config/mise/conf.d/shared.toml", "python/src/dotfiles_setup/sync.py"]
        )
    ]
    assert "sync-full" not in names


def test_run_gates_stops_at_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[str] = []

    def fake_stream(cmd: list[str], **_k: object) -> int:
        ran.append(cmd[-1])
        return 1 if len(ran) == 2 else 0

    monkeypatch.setattr(pr, "_stream", fake_stream)
    gates = [
        pr.Gate("a", ("x", "a")),
        pr.Gate("b", ("x", "b")),
        pr.Gate("c", ("x", "c")),
    ]
    assert pr.run_gates(_WORKSPACE, gates) is False
    assert ran == ["a", "b"]


# ------------------------------------------------------ check verification


def test_pr_checks_green_all_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    checks = [
        {"name": "lint", "bucket": "pass"},
        {"name": "build", "bucket": "skipping"},
    ]
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(checks)))
    ok, detail = pr.pr_checks_green(1)
    assert ok
    assert "2 checks" in detail


@pytest.mark.parametrize("bucket", ["fail", "pending", "cancel"])
def test_pr_checks_not_green_on_bad_bucket(
    monkeypatch: pytest.MonkeyPatch, bucket: str
) -> None:
    checks = [{"name": "lint", "bucket": "pass"}, {"name": "x", "bucket": bucket}]
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(checks)))
    ok, detail = pr.pr_checks_green(1)
    assert not ok
    assert f"x={bucket}" in detail


# ------------------------------------------------------------------- ship


def test_ship_refuses_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pr, "_current_branch", lambda _w: "main")
    assert pr.ship_main(_WORKSPACE) == 1


def test_ship_refuses_dirty_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pr, "_current_branch", lambda _w: "feat/x")
    monkeypatch.setattr(pr, "_working_tree_clean", lambda _w: False)
    assert pr.ship_main(_WORKSPACE) == 1


def test_ship_gate_failure_stops_before_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pr, "_current_branch", lambda _w: "feat/x")
    monkeypatch.setattr(pr, "_working_tree_clean", lambda _w: True)
    monkeypatch.setattr(pr, "changed_paths_vs_main", lambda _w: ["a.py"])
    monkeypatch.setattr(pr, "run_gates", lambda *_a: False)

    def _boom(*_a: object, **_k: object) -> int:
        msg = "must not push after a failed gate"
        raise AssertionError(msg)

    monkeypatch.setattr(pr, "_stream", _boom)
    assert pr.ship_main(_WORKSPACE) == 1


# ------------------------------------------------------------------- land


def test_land_aborts_on_non_green_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    view = {"state": "OPEN", "headRefOid": "a" * 40, "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(pr, "pr_checks_green", lambda _n: (False, "lint=fail"))

    def _boom(*_a: object, **_k: object) -> int:
        msg = "must not merge with non-green checks"
        raise AssertionError(msg)

    monkeypatch.setattr(pr, "_stream", _boom)
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_aborts_on_closed_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    view = {"state": "MERGED", "headRefOid": "a" * 40, "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_merge_pins_verified_head(monkeypatch: pytest.MonkeyPatch) -> None:
    head = "b" * 40
    view = {"state": "OPEN", "headRefOid": head, "baseRefName": "main"}
    streamed: list[list[str]] = []
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(pr, "_pr_changed_paths", lambda _n: ["a.py"])
    monkeypatch.setattr(pr, "pr_checks_green", lambda _n: (True, "ok"))
    monkeypatch.setattr(pr, "_stream", lambda cmd, **_k: streamed.append(cmd) or 0)
    monkeypatch.setattr(pr, "_merge_commit_oid", lambda _n: "c" * 40)
    monkeypatch.setattr(pr, "_main_run_conclusion", lambda _o, **_k: True)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    assert pr.land_main(_WORKSPACE, 7) == 0
    merge_cmd = next(c for c in streamed if c[:3] == ["gh", "pr", "merge"])
    assert "--match-head-commit" in merge_cmd
    assert head in merge_cmd


def test_land_surface_pr_validates_full_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = {"state": "OPEN", "headRefOid": "d" * 40, "baseRefName": "main"}
    seen: dict[str, bool] = {}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(
        pr, "_pr_changed_paths", lambda _n: [".devcontainer/Dockerfile"]
    )
    monkeypatch.setattr(pr, "pr_checks_green", lambda _n: (True, "ok"))
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "_merge_commit_oid", lambda _n: "e" * 40)
    monkeypatch.setattr(pr, "_main_run_conclusion", lambda _o, **_k: True)

    def fake_sync(_w: Path, options: SyncOptions) -> int:
        seen["full"] = options.full
        return 0

    monkeypatch.setattr(pr, "sync_main", fake_sync)
    assert pr.land_main(_WORKSPACE, 7) == 0
    assert seen["full"] is True


def test_watch_awaits_check_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Registration + ci-gate waits both precede --watch; then buckets verify."""
    calls: list[str] = []
    responses = iter(
        [
            _cp("", returncode=1),  # registration window: gh errors
            _cp("[]"),  # registered but empty list — still pending
            _cp(json.dumps([{"name": "lint", "bucket": "pending"}])),  # >=1 check
            _cp(json.dumps([{"name": "lint"}])),  # ci-gate not present yet
            _cp(json.dumps([{"name": "lint"}, {"name": "ci-gate"}])),  # ci-gate here
            _cp(  # final bucket verify
                json.dumps(
                    [
                        {"name": "lint", "bucket": "pass"},
                        {"name": "ci-gate", "bucket": "pass"},
                    ]
                )
            ),
        ]
    )
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: next(responses))
    monkeypatch.setattr(pr, "_stream", lambda cmd, **_k: calls.append(cmd[0]) or 0)
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.watch_pr_checks(9) is True
    assert calls == ["gh"]  # --watch ran exactly once, after BOTH waits


def test_watch_fails_when_checks_never_register(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp("", returncode=1))
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)

    def _boom(*_a: object, **_k: object) -> int:
        msg = "must not watch before checks register"
        raise AssertionError(msg)

    monkeypatch.setattr(pr, "_stream", _boom)
    assert pr.watch_pr_checks(9) is False


def test_watch_fails_when_aggregate_never_registers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#181: >=1 check exists but ci-gate never appears — not green, no watch.

    The premature-green gap: without the ci-gate wait, --watch could exit on
    an early all-green wave (here `lint`) before the build jobs registered.
    """
    monkeypatch.setattr(
        pr,
        "_run",
        lambda *_a, **_k: _cp(json.dumps([{"name": "lint", "bucket": "pass"}])),
    )
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)

    def _boom(*_a: object, **_k: object) -> int:
        msg = "must not watch before ci-gate registers"
        raise AssertionError(msg)

    monkeypatch.setattr(pr, "_stream", _boom)
    assert pr.watch_pr_checks(9) is False


def test_land_refuses_non_main_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review finding [11]: land only lands main-based PRs."""
    view = {"state": "OPEN", "headRefOid": "a" * 40, "baseRefName": "develop"}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_resume_requires_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review finding [6]: --resume only replays post-merge steps."""
    monkeypatch.setattr(
        pr, "_run", lambda *_a, **_k: _cp(json.dumps({"state": "OPEN"}))
    )
    assert pr.land_main(_WORKSPACE, 7, resume=True) == 1


def test_land_resume_replays_post_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pr, "_run", lambda *_a, **_k: _cp(json.dumps({"state": "MERGED"}))
    )
    monkeypatch.setattr(pr, "_pr_changed_paths", lambda _n: ["a.py"])
    monkeypatch.setattr(pr, "_merge_commit_oid", lambda _n: "c" * 40)
    monkeypatch.setattr(pr, "_main_run_conclusion", lambda _o, **_k: True)
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    assert pr.land_main(_WORKSPACE, 7, resume=True) == 0


@pytest.mark.parametrize(
    "path",
    ["hk-common.pkl", "hk-image.pkl", ".config/mise/conf.d/shared.toml", "mise.toml"],
)
def test_surface_covers_image_copy_inputs(path: str) -> None:
    """Review finding [5]: image COPY inputs + task definitions are surface."""
    assert pr.touches_surface([path])


# ------------------------------------------- main-CI expectation (post #178)


def _ci_yml_push_paths() -> list[str]:
    """The on.push.paths entries as written in ci.yml (comments skipped)."""
    text = (
        Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    ).read_text()
    block = text.split("push:", 1)[1].split("paths:", 1)[1]
    entries: list[str] = []
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if not stripped.startswith("- "):
            break
        entries.append(stripped[2:].strip('"'))
    return entries


def _fnmatch_patterns_for(yaml_path: str) -> tuple[str, ...]:
    """The fnmatch mirror of one ci.yml glob (``x/**`` needs two patterns)."""
    if yaml_path.endswith("/**"):
        base = yaml_path.removesuffix("/**")
        return (f"{base}/*", f"{base}/**/*")
    return (yaml_path,)


def test_ci_push_paths_mirror_ci_yml() -> None:
    """CI_PUSH_PATHS must stay in lockstep with ci.yml on.push.paths.

    Land's "no main run expected" outcome (#178) is only correct while the
    mirrored constant matches the workflow — this test fails on drift in
    either direction.
    """
    entries = _ci_yml_push_paths()
    assert entries, "failed to parse ci.yml on.push.paths"
    expected: set[str] = set()
    for entry in entries:
        expected.update(_fnmatch_patterns_for(entry))
    assert set(pr.CI_PUSH_PATHS) == expected


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["mise.toml", "mise.lock", ".agnix.toml"], False),  # the #178 shape
        ([".config/mise/conf.d/shared.toml"], True),
        (["python/src/dotfiles_setup/pr.py"], True),
        (["home/dot_zshrc"], True),
        ([".devcontainer/mise-system.lock"], True),
        ([".claude/rules/do-not.md", "AGENTS.md"], False),
    ],
)
def test_expects_main_run(paths: list[str], *, expected: bool) -> None:
    assert pr.expects_main_run(paths) is expected


def _land_run_dispatch(view: dict[str, str], *, run_id: str = "") -> object:
    """Fake ``pr._run`` dispatching by gh subcommand for land_main flows."""

    def fake(cmd: list[str], **_k: object) -> subprocess.CompletedProcess[str]:
        if "run" in cmd and "list" in cmd:
            return _cp(f"{run_id}\n" if run_id else "")
        if "conclusion" in cmd:
            return _cp("success\n")
        if "mergeCommit" in cmd:
            return _cp(json.dumps({"mergeCommit": {"oid": "c" * 40}}))
        if "checks" in cmd:
            return _cp(json.dumps([{"name": "lint", "bucket": "pass"}]))
        return _cp(json.dumps(view))

    return fake


def test_land_passes_when_no_main_run_expected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#178: a merge whose paths match no ci.yml push path needs no run."""
    view = {"state": "OPEN", "headRefOid": "b" * 40, "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", _land_run_dispatch(view))
    monkeypatch.setattr(
        pr, "_pr_changed_paths", lambda _n: ["mise.toml", ".agnix.toml"]
    )
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.land_main(_WORKSPACE, 7) == 0


def test_land_fails_when_expected_main_run_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ci.yml-push-path merge with no main run is a real failure."""
    view = {"state": "OPEN", "headRefOid": "b" * 40, "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", _land_run_dispatch(view))
    monkeypatch.setattr(
        pr, "_pr_changed_paths", lambda _n: [".config/mise/conf.d/shared.toml"]
    )
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_watches_main_run_when_one_unexpectedly_appears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Grace poll: a run appearing despite no expectation is still verified."""
    view = {"state": "OPEN", "headRefOid": "b" * 40, "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", _land_run_dispatch(view, run_id="999"))
    monkeypatch.setattr(pr, "_pr_changed_paths", lambda _n: ["docs/x.md"])
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.land_main(_WORKSPACE, 7) == 0
