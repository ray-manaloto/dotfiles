PREMISE REPORT: spec-credit-fallback-projection-r1.md, checked against worktree credit-fallback @ 636dd297

I had no Bash or write tools, so nothing was persisted. The coordinator should save this report verbatim. I ran no git, test or mise commands, which is why P2 and P38 stay assumptions.

ROWS: 40 checked. 34 CONFIRMED (0 provenance corrected), 1 REFUTED, 0 UNVERIFIABLE, 5 ASSUMED (0 checkable).

All paths below are in the worktree. Shorthand: `fanout` = python/src/dotfiles_setup/research_fanout.py, `gate` = scripts/codex-research-gate.py, `wf` = .claude/workflows/research-sweep-run.js, `probe-test` = tests/test_research_fanout_probe.py, `fanout-test` = tests/test_research_fanout.py, `wfjs-test` = tests/test_workflows_js.py.

**Row verdicts**
- **P1 — CONFIRMED.** `.git/packed-refs:173` has `636dd297… refs/heads/feat/research-credit-fallback`, and `.git/worktrees/credit-fallback/HEAD:1` points at that ref. No loose ref overrides it. Control: a Glob of `.git/refs/heads/**` does list four other loose refs.
- **P2 — ASSUMED.** "The worktree is clean." Not checkable without git. The coordinator must confirm it.
- **P3 — CONFIRMED.** `gate:123-130` sets `"reason": … + "; ".join(verdict.provisional)`.
- **P4 — CONFIRMED.** Tokens are built at `gate:109-116`; the `named` test with lookarounds is at `gate:117-120`; the `stop_hook_active` allow is at `:121-122`. The spec's "`named` is exactly :117-122" is off by two lines. Harmless.
- **P5 — CONFIRMED.** `gate:132-149`.
- **P6 — CONFIRMED.** KB `codex/hooks.md:905` (`stop_hook_active`) and `:923-925` ("creates a new continuation prompt that acts as a new user prompt, using your `reason`").
- **P7 — CONFIRMED.** `fanout:1393-1399`.
- **P8 — CONFIRMED.** `fanout:1430-1437` searches the whole body; `[-300:]` is applied to the raw body.
- **P9 — CONFIRMED.** `fanout:993-996`.
- **P10 — CONFIRMED.** `fanout:137-147`.
- **P11 — CONFIRMED.** `fanout:1454-1464` appends `final.raw`; `:1807-1827` hashes the evidence; the status lives only in RouteAttempt.
- **P12 — CONFIRMED.** `fanout:1341-1354` uses sort_keys. `_Attempt.rc` defaults to None (`:270`), so a fallback envelope's `rc` will be null.
- **P13 — CONFIRMED.** `fanout:2065-2073` (an evidence-less SKIPPED attempt passes), `:2120-2128`, `:2151`.
- **P14 — CONFIRMED.** `fanout:2129-2136`.
- **P15 — CONFIRMED.** `fanout:2023`, `:2026-2029`, `:2053-2059`, `:2186-2196`, `:2207-2211`.
- **P16 — CONFIRMED.** `fanout:1977-2002`.
- **P17 — CONFIRMED.** `fanout:2491-2493`, `:2505` (`sources` raw), `:2511-2512`.
- **P18 — CONFIRMED.** `fanout:2774-2778`.
- **P19 — CONFIRMED.** `fanout:2892-2920` and `probe-test:117-118`. Note that `:117-118` is a code-search-only test (see P31).
- **P20 — CONFIRMED.** `fanout:2554-2556`, `:2610`, `:2634-2636`.
- **P21 — CONFIRMED.** `fanout:2711`, `:2742`.
- **P22 — CONFIRMED.** `fanout:2923-2940`, `:2986-2989`.
- **P23 — CONFIRMED.** Every §3.1 literal is at its cited line: `:319`, `:331`, `:337`, `:630`, `:661`, `:704`, `:769/:771/:776`, `:802`, `:877`, `:881`, `:987`, `:991`, `:995`, `:1044`, `:1186`, `:1203-1221`, `:1265`, `:1384`, `:1418`, `:1552-1556`, `:2524-2561`, `:2580-2587`, `:2641-2667`.
- **P24 — CONFIRMED.** `fanout:2255`.
- **P25 — CONFIRMED.** A grep for `FailureCode|failure_code|FAILURE_CODES|_fallback_credit|_transport_envelope|_PREREQUISITE_TEXTS` over `*.{py,js}` found 0 files. Control: `_FALLBACK_CREDIT_TEXT|_attempt_credit` found 1.
- **P26 — CONFIRMED.** `wf:182-190`.
- **P27 — CONFIRMED.** `wf:481-485`, `:497-503`, `:635-641`, `:679`, `:737`, `:747-751`.
- **P28 — CONFIRMED.** `wf:321-337`.
- **P29 — CONFIRMED.** `wf:125-126`.
- **P30 — CONFIRMED.** `wfjs-test:189-205`, `:224-226`. `MIRROR_OK` currently emits `reason: ''`.
- **P31 — REFUTED, in part.** `probe-test:102-118` is `test_code_search_records_the_real_count…`. Its only probe is code-search (`:105-108`) and it has no mirror row, so `on_disk == payload` at `:118` encodes no diagnostic and stays true under U4 unchanged. The other cited lines do encode raw diagnostics, but the list is incomplete (see MISSING).
- **P32 — CONFIRMED.** `tests/test_codex_research_gate.py:19-33` (`_invoke` sets `HOME` and copies `os.environ`) and `:288-384`. The gate puts the worktree's `python/src` first on `sys.path` (`gate:14-15`), so the tests exercise this worktree's module.
- **P33 — CONFIRMED.** `fanout-test:2802-2804`.
- **P34 — ASSUMED.** The real provider bodies use a top-level `message`/`error` field. The code does not contradict this: `fanout:949` cites the SerpApi docs, and `fanout-test:2816-2817` marks Serper as unverified.
- **P35 — CONFIRMED.** `fanout-test:2056-2094`.
- **P36 — ASSUMED.** `output.md:19` says the SDLC review reproduced only the emitted hook JSON.
- **P37 — ASSUMED.** The cold review's `:135`, `:140`, `:151` and `:165-166` say what the spec claims. Consistent with that: the gate parametrize table (`:288-310`) has no `exa`/`exactly` boundary case, and the only cap asserts (`fanout-test:2562-2563`) cover the primary reason, not the fallback reason. I did not read the ctx7 source.
- **P38 — ASSUMED.** The cold review records 331 passed at `:17-18` and `:104`. Not re-measured.
- **P39 — CONFIRMED.** A grep excluding `docs/**` hits only the gate, the workflow, the module, the 2 tests and `mise.toml`. It also hits `session_ledger.py:4316`, but that is an unrelated `_primary_reason`. No `suites.toml`/`.pkl` contract pins these files (control: `mise.toml:890` matched).
- **P40 — CONFIRMED.** Under `.claude/`, `NO MIRROR` and `failure reason` occur only in the workflow and the module.

