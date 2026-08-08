# Symphony and its ports — orchestration model and harness deltas

**Agent:** symphony-and-ports research delegation
**Measured:** 2026-08-04 (all GitHub metadata read via `gh api` at 2026-08-04T21:42Z unless stated otherwise)
**Question:** What is symphony's orchestration model, and what did each port have to change to run on a different harness?

> STATUS: complete.

**Headline:** symphony has **no role taxonomy** — it is one Codex agent per ticket, and its "roles" are tracker states plus on-demand skill files (control-armed in §1.0). Two of the four ports added one: **stokowski** as pipeline stage prompts with human gates, **itervox** as file-backed `SOUL.md` + `INSTRUCTIONS.md` profiles. **None of the four uses Claude Code's native multi-agent primitives** (§3.1) — every one drives Claude Code as a headless single-agent subprocess and reimplements coordination in its host language.

## Repo metadata snapshot (2026-08-04T21:42Z, `gh api repos/<o>/<r>`)

| Repo | Stars | Forks | Open issues | Created | Last push | License |
|---|---|---|---|---|---|---|
| openai/symphony | 26,429 | 2,675 | 9 | 2026-02-26 | 2026-07-24T17:56:45Z | Apache-2.0 |
| Sugar-Coffee/stokowski | 112 | 26 | 6 | 2026-03-07 | 2026-06-23T16:10:29Z | Apache-2.0 |
| mksglu/hatice | 154 | 27 | 6 | 2026-03-06 | 2026-05-15T20:24:38Z | MIT |
| manav03panchal/phonyhuman | 3 | 1 | 0 | 2026-03-06 | 2026-03-16T04:35:29Z | Apache-2.0 |
| vnovick/itervox | 38 | 9 | 11 | 2026-03-18 | 2026-07-06T14:29:59Z | NOASSERTION |

## 1. openai/symphony

**Source read:** shallow clone at commit `f8e8b8a670c799f6e0ade7a8c25c4bf4a4a56ec7` (2026-07-24 10:56:43 -0700), 130 tracked blobs. Citations below are `path:line` in that tree; the same paths resolve at `https://github.com/openai/symphony/blob/main/<path>`.

### 1.0 The headline finding: symphony has NO role taxonomy

**Symphony is not a multi-role agent team.** It is a *single-agent-per-ticket daemon*. There is exactly one agent identity — a Codex app-server session — and everything the brief calls a "role" is either (a) a **tracker state**, or (b) a **skill file** the one agent opens on demand.

Control-armed absence probe (2026-08-04, in the clone root):

```
grep -rniEc 'role|persona|planner|architect|sub-?agent|multi-agent' SPEC.md README.md elixir/WORKFLOW.md
  → SPEC.md:0   README.md:0   elixir/WORKFLOW.md:0
grep -rniEc 'orchestrator|workspace' SPEC.md README.md elixir/WORKFLOW.md   # CONTROL
  → SPEC.md:202 README.md:0   elixir/WORKFLOW.md:7
```

The control term returns 202 hits in the same file with the same command shape, so the probe discriminates; the 0 is a real negative. Repo-wide, the only `persona` hits are `.codex/skills/land/SKILL.md:78,132,143`, which refer to **OpenAI's cloud Codex Review personas** posting `## Codex Review — <persona>` comments on the PR — an *external* reviewer symphony reads, not a role it defines. The only `subagent` hit is `elixir/README.md:390`, describing the Elixir observability dashboard showing "actively running subagents" (i.e. Codex's own internal subagents, below symphony's abstraction).

This matters for the design question: **any role taxonomy in a Claude Code agent team is an addition to symphony, not a port of it.**

### 1.1 What symphony actually is

> "Symphony is a long-running automation service that continuously reads work from a configured issue tracker, creates an isolated workspace for each issue, and runs a coding agent session for that issue inside the workspace." — `SPEC.md:18-20`

> "Symphony is a scheduler/runner and tracker reader." — `SPEC.md:38`

The repo ships two things:

1. **`SPEC.md`** (2,311 lines) — a language-agnostic, RFC-2119 normative specification. `README.md:21-26` explicitly invites you to hand the spec URL to a coding agent and have it build its own implementation ("Option 1. Make your own"). **The spec is the artifact; the code is a reference.**
2. **`elixir/`** — "our experimental reference implementation" (`README.md:28`), an OTP app (~10k lines) with a Phoenix LiveView dashboard.

Marked "a low-key engineering preview for testing in trusted environments" (`README.md:10-11`).

### 1.2 Role taxonomy — the honest enumeration

Since there are no agent roles, here is what occupies the same slot in the design. Three separate axes, none of which is "a team of agents":

**(a) Components** (`SPEC.md:73-116`) — software modules, not agents:

| Component | Stated responsibility (verbatim, condensed) | Cite |
|---|---|---|
| `Workflow Loader` | Reads `WORKFLOW.md`; parses YAML front matter and prompt body; returns `{config, prompt_template}` | `SPEC.md:75-78` |
| `Config Layer` | Typed getters for workflow config; defaults + env-var indirection; validation used before dispatch | `SPEC.md:80-83` |
| `Issue Tracker Adapter` | Fetches candidate issues in active states; fetches states by ID; fetches terminal-state issues at startup; normalizes payloads; MAY expose provider-native agent tools | `SPEC.md:85-91` |
| `Orchestrator` | Owns the poll tick; owns in-memory runtime state; decides dispatch/retry/stop/release; tracks metrics + retry queue | `SPEC.md:93-97` |
| `Workspace Manager` | Maps issue IDs to workspace paths; ensures directories; runs lifecycle hooks; cleans terminal workspaces | `SPEC.md:99-103` |
| `Agent Runner` | Creates workspace; builds prompt; launches coding-agent app-server client; streams updates back | `SPEC.md:105-109` |
| `Status Surface` (OPTIONAL) | Human-readable runtime status | `SPEC.md:111-112` |
| `Logging` | Structured runtime logs to configured sinks | `SPEC.md:114-115` |

**(b) Tracker states** (`elixir/WORKFLOW.md:107-116`) — the closest thing to "phases of work", and they live in Linear, not in code:

| State | Meaning (verbatim) |
|---|---|
| `Backlog` | "out of scope for this workflow; do not modify" |
| `Todo` | "queued; immediately transition to `In Progress` before active work" |
| `In Progress` | "implementation actively underway" |
| `Human Review` | "PR is attached and validated; waiting on human approval" |
| `Merging` | "approved by human; execute the `land` skill flow (do not call `gh pr merge` directly)" |
| `Rework` | "reviewer requested changes; planning + implementation required" |
| `Done` | "terminal state; no further action required" |

**(c) Codex skills** (`.codex/skills/*/SKILL.md`) — capability modules the one agent loads, name + verbatim description:

| Skill | Description (frontmatter, verbatim) | Lines |
|---|---|---|
| `commit` | "Create a well-formed git commit from current changes using session history for rationale and summary; use when asked to commit, prepare a commit message, or finalize staged work." | 75 |
| `debug` | "Investigate stuck runs and execution failures by tracing Symphony and Codex logs with issue/session identifiers; use when runs stall, retry repeatedly, or fail unexpectedly." | 118 |
| `land` | "Land a PR by monitoring conflicts, resolving them, waiting for checks, and squash-merging when green; use when asked to land, merge, or shepherd a PR to completion." | 225 |
| `linear` | "Use Symphony's `linear_graphql` client tool for raw Linear GraphQL operations such as comment editing and upload flows." | 388 |
| `pull` | "Pull latest origin/main into the current local branch and resolve merge conflicts (aka update-branch)… merge-based update (not rebase)…" | 100 |
| `push` | "Push current branch changes to origin and create or update the corresponding pull request…" | 117 |
| `release` | "Cut a Symphony release by bumping the committed version, landing it, tagging the merged commit, and verifying the Burrito release workflow." | 28 |

These are Codex-format `SKILL.md` files — structurally identical to Claude Code skills (frontmatter `name` + `description`, markdown body). `elixir/WORKFLOW.md:99-105` lists five of them under "## Related skills" as the workflow's declared capability surface.

### 1.3 Coordination model

- **Who assigns work:** the orchestrator alone. "The orchestrator is the only component that mutates scheduling state. All worker outcomes are reported back to it and converted into explicit state transitions." (`SPEC.md:637-638`). "The orchestrator serializes state mutations through one authority to avoid duplicate dispatch." (`SPEC.md:727`)
- **How tasks are represented:** a normalized `Issue` record (`SPEC.md:156-197`) — `id`, `native_ref`, `identifier`, `title`, `description`, `priority`, `state`, `branch_name`, `url`, `assignee_id`, `labels`, `blocked_by`, `dispatchable`, `created_at`, `updated_at`. The unit of work is **one tracker ticket**, full stop.
- **Is there a DAG?** **No.** There is no dependency graph and no task decomposition. `blocked_by` exists on the Issue (`SPEC.md:188-193`) but is explicitly *"Best-effort provider metadata"*, and the orchestrator is forbidden from acting on it: "The orchestrator MUST NOT … branch on provider-specific blocker, board, transition, or comment semantics." (`SPEC.md:1242-1243`). Blocker semantics are pushed into the adapter's boolean `dispatchable` flag (`SPEC.md:1279-1280`). Parallelism is across *independent tickets*, never across subtasks of one ticket.
- **Dispatch order** is a flat priority sort, not a topological one (`SPEC.md:771-776`): `priority` ascending for 1..4 (others and null after), then `created_at` oldest first, then `identifier` lexicographic.
- **How parallelism is bounded** — three independent caps:
  - `agent.max_concurrent_agents` (default `10`), global: `available_slots = max(max_concurrent_agents - running_count, 0)` (`SPEC.md:448-450`, `781`).
  - `agent.max_concurrent_agents_by_state` — a per-tracker-state map, default empty, falling back to the global limit (`SPEC.md:458-461`, `783-786`). This is the interesting one: it lets you say "at most 2 tickets in `Merging` at once".
  - `worker.max_concurrent_agents_per_host` in the OPTIONAL SSH extension (`SPEC.md:2258-2259`).
  - Turn-level: `agent.max_turns` (default `20`) caps coding-agent turns inside one worker session (`SPEC.md:451-453`).
