# Spec — fix round 6: close the f2f163a9 cold-review LOWs (freeze gate)

Review: `docs/research/kb/reports/agents/cold-reviewer-llvm-fix5-f2f163a9-2026-10-04.md` (0 HIGH/MEDIUM, 8 LOW).
Parent: `docs/specs/llvm-major-detect-bump-fix5.md`. Lane llvm23. Line numbers are the review's, at f2f163a9; re-read
them.

> **F1 RULED (Ray, 2026-10-04, direct AskUserQuestion): "Not frozen: require head".** This amends R1's recorded
> "apt build is that tag OR the branch head" to "apt has built the current branch head" (head may be the tag or tag+1).

## Architect decisions on the review

- **F1 (resolves an ambiguity in the ruling):** Ray's ruling text — "release/M.x head equals its latest llvmorg-M tag AND
  the live -M suite build is that tag (or tag+1)" — exists to stop the churn in which apt.llvm.org rebuilds a moving
  branch. The state `ahead_of_tag == 1 && apt_build == tag` means apt has NOT yet built the current head and WILL
  rebuild: exactly the churn. Condition (b) therefore becomes **`apt_build == branch_head[:12]`** (apt has built the
  current head). Condition (a) stays `ahead_of_tag <= 1`, so head = tag or tag+1, which is the ruling's "tag (or
  tag+1)". Live: 22 (head == tag == build) stays frozen; 23 stays not frozen.
- **F7: no action.** This PR already changes `.devcontainer/mise-system.toml` bytes in earlier commits (the fix2 IWYU
  pin, the fix1/fix3 comments), so the base-hash rebuild is paid regardless.
- **F2, F3, F4, F5, F6, F8 and the stale docstring:** fix all of them, as below.

## Files

`python/src/dotfiles_setup/llvm_major.py`, `tests/test_llvm_major.py`.

## Required behaviour

- **F1:** `freeze_state` condition (b) = `apt_build == branch_head[:12]`. Update the test table:
  - (ahead 1, build == tag ≠ head) → NOT frozen (the F1 state);
  - (ahead 1, build == head) → frozen;
  - (ahead 0, build == head == tag) → frozen.
- **F3:** `_freeze_summary` derives its "matches/≠" text from the `Freeze` result fields, not from a second copy of the
  membership test. Add tests asserting both summary variants. They must fail if (b) changes without the summary.
- **F2:** in the `_bump`/`plan_bump` path, after the target is selected from freeze evidence, the freshly read clang-T
  version (`_index_version`) must embed `freeze_evidence[T].apt_build`. Otherwise RAISE ("apt rebuilt -T since
  detection; re-run"). Add a test.
- **F4:** restore the IWYU explanation in the held reason, alongside the freeze summary. Format: `<M> GA+served, held:
  IWYU, freeze; IWYU: <the previous explanation>; freeze: <summary>`. Restore the `for {codename}` wording in the two
  non-held strings (parent b1224700 :408, :428). Keep the `"<M> GA+served, held: "` prefix and the gate order.
- **F5:** add tests for:
  - `_commit_sha` rejecting a non-40-hex SHA (must RAISE, never "not frozen");
  - a naive `now` raising;
  - "no GA tag for the major" raising;
  - `ahead_by` negative or non-int raising;
  - the clang-M count ≠ 1 raising.
  Each must fail when its guard is deleted.
- **F6:** the gh fake used by the `gh api --include` tests returns a realistic header block (an `HTTP/2.0 200 OK` line
  plus ≥2 header lines, `\r\n` or `\n` as the real gh emits; check `default_gh` and use the separator it actually
  splits on), so a regression that splits on the first newline fails a test.
- **F8:**
  - The clang-count error names `binary-amd64/Packages.gz` of the suite, not "Release".
  - The summary says `suite published <date>` instead of `built <date>`, and the Release `Date` is labelled as such.
  - Fix the `bump_main` docstring (:1138): a held run (IWYU or freeze) changes no files.

## Constraints

No pin, `_.path`, Dockerfile, Renovate, workflow, lockfile or `mise-system.toml` change. Zero inline suppressions;
ruff, ruff format and ty clean; `llvm-parity` rc 0. The ONLY test command: `uv run --project python pytest
tests/test_llvm_major.py -x -q -n 0`.

## Verification

1. That pytest command → rc 0, and every new arm shown failing against f2f163a9 (or by a sharp mutation).
2. Live: `mise run llvm-detect -- --json` → rc 4, reason contains `held: IWYU, freeze`, frozen {23: false}. A direct
   live `freeze_state(22, …)` → frozen True.
3. ruff, ruff format, ty, `mise run llvm-parity` → rc 0.

## Commit

`lane`: ONE commit, `fix(llvm): …`, with the dispatch's attribution lines. Never push.

## PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | condition (b) = `build in {tag_commit[:12], head[:12]}` | `llvm_major.py:444` (review F1) |
| 2 | L | `_freeze_summary` recomputes (b) | `llvm_major.py:452-456` (review F3) |
| 3 | L | `plan_bump` pins a fresh `_index_version` without re-checking the freeze build | `llvm_major.py:1101,1121,959` (review F2) |
| 4 | L | the held reason dropped the IWYU explanation; the non-held strings dropped `for {codename}` | `llvm_major.py:594,616-623` vs b1224700 :408,:420-422,:428 (review F4) |
| 5 | L | untested guards at :357, :390, :424, :427, :438 | review F5 |
| 6 | L | the gh fakes contain no header lines; split is `partition(b"\n\n")` | `tests/test_llvm_major.py:217-220,437`; `llvm_major.py:187-191` (review F6) |
| 7 | E | live: 22 head == tag == build `ca7933e47d3a`; 23 ahead 27, build `67f4a076a097` | architect probe 2026-10-04 (fix5 spec premises 1-2) |
