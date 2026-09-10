# Codex Configuration Schema — Complete Enumeration

**Research Date:** 2026-09-10  
**Codex Version Installed:** 0.154.0  
**Branch:** chore/codex-upgrade-and-research  
**Source:** Official codex-docs KB (learn.chatgpt.com/docs/config-file/config-reference, v0.146–0.153.2)

---

## Executive Summary

Codex configuration is **NOT a limited set** of keys we've manually discovered. The authoritative schema (from official OpenAI documentation in the KB) contains **150+ top-level configuration keys**, organized into sections for models, sandbox, approval, MCP, agents, environment, and more. This repo currently uses only **6 keys** in `.codex/config.toml`:

```toml
[shell_environment_policy]
inherit = "core"

[shell_environment_policy.set]
CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = "33"
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD = "1"
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"
CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS = "20"
CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION = "200"
CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH = "3"
CLAUDE_CODE_TASK_LIST_ID = "dotfiles-dag"
OTEL_LOG_RAW_API_BODIES = "0"
```

And agent configs use just **4 keys**:
- `name`
- `description`
- `model_reasoning_effort`
- `developer_instructions`

But **we should be considering many others** to pin lane behaviour.

---

## 1. Global & Project Configuration (`~/.codex/config.toml` and `.codex/config.toml`)

### Core Model Settings

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `model` | string | `gpt-4o` | Default LLM model for exec/plan/review; can roll forward on version bumps |
| `review_model` | string | unset | Optional override for `/review` subcommand |
| `model_provider` | string | `openai` | Provider ID (openai, ollama, lmstudio, custom, amazon-bedrock) |
| `model_reasoning_effort` | enum | `medium` | Reasoning depth: `minimal`, `low`, `medium`, `high`, `xhigh` (model-dependent) |
| `plan_mode_reasoning_effort` | enum | unset | Plan-mode-specific override |
| `model_reasoning_summary` | enum | unset | Reasoning output detail: `auto`, `concise`, `detailed`, `none` |
| `model_verbosity` | enum | unset | GPT-5 Responses API verbosity: `low`, `medium`, `high` |
| `model_context_window` | number | — | Context window override (tokens) |
| `model_auto_compact_token_limit` | number | unset | Compaction threshold; unset uses model defaults |
| `model_auto_compact_token_limit_scope` | enum | `total` | Compaction scope: `total` or `body_after_prefix` |

### Sandbox & Security

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `approval_policy` | enum/table | `on-request` | When to prompt for approval: `on-request`, `never`, or granular table |
| `sandbox_mode` | enum | `read-only` | Filesystem/network access: `read-only`, `workspace-write`, `danger-full-access` |
| `sandbox_workspace_write.writable_roots` | array | — | Additional writable paths in workspace-write mode |
| `sandbox_workspace_write.network_access` | bool | false | Allow outbound network in workspace-write |
| `sandbox_workspace_write.exclude_tmpdir_env_var` | bool | false | Exclude `$TMPDIR` from writeable roots |
| `browser_use.allow_history_access` | bool | true | Allow browser history access |
| `computer_use.default_app_access` | enum | `allow` | Fallback app access: `allow` or `deny` |

### Shell Environment

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `shell_environment_policy.inherit` | enum | unset | Env baseline: `all`, `core`, `none` |
| `shell_environment_policy.filters` | map | — | Canonical case-insensitive var patterns (include/exclude) |
| `shell_environment_policy.ignore_default_excludes` | bool | true | Skip auto-secret-name filters before user filters |
| `shell_environment_policy.set` | map | — | **Explicit env vars injected after filters** (this repo uses it) |
| `shell_environment_policy.experimental_use_profile` | bool | false | Source shell profile when spawning subprocesses |
| `allow_login_shell` | bool | true | Allow login-shell semantics in shell tools |

### Instructions & Guidance

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `developer_instructions` | string | empty | **Custom system instructions** (used in agent TOMLs here) |
| `instructions` | string | — | Reserved for future use |
| `model_instructions_file` | string | — | Path to replace built-in instructions instead of AGENTS.md |
| `project_doc_max_bytes` | number | — | Max bytes read from `AGENTS.md` |
| `personality` | enum | unset | Default communication style: `none`, `friendly`, `pragmatic` |

