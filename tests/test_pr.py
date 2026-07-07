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


def test_gate_matrix_surface_adds_full_sync_last() -> None:
    names = [g.name for g in pr.gate_matrix([".devcontainer/Dockerfile"])]
    assert names[-1] == "sync-full"


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
    view = {"state": "OPEN", "headRefOid": "a" * 40, "files": [{"path": "a.py"}]}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(pr, "pr_checks_green", lambda _n: (False, "lint=fail"))

    def _boom(*_a: object, **_k: object) -> int:
        msg = "must not merge with non-green checks"
        raise AssertionError(msg)

    monkeypatch.setattr(pr, "_stream", _boom)
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_aborts_on_closed_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    view = {"state": "MERGED", "headRefOid": "a" * 40, "files": []}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_merge_pins_verified_head(monkeypatch: pytest.MonkeyPatch) -> None:
    head = "b" * 40
    view = {"state": "OPEN", "headRefOid": head, "files": [{"path": "a.py"}]}
    streamed: list[list[str]] = []
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(pr, "pr_checks_green", lambda _n: (True, "ok"))
    monkeypatch.setattr(pr, "_stream", lambda cmd, **_k: streamed.append(cmd) or 0)
    monkeypatch.setattr(pr, "_merge_commit_oid", lambda _n: "c" * 40)
    monkeypatch.setattr(pr, "_main_run_conclusion", lambda _o: True)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    assert pr.land_main(_WORKSPACE, 7) == 0
    merge_cmd = next(c for c in streamed if c[:3] == ["gh", "pr", "merge"])
    assert "--match-head-commit" in merge_cmd
    assert head in merge_cmd


def test_land_surface_pr_validates_full_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = {
        "state": "OPEN",
        "headRefOid": "d" * 40,
        "files": [{"path": ".devcontainer/Dockerfile"}],
    }
    seen: dict[str, bool] = {}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(pr, "pr_checks_green", lambda _n: (True, "ok"))
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "_merge_commit_oid", lambda _n: "e" * 40)
    monkeypatch.setattr(pr, "_main_run_conclusion", lambda _o: True)

    def fake_sync(_w: Path, options: SyncOptions) -> int:
        seen["full"] = options.full
        return 0

    monkeypatch.setattr(pr, "sync_main", fake_sync)
    assert pr.land_main(_WORKSPACE, 7) == 0
    assert seen["full"] is True


def test_watch_awaits_check_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    """'no checks reported' right after PR-create is pending, not failure."""
    calls: list[str] = []
    responses = iter(
        [
            _cp("", returncode=1),  # registration window: gh errors
            _cp("[]"),  # registered but empty list — still pending
            _cp(json.dumps([{"name": "lint", "bucket": "pending"}])),  # registered
            _cp(json.dumps([{"name": "lint", "bucket": "pass"}])),  # final verify
        ]
    )
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: next(responses))
    monkeypatch.setattr(pr, "_stream", lambda cmd, **_k: calls.append(cmd[0]) or 0)
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.watch_pr_checks(9) is True
    assert calls == ["gh"]  # the --watch ran exactly once, after registration


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