- **Poll tick sequence** (`SPEC.md:742-749`): reconcile running issues → dispatch preflight validation → fetch candidates by active states → sort → dispatch while slots remain → notify observability. Default `polling.interval_ms` = `30000` (`SPEC.md:406-407`); the reference `WORKFLOW.md` sets `5000` (`elixir/WORKFLOW.md:18-19`).

### 1.4 State and handoff

- **Intermediate results live in two places, and neither is a message bus:**
  1. **The filesystem workspace** — `<workspace.root>/<workspace_key>`, one per issue, "reused across runs for the same issue. Successful runs do not auto-delete workspaces." (`SPEC.md:863-866`). This is the durable artifact between attempts.
  2. **A single persistent tracker comment**, the "workpad". `elixir/WORKFLOW.md:86` — "Treat a single persistent Linear comment as the source of truth for progress." Marker header `## Codex Workpad`, exactly one per issue (`elixir/WORKFLOW.md:281`), with a mandated template: `Plan` / `Acceptance Criteria` / `Validation` / `Notes` / `Confusions` (`elixir/WORKFLOW.md:299-329`), stamped with `<hostname>:<abs-path>@<short-sha>` (`elixir/WORKFLOW.md:154-157`).
- **What an agent hands to "the next one":** nothing directly — there is no next agent. Handoff is **to a tracker state**, and the receiving party is either the same workflow on a later tick or a human. "A successful run can end at a workflow-defined handoff state (for example `Human Review`), not necessarily `Done`." (`SPEC.md:43-44`)
- **Orchestrator runtime state** is in-memory only (`SPEC.md:280-293`): `running` map, `claimed` set, `retry_attempts` map, `completed` set, token totals, rate limits. Deliberately no database: "Support tracker/filesystem-driven restart recovery without requiring a persistent database; exact in-memory scheduler state is not restored." (`SPEC.md:57-58`). Persisting the retry queue is listed as a **TODO** at `SPEC.md:2238`.
- **Claim states** (internal, distinct from tracker states) — `Unclaimed`, `Claimed`, `Running`, `RetryQueued`, `Released` (`SPEC.md:645-660`).
- **Run-attempt lifecycle** (`SPEC.md:680-690`): `PreparingWorkspace` → `BuildingPrompt` → `LaunchingAgentProcess` → `InitializingSession` → `StreamingTurn` → `Finishing` → then one of `Succeeded` / `Failed` / `TimedOut` / `Stalled` / `CanceledByReconciliation`. "Distinct terminal reasons are important because retry logic and logs differ." (`SPEC.md:692`)
- **Failure/retry:**
  - Normal continuation after a clean exit: fixed `1000 ms` delay (`SPEC.md:799`). Symphony re-dispatches even on success, because success ≠ done.
  - Failure-driven: `delay = min(10000 * 2^(attempt - 1), agent.max_retry_backoff_ms)`, cap default `300000` ms / 5 min (`SPEC.md:800-801`, `455-457`).
  - Retry handling refreshes the specific issue by ID first, and releases the claim if it vanished, went terminal, or became unroutable (`SPEC.md:805-812`).
  - **Stall detection**: if `elapsed_ms` since the last agent event exceeds `codex.stall_timeout_ms` (default 5 min), kill the worker and queue a retry; `<= 0` disables it (`SPEC.md:825-829`, `489-491`).
  - **Reconciliation runs every tick, before dispatch** (`SPEC.md:729`, `819-839`): terminal tracker state → terminate worker *and* clean workspace; still-active-and-routable → refresh the in-memory snapshot; active-but-unroutable, or neither active nor terminal → terminate *without* cleanup. A state-refresh failure keeps workers running and retries next tick.
  - `Rework` is a **full reset, not a patch**: close the PR, delete the workpad comment, branch fresh from `origin/main`, re-plan end to end (`elixir/WORKFLOW.md:253-263`).

### 1.5 Per-agent configuration — everything is per-*workflow*, nothing is per-role

All tunables live in the YAML front matter of a single repo-owned `WORKFLOW.md` (`SPEC.md:605-633`). There is exactly one such block per service, so **there is no per-role model, effort, or tool-access knob** — the notion doesn't exist. The full surface:

| Key | Default | What it tunes |
|---|---|---|
| `tracker.kind` | REQUIRED | which adapter (`linear`, `github`, `gitlab`, `jira`, `asana` in the Elixir impl) |
| `tracker.provider` | `{}` | adapter-owned endpoint/scope/auth, `$VAR` refs |
| `tracker.required_labels` | `[]` | every label must be present to dispatch |
| `tracker.active_states` / `terminal_states` | adapter-defined | which tracker states are dispatchable / terminal |
| `polling.interval_ms` | `30000` | tick cadence |
| `workspace.root` | `<system-temp>/symphony_workspaces` | where per-issue dirs live |
| `hooks.after_create` / `before_run` / `after_run` / `before_remove` | none | shell scripts, cwd = workspace |
| `hooks.timeout_ms` | `60000` | applies to all hooks |
| `agent.max_concurrent_agents` | `10` | global parallelism |
| `agent.max_turns` | `20` | turns per worker session |
| `agent.max_retry_backoff_ms` | `300000` | backoff cap |
| `agent.max_concurrent_agents_by_state` | `{}` | **per-tracker-state parallelism cap** |
| `codex.command` | `codex app-server` | the launched process, via `bash -lc` |
| `codex.approval_policy` | impl-defined | Codex `AskForApproval` pass-through |
| `codex.thread_sandbox` | impl-defined | Codex `SandboxMode` pass-through |
| `codex.turn_sandbox_policy` | impl-defined | Codex `SandboxPolicy` pass-through |
| `codex.turn_timeout_ms` | `3600000` | max silence while a turn streams |
| `codex.read_timeout_ms` | `5000` | startup/sync request timeout |
| `codex.stall_timeout_ms` | `300000` | orchestrator-side inactivity kill |

Model and reasoning effort are **not first-class fields** — they ride inside `codex.command` as CLI flags. The reference workflow (`elixir/WORKFLOW.md:33-34`):

```
codex: command: codex --config shell_environment_policy.inherit=all --config 'model="gpt-5.5"' --config model_reasoning_effort=xhigh app-server
```

with `approval_policy: never`, `thread_sandbox: workspace-write`, `turn_sandbox_policy: {type: workspaceWrite, networkAccess: true}` (`elixir/WORKFLOW.md:35-39`).

**Isolation** is the one thing that *is* strongly specified, as three hard invariants (`SPEC.md:928-948`): agent cwd MUST equal the workspace path; the workspace path MUST stay under the workspace root (prefix check on normalized absolute paths); the workspace key MUST be sanitized to `[A-Za-z0-9._-]` with a ≥64-bit hash suffix appended when sanitization changes the identifier, so distinct identifiers can't collide. `SPEC.md:930` calls this "the most important portability constraint."

**Dynamic reload is REQUIRED** (`SPEC.md:562-578`): the service MUST watch `WORKFLOW.md`, re-read and re-apply config *and prompt* without restart, and MUST NOT crash on an invalid reload — it keeps the last known good config and emits an operator-visible error. In-flight sessions need not restart. A workflow reload MUST NOT make an in-flight session "advertise one provider and execute another" (`SPEC.md:1096-1098`).

### 1.6 Self-improvement: absent

Control-armed probe (2026-08-04):

```
grep -rniEc 'self-improv|self improv|evolve|revise the prompt|learn from|feedback loop|eval' SPEC.md  → 2
grep -rniEc 'retry' SPEC.md   # CONTROL                                                             → 75
```

Both of the 2 hits are substring false positives — `SPEC.md:1202` "revalidation" and `SPEC.md:1777` "evaluate their own risk profile". There is **no loop in which symphony revises its own agents or prompts based on outcomes.** The only prompt-mutation channel is a human editing `WORKFLOW.md`, which hot-reloads (§1.5). `SPEC.md:2238-2242` lists three TODOs, none of them self-improvement.

The nearest thing is a **within-ticket** learning artifact: the workpad's mandated `### Confusions` section — "Add a short `### Confusions` section at the bottom when any part of task execution was unclear/confusing" (`elixir/WORKFLOW.md:228`, template at `:326-328`). That is a signal *for humans* to go improve the workflow; nothing consumes it automatically.

### 1.7 Human checkpoints

Symphony is designed to run unattended in the middle and require a human at exactly **two** points:

1. **`Backlog` → `Todo`** (entry). "`Backlog` -> do not modify issue content/state; stop and wait for human to move it to `Todo`." (`elixir/WORKFLOW.md:124`, guardrail at `:279`)
2. **`Human Review` → `Merging`** (approval). "When the issue is in `Human Review`, do not code or change ticket content… If approved, human moves the issue to `Merging`." (`elixir/WORKFLOW.md:246-249`). The agent polls in this state; it does not act.

Everything else is explicitly unattended: "This is an unattended orchestration session. Do not ask a human to perform follow-up actions." (`elixir/WORKFLOW.md:69`). "Final message must report completed actions and blockers only. Do not include 'next steps for user'." (`:71`).

The escape hatch is narrow and deliberately asymmetric (`elixir/WORKFLOW.md:187-197`): a missing non-GitHub tool or auth moves the ticket to `Human Review` with a blocker brief — but **"GitHub is *not* a valid blocker by default"**, and the agent must exhaust fallback auth strategies and document them first.

At the protocol layer, `SPEC.md:1073-1075` makes the anti-stall rule normative: "Approval requests and user-input-required events MUST NOT leave a run stalled indefinitely." The documented high-trust posture (`SPEC.md:1077-1081`) auto-approves command execution and file changes for the session and treats user-input-required as a **hard failure** — i.e. in the reference posture, an agent that asks a question dies rather than waits.

Operator intervention points are enumerated at `SPEC.md:1707-1717`: edit `WORKFLOW.md` (hot-reloaded), or change the tracker state (terminal stops + cleans, non-active stops without cleanup). Restart is explicitly *not* the normal path for applying config.

### 1.8 Two more design choices worth carrying

- **Tracker writes are the agent's job, not the orchestrator's.** `SPEC.md:1309-1319`: symphony ships no comment/state CRUD. It executes *provider-native tools* host-side with its own credential and hands the child the results — so the coding agent never sees a raw tracker token (`SPEC.md:1107-1111`, `15.3` at `:1747-1755`). The adapter hook surface is three functions: `agent_tool_specs()`, `secret_environment_names()`, `execute_agent_tool(name, arguments, context={issue})` (`SPEC.md:1124-1126`).
- **Prompt rendering is strict.** Liquid-compatible semantics; "Unknown variables MUST fail rendering. Unknown filters MUST fail rendering." (`SPEC.md:499-501`). Template inputs are exactly `issue` and `attempt` (`SPEC.md:503-509`). A render failure fails only that attempt; a workflow *file* error blocks all new dispatch (`SPEC.md:528-532`).
- **Distribution, when it happens, is by host — not by role.** Appendix A (`SPEC.md:2251-2311`) keeps one central orchestrator and pushes worker runs to `worker.ssh_hosts` over SSH stdio. Continuation turns SHOULD stay on the same host; workspaces are host-local so moving hosts is a cold restart; and "Once a run has already produced side effects, a transparent rerun on another host SHOULD be treated as a new attempt, not as invisible failover."

## 2. Ports

### 2.1 Sugar-Coffee/stokowski — Python + Claude Code/Codex, **the only port with a role taxonomy**

**Measured 2026-08-04:** 112 stars, 26 forks, 6 open issues, Apache-2.0, created 2026-03-07, last push 2026-06-23T16:10:29Z. Clone at `6e51bdf26c8cf6206893beb7c01b71297539469d` (2026-06-23 17:09:04 +0100), 30 tracked blobs, ~6,300 lines of Python.

**Harness targeted:** the **Claude Code CLI** (`claude -p --output-format stream-json`) *and* the Codex CLI (`codex --quiet`), selectable per pipeline stage. Named for the conductor Leopold Stokowski (`README.md:15`).

Self-description: *"Built on OpenAI's Symphony spec and taken further — with configurable state machines, gate-based human review, multi-runner support, and a live web dashboard."* (`README.md:7`)

#### The protocol mapping it publishes

`README.md:139-147` gives the port's own translation table, which is the single most useful artifact in this whole survey:

| Symphony | Stokowski |
|---|---|
| `codex app-server` JSON-RPC | `claude -p --output-format stream-json` or `codex --quiet` |
| `thread/start` → thread_id | First turn → `session_id` |
| `turn/start` on thread | `claude -p --resume <session_id>` |
| `approval_policy: never` | `--dangerously-skip-permissions` |
| `thread_sandbox` tools | `--allowedTools` list |
| Elixir/OTP supervision | Python asyncio task pool |

Verified in code — `stokowski/runner.py:23-61` `build_claude_args()`: `-p <prompt>` plus `--resume <session_id>` when continuing (`:34`), `--dangerously-skip-permissions` when `permission_mode == "auto"` (`:42-43`), `--allowedTools <csv>` when `permission_mode == "allowedTools"` (`:44-45`), `--model` (`:48-49`), `--append-system-prompt` (`:59-61`). `build_codex_args()` at `:66-72` emits `codex --quiet`.

**Symphony's app-server protocol is the single thing that could not be ported.** Everything else survives; the JSON-RPC session protocol becomes CLI flags plus stream-json parsing.

#### What it ADDED — a real state machine with typed states

This is the biggest deviation from symphony and the one most relevant to designing an agent team. Symphony has a flat active/terminal model with no stages; stokowski adds a configurable DAG-with-cycles.

> "Symphony uses a flat model — issues are either active or terminal, and agents run until the issue moves to a done state. There's no concept of stages, gates, or transitions." — `README.md:175`

Three **state types** (`stokowski/config.py:104`, validated at `:633`; documented `README.md:679-683`):

| Type | Has prompt | Behavior |
|---|---|---|
| `agent` (default) | Yes | Dispatches a runner, runs turns, follows `transitions.complete` on success |
| `gate` | No | Moves the issue to the review Linear state and **waits for a human**; follows `transitions.approve` on Gate Approved, `rework_to` on Rework |
| `terminal` | No | Moves to terminal Linear state, deletes workspace |

Per-state fields on `StateConfig` (`stokowski/config.py:101-120`): `type`, `prompt`, `linear_state`, `runner`, `model`, `max_turns`, `turn_timeout_ms`, `stall_timeout_ms`, `session`, `permission_mode`, `allowed_tools`, `hooks`, `transitions`, `rework_to` (gate only, `:115`), `max_rework` (gate only, `:116`). Validation rejects an unknown `type` (`:633`) and a gate missing `rework_to` or pointing at a nonexistent state (`:643-645`).

**Rework targets can point at any earlier state, not just the previous one** (`README.md:180`) — so the graph admits cycles, unlike a pure DAG.

#### The role taxonomy — stage prompt files

Stokowski's shipped example pipeline is the four-role team symphony never had. Roles are *files in `prompts/`*, not agent definitions:

| Stage prompt | Verbatim role statement | Lines |
|---|---|---|
| `prompts/global.example.md` | shared project context injected into every turn | 46 |
| `prompts/investigate.example.md` | "You are investigating issue **{{ issue.identifier }}**… **Objective:** Understand the problem thoroughly before any code is written. Your output is an investigation summary posted as a Linear comment — not code changes." (`:3`, `:19-21`) | 51 |
| `prompts/implement.example.md` | implementation stage | 73 |
| `prompts/review.example.md` | "You are an independent code reviewer with **NO prior context** about this issue… Perform a thorough, adversarial code review. Your job is to find problems the implementer missed — not to rubber-stamp the PR." (`:3-4`, `:19-21`) | 64 |
| `prompts/merge.example.md` | merge stage | 52 |

The reviewer role is enforced structurally, not just by prompt wording: `session: fresh` on the `code_review` state starts a new session with no prior context, and `runner: codex` runs it on a **different model family** than the implementer (`README.md:656-663`). That is cross-family cold review expressed as config.

#### Three-layer prompt assembly

> "Symphony renders a single Jinja2 template from `WORKFLOW.md`. Stokowski builds prompts from three layers" — `README.md:200-205`

1. **Global prompt** — shared context, every turn.
2. **Stage prompt** — per-state instructions, "pure Markdown, no config in prompt files".
3. **Lifecycle injection** — auto-generated: issue metadata, rework context, recent Linear comments, available transitions.

> "Prompt authors never need to write 'move the issue to Human Review when done' — the lifecycle layer handles that based on the YAML config." (`README.md:205`)

Template variables are *flattened* relative to symphony's nested `issue` object (`README.md:715-728`): `issue_identifier`, `issue_title`, `issue_description`, `issue_state`, `issue_priority`, `issue_labels`, `issue_url`, `issue_branch`, plus **three symphony doesn't have** — `state_name`, `run` ("Run number for this state (increments on rework)"), and `last_run_at`. Symphony's single `attempt` is split into `run` (rework generation) and `attempt` (retry within a run) — exactly the `retry_kind` distinction `SPEC.md:1347-1349` names as out of core scope.

#### State persistence: HTML comments as a database

Where symphony keeps a free-form `## Codex Workpad` markdown comment for *humans*, stokowski writes **machine-readable HTML comments** to Linear and parses them back for crash recovery (`stokowski/tracking.py`):

```python
STATE_PATTERN = re.compile(r"<!-- stokowski:state ({.*?}) -->")  # tracking.py:13
GATE_PATTERN = re.compile(r"<!-- stokowski:gate ({.*?}) -->")  # tracking.py:14
```

Each comment carries a JSON payload (`state`, `run`, `timestamp`; gates add `status` and `rework_to`) followed by a human-readable line (`tracking.py:17-49`). This is how the port gets durable state without the database symphony declines to require — the tracker *is* the database. `README.md:182` calls it "state transitions persisted as HTML comments on Linear issues for crash recovery".

