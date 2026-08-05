# Claude Code expertise — durable-node death detection & resume (2026-08-05, v2.1.222)

`claude --version` → `2.1.222 (Claude Code)`. Binary audited:
`~/.local/share/claude/versions/2.1.222`.

Corpora consulted: ledger (`.claude/agents/claude-code-expert.md`) → installed binary →
`claude --help` / subcommand `--help` → live host state (`~/.claude/daemon/`,
`~/.claude/jobs/`) → offline docs (`$CC`, 174 pages) → live probe.

STATUS: COMPLETE. 175 doc pages (not 174 — re-counted: `ls $CC | wc -l` = 175).

---

## HEADLINE

1. **The watchdog already exists and I proved it live.** `claude --bg` nodes are hosted by
   a per-user supervisor that polls `kill(pid,0)` every **5 s**, compares `procStart` every
   **60 s**, and respawns a dead node after **10 s** with its conversation intact. I killed
   a real node with `kill -9`; it came back 36 s later, same `sessionId`, `attempt`→2.
2. ⚠️ **The ledger row "`claude attach` DOES NOT EXIST" is REFUTED.** `attach`, `stop`,
   `kill`, `logs`, `rm`, `respawn` and `daemon` are all real subcommands, hidden from root
   `--help` but documented in `$CC/cli-reference.md`. **`claude respawn <id>` is the
   recovery primitive the framework needs.**
3. **Two real gaps.** A *hung* node is detected (`tengu_bg_worker_stalled`) and **never
   recovered** — recovery is attach-triggered. And there is **no always-on local
   watchdog**: `claude daemon` service install is *disabled in this version* and the
   supervisor exits when the last client disconnects. The outermost loop must be `launchd`.
4. **`~/.claude/jobs/<id>/state.json` is already the per-node ledger** the framework was
   going to design — `state`, `needs`, `suggestedReply`, `output.result`, `tokens`,
   `respawnFlags`, `resumeSessionId`, `intent`. Reuse its vocabulary.

---

## 1. `claude daemon` — the hidden supervisor

CONFIRMED. Verbatim:

```
$ claude daemon --help            # rc=0
Usage: claude daemon [subcommand] [options]

Service lifecycle:
  run [json-path]   Run the supervisor in the foreground (default when piped)
  status            Show daemon pid, version, uptime
  logs              Tail the daemon log (Ctrl-C to stop)
  uninstall         Remove the background service (launchctl/systemd)
  stop              Shut down the supervisor and terminate background sessions
                      --any           also stop a transient (non-service) daemon
                      --keep-workers  leave detached sessions running

  Service install is disabled in this version — the daemon runs on demand
  and exits when the last client disconnects.

Options:
  --json-path <p>   Config file (default: ~/.claude/daemon.json)
  --log-file <p>    Log file (default: ~/.claude/daemon.log)
  --help, -h        Show this help
```

Control arm (fresh, invented token): `claude zzflorbnix --help` falls through to the root
help, while `claude daemon --help` prints its own — so the probe discriminates. Full
subcommand enumeration and the **correction of the ledger's `claude attach` row** are in
§9. `claude daemon` is *hidden from root `--help`* but is **documented** —
`$CC/cli-reference.md:32,33` — so "hidden" here means hidden from `--help`, not undocumented.

⚠️ **The critical limitation, in the harness's own words:** *"Service install is
disabled in this version — the daemon runs on demand and exits when the last client
disconnects."* So the supervisor is **not** a persistent watchdog at 2.1.222. It is
started on demand by `claude agents` / a `--bg` launch and dies when the last client
goes. `uninstall` still exists (launchctl/systemd), `install` does not.

Implication for the framework: **the daemon is a re-adoption and respawn engine, not
an always-on watchdog.** Something outside Claude Code must poke it.

## 2. Death detection IS implemented — and it tells you what to do

CONFIRMED, live on this host (a real crash-residue case, not a fixture):

```
$ claude daemon status            # rc=1
not running

bg sessions:
  sock dir:     /tmp/cc-daemon-501/9396e338
  control.sock: unreachable (connect ENOENT /tmp/cc-daemon-501/9396e338/control.sock)
  bg workers:   3 in roster.json (control unreachable)
  roster.json:  updated 194577s ago
  daemon.log:   26.9KB at /Users/rmanaloto/.claude/daemon.log
  warning:      supervisor not running but 3 workers in roster — running `claude agents`
                restarts the daemon and re-adopts still-running sessions; run
                `claude daemon stop --any` to reap them instead
```

Three separable facts:

- `claude daemon status` **exits 1** when the supervisor is dead. That is a scriptable
  watchdog predicate today.
- The harness distinguishes *supervisor dead* from *workers dead* and says so.
- **Re-adoption is native**: `claude agents` restarts the daemon and re-adopts
  still-running sessions.

## 3. What is persisted per background node — `~/.claude/daemon/roster.json`

CONFIRMED by shape-enumeration of every worker record (not by grepping expected keys).
Per worker:

| Field | Value on this host | Why it matters |
|---|---|---|
| `pid` | `14595` | liveness check |
| `procStart` | `"Wed Jul 15 10:54:17 2026"` | **defeats PID reuse** — pid alone is not enough and the harness knows it |
| `sessionId` | `8a0fff99-1650-4bef-bb04-189fa3d55f89` | the resume handle |
| `rendezvousSock` / `ptySock` | `/tmp/cc-daemon-501/<inst>/rv/<short>.sock` | control + PTY channels |
| `cliVersion` | `2.1.210` | records the version that launched it (workers survive a CLI upgrade) |
| `startedAt` | epoch ms | age |
| **`attempt`** | `1` | **a restart-attempt counter ⇒ respawn is a real code path** |
| `cwd` | repo path | where to relaunch |
| `dispatch.launch.mode` | `"resume"` | how it was started |
| `dispatch.launch.sessionId` | **a transcript `.jsonl` PATH**, not a uuid | what it resumes from |
| `dispatch.launch.fork` | `true` | forked on resume |
| **`dispatch.respawnFlags`** | 52-element argv array | **the harness persists the full relaunch command line** |
| `dispatch.env` | `{AWS_REGION, AWS_DEFAULT_REGION, CLAUDE_BG_ISOLATION}` | the *only* env carried — matches the ledger's env-stripping row |
| `dispatch.isolation` | `"none"` | worktree/none |
| **`dispatch.seed`** | `{intent: "...", name: "..."}` | **the node's task text and display name — the framework's "what was this node doing"** |
| `dispatch.nonce`, `rvAuth`, `ptyAuth` | hex | per-worker auth |
| `cols` / `rows`, `decModes` | terminal geometry | PTY replay |

Top level: `{proto:1, supervisorPid, updatedAt, workers:{<short>:…}}`.

Sibling files: `~/.claude/daemon.lock` (supervisorPid, `version`, `origin:"transient"`,
`spawnedBy:{label,cwd,pid}`, `procStart`, `launchTarget` = the version dir),
`~/.claude/daemon.status.json` (`supervisorPid`, `supervisorProcStart`, `writtenAt`,
`workers`), `~/.claude/daemon/control.key`, `~/.claude/daemon/dispatch/`.

