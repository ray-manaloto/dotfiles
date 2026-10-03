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


def _deny_reason(target: Path, main: Path | None = None) -> str:
    checkout = str(main) if main is not None else "<main>"
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
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=anchor,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return _deny_reason(target)
        common_dir = Path(proc.stdout.strip())
        if not common_dir.is_absolute():
            common_dir = anchor / common_dir
        main = common_dir.resolve().parent
        if not target.is_absolute():
            target = anchor / target
        target = target.resolve()
    except OSError, ValueError, subprocess.SubprocessError:
        return _deny_reason(target)

    allowed = main / ".claude" / "worktrees"
    if target != allowed and target.is_relative_to(allowed):
        try:
            proc = subprocess.run(
                ["git", "worktree", "list", "--porcelain", "-z"],
                cwd=anchor,
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if (
                target.is_dir()
                and proc.returncode == 0
                and any(
                    Path(record.removeprefix("worktree ")).resolve() == target
                    for record in proc.stdout.split("\0")
                    if record.startswith("worktree ")
                )
            ):
                return None
        except OSError, ValueError, subprocess.SubprocessError:
            pass
    return _deny_reason(target, main)
