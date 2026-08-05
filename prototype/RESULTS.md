# PROTOTYPE RESULTS — agent-team mechanism bets

Run 2026-08-04c on **Claude Code 2.1.221**, macOS, in `ray-manaloto/dotfiles`.
Claim 6 was added 2026-08-04d on **2.1.222** — its changelog touches nothing in the workflow
resume path (checked), but the version differs from claims 0–5 and is recorded rather than assumed.
Branch `prototype/agent-team-mechanisms` (throwaway — the primary source for these claims).

Every claim reports **both arms**. A probe that has only ever produced one answer is not
evidence (`.claude/rules/probes-need-a-control-arm.md`).

| # | Claim | Verdict |
|---|---|---|
| 0 | *(unplanned)* Passing `name` to the Agent tool changes **what kind of agent you get** | 🔴 **CONFIRMED — and it invalidates an assumption in `docs/agent-team.md`** |
| 1 | A dynamic workflow works: `agent({schema})`, `pipeline()`, per-stage `model`, resume | 🟢 **CONFIRMED — all four, with corroboration** |
| 2 | A frontmatter `Stop` hook can block a delegated agent from finishing | 🟢 **CONFIRMED on the subagent path — it fired, blocked, and forced extra work** |
| 3 | `TeammateIdle` is reachable from the CLI, not TypeScript-SDK-only | 🟢 **REFUTED the doubt — the CLI ships it** |
| 4 | `memory: project` persists a fact across spawns | 🟠 **PARTLY REFUTED — it writes, but the next spawn does not read it** |
| 5 | `permissionMode` / `hooks` / `mcpServers` are ignored for plugin-scoped subagents | 🟢 **CONFIRMED — already documented, no probe needed** |
| 6 | Resuming an **interrupted** run: replay stops at the first unfinished agent, and everything dispatched after it re-runs *even if it completed* | 🟢 **CONFIRMED — measured, then confirmed at the source** |

---

## Claim 0 — `name` silently decides whether you get a teammate or a subagent

**This was not on the list. It surfaced because claim 2's probe failed in a way the probe
could distinguish**, and it is the most consequential result of the run.

### What was measured

| Spawn | Result | Team config entry | Transcript |
|---|---|---|---|
| `Agent(subagent_type: proto-stop-blocker, name: "proto-stop")` | *"Spawned successfully… will receive instructions via mailbox"*, id `proto-stop@session-cd1818f5` | **present**, `agentType: proto-stop-blocker` | teammate path |
| `Agent(subagent_type: general-purpose)` — **no `name`** | *"Async agent launched successfully"*, id `ab3f68050465a04ef` | **absent** | own `tasks/<id>.output` |

**Control arms.** `ab3f68050465a04ef` in the team config → **0 occurrences**; `proto-stop` in
the same file with the same command shape → **4**. The grep discriminates, so the absence is
real. And every one of the **17** agents spawned this session with a `name` is recorded as a
team member, while **0** subagent-path transcripts
(`~/.claude/projects/{project}/{sessionId}/subagents/agent-*.jsonl`) were written in the same
window — so nothing at all ran down the subagent path.

### A second difference, found by accident

The two paths **resolve agent types from different registries.** `proto-stop-blocker` was
created mid-session. It resolved fine on the named path. On the unnamed path the same
`subagent_type` returned:

> `Agent type 'proto-stop-blocker' not found. Available agents: …`

— and the list omitted both agent files created during this session.

### Why it matters

`docs/agent-team.md` §2 says role definitions in `.claude/agents/` are *"the only place all
sixteen knobs apply"*. **That is true only for a spawn without a `name`.** Naming an agent —
which is the natural thing to do, and which was done 17 times today — silently converts it to a
teammate, where `skills`, `mcpServers` and `hooks` are documented as ignored.

**The failure mode is silence.** No warning, no error. A role definition carefully tuned with
`hooks:` and `skills:` runs with neither, and looks like it worked.

**Consequence for the design:** the enforcement layer (a `Stop` hook in role frontmatter) and
per-role skills/MCP are only available if roles are spawned **unnamed** — which also costs the
mailbox and the ability to address an agent by name. That is a real trade-off the design has to
make explicitly, not discover later.

