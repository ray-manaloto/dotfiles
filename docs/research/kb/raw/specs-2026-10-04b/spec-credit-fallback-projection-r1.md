# Spec r1 (2026-10-04, spec-scribe): credit-fallback N2/N1 fix + full workflow diagnostic projection

**Status: RATIFIED by architect 633cd8 (2026-10-04). U1–U8 all take the §4.5 Recommendation column.**

- **U1:** the §3.2 literal.
- **U2:** not credit.
- **U3:** envelope only for credit-skipped fallback attempts; keep strict-five-v2.
- **U4:** a `detail` object.
- **U5:** no schema change.
- **U6:** G5 + K16.
- **U7:** the closed prerequisite set.
- **U8:** include `_REPO_SHAPE`.
- **Tickets:** N3, N4 and K11/K12 are filed by the coordinator after the lane commits. N4 (the false PROVISIONAL context7 demand) is accepted as a known residual for this round.
- **Dispatch:** only after the premise check.

**Ray's ruled scope, verbatim (2026-10-04, relayed by the coordinator):** "Full workflow projection now".

**Coordinator decision notes, kept verbatim. These are load-bearing:**
1. N2: Stop block reason built ONLY from validated identifiers (verdict.provisional_entries source + optional
   `via <route>`) and fixed text; no provider diagnostics/bodies/stderr; preserve one-block, null-answer,
   already-continued behaviour.
2. N1: credit-phrase fallback recognition only on non-2xx provider failures (prefer top-level message/error fields);
   2xx shape failures stay errors; keep genuine 402 / quota-429. Strict validation must RE-DERIVE fallback credit skips
   from bound transport evidence and reject receipts that cannot establish it; keep missing-key skips distinct.
3. Workflow projection: structured provenance + finite failure codes replacing raw diagnostics on every path in the
   injection-path table (PROBE-JSON copy, provisional strings into synthesis, mirror diagnostics, fanout error gaps,
   mirror failures/redirect metadata, CLI summaries, mirror README); re-validate at the copied-JSON consumer; detailed
   diagnostics stay in evidence artifacts only.

