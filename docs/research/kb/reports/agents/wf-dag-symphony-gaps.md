# Gap analysis — our autonomous-DAG sketch vs openai/symphony SPEC.md and its ports

**Agent:** wf-dag-symphony-gaps
**Date:** 2026-08-05
**Harness:** `claude --version` → **`2.1.222 (Claude Code)`**
**Branch:** `research/wayfinder-autonomous-dag` (repo writes allowed; no commits, no pushes)

> STATUS: complete.

## Versions audited

| Artifact | Version | Fetch / control arm |
|---|---|---|
| `openai/symphony` `SPEC.md` (2,311 lines) | HEAD **`f8e8b8a670c799f6e0ade7a8c25c4bf4a4a56ec7`**, committed 2026-07-24T17:56:43Z | `raw.githubusercontent.com/openai/symphony/main/SPEC.md` → **200**, 2,311 lines; control (freshly-invented bogus path `qvzzrt-nosuch.md`) → **404**, 0 bytes. The probe discriminates. |
| `openai/symphony` `README.md` (41 l), `elixir/WORKFLOW.md` (329 l) | same commit | 200 / 200 |
| our sketch — `docs/agent-team.md` | 772 lines, `main` @ `ff3b9e3`, incl. the 2026-08-05 correction block | local |
| our sketch — `docs/specs/agent-team-first-slice.md` | 334 lines; issue **#550** is the canonical tracker entry | local |
| prior survey — `symphony-and-ports.md` | 693 lines, measured 2026-08-04 against the **same** symphony commit | local |
| harness ledger — `.claude/agents/claude-code-expert.md` | 274 lines, 47 rows, all at 2.1.222 / 2026-08-05 | local |
| installed binary | `~/.local/share/claude/versions/2.1.222` (271,289,792 bytes) | byte-scanned with `python3` + regex per the ledger's hazard note |

**The prior survey is not stale.** It read symphony at `f8e8b8a`; `gh api repos/openai/symphony/commits/main` returns the same SHA today. Every line anchor it recorded still resolves, so this report *builds on* it. The no-role-taxonomy finding is settled and is not re-litigated.

---

## 0. Headline

**Our sketch calls its edges a "push". The harness implements them as a 1 Hz poll of a per-agent mailbox. So the push/pull question is already answered by the substrate — and answered symphony's way.**

The real gap is not push-vs-pull. It is **what gets polled**: a *mailbox* (delivery of a message to one named agent) versus a *work queue* (selection of the next eligible ticket by a scheduler). Symphony polls the second. We currently poll neither, because our sketch has no loop at all.

Four consequences, each measured below:

1. **`SendMessage` delivery is a poller, not a push** — `[InboxPoller]`, `EYT=1000` ms interactive, `await _r(500)` headless. §1.
2. **A headless node cannot wait for an inbound edge.** The headless poll loop breaks on *"No more active teammates, stopping poll"* — so a durable background-session node that finishes and waits for a sibling's message **exits instead of waiting**. §1.3. This kills the "edges = SendMessage between durable nodes" shape as written.
3. **We already own symphony's database and are routing around it.** `CLAUDE_CODE_TASK_LIST_ID` is persistent, file-locked, cross-session with native `blocks`/`blockedBy` (ledger, CONFIRMED). Symphony's whole architecture is *"the tracker is the database; the orchestrator holds nothing durable"* (`SPEC.md:57-58`, `:1689-1704`). §2.
4. **The harness ships the missing scheduler primitives and our sketch names none of them** — `CronCreate` (22 occurrences), `TaskStop` (23), `Monitor`, plus a live `createCronScheduler` wired into headless mode. §5.

And one hard divergence to state up front: **symphony would reject our DAG.** *"The orchestrator MUST NOT … branch on provider-specific blocker, board, transition, or comment semantics"* (`SPEC.md:1242-1243`); `blocked_by` is *"Best-effort provider metadata"* (`:188-193`) and graph reasoning is pushed into the adapter's boolean `dispatchable` flag (`:1279-1280`). Symphony parallelises across *independent tickets only*. Every mechanism it specifies is sized for a flat priority queue. We want a dependency graph — so we inherit its **lifecycle** mechanisms, not its **selection** mechanism.

---

## 1. The user's question: PULL from tracker-generated tickets vs our PUSH/SendMessage

### 1.1 What symphony specifies

The loop is stateless and re-derives everything every tick (`SPEC.md:735-749`):

> Tick sequence:
> 1. Reconcile running issues.
> 2. Run dispatch preflight validation.
> 3. Fetch candidate issues from tracker using active states.
> 4. Sort issues by dispatch priority.
> 5. Dispatch eligible issues while slots remain.
> 6. Notify observability/status consumers of state changes.

Cadence `polling.interval_ms`, default `30000` (`SPEC.md:406-407`); the reference workflow sets `5000` (`elixir/WORKFLOW.md:18-19`).

Three properties make this a *pull*, and all three are load-bearing:

- **Nobody is told anything.** No component notifies the orchestrator that work exists. Eligibility is a predicate re-evaluated against the tracker every tick — 8 conjunctive conditions at `SPEC.md:754-772`.
- **The orchestrator is the single mutator.** *"The orchestrator is the only component that mutates scheduling state. All worker outcomes are reported back to it and converted into explicit state transitions."* (`SPEC.md:637-638`); *"serializes state mutations through one authority to avoid duplicate dispatch"* (`:727`).
- **Crash recovery is free.** *"Restart recovery is tracker-driven and filesystem-driven (without a durable orchestrator DB)"* (`SPEC.md:731`); after restart, *"No retry timers are restored… Service recovers by: startup terminal workspace cleanup / fresh polling of active issues / re-dispatching eligible work"* (`:1689-1704`). Losing the whole orchestrator loses nothing, because the tracker holds the truth.

### 1.2 What our sketch says, and what the harness actually does

Our sketch: *"edges = SendMessage to named peers"*, *"durable nodes = background sessions"*.

**MEASURED — `SendMessage` delivery is a poller.** Binary 2.1.222, byte-scanned:

