# Cold review — credit-fallback projection (N1/N2), `636dd297..e90833fd`

- Reviewer: cold-reviewer (Opus), 2026-10-04. Status: COMPLETE.
- **Verdict: SHIP** — 0 HIGH, 0 MEDIUM, 3 LOW, 4 INFO. Every focus question answered "holds" (see § Focus answers).
- Subject: `git diff 636dd297 e90833fd` (one commit, `e90833fd`), worktree
  `.claude/worktrees/credit-fallback`, branch `feat/research-credit-fallback`.
- Spec: `handoff-2026-10-04b/docs/research/kb/raw/specs-2026-10-04b/spec-credit-fallback-projection-r1.md` (§8 r1.1 supersedes).
- Memory: consulted (`fetcher_fanout_review_patterns.md` rounds 4-5, `saved_workflow_js_review.md`, `mutation_harness.md`).

## Findings

| # | Severity | Claim | file:line |
|---|---|---|---|
| F1 | LOW | The JS copied-row checks `Number.isInteger(m.rc)`, `Number.isInteger(m.bytes)` and `typeof m.provisional === 'boolean'` are the ONLY barrier for those three fields. Removing them puts a forged sentinel into the synthesize prompt with 0 gaps (E4, both arms). Yet no test pins any of them: U-JS1/2/3 are each GREEN 417/417 (E5). The `required_failed` length cap is unpinned too (U-JS4 GREEN). The claimed M-W1 is coarse: it goes red only through the route and code arms. Fix: add rc/bytes/provisional/oversize arms to the T13 parametrize | `.claude/workflows/research-sweep-run.js:507`, `:133`; `tests/test_workflows_js.py` (`test_projection_workflow_revalidates_copied_rows`) |
| F2 | LOW (reachability UNVERIFIED) | The fallback rule still launders a NON-credit non-2xx failure into a credit skip when the provider's top-level `message`/`error` echoes a query containing the phrase. Probe: serper `400 {"message":"Invalid query: why do I get not enough credits"}` gives serper `skipped` and strict **True** (provisional). The fresh-token control gives serper `error` and strict False (E3). This is the N4 query-echo class on the fallback routes. It matches ratified §3.3, so it calls for a **ticket** (N4 sibling), not a change to this diff. It is unverified whether Serper or SerpApi echo the query in a top-level 4xx field | `python/src/dotfiles_setup/research_fanout.py:241-244` |
| F3 | LOW | Two mirror rows that the producer never emits (`research_fanout.py:2828-2831`) get through the JS consumer. (a) It hardcodes "mirrored via webclaw" and never checks route against provisional, so a copied row with `route:'firecrawl', provisional:true` renders `mirrored via webclaw (credits-exhausted)`. (b) A copied `route:'webclaw', provisional:false` mirrored row yields status `complete` with no provisional disclosure and no gap (probe XFIELD, E6). The Q-CLAIM clause "via webclaw" has no enforcing line in the consumer. (b) pre-exists at 636dd297 (`provisional: m.provisional === true`). Fix: reject `provisional !== (route === 'webclaw' && mirrored)` in the row check | `.claude/workflows/research-sweep-run.js:665`, `:506-514` |
| F4 | INFO | The T7 re-derivation runs only when `status == "skipped"`. A 636dd297-era bare-body serper attempt relabelled to `ok`, `empty_verified` or an unknown string therefore passes strict as a route-less provisional skip (E3: `(True, …)` for all three; `skipped` control → the fixed reject). This is subsumed by the retained §4.3 missing-key class: the evidence-less "not inherited" relabel also passes (probed). Optional closure: in a route-less skip, require every fallback attempt to be SKIPPED | `research_fanout.py:2181-2182`, `:2255-2260` |
| F5 | INFO | Two reachable clauses of `_validate_fallback_prerequisite` are unpinned: `status == SKIPPED` (U-PY3 GREEN) and `raw_sha256 is None` (U-PY4 GREEN). Impact is nil beyond F4: the route-less check already rejects an evidence-less ERROR attempt | `research_fanout.py:2187-2189` |
| F6 | INFO | §4.2 says "no unpinnable guard … report it instead of shipping it". Four redundant or unreachable guards shipped unreported, each GREEN when deleted: `transport.rc is not None` (dead, because the decoder forces rc None when status is an int, `:2224-2228`); `type(http_status) is not int` (redundant, since `_fallback_credit(None, …)` is False); the summary check `result.reason in _PREREQUISITE_TEXTS` (unreachable: the only PREREQUISITE producer, `:1606`, uses the closed literals); and the JS `codeText` set fallback (unreachable). All are harmless defence in depth; this is a process deviation only | `research_fanout.py:2204-2205`, `:3150`; `research-sweep-run.js:519` |
| F7 | INFO | A fixture update in the §5.2 class is missing from the implementer's inversion list: `"reason": ""` → `"code": ""` in `test_mirror_index_never_lists_an_earlier_runs_probe_as_a_mirror`. The README now fails closed on a missing code, so the test needs this change to stay on its stale-probe branch. It is sanctioned in substance, not edit-to-pass | `tests/test_research_fanout_probe.py:500` |

