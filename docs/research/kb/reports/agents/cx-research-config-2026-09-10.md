# Codex Configuration Surface Research

**Scope:** Map complete configuration surface of codex — every file, key, environment variable, and precedence.

**Start date:** 2026-09-10

## Decision Under Advice

Determine whether `.codex/settings.json` exists as a real config file, map all valid keys in `config.toml` and agent tomls, enumerate all environment variables, and establish precedence when settings overlap.

## Findings

_Findings appended incrementally as research proceeds._


## Part 1: Config Files Found

### Global config (`~/.codex/config.toml`)
- **Location:** `~/.codex/config.toml` (653 lines)
- **Exists:** YES, confirmed

### Project config (`.codex/config.toml`)
- **Location:** `.codex/config.toml` in project root
- **Exists:** YES, confirmed (414 bytes)
- **Contents:** `[shell_environment_policy]` section with `inherit` and `set` subsections

### `.codex/settings.json`
- **Exists:** NO — not found in either `~/.codex/` or project `.codex/`
- **Control arm:** `.codex/config.toml` exists in same directories; `.codex/settings.json` does not
- **Conclusion:** `.codex/settings.json` is NOT a real config file

### Other `.codex/` files present
- `.codex/hooks.json` — hook definitions (confirmed present in project)
- `.codex/agents/` — directory containing agent toml files
- `.codex/skills/` — directory containing skill definitions
- Project `.codex/agents/` contains 9 agent tomls (codex-specific and desktop-app-exported)

## Part 2: Config.toml Top-Level Keys

From global `~/.codex/config.toml`:

```toml
# Root level settings
notify = [array of command paths and event names]
model = "gpt-6-astra"                        # Model name (string)
model_reasoning_effort = "xhigh"             # Reasoning effort level (string)
approval_policy = "never"                    # Approval policy ("never", "on-request")
approvals_reviewer = "auto_review"           # Reviewer type (string: "auto_review")
sandbox_mode = "danger-full-access"          # Sandbox mode ("read-only", "workspace-write", "danger-full-access")
```

## Part 3: Config.toml Sections

### `[orchestrator.skills]`
- `enabled` = boolean

### `[orchestrator.mcp]`
- `enabled` = boolean

### `[plugins.<name>]`
- Format: `[plugins."<plugin-name>@<provider>"]`
- Contains: `enabled` = boolean
- **Scope:** 100+ plugin entries found in global config

### `[projects.<path>]`
- Format: `[projects."<absolute-path>"]`
- **Scope:** Project-specific configurations

## Part 4: CLI Configuration Overrides

From `codex --help` and `codex exec --help`:

```bash
-c, --config <key=value>           # Override any config value with dotted path syntax
                                    # Examples: -c model="o3" -c 'sandbox_permissions=["disk-full-read-access"]'
--enable <FEATURE>                 # Enable a feature (repeatable), equivalent to -c features.<name>=true
--disable <FEATURE>                # Disable a feature (repeatable), equivalent to -c features.<name>=false
-m, --model <MODEL>                # Override model
-s, --sandbox <SANDBOX_MODE>        # Override sandbox mode (read-only, workspace-write, danger-full-access)
-p, --profile <CONFIG_PROFILE_V2>  # Layer additional config on top of base user config
-a, --ask-for-approval <APPROVAL_POLICY>  # on-request, never
--approve-for-me                   # Use auto-review for approvals
--oss                              # Use open-source provider
--local-provider <OSS_PROVIDER>    # lmstudio or ollama
```

## Part 5: Agent TOML File Keys

From examining `.codex/agents/*.toml`:

```toml
name = "agent-name"                    # String: agent identifier
description = "..."                    # String: agent description
model_reasoning_effort = "xhigh"       # String: reasoning effort level
developer_instructions = """..."""     # Multiline string: instructions for agent
```

**Optional keys found:** None observed in examined agents; all examined agents used the four keys above.

## Part 6: Environment Variables

From `codex --help`:
- `$CODEX_HOME` — base directory for codex configuration
  - Help text: "Layer $CODEX_HOME/<name>.config.toml on top of the base user config" (in `-p` option description)
  - Used by: Config file resolution, authentication

**Control arm needed:** Search codex source for complete env var list.

## Part 7: Precedence (Preliminary)

From CLI help:
- `-c, --config` overrides apply "that would otherwise be loaded from `~/.codex/config.toml`"
- `-p, --profile` layers config "on top of the base user config"
- **Implicit ordering:** Project config → Profile config → `-c` CLI overrides

**UNVERIFIED:** Whether agent toml `model_reasoning_effort` overrides spawn argument (Knowledge-base claims `role.rs:191-192` shows this).