| Token | Count |
|---|---:|
| `readMailbox` | 10 |
| `writeToMailbox` / `readUnreadMessages` | present (module export map @ 246903198) |
| `deliverMessage` | **0** |
| `pollMailbox` | **0** |
| `watchMailbox` | **0** |
| `setInterval` (control, known-present) | 140 |
| `qzzxvv7fresh` (freshly-invented control, known-absent) | **0** |

The control returns 140 and the invented token returns 0, so token-existence discriminates. `readMailbox` is a plain file read with no watcher:

```js
async function HXe(e,t){let r=A4t(e,t);C(`[TeammateMailbox] readMailbox: path=${r}`);
  try{let n=await ps().read(r),{valid:o,droppedCount:i}=_Ld(jt(n),r); … }
  catch(n){if(Ft(n)==="ENOENT")return C("[TeammateMailbox] readMailbox: file does not exist"),[]; … }}
```
— binary @ byte 246903198

Its consumer `R4t` (`readUnreadMessages`) has exactly **3 call sites**. Site 1 is the interactive UI loop, and the harness's own log tag is literally `[InboxPoller]`:

```js
let T=await R4t(b,y.teamContext?.teamName);
if(T.length===0)return;
C(`[InboxPoller] Found ${T.length} unread message(s)`);
…
if(!t&&!r){ C("[InboxPoller] Session idle, submitting immediately"), … }
else C("[InboxPoller] Session busy, queuing for later delivery"), V();
```
— binary @ 259929013

The interval is a self-rescheduling `setTimeout` chain, `pu(h, m?EYT:null)`, with:

```
EYT=1000
function pu(e,t,r){ … let d=()=>{if(c)return;try{n.current()}finally{if(!c)u=o.setTimeout(d,t)}};
  return u=o.setTimeout(d,t), … }
```
— binary @ 244584811

**Control arm for "no watcher"**: the binary *does* ship filesystem watchers — `chokidar` **7**, `FSWatcher` **7**, `watchFile` **29**, `fs.watch` **3**. A watcher-shaped probe can therefore find one. In the 10 KB region containing the mailbox module and `getInboxPath`, `watch` returns **0** against a control of **2** `inboxes` hits in the same region. So the mailbox is genuinely poll-only, not watched.

**This resolves a disagreement between two corpora** — exactly the cross-check the repo's rules ask for. `$CC/agent-teams.md:275` says *"**Automatic message delivery**: when teammates send messages, they're delivered automatically to recipients. The lead doesn't need to poll for updates."* That is true from the **operator's** point of view and false as a description of the mechanism: the lead does not poll *by hand* because the harness polls for it, once a second. Per the three-corpus rule the binary wins. It also independently re-confirms ledger row *"mailboxes are pull-only, no watcher"* by a second route (that row was derived from a 25-verb shape enumeration; this one from the call-site chain and the interval constant).

**Verdict: the push/pull framing is a false dichotomy. There is no push in this harness. Our "push" is a poll of the wrong queue.**

### 1.3 The finding that breaks the sketch as written — CONFIRMED

Call site 2 of `R4t` is the **headless** (`print.ts`) loop, i.e. the mode a background-session node runs in:

```js
while(!0){
  let so=a();
  if(!(OMt(so)||PMt(so.teamContext))){
    C("[print.ts] No more active teammates, stopping poll"); … break; }
  let Ha=await R4t("team-lead",so.teamContext?.teamName);
  if(Ha.length>0){ C(`[print.ts] Team-lead found ${Ha.length} unread messages`) … }
  if(O&&ig()){C("[print.ts] Input closed with active teammates, injected shutdown prompt");return}
  yt(),await _r(500)
}
```
— binary @ 260785487

Three facts, each with a direct design consequence:

| Measured | Consequence for our sketch |
|---|---|
| Poll cadence is **500 ms** headless (vs 1,000 ms interactive) | fine; not the problem |
| The inbox read is **hardcoded to `"team-lead"`** | in headless mode the loop drains only the lead's mailbox. A non-lead node has no equivalent drain loop in this code path |
| The loop **breaks** when `!(OMt(so)‖PMt(so.teamContext))` — logged *"No more active teammates, stopping poll"* | **a headless node that has no active teammates stops polling and the session ends.** It cannot sit idle awaiting an inbound edge from a sibling node |

So "durable nodes = background sessions, edges = SendMessage" has a liveness hole: **the receiver must already be busy to receive.** A node that finishes its stage and waits to be handed the next one terminates instead. This is the same class of failure the repo has already hit three times — *"2 died + 1 idled without reporting"* — but here it is structural, not a discipline problem.

Symphony has no such hole *because it never delivers to a waiting worker*. A worker is created when work is selected, and it exits when done; waiting is the scheduler's job, and the scheduler's waiting state is a row in the tracker, not a live process.

### 1.4 The mapping, stated plainly

| | symphony | our sketch as written | what the substrate supports |
|---|---|---|---|
| Who initiates | scheduler pulls from tracker | upstream node pushes to named peer | receiver polls its own mailbox at 1 Hz |
| Where "next work" lives | tracker row (durable, survives everything) | in the message (ephemeral, in a JSON file with no reader unless a session is running and busy) | task list (durable, file-locked, cross-session) — **unused by the sketch** |
| Cost of losing the coordinator | zero; re-derive next tick | the whole graph; edges in flight are lost | zero *if* state is in the task list |
| Waiting node | not a process — a tracker state | a live process that must stay busy to receive | **cannot wait**; headless poll loop exits |

**Recommendation, and it is the report's main one: invert the edge direction.** Keep `SendMessage` for *escalation upward* (which is the one thing a subagent can do and cannot do any other way — `AskUserQuestion` is unconditionally absent, ledger CONFIRMED), and make *work selection* a pull: a node, on start, reads the task list, finds the first task whose `blockedBy` set is satisfied, claims it, and works it. That is symphony's loop with `blockedBy` promoted from best-effort metadata to the selection predicate — which is precisely the one place symphony forbids, and the one place our design needs.

