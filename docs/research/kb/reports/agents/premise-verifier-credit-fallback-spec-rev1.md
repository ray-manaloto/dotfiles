# Premise report: credit-fallback spec rev 1

Report from the premise-verifier subagent of coordinator f9467b, 2026-10-03, persisted when it arrived. The spec draft is at `/Users/rmanaloto/.claude/jobs/1854b55f/tmp/spec-credit-fallback.md`. The spec will move to `docs/specs/research-credit-fallback.md` once it is ratified (Q10).

## Coordinator annotation (added after receipt)

Step-0 fixtures were captured live at 22:2x CDT and are stored in `/Users/rmanaloto/.claude/jobs/1854b55f/tmp/fc402/`.
- **Search:** `firecrawl search "mise tasks" --limit 1` exited 1 with empty stdout. Stderr was:
  `Error: {"success":false,"error":"Insufficient credits to perform this request. …","code":"ERR_BAD_REQUEST","status":402}`
- **Scrape:** `firecrawl scrape https://mise.jdx.dev/ --format markdown` exited 1 with empty stdout. Stderr was:
  `Error: Insufficient credits to perform this request. …`
  This message has **no** numeric 402, so the classifier has to match the text.

This settles MISSING-2: the CLI exits non-zero on a 402. Only the failure arm can be measured while credits are exhausted, so the exit code of a successful run remains an inherited claim.

## Report (verbatim)

ROWS: 41 checked — 32 CONFIRMED (0 provenance corrected) / 1 REFUTED / 0 UNVERIFIABLE / 8 ASSUMED (2 checkable)

