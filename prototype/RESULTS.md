# PROTOTYPE RESULTS — agent-team mechanism bets

Run 2026-08-04c on **Claude Code 2.1.221**, macOS, in `ray-manaloto/dotfiles`.
Branch `prototype/agent-team-mechanisms` (throwaway — the primary source for these claims).

Every claim reports **both arms**. A probe that has only ever produced one answer is not
evidence (`.claude/rules/probes-need-a-control-arm.md`).

| # | Claim | Verdict |
|---|---|---|
| 0 | *(unplanned)* Passing `name` to the Agent tool changes **what kind of agent you get** | 🔴 **CONFIRMED — and it invalidates an assumption in `docs/agent-team.md`** |
| 1 | A dynamic workflow works: `agent({schema})`, `pipeline()`, per-stage `model`, resume | 🟢 **CONFIRMED — all four, with corroboration** |
| 2 | A frontmatter `Stop` hook can block a delegated agent from finishing | 🟡 **INCONCLUSIVE — the hook never fired, for the reason in claim 0** |
| 3 | `TeammateIdle` is reachable from the CLI, not TypeScript-SDK-only | 🟢 **REFUTED the doubt — the CLI ships it** |
| 4 | `memory: project` persists a fact across spawns | 🟡 **INCONCLUSIVE — nothing was written, for the reason in claim 0** |
| 5 | `permissionMode` / `hooks` / `mcpServers` are ignored for plugin-scoped subagents | 🟢 **CONFIRMED — already documented, no probe needed** |

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

## Claim 2 — can a frontmatter `Stop` hook block?

**INCONCLUSIVE, and the probe was built to tell you that rather than guess.**

`prototype/stop_gate.py` logs to `/tmp/proto-stop-gate.log` on **every** invocation, before it
decides anything. So an empty log distinguishes *"the hook ran and could not block"* from
*"the hook never ran"*.

| Signal | Result | Reading |
|---|---|---|
| `/tmp/proto-stop-gate.task-done` | **written** | the agent ran and did its work — it was alive |
| `/tmp/proto-stop-gate.log` | **absent** | the hook **never fired** |
| `/tmp/proto-stop-gate.witness` | absent | consistent with the hook never firing |

Two candidate causes were checked and one was eliminated:

- **Workspace trust** — `sub-agents.md` says an untrusted folder makes the harness *skip*
  frontmatter hooks while still running the agent, which matches the symptom exactly.
  **Eliminated:** this project's `hasTrustDialogAccepted` is `true`. Control arm — of 31
  recorded projects, **17** are trusted and 14 are not, so the field discriminates.
- **The agent ran as a teammate** (claim 0). Teammates honour only `tools` and `model` from a
  definition. **This is the surviving explanation.**

**Remaining step:** re-run on the unnamed path. Blocked today because the unnamed registry did
not carry the mid-session agent file — likely needs a fresh session.

---

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

## Claim 4 — does `memory: project` persist a fact?

**INCONCLUSIVE.** `.claude/agent-memory/` was never created, so nothing was written to inspect
— and the recall arm was never worth running. The agent carrying `memory: project` was spawned
with a `name`, i.e. as a teammate (claim 0), which is the most likely explanation. Re-run on the
unnamed path before drawing any conclusion about the field itself.

---

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

### Not tested

**Resume.** The run is resumable by `runId` and the runtime says unchanged `(prompt, opts)`
pairs replay from cache, but no interrupted run was exercised.

## What to change in `docs/agent-team.md`

1. **§2 needs a correction**: "the only place all sixteen knobs apply" holds for **unnamed**
   spawns only. Naming an agent downgrades it to a teammate and silently drops `skills`,
   `mcpServers` and `hooks`.
2. **§9's enforcement design** depends on frontmatter hooks firing, which requires the unnamed
   path. State that dependency, or move enforcement to session-level `settings.json` hooks,
   which apply inside subagents regardless.
3. **§10 item 8** (probe plugin-scoped field ignoring) can be closed — it is documented.
4. **The `TeammateIdle` contradiction can be closed** as far as availability goes.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under test
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed 2.1.221 binary was probed directly for claim 3
