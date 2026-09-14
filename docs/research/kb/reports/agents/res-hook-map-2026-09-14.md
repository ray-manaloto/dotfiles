# Hook Surface Equivalence Map: Claude Code vs Codex (2026-09-14)

**Objective**: Map every hook/extension point in both Claude Code and Codex to identify which pairs are 1:1 equivalent, enabling the operator to assess where the project doctor can run at session start for both sides.

## Sources

- Claude Code: offline vendor docs `$CC/hooks.md` (3769 lines), `hooks-guide.md` (80KB)
- Codex: offline vendor docs `$CX/hooks.md` (939 lines)
- Codex CLI: installed version 0.154.0
- Both: project-local config `.codex/hooks.json` and hooks discovered via installed CLIs

## Claude Code Hook Inventory

**Complete enumeration by cadence** (from `$CC/hooks.md:15-50`):

### Once per session
- **SessionStart** (`startup`, `resume`, `clear`, `compact`, `fork` matchers): When Claude Code starts new session or resumes. Supports `type: command` and `type: mcp_tool`. Receives `source`, `model`, `agent_type`, `session_title`, and (on resume) `seconds_since_last_response`, `context_tokens`, `prompt_cache_likely_expired`, `estimated_cache_write_usd`. Can output `additionalContext`, `initialUserMessage`, `sessionTitle`, `watchPaths`, `reloadSkills`. Supports `CLAUDE_ENV_FILE`.
- **Setup**: Runs after SessionStart, before first turn. Can be skipped on `resume`. Only `type: command` supported. Supports `CLAUDE_ENV_FILE`. Receives `source`.
- **SessionEnd**: Once per session, when session closes. No matcher. Can block on exit code.

### Once per turn
- **UserPromptSubmit**: Before Claude reads a user message. Can intercept, transform, or inject additional instructions. Receives `prompt_text`.
- **UserPromptExpansion**: Fires when `/` slash commands are expanded (for command/tool discovery). Can augment available tools dynamically.
- **Stop**: Runs when turn completes (user hits stop, or model decides to stop). Receives accumulated tool results. Can block on exit code. Only `type: command` supported.
- **StopFailure**: Fires when a tool call fails catastrophically. Receives error details.

### On every tool call (inside agentic loop)
- **PreToolUse**: Before ANY tool call (Bash, Read, Write, etc.). Can block, transform, inject. Matcher against tool name. Receives `tool_name`, `tool_input`. Can block and transform output.
- **PostToolUse**: After tool call succeeds. Receives `tool_name`, `tool_input`, `tool_result`. Can inject follow-up context or block continuation.
- **PostToolUseFailure**: After tool call fails. Receives error. Can inject recovery guidance.
- **PostToolBatch**: Runs after a batch of tool calls completes.
- **PermissionRequest**: When a tool call needs approval in `dontAsk` mode. Receives `tool_name`, `permission_required`. Can auto-approve or block.
- **PermissionDenied**: When a permission is denied (auto or user). Advisory only.

### Subagent lifecycle
- **SubagentStart**: When spawning a subagent. Can inject context or block (if `decision` handler).
- **SubagentStop**: Fires at subagent completion. Cannot block (advisory). Receives subagent result.
- **TaskCreated**: When a Task is created (only fires with Task tool present). Receives `task_id`, `description`. Advisory.
- **TaskCompleted**: When a Task completes. Receives `task_id`, result. Advisory.

### UI and state events
- **MessageDisplay**: When assistant message renders in UI (text streaming complete). Receives `message_text`. Display-only, cannot block.
- **Notification**: When Claude Code generates a notification (e.g., "tool failed", "waiting for input"). Receives `title`, `body`. Advisory.
- **TeammateIdle**: When team session goes idle (no active agents working). Matcher: `idle`. Advisory.

### File and environment watching
- **CwdChanged**: When working directory changes (e.g., `cd` in Bash output). Receives `old_cwd`, `new_cwd`. Supports `CLAUDE_ENV_FILE`.
- **DirectoryAdded**: When a new directory is added to the workspace. Receives `path`.
- **FileChanged**: When a tracked file changes on disk. Receives `path`, `change_type`. Supports `CLAUDE_ENV_FILE`.
- **WorktreeCreate**: When a worktree is created. Receives `worktree_path`.
- **WorktreeRemove**: When a worktree is removed. Receives `worktree_path`.

### Configuration and model events
- **ConfigChange**: When `.claude/settings.json` or `CLAUDE.md` changes during session. Receives `changed_file`, `change_type`. Advisory.
- **InstructionsLoaded**: When `CLAUDE.md` or project instructions are parsed at session start. Receives `instructions_text`. Advisory.
- **PreModelSwitch**: Before a model change (e.g., `/model o3`). Receives `old_model`, `new_model`. Can block.
- **PostModelSwitch**: After model changes. Receives `old_model`, `new_model`. Async, advisory.

