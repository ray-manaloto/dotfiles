# Spec — codex-takeover Phase C: handover pack, per-session issues, always-ready rule (2026-10-05 ~11:50 CDT)

Claude's weekly budget is at 95%. **Assume this is the LAST Claude-dispatched run.** Ray's rulings
(verbatim) are in `docs/specs/codex-takeover-2026-10-05.md` § "Round 6". Read that file's
"Round 6" and "Lane state" sections first. Umbrella #1721.

## 1. Objective

A codex agent with NO Claude available must be able to answer three questions, then act:
what are we doing, what is done, and what is pending (per lane). Claude must later be able to
take back over by the same protocol. In Ray's words: "claude should always be ready to handoff
to codex and vice versa".

## 2. Work items (in order)

**C1. Make the B1+B2a commit pass, then commit.**

1. The pre-commit hook refused the commit. `py_ty` reported 11 diagnostics; the full log is at
   `.agent/logs/b1b2a-precommit-fail.log`. Examples:
   - `tests.test_session_ledger` cross-test import unresolvable;
   - `Path | None` `.mkdir`/`/` misuse.
2. Fix the CODE. No suppressions, no `--no-verify`.
3. The index is already staged with exactly the intended paths (`git diff --cached --name-only`).
   Re-stage only the files you fix.
4. Commit with the prepared message saved at `.agent/plans/commit-msg-b1b2a.txt`.
5. Record the literal SHA printed by the commit.

**C2. Tracked START-HERE pack: `docs/handoffs/codex-takeover-START-HERE.md`.** Contents:

- Who is who:
  - the current coordinator name: `dotfiles-20261005T111320.040016000-05.coordinator`;
  - this lane, `dotfiles-20261005T064930-05.codex-takeover`, with its worktree, branch and
    absolute paths.
- Read order for codex: `AGENTS.md` → `docs/agents/codex-policy-index.md` →
  `docs/agents/session-orchestration.md` → this file → `task_plan.md` (main checkout) →
  `.agent/plans/main-checkout-ship-queue.md` → `.agent/plans/handoff-inbox/`.
- A per-lane table generated from the real `mise run lane-cards -- --json` output (both repos).
  - Include every working/blocked/stopped session: name, session id, cwd/worktree, branch,
    state, its issue #, done and pending if known, and open questions.
  - Save the raw JSON beside the doc as `docs/handoffs/lane-snapshot-2026-10-05.json`.
  - Print presence only; never secrets.
- codex-takeover status:
  - DONE: grilling, research, B1, B2a.
  - PENDING: SLOT position 3 (full gates → codex review lens → ship via the coordinator), then
    B2b (W4 takeover-check + launcher default-OFF), per `docs/specs/codex-takeover-phaseB-design.md` §W4.
- **Codex priorities after codex-takeover ships, per Ray: (1) docker images and devcontainers,
  (2) project repo dependencies, (3) graphify fork integration.** Point to their existing issues
  or plan phases, found via `gh issue list -R ray-manaloto/dotfiles` and `task_plan.md`. The other
  meta/orchestration lanes stay READ-ONLY (keep their cards current; do not resume them).
- How codex becomes coordinator: `mise run handoff-inbox -- coordinator-claim --name
  dotfiles-<ts>.coordinator --supersedes <current newest>`. This needs B2a on main, OR running
  from this worktree, where it is already committed. Then the queue/SLOT rules apply.
- The hand-back protocol (C4).

**C3. Always-ready rule.**

- Add ONE line to `AGENTS.md`, keeping it ≤ 12,000 chars: both agents keep
  `docs/handoffs/codex-takeover-START-HERE.md` and the lane cards current at every milestone, so
  either can take over at any time (see session-orchestration.md § Handover).
- Add the matching "Handover (both directions)" section to `docs/agents/session-orchestration.md`.

**C4. Hand-back by probe. This is Ray's ruling, accepting its conflict with the AUTO-LAUNCH OFF
/ #1681 ruling for THIS case.**

1. At each milestone, and at most every 30 min, codex runs one bounded cheap probe:
   `claude -p "reply OK"` under a deadline. Record the rc.
