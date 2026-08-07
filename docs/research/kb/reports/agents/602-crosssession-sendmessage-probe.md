# Cross-session SendMessage reach — can a human answer be delivered to a blocked `--bg` node? (2026-08-07, v2.1.224)

**Question.** Can a human's answer be delivered, via 2.1.224's cross-session
`SendMessage` (or `ListAgents` + `SendMessage`), to a background `--bg` node that is
in `state="blocked"` with a non-empty `needs` payload and NO `queuedPrompt`?

Split into two sub-cases, answered separately:

- **(a) LIVE blocked node** — process alive, `state=blocked`, `needs` set.
- **(b) DEAD blocked node** — process exited, `state.json` still reads `blocked` with a
  `needs`. The real case on this host (`ad8baf35`, `fdfdaf90`).

**Corpora, in precedence order:** the 2.1.224 binary
(`~/.local/share/claude/versions/2.1.224`, 277,495,040 B) > `claude --help` /
`claude <verb> --help` > the offline doc tree
(`$CC = ~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`).
The 2.1.223 bundle (272,553,824 B) is a **built-in control arm** — diffing the two
separates "2.1.224 added this" from "this was always there".

**Hard constraint honoured:** `~/.claude/jobs/**` is READ-ONLY for this run. No probe
below writes to a job dir. Where a write would have been required, the probe is
described, not run.

**Method note.** BSD `grep` is blind on this binary; every count below comes from a
python byte-search (`re.finditer` over `open(path,'rb').read()`), counting
**occurrences**, not lines.

---

## Verdict table

_(filled in as findings land — see sections below)_

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | CONFIRMED | The local cross-session transport is a **unix domain socket**, and a peer is listed only if a live `net.connect()` to it succeeds within 250 ms | binary `rfa()`/`p1p()` @255813842; control `qzrmvblunk7742xy` → 0/0 vs `SendMessage` → 85/89 |
| 2 | CONFIRMED | The peer registry is **`~/.claude/sessions/<pid>.json`**, a corpus entirely disjoint from `~/.claude/jobs/<id>/state.json` | binary `tfa()` @255814178; live: 2 registry entries, both for running pids; **0** entries for `ad8baf35`/`fdfdaf90` |
| 3 | CONFIRMED | A dead peer's registry entry is **actively unlinked** during enumeration when the socket fails AND `process.kill(pid,0)` fails | binary `rfa()`: `nIr.unlink(s)`; `zC()` @246486880 |
| 4 | CONFIRMED | **`bg` is a first-class peer kind** — a LIVE `--bg` node is enumerable and addressable | binary `a1b=["interactive","bg","daemon","daemon-worker"]` @255816856 |
| 5 | CONFIRMED | **The peer backend NEVER writes `queuedPrompt`** — all three of its outcomes return before the only two writers | binary `WUn` @261567100, `ddm`/`GUn` @261587013 |
| 6 | CONFIRMED | The only route carrying human text to a not-running job is a **respawn `initialPrompt`**, owned by FleetView's TUI | binary @265824651, resume resolution @261590516 |
| 7 | **REFUTED** | "2.1.224 created a new delivery route" — the entire reply/queue/respawn machinery is **byte-identical** in 223 and 224 | 10 tokens all flat; control `crossSessionInbound` 0→18, `peer_inbound_gate` 0→9 in the same probe shape |
| 8 | CONFIRMED | Live: the two blocked jobs carry `state` and **no `pid`**; the two live peers carry `pid`/`status` and **no `state`** | `claude agents --json` rc=0 — one command, both arms |
| 9 | CONFIRMED | A non-interactive node's inbound gate **fail-closes to `hold`**, and hold needs a React dialog it cannot render | binary `lya()`/`cya()` @256689279; headless hold-receipt is log-only @266713516 |
| 10 | CONFIRMED | **No `claude` job verb accepts text** — `respawn`/`attach`/`logs`/`stop`/`rm` take an id only | `claude <verb> --help`, rc=0 each |
| 11 | **NEEDS-PROBE** | `claude attach` refuses a `blocked` job ("back to the list") | binary `pdm` only — not run, would write to a job dir |

---

## Findings

### 1. The transport is a live socket, not a file drop

`listAllPeers` (`ofa`, @255816856) builds the addressable set from four transports —
`uds` (local machine), `cloud`, `bridge` (Remote Control), and `did` (hard-wired to
empty in this build: `o=Promise.resolve({peers:[],warnings:[]})`). Local peers are
`uds` only:

```js
let c = i.map((d) => ({transport:"uds", address:`uds:${d.sock}`, session:d}));
```