### Advanced Model & Context

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `model_catalog_json` | string (path) | — | Custom model catalog JSON file |
| `model_supports_reasoning_summaries` | bool | unset | Force reasoning metadata on/off |
| `service_tier` | string | unset | Preferred service tier (e.g., `fast`) |
| `oss_provider` | enum | unset | Local provider for `--oss`: `lmstudio`, `ollama` |

### Features (Experimental/Stable Toggles)

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `features.hooks` | bool | true | Enable lifecycle hooks from hooks.json (stable) |
| `features.multi_agent` | bool | true | Enable spawn_agent/send_input (stable) |
| `features.unified_exec` | bool | true (except Windows) | PTY-backed exec tool (stable) |
| `features.shell_snapshot` | bool | true | Snapshot shell env for speed (stable) |
| `features.goals` | bool | true | Persisted goals & continuation (stable) |
| `features.web_search` | enum | — | Web search: `cached`, `live`, or unset |
| `features.code_mode.enabled` | bool | false | Code mode (experimental) |
| `features.context_management.experimental_mode` | bool | false | Notes-based history (experimental) |
| `features.rollout_budget.enabled` | bool | false | Token usage tracking (experimental) |

### Multi-Agent Settings

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `agents.enabled` | bool | true | Enable multi-agent tools |
| `agents.max_concurrent_threads_per_session` | number | unset | Max spawned agent threads concurrently |
| `agents.default_subagent_model` | string | unset | Default model for spawned agents |
| `agents.default_subagent_reasoning_effort` | string | unset | Default reasoning effort for spawned agents |
| `agents.interrupt_message` | bool | true | Record message when agent interrupted |

### MCP Configuration

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `mcp_servers.<id>.enabled` | bool | true | Enable/disable MCP server |
| `mcp_servers.<id>.required` | bool | false | Fail startup if this enabled server can't init |
| `mcp_servers.<id>.command` | string | — | Stdio server launcher command |
| `mcp_servers.<id>.url` | string | — | HTTP/streamable MCP server endpoint |
| `mcp_servers.<id>.auth` | enum | `oauth` | Auth fallback: `oauth` or `chatgpt` |
| `mcp_servers.<id>.startup_timeout_sec` | number | 10 | Server startup timeout |
| `mcp_servers.<id>.tool_timeout_sec` | number | 60 | Per-tool timeout |
| `mcp_servers.<id>.enabled_tools` | array | — | Allowlist of tool names |
| `mcp_servers.<id>.disabled_tools` | array | — | Denylist of tool names |

### Hooks Configuration

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `hooks` | table | — | **Inline hooks in config.toml** (same schema as hooks.json) |
| `hooks.<Event>` | array | — | Event types: PreToolUse, SessionStart, SessionEnd, SubagentStart, etc. |
| `features.hooks` | bool | true | Enable hooks globally |

### Skills & Apps

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `skills.max_context_tokens` | number | 2% of context | Token budget for skills catalog |
| `skills.config[].path` | string | — | Path to skill folder with SKILL.md |
| `skills.config[].enabled` | bool | — | Enable/disable specific skill |
| `apps.<id>.enabled` | bool | true | Enable/disable app by ID |
| `apps._default.enabled` | bool | true | Default app state |

### History & Telemetry

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `history.persistence` | enum | `save-all` | Session history: `save-all` or `none` |
| `history.max_bytes` | number | — | Cap history file size |
| `log_dir` | string | `$CODEX_HOME/log` | Log directory |
| `analytics.enabled` | bool | unset | Enable/disable analytics |
| `check_for_update_on_startup` | bool | true | Check for Codex updates on startup |

---

## 2. Agent Configuration (`.codex/agents/<name>.toml`)

Each agent TOML defines a role with optional behavioural overrides. The schema is a **subset of global config**, not a separate schema.

### Agent-Specific Keys

| Key | Type | Required | Meaning |
|-----|------|----------|---------|
| `name` | string | ✅ YES | Agent identifier (used by spawn_agent) |
| `description` | string | ✅ YES | Role guidance shown to Codex |
| `model_reasoning_effort` | enum | ❌ NO | Reasoning level override for this agent |
| `developer_instructions` | string | ❌ NO | **Custom instructions for this role** |
| `model` | string | ❌ NO | **Model override (AWAITING VERIFICATION)** |
| `config_file` | string | ❌ NO | Path to additional TOML config layer |

### This Repo's Agent Configs (9 agents)

