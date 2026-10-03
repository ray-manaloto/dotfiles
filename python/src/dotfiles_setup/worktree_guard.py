# Copyright (c) 2026 Raymond Manaloto
"""Restrict EnterWorktree paths to existing managed worktrees (#1606).

Native ``name=`` creation uses the main checkout's ``.claude/worktrees/``.
The PreToolUse hook applies this location policy in every permission mode.
Only stdlib imports: git runs only when deciding an EnterWorktree path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def handles(tool_name: str) -> bool:
    """Whether this guard decides on the named tool."""
    return tool_name == "EnterWorktree"


def _deny_reason(target: Path, main: Path) -> str:
    checkout = str(main)
    allowed = f"{checkout}/.claude/worktrees"
    return (
        f"#1606: EnterWorktree path={target} must be an existing worktree under "
        f"{allowed}/, strictly inside that directory and registered with this repo. "
        "This location policy applies in every permission mode. "
        f"For NEW worktrees, from the main checkout ({checkout}), use "
        "`EnterWorktree name=<name>`. From inside a worktree session, use "
        f"`EnterWorktree path={allowed}/<name>` for an existing registered worktree, "
        "or ExitWorktree (keep) before creating a NEW worktree with name=."
    )


def _unverified_reason(target: Path, detail: str) -> str:
    """Fail closed when git cannot answer, naming why instead of a location."""
    cause = " ".join(detail.split())[:300] or "git printed no diagnostic"
    return (
        f"#1606: EnterWorktree path={target} was denied because the guard could "
        f"not verify it (fails closed): {cause}. Check the repository with "
        "`git worktree list`; for a NEW worktree, use `EnterWorktree name=<name>` "
        "from the main checkout."
    )


class _VerificationError(Exception):
    """Git could not answer; the guard fails closed and reports this cause."""


def _git(cmd: list[str], anchor: Path) -> str:
    """Run one git query from ``anchor``; any failure is a verification error."""
    try:
        proc = subprocess.run(
            cmd, cwd=anchor, capture_output=True, text=True, check=False, timeout=5
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise _VerificationError(str(exc)) from exc
    if proc.returncode != 0:
        raise _VerificationError(proc.stderr or f"{cmd} exited {proc.returncode}")
    return proc.stdout


def _main_checkout(anchor: Path) -> Path:
    """The main checkout owning ``anchor``'s repository (common dir's parent)."""
    common = _git(["git", "rev-parse", "--git-common-dir"], anchor).strip()
    if not common:
        msg = "git rev-parse --git-common-dir printed nothing"
        raise _VerificationError(msg)
    common_dir = Path(common)
    if not common_dir.is_absolute():
        common_dir = anchor / common_dir
    return common_dir.resolve().parent


def decide(
    tool_input: dict[str, object], project_dir: Path, cwd: Path | None = None
) -> str | None:
    """Require an existing managed worktree; deny paths we cannot verify."""
    path = tool_input.get("path")
    if not isinstance(path, str) or not path:
        return None
    target = Path(path)
    try:
        anchor = (cwd if cwd is not None else project_dir).resolve()
        main = _main_checkout(anchor)
        if not target.is_absolute():
            target = anchor / target
        target = target.resolve()
        allowed = main / ".claude" / "worktrees"
        if target != allowed and target.is_relative_to(allowed) and target.is_dir():
            listing = _git(["git", "worktree", "list", "--porcelain", "-z"], anchor)
            if any(
                Path(record.removeprefix("worktree ")).resolve() == target
                for record in listing.split("\0")
                if record.startswith("worktree ")
            ):
                return None
    except (OSError, ValueError, _VerificationError) as exc:
        return _unverified_reason(target, str(exc))
    return _deny_reason(target, main)
