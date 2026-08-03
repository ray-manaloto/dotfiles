"""Tests for the default-branch write guard.

Every test builds a **real git repo** rather than mocking git. The fixture is
the thing most likely to lie here (``probes-need-a-control-arm.md`` rule 8:
"could this setup have produced the other result?"), and a mocked
``rev-parse`` would prove only that the mock returns what it was told to.

Each behaviour is asserted in BOTH directions — a guard verified only on the
deny path is a check that can only pass.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import branch_guard, hook_guard

if TYPE_CHECKING:
    from pathlib import Path


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git repo on `main`, with a .gitignore and one commit."""
    root = tmp_path / "repo"
    root.mkdir()
    _run(["git", "init", "-b", "main"], root)
    _run(["git", "config", "user.email", "t@example.com"], root)
    _run(["git", "config", "user.name", "T"], root)
    (root / ".gitignore").write_text(".agent/\nmise.local.toml\n")
    (root / "tracked.md").write_text("hello\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-m", "init"], root)
    (root / ".agent").mkdir()
    return root


def test_denies_tracked_file_on_default_branch(repo: Path) -> None:
    """The headline case: real work, on main, must be refused."""
    reason = branch_guard.decide({"file_path": str(repo / "tracked.md")})
    assert reason is not None
    assert "default branch" in reason
    assert "git checkout -b" in reason
    assert "tracked.md" in reason


def test_denies_a_new_untracked_file_on_default_branch(repo: Path) -> None:
    """The exact 2026-08-03-f failure: agent reports written to main.

    The file does not exist yet and is not tracked — but it is not ignored
    either, so it is work that belongs on a branch.
    """
    reason = branch_guard.decide({"file_path": str(repo / "docs" / "report.md")})
    assert reason is not None


def test_allows_same_file_on_a_feature_branch(repo: Path) -> None:
    """CONTROL ARM for the deny above — only the branch differs."""
    _run(["git", "checkout", "-b", "feat/x"], repo)
    assert branch_guard.decide({"file_path": str(repo / "tracked.md")}) is None


def test_allows_gitignored_paths_on_default_branch(repo: Path) -> None:
    """`.agent/` and friends can never reach a PR, so they are never blocked."""
    assert (
        branch_guard.decide({"file_path": str(repo / ".agent" / "notepad.md")}) is None
    )
    assert branch_guard.decide({"file_path": str(repo / "mise.local.toml")}) is None


def test_allows_paths_outside_any_repo(tmp_path: Path) -> None:
    """The auto-memory dir and the session scratchpad must stay writable."""
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    assert branch_guard.decide({"file_path": str(outside / "MEMORY.md")}) is None


def test_allows_when_detached_head(repo: Path) -> None:
    """A detached HEAD is not a branch anyone ships from."""
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    _run(["git", "checkout", sha], repo)
    assert branch_guard.decide({"file_path": str(repo / "tracked.md")}) is None


def test_allows_master_as_well_as_main(tmp_path: Path) -> None:
    """The fallback pair covers a `master`-default clone."""
    root = tmp_path / "old"
    root.mkdir()
    _run(["git", "init", "-b", "master"], root)
    _run(["git", "config", "user.email", "t@example.com"], root)
    _run(["git", "config", "user.name", "T"], root)
    (root / "f.md").write_text("x\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-m", "i"], root)
    assert branch_guard.decide({"file_path": str(root / "f.md")}) is not None


def test_allows_missing_or_malformed_input() -> None:
    """Fails OPEN — a payload without a path must never block."""
    assert branch_guard.decide({}) is None
    assert branch_guard.decide({"file_path": ""}) is None
    assert branch_guard.decide({"file_path": 42}) is None


def test_notebook_path_is_honoured(repo: Path) -> None:
    """NotebookEdit carries `notebook_path`, not `file_path`."""
    assert branch_guard.decide({"notebook_path": str(repo / "nb.ipynb")}) is not None


def test_handles_covers_exactly_the_file_modifying_tools() -> None:
    """Both arms: the covered set, and a tool that must NOT route here."""
    for name in ("Edit", "Write", "NotebookEdit"):
        assert branch_guard.handles(name)
    for name in ("Bash", "AskUserQuestion", "Read", "Grep"):
        assert not branch_guard.handles(name)


def test_dispatch_routes_edit_to_the_branch_guard(repo: Path) -> None:
    """The WIRING, not just the module — `decide_payload` must reach it.

    Without this, the guard could be perfect and never called; that is the
    #343 fail-open shape.
    """
    reason = hook_guard.decide_payload("Write", {"file_path": str(repo / "tracked.md")})
    assert reason is not None
    assert "default branch" in reason


def test_dispatch_still_treats_bash_as_a_command() -> None:
    """CONTROL ARM: adding the branch guard must not swallow Bash rules."""
    assert hook_guard.decide_payload("Bash", {"command": "git status"}) is None
    assert hook_guard.decide_payload("Bash", {"command": "git commit --no-verify -m x"})
