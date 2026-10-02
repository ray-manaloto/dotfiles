# Copyright (c) 2026 Raymond Manaloto
"""graphify's PreToolUse nudge, rewritten to this repo's wording — kept LIGHT.

This runs inside the merged per-tool-call hook (:mod:`dotfiles_setup.
hook_dispatch`), on every Bash/Grep/Read/Glob call in every session. It
therefore must not import :mod:`dotfiles_setup.graphify`, which costs ~215 ms
(it pulls in ``kb_setup.graph``) — measured 2026-10-02, against ~10 ms for
this module's own imports.

graphify's own nudge stays a SUBPROCESS: its only implementation is the
private ``graphify.cli._run_hook_guard`` (no public API; ruff's SLF001 and the
zero-suppression rule bar calling it), and the public ``main()`` may re-exec the
interpreter. The subprocess is the venv's own ``graphify`` next to
``sys.executable``: this module runs from the venv interpreter directly, NOT
under ``uv run``, so a bare ``graphify`` would resolve through ``PATH`` to the
mise shim / user-global pin instead of the repo-locked version
(``graphify-first.md``).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from dotfiles_setup.child_env import without_env_diff
from dotfiles_setup.mise_config_context import already_seen, was_seen

__all__ = [
    "NO_AUTO_REFRESH_ENV",
    "graphify_binary",
    "hook_guard_main",
    "nudge",
    "rewrite_hook_nudge",
]

# Graphify 0.9.72 (#3895) rewrites a stale HOME-level skill copy on any
# non-install command; do-not.md #8 forbids graphify writing under $HOME, so
# every child this package spawns opts out (root mise.toml [env] sets it too).
NO_AUTO_REFRESH_ENV = "GRAPHIFY_NO_AUTO_REFRESH"

#: A wedged graphify must not eat the hook's whole 20 s budget.
_NUDGE_TIMEOUT_S = 10.0


def graphify_binary() -> str:
    """The venv's ``graphify`` beside this interpreter, else a bare name."""
    candidate = Path(sys.executable).parent / "graphify"
    return str(candidate) if candidate.is_file() else "graphify"


def _run(
    args: list[str], *, cwd: Path, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run graphify's hook-guard (``__MISE_DIFF`` scrubbed, auto-refresh off)."""
    child_env = without_env_diff()
    child_env[NO_AUTO_REFRESH_ENV] = "1"
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        input=stdin,
        env=child_env,
        timeout=_NUDGE_TIMEOUT_S,
    )


#: Replaces graphify's hardcoded "MANDATORY ... You MUST run" nudges, stated as
#: facts per Claude Code's hook guidance ($CC/hooks.md:1033: imperative
#: out-of-band text can trip prompt-injection defenses) and the standard
#: tests/test_mise_config_context.py pins for this repo's own hook text.
_GRAPH_NUDGE = (
    "graphify-out/graph.json exists for this repository. `mise run graphify-query "
    '-- "<question>"` answers structural questions (callers, dependencies, where '
    "a symbol lives) from it; `mise run graphify-health` reports whether it is "
    "current."
)


def _general_nudge(text: str) -> dict[str, object] | None:
    """The parsed payload when `text` is one of graphify's two ``MANDATORY:`` nudges.

    Only that general, advisory nudge is replaced and deduplicated. Anything
    else — the per-file stale nudge, and above all a payload carrying a
    ``permissionDecision`` (graphify's opt-in strict-mode deny) — is not it.
    """
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    hook = payload.get("hookSpecificOutput") if isinstance(payload, dict) else None
    if not isinstance(hook, dict) or "permissionDecision" in hook:
        return None
    context = hook.get("additionalContext")
    if isinstance(context, str) and context.startswith("MANDATORY:"):
        return payload
    return None


def rewrite_hook_nudge(text: str) -> str:
    """Rewrite graphify's own PreToolUse nudge text to this repo's wording.

    graphify's ``hook-guard`` subcommand hardcodes its nudge copy
    (``graphify/cli.py`` — no flag or env var changes the wording). The two
    ``MANDATORY:`` nudges are replaced whole with :data:`_GRAPH_NUDGE`: they
    name bare-binary commands ``graphify-first.md`` forbids (including
    ``graphify explain``/``path``, which have no mise task) and demand a query
    regardless of graph health. Any other payload (the stale-file nudge) gets
    plain substitution of the bare ``query``/``update`` commands.
    """
    payload = _general_nudge(text)
    if payload is not None:
        hook = payload["hookSpecificOutput"]
        if isinstance(hook, dict):
            hook["additionalContext"] = _GRAPH_NUDGE
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    return text.replace("`graphify query", "`mise run graphify-query --").replace(
        "`graphify update`", "`mise run graphify-rebuild`"
    )


def nudge(project_root: Path, kind: str, raw: str) -> str:
    """Return graphify's advisory nudge for one payload, rewritten; ``""`` if none.

    ``kind`` is ``search`` (Bash|Grep) or ``read`` (Read|Glob), graphify's own
    vocabulary. Never raises for a graphify failure: a missing, failing,
    timed-out or silent graphify yields ``""``.

    The general nudge is delivered once per session and agent (the
    ``mise_config_context`` marker): after the rewrite the search and read
    variants are the same sentence, and repeating it on every search/read is
    re-insertion, not information. Only that nudge is deduplicated — the
    per-file stale nudge carries information specific to the file, and a
    ``permissionDecision`` payload is a decision, never a reminder, so both
    always pass through.

    A ``search`` whose session already got the general nudge does not spawn
    graphify at all: graphify 0.9.73's search branch can emit only that nudge
    (``graphify/cli.py`` ``_run_hook_guard``; search stays nudge-only even in
    strict mode), so the spawn could only produce text that would be dropped.
    ``read`` still spawns — its stale-file nudge is per file.
    """
    try:
        event = json.loads(raw) if raw.strip() else {}
    except ValueError:
        event = {}
    if not isinstance(event, dict):
        event = {}
    session_id = str(event.get("session_id", ""))
    agent_id = str(event.get("agent_id", ""))
    marker = f"graphify-nudge-{session_id}"
    if kind == "search" and session_id and was_seen(project_root, marker, agent_id):
        return ""
    try:
        result = _run(
            [graphify_binary(), "hook-guard", kind], cwd=project_root, stdin=raw
        )
    except OSError, subprocess.TimeoutExpired:
        return ""
    if result.returncode != 0 or not result.stdout:
        return ""
    if (
        session_id
        and _general_nudge(result.stdout) is not None
        and already_seen(project_root, marker, agent_id)
    ):
        return ""
    return rewrite_hook_nudge(result.stdout)


def hook_guard_main(project_root: Path, kind: str) -> int:
    """CLI entry for ``dotfiles-setup graphify hook-guard <kind>``.

    Reads the hook payload on stdin, prints :func:`nudge`'s text, and always
    returns 0 (never blocks the tool call it is attached to). The wired hook
    reaches :func:`nudge` through :mod:`dotfiles_setup.hook_dispatch`; this
    entry stays for probing one kind by hand.
    """
    try:
        raw = sys.stdin.read()
    except OSError:
        raw = ""
    sys.stdout.write(nudge(project_root, kind, raw))
    return 0