**This is the single most important finding for the framework: `respawnFlags` + `seed` +
`launch` mean the harness already stores everything needed to bring a dead node back.**
The framework does not need to re-invent per-node launch persistence — it needs to decide
whether to *use* the daemon's copy or keep its own.

## 4. `claude agents --json` is the scriptable roster read — and it does NOT start the daemon

CONFIRMED with a control arm: `claude daemon status` printed `not running` **both before
and after** `claude agents --json`, so the `--json` path reads roster state without
resurrecting the supervisor.

```
$ claude agents --json            # rc=0
[
  { "id": "ad8baf35", "cwd": "…/dotfiles", "kind": "background",
    "startedAt": 1783962604973, "sessionId": "ad8baf35-…", "name": "zstd-compression-level-tuning",
    "state": "blocked" },
  { "pid": 98962, "cwd": "…/dotfiles", "kind": "interactive",
    "startedAt": 1785894025489, "sessionId": "20df00a4-…", "name": "dotfiles-20260805",
    "status": "busy" }
]
```

Two record shapes, and the difference is load-bearing:

- `kind:"background"` → carries **`state`** (`blocked` here) and **no `pid`**.
- `kind:"interactive"` → carries **`pid`** and **`status`** (`busy`).

`claude agents --help` documents `--all` ("also include completed background sessions"),
`--cwd <path>` ("show only background sessions started under `<path>`") and `--json`
("does not require a TTY"). So the framework gets a cwd-scoped, TTY-free node census for
free.

⚠️ Two of the three roster workers are ~2 weeks stale and report `state:"blocked"` while
their supervisor is dead. **`state` is a last-known value from the roster, not a live
probe** — do not treat `state:"blocked"` as "alive but waiting" without a pid/procStart
check. **Resolved in §5 and §13a**: `state` is a last-known roster/job value; a dead pid
makes `adopt()` return `null`, and the three stale entries were silently reaped when the
supervisor next started.

## 5. Detection: exactly how the supervisor notices a dead node

CONFIRMED — binary, `~/.local/share/claude/versions/2.1.222` @252786470, verbatim:

```js
startPidPoll(){
  if(this.pidPoll)return;
  this.lastCheckPidAt=Date.now(),
  this.pidPoll=setInterval(()=>void this.checkPid(!0),_Sa),   // _Sa = 5000
  this.pidPoll.unref()
}
pidRecycled(){
  if(!this.procStart||!this.record.pid)return!1;
  let e=yVe(this.record.pid);
  return e!==void 0&&e!==this.procStart
}
async checkPid(e=!1){
  let t=Date.now()-this.lastCheckPidAt; this.lastCheckPidAt=Date.now();
  let r=t>tXp;                              // tXp = _Sa*3 = 15000  → host slept
  if(r)this.hostWokeAt=Date.now();
  if(this.record.outcome||!this.record.pid)return;
  if(r&&this.lastRvHeartbeat!==void 0)this.lastRvHeartbeat=Date.now();
  if(!this.pty)try{process.kill(this.record.pid,0)}catch(o){
     let i=Ft(o);
     if(i==="ESRCH"||i==="EPERM"){this.logVanished(!1,e),
        this.settle(this.isKilling?"killed":"crashed");return}
  }
  let n=this.lastRvHeartbeat;
  if(!r&&!this.stalledLogged&&n!==void 0&&Date.now()-n>$jb){   // $jb = 120000
     let o=await ml(Oc(this.dispatch.short));
     if(!this.stalledLogged&&(o?.tempo??this.record.tempo)==="active")
        this.stalledLogged=!0,N("tengu_bg_worker_stalled",{…});
  }
  if(this.pty)return;
  if(e&&this.pidPollTick++%12!==0)return;
  if(await this.pidRecycledAsync()){…this.logVanished(!0,e),
     this.settle(this.isKilling?"killed":"crashed")}
}
```

Answering question (1) precisely — **four detection mechanisms, all inside the supervisor
process**:

| Mechanism | Cadence | What it catches |
|---|---|---|
| `process.kill(pid, 0)` → `ESRCH`/`EPERM` | **every 5 s** | process gone |
| `pidRecycledAsync()` — compares live `procStart` to the recorded one | every **12th** tick = **60 s** | PID reuse (a *different* process now holds the pid) |
| PTY `onExit(code, signal)` | event | the normal exit path for PTY-attached workers (`if(this.pty)return` — the pid poll deliberately defers to it) |
| rendezvous-socket heartbeat gap > `$jb` = **120 s** while job `tempo==="active"` | 5 s check | **a HUNG (not dead) node** |

⚠️ **The stall detector only emits telemetry (`tengu_bg_worker_stalled`) — it takes no
recovery action.** A node that is alive but wedged is *observed* and *not* recovered.
That is the single biggest native gap for an unattended DAG.

Also note the **host-sleep guard**: a gap > 15 s between polls sets `hostWokeAt`, and for
60 s afterwards exits are not counted as crashes. Laptop sleep will not trigger a
respawn storm.

`setInterval` control arm: 140 occurrences in the binary; the invented control token
`zzqvvnk9` → **0**, so the byte-scan discriminates. (`respawnFlags` 56, `procStart` 93,
`roster.json` 21, `respawn` 317, `supervisorPid` 15, `daemon.lock` 7.)

## 6. Respawn: the native watchdog, its caps, and its suppressions

CONFIRMED — binary @252783762 (`scheduleRespawn`) and @252782956
(`doSpawnUnlessSettledOnDisk`):

```js
scheduleRespawn(e){
  if(this.attempt>=QJp)   // QJp = 20
     return N("tengu_bg_respawn_exhausted",{…}),
            this.patch({state:"crashed",detail:e}),this.settle("crashed");
  if(this.phase.kind==="running")this.transitionTo({kind:"spawning"});
  this.patch({pid:0,state:"crashed",detail:`${e}; respawning`}),this.procStart=void 0;
  …"worker crashed (…) — respawning…"
  this.backoffTimer=setTimeout(()=>{…this.doSpawnUnlessSettledOnDisk()…},Pjb) // Pjb = 10000
  this.backoffTimer.unref()
}

async doSpawnUnlessSettledOnDisk(){
  let e = ZJp() ? await ml(Oc(this.dispatch.short)) : void 0;   // read jobs/<short>/state.json
  if(this.record.outcome||retiring||retired)return;
  if(e&&rh(e)&&!e.queuedPrompt){
     N("tengu_bg_respawn_suppressed",{reason:"settled_on_disk"});
     return this.settle(mapped outcome);
  }
  if(e?.interactiveLineage&&this.lastExitExternalStop){
     N("tengu_bg_respawn_suppressed",{reason:"no_task_contract"});
     this.patch({state:"stopped",detail:"stopped by an external signal"});
     return this.settle("killed");
  }
  return this.doSpawn();
}
```

