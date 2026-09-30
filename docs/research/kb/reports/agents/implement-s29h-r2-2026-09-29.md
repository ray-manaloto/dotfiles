# Implement S29-H round 2 (FINAL) — `docs/specs/s29h-r2-review-fixes.md`

- **Implementer:** s29h-implementer (Claude Opus, the stated fallback for `codex-sol-implementer`; codex is
  usage-limited until 2026-10-03).
- **Branch / base:** `feat/s29h-machine-checked-handoff` at HEAD `744c3b92`; tracked tree clean at start. The only
  untracked paths were the coordinator's `cold-review-744c3b92-2026-09-29.md` and `s29h-r2-review-fixes.md`.
- **Status:** COMPLETE. Uncommitted (COMMIT: caller). Gates lint/pytest/verify are rc=0/0/0, all 8 mutations went red and were restored, and live arms 1-4 plus their controls ran as specified.

## Progress log

- Pre-change byte copies of the four allowlisted files were saved to scratchpad `r2-orig/`.
- F1-F5 implemented in `handoff_check.py` / `session_state.py`; tests updated and added. ruff check, ruff format
  --check and ty are clean on all four files, and the three S29-H test files pass (213 passed, rc=0).
- **Licensed dissent 1 (F1 `now`):** the spec asks for `gather` to set `generated_at` "from an injectable `now`".
  As a seventh parameter (repo_root + 5 keywords + now), that trips ruff PLR0913 (max-args 5), and inline
  suppressions are banned. So the injection point is the call-time module-attribute seam this repo already uses for
  `pr_facts.run_gh`: `session_state.utc_now()`. `gather` reads it once, for both the stamp and the default window.
  Tests pin it with `monkeypatch.setattr(session_state, "utc_now", …)`. Round 1 made the same trade for
  `CLAIMS_DEADLINE_S`.
- **Licensed dissent 2 (F5, library side):** the spec says `exclude`'s basename "must match `_HANDOFF_RE`" but does
  not say what `newest_handoff` does when it does not. It now raises `ValueError`, because silently excluding
  nothing is exactly the F5 defect. The CLI validates first (rc=2), so the raise is unreachable from `session-state`.
  I also added a public `handoff_check.handoff_key(path)`, so `session_state` does not reach into the private
  `_HANDOFF_RE` (ruff SLF001).
- **Tests updated rather than deleted:**
  - The `render`/`check_with_claims` tests now use `ClaimTally`.
  - `"owner/repo pr #7 landed"` moved from the foreign-qualifier test to the "still read as dotfiles" test (F4 by
    design).
  - `owner/repo#12` moved to a glued-number test. It is excluded by `\w`, not `/`, which is F6's point.
  - `test_main_since_wins_over_for` now passes `--for session-2026-09-30.md` instead of `x.md`, which F5 rejects
    with rc=2. The `--since`-wins assertion is unchanged.

## Gates (after the F1-F5 edits, before live arms)

| gate | rc | evidence |
|---|---|---|
| `mise run gate -- run lint` | 0 | `{"gate":"lint","status":"passed","returncode":0,…}` |
| `mise run gate -- run pytest` | 0 | `4286 passed, 11 deselected in 313.69s` |
| `mise run gate -- run verify` | 0 | `166 passed, 0 failed, 4 skipped` |

## F6 mutation arms

Harness: `$SCRATCH/mutate.py`. Each mutation asserts its site count is exactly 1, runs the named test files, and then restores the file by byte copy from `r2-new/` (`shutil.copyfile`, then a `filecmp` deep compare). After all eight, `cmp` shows both modules byte-identical to `r2-new/`.

