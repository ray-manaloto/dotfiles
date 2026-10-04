# Codex non-interactive settings: the codex-cli 0.160.0 surface, a unified output schema, and a proposal for both repos

- **Date:** 2026-10-03
- **Question:** What is the complete, current (codex-cli 0.160.0) surface for running
  OpenAI Codex non-interactively and configuring it per project? Which settings should
  knowledge-base and dotfiles adopt?
- **Binary under test:** `/Users/rmanaloto/.codex/packages/standalone/current/bin/codex`,
  which reports `codex-cli 0.160.0`.
- **Source under test:** `openai/codex` at tag `rust-v0.160.0`, clone HEAD
  `a956835d020762cb2b570053af06f643a11c0ecc`.
- **Status:** a proposal only. Nothing in either repo was changed.

## Answer

> ⚠️ **This sweep is INCOMPLETE.** Two mandatory stages did not run:
>
> 1. The `openai/codex` dependency stage for the query `"claude-code"` failed on
>    **github-releases**. The error was `exited 1: stream error: stream ID 1; CANCEL;
>    received from peer`.
> 2. The `anthropics/claude-code` dependency stage has **no PROBE-JSON line**. Either the
>    probe never ran or its output was never copied.
>
> As a result, **this sweep read no codex release notes from GitHub Releases**. It also
> ran **no dependency fan-out against `anthropics/claude-code`**. Seven caller-named
> codex pages were also **not mirrored offline**: the 404'd `config-file` root, plus six
> pages that hit a firecrawl rate limit. Those six were read **live** instead (see Gaps).

### 1. The CLI surface (binary + source; the docs are incomplete *and* wrong in places)

**Non-interactive entry points.** There are three, and they differ in what they emit:

| Command | Machine output | Notes |
|---|---|---|
| `codex exec [PROMPT\|-]` (alias `e`) | `--json` (alias `--experimental-json`) gives a JSONL event stream. `-o/--output-last-message FILE`. `--output-schema FILE`. | The real headless surface. |
| `codex exec review` | Accepts `--json`, `-o`, `--output-schema`, `--base`, `--commit`, `--uncommitted`, `--title`. | `--output-schema` is *accepted* because exec declares it `global = true` (`exec/src/cli.rs#L47-L49`). Two open issues say it is then *ignored*: #38545 and #35596. That is unverified at the binary level. |
| `codex review` (top level) | **None.** The probed flag set is exactly `--base --commit --uncommitted --title --strict-config --enable --disable -c`. | It has no `--json`, `--output-schema`, `-o` or `--sandbox` **of its own**, so it is useless for structured output. Qualification: it is a thin alias that inherits ROOT options given before the subcommand (`codex -s X review`, `codex -m X review`, `codex -c ... review`), so a sandbox is still reachable there. `exec review` has no `-s` either. Its prompt conflicts with `--uncommitted`/`--base`/`--commit`, and `--title` requires `--commit` (source only). |

**Every flag `codex exec --help` lists in 0.160.0** (taken from the help text, then
de-duplicated):

- `-c/--config`, `--enable`, `--disable`, `--strict-config`
- `-i/--image`, `-m/--model`, `--oss`, `--local-provider`
- `-p/--profile`, `-s/--sandbox`, `--approve-for-me`
- `--dangerously-bypass-approvals-and-sandbox`, `--dangerously-bypass-hook-trust`
- `-C/--cd`, `--add-dir`, `--worktree`
- `--skip-git-repo-check`, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`
- `--output-schema`, `--color`, `--json`, `-o/--output-last-message`, `--thread-source`

Subcommands are `resume`, `fork` and `review`.

**Two things exec does NOT accept.** Both are absence claims, and both were armed:

- **`--full-auto`.** It gives rc 2 and `error: unexpected argument '--full-auto' found`. A
  bogus flag gives the same rc 2. The control, the hidden alias `--experimental-json`,
  gives rc 0. The docs say `--full-auto` is still a *deprecated compatibility flag that
  prints a warning*. **For 0.160.0 that is false.**
- **`--ask-for-approval`.** It gives rc 2 after `exec`. Set approval with
  `-c approval_policy="never"` (rc 0). The top-level form `codex -a never exec …` also
  parses (rc 0), but only the parse was tested, not the effect.

**Hidden subcommands.** These are absent from `codex --help` but present in the binary:

- `execpolicy` (with `check`)
- `responses-api-proxy`
- `stdio-to-uds`

The control arm: `codex zzbogus --help` prints the top-level "Codex CLI" help. So do
`mcp-server` and `generate-ts`, which means **those two are NOT subcommands in 0.160.0**.

**`--strict-config` is a root flag gated by a subcommand WHITELIST, not a global arg.**
(Verification qualified this item; see `## Verification`.) The source function
`unsupported_subcommand_name_for_strict_config` (`cli/src/main.rs` ~L2228-2268) allows the
top level, `agents`, `exec`, `review`, `exec-server`, `resume`, `queue`, `archive`, `delete`,
`unarchive`, `fork`, `doctor` and bare `app-server`. It **hard-rejects** `features`, `mcp`,
`plugin`, `login`, `logout`, `cloud`, `sandbox`, `debug`, `apply`, `completion` and `update`
with ``--strict-config` is not supported for `codex <sub>```. Probed: `codex --strict-config
mcp list`, `... features list` and `... login status` each fail with that error. The cited
L314/L394/L562 are the `ReviewCommand`, session-archive and `app-server` declarations, not
exec or the root flag. A wrapper must therefore add it only to whitelisted commands. Help
output:

| Help output | `--strict-config` listed? |
|---|---|
| `codex exec --help` | yes |
| `codex exec review --help` | yes |
| `codex review --help` | yes |
| `codex features --help` | **no** (actively rejected, not merely unlisted) |
| `codex resume --help` | yes |

**Feature flags.** `codex features list` gives **154 rows** in this binary. The four the
user named:

| Feature | Stage | Default (source) | Effective here | Use for headless? |
|---|---|---|---|---|
| `agent_message_board` | under development | false (`features/src/lib.rs#L1349-L1353`) | false | No. Under development, and wired into multi-agent v2 runtimes (PR #47017). |
| `analytics_plan_history` | experimental | false (`lib.rs#L936-L942`) | false | No. It is an `/analytics` preview of consumer-plan allowance history (the source says `/analytics` and consumer accounts; "TUI" is inferred). |
| `multi_agent_v2` | **stable** (Stable does NOT mean on or recommended; the default-on path is `multi_agent`/Collab) | **false** (`lib.rs#L1337-L1341`) | false | Candidate. Trial it per invocation with `--enable multi_agent_v2` before committing it. |
| `recommended_plugins` | **stable** | false (`lib.rs#L1451-L1455`) | false | No. It suggests plugins and is OR-gated with `tool_suggest` (`lib.rs:534`); only matters when Apps and Plugins are on. |

Qualification: `multi_agent_v2` accepts a bool or a config table (`[features.multi_agent_v2]`,
`MultiAgentV2ConfigToml`), `multi_agent_mode` is Stage::Removed, and defaults are compile-time
only; config, requirements or account gating can change the effective state.

The full 154-row list is in Evidence. `codex features list` reports the **effective**
state for the current config layers, not the built-in default. Its help says so: "List
known features with their stage and effective state". So `true` in that column may be a
user setting.

### 2. Configuration surface

**Precedence (live config-basic).** From highest to lowest:

1. CLI flags and `-c`
2. Project `.codex/config.toml`, closest file wins (**trusted projects only**)
3. `--profile` file `~/.codex/<name>.config.toml` (separate files since 0.134.0; `[profiles.x]` tables are dead)
4. `~/.codex/config.toml`
5. Cloud-managed and `/etc/codex/config.toml`
6. Built-in defaults

**Keys a project file cannot set.** Codex ignores these with a startup warning:

- `openai_base_url`, `chatgpt_base_url`
- `apps_mcp_product_sku`
- `model_provider`, `model_providers`
- `notify`
- `profile`, `profiles`
- `experimental_realtime_ws_base_url`
- `otel`

**Project-level files.** All of these are trust-gated: "Untrusted projects skip
project-scoped `.codex/` layers, including project-local config, hooks, and rules."

- `.codex/config.toml`
- `.codex/hooks.json`, or inline `[[hooks.<Event>]]` in config.toml. A layer holding both loads both and warns.
- `.codex/rules/*.rules`: Starlark `prefix_rule`, experimental. Test them with the hidden `codex execpolicy check`.
- `.codex/agents/*.toml`: required keys `name`, `description`, `developer_instructions`.
- `AGENTS.md` / `AGENTS.override.md`: these sit in the repo directories, **not** in `.codex/`. They are loaded from the root down to the cwd, capped by `project_doc_max_bytes` (32 KiB).

