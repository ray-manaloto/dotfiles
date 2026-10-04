# handoff-automation PR 1 — implementation round 3 (Revision C + round-2 LOWs)

Coordinator: a7139527. Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1`,
branch `feat/handoff-automation-pr1` at 18e35f9c. Work ONLY there.

## 1. Objective

Round 2 (18e35f9c) is implemented, and its Opus cold review is SHIP. Two things changed since then:

1. **Ray's D1a ruling (2026-10-04, AskUserQuestion via the handoff-automation lane): HYBRID.**
   Implement **"Revision C"**, the LAST section of
   `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.agent/plans/spec-delta-handoff-pr1-round2-2026-10-03.md`
   (heading "## Revision C — Ray's D1a ruling"). It supersedes Fix 1's "two roots" split wherever
   they differ. In summary:
   - all four hooks pass `DOTFILES_PROJECT_ROOT = session.root() ?? CLAUDE_PROJECT_DIR`;
   - the two state hooks (session-start, coordinator-handoff) run their CLI from the plugin tree
     and always pass an explicit main-checkout `--state-dir`;
   - install-doctor and plugin-health keep cwd = the live project;
   - sessionProject goes back into all four parity sets;
   - add the Revision C harness assertions and the real-CLI pass arm;
   - reword the main.py docstring "any other setter is a bug", per Revision C's licensed-dissent fix
     (spec §3j `gate_env()`).

   Read the whole delta for context. Revision C is binding.
2. **The round-2 cold review's 8 LOWs** (R2-1…R2-8):
   `docs/research/kb/reports/agents/cold-review-handoff-pr1-round2-18e35f9c.md` (untracked, in
   the worktree). Fix each one in this unit:
   - R2-1, R2-5, R2-6: add the missing branch tests;
   - R2-2, R2-3, R2-4, R2-7: align the claims and docs (TTL, F9);
   - R2-8: rename the overclaiming test.

   If one cannot be fixed without contradicting Revision C, say so and list it for a ticket.

## 2. Files

The files Revision C names, plus the files the R2-n findings cite. Nothing outside the PR-1 file
set already touched by 21011fb5/18e35f9c unless Revision C names it. Do not edit the review report
or the spec delta.

## 3. Interfaces

As specified in Revision C. No new interfaces beyond it.

## 4. Constraints

- HOST SLOT: a heavy run may own the host. Run ONLY targeted pytest on the PR-1 test files you
  touch, plus ruff check / ruff format --check / ty on touched python files.
- Do NOT run the full suite, mise run lint/verify, ship/land or container ops.
- No inline suppressions, no `--no-verify`. Never print credential values.
- If Revision C contradicts the code or itself, STOP and report; do not guess.

## 5. Verification

Report:
- the targeted pytest rc and counts;
- the ruff/ty rc;
- a mutation table: each Revision C rule (state-hook `--state-dir`, the env on all four hooks,
  sessionProject parity, stable state/cwd across `s.move()`) → which test fails when it is removed;
- the R2-n closure list.

## 6. Commit

ONE new commit on top of 18e35f9c:
`fix(handoff): PR 1 round 3 — D1a hybrid (Revision C) + round-2 LOWs`. The body cites Ray's
ruling and lists the R2-n closures. Do not push.

## 7. PREMISES

- P1: Revision C exists at the path above and is the last section.
- P2: 18e35f9c is the branch head, and the round-2 report lists R2-1…R2-8 with file:line.
- P3: the state hooks are session-start and coordinator-handoff; the inspection hooks are
  install-doctor and plugin-health (per Revision C's rule table).

## 6a. Commit-body line (required)
Include verbatim: "Round 3 implements Ray's own D1a HYBRID ruling (2026-10-04); it is not review residue, so it does not count against the two-respec-rounds cap."

## 8. BINDING CORRECTIONS (r3.1, after premise verification; these override the sections above)

Premise report: `docs/research/kb/reports/agents/premise-verifier-handoff-pr1-round3.md` (worktree).

- **(a) `gate_env()`.** `verify_clone.gate_env()` is NOT built yet; it is planned in spec §3j step 5
  (`docs/specs/session-handoff-automation.md:301`). Word the main.py docstring (`main.py:3229-3234`)
  as "and, once built, by `verify_clone.gate_env()` (spec §3j)". Its absence is NOT a STOP
  condition.
- **(b) State hooks when `sessionProject` is undefined** (`root()` throws and `CLAUDE_PROJECT_DIR` is
  unset):
  - omit `DOTFILES_PROJECT_ROOT`;
  - never return `n/a (session project unavailable)` (the existing `n/a (CLI unavailable)`/`n/a (CLI skew)` returns stay) and NEVER gate `decide`/`release` (delta Fix 2 at `:75`; Revision C `:209`);
  - add the matching harness arm (around `harness.ts:148-153`).

  install-doctor keeps its n/a behaviour.
- **(c) R2-7.** Reword the toast to exactly `(PIN; advisory in PR 1, PR 2 may enforce)`. This keeps
  the `PIN;` substring that `harness.ts:218` asserts, and it supersedes Fix 3's literal.
- **(d) R2-8.** First rewrite `test_session_start_real_cli_move`
  (`test_cli_resolver_parity.py:226-261`) to Revision C's shape: env A, then env w, with the same
  `--state-dir`, expecting rc 0. Then rename it to `test_session_start_state_dir_overrides_live_root`.
- **(e) Mirrors.** Add `.agents/skills/session-start/SKILL.md` and
  `.agents/skills/coordinator-handoff/SKILL.md` to §2, edited in lockstep with their `.claude`
  twins. R2-2's anchor is `coordinator-handoff/SKILL.md:18`.
- **(f) Arm counts and title.** Update `BASE_ARMS`/`PIN_ARMS`/`EXTRA_ARMS`
  (`test_cli_resolver_parity.py:20-22`) for the new arms. The §6 title is THIS commit's title;
  Revision C's `:217` title is the PR title.