**Injection-path table coverage (`output.md:25-41`).** Every row is either changed in §3 or named:
- The failed-receipt Stop reason is named as unchanged in §3.2.
- The `systemMessage`, `additionalContext`, `last_assistant_message`, retrieved-results, derived-prose and write-error rows are in §4.3.
- The PROBE-JSON, provisional→synthesis, mirror-primary, fanout→dependency-gaps, mirror/redirect, CLI-summary and README rows are in §3.5/§3.6.

No uncovered row.

**Rows that block (also listed under MISSING)**

A. **T7 / M-N1c contradicts the code it reuses.**
- §3.4 says to factor the envelope decode out of `_credit_envelope`. That code raises `"malformed primary envelope"` / `"malformed primary transport"` (`fanout:2092`, `:2098`), and `_decode_json` raises a ValueError that `strict_five_verdict` maps to `"malformed or unreadable research evidence"` (`fanout:2212-2216`).
- So a 636dd297-era bare-body receipt is rejected with one of those texts, not with `fallback credit skip does not re-derive` as T7 asserts.
- And because a bare body already fails the envelope shape check, deleting only the `_fallback_credit` call (M-N1c) leaves T7 GREEN. The mutation survives.
- Fix: map every decode or shape failure of a credit-SKIPPED fallback attempt to `fallback credit skip does not re-derive`. Add a T7 arm with a well-formed envelope that does not re-derive (for example `http_status: 200` with the credit phrase, or `400` without it), so that M-N1c has something to kill.

B. **T4's first mutation cannot produce the predicted RED.**
- Delete the route check at `fanout:2027-2029` and a route of `"serper; <sentinel>"` is still rejected. Attempt routes must be in `allowed` (`:2057-2059`), so no attempt can match the row route, and `_validate_credit_output` raises `missing winning route evidence` (`:2129-2136`).
- That reason is fixed text, so the sentinel never appears.
- Fix: T4 must pin the exact reason `firecrawl-search invalid fallback route`, or the row should be dropped as a redundant check.

C. **A JS mirror row with `code: ''` that is not mirrored has no rule.**
- §3.6 drops the `wf:498` fallback text (`rc=…, … bytes`) and keys `mirrorGaps` on the code. A row with rc 0, 0 bytes and code `''` (allowed by the §3.6 validation) would be neither mirrored nor a gap. That fails open.
- §5.2's `:2354/:2359 → (NO MIRROR: empty-output)` cannot come from the `MIRROR_OK` stub, whose default code is `''`.
- Fix: specify that a not-mirrored row with code `''` becomes `empty-output`, or is invalid (`invalid-probe` plus a gap).