| Agent | Description | Reasoning Level | Notes |
|-------|---|---|---|
| `codex-advisor` | Verdict at commitment boundary | `xhigh` | Uses `developer_instructions` |
| `codex-operator` | Runs one `mise run` task | `xhigh` | Full access for git writes |
| `codex-claude-code-expert` | Authority on Claude Code harness | `xhigh` | Read-only sandbox |
| `codex-adversarial-critic` | Attacks proposals (codex) | `xhigh` | Codex lane |
| `codex-staleness-auditor` | Audits prose for stale claims | `xhigh` | Codex lane |
| `adversarial-critic` | Same (Claude-backed) | `high` | Codex fallback |
| `claude-code-expert` | Same (Claude-backed) | unset | Codex fallback |
| `staleness-auditor` | Same (Claude-backed) | unset | Codex fallback |
| `dockerfile-reviewer` | Reviews Dockerfiles & BuildKit | unset | — |

---

## 3. Environment Variables

Codex reads these env vars for configuration and runtime:

| Variable | Type | Overrides | Purpose |
|----------|------|-----------|---------|
| `CODEX_HOME` | string (path) | — | Config/state home (default `~/.codex`) |
| `CODEX_MODEL` | string | `model` key | Default model |
| `CODEX_REASONING_EFFORT` | string | `model_reasoning_effort` | Reasoning level |
| `CODEX_API_KEY` | string | — | OpenAI API key |
| `OPENAI_API_KEY` | string | — | Fallback API key if CODEX_API_KEY unset |
| `HOME` | string | — | Home directory for config lookup |

---

## 4. Precedence Chain (Authoritative)

**Highest to lowest priority:**

1. **CLI flags** (`-c KEY=VALUE`, `--model <model>`, etc.)
2. **Environment variables** (`CODEX_*`)
3. **Agent TOML** (`.codex/agents/<name>.toml`)
4. **Project config** (`.codex/config.toml`)
5. **Global config** (`~/.codex/config.toml`)
6. **Built-in defaults** (hardcoded fallbacks)

### CRITICAL UNVERIFIED CLAIM

**"An agent's `model_reasoning_effort` in `.codex/agents/<name>.toml` CLOBBERS a `-c model_reasoning_effort=high` CLI flag."**

**Status:** UNVERIFIED — requires source code audit of [openai/codex](https://github.com/openai/codex/blob/main/src/config) precedence logic. The claim came from a sibling repo that may have incorrect information.

**What we know:** The precedence chain above is from official docs. Whether agent TOML is evaluated BEFORE or AFTER CLI flags requires code inspection.

---

## 5. Hooks Configuration (`hooks.json` and inline `[hooks]`)

### Supported Hook Events

Codex fires hooks at these lifecycle points:

| Event | Fires When | Notes |
|-------|---|---|
| `PreToolUse` | Before a tool call | Can deny/modify calls |
| `PostToolUse` | After a tool completes | Receives result |
| `SessionStart` | Session begins | Startup, `resume` |
| `SessionEnd` | Session ends | Runs once per session |
| `SubagentStart` | Spawned agent starts | Multiagent flow |
| `SubagentStop` | Spawned agent stops | — |
| `PermissionRequest` | Approval prompt | Can auto-approve/deny |
| `PreCompact` | Before context compaction | Read-only |
| `PostCompact` | After compaction | — |
| `UserPromptSubmit` | User submits prompt | Before processing |
| `Stop` | Session stop requested | Per-turn, can block |
| `Interrupt` | Session interrupted | User ctrl-c |

### Hook Handler Schema

```toml
[[hooks.PreToolUse]]
matcher = "Bash|AskUserQuestion"

[[hooks.PreToolUse.hooks]]
type = "command"
command = "bash ./scripts/guard.sh"
timeout = 20

[hooks.PreToolUse.hooks.async]
# command runs in background without blocking
```

### This Repo's Hooks (`.codex/hooks.json`)

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash|AskUserQuestion|Edit|Write|NotebookEdit",
        "hooks": [{ "type": "command", "command": "bash scripts/pretooluse-guard.sh", "timeout": 20 }] },
      { "matcher": "Bash|Grep",
        "hooks": [{ "type": "command", "command": "bash scripts/graphify-hook-guard.sh search", "timeout": 15 }] },
      { "matcher": "Read|Glob",
        "hooks": [{ "type": "command", "command": "bash scripts/graphify-hook-guard.sh read", "timeout": 15 }] }
    ],
    "SessionStart": [/* ... */],
    "SessionEnd": [/* ... */]
  }
}
```

---

## 6. Skills Schema (`.codex/skills/`)

Skills are **referenced via SKILL.md** inside a folder. Each skill must have:

```
.codex/skills/<name>/
  SKILL.md              # Frontmatter + description + implementation
  references/           # Optional reference docs
  ...
