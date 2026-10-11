# Codex takeover Phase B1 validation — 2026-10-05

Status: **PARTIAL — required W5a runtime proof blocked and shipping-policy contradiction unresolved.** Implementation and permitted targeted checks are complete; caller owns commits. No commit/push was performed. This report is the sole incremental findings record for this run. Spec: `docs/specs/codex-takeover-phaseB1-spec.md`; adopted design: `docs/specs/codex-takeover-phaseB-design.md`.

## Scope and gates

- Python specialist owns registry, handoff mechanics, ledger/audit/review and targeted tests.
- Config specialist owns only the `mise.toml` lane-cards wrapper. Documentation specialist owns policy index, bootstrap, runbook, handoff skill, generated mirrors and this report.
- No SLOT GO: full `mise run lint`, full pytest and `mise run verify` are **NOT_RUN** under spec §4. Targeted tests, lint-docs and mirror parity remain required.
- COMMIT: caller. No commit, push, GitHub write, B2 implementation or implementation user-level file modification is authorized. The developer-mandated shared research receipt writes only its explicit external coverage directory; it does not authorize a persisted bootstrap session under ~/.codex.

## Incremental findings

1. Config specialist confirms a thin `uv run --project python dotfiles-setup …` wrapper following neighboring coordinator-handoff/handoff-inbox tasks; those wrappers have no `dir` or dependencies. Its earlier `dir` claim was corrected before use.
2. W0 retains all CLAUDE.md import stubs and pair contracts. W5a must explicitly READ the index; a pointer alone does not establish policy loading.

## Verification

Final combined five-file pytest passes: **544 passed, rc 0**, with all 11 source/test hashes unchanged before/after. Documentation lint and mirror parity pass with real fail arms. Native inventory passes rc 0; live cards/issue preview return explicit PARTIAL rc 2. Required runtime bootstrap proof is BLOCKED, and the shipping-policy discrepancy remains unresolved.

## Research receipt

Parent owns the shared strict-five receipt; it passes PROVISIONAL with recorded Firecrawl credit substitutions and primary verification below.

### Config specialist incremental result

`mise.toml:1743` now declares a thin `lane-cards` task: `uv run --project python dotfiles-setup lane-cards`. `mise tasks info lane-cards --json` rc 0 resolved the intended worktree source/cwd and empty depends/env arrays. `git diff --check -- mise.toml` rc 0. Public task evidence awaits registry implementation. Full gates remain NOT_RUN.

### Documentation starting measurement

Root AGENTS.md measured live: 11,892 Unicode characters, 11,978 UTF-8 bytes, 194 lines. All 27 rule files were enumerated: 25 eager rules and 2 path-scoped rules (`ci-local-parity`, `md-size-budgets`). W0 import stubs will remain untouched.

### W5a implementation

Moved the unchanged key-file reference from root AGENTS.md to the policy index and added the explicit Codex READ bootstrap. All 25 eager and both scoped policies are mapped, along with `.claude/CLAUDE.md`, nested AGENTS instructions and canonical generated skill pointers. Root invariants and CLAUDE stubs are retained. Updated root: 10907 chars / 10991 bytes / 187 lines.

### Runbook and handoff skill

Unified runbook now specifies shared roles, read-only recovery, card schema, issue preview, SLOT request/grant/release, main-checkout ship/land and both-direction transfer. All W4 capabilities and Codex coordinator writes are explicitly deferred to B2. Canonical handoff skill calls the agreed explicit `snapshot-cards --handoff <absolute-tracked-handoff> [--repo-root …]` before commit/ship; no automatic launch side effect is claimed.

### Shared research receipt (parent result)

Native fnox research-fanout completed rc 0 under strict-five-v2, request `01a10c0e-f0a2-7160-bae7-be097a3e5127`, generated `2026-10-05T12:39:52.364253+00:00`. Receipt is **PROVISIONAL**: Firecrawl search failed with exact blocker `Error: Request failed with status code 402`, recorded credits-exhausted and substituted by Serper HTTP 200 (status ok). GitHub issues/discussions/releases empty_verified with controls 10/10/1; Exa ok10; Context7 ok5; Firecrawl developer ok10; Firecrawl search via Serper ok10; Last30Days ok10. No app connector/MCP ran. Manifest: `/Users/rmanaloto/.codex/research-coverage/01a10c0e-e4ea-7ba2-9e45-ffc8a51d42df/01a10c0e-f0a2-7160-bae7-be097a3e5127/manifest.json`. Parent primary verification pending. Parent graphify-health rc 3: missing worktree graph.json; source fallback used.

