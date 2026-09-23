# codex exec review: settings that govern sandboxing and output (#1296)

Ticket #1296 (wayfinder map #1293). Research only: no `codex exec` / `codex exec review` was run
against a repo with a prompt. The only codex commands run were `--version`, `--help` variants and
`mise run codex-schema-generate`. The write-canary is #1297.

- **Installed:** `codex-cli 0.154.0`. `mise which codex` resolves to
  `~/.local/share/mise/installs/npm-openai-codex/0.154.0/bin/codex`; the pin is
  `.config/mise/conf.d/shared.toml:44`.
- **Source read:** `knowledge-base/sources/codex`, commit `6b9826e3`. Its
  `codex-rs/Cargo.toml:152` says `version = "0.154.0"`, the same version as the install. All `file:line`
  below are relative to `codex-rs/` in that tree unless prefixed.
- **Forward check:** the six review-relevant files were fetched at `rust-v0.156.1`, the latest stable
  release on 2026-09-23, and diffed against 0.154.0 (see P9). Nothing below changes in 0.156.1.

## Answer (one paragraph)

`codex exec review` is the `exec` session machinery pointed at a review target. The review target
comes from `--commit`/`--base`/`--uncommitted`, or from a custom prompt. You can use a target flag or
a custom prompt, not both: the parser rejects the combination. Read-only is decided in five places:

1. **The sandbox setting.** Precedence, highest first: `--dangerously-bypass-approvals-and-sandbox`
   (forces danger-full-access), then a typed `-s` placed *before* `review`
   (`codex exec -s read-only review …`, which parses even though `exec review --help` hides it), then
   the merged config `sandbox_mode`, where `-c` session flags (30) beat project (25) and user (20),
   then a trust-derived default of workspace-write for trusted projects, then read-only.
2. **The review sub-agent's inheritance.** It clones the whole session config and changes only the
   model, instructions, approval (`Never`), web search and two features. So it inherits whatever
   sandbox the session resolved.
3. **execpolicy `.rules`.** An `allow` rule bypasses the sandbox. This user has `allow` rules for
   `git add` and `git commit`, so read-only has a hole unless `--ignore-rules` is passed.
4. **`--approve-for-me`.** It silently injects `sandbox_mode="workspace-write"`.
5. **The user config default.** It is `sandbox_mode = "danger-full-access"`, so a review with no
   override is fully writable.

On output: `--json` and `-o` work. **`--output-schema` parses but is silently ignored**: the review
branch never loads it, `ReviewStartParams` has no schema field, and the sub-agent is started with
`final_output_json_schema: None`. The final message is a rendered text summary; priority survives
only as a `[Pn]` title tag. The structured `review_output` (findings, `overall_correctness`,
confidence) never reaches the JSONL. It is persisted only in the session rollout file, which
`--ephemeral` suppresses. The model is `review_model` (only `-c`) if set, else the session model
(`-m`).

## Matrix

Kind: **CLI** = flag, **CFG** = `config.toml` key (settable with `-c`), **ENV** = environment,
**FILE** = on-disk input. Confidence: **H** = read in source and cross-checked (help, schema or
second file), **M** = source-read on one route only, or relies on a claim from a prior measured
report, **L** = inferred, not read.

