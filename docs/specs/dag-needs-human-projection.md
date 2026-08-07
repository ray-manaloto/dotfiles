# Spec — projecting NEEDS_HUMAN to the tracker (#602)

**Status:** scoping complete, build not started. This document settles the four
decisions #602 leaves open and specifies the build; it authorises no code.

**Ticket:** [#602](https://github.com/ray-manaloto/dotfiles/issues/602) —
"Project NEEDS_HUMAN to the tracker: the `dag:needs-human` label and the
escalation comment".

**Why a spec and not a plan file.** `.agent/plans/` is gitignored and
this-clone-only, and **#602 exists precisely because a deferral lived only in a
code comment**. A decision that must outlive this clone is tracked or it is not a
decision.

---

## 0. What was measured before designing

Every design fact below was probed on this host on **2026-08-07**, not inherited
from the ticket. Where a probe returned a negative, its control arm is named —
per `.claude/rules/probes-need-a-control-arm.md`, an unarmed negative is not
evidence.

| # | Claim | Probe | Control arm |
|---|---|---|---|
| M1 | **No scheduler module exists.** #602 is greenfield, not an extension. | `ls python/src/dotfiles_setup/ \| grep -iE 'sched\|relaunch\|tracker\|project'` → rc=1 | 47 modules listed by the same `ls`, so the listing is not empty |
| M2 | **Nothing in the package writes to the GitHub tracker.** The write side is greenfield too. | `grep -rn 'gh issue\|--add-label\|issues/comments' python/src/dotfiles_setup/*.py` → 3 hits, **all prose inside docstrings** (`heredoc.py:12`, `workflow_hooks.py:466,779`), zero call sites | the grep does return hits, so it is not blind |
| M3 | **No node→issue binding exists anywhere.** | union of `state.json` keys across all **8** job dirs contains no `issue`/`ticket`/`taskId` field; a job dir holds only `state.json`, `timeline.jsonl`, `tmp/`; no binding symbol in `dag_tick.py`/`codex_lane.py`/`codex_verdict.py` | known-present `NEEDS_HUMAN_LABEL` → 3 files; fresh known-absent term → 0 files. Probe discriminates both ways |
| M4 | **The launchd tick CAN authenticate to the tracker.** | under the exact `environment` PATH from `mise.toml`'s `[bootstrap.macos.launchd.agents.dotfiles-dag-tick]`, `env -i PATH=… HOME=… gh auth status` → **rc=0**, via `~/.config/gh/hosts.yml`, a `gho_` token with `repo` scope; `gh api /repos/ray-manaloto/dotfiles` → **rc=0** | ⚠️ the FIRST run of this probe reported "gh: No such file or directory" — a **null arm**: the PATH passed did not contain `gh`, so it never asked the question. Corrected by first asserting `command -v gh` resolves on that PATH |
| M5 | **Exactly two live escalations exist**, both `blocked ∧ needs ∧ ¬queuedPrompt`, both `tempo=blocked`. | enumerated `~/.claude/jobs/*/state.json` | 8 job dirs read, 6 non-matching — the filter discriminates |
| M6 | **Neither live payload names what was exhausted** ⇒ both fail #575 R5. | read verbatim (§2.2) | — |
| M7 | **2.1.224 added no new delivery route to a blocked node** (§3). | byte-diff of the 2.1.223 and 2.1.224 bundles: every delivery term identical | `crossSessionInbound` 0→18, `peer-send-message` 0→10 on the same command — the probe can produce a delta, and produces none here |
| M8 | **Neither the `dag:needs-human` label nor a standing escalation issue existed** before phase 1. | `gh label list` → no `dag:*` label (only `needs-triage`, `needs-info`); `gh issue list --state open` → no escalation issue | 23 labels and 137 open issues returned by the same commands, so neither probe is blind |
| M9 | **A real NEEDS_HUMAN node is manufacturable in seconds** — `claude --bg --bare` lands in `blocked` + `needs: "login required — run /login"` (§4 phase 2). | spawned one 2026-08-07; it satisfied `is_needs_human()` on first read | the same `claude agents --json` census showed the two interactive rows as `busy`, not `blocked` — the probe distinguishes the states |
| M10 | **`claude rm` requires a live daemon, and its error text misattributes the cause.** It says *"the background service may be restarting"* when the supervisor has been dead for days. | `roster.json`'s `supervisorPid` 42939 → `ProcessLookupError`; `~/.claude/daemon/dispatch/` empty; three `claude rm` attempts refused. Spawning any `--bg` session revives it (new PID 50245) and `rm` then succeeds rc=0 | the liveness probe reported the shell's own PID as ALIVE, so it discriminates; and after the fix, `rm` removed exactly the two named nodes while an untargeted node stayed present |

⚠️ **TWO wrong claims were made during this pass and corrected by evidence.
Recorded, because both would otherwise read as facts — and the second is the more
instructive.**

**C1 — the null arm (M4).** Covered above: a probe that could not have produced
the other answer, reported as an answer.

**C2 — a claim correct inside its bound, stated about the world.** The scoping
session's `ListAgents` call returned 34 rows, two of them matching the live nodes'
`name` fields. First reading: *"the escalated nodes are enumerable."* The probe's
first round replied that they are **not** in the peer namespace, because
`SendMessage` resolves against the local socket registry, which holds zero entries
for either. Round 2 retracted that: `listAllPeers` has **four** transports and only
`uds` had been checked, so a conclusion about the local registry was stated about
everything `SendMessage` can resolve.

**Both readings were wrong, and the truth is neither.** The nodes ARE those rows —
real records of the real sessions, held in the server-side `bridge` corpus — and
they are enumerable **because** they are dead (§3.2). They are simply not
addressable: a bridge-matched name returns `success: false`. **Enumerable ≠
addressable, and it is enforced in code rather than merely documented.**

The verdict on case (b) never moved; the mechanism under it was wrong twice. That
is the failure mode this file's §0 exists to make expensive — and the only reason
either was caught is that each claim was handed onward with *"verify this"*
attached rather than *"use this"*.

**C3 — an inherited "correction" that was a TIMEZONE, and a name read as an
assertion.** The session handoff flagged *"⚠️ #602's body says '2026-07-14'; the
measured mtime is 2026-07-13 … re-derive, never navigate by them"*, citing
`tests/test_dag_tick.py`'s `_LIVE_NEEDS_JULY_13` as corroboration. Re-derived:
`ad8baf35`'s mtime is **`2026-07-14T01:29:08Z`** in UTC and `2026-07-13T20:29` in
local time (this host is UTC-5), and `state.json`'s own `updatedAt` reads
`2026-07-14T01:29:08.930Z`. **#602's body was right**; `ls` prints local time, and
a date stated without a timezone is not a measurement. The cited corroboration is
worse than neutral: `_LIVE_NEEDS_JULY_13` is a **variable name** whose value is
the payload string — it asserts no date at all. *A name is not an assertion*, and
a rule about not inheriting numbers was itself passed on with an uninherited one.

Operational consequence, in the format: **read `updatedAt`, never a formatted
`ls`**, and always carry the offset.

**M4 is the one that changed the design.** Had the null arm stood, this spec
would have specified a credential-passing mechanism the tick does not need.
Recorded here rather than quietly dropped, because the corrected result reverses
the conclusion.

---

## 1. The gap, restated precisely

`dag_tick.py` classifies an escalated node `NodeClass.NEEDS_HUMAN`
(`state == "blocked"` ∧ non-empty `needs` ∧ no `queuedPrompt`), logs it, and
**never respawns** it. The projection half — the `dag:needs-human` label and the
append-only tracker comment — was deliberately left unowned, because
`docs/receipts/575.md` R1 keeps projection **one-directional and
scheduler-owned**, and a tick that labelled directly would put a second writer on
the tracker.

The boundary is right. Nothing owns the other side. Consequence, live: an
escalated node is visible **in a launchd log only** — `~/Library/Logs/
dotfiles-dag-tick.log` — so the `needs` payload that R1 makes load-bearing
reaches a human only if somebody reads that file.

Three things are already **settled** and are not reopened here:

- **Ownership** — `575.md` R1: the scheduler projects, one direction only.
- **This label's spelling** — `575.md`: *"#573's receipt `dag:needs-human` — the
  receipt is later and governs"*. (#601's close-out claimed the receipt deferred
  the spelling; it does not.)
