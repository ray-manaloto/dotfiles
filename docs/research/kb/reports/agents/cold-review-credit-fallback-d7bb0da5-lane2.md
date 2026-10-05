# Cold review (lane 2) — d7bb0da5 (credit-exhaustion fallbacks) vs b9a027f6

- Subject: `d7bb0da53df42ff933894138e41ff959d7dcc36a` (single commit on `feat/research-credit-fallback`;
  worktree HEAD == d7bb0da5, clean, verified with `git rev-parse` before Bash was lost)
- Base: `b9a027f63982b33d9acf326cc9a604544bfa1dbc`
- Reviewer: cold-reviewer (Opus), diff-only. The spec was read only for the Spec axis, AFTER the code view was formed.
- Brief shape: round 1, OPEN HUNTING. It states no domain with a cardinality, so this round cannot end the loop by
  any outcome. It promotes to one bounded round.
- Memory: this lane's `memory: local` directory was empty at start.
- **Why a separate file:** the requested path `cold-review-credit-fallback-d7bb0da5.md` was overwritten mid-review
  by another reviewer instance ("This report OVERWRITES an earlier IN-PROGRESS stub whose harness lost Bash").
  To avoid two writers on one file, this lane writes here.
- **Tooling limit:** after the first Bash calls (ref resolution, `--stat`, two diff dumps), the harness refused every
  further Bash call and every Edit ("session is isolated in worktree handoff-2026-10-03s"). Everything after that
  came from `Read` on files at d7bb0da5. **No pytest was run.** Runtime claims are code traces, and claims that
  depend on provider or CLI behaviour are labelled UNVERIFIED.
- Status: COMPLETE

## Verdict: DO-NOT-SHIP (as committed). Three conditions, each cheap

1. **Fix F1, a regression on non-metered sources.** Scope the request-URL redaction to the fallback request and
   response paths only. Today it runs before the JSON decode of every CLI's stdout and inside mirrored pages.
2. **Narrow F2 or record a ruling and a ticket for it.** The bare `\b402\b` and quota text on CLI routes can launder
   a non-credit failure into a provisional pass. That breaks spec §4.1 "Genuine errors are never laundered".
3. **Close F4.** Record the R1–R4 live arms and the provider-doc URLs that spec §3.3/§6 require
   (`.claude/rules/real-integration-evidence.md`).

