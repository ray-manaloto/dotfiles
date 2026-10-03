# Copyright (c) 2026 Raymond Manaloto
"""#1606 path decisions and dispatcher routing on real linked git worktrees."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import hook_dispatch, worktree_guard


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True, timeout=10
    )


@pytest.fixture
def worktrees(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Main checkout, sibling lane, and a lane under the canonical directory."""
    main = tmp_path / "repo"
    main.mkdir()
    _git(main, "init", "-b", "main")
    _git(main, "config", "user.name", "Worktree Guard Test")
    _git(main, "config", "user.email", "worktree@example.invalid")
    (main / ".gitignore").write_text(".claude/worktrees/\n")
    _git(main, "add", ".gitignore")
    _git(main, "-c", "commit.gpgsign=false", "commit", "-m", "fixture")
    sibling = tmp_path / "repo.worktrees" / "lane"
    canonical = main / ".claude" / "worktrees" / "lane"
    _git(main, "worktree", "add", "-b", "sibling", str(sibling))
    _git(main, "worktree", "add", "-b", "canonical", str(canonical))
    return main, sibling, canonical


@pytest.mark.parametrize(
    ("tool", "expected"),
    [("EnterWorktree", True), ("Bash", False), ("ExitWorktree", False), ("", False)],
)
def test_handles_only_enterworktree(tool: str, *, expected: bool) -> None:
    assert worktree_guard.handles(tool) is expected


@pytest.mark.parametrize("session", [0, 1, 2])
@pytest.mark.parametrize("shape", ["sibling", "nested", "escape", "directory"])
def test_denies_paths_outside_main_worktree_directory(
    worktrees: tuple[Path, Path, Path], session: int, shape: str
) -> None:
    main, sibling, _ = worktrees
    allowed = main / ".claude" / "worktrees"
    targets = {
        "sibling": main / ".." / "repo.worktrees" / "handoff-2026-10-03c",
        "nested": sibling / ".claude" / "worktrees" / "x",
        "escape": allowed / ".." / ".." / "escape",
        "directory": allowed,
    }
    target = targets[shape]
    reason = worktree_guard.decide({"path": str(target)}, worktrees[session])
    assert reason is not None
    assert "#1606" in reason
    assert str(target.resolve()) in reason
    assert f"main checkout ({main.resolve()})" in reason
    assert "EnterWorktree name=<name>" in reason
    assert f"EnterWorktree path={allowed.resolve()}/<name>" in reason


@pytest.mark.parametrize("session", [0, 1, 2])
def test_allows_name_and_canonical_path_from_main_or_linked_worktree(
    worktrees: tuple[Path, Path, Path], session: int
) -> None:
    main, _, _ = worktrees
    project_dir = worktrees[session]
    assert worktree_guard.decide({"name": "foo"}, project_dir) is None
    assert (
        worktree_guard.decide(
            {"path": str(main / ".claude" / "worktrees" / "foo")}, project_dir
        )
        is None
    )


def test_resolves_relative_paths_against_project_dir(
    worktrees: tuple[Path, Path, Path],
) -> None:
    main, _, canonical = worktrees
    # Main's --git-common-dir is relative (.git), unlike the linked worktree's.
    assert worktree_guard.decide({"path": ".claude/worktrees/foo"}, main) is None
    assert worktree_guard.decide({"path": "../foo"}, canonical) is None
    assert worktree_guard.decide({"path": "../repo.worktrees/foo"}, main) is not None
    assert worktree_guard.decide({"path": "../../../escape"}, canonical) is not None


def test_resolves_symlinks_before_containment_check(
    worktrees: tuple[Path, Path, Path],
) -> None:
    main, sibling, canonical = worktrees
    escape = canonical.parent / "escape-link"
    escape.symlink_to(sibling, target_is_directory=True)
    assert worktree_guard.decide({"path": str(escape / "x")}, canonical) is not None
    safe = sibling / "safe-link"
    safe.symlink_to(canonical, target_is_directory=True)
    assert worktree_guard.decide({"path": str(safe)}, main) is None


def test_path_takes_precedence_if_both_keys_are_supplied(
    worktrees: tuple[Path, Path, Path],
) -> None:
    main, sibling, _ = worktrees
    assert (
        worktree_guard.decide({"name": "foo", "path": str(sibling)}, main) is not None
    )


def test_dispatch_routes_enterworktree(
    worktrees: tuple[Path, Path, Path],
) -> None:
    """An unwired dispatcher cannot pass by taking a non-repo fail-open path."""
    main, sibling, canonical = worktrees
    raw = json.dumps(
        {"tool_name": "EnterWorktree", "tool_input": {"path": str(sibling)}}
    )
    out = hook_dispatch.dispatch(canonical, raw)
    assert out, "EnterWorktree must reach the guard instead of the unknown-tool return"
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "#1606" in decision["permissionDecisionReason"]
    for tool_input in ({"name": "foo"}, {"path": str(canonical)}):
        raw = json.dumps({"tool_name": "EnterWorktree", "tool_input": tool_input})
        assert hook_dispatch.dispatch(main, raw) == ""


def test_nonrepo_fails_open(tmp_path: Path) -> None:
    assert worktree_guard.decide({"path": str(tmp_path / "x")}, tmp_path) is None


def test_missing_git_fails_open(
    worktrees: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    main, sibling, _ = worktrees
    monkeypatch.setenv("PATH", str(main / "no-binaries"))
    assert worktree_guard.decide({"path": str(sibling)}, main) is None


@pytest.mark.parametrize("path", [None, "", 1, "bad\0path"])
def test_malformed_path_fails_open(
    worktrees: tuple[Path, Path, Path], path: object
) -> None:
    assert worktree_guard.decide({"path": path}, worktrees[0]) is None