**Evidence base:**
- SDLC review: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/sdlc-runs/1d3880fb9c0240c1ac565ff8136fb39b/output.md`.
  It supplies the findings, the injection-path table and the required tests and mutations.
- Opus cold review at 636dd297, in the worktree: `docs/research/kb/reports/agents/cold-review-credit-fallback-636dd297.md`.
  It supplies N1–N5.
- Base specs, still binding where this spec is silent: `spec-credit-fallback-rev2.1.md` and
  `spec-credit-fallback-respec-r1.md` under
  `.claude/worktrees/handoff-2026-10-04a/docs/research/kb/raw/specs-2026-10-04a/`.

**Provenance of this draft:**
- Spec-scribe memory was consulted.
- This lane has no Bash. It ran no `git`, `mise`, `uv` or test command, so it reports no measured test counts and
  cannot see whether the worktree is dirty.
- Every `V` premise below cites a line that this lane read during this run.
- The caller restricted writes to this file, so no memory update, `findings.md` entry or `progress.md` entry was made.
  The proposed memory conventions are in the hand-back.

---

## 1. Objective

At `feat/research-credit-fallback` @ 636dd297, make one new commit that removes every path in the ruled
injection-path table. On those paths, provider-controlled bytes currently reach a model-visible channel. The commit
must keep the credit-fallback behaviour that 636dd297 established.

1. **N2, the Stop continuation.** A provisional Stop `decision: block` is fed to Codex as a new user prompt (codex
   `hooks.md:923-925`).
   - Its `reason` becomes fixed text plus the validated identifiers from `verdict.provisional_entries`: each entry's
     `source`, plus `via <route>` when it has a route.
   - No provider body, stderr or diagnostic may appear in it.
   - The one-block, null-answer and already-continued (`stop_hook_active`) semantics stay exactly as they are at
     636dd297.
2. **N1, the producer.** The fallback credit-phrase rule fires only when a fallback provider answers non-2xx, and only
   on that response's top-level `message`/`error` string fields (subject to U2).
   - A 2xx response that fails the shape check stays `ERROR`.
   - A genuine HTTP 402 and a 429 carrying quota or credit text stay credit exhaustion.
3. **N1, the consumer.** Strict validation re-derives every credit-SKIPPED fallback attempt from bound transport
   evidence, an envelope that carries the HTTP status inside the hashed bytes.
   - It rejects any receipt that cannot establish the skip, including every 636dd297-era receipt whose fallback skip
     evidence is a bare body.
   - A missing-key fallback skip stays a distinct, evidence-less state, checked separately.
4. **Workflow projection.** Every model-visible output named in decision note 3 carries only these values:
   - validated identifiers;
   - finite `FailureCode` values;
   - integers;
   - fixed text.

   The outputs are: the PROBE-JSON line and per-probe stdout lines, the `strict-five` line and the CLI summary, the
   workflow's mirror, provisional and dependency strings, and the mirror README.

   Detailed diagnostics stay in the evidence artifacts only:
   - the fan-out `manifest.json`;
   - each `<source>.json`;
   - the `.raw` files;
   - the mirror `detail` object (U4).

   The workflow re-validates every identifier and code it reads from a copied PROBE-JSON line. It fails closed when
   one is invalid.

**Non-goals.** No change to:
- classification of the primary routes (`is_credit_exhaustion`, and its table at `tests/test_research_fanout.py:2056-2089`);
- the strict-five required set, or `policy_version` (U3);
- the Stop hook's blocking conditions;
- docs, skills, rules, `AGENTS.md`, `mise.toml`, `~/.codex/**`.

N3 and N4 are not fixed here, and only part of N5 is (§4.4).

## 2. Files

The implementer may touch **only** these paths, in the worktree
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/credit-fallback`:

| # | Path | Change |
|---|---|---|
| 1 | `python/src/dotfiles_setup/research_fanout.py` | `FailureCode`, `failure_code()`, `_fallback_credit()`, transport envelope for credit-skipped fallback attempts, validator re-derivation and the missing-key check, projected `_provisional_line`, projected `_print_summary`, projected probe rows (fanout-manifest, mirror, repo-check), README `code` column |
| 2 | `scripts/codex-research-gate.py` | provisional block `reason` built from `provisional_entries` only |
| 3 | `.claude/workflows/research-sweep-run.js` | PROBE-JSON row re-validation, the `FAILURE_CODES`/`PROVISIONAL_ROUTES` literals, mirror objects carry `code` (not `reason`/`primaryReason`), projected provisional/required-failed strings |
| 4 | `tests/test_research_fanout.py` | N1 producer and consumer arms; projected summary and strict line; the inversions listed in §5.2 |
| 5 | `tests/test_research_fanout_probe.py` | projected probe rows, README code column, sentinel exclusion, the inversions in §5.2 |
| 6 | `tests/test_codex_research_gate.py` | exact-reason literal, sentinel exclusion, prose-invariance, invalid-name controls, the `exa`/`exactly` lookaround pin |
| 7 | `tests/test_workflows_js.py` | harness stubs (`MIRROR_OK`, `PLAN_MANIFEST_OK`, `DEPS`) emit projected rows; consumer re-validation arms; drift test; the inversions in §5.2 |
| 8 | `tests/fixtures/research_fanout/**` | new fixtures only. Existing fixture bytes are unchanged. |

**Never touched:**
- the untracked review reports in the worktree (`docs/research/kb/reports/agents/*.md`);
- every other tracked file;
- `~/.codex/**`, `~/.config/**`, the knowledge-base repo, and `task_plan.md`.

The commit stages the paths above **by name**, never with `git add .` (`do-not.md` #5).

## 3. Interfaces

### 3.1 Finite codes (`research_fanout.py`, new and public)

```python
class FailureCode(Enum):
    """Closed set of model-visible failure codes. Values never derive from provider text."""
    CREDITS_EXHAUSTED = "credits-exhausted"
    PREREQUISITE = "prerequisite"
    HTTP_ERROR = "http-error"
    INVALID_JSON = "invalid-json"
    SHAPE_ERROR = "shape-error"
    PROVIDER_FAILURE = "provider-failure"
    PROCESS_FAILED = "process-failed"
    TIMEOUT = "timeout"
    REQUEST_FAILED = "request-failed"
    CREDENTIAL_INVALID = "credential-invalid"
    CANARY_FAILED = "canary-failed"
    CANARY_EMPTY = "canary-empty"
    NO_CANARY = "no-canary"
    NOT_FOUND = "not-found"
    REDIRECTED = "redirected"
    EMPTY_OUTPUT = "empty-output"
    IO_ERROR = "io-error"
    OTHER = "other"

def failure_code(reason: object, *, status: object, skip_reason: object = None) -> FailureCode | None:
    """None when status is ok/empty_verified. Otherwise a member chosen by the ordered table below.
    Unknown or non-string input -> OTHER. The return value NEVER carries text from `reason`."""
```

**Row and attempt mapping.** The rules are ordered, and the first match wins. Every left-hand string is a fixed
producer literal in `research_fanout.py`; the line numbers are at 636dd297.

| Rule | Code |
|---|---|
| `skip_reason == "credits-exhausted"` | `credits-exhausted` |
| `skip_reason == "prerequisite"`, or `status == "skipped"` with a reason in `_PREREQUISITE_TEXTS` (U7) | `prerequisite` |
| reason fullmatches `HTTP \d{3}` (`:877`, `:987`) | `http-error` |
| `invalid JSON` (`:630`, `:661`, `:881`, `:991`) | `invalid-json` |
| `unexpected response shape`, `unexpected discussions search shape`, `unexpected JSON shape`, `unexpected fallback response shape`, `response contained errors` (`:769-776`, `:802`, `:995`) | `shape-error` |
| `provider reported failure` (`:1044`) | `provider-failure` |
| matches `^exited -?\d+: ` (`_subprocess_error`, `:704`) | `process-failed` |
| `timed out` | `timeout` |
| `request failed`, `response too large`, `incomplete response` (`:331`, `:337`, `:1384`) | `request-failed` |
| starts with `invalid credential header for ` (`:319`) | `credential-invalid` |
| `canary failed` | `canary-failed` |
| `canary returned 0 items` | `canary-empty` |
| `no canary` | `no-canary` |
| `script disappeared`, `unknown source` | `not-found` |
| anything else | `other` |

**Mirror-probe codes.** `_mirror_probe` sets `code` per branch at production time and never maps from text:

| Branch at 636dd297 | `code` |
|---|---|
| cannot prepare the path (`:2580-2587`) | `io-error` |
| firecrawl rc 0 and mirrored | `""` |
| `_scrape_payload` not JSON (`:2656`) | `invalid-json` |
| `success:false`, not credit (`:2658`) | `provider-failure` |
| unexpected shape (`:2661`) | `shape-error` |
| page status ≥ 400 (`:2667`) | `http-error` (the int stays in `http_status`) |
| firecrawl rc ≠ 0, not credit (`:2610`) | `process-failed` |
| firecrawl timeout / not found (`:2641-2644`) | `timeout` / `not-found` |
| credit, then webclaw mirrored | `""`, with `route: "webclaw"` and `provisional: true` |
| webclaw not found / timeout / rc ≠ 0 (`:2524-2532`) | `not-found` / `timeout` / `process-failed`, with `route: "webclaw"` |
| webclaw redirected (`:2554-2556`) | `redirected` (the final URL goes ONLY to `detail`) |
| webclaw empty markdown / not JSON (`:2558`, `:2561`) | `empty-output` / `invalid-json` |
| fall-through `rc=N, M bytes` (`:2646-2647`) | `empty-output` if rc 0, else `process-failed` |

### 3.2 N2: the Stop reason (`scripts/codex-research-gate.py` `_on_stop`)

- `tokens` are built exactly as at `:109-116`, and the `named` test is exactly `:117-122`. The one-block,
  null-answer and `stop_hook_active` behaviour is unchanged.
- The provisional branch keys on `verdict.provisional_entries`, not on `verdict.provisional`.
- The block `reason` is built ONLY from the entries:

```python
listed = "; ".join(
    entry.source + (f" via {entry.route}" if entry.route else "")
    for entry in verdict.provisional_entries
)
reason = (
    "Research receipt PROVISIONAL (credit-exhausted provider). Name PROVISIONAL and each of "
    f"these in the answer: {listed}."
)   # U1: exact wording
```

- `verdict.provisional`, `verdict.reason` and every manifest field are **not** read on this branch.
- The identifiers are already validated:
  - the source set is checked at `research_fanout.py:2185-2196`;
  - the source is checked against `CREDIT_METERED_SOURCES` at `:2023`;
  - the route is checked at `:2026-2029` and `:2053-2059`;
  - the entries are built after validation at `:2207-2211`.
- No extra gate-side identifier check is added, because it could not be pinned through a public interface; see §4.2.
- The failed-receipt branch (`:132-149`) is unchanged. Its reason is already fixed validator text.

### 3.3 N1: fallback classification (producer)

```python
def _fallback_credit(http_status: int | None, body: str) -> bool:
    """Fallback routes (serper/serpapi) only.
    False when http_status is None or 200 <= http_status < 300.
    True when is_credit_exhaustion(http_status, body) (402; 429 with credit/quota text).
    Else True only when `body` JSON-decodes to a dict whose TOP-LEVEL "message" or "error"
    value is a str matching _FALLBACK_CREDIT_TEXT. Nested fields, non-dict JSON and non-JSON
    bodies -> False (U2)."""
```

- In `_credit_result`, `:1428-1437` becomes `if final.error and _fallback_credit(final.http_status, body_text):`. Here
  `body_text = final.raw.decode(errors="replace")`.
  - The bare `_FALLBACK_CREDIT_TEXT.search(<whole body>)` disappears.
  - `_attempt_credit(final)` is no longer consulted on the fallback path. Its 402/quota-429 cases are now inside
    `_fallback_credit`.
- The fallback skip `reason` stays the raw body tail, capped at 300 (`[-300:]`), in the manifest only. It is evidence
  (N5 K16 pin, U6).
- A **credit-SKIPPED fallback attempt's evidence** becomes a transport envelope, not the bare body.
  - Rename `_primary_envelope` (`:1341-1354`) to `_transport_envelope(attempt)`. Its byte format is unchanged:
    `{"body", "http_status", "rc", "stderr_redacted"}`, with sort_keys.
  - Use it for the primary, and for every fallback attempt whose status is `SKIPPED` because of credit. Such an
    attempt has `http_status` set to an int, `rc: null` and `stderr_redacted: ""`.
  - Winning (ok/empty_verified) and `ERROR` fallback attempts keep their bare-body evidence. The winner must, because
    `:2133` binds the winner's hash to `<source>.raw` (U3).

### 3.4 N1: strict validation (consumer)

`_credit_attempts` (`:2040-2082`) applies these rules to every attempt whose `route != source`:

| Attempt state | Required | Rejection reason (fixed text) |
|---|---|---|
| `SKIPPED`, `raw_file` null | `raw_sha256` null, AND `reason == f"{_FALLBACK_KEYS[route]} not inherited; run through fnox exec"` (the producer literal at `:1418`) | `invalid fallback prerequisite skip` |
| `SKIPPED`, `raw_file` set | bound and hash-checked (`_bound_raw`); decodes as a transport envelope with `http_status` an int and `rc` null; `_fallback_credit(http_status, body)` is True | `fallback credit skip does not re-derive` |
| `ERROR`, `OK`, `EMPTY_VERIFIED`, `EMPTY_UNVERIFIED` | unchanged from 636dd297 | unchanged |

- Factor the envelope decode shared with `_credit_envelope` (`:2085-2111`) into one helper.
- `_credit_envelope` keeps re-deriving the **primary** with `_attempt_credit`, unchanged.
- **The same `_fallback_credit` function is called by the producer and by the validator.** The §5.1 mutation M-N1c
  deletes only the validator call, to prove that the consumer is independently pinned.
- **Compatibility.** A 636dd297-era receipt with a credit-SKIPPED fallback attempt carries bare-body evidence.
  - It now fails with `fallback credit skip does not re-derive`. This fails closed, and is intended.
  - No historical receipt is shipped: the branch is unmerged.
  - Receipts with no fallback skip are unaffected.

### 3.5 Projected strings (`research_fanout.py`)

**`_provisional_line(row)`** is rewritten. It takes nothing from `reason`, `attempts[*].reason`, a body or stderr.

- A row with a route renders as `"{source} via {route} (credits-exhausted)"`.
- A row without a route renders as `"{source} skipped: credits-exhausted; "` followed by
  `"no fallback succeeded"` when `_FALLBACK_ROUTES.get(source)` is set, and `"no fallback route"` otherwise.
- Each `attempts[1:]` entry whose status is error or skipped appends `"; {route}: {code}"`. The code is derived as
  follows:
  - a SKIPPED attempt with no `raw_file` gives `prerequisite`;
  - a SKIPPED attempt with a `raw_file` gives `credits-exhausted`;
  - otherwise the code is `failure_code(reason, status=…)`.

The output feeds these consumers:
- `StrictVerdict.provisional` (type unchanged);
- the `validate_strict_five` reason (`"provisional: " + "; ".join(lines)`, shape unchanged);
- the `strict-five  pass  [...]` line (`:2989`);
- `_print_summary`.

**`_print_summary`** (`:2923-2940`):
- Provisional with a route: `[provisional: <line>]`.
- Provisional without a route: `[<line minus "<source> ">]`.
- Any other non-ok row: `[<code>]`.
- When the code is `prerequisite` and the row reason is in the closed set `_PREREQUISITE_TEXTS` (U7), the bracket is
  `[prerequisite: <that fixed text>]`.
- `result.reason` itself is never printed.

**Probe rows.** The PROBE-JSON line and the `{kind}  {json}` stdout lines both print the projected rows.

| Probe kind | Projected fields |
|---|---|
| `fanout-manifest` | `required_failed`: each entry `"{name}: {status} ({code})"`, `"{name}: {status}"` when there is no code, or the existing fixed `"{name}: no manifest"` / `"{name}: unreadable"`. `name` is pre-validated by `_probe_required` (`:2774-2778`). `status` is a `Status` value, `not run`, or the literal `invalid` for an unknown string. Capped at `len(_SOURCE_NAMES)` entries. `sources`: only keys in `_SOURCE_NAMES` and values in `Status` values, else `"invalid"`. `provisional`: a list of `{"source": str, "route": str \| null}` kept only when `source ∈ CREDIT_METERED_SOURCES` and `route ∈ (None, *_FALLBACK_ROUTES.get(source, ()))`. `provisional_invalid`: true when any `provisional: true` row failed that check. `query`, `age_s`, `fresh` and `request_id` are unchanged. |
| `mirror` | `kind, url, path, route, provisional, rc, http_status, bytes, code`. `reason` and `primary_reason` are **removed from the line**. |
| `mirror-index` | unchanged |
| `code-search` | unchanged |
| `repo-check` | `full_name` is emitted only when it fullmatches `_REPO_SHAPE` (`:2255`), else `""` (U8) |

**The mirror `detail` object (U4, recommended option).**
- The on-disk probe file holds the projected payload plus, on each mirror row, a
  `detail: {"reason": <636dd297 reason text>, "primary_reason": <capped credit text>}`.
- `detail` is stripped from the stdout projection.
- `on_disk` therefore equals `payload` except for `detail`.

**README** (`_mirror_index_probe`):
- The header becomes `| n | url | file | rc | bytes | failure code | route |`.
- The failure cell is the probe file's `code` when it is a `FailureCode` value or `""`.
- A probe file with a missing or invalid `code` is counted `missing` and rendered with the existing fixed text
  `mirror probe missing or unreadable`. This fails closed.
- `stale probe from an earlier run` is unchanged.
- The header paragraph adds one sentence: "The failure code is a fixed value; diagnostics are in each
  `<n>.probe.json` `detail`."

### 3.6 Workflow (`.claude/workflows/research-sweep-run.js`)

**New single-line literals, kept beside `SOURCES` (`:125-126`):**

```js
const FAILURE_CODES = new Set(['credits-exhausted', 'prerequisite', /* … exactly FailureCode values … */ 'other'])
const WORKFLOW_CODES = new Set(['probe-missing', 'invalid-probe'])
const PROVISIONAL_ROUTES = { exa: [], context7: [], 'firecrawl-developer': [], 'firecrawl-search': ['serper', 'serpapi'] }
const MIRROR_ROUTES = ['firecrawl', 'webclaw']
const MAX_PROBE_ENTRIES = 8
```

**Re-validation at the copied-JSON consumer.** It runs after `readProbe` and fails closed:

| Copied field | Rule | On violation |
|---|---|---|
| mirror row | `route ∈ MIRROR_ROUTES`; `code === ''` or `FAILURE_CODES.has(code)`; `rc` and `bytes` are integers; `provisional` is boolean | the mirror entry becomes `{ url, path, rc: null, bytes: 0, code: 'invalid-probe' }`, plus mandatory gap `mirror stage for ${url}: probe row failed validation` |
| fanout `provisional` | an array of at most `MAX_PROBE_ENTRIES` entries; each `source ∈ PROVISIONAL_ROUTES` and `route === null \|\| PROVISIONAL_ROUTES[source].includes(route)`; `provisional_invalid !== true` | none of that manifest's entries are used, plus mandatory gap `${m.path}: provisional projection failed validation` |
| fanout `required_failed` | an array of at most `MAX_PROBE_ENTRIES` strings; each matches `^(SOURCES): (ok\|empty_verified\|empty_unverified\|error\|skipped\|not run\|invalid\|no manifest\|unreadable)( \((FAILURE_CODES)\))?$`, built from the literals | the entry is replaced by the fixed `unrecognised required_failed entry`, which still counts as a failure |

**Rendering. Only validated values are interpolated:**
- Mirror objects carry `code` and `httpStatus`, and no longer carry `reason` or `primaryReason`.
- The probe-missing path (`:493-495`) uses `code: 'probe-missing'`.
- `mirrored = m => m.rc === 0 && m.bytes > 0 && !m.code`.
- `codeText(m)` is `http-error <int>` when `code === 'http-error'` and `httpStatus` is an integer in 100–599. Otherwise
  it is `code`. For `route === 'webclaw'` it is prefixed `credits-exhausted; webclaw `.
- `mirrorGaps` is `${m.url}: not mirrored (${codeText(m)})`, and the reader note is `NO MIRROR: ${codeText(m)}`.
- `provisionalRoutes`:
  - a mirror renders `${m.url}: mirrored via webclaw (credits-exhausted)`;
  - a manifest entry renders `${m.path}: ${source} via ${route} (credits-exhausted)`, or
    `${m.path}: ${source} skipped (credits-exhausted)` when it has no route.
- Status and precedence logic are unchanged.

## 4. Constraints and invariants

### 4.1 Hard constraints

- **Run targeted tests only.** The HOST SLOT is shared, and memory says one test slot runs host-wide. Run only §5.3.
  Do NOT run:
  - the full suite;
  - `mise run lint`, `mise run verify` or `mise run gate`;
  - container operations;
  - `ship` or `land`;
  - any live provider call.
- No inline suppressions (`noqa`, `type: ignore`, …), no `--no-verify`, no new `.sh` file.
- Never print a credential value. No `fnox`, no `echo`/`printf` of a credential variable, no env dump.
- **Fresh sentinels.** Every diagnostic sentinel in a test is built at runtime by concatenation with `uuid.uuid4().hex`.
  It is never a committed literal, because a committed control stops being absent (probes rule 3).
- Expected values are literals or come from fixtures, and are never recomputed the code's way (`tests/AGENTS.md`).
  The §5.2 inversions are **ratified behaviour changes** (decision note 3), not "edit to pass".

### 4.2 Lane prohibitions

The guard cannot see codex shell commands, so these are stated here. The lane must NOT:
- push, open a PR, amend 636dd297, or rebase;
- edit outside §2;
- stage the untracked review reports;
- run `mise run lock`;
- write `task_plan.md`, `findings.md` or `progress.md`.

**No unpinnable guard.** Do not add a guard that no public-interface test can turn red, such as gate-side identifier
re-validation reachable only through a stubbed verdict. Report any such guard instead of shipping it.

### 4.3 Out-of-scope exposures (named, retained deliberately)

From the SDLC review table (`output.md:25-41`), these paths are NOT changed:

| Path | Why it is retained |
|---|---|
| Retrieved results and documents → readers/claims | This is the intended intake of untrusted evidence. Explicit data-only reader guidance is a ticket candidate (defense in depth only). |
| Triage agent reads `manifest.json` / `<source>.json` raw reasons (`workflow:618`) | These are evidence artifacts by decision note 3. Same ticket candidate. |
| Derived prose → refute, adjudicate, reconcile, retrospect | Conditional propagation. Upstream projection shrinks it. |
| `last_assistant_message` matching (`gate:117-120`) | A presence check only, with no reflection. |
| Incomplete `systemMessage` and the UserPromptSubmit `additionalContext` | Already fixed text plus validated identifiers. |
| Internal write-error stderr (`fanout:2906-2909`, `:2981-2984`) | Exception type names only. |
| Agent-authored strings (`plan.runs[].query` in `fanoutGaps`, `m.query`, code-search `query`) | Not provider bytes. |
| Receipt self-attestation | Validation detects stale or relabeled receipts. A writer of the receipt directory can still hand-forge a re-deriving envelope (cold review INFO, `:72-75`). |
| Missing-key claim | An evidence-less `SKIPPED` "not inherited" attempt cannot be disproven from bytes. It is distinct (exact fixed reason, no evidence), not proven. |
| Live Codex | The hook runs the `~/.codex/tools/dotfiles-research-gate` clone, so this fix is inert there until the O1 pull. |

### 4.4 N3/N4/N5 interaction: ticket or include

| Item | Disposition | Interaction with this fix |
|---|---|---|
| **N3** (ctx7 `HTTP error <code>` on stdout is unclassified) | **Ticket.** It needs a live Context7 402 sample. | None with N1, which touches only the fallback routes. A ctx7 402 stays `ERROR` and now projects as `process-failed`. Do not restore bare-number matching. |
| **N4** (the ctx7 echoed query launders into a credit skip) | **Ticket.** It needs a ctx7-specific error-line parse that is multiline-query aware. | Projection removes the echoed query from the Stop continuation and the summaries. It does **not** fix the false `context7 skipped: credits-exhausted`. The primary envelope genuinely re-derives, so neither the N1 consumer fix nor the gate catches it; the Stop hook will demand a false PROVISIONAL `context7`. |
| **N5-G5** (gate token lookarounds unpinned) | **Include.** It is required by the SDLC test table row 6, and this commit touches the hook. | — |
| **N5-K16** (fallback skip reason cap unpinned) | **Include (U6).** This commit rewrites those lines. | — |
| **N5-K11/K12** (SerpApi Fully-empty clauses unpinned) | **Ticket.** These are test-only pins with no interaction. | — |

### 4.5 Unratified choices: STOP for the architect

| # | Choice | Recommendation | Alternative |
|---|---|---|---|
| U1 | Exact Stop reason wording | The §3.2 literal. It still contains the substrings asserted at `test_codex_research_gate.py:369-371`. | Any fixed text, provided it is pinned as an exact literal. |
| U2 | A non-2xx fallback body that is not a JSON dict, or whose phrase is nested | **Not credit** (an `ERROR`, visible). Fields-only, as the note's "prefer" reads. PRO: fail closed, since content cannot launder a failure. CON: a plain-text exhaustion page fails until a provider rule is verified. | Search the whole body for non-JSON non-2xx bodies only. |
| U3 | Transport binding and policy version | An envelope **only** for credit-SKIPPED fallback attempts. Keep `strict-five-v2`, because nothing has shipped and a bump churns the gate marker, the submit context and the ≤1000-character test. Legacy receipts fail closed. | An envelope for every fallback attempt (changes the `:2133` winner binding); or bump to `strict-five-v3`. |
| U4 | Where the mirror diagnostics live | A `detail` object in the on-disk probe file, stripped from stdout. This changes the `on_disk == payload` assertion (`probe:117-118`) to compare without `detail`. | A sibling `<n>.probe.detail.json`; or drop the mirror detail entirely. |
| U5 | How a missing-key skip is kept distinct | No evidence, plus the exact producer reason. There is no schema change. | Add `skip_reason` to `RouteAttempt` (schema and fixture churn). |
| U6 | N5 scope | Include G5 and K16; ticket K11 and K12. | Include all four; or G5 only. |
| U7 | Prerequisite hint in the CLI summary | Pass through only the closed `_PREREQUISITE_TEXTS` set (the `_prerequisite_reason` literals at `:1203-1221`, plus the two fallback `not inherited` strings). PRO: keeps the actionable `run through fnox exec` hint. | Code only. |
| U8 | `repo-check.full_name` (GitHub bytes in PROBE-JSON, not in the review table) | Include the `_REPO_SHAPE` filter, because PROBE-JSON is a ruled path. | Ticket it. |

## 5. Verification

### 5.1 Tests and mutations

The table carries the SDLC review's required tests (`output.md:67-78`) and adds this spec's.

Every test goes through a public interface: `main()`, `validate_strict_five`/`strict_five_verdict`, the real hook
subprocess (`_invoke`), or the Bun workflow harness.

Each mutation reverts **only** the named hunk to its 636dd297 form (from `git show 636dd297:<path>`). After the
mutation is applied, the lane must confirm that the target test is RED, then restore the hunk and confirm GREEN.

| # | Test and control arms | File | Mutation that must turn it RED |
|---|---|---|---|
| T1 | Real hook CLI with a valid receipt carrying a **primary sentinel** (stderr `Insufficient credits ` + fresh sentinel) and a **fallback sentinel** (serper 400 `{"message":"Not enough credits " + sentinel}` credit-skip envelope, serpapi winning). The result is a block; the reason **equals** the U1 literal ending `firecrawl-developer; firecrawl-search via serpapi.`; neither sentinel is present. | gate | M-N2a: restore `"; ".join(verdict.provisional)` in the reason, with `_provisional_line` restored to 636dd297 (the true prior pair). M-N2b: gate-only restore while `_provisional_line` stays projected. The exact-literal assert goes RED. |
| T2 | **Prose invariance.** Two receipts differing only in diagnostic prose produce byte-identical reasons. | gate | M-N2c: append any row `reason` to the block reason. |
| T3 | Substituted and skipped receipts with named, unnamed, null, continued and earlier-incomplete arms. Keep the existing `:288-384` table. | gate | Remove block enforcement / the `stop_hook_active` check / route tokens / source tokens (existing G1–G4, G7, G8). |
| T4 | **Invalid-name controls.** A provisional row whose `route` is `"serper; " + sentinel` → fail-block with a fixed reason and no sentinel. A provisional `github-issues` row with a re-deriving 402 envelope → fail. | gate / fanout | Delete the route check at `:2027-2029`: the sentinel appears and T4 goes RED. Delete `or source not in CREDIT_METERED_SOURCES` at `:2023`: T4 goes RED. |
| T5 | `PROVISIONAL exactly` does not acknowledge an `exa` credit-skip source; `PROVISIONAL exa` does. | gate | Delete the token lookarounds at `gate:118` (N5-G5). |
| T6 | **Both fallback providers:** serper and serpapi each return (a) a 200 malformed shape with credit wording, which stays `ERROR` with strict False; (b) a 200 malformed shape without the wording, which stays `ERROR`; (c) a 200 valid result whose snippet mentions "Not enough credits", which is `ok`; (d) the existing `:2802-2804` non-2xx credit responses, which stay provisional with strict True; (e) a non-2xx response whose phrase is only nested (`{"detail":{"message":"Not enough credits"}}`), which is `ERROR` (U2). | fanout | M-N1a: restore the `:1430-1433` whole-body/any-status match; (a) goes RED. M-N1b: whole-body search for non-2xx responses; (e) goes RED. |
| T7 | **Historical/relabeled receipt.** Take a hash-valid receipt in the 636dd297 format, whose serper credit-skip evidence is a bare body, and relabel it: strict gives False, `fallback credit skip does not re-derive`. **Control:** a genuine producer receipt (402/400-credit envelope) gives True. **Missing-key control:** an evidence-less SKIPPED serper attempt with the exact producer reason gives True. With the reason `"key gone"` it gives False, `invalid fallback prerequisite skip`. | fanout | M-N1c: delete the validator's `_fallback_credit` call (the producer fix stays); T7 goes RED. M-N1d: drop the exact-reason check; the missing-key arm goes RED. |
| T8 | **The N1 compatibility literal.** The SDLC review's reproduction (Serper 200 `knowledgeGraph.description` quoting the phrase), end to end through `main()` and `validate_strict_five`. | fanout | M-N1a. |
| T9 | **CLI projection.** `main()` stdout for credit, skip, error (`exited 1:` stderr sentinel), HTTP-500 sentinel body and prerequisite rows contains its code / `prerequisite: EXA_API_KEY not inherited; run through fnox exec`. No sentinel appears in stdout or in the `strict-five` line. Every sentinel is still in `manifest.json` / `<source>.json` (evidence kept). | fanout | M-P1: restore the 636dd297 `_print_summary` (`detail = result.reason`). M-P2: restore the 636dd297 `_provisional_line`. |
| T10 | **Probe projection.** A fan-out manifest with an error reason sentinel, plus a provisional row with sentinel reasons, gives PROBE-JSON `required_failed == ["github-issues: error (process-failed)"]`, structured `provisional`, and no sentinel in stdout. Forged rows (unknown source key, unknown status, invalid route) give `invalid` / `provisional_invalid: true`. More than 8 entries are capped. | probe | M-P3: restore `:2491-2493` (`_provisional_line` in the probe). M-P4: restore the `({reason})` detail at `:2511-2512`. |
| T11 | **Mirror projection.** A non-credit stderr sentinel, a webclaw redirect to a sentinel URL, and credit primary text with a sentinel all give the right `code`, and no sentinel on the stdout PROBE-JSON. Each sentinel is in the on-disk `detail` (U4). | probe | M-P5: restore `reason`/`primary_reason` in the emitted row. |
| T12 | **README.** The `failure code` column; a missing or invalid `code` in a probe file → `mirror probe missing or unreadable` and counted missing; no sentinel. | probe | M-P6: restore `mirror["reason"]` at `:2711`. |
| T13 | **Workflow re-validation.** Copied lines with route `'serper; ' + sentinel`, code `'http-error; ' + sentinel`, an unknown source, 9 provisional entries, `provisional_invalid: true`, and an unmatched `required_failed` string. Each gives its mandatory gap, and no sentinel appears in any captured prompt (synth, read-link, retrospect) or in the result. | workflows | M-W1: remove the JS validation (interpolate raw); the sentinel appears and T13 goes RED. |
| T14 | **Workflow rendering.** Provisional mirror → `https://caller.test/a: mirrored via webclaw (credits-exhausted)`. A manifest entry → `<path>: firecrawl-search via serper (credits-exhausted)`. A 404 mirror → `(NO MIRROR: http-error 404)` and mirrorGaps `… not mirrored (http-error 404)`. | workflows | M-W2: restore `${m.primaryReason}` / `${m.reason}` interpolation. |
| T15 | **Drift.** The JS `FAILURE_CODES` literal (extracted by regex from the JS source) equals `{c.value for c in FailureCode}`, and `PROVISIONAL_ROUTES` matches `CREDIT_METERED_SOURCES` and `_FALLBACK_ROUTES`. | workflows | Add a member to `FailureCode` only. |
| T16 | **N5-K16.** A fallback skip `reason` longer than 300 characters is capped to 300 in the manifest (U6). | fanout | Remove the `[-300:]` at the fallback skip reason. |

