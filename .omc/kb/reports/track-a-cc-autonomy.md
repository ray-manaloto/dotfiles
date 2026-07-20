# Unattended-but-Escalating Claude Code Orchestrator — Research Report

**Date**: 2026-07-19  
**Scope**: Building autonomous, ticketed Claude Code loops that run well-specified tasks to completion, auto-merge on green, and escalate only genuine decisions to a human

---

## 1. Fork vs. Continue vs. Subtask: Exact Semantics

### `/fork` (Agent SDK: `fork_session=true`)

**Documentation**: https://code.claude.com/docs/en/agent-sdk/sessions.md

**Exact semantics**:
- Creates a **new session** that starts with a **copy** of the original's entire conversation history
- The fork gets a **distinct session ID**; the original session's ID and history remain **unchanged**
- Both sessions are **independent** after the fork point: changes made in the fork do not affect the original, and vice versa
- Both can be resumed and worked on separately using their respective session IDs

**SDK interfaces**:
- Python: `fork_session=True` in `ClaudeAgentOptions` passed to `query()`
- TypeScript: `forkSession: true` in `Options` passed to `query()`
- Example (Python):
  ```python
  async for message in query(
      prompt="Outline how OAuth2 would work",
      options=ClaudeAgentOptions(
          resume=session_id,
          fork_session=True,  # Creates a branch, not a mutation
          max_turns=5,
      ),
  ):
  ```
- The fork fires immediately; the original **remains idle** until resumed separately

**How to resume / list / drive**:
- Capture the fork's session ID from the `session_id` field on the `ResultMessage` 
- Pass to `resume=fork_id` on the next `query()` call
- List all sessions: `list_sessions()` (Python) / `listSessions()` (TypeScript)
- Retrieve past messages: `get_session_messages(session_id)` (Python) / `getSessionMessages(session_id)` (TypeScript)

---

### `continue` (Not a fork — reuses the most recent session)

**Documentation**: https://code.claude.com/docs/en/agent-sdk/sessions.md

**Exact semantics**:
- Finds and resumes the **most recent session** in the current project directory
- **No explicit session ID tracking required**
- Appends new messages to the same conversation history
- Best for multi-turn chat within a single process

**SDK interfaces**:
- Python: `continue_conversation=True` in `ClaudeAgentOptions`
- TypeScript: `continue: true` in `Options`

---

### `/subtask` (Does Not Exist)

`/subtask` **is not documented** in the Claude Code or Agent SDK documentation. The equivalent is **`subagent`** (a distinct concept: a nested agent spawned by Claude during a task) or the **Task tool** (for parallel work). There is no `/subtask` slash command.

If you're looking to spawn parallel child agents: use the **`Agent` tool** (built-in), or define custom **subagent definitions** in the Agent SDK. See https://code.claude.com/docs/en/sub-agents.md.

---

## 2. Unattended-but-Escalating Loop: Exact Pause/Resume Mechanism

### When No Human Is Present: Behavior Matrix

| Scenario | Current Behavior | Configurable? |
|----------|------------------|---------------|
| Permission prompt (`Bash`, `Write`, etc.) in auto mode | **Auto-approved** (via classifier) or **denied** | Yes: `permissions.ask` forces prompt; `permissions.deny` blocks |
| Permission prompt in `dontAsk` mode | **Denied** (never prompts) | Yes: `permissionMode` setting |
| Permission prompt in default mode, no human | **Blocks indefinitely** (waits for input) | Yes: use auto mode, or set `canUseTool` callback |
| `AskUserQuestion` tool (Claude asks for clarification) | **Blocks indefinitely** | Yes: implement `canUseTool` callback to answer; or channel via `PermissionRequest` hook |
| Tool call denied by hook | **Blocks indefinitely** | Yes: hook returns `defer` to exit and resume later |

### The `defer` Mechanism (From Hook Return)

**Documentation**: https://code.claude.com/docs/en/agent-sdk/hooks.md

A `PreToolUse` hook can return `"defer"` as the `permissionDecision`:
```python
return {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "defer",
        "permissionDecisionReason": "Awaiting human review of production deploy"
    }
}
```

**Behavior**:
- Ends the current `query()` call **immediately**
- The session is **persisted** to disk and remains **resumable**
- The tool call is **not executed**
- Resume with `--resume <session-id>` to continue; Claude reattempts the tool call or takes an alternative path