The `uds` set comes from `rfa()` @255816040, which is the whole answer:

```js
function rfa(){
  let e=WXo(),
      t=(await tfa()).filter((i)=>i.sock&&i.sock!==e),
      r=await Promise.all(t.map((i)=>p1p(i.sock))),   // live socket probe
      n=Wt()!=="wsl", o=[];
  for(let i=0;i<t.length;i++){
    let{file:s,...a}=t[i];
    if(r[i]) o.push(a);                               // answered -> listed
    else if(n&&!zC(a.pid)) nIr.unlink(s).catch(()=>{}) // dead -> DELETE the entry
  }
  return o
}
```

`p1p` @255813842 is a real connect, not a stat:

```js
function p1p(e){return new Promise((t)=>{
  if(!Z_e(e)){t(!1);return}
  let r=Qpa.connect({path:e}),          // Qpa = require("net")
      n=(o)=>{r.destroy(),t(o)};
  r.on("connect",()=>n(!0));
  r.on("error",(o)=>n(zt(o)==="EBUSY"));
  r.setTimeout(250,()=>n(!1))
})}
```

**A listening process is a precondition for addressability.** There is no filesystem
drop-box fallback: if the socket does not answer inside 250 ms, the peer is not in the
returned set, and therefore cannot be named by `SendMessage`.

### 2. The peer registry is `~/.claude/sessions/<pid>.json` — not the job dir

`tfa()` @255814178 reads `path.join(configDir, "sessions")` and accepts only filenames
matching `/^\d+\.json$/` — **the registry is keyed by PID**. Each entry yields
`messagingSocketPath`, `cwd`, `startedAt`, `procStart`, `name`, `kind`, `sessionId`,
`jobId`, `parkedJobId`, `bridgeSessionId`, `logPath`, `status`, `waitingFor`.

Live on this host (read-only), the registry holds exactly two entries, both running:

```
/Users/rmanaloto/.claude/sessions/1473.json
  sessionId: '732297c5-087e-4e0d-b100-9ace9ce64873'  kind: 'interactive'  status: 'shell'
  cwd: '/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base'  name: 'knowledge-base-77'
/Users/rmanaloto/.claude/sessions/14968.json
  sessionId: '96dd0e23-6066-4c5e-aa6c-b38c2111e39b'  kind: 'interactive'  status: 'busy'
  cwd: '/Users/rmanaloto/dev/github/ray-manaloto/dotfiles'  name: 'dotfiles-5e'
```

Both carry `messagingSocketPath`. **Neither `ad8baf35` nor `fdfdaf90` has a registry
entry** — those job dirs (`state.json` mtimes 2026-07-13 and 2026-07-22) are in
`~/.claude/jobs/`, a directory `tfa()` never reads.

The entry carries a `jobId` field, so a *live* bg node's peer entry points **at** its
job. There is no reverse pointer: nothing maps a job dir back to an addressable peer.

### 3. Dead entries are garbage-collected, not merely skipped

The `else if(n&&!zC(a.pid)) nIr.unlink(s)` branch means the first `ListAgents` after a
node dies **deletes** its registry file. `zC` @246486880 is `process.kill(pid,0)`.
So a dead node is not "listed but unreachable" — it is erased from the only namespace
`SendMessage` resolves against.

### 4. `bg` is a first-class peer kind

`a1b=["interactive","bg","daemon","daemon-worker"]` @255816856 is the accepted-kind
list, and `c1b=["busy","shell","idle","waiting"]` the status list. A `--bg` node is
therefore a legitimate peer *while it is running* — case (a) is not excluded by kind.

Note what is **absent** from the peer status list: `blocked`. Peer status is
`busy|shell|idle|waiting`; `blocked` is a *job* state living in `state.json`. The two
vocabularies do not overlap, which is the first hint that the peer channel and the job
escalation ledger are separate systems.

### 5. The peer backend NEVER writes `queuedPrompt` — decisive for the seam question

`WUn(e,t,r,n,o)` @261567100 is the bg reply dispatch. Its first branch is the peer
transport, and it returns in all three outcomes without touching disk:

```js
if(r?.backend==="peer"){
  if(!r.sock) return Se("job_reply"), s("ok"), {err:Sil};          // no socket
  try{ return await Zpa(r.sock,t), Se("job_reply"), s("ok"), null } // delivered
  catch(h){ return me("job_reply","job_reply_peer_send_failed"),
            s("bad","job_reply_peer_send_failed"),
            {err:`Couldn't send to that session — ${ue(h)}`} } // failed
}
```

There is no `ddm()` / `GUn()` call on this path. **`ddm` → `GUn` is the only function
that sets `queuedPrompt`**, and it is reachable only from the *daemon* backend's
failure branches further down the same function:

```js
async function GUn(e,t,r){ return Sh(e,{...t, queuedPrompt:r,
  updatedAt:new Date().toISOString()}).then(()=>!0,(n)=>(z_(n),!1)) }   // @261587013
async function ddm(e,t){ if(U1(t)!=="prompt")return!1; SE(e);
  let r=await xl(e); if(!r)return!1;
  if(r.queuedPrompt!==void 0) return r.queuedPrompt===t;               // won't overwrite
  return GUn(e,r,t) }                                                  // @261567100
```

And the daemon branch only queues when the **daemon** is unreachable
(`ENOCONN`/`ETIMEOUT`) or the send fails unclassified. When the daemon is up and
answers `ENOJOB` — the job is known not-running — it returns
`{err:uxt, code:"ENOJOB"}` with **no queue**. So `queuedPrompt` encodes "we could not
determine the node's fate", not "the node is dead and here is its mail".

### 6. The one path that does reach a not-running job is a RESPAWN, and it is FleetView's

The second `queuedPrompt` writer is FleetView's peek-reply @265824651. Read in order,
it does three things after `WUn` returns:

```js
let Kf = await WUn(et.id, Br, et.state, void 0, nl); Jo = Kf?.err ?? null; Pi = Kf?.code;
if(Jo===uxt && U1(Br)==="prompt"){                                  // uxt = "not running"
  let $a = await i8n(et.id,{knownState:et.state, initialPrompt:Br}); // RESPAWN with the text
  os=!$a.ok; ra=!$a.ok&&$a.queued===!0;
  Jo=$a.ok?null:ra?"Reply queued — will be sent when this session restarts":$a.error;
}
...
if(!Pi && Kf!==void 0 && _vv.has(Kf) && U1(Br)==="prompt")
  Rp = await Sh(qc(et.id), {...et.state, queuedPrompt:Br, updatedAt:...});
```

with `_vv=new Set(["EPIPE","ECONNRESET","ECONNREFUSED","ENOTCONN"])` @265850919.

So the human's text reaches a not-running node **as a respawn `initialPrompt`**, not as
a message. That matches the resume-prompt resolution already in the ledger:
`M = t?.initialPrompt ?? c.queuedPrompt ?? (…) n.intent` @261590516.

**This is a job-verb/FleetView route, not a cross-session `SendMessage` route.**

### 7. ⚠️ None of §5–§6 is new in 2.1.224 — the version diff is flat

This is the finding that decides the scope question, so it gets its own control arm.
Same probe shape, same two files, run in one invocation:

```
'Reply queued':                           223=2   224=2
'will be sent when this session restarts': 223=2   224=2
'queue-to-disk write failed':             223=2   224=2
'fleet_view_reply':                       223=10  224=10
'queued_for_later':                       223=5   224=5
'not_running_no_respawn':                 223=2   224=2
'job_reply_peer_send_failed':             223=3   224=3
'backend==="peer"':                       223=3   224=3
'peek-reply send failed':                 223=2   224=2
'queuedPrompt':                           223=14  224=14
```

**Control arm, same command, same corpus:** `crossSessionInbound` 223=0 → 224=18,
`peer_inbound_gate` 0 → 9, `dialogExpiry` 0 → 4, `peer-send-message` 0 → 10. The probe
plainly can produce a non-zero delta; it produces none here.

And the live-socket constraint itself predates 224. 2.1.223 @252054500 carries
`qAb()`, logically identical to 224's `rfa()`:

```js
async function qAb(){let e=fca(),t=(await pca()).filter((i)=>i.sock&&i.sock!==e),
  r=await Promise.all(t.map((i)=>PMp(i.sock))),n=$t()!=="wsl",o=[];
  for(let i=0;i<t.length;i++){let{file:s,...a}=t[i];
    if(r[i])o.push(a); else if(n&&!AC(a.pid))bRr.unlink(s).catch(()=>{})}
  return o}
