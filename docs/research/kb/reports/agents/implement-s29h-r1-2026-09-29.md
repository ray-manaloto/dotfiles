# implement-s29h-r1 — S29-H round-1 review fixes (Opus fallback), 2026-09-29

Spec: `docs/specs/s29h-r1-review-fixes.md`. Branch: `feat/s29h-machine-checked-handoff` @ `4e337900`. Nothing is committed (COMMIT: caller).

## Status

R1-R8 are all implemented. All three gates pass (lint 0, pytest 0, verify 0). All five live arms, each with a control arm, behave as specified. All eleven mutation arms turn their tests red. No gate demanded a change to the classifier files.

## Changed paths (inside the spec's §2 allowlist)

- **`python/src/dotfiles_setup/handoff_check.py`**
  - R1: `_FOREIGN_QUALIFIER`. A qualified reference yields no claim but still ends the previous reference's window. The limitation is documented in `extract_claims`.
  - R6: `_NEGATED_CLAIM` is masked inside `_window_words` before the claim patterns run.
  - R2: `newest_handoff(repo_root, *, exclude=None)` compares resolved paths. Existing callers are unchanged.
  - R8: `CLAIMS_DEADLINE_S` comment and `check_with_claims` docstring say "no NEW lookup after 300 s; in-flight adds up to 2 × GH_TIMEOUT (~540 s)".
- **`python/src/dotfiles_setup/pr_facts.py`**
  - R4: `_started_at`, `_dedupe_key`, `_latest_checks`. `count_checks` now buckets only the newest entry per key: `context`, else `(name, workflowName)`. The docstring notes that gh also keys on the workflow run's event, which `--json statusCheckRollup` does not expose.
  - R8: the `classify_check` docstring says why gh's `bucket` isn't used and that CANCELLED/STARTUP_FAILURE deliberately count as failing.
- **`python/src/dotfiles_setup/session_state.py`**
  - R2: `default_since(..., *, exclude=None)`. The source reads `"<path> mtime (excluding <for-path>)"`. Also `gather(..., for_handoff=None)` and `main --for <path>` (rc=2 with no value; `--since` wins).
  - R3: a `_code()` helper renders the branch-PR title and commit subjects as code spans, with backticks replaced by `'`.
  - R5: `_summaries` returns `(rows, truncated)`. `Snapshot` gains `open_truncated` and `merged_truncated` (default False). A list that fills the limit renders `(100, TRUNCATED at --limit 100 — list may be incomplete)`.
- **`python/src/dotfiles_setup/main.py`**: the session-state `--for` parser argument (`dest=for_handoff`) and its dispatch forwarding only.
- **`mise.toml`**: the session-state description gains `[-- --for <handoff>]`.
- **Tests**:
  - `tests/test_handoff_check.py`: R1, R6, M9, M10, `newest_handoff(exclude=)`.
  - `tests/test_pr_facts.py`: R4.
  - `tests/test_session_state.py`: R2, R3, R5, M1, `--for` dispatch.
- **Append-only**: `progress.md`.

## Gates

| gate | command | rc | evidence |
|---|---|---|---|
| lint | `mise run gate -- run lint` | **0** | failures [] |
| pytest | `mise run gate -- run pytest` | **0** | `4268 passed, 11 deselected in 295.62s` (no other pytest process was running) |
| verify | `mise run gate -- run verify` | **0** | `166 passed, 0 failed, 4 skipped` |

## Live arms (§5), live GitHub, each with a control

1. `mise run handoff-check -- .agent/plans/session-2026-09-29b.md` → **rc=0**: `handoff-check: OK — .agent/plans/session-2026-09-29b.md citations resolve; 19 PR claim(s) match GitHub`. The control is arm 3's control, run against the same handoff: rc=1.
2. Scratch copy + `- knowledge-base PR #611 MERGED and KB #509 OPEN` → **rc=0**, `… 19 PR claim(s) match GitHub`. The count is unchanged, and no finding mentions #611 or #509.
   Control, the same line without qualifiers (`- PR #611 MERGED and #509 OPEN`) → **rc=1**: `pr_claim_mismatch: #509 OPEN (r1-arm2-control.md:63) — GitHub reports PR #509 state=MERGED auto-merge=yes checks fail:0 pending:0 pass:15`. An in-process extract of that line gives `[(611, 'MERGED'), (509, 'OPEN')]`. The #611 claim held because dotfiles #611 is MERGED (`gh pr view 611` → MERGED). The qualified line extracts `[]`.
3. Scratch copy + `- #1454 was RED; auto-merge disarmed on #1452` → **rc=0**, 19 claims, no finding.
   Control `- #1454 RED` → **rc=1**: `pr_claim_mismatch: #1454 RED (r1-arm3-control.md:63) — GitHub reports PR #1454 state=MERGED auto-merge=yes checks fail:0 pending:0 pass:15`.