#### Other additions beyond symphony

- **Multi-project**: one daemon, many Linear projects, each with its own repo/hooks/prompts/state machine, sharing one global concurrency pool with optional per-project fairness caps and runtime pause/resume (`README.md:152`, `:465-544`). Symphony has no notion of more than one project.
- **`on_stage_enter` hook** — a fifth lifecycle hook symphony does not define (`README.md:587`).
- **`gate_approved` and `rework` as first-class lifecycle roles** — six required roles (`todo`, `active`, `review`, `gate_approved`, `rework`, `terminal`) mapped to renameable Linear state names (`README.md:346-359`). `config.py:627` also lists an `awaiting_ci` role key.
- **`max_rework` with automatic escalation** (`README.md:181`).
- **Acceptance-criteria JSON in the ticket body** that the agent self-verifies before moving to review (`README.md:779-794`).
- **Web dashboard** (FastAPI + vanilla JS, `stokowski/web.py`, 1,394 lines) and a persistent terminal command bar with single-key controls (`README.md:210-228`).
- **Process-group kill** via `os.killpg` "catching grandchild processes too" (`README.md:234`) — a real hazard when the child is a CLI that spawns its own subagents.
- **Headless system prompt** "disabling interactive skills, plan mode, and slash commands" (`README.md:236`).

#### What it DROPPED / reshaped

- **The app-server protocol**, necessarily (see mapping table).
- **`WORKFLOW.md` as the config carrier** — replaced by `workflow.yaml` + a `prompts/` directory; the old format "is still parsed for backward compatibility" (`README.md:890`). The stated reason is *context hygiene*, and it is the sharpest harness-specific argument in the survey:
  > "The problem with putting autonomous agent instructions in `CLAUDE.md` is that they bleed into your regular Claude Code sessions — your day-to-day interactive work now carries all the 'you are running headlessly, never ask a human, follow this state machine' instructions that only make sense for an unattended agent." (`README.md:93`)
- **Trackers other than Linear** — `tracker.kind` accepts `"linear"` only (`README.md:553`), against symphony's five adapters. A narrowing, not an extension.
- **Symphony's default concurrency** — `agent.max_concurrent_agents` defaults to `5` here (`README.md:609`) vs symphony's `10`.

#### Does it use Claude Code's native team primitives? **No.**

Control-armed probe (2026-08-04, clone root):

```
grep -rniE '\.claude/agents|AGENT_TEAMS|EXPERIMENTAL_AGENT_TEAMS|subagent_type|Workflow tool|Task tool' \
  --include='*.py' --include='*.ts' --include='*.md' --include='*.yaml' stokowski/   → 0 hits
grep -rniEc 'claude' stokowski/stokowski/runner.py   # CONTROL                        → 27
```

The control finds 27 hits in the file that does the invoking, so the probe reaches the code. Stokowski drives Claude Code purely as a **headless CLI subprocess**; it reimplements every coordination concern (dispatch, concurrency, retry, reconciliation, session resume) in Python asyncio. It does ship one native artifact — `.claude/commands/release.md`, its own maintainers' slash command — and `examples/create-ticket.md` is a slash command for *humans* to author tickets. Neither is orchestration.

Its only concession to Claude Code's ecosystem is MCP: agents run with `cwd` = the workspace, so a repo `.mcp.json` is picked up automatically (`README.md:736`).

---

### 2.2 mksglu/hatice — TypeScript, **the closest structural port**, on the Claude Agent SDK

**Measured 2026-08-04:** 154 stars, 27 forks, 6 open issues, MIT, created 2026-03-06, last push 2026-05-15T20:24:38Z. Clone at `389627cc2d2e8037ea3cc68c7e16dccb2dc0c4eb` (2026-05-15 23:24:38 +0300), 84 blobs, `package.json` version `0.1.0`.

**Harness targeted:** the **Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk ^0.2.70`, `package.json`) — the only port of the four that uses a *programmatic* SDK rather than shelling out to a CLI.

Self-description: *"We reimagined every component from scratch in TypeScript, replacing Codex with Claude Code Agent SDK and adding capabilities that go beyond the original. **No code was copied. No license was violated.** We adopted the manifesto, studied the architecture, and built something new."* (`README.md:36-38`)

#### Module-for-module correspondence

This is a 1:1 structural port. Compare the file trees:

| symphony (`elixir/lib/symphony_elixir/`) | hatice (`src/`) |
|---|---|
| `orchestrator.ex` | `orchestrator.ts` + `orchestrator-state.ts` |
| `workspace.ex` | `workspace.ts` |
| `workflow_store.ex` | `workflow-store.ts` |
| `agent_runner.ex` | `agent-runner.ts` |
| `prompt_builder.ex` | `prompt-builder.ts` |
| `status_dashboard.ex` | `status-dashboard.ts` + `dashboard-template.ts` |
| `http_server.ex` | `http-server.ts` |
| `config.ex` + `config/schema.ex` | `config.ts` |
| `tracker.ex` + `{linear,github,gitlab,jira,asana}/adapter.ex` | `tracker.ts` + `{linear,github,gitlab}/adapter.ts` |
| `agent_runtime_supervisor.ex` (OTP) | `supervisor.ts` (hand-written) |
| `log_file.ex` | `logger.ts` + `session-logger.ts` |
| `path_safety.ex` | `path-utils.ts` |

Hatice's own comparison table (`README.md:41-70`) names every substitution: Elixir/OTP → Node 20+/Bun, Codex JSON-RPC → Agent SDK `query()`, Phoenix LiveView (WebSocket) → Hono + SSE, NimbleOptions → Zod v4, EEx → LiquidJS, Elixir Logger → Pino, OptionParser → Commander.js, **OTP Supervisor (native) → "Custom Supervisor class"**, Phoenix.PubSub → "Typed EventBus with wildcard".

That OTP row is the load-bearing one. Symphony's crash-recovery and process-supervision semantics are *free* on the BEAM; every port off Elixir has to hand-write them. Hatice's answer is `src/supervisor.ts` plus `src/event-bus.ts`; stokowski's is a Python asyncio task pool plus `os.killpg`.

#### It kept symphony's `WORKFLOW.md` contract intact

Unlike stokowski, hatice preserves the single repo-owned `WORKFLOW.md` with YAML front matter + prompt body (parsed with `gray-matter`, rendered with LiquidJS — Liquid-compatible, as `SPEC.md:499` requires). Its front matter is symphony's schema in camelCase (`WORKFLOW.md:1-23`): `tracker.{kind,apiKey,projectSlug,activeStates,terminalStates,assignee}`, `workspace.rootDir`, `hooks.afterCreate`, `polling.intervalMs`, `agent.{maxConcurrentAgents,maxTurns}`, `claude.{permissionMode,model}`, `server.port`.

The one schema deviation that matters: **`codex:` becomes `claude:`**, and its fields are Agent SDK options rather than Codex pass-throughs (`src/config.ts:46-55`, Zod):

```
model: string|null = null                     permissionMode: string = 'bypassPermissions'
allowedTools: string[]|null = null            disallowedTools: string[]|null = null
systemPrompt: string|null = null              canUseTool: Record<string,boolean>|null = null
claudeCodePath: string|null = null
```

`agent.maxTurns` defaults to `20` (`src/config.ts:40,78`) — symphony's number, kept.

#### How the session protocol maps

`src/agent-runner.ts:147-192` builds the `query()` call. The mapping to symphony's app-server concepts:

| symphony | hatice |
|---|---|
| `bash -lc <codex.command>` in the workspace | `queryOptions.cwd = workspacePath` (`:164`) |
| `approval_policy: never` | `permissionMode` + `allowDangerouslySkipPermissions: true` when `bypassPermissions` (`:167-168`) |
| `thread_sandbox` / tool declarations | `allowedTools` / `disallowedTools` / `canUseTool` callback (`:171-179`) |
| `thread_id`, reused across continuation turns | `session_id` captured from the SDK `system`/`init` message (`:207-209`), replayed as `resume` on turn > 1 (`:181`) |
| `agent.max_turns` | `maxTurns` in query options (`:165`) |
| stall/turn timeouts | `abortController` (`:166`) + `TurnTimeout` (`src/turn-timeout.ts`) |
| provider-native agent tools | `createSdkMcpServer` + `tool` → `linear_graphql`, `github_graphql` (`:153-156`) |

One detail worth stealing verbatim — hatice has to **strip `CLAUDECODE` from the child env** so an agent can be spawned from inside a Claude session (`src/agent-runner.ts:159-161`):

```ts
// Strip CLAUDECODE env var to allow spawning Claude from within a Claude session
const cleanEnv = { ...process.env };
delete cleanEnv.CLAUDECODE;
```

`src/agent-spawn.ts` additionally provides a custom spawn function for the SDK's `spawnClaudeCodeProcess` option so a pinned `claudeCodePath` binary can be used.

#### What it added

Per `README.md:41-70` and `:72-82`: GitHub Issues and GitLab adapters (symphony's Elixir impl has Linear/GitHub/GitLab/Jira/Asana, so this is parity-minus-two, not a net add — see the correction below); per-session **USD cost tracking**; **cache token metrics** (`cacheRead`/`cacheCreationInputTokens`); full 429 rate-limit tracking (`src/rate-limiter.ts`); per-session NDJSON logs via Pino (`src/session-logger.ts`); **auto-respond to agent input requests** (`src/input-handler.ts`, config `claude.autoRespondToInput`) — a direct answer to `SPEC.md:1073-1075`'s "MUST NOT stall indefinitely", choosing *auto-resolve* where symphony's reference posture chooses *hard failure*; per-turn `AbortController` deadline; age-based stale-workspace startup cleanup; `~/` expansion in config paths.

> ⚠️ **UNVERIFIED / likely wrong in the source:** hatice's table claims symphony has "Issue Tracker: Linear only" and "MCP Tools: Not available". Both are false against the tree I read — `elixir/lib/symphony_elixir/{linear,github,gitlab,jira,asana}/adapter.ex` are all present, each with an `agent_tool.ex`, and `SPEC.md:1091-1127` specifies the provider-native agent-tool extension. The likely explanation is that the table was written against an earlier symphony commit; I did not check symphony's history to confirm that, so treat the *reason* as unverified while the present-day discrepancy is measured.

#### What it did NOT add: any role taxonomy

Control-armed probe (2026-08-04, clone root):

```
grep -rniEc 'role|stage|gate|reviewer|investigat' README.md WORKFLOW.md src/config.ts
  → README.md:1   WORKFLOW.md:0   src/config.ts:0
