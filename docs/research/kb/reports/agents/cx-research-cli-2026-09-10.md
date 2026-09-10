# Codex CLI Surface Research — 0.154.0

**Date:** 2026-09-10  
**Version:** 0.154.0  
**Scope:** Exhaustive documentation of all codex CLI subcommands, flags, and invocation patterns  
**Status:** IN PROGRESS

## Executive Summary

Codex 0.154.0 is verified working. The CLI structure has expanded significantly with explicit subcommands for execution modes (`codex exec`, `codex review`) alongside the top-level interface. Key changes vs prior documentation:

- `-p` flag **still exists** and means `--profile` (not `-p` as "prompt" — that was a misunderstanding)
- `--full-auto` is **GONE** — replaced by explicit `--approve-for-me` and `--dangerously-bypass-approvals-and-sandbox`
- `--sandbox` flag **exists and works** with three values: `read-only`, `workspace-write`, `danger-full-access`
- Stdin via `-` **is the documented pattern** for reading prompts (CORRECT in existing docs)
- Output capture via `-o, --output-last-message <FILE>` captures the agent's final message to a file (not stdout streaming)

---

## Top-Level Commands

### Root: `codex [OPTIONS] [PROMPT]`

**Behavior:** If a subcommand is specified, routes to it. If no subcommand is given, options are forwarded to the interactive CLI.

### Main Subcommands (by category)

#### Core Execution
- **`codex exec`** — Run non-interactively (aliases: `e`)
- **`codex review`** — Code review non-interactively
- **`codex interactive` (implied)** — No explicit subcommand; enters TUI

#### Session Management
- **`codex agents`** — Browse all agent sessions on the app-server daemon
- **`codex resume`** — Resume a previous interactive session (picker by default)
- **`codex fork`** — Fork a previous interactive session
- **`codex queue`** — Queue a message for an existing session
- **`codex archive`** — Archive a saved session by id or name
- **`codex unarchive`** — Unarchive a saved session
- **`codex delete`** — Permanently delete a saved session
- **`codex migrate-rollouts`** — Inspect/migrate legacy local sessions to paginated history

#### Authentication & Config
- **`codex login [OPTIONS] [COMMAND]`** — Manage login (subcommands: `status`)
  - `--with-api-key` — Read API key from stdin
  - `--with-access-token` — Read access token from stdin
  - `--device-auth` — Device-based auth
- **`codex logout`** — Remove stored credentials

#### Tools & Integrations
- **`codex mcp`** — Manage external MCP servers (subcommands: `list`, `get`, `add`, `remove`, `login`, `logout`)
- **`codex plugin`** — Manage plugins (subcommands: `add`, `list`, `marketplace`, `remove`)
- **`codex sandbox`** — Run commands within a Codex-provided sandbox

#### Utilities
- **`codex apply`** — Apply the latest diff from Codex agent as `git apply` (aliases: `a`)
- **`codex doctor`** — Diagnose installation, config, auth, runtime health
- **`codex features`** — Inspect feature flags (subcommands: `list`, `enable`, `disable`)
- **`codex update`** — Update Codex to latest version
- **`codex completion`** — Generate shell completion scripts
- **`codex debug`** — Debugging tools (subcommands: `models`, `app-server`, `prompt-input`)

#### Desktop & Experimental
- **`codex app`** — Launch the Desktop app (opens installer if missing)
- **`codex app-server` [experimental]** — Run the app server or related tooling
- **`codex remote-control` [experimental]** — Manage app-server daemon with remote control
- **`codex exec-server` [experimental]** — Run the standalone exec-server service
- **`codex cloud` [experimental]** — Browse tasks from Codex Cloud and apply changes locally

---

## Common Flags (Available Across All Commands)

### Configuration
| Flag | Form | Type | Default | Behavior |
|------|------|------|---------|----------|
| `-c` | `--config <key=value>` | String | — | Override config value. Uses dotted paths (`foo.bar.baz`). Value parsed as TOML; falls back to literal string. Repeatable. |
| — | `--enable <FEATURE>` | String | — | Enable a feature. Equivalent to `-c features.<name>=true`. Repeatable. |
| — | `--disable <FEATURE>` | String | — | Disable a feature. Equivalent to `-c features.<name>=false`. Repeatable. |
| — | `--strict-config` | Flag | false | Error if config.toml contains unrecognized fields. |
| — | `--ignore-user-config` | Flag | false | Do not load `$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`. |