**Environment variables.** The live environment-variables page lists only these stable
public names:

- `CODEX_HOME` (must already exist), `CODEX_SQLITE_HOME`
- `CODEX_NON_INTERACTIVE` and `CODEX_INSTALL_DIR` (installer only)
- `CODEX_API_KEY` (set it inline, never job-wide), `CODEX_ACCESS_TOKEN`
- `OPENAI_FEDERATION_RULE_ID`, `OPENAI_IDENTITY_TOKEN_FILE`, `OPENAI_WORKLOAD_IDENTITY_CONTEXT`
- `CODEX_CA_CERTIFICATE` (wins over `SSL_CERT_FILE`)
- `RUST_LOG`: exec defaults to `error`

`strings` on the binary finds more `CODEX_*` names that the page does not document:

- `CODEX_EXEC_SERVER_URL`, `CODEX_URL`, `CODEX_AUTH`
- `CODEX_GITHUB_PERSONAL_ACCESS_TOKEN`, `CODEX_APPLY_GIT_CFG`
- `CODEX_MANAGED_PACKAGE_ROOT`, `CODEX_MCP_PROTOCOL_VERSION`, `CODEX_INTERNAL_ORIGINATOR_OVERRIDE`
- the `CODEX_NETWORK_PROXY_*` family

This list is a **lower bound**, because `strings` cannot see names that are built at
runtime.

### 3. Machine-readable output, compared

| Field | `codex exec --json` | `claude -p --output-format json` | `agy --output-format json` |
|---|---|---|---|
| Framing | JSONL events, discriminated by `type` (`thread.started`, `turn.*`, `item.*`, `error`) | One result object. `stream-json` gives `type`/`subtype` events and needs `--verbose`. | One envelope. `stream-json` gives `init`/`step_update`/`result` events, discriminated by `event` with a nested payload. |
| Session id | `thread.started.thread_id` | `session_id` | `conversation_id` |
| Final text | the last `item.completed` whose `item.type=agent_message` has `.text` set (also `-o FILE`) | `result` | `response` |
| Structured output | **no separate field.** With `--output-schema`, the final agent-message *text* is the JSON. | `structured_output` (needs `--json-schema`) | `structured_output` and `json_schema`. `response` holds the same payload serialized. |
| Status | `turn.completed` vs `turn.failed`, plus `error` events | `subtype`: `success`, `error_max_turns`, `error_during_execution`, `error_max_budget_usd`, `error_max_structured_output_retries`; plus `is_error` | `status`: `SUCCESS`, `ERROR`, `CANCELED`, `INTERRUPTED`, `INVALID`, `WAITING`, `RUNNING`; plus `error` |
| Usage | `usage.{input_tokens, cached_input_tokens, output_tokens, reasoning_output_tokens}` on `turn.completed` | `usage`, plus per-model `modelUsage` | `usage.{input_tokens, output_tokens, thinking_tokens, cache_read_tokens, total_tokens}` |
| Cost | **none** (the wrapper must compute it from a price table) | `total_cost_usd` (a client-side estimate) | **none** |
| Duration / turns | **none in the documented stream** (the wrapper must time the run; claude is `duration_ms`, agy is `duration_seconds`, different units) | `duration_ms`, `duration_api_ms`, `num_turns` | `duration_seconds`, `num_turns` |

**Proposed unified schema.** The JSON Schema is under Recommendation §C. It has a common
core envelope with normalized names, plus `extensions.{codex,claude,agy}`, which carry
every CLI-native field verbatim.

### 4. Saved GitHub searches

These are under Recommendation §B. Each is an exact `gh api` command with its qualifiers
and a control arm, and each can be tuned and re-run.

### 5. Recommended configuration

This is under Recommendation §D, as a proposal only. The headline:

- Keep project `.codex/config.toml` minimal and trust-dependent.
- Put the non-interactive flag set in an **invocation wrapper**, not in a profile file.
  A profile has to live in `$CODEX_HOME`, which is user-global, and `do-not.md` #11
  forbids writing there.
- Use `--strict-config` on every lane run of `exec`, `exec review`, `review`, `resume` and
  `fork`, and NOT on `features`, `mcp`, `login`, `plugin`, `sandbox` etc., which reject it.
  Its effect on both repos' configs is still unprobed (see Gaps), so this is unproven.
- Drop `--full-auto` everywhere.
- Use `codex exec review --json`, never top-level `codex review`, when you need machine
  output.

## Evidence

### Claims

