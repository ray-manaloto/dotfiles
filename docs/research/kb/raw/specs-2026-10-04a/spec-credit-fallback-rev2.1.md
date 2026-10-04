# Spec rev 2 (2026-10-03, spec-scribe): credit-exhausted route state and fallback routes for research fan-out (Claude and codex)

**Status: rev 2.** The open choices were ratified in the RATIFICATION section at the end, which the coordinator wrote
and which is kept verbatim. Rev 2 applies premise-verifier report rev 1
(`.claude/worktrees/handoff-2026-10-03q/docs/research/kb/reports/agents/premise-verifier-credit-fallback-spec-rev1.md`,
verdict CORRECT-SPEC-FIRST). Nothing has been dispatched yet. The coordinator gated dispatch on the premise result.

**Ratified request, verbatim (Ray, 2026-10-03 21:51 CDT):** "/codex-sdlc-team make updates to how this works for both
claude and codex where we check if api credits for 3rd party services like this are used up and either skip them or
fallback like we are doing w webclaw and not make it a failure"

**Provenance:**
- Spec-scribe memory was consulted (`.claude/agent-memory-local/spec-scribe/spec_drafting_conventions.md`).
- The rev 1 memory update was blocked by the bg-isolation guard, so the proposed conventions are in the rev 1
  hand-back, not in this file.
- This lane has no Bash. It ran no `mise`, `git`, `gh`, `fnox` or network probe.
- Every `V` row in PREMISES cites a `file:line` that this lane read during its own runs (rev 1 or rev 2).
- The fnox config was only queried with name-only `Grep -o -n`. No line content and no value was displayed.

**Rev 2 changelog** (the premise-report item each change answers is in brackets):

| Item | Change |
|---|---|
| (a) P18 | `additionalContextLimit` is a **token** threshold. P18 and §3.6 are reworded, and P40 is now cited from the KB codex docs. |
| (b) MISSING-1 | The pin-parity gate claim for webclaw is dropped, because `pin-parity.toml` has no webclaw entry and must not get one. Parity between the dotfiles, KB and user-global pins becomes a manual coordinator cross-check (§5.3). |
| (c) MISSING-2 | The live step-0 fixtures now anchor P25/P26/P42/P43. The CLI classifier must match the `Insufficient credits` text, because the scrape stderr carries no 402. There is a defensive branch for rc==0 with a `success:false` payload. The lane copies the fixtures into `tests/fixtures/research_fanout/`, which is on the allowlist (file 15). Step 0 is marked done. |
| (d) MISSING-3 | A manifest-derived provisional list. `_fanout_manifest_probe` emits per-manifest `provisional` lines, and the workflow probes the planner manifests. `provisionalRoutes` lives in `common` (`:734`) and reaches the result through `...common` at `:842`. It is **not** added at `:322`, which is only the retrospect `facts` map. |
| MISSING-4 | The mirror README gets a trailing `route` column and a provenance sentence (§3.7). |
| MISSING-5 | The HTTP status is persisted inside the hashed primary envelope for HTTP routes too, so forgery resistance covers exa and firecrawl-developer. Branch (c) bypasses the empty-body check (§3.3, §3.5). |
| MISSING-6 | `_fanout_manifest_probe`'s `required_failed` semantics are named as a residual (§4.6). |
| MISSING-7 | The redaction helper does not truncate before classifying (§3.2). |
| MISSING-8 | `AGENTS.md:9-10` is fixed. The parallel line in `codex-team-research/SKILL.md:30-31` is fixed too (§4.3). |
| MISSING-9 | The in-lane step at `research-sweep/SKILL.md:134` must use the mirror probe (§2 file 8). |
| MISSING-10 | `CREDIT_METERED_SOURCES` membership is now an `A` row (P44). |
| MISSING-11 | webclaw gets a separate `FileNotFoundError` handler (§3.7). |
| Accepted | P20/P23/P24/P39/P40 are accepted on record. |
| Also corrected | P31 and O2 now cite `~/.codex/AGENTS.md:16-17`. P28, Q9 and O3 reflect the ratified Q9 ruling. |

---

## 1. Objective

When a metered third-party research provider says its credits or quota are used up, the research tooling should stop
treating that as a hard failure. That answer is HTTP 402, a 429 with a quota message, or a provider's "Insufficient
credits" text, measured live in step 0 (P42, P43). The new behaviour:

1. **Classify it.** A credit or quota exhaustion is a distinct, typed route state, rendered `skipped:
   credits-exhausted`. It is never `error` and never silently `ok`.
2. **Substitute where a fallback exists.** This follows the webclaw pattern in knowledge-base
   `kb_setup/docs_mirror.py:399-419`:
   - the native route runs first;
   - the fallback runs only on an eligible condition;
   - the fallback's output is validated;
   - the row records which route produced it.

   The analogy is at the level of shape. KB falls back when a native fetch *succeeds in the wrong format*; this spec
   falls back on *credit exhaustion* (P21). The fallback routes are:
   - Firecrawl **search** falls back to Serper (`SERPER_API_KEY`), then SerpApi (`SERP_API_KEY`).
   - Firecrawl **scrape** (the mirror probe) falls back to `webclaw -f json`.
3. **Mark the receipt provisional.** The strict-five receipt still passes when a metered arm was credit-skipped or
   substituted, but it passes **provisional**. Every one of these surfaces names the route:
   - the manifest row;
   - the CLI summary line;
   - `validate_strict_five`'s reason;
   - the codex Stop hook;
   - the Claude workflow's status and result, for both mirror probes **and** planner fan-out manifests.

   Nothing passes silently.
4. **Keep genuine errors as failures.** These fail as they do today and never trigger a fallback:
   - auth failures (401/403);
   - 5xx;
   - timeouts;
   - malformed JSON;
   - a plain rate-limit 429 with no quota text;
   - any `github-*` source.

Both harnesses get this from one Python implementation (`research_fanout.py`):

- **Codex** gets it through the global research hook (`scripts/codex-research-gate.py`, run from a separate clone; see
  §5.3 O1).
- **Claude** gets it through the `research-sweep-run` workflow and the `research-sweep` skill.

This replaces the per-spec "named gap" rulings (handoff `docs/handoffs/session-2026-10-03n.md:131`).

It also reverses one documented rule. `python/src/dotfiles_setup/AGENTS.md:5-6` says "payment-required or failed sources
must remain visible as a failed receipt". Ray's request supersedes that for credit exhaustion only. Payment-required
stays *visible*; it stops being *failed*.

## 2. Files

The codex lane (`mise run sdlc-team`, implement mode) may touch **only** the paths below. Everything else is read-only
for the lane.

**Modify (Python and tests):**

