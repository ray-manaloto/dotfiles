# Copyright (c) 2026 Raymond Manaloto
"""ONE process for every per-tool-call PreToolUse hook this project wires.

Until 2026-10-02 a single Bash tool call started two project hooks in parallel:
``pretooluse-guard.sh`` (bash -> ``uv python find`` -> ``uv run`` -> the whole
``dotfiles-setup`` CLI) and ``graphify-hook-guard.sh`` (bash -> ``uv run`` ->
``dotfiles-setup`` -> a second Python for graphify). Measured at load ~6: 0.57-0.64
s plus 0.61-0.69 s of process starts per call, on every call, in every session
(`docs/research/kb/reports/agents/host-load-review-2026-10-02.md`).

``scripts/pretooluse-guard.sh`` now runs this module directly with the venv's
own interpreter (``python -m dotfiles_setup.hook_dispatch <root>``) — no ``uv``
resolution per call, and only light imports (``dotfiles_setup.main`` alone costs
~300 ms). One stdin read feeds three consumers:

1. the policy guard (:func:`hook_guard.decide_payload`) for the tools it
   governs — a deny is final, and the nudge is skipped;
2. the #1606 EnterWorktree location guard (:func:`worktree_guard.decide`),
   anchored to the payload ``cwd`` (the project root when absent) — it fails
   CLOSED itself, denying any path it cannot verify;
3. graphify's advisory nudge (:func:`graphify_hook.nudge`) for the tools
   graphify reads: Bash and Grep are ``search``, Read and Glob are ``read``.

Fails open like its predecessors only on an UNCAUGHT exception: that leaves the
call allowed, and the bash wrapper records the fail-open (#343).
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotfiles_setup import graphify_hook, hook_guard, worktree_guard

__all__ = ["GRAPHIFY_KINDS", "GUARDED_TOOLS", "dispatch", "main"]

#: Tools the policy guard decides on (mise-tasks-only redirects for Bash,
#: ask-quality for AskUserQuestion, the default-branch/script guards for writes).
GUARDED_TOOLS = frozenset({"Bash", "AskUserQuestion", "Edit", "Write", "NotebookEdit"})

#: Tools graphify nudges on, mapped to graphify's own ``hook-guard`` kind.
GRAPHIFY_KINDS: dict[str, str] = {
    "Bash": "search",
    "Grep": "search",
    "Read": "read",
    "Glob": "read",
}


def dispatch(project_root: Path, raw: str) -> str:
    """The hook output for one PreToolUse payload (``""`` allows silently)."""
    tool_name, tool_input, payload = hook_guard.parse_payload(raw)
    # An absent tool_name is the legacy Bash shape (hook_guard.decide_payload).
    if not tool_name or tool_name in GUARDED_TOOLS:
        reason = hook_guard.decide_payload(tool_name, tool_input)
        if reason is not None:
            return hook_guard.deny_output(reason)
    if worktree_guard.handles(tool_name):
        cwd = payload.get("cwd")
        session_cwd = Path(cwd) if isinstance(cwd, str) and cwd else None
        reason = worktree_guard.decide(tool_input, project_root, session_cwd)
        if reason is not None:
            return hook_guard.deny_output(reason)
    kind = GRAPHIFY_KINDS.get(tool_name)
    if kind is None:
        return ""
    return graphify_hook.nudge(project_root, kind, raw)


def main(argv: list[str] | None = None) -> int:
    """Read the payload on stdin, print the decision/nudge, exit 0."""
    args = sys.argv[1:] if argv is None else argv
    project_root = Path(args[0]) if args else Path.cwd()
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    sys.stdout.write(dispatch(project_root, raw))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
