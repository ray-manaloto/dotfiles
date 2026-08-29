# fable-advisor — plugin/PR housekeeping plan validation (2026-08-29)

## Brief (prompt sent to the agent)

DECISION NEEDED: Which of the currently open/pending items in ray-manaloto/dotfiles should be actioned now, in what order, and which (if any) can run as parallel codex-implementer lanes without touching the same files? This session lost track of state across several sessions today due to `/login` interruptions, so we re-audited GitHub directly (not trusting session notes) before asking you.

Session config: fable-orchestrator implementation lane = codex, codex effort = xhigh. Codex lane diffs get cold review from codex-reviewer is WRONG per doctrine (same family) — codex diffs must get `grok-reviewer` as the cross-family cold review lane (grok CLI availability unconfirmed this session — if unavailable, fallback chain is: other CLI first (n/a, codex is the implementer), then Claude Opus subagent, announced).

CONFIRMED CANDIDATE ITEMS (verified live via `gh`, not inherited from session files):

1. **Issue #818** — "CLAUDE_CODE_OAUTH_TOKEN leaked into ambient shell despite fnox env=exec (stale process env, not a config bug)". State: OPEN. Its own body ends: *"Closing immediately — fully diagnosed, fixed (terminal restart), and now monitored. Filed for the paper trail... not as a pending action item."* The monitoring fix (a `fnox-exec-leak` doctor check) is already merged to main in PR #819, with its own test (`tests/test_doctor.py`) added in that same PR. No remaining code work — the issue is just not closed.

2. **PR #815** — "chore: refresh lockfiles" (bot-authored, branch `chore/lock-refresh`). CI is RED:
   ```
   assert config - locked == set(), (
   >       assert locked - config == set(), (
   E       AssertionError: stale mise.lock entries for removed tools: ['node']
   1 failed, 2484 passed, 6 skipped, 10 deselected in 52.00s
   ```
   `mise.toml` declares `tools.node = "24"` as a task-scoped pin on the `renovate-dryrun` task; `.claude/rules/mise-tasks-only.md` and session notes record that the `mise lock` family only ADD/UPDATE entries, never PRUNE ones for tools no longer declared. This PR is bot-owned — decide whether the fix should land on the bot's existing branch or a separate PR.

3. **Issue #787** — "secrets: the add-a-secret runbook has no step that sets `env = true`" — OPEN, most recently updated 2026-08-29. A prior session deferred it as a scope-switch, noting the blocking defect's real fix lives in a SIBLING repo (`macos-development-environment`), out of scope for dotfiles.

4. Two long-open BOT PRs never reviewed: **#779** (dependabot) and **#767** (renovate/all, ~2 weeks stale).

NOT in scope: issues #708–#772 (a separate ticket-generation epic).

WHAT TO DECIDE: for each item 1–4, proceed now / defer / skip, with reason; for code-change items, correctness-critical (codex-implementer) vs. architect trivial-edit; which items are safe to parallelize; confirm the codex/grok-reviewer pairing.

## Report (verbatim)

Verdict, per item:

| # | Item | Decision | Lane |
|---|---|---|---|
| 1 | Issue #818 | **Proceed now** — pure `gh issue close 818 --comment` citing merged #819; no code | Architect trivial-edit, no lane |
| 2 | PR #815 red CI | **Proceed now**, small | Codex lane (or architect — see below) |
| 3 | Issue #787 | **Defer** — real fix is in the sibling repo; a doc-only slice is not urgent and I could not read the body (no `gh` access here — read-only FS) | — |
| 4 | PRs #779/#767 | **Conditional** — I cannot see their CI status (no `gh`). If green: `mise run automerge -- <n>` each, zero lanes. If red/conflicted (#767 at 2 weeks stale likely is): close and let Renovate reopen fresh rather than hand-rebasing a bot branch | No lane either way |

On #815, I verified the root cause myself: **main's `mise.lock` contains no `node` entry** (grep: 0 hits) and root `[tools]` declares none — but `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:815` has `tools.node = "24"` as a **task-scoped** pin on the renovate-dryrun task (#251). The bot's whole-file refresh locked that task-scoped tool; `tests/test_lock_coverage.py:197-207` reads only top-level `[tools]`, so `locked - config == {'node'}`. Fix: hand-prune the `node` block from `mise.lock` **on the bot's `chore/lock-refresh` branch** (the #817-session precedent), push onto that branch, then `mise run automerge -- 815` — the PR author stays the bot, so provenance is `automerge`, not `ship`. This is small enough for the architect's trivial-edit exemption; if you lane it, it's one file (`mise.lock`, bot branch).

**The decisive risk:** this will recur on every future lock-refresh run unless the refresh task prunes task-scoped tools. File a follow-up issue in the same breath; do not expand #815's fix into the workflow.

Parallelism: moot — only one code change exists.

Review pairing: confirmed correct. Codex diffs get grok-reviewer; Opus subagent if grok CLI is absent (per your 2026-08-29c note it was). Never codex-reviewer — same family.

Order: 1 → 2 → 4 (status check) → stop.

## Outcome (what the architect actually did, for the record)

- #818: closed with the exact comment recommended.
- #815: NOT hand-patched as recommended — deeper investigation found the branch predated PRs #816/#817 by 5 commits, so it was stale in more ways than the one flagged; closed instead and the `Refresh lockfiles` workflow re-dispatched for a clean regen (ran to `success`, no drift found).
- #787: deferred, per the verdict.
- #779/#767: both confirmed red for reasons unrelated to their own diffs (base predates recent hk/lint config changes); both closed rather than patched.
- Filed **#820** for the underlying `test_root_lock_covers_host_config` scoping gap the advisor's root-cause analysis surfaced.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — every item in this brief.