### Initial gate capture failure

Both initial lint-docs and skills-mirror attempts exited 1 before invocation because `.agent/logs/` did not exist. No gate ran. Created the standard runtime log directory, then retried with the same file-capture contract.

### Research primary verification updates

Parent ran public `validate_strict_five(manifest, request_id)`: rc 0, passed=True, provisional reason Firecrawl search via Serper (credits-exhausted). GitHub code-search controls rc 0 each: official Codex loader must-hit query returned 2 source/test paths; fresh absent query returned 0. Official OpenAI agents documentation redirected to `https://learn.chatgpt.com/docs/agent-configuration/agents-md` and its web contents confirmed first per-directory candidate, root-to-cwd concatenation and documented 32 KiB default; this is not installed effective config evidence. Original-URL native mirror invocation rc 0 masked a failed route: probe reported `route=webclaw`, `code=redirected`, `bytes=0`, `provisional=false`; parent retried the canonical URL. Tools/routes actually run: fnox, mise, uv/Python, gh, ctx7 library/docs, Exa HTTP, Firecrawl developer HTTP, Firecrawl search CLI with Serper HTTP fallback, Last30Days script, official-doc web open. No connector/MCP ran. Parent skill: codex-sdlc-team; documentation skill: skill-creator.

### Documentation lint schema correction / fail arm

`mise run lint-docs` initially ran and exited 1 with two agent-file frontmatter errors at the new docs line 1. agnix classifies `**/agents/*.md` as agent files; existing `docs/agents/goal-history.md` and `codex-task-orchestration.md` demonstrate the expected name/description frontmatter. Added the same supported metadata, without new suppressions. The real missing-frontmatter arm already proved the lint gate fails on that realistic omission. Generator `mise run skills-mirror` rc 0: WROTE coordinator-handoff.

### Documentation gate evidence

- `mise run lint-docs` rc **0**, no issues; capture `.agent/logs/phaseB1-lint-docs.{log,rc}`. Missing-frontmatter arm rc **1** before correction (both new docs), demonstrating a realistic lint failure.
- `mise run skills-mirror` rc **0**, coordinator-handoff regenerated; capture `.agent/logs/phaseB1-skills-mirror.{log,rc}`.
- `mise run skills-mirror -- --check` rc **0**, generator parity; capture `.agent/logs/phaseB1-skills-mirror-check.{log,rc}`.
- Real stale-mirror control removed the new snapshot instructions from canonical skill only, retaining the generated mirror; the public parity check returned rc **1** with `skills-mirror DRIFT: coordinator-handoff`. Restored canonical bytes in finally; public check rc **0**. Captures `.agent/logs/phaseB1-skills-mirror-control.{log,rc}` and `phaseB1-skills-mirror-restored.{log,rc}`. Mirrors were never hand-edited.
- `git diff --check -- <owned documentation paths>` rc **0**.

### W5a actual runtime probe — licensed dissent

**BLOCKED / NOT_RUN**: actual eager/scoped/discovered-skill runtime load proof, removed-bootstrap runtime fail arm and effective `project_doc_max_bytes` measurement. No synthetic probe is substituted. Spec §4 simultaneously prohibits user-level file changes (`~/.codex`), prohibits `--ephemeral`, and requires a fresh persisted isolated Codex session in §5/adopted design. Installed `mise exec -- codex exec --help` rc 0 documents `--ephemeral` as disabling persisted session files and `--ignore-user-config` as still using CODEX_HOME for auth. The primary config schema exposes `log_dir` and `sqlite_home`, but neither relocates rollout/session storage; no session/rollout-directory config key was found by full property enumeration. The primary agents guide describes CODEX_HOME relocation (`docs/research/kb/raw/codex-takeover/links/codex-agents-md-fallback.md:99-103`), which conflicts with the current developer instruction never to repurpose CODEX_HOME. Parent accepted this dissent and instructed no repurposing or ephemeral workaround. No Codex session was started and no user-level file was modified by this specialist.