## Focus answers (each verified, not inherited)

1. **N2: holds.** The Stop reason is built from `provisional_entries` (source and route) plus fixed text only. Every
   identifier is set-validated before an entry is built. The one-block, null-answer and `stop_hook_active` code is
   unchanged. The failed-branch reasons are fixed text (E2). M-N2b is RED.
2. **N1: holds.** The producer and the consumer call the same `_fallback_credit` (`:1526`, `:2206`). Every T7 and §8.A
   arm returns the single fixed reason. M-N1c turns exactly the two well-formed, non-re-deriving arms RED (E3, E5).
   M-N1d is RED. Residuals: F2 (a ticket) and F4 (subsumed by §4.3).
3. **§3.6 JS re-validation: fails closed.**
   - §8.C: C-JS1 is RED, and the T14 arms cover rc 0/bytes 0 → `empty-output`, and rc≠0 or bytes<0 →
     `invalid-probe` + gap.
   - `full_name`: C-JS3 is RED. Python's `.strip()` + `_REPO_SHAPE.fullmatch` is pinned (`test_projection_repo_name_rejects_diagnostic_bytes`).
   - `required_failed`: validated before the disabled-tracker filter (`:490-491`).
   - Gaps: F1 (unpinned) and F3 (cross-field).
4. **FailureCode: no text passthrough.**
   - `failure_code` returns only enum members (`:150-191`). Every model-visible consumer uses `.value`.
   - The only passthrough is `[prerequisite: <text>]`, gated on the 8-literal closed set (`:3150`).
   - Every mirror branch sets its code at production time and never derives it from text. This matches the §3.1 mirror table row by row (`:2682-2853`).
5. **Inversions: all sanctioned.** Every changed pre-existing assertion maps to a §5.2 or §8.E line:
   - `test_research_fanout.py`: 734, 2417, 2535/2538, 2832/2833.
   - probe tests: 285, 352-363, 376, 401, 410, 418-430, 635/638, 686, 740/750/753, 771-773.
   - JS tests: harness, 1306-1318, 1338-1364, 1391/1469, 1451, 1483-1493, 1579-1588, 2354-2382, 2918/2930, 3029/3039.

   The one unlisted fixture update (F7) is a necessary consequence. No assertion was weakened outside these.
6. **Spot-check of the claimed mutations: 4/4 RED** (M-N2b, M-N1c, M-N1d, M-W1-route). Six controls were RED. Every
   restore was confirmed.

## Q-CLAIM (operator/model-facing strings this diff adds)

| String clause | Enforcing line | OK? |
|---|---|---|
| gate `PROVISIONAL (credit-exhausted provider)` | entries exist only for rows whose primary credit re-derived, `research_fanout.py:2284`, `:2239-2244` | yes |
| gate `Name PROVISIONAL and each of these` | `named` check, `codex-research-gate.py:117-120` | yes |
| `{source} via {route} (credits-exhausted)` / `skipped: credits-exhausted; no fallback succeeded` | route validated `:2128-2131`; route-less evidence `:2255-2260` | yes |
| `; {route}: credits-exhausted` (SKIPPED + `raw_file`) | re-derived `:2181-2182` | yes |
| `; {route}: prerequisite` (SKIPPED, no file) | exact literal `:2186-2194` | yes, within the §4.3 retained class |
| README `The failure code is a fixed value` | `_mirror_code` `:2880-2885` | yes |
| JS `mirrored via webclaw (credits-exhausted)` | **none in the consumer** | F3 |

Q-FRESH: not applicable. Each Stop invocation re-reads the manifest, and the JS validates and renders from the same
object. Q-SCOPE: F2 and F4 are siblings or retained (§4.3/N4); F1, F3, F5, F6 and F7 are in scope.

## Evidence log

### E1 — refs and baseline (measured)

- `636dd297` = `636dd29708f61c3cd8b937d195f18f41dcc56616`, `e90833fd` = `e90833fde8c2fab112f0297e693a72848af5ba86`;
  one commit in range; worktree HEAD = e90833fd, tracked tree clean (only untracked reports).
- Diffstat: 7 files, +1318/-128 (`research_fanout.py` 359, `research-sweep-run.js` 51, gate 12, four test files).
- §5.3 in the reviewed worktree: pytest 4 files **417 passed, rc=0** (`/tmp/cr-e9/pytest.log`); ruff check rc=0;
  ruff format --check rc=0 (6 files); ty rc=0. Implementer's "417 passed" reproduced.