1. **`python/src/dotfiles_setup/research_fanout.py`.** This holds:
   - the classifier;
   - the fallback routes;
   - the provisional receipt;
   - the mirror fallback;
   - the mirror README route column;
   - the per-manifest provisional lines in `_fanout_manifest_probe` (§3).
2. **`tests/test_research_fanout.py`.** Fan-out and strict-five arms (§5.1). Extending the `FakeHttp` double
   (`:215-238`) is in scope, because it keys on `payload["query"]` (`:236`) and Serper's body key is `q` (P23).
3. **`tests/test_research_fanout_probe.py`.** Mirror-probe webclaw arms, the README route column, and the
   fanout-manifest provisional lines.
4. **`scripts/codex-research-gate.py`.** Report a provisional pass through `systemMessage`, add the credit sentence to
   the submit context, and bump the policy string (§3.6).
5. **`tests/test_codex_research_gate.py`.** Provisional and failing Stop arms through the real hook entrypoint (the
   `:17-29` pattern).

**Modify (Claude side):**

6. **`.claude/workflows/research-sweep-run.js`.**
   - Mirror route provenance.
   - A planner-manifest provisional probe.
   - `provisionalRoutes` in `common`.
   - The `provisional` status (§3.7).
7. **`tests/test_workflows_js.py`.** Provisional arms, their controls, and an update to the pinned-routing test if a
   node is added.
