---
name: session-review
description: Find what a session did BY HAND that should have become a skill, mise task or python module, via `mise run session-review`. Use at the end of a working session, during `/clear-prep` or handoff writing, when a task felt like a slog and you want to know whether it was one, or when deciding what automation to build next. Two disjoint lanes — a transcript mine for recurring command shapes and a narrative pass over the notepad and handoff for reasoning sinks that leave no repeated command. Run it before writing the handoff, while the session's own notes are still in front of you.
user-invocable: true
---

# session-review: what should have been code

```bash
mise run session-review                                   # both lanes
mise run session-review -- --output .agent/session-review.md
mise run session-review -- --narrative-only               # cheap re-check
mise run session-review -- --sessions 6                   # narrow the mine
```

`python/src/dotfiles_setup/session_review.py` does the collecting. The report
is evidence plus a template; **the judgement is yours**, and the sections below
are the judgement worth having.

## The two lanes find different things, so read both

**Lane 1 — recurring command shapes**, ranked by how many distinct **sessions**
a shape appears in rather than by raw frequency. Twenty uses inside one session
is one grind someone worked through; three uses across three sessions is a
workflow, and only the second keeps costing.

**Lane 2 — passages in your own notes** that read like manual work.

Neither subsumes the other. #650 — regenerating the image locks, the best find
of the review this tool came from — was ~15 turns of reading CI config,
transcribing a recipe, running it on the wrong platform, measuring the damage
and re-running in a container. **There was no repeated one-liner to count.**
Frequency is a proxy for cost and a poor one; the expensive thing was reasoning.

The converse is why lane 1 stays on: you do not reliably remember every one-off
you ran, and the transcript does.

## The gate: name the cost, or it is not a candidate

This inherits #608's objection — *prose was not the lever* — so apply #607's
test to everything the report surfaces:

> **What concrete cost would this have avoided?**

A wrong-platform run. A re-derivation. A spurious red gate. A near-committed
corruption. If the answer is "it would be nicer", you have a preference, not a
candidate. The report's template puts that line in the middle of the write-up
so it cannot be skipped.

Worth stating plainly: the four candidates that came out of the manual review
this replaces all had one, and it is why they were worth building.

## What the report is bounded by

Both lanes are windowed, and the report says so on its first line — a
bound-limited search that does not declare its bound reads as complete.

- **Lane 1** scans the most recent sessions' transcripts. The count printed is
  **transcript files**, which includes every nested subagent transcript, so it
  is much larger than the session count you asked for.
- **Lane 2** reads the **tail** of `.agent/notepad.md` and only the **newest**
  handoff. The notepad accumulates across every session this repo has had; an
  unbounded scan answers "what has this repo ever done by hand" and buries the
  session you are reviewing under its own history.

Widen either with `--sessions` or by pointing the library at different files.

## Lane 2 surfaces, it does not judge

A regex cannot tell an expensive slog from a sentence describing one, so read
the passage before believing the row. Two filters already run, both derived
from real output rather than guessed:

- Shell constructs and harness mechanics are dropped from lane 1 — `while [`,
  `for i`, scratchpad `mkdir -p`, the in-turn poll loop. The poll loop is
  *mandated* by `long-running-command-hangs.md` rule 2, so ranking it would put
  a required behaviour at the top of a list of things to stop doing.
- Instructions **not** to do something by hand are dropped from lane 2. A
  handoff saying "do NOT re-derive this" is the previous session having already
  paid, which is the opposite of a finding.

If a filter is hiding something real, widen it in a reviewed diff and say what
it missed — that is cheaper than reading a report nobody trusts.

## Then write it up

One candidate per issue, in the shape #650–#653 use: what was done by hand, the
cost avoided, and the proposed `skill → mise task → python library` triple
(`agent-artifact-conventions.md` rule 6). Reusable **by parameter** — this
repo's case is the default of a parameterised function, never hard-coded.