### Authentication & Remote
| Flag | Form | Type | Default | Behavior |
|------|------|------|---------|----------|
| — | `--remote <ADDR>` | String | — | Connect TUI to remote app server. Forms: `ws://host:port`, `wss://host:port`, `unix://`, `unix://PATH`. |
| — | `--remote-auth-token-env <ENV_VAR>` | String | — | Environment variable containing bearer token for remote websocket. |

### Display & Output
| Flag | Form | Type | Default | Behavior |
|------|------|------|---------|----------|
| — | `--color <COLOR>` | Enum | `auto` | Color settings: `always`, `never`, `auto`. |
| — | `--no-alt-screen` | Flag | false | Disable alternate screen mode; runs TUI inline, preserves terminal scrollback. |
| — | `--json` | Flag | false | Print events to stdout as JSONL. |

### Help & Version
| Flag | Form | Type | Default | Behavior |
|------|------|------|---------|----------|
| `-h` | `--help` | Flag | — | Print help. |
| `-V` | `--version` | Flag | — | Print version. |

---

## `codex exec` — Non-Interactive Execution

**Usage:** `codex exec [OPTIONS] [PROMPT]` or `codex exec [OPTIONS] <COMMAND> [ARGS]`

**Subcommands:** `resume`, `fork`, `review`, `help`

### Execution-Specific Flags

| Flag | Form | Type | Default | Behavior |
|------|------|------|---------|----------|
| `-m` | `--model <MODEL>` | String | config | Model the agent should use (e.g., `gpt-6-astra`). |
| `-s` | `--sandbox <SANDBOX_MODE>` | Enum | config | Sandbox policy: `read-only`, `workspace-write`, `danger-full-access`. |
| `-p` | `--profile <CONFIG_PROFILE_V2>` | String | — | Layer `$CODEX_HOME/<name>.config.toml` on top of base user config. |
| — | `--oss` | Flag | false | Use open-source provider. |
| — | `--local-provider <OSS_PROVIDER>` | String | config | Which local provider: `lmstudio` or `ollama`. Shows selection if not specified with `--oss`. |
| `-i` | `--image <FILE>...` | Path | — | Attach image(s) to the initial prompt. Repeatable. |
| `-C` | `--cd <DIR>` | Path | cwd | Use specified directory as working root. |
| — | `--add-dir <DIR>` | Path | — | Additional directories writable alongside primary workspace. Repeatable. |
| — | `--worktree` | Flag | false | Run session in a new managed Git worktree. |
| — | `--skip-git-repo-check` | Flag | false | Allow running Codex outside a Git repository. |
| — | `--ephemeral` | Flag | false | Run without persisting session files to disk. |

### Approval & Sandboxing

| Flag | Form | Type | Default | Behavior |
|------|------|------|---------|----------|
| `-a` | `--ask-for-approval <APPROVAL_POLICY>` | Enum | config | When model requires approval: `on-request` (model decides), `never` (no approval). |
| — | `--approve-for-me` | Flag | false | Route approval requests through automatic review using workspace-write sandbox. |
| — | `--dangerously-bypass-approvals-and-sandbox` | Flag | false | Skip confirmations and execute without sandboxing. EXTREMELY DANGEROUS. External sandboxing only. |
| — | `--dangerously-bypass-hook-trust` | Flag | false | Run enabled hooks without persisted trust. DANGEROUS. Automation that vets hooks only. |

### Rules & Policies

| Flag | Form | Type | Default | Behavior |
|------|------|------|---------|----------|
| — | `--ignore-rules` | Flag | false | Do not load user or project execpolicy `.rules` files. |

### Output Handling

| Flag | Form | Type | Default | Behavior |
|------|------|------|---------|----------|
| `-o` | `--output-last-message <FILE>` | Path | — | File where the last message from the agent is written. **IMPORTANT:** Use this to capture results; stdout streaming unreliable. |
| — | `--output-schema <FILE>` | Path | — | JSON Schema file describing the model's final response shape. |
| — | `--thread-source <SOURCE>` | String | — | Source classification for newly created/forked threads. |

### Prompt Input

**Behavior:** Prompt can come from:
1. Positional argument: `codex exec [OPTIONS] "my prompt"`
2. Stdin via `-`: `echo "prompt" | codex exec [OPTIONS] -`
3. If `[PROMPT]` is omitted and no `-`, reads from stdin
4. If stdin is piped AND a prompt is provided, stdin is appended as `<stdin>` block

---

## `codex exec resume` — Resume Previous Session

**Usage:** `codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]`