4. session-state `--for` (29z was confirmed absent beforehand and deleted afterwards):
   - `mise run session-state -- --for .agent/plans/session-2026-09-29c.md` → rc=0: `- **merged since** 2026-09-29T22:26:03Z (.agent/plans/session-2026-09-29b.md mtime (excluding .agent/plans/session-2026-09-29c.md)): none`
   - After `touch .agent/plans/session-2026-09-29z.md`, `--for` that path → rc=0: `… (.agent/plans/session-2026-09-29b.md mtime (excluding .agent/plans/session-2026-09-29z.md)): none`
   - Control, without `--for` → rc=0: `- **merged since** 2026-09-30T00:11:35Z (.agent/plans/session-2026-09-29z.md mtime): none`. This is the collapse R2 prevents.
5. Live `session-state -- --for …29c.md` output (7 open PR rows, commit subjects now code spans) pasted into a scratch handoff → **rc=0**, `… 39 PR claim(s) match GitHub`. That is 19 from the handoff plus 20 from the pasted rows.
   Control, one pasted row flipped `#1141 OPEN, green` → `#1141 OPEN, RED` → **rc=1**: `pr_claim_mismatch: #1141 RED (r1-arm5-control.md:99) — GitHub reports PR #1141 state=OPEN auto-merge=no checks fail:0 pending:0 pass:14`.

## Mutation arms

Each arm deleted or neutered one production line and ran the owning test file. The file was then restored from a byte copy; `cmp` confirmed all four sources identical afterwards.

| arm | mutation | result |
|---|---|---|
| M1 | main.py: delete the `--since` forwarding line | rc=1, `test_cli_dispatch_forwards_since` |
| `--for` | main.py: delete the `--for` forwarding | rc=1, `test_cli_dispatch_forwards_for` |
| M9 | `check()`: drop `facts=facts` | rc=1, `test_check_forwards_injected_facts`. `run_gh` was patched to fail, so no network call was made |
| M10 | lookbehind `[\w#/]` → `[\w#]` | rc=1, `test_a_slash_before_the_hash_is_not_a_reference[see https://docs.example.com/guide/#12 MERGED]` |
| R1 | delete the `_FOREIGN_QUALIFIER` skip | rc=1, 6 failed (5 qualified forms plus window-end) |
| R2 | delete `or path.resolve() == excluded` | rc=1, `test_default_since_excludes_the_handoff_being_written`, `test_cli_dispatch_forwards_for` |
| R3 | commit subject rendered raw | rc=1, `test_branch_pr_and_commit_subjects_render_as_code_spans` |
| R3b | branch-PR title rendered raw | rc=1, same test |
| R4 | `count_checks` without `_latest_checks` | rc=1, 4 failed (stale FAILURE/newer SUCCESS, reverse, missing startedAt, context dedupe) |
| R5 | truncated flag → `False` | rc=1, `test_a_list_that_fills_the_limit_says_it_may_be_truncated` |
| R6 | delete the `_NEGATED_CLAIM` mask | rc=1, 9 failed (every negated/past form) |

## Dissent / deviations

1. **M10's example cannot carry the arm.** R7 asks for a test that `owner/repo#12 MERGED` yields no claim and turns red when `/` is removed from the lookbehind. It cannot turn red: the character before `#` is `o`, which the `\w` in the lookbehind already rejects. That is why cold F5 found M10 deletable. I kept the spec's literal case and added `see https://docs.example.com/guide/#12 MERGED`, where `/` directly precedes `#`. That second case is the one that goes red, as the table shows.
2. **R4 changed existing fixtures, not assertions.** Several fixtures listed rollup entries with no `name`, `workflowName` or `context`. Under the spec's key rule those all share one key and collapse to one, and gh would collapse them the same way. I gave each such entry a distinct `name` or `context`. Every expected value stays as it was: `2/3 passing`, `fail:1 pending:0 pass:2`, `CheckCounts(1, 2, 1)` and so on. No assertion was edited.
3. **R5 carries the truncation flag on the snapshot.** It lives in two `Snapshot` fields with default False, not in a new container type, so `open_prs` and `merged_prs` stay `tuple[PrSummary, ...] | None` for callers. The spec allowed either shape. The flag is set when `len(rows) >= 100`.
4. I also restored `gather`'s original gh call order (branch PR first), after an intermediate version reordered it and broke the tests that index `calls`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): live PR/issue facts for arms 1-5, read-only.
- [cli/cli](https://github.com/cli/cli): not fetched by me. The R4 rule follows the spec's citation of `pkg/cmd/pr/checks/aggregate.go:96-120@e9542451`.
