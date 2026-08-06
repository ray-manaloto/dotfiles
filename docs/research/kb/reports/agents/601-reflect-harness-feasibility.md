# Claude Code expertise — self-reflection loop feasibility (#601) (2026-08-06, v2.1.223)

⚠️ **Version moved**: the ledger in `.claude/agents/claude-code-expert.md` is pinned at
**2.1.222**; the installed binary is **2.1.223** (`claude --version` → `2.1.223 (Claude Code)`).
Claims below are re-derived at 2.1.223 or explicitly marked inherited/UNVERIFIED.

Corpora consulted: offline docs `$CC` / graphify KB prose graph / binary byte-scan /
live probe (I am myself a teammate in the session under study) / repo source.

`$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`

---

## Verdict table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | CONFIRMED | **31 hook events exist** at 2.1.223 | shape-enum → 31 unique; control `PreToolUse` → 72, fresh bogus term → 0 |
| 2 | CONFIRMED | A **`type: "agent"` hook exists** — spawns ONE subagent, ≤50 turns, tool access | `$CC/hooks.md:3120-3160` |
| 3 | **REFUTED** | "SessionEnd can run an agent hook" — **SessionEnd does NOT support `prompt` or `agent` hooks** | `$CC/hooks.md:2996-3010` explicit exclusion list |
| 4 | CONFIRMED | An agent hook's ONLY return channel is `{ok, reason}` — a gate, not a producer | `$CC/hooks.md:3131-3145` |
| 5 | CONFIRMED | **`async: true` is `type: "command"` ONLY** | `$CC/hooks.md:3175` verbatim |
| 6 | CONFIRMED | **SessionEnd hooks share a 1.5-SECOND budget**, ceiling 60 s | `$CC/hooks.md:2857`, `:415` |
| 7 | CONFIRMED | Frontmatter = **16 documented fields**, **19 in the binary** — `effort`, `maxTurns`, `color` all real | `$CC/sub-agents.md:282-297` + binary string table |
| 8 | CONFIRMED | **A subagent CAN read the session transcript**; path derivable from `$CLAUDE_CODE_SESSION_ID` | live probe, rc=0, 2739 lines; control bogus id → not readable |
| 9 | CONFIRMED | **Every teammate's full transcript is on disk** under `<session>/subagents/` | live probe: 5 files, 100% `isSidechain` |
| 10 | CONFIRMED | A subagent starts with **fresh context** — no history, no loaded skills, no read files | `$CC/sub-agents.md:921` |

---

## Q1 — Where can the loop be triggered from?

### The 31 hook events (shape-enumerated, NOT an expected list)

Probe: `grep -rhoE '"hook_event_name": *"[A-Za-z]+"' "$CC/" | sort -u` → **31 unique**.
Control: `PreToolUse` → 72 hits; freshly-invented term → 0. The probe discriminates.

```
ConfigChange  CwdChanged  DirectoryAdded  Elicitation  ElicitationResult
FileChanged   InstructionsLoaded  MessageDisplay  Notification  PermissionDenied
PermissionRequest  PostCompact  PostToolBatch  PostToolUse  PostToolUseFailure
PreCompact  PreToolUse  SessionEnd  SessionStart  Setup  Stop  StopFailure
SubagentStart  SubagentStop  TaskCompleted  TaskCreated  TeammateIdle
UserPromptExpansion  UserPromptSubmit  WorktreeCreate  WorktreeRemove
```

⚠️ **Corrects a repo belief.** Memory `feedback_enumerate_dont_assert_the_list` records
"18 of 29 hook events". At 2.1.223 it is **31** — `TaskCreated`, `TaskCompleted` and
`TeammateIdle` are new-to-us and directly relevant to a DAG node type.

### ⚠️ The SessionEnd 1.5-second budget

`$CC/hooks.md:2857`, verbatim:

> SessionEnd hooks have a default timeout of **1.5 seconds**. … The overall budget is
> automatically raised to the highest per-hook timeout configured in settings files,
> **up to 60 seconds**. Timeouts set on **plugin-provided hooks don't raise the budget**.
> To override the budget explicitly, set `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`.

Plus `$CC/hooks.md:2855`: *"SessionEnd hooks have no decision control. They can't block
session termination."*