**Repo-wide literal note.** Sentinels are built by concatenation with a fresh nonce, so the test file never contains
the searched-for value.

### 5.2 Existing assertions to invert or update

These are ratified by decision note 3. Each is listed so that a reviewer can tell a sanctioned change from
edit-to-pass. Lines are at 636dd297.

**`tests/test_research_fanout.py`**
- `:2830`: stays (the manifest attempt reason is evidence).
- `:2832`: inverts to `not in output`, and adds `"credits-exhausted" in output`.
- `:2417`: moves the pricing-URL assertion from stdout to `exa.json`, and adds a `not in output` check.

**`tests/test_research_fanout_probe.py`**
- `:117-118`: becomes on-disk equal to payload except `detail` (U4).
- `:285`: becomes `["github-issues: error (process-failed)"]`.
- `:352-363`: the exact mirror dict drops `reason`/`primary_reason` and adds `code: ""`.
- `:376`, `:401`, `:410`: become `code` asserts (`process-failed`, `http-error` with `http_status == 404`,
  `invalid-json`).
- `:418-430`: the fixture gains `"code": ""`.
- `:450`: the header text check, if any, is updated.
- `:638`: moves to `detail.primary_reason`.
- `:686`: moves to `detail.primary_reason`; the cap stays.

**`tests/test_codex_research_gate.py`**
- `:369-371`: stays, and is superseded by T1's exact literal.

