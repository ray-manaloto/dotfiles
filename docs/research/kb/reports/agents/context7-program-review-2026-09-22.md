# Context7 research: program items a–e (2026-09-22)

> **CORRECTION (session review, 2026-09-22d): the `LifecycleOutput` field names quoted in §b are Rust names; the emitted JSON keys are camelCase (`cliVersion`, `appServerVersion`, `managedCodexVersion`, `managedCodexPath`).**

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. Raw query outputs: session scratchpad `c7/`
> (`lib-*.txt`, `q-*.txt`). HTML entities introduced in transit restored.

The brief's premises mostly hold, but each item needs changes. Context7 could not verify three things: graphify 0.9.65, hk 2.0, and the ChatGPT Desktop environment variable. This lane was read-only, so I wrote nothing to the repo, `findings.md` or `progress.md`.

The only external doc source was the `ctx7` CLI, version 0.5.11. Library IDs I resolved and queried: `/openai/codex` (indexed at main; tags include rust-v0.155.1 and rust-v0.154.0), `/websites/code_claude`, `/anthropics/claude-code` (v2.1.278), `/graphify-labs/graphify` (branch `v8`, no version tags), `/othmanadi/planning-with-files`, `/jdx/hk`, `/websites/hk_jdx_dev`, `/jdx/mise`, `/mattpocock/skills`, `/vercel-labs/skills` and `/astral-sh/uv`.

## a. knowledge-base graphify corpus — changes (one native option; the 0.9.65 part is UNVERIFIED)