**So SessionEnd cannot host the reflection team.** 60 s is the hard ceiling and the session
will not wait. The existing `command-audit` hook fits only because it is a cheap
transcript scan.

### ⚠️ Trigger-surface table — which events can natively run an agent

`$CC/hooks.md:2977-3010` splits the 31 events by supported hook type. **13 events support
all five types** (`command`, `http`, `mcp_tool`, `prompt`, `agent`):

`PermissionDenied`, `PermissionRequest`, `PostToolBatch`, `PostToolUse`,
`PostToolUseFailure`, `PreToolUse`, `Stop`, `SubagentStop`, `TaskCompleted`,
`TaskCreated`, `TeammateIdle`, `UserPromptExpansion`, `UserPromptSubmit`

**15 events support `command`/`http`/`mcp_tool` but NOT `prompt` or `agent`** — and
**`SessionEnd` is in this list**, along with `PreCompact`, `PostCompact`, `SubagentStart`,
`StopFailure`, `Notification`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`,
`DirectoryAdded`, `FileChanged`, `Elicitation`, `ElicitationResult`, `WorktreeCreate`,
`WorktreeRemove`.

`SessionStart` and `Setup` are narrower still: **`command` and `mcp_tool` only** — no
`http`, no `prompt`, no `agent`.

**Net for tier 1:** of the events that naturally mark "a unit of work just ended", only
**`Stop`**, **`SubagentStop`**, **`TaskCompleted`** and **`TeammateIdle`** can natively run
an agent hook. `SessionEnd` and `PreCompact` cannot.

### The trigger options, ranked

| Trigger | Can run an agent natively? | Can block? | Time budget | Fit for the reflection loop |
|---|---|---|---|---|
| `SessionEnd` | **No** (command/http/mcp only) | No | **1.5 s → 60 s max** | Only as a *launcher* of a detached process |
| `Stop` | **Yes** | **Yes** (≤8 consecutive blocks) | 600 s command / 60 s agent | Fires **every turn** — too hot without a guard |
| `SubagentStop` | Yes | Yes | as above | Per-agent, not per-unit-of-work |
| `TaskCompleted` | Yes | Yes | as above | **Best native fit for a DAG node boundary** |
| `TeammateIdle` | Yes | Yes | as above | Fires as a teammate goes idle |
| `PreCompact` | **No** | Yes | 600 s | Context-pressure trigger only, command-type |
| Skill step (`/clear-prep`) | n/a — it's the session itself | n/a | none | **Tier 1's real home** |
| launchd tick → `claude -p`/`--bg` | Yes, full session | n/a | none | **Tier 2's real home** |

---

## Q2 — Can a hook spawn a team? (the load-bearing question)

**Answer: NO natively. A hook can spawn ONE subagent (`type: "agent"`), or reach a full
team only by shelling out to a detached `claude` process from a `command` hook.**

### 2a. The `type: "agent"` hook — ONE subagent, `{ok}` return only

`$CC/hooks.md:3120-3145`, verbatim:

> Agent-based hooks (`type: "agent"`) are like prompt-based hooks but with multi-turn tool
> access. Instead of a single LLM call, **an agent hook spawns a subagent** that can read
> files, search code, and inspect the codebase to verify conditions.
>
> 1. Claude Code spawns **a subagent** with your prompt and the hook's JSON input
> 2. The subagent can use tools like Read, Grep, and Glob to investigate
> 3. **After up to 50 turns**, the subagent returns a structured `{ "ok": true/false }` decision

Config fields: `type`, `prompt`, `model` (defaults to a **fast model**), `timeout`
(default **60 s**).

⚠️ **Four hard limits that constrain the design:**

1. **Singular.** One subagent, never a team.
2. **Return channel is `{ok, reason}` only.** It cannot hand back a prescriptive document;
   anything it produces must be written to disk as a side effect.
3. **Cannot be async.** `async` is `type: "command"`-only (`$CC/hooks.md:3175`), so an agent
   hook always blocks within its timeout.
4. **EXPERIMENTAL.** `$CC/hooks.md` carries a `<Warning>`: *"Agent hooks are experimental.
   Behavior and configuration may change… For production workflows, prefer command hooks."*

### 2b. The only route to a real team: a detached `command` hook

`$CC/hooks.md:3196-3199`, verbatim:

> * In non-interactive mode with the `-p` flag, Claude Code **kills any async hook still
>   running at teardown** and finalizes it with outcome `cancelled`
> * **If your hook's work must outlive a `claude -p` session, start a fully detached
>   process from it**

That is the harness's own sanctioned pattern, and the only one that survives teardown. It
means the reflection team runs in a **new session**, not the one being reflected on — which
is fine, because (Q5) the session's whole transcript is on disk by then.

⚠️ **Ledger cross-check (inherited, 2.1.222):** `--bg` + `--print` is a hard rc=1 error, and
an unknown slash verb under `--bg` creates a live job at rc=0. Both bite a launcher script.

---

## Q3 — Durable subagent-definition fields (exact)

**16 documented fields** — `$CC/sub-agents.md:282-297`, read as a table (shape-enumerated,
not an expected list):

| Field | Req | Note (abridged from the docs) |
|---|---|---|
| `name` | **Yes** | lowercase + hyphens; no `:` (reserved for plugin scope); filename need not match |
| `description` | **Yes** | when Claude should delegate |
| `tools` | No | allowlist; inherits all subagent-available tools if omitted |
| `disallowedTools` | No | denylist, removed from inherited/specified list |
| `model` | No | `sonnet`/`opus`/`haiku`/`fable`/full ID/`inherit`. **Defaults to `inherit`** |
| `permissionMode` | No | `default`/`acceptEdits`/`auto`/`dontAsk`/`bypassPermissions`/`plan`/`manual` |
| `maxTurns` | No | **YES, it exists** — max agentic turns before the subagent stops |
| `skills` | No | preloaded into context at startup; **full content injected**, not just description |
| `mcpServers` | No | name reference or inline definition |
| `hooks` | No | lifecycle hooks scoped to this subagent |
| `memory` | No | `user`/`project`/`local` — enables cross-session learning |
| `background` | No | `true` = always background; **default since v2.1.198 is background anyway** |
| `effort` | No | **YES, it exists** — `low`/`medium`/`high`/`xhigh`/`max`; overrides session effort |
| `isolation` | No | `worktree` (binary also accepts `remote`) |
| `color` | No | **YES** — `red`/`blue`/`green`/`yellow`/`purple`/`orange`/`pink`/`cyan` |
| `initialPrompt` | No | auto-submitted first user turn when run as the **main** session agent |

**The maintainer's ask — model and effort per role — is directly supported:** `model:` and
`effort:` are both first-class frontmatter fields. `effort` overrides the session level, and
available levels depend on the model.

### Three undocumented fields the binary carries (19 total)

Binary string-table extraction at 2.1.223 shows the agent-frontmatter cluster carrying, in
addition to the 16 above: **`observer`**, **`observerMessage`**, **`observeSubagents`**.

Doc coverage probe across all 177 pages, with control arms:

| Token | Doc files | Binary count |
|---|---:|---:|
| `observer` | **0** | — |
| `observerMessage` | **0** | 27 |
| `observeSubagents` | **0** | 12 |
| `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS` | **0** | — |
| *control* `initialPrompt` | 6 | 49 |
| *control* `maxTurns` | 14 | 57 |
| *control* fresh bogus token | 0 | **0** |

The controls fire in both directions, so the zeros are real. This re-derives the ledger's
2.1.222 "19 fields, not 16" row **unchanged at 2.1.223**.

⚠️ **Caveat — existence, not semantics.** I established that these three strings ship and
sit in the frontmatter cluster. I did **not** establish that they are reachable or behave as
named. The ledger records them as gated by `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS`
(inherited, 2.1.222). Treat `observer` as **UNVERIFIED** for design purposes.

---

## Q4 — What a subagent does NOT inherit

`$CC/sub-agents.md:921`, verbatim — the direct answer:

> Each subagent starts with a **fresh, isolated context window. It doesn't see your
> conversation history, the skills you've already invoked, or the files Claude has already
> read.** Claude composes a delegation message that summarizes the task, and the subagent
> works from there. The exception is a **fork**, which inherits the parent conversation.

**Does NOT inherit:** conversation history; invoked skills; files already read.
**DOES inherit:** permissions context; model (default `inherit`); MCP tools; extended-thinking
config (since v2.1.198); built-in tools minus two filters.

### The two tool filters (this is where a reflection agent can lose capability)

**Filter 1 — removed from EVERY subagent**, even if listed in `tools`
(`$CC/sub-agents.md:331-339`): `Agent` (at depth limit), `AskUserQuestion`,
`EndConversation`, `EnterPlanMode`, `ExitPlanMode` (unless `permissionMode: plan`),
`ScheduleWakeup`, `TaskOutput`, `WaitForMcpServers`, `Workflow`.

**Filter 2 — background subagents** (the default since v2.1.198) keep every MCP tool but
**only** these built-ins (`$CC/sub-agents.md:341`): `Read`, `Grep`, `Glob`, `Bash`,
`PowerShell`, `Edit`, `Write`, `NotebookEdit`, `WebFetch`, `WebSearch`, `TodoWrite`,
`Skill`, `ToolSearch`, `EnterWorktree`, `ExitWorktree`, `Monitor`, `TaskStop`,
`SendMessage`, `Artifact`.

**Good news for this design:** `Read`, `Grep`, `Bash`, `Write`, `Edit`, `Skill` and
`SendMessage` all survive filter 2 — a background reflection agent can read transcripts,
write its report, and message the lead.

**Bad news:** `AskUserQuestion` is gone unconditionally (ledger row, re-confirmed here at
`:332`), and `Workflow` is stripped — so a reflection agent **cannot invoke a workflow** and
cannot ask the user anything.

Teammates additionally keep `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `CronCreate`,
`CronDelete`, `CronList` (`$CC/sub-agents.md:343`) — **the task tools survive, which is what
makes tier 2 DAG integration possible from inside a teammate.**

