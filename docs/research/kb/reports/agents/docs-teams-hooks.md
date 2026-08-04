# Agent Teams & the Hook Surface That Governs Them — Claude Code reference

**Status:** COMPLETE — all nine sections written.

**The three answers the brief was commissioned for:**

1. 🔴 **`SubagentStart` CANNOT refuse to start an agent** (`hooks.md:2027`, `:724`). The branch gate
   must be a **`PreToolUse` hook matching `Agent`**, reading `.tool_input.subagent_type` — §2.
2. 🔴 **Agent teams do NOT isolate teammates in worktrees** (`agents.md:45`). Nine teammates share
   one checkout; partitioning is by prompt only — §7.
3. ✅ **`TeammateIdle` (exit 2) and `SubagentStop` (`decision: "block"`) CAN force more work** —
   bounded at **8 consecutive blocks** (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`), after which the harness
   overrides the hook and ends the turn anyway — §3.

**Date:** 2026-08-04
**Repo:** `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch `research/agent-team-design`
**Companion:** `docs/research/kb/reports/agents/harness-settings-reference.md` (frontmatter
fields, env vars, settings keys, project audit). This report does **not** re-derive those; it
builds on them.

## Citation convention

`$CC = ~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.
A bare `page.md:N` means `$CC/page.md:N`. Live URLs are written in full. Any claim without a
`file:line` or URL is labelled **UNVERIFIED**.

---

## 1. The full hook event list — **30 events**, enumerated four independent ways

### 1.1 The enumeration, and why you can trust the count

The brief warned that a prior session missed 18 of 29 events by grepping for the names it
expected. The fix is to match the **shape** of an event name and then cross-check by a second
route. Four routes were run; **all four return exactly the same 30 names.**

| # | Route | Command shape | Result |
|---|---|---|---|
| A | Section headers inside the `## Hook events` block (`hooks.md:935`–`2814`) | `sed -n '935,2814p' hooks.md \| grep '^### '` | **30** |
| B | JSON payload field, across the **whole 175-page doc tree** | `grep -rhoE '"hook_event_name":\s*"[A-Za-z]+"' .` | **30** |
| C | The exit-code-2 behaviour table (`hooks.md:706`–`737`) | table rows | **30** |
| D | The matcher table (`hooks.md:228`–`244`) | table rows, expanding grouped cells | **30** |

Routes A and B were set-differenced in both directions: `comm -23` → empty, `comm -13` → empty.

**Control arm for route B.** The same grep shape, asked for a term invented fresh for this run
(`Quixotrap`), returns **0**. So the probe is not a match-anything sieve: it returns 30 real names
and 0 for a name that does not exist. (Per `probes-need-a-control-arm.md` rule 3, the control term
is invented here rather than reused from a prior receipt — a published control string is in the
corpus and stops discriminating.)

### 1.2 The table

Columns: **Blocks?** = can the hook prevent the thing from happening; **Modifies?** = can it
rewrite content rather than only allow/deny; **Matcher** = what the `matcher` field filters on;
**In subagents?** = does a `settings.json`-declared hook of this event fire inside a subagent or
teammate. Timeouts are the `command`/`http`/`mcp_tool` defaults unless noted
(`hooks.md:343`).

Lifecycle order, as the doc orders them (`hooks.md:937`).

| # | Event | When it fires | Payload beyond [common fields](#common-input-fields) | Blocks? | Modifies? | Matcher |
|---|---|---|---|---|---|---|
| 1 | `SessionStart` | New session **or resume** (`hooks.md:941`) | `source`; optional `model` — the **only** event that can get `model`, and not guaranteed (`hooks.md:645`) | **No** — stderr to user only (`hooks.md:725`) | Context only, **plus** `initialUserMessage`, `watchPaths`, `sessionTitle`, `reloadSkills` (`hooks.md:874`) | `startup`\|`resume`\|`clear`\|`compact`\|`fork` (`:229`) |
| 2 | `Setup` | **Only** `--init-only`, or `--init`/`--maintenance` with `-p`. Never on normal startup (`hooks.md:1061`) | — | **No** (`hooks.md:726`) | Context only | `init`\|`maintenance` (`:230`) |
| 3 | `InstructionsLoaded` | A `CLAUDE.md` or `.claude/rules/*.md` is loaded — at session start for eager files, **and again later** for lazy loads (`hooks.md:1117`) | `load_reason` | **No** — exit code **ignored** (`hooks.md:736`) | No | `session_start`\|`nested_traversal`\|`path_glob_match`\|`include`\|`compact` (`:240`) |
| 4 | `UserPromptSubmit` | User submits a prompt, before Claude processes it (`hooks.md:1152`) | `prompt` | **Yes** — blocks **and erases the prompt** (`hooks.md:710`) | No — injects `additionalContext` only, cannot replace the prompt (`hooks.md:882`) | **none** (`:244`) |
| 5 | `UserPromptExpansion` | A user-typed command expands into a prompt. Covers the path `PreToolUse` misses: typing `/skillname` directly **bypasses `PreToolUse` on the `Skill` tool** (`hooks.md:1212`) | command name | **Yes** — blocks the expansion (`:711`) | `additionalContext` | command name (`:241`) |
| 6 | `MessageDisplay` | While assistant text **streams**; runs once per rendered batch of lines, so a long message fires it several times (`hooks.md:1260`) | the lines being rendered | **No** — original text is displayed (`:737`) | **Yes** — `displayContent` replaces on-screen text. **Display-only**: transcript and what Claude sees keep the original (`:873`) | **none** (`:244`) |
| 7 | `PreToolUse` | After Claude builds tool parameters, before the call (`hooks.md:1394`) | `tool_name`, `tool_input`, `tool_use_id` | **Yes** — blocks the call (`:708`) | **Yes** — `updatedInput` replaces the tool's arguments (`:879`) | tool name (`:228`) |
| 8 | `PermissionRequest` | Claude Code is about to ask **you** for permission. Also runs where no prompt can be shown (background subagents in headless) — **and if no hook decides, the call is DENIED** (`hooks.md:1625`) | permission request detail | **Yes** — denies (`:709`) | **Yes** — `decision.updatedInput` (`:880`) | tool name (`:228`) |
| 9 | `PostToolUse` | Immediately after a tool succeeds (`hooks.md:1715`) | `tool_name`, `tool_input`, `tool_response` | **No** — the tool already ran; stderr shown to Claude (`:719`) | **Yes** — `updatedToolOutput` replaces the result (`:881`) | tool name (`:228`) |
| 10 | `PostToolUseFailure` | A tool that started executing **failed**, or an MCP tool returned an error (`hooks.md:1785`) | as `PostToolUse` + error | **No** (`:720`) | No | tool name (`:228`) |
| 11 | `PostToolBatch` | **Once** after every tool call in a batch resolves, before the next model call. `PostToolUse` fires per-tool and therefore concurrently on parallel calls; this fires exactly once with the full batch (`hooks.md:1841`) | the batch | **Yes** — stops the agentic loop before the next model call (`:721`) | No | **none** (`:244`) |
| 12 | `PermissionDenied` | **Auto mode's classifier** denied a call. Does *not* fire for a manual deny, a `PreToolUse` block, or a `deny` rule (`hooks.md:1898`) | tool name + denial | **No** — the denial already happened (`:722`) | `retry: true` tells the model it may retry (`:869`) | tool name (`:228`) |
| 13 | `Notification` | Claude Code sends a notification (`hooks.md:1944`) | `message` | **No** — stderr to user only (`:723`) | No | 8 values incl. `agent_needs_input`, `agent_completed` (`:232`) |
| 14 | `SubagentStart` | A subagent is spawned via the Agent tool (`hooks.md:2008`) | `agent_id`, `agent_type` | 🔴 **NO — see §2** (`hooks.md:2027`, `:724`) | Context only (`additionalContext` into the subagent) | agent type (`:233`) |
| 15 | `SubagentStop` | A subagent finished responding (`hooks.md:2042`) | `stop_hook_active`, `agent_id`, `agent_type`, `agent_transcript_path`, `last_assistant_message`, `background_tasks`, `session_crons` | **Yes** — prevents the subagent stopping (`:713`) | `additionalContext` | agent type (`:235`) |
| 16 | `TaskCreated` | A task is being created via `TaskCreate` (`hooks.md:2073`) | task fields, `team_name` (**deprecated**, `agent-teams.md:18`) | **Yes** — **rolls back the creation** (`:715`) | No | **none** (`:244`) |
| 17 | `TaskCompleted` | A task is marked complete — **either** by `TaskUpdate` **or** when a teammate finishes its turn with in-progress tasks (`hooks.md:2128`) | task fields, `team_name` (deprecated) | **Yes** — prevents completion (`:716`) | No | **none** (`:244`) |
| 18 | `Stop` | Main agent finished responding. **Does not run on a user interrupt**; API errors fire `StopFailure` instead (`hooks.md:2184`) | `stop_hook_active`, `last_assistant_message`, `background_tasks`, `session_crons` | **Yes** — see §3 (`:712`) | `additionalContext` | **none** (`:244`) |
| 19 | `StopFailure` | Instead of `Stop` when the turn ends on an API error (`hooks.md:2284`) | error type | **No** — "output and exit code are ignored" (`:718`) | No | 10 error types incl. `rate_limit`, `max_output_tokens` (`:239`) |
| 20 | `TeammateIdle` | 🟢 A **teammate** is about to go idle after finishing its turn (`hooks.md:2312`) | teammate id, `team_name` (deprecated) | **Yes** — teammate gets stderr and **continues working** (`:714`) | No | **none** (`:244`) |
| 21 | `ConfigChange` | A settings/policy/skill file changes mid-session (`hooks.md:2359`) | `source`, optional `file_path` | **Yes** — blocks the change, **except `policy_settings`** (`:717`) | No | `user_settings`\|`project_settings`\|`local_settings`\|`policy_settings`\|`skills` (`:236`) |
| 22 | `CwdChanged` | Working directory changes, e.g. Claude runs `cd` (`hooks.md:2428`) | old/new cwd; has `CLAUDE_ENV_FILE` (`:2431`) | **No** (`:728`) | Env persistence via `CLAUDE_ENV_FILE` | **none** (`:237`) |
| 23 | `FileChanged` | A watched file changes **on disk** (`hooks.md:2461`) | path | **No** (`:729`) | No | **literal filenames to watch** — the matcher *is* the watch list, and uses a narrower exact-match set (`:220`,`:238`) |
| 24 | `WorktreeCreate` | A worktree is being created — `--worktree`, subagent `isolation: "worktree"`, or a background session (`hooks.md:2502`) | worktree request | **Yes** — ⚠️ **any non-zero exit aborts creation**, unlike every other event (`:699`,`:734`) | **Replaces** the default `git worktree` behaviour entirely; returns the path. `.worktreeinclude` is then **not processed** (`:2504`) | **none** (`:244`) |
| 25 | `WorktreeRemove` | A worktree is being removed (`hooks.md:2558`) | worktree | **No** — failures logged in debug only (`:735`) | No | **none** (`:244`) |
| 26 | `PreCompact` | Before a compact operation (`hooks.md:2605`) | trigger, custom instructions | **Yes** — **blocks compaction** (`:730`) | No | `manual`\|`auto` (`:234`) |
| 27 | `PostCompact` | After compaction completes (`hooks.md:2635`) | summary | **No** (`:731`) | No | `manual`\|`auto` (`:234`) |
| 28 | `SessionEnd` | Session ends (`hooks.md:2663`) | exit reason | **No** (`:727`) | No | `clear`\|`resume`\|`logout`\|`prompt_input_exit`\|`bypass_permissions_disabled`\|`other` (`:231`) |
| 29 | `Elicitation` | An **MCP server** requests user input mid-task; a hook can answer programmatically and skip the dialog (`hooks.md:2701`) | elicitation request | **Yes** — denies (`:732`) | **Yes** — `action` + `content` form values (`:871`) | MCP server name (`:242`) |
| 30 | `ElicitationResult` | After a user answers an MCP elicitation (`hooks.md:2771`) | the response | **Yes** — blocks; action becomes decline (`:733`) | **Yes** — `content` overrides the user's answer (`:872`) | MCP server name (`:243`) |

### 1.3 Timeouts

Per-handler `timeout` in seconds (`hooks.md:343`):

| Handler type | Default | Event overrides |
|---|---|---|
| `command`, `http`, `mcp_tool` | **600 s** | `UserPromptSubmit` → **30 s**; `MessageDisplay` → **10 s**; `SessionEnd` → a shared **1.5 s budget** for all its hooks |
| `prompt` | **30 s** | — |
| `agent` | **60 s** | — |

The `SessionEnd` budget is raised to match the longest per-hook `timeout` in settings files,
**capped at 60 s** — and per the companion report's Table B,
`CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` (default 1500) is the same knob, with the caveat that
**plugin hook timeouts do not raise it**.

### 1.4 Do these fire inside subagents and teammates?

**Yes, broadly, and this is the mechanism by which an existing `settings.json` guard already binds
delegated agents.** `sub-agents.md:613`: *"Hooks from settings files, managed policy settings, and
plugins all apply inside subagents, so a `PreToolUse` hook in `settings.json` also runs before
every tool a subagent uses."* Tool events fire for the subagent's calls the same way as in the main
conversation (`sub-agents.md:611`).

Three qualifications that change design:

1. **A hook can tell it is inside a subagent.** `agent_id` is present *only* when the hook fires
   inside a subagent call, and `agent_type` carries the agent name — the frontmatter `name`, or
   the plugin-scoped `plugin:agent` identifier (`hooks.md:642-643`). That is the discriminator for
   "apply this rule only to delegated agents".
2. **Frontmatter `Stop` becomes `SubagentStop`.** Automatic, at runtime (`hooks.md:570`,
   `sub-agents.md:663`).
3. **Project-scope frontmatter hooks need workspace trust as of v2.1.218.** Until the folder is
   trusted the subagent *still runs* and its hooks are **silently skipped** with only a debug-log
   error (`hooks.md:591`, `sub-agents.md:627`). `~/.claude/agents/` and `--agents` definitions are
   exempt. ⚠️ A folder added with `--add-dir` from outside the trusted repo **must be trusted
   separately** — its `.claude/agents/` hooks do not inherit the workspace grant
   (`sub-agents.md:627`). This repo adds two sibling repos with `--add-dir`.

**Which events are teammate-specific:** `TeammateIdle` fires only for agent-team teammates
(`hooks.md:2312`); `TaskCreated`/`TaskCompleted` fire on the shared task list teams coordinate
through, and `TaskCompleted` additionally fires when a **teammate finishes its turn with
in-progress tasks** (`hooks.md:2128`). `agent-teams.md:194-198` names exactly these three as the
team quality-gate mechanism.

### 1.5 Five things in this table that are easy to get wrong

- **Exit 1 does not block.** Only exit 2 does, for every event except `WorktreeCreate`, where
  *any* non-zero exit aborts (`hooks.md:699`). A policy hook that returns the conventional Unix
  failure code proceeds anyway.
- **Exit 2 discards your JSON.** JSON output is processed **only on exit 0** (`hooks.md:760`).
  Choose one channel. Since v2.1.214 a hook that exits 2 *and* prints schema-invalid JSON still
  blocks, using stderr as the reason; before that the combination was a non-blocking error and the
  action **proceeded** (`hooks.md:678`).
- **`if` is best-effort and fails OPEN.** It is evaluated only on `PreToolUse`, `PostToolUse`,
  `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied` — *"On other events, a hook with
  `if` set never runs"* (`hooks.md:342`) — and it runs the hook regardless of pattern when the Bash
  command can't be parsed (`hooks.md:361`). The doc's own conclusion: *"use the permission system
  rather than a hook to enforce a hard allow or deny."*
- **Hook output is capped at 10,000 characters** including `additionalContext` and `systemMessage`;
  the overflow is written to a file and replaced with a path + preview (`hooks.md:765`,`:845`).
- **`OTEL_*` exporter variables are removed from every subprocess Claude Code spawns, including
  hooks** (`hooks.md:645`). A hook cannot re-export telemetry using the parent's OTEL config — see
  §8.

## 2. `SubagentStart` and `SubagentStop`

### 2.1 🔴 The headline: **`SubagentStart` CANNOT refuse to start an agent**

The brief asks this because the repo wants a gate that refuses to start a *writing* agent on the
default branch. The answer is **no, not with `SubagentStart`**, stated twice in the vendor docs:

> *"SubagentStart hooks **can't block subagent creation**, but they can inject context into the
> subagent."* — `hooks.md:2027`

> `SubagentStart` | Can block? **No** | *"Shows stderr to user only"* — the exit-code-2 table,
> `hooks.md:724`

Reinforced structurally: `SubagentStart` sits in the decision-control table's **"Context only"**
row alongside `SessionStart` and `Setup`, whose entry ends *"No blocking or decision control"*
(`hooks.md:874`). And unlike almost every other event, its section has **no
`#### SubagentStart decision control` subsection at all** — the header enumeration in §1.1 shows
`#### SubagentStart input` (`hooks.md:2012`) and then straight to `### SubagentStop` (`:2042`).

One extra detail worth knowing when debugging: as of v2.1.199 a `SubagentStart` exit-2 stderr does
render, but **in the subagent's own transcript, not the parent conversation**, as a
`<hook name> hook error` notice — *"Claude doesn't see it, and the session or subagent proceeds"*
(`hooks.md:739`). So a hook written as a gate looks like it did something while the agent runs on
regardless. That is the worst possible failure shape: a gate that can only pass, which
`probes-need-a-control-arm.md` exists to catch.

**`continue: false` is not an escape hatch either.** It is a universal field
(`hooks.md:775`) whose documented effect is *"Claude stops processing entirely after the hook
runs"* — it is not listed as available to `SubagentStart`, whose decision-control row is
"Context only", and the row's semantics are about the **parent** stopping, not about the child
never starting.

### 2.2 What DOES gate agent creation — `PreToolUse` on the `Agent` tool

`Agent` is an explicitly documented `PreToolUse` matcher value (`hooks.md:1394`), and the tool's
`tool_input` schema carries exactly what a branch gate needs (`hooks.md:1492-1500`):

| Field | Type | Description |
|---|---|---|
| `prompt` | string | The task for the agent to perform |
| `description` | string | Short description of the task |
| `subagent_type` | string | **Type of specialized agent to use** — this is the discriminator |
| `model` | string | Optional model alias overriding the default |

So the working design is a `PreToolUse` hook with `"matcher": "Agent"` that reads
`.tool_input.subagent_type`, checks the branch, and returns:

```json
{ "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Refusing to start a writing agent on the default branch — create a branch first." } }
```

`deny` **prevents the tool call**, and its `permissionDecisionReason` is **shown to Claude**
(`hooks.md:1550-1551`), so the lead learns why and can branch and retry. Where several hooks
disagree, precedence is **`deny` > `defer` > `ask` > `allow`** (`hooks.md:1555`), so this cannot be
overridden by a permissive hook. This is the same shape this repo's existing `hook_guard` already
uses for `Bash`/`Edit`/`Write`.

**Three caveats before building on it:**

1. **It fires only when Claude *calls the tool*.** An @-mention or any path that does not go
   through the `Agent` tool is not covered by this matcher. The general form of the warning is at
   `hooks.md:1397`: `@`-referenced files never fire `PreToolUse` at all because no tool call
   happens. Verify empirically that your delegation path uses the tool.
2. **A second, non-hook layer exists and is stronger.** `permissions.deny` accepts
   `Agent(<name>)` entries that block a specific subagent type outright, and denying the bare
   `Agent` tool blocks all delegation (companion report Table C, citing `sub-agents.md:590,87`).
   The docs' own advice for hard enforcement is *"use the permission system rather than a hook"*
   (`hooks.md:361`). The trade-off: permission rules are static, a hook can consult live state
   (the current branch). For a branch gate you need the hook.
3. **`SubagentStart` is still useful — as the *context* half.** It can inject
   `additionalContext` into the subagent **before its first prompt** (`hooks.md:840`), which is the
   right place to tell every delegated agent the branch it is on, its report path, and the
   incremental-persistence requirement — the thing `agent-report-persistence.md` rule 1b says must
   ride the agent definition rather than the brief.

### 2.3 `SubagentStart` reference

| Property | Value |
|---|---|
| Fires | When a subagent is spawned via the Agent tool (`hooks.md:2008`) |
| Matcher | **Agent type name.** Built-ins: `general-purpose`, `Explore`, `Plan`. Custom: the frontmatter `name`, **not the filename**. Plugins: the plugin-scoped `my-plugin:reviewer` (`hooks.md:2008-2010`) |
| Payload | common fields + `agent_id` (unique subagent id) + `agent_type` (`hooks.md:2014`) |
| Blocks | **No** |
| Output | `additionalContext` only — inserted at the start of the subagent's conversation, before its first prompt (`hooks.md:2034`, `:840`) |
| Timeout | 600 s (command/http/mcp_tool default) |

⚠️ **Matcher trap for plugin agents.** A colon puts the matcher on the **regular-expression** path
(§1's matcher rules, `hooks.md:212`), and JS `RegExp.test` matches **anywhere** in the value. So
`my-plugin:reviewer` also fires for `my-plugin:reviewer-senior`. Anchor it: `^my-plugin:reviewer$`
(`hooks.md:2010`). The same trap applies to hyphenated names on Claude Code **before v2.1.195**,
where `code-reviewer` was regex-evaluated and also fired for `senior-code-reviewer`
(`hooks.md:218`).

### 2.4 `SubagentStop` reference — and yes, it can force more work

| Property | Value |
|---|---|
| Fires | When a subagent has finished responding (`hooks.md:2042`) |
| Matcher | Agent type, same values as `SubagentStart` (`hooks.md:2044`) |
| Blocks | **Yes** — exit 2 *"prevents the subagent from stopping"* (`hooks.md:712`) |
| Decision format | **Same as `Stop`** (`hooks.md:2069`) — see §3 |

Payload, all beyond the common fields (`hooks.md:2048-2052`):

| Field | Notes |
|---|---|
| `stop_hook_active` | The re-entrancy flag — see §3.2 |
| `agent_id` | The subagent's id |
| `agent_type` | The value the matcher filters on |
| `agent_transcript_path` | ⚠️ **The subagent's OWN transcript**, in a nested `subagents/` folder. `transcript_path` (the common field) is the **main session's** — two different files, easy to confuse |
| `last_assistant_message` | The text of the subagent's final response, *"so hooks can access it without parsing the transcript file"* |
| `background_tasks`, `session_crons` | Arrays described under `Stop` input; **scoped to the parent session, not the subagent**. Requires v2.1.145+ |

**Can a `SubagentStop` hook force an agent to do more work? Yes, explicitly:**

> *"Returning `decision: "block"` with a `reason` **keeps the subagent running and delivers
> `reason` to the subagent as its next instruction**."* — `hooks.md:2069`

That is the mechanism for the failure this repo has hit twice: an agent that finished and went idle
without persisting its report (memory `feedback_agent_team_delivery_discipline`). A `SubagentStop`
hook can `stat` the expected report path and, if it is missing, block with
`"Write your report to <path> before finishing."` — turning a soft brief instruction into a
machine gate. Bounded by the block cap in §3.3.

**Two practical notes.** To inject context into the **parent** after a subagent returns, the doc
says use a `PostToolUse` hook on the `Agent` tool instead (`hooks.md:2069`) — `SubagentStop`'s
output goes to the subagent. And `last_assistant_message` exists because the transcript file is
written **asynchronously and may lag the in-memory conversation** (`hooks.md:632`), so a hook that
reads the transcript for the final turn can legitimately find it absent.

## 3. `Stop` hook blocking and the block cap

### 3.1 The block shape

`Stop` and `SubagentStop` share one decision format (`hooks.md:2256-2262`):

| Field | Description |
|---|---|
| `decision` | `"block"` prevents Claude from stopping. **Omit** to allow stopping — there is no `"allow"` value |
| `reason` | **Required** when `decision` is `"block"`. Tells Claude why to continue. For `SubagentStop` it is *delivered to the subagent as its next instruction* (`hooks.md:2069`) |
| `hookSpecificOutput.additionalContext` | Non-error feedback. Conversation continues **through the same loop protections**, but the transcript labels it `Stop hook feedback` rather than raising a hook-error notification (`hooks.md:2262`, `:2271`) |

```json
{ "decision": "block", "reason": "Must be provided when Claude is blocked from stopping" }
```

**Prefer `additionalContext` when the hook is working as designed.** The docs' own guidance: use it
for guidance like *"run the test suite before finishing"* — it is subject to the identical
`stop_hook_active` flag and 8-continuation cap, but does not present as an error
(`hooks.md:2271`). Reserve `decision: "block"` for genuine violations.

Note the asymmetry with `TeammateIdle`/`TaskCreated`/`TaskCompleted`, which use **exit code 2 or
`continue: false`** and do *not* take a top-level `decision` (`hooks.md:866`).

### 3.2 `stop_hook_active` — the re-entrancy flag you must check

`stop_hook_active` is `true` *"when Claude Code is already continuing as a result of a stop hook"*
(`hooks.md:2194`). The doc's instruction is explicit: *"Check this value or process the transcript
to avoid blocking on a condition that will never resolve."* A hook that blocks unconditionally
builds a loop the cap then has to break.

Two adjacent `Stop` payload fields exist to prevent a different wrong answer:

- **`last_assistant_message`** — use it, not `transcript_path`, for anything acting on the turn
  that just finished: *"the transcript file isn't guaranteed to include the final message at Stop
  time on all versions"* (`hooks.md:2196`).
- **`background_tasks` and `session_crons`** (v2.1.145+) — they let a hook *"distinguish 'session
  is done' from 'session is paused waiting for background work to wake it back up'"*
  (`hooks.md:2198`). Both are present when the task registry is reachable and **empty** when
  nothing is in flight. Each `background_tasks` entry carries a `type` label from the set `shell`,
  `subagent`, `monitor`, `workflow`, **`teammate`**, `cloud session`, `MCP task`, plus `agent_type`
  for subagent tasks (`hooks.md:2205,2209`). So a `Stop` hook **can see how many teammates are
  still working** — the natural guard against a lead stopping out from under its team.

### 3.3 `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`

Verbatim (`env-vars.md:336`):

> *"Maximum number of consecutive times a Stop or SubagentStop hook may block the turn from ending
> **before Claude Code overrides it and ends the turn anyway** (default: 8). Set to `0` to disable
> the cap. Raise this if your hook legitimately needs more iterations to resolve."*

Corroborated in the `Stop input` section: *"Claude Code overrides the hook and ends the turn after
8 consecutive blocks"* (`hooks.md:2194`).

**What happens when the cap is exceeded: the turn ends, the hook loses.** This is a silent
failure mode for anything treating a `Stop` hook as enforcement — after 8 blocks the gate stops
gating and nothing about the outcome distinguishes "the condition was satisfied" from "the harness
gave up". Any `Stop`-based gate should therefore log its own verdict rather than relying on the
turn ending as evidence of compliance.

Three details that matter:

- **The cap counts CONSECUTIVE blocks**, so a single non-blocking turn resets it.
- **`additionalContext` counts too.** It is explicitly subject to *"the same loop protections… namely
  the `stop_hook_active` input and the 8-consecutive-continuation cap"* (`hooks.md:2271`). Using the
  gentler channel does not buy more iterations.
- **`0` disables the cap entirely** — an unbounded loop, only safe with a hook that provably
  terminates.

### 3.4 Can `SubagentStop` force an agent to do more work?

**Yes.** `decision: "block"` with a `reason` *"keeps the subagent running and delivers `reason` to
the subagent as its next instruction"* (`hooks.md:2069`). Up to 8 consecutive times by default.

For an agent team, the sibling event is **`TeammateIdle`**, which is the *right* one to use for a
teammate — a teammate is a session, not an Agent-tool subagent. Exit 2 sends stderr as feedback and
the teammate **continues working instead of going idle**; `{"continue": false, "stopReason": …}`
stops it entirely (`hooks.md:2341-2342`). Payload is `teammate_name` plus the deprecated
`team_name` (`hooks.md:2320`). No matcher — it fires for every teammate, so the hook script must
branch on `teammate_name` itself.

The vendor's own worked example is exactly the "did you produce your artifact" gate:

```bash
#!/bin/bash
if [ ! -f "./dist/output.js" ]; then
  echo "Build artifact missing. Run the build before stopping." >&2
  exit 2
fi
exit 0
```
— `hooks.md:2346-2352`

Substituting this repo's report path for `dist/output.js` is a direct, documented fix for the
twice-observed failure in `feedback_agent_team_delivery_discipline` (an agent that finished and
idled without delivering). It is a **stronger** layer than the agent-definition prose that has
already failed twice, because it is machine-checked at the exact moment of idling.

### 3.5 `/goal` — the built-in Stop hook

*"The `/goal` command is a built-in shortcut for a session-scoped **prompt-based Stop hook**. Use
it when you want Claude to keep working until a condition holds without writing hook
configuration."* (`hooks.md:2189`). Same cap and `stop_hook_active` protections apply; it is a
prompt hook (§5), so it costs a model call per turn end.

### 3.6 `StopFailure` — the case `Stop` does not cover

`Stop` **does not run on a user interrupt at all**, and on an API error `StopFailure` runs
*instead* (`hooks.md:2184`). `StopFailure` has **no decision control** — *"output and exit code are
ignored"* (`hooks.md:2308`) — so an API failure can never be blocked, only logged. Its
`last_assistant_message` is **not** Claude's output but the API error string itself, e.g.
`"API Error: Rate limit reached"` (`hooks.md:2294`) — a shape difference that will silently corrupt
a hook reusing one parser across both events. Matchers cover 10 error types including
`rate_limit`, `overloaded`, `billing_error` and `max_output_tokens` (`hooks.md:2292`).

**Consequence for a team:** a teammate whose turn dies on a rate limit fires `StopFailure`, which
cannot block, so **no quality gate runs on that path**. `TeammateIdle` is the event to rely on for
teammates; `StopFailure` is the observability channel for why a teammate went quiet.

## 4. `PreCompact`, `PostCompact`, and surviving compaction

The brief cites arXiv 2607.22917v2 naming *compaction eroding working detail* as a top failure mode
of long-lived agent teams. Here is what the harness actually offers against it. (The paper is
inherited context from the brief and is **UNVERIFIED** here — not read, not cited below.)

### 4.1 What reloads automatically, and the one thing that does not

`context-window.md:620` states the mechanism outright:

> *"Compaction replaces the conversation with a structured summary. **System prompt, CLAUDE.md,
> memory, and MCP tools reload automatically. The skill listing is the one exception. Only skills
> you actually invoked are preserved.**"*

Corroborated at `context-window.md:947`: what remains is *"startup content, which lives outside the
message history and reloads after compaction, plus a structured summary of the entire
conversation. Skill descriptions don't reload."* And at `:57`, the skill listing is flagged
`noSurviveCompact: true` — *"Unlike the rest of the startup content, this listing is not
re-injected after `/compact`."*

**So the erosion is asymmetric, and that is the actionable part.** Eager instruction context —
`CLAUDE.md`, `AGENTS.md`, `.claude/rules/*.md`, memory — survives by reloading. **Conversation
detail** (probe output, file:line anchors, evidence tables, what an agent already tried) is
replaced by a summary and is gone. For this repo that inverts the usual intuition: the ~31k tokens
of eager rules the companion report measured are the part that *survives*; a teammate's actual
findings are the part that does not. This is precisely why
`agent-report-persistence.md` requires persisting **verbatim, at receipt** — the file on disk is
the only copy that compaction cannot summarize away.

Corroborating signal from the hook surface itself: `InstructionsLoaded`'s matcher accepts
`compact` as a `load_reason` (`hooks.md:240`) — i.e. instruction files *are* re-loaded after
compaction, and a hook can observe each one.

### 4.2 `PreCompact` — the only event that can stop compaction

| Property | Value |
|---|---|
| Fires | Before a compact operation (`hooks.md:2605`) |
| Matcher | `manual` (`/compact`) \| `auto` (context window full) (`hooks.md:2609-2612`) |
| Payload | `trigger`, `custom_instructions` — for `manual` this is what the user typed after `/compact`; for `auto` it is **empty** (`hooks.md:2620`) |
| Blocks | **Yes** — exit 2, or JSON `{"decision": "block"}` (`hooks.md:2614`) |
| Timeout | 600 s |

⚠️ **Blocking auto-compaction has two completely different outcomes** (`hooks.md:2616`):

- Compaction triggered **proactively**, before the context limit → Claude Code *"skips it and the
  conversation continues uncompacted."* Recoverable.
- Compaction triggered **to recover from a context-limit error the API already returned** → *"the
  underlying error surfaces and **the current request fails**."*

So a `PreCompact` blocker is safe only in the proactive window and destructive at the limit. There
is nothing in the payload that distinguishes the two cases — `trigger` is `auto` for both. A hook
that blocks `auto` unconditionally will eventually kill a turn.

For `manual`, the stderr message is shown to the **user** (`hooks.md:2614`).

### 4.3 `PostCompact` — observation only

Fires after compaction completes (`hooks.md:2635`). Payload is `trigger` and **`compact_summary`,
the generated conversation summary** (`hooks.md:2646`). *"PostCompact hooks have no decision
control. They can't affect the compaction result but can perform follow-up tasks"*
(`hooks.md:2659`).

`compact_summary` is the useful part: a `PostCompact` hook can **write the summary to disk**,
giving a durable record of what each compaction kept — and, by diffing against the persisted agent
reports, of what it dropped.

### 4.4 The re-injection channel: `SessionStart` with `source: "compact"`

This is the documented way to put working detail *back* after a compaction.

`SessionStart`'s `source` field takes `"compact"` — *"after compaction"* (`hooks.md:963`). Its
decision control offers `additionalContext`, *"added to Claude's context at the start of the
conversation, before the first prompt"* (`hooks.md:985`), and for this event **plain stdout also
reaches Claude** without building JSON (`hooks.md:674`, `:1003`).

So: `{"matcher": "compact"}` on `SessionStart`, printing the current branch, the open task list,
and the paths of the persisted agent reports, restores the pointers a summary erodes. Cheaply, and
every time.

⚠️ **Two limits on this channel.** `sessionTitle` is *"ignored on `"clear"` and `"compact"`"*
(`hooks.md:988`) — that field alone does not apply. And on **resume**, Claude Code *"replays the
saved text rather than re-running the hook for past turns, so values like timestamps or commit SHAs
become stale"* for mid-session events; `SessionStart` hooks specifically **do run again**
(`hooks.md:857`). Write the context as factual statements, not imperatives — *"Text framed as
out-of-band system commands can trigger Claude's prompt-injection defenses"* (`hooks.md:855`).

### 4.5 The compaction knobs

| Knob | Default | Effect |
|---|---|---|
| `autoCompactEnabled` (setting) | **`true`**, v2.1.119+ | Auto-compact when context approaches the limit; shown in `/config` as **Auto-compact** (`settings.md:234`) |
| `DISABLE_AUTO_COMPACT` (env) | unset | `1` disables auto-compaction; `/compact` stays available. **Overrides `autoCompactEnabled`** (`env-vars.md:368`) |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | model-dependent | Percentage (1–100) of the window at which auto-compaction fires. **Can only LOWER the threshold** — values above the default have no effect. 🟢 *"Applies to both main conversations **and subagents**"* (`env-vars.md:189`) |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | the model's context window | Treat the window as smaller than it is for compaction purposes. Capped at the real window. Setting it **decouples the compaction threshold from the status line's `used_percentage`**, which always uses the full window (`env-vars.md:201`) |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | model-dependent | Raising it *"reduces the effective context window available before auto-compaction triggers"* (`env-vars.md:277`) — an indirect lever people trip over |

⚠️ **`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` only bites when compaction is PROACTIVE**, which is
model-and-context dependent: it applies when `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is set, in cloud
sessions, and on Sonnet 4.6 / Opus 4.6 without extended context. *"In other cases, such as a local
session on Opus 4.8, auto-compaction triggers when the conversation reaches the model's context
limit"* (`env-vars.md:189`) — i.e. the destructive branch of §4.2. **This session's model is
`claude-opus-5[1m]`, which is named in neither list**, so which branch applies here is
**UNVERIFIED**; settle it by observing whether a `PreCompact` hook sees `auto` before or at the
limit.

### 4.6 What the harness does NOT offer

Stated as absences, each with the control arm that makes the absence meaningful. Command shape:
`grep -rn '<term>'` over the whole 175-page tree.

| Claimed absent | Hits | Control arm (same command shape) |
|---|---|---|
| A hook that **edits** the compaction summary before it is applied | `PostCompact` has "no decision control" (`hooks.md:2659`); no `updatedSummary`-shaped field appears in the JSON-output or decision tables | `updatedInput` → present (`hooks.md:879`), `updatedToolOutput` → present (`:881`). The probe finds rewrite fields where they exist |
| Per-teammate compaction control | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` says "main conversations and subagents"; **teammates are named nowhere in the compaction knobs** | `agent-teams.md` → 3 hook mentions found (`:196-198`), so the file is greppable and the silence is real |
| Compaction survival for the **skill listing** | Explicitly `noSurviveCompact: true` (`context-window.md:57`) — a documented non-survival, not an absence | — |

**Practical conclusion for a long-lived team:** the harness gives you (a) a block, which is unsafe
at the limit, (b) an observation point that hands you the summary, and (c) a re-injection channel
at `SessionStart{compact}`. It gives you **no** way to preserve specific conversation detail
through a compaction. The only durable mechanism is writing to disk *before* it happens — which is
what `agent-report-persistence.md` rule 1b and `notepad-enforcement.md` already require, for
reasons that predate this doc and are independently confirmed by it.

## 5. The `"type": "agent"` hook — an LLM with deny authority, and yes it is documented

The brief reports a third-party framework wiring Haiku into `PreToolUse` with authority to deny.
**That is a documented, first-class hook type.** It is not a hack, and it is not undocumented — but
it is labelled **experimental**.

### 5.1 It is one of five hook types

`hooks.md:323-329` enumerates them: `command`, `http`, `mcp_tool`, `prompt`, and `agent`.

> *"**Agent hooks** (`type: "agent"`): spawn a subagent that can use tools like Read, Grep, and
> Glob to verify conditions before returning a decision. **Agent hooks are experimental and may
> change.**"* — `hooks.md:329`

And a standing warning at the top of the section:

> *"Agent hooks are experimental. Behavior and configuration may change in future releases. **For
> production workflows, prefer command hooks.**"* — `hooks.md:2948`

### 5.2 Exact schema

Configuration fields (`hooks.md:2968-2973`), which are the prompt-hook fields with a longer
timeout:

| Field | Required | Description |
|---|---|---|
| `type` | **yes** | Must be `"agent"` |
| `prompt` | **yes** | Prompt describing what to verify. `$ARGUMENTS` is the placeholder for the hook input JSON; **if `$ARGUMENTS` is absent the input JSON is appended** to the prompt (`hooks.md:2888`) |
| `model` | no | *"Defaults to a fast model"* — the docs say Haiku by default for prompt hooks (`hooks.md:2858`); the `agent` row says only "a fast model" (`:2972`) |
| `timeout` | no | **Default 60 s** (`:2973`). Compare: `prompt` 30 s, `command`/`http`/`mcp_tool` 600 s (`:343`) |

Plus the common fields (`hooks.md:341-345`): `if`, `statusMessage`, `once`.
⚠️ **`continueOnBlock` is listed on the prompt-hook table (`hooks.md:2891`) and NOT on the agent
table** — whether an agent hook honours it is **UNVERIFIED**. The text says agent config fields are
*"the same as prompt hooks, with a longer default timeout"* (`:2966`), which implies yes, but the
table omits it. Settle before relying on it.

Response schema — identical to prompt hooks (`hooks.md:2975`, `:2897-2907`):

```json
{ "ok": true }
{ "ok": false, "reason": "Explanation — required when ok is false" }
```

Execution model (`hooks.md:2955-2960`):

1. Claude Code spawns a subagent with your prompt and the hook's JSON input.
2. The subagent uses tools like Read, Grep, Glob to investigate.
3. **After up to 50 turns**, it returns `{ "ok": true/false }`.
4. Claude Code processes the decision exactly as a prompt hook's.

The vendor's own example is a `Stop` hook that runs the test suite with `"timeout": 120`
(`hooks.md:2979-2995`).

### 5.3 Which events support it — 13 yes, 15 no, 2 partial

`prompt` and `agent` support the **same** event set (`hooks.md:2951`).

**Supports all five types (`hooks.md:2821-2833`) — 13 events:**
`PermissionDenied`, `PermissionRequest`, `PostToolBatch`, `PostToolUse`, `PostToolUseFailure`,
**`PreToolUse`**, `Stop`, `SubagentStop`, `TaskCompleted`, `TaskCreated`, **`TeammateIdle`**,
`UserPromptExpansion`, `UserPromptSubmit`.

**`command`/`http`/`mcp_tool` only, no `prompt` or `agent` (`hooks.md:2837-2850`) — 14 events:**
`ConfigChange`, `CwdChanged`, `Elicitation`, `ElicitationResult`, `FileChanged`,
`InstructionsLoaded`, `Notification`, `PostCompact`, `PreCompact`, `SessionEnd`, `StopFailure`,
**`SubagentStart`**, `WorktreeCreate`, `WorktreeRemove`.

**`command` and `mcp_tool` only — no `http`, no `prompt`, no `agent` (`hooks.md:2852`):**
`SessionStart`, `Setup`.

13 + 14 + 2 = **29**. `MessageDisplay` appears in none of the three lists — its support set is
**UNVERIFIED**; §1's list of 30 is unaffected since that count came from four other routes.

🔴 **Note `SubagentStart` is in the no-agent-hook list.** So even the LLM-hook route cannot gate
agent creation — it is not merely that `SubagentStart` can't block; it can't run a `prompt`/`agent`
hook at all. §2.2's `PreToolUse`-on-`Agent` design is the only route, and `PreToolUse` **does**
support agent hooks if you want the verification to be model-driven.

### 5.4 Cost and blocking semantics — the part that decides whether to use one

**Every fire is a model call.** A prompt hook is one LLM call; an agent hook is **a subagent that
can take up to 50 turns**. On `PreToolUse` that is per tool call. This repo already measures its
*command* guard at ~340 ms/edit (inherited from memory `project_session_2026-08-03-f`, not
re-derived here); an agent hook on the same event is orders of magnitude more expensive in both
latency and tokens, and it is paid independently inside every teammate.

**`ok: false` does something different on every event** (`hooks.md:2911-2919`). The rows that
matter for a team:

| Event | Effect of `ok: false` |
|---|---|
| `Stop`, `SubagentStop` | Reason is fed back as the next instruction; **the turn continues** |
| `PreToolUse` | Tool call denied. **By default the TURN ENDS** and the reason appears as a chat warning. `continueOnBlock: true` returns it as a tool error so Claude can adjust — equivalent to a command hook's `permissionDecision: "deny"`. ⚠️ Before v2.1.210 the *default* was the continue-behaviour; the default **reversed** |
| `TeammateIdle` | **By default the teammate STOPS** and the reason is a warning line. `continueOnBlock: true` keeps it working |
| `TaskCompleted` | Marked-complete-during-a-turn → tool error, turn continues, `continueOnBlock` **ignored**. Teammate-stops → behaves like `TeammateIdle`, halts by default. **Same event, two behaviours** |
| `PostToolUseFailure`, `TaskCreated` | Tool error, turn continues, **regardless of `continueOnBlock`** |
| `PermissionRequest` | 🔴 **`ok: false` has NO EFFECT.** To deny, you must use a command hook returning `hookSpecificOutput.decision.behavior: "deny"` |
| `PermissionDenied` | 🔴 **No effect.** The only field this event reads is `hookSpecificOutput.retry`, which *"prompt and agent hooks can't set. They run on this event, but **their output is discarded**"* |

Those last two are the trap: a `prompt`/`agent` hook configured on `PermissionRequest` or
`PermissionDenied` is **accepted, runs, bills you, and does nothing.** A gate that can only pass —
exactly the class `probes-need-a-control-arm.md` exists for, here shipped by the harness itself.

The docs' own closing advice: *"If you need finer control on any event, use a command hook with the
per-event fields described in Decision control"* (`hooks.md:2921`).

### 5.5 Verdict for this repo

Against `use-tool-builtins.md` and `zero-bash-logic.md`, an agent hook is attractive — no script,
no allowlist entry, no bash budget. Against `mise-tasks-only.md`'s enforcement doctrine it is
weak: it is **experimental**, the vendor says prefer command hooks for production, its `ok: false`
semantics differ per event and have already reversed once, and it introduces a nondeterministic
judgment where the existing `hook_guard` is deterministic. For a branch gate — a question with a
mechanical answer (`git rev-parse --abbrev-ref HEAD`) — a command hook is strictly better. Reserve
agent hooks for verifications that genuinely need to read files, e.g. a `TeammateIdle` check that a
report is not just present but substantive.

## 6. Agent teams — everything not in the companion report

Page state: *"describes agent teams as of v2.1.178"* (`agent-teams.md:18`). Experimental, off by
default (`:10`).

### 6.1 Display modes and `teammateMode`

Two modes (`agent-teams.md:98-101`): **in-process** (all teammates in the main terminal, arrow keys
+ Enter to view, works anywhere) and **split panes** (one pane each, needs tmux or iTerm2).

| Value | Behaviour |
|---|---|
| `in-process` | **The default** (`agent-teams.md:107`) |
| `auto` | Split panes **only if already inside a tmux session**, or iTerm2 with `it2` on PATH; falls back to in-process otherwise |
| `tmux` | Enables split panes and **auto-detects** tmux vs iTerm2 from your terminal |
| `iterm2` | v2.1.186+. iTerm2 native panes explicitly. Errors with an install command if `it2` is missing (`agent-teams.md:109`) |

⚠️ *"Before v2.1.179 the default was `auto`, so upgraded sessions that previously opened split
panes now stay in one terminal unless you set the mode explicitly"* (`:107`). `--teammate-mode`
overrides per session and is **experimental and absent from `claude --help`** (`:125`). iTerm2 also
requires enabling the Python API in **Settings → General → Magic** (`:130`).

Panel controls (`agent-teams.md:82-88`): ↑/↓ select, **Enter** opens the teammate's transcript and
messages it, **Esc** interrupts its turn, **`x`** stops a selected teammate, **Ctrl+T** toggles the
task list (`:162`).

**Idle-row hiding is a live source of "my teammate vanished" confusion.** As of v2.1.199 an idle
row stays while *any* agent is working; once **everything** is idle, rows hide after **30 s** and
reappear on the teammate's next turn — *"the teammate stays running and addressable while hidden"*
(`:86`). In v2.1.181–2.1.198 a row hid 30 s after **its own** turn, even with others still working.
Beyond three idle teammates, surplus rows collapse into one `N idle agents` row (`:88`).

### 6.2 Models, effort, and fast mode

- **Teammates do NOT inherit the lead's `/model`** (`agent-teams.md:141`). `/config` →
  **Default teammate model**; pick **Default (leader's model)** to make them follow the lead.
- **Teammates DO inherit the lead's effort level** (`:143`) — in split-pane mode only from
  v2.1.186; earlier versions did not pass session effort to split-pane teammates.
- 🔴 **A teammate's model and fast mode are FIXED at spawn.** `/model` and `/fast` typed while
  viewing a teammate change **the lead** (`:167`). As of v2.1.199 you get a notice saying so;
  **earlier versions applied it to the lead with no indication at all.** `/effort` is the exception
  — it does apply to the viewed teammate's later turns.
- While viewing an in-process teammate, *"plain text and skills go to that teammate, but built-in
  commands still run in the lead's session"* (`:165`).

### 6.3 Plan approval for teammates

Request it in natural language (`agent-teams.md:147-152`). The teammate works in **read-only plan
mode** until approved. On finishing planning it sends a plan-approval request to the lead; the lead
approves, or rejects with feedback — on rejection *"the teammate stays in plan mode, revises based
on the feedback, and resubmits"* (`:154`).

🔴 **The lead approves autonomously, and this is the one designed bypass of you.**
*"The lead makes approval decisions autonomously"* (`:156`), and *"Plan approval is the designed
exception: the lead session grants teammate plan approvals **without a separate prompt to you**"*
(`:267`). Your only lever is criteria in the prompt — the docs' examples: *"only approve plans that
include test coverage"*, *"reject plans that modify the database schema."*

### 6.4 Task assignment, claiming, and dependency auto-unblocking

Three states: pending, in progress, completed (`agent-teams.md:171`). Two assignment paths: the
lead assigns explicitly, or a teammate **self-claims** the next unassigned, unblocked task after
finishing one (`:173-176`).

- **Claiming uses file locking** to prevent races when teammates claim simultaneously (`:178`).
  Note the scope precisely: the harness locks **task claims**, not files. Nothing prevents two
  teammates writing the same file — *"Two teammates editing the same file leads to overwrites"*
  (`:370`).
- **Dependencies auto-unblock**: *"when a teammate completes a task that other tasks depend on, it
  unblocks the dependent tasks without any action from you"* (`:228`). A pending task with
  unresolved dependencies **cannot be claimed** until they complete (`:171`).
- ⚠️ **The failure mode this creates** is in Limitations: *"teammates sometimes fail to mark tasks
  as completed, which blocks dependent tasks"* (`:422`). Auto-unblocking is only as good as
  completion reporting, and completion reporting is the known-unreliable part. `TaskCompleted` is
  the hook on that boundary.

### 6.5 Shutdown

Ask by name — *"Ask the researcher teammate to shut down"* (`agent-teams.md:185`). The lead sends a
shutdown request and **the teammate can approve or reject with an explanation** (`:188`). Cleanup
is automatic at session end (`:190`).

⚠️ *"Shutdown can be slow: teammates finish their current request or tool call before shutting
down"* (`:423`). And orphaned tmux sessions can survive — `tmux ls` then
`tmux kill-session -t <name>` (`:410-414`).

### 6.6 The mailbox file format and its validation

> *"Each agent's mailbox is a JSON file at
> `~/.claude/teams/{team-name}/inboxes/{agent-name}.json`. Claude Code **validates every entry**
> when it reads a mailbox file. Entries that don't match the message format are **reported as
> errors and removed from the file**; the valid messages are still delivered."* —
> `agent-teams.md:226`

⚠️ **Before v2.1.207 a single malformed entry caused a repeated error every second and blocked
delivery for that mailbox until you deleted the file manually.** Now it self-heals — but note the
healing is *destructive*: the malformed entry is deleted, so a message lost to a format error is
lost silently apart from the error report.

**Storage layout** (`agent-teams.md:230-235`) — team name is `session-` + the **first 8 characters
of the session ID**:

| Path | Lifetime |
|---|---|
| `~/.claude/teams/{team-name}/config.json` | **Removed when the session ends** |
| `~/.claude/teams/{team-name}/inboxes/{agent-name}.json` | with the team dir |
| `~/.claude/tasks/{team-name}/` | **Persists locally, never uploaded** — resumed sessions keep their tasks. Retention via `cleanupPeriodDays` |

- **Do not hand-edit or pre-author `config.json`** — it holds runtime state (session IDs, tmux pane
  IDs) and *"your changes are overwritten on the next state update"* (`:237`).
- Its `members` array carries each member's name and agent ID. **The lead's entry always has agent
  type `team-lead`**; a teammate's carries whatever type the lead named, and **omits the field when
  the lead named none** (`:241`). *"Teammates can read this file to discover other team members"* —
  the documented discovery mechanism.
- 🔴 **There is no project-level team config.** *"A file like `.claude/teams/teams.json` in your
  project directory is not recognized as configuration; Claude treats it as an ordinary file"*
  (`:243`). Team composition cannot be checked into the repo. Reusable **roles** can — via subagent
  definitions (`:239`).

### 6.7 Subagent definitions as teammate roles

*"Reference a subagent type from any subagent scope: project, user, plugin, or CLI-defined"*
(`agent-teams.md:247`). Mention it by name in the spawn prompt (`:252`).

What applies (`:255`): the definition's **`tools` allowlist** and **`model`**, and its **body is
APPENDED to the teammate's system prompt as additional instructions rather than replacing it** —
the opposite of a plain subagent, where the body *replaces* the CC system prompt.
**`SendMessage` and the task tools are always available even when `tools` restricts everything
else.**

What does not (`:258`): **`skills` and `mcpServers` are not applied.** Teammates load skills and
MCP servers from **project and user settings**, like a regular session.

### 6.8 Permissions — one correction to the companion report

`agent-teams.md:263` in full: *"Teammates start with the lead's permission settings. If the lead
runs with `--dangerously-skip-permissions`, all teammates do too. **After spawning, you can change
individual teammate modes**, but you can't set per-teammate modes at spawn time."*

The companion report's Table D reads this as `permissionMode` DOCUMENTED-IGNORED for teammates,
which is right about the **spawn-time** frontmatter field. The refinement: per-teammate modes are
changeable **after** spawn — the restriction is on the spawn path, not on the mode being per-agent.

The security model is explicit and worth knowing before designing escalation paths (`:265`):

- A `SendMessage` recipient is told the message came from **another Claude session, not from you**.
- *"A teammate cannot approve a permission prompt or supply consent on your behalf, and a teammate
  that was denied an action **cannot relay it to another teammate to bypass the check**."*
- In auto mode, *"the classifier treats an approval claim relayed from another agent as **untrusted
  input** rather than confirmation from you."*

Teammate permission prompts surface **in the lead session** (`:267`). Mitigation for prompt
fatigue: *"Pre-approve common operations in your permission settings before spawning teammates"*
(`:393`).

### 6.9 Context and communication

Each teammate has its own context window and loads *"the same project context as a regular session:
CLAUDE.md, MCP servers, and skills"* plus the spawn prompt. **The lead's conversation history does
not carry over** (`agent-teams.md:271`).

Sharing mechanisms (`:275-278`):

- **Automatic message delivery** — the lead does not poll.
- **Idle notifications** — a teammate that finishes notifies the lead automatically. As of v2.1.198
  a teammate whose turn ends on an **API error notifies the lead that it failed and includes the
  error text**, *"instead of appearing to finish normally"*. ⚠️ On earlier versions an API-killed
  teammate looked like a successful completion — the exact shape of the two silent losses in
  memory `feedback_agent_team_delivery_discipline`.
- **Shared task list** — all agents see status and claim work.
- **Teammate messaging is point-to-point**: *"To reach everyone, send one message per recipient"*
  — there is no broadcast.
- **Names are assigned by the lead at spawn.** For names you can reference later, *"tell the lead
  what to call each teammate in your spawn instruction"* (`:280`).
- v2.1.198+: a message from the lead or another teammate **wakes an in-process teammate waiting to
  retry a failed API request**, so it retries immediately (`:402`).

### 6.10 Sizing guidance (the vendor's, not this repo's)

- *"There's **no hard limit** on the number of teammates"* (`agent-teams.md:334`) — the constraints
  are token cost (**scales linearly**), coordination overhead, and diminishing returns.
- **Start with 3–5 teammates.** *"Three focused teammates often outperform five scattered ones"*
  (`:340,344`).
- **5–6 tasks per teammate.** *"If you have 15 independent tasks, 3 teammates is a good starting
  point"* (`:342`).
- Task sizing: too small → coordination exceeds benefit; too large → teammates work too long
  without check-ins; right → *"self-contained units that produce a clear deliverable"* (`:348-350`).
- *"Start with research and review"* — tasks that don't write code (`:366`).
- *"Letting a team run unattended for too long increases the risk of wasted effort"* (`:374`).

### 6.11 Every item under Limitations

Verbatim-faithful, `agent-teams.md:421-429`:

| # | Limitation | Consequence |
|---|---|---|
| 1 | **No session resumption with in-process teammates** | `/resume` and `/rewind` do not restore them. *"After resuming, the lead may attempt to message teammates that no longer exist"* — tell it to spawn new ones |
| 2 | **Task status can lag** | Teammates sometimes fail to mark tasks completed, **blocking dependent tasks**. Check and update manually |
| 3 | **Shutdown can be slow** | Teammates finish the current request or tool call first |
| 4 | **One team per session** | No additional named teams, no sharing a team across sessions |
| 5 | **No nested teams** | Teammates cannot spawn teammates. Only the lead manages the team |
| 6 | **No background subagents from in-process teammates** | Their subagents run in the **foreground**. Asking for background — via `run_in_background` **or** a definition with `background: true` — **returns an error**, *"because a teammate's background work can't outlive the lead's process"* |
| 7 | **Lead is fixed** | The main session is lead for its lifetime. No promotion, no transfer |
| 8 | **Permissions set at spawn** | All teammates start on the lead's mode; changeable after, not at spawn |
| 9 | **Split panes require tmux or iTerm2** | 🔴 **Not supported in VS Code's integrated terminal, Windows Terminal, or Ghostty** |

Limitation 6 is the sharpest for delegation design: subagents default to **background** as of
v2.1.198 in a normal session, so a definition that works from the lead **errors** from a teammate.
A team-role definition must not set `background: true`.

### 6.12 Every item under Troubleshooting

`agent-teams.md:378-415`:

| Symptom | Cause / fix |
|---|---|
| **Teammates not appearing** | Check the agent panel (↑/↓, Enter). **A disappeared row is hidden, not stopped** — message the teammate by name to bring it back. Or the task wasn't complex enough for Claude to form a team. For split panes: `which tmux`; for iTerm2 verify `it2` + Python API |
| **Claude used subagents instead of a team** | *"Subagents appear in the same agent panel as teammates, so **the panel alone doesn't confirm a team formed**."* Ask again and explicitly request an agent team (`:78`) |
| **Too many permission prompts** | Pre-approve common operations before spawning |
| **Teammates stopping on errors** | They may stop rather than recover. Inspect via the panel, then give instructions directly or spawn a replacement |
| **Lead shuts down before work is done** | *"The lead may decide the team is finished before all tasks are actually complete."* Tell it to keep going, or to wait for teammates before proceeding |
| **Lead does the work itself** | *"Sometimes the lead starts implementing tasks itself instead of waiting"* — prompt: *"Wait for your teammates to complete their tasks before proceeding"* (`:358-362`) |
| **Orphaned tmux sessions** | `tmux ls` → `tmux kill-session -t <name>` |

The "panel alone doesn't confirm a team formed" line is worth flagging as a **probe with no control
arm**: the panel is not a discriminating observation. The discriminating one is whether
`~/.claude/teams/{session-XXXXXXXX}/config.json` exists.

### 6.13 Subagents vs teams — the vendor's own comparison

`agent-teams.md:42-48`:

| | Subagents | Agent teams |
|---|---|---|
| **Context** | Own window; results return to caller | Own window; **fully independent** |
| **Communication** | Report to the main agent only | **Teammates message each other directly** |
| **Coordination** | Main agent manages all work | **Shared task list with self-coordination** |
| **Best for** | Focused tasks where only the result matters | Work requiring discussion and collaboration |
| **Token cost** | Lower — results summarized back | **Higher — each teammate is a separate Claude instance** |

*"For sequential tasks, same-file edits, or work with many dependencies, a single session or
subagents are more effective"* (`:30`).

## 7. Worktrees

### 7.1 🔴 The headline: **agent teams do NOT isolate teammates in worktrees**

Stated directly, on the page that compares the parallelisation surfaces:

> *"Do the tasks touch the same files? Isolate the work with worktrees. Subagents and sessions you
> run yourself can each use a separate worktree. **Agent teams don't isolate teammates in
> worktrees**, so partition the work so each teammate owns a different set of files."* —
> `agents.md:45`

Independently control-armed before that sentence was found, by grepping both pages:

| Probe | Hits | Control arm, same command shape |
|---|---|---|
| `worktree` in `agent-teams.md` | **1** — and it is the "Next steps" link describing worktrees as *"**Manual parallel sessions**… run multiple Claude Code sessions **yourself** without automated team coordination"* (`:440`) | `teammate` in the same file → **127**. The file is greppable |
| `teammate` in `worktrees.md` | **0** in any isolation context — 2 hits are cross-links to the teams page (`:15`, `:255`) | `subagent` in the same file → **12**, including a whole section *"Isolate subagents with worktrees"* (`:68`) |

So two routes and a direct statement agree. **The only file isolation available to a 9-role team is
the spawn prompt.** `agent-teams.md:370`: *"Two teammates editing the same file leads to
overwrites."* The harness locks **task claims** (`agent-teams.md:178`), not files.

### 7.2 `worktree.baseRef`

| Value | Behaviour |
|---|---|
| **`"fresh"`** — the default | Branch from *"the repository's default branch **on the remote**, usually `main`"* (`worktrees.md:107`) |
| `"head"` | Branch from your current local `HEAD`, carrying unpushed commits and feature-branch state. *"Use this when isolating subagents that need to operate on in-progress work."* **Inside a worktree, `"head"` resolves to that worktree's `HEAD`, not the main checkout's** (`:108`) |

- **It applies to all three creation paths**: `--worktree`, the `EnterWorktree` tool, and subagent
  `isolation: worktree` (`settings.md:370`). *"Subagent worktrees use the same base branch as
  `--worktree`, so they branch from your repository's default branch unless `worktree.baseRef` is
  set to `"head"`"* (`worktrees.md:87`).
- **You cannot set it to a branch name** — only `fresh` or `head`. For a specific branch, create the
  worktree with git directly (`worktrees.md:110`).
- **`"fresh"` does network I/O.** Claude Code keeps `origin/HEAD` current: if the repo hasn't been
  fetched in 24 hours it **fetches the default branch, capped at 5 seconds**, falling back to the
  cached ref on failure. With no remote, or an uncached and unfetchable `origin/HEAD`, *"the
  worktree falls back to your current local `HEAD`"* (`worktrees.md:112`). Before v2.1.208 it used
  whatever was cached. 🟢 Note the fallback direction: a network failure silently gives you `head`
  behaviour, so a worktree that "worked" offline may not reproduce online.

⚠️ **For this repo specifically**, `.claude/rules/do-not.md` #9 and memory
`feedback_branch_before_any_work` require all work on a branch, and the `branch_guard` PreToolUse
hook denies writes on the default branch. With the **default `"fresh"`**, any subagent given
`isolation: worktree` lands on a fresh branch off `origin/main` **without the working branch's
commits** — so it neither sees the branch's work nor is on the branch the PR will merge. The
companion report already flags `"head"` as the highest-value absent setting after
`teammateDefaultModel`; this is the mechanism behind that recommendation.

### 7.3 `worktree.symlinkDirectories`

> *"Directories to symlink from the main repository into each worktree **to avoid duplicating large
> directories on disk**. No directories are symlinked by default."* Example:
> `["node_modules", ".cache"]` — `settings.md:371`

**Control arm on its documentation footprint:** `symlinkDirectories` appears in exactly **2 files**
(`settings.md`, `large-codebases.md`); the same grep for `baseRef` returns **5 files**
(`settings.md`, `changelog.md`, `worktrees.md`, `whats-new.md`, `whats-new__2026-w19.md`). Both
non-zero, so the probe discriminates — `symlinkDirectories` is simply thinly documented, notably
**absent from `worktrees.md` itself**.

Sibling: **`worktree.sparsePaths`** checks out only the listed directories plus root-level files
via git sparse-checkout. ⚠️ *"While a sparse worktree exists, git enables `extensions.worktreeConfig`
in the repository's **shared `.git/config`**"* (`settings.md:372`) — a repo-wide side effect that
outlives the worktree.

### 7.4 `worktree.bgIsolation`

> v2.1.143+. Isolation mode for **background sessions**. **`"worktree"` (the default) blocks
> `Edit`/`Write` in the main checkout until `EnterWorktree` is called.** `"none"` lets background
> jobs edit the working copy directly. — `settings.md:373`

As of v2.1.203, **outside a git repository** a failing `WorktreeCreate` hook *releases* the block so
the session can edit in place (`settings.md:373`). `agent-view.md:453` gives the escape hatch for
repos where worktrees are impractical.

⚠️ **Scope check — this governs *background sessions*, not subagents and not teammates.** Both
`settings.md:373` and `agent-view.md:453` say "background sessions", linking to
`agent-view.md#how-file-edits-are-isolated`. Do not read it as a write-guard over delegated agents.

### 7.5 How worktree isolation interacts with teammates vs subagents

| | Subagents | Teammates | Background sessions (`claude agents`) |
|---|---|---|---|
| Per-agent worktree | **Yes** — `isolation: worktree` frontmatter, or ask Claude to "use worktrees for your agents" (`worktrees.md:70`) | 🔴 **No** — undocumented and explicitly denied (`agents.md:45`) | **Yes, automatically** — *"Agent view moves each dispatched session into its own worktree automatically"* (`agents.md:22`) |
| Base ref | `worktree.baseRef`, default `fresh` (`worktrees.md:87`) | n/a | `worktree.baseRef` |
| Write block outside the worktree | v2.1.203+: a command escaping to the main checkout **fails**; v2.1.210+ the check covers the whole repo and inspects `git -C`, `--git-dir`, `GIT_DIR`/`GIT_WORK_TREE`, and `cd` (companion report Table A, `sub-agents.md:267-271`) | none | `worktree.bgIsolation: "worktree"` (default) blocks Edit/Write in the main checkout until `EnterWorktree` |
| Cleanup | Auto-removed **if unchanged**; a worktree with changes survives until the periodic sweep can remove it without losing work (`worktrees.md:85`) | n/a | same sweep |

**Lifecycle details that bite in a fan-out:**

- **A running agent's worktree is `git worktree lock`ed** so concurrent cleanup cannot remove it;
  released when the agent finishes (`worktrees.md:93`). As of v2.1.210 the sweep also releases a
  lock left by a **session whose process exited**, so a killed background session no longer leaves
  a permanently locked worktree — *"The sweep never releases a lock you set yourself"* (`:95`).
- **The sweep is governed by `cleanupPeriodDays`** and **skips any worktree still holding work**
  (changed/untracked files, unpushed commits). It **never** removes `--worktree` worktrees
  (`worktrees.md:91`).
- **Non-interactive runs are never cleaned up.** *"Non-interactive runs with `-p` have no exit
  prompt, so Claude doesn't clean up their worktrees. Remove them with `git worktree remove`"*
  (`worktrees.md:52`).
- **`.worktreeinclude`** copies gitignored files (`.env`, `config/secrets.json`) into every
  git-created worktree, using `.gitignore` syntax; only files that match **and are gitignored** are
  copied (`worktrees.md:134-146`). ⚠️ **A `WorktreeCreate` hook replaces the default entirely, so
  `.worktreeinclude` is NOT processed** — copy inside the hook (`worktrees.md:146`, `:215`).
  🔴 Relevant to this repo: `mise.local.toml` and anything under `.agent/` are gitignored and would
  be absent from every subagent worktree unless listed there.
- **Shared with the main checkout** (`worktrees.md:168-174`): the `.git` directory (so `git commit`
  works from a worktree even under sandboxing); **project-scope plugins** (v2.1.200+, no reinstall
  per worktree); and **permission approvals** — v2.1.211+, "Yes, don't ask again" in a worktree
  saves to the *main checkout's* `.claude/settings.local.json` and survives the worktree's removal.
  Before v2.1.211 such an approval was saved inside the worktree and **lost with it**.
- **`EnterWorktree` outside `.claude/worktrees/` always prompts.** *"An `EnterWorktree` permission
  rule or choosing 'don't ask again' doesn't suppress this prompt; only `bypassPermissions` mode
  skips it"* (`worktrees.md:43`) — because the move takes the session's cwd, write access, **and
  project configuration such as `CLAUDE.md` and settings** to that location.
- **Two failure modes** (`worktrees.md:242-248`): Claude Code exits **code 1** when it can't enter
  the worktree at startup — typically a `WorktreeCreate` hook that **printed something other than
  the directory path**; and it **refuses** to create a worktree when `.claude`,
  `.claude/worktrees`, or the worktree directory is a **symlink**.
- Add `.claude/worktrees/` to `.gitignore` (`worktrees.md:32`). Interactive `--worktree` requires
  workspace trust first; `-p` skips the check (`:29`).

### 7.6 Practical read for a 9-role team

The isolation story and the coordination story do not compose. You can have **teammates** (shared
task list, direct messaging, self-claiming) **or** **worktree isolation** (subagents, background
sessions) — not both. If parallel *writes* to overlapping files are the risk, the harness's answer
is worktree-isolated **subagents**, which cannot message each other; if inter-agent discussion is
the point, it is **teammates**, which share one checkout and rely on partitioning by prompt.
`agent-teams.md:366` steers new users to research and review precisely because those *"don't
require writing code"* — which is the same constraint stated as advice.

## 8. Cost and monitoring

### 8.1 The documented multiplier — **~7×, and carry it with its CONDITION**

> *"Agent teams use **approximately 7x more tokens than standard sessions when teammates run in
> plan mode**, because each teammate maintains its own context window and runs as a separate Claude
> instance."* — `costs.md:246`

**The clause "when teammates run in plan mode" is load-bearing and is usually dropped when this
number is quoted.** Plan mode is read-only exploration; it is not the general case, and the docs do
not give a multiplier for teammates doing ordinary implementation work. Per
`verify-before-advancing.md`'s closing note, the honest form is *"~7× under the documented
condition (plan mode)"*, not *"agent teams cost 7×"*.

The unconditioned statements are weaker but general:

- *"Token usage scales with the number of active teammates and how long each one runs"*
  (`costs.md:134`).
- *"Token costs scale **linearly**: each teammate has its own context window and consumes tokens
  independently"* (`agent-teams.md:336`); *"token usage is roughly proportional to team size"*
  (`costs.md:139`).
- *"Each active teammate **keeps consuming tokens until it exits**"* (`costs.md:277`) — idle is not
  free, and combined with §6.1's idle-row hiding, a teammate can be invisible *and* billing.

**The five documented cost controls** (`costs.md:136-142`):

1. **Use Sonnet for teammates** — *"balances capability and cost for coordination tasks"*.
2. **Keep teams small.**
3. **Keep spawn prompts focused** — *"Teammates load CLAUDE.md, MCP servers, and skills
   automatically, but everything in the spawn prompt adds to their context from the start."*
4. **Shut teammates down when their work is done.**
5. Teams are off by default; `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` enables them.

Control 3 pairs directly with the companion report §2.7's measurement: ~31k tokens of eager
instruction context **per teammate** from this repo alone, before the spawn prompt. The vendor's
advice is to economise on the spawn prompt; the larger lever here is the eager corpus, which the
vendor's advice does not mention because most repos do not have one this size.

### 8.2 What `/usage` attributes — and the caveats it states about itself

> *"On a Pro, Max, Team, or Enterprise plan, `/usage` also shows a breakdown of what counts against
> your plan limits. **It attributes recent usage to skills, subagents, plugins, and individual MCP
> servers**, with each shown as a percentage of the total. It also flags behaviors such as long
> context or cache misses when one accounts for **10% or more** of recent usage. Press `d` or `w`
> to switch between the last 24 hours and the last 7 days."* — `costs.md:36`

🔴 **Teammates are not in that list.** The four attribution buckets are skills, subagents, plugins,
MCP servers. **Control arm:** the same grep for `teammate` over `costs.md` returns hits at lines
134, 138, 139, 140, 141, 246, 277 — the file discusses teammates at length, so their absence from
the attribution sentence is a real omission and not a blind probe. Whether teammate usage lands in
the "subagents" bucket, in the untagged remainder, or is missing entirely is **UNVERIFIED**.

**Four caveats `/usage` states about itself** — all four matter before quoting a figure from it:

1. **Locally computed at list prices.** *"Claude Code computes the dollar figure locally from token
   counts priced at standard list rates, so it doesn't reflect promotional pricing or contracted
   discounts and **may differ from your actual bill**."* Authoritative billing is the Claude
   Console (`costs.md:23`).
2. **This machine only.** *"The figures are **approximate** and computed from **local session
   history on this machine**, so usage from other devices or claude.ai is not included"*
   (`costs.md:36`).
3. **The Session block is for API users.** On Max/Pro *"the session cost figure isn't relevant for
   billing purposes"* (`costs.md:20`).
4. **It can show stale data as if current.** When the plan-limits request fails (usually rate
   limiting), `/usage` shows *"the last usage bars it loaded on this machine within the past 60
   minutes"* with a `Showing last-known usage` note (`costs.md:38`). Press `r` to retry. **Read the
   note before reading the bars.**

On Bedrock / Google Cloud Agent Platform / Microsoft Foundry, *"Claude Code does not send metrics
from your cloud back to Anthropic, so the analytics dashboards and the Claude Code Analytics API
**do not cover this usage**"* (`costs.md:116`).

### 8.3 OTEL — which spans and attributes identify an agent

Tracing is **off by default** and needs **both** `CLAUDE_CODE_ENABLE_TELEMETRY=1` **and**
`CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, plus `OTEL_TRACES_EXPORTER`
(`monitoring-usage.md:146,150`).

**Span hierarchy** (`monitoring-usage.md:172-181`): each user prompt starts a
`claude_code.interaction` root span; API calls, tool calls and hook executions are its children; a
tool span has two children (permission wait, execution). Crucially:

> *"When the Agent tool, or legacy Task tool, spawns a subagent, **the subagent's API and tool
> spans nest under the parent's `claude_code.tool` span**."*

So the trace tree *is* the delegation tree — subagent work is attributable by structure, not just
by attribute.

**The agent-identifying attributes.** On both `claude_code.llm_request` (`:206-208`) and
`claude_code.tool.execution`'s parent `claude_code.tool` (`:239-248`):

| Attribute | Meaning | Gated by |
|---|---|---|
| `agent_id` | *"Identifier of the subagent **or teammate** that issued the request. **Absent on the main session**"* | — |
| `parent_agent_id` | *"Identifier of the agent that spawned this one. Absent for the main session and for agents spawned directly from it"* | — |
| `query_source` | *"Subsystem that issued the request, such as `repl_main_thread` or **a subagent name**"* | — |
| `subagent_type` | *"Subagent type for the Agent tool or legacy Task tool"* | **`OTEL_LOG_TOOL_DETAILS`** |
| `tool_use_id` | Joins the span to the `tool_result` / `tool_decision` events **and to hook payloads** (`:243`) | — |

🟢 **`agent_id` explicitly covers teammates**, and `parent_agent_id` gives the spawn edge. This is
the one surface where teammate work is first-class — better than `/usage` (§8.2). Two absences to
note: `parent_agent_id` is absent *"for agents spawned directly from"* the main session, so the
root edge is implicit; and there is no documented `team_name` span attribute — control arm:
`agent_id` → present twice in the span tables, so the tables are greppable.

**The `claude_code.hook` span** (`monitoring-usage.md:270-283`) is how you would measure this
repo's guard overhead per agent: `hook_event`, `hook_name` (e.g. `PreToolUse:Write`), `num_hooks`,
`duration_ms` (wall-clock for all matching hooks), `num_success`, **`num_blocking`**,
`num_non_blocking_error`, `num_cancelled`.

🔴 **But it is triple-gated.** It is emitted *only* when **detailed beta tracing** is active, which
needs `ENABLE_BETA_TRACING_DETAILED=1` **and** `BETA_TRACING_ENDPOINT` **in addition to** the trace
exporter config, **and** — in interactive CLI sessions — *"your organization to be allowlisted for
the feature"*. Agent SDK and `-p` sessions are not gated. *"It is **not** emitted when only
`CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` is set"* (`monitoring-usage.md:272`). So the natural way to
re-derive the ~340 ms/edit guard cost per teammate is **not available in an interactive session on
a non-allowlisted org**. Measure it out-of-band instead.

### 8.4 🔴 The cost METRIC cannot tell your custom agents apart

The **Cost counter** metric, incremented after each API request, carries
(`monitoring-usage.md:528-536`): `model`, `query_source` (one of `"main"`, `"subagent"`,
`"auxiliary"`), `speed`, `effort`, `agent.name`, `skill.name`, `plugin.name`, `marketplace.name`.

> `agent.name`: *"Subagent type that issued the request. Built-in agent names and agents from
> official-marketplace plugins appear verbatim. **Other user-defined agent names are replaced with
> `"custom"`.** Absent when the request was not issued by a named subagent type."*

**A 9-role team of project-local definitions therefore reports `agent.name = "custom"` for all
nine** in the cost metric. The same redaction hits `skill.name` and `plugin.name` for third-party
plugins (`"third-party"`). Per-role cost attribution must come from the **spans** (`agent_id` /
`parent_agent_id`, §8.3), not the cost metric — and `query_source` on the metric is only a
three-way category. Note also that `query_source` takes **different value spaces** on the metric
(`"main"`/`"subagent"`/`"auxiliary"`, `:530`) and on the span (`repl_main_thread`, `compact`, or a
subagent name, `:206,636`) — a dashboard that joins them on that field will silently mismatch.

### 8.5 Per-subagent cost without any telemetry at all

`PostToolUse` on the `Agent` tool receives usage telemetry directly in `tool_response` — *"Read
these fields to record per-subagent cost from a hook"* (`hooks.md:1503`):

`status`, `agentId`, `content`, `resolvedModel`, `modelsUsed`, **`totalTokens`**,
`totalDurationMs`, `totalToolUseCount`, and `usage` (`input_tokens`, `output_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`).

⚠️ **This only works for FOREGROUND subagents.** *"For background subagents, the tool returns when
the task moves to the background, so `tool_response` carries **no usage fields**"* — you get
`status: "async_launched"`, `agentId`, `description`, `prompt`, `outputFile`, `resolvedModel` only
(`hooks.md:1517`). **Subagents default to background as of v2.1.198** (`:1507`), so the default
path yields no cost data. A hook-based cost ledger must either force foreground or correlate
`agentId` against `SubagentStop` later.

`resolvedModel` is worth logging on its own: it *"can differ from the `model` value in
`tool_input`"* when `availableModels` or another override applies (`hooks.md:1519`) — which is
exactly the silent-skip behaviour the companion report flags at `sub-agents.md:314`. It is the only
way to observe that an agent did **not** run on the model you asked for.

### 8.6 Observability verdict

The field's standing criticism of multi-agent systems is that you cannot see what the agents did.
Here, the surfaces are unevenly good:

| Question | Best available answer | Quality |
|---|---|---|
| Which agent made this API call? | `agent_id` / `parent_agent_id` on `llm_request` spans | 🟢 Good, covers teammates |
| What did the delegation tree look like? | Span nesting under the parent's `claude_code.tool` span | 🟢 Good |
| What did **this named role** cost? | Cost-counter `agent.name` → **`"custom"`** for user-defined agents | 🔴 Blind |
| What did **one subagent** cost? | `PostToolUse` on `Agent` → `totalTokens`, `usage` | 🟠 Foreground only; background is the default |
| What is my hook overhead per agent? | `claude_code.hook` span | 🟠 Triple-gated, org allowlist in interactive CLI |
| What did teammates cost? | `/usage` breakdown | 🔴 Not an attribution bucket |
| Did an agent run on the model I asked for? | `resolvedModel` in `tool_response` | 🟢 Good, and the only route |

One more constraint that closes an obvious workaround: **`OTEL_*` exporter variables are removed
from every subprocess Claude Code spawns, including hooks** (`hooks.md:645`). A hook cannot
piggyback on the parent's OTEL configuration to emit its own spans — it must carry its own endpoint
config. (Tracing does export `TRACEPARENT` into Bash/PowerShell subprocesses so they can parent
their spans under the same trace — `monitoring-usage.md:158` — but that is the trace *context*, not
the exporter *destination*.)

## 9. Cross-cutting findings and corroborations

### 9.1 The 8-block cap, three independent routes

Beyond `env-vars.md:336` and `hooks.md:2194`, `best-practices.md:47` states it a third time, in a
different context (the "deterministic gate" pattern): *"a Stop hook runs your check as a script and
blocks the turn from ending until it passes. **Claude Code overrides the hook and ends the turn
after 8 consecutive blocks.**"* `changelog.md` records the same number alongside the override
variable. Three routes, one number — this one is safe to build on.

`best-practices.md:50` also frames the escalation this repo would care about: *"Each step trades
setup for attention. The prompt version works on any task today. The `/goal` and Stop hook versions
are what let an unattended run finish correctly **without you**."*

### 9.2 The vendor's own hooks-vs-prose doctrine

Independently arrived at, and identical to `mise-tasks-only.md`'s enforcement-layer doctrine:

> *"Use hooks for actions that must happen every time with zero exceptions… **Unlike CLAUDE.md
> instructions which are advisory, hooks are deterministic and guarantee the action happens.**"* —
> `best-practices.md:245,248`

> *"Like CLAUDE.md, rules are **guidance Claude reads, not configuration Claude Code enforces**.
> For guaranteed behavior use hooks or permissions."* — `claude-directory.md:168`

That is the vendor stating, about `.claude/rules/*.md` specifically, what this repo learned the
expensive way: markdown alone is never the only layer. It applies directly to
`agent-report-persistence.md` rule 1b, which has now failed twice in prose form and has a
documented hook (`TeammateIdle`, §3.4) available to carry it.

### 9.3 🔴 `~/.claude/teams/` is undocumented in the directory reference

`claude-directory.md` — the page whose whole job is *"Where Claude Code reads CLAUDE.md,
settings.json, hooks, skills, commands, subagents, workflows, rules, and auto memory"* (`:7`) —
mentions `teams/` **0 times**. **Control arm:** `tasks/` in the same file → **3** hits (`:1531`,
`:1628`, plus the per-session cleanup list), so the file does cover team-adjacent state and the
probe discriminates.

Consequence: `~/.claude/teams/{team-name}/config.json` and `inboxes/*.json` are documented **only**
in `agent-teams.md:226-235`. Anyone auditing the `.claude` surface from the directory reference —
including a security or backup review — will miss the mailbox files entirely. `claude-directory.md`
does list `~/.claude/tasks/` under *"Nothing user-facing"* (`:1628`), which is also where a team's
**persistent** task list lives.

### 9.4 Where the pieces this repo needs actually live

Mapping the two gates the companion report §2.4 called for onto the documented surface:

| Wanted | Documented mechanism | Verdict |
|---|---|---|
| Refuse to start a writing agent on the default branch | **`PreToolUse` matcher `Agent`**, read `.tool_input.subagent_type`, return `permissionDecision: "deny"` (§2.2) | ✅ Works. `SubagentStart` **cannot** (§2.1) — and cannot even run a `prompt`/`agent` hook (§5.3) |
| Force an agent to deliver its report before idling | **`TeammateIdle`** exit 2 for teammates (§3.4, vendor example at `hooks.md:2346-2352`); **`SubagentStop`** `decision: "block"` for Agent-tool subagents (§2.4) | ✅ Works, bounded at 8 consecutive blocks |
| Tell every delegated agent its branch, report path and persistence rule | **`SubagentStart`** `additionalContext`, injected before the subagent's first prompt (§2.3) | ✅ Works — this is what `SubagentStart` is *for* |
| Isolate 9 teammates' file writes | — | 🔴 **Nothing.** Teams do not use worktrees (§7.1); partition by prompt |
| Attribute cost per named role | Spans' `agent_id`/`parent_agent_id` (§8.3) | 🟠 Spans yes; the cost **metric** reports `"custom"` for all user-defined agents (§8.4) |
| Escalate a question to the human from inside a teammate | — | 🔴 `AskUserQuestion` is removed from every delegated agent (companion report §2.4 item 1). `SendMessage` to the lead is the only route; the **lead** owns the ask |

## Open items and UNVERIFIED claims

Per this repo's evidence policy, every claim above carries a `file:line` except these.

- **UNVERIFIED — `MessageDisplay`'s hook-type support.** It appears in none of the three lists at
  `hooks.md:2821-2852`. The §1 count of 30 is unaffected (four other routes).
- **UNVERIFIED — whether `continueOnBlock` applies to `agent`-type hooks.** Listed on the prompt
  table (`hooks.md:2891`), absent from the agent table (`:2968-2973`), while the prose says the
  fields are "the same" (`:2966`).
- **UNVERIFIED — where teammate usage lands in the `/usage` breakdown.** The attribution buckets
  are skills, subagents, plugins, MCP servers (`costs.md:36`); teammates are not named. Control arm
  run (§8.2) — the absence is real, the *destination* is unknown.
- **UNVERIFIED — which auto-compaction branch applies on `claude-opus-5[1m]`.** `env-vars.md:189`
  names Sonnet 4.6 / Opus 4.6 and a set of conditions for *proactive* compaction and gives Opus 4.8
  as an at-the-limit example; Opus 5 is in neither list. Decides whether a `PreCompact` block is
  recoverable or fatal (§4.2).
- **UNVERIFIED — the arXiv 2607.22917v2 claim** about compaction eroding working detail. Inherited
  from the brief, not read. §4 answers what the harness offers **without** relying on it.
- **NOT RE-DERIVED — the ~340 ms/edit guard cost** quoted in §5.4. Inherited from memory
  `project_session_2026-08-03-f` and labelled as such per `probes-need-a-control-arm.md` rule 6.
  §8.3 explains why the natural re-derivation (`claude_code.hook` spans) is unavailable here.
- **NOT MEASURED — every behavioural claim in this report.** This is a documentation review. No
  hook was configured, no teammate spawned, no probe run against a live session. Absences are
  control-armed **against the documentation corpus**, which establishes that the docs are silent,
  **not** that the harness lacks the behaviour. `probes-need-a-control-arm.md` rule 3's warning
  applies in full: a doc corpus is a bounded search space.
- **Citations were audited, and 33 were wrong.** After drafting, every `file:line` in a sample of
  ~45 was re-resolved with `sed -n "${N}p" <file>`. The exit-code-2 table's 30 per-row citations
  were **systematically off by 1–5 lines** (an off-by-N introduced when transcribing a long table),
  plus three prose refs. All 33 are corrected above and re-verified to land on the named event.
  **Control arm:** the same re-resolution on the untouched refs (`hooks.md:874`, `:1550`, `:1555`,
  `:2194`, `agent-teams.md:226`, `:370`, `:426`, `costs.md:36`, `monitoring-usage.md:533`,
  `settings.md:373`, `worktrees.md:93`) returned the expected text unchanged — so the audit
  discriminates between a good and a bad citation rather than flagging everything. Treat any
  `file:line` in this report as verified for the audited sample and *spot-checked* elsewhere; the
  quoted text, not the line number, is the load-bearing part.
- **Version note.** The offline tree was treated as current per the brief. `agent-teams.md:18`
  self-describes as *"as of v2.1.178"* while this host runs **2.1.221** (companion report §2), so
  the teams page is the one most likely to lag its own subject. Claims carrying an explicit
  "requires vX" note are the reliable ones; the unversioned prose on that page is the weakest tier
  of evidence in this report.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the subject: every `$CC/*.md`
  page cited (`hooks.md`, `agent-teams.md`, `agents.md`, `worktrees.md`, `settings.md`,
  `env-vars.md`, `costs.md`, `monitoring-usage.md`, `context-window.md`, `best-practices.md`,
  `claude-directory.md`, `features-overview.md`, `champion-kit.md`, `sub-agents.md`,
  `agent-view.md`, `changelog.md`) is vendored from this repo's docs. Also the linked
  `examples/hooks/bash_command_validator_example.py` reference implementation (`hooks.md:933`).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — hosts the offline
  vendor doc tree at `sources/agent-harness-docs/docs/claude-code`; the sole corpus for this report.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the consuming repo: its
  `.claude/rules/*.md`, `hook_guard.py`/`branch_guard`, and the companion
  `harness-settings-reference.md` are what §9.4 maps the documented mechanisms onto.
- [mkusaka/it2](https://github.com/mkusaka/it2) — required CLI for `teammateMode: "iterm2"`, and the
  subject of the setup prompt under `"auto"`/`"tmux"` (`agent-teams.md:109,127-130`).
- [tmux/tmux](https://github.com/tmux/tmux) — split-pane backend; its wiki is the vendor's install
  pointer, and `tmux ls` / `tmux kill-session` is the orphaned-session fix (`agent-teams.md:129,410`).

_Non-GitHub sources: `https://code.claude.com/docs/en/*.md` (the live equivalents of every page
above, not re-fetched for this report — the offline tree was used per the brief);
`https://git-scm.com/docs/git-worktree` (linked by `worktrees.md:9`)._
