# Spec r2 (self-contained): codex banner ANSI fix — r1 sections + r2 deltas

## Part A — r1 spec (verbatim, still in force except where Part B overrides)

### Spec: strip ANSI from the codex banner before session-id parsing (ratified by Ray, 2026-10-04)

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

## Part B — r2 deltas (override Part A)


Same worktree, branch and caller mode as r1 (`/Users/rmanaloto/.claude/jobs/e67105a8/tmp/spec-banner-ansi-fix.md`). Keep everything currently staged and apply ONLY these changes:

1. **HIGH: fixture EOF.** `tests/fixtures/codex-0.160.0-banner.txt` ends in `\n\n`, which fails the `newlines` hk step.
   - Make it end in exactly one `\n`, so it is lines 1-19 of the source log.
   - Prove it: `hk util end-of-file-fixer tests/fixtures/codex-0.160.0-banner.txt`, then `git diff --exit-code` on the fixture, must show rc 0 and no change.
   - Re-verify byte-equality to `sed -n '1,19p'` of the source log with `cmp`.
   - Update every place that says "20 lines" or names the SHA.
2. **MEDIUM: the root cause is environmental, not the codex version.**
   - Cause: `claude --bg` sessions export `FORCE_COLOR=3`, and codex's `--color auto` honours it. The codex colour code is identical in 0.158 and 0.160.
   - Rename the fixture to `tests/fixtures/codex-banner-ansi.txt` and the test identifiers to say "ansi banner", not "0.160".
   - Fix the report wording (`…banner-ansi.md:141` and wherever else it is claimed).
3. **MEDIUM: native fix.** Add `"--color", "never",` to the `sdlc_team.py` argv (around :811-824, before `-C`), and pin it in `tests/test_sdlc_team.py` where the argv is asserted.
   - Mutation arm: drop the flag, and the pin must fail.
   - Keep the parser strip as a backstop and say so in a short comment.
   - Do NOT touch `codex_lane.py`; the coordinator files that as an issue.
   - Verify the flag with `mise exec -- codex exec --help | grep -n -- --color` and record the output.
4. **LOW:** evidence cited only at `/tmp`, `.agent/state` or `~/.codex` paths gets copied under `docs/research/kb/raw/banner-ansi/` (byte-verbatim, and redact nothing that is secret-like; there should be none) and re-cited there. If there is too much, drop the citation and state the fact with its probe command instead.

Run the targeted pytest (`tests/test_lane_result.py` and `tests/test_sdlc_team.py`, `-n 2`) plus both mutation arms, each with a file-captured rc. Stage everything; do NOT commit. Report the rcs and `git diff --cached --stat`. TIMEOUT: 1800.

## Part C: §2 FILES allowlist for r2 (this replaces Part A §2)

- `python/src/dotfiles_setup/lane_result.py`: r1 change, kept as is.
- `tests/test_lane_result.py`: rename test ids only (item 2).
- `tests/fixtures/codex-0.160.0-banner.txt`: rename it to `tests/fixtures/codex-banner-ansi.txt` with `git mv`, and fix its EOF (items 1 and 2).
- `python/src/dotfiles_setup/sdlc_team.py`: add `--color never` to the argv (item 3).
- `tests/test_sdlc_team.py`: pin the flag (item 3).
- `docs/research/kb/reports/agents/codex-sol-implementer-banner-ansi.md`: your report, with an r2 section.
- `docs/research/kb/raw/banner-ansi/*`: new; evidence copies (item 4).
- Out of scope, do not touch:
  - `python/src/dotfiles_setup/codex_lane.py` (issue #1660);
  - `docs/research/kb/reports/agents/cold-review-banner-ansi-r1.md`.

## Part D: PREMISES for r2 (coordinator, probed 2026-10-04)

- **R2-P1: CONFIRMED.** The fixture ends in `\n\n`.
  - Probe: `od -c` of the last bytes shows `.  \n  \n`.
  - The cold reviewer ran `hk util end-of-file-fixer` on a byte copy and got rc 1; a one-newline copy gave rc 0.
- **R2-P2: CONFIRMED.** `codex exec --help` (codex-cli 0.160.0 via `mise exec --`) lists `--color <COLOR>` at help line 96 ("Specifies color settings for use in the output").
- **R2-P3: CONFIRMED.** This `claude --bg` session has `FORCE_COLOR=3` (probe: `[ -n "$FORCE_COLOR" ]`). The cold review reports codex colour logic and the `supports-color` 3.0.2 pin are identical in rust-v0.158.0 and rust-v0.160.0. That comparison is ASSUMED here (inherited from the review, not re-derived).
- **R2-P4: CONFIRMED.** The argv tuple is in `sdlc_team.py` at ~:811-824 of the worktree (`model_reasoning_effort` is at :814). The tests assert the argv prefix at `tests/test_sdlc_team.py:408-409`.
- **R2-P5: CONFIRMED.** `codex_lane.py:389` has the same launch pattern. Out of scope, tracked as #1660.
