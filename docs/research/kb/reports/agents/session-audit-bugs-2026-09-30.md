# Session audit — bugs lane (cold review by ref) — 2026-09-30

Status: COMPLETE.

⚠️ **Persistence:** the requested tracked path `docs/research/kb/reports/agents/session-audit-bugs-2026-09-30.md`
was DENIED by the PreToolUse `branch_guard` (the checkout is on `main`; `do-not.md` #9). This lane did not branch
(it may not change repo state) and did not route around the guard with a shell write. The report lives at
`<scratchpad>/session-audit-bugs-2026-09-30.md`; the coordinator must persist it verbatim from a branch.

- Lane: handoff §1c session-integrity, **bugs** (a cold bug review with no statement of intent).
- Reviewer: Opus `cold-reviewer` (Claude). Every subject is **Claude-authored**, so the documented cross-family lens
  is codex, which is **usage-limited until 2026-10-03**. This Opus pass is the documented FALLBACK, not the full gate.
- Round: OPEN HUNTING over the landed squash commits. It states no domain with a cardinality, so it cannot end the
  review loop by any outcome.

## Subjects (resolved refs)

| # | Ref | Resolved | What |
|---|---|---|---|
| S1 | `725c79c9` | `725c79c995fec650e3c891666b078ab1abd52669` | S29-H machine-checked handoff (#1461) |
| S2 | `ea1eaa0b` | `ea1eaa0bbe34ca961981a348850067379826d737` | doctor devcontainer arches (#1464) |
| S3 | `28a124a3` | `28a124a3739f9d69580177836f303b977f5e0c24` | graphify 0.9.73 currency (#1467) |
| S4 | `origin/feat/native-cli-installers-workflow` | head `102ee0c5d3d0cc5fb0b4c4194ae9e67da69aac74`, merge-base `a5a9f786b1a953148ae1624d581f2a71f02359d9` | `7171fea0` + `102ee0c5` |

## Findings

Severity is for the landed/branch code as it stands. "Q-SCOPE" says whether the defect is this diff's or a sibling.

### S1 — `725c79c9` S29-H machine-checked handoff

Method: this subject had two earlier cold rounds (`4e337900`, `744c3b92`; reports
`cold-review-4e337900-2026-09-29.md`, `cold-review-744c3b92-2026-09-29.md`). This pass reviews the landed squash and the
delta `744c3b92..725c79c9` (`handoff_check.py` +138/-, `session_state.py` +61/-, the skill).

| # | Severity | Claim | file:line | Evidence | Control arm | Disposition |
|---|---|---|---|---|---|---|
| S1-1 | LOW | The F3 fix (a glued foreign number `KB#N` now ENDS the previous window) silently drops a true claim in the list shape `#A/#B/KB#C all landed`: `#A`'s window stops at `KB#C`, before the shared predicate, and `#B` is never a reference (`/#`). So the whole line yields zero claims and is not counted. It is the one claim in the real corpus whose outcome changed. | `python/src/dotfiles_setup/handoff_check.py:455-467` (boundaries incl. `_GLUED_REFERENCE`), `:59` | Differential replay of the REAL corpus (97 docs: 96 `.agent/plans/session-*.md` + `task_plan.md` active section) through `extract_claims` of `744c3b92` vs `725c79c9` (both modules loaded from `git archive` copies, `__file__` asserted): old 342 claims, new 341, **gained 0, lost 1**: `session-2026-08-29f.md:1 #826 landed` on `# Session 2026-08-29f — … #826/#827/KB#611 all landed` (#826 is a MERGED PR, so the lost claim was TRUE). | Bulk kind oracle: `gh issue list --state all` (627) + `gh pr list --state all` (843) = 1470 = the highest number, so every number classifies. The replay's own control: `gained 0` for the F4 narrowing (`owner/repo #N` is now read as a dotfiles number) proves no corpus line uses that spelling with a claim word. | **Accept / doc-only.** The drop is the documented price of F3 (a glued number "names another repo"). If kept, add one sentence to the skill's claim grammar: "a trailing `KB#N` in a list ends the list's claim — repeat the word on each dotfiles number". |

**Re-verification of round 2's open findings (all six now closed at `725c79c9`):** F1 (mtime vs generation) → a
`- **generated**:` stamp is rendered (`session_state.py:523`) and preferred by `default_since` (`:366-368`); the real
newest handoff `.agent/plans/session-2026-09-30.md:87` carries one, so the mechanism is live. F2 (invisible issue skip)
→ `ClaimTally.skipped` + an info line per skip (`handoff_check.py:708-712`). F3 → `_GLUED_REFERENCE` boundary. F4 →
`_FOREIGN_QUALIFIER` narrowed to KB spellings (corpus impact 0, above). F5 → `handoff_key` identity + `--for` name
validation (`session_state.py:573-578`). F6 → `#A/#B` test at `tests/test_handoff_check.py:972-973`.

**Mutation table (S1 delta, archive harness, pristine control = 170 passed rc=0):** 9 of 9 mutations RED — stamp
ignored; first-not-last stamp; glued boundary deleted; exclude `ValueError` deleted; skip info lines dropped; `--for`
validation deleted; suffix case-fold dropped; `generated` render line dropped; skip count dropped from the OK line.
Every new behaviour in the delta is pinned by a test that fails on its deletion.

| S1-2 | LOW (**UNVERIFIED**; Q-FRESH) | The `generated` stamp is taken at the START of `gather()`, before the `gh pr list --state merged --search merged:>=<since>` call, and the next handoff's window starts exactly at it. `gh pr list --search` reads GitHub's search index; a PR merged seconds before generation that the index has not caught yet is absent from THIS handoff's list, and the next window starts after its merge time, so it is absent from both. | `python/src/dotfiles_setup/session_state.py:391-392` (stamp), `:415` (the later merged fetch), `:366-368` (next window starts at it) | The stamp is `_format_since(utc_now())` computed before `_merged_prs(...)`. Search-index lag is not measured here (my 2026-09-29 memory records "eventual consistency unverified"). | Not armed: arming needs a merge inside a lag window. | **PLAN (cheap):** start the default window a fixed margin before the stamp (for example 15 min); a duplicate row across two handoffs is harmless, a missing one is the defect this stamp was added to close. |

### S2 — `ea1eaa0b` doctor devcontainer arches

Method: two earlier cold rounds (`7cb15346`, `4ccb98a5`). This pass reviews the landed squash and the delta
`4ccb98a5..ea1eaa0b` (`doctor.py` +30, `platform_target.py` +9).

| # | Severity | Claim | file:line | Evidence | Control arm | Disposition |
|---|---|---|---|---|---|---|
| S2-1 | LOW (Q-CLAIM; introduced by the round-2 fix) | The platform-literal gate now demands an arch profile carry its EXACT published triple, but the violation text still tells the operator the old arch-word rule: a level-less `linux/arm64` in `mise.arm64.toml` is reported as "it may only name linux/arm64" — the literal it just rejected. Following the message reproduces the violation. The amd64 message likewise names `linux/amd64`, which the gate also rejects (it needs `linux/amd64/v2`). | `python/src/dotfiles_setup/platform_target.py:546-549` (`render`), vs the new predicate `:608-610` | Ran `find_violations` from a `git archive ea1eaa0b` copy (module path asserted) over a scratch git repo: `mise.arm64.toml:2: platform literal 'linux/arm64' in the arm64 arch profile — it may only name linux/arm64, the arch its MISE_ENV selects`. | The same scratch repo's `mise.amd64.toml` carrying `linux/arm64/v8` produced the expected cross-arch violation, so the harness reads profiles; the real repo's `mise.arm64.toml` (`linux/arm64/v8`) yields none. | **FIX-NOW:** render `it may only name {published_platform(expected_arch)}, the exact published triple its MISE_ENV selects`, and assert the text in `test_an_arch_profile_must_carry_the_exact_published_triple`. |
| S2-2 | LOW (Q-CLAIM; process) | The squash body says "Residual (ticket): .miserc.toml is not honoured under `mise -C`", but no ticket was filed. The residual (round-2 finding 4: SessionStart runs `mise -C "$CLAUDE_PROJECT_DIR"`, and mise reads `.miserc.toml` from the PROCESS cwd) therefore has no tracker entry, and it goes live when mise flips `auto_env` on by default (2027.6.0, per the vendored upstream `configuration/environments.md:209`). | commit `ea1eaa0b` body; `.miserc.toml:4` | `gh issue list --state all --limit 40` created ≥ 2026-09-29: only #1457, #1435, #1434 — none about miserc/`-C`. `gh api /search/issues?q=repo:ray-manaloto/dotfiles+miserc` → 6 hits, none a residual ticket (only #1464 itself). | Control: the same listing shows #1457, the ticket filed the same day for S29-H's deferred findings, so the probe can see a residual ticket. | **FILE the ticket** (issue-filer), citing `cold-review-4ccb98a5-2026-09-30.md` finding 4. |

**Re-verification of round 2 (`4ccb98a5`):** finding 1 (env cache) → `MISE_ENV_CACHE=0` in the child
(`doctor.py:1538`); armed live: `MISE_ENV_CACHE=0 mise settings get env_cache` → `false`, bare → `true`, a misspelled
control var → `true`. Finding 2 (aliases) → stripped (`doctor.py:1427-1428`). Finding 3 (arch-word compare) → exact
triple in both the gate and the doctor. Finding 5 (first stderr line) → up to three lines. Finding 4 → S2-2.

**Mutation table (S2 delta, full `git archive` harness, pristine control = 81 selected passed rc=0):** 7 of 7 RED —
env cache line deleted; `MISE_PROFILE` / `MISE_ENVIRONMENT` un-stripped; doctor and gate reverted to arch-word compares;
stderr back to one line; port-collision clause disabled.

### S3 — `28a124a3` graphify 0.9.65 → 0.9.73 currency

Method: two earlier cold rounds (`6ef572d4`, `b8479e34`). This pass reviews the landed squash, including the
`0.9.72 → 0.9.73` bump that no earlier round saw.

| # | Severity | Claim | file:line | Evidence | Control arm | Disposition |
|---|---|---|---|---|---|---|
| S3-1 | LOW (test gap for a claimed behaviour) | Three of the four opt-out behaviours the round-2 fix CLAIMS are unpinned: "the shared runner forces the opt-out (an ambient "0" no longer wins)" and "both graph bake-off graphify children carry it". Reverting the runner to `setdefault` (an ambient `GRAPHIFY_NO_AUTO_REFRESH=0` then wins and 0.9.73 rewrites a stale HOME skill), or deleting either bake-off opt-out, leaves every test green. The skill now asserts both as facts ("forced, so an ambient `0` cannot win"; "both bake-off sites"). | `python/src/dotfiles_setup/graphify.py:572`; `python/src/dotfiles_setup/graph_bakeoff.py:156`, `:571`; claim text `.claude/skills/graphify-currency/SKILL.md:116-119` | Mutation table below: G2, G3, G5 survive (156 passed each). The only opt-out test, `tests/test_graphify.py:1630-1647`, calls `prs()` with `without_env_diff` patched to `dict` (an EMPTY env), so it cannot tell "forced" from "setdefault", and it never touches `graph_bakeoff`. | Pristine control 144 passed rc=0 (156 with `test_pin_parity.py`); the path-probe opt-out (G1), the mise `[env]` line (G7), the receipt `rstrip` (G6) and two scrub names (G8, G9) all go RED in the same harness, so the harness discriminates. | **FIX-NOW (tests only):** in the opt-out test, patch `without_env_diff` to return `{"GRAPHIFY_NO_AUTO_REFRESH": "0"}` and still assert `"1"`; add a bake-off test that fakes `subprocess.run` and asserts the opt-out on `_run` and `gather_versions`. |

**Mutation table (S3, full `git archive 28a124a3` harness; tests: `test_graphify.py`, `test_graphify_currency.py`,
`test_graph_bakeoff.py`, `test_pin_parity.py`):**

| Mutation | Result |
|---|---|
| G1 path-probe opt-out dropped (`graphify_currency.py:195`) | RED (4 failed) |
| G2 bake-off `_run` opt-out dropped (`graph_bakeoff.py:156`) | **survived** |
| G3 `gather_versions` opt-out dropped (`graph_bakeoff.py:571`) | **survived** |
| G4 `_rebuild_env` opt-out dropped (`graphify.py:589`) | survived — **not a finding**: the rebuild spawns through `_run` (`graphify.py:862-865`), which forces the opt-out anyway |
| G5 runner forced → `setdefault` (`graphify.py:572`) | **survived** |
| G6 receipt `rstrip` removed | RED (4 failed) |
| G7 root `mise.toml` `[env]` opt-out removed | RED (1 failed) |
| G8 / G9 scrub `OPENAI_BASE_URL` / `AWS_ACCESS_KEY_ID` removed | RED (1 failed each) |

**Probes that came back clean (with their controls):**
- Receipts 0.9.66-0.9.73 are byte-equal to `gh api repos/Graphify-Labs/graphify/releases` bodies after the writer's
  own normalization (`replace("\r\n","\n").rstrip()`), 8 of 8. 0 of the last 40 upstream bodies carry an interior
  trailing-whitespace line or a lone CR, so the writer's tail-only normalization is sufficient today.
- The installed venv is `graphifyy 0.9.73`, and its `__main__.py:289` still reads `GRAPHIFY_NO_AUTO_REFRESH` with
  `("1","true","yes")`; `_refresh_stale_skills()` is still called at `:726`.
- `skills-mirror --check` on `main` (= `28a124a3`): rc=0.
- The `cpy` typos allowance binds by basename glob `0.9.*.md`; `git ls-files` finds 9 such files, all under
  `docs/receipts/graphify/`.

### S4 — `origin/feat/native-cli-installers-workflow` (`a5a9f786..102ee0c5`)

803 files, +142,790 lines: one new saved workflow (`.claude/workflows/native-cli-installers.js`, 292 lines), two
tests, two specs, 14 agent reports, and 785 raw-source files (744 of them a copy of mise's docs SOURCE tree). No PR and
no CI run exist for this branch (`gh pr list --head …` → `[]`; `gh run list --branch …` → `[]`). Specs and verbatim
reports were read only where code or a gate consumes them.

Harnesses: (1) `tests/test_workflows_js.py` from `git archive 102ee0c5` → 28 passed rc=0 (control). (2) A scenario
driver over the REAL workflow source (`git show 102ee0c5:.claude/workflows/native-cli-installers.js`) with a recording
`agent()` (label, agentType, model, effort, prompt), a per-label null injector, and a `parallel()`/`pipeline()` that map
a throwing thunk to `null` (the documented runtime semantics; the repo stub uses bare `Promise.all`). (3) Renovate
44.125.2 `--platform=local --dry-run=lookup` with the repo's own `RENOVATE_FORCE='{"cloneSubmodules":false}'` recipe
(`python/src/dotfiles_setup/renovate_dryrun.py:70`) over a scratch repo holding `renovate.json`,
`.devcontainer/Dockerfile` and the vendored tree.

| # | Severity | Claim | file:line | Evidence | Control arm | Disposition |
|---|---|---|---|---|---|---|
| S4-1 | **MEDIUM** | The vendored mise docs tree ships a `Dockerfile` that Renovate EXTRACTS as a live package file (`debian:trixie-slim@sha256:a99cfc51…`). `renovate.json` enables the `dockerfile` manager, sets no `ignorePaths` covering `docs/**` (the `jdx` preset's list covers `node_modules`/`vendor`/`examples`/`test(s)` only), and rule 3 automerges every `digest` update. The first time Debian re-publishes `trixie-slim`, a bot PR will rewrite a "verbatim" raw record, and auto-merge it. | `docs/research/kb/raw/mise-packslip-docs-2026-09-30/mise/docs-source/.vitepress/showreel-capture/Dockerfile:20`, `:53`; `renovate.json` `enabledManagers` + `packageRules[3]` | Renovate report: `dockerfile docs/research/kb/raw/mise-packslip-docs-2026-09-30/mise/docs-source/.vitepress/showreel-capture/Dockerfile debian trixie-slim sha256:a99cfc517144 []` plus 14 apt-package deps from the same file. No update is pending TODAY (empty `updates`). `gh api repos/jdx/renovate-config/contents/default.json`: `ignorePaths` has no `docs/**`. Recent main commit `249c3fa4` ("Update docker/dockerfile:1.27 Docker digest", #1465) shows the digest path is live. | Same run: `.devcontainer/Dockerfile` extracted with pending `digest` updates (`ubuntu 26.04`, `docker/dockerfile 1.27`), so lookups work; rc=1 is the documented node-engine warning (`mise.toml:958-962`), not an extract failure. | **FIX before merge:** add `"ignorePaths": ["docs/research/**"]` (append to the preset's list, or restate it) in `renovate.json`, or drop the Dockerfile from the vendored copy. Arm it with the same `renovate-dryrun` recipe: the vendored file must disappear from `packageFiles`. |
| S4-2 | MEDIUM (Q-SCOPE: a pre-existing class, magnified) | The "docs mirror" is a 21.75 MiB copy of mise's whole docs SITE, including binaries no report cites: `demo.mp4`, two `.mp3`, a `.gif`, 15 PNGs, 3 TTF and 4 WOFF2 fonts. Squash-merging it makes the bytes permanent in history (the whole `.git` is 49 MB). It also carries CODE into Graphify's corpus: the manifest already scans `docs/research/kb/raw/**` (573 paths today, including `.ts` and `.py`), and `.graphifyignore` excludes only `docs/research/mintlify-cache/`. So the next rebuild ingests 8 `.py`, 143 `.ts`, 9 `.mjs` and 9 `.vue` files from mise's showreel into this repo's code graph, polluting `graphify-affected` and `graphify-query` answers. It also ships a nested `.mise.toml` whose `commit-and-push` task runs `git ci -pm docs` then `git push`. This host trusts `/` (`trusted_config_paths`), so that task is runnable from inside the tree. | `docs/research/kb/raw/mise-packslip-docs-2026-09-30/**` (744 files); `…/docs-source/.mise.toml:4-6`; `.graphifyignore:1-7` | `git ls-tree -r -l 102ee0c5 -- docs/research/kb/raw/mise-packslip-docs-2026-09-30` → 21.75 MiB; `git diff --numstat` lists 29 binary blobs (15 png, 4 woff2, 3 ttf, 2 mp3, 2 jpg, 1 mp4, 1 gif, 1 ico). Manifest probe: `docs/research/kb/raw/2026-09-11-anthropics-mods-diff-shell-tools.ts` and `…/FilipHarald_oma-mise__bootstrap.py` are already graph inputs. Font licensing for the `rocgrotesk-*` webfonts is **UNVERIFIED** (not read). | Control for the graph claim: the manifest DOES list files under `docs/research/kb/raw/` (573), so the probe can see raw-tree ingestion. `betterleaks dir … docs/research/kb` over the S4 archive → "no leaks found", rc=0 (25.2 MB scanned); that arm was not seeded with a known secret, so it is a presence check only. | **FIX before merge:** keep only the `.md` pages the report cites (the vitepress theme, showreel, fonts, media, Dockerfile, `.mise.toml` and `lefthook.yml` add nothing a citation needs). Or add the tree to `.graphifyignore`, and to `renovate.json` `ignorePaths` (S4-1). |
| S4-3 | **MEDIUM** | Execute mode runs Docs AFTER QA and AFTER Review. The docs lane edits `.claude/rules/ai-cli-invocation.md` (an eager rule), `.claude/CLAUDE.md` (rule-synced with knowledge-base), skills, and the regenerated `.agents` mirror. None of those edits reach `lint-docs`, `md_size_budget`, `rule-sync`, the cold review, or the security review; only `verify:live` runs after them, and it checks binaries, not prose. The cold review is also told to review "the working tree", which the docs lane then changes. So the reviewed subject is not the shipped subject. Separately, a `null` QA or review result does not stop the run: it continues to Docs and Verify and returns `gates: null` beside a normal result. | `.claude/workflows/native-cli-installers.js:253-292` (phase order), `:262-265` (review target = working tree), `:254` (no null check on `gates`) | Driver, execute defaults: call order `implement:repo, qa:gates, cold-reviewer:diff, review:security, docs:sync, verify:live`. With `qa:gates`, `cold-reviewer:diff` and `review:security` forced `null`, the run returned `gates: null, reviews: [null, null]` and `error: None`. | Control: forcing `implement:repo` null throws `implementer returned null` (`:233`), so the driver's null injection does reach the script's guards. | **FIX before merge:** move `docs:sync` before `qa:gates`; have review pin a commit (the implementer and docs lanes commit on the worktree branch, and review gets that SHA); `if (!gates \|\| gates.gates.some(g => g.rc !== 0)) throw …` before Review. |
| S4-4 | **MEDIUM** | Execute mode silently skips the Sweep when `args.sweepTargets` is absent. `SWEEP_TARGETS` defaults to `[]`, `pipeline([])` spawns nothing, no log line is emitted, and the result carries `swept: []` as if the sweep happened. Nothing wires plan mode's `inventory.files` into execute, so the operator must hand-copy it. The spec's own requirement, "remove these tools from EVERY mise config incl. worktrees" (`:173`), is therefore dropped by a default, without a trace. | `.claude/workflows/native-cli-installers.js:224`, `:238-251` | Driver, `mode: execute` without `sweepTargets`: labels `implement:repo, qa:gates, cold-reviewer:diff, review:security, docs:sync, verify:live`, `log` events `[]`, `swept: []`. | The repo's own test supplies two targets and sees two `sweep:*` calls (`tests/test_workflows_js.py` `test_native_cli_installers_execute_mode_reaches_every_phase`), so the sweep path works when fed. | **FIX before merge:** `if (!Array.isArray(A.sweepTargets)) throw new Error('execute needs args.sweepTargets (the plan inventory, or [] explicitly)')`, and log the count. Better: accept the plan result's `inventory` directly. |
| S4-5 | LOW (Q-CLAIM) | The comment "Standing constraints every stage inherits" is false. `RULES` is appended to 4 of 8 plan-mode prompts (discover + the 3 research lanes) and to 0 of 6 execute-mode prompts. The lanes that edit files (implement, sweep, docs), and the lane that runs binaries and the doctor (verify), never receive "Edits outside a file allowlist are forbidden", "Print presence of credentials, never values", or the HOST/IMAGE/CI classification rule. The sweep lane is the one that could remove an IMAGE pin. | `.claude/workflows/native-cli-installers.js:37-44` (claim), `:127`, `:142`, `:150`, `:161` (the only four uses) | Driver: plan mode — `RULES carried by: discover:mise-configs, research:native-installers, research:github-examples, research:blast-radius` of 8 calls; execute mode — `[]`. | The marker string `Print presence of credentials` is found in exactly the 4 prompts that interpolate `${RULES}`, so the probe discriminates. | **FIX-NOW:** append `\n- ${RULES}` to every agent prompt, or narrow the comment to "the discovery and research lanes". |
| S4-6 | LOW (Q-CLAIM) | "N research lane(s) returned null — carried as gaps" is false. The spec writer is given only the surviving `reportPath`s and is never told a lane failed or which one. The returned `research` array drops the null, so the caller cannot tell which lane is missing either. | `.claude/workflows/native-cli-installers.js:165-166`, `:172`, `:210` | Driver, `research:github-examples` forced null: the log says "1 research lane(s) returned null — carried as gaps"; the `design:spec` prompt's line is `Research reports: /r/research:native-installers, /r/research:blast-radius`; "github-examples" and "gap" are absent from the prompt; `result.research.length == 2`. | With no lane nulled, all three `reportPath`s appear (plan-mode default run). | **FIX-NOW:** keep the labels, pass `Missing research lanes: …` into the spec prompt, and return `researchGaps`. |
| S4-7 | LOW | The cold reviewer is told the wrong author family for `codex-astra-implementer`. The ternary knows only `codex-sol-implementer`, so an astra (codex-family) diff is announced as "Anthropic — same-family fallback, say so". The reviewer then records a false degraded-gate label, although an Opus pass on a codex diff is the full cross-family gate. | `.claude/workflows/native-cli-installers.js:263` | Driver, `implementer: codex-astra-implementer` → prompt contains `author family: Anthropic — same-family fallback, say so)`. | With `codex-sol-implementer`, the same expression yields `codex`. | **FIX-NOW:** `IMPLEMENTER.startsWith('codex-') ? 'codex' : …`. |
| S4-8 | LOW (**UNVERIFIED**; Q-FRESH) | Sweep agents run concurrently (`pipeline`, up to 16 agents, `$CC/workflows.md:357`). Each agent "proves the tool no longer resolves through mise" with `mise ls` from its own directory, but the global `~/.config/mise/config.toml` is edited by another concurrent agent in the same pipeline, and a global pin makes the tool resolve everywhere. So each proof depends on whether the global sweep has finished yet. A repo agent that sees the tool still resolving may report failure, or edit the global file itself, concurrently with the global agent. | `.claude/workflows/native-cli-installers.js:238-249` | Prompt text: "after the edit run `mise config ls` and `mise ls` from that directory to prove the tool no longer resolves through mise", with no ordering between the `kind: global` target and the rest. | Not armed (it depends on agent behaviour under a race). | **PLAN:** sweep the `global` target first (a separate `agent()` before the pipeline), then fan out the rest. |
| S4-9 | LOW (Q-CLAIM) | "plan mode is read-only everywhere" is false. Every plan-mode lane but discovery and premises WRITES: the reports go to `${OUT}` (default `${REPO}/docs/research/kb/reports/agents`), and the spec goes to `${REPO}/docs/specs/`. If `repoRoot` is a checkout on `main`, the PreToolUse `branch_guard` denies every one of those writes. This lane hit exactly that denial on this checkout. | `.claude/workflows/native-cli-installers.js:40`, `:27`, `:142`, `:150`, `:161`, `:171`, `:191`, `:198` | This review's own `Write` to `docs/research/kb/reports/agents/…` was denied: "You are on the default branch (main) … branch FIRST". | A write to the scratchpad (outside the repo) succeeded, as the guard documents. | **FIX-NOW:** say "read-only outside `${OUT}` and the spec path", and refuse `repoRoot` on a default branch up front (have the discover lane report `git branch --show-current`, then throw). |
| S4-10 | LOW | The Discover lane's file-name list omits six mise config spellings that upstream documents: `mise/config.toml`, `mise/conf.d/*.toml`, `.mise/config.toml`, `.mise/conf.d/*.toml`, `.config/mise.toml`, and `.config/mise/config.toml`. It also bounds `~` at `maxdepth 3`. The native, authoritative list is `mise config ls` run per directory, which the prompt uses only later, in the sweep. A pin in a missed spelling survives the migration and keeps shadowing the native binary. | `.claude/workflows/native-cli-installers.js:121-122` | Vendored upstream `docs-source/configuration.md:38-48` lists these paths. | "at least" in the prompt allows a diligent lane to search more, so this is a completeness risk, not a certainty. | **FIX-NOW:** add the six spellings, and require `mise config ls` from each repo/worktree root as the discovery's second route. |
| S4-11 | LOW (doc drift) | `.claude/CLAUDE.md` enumerates the saved workflows and does not list the new `/native-cli-installers`. | `.claude/CLAUDE.md:67` | `git grep research-sweep-run 102ee0c5 -- .claude/CLAUDE.md` finds the list; `native-cli-installers` is absent from it. | — | **FIX-NOW** (one word), in the same PR. |

## Count

**0 HIGH · 4 MEDIUM · 12 LOW (16 total).**
- MEDIUM, all in S4: S4-1, S4-2, S4-3, S4-4.
- LOW: S1-1, S1-2, S2-1, S2-2, S3-1, and S4-5 through S4-11.

Per-subject verdict:
- S1, S2 and S3 are landed and hold. Their residue is LOW, and every delta behaviour in S1 and S2 is mutation-pinned.
- S4 is **DO NOT MERGE as-is**, because of S4-1 through S4-4.

## Required questions

- **Q-FRESH** (is each decision re-validated against freshly read inputs right before its action?):
  - S1: handoff-check takes no action. The window stamp has a search-index lag gap (S1-2, UNVERIFIED).
  - S2: the doctor only prints a restore command. It resolves each arch through `mise env` in the same run, with
    `MISE_ENV_CACHE=0`, so the answer is fresh.
  - S3: there is no decision→action pair.
  - S4: the sweep delegates the dirty-tree and live-writer re-check to each agent at action time, which is fresh.
    The global-config/`mise ls` proof, however, races (S4-8), and QA/review results are never re-checked before Docs
    and Verify (S4-3).
- **Q-SCOPE** (is each finding in scope here, or a sibling?):
  - In scope: S1-1, S2-1, S3-1 and S4-1 through S4-11.
  - S1-2 is a sibling. It belongs with the deferred S29-H claim-grammar ticket #1457.
  - S2-2 is a process gap (a residual ticket that was promised but not filed).
  - S4-2's graph-ingestion half is a pre-existing class, which this branch magnifies.
- **Q-CLAIM** (does every operator-facing string clause added or changed have an enforcing line?). Checked clauses:
  - S1 `handoff-check: info — skipped … is an issue, not a PR` is enforced: `claim_holds` returns None only for
    `ItemKind.ISSUE` (`handoff_check.py:484-487`).
  - S1 skill "(matched by date + letter)" is enforced by `handoff_key`.
  - S1 verify-skill row: `GH_HOST=bogus.invalid` → `pr_claim_unverifiable` rc=1. Armed live: a merged-PR fixture
    returns `OPEN` → `pr_claim_mismatch` rc=1, `MERGED` → OK rc=0, and `MERGED` + bogus host → unverifiable rc=1.
  - S2 profile violation text has no enforcing line: **S2-1**.
  - S2 commit body "Residual (ticket)" has no ticket: **S2-2**.
  - S3 "forced, so an ambient `0` cannot win" is enforced in code (`graphify.py:572`) but unpinned: **S3-1**.
  - S4 "every stage inherits": **S4-5**. "carried as gaps": **S4-6**. "plan mode is read-only everywhere": **S4-9**.

## Cross-family debt

Every subject is Claude-authored. The documented cross-family lens is the read-only codex review, which is
usage-limited until **2026-10-03**. This Opus pass is the documented fallback, so the codex lens is still OWED for
`725c79c9`, `ea1eaa0b`, `28a124a3` and `102ee0c5`. Queue it when the limit resets. Same-family reviewers share blind
spots, and this pass does not discharge that.

## Bounds of this review

- Not reviewed for correctness: the specs `docs/specs/native-cli-installers-2026-09-30.md` and
  `docs/specs/research-watch-2026-09-30.md`, and the 14 verbatim agent reports on S4. These are intent documents and
  records; no code consumes them.
- The S4 raw tree was probed only by the Renovate extract, the betterleaks scan, and the manifest/graph checks.
- S1 through S3 had two earlier cold rounds each. This pass covered their final deltas plus live arms, not a full
  re-read.
- Memory was consulted (`handoff_claim_checker_review`, `doctor_docker_restore_review`, `graphify_bump_review_patterns`,
  `saved_workflow_js_review`, `mutation_harness`).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the four subjects; bulk issue/PR state oracle; residual-ticket search
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — `default.json` `ignorePaths` / automerge preset read for S4-1
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — release bodies byte-compared with receipts 0.9.66-0.9.73
- [jdx/mise](https://github.com/jdx/mise) — upstream docs (via the vendored S4 copy): config file names, `.miserc.toml`, `auto_env`