2. On success, codex:
   - updates START-HERE and the cards;
   - runs `coordinator-release`;
   - starts ONE Claude coordinator via the existing coordinator-handoff successor launch path
     (`python/src/dotfiles_setup/coordinator_handoff.py`; reuse it, do not hand-roll it);
   - appends a hand-back record to the main checkout inbox through
     `mise run handoff-inbox -- append --lane codex-takeover`.
3. One launch at most: check for an existing live Claude coordinator first.
4. Document the procedure in session-orchestration.md § Handover. Implement ONLY if it is a thin
   reuse of existing code. Otherwise document it as the manual codex runbook step.

**C5. Per-session issues + plan tasks.**

1. Run `mise run lane-cards -- --issue-plan`.
2. For every `create` intention, file the issue with
   `gh issue create -R ray-manaloto/<repo> --title … --body …`. The body links umbrella
   `ray-manaloto/dotfiles#1721` and holds the card summary.
3. Reuse intentions keep their existing issue.
4. Record every issue number in the lane-snapshot JSON and the START-HERE table.
5. Write a plan delta proposing one `task_plan.md` task per session/role-chain with its issue
   link: `.agent/plans/task_plan-delta-codex-takeover-sessions-<stamp>.md`.
6. Append its path to the coordinator inbox via
   `mise run handoff-inbox -- append --lane codex-takeover`. The coordinator applies it; do NOT
   edit `task_plan.md`.

**C6. Copy START-HERE into the main checkout inbox**
(`mise run handoff-inbox -- append --lane CODEX-START-HERE --title "Codex: start here"`). The
body is a pointer to the absolute tracked path plus the 10-line summary. Then append
`B2a SETTLED <C1 commit SHA>; START-HERE ready` to the `codex-takeover` inbox lane for the
coordinator.

## 3. Files (allowlist)

- C1 fixes: `python/src/dotfiles_setup/**`, `tests/**` — only the files `py_ty` flags.
- `docs/handoffs/codex-takeover-START-HERE.md` (new), `docs/handoffs/lane-snapshot-2026-10-05.json` (new)
- `AGENTS.md`, `docs/agents/session-orchestration.md`
- `python/src/dotfiles_setup/coordinator_handoff.py`, `tests/test_coordinator_handoff.py` — only for the C4 thin reuse
- `docs/research/kb/reports/agents/codex-takeover-phaseC-2026-10-05.md` (new; the run report, written incrementally)

## 4. Constraints

- Never `--no-verify`, `--ephemeral`, inline suppressions, or `gh pr` commands.
- No push: the coordinator ships.
- No user-level file edits.
- `task_plan.md` goes through the delta only.
- Gates: the pre-commit hook IS the commit gate. Also run targeted pytest for touched tests, and
  `mise run lint-docs` (AGENTS.md changes).
- Full lint, pytest and verify wait for the coordinator's SLOT GO; record them as NOT_RUN.
- Print no secret values.

## 5. Verification

- C1: commit rc 0 and its SHA.
- `mise run lint-docs` rc 0.
- AGENTS.md ≤ 12,000 chars.
- Every working/blocked/stopped session in the snapshot has an issue #.
- The issue count is consistent with `--issue-plan` (created plus reused).
- The inbox appends returned rc 0.

## 6. Commit

`lane`, as two commits:

1. C1, using the prepared message.
2. `docs(takeover): codex START-HERE handover pack + always-ready rule + session issues (#1721)`,
   with the attribution trailer lines from the prepared message.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | py_ty 11 diagnostics block the commit | `.agent/logs/b1b2a-precommit-fail.log:267-452` |
| 2 | I | `lane-cards --json`/`--issue-plan` exist, rc 2 = partial | `docs/research/kb/reports/agents/codex-takeover-phaseB1-validation-2026-10-05.md` |
| 3 | I | `coordinator-claim --name --supersedes`, `coordinator-release` | `docs/research/kb/reports/agents/codex-takeover-phaseB2a-validation-2026-10-05.md:77` |
| 4 | L | SLOT position 3 after r2 ship and #1673 ship; GO conditional on "B2a SETTLED <sha>" | coordinator message, recorded in the parent spec's Lane state |
| 5 | A | `claude -p` fails fast (not hangs) when the subscription is exhausted — bound it with a deadline regardless | — |