grep -rniEc 'orchestrat|workspace' README.md WORKFLOW.md src/config.ts   # CONTROL
  → README.md:25  WORKFLOW.md:3   src/config.ts:2
```

The control returns hits in all three files with the same command shape, so the zeros are real. Hatice is **one agent, one prompt, one ticket** — exactly symphony's model. It does not add stages, gates, or reviewer roles.

Human checkpoints are correspondingly thinner than either symphony's or stokowski's: there is no `Human Review` gate in the shipped `WORKFLOW.md` (`activeStates: ["In Progress"]`, `terminalStates: ["Done","Canceled","Duplicate"]`), and `permissionMode: bypassPermissions` is the *default* in the Zod schema (`src/config.ts:48`), not an opt-in.

#### Does it use Claude Code's native team primitives? **No.**

Same control-armed probe as §2.1, run over `hatice/`: zero hits for `.claude/agents`, `AGENT_TEAMS`, `EXPERIMENTAL_AGENT_TEAMS`, `subagent_type`, `Workflow tool`, `Task tool` across `*.ts`/`*.md`/`*.yaml`; the `claude` control returns 27 hits in stokowski's runner in the same sweep, so the sweep reaches code. Hatice uses the **Agent SDK** (a native Anthropic primitive) but reimplements all coordination — dispatch, concurrency, retry, reconciliation, supervision — in TypeScript. It ships a `.claude/CLAUDE.md` that "enforces test-driven development for all contributions" (`README.md:82`) — that is the maintainers' own repo instruction file, not orchestration.

---

### 2.3 manav03panchal/phonyhuman — a **hard fork** of symphony's Elixir, with a protocol shim

**Measured 2026-08-04:** 3 stars, 1 fork, 0 open issues, Apache-2.0, created 2026-03-06, last push 2026-03-16T04:35:29Z — **the least maintained of the four; last touched ~4.5 months before I measured.** 201 blobs. Read via `raw.githubusercontent.com/manav03panchal/phonyhuman/HEAD/…`; the tree via `gh api repos/…/git/trees/HEAD?recursive=1`.

**Harness targeted:** the **Claude Code CLI**, via a Python translation layer. Self-description: *"A fork of OpenAI's Symphony that uses **Claude Code** instead of Codex. Works with your Claude Max subscription — no Anthropic API key needed."* (`README.md:3`)

**This is the only port that keeps symphony's actual code.** `elixir/lib/symphony_elixir/…` is present with the original module names, and the Elixir tree is *extended* rather than replaced — `orchestrator/{dispatch,fleet_pause,reconciliation,token_accounting}.ex`, `linear/circuit_breaker.ex`, `log_redactor.ex`, `redacting_formatter.ex`, `restart_monitor.ex`, `hook_validator.ex`, `agent_server/{protocol,server,tool_handler,dynamic_tool}.ex`. Symphony's four non-Linear adapters (github/gitlab/jira/asana) are **gone** — `linear/` only.

#### The delta that defines it: `claude-shim.py`

791 lines of Python stdlib, zero dependencies. Its own docstring (`claude-shim.py:3-10`):

> "claude-shim: An agent server protocol shim that drives Claude Code CLI… but internally spawns `claude` CLI using the user's Claude Code Max subscription."

The architecture the README draws (`README.md:222-227`):

```
phonyhuman            TOML config → generates WORKFLOW.md → launches Symphony
  └─ Symphony (Elixir)   Polls Linear, manages workspaces, dispatches agents
       └─ claude-shim.py Speaks Codex JSON-RPC protocol, drives Claude Code CLI
            └─ claude     Your Claude Max subscription does the actual work
```

**Symphony is unmodified above the shim.** Instead of porting the orchestrator to a new agent, phonyhuman makes Claude Code *impersonate* a Codex app-server: `handle_initialize` (`:562`), `handle_initialized` (`:572`), `handle_thread_start` (`:575`), `handle_turn_start` (`:582`), plus `linear_graphql` tool-call execution (`:99`). `turn/start` acks immediately with a turn ID and streams thereafter — "Codex protocol: ack, then stream" (`:602`).

Each turn spawns (`claude-shim.py:411-423`):

```python
cmd = [
    "claude",
    "-p",
    self.prompt,
    "--output-format",
    "stream-json",
    "--dangerously-skip-permissions",
    "--verbose",
]
allowed = get_allowed_tools()
if allowed:
    cmd.extend(["--allowedTools"] + allowed)
```

It strips `CLAUDECODE` from the child env for the same nested-session reason hatice does (`:427-428`), and additionally strips OTEL exporter endpoint vars "to prevent bypass via protocol-specific overrides" (`:429-431`, helpers at `:295-344`).

#### The regression this shim introduces: no session continuity

Control-armed probe (2026-08-04):

```
grep -nc -- '--resume\|session_id\|--continue' ph/claude-shim.py       → 0
grep -nc -- '--output-format\|--allowedTools' ph/claude-shim.py  # CONTROL → 3
```

The control finds the sibling flags in the same file with the same command shape, so the zero is real. **Every turn is a fresh `claude -p` with no `--resume`.** Symphony's normative requirement is the opposite — `SPEC.md:1011` "Reuse the same `thread_id` for all continuation turns inside one worker run", and `SPEC.md:998-999` "Start later in-worker continuation turns on the same live thread with continuation guidance rather than resending the original issue prompt."

Stokowski maps this correctly (`claude -p --resume <session_id>`) and hatice maps it correctly (`resume: this.sessionId` when `turn > 1`). Phonyhuman does not. The practical consequence: continuation context lives only in the git workspace and the Linear workpad comment — which is precisely why symphony's workpad discipline exists, so the design degrades rather than breaking. Worth knowing before borrowing the shim pattern.

#### What it added

- **A TOML config layer above `WORKFLOW.md`.** You edit `my-project.toml` (`[linear]`, `[repo]`, `[agent]`, `[workspace]`, `[server]`, `[prompt]`) and `bin/phonyhuman` generates the `WORKFLOW.md` symphony consumes (`README.md:106-176`). Symphony's "self-contained `WORKFLOW.md`" design intent (`SPEC.md:336-340`) is inverted into a generated artifact.
- **`phonyhuman init` packages skills into the target project** — it "copies all agent skills into `.codex/skills/` so your project is self-contained. Skills can be customized per-project — re-running init won't overwrite existing skills." (`README.md:33`)
- **Two new skills beyond symphony's seven** (`README.md:70-80`), and this is the port's most interesting design addition:
  - **`prd`** — "Decompose a PRD into Linear issues with dependencies, acceptance criteria, and validation". It reads a PRD, scans the repo for stack and patterns, **creates the Linear project if missing**, **creates the required workflow states if missing**, decomposes into "agent-sized issues (1–5 files each, single responsibility)", creates them in `Backlog` with **`blockedBy` dependency chains**, and reports "parallel tracks, critical path, and estimated points" (`README.md:82-96`).
  - **`sprint-planning`** — "Reference guide for Scrum Masters — issue structure, sizing, and workflow conventions".

  This is how phonyhuman gets a task DAG without changing symphony: **the decomposition happens in a planning agent, upstream, and the graph is expressed as Linear `blockedBy` edges.** "Dependencies are respected — blocked issues wait." (`README.md:48`). Symphony's orchestrator still never reasons about the graph — the adapter's `dispatchable` flag does (`SPEC.md:1279-1280`).
- **Worktree mode** — setting `repo.local_repo` makes workspace creation a `git worktree` off a local checkout instead of a clone, "for fast workspace creation" (`README.md:151-153`; `.codex/worktree_init.sh`).
- **Ops hardening**: `linear/circuit_breaker.ex`, `log_redactor.ex` + `redacting_formatter.ex` (credential redaction in logs), `restart_monitor.ex`, `hook_validator.ex`, `orchestrator/fleet_pause.ex`, a `SECURITY.md` threat model, a `CLAUDE_ALLOWED_TOOLS` env allowlist, Docker/`docker-compose.yml`, golden contract fixtures (`contract/golden/state_*.json`), and a signed-release installer.
- **Rate-limit and usage-cap classification** in the shim (`is_rate_limit` `:228`, `is_usage_cap` `:234`, `parse_retry_after` `:247`, `classify_error` `:263`) — a Max-subscription concern Codex-based symphony never had.

#### Role taxonomy, and human checkpoints

No agent roles — it inherits symphony's model exactly. The tracker states are symphony's plus a documented `Merging` step, and **"Human Review, Merging, and Rework must be named exactly as shown — agents use exact string matching"** (`README.md:196`). Human checkpoints are the same two as symphony (`Backlog`→`Todo` entry, `Human Review`→`Merging` approval), with `Rework` defined as a full restart: "Reviewer requested changes; agent closes PR, starts fresh" (`README.md:215`).

#### Does it use Claude Code's native team primitives? **No.**

It drives `claude -p` as a subprocess from Python. Its `.codex/skills/` are Codex-format skill files (symphony's, minus `release`), used inside the agent's own session — not Claude Code subagent definitions. Note the naming inversion worth flagging if you borrow from it: the agent is Claude, but the skills directory, the workpad marker (`## Codex Workpad`), and the PR label (`symphony`) are all still Codex/symphony-branded.