**Arguments:**
- `[SESSION_ID]` — UUID or thread name; UUIDs take precedence. Omit with `--last` to pick most recent.
- `[PROMPT]` — Optional prompt to send after resuming. Use `-` to read from stdin.

**Flags:**
- `--last` — Resume most recent session without specifying ID
- `--all` — Show all sessions (disables cwd filtering)
- `-i, --image <FILE>` — Attach image(s) to resumed prompt
- Plus all common `codex exec` flags above

---

## `codex exec fork` — Fork Previous Session

**Usage:** `codex exec fork [OPTIONS] <SESSION_ID> [PROMPT]`

**Arguments:**
- `<SESSION_ID>` — UUID or thread name to fork (required)
- `[PROMPT]` — Optional prompt after forking; use `-` for stdin

**Flags:**
- `-i, --image <FILE>` — Attach image(s) to post-fork prompt
- Plus all common `codex exec` flags

---

## `codex exec review` — Code Review Non-Interactively

**Usage:** `codex exec review [OPTIONS] [PROMPT]`

**Arguments:**
- `[PROMPT]` — Custom review instructions; use `-` for stdin

**Review-Specific Flags:**
- `--base <BRANCH>` — Review changes against this base branch
- `--commit <SHA>` — Review changes introduced by a commit
- `--uncommitted` — Review staged, unstaged, and untracked changes
- `--title <TITLE>` — Optional commit title for review summary

**Plus all common `codex exec` flags**

---

## `codex review` — Top-Level Code Review

**Usage:** `codex review [OPTIONS] [PROMPT]`

**Note:** Similar to `codex exec review` but entry point at root level.

**Flags:**
- `--base <BRANCH>` — Review against this base
- `--commit <SHA>` — Review a specific commit
- `--uncommitted` — Review uncommitted changes
- `--title <TITLE>` — Display title for review
- Plus common config flags (no model/sandbox/exec-specific flags here)

---

## `codex sandbox` — Execute Commands in Sandbox

**Usage:** `codex sandbox [OPTIONS] [COMMAND]...`

**Arguments:**
- `[COMMAND]...` — Full command args to run under seatbelt

**Sandbox-Specific Flags:**
- `--sandbox-state-json <JSON>` — JSON from `codex/sandbox-state-meta` to apply directly
- `--sandbox-state-readable-root <PATH>` — Add readable root to sandbox state. Repeatable.
- `--sandbox-state-disable-network` — Disable direct network access
- `-P, --permission-profile <NAME>` — Named permissions profile from active config
- `--include-managed-config` — Include managed requirements while resolving profile
- `--allow-unix-socket <PATH>` — Allow sandboxed AF_UNIX sockets rooted at path. Repeatable.
- `--log-denials` — Capture macOS sandbox denials via `log stream` and print after exit

---

## `codex login` — Authentication Management

**Usage:** `codex login [OPTIONS] [COMMAND]`

**Subcommands:**
- `status` — Show login status

**Flags:**
- `--with-api-key` — Read API key from stdin
- `--with-access-token` — Read access token from stdin
- `--device-auth` — Device-based authentication

---

## `codex doctor` — Installation & Health Diagnostics

**Usage:** `codex doctor [OPTIONS]`

**Flags:**
- `--json` — Emit redacted machine-readable report
- `--summary` — Show grouped check rows and final count summary only
- `--all` — Expand long lists in detailed human output
- `--no-color` — Disable ANSI color
- `--ascii` — Use ASCII status labels and separators

---

## `codex features` — Feature Flag Management

**Usage:** `codex features [OPTIONS] <COMMAND>`

**Subcommands:**
- `list` — List known features with stage and effective state
- `enable` — Enable a feature in config.toml
- `disable` — Disable a feature in config.toml

---

## `codex debug` — Debugging Tools

**Usage:** `codex debug [OPTIONS] <COMMAND>`

**Subcommands:**
- `models` — Render raw model catalog as JSON
  - `--bundled` — Skip refresh, dump only bundled catalog
- `app-server` — Tooling for debugging app server
- `prompt-input` — Render model-visible prompt input list as JSON

---

## Model Selection: `-m, --model <MODEL>`

**Available values:**
- `gpt-6-astra` (verified reachable)
- `gpt-5.6-sol` (documented in repo)
- Others available in the model catalog (inspect via `codex debug models`)

**Behavior:**
- If model doesn't exist, codex returns rc=1 with error
- Default from `~/.codex/config.toml` if not specified

---

## Sandbox Modes: `-s, --sandbox <SANDBOX_MODE>`