**Why this matters for autonomous loops**:
- An autonomous agent can hit a hook that says "I need human approval for this database write"
- The hook returns `"defer"`
- The agent loop exits cleanly (not crashed)
- The human is notified (via a Notification hook or Channel)
- The human reviews and later resumes the session
- Claude continues from exactly where it left off

---

### Escalation Without Blocking: Channels + Permission Relay

**Documentation**: https://code.claude.com/docs/en/channels-reference.md

**What they are**:
- MCP servers that push events INTO a Claude Code session (one-way or two-way)
- Two-way channels can **relay permission prompts** to external systems (Slack, mobile app, etc.)

**Permission relay flow** (no local terminal needed):
1. Claude tries to call a tool that needs approval (e.g., `Bash`)
2. Server generates a 5-letter request ID (e.g., `abcde`)
3. Sends `notifications/claude/channel/permission_request` to the channel server
4. Channel forwards the prompt to Slack/Discord/etc. with the ID
5. Human replies `yes abcde` or `no abcde`
6. Channel sends back `notifications/claude/channel/permission` with the verdict
7. Claude Code **applies the verdict** and continues (or blocked if `deny`)
8. Local terminal dialog also stays open — first answer wins

**Key**: Both the local and remote approval dialogs stay open. The agent is **unblocked** in seconds (remotely answered) rather than indefinitely (waiting for the Mac user to notice).

**Example Zod schema for permission relay**:
```typescript
const PermissionRequestSchema = z.object({
  method: z.literal('notifications/claude/channel/permission_request'),
  params: z.object({
    request_id: z.string(),     // five lowercase [a-km-z]
    tool_name: z.string(),      // e.g. "Bash", "Write"
    description: z.string(),    // untrusted, sanitized by CC v2.1.211+
    input_preview: z.string(),  // tool args, untrusted
  }),
})
```

Requires:
- Channel capability: `experimental['claude/channel/permission']: {}`
- https://code.claude.com/docs/en/channels-reference.md#relay-permission-prompts

---

## 3. Claude Code Autonomy Features: Changelog & Current Capabilities

### Complete Feature Map (v2.1.212+)

**Built-in**: Direct slash commands and modes

| Feature | Type | Entry Point | Use Case | Docs |
|---------|------|------------|----------|------|
| **Auto Mode** | Permission classifier | `permissionMode: "auto"` | Block destructive operations; allow routine internal work | https://code.claude.com/docs/en/permission-modes#eliminate-prompts-with-auto-mode |
| **`/goal`** | Continuous execution gate | `/goal <condition>` | Keep running until condition met (e.g., "all tests pass") | https://code.claude.com/docs/en/goal.md |
| **`/loop`** | Fixed or dynamic interval | `/loop <interval> <prompt>` or `/loop` | Re-run prompt every N minutes, or let Claude pick interval | https://code.claude.com/docs/en/scheduled-tasks.md |
| **Headless (`-p`)** | CLI non-interactive | `claude -p "prompt"` | One-shot unattended run; combines with `--allowedTools`, `--permission-mode auto` | https://code.claude.com/docs/en/headless.md |
| **Channels** | External event injection | MCP server + `--channels` | Receive webhooks, Slack messages, alerts; relay approvals back | https://code.claude.com/docs/en/channels-reference.md |
| **Hooks** | Execution intercepts | `hooks.PreToolUse`, `PostToolUse`, `Stop`, `Notification` | Enforce policy, gate operations, log/notify, defer escalations | https://code.claude.com/docs/en/agent-sdk/hooks.md |
| **Background sessions** | Agent view UI | `/agent start ...` in CLI | Run a session in the background; still consumes your terminal but stays live | https://code.claude.com/docs/en/agent-view.md |
| **Routines (Cloud)** | Managed infrastructure | `claude /schedule daily <prompt>` | Run on cloud infrastructure on a cron, GitHub event, or API call; no machine needed | https://code.claude.com/docs/en/routines.md |
| **Auto mode + environment** | Config-driven trust | `autoMode.environment` in settings | Tell classifier which repos, buckets, domains to trust for safe auto-approval | https://code.claude.com/docs/en/auto-mode-config.md |
| **Fork sessions** | Branching history | `fork_session=True` in SDK | Explore alternative approaches without losing the original thread | https://code.claude.com/docs/en/agent-sdk/sessions.md |