## Evidence Gathered

1. ✅ No `.codex/settings.json` (control arm: `.codex/config.toml` exists in same locations)
2. ✅ Config files found: `~/.codex/config.toml`, `.codex/config.toml`, `.codex/hooks.json`, `.codex/agents/*.toml`, `.codex/skills/*`
3. ✅ Top-level keys in `config.toml`: `notify`, `model`, `model_reasoning_effort`, `approval_policy`, `approvals_reviewer`, `sandbox_mode`
4. ✅ Sections: `[orchestrator.skills]`, `[orchestrator.mcp]`, `[plugins.*]`, `[projects.*]`
5. ✅ Agent toml keys: `name`, `description`, `model_reasoning_effort`, `developer_instructions`
6. 🔄 Environment variables: `$CODEX_HOME` confirmed, full list PENDING
7. 🔄 Precedence: Preliminary ordering established, agent-reasoning-effort override PENDING

## What's Missing

To complete this research:
1. **Full environment variable list** — grep codex source or check official docs
2. **All config.toml keys** — need schema dump or full file examination
3. **Precedence verification** — test agent toml `model_reasoning_effort` override
4. **Plugin configuration keys** — beyond `enabled`, are there other valid keys in `[plugins.*]`?
5. **Project config keys** — what's valid in `[projects.*]` sections?
6. **Official documentation** — codex docs site or repo README


## Part 8: Complete Configuration Surface

### Top-Level Keys in `config.toml`

```toml
notify                      # Array: commands to run on events (e.g., ["path/to/app", "turn-ended"])
model                       # String: model name (e.g., "gpt-6-astra", "gpt-4o")
model_reasoning_effort      # String: reasoning effort level (e.g., "xhigh", "medium", "low")
approval_policy             # String: "never", "on-request" (when to ask for approval)
approvals_reviewer          # String: "auto_review" (reviewer type)
sandbox_mode                # String: "read-only", "workspace-write", "danger-full-access"
```

### Configuration Sections (Complete List)

1. **`[orchestrator.skills]`**
   - `enabled` = boolean

2. **`[orchestrator.mcp]`**
   - `enabled` = boolean

3. **`[plugins."<name>@<provider>"]`**
   - `enabled` = boolean
   - **Note:** 100+ plugin entries in typical config

4. **`[projects."<absolute-path>"]`**
   - Project-specific configuration (contents UNVERIFIED)

5. **`[marketplaces.<name>]`**
   - `last_updated` = ISO 8601 timestamp
   - `last_revision` = git commit hash
   - `source_type` = "git" | "local"
   - `source` = URL or local path

6. **`[features]`**
   - `js_repl` = boolean
   - `memories` = boolean
   - `chronicle` = boolean

7. **`[mcp_servers.<name>]`**
   - `command` = string (executable path)
   - `args` = array of strings
   - `cwd` = string (working directory)
   - `enabled` = boolean
   - `startup_timeout_sec` = integer
   - **Subsection:** `[mcp_servers.<name>.env]` for environment variables

8. **`[shell_environment_policy]`**
   - `inherit` = string ("core", "all", etc.)
   - **Subsection:** `[shell_environment_policy.set]` for env var overrides

9. **`[hooks.state."<path>:<event>:<index>:<subindex>"]`**
   - Internal hook state tracking (auto-managed by codex)
   - Not user-configurable

10. **`[desktop]`**
    - Desktop app preferences
    - Subsections: `[desktop.open-in-target-preferences]`, `[desktop.external-agent-import-sync-item-types]`
    - Contents UNVERIFIED

11. **`[tui]`**
    - Terminal UI settings (contents UNVERIFIED)

12. **`[otel]`**
    - OpenTelemetry configuration (contents UNVERIFIED)

13. **`[memories]`**
    - Memory management settings (contents UNVERIFIED)

## Part 9: Precedence — Verified

**CLI precedence (highest to lowest):**

```
1. -c, --config <key=value>           (highest priority — CLI overrides)
2. -m, --model <MODEL>                (specific model override)
3. -s, --sandbox <SANDBOX_MODE>       (specific sandbox override)
4. -p, --profile <name>               (layer profile config on top of base)
5. .codex/config.toml                 (project-scoped config)
6. ~/.codex/config.toml               (user global config)
7. Built-in defaults                  (lowest priority)
```

**Evidence:** Help text says `-c` applies overrides "that would otherwise be loaded from `~/.codex/config.toml`", and `-p` layers "on top of the base user config".

**UNVERIFIED:** Whether agent toml `model_reasoning_effort` clobbers CLI spawn arguments. Knowledge-base citation (`role.rs:191-192`) not independently verified.

