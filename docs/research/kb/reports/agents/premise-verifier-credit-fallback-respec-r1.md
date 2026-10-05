# premise-verifier: credit-fallback respec r1 (verbatim hand-back)

PREMISE REPORT: credit-fallback respec r1 (`/Users/rmanaloto/.claude/jobs/a7139527/tmp/specs/spec-credit-fallback-respec-r1.md`), checked against worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/credit-fallback` at d7bb0da5.

This lane is read-only (no Write/Edit tools), so nothing went into findings.md. Please persist this report yourself.

**Overall: FIX FIRST.** All four listed premises are true. The blockers are three contradictions inside the spec: M-L1 vs M25, M5 vs the base spec, and M3 reversing ratified Q5 without saying so.

ROWS: 4 checked — 4 CONFIRMED (0 provenance corrected) / 0 REFUTED / 0 UNVERIFIABLE / 0 ASSUMED

- **P1 — CONFIRMED.** `_CREDIT_TEXT` is at `python/src/dotfiles_setup/research_fanout.py:116-120`. The bare-402 disjunct is at `:134`: `return bool(_CREDIT_TEXT.search(text) or re.search(r"\b402\b", text))`. It is consumed by `_attempt_credit` at `:1286-1297` and re-used by receipt re-derivation at `:2035`.
- **P2 — CONFIRMED.** The provisional branch is at `scripts/codex-research-gate.py:106-114`: a `systemMessage` ending "Say so in the answer.", with no `decision`. The fail branch at `:115-132` already reads `stop_hook_active` and `last_assistant_message`.
- **P3 — CONFIRMED.** `.claude/workflows/research-sweep-run.js:631`: `if (planManifests.length && planManifestProbe === null) fanoutGaps.push('planner provisional check did not run')`. `readProbe` (`:182-190`) returns null for both a null node and a malformed line. The status list is at `:855-862`; `fanoutGaps` does not feed it.
- **P4 — CONFIRMED.** The regex is at `research_fanout.py:669-673`, class `[^\s\"<>]*`, which admits `\`. It runs before decode at `:636` (`_run_json`, then `_decode_json` at `:647`). It is also called at `:943` (fallback body), `:1305/:1308` (envelope), `:1326`, `:2475`, `:2480` (webclaw markdown) and `:2528` (scrape stdout).

**§3 cross-check against the two reports.** Every finding ID matches its report:
- M1 = R-A F1 + R-B F2
- M2 = R-A F6 (LOW) + R-B F1 (MED)
- M3 = R-A F2 + R-B F3
- M4 = R-A F3
- M5 = R-B F4
- M-L1 = R-A F4 + R-B F7
- M-L2 = R-A F5 + R-B F6
- M-L3 = R-A F7 + R-B F5
- M-L4 = R-A F8. Its "fallback `limit`" is R-A's M20, at `research_fanout.py:958`.
- M-L5 = R-A F9
- M-L6 = R-A F10 + R-B F11
- M-L7 = R-A F11 + R-B F9
- M-L8 = R-B F8
- Deferred: R-A F12 and R-B F10.

The line anchors hold at the code:
- `:1852` dead `success` set
- `:1366-1374` broad except that produces "request failed"
- `:1909-1929` `_provisional_line`, which says "no fallback route" and lists only ERROR attempts
- `:1587` `--out type=Path`; the only `expanduser` is at `:1100`
- guards: M3 `:2049`, M5 `:1937`, M24 `:2060`, M25 `:2068`, M23 `:636`, M30 `:2480`
- the retrospect string at `research-sweep-run.js:331`
- the AGENTS.md claim at `python/src/dotfiles_setup/AGENTS.md:26-27`
- Codex `hooks.md:423`

One small drift: R-A cites `hooks.md:921-924` for the continuation semantics; the text is at `:923-925`.

**MISSING (unstated premises):**

1. **M3 vendor support: CONFIRMED, cite it.** Stop input has `stop_hook_active` ("Whether this turn was already continued by `Stop`") and `last_assistant_message` (type `string | null`) at `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/hooks.md:905-906`. `decision: "block"` plus `reason` becomes a new continuation prompt (`:914-925`). `systemMessage` is UI-only (`:423`). Two gaps for the spec:
   - (a) The message can be null; say that null counts as "not named", so the hook blocks.
   - (b) `stop_hook_active` is also true after an earlier INCOMPLETE block, so a provisional pass that follows one will not block. Accept or state that.
2. **M3 "name of every provisional route" is undefined (load-bearing).** `StrictVerdict.provisional` (`research_fanout.py:1905`) holds whole lines, including the reason, and has no route names. A skip with no route, like the hook test's firecrawl-developer row, has no route at all, only a source. The spec must define the token to match: the source name, plus `via <route>` when a route exists. Otherwise the implementer must either parse the lines or extend `StrictVerdict`.
3. **M3 inverts an existing test and overrides ratified Q5 (load-bearing).**
   - `tests/test_codex_research_gate.py:238-241` asserts there is no `decision` on a provisional Stop.
   - The base spec, `spec-credit-fallback-rev2.1.md:356`, says "(Q5, ratified: non-blocking)", and `:505` repeats it.
   - The base R4 at `:638` expects "a `PROVISIONAL` systemMessage".
   - The respec must say it overrides Q5 and R4, and Ray's re-ratification must be on record.
4. **M-L1 "OK with 0 records" contradicts the code and M-L4/M25 (load-bearing).**
   - An empty fallback today goes to the empty-control path, which gives EMPTY_VERIFIED/UNVERIFIED, not OK (`:1382-1389`).
   - The receipt validator rejects a missing `organic_results` key (`:2066-2067`).
   - It also rejects OK with empty records (`:2068`). That is exactly the M25 guard M-L4 asks the lane to pin.
   - Restate it: a documented SerpApi empty-state response is treated as `records = []`, goes through the existing empty-control path, and `_validate_credit_output` accepts that shape.
   - The SerpApi empty-response shape itself is unverified: no doc URL in either report.
5. **M-L1 Serper status (load-bearing for M-L1).** `is_credit_exhaustion` returns False for any status other than 402, 429 or None (`:135`). Serper's HTTP status for "Not enough credits" is unverified: R-A F4 says so, and R-B F7's "400" is from memory. Adding the phrase to `_CREDIT_TEXT` will not fire if Serper answers 400 or 403. The spec must either verify the status or allow text-based classification on the fallback HTTP route.
6. **M1 trigger set is ambiguous.**
   - Today `_CREDIT_TEXT` mixes credit phrases with "quota exceeded" and "exceeded your quota". Say which phrases count on a status-None CLI failure; the M1 prose implies quota wording counts only with a 429.
   - Say whether a "429" in CLI text must also be structurally identified.
   - The real search fixture is `"status":402` (`tests/fixtures/research_fanout/firecrawl-402-search.err:1`), not `"statusCode": 402`.
   - Both fixtures also carry "Insufficient credits", so they keep classifying either way. Existing tests use a structured `http_status` 402 (`test_codex_research_gate.py:162`).
   - Re-derivation (`:2035`) reuses the predicate, so a d7bb0da5-era manifest whose only evidence is a bare 402 will now fail. That fails closed and is fine, but name it.
7. **M2 must keep value redaction on stdout.** `_redact_text` also does credential-value replacement (`:657-667`). That stdout redaction is the M23 guard M-L4 pins. Only the URL substitution should move.
   - The persisted raw bytes are hashed and later decoded by the receipt (`:2064`). Specify that the raw evidence written to disk stays valid JSON and is the redacted form that gets hashed.
   - Whether a SerpApi response echoes `api_key` in any URL is unverified. The value-replace already covers a literal key value.
8. **M4 overrides the base spec and inverts a test.**
   - The base spec (`rev2.1.md:423-424`) says "Do not treat this as a mandatory gap."
   - `tests/test_workflows_js.py:1397-1410` asserts `mandatoryGaps == []` and documents "without a mandatory gap".
   - Name both as overridden and require the test to be inverted, including a `status` assertion.
9. **M5 vs the base spec (load-bearing).**
   - The base spec says R1–R4 "run from the main session" (`rev2.1.md:625`).
   - It also says the lane leaves the tree uncommitted for the architect (`:652-653`).
   - So "re-run if the base spec allows" means the lane may not run them, and the base spec has no R1–R4 values, only expectations.
   - R4's expectation is stale after M3.
   - Decide: either the coordinator runs R1–R4 before the commit and hands the lane the values, or the lane's commit body says "not run" and the architect amends it. As written, the commit cannot carry them.
10. **M-L6 alternative is a trap.** Reverting `--out` to an absolute path risks the ≤1000-character submit test (`test_codex_research_gate.py:255-283`, long REPO_ROOT; base `rev2.1.md:367`). Mutation G2 already pins the relative form. Specify `expanduser()` only.
11. **Deployment (non-blocking, coordinator).** R-A Q-SCOPE notes the live Codex hook runs the clone `~/.codex/tools/dotfiles-research-gate` (still v1). M3 does nothing in live Codex until O1 (`rev2.1.md:641-642`) runs. Track it as a ticket or operator step.

**VERDICT: correct the spec first.** Items 2, 3, 4, 5 and 9 block. Exact fixes:

- **(a) M3:** define the match token (source, plus `via <route>`). Treat a null message as unnamed. State the override of Q5 (`rev2.1.md:356`) and R4 (`:638`) with Ray's re-ratification. Name the test to invert (`test_codex_research_gate.py:238-241`). Cite `hooks.md:905-906` and `:914-925`.
- **(b) M-L1:** replace "OK with 0 records" with "empty → existing empty-control path; `_validate_credit_output` accepts the documented SerpApi empty shape". Keep M25. Require a doc URL for the empty shape and for Serper's credit-exhaustion HTTP status, or allow text classification on the fallback route whatever the status.
- **(c) M5:** decide who runs R1–R4 (the base spec says the coordinator) and restate R4's expected output for the blocking hook.
- **(d) M1:** split credit phrases from quota phrases and say which apply with no status. Note that the real fixture form is `"status":402`.
- **(e) M2:** keep value redaction on stdout (M23), and require that the hashed raw evidence stays valid JSON.
- **(f) M4:** name the base clause `rev2.1.md:423-424` and the test `test_workflows_js.py:1397-1410` as overridden or inverted.
- **(g) M-L6:** drop the "absolute path" alternative.
- **(h)** Record item 11 as a named non-blocking residual.


## Round 2 (verbatim)

ROUND 2 — §8 (rev r1.1) re-check of `/Users/rmanaloto/.claude/jobs/a7139527/tmp/specs/spec-credit-fallback-respec-r1.md`

**FIX FIRST.** Seven of the eight corrections close their blocker cleanly. Fix (b) adds a new contradiction, and a one-line scoping fix clears it.

**(b) M-L1 introduces a new contradiction.** The fix says to classify the provider phrases as credit exhaustion "WHATEVER the HTTP status". If the lane puts that into the shared `is_credit_exhaustion` (`research_fanout.py:127-135`), it breaks things that are pinned today:
- **The classifier test table.** `tests/test_research_fanout.py:2062-2065` asserts that `(401, "Insufficient credits")`, `(403, "out of credits")`, `(500, "payment required")` and `(200, "Insufficient credits")` are all NOT credit. That is the base spec's §4.1 rule that genuine errors are never laundered.
- **The R2 auth arm**, which expects a primary 401 to stay an error.
- **Receipt re-derivation** at `:2035`, which reuses the same predicate.

The rest of (b) is fine: the empty-control path, keeping M25, and the doc-or-residual rule for the SerpApi empty shape all close blocker 4.

Exact fix — add to (b): "The status-independent rule applies ONLY to fallback-route attempts (serper/serpapi, in `_credit_result`'s loop at `:1375-1381`) and ONLY to those two phrases. Implement it outside `is_credit_exhaustion`, and do not change the existing table rows at `test_research_fanout.py:2059-2067`. Add a primary-route arm, `(401, "Not enough credits")` → not credit, plus one fallback arm per phrase at a non-402/429 status."

**(d) M1 needs one clarifying line.** Today's `_CREDIT_TEXT` (`:116-120`) also matches "payment required" and "out of credits". §8 lists the no-status credit phrases without saying whether those two stay. Exact fix: "the list is exhaustive; 'payment required' and 'out of credits' are dropped (or: retained)." The rest of (d) closes blocker 6: the structural-token rule and the real fixture form `"status":402` (`firecrawl-402-search.err:1`).

**The other six close their blockers:**
- **(a) M3** closes blockers 2 and 3. The structured fields go on `StrictVerdict` (`:1901-1906`), which is in the allowlist. A null message blocks. The `stop_hook_active` limitation is accepted on record. The test to invert is `test_codex_research_gate.py:238-241`. The doc citations match the vendor docs (`hooks.md:423`, `:905-906`, `:914-925`).
- **(c) M5** closes blocker 9 and matches the base spec (`rev2.1.md:625`). R4 is restated to expect a block. The coordinator amending the body later is consistent with §6, since nothing has been pushed.
- **(e) M2** closes item 7. It keeps the M23 credential-value redaction and requires that the hashed raw evidence stays valid JSON.
- **(f) M4** closes item 8. It names `rev2.1.md:423-424` and the test `test_workflows_js.py:1397-1410`.
- **(g) M-L6** closes item 10. Only `expanduser()` remains, which protects the ≤1000-character submit test.
- **(h)** records the deployment item as a named residual. The live Codex hook runs the `~/.codex/tools/dotfiles-research-gate` clone, so M3 has no effect there until the O1 pull.

Once the (b) scoping line is in, and ideally the one-line (d) clarification, the spec is DISPATCH-READY.