- Scratch harness: `git worktree add --detach /tmp/cr-e9/wt e90833fd`, run with the reviewed worktree's venv python;
  `m.__file__` = `/private/tmp/cr-e9/wt/python/src/dotfiles_setup/research_fanout.py` (tests and the hook both
  `sys.path.insert(0, <own repo>/python/src)`). Pristine control 417 passed rc=0.

### E2 — N2: Stop reason (code read, cited at `e90833fd`)

- `scripts/codex-research-gate.py:107` branches on `verdict.provisional_entries`; `:123-132` builds `listed` from
  `entry.source` + `via {entry.route}` only; `verdict.provisional`/`verdict.reason`/manifest are not read on this
  branch. `named`/`stop_hook_active` logic `:108-122` byte-identical to 636dd297 (only `:107` and `:123-132` in the hunk).
- Entries are built at `research_fanout.py:2342-2344` only after `_validate_provisional_row` passed:
  source ∈ `_SOURCE_NAMES` set-equality `:2319-2329`, ∈ `CREDIT_METERED_SOURCES` `:2125`, truthy route ∈
  `_FALLBACK_ROUTES[source]` `:2128-2131`. A falsy non-None route (`""`, `0`) renders nothing (`if entry.route`).
- Failed branch `:134-155` interpolates `verdict.reason`; every `_ReceiptError`/`_validate_*` message is fixed text
  plus a set-validated source (`:1954-1975`, `:2037-2053`, `:2107-2293`) — no receipt/provider text.
- **N2 holds.** Spot-check M-N2b (gate-only restore of the 636dd297 reason) → `1 failed, 416 passed` (T1 exact literal).

### E3 — N1 producer/consumer (code read + probes)

- Same function: producer `research_fanout.py:1525-1526` and consumer `:2203-2211` both call `_fallback_credit`
  (`:231-244`). Inputs differ only by redaction: the envelope body is `_redact_request_text(...)` (`:1438-1452`) while
  the producer classifies the unredacted body — divergence can only fail CLOSED (producer True, consumer False) and
  needs a credential VALUE overlapping the phrase or JSON syntax; not reachable for real keys (INFO, not probed).
- §8.A: `_validate_fallback_credit` `:2197-2211` catches `ValueError` (which `_ReceiptError` subclasses, `:2107`), so
  `malformed primary envelope|transport` never leaks into the fallback path; every failure → the one fixed reason.
  Bound/hash failure keeps its own reason (`_bound_raw` runs first, `:2174-2178`).
- T7 arms (tests `test_projection_fallback_skip_rederives_bound_transport`): genuine True; bare, 200-credit,
  400-no-credit, malformed, cli → exact fixed reason. Spot-check M-N1c → `2 failed, 415 passed` (exactly the 200-credit
  and 400-no-credit arms, as §8.A predicts). M-N1d → `1 failed, 416 passed` (missing-key "key gone" arm).
- Probe (scratch `tests/test_zz_cr_probe.py` in a `git archive e90833fd` copy, HOME real, fixtures `credit_env`):
  producer-made genuine receipt, serper evidence replaced by the 636dd297 bare body and its `status` relabelled:
  `skipped` → `(False, 'firecrawl-search fallback credit skip does not re-derive')` (control);
  `ok` / `empty_verified` / `bogus` → **`(True, 'provisional: …')`**; evidence-less missing-key relabel → `(True, …)`.
- Probe: serper **400** `{"message":"Invalid query: <query>"}` where the query contains `not enough credits` →
  serper `skipped`, strict **True** (provisional); control query `qx<fresh hex>` → serper `error`, strict False.

### E4 — JS copied-row scalar checks are load-bearing (probe, both arms)

- Forged mirror row `{code:'process-failed', rc|bytes|provisional: 'x '+sentinel}` through `_mandatory_run`:
  HEAD copy → `probe row failed validation`, sentinel absent from payload (control).
  Copy with `!Number.isInteger(m.rc) || !Number.isInteger(m.bytes) || typeof m.provisional !== 'boolean' ||` replaced by
  `false ||` → **sentinel in payload AND in the synthesize prompt**, 0 mirror gaps, for all three fields.
  So these three clauses (`research-sweep-run.js:507`) are the only barrier for those fields.

### E5 — mutation table (measured; `/tmp/cr-e9/mutate.py`, scratch worktree, all 4 §5.3 files per row)

Each row asserted its anchor `count == 1` before writing, ran the four §5.3 test files, then
`git -C /tmp/cr-e9/wt checkout -- <file>` and `git diff --quiet` (all 21 rows: `restored=yes`).