**`tests/test_workflows_js.py`**
- The harness `MIRROR_OK` (`:224-226`) emits `code` (default `''`).
- `PLAN_MANIFEST_OK`/`DEPS` (`:189-205`) take structured `provisional` entries.
- `:1306-1318`: the route literal becomes `(credits-exhausted)`, and `primaryReason` is absent.
- `:1338`: becomes structured entries; the rendered line becomes `… firecrawl-search via serper (credits-exhausted)`.
- `:1451`: becomes `'github-issues: error (http-error)'`.
- `:1483`, `:1491`, `:1493`: become `code: 'http-error', http_status: 404` and `(http-error 404)`.
- `:2354`, `:2359`: become `(NO MIRROR: empty-output)`.
- `:2375`, `:2380`, `:2382`: become `(http-error 404)`.
- Mocks at `:1391`, `:1469` drop `primary_reason`.

If any other existing assertion encodes a raw diagnostic on a projected path, apply the same rule and list it in the
report.

### 5.3 Commands the lane runs

Capture each command's output and rc to a file. Never pipe to `tail`/`head`.

```bash
uv run --project python pytest tests/test_research_fanout.py tests/test_research_fanout_probe.py \
  tests/test_codex_research_gate.py tests/test_workflows_js.py -q > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"
uv run --project python ruff check python/src/dotfiles_setup/research_fanout.py scripts/codex-research-gate.py \
  tests/test_research_fanout.py tests/test_research_fanout_probe.py tests/test_codex_research_gate.py tests/test_workflows_js.py
uv run --project python ruff format --check <same .py files>      # .py only; never markdown
uv run --project python ty check python/src/dotfiles_setup/research_fanout.py scripts/codex-research-gate.py
```