| Claim | URL or file:line | Quote |
|---|---|---|
| Installed binary = tag under test | `codex --version` (probe, this report); <https://github.com/openai/codex/tree/rust-v0.160.0> | `codex-cli 0.160.0` |
| exec: progress goes to stderr, the final message to stdout | <https://learn.chatgpt.com/docs/non-interactive-mode> (mirror links/1.md) | "Codex streams progress to `stderr` and prints only the final agent message to `stdout`." |
| exec's default sandbox is read-only | same | "By default, `codex exec` runs in a read-only sandbox." |
| Docs claim `--full-auto` is a deprecated warning flag | same | "Codex keeps `codex exec --full-auto` as a deprecated compatibility flag and prints a warning." |
| **Binary rejects `--full-auto`** | probe: `codex exec --full-auto --help` → rc 2; bogus flag → rc 2; `--experimental-json` → rc 0 | "error: unexpected argument '--full-auto' found" |
| `--json` event types | <https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable> | "Event types include `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.*`, and `error`." |
| Shape of usage on `turn.completed` | same | `{"type":"turn.completed","usage":{"input_tokens":24763,"cached_input_tokens":24448,"output_tokens":122,"reasoning_output_tokens":0}}` |
| `-o` writes a file and still prints | same | "This writes the final message to the file and still prints it to `stdout`" |
| `--output-schema` constrains the final response | <https://learn.chatgpt.com/docs/non-interactive-mode#create-structured-outputs-with-a-schema> (links/3.md:173) | "use `--output-schema` to request a final response that conforms to a JSON Schema." |
| `--output-schema` is a global option on exec | <https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/exec/src/cli.rs#L47-L49> | `#[arg(long = "output-schema", value_name = "FILE", global = true)]` |
| `--json` alias | <https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/exec/src/cli.rs#L58-L74> | `long = "json", alias = "experimental-json"` |
| `--ignore-user-config` and `--ignore-rules` | <https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/exec/src/cli.rs#L31-L45> | "Do not load `$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`." |
| exec flag set (binary) | probe: `codex exec --help` (de-duplicated flag list in Answer §1) | `--strict-config`, `--dangerously-bypass-hook-trust`, `--approve-for-me`, `--thread-source` … |
| exec review accepts `--json`, `--output-schema` and `-o` | probe: `codex exec review --help` | flag list includes `--json --output-schema -o, --output-last-message` |
| **Top-level `codex review` has no machine output** | probe: `codex review --help` | flag list is exactly `--base --commit --disable --enable --strict-config --title --uncommitted -c, --config -h, --help` |
| `--strict-config` is declared per struct | <https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/cli/src/main.rs#L314> | `#[arg(long = "strict-config", default_value_t = false)]` |
| Docs say what `--strict-config` covers | <https://learn.chatgpt.com/docs/developer-commands?surface=cli#cli-global-flags> (links/9.md) | "Supported by runtime commands such as `codex`, `exec`, `review`, `resume`, `fork`, `app-server`, and `exec-server`." |
| `features` does not take `--strict-config` or `--profile` | probe: `codex features --help`; docs links/9.md | "The `features` subcommand doesn't accept `--profile`." |
| exec rejects `--ask-for-approval`; `-c approval_policy` works | probe: `codex exec --ask-for-approval never --help` → rc 2; `codex exec -c approval_policy=never --help` → rc 0; `codex -a never exec --help` → rc 0 (parse only) | — |
| Hidden subcommands exist | probe: `codex execpolicy --help` → "Execpolicy tooling"; `responses-api-proxy` → "Internal: run the responses API proxy"; `stdio-to-uds` → "Internal: relay stdio to a Unix domain socket"; control `codex zzbogus --help` → "Codex CLI" | — |
| `mcp-server` and `generate-ts` are NOT subcommands in 0.160.0 | same probe: both print the top-level "Codex CLI" help, the same as the bogus control | — |
| `agent_message_board` | <https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/features/src/lib.rs#L1349-L1353> | `key: "agent_message_board", stage: Stage::UnderDevelopment, default_enabled: false,` |
| `multi_agent_v2` | <https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/features/src/lib.rs#L1337-L1341> | `key: "multi_agent_v2", stage: Stage::Stable, default_enabled: false,` |
| `recommended_plugins` | <https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/features/src/lib.rs#L1451-L1455> | `key: "recommended_plugins", stage: Stage::Stable, default_enabled: false,` |
| `analytics_plan_history` | <https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/features/src/lib.rs#L936-L942> | "Preview five-hour and weekly allowance history for consumer accounts in /analytics." |
| `agent_message_board` was introduced, not added and then removed | <https://github.com/openai/codex/pull/47017> | "Wire agent message boards into persistent multi-agent runtimes (#47017)" |
| `features enable/disable` persist to user config | links/9.md | "The `enable` and `disable` commands persist changes so they apply to future sessions." |
| `--enable` translates to `-c features.<name>=true` | probe: `codex features --help` | "Enable a feature (repeatable). Equivalent to `-c features.<name>=true`" |
| Flag safety tips | <https://learn.chatgpt.com/docs/developer-commands?surface=cli#cli-flag-combinations-and-safety-tips> (links/8.md) | "Pair `--json` with `--output-last-message` in CI to capture machine-readable progress and a final natural-language summary." |
| Avoid the full-bypass flag | same | "avoid `--dangerously-bypass-approvals-and-sandbox` unless you are inside a dedicated sandbox VM." |
| Purpose of the hook-trust bypass | links/9.md | "Intended only for automation that already vets hook sources." |
| Config precedence | <https://learn.chatgpt.com/docs/config-file/config-basic> (LIVE, not mirrored) | "2. Project config files: `.codex/config.toml` … (closest wins; trusted projects only)" |
| Profiles are separate files | <https://learn.chatgpt.com/docs/config-file/config-advanced> (LIVE) | "In Codex 0.134.0 and later, `--profile` no longer reads `[profiles.profile-name]`" |
| Keys ignored in project config | same (LIVE) | "Codex ignores the following keys in project-local `.codex/config.toml` … `notify`, `profile`, `profiles` … and `otel`." |
| Docs' feature table is not exhaustive | config-basic (LIVE) | "This table lists common user-facing flags, not every internal or under-development feature." |
| Trust gates the project layers | <https://learn.chatgpt.com/docs/config-file/config-reference> (LIVE) | "Untrusted projects skip project-scoped `.codex/` layers, including project-local config, hooks, and rules." |
| `default_permissions` exclusivity | same (LIVE) | "Don't combine with `sandbox_mode` or `[sandbox_workspace_write]`." |
| `CODEX_API_KEY` scope | <https://learn.chatgpt.com/docs/non-interactive-mode#authenticate-in-automation> | "You can use `CODEX_API_KEY` with `codex exec`, `codex review`, the TypeScript SDK, and `codex exec-server --remote`." |
| `RUST_LOG` default for exec | <https://learn.chatgpt.com/docs/config-file/environment-variables> (LIVE) | "`codex exec` defaults to `error` output unless you set a more verbose value." |
| Env-var page coverage is bounded | same (LIVE) | "It does not list internal development variables, test variables, or provider-specific secret names" |
| Undocumented `CODEX_*` names in the binary | probe: `strings codex \| grep -oE 'CODEX_[A-Z_]{3,}'` (control: `CODEX_HOME` is found) | `CODEX_EXEC_SERVER_URL CODEX_URL CODEX_AUTH CODEX_APPLY_GIT_CFG …` |
| Subagent approvals fail in exec | <https://learn.chatgpt.com/docs/agent-configuration/subagents?surface=cli> (links/17.md) | "an action that needs new approval fails and Codex surfaces the error back to the parent workflow." |
| Subagents inherit live overrides | same | "Codex also reapplies the parent turn's live runtime overrides when it spawns a child." |
| Location of custom agents | same | "add standalone TOML files under `~/.codex/agents/` … or `.codex/agents/` for project-scoped agents." |
| AGENTS.md concatenation | <https://learn.chatgpt.com/docs/agent-configuration/agents-md> (LIVE) | "Codex concatenates files from the root down, joining them with blank lines." |
| Size cap on AGENTS.md | same (LIVE) | "`project_doc_max_bytes` (32 KiB by default)" |
| Project rules are trust-gated | <https://learn.chatgpt.com/docs/agent-configuration/rules> (LIVE) | "Project-local rules under `<repo>/.codex/rules/` load only when the project `.codex/` layer is trusted." |
| Offline rule test | same (LIVE) | `codex execpolicy check --pretty --rules ~/.codex/rules/default.rules -- gh pr view 7888 …` |
| Hook locations, all of which load | <https://learn.chatgpt.com/docs/hooks> (links/19.md) | "Higher-precedence config layers don't replace lower-precedence hooks." |
| Hook trust is keyed to a hash | same | "Codex records trust against the hook's current hash, so new or changed hooks are marked for review and skipped until trusted." |
| Hook-trust bypass for automation | same | "pass `--dangerously-bypass-hook-trust` to run enabled hooks without requiring persisted hook trust for that invocation." |
| 12 hook events | same | "`PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop` … `Interrupt` … `SessionStart`, `SubagentStart` … `SessionEnd`" |
| Hooks are not a security boundary | same | "Treat tool hooks as a useful guardrail, not a complete enforcement boundary." |
| Async hooks are cancelled at session end | same | "When the session ends, Codex cancels unfinished background hooks and discards output that hasn't been delivered." |
| A Stop hook block extends the run | same | "`decision: \"block\"` doesn't reject the turn. Instead, it tells Codex to continue …" |
| Hooks page says nothing about exec behavior | links/19.md: `grep -iE 'non-interactive\|codex exec\|strict-config'` → only the sidebar link (line 53); control `hooks.json` → many | "- [Non-interactive mode](…)" |
| Claude json output | <https://code.claude.com/docs/en/headless#get-structured-output> (links/4.md) | "`json`: structured JSON with result, session ID, and metadata" |
| Where Claude puts schema output | same (links/4.md:124) | "with the structured output in the `structured_output` field." |
| Claude cost field | same (links/4.md:90) | "the response payload includes `total_cost_usd` and a per-model cost breakdown" |
| Claude result fields | `knowledge-base/sources/claude-code-docs/content/en/docs/claude-code/agent-sdk/typescript.md:1237-1291` (mirror commit `1e8a2c489fc9d10df612b4ce19e6a9ad1e555d36`, 2026-09-01) | `subtype: "success"; … duration_ms … is_error … num_turns … result … total_cost_usd … modelUsage … structured_output?` |
| agy json envelope | <https://antigravity.google/docs/cli/headless#json> (links/5.md) | "`usage` … Token counts: `input_tokens`, `output_tokens`, `thinking_tokens`, `cache_read_tokens`, `total_tokens`" |
| agy schema flag | <https://antigravity.google/docs/cli/headless#structured-output-with-a-schema> (links/7.md) | "The flag accepts a schema string, a path to a `.json` schema file, or a primitive type name" |
| agy stream | <https://antigravity.google/docs/cli/headless#streaming-json> (links/6.md, byte-identical to 5.md) | "The stream begins with one `init` event, followed by any number of `step_update` events, and ends with one `result` event" |
| agy soft-deny exits 0 | links/5.md:496 | "A tool that requires approval it can't obtain is soft-denied: the run continues, exits `0`" |
| Offline codex corpus pinned at 0.153.4 | `knowledge-base/sources/codex-docs/docs/freshness.json` (manifest commit `262d53df92e9cf7495206e64e3f6c4edc757116f`) | `"source_ref": "rust-v0.153.4"`, `"last_successful_full_sync_at": "2026-09-09T16:07:05+00:00"` |
| Upstream codex-docs already covers 0.160.0 | `git ls-remote` → `4f2dd1b793dcb0e5fc08d4fe6c76f9b7acb5d3b3`; `gh api repos/chenrui333/codex-docs/contents/docs/freshness.json` | `"last_successful_full_sync_at": "2026-09-30T21:59:07+00:00"`, `"version": "0.160.0"` |
| The task-named offline corpus is superseded and stale | `knowledge-base/sources/agent-harness-docs.manifest` (pin `9625db96360641da03257ea7b01ab5cbbee6410c`, 2026-09-01; clone HEAD `82312cd7861ef348450c5f0dbaa4b54c4cf78038`, 2026-09-15) | "docs/codex/ here is SUPERSEDED by sources/codex-docs.manifest" |
| The task-named offline corpus lacks every new term | `grep -rl` in `agent-harness-docs/docs/codex/`: `agent_message_board`, `analytics_plan_history`, `multi_agent_v2`, `recommended_plugins` and `strict-config` → 0 files each; control `multi_agent` → 5, `hooks.json` → 5 | — |
| Both repos set a key the docs call unavailable | `knowledge-base/.codex/config.toml:267-268`, `dotfiles/.codex/config.toml:14-15` | `[features.context_management]` / `experimental_mode = true` |

