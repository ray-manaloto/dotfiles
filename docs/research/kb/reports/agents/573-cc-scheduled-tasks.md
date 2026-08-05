# Claude Code expertise — scheduling surfaces vs launchd for the #573 pull-loop tick (2026-08-05, v2.1.222)

**STATUS: complete**

Question: can any Claude Code native scheduling surface REPLACE or COMPLEMENT
launchd as the outer ~60 s tick that runs `mise run <task>` in
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`?

Corpora consulted: installed binary (`~/.local/share/claude/versions/2.1.222`,
271,289,792 bytes), loaded tool schemas, `claude --help` + hidden-subcommand
probes, offline docs (`$CC =
~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`,
175 pages), live probes on this host.

**Headline: launchd stays. No surface can replace it, and the reason is not
persistence — it is that every Claude scheduling surface fires a PROMPT, never a
command.** Two surfaces earn narrow complementary roles.

## Verdict table

| # | Surface | Verdict | The single deciding fact |
|---|---|---|---|
| 1 | `CronCreate`/`CronList`/`CronDelete` | **REJECT** | Fires a prompt into the live session's queue (`Yv({mode:"prompt"…})`) — a model turn, not a command. Needs a live REPL; `durable` gate is **OFF** on this host |
| 2 | `/loop` + `ScheduleWakeup` | **REJECT** | Same enqueue path. Carries over to a background session, but that supervisor "exits when the last client disconnects" and **service install is disabled in this version** |
| 3 | Cloud routines (`/schedule`) | **REJECT** as tick · **COMPLEMENT** as off-machine escalation | Executes on Anthropic infrastructure against a **fresh clone** — cannot see this Mac's tree or run `mise`. Minimum interval **1 hour**, shorter expressions "are rejected" |
| 4 | Desktop scheduled tasks | **REJECT** as tick · **COMPLEMENT** as supervisory repair lane | Runs locally with real file access (the app IS installed and running here), but only "while the desktop app is running and your computer is awake", plus a deterministic **few-minutes stagger** — fatal at 60 s |
| 5 | `createCronScheduler`/`isKairosCronEnabled` | **SETTLED** (was SUSPECT) | Gate is **ON**; the scheduler is constructed and `.start()`ed inside the REPL. Its only consumer is the prompt-enqueue callback. The **durable** sub-gate is OFF |
| 6 | Anything new (flags / subcommands / settings) | **NONE FOUND** | 0 scheduling flags in `--help`, 0 hidden subcommands (control-armed), 0 settings keys. 2 undocumented env tokens exist and neither confers durability |

## Findings

### 1. CONFIRMED — a cron fires a PROMPT into the session's queue, not a command

This is the architectural disqualifier and it is upstream of every persistence
question. The scheduler's fire callback, verbatim from the binary at the REPL
construction site:

```js
if(Wdh.isKairosCronEnabled()){
  let Vr=(on,yt)=>{
    if(O)return;
    let Ao=$pv.resolveLoopDefaultFire(on);
    Yv({mode:"prompt",agentId:ki(),value:Ao,uuid:zM.randomUUID(),
        priority:"later",isMeta:!0,skipSlashCommands:!0,
        modelScheduledOrigin:!0,wakeupSource:yt,workload:psr});
    to("cron_fire");ii()
  };
  So=Lpv.createCronScheduler({
    onFire:(on)=>Vr(on,"schedule_wakeup"),
    onFireTask:(on)=>Vr(on.prompt,i5o(on)),
    isLoading:()=>g||O,
    getJitterConfig:Npv.getCronJitterConfig,
    isKilled:()=>!Wdh.isKairosCronEnabled()
  });
  So.start()
}
```

`Yv({mode:"prompt", …})` enqueues a **user-turn prompt** at `priority:"later"`.
Nothing is exec'd. One tick = one model turn that must then decide to call `Bash`,
clear the permission system, and produce a `mise run` invocation.

Consequences for a 60 s tick, none of which launchd has:

- **Every tick costs tokens.** The deterministic Python scheduler costs zero model
  tokens under launchd; under cron it costs a full turn (system prompt +
  transcript + tool round-trip) — 1,440 turns/day at 60 s.
- **The tick is non-deterministic.** The model may summarise instead of running,
  or run something adjacent. `mise run <task>` is a *guarantee* under launchd and
  a *request* under cron.
- **`skipSlashCommands:!0`** — the fired prompt bypasses slash expansion, so the
  `claude -p "/verb"` prefix-expansion route (existing ledger row) is unavailable
  inside a cron fire.
- **Fires only between turns.** `$CC/scheduled-tasks.md:172`: "A scheduled prompt
  fires between your turns, not while Claude is mid-response." A busy session
  defers its own tick, and there is **no catch-up** (`:215`) — one fire when idle,
  not one per missed interval.

Control arm: the same binary's `Monitor` tool *does* run a script directly, and
`CronCreate`'s own description points at it ("To watch a log file, process, or
command output … use the Monitor tool instead"). The cron path deliberately does
not exec.

### 2. CONFIRMED — `durable: true` exists in the binary and is OFF on this host

`$CC/scheduled-tasks.md` describes cron tasks as session-scoped throughout and
never documents a `durable` parameter. The binary has one, behind a gate:

```js
function FX(){return!tr(process.env.CLAUDE_CODE_DISABLE_CRON)&&hEe("tengu_kairos_cron",!0,H$u)}
function $Ue(){return hEe("tengu_kairos_cron_durable",!0,H$u)}
```

Both are `hEe(...)` remote feature gates with a **local default of `true`**. Every
user-facing string is a ternary on `$Ue()`, which makes the **live tool schema its
own control-armed probe** — the branches are mutually exclusive and both ship.

Loaded live on this host, all three tools returned the **negative** branch:

| Tool | Live text on this host | The other branch (also in the binary) |
|---|---|---|
| `CronCreate.durable` | "**Has no effect — durable persistence is not available.** All jobs are session-only (in-memory, gone when this Claude session ends)." | "true = persist to .claude/scheduled_tasks.json and survive restarts" |
| `CronList` | "List all cron jobs scheduled via CronCreate **in this session**." | "…both durable (.claude/scheduled_tasks.json) and session-only." |
| `CronDelete` | "Removes it from **the in-memory session store**." | "Removes it from .claude/scheduled_tasks.json (durable jobs) or the in-memory session store" |

Three independent strings, all negative, mutually consistent — `tengu_kairos_cron_durable`
is **OFF for this host** despite the code default being `true`. It is a remote gate
someone else owns, so it can flip without a release.

The parameter is present in the schema and inert — exactly the shape that reads as
a capability to anyone who greps for the field name and stops there.

### 3. CONFIRMED — even with the gate ON, durable ≠ unattended

Worth settling because the gate could flip. Durable buys *restart survival*, not
*fire-while-nothing-runs*. The binary's own catch-up text:

```
The following one-shot scheduled task${s were/ was} missed while Claude was not
running. ${They have/It has} already been removed from .claude/scheduled_tasks.json.
Do NOT execute ${these prompts/this prompt} yet. First use the AskUserQuestion tool
to ask whether to run ${each one/it} now. Only execute if the user confirms.
```

A durable task that came due while the REPL was closed is **missed, deleted, and
surfaced for confirmation** — not executed, and it requires a human answer. The
scheduler lives inside the REPL process (`createCronScheduler` is constructed
there; `isKilled` ties it to the same gate). There is no scheduling daemon.

That disqualifies the whole cron family from the outer tick, gate or no gate.

### 4. CORRECTED — the jitter numbers in the tool prose are stale; do not cite them

Nearly published as a finding. `CronCreate`'s live description says "recurring
tasks fire up to **10% of their period late (max 15 min)**". That sentence is a
**hardcoded string literal** in the prompt template, not interpolated from config
— verified by dumping the template source, where `${YPe}` and `${r}` *are*
interpolated in adjacent sentences and the jitter numbers are not.

The real config is `getCronJitterConfig()` = `hEe("tengu_kairos_cron_config", dhe, _k_)`,
local default:

```js
dhe={recurringFrac:0.5, recurringCapMs:1800000, oneShotMaxMs:90000,
     oneShotFloorMs:0, oneShotMinuteMod:30, recurringMaxAgeMs:604800000,
     cacheLeadMs:15000}
