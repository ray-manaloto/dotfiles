# Implementation-risk review: the 2026-09-22d program ("implement with minimal bugs")

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. The harness neutralised `<`/`>` in transit; restored.
> Harness banner on receipt: "subagent output matched instruction-shaped pattern(s):
> settings-json" (relayed, not acted on). Staged in scratchpad pending the next branch.

I stayed read-only: I edited no files and appended nothing to `findings.md` or `progress.md`, because the brief forbids edits. The only files I wrote are scratch probe outputs (`rv-*.json`, `rvw-*.json`, `rvp.py`, `rvm.py`) in the session scratchpad. The coordinator should save this report verbatim, for example as `docs/research/kb/reports/agents/implementation-risk-review-2026-09-22.md`.

**How I gathered evidence.**
- **AgentsView.** Semantic and hybrid search are down: the embeddings index is still building (9%), so every hybrid call failed. I fell back to full-text search: 17 searches across both repos, Claude and Codex, excluding this session. I then read message windows from 9 past sessions.
- **This session.** I read the user turns directly (`session messages b72c95e0… --role user`, #0-347). The rulings came from root `findings.md` lines 1936-1967, plus the Fable synthesis and the plugin-CLI report.
- **Graph.** `mise run graphify-health` returned rc=3, stale: the graph was built at 9a6ea68f and HEAD is 126c0ebf. All `file:line` references below were read directly from source.
- **Live probes.** I ran 6 on the host, each with a control; they are cited inline.

## 1-2. Likely failure modes per item, and the check that catches each

**A. claude-code 2.1.278 → 2.1.280 bump (the first PR)**
- **Comments silently dropped.** `schema-vendor-refresh` deletes the authored comment block. Issue #1205 is still OPEN, and the 09-18 bump recipe says to restore the block from `git show HEAD:schemas/sources.toml` (memory `project_session_2026-09-18.md:50-58`).
  - Catch: `git diff schemas/sources.toml` should show only the `version`, `source` and `sha256` lines. Then run `mise run schema-vendor-check`.
- **Drift across pin sites.** The version lives in four places: two regexes in `schemas/sources.toml`, `.claude/types/README.md:54`, and the `// Written by Claude Code` token in `python/verification/suites.toml`.
  - The token is still `2.1.277` while the pin is `2.1.278`. That is allowed while upstream's headers lag (`pin-parity.toml:84-105`), but it has to be re-checked every bump.
  - `pin-parity` catches a missed README bump; it was mutation-tested in codex:01a0a88c #455-481 @481 (rc=1 "DRIFT claude-code").
  - The suites token is NOT a pin-parity site, so only `mise run verify` catches it.
- **`mods/` is already answered.** The Fable synthesis lists "does `mods/` exist at 2.1.280?" as unverified (probe C6), but `schemas/sources.toml:52` already fetches `…/v2.1.278/mods/types/claude-code.d.ts`. So `mods/` existed at 2.1.278. The only thing left to check is the one v2.1.280 path, with CHANGELOG.md as the control.
- **Stale comment found.** `mise.toml:208-209` says the claude version is "recorded" in `[env]`, but there is no variable after that comment. `doctor.toml:258-260` repeats the claim. Fix or delete it in this PR, before the codex migration copies the pattern.

**B. KB dependencies + graphify unfork to upstream 0.9.65**
- **The last bump failed closed on the SDK contract.** The 0.9.57 bump hit a new keyword-only argument (`build_merge(ast_sources=…)`), and `graphify_sdk.py`'s pinned signature refused at `cli.py:142`. That blocked every `kb-setup` command. It also needed a re-derived `sdk_fingerprint_sha256` (`graphify_baseline.py:292`) and a new baseline snapshot (KB `graphify-out/memory/query_20260909_205125…`).
  - Budget for more than the pin moves. Eight releases (0.9.58-0.9.65) have to be checked against the contract.
  - Catch: `kb-setup` smoke plus `tests/test_graphify_baseline.py`. The fail arm is the old fingerprint.
- **The fork is wired in two places.** `pyproject.toml:303` `[tool.uv.sources] graphifyy = { git = …/ray-manaloto/graphify, rev = 3c9b930f }` and `pyproject.toml:32` `==0.9.57`. Also update `sources/graphify.manifest` and both `.graphify_version` stamps (still 0.9.57).
  - 12 tracked files carry `0.9.57`: `gates.py`, `graph.py`, `graphify_baseline.py`, `graphify_sdk.py`, two tests, `uv.lock`, the rule, and `CLAUDE.md`.
- **The currency engine fails closed.** It still probes `openai-cli` (`backend_probes`, `currency.toml:49`).
  - Delete `[tool.graphify.fork]` (`currency.toml:208-214`) and the `openai-cli` probe.
  - Also remove `openai-cli` from: KB `CLAUDE.md:66,124`, `.claude/rules/ai-cli-invocation.md:25-26`, `.claude/rules/do-not.md:63-69`, `kb-curator/SKILL.md:56` (both copies), and `tool-currency-and-native-first.md:86`.
  - Catch: `kb-setup currency check` rc=0, plus a KB-wide search for `openai-cli` returning 0 hits, run alongside a control search for `claude-cli` that must return hits.
- **Knock-on in dotfiles.** Dotfiles pins `kb-setup@e8fe42ae`, which pins graphifyy 0.9.57; only the loose override keeps dotfiles on 0.9.65 (`python/pyproject.toml:40,51-57`). After KB merges, bump that SHA in a separate dotfiles PR.
  - The override is the only thing governing the version. A 09-22 measurement showed the dependency line's `==` is ignored while an override is present (memory `project_session_2026-09-22.md:32-38`).
- **Retry trap.** Mise's lockfile forces `--no-build` on pipx tools (09-13d root cause). If `graphifyy[all]` fails to build under `update:all`, suspect the lockfile before suspecting the package.

**C. hk 2.0, one PR per repo**
- **Four version tokens per file.** Bumping only the `amends` line gives "Module version conflict: Expected … hk@1.57.0 … but got … hk@1.56.1" (KB `hk.pkl:336-339`).
  - Dotfiles sites: `hk.pkl:1,8,11`, `hk-common.pkl:17,18` (plus a comment at `:8`), `hk-image.pkl:11,14`, and `shared.toml:37`.
  - Pin-parity gap: `pin-parity.toml:78-81` captures only `hk@X`, not the `/download/vX/` segment of the same URL, so a half-edited URL passes. Add a second pattern.
  - KB has no pin-parity at all (`ls pin-parity.toml` fails in KB), so a partial KB bump has no gate.
- **Renovate is splitting hk right now.** PR #1090 bumps only the three pkl files to v2. PR #1093 bumps `shared.toml` hk 1.57.0→2.0.1 and bundles pinact 4.1.1→5.0.0 (a major) into the same "image-build inputs (major)" group. PR #1079 bumps the pkl files to 1.58.1 on their own.
  - This is exactly the 09-14 pattern: one tool, several pin sites, split across PRs (memory `project_session_2026-09-14-d.md`, "hk — 3 pkl URLs vs shared.toml, split across #1063/#1079").
  - Close all three and hand-roll one lockstep PR.
- **Base-image rebuild.** `shared.toml`, `hk-common.pkl` and `hk-image.pkl` are all inputs to the base-image hash (`Dockerfile:139,392-393`; `p2996_hash.py:362-373`). That means a cold CI base build of about 2.5 hours, and a mismatched image `hk` and pkl URL breaks in-image lint.
- **Formatter behaviour change.** `hk fix` no longer stages files (single source: exa). `mise run fmt` is bare `hk fix` (`mise.toml:1287-1289`), and the AGENTS.md doctrine says "`git add` BEFORE `mise run fmt`". Re-measure and update both in the same PR.
  - The hk 2 settings docs also say `--all` excludes untracked files when stashing is on (scratchpad `hk-settings.toml`). The re-staging rule in `clean-git-state.md` matters more after this.
- **Checks to run:** `mise run lint` rc=0 on both versions. Also run `hk test` and compare the count (KB measured 46→51 at the last bump). The fail arm is reverting one import token.

**D. Dotfiles deps to latest + Renovate `packageRules`**
- **Lock regeneration.** A whole-file relock is destructive (memory `feedback_mise_lock_whole_file_is_destructive`), and PR #1221, which refreshes the root `mise.lock` via lockFileMaintenance, is a whole-file relock. `mise run lock` reuses the version already locked (memory `feedback_mise_lock_reuses_locked_version`): delete the tool's `[[tools.X]]` block first. Anything in `shared.toml` must go through `lock-shared`: in the #790 run (e0d8343b #500-518 @510), typos, uv and yq each dropped from 11 locked platforms to 2. `lock-image` on macOS truncates without warning (4a066d43 #84-178 @100-106: rc=0 while `mise-runtime.lock` lost 6 lines and picked up unrelated drift).
  - Catch: the `mise_lock_integrity` lint step, plus a line-count and platform-count diff against the baseline before and after.
- **Mise itself has four pin sites.** PR #1131 bumps only `setup-mise/action.yml` to 2026.9.12, but the pin also lives in `Dockerfile` ARG, `schemas/sources.toml` and `shared.toml`. `pin-parity` catches this; the fix is a lockstep rule.
- **Missing `packageRules`.** Add lockstep groups for hk, mise and claude-code, spanning every pin site. `pin_parity`'s own error text asks for this (codex:01a0a88c @481).
  - Split majors out of `packageRules[0]` ("image-build inputs"). Otherwise pinact 5 and hk 2 ship together (PR #1093).
  - Why: `group:all` carried `separateMajorMinor:false` and had been holding sites together by accident (df158dd3 #293-532 @345; memory 09-14d).
  - Catch: `mise run renovate-dryrun -- --json` before and after, with the old config as the control arm (the method from df158dd3 @345-347).
- **Deprecation warning.** Mise 2026.9.12 warns `python.uv_venv_auto=true` is deprecated. That same stderr warning is what bricked the claude-doctor on 09-18 (memory `project_session_2026-09-18.md`). Fix it to `"source"` in this PR; it has been owed since 09-22c.

**E. Plugin CLI pins: node, gh, conda:coreutils, and `.firecrawl/`**
- **The `timeout` shim is broken, confirmed live.** My own `timeout 120 mise run graphify-health` returned rc=1 "No version is set for shim: timeout". This matches the plugin-CLI report's finding 1 (`agy-delegate.sh:204,434`).
- **Side effects of `conda:coreutils`.** It puts about 101 GNU commands ahead of BSD on the host, so re-run lint, pytest, verify and `hook-selfcheck` under the new PATH. It must be macOS-only (`os=["macos"]`): conda can't write linux lock URLs (jdx/mise#7700).
- **A root `node` pin changes CI.** The lint job runs `mise install --locked`, so it now also installs node. Use a scoped `mise run lock -- "node"`. Pin-parity against the image's `node = "latest"` (`mise-system.toml:22`) is advisory only.
- **Checks to run:** `bin/agy-doctor` rc=0 (the fail arm is today's rc=1). Run each npm CLI with `MISE_IGNORED_CONFIG_PATHS=~/.config/mise/config.toml`. For `.firecrawl/`, `git check-ignore .firecrawl/x` must return 0, with `.agent/x` as the control.

**F. pwf interim: 3.20.5, archive, root pin, PLANNING_DISABLED decision**
- **The wrong-plan shadowing can come back.** Any codex lane that runs pwf `init-session.sh` re-creates `.planning/<slug>/task_plan.md`, and that silently wins over root (memory 09-22c).
  - Today, `.planning/2026-09-21-graphify-0-9-65-skill-refresh/` still holds `task_plan.archived.md`. Move it to `.planning/.archive/`.
  - Guardrail: a doctor or handoff check that `.planning/*/task_plan.md` and `.planning/.active_plan` are both absent. `handoff-check` cannot see this today.
- **`sdlc_team.py` has no `PLANNING_DISABLED`.** It uses `shutil.which("codex")` (`:724`) and `Popen` (`:805,961`) without the variable. `codex_lane.py:136` sets `LANE_ENV_OVERRIDES` and the `.claude/agents/codex-*.md` briefs set it inline (`:103`). Past lanes already hit `PLAN TAMPERED` (codex:01a06312 #431-463 @433).
  - Test: `tests/test_sdlc_team.py` should assert the env the supervisor is launched with. The mutation is deleting the key.
- **Version skew.** The plugin cache already holds 3.20.5 alongside 3.17.2 (`ls ~/.claude/plugins/cache/planning-with-files/planning-with-files/`), and the attest wrapper picks the highest directory. Re-attest after the bump; the plan's digest has to match the version the hook actually runs.
- **`PWF_PLAN_ROOT`.** Put it in `.claude/settings.json` `env`, not a shell export (`.claude/CLAUDE.md` DAG pins).
  - Test from an `isolation: worktree` delegate. On the Codex route, P3 fails closed when the root is not a descendant of cwd, so an absolute main-checkout path either fails or lets a worktree write the main plan.
- **Hook timing.** The hook takes 11-12 s against a 10 s timeout, and the version bump doesn't change that. The fix is shrinking `task_plan.md` (90,441 bytes).

**G. KB source resync and manifests (claude-code as code, mattpocock, pwf)**
- **Same-name file collisions.** pwf ships 18 `SKILL.md` copies; the collision risk is unverified at 0.9.65 (probe C1). Count the distinct `source_file` values per path after extraction, with a uniquely named file as the control.
- **Code-only builds drop markdown.** `--code-only` indexes 0 `.md` nodes (G1), so a "full extraction" of skills repos is mostly docs.
  - State the expected node counts before running, so an empty result can't read as success.
- **Manifest mismatch.** The claude-code manifest still says kind=docs with "no product source to AST" (`sources/claude-code.manifest:2`). Update the comment and the `kind` together.

**H. Codex: move to the native installer, with the synced version in `schemas/sources.toml`**
- **Top risk: the native binary gets shadowed on PATH. Measured live.** `which -a codex` → `…/installs/npm-openai-codex/0.154.0/bin/codex`, then `…/mise/shims/codex`, then `~/.local/bin/codex`. Run from `/tmp`, the shim reports **0.155.1**, because the user-global `~/.config/mise/config.toml:144` pins `npm:@openai/codex` 0.155.1. `~/.local/bin/codex` reports **0.151.0**.
  - Control arm: the claude shim and `~/.local/bin/claude` both report 2.1.280, because nothing pins claude, so the shim falls through to the native binary.
  - So removing the dotfiles pin alone makes `codex` in dotfiles resolve to the user-global npm 0.155.1, not the native install. The same happens in KB until KB's `mise.toml:239` pin is removed.
  - The user-global line is Ray's file to change (memory `feedback_no_user_level_file_updates`). It must be removed and `mise reshim` run before the codex-doctor starts enforcing.
- **Code that still expects the mise pin.**
  - `codex_schema.py:25-26` runs `mise exec -- codex --version`.
  - `schema_vendor.py:119` reads the pin from `shared.toml` `npm:@openai/codex`, and `sources.toml:45` sets `pin_source` to that file.
  - `.claude/rules/ai-cli-invocation.md:16,19,106` uses `mise exec -- codex`, and that rule is in the cross-repo `rule-sync` set.
  - The KB `currency.toml:1855-1857` `[tool.codex] mise_key = "npm:@openai/codex"` row must change to a non-mise source, or the engine errors.
  - `hook_guard._CODEX_EXEC` (`:366`) already accepts the bare `codex exec` form, so there is no regex change there.
- **Unpinned schema URL.** The codex schema source (`sources.toml:44`, `learn.chatgpt.com/docs/config-schema.json`) has no version in it. Its sha256 can drift without the version changing, so the refresh must record both.
- **Image and CI.** Removing `shared.toml:44` changes the base hash, which means a cold CI build of about 2.5 hours. Both lockfiles must drop the entry: `.config/mise/mise.lock:531` via `lock-shared`, `.devcontainer/mise-system.lock:5209` via `lock-image`. The Dockerfile `install.sh --release <recorded>` needs a pinned checksum for the script (`no-stderr-suppression` applies), and the smoke tests must assert `codex --version` equals the recorded version.
- **Model outage history.** Global `~/.codex/config.toml:2` pins `model = "gpt-6-astra"`. On 09-10, an old CLI that couldn't reach the configured model returned HTTP 400 on every call and silently killed five lanes (memory `project_session_2026-09-10.md`).
  - Catch: after every version change, run one real `codex exec` with a trailing `-`. Never omit the `-`: that hung for 28 minutes last time.

**I. codex-doctor hooks: pause, update, restart, continue**
- **A false deny can lock the session out.** The 09-18 lockout came from a stderr warning being read as a version: every Bash, Edit and Write call was denied, and the verdict was cached for the whole session (`register.ts:43` `cachedReport`). #1202 is now CLOSED; clone its fix, not the pre-fix shape.
  - Rules: read stdout only. Anything unparseable is UNKNOWN, which warns and does not block. Get "latest" from `gh api releases/latest`, never the cached `version.json` (exa). Use `daemon version` JSON, never `codex doctor`, which reports healthy on skew (firecrawl, #32983).
  - Required: a table of prior versus new enforcement behaviour (the 09-18 ruling).
- **Updating the daemon kills other repos' lanes.** There is one daemon per `CODEX_HOME`, and KB runs codex lanes too (memory `feedback_scope_process_hunts_to_this_project`). A restart triggered from dotfiles kills KB's in-flight turns (#40969: SIGKILL after 60-300 s).
  - Define the "good checkpoint" as: no live `sdlc-team` settlement pending in either repo, and no codex process under either repo.
- **Don't implement the pause as a Stop hook.** A Stop hook forces extra turns (memory `feedback_stop_hooks_force_a_turn`: 4 forced continuations measured). Use SessionStart or PreToolUse.

**J. Desktop environment probe**
- **Dock-launched apps don't see shell env** (`do-not.md` #1). Exporting `CODEX_APP_SERVER_USE_LOCAL_DAEMON` in `.zshrc` won't reach a Dock-launched ChatGPT, and the probe will look like "env var ignored". Use `launchctl setenv` (or a LaunchAgent) plus a full app restart.
  - Arms from probe C2: an `lsof -U` connection on `app-server-control.sock` with no stdio child; with the variable unset, the stdio child is the control.

**K. Codex hook trust and PreToolUse deny parity**
- **Trust is per hook hash.** Every edit to `.codex/hooks.json`, and possibly to the script it runs, silently un-trusts that hook under `exec`. KB measured 3 trusted pre_tool_use hooks against 0 post_tool_use (093aab0c #578-596 @588-596).
  - Guardrail: a doctor check that counts this repo's `[hooks.state."…/.codex/hooks.json:<event>"]` entries against the configured events. The fail arm is adding an event; the probe must count keys only, never print values. Probe C4 settles whether trust hashes the script.
- **Blind spot.** `branch_guard` skips `apply_patch` (pwf-claude-codex report).

**L. Wrapper skills, only for unattended chains**
- **Wrappers go stale on plugin update.** The `@<installPath>` path is version-scoped (`…/1.2.3/`), so every plugin update breaks it.
  - The sync task must fail when the path is missing (the arm is pointing it at a bogus version), and `plugin-health` should run it.
  - Each wrapper adds to the skill-listing budget: check `/context` before and after.

## 3. Sequencing and PR boundaries

1. **KB first:** deps (no hk), then the graphify unfork (SDK fingerprint and baseline in the same PR), then hk 2.0. Unfork and hk must not share a PR: they fail the same gates for different reasons.
2. **Dotfiles, no base rebuild:** claude-code 2.1.280, then the pwf interim (settings `env`, archive, `sdlc_team` env plus test), then plugin CLIs (root `mise.toml` only; not image inputs). Also consider a separate `kb-setup` SHA bump after KB's unfork merges.
3. **Dotfiles, base rebuild (~2.5 h each):**
   - hk 2.0 lockstep: shared.toml plus the three pkl files, with pinact 5 split out.
   - Codex removal: shared.toml, both lockfiles, Dockerfile installer.
   - Never put two base-rebuild PRs in flight at once; each invalidates the other's cache hash. Do not bundle hk with codex.
   - Before opening either PR: close or supersede Renovate #1090, #1093 and #1079, and merge the new `packageRules` first. Otherwise Renovate re-splits the bump within the hour.
4. **Operator steps before the codex PR:** Ray removes user-global `:144`; remove the KB `mise.toml:239` pin; `mise reshim`; run `install.sh` with `CODEX_NON_INTERACTIVE=1` after removing the pin (Fable CHANGE 2). The installer appends a PATH block to `.zshrc`/`.zprofile`, which chezmoi manages, so chezmoi will revert it or show drift. Put the change in the chezmoi source instead.
5. **Last:** the codex-doctor (after D1), hook parity (after C3/C4), and wrappers.

**Cross-repo gate.** `rule-sync` matches rule files by name (`rule_sync.py:112`), and `ai-cli-invocation`/`do-not` are in the shared set. Adding a shared plugin such as pwf to `rule-sync.toml` before KB carries it turns `main` red (`rule-sync.toml` header "THE ORDER IS LOAD-BEARING").

## 4. Missing items nobody listed

- **`pin-parity.toml`:**
  - A `[tools.codex]` entry covering the `sources.toml` version, the Dockerfile `--release` value, and `doctor.toml` if it records one. The codex-0156 report notes `pin_source` has no target after the pin is removed.
  - An hk `download/v` pattern.
- **`doctor.toml`:** a `[codex]` section with `expected_install_method = "native"`, cloned from `:243-272`, with a matching `pin-parity.toml` description stanza. The existing `[codex]` (`:273`) covers only schema currency.
- **`schema_vendor._PIN_RESOLVERS["codex"]`:** a new resolver plus tests. Also `codex_schema.py`, `tests/test_hook_guard.py:150-195` (fixtures in the `mise exec` form), and `tests/test_sdlc_team.py`.
- **Codex agent briefs:** the `.claude/agents/codex-sol-*.md` briefs use a bare `codex exec`. After any edit, run `mise run codex-lane-mirror` so the astra copies match.
- **Rules and docs:** `ai-cli-invocation.md` plus its evidence file, `.claude/CLAUDE.md` (the codex lane description), AGENTS.md "Validate before committing"/fmt, the `pin-parity` and `lock-shared` skills' codex mentions, and `mise.toml:119-126`'s codex rationale comment. Also the stale `mise.toml:208-209`/`doctor.toml:258-260` claim that `[env]` records a version.
- **KB:** `currency.toml` graphify fork block and `[tool.codex]` row; the `openai-cli` doctrine in 6 files; `.graphify_version` stamps; `sources/graphify.manifest`.
- **`suites.toml` contracts** that assert the literal `npm:@openai/codex` or `hk@1.57.0`. Search with a control term before editing.
- **`goal-history.md`:** append an iteration for the codex authority change, which reverses the 09-16 exact-pin ruling.
- **Renovate:** disable lockFileMaintenance for `mise.lock` (PR #1221), or gate it on `mise_lock_integrity`.

## 5. Suggested new guardrails

1. **`codex-resolution` doctor check.** Assert `shutil.which("codex")` resolves to the native path and that its `--version` equals the recorded version. Arm it with today's live state, where the shim wins at 0.155.1: that state must fail.
2. **Pin-parity for KB.** Port it, or add a `kb-setup` equivalent, covering hk tokens and graphify stamps.
3. **Renovate lockstep check.** `pin-parity` should also check that each multi-site tool has a matching `packageRules` group. Otherwise Renovate re-splits hk and mise (live: PRs #1090, #1093, #1131).
4. **Lint step: no `.planning/*/task_plan.md` and no `.active_plan`.** The mutation is recreating the lane directory.
5. **Codex hook-trust counter** in the doctor, counting keys only (secrets rule §8).
6. **Stdout-only rule for every doctor oracle.** Add a shared helper plus a test that injects a mise stderr warning; a result other than UNKNOWN fails.
7. **Wrapper `@path` existence check** in `plugin-health`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): source files, rules, `pin-parity.toml`, `renovate.json`, open Renovate PRs #1090/#1093/#1079/#1131/#1221, issues #1202/#1205/#1110/#1054/#1165
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): `currency.toml`, `pyproject.toml`, `hk.pkl`, manifests, `openai-cli` doctrine files, graphify memory
- [ray-manaloto/graphify](https://github.com/ray-manaloto/graphify): the fork's `uv` source pin (read via KB `pyproject.toml:303` only)