---

## Claim 2 — can a frontmatter `Stop` hook block? **YES, on the subagent path**

The first attempt was inconclusive because the agent ran as a teammate (claim 0). Re-run
**unnamed**, once the agent-type registry had picked the definition up:

| Signal | Result |
|---|---|
| `/tmp/proto-stop-gate.task-done-unnamed` | written — the agent did its original task |
| hook log, **call 1** | fired, `stop_hook_active: false` → returned `{"decision":"block", …}` |
| `/tmp/proto-stop-gate.witness` | **`PROTO-STOP-GATE-OBSERVED`** |
| hook log, **call 2** | fired, `stop_hook_active: **true**` → allowed, agent finished |
| agent `tool_uses` | **2** — the original `echo`, plus the forced witness write |

**The witness file is the finding.** The agent was never asked to write it in its prompt; the
only instruction to do so came from the hook's `reason`. So a `SubagentStop` hook can **force a
delegated agent to do work before its turn ends**, which is exactly the mechanism the
"deliver before you go idle" rule has always needed.

Both arms observed in one run: the block path (call 1) and the allow path (call 2).

### The payload, which is what makes enforcement possible

```
agent_id · agent_transcript_path · agent_type · background_tasks · cwd ·
hook_event_name · last_assistant_message · permission_mode · prompt_id ·
session_crons · session_id · stop_hook_active · transcript_path
```

**`agent_transcript_path` is present**, so an enforcing hook can *inspect what the agent actually
did* rather than merely nag. And `stop_hook_active` flips `false` → `true` between calls — the
loop-guard signal, and the thing `cc-native` warns must be anchored on correctly.

⚠️ **Scope:** proven for a frontmatter hook on the **unnamed/subagent** path only. On the named
teammate path it never fired at all.

## Claim 3 — is `TeammateIdle` CLI-reachable?

**The doubt is refuted: the CLI ships it.** Counted directly in the installed binary
(`~/.local/share/claude/versions/2.1.221`):

| Token | Hits | Role |
|---|---:|---|
| `TeammateIdle` | **30** | under test |
| `SubagentStop` | 73 | control — known CLI event, expect > 0 |
| `TaskCompleted` | 34 | control — known CLI event, expect > 0 |
| `Qwlfbz9NotAnEvent` | **0** | control — invented, expect 0 |

Both directions arm the probe: known-present tokens return hits, an invented token returns
zero. The SDK's *"TypeScript-only"* note describes the **SDK**, not the CLI.

⚠️ **What this does not prove.** Shipping the string is not the same as firing the event with a
blocking payload. This removes the reason to doubt; it does not verify the behaviour.

---

## Claim 4 — does `memory: project` persist a fact? **It writes. Nothing reads it.**

Two spawns, both unnamed, second one with no conversation history.

| Arm | Result |
|---|---|
| **write** | ✅ created `.claude/agent-memory/proto-memory/witness_token_marlinspike.md` — **the documented path** for `memory: project` |
| **recall** | ❌ returned **`NOTHING IN MEMORY`**, with **`tool_uses: 0`** |

`tool_uses: 0` is the decisive number: the second spawn **never even read the file**. The store
was not injected into its context, and it did not go looking.

### The likely cause, with a control arm

The probe's store contains **only the topic file**. It has **no `MEMORY.md`**.

| Store | Has `MEMORY.md`? |
|---|---|
| `~/.claude/agent-memory/researcher/` (pre-existing, working) | **yes**, alongside 9 topic files |
| `.claude/agent-memory/proto-memory/` (this probe) | **no** |

Auto-memory injects `MEMORY.md`; topic files are read *on demand*. The agent wrote a topic file
and never indexed it, so it wrote to a store nothing reads. That settles open item 9 of the
`docs-subagents-deep` work queue in the unhelpful direction: **an unindexed topic file was
inert** — neither injected nor spontaneously opened.

**Design consequence:** `memory:` is **not** automatic durable learning. A role that records a
lesson without maintaining its own `MEMORY.md` index has written to `/dev/null` with extra steps
— the same failure this repo already documents for its own memory index.

