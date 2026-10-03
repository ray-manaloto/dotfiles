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
    _, _, canonical = worktrees
    project_dir = worktrees[session]
    assert worktree_guard.decide({"name": "foo"}, project_dir) is None
    assert worktree_guard.decide({"path": str(canonical)}, project_dir) is None


def test_resolves_relative_paths_against_project_dir(
    worktrees: tuple[Path, Path, Path],
) -> None:
    main, _, canonical = worktrees
    # Main's --git-common-dir is relative (.git), unlike the linked worktree's.
    assert worktree_guard.decide({"path": ".claude/worktrees/lane"}, main) is None
    assert worktree_guard.decide({"path": "../lane"}, canonical) is None
    assert worktree_guard.decide({"path": "../repo.worktrees/foo"}, main) is not None
    assert worktree_guard.decide({"path": "../../../escape"}, canonical) is not None


@pytest.mark.parametrize("session", [0, 1, 2])
def test_denies_nonexistent_path_inside_managed_directory(
    worktrees: tuple[Path, Path, Path], session: int
) -> None:
    main, _, _ = worktrees
    target = main / ".claude" / "worktrees" / "does-not-exist"
    assert not target.exists()
    reason = worktree_guard.decide({"path": str(target)}, worktrees[session])
    assert reason is not None
    assert f"an existing worktree under {target.parent}/" in reason
    assert "NEW worktrees" in reason
    assert "EnterWorktree name=<name>" in reason


def test_denies_existing_unregistered_directory(
    worktrees: tuple[Path, Path, Path],
) -> None:
    main, _, canonical = worktrees
    target = canonical.parent / "unregistered"
    target.mkdir()
    assert worktree_guard.decide({"path": str(target)}, main) is not None


def test_denies_missing_registered_worktree(
    worktrees: tuple[Path, Path, Path],
) -> None:
    main, _, canonical = worktrees
    canonical.rename(canonical.with_name("moved"))
    # Git still lists the original path until worktree repair/prune.
    assert worktree_guard.decide({"path": str(canonical)}, main) is not None


def test_repo_anchor_follows_cwd_in_another_repo(
    worktrees: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    main, _, canonical = worktrees
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-b", "main")
    reason = worktree_guard.decide({"path": str(canonical)}, main, cwd=other)
    assert reason is not None
    assert f"an existing worktree under {other}/.claude/worktrees/" in reason


@pytest.mark.parametrize("mode", ["default", "auto", "bypassPermissions"])
def test_location_policy_is_uniform_across_permission_modes(
    worktrees: tuple[Path, Path, Path], mode: str
) -> None:
    main, sibling, _ = worktrees
    raw = json.dumps(
        {
            "tool_name": "EnterWorktree",
            "tool_input": {"path": str(sibling)},
            "permission_mode": mode,
        }
    )
    reason = json.loads(hook_dispatch.dispatch(main, raw))["hookSpecificOutput"][
        "permissionDecisionReason"
    ]
    assert "This location policy applies in every permission mode." in reason
    assert "raise a permission prompt" not in reason


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


def test_nonrepo_denies_unverifiable_path(tmp_path: Path) -> None:
    assert worktree_guard.decide({"path": str(tmp_path / "x")}, tmp_path) is not None


def test_missing_git_denies_unverifiable_path(
    worktrees: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    main, sibling, _ = worktrees
    monkeypatch.setenv("PATH", str(main / "no-binaries"))
    assert worktree_guard.decide({"path": str(sibling)}, main) is not None


@pytest.mark.parametrize("path", [None, "", 1])
def test_malformed_path_fails_open(
    worktrees: tuple[Path, Path, Path], path: object
) -> None:
    assert worktree_guard.decide({"path": path}, worktrees[0]) is None


def test_invalid_string_path_is_denied(worktrees: tuple[Path, Path, Path]) -> None:
    assert worktree_guard.decide({"path": "bad\0path"}, worktrees[0]) is not None
