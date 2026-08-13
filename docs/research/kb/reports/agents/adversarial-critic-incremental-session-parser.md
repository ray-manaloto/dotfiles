# Adversarial critique — incremental session parser (2026-08-13)

Re-review status: **ACCEPT** against the current fixed diff. Exact replay scope:
attachment-change plus transcript-append, and valid non-newline EOF followed by
newline plus record.

## Fixed-diff re-review — ACCEPT

The prior BLOCK is overturned for the current fixed diff. Both and exactly both
motivating defects now fire correctly, their regression tests drive the public
cache path against the independent cold parser, and the complete focused suite
passes.

| Cell | Current result | Armed control |
|---|---|---|
| Attachment bytes change and the owning transcript appends | **FIRES.** `_append_source_facts()` revalidates the cached dependency before extending facts (`session_ledger.py:3069-3080`). Mismatch raises `AppendRebuildError`; `SessionStore.resolve()` cold-rebuilds (`session_store.py:412-427`). Exact replay: cached hash, cold hash, and independent expected hash all `f6541576…`; `rebuilt_sources=1`, `appended_sources=0`, `decoded_bytes=808`. | `test_attachment_change_plus_transcript_append_forces_cold_oracle` (`tests/test_session_ledger.py:1012-1087`) asserts full cold-oracle field equality, independent attachment SHA-256, rebuild count 1, append count 0, and full-source decoded bytes. The pre-fix historical replay returned stale `d8fa39ab…`, so this control discriminates. |
| Valid JSON at non-newline EOF, then newline plus another record | **FIRES.** `_snapshot()` commits only a newline-terminated prefix (`session_store.py:255-272`), so the valid but unterminated record is initially incomplete and the later append begins at the previous newline boundary. Exact replay: cached and cold evidence digest both `5fc7625d…`; omissions agree exactly; no malformed JSON; `appended_sources=1`. | `test_valid_non_newline_tail_is_not_committed_before_later_append` (`tests/test_session_ledger.py:1090-1144`) asserts the first pass is incomplete, cached/cold field equality after continuation, both requirements, and absence of malformed JSON. The pre-fix historical replay produced stale `f801fb78…` plus a spurious malformed line, so this control discriminates. |

Exact replay output:

```text
attachment_initial_hash=d8fa39abdd51e891fb3d883b3ce7ab6fbb4ee8d98ae3c7acfe7528cba680c6d2
attachment_cached_after_append=f654157644d60c1adce8f39cd2a6f757aaef0845de0a490fb1c1641a9145a80a
attachment_cold_oracle_after_append=f654157644d60c1adce8f39cd2a6f757aaef0845de0a490fb1c1641a9145a80a
attachment_expected_second=f654157644d60c1adce8f39cd2a6f757aaef0845de0a490fb1c1641a9145a80a
attachment_cached_equals_cold=True
attachment_coverage_equals_cold=True
append_stats=CacheStats(reused_sources=0, appended_sources=0, rebuilt_sources=1, decoded_bytes=808, corrupt_entries=0)
newline_first_incomplete=True
newline_cached_event_signature=[('user_message', 2, '5fc7625d9f2aa471786d237b6efa3e4c5c192c0ca8c7659726ea38c9d78bf428')]
newline_cold_oracle_signature=[('user_message', 2, '5fc7625d9f2aa471786d237b6efa3e4c5c192c0ca8c7659726ea38c9d78bf428')]
newline_cached_omissions=('codex:active: open turn turn-2',)
newline_cold_oracle_omissions=('codex:active: open turn turn-2',)
newline_cached_equals_cold=True
newline_stats=CacheStats(reused_sources=0, appended_sources=1, rebuilt_sources=0, decoded_bytes=178, corrupt_entries=0)
```

Focused regression result:

```text
........................................................................ [ 42%]
........................................................................ [ 85%]
.........................                                                [100%]
169 passed in 3.04s
```

The current diff was re-read immediately before this verdict at
`session_ledger.py:3052-3080`, `:3112-3163`, `session_store.py:255-272`,
`:412-444`, and `tests/test_session_ledger.py:1012-1144`. It had not moved
during replay: 8 proposal files, 1,133 insertions and 73 deletions; `git diff
--check` remained clean.

The historical BLOCK analysis below is retained as the replay record for the
superseded diff; it is not the verdict on the current fixed diff.

Record replayed against: the exact uncommitted diff in
`/private/tmp/dotfiles-session-incremental.KDs8T9/repo`; production wiring in
`python/src/dotfiles_setup/session_ledger.py` and
`python/src/dotfiles_setup/session_store.py`; focused controls in
`tests/test_session_ledger.py`, `tests/test_session_store.py`, and
`tests/test_session_review.py`; and fresh temporary JSONL fixtures driven through
the public `build_requirement_coverage()` cache path and the cold
`parse_transcripts()` oracle.