**Verification note:** the README names files that a shallow tree listing could miss. I control-armed it — `skills/{commit,land,linear,prd,pull,push,sprint-planning}`, `linear-cli.py`, `templates/default-prompt.md`, `templates/example.toml`, `install.sh`, `example.toml` are all present in the tree; the control (`claude-shim.py`, `bin/phonyhuman`, `demo.toml`) matched too, so the probe discriminates. Every README claim I cite above is backed by a file that exists.

---

### 2.4 vnovick/itervox — Go, **the most feature-complete, and the only one with agent evals**

**Measured 2026-08-04:** 38 stars, 9 forks, 11 open issues, license `NOASSERTION` (README badge says Apache-2.0), created 2026-03-18, last push 2026-07-06T14:29:59Z. **839 blobs** — by far the largest. Read via `raw.githubusercontent.com/vnovick/itervox/HEAD/…`.

**Harness targeted:** *both* — "spawns Claude Code or Codex agents per issue", pluggable backends (`internal/agent/claude.go`, `internal/agent/codex.go`, `internal/agent/multi.go`), "OpenCode and Gemini CLI are on the roadmap" (`README.md:74`). It shells out and explicitly does not manage credentials: "Itervox shells out to `claude` or `codex` and does **not** manage agent credentials itself" (`README.md:46`).

Self-description: *"a full Go implementation of the OpenAI Symphony spec — formerly known as 'Symphony Go'."* (`README.md:24`)

**It went further than being a port — it wrote its own spec.** `README.md:26-33`: itervox is "the reference implementation of the [Orchestrated Coding spec](https://github.com/vnovick/orchestrated-coding) and conforms at **L3**… Itervox is *also* a conforming OpenAI Symphony runtime." So symphony's spec got forked into a tiered conformance spec with its own implementation ledger. I did not audit `vnovick/orchestrated-coding` itself — flagged as **UNVERIFIED** beyond the claim's existence.

#### The role taxonomy: file-backed agent profiles (`SOUL.md` + `INSTRUCTIONS.md`)

This is the second port with roles, and it expresses them as **files on disk in a convention-named directory** — the closest thing in this survey to Claude Code's `.claude/agents/`:

```text
.itervox/agents/
  implementer/
    SOUL.md          # compact identity — who this agent is, what it values
    INSTRUCTIONS.md  # full operating rules, checklists, Liquid template
  reviewer/
    SOUL.md
    INSTRUCTIONS.md
```
(`README.md:232-242`)

> "Define named agent profiles with their own command, backend, and operating instructions. Different issue types get different profiles — a senior reviewer for security work, a fast haiku model for typo fixes, a Codex long-horizon runner for research." (`README.md:230`)

`WORKFLOW.md` references them via `agent.profiles.<name>.soul_file` / `.instructions_file`, gated on `itervox_schema_version: 2` (`README.md:244`, example at `:400-407`). **Inline prompts were deliberately removed** — "inline `agent.profiles.<name>.prompt` is rejected by schema 2", with `itervox init --update` as a one-shot migrator that extracts inline prompts into `INSTRUCTIONS.md` and generates starter `SOUL.md` files (`README.md:246`). `.itervox/agents/**` is checked into git; `HEARTBEAT.md`, logs and `.env` stay ignored.

**The SOUL/INSTRUCTIONS split is the single most transferable idea in this survey.** Worked example — the built-in `merge-bot`, embedded in the binary (`internal/profiles/builtin/merge-bot/SOUL.md`, 10 lines, verbatim opening):

> "You are merge-bot — the final gate before code reaches main.
> Your identity:
> - You are **paranoid by design**. You exist precisely because humans make mistakes when they are tired or excited about shipping.
> - **You never write code. You never push commits. You never start new work.**
> - Your only job is to verify a pull request meets every required precondition, then merge it.
> - If anything is off — failing checks, blocking labels, an unsignalled diff — you refuse to merge and explain exactly what is wrong in a comment.
> - **A wrong merge has unbounded blast radius. A refused merge is annoying. You always prefer the annoying outcome.**
>
> Tone: terse, factual, no apologies. State the precondition that failed and what the operator needs to do."

`INSTRUCTIONS.md` (47 lines) is the *procedure*: numbered ordered steps, exact `gh` commands, explicit STOP conditions, and one hard prohibition worth noting — "**DO NOT shell out to `gh pr merge` directly.** The `merge_pr` action centralises the guard list, the dedup ledger, and the dashboard surface." (`:35-37`).

The separation is clean and load-bearing: **SOUL = values and refusal posture (why), INSTRUCTIONS = procedure and guards (how)**. A role's judgment is versioned separately from its checklist.

#### Agent evals — the only self-improvement machinery in the survey

`internal/evals/fixtures/<profile>/<scenario>/` holds `input.yaml`, `expected.yaml`, and `recording.jsonl`. Shipped scenarios: `merge-bot/{green-ci-approval, green-ci-block-label, multiple-matching-prs, no-matching-pr, red-ci-approval, wrong-marker-phrase}` and `reviewer/{approves-with-marker, rejects-and-moves-back}`.

`expected.yaml` is "the behavioral contract the judges enforce: `required_action_calls` / `forbidden_actions` against the transcript's action events, `marker_phrases` as substrings of its comment events" (`internal/evals/fixtures/README.md:7-10`). The purpose: "a prompt edit that changes the contract fails `make evals-fast` and forces a deliberate fixture update" (`:20-22`).

**That README also contains the most intellectually honest caveat in any of these five repos**, and it is worth quoting because it is exactly the control-arm discipline this repo's rules demand:

> "## Provenance — read before trusting a green run
> The recordings here are **hand-authored behavioral contracts**, not captures of real agent runs (live-recording mode is future work)… They do NOT prove the current SOUL/INSTRUCTIONS actually produce these transcripts; that is exactly what live-recording mode adds. When it lands, re-record every scenario and delete this caveat.
> Known judge limitation: marker phrases assert presence only. 'The approve path must NOT emit `/ai-approved` on a failing PR' is not expressible — absence checks also wait for live mode." (`:14-28`)

So: **prompt-regression gating exists; outcome-driven prompt revision does not.** Still no closed self-improvement loop — but this is the only port that built the harness a loop would need.

#### Coordination: automations replace a state machine

Where stokowski added an explicit state machine, itervox added an **event-triggered automation system** with ten trigger types (`README.md:82`): `cron`, `input_required`, `tracker_comment_added` (with `body_contains` / `body_regex` filters), `issue_entered_state`, `issue_moved_to_backlog`, `run_failed`, `pr_opened`, `pr_merged`, `rate_limited`, `blockers_resolved` (dependency audit). Its stated design rationale is directly relevant to any team design:

> "Reuse normal profiles, filters, and permissions instead of inventing a separate workflow engine." (`README.md:82`)

That is the opposite bet from stokowski's, and both are defensible: stokowski declares the pipeline; itervox declares the triggers and lets the pipeline emerge. Implementation lives across ~25 files in `internal/orchestrator/automation*.go` plus a persisted `automation_queue`.

Multi-agent chaining does exist, in two narrow forms:

- **`reviewer_profile` + `auto_review`** — "dispatch a second worker for PR review". The workspace-lifetime interaction was a real bug they had to fix: "`auto_clear` now fires only on terminal tracker states, so the reviewer gets the implementer's workspace and the clear is deferred until after the reviewer also completes" (`README.md:262`, `:445`).
- **`.itervox/handoff/` files** — "the workspace persists across retries, input-required pauses, and pipeline mid-states — so **chained profiles can share `.itervox/handoff/` files on the same branch**" (`README.md:445`). That is the port's answer to inter-agent handoff: a shared directory in a shared workspace, not a message.

#### Per-role configuration and permissions

Per-profile: `command` (which includes the model, e.g. `claude --model claude-opus-4-6`), `backend`, `soul_file`, `instructions_file`, `enabled`, and — importantly — **`allowed_actions`**:

> "Automation helpers stay sandboxed by profile permissions. If an automation should comment, move state, create follow-up issues, or auto-resume a blocked run, enable only the required `allowed_actions` on that profile. **The daemon issues short-lived action grants per run instead of handing the agent your dashboard API token.**" (`README.md:264`)