**Nesting depth:** `$CC/sub-agents.md:867` — a subagent can spawn subagents "up to three
layers below the main conversation"; at the limit `Agent` is withheld. So a reflection agent
*can* itself fan out, but only if it is not already at depth 3.

---

## Q5 — Can an agent read the current session's transcript?

**YES — confirmed by live probe, from inside a subagent, with a control arm.**

### The main session transcript

`transcript_path` is a **common input field on every hook event** (`$CC/hooks.md:704`). For
an agent (not a hook), the path is derivable from the environment. Live probe from my own
Bash (I am a teammate in the session under study):

```
SESSION_ID=99d89987-5c97-45a2-9bf9-0d7f80a1ed54
/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/99d89987-….jsonl
READABLE rc=0
    2739 <that file>
```

**Control arm:** the same `test -r` against a freshly-invented bogus session id →
`NOT readable -> probe discriminates`.

⚠️ **`$CLAUDE_CODE_SESSION_ID` inside a subagent names the PARENT session, not the
subagent.** That is what makes this useful: a delegated reflection agent reads the *main*
conversation without being told where it is.

The repo already encodes the path rule in `python/src/dotfiles_setup/command_audit.py:212-233`:
base = `$CLAUDE_CONFIG_DIR/projects` (default `~/.claude/projects`), directory =
`encode_cwd(cwd)` = `re.sub(r"[/.]", "-", str(cwd))`, file = `<session>.jsonl`.