```

**What 2.1.224 actually added is a receive-side GATE, not new reach.**
`crossSessionInbound` is `["accept","hold","refuse"]` with this `.describe()`
@245372933:

> "Inbound cross-session peer messages (SendMessage from your other sessions):
> 'accept' delivers them, 'hold' parks them for your review without letting Claude act,
> 'refuse' opts this session out. An explicit value always wins. Unset (mode parity): a
> message auto-delivers only when the sending session's permission-mode class matches
> yours (bypass↔bypass or prompting↔prompting); a mismatched sender's message is held
> for your approval…"

2.1.224 made cross-session messaging **more reviewed**, not further-reaching.

### 8. LIVE ARM — one command separates the two namespaces on this host

`claude agents --json` (read-only, rc=0, empty stderr) returns **4 rows in two
disjoint shapes**:

```
{"id":"ad8baf35","cwd":".../dotfiles","kind":"background","startedAt":1783962604973,
 "sessionId":"ad8baf35-00fe-4223-80d1-9b0d94d9c338","state":"blocked"}   name:'zstd-compression-level-tuning'
{"id":"fdfdaf90","cwd":".../dotfiles","kind":"background","startedAt":1784744247227,
 "sessionId":"fdfdaf90-801e-4c7d-afe9-e00b780cc5bd","state":"blocked"}   name:'Resume KB concurrency queuing design…'
{"pid":1473, "cwd":".../knowledge-base","kind":"interactive","status":"waiting","waitingFor":"input needed"}  name:'knowledge-base-77'
{"pid":14968,"cwd":".../dotfiles",       "kind":"interactive","status":"busy"}                                name:'dotfiles-5e'
```

| | job rows (`ad8baf35`, `fdfdaf90`) | peer rows (`knowledge-base-77`, `dotfiles-5e`) |
|---|---|---|
| `id` | present | **absent** |
| `pid` | **absent** | present |
| `state` | `"blocked"` | **absent** |
| `status` | **absent** | `waiting` / `busy` |

**The two blocked nodes have no `pid`.** They are ledger entries, not processes. The
live sessions have no `state` — they are processes, not ledger entries. This is the
binary's `tfa()`-vs-jobs split, visible in one command.

`knowledge-base-77` is the instructive row: a **live** session that is
`status:"waiting", waitingFor:"input needed"` — the live analogue of "blocked" — and it
*is* addressable, because it has a pid and a socket.

The two target `state.json` files (read-only) are exactly the shape #602 cares about:

```
ad8baf35: state="blocked" tempo="blocked" backend="daemon"
          needs="run `/clear` to proceed to next task"          queuedPrompt PRESENT: False
fdfdaf90: state="blocked" tempo="blocked" backend="daemon"
          needs="do /clear with resume, or run full command-catalog extraction first?"
                                                                queuedPrompt PRESENT: False
```

`backend:"daemon"`, **not `"peer"`** — so `WUn` would not even enter the peer branch for
these. And `~/.claude/daemon/roster.json` reads `workers: []` (updated 2026-08-05):
no live worker exists for either.

### 9. Case (a): a live bg node is addressable, but the inbound gate defaults to HOLD

Delivery to a live peer is real. The `SendMessage` schema states it directly:

> "A listed peer is alive and will process your message — no 'busy' state; messages
> enqueue and drain at the receiver's next tool round. Your message arrives wrapped as
> `<cross-session-message from="...">`."

But whether Claude *acts* on it is decided by `lya()` @256689279:

```js
function lya(){
  let e=TPr(); if(e!==void 0) return {policy:e, holdCause:"explicit-setting"};
  let t=dya(); if(t===null) return {policy:"hold", holdCause:"mode-unknown"};
  if(!iya.has(t.mode)) return E(`[cross-session-inbound] unrecognized permission mode …`),
                              {policy:"hold", holdCause:"mode-unknown"};
  return {policy: cya(t)?"hold":"accept", holdCause:"bypass-default"};
}
function cya(e){return e.mode==="bypassPermissions"
                    || e.mode==="plan"&&e.isBypassPermissionsModeAvailable}  // @256690509