---

## 2. Mechanism-by-mechanism gap table

Enumerated **by shape from the spec's own structure** (§6–§15 headings plus the §18.1 conformance list at `SPEC.md:2211-2231`), not from an expected list.

Legend: **HAVE** · **PLANNED** (named ticket) · **MISSING** (proposed ticket / fog) · **REJECTED** (our evidence rules it out) · **DIVERGE** (deliberate departure).

### A. Scheduler loop

| # | Mechanism (spec anchor) | Status | Notes |
|---|---|---|---|
| A1 | **Poll tick on a fixed cadence**, `polling.interval_ms` default `30000` (`SPEC.md:735-741`, `:406-407`) | **MISSING** → propose ticket | We have no loop. The harness *has* one (`[InboxPoller]`, §1) but it polls a mailbox, not a work queue. `CronCreate` is the native tick (§5). |
| A2 | **Tick ordering: reconcile → preflight → fetch → sort → dispatch** (`SPEC.md:742-749`); *"If per-tick validation fails, dispatch is skipped… but reconciliation still happens first"* (`:751-752`) | **MISSING** → propose ticket | The ordering is the mechanism: reconcile-first means a stale run is killed before new work is created. |
| A3 | **Dispatch preflight validation, per tick** (`SPEC.md:580-604`) | **PLANNED (partial) — #550** | #550's `find_violations()` is exactly a preflight, but it is an **hk step at commit time**. Symphony re-validates *before every dispatch cycle* and keeps reconciliation alive when it fails. Gap: no runtime revalidation. |
| A4 | **Candidate selection predicate** — 8 conjunctive conditions incl. `dispatchable`, `required_labels`, not-running, not-claimed, global + per-state slots (`SPEC.md:754-772`) | **MISSING** → propose ticket | The core of the pull loop. Ours must add "every `blockedBy` is Done". |
| A5 | **Flat priority sort** — `priority` 1..4 asc, `created_at` oldest, `identifier` lexicographic (`SPEC.md:771-776`) | **DIVERGE** | We need a topological order. Symphony's sort is deliberately graph-blind. |
| A6 | **Single-authority state mutation** (`SPEC.md:637-638`, `:727`) | **MISSING**, and the push sketch **violates** it | With SendMessage edges every node mutates scheduling state. This is the structural argument for a pull loop independent of the liveness hole in §1.3. |

### B. Claims and concurrency