- **Labels vs comments vs body** — `docs/receipts/573.md` §VERDICT: *"LABELS for
  anything the selector reads; APPEND-ONLY COMMENTS for retry counts, terminal
  reasons and stall timestamps. Never the body."*

---

## 2. The four decisions

### 2.1 Decision A — the OWNER

> **A new `dag_project.py` module, a `mise run dag-project` task, and its own
> LaunchAgent — built as the SCHEDULER'S FIRST SLICE, not as a watchdog feature.**

`575.md` R1 assigns projection to the scheduler. M1 measured that no scheduler
exists, so #602 cannot "extend" one — it must create the first phase of the thing
#573 specified. Shaped so that when #573's pull loop lands, projection is
absorbed as a phase in its fixed order (reconcile → **project** → preflight →
select → dispatch) rather than refactored out of somewhere it should never have
been.

**Rejected: fold projection into `dag_tick.py` behind a flag.** Forbidden three
times over — `575.md` R1, the `NEEDS_HUMAN_LABEL` comment in `dag_tick.py:155-176`
(*"a tick that labelled directly would put a second writer on the tracker"*), and
the `workflow.dag-tick-wiring` contract, which binds the current wording. It would
also make the eventual move to the scheduler a contract edit rather than a
re-wiring.

**Rejected: wait for the full #573 pull loop.** That leaves the two live
escalations invisible for the duration, which is the failure being ended.

Four properties bind the module:

1. **It reuses `dag_tick`'s predicates by import — it never re-derives them.**
   `node_from_state`, `normalize_needs`, `is_needs_human`. This is the #601/#604
   lesson stated as an invariant: two readers of one file that disagree about it
   is the exact defect class both of those tickets shipped fixes for. A private
   copy of `is_needs_human` in `dag_project.py` is a spec violation, not a style
   choice.
2. **One direction, always.** It READS `~/.claude/jobs/**` and WRITES only to
   GitHub. It never writes a job dir, never calls `claude respawn`/`stop`/`rm`,
   and never edits an issue **body**.
3. **Zero escalations ⇒ zero API calls.** It classifies from disk first and
   returns before touching the network if no node is NEEDS_HUMAN. The common case
   is zero, and a projector that makes no call when idle cannot misfire when idle.
4. **Its own lockfile**, `~/.local/state/dotfiles/dag-project.lock`, on the same
   `fcntl` pattern as `dag_tick`'s. A second projector that finds it held exits 0
   silently. Distinct from the tick's lock — the two are separate processes and
   must not serialise against each other.

**Interval: 300s, not 60s.** The watchdog's 60s exists because a crashed process
should be recovered fast. A human's question does not become more answerable at
60s than at 5 minutes, and the tracker is a shared rate-limited resource. Stated
as a decision so a later reader does not "fix" it into alignment with the tick.

### 2.2 Decision B — the BINDING and the projection TARGET

> **The scheduler writes a node→issue binding at dispatch. A BOUND node projects
> to its own issue; an UNBOUND node projects to one designated standing
> escalation issue.**