```

`recurringFrac: 0.5`, `recurringCapMs: 1800000` = **half the period, capped at 30
min** — matching `$CC/scheduled-tasks.md:180` and contradicting the tool's own
prose. On a 60 s period that is up to **30 s of jitter**, a 50% timing error, and
it is remote-gated so it can move without a release.

Trust `dhe`/the docs, not the tool description. Whether the remote config
currently overrides `dhe` here is **NOT established** — the prose cannot tell you,
because it is a literal.

### 5. CONFIRMED — live probe: created, listed, no disk write, deleted

Full transcript on this host, from a teammate agent in session
`5f268f59-fb82-4b3a-a4eb-2b6d4f7584cc`:

```
CronCreate{cron:"37 3 14 3 *", recurring:false, durable:true}
  → ERROR: durable crons are not supported for teammates
           (teammates do not persist across sessions)

CronCreate{cron:"37 3 14 3 *", recurring:false}
  → Scheduled one-shot task 6cc47c35 (37 3 14 3 *).
    Session-only (not written to disk, dies when Claude exits).

CronList
  → 6cc47c35 — 37 3 14 3 * (one-shot) [session-only]: PROBE-573-NOOP…

CronDelete{id:"6cc47c35"} → Cancelled job 6cc47c35.
```

The cron was scheduled for 14 March — months away and one-shot, so it could not
fire during the probe; it was deleted regardless. Disk, before and after, with the
control arm on every negative:

```
find /Users/rmanaloto -maxdepth 6 -name scheduled_tasks.json  → (empty, both times)
find /Users/rmanaloto -maxdepth 6 -name scheduled_tasks.lock  → .../dotfiles/.claude/scheduled_tasks.lock
```

The `.json` negative is armed: the identical `find` locates the `.lock`, so the
probe can see files of that shape in that place. **Zero durable tasks exist
anywhere on this machine**, consistent with the gate being off.

The teammate refusal names a *different* reason than the schema text, so I read
the call sites rather than pick one. Every description is rendered from `$Ue()`
alone, with no teammate term:

```js
durable:YU(E.boolean().optional()).describe($bs($Ue()))
async description(){return Nbs($Ue())}   async prompt(){return Fbs($Ue())}
async prompt(){return jbs($Ue())}        async prompt(){return Ubs($Ue())}
```

Both facts are true and independent: the gate is off, *and* teammates are
separately barred in `validateInput`. The apparent disagreement was two mechanisms,
not a broken probe.

Two side-findings worth keeping:

- **`CronList` is agent-scoped.** `call()` does
  `(t?e.filter((o)=>o.agentId===t.agentId):e)` — a teammate sees only its own jobs.
  A supervisor cannot enumerate a worker's crons.
- **`CronCreate` needs classifier review in auto mode.**
  `checkPermissions(){ if(hn(t).mode==="auto") return {behavior:"passthrough",
  message:"Scheduling a cron prompt requires classifier review."} }` — an
  autonomous background node cannot silently self-schedule.

### 6. CONFIRMED — the cron scheduler is single-writer per project directory (undocumented)

Creating the probe cron rewrote `.claude/scheduled_tasks.lock` (Jul 5 10:51, 129 B
→ Aug 5 15:29, 130 B), taking the lock under the *parent session* id:

```json
{"sessionId":"5f268f59-fb82-4b3a-a4eb-2b6d4f7584cc","pid":98962,
 "procStart":"Wed Aug  5 01:40:24 2026","acquiredAt":1785961740944}