### Channels (Research Preview)

**Status**: Research preview (requires `--dangerously-load-development-channels` for custom channels)

**Supported out-of-the-box**: Telegram, Discord, iMessage, fakechat

**What they do**:
- **One-way**: forward alerts/webhooks into Claude (e.g., CI failure → Claude investigates)
- **Two-way**: Claude can reply via the channel's reply tool
- **Permission relay**: Forward approval prompts to external systems; remote user answers via text

**Key limitation**: Not eligible for Zero Data Retention (ZDR) because events persist in the session transcript.

**Certificate**: https://code.claude.com/docs/en/channels-reference.md

---

### Checkpointing & Rewind

**Status**: Documented, shipping

**What it does**: Automatically saves conversation snapshots; you can rewind and summarize.

**Docs**: https://code.claude.com/docs/en/checkpointing.md

**Limitation**: Snapshots are within the same session. To branch to a truly independent thread, use `/fork`.

---

### Headless Mode (`claude -p`)

**Status**: Fully available

**Exact behavior**:
- No interactive prompt; runs one prompt to completion
- Combines with `--allowedTools`, `--permission-mode`, `--output-format`
- If a permission prompt would appear in default mode, the command **fails** unless you pre-approve with `--allowedTools "Bash,Read,Write"`

**Example**:
```bash
claude -p "Find and fix the bug" \
  --allowedTools "Bash,Read,Edit" \
  --permission-mode auto \
  --output-format json
```

**Exit codes**: 0 = success, non-zero = error or blocked permission

**Key**: `--bare` skips loading hooks, skills, plugins, MCP servers from `.claude/` (useful for CI consistency)

**Docs**: https://code.claude.com/docs/en/headless.md

---

### Agent SDK Session Lifecycle (Python + TypeScript)

**Documentation**: 
- Python: https://code.claude.com/docs/en/agent-sdk/python.md
- TypeScript: https://code.claude.com/docs/en/agent-sdk/typescript.md

**Resume flow (Python)**:
```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

# Resume by explicit ID
async for message in query(
    prompt="Continue the work",
    options=ClaudeAgentOptions(resume="session_01ABC..."),
):
    if isinstance(message, ResultMessage):
        print(f"Final result: {message.result}")
```

**Continue (most recent)**:
```python
# First call creates session
# Second call auto-resumes the most recent
async for message in query(
    prompt="Next step",
    options=ClaudeAgentOptions(continue_conversation=True),
):
```

**Managed Agents API** (different from Agent SDK):
- Server-hosted sessions that persist independently
- Anthropic manages the sandbox
- No file-system access on the orchestrator's machine (fresh clone each run)
- Session events stream over SSE
- Can schedule recurring deployments

**Docs**: https://platform.claude.com/docs/en/managed-agents/overview.md

**Key difference**: Agent SDK = harness you host; Managed Agents = harness Anthropic hosts. Agent SDK has full local file access; Managed Agents gets a fresh clone.

---

## 4. Unattended-but-Escalating Loop: The Complete Mechanism

### Permission Evaluation Order (Pre-Classifier)

**Documentation**: https://code.claude.com/docs/en/agent-sdk/permissions.md

Hooks fire **first**, then rules (deny, ask, allow), then permission mode, then `canUseTool` callback.

```
1. Hooks (PreToolUse)
   ├─ Allow? → Execute
   ├─ Deny? → Block (even in bypassPermissions)
   └─ Defer? → Exit session, persist, wait for resume
   
2. Deny rules (permissions.disallow)
   └─ Match? → Block (always)
   
3. Ask rules (permissions.ask)
   └─ Match? → Fall through to canUseTool callback (even in bypassPermissions)
   
4. Permission mode
   ├─ bypassPermissions → Execute
   ├─ auto → Classifier decides (UNATTENDED if classifier approves)
   ├─ dontAsk → Deny (never prompt)
   ├─ acceptEdits → Auto-approve file operations
   └─ plan → Prompt for file writes (readonly tools auto-approve)
   
5. Allow rules (permissions.allow)
   └─ Match? → Execute
   
6. canUseTool callback
   └─ Invoke for decision (skipped in dontAsk)
```

### Auto Mode Classifier

**Documentation**: https://code.claude.com/docs/en/auto-mode-config.md

