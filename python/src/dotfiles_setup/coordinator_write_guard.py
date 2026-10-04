# Copyright (c) 2026 Raymond Manaloto
"""Confine coordinator writes in the main checkout to git-ignored paths.

Linked worktrees and non-coordinator sessions remain unrestricted by this
guard. Every unresolvable step fails OPEN: a coordinator whose job record
cannot be read is not confined. Git errors likewise allow the write.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dotfiles_setup import session_common
from dotfiles_setup.branch_guard import _git_capture, _probe_dir, _target

if TYPE_CHECKING:
    from pathlib import Path

_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})
_TOPOLOGY = [
    "rev-parse",
    "--path-format=absolute",
    "--show-toplevel",
    "--git-dir",
    "--git-common-dir",
]
_TOPOLOGY_FACT_COUNT = 3
_NOT_IGNORED_RC = 1


def handles(tool_name: str) -> bool:
    """Whether this tool modifies a file or notebook."""
    return tool_name in _TOOLS


def _main_root(target: Path | None) -> Path | None:
    """Resolve topology in one invocation, allowing on missing facts."""
    if target is None or (probe := _probe_dir(target)) is None:
        return None
    result = _git_capture(_TOPOLOGY, probe)
    if result is None or result[0] != 0:
        return None
    facts = result[1].splitlines()
    if len(facts) != _TOPOLOGY_FACT_COUNT or not all(facts):
        return None
    root, git_dir, common_dir = ((probe / fact).resolve() for fact in facts)
    return root if git_dir == common_dir and target.is_relative_to(root) else None


def decide(
    tool_input: dict[str, object],
    session_id: str | None,
    *,
    jobs_dir: Path | None = None,
) -> str | None:
    """Deny a known coordinator's non-ignored main-checkout write, or allow.

    Read one job record and short-circuit before Git for other sessions.
    A coordinator costs one combined topology probe, then at most one
    check-ignore call. Only check-ignore's explicit rc 1 permits a denial.
    """
    if not isinstance(session_id, str) or not session_id:
        return None
    name = session_common.session_name(
        session_id, jobs_dir or session_common.default_jobs_dir()
    )
    if not session_common.is_coordinator(name):
        return None
    try:
        target = _target(tool_input)
        root = _main_root(target)
        if root is None or target is None:
            return None
        ignored = _git_capture(["check-ignore", "-q", "--", str(target)], root)
        if ignored is None or ignored[0] != _NOT_IGNORED_RC:
            return None
    except OSError, RuntimeError, ValueError:
        return None
    return (
        f"Coordinator writes in the main checkout are limited to git-ignored "
        f"paths; {target.relative_to(root)} is not ignored. "
        "EnterWorktree name=<branch-slug>, then edit the worktree copy."
    )
