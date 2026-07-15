# Mise Tasks Only: No One-Off Commands for Canonical Workflows

Every recurring workflow in this repo has (or gets) a canonical mise
task. When a task exists, USE IT — never hand-roll the underlying
command sequence. When you build a new recurring workflow, ship its mise
task (wrapping the python library, zero-bash-logic) in the same change.

## The canonical task map

| Instead of | Use |
|---|---|
| `hk run pre-commit --all` | `mise run lint` (hard timeout + log-tail diagnostics) |
| bare `pytest` | `mise run test`, or `uv run --project python pytest <target>` (doc-level only: the permission engine unwraps runners, so a hook rule would also deny the canonical uv form) |
| `devcontainer up` / `devcontainer build` | `mise run up` / `mise run dev-rebuild` (env + workspace-hash guard) |
| `docker pull …dotfiles-devcontainer…` | `mise run sync` (buildkit, digest-aware, verifying; classic pull wedges on ~38GB) |
| `gh pr create` (+ push + gates by hand) | `mise run ship` |
| `gh pr merge` (+ watch + validate by hand) | `mise run land -- <PR#>` |
| `nohup … mise run <task>` (hand-detaching a task) | the harness background run — stays tracked, one clean completion (no orphaned process, no hand-rolled log monitor) |
| `gh run watch <id>` (hand-rolled CI wait) | `mise run land -- <PR#>` (watches main CI via --json buckets); one-shot: `gh run view <id> --json conclusion` |
| `gh pr checks … --watch` (hand-rolled CI wait) | `mise run ship`/`land` already watch; one-shot read: `gh pr checks <n> --json` |
| autofix artifact recovery by hand | `mise run autofix-apply -- <run-id>` |
| `gh workflow run` / `gh run rerun` | `mise run gha-dispatch -- <wf>` / `mise run gha-rerun -- <id>` |
| `npx <tool>` | the mise-pinned binary directly |
| `chezmoi apply/update` on the Mac host | nothing — devcontainer-only |

Diagnostic/read-only commands (`docker ps`, `gh pr view`, `git status`,
single-test `pytest path::test` via uv) are NOT wrapped and stay direct.

## Enforcement layers (deep-research verified, 2026-07-07)

1. **PreToolUse hook (hard deny)** — `.claude/settings.json` wires every
   Bash call through `dotfiles-setup hook pretooluse`
   (`python/src/dotfiles_setup/hook_guard.py`): a matched one-off command
   is DENIED with the redirect reason fed back (JSON
   `permissionDecision: "deny"`; deterministic, applies even in
   bypassPermissions mode). The rules are tested in
   `tests/test_hook_guard.py`.
2. **ship/land `hook-selfcheck` gate** — `mise run ship` / `land` run
   `dotfiles-setup hook selfcheck`
   (`python/src/dotfiles_setup/hook_selfcheck.py`) as an always-run gate: it
   drives the WIRED PreToolUse guard end-to-end (settings.json wiring +
   `Bash` matcher, the real wrapper, `bash -n` on the scripts), so a hook
   regression fails a PR like lint/pytest. Tested in
   `tests/test_hook_selfcheck.py`.
3. **This rule + skills** — `pr-workflow` and `devcontainer-sync` skills
   name the canonical tasks; markdown alone is "relying on the LLM", so
   it is never the only layer.
4. **Self-learning loop (`mise run command-audit`)** —
   `python/src/dotfiles_setup/command_audit.py` scans this project's recent
   Claude Code transcript JSONL (native capture — no logging hook) and flags
   mutating one-off Bash commands the guard does NOT yet cover, so the layers
   above get refined over time. It is the *inverse* of Claude Code's
   `fewer-permission-prompts` skill (same transcript mine + command+subcommand
   grouping, opposite verdict). Review the report, then add a `mise run` task
   (+ a `hook_guard._RULES` redirect for a known-bad shape) for the top
   culprits. A rule-matching command is only an alarm (`bypass`) when it ran
   AFTER its rule's `since` date AND actually executed — see "Reading the
   report" below. Ongoing, not one-shot — a **`SessionEnd` hook** in
   `.claude/settings.json` runs it once per session (`-- --output
   .omc/command-audit.md`), so the report is always waiting rather than
   remember-to-run. `SessionEnd` and not `Stop`: it fires once per session at
   termination and *cannot block*, while `Stop` fires every turn and can block
   (exit 2 continues the turn) — a transcript scan belongs on neither the
   per-turn path nor a blocking one. It is also **local-only by nature** (it
   reads `~/.claude` transcripts), so it is a hook and never a GHA job — a CI
   runner has no transcripts. The report stays out of git via `.gitignore`.