*(Ray's ruling, 2026-08-07, on the fork M3 uncovered.)*

M3 is the load-bearing measurement: **nothing binds a node to an issue today.**
Both live escalations were hand-launched long before any scheduler, so under a
bound-nodes-only reading #602 would ship having surfaced **0 of its own 2
motivating cases** — a fix that would not have caught its own motivating defect.

**The binding artifact:** `~/.claude/jobs/<node>/dag-binding.json`

```json
{"schema_version": 1, "repo": "ray-manaloto/dotfiles", "issue": 602,
 "bound_at": "2026-08-07T12:00:00Z", "bound_by": "dag-dispatch"}
```

Colocated in the job dir on #580's precedent for `CODEX_LANE_DIRNAME`: *"a
`claude rm` of the node takes its lane with it instead of orphaning a run dir the
reaper would keep finding forever."* The same argument holds exactly — a binding
that outlives its node is a pointer to nothing.

`schema_version` is present from v1 deliberately: `codex_verdict.py`'s docstring
records that OMC's payload lacks one *"which is why a contract change there breaks
silently"*.

**The standing escalation issue is
[#623](https://github.com/ray-manaloto/dotfiles/issues/623)**, created in phase 1.
Its number becomes the module constant `DEFAULT_ESCALATION_ISSUE = 623`, with a
`--escalation-issue` override — a reviewable diff, not silent per-clone drift. The
issue's own body states its contract (append-only, never closed, never
machine-written body) so an operator who finds it without this spec still knows
what it is.

**Rejected: infer the issue from a node's free text.** Measured on the real data,
it fabricates. `ad8baf35` is NAMED `zstd-compression-level-tuning`, its `intent`
reads *"Resume the hk-enforcement task"*, and its `output.result` names **#237,
#238 and #231** — three candidate numbers, none authoritative, and none of them
what the node was actually blocked on. A wrong guess posts a human's unanswered
question onto an unrelated ticket, which is worse than the silence it replaces.

**Closed-target handling** — both arms, because both are reachable:

| Target state | Action | Why |
|---|---|---|
| Standing issue is **closed** | **Reopen it**, then project | A closed standing escalation issue while escalations exist *is* the silence failure. #573: *"only the scheduler transitions state"* — this is the scheduler, so the transition is in-bounds |
| A **bound** node's issue is closed | Project to the **standing issue** instead, with a line naming the closed bound issue | Reopening a work issue is **rework**, whose semantics `575.md` R7 owns (`max_rework` 2, reopen-the-upstream-issue). A projector must not invent them as a side effect of an escalation |

### 2.3 Decision C — the COMMENT FORMAT

> **One append-only comment per (node, question), opening with an invisible HTML
> machine marker and followed by a dual-audience human body.**

Dual-audience follows #573's adopted stokowski precedent (*"append-only
dual-audience comments"*).

**This template is PILOT-VALIDATED**, not proposed — both live escalations were
projected by hand with it on 2026-08-07 and the round-trip was byte-verified
(§4 phase 1). An earlier draft of it was wrong in three ways; see the note below.

````markdown
<!-- dag:needs-human node=ad8baf35 digest=a5f7040626d9 schema=1 -->
### 🙋 NEEDS_HUMAN — node `ad8baf35`

**The question** — `needs`, verbatim from `~/.claude/jobs/ad8baf35/state.json`:

```text
run `/clear` to proceed to next task
```

**Suggested reply** — `suggestedReply`: _absent_

| Field | Value |
|---|---|
| node | `ad8baf35` |
| session | `ad8baf35-00fe-4223-80d1-9b0d94d9c338` |
| state / tempo | `blocked` / `blocked` |
| `queuedPrompt` | absent — a question awaiting an answer, not an answer awaiting delivery |
| `state.json` mtime | 2026-07-14T01:29:08Z (`updatedAt` agrees) |
| written by CLI | 2.1.207 |
| binding | **UNBOUND** — no `dag-binding.json`; projected to the standing escalation issue |
| R5 evidence | ⚠️ **UNVALIDATED** — see below |
| also stalled | no (`tempo` is `blocked`, not `active`) |
| projected by | `dag-project` @ 2026-08-07T14:02:11Z |

**What the watchdog will and will not do** — reproduced verbatim from
`dag_tick._needs_human_reason()`, not paraphrased:

> escalated — state=blocked with a needs payload and no queued reply, so a human
> was asked a question a respawn cannot answer; not respawned BY THIS TICK at any
> age […]

**How to answer:** the job dir still exists, so this is a live question. Reply to
this node in FleetView — that respawns it with your answer as `initialPrompt`,
the only route that reaches a not-running job (§3.3). `claude respawn` alone
returns it **idle with no prompt** and discards the question.
````

⚠️ **Three defects the by-hand pilot caught in the draft above — this is what
phase 1 is FOR.** None would have been visible from reading the format; all three
came from producing one.

1. **A blockquote does not quote verbatim.** The draft used `> run `/clear` …`
   and `ad8baf35`'s payload **contains backticks**, so GitHub renders them as
   inline code and the raw characters never appear. A payload is cargo, not prose:
   it goes in a **fenced `text` block**, always. (This was named as phase 1's
   specific risk and it fired on the first comment.)
2. **The example's own timestamp was wrong, by timezone.** The draft read
   `2026-07-13T20:29:08Z` — that is the **local** time `ls` prints, stamped `Z`.
   The real UTC mtime is `2026-07-14T01:29:08Z`, which is what `state.json`'s own
   `updatedAt` says. **Read `updatedAt`, never a formatted `ls`.**
3. **The example asserted the job dir was gone.** It is not; both job dirs exist,
   so both nodes get the live-answer form. The draft showed both forms
   concatenated, which reads as one contradictory instruction.

The "How to answer" line has **two forms and the projector must pick by testing
`os.path.isdir(job_dir)`**: present → the FleetView instruction; absent → *"this
comment is a record, not a live question"*. Telling an operator to reply to
something that cannot receive a reply is the same class of defect as a log line
naming an action the code does not perform.

**An optional final `⚠️ Context worth having` paragraph is encouraged** and was
used on both pilot comments. A three-week-old escalation often should not be
answered at all — `ad8baf35` is asking permission to `/clear` after work that
merged in July, where `claude rm` is the likelier correct action. Projecting an
escalation is not a recommendation to resume it, and the comment should say so
when that is the case.

Rules that make the format a contract rather than a layout:

- **The `needs` payload is quoted VERBATIM, in a fenced block, and never
  summarised.** It is the entire cargo; a projector that paraphrases it has lost
  the thing it exists to carry. Same for `suggestedReply` when present.
- **The reason string is reproduced verbatim from `_needs_human_reason()`**, not
  restated. That string is pinned by **golden equality** in `tests/test_dag_tick.py`
  precisely because it must claim the re-check without claiming the race is gone;
  a paraphrase in the comment would silently drop the scope qualifiers that two
  rounds of #601 review put there.
- **Never the issue body.** #573 §VERDICT.
- **`schema=1` in the marker**, same reasoning as the binding file.

**Dedupe key: `digest = sha256(needs_normalized).hexdigest()[:12]`.**

The projector lists the target issue's existing comments and skips if a marker
with the same `node=` **and** `digest=` is already present. Keyed on both because
the two failure modes are opposite: keying on `node` alone means a node that
re-escalates with a **new** question is silently never reported again; keying on
`digest` alone collides across nodes asking the same question.

**Why not the label as the dedupe key.** It cannot work for the standing issue:
the label lives on the *issue*, so the first escalation would label it and every
subsequent node's comment would be suppressed. The marker is per-node by
construction.

This is a **read of a snapshot, not a read-back of our own write** — #573's
gotcha (*"never read back your own GitHub write to confirm it"*) is respected.
A double-post from replication lag is possible and benign: the artifact is
append-only and the second copy is identical.

### 2.4 Decision D — R5 is a LABEL, NOT A GATE

> **An escalation that fails #575 R5 is PROJECTED ANYWAY, marked
> `R5: UNVALIDATED` in the comment. It is never dropped.**

*(Ray's ruling, 2026-08-07.)* `575.md` R5 says a blocker is valid only if it names
what was exhausted, and that *"the scheduler rejects an evidence-free escalation
at projection time"*. Read as a gate, that would **drop** both live escalations
(M6) — and **the failure #602 exists to end is silence**, so dropping a malformed
escalation recreates that exact failure at a new layer. `dag_tick`'s own
`REPLY_QUEUED` precedent chose visibility for the same reason: *"Making it VISIBLE
IS the fix."*

Say it explicitly in the artifact rather than letting the comment read as
compliance. The spec's position is that R5 as written is **not implementable as a
gate on harness-native payloads**, and here is why:

**R5 validity is decided STRUCTURALLY, never semantically.** The projector asks
*"does this escalation carry a machine-readable evidence field?"* — not *"does
this prose sound like it names what was exhausted?"*

That is a deliberate refusal to build a semantic classifier, and the reason is on
the record in this repo: the #601 review killed substring-based reason checking
across two rounds, concluding that *"a substring guard cannot judge meaning, so
tightening it is unwinnable"*. Each round's counterexample defeated the previous
guard by adding a clause it did not constrain. A heuristic scanning `needs` for
"tried"/"exhausted"/"fallback" is that same losing shape, one layer up — and its
false negatives would drop a real human question.

Consequence, stated plainly: **every harness-native escalation is `UNVALIDATED`
today**, because `state.json`'s `needs` is a free-form string the harness writes
and there is no evidence field to carry. That is honest, matches M6 exactly, and
leaves a clean seam — when the scheduler dispatches nodes with a brief that
instructs them to write structured evidence, `VALIDATED` becomes reachable
without changing the predicate. Out of scope here.

**R5 status does NOT get its own label.** #573: labels are for *"anything the
selector reads"*. Nothing selects on R5 validity in this slice, so by the
receipt's own rule it belongs in the comment.

### 2.5 Decision E — the ANSWER path stays OUT OF SCOPE

> **Projection is one-directional. Not by policy — by measurement.**

*(Ray's ruling 3: probe first, then decide. The probe ran; full evidence in
`docs/research/kb/reports/agents/602-crosssession-sendmessage-probe.md`.)*

The premise the ruling was hedging against is **refuted**. §3 has the detail; the
decision follows from it and is no longer a boundary argument.

---

## 3. The answer path — what 2.1.224 actually changed

The previous session measured `crossSessionInbound` 0→18, `dialogExpiry` 0→4 and
`ListAgents` 5→10 between the 2.1.223 and 2.1.224 bundles, and inferred that
cross-session `SendMessage` was *"a NEW delivery route for a NEEDS_HUMAN answer,
material to #602 and #590"*. That inference is **wrong**, and the string counts
never supported it — they proved a feature exists, not that it reaches anything.

### 3.1 The version diff is FLAT for every delivery mechanism

Same probe shape, both bundles, one invocation:

| Term | 2.1.223 | 2.1.224 |
|---|---|---|
| `queuedPrompt` | 14 | 14 |
| `Reply queued` | 2 | 2 |
| `will be sent when this session restarts` | 2 | 2 |
| `fleet_view_reply` | 10 | 10 |
| `queued_for_later` | 5 | 5 |
| `not_running_no_respawn` | 2 | 2 |
| `backend==="peer"` | 3 | 3 |

**Control arm, same command, same corpus:** `crossSessionInbound` 0→**18**,
`peer_inbound_gate` 0→**9**, `peer-send-message` 0→**10**. The probe plainly
*can* produce a non-zero delta. It produces none on any delivery path.

**What 2.1.224 actually added is RESTRICTION, on two independent axes.** A
receive-side gate — `crossSessionInbound` is `["accept","hold","refuse"]`,
controlling whether an inbound peer message auto-delivers or is held for review —
and an expanded send-side refusal surface: `reply-only` 1→**11**, `only in reply`
0→**2**, `recordModelViewOfBridgePeers` 0→**3**, while `bridgeOutboundOnly` held
at 9/9 and `isBridgeDispatchable` at 2/2. Both axes narrow what a message can do.
2.1.224 made cross-session messaging **more reviewed, not further-reaching.**

### 3.2 The two sub-cases

**(b) A DEAD blocked node is ENUMERABLE BUT NOT ADDRESSABLE.** This is the case
#602 exists for, and the distinction is the whole of it.

`listAllPeers` has **four** transports. Two are hard-wired empty in this build
(`cloud`, `did`); two are real:

- **`uds`** — the local registry `~/.claude/sessions/<pid>.json`, keyed by PID and
  entirely disjoint from `~/.claude/jobs/<id>/state.json`. Enumeration probes each
  peer's unix socket with a real 250 ms `net.connect()`, and when the socket fails
  *and* `process.kill(pid,0)` fails it **unlinks the registry file**. Verified
  live: zero `uds` entries for either node.
- **`bridge`** — rows fetched from Anthropic's server over an authenticated API
  call, not read from local disk. Both nodes registered while alive
  (`bridgeSessionId: "cse_…"`, `bridgeOutboundOnly: false`), so both still appear
  here. The join keeps a bridge row **only when no live local peer claims its
  `bridgeSessionId`** — so the bridge listing is, by construction, *the set of
  sessions that are not locally live*. **Their presence in it is a consequence of
  being dead, not evidence of reachability.**

**Addressability is refused in CODE, not by convention.** Inside `SendMessage`'s
own `call`, a name matching a bridge row resolves to `kind: "not-found"` and the
tool returns **`success: false`** with an explicit *"isn't reachable by name from
this machine"*; a `bridgeReplyOnly` flag only customises the refusal text. The
file-send path refuses in parallel with `kind: "refused"`. The dangerous
outcome — a cheerful success for a node dead since July — is specifically what the
code declines to produce.

⚠️ **Honest bound.** That these bridge rows are *the same sessions* rather than
similarly-titled ones is **SUSPECT, one route**: it rests on both nodes holding a
`cse_…` id plus the keep-if-not-live filter, not on an observed id match. The
settling probe is to capture `ListAgents` output exposing each row's id and
compare. **The addressability verdict does not depend on it** — that one is read
straight off the tool's own `call`.

Confirmed in one command: `claude agents --json` returns **two disjoint row
shapes** — the two blocked nodes carry `id` + `state:"blocked"` and **no `pid`**
(ledger entries), while the two live sessions carry `pid` + `status` and **no
`state`** (processes). Both live nodes also read `backend:"daemon"`, not `"peer"`,
so the peer transport branch is never even entered for them, and
`~/.claude/daemon/roster.json` reads `workers: []`.

**(a) A LIVE blocked node is addressable, but the answer is HELD, not acted on.**
`bg` is a first-class peer kind, so a running `--bg` node is enumerable and can be
messaged. Two things stop that from being an answer path:

- **The peer transport never writes `queuedPrompt`.** Its three outcomes are
  delivered, no-socket and send-failed, and none touches disk. `queuedPrompt` is
  written only by the *daemon* backend's failure branches, and only when the
  daemon is **unreachable** — so it encodes *"we could not determine the node's
  fate"*, not *"the node is dead, here is its mail"*. The existing `dag_tick`
  seam is therefore not something a cross-session message can drive.
- **2.1.224's new inbound gate defaults to HOLD for a non-interactive node.**
  With `crossSessionInbound` unset (it is unset in both this repo's and the user's
  `settings.json`), mode parity applies and every branch that is not a prompting
  mode lands on `hold`. Hold is a dead end for a `--bg` node: the buffer is
  **in-memory** (so it dies with the process and evicts oldest when full) and
  approval is a **React dialog a background node has no surface to render**.

**No non-interactive verb carries text to a job either.** `claude
respawn|attach|logs|stop|rm` — none accepts a prompt or message argument, and the
binary explicitly **refuses to attach a blocked job** (*"That session is blocked —
back to the list"*).

### 3.3 The route that DOES reach a not-running node — and why the watchdog must not take it

There is exactly one, and it is not a message: FleetView's reply path, on getting
"not running", **respawns the node with the human's text as `initialPrompt`**.

This sharpens #601 rather than contradicting it. #601 forbade the watchdog from
respawning a NEEDS_HUMAN node because a **bare** respawn returns the node idle
with no prompt, discarding the payload. A respawn carrying `initialPrompt` is a
different operation — it delivers. The distinction is now on the record so a
future reader does not resolve the tension in the wrong direction: **`dag_project`
still never respawns anything.** It is a projector; taking the delivery route
would make it a second actor on the fleet and re-cross the R1 boundary from the
other side.

### 3.4 Consequences for this spec

1. **The answer path is OUT of scope, on evidence.** #601, #616 and #604 each
   stopped at R1's one-directional boundary as a judgment call. It is no longer a
   judgment call: for the case that matters, no inbound route exists at all.
2. **`_needs_human_reason()`'s scope qualifiers survive unchanged.** The previous
   session speculated its *"separate route this module cannot close"* count was
   *"plausibly 3, not 2"* on the strength of the string deltas. **It is still 2** —
   nothing in 2.1.224 added a route. Do not edit that golden string on this basis.
3. **The comment's "How to answer" section becomes concrete** rather than vague:
   answer through FleetView's reply on the node, which respawns it with the answer
   as `initialPrompt`. For a node whose job dir is gone, say so — there is nothing
   to answer, and the comment should not imply otherwise.
4. **#590 inherits an unchanged question.** The harness's own supervisor respawn
   predicate reads `state`/`tempo`/`queuedPrompt` and never `needs`; whether it
   fires for a `blocked` node remains unverified, and 2.1.224 did not touch it.

### 3.5 A seam this leaves open — for a later ticket, not this one

The respawn-with-`initialPrompt` route is **a scheduler action, not a message** —
it restarts the node. So a future ticket that builds an answer path on it would
sit squarely on the scheduler's side of R1's boundary and would **confirm** that
boundary rather than make it decorative. That is a real option, and naming it is
the point; building it is not in #602.

### 3.6 What the probe could NOT establish — do not read past these

- **No end-to-end live send was performed.** Case (a) is a code read of the
  binary plus the tool's own schema, not an exercised probe. The mutation ban on
  `~/.claude/jobs/**` and the no-long-lived-agents constraint made the clean
  version unavailable. **If a later ticket wants the live-node path, that probe
  must be run for real.**
- **`claude attach` on a blocked job is binary-only evidence**, deliberately not
  run against the two live nodes.
- **Whether a `--bg` node's socket survives entering `state=blocked` is
  unconfirmed.** The registry status vocabulary has no `blocked` value.
- **The bridge rows' raw ids were never observed** — "same session, not a
  similarly-titled one" is SUSPECT/one-route (§3.2's honest bound).
- **The reply path itself was not exercised.** The code refuses *by-name* sends;
  whether a live bridge session can be reached *in reply* was not tested, since
  that requires an inbound message first.

None of these weakens the case-(b) answer. Its load-bearing half is
**addressability**, read straight off the `SendMessage` tool's own `call` —
`kind: "not-found"` → `success: false` — and that does not depend on any of the
open items above. The `idle`-vs-`blocked` disagreement is also resolved, and the
resolution is the third option: **two probes of different facts, neither broken.**
The bridge row's `idle` is the server's record; `state.json`'s `blocked` is the
local job ledger's last write. The server was never told about `blocked` — that
vocabulary is local-only — and the harness ships a stale-bridge classifier
precisely because it expects the divergence.

---

## 4. Build plan

Phased so each phase is independently shippable and independently green. **No
phase begins before the previous one's gates pass** (`verify-before-advancing.md`).

### Phase 1 — the artifact, no automation ✅ **DONE 2026-08-07**

1. ✅ `dag:needs-human` label created (`d93f0b`). Label count 23 → 24.
2. ✅ Standing escalation issue created: **#623**, labelled, contract in its body.
3. ✅ Both live escalations hand-projected with the §2.3 format —
   [`ad8baf35`](https://github.com/ray-manaloto/dotfiles/issues/623#issuecomment-5213944853)
   and
   [`fdfdaf90`](https://github.com/ray-manaloto/dotfiles/issues/623#issuecomment-5213947098).

**Why by hand first.** `docs/specs/ticket-bound-receipts.md` piloted exactly this
way and its §12 verdict is the reason: writing the artifact by hand is what
reveals which fields are real and which become ritual, *before* a module hardcodes
them. Two instances is a thin pilot, but two is every case that exists — **and it
paid: three format defects fell out of producing the first comment** (§2.3).

**Gate — PASSED, round-tripped through the API rather than eyeballed.** All three
payloads (`ad8baf35.needs`, `fdfdaf90.needs`, `fdfdaf90.suggestedReply`) were
re-fetched from `/issues/623/comments`, extracted from their fenced blocks, and
compared to `state.json` — **3/3 byte-identical**. Markers: one per comment,
`node=`+`digest=` pairs unique across the issue.

⚠️ **The gate as originally written would have PASSED the broken draft.** "Renders
correctly" is an eyeball check, and a backticked payload in a blockquote *renders
fine* — it just is not the payload. The gate only became real when it was
restated as a **byte comparison against the source**. A rendering check cannot
detect a fidelity loss that renders nicely.

### Phase 2 — `dag_project.py`, read-only ✅ **DONE 2026-08-07**

`--dry-run` prints exactly what it would post and posts nothing; a run WITHOUT it
**refuses (rc=2)** rather than exiting 0 having done nothing, which would read as
a successful projection. Reuses `dag_tick`'s predicates per §2.1 invariant 1 —
`node_from_state`, `is_needs_human`, `normalize_needs`, `is_stalled`, all by
import. Bound by the new `workflow.dag-projection-wiring` contract, whose FAIL
arm was proven by deleting the delegation call site.

⚠️ **The mise task landed HERE, not in phase 4, and the spec is corrected rather
than left disagreeing with the tree.** `mise-tasks-only.md` says a recurring
workflow ships its task WITH it, or every invocation is the hand-rolled `uv run`
that rule exists to prevent. Phase 4 still owns the **LaunchAgent** — the
schedule, not the verb.

**Gate — PASSED, and it was a real control arm.** `--dry-run` was run against a
fixture of the two real payloads and compared to the comments **already live on
#623**, which were hand-written before this module existed: marker present in
both, and all 3 fenced payload blocks reproduced exactly. A projector verified
only against fixtures it authored proves nothing; these it did not author.

**Two defects the gate caught that no test would have:**

1. **The mtime was wrong, and `updatedAt` was right.** The fixture was built with
   `cp`, so the projector reported the day of the COPY as the node's last update
   while `updatedAt` still held the real one three weeks earlier. Fixed in the
   CODE, not the fixture: **`updatedAt` is authoritative, the file mtime is the
   fallback**, and a disagreement between them is reported rather than hidden —
   it means something that is not the harness touched the file. A timestamp a
   file operation can rewrite is not a measurement of when a human was asked.
2. **`git checkout --` cannot restore an UNTRACKED file.** Four mutation arms ran
   against the new module and every restore silently failed, so the mutations
   accumulated and the "restored" run was still broken. `git add` the file before
   mutation-testing it. (The blast radii are still good data: 2 / 3 / 4 / 6 —
   each mutation kills a different and growing set, which is the health signal
   `tests/AGENTS.md` describes.)

### Phase 3 — the write path ✅ **DONE 2026-08-07**

Label application, comment posting, marker-based dedupe, and the §2.2
closed-target table. The `gh` CLI is a real system boundary, so it is
**injected** (`GhRunner`) rather than constructed — every test substitutes a
recorder and none reaches the network.

**Neither `--dry-run` nor `--write` REFUSES (rc=2), and so does passing both.**
Writing to the tracker is outward-facing, so it is never what a bare invocation
falls into.

**Gate — PASSED at the unit level, with one live arm.** Run twice: the first
posts, the second sees its own marker and posts **nothing** (`gh issue comment`
absent from the second run's recorded argv). A dedupe verified only on the first
run is a check that can only pass.

The live arm exercises the REAL `default_gh_runner` and writes nothing: with zero
escalations, `--write` reported *"NO API call was made"* and #623's comment count
was unchanged (4 → 4), while the same binary on the fixture produced 2 would-post
blocks. So the idle path is silent by **measurement**, not by assumption.

⚠️ **What is NOT proven, stated rather than implied: a LIVE two-run against a
scratch issue.** The dedupe is proven against an injected recorder, which cannot
catch a mistake in how `gh` itself is invoked — a malformed `--body`, a wrong
`-R`, an API shape change. Phase 4 (the LaunchAgent) should not be armed until
that live two-run has happened against a scratch issue with a manufactured
escalation (`claude --bg --bare` produces one in seconds, §4 phase 2).

Four decisions worth carrying:

- **`None` and `set()` mean OPPOSITE things** when reading a target's existing
  markers, and the code must not collapse them: empty says *"read it, nothing
  there, safe to post"*; `None` says *"could not read it"*, and posting then
  risks a duplicate. Unreadable **SKIPS** — a duplicate escalation is noise a
  human must sort out, a skip is retried next tick with nothing lost. Reported as
  a distinct `skipped-unreadable` outcome, never folded into "skipped".
- **A closed STANDING issue is reopened; a closed BOUND issue is not.** Reopening
  the standing target is in-bounds (#573: only the scheduler transitions state,
  and this is the scheduler). Reopening a *work* issue is **rework**, whose
  semantics `575.md` R7 owns — so a bound-but-closed node falls back to the
  standing issue with a routing note instead.
- **An existing label is SUCCESS.** `gh label create` exits non-zero for the
  steady state, so that one failure is read as "already there" and any other is
  reported.
- **The marker regex is anchored on the full HTML comment**, so a comment
  *discussing* a marker cannot register as one — pinned by a test.

### Phase 4 — the mise task and the LaunchAgent ✅ **DONE 2026-08-07**

The task landed in phase 2 (see there for why). This phase adds
`[bootstrap.macos.launchd.agents.dotfiles-dag-project]`: `start_interval = 300`,
the literal `~/.local/bin/mise` program path (the `mise`-is-a-zsh-function trap),
the same explicit `environment` PATH as the tick, and `--write` passed
**explicitly** because a bare invocation refuses. **INERT until a human runs
`mise bootstrap macos launchd-agents apply`** — never implicit (`do-not.md`).

It is a SECOND agent rather than a phase inside the tick, and that is the design:
R1 assigns projection to the scheduler while the tick is the watchdog, so #573's
loop absorbs this by re-wiring a LaunchAgent rather than refactoring the watchdog.
300s not 60s — a human's question does not become more answerable at 60s, and the
tracker is a shared rate-limited resource.

**The precondition this spec set is MET.** The live two-run ran against scratch
issue #629 on 2026-08-07:

| Run | Outcome | Comments on #629 |
|---|---|---|
| 1 | `posted 0ecc0cb5 -> #629`, `dag:needs-human` applied | **1** |
| 2 | `skipped-duplicate` | **1** — posted nothing |

The escalation was **manufactured** (`claude --bg --bare` → `blocked` +
`needs: "login required — run /login"`, §4 phase 2), and the node was stopped and
removed before the gate ran, so nothing in `~/.claude/jobs/` was touched. The
posted comment round-tripped through the real `gh --body`: payload verbatim
inside its fence, marker intact, the **BOUND** path taken (a `dag-binding.json`
pointed it at #629, so the bound branch is live-proven too), the reason string
verbatim, and the em-dash preserved. Scratch issue closed.

That is exactly what an injected recorder cannot check — a malformed `--body`, a
wrong `-R`, an API shape change — which is why it was the gate.

### Phase 5 — the binding, written at dispatch

`dag-binding.json` (§2.2) plus the bound-node branch. **This phase is blocked on
a dispatcher existing** and may land with #573 rather than here; the unbound path
from phases 1–4 is complete without it.

### Phase 6 — contracts and docs, in the same change as the code

- **Edit `workflow.dag-tick-wiring`'s description** in
  `python/verification/suites.toml` — it records the deferral in three places
  (*"#602 owns that projection"*, *"no in-tree component emits the label"*,
  *"only the IMPLEMENTATION is pending"*). Closing #602 without this leaves the
  contract asserting a gap that no longer exists.
- **Edit `dag_tick.py:161-164`** — the `⚠️ Nothing in this process emits it —
  #602 owns the projection` comment, same reason.
- ⚠️ **Do NOT edit `_needs_human_reason()`'s `"is NOT done here — #602"`
  clause.** It is scoped to *this process*, and it stays true after #602 ships:
  the tick still does not project. It is pinned by golden equality; changing it
  fails `test_plan_needs_human_reason_claims_no_action_this_module_skips`, and
  that test is doing its job.
- Add a `workflow.dag-projection-wiring` contract binding the new chain.
- Write `docs/receipts/602.md`.

---

## 5. Known holes — named, not papered over

1. **The standing issue grows without bound.** Every unbound escalation appends
   forever, and nothing prunes. No hygiene mechanism is specified because none is
   needed at 2 escalations in 3 weeks; revisit if it exceeds ~50 comments.
2. **A node that escalates, is answered, and re-escalates with the SAME question
   posts once.** The digest cannot distinguish "still asking" from "asking
   again". Accepted: the label persists, so the state is not lost — only the
   second timestamp is.
3. **Label removal is unspecified.** Nothing in this slice clears
   `dag:needs-human` when an escalation resolves, because nothing observes
   resolution. The label is therefore **monotone** in slice 1 and a human clears
   it. State it in the comment so no operator reads a stale label as live.
4. **Two LaunchAgents now read `~/.claude/jobs/**` on different intervals.**
   Reads only, no lock shared, no interaction — but it is two schedules to
   reason about, and #573's loop should collapse them.
5. **The `gho_` token's scopes were read, not exercised for a write.** M4 proved
   `repo` scope is present and a read call succeeds; it did not post a comment
   from the launchd env. Phase 3's gate closes this.
6. **`_needs_human_reason()` is reproduced verbatim into a GitHub comment**, so
   the golden-equality test now indirectly pins operator-facing tracker content.
   That is intended, and worth knowing before someone "improves" the string.
7. ⚠️ **An escalated node whose daemon has died cannot be cleaned up by any
   automated path — and that is not this spec's to fix.** `claude rm` needs the
   daemon socket (M10), and `dag_tick` deliberately never acts on a NEEDS_HUMAN
   node, which is the whole of #601. So the class of node most likely to go
   stale is exactly the class nothing can remove. Both phase-1 nodes hit this;
   the manual cure is to spawn any `--bg` session, which revives the supervisor.
   **This belongs with #590 (stall recovery), not #602** — a projector that
   started removing nodes would stop being one-directional. Recorded here because
   #602's own phase 1 is where it surfaced.

---

## 6. What this would have caught — and what it would not

**Would have caught:** the live case. Two nodes have sat `blocked ∧ needs` since
2026-07-13 and 2026-07-22 with their questions visible only in a launchd log. With
this shipped, both appear on the tracker as labelled, quoted, timestamped
comments.

**Would NOT have caught:** anything about whether the *answer* gets back. §3
settles that this projection is one-directional by measurement, not merely by
policy. A human reading the comment still answers out-of-band.

**Would NOT have caught:** an escalation whose node was `claude rm`'d before the
next projector tick — the job dir is the only source, and it is gone. Latency to
first projection is up to 300s.

---

## 7. Sources — what was actually opened

- [#602](https://github.com/ray-manaloto/dotfiles/issues/602) — the ticket, read
  in full. It carries its own correction to #601's close-out: `575.md` **settles**
  the label spelling; what is deferred is the owner and the comment format.
- `docs/receipts/575.md` — R1 (projection scheduler-owned, one direction), R5
  (a blocker names what was exhausted), R7 (rework), and the *"Deferred
  deliberately"* line.
- `docs/receipts/573.md` — tracker-owned counters, the labels/comments/body
  split, the stokowski dual-audience precedent, and the two gotchas (never read
  back your own write; verify a mutation from its own response body).
- `python/src/dotfiles_setup/dag_tick.py` — the seam: `NEEDS_HUMAN_LABEL:176`,
  `is_needs_human:399`, `is_reply_queued:435`, `classify:470`,
  `_needs_human_reason:569`, `plan:653`, the note loop at `:1001`.
- `python/verification/suites.toml` — `workflow.dag-tick-wiring`, which records
  the same deferral in three places and must be edited to close #602.
- `python/src/dotfiles_setup/codex_verdict.py` — the `schema_version` precedent
  and the "the file exists is necessary but never sufficient" discipline.
- `docs/specs/ticket-bound-receipts.md` — the pilot-by-hand-first precedent
  adopted for phase 1, and its §12 verdict on which fields become ritual.
- `mise.toml` — `[tasks.dag-tick]:514`, the LaunchAgent block at `:1064`, and its
  `environment` PATH (the M4 probe input).
- `~/.claude/jobs/*/state.json` — all 8, read-only.
- `docs/research/kb/reports/agents/602-crosssession-sendmessage-probe.md` — the
  ruling-3 probe, persisted verbatim.

## 8. Review history

- **2026-08-07** — scoped. Ray ruled on three forks before scoping began (owner
  deliverable shape, R5-as-label, answer-path-probe-first) and on a fourth the
  scoping pass uncovered (§2.2, the projection target for an unbound node). The
  answer-path probe ran during scoping and **refuted** the prior session's
  reading of the 2.1.224 string deltas (§3).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  this spec is for; #602, #601, #604, #616, #573, #575, #580, #590 read via `gh`
  and via `docs/receipts/`.