The schema and current official guide document a 32 KiB default; this is **not** the measured effective installed runtime value. Root received-file measurement is 10,991 UTF-8 bytes / 10,907 characters / 187 lines; runtime combined closure and actual policy adherence remain unverified. Resolving the probe requires an explicit compatible persistence/isolation authorization from the architect, not a guessed CLI setting.

### Primary mirror recovery

The original developers URL native mirror had command rc 0 but reported redirected/0 bytes and was preserved as a failed route. Canonical `https://learn.chatgpt.com/docs/agent-configuration/agents-md` retry rc **0**, 8,063 bytes, route `webclaw`, provisional=True, generated `2026-10-05T12:43:59.301839+00:00`. **PROVISIONAL:** Firecrawl scrape via Webclaw (credits-exhausted), in addition to Firecrawl search via Serper. Artifacts `agents-md-current-probe.json` and `agents-md-current.md` reside in the shared receipt directory. At that checkpoint, parent reported no other unrecovered provider-route failure; later primary-source path retries are recorded below.

### Static preservation review (not runtime load proof)

All 27 canonical rule files appear in the index; all local Markdown targets exist. Root is 10,907 chars / 10,991 UTF-8 bytes / 187 lines. Read-only comparison with HEAD proves the invariant-bearing root tail from `## Subdirectories` onward is identical after removing only the added bootstrap; the original Key Files section is preserved verbatim in the index. Root CLAUDE.md is byte-identical to HEAD; no nested stubs changed. Initial static probes incorrectly assumed literal stub bytes instead of comparing the existing file: the current and HEAD stub both include `@AGENTS.md` plus the existing explanatory HTML comment. Direct byte comparison corrected the probe without changing the stub. These checks do not assert runtime adherence or policy injection.

### Shipping-instruction consistency finding — stopped for caller respec

Canonical coordinator-handoff skill §1 retains its existing docs-only handoff-worktree ship exception, citing `pr._ship_preflight` refusal only when `needs_full_sync`. The adopted W5b design/runbook requests main-checkout dotfiles ship/land. The new shared runbook states main-checkout shipping; no existing exception was silently rewritten. Documentation specialist reported this discrepancy and stopped further shipping-instruction changes pending parent ruling.

Parent ruling: apply LICENSED DISSENT literally; no shipping-policy reconciliation or canonical exception change in this dispatcher run. Stop affected instruction changes, preserve exact partial edits, and report for caller respec. Existing exception anchors: `.claude/skills/coordinator-handoff/SKILL.md:51-54`, `python/src/dotfiles_setup/pr.py:596-627` (linked refusal conditioned on `needs_full_sync` at :612). New runbook main-checkout instruction is at `docs/agents/session-orchestration.md:138`; adopted W5b design `docs/specs/codex-takeover-phaseB-design.md:367-370` says main-checkout ship/land. This remains **UNRESOLVED**, alongside the W5a runtime probe blocker.

### Specialist ownership split / final spawned roster