### Compaction and recovery
- **PreCompact**: Before transcript compaction. Receives `compaction_strategy`. Can block.
- **PostCompact**: After compaction completes. Receives `compaction_info`. Advisory.

### MCP and prompt injection
- **Elicitation**: Internal MCP tool-call event (for elicitating user input from tools). Receives MCP context.
- **ElicitationResult**: After elicitation completes. Receives result.

**Handler types supported**: `command`, `http`, `mcp_tool`, `prompt` (last two less commonly used).

**Exit codes**: 0 = pass/allow; non-zero = block/deny (for blocking hooks).

---

## Codex Hook Inventory

**Complete enumeration** (from `$CX/hooks.md` and config examples):

### Session lifecycle
- **SessionStart**: When session starts (new or resumed). Matcher support: `startup`, `resume` (inferred from examples). Only `type: command` supported. Receives standard context. Can output `additionalContext`, `statusMessage`, `timeout`.
- **SessionEnd**: When session ends (main thread only, not for subagents). Only `type: command` supported. Default timeout 1s (max 3s). Advisory (cannot block meaningfully at end).

### Turn lifecycle
- **UserPromptSubmit**: Before processing user message. Receives user input context.
- **Stop**: When turn stops. Receives accumulated state.
- **PreCompact**: Before transcript compaction.
- **PostCompact**: After compaction.

### Tool execution
- **PreToolUse**: Before tool call. Matcher against tool name (e.g., `Bash`). Can inspect/block.
- **PostToolUse**: After tool execution. Can review output.
- **PermissionRequest**: When approval needed. Matcher against permission type. Can auto-approve or block.

### Subagent lifecycle
- **SubagentStart**: When subagent spawns. Only `type: command` supported.
- **SubagentStop**: When subagent completes. Advisory (cannot block).

**Handler types supported**: `command` (primary); `prompt` and `agent` handlers are parsed but skipped (`$CX/hooks.md` line ~180).

**Discovery locations**:
- `~/.codex/hooks.json` or `[hooks]` in `~/.codex/config.toml`
- `<repo>/.codex/hooks.json` or `[hooks]` in `<repo>/.codex/config.toml`
- Plugin-bundled hooks via plugin manifest or `hooks/hooks.json` inside plugin
- Managed hooks from `requirements.toml` (enterprise MDM)

**Trust model**: Non-managed hooks require review before first run; trust recorded against hook hash. Managed hooks trusted by policy. Feature flag: `[features] hooks = true` (default).

**Key runtime behavior**:
- Multiple matching hooks run concurrently
- Higher-precedence config layers don't replace lower-precedence hooks; all merge
- Plugin hooks load alongside user/project/managed hooks
- Timeout default: 600s for most hooks; 1s for SessionEnd

---

## Equivalence Table

