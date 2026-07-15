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
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    """One deny rule: what it matches, why, and when it started denying.

    ``since`` is the ISO date (UTC) the rule LANDED ON MAIN — the date from
    which a matching command that actually RAN is a genuine bypass. It exists
    for :mod:`dotfiles_setup.command_audit`, which scans transcripts reaching
    back long before the guard did: with no per-rule cutoff, every historical
    ``gh pr create`` (2026-07-01, when no guard existed) reads as an evasion.
    Measured 2026-07-14: 147 of 155 rule-matching commands predated their rule
    — a 95% false-alarm rate that buries any real signal.

    Set ``since`` when a rule is ADDED and never touch it again: it dates the
    RULE, not the wording. Rewording a reason must not reset the cutoff, or
    real bypasses go dark. (Deriving these from ``git log -S`` was rejected:
    non-deterministic, slow, needs git at scan time, and a reword would reset
    the date — the very failure this field is pinned against. A test asserts
    every rule carries a valid one.)

    ``name`` is a short shape label. The audit report groups guard denials by
    rule identity, because grouping them by command head is meaningless — a
    prose false-positive like ``ps aux | grep -iE "…|devcontainer up|…"``
    groups under ``echo``, naming nothing.
    """

    name: str
    pattern: re.Pattern[str]
    reason: str
    since: str


# First match wins. Patterns run against the whole Bash command string;
# they are deliberately narrow — a redirect that misfires on legitimate
# diagnostics erodes trust in the guard.
#
# _CMD anchors every rule to command position (start of string or right
# after a shell separator) so quoted/prose mentions — `echo 'gh pr
# merge'`, `rg 'npx' docs/`, a commit message DESCRIBING the chezmoi
# ban — never false-positive. Probe-observed 2026-07-07: the unanchored
# chezmoi rule denied a commit whose message documented it. Anchoring
# still catches every real invocation (they sit at command position).
# Findings [13][14][15]: newline is a separator; common wrappers
# (env/VAR=x/exec/nohup/time/timeout N/xargs, possibly stacked) must not
# hide the real command; and the open-paren was removed from the class —
# it false-positived on quoted prose (probe-observed live: the guard
# denied a review agent quoting the merge rule). Deliberately fail-open
# beyond this (sh -c, base64, aliases): this is a redirect guard, not a
# sandbox — hard bans live in settings.json permissions deny.
#
# Anchoring does NOT make the guard quoting-aware, and that gap is the only
# defect the audit has ever measured (#265): the separator class cannot see
# that a `|` INSIDE a quoted string is not a shell separator, so
# `grep -iE "…|devcontainer up|…"` denies. 2 of the 3 denials this guard has
# ever issued were this shape; 0 commands have ever evaded it. Any narrowing
# here should trade recall for precision — never the reverse.
_WRAPPER = (
    r"(?:(?:env\s+)?(?:\w+=\S*\s+)*"
    r"(?:exec\s+|nohup\s+|time\s+|timeout\s+\S+\s+|xargs\s+)?)*"
)
_CMD = r"(?:^|[;&|\n]\s*)" + _WRAPPER
# The eight original rules landed together in #174 (90d699e, 2026-07-07);
# #176 re-anchored them the same day, so the cutoff is unchanged.
_V1 = "2026-07-07"
# The three workflow-observation rules landed in #260 (7eae108, 2026-07-14).
_V2 = "2026-07-14"