**Three valid values:**
1. **`read-only`** — Agent can read files only; no shell execution or writes
2. **`workspace-write`** — Agent can read/write workspace; execute shell
3. **`danger-full-access`** — Full filesystem access (dangerous)

**Default:** From config; `read-only` is typical safe default

**Error handling:** Invalid sandbox mode returns rc=1

---

## Output Capture: `-o, --output-last-message <FILE>`

**Behavior:**
- Writes the agent's final message (last response) to the specified file
- **NOT** streaming stdout; file contains the complete message
- File is created/overwritten if it doesn't exist
- Use this pattern:
  ```bash
  codex exec --ephemeral -s read-only -o /tmp/out.md - < prompt.md
  # Read result from /tmp/out.md, not stdout
  ```

---

## Stdin Patterns: Reading Prompts

**Valid patterns:**
1. **Explicit `-` at end:**
   ```bash
   echo "prompt" | codex exec --ephemeral -s read-only -o /tmp/out.md -
   ```
2. **Piped stdin (implicit):**
   ```bash
   echo "prompt" | codex exec --ephemeral -s read-only -o /tmp/out.md
   ```
3. **Positional prompt argument:**
   ```bash
   codex exec --ephemeral -s read-only -o /tmp/out.md "prompt text"
   ```
4. **Mixed stdin + argument (stdin appended):**
   ```bash
   echo "stdin content" | codex exec --ephemeral "initial prompt"
   # Result sees: "initial prompt\n<stdin>\nstdin content"
   ```

**Recommendation:** Use explicit `-` at end for clarity

---

## Config Override Examples

**From help text:**
- `-c model="o3"` — Override model
- `-c 'sandbox_permissions=["disk-full-read-access"]'` — Set array config
- `-c shell_environment_policy.inherit=all` — Nested TOML path

**TOML parsing:** If value fails TOML parse, treated as literal string

---

## Changes vs 0.152.1 (Where Detectable)

### REMOVED/CHANGED FLAGS
- **`--full-auto`** — GONE. Replaced by:
  - `--approve-for-me` (auto-approve with workspace-write sandbox)
  - `--dangerously-bypass-approvals-and-sandbox` (full bypass)
- **`-p` as "prompt"** — NEVER EXISTED. `-p, --profile` is profile config, always has been.

### STILL VALID
- **`--sandbox <MODE>`** — Present, working, three values documented
- **Stdin via `-`** — Documented and working
- **`-o, --output-last-message`** — Present and functional

### NEW/EXPANDED
- **`--ephemeral`** — Explicit flag for non-persistent sessions
- **`--dangerously-bypass-hook-trust`** — New explicit flag
- **`--ignore-rules`** — New flag for rule bypass
- **`--thread-source`** — New flag for thread classification
- **`--oss`, `--local-provider`** — Open-source provider support
- **`--approve-for-me`** — Replacement for old approval logic
- **Subcommand structure** — `codex exec`, `codex review` at top level; `codex exec resume`, `codex exec fork` as exec subcommands

---

## Mutual Exclusivity Notes

1. **`--approve-for-me` vs `--dangerously-bypass-approvals-and-sandbox`** — Both handle approvals differently; unclear if mutually exclusive from help alone
2. **`--ephemeral` vs persisted sessions** — `--ephemeral` suppresses session persistence; other flags assume persistence
3. **`--worktree` vs `-C`** — Both affect working directory; `--worktree` creates a managed one, `-C` uses existing
4. **`--oss` + `--local-provider`** — `--local-provider` requires `--oss` or config default

---

## Verification Status

**Verified working (by team lead):**
- `echo "..." | mise exec -- codex exec --ephemeral --sandbox read-only -o /tmp/out.md -` (rc=0)
- `-m gpt-6-astra` flag and model resolution
- Invalid `-m` value produces rc=1 (flag binding confirmed)

**Not yet probed (but help text consistent):**
- `--approve-for-me` execution
- `--dangerously-bypass-approvals-and-sandbox` behavior
- Sandbox denial logging (`--log-denials`)
- MCP server management (`codex mcp list/add/remove`)
- Plugin marketplace workflows
- Worktree isolation (`--worktree`)
- Remote app server connection (`--remote`)

---

## Next Steps (Delegated)

- [ ] Probe approval workflows: `--approve-for-me` vs manual approval
- [ ] Test worktree isolation behavior
- [ ] Verify MCP server add/remove workflow
- [ ] Confirm mutual exclusivity of approval flags
- [ ] Check if `--dangerously-bypass-hook-trust` requires specific conditions