5. **Contracts** — `workflow.mise-tasks-enforcement` (the deny guard),
   `workflow.hook-selfcheck-wiring` (the selfcheck gate), and
   `workflow.command-audit-wiring` (the self-learning loop) in suites.toml
   assert the whole chain exists (settings.json → wrapper → CLI → module →
   tests), so nothing silently drifts out.

The hook fails OPEN on its own errors (a crashed guard must not brick every
Bash call — the wrapper exits 0 when the Python>=3.14 interpreter is absent,
e.g. a cold Claude-web session). Hard one-off bans that must never fail open
belong in settings.json permission deny rules, not the hook.

> **Enforcement design note (2026-07-14, research-backed):** we deliberately
> do NOT re-inject a "use mise tasks" reminder every turn (UserPromptSubmit)
> or nudge after every command (PostToolUse). Anthropic's guidance routes
> static conventions to CLAUDE.md and enforcement to the PreToolUse hook,
> and the LLM-behavior evidence ranks a hard gate (zero decay) far above
> per-turn reminders (which decay, cost instruction budget, and sit in the
> lowest-trust context tier). See
> `.omc/research/research-20260714-hook-enforcement/report.md`. The improvement
> path is the self-learning loop (`mise run command-audit`, layer 4 above) that
> mines native transcripts for one-off-command culprits to refine these layers
> — not more per-turn hooks.

## Reading the command-audit report

Only **`bypass`** is an alarm: a command that matched a rule ALREADY LIVE
(`timestamp > rule.since`) and that really executed. The other rule-matching
classes are not:

- **`blocked`** — the guard denied it; it never ran. The guard working. Audit
  these for FALSE POSITIVES (see the known limitation below), not for evasion.
- **`pre_rule`** — it predates the rule that matches it. History.
- **`one_off`** — the refine-loop candidates, but known-noisy (#266): its top
  shapes are currently sanctioned work (plain git, ad-hoc scripts, the
  prescribed wait-loops). Read it with that discount until #266 lands.

Both distinctions are load-bearing, because a bare "matched a rule" verdict is
almost pure noise. Measured over 3,615 real commands (2026-07-14): **155**
matched a rule — **147** predated it, **3** were denials, and **0** were
bypasses. Nothing has ever evaded the guard. The transcript is what forces the
second axis: it records the Bash `tool_use` block whether or not the command
ran (a PreToolUse deny lands *after* the model emits it), so a denial and a
bypass are byte-identical until you pair the attempt to its result.

## Known limitation: prose content in compound commands

The guard matches the raw Bash string, so heredoc/quoted CONTENT that
embeds a denied command shape (e.g. a doc edit containing
`&& hk run pre-commit`) can be denied — and a deny cancels the ENTIRE
compound command, silently skipping its other parts (observed twice,
2026-07-07). Workaround: write scripts via the Write tool and run
`python3 <file>`; after ANY deny, re-check that the command's intended
side effects actually happened.

**This — not evasion — is the guard's live defect** (issue #265). The audit's
`blocked` bucket measures it: 2 of the 3 denials ever recorded were false
positives, both from a `|` INSIDE a quoted regex (`grep -iE
"…|devcontainer up|…"`) reading as a shell separator.

## Extending

New redirect = new `_RULES` entry in `hook_guard.py` + a test + a row in
the table above, same change. Give it a `since` date (the day it lands on
main) — the audit needs it to tell a real bypass from pre-rule history, and a
rule missing one classifies every match as history forever, darkening the
alarm. `since` dates the RULE, not its wording: never bump it on a reword.
Keep patterns narrow: a redirect that misfires on legitimate diagnostics
erodes trust in the guard.

## See also

- `.claude/rules/verify-before-advancing.md` — the gates the ship/land
  tasks encode.
- `.claude/rules/long-running-command-hangs.md` — why `mise run lint`.
- `.omc/research/research-20260707-gha-shipland-enforcement/report.md` —
  the evidence base (hooks deny; allow-lists live in permissions; hookify
  is advisory-grade).