Row verdicts:
- P1 CONFIRMED — `research_fanout.py:93-100` has exactly the five Status members.
- P2 CONFIRMED — `:62-71` eight sources; strict-five set equality `:1521-1527` (`:1525`).
- P3 CONFIRMED — `:737-738` `_Attempt((), raw, f"HTTP {status}")`; status dropped; `_Attempt` `:199-203`.
- P4 CONFIRMED — `:534-537` raw = stdout only; `:548-565` redacts stderr (also truncates to last 300 chars `:565` — see MISSING-7).
- P5 CONFIRMED — `:801-827`, `clean_env(keep={"FIRECRAWL_API_KEY"})` `:823`.
- P6 CONFIRMED — `Status.SKIPPED` only built `:1093`, prerequisite branch `:1089-1100`; reasons `:967-985`.
- P7 CONFIRMED — `:1404-1408`.
- P8 CONFIRMED — `:1438-1441` (`data.web`), `:1458-1459` (`success is True`).
- P9 CONFIRMED — `:1365-1369`.
- P10 CONFIRMED — `:1395` writes, `:1514` checks equality.
- P11 CONFIRMED — `:2190-2191`.
- P12 CONFIRMED — `:1835-1872`.
- P13 CONFIRMED — `research-sweep-run.js:499` (mirrored), `:501` (mirrorGaps).
- P14 CONFIRMED — `research-sweep-run.js:834-841`.
- P15 CONFIRMED — `mise run research-fanout` with no fnox at `:179` (probeCmd), `:382`, `:408`.
- P16 CONFIRMED — `codex-research-gate.py:14-19` (REPO_ROOT from `__file__`, import) + `:100-103`.
- P17 CONFIRMED — `:75`, `:81`; `mise -C {REPO_ROOT}` `:84`.
- P18 REFUTED (units only) — `~/.codex/hooks.json:7`, `:9`, `:19-20` match, but `additionalContextLimit` is a TOKEN threshold, not characters: KB `sources/agent-harness-docs/docs/codex/hooks.md:453` "customize the approximate token threshold", `:464` "default `2500`-token threshold". Not load-bearing (a ≤1000-char test is stricter than 1000 tokens). Fix wording in P18 and §3.6.
- P19 CONFIRMED — `~/.codex/tools/dotfiles-research-gate/.git/HEAD:1` `ref: refs/heads/main`.
- P20 ASSUMED — KB `docs_mirror.py:222` says only "a 404 exits 1 with empty stdout"; nothing establishes webclaw has no HTTP-status field — code just reads `content.markdown`/`metadata.url` (`:237-238`).
- P21 CONFIRMED — KB `docs_mirror.py:399-419`, `:456`. Data-level caveat: KB falls back only when the native fetch SUCCEEDED (HTTP 200 + non-markdown, or same-page redirect `:403`, `:407-408`); `resp.error`/any 4xx/5xx → None, never fallback (`:405-409`). The precedent is "fallback on success-but-wrong-format", the spec uses "fallback on 402". Ray asked for the analogy explicitly, so not blocking, but "same pattern" is shape-level, not data-level.
- P22 CONFIRMED — KB `mise.toml:123` `"github:0xMassi/webclaw" = "0.6.23"`; `~/.config/mise/config.toml:226` same. Dotfiles has no webclaw in any `*.py/toml/pkl/js/json` (control: `firecrawl-cli` hits `mise.toml`/`mise.lock`).
- P23 ASSUMED — external Serper API shape; no file in reach documents it.
- P24 ASSUMED — external SerpApi shape; same.
- P25 ASSUMED — only source `docs/handoffs/session-2026-10-03n.md:131` ("Firecrawl search returns HTTP 402 (billing)"); not re-measurable without network.
- P26 ASSUMED — no capture exists; step 0 is the settle.
- P27 CONFIRMED — `~/.config/fnox/config.toml:82-83` (names), `:90` `[profiles.codex_research.secrets]`, `:93-94` — name-only `-o` grep.
- P28 CONFIRMED — `doctor.toml:39-96`; `SCRAPECREATORS_API_KEY` `:91` → `SKILLSMP_API_KEY` `:92` (control `FIRECRAWL_API_KEY` `:54`).
- P29 CONFIRMED — `child_env.py:49-57`; `(?:^|_)API_KEY(?:_|$)` matches both `SERPER_API_KEY` and `SERP_API_KEY`.
- P30 CONFIRMED — `python/src/dotfiles_setup/AGENTS.md:5-6` "payment-required or failed sources must remain visible as a failed receipt"; `:16-20` paragraph as described.
- P31 CONFIRMED — `~/.codex/AGENTS.md:16-17`.
- P32 CONFIRMED — `mise.toml:1389-1392`; both `.agents/skills/{research-sweep,codex-team-research}/SKILL.md` exist.
- P33 CONFIRMED — `rule-sync.toml:51-56`, `:73`.
- P34 CONFIRMED — `tests/test_research_fanout.py:236` `query = str(payload["query"])` → a Serper `q` body KeyErrors.
- P35 CONFIRMED — `tests/test_research_fanout.py:1856-1865` (`rsplit("  ", 1)`).
- P36 CONFIRMED — `tests/test_codex_research_gate.py:14-29`.
- P37 CONFIRMED — `docs/specs/research-fanout.md:3`, `:6-7`.
- P38 CONFIRMED — `.claude/rules/real-integration-evidence.md:6-11`.
- P39 ASSUMED — `mise.toml:132` `auto_install = true`; whether the clone auto-installs webclaw under `mise -C` with fnox is not measured.
- P40 ASSUMED (checkable) — codex docs settle it: over the limit Codex "saves the full text to disk and sends a shorter preview" (KB `hooks.md:185-187`) — a preview, not rejection; units are tokens (P18). Should be a cited row.
- P41 CONFIRMED — no dotfiles code outside docs references webclaw (grep excl. `.venv`/worktrees/docs → 0 files; control same shape over KB → `docs_mirror.py`).

