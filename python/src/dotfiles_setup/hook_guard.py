"""PreToolUse Bash guard: canonical mise tasks over one-off commands.

``dotfiles-setup hook pretooluse`` is the single project PreToolUse hook
(wired in ``.claude/settings.json``). It reads the hook JSON from stdin
and either allows the Bash call (silent exit 0) or denies it with a
redirect reason via the documented JSON contract
(``permissionDecision: "deny"`` — deterministic, applies even in
bypassPermissions mode).

Why a deny-with-redirect hook and not more: the deep-research pass
(docs/research/runs/research-20260707-gha-shipland-enforcement/report.md)
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

from dotfiles_setup.heredoc import HEREDOC_PATTERN, NUL_FILLER, blank_heredoc


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
    rule identity, because grouping them by command head is meaningless — the
    guard's one real denial reaches ``npx`` through a ``||`` fallback after a
    ``cd``+``echo`` preamble, so it groups under ``echo``, naming nothing.
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
# Anchoring alone did NOT make the guard quoting-aware, and that gap was the
# only defect the audit ever measured (#265): the separator class could not see
# that a `|` INSIDE a quoted string is not a shell separator, so
# `grep -iE "…|devcontainer up|…"` denied. 2 of the 3 denials this guard had
# ever issued were that shape; 0 commands have ever evaded it. `_inert_masked`
# below closes it by neutering separators that are DATA before these rules run;
# the rules themselves are unchanged. Any further narrowing here should keep
# trading recall for precision — never the reverse.
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
# The two evidence-discipline rules (pipe-to-pager, `&`-detachment) landed
# 2026-07-21 — guardrails 2 and 3 of the session-2026-07-21 handoff.
_V3 = "2026-07-21"
# The repo-aware gh-pr rules landed 2026-07-23, once the knowledge-base repo
# grew its own kb-ship/kb-land to redirect to.
_V4 = "2026-07-23"
# The bot-PR arming rule landed 2026-07-27 with `mise run automerge` (#369) —
# the same "the redirect target must be able to do the job" fix as _V4, along
# the PR-provenance axis instead of the target-repo one. Until the verb
# existed, `gh pr merge --auto` on a Renovate PR could only be redirected to
# `land`, which refuses an OPEN PR.
_V5 = "2026-07-27"

# `gh` names a target repo with `-R owner/repo` / `--repo owner/repo` (or
# `--repo=owner/repo`); with none, it infers from cwd — which, for a guard
# running in this repo, means dotfiles. Both fragments are SUFFIXES appended
# after `gh pr create|merge`, and both scan only to the next shell separator so
# they cannot read a flag belonging to a later command in a compound.
_GH_REPO = r"(?:-R|--repo)[=\s]\s*"
_REPO_RE = r"[\w.-]+/[\w.-]+"
# "an explicit -R naming the knowledge-base repo appears in this command"
_GH_REPO_IS_KB = rf"(?=[^;&|\n]*{_GH_REPO}ray-manaloto/knowledge-base\b)"
# "no explicit -R naming a repo OTHER than dotfiles appears in this command" —
# so a bare `gh pr create` (cwd = dotfiles) still denies, while a sibling repo's
# is left alone.
_GH_REPO_NOT_FOREIGN = rf"(?![^;&|\n]*{_GH_REPO}(?!ray-manaloto/dotfiles\b){_REPO_RE})"

# A GATE command: one whose exit code is the answer you are about to act on.
# Deliberately NOT every command — `git log | head` is fine, and a rule that
# misfires on legitimate diagnostics erodes trust in the guard.
#
# `pytest` is the one token here that also occurs as ordinary prose in this
# repo's docs, so it is only ever reached through `_CMD` (command position)
# or the `uv run --project python` prefix below. `rg 'pytest' docs/ | head`
# must stay allowed; tests/test_hook_guard.py pins that.
_GATE = (
    r"(?:mise\s+run\s+"
    r"(?:lint|fmt|test|verify[\w-]*|ship|land|bakeoff|smoke[\w-]*"
    r"|lint-docs|pin-actions|check-doc-refs)\b"
    r"|dotfiles-setup\s+verify\b"
    r"|hk\s+(?:run|fix|check)\b"
    r"|pytest\b)"
)
# `uv run --project python pytest …` — the canonical runner prefix, which
# `_WRAPPER` does not model (it covers env/exec/nohup/time/timeout/xargs).
_RUNNER = r"(?:uv\s+run\s+(?:-\S+\s+\S+\s+)*)?"

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
        "hk run pre-commit/check",
        re.compile(_CMD + r"hk\s+run\s+(?:pre-commit|check)\b"),
        "Use `mise run lint` (read-only gate, ≡ CI) — it wraps hk in a hard "
        "timeout (hk has none) with log-tail diagnostics. To apply fixes use "
        "`mise run fmt`. See .claude/rules/long-running-command-hangs.md.",
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
    # --- gh pr create/merge: REPO-AWARE (#349 follow-up, 2026-07-23) ---
    #
    # These rules used to match `gh pr create|merge` unconditionally, which was
    # wrong the moment a second repo entered the picture: a knowledge-base PR was
    # denied and redirected to `mise run land`, a DOTFILES task that has no repo
    # parameter, watches dotfiles' main CI, and re-validates the dotfiles
    # devcontainer. The guard blocked the only working command and pointed at a
    # task that cannot do the job. Measured 2026-07-23 — it is why KB PRs #1 and
    # #2 had to be merged by hand.
    #
    # Dispatch is by TARGET repo, resolved from an explicit `-R`/`--repo`:
    #   dotfiles (or no -R, i.e. cwd)  -> ship / land
    #   knowledge-base                 -> kb-ship / kb-land
    #   any other repo                 -> ALLOW
    # Allowing the rest is deliberate: no canonical task exists for a sibling
    # repo, so a deny would redirect to nothing and merely block real work. This
    # is a redirect guard, not a sandbox (it already fails open on `$(…)`,
    # `sh -c`, and aliases) — see .claude/rules/mise-tasks-only.md.
    #
    # KB rules come FIRST because first match wins; the dotfiles rules carry a
    # negative lookahead so they do not swallow another repo's `-R`.
    Rule(
        "gh pr create (knowledge-base)",
        re.compile(_CMD + r"gh\s+pr\s+create\b" + _GH_REPO_IS_KB),
        "Use `mise run kb-ship` (in the knowledge-base repo) — it runs that "
        "repo's lint+test gates BEFORE pushing, so a red branch never becomes "
        "a PR. `mise run ship` is a dotfiles task and cannot ship a KB PR.",
        _V4,
    ),
    Rule(
        "gh pr merge (knowledge-base)",
        re.compile(_CMD + r"gh\s+pr\s+merge\b" + _GH_REPO_IS_KB),
        "Use `mise run kb-land -- <PR#>` (in the knowledge-base repo) — it "
        "verifies the checks, then pins the merge to that verified head SHA. "
        "`mise run land` is a dotfiles task: no repo parameter, and it watches "
        "dotfiles' main CI.",
        _V4,
    ),
    Rule(
        "gh pr create",
        re.compile(_CMD + r"gh\s+pr\s+create\b" + _GH_REPO_NOT_FOREIGN),
        "Use `mise run ship` — it runs the path-aware gate matrix (incl. "
        "the hard full-sync gate on devcontainer-surface diffs) before the "
        "PR opens, then watches checks to bucket-verified green. See "
        ".claude/skills/pr-workflow/SKILL.md.",
        _V1,
    ),
    # `--auto` names the intent exactly — ARM auto-merge — and that is the one
    # thing `land` cannot do, which is how #369 became an outage: a Renovate PR
    # never runs ship, so nothing armed it, and the only sanctioned redirect
    # pointed at a task that refuses an OPEN PR. Ordered BEFORE the generic
    # merge rule (first match wins) so the precise shape gets the precise
    # redirect. The repo lookahead sits at the same position as the other
    # gh-pr rules, so a `-R` naming a foreign repo is seen wherever it appears.
    Rule(
        "gh pr merge --auto",
        re.compile(
            _CMD + r"gh\s+pr\s+merge\b" + _GH_REPO_NOT_FOREIGN + r"[^;&|\n]*--auto\b"
        ),
        "Use `mise run automerge -- <PR#>` for a BOT-opened PR (Renovate / the "
        "refresh bot) — it checks provenance, then arms auto-merge pinned to "
        "the head SHA and exits. For your OWN branch use `mise run ship`, which "
        "gates the tree before arming. See .claude/skills/pr-workflow/SKILL.md.",
        _V5,
    ),
    Rule(
        "gh pr merge",
        re.compile(_CMD + r"gh\s+pr\s+merge\b" + _GH_REPO_NOT_FOREIGN),
        "Merging is armed, not performed, in this repo — one verb per PR "
        "provenance: `mise run ship` for your own branch (gates, then arms), "
        "`mise run automerge -- <PR#>` for a bot-opened PR (#369). Once GitHub "
        "has merged it, `mise run land -- <PR#>` runs the post-merge main-CI "
        "check + local validation. See .claude/skills/pr-workflow/SKILL.md.",
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
    # Bash returns the LAST pipeline element's exit code, so `mise run lint
    # 2>&1 | tail -40` reports tail's 0 even when the gate failed or was
    # killed. That is how a 7-hour wedged hk run read as a pass (2026-06-29)
    # and why .claude/rules/long-running-command-hangs.md rule 3 exists — a
    # rule broken again in the 2026-07-21 session, hence the machine layer.
    #
    # The span between the gate and the pager allows `|` on purpose, so
    # `<gate> | grep x | tail` is caught too, but stops at `;`/`&&`/newline so
    # the match cannot run past the gate's own segment into an unrelated
    # `mise run lint && docker ps | tail`. `&` is admitted ONLY as an fd-dup
    # (`(?<=>)&`, i.e. `2>&1` — near-universal in the very commands this rule
    # targets); a bare `&` is a background operator and ends the segment.
    Rule(
        "gate command piped to head/tail",
        re.compile(
            _CMD + _RUNNER + _GATE + r"(?:[^;&\n]|(?<=>)&)*\|\s*(?:tail|head)\b"
        ),
        "Do not pipe a gate command into `tail`/`head` — bash returns the "
        "PIPE's exit code (tail's 0), silently masking a failed or killed "
        "gate. Redirect to a file and read the recorded rc instead: "
        '`<cmd> > /tmp/out.log 2>&1; echo "rc=$?" >> /tmp/out.log`, then '
        "read the file. See .claude/rules/long-running-command-hangs.md "
        "rule 3 and .claude/rules/verify-before-advancing.md "
        "(evidence discipline).",
        _V3,
    ),
    # The `&` sibling of the `nohup mise run` rule above: same orphaning, same
    # redirect. Measured twice on 2026-07-21 — a bare `&` was reaped at ~2min
    # and a 10-minute foreground bound killed a bake-off at rc=143. The harness
    # background mechanism is the one path that stays tracked.
    #
    # The lookarounds are what make this a BACKGROUND operator and not a false
    # positive: `(?!&)` excludes `&&`, and `(?<![&>])` excludes both the second
    # `&` of `&&` and the `&` of a `2>&1` fd-dup (which is otherwise the most
    # common `&` in a detached command line).
    Rule(
        "backgrounded mise run",
        re.compile(
            r"(?:^|[;&|\n]\s*)"
            + _WRAPPER
            + r"mise\s+run\b[^;\n]*?(?<![&>])&(?!&)\s*(?:$|[;\n])"
        ),
        "Do not hand-detach a `mise run` task with a trailing `&`. Long "
        "Mac-side tasks backgrounded this way get REAPED when the turn goes "
        "idle. Use the harness background mechanism so it stays tracked and "
        "reports one clean completion. See "
        ".claude/rules/long-running-command-hangs.md rule 2 and "
        ".claude/rules/mise-tasks-only.md.",
        _V3,
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


# --- #265: a separator inside an inert span is not a separator --------------
#
# `_CMD` anchors on `[;&|\n]`. Bash only treats those characters as syntax when
# they are UNQUOTED, so the rules were denying literals sitting at a "command
# position" that did not exist. Rather than teach 11 rule patterns about
# quoting, the command is normalized ONCE here: every separator that is data
# gets neutered, and the rules run against the result unchanged.
#
# Existing tools were researched first and none fits (the hard gate in
# .claude/rules/use-tool-builtins.md; full report + probe evidence in
# docs/research/runs/research-20260714-guard-quoting/agents/native-options.md):
#   - `shlex(punctuation_chars=True)` — its `whitespace` includes `\n`, so a
#     newline is never an operator token: a heredoc body and two real
#     newline-separated commands tokenize IDENTICALLY. Cannot fix one without
#     losing the other.
#   - `bashlex` — GPLv3, unmaintained since 2024, and raises ParsingError on
#     `<<'EOF'` (upstream #97/#99) — precisely the shape that must be fixed.
#   - `tree-sitter-bash` — correct (a real `heredoc_body` node) but costs two
#     deps and ~20-40ms of import on EVERY Bash call. Kept as the documented
#     upgrade path if richer shell constructs ever matter.
#   - Claude Code natively — the PreToolUse payload carries only the raw
#     string, its own matcher is not callable from Python, and native
#     permission `deny` rules carry no custom-reason field, so they cannot
#     deliver a redirect message. The hook stays.
# So the residue is hand-written, per rule 3 of use-tool-builtins.md: only
# heredoc-boundary detection has no stdlib model. The quote-span scan itself is
# the canonical alternation idiom (Friedl's "unrolling the loop"), not a novel
# parser.
#
# This is a redirect guard, not a sandbox: `$(…)` substitution, `sh -c`/`eval`,
# base64 and aliases are fail-open BY DESIGN. Masking narrows that class
# slightly and DELIBERATELY (measured against the pre-fix guard, not assumed):
# `eval "echo x; gh pr create"` was denied before, because the quoted `;`
# anchored `_CMD`, and is allowed now. That catch was an ACCIDENT, not a
# capability — `eval "gh pr create"` was always allowed, so the class was never
# actually covered; only its separator-bearing variant was, which is not a
# property anyone could have relied on. Losing it is the trade this fix exists
# to make: evasion has measured 0 for the guard's lifetime while false
# positives were 2 of its 3 denials. Pinned by
# tests/test_hook_guard.py::test_masking_trades_the_incidental_eval_catch.

# Exactly `_CMD`'s separator class: neutering these and nothing else is what
# makes the rules quoting-aware without touching a rule.
_SEPARATORS = ";&|\n"

# NUL is the filler because it is the one byte that CANNOT occur in a real Bash
# command (execve arguments are NUL-terminated), so input can never forge it,
# and it is neither `\w` nor `\s` — it cannot be absorbed by `_WRAPPER` or any
# rule token. Substitution is length-preserving so every other offset, and thus
# every rule's view of the surrounding text, is untouched.
_FILLER = NUL_FILLER
_SEPARATOR_TABLE = str.maketrans(_SEPARATORS, _FILLER * len(_SEPARATORS))

# The heredoc pattern + its blanking substitution moved to
# `dotfiles_setup.heredoc` when `workflow_hooks` became a second consumer: a
# workflow `run:` block hits the same "a body is data, not a command" problem,
# and two copies of this regex would drift. Behaviour here is unchanged — the
# guard redacts EVERY heredoc it sees, because the body is an argument to the
# tool being guarded. See that module for why `workflow_hooks` instead uses the
# interpreter-aware `redact_heredoc_bodies`.

# Quoted spans, scanned left-to-right and non-overlapping so alternating quotes
# resolve correctly. The leading `\\.` consumes an escaped character — critical,
# because it stops a `\'`/`\"` from opening a phantom span. Single quotes take
# no escapes (bash semantics), and the double-quoted body is the unrolled-loop
# form whose two alternatives are disjoint, so it cannot backtrack pathologically.
_QUOTED_SPAN = re.compile(
    r"""
      \\.
    | '[^']*'
    | "(?:\\.|[^"\\])*"
    """,
    re.VERBOSE | re.DOTALL,
)


def _blank_quoted(match: re.Match[str]) -> str:
    """Neuter the separators inside one quoted span, keeping its content."""
    span = match.group(0)
    if span[0] not in "\"'":
        return span  # an escaped character, consumed so it cannot open a span
    return span.translate(_SEPARATOR_TABLE)


def _inert_masked(command: str) -> str:
    """``command`` with every separator that is DATA, not syntax, neutered.

    Heredocs are redacted BEFORE quotes, and are redacted *whole* rather than
    separator-only. Both details are load-bearing. A body is stdin data, so
    nothing in it is ever rule-relevant — and blanking it removes any apostrophe
    it contains (``don't``) that would otherwise open a span in the quote pass
    below and run on to a later real quote, neutering the real separators in
    between and silently costing recall.

    Quoted spans get the opposite, conservative treatment: only their separators
    are neutered, because their CONTENT is still rule-relevant — the
    ``docker pull "…dotfiles-devcontainer:dev"`` denial depends on the rule
    reading a literal inside the quotes.

    Deliberately NOT wrapped in try/except: every operation here is total (slice,
    ``len``, ``translate`` over a regex match), so there is no exception to
    catch, and the realistic failure mode — a *wrong* mask — is one no handler
    would see. Fail-open lives where it actually works: a crash exits non-zero,
    which PreToolUse treats as non-blocking, and scripts/pretooluse-guard.sh
    covers a missing interpreter.

    An unterminated quote closes no span, so nothing is redacted and the real
    separators still anchor — a malformed command cannot launder itself.
    """
    return _QUOTED_SPAN.sub(_blank_quoted, HEREDOC_PATTERN.sub(blank_heredoc, command))


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

    Rules run against :func:`_inert_masked`, never the raw string, so a
    separator that is quoted or inside a heredoc body cannot fake a command
    position (#265). Masking here — the one chokepoint :func:`decide` and
    :mod:`dotfiles_setup.command_audit` both go through — is what lets the audit
    MEASURE the fix: the same call that denies a command is the one that
    classifies it, so the report's `blocked` bucket moves without any change
    there.

    Split out of :func:`decide` for :mod:`dotfiles_setup.command_audit`, which
    needs the matched rule's ``since`` date (and ``name``) — not just its
    reason — to tell a genuine bypass from pre-rule history.
    """
    target = _inert_masked(command)
    for rule in _RULES:
        if rule.pattern.search(target):
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