Parent split W3 work after `/root/python` explicitly acknowledged yielding `session_ledger.py`, `session_store.py`, `command_audit.py`, `session_review.py` and their three tests. Newly spawned `/root/digest` owns those files. `/root/python` retains registry/main/handoff and their two tests, plus final combined five-file targeted pytest. `/root/config` owns mise.toml; `/root/documentation` remains the sole report/documentation writer. No SLOT GO was granted.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python`
- `sdlc-config-specialist` — `/root/config`
- `sdlc-documentation-specialist` — `/root/documentation`
- `sdlc-python-specialist` — `/root/digest`

No others were spawned.

### Later primary-source path recovery

Digest specialist inherited the obsolete official Codex source path `codex-rs/core/src/tools/handlers/exec_command.rs`; its HTTP request returned **404**. Retried the current official path `codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs` successfully. This failed primary path is preserved separately from the provisional provider-credit substitutions. Full digest evidence/report pending.

## Current status boundaries

- **Required proof BLOCKED:** W5a actual persisted Codex positive and removed-bootstrap runtime controls; effective runtime byte limit NOT_MEASURED.
- **Unresolved policy contradiction:** adopted runbook main-checkout shipping versus canonical docs-only handoff-worktree exception and existing preflight behavior. Affected further instruction changes stopped; caller respec needed.
- **NOT_RUN, no SLOT GO:** full lint, full pytest and full verify. These are permission-limited gates, not failures or runtime-proof substitutes.
- **PROVISIONAL research:** strict-five receipt passes with Firecrawl search credits exhausted/substituted by Serper; primary scrape credits exhausted/substituted by Webclaw. The old official-doc redirect/zero-byte and old Codex handler HTTP404 routes were retried successfully and remain recorded.
- **Passed local documentation evidence:** lint-docs rc 0; generated skill parity rc 0; missing-frontmatter and stale-mirror fail arms rc 1; root character preservation check passes. Python targeted/live/mutation reports await their owning specialists.

## W3 digest specialist — incremental report (verbatim)

> W3 incremental: native command_projection tests 5 passed rc0 (/tmp/phaseB1-digest-initial.log), public audit/review first run hit test-module import error rc1 (fix in progress). Verified inherited primary exec_command handler exact refusal string at lines336-345; only that native policy refusal is classified refused for Codex, generic is_error/unrecognized/missing/ambiguous outputs remain unknown. New fixed-shape allowlist/hash-only projection + siblingJSON present; now resolving Ruff limits via small helpers/built-in option dictionaries, no model/schema additions. Full gates remain NOT_RUN.

## Registry/handoff Python specialist — incremental report (verbatim)

> Interim targeted pytest `.agent/logs/codex-takeover-phaseB1-registry-handoff.{log,rc}` rc1: 231 passed, two new handoff tests failed because existing handoff_inbox.edit_file(checkout,target) requires target relative to checkout; passing canonical main with linked-worktree tracked doc violates that public interface. Corrected snapshot typed edit call to use the verified containing registered worktree; card publication still canonical main. Rerun `.agent/logs/codex-takeover-phaseB1-registry-handoff-2.{log,rc}` active. Stable interfaces: lane-cards [--json|--write|--issue-plan] --repo-root repeated; snapshot-cards --handoff tracked existing docs/handoffs/*.md --repo-root repeated. Both writer routes authorize newest native Claude coordinator; Codex writer blocked. Digest CLI --digest/--since/--providers repeat/comma --repo-root repeat --codex-base/--claude-base wired by me and implemented by digest specialist.

## Registry/handoff Python specialist — targeted/live result (verbatim)

> Evidence ready: targeted registry/handoff rc0,233passed34.55s `.agent/logs/codex-takeover-phaseB1-registry-handoff-2.{log,rc}`. Live native inventory rc0 rows134: working23 blocked14 stopped30 done67. lane-cards --json rc2 sessions1935: all134 Claude +1801Codex metadata rows (803dotfiles+998KB Codex, unknown liveness/state). Dotfiles Claude working16 blocked10 stopped28 done57; KB working6 blocked1 stopped1 done6; unresolved Claude working1 blocked3 stopped1 done4. Omissions11=9unregistered cwd+2missing Codex metadata. --issue-plan rc2 intentions53 actions46blocked7reuse; dotfiles33blocked7reuse,KB8blocked,unresolved5blocked; request#1715-1721 reused, no done-only lane intentions. Captures `.agent/logs/codex-takeover-phaseB1-live-{inventory,cards,issues}.{json,stderr,rc}`. No card/GH/plan writes in live probes. Mutation red arms next; broad gates NOT_RUN no SLOT GO.

Live inventory is explicit **PARTIAL** at lane-cards/issue-plan rc 2; successful native inventory rc 0 does not upgrade uncertain Codex metadata/liveness or unresolved Git topology to complete. Counts include working/blocked/stopped Claude rows from both resolved repositories; Codex rollout metadata is discovery evidence, not verified process liveness or role/state.

### Registry specialist static checks / mutation coordination

Parent reports targeted Ruff rc **0** and correctly project-routed `uv … ty check <owned paths>` rc **0**. Initial bare `mise` ty route exited **1** because it selected the wrong Python/import roots; this failed route remains recorded. Three additional public controls were added after the 233-passed run, so that checkpoint is not the final combined five-file test proof. Registry/handoff author temporarily owns real red mutations in session_registry.py/coordinator_handoff.py; other agents must not read/run those files until restoration is confirmed.

## Registry/handoff Python specialist — mutation/schema result (verbatim)

> 13/13 real source regression mutations red rc1 (all targeted assertions, no collection errors): omitted Codex rows; filtered nameless rows; removed path sanitizer; accepted failed Claude call; clobbered failed-census cards; lexicographic timestamp order; disabled role chain; removed predecessor wire; removed stable-marker reuse; included done-only lanes; failed issue reads create; removed writer auth; removed handoff write. Manifest `.agent/logs/codex-takeover-phaseB1-mutations/manifest.json` with per-control .log/.rc. All restored. Live schema correction: startedAt is integer Unix milliseconds in134/134 rows (13digits); treating raw strings as ISO fell back to IDs. Added millisecond normalization and native fail arm; refresh public probe pending. Design had no mandated timestamp wire type, so this honors parsed-started_at requirement. Prior live IDs/states match independently confirmed; zero done-only preview intentions. Owned Ruff rc0; correct uv-runtime ty check rc0.

All red source mutations were restored before shared verification. Live startedAt millisecond normalization is an observed native schema correction, not invented ISO data; final public refresh and combined-five-file gate must validate the corrected implementation.

### Additional W3 interim checkpoints (parent result)

Public digest subsets first had 16 passing tests, then 24 passed / 1 cache-fixture failure (rc 1); the fixture failure was fixed. Three-file W3 targeted tests are running; five digest mutations remain pending. None of these checkpoints substitutes for the final combined-five-file result. Parent independently checked native startedAt: dividing 13-digit epoch-ms by 1 is invalid while dividing by 1000 yields 2026-10-05; optional name is present on 133/134 native rows. Native epoch-ms red control/live refresh remain pending at this checkpoint.

## W3 digest specialist — targeted/cache interim result (verbatim)

> W3 targeted three-file first run304passed/1 warm-cache fixture setup error rc1 captured /tmp/phaseB1-digest-targeted.log + .rc. Required append_parser args in both public SessionStore fixture calls corrected. Warm unchanged-source cache control now1passed rc0 /tmp/phaseB1-digest-cache-final.log+.rc. Five serialized provider/date/pairing/repo/privacy mutations running against BOTH public audit/review digest tests; exact rc logs /tmp/phaseB1-digest-mutation-*.log and *.rc forthcoming. Code restored in finally before final targeted3file suite. Focused Ruff six changed files and ty3production rc0 after fixes.

## Registry/handoff Python specialist — native timestamp control (verbatim)

> Native timestamp control now green rc0 (1passed3.40s); realistic removal of millisecond normalization red rc1 (older zzzz-ID selected over newer aaaa-ID). Added to same mutation manifest; all sources restored. Final live refresh active at `.agent/logs/codex-takeover-phaseB1-live-final-{inventory,cards,issues}.{json,stderr,rc}` to reflect the corrected display order. Also hardened missing Codex sessions directory as explicit inventory omission (not empty complete fleet), with isolated positive directory fixtures/negative absent directory public test. Combined five-file pytest waits for digest specialist restoration/readiness.

## W3 digest specialist — public mutation result (verbatim)

> W3 red mutations complete, restored: provider/date/pairing/repository/privacy each rc1, BOTH public audit+review tests failed. Logs /tmp/phaseB1-digest-mutation-{provider,date,pairing,repository,privacy}.log + .rc; privacy rerun now fails directly `assert secret not in artifact_text` in BOTH interfaces. Mutations: delete exec_command names from supported set; remove timestamp predicate; choose first result instead of native ID match; drop cwd filter; return raw command instead of approved shape. Final focused Ruff6files rc0 (/tmp/phaseB1-digest-ruff-final.log+.rc), ty3production rc0 (/tmp/phaseB1-digest-ty-final.log+.rc), diffcheck rc0. Final3file pytest running /tmp/phaseB1-digest-targeted-final.log+.rc. Added explicit source-metadata drift omission (provider census reuse); no new parser/model/schema.

## Registry/handoff Python specialist — final live refresh (verbatim)

> Latest live refresh receipt (supersedes earlier counts): native rc0 rows135 working25 blocked12 stopped30 done68. cards rc2 sessions1937=135Claude+1802Codex(803dotfiles/999KB);11omissions unchanged. Dotfiles Claude working19 blocked8 stopped28 done57; KB working4 blocked2 stopped1 done7; unresolved working2 blocked2 stopped1 done4. issuepreview rc2 intentions52=45blocked7reuse. All135native IDs and state counts exactly match; registry coordinator display matches numeric-native startedAt independent ordering. Comparison `.agent/logs/codex-takeover-phaseB1-live-final-comparison.json`; stdout/stderr/rc final-prefix captures. Fourteen regression controls now red plus native milliseconds green rc0. Ruff, correct uv ty, diff check rc0 captured `.agent/logs/codex-takeover-phaseB1-python-style-{ruff,ty,diff}.{log,rc}`. Final bundle waits digest readiness.

This **supersedes** the earlier 134-native-row / 1935-session checkpoint; the native fleet changed during the run. Current live previews remain PARTIAL rc 2, not failed test gates. All native rows are preserved, including working/blocked/stopped rows in both resolved repositories, while unresolved topology and Codex liveness remain explicit.

## W3 digest specialist — final report (verbatim)

> W3 FINAL ready: three-file target306passed rc0 /tmp/phaseB1-digest-targeted-final.log + /tmp/phaseB1-digest-targeted-final.rc. Fresh random absent command SHA assertions subsequently added to BOTH public audit/review controls;2passed rc0 /tmp/phaseB1-digest-absent-final.log+.rc. Final current Ruff6ownedfiles rc0 /tmp/phaseB1-digest-ruff-final.log+.rc; ty3production rc0 /tmp/phaseB1-digest-ty-final.log+.rc; diffcheck rc0. Five mutations each2failed rc1 captured /tmp/phaseB1-digest-mutation-{provider,date,pairing,repository,privacy}.log+.rc; privacy fails direct secret-not-in-artifact assertion BOTH. Warm cache stale-policy fixture1passed rc0 /tmp/phaseB1-digest-cache-final.log+.rc; final suite includes that plus explicit malformed-metadata discovery omission case. Modified6files: session_ledger.py,command_audit.py,session_review.py and their3testfiles; session_store.py unchanged (reused native public storage API). CLI-compatible keyword contract as sent Python owner. Full lint/fullpytest/verify NOT_RUN (no SLOT); exact5file combined owned by Python specialist. Limitations: opaque JS wrapper omitted; unknown/missing/duplicate results/schema drift return partial rc2; only primary-verified native Codex policy refusal recognized. No commits/GH/user-level changes/subagents.

### Final combined gate launched

The exact spec five-file pytest command is running after W3 readiness at `.agent/logs/codex-takeover-phaseB1-five-file-final.{log,rc,sources.json}`. The sourcehash receipt pins 11 production/test paths before execution and verifies unchanged bytes afterward; no further Python source changes are planned unless the gate fails. Result pending.

## Registry/handoff Python specialist — final report (verbatim)

> FINAL exact spec five-file pytest PASSED rc0,544passed66.57s. Log/rc `.agent/logs/codex-takeover-phaseB1-five-file-final.{log,rc}`, sourcehash receipt same prefix `.sources.json`; all11source/test SHA256 hashes unchanged before/after. Ownedregistry/handoff/main slice complete; no further source edits planned. Fullpytest/lint/verify NOT_RUN(noSLOTGO). No commit/push/GH/hook/userfile writes. Session_store unchanged existingAPI reused. Ready to persist final evidence and own report final lint; live latest135Claude/allID-state match+1802Codex,1937total,11omissions; card/issuepreviewrc2 expectedpartial.

## Config specialist — final report (verbatim)

> Implemented only [mise.toml:1743](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/codex-takeover/mise.toml:1743):
>
> `mise run lane-cards -- <args>` delegates to `uv run --project python dotfiles-setup lane-cards`.
>
> Checks: task resolution rc **0**; whitespace diff check rc **0**. No dependencies, environment changes, or B2 configuration added.
>
> Live `--json` / `--issue-plan` probes are assigned to the Python specialist to avoid duplicate inventories. Full lint, pytest, and verify are **NOT_RUN: NO SLOT GO**. No commit or push.
>
> Specialists spawned:
>
> No specialists or other agents were spawned by this specialist.

## Final verification ledger

| Evidence | Final result | Capture / limitation |
|---|---|---|
| Exact spec five-file pytest | **rc 0; 544 passed in 66.57 s** | `.agent/logs/codex-takeover-phaseB1-five-file-final.{log,rc,sources.json}`; 11 hashes stable before/after. |
| Registry/handoff regression controls | **14 realistic mutations, each rc 1** | `.agent/logs/codex-takeover-phaseB1-mutations/manifest.json`; targeted assertion failures, all source restored. Native-ms positive rc 0. |
| Digest controls | **5 mutations, both public consumers fail, each rc 1** | `/tmp/phaseB1-digest-mutation-{provider,date,pairing,repository,privacy}.{log,rc}`; all restored. Privacy fails direct secret-exclusion assertion. |
| Digest final targeted / absent / cache | **rc 0: 306 / 2 / 1 passed** | `/tmp/phaseB1-digest-{targeted,absent,cache}-final.{log,rc}`; combined suite covers final code. |
| Documentation lint | **rc 0** | `.agent/logs/phaseB1-lint-docs.{log,rc}`; missing-frontmatter fail arm rc 1. |
| Generated skills / parity | **rc 0 / rc 0** | `.agent/logs/phaseB1-skills-mirror{,-check}.{log,rc}`; stale-mirror control rc 1, restored check rc 0. |
| Root budget | **10,907 chars / 10,991 UTF-8 bytes / 187 lines** | Below 12,000 chars; unchanged invariant tail and import stubs; runtime combined instruction closure unmeasured. |
| Final native inventory | **rc 0; 135 Claude rows** | `.agent/logs/codex-takeover-phaseB1-live-final-inventory.{json,stderr,rc}`; working 25 / blocked 12 / stopped 30 / done 68. |
| Final card preview | **PARTIAL rc 2; 1,937 sessions** | 135 Claude + 1,802 Codex metadata; 11 omissions; all native IDs/states match independent comparison. |
| Final issue-plan preview | **PARTIAL rc 2; 52 intentions** | 45 blocked / 7 reused; no done-only intentions; no GitHub/card/plan writes. |
| Scoped Ruff / Ty / diff | **rc 0** | Registry `.agent/logs/codex-takeover-phaseB1-python-style-{ruff,ty,diff}.{log,rc}`; W3 `/tmp/phaseB1-digest-{ruff,ty}-final.{log,rc}`; wrong-runtime Ty route rc 1 corrected. |
| Full lint / full pytest / verify | **NOT_RUN: NO SLOT GO** | Architect owns the slot and later full gates. |
| W5a actual bootstrap positive/control | **BLOCKED / NOT_RUN** | Persisted user-level writes vs no-user-file/no-ephemeral/no-CODEX_HOME-repurpose constraints; actual eager/scoped/skill load remains unverified. |
| Effective runtime project_doc_max_bytes | **NOT_MEASURED** | Documented default 32 KiB is not an installed-runtime measurement. |
| Shipping-policy consistency | **UNRESOLVED; affected changes stopped** | Design :367 requires main checkout; skill :51 permits docs-only worktree ship; preflight :612 conditions refusal on full sync. |
| Strict-five research | **rc 0, PROVISIONAL** | Firecrawl search→Serper and scrape→Webclaw, credits-exhausted; failed old URL/source routes recovered and retained above. |

## Final scope and limitations

W1, W2 preview, W3 and W5 documentation changes are present within the allowlist.
`session_store.py` did not need an edit because the existing public storage API was reused.
W2 GitHub issue application, handoff_inbox/provider writer changes, all W4 features,
launcher/launchd/self-heal, hooks and user-level installs remain **NOT_IMPLEMENTED / DEFERRED TO B2**.
This run did not commit, push or deliver the diff. Full heavy gates require architect SLOT GO.
Opaque JavaScript wrappers and unsupported/missing/duplicate native result schemas remain
explicit unknown/partial evidence; no raw payload is credited as executed.
The required W5a runtime proof and the contradictory shipping instructions prevent an
all-green or fully complete Phase B1 claim; caller respec is required for those exact items.

## Parent independent final verification

Current branch `feat/codex-takeover`, HEAD `85e5eaf7a654804010d34c5a7059d75d583f51de`, dirty/uncommitted. Parent independently read the real five-file `.rc` (0) and log (544 passed in 66.57 s), matched all 11 current SHA256 values to `.sources.json`, verified agnix lint-docs log/rc 0 and generator parity log/rc 0, and re-measured root 10,907 chars / 10,991 bytes. The sourcehash receipt, not clean HEAD alone, identifies the tested dirty implementation. No source edits followed the final gate. Known implementation changes stay within the allowlist; initial Phase A/spec/raw untracked paths preexisted this run.

Final registry-owner style refresh also returned Ruff rc 0, uv-runtime Ty rc 0 and diff check rc 0, with existing style captures refreshed. Public interfaces: `session_registry.py:386` collect, `:513` write_cards, `:602` issue_plan; `coordinator_handoff.py:1368` snapshot_cards; `main.py:3047` lane-cards and `:3345` shared digest args.

Exact unresolved shipping anchors: adopted `docs/specs/codex-takeover-phaseB-design.md:367-370` and new `docs/agents/session-orchestration.md:138-141` prescribe main-checkout shipping; canonical `.claude/skills/coordinator-handoff/SKILL.md:51-54` preserves docs-only handoff-worktree shipping; existing `python/src/dotfiles_setup/pr.py:612-627` refuses linked worktrees only when `needs_full_sync(paths)` is true (`:283-290`). No shipping-policy reconciliation was ratified.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python`
- `sdlc-config-specialist` — `/root/config`
- `sdlc-documentation-specialist` — `/root/documentation`
- `sdlc-python-specialist` — `/root/digest`