| Row | Kind | Result |
|---|---|---|
| PRISTINE | control | rc=0, 417 passed |
| M-N2b gate-only restore of the 636dd297 reason | claimed | **RED** 1 failed / 416 |
| M-N1c delete validator `_fallback_credit` call | claimed | **RED** 2 failed / 415 (the §8.A 200-credit + 400-no-credit arms) |
| M-N1d drop exact prerequisite-reason check | claimed | **RED** 1 failed / 416 |
| M-W1(route) `false && …` — note: by `&&`/`||` precedence this disabled ONLY the route clause | claimed (partial) | **RED** 1 failed / 416 |
| U-JS1 drop `Number.isInteger(m.rc)` | unclaimed | **GREEN** 417 |
| U-JS2 drop `Number.isInteger(m.bytes)` | unclaimed | **GREEN** 417 |
| U-JS3 drop `typeof m.provisional !== 'boolean'` | unclaimed | **GREEN** 417 |
| U-JS4 drop `required_failed` length cap | unclaimed | **GREEN** 417 |
| U-JS5 `codeText` set check → `m.code` | unclaimed | GREEN 417 (unreachable: codes validated at construction) |
| U-PY1 drop `transport.rc is not None` | unclaimed | GREEN 417 (dead: decoder `:2224-2228` forces rc None when status is int) |
| U-PY2 drop `type(http_status) is not int` | unclaimed | GREEN 417 (redundant: `_fallback_credit(None, …)` is False `:233`) |
| U-PY3 prereq skip: drop `status == SKIPPED` | unclaimed | **GREEN** 417 |
| U-PY4 prereq skip: drop `raw_sha256 is None` | unclaimed | **GREEN** 417 |
| U-PY5 summary prerequisite closed-set check removed | unclaimed | GREEN 417 (unreachable: only producer `:1606` uses `_prerequisite_reason` literals) |
| C-PY1 `_fallback_credit` reads only `message` | control | RED 2 failed |
| C-PY2 fan-out provisional cap removed | control | RED 1 failed |
| C-PY3 `_fallback_credit` 2xx guard removed (M-N1a-like) | control | RED 3 failed |
| C-JS1 §8.C empty-code clause removed | control | RED 2 failed |
| C-JS2 `provisional_invalid` ignored | control | RED 1 failed |
| C-JS3 `repoCheckGap` full_name shape check removed | control | RED 1 failed |

Spot-checked claimed mutations: 4/4 RED (implementer's 26/26 claim consistent for these rows). The claimed M-W1 is a
COARSE mutation (whole validation removed) — it goes red on the route/code arms only; the sharp per-field rows
U-JS1..3 survive, and E4 shows each of those three clauses is the sole barrier for its field.

### E6 — JS route/provisional cross-field (probe, HEAD copy)

`MIRROR_OK` overrides with `code: ''`, bytes 42 via `_mandatory_run`:
- `{route:'webclaw', provisional:true}` (control) → status `provisional`, `["…/a: mirrored via webclaw (credits-exhausted)"]`.
- `{route:'firecrawl', provisional:true}` → status `provisional`, the SAME "via webclaw" string (false route claim).
- `{route:'webclaw', provisional:false}` → status **`complete`**, provisionalRoutes `[]`, 0 mirror gaps.

### Not findings (checked and cleared)

- Redaction divergence: the producer classifies the unredacted body, while the consumer reads the `_redact_request_text`'d
  envelope body. A difference can only fail CLOSED, and only if a credential VALUE overlaps the phrase or JSON syntax.
  That is not reachable for real keys, and it was not probed.
- `_FALLBACK_KEYS[route]` KeyError in `_validate_fallback_prerequisite`: unreachable, because the route is already in `allowed` (`:2155-2161`).
- The fan-out probe silently truncates more than 8 provisional entries, while the JS rejects more than 8. This is reachable only from a forged manifest, since there are at most 4 metered sources.
- The planner/dependency `m.path` and `m.query` interpolations are agent-authored and retained by §4.3, unchanged from 636dd297.

### Harness and cleanup

- Probes: `git archive e90833fd python tests scripts .claude/workflows` → `/tmp/cr-e9/probe` (plus a mutated copy,
  `probe-mut`); scratch test `tests/test_zz_cr_probe.py`; reviewed-worktree venv python, `-p no:xdist -o addopts=""`.
- No source, test, fixture or config file in the reviewed worktree was edited. Only this report was written.
- Afterwards the scratch worktree `/tmp/cr-e9/wt` was removed (`git worktree remove`), along with `/tmp/cr-e9` (logs,
  harness and probe copies) and `/tmp/cr-e9-rf.py` / `/tmp/cr-e9-wf.js`. The results above are transcribed verbatim from those logs.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed diff `636dd297..e90833fd` (local worktree only; no API calls).