**Report:**
- the pytest rc and the passed/failed counts;
- the ruff/ty rcs;
- the §5.1 mutation table, with RED/GREEN per row and the restore confirmed;
- every §5.2 inversion actually made;
- any premise found false. If one is false, stop and report rather than guess.

### 5.4 After the lane (coordinator)

These are UNVERIFIED by this draft and owed by the coordinator:
- the full `mise run gate -- run lint|pytest|verify` once the host slot is free;
- an Opus diff-only cold review of `636dd297..<new>`;
- the R1–R4 live arms (base §5.3), with R4 now expecting the U1 literal;
- O1, the clone pull.

## 6. Commit

- Make **ONE new commit** on top of 636dd297. It is not an amend, there is no push, and there is no PR.
- Stage the §2 paths by name.
- Commit with hooks enabled. If pre-commit fails, fix the cause and commit again; never `--no-verify`.
- If pre-commit runs longer than 10 minutes, stop and report.

```
fix(research): project provider diagnostics to validated ids and codes (N1, N2)

N2: the provisional Stop block reason is built only from validated
strict-verdict entries (source, optional "via <route>") plus fixed text.
Codex turns a Stop reason into a new user prompt (KB codex hooks.md:923-925),
so provider bodies/stderr no longer reach it. One-block, null-answer and
stop_hook_active behaviour unchanged.

N1: the fallback credit phrase rule fires only on non-2xx Serper/SerpApi
responses, on top-level message/error fields; a 2xx shape failure stays an
error. Credit-skipped fallback attempts persist a transport envelope and
strict validation re-derives them with the same rule; 636dd297-era receipts
whose fallback skip evidence is a bare body now fail closed. Missing-key
skips stay distinct (no evidence + exact producer reason).

Projection: PROBE-JSON rows, per-probe stdout, the CLI summary and
strict-five line, the mirror README and every workflow mirror/provisional/
required-failed string now carry only validated identifiers, FailureCode
values, integers and fixed text; the workflow re-validates copied rows and
fails closed. Diagnostics remain in manifest/<source>.json/.raw and the
mirror probe file's detail object.

Tickets (not here): N3 ctx7 "HTTP error <code>", N4 ctx7 echoed query,
N5 K11/K12 pins.
Targeted pytest: <rc, counts>. ruff/ty: <rc>. Mutations: <n RED / n>.
R1-R4: not run by the lane; coordinator appends results
```