**Open issue threads.** Their state was re-read live on 2026-10-03 with `gh api
repos/openai/codex/issues/<n>`. Treat them as *reports*, not as verified behavior.

| # | State | Title |
|---|---|---|
| [49333](https://github.com/openai/codex/issues/49333) | open | `codex exec --ignore-user-config` also skips the project `.codex` layer (hooks and MCP servers), unlike its help text |
| [38545](https://github.com/openai/codex/issues/38545) | open | `codex exec review` accepts but ignores `--output-schema` |
| [35596](https://github.com/openai/codex/issues/35596) | open | codex exec review silently ignores `--output-schema` and writes prose |
| [46210](https://github.com/openai/codex/issues/46210) | open | SessionStart hook in config.toml is silently skipped in codex exec unless `--dangerously-bypass-hook-trust` is set (0.153.4) |
| [47464](https://github.com/openai/codex/issues/47464) | open | `codex exec -s read-only` silently ignored when requirements.toml defines `allowed_permission_profiles` |
| [29857](https://github.com/openai/codex/issues/29857) | open | codex exec silently auto-cancels MCP tool calls regardless of `default_tools_approval_mode` |
| [19816](https://github.com/openai/codex/issues/19816) | open | codex exec `--output-schema` does not apply only to final output |
| [44610](https://github.com/openai/codex/issues/44610) | open | a switch to disable the file watcher for one-shot headless runs |
| [47483](https://github.com/openai/codex/issues/47483) | open | codex exec downloads ~24 MB remote plugin catalog on every cold start |
| [41499](https://github.com/openai/codex/issues/41499) | open | 0.150.1: untrusted project AGENTS.md is included in prompt input |

The rest of the triage list was **not re-read**, and its titles are carried as-is:

- Issues: #47043, #37994, #22148, #46914, #45627, #38850, #21753, #34961
- Discussions: #12463, #26901, #21764, #7740, #46874
- Release: `rust-v0.156.0`

**Full `codex features list` (0.160.0, effective state in the knowledge-base cwd).** This
is a probe output, quoted as stage/effective. The 154 rows split into these groups.

*Stable, effective true:*

- `apps`, `auth_elicitation`, `browser_use`, `browser_use_external`, `browser_use_full_cdp_access`
- `code_mode_host`, `compaction_image_budget`, `computer_use`, `content_item_kinds`
- `daemon_auto_start`, `enable_request_compression`, `fast_mode`, `goals`
- `guardian_approval`, `guardian_reuse_parent_compaction`, `hooks`, `image_generation`
- `in_app_browser`, `in_app_chat`, `in_app_dictation`, `in_app_local_automation`, `in_app_updates`
- `memories`, `mentions_v2`, `multi_agent`, `plugin_sharing`, `plugins`
- `realtime_conversation`, `remote_plugin`, `shell_snapshot`, `shell_tool`
- `skill_mcp_dependency_install`, `skill_search`, `sleep_tool`, `system_proxy_fallback`
- `tool_call_mcp_elicitation`, `tool_suggest`, `unbounded_connection_retries`
- `unified_exec`, `unified_exec_tty`, `view_image`, `workspace_dependencies`, `worktrees`, `write_stdin_approval`

*Stable, effective false:* `multi_agent_v2`, `recommended_plugins`, `secret_auth_storage`.

*Experimental, false:* `analytics_plan_history`, `network_proxy`, `prevent_idle_sleep`.

*Deprecated:* `transcript_v2`, `use_legacy_landlock`, `web_search_cached`,
`web_search_request`.

*Under development, effective true:* `chronicle`, `context_management`.

*Under development, false (the remaining ~60):*

- `agent_message_board`, `api_key_model_discovery`
- `apply_patch_preserve_line_endings`, `apply_patch_streaming_events`
- `artifact`, `background_paginated_rollout_migration`, `bedrock_setup_wizard`
- `code_mode`, `code_mode_interrupt`, `code_mode_only`, `code_mode_prewarm`
- `codex_apps_mcp_2026_07_28`, `concurrent_reasoning_summaries`, `current_time_reminder`
- `cwd_relative_turn_diffs`, `default_mode_request_user_input`, `defer_mailbox_preemption`
- `deferred_executor`, `deferred_tool_world_state`, `enable_mcp_apps`
- `exec_permission_approvals`, `executed_tool_call_metadata`, `executor_capability_discovery`
- `external_agent_memory_import`, `guardian_conversation_history_tools`
- `guardian_enhanced_node_repl_transcripts`, `guardian_node_repl_transcript_images`
- `guardian_root_handoff_context`, `guardianv2`, `image_resize_notice`, `instant_interrupt`
- `local_thread_store_compression`, `mcp_2026_07_28`, `mcp_oauth_refresh_coordination`
- `non_prefixed_mcp_tool_names`, `nonfatal_clock_read_errors`, `omit_app_server_notification_media`
- `powershell_shell_version`, `prefer_mxc`, `psp`, `reasoning_effort_override`
- `request_permissions_tool`, `respect_system_proxy`, `retain_client_developer_messages`
- `rollout_budget`, `runtime_metrics`, `send_message_to_user_async`, `shell_snapshot_v2`
- `shell_zsh_fork`, `skip_host_skill_discovery`, `standalone_web_search`, `step_model_switching`
- `terminal_visualization_instructions`, `token_budget`, `unified_image_budget`
- `use_agent_identity`, `use_xaa`, `windows_sandbox_service`

*Removed (still listed; no hard-fail by name):*

- `apply_patch_freeform`, `apps_mcp_path_override`, `code_mode_buffered_exec`, `codex_git_commit`
- `collaboration_modes`, `elevated_windows_sandbox`, `enable_fanout`, `experimental_windows_sandbox`
- `external_migration`, `guardian_ext`, `guardianv2.thread_context`, `image_detail_original`
- `item_ids`, `js_repl`, `js_repl_tools_only`, `local_thread_store_shared_compression`
- `multi_agent_mode`, `personality`, `plugin_hooks`, `remote_compaction_v2`, `remote_control`
- `remote_models`, `request_rule`, `resize_all_images`, `responses_websockets`, `responses_websockets_v2`
- `search_tool`, `send_async_message`, `skill_env_var_dependency_prompt`, `sqlite`, `steer`
- `terminal_resize_reflow`, `tool_search`, `tool_search_always_defer_mcp_tools`, `tui_app_server`
- `unavailable_dummy_tools`, `undo`, `unified_exec_zsh_fork`, `use_linux_sandbox_bwrap`
- `workspace_owner_usage_nudge`

### Code search

The manifests are under
`dotfiles/.agent/kb/raw/research-fanout/codex-exec-output-schema/manifest.json` and
`.../codex-features-feature-flags-config-toml/manifest.json`.

| Query | Role | Source | Count | rc |
|---|---|---|---|---|
| `multi_agent_v2 filename:config.toml` | query | planner | 280 | 0 |
| `output-schema language:yaml` | query | planner | 2008 | 0 |
| `PreToolUse filename:hooks.json path:.codex` | query | planner | 2428 | 0 |
| `model filename:config.toml` | must-hit | planner | 36288 | 0 |
| `codex language:yaml` | must-hit | planner | 241152 | 0 |
| `command filename:hooks.json path:.codex` | must-hit | planner | 4248 | 0 |
| `zqvxjw7trk9plmnb3` | known-absent | planner | 0 (expected: this is the known-absent control) | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:openai/codex filename:README.md` | must-hit | workflow | 54 | 0 |

Note: no CODE SEARCH NOTES were supplied for this run. The `output-schema language:yaml`
count of 2008 is inflated by noise. GitHub's legacy code tokenizer splits `output-schema`
on the `-`, so many hits match only `output` or `schema`. The saved search in §B adds
`"codex exec"` and `path:.github/workflows` to discriminate.

### Dependency-repo fan-out

| Repo | Query | Required sources failed | Manifest |
|---|---|---|---|
| openai/codex | `codex exec non-interactive config` | none | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/research--kb--reports--agents--codex-noninteractive-settings-2026-10-03/deps/openai--codex/1/manifest.json` |
| openai/codex | `claude-code` | github-releases: error (exited 1: stream error: stream ID 1; CANCEL; received from peer) | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/research--kb--reports--agents--codex-noninteractive-settings-2026-10-03/deps/openai--codex/2/manifest.json` |
| anthropics/claude-code | (not run) | no PROBE-JSON line recorded | `.agent/kb/raw/research-fanout/research--kb--reports--agents--codex-noninteractive-settings-2026-10-03/deps/anthropics--claude-code/probe.json` (missing) |

### Offline mirrors

The mirror root is
`dotfiles.worktrees/codex-noninteractive-research/docs/research/kb/raw/research--kb--reports--agents--codex-noninteractive-settings-2026-10-03/links/`.

| Link | Mirror file | rc | Bytes | Failure |
|---|---|---|---|---|
| <https://learn.chatgpt.com/docs/non-interactive-mode> | links/1.md | 0 | 16944 | — |
| …non-interactive-mode#make-output-machine-readable | links/2.md | 0 | 16944 | — (same page as 1.md) |
| …non-interactive-mode#create-structured-outputs-with-a-schema | links/3.md | 0 | 16944 | — (same page as 1.md) |
| <https://code.claude.com/docs/en/headless#get-structured-output> | links/4.md | 0 | 35310 | — |
| <https://antigravity.google/docs/cli/headless#json> | links/5.md | 0 | 30605 | — |
| …headless#streaming-json | links/6.md | 0 | 30605 | — (byte-identical to 5.md) |
| …headless#structured-output-with-a-schema | links/7.md | 0 | 30605 | — (same page) |
| …developer-commands?surface=cli#cli-flag-combinations-and-safety-tips | links/8.md | 0 | 105216 | — |
| …developer-commands?surface=cli#cli-global-flags | links/9.md | 0 | 105216 | — (byte-identical to 8.md) |
| <https://learn.chatgpt.com/docs/config-file> | links/10.md | 0 | 0 | HTTP 404 |
| …config-file/config-basic | links/11.md | 1 | 0 | firecrawl rate limit (11 req/min consumed) |
| …config-file/config-advanced | links/12.md | 1 | 0 | firecrawl rate limit |
| …config-file/config-reference | links/13.md | 1 | 0 | firecrawl rate limit |
| …config-file/environment-variables | links/14.md | 1 | 0 | firecrawl rate limit |
| …config-file/config-sample | links/15.md | 1 | 0 | firecrawl rate limit |
| …agent-configuration/agents-md | links/16.md | 1 | 0 | firecrawl rate limit |
| …agent-configuration/subagents?surface=cli | links/17.md | 0 | 23026 | — |
| …agent-configuration/rules | links/18.md | 1 | 0 | firecrawl rate limit |
| <https://learn.chatgpt.com/docs/hooks> | links/19.md | 0 | 44120 | — |

## Verification

Five load-bearing claims were each re-probed by an independent refuter (binary plus source), then an adjudicator re-ran the contested ones. Critic: ran (15 gaps, appended to Gaps). Adjudicator: ran.

| # | Claim | Result | Evidence and effect |
|---|---|---|---|
| 1 | `codex exec --full-auto` is rejected by 0.160.0 (rc 2), like a bogus flag, while `--experimental-json` is accepted; docs say it warns | **Confirmed** | Re-probed: rc 2 `unexpected argument '--full-auto' found` with and without `--help`, identical to `--zzbogus-flag`; `--experimental-json --help` rc 0; source `cli.rs:61` has the alias, zero `full-auto` hits in codex-rs. Nuance: bare `exec --experimental-json` with no stdin is rc 1 (no prompt); rc 0 holds only for `--help`. The source clone pin may predate 0.160.0, so the code route only corroborates; the removal changelog was not read (Gap 1). No change to the conclusion. |
| 2 | Top-level `codex review` has no `--json`, `--output-schema`, `-o`, `--sandbox`; machine output needs `codex exec review` | **Confirmed**; refuter said misleading, **overturned by the adjudicator** | Help output and source (`ReviewCommand` plus `ReviewArgs`) agree. Adjudicator: the omissions are side notes. Kept as a minor qualification only: root options given before `review` (`-s`, `-m`, `-c`) are inherited, `exec review` also lacks `-s`, and prompt conflicts with `--uncommitted/--base/--commit`. Conclusion unchanged. |
| 3 | `multi_agent_v2` and `recommended_plugins` Stable/false; `agent_message_board` UnderDevelopment/false; `analytics_plan_history` Experimental/false | **Confirmed**; refuter said misleading, **overturned by the adjudicator** | `lib.rs` at rust-v0.160.0 and `codex features list` agree on all four. Control: `multi_agent` is Stable/true. Context kept in the table: Stable is not on, `multi_agent_v2` takes a table, `recommended_plugins` needs Apps+Plugins, "TUI" is inferred, defaults are compile-time. Conclusion unchanged. |
| 4 | `--strict-config` is per-command and not listed by `codex features --help` | **UPHELD misleading** (literal claim true) | `features --strict-config list` fails with unexpected argument; `resume --help` lists it. But `features` is not the only exception: the root flag is gated by a whitelist that hard-rejects `mcp`, `login`, `plugin`, `sandbox`, `cloud`, `debug`, `apply`, `completion`, `update`, and more accept it than the 4 named (`resume`, `fork`, `agents`, `exec-server`, `doctor`, `archive`...). The cited L314/L394/L562 are not exec or the root flag. **Qualified in Answer §1, Conflicts item 2 and the recommendation.** Effect: a wrapper adding `--strict-config` to every codex call would break `mcp`/`login`/`plugin`/`sandbox`; apply it only to whitelisted commands. |
| 5 | `codex exec --json` has no `structured_output`, cost or duration field; with `--output-schema` the final `agent_message` text is the JSON | **Confirmed**; refuter said misleading, **overturned by the adjudicator** | Docs events plus `exec_events.rs` (`TurnCompletedEvent{usage}`, `AgentMessageItem{text}`); no cost/duration anywhere. The report already covers token usage, `-o`, and wrapper-derived duration. Added a note in the §3 table that cost and duration must be computed by the wrapper. Refuter note: some mirror `links/N.md` files did not map to the stated pages in its worktree, so it verified against the live URL. |

Other claims in the Evidence table were not re-probed this round and remain as originally graded (documented or probed once). The strict-config effect on both repos' configs, hook behaviour under exec, real JSONL wire format, agy output and the saved-search results are **unverified** (Gaps 3-8, 12).

**How the conclusion changes.** The headline holds: `--full-auto` is gone, machine output needs `exec`/`exec review`, the four named features are all off by default, and the unified schema must derive cost and duration. The one real change is operational: `--strict-config` must be applied per whitelisted subcommand rather than as a blanket wrapper flag. The sweep remains **INCOMPLETE** (the two mandatory stage gaps above stand), and the recommended flag set is still unproven until Gap 6 is probed.

## Conflicts resolved

1. **`--full-auto` exists (docs) vs. it does not (binary).** The non-interactive and
   developer-commands pages say it is a deprecated flag that warns. The 0.160.0 binary
   rejects it with rc 2, exactly like a bogus flag, while the alias control gives rc 0.
   **I trusted the binary.** It is the artifact that runs, and the probe discriminates.
   This matches `ai-cli-invocation.md` (hard error on 0.152.0). The docs are stale.
2. **Is `--strict-config` global?** The docs list it under "global flags". The source
   declares it per struct, and the binary's `codex features --help` omits it. **Resolved:
   it is accepted by a whitelist (exec, exec review, review, top level, resume, fork,
   agents, exec-server, doctor, archive and others) and hard-rejected by `features`, `mcp`,
   `login`, `plugin`, `sandbox` and more.** I trusted the source and binary over the docs.
   (Corrected after verification: the original text named only `features` as an exception.)
3. **Scope of `CODEX_API_KEY`.** The live learn.chatgpt.com pages (2026-10-03) say it
   covers exec, review, the TS SDK and `exec-server --remote`. A claim citing
   developers.openai.com says "only supported in `codex exec`"; that page was not
   mirrored and its date is unknown. **I trusted the newer learn.chatgpt.com text.** It
   is still unverified at the binary level, because `strings` shows the name but not
   where it is consumed.
4. **Hook event count: 11 vs 12.** The developers.openai.com claim omits `Interrupt`. The
   learn.chatgpt.com mirror links/19.md lists 12. **I trusted links/19.md**, which is
   newer and mirrored with bytes.
5. **"Project-level `.codex/AGENTS.md`" and "`agents/*.toml` per the agents-md page".**
   These are secondary-reader claims citing developers.openai.com. They contradict the
   agents-md page, where AGENTS.md lives in repo directories, and the subagents page,
   where custom agents live in `.codex/agents/*.toml`. **I trusted the primary pages.**
6. **The feature tables.** The live config-basic and config-reference pages name
   `personality` as a flag and `memories` as off. The binary lists `personality` as
   **removed**, and `memories` as stable with effective **true**. The "effective" column
   includes user config, so this does not prove the default. **For stage, I trusted the
   binary.** The `memories` default is unresolved (see Gaps). The docs also list
   `web_search` as deprecated, but the binary has no `web_search` key, only
   `web_search_cached` and `web_search_request`.
7. **`features.context_management.experimental_mode`.** config-reference says "not
   available", yet both repos set it, and the binary shows `context_management` as under
   development with effective **true**. Either the key works or it is silently ignored.
   This is unresolved. The probe is `codex exec --strict-config` from each repo (see
   Gaps).
8. **`--output-schema` on `codex exec review`.** The source accepts it, because the flag
   is `global = true`. Two open issues (#38545 for 0.148, #35596 for 0.145) say it is
   ignored. **Source shows acceptance only.** It does not show that the schema is applied.
   The issues are older than 0.160.0 and still open, so I treat them as **unverified,
   likely still true**. Don't rely on it until it is tested.
9. **Offline corpus vs. live.** The task named `sources/agent-harness-docs/docs/codex/`
   (126 pages). Its own manifest says it is **superseded** by `sources/codex-docs`, and it
   has 0 hits for every 0.160.0-era term. `sources/codex-docs` is pinned at **0.153.4**,
   while upstream `chenrui333/codex-docs` already synced **0.160.0** on 2026-09-30.
   **I trusted the live and mirror pages and the binary over both local corpora.**

## Gaps

These are named gaps, not "nothing found".

- **MANDATORY: GitHub Releases for openai/codex were never read.** The stage failed with
  `stream ID 1; CANCEL`. The 0.153 to 0.160 changelog was therefore not reviewed. Re-run
  `gh api repos/openai/codex/releases --paginate`.
- **MANDATORY: no `anthropics/claude-code` dependency probe ran.** The Claude side of the
  unified schema rests on the headless mirror (links/4.md) and the 2026-09-01
  claude-code-docs mirror. It was never checked against the current CLI.
- **unverifiedEmpty: github-releases (codex-exec-output-schema).** Status was error, with
  0 items. That count is unknown, not zero.
- **unverifiedEmpty: github-releases (deps/openai--codex/2, query claude-code).** Status
  was error, with 0 items. Unknown.
- **Mirror gaps:**
  - `config-file` gave HTTP 404. The page does not exist at that URL; the subpages are
    the real content.
  - `config-basic`, `config-advanced`, `config-reference`, `environment-variables`,
    `config-sample`, `agents-md` and `rules` were not mirrored because of the firecrawl
    rate limit. They were read live, so their quotes have **no byte-stable offline
    copy**. Re-mirror them.
- **Code search gaps:** none were reported. Every row is armed or a control.
- **The real wire format of `codex exec --json` was not captured.** No model call was
  made, to avoid spend. The documented sample is the only evidence, so each of these is
  unverified for 0.160.0:
  - the `item.*` subtypes
  - whether any duration field exists
  - where schema output lands
- **The binary behaviour of `--strict-config` with both repos' configs was not probed.**
  Resolving the `context_management` and `[tools.update_plan]` questions needs a real
  exec run from each repo. It also needs project trust, because an untrusted project
  layer is skipped before strict checking.
- **Unknown default for `memories`.** `codex features list` shows the effective state
  only. Read `features/src/lib.rs` at the tag for `Feature::Memories`.
- **`default_features` vs effective state.** All the effective-state values above were
  taken in the knowledge-base cwd. The dotfiles cwd was not listed.
- **Upstream changes on main after the tag (`rust-v0.160.0...main`) are unverified.** The
  shallow clone could not resolve the range. No merged-but-unreleased claims are made.
- **Hook behaviour under exec** is undocumented and was not tested here. That covers the
  trust prompt, `SessionEnd` timing, and cancellation of async hooks. #46210 is a report
  only.
- **Issue bodies were not read.** Only state and title were checked.

### Critic gaps (appended by reconcile)

1. GitHub Releases for openai/codex 0.153 to 0.160 never read (stream CANCEL), so the changelog behind flag removals such as `--full-auto` is unconfirmed. Next: `gh api repos/openai/codex/releases --paginate --jq '.[]|select(.tag_name|test("rust-v0.1(5[3-9]|60)"))|{tag_name,published_at,body}'`, then grep bodies for full-auto, strict-config, multi_agent_v2, output-schema, hook-trust.
2. No anthropics/claude-code dependency probe; the Claude side of the unified schema rests on a docs mirror and a 2026-09-01 SDK doc, never checked against the installed CLI. Next: `claude --version`, `claude -p 'say ok' --output-format json --json-schema '{...}'` and `--output-format stream-json --verbose`, diff the real field set; read anthropics/claude-code releases and issues.
3. Real `codex exec --json` wire format never captured; item.* subtypes, any duration/model field and where `--output-schema` output lands are documented-only, so the unified schema's codex mapping (num_turns, model, derived duration) is speculative. Next: one cheap `codex exec --json --output-schema s.json --strict-config` run, save the JSONL, cross-check `exec/src/exec_events.rs` at the tag.
4. agy side never run live; envelope fields come from docs only; the soft-deny exit-0 claim and status enum are unverified. Next: `agy --version`, `agy -p ... --output-format json` and `stream-json` with a schema; test a denied tool.
5. Whether `codex exec review --output-schema` is applied is unverified (source shows acceptance only; #38545 and #35596 say ignored, bodies unread, issues predate 0.160.0). Next: read both issues and linked PRs, run it on a trivial diff.
6. `--strict-config` effect on both repos' configs (`features.context_management.experimental_mode`, `[tools.update_plan]`) unprobed; the recommended flag set is gated on it. Next: `codex exec --strict-config -c approval_policy='"never"' 'noop'` from each trusted repo; check key against codex-rs/config types.
7. `memories` default and the four flags' defaults were read from source only; effective state was taken in the knowledge-base cwd only. Next: `codex features list` from dotfiles and with `--ignore-user-config`; grep `Feature::Memories` default_enabled at the tag.
8. Hook behaviour under exec (trust prompt, SessionEnd timing, async cancel, #46210) untested; the `--dangerously-bypass-hook-trust` recommendation rests on one open issue and its security implications for the guard stack are unassessed. Next: throwaway SessionStart marker hook, run with and without the bypass; read #46210.
9. Seven live-read pages (config-basic, config-advanced, config-reference, environment-variables, config-sample, agents-md, rules) have no byte-stable mirror, and "every config key / env var" was never enumerated. Next: re-mirror with a rate-limit pause; generate the key list from the source schema at the tag and diff against config-reference.
10. Offline freshness checked only indirectly (`sources/codex-docs` at 0.153.4 vs upstream 0.160.0); upstream `docs/cli-surface/*.json` and `lifecycle.md` not diffed against the binary. Next: fetch chenrui333/codex-docs at 4f2dd1b and diff.
11. Undocumented env vars come from `strings` only (lower bound); consumers and semantics unverified (CODEX_EXEC_SERVER_URL, CODEX_AUTH, CODEX_GITHUB_PERSONAL_ACCESS_TOKEN...); CODEX_API_KEY scope conflict resolved by recency only. Next: grep source at the tag for each name with file:line.
12. Saved GitHub searches were not executed with results recorded; only planner counts exist for 4 of ~25 queries; I1, I2, P1, D1 have no counts, controls or `incomplete_results`; discussions and #47043 etc. never re-read. Next: execute every section B query and its control via `gh api`, record `total_count` and `incomplete_results`.
13. Merged-but-unreleased changes after rust-v0.160.0 unchecked; PR #47017 (agent_message_board) is cited as wired into runtimes without confirming it shipped in 0.160.0. Next: unshallow or `gh api repos/openai/codex/compare/rust-v0.160.0...main`.
14. The unified schema was never validated as JSON Schema or run against real captured outputs; no consumer in either repo is cited. Next: capture one output per CLI, write adapters, validate with check-jsonschema, grep both repos for existing wrappers.
15. The side-agent note (stash of the uncommitted `.codex/config.toml` edit near line 266 in knowledge-base) is not reconciled: the report cites knowledge-base `.codex/config.toml:267-268`, which may be the stashed or unstashed state. Next: `git stash list` / `git stash show -p` and confirm lines 266-268 exist on the probed branch.

## Recommendation

### A. Refresh the offline corpus first (knowledge-base)

1. Run `mise run kb-update -- codex-docs`. It moves from 0.153.4 to the upstream 0.160.0
   sync at `4f2dd1b793dcb0e5fc08d4fe6c76f9b7acb5d3b3`, which carries
   `docs/feature-flags/lifecycle.md` and `docs/cli-surface/*.json`.
2. Re-mirror the seven rate-limited pages through `mise run kb-add` with a pause between
   requests. This keeps to Invariant 5: no ad-hoc fetch as the final home.
3. Stop pointing research at `sources/agent-harness-docs/docs/codex/`, because its own
   manifest says it is superseded.

### B. Saved GitHub searches

All of these can be tuned and re-run. Each row is a **query/control pair**. Before you
report any zero, check `incomplete_results` and the control count. Use `gh api`, not
`gh search`. To keep `incomplete_results`, project with `--jq '{total_count,
incomplete_results}'`, never with `.items` alone.

```bash
# --- CODE (REST search/code; legacy tokenizer splits on - and .) ---
# S1 multi_agent_v2 in project configs        | control C1
gh api -X GET search/code -f q='multi_agent_v2 path:.codex filename:config.toml' --jq '{total_count,incomplete_results}'
gh api -X GET search/code -f q='model path:.codex filename:config.toml'          --jq '{total_count,incomplete_results}'
# S2 other named features (tune the term)     | control C1
gh api -X GET search/code -f q='recommended_plugins filename:config.toml'        --jq '{total_count,incomplete_results}'
gh api -X GET search/code -f q='agent_message_board filename:config.toml'        --jq '{total_count,incomplete_results}'
# S3 codex exec with --output-schema in CI     | control C3
gh api -X GET search/code -f q='"codex exec" output-schema path:.github/workflows language:yaml' --jq '{total_count,incomplete_results}'
gh api -X GET search/code -f q='"codex exec" path:.github/workflows language:yaml'               --jq '{total_count,incomplete_results}'
# S4 --strict-config in the wild               | control C3
gh api -X GET search/code -f q='"codex exec" strict-config path:.github/workflows'                --jq '{total_count,incomplete_results}'
# S5 project hooks.json using PreToolUse       | control C5
gh api -X GET search/code -f q='PreToolUse path:.codex filename:hooks.json'      --jq '{total_count,incomplete_results}'
gh api -X GET search/code -f q='command path:.codex filename:hooks.json'         --jq '{total_count,incomplete_results}'
# S6 execpolicy rules                          | control C6
gh api -X GET search/code -f q='prefix_rule path:.codex/rules extension:rules'   --jq '{total_count,incomplete_results}'
gh api -X GET search/code -f q='pattern extension:rules'                         --jq '{total_count,incomplete_results}'
# S7 custom agents                             | control C7
gh api -X GET search/code -f q='developer_instructions path:.codex/agents extension:toml' --jq '{total_count,incomplete_results}'
gh api -X GET search/code -f q='name path:.codex/agents extension:toml'                   --jq '{total_count,incomplete_results}'
# S8 cross-CLI structured output (unified-schema prior art) | control C3-style
gh api -X GET search/code -f q='"--json-schema" "claude -p" path:.github/workflows'  --jq '{total_count,incomplete_results}'
gh api -X GET search/code -f q='agy "--output-format" stream-json'                   --jq '{total_count,incomplete_results}'

# --- ISSUES / PRs (REST search/issues) ---
# I1 exec + output-schema bugs                 | control I0 (must be >0)
gh api -X GET search/issues -f q='repo:openai/codex is:issue "output-schema" in:title,body' --jq '{total_count,incomplete_results}'
gh api -X GET search/issues -f q='repo:openai/codex is:issue "codex exec" in:title'         --jq '{total_count,incomplete_results}'
# I2 hook trust under exec
gh api -X GET search/issues -f q='repo:openai/codex is:issue "bypass-hook-trust"'           --jq '{total_count,incomplete_results}'
# P1 merged PRs touching the flags/features (source beats issues)
gh api -X GET search/issues -f q='repo:openai/codex is:pr is:merged "strict-config"'        --jq '{total_count,incomplete_results}'
gh api -X GET search/issues -f q='repo:openai/codex is:pr is:merged multi_agent_v2'         --jq '{total_count,incomplete_results}'
gh api -X GET search/issues -f q='repo:openai/codex is:pr is:merged output_schema exec'     --jq '{total_count,incomplete_results}'

# --- DISCUSSIONS (GraphQL only; REST has no discussion search) ---
# D1 exec automation threads                   | control D0
gh api graphql -f query='query($q:String!){search(query:$q,type:DISCUSSION,first:50){discussionCount nodes{... on Discussion{url title createdAt}}}}' -F q='repo:openai/codex "codex exec"'
gh api graphql -f query='query($q:String!){search(query:$q,type:DISCUSSION,first:50){discussionCount nodes{... on Discussion{url title createdAt}}}}' -F q='repo:openai/codex config'

# --- RELEASES (the stage that FAILED this run) ---
gh api repos/openai/codex/releases --paginate --jq '.[] | select(.tag_name|startswith("rust-v0.15") or startswith("rust-v0.16")) | {tag_name,published_at}'
```

### C. Proposed unified cross-CLI output schema (JSON Schema 2020-12)

Normalisation rules:

- Every field in the core is **derived**.
- Each CLI's native payload is kept **verbatim** under `extensions.<cli>.raw`. That way
  no field any CLI emits is ever lost.
- `null` means the CLI does not report the field. It never means zero. For example,
  `cost_usd` is `null` for codex and agy.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/ray-manaloto/knowledge-base/schemas/agent-run-result.schema.json",
  "title": "AgentRunResult",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "cli", "status", "is_error", "exit_code", "session_id", "result_text", "structured_output", "usage", "cost_usd", "extensions"],
  "properties": {
    "schema_version": { "const": "1" },
    "cli": { "enum": ["codex", "claude", "agy"] },
    "cli_version": { "type": ["string", "null"] },
    "model": { "type": ["string", "null"], "description": "codex: null unless the caller passed -m (exec --json does not report it); claude: system/init.model; agy: init.model when overridden" },
    "session_id": { "type": ["string", "null"], "description": "codex thread.started.thread_id | claude session_id | agy conversation_id" },
    "status": { "enum": ["success", "error", "canceled", "interrupted", "invalid", "max_turns", "max_budget", "schema_retries_exhausted", "timeout", "unknown"],
      "description": "codex: turn.completed->success, turn.failed/error->error; claude: subtype success|error_max_turns->max_turns|error_max_budget_usd->max_budget|error_max_structured_output_retries->schema_retries_exhausted|error_during_execution->error; agy: SUCCESS|ERROR|CANCELED|INTERRUPTED|INVALID lower-cased; timeout = wrapper-imposed" },
    "is_error": { "type": "boolean" },
    "exit_code": { "type": "integer", "description": "process rc as observed by the wrapper; agy soft-denials exit 0, so check permission_denials" },
    "result_text": { "type": ["string", "null"], "description": "codex last agent_message item .text (or -o file) | claude result | agy response" },
    "structured_output": { "description": "parsed JSON when a schema was supplied, else null. codex: JSON.parse(result_text); claude/agy: structured_output", "type": ["object", "array", "string", "number", "integer", "boolean", "null"] },
    "schema_supplied": { "type": "boolean" },
    "num_turns": { "type": ["integer", "null"], "description": "codex: count of turn.completed events (derived); claude/agy: num_turns" },
    "duration_ms": { "type": ["integer", "null"], "description": "claude duration_ms | agy duration_seconds*1000 | codex: wrapper wall clock" },
    "usage": {
      "type": "object",
      "additionalProperties": false,
      "required": ["input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens", "total_tokens"],
      "properties": {
        "input_tokens": { "type": ["integer", "null"] },
        "output_tokens": { "type": ["integer", "null"] },
        "cached_input_tokens": { "type": ["integer", "null"], "description": "codex cached_input_tokens | claude cache_read_input_tokens | agy cache_read_tokens" },
        "reasoning_tokens": { "type": ["integer", "null"], "description": "codex reasoning_output_tokens | agy thinking_tokens | claude null" },
        "total_tokens": { "type": ["integer", "null"], "description": "agy total_tokens; else sum of the above when all are non-null" }
      }
    },
    "cost_usd": { "type": ["number", "null"], "description": "claude total_cost_usd (client estimate); codex and agy: null" },
    "permission_denials": { "type": ["array", "null"], "items": { "type": "object" } },
    "error": {
      "type": ["object", "null"],
      "additionalProperties": true,
      "properties": { "type": { "type": "string" }, "message": { "type": "string" } }
    },
    "extensions": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "codex": { "type": "object", "properties": { "events": { "type": "array", "items": { "type": "object", "required": ["type"] } }, "items_by_type": { "type": "object" } }, "additionalProperties": true },
        "claude": { "type": "object", "properties": { "raw": { "type": "object" }, "modelUsage": { "type": "object" }, "stop_reason": { "type": ["string", "null"] }, "terminal_reason": {}, "duration_api_ms": { "type": "integer" } }, "additionalProperties": true },
        "agy": { "type": "object", "properties": { "raw": { "type": "object" }, "json_schema": {}, "permission_mode": { "type": "string" }, "steps": { "type": "array" } }, "additionalProperties": true }
      }
    }
  }
}
```

**Placement.** In knowledge-base this belongs in `schemas/agent-run-result.schema.json`.
Generate the msgspec model with `mise run kb-codegen`, following the codegen-owns-types
rule. The adapter belongs in a `kb_setup` module with a mise task, never shell. dotfiles
would consume it as it consumes `kb_setup.currency`.

### D. Proposed non-interactive codex config and flags for both repos (not applied)

**Invocation (the wrapper owns it; the same for both repos).**

```bash
echo "$PROMPT" | codex exec \
  --strict-config \
  --sandbox workspace-write \
  --add-dir "$HOME/Library/Caches" \
  -c approval_policy='"never"' \
  --json -o "$RUN_DIR/last-message.txt" \
  [--output-schema "$RUN_DIR/schema.json"] \
  [-c sandbox_workspace_write.network_access=true]   # only lanes that fetch
  [--dangerously-bypass-hook-trust]                   # only lanes that must run repo hooks
  [--enable multi_agent_v2]                           # trial only, see below
  -
```

Rules behind each choice:

- **`--strict-config`, always.** An unknown key then fails loudly instead of being
  silently ignored. That is the zero-skip policy applied to config.
  - **Prerequisite:** first resolve `features.context_management.experimental_mode`
    (both repos) and `[tools.update_plan]` (knowledge-base). Either they pass strict
    checking or they are removed.
- **Never `--full-auto`.** It hard-errors on 0.160.0.
- **Never `--ephemeral`.** This repo's rule needs sessions to be reviewable, and
  agentsview reads `~/.codex/sessions/`.
- **Never `--sandbox` together with `--dangerously-bypass-approvals-and-sandbox`.** See
  `do-not.md` #12.
- **Never `--ignore-user-config` for a lane that needs project hooks or MCP.** #49333
  reports that it also drops the project `.codex` layer. Re-test before relying on either
  reading.
- **`codex exec review --json`, not top-level `codex review`, for machine output.** Do
  not trust `--output-schema` there (#38545, #35596). Parse the final `agent_message`
  from the event stream instead.
- **Approval: use `-c approval_policy="never"`, not `--ask-for-approval`.** exec rejects
  `--ask-for-approval`. Subagent approvals fail outright in exec, so a pre-set policy is
  required.

**Project `.codex/config.toml` (both repos).**

- Keep it minimal. It applies to interactive runs too, and it loads only in a **trusted**
  project.
- Do NOT move `approval_policy` or `sandbox_mode` here. Set them per invocation.
- Keep `[agents].default_subagent_model` and `default_subagent_reasoning_effort` where
  they are already set.
- Add `project_doc_max_bytes` only if AGENTS.md plus its nested files approach 32 KiB.
  Measure first.

**Profiles.** **Do not** adopt a `--profile`. The profile file must live at
`$CODEX_HOME/<name>.config.toml`, which is user-global (`do-not.md` #11). Pointing
`CODEX_HOME` at the repo would also move auth. Use `-c` overrides in the wrapper instead.

**Features.**

| Feature | Proposal | Reason |
|---|---|---|
| `multi_agent_v2` | **Trial** per invocation (`--enable multi_agent_v2`) on one lane; commit nothing until it is measured | Stable but default-off; changes the subagent runtime |
| `agent_message_board` | **Leave off** | Under development; depends on v2 runtimes |
| `analytics_plan_history` | **Leave off** (irrelevant headless) | TUI `/analytics` only |
| `recommended_plugins` | **Leave off** | Suggestion UX; no headless value |
| `hooks` | keep the default (on) | Needed for the guard stack; trust is still per hash |

**Hooks and rules.**

- Keep `.codex/hooks.json` and use git-root-anchored commands. The hooks page recommends
  this because exec may start in a subdirectory.
- For lanes that rely on hooks, pass `--dangerously-bypass-hook-trust`. Per-hash trust
  lives in user config, which this repo may not write, and #46210 reports `SessionStart`
  being skipped in exec without the bypass.
- Add `.codex/rules/*.rules` only alongside `codex execpolicy check` tests in hk, so the
  inline `match` / `not_match` examples are gated.

**Environment.**

- Never set `CODEX_API_KEY` job-wide. These lanes are subscription-auth.
- Leave `RUST_LOG` at the exec default (`error`) unless you are debugging.

## Provenance

Every node that ran, including the reconcile node. No stage failed outright at the workflow level (FAILED STAGES: none); the two MANDATORY gaps above are inside the dependency stages.

| Node | Agent type | Model | Effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:openai/codex | general-purpose | sonnet | low |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| mirror:1/19 ... mirror:19/19 (19 nodes) | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 ... read-link:7 (7 nodes) | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| source-dive | general-purpose | sonnet | medium |
| synthesize (also ran the binary probes) | general-purpose | opus | high |
| refute:1/5 ... refute:5/5 (5 nodes) | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile (this edit) | general-purpose | sonnet | medium |

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex): clap definitions, the features registry, the issue states at `rust-v0.160.0`, and the triaged issues and discussions.
- [chenrui333/codex-docs](https://github.com/chenrui333/codex-docs): the offline codex docs mirror (`sources/codex-docs.manifest`), pinned at 0.153.4 while upstream is at 0.160.0.
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs): the task-named offline corpus. Its manifest says it is superseded for codex.
- [anthropics/claude-code](https://github.com/anthropics/claude-code): named as a dependency target. Its probe **did not run**, so it was not read.
- [cli/cli](https://github.com/cli/cli): health-control repo for the code-search arm only.

## Gap closure (added after the run, 2026-10-03, by the calling session)

The run returned `status: mandatory-gap`. These were closed by hand afterwards. Everything else above is unchanged.

| Gap | Action | Result |
|---|---|---|
| 6 caller links not mirrored (firecrawl rate limit): 11 config-basic, 12 config-advanced, 13 config-reference, 14 environment-variables, 15 config-sample, 16 agents-md; and 18 rules | Re-fetched one at a time with an 8 s spacing, through `mise run research-fanout -- --probe-out <n>.probe.json --mirror-url U --mirror-path <n>.md`, then rebuilt the index with `--mirror-index ... --mirror-count 19` (rc 0) | All 7 rc 0: 13,609 / 47,272 / 195,435 / 6,953 / 34,934 / 10,145 / 8,799 bytes. `links/README.md` now lists 18 of 19 mirrored. |
| 10 `https://learn.chatgpt.com/docs/config-file` (HTTP 404) | Control-armed with curl: this URL gives 404, the known-good `config-file/config-basic` gives 200, and a bogus `docs/bogus-zzq` gives 404 | A **real 404**: the index page does not exist. Its five sub-pages are all mirrored. |
| `anthropics/claude-code` dependency fan-out (no PROBE-JSON) | `mise run research-fanout -- "codex" --repo anthropics/claude-code --sources github-issues,github-discussions,github-releases` gave rc 0 | issues `ok` (10 hits, all off-topic for this question); releases `empty_verified`; discussions `empty_unverified`, but `gh api repos/anthropics/claude-code --jq .has_discussions` gives `false`, so that is a disabled tracker (a note, not a gap). Manifest: `.agent/kb/raw/research-fanout/codex/manifest.json` (worktree). |
| `openai/codex` github-releases error (stream CANCEL) | `mise run research-fanout -- "exec output-schema strict-config" --repo openai/codex --sources github-releases` gave rc 0 (one hit, rust-v0.158.0), plus a direct `gh api repos/openai/codex/releases/tags/rust-v<v>` for 0.156.0 through 0.160.0 (all rc 0) | The bodies are saved under `raw/codex-noninteractive-settings-2026-10-03/releases/`. A keyword skim (exec, strict-config, output-schema, features, hooks, `--json`, review) found only exec-server, Guardian and unified-exec internals. **No change to a CLI flag, feature default or output field that alters a conclusion above was seen**, though that is a skim and not a full read. |

The binary evidence the calling session captured independently is under `raw/codex-noninteractive-settings-2026-10-03/binary/`:

- `codex features list` (154 rows, rc 0)
- `--help` for all 28 top-level subcommands and their sub-subcommands
- `strings`-derived `CODEX_*` names (17) and `OPENAI_*` names (1)
