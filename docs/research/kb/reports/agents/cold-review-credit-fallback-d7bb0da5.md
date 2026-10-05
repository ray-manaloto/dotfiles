# Cold review — d7bb0da5 (credit-exhaustion fallbacks) vs b9a027f6

- Subject: `d7bb0da53df42ff933894138e41ff959d7dcc36a` (single commit on `feat/research-credit-fallback`)
- Base: `b9a027f63982b33d9acf326cc9a604544bfa1dbc`
- Reviewer: cold-reviewer (Opus), diff-only, by ref. Every line number below is from `git show d7bb0da5:<path>`.
  The reviewed worktree was clean at `d7bb0da5` throughout (only this report untracked).
- Memory: consulted (`fetcher_fanout_review_patterns`, `saved_workflow_js_review`, `contract_token_and_mirror_replay`,
  `review_method`). This report OVERWRITES an earlier IN-PROGRESS stub whose harness lost Bash.
- Brief shape: round 1, OPEN HUNTING (no enumerated domain), so it cannot end the loop by any outcome; it promotes to
  one bounded round. Q-FRESH / Q-SCOPE / Q-CLAIM are answered below.
- Status: COMPLETE

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | A bare `\b402\b` anywhere in a CLI source's stderr/stdout classifies a NON-credit failure as credit exhaustion, so the strict-five receipt PASSES (provisional) where it used to fail. The clause is needed by no fixture (mutation M1 deleting it: 158/158 green) and is broader than every documented trigger ("HTTP 402, a 429 with quota text, or Insufficient credits") | `python/src/dotfiles_setup/research_fanout.py:134` (consumed at `:1286-1297`, dispatched at `:1464-1471`; the receipt "re-derivation" at `:2035` reuses the same predicate so it cannot catch it) | P1/P1b: firecrawl-search and context7 exiting 1 with a Node stack frame `index.js:402:17` → `skipped/credits-exhausted`, `strict_five_verdict.passed=True`; control `:401:17` → `error`, `passed=False` |
| F2 | MEDIUM | The Codex Stop hook's only provisional enforcement is a `systemMessage` saying "Say so in the answer", but Codex surfaces Stop `systemMessage` as a UI/event-stream warning after the answer is written — the model never reads it, and nothing checks `last_assistant_message`. "The answer must name every provisional route" has no enforcing line; a consumer that reads only the final message (`codex exec -o`) never sees the provisional status (inference from the documented channel, not run) | `scripts/codex-research-gate.py:106-113`; claim at `python/src/dotfiles_setup/AGENTS.md:26-27` | Codex docs `$KB/agent-harness-docs/docs/codex/hooks.md:423` ("`systemMessage` — Surfaced as a warning in the UI or event stream") and `:921-924` (only `decision:block` creates a continuation prompt). The same file already uses `last_assistant_message` for `RESEARCH INCOMPLETE:` at `:116-122`, so the enforcing pattern exists one screen away |
| F3 | MEDIUM | research-sweep-run: when the planner provisional-check node returns null or a malformed line, the run status is `complete` (statuses `[]`), although whether the planner manifests hold credit-skipped sources is then unknown. The dependency-stage analogue (`no PROBE-JSON line`) is a MANDATORY gap; this one is only a `fanoutGap`, which feeds no status | `.claude/workflows/research-sweep-run.js:631` (status list `:856-862`) | Scratch test through the subject's own `_mandatory_run` harness: `plan_manifests: null` → `status complete []`, fanoutGaps `['planner provisional check did not run']`; `{ line: 'not-json' }` → same. Positive arm: the subject's `test_research_sweep_manifest_provisional_is_probe_derived[planner]` reaches `provisional` (mutation J1 turns it red). The subject's test for this case asserts the gap and `mandatoryGaps == []` but never `status` |
| F4 | LOW | Neither FALLBACK provider's real exhaustion response is classified as credit exhaustion: SerpApi documents out-of-searches as HTTP 429 `{"error": "Your account has run out of searches."}`, and Serper clients detect `"Not enough credits"`; `_CREDIT_TEXT` matches neither. The `fallback_status = SKIPPED` branch is therefore unreachable on real fallback exhaustion: the row becomes `error` / `HTTP 429` (fails closed, but contradicts the `skipped: credits-exhausted` contract and hides the cause) | `python/src/dotfiles_setup/research_fanout.py:116-120`, `:1377` | `is_credit_exhaustion(429, '{"error": "Your account has run out of searches."}')` → False; control `(429, "quota exceeded")` → True. SerpApi doc fetched live (`https://serpapi.com/api-status-and-error-codes`, "Error for no searches remaining HTTP Status: 429 … run out of searches"). Serper text from `shibing624/agentica` `agentica/tools/search_serper_tool.py:63` and `pat-jj/harness-1` `eval_scripts/web_tools.py:100,134`; Serper's HTTP status for it is UNVERIFIED |
| F5 | LOW | Credit `reason` is the provider's WHOLE stderr/body, uncapped (base capped subprocess reasons at 300 chars). It is copied into the manifest twice, into `_provisional_line`, the strict verdict, the Codex warning, and the PROBE-JSON line a haiku agent must copy verbatim | `python/src/dotfiles_setup/research_fanout.py:1326-1332`, `:1909-1929` | P3: a 22,026-byte HTML 402 body → `row.reason` 23,026 chars; `_fanout_manifest_probe` PROBE-JSON line 46,406 chars (reason appears in `provisional` AND `required_failed`). A failed verbatim copy is a MANDATORY gap for dependency runs (`research-sweep-run.js:456`) |
| F6 | LOW | Request-URL redaction is a regex over SERIALIZED JSON and is not escape-aware: a URL inside an HTML attribute (`href=\"https://serpapi.com/search.json?…\"`) consumes the `\` and leaves a bare `"`, so the whole gh / firecrawl / last30days payload becomes invalid JSON and that source errors. It now runs on every subprocess stdout | `python/src/dotfiles_setup/research_fanout.py:670` (applied at `:636`) | P2: `json.loads(_redact_text(raw))` → `Expecting ',' delimiter`; control (same body, `serpapi.com/docs`) parses |
| F7 | LOW | `_provisional_line` prints "no fallback route" when routes EXIST but were skipped, and lists only `error` attempts, so the actionable cause ("SERPER_API_KEY not inherited; run through fnox exec") never reaches the verdict, CLI summary, Codex warning or workflow | `python/src/dotfiles_setup/research_fanout.py:1919-1929` | P1b output for firecrawl-search with no fallback keys: `skipped: credits-exhausted (…); no fallback route`, while the row's attempts carry two `SKIPPED … not inherited` routes |
| F8 | LOW | Seven receipt/redaction guards this diff adds are unpinned: deleting each leaves all 158 Python tests green — `_bound_raw` same-directory binding (the docstring's "same-turn" clause, M5), skip-row `raw == primary_raw` (M3), winning-route hash bind (M24), OK-with-zero-records (M25), stdout credential redaction in `_run_json` (M23), webclaw markdown redaction (M30), fallback `limit` slice (M20) | `python/src/dotfiles_setup/research_fanout.py:1937`, `:2049`, `:2060`, `:2068`, `:636`, `:2480`, `:958` | Mutation table below (each anchor asserted `count == 1`, applied, restored; red controls M2/M4/M6/M7/M9 prove the harness discriminates) |
| F9 | LOW | The fallback loop catches `ValueError` broadly, so a malformed `SERPER_API_KEY` reads `request failed`, while the primary path reports `invalid credential header for <NAME>` (and `_HttpBodyError.reason` is likewise lost) | `python/src/dotfiles_setup/research_fanout.py:1366-1374` | P4: `SERPER_API_KEY="bad\nkey…"` → serper attempt `error / request failed`; control: same value in `EXA_API_KEY` → `invalid credential header for EXA_API_KEY`. No sentinel reached any persisted file |
| F10 | LOW | The injected command switched `--out` from an absolute path to `~/.codex/research-coverage/…`, but `--out` is `type=Path` with no `expanduser`, so a model that quotes the path writes under `<checkout>/~/…` and the Stop gate finds no manifest (fails closed) | `scripts/codex-research-gate.py:80-90`; `python/src/dotfiles_setup/research_fanout.py:1587` | `grep expanduser` hits only `:1100` (last30days script lookup) |
| F11 | LOW | `serper`/`serpapi` in the `success is True` set are unreachable (rows are validated against `_SOURCE_NAMES`, which excludes them) and would be wrong if reached — neither provider returns `success` | `python/src/dotfiles_setup/research_fanout.py:1852` | `_SOURCE_NAMES` `:65-74`; set check `:2119`; mutation M14 removing them: green |
| F12 | LOW | Two prose clauses have no enforcing line: the synth instruction "Name every PROVISIONAL ROUTE" (deleting it, J6: green; no verify node checks it), and the status comment "provisional = a VALIDATED … credit-skipped manifest source" (planner/dependency manifest provisional lines are read from `r.get("provisional") is True`, never validated) | `.claude/workflows/research-sweep-run.js:734`, `:853`; `python/src/dotfiles_setup/research_fanout.py:2412-2414` | Mutation J6; `_fanout_manifest_probe` source |

## Q-FRESH — decision→action pairs re-validated before the action?

Answered for every pair the diff adds: fallback-key presence (`:1345`) and its use in `_fallback_search` (`:929`) read
`os.environ` in the same thread with no writer; `_mirror_probe` unlinks the target before firecrawl, and webclaw writes
only after its own checks; `_persist` unlinks every owned name (now incl. `.primary.raw` / `.<route>.raw`) before
writing; the strict verdict reads each raw file once and validates those bytes. **No temporal defect found.**

## Q-SCOPE

- F1-F12 are in scope for this diff (each is new code or a new string).
- **Deployment, sibling ticket**: the live Codex hook (`~/.codex/hooks.json:7,19`) runs a SEPARATE clone,
  `~/.codex/tools/dotfiles-research-gate`, at `2d763acb` (#1409). It still writes and accepts `strict-five-v1`, and the
  injected `mise -C {REPO_ROOT}` points back at that clone, so this diff is inert for Codex until the clone is advanced;
  the gate and the fan-out must move together, because v2 rejects v1 manifests. Nothing in the diff names that step.
  Recommend a ticket or a deploy-step line in `python/src/dotfiles_setup/AGENTS.md`, not a change here.
- **Design note, not a defect**: by the documented design, a strict-five receipt can now pass with all four metered
  sources credit-skipped (the subject's own `test_credit_all_metered_sources_form_provisional_strict_receipt`), and
  the `402` envelope is a one-line JSON that any writer can produce. F1 and F2 matter more because of this floor.
- webclaw cross-repo pin parity is declared manual in `mise.toml` (pin-parity.toml is in-repo only, confirmed by its
  header); that is a pre-existing capability gap, not this diff's.

## Q-CLAIM — operator-facing strings added or changed

| String | Enforcing line | Verdict |
|---|---|---|
| `fallback:<route> … <KEY> in process environment present/absent` | `research_fanout.py:1662-1667` | enforced |
| `fallback:webclaw … webclaw on PATH present/absent` | `:1668-1669` (`shutil.which`) | enforced |
| `<KEY> not inherited; run through fnox exec` | `:1345-1355` | enforced, but never surfaced (F7) |
| `<src> skipped: credits-exhausted (<reason>); no fallback route` | `:1919-1929` | "no fallback route" false when routes were skipped (F7); reason unbounded (F5) |
| `<src> via <route> (credits-exhausted: <reason>)` | `:1925` | enforced |
| `credits-exhausted; webclaw rc=N / redirected to / empty markdown / not JSON / not found / timed out` | `:2438-2482` | enforced; webclaw's own stderr (e.g. its 404 reason) is dropped — cosmetic |
| Mirror README: "fetched with `webclaw -f json` instead (route `webclaw`, provisional)" | `:2558-2561` | enforced (route is set before the attempt, so it names the attempted route) |
| Gate submit: "A provider out of credits (HTTP 402 or quota 429) is recorded skipped…" | `research_fanout.py:127-136` | broader than stated (F1) |
| Gate submit: "the receipt passes PROVISIONAL; report it" | pass: `strict_five_verdict`; "report it": none | F2 |
| Gate stop: "Research receipt PROVISIONAL … Say so in the answer." | none — UI-only channel | F2 |
| AGENTS.md: "(HTTP 402, a 429 with quota text, or "Insufficient credits")" | `:127-136` | broader (F1) and misses real fallback texts (F4) |
| AGENTS.md: "receives the Exa, Firecrawl, Serper (`SERPER_API_KEY`) and SerpApi (`SERP_API_KEY`) keys from that profile" | user `~/.config/fnox/config.toml` | **verified** — names-only parse: profile `codex_research` declares EXA/FIRECRAWL/SERPER/SERP keys |
| AGENTS.md: "the answer must name every provisional route the manifest lists" | none | F2 |
| research-doc-sources.md: `--probe-out <p> --mirror-url <u> --mirror-path <f>` | parser `:1595`, `:1602-1603` | enforced |
| mise.toml: "Same pin and rationale as KB mise.toml:118-123" | KB `mise.toml:118-123` | verified (webclaw block, pin at `:123`) |
| Workflow status comment: "provisional = a validated credit fallback or credit-skipped manifest source" | mirror rows yes (`mirrored()`), manifest rows no | F12 |
| Workflow synth: "Name every PROVISIONAL ROUTE below…" | none (J6 green) | F12 |
| Workflow gap: "planner provisional check did not run" | `:631` | enforced, but status-neutral (F3) |

## Probes run (control arm named for each)

- Targeted pytest at the ref, from the reviewed worktree: `test_research_fanout.py`, `test_research_fanout_probe.py`,
  `test_codex_research_gate.py`, `test_workflows_js.py` → **268 passed, rc=0** (30 s). Same 268 (158 + 110) in the
  scratch worktree.
- Scratch worktree `git worktree add --detach /tmp/cr-cf/wt d7bb0da` for every probe and mutation; module origin
  printed (`/tmp/cr-cf/wt/python/src/dotfiles_setup/research_fanout.py`) so no arm silently imports the installed copy.
- **P1 (classifier)**: `is_credit_exhaustion(None, …)` on `…index.js:402:17)` → True; `…:401:17)` → False;
  `"response was 402 bytes"` → True; `ECONNRESET` → False.
- **P1b (end to end through `main` + `strict_five_verdict`)**, using the subject's own `ScriptedRunner`/`FakeHttp`,
  PATH and metered keys isolated as in its `credit_env` fixture:

  | source | stderr stack line | row status | skip_reason | strict passed |
  |---|---|---|---|---|
  | firecrawl-search | `:402:17` | skipped | credits-exhausted | **True** (provisional) |
  | firecrawl-search | `:401:17` (control) | error | — | False |
  | context7 | `:402:17` | skipped | credits-exhausted | **True** (provisional) |
  | context7 | `:401:17` (control) | error | — | False |

- **P2 (redaction)**: `{"items":[{"body":"<a href=\"https://serpapi.com/search.json?engine=google&q=x\">demo</a>"}]}`
  → invalid JSON after `_redact_text`; control with `serpapi.com/docs` → valid.
- **P3 (reason size)** and **P4 (malformed fallback key)**: see F5 and F9.
- **F3 scenario**: a scratch test in the scratch worktree only, importing `_mandatory_run`/`_result` from the subject's
  `tests/test_workflows_js.py`.
- **Refuted hypothesis (not a finding)**: "webclaw saves a 404 page as a successful mirror" — the hazard the base
  docstring warned about for firecrawl, and that docstring was deleted by this diff. Live, webclaw 0.6.23
  (`~/.local/share/mise/installs/github-0x-massi-webclaw/0.6.23/webclaw -f json`): two 404 URLs → rc=1, 0 bytes,
  stderr `the target returned HTTP 404 instead of a successful page`; control `https://example.com/` → rc=0, 156-char
  markdown. Redirect guard armed live: `https://github.com/jdx/rtx` → `metadata.url` `https://github.com/jdx/mise`
  (rejected by the path compare); `https://EXAMPLE.com` → `https://example.com/` (accepted).
- **Gate replays**: `.agents` mirrors — `research-sweep` differs from `.claude` only by the known `Claude Code`→`Codex`
  line; `codex-team-research` identical. Strict `per_path_tokens` scan of the ref's `suites.toml`: 1,414 tokens, 0
  failures. No suites.toml contract names `research_fanout`, `research-sweep-run` or the gate (control: `research`
  hits 3+ suites), so pytest is the only gate on this code.
- `mise.lock` webclaw block: 11 platform entries incl. `linux-x64`, `linux-arm64`, `macos-arm64`, matching KB's.

### Mutation table (anchor `count == 1` asserted; restored with `git checkout --`; final `git status` clean)

| Row | Mutation | Result |
|---|---|---|
| M1 | drop `or re.search(r"\b402\b", text)` | **GREEN** (F1: unneeded) |
| M2 | any 429 = credit | RED (control) |
| M3 | skip-row `raw != primary_raw` removed | **GREEN** (F8) |
| M4 | envelope re-derivation off | RED |
| M5 | `_bound_raw` path equality off | **GREEN** (F8) |
| M6 | no `.primary.raw` unlink | RED |
| M7 | URL redaction regex never matches | RED |
| M8 | fallback credit → genuine error | RED |
| M9 | genuine error dropped | RED |
| M10 | credit check for ANY source | **GREEN** (validator still rejects non-metered provisional rows; producer guard unpinned) |
| M11 | webclaw redirect check off | RED |
| M12 | mirror `provisional` always False | RED |
| M13 | manifest-probe provisional `[]` | RED |
| M14 | dead serper/serpapi `success` set removed | GREEN (F11, expected) |
| M15/M16/M17 | route disjunct / route allowlist / duplicate-route check off | GREEN — each is backed by a later guard in series (redundant, not a defect) |
| M18 | webclaw never tried | RED |
| M19 | `_scrape_payload` `success:false` check off | GREEN (later checks still reject) |
| M20 | fallback `limit` slice off | **GREEN** (F8) |
| M21 | skip keeps items | GREEN (items always empty there) |
| M22 | claimed int status ignored | GREEN (fixtures also carry credit text) |
| M23 | `_run_json` stdout not redacted | **GREEN** (F8) |
| M24 | winning-route hash bind off | **GREEN** (F8) |
| M25 | OK with 0 raw records allowed | **GREEN** (F8) |
| M26 | attempt evidence blanked | RED |
| M27 | fallback errors not listed | RED |
| M28 | `--list-sources` fallback rows off | RED |
| M29 | empty webclaw markdown accepted | RED |
| M30 | webclaw markdown unredacted | **GREEN** (F8) |
| G1 | gate provisional message off | RED |
| G2 | gate `--out` back to absolute | RED |
| G3 | gate PROVISIONAL instruction off | RED |
| J1 | no `provisional` status | RED |
| J2 | plan-manifests node off | RED |
| J3 | provisional-check gap off | RED |
| J4 | dependency provisional off | RED |
| J5 | count unmirrored provisional rows | GREEN (unreachable: provisional ⇒ mirrored) |
| J6 | synth "Name every PROVISIONAL ROUTE" off | **GREEN** (F12) |
| J7 | PROVISIONAL ROUTES block off | RED |
| J8 | planManifests route pin off | RED |
| J9 | `provisionalRoutes` not returned | RED |

## Disposition recommendation

- Fix in this unit: F1 (delete the bare-`402` disjunct; M1 shows no fixture needs it), F2 (on a provisional pass,
  `decision: block` once when `last_assistant_message` lacks `PROVISIONAL`, mirroring the existing
  `RESEARCH INCOMPLETE:` arm), F3 (make the missing provisional check status-bearing, as the dependency analogue is),
  F4 (add the two providers' real exhaustion texts, each with a fixture from its source).
- LOW F5-F12: fix or ticket; F8 is a test-only change.
- Deployment of the `~/.codex/tools/dotfiles-research-gate` clone: ticket (Q-SCOPE).

## Scratch cleanup

`/tmp/cr-cf/` (scratch worktree `wt`, probe scripts `h/`, logs) — removed at the end of the review, worktree
deregistered with `git worktree remove`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject diff
- [shibing624/agentica](https://github.com/shibing624/agentica) — Serper `Not enough credits` detection (`search_serper_tool.py:63`)
- [pat-jj/harness-1](https://github.com/pat-jj/harness-1) — Serper `Not enough credits` detection (`eval_scripts/web_tools.py:100,134`)
- [0xMassi/webclaw](https://github.com/0xMassi/webclaw) — the pinned 0.6.23 binary, run live (404 and redirect behaviour)

VERDICT: DO NOT SHIP

Findings (severity / claim / file:line):

- MEDIUM / bare `\b402\b` in CLI text turns a non-credit failure into a passing provisional strict receipt / `python/src/dotfiles_setup/research_fanout.py:134`
- MEDIUM / Stop-hook `systemMessage` is UI-only; nothing enforces that the answer names provisional routes / `scripts/codex-research-gate.py:106-113`
- MEDIUM / missing planner provisional check leaves workflow status `complete` / `.claude/workflows/research-sweep-run.js:631`
- LOW / real SerpApi/Serper exhaustion texts unmatched, so fallback exhaustion reads as a genuine error / `python/src/dotfiles_setup/research_fanout.py:116-120`
- LOW / credit reason uncapped (22 KB body → 46 KB PROBE-JSON line) / `python/src/dotfiles_setup/research_fanout.py:1326-1332`
- LOW / URL redaction breaks serialized JSON on an escaped-quote URL / `python/src/dotfiles_setup/research_fanout.py:670`
- LOW / "no fallback route" hides skipped routes and their fix / `python/src/dotfiles_setup/research_fanout.py:1919-1929`
- LOW / seven new guards unpinned (M3, M5, M20, M23, M24, M25, M30) / `python/src/dotfiles_setup/research_fanout.py:1937`
- LOW / fallback catch collapses the credential-header reason to `request failed` / `python/src/dotfiles_setup/research_fanout.py:1366-1374`
- LOW / `--out ~/…` relies on shell tilde expansion; argparse does not expand it / `scripts/codex-research-gate.py:80-90`
- LOW / dead `serper`/`serpapi` `success` requirement / `python/src/dotfiles_setup/research_fanout.py:1852`
- LOW / two prose clauses unenforced (synth instruction; "validated" manifest rows) / `.claude/workflows/research-sweep-run.js:734`