```text
M10-slash-lookbehind: pytest rc=1 restored_byte_identical=True ['2 failed, 120 passed in 12.68s']
    FAILED tests/test_handoff_check.py::test_a_slash_before_the_hash_is_not_a_reference
    FAILED tests/test_handoff_check.py::test_the_second_number_of_a_slash_list_is_not_a_claim
script rc=0
F3-drop-glued-terminator: pytest rc=1 restored_byte_identical=True ['2 failed, 120 passed in 9.92s']
    FAILED tests/test_handoff_check.py::test_a_glued_foreign_number_ends_the_previous_window[- #1454 MERGED; KB#814 OPEN]
    FAILED tests/test_handoff_check.py::test_a_glued_foreign_number_ends_the_previous_window[- #1454 MERGED; owner/repo#12 OPEN]
script rc=0
F4-restore-slash-qualifier: pytest rc=1 restored_byte_identical=True ['2 failed, 120 passed in 9.99s']
    FAILED tests/test_handoff_check.py::test_an_unrecognised_repo_name_is_still_read_as_dotfiles[owner/repo pr #7 landed-expected1]
    FAILED tests/test_handoff_check.py::test_a_slash_token_before_a_reference_is_not_a_qualifier
script rc=0
F2-drop-skip-record: pytest rc=1 restored_byte_identical=True ['2 failed, 120 passed in 10.01s']
    FAILED tests/test_handoff_check.py::test_a_pr_only_word_on_an_issue_is_skipped_counted_and_listed
    FAILED tests/test_handoff_check.py::test_main_lists_skipped_claims_and_keeps_rc_zero
script rc=0
F5-exclude-nothing: pytest rc=1 restored_byte_identical=True ['7 failed, 163 passed in 71.64s (0:01:11)']
    FAILED tests/test_handoff_check.py::test_newest_handoff_can_exclude_the_one_being_written
    FAILED tests/test_handoff_check.py::test_newest_handoff_excludes_by_date_and_letter_not_path[session-2026-09-29-c.md]
    FAILED tests/test_handoff_check.py::test_newest_handoff_excludes_by_date_and_letter_not_path[.agent/plans/session-2026-09-29C.md]
    FAILED tests/test_handoff_check.py::test_newest_handoff_excludes_by_date_and_letter_not_path[/elsewhere/session-2026-09-29c.md]
    FAILED tests/test_session_state.py::test_default_since_excludes_the_handoff_being_written
    FAILED tests/test_session_state.py::test_cli_dispatch_forwards_for - Assertio...
    FAILED tests/test_session_state.py::test_main_for_excludes_the_handoff_by_date_and_letter
script rc=0
F5-drop-cli-check: pytest rc=1 restored_byte_identical=True ['1 failed, 47 passed in 55.33s']
    FAILED tests/test_session_state.py::test_main_rejects_a_for_that_is_not_a_handoff_name
script rc=0
F1-ignore-stamp: pytest rc=1 restored_byte_identical=True ['3 failed, 45 passed in 54.63s']
    FAILED tests/test_session_state.py::test_default_since_prefers_the_generated_stamp_over_a_later_mtime
    FAILED tests/test_session_state.py::test_default_since_takes_the_last_parsable_stamp
    FAILED tests/test_session_state.py::test_a_pasted_state_block_starts_the_next_window
script rc=0
F1-drop-render-line: pytest rc=1 restored_byte_identical=True ['2 failed, 46 passed in 54.97s']
    FAILED tests/test_session_state.py::test_render_stamps_the_generation_time_right_after_the_branch
    FAILED tests/test_session_state.py::test_a_pasted_state_block_starts_the_next_window
script rc=0
```

## Live arms (§5)

**Arm 1:** `mise run handoff-check -- .agent/plans/session-2026-09-29b.md` gives rc=0. There are no skipped claims, so
no info lines are printed.

```text
handoff-check: OK — .agent/plans/session-2026-09-29b.md citations resolve; 19 PR claim(s) match GitHub
rc=0
```

*Control:* a scratch copy of 29b plus `- #1454 OPEN` gives rc=1, so the arm discriminates.

```text
handoff-check: 1 finding(s) in $SCRATCH/arm1-control.md
- pr_claim_mismatch: `#1454 OPEN ($SCRATCH/arm1-control.md:64)` — GitHub reports PR #1454 state=MERGED auto-merge=yes checks fail:0 pending:0 pass:15
[handoff-check] ERROR task failed
rc=1
```

**Arm 2:** `mise run handoff-check -- .agent/plans/session-2026-09-02.md`. The info lines name #887 as skipped,
including the cold review's line 42, `#905 … #887's … OPEN, auto-merge ARMED`. The rc=1 comes from a pre-existing
`forbidden_task_carrier` in this old handoff, not from a claim. Skips never fail.

