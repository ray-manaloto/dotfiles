# Explore agent report — is there a session-liveness signal for a lease reaper? (2026-08-27, session ad30e818, #791)

Brief: is there any RELIABLE on-disk or process-level signal that a Claude Code session (by `session_id`) or a Codex session is still alive vs finished/dead — for #791 fix 4 ("reap in-flight entries whose registering session is dead"). Persisted verbatim at receipt per `.claude/rules/agent-report-persistence.md`.

---

## Report — is there a reliable liveness signal for a Claude Code / Codex `session_id`?

**Tooling caveat up front:** this session had only `Read` (no `Bash`, `Grep`, `Glob` — `ToolSearch` returned no file-search tools, and `Bash` was refused with `Writer lease denied this tool call`). So **step 4 of the brief (real on-disk enumeration of `~/.claude/sessions/*`, `*.jsonl` counts, `*.lock`, `~/.codex/sessions/**`) could not be performed.** Everything below is from the two doc corpora plus the project's verified ledger. Treat the "no lock file exists" statements as *not observed on disk here* — they are docs-and-ledger-derived and one of them (`.lock`) is explicitly `NEEDS-PROBE`.

---

### What the hook payload itself carries

`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md:700-717` — the complete Claude Code common-input table: `session_id`, `prompt_id`, `transcript_path`, `cwd`, `permission_mode`, `effort`, `hook_event_name`, plus `agent_id` / `agent_type` inside a subagent. **There is no pid, no ppid, no process handle, no start-time, no lock path.** Ledger row `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/agents/claude-code-expert.md:233` independently confirms the shape by a second route: the binary's common hook base `$m()` is *exactly 8 fields*, enumerated by shape across 64 `hook_event_name:` sites. So a hook consumer gets an opaque UUID and nothing process-level.

Codex is the same shape: `.../docs/codex/hooks.md:382-388` — `session_id`, `transcript_path` (`string | null`), `cwd`, `hook_event_name`, `model`, plus `turn_id` on turn-scoped events. No pid. Note `session_id` is a **thread id** (`"thr_123"`, `.../codex/hooks.md:537`) and `transcript_path` is explicitly nullable and explicitly **not a stable interface** (`.../codex/hooks.md:398-400`).

---

### Candidate signals, one by one