## 7. PREMISES

Legend:
- `V`: read by this lane during this run, at the cited line.
- `A`: assumed or inherited, with the reason given.

All `research_fanout.py`, gate, workflow and test paths are relative to the credit-fallback worktree.

| # | Premise | Status | Provenance |
|---|---|---|---|
| P1 | The branch `feat/research-credit-fallback` points at `636dd29708f6…`, and the worktree HEAD is that branch | V | `.git/packed-refs:173`; `.git/worktrees/credit-fallback/HEAD:1` |
| P2 | The worktree is clean at 636dd297 | A | No Bash; `git status` was not run. The coordinator confirms before dispatch. |
| P3 | The provisional block reason joins `verdict.provisional` | V | `scripts/codex-research-gate.py:123-130` |
| P4 | The gate tokens come from `provisional_entries`; `named` needs all of them, with lookarounds; `stop_hook_active` allows | V | `scripts/codex-research-gate.py:107-122` |
| P5 | The failed-receipt branch uses `verdict.reason` and fixed text | V | `scripts/codex-research-gate.py:132-149` |
| P6 | A Codex Stop `decision: block` reason becomes a new user-role continuation prompt; `stop_hook_active` is in the input | V | KB `sources/agent-harness-docs/docs/codex/hooks.md:905`, `:914-925` |
| P7 | The primary credit reason is raw stderr/body text, capped at 300 | V | `research_fanout.py:1393-1399` |
| P8 | The fallback phrase rule searches the whole body at any status, and the skip reason is the raw body tail | V | `research_fanout.py:1428-1437` |
| P9 | A 2xx fallback with the wrong shape returns `unexpected fallback response shape` with `http_status=200` | V | `research_fanout.py:986-996` |
| P10 | `is_credit_exhaustion` returns False for every status other than 402, 429 or None | V | `research_fanout.py:137-147` |
| P11 | Fallback attempt evidence is the bare body, and its status sits only in the unhashed `RouteAttempt` | V | `research_fanout.py:1454-1464`, `:1807-1827` |
| P12 | The primary evidence is a `{http_status, rc, body, stderr_redacted}` envelope | V | `research_fanout.py:1341-1354` |
| P13 | The validator re-derives only the primary envelope; an evidence-less SKIPPED attempt passes on its status alone; a route-less skip checks only that no ERROR/EMPTY_UNVERIFIED attempt exists | V | `research_fanout.py:2065-2073`, `:2085-2111`, `:2120-2128`, `:2151` |
| P14 | The winner's attempt hash must equal the row's raw hash | V | `research_fanout.py:2129-2136` |
| P15 | The source set, the metered source and the route are validated before provisional entries are built | V | `research_fanout.py:2023-2029`, `:2053-2059`, `:2185-2196`, `:2207-2211` |
| P16 | `_provisional_line` interpolates primary and attempt reasons | V | `research_fanout.py:1977-2002` |
| P17 | The fanout probe embeds `_provisional_line` and `({reason})` in its copied rows; `sources` is unvalidated | V | `research_fanout.py:2486-2513` |
| P18 | `--require` names are validated against `_SOURCE_NAMES` | V | `research_fanout.py:2774-2778` |
| P19 | PROBE-JSON and the per-probe stdout lines print full rows; the on-disk probe equals the payload | V | `research_fanout.py:2892-2920`; `tests/test_research_fanout_probe.py:117-118` |
| P20 | The mirror reason comes from the first stderr line; the redirect reason embeds the final URL; `primary_reason` is raw | V | `research_fanout.py:2554-2556`, `:2610`, `:2634-2636` |
| P21 | The README renders `mirror["reason"]` | V | `research_fanout.py:2704-2713`, `:2742-2744` |
| P22 | The summary prints `result.reason`, and the strict line prints the verdict reason | V | `research_fanout.py:2923-2940`, `:2986-2989` |
| P23 | The producer reason literals mapped in §3.1 exist at the cited lines | V | `research_fanout.py:319`, `:331`, `:337`, `:630`, `:704`, `:769-776`, `:802`, `:877-881`, `:987-995`, `:1044`, `:1186`, `:1265`, `:1384`, `:1418`, `:1540-1557`, `:1203-1221`, `:2524-2561`, `:2580-2587`, `:2641-2667` (Grep `_Attempt\(` and the reads) |
| P24 | `_REPO_SHAPE` exists | V | `research_fanout.py:2255` |
| P25 | `FailureCode`/`failure_code`/`FAILURE_CODES` do not exist yet | V | Grep over `*.{py,js}` in the worktree gave 0 files. Control: `SkipReason` with the same glob gave 1 file, so the probe discriminates. |
| P26 | `readProbe` accepts any parsed row without per-field validation | V | `.claude/workflows/research-sweep-run.js:182-191` |
| P27 | The workflow interpolates the mirror reason, `primaryReason`, provisional lines and `required_failed` into prompts and gaps | V | `research-sweep-run.js:481-485`, `:497-503`, `:635-641`, `:679`, `:737`, `:747-751` |
| P28 | The retrospect facts carry `mirrorGaps`, `mandatoryGaps` and `fanoutGaps` | V | `research-sweep-run.js:321-337` |
| P29 | `SOURCES` is a JS literal; there is no JS import from Python | V | `research-sweep-run.js:125-126` |
| P30 | The harness stubs that emit the rows needing projection | V | `tests/test_workflows_js.py:189-205`, `:224-226` |
| P31 | The existing assertions listed in §5.2 encode raw diagnostics | V | `tests/test_research_fanout.py:2414-2417`, `:2830-2834`; `tests/test_research_fanout_probe.py:285`, `:352-363`, `:376`, `:401`, `:410`, `:418-430`, `:450`, `:638`, `:686`; `tests/test_workflows_js.py:1306-1318`, `:1338-1364`, `:1451`, `:1483-1493`, `:2354-2382` |
| P32 | The gate tests run the real hook script with `HOME` overridden; the provisional parametrize table sits at `:288-384` | V | `tests/test_codex_research_gate.py:16-33`, `:288-384` |
| P33 | The fallback exhaustion fixtures use a Serper 400 `{"message":…}` and a SerpApi 403/429 `{"error":…}` | V | `tests/test_research_fanout.py:2799-2805` |
| P34 | The real Serper/SerpApi exhaustion responses carry the phrase in a top-level `message`/`error` | A | Inherited from the test fixtures (P33) and the SerpApi doc URL cited in code (`research_fanout.py:949`). No provider doc was fetched in this run, and the Serper status is "intentionally unverified" (`tests/test_research_fanout.py:2816-2817`). U2 decides how to fail when this is wrong. |
| P35 | The primary classifier table is unchanged by this spec | V | `tests/test_research_fanout.py:2056-2089` |
| P36 | The live continuation behaviour of Codex and model obedience were not reproduced | A | Inherited from the SDLC review (`output.md:19`). Only the emitted hook JSON was reproduced there. |
| P37 | N3–N5 facts (the ctx7 `HTTP error` form, the query echo, the unpinned guards K11/K12/K16/G5) | A | Inherited from the cold review (`cold-review-credit-fallback-636dd297.md:60-62`, `:135-151`) and the SDLC review (`output.md:80-84`). The ctx7 source was not read in this run. |
| P38 | The cold review's 331/331 green baseline at 636dd297 | A | Inherited (`cold-review-credit-fallback-636dd297.md:104`). Not re-measured, because there was no Bash. |
| P39 | There are no other code consumers of `research_fanout` beyond the gate, the workflow and the two test files | V | Grep `research_fanout\|strict_five_verdict\|validate_strict_five` (excluding `docs/**`) gave 6 files: the gate, the workflow, the module, 2 tests, and `mise.toml` (the task definition) |
| P40 | No skill or rule text documents the `reason`/`primary_reason`/`required_failed` probe fields | V | Grep under the worktree `.claude/` matched only the workflow (`:481`, `:499`, `:638`). That match is the control arm. |

