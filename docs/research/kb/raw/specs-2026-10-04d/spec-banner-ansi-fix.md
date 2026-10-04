# Spec: strip ANSI from the codex banner before session-id parsing (ratified by Ray, 2026-10-04)

## 1. Objective
Since codex 0.160.0, every `mise run sdlc-team` settlement fails with "spawn reconciliation: parent thread id not found in codex.log banner". The codex.log banner prints the key coloured, as `ESC[1msession id:ESC[0m <uuid>`. The parser at `python/src/dotfiles_setup/lane_result.py:216-219` compares the raw key against `"session id"`, so it misses.

Make the banner parse colour-insensitive.

## 2. Files
- `python/src/dotfiles_setup/lane_result.py`: the banner parser (around :190-220).
- `tests/` (the existing lane_result / sdlc_team banner tests; find them with `grep -rn "session id" tests/`).

## 3. Interfaces
- No public signature changes.
- Strip ANSI CSI sequences (`\x1b\[[0-9;]*[A-Za-z]`) from each banner line before the `partition(":")`. Strip them from the `--------` delimiter and banner-start detection too, if those compare raw text.

## 4. Constraints
- Branch `fix/codex-banner-ansi`, cut from origin/main in worktree `.claude/worktrees/codex-banner-ansi`. Never in the main checkout.
- Use no regex for anything beyond the ANSI strip. There are no inline lint suppressions.
- Commit mode `caller`: stage only. The coordinator runs the gates.

## 5. Verification
- **New test, real shape.** Use a fixture whose banner lines are byte-copied from the real 0.160.0 log: `sed -n '1,20p' .agent/sdlc-runs/0087b1820d1c4b6aa3b186c6436d8bab/codex.log` in the main checkout. It must contain the ESC bytes. Assert that the parsed session id equals `01a1068f-53a0-7540-a774-b8222ab83864`.
- **Control arm.** The existing plain-banner tests still pass.
- **Mutation arm.** Remove the ANSI strip; the new test must FAIL and the plain tests must still pass. Record the rc of both runs.
- **Run:** `uv run --project python pytest <the touched test files> -x -q -n 2`, with the rc captured to a file.

## 6. Commit
`fix(lane-result): strip ANSI from the codex banner before parsing the session id`. The body cites the run ids 0087b182 and 0ca4b234 and codex 0.160.0.

## 7. PREMISES
- **P1:** CONFIRMED. Both 0.160 logs give `grep -c '^session id: '` = 0 and `grep -c $'^\e\[1msession id:'` = 1. The older run `fef427ec` gives plain = 1, so the probe discriminates.
- **P2:** CONFIRMED. `lane_result.py:216-219` uses `key.strip().lower() == "session id"` on raw text (read in the main checkout).
- **P3:** ASSUMED. The colour is version-driven, not environment-driven. The fix strips either way, so P3 is non-blocking.
