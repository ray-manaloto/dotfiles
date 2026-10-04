# Copyright (c) 2026 Raymond Manaloto
"""Coordinator confinement on real repositories and the public hook routes.

Feature branches distinguish this guard from branch_guard. Error controls
replace only the subprocess/filesystem boundary; successful probes use Git.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotfiles_setup import (
    coordinator_handoff,
    hook_guard,
    session_common,
)
from dotfiles_setup import (
    coordinator_write_guard as guard,
)

_SESSION = "12345678-coordinator"
_NAME = "dotfiles-20261003T120000.coordinator"
_LANE = "dotfiles-20261003T120000.L1-docs-rules"
_PROJECT = Path(__file__).resolve().parent.parent
_TWO_CALLS = 2
_GIT_ERROR = 128


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True, timeout=10
    )


def _record(jobs: Path, data: object) -> Path:
    path = jobs / _SESSION[:8] / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout on a feature branch with tracked and ignored paths."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "feat/lane")
    (root / ".gitignore").write_text("/task_plan.md\n.agent/\n", encoding="utf-8")
    (root / "tracked.md").write_text("tracked\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "initial")
    return root


@pytest.fixture
def jobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use a disposable HOME so public hooks discover only our fake record."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    jobs = home / ".claude" / "jobs"
    _record(jobs, {"sessionId": _SESSION, "name": _NAME})
    return jobs


@pytest.mark.parametrize("tool", ["Edit", "Write", "NotebookEdit", "Read", "Bash"])
def test_handles_only_file_modifications(tool: str) -> None:
    """Read and Bash control accidental overbroad matching."""
    assert guard.handles(tool) is (tool in {"Edit", "Write", "NotebookEdit"})


@pytest.mark.parametrize(
    "name", [_NAME, _LANE, None, "other.coordinator", "dotfiles-x.coordinator.extra"]
)
def test_shared_identity_preserves_handoff_api(name: str | None) -> None:
    """Both public consumers recognize exactly the established name grammar."""
    expected = name == _NAME
    assert session_common.is_coordinator(name) is expected
    assert coordinator_handoff.is_coordinator(name) is expected
    assert coordinator_handoff.COORDINATOR_NAME_RE is session_common.COORDINATOR_NAME_RE


@pytest.mark.parametrize("key", ["file_path", "notebook_path"])
@pytest.mark.parametrize(
    "path", ["tracked.md", "new/deep/report.md", "task_plan.md", ".agent/plans/x.md"]
)
def test_main_paths(repo: Path, jobs: Path, key: str, path: str) -> None:
    """Ignored and new non-ignored files control tracked-path confinement."""
    reason = guard.decide({key: str(repo / path)}, _SESSION, jobs_dir=jobs)
    if path in {"task_plan.md", ".agent/plans/x.md"}:
        assert reason is None
    else:
        assert reason is not None
        assert "EnterWorktree name=<branch-slug>, then edit the worktree copy" in reason
        assert path in reason


def test_linked_worktree_and_outside(repo: Path, jobs: Path, tmp_path: Path) -> None:
    """Even a worktree nested in the main directory is a separate checkout."""
    linked = repo / ".claude" / "worktrees" / "lane"
    _git(repo, "worktree", "add", "-b", "feat/linked", str(linked))
    for target in [
        linked / "tracked.md",
        linked / "new/deep/report.md",
        tmp_path / "outside.md",
    ]:
        assert guard.decide({"file_path": str(target)}, _SESSION, jobs_dir=jobs) is None
    assert (
        guard.decide({"file_path": str(repo / "tracked.md")}, _SESSION, jobs_dir=jobs)
        is not None
    )


@pytest.mark.parametrize(
    "record",
    [
        None,
        [],
        {"sessionId": "12345678-wrong", "name": _NAME},
        {"sessionId": _SESSION, "name": 3},
        {"sessionId": _SESSION, "name": _LANE},
    ],
)
def test_missing_malformed_and_lane_records(
    repo: Path, jobs: Path, record: object
) -> None:
    """Untrusted job identities never acquire coordinator privileges."""
    path = _record(jobs, record)
    if record is None:
        path.unlink()
    assert (
        guard.decide({"file_path": str(repo / "tracked.md")}, _SESSION, jobs_dir=jobs)
        is None
    )
    _record(jobs, {"sessionId": _SESSION, "name": _NAME})
    assert (
        guard.decide({"file_path": str(repo / "tracked.md")}, _SESSION, jobs_dir=jobs)
        is not None
    )


@pytest.mark.parametrize("content", ["{", "\udcff"])
def test_unreadable_json_allows(repo: Path, jobs: Path, content: str) -> None:
    """Corrupt JSON and invalid UTF-8 fail open; a valid record denies."""
    path = jobs / _SESSION[:8] / "state.json"
    path.write_bytes(content.encode("utf-8", errors="surrogateescape"))
    assert (
        guard.decide({"file_path": str(repo / "tracked.md")}, _SESSION, jobs_dir=jobs)
        is None
    )
    _record(jobs, {"sessionId": _SESSION, "name": _NAME})
    assert (
        guard.decide({"file_path": str(repo / "tracked.md")}, _SESSION, jobs_dir=jobs)
        is not None
    )


def test_job_record_read_error_allows(repo: Path, jobs: Path) -> None:
    """A directory in place of state.json causes a real OS read failure."""
    path = jobs / _SESSION[:8] / "state.json"
    path.unlink()
    path.mkdir()
    target: dict[str, object] = {"file_path": str(repo / "tracked.md")}
    assert guard.decide(target, _SESSION, jobs_dir=jobs) is None
    path.rmdir()
    _record(jobs, {"sessionId": _SESSION, "name": _NAME})
    assert guard.decide(target, _SESSION, jobs_dir=jobs) is not None


def test_symlink_resolves_actual_target(repo: Path, jobs: Path) -> None:
    """An ignored alias cannot make a tracked file writable."""
    ignored = repo / "task_plan.md"
    ignored.symlink_to(repo / "tracked.md")
    assert (
        guard.decide({"file_path": str(ignored)}, _SESSION, jobs_dir=jobs) is not None
    )
    ignored.unlink()
    assert guard.decide({"file_path": str(ignored)}, _SESSION, jobs_dir=jobs) is None


@pytest.mark.parametrize("session_id", [None, "", "../escape", "87654321-unknown"])
def test_absent_session_allows(repo: Path, jobs: Path, session_id: str | None) -> None:
    """Interactive or unresolvable sessions allow the identical target."""
    target: dict[str, object] = {"file_path": str(repo / "tracked.md")}
    assert guard.decide(target, session_id, jobs_dir=jobs) is None
    assert guard.decide(target, _SESSION, jobs_dir=jobs) is not None


@pytest.mark.parametrize(
    "payload", [{}, {"file_path": ""}, {"file_path": 3}, {"file_path": "\x00"}]
)
def test_unresolvable_target_allows(
    repo: Path, jobs: Path, payload: dict[str, object]
) -> None:
    """Malformed targets control the normal resolvable denial."""
    assert guard.decide(payload, _SESSION, jobs_dir=jobs) is None
    assert (
        guard.decide({"file_path": str(repo / "tracked.md")}, _SESSION, jobs_dir=jobs)
        is not None
    )


@pytest.mark.parametrize("command", ["rev-parse", "check-ignore"])
@pytest.mark.parametrize("failure", ["rc128", "oserror", "timeout", "bad-output"])
def test_git_failures_open(
    repo: Path, jobs: Path, monkeypatch: pytest.MonkeyPatch, command: str, failure: str
) -> None:
    """Git-runner boundary errors differ from check-ignore's explicit rc 1."""
    real_run = subprocess.run

    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["git", command]:
            if failure == "oserror":
                msg = "git unavailable"
                raise OSError(msg)
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args, 5)
            if failure == "bad-output" and command == "rev-parse":
                return subprocess.CompletedProcess(args, 0, stdout="missing\nfacts\n")
            return subprocess.CompletedProcess(
                args, _GIT_ERROR, stdout="", stderr="fatal"
            )
        return real_run(
            args,
            cwd=Path(str(kwargs["cwd"])),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    target: dict[str, object] = {"file_path": str(repo / "tracked.md")}
    assert guard.decide(target, _SESSION, jobs_dir=jobs) is not None
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "run", run)
        assert guard.decide(target, _SESSION, jobs_dir=jobs) is None
    assert guard.decide(target, _SESSION, jobs_dir=jobs) is not None


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("main", _TWO_CALLS),
        ("ignored", _TWO_CALLS),
        ("linked", 1),
        ("outside", 1),
        ("lane", 0),
        ("missing", 0),
    ],
)
def test_costs_one_record_and_at_most_two_git_calls(
    *,
    repo: Path,
    jobs: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
    expected: int,
) -> None:
    """Real GIT_TRACE counts calls; file-read boundary counts the identity read."""
    target = repo / "tracked.md"
    if location == "linked":
        linked = repo.parent / "linked"
        _git(repo, "worktree", "add", "-b", "feat/cost", str(linked))
        target = linked / "tracked.md"
    elif location == "outside":
        target = repo.parent / "outside.md"
    elif location == "ignored":
        target = repo / "task_plan.md"
    elif location == "lane":
        _record(jobs, {"sessionId": _SESSION, "name": _LANE})
    elif location == "missing":
        (jobs / _SESSION[:8] / "state.json").unlink()
    trace = repo.parent / "git-trace.log"
    monkeypatch.setenv("GIT_TRACE", str(trace))
    reads: list[Path] = []
    read_text = Path.read_text

    def read(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        reads.append(path)
        return read_text(path, encoding=encoding, errors=errors, newline=newline)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", read)
        reason = guard.decide({"file_path": str(target)}, _SESSION, jobs_dir=jobs)
    assert reads == [jobs / _SESSION[:8] / "state.json"]
    log = trace.read_text() if trace.exists() else ""
    assert log.count("built-in: git ") == expected
    assert (reason is not None) is (location == "main")


@pytest.mark.parametrize("tool", ["Edit", "Write", "NotebookEdit"])
def test_decide_payload_wiring(repo: Path, jobs: Path, tool: str) -> None:
    """Removing only the coordinator wiring makes this feature-branch test fail."""
    _ = jobs
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    target: dict[str, object] = {key: str(repo / "tracked.md")}
    reason = hook_guard.decide_payload(tool, target, session_id=_SESSION)
    assert reason is not None
    assert "EnterWorktree name=<branch-slug>" in reason
    assert hook_guard.decide_payload(tool, target) is None


def test_coordinator_reason_wins_on_the_default_branch(repo: Path, jobs: Path) -> None:
    """On `main`, a coordinator must get EnterWorktree, never `git checkout -b`.

    branch_guard's fix would switch the SHARED main checkout's branch (cold
    review F1, 2026-10-03); a non-coordinator still gets branch_guard's reason.
    """
    _ = jobs
    _git(repo, "branch", "-m", "main")
    target: dict[str, object] = {"file_path": str(repo / "tracked.md")}
    coordinator = hook_guard.decide_payload("Edit", target, session_id=_SESSION)
    assert coordinator is not None
    assert "EnterWorktree name=<branch-slug>" in coordinator
    assert "checkout -b" not in coordinator
    other = hook_guard.decide_payload("Edit", target)
    assert other is not None
    assert "EnterWorktree name=<branch-slug>" not in other


@pytest.mark.parametrize("route", ["pretooluse", "dispatch", "wrapper"])
@pytest.mark.parametrize("session_id", [_SESSION, None, 42])
def test_real_hook_routes(
    repo: Path, jobs: Path, route: str, session_id: object
) -> None:
    """Both stdin entrypoints and the registered shell wrapper carry identity."""
    _ = jobs
    commands = {
        "pretooluse": [
            sys.executable,
            "-c",
            (
                "from dotfiles_setup.hook_guard import pretooluse_main; "
                "raise SystemExit(pretooluse_main())"
            ),
        ],
        "dispatch": [
            sys.executable,
            "-m",
            "dotfiles_setup.hook_dispatch",
            str(_PROJECT),
        ],
        "wrapper": ["bash", str(_PROJECT / "scripts" / "pretooluse-guard.sh")],
    }
    payload = json.dumps(
        {
            "tool_name": "Write",
            "session_id": session_id,
            "tool_input": {"file_path": str(repo / "tracked.md"), "content": "x"},
        }
    )
    proc = subprocess.run(
        commands[route],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(_PROJECT)},
    )
    assert proc.returncode == 0, proc.stderr
    assert not proc.stderr
    if session_id == _SESSION:
        decision = json.loads(proc.stdout)["hookSpecificOutput"]
        assert decision["permissionDecision"] == "deny"
        assert (
            "EnterWorktree name=<branch-slug>" in decision["permissionDecisionReason"]
        )
    else:
        assert proc.stdout == ""