## 8. Corrections r1.1 (architect, 2026-10-04 ~04:30 CDT, from premise-verifier round 1)

Source: `docs/research/kb/reports/agents/premise-verifier-credit-fallback-projection-r1.md` in the credit-fallback
worktree (verdict FIX FIRST). These corrections SUPERSEDE the conflicting text above. P2 confirmed by the architect:
`git status --short` in the worktree shows only untracked report files; tracked tree clean at 636dd297.

**A. T7 / M-N1c (§3.4, §5.1).** For a `SKIPPED` fallback attempt with `raw_file` set, EVERY failure of the shared
decode helper (bound/hash failure excepted — keep its existing reason), envelope-shape failure, or `_fallback_credit`
False maps to the single fixed reason `fallback credit skip does not re-derive`. The shared helper must not leak its
`malformed primary …` texts into the fallback path. T7 gains two arms with a WELL-FORMED envelope that does not
re-derive: (i) `http_status: 200` with the credit phrase at top-level `message`; (ii) `http_status: 400` without the
phrase. Both → strict False with that exact reason. M-N1c (delete only the validator `_fallback_credit` call) must turn
both arms RED; the bare-body arm may stay GREEN under M-N1c and that is expected.

**B. T4 (§5.1).** T4's route arm pins the EXACT reason `firecrawl-search invalid fallback route` (and asserts the
sentinel absent). Deleting the route check at `:2027-2029` then yields `missing winning route evidence`, so T4 goes RED
on the reason pin, not on the sentinel.