```

The acquire function `U$l`:

```js
async function U$l(e){
  let r=e?.lockIdentity??Ot(),
      n={sessionId:r,pid:process.pid,procStart:SIe(),acquiredAt:Date.now()};
  if(await Fth(n,t)) return …,!0;                      // exclusive create (flag:"wx")
  let o=await Bth(t);
  if(o?.sessionId===r){ if(o.pid!==process.pid) await k$e.writeFile(…); return !0 }  // re-entrant
  if(o&&_C(o.pid)&&await SU(o.pid,o.procStart)){        // holder alive?
    …C(`[ScheduledTasks] scheduler lock held by session ${o.sessionId} (PID ${o.pid})`);
    return !1 }                                          // ← second session gets NO scheduler
  if(o)C(`[ScheduledTasks] recovering stale scheduler lock from PID ${o.pid}`);
  await k$e.unlink(cjn(t)).catch(()=>{});
  return await Fth(n,t) ? (…,!0) : !1
}
```

So **exactly one live session per project directory runs the cron scheduler**. A
second concurrent session in the same repo silently gets none — `return !1`, a
debug log, no user-visible error. Staleness is decided by the same `pid` +
`procStart` liveness pair the daemon roster's `adopt()` uses (existing ledger row),
so a crashed holder's lock is recovered rather than leaked.

`$CC/scheduled-tasks.md` documents none of this; its only mention of the file is
line 217 (scheduling fails when the file or directory is a symlink).

⚠️ **Counting correction, made before publishing.** I first wrote "`grep -c lock`
→ 0" from memory rather than running it. Actually run:
`grep -ci lock $CC/scheduled-tasks.md` → **1**, `grep -ci durable` → **1**
(control: `grep -ci cron` → 15). Reading the hits shows both are false positives
for the claim:

- line 178 — "the same wall-**clock** moment" (substring, not a lock file)
- line 187 — "…use Routines or Desktop scheduled tasks for **durable** scheduling"
  (the English word, not the parameter)

The substantive claims hold — the page documents neither the lock nor the `durable`
parameter — but the counts I nearly published were wrong, and a bare "0 hits" would
have been a substring artifact in exactly the shape this agent's founding incident
warns about. **State the count and read the hits.**

### 7. CONFIRMED — `/loop`'s only "no terminal" route dies with the daemon

`$CC/agent-view.md:396` does confirm the carryover the map flagged:

> "Backgrounding starts a fresh process that resumes from the saved conversation,
> and in-flight work moves to it: running background shell commands, backgrounded
> subagents, dynamic workflows, and scheduled tasks you created with `/loop` all
> carry over and keep running there."

So a `/loop` genuinely survives losing its terminal, and agent view renders it
(`:124` — "`✢` A `/loop` session sleeping between iterations … run count and a
countdown"). That is the strongest local case for Claude-side scheduling, and it
still fails, because of what supervises it. Verbatim from `claude daemon --help`
on this host:

```
  Service install is disabled in this version — the daemon runs on demand
  and exits when the last client disconnects.