| # | Setting | Kind | Effect on review sandbox / output | Evidence | Conf |
|---|---|---|---|---|---|
| 1 | `--commit <SHA>` | CLI | Target = one commit. Conflicts with `--uncommitted`, `--base` and `[PROMPT]` | `exec/src/cli.rs:291-297`; vendor `cli__reference.md:117-118` | H |
| 2 | `--base <BRANCH>` | CLI | Target = diff against a base. Same conflicts | `exec/src/cli.rs:283-289` | H |
| 3 | `--uncommitted` | CLI | Target = working tree. No immutable ref, so never use it in a gate | `exec/src/cli.rs:275-282` | H |
| 4 | `--title <T>` | CLI | `requires = "commit"`. Display only | `exec/src/cli.rs:299-301`; KB `codex_run.py:446-450` | H |
| 5 | `[PROMPT]` / `-` | CLI | Custom instructions become `ReviewTarget::Custom`; the model chooses what to review. Parse conflict with 1-3 | `exec/src/cli.rs:303-305`; fable-orchestrator `CHANGELOG.md:128` (0.144.1) | H |
| 6 | `-s/--sandbox` **before** `review` | CLI | Typed override. `codex exec -s read-only review` parses (rc=0); `codex exec review -s …` fails (rc=2). Not `global`, so not shown in review help, but destructured regardless of subcommand. Beats the config `sandbox_mode`. Top-level `codex -s … review` and `codex -s … exec review` also parse and inherit it | P3; `exec/src/cli.rs:140-147`; `exec/src/lib.rs:282-332,563-571`; `config/src/config_toml.rs:758`; `cli/src/main.rs:1242-1258`; `utils/cli/src/shared_options.rs:95-140` | H (parse + source); runtime is #1297 |
| 7 | `sandbox_mode` | CFG / `-c` | `-c sandbox_mode="read-only"` goes into the SessionFlags layer (30), above user (20) and project (25). Used when no `-s`. KB two-armed it on top-level `codex review` (banner `sandbox: danger-full-access` → `read-only`) | `config/src/config_layer_source.rs:33-50`; `config/src/config_toml.rs:205,758`; KB `.claude/skills/kb-review/references/lanes.md:177-186` | H (source), M (runtime on `exec review` spelling) |
| 8 | User `~/.codex/config.toml` `sandbox_mode = "danger-full-access"` | FILE | **Default with no override = full access.** Also `:4 approval_policy = "never"` and `:2 model = "gpt-6-astra"` | P6 | H |
| 9 | Project trust (`[projects."…/dotfiles"] trust_level = "trusted"`) | FILE | Matters only when no `sandbox_mode` is set anywhere: trusted/untrusted → workspace-write, otherwise read-only (`SandboxMode` default) | `config/src/config_toml.rs:759-776`; `protocol/src/config_types.rs:104-107`; P6 | H |
| 10 | Review sub-agent config inheritance | code | `start_review_conversation` clones the config and alters only web_search=Disabled, Collab/MultiAgentV2 off, `base_instructions = REVIEW_PROMPT`, `approval_policy = Never`, `model`. **The sandbox is inherited unchanged** | `core/src/tasks/review.rs:105-137` | H |
| 11 | `--dangerously-bypass-approvals-and-sandbox` (`--yolo`) | CLI (global) | Forces DangerFullAccess and skips the git-repo check. Never use it on a review | `exec/src/lib.rs:328-332,962-969` | H |
| 12 | `--approve-for-me` (before `review`) | CLI | Pushes `sandbox_mode="workspace-write"`, `approval_policy="on-request"`, `approvals_reviewer="auto_review"`. Conflicts with `-s`. **Makes a review writable** | `utils/cli/src/shared_options.rs:43-50,80-93`; `exec/src/lib.rs:281` | H |
| 13 | execpolicy `.rules` (user `~/.codex/rules/default.rules`, project `.codex/rules/`) | FILE | `Decision::Allow` gives `bypass_sandbox: true` when every command segment is allowed. **This user allows `git add` and `git commit`** (6 allow rules), so a sandboxed reviewer could still commit | `core/src/exec_policy.rs:440-455`; P7 | H (source + rule file), M (reviewer reaches this path) |
| 14 | `--ignore-rules` | CLI (global) | Skips User and Project `rules/` layers, which closes #13. System/managed rules still load | `exec/src/cli.rs:44`; `core/src/exec_policy.rs:662-679` | H |
| 15 | `default_permissions` / `[permissions]` | CFG | A layer with `default_permissions` switches to profile syntax. A session `-c sandbox_mode` (highest layer) switches back to legacy. A typed `-s` cannot be combined with `permission_profile`/`default_permissions` overrides (error). **Not set in this user config** (0 `[permissions` tables; control `[projects.` = 41) | `core/src/config/mod.rs:2491-2538,3274-3285`; P6 | H |
| 16 | `sandbox_workspace_write.*` | CFG | Applies only in workspace-write (writable roots, network). Irrelevant under read-only | `config/src/config_toml.rs:789-800` | H |
| 17 | `--add-dir` (before `review`) | CLI | Adds writable roots (workspace-write only). Parses before `review` | P3; `utils/cli/src/shared_options.rs:74-76` | M |
| 18 | `-C/--cd` (before `review`) | CLI | Sets the cwd, i.e. which repo gets diffed. Parses before `review`, which corrects "`--cd` is absent" in `codex-entrypoint-design-2026-09-22.md:36` | P3; `exec/src/lib.rs:344-350,574` | H (parse), M (runtime) |
| 19 | `-p/--profile` (v2, before `review`) | CLI | Layers `$CODEX_HOME/<name>.config.toml` (precedence 21). Could carry `sandbox_mode`. No v2 profile files exist here | `utils/cli/src/shared_options.rs:34-36`; `config_layer_source.rs:38-44`; P6 | H |
| 20 | `profile` / `profiles` (legacy) | CFG | `-c profile="x"` selects a `[profiles.x]` that may set `sandbox_mode`. Depends on user config; not recommended | `schemas/codex-config.json` (`profile`, `profiles`) | M |
| 21 | `--ignore-user-config` | CLI (global) | Skips `$CODEX_HOME/config.toml`, which drops the danger-full-access default, model, approval, **and** the `[projects]` trust. With nothing set, the fallback is read-only. Auth still comes from `CODEX_HOME`. Also drops MCP/hook config | `exec/src/cli.rs:40-42`; `exec/src/lib.rs:361-370`; `config_toml.rs:759-776` | M |
| 22 | `--strict-config` | CLI (global) | Validates `-c` overrides strictly (`validate_cli_overrides_strictly`), so a misspelled `-c sandbox_modee=` errors instead of being dropped silently (the risk fable's `run-lane.sh:103-104` names). **Also** validates user `config.toml`; whether this 25 KB config passes is unmeasured | `config/src/loader/mod.rs:277-287` | H (source), L (passes here) |
| 23 | `--worktree` | CLI (global) | Bails: "not supported with `codex exec review`" | `exec/src/lib.rs:308-310` | H |
| 24 | `review_model` | CFG / `-c` only | Reviewer model = `config.review_model` else session slug. No CLI flag (`ConfigOverrides.review_model: None`). The banner `model:` line does NOT show the reviewer model; a bogus slug fails loudly (KB, three-row measurement) | `core/src/tasks/review.rs:123-127`; `exec/src/lib.rs:565`; `config/src/config_toml.rs:159`; KB `lanes.md:189-211`; vendor `config-file__config-reference.md:32` | H |
| 25 | `-m/--model` | CLI (global) | Sets the **session** model. Becomes the reviewer model only when no layer sets `review_model` (none here). `run-lane.sh:112` relies on this | `exec/src/cli.rs:141`; `exec/src/lib.rs:552-564`; `review.rs:123-127` | H |
| 26 | `model_reasoning_effort` | CFG / `-c` | Inherited by the reviewer (config clone). User default `xhigh` | `config_toml.rs:371`; `review.rs:105`; KB `codex_run.py:480-482` | H |
| 27 | `developer_instructions` | CFG / `-c` | Not cleared by `start_review_conversation`, so it is the only channel for briefing a `--commit`/`--base` review (KB's `kb-codex` does this). This weakens the "runs unbriefed" premise in `codex-entrypoint-design-2026-09-22.md:32` | `review.rs:105-137`; `config_toml.rs:235`; KB `codex_run.py:440-445,522-523` | M |
| 28 | `base_instructions` / `model_instructions_file` | CFG | **Overwritten** by `REVIEW_PROMPT` for the reviewer, so setting them has no effect on a review | `review.rs:118-119` | H |
| 29 | `approval_policy` | CFG | Headless exec forces `Never`, and the reviewer is hard-set to `Never`. Forwarding it does nothing | `exec/src/lib.rs:568`; `review.rs:120` | H |
| 30 | `web_search`, `features.collab`, `features.multi_agent_v2` | CFG | Forced off for the reviewer | `review.rs:108-116` | H |
| 31 | `--output-schema <FILE>` | CLI (global) | **Silently ignored for review.** The review branch builds `InitialOperation::Review` with no schema. Control: the other three branches call `load_output_schema`. `ReviewStartParams` has only `threadId/target/delivery`, while `TurnStartParams` has `outputSchema`. The reviewer gets `final_output_json_schema: None` | `exec/src/lib.rs:871-876,900,922,951,1176-1188`; `review.rs:136`; generated `schemas/codex_app_server_protocol.v2.schemas.json` | H |
| 32 | `--json` | CLI (global) | JSONL events. The `ExitedReviewMode` item falls into `_ => None`, so only the rendered agent message, the reviewer's forwarded command items and `turn.completed` appear | `exec/src/event_processor_with_jsonl_output.rs:142-317,380-394`; `review.rs:179-181` | H |
| 33 | `-o/--output-last-message <FILE>` | CLI (global) | Writes the final agent message = `render_review_output_text`: explanation plus `- <title> — <abs path>:<start>-<end>` plus body. Drops the numeric `priority`, `confidence_score` and `overall_correctness`; priority survives only as the rubric's `[Pn]` title tag | `protocol/src/review_format.rs:23-82`; `prompts/templates/review/rubric.md:56-58,71-91` | H |
| 34 | Session rollout `~/.codex/sessions/**/rollout-*-<thread>.jsonl` | FILE (output) | Persists `EnteredReviewMode`/`ExitedReviewMode` with structured `review_output` (`findings[]`, `overall_correctness`). This is the only structured channel. The observed file predates 0.154 | P8 | M |
| 35 | `--ephemeral` | CLI (global) | No session files, so no rollout (#34) and invisible to agentsview. Whether it breaks the review sub-agent (`run_codex_thread_one_shot`, not a collab spawn) is **unmeasured**; `ai-cli-invocation.md` records it breaking collab spawns | `exec/src/cli.rs:36-37`; `.claude/rules/ai-cli-invocation.md` | L |
| 36 | `--color` | CLI | Human output only. Exec-level, not global | `exec/src/cli.rs:54-56` | H |
| 37 | `--thread-source`, `--skip-git-repo-check` | CLI (global) | Metadata / repo check. No sandbox effect | `exec/src/cli.rs:28-34` | H |
| 38 | `--enable/--disable <F>` | CLI | `-c features.<F>=bool`. `collab`/`multi_agent_v2` are forced off for the reviewer anyway | help; `review.rs:115-116` | H |
| 39 | `--dangerously-bypass-hook-trust` + `.codex/hooks.json` | CLI/FILE | Project hooks (SessionStart runs `mise run doctor`; SessionEnd **writes `.agent/command-audit.md`**) run when trusted. Trust is keyed by the absolute hooks.json path; the main checkout's is trusted, a worktree's path is not. **A write confound for #1297** | `.codex/hooks.json:35-57`; `~/.codex/config.toml:400-412` (`hooks.state` keys) | M |
| 40 | `service_tier`, `features.fast_mode` | CFG | Speed/credits only (fable `run-lane.sh:99`) | fable `run-lane.sh:99` | M |
| 41 | `CODEX_HOME` | ENV | Chooses which `config.toml`, `rules/` and auth are loaded. A dedicated home is an alternative to `--ignore-user-config` | vendor `config-file__environment-variables.md:17` | H |
| 42 | `CODEX_SANDBOX=seatbelt` / `CODEX_SANDBOX_NETWORK_DISABLED` | ENV (set *by* codex) | Set in commands spawned under the macOS sandbox or with restricted network. **A canary can observe these from inside** | `core/src/sandboxing/mod.rs:182`; `core/src/spawn.rs:15-26` | H |
| 43 | `CODEX_API_KEY`, `CODEX_ACCESS_TOKEN` | ENV | Auth only. No sandbox effect | vendor `config-file__environment-variables.md:49-50` | H |
| 44 | Repo `.codex/config.toml` | FILE | Gitignored (`.gitignore:59`), main checkout only, `[shell_environment_policy]` only. No sandbox key; absent from worktrees | P6 | H |

## Corrections to prior repo claims

- `codex-entrypoint-design-2026-09-22.md:32` said "Structure is enforced CLI-side via
  `--output-schema` … UNVERIFIED". Source says **false**: row 31. `matrix D`/`D10` should drop
  `--output-schema` for review. Use `-o` text plus the rollout's `ExitedReviewMode.review_output`
  (rows 33-34), or parse `[Pn]` titles.
- `codex-entrypoint-design-2026-09-22.md:36` said "`--cd` is absent". It is absent only *after*
  `review`; `codex exec -C <dir> review` parses (row 18).
- `codex-entrypoint-design-2026-09-22.md:32` said "runs the built-in review prompt unbriefed".
  `-c developer_instructions=` survives into the reviewer (row 27, M).
- The inherited premise "read-only rests on `-c sandbox_mode`" (sessions `779cb015`, `525e74e6`) is
  **incomplete**. A typed `-s` before `review` exists (row 6), and neither closes the execpolicy
  allow-rule bypass (rows 13-14).

## Candidate invocations for #1297 (write-canary)

Run each arm in a **throwaway git repo** under the scratchpad, not in this checkout or its main path.
That avoids the trusted hooks (row 39) and any writable-arm damage. `cd` into it; `-C` is optional.
Each arm needs a write *driver*. `--commit` forbids `[PROMPT]`, so drive with
`-c developer_instructions="…"` (row 27), or run the same arm once in custom-prompt mode (`-`, no
target), which is fable's form.

The sentinel is a path the reviewer is told to create (for example `./CANARY_WRITTEN`, and
`$TMPDIR/canary-<nonce>`). Observables:

1. The sentinel appears, or not.
2. `git status --porcelain` in the throwaway repo.
3. The JSONL `command_execution` items' `exit_code` and `aggregated_output` (expect
   `Operation not permitted`).
4. The reviewer running `env | grep CODEX_SANDBOX`, which should print `seatbelt` (row 42).
5. The human-mode banner `sandbox:` line, when not in `--json` (KB: a valid observable).

```bash
# A — the doctrine form (config key only)
mise exec -- codex exec review --commit <SHA> \
  -c 'sandbox_mode="read-only"' -c 'review_model="gpt-6-sol"' \
  -c 'developer_instructions="<attempt-write driver>"' --json -o <final.txt>

# B — typed flag only (-s MUST precede `review`)
mise exec -- codex exec -s read-only review --commit <SHA> \
  -c 'review_model="gpt-6-sol"' -c 'developer_instructions="<driver>"' --json -o <final.txt>

# C — POSITIVE CONTROL: no override -> user config danger-full-access -> the write MUST land.
#     If it does not, the driver/observable is broken and A/B prove nothing.
mise exec -- codex exec review --commit <SHA> \
  -c 'developer_instructions="<driver>"' --json -o <final.txt>

# D — allow-rule hole: read-only, but drive `git add <f> && git commit -m canary` (matches the
#     user allow rules). Expect the commit to LAND without --ignore-rules and FAIL with it.
mise exec -- codex exec -s read-only review --commit <SHA> -c 'developer_instructions="<git-commit driver>"' --json -o <d1.txt>
mise exec -- codex exec -s read-only --ignore-rules review --commit <SHA> -c 'developer_instructions="<git-commit driver>"' --json -o <d2.txt>

# E — output-schema arm (settles row 31 empirically): add --output-schema <schema>; expect the
#     -o text to be the rendered review, NOT schema-shaped JSON.
# F — --strict-config arm: add --strict-config to A; a pass shows the user config is strict-clean,
#     and a deliberately misspelled `-c sandbox_modee=` must then FAIL (validates row 22).
# G — --ephemeral arm: add --ephemeral to A; record whether the review still completes (row 35).
```

**Recommended production form**, pending #1297 results:

```bash
mise exec -- codex exec -s read-only --ignore-rules review --commit <SHA> \
  -c 'sandbox_mode="read-only"' -c 'review_model="<model>"' \
  -c 'model_reasoning_effort="xhigh"' [-c 'developer_instructions="<method>"'] \
  --json -o <final.txt>
```

- `-s` and `-c` are redundant on purpose: the typed flag wins and the key covers any caller that
  drops the flag.
- No `--output-schema`: it is ignored.
- No `--ephemeral` until arm G has run, so the rollout keeps the structured review.
- Never `--approve-for-me`, `--yolo`, `--add-dir` or `--uncommitted`.

## Probe log (with control arms)

### P1 — version

`codex --version` gave `codex-cli 0.154.0`. `codex-rs/Cargo.toml:152` gives `0.154.0`. Two routes,
same answer.

### P2 — help surfaces

Raw captures are in `.agent/kb/raw/codex-0154-exec-review-help.txt` and
`.agent/kb/raw/codex-0154-exec-help.txt`.

`codex exec review --help` lists: `-c`, `--uncommitted`, `--base`, `--enable`, `--commit`,
`--disable`, `--strict-config`, `--title`, `-m`, `--dangerously-bypass-approvals-and-sandbox`,
`--dangerously-bypass-hook-trust`, `--worktree`, `--thread-source`, `--skip-git-repo-check`,
`--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--output-schema`, `--json` and `-o`. It
does not list `-s`, `-p`, `-C`, `--add-dir` or `--approve-for-me`.

**Control:** `codex exec --help` does list `-s, --sandbox <SANDBOX_MODE>`. The absence is real, not
a display bound.

### P3 — flag placement (help-only; nothing executes)

| Probe | Result |
|---|---|
| `codex exec -s read-only review --help` | rc=0 |
| `codex exec review -s read-only --help` | rc=2, `unexpected argument '-s'` |
| Control: `codex exec -Q review --help` | rc=2, `unexpected argument '-Q'`, so the parser rejects unknown names |
| `codex exec -p x -C /tmp --add-dir /tmp review --help` | rc=0 |
| `codex -s read-only review --help` | rc=0 |
| `codex -s read-only exec review --help` | rc=0 |

⚠️ **Limit:** `-s bogus-mode … --help` also returned rc=0 on both spellings. `--help` short-circuits
before the value is validated, so these probes prove the flag *name* is accepted in that position,
not the value. The value and its runtime effect are #1297's job. `-s` uses a clap `ValueEnum`
(`utils/cli/src/shared_options.rs:40-41`).

### P4 — agentsview (current session `f643887b` excluded)

- Sessions `779cb015` and `525e74e6` (2026-09-22): "no `-s`; read-only rests on `-c sandbox_mode`,
  unverified". This is the premise this ticket inherits.
- `dd442cf4-4469-4773-9f50-6f6c2584afae` #442: points to fable-orchestrator `CHANGELOG.md:128`
  (`--commit`/`--base` are mutually exclusive with custom instructions on 0.144.1), which prompted
  the re-measure.
- `b72c95e0-c9b0-4405-9c38-6bd9885f2f71` #676-698: the drafted doctrine lists `-c review_model`,
  `-c sandbox_mode`, `--output-schema`.
- KB codex sessions `codex:01a09c55…` (2026-09-13/14): the bogus-`review_model` arm, which led to KB
  `lanes.md:189-211`.
- The first unexcluded search returned 8/8 hits from this very session. That is why
  `--exclude-session` matters.

### P5 — source

Every `file:line` in the matrix. The key cross-checks:

- `--output-schema` is ignored for review by **three independent routes**:
  1. the exec review branch has no `load_output_schema` (control: the three other branches do);
  2. the generated v2 schema's `ReviewStartParams` has no `outputSchema` (control: `TurnStartParams`
     has it);
  3. `review.rs:136` passes `final_output_json_schema: None`.
- The sandbox is inherited by **two routes**: `review.rs:105` clones the config, and
  `review.rs:106-127` has no permission or sandbox write.

### P6 — local config

Only key names and non-secret values were read; lines holding hashes were elided.

- `~/.codex/config.toml`:
  - `:2 model = "gpt-6-astra"`, `:3 model_reasoning_effort = "xhigh"`,
    `:4 approval_policy = "never"`, `:6 sandbox_mode = "danger-full-access"`.
  - No top-level `review_model` or `default_permissions`.
  - `grep -c '^\[permissions'` = 0. Control: `grep -c '^\[projects\.'` = 41 on the same file.
  - `:305-306` `[projects."…/dotfiles"] trust_level = "trusted"`.
  - `:383-412` `hooks.state` trusts the main-checkout `.codex/hooks.json` pre_tool_use,
    session_start and session_end entries.
- No `~/.codex/*.config.toml` (v2 profiles) and no `/etc/codex`.
- The repo `.codex/config.toml` is gitignored and holds `[shell_environment_policy]` only.

### P7 — execpolicy rules

- `grep -c prefix_rule ~/.codex/rules/default.rules` = 6. All 6 have `decision="allow"`.
- The patterns (only `pattern=` extracted) include `["git","add"]`, `["git","commit"]` and
  `["gh","run","list"]`, plus a `git push` wrapper.
- Source: `core/src/exec_policy.rs:440-455` gives `Allow => Skip { bypass_sandbox: <all segments allowed> }`.

### P8 — rollout persistence

- `grep -rli 'review_output|exitedreviewmode|exited_review' ~/.codex/sessions` found 269 files.
- One (2026-03-26) carries `"type":"ExitedReviewMode"` with `"review_output":{"findings":[{"title":"[P2…`
  and `"overall_correctness":"patch is incorrect"`.
- The first probe for the lowercase `"exited_review_mode"` returned 0 while the control
  `"turn_context"` hit. The spelling was the bound. This file predates 0.154, so the 0.154 format
  is M.

### P9 — 0.154.0 to 0.156.1 forward check

- The GitHub compare API truncates its file list at 300 files (739 commits). That list is a bound,
  not evidence of "no change".
- So each file was fetched directly at `rust-v0.156.1` (raw copies in
  `.agent/kb/raw/codex-01561/`) and diffed:

| File | Diff |
|---|---|
| `exec/src/cli.rs` | identical |
| `utils/cli/src/shared_options.rs` | identical |
| `protocol/src/review_format.rs` | identical |
| `core/src/tasks/review.rs` | +2 lines (`ctx.model_info()` args) |
| `exec/src/lib.rs` | only `disabled_plugin_ids` and `turn_trigger` in `TurnStartParams`; the review branch is unchanged |
| JSONL processor | web-search mapping only; `ExitedReviewMode` 0 hits (control: `ThreadItem::AgentMessage` 4) |

### P10 — offline vendor docs

`knowledge-base/sources/agent-harness-docs/docs/codex/`:

- `cli__reference.md:110-118` documents the top-level `codex review` and its target/prompt
  conflicts.
- `config-file__config-reference.md:32` documents `review_model`.
- `non-interactive-mode.md:92-116` documents `--output-schema` for **prompted `codex exec` only**.
- No page documents `codex exec review`: 0 hits for `exec review`, while the control
  `codex review` hits 2 files.
- `config-file__environment-variables.md` documents no sandbox-configuring env var.

### P11 — schema

- `mise run codex-schema-generate` returned rc=0; `schemas/codex_app_server_protocol.version` =
  `0.154.0`.
- The vendored `schemas/codex-config.json` (`sources.toml:40-46`, 0.154.0) describes
  `review_model`, `sandbox_mode`, `default_permissions`, `developer_instructions`, `profile` and
  `approvals_reviewer`.
- `ephemeral` is ABSENT from the config schema. That is expected (it is a CLI flag) and serves as
  the known-absent arm.

## Open (for #1297 or later)

1. Runtime effect of `-s` placed before `review` (arm B) versus `-c sandbox_mode` (arm A). Source
   predicts both give read-only.
2. Whether the reviewer's shell tool actually takes the execpolicy allow-bypass path (arm D).
3. Whether `--ephemeral` breaks the review sub-agent (arm G).
4. Whether the user config is `--strict-config`-clean (arm F).
5. Whether `developer_instructions` reaches the reviewer's prompt (KB claims it; not re-measured
   here).
6. The rollout `ExitedReviewMode` format at 0.154.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — exec/review/config/exec-policy source at 0.154.0 (KB offline copy) and 0.156.1 (fetched), plus the releases list and the compare API
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `kb_setup/codex_run.py`, `kb-review/references/lanes.md` (prior measured review-flag work), offline vendor docs `sources/agent-harness-docs/docs/codex/`
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — prior reports, `.codex/hooks.json`, `schemas/`, `python/src/dotfiles_setup/codex_schema.py`
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — plugin cache 1.21.0 `CHANGELOG.md:128`, `scripts/run-lane.sh:96-116`, `agents/codex-reviewer.md` (read from the local cache; the prior report records that the upstream repo returns 404)