**C. JS mirror row with `code: ''` (§3.6).** Add to the mirror-row validation: a row with `code === ''` that is not
`mirrored` (i.e. `rc !== 0 || bytes <= 0`) is coerced — `rc === 0 && bytes === 0` → `code: 'empty-output'`; anything
else → `invalid-probe` plus the mandatory gap. No row may be neither mirrored nor a gap. Add a T14 arm for each branch.

**D. P31 correction.** `tests/test_research_fanout_probe.py:117-118` is code-search only and encodes no diagnostic;
remove it from §5.2 (it stays unchanged under U4).

**E. §5.2 additions (sanctioned inversions).**
- `tests/test_research_fanout.py`: `:734` → `[process-failed]`; `:2535`, `:2538` → `serper: http-error`; `:2833` →
  `<route>: prerequisite`.
- `tests/test_research_fanout_probe.py`: `:635` reads `detail.primary_reason` / `detail.reason` from the on-disk probe;
  `:740`, `:750`, `:753` become `code` checks (non-empty, `not-found`, `timeout`); `:771-773` become structured
  `{source, route}` entries; `:686` reads the on-disk file (stdout has no `detail`).
- `tests/test_workflows_js.py`: `:1579`, `:1583-1588`, `:3029`, `:3039` → `(http-error)`; `:2918`, `:2930` →
  `(canary-empty)`. The `required_failed` validation runs BEFORE the `wf:482` disabled-tracker filter.

**F. Non-blocking, fold in.** T6(e) pins `http_status` 400 (serper) / 403 (serpapi). U8: `.strip()` `full_name` before
`_REPO_SHAPE.fullmatch`. JS re-validates `repo-check.full_name` against `REPO_SHAPE` (`wf:105`) before `wf:519-523`;
on violation interpolate `""`. New T6–T9/T16 tests use the `credit_env` / `mirror_credit_env` fixtures; T9's
prerequisite arm unsets `EXA_API_KEY`.