**MISSING**
- **T7/M-N1c and the decode helper's reason texts** (A above). Load-bearing; must be fixed.
- **T4 route-mutation mechanism** (B above). Load-bearing for the mutation table: the lane is told to stop when a premise is false.
- **JS empty-code, not-mirrored row** (C above). Load-bearing because it fails open.
- **§5.2 omissions in `fanout-test`** (each asserts raw diagnostics on a projected path):
  - `:734` asserts `"first line | second line | third" in lines[1]`, but the summary will now read `[process-failed]`.
  - `:2535` and `:2538` assert `"serper: HTTP 500"` in stdout and in the strict reason; both become `serper: http-error`.
  - `:2833` asserts `"not inherited" in output`; the projected provisional line has `<route>: prerequisite` instead. The U7 hint applies only to non-provisional rows.
- **§5.2 omissions in `probe-test`:**
  - `:635` reads `row["reason"]` from the on-disk probe, which will KeyError once `reason` moves into `detail`.
  - `:740`, `:750` and `:753` assert on the stdout row's `reason`; these become `code` checks (non-empty, `not-found`, `timeout`).
  - `:771-773` expects provisional line strings; these become structured `{source, route}` entries.
  - `:686` reads the stdout payload, which has no `detail`, so "moves to `detail.primary_reason`" needs it to read the on-disk file.
- **§5.2 omissions in `wfjs-test`.** The `required_failed` fixtures below fail the new §3.6 regex, so the workflow replaces each with `unrecognised required_failed entry`. That replacement drops the `<source>:` prefix that the disabled-tracker filter at `wf:482` needs.
  - `:1579` and `:1583-1588` use `(exited 1: HTTP 422)`.
  - `:2918` and `:2930` use `(canary returned 0 items)`, which should be `(canary-empty)`.
  - `:3029` and `:3039` use `(exited 1: HTTP 403)`.
  - Update these fixtures to projected forms, and state that the validation runs before the `:482` filter. §5.2's catch-all clause covers this, so it is not blocking.
- **JS consumer does not re-validate `repo-check.full_name`.** U8 filters it in Python, but `wf:519-523` interpolates `full_name` into mandatory gaps, and the §3.6 table has no row for it, although decision note 3 requires re-validation at the copied-JSON consumer. JS already has `REPO_SHAPE` (`wf:105`). Non-blocking: the field is GitHub-shaped after the Python filter, and other copied scalars (`count`, `rc`, `age_s`) are not re-validated either.
- **T6(e) does not pin a status.** At 402, or at 429 with a nested phrase, `is_credit_exhaustion` returns True from a whole-body `_CREDIT_TEXT` search (`fanout:141-144`). Pin (e) to 400 or 403, or M-N1b cannot discriminate. Non-blocking; a one-line fix.
- **U8 strip order.** `full_name` must be `.strip()`ped before `_REPO_SHAPE.fullmatch`, or `probe-test:212` (`"jdx/mise\n"` → `"jdx/mise"`) breaks. Non-blocking.
- **Unstated: test environment isolation.** Every key is in the shell env (`secrets-out-of-the-shell-env.md`), and `gh`/`ctx7`/`firecrawl` on PATH change the prerequisites (`fanout:1203-1221`). New T6–T9 and T16 tests must use the `credit_env` fixture (`fanout-test:2037-2053`) or `mirror_credit_env` (`probe-test:566-570`). T9's prerequisite arm needs `EXA_API_KEY` unset. Non-blocking: the fixture exists.
- **Unstated: the Bun harness.** `wfjs-test:355-360` runs `mise exec -- bun` from the worktree, so it needs the worktree's mise config trusted and `bun` installed. The cold review's 331-pass baseline ran in a worktree. Non-blocking residual.
- **Unstated: no CI host gates.** None of the four test files has a `platform`/`skipif`/`CI` gate. Control: `skipif` exists in `test_renovate_validate.py` and `test_fnhook_gates.py`, so the probe discriminates. No argv-index hazard: the new rows add no argv positions. Non-blocking.
- **Unstated: double redaction.** The validator re-derives credit from a body redacted twice (`fanout:985`, then `_transport_envelope`'s `_redact_request_text`), while the producer classifies the once-redacted raw. Redaction only replaces credential values and request URLs, so it is idempotent for the `message`/`error` phrase. Non-blocking.

**Non-blocking residuals that must be named (all ASSUMED rows, plus the rest)**
- P2: the coordinator must confirm `git status` is clean.
- P34: if Serper or SerpApi exhaustion arrives in another field shape, U2 fails closed by design (visible ERROR).
- P36: live Codex continuation was never reproduced; covered by §5.4 R4.
- P37: N3–N5 come from the cold review; consistent with the tests I read.
- P38: the baseline is inherited; the lane's targeted pytest re-measures it.
- The `full_name` JS re-validation, T6(e) status, U8 strip order, environment isolation, Bun/mise trust and double redaction items above.

VERDICT: **FIX FIRST.** Before dispatch, correct T7/M-N1c (the reason text must agree with the shared decode helper, and an envelope-shaped non-re-deriving arm is needed so the mutation can fail), T4's route mutation (pin the exact reason or drop the row), and the JS rule for a not-mirrored `code: ''` row. Also correct P31's `:117-118` entry and fold the listed §5.2 omissions into the spec.

