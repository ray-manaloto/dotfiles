# Copyright (c) 2026 Raymond Manaloto
"""Redirect EnterWorktree paths that would park background sessions (#1606).

Native ``name=`` creation uses the main checkout's ``.claude/worktrees/``.
Permission allow rules cannot suppress the relocation prompt for external
paths (``$CC/worktrees.md``), so the existing PreToolUse hook denies them.
Only stdlib imports: git runs only when deciding an EnterWorktree path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def handles(tool_name: str) -> bool:
    """Whether this guard decides on the named tool."""
    return tool_name == "EnterWorktree"


def decide(tool_input: dict[str, object], project_dir: Path) -> str | None:
    """Deny paths outside the main worktree directory; fail open without git."""
    path = tool_input.get("path")
    if not isinstance(path, str) or not path:
        return None
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        common_dir = Path(proc.stdout.strip())
        if not common_dir.is_absolute():
            common_dir = project_dir / common_dir
        main = common_dir.resolve().parent
        target = Path(path)
        if not target.is_absolute():
            target = project_dir / target
        target = target.resolve()
    except OSError, ValueError, subprocess.SubprocessError:
        return None

    allowed = main / ".claude" / "worktrees"
    if target != allowed and target.is_relative_to(allowed):
        return None
    return (
        f"#1606: EnterWorktree path={target} must be strictly inside {allowed}/. "
        "External paths raise a permission prompt that parks --bg coordinators. "
        f"From the main checkout ({main}), use `EnterWorktree name=<name>`. "
        "From inside a worktree session, only "
        f"`EnterWorktree path={allowed}/<name>` works."
    )