```text
handoff-check: 1 finding(s) in .agent/plans/session-2026-09-02.md
- forbidden_task_carrier: `## NEXT TASK 3 — the mise-config-tier clarity task, in detail` — task_plan.md is the only task carrier; handoffs carry state and evidence
handoff-check: info — skipped #887 MERGED (.agent/plans/session-2026-09-02.md:40): #887 is an issue, not a PR
handoff-check: info — skipped #887 auto-merge armed (.agent/plans/session-2026-09-02.md:42): #887 is an issue, not a PR
[handoff-check] ERROR task failed
rc=1
```

*Control:* the same file through the `744c3b92` module (`git archive` into the scratchpad, `PYTHONPATH`, with
`__file__` printed to prove which module ran) prints the same finding and **no** info line. That is the skip being
invisible before this change.

```text
module: $SCRATCH/base744/python/src/dotfiles_setup/handoff_check.py
handoff-check: 1 finding(s) in .agent/plans/session-2026-09-02.md
- forbidden_task_carrier: `## NEXT TASK 3 — the mise-config-tier clarity task, in detail` — task_plan.md is the only task carrier; handoffs carry state and evidence
rc=1
```

**Arm 3a:** `mise run session-state -- --for .agent/plans/session-2026-09-29c.md` gives rc=0.
- The `generated` line sits right after the branch line.
- The since source is still `…29b.md mtime`, because 29b has no stamp.
- This run is the control for 3b: #1455 is **absent** here.

```text
- **branch**: `feat/s29h-machine-checked-handoff`
- **generated**: 2026-09-30T15:30:43Z
- **merged since** 2026-09-29T22:26:03Z (.agent/plans/session-2026-09-29b.md mtime (excluding .agent/plans/session-2026-09-29c.md)) (3):
  - #1460 MERGED 2026-09-30T11:07:46Z — `Update mise tools` (@app/renovate)
  - #1459 MERGED 2026-09-30T10:57:25Z — `chore: refresh vendored config schemas` (@app/dotfiles-refresh-bot-org)
  - #1458 MERGED 2026-09-30T04:22:54Z — `Update mise tools` (@app/renovate)
rc=0
```

**Arm 3b:** I wrote the scratch file `.agent/plans/session-2026-09-29y.md` containing only
`- **generated**: 2026-09-29T21:00:00Z`, then ran `mise run session-state -- --for session-2026-09-29-z.md`.
- It gave rc=0, with since `2026-09-29T21:00:00Z` taken from `…29y.md generated stamp`, and the merged list
  includes #1455.
- The scratch file was then deleted: `rm` rc=0, and a directory listing shows 0 matches.

```text
- **merged since** 2026-09-29T21:00:00Z (.agent/plans/session-2026-09-29y.md generated stamp (excluding session-2026-09-29-z.md)) (7):
  - #1460 MERGED 2026-09-30T11:07:46Z — `Update mise tools` (@app/renovate)
  - #1459 MERGED 2026-09-30T10:57:25Z — `chore: refresh vendored config schemas` (@app/dotfiles-refresh-bot-org)
  - #1458 MERGED 2026-09-30T04:22:54Z — `Update mise tools` (@app/renovate)
  - #1456 MERGED 2026-09-29T22:09:36Z — `docs(handoff): 2026-09-29b — mise-native dotfiles research + plan, Omarchy verdicts, /ultrareview research, §1c audits, goal-history 044` (@sortakool)
  - #1455 MERGED 2026-09-29T22:02:07Z — `Update dependency aqua:betterleaks/betterleaks to v1.9.0` (@app/renovate)
  - #1454 MERGED 2026-09-29T21:52:30Z — `feat/research sweep tuning` (@sortakool)
  - #1453 MERGED 2026-09-29T21:05:02Z — `Update mise tools` (@app/renovate)
