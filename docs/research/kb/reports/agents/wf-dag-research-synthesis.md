# wf-dag research synthesis — seven parallel researchers → one revised map

**Agent:** wf-dag-research-synthesis · **Date:** 2026-08-05 · **Harness:** `claude --version` → `2.1.222 (Claude Code)`
**Branch:** `research/wayfinder-autonomous-dag` (repo writes allowed; no commits, no branch switches)
**Status:** COMPLETE — written incrementally per `.claude/rules/agent-report-persistence.md`.

## Method and scope

Seven researchers ran in parallel against the autonomous-DAG design
(`docs/agent-team.md`, `docs/specs/agent-team-first-slice.md`, issue #550). **Every report
was read in full**, not from its structured summary — three of the findings below exist
only in report bodies and never surfaced in a summary, and two of the contradictions in §9
are visible *only* when two full reports are held side by side.

| Area | Report | Bytes |
|---|---|---:|
| protocol-verbs | `docs/research/kb/reports/agents/wf-dag-protocol-verbs.md` | 17,610 |
| codex-lane | `docs/research/kb/reports/agents/wf-dag-codex-lane.md` | 43,005 |
| recovery | `docs/research/kb/reports/agents/wf-dag-recovery.md` | 53,897 |
| plugin-extraction | `docs/research/kb/reports/agents/wf-dag-plugin-extraction.md` | 27,367 |
| symphony-gaps | `docs/research/kb/reports/agents/wf-dag-symphony-gaps.md` | 47,008 |
| context-gate | `docs/research/kb/reports/agents/wf-dag-context-gate.md` | 47,046 |
| model-routing | `docs/research/kb/reports/agents/wf-dag-model-routing.md` | 44,360 |

**Reading rule applied throughout:** a claim is carried into the map only with its verdict
attached. `SUSPECT` and `NEEDS-PROBE` claims become **tickets**, never decisions. Two
reports repeat an inherited number (~78–85k tokens per agent); only one flags it as
inherited — §9 contradiction 5 handles that, and the number does **not** become a decision.

---

## 0. The headline, before the per-area detail

**The plan survives, but one sentence in it is mechanically wrong and one packaging
assumption is unachievable.**

1. **"Edges = SendMessage to named peers" describes a mechanism the harness does not have.**
   `SendMessage` delivery is a 1 Hz poll of a mailbox file with no watcher, and a headless
   node that finishes its stage **exits instead of waiting** for an inbound edge
   (symphony-gaps §1.2–1.3, binary `print.ts` loop, verbatim log string *"No more active
   teammates, stopping poll"*). Edges must become `blockedBy` in the task list; `SendMessage`
   is escalation **upward only**.

2. **The scheduler question is unblocked.** `claude -p "/to-tickets #542" < /dev/null` runs
   the genuine vendor skill, with `$ARGUMENTS`, unattended — the `disable-model-invocation`
   flag gates model-side *discovery*, not user-prompt *expansion* (protocol-verbs §1, live
   fixture, internal control arm). Option (a) is available; no human-at-the-gate workaround
   is needed and the verbs need not be forked.

3. **The watchdog largely already exists.** A `claude --bg` node killed with `kill -9` was
   respawned 36 s later with the same `sessionId` and its conversation intact
   (recovery §13, live probe on this host). What the harness does **not** do is recover a
   *hung* node — the stall detector only emits telemetry.

4. **"Plugin at extraction after proven" is only partly achievable.** A plugin `settings.json`
   is `BW().pick({agent, subagentStatusLine}).strip()` — `env`, `permissions`, `statusLine`
   and `baseRef` are discarded **with no error and no warning** (plugin-extraction §2,
   binary verbatim). The project-scoped shim is permanent, not transitional.

5. **A collision no single researcher saw.** protocol-verbs' whole route is `claude -p`;
   model-routing establishes `--bg` and `--print` are **mutually exclusive** (hard error
   since v2.1.198); recovery establishes that **`exec`-mode workers are never
   auto-respawned** — only PTY/daemon-backed `--bg` sessions get the watchdog. So the
   verb-running launch shape and the supervised launch shape are, on today's evidence,
   *different shapes*. Whether a `--bg` positional prompt gets slash expansion is
   **unprobed**, and it is now the single highest-leverage cheap probe in the plan (§9
   contradiction 1, ticket **P1**).

---

## 1. protocol-verbs — what it settles

**Report:** `docs/research/kb/reports/agents/wf-dag-protocol-verbs.md`

### Settled (becomes a decision)

| Finding | Verdict | Consequence |
|---|---|---|
| `claude -p "/verb args"` runs a `disable-model-invocation: true` skill; the harness expands SKILL.md verbatim into the first user message | CONFIRMED (live, internal control arm: the same session's `skill_listing` omits the flagged skill) | **Option (a) is live.** Automation drives the real `/wayfinder`, `/to-spec`, `/to-tickets`, `/triage`, `/implement`. |
| `$ARGUMENTS` substitutes normally under `-p` via a real `<command-args>` frame | CONFIRMED | Tickets can pass `#NNN` to a verb. |
| All five protocol verbs carry the flag; `grilling`/`prototype`/`research`/`code-review` do not | CONFIRMED (direct frontmatter read, plugin cache v1.2.0) | The verb set is stable and enumerated. |

### Four hard constraints that become spawn-helper assertions

Each is measured, and **each fails silently** — which is why they belong in code, not prose:

1. **Prefix-only.** `-p "Do nothing else first. /probe-verb"` produced *control-verb's*
   token while the model narrated having run `/probe-verb`. The decisive control arm: the
   **unflagged** skill mid-message also failed to expand (0 `command-name` frames), so this
   is `-p` prompt parsing, not the flag. → assert `prompt.startswith('/')`.
2. **stdin must be closed.** A leftover heredoc body landed verbatim in `<command-args>`;
   `stdin=DEVNULL` was clean. → `< /dev/null`.
3. **`CLAUDE_CODE_COORDINATOR_MODE` must be unset.** In coordinator mode a flagged verb is
   *refused* and an unflagged verb is rewritten into a "brief a worker" note — the
   coordinator never executes skill content at all. 0 of 174 doc pages, 9 binary hits.
   → strip `CLAUDE_CODE_*` from the child env.
4. **`Unknown command: /x` exits rc=0.** A typo'd or not-installed verb is invisible to
   exit-code checks. → preflight each verb name and assert absence of `Unknown command`.

### What it overturns in the plan

- **Drops** the sketched ticket *R scripted-protocol-verbs* — answered.
- **Removes** the largest open question about the framework's shape; no ticket is needed
  for a human-at-the-gate workaround and none for forking the verbs.
- **Constrains the durable-node design directly:** if any node is launched as an
  agent-teams *coordinator*, every flagged verb is refused there. This is the second
  independent argument (with symphony-gaps §C2/I9) for staying off the teams path.
- **Adds** option (c) as a *specified, cheap* escape hatch rather than a rewrite: read the
  vendor SKILL.md, strip frontmatter, prepend `Base directory for this skill: <dir>`,
  substitute `$ARGUMENTS`, feed as the prompt — byte-for-byte what the harness injects.
  Cost to record: it drops `allowed-tools` / `context: fork` / `hooks` frontmatter, so an
  adapter must assert what it discards.

### Residual (→ ticket)

The coordinator gate is undocumented, lives in an unexported minified predicate `Wb()` that
also consults `F2()`, `qa()` and `CLAUDE_CODE_REMOTE`, and the vendor skill path embeds a
plugin version. Both are movable → the harness-currency ticket gains a named re-probe.

---

## 2. recovery — what it settles

**Report:** `docs/research/kb/reports/agents/wf-dag-recovery.md`

### Settled

| Finding | Verdict | Consequence |
|---|---|---|
| `attach`, `stop`, `kill`, `logs`, `rm`, `respawn`, `daemon` are real subcommands — hidden from root `--help`, documented in `$CC/cli-reference.md` | **REFUTES a ledger row** (three routes: `--help` with a fresh `zzflorbnix` control, binary dispatcher `Set([...])`, docs) | `claude respawn <id>` is the recovery primitive; the whole recovery API is ~4 verbs. |
| `kill -9` on a `--bg` node → respawned in ~36 s, same `sessionId`, `attempt`→2, conversation continued | CONFIRMED (live probe, host restored afterwards) | The "build a watchdog" ticket shrinks dramatically. |
| Detection = `kill(pid,0)` every **5 s** + `procStart` compare every **60 s** + PTY exit event + rv-heartbeat gap > **120 s** | CONFIRMED (binary `startPidPoll`/`checkPid`, constants block) | Liveness is free. |
| Respawn = **fixed 10 s** delay (not exponential), cap **20**, 3-fast-crash breaker, and `attempt` **resets to 1 after any 5-minute healthy run** | CONFIRMED | **The harness's `attempt` is NOT a usable retry budget** — a slow-failing node loops forever inside the cap. |
| `~/.claude/jobs/<id>/state.json` already carries `state`, `detail`, `tempo`, `needs`, `suggestedReply`, `output.result`, `tokens`, `respawnFlags`, `resumeSessionId`, `intent` | CONFIRMED (shape-enumerated over 3 real job dirs + the probe) | The escalation protocol has a native vocabulary to reuse, not invent. |
| `CLAUDE_CODE_TASK_LIST_ID` is **not** in `RQr`, the respawn env set; unpinned it defaults to the **session id** | CONFIRMED (binary `u8()`, `RQr`) | A shell export dies; an id-changing respawn hands the node an **empty task list**. |
| `CLAUDE_CODE_RESUME_PROMPT` is set with `??=` — overridable per node — and is **never written to the transcript** | CONFIRMED (binary `Djb`; transcript grep 0, control 3) | The only text a respawned node is *guaranteed* to receive. |
| A `--bg` node runs in **brief mode**: plain assistant text is hidden from the user | CONFIRMED (live transcript meta message, verbatim) | Node output must be a file or `SendUserMessage`. |
| `Monitor` does **not** survive a restart; background shell commands, dynamic workflows and background subagents do | CONFIRMED (`$CC/agent-view.md` § handoff) | No node may depend on a live `Monitor`. |
| **cwd gone ⇒ permanently unrecoverable**; `exec`-mode workers are **never** auto-respawned | CONFIRMED (binary `settleCwdGone`, literal string) | A deleted worktree kills a node for good. |

### The two real gaps — both become tickets

1. **A HUNG node is detected and never recovered.** The stall detector emits
   `tengu_bg_worker_stalled` and takes no action; the vendor docs confirm by a second route
   that stall recovery is **attach-triggered** (*"When you open a session that has stopped
   responding, the supervisor restarts its process"*). This is the single biggest native gap
   for an unattended DAG — and symphony-gaps independently demands the same mechanism (D2,
   300 s stall timeout). Two researchers, two corpora, one ticket.
2. **There is no native always-on local watchdog.** `claude daemon` service install is
   *"disabled in this version"* (its own `--help`); the supervisor exits when the last
   client disconnects. Cloud routines have no local file access and a 1 h minimum; Desktop
   tasks need the Desktop app open. **The outermost loop must be `launchd`.**

### What it overturns

- **Drops** the sketched *R recovery semantics* ticket.
- **Overturns** the plan's implicit premise that nothing detects a dead node.
- **Overturns** "write `state:"done"` to signal completion": in the live probe `state:'done'`
  did **not** suppress the respawn (`tempo` was `'active'`), contradicting
  `$CC/agent-view.md`. `claude stop` (→ `state:"stopped"`) **did**. Marked SUSPECT by the
  researcher — **one route only** — so the terminal-state predicate `rh()` becomes a probe
  (ticket **P2**), and the interim rule is *signal completion with `claude stop`, never a
  file write*.
- **Adds a blocking pre-flight**: all six background verbs sit behind
  `isAgentsFleetEnabled()`, an undocumented remote gate. If it is off on a target host the
  entire durable-node design changes and Option C ("own the loop") becomes the only path.

---

## 3. symphony-gaps — what it settles

**Report:** `docs/research/kb/reports/agents/wf-dag-symphony-gaps.md`

### The finding that rewrites a line of the plan

`SendMessage` delivery is a **poller**, not a push: `[InboxPoller]`, `EYT=1000` ms
interactive / `await _r(500)` headless, `readMailbox` a plain file read. The no-watcher
claim is control-armed the right way — the binary *does* ship watchers (`chokidar` 7,
`FSWatcher` 7, `watchFile` 29) but the 10 KB mailbox-module region has **0** `watch` tokens
against a control of 2 `inboxes` hits in the same region. So the probe can see watchers and
there are none here.

And the liveness hole: the headless loop **breaks** on *"[print.ts] No more active
teammates, stopping poll"*, and its inbox read is hardcoded to the literal `"team-lead"`.
**A node that finishes its stage and waits to be handed the next one terminates instead of
waiting.**

> **Plan edit, verbatim:** *"edges = SendMessage to named peers"* → **"edges = `blockedBy`
> in the task list; `SendMessage` is for escalation upward only."**

### Settled by borrowing symphony's lifecycle, rejecting its selection

Symphony would **reject our DAG**: *"The orchestrator MUST NOT … branch on
provider-specific blocker, board, transition, or comment semantics"* (`SPEC.md:1242-1243`),
`blocked_by` is *"best-effort provider metadata"*, and dispatch order is a flat 3-key
priority sort. **We inherit its lifecycle mechanisms, not its selection mechanism** — and
phonyhuman's `prd` skill (upstream decomposition into `blockedBy` chains) is external
validation that our `/to-tickets` move is the right one.

Six REQUIRED conformance items we lack entirely, each now a ticket line:
reconcile-before-dispatch · claim states · stall timeout · retry backoff with a cap ·
terminal-workspace cleanup · **distinct terminal reasons**.

### What it overturns

- **Drops** the sketched *R symphony gap analysis* ticket.
- **Overturns the edge model** (above) — the largest single change to the plan.
- **Rejects two imported ideas by evidence, not preference:** symphony's credential boundary
  (unbuildable — all 50 credentials are `env = true` by an explicit 2026-08-02 user ruling)
  and itervox's `input_required` pause-and-resume (unbuildable — nothing gives a subagent a
  way to ask, and a headless node cannot idle). Symphony's hard-failure posture is
  **forced**, not chosen.
- **Reinforces** the decision to stay on the subagent/workflow path and never use teammates:
  three independent losses on the named path (zero worktree isolation, dropped frontmatter
  fields so per-role capability scoping is unenforceable, forced `permissionMode`).
- **Names the concurrency knob we lack:** per-*stage* caps
  (`max_concurrent_agents_by_state`). The harness caps agents globally (20) and never by
  stage.

### The one recommendation this synthesis does **not** carry forward

symphony-gaps' **P1 "wire the scheduler tick to the native cron"** is contradicted by
recovery's reading of `CronCreate`'s own loaded schema. See §9 contradiction 1. The
researcher self-marked it SUSPECT and never fired one live; recovery read the tool
definition. **Recovery wins.**

---

## 4. plugin-extraction — what it settles

**Report:** `docs/research/kb/reports/agents/wf-dag-plugin-extraction.md`

### The sharpest finding of the sweep, in one line of binary

```js
O7u = ["agent","subagentStatusLine"];
zB_ = Te(() => BW().pick(Object.fromEntries(O7u.map((e)=>[e,!0]))).strip());
```

A plugin `settings.json` is a **two-key projection of the full settings schema with
`.strip()`**. `env` and `permissions` are keys of `BW()` (control arm, both located in the
binary) — so they are exactly what `.strip()` eats, **silently**.

### Settled

| Finding | Verdict | Consequence |
|---|---|---|
| A plugin agent loses **seven** frontmatter fields, not three: `permissionMode`/`hooks`/`mcpServers` warn; **`initialPrompt`, `observer`, `observerMessage`, `observeSubagents` are dropped silently**; `isolation` narrows to `{worktree}` | CONFIRMED (loader `zzu()` token census, control-armed inside the same 2,100-byte body; second route = local loader `fVu()` spreads all four) | `claude --debug` surfaces the three that warn and **nothing** surfaces the four that do not. |
| Plugin settings are the **base layer** — lowest precedence of every source; plugin agents are agent scope 5 of 5 | CONFIRMED (binary `S8i()`; `$CC/sub-agents.md:167`) | Extraction is non-destructive and always project-overridable. |
| **Hooks MERGE across sources; they do not override** | CONFIRMED (`$CC/hooks.md:268`) | The same blocking `SubagentStop`/`TeammateIdle` gate in both places is a **double block**. Move a hook, never copy it. |
| Skills and workflows are namespaced (`plugin:skill`, `/<plugin>:<workflow>`) | CONFIRMED | The least lossy components; extract first. |
| The real spawn pins are `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | CONFIRMED, and it **REFUTES the researcher's own first guesses** (`CLAUDE_CODE_MAX_AGENT_DEPTH` → 0, `..._CONCURRENT_AGENTS` → 0; fresh control `ZZQFRESHCTRL8811` → 0) | Any doc or ticket naming the plausible-looking names is naming nothing. |

### What it overturns

- **Drops** the sketched *R plugin-extraction boundary* ticket.
- **Amends the packaging decision.** "Project-scoped now, plugin at extraction after proven"
  becomes **"project-scoped now; extraction moves files, never settings — the
  `.claude/settings.json` shim is permanent and documented."** Anything expressed as a
  settings key or an environment variable stays forever.
- **Kills `observer` as a telemetry route for a packaged framework** twice over: the
  frontmatter fields are silently stripped *and* the mechanism's gate
  `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS` is an env var, which is also unextractable.
- **Constrains the durable-node launch:** `initialPrompt` is how a `--agent` main session
  gets its opening instruction, and plugin-packaged role agents cannot carry it. Either the
  launcher passes the prompt explicitly (preferred, vendor-independent) or those role
  definitions stay in `.claude/agents/`.
- **Adds a pre-extraction audit gate** (a new hk-step candidate): grep
  `.claude/agents/*.md` for `initialPrompt|observer|observerMessage|observeSubagents|isolation: *remote`
  and keep every hit project-scoped.
- **Adds three one-line binary regression checks** to the harness-currency loop.

---

## 5. context-gate — what it settles

**Report:** `docs/research/kb/reports/agents/wf-dag-context-gate.md`

### Settled

| Finding | Verdict | Consequence |
|---|---|---|
| **No hook event receives context utilization.** The common base `$m()` is exactly 8 fields | CONFIRMED — enumerated by SHAPE over all 64 `hook_event_name:` construction sites; control = the statusline assembler in the *same* binary demonstrably spreads `context_window` | Any ticket written as *"a hook checks context % and blocks"* is unbuildable as written. |
| The **status line** is the only surface handed a pre-computed `used_percentage` — and it is a **sensor only** | CONFIRMED | Sensor and actuator must be separate components. |
| ⚠️ The status line **goes quiet while a session waits on background subagents** | CONFIRMED (`$CC/statusline.md:153`, verbatim) | An event-driven-only sensor is blind in a coordinator node's longest phase. `refreshInterval` is mandatory. |
| Auto-compact trigger = `min(window − round(window×buffer), min(floor(window×pct/100), window−13000))`; `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=33` on 200K lands at ~30% | CONFIRMED (binary `FTo`/`ISs` verbatim; the `Math.min` is *why* the override can only lower) | The **only** native knob that fires an event at a percentage you choose. |
| `PreCompact` (matcher `auto`) **can block**, and blocking a *proactive* compaction is safe — the conversation just continues uncompacted | CONFIRMED (`$CC/hooks.md:2755`, verbatim) | A free, harness-fired, percentage-accurate tripwire. |
| `SessionStart` `hookSpecificOutput.initialUserMessage` **creates the first turn of a `-p` run with no prompt argument** | CONFIRMED | The native restart-injection channel; strictly more robust than a shell-quoted prompt. |
| `--resume` / `--continue` / `--fork-session` / `claude respawn` **all restore the conversation** — the thing the gate exists to discard | CONFIRMED | The restart is a NEW session handed a durable file, optionally with `--session-id` for a deterministic successor. |
| A live transcript carries every token needed to compute utilization — **but not the denominator** (`message.model` present, `context_window_size` absent) | CONFIRMED (live probe, 3-way control arm: long file → number, six trivial files → `(None,None)` not `0`, missing path → `Errno 2`) | A transcript-derived gate owns a model→window map that drifts. |

### The mutually-exclusive pair the plan must not trip over

**`DISABLE_AUTO_COMPACT=1`** — the naive "we never compact" setting, which this repo's
`feedback_no_compact` memory practically invites — **turns the `PreCompact` gate off.** Use
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` plus a `PreCompact` block instead.

### What it overturns — and the one thing that outranks all the mechanics

- **Drops** the sketched *R context-gate mechanics* ticket.
- **Re-shapes the gate ticket** from "a hook reads the %" to a sensor+actuator design; the
  researcher's recommended Design D (native trip + statusline number + Stop actuator +
  `PostCompact` tripwire) is a specification, not a research question.
- ⚠️ **The threshold itself is unsettled, and it is the bigger risk.** A 30% gate on a 200K
  window fires at **~54,000 tokens**, against an inherited ~78–85k cold-start figure the
  researcher explicitly declined to re-derive (`probes-need-a-control-arm.md` rule 6). Those
  numbers do not fit. Viable only if nodes run 1M-context, or "30%" means the hop's working
  budget rather than the raw window, or a lean node's cold start is genuinely small.
  **This becomes a measurement ticket that BLOCKS the gate design and the fan-out sizing.**
- **Adds a placement rule:** the durable node file must live in a **tracked** path.
  `clear-prep`'s handoff lives in `.agent/plans/`, which is gitignored — invisible to a
  reviewer and destroyed by `git clean -xdf` in a multi-worktree DAG.

---

## 6. model-routing — what it settles

**Report:** `docs/research/kb/reports/agents/wf-dag-model-routing.md`

### Settled

| Finding | Verdict | Consequence |
|---|---|---|
| The native `--fallback-model` / `fallbackModel` chain **explicitly excludes 429, rate-limit and billing** | CONFIRMED, two routes (docs `$CC/model-config.md:359` **and** binary `tR_=new Set([401,407,429,404,403,413])` + the `billing_error` guard) | It cannot carry Fable-exhaustion fallback. |
| A **second, entirely undocumented** path — `model_fable_consent` → `hVe()` — substitutes Opus → Sonnet → Haiku on Fable credit/spend-cap/seat exhaustion, emitting `query_model_change` + `model_consent_fallback` | CONFIRMED (binary @246376864/@240965321; **0 of 174** doc files, controls `fallbackModel` → 8 files, invented `bqx9tzm` → 0) | **Do not build a bespoke Fable→Opus swapper** — it would fight the harness's own latch. Build a *detector*. |
| There is **no `seven_day_fable` bucket** — Fable draws the shared `five_hour`/`seven_day`; only Opus and Sonnet have model-scoped sub-buckets | CONFIRMED (probe 0, control `seven_day_opus` → 15) | Fable→Opus buys **capability continuity, not headroom**. |
| The session and weekly windows are **shared across all models**, and *"a large workflow fanout can exhaust the weekly allowance before the session window resets"* | CONFIRMED, two routes (`$CC/costs.md:128`, `$CC/errors.md:321-323`, both verbatim) | The vendor names this framework's exact hazard. |
| There is **no pre-flight quota API** — `rate_limits.*` appears in the statusline JSON only *after* the first API response; `/usage` is a ≤60-min-old **local** cache | CONFIRMED | The only proactive lever is throttling fan-out, not choosing models. |
| `CLAUDE_CODE_SUBAGENT_MODEL` is a global hammer overriding per-invocation *and* frontmatter models for subagents, workflow agents **and teammates** | CONFIRMED (three doc anchors incl. the changelog entry that made it reach teammates) | Setting it destroys every per-node model decision. |
| `CLAUDE_CODE_NO_MODEL_FALLBACK=true` disables **both** mechanisms and turns Fable exhaustion into a hard `model_error` — undocumented | CONFIRMED (binary `yIe()`/`iJr()`/`hVe()` + a throwing tripwire string) | Never set it unless a node must be Fable-or-fail. |
| Fable specifics: never a default on any account type (and `/model fable` writes it into **user** settings, contaminating later sessions); thinking cannot be disabled so `/effort` is the only spend dial; a non-interactive `/effort` **cannot** release the model-default hold (reports `Not applied`) | CONFIRMED | A Fable node must pass `--model fable` **and** `--effort` at **every launch**. |
| Org effort caps clamp **silently** in background agents and under json/stream-json; a subagent whose model is excluded by `availableModels` is **silently run on the inherited model** | CONFIRMED | Verify the actual model from the result message's `modelUsage`. |

### What it overturns

- **Drops** the sketched *R fable-exhaustion detection* ticket, **and drops the sketched
  grilling *G model-routing ladder*** — the ladder is now settled mechanics plus two
  settings lines, not a design debate. What remains of it (which stage runs which model)
  folds into node-granularity, and the capacity consequence folds into budget guardrails.
- **Promotes the Codex lane from a nicety to a capacity dependency.** Fable→Opus draws the
  same meter; Opus additionally burns `seven_day_opus`. **The only lane that adds
  Anthropic-side headroom is Codex.** If the DAG's throughput target assumes N concurrent
  Anthropic nodes, that assumption is bounded by one shared weekly meter.
- **Re-keys exhaustion detection** onto the structured headless `error` category
  (`rate_limit` | `overloaded` | `billing_error` | `model_not_found` | …), never on prose —
  because the doc-promised literal `You've hit your Opus limit` is **absent from the binary**
  (SUSPECT, shape probe found 9 other limit strings, none Opus).
- **Splits exhaustion into two handlers**: (a) Fable credit gate → native substitution, node
  survives degraded, DAG continues; (b) shared window → 429 after retries, **no native
  help**, and every Anthropic node dies simultaneously.
- **Leaves one unresolved collision** for the background-node ticket: `--bg` ⊕ `--print`,
  while `--help` labels `--fallback-model` and `--max-budget-usd` print-only and
  `$CC/agent-view.md:408` says a backgrounded session carries `--fallback-model`. Interim
  guidance: put the chain in the `fallbackModel` **setting**, which carries no `--print`
  caveat in any corpus.

---

## 7. codex-lane — what it settles

**Report:** `docs/research/kb/reports/agents/wf-dag-codex-lane.md`

### Settled

| Finding | Verdict | Consequence |
|---|---|---|
| Remaining Codex budget **is** programmatically inspectable without running a job, via app-server JSON-RPC `account/rateLimits/read` (`params: null`) → `RateLimitWindow{usedPercent, windowDurationMins, resetsAt}` | CONFIRMED (`codex app-server generate-json-schema --out DIR`, rc=0 — the binary's own protocol schema, offline and greppable) | The DAG's **only** source of remaining-budget telemetry, and it is better than anything the Claude lane has. |
| `codex exec --json` carries **no** rate-limit telemetry | **REFUTED — the researcher's own first inference**, caught by a cross-check against upstream source (`exec_events.rs` event enum; controls `grep -ci rate` → 1 comment, `usage` → 3, fresh-absent `xqvbz42` → 0) | Building the governor on a `codex exec --json` field that does not exist would have failed **silently** — the field would simply always be absent. |
| `codex exec` has **no** distinct exhaustion exit code — every failure is a generic `exit(1)`, and `Interrupted` also yields 1 | REFUTED (as a detector) | Timeout and failure are indistinguishable by rc; the framework needs its own timeout bookkeeping. |
| In-band detection is a **set** of substrings — 4 of 11 message variants do **not** contain `You've hit your usage limit` (two spend-cap, two credits) | CONFIRMED (`error.rs:622-727` message table) | A single-prefix matcher misses a third of the shapes. |
| The reset timestamp in the error text is **local-tz, no date when same-day, no tz marker** | REFUTED (as parseable) | Read `resetsAt` from `account/rateLimits/read`; the text is for humans. |
| Exhaustion does **not** abort the in-flight turn (*"the agent will be able to continue working on that turn"*, primary pricing page re-derived 2026-08-05) | CONFIRMED | "Budget hit" must gate the **next dispatch**, not condemn the running node. |
| `planType` **cannot** discriminate Pro 5x from Pro 20x (enum has a single `pro` member) | REFUTED | Do not route on a static per-plan message budget; the published ranges span 10×. |
| `codex exec` ships `--output-schema <FILE>` + `-o <FILE>` — a **provider-enforced** structured-output path OMC cannot use (its workers are persistent panes, not `codex exec`) | CONFIRMED | The verdict contract becomes a JSON Schema, not a prompt fragment plus nine hand-rolled type checks. |
| OMC's reaper has two **disqualifying** defects for unattended operation: `file_missing`/`parse_failed` leave a task *"stuck in_progress pending human review"*, and `revise`+`reject` collapse to one terminal status | CONFIRMED (`runtime-v2.ts:3023-3024`, `:3106`) | Port its *mechanics*, invert its *defaults*. |
| `/usage` is TUI-only — no `claude usage` subcommand at 2.1.222 | CONFIRMED (control-armed against `agents`/`doctor` in the same `--help` block) | Wrapper-tax measurement is a **human step**, not automatable through `/usage`. |
| ⚠️ Probe hazard: `codex <unknown-subcommand> --help` **exits 0** and prints top-level help | CONFIRMED | rc is not a discriminator for Codex subcommand existence — the same "a check that can only pass" class as `no_grep_q_under_pipefail`. |

### Mechanics worth porting verbatim from OMC

Liveness gate before reading (only reap when the pane is dead) · compare-and-swap under a
file lock re-verifying `status === 'in_progress' && owner === worker.name` ·
rename `verdict.json` → `verdict.processed.json` for idempotency · a typed reap-outcome
enum. These are transport-independent and are the genuinely hard-won part.

### What it overturns

- **Drops** the sketched *R codex-lane facts* ticket.
- **Removes the Codex verdict-file contract from fog** and makes it a specified task.
- **Adds a `use-tool-builtins` gate before writing any client:** the upstream Codex repo has
  `sdk/python`, `sdk/typescript` and `codex-rs/app-server-protocol/schema/typescript/v2/`.
  Directories confirmed to exist; contents unevaluated → a small research ticket that
  **blocks** the governor task.
- **Adds a NEEDS-PROBE the reaper must be built around:** whether a usage-limit-aborted turn
  still writes the `-o` file (`print_final_output()` runs before `exit(1)`, so a partial
  write is plausible). "File exists" is necessary, not sufficient.
- **Adds a corpus fact worth keeping:** `codex app-server generate-json-schema` is the Codex
  analogue of the three-corpus rule's binary tier — authoritative, offline, greppable.

---

## 8. Consolidated map updates

### 8a. Decisions to amend

| # | Amendment | Driven by |
|---|---|---|
| D1 | **Edges are `blockedBy` in the task list, not `SendMessage`.** `SendMessage` is escalation upward only. | symphony-gaps §1.2–1.3 (poller, no watcher; headless loop breaks) |
| D2 | **Node startup is a PULL**: read the task list, select the first task whose `blockedBy` set is all-Done, claim it, work it. Waiting is a task-list row, never a live process. | symphony-gaps §1.4, A4, A6, D9 |
| D3 | **Packaging: extraction moves FILES, never SETTINGS.** The `.claude/settings.json` shim is permanent and documented, not transitional. | plugin-extraction §2 (`.pick({agent,subagentStatusLine}).strip()`) |
| D4 | **Protocol verbs are driven, not forked.** `claude -p "/verb args" < /dev/null` with the four asserted preconditions. Option (c) (SKILL.md adaptation) is a *tested escape hatch*, not the plan. | protocol-verbs §1, §4, §6, §9 |
| D5 | **Model routing is settled mechanics, not a design debate.** Fable explicit per launch + `--effort` at launch; `fallbackModel: ["opus","sonnet"]` and `switchModelsOnFlag: true` in settings; never `CLAUDE_CODE_SUBAGENT_MODEL`, never `CLAUDE_CODE_NO_MODEL_FALLBACK`; detect demotion via `query_model_change` / `model_consent_fallback`. | model-routing §2, §4, §6 |
| D6 | **The Codex lane is a CAPACITY dependency, not a review nicety** — it is the only lane that adds Anthropic-side headroom. | model-routing §5 |
| D7 | **Parallelism is the spend lever, not model choice.** Fan-out width against one shared weekly meter is the binding constraint on the whole design. | model-routing §5; `$CC/errors.md:323` verbatim |
| D8 | **Every `CLAUDE_*` pin lives in the project `.claude/settings.json` `env` block, never as a shell export.** Triple-confirmed. | recovery §11, plugin-extraction §2, context-gate §3a, symphony-gaps I14 |
| D9 | **Completion is signalled with `claude stop <id>`, not by writing `state:"done"`** — the latter did not suppress respawn in a live probe. | recovery §13b/§13d |
| D10 | **The framework owns its retry budget.** The harness's `attempt` resets after any 5-minute healthy run and is not a usable cap. | recovery §6 |
| D11 | **The context gate is sensor + actuator, never a hook reading its own stdin.** Primary trip = `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` + a `PreCompact(auto)` block; do **not** set `DISABLE_AUTO_COMPACT` (mutually exclusive). | context-gate §1c, §4a |
| D12 | **The restart is a NEW session handed a durable file** — never `--resume`/`--continue`/`--fork-session`/`respawn`, all of which restore the conversation. The prompt is a one-line pointer (clear-prep step 6, adopted verbatim). | context-gate §3b, §3c |
| D13 | **The durable node file lives in a TRACKED path**, not `.agent/`. | context-gate §3d; `agent-artifact-conventions.md` |
| D14 | **The verdict contract is a JSON Schema passed to `codex exec --output-schema`, captured with `-o`, carrying `schema_version`** — not a prompt fragment. Keep three terminal verdicts (approve/revise/reject) mapped to three edges. | codex-lane §4.4, §4.3 |
| D15 | **`file_missing` and `parse_failed` are escalation edges, not warnings** — inverting OMC's "leave it stuck for human review" default. | codex-lane §4.3 |
| D16 | **Budget telemetry is asymmetric and the design must say so**: Codex has a typed pre-flight (`account/rateLimits/read`); Claude has **no pre-flight quota API** — only a post-first-response statusline read. | codex-lane §2, model-routing §1a |
| D17 | **Detection keys on structured categories, never prose** — headless `error` category on the Claude side, `codexErrorInfo`/substring-set on the Codex side; never on exit codes. | model-routing §1b, codex-lane §3.1–3.5 |
| D18 | **Node output is a file or `SendUserMessage`, never plain assistant text** — background sessions run in brief mode. | recovery §13c (live transcript meta message) |
| D19 | **No node may depend on a live `Monitor`; no node's worktree may be deleted while it lives** (cwd-gone ⇒ permanently unrecoverable). | recovery §10, §6 |
| D20 | **Reuse the harness's own escalation vocabulary** — `state` / `detail` / `tempo` / `needs` / `suggestedReply` / `output.result` from `~/.claude/jobs/<id>/state.json`. | recovery §8 |
| D21 | **Never the agent-teams / teammate path** — now four independent losses (zero worktree isolation; ten dropped frontmatter fields; forced `permissionMode`; coordinator mode refuses every flagged verb). | symphony-gaps C2/I9/E2, protocol-verbs §6 |
| D22 | **The outermost loop is `launchd`.** There is no native always-on local watchdog at 2.1.222, and `CronCreate` is session-only. | recovery §1, §14 |
| D23 | **Move a hook, never copy it** — hooks merge across sources, so a duplicated blocking gate is a double block. | plugin-extraction §3 |
| D24 | **Two exhaustion handlers, not one**: Fable credit gate (native substitution, node survives) vs shared window (no native help, every Anthropic node dies at once). | model-routing §2 |
| D25 | **Spawn-pin names are `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` / `_MAX_CONCURRENT_SUBAGENTS` / `_MAX_SUBAGENTS_PER_SESSION`** — the plausible-looking alternatives do not exist. | plugin-extraction §2 (refutes the researcher's own guess) |

### 8b. Revised ticket list

See the structured output for the machine-readable form. Summary of the delta:

- **Dropped (answered by today's runs, → decisions):** R scripted-protocol-verbs ·
  R codex-lane facts · R recovery semantics · R plugin-extraction boundary ·
  R symphony gap analysis · R context-gate mechanics · R fable-exhaustion detection ·
  **G model-routing ladder** (settled to two settings lines + a detector).
- **Carried forward:** T pin-the-topology settings (now fully specified) · T escalation
  clause in `clarify-before-acting` · T harness-currency loop (now with a named regression
  list) · the six remaining grillings, re-blocked.
- **Added:** four prototypes (the `--bg`/`-p` collision, the fleet gate + `rh()` predicate,
  the cold-start measurement, and a Codex SDK check) plus five tasks lifted out of fog
  (spawn helper, watchdog tick, verdict contract, ledger corrections, stall recovery).

### 8c. Revised fog

- **Task-graph ⇄ issue wiring.** We now have *two* candidate trackers —
  `CLAUDE_CODE_TASK_LIST_ID` (durable, file-locked, native `blocks`/`blockedBy`) and GitHub
  Issues. Symphony's whole architecture is "the tracker is the database". Which one is
  authoritative is the scheduler's **first** question.
- **Worktree isolation for concurrent implement nodes** — sharpened by three facts:
  cwd-gone is permanently fatal, `baseRef` defaults to `"fresh"` (= `origin/<default>`, so a
  node on a feature branch gets a tree without the branch's commits), and per-stage
  concurrency caps have no native equivalent.
- **Re-derived build slices** (tracer bullet, reviewer/executor stages, gate node,
  validation seam, proof run).
- **Whether #524 gates the Codex stage.**
- **NEW — rework: a cycle or a new task?** `blockedBy` is a DAG edge and cannot express "go
  back to research"; stokowski's `rework_to` targets any earlier state, making its graph
  cyclic. Name the choice before building.
- **NEW — does `TaskStop` reap a detached `codex exec` grandchild?** Two ports independently
  needed process-group kill, and our Codex lane already runs detached with its own group.
- **NEW — do transcript records at 2.1.222 carry per-subagent token attribution?** If not,
  there is no headless cost governor at all.
- **NEW — the `yFu` `window < 200000` branch.** Unexplained; prefer window = 200000 and move
  the trigger with `PCT_OVERRIDE` until probed.
- **NEW — does a usage-limit-aborted `codex exec` still write its `-o` file?** Decides
  whether "file exists" can ever be sufficient for the reaper.

### 8d. Revised out-of-scope

Carried: secrets-CLI program · memory-index compaction · generalizing beyond this repo
(extraction IS the path back) · rebuilding the interview verbs.

**Added, each with the evidence that rules it out:**

- **The agent-teams / teammate path** — four independent losses (D21).
- **A bespoke Fable→Opus swapper** — the harness's `model_fable_consent` path already does
  it and persists its own latch; a competitor would fight it.
- **Symphony's credential boundary** (host-side tool execution so the child never sees a
  token) — unbuildable under the deliberate 2026-08-02 `env = true` ruling.
- **itervox's `input_required` pause-and-resume-in-session** — nothing gives a subagent a
  way to ask, and a headless node cannot idle.
- **The `observer` frontmatter mechanism as a packaged telemetry route** — silently stripped
  from plugin agents *and* gated by an unextractable env var.
- **Symphony's flat priority sort** — deliberately graph-blind; we need topological order.
- **`CronCreate` / `/loop` / cloud routines / Desktop tasks as the DAG watchdog** — each
  disqualified by a different property (session-only, session-only, no local file access,
  requires the Desktop app open).
- **Whether plugin hooks fire inside a teammate's turn** (plugin-extraction SUSPECT #6) —
  moot under D21.

---

## 9. Contradictions

Named, both sides, and which corpus wins. Nothing papered over.

### 1. `--bg` vs `-p`: the verb-running shape and the supervised shape may be different shapes

**No single researcher saw this — it only exists across three reports.**

| Side | Claim | Corpus |
|---|---|---|
| protocol-verbs | The route that runs a protocol verb is `claude -p "/verb" < /dev/null`; all ten probes used `-p` | live fixture, 10 sessions |
| model-routing | `--bg` and `--print` are **mutually exclusive** — hard error since v2.1.198, verbatim error text | `$CC/errors.md:1191-1195` |
| recovery | ***"exec workers are never auto-respawned"*** — only PTY/daemon-backed `--bg` sessions get the watchdog | binary literal string |

**Neither report is wrong; they never met.** The consequence is that on today's evidence a
`-p` verb node has **no watchdog** and a `--bg` node has **unproven** slash expansion.

**Resolution: unresolved, and it is the cheapest high-value probe in the plan.** It cannot
be settled by reasoning — `--bg` takes its prompt as a positional argument, and whether the
positional travels the same user-prompt expansion path as `-p`'s is a question about code
neither researcher read. → ticket **P1**, which **blocks the scheduler grilling**. If `--bg`
does not expand verbs, the shapes are: verb nodes are `-p` under the framework's own launchd
supervision, and only long-lived worker nodes are `--bg`.

### 2. Is the native cron the scheduler tick?

| Side | Claim | Corpus |
|---|---|---|
| symphony-gaps (P1, "cheapest high-value ticket in this report") | Wire the tick to `CronCreate` / `createCronScheduler` rather than building a daemon — 22 / 3 binary occurrences, a live call site in `print.ts`, `wakeupSource` 16 | binary byte-scan; **self-marked SUSPECT**, no cron fired live |
| recovery | `CronCreate` is **DISQUALIFIED**: *"Jobs live only in this Claude session — nothing is written to disk"*, `durable` *"has no effect"*, *"Jobs only fire while the REPL is idle"*, auto-expires after 7 days | **the tool's own loaded schema**, verbatim |

**Recovery wins, decisively.** The tool definition is the primary corpus for the tool's own
semantics; a byte-scan proves a symbol exists, not what it does — the exact generalisation
codex-lane arrived at independently (*"binary `strings` proves a symbol EXISTS; it says
nothing about WHICH surface EXPOSES it"*). A cron hosted inside the session it must watch
dies with that session and cannot detect the crash it exists to detect.

**Resolution:** `launchd` is the outer loop (D22). `createCronScheduler` may still be a
useful *in-session* wakeup and is not banned — but it cannot be the DAG tick, and
symphony-gaps' P1 does **not** enter the map as written.

### 3. Can a node idle?

| Side | Claim |
|---|---|
| symphony-gaps | A headless node **cannot** idle awaiting an edge — the poll loop breaks on *"No more active teammates, stopping poll"* and the session ends |
| recovery | Real background nodes on this host sat in `state:"blocked"`, `tempo:"blocked"`, with `needs` and `suggestedReply` populated, **for ~2 weeks** |

**Not a contradiction — two different loops, and the distinction is load-bearing.**
symphony-gaps measured the *teams inbox poll* in `print.ts`; recovery measured the *bg
supervisor* keeping a session's job record alive. A `--bg` node **can** persist in a blocked
state; it **cannot** be woken by a sibling's `SendMessage`.

**Two riders that neither report states together:** the supervisor *"stops its process"*
after a session sits unattached ~1 hour (recovery §10), so idle waiting is bounded anyway;
and a stale roster entry is **reaped, never respawned** (`adopt()` returns null on a dead
pid), so "blocked for two weeks" means a *job record* survived, not a process.
**Resolution:** D1/D2 stand — waiting is a task-list row.

### 4. `claude attach` — two researchers refuted the same ledger row independently

recovery (three routes: `--help` with a fresh `zzflorbnix` control, the binary dispatcher's
`Set(["logs","attach","stop","kill","respawn","rm"])`, and `$CC/cli-reference.md:29–45`) and
context-gate (live `claude attach --help`, control `claude peek --help` falls through to
root help) both **REFUTE** the ledger's *"`claude attach` DOES NOT EXIST"* row.

**Not a contradiction — a double confirmation with disjoint controls**, which is stronger
than either alone. Both diagnose the same root cause: the prior probe was bounded to the
*visible* `--help` command list and the answer was reported about *the CLI*. That is the
founding incident's exact shape. → ticket **T5** (ledger corrections) is mandatory, not
optional.

### 5. The ~78–85k per-agent number

| Side | Handling |
|---|---|
| context-gate | Explicitly labels it **INHERITED** from 2026-08-04c *for a different agent shape*, declines to re-derive it, and makes re-derivation the report's headline risk |
| model-routing | *"This corroborates the ledger row `~78-85k tokens per agent spawned regardless of size`"* |
| symphony-gaps | Cites it as *"a single measurement"* with *"no live per-subagent token figure"* |

**model-routing does not corroborate it — it cites it.** A doc anchor about *what burns the
weekly window* is consistent with the number but is not an independent measurement of it.
Per `probes-need-a-control-arm.md` rule 6, restating an inherited figure converts someone
else's unverified note into a finding.

**Resolution: the number does NOT become a decision.** It becomes ticket **P3**, and it
**blocks both** the context-gate threshold and the fan-out concurrency cap — the two places
the plan would otherwise hard-code it.

### 6. Does blocking `PreCompact` need auto-compact ON, when this repo's rule says never compact?

`feedback_no_compact` (*"never /compact; resume file + /clear"*) reads as an instruction to
set `DISABLE_AUTO_COMPACT=1`. context-gate measures that doing so **turns the gate off** —
the two are mutually exclusive.

**Resolution: no real conflict once stated precisely.** The repo rule bans *compaction as a
context strategy*; the gate design uses the *auto-compact threshold as a tripwire* and then
**blocks the compaction**, so no compaction ever happens. `PCT_OVERRIDE` + `PreCompact` exit
2 honours the rule's intent while `DISABLE_AUTO_COMPACT` would defeat the mechanism. This
must be written into the settings ticket **with the rationale**, or a future session will
"fix" it back — the same failure mode `secrets-out-of-the-shell-env.md` records.

### 7. Vendor docs vs binary on message delivery

`$CC/agent-teams.md:275` — *"Automatic message delivery: when teammates send messages,
they're delivered automatically to recipients. **The lead doesn't need to poll for
updates.**"* The binary shows a 1,000 ms poller that **queues rather than delivers** while
the session is busy (*"[InboxPoller] Session busy, queuing for later delivery"*).

**The binary wins** (three-corpus rule). The doc sentence is true from the *operator's*
point of view — the lead does not poll *by hand* — and false as a description of the
mechanism. Recorded because *"anyone designing from the docs alone would build a push
architecture on a poll substrate"*, which is exactly what the plan's edge sentence did.

### 8. Two self-refutations worth carrying forward as method

Neither is a cross-report contradiction, but both change how the remaining tickets should be
written:

- **codex-lane refuted its own inference** that `codex exec --json` carries rate-limit
  telemetry. Had it not cross-checked, the budget governor would have been built on a field
  that is always absent — a **silent** failure.
- **plugin-extraction refuted its own guessed env-var names**
  (`CLAUDE_CODE_MAX_AGENT_DEPTH` → 0). Shape-enumerating all 439 `CLAUDE_CODE_*` tokens gave
  the real ones.

**Both were caught by enumerating BY SHAPE instead of grepping an expected list** — the same
habit that found four silently-dropped agent fields the docs never enumerate and 64 hook
construction sites. Any ticket that says "check whether X exists" should say "enumerate the
set and see what is in it".

---

## 10. What the next session should do first

1. Run **P1** (`--bg` slash expansion). One probe, ~10 minutes, and it decides the node
   launch shape that four other tickets depend on.
2. Run **P2** (fleet gate + `rh()`). If `isAgentsFleetEnabled()` is false on the target host,
   the durable-node design changes wholesale and Option C becomes the only path.
3. Run **P3** (cold-start measurement). Until it lands, "30%" is a number with no denominator
   and the fan-out cap has no basis.
4. Land **T1** (pin the topology). One file, ~six lines, and it prevents a *total silent
   failure* of the DAG substrate (`CLAUDE_CODE_TASK_LIST_ID` lost on respawn → empty task
   list → every claim gone).

Only then is the scheduler grilling worth a session.

---

## GitHub repos touched

Aggregated across all seven reports.

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed binary
  v2.1.222 (`~/.local/share/claude/versions/2.1.222`, 271,289,792 bytes) was byte-scanned by
  six of the seven researchers for the plugin loader, agent frontmatter schema, settings
  merge order, hook payload base, auto-compact arithmetic, mailbox poller, supervisor
  respawn path, model-fallback chains and the `CLAUDE_CODE_*` token census; its `--help`
  surface and offline documentation tree were the second and third corpora.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the offline
  vendor doc tree `sources/agent-harness-docs/docs/claude-code` (`$CC`, 174–175 pages)
  supplied every `$CC/*` citation: `agent-view.md`, `cli-reference.md`, `hooks.md`,
  `statusline.md`, `sub-agents.md`, `model-config.md`, `costs.md`, `errors.md`,
  `plugins-reference.md`, `agent-teams.md`, `workflows.md`, `skills.md`,
  `context-window.md`, `headless.md`, `routines.md`, `desktop-scheduled-tasks.md`.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo:
  `docs/agent-team.md`, `docs/specs/agent-team-first-slice.md`, the harness ledger
  `.claude/agents/claude-code-expert.md`, `.claude/skills/clear-prep/SKILL.md`,
  `.claude/rules/*`, and issues #550 / #354 / #283 / #476 / #538 / #524.
- [mattpocock/mattpocock-skills](https://github.com/mattpocock/mattpocock-skills) — the
  protocol verbs' frontmatter read directly from the installed plugin cache v1.2.0
  (`wayfinder`, `to-spec`, `to-tickets`, `triage`, `implement` all carry
  `disable-model-invocation: true`; `grilling`, `prototype`, `research`, `code-review` do
  not).
- [openai/codex](https://github.com/openai/codex) — primary source of truth for the Codex
  lane: `codex-rs/exec/src/lib.rs`, `exec_events.rs`,
  `event_processor_with_jsonl_output.rs`, `codex-rs/protocol/src/error.rs`,
  `protocol/src/protocol.rs`, `docs/exec.md`, and the `sdk/python` / `sdk/typescript` /
  `app-server-protocol/schema/typescript/v2` directories (existence confirmed, contents
  unevaluated).
- [openai/symphony](https://github.com/openai/symphony) — `SPEC.md` (2,311 lines),
  `README.md`, `elixir/WORKFLOW.md`, re-fetched at HEAD `f8e8b8a` (unchanged since the
  2026-08-04 survey; fetch control arm 200 vs 404 on an invented path).
- [Sugar-Coffee/stokowski](https://github.com/Sugar-Coffee/stokowski) — typed states,
  `max_rework`, three-layer prompt assembly, process-group kill, config-out-of-CLAUDE.md
  rationale (cited via the prior survey's anchors).
- [vnovick/itervox](https://github.com/vnovick/itervox) — `SOUL`/`INSTRUCTIONS` split,
  `allowed_actions` capability scope, agent evals and their provenance caveat,
  `input_required` state.
- [manav03panchal/phonyhuman](https://github.com/manav03panchal/phonyhuman) — upstream
  decomposition into `blockedBy` chains; the `CLAUDECODE` env-strip hazard.
- [mksglu/hatice](https://github.com/mksglu/hatice) — per-turn `AbortController` deadline,
  auto-respond-to-input, the `CLAUDECODE` strip.
- [Yeachan-Heo/oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) — the
  prior-art verdict contract and its consumer, read from the local plugin cache at v4.15.7
  (`src/team/cli-worker-contract.ts`, `src/team/runtime-v2.ts`). The plugin is disabled in
  this repo; the cache was read-only.

Non-GitHub sources consulted (via the codex-lane report):
<https://learn.chatgpt.com/docs/pricing> (re-fetched 2026-08-05),
<https://learn.chatgpt.com/docs/non-interactive-mode>,
<https://code.claude.com/docs/en/costs.md>, and six practitioner/secondary blogs explicitly
labelled ANECDOTAL.