### ⚠️ And the teammate path is actively harmful

The *named* run of the same agent did not write to `.claude/agent-memory/` at all. It wrote into
the **shared session auto-memory** — `~/.claude/projects/<project>/memory/` — and **added an
index line to the project's `MEMORY.md`**, the file loaded into every session.

That file was deleted and the index line removed during this run (verified: 0 remaining
references, `MEMORY.md` intact at 113 entries).

**At nine roles this is a real hazard.** Nine teammates with `memory:` would all write into one
shared store and index themselves into a `MEMORY.md` that is already near its read limit — while
nine *subagents* would each get an isolated store, and none of them would be read unless the
index is maintained.

## Claim 5 — are fields ignored for plugin-scoped subagents?

**Confirmed from the vendor docs; no live probe needed, and none should have been planned.**
`$CC/sub-agents.md` states *"Ignored for [plugin subagents]"* on exactly three rows:

| Line | Field |
|---|---|
| 282 | `permissionMode` |
| 285 | `mcpServers` |
| 286 | `hooks` |

Control arm: a phrase known to be in the same table (`"Maximum number of agentic turns"`)
returns 1, so the grep is reaching the table rather than missing it.

**Design consequence:** the team **cannot ship as a plugin** if any role needs per-agent hooks,
`permissionMode`, or MCP servers. That was flagged UNVERIFIED in the framework review on the
strength of a third-party repo's verifier; the vendor states it outright.

---

## Claim 1 — does a dynamic workflow actually work?

**CONFIRMED.** Run `wf_c18255a9-2ea`, 6 agents, **0 errors**, **10.0 s** wall clock.

### 1a. `agent({schema})` returns a validated object, not prose

```json
{"token": "WORKFLOW-SCHEMA-OK", "n": 7}
```

`is_object: true`, `token_matches: true`, `n_is_number: true`. The integer came back as a
number, so the schema is enforced at the tool-call layer rather than hopefully parsed.

### 1b. `pipeline()` fans out one agent per item

3 items in → **3 results out, 0 nulls**. Tokens `FAN-alpha` / `FAN-beta` / `FAN-gamma` with
indices `0` / `1` / `2` — so the stage callback's index argument is real and ordering is
preserved in the returned array even though the journal shows `beta` completing before `alpha`.

### 1c. Per-stage `model` routing reaches a different model — **two independent signals**

This was the sub-claim most at risk of a weak probe, because a model's self-report is not
authoritative. Both arms agree:

| Signal | Routed stage (`model: 'haiku'`) | Unrouted stage |
|---|---|---|
| **Harness's own record** (`agent-*.meta.json`) | `{"agentType":"workflow-subagent","spawnDepth":1,"model":"haiku"}` | `{"agentType":"workflow-subagent","spawnDepth":1}` — **no model key** |
| Agent self-report | `claude-haiku-4-5-20251001` | `claude-opus-5[1m]` |

**Exactly one of the six agents carries a `model` key**, and it is the one the script routed.
That is the harness's metadata, not the model's opinion — the self-report merely corroborates.

### 1d. Bonus finding — workflow agents are **subagents**, not teammates

Their transcripts land on the subagent path
(`…/subagents/workflows/wf_<id>/agent-<id>.jsonl`) and their metadata says
`agentType: "workflow-subagent"`, `spawnDepth: 1`. **None appears in the team config.**

That matters for claim 0: routing work through a workflow keeps the subagent characteristics
that a *named* direct spawn silently gives away.

### 1e. ⚠️ Cost signal worth recording

**465,028 subagent tokens for six trivial agents** — roughly **78 k per agent** for tasks that
were one sentence each. Every workflow agent pays a full project-context load regardless of how
small its job is. (Corroborating datapoint from the same session: an unnamed direct subagent
spent 89 k tokens to run a single `echo`.)

This sharpens the resume constraint rather than contradicting it: many small agents preserve
more *progress*, but each one costs a full context load, so "small" should mean *few, tightly
scoped stages* — not a wide fan-out over trivia.