| # | Mechanism | Status | Notes |
|---|---|---|---|
| B1 | **Claim states** `Unclaimed` / `Claimed` / `Running` / `RetryQueued` / `Released` — internal, distinct from tracker states (`SPEC.md:645-660`) | **MISSING** → propose ticket | Nearest native: the task list's own status field. Its exact enum is **NEEDS-PROBE** — I did not enumerate it. Note symphony's claim state is *in-memory* precisely because it is reconstructible; ours can be durable for free. |
| B2 | **Global concurrency cap** `agent.max_concurrent_agents` = 10 (`SPEC.md:448-450`, `:781`) | **HAVE** (different mechanism) | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` = 20, workflow runtime 16/run. ⚠️ ledger: the cap comes from an **undocumented remote feature gate** when the env var is unset — pin it. |
| B3 | **Per-state concurrency** `max_concurrent_agents_by_state` (`SPEC.md:458-461`, `:783-786`) | **MISSING** → propose ticket | The most transferable knob in the spec: "at most 2 tickets in `Merging`" ≙ "at most 1 node in `implement`". No native equivalent — the harness caps agents globally, never by stage. |
| B4 | **Turn cap** `agent.max_turns` = 20 (`SPEC.md:451-453`) | **HAVE** | `maxTurns` frontmatter; `CLAUDE_CODE_MAX_TURNS` (the one numeric var rejected at startup rather than silently defaulted). |

### C. Workspace lifecycle

| # | Mechanism | Status | Notes |
|---|---|---|---|
| C1 | **Per-issue deterministic workspace, reused across runs; success does NOT auto-delete** (`SPEC.md:863-866`) | **PLANNED (partial) — #550** | `isolation: worktree` is the analogue. ⚠️ `worktree.baseRef` defaults to `"fresh"` = `origin/<default-branch>`, so a node on a feature branch gets a tree **without the branch's commits** (agent-team.md §8). #550 lists setting it as a prerequisite. |
| C2 | **Three safety invariants**: cwd == workspace; path under root (normalized prefix check); key sanitized to `[A-Za-z0-9._-]` + ≥64-bit hash suffix on change (`SPEC.md:928-948`, called *"the most important portability constraint"* at `:930`) | **HAVE** on the subagent path | **REJECTED for the teammate path**: ledger CONFIRMED — *"Teammates get **zero** worktree isolation"*, and `$CC/agent-teams.md` warns *"Two teammates editing the same file leads to overwrites."* Another reason the design must stay on the subagent/workflow path. |
| C3 | **Four workspace hooks** `after_create` / `before_run` / `after_run` / `before_remove`, `hooks.timeout_ms` default `60000`, **with per-hook fatality**: `after_create` fatal to creation, `before_run` fatal to the attempt, the other two logged-and-ignored (`SPEC.md:903-927`) | **MISSING** (asymmetrically) → propose ticket | Our nearest pair is inverted. `SubagentStart` **cannot block** (`$CC/hooks.md:2029`, `:727`) so we cannot have a fatal `before_run`; `SubagentStop` **can** block (measured) so we can have a hard `after_run` — the opposite of symphony's fatality assignment. Design around it, don't assume parity. |
| C4 | **Startup terminal-workspace cleanup sweep** (`SPEC.md:841-850`) | **MISSING**, and we have a measured leak | Ledger, REFUTED: docs claim team dirs are cleaned at session end — *"they are not (8 stale dirs on this host)"*. Symphony's answer is a startup sweep driven by terminal tracker states; ours would be driven by Done tasks. |

### D. Reconciliation, failure and recovery

| # | Mechanism | Status | Notes |
|---|---|---|---|
| D1 | **Reconciliation every tick, before dispatch** (`SPEC.md:729`, `:819-839`) — terminal state ⇒ terminate + clean; active-and-routable ⇒ refresh snapshot; active-but-unroutable *or* neither ⇒ terminate **without** cleanup; refresh failure ⇒ keep workers, retry next tick | **MISSING** → propose ticket | The single biggest structural gap. It is also what makes "change the tracker state" a **kill signal** (`SPEC.md:1711-1714`) — the operator's only lever besides config. |
| D2 | **Stall detection** — `elapsed_ms` since last agent event > `codex.stall_timeout_ms` (default `300000`) ⇒ kill + retry; `<= 0` disables (`SPEC.md:825-829`, `:489-491`) | **MISSING** → propose ticket | No harness equivalent for a wedged agent. Directly relevant: this repo's rule `long-running-command-hangs.md` exists because a 7-hour 0%-CPU hang went unnoticed. `TaskStop` (§5) is the kill primitive. |
| D3 | **Turn timeout** `codex.turn_timeout_ms` default `3600000`; `read_timeout_ms` `5000` (`SPEC.md:150-152` cheat-sheet rows) | **NEEDS-PROBE** | Two ports had to add a per-turn deadline (hatice `AbortController`, itervox). Whether the harness bounds a single subagent turn by wall clock is unprobed. |
| D4 | **Exponential backoff** `delay = min(10000·2^(attempt-1), agent.max_retry_backoff_ms)`, cap default `300000` (`SPEC.md:800-801`, `:455-457`) | **MISSING** → propose ticket | Our sketch names *"retry cap exhausted"* as an escalation trigger but specifies no backoff and no cap value. |
| D5 | **Continuation retry after a CLEAN exit** — fixed `1000` ms, because *"A successful worker exit does not mean the issue is done forever"* (`SPEC.md:662-674`, `:799`) | **MISSING**, and conceptually important | Symphony re-dispatches on **success**. Our sketch treats an agent's completion as the edge trigger. Symphony's model — success means "re-check whether it's still active" — is what makes a stage that needs three passes work without anyone modelling three passes. |
| D6 | **Distinct terminal reasons**: `Succeeded` / `Failed` / `TimedOut` / `Stalled` / `CanceledByReconciliation`, because *"retry logic and logs differ"* (`SPEC.md:680-692`) | **MISSING** → propose ticket | We have one signal: the agent ended. Ledger, relevant: *"failed subagents leave the `/tasks` list while completed ones persist"* — the list is success-biased and cannot be used to audit failures. |
| D7 | **Failure-class taxonomy** — 5 classes (workflow/config, workspace, agent session, tracker, observability) (`SPEC.md:1635-1667`) | **MISSING** (low priority) | Useful as a checklist for what an escalation gate must distinguish. |
| D8 | **Recovery behaviour** — dashboard/log failures *"Do not crash the orchestrator"* (`SPEC.md:1686-1687`); candidate-fetch failure skips the tick | **HAVE (principle)** | Already our posture: `hook_guard` fails open on its own errors and records every fail-open. Same doctrine, arrived at independently. |
| D9 | **Restart recovery is tracker + filesystem driven, no DB** (`SPEC.md:57-58`, `:731`, `:1689-1704`) | **MISSING — and this is the free win** | We have the durable store (`CLAUDE_CODE_TASK_LIST_ID`, ledger CONFIRMED: persistent, file-locked, cross-session, native `blocks`/`blockedBy`, control-armed with a different id returning EMPTY). Symphony proves you need nothing else. Our sketch names it as the "DAG substrate" and then never uses it for recovery. |

### E. Human attention

| # | Mechanism | Status | Notes |
|---|---|---|---|
| E1 | **Exactly two human gates** — `Backlog`→`Todo` entry (`elixir/WORKFLOW.md:124`, `:279`) and `Human Review`→`Merging` approval (`:246-249`); everything between unattended (`:69`) | **HAVE (aligned)** | Our sketch: one human gate at the interview→spec boundary, plus dynamic escalation. Same shape, entry gate moved earlier. |
| E2 | **Normative anti-stall rule**: *"Approval requests and user-input-required events MUST NOT leave a run stalled indefinitely"* (`SPEC.md:1073-1075`) | **MISSING as a rule; forced by the substrate anyway** | Ledger CONFIRMED: *"Nothing gives a subagent a way to ASK"* — `AskUserQuestion` unconditionally filtered, `SendUserMessage` absent from a subagent's tool list. So our agents cannot stall on a question; they can only stall silently. Write the rule anyway, because the *failure* mode it prevents is ours. |
| E3 | **Reference posture: user-input-required = HARD FAILURE** (`SPEC.md:1077-1081`) vs itervox's `input_required` as a first-class pausable state that resumes in the same session | **symphony's posture is the one our substrate supports** | itervox's pause-and-wait requires a process that can idle and be woken. §1.3 measured that a headless node **cannot** — it exits. So "escalate and die, let the scheduler re-dispatch" is the right posture here, and it is symphony's. |
| E4 | **Escape hatch is narrow and asymmetric** — a missing non-GitHub tool/auth ⇒ move to `Human Review` with a blocker brief, but *"GitHub is **not** a valid blocker by default"*; exhaust fallbacks and document them first (`elixir/WORKFLOW.md:187-197`) | **MISSING** → propose ticket | Our sketch's escalation triggers (retry cap, spec mismatch, flagged ambiguity) have no such asymmetry. Without one, "flagged ambiguity" becomes an unbounded escape hatch. |
| E5 | **Operator intervention points** — edit config (hot-reloaded) or change tracker state; restart is *not* the normal path (`SPEC.md:1705-1717`) | **PARTIAL** | Config half is **HAVE**: ledger CONFIRMED — `~/.claude/settings.json` **is** watched and reaches every session on the machine within a tick. Tracker-state-as-kill-signal is **MISSING** (needs D1). |

### F. Configuration and prompt contract

| # | Mechanism | Status | Notes |
|---|---|---|---|
| F1 | **Repo-owned single config file, YAML front matter + prompt body** (`SPEC.md:332-354`) | **DIVERGE (correctly)** | stokowski explicitly split config from prompts, and its stated reason is our hazard verbatim: *"autonomous agent instructions in `CLAUDE.md`… bleed into your regular Claude Code sessions"* (`README.md:93`). Our roles are separate `.claude/agents/*.md` — already the better shape. |
| F2 | **Dynamic reload REQUIRED**: watch, re-apply config **and prompt** without restart, MUST NOT crash on invalid reload, keep last-known-good + operator-visible error (`SPEC.md:562-578`) | **PARTIAL / NEEDS-PROBE** | settings.json is watched (ledger CONFIRMED). Whether an invalid settings reload keeps last-known-good or degrades is **unprobed**. ⚠️ Counter-fact: agent-team.md records the **agent-type registry lags disk** — definitions created mid-session were unresolvable on the unnamed path for ~2 hours. So role hot-reload is *worse* than symphony's requirement, not better. |
| F3 | **Strict prompt rendering** — *"Unknown variables MUST fail rendering. Unknown filters MUST fail rendering"* (`SPEC.md:499-501`); inputs exactly `issue` + `attempt` (`:503-509`); render failure fails only that attempt, a workflow *file* error blocks all dispatch (`:528-532`) | **MISSING** → propose ticket (small) | We have `schema:` validating an agent's **output**; nothing validates its **input**. A brief with a silently-empty interpolation is exactly how a node does confident work on nothing. |
| F4 | **`attempt` vs `run` split** — stokowski splits symphony's single `attempt` into `run` (rework generation) and `attempt` (retry within a run), which `SPEC.md:1347-1349` names as out of core scope | **MISSING** → fold into D4 | Needed the moment a rework cycle exists, which our design has. |

### G. Observability

| # | Mechanism | Status | Notes |
|---|---|---|---|
| G1 | **Structured logs carrying `issue_id`, `issue_identifier`, `session_id`** — a REQUIRED conformance item (`SPEC.md:2229`, §13.1) | **PARTIAL** | Per-agent transcripts exist at a known path, unaffected by main-conversation compaction, retained for `cleanupPeriodDays`. Missing: a ticket id on them. Correlating a transcript to a task is currently manual. |
| G2 | **Token accounting with absolute-vs-delta discipline** — prefer absolute thread totals, *"Ignore delta-style payloads"*, track deltas against last reported totals to avoid double-counting (`SPEC.md:1418-1447`) | **MISSING** → propose ticket | Directly relevant: our `~78–85 k tokens per agent` is a single measurement, and there is **no live per-subagent token figure** (`preTokens` only appears at a compaction boundary, so an agent that never compacts reports nothing). Open question 4 in agent-team.md is exactly this. |
| G3 | **Rate-limit tracking** — *"Track the latest rate-limit payload seen in any agent update"* (`SPEC.md:1444-1447`) | **MISSING** → propose ticket, and it matters **more** for us | phonyhuman and itervox both had to add usage-cap classification once the agent was a subscription-backed CLI. Our constraint is sharper: `$CC/costs.md:128` — *"These windows are shared across all models, so switching models with `/model` doesn't restore access."* A DAG that hits the weekly cap mid-run with no rate-limit state has no way to resume sanely. |
| G4 | **Runtime snapshot / monitoring interface** (`SPEC.md:1389-1409`, OPTIONAL but RECOMMENDED) | **MISSING** → propose ticket | agent-team.md open question 6 (*"Observability — the field's loudest warning, and we have nothing designed for it yet"*). itervox is the only port that reaches a Claude-Code-specific surface for this (`CLAUDE_CODE_LOG_DIR` fleet logs). |

### H. Security

| # | Mechanism | Status | Notes |
|---|---|---|---|
| H1 | **Never pass tracker secrets to the child** — the orchestrator executes provider-native tools host-side with its own credential and hands the child results (`SPEC.md:1107-1111`, `:1309-1319`, `:1747-1755`) | **REJECTED-BY-EVIDENCE** | Unreachable here by a deliberate decision: `.claude/rules/secrets-out-of-the-shell-env.md` — reversed 2026-08-02, **all 50 credentials `env = true`**, inherited by every terminal, agent and MCP server. Symphony's credential boundary cannot be built on this host without reversing a user ruling. Do not design around it; design around its absence (rule 7: print presence, never a value). |
| H2 | **Hook script safety** (`SPEC.md:1759-1769`) | **HAVE** | `hook_guard`, `branch_guard`, `hook_selfcheck` gate in ship/land. |
| H3 | **Trust boundary: high-trust environments only** (`SPEC.md:1720-1732`) | **HAVE (aligned)** | Same posture; symphony is marked *"a low-key engineering preview for testing in trusted environments"* (`README.md:10-11`). |

### I. Mechanisms the PORTS added that symphony lacks

| # | Mechanism (port) | Status | Notes |
|---|---|---|---|
| I1 | **Typed states `agent` / `gate` / `terminal`** with per-state `runner`, `model`, `max_turns`, `turn_timeout_ms`, `stall_timeout_ms`, `permission_mode`, `allowed_tools`, `hooks`, `transitions`, `rework_to`, `max_rework` (stokowski `config.py:101-120`, validated `:633-645`) | **PLANNED (partial) — #550** | #550 has the `gate` node and per-stage `model:`. The per-state **timeouts** and `max_rework` are not in it. |
| I2 | **`rework_to` can target ANY earlier state** ⇒ the graph admits cycles (stokowski `README.md:180`) | **MISSING** → decision needed | Our sketch says DAG. A rework edge makes it a cyclic graph. `blockedBy` cannot express "go back to research"; that needs a new task, or a status transition. Name the choice. |
| I3 | **Machine-readable state in tracker comments for crash recovery** — `<!-- stokowski:state {...} -->` / `:gate` parsed back (`tracking.py:13-14`) | **MISSING** → propose ticket | Our native analogue is task-list metadata, which is strictly better (file-locked, typed). This is the port's workaround for not having one; we have one. |
| I4 | **`max_rework` with automatic escalation** (stokowski `README.md:181`) | **PLANNED (unnumbered)** | Our sketch's "retry cap exhausted" escalation. Needs an actual number and a distinct terminal reason (D6). |
| I5 | **Cold review enforced structurally** — `session: fresh` + `runner: codex` (a different model family) (stokowski `README.md:656-663`) | **PLANNED — #550** | The `adversarial-reviewer` role. Note: #550 keeps it on the subagent path, which is right — a teammate would drop its `skills`/`mcpServers`/`hooks`. |
| I6 | **Three-layer prompt assembly** — global + stage + **auto-injected lifecycle** (issue metadata, rework context, recent comments, available transitions); *"Prompt authors never need to write 'move the issue to Human Review when done'"* (stokowski `README.md:200-205`) | **MISSING** → propose ticket | The lifecycle layer is the interesting third. It is where the branch precondition would go — which is exactly the thing `SubagentStart` **can** do (inject context) and cannot do (block). Good fit. |
| I7 | **Process-group kill** (`os.killpg`) *"catching grandchild processes too"* (stokowski `README.md:234`) | **MISSING** → propose ticket | Live hazard for us: our Codex lane already *"runs detached with its own process group and a bash watchdog"* (agent-team.md §5). `TaskStop` kills a task; whether it reaps a detached `codex exec` grandchild is **NEEDS-PROBE**. |
| I8 | **`SOUL.md` (identity/refusal posture) vs `INSTRUCTIONS.md` (procedure/guards)** split (itervox `.itervox/agents/<name>/`) | **MISSING** → propose ticket (cheap, high value) | Maps ~1:1 onto a role definition's body. The split lets a role's *judgment* be versioned separately from its *checklist*. `merge-bot`'s *"A wrong merge has unbounded blast radius. A refused merge is annoying. You always prefer the annoying outcome."* is the shape we want for a gate role. |
| I9 | **Per-role capability scope `allowed_actions`** + *"The daemon issues short-lived action grants per run instead of handing the agent your dashboard API token"* (itervox `README.md:264`) | **PARTIAL / REJECTED on the teammate path** | `tools:` / `disallowedTools:` are the analogue and work on the subagent path. On the named/teammate path ten frontmatter fields are dropped and `permissionMode` is forced (ledger CONFIRMED) — so per-role scoping is *unenforceable* there. Another reason to stay unnamed. |
| I10 | **Agent evals** — `required_action_calls` / `forbidden_actions` / `marker_phrases` graded against a transcript; *"a prompt edit that changes the contract fails `make evals-fast`"* (itervox `internal/evals/fixtures/README.md:7-10`) | **PLANNED — #354** (epic: eval harness that enforces our workflow) | The only prompt-regression gate in the survey. ⚠️ Carry its own caveat verbatim: *"The recordings here are **hand-authored behavioral contracts**, not captures of real agent runs… They do NOT prove the current SOUL/INSTRUCTIONS actually produce these transcripts."* An eval built the same way is a fixture with no control arm. |
| I11 | **Decomposition pushed UPSTREAM into a planning agent emitting `blockedBy` chains** (phonyhuman `prd` skill, `README.md:82-96`) — *"Dependencies are respected — blocked issues wait."* (`:48`) | **HAVE (this IS our design)** | Strong external validation: our `/to-tickets` → task-list `blocks`/`blockedBy` is the same move, and it is how you get a DAG **without teaching the scheduler about graphs**. Note what phonyhuman keeps: the orchestrator still never reasons about the graph; the *adapter's* `dispatchable` flag does (`SPEC.md:1279-1280`). Our equivalent of `dispatchable` is "every `blockedBy` is Done" — one predicate, evaluated at selection. |
| I12 | **Worktree mode** for fast workspace creation (phonyhuman `README.md:151-153`) | **HAVE** | `isolation: worktree` (and `remote`, ledger). |
| I13 | **Auto-respond to agent input requests** (hatice `input-handler.ts`, `claude.autoRespondToInput`) | **REJECTED-BY-EVIDENCE** | Nothing to respond to: a subagent has no way to ask (ledger, two independent probes). |
| I14 | **Strip `CLAUDECODE` from the child env** so an agent can spawn Claude from inside a Claude session — found independently by **two** ports (hatice `agent-runner.ts:159-161`, phonyhuman `claude-shim.py:427-428`) | **HAVE, inverted — and it creates a trap for our DAG substrate** | Ledger CONFIRMED: *"In `exec` background-launch mode the child's env is stripped of EVERY `CLAUDE_*`"* except `CLAUDE_JOB_DIR`, `CLAUDE_CONFIG_DIR`, `CLAUDE_BG_PTY_AUTH`. **So `export CLAUDE_CODE_TASK_LIST_ID=…` will NOT reach a background-session node.** It must be set in the settings `env` block. This is a concrete, shippable ticket and a silent-failure waiting to happen. |
| I15 | **Fleet Logs** — full subagent tree via `CLAUDE_CODE_LOG_DIR` (itervox `README.md:299`) | **MISSING** → fold into G4 | The only port-side use of a Claude-Code-native observability surface. |
| I16 | **Harness capability inventory** — skills/plugins/MCP/hooks/instructions scan with `BLOATED_PROFILE`, `LARGE_CONTEXT`, `INSTRUCTION_SHADOWING`, `ORPHAN_MCP` rules (itervox `docs/skills-inventory.md:11-44`) | **PARTIAL — HAVE the need, tickets exist** | We already have #283 (15 unscoped rules ≈ 16k tok/session), #538 (8 unused plugins ≈ 1.7k tok), #476 (memory curation). itervox generalised these into *static analyzer rules*. Worth borrowing the framing: our per-agent context cost is multiplied by team size, and `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` means every agent inherits **three repos'** rule sets. |

---

## 3. Where symphony's answer conflicts with a measured harness fact

Six, each with the measurement that settles it.

| # | Symphony's answer | Measured harness fact | Resolution |
|---|---|---|---|
| 1 | A **polling daemon** external to the agent | The harness **is** a poller — `[InboxPoller]`, `EYT=1000` interactive / `_r(500)` headless — but it polls a **mailbox**, not a work queue; and there is **no watcher** (control-armed: `chokidar` 7 / `FSWatcher` 7 in the binary, **0** in the mailbox module vs control `inboxes` 2 in the same region) | Not a conflict — a **scope mismatch**. Build the work-queue poll; do not build a message bus. |
| 2 | A worker **waits** in a tracker state; the process does not idle | A headless node **cannot idle awaiting an edge** — *"[print.ts] No more active teammates, stopping poll"* then `break` | Symphony wins outright. Waiting must be a task-list row, never a live process. |
| 3 | The orchestrator **kills** a stalled or reconciled-out worker (`SPEC.md:825-829`, `:832-836`) | `TaskStop` exists (23 occurrences, binary) — but whether it reaps a **detached `codex exec` grandchild** is unprobed | **NEEDS-PROBE.** Two ports independently needed process-group kill (I7). |
| 4 | Config **and prompt** hot-reload without restart, MUST NOT crash on invalid reload (`SPEC.md:562-578`) | settings.json **is** watched machine-wide (ledger). But the **agent-type registry lags disk** — mid-session definitions unresolvable for ~2 h (agent-team.md) | Partial conflict: role hot-reload is *worse* than the spec requires. Create role files, then start a fresh session. |
| 5 | The child **never sees a tracker credential** (`SPEC.md:1107-1111`, `:1747-1755`) | All 50 credentials are `env = true` in every shell and every agent, by an explicit user decision (2026-08-02) | **REJECTED-BY-EVIDENCE.** Symphony's boundary is unreachable here. Substitute rule 7 discipline (presence flags, never values) — the blast radius is 12.5× what the original posture assumed. |
| 6 | `user-input-required` is a **hard failure** in the reference posture (`SPEC.md:1077-1081`); itervox instead pauses and resumes in-session | A subagent **cannot ask at all** (ledger, two probes: `AskUserQuestion` unconditionally filtered; `SendUserMessage` absent from its tool list) | Symphony's posture is forced. itervox's is unbuildable. Escalation = `SendMessage` upward + terminate; the lead owns every `AskUserQuestion`. Already item 1 of agent-team.md §10 and a #550 prerequisite. |

⚠️ **One conflict inside our own corpus, now settled.** `$CC/agent-teams.md:275` — *"Automatic message delivery… The lead doesn't need to poll for updates"* — reads as a push guarantee and is not one. Per the three-corpus rule the binary wins: delivery is a 1 Hz poll, and it is queued rather than delivered while the session is busy (*"[InboxPoller] Session busy, queuing for later delivery"*). Anyone reading only the docs would design a push architecture on a poll substrate.

---

## 4. What the harness already ships that our sketch never names

Probed in the binary, control-armed with the freshly-invented token `zzkkwq9never` → **0**:

| Primitive | Occurrences | Symphony's counterpart |
|---|---:|---|
| `CronCreate` (+ `CronList`, `CronDelete`) | 22 | **the poll tick** (`SPEC.md:735-741`) — a scheduled wakeup is exactly `polling.interval_ms` |
| `createCronScheduler` / `isKairosCronEnabled` | 3 / 4 | live and wired into the headless path (`createCronScheduler({onFire:…})` with a `wakeupSource`, binary @ ~260787900) |
| `TaskStop` | 23 | **terminate worker** on stall or reconciliation (`SPEC.md:827`, `:832-836`) |
| `Monitor` | (tool, present) | the operator-side watch loop |
| `wakeupSource` | 16 | evidence the scheduler distinguishes *why* a session woke — the hook a reconcile-vs-dispatch tick would hang on |

**A `/loop` skill and a `schedule` skill are both installed on this machine.** So the scheduler tick — the mechanism our sketch is missing and symphony makes REQUIRED — is not something to build. It is something to wire. That is the cheapest high-value ticket in this report.

⚠️ Two caveats before designing on it: `isKairosCronEnabled()` is a **feature gate**, so availability is not guaranteed by token existence (the ledger's rule: *existence needs a count; liveness needs a call site* — I have call sites for `createCronScheduler`, but I did **not** run a live cron end-to-end). Mark the cron path **SUSPECT** until one fires.

---

## 5. Ticket implications

Ordered by leverage. None of these exists today; #550 and #354 are the only related open tickets.

**Rewrite one line of the sketch first.** *"Edges = SendMessage to named peers"* → *"Edges = `blockedBy` in the task list; `SendMessage` is for escalation upward only."* Everything below follows from that. The current phrasing describes a mechanism the harness does not have, on nodes that cannot receive it.

| Priority | Proposed ticket | Grounds |
|---|---|---|
| **P0** | **Set `CLAUDE_CODE_TASK_LIST_ID` in the settings `env` block, never as a shell export** — background-launch strips every `CLAUDE_*` except three | I14. A silent total failure of the DAG substrate; costs one line to prevent. |
| **P0** | **Node startup = a pull: read the task list, select the first task whose `blockedBy` is all-Done, claim it, work it** — replaces the push edge | §1.3, A4, A6, D9 |
| **P0** | **Reconcile-before-dispatch**: on each tick, kill runs whose task left the active set; refresh snapshots; never dispatch on a failed preflight | D1, A2 |
| **P1** | **Wire the scheduler tick to the native cron** rather than building a daemon (`CronCreate` + `createCronScheduler`) — verify one fires first | §4, A1 |
| **P1** | **Stall detection + `TaskStop`**, default 300 s; probe whether `TaskStop` reaps a detached `codex exec` grandchild | D2, I7, conflict 3 |
| **P1** | **Retry with backoff and a cap** — `min(10·2^(n-1), 300) s` — plus the `run` vs `attempt` split, and a **distinct terminal reason** per outcome | D4, D6, F4, I4 |
| **P1** | **Per-stage concurrency caps** (`max_concurrent_agents_by_state`) — the harness caps globally and never by stage | B3 |
| **P2** | **Startup sweep for orphaned workspaces / team dirs** — 8 stale dirs measured on this host, and the docs say they are cleaned | C4 |
| **P2** | **Lifecycle prompt layer** — auto-injected task metadata, rework context, available transitions, branch precondition — delivered via `SubagentStart` (which can inject but not block) | I6, C3 |
| **P2** | **Strict brief rendering**: an unresolved interpolation fails the dispatch, it does not ship an empty section | F3 |
| **P2** | **Rate-limit + token state in the run record** — the weekly window is shared across models, so a cap hit mid-DAG must be resumable | G2, G3 |
| **P2** | **Decide: is rework a cycle or a new task?** `blockedBy` cannot express "go back to research" | I2 |
| **P3** | **Split role files into identity vs procedure** (itervox `SOUL`/`INSTRUCTIONS`) | I8 |
| **P3** | **Escalation asymmetry** — enumerate what is *never* a valid blocker, mirroring *"GitHub is not a valid blocker by default"* | E4 |
| **P3** | **Observability surface** — correlate transcripts to task ids; the `/tasks` list is success-biased and cannot audit failures | G1, G4, I15 |
| — | **Fold into #354** (eval harness) — `required_action_calls` / `forbidden_actions` / `marker_phrases`, **carrying itervox's provenance caveat verbatim** | I10 |
| — | **Fold into #550** — per-state timeouts and `max_rework` are absent from the first slice | I1 |

**Two things this analysis does NOT change**: #550's role set and its validator seam are sound and orthogonal to the pull loop; and the decision to stay on the subagent/workflow path (never teammates) is *reinforced* — C2, I9 and E2 are three independent losses on the named path.

---

## 6. Claim classification

| Claim | Verdict | Route(s) |
|---|---|---|
| `SendMessage` delivery is a 1,000 ms poll of a per-agent mailbox file, no watcher | **CONFIRMED** | binary: `[InboxPoller]` tag, `EYT=1000`, `pu()` self-rescheduling `setTimeout`; control: watchers exist elsewhere in the binary (chokidar 7 / FSWatcher 7) but 0 in the mailbox module vs control `inboxes` 2 in the same region. Second route: ledger row *"mailboxes are pull-only, no watcher"*, derived independently by verb enumeration |
| A headless node stops polling and exits when it has no active teammates | **CONFIRMED** | binary `print.ts` loop @ 260785487, verbatim log string *"No more active teammates, stopping poll"* followed by `break` |
| The headless lead poll reads only the hardcoded `"team-lead"` inbox | **CONFIRMED** | same call site, literal string argument |
| `$CC/agent-teams.md:275`'s "automatic delivery, no polling" describes the operator's view, not the mechanism | **CONFIRMED** (as a corpus disagreement resolved by the three-corpus rule) | docs vs binary |
| symphony `SPEC.md` is unchanged since the prior survey | **CONFIRMED** | `gh api repos/openai/symphony/commits/main` → `f8e8b8a…`, identical to the surveyed commit; fetch control 200 vs 404 |
| The harness ships a cron scheduler usable as the poll tick | **SUSPECT** | binary: `createCronScheduler` 3, `isKairosCronEnabled` 4, `CronCreate` 22, call site in `print.ts`. **Not run live**; `isKairosCronEnabled()` is a feature gate |
| `TaskStop` reaps a detached `codex exec` grandchild | **NEEDS-PROBE** | token present (23); no behavioural probe run |
| The task list's claim-state enum covers symphony's five claim states | **NEEDS-PROBE** | not enumerated in this run |
| Whether an invalid settings reload keeps last-known-good | **NEEDS-PROBE** | not probed |
| Whether the harness bounds a single subagent turn by wall clock | **NEEDS-PROBE** | not probed; two ports had to add it |
| symphony's credential boundary is buildable here | **REFUTED** | `secrets-out-of-the-shell-env.md` — all 50 credentials `env = true` by explicit user decision, 2026-08-02 |
| itervox's pause-and-resume-in-session `input_required` is buildable here | **REFUTED** | ledger: nothing gives a subagent a way to ask; §1.3: a headless node cannot idle |

**Probe hygiene note.** Control tokens used here were invented fresh for this run — `qvzzrt-nosuch.md` (HTTP), `qzzxvv7fresh` (binary, mailbox pass), `zzkkwq9never` (binary, cron pass) — per the rule that a published control string stops discriminating. They are now published; the next run must invent its own.

---

## GitHub repos touched

- [openai/symphony](https://github.com/openai/symphony) — the spec under audit; `SPEC.md`, `README.md`, `elixir/WORKFLOW.md` re-fetched at HEAD `f8e8b8a` and read for §6–§18 mechanism shape
- [Sugar-Coffee/stokowski](https://github.com/Sugar-Coffee/stokowski) — typed states, `max_rework`, three-layer prompt assembly, process-group kill, config-out-of-CLAUDE.md rationale (cited via the prior survey's anchors, not re-fetched)
- [vnovick/itervox](https://github.com/vnovick/itervox) — `SOUL`/`INSTRUCTIONS` split, `allowed_actions` capability scope, agent evals + their provenance caveat, `input_required` state (cited via the prior survey)
- [manav03panchal/phonyhuman](https://github.com/manav03panchal/phonyhuman) — upstream decomposition into `blockedBy` chains; the `CLAUDECODE` env-strip hazard (cited via the prior survey)
- [mksglu/hatice](https://github.com/mksglu/hatice) — per-turn `AbortController` deadline, auto-respond-to-input, the `CLAUDECODE` strip (cited via the prior survey)
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed binary `2.1.222` was byte-scanned directly for the mailbox, poller, cron and `TaskStop` findings
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo this design is for; `docs/agent-team.md`, `docs/specs/agent-team-first-slice.md`, `.claude/agents/claude-code-expert.md`, issues #550 / #354 / #283 / #538 / #476