**CLAUDE_* vars visible to a subagent's Bash** (names only): `CLAUDE_CODE_SESSION_ID`,
`CLAUDE_CODE_TASK_LIST_ID`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_FORK_SUBAGENT`,
`CLAUDE_CODE_BRIEF`, `CLAUDE_CODE_BRIDGE_SESSION_ID`, `CLAUDE_CODE_ENTRYPOINT`,
`CLAUDE_EFFORT`, `CLAUDE_PID`, `CLAUDECODE`, plus the three spawn-control caps.

### ⚠️ EVERY teammate's full transcript is also on disk — and this is the big one

```
~/.claude/projects/<encoded-cwd>/<session-id>/subagents/agent-a<name>-<16hex>.jsonl
```

Live listing from this very session (modified in the last 60 min):

```
 463065  …/99d89987-…/subagents/agent-aloop-forensics-2c834d8741f3cf43.jsonl   55 lines, sidechain=55
 409480  …/99d89987-…/subagents/agent-aprocess-designer-1816852bb0ec3905.jsonl 53 lines, sidechain=53
 471136  …/99d89987-…/subagents/agent-arule-coverage-52552f8bad89435f.jsonl    56 lines, sidechain=56
 317915  …/99d89987-…/subagents/agent-acost-analyst-341b50ac36e2c184.jsonl     62 lines, sidechain=62
 371237  …/99d89987-…/subagents/agent-aharness-expert-98e78679eaca2fcb.jsonl   93 lines, sidechain=93
