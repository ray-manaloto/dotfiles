# Claude Code settings schema — extracted from the 2.1.222 binary

**Generated, not hand-written.** The shipped bundle is minified but *not*
obfuscated, so the zod settings schema survives with its `.describe()` strings
intact. That makes the binary a **better corpus than `settings.md`** for settings
questions — several keys here appear in no doc page at all.

## Method (re-runnable at any version)

Every `.describe(` call is attributed to the nearest preceding `key:E.`/`key:z.`
zod chain, then the description is read as a JS string literal, following `+`
concatenation. The settings object is one contiguous run, so the extract is bounded
to the tightest window containing three known settings keys, widened while
neighbouring matches stay closer than 20 KB.

- total describe() calls in binary: 1439
- settings-region rows: 426
- distinct settings keys: 273
- region: 238367731..238473834

### Control arms

| Probe | Expect | Got |
|---|---|---|
| `disableClaudeAiConnectors` | present | ✅ 1 |
| `skipWorkflowUsageWarning` | present | ✅ 1 |
| `teammateMode`, `enableWorkflows`, `bgIsolation`, `baseRef` | present (multi-agent keys) | ✅ all 4 |
| `zzflibbernaught` (invented) | absent | ✅ 0 |

⚠️ **Not every settings key carries a description.** `teammateDefaultModel` is a real,
documented key with **zero** zod-typed occurrences — it is read and written directly in
UI code. So this file is *the described subset*, not the complete key list. A key's
absence here is not evidence it does not exist.

⚠️ **Count discrepancy, unresolved.** A subagent reported "604 settings keys with
descriptions" from the same binary. This extraction, with the method stated above,
yields **273 distinct described keys** in the settings region and **738** keys with a
description binary-wide (the latter includes tool and MCP schemas, which are not
settings). The 604 figure could not be reproduced and its method was not recorded;
treat it as unverified.

## The extractor

```python
"""Extract Claude Code's embedded zod settings schema from the installed binary.

The bundle is minified but NOT obfuscated, so the schema survives with its
.describe() strings intact. Re-runnable at any version: point BIN at the binary.
"""

import re
import sys
from pathlib import Path

BIN = Path(sys.argv[1])
OUT = Path(sys.argv[2])

src = BIN.read_bytes().decode("utf-8", "replace")

# A describe() call is owned by the nearest preceding `key:E.` / `key:z.` chain.
KEY = re.compile(r"([A-Za-z_$][\w$]*)\s*:\s*[Ez]\.")
STR = re.compile(r"""\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')""")


def read_concat(text: str, pos: int) -> tuple[str, int]:
    """Read a JS string literal at pos, following `+` concatenation."""
    parts = []
    while True:
        m = STR.match(text, pos)
        if not m:
            break
        parts.append(m.group(1) if m.group(1) is not None else m.group(2))
        pos = m.end()
        nxt = re.match(r"\s*\+\s*", text[pos:])
        if not nxt:
            break
        pos += nxt.end()
    raw = "".join(parts)
    return raw.encode().decode("unicode_escape", "replace"), pos


rows = []
for m in re.finditer(r"\.describe\(", src):
    back = src[max(0, m.start() - 500) : m.start()]
    keys = list(KEY.finditer(back))
    if not keys:
        continue
    key = keys[-1].group(1)
    chain = back[keys[-1].end() - 2 :]  # the zod chain, e.g. E.boolean().optional()
    desc, _ = read_concat(src, m.end())
    if not desc:
        continue
    rows.append((m.start(), key, chain.strip(), desc))

# The settings schema is one contiguous run. Anchor on keys we know live in it,
# then keep every row inside the tightest window containing all anchors.
ANCHORS = ("disableClaudeAiConnectors", "skipWorkflowUsageWarning", "autoDreamEnabled")
anchor_offsets = [o for o, k, _, _ in rows if k in ANCHORS]
lo, hi = min(anchor_offsets), max(anchor_offsets)
# widen to the contiguous block: walk out while rows stay densely packed
ordered = sorted(rows)
idx_lo = next(i for i, r in enumerate(ordered) if r[0] >= lo)
idx_hi = next(i for i in range(len(ordered) - 1, -1, -1) if ordered[i][0] <= hi)
GAP = 20_000  # a jump larger than this means we left the schema object
while idx_lo > 0 and ordered[idx_lo][0] - ordered[idx_lo - 1][0] < GAP:
    idx_lo -= 1
while idx_hi < len(ordered) - 1 and ordered[idx_hi + 1][0] - ordered[idx_hi][0] < GAP:
    idx_hi += 1
settings = ordered[idx_lo : idx_hi + 1]

seen: dict[str, tuple[str, str]] = {}
for _, key, chain, desc in settings:
    seen.setdefault(key, (chain, desc))

with OUT.open("w") as fh:
    fh.write(f"total describe() calls in binary: {len(rows)}\n")
    fh.write(f"settings-region rows: {len(settings)}\n")
    fh.write(f"distinct settings keys: {len(seen)}\n")
    fh.write(f"region: {settings[0][0]}..{settings[-1][0]}\n\n")
    for key, (chain, desc) in sorted(seen.items()):
        fh.write(f"## {key}\n`{chain}`\n{desc}\n\n")

print(f"describe() total : {len(rows)}")
print(f"settings rows    : {len(settings)}")
print(f"distinct keys    : {len(seen)}")
print(f"region           : {settings[0][0]}..{settings[-1][0]}")
print(f"wrote            : {OUT}")
```

## The 273 described settings keys

