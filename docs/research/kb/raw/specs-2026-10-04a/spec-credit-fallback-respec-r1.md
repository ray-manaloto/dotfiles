# credit-fallback — respec round 1 (fixes over d7bb0da5)

Coordinator: a7139527. Max 2 respec rounds; this is round 1.
Base spec (still binding except where this respec overrides it):
`/Users/rmanaloto/.claude/jobs/a7139527/tmp/specs/spec-credit-fallback-rev2.1.md`.
Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/credit-fallback`,
branch at d7bb0da5. Work ONLY there.

Two cold reviews returned DO NOT SHIP. Read both in full first (untracked, in the worktree):
- R-A: `docs/research/kb/reports/agents/cold-review-credit-fallback-d7bb0da5.md` (F1–F12; it has a
  41-row mutation table: M-numbers referenced below).
- R-B: `docs/research/kb/reports/agents/cold-review-credit-fallback-d7bb0da5-lane2.md` (F1–F11).

## 1. Objective

Fix every MEDIUM and the listed LOW findings so that a re-review can return SHIP.

## 2. Files (allowlist)

`python/src/dotfiles_setup/research_fanout.py`, `scripts/codex-research-gate.py`,
`.claude/workflows/research-sweep-run.js`, `python/src/dotfiles_setup/AGENTS.md`,
`tests/test_research_fanout.py`, `tests/test_research_fanout_probe.py`,
`tests/test_codex_research_gate.py`, `tests/test_workflows_js.py`,
`tests/fixtures/research_fanout/**` (new fixtures allowed). Nothing else. Do not touch the two
review reports.

## 3. Required changes

MEDIUM (all must land):

- **M1, credit classification (R-A F1, R-B F2).** Delete the bare `\b402\b` disjunct
  (`research_fanout.py:~134`). On CLI routes, classify credit exhaustion only by these triggers:
  - an HTTP 402 status that is structurally identified (a status field or line, e.g.
    `status code 402` / `HTTP 402` / `"statusCode": 402`), never a `402` inside a URL, id or query;
  - a 429 whose text carries quota/credit wording;
  - the documented credit phrases (`Insufficient credits`, plus the provider phrases in M-L1).

  A transient "rate limit"/"quota exceeded" with no credit wording on a 429-less failure stays an
  ERROR. Tests: `…/issues/402` in stderr → ERROR, not a skip. Both arms.
- **M2, redaction (R-A F6, R-B F1).** The Serper/SerpApi request-URL redaction must not corrupt
  other sources' JSON. Redact decoded string values after JSON decode (or make it escape-aware), and
  only where a Serper/SerpApi URL/key can appear. A gh payload containing
  `href=\"https://serpapi.com/search.json?…\"` must still decode. Both arms.
- **M3, Stop hook enforcement (R-A F2, R-B F3).** In `scripts/codex-research-gate.py:~106-114`:
  - On a provisional pass whose `last_assistant_message` does not contain `PROVISIONAL` and the
    name of every provisional route, return a Stop **block** (`decision: block` with a reason
    naming the routes) once. Use the hook's stop-loop flag (`stop_hook_active`) so it blocks at most
    once per stop cycle.
  - If the message already names them, allow.
  - Verify the Codex Stop-hook input and output field names against the vendor docs on disk
    (`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/`) and cite
    the file:line in the commit body.
  - Make the AGENTS.md claim match what is enforced.
- **M4, workflow status (R-A F3).** In `research-sweep-run.js:~631`: when the planner
  provisional-check node returns null or a malformed line, the run status must not be `complete`.
  Treat it like the dependency-stage `no PROBE-JSON line` MANDATORY gap. Add a test.
- **M5, commit body (R-B F4).** The new commit body must carry:
  - the provider-doc URLs for the Serper and SerpApi request shapes;
  - the SerpApi `num` deviation;
  - the R1–R4 live-arm rc values and manifest paths (from the base spec's verification section).
    Re-run them if the base spec allows.

  If a live arm cannot run (credits/network), say so explicitly and do not claim it.

LOW (fix in this round):

- **M-L1 (R-A F4, R-B F7).** Classify the fallback providers' own exhaustion:
  - SerpApi HTTP 429 `Your account has run out of searches` → skip;
  - Serper `Not enough credits` → skip;
  - a SerpApi response without `organic_results` but with a valid empty search → OK with 0
    records, not ERROR.

  Cite the provider docs.
- **M-L2 (R-A F5, R-B F6).** Cap credit `reason` / `primary_reason` at 300 chars, matching the
  base cut.
- **M-L3 (R-A F7, R-B F5).** `_provisional_line` must list the skipped fallback attempts and their
  cause (e.g. key not inherited), and must say "no fallback route" only when none is configured.
- **M-L4 (R-A F8).** Pin each of the 7 unpinned guards (M3, M5, M23, M24, M25, M30 and the fallback
  `limit`) with a test that fails when the guard is deleted. Report the mutation pairs.
- **M-L5 (R-A F9).** The fallback loop preserves the specific credential/`_HttpBodyError` reason
  instead of `request failed`.
- **M-L6 (R-A F10, R-B F11).** `--out` gets `expanduser()` (or the injected command reverts to an
  absolute path) so a quoted `~` path works.
- **M-L7 (R-A F11, R-B F9).** Remove the dead `serper`/`serpapi` entries from the `success is True`
  set.
- **M-L8 (R-B F8).** Fix the retrospect prompt so a `provisional` status is not called an
  incomplete run.

Deferred to tickets (do NOT fix; the coordinator files them): R-A F12 (prose clauses without
enforcement) and R-B F10 (webclaw HTTP-status check).

## 4. Constraints

- HOST SLOT: another heavy run may own the host. Run ONLY targeted tests:
  `uv run --project python pytest tests/test_research_fanout.py tests/test_research_fanout_probe.py
  tests/test_codex_research_gate.py tests/test_workflows_js.py -q`, plus `ruff check` / `ruff format
  --check` / `ty check` on the touched python files.
- Do NOT run the full suite, `mise run lint`, `mise run verify`, ship, land or container ops.
- No inline suppressions (`noqa`, `type: ignore`, …).
- No `--no-verify`.
- Never print credential values. Use `fnox exec` for any live arm.

## 5. Verification

Report:
- the targeted pytest rc and counts;
- the ruff/ty rc;
- a mutation table (each MED fix and M-L4 guard: delete it → which test fails);
- the live-arm results (or why each was not run).

## 6. Commit

Make ONE new commit on top of d7bb0da5 (not an amend):
`fix(research): credit-fallback review round 1 (classification, redaction, Stop enforcement)`, with
the M5 evidence in the body. Do not push.

## 7. PREMISES

- P1: `_CREDIT_TEXT` and the bare-402 disjunct live near `research_fanout.py:116-135` (R-A F1, R-B
  F2/F7).
- P2: The Stop hook's provisional branch is at `scripts/codex-research-gate.py:106-114` (R-A F2).
- P3: The planner provisional-check status handling is near `research-sweep-run.js:631` (R-A F3).
- P4: The redaction regex is at `research_fanout.py:~670` and runs before JSON decode (R-A F6, R-B
  F1).
- Re-verify each before editing. If a premise is false, stop and report rather than guess.

## 8. BINDING CORRECTIONS (rev r1.1, after premise verification — these OVERRIDE §3–§6 where they conflict)

Premise report: `docs/research/kb/reports/agents/premise-verifier-credit-fallback-respec-r1.md` (in the worktree).

- **(a) M3.** RAY RE-RATIFIED, 2026-10-04 ~00:0x CDT: "Block once if unnamed". This OVERRIDES base Q5
  (`rev2.1.md:356`, `:505`) and the base R4 expectation (`:638`).
  - Match token, per provisional entry: its source name, plus `via <route>` when a route exists.
    Extend `StrictVerdict` (or its provisional entries) with structured source/route fields rather
    than parsing the human lines.
  - The hook blocks when `last_assistant_message` is null, lacks `PROVISIONAL`, or lacks any token.
  - Accepted limitation: `stop_hook_active` is also true after an earlier INCOMPLETE block, so a
    provisional pass right after one does not block. Document it in AGENTS.md.
  - Invert `tests/test_codex_research_gate.py:238-241`.
  - Cite codex `hooks.md:423`, `:905-906` and `:914-925`.
- **(b) M-L1.**
  - An empty fallback result goes through the EXISTING empty-control path
    (EMPTY_VERIFIED/UNVERIFIED, `:1382-1389`), never OK with 0 records. Keep the M25 guard (`:2068`).
  - `_validate_credit_output` must accept the documented SerpApi empty-state shape. Find its doc
    URL; if no doc exists, leave the missing-`organic_results` rejection and record it as a residual.
  - On the fallback HTTP route, classify the provider phrases ("Your account has run out of
    searches", "Not enough credits") as credit exhaustion WHATEVER the HTTP status, because the
    Serper status is unverified.
- **(c) M5.** The lane does NOT run R1–R4 (base `rev2.1.md:625`: the main session runs them).
  - Its commit body carries the provider-doc URLs and the SerpApi `num` deviation, plus the literal
    line `R1-R4: not run by the lane; coordinator appends results`.
  - The coordinator runs R1–R4 after the commit and amends the body.
  - Restated R4 expectation: the provisional Stop returns `decision: block` naming the source/route,
    once.
- **(d) M1.**
  - CREDIT phrases ("Insufficient credits", "credits exhausted", "Not enough credits", "run out of
    searches") count with no status.
  - QUOTA phrases ("quota exceeded", "exceeded your quota") count ONLY with a structurally
    identified 429.
  - A structural 402/429 means a status token: `"status":402`, `"statusCode": 402`,
    `status code 402`, `HTTP 402` (the real fixture is `"status":402`, in
    `tests/fixtures/research_fanout/firecrawl-402-search.err:1`).
  - Note in the commit body: a d7bb0da5-era manifest whose only evidence is a bare 402 now fails
    re-derivation (`:2035`). This fails closed, which is accepted.
- **(e) M2.** Only the Serper/SerpApi URL substitution moves. Credential-VALUE redaction of stdout
  (`:657-667`, the M23 guard) stays.
  - The raw evidence written to disk must be valid JSON in its redacted form, and that redacted
    form is what gets hashed (`:2064`).
- **(f) M4.**
  - Overrides base `rev2.1.md:423-424` ("Do not treat this as a mandatory gap").
  - Invert `tests/test_workflows_js.py:1397-1410`, including a `status` assertion.
- **(g) M-L6.** `expanduser()` ONLY; drop the absolute-path alternative (it breaks the ≤1000-char
  submit test, `test_codex_research_gate.py:255-283`).
- **(h) Residual, non-blocking.** The live Codex hook runs the clone
  `~/.codex/tools/dotfiles-research-gate` (v1). M3 is inert in live Codex until the O1 gate pull.
  The coordinator tracks this.

### §8 addenda (rev r1.2, premise round 2: DISPATCH-READY once these two lines are applied)
- **(b) scope.** The status-independent rule applies ONLY to fallback-route attempts
  (serper/serpapi, in `_credit_result`'s loop at `:1375-1381`) and ONLY to those two phrases.
  - Implement it OUTSIDE `is_credit_exhaustion`.
  - Do NOT change the existing classifier table rows at `tests/test_research_fanout.py:2059-2067`.
  - Add a primary-route arm, `(401, "Not enough credits")` → not credit.
  - Add one fallback arm per phrase, each at a non-402/429 status.
- **(d) exhaustive list.** The no-status CREDIT phrase list is: "Insufficient credits", "credits
  exhausted", "Not enough credits", "run out of searches", "payment required", "out of credits".
  The last two are RETAINED from today's `_CREDIT_TEXT`. Status gating per the existing table
  (`:2059-2067`) is unchanged for the primary route.