Anchors verified: research_fanout.py `Endpoint` `:103-107`, `SourceResult` `:128-139`, `default_http` `:407-446`, `_record_item` url keys `:461`, `_records` `:490-502`, `_subprocess_error` `:548-565`, `_credential_header` `:568-575`, `_http_json` `:724-743`, exception→fixed-string map `:1140-1159` (`_CredentialHeaderError` = "invalid credential header for {name}" `:246-250` — no URL leak), `--sources` allowlist `:1275`, `_list_sources` `:1296-1301`, `_persist` `:1356-1401`, `_validate_row_status` `:1404-1425`, `_validate_strict_row` `:1487-1503`, `validate_strict_five` `:1506-1533`, `_fanout_manifest_probe` successful-set `:1801`, `_mirror_probe` `:1812-1872`, `_print_summary` `:2133-2141`. Strict-five semantics at `:1395-1514` are as described; the v1-validator-fails-closed claim on a substituted row holds (Serper body has no `data.web` `:1438-1441`); a credit-skipped row fails at `:1407-1408` under v1. Workflow JS `:488-498`, `:499`, `:726`, `:734`, `:834-840` correct; **`:322` is wrong** — it is the retrospect `facts` map inside `finish()`; the result object is built at `:842` from `...common`, so adding to `common` already reaches it, and `:322` only feeds the retrospect. `research-sweep/SKILL.md:61-73`, `:187-196`, `codex-team-research/SKILL.md:44-46`, `research-doc-sources.md:16-18` correct. Q2's five v1 sites: exactly five outside docs (`research_fanout.py:1395`, `:1514`; `codex-research-gate.py:75`, `:81`; `tests/test_research_fanout.py:95`), grep incl. `.codex/`, `scripts/`, `tests/`.

MISSING:
1. §5.2's pin-parity gate cannot check webclaw. `pin_parity.py:94-106` reads only `pin-parity.toml` entries resolved as `project_root / path`; `pin-parity.toml` has no webclaw entry (sections graphify, chezmoi, hk, claude-code, mise `:46-123`; control grep hit those). KB `mise.toml` and user-global `config.toml` are not repo-relative sites, so CI could never read them. As written `mise run pin-parity` passes whatever webclaw version is pinned — a check that can only pass. Fix: drop the claim, or add a repo-relative check (then `pin-parity.toml` joins the allowlist); KB/user-global parity stays a manual cross-check.
2. The firecrawl CLI's exit code on 402 is unstated, and it is load-bearing. Firecrawl is known to exit 0 with a full body for a 404 scrape (`research_fanout.py:1817-1819`). If a 402 also exits 0 with `{"success":false,...}`: search → `_run_json` no error (`:536-539`) → empty-result path (`:1120-1138`) → `empty_unverified`, classifier never consulted; mirror → `_scrape_payload` (`:1852-1853`), and §3.7's "must exit non-zero" gate never fires. Step 0 records rc, but the spec must branch on rc==0-with-error-payload too, or state the rc as a premise anchored to the fixture.
3. Planner fan-out rows are not surfaced by the workflow. §1 point 3 says the Claude workflow names every skipped/substituted route, but `provisionalRoutes` covers mirror probes only. Planner manifests reach only the triage LLM, told to list `empty_unverified or error` (`research-sweep-run.js:615-616`); a `skipped: credits-exhausted` or provisional `ok` row (exa, context7, firecrawl-*) is invisible to `statuses`. Add a manifest-derived provisional list or narrow §1's claim.
4. The mirror README misattributes webclaw mirrors: `_mirror_index_probe` (`research_fanout.py:1897-1955`) renders rc/bytes/reason only, under a fixed header "Caller links fetched with `firecrawl scrape …`" (`:1945-1949`); a webclaw mirror shows as a clean firecrawl row with no provenance. Same file, not instructed.
5. HTTP-route forgery resistance is weaker than §3.5 implies. `_persist` writes body bytes only (`:1374-1375`); HTTP status is never in the raw file. For exa/firecrawl-developer, re-classification trusts the row's `attempts[0].http_status`, and `is_credit_exhaustion(402, any_body)` is True, so a forged row with http_status=402 over any body passes. Only CLI envelopes truly re-derive from bytes. Test 7 / test 13 ("primary raw replaced by a 500 body") discriminate only if built on a CLI route — say so, or persist the status inside the hashed raw envelope for HTTP too. Also a 402 with an empty body hits `raw evidence is empty` at `:1499-1500`, which branch (c) must bypass.
6. `_fanout_manifest_probe` not updated (`:1801-1807`): any `--require`d source that is credit-skipped lands in `required_failed`. Non-blocking today — the workflow's only `--require` is `DEP_SOURCES = 'github-issues,github-discussions,github-releases'` (`research-sweep-run.js:129`) and github is never classified. Name it as a residual.
7. `_subprocess_error` truncates stderr to the last 300 chars (`:565`), and the mirror probe already reuses its output (`:1850-1851`). The new redaction helper must not inherit the truncation, or a credit message early in a long stderr is lost. §3.2 says factor out the redaction; it should also say do not truncate before classifying.
8. Stale sentence in AGENTS.md: `python/src/dotfiles_setup/AGENTS.md:9-10` "The native `fnox exec` process receives only the existing Exa and Firecrawl keys from that profile" — the profile also carries `SERP_API_KEY`/`SERPER_API_KEY` (`fnox config.toml:93-94`). File is allowlisted but §4.3 rewrites only `:3-6` and `:16-20`.
9. In-lane mirror path does not get the fallback: `research-sweep/SKILL.md:134` (in-lane step 1) still says save links with `mise exec -- firecrawl scrape` directly, bypassing the probe; only `:61-73` is in scope. Same file — instruct or name as a residual.
10. Which sources are metered is assumed, not cited: `CREDIT_METERED_SOURCES` assumes context7 and firecrawl-developer can answer 402/quota; firecrawl-developer's prerequisite is "none", key optional (`:84`, `:783-787`). Low risk (the classifier still needs 402 or quota text). Should be an A row.
11. A webclaw-missing error could be mislabelled: the mirror probe's `except FileNotFoundError` (`:1859-1860`) says "firecrawl not found on PATH"; if the webclaw call sits in the same try, a missing webclaw is mislabelled. Spec wants rc 127 "webclaw not found" — say "separate handler".
12. Allowlist completeness: every described edit maps to an allowlisted path except the pin-parity claim (item 1, would need `pin-parity.toml`) and `docs/specs/research-credit-fallback.md` (Q10, architect-owned — fine). Items 4, 6, 7, 8, 9 fall in already-allowlisted files but lack instructions. No `suites.toml` contract or test pins text in the four doc/skill files being edited (grep 0; control `firecrawl`/`plugin-health` hit `suites.toml`).