No others were spawned.

## Architect W5a runtime proof (2026-10-05, after settlement)

The lane's blocker is resolved. A normal `codex exec` writing its own rollout is ordinary
operation, not a user-level config edit. Two read-only arm pairs were run with
`mise exec -- codex exec -s read-only -m gpt-6.1-sol -c model_reasoning_effort="medium" -C <dir> -`.
Evidence: `docs/research/kb/raw/codex-takeover/w5a-probe/`.

| Probe | Positive arm (this worktree, bootstrap) | Control arm (main checkout, no bootstrap) | Discriminates? |
|---|---|---|---|
| 1: policy question ("before reporting does-not-exist") | rc 0; opened `codex-policy-index.md`; correct rule cited | rc 0; ALSO found `probes-need-a-control-arm.md` by its own search | **No.** The fixture admits the answer without the bootstrap, so it is not evidence. |
| 2: unrelated task (summarize `_ship_preflight`, list opened files in order) | rc 0; opened the index, then all 26 eager rule files, `.claude/CLAUDE.md`, `md-size-budgets.md` and `session-orchestration.md` BEFORE `pr.py` | rc 0; opened only `python/AGENTS.md`, `python/src/dotfiles_setup/AGENTS.md`, `pr.py`; 0 rule files | **Yes.** |

**Verdict: W5a PROVEN** on installed codex-cli 0.160.0. The bootstrap line makes codex read the
policy index and the eager rules before ordinary work. Without it, codex reads none of them.

Cost note, for a follow-up optimization: each codex session now reads ~29 policy files up front.
A tiered index could trim that per task (W3 digest input).