Credential handling is clean: no key value reaches stdout, a reason, a raw file or the manifest on any path traced.
`mise.lock` is additive-only.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | The Serper/SerpApi request-URL redaction regex runs over EVERY CLI's stdout **before** JSON decode, and over mirrored pages. A URL followed by an escaped quote (`…search.json?q=x\"`) loses its backslash, so valid JSON from a non-metered source (gh issues/discussions/releases, last30days) becomes "invalid JSON", which is ERROR and a strict-five FAIL. The same regex silently rewrites mirrored page text | `python/src/dotfiles_setup/research_fanout.py:669-673` (regex `[^\s\"<>]*` admits `\`), applied pre-decode at `:636` (`_run_json`, all gh/firecrawl/last30days stdout), `:2528-2530` (scrape stdout), `:2480` (webclaw markdown) | Trace: `\"https://serpapi.com/search.json?q=x\" more` → match ends after `x\` → `\"[REDACTED REQUEST URL]" more`, an unterminated string. Spec REV 2.1 addendum C scopes this rule to the *request* URL and key-bearing strings, not third-party content. Before this commit, stdout was not URL-rewritten. Reachable whenever researched content quotes a Serper/SerpApi URL. Runtime UNVERIFIED (no Bash). |
| F2 | MEDIUM | On the CLI routes (`firecrawl-search`, `context7`, mirror scrape), any standalone `402` token or quota phrase in stderr+stdout counts as credit exhaustion. A non-credit failure whose text carries a URL/id/query with `402` (`…/issues/402`), or a transient "quota exceeded" rate limit, is laundered into `skipped: credits-exhausted`, a provisional PASS, or a webclaw substitution | `research_fanout.py:133-134`; consumers `:1286-1297` (`_attempt_credit`, text = stderr + stdout), `:2551-2553` (mirror) | Spec §3.2 ratified the bare `\b402\b`, which contradicts §4.1 "Genuine errors are never laundered". No negative arm: the classifier table `tests/test_research_fanout.py:2056-2073` has only `connection reset`/`billing` as `None`-status negatives. Whether firecrawl/ctx7 echo URLs or queries in non-credit errors is UNVERIFIED. Suggested narrowing: anchor `402` to `"status":402` or `status code 402`, and treat quota text on `None` as credit only with an exhaustion word. |
| F3 | MEDIUM | The provisional Stop branch tells a model that has already finished to "Say so in the answer". `systemMessage` is a UI warning, not model-visible, and nothing checks `last_assistant_message`, so AGENTS.md's "the answer must name every provisional route" has no enforcing line | `scripts/codex-research-gate.py:106-114`; claim at `python/src/dotfiles_setup/AGENTS.md` (last paragraph) | KB `sources/agent-harness-docs/docs/codex/hooks.md:423`: `systemMessage` is "Surfaced as a warning in the UI or event stream". Contrast the fail branch `:117-131`, which inspects the message and blocks. Spec Q5 ratified non-blocking, so this is a spec-level defect. **Ticket:** block once on provisional unless `last_assistant_message` contains `PROVISIONAL`, mirroring `:117-122`. |
| F4 | MEDIUM | The commit body omits the evidence the spec requires: provider-doc URLs for the Serper/SerpApi request shapes (including the recorded deviation that SerpApi's `num` was dropped), and the R1–R4 live-arm rc and manifest paths. It still makes the completion claim "no longer fails the strict-five gate" | `.git/worktrees/credit-fallback/COMMIT_EDITMSG:1-11` (subject matches `git log --oneline` for d7bb0da5); deviation only in a code comment at `research_fanout.py:942` | Spec §3.3 ("cite the docs URLs in the commit body … record the difference") and the §6 template ("Provider request shapes verified against: … Live arms R1-R4: …"). `.claude/rules/real-integration-evidence.md` requires a real public-entrypoint invocation plus a control arm before a completion claim. |
| F5 | LOW | A firecrawl-search skip prints "no fallback route" even when both fallback routes exist but their keys were absent or the routes were themselves credit-exhausted. That hides an actionable misconfiguration | `research_fanout.py:1923-1929` (`_provisional_line` lists only `ERROR` attempts) | The SKIPPED "not inherited" attempts (`:1338-1356` region of `_credit_result`) are in the manifest but are dropped from the operator line, the summary line and the Stop message. |
| F6 | LOW | The credit reason and `primary_reason` are untruncated. A whole 402 body or stderr flows into the manifest `reason`, the CLI summary, the codex Stop `systemMessage`, the workflow `provisionalRoutes` and the synthesis prompt | `research_fanout.py:1326-1332`, `:2555-2557`, `:1909-1929` | Spec §3.2 keeps the 300-char cut in the human-readable reason after classification (MISSING-7). Only `_subprocess_error` applies it. |
| F7 | LOW | The fallback providers' own credit exhaustion may not classify. SerpApi "run out of searches" and Serper `400 "Not enough credits"` match neither `_CREDIT_TEXT` nor 402/429 handling, so a depleted fallback gives ERROR (strict FAIL) rather than a provisional skip. An empty SerpApi result (no `organic_results` key) also becomes ERROR | `research_fanout.py:116-120`, `:127-135`; shape check in `_fallback_search` (`:925-` region, "unexpected fallback response shape") | Fails closed, so nothing is masked. Provider messages and the empty-result shape are from memory: UNVERIFIED. The spec required the lane to confirm shapes against provider docs (no URLs recorded, see F4). |
| F8 | LOW | The retrospect prompt tells the agent a `provisional` run "may be missing or partial: the run did not complete". That claim is false for the new status, which is a completed run | `.claude/workflows/research-sweep-run.js:331` (status `!== 'complete'`) with the new status at the `statuses` list (`provisionalRoutes.length ? 'provisional' : ''`) | Pre-existing string. It is made false by the status value this diff adds. |
| F9 | LOW | Adding `serper`/`serpapi` to the `success is True` set in `_valid_json_response` is dead code, and wrong if reached: neither provider returns `success` | `research_fanout.py:1852-1853` | The only caller, `_validate_raw_response` (`:1897`), sees `_SOURCE_NAMES` rows only. Routed rows go through `_validate_credit_output`. For these names the function already falls into the `github-discussions` else-branch (`:1841-1849`). |
| F10 | LOW | webclaw acceptance has no HTTP-status check. The README clause "a page answering HTTP >= 400 is a failure whatever its size" holds on the webclaw route only through accepted assumption P20 (404 gives rc 1). A missing `metadata.url` is reported as "webclaw redirected to None". The skill sentence that splices "except … validated webclaw response" before ": firecrawl exits 0 with a full 404 body" is garbled | `research_fanout.py:2457-2483` (`:2475-2477`), README text `:2655-2664`; `.claude/skills/research-sweep/SKILL.md:72-75` | Spec P20 is `A (accepted)`. "Validated" means same-URL plus non-empty markdown only. |
| F11 | LOW | The submit context now passes `--out ~/.codex/research-coverage/...` instead of the absolute `marker.parent`. A model that quotes the path (a common habit) gets no tilde expansion, so the manifest lands elsewhere and Stop blocks | `scripts/codex-research-gate.py:80-90` vs `handle()` state root `:160` | Fails closed, so nothing is masked. The trade was made for the ≤1000-char budget (spec §3.6). |

### INFO (not defects in this diff)

- **I1 (Q-SCOPE, policy):** a strict-five receipt now PASSES with all four metered sources (exa, context7,
  firecrawl-developer, firecrawl-search) credit-skipped. That pass rests on GitHub ×3 + last30days only, and
  `tests/test_research_fanout.py:2636-2668` pins it. This matches spec §3.3 and Ray's ratified request. If Ray wants
  a floor (for example, at least one web route `ok`), that needs a separate ticket.
- **I2:** `doctor.toml:39-96` at d7bb0da5 does not list `SERPER_API_KEY`/`SERP_API_KEY`. The spec says Q9 shipped
  separately as 1ba74fab, which is not in this base. That is a sibling change, not this diff.
- **I3:** `mise.lock` is ONE hunk `@@ -6198,6 +6198,65 @@` of pure `+` lines: webclaw 0.6.23 across 11 platform
  tables, sha256-pinned, no `provenance` (none published). **Additive only: confirmed.** The `mise.toml` comment's
  claim "Same pin … as KB mise.toml:118-123 (#837/#847)" was verified against
  `knowledge-base/mise.toml:118-123`.
- **Credential handling (requested focus), clean:**
  - Both keys match `child_env.CREDENTIAL_NAME` (`child_env.py:49-57`), so value redaction covers them.
  - Both pass through `_credential_header` (`research_fanout.py:929`).
  - The SerpApi key only reaches the request URL. The fallback HTTP code (`:510-547`) does not log, and every
    fallback exception becomes a fixed string (`_credit_result`'s except at `≈:1366-1374`).
  - webclaw runs with `child_env.clean_env()` (`:2443`), and the scrape keeps only `FIRECRAWL_API_KEY` (`:2509`).
  - `--list-sources` prints presence only (`:1662-1669`).
  - Tests use sentinels over all `*.json`/`*.raw` files and stdout (`tests/test_research_fanout.py:2152-2214`,
    `:2228-2259`, `:2371-2399`).
- **402 detection (requested focus):**
  - The search fixture `tests/fixtures/research_fanout/firecrawl-402-search.err:1` (JSON `"status":402`) and the
    scrape fixture `firecrawl-402-scrape.err:1` (text only) both classify through `_CREDIT_TEXT`/`\b402\b`
    (`tests/test_research_fanout.py:2076-2080`).
  - The CLI path does not parse the JSON in stderr. It relies on the text, which is acceptable here but is the root
    of F2.
- **Provisional / `skip_reason` semantics in the strict gate (requested focus):**
  - Dispatch is `research_fanout.py` `strict_five_verdict`: a row that is provisional, has a route, or has
    `skip_reason == credits-exhausted` goes to the provisional validator. Everything else goes through the old
    byte-for-byte path.
  - A non-metered source fails: `_validate_credit_status`, which also rejects `provisional is not True` and a route
    outside `_FALLBACK_ROUTES`.
  - A `prerequisite` skip fails as "did not complete".
  - The envelope re-derives from its own bytes. The forged HTTP-500/rc-auth envelopes fail
    (`tests/test_research_fanout.py:2284-2319`, `tests/test_codex_research_gate.py:226-252`).
  - A fallback genuine error makes the row ERROR (`provisional False`), so the strict gate fails
    (`tests/test_research_fanout.py:2262-2281`, `:2596-2633`). **A fallback cannot mask a non-credit failure of the
    FALLBACK. The masking risk is in classifying the PRIMARY (F2).**

## Required questions

**Q-FRESH:** no stale decision→action pair found.
- The credit decision and the fallback run inside one `_source_result` call (`:1464-1471`).
- The strict verdict re-reads the manifest and every raw at Stop time.
- The mirror unlinks before fetching (`:2500`), and webclaw writes only on its own validated success.

**Q-SCOPE:** F1–F11 are in scope for this unit. I1 is policy (ticket if wanted). Out of scope, already named
residuals in the spec: the deep-read bare `firecrawl scrape` (addendum F) and last30days credit handling (Q6).

**Q-CLAIM:** operator-facing strings this diff adds or changes, each with its enforcing line.

| String (clause) | Enforcing line | Outcome |
|---|---|---|
| `<KEY> not inherited; run through fnox exec` | `os.environ.get(key)` in `_credit_result` | enforced; the fnox-profile half is P27, user-level, UNVERIFIED here |
| `<src> via <route> (credits-exhausted: …)` | `_validate_credit_output` + envelope re-derive | enforced |
| `… skipped: credits-exhausted (…); no fallback route` | none for "no fallback route" when routes exist | **F5** |
| summary `[provisional: via …]` | `_print_summary` built from `_provisional_line` | enforced |
| `fallback:* … present\|absent` | `os.environ.get` / `shutil.which` | enforced |
| `credits-exhausted; webclaw redirected to <final>` | URL compare `:2466-2474` | false when `final` is None (**F10**) |
| README "a page answering HTTP >= 400 is a failure" (webclaw route) | none (P20 assumption) | **F10** |
| README "(route `webclaw`, provisional)" | `route` column only; no provisional column | partial (LOW, folded into F10) |
| gate submit "HTTP 402 or quota 429 … passes PROVISIONAL" | `is_credit_exhaustion` + `strict_five_verdict` | mostly; a CLI also classifies on text with no status |
| gate Stop "Say so in the answer." | none (UI-only `systemMessage`) | **F3** |
| AGENTS.md "answer must name every provisional route" | none in code | **F3** |
| skill trap "Auth failures, 5xx, timeouts … do not trigger fallback" | false on the CLI routes for 402/quota-bearing text | **F2** |
| commit "no longer fails the strict-five gate" | tests only; no live R1–R4 recorded | **F4** |
| retrospect "the run did not complete" (now reachable for `provisional`) | none | **F8** |
| JS fanoutGaps `planner provisional check did not run` | `readProbe` null check | enforced |

## Spec axis (rev 2 + REV 2.1 addendum)

The implementation broadly matches §3.1–§3.7, and the addendum (A, C, D, H, J) is honoured. Deviations:
- **F4:** the commit body misses the §3.3/§6 evidence.
- **F6:** §3.2 MISSING-7 keeps the human-reason truncation, which the credit path omits.
- SerpApi `num` was dropped. Docs may win over the spec, but no doc URL was recorded.
- Spec self-conflict §3.2 vs §4.1: **F2**.
- Spec Q5 makes the provisional Stop message unenforceable: **F3**.

The existence of the spec's workflow tests 16–17 (provisional mirror and planner arms) is UNVERIFIED by this lane,
which had no grep. The `PLAN_MANIFEST_OK` stubs and the routing row `plan-manifests` are present
(`tests/test_workflows_js.py:655`, `:2376`).

## GitHub repos touched

_None._ Only local files were read: this worktree, the knowledge-base offline codex docs and `mise.toml`, and the
spec/fixture paths the caller named.