_RULES: tuple[Rule, ...] = (
    Rule(
        "npx",
        re.compile(_CMD + r"npx\s"),
        "Do not use npx. Use the mise-installed binary directly (e.g. "
        "`agnix`, not `npx agnix`) — all tools are pinned in mise.toml. "
        "See .claude/rules/ci-local-parity.md.",
        _V1,
    ),
    Rule(
        "chezmoi apply/update",
        re.compile(_CMD + r"chezmoi\s+(apply|update)\b"),
        "chezmoi apply/update is blocked on the Mac host — it may only run "
        "inside the devcontainer (chezmoi.os == 'linux' renders the "
        "container-only overlay). Read-only chezmoi commands are fine. See "
        ".claude/rules/use-tool-builtins.md.",
        _V1,
    ),
    Rule(
        "hk run pre-commit",
        re.compile(_CMD + r"hk\s+run\s+pre-commit\b"),
        "Use `mise run lint` — it wraps hk in a hard timeout (hk has none) "
        "with log-tail diagnostics. See "
        ".claude/rules/long-running-command-hangs.md.",
        _V1,
    ),
    Rule(
        "devcontainer up",
        re.compile(_CMD + r"devcontainer\s+up\b"),
        "Use `mise run up` (or `mise run dev-rebuild` to force-refresh) — "
        "the task carries BASE_IMAGE/platform/ssh-port env and the "
        "workspace-hash collision guard a raw `devcontainer up` misses.",
        _V1,
    ),
    Rule(
        "devcontainer build",
        re.compile(_CMD + r"devcontainer\s+build\b"),
        "Use `mise run dev-rebuild` — the overlay build needs the task's "
        "env (BASE_IMAGE, DOCKER_DEFAULT_PLATFORM) to be reproducible.",
        _V1,
    ),
    Rule(
        "docker pull (devcontainer image)",
        re.compile(
            _CMD + r"docker\s+(?:image\s+)?pull\b[^;&|\n]*dotfiles-devcontainer"
        ),
        "Never classic-pull the devcontainer image (it wedges on the ~38GB "
        "blob). Use `mise run sync` — buildkit-based, digest-aware, and it "
        "verifies the result.",
        _V1,
    ),
    Rule(
        "gh pr create",
        re.compile(_CMD + r"gh\s+pr\s+create\b"),
        "Use `mise run ship` — it runs the path-aware gate matrix (incl. "
        "the hard full-sync gate on devcontainer-surface diffs) before the "
        "PR opens, then watches checks to bucket-verified green. See "
        ".claude/skills/pr-workflow/SKILL.md.",
        _V1,
    ),
    Rule(
        "gh pr merge",
        re.compile(_CMD + r"gh\s+pr\s+merge\b"),
        "Use `mise run land -- <PR#>` — it verifies check buckets, pins the "
        "merge to the verified head SHA, watches main CI, and validates "
        "locally. See .claude/skills/pr-workflow/SKILL.md.",
        _V1,
    ),
    # `nohup`/manual detachment of a mise task orphans it from the harness
    # (no completion notification, hand-rolled log-polling on top). _CMD's
    # _WRAPPER treats `nohup` as transparent for OTHER rules, so `mise run`
    # (otherwise canonical/allowed) slips through when detached — hence a
    # dedicated rule that anchors `nohup` at command position and requires a
    # `mise run` later in the same segment.
    Rule(
        "nohup mise run",
        re.compile(
            r"(?:^|[;&|\n]\s*)(?:env\s+)?(?:\w+=\S*\s+)*nohup\s+[^;&|\n]*"
            r"mise\s+run\b"
        ),
        "Do not `nohup`/hand-detach a `mise run` task. Run it via the harness "
        "background mechanism so it stays tracked and reports one clean "
        "completion — no orphaned process, no hand-rolled log monitor. See "
        ".claude/rules/mise-tasks-only.md.",
        _V2,
    ),
    Rule(
        "gh run watch",
        re.compile(_CMD + r"gh\s+run\s+watch\b"),
        "Do not hand-roll `gh run watch` (it reports prematurely — see "
        ".claude/rules/gh-cli-watch.md). `mise run land -- <PR#>` already "
        "watches main CI via --json buckets; for a one-shot check use "
        "`gh run view <id> --json conclusion`.",
        _V2,
    ),
    Rule(
        "gh pr checks --watch",
        re.compile(_CMD + r"gh\s+pr\s+checks\b[^;&|\n]*--watch\b"),
        "Do not hand-roll `gh pr checks --watch` — `mise run ship` already "
        "watches PR checks to bucket-verified green and `mise run land` "
        "watches main CI. A one-shot `gh pr checks <n> --json` read is fine. "
        "See .claude/rules/mise-tasks-only.md.",
        _V2,
    ),
)

# NO pytest rule, deliberately (probe-observed 2026-07-07): Claude Code's
# permission engine UNWRAPS runner commands before invoking hooks — the
# canonical `uv run --project python pytest tests/` reaches the hook as
# plain `pytest tests/`, indistinguishable from the bare form the rule
# meant to redirect. A rule here would deny the documented command.
# Bare-pytest guidance stays doc-level (python/AGENTS.md, mise-tasks-only).

# NO `cd`-prefix unwrap, deliberately (probe-observed 2026-07-14): the
# "chained-command evasion" the enforcement research predicted for
# `cd /x && gh pr create` does not exist here. Every `cd` prefix ends in
# `&&`/`;`/newline BY CONSTRUCTION, `_CMD`'s `[;&|\n]` class re-anchors on
# that separator, and `re.search` retries at every offset — so the rule
# already matches the operative command. Mirroring `command_audit._operative`
# into `decide()` would be dead code: that module needs the unwrap because it
# reads token[0] after `.split()` (a genuinely positional read); a regex
# search is not positional. tests/test_hook_guard.py pins the cd-prefixed
# denials so a future narrowing of `_CMD` fails loudly rather than silently
# opening the bypass.


def rules() -> tuple[Rule, ...]:
    """Every deny rule, in match order — the guard's introspection surface.

    The rule table is a contract, not an implementation detail: `since` and
    `name` are read outside this module (the audit dates bypasses by the first
    and groups denials by the second), and the invariants that keep those
    honest — every rule dated, every name unique — are asserted against this.
    """
    return _RULES


def match(command: str) -> Rule | None:
    """The first :class:`Rule` matching ``command``, else None.

    Split out of :func:`decide` for :mod:`dotfiles_setup.command_audit`, which
    needs the matched rule's ``since`` date (and ``name``) — not just its
    reason — to tell a genuine bypass from pre-rule history.
    """
    for rule in _RULES:
        if rule.pattern.search(command):
            return rule
    return None


def decide(command: str) -> str | None:
    """Redirect reason when ``command`` should be denied, else None."""
    rule = match(command)
    return rule.reason if rule is not None else None


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