**How it works**:
- Reads your CLAUDE.md instructions and `autoMode.environment` config
- Evaluates each tool call against four rule lists: `hard_deny`, `soft_deny`, `allow`, `environment`
- Runs in-process (no network call)

**Activation**: `permissionMode: "auto"` in query options or settings

**Default behavior** (without customization):
- ✅ Allows: reads to your working repo, writes to `claude/`-prefixed branches, routine npm installs, git commits
- ❌ Blocks: force pushes, deploys to production-named targets, writes outside your repo, network calls to untrusted domains

**Configuration** (in `~/.claude/settings.json` or managed settings):
```json
{
  "autoMode": {
    "environment": [
      "$defaults",
      "Source control: github.example.com/acme-corp",
      "Trusted cloud buckets: s3://acme-builds",
      "Trusted internal domains: api.internal.example.com"
    ],
    "allow": [
      "$defaults",
      "Deploying to staging is allowed (ephemeral, resets nightly)"
    ],
    "soft_deny": [
      "$defaults",
      "Never run migrations outside the migrations CLI"
    ],
    "classifyAllShell": true  // Routes ALL bash through classifier
  }
}
```

**When denies happen without escalation**:
- Tool is blocked silently in a background loop
- A `PermissionDenied` hook fires (for logging / retry logic)
- Claude receives an error result and adapts

---

## 5. Settings + Hooks to Make Loops Safe and Observable

### Complete Settings Configuration

**File location**: `~/.claude/settings.json` (user-level, applies to all sessions)

**Minimal autonomous loop configuration**:
```json
{
  "permissionMode": "auto",
  "autoMode": {
    "environment": [
      "$defaults",
      "Source control: github.example.com/my-org",
      "Trusted cloud buckets: s3://my-builds"
    ],
    "classifyAllShell": true
  },
  "permissions": {
    "ask": [
      "Bash(git push main)",
      "Bash(gh pr merge *)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(rm -rf *|git reset --hard|git push --force)",
        "hooks": [
          "escalate_to_slack"
        ]
      }
    ],
    "Notification": [
      {
        "hooks": ["notify_on_permission_request"]
      }
    ]
  }
}
```

### Permissions Settings (Full Reference)

**Documentation**: https://code.claude.com/docs/en/permissions.md

| Setting | Type | Effect | Unattended Behavior |
|---------|------|--------|-------------------|
| `permissions.allow` | string[] | Pre-approve tool calls | Tool runs without prompt |
| `permissions.ask` | string[] | Force prompt (even in `auto` mode) | **Blocks** the tool (returns deny) unless `canUseTool` callback approves |
| `permissions.deny` | string[] | Unconditional block | Tool never runs, even in `bypassPermissions` |
| `permissionMode` | enum | Global approval strategy | `auto` = classifier; `dontAsk` = deny unmatched; `acceptEdits` = auto-approve file ops |

**Examples**:
```json
{
  "permissions": {
    "allow": ["Read", "Glob", "Grep"],
    "ask": ["Bash(git push *)", "Write(/etc/*)"],
    "deny": ["Bash(rm *)", "Edit(/sensitive-file)"]
  },
  "permissionMode": "auto"
}
```

---

## 6. Recurring/Scheduled + Resilience

### Session Persistence & Resume

**Documentation**: https://code.claude.com/docs/en/agent-sdk/sessions.md

| Scenario | Behavior | Recovery | Code |
|----------|----------|----------|------|
| Process crashes during query | Session partially written; on-disk state is latest completed turn | Resume with `--resume <id>`: Claude resumes from last message | `claude --resume <session-id>` |
| Network timeout mid-turn | Session may or may not have progressed; unclear state on-disk | Retry the query; if it succeeds, session has progressed; if it fails, retried prompt is lost (not idempotent) | Wrap in retry loop with exponential backoff |
| Loop iteration finishes | Session fully persisted | Restart with same loop; Claude re-reads full history | `/loop` auto-continues on next wakeup |
| Goal is met | Session marked as "goal achieved" | Resume to start new work | `--resume <id>` after `/goal` complete |
| Fork created | Both original and fork are persisted | Resume either session independently | `--resume <original-id>` or `--resume <fork-id>` |

---

### In-Session `/loop` vs. Cloud Routines vs. Desktop Tasks

**Documentation**:
- `/loop`: https://code.claude.com/docs/en/scheduled-tasks.md
- Routines: https://code.claude.com/docs/en/routines.md
- Desktop tasks: https://code.claude.com/docs/en/desktop-scheduled-tasks.md