```

`uninstall` is offered; `install` is not. So the background session that hosts the
carried-over loop has **no service to restart it after logout or reboot**, and the
supervisor itself exits once the last client disconnects. This re-verifies the
existing ledger row at 2.1.222 rather than inheriting it.

### 8. REFUTED — `CLAUDE_CODE_LOOP_PERSISTENT` does not make a loop persistent

The most promising-looking discovery of the sweep, and it does not survive reading.
Both tokens are **0 of 175 doc pages** (control: `CLAUDE_CODE_SUBAGENT_MODEL` → 5
pages; fresh `CLAUDE_CODE_ZZFRESH8842` → 0), so they are genuinely undocumented —
but neither confers durability:

```js
function eTo(){if(te.CLAUDE_CODE_LOOP_PERSISTENT)return!0;
               return Qe("tengu_kairos_loop_persistent",!1)}
function Tbs(){return eTo()?qNu:gbs}        // getAutonomousLoopPreamble
```

`eTo()` (`isLoopPersistentPreambleEnabled`) selects **which preamble text** the
loop is given, and softens the stop condition — with it on, the loop ends only when
"newly blocked on a decision you won't make alone"; with it off, also on "third
straight tick with nothing to do". It is a **prompt variant that makes the model
less likely to quit**, not a mechanism that outlives the process.

`CLAUDE_CODE_LOOP_KEEPALIVE` is a **fallback heartbeat inside a live session**:

```js
function r$u(){if(tr(process.env.CLAUDE_CODE_LOOP_KEEPALIVE))return!0;
               return Qe("tengu_kairos_loop_keepalive",!1)}