- **0.9.65 cannot be verified through Context7.** The graphify index is the `v8` branch with no version tags. A CHANGELOG query returned only 0.9.17 and 0.9.22 entries (`q-gr-changelog.txt`, `q-gr-latestcl.txt`). The query "CHANGELOG 0.9.58 … 0.9.62 built_at_commit" returned rc=1, "No documentation matched". Control: the same CHANGELOG file does answer for 0.9.17 and 0.9.22, so the file is indexed but the new entries are not. Every 0.9.58–0.9.65 claim must come from the installed source or release notes, which is the method of the existing `graphify-features` report.
- **Native features that could replace custom KB code** (source: `graphify-labs/graphify` README.md and `skills/agents/references/github-and-merge.md`, `v8`):
  - `graphify clone <url>` checks out to `~/.graphify/repos/<owner>/<repo>`.
  - `graphify merge-graphs a.json b.json --out …` merges graphs.
  - `graphify global add <graph.json> --as <tag>` plus `global list`, `global remove` and `global path`. `build.py:prefix_graph_for_global` namespaces node IDs as `repo_tag::` and offsets community IDs (#3014).

  If the KB's 99-source resync (kb-update) re-implements per-repo graph building and merging, these are the built-in path. Caveat: no Context7 snippet shows `clone` accepting a `--ref` or SHA. The query "clone --branch --ref commit pin" returned only the unpinned form, so clone probably cannot carry the KB's SHA pins (UNVERIFIED).
- **Deep extraction flags are documented:**
  - `graphify extract … --mode deep` gives richer semantic extraction.
  - `--backend claude-cli` routes through the Claude subscription with no API key, which fits the KB's Claude-only rule.
  - Also: `--no-gitignore`, `--dedup-llm`, `--force` (overwrite even when the new graph shrinks), `--global --as <tag>`, `update --no-cluster`, `check-update`.
- **Reflect:** `graphify save-result --outcome useful|dead_end|corrected`, `graphify reflect --if-stale` (a no-op when LESSONS.md is newer), and `reflect --graph …`, which writes the `.graphify_learning.json` overlay behind the "Lesson:" hints in `explain`/`query`.
- **Exports:** `--wiki`, Obsidian vault, GraphML, Neo4j, HTML, and `graphify export callflow-html`.
- I did not verify the `anthropics/claude-code` `mods/` directory. Context7's library for that repo is doc/changelog-shaped, and no query surfaced `mods/`.

## b. Codex currency — changes (the plan conflicts with the native auto-updater)

- **Native install and update exist.**
  - Install: `curl -fsSL https://chatgpt.com/codex/install.sh | sh` (`openai/codex` README.md).
  - `codex update` detects the install method (`install-context/src/lib.rs` `InstallContext::current()`: Standalone, Npm, Bun, Pnpm, VitePlus, Brew). It maps that method to an action (`tui/src/update_action.rs`).
    - Standalone re-runs `install.sh` with `CODEX_NON_INTERACTIVE=1`.
    - **An npm install runs `npm install -g @openai/codex`**, which is outside mise's control. That is a concrete reason to leave `npm:@openai/codex`.
- **mise's own backend policy agrees.** jdx/mise `CLAUDE.md` puts `npm:` in "Tier 4 — extremely high bar … silently bind to whichever node was on PATH". The preferred order is `packslip:`, then `aqua:`/`github:`.
  - I could not find out whether mise's registry has a non-npm codex entry. Both the codex query and the control ("claude" registry entry) returned 0 hits, so the probe cannot discriminate. The mise registry is not answerable through Context7.
- **Conflict with "record the synced version in a repo file" (a pin).**
  - `app-server-daemon/src/update_loop.rs` runs a detached updater. It checks 5 minutes after start and then hourly, re-running the installer and restarting the app-server.
  - README: `CODEX_HOME/app-server-daemon/settings.json` accepts `{"updater":{"autoUpdateEnabled":false,"updateIntervalMinutes":N}}`, applied by `daemon restart`.
  - `daemon update` "selects the latest stable release, even with automatic updates disabled", and "returns pinned or local managed packages to production update eligibility".

  So either accept auto-update and let the repo file record what was observed, or disable the updater. Otherwise the recorded version drifts within an hour.
- **Native version reporting replaces custom scraping.** Every `codex app-server daemon …` command "writes exactly one JSON object to stdout". `LifecycleOutput` has `status`, `backend`, `managed_codex_path`, `managed_codex_version`, `cli_version` and `app_server_version` (`app-server-daemon/src/lib.rs`).
  - Caveat: `daemon version` **errors** (it does not return `notRunning`) when the socket is unreachable.
  - The codex-doctor should parse this JSON rather than write its own detection.
- **The startup update check is native.** `check_for_update_on_startup` defaults to true (`config/src/config_toml.rs`), with the note "Set to false only if your Codex updates are centrally managed."
  - The check is advisory, a TUI popup. The "block lanes when behind" part still needs custom code, but that code can be small.
- **Hook trust affects the codex-doctor hook, and item c.**
  - A project `.codex/hooks.json` hook runs only when it is enabled **and** its trust status is Trusted or Managed, or trust is bypassed (`hooks/src/engine/discovery.rs`). Trust is a SHA-256 of the normalized event+matcher+handler, stored as `hooks.state.<key>.trusted_hash`.
  - The TUI prompts to trust new or changed hooks. "Continue without trusting" means the hooks do not run (`tui/src/startup_hooks_review.rs`).
  - Managed layers (System, MDM, requirements.toml `[hooks]`) are always `is_managed`. `allow_managed_hooks_only` is valid only in requirements.toml.
  - **Implication:** any edit to a project hook changes its hash and needs re-trust. `codex exec` lanes have no prompt, so an untrusted gate is silently absent. That is the fail-open shape this repo already bans. A hook that must enforce should be delivered as managed, or its trust state should be checked by the doctor. The exact requirements.toml path is UNVERIFIED.
- **`CODEX_APP_SERVER_USE_LOCAL_DAEMON`: no Context7 coverage.** 0 hits, against a control of 18 hits for `CODEX_HOME` on the same library. The variable comes from the closed-source ChatGPT Desktop bundle; the existing `codex-desktop-settings` report found it in the Desktop binary.
  - For the CLI, Context7 shows the TUI auto-probes `CODEX_HOME/app-server-control/app-server-control.sock` and uses `LocalDaemon` when it is reachable, otherwise `Embedded` (`tui/src/lib.rs`). No environment variable is needed there.
- **The Claude Code comparison holds.** The native installer has `autoUpdatesChannel` stable/latest, `DISABLE_AUTOUPDATER`, `claude update` and `minimumVersion` (code.claude.com setup and settings-reference).

## c. pwf shared plan ("A-enforced") — changes (much of it is native; the guard needs Codex-specific details)

- **Native in planning-with-files** (README.md, SKILL.md, `docs/long-running-agent-tasks.md`, `docs/attestation-locking.md`):
  - **Per-agent run ledger.** Workers append JSONL to agent-specific ledgers, which are summarized into a fixed-shape block. "An orchestrator manages the task plan, while individual workers maintain their own event ledgers." This is the "codex workers write pwf ledger" half of A-enforced, and it is upstream design, not custom work.
  - **Plan isolation.** `init-session.sh`, `set-active-plan.sh`, `PLAN_ID`, `PWF_PLAN_ROOT` and session attachment.
  - **Parallel-write guard** (v3.10.0, on by default). It is **advisory only**: it warns on a progress decrease and does not block.
  - **Attestation.** A SHA-256 lock on `task_plan.md`; hooks "refuse to inject" when the file diverges. This detects a worker writing the plan without denying the write.
  - **`PLANNING_DISABLED=1`** (docs/codex.md), already used by `codex_lane`.
  - **Codex install** uses `.agents/skills/` plus `.codex/hooks.json`. docs/codex.md warns against installing hooks both workspace and global, which doubles messages.
- **Codex PreToolUse deny, confirmed from source:**
  - The shape is `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}`. **A non-empty reason is required.** `ask` is rejected as unsupported (`hooks/src/engine/output_parser.rs`, `events/pre_tool_use.rs`).
  - File edits are `apply_patch`. Matchers accept the aliases **`Write`/`Edit`** (`core/src/tools/hook_names.rs`), but stdin carries `tool_name: "apply_patch"` and `tool_input: {command: <patch text>}`. The guard must therefore parse `*** Update/Add File:` headers; there is no `file_path` field.
  - Stdin includes `agent_id` and `agent_type` (`pre_tool_use.rs`), which lets a guard tell the coordinator from its workers.
- **Events at Codex main:** PreToolUse, PermissionRequest, PostToolUse, SessionStart, SessionEnd, SubagentStart/Stop, PreCompact/PostCompact, UserPromptSubmit, Stop, Interrupt.
  - `SubagentStart` injects context only and cannot block, the same as Claude (code.claude.com hooks).
  - Stop and UserPromptSubmit ignore matchers.
  - This list comes from **main**. Whether the pinned 0.154/0.155 has every event is UNVERIFIED here.
- **A gap on both vendors:** a shell write (`>` or `sed -i` on `task_plan.md`) goes around a Write/Edit/apply_patch deny. Attestation is the native backstop for that case.
- The Codex trust gate from item b applies: an untrusted deny guard does not run under `codex exec`.

## d. Plugin skills made model-invocable through wrappers — changes (high risk; the key mechanism is UNVERIFIED)

- **Confirmed:** "Overrides don't apply to plugin skills, which you manage through `/plugin`" (code.claude.com settings-reference and skills). The brief's measurement matches the docs.
- **`@<path>` in SKILL.md is not documented for skills.**
  - `@path` expansion is documented for CLAUDE.md imports (code.claude.com memory: relative to the file, 4 hops, external paths need approval).
  - It is also documented for **command** files. `anthropics/claude-code` `plugins/plugin-dev/skills/command-development/README.md` says "`@path/to/file` – Include file contents", and the CHANGELOG says commands and skills were "merged … no change in behavior".
  - The skills page itself prescribes markdown links, which Claude reads when needed, and `` !`cmd` `` dynamic injection. That injection runs "before the skill content is sent to Claude", in one pass, and only at line start or after whitespace.
  - **Whether `@` expands when the model invokes the wrapper through the Skill tool is UNVERIFIED** and needs a real arm: a wrapper that `@`-references a file containing a fresh sentinel, invoked by the model.
  - The documented fallback is a `` !`cat <path>` `` line. But `${CLAUDE_PLUGIN_ROOT}` is substituted **only in plugin skills**, so a project wrapper would need the versioned cache path. `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` do work in project skills.
- **This goes against documented intent, and Ray needs to rule on it.**
  - code.claude.com skills: when Claude tries a `disable-model-invocation` skill, "Claude Code blocks the call and instructs it not to reproduce the … steps another way."
  - mattpocock/skills `docs/engineering/implement.md`: it "ships with `disable-model-invocation: true`, so no other skill can call it either". `engineering/README.md` lists to-spec, to-tickets and implement as **User-invoked**.
  - The wrapper exists to do what both sources say not to do. That matches the repo's own memory, "Protocol verbs are USER-INVOKED only".
- **Built-in alternatives to weigh first:**
  1. Vendor the three skills as **project** skills with the frontmatter flag flipped. The `vercel-labs/skills` CLI (`skills add`, `skills check`, `skills update`, `skills-lock.json`) is an existing sync tool that could replace a custom sync task. Run it through a mise-pinned binary, not `npx`.
  2. Subagent `skills:` frontmatter "fully preloads" the listed skills into the subagent (code.claude.com features-overview). Whether that honors `disable-model-invocation` for plugin skills is UNVERIFIED.
  3. Stacked user invocation, `/to-spec /to-tickets …` (up to 5 skills, v2.1.199+).

  UNVERIFIED as well: whether `skillOverrides: "on"` beats a project skill's frontmatter `disable-model-invocation: true`. The docs only say overrides work "instead of the skill's own frontmatter".

## e. Every tool at latest — changes (native mise commands; hk 2.0 is UNVERIFIED)

- **Native "am I current" gates** (jdx/mise `docs/cli/upgrade.md`, `docs/cli/lock.md`):
  - `mise upgrade --bump` moves to the latest version and rewrites `mise.toml`.
  - **`--dry-run-code`** exits 1 when anything is outdated.
  - `mise lock --bump --dry-run --json` lists available updates as JSON.

  These may replace parts of custom currency scripts; I have not checked this against `kb_setup.currency`.
- **`mise lock` "preserves existing matching locked versions unless `--bump`".** This confirms the memory that `lock` reuses the locked version. `--bump` only re-resolves **fuzzy** selectors, so exact pins still need `mise upgrade --bump` or Renovate.
- **`mise lock --platform linux-x64`** is native cross-platform locking. It might reduce the need for `lock-shared`'s routing into the devcontainer. UNVERIFIED: memory says macOS resolves a different asset for at least one tool, so this needs an arm.
- **Other mise facts:**
  - `--minimum-release-age` exists on both `upgrade` and `lock`, and `install_before` is a deprecated alias.
  - The npm backend has a v2 lockfile of transitive deps plus `mise install --locked`.
- **hk 2.0 is not in Context7.**
  - The index stops at **1.56.1 (2026-08-23)**, while the repo pins 1.57.0. A "v2.0.0 release removed deprecated" query returned rc=1.
  - Control: the same library returned the 1.56.0/1.56.1 CHANGELOG, so the index is readable but stale.
  - What does apply to the bump: `hk.pkl` amends/import URLs are pinned to the exact binary version, and the embedded package preloads **only** when the URL matches (`src/config.rs`). All three pkl files must change in lockstep with the binary, which is a pin-parity case.
  - A "step timeout" query returned timing docs only, so hk still shows no timeout and `lint.py`'s wrapper remains justified.
- **uv:** `uv add "<spec>" --upgrade-package <name>` and `uv add --bounds lower|major|minor|exact` (astral-sh/uv `docs/concepts/projects/dependencies.md`, `pyproject_mut.rs`).

## Control arms run

| Probe that came back empty | Control on the same library and command shape | Result |
|---|---|---|
| `CODEX_APP_SERVER_USE_LOCAL_DAEMON`: 0 hits | `CODEX_HOME`: 18 | The probe discriminates; the variable is not in openai/codex |
| graphify 0.9.58–62: rc=1 | 0.9.17/0.9.22 entries returned | The index is stale |
| hk v2.0.0: rc=1 | 1.56.x returned | The index is stale |
| mise registry codex: 0 | "claude": 0 | The probe is broken; the question is unanswered, not negative |
| mattpocock `to-spec` | `grill`: 20 hits | Both answer |

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — installer, `codex update`, app-server daemon updater and JSON, hook trust, PreToolUse deny and apply_patch
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — CHANGELOG (commands/skills merge), plugin-dev `@path` in commands
- [graphify-labs/graphify](https://github.com/graphify-labs/graphify) — extract, update, reflect, export, clone/global/merge-graphs; changelog coverage
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — ledger, isolation, parallel-write guard, attestation, Codex setup
- [jdx/hk](https://github.com/jdx/hk) — changelog coverage, amends-URL version binding
- [jdx/mise](https://github.com/jdx/mise) — upgrade/lock flags, backend tiers, npm lock
- [mattpocock/skills](https://github.com/mattpocock/skills) — user-invoked status of to-spec, to-tickets, implement
- [vercel-labs/skills](https://github.com/vercel-labs/skills) — `skills add/check/update` sync CLI
- [astral-sh/uv](https://github.com/astral-sh/uv) — upgrade and bounds commands