Graphify orientation was attempted first and retained as a hard failure:

```text
[graphify-query] $ uv run --project python dotfiles-setup graphify query 'Orien…
graphify: incomplete: graph health is missing: /private/tmp/dotfiles-session-incremental.KDs8T9/repo/graphify-out/graph.json
[graphify-query] ERROR task failed
```

| # | Verdict | Proposal | Fires on its motivating cases? | Shape |
|---|---|---|---|---|
| 1 | **BLOCK** | Persist per-source pre-finalization facts; reuse or suffix-append them; globally refinalize every run; recover through a cold parser. | **No.** Positive controls pass, but 3 fresh motivating-case replays fail: private text is persisted; attachment mutation plus append returns stale evidence; a valid non-newline EOF record followed by its newline breaks evidence and line parity. | 5; direct replay defects outside the seven zero/backwards shapes |

## 1. Incremental per-source facts with global refinalization — BLOCK

### Proposal and motivating defects

The proposal stores normalized per-source facts under
`.agent/state/session-review`, chooses reuse/append/rebuild from a validated
source prefix, and re-runs cross-source relationships and semantic dispositions
globally. Its motivating defects, supplied with the review brief, are:

- repeated full reparse of about 1 GB across 152 sources;
- late evidence, forms, tools, compaction, and lineage losing cold-parser parity;
- raw or private cache leakage;
- corrupt, torn, or concurrent cache publication;
- semantic dispositions requiring global refinalization with zero transcript
  decode.

The implementation anchors are `session_ledger.py:2714-2733` (fact encoding),
`:2746-2908` (global merge/finalization), `:3066-3199` (production cache
wiring), and `session_store.py:255-278`, `:322-359`, `:371-464` (snapshot,
publication, and resolve state machine). The claimed production controls are
summarized at `tests/TEST-INDEX.md:74`.

### Replay table

| Real/motivating case | Result | Replay |
|---|---|---|
| Cold parse, unchanged reuse, semantic disposition-only refinalization, forms/tools/terminal suffix, corrupt object, same-size rewrite, explicit rebuild | **FIRES** | `test_build_coverage_cache_is_incremental_global_and_path_private` plus store controls; cached fields equal cold oracle and unchanged/disposition-only runs decode 0 transcript bytes. |
| Late direct/response user twins, both orders | **FIRES (2/2)** | `test_cached_late_codex_user_twins_match_the_cold_oracle[direct-first]` and `[response-first]`. |
| Cross-source lineage and compaction on unchanged reuse | **FIRES** | `test_cached_cross_source_lineage_and_compaction_match_cold_oracle`; all selected sources reused with 0 decoded bytes. |
| Focused suite as published | **FIRES** | 167 of 167 focused tests pass. This is the positive arm proving the harness reaches the intended production path. |
| Private cache leakage | **NO** | Fresh synthetic private canary appears verbatim in one content-addressed fact object; a freshly invented absent term appears in none. The shipped control checks absolute transcript paths only (`test_session_ledger.py:734-741`). |
| External attachment changes while its transcript also appends | **NO** | Cache appends 110 transcript bytes and retains the old attachment hash; the cold oracle returns the new hash. Dependency validation is conditional on `reused_sources` only (`session_ledger.py:3143-3151`), so APPEND bypasses it. |
| Valid JSON record at EOF without newline, then writer appends newline plus next record | **NO** | Cache appends 81 bytes, manufactures a line-3 malformed-JSON omission, and keeps the old evidence digest; cold oracle has no malformed line and hashes the record including its newline. `_snapshot()` deliberately accepts valid non-newline JSON (`session_store.py:271-278`), but suffix parsing begins at the former EOF byte boundary. |
| Same-process concurrent publication | **PARTIAL** | The focused store test proves two identical run receipts use distinct temporaries and leave a valid pointer. It does not replay competing non-identical aggregate run receipts or multi-source snapshot consistency. No failure was established here because the two direct failures above already settle BLOCK. |

Focused positive replay, verbatim:

```text
........................................................................ [ 43%]
........................................................................ [ 86%]
.......................                                                  [100%]
167 passed in 2.70s
```

Private-cache negative and control arm, verbatim:

```text
privacy_positive_canary_hits=['objects/05/43ef694ce94d632e7562cd6390b95b11c8c94b78532543b0ef3d012645d696']
privacy_fresh_absent_control_hits=[]
```

Attachment append replay, verbatim:

```text
attachment_initial_hash=d8fa39abdd51e891fb3d883b3ce7ab6fbb4ee8d98ae3c7acfe7528cba680c6d2
attachment_cached_after_append=d8fa39abdd51e891fb3d883b3ce7ab6fbb4ee8d98ae3c7acfe7528cba680c6d2
attachment_cold_oracle_after_append=f654157644d60c1adce8f39cd2a6f757aaef0845de0a490fb1c1641a9145a80a
attachment_expected_second=f654157644d60c1adce8f39cd2a6f757aaef0845de0a490fb1c1641a9145a80a
attachment_cached_equals_cold=False
append_stats=CacheStats(reused_sources=0, appended_sources=1, rebuilt_sources=0, decoded_bytes=110, corrupt_entries=0)
```

Non-newline EOF append replay, verbatim:

```text
cached_event_signature=[('user_message', 2, 'f801fb786262f76d6b5d39f0fe11804a8e81b84f17a0d5053aab6bdedba1ca99')]
cold_oracle_signature=[('user_message', 2, '5fc7625d9f2aa471786d237b6efa3e4c5c192c0ca8c7659726ea38c9d78bf428')]
cached_omissions=('codex:active.jsonl:3: malformed JSON', 'codex:active: open turn turn-2')
cold_oracle_omissions=('codex:active: open turn turn-2',)
cached_equals_cold=False
append_stats=CacheStats(reused_sources=0, appended_sources=1, rebuilt_sources=0, decoded_bytes=81, corrupt_entries=0)
```

### Control arm

The zero/decode and parity probes are not inert: the published positive suite
passes 167 cases, the cold attachment oracle returns exactly the independently
computed SHA-256 of `second-attachment`, and the fresh absent privacy term
returns zero hits while the synthetic private canary returns one. The two NO
results therefore are not failed discovery or an empty cache.

### What fires first

On an appended source, `SessionStore.resolve()` classifies APPEND and publishes
the appended fact object before `_cached_requirement_coverage()` considers
external dependencies. The only dependency check is guarded by
`resolved.stats.reused_sources`; therefore APPEND fires first and makes the
dependency guard inert on that branch. For a formerly non-newline EOF record,
the cached byte count fires as the suffix boundary before JSONL line boundaries
are restored, so suffix decode starts with a bare newline.

### Placement cost

The implementation lives in the Python library and the operator note lives in a
lazy session-review skill, not eager global prose. That placement cost is
appropriate. `.agent/` is gitignored, which limits Git publication, but it does
not make verbatim private transcript text absent from the local cache.

### Seven-shape check

1. **Fires on zero motivating cases:** no; the positive controls genuinely fire.
2. **Inverted selectivity:** no inversion established.
3. **Self-refuting:** no.
4. **Dominated/inert by construction:** only on the attachment-APPEND branch,
   where APPEND bypasses the reuse-only dependency guard.
5. **The saving throw is judgement, not the gate:** yes. The test index claims
   “attachment dependency invalidation,” but the attachment test exercises only
   the cold parser; the production cache equality test has no attachment. The
   missing APPEND × external-dependency cell is caught only by the adversarial
   cold-oracle question.
6. **Misapplied, not wrong:** no. The underlying per-source/global-finalization
   split survives this BLOCK and should not be discarded with the verdict.
7. **A metric that ranks the winner worst:** not established. `decoded_bytes`
   correctly measures decoder work, though it does not measure the full-file
   reads and hashing still required for prefix validation.

### Exact disposition

**BLOCK.** Do not accept this proposal while the production append path can
return a ledger unequal to its cold oracle and while the private-cache contract
is stated only as path absence. The caller owns any replacement; this critique
does not edit the proposal.

## What survives, and what the survivors do NOT cover

The content-addressed object/manifest/pointer design, exclusive source resolve,
parser/policy fingerprints, explicit cold rebuild, per-source pre-finalization
facts, and global semantic refinalization all survive. The focused positive
replay demonstrates real value: unchanged and disposition-only runs report zero
decoded transcript bytes, late form/tool completion matches the cold oracle,
and corruption/rewrite repair works.

Those survivors do **not** cover external dependency mutation concurrent with
append, transition from a valid non-newline EOF record to continued JSONL, or a
privacy requirement stronger than hiding absolute transcript paths. The 1 GB /
152-source historical workload also has no retained workload replay in this
diff; the evidence here establishes functional decoded-byte savings on small
fixtures, not an end-to-end wall-time or I/O result on that corpus.

## Re-verified before reporting

Immediately before reporting, I re-read the exact current diff and the verdict's
dependencies at `session_ledger.py:2714-2733`, `:3098-3160`,
`session_store.py:255-278`, `:371-464`, `tests/test_session_ledger.py:694-771`,
`:840-914`, `:1331-1389`, `tests/TEST-INDEX.md:72-74`, and
`.claude/skills/session-review/SKILL.md:24-28`. The proposal had not moved: the
diff remained 8 modified proposal files, 999 insertions/deletions net as shown
by the same `git diff --stat`, and the report was the only new path.

## GitHub repos touched

- None — this critique used only the supplied local temporary checkout.
