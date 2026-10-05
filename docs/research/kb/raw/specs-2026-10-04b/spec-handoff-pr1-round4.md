# Spec: handoff PR1 round 4 — fix cold-review F1 (and F2, F3, F5) on 17a97975

Ratified by the architect, coordinator 633cd8, 2026-10-04.

Input: the cold review `docs/research/kb/reports/agents/cold-review-handoff-pr1-round3-17a97975.md`, untracked in the worktree. Its verdict was DO NOT SHIP.
Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-pr1`, at HEAD 17a97975.

## 1. Objective

Make every test that loads the changed hook sources pass, with each behaviour still pinned:

- **F1 (blocking).** The install-doctor hook harness arm at `tests/fixtures/install_doctor_hook/harness.ts:345-363` expects a DENY on an Edit of `doctor.toml` when both session roots are lost. Under r3.1(b) and R2-5, install-doctor instead keeps its n/a behaviour: the edit is ALLOWED, no CLI runs, and the status is a visible n/a. Rewrite that arm to assert exactly that. Do NOT change `register.ts` behaviour to satisfy the old arm. The resolver arm at `tests/fixtures/cli_resolver/harness.ts:171-174` stays.
- **F2.** In session-start (`.claude/skills/session-start/hooks/register.ts:321-335`), a prompt-time branch re-read that changes the branch must REDRAW the status line. Today the line keeps its stale `· main checkout on <old branch>` text, for example after a flip back to `main`. coordinator-handoff already redraws, so mirror its pattern. Add a harness arm with a branch flip and NO rename in the same prompt, which must show the redrawn status. The existing arm at `tests/fixtures/session_start_hook/harness.ts:606-622` passes only because a rename triggers the redraw.
- **F3.** Correct the `main.py:3231-3234` docstring. session-start's default state directory, used when `--state-dir` is omitted, DOES follow `DOTFILES_PROJECT_ROOT` (`session_start.py:398-404`, `:413`). Keep the "once built, by `verify_clone.gate_env()` (spec §3j)" wording.
- **F5.** Correct the `--probe` help at `coordinator_handoff.py:1195-1198` to match the real behaviour at `:410-413`: an unconfirmed (rejected) probe is released and re-fires at the next measurement.
- **F4: no change.** The coordinator tickets it.

## 2. Files

- `tests/fixtures/install_doctor_hook/harness.ts`
- `.claude/skills/session-start/hooks/register.ts`, and its `.agents/skills/session-start/` mirror if one exists. The `skills_mirror_parity` gate must stay green; regenerate the mirror with `uv run --project python dotfiles-setup skills-mirror`, never by hand.
- `tests/fixtures/session_start_hook/harness.ts`
- `python/src/dotfiles_setup/main.py`
- `python/src/dotfiles_setup/coordinator_handoff.py`
- Plus any test that pins the help text.

## 3. Interfaces

No CLI or schema change.

## 4. Constraints

- The host test slot is shared, so run targeted tests only:
  - EVERY test file that loads a changed source;
  - at minimum `tests/test_install_doctor_hook.py`, `tests/test_cli_resolver_parity.py`, `tests/test_session_start_hook.py`, `tests/test_coordinator_handoff_hook.py` and `tests/test_coordinator_handoff.py`;
  - plus any file that a `grep -rl` over `tests/` finds referencing a changed file name.

  Run them with `-n 0`.
- Also run ruff and `ty check --project python` on the changed Python files, and `uv run --project python dotfiles-setup skills-mirror --check`.
- Do NOT run the full suite, lint, verify, ship or push.
- No suppressions.
- Never write in a main checkout.

## 5. Verification

Report:

- the rc and counts per command above, including the grep that selected the test list;
- a mutation table in which each of these must go red:
  - (a) restore the old deny expectation in the install-doctor arm → `test_install_doctor_hook.py` fails;
  - (b) remove the F2 redraw → the new session-start arm fails;
  - (c) restore the round-2 guard removal → the resolver arm fails.

## 6. Commit

ONE new commit on 17a97975: `fix(handoff): PR 1 round 4 — install-doctor harness parity + status redraw (cold-review F1/F2/F3/F5)`.

- Stage files by explicit path.
- No amend, no push.

## 7. PREMISES

| # | Premise | Source |
|---|---|---|
| P1 | The failing arm is the install-doctor harness at `:345-363`, which asserts deny at `:203`. Every other arm passes. | Cold review, verified by its replacement probe |
| P2 | `21011fb5` passed and `18e35f9c` introduced the guard at `register.ts:136-139`. | Cold review, three-commit bisect |
| P3 | Spec r3.1(b): install-doctor keeps n/a. | `spec-handoff-pr1-round3.md` §8(b) |
| P4 | coordinator-handoff redraws its status on a branch flip. | Cold review F2 |