```

The last one is **me**. Every line in every subagent file carries `isSidechain: true`; the
parent transcript carries **`isSidechain` = 0**. The split is clean:

- **parent `<session>.jsonl`** — main thread only (2,753 lines, types include `assistant`,
  `user`, `attachment`, `agent-name`, `last-prompt`, `queue-operation`)
- **`<session>/subagents/*.jsonl`** — one complete transcript per delegated agent

**This is decisive for the design.** A reflection loop that reads only the main transcript
sees the lead's turns and *none* of the team's actual work. Reading `<session>/subagents/`
gives it every agent's full tool-call history — which is precisely the raw material a
"what went wrong / what repeated" analysis needs.

⚠️ **`command_audit.py` currently misses this.** `project_transcripts()` globs `*.jsonl` in
the project dir only (line 233) — it never descends into `<session>/subagents/`. So the
existing self-learning loop is, today, **blind to all subagent activity**. That is a
concrete, actionable gap for #601.

### ⚠️ A false negative I produced and caught — worth recording

My first probe was `find ~/.claude -maxdepth 3 -type d -name 'subagents'` → **no output**,
and I nearly reported "no subagents dir exists". The directory is at **depth 4**. The
`-maxdepth 3` bound turned *absent* into *unreachable* — exactly the failure
`.claude/rules/probes-need-a-control-arm.md` rule 3 describes ("bound-limited searches are
suspect by construction"). It was caught only because a second, unbounded route
(`find … -name '*.jsonl' -mmin -60`) contradicted it. **Two probes disagreed and the broken
one was mine.**

Also note `$CC` documents `agent_transcript_path` as a `SubagentStop` hook input
(`changelog.md:4407`, `agent-sdk__typescript.md:1815`) — a second, independent route to the
same files, delivered rather than derived.

---

## What this means for the design

**Tier 1 (`/clear-prep` skill step) — feasible, and the skill is the right host.**
A skill step runs *inside* the live session, so it has no hook time budget, can spawn a
real team via the `Agent` tool, and can read both the main transcript and every
`subagents/*.jsonl`. This is strictly better than any hook-based trigger.

**A `SessionEnd` hook cannot host it** (1.5 s → 60 s, no agent hook type, no blocking). Its
only viable role is to *launch a fully detached process*, per `$CC/hooks.md:3199`.

**Tier 2 (DAG node) — feasible.** A teammate keeps `TaskCreate`/`TaskGet`/`TaskList`/
`TaskUpdate`, so a reflection node can read and update the DAG from inside. The launchd
tick → `claude` route has no time bound at all.

**The strongest *native* trigger** for "a unit of work just finished" is **`TaskCompleted`**
(supports agent hooks, can block, fires at a task boundary) — closer to a DAG node boundary
than `Stop`, which fires every turn.

**Per-role model + effort is directly supported** by frontmatter `model:` and `effort:`.

### `TaskCompleted` in detail — the best native tier-2 trigger

`$CC/hooks.md:2252-2258`, verbatim:

> Runs when a task is being marked as completed. This fires in two situations: **when any
> agent explicitly marks a task as completed through the TaskUpdate tool**, or **when an
> agent team teammate finishes its turn with in-progress tasks**. Use this to enforce
> completion criteria like passing tests or lint checks before a task can close.
>
> When a `TaskCompleted` hook exits with code 2, **the task is not marked as completed** and
> the stderr message is fed back to the model as feedback. To stop the teammate entirely,
> return `{"continue": false, "stopReason": "..."}`. **TaskCompleted hooks don't support
> matchers and fire on every occurrence.**

Input carries `task_id`, `task_subject`, `transcript_path`, and optionally
`task_description`, `teammate_name`, `team_name`.

**Why this is the right tier-2 trigger:** it fires at a genuine unit-of-work boundary (not
per-turn), it supports `agent` hooks, it can block completion until reflection criteria are
met, and it hands over the team/teammate identity so the loop knows *whose* work to reflect
on. ⚠️ **Constraint: no matchers** — it fires on *every* task completion, so any scoping must
happen inside the hook body.

### `Stop` — usable but hot, and it has a hard block ceiling

`$CC/hooks.md:2320`, verbatim: Stop hooks receive `stop_hook_active`,
`last_assistant_message`, `background_tasks`, `session_crons`. *"`stop_hook_active` is `true`
when Claude Code is already continuing as a result of a stop hook. Check this value or
process the transcript to avoid blocking on a condition that will never resolve. **Claude
Code overrides the hook and ends the turn after 8 consecutive blocks.**"*

This re-confirms the inherited ledger row at 2.1.223. `background_tasks` also lets a hook
distinguish "session done" from "waiting on background subagents" — relevant if reflection
must wait for a team to finish.

---

## Ledger entries to append

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| **31 hook events** (not 29) — `TaskCreated`, `TaskCompleted`, `TeammateIdle` among them | CONFIRMED | shape-enum of `hook_event_name` → 31; control `PreToolUse` 72 vs fresh term 0 | 2.1.223 | 2026-08-06 |
| **`SessionEnd` supports NEITHER `prompt` NOR `agent` hooks** — command/http/mcp_tool only; `SessionStart`/`Setup` are command/mcp_tool only | CONFIRMED | `$CC/hooks.md:2996-3010` explicit exclusion list | 2.1.223 | 2026-08-06 |
| Exactly **13 events support all five hook types**; a `type:"agent"` hook spawns **ONE** subagent, ≤50 turns, returns only `{ok,reason}`, **cannot be async**, marked EXPERIMENTAL | CONFIRMED | `$CC/hooks.md:2977-3010, 3120-3175` | 2.1.223 | 2026-08-06 |
| **SessionEnd hooks share a 1.5 s budget**, raised only to the max per-hook `timeout` in *settings* files (plugin hooks don't raise it), ceiling **60 s**; override `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` | CONFIRMED | `$CC/hooks.md:2857`, `:415` | 2.1.223 | 2026-08-06 |
| **Every subagent/teammate writes a FULL transcript** to `~/.claude/projects/<encoded-cwd>/<session-id>/subagents/agent-a<name>-<16hex>.jsonl`, 100% `isSidechain:true`; the parent `<session>.jsonl` has `isSidechain` **0** | CONFIRMED | live probe, 5 files this session incl. my own; control: bogus session id unreadable | 2.1.223 | 2026-08-06 |
| **`$CLAUDE_CODE_SESSION_ID` inside a subagent names the PARENT session**, making the main transcript runtime-derivable with no configuration | CONFIRMED | live probe rc=0, 2739 lines; control bogus id → not readable | 2.1.223 | 2026-08-06 |
| ⚠️ **`find -maxdepth 3` hid the `subagents/` dir (it is at depth 4)** — a bounded search reported absence; caught only by an unbounded second route | CONFIRMED | my own false negative, this run | 2.1.223 | 2026-08-06 |
| Frontmatter re-derived at 2.1.223: **16 documented + `observer`/`observerMessage`/`observeSubagents` = 19**; `effort`, `maxTurns`, `color` are all real documented fields | CONFIRMED | `$CC/sub-agents.md:282-297` + binary; doc control `initialPrompt` 6 / `maxTurns` 14 vs observer* 0, fresh token 0 | 2.1.223 | 2026-08-06 |
| Filter-2 background subagents keep `Read/Grep/Glob/Bash/Edit/Write/Skill/SendMessage/Artifact/Monitor/…`; **`Workflow` and `AskUserQuestion` are stripped**; teammates additionally keep all Task* and Cron* tools | CONFIRMED | `$CC/sub-agents.md:331-343` | 2.1.223 | 2026-08-06 |
| A subagent gets **fresh context** — no conversation history, no invoked skills, no files already read; only a **fork** inherits | CONFIRMED | `$CC/sub-agents.md:921`, `:1009` | 2.1.223 | 2026-08-06 |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `command_audit.py` transcript-path derivation; the `/clear-prep` + DAG design this report serves
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline `agent-harness-docs` corpus (`$CC`) and the graphify prose graph used for orientation
