# SDLC team learning loop — design, NOT built

**Status:** design only, 2026-09-14. Nothing here is implemented.
**Why a design and not code:** operator ruling — "design it, don't build it".
**Parent:** `docs/specs/codex-sdlc-subagent-team.md` (D6, scoped out at grilling Q3).

## The honest starting position

Codex has **no native per-agent performance learning**. "Memories" is a
ChatGPT-account feature for carrying context between chats
(`$KB/agent-harness-docs/docs/codex/app__settings.md:108-111`,
`chrome-extension.md:155`), not a record of how an agent performed on a task. So
every mechanism below is homegrown, which `.claude/rules/use-tool-builtins.md`
permits only with written justification — this file is that justification.

Claude Code's own `memory:` scopes (`.claude/agent-memory/<agent>/`, version
controlled) are the nearest native precedent, but they bind **Claude** subagents.
These six are codex agents; the scope does not reach them.

## What makes a loop possible here at all

The roster's D1 decision gave every specialist an **owned gate**:

| specialist | owned gate |
|---|---|
| `sdlc-python-specialist` | `pytest tests/` |
| `sdlc-config-specialist` | `mise run lint` |
| `sdlc-workflows-specialist` | `mise run pin-actions` |
| `sdlc-documentation-specialist` | `mise run lint-docs` |
| `sdlc-image-specialist` | the image/smoke tier |

That is the substrate. A gate's **real exit code** is an objective per-agent
outcome — no self-assessment, no model judging its own work. This is the one
reason a loop is worth designing rather than hand-waving.

## The signal: three things, all objectively measurable

### S1 — did the owned gate pass?
Per specialist per run: the gate it owns, the command, the **file-captured rc**.
Never a notification's exit code and never a piped tail
(`.claude/rules/verify-before-advancing.md`; task notifications lied four times in
one session).

### S2 — was the dispatcher's team selection RIGHT? (the load-bearing one)

This is the signal worth building the loop for, because it needs no opinion:

> Compare the dispatcher's selected team against the artifacts the change
> **actually touched**, read from `git diff --name-only`.

- An artifact changed whose specialist was **not** selected → an **under-select**,
  the routing failure that matters.
- A specialist selected whose artifacts were **not** touched → an **over-select**,
  wasted tokens.

Both are computed from the diff. Neither asks an agent how it thinks it did.
Measured precedent that this discriminates: on the two verification runs the
dispatcher selected python+workflows for a `python/`+`.github/` task and
config+documentation for a `*.pkl`+docs task, excluding the rest by name (V3, V4
in the parent spec).

### S3 — round count
How many respec rounds a specialist needed before its gate went green. A
specialist that routinely needs two rounds has an instruction problem, not a luck
problem.

## Storage: must be TRACKED, and this is not a detail

`.agent/telemetry/` already exists and holds `*.request.json` files — but
**`.gitignore:109` ignores `.agent/`**, so it is machine-local and dies with a
`git clean -xdf`. This session's own coverage audit found **nine** findings
tracked nowhere, the worst being its own rank-1 action (now #1116). A learning
signal in a gitignored directory is a learning signal one clone away from zero.

So: an **append-only JSONL under a tracked path**, one record per specialist per
run, sibling to the existing report tree. Append-only for the same reason
`findings.md` is — a codex lane once opened its section by writing its own heading
as the whole file and destroyed the coordinator's entries.

One record, minimally:

```json
{"run": "<iso8601>", "task_ref": "#1116", "dispatcher_selected": ["sdlc-python-specialist"],
 "artifacts_touched": ["python/"], "under_selected": [], "over_selected": [],
 "gate": "pytest tests/", "rc": 0, "rounds": 1}
```

## Approval: the loop PROPOSES, a human APPLIES

**No agent edits its own definition.** That is self-modifying config with no
review gate, and it cuts against this repo's whole reviewed-diff posture.

The precedent to copy is `pwf-scribe`, which may not write `task_plan.md` and
instead writes a **separate delta file** the coordinator reads and applies
(`.claude/rules/agent-report-persistence.md`). Same shape here: the loop writes
`.agent/plans/sdlc-tuning-delta-<stamp>.md` naming the agent, the signal that
triggered it, the current `developer_instructions` text and the proposed text. A
human applies it as a normal reviewed diff.

That also keeps the `#:schema` guarantee intact: a proposal that would produce an
invalid agent file fails `taplo` at commit time like any other edit.

## What would make this real, in order

1. **S2 only, reporting only.** Compute under/over-select from the diff and print
   it. No storage, no proposals. Cheapest possible thing that tells you whether
   routing is actually accurate over more than the two runs measured so far.
2. **Add the tracked JSONL.** Once S2 has said something interesting more than
   once.
3. **Add S1/S3.** Gate rc and round count per specialist.
4. **Add the proposal writer.** Only after the data shows a *pattern* — a single
   bad run is noise, and `.claude/rules/probes-need-a-control-arm.md` rule 6 warns
   that a difference smaller than same-input variance is not a difference.

⚠️ **Do not start at step 4.** A proposal generator fed by two data points will
confidently rewrite instructions on noise.

## What this design does NOT claim

- It is not self-healing. Nothing here repairs a failed run; it records that one
  happened and proposes an instruction change a human may apply.
- It is not autonomous. Every change to an agent passes through a reviewed diff.
- It is unvalidated. No part of this has been run. The two dispatcher runs in the
  parent spec are evidence that **routing works**, not that measuring routing
  accuracy over time produces a useful signal.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the gates, agents, and telemetry paths named above.