| Key | Type | Description |
|---|---|---|
| `$schema` | `E.string().optional()` | JSON Schema reference for editor autocomplete/validation; ignored at load time |
| `additionalDirectories` | `E.array(E.string()).optional()` | Additional directories to include in the permission scope |
| `advisorModel` | `E.string().optional()` | Advisor model for the server-side advisor tool. |
| `agent` | `E.string().optional()` | Name of an agent (built-in or custom) to use for the main thread. Applies the agent's system prompt, tool restrictions, and model. |
| `agentPushNotifEnabled` | `E.boolean().optional()` | Allow Claude to push proactive mobile notifications |
| `agents` | `E.union([e8i()` | Path to an agent file, relative to the plugin root. When set, the agents/ directory is not auto-loaded — list its files here if you want both. |
| `allow` | `E.array(E.string()).optional()` | Rules for the auto mode classifier allow section. Include the literal string "$defaults" to inherit the built-in rules at that position. |
| `allowAllClaudeAiMcps` | `E.boolean().optional()` | When true (and set in managed settings), claude.ai cloud MCP connectors load alongside managed-mcp.json instead of being suppressed by its exclusive-control lockdown. Default off preserves the lockdown. Read from managed settings only. |
| `allowCrossMarketplaceDependenciesOn` | `E.array(E.string()).optional()` | Marketplace names whose plugins may be auto-installed as dependencies. Only the root marketplace's allowlist applies — no transitive trust. |
| `allowManagedHooksOnly` | `E.boolean().optional()` | When true (and set in managed settings), only hooks from managed settings run. User, project, and local hooks are ignored. |
| `allowManagedMcpServersOnly` | `E.boolean().optional()` | When true (and set in managed settings), allowedMcpServers is only read from managed settings. deniedMcpServers still merges from all sources, so users can deny servers for themselves. Users can still add their own MCP servers, but only the admin-defined allowlist applies. |
| `allowManagedPermissionRulesOnly` | `E.boolean().optional()` | When true (and set in managed settings), only permission rules (allow/deny/ask) from managed settings are respected. User, project, local, and CLI argument permission rules are ignored. |
| `allowedEnvVars` | `E.array(E.string()).optional()` | Explicit list of environment variable names that may be interpolated in header values. Only variables listed here will be resolved; all other $VAR references are left as empty strings. Required for env var interpolation to work. |
| `allowedHttpHookUrls` | `E.array(E.string()).optional()` | Allowlist of URL patterns that HTTP hooks may target. Supports * as a wildcard (e.g. "https://hooks.example.com/*"). When set, HTTP hooks with non-matching URLs are blocked. If undefined, all URLs are allowed. If empty array, no HTTP hooks are allowed. Arrays merge across settings sources (same semantics as allowedMcpServers). |
| `allowedMcpServers` | `E.array(NZn()).optional()` | Enterprise allowlist of MCP servers that can be used. Applies to all scopes including enterprise servers from managed-mcp.json. If undefined, all servers are allowed. If empty array, no servers are allowed. Denylist takes precedence - if a server is on both lists, it is denied. |
| `allowedTools` | `E.array(E.string()).optional()` | Tools allowed when command runs |
| `alwaysThinkingEnabled` | `E.boolean().optional()` | When false, thinking is disabled. When absent or true, thinking is enabled automatically for supported models. |
| `apiKeyHelper` | `E.string().optional()` | Path to a script that outputs authentication values |
| `args` | `E.array(E.string()).optional()` | Argument list for exec form. When present, `command` is resolved as an executable and spawned directly with these arguments — no shell. Path placeholders like ${CLAUDE_PLUGIN_ROOT} are substituted per-element as plain strings, so paths with quotes, $, or backticks never reach a shell parser. When absent, `command` runs through a shell (bash on POSIX, PowerShell on Windows without Git Bash). |
| `argumentHint` | `E.string().optional()` | Hint for command arguments (e.g., "[file]") |
| `ask` | `E.array(d8i()).optional()` | List of permission rules that should always prompt for confirmation |
| `askUserQuestionTimeout` | `E.enum(["60s","5m","10m","never"]).optional().catch(void 0)` | Idle time before Claude's questions auto-continue with any answers selected so far. Defaults to never — auto-continue only runs when explicitly set to 60s/5m/10m. |
| `async` | `E.boolean().optional()` | If true, hook runs in background without blocking |
| `asyncRewake` | `E.boolean().optional()` | If true, hook runs in background and wakes the model on exit code 2 (blocking error). Implies async. |
| `auto` | `E.boolean().optional()` | True when this plugin was pulled in as a dependency rather than installed explicitly. Auto-installed plugins are eligible for removal by the orphan sweep when nothing depends on them. Absent = manual (preserves pre-flag installs). |
| `autoCompactEnabled` | `E.boolean().optional()` | Automatically compact conversation when context fills |
| `autoCompactWindow` | `E.number().int().min(1e5).max(1e6).optional().catch(void 0)` | Auto-compact window size |
| `autoDreamEnabled` | `E.boolean().optional()` | Enable background memory consolidation (auto-dream). When set, overrides the server-side default. |
| `autoMemoryDirectory` | `E.string().optional()` | Custom directory path for auto-memory storage. Supports ~/ prefix for home directory expansion. Ignored if set in projectSettings (checked-in .claude/settings.json) for security. When unset, defaults to ~/.claude/projects/<sanitized-cwd>/memory/. |
| `autoMemoryEnabled` | `E.boolean().optional()` | Enable auto-memory for this project. When false, Claude will not read from or write to the auto-memory directory. |
| `autoScrollEnabled` | `E.boolean().optional()` | Auto-scroll the conversation view to bottom (fullscreen mode only) |
| `autoSubmit` | `E.boolean().optional()` | Submit the prompt when hold-to-talk is released (hold mode only) |
| `autoUpdate` | `E.boolean().optional()` | Whether to automatically update this marketplace and its installed plugins on startup |
| `autoUpdatesChannel` | `E.enum(["latest","stable","rc"]).optional()` | Release channel for auto-updates (latest or stable) |
| `autoUploadSessions` | `E.boolean().optional()` | Mirror local sessions to claude.ai as view-only (no remote control) |
| `availableModels` | `E.array(E.string()).optional()` | Allowlist of models that users can select. Accepts family aliases ("opus" allows any opus version), version prefixes ("opus-4-5" allows only that version), and full model IDs. If undefined, all models are available. If empty array, only the default model is available. Typically set in managed settings by enterprise administrators. |
| `awaySummaryEnabled` | `E.boolean().optional()` | @internal When false, the session recap (shown when you return after being away for 5+ minutes) is disabled. When absent or true, recap is enabled. Hidden from public SDK types until external launch. |
| `awsAuthRefresh` | `E.string().optional()` | Path to a script that refreshes AWS authentication |
| `awsCredentialExport` | `E.string().optional()` | Path to a script that exports AWS credentials |
| `axScreenReader` | `E.boolean().optional()` | Render screen-reader friendly output (flat text, no decorative borders or animations). Overridden by the CLAUDE_AX_SCREEN_READER env var and the --ax-screen-reader CLI flag. |
| `baseRef` | `E.enum(["fresh","head"]).optional()` | Which ref new worktrees branch from. 'fresh' (default) branches from origin/<default-branch> for a clean tree. 'head' branches from your current local HEAD so unpushed commits and feature-branch state are present. Applies to --worktree, EnterWorktree, and agent isolation. |
| `bgIsolation` | `E.enum(["worktree","none"]).optional().catch(void 0)` | Isolation mode for background sessions in this repo. 'worktree' (default) blocks Edit/Write in the main checkout until EnterWorktree is called. 'none' lets background jobs edit the working copy directly. |
| `binaries` | `E.unknown().transform(qnr)` | sha256-pinned files to fetch into bin/ at install time, keyed by basename (target triple encoded in the name) |
| `blockedMarketplaces` | `E.array(BVr()).optional()` | Enterprise blocklist of marketplace sources. When set in managed settings, these exact sources are blocked from being added as marketplaces. The check happens BEFORE downloading, so blocked sources never touch the filesystem. |
| `breakThresholdMinutes` | `E.number().int().positive().optional()` | Minutes of inactivity that count as a break and reset the timer (default 10) |
| `callbackPort` | `E.number().int().positive().optional()` | Fixed loopback callback port for the IdP OIDC login. Only needed if the IdP does not honor RFC 8252 port-any matching. |
| `category` | `E.string().optional()` | Category for organizing plugins (e.g., "productivity", "development") |
| `channelsEnabled` | `E.boolean().optional()` | Managed-org opt-in for channel notifications (MCP servers with the claude/channel capability pushing inbound messages). claude.ai Teams/Enterprise: default off. Console: default on unless managed settings exist. Set true to allow; users then select servers via --channels. |
| `classifyAllShell` | `E.boolean().optional()` | When true, every Bash/PowerShell allow rule is suspended while auto mode is active so all shell commands are routed through the classifier (higher safety, more classifier calls). Default: false. |
| `claudeMd` | `E.string().optional()` | CLAUDE.md-style instructions injected as organization-managed memory. Only honored from managed/policy settings. |
| `claudeMdExcludes` | `E.array(E.string()).optional()` | Glob patterns or absolute paths of CLAUDE.md files to exclude from loading. Patterns are matched against absolute file paths using picomatch. Only applies to User, Project, and Local memory types (Managed/policy files cannot be excluded). Examples: "/home/user/monorepo/CLAUDE.md", "**/code/CLAUDE.md", "**/some-dir/.claude/rules/**" |
| `cleanupPeriodDays` | `E.number().int().positive().optional()` | Number of days to retain chat transcripts before automatic cleanup (default: 30). Minimum 1. Use a large value for long retention; use --no-session-persistence to disable transcript writes entirely. |
| `cli` | `E.array(E.string().max(64)).max(10).optional()` | First command tokens (e.g. ["stripe"]) — exact match against commands run this session. |
| `clientId` | `E.string()` | Claude Code's client_id registered at the IdP |
| `command` | `E.string()` | Shell command to execute |
| `commands` | `E.union([t8i()` | Path to a command file or skill directory, relative to the plugin root. When set, the commands/ directory is not auto-loaded — list its files here if you want both. |
| `commit` | `E.string().optional()` | Attribution text for git commits, including any trailers. Empty string hides attribution. |
| `companyAnnouncements` | `E.array(E.string()).optional()` | Company announcements to display at startup (one will be randomly selected if multiple are provided) |
| `content` | `E.string().optional()` | Inline markdown content for the command |
| `cwd` | `E.array(E.string().max(256)).max(10).optional()` | Glob patterns (e.g. ["Engine/Source/Runtime/Renderer/**"]) — the plugin is relevant when the |
| `daemonColdStart` | `E.enum(["transient","ask"]).optional()` | When no background service is running: 'transient' spawns one for this login session; 'ask' offers to install it persistently |
| `default` | `E.union([E.string(),E.number(),E.boolean(),E.array(E.string())]).optional()` | Default value used when the user provides nothing |
| `defaultEnabled` | `E.boolean().optional()` | Whether the plugin starts enabled when the user has no explicit enabled/disabled setting for it (default: true). Explicit enabledPlugins values always win, and a plugin required by an enabled dependent is enabled regardless of this value. |
| `defaultEnvironmentId` | `E.string().optional()` | Default environment ID to use for cloud sessions |
| `defaultMode` | `E.preprocess(rH,E.enum([...uTe,...Dpc(e)])).optional()` | Default permission mode when Claude Code needs access ('manual' is accepted as an alias for 'default') |
| `defaultShell` | `E.enum(["bash","powershell"]).optional()` | Default shell for input-box ! commands. Defaults to 'bash' on all platforms (no Windows auto-flip). |
| `defaultView` | `E.enum(["chat","transcript"]).optional()` | Default transcript view: chat (SendUserMessage checkpoints only) or transcript (full) |
| `deniedMcpServers` | `E.array($Zn()).optional()` | Enterprise denylist of MCP servers that are explicitly blocked. If a server is on the denylist, it will be blocked across all scopes including enterprise. Denylist takes precedence over allowlist - if a server is on both lists, it is denied. |
| `deny` | `E.array(d8i()).optional()` | List of permission rules for denied operations |
| `description` | `E.string().optional()` | Brief, user-facing explanation of what the plugin provides |
| `diagnostics` | `E.boolean().optional()` | Whether to push publishDiagnostics into the agent context after edits. Set to false to keep LSP navigation (goToDefinition, hover, etc.) but suppress automatic diagnostic injection. Defaults to true. |
| `disableAgentView` | `E.boolean().optional()` | Disable agent view (`claude agents`, `--bg`, /background, the on-demand daemon). Typically set in managed settings. Equivalent to CLAUDE_CODE_DISABLE_AGENT_VIEW=1. |
| `disableAllHooks` | `E.boolean().optional()` | Disable all hooks and statusLine execution |
| `disableArtifact` | `E.boolean().optional()` | Disable the Artifact tool (also via CLAUDE_CODE_DISABLE_ARTIFACT). |
| `disableAutoMode` | `E.enum(["disable"]).optional()` | Disable auto mode |
| `disableBundledSkills` | `E.boolean().optional()` | Disable the skills and workflows that ship with Claude Code: bundled skills and workflows are removed entirely; built-in slash commands stay typable but are hidden from the model. Plugins, .claude/skills/, and .claude/commands/ are unaffected. Equivalent to CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1. |
| `disableBypassPermissionsMode` | `E.enum(["disable"]).optional()` | Disable the ability to bypass permission prompts |
| `disableClaudeAiConnectors` | `E.boolean().optional()` | When true in any settings source, claude.ai MCP cloud connectors are not auto-fetched or connected. Only gates auto-fetched connectors — a claudeai-proxy server passed explicitly (e.g. via --mcp-config or the SDK mcpServers option) still follows the normal MCP config trust flow. Any-source-true wins: a project can opt out, but a project-level false cannot override a user-level true. |
| `disableDeepLinkRegistration` | `E.enum(["disable"]).optional()` | Prevent claude-cli:// protocol handler registration with the OS |
| `disableRemoteControl` | `E.boolean().optional()` | Disable Remote Control (claude.ai/code, `claude remote-control`, `--remote-control`/`--rc`, auto-start, and the in-session toggle). Typically set in managed settings. |
| `disableSideloadFlags` | `E.boolean().optional()` | When true (and set in managed settings), rejects the --plugin-dir, --plugin-url, --agents, and non-sdk --mcp-config CLI flags at startup. Closes the CLI-flag bypass of strictKnownMarketplaces. Pair with allowedMcpServers for per-server MCP control; this setting does not gate other MCP entry points (SDK setMcpServers, claude mcp add, .mcp.json). Also blocks surfaces that spawn the CLI with these flags internally (see settings documentation). Only honored from managed settings; ignored in user/project/local settings. |
| `disableSkillShellExecution` | `E.boolean().optional()` | Disable inline shell execution in skills and custom slash commands from user, project, or plugin sources. Commands are replaced with a placeholder instead of being run. |
| `disableWorkflows` | `E.boolean().optional()` | Disable the Workflows feature (also via CLAUDE_CODE_DISABLE_WORKFLOWS). |
| `disabledMcpjsonServers` | `E.array(E.string()).optional()` | List of rejected MCP servers from .mcp.json |
| `displayName` | `E.string().optional()` | Human-readable name shown in UI (e.g., "GitHub Utils"). Falls back to `name` when omitted. Unlike `name`, may contain spaces and any casing; not used for namespacing or lookup. |
| `doneMeansMerged` | `E.boolean().optional()` | @internal When true, Claude keeps working until the PR is ready for you to merge, a cron/Monitor is armed to resume later, or it hands you a self-contained next step. |
| `editorMode` | `E.enum(fZn).optional().catch(void 0)` | Key binding mode for the prompt input |
| `effortLevel` | `E.enum(["low","medium","high","xhigh"]).optional().catch(void 0)` | Persisted effort level for supported models. |
| `email` | `E.string().optional()` | Contact email for support or feedback |
| `emojiCompletionEnabled` | `E.boolean().optional()` | When false, the :emoji: shortcode typeahead (the suggestion popup and the :name: inline replacement) is disabled. When absent or true, it is enabled. |
| `enableAllProjectMcpServers` | `E.boolean().optional()` | Whether to automatically approve all MCP servers in the project |
| `enableArtifact` | `E.boolean().optional()` | Enable or disable the Artifact tool for this user. Unset defaults to enabled once the feature is available. |
| `enableWorkflows` | `E.boolean().optional()` | Enable or disable the Workflows feature for this user. Unset = default by plan once the feature is available. |
| `enabled` | `E.boolean().optional()` | Show a friendly nudge after sustained continuous use (default false). Must be true for the reminder to fire. |
| `enabledMcpjsonServers` | `E.array(E.string()).optional()` | List of approved MCP servers from .mcp.json |
| `enabledPlugins` | `E.record(E.string(),E.union([E.array(E.string()),E.boolean(),E.undefined()])).optional()` | Enabled plugins using plugin-id@marketplace-id format. Example: { "formatter@anthropic-tools": true }. Also supports extended format with version constraints. Settings precedence is user < project < local < flag < policy, so to disable a plugin that project settings enable, set it to false in .claude/settings.local.json — setting false in ~/.claude/settings.json is overridden by the project. |
| `end` | `E.string().regex(/^([01]?\d|2[0-3]):[0-5]\d$/,'Expected 24-hour local time "HH:MM" (e.g. "07:00")').optional()` | End of the quiet-hours window, 24-hour local time "HH:MM". May be earlier than start for an overnight range. |
| `enforceAvailableModels` | `E.boolean().optional()` | When true and availableModels is a non-empty array, the Default model selection is also constrained: if the default model for the user tier is not in availableModels, Default resolves to the first allowed availableModels entry instead. Has no effect when availableModels is unset or an empty array. Typically set in managed settings by enterprise administrators. |
| `env` | `E.record(E.string(),E.string()).optional()` | Environment variables to set when starting the server |
| `environment` | `E.array(E.string()).optional()` | Entries for the auto mode classifier environment section. Include the literal string "$defaults" to inherit the built-in entries at that position. |
| `evals` | `E.union([E.string(),E.array(E.string())]).optional()` | Path(s) to evaluation query files for `claude plugin eval`. Defaults to `evals/`. |
| `extensionToLanguage` | `E.record(ifg(),vpc()).refine((e)=>Object.keys(e).length>0,{message:"extensionToLanguage must have at least one mapping"})` | Mapping from file extension to LSP language ID. File extensions and languages are derived from this mapping. |
| `extraKnownMarketplaces` | `E.record(E.string(),Pfg()).check((t)=>{for(let[r,n]of Object.entries(t.value))if(n.source.source==="settings"&&n.source.name!==r)t.issues.push({code:"custom",input:n.source.name,path:[r,"source","name"],message:`Settings-sourced marketplace name must match its extraKnownMarketplaces key (got key "${r}" but source.name "${n.source.name}")`})}).optional()` | Additional marketplaces to make available for this repository. Typically used in repository .claude/settings.json to ensure team members have required plugin sources. |
| `fallbackModel` | `E.array(E.string()).optional()` | Fallback model(s) tried in order when the primary model is overloaded or unavailable. Each element accepts a model name or alias; "default" expands to the default model. CLI --fallback-model takes precedence. |
| `fastMode` | `E.boolean().optional()` | When true, fast mode is enabled. When absent or false, fast mode is off. |
| `fastModePerSessionOptIn` | `E.boolean().optional()` | When true, fast mode does not persist across sessions. Each session starts with fast mode off. |
| `feedbackDrafts` | `E.enum(["notify","quiet","off"]).optional()` | Model-drafted feedback (the SendFeedback tool). "notify" (default) shows a one-line notice when a draft is queued; "quiet" shows only the footer counter; "off" disables the tool entirely so drafts are never queued. |
| `feedbackSurveyRate` | `E.number().min(0).max(1).optional()` | Probability (0–1) that the session quality survey appears when eligible. 0.05 is a reasonable starting point. |
| `fileCheckpointingEnabled` | `E.boolean().optional()` | Snapshot files before edits so /rewind can restore them |
| `filesRead` | `E.array(E.string().max(256)).max(10).optional()` | Glob patterns (e.g. ["**/*.tf"]) — the plugin is relevant when a file Claude has read this session matches any pattern. Matched against read-file paths, forward-slash normalized, case-insensitive. |
| `footerLinksRegexes` | `E.array(Dfg().catch(Gpc)).transform((t)=>t.filter((r)=>r!==Gpc)).optional().catch(void 0)` | Extra clickable footer badges that appear when a regex matches turn output (tool results and assistant responses). Read from user, flag, and managed settings only; ignored in project .claude/settings.json and local .claude/settings.local.json. At most 5 badges render; the oldest is displaced by newer matches and /clear removes them. Use to surface IDs printed by project CLIs as session links. |
| `forceLoginGatewayUrl` | `E.string().url().optional().catch(void 0)` | @internal Cloud gateway URL to pre-fill and auto-connect to during login. Typically set in local managed settings alongside forceLoginMethod: "gateway" so users never type the URL. Hidden from public SDK types until Cloud gateway is documented. |
| `forceLoginMethod` | `E.enum(["claudeai","console","gateway"]).optional().catch(void 0)` | Force a specific login method: "claudeai" for Claude Pro/Max, "console" for Console billing, "gateway" for the Cloud gateway OIDC device flow |
| `forceLoginOrgUUID` | `E.union([E.string(),E.array(E.string())]).optional()` | Organization UUID to require for OAuth login. Accepts a single UUID string or an array of UUIDs (any one is permitted). When set in managed settings, login fails if the authenticated account does not belong to a listed organization. |
| `forceRemoteSettingsRefresh` | `E.boolean().optional()` | When set in managed settings, the CLI blocks startup until remote managed settings are freshly fetched, and exits if the fetch fails |
| `forceRemoveDeletedPlugins` | `E.boolean().optional()` | When true, plugins removed from this marketplace will be automatically uninstalled and flagged for users |
| `gcpAuthRefresh` | `E.string().optional()` | Command to refresh GCP authentication (e.g., gcloud auth application-default login) |
| `gitCommitSha` | `E.string().optional()` | Git commit SHA for git-based plugins (for version tracking) |
| `hard_deny` | `E.array(E.string()).optional()` | Rules for the auto mode classifier HARD BLOCK section — security boundaries that user intent does NOT clear. Include the literal string "$defaults" to inherit the built-in rules at that position. |
| `headers` | `E.record(E.string(),E.string()).optional()` | Additional headers to include in the request. Values may reference environment variables using $VAR_NAME or ${VAR_NAME} syntax (e.g., "Authorization": "Bearer $MY_TOKEN"). Only variables listed in allowedEnvVars will be interpolated. |
| `hideVimModeIndicator` | `E.boolean().optional()` | Hide the built-in `-- INSERT --` / `-- VISUAL --` indicator below the prompt. Use this when your status line script renders `vim.mode` itself. |
| `homepage` | `E.string().url().optional()` | Plugin homepage or documentation URL |
| `hooks` | `E.array(gpc())` | List of hooks to execute when the matcher matches |
| `hostPattern` | `E.string()` | Regex pattern to match the host/domain extracted from any marketplace source type. For github sources, matches against github.com. For git sources (SSH or HTTPS), extracts the hostname from the URL. Use in strictKnownMarketplaces to allow all marketplaces from a specific host (e.g., "^github\.mycompany\.com$"). |
| `hosts` | `E.array(E.string().max(128)).max(20).optional()` | Hostnames (e.g. ["api.stripe.com"]) — exact, case-insensitive match against hostnames seen in https?:// URLs in bash commands run this session. Bare hostname only: lowercase, no scheme, no port, no path. |
| `httpHookAllowedEnvVars` | `E.array(E.string()).optional()` | Allowlist of environment variable names HTTP hooks may interpolate into headers. When set, each hook's effective allowedEnvVars is the intersection with this list. If undefined, no restriction is applied. Arrays merge across settings sources (same semantics as allowedMcpServers). |
| `id` | `E.string()` | Unique identifier for this SSH config. Used to match configs across settings sources. |
| `includeCoAuthoredBy` | `E.boolean().optional()` | Deprecated: Use attribution instead. Whether to include Claude's co-authored by attribution in commits and PRs (defaults to true) |
| `includeGitInstructions` | `E.boolean().optional()` | Include built-in commit and PR workflow instructions in Claude's system prompt (default: true) |
| `initializationOptions` | `E.unknown().optional()` | Initialization options passed to the server during initialization |
| `input` | `E.record(E.string(),E.unknown()).optional()` | Arguments passed to the MCP tool. String values support ${path} interpolation from the hook input JSON (e.g. "${tool_input.file_path}"). |
| `inputNeededNotifEnabled` | `E.boolean().optional()` | Push to mobile when a permission prompt or question is waiting |
| `installLocation` | `E.string()` | Local cache path where marketplace manifest is stored |
| `installPath` | `E.string()` | Absolute path to the installed plugin directory |
| `installedAt` | `E.string()` | ISO 8601 timestamp of installation |
| `intervalMinutes` | `E.number().int().positive().optional()` | Minutes of continuous use before the reminder fires (default 30). Re-fires every interval until you take a break. |
| `isolatePeerMachines` | `E.boolean().optional()` | Require explicit approval before SendMessage can reach a peer session on another machine via Remote Control |
| `issuer` | `E.string().url()` | IdP issuer URL for OIDC discovery |
| `keywords` | `E.array(E.string()).optional()` | Tags for plugin discovery and categorization |
| `label` | `E.string().optional()` | Badge text. {name} placeholders filled from named capture groups; defaults to the full match. |
| `language` | `E.string().optional()` | Preferred language for Claude responses and voice dictation (e.g., "japanese", "spanish") |
| `lastUpdated` | `E.string().optional()` | ISO 8601 timestamp of last update |
| `license` | `E.string().optional()` | SPDX license identifier (e.g., MIT, Apache-2.0) |
| `lspServers` | `E.union([JDt()` | Path to .lsp.json configuration file relative to plugin root |
| `matcher` | `E.string().optional()` | String pattern to match (e.g. tool names like "Write") |
| `max` | `E.number().optional()` | Maximum value (number type only) |
| `maxRestarts` | `E.number().int().nonnegative().optional()` | Maximum number of restart attempts before giving up |
| `mcpServers` | `E.union([JDt()` | MCP servers to include in the plugin (in addition to those in the .mcp.json file, if it exists) |
| `message` | `E.string().optional()` | Custom reminder text. Leave unset for a rotating set of friendly nudges. |
| `metadata` | `E.preprocess((e)=>as(e)?e:void 0,E.record(E.string(),E.unknown()).optional())` | Free-form metadata for the plugin author's own use (e.g. entitlement or catalog fields). Preserved on the parsed manifest but not read by Claude Code. |
| `min` | `E.number().optional()` | Minimum value (number type only) |
| `minimumVersion` | `E.string().optional()` | Minimum version to stay on - prevents downgrades when switching to stable channel |
| `mode` | `E.enum(["hold","tap"]).optional()` | 'hold' (default): hold to talk. 'tap': tap to start, tap to stop+submit. |
| `model` | `E.string().optional()` | Model to use for this prompt hook (e.g., "claude-sonnet-5"). If not specified, uses the default small fast model. |
| `modelOverrides` | `E.record(E.string(),E.string()).optional()` | Override mapping from Anthropic model ID (e.g. "claude-opus-4-6") to provider-specific model ID (e.g. a Bedrock inference profile ARN). Typically set in managed settings by enterprise administrators. |
| `monitors` | `E.union([JDt()` | Path to a JSON file containing the monitors array, relative to the plugin root |
| `multiple` | `E.boolean().optional()` | For string type: allow an array of strings |
| `name` | `E.string().min(1,"Author name cannot be empty")` | Display name of the plugin author or organization |
| `once` | `E.boolean().optional()` | If true, hook runs once and is removed after execution |
| `options` | `E.record(E.string(),E.union([E.string(),E.number(),E.boolean(),E.array(E.string())])).optional()` | Non-sensitive option values from plugin manifest userConfig, keyed by option name. Sensitive values go to secure storage instead. |
| `otelHeadersHelper` | `E.string().optional()` | Path to a script that outputs OpenTelemetry headers |
| `outputStyle` | `E.string().optional()` | Controls the output style for assistant responses |
| `outputStyles` | `E.union([dTe()` | Path to an output-styles directory or file, relative to the plugin root. When set, the output-styles/ directory is not auto-loaded — list its files here if you want both. |
| `parentSettingsBehavior` | `E.enum(["first-wins","merge"]).optional()` | Controls whether the SDK parent tier (Options.managedSettings / --managed-settings) layers under this admin tier. "first-wins" (default): parent is dropped — admin tiers are the only policy |
| `path` | `E.string().optional()` | Path to marketplace.json within repo (defaults to .claude-plugin/marketplace.json) |
| `pathPattern` | `E.string()` | Regex pattern matched against the .path field of file and directory sources. Use in strictKnownMarketplaces to allow filesystem-based marketplaces alongside hostPattern restrictions for network sources. Use ".*" to allow all filesystem paths, or a narrower pattern (e.g., "^/opt/approved/") to restrict to specific directories. |
| `pattern` | `E.string().max(256)})).max(10).optional()` | Dependency declared in a package manifest. Each {file, pattern} is a pair of RegExp sources: `file` matches the manifest filename (package.json, go.mod, requirements.txt, …); `pattern` matches the dependency declaration inside that file. Evaluated against files read this session. |
| `plansDirectory` | `E.string().optional()` | Custom directory for plan files, relative to project root. If not set, defaults to ~/.claude/plans/ |
| `plugin` | `E.string()})).optional()` | Managed-org allowlist of channel plugins. When set, replaces the default Anthropic allowlist — admins decide which plugins may push inbound messages. Undefined falls back to the default. Requires channelsEnabled: true. |
| `pluginRoot` | `E.string().optional()` | Base path for relative plugin sources |
| `pluginSuggestionMarketplaces` | `E.array(E.string()).optional()` | Marketplace names whose plugins may surface as contextual install suggestions (relevance-based tips). No marketplace-declared suggestions surface without this allowlist; the built-in first-party frontend-design tip is unaffected. Only honored when set in managed settings (policy scope); the key is ignored in user, project, and local settings. A name only takes effect when the marketplace is registered on the machine AND its registered source is also declared in managed settings, either as the extraKnownMarketplaces entry for that name or as an entry of strictKnownMarketplaces. A marketplace registered from a different source under an allowlisted name is ignored. The official marketplace is exempt from the source requirement: allowlisting its name alone suffices, since that name can only register from the official Anthropic source. |
| `pluginTrustMessage` | `E.string().optional()` | Custom message to append to the plugin trust warning shown before installation. Only read from policy settings (managed-settings.json / MDM). Useful for enterprise administrators to add organization-specific context (e.g., "All plugins from our internal marketplace are vetted and approved."). |
| `plugins` | `E.array(hfg())` | Plugin entries declared inline in settings.json |
| `pr` | `E.string().optional()` | Attribution text for pull request descriptions. Empty string hides attribution. |
| `prUrlTemplate` | `E.string().optional()` | URL template for PR links in the footer link badges and inline messages. The detected git PR is rendered as the first footer-link badge. Placeholders: {host} {owner} {repo} {number} {url}. Example: "https://reviews.example.com/{owner}/{repo}/pull/{number}" |
| `precomputeCompactionEnabled` | `E.boolean().optional()` | Precompute the compaction summary in the background before it is needed. Only applies when auto-compact is on. |
| `preferredNotifChannel` | `E.enum(fae).optional().catch(void 0)` | Preferred OS notification channel |
| `prefersReducedMotion` | `E.boolean().optional()` | Reduce or disable animations for accessibility (spinner shimmer, flash effects, etc.) |
| `processWrapper` | `E.string().optional()` | Corporate launcher argv prefix for the background-agent supervisor, the sessions and workers it hosts, and the other covered background processes listed in the Claude Code corporate-launcher documentation. Equivalent to the CLAUDE_CODE_PROCESS_WRAPPER environment variable, which takes precedence when set. Honored from managed settings, a --settings/SDK-supplied settings file, and user settings, in that precedence order; project and local settings are ignored. |
| `projectPath` | `E.string().optional()` | Project path (required for project/local scopes) |
| `prompt` | `E.string()` | Prompt to evaluate with LLM. Use $ARGUMENTS placeholder for hook input JSON. |
| `promptSuggestionEnabled` | `E.boolean().optional()` | When false, prompt suggestions are disabled. When absent or true, prompt suggestions are enabled. |
| `proxyAuthHelper` | `E.string().optional()` | Shell command that outputs a Proxy-Authorization header value (EAP) |
| `ref` | `E.string().optional()` | Git branch or tag to use (e.g., "main", "v1.0.0"). Defaults to repository default branch. |
| `refreshInterval` | `E.number().min(1).optional().catch(void 0)` | Re-run the status line command every N seconds in addition to event-driven updates |
| `registry` | `E.string().url().optional()` | Custom NPM registry URL (defaults to using system default, likely npmjs.org) |
| `remoteControlAtStartup` | `E.boolean().optional()` | Start Remote Control bridge automatically each session |
| `renames` | `E.record(E.string(),E.string().nullable()).optional().catch(void 0)` | Append-only map of old plugin name → current name (or null when removed). The loader follows this on plugin-not-found and migrates user settings to the new name. |
| `repo` | `E.string()` | GitHub repository in owner/repo format |
| `repository` | `E.string().optional()` | Source code repository URL |
| `required` | `E.boolean().optional()` | If true, validation fails when this field is empty |
| `requiredMaximumVersion` | `E.string().optional()` | Maximum Claude Code version allowed to start. If the running version is newer, Claude Code exits at startup with instructions to install an approved version. Only enforced from managed (policy) settings. |
| `requiredMinimumVersion` | `E.string().optional()` | Minimum Claude Code version required to start. If the running version is older, Claude Code exits at startup with instructions to update. Only enforced from managed (policy) settings. |
| `resolvedVersion` | `E.string().optional()` | Tag-derived semver this install resolved to (when fetched via a version constraint). Used by verifyAndDemote in preference to manifest.version, since the upstream may have forgotten to bump plugin.json. |
| `respectGitignore` | `E.boolean().optional()` | Whether file picker should respect .gitignore files (default: true). Note: .ignore files are always respected. |
| `respondToBashCommands` | `E.boolean().optional()` | Whether Claude responds after an input-box ! bash command runs. Set to false to add the command output to context without a response. Default: true. |
| `restartOnCrash` | `E.boolean().optional()` | Whether to restart the server if it crashes |
| `rewakeMessage` | `E.string().min(1).optional()` | @internal Custom prefix for the system-reminder shown to the model when an asyncRewake hook exits with code 2. The hook output is appended after this prefix. |
| `rewakeSummary` | `E.string().min(1).optional()` | @internal One-line summary shown to the user in the terminal when an asyncRewake hook exits with code 2. Defaults to "Stop hook feedback". |
| `sensitive` | `E.boolean().optional()` | If true, masks dialog input and stores value in secure storage (keychain/credentials file) instead of settings.json |
| `server` | `E.string()` | Name of an already-configured MCP server to invoke |
| `serverCommand` | `E.array(E.string()).min(1,"Server command must have at least one element (the command)").optional()` | Command array [command, ...args] to match exactly for allowed stdio servers |
| `serverName` | `E.string().regex(/^[a-zA-Z0-9_-]+$/,"Server name can only contain letters, numbers, hyphens, and underscores").optional()` | Name of the MCP server that users are allowed to configure |
| `serverUrl` | `E.string().optional()` | URL pattern with wildcard support (e.g., "https://*.example.com/*") for allowed remote MCP servers |
| `sessionUrl` | `E.boolean().optional()` | Whether to append the claude.ai session link to commits and PRs created from web or Remote Control sessions (default: true). Set to false to omit the Claude-Session trailer and PR-body link. |
| `settings` | `E.unknown().optional()` | Settings passed to the server via workspace/didChangeConfiguration |
| `shell` | `E.enum(fpc).optional()` | Shell interpreter. 'bash' uses your $SHELL (bash/zsh/sh); 'powershell' uses pwsh. Defaults to bash (powershell on Windows without Git Bash). |
| `showClearContextOnPlanAccept` | `E.boolean().optional()` | When true, the plan-approval dialog offers a "clear context" option. Defaults to false. |
| `showMessageTimestamps` | `E.boolean().optional()` | Stamp each message with its arrival time |
| `showThinkingSummaries` | `E.boolean().optional()` | Request API-side thinking summaries and show them in the conversation and in the transcript view (ctrl+o). Set explicitly to override the default for your install. |
| `showTurnDuration` | `E.boolean().optional()` | Show "Cooked for Nm Ns" after each assistant turn |
| `shutdownTimeout` | `E.number().int().positive().optional()` | Maximum time to wait for graceful shutdown (milliseconds) |
| `skillListingBudgetFraction` | `E.number().gt(0).lte(1).optional()` | Fraction of the context window (in characters) reserved for the skill listing sent to Claude (default: 0.01 = 1%). When the listing exceeds this, descriptions are shortened to fit. Raise to opt in to higher per-turn context cost. |
| `skillListingMaxDescChars` | `E.number().int().positive().optional()` | Per-skill description character cap in the skill listing sent to Claude (default: 1536). Descriptions longer than this are truncated. Raise to opt in to higher per-turn context cost. |
| `skillOverrides` | `E.record(E.string(),E.enum(["on","name-only","user-invocable-only","off"])).optional()` | Per-skill listing overrides keyed by skill name. "name-only" lists the skill without its description; "user-invocable-only" hides it from the model but keeps /name; "off" hides it from both. Absent = on. |
| `skills` | `E.union([Spc()` | Path to a skill directory, relative to the plugin root ("." / "./" denote the plugin root itself). Loaded in addition to the skills/ directory (except: for a marketplace entry whose source resolves to the marketplace root, declaring a specific subdirectory replaces the skills/ scan). |
| `skipAutoPermissionPrompt` | `E.boolean().optional()` | Whether the user has accepted the auto mode opt-in dialog |
| `skipDangerousModePermissionPrompt` | `E.boolean().optional()` | Whether the user has accepted the bypass permissions mode dialog |
| `skipLfs` | `E.boolean().optional()` | Skip Git LFS smudge during clone and update (sets GIT_LFS_SKIP_SMUDGE=1) so LFS pointer files stay as pointers instead of downloading their content. Use for marketplaces hosted in repos with large LFS objects. |
| `skipWebFetchPreflight` | `E.boolean().optional()` | Skip the WebFetch blocklist check for enterprise environments with restrictive security policies |
| `skipWorkflowUsageWarning` | `E.boolean().optional()` | @internal Whether the user has accepted the multi-agent workflow usage warning. Until set, auto permission mode prompts before running a workflow. |
| `soft_deny` | `E.array(E.string()).optional()` | Rules for the auto mode classifier SOFT BLOCK section — destructive/irreversible actions that user intent can clear. Include the literal string "$defaults" to inherit the built-in rules at that position. |
| `source` | `E.literal("npm"),package:xpc()` | NPM package containing marketplace.json |
| `sparsePaths` | `E.array(E.string()).optional()` | Directories to include via git sparse-checkout (cone mode). Use for monorepos where the marketplace lives in a subdirectory. Example: [".claude-plugin", "plugins"]. If omitted, the full repository is cloned. |
| `spinnerTipsEnabled` | `E.boolean().optional()` | Whether to show tips in the spinner |
| `sshHost` | `E.string()` | SSH host in format "user@hostname" or "hostname", or a host alias from ~/.ssh/config |
| `sshIdentityFile` | `E.string().optional()` | Path to SSH identity file (private key) |
| `sshPort` | `E.number().int().optional()` | SSH port (default: 22) |
| `start` | `E.string().regex(/^([01]?\d|2[0-3]):[0-5]\d$/,'Expected 24-hour local time "HH:MM" (e.g. "22:00")').optional()` | Start of the quiet-hours window, 24-hour local time "HH:MM". |
| `startDirectory` | `E.string().optional()` | Default working directory on the remote host. Supports tilde expansion (e.g. ~/projects). If not specified, defaults to the remote user home directory. Can be overridden by the [dir] positional argument in `claude ssh <config> [dir]`. |
| `startupTimeout` | `E.number().int().positive().optional()` | Maximum time to wait for server startup (milliseconds) |
| `statusMessage` | `E.string().optional()` | Custom status message to display in spinner while hook runs |
| `strict` | `E.boolean().optional().default(!0)` | Require the plugin manifest to be present in the plugin folder. If false, the marketplace entry provides the manifest. |
| `strictKnownMarketplaces` | `E.array(BVr()).optional()` | Enterprise strict list of allowed marketplace sources. When set in managed settings, ONLY these exact sources can be added as marketplaces. The check happens BEFORE downloading, so blocked sources never touch the filesystem. Note: this is a policy gate only — it does NOT register marketplaces. To pre-register allowed marketplaces for users, also set extraKnownMarketplaces. |
| `strictPluginOnlyCustomization` | `E.preprocess((t)=>Array.isArray(t)?t.filter((r)=>Wlt.includes(r)):t,E.union([E.boolean(),E.array(E.enum(Wlt))])).optional().catch(void 0)` | When set in managed settings, blocks non-plugin customization sources for the listed surfaces. Array form locks specific surfaces (e.g. ["skills", "hooks"]); `true` locks all four; `false` is an explicit no-op. Blocked: ~/.claude/{surface}/, .claude/{surface}/ (project), settings.json hooks, .mcp.json. NOT blocked: managed (policySettings) sources, plugin-provided customizations. Composes with strictKnownMarketplaces for end-to-end admin control — plugins gated by marketplace allowlist, everything else blocked here. |
| `switchModelsOnFlag` | `E.boolean().optional()` | When safeguards flag a message, automatically switch to a different model to keep chatting. When off, your session will pause instead. |
| `symlinkDirectories` | `E.array(E.string()).optional()` | Directories to symlink from main repository to worktrees to avoid disk bloat. Must be explicitly configured - no directories are symlinked by default. Common examples: "node_modules", ".cache", ".bin" |
| `syntaxHighlightingDisabled` | `E.boolean().optional()` | Whether to disable syntax highlighting in diffs |
| `tags` | `E.array(E.string()).optional()` | Tags for searchability and discovery |
| `teammateMode` | `E.enum(tpc).optional().catch(void 0)` | How spawned teammates execute (tmux, iterm2, in-process, auto) |
| `terminalProgressBarEnabled` | `E.boolean().optional()` | Emit OSC 9;4 progress sequences during long operations |
| `terminalTitleFromRename` | `E.boolean().optional()` | Whether /rename updates the terminal tab title (defaults to true). Set to false to keep auto-generated topic titles. |
| `theme` | `E.union([E.enum(bVr),E.string().startsWith("custom:").transform((t)=>t)]).optional().catch(void 0)` | Color theme for the UI |
| `themes` | `E.union([dTe()` | Path to a themes directory or file, relative to the plugin root. When set, the themes/ directory is not auto-loaded — list its files here if you want both. |
| `timeout` | `E.number().positive().optional()` | Timeout in seconds for this specific command |
| `tips` | `E.array(E.string())}).optional()` | Override spinner tips. tips: array of tip strings. excludeDefault: if true, only show custom tips (default: false). |
| `title` | `E.string()` | Human-readable label shown in the config dialog |
| `todoFeatureEnabled` | `E.boolean().optional()` | Enable the todo / task tracking panel |
| `tool` | `E.string()` | Name of the tool on that server to call |
| `topic` | `E.string().max(64).optional()` | What the user is working with when this plugin is relevant — fills "Working with {topic}?". Often the product name (e.g. "Stripe"); use a domain (e.g. "design") when the plugin name does not read naturally as a topic. Defaults to the plugin name with each hyphen-segment capitalized. |
| `totalTokensReminder` | `E.enum(["off","infinite","fixed","countdown","padded-countdown"]).optional()` | @internal Emit a <total_tokens>N tokens left</total_tokens> block in the system prompt, after each tool result, and (when totalTokensReminderAfterUserTurn is on) after each regular user prompt. 'infinite' uses the literal value Infinite, 'fixed' uses 5000000, 'countdown' uses the live remaining context-window tokens, 'padded-countdown' counts down from totalTokensReminderBudget (re-anchoring to the full budget on each regular user prompt when totalTokensReminderAfterUserTurn is on — task-budget semantics). Defaults to off. Env var CLAUDE_CODE_TOTAL_TOKENS_REMINDER overrides. |
| `totalTokensReminderAfterUserTurn` | `E.boolean().optional()` | @internal When true, emit the totalTokensReminder block after each regular user prompt and (for 'padded-countdown') re-anchor the task budget to the full configured value at the start of each user turn. When false, the reminder appears only in the system prompt and after each tool-result batch, and 'padded-countdown' counts down over the whole session. Defaults to off. Env var CLAUDE_CODE_TOTAL_TOKENS_REMINDER_AFTER_USER_TURN overrides; server-controlled via GrowthBook tengu_lapis_anchor_user_turn. |
| `totalTokensReminderBudget` | `E.number().int().positive().optional()` | @internal Starting budget (tokens) for totalTokensReminder 'padded-countdown' mode. Defaults to 15000000. Server-controlled via GrowthBook; env var CLAUDE_CODE_TOTAL_TOKENS_REMINDER_BUDGET overrides. |
| `transport` | `E.enum(["stdio","socket"]).default("stdio")` | Communication transport mechanism |
| `tui` | `E.enum(["default","fullscreen"]).optional()` | Terminal UI renderer. "fullscreen" uses the flicker-free alt-screen renderer with virtualized scrollback (equivalent to CLAUDE_CODE_NO_FLICKER=1). "default" uses the classic main-screen renderer. |
| `type` | `E.literal("command")` | Shell command hook type |
| `ultracode` | `E.boolean().optional().catch(void 0)` | Enable ultracode for the session: xhigh effort plus standing dynamic-workflow orchestration. Session-scoped — typically provided via --settings or the apply_flag_settings control request; interactive toggles never persist it. Requires workflows to be enabled and an xhigh-capable model. |
| `url` | `E.string().url()` | URL to POST the hook input JSON to |
| `useAutoModeDuringPlan` | `E.boolean().optional()` | Whether plan mode uses auto mode semantics when auto mode is available (default: true) |
| `userConfig` | `E.record(E.string().regex(/^[A-Za-z_]\w*$/,"Option keys must be valid identifiers (letters, digits, underscore; no leading digit) \u2014 they become CLAUDE_PLUGIN_OPTION_<KEY> env vars in hooks"),Rpc()).optional()` | User-configurable values this plugin needs. Prompted at enable time. Non-sensitive values saved to settings.json; sensitive values to secure storage. Available as ${user_config.KEY} in MCP/LSP server config, hook commands, and (non-sensitive only) skill/agent content. Keep sensitive value counts small. |
| `verbose` | `E.boolean().optional()` | Show full tool output instead of truncated summaries |
| `verbs` | `E.array(E.string())}).optional()` | Customize spinner verbs. mode: "append" adds verbs to defaults, "replace" uses only your verbs. |
| `version` | `E.string().optional()` | Semantic version (e.g., 1.2.3) following semver.org specification |
| `viewMode` | `E.enum(["default","verbose","focus"]).optional().catch(void 0)` | Default transcript view mode on startup |
| `vimInsertModeRemaps` | `E.record(E.string(),E.unknown()).optional().catch(void 0)` | Vim INSERT-mode key-sequence remaps, e.g. {"jj": "<Esc>"}. Each key is exactly two printable characters typed in sequence; "<Esc>" (return to NORMAL mode) is the only supported target. Applies when editorMode is "vim". |
| `voiceEnabled` | `E.boolean().optional()` | Enable voice mode (hold-to-talk dictation) |
| `wheelScrollAccelerationEnabled` | `E.boolean().optional()` | Ramp mouse-wheel scroll speed during fast scrolls (fullscreen mode only) |
| `when` | `E.union([E.literal("always"),E.string().startsWith("on-skill-invoke:").refine((e)=>e.length>16,{message:"on-skill-invoke: must specify a skill name"})]).default("always")` | Arm trigger. "always" arms at session start and on plugin reload. "on-skill-invoke:<skill>" arms the first time that skill is dispatched (via Skill tool or slash command). |
| `workflowKeywordTriggerEnabled` | `E.boolean().optional()` | Enable the "ultracode" keyword trigger: including the keyword in a prompt opts that turn into the Workflow tool. Set to false to disable the trigger. Default: true. |
| `workflowSizeGuideline` | `E.enum(["unrestricted","small","medium","large"]).optional()` | Advisory size guideline for the dynamic workflows Claude writes: "small" aims for fewer than 5 agents, "medium" (the default) fewer than 15, "large" fewer than 50, and "unrestricted" sends no guideline. A value here — including from managed settings — takes precedence over the "Dynamic workflow size" choice in /config, and that /config row is hidden while a settings file provides the key. This is a guideline, not an enforced limit. |
| `workflows` | `E.union([dTe()` | Path to a workflows directory or .js file, relative to the plugin root. When set, the workflows/ directory is not auto-loaded — list its files here if you want both. |
| `workspaceFolder` | `E.string().optional()` | Workspace folder path to use for the server |
| `wslInheritsWindowsSettings` | `E.boolean().optional()` | When set to true in either admin-only Windows source — the HKLM SOFTWARE/Policies/ClaudeCode registry key or C:/Program Files/ClaudeCode/managed-settings.json — WSL reads managed settings from the full Windows policy chain (HKLM, C:/Program Files/ClaudeCode via DrvFs, HKCU) in addition to /etc/claude-code. Windows sources take priority. The flag is also required in HKCU itself for HKCU policy to apply on WSL (double opt-in: admin enables the chain, user confirms HKCU). On native Windows the flag has no effect. |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the shipped 2.1.222 binary is the corpus
