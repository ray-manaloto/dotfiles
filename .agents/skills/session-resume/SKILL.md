---
name: session-resume
description: "Pick up where the last dotfiles session stopped: reconcile the local handoff and authoritative task plan with real git and PR state, then report disagreements, the active plan phase, owed work, and traps. Use this first after /clear or whenever the user says resume, catch me up, where were we, or what is active."
argument-hint: "[optional: a specific handoff path, or a nudge like 'just the traps']"
---

# Session Resume — Reconcile After `/clear`

`/session-handoff` writes a local handoff. This skill reads it and checks its
claims against the repo instead of taking them on faith.

`$ARGUMENTS` can name a specific handoff or narrow the report with a nudge such
as *"just the traps"* or *"only what's owed"*. Empty is the normal full
reconciliation.

This differs from `.agents/skills/resume/SKILL.md`: `resume` is cross-surface
and fetches tracked `docs/handoffs/session-*.md`; this skill is same-clone,
post-`/clear`, and reads gitignored `.agent/plans/session-*.md` files.

## Process

### 1. Find and read the handoff

Apply `$ARGUMENTS` before choosing a file:

- When it contains `/` or ends in `.md`, treat it as the exact handoff path.
  Read that file in full. If it does not exist, report that and stop; the newest
  handoff is not a substitute for a named one.
- Otherwise, treat non-empty arguments as a report nudge, then select the
  newest `.agent/plans/session-*.md` by date and letter suffix.
- With empty arguments, select that same newest handoff and read it in full.

`.agent/` is gitignored. A fresh clone can have no handoff, which is different
from "no work pending." Say that plainly, then orient from these tracked/live
sources instead of inventing a directive. If `task_plan.md` is also absent,
say task authority is unavailable; issues and commits are context, not a
substitute plan:

The tracked plan pointer is a same-clone continuity check; a fresh clone cannot
verify its digest because `task_plan.md` is gitignored.

```bash
git log --oneline -8
gh issue list --state open --limit 10
```

### 2. Read the real state

Run the read-only snapshot:

```bash
mise run session-state
```

A failed GitHub lookup is `UNVERIFIABLE`, never `none`.

When the handoff makes citation-heavy claims, also run:

```bash
mise run handoff-check
```

With a specifically named handoff, pass the same path after `--`.
`handoff-check` verifies paths, line ranges, mise task names, absence of a
second task carrier, the active-plan shape, and the tracked plan pointer; it
does not prove the handoff covered every non-task obligation.

### 3. Reconcile and report disagreements first

Compare the handoff with the snapshot and checker. Lead with every
contradiction: branch or SHA drift, a PR whose live state differs, dirty paths
the handoff omitted, or a stale citation.

Read the active phase heading directly from `task_plan.md`; never recover task
selection from handoff prose. Quote the handoff's traps and preserve issue
numbers and explicit owed non-task work. If everything agrees, say so in one
line.

Use this tight shape:

```text
On <branch> at <sha> — clean|N uncommitted. <PR state.>

DISAGREEMENT: <only when one exists>

PLAN: task_plan.md → <active phase heading>

OWED: <short list with issue numbers>

TRAPS: <the ones that can bite now, quoted>
```

When `$ARGUMENTS` is a nudge, print the header plus only the requested section.
`DISAGREEMENT` remains mandatory whenever reality contradicts the handoff.

### 4. Offer to begin the active phase

Ask whether to begin the active plan phase without copying its task text into
another carrier. Orientation is the whole action here; the user may have
arrived with a different priority.

## What this does not do

It does not write, commit, or ship. It does not update the handoff;
`/session-handoff` owns the sending half.

It also does not certify coverage. `handoff-check` can validate every citation
while the handoff still omits an item, so reconcile important owed lists with
the prior handoff when completeness matters.

## See also

- `.agents/skills/session-handoff/SKILL.md` — write the same-clone handoff before `/clear`.
- `.agents/skills/resume/SKILL.md` — resume a tracked handoff on another surface.
- `.claude/rules/agent-artifact-conventions.md` — local versus tracked handoff storage.