**Constants, verbatim from the binary's constant block @252788265:**

| Const | Value | Meaning |
|---|---|---|
| `QJp` | **20** | max respawn attempts before `tengu_bg_respawn_exhausted` → permanent `crashed` |
| `Pjb` | **10 000 ms** | respawn delay — **fixed 10 s, NOT exponential backoff** |
| `eXp` | 5 000 ms | "fast crash" window |
| fast-crash streak | **3** | 3 crashes each within 5 s of spawn → give up (`crashed`, no more respawns) |
| `Ljb` | **300 000 ms** | a worker that ran healthy ≥ 5 min **resets `attempt` to 1** |
| `Njb` | 60 000 ms | post-host-wake grace: exits in this window are not crashes |
| `$jb` | 120 000 ms | rv-heartbeat stall threshold (telemetry only) |
| `Hjb` | **3 600 000 ms** | `CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` default (1 h) |
| `Mjb` | 3 | max socket-auth re-keys |
| `Ojb` | `Set([129,143])` | exit codes counted as *external stop* (SIGHUP, SIGTERM) |

So the effective cap is "**20 consecutive failures without a 5-minute healthy run**", plus
a hard 3-strike fast-crash breaker, plus a "never respawned before init succeeded twice"
rule (`!workerReady && attempt>=2` → permanent `crashed`).

**Three ways respawn is refused:**
1. `settled_on_disk` — `jobs/<short>/state.json` already holds a terminal state and there
   is no `queuedPrompt`. **The framework can therefore stop the watchdog by writing state.**
2. `no_task_contract` — `interactiveLineage === true` AND the exit was an external signal.
   ⚠️ **This is the only signal-based suppression, and it does not apply to a
   task-dispatched node.** A background node with no interactive lineage IS respawned
   after `kill -9`.
3. `cwd gone` — `tengu_bg_spawn_cwd_gone`, "this job cannot be respawned". **A worktree
   deleted under a running node makes that node permanently unrecoverable.**

⚠️ **`exec`-mode workers are NEVER auto-respawned** — verbatim from the binary:
`"exec workers are never auto-respawned"`. Only PTY/daemon-backed background sessions get
the watchdog.

## 7. Resume-with-state: what survives `kill -9` and what is lost

CONFIRMED — binary @252774273 and @251758057 / @257405697.

On `attempt > 1` the supervisor re-reads `jobs/<short>/state.json` and prefers its values
over the roster's: `resumeSessionId`, `respawnFlags`, `cwd`, `interactiveLineage`. It then
scans the transcript (`Uxe(sessionId, cwd, linkScanPath)` → `{hasMessages, path}`) and:

```js
if(this.attempt>1 && hasMessages && !afterUpgrade){
   g.CLAUDE_CODE_RESUME_INTERRUPTED_TURN="1";
   if(ZJp()){
      g.CLAUDE_CODE_RESUME_PROMPT ??= Djb;
      if(interactiveLineage) g.CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS ??= String(Hjb);
   }
}
if(this.attempt>1 && !hasMessages && resumeSessionId!==dispatch.sessionId)
   g.CLAUDE_BG_POST_CLEAR_RESPAWN="1";
```

`ZJp()` = `Qe("tengu_bg_revival_guard", true)` — an **undocumented remote feature gate,
defaulting to TRUE**. (Same shape as the ledger's nesting-depth / concurrency-cap gates.
Pin behaviour by setting the env vars explicitly rather than relying on the gate.)

**`Djb`, the default resume prompt, verbatim:**

> `Continue from where you left off. Note: this session was automatically restarted after
> its process exited unexpectedly; the user has not sent a new message since the restart.
> Re-verify anything time-sensitive (branch state, running processes, prior partial work)
> before continuing.`

**It is overridable** — `CLAUDE_CODE_RESUME_PROMPT` is set with `??=`, so a value already
present in `dispatch.env` wins. **This is the framework's hook: put the ticket contract
and the "re-read your task-list claim" instruction in `CLAUDE_CODE_RESUME_PROMPT`.**

### What is LOST from the in-flight turn

CONFIRMED — the transcript deserializer @251758057:

```js
let u = te.CLAUDE_CODE_RESUME_INTERRUPTED_TURN && !t?.size && !r && !nFp(a),
    d = _0r(a, t, u ? {dropSiblingBlocks:!0, outSupersededToolUseIds:c,
                       shutdownUnwindResultsDoNotResolve:!0} : void 0),
    …
if(m.kind==="interrupted_turn"){ …f.push(interrupted_prompt meta message)… }
if(g && te.CLAUDE_CODE_RESUME_INTERRUPTED_TURN) N("tengu_resume_stale_turn_suppressed",{…});
```

- Everything already **written to the transcript `.jsonl` survives** — the resume replays it.
- The **in-flight turn's unresolved `tool_use` blocks are dropped/unwound**
  (`dropSiblingBlocks`, `outSupersededToolUseIds`, `shutdownUnwindResultsDoNotResolve`).
  A tool call that was executing at `kill -9` is **not** re-run and **not** resolved — it
  vanishes, and the model is told to re-verify.
- Any assistant text produced after the last transcript flush is lost.
- If the interrupted turn is older than `CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS`
  the auto-resume is **suppressed** (`tengu_resume_stale_turn_suppressed`) — the node
  comes back but does **not** auto-continue.
- ⚠️ If the transcript has **no messages at all** and the original launch session also has
  none, the respawn is aborted as `crashed` — **a node killed before its first turn
  flushed is not recoverable.**

### What IS re-established natively

CONFIRMED @257405697 / @260744861:

- `[sessionRestore] Auto-resuming interrupted turn for bg crash-respawn` — the interrupted
  prompt is re-injected as the initial message.
- `restoreGoalFromTranscript(e.messages, …)` — the session **goal** is restored.
- `restoredWorkerState.internal.running_background_tasks` **and**
  `orphaned_background_tasks_pending_notification` are read back, deduped by `task_id`, and
  the orphans are surfaced — so in-flight *Bash background* tasks are accounted for.
- `sendMessagePins` (`Asa(R)`) are restored into session state.

`RQr` (the env set carried into a respawn) is verbatim:
`["CLAUDE_CODE_SESSION_KIND","CLAUDE_BG_SOURCE","CLAUDE_BG_ISOLATION","CLAUDE_BG_BACKEND",
"CLAUDE_CODE_SESSION_NAME","CLAUDE_CODE_RESUME_INTERRUPTED_TURN",
"CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS","CLAUDE_CODE_RESUME_PROMPT",
"CLAUDE_CODE_RESUME_SOURCE_ALIVE","CLAUDE_BG_POST_CLEAR_RESPAWN",
"CLAUDE_BG_SESSION_PERMISSION_RULES","CLAUDE_BG_MEMORY_TOGGLED_OFF"]`

