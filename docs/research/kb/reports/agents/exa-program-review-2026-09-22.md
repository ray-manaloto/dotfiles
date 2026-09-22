# Exa research sweep of program items a–e (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. HTML entities introduced in transit restored.

I ran the searches myself instead of sending them to haiku subagents. The Exa skill suggests subagents, but my brief says not to re-delegate. That came to 15 Exa searches and 1 Exa fetch, and I checked every load-bearing hit with `gh api` or a local probe. I edited no repo files, so the only incremental notes are in the scratchpad (`exa-program-notes.md`). You need to save this report under `docs/research/kb/reports/agents/`.

## a. knowledge-base graphify corpus — **changes the plan: the upgrade is a fork rebase, not a pin bump**

- **Upstream has no `openai-cli` backend.** The latest upstream release is v0.9.65, dated 2026-09-20 (checked with `gh api` and PyPI). I grepped its `graphify/llm.py`: `openai-cli` 0 hits and `codex` 0 hits, against 26 hits for `claude-cli` as the control. PR [#3073](https://github.com/Graphify-Labs/graphify/pull/3073), which adds `openai-cli`, is still `open` and not merged (last updated 2026-08-25).
  - The KB comment in `currency.toml` says losing this backend "can fall back to the metered OpenAI API — a spending regression".
  - So "upgrade from the 0.9.57 fork to upstream 0.9.65" really means one of two things: rebase the fork patch onto 0.9.65, or drop `openai-cli` and use `claude-cli` only.
- **0.9.58–0.9.65 help the new markdown-heavy sources.** Release notes were fetched with `gh api`. Three changes matter for pwf and mattpocock/skills:
  - [v0.9.62](https://github.com/Graphify-Labs/graphify/releases/tag/v0.9.62): an inline code span in Markdown now emits a `references` edge, but only when exactly one callable matches.
  - [v0.9.64](https://github.com/Graphify-Labs/graphify/releases/tag/v0.9.64): incremental `update` reconciles Markdown links across `.md`, `.mdx`, `.qmd` and `.skill`, and `export` now detects a stale sidecar.
  - [v0.9.63](https://github.com/Graphify-Labs/graphify/releases/tag/v0.9.63): every edge endpoint in `graph.json` is now a declared node.
- **Native features that cover parts of the plan:** [the README](https://github.com/Graphify-Labs/graphify) documents `graphify clone <url>`, `merge-graphs`, `global add`, and `extract --global --as` for multi-repo corpora.
- **A community trap:** [terrylica/cc-skills](https://github.com/terrylica/cc-skills/blob/main/plugins/graphify-tools/skills/build-graph/SKILL.md) reports that a corpus with many same-named `SKILL.md` files silently drops colliding nodes. Its advice is to extract per subfolder, then `merge-graphs`. This bites the pwf mirror copies and mattpocock/skills directly. **Unverified at 0.9.65.**
- **Nothing found** that replaces `kb-update`'s 99-source resync.

## b. Codex currency — **changes the plan: mise already ships a native backend, the daemon updater is dangerous, and the Desktop env var is broken right now**

- **mise already has a native, non-npm codex backend.** `mise registry codex` lists `aqua:openai/codex` first and `npm:@openai/codex` second (probed locally). The aqua backend installs a checksum-verified GitHub-release binary and records the version in `mise.lock`. That covers "native binary" and "synced version recorded in a repo file" with no custom installer code.
  - One gap: the app-server daemon only runs the standalone layout under `~/.codex/packages/standalone/current` ([daemon README](https://github.com/openai/codex/blob/main/codex-rs/app-server-daemon/README.md)). An aqua binary cannot serve it.
- **The standalone installer can pin.** [`install.sh`](https://github.com/openai/codex/blob/main/scripts/install/install.sh) takes `--release VERSION` or `CODEX_RELEASE`, plus `CODEX_NON_INTERACTIVE` (read from its `--help` text).
  - So "match the mise pin exactly" (the ruling recorded in the codex-daemon-history report) is achievable by passing the same version to both.
  - Side effect: the installer appends a PATH block to `~/.zprofile` or `~/.zshrc` when its bin dir is not on PATH, or when it detects a conflicting npm/bun codex (lines 597–628). Today's npm pin would trigger that.
- **The daemon's auto-updater is hazardous.** `bootstrap` starts an updater that runs `install.sh` every hour, always to *latest*, so it would overrule any pin.
  - [#40969](https://github.com/openai/codex/issues/40969), OPEN: an update SIGKILLs in-flight turns after a 60-second drain, and auto-update cannot be turned off. The `autoUpdateEnabled` status field is a hardcoded literal.
  - [#34692](https://github.com/openai/codex/issues/34692), OPEN: security objection to piping a remote script into `sh`.
  - [#32785](https://github.com/openai/codex/issues/32785), OPEN: an inherited `CODEX_INSTALL_DIR` can corrupt the managed install.
  - Recommendation: use `start`/`restart`, not `bootstrap`, and let the doctor drive updates.
- **`CODEX_APP_SERVER_USE_LOCAL_DAEMON=1` is broken on current Desktop.**
  - [#41112](https://github.com/openai/codex/issues/41112) and [#41014](https://github.com/openai/codex/issues/41014), both OPEN: Desktop 26.820.60940 ignores the variable. The bundled `codex_app` MCP override makes `configOverrides` non-empty, so Desktop starts a private stdio app-server anyway.
  - [#37568](https://github.com/openai/codex/issues/37568), OPEN: a stale daemon can stop Desktop from launching at all.
  - Desktop's bundled codex only moves when the app itself updates. **Plan item b's Desktop path is blocked upstream.**
- **`codex update` works, but has no report-only mode.** It arrived in v0.128.0 and detects the install channel ([#9274](https://github.com/openai/codex/issues/9274)). I probed pinned 0.154.0: `codex update --help` has no `--check` flag (0 hits, against 1 hit for `--config` as the control). A [blog's](https://codex.danielvaughan.com/2026/05/08/codex-cli-codex-update-self-update-command/) `codex update --check` claim is **false** at this version.
  - The TUI caches the latest version in `~/.codex/version.json` ([updates.rs](https://github.com/openai/codex/blob/main/codex-rs/tui/src/updates.rs), 20-hour refresh). On this host that file was last modified Sep 9, because only the TUI refreshes it. It is not a reliable doctor input.
  - Querying GitHub `releases/latest` is still needed; that endpoint currently returns rust-v0.155.1.

## c. pwf shared plan, "A-enforced" — **changes the plan: a sandbox rule beats a Codex PreToolUse deny**

- **Existing tool that replaces the planned Codex guard:** Codex [permission profiles](https://developers.openai.com/codex/permissions) support `[permissions.<p>.filesystem.":workspace_roots"] "task_plan.md" = "read"`. The OS sandbox enforces that, so shell writes are blocked too. `extends = ":workspace"` keeps the built-in `.git`/`.codex` protections.
  - Why it's better: in [#27833](https://github.com/openai/codex/issues/27833) a PreToolUse deny on `apply_patch` *was* enforced at 0.147, but the model then rewrote the file with `perl -pi` through the shell. A deny on edit tools alone is walked around.
  - **Caveats:**
    - Profiles do not combine with `sandbox_mode` or `-s`. `sdlc_team`'s `-s workspace-write` would have to switch to `default_permissions`.
    - Full-access implementer lanes cannot carve out a deny ([#31929](https://github.com/openai/codex/issues/31929), OPEN).
    - **Unverified:** that a single-file `read` entry works on macOS Seatbelt. The docs show directory and glob examples.
- **Codex hook facts** ([hooks docs](https://developers.openai.com/codex/hooks)):
  - A deny requires `permissionDecision: "deny"` with a non-empty reason. `ask`, extra keys, or a malformed reply is logged as `Failed` and the tool call **proceeds** ([#27833](https://github.com/openai/codex/issues/27833) thread).
  - `spawn_agent` also matches `Agent`.
  - Untrusted hooks are skipped **silently** in `exec`. With persisted trust, `exec` dispatches them at 0.147 ([#32491](https://github.com/openai/codex/issues/32491)).
  - PreToolUse `ask` is unsupported ([#28437](https://github.com/openai/codex/issues/28437), OPEN).
- **pwf's own docs agree.** Its [SKILL.md](https://github.com/OthmanAdi/planning-with-files/blob/master/skills/planning-with-files/SKILL.md) describes parallel-plan isolation (`PLAN_ID`, `PWF_PLAN_ROOT`). It lists no PreToolUse deny, which matches the pwf-claude-codex report's finding that the parallel-write guard is advisory only.
  - Sibling project [OthmanAdi/planning-with-teams](https://github.com/OthmanAdi/planning-with-teams/blob/master/README.md) targets Claude-only Agent Teams, so it does not cover the Codex lanes.
- On the Claude side, the planned `agent_id`-based PreToolUse deny remains the correct native mechanism. No change there.

## d. Wrapper skills over hidden plugin skills — **the mechanism is supported, but the plan conflicts with a standing rule of yours**

- **The mechanism works.** The docs (`$CC/skills.md:247`) say a local skill "attach[es] the files that `@` references name", while synced skills in other sessions receive them as literal text. So a project wrapper whose body is `@<plugin SKILL.md path>` is supported.
  - Caveat: the plugin cache path contains the plugin version, so the sync task stays necessary. `${CLAUDE_PLUGIN_ROOT}` is only substituted inside plugin skills (docs), so it cannot stand in for the path in a project wrapper. **Unverified:** whether `@` paths resolve relative to the skill file.
- **The native routes are confirmed closed.** The [docs](https://code.claude.com/docs/en/skills) say "Plugin skills are not affected by `skillOverrides`". [#22345](https://github.com/anthropics/claude-code/issues/22345) (OPEN) quotes the binary short-circuiting `source === "plugin"` to `"on"`. [#78523](https://github.com/anthropics/claude-code/issues/78523) and [#82237](https://github.com/anthropics/claude-code/issues/82237) are also OPEN; the latter reports coordinator mode hiding these skills entirely.
- **An existing tool replaces the custom sync task:** `npx skills add mattpocock/skills` plus `npx skills update` ([README](https://github.com/mattpocock/skills/blob/6acc160e/README.md)) installs editable copies. Its downside is that an update restores `disable-model-invocation: true`.
- **Intent conflict. This needs your decision before it is built.**
  - The changelog entry at `$CC/changelog.md:1565` says Claude is now "told to ask you to run the skill instead of replicating its workflow".
  - mattpocock's design treats these as user-invoked orchestrators. A Codex mirror, `agents/openai.yaml` `allow_implicit_invocation: false`, enforces the same thing ([#693](https://github.com/mattpocock/skills/issues/693)).
  - Your own memory `feedback_protocol_verbs_are_user_invoked_only` says "STOP and name the command; never hand-roll".

## e. Everything at latest, including hk 2.0 — **mostly native tools already cover it; hk 2.0 changes `mise run fmt`**

- **hk.** Latest is v2.0.1 (2026-09-15). The repo pins 1.57.0 in `shared.toml`, and the `hk.pkl` URLs in both repos are on 1.57.0. The Renovate PR for v2 is dotfiles#1090, still OPEN. From the [v2.0.0 notes](https://newreleases.io/project/github/jdx/hk/release/v2.0.0):
  - **`hk fix` no longer stages.** `mise run fmt` is `hk fix` (`mise.toml:1287-1289`), so the AGENTS.md "git add BEFORE `mise run fmt`" doctrine changes meaning.
  - Two items are already done: `byte_order_marker` is migrated (`hk-common.pkl:118`) and `HK_PKL_BACKEND` is dropped.
  - The optional top-level `steps` map can shrink `hk.pkl`.
- **hk still has no timeout.** `settings.toml` on main has 0 hits for `timeout`, against 2 for `fail_fast` as the control. The custom `lint.py` wrapper stays justified.
  - Separately, hk [#1099](https://github.com/jdx/hk/pull/1099) (merged 2026-07-22) fixed the `depends` + `fail_fast=false` hang. The `no_hk_depends` ban may be retirable (not probed).
- **uv has a native bump command.** `uv upgrade` exists as a **hidden** command, added in PR [#19678](https://github.com/astral-sh/uv/pull/19678) and touched again in [0.12.16](https://github.com/astral-sh/uv/releases/tag/0.12.16).
  - My first probe, the `uv help` listing, did not show it. `uv upgrade --help` returned rc=0 on local uv 0.12.13, so the first probe was blind.
  - It removes upper and equality bounds. The first version was read-only; **whether it writes `pyproject.toml` at 0.12.17 is unverified**. The main tracking issue [#6794](https://github.com/astral-sh/uv/issues/6794) is still OPEN.
  - Stable route today: `uv lock --upgrade`, plus Renovate or the third-party [uv-bump](https://github.com/zundertj/uv-bump/).
- **mise has a native bump.** [`mise upgrade --bump`](https://mise.jdx.dev/cli/upgrade.html) rewrites `mise.toml` pins and supports `--minimum-release-age`. Given the memory `feedback_mise_lock_reuses_locked_version`, run it scoped per tool.

## Unverified claims (collected)
- A single-file `read` entry in a Codex permission profile.
- Whether `@` paths in a skill resolve relative to the skill file.
- Whether `uv upgrade` writes files at 0.12.17.
- The graphify same-name collision at 0.9.65.
- Whether `no_hk_depends` can be retired.

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — releases 0.9.58–0.9.65, PR #3073, `llm.py` backend grep
- [openai/codex](https://github.com/openai/codex) — install.sh, daemon README and update loop, updates.rs, hooks docs, issues #40969 #34692 #32785 #41112 #41014 #37568 #27833 #32491 #28437 #31929 #9274
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — SKILL.md, README, Codex and parallel-plan docs
- [OthmanAdi/planning-with-teams](https://github.com/OthmanAdi/planning-with-teams) — sibling multi-agent skill
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issues #22345 #78523 #43875 #82237, skills docs
- [mattpocock/skills](https://github.com/mattpocock/skills) — invocation model, README, issue #693
- [jdx/hk](https://github.com/jdx/hk) — v2.0.0/v2.0.1 notes, settings.toml, PR #1099
- [jdx/mise](https://github.com/jdx/mise) — `upgrade --bump` docs and source
- [astral-sh/uv](https://github.com/astral-sh/uv) — `uv upgrade` PRs #19678 and #21776, issues #6794 and #6692, release notes
- [zundertj/uv-bump](https://github.com/zundertj/uv-bump) — third-party pyproject bumper
- [terrylica/cc-skills](https://github.com/terrylica/cc-skills) — graphify same-name collision note