```

Every branch that is not "prompting mode" lands on **hold**, and hold is a dead end for
a non-interactive node:

- The hold buffer is an **in-memory array** — `q0e.push(e)` / `q0e.shift()` @256691439
  — so it does not survive the process, and is capped (`q0e.length>=hqb` evicts oldest
  as `expired`).
- Approval is a **React dialog** — `[{value:"approve",label:"Deliver this message to
  Claude"},{value:"deny",label:"Deny — drop it and tell the sender it was declined"}]`
  @263382544 — which a `--bg` node has no surface to render or answer.
- In headless the held message is merely **logged**: `E("[headless] cross-session
  hold-receipt: status=${Ln} from=${…}")` @266713516.

Neither this repo's `.claude/settings.json` nor `~/.claude/settings.json` sets
`crossSessionInbound` (both `<UNSET>`), so mode parity applies rather than an explicit
`accept`.

### 10. No non-interactive verb carries text to a job

`claude <verb> --help` (rc=0 each, read-only):

```
claude respawn <id>|--all   Restart a background session … so it picks up the current Claude binary.
claude attach  <id>         Open the background session in this terminal.
claude logs    <id>         Print the background session's recent terminal output.
claude stop    <id>         Stop a background session.
claude rm      <id>         Delete a background session and its worktree.
```

**None accepts a prompt or message argument.** The only code path that hands a human's
text to a not-running job is FleetView's `i8n(et.id,{knownState, initialPrompt:Br})`
(§6) — an interactive TUI action.

And the binary refuses to attach a blocked job at all (`pdm` @261567100):

```js
if(r.state==="done"||r.state==="stopped"||r.state==="blocked")
  return Se("job_attach"), ufe(t,"detached"), {kind:"error",ended:!0,
    msg: … r.state==="blocked" ? "That session is blocked — back to the list" : …};
```

⚠️ **Not probe-exercised.** Running `claude attach ad8baf35` could write to the job dir,
which this run is forbidden to do, so this is binary-only evidence. The probe that
would settle it: `claude attach <id>` on a scratch blocked job (never on these two),
expecting the literal `That session is blocked — back to the list`.

---

## Answers

### (a) LIVE blocked node — **reachable, but the answer will not be acted on by default**

`ListAgents` **can** enumerate it (`bg` is an accepted peer kind, §4) and `SendMessage`
**can** address and deliver to it, provided its socket answers within 250 ms (§1).

But a `--bg` node runs non-interactively, so `lya()` resolves to **hold** unless it is
in a prompting permission mode or `crossSessionInbound:"accept"` is set explicitly
(§9). Held means: parked in an in-memory buffer, awaiting a React approval dialog the
node cannot render, logged as a `hold-receipt` and never actioned. Setting
`crossSessionInbound:"accept"` in settings is the documented escape.

**Confidence:** delivery mechanism and gate logic are CONFIRMED from the binary plus
the tool's own loaded schema. **NOT probe-exercised end-to-end** — I did not spawn a
`--bg` node and message it, per the "no long-lived background agents" constraint. A
real send could still fail for a reason not visible in the code read.

### (b) DEAD blocked node — **NO. Nothing cross-session can deliver to it.**

Unambiguous, three independent routes:

1. **It is not in the namespace.** `SendMessage` resolves names against `listAllPeers`,
   which is built from `~/.claude/sessions/<pid>.json` filtered by a **live socket
   connect** (§1, §2). `ad8baf35` and `fdfdaf90` have no entry there — live-verified,
   §8.
2. **Its entry would be deleted, not queued.** `rfa()` unlinks a registry file whose
   socket is dead and whose pid is gone (§3).
3. **The peer transport has no disk fallback.** `WUn`'s peer branch returns on all three
   outcomes without ever calling `ddm`/`GUn`, the only `queuedPrompt` writers (§5).

**Control arm for this negative:** the identical probe shape *does* return "reachable"
for the two live sessions in the same `claude agents --json` output (§8), and the same
byte-scan *does* find deltas where 2.1.224 changed things (§7). The probe can produce
both answers; for case (b) it produces "absent".

### Does 2.1.224 create a route that did not exist when R1 was written?

**No.** The `queuedPrompt`/reply/respawn machinery is byte-identical across 2.1.223 and
2.1.224 (§7, ten tokens, all flat), and the live-socket-only peer enumeration already
existed in 223 as `qAb()`. 2.1.224 added an inbound **gate** (`crossSessionInbound`,
`peer_inbound_gate`, `dialogExpiry`), which is a restriction.

### Can an inbound cross-session message set `queuedPrompt`?

**No — not from the peer path.** `queuedPrompt` has exactly two writers: `ddm`→`GUn`
(daemon-backend failure, and only when the *daemon* is unreachable, never on a
known-`ENOJOB`), and FleetView's peek-reply on an `_vv` errno. The peer branch of `WUn`
reaches neither. The existing `dag_tick.py` seam is therefore **not** something
2.1.224 lets a cross-session message drive.

---

## What this means for #602

The default stays **OUT of scope**, and the evidence strengthens rather than weakens
`docs/receipts/575.md` R1:

- Case (b) — the case #602 exists for — has **no delivery route at all**, at any
  version. The two real payloads on this host are unreachable by construction.
- The only mechanism that gets human text into a not-running job is a **respawn with
  `initialPrompt`**, which is a *scheduler* action (it restarts the node), not a
  message. That is squarely on the scheduler's side of R1's boundary, so honouring it
  would not make the boundary decorative — it would confirm it.
- Case (a) is real but narrow, and would additionally require setting
  `crossSessionInbound:"accept"`. Building the answer path on it would serve only live
  nodes, which are not the ones that accumulate `needs`.

**Blunt caveat:** everything about case (a)'s end-to-end behaviour is code-read, not
probe. If #602 ever wants the live-node path, that probe must be run for real.

---

## What I could not establish

- **No end-to-end live send.** I did not spawn a `--bg` node, block it, and message it.
  The "no long-lived background agents" constraint plus the mutation ban made the clean
  version of that probe unavailable within this run.
- **`ListAgents` from a subagent.** I could not run the live `ListAgents` arm: the tool
  is absent from a subagent's surface. Control-armed — `ToolSearch("select:ListAgents,
  SendMessage")` returned **only** `SendMessage`, and `ToolSearch("select:ListAgents")`
  returned "No matching deferred tools found". Matches the existing ledger row.
- **`claude attach` on a blocked job** — binary-only (§10), deliberately not run.
- **Whether a `--bg` node's socket survives entering `state=blocked`.** The registry
  status vocabulary has no `blocked` value, so a blocked-but-alive node presumably
  reports `idle`/`waiting`; I did not confirm this against a running instance.

## Method notes

- Control term used for the absence arm: a freshly invented token returning **0/0** in
  both bundles while `SendMessage` returned 85/89. **That token is now burned by
  appearing in this file** — invent a new one next run.
- All counts are **occurrences** from a python byte-scan (`re.finditer` over the raw
  bytes), not `grep` lines; BSD `grep` is blind on these bundles.
- Scanner: `bscan.py` in the session scratchpad (not tracked).
- `graphify` was not used: its graph covers this repo's source, and every corpus here
  is the CLI bundle, `~/.claude`, or `--help` output — none of which it indexes.

---

# Round 2 — CORRECTION: my claim #1 was bounded to one transport

The parent reported that both dead nodes **DO** appear in a real `ListAgents` call at
2.1.224, as `Remote Control · idle`, among 34 such rows. That is correct, and it
falsifies the *reasoning* I gave for case (b).

## ⚠️ What I got wrong, stated plainly

§(b) claim 1 read: *"It is not in the namespace. `SendMessage` resolves names against
`listAllPeers`, which is built from `~/.claude/sessions/<pid>.json` filtered by a live
socket connect."*

`listAllPeers` has **four** transports — `uds`, `cloud`, `bridge`, `did` — and I
verified only `uds`. I then stated the conclusion about `listAllPeers` as a whole.
**That is the founding incident's exact shape: a probe correct inside its bound,
reported about the world.** The bound was "the local socket registry"; the answer was
given about "everything `SendMessage` can resolve".

The verdict on case (b) survives — **but on different evidence, and claim 1 as written
must be replaced.** Corrected rows are in the table below.

## Finding 12 — bridge rows come from a REMOTE server, and are de-duplicated *against* live local peers

`UXo()` @255810288 fetches bridge rows via `listBridgePeerSessions`, which is an
**authenticated cloud API call** (`t1b` @255805456: `prepareApiRequest`,
`getOAuthHeaders`, `accessToken`, `orgUUID`), paged and fallible:

```
E(`[bridge:population] fetched ${s.length} rows in ${Date.now()-n}ms${i.failed?" (FAILED — not recordable)":""}${i.truncated?" (truncated at page budget)":""}`)
```

So bridge rows are **not read from local disk at all**. They are the server's record of
sessions on this account. Both target nodes registered one while alive — read-only from
their `state.json`:

```
ad8baf35: bridgeSessionId "cse_01GUpexKZFUw8TRpDGyDYNo3"  bridgeOutboundOnly false  bridgeSessionSeq 2804
fdfdaf90: bridgeSessionId "cse_0169UxhfT3XUpG9ATWWgwk1K"  bridgeOutboundOnly false
```

Then `jXo` @255811685 is the join, and it is the whole explanation:

```js
function jXo(e,t,r){                       // e = bridge rows, t = live uds peers, r = cloud sessions
  let n=new Set(t.map((i)=>i.bridgeSessionId).filter((i)=>!!i)),
      o=new Set(r.filter((i)=>!zAn(t,i.id)).map((i)=>lz(i.id)));
  return e.filter((i)=>!n.has(i.id) && !o.has(lz(i.id)))
}
```

A bridge row is kept **only if no live local peer claims its `bridgeSessionId`**. The
bridge listing is therefore, by construction, *the set of sessions that are NOT locally
live* — which is precisely why two long-dead nodes appear there and my live sessions do
not. Their presence is not evidence of reachability; it is a **consequence of being
dead**.

(`RWt()` @255811685 is `async function RWt(){return{sessions:[],unavailable:void 0}}` —
the `cloud` transport is hard-wired empty in this build, as is `did`. Only `uds` and
`bridge` are real.)

## Finding 13 — reply-only is ENFORCED IN CODE, not prose. Answers the parent's Q1

This is the parent's first question, and the answer is unambiguous: **code**.

Inside the `SendMessage` tool's own `call` @256735394, a name that matches a bridge row
resolves to kind **`not-found`** — bridge rows are never a deliverable target — and
`bridgeReplyOnly` only customises the refusal text:

```js
if(p.kind==="not-found"){
  if(p.bridgeReplyOnly){
    let A=f?`check the spelling against ${cy}`:"check the spelling";
    return {data:{success:!1, message:`'${e.to}' matches a ${WLe} session on this account,
      and those are reply-only from here: messageable ${_Bt}. The Claude Code Remote
      send_message connector is not a workaround either — it cannot reach these
      device-gated sessions, and its "untrusted device" error is misleading (this device
      is not the problem). If that session is who you meant, it isn't reachable by name
      from this machine; if you meant a different agent, ${A}.`}}
  }
}
```

with `WLe="Remote Control"` and `_Bt="only in reply, after it messages you first"`.
`Oqp(e,t)` @256685964 sets the flag by matching the requested name against bridge row
**titles**; `Z_a` @256685964 returns `{kind:"not-found", …}`. The file-send path refuses
in parallel: `{kind:"refused", message:…}` @256753722.

**`success: false`.** The send does not happen, and the caller is told so.

⚠️ **Do not mistake `isBridgeDispatchable` for a peer predicate.** It has 2 occurrences
in both 223 and 224, and it lives in the **slash-command** module @255903477 alongside
`isAdvertisedSlashCommand` / `getCommands`. It governs commands, not messaging.

## Finding 14 — `idle` vs `blocked`: two probes of DIFFERENT facts, neither broken

The parent invoked `probes-need-a-control-arm.md` rule 7 correctly, and the resolution
is the third option: they are not measuring the same fact.

| | bridge row `idle` | `state.json` `blocked` |
|---|---|---|
| Source | Anthropic's server, over an authenticated fetch (§12) | local disk, `~/.claude/jobs/<id>/state.json` |
| Written by | the bridge session record | the local job supervisor |
| Means | the server's session record has no active turn | the local job ledger's last escalation before the process died |
| Knows about local process liveness? | **No** | no — it is a last-write, not a heartbeat |

The bridge server was never told about `state:"blocked"`; that vocabulary is local-only
(and recall from §4 that the peer status vocabulary — `busy|shell|idle|waiting` — has no
`blocked` member at all). Both nodes carry `firstTerminalAt` (2026-07-13 / 2026-07-22),
so locally they reached a terminal moment; the server simply still holds a stale record.

The harness **expects** this staleness — it ships a classifier for it,
`isLikelyStaleBridgeError` (`r1b` @255807696) and `classifyBridgeSendError` (`n1b`).

### The parent's worry — "may ACCEPT a send and report success" — does NOT happen

This was the right thing to be worried about, and it is settled: delivery does **not**
route on the bridge view. A bridge-matched name resolves to `not-found` and returns
`success:false` (§13). The dangerous outcome — a cheerful success for a node dead since
July — is specifically what the code refuses to produce.

## Corrected verdict rows

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| ~~1~~ | **CORRECTED** | ~~"`SendMessage` resolves names against `listAllPeers`, built from the socket registry"~~ — true of the `uds` transport ONLY; `listAllPeers` also returns `bridge` rows | superseded by rows 12–14 |
| 12 | CONFIRMED | Bridge rows come from an **authenticated remote fetch**, and `jXo` keeps a row only when **no live local peer** claims its `bridgeSessionId` — so the bridge list is enriched with dead sessions **by construction** | binary `UXo` @255810288, `t1b` @255805456, `jXo` @255811685; live: both nodes carry a `cse_…` `bridgeSessionId` |
| 13 | CONFIRMED | **Reply-only is enforced in CODE.** A bridge-matched name resolves to `kind:"not-found"` and `SendMessage` returns **`success:false`** | binary @256735394 (tool `call`), `Oqp`/`Z_a` @256685964, file path @256753722 |
| 14 | CONFIRMED | `idle` and `blocked` are **different facts from different corpora**, not a disagreement; the harness ships a stale-bridge classifier | binary `r1b`/`n1b` @255807696; `firstTerminalAt` set on both nodes |
| 15 | REFUTED | "delivery might route on the bridge view and report success for a dead node" | the refusal returns `success:false`; there is no path from a bridge row to a send |

## Case (b), restated on correct evidence

**Still NO — nothing can deliver to a dead blocked node.** The reasoning changes:

- **Enumerable: YES.** Both nodes appear via the `bridge` transport, sourced from the
  server, *because* they are locally dead (§12).
- **Addressable: NO.** A bridge-matched name is `kind:"not-found"`; `SendMessage`
  returns `success:false` with an explicit "isn't reachable by name from this machine"
  (§13).
- **Enumerable ≠ addressable** — exactly as the parent suspected, and it is enforced,
  not merely documented.

The `--bg`/`background` label is absent from those rows for the same reason: the row is
the *server's* session record, which carries a title, not the local job ledger's `kind`.

## Finding 16 — ⚠️ it is NOT a "name collision"; correct the spec's mechanism

`docs/specs/dag-needs-human-projection.md` §0 currently records the bridge rows as
*"Name collision, not reach."* **The conclusion (not reachable) is right; the stated
mechanism is wrong**, and a wrong mechanism in a tracked spec will mislead whoever reads
it next.

A collision would mean two unrelated sessions that happen to share a title. The evidence
says these are **the same sessions, recorded in a different corpus**:

- Both nodes carry a real bridge registration in their own `state.json` —
  `bridgeSessionId: "cse_01GUpexKZFUw8TRpDGyDYNo3"` and `"cse_0169UxhfT3XUpG9ATWWgwk1K"`,
  with `bridgeOutboundOnly:false`. They registered with the bridge **while alive**.
- `jXo` @255811685 retains a bridge row **only when no live local peer claims its
  `bridgeSessionId`** — so a genuinely-dead node's own row is exactly what survives.

The accurate one-liner is: **"the same session, held in the server-side bridge corpus,
which is enumerable but refuses by-name delivery (`success:false`) — enumerable ≠
addressable."** Not a coincidence of names; a real record of the real node, kept
*because* it is dead.

**Honest bound on this correction:** I did not see the raw bridge row **ids** — the
parent's listing showed titles and labels only. So "same session" is **SUSPECT, one
route**: it rests on both nodes holding a `cse_…` id plus `jXo`'s keep-if-not-live
filter, not on an observed id match. The probe that would settle it: capture
`ListAgents` output that exposes each row's `[ref]`/id and compare against the two
`bridgeSessionId` values above. Either way the *addressability* verdict (§13) is
unaffected — that one is settled from the tool's own `call`.

## Round 2 control arms

- Fresh known-absent term, invented for this round: **0 / 0** in both bundles, while
  `bridgeSessionId` returned 76 / 79 and `Remote Control` 211 / 218 in the same
  invocation — the probe discriminates. (That term is now burned by being run in this
  session; invent another next round.)
- Version arm: `reply-only` 223=**1** → 224=**11**, `only in reply` 0 → 2,
  `recordModelViewOfBridgePeers` 0 → 3, while `bridgeOutboundOnly` stayed 9/9 and
  `isBridgeDispatchable` 2/2. So 2.1.224 substantially **expanded the reply-only
  refusal surface** — again a restriction, consistent with §7.
- I did **not** send to either node, per instruction. No job dir was written: mtimes
  remain `Jul 13 20:29` and `Jul 22 13:23`.

## Round 2 — what remains unestablished

- **I did not spawn a throwaway node.** Case (a) is still code-read only; the parent
  offered a throwaway-node arm and I did not take it, because the two questions asked
  in round 2 were both settleable from the binary and the offered arm would not have
  exercised the *bridge* path anyway (a fresh local node is a `uds` peer).
- **Whether a live bridge session can be reached "in reply"** — the code refuses
  by-name sends, but I did not verify the reply path itself, which requires an inbound
  message first.
- **What the bridge row's `idle` would show for a node that is alive but blocked** —
  unprobed; §14 establishes only that the server is not told about `blocked`.

## GitHub repos touched

_None._ Every corpus consulted was local: the installed Claude Code bundles at
`~/.local/share/claude/versions/{2.1.223,2.1.224}`, runtime state under `~/.claude/`,
and `claude --help` output. No repository source or documentation site was read.
Note that the `bridge` transport's rows originate from an Anthropic API endpoint, but I
read the calling code, not the endpoint.