8. **`.claude/skills/research-sweep/SKILL.md`.**
   - The mirror stage text (`:61-73`).
   - The status precedence (`:187-196`).
   - A new trap bullet.
   - **In-lane step 1 (`:134`).** Replace the instruction "save every link you were given with `mise exec --
     firecrawl scrape`" with the probe form `mise run research-fanout -- --probe-out <p> --mirror-url <u>
     --mirror-path <f>`. Only the probe carries the webclaw fallback [MISSING-9].
9. **`.claude/skills/codex-team-research/SKILL.md`.**
   - Step 3's "A failed arm is a blocker" (`:44-46`) gains the provisional exception.
   - `:30-31` "supplies Exa and Firecrawl credentials" gains Serper and SerpApi [MISSING-8].
10. **`.agents/skills/research-sweep/SKILL.md` and `.agents/skills/codex-team-research/SKILL.md`.** **Regenerate
    only**, with `mise run skills-mirror` (`mise.toml:1389-1392`). Never hand-edit them.
11. **`.claude/rules/research-doc-sources.md`.** "Always" item 4 (`:16-18`) gains one sentence: the mirror probe
    (`mise run research-fanout -- --probe-out … --mirror-url …`) falls back to webclaw when firecrawl answers credit
    exhaustion and records the mirror as provisional; a bare `firecrawl scrape` has no fallback.
12. **`python/src/dotfiles_setup/AGENTS.md`.** Rewrite `:3-6`, `:9-10` and `:16-20` with the text in §4.3. The file is
    under agnix AGM-003's 12,000-character limit.

**Modify (tool pin):**

13. **`mise.toml`.** Add `"github:0xMassi/webclaw" = "0.6.23"` beside the firecrawl pin (`:117-128`), with a comment
    citing KB `mise.toml:118-123`. Do **not** add a `pin-parity.toml` entry [MISSING-1].
14. **`mise.lock`.** Change it **only** by running the scoped `mise run lock -- "github:0xMassi/webclaw"`. A bare
    `mise run lock` is destructive.

**Create:**

15. **`tests/fixtures/research_fanout/`.** Byte-for-byte copies of the coordinator's live step-0 captures, from
    `/Users/rmanaloto/.claude/jobs/1854b55f/tmp/fc402/{search,scrape}.{out,err}`. Name them
    `firecrawl-402-search.out`, `firecrawl-402-search.err`, `firecrawl-402-scrape.out` and
    `firecrawl-402-scrape.err`.
    - The `.out` files are empty, and must stay empty files.
    - The captured exit code was 1 for both (P43, inherited). Record it as a named test constant whose comment cites
      the capture (2026-10-03 22:2x CDT, coordinator f9467b) and the two capture commands.
    - Do not edit the bytes.

**Never touched by the lane:**
- `~/.codex/**`, including `AGENTS.md`, `hooks.json` and the `tools/dotfiles-research-gate` clone;
- `~/.config/**`;
- `doctor.toml` (the Q9 change shipped separately, per RATIFICATION);
- `pin-parity.toml`;
- the knowledge-base repo;
- `docs/specs/research-fanout.md`;
- `task_plan.md`.

## 3. Interfaces

### 3.1 Types (`research_fanout.py`)

```python
class SkipReason(Enum):
    PREREQUISITE = "prerequisite"            # set on every existing SKIPPED row (_source_result :1090-1100)
    CREDITS_EXHAUSTED = "credits-exhausted"

@dataclass(frozen=True)
class RouteAttempt:
    route: str                 # source name for the primary; "serper" | "serpapi" | "webclaw" for fallbacks
    status: Status
    http_status: int | None    # None for a CLI route
    reason: str | None         # already redacted; never contains a credential value
    raw_file: str | None
    raw_sha256: str | None

@dataclass(frozen=True)
class SourceResult:            # existing fields unchanged (:128-139); NEW fields are all defaulted
    ...
    skip_reason: SkipReason | None = None
    route: str | None = None           # None = the primary produced this row; else the fallback route that did
    provisional: bool = False          # True iff skip_reason is CREDITS_EXHAUSTED or route is not None
    attempts: tuple[RouteAttempt, ...] = ()   # primary first, then each fallback TRIED; empty when no credit logic ran
```

`_Attempt` (`:199-203`) gains `http_status: int | None = None`, which `_http_json` (`:724-743`) fills in.

`Status` is unchanged. A credit skip is `Status.SKIPPED` with `skip_reason=CREDITS_EXHAUSTED` (Q1 was ratified as
drafted).

### 3.2 Classifier (public and pure)

```python
CREDIT_METERED_SOURCES: frozenset[str] = frozenset({"exa", "context7", "firecrawl-developer", "firecrawl-search"})

def is_credit_exhaustion(http_status: int | None, text: str) -> bool:
    """402 -> True. 429 -> True only when `text` matches _CREDIT_TEXT.
    http_status None (a CLI route) -> True when `text` matches _CREDIT_TEXT or a bare \\b402\\b.
    Every other status (401, 403, other 4xx, 5xx, 2xx) -> False REGARDLESS of text."""
```

**`_CREDIT_TEXT`** is case-insensitive.
- It **must** match the literal `Insufficient credits`. The scrape fixture (P43) carries no numeric 402, so the
  classifier depends on that text, not on 402 alone.
- The other seed terms are `payment required`, `out of credits`, `credits exhausted`, `quota exceeded` and `exceeded
  your quota`.
- `billing` alone is excluded, because it is too broad.
- The pattern must match **both** captured `.err` fixtures. The search fixture also contains `"status":402`.

**Applicability.** Classification runs only for sources in `CREDIT_METERED_SOURCES` and in the mirror probe.
- `github-*` is never classified.
- `last30days` is out of scope (Q6, ratified).

**Text inputs.**
- **HTTP routes** classify on `(status, body)`.
- **CLI routes** (`firecrawl-search`, `context7`, the firecrawl scrape) classify on `(None, redacted_stderr + "\n" +
  stdout)`.
- Factor the credential-value replacement out of `_subprocess_error` (`:548-565`) into one helper, for example
  `_redacted_stderr(completed, env) -> str`.
  - The helper **must not truncate**. `_subprocess_error`'s last-300-characters cut (`:565`) stays only in the
    human-readable reason string, and is applied after classification [MISSING-7].
  - The mirror probe (`:1850-1851`) classifies on the untruncated helper output.

**Defensive branch: rc == 0 with an error payload [MISSING-2].** The measured 402 exits 1 (P43). A future firecrawl
version could instead exit 0 with `{"success": false, ...}`, which would route to the empty-result path (`:1120-1138`)
or into `_scrape_payload` (`:1852-1853`) and never reach the classifier. So:
- `_firecrawl_search`, when `payload` is a dict with `success is False`, returns an `_Attempt` error. It classifies on
  `(payload["status"] if it is an int else None, <raw stdout text>)`.
- `_scrape_payload`, when the top-level payload has `success is False`, returns a failure reason. The mirror probe
  classifies that case the same way.
- Both branches need a test arm (§5.1 items 4b and 10b).

### 3.3 Fallback routes

```python
# NOT members of _SOURCE_NAMES (:62-71): that tuple is strict-five's REQUIRED set (:1521-1527), _persist's
# owned-file list (:1365-1369) and the --sources allowlist (:1275).
_FALLBACK_ROUTES: Mapping[str, tuple[str, ...]] = MappingProxyType({"firecrawl-search": ("serper", "serpapi")})
_FALLBACK_KEYS = MappingProxyType({"serper": "SERPER_API_KEY", "serpapi": "SERP_API_KEY"})
```

**`Endpoint`** (`:103-107`) and `default_http` (`:407-446`) gain two members, using the same bounded-read path:
- `SERPER_SEARCH`: `POST https://google.serper.dev/search`, header `X-API-KEY`, JSON `{"q": query, "num": limit}`.
- `SERPAPI_SEARCH`: `GET https://serpapi.com/search.json` with `engine=google`, `q`, `num` and `api_key`.

These request shapes are **UNVERIFIED and accepted on record** (P23, P24). The lane must:
- confirm them against the provider's own docs, via the `.claude/rules/research-doc-sources.md` chain, before coding;
- cite the docs URLs in the commit body;
- let the docs win over this spec if they disagree, and record the difference.

**Credential handling.**
- Both keys go through `_credential_header` (`:568-575`).
- No URL may appear in any reason, exception message, raw file or stdout, because SerpApi's key is in the query string.
- Normalisation is route-specific: Serper uses `organic[]` and SerpApi `organic_results[]`, each with `title`, `link`,
  `snippet` and `date`.
- Do **not** widen `_records` (`:490-502`) or `_record_item`'s url keys (`:461`).

**Run order** (in `_source_result`). Run the primary first.

- **The primary is credit-exhausted and the source has a fallback.** Try each route in order.
  - A route whose key is absent is recorded as `RouteAttempt(route, SKIPPED, None, "<KEY> not inherited; run through
    fnox exec", None, None)`.
  - The first route that answers `ok` or `empty_verified` wins, with `route` set and `provisional=True`. An empty
    fallback answer uses `_empty_control` on the fallback route, with canary `"python"`.
  - If every tried route is credit-exhausted or absent, the row is `SKIPPED` with `CREDITS_EXHAUSTED` and
    `provisional=True`.
  - If any tried route had a genuine error and none succeeded, the row is `ERROR` (Q4, ratified as drafted). If a later
    route succeeds, the earlier error stays listed in `attempts` and in the provisional line.
- **The primary is credit-exhausted and the source has no fallback** (exa, context7, firecrawl-developer). The row is
  `SKIPPED` with `CREDITS_EXHAUSTED` and `provisional=True`.
- **Any other primary error.** No fallback runs, and the row is `ERROR` as today.

**Persistence** (`_persist`, `:1356-1401`).
- `<source>.raw` holds the bytes of the route that produced the final status. For a credit-skipped row, that is the
  primary envelope below.
- Each attempt's evidence is written to `<source>.<route>.raw`, and the primary's to `<source>.primary.raw`.
- **The primary evidence is always a JSON envelope, for HTTP and CLI routes alike [MISSING-5]:**
  `{"http_status": int | null, "rc": int | null, "body": str, "stderr_redacted": str}`.
  - `body` is the HTTP body, or the stdout for a CLI.
  - `http_status` is null for a CLI and `rc` is null for HTTP.
  - Because the status sits inside the hashed bytes, the validator re-derives the classification from bytes alone and
    never trusts `attempts[0].http_status`. A forged row that claims `http_status: 402` over a 500 envelope fails.
- `owned_names` (`:1365-1369`) must include every new filename pattern (the `:1753-1799` test pattern).
- `policy_version` becomes `strict-five-v2` (Q2, ratified). It is used at `:1395` and `:1514`.

**Summary line** (`_print_summary`, `:2133-2141`). The columns are unchanged; only the bracketed reason is extended:
```
firecrawl-search  ok  5 items  1.234s  [provisional: via serper; firecrawl-search credits-exhausted (Insufficient credits)]
firecrawl-developer  skipped  0 items  0.412s  [skipped: credits-exhausted (HTTP 402); no fallback route]
```

**Process rc (non-strict, `:2190-2191`).** The success set is unchanged. A provisional `ok` counts toward rc=0; a credit
`SKIPPED` does not (Q3, ratified: stay rc=1).

### 3.4 `--list-sources`

The eight existing lines are unchanged (`:1296-1301`; the test parses the last column at `:1856-1865`). After them,
three presence-only lines are appended:
```
fallback:serper  HTTPS POST  SERPER_API_KEY in process environment  present|absent
fallback:serpapi  HTTPS GET  SERP_API_KEY in process environment  present|absent
fallback:webclaw  webclaw CLI  webclaw on PATH  present|absent
```

### 3.5 Strict-five verdict

```python
@dataclass(frozen=True)
class StrictVerdict:
    passed: bool
    provisional: tuple[str, ...]   # e.g. "firecrawl-search via serper (credits-exhausted: Insufficient credits)"
    reason: str

def strict_five_verdict(manifest_path: Path, request_id: str) -> StrictVerdict: ...
def validate_strict_five(manifest_path: Path, request_id: str) -> tuple[bool, str]:
    # signature UNCHANGED. Reason "all required sources completed" when not provisional,
    # else "provisional: " + "; ".join(lines).
```

Row acceptance extends `:1404-1425` and `:1487-1503`. There are three cases.

**(a) Not provisional.** The existing checks apply byte-for-byte.

**(b) Provisional and substituted.** The row is ok or empty_verified, with `route` set. All of these must hold:
- the source is in `_FALLBACK_ROUTES`, and `route` is in its tuple;
- `provisional` is true;
- `attempts[0].route == source`;
- the primary envelope exists, its hash matches, and it **re-classifies** from its own bytes as credit exhaustion;
- the route raw validates against its route-specific shape (a list, non-empty for `ok`);
- every named attempt raw has a matching hash.

**(c) Provisional and skipped.** The row is `skipped` with `skip_reason == "credits-exhausted"`.
- The source must be in `CREDIT_METERED_SOURCES`.
- The primary envelope must re-classify as credit exhaustion.
- This branch **bypasses** the `raw evidence is empty` check (`:1499-1500`) on the envelope's `body` field, because a
  402 can arrive with an empty body [MISSING-5]. The envelope itself is never empty, and its hash is still checked.

**Rejected.**
- A `skipped` row with any other `skip_reason`, or none, fails.
- An envelope that does not re-classify fails with `"<source> credit-exhaustion evidence does not re-derive"`.

The required set (`:1525`) is unchanged.

### 3.6 Codex hook (`scripts/codex-research-gate.py`)

**`_on_stop`** (`:100-120`) uses `strict_five_verdict`:
- passed and not provisional: return `{}`;
- passed and provisional: return `{"systemMessage": "Research receipt PROVISIONAL (credit-exhausted provider): " +
  "; ".join(verdict.provisional) + ". Say so in the answer."}` (Q5, ratified: non-blocking);
- not passed: unchanged.

**`_on_submit`** (`:80-91`) gains one sentence: "A provider out of credits (HTTP 402 or quota 429) is recorded
`skipped: credits-exhausted` or substituted, and the receipt passes PROVISIONAL; report it." The policy string at
`:75` and `:81` becomes `strict-five-v2`.

**Context length.**
- The configured `additionalContextLimit` (`~/.codex/hooks.json:9`, value 1000) is an **approximate token** threshold,
  not a character count (KB `sources/agent-harness-docs/docs/codex/hooks.md:453`, `:464`).
- Over that threshold, Codex saves the full text to disk and sends the model a shorter preview (`:185-186`).
- The test keeps the whole submit string **≤ 1000 characters** for a long `REPO_ROOT` (see §5.1 item 14). That is
  stricter than 1000 tokens, so the context is never previewed.

### 3.7 Mirror probe, README and the workflow

**`_mirror_probe`** (`:1812-1872`):

**Fallback trigger.** The firecrawl scrape fails, by a non-zero exit or by the rc==0 `success:false` branch of §3.2.
The untruncated redacted text must also satisfy `is_credit_exhaustion(None, text)`. Only then does the probe run
`webclaw -f json <url>`, with `child_env.clean_env()` and no credentials. This follows the KB parse at
`docs_mirror.py:228-238`.

**The webclaw call has its own `try`** [MISSING-11]:
- `FileNotFoundError` gives rc=127 and reason `credits-exhausted; webclaw not found on PATH`. It must not reuse the
  firecrawl handler at `:1859-1860`, which says "firecrawl not found on PATH".
- `subprocess.TimeoutExpired` gives rc=124 and reason `credits-exhausted; webclaw timed out`.

**Accept** only when both hold:
- `markdown.strip()` is non-empty;
- the final URL equals the requested URL. Compare scheme, host and path, strip trailing `/`, and ignore the fragment.

Otherwise, use reason `credits-exhausted; webclaw redirected to <final>` or `credits-exhausted; webclaw rc=<n>`, and
write nothing.

**Probe row fields.**
- `route` is `"firecrawl"` or `"webclaw"`.
- `provisional` is a bool.
- `primary_reason` is the redacted credit text, or `""`.
- On a webclaw success, `http_status` is `0` (P20, accepted on record).

**Non-credit firecrawl failure:** no webclaw call, and the row is unchanged.

**`_mirror_index_probe` README** (`:1897-1955`) [MISSING-4]:
- Append a trailing `route` column to the table header and every row. A probe file with no `route` field renders as
  `firecrawl`.
- Extend the header paragraph (`:1945-1949`) with this sentence: "When firecrawl answered credit exhaustion the link was
  fetched with `webclaw -f json` instead (route `webclaw`, provisional)."
- The existing README assertions (`tests/test_research_fanout_probe.py:446-449`) are substring matches ending in `|  |`.
  They stay valid because the new column is appended at the end.

**`_fanout_manifest_probe`** (`:1758-1809`) [MISSING-3]:
- Each row gains `provisional: [str, ...]`, with one line per manifest source row whose `provisional` is true, in the
  §3.5 line format.
- It is derived from the manifest's own rows: `route`, `skip_reason` and the attempts' reasons.
- `required_failed` is unchanged (§4.6).

**Workflow `research-sweep-run.js`:**

- **Mirror.** The `mirror` mapper (`:488-498`) copies `route`, `provisional` and `primaryReason`. `mirrored()` (`:499`)
  is unchanged, so a provisional mirror is still a mirror.
- **Planner manifests [MISSING-3].**
  - When `planManifests` (`:580`) is non-empty, run one probe in the same `Promise.all` as triage (`:608-620`):
    `probeCmd(PLAN_MANIFEST_PROBE, planManifests.map(m => '--fanout-manifest ' + shq(m)))`.
    `PLAN_MANIFEST_PROBE` is `${FANOUT_DIR}/plan/manifests.json`.
  - Use the same agent type, model and effort as the existing `mirrorIndex` node (`:619`), with schema `PROBE`. Read it
    back with `readProbe`.
  - If that probe returns no PROBE-JSON, add the `fanoutGaps` entry `planner provisional check did not run`. Do not
    treat this as a mandatory gap.
- **Dependency manifests.** The probes already read here (`:458`) also contribute their rows' `provisional` lines.
  GitHub is never classified, so this is expected to be empty, but read it anyway rather than assume it.
- **`provisionalRoutes`.** This is the union of:
  - each provisional mirror, as `${url}: mirrored via webclaw (${primaryReason})`;
  - each planner or dependency manifest provisional line, as `${manifestPath}: ${line}`.

  Define it in `common` (`:734`), which reaches the result through `...common` at `:842`. Add it to the synthesis
  prompt beside `MIRROR GAPS` (`:726`). Do **not** add it at `:322`.
- **Status.** `statuses` (`:834-840`) gains `provisionalRoutes.length ? 'provisional' : ''` as the **last** entry (Q7,
  ratified).

## 4. Constraints and invariants

### 4.1 Hard constraints

- **Zero bash logic.** There is no new `.sh` file.
- **No inline suppressions** (`no_lint_skip`).
- **Never print a secret value.**
  - The fallback keys are used only in headers and params.
  - A sentinel test covers every reason, summary line, envelope, `--list-sources` line, README and hook message.
  - Redaction uses `child_env.is_credential`, which already matches `_API_KEY` (`child_env.py:49-57`).
- **Genuine errors are never laundered.** None of the following triggers a fallback or a credit skip:
  - 401, 403, or any other non-402 4xx;
  - a 429 with no quota text;
  - 5xx, a timeout, or invalid JSON;
  - any `github-*` source.
- **`_SOURCE_NAMES` is not extended.**
- **Hermetic tests.**
  - Each credit-path test sets or deletes `SERPER_API_KEY`, `SERP_API_KEY`, `FIRECRAWL_API_KEY` and `EXA_API_KEY`, and
    controls `PATH` for webclaw.
  - The ambient shell carries `env = true` secrets (`doctor.toml:39-96`, which gains both keys per Q9), so a test must
    never rely on it.
- **The fixtures are real.** The CLI classifier is tested against the copied live fixtures, not invented text.

### 4.2 Lane prohibitions

The guard cannot see codex shell commands, so these are stated explicitly. The lane must NOT:
- run `fnox`;
- `echo` or `printf` a credential variable;
- write `env`, `printenv` or `export -p` output into a tracked file;
- run a bare `mise run lock`, `git commit`, `git push`, `gh pr *`, `mise run ship` or `mise run land`;
- edit `~/.codex`, `~/.config`, `doctor.toml`, `pin-parity.toml` or the knowledge-base repo;
- hand-edit `.agents/skills/**`;
- write `task_plan.md`.

The lane MAY:
- run `mise run lock -- "github:0xMassi/webclaw"`, `mise run skills-mirror`, `mise run fmt` and the §5.2 gates;
- read the fixture directory `/Users/rmanaloto/.claude/jobs/1854b55f/tmp/fc402/` in order to copy it.

### 4.3 Replacement text for `python/src/dotfiles_setup/AGENTS.md`

Replace `:3-6` with:

> For a live research request, use the strict five-provider receipt. Create a Last30Days plan whose `subqueries` list
> names only the active sources relevant to the question. Failed sources remain visible as a failed receipt and never
> count as evidence. The one exception is a metered provider that answers credit or quota exhaustion (HTTP 402, a 429
> with quota text, or "Insufficient credits"). That provider is recorded `skipped: credits-exhausted` or substituted:
> Firecrawl search goes to Serper/SerpApi, and scrape goes to webclaw. The receipt then passes **provisional** and names
> the route. Report that; never present it as complete.

Replace `:9-10` [MISSING-8] with: "The native `fnox exec` process receives the Exa, Firecrawl, Serper (`SERPER_API_KEY`)
and SerpApi (`SERP_API_KEY`) keys from that profile."

At `:16-20`, append: "A provisional pass is not a failure, but the answer must name every provisional route the
manifest lists."

### 4.4 Invariants a reviewer can check

Each line below is a mutation the reviewer can make, and the test it should break.

- Remove the `is_credit_exhaustion` call from `_source_result`. The 402 arm goes red, and the 500 arm stays green.
- Make the classifier return True for 500. The 500 control arm goes red.
- Delete the envelope re-classification in the strict validator. The forged-receipt arms go red, for HTTP **and** CLI.
- Drop `insufficient credits` from `_CREDIT_TEXT`. The scrape-fixture arm goes red, and the search fixture still passes
  on `402`.

### 4.5 Open choices

All are **ratified** (see RATIFICATION):
- Q1–Q8 and Q10 are as drafted in rev 1: SKIPPED plus `skip_reason`; `strict-five-v2`; rc=1 for a credit-only run; the
  Q4 drafted rule; a non-blocking systemMessage; last30days out of scope; the `provisional` status; Serper before
  SerpApi; save the spec as `docs/specs/research-credit-fallback.md`.
- Q9: Ray ruled "Add both to env_true". This shipped separately as `chore/serp-api-key-doctor` 1ba74fab, so the lane
  does not touch `doctor.toml`.

### 4.6 Named residuals (deliberately not changed)

- **`_fanout_manifest_probe`'s `required_failed`** (`:1801-1807`). It still counts any non-`ok`/`empty_verified`
  required source as failed, so a credit-skipped `--require`d source would land there [MISSING-6]. This is
  non-blocking today, because the workflow's only `--require` is `DEP_SOURCES = 'github-issues,github-discussions,
  github-releases'` (`research-sweep-run.js:129`), and GitHub is never classified. If a metered source is ever
  required, revisit this.
- **last30days' internal provider credit exhaustion** (Q6). File a follow-up issue.
- **Capture argv.** The step-0 captures used a shorter argv than the fan-out's (P45). The rc==0 defensive branch and
  live arm R1 cover the difference.

## 5. Verification

### 5.1 Tests the lane writes

Expected values come from fixtures or literals and are never recomputed. Each item names its arm.

**`tests/test_research_fanout.py`**

1. **Classifier table.** Each input and its expected result:

   | Input | Expected |
   |---|---|
   | `(402, "")` | True |
   | `(429, "quota exceeded")` | True |
   | `(429, "rate limit")` | False |
   | `(401, "Insufficient credits")` | False |
   | `(500, "payment required")` | False |
   | `(None, <firecrawl-402-search.err bytes>)` | True |
   | `(None, <firecrawl-402-scrape.err bytes>)` | True (text only, no 402) |
   | `(None, "connection reset")` | False |

2. **402 arm.** firecrawl-developer gets HTTP 402. Expect `skipped`, `skip_reason == "credits-exhausted"`,
   `provisional`, and zero further HTTP calls. Then run it again with an **empty** 402 body: still skipped, and the
   strict validator still accepts it (the branch (c) bypass).
3. **500 control.** The same with HTTP 500. Expect `error` with reason `HTTP 500`, not provisional, and no fallback
   call.
4. **Substitution arm.**
   - The runner returns rc=1, the empty `firecrawl-402-search.out` as stdout, and `firecrawl-402-search.err` as stderr.
     `SERPER_API_KEY` is a sentinel.
   - Expect a `SERPER_SEARCH` call. The row is `ok` with `route == "serper"`, provisional, and items taken from `link`.
   - The envelope `<source>.primary.raw` carries `rc: 1`.
   - The sentinel appears in no output or file.
   - **4b (rc==0 `success:false`).** The runner returns rc=0 with stdout `{"success":false,"error":"Insufficient
     credits …","status":402}`. Expect the same substitution, not `empty_unverified`.
5. **Chain arm.** The serper key is absent, so the route is `serpapi`, and `attempts[1]` is serper `SKIPPED` "not
   inherited". SerpApi's sentinel appears nowhere.
6. **Fallback genuine error (Q4).** serper returns 500 and the serpapi key is absent. Expect `ERROR`.
7. **Strict-five arms.**
   - A fully provisional manifest gives `(True, "provisional: …")`.
   - **Forged CLI receipt.** The primary envelope is replaced by an rc=1 auth-error envelope and rehashed. Expect False,
     "does not re-derive".
   - **Forged HTTP receipt.** A firecrawl-developer skipped row whose envelope says `http_status: 500` but whose row
     claims 402. Expect False.
   - A `skip_reason == "prerequisite"` row gives False.
   - A credit-skipped `github-issues` row gives False.
   - A non-provisional manifest's reason is exactly `"all required sources completed"`.
   - `policy_version` `strict-five-v1` gives False ("request identity or policy mismatch").
8. **Reused output directory.** Stale `<source>.*.raw` files are removed.
9. **`--list-sources`.** The three `fallback:*` lines are present, the eight lines are unchanged, and no value appears.

**`tests/test_research_fanout_probe.py`**

10. **Mirror credit arm.**
    - The scrape returns rc=1, the `firecrawl-402-scrape.out` and `.err` fixtures, and webclaw JSON with a matching
      `metadata.url`.
    - Expect `route: "webclaw"`, `provisional: true`, `reason: ""`, the file written, and a README row whose `route`
      cell is `webclaw`.
    - **10b.** rc=0 with a `success:false` scrape payload falls back the same way.
11. **Mirror controls.**
    - A non-credit failure (an rc=1 auth-error stderr) causes no webclaw argv.
    - An off-site webclaw redirect is rejected and nothing is written.
    - webclaw is missing: rc 127, and the reason names **webclaw**, not firecrawl.
12. **Fanout-manifest provisional lines.** A manifest with one provisional row gives that row's `provisional` line. The
    control, an all-`ok` manifest, gives `provisional == []`.

**`tests/test_codex_research_gate.py`** (real hook subprocess)

13. A provisional v2 manifest makes Stop return a `systemMessage` containing `PROVISIONAL` and no `decision`.
14. A manifest whose primary envelope does not re-derive makes Stop return `decision: block`.
15. The submit context is ≤ 1000 characters when the script runs from a long temporary path. `REPO_ROOT` comes from
    `__file__` (`:14`), so the test must copy the script there. Its marker says `strict-five-v2`.

**`tests/test_workflows_js.py`**

16. A provisional mirror probe row gives a `provisionalRoutes` of length 1, a `statuses` that includes `'provisional'`,
    and `status === 'provisional'`.
17. A planner-manifest probe with one provisional line gives `provisionalRoutes` with that line, and
    `status === 'provisional'`.
18. **Control.** No provisional rows anywhere gives no `'provisional'` and `status === 'complete'`. Update the pinned
    routing test for the new node.

**Mutation check.** Run each §4.4 mutation once, confirm which test goes red, revert it, and report the result.

### 5.2 Gates (each through `mise run gate -- run <name>`; read the real rc)

- `lint`, `pytest`, `verify`.
- `lint-docs`, because AGENTS.md, a rule and skills changed.
- `mise run skills-mirror -- --check`, which must give rc 0.
- `mise ls --current github:0xMassi/webclaw`. The source column must name `mise.toml`.
- **There is no pin-parity gate for webclaw** [MISSING-1]. `pin_parity.py:94-106` reads only `pin-parity.toml` sites,
  which are resolved under the project root, and that file has no webclaw entry. Cross-repo parity is a manual check
  (§5.3).

### 5.3 Coordinator and operator actions

**Step 0: DONE.** The coordinator captured the fixtures live, 2026-10-03 22:2x CDT, into
`/Users/rmanaloto/.claude/jobs/1854b55f/tmp/fc402/`. Ray chose not to top up, so the 402 condition persists
(RATIFICATION).

**Manual pin cross-check [MISSING-1].** After the lane returns, the coordinator reads the new dotfiles `mise.toml` webclaw
line, KB `mise.toml:123` and `~/.config/mise/config.toml:226`, and confirms all three say `0.6.23`.

**Dispatch.** Run `mise run sdlc-team -- request.json` (implement mode) in its own worktree, on a fresh branch.

**Real-integration arms.** These run from the main session through `mise run research-fanout`:
- **R1 (substitution).** `fnox … exec -- mise run research-fanout -- "mise tasks" --sources firecrawl-search --out
  $TMP/r1`. Expect `ok [provisional: via serper …]` and rc 0. Once Q9's `env_true` change is live, also run it
  **without** fnox, which is the Claude-side path.
- **R2 (genuine failure still fails).** The same command with `FIRECRAWL_API_KEY` set to an invalid fresh-nonce value.
  Expect `error` (401/auth) and no fallback attempt. This arm checks itself: if the reason says credits, the override
  never reached the child, and the arm is VOID, not passed.
- **R3 (mirror).** `--probe-out $TMP/p.json --mirror-url https://mise.jdx.dev/tasks/ --mirror-path $TMP/m.md`. Expect
  `route webclaw`, `provisional true` and `bytes > 0`. Its control is a fresh-nonce 404 path: expect a reason and no
  file.
- **R4 (strict receipt end-to-end).**
  - Run `--strict-five` into a temporary `HOME/.codex/research-coverage/<s>/<t>/`.
  - Pipe a Stop event into the gate script.
  - Expect `strict-five pass [provisional: …]` and a `PROVISIONAL` systemMessage.

**Operator items:**
- **O1.** After merge, run `git -C ~/.codex/tools/dotfiles-research-gate pull --ff-only` (the clone is on `main`, and
  `hooks.json:7`/`:19` point to it). Then re-run R4 against the clone's script.
- **O2.** In `~/.codex/AGENTS.md:16-17`, append to "A failed arm is a recorded blocker, not a successful five-provider
  audit.": "; an arm skipped or substituted for credit exhaustion passes PROVISIONAL and must be named in the answer."
  Also, `:11` "This profile injects Exa and Firecrawl" gains Serper/SerpApi. This is Ray's or the operator's edit only.
- **O3.** Q9 is resolved (1ba74fab). Confirm it ships before R1's no-fnox run.
- **O4.** File a follow-up for last30days credit handling (Q6). The KB copy of `research-doc-sources` is optional,
  because rule-sync checks stems only.

## 6. Commit

`COMMIT: caller`. The lane leaves the tree uncommitted, per the precedent in `docs/specs/research-fanout.md:6-7`. The
architect commits after the gates and an Opus diff-only cold review.

```
feat(research-fanout): credit-exhausted route state + provisional fallbacks

A metered provider answering HTTP 402, a quota 429, or "Insufficient
credits" is now `skipped: credits-exhausted` instead of `error`; Firecrawl
search falls back to Serper/SerpApi and the mirror probe's scrape to
webclaw (KB docs_mirror pattern). Evidence is a hashed envelope carrying
the HTTP status or rc, so the strict-five-v2 receipt re-derives every
provisional row from bytes and passes PROVISIONAL, naming each route; the
codex Stop hook and the research-sweep workflow (mirrors and planner
manifests) surface it. Auth failures, 5xx, timeouts and plain rate limits
still fail. Fixtures: live firecrawl 402 captures, 2026-10-03.

Provider request shapes verified against: <URLs the lane cites>.
Live arms R1-R4: <rc + manifest paths>.
```

Ship it with `mise run ship`.

## 7. PREMISES

Legend:
- `V`: verified by this lane's own read at the cited `file:line`.
- `A`: assumed or inherited, with the reason given.
- `A (accepted)`: an assumption the coordinator accepted on record.

| # | Premise | Status | Provenance |
|---|---|---|---|
| P1 | `Status` has exactly OK, EMPTY_VERIFIED, EMPTY_UNVERIFIED, ERROR, SKIPPED | V | `python/src/dotfiles_setup/research_fanout.py:93-100` |
| P2 | `_SOURCE_NAMES` has eight sources, and strict-five requires exactly that set | V | `research_fanout.py:62-71`, `:1521-1527` |
| P3 | An HTTP non-2xx becomes the error `"HTTP {status}"`, and the status is not otherwise kept | V | `research_fanout.py:737-738` |
| P4 | A CLI failure's text is in redacted stderr, truncated to the last 300 characters; raw is stdout only | V | `research_fanout.py:534-537`, `:548-565` |
| P5 | firecrawl-search keeps only `FIRECRAWL_API_KEY` | V | `research_fanout.py:801-827` |
| P6 | SKIPPED today means a missing prerequisite | V | `research_fanout.py:967-985`, `:1089-1100` |
| P7 | The strict row check accepts only ok/empty_verified | V | `research_fanout.py:1404-1408` |
| P8 | The strict firecrawl-search raw requires `data.web` and `success: true` | V | `research_fanout.py:1438-1441`, `:1458-1459` |
| P9 | `_persist` unlinks only owned names derived from `_SOURCE_NAMES`, and writes body bytes only | V | `research_fanout.py:1365-1375` |
| P10 | `strict-five-v1` is written and checked by equality | V | `research_fanout.py:1395`, `:1514` |
| P11 | Non-strict rc is 0 iff any source is ok or empty_verified | V | `research_fanout.py:2190-2191` |
| P12 | The mirror probe runs `firecrawl scrape … --json`, and FileNotFoundError says "firecrawl not found on PATH" | V | `research_fanout.py:1835-1872` (`:1859-1860`) |
| P13 | `mirrored()` is `rc===0 && bytes>0 && !reason` | V | `.claude/workflows/research-sweep-run.js:499-501` |
| P14 | `statuses` is defined at `:834-840`, and the result is built from `...common` at `:842` | V | `research-sweep-run.js:834-842` |
| P15 | The Claude workflow runs plain `mise run research-fanout` (no fnox) | V | `research-sweep-run.js:179`, `:382`, `:408` |
| P16 | The codex gate imports `validate_strict_five` from its own checkout and returns `{}` on pass | V | `scripts/codex-research-gate.py:14-19`, `:100-103` |
| P17 | The submit context hard-codes `strict-five-v1` and `mise -C {REPO_ROOT}` | V | `scripts/codex-research-gate.py:75`, `:80-91` |
| P18 | The global hooks run the gate from `~/.codex/tools/dotfiles-research-gate`, with `additionalContextLimit` 1000, an **approximate token** threshold, and 5 s timeouts | V | `~/.codex/hooks.json:7-9`, `:19-20`; units: KB `sources/agent-harness-docs/docs/codex/hooks.md:453`, `:464` |
| P19 | That clone's HEAD is `refs/heads/main` | V | `~/.codex/tools/dotfiles-research-gate/.git/HEAD:1` |
| P20 | webclaw: a 404 exits 1 with empty stdout; success gives `content.markdown`/`metadata.url`; there is no status field | A (accepted) | KB `python/src/kb_setup/docs_mirror.py:222-238`. "No status field" is inferred from what the code reads. |
| P21 | The webclaw fallback pattern: native first, fallback when eligible, final URL validated, provenance recorded. The KB trigger is a native *success in the wrong format*. | V | KB `docs_mirror.py:399-419` (`:403-409`), `:456` |
| P22 | webclaw 0.6.23 is pinned in KB and user-global, and absent from dotfiles | V | KB `mise.toml:118-123`; `~/.config/mise/config.toml:226`; the dotfiles `*.toml` grep found no webclaw (control `firecrawl-cli` `mise.toml:128`) |
| P23 | Serper request/response shape | A (accepted) | Model knowledge; the lane verifies it against the provider's docs |
| P24 | SerpApi request/response shape | A (accepted) | Same |
| P25 | Firecrawl was answering credit exhaustion on 2026-10-03, and Ray is not topping up | V | Fixtures `/Users/rmanaloto/.claude/jobs/1854b55f/tmp/fc402/search.err:1`, `scrape.err:1`; RATIFICATION (this file, "Firecrawl stays un-topped-up") |
| P26 | On a credit 402, the firecrawl CLI writes nothing to stdout | V | `fc402/search.out` and `scrape.out` read this run; both empty |
| P27 | `SERPER_API_KEY`/`SERP_API_KEY` are declared in fnox `[secrets]` and the `codex_research` profile | V | `~/.config/fnox/config.toml:82-83`, `:90`, `:93-94` (name-only grep) |
| P28 | Neither key is in **this checkout's** `doctor.toml` `env_true`. Ray ruled to add both, shipped separately as 1ba74fab. | V / A | `doctor.toml:39-96` (`:91`→`:92`; control `:54`) is V. The 1ba74fab delivery is inherited from RATIFICATION and was not read. |
| P29 | `_API_KEY` names are credentials for redaction | V | `python/src/dotfiles_setup/child_env.py:49-57` |
| P30 | The receipt contract says payment-required must be a failed receipt; `:9-10` names only Exa and Firecrawl keys | V | `python/src/dotfiles_setup/AGENTS.md:3-6`, `:9-10` |
| P31 | The global codex rule says a failed arm is a blocker | V | `~/.codex/AGENTS.md:16-17` |
| P32 | The skill mirror is generated by `mise run skills-mirror` | V | `mise.toml:1389-1392` |
| P33 | `research-doc-sources` is rule-synced by stem only | V | `rule-sync.toml:51-56`, `:73` |
| P34 | `FakeHttp` keys on `payload["query"]` | V | `tests/test_research_fanout.py:224-238` |
| P35 | The `--list-sources` test parses the last two-space column | V | `tests/test_research_fanout.py:1856-1865` |
| P36 | The codex hook tests run the real script with `HOME` overridden | V | `tests/test_codex_research_gate.py:14-29` |
| P37 | The shipped spec is a record, and `COMMIT: caller` has precedent | V | `docs/specs/research-fanout.md:3`, `:6-7` |
| P38 | Real-integration evidence needs a public entrypoint run plus a failure arm | V | `.claude/rules/real-integration-evidence.md:6-11` |
| P39 | `auto_install = true` lets the clone install the pinned webclaw | A (accepted) | `mise.toml:132` read; the install in the clone is inferred, and would surface in R4 |
| P40 | Over the limit, Codex saves the full text and sends a shorter preview; it does not reject | V (accepted) | KB `sources/agent-harness-docs/docs/codex/hooks.md:185-186` |
| P41 | No dotfiles code calls webclaw; the "existing fallback" is the KB docs mirror | V | dotfiles grep: only `docs/**` hits; control: KB grep hits `docs_mirror.py` |
| P42 | The search 402 stderr is `Error: {"success":false,"error":"Insufficient credits to perform this request. …","code":"ERR_BAD_REQUEST","status":402}` | V | `/Users/rmanaloto/.claude/jobs/1854b55f/tmp/fc402/search.err:1` |
| P43 | The scrape 402 stderr is `Error: Insufficient credits to perform this request. …`, with **no** numeric 402. Both commands exited rc=1. | V / A | Text: `fc402/scrape.err:1` (V). rc=1: inherited from the coordinator annotation at premise report `:8`, `:10`. There is no rc file in `fc402/`. |
| P44 | `context7` and `firecrawl-developer` can answer 402/quota; firecrawl-developer is keyless with an optional key | A | Membership in `CREDIT_METERED_SOURCES` is assumed [MISSING-10]. Keylessness is seen at `research_fanout.py:84`, `:783-787`. Low risk, because classification still needs 402 or quota text. |
| P45 | The capture argv differs from the fan-out's: no `--sources web --json` (search), and no `--only-main-content --json` (scrape) | A | Premise report `:8`, `:10` (inherited). Whether those flags change the error output is unmeasured; the rc==0 branch and R1 cover it. |
| P46 | The triage prompt surfaces only `empty_unverified`/`error` sources, so planner provisional rows need their own probe | V | `research-sweep-run.js:615-616` |
| P47 | Planner manifests are agent-reported paths, not probed | V | `research-sweep-run.js:580-585` |
| P48 | The README assertions are substring matches, which a trailing `route` column preserves | V | `tests/test_research_fanout_probe.py:446-449` |
| P49 | `pin_parity` reads only `pin-parity.toml` sites, resolved under the project root, and `pin-parity.toml` has no webclaw section | V | `python/src/dotfiles_setup/pin_parity.py:94-106`; `pin-parity.toml:43`, `:46`, `:61`, `:72`, `:84`, `:123` (section headers only) |

## RATIFICATION (coordinator f9467b, 2026-10-03 ~22:20 CDT)
- Q1–Q8, Q10: recommendations as drafted (Ray: "No, proceed").
- Q9: RAY RULED "Add both to env_true". Already delivered by `chore/serp-api-key-doctor` 1ba74fab (doctor.toml +SERPER_API_KEY +SERP_API_KEY), ship-queue item 4. The lane does NOT touch doctor.toml.
- Firecrawl stays un-topped-up (Ray 22:05), so the 402 condition persists for step-0 fixture capture.
- Dispatch is gated on the premise-verifier result.

## REV 2.1 ADDENDUM (coordinator f9467b, from premise report rev 2 — these OVERRIDE the body where they conflict)
Report: docs/research/kb/reports/agents/premise-verifier-credit-fallback-spec-rev2.md (branch docs/handoff-2026-10-03q).
- **A (blocking):** when the mirror probe's webclaw fallback succeeds, the row's `rc` is webclaw's rc (0), so `mirrored()`/`m.rc === 0` (research-sweep-run.js:497,499) counts it as mirrored; `reason` is "" and `route: "webclaw"`, `provisional: true`. The README rc cell shows webclaw's rc (0), and the new `route` column shows `webclaw`.
- **B (blocking):** §4.3 replaces `python/src/dotfiles_setup/AGENTS.md:9-11`, not `:9-10`. Keep the Doppler sentence ("Fnox resolves its Doppler token internally with `env = false`.") intact.
- **C (blocking):** §3.3's "no URL" rule is SCOPED. It applies to the *request* URL (and query strings) and to any key-bearing string. Provider text in stderr, such as `https://firecrawl.dev/pricing`, is evidence: keep it in the redacted envelope and in reasons. The sentinel test asserts the absence of the request URL and key material, not of all URLs.
- **D:** extend `_Attempt`/`_run_json` to carry the CLI `rc` and the untruncated redacted stderr.
- **E:** P43 is re-cited to `fc402/rc.txt:1-3`.
- **F (residual, §4.6):** the deep-read paths `research-sweep/SKILL.md:156-158` and workflow `FETCH` `:175`/`:645` still call a bare `firecrawl scrape` with no fallback. Out of scope; file a follow-up.
- **G (residual):** the early exits via `withStatuses` (`:584`, `:586`, `:624`, `:735`) never get `provisional`, which is acceptable because they are already degraded.
- **H:** a README row with no `route` field renders a BLANK route cell, not `firecrawl`.
- **I:** test 15: confirm that the copied gate imports `dotfiles_setup` from the venv; otherwise mirror `python/src` beside the copy.
- **J:** the new planner node gets a `ROUTE` key and a `_SWEEP_ROUTING` row in `tests/test_workflows_js.py:648`. Update existing mocks so they handle the new label.
Premise verifier: no further round needed (no new premise rows). READY TO DISPATCH.