### 1f. Resume — **CONFIRMED, and the numbers are unambiguous**

Method: append **one** new stage to the already-completed script and re-invoke with
`resumeFromRunId: wf_c18255a9-2ea`. Everything above the new stage is byte-identical, so it must
replay from cache. **The control arm is the contrast with the first run.**

| | First run | Resume run |
|---|---:|---:|
| agents | 6 | **7** (6 cached + 1 new) |
| **`tool_uses`** | 6 | **1** |
| **subagent tokens** | **465,028** | **81,256** |
| wall clock | 10,052 ms | **3,718 ms** |
| errors | 0 | 0 |
| agent transcript files on disk | 6 | **7** (exactly one added) |

**`tool_uses: 1` is the decisive figure** — only one agent actually executed. The token count
lands at ~81 k, i.e. almost exactly the ~78 k single-agent cost measured in 1e, so the other six
cost essentially nothing. One new transcript file appeared, not six.

The returned object still carries all four probes' results, so **cached results are real values,
not placeholders**: `probe1`, `probe2` and `probe3` came back fully populated without re-running.

⚠️ **What this does *not* test:** an **interrupted** run — this resumed a run that had completed
cleanly. That half is **claim 6** below, and it is the half that constrains role granularity.

---

## Claim 6 — resuming an INTERRUPTED run

**CONFIRMED**, by two independent routes: a live interrupt, then the harness's own replay code.
Run `wf_99fff833-07e`, script `prototype/interrupt_resume_probe.js`, unchanged between the two
invocations (any edit would have invalidated the cache and destroyed the measurement).

### The fixture, and why it can produce every answer

Four agents, each stamping `START` before its work and `END` after into its own witness log, so
**execution count is counted per agent** rather than inferred from aggregate tokens:

| agent | dispatch order | designed state at the interrupt |
|---|---|---|
| `before` | 1st | finished |
| `slow` | 2nd (first thunk of a `parallel()`) | **in flight** — a 240 s `python3` sleep |
| `fast_b` | 3rd (second thunk of the same `parallel()`) | **finished**, but dispatched *after* `slow` |
| `after` | 4th, past the barrier | never started |

`fast_b` is the discriminating arm and `before` is the control arm. If `before` had re-run too,
"everything re-ran" would be indistinguishable from "an interrupted run caches nothing", and
`fast_b`'s reading would mean nothing.

The fixture was **verified before the interrupt, not after** — the poll loop stopped only once
`before` and `fast_b` had `END` lines and `slow` had a `START` with no `END`, and the `slow`
agent's `python3 -c 'import time; time.sleep(240)'` child was confirmed alive in `ps`.

### What the interrupt itself did

`TaskStop` on the workflow task:

| Signal | Result |
|---|---|
| `slow`'s `python3` child process | **gone** — the abort propagates into the agent's shell child |
| `journal.jsonl` before vs after the stop | **byte-identical**, 5 lines — the stop writes nothing |
| orphan record | `slow` left a `started` row with **no matching `result`** |

### The measurement

| agent | run 1 | resume | executions total |
|---|---|---|---:|
| `before` | START+END | **nothing** — no new agent, no new witness line, no new transcript | **1** ✅ cached |
| `slow` | START only (killed mid-body) | START+END, **new agentId** | 2 |
| `fast_b` | START+END, **`result` in the journal** | START+END, **new agentId** | **2** 🔴 re-ran anyway |
| `after` | — | START+END | 1 |

Corroborating counts, all from the harness rather than from the agents:

- **transcript files 3 → 6**: exactly **three** new ones, i.e. one per live agent and none for `before`.
- **`tool_uses: 10`** on the resume, and the per-transcript counts sum to exactly that:
  `slow` 4 + `fast_b` 3 + `after` 3 = 10, **`before` contributing 0**. A cached agent does not
  merely return early — it never runs a tool.
- **journal 5 → 11 lines**, and key `v2:72448e…` (`fast_b`) now carries **two `result` rows**.
- `subagent_tokens` **253,446** for the 3 live agents ≈ 84 k each, consistent with the ~78 k/agent
  of 1e. **The wasted work is `fast_b`'s ~84 k — an agent that had already delivered its result.**