⚠️ Consistent with the ledger's env-stripping row: `CLAUDE_CODE_TASK_LIST_ID` is **not**
in that list, and the roster's `dispatch.env` on this host carried only
`{AWS_REGION, AWS_DEFAULT_REGION, CLAUDE_BG_ISOLATION}`. **A task-list id exported into
the launching shell will not survive a respawn** — it must be in the project's
`settings.json` `env` block (the ledger's settings-beat-the-shell row) or in
`dispatch.env`/`respawnFlags`.

## 8. `~/.claude/jobs/<short>/state.json` — the harness's own per-node ledger

CONFIRMED by shape-enumeration of three real job dirs on this host. This is the single
most reusable artifact for the framework. Fields observed (union of three records):

```
state            'done' | 'blocked' | …          detail   human status line
tempo            'idle' | 'blocked' | 'active'   needs    what it needs from a human
output           {result: "…"}                   children (null here)
tokens           27469                           inFlight {tasks, queued, kinds}
intent           the task text                   name / nameSource ('user'|'auto')
sessionId / resumeSessionId / daemonShort        cwd / cliVersion / template ('bg')
respawnFlags     full argv                       bgIsolation / providerEnv
interactiveLineage  true|absent                  backend ('daemon')
linkScanPath / linkScanOffset  (transcript cursor)
forkSessionId / forkParentSessionId / forkBoundaryAt / forkSourceAlive
bridgeSessionId / bridgeSessionSeq / bridgeOutboundOnly
createdAt / updatedAt / firstTerminalAt          suggestedReply
```

Sibling files in the same job dir: `timeline.jsonl` (event log) and
`tmp/parent-transcript.jsonl` (2.3 MB on `fdfdaf90` — the forked parent's transcript).

Verbatim example (`fdfdaf90`):

```
state    = 'blocked'
detail   = 'commands KB updated; awaiting go on /clear or full catalog pass'
tempo    = 'blocked'
needs    = 'do /clear with resume, or run full command-catalog extraction first?'
suggestedReply = 'do the full command catalog extraction pass'
```

**`state` + `needs` + `suggestedReply` + `output.result` is already an escalation and
completion protocol** — the framework's "dynamic escalation gate" has a native shape to
reuse rather than invent. And because `doSpawnUnlessSettledOnDisk` reads `rh(state)`,
**writing a terminal state here is how a node tells the watchdog "do not restart me".**

## 9. ⚠️ LEDGER CORRECTION — `claude attach` **DOES** exist. So do `stop`, `kill`, `logs`, `rm`, `respawn`

**REFUTED** (the ledger row *"`claude attach` DOES NOT EXIST at this version"* is wrong,
and I am reporting it rather than repeating it). The prior probe read the **root
`--help` command list**, which is not the subcommand surface — the same mistake shape as
the founding incident.

Probe, with a **freshly invented** known-absent control (`zzflorbnix`):

```
$ claude attach --help        rc=0  Usage: claude attach <id>
$ claude stop --help          rc=0  Usage: claude stop <id>
$ claude kill --help          rc=0  Usage: claude stop <id>        (alias)
$ claude logs --help          rc=0  Usage: claude logs <id>
$ claude rm --help            rc=0  Usage: claude rm <id>
$ claude respawn --help       rc=0  Usage: claude respawn <id>|--all
$ claude daemon --help        rc=0  Usage: claude daemon [subcommand] [options]
$ claude zzflorbnix --help    rc=0  Usage: claude [options] [command] [prompt]   ← control: falls through to root help
$ claude peek --help          rc=0  ← root help (NOT a subcommand)
$ claude reply --help         rc=0  ← root help (NOT a subcommand)
$ claude dispatch --help      rc=0  ← root help (NOT a subcommand)
```

Second route, the binary's own dispatcher @261412063 — **shape-enumerated, not guessed**:

```js
if(t[0]==="logs"||t[0]==="attach"||t[0]==="stop"||t[0]==="kill"||t[0]==="respawn"
   ||t[0]==="rm"||t.includes("--bg")||t.includes("--background")){ … }
```
and the hint printer @255761394:
```js
let t=new Set(["logs","attach","stop","kill","respawn","rm"]);
…
[`backgrounded · ${e}`,
  "  claude agents               list sessions",
  `  claude attach ${e}          open in this terminal`,
  `  claude logs ${e}            show recent output`,
  `  claude stop ${e}            stop this session`]
```

Third route, the docs — `$CC/cli-reference.md:29,32,33,35,42,43,45` document
`claude attach`, `claude daemon status`, `claude daemon stop --any`, `claude logs`,
`claude respawn`, `claude rm`, `claude stop` **verbatim**, e.g.:

> `$CC/cli-reference.md:42` — *"`claude respawn <id>` — Restart a background session,
> running or stopped, **with its conversation intact**. Use `--all` to restart every
> running session…"*
>
> `$CC/cli-reference.md:32` — *"`claude daemon status` … **Exits 1 if the supervisor
> isn't running**"*

**Verb table for the framework** (all six are hidden from root `--help`):

| Verb | Effect | Framework use |
|---|---|---|
| `claude agents --json [--all] [--cwd P]` | node census, TTY-free | the poll |
| `claude respawn <id>` | restart, **conversation intact**, running *or stopped* | **the recovery primitive** |
| `claude respawn --all` | restart every running session | version-bump sweep |
| `claude stop <id>` / `claude kill <id>` | stop, conversation kept | cancel a node |
| `claude rm <id>` | delete session **and its worktree**; works on exited sessions | reap |
| `claude logs <id>` | recent terminal output | triage without attaching |
| `claude attach <id>` | open in this terminal | human escalation landing |
| `claude daemon status` | **rc=1 when supervisor dead** | the liveness predicate |
| `claude daemon stop --any --keep-workers` | restart supervisor, leave nodes alive | version/wedge recovery |

⚠️ **All six are behind a remote fleet gate.** Binary @261412063:
`if(!h.isAgentsFleetEnabled()) return h.fleetGateRejected(<verb>)`. Same undocumented-gate
shape as the ledger's nesting/concurrency rows. The framework must probe the gate on the
target host, not assume it.

## 10. The vendor's own semantics — `$CC/agent-view.md` § "The supervisor process"

The docs corpus is far richer here than the ledger's gap statistics would suggest.
Doc hits (control `qqzvvnk9x` → **0 of 175**): `claude daemon` 6 files, `daemon` 10,
`roster` 4, `respawn` 5, `background agent` 16, `watchdog` 7, `re-adopt` **0**.

Verbatim from `$CC/agent-view.md` § *The supervisor process* — these confirm the binary
reading by a second route and add semantics no byte-scan gives:

- *"Background sessions are hosted by a **per-user supervisor process**… starts
  automatically the first time you background a session or open agent view."*
- *"The supervisor keeps **one pre-warmed worker process** ready…"*
- *"Once a session finishes and sits unattached for **about an hour**, the supervisor stops
  its process to free resources. A session you have **pinned** with `Ctrl+T` is exempt…
  When every session has finished and no terminal is connected, **the supervisor itself
  exits**."*
- *"The supervisor also restarts a session whose process exits unexpectedly, **with three
  safeguards**…"* — and the three match the binary's
  `settled_on_disk` / `no_task_contract` / resume-prompt paths exactly:
  1. *"A session whose state on disk already shows it as done, failed, or stopped isn't
     restarted, **unless a reply you sent is still waiting to be delivered**."*
     (= `rh(state) && !queuedPrompt`)
  2. *"Ending the process of a session **you backgrounded with `←` or `/background`**
     yourself, for example with `kill`, marks the session stopped instead of restarting
     it. **A session dispatched with a task, from the agent view input or `claude --bg`,
     is still restarted so the dispatched work completes.**"* (= `interactiveLineage`)
  3. *"A session the supervisor restarts is told it was restarted… A restarted `←` or
     `/background` session also doesn't resume an interrupted response **older than about
     an hour**."* (= `Djb` + `Hjb`)
- *"Session state persists on disk through auto-updates and supervisor restarts. Sessions
  are also preserved when your machine sleeps."* (= the `hostWokeAt` guard)
- *"When you open a session that has stopped responding, the supervisor **restarts its
  process** and the session continues the interrupted response from where it left off."*
  — i.e. **stall recovery is ATTACH-TRIGGERED, not automatic.** This is the second route
  confirming §5's finding that the stall detector only logs.
- *"When the host runs low on memory, the supervisor stops idle non-pinned sessions first."*
- *"A supervisor running an older Claude Code version than the one a session's process was
  started with leaves that process alone."*

### Question (3), answered by the vendor — background-work handoff

> *"Background work the session itself started at the top level **is handed off** when its
> process is stopped, restarted, or updated… The next process started for that session
> picks the work back up:*
> * *A background shell command that finished in the meantime is reported as completed with its output*
> * *A dynamic workflow resumes from where it left off*
> * *A background subagent resumes from its own transcript*
>
> *Work whose state lives **only inside the process** stops with it instead of being handed
> off. That's **shell commands a subagent started**, which the resumed subagent can start
> again, and **running monitors**, whose event stream can't be moved to another process."*

⚠️ **`Monitor` does not survive.** Any node whose design depends on a live `Monitor` loses
it on respawn, silently. Opt out of handoff entirely with
`CLAUDE_CODE_DISABLE_BG_EXIT_HANDOFF=1`.

### Transcript recovery is defensive

> *"A restarted process finds the conversation of a session that moved into a worktree
> mid-task: when the transcript isn't where the session started, Claude Code also looks
> under the repository's registered worktrees. When neither… has the transcript, Claude
> Code **scans all your saved session transcripts as a last resort**…"*
> *"If a restarted session comes back showing only its original prompt because Claude Code
> misread its transcript as empty, the conversation transcript is renamed with an
> **`.orphaned-`** suffix instead of deleted."*

### Where state lives (`$CC/agent-view.md`, verbatim table)

| Path | Contents |
|---|---|
| `~/.claude/daemon.log` | Supervisor log |
| `~/.claude/daemon/roster.json` | List of running background sessions, **used to reconnect after a restart** |
| `~/.claude/jobs/<id>/state.json` | Per-session state shown in agent view |
| `~/.claude/jobs/<id>/tmp/` | Per-session scratch dir; **writes here don't prompt for permission** |

`CLAUDE_JOB_DIR` is set in every background session — consistent with the ledger's
env-strip row.

⚠️ *"If you set `CLAUDE_CONFIG_DIR`, the supervisor uses that directory instead of
`~/.claude` and **runs as a separate instance with its own sessions**."* — a second DAG
universe per config dir. Useful for isolation; fatal if set inconsistently between the
watchdog and the nodes.

## 11. Question (3) — task-list claims, peers and roster on resume

The task-list id resolver, binary @246204753, verbatim:

```js
function u8(){
  if(te.CLAUDE_CODE_TASK_LIST_ID) return te.CLAUDE_CODE_TASK_LIST_ID;
  let e=TU(); if(e) return e.teamName;
  return Km()||VBs||Ot();     // Ot() = this session's id
}
function sK(e){ return Pbr.join(fn(),"tasks",$4e(e)) }        // ~/.claude/tasks/<sanitised>
```

and the fork-carry, @259907526:

```js
async function uYT(e,t){
  let r=Ot();
  if(te.CLAUDE_CODE_TASK_LIST_ID || u8()!==r) return;   // ← NO carry when the id is pinned
  …copy every task entry from sK(r) into sK(e)…         // "[tasks] carry to fork failed"
}
```

CONFIRMED consequences:

- **A respawn reuses `resumeSessionId`, so `Ot()` is unchanged and the session-derived task
  list is the same list.** No re-attachment is needed *in the ordinary respawn case*.
- ⚠️ **But `CLAUDE_BG_POST_CLEAR_RESPAWN` and the `mode:"prompt"` fallback path assign a
  NEW `--session-id`.** With a session-derived list id that is a **brand-new, empty task
  list** — the node silently loses every claim. Pinning `CLAUDE_CODE_TASK_LIST_ID` is
  therefore **mandatory** for the framework, not optional.
- ⚠️ **And pinning it disables the native fork-carry** (`if(CLAUDE_CODE_TASK_LIST_ID) return`)
  — which is what you want for a shared DAG (every node points at the same list) but means
  no per-node inheritance.
- ⚠️ `CLAUDE_CODE_TASK_LIST_ID` is **not** in `RQr`, the env set the supervisor re-applies on
  respawn, and the roster's `dispatch.env` on this host carried only three vars. **An
  exported shell variable will not survive.** Put it in the project's
  `.claude/settings.json` `env` block (ledger: settings assign onto `process.env` and beat
  the shell), which `agent-view.md` independently confirms is how project env reaches a
  background worker.

**No native re-attachment of `SendMessage` peers or the agent roster is described in any
corpus.** `sendMessagePins` are restored into session state (binary @260744861), and the
ledger already establishes that **`ListAgents` is stripped from every async agent**, so
peer *discovery* was never available to a node in the first place. Verdict:
**SUSPECT→CONFIRMED-by-absence** — the framework must re-establish edges itself. The cheap
way is that the roster is derivable from `claude agents --json` **outside** the nodes, by
the watchdog, and re-injected as text.

## 12. `/restart` — how the harness itself respawns a background node

Binary @249150939, verbatim (this is the `/update` + `/restart` path inside a bg session):

```js
if(<work running in background>) return {value:"Can't restart while work is running in
   the background — wait for it to finish, then try again."};
…await session flush (30 s bound, "session flush")…
let y={...process.env};
for(let b of RQr) delete y[b];
delete y.CLAUDE_JOB_DIR;
for(let b of Object.keys(y)) if(b.startsWith("CLAUDE_BG_")) delete y[b];
spawn(g.cmd,[...g.prefixArgs,"respawn",m],{detached:!0,stdio:"ignore",env:y,cwd:homedir()});
…"If it doesn't come back within a minute, run `claude respawn <short>` from a terminal."
```

**The harness's own recovery recipe is: flush the transcript, strip every `CLAUDE_BG_*`
and `CLAUDE_JOB_DIR`, then `claude respawn <short>` detached from `$HOME`.** Copy it.
Note the explicit precondition — *do not respawn a node with live background work*.

## 13. LIVE PROBE — I killed a real background node with `kill -9` and it came back

**I did this on this host**, 2026-08-05, v2.1.222. Cost: one haiku session, ~1.2 k tokens.
Host state was restored afterwards (see §13d).

### 13a. Spawn

```
$ cd <scratchpad>/probe
$ claude --bg --model haiku "Count slowly from 1 to 400, one number per line, with a short
   comment after every tenth number. Do not use any tools."          # rc=0
Starting background service…
backgrounded · 2102fbc9
  claude agents             list sessions
  claude attach 2102fbc9    open in this terminal
  claude logs 2102fbc9      show recent output
  claude stop 2102fbc9      stop this session
```

Roster after 12 s:

```
pid = 91898   procStart = Wed Aug  5 08:39:40 2026   attempt = 1
sessionId = 2102fbc9-c9f4-472b-ada0-db636da4f174     cliVersion = 2.1.222
launch: prompt | source: shell
seed: {'intent': 'Count slowly from 1 to 400, …'}
all workers: ['2102fbc9']
```

⚠️ **Control-arm observation with real consequences:** the roster held **3 stale workers
from 2026-07** before this run and held **only the new one after**. Starting the supervisor
**reaped** them; it did **not** respawn them. Second route — the adoption path, binary
@252764483:

```js
static async adopt(e,t,r,n){
  … if(!_C(t.pid)) return null;                       // pid not alive → no handle
  let o=await nP(t.pid,{skipCache:!0});
  if(o && t.procStart!==o) return null;               // procStart mismatch → no handle
  … state:"adopted", detail:"adopted from previous supervisor" …
}
```
A dead pid produces **no worker handle**, so there is **no exit event and therefore no
respawn**. Their `~/.claude/jobs/<id>/` dirs and transcripts all survived. Pre-flight arm:
`ps -p 14595/11251/5748/87604` → all DEAD; control `ps -p $$` → ALIVE.

### 13b. `kill -9`, and the respawn

Pre-kill `state.json` (verbatim, trimmed):

```
state = 'done'          detail = '<the prompt>'      tempo = 'active'
tokens = 1249           firstTerminalAt = '2026-08-05T08:39:53.360Z'
respawnFlags = ['--model','haiku','--permission-mode','default']
name = 'slow counting with comments'   nameSource = 'auto'
bridgeSessionId = 'cse_019pA9NCx3jchVajimcTmW6X'
```

```
$ kill -9 91898      # rc=0
$ ps -p 91898 …      → pid 91898 confirmed dead
```

**~36 s later**, with no human action:

```
$ claude agents --json --all
{'pid': 21335, 'id': '2102fbc9', 'kind': 'background',
 'startedAt': 1785919219329,       ← NEW (was 1785919180389)
 'sessionId': '2102fbc9-c9f4-472b-ada0-db636da4f174',   ← SAME
 'name': 'slow counting with comments', 'status': 'idle', 'state': 'working'}

roster:  pid 21322   attempt 2   procStart Wed Aug  5 08:40:16 2026
state.json: state = running   tempo = idle
```

```
$ claude logs 2102fbc9
…
[worker crashed (exit -1) — respawning…]
…
Claude 3:40 AM
I've counted from 1 to 400, with a short comment after every tenth number…
```

**CONFIRMED end-to-end**: `kill -9` on a `claude --bg` node → detected → respawned with the
**same `sessionId`** and `attempt` incremented to 2 → the conversation continued. The dim
notice `[worker crashed (exit -1) — respawning…]` is `scheduleRespawn`'s, verbatim.

⚠️ Note the respawn happened **even though `state.json` said `state:'done'`** at kill time
(`tempo` was `'active'`). So the docs' *"a session whose state on disk already shows it as
done … isn't restarted"* is **not a `state=='done'` string test** — the terminal predicate
`rh()` is narrower than the doc sentence implies. **Do not rely on writing
`state:"done"` to stop the watchdog** without probing `rh()` on the exact shape you write.
Marked **SUSPECT** — one route only, and it contradicts the docs.

### 13c. What the probe did NOT establish

`grep -c "automatically restarted after its process exited unexpectedly"` on the
transcript → **0**; control `grep -c "Count slowly"` → **3**. So the `Djb` resume prompt is
**injected in memory only and never written to the transcript** — a framework cannot audit
from the jsonl whether a node was told it had restarted.

`grep -oE "interrupted[a-zA-Z_]*"` → **0 matches**: the killed turn had already completed,
so `turnInterruptionState` was `{kind:"none"}`. **The mid-tool-call interruption path
(`dropSiblingBlocks` / `shutdownUnwindResultsDoNotResolve`) is CONFIRMED from the binary
but NOT exercised by this probe.** Treat §7's "what is lost" as code-confirmed,
probe-unconfirmed.

Incidental but load-bearing: the transcript contains
`"You ended the turn without calling SendUserMessage. In brief mode, plain assistant text is
hidden from the user…"` — **background sessions run in brief mode**, so a node's plain text
is invisible. Consistent with the ledger's `PEWTER_OWL` row, and it means **framework
output from a node must go through `SendUserMessage` or a file, never plain text.**

### 13d. `claude stop` and cleanup (host restored)

```
$ claude stop 2102fbc9   → stopped 2102fbc9         (rc=0)
   state.json: state = 'stopped'  detail = 'stopped'  tempo = 'idle'
   roster workers: []            ← removed, NOT respawned
$ claude rm 2102fbc9     → removed 2102fbc9         (rc=0)
$ claude daemon stop --any → no daemon running      (rc=0)
$ claude daemon status   → not running, 0 workers   (rc=1)
```

**`claude stop` writes `state:"stopped"` and the watchdog honours it.** That is the
framework's clean "this node is finished, do not resurrect it" primitive — and it is the
one terminal write I *did* observe suppressing respawn.

## 14. Question (4) — cron / scheduled tasks / daemon as watchdog candidates

### `CronCreate` is DISQUALIFIED — from its own loaded schema

REFUTED as a watchdog. Verbatim from the tool definition loaded via `ToolSearch`:

> *"**Session-only** — Jobs live only in this Claude session — nothing is written to disk,
> and the job is gone when Claude exits."*
> `durable`: *"**Has no effect — durable persistence is not available.** All jobs are
> session-only (in-memory, gone when this Claude session ends)."*
> *"Jobs only fire **while the REPL is idle** (not mid-query)."*
> *"Recurring tasks **auto-expire after 7 days** — they fire one final time, then are
> deleted. This bounds session lifetime."*
> *"**Not for live watching** … use the Monitor tool instead."*

A cron job hosted inside the session it is supposed to watch dies with that session. It
**cannot** detect the crash it exists to detect. And "fires only while the REPL is idle"
means a wedged node never fires its own watchdog.

### `/loop`, Desktop tasks, cloud Routines

`$CC/desktop-scheduled-tasks.md` gives the vendor's own comparison table verbatim:

| | Cloud (routines) | Desktop | `/loop` |
|---|---|---|---|
| Runs on | Anthropic cloud | Your machine | Your machine |
| Requires machine on | No | **Yes** | **Yes** |
| Requires open session | No | No | **Yes** |
| Persistent across restarts | Yes | Yes | Restored on `--resume` if unexpired |
| Access to local files | **No (fresh clone)** | Yes | Yes |
| Minimum interval | **1 hour** | 1 minute | 1 minute |

- **Cloud routines** (`$CC/routines.md`): *"execute on Anthropic-managed cloud
  infrastructure"*, *"in research preview"*, min interval 1 h, **no access to local files**,
  and *"count against your account's daily run allowance"*. They cannot see
  `~/.claude/daemon/roster.json`. **Disqualified as a local watchdog**; still useful as a
  *heartbeat auditor* that reads a repo-committed status file.
- **Desktop scheduled tasks**: local, 1-minute granularity, persistent — but *"only fires
  while the app is open and your computer is awake"*. Requires **Claude Code Desktop**.
  Viable only if the operator runs Desktop permanently.
- **`/loop`**: same-session. Same disqualification as `CronCreate`.

### `claude daemon` as the watchdog

CONFIRMED and **partially disqualified by its own help text**:

> *"**Service install is disabled in this version** — the daemon runs on demand and exits
> when the last client disconnects."*

corroborated by `$CC/agent-view.md`: *"When every session has finished and no terminal is
connected, the supervisor itself exits."* And `uninstall` exists while `install` does not,
so the launchctl/systemd path **existed and has been withdrawn at 2.1.222**.

**Net answer to (4): there is no native always-on local watchdog at 2.1.222.** The
supervisor is an excellent *in-life* watchdog (5 s pid poll, 60 s procStart check, 10 s
respawn, 20-attempt cap) and it survives its own restarts via `roster.json` — but nothing
starts it after it exits, and it exits when the DAG goes idle. **The outermost loop must be
OS-level (`launchd`) or an external process.** `mise run` + a `launchd` plist calling
`claude agents --json` is the honest shape.

---

# RECOVERY DESIGN — three options for the framework

Common substrate, whichever option is chosen. **Per node, persist beyond the task list:**

| Datum | Where | Why |
|---|---|---|
| ticket id ⇄ `daemonShort` ⇄ `sessionId` | framework's own DAG file | `claude agents --json` gives `id` + `sessionId`; you need the ticket edge |
| `CLAUDE_CODE_TASK_LIST_ID` | **project `.claude/settings.json` `env` block** | not in `RQr`; a shell export dies on respawn (§11) |
| the node's contract / re-entry instructions | `CLAUDE_CODE_RESUME_PROMPT` in the launch env | overrides `Djb` via `??=`; the ONLY text a respawned node is guaranteed to see (§7) |
| `attemptBudget` consumed | framework file | the harness's `attempt` resets after a healthy 5 min (§6) — it is **not** your retry cap |
| peers / roster | framework file, re-injected as text | no native re-attachment; `ListAgents` is denied to async agents (ledger) |
| last verified artifact (branch, PR#, files) | framework file + the repo | the resume prompt tells the node to *re-verify*; give it something to verify against |
| `cwd` and worktree path | framework file | **cwd gone ⇒ permanently unrecoverable** (§6) |

**Never** depend on a live `Monitor` inside a node (§10), and never parse a node's plain
text — it is hidden in brief mode (§13c).

## Option A — "Ride the supervisor" (thinnest)

Nodes are `claude --bg` sessions. The harness's own supervisor is the watchdog. The
framework adds only:

1. A `launchd` agent (`~/Library/LaunchAgents`, `StartInterval 60`) running a
   `mise run dag-tick` task that: `claude agents --json --cwd <repo>` → for every node the
   DAG expects, assert it is present; if absent or `state` is `crashed`/`stopped`, call
   `claude respawn <id>`; if `claude daemon status` rc≠0 while nodes should be live, run
   `claude agents --json` (which restarts the supervisor and re-adopts).
2. Per-node contract in `CLAUDE_CODE_RESUME_PROMPT`.
3. Terminal completion via `claude stop <id>` (observed to suppress respawn, §13d).

**Pros** — almost no new code; inherits 5 s pid polling, PID-reuse defence, sleep/wake
handling, transcript recovery across worktrees, background-work handoff.
**Cons** — inherits a **fixed 10 s, non-exponential** respawn delay and a 20-attempt cap
you do not control; the fleet gate can turn the whole verb set off; a **wedged** node is
never recovered (stall detection only logs); `state:'done'` did **not** suppress respawn in
the live probe, so "done" needs its own framework-side enforcement.

## Option B — "Supervise the supervisor" (recommended)

Option A plus a framework-owned **liveness contract** that closes the two real gaps —
hang detection and retry accounting.

1. **Heartbeat, node-written.** Every node writes `<dagdir>/<ticket>/heartbeat.json`
   (`{ts, ticket, sessionId, phase, lastArtifact}`) at each phase boundary and after every
   long tool call. `$CLAUDE_JOB_DIR/tmp` is permission-free (`$CC/agent-view.md`) but is
   deleted with the session — so write to the **repo-side DAG dir**, not the job dir.
2. **The tick** (launchd, 60 s) classifies each expected node into exactly one of:
   `ALIVE` (in `agents --json`, heartbeat < 5 min) · `DEAD` (absent, or present with
   `state` in {crashed, stopped} ) · `WEDGED` (present, heartbeat stale > 15 min) ·
   `DONE` (framework-side terminal marker present).
3. **Actions.** `DEAD` → `claude respawn <id>` if the framework's own `attemptBudget` is
   unspent, else escalate. `WEDGED` → `claude stop <id>` then `claude respawn <id>` (this
   is exactly the harness's own attach-stall recipe, binary @255667453: SIGTERM, wait,
   re-dispatch with `source:"respawn"`), decrementing the budget. `DONE` → `claude stop`.
4. **Retry cap is the framework's**, not `attempt`'s — `attempt` resets after 5 healthy
   minutes and would let a slow-failing node loop forever.
5. **Escalation** rides the harness's own vocabulary: the node writes `needs` +
   `suggestedReply` into its state and the framework surfaces them, mirroring
   `~/.claude/jobs/<id>/state.json`'s existing shape (§8).

**Pros** — covers the hang case the harness does not; retry policy is yours and auditable;
uses only documented verbs. **Cons** — a heartbeat convention every node must honour, and
one more file per ticket.

## Option C — "Own the loop" (`--print` workers, no supervisor)

Nodes are `claude -p` / `--output-format stream-json` processes the framework spawns and
supervises itself (an external Python supervisor + `launchd`), resuming with
`claude --resume <sessionId>`.

**Pros** — total control of backoff, caps, env, and concurrency; no fleet gate; no daemon
version skew; stream-json gives structured turn events.
**Cons** — you give up everything §6/§7/§10 buys: no `roster.json` re-adoption, no
background-work handoff, no interrupted-turn unwinding (`CLAUDE_CODE_RESUME_INTERRUPTED_TURN`
is set *by the supervisor*, so you must set it yourself and it is an undocumented,
gate-guarded contract), no PTY, no `claude attach` for a human. Also the ledger's
**`claude -p` stdout can be a receipt, not the answer** trap applies with force here.
Recommend **against** unless the fleet gate turns out to be off on the target host.

**Recommendation: B.** A is one launchd plist away and is strictly better than nothing; B
adds the two things the harness demonstrably does not do (hang recovery, framework-owned
retry accounting) for a heartbeat file per ticket. C only becomes correct if
`isAgentsFleetEnabled()` is false here — **probe that before designing** (see the open
questions).

---

## Ledger entries to append

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| ⚠️ **`claude attach` DOES exist** — and so do `stop`, `kill`, `logs`, `rm`, `respawn`, `daemon`. The earlier REFUTED row read the ROOT `--help` command list, which is not the subcommand surface | REFUTED (corrects a ledger row) | `claude attach --help` rc=0 with distinct text; control `claude zzflorbnix --help` → root help; binary dispatcher `Set(["logs","attach","stop","kill","respawn","rm"])`; `$CC/cli-reference.md:29,32,33,35,42,43,45` | 2.1.222 | 2026-08-05 |
| **A background node killed with `kill -9` is respawned automatically**, same `sessionId`, `attempt`→2, ~36 s later, conversation intact | CONFIRMED | live probe; `claude logs` → `[worker crashed (exit -1) — respawning…]`; roster pid+procStart changed | 2.1.222 | 2026-08-05 |
| Liveness = `kill(pid,0)` **every 5 s** + `procStart` comparison **every 60 s**; PTY workers defer to the PTY exit event | CONFIRMED | binary `startPidPoll`/`checkPid` @252786470 | 2.1.222 | 2026-08-05 |
| ⚠️ **A HUNG node is detected but never recovered** — rv-heartbeat gap > 120 s while `tempo==="active"` emits `tengu_bg_worker_stalled` and nothing else; recovery is attach-triggered | CONFIRMED | binary + `$CC/agent-view.md` ("when you open a session that has stopped responding…") | 2.1.222 | 2026-08-05 |
| Respawn: **fixed 10 s delay (not exponential)**, cap **20 attempts**, 3-fast-crash breaker, and `attempt` **RESETS to 1** after a 5-minute healthy run | CONFIRMED | binary `scheduleRespawn` @252783762; constants `QJp=20, Pjb=1e4, eXp=5000, Ljb=300000` | 2.1.222 | 2026-08-05 |
| Three respawn refusals: `settled_on_disk`, `no_task_contract` (interactive lineage + external signal), and **cwd gone ⇒ permanently unrecoverable**. **`exec`-mode workers are NEVER auto-respawned** | CONFIRMED | binary `doSpawnUnlessSettledOnDisk`, `settleCwdGone`, `"exec workers are never auto-respawned"` | 2.1.222 | 2026-08-05 |
| ⚠️ **`state:"done"` on disk did NOT suppress the respawn** in a live probe, contradicting `$CC/agent-view.md`. `claude stop` (→ `state:"stopped"`) DID | SUSPECT / CONFIRMED | live probe both ways | 2.1.222 | 2026-08-05 |
| The default crash-resume prompt is `CLAUDE_CODE_RESUME_PROMPT`, set with `??=` so it is **overridable per node**, and it is **never written to the transcript** | CONFIRMED | binary `Djb`; transcript grep 0, control 3 | 2.1.222 | 2026-08-05 |
| What is lost from an interrupted turn: unresolved `tool_use` blocks are **dropped and unwound** (`dropSiblingBlocks`, `shutdownUnwindResultsDoNotResolve`); a turn older than **1 h** is not auto-resumed; a node with **no flushed messages at all is unrecoverable** | CONFIRMED (code) / not probe-exercised | binary @251758057, @252772981 | 2.1.222 | 2026-08-05 |
| `~/.claude/jobs/<id>/state.json` is a per-node ledger carrying `state, detail, tempo, needs, suggestedReply, output.result, tokens, inFlight, intent, respawnFlags, resumeSessionId, cwd, linkScanPath, fork*, bridge*` — an escalation protocol the framework can reuse rather than invent | CONFIRMED | 3 real job dirs + 1 probe, shape-enumerated | 2.1.222 | 2026-08-05 |
| `~/.claude/daemon/roster.json` per worker carries `pid + procStart + attempt + respawnFlags + dispatch.seed{intent,name} + isolation`; **a dead pid or a `procStart` mismatch makes `adopt()` return null**, so stale entries are reaped, never respawned | CONFIRMED | binary `adopt()` @252764483; live: 3 stale workers reaped on supervisor start | 2.1.222 | 2026-08-05 |
| ⚠️ **`CLAUDE_CODE_TASK_LIST_ID` is NOT in the respawn env set `RQr`** — an exported shell var dies on respawn; it must live in the project `settings.json` `env` block. Unpinned, the id defaults to the **session id**, so any respawn that mints a new session id gets an EMPTY task list | CONFIRMED | binary `u8()` @246204753, `RQr` @241422305 | 2.1.222 | 2026-08-05 |
| ⚠️ **`CronCreate` cannot be a watchdog** — session-only, `durable` has NO effect, fires only while the REPL is idle, auto-expires after 7 days | REFUTED (as a candidate) | the tool's own loaded schema | 2.1.222 | 2026-08-05 |
| **There is no native always-on local watchdog**: `claude daemon` service install is **disabled in this version**; the supervisor exits when the last client disconnects. Cloud routines have no local file access and a 1 h minimum; Desktop tasks need the Desktop app open | CONFIRMED | `claude daemon --help`; `$CC/agent-view.md`; `$CC/desktop-scheduled-tasks.md` comparison table | 2.1.222 | 2026-08-05 |
| A background session runs in **brief mode** — plain assistant text is hidden; output must go through `SendUserMessage` or a file | CONFIRMED | live probe transcript meta message | 2.1.222 | 2026-08-05 |
| `Monitor` does **not** survive a node restart, nor do shell commands a subagent started; background shell commands, dynamic workflows and background subagents DO | CONFIRMED | `$CC/agent-view.md` § handoff | 2.1.222 | 2026-08-05 |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed binary
  `~/.local/share/claude/versions/2.1.222` and its `--help` surface are the primary corpus;
  the vendor doc tree mirrored under the knowledge-base is this product's documentation.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline
  vendor doc tree `$CC` (`agent-view.md`, `cli-reference.md`, `routines.md`,
  `scheduled-tasks.md`, `desktop-scheduled-tasks.md`).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the ledger
  `.claude/agents/claude-code-expert.md` and the design doc `docs/agent-team.md` this
  research feeds.
