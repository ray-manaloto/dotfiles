# Claude Code Agent Teams — re-review (2.1.222)

Binary: `/Users/rmanaloto/.local/share/claude/versions/2.1.222` (271,289,792 bytes, 2026-08-04)
Docs: `$CC = ~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`
Date: 2026-08-05. Status: **COMPLETE**.

## Findings table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| F1 | CONFIRMED | Agent teams are experimental, **off by default**, gated on `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | `$CC/agent-teams.md:10`; binary env table |
| F2 | CONFIRMED | `TeamCreate`/`TeamDelete` are gone; `team_name` on the Agent tool is accepted-and-ignored | `$CC/agent-teams.md:18` |
| F3 | CONFIRMED | No project-level team config exists; it is runtime state and is overwritten | `$CC/agent-teams.md:237,243` |
| F4 | CONFIRMED | Task list = `<configDir>/tasks/<sanitized-id>/<task-id>.json`, one file per task | binary @246204753; control `CLAUDE_CODE_QWFJVX_NOPE` → 0 vs `CLAUDE_CODE_TASK_LIST_ID` → 5 |
| F5 | CONFIRMED | Tasks are carried into a forked session, but **not** when `CLAUDE_CODE_TASK_LIST_ID` is set | binary @259907526 |
| F6 | CONFIRMED | The shared task list is the **ordinary todo checklist** and is shareable across sessions **without teams** | `$CC/interactive-mode.md:391,396`; `$CC/env-vars.md:345`; control `zfqrbn_notatoken` → 0 files vs `CLAUDE_CODE_ENABLE_TASKS` → 6 |
| F7 | CONFIRMED | Team hook events are exactly three: `TeammateIdle`, `TaskCreated`, `TaskCompleted` | shape-enumeration of `execute*Hooks` (30) + event enum @90565776; control `TeammateStop`/`TeammateStart`/`TeammateSpawn`/`zzfreshnope` → 0, vs `TeammateIdle` 23 |
| F8 | CONFIRMED | Subagent **frontmatter** hooks do NOT fire on the teammate path | `$CC/sub-agents.md:621,656`; `$CC/agent-teams.md:255,258` |
| F9 | CONFIRMED | `TaskCreate` creates ONE task per call (`subject`, `description`) | binary @115953152 (the harness's own error string) |
| F10 | CONFIRMED | Teams are **already enabled in this repo** via project `settings.json` `env` | `.claude/settings.json`; armed control: `.zshrc` known-token grep → 8, `EXPERIMENTAL_AGENT_TEAMS` in shell startup → 0 |
| F11 | CONFIRMED | Mailbox = a JSON **array** per agent, drained on read, invalid entries pruned, unparseable → treated as empty | binary @246902859, @105623440; live `~/.claude/teams/session-a0684dd5/inboxes/*.json` all `[]` |
| F12 | CONFIRMED | Team config schema (live, this session) incl. `backendType`, `tmuxPaneId`, `subscriptions` | `~/.claude/teams/session-7e75e5ce/config.json` |
| F13 | SUSPECT | The shared task list has **never held a file** on this host | `find ~/.claude/tasks -type f` → 1 (`.DS_Store`) across 58 dirs; control `find ~/.claude/teams -type f` → 13 |
| F14 | REFUTED | "Team directories are cleaned up automatically when the session ends" | `$CC/agent-teams.md:190` vs **8 stale** `~/.claude/teams/session-*/` dirs, oldest 2026-07-16 |
| F15 | CONFIRMED | **Teammates get no worktree isolation.** `isolation: worktree` is subagent-only | `$CC/worktrees.md:68-87`; `worktree` appears in `agent-teams.md` exactly **once** (:440, as the manual alternative); binary shape-scan for any teammate↔worktree token → **0**, control `isolation` → 271 |
| F16 | CONFIRMED | `--teammate-mode` exists but is `.hideHelp()`-suppressed; absent from the 62 `--help` flags | binary @260892578; control `--tmux` → 17, `zzqrfx-nope` → 0 |
| F17 | CONFIRMED | `--name` in `--help` is a **session display name**, unrelated to the Agent tool's teammate `name` | `claude --help` verbatim |
| F18 | CONFIRMED | Agent teams cost **~7×** a standard session (teammates in plan mode) | `$CC/costs.md:246` |
| F19 | CONFIRMED | The only path lever over team/task storage is `CLAUDE_CONFIG_DIR`, which relocates **all** of `~/.claude` | binary @238810955: `sOt(){return join(fn(),"teams")}`, `fn()` ← `process.env.CLAUDE_CONFIG_DIR` |

---

## Q1 — Is the user-scope-only constraint total?

**Mostly yes for the team; no for team POLICY.** The distinction the caller needs is between the
team *instance* (unversionable) and the team *policy* (fully versionable in-repo).

Shape-enumeration of every `CLAUDE_CODE_*` env var in the binary (439 unique) filtered to
`TEAM|TASK|AGENT|WORKTREE|MAILBOX|INBOX` yields **26**, of which only four are team/task related:

```
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
CLAUDE_CODE_TASK_LIST_ID
CLAUDE_CODE_TEAM_TEARDOWN_PARK_TIMEOUT_MS
CLAUDE_CODE_TEAMMATE_COMMAND
```

**None of them redirects the teams path.** The path is hardcoded relative to the config dir:

```js
// binary @238810955
function fn(){ ... process.env.CLAUDE_CONFIG_DIR ... }
function sOt(){ return ESe.join(fn(), "teams") }
// binary @246204753
function sK(e){ return Pbr.join(fn(), "tasks", $4e(e)) }
```

So the single redirect is `CLAUDE_CONFIG_DIR` — which moves settings, history, agents, plugins and
credentials along with it. Not a project-scoping route; a whole-profile relocation.

And the docs close the symlink/pre-authoring door explicitly:

- `$CC/agent-teams.md:243` — "There is no project-level equivalent of the team config. A file like
  `.claude/teams/teams.json` in your project directory is not recognized as configuration; Claude
  treats it as an ordinary file."
- `$CC/agent-teams.md:237` — "The team config holds runtime state such as session IDs and tmux pane
  IDs, so don't edit it by hand or pre-author it: your changes are overwritten on the next state
  update."
- `$CC/agent-teams.md:424` — "**One team per session**: a session has exactly one team, scoped to
  that session. You can't create additional named teams or share a team across sessions."

**But five things ARE version-controllable in `.claude/`, and they are proven to work here:**

| Versionable in-repo | Where | Proof |
|---|---|---|
| Team enablement | `.claude/settings.json` → `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | F10 — armed: it is set in this session and appears in **no** shell startup file |
| Shared task-list identity | `.claude/settings.json` → `env.CLAUDE_CODE_TASK_LIST_ID` | F6 + F4 — env is read first in `u8()`, before the team name |
| Display + default model | `.claude/settings.json` → `teammateMode`, `teammateDefaultModel` | `$CC/settings.md:332,363` — neither is marked "user settings only" (contrast `sshConfigs`, `:326`) |
| Teammate **roles** | `.claude/agents/*.md` | `$CC/agent-teams.md:247-255` — `tools` + `model` honored, body appended |
| Team **quality gates** | `.claude/settings.json` → `hooks.TeammateIdle` / `TaskCreated` / `TaskCompleted` | `$CC/hooks.md:2172,2227,2411` |

What stays unversionable: membership, teammate names, the spawn graph, and the topology — i.e.
the DAG the caller actually wants to encode. **The caller's objection stands for the thing that
matters.** You can commit the rules the team plays by; you cannot commit the team.

---

## Q2 — The shared task list, evaluated as cross-session DAG state

### Mechanics

```js
// binary @246204753 — id resolution, sanitization, paths
function u8(){ if(te.CLAUDE_CODE_TASK_LIST_ID) return te.CLAUDE_CODE_TASK_LIST_ID;
               let e=TU(); if(e) return e.teamName;
               return Km()||VBs||Ot(); }
function $4e(e){ return e.replace(/[^a-zA-Z0-9_-]/g,"-") }
function sK(e){ return Pbr.join(fn(),"tasks",$4e(e)) }
function Dbr(e,t){ return Pbr.join(sK(e), `${$4e(t)}.json`) }
```

- **Location**: `~/.claude/tasks/<sanitized-id>/` — a **directory of per-task JSON files**, not one
  list file. Sanitizer maps anything outside `[A-Za-z0-9_-]` to `-`.
- **ID precedence**: `CLAUDE_CODE_TASK_LIST_ID` → team name → session-derived fallback.
- **Not team-gated.** `$CC/interactive-mode.md:391`: "The task list is Claude's to-do checklist".
  `:396`: "To share a task list across sessions, set `CLAUDE_CODE_TASK_LIST_ID` to use a named
  directory in `~/.claude/tasks/`: `CLAUDE_CODE_TASK_LIST_ID=my-project claude`".
  `$CC/env-vars.md:345`: "Set the same ID in multiple Claude Code instances to coordinate on a
  shared task list." **This works with plain sessions and workflow scripts — teams not required.**
- **Tools** (shape-enumerated): `TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList`. `TaskCreate`
  takes `subject` + `description`, one task per call (F9). Distinct from `TodoWrite`, which the
  binary lists as a separate tool.
- **States + DAG**: pending / in_progress / completed, with dependencies.
  `$CC/agent-teams.md:171`: "a pending task with unresolved dependencies cannot be claimed until
  those dependencies are completed." `:228`: completion auto-unblocks dependents.
- **Claiming**: `$CC/agent-teams.md:178` — "Task claiming uses file locking to prevent race
  conditions when multiple teammates try to claim the same task simultaneously." Lead can assign;
  a teammate can self-claim the next unassigned, unblocked task (`:173-176`).
- **Who can create/complete**: any agent. `$CC/hooks.md:2229` — `TaskCompleted` "fires in two
  situations: when **any agent** explicitly marks a task as completed through the TaskUpdate tool,
  or when an agent team teammate finishes its turn with in-progress tasks."
- **Fork behaviour**: tasks are copied into a forked session, *unless* the env override is set
  (binary @259907526: `if(te.CLAUDE_CODE_TASK_LIST_ID||u8()!==r) return;`). With a pinned ID there
  is nothing to copy — the fork already reads the same directory.
- **Survives session end?** Docs say yes: `$CC/agent-teams.md:235` — "The task list directory
  persists locally and is never uploaded, so resumed sessions keep their tasks. Retention is
  governed by the same `cleanupPeriodDays`." (unset in both settings files here).

### Verdict as cross-session DAG state: **the strongest candidate, and the only one that survives —
but F13 is an unresolved warning.**

Observed on this host: **58** task directories, **zero** task files (`find ~/.claude/tasks -type f`
→ 1, a `.DS_Store`). Control arm: `find ~/.claude/teams -type f` → 13, so the probe is not blind.
`session-a0684dd5` really ran five teammates — five inbox files exist — and left no task file.

I cannot separate two explanations from disk alone: (a) `TaskCreate` was never called in any
session here; (b) something clears the directory — the binary @246204753 does contain a loop that
deletes every non-dot `.json` in a task dir. Marked **SUSPECT**, not refuted. Before building on
it, run the one probe that settles it: `CLAUDE_CODE_TASK_LIST_ID=probe-dag claude`, create a task,
exit, and check `~/.claude/tasks/probe-dag/`.

Both the tasks and teams directories for this session were created eagerly at session start
(20:40), before any teammate existed — so directory existence proves nothing about use.

---

## Q3 — The mailbox

```js
// binary @246902859
function A4t(agent, team){
  let r = team || Km() || "default";
  let i = O1o.join(sOt(), $4e(r), "inboxes");
  return O1o.join(i, `${$4e(agent)}.json`);
}
```

- **Format**: one JSON **array** per agent at `~/.claude/teams/{team}/inboxes/{agent}.json`.
  Entries with no `type` are defaulted to `"message"` (binary: `if(s.type===void 0)s.type="message"`).
- **Frame types** (shape-enumerated from the binary @105623440 and the literal sweep):
  `message`, `permission_request`, `permission_response`, `sandbox_permission_request`,
  `sandbox_permission_response`, `shutdown_request`, `shutdown_approved`,
  `team_permission_update`, `mode_set_request`, `plan_approval_request`, `plan_approval_response`,
  `task_notification`, `task_assignment`, `task_reminder`, `teammate_spawned`,
  `teammate_terminated`.
- **Delivery**: push, not poll. `$CC/agent-teams.md:275` — "when teammates send messages, they're
  delivered automatically to recipients. The lead doesn't need to poll for updates." A message also
  **wakes** a teammate mid-retry-backoff (`:402`, v2.1.198+).
- **Malformed entries**: validated on every read; invalid ones are dropped and the file atomically
  rewritten — `[TeammateMailbox] pruned N schema-invalid entries at <path>`. An unparseable file is
  "treated as empty" rather than fatal. `$CC/agent-teams.md:226`: "Before v2.1.207, a single
  malformed mailbox entry caused a repeated error every second and blocked delivery for that
  mailbox until you deleted the file manually." **2.1.222 is past that fix.**
- **Arbitrary peer addressing: YES.** `$CC/agent-teams.md:280` — "The lead assigns every teammate a
  name when it spawns them, and **any teammate can message any other by that name**." No broadcast:
  `:278` "To reach everyone, send one message per recipient."
- **Survives a restart: NO.** Mailboxes are **drained** — all five live inboxes in
  `session-a0684dd5` are `[]` despite that team having run. The file is a queue, not a log; there
  is no message history. And `$CC/agent-teams.md:421` — "`/resume` and `/rewind` do not restore
  in-process teammates. After resuming a session, the lead may attempt to message teammates that no
  longer exist."
- **Priority**: `[inProcessRunner] received shutdown request from … (prioritized over unread
  messages)` — shutdown jumps the queue. Unrecognised frames: `dropping protocol frame from <x>` at
  warn level.
- **Security**: `$CC/agent-teams.md:265` — a `SendMessage` arrival is labelled as coming from
  another Claude session, not from you; a teammate cannot relay consent to bypass a denial, and
  auto-mode's classifier treats a relayed approval claim as untrusted input.

---

## Q4 — Worktrees + teams

**`worktrees.md` is describing subagents and manual parallel sessions. Teammates get nothing.**

- `$CC/worktrees.md:68-87` — "## Isolate subagents with worktrees … make the isolation permanent
  for a custom subagent by adding `isolation: worktree` to its frontmatter." Every sentence in that
  section says *subagent*.
- `$CC/worktrees.md:87` — subagent worktrees branch from the default branch unless
  `worktree.baseRef` is `"head"` (`:105-110`; a branch name is not accepted).
- `$CC/worktrees.md:85` — a subagent worktree is auto-removed if the subagent made no changes; one
  with changes survives until the `cleanupPeriodDays` sweep (`:91`), which skips any worktree
  holding changed/untracked files or unpushed commits.
- **`worktree` occurs exactly ONCE in `agent-teams.md`**, at `:440`, listing worktrees as the
  *manual alternative*: "Manual parallel sessions: Git worktrees let you run multiple Claude Code
  sessions yourself **without automated team coordination**."
- Binary shape-scan for any identifier containing both `teammate` and `worktree` (either order) →
  **0 hits**. Control: `isolation` → 271. The probe discriminates.

**What isolates two teammates editing the same file: nothing but instructions.**
`$CC/agent-teams.md:370` — "Two teammates editing the same file leads to overwrites. Break the work
so each teammate owns a different set of files." That is the entire mechanism. Contrast a subagent,
where `isolation: worktree` is a real filesystem boundary.

`WorktreeCreate`/`WorktreeRemove` hooks do exist (`executeWorktreeCreateHook`,
`executeWorktreeRemoveHook`) but they are for non-git VCS backends (`$CC/worktrees.md:215`), not
team coordination.

---

## Q5 — Teammate lifecycle

- **Spawn**: no setup step since v2.1.178 — the team forms when the first teammate is spawned
  (`$CC/agent-teams.md:206`). Two routes: you ask, or Claude proposes and you confirm (`:208-211`).
  A teammate is a **separate Claude Code instance**, launched via `CLAUDE_CODE_TEAMMATE_COMMAND`
  (binary @242610163, default `"claude"`; the same block carries `the="claude-swarm"`,
  `Fm="team-lead"`, `fdr="swarm-view"`).
- **Name**: validated against `/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/` (binary @242610163) — byte-for-byte
  the Agent tool's documented `name` pattern. This is the mechanism behind "`name` makes a teammate".
- **Model**: **not inherited by default.** `$CC/agent-teams.md:141` — "Teammates don't inherit the
  lead's `/model` selection by default. To change the model used when the prompt doesn't specify
  one, set **Default teammate model** in `/config`." Backed by `teammateDefaultModel`
  (`$CC/settings.md:363`: a model alias, or `null` to inherit the lead's current `/model`).
  Currently **unset** in both settings files here.
- **Effort: inherited.** `$CC/agent-teams.md:143` — "Teammates inherit the lead's effort level. In
  split-pane mode this applies from v2.1.186." `/effort` still applies to a viewed teammate's later
  turns; `/model` and `/fast` are fixed at spawn and only change the lead (`:167`).
- **Permissions**: start as the lead's, including `--dangerously-skip-permissions`; per-teammate
  modes cannot be set at spawn, only changed after (`:263`, `:428`). Prompts surface in the lead
  session.
- **Mode**: `teammateMode` ∈ `in-process` (default since v2.1.179) | `auto` | `tmux` | `iterm2`.
  Per-session override `--teammate-mode`, which exists in the binary but is `.hideHelp()`-suppressed
  and absent from the 62 flags `--help` prints (F16).
- **Shutdown**: the lead sends a `shutdown_request`; the teammate may approve or reject with an
  explanation (`:188`). Shutdown is prioritised over unread messages. It is slow by design —
  `:423` "teammates finish their current request or tool call before shutting down".
  `CLAUDE_CODE_TEAM_TEARDOWN_PARK_TIMEOUT_MS` bounds teardown parking.
- **What kills a teammate's background tasks**: they cannot exist. `$CC/agent-teams.md:426` — "**No
  background subagents from in-process teammates**: an in-process teammate's own subagents run in
  the foreground. Asking for a background one, whether with `run_in_background` or a subagent
  definition that sets `background: true`, returns an error, **because a teammate's background work
  can't outlive the lead's process**." Also `:425`: no nested teams — a teammate cannot spawn
  teammates. And `:427`: the lead is fixed for the session's lifetime.
- **Failure surfacing**: since v2.1.198 a teammate whose turn ends on an API error notifies the lead
  with the error text instead of appearing to finish normally (`:276`).

---

## Q6 — Which hooks fire on the teammate path

**Enumerated by shape**, not by expected list. `grep -oE 'execute[A-Za-z]+Hooks?\b'` over the
binary strings yields 30 dispatchers; the event enum at byte 90565776 reads:

```
PermissionDenied, Notification, UserPromptSubmit, UserPromptExpansion, SessionStart, SessionEnd,
Stop, StopFailure, SubagentStart, SubagentStop, PreCompact, PostCompact, PermissionRequest, Setup,
TeammateIdle, TaskCreated, TaskCompleted, Elicitation, ElicitationResult, ConfigChange,
InstructionsLoaded, CwdChanged, FileChanged, DirectoryAdded, MessageDisplay
```
plus `executeWorktreeCreateHook` / `executeWorktreeRemoveHook`.

**Team-related events: exactly three.** Control arm on invented siblings —
`TeammateStop` 0, `TeammateStart` 0, `TeammateSpawn` 0, `zzfreshnope` 0, against
`TeammateIdle` 23, `TaskCreated` 20, `TaskCompleted` 27. The list in the brief was complete.

| Event | Fires | Block semantics |
|---|---|---|
| `TeammateIdle` | a teammate is about to go idle after finishing its turn (`$CC/hooks.md:2413`) | exit 2 → stderr fed back, teammate **keeps working**; `{"continue":false,"stopReason":…}` stops it entirely (`:2440-2443`) |
| `TaskCreated` | a task is being created via `TaskCreate` (`:51`) | exit 2 → task not created, rolled back (`:787`, `:2176`) |
| `TaskCompleted` | any agent marks a task complete via `TaskUpdate`, **or** a teammate ends its turn with in-progress tasks (`:2229`) | exit 2 → completion prevented (`:788`) |

- None of the three supports matchers; a `matcher` field is silently ignored (`$CC/hooks.md:316,340`).
- Payloads: `TeammateIdle` gets `teammate_name` + `team_name` (`:2419`); the two task events get
  `task_id`, `task_subject`, optionally `task_description`, `teammate_name`, `team_name`
  (`:2180`, `:2235`). `team_name` is the session-derived name and is **deprecated**
  (`$CC/agent-teams.md:18`).
- All three support all five hook types incl. `prompt` and `agent` (`$CC/hooks.md:2960-2972`).
- `continueOnBlock` nuance (`:3055-3057`): `TeammateIdle` **stops the teammate by default**; set
  `continueOnBlock: true` to feed the reason back and keep it working.

### The prior probe: **CONFIRMED, not refuted**

A frontmatter `SubagentStop` hook fires for a subagent and never on the named-teammate path:

- `$CC/sub-agents.md:621` — "Frontmatter hooks fire when the agent is spawned **as a subagent
  through the Agent tool or an @-mention**, and when the agent runs as the **main session** via
  `--agent` or the `agent` setting." A teammate is neither.
- `$CC/sub-agents.md:656` — "When the agent is invoked as a subagent, `Stop` hooks in frontmatter
  are automatically converted to `SubagentStop` events." That conversion is on the subagent path.
- `$CC/agent-teams.md:255` — as a teammate, a subagent definition contributes only its `tools`
  allowlist and `model`, with the body appended to the system prompt. `:258` — `skills` and
  `mcpServers` are explicitly dropped. `hooks` is not listed as honored anywhere.
- Structural corroboration: there is **no `executeSubagentStopHooks`**; `SubagentStop` rides the
  `Stop` dispatcher (byte-scan @102342592 shows `hookEvent`/`Stop`/`SubagentStop` adjacent in one
  table) — a teammate's turn ending is a `TeammateIdle`, not a `Stop`.

**Consequence for the caller: a teammate carries no per-agent hooks.** Every gate on the teammate
path must live in `settings.json`, which is session-wide. That is a real loss of per-role
enforcement relative to a subagent definition.

---

## Ledger entries to append

- **Agent teams are OFF by default and ON in this repo.** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
  sits in BOTH `.claude/settings.json` and `~/.claude/settings.json`. Armed: it appears in no shell
  startup file. This is why `name:` on the Agent tool produced teammate behaviour.
- **`name` on the Agent tool is validated by `/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/`** — the
  teammate-name regex from the swarm module. `claude --name` in `--help` is something else
  entirely (a session display name); do not conflate them.
- **The shared task list is NOT a team feature.** It is the ordinary todo checklist, and
  `CLAUDE_CODE_TASK_LIST_ID` shares one directory across sessions with **no team involved**. This
  is the one piece of team machinery a workflow script can use directly.
- **A teammate gets ZERO worktree isolation.** `isolation: worktree` is subagent-only; the binary
  has no teammate↔worktree identifier at all (control `isolation` → 271). Two teammates on one file
  overwrite each other, and the only defence is the spawn prompt.
- **Frontmatter hooks do not run on the teammate path** — only `settings.json` `TeammateIdle` /
  `TaskCreated` / `TaskCompleted`, none of which support matchers. Per-role enforcement is lost.
- **Mailboxes are DRAINED queues, not logs.** Every live inbox on this host is `[]`. Nothing about
  inter-agent communication survives a restart, and `/resume` does not restore in-process teammates.
- **`~/.claude/teams/` is not reliably cleaned up** despite the doc's claim — 8 stale dirs here,
  oldest three weeks old. Do not treat directory absence as "session ended cleanly".
- **Teams cost ~7×** a standard session (`$CC/costs.md:246`), and teammates do **not** inherit the
  lead's model by default (they do inherit effort).
- ⚠️ **58 task dirs, 0 task files** on this host — the DAG substrate has never been observed to
  hold state here. Settle with `CLAUDE_CODE_TASK_LIST_ID=probe-dag claude` before designing on it.

---

## The honest trade-off

| Dimension | Agent team | Workflow script (+ subagents) |
|---|---|---|
| **Version-controlled definition** | ❌ team instance is runtime state under `~/.claude/teams/`, session-derived name, overwritten on update, explicitly not project-scopable (`agent-teams.md:243`) | ✅ the script IS the repo |
| **Version-controlled policy** | ✅ enablement, `teammateMode`, `teammateDefaultModel`, roles in `.claude/agents/`, the 3 hooks — all in `.claude/` | ✅ same, plus everything else |
| **Cross-session durable state** | ⚠️ task list only, and it is not team-exclusive — see next row. Mailboxes drain; `/resume` does not restore teammates | ✅ any file you choose, with your own schema and your own locking |
| **Shared task list w/ dependency DAG + file-locked claiming** | ✅ built in | ✅ **also available** — `CLAUDE_CODE_TASK_LIST_ID` needs no team (F6). This is not a team advantage |
| **Peer-to-peer agent messaging** | ✅ genuinely unique; any teammate → any teammate by name, push-delivered, wakes a backing-off peer | ❌ subagents report to the caller only |
| **Adversarial debate / cross-challenge** | ✅ the one workload that needs peer messaging (`agent-teams.md:304-317`) | ❌ requires the parent to relay every exchange |
| **Human can steer one worker mid-flight** | ✅ arrow-keys + Enter into a teammate's transcript, or its own tmux pane | ⚠️ `SendMessage` to a running agent; no transcript view |
| **File-conflict isolation** | ❌ **nothing** — prompt discipline only (`agent-teams.md:370`) | ✅ `isolation: worktree` per subagent, with `worktree.baseRef` |
| **Per-role hooks** | ❌ frontmatter hooks dropped; only session-wide, matcher-less events | ✅ full frontmatter `hooks:` incl. `PreToolUse` matchers and `Stop`→`SubagentStop` |
| **Per-role skills / MCP** | ❌ `skills` and `mcpServers` explicitly dropped (`:258`) | ✅ both honored |
| **Background / long-running work** | ❌ in-process teammates cannot run background subagents at all (`:426`) | ✅ `background: true`, `run_in_background` |
| **Nesting** | ❌ no nested teams (`:425`) | ✅ subagents can fan out (`MAX_SUBAGENT_SPAWN_DEPTH`) |
| **Determinism / replay** | ❌ lead decides autonomously; "lead shuts down before work is done" is a documented failure mode (`:404`) | ✅ the script decides |
| **Token cost** | ❌ ~7× (`costs.md:246`) | ✅ bounded by what you launch |
| **Stability** | ❌ experimental, off by default, 9 documented limitations | ✅ no feature flag |

### Was choosing workflows over teams right?

**Yes — and the strongest reason is not the one the caller gave.**

The stated objection (a team cannot be versioned) is **correct but narrower than it looks**: the
team *policy* is perfectly versionable in `.claude/`. The reasons that actually decide it:

1. **The caller's best candidate for teams — the shared task list — is not a team feature.**
   `CLAUDE_CODE_TASK_LIST_ID` in `.claude/settings.json` gives a workflow script the same
   dependency-aware, file-locked, cross-session task DAG with no team, no 7× cost, and no
   experimental flag. Teams do not have to be adopted to get it. (Settle F13 first.)
2. **Teams *lose* capabilities a subagent has**: worktree isolation, frontmatter hooks, per-role
   skills and MCP, background execution, nesting. For a repo whose entire discipline is
   machine-enforced gates, dropping per-role hooks is a direct regression.
3. **Nothing durable survives** — mailboxes drain, `/resume` doesn't restore teammates, and
   `~/.claude/teams/` isn't even reliably cleaned up.

**The one thing teams give that nothing else does is peer-to-peer messaging** — a teammate
challenging another teammate's finding without the lead relaying it. If the caller ever wants the
adversarial-debate pattern (`agent-teams.md:304-317`, the competing-hypotheses investigation), that
is the workload to spend a team on. For everything else — a versionable, gated, resumable DAG —
workflows plus `CLAUDE_CODE_TASK_LIST_ID` dominate.

---

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the 2.1.222 binary and
  `claude --help` flag surface were the primary existence corpus.
- [mkusaka/it2](https://github.com/mkusaka/it2) — named by `$CC/agent-teams.md:109,127` as the CLI
  required for `teammateMode: "iterm2"` split panes; not fetched, only enumerated.
- [tmux/tmux](https://github.com/tmux/tmux) — named by `$CC/agent-teams.md:127-129` as the
  split-pane backend; not fetched, only enumerated.