rc=0
```

This also shows F1's reach beyond #1455. #1453, #1454 and #1456 were hidden by the mtime window too. #1456 is 29b's own
docs PR, merged at 22:09:36Z, before 29b's mtime of 22:26:03Z.

**Arm 4:** `mise run session-state -- --for notes.md` gives rc=2.

```text
session-state: --for must name a session-YYYY-MM-DD[-x].md handoff
[session-state] ERROR task failed
rc=2
```

*Control:* `mise run session-state -- --no-pr --for session-2026-09-29-c.md` gives rc=0, so a valid handoff name
passes, including the hyphenated spelling.

**Extra (paste round trip, with the generated line):** the arm 3b output, pasted under `## State` into a scratch
handoff, gives `handoff-check` rc=0. The new line adds no finding.

```text
handoff-check: OK — $SCRATCH/paste-r2.md citations resolve; 39 PR claim(s) match GitHub
rc=0
```

## What changed, per finding

- **F1:**
  - `Snapshot.generated_at: str` is set once in `gather` from `utc_now()`. The same moment also feeds the
    default window.
  - `render` emits `- **generated**: <UTC>` directly after the branch line.
  - `default_since` reads the chosen previous handoff's LAST `^- \*\*generated\*\*: (\S+)\s*$` line that
    `parse_since` accepts. The source is then `"<path> generated stamp"`, plus the existing `(excluding …)`.
  - With no parsable stamp it keeps the mtime behaviour. An unreadable file (`OSError`) falls back to mtime without
    raising.
- **F2:**
  - `ClaimTally(checked, skipped)` exactly as in the spec. `check_with_claims` returns `(findings, ClaimTally)`,
    and `check()` still returns findings only.
  - `render(findings, *, source, tally=None)` appends `; K skipped (PR-only word on an issue)` to the OK line.
    Both forms get one `handoff-check: info — skipped #N <word> (<source>:<line>): #N is an issue, not a PR` per
    skip.
  - The rc is unchanged. `claims_checked` is replaced by `tally.checked`.
- **F3:** `_GLUED_REFERENCE = (?<=\w)#\d+` adds window boundaries without adding references. `/#N` matches neither
  regex, so `#A/#B` is unchanged.
- **F4:** `_FOREIGN_QUALIFIER` keeps only `KB`, `kb` and `knowledge-base`, with an optional `PR`/`issue`. The
  `extract_claims` docstring now names `owner/repo #12` and `other-repo #5` as still read as dotfiles.
- **F5:**
  - New public `handoff_check.handoff_key(path)` returns (date, letter order) from the basename.
  - `newest_handoff` excludes by that key and raises `ValueError` for a non-handoff `exclude` (dissent 2 above).
  - The `session-state` `--for` flag rejects a non-matching basename with the exact spec message and rc=2.
- **F6:** new tests cover every spec bullet. The pre-existing M10 URL test is kept, and `owner/repo#12` moved to its
  own glued-number test.

## Allowlist compliance

`git diff --stat` covers only `handoff_check.py`, `session_state.py`, `tests/test_handoff_check.py` and
`tests/test_session_state.py`. `main.py` is untouched because no interface forced it. Beyond that, the only writes
were append-only `progress.md`/`findings.md` and this report. I did not touch `task_plan.md`, `.claude/**`,
`.agents/**`, other `docs/**` or the classifier files, and no gate demanded it. No credential was printed. No
suppressions were added.

## Residue for #1457 (not fixed here: outside the r2 allowlist)

1. `python/src/dotfiles_setup/main.py:1543` and `:1550`: the `session-state` help text still says the default is
   "newest handoff's mtime". It should read "generated stamp, else mtime". This is a two-string edit. No interface
   forced it, so it stayed out.
2. `.claude/skills/session-handoff/SKILL.md` step 5 grammar: add the clause that a PR-only word on an issue is
   SKIPPED, counted on the OK line and listed as an info line (cold-review F2 disposition). `--for` now also
   requires a `session-YYYY-MM-DD[-x].md` name. This is the architect's docs lane.
3. By design, F2 stays a visibility fix. A PR's words captured by an intervening issue number (`#905 … #887's … OPEN,
   auto-merge ARMED`) still attach to the issue. Arm 2 shows the skip is now printed, but #905 itself is still not
   judged.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): live `gh api …/issues/N` and `gh pr view` for the
  claims in 29b, 09-02 and the scratch copies (#1454, #887 and others); `gh pr list` for the open and merged-since
  lists in arms 3a/3b.