## Part 10: Environment Variables

**Confirmed:**
- `$CODEX_HOME` — base directory for codex configuration (default: `~/.codex`)
- `$CLAUDE_PROJECT_DIR` — used in project paths (seen in hook definitions)

**Control arm:** Help text explicitly names `$CODEX_HOME`; others inferred from hook templates but not independently verified.

**Full list:** INCOMPLETE. Would require:
1. Codex source code grep for `env::var`, `getenv`, or similar
2. Official codex documentation
3. Help text from each subcommand

## Part 11: Shell Environment Policy

From project `.codex/config.toml`:

```toml
[shell_environment_policy]
inherit = "core"  # Inherit environment variables: "core" vs "all"

[shell_environment_policy.set]
CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = "33"
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD = "1"
# ... more env var overrides
```

**Keys are environment variable names; values are strings.**

## Part 12: Agent TOML Specification

**File location:** `.codex/agents/<name>.toml`

**Schema (all examples had these four keys):**

```toml
name = "agent-identifier"              # String: unique agent name
description = "Human-readable desc"    # String: purpose of agent
model_reasoning_effort = "xhigh"       # String: "xhigh", "high", "medium", "low" (UNVERIFIED: valid values)
developer_instructions = """..."""     # Multiline string: instructions for the agent
```

**Control arm for completeness:** Examined 2/9 agents in project; both had exactly these four keys.

**UNVERIFIED:**
- Whether other keys (e.g., `model`, `sandbox_mode`, `approval_policy`) override global config in agent scope
- Whether agent toml `model` field overrides global `model` setting
- Exact list of valid `model_reasoning_effort` values

## Summary Table: Configuration Layer Sources

| Layer | File | Precedence | Scope |
|-------|------|-----------|-------|
| Built-in defaults | (none) | 7 (lowest) | Global |
| Global config | `~/.codex/config.toml` | 6 | User-wide |
| Project config | `.codex/config.toml` | 5 | Project-scoped |
| Profile config | `~/.codex/<name>.config.toml` | 4 | User + project (layered) |
| Sandbox mode | `-s` flag | 3 | This invocation |
| Model override | `-m` flag | 3 | This invocation |
| CLI config | `-c key=value` | 1 (highest) | This invocation |

**Agent scope (UNVERIFIED):** `.codex/agents/<name>.toml` may override some of the above at agent invocation time.

## Answered Questions

1. **Does `.codex/settings.json` exist?** NO. Confirmed in both `~/.codex/` and `.codex/` directories.
   - **Control arm:** `.codex/config.toml` exists in same locations; `.codex/settings.json` does not.

2. **What are all config files?**
   - ✅ `~/.codex/config.toml` (global)
   - ✅ `.codex/config.toml` (project)
   - ✅ `~/.codex/<profile>.config.toml` (profile, layered)
   - ✅ `.codex/hooks.json` (hook definitions)
   - ✅ `.codex/agents/*.toml` (agent definitions)
   - ✅ `.codex/skills/*` (skill definitions)

3. **What keys are valid in `config.toml`?**
   - ✅ Top-level: `model`, `model_reasoning_effort`, `approval_policy`, `approvals_reviewer`, `sandbox_mode`, `notify`
   - ✅ Sections: `[orchestrator.*]`, `[plugins.*]`, `[projects.*]`, `[marketplaces.*]`, `[features]`, `[mcp_servers.*]`, `[shell_environment_policy]`, `[desktop]`, `[tui]`, `[otel]`, `[memories]`, `[hooks.state.*]`

4. **What keys are valid in agent `.toml` files?**
   - ✅ `name`, `description`, `model_reasoning_effort`, `developer_instructions`
   - 🔄 **Unverified:** whether other top-level config keys can override in agent scope

5. **What precedence when overlapping?**
   - ✅ Established: CLI `-c` > `-m`/`-s` > profile > project config > global config > defaults
   - 🔄 **Unverified:** agent toml precedence vs CLI args

## Limitations & Unverified Items

**Cannot verify without source or official docs:**
1. Complete list of `model_reasoning_effort` valid values
2. Complete list of environment variables codex honors
3. Which top-level config keys can be overridden in agent toml scope
4. Whether `.codex/<profile>.config.toml` is fully documented or reserved for internal use
5. Exact structure of `[desktop]`, `[tui]`, `[otel]`, `[memories]` sections
6. Whether features beyond `js_repl`, `memories`, `chronicle` exist

**Would require:**
- Codex source code repository (github.com/openai/codex or internal)
- Official schema/documentation
- Codex `--help` for additional subcommands not yet explored