### The source, which settles an alternative my fixture could not

My fixture cannot separate *positional* ("everything after the first unfinished call") from
*group* ("the whole `parallel()` barrier re-runs if any member is unfinished") — both predict
`fast_b` re-running. The installed binary settles it. In `2.1.222` at offset `249187093`:

```js
if(a){ he = kgp(ye, ee, b), b = he;
       let St = T ? void 0 : l?.results.get(he);
       if(St !== void 0) return /* …progress: cached:true… */ , m(St.result);
       T = !0;
       let $e = l?.started.get(he);
       if($e && $e.length > 0) N("tengu_workflow_journal_started_hit_respawn", {attempts: $e.length}) }
```

Three things fall straight out of it:

1. **`T` is a sticky first-miss flag.** `T ? void 0 : results.get(he)` — once one lookup misses,
   `T = !0` and **every later call skips the cache lookup entirely**, whatever the journal holds.
   That is positional, not group-scoped. `parallel()` is irrelevant except that it fixes the
   dispatch order.
2. **The key is a rolling chain hash**: `kgp(prompt, opts, b)` with `b` the *previous* key, then
   `b = he`. So a key encodes the whole preceding call sequence — which is why `fast_b`'s re-run
   reused the *same* key under a *new* agentId, and why editing any earlier call invalidates
   everything downstream.
3. `Inb(opts)` hashes only `schema`, `model`, `effort`, `isolation`, `agentType` — **`label` and
   `phase` do not affect the key**, so renaming a stage for readability is cache-safe.

There is even a telemetry event for exactly this case —
`tengu_workflow_journal_started_hit_respawn`, counting the re-spawn of a key that had already
started. Control arm for that grep: a known event token returns 2, an invented one returns 0.

### Design consequence — this is the granularity argument, and it is sharper than "many small stages"

The re-run cost of an interrupt is **everything dispatched after the earliest agent that has not
finished**, at a full ~78–85 k context load each. Two rules follow that were not obvious before:

- **A wide `parallel()` is the worst shape to be interrupted in.** All thunks dispatch at once, so
  a single slow member early in the array discards every completed result after it. A 10-agent
  fan-out interrupted while agent 2 is still running throws away 8 finished agents ≈ 650 k tokens.
- **Order inside a `parallel()` is load-bearing for resume economics** — put the likely-slowest
  work **last** in the array and the fast members ahead of it survive an interrupt. This follows
  from the sticky-flag mechanism above; it is *inferred from the source*, not separately measured.

It also tempers 1e's "few, tightly scoped stages": small stages preserve more progress on an
interrupt, but each still pays a full context load, so the win is only real where a stage boundary
sits **before** the long pole.

⚠️ **Scope.** `TaskStop` is a *controlled* abort. A hard crash, an OOM, or a machine losing power
mid-append could leave a torn journal line; `LocalFileJournal.load()` catches the `JSON.parse`
failure per line, logs it and continues, so a torn tail should degrade to an earlier cache miss
rather than a crash — read from the source, not measured.

## What to change in `docs/agent-team.md`

1. **§2 needs a correction**: "the only place all sixteen knobs apply" holds for **unnamed**
   spawns only. Naming an agent downgrades it to a teammate and silently drops `skills`,
   `mcpServers` and `hooks`.
2. **§9's enforcement design** depends on frontmatter hooks firing, which requires the unnamed
   path. State that dependency, or move enforcement to session-level `settings.json` hooks,
   which apply inside subagents regardless.
3. **§10 item 8** (probe plugin-scoped field ignoring) can be closed — it is documented.
4. **The `TeammateIdle` contradiction can be closed** as far as availability goes.
5. **Role granularity now has a measured constraint** (claim 6): an interrupt discards every agent
   dispatched after the earliest unfinished one, so the orchestration script should keep
   `parallel()` groups narrow, order the long pole last within a group, and put stage boundaries
   before slow work rather than after it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under test
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed 2.1.221 binary was probed directly for claim 3
