"""PreToolUse Bash guard: canonical mise tasks over one-off commands.

``dotfiles-setup hook pretooluse`` is the single project PreToolUse hook
(wired in ``.claude/settings.json``). It reads the hook JSON from stdin
and either allows the Bash call (silent exit 0) or denies it with a
redirect reason via the documented JSON contract
(``permissionDecision: "deny"`` — deterministic, applies even in
bypassPermissions mode).

Why a deny-with-redirect hook and not more: the deep-research pass
(.omc/research/research-20260707-gha-shipland-enforcement/report.md)
verified that hooks cannot ALLOW-list (the JSON "approve" path was
refuted) — allow rules belong to the permission system — and that
markdown rules alone are "relying on the LLM". So: hard bans and
redirects live here; hookify remains advisory-grade (fail-open).

Scope (Ray's decision, 2026-07-07): WORKFLOW commands only — commands
that have a canonical mise task. Read-only/diagnostic commands
(``docker ps``, ``gh pr view``, granular ``pytest path::test``) pass
untouched. This module also absorbs the two legacy shell guards (npx,
chezmoi apply/update) which exited 1 — a NON-blocking code for
PreToolUse; the intent was clearly to block, so consolidating here
fixes them.
"""

from __future__ import annotations

import json
import os
import re
import sys

# (pattern, reason). First match wins. Patterns run against the whole
# Bash command string; they are deliberately narrow — a redirect that
# misfires on legitimate diagnostics erodes trust in the guard.
#
# _CMD anchors every rule to command position (start of string or right
# after a shell separator) so quoted/prose mentions — `echo 'gh pr
# merge'`, `rg 'npx' docs/`, a commit message DESCRIBING the chezmoi
# ban — never false-positive. Probe-observed 2026-07-07: the unanchored
# chezmoi rule denied a commit whose message documented it. Anchoring
# still catches every real invocation (they sit at command position).
_CMD = r"(?:^|[;&|(]\s*)"
_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(_CMD + r"npx\s"),
        "Do not use npx. Use the mise-installed binary directly (e.g. "
        "`agnix`, not `npx agnix`) — all tools are pinned in mise.toml. "
        "See .claude/rules/ci-local-parity.md.",
    ),
    (
        re.compile(_CMD + r"chezmoi\s+(apply|update)\b"),
        "chezmoi apply/update is blocked on the Mac host — it may only run "
        "inside the devcontainer (chezmoi.os == 'linux' renders the "
        "container-only overlay). Read-only chezmoi commands are fine. See "
        ".claude/rules/use-tool-builtins.md.",
    ),
    (
        re.compile(_CMD + r"hk\s+run\s+pre-commit\b"),
        "Use `mise run lint` — it wraps hk in a hard timeout (hk has none) "
        "with log-tail diagnostics. See "
        ".claude/rules/long-running-command-hangs.md.",
    ),
    (
        re.compile(_CMD + r"devcontainer\s+up\b"),
        "Use `mise run up` (or `mise run dev-rebuild` to force-refresh) — "
        "the task carries BASE_IMAGE/platform/ssh-port env and the "
        "workspace-hash collision guard a raw `devcontainer up` misses.",
    ),
    (
        re.compile(_CMD + r"devcontainer\s+build\b"),
        "Use `mise run dev-rebuild` — the overlay build needs the task's "
        "env (BASE_IMAGE, DOCKER_DEFAULT_PLATFORM) to be reproducible.",
    ),
    (
        re.compile(_CMD + r"docker\s+pull\b.*dotfiles-devcontainer"),
        "Never classic-pull the devcontainer image (it wedges on the ~38GB "
        "blob). Use `mise run sync` — buildkit-based, digest-aware, and it "
        "verifies the result.",
    ),
    (
        re.compile(_CMD + r"gh\s+pr\s+create\b"),
        "Use `mise run ship` — it runs the path-aware gate matrix (incl. "
        "the hard full-sync gate on devcontainer-surface diffs) before the "
        "PR opens, then watches checks to bucket-verified green. See "
        ".claude/skills/pr-workflow/SKILL.md.",
    ),
    (
        re.compile(_CMD + r"gh\s+pr\s+merge\b"),
        "Use `mise run land -- <PR#>` — it verifies check buckets, pins the "
        "merge to the verified head SHA, watches main CI, and validates "
        "locally. See .claude/skills/pr-workflow/SKILL.md.",
    ),
)

# NO pytest rule, deliberately (probe-observed 2026-07-07): Claude Code's
# permission engine UNWRAPS runner commands before invoking hooks — the
# canonical `uv run --project python pytest tests/` reaches the hook as
# plain `pytest tests/`, indistinguishable from the bare form the rule
# meant to redirect. A rule here would deny the documented command.
# Bare-pytest guidance stays doc-level (python/AGENTS.md, mise-tasks-only).


def decide(command: str) -> str | None:
    """Redirect reason when ``command`` should be denied, else None."""
    for pattern, reason in _RULES:
        if pattern.search(command):
            return reason
    return None


def _read_command() -> str:
    """Bash command from the hook stdin JSON (env-var fallback)."""
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        tool_input = payload.get("tool_input", payload)
        if isinstance(tool_input, dict):
            return str(tool_input.get("command", ""))
    legacy = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if legacy:
        try:
            return str(json.loads(legacy).get("command", ""))
        except json.JSONDecodeError, AttributeError:
            return ""
    return ""


def pretooluse_main() -> int:
    """Hook entry: emit a deny decision or allow silently.

    Always exits 0 — the decision travels in the JSON (the documented
    contract); a crash here would fail OPEN (hook errors do not block),
    which is the acceptable failure mode for a redirect guard.
    """
    reason = decide(_read_command())
    if reason is not None:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
            + "\n"
        )
    return 0