function o$u(e){if(!wKe()){GNt("gate_off");return null}
  if(y8n()>=Nk_){C("[loop] keepalive budget exhausted (model declined to reschedule twice) — ending loop");
    GNt("model_stopped",{via_keepalive:!0});return null}
  return s$u(Lk_,e,{viaKeepalive:!0})}
```

It re-arms a self-paced loop when the model forgets to, with a budget of two
declines. Both are session-bound. A name is not a semantics — worth stating plainly
because "LOOP_PERSISTENT" is precisely the token someone would cite as proof that
`/loop` can carry an unattended tick.

### 9. CONFIRMED — cloud routines cannot reach this Mac, and floor at 1 hour

Two independent hard stops, either sufficient:

- **Execution locus is Anthropic's infrastructure on a fresh clone.**
  `$CC/routines.md:13` — "Routines execute on Anthropic-managed cloud
  infrastructure"; `:73` — "Each repository is cloned at the start of a run,
  starting from the default branch". The comparison table
  (`$CC/scheduled-tasks.md:23`) states access to local files: **"No (fresh
  clone)"**. It cannot see the working tree, cannot run `mise run`, and cannot
  observe host state. This is verified, not assumed — it was the caller's explicit
  ask.
- **Minimum interval is one hour.** `$CC/routines.md` — "The minimum interval is
  one hour; **expressions that run more frequently are rejected**." A 60 s tick is
  not merely discouraged, it is refused.

Also: runs carry a few-minutes stagger, count against a daily routine run cap, and
the feature is in research preview. `/schedule` is a **skill**, not a CLI verb
(see finding 10), so scripting it means `claude -p "/schedule …"`.

The one genuinely useful piece is the **API trigger**: a per-routine `/fire`
endpoint taking `Authorization: Bearer`, with an optional `text` payload that
arrives wrapped in a `<routine-fire-payload>` block marked untrusted (so the
routine's own prompt must opt into acting on it). That is a real inbound hook from
this Mac *to* the cloud — which is why the complement below is escalation, not
ticking.

### 10. CONFIRMED — Desktop tasks run locally, but cannot hold a 60 s tick

The map recorded Desktop tasks as needing "the app open" and left installation
open. Settled: **the Desktop app is installed and running on this host** —
`/Applications/Claude.app`, bundle `com.anthropic.claudefordesktop`, version
1.25927.0, pid 73345. The docs mean this app: `$CC/desktop-quickstart.md:45`
("Launch Claude from your Applications folder on macOS") and `:53` ("The desktop
app includes Claude Code").

It is also the surface with the best execution locus of the four — a local run with
real file access that *could* run `mise`. It still cannot be the tick:

| Property | Value | Source |
|---|---|---|
| Requires the app open | **Yes** — "Tasks only run while the desktop app is running and your computer is awake" | `$CC/desktop-scheduled-tasks.md:70` |
| Sleep behaviour | Run **skipped**; closing the lid still sleeps | `:70` |
| Stagger | "a small delay of a **few minutes** after the scheduled time" | `:66` |
| Schedule floor in UI | presets are Manual/Hourly/Daily/Weekdays/Weekly; sub-hour needs asking Claude | `:54-62` |
| What a run is | "starts a **fresh session**" — a full model session per fire | `:66` |
| Missed runs | exactly **one** catch-up for the most recent miss, older discarded | `:74` |
| Task storage | `~/.claude/scheduled-tasks/<task-name>/SKILL.md` | `:101` |

The few-minutes deterministic stagger alone is fatal at 60 s. And each fire is a
fresh Claude session, so the token cost objection from finding 1 applies with more
force, not less.

On this host: `~/.claude/scheduled-tasks/` **does not exist** (nor does
`~/.claude/routines/`), so zero Desktop tasks and zero local routine state are
currently defined. Control arm: the same `ls` pattern resolves
`/Applications/Claude.app` and other real paths in the same command.

### 11. SETTLED (was SUSPECT) — the kairos gate is ON; its only consumer is the prompt enqueue

The prior report marked `isKairosCronEnabled` SUSPECT ("not run live; it is a
feature gate"). Settled without needing a risky probe:

- `FX()` = `!tr(process.env.CLAUDE_CODE_DISABLE_CRON) && hEe("tengu_kairos_cron",!0,H$u)`
  — env unset here (`[ -n "$CLAUDE_CODE_DISABLE_CRON" ]` → ABSENT, control `HOME` →
  SET), no `CRON` key in `.claude/settings.json`, and the remote gate defaults
  `true`. **Cron is enabled on this host** — proven behaviourally by finding 5,
  where `CronCreate` actually scheduled a job (`isEnabled(){return FX()}` guards
  all three tools, so a successful call *is* the gate reading true).
- Its consumer is the block in finding 1 and nothing else: `createCronScheduler` is
  constructed only there, and `isKilled:()=>!Wdh.isKairosCronEnabled()` lets a gate
  flip stop a running scheduler mid-session.

So the SUSPECT row resolves to: the gate is on, the scheduler is real and running,
and it still cannot help — because what it does when it fires is enqueue a prompt.

### 12. CONFIRMED — no other scheduling surface exists at this version

Enumerated by shape, not by expected name:

- **CLI flags**: `claude --help | grep -i "cron|sched|loop|routine|timer|interval"`
  → **rc=1, zero matches** (control: `grep -c print` → 11).
- **Hidden subcommands**: probed `schedule`, `cron`, `routines`, `loop`, `timer` —
  all five return **root help**, i.e. not subcommands. Control arms both ways:
  `claude attach --help` returns distinct text ("Open the background session in
  this terminal…"), fresh bogus `claude zzqfresh9931 --help` returns root help. So
  the probe discriminates, and `/schedule` is a skill only.
- **Env tokens**: shape-enumerated all 633 `CLAUDE_*`/`ANTHROPIC_*` tokens (this
  count uses my own regex and is *not* comparable to the ledger's 254/614 figures,
  which used a different method — do not diff them). Nine match schedule terms;
  the only load-bearing ones are `CLAUDE_CODE_DISABLE_CRON` (documented) and the
  two refuted in finding 8. Control: fresh `ZZQ_FRESH_CTRL_5591` → 0,
  `CLAUDE_CODE_TASK_LIST_ID` → 5.
- **Settings schema**: 16 of 1,173 zod-shaped keys match schedule terms, and all
  are internal object fields (`cron`, `crons`, `humanSchedule`, `scheduledFor`,
  `selfWake`, `rewakeMessage`) or the known statusline `refreshInterval`. **No
  user-facing settings key changes durability.**

## Pros and cons vs launchd

launchd via mise's `[bootstrap.macos.launchd.agents]`, `start_interval=60`:

| Axis | launchd (incumbent) | Best Claude alternative (Desktop task) |
|---|---|---|
| Executes | the literal command, deterministically | a prompt; the model decides what to run |
| Token cost per tick | **zero** | one full session per fire |
| Timing accuracy at 60 s | `start_interval` honoured | few-minutes stagger; 60 s not offered in UI |
| Survives logout / reboot | **yes**, no app or session | no — needs the app open and the machine awake |
| Survives sleep | fires on wake | run skipped; one catch-up only |
| Observability when it stops | `launchctl list`, exit status, log file | run history in the app; nothing if the app is closed |
| Failure mode | process exits non-zero, launchd retries | silently no runs while the app is shut |

launchd's only real weakness is the inverse: it cannot *reason*. That is exactly
what the complementary roles below are for.

The honest counter-argument, stated rather than argued away: if the
`tengu_kairos_cron_durable` gate flips on, `CronCreate` gains restart survival and
becomes a more interesting *watchdog* than it is today. It still would not become a
tick — findings 1 and 3 are independent of the gate — and it would still need a
live REPL, so launchd would remain the thing that guarantees a REPL exists.

## Recommended shape

1. **Keep launchd as the tick.** Unchanged from the map's ruling, but now on
   re-verified evidence at 2.1.222 rather than the morning's inherited note — and
   with a better reason than "the others are session-only": *the others fire
   prompts, not commands.*
2. **COMPLEMENT — Desktop scheduled task as a low-frequency supervisory lane.**
   A daily or hourly local task ("check the pull-loop's own health: is the launchd
   agent loaded, is the queue advancing, did any worker wedge?") buys a *reasoning*
   pass that launchd cannot do, with real file access and a visible run history.
   Precise role: **repair and report, never tick.** It must never be on the
   critical path, because it stops silently whenever the app is closed.
3. **COMPLEMENT — a cloud routine as off-machine escalation.** It runs when the Mac
   is off and can reach GitHub Issues through connectors, so it can notice "the
   queue has been stalled for 6 h" and open an issue or PR. Its `/fire` API
   endpoint also gives the local scheduler an outbound escalation hook. Floor is
   1 h; it cannot see the working tree.
4. **Do not use `CronCreate` or `/loop` for anything the framework depends on.**
   Both are fine for in-session convenience during an interactive debugging
   session. Neither is a scheduling primitive: session-bound, agent-scoped listing,
   classifier review in auto mode, 7-day expiry, up to half-period jitter, and a
   single-writer lock per repo.

If a future session sees `durable: true` start working, re-open only question 2 —
whether a durable cron makes a *better watchdog* than a Desktop task — and leave
the tick decision alone.

## Ledger rows to append

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| **A cron/loop fire ENQUEUES A PROMPT, never a command** — `Yv({mode:"prompt",…,skipSlashCommands:!0,priority:"later"})`; a scheduled tick is a model turn, not an exec | CONFIRMED | binary REPL construction site; `CronCreate`'s own text points at `Monitor` for real execution | 2.1.222 | 2026-08-05 |
| **`CronCreate` has an undocumented `durable` param (0 of 175 pages) that is GATED OFF on this host** — `$Ue()`=`tengu_kairos_cron_durable`, code default `true`, remote gate false here | CONFIRMED | live schema returned the negative branch of all 3 ternaries (`durable`/`CronList`/`CronDelete`); both branches ship in the binary | 2.1.222 | 2026-08-05 |
| **Durable ≠ unattended even when ON** — a task due while the REPL was closed is missed, deleted, and surfaced via `AskUserQuestion` for confirmation; the scheduler lives in the REPL | CONFIRMED | binary `buildMissedTaskNotification` verbatim | 2.1.222 | 2026-08-05 |
| ⚠️ **`CronCreate`'s jitter prose ("10% of period, max 15 min") is a HARDCODED LITERAL and contradicts the code** — real default `dhe` is `recurringFrac:0.5, recurringCapMs:1800000` (half the period, 30 min cap), matching the docs. Up to 30 s jitter on a 60 s period | CONFIRMED | template source shows `${YPe}` interpolated in adjacent sentences, jitter numbers not | 2.1.222 | 2026-08-05 |
| **The cron scheduler is SINGLE-WRITER per project dir** via `.claude/scheduled_tasks.lock` — a second live session in the same repo silently gets no scheduler (`return !1` + debug log); staleness by `pid`+`procStart`, same pair as roster `adopt()` | CONFIRMED | binary `U$l`; live: probe rewrote the lock (Jul 5 → now) under the parent session id; 0 doc mentions | 2.1.222 | 2026-08-05 |
| **`CronList` is AGENT-SCOPED** — `(t?e.filter((o)=>o.agentId===t.agentId):e)`; a supervisor cannot enumerate a worker's crons. **`CronCreate` needs classifier review in `auto` mode** | CONFIRMED | binary `call()` / `checkPermissions()` | 2.1.222 | 2026-08-05 |
| **A teammate cannot create a durable cron** — hard `validateInput` guard, independent of the gate | CONFIRMED | live: `errorCode:4` "durable crons are not supported for teammates" | 2.1.222 | 2026-08-05 |
| ⚠️ **`CLAUDE_CODE_LOOP_PERSISTENT` does NOT make a loop persistent** — it selects the preamble text and softens the stop condition. `CLAUDE_CODE_LOOP_KEEPALIVE` is an in-session fallback heartbeat with a 2-decline budget. Both 0 of 175 docs; neither confers durability | REFUTED | binary `eTo()`/`Tbs()`/`r$u()`/`o$u()`; control `CLAUDE_CODE_SUBAGENT_MODEL` → 5 pages | 2.1.222 | 2026-08-05 |
| **`/loop` DOES carry over to a background session** (docs confirm), but the supervisor "exits when the last client disconnects" and **service install is disabled in this version** — no logout/reboot survival | CONFIRMED | `$CC/agent-view.md:396`; `claude daemon --help` verbatim (offers `uninstall`, not `install`) | 2.1.222 | 2026-08-05 |
| **Cloud routines cannot reach the local tree** (fresh clone, Anthropic infra) and **reject sub-hour expressions** | CONFIRMED | `$CC/routines.md:13,73` + "minimum interval is one hour; expressions that run more frequently are rejected" | 2.1.222 | 2026-08-05 |
| **Claude Desktop IS installed and running on this host** (`com.anthropic.claudefordesktop` 1.25927.0, pid 73345) — but tasks need the app open + machine awake, add a **few-minutes** stagger, and each fire is a **fresh full session**. `~/.claude/scheduled-tasks/` does not exist ⇒ zero tasks defined | CONFIRMED | `Info.plist` + `pgrep`; `$CC/desktop-scheduled-tasks.md:66,70,74` | 2.1.222 | 2026-08-05 |
| **No scheduling CLI surface exists** — 0 flags in `--help`; `schedule`/`cron`/`routines`/`loop`/`timer` are all NOT subcommands; no settings key confers durability | CONFIRMED | control-armed: `claude attach --help` distinct vs fresh bogus verb → root help; settings scan 16/1173 keys all internal | 2.1.222 | 2026-08-05 |
| `isKairosCronEnabled` gate is **ON** on this host and its sole consumer is the prompt-enqueue callback (settles the prior SUSPECT row) | CONFIRMED | `FX()` env unset + successful live `CronCreate` (all 3 tools guarded by `isEnabled(){return FX()}`) | 2.1.222 | 2026-08-05 |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo the tick must run `mise run <task>` against; `.claude/` inspected for scheduler state
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline `agent-harness-docs` claude-code doc tree (175 pages), the semantics corpus for every doc citation above

_No third-party repo source was read; the binary and the offline docs are both local._