```

### SKILL.md Frontmatter

```yaml
---
name: <skill-name>
description: <one-line summary for Codex matching>
enabled: true
---

<skill content: prompt or call instructions>
```

This repo has ONE skill tracked:
- `.codex/skills/graphify/` — graphify integration

---

## 7. What We ARE Currently Configuring

### Global: `.codex/config.toml`

```toml
[shell_environment_policy]
inherit = "core"

[shell_environment_policy.set]
# 8 environment variables pinned explicitly
CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = "33"
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD = "1"
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"
CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS = "20"
CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION = "200"
CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH = "3"
CLAUDE_CODE_TASK_LIST_ID = "dotfiles-dag"
OTEL_LOG_RAW_API_BODIES = "0"
```

### Agents: 9 tracked agent TOML files

- All use `model_reasoning_effort = "xhigh"` or omit it
- All use `developer_instructions` with custom role guidance
- None explicitly pin a `model` (relies on global default)

---

## 8. CRITICAL GAPS — What We Should Be Pinning

### 1. Model Pinning (URGENT)

**Problem:** This repo's default model is `gpt-4o`, which can roll forward on version bumps. Recent incident: gpt-4o defaulted to `gpt-6-astra`, breaking lanes.

**Recommendation:**
```toml
model = "gpt-4o"                          # Pin to specific model
model_provider = "openai"                 # Explicit provider
```

And in EACH agent TOML, add if absent:
```toml
model = "gpt-4-turbo"  # OR "gpt-5.6-sol" for codex lanes
```

### 2. Explicit Sandbox Pinning

**Currently:** Relying on Codex defaults.

**Should configure:**
```toml
sandbox_mode = "read-only"               # CI/read-only lanes
# OR
sandbox_mode = "workspace-write"
sandbox_workspace_write.network_access = false
```

### 3. Approval Policy Clarity

**Currently:** Unset (uses default).

**Consider adding:**
```toml
approval_policy = "never"                 # For CI automation
# OR
approval_policy = { granular = { sandbox_approval = false, rules = true, mcp_elicitations = false } }
```

### 4. Model Override per Agent

**Question:** Should each codex lane pin its model to guarantee `gpt-5.6-sol`?

```toml
# In .codex/agents/codex-advisor.toml
model = "gpt-5.6-sol"
```

**Status:** AWAITING SOURCE VERIFICATION that agent `model` key is valid and has correct precedence.

### 5. Developer Instructions Consolidation

Currently scattered across 9 agent TOMLs. Consider a `model_instructions_file` or centralized policy:

```toml
developer_instructions = "Project guidance here..."
```

---

## 9. Unverified / Research Gaps

- [ ] **Agent `model` validity:** Is `model` a valid key in `.codex/agents/<name>.toml`? What's the interaction with `model_reasoning_effort`?
- [ ] **Precedence of agent TOML `model_reasoning_effort` vs CLI `-c` flag:** Requires openai/codex source inspection.
- [ ] **`shell_environment_policy.set` interaction:** How do filters and set interact? Does `set` override filters?
- [ ] **Hooks async semantics:** What does background hook execution guarantee about ordering?
- [ ] **Skills namespace resolution:** How does Codex find and invoke skills from code?
- [ ] **MCP server startup on failure:** What happens if a `required = true` MCP server fails to init?

---

## 10. Action Items for Owner

1. **Pin `model` globally and per-agent** to prevent version rollover incidents.
2. **Audit precedence** — run a control-armed probe to confirm agent TOML `model_reasoning_effort` precedence vs CLI.
3. **Explicit approval_policy** — decide whether CI lanes should be `never` or `on-request`.
4. **Sandbox mode documentation** — clarify which lanes run in which mode and why.
5. **Consolidate developer_instructions** — centralize common guidance or justify per-role variance.
6. **Add MCP configuration** if using external tools (currently empty).

---

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — Official Codex source; configuration precedence logic resides here (unverified probe results)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — KB sources/codex-docs; official configuration reference documentation