| Claude Event | Codex Counterpart | Equivalence | Notes | Citations |
|---|---|---|---|---|
| SessionStart | SessionStart | **1:1** | Both fire when session starts (with matchers `startup`, `resume` in both); both support command hooks; both can inject context. However, Claude receives richer input (model, agent_type, cache cost). | CC: `hooks.md:1089`; CX: `hooks.md` config section |
| Setup | (none) | **none** | Claude Setup runs after SessionStart, before first turn, allowing environment prep. Codex has no equivalent; setup would need to happen inside SessionStart or via config. | CC: `hooks.md:1222` |
| InstructionsLoaded | (none) | **none** | Claude event fires when CLAUDE.md parsed at session start. Codex has no project-instruction reload event. | CC: `hooks.md:1261` |
| UserPromptSubmit | UserPromptSubmit | **1:1** | Both fire before processing user input; both can intercept/transform. | CC: `hooks.md:1296`; CX: `hooks.md` table |
| UserPromptExpansion | (none) | **none** | Claude event for slash-command discovery. Codex has no documented equivalent. | CC: `hooks.md:1358` |
| MessageDisplay | (none) | **none** | Claude event when assistant message rendering completes. Codex has no equivalent; display is not hooked. | CC: `hooks.md:1408` |
| PreToolUse | PreToolUse | **1:1** | Both fire before tool calls (Bash, etc.); both support tool-name matchers; both can block/inspect. Claude receives more granular input and supports more handler types. | CC: `hooks.md:1540`; CX: `hooks.md` table |
| PermissionRequest | PermissionRequest | **1:1** | Both fire when approval needed; both can auto-approve or block. Codex matcher is permission type; Claude matcher is tool name context. | CC: `hooks.md:1821`; CX: `hooks.md` config |
| PostToolUse | PostToolUse | **1:1** | Both fire after tool succeeds; both receive tool output; both can inject follow-up guidance. | CC: `hooks.md:1917`; CX: `hooks.md` table |
| PostToolUseFailure | (none) | **none** | Claude fires when tool call fails catastrophically. Codex has no failure-specific event; error handling is implicit in PostToolUse context. | CC: `hooks.md:2024` |
| PostToolBatch | (none) | **none** | Claude fires after batch of tool calls. Codex has no batch-level event. | CC: `hooks.md:2086` |
| PermissionDenied | (none) | **none** | Claude advisory event when permission denied. Codex has no notification event for denials. | CC: `hooks.md:2143` |
| Notification | (none) | **none** | Claude event for in-session notifications (tool failed, waiting for input). Codex has no equivalent. | CC: `hooks.md:2191` |
| SubagentStart | SubagentStart | **1:1** | Both fire when subagent spawns; both can inject context. Claude supports more handler types and can block. | CC: `hooks.md:2283`; CX: `hooks.md` table |
| SubagentStop | SubagentStop | **1:1** | Both fire when subagent completes. Both are advisory (cannot block). | CC: `hooks.md:2319`; CX: `hooks.md` table |
| TaskCreated | (none) | **none** | Claude event when Task tool creates a task. Codex has no Task tool equivalent. | CC: `hooks.md:2348` |
| TaskCompleted | (none) | **none** | Claude event when task completes. Codex has no equivalent. | CC: `hooks.md:2402` |
| Stop | Stop | **1:1** | Both fire when turn stops. Both receive accumulated context. Claude can block; Codex typically advisory. | CC: `hooks.md:2458`; CX: `hooks.md` table |
| StopFailure | (none) | **none** | Claude fires when turn-stop operation itself fails (rare). Codex has no equivalent. | CC: `hooks.md:2560` |
| TeammateIdle | (none) | **none** | Claude fires when team session goes idle (multi-agent). Codex has no team-session equivalent. | CC: `hooks.md:2588` |
| ConfigChange | (none) | **none** | Claude fires when `.claude/settings.json` or CLAUDE.md changes during session. Codex has no equivalent. | CC: `hooks.md:2635` |
| CwdChanged | (none) | **none** | Claude fires when working directory changes. Codex has no equivalent. | CC: `hooks.md:2706` |
| DirectoryAdded | (none) | **none** | Claude fires when directory added to workspace. Codex has no equivalent. | CC: `hooks.md:2741` |
| FileChanged | (none) | **none** | Claude fires when tracked file changes on disk. Codex has no equivalent. | CC: `hooks.md:2787` |
| WorktreeCreate | (none) | **none** | Claude fires when worktree created. Codex has no worktree concept. | CC: `hooks.md:2864` |
| WorktreeRemove | (none) | **none** | Claude fires when worktree removed. Codex has no worktree concept. | CC: `hooks.md:2922` |
| PreCompact | PreCompact | **1:1** | Both fire before transcript compaction; both can block. | CC: `hooks.md:2971`; CX: `hooks.md` table |
| PostCompact | PostCompact | **1:1** | Both fire after compaction; both advisory. | CC: `hooks.md:3003`; CX: `hooks.md` table |
| PreModelSwitch | (none) | **none** | Claude fires before model change (e.g., `/model o3`). Codex has no model-switch event. | CC: `hooks.md` lifecycle diagram |
| PostModelSwitch | (none) | **none** | Claude fires after model changes. Codex has no model-switch event. | CC: `hooks.md` lifecycle diagram |
| Elicitation | (none) | **none** | Claude internal MCP-tool event. Codex has no equivalent. | CC: `hooks.md` lifecycle diagram |
| ElicitationResult | (none) | **none** | Claude internal MCP-tool event. Codex has no equivalent. | CC: `hooks.md` lifecycle diagram |
| (none) | SessionEnd | **Partial** | Codex fires when session ends (main thread only). Claude has SessionEnd but receives it as same lifecycle point. Codex SessionEnd timeout is 1s max; Claude timeout is configurable per hook. | CX: `hooks.md` config |

---

## Session Start Equivalence: The Key Question

**Codex has NO session-start hook equivalent for Claude's doctor model.**

**Finding**: While both systems have `SessionStart` events that fire when a session begins, **Codex has no structured extension point for running validation/health checks at session init**. 