This is symphony's credential-isolation principle (`SPEC.md:1107-1111`) generalized into **per-role capability scoping** — the design most worth copying for a Claude Code team, where the analogue is a per-subagent `tools:` list.

`agent.max_concurrent_agents`, per-state concurrency limits, retry backoff ("10s, 20s, 40s… capped at 5 min" — symphony's formula exactly), stall detection, and `max_turns` are all inherited from symphony (`README.md:78-80`, `WORKFLOW.md:26-33`).

#### Symphony's SSH appendix, actually implemented

`agent.ssh_hosts` + `dispatch_strategy: round-robin | least-loaded`, "automatic failover to the next host on connection failure" (`README.md:291-301`, `internal/agent/ssh.go`). Symphony leaves this to Appendix A as an OPTIONAL extension with a list of "Problems to Consider" (`SPEC.md:2292-2311`); itervox shipped it, with least-loaded dispatch that the appendix doesn't specify.

Plus **Fleet Logs**: "capture the full subagent tree — parent plus every spawned sub-agent, every tool call — via `CLAUDE_CODE_LOG_DIR`" (`README.md:299`). This is the one place a port reaches into a Claude-Code-specific observability surface.

#### Skills Inventory — a Claude Code capability analyzer

`internal/skills/scan_{skills,plugins,mcp,hooks,instructions,codex,ssh}.go` + `analyze.go` + `recommend.go` + `context_budget.go` build an inventory of "every Claude Code / Codex capability your project carries — skills, plugins, MCP servers, hooks, and instruction docs" from `.claude/skills/`, `~/.claude/skills/`, `.claude/plugins/`, `.claude/settings.json::mcpServers`/`::hooks`, `CLAUDE.md`/`AGENTS.md`, and the Codex equivalents (`docs/skills-inventory.md:11-30`).

Seven static analyzer rules (`docs/skills-inventory.md:34-44`): `DUPLICATE_SKILL`, `DUPLICATE_MCP`, `UNUSED_PROFILE`, `BLOATED_PROFILE` (">20 MCP servers OR >15 skills"), `LARGE_CONTEXT` (">50K tokens"), `INSTRUCTION_SHADOWING`, `ORPHAN_MCP`. Token estimates are declared heuristics (`len(file)/4`; `800 × server_count` for MCP schemas).

This is **entirely absent from symphony and from the other three ports**, and it is the only component in the survey that reasons about the *harness's own* context economy.

#### Human checkpoints — the strictest of the four

Section heading: **"Human in the Loop — Autonomous, not unsupervised."** (`README.md:258-260`)

- **"You merge the PR. Agents submit PRs and post a session summary as a comment — they never merge."** (`README.md:266`) — a harder line than symphony's `Merging`-state agent-driven `land` skill. (The built-in `merge-bot` profile is the deliberate, guard-railed, opt-in exception.)
- **`input_required` is a first-class state, not a failure.** Symphony's reference posture treats user-input-required as a hard failure (`SPEC.md:1081`); itervox pauses, posts the question as a tracker comment, and "the agent picks up your response and resumes automatically **in the same session**" (`README.md:80`, `:264`). The recommended signal is an explicit marker, `<!-- itervox:needs-input -->`, with a "best-effort English-oriented fallback" detector that the docs correctly flag as heuristic (`internal/agent/input_detector.go`).
- **Auto-pause on open PR** — "an existing open PR is detected and the agent pauses to prevent duplicate work" (`README.md:87`).
- **Pause & resume** — "free up a slot; resume later via `--resume` and continue the same session from exactly where it stopped" (`README.md:78`).

#### Does it use Claude Code's native team primitives? **No — but it is the most Claude-Code-aware.**

Control-armed probe over the 839-path tree (2026-08-04):

```
grep -iE '\.claude/agents|agent_teams|subagent' tree-itervox.txt
  → internal/orchestrator/subagents_internal_test.go
  → web/src/components/itervox/timeline/SubagentBar.tsx
grep '^\.claude' tree-itervox.txt   # CONTROL
  → .claude/commands/{brainstorm,interview}.md, .claude/settings.json,
    .claude/skills/{authed-transport,breaking-change-gate,…}/SKILL.md  (13 paths)
```

The control finds itervox's own `.claude/` tree, so the probe reaches `.claude` paths — and **there is no `.claude/agents/` directory**. The two `subagent` hits are *observability*: displaying the subagent tree Claude Code produces inside a single agent run (Fleet Logs), not defining subagents. `AGENT_TEAMS` / `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`: zero hits.

Its `.claude/skills/*` (10 skills — `orchestrator-invariants`, `verify-before-done`, `breaking-change-gate`, `change-impact-review`, …) are the maintainers' own dev skills, and `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / `.cursor/rules` / `.codex/config.toml` at the root are its own harness config. Its *product* reads those directories (Skills Inventory) and spawns `claude`/`codex` as subprocesses; it never delegates coordination to them.

## 3. Comparison table

All rows measured 2026-08-04 from the commits named in each section.

| Dimension | **openai/symphony** | **stokowski** | **hatice** | **phonyhuman** | **itervox** |
|---|---|---|---|---|---|
| Language / runtime | Elixir/OTP (spec is language-agnostic) | Python 3.11+ asyncio | TypeScript / Node 20+ / Bun | Elixir/OTP **fork** + Python shim | Go, single static binary |
| Relationship to symphony | the original + `SPEC.md` | independent impl of the spec, extended | clean-room reimpl ("no code was copied") | **hard fork of the code** | full Go impl; also wrote its own tiered spec |
| Agent harness | Codex `app-server` JSON-RPC over stdio | `claude -p --output-format stream-json` **or** `codex --quiet`, per stage | **Claude Agent SDK `query()`** | `claude -p` behind a JSON-RPC **shim** | `claude` **or** `codex` subprocess, pluggable |
| **Role taxonomy** | **NONE** (control-armed) — 1 agent, 7 Codex skills | **5 stage prompts**: global, investigate, implement, review, merge | **NONE** (control-armed) — inherits symphony | **NONE** — but adds `prd` + `sprint-planning` *planning* skills | **named profiles** as `SOUL.md` + `INSTRUCTIONS.md` under `.itervox/agents/<name>/` |
| Work unit | one tracker ticket | one ticket × one pipeline stage | one tracker ticket | one tracker ticket | one ticket × profile |
| Task graph / DAG | **none**; `blocked_by` is best-effort metadata the orchestrator MUST NOT interpret | **explicit state machine** with typed states + cycles (`rework_to` → any earlier state) | none (symphony's model) | **upstream** — `prd` skill decomposes a PRD into issues with `blockedBy` chains | none declared; **10 event triggers** ("reuse profiles… instead of inventing a separate workflow engine") |
| Config carrier | repo-owned `WORKFLOW.md` (YAML front matter + Liquid body), hot-reloaded | `workflow.yaml` + `prompts/*.md` dir (WORKFLOW.md still parsed for back-compat) | `WORKFLOW.md`, camelCase keys, Zod-validated | **TOML → generates `WORKFLOW.md`** | `WORKFLOW.md` `itervox_schema_version: 2`; inline prompts **rejected** |
| Per-role tunables | n/a — one global block; model/effort ride inside `codex.command` | `runner`, `model`, `max_turns`, timeouts, `session: inherit\|fresh`, `permission_mode`, `allowed_tools`, `hooks` | n/a — one `claude:` block (`model`, `permissionMode`, `allowed/disallowedTools`, `canUseTool`, `systemPrompt`) | n/a — inherits symphony; `CLAUDE_ALLOWED_TOOLS` env allowlist | `command` (incl. model), `backend`, soul/instructions files, `enabled`, **`allowed_actions`** capability scope |
| Session continuity | same `thread_id` across continuation turns (REQUIRED) | `claude -p --resume <session_id>` ✅ | `resume: sessionId` when turn > 1 ✅ | **❌ none** — fresh `claude -p` every turn (control-armed) | `--resume`, incl. resume after an `input_required` pause |
| Concurrency bounds | global `max_concurrent_agents`=10, `max_concurrent_agents_by_state`, `max_turns`=20 | global (default 5) + per-state + **per-project** caps, runtime pause/resume | global + per-state (symphony's) | `max_concurrent`=5 (symphony's) | global + per-state; "1 to 50+ without config changes" |
| Intermediate state | filesystem workspace + one free-form `## Codex Workpad` tracker comment | workspace + **machine-readable `<!-- stokowski:state {...} -->` / `:gate` HTML comments** parsed back for crash recovery | workspace + tracker comment | workspace (or **git worktree**) + workpad | workspace + `.itervox/handoff/` shared files + `.itervox/HEARTBEAT.md` |
| Retry / backoff | `min(10000·2^(n-1), 300000)`; 1s continuation retry after clean exit | exponential backoff + stall detection + `os.killpg` process-group kill | exponential + `AbortController` per-turn deadline + 429 tracking | exponential + rate-limit/usage-cap classification in the shim | "10s, 20s, 40s… capped at 5 min" + stall detection + **rate-limit reassignment to a different profile** |
| Human checkpoints | 2: `Backlog`→`Todo`, `Human Review`→`Merging`. Unattended otherwise; user-input-required = **hard failure** | 2+ per pipeline: every `gate` state, with `max_rework` and escalation | **fewest** — no gate in the shipped workflow; `bypassPermissions` is the schema default | symphony's 2, + `Merging` documented as agent-driven `land` | **strictest** — "agents never merge"; `input_required` is a first-class pausable state with tracker round-trip |
| Self-improvement loop | **none** (control-armed); `### Confusions` workpad section is a human signal only | none found | none found | none found | **none closed**, but the only one with **agent evals** (`required_action_calls` / `forbidden_actions` / `marker_phrases`) gating prompt edits — with an honest "does NOT prove the prompts produce these transcripts" caveat |
| Trackers | Linear, GitHub, GitLab, Jira, Asana | **Linear only** | Linear, GitHub, GitLab | **Linear only** | Linear, GitHub Issues |
| Distribution | Appendix A: OPTIONAL SSH workers, one central orchestrator | single host | single host | single host + Docker/compose | **SSH fleet implemented**: `ssh_hosts` + `round-robin`/`least-loaded` + failover + Fleet Logs |
| Uses `.claude/agents`, agent teams, or the Workflow tool? | n/a | **No** (0 hits, control 27) | **No** (0 hits) — uses the Agent SDK, reimplements coordination | **No** — `.codex/skills/` + `claude -p` subprocess | **No** (0 hits; control finds its own 13 `.claude/` paths) — but *reads* those dirs via Skills Inventory |
| Maturity (2026-08-04) | 26,429★ · 2,675 forks · 9 open · pushed 2026-07-24 | 112★ · 26 forks · 6 open · pushed 2026-06-23 | 154★ · 27 forks · 6 open · pushed 2026-05-15 | **3★ · 1 fork · 0 open · pushed 2026-03-16** (stalest) | 38★ · 9 forks · 11 open · pushed 2026-07-06 |

### 3.1 What the deltas reveal

**Essential to the design — every port kept it:**

1. **Poll a tracker → per-issue isolated workspace → one agent session → reconcile.** Untouched by all four.
2. **The tracker is the database.** No port added a durable orchestrator DB; all four persist state as tracker comments and filesystem workspaces, exactly as `SPEC.md:57-58` prescribes.
3. **Repo-owned, hot-reloadable workflow config as the policy layer.** Kept even by stokowski, which changed its shape and file name but not its role.
4. **Reconcile-before-dispatch, with tracker state as the kill signal.** All four.
5. **The three workspace safety invariants** (cwd == workspace, path under root, sanitized key).
6. **Exponential backoff + stall detection.** Reproduced numerically, sometimes to the millisecond.
7. **Success ≠ done** — a run ends at a handoff state, and re-dispatch is normal.

**Artifacts of OpenAI's runtime — every port had to replace them:**

1. **The Codex app-server JSON-RPC protocol.** Four ports, four answers: CLI flags + stream-json (stokowski), the Agent SDK (hatice), a Python shim that impersonates the protocol (phonyhuman), pluggable Go backends (itervox). This is the *only* hard incompatibility.
2. **OTP supervision.** Free on the BEAM, hand-written everywhere else (`supervisor.ts`, an asyncio pool + `os.killpg`, a single-goroutine state machine with an ADR justifying it — `docs/adr/001-single-goroutine-orchestrator.md`).
3. **Codex-specific config pass-through** (`approval_policy`, `thread_sandbox`, `turn_sandbox_policy`) → `permissionMode` / `--dangerously-skip-permissions` / `allowedTools` / `canUseTool`.
4. **Session identity.** `thread_id` + `turn_id` → a single Claude `session_id` replayed via `--resume`. Phonyhuman dropped it entirely, which is the clearest evidence it is a *runtime* affordance and not a spec-level concept.
5. **Two environment details nobody warns you about, found independently by two ports:** strip `CLAUDECODE` from the child env or Claude refuses to spawn nested (hatice `agent-runner.ts:159-161`, phonyhuman `claude-shim.py:427-428`); and kill by **process group**, because the agent CLI spawns grandchildren (stokowski `README.md:234`).

**Added by ports, absent from symphony — i.e. the gaps a real deployment hits:**

| Addition | Who | Why it matters for a Claude Code team |
|---|---|---|
| Typed pipeline stages + human gates + rework cycles | stokowski | the role sequencing symphony has no concept of |
| Roles as versioned files, split **identity** (`SOUL.md`) vs **procedure** (`INSTRUCTIONS.md`) | itervox | maps almost 1:1 onto `.claude/agents/<name>.md`; the split is the transferable part |
| Per-role capability scope (`allowed_actions`, short-lived grants, never hand over the API token) | itervox | the analogue of a per-subagent `tools:` allowlist |
| Cold-review structurally enforced: `session: fresh` + a **different model family** (`runner: codex`) | stokowski | adversarial review that cannot inherit the implementer's blind spots |
| Machine-readable state in tracker comments for crash recovery | stokowski | durable coordination without a database |
| Agent **evals** gating prompt edits, with an explicit provenance caveat | itervox | the only foundation for a future self-improvement loop |
| Task decomposition pushed **upstream** into a planning agent emitting `blockedBy` chains | phonyhuman | how to get a DAG without teaching the orchestrator about graphs |
| Three-layer prompt assembly (global + role + auto-injected lifecycle) | stokowski | keeps role prompts free of transition boilerplate |
| Keeping autonomous-agent instructions **out of `CLAUDE.md`** | stokowski | headless-only rules bleeding into interactive sessions is a real, named failure mode |
| Harness capability inventory (skills/MCP/hooks/instructions + bloat and context-budget rules) | itervox | the only component reasoning about the harness's own context economy |
| `input_required` as a pausable first-class state with a tracker round-trip | itervox | symphony's reference posture *kills* a run that asks a question |

**The most important negative result for the brief's purposes:** **none of the four ports uses Claude Code's native multi-agent primitives.** Zero hits across all four for `.claude/agents`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `subagent_type`, or the Workflow tool — against controls that returned 27, 13, and 3 hits respectively in the same sweeps. Every one of them drives Claude Code as a **headless single-agent subprocess** (or, for hatice, via the Agent SDK) and reimplements dispatch, concurrency, retry, and reconciliation in its host language. The role taxonomies that do exist (stokowski's stage prompts, itervox's profiles) are **outside** the harness, selected by the orchestrator before it spawns a single-agent session — not subagents the session delegates to.

That is a design fork, not an oversight: these are *daemons* that outlive any session, and Claude Code's team primitives live inside one. A Claude Code agent team borrowing from symphony inherits its **role taxonomy, gating, and handoff discipline**; it does not inherit the daemon, and it should not expect the ports to have solved in-session delegation, because none of them attempted it.

## 4. Caveats on this report

- Every claim above carries a `path:line` in a named commit or a URL. Claims I could not verify are labelled **UNVERIFIED** inline (two: hatice's characterization of symphony's tracker/MCP support, and itervox's L3 conformance against `vnovick/orchestrated-coding`, which I did not audit).
- Absence claims (no role taxonomy in symphony/hatice; no self-improvement loop; no Claude Code team primitives in any port; no `--resume` in phonyhuman) were each run with a **control arm** whose output is printed alongside. No absence is reported on an unarmed probe.
- Star counts, issue counts and push dates are a single snapshot at **2026-08-04T21:42Z** via `gh api`.
- I read symphony deepest (full `SPEC.md`, `WORKFLOW.md`, skill frontmatter, tree). For the ports I read READMEs, workflow/config files, and the specific source files cited; I did **not** read every source file in itervox (839 blobs) or hatice (84).
- The `graphify query` PreToolUse reminder fired on every Bash call in this run. It is scoped to *this* repo's graph; all greps here ran against external repos cloned into the scratchpad, which that graph does not cover.

## GitHub repos touched

- [openai/symphony](https://github.com/openai/symphony) — the reference design: read `SPEC.md` in full, `README.md`, `elixir/WORKFLOW.md`, `elixir/README.md`, and all seven `.codex/skills/*/SKILL.md` frontmatter blocks, at commit `f8e8b8a`.
- [Sugar-Coffee/stokowski](https://github.com/Sugar-Coffee/stokowski) — Python port with the only stage/gate state machine and role prompts; read `README.md`, `stokowski/{runner,config,tracking}.py`, `prompts/*.example.md`, at commit `6e51bdf`.
- [mksglu/hatice](https://github.com/mksglu/hatice) — TypeScript port on the Claude Agent SDK; read `README.md`, `WORKFLOW.md`, `package.json`, `src/{agent-runner,agent-spawn,config}.ts`, at commit `389627c`.
- [manav03panchal/phonyhuman](https://github.com/manav03panchal/phonyhuman) — hard fork of symphony's Elixir with a Codex-protocol shim; read `README.md`, `claude-shim.py`, `demo.toml`, and the full file tree at `HEAD`.
- [vnovick/itervox](https://github.com/vnovick/itervox) — Go implementation with `SOUL.md`/`INSTRUCTIONS.md` agent profiles, automations, SSH fleet, and agent evals; read `README.md`, `WORKFLOW.md`, `docs/skills-inventory.md`, `internal/profiles/builtin/merge-bot/{SOUL,INSTRUCTIONS}.md`, `internal/evals/fixtures/README.md`, and the full 839-path tree at `HEAD`.
- [vnovick/orchestrated-coding](https://github.com/vnovick/orchestrated-coding) — referenced by itervox as the tiered spec it conforms to at L3; **cited only, not read** — the L3 claim is UNVERIFIED here.
- [emdash-sh/emdash](https://www.emdash.sh/) — named in stokowski's comparison section as the interactive-GUI alternative; not fetched, listed for completeness of provenance.