| Feature | `/loop` | Cloud Routines | Desktop Tasks | GitHub Actions |
|---------|--------|---|---|---|
| **Where** | Local terminal | Anthropic-managed cloud | User's machine | GitHub runner |
| **Requires** | Open session | claude.ai account | Local machine | GitHub repo + secret |
| **Persistence** | Within session (7-day expiry) | Indefinite | Indefinite | Indefinite |
| **Local file access** | Yes (full) | No (fresh clone only) | Yes (full) | No (cloned repo only) |
| **Trigger** | Time interval or manual | Cron / API / GitHub event | Cron / manual | GitHub event / manual |
| **Multi-repo** | No | Yes (select per routine) | No | Yes (entire workflow) |
| **Approval prompts** | Inherited from session | None (autonomous) | Configurable per task | Via hook or skipped |
| **MCP servers** | From session config | From routine config | From session config | Via action |

---

### Cloud Routines (Unattended Infrastructure)

**Documentation**: https://code.claude.com/docs/en/routines.md

**Create**: 
```bash
/schedule daily at 9am, review and merge overnight PRs
```

**Trigger types**:
1. **Scheduled cron**: `0 9 * * *` = 9am daily
2. **API**: POST to `/fire` endpoint with bearer token; passes optional `text` payload
3. **GitHub event**: PR opened/closed, release created, etc., with filters

**Example API trigger** (from a CI pipeline):
```bash
curl -X POST https://api.anthropic.com/v1/claude_code/routines/trig_01ABC.../fire \
  -H "Authorization: Bearer sk-ant-oat01-xxxxx" \
  -H "anthropic-beta: experimental-cc-routine-2026-04-01" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Sentry alert SEN-4521 fired in prod. Stack trace: ..."
  }'
```

**Key limitations** (research preview):
- No local file-system access (fresh clone only)
- No Zero Data Retention (sessions persist server-side)
- Per-account daily run caps (exempt: one-off scheduled fires)

---

### Managed Agents (Claude Platform API)

**Documentation**: https://platform.claude.com/docs/en/managed-agents/overview.md

**What it is**: Server-hosted stateful sessions (NOT the Agent SDK; different product)

**How it differs from Agent SDK**:
| Aspect | Agent SDK | Managed Agents |
|--------|-----------|---|
| **Hosted by** | You (your code) | Anthropic |
| **Session model** | Ephemeral (within your process) | Persistent (server-side) |
| **File access** | Local filesystem | Fresh clone per run |
| **Data retention** | Zero Data Retention available | Ineligible (sessions persist) |

---

## 7. What Exists Natively vs. What You Must Build

### Exists Natively ✅

✅ **Session persistence & resume**: Automatic; SDK and CLI handle it
✅ **Permission gating**: Hooks, settings.json, permission modes
✅ **Async notification**: Async-mode hooks, Notification hooks
✅ **Escalation via defer**: Hook's `permissionDecision: "defer"`
✅ **Auto mode classifier**: Built-in; configure `autoMode.environment`
✅ **Recurring execution**: `/loop`, Routines, Desktop tasks
✅ **Channel integration**: MCP servers for two-way communication
✅ **Permission relay**: Channels' `claude/channel/permission` capability

### You Must Build ❌

❌ **Custom orchestrator loop**: If you want multi-session ticket orchestration
  - Solution: Use Routines (cloud) or `/loop` + session resume (local)
  
❌ **Ticket system integration**: Linking Claude sessions to your tracker
  - Solution: Use Bash/MCP in Claude to read from Linear/GitHub Issues, or hook→webhook to your API
  
❌ **Custom approval UI**: Beyond Slack/Discord/remote answer
  - Solution: Build a channel server (MCP) that receives permission relay and routes to your UI
  
❌ **Multi-agent orchestration**: Agent A spawns Agent B, tracks outcomes
  - Solution: Use Routines' API trigger to queue Agent B; use a Notification hook to watch Agent A

---

## GitHub repos touched

- [anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) — Agent SDK Python reference, types, `query()`, `ClaudeSDKClient`
- [anthropics/anthropic-sdk-js](https://github.com/anthropics/anthropic-sdk-js) — Agent SDK TypeScript reference, types, streaming
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — Channel implementations (Telegram, Discord, iMessage, fakechat)