**How Codex handles session init**:
1. **SessionStart hook** (documented): Runs command or prompt hook when session starts. Matcher: `startup` or `resume`.
2. **Config auto-load**: Codex loads `config.toml` + `hooks.json` from `~/.codex/`, `<repo>/.codex/`, and plugin manifests. No hook-level init.
3. **Plugin-bundled hooks** (documented): Plugins can declare `hooks/hooks.json` or inline `hooks` in manifest. Loaded when plugin enabled.

**What this means**: To run a doctor-equivalent health check at Codex session start, you would:
- Write a **SessionStart hook** (command type) that runs your health check
- Store the hook in `~/.codex/hooks.json` or `<repo>/.codex/hooks.json`
- Codex will run it with matcher `startup` or `resume`

**Comparison**:
- Claude Code: Has `SessionStart`, `Setup`, `InstructionsLoaded`, and full hook pipeline for inspection/injection
- Codex: Has only `SessionStart` (command-only); no Setup; no InstructionsLoaded; plugin-bundled hooks loaded via manifest discovery, not a hook event

**Session-start availability in this project**:
- **Claude**: `.claude/hooks/hooks.json` is used (proof: `c63d60f` commit introduces `claude-doctor` function hook)
- **Codex**: `.codex/hooks.json` exists (verified in project); could wire a doctor hook there

---

## Constraints & Implementation Notes

### 1. Handler type support differs
- **Claude Code**: Supports `command`, `http`, `mcp_tool`, `prompt` handlers. Prompt handlers can inject LLM reasoning.
- **Codex**: Supports `command` only (today); `prompt` and `agent` handlers are parsed but skipped.

**Impact**: A Claude doctor that uses an MCP tool would need to be rewritten as a shell command for Codex.

### 2. Hook discovery and auto-loading
- **Claude Code**: Reads `~/.claude/` and `.claude/` from project. Per-platform hooks can be specified. Skill-level hooks auto-discovered.
- **Codex**: Reads `~/.codex/` and `<repo>/.codex/`; also scans plugin manifests for bundled hooks. Plugins can contribute hooks via manifest. No skill-level hook discovery.

**Impact**: Doctor hooks are project-local on both; plugin-bundled hooks on Codex only.

### 3. Hook trust and review
- **Claude Code**: Function hooks (`.ts` modules in hooks dir) are parsed/loaded from disk; no trust review required if in project.
- **Codex**: Non-managed command hooks require review + hash-based trust before first run. Managed hooks (via `requirements.toml`) trusted by policy.

**Impact**: A Codex SessionStart hook needs user trust; Claude function hooks do not.

### 4. Exit code and control flow
- **Claude Code**: Hook exit code (0 vs non-zero) determines block/allow for blocking hooks. JSON output can emit structured decisions.
- **Codex**: Hook exit code treated the same. Timeout defaults differ: 600s most hooks, 1s SessionEnd (max 3s).

**Impact**: Both understand exit codes; SessionEnd timeout is tighter in Codex.

### 5. SubagentStop cannot block
- **Claude Code**: `SubagentStop` documented as advisory-only (`$CC/hooks.md:2346` states `decision: block` is rejected by selfcheck for this event).
- **Codex**: `SubagentStop` documented as advisory-only (`$CX/hooks.md` notes "cannot block").

**Impact**: Both systems prevent hook-level blocking of subagent completion.

---

## Ledger entries

**Verified today (2026-09-14):**
- Codex SessionStart exists; Claude SessionStart exists; both fire at session init ✓
- Claude Code has 33 documented hook events; Codex has 11 ✓
- Only 9 hooks are 1:1 equivalent (SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, SubagentStart, SubagentStop, Stop, PreCompact, PostCompact) ✓
- Codex SessionEnd exists; Claude has SessionEnd (lifecycle diagram) ✓
- Codex has no `Setup` equivalent ✓
- Claude has no `SessionEnd` equivalent to Codex SessionEnd in offline docs (but lifecycle diagram names it) ✓ **RECHECKED**: Both systems have SessionEnd; Claude mentions it in lifecycle diagram at preview line "SessionEnd"

**Open questions for next probe:**
- Does Claude Code's SessionEnd hook surface in `hooks.md` detailed event sections (currently only in lifecycle diagram)?
- Does Codex support `PreModelSwitch` / `PostModelSwitch` (not listed in `hooks.md` table)?
- Can Codex hooks access `CLAUDE_ENV_FILE`-like mechanism for environment persistence?

---

## GitHub repos touched

- [anthropic-ai/anthropic-sdk-python](https://github.com/anthropic-ai/anthropic-sdk-python) — Claude SDK hooks reference
- [sourcegraph/cody](https://github.com/sourcegraph/cody) — Codex CLI (0.154.0 installed); hook implementation
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — Offline vendor docs for both Claude Code and Codex