**1. `SessionEnd` firing (Claude Code).**
`hooks.md:2824-2856`. Reasons are `clear`, `resume`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` (`hooks.md:2831-2838`). Distinguishes live/dead? **Only positively, and unreliably.** Failure modes, all load-bearing: (a) the reason enum has no `crash`/`signal` member — a `SIGKILL`, a panic, or a closed terminal cannot deliver a hook from a dead process, so absence of `SessionEnd` is *not* evidence of liveness; (b) it has a **1.5-second budget** (`hooks.md:2856`) shared across all `SessionEnd` hooks, so a reaper's own write can be truncated mid-flight; (c) `clear` and `resume` fire `SessionEnd` on a session whose *process is still alive* — `/clear` ends the session id but not the harness. So `SessionEnd` is a *lossy* "dead" signal that also fires when the user is still sitting there. It has no decision control and cannot block (`hooks.md:801`, `:948`).

**2. `SessionEnd` firing (Codex).** `.../codex/hooks.md:512-547` is materially better and is the single strongest finding in this report:

> "It runs for the main thread when you archive or delete a conversation that's still open, when Codex closes normally, or **after a conversation has been idle and isn't open in any connected client for 30 minutes**."

That clause means Codex's app-server maintains a real client-subscription notion of liveness and *eventually* emits a terminal event even for an abandoned thread. But: `reason` is **always `other`** (`.../codex/hooks.md:524`, `:531`) so you cannot tell "archived" from "crashed" from "idled out"; the signal is up to **30 minutes late**; and `.../codex/hooks.md:520` warns that unsubscribing or switching away does *not* promptly end the session. It also never runs for subagents (`.../codex/hooks.md:27`, `:518`).

**3. Transcript file mtime.** `hooks.md:704`: "The transcript file is written **asynchronously and may lag** the in-memory conversation." Distinguishes live/dead? **No.** Recent mtime proves recent activity, never current liveness; stale mtime proves neither death nor idleness (a session blocked on a 40-minute subagent writes nothing). The doc's own remedy — use `last_assistant_message` on `Stop` — is a per-turn field, not a liveness probe.

**4. A pid + `kill(pid,0)`.** This is the only *mechanically sound* liveness test on the machine, and the harness itself uses it — but **only for background jobs, not for sessions.** `claude-code-expert.md:217`: liveness = `kill(pid,0)` every 5 s plus a `procStart` comparison every 60 s (`startPidPoll`/`checkPid`). The `procStart` comparison is precisely the pid-reuse defence. `claude-code-expert.md:227`: `~/.claude/daemon/roster.json` carries `pid + procStart + attempt + …` per worker, and `adopt()` returns null on a dead pid *or* a `procStart` mismatch, so stale entries are reaped rather than respawned (observed live: 3 stale workers reaped on supervisor start).

**The catch, and it is fatal for the general case:** that roster is keyed by **job id**, populated only for `--bg` / fleet workers, and the fleet is gated (`claude-code-expert.md:222` — `isAgentsFleetEnabled()`). An ordinary interactive session that fired your `PreToolUse` hook has no roster entry at all. And `claude-code-expert.md:230`: "**There is no native always-on local watchdog**" — `claude daemon` service install is disabled in this version and the supervisor exits when the last client disconnects, so even the roster is not durable.

**5. "Process gone ⇒ session dead" as an inference.** **Refuted for background nodes.** `claude-code-expert.md:216`: a background node killed with `kill -9` is **respawned automatically, same `sessionId`**, `attempt`→2, ~36 s later, conversation intact. So a dead pid under a given `session_id` can be a 36-second gap, not a death. Conversely `claude-code-expert.md:218`: a **hung** node is detected (`tengu_bg_worker_stalled` after a >120 s heartbeat gap) but **never recovered** — so a live pid can be a permanently wedged session. Liveness of the process and liveness of the session are independent in both directions.

**6. On-disk terminal state.** `claude-code-expert.md:221` is the closest thing to an authoritative "this is over" record: terminal = `state ∈ {done, failed, stopped}` **AND** `tempo ≠ "active"` **AND** no `queuedPrompt`, in `~/.claude/jobs/<id>/state.json` (`claude-code-expert.md:226`). Note `killed` and `blocked` are **not** terminal. Same scope limit as (4): job id, background only.

**7. Stale-directory / stale-file heuristics.** Actively dangerous. `claude-code-expert.md:194`: docs claim team dirs are cleaned up at session end — **they are not**, 8 stale dirs measured on this host. An orphaned artifact is the expected steady state, not a signal.

**8. A `.lock` file.** Nothing in `hooks.md`, the Codex `hooks.md`, or the ledger mentions a per-session lock. I could not check `~/.claude/*.lock` on disk. The one lock the ledger does name is unrelated in scope: `claude-code-expert.md:181`, `CLAUDE_CODE_TASK_LIST_ID` gives a "persistent, **file-locked**, cross-session task DAG" — a task-list lock, not a session-liveness lease. **Verdict: `NEEDS-PROBE`, not "absent."** Given the founding incident recorded at `claude-code-expert.md:16-45` (a correct grep, bounded to the docs, reported about the world), I will not convert "no doc mentions it" into "it does not exist."

**9. Cross-session peer discovery as a liveness oracle.** `claude-code-expert.md:183` — `SendMessage` + `ListAgents` do reach other sessions as peers, which in principle enumerates the live roster. But `claude-code-expert.md:185`: **`ListAgents` is stripped from every async agent, teammates included** — "the limit on A2A is DISCOVERY, not delivery." A reaper running as a hook subprocess has no access to either tool. Dead end.

---

### Best-supported answer for a lease reaper

**Claude Code: there is no reliable signal, and you should stop looking for one.** No hook payload field, no documented per-session lock, and no pid anywhere in the `session_id`-keyed world. The one sound mechanism (`kill(pid,0)` + `procStart`, `claude-code-expert.md:217,227`) exists only for `--bg` job ids behind a gate, is not durable across supervisor exit, and is contradicted in both directions by auto-respawn (`:216`) and undetected hangs (`:218`).

The lazy design that actually holds: **make the lease self-expiring and have the session renew it.** A `PostToolUse`/`Stop` hook touches the lease with a timestamp; the reaper harvests anything past a TTL comfortably above the longest legitimate silent stretch. That reduces the problem to one your own code owns, and it degrades correctly — a crashed session simply stops renewing. Treat `SessionEnd` as a *best-effort early release* that lets you reap sooner when it happens, never as the thing correctness depends on. Skipped: any pid/lock/process-inspection layer — add it only if TTL latency measurably hurts, and note that even then it cannot fix cases (5).

**Codex: marginally better, same conclusion.** The 30-minute no-connected-client rule (`.../codex/hooks.md:512-518`) is a genuine server-side liveness notion and will eventually fire `SessionEnd` for an abandoned thread — but with `reason` permanently `other`, up to 30 minutes of latency, no subagent coverage, and `transcript_path` nullable and explicitly unstable. Use it as an early-release optimisation on top of the same TTL.

**What none of this can prove, in either harness:** that a session which has gone quiet is *dead* rather than *hung* (Claude Code detects the hung case and deliberately does nothing about it — `claude-code-expert.md:218`), and that a session whose process is gone will *stay* gone (`:216`, auto-respawn, same `session_id`). A reaper can therefore only ever assert "**this lease has not been renewed within its TTL**" — which is a statement about the lease, not about the session. Any code or comment that upgrades that to "the session is dead" is claiming something no available signal supports.

---

## GitHub repos touched

_None._ (local KB corpus + project ledger only)