VERDICT: CORRECT-SPEC-FIRST.
- Blocking: P18 unit wording (cheap); MISSING-1 (§5.2 pin-parity gate can only pass); MISSING-2 (unstated 402 rc — classifier never runs if the CLI exits 0); MISSING-3 (§1's "nothing passes silently" contradicted by Claude-side planner rows).
- Accept-on-record residuals: P20/P23/P24/P25/P26 (external/ephemeral; lane doc checks + step 0); P39 (auto-install inferred; failure would surface in R4); P40 (settled: preview not rejection; moot under the ≤1000-char test); MISSING-4..11 (each a one-line spec addition in an allowlisted file; MISSING-5 matters only if the forged-receipt guarantee is meant to cover HTTP routes).

Files read: dotfiles `python/src/dotfiles_setup/{research_fanout.py,child_env.py,pin_parity.py,AGENTS.md}`, `pin-parity.toml`, `scripts/codex-research-gate.py`, `tests/{test_research_fanout.py,test_research_fanout_probe.py,test_codex_research_gate.py,test_workflows_js.py}`, `.claude/workflows/research-sweep-run.js`, `.claude/skills/{research-sweep,codex-team-research}/SKILL.md`, `.claude/rules/research-doc-sources.md`, `mise.toml`, `doctor.toml`, `rule-sync.toml`, `docs/specs/research-fanout.md`, `docs/handoffs/session-2026-10-03n.md`; KB `python/src/kb_setup/docs_mirror.py`, `mise.toml`, `sources/agent-harness-docs/docs/codex/hooks.md`; user-global `~/.codex/hooks.json` (key grep), `~/.codex/AGENTS.md`, `~/.codex/tools/dotfiles-research-gate/.git/HEAD`, `~/.config/mise/config.toml`, `~/.config/fnox/config.toml` (name-only).

## GitHub repos touched

_None._ (local files only)
