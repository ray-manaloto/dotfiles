---
name: session-resume
description: "Pick up where the last dotfiles session stopped: find the local handoff, compare it with the real git and PR state, and report disagreements, the exact next task, owed work, and traps. Use this as the first action after /clear or in a fresh same-clone session, and whenever the user says resume, catch me up, where were we, what was I doing, or what is next."
argument-hint: "[optional: a specific handoff path, or a nudge like 'just the traps']"
---

# Session Resume — Reconcile After `/clear`

`/session-handoff` writes a local handoff. This skill reads it and checks its
claims against the repo instead of taking them on faith.

`$ARGUMENTS` can name a specific handoff or narrow the report with a nudge such
as *"just the traps"* or *"only what's owed"*. Empty is the normal full
reconciliation.

This differs from `.claude/skills/resume/SKILL.md`: `resume` is cross-surface
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
sources instead of inventing a directive:

```bash
git log --oneline -8
gh issue list --state open --limit 10
```

### 2. Read the real state

Run the read-only snapshot:

```bash
mise run session-state
```

A failed GitHub lookup is `UNVERIFIABLE`, never `none`. To copy a branch, SHA,
PR number, or any other figure from the output, run the direct command instead:

```bash
uv run --project python dotfiles-setup session-state
```

Mise output redaction can mask digit runs, so task output is suitable for
reading but not for copying exact figures.

When the handoff makes citation-heavy claims, also run:

```bash
mise run handoff-check
```

With a specifically named handoff, pass the same path after `--`.
`handoff-check` verifies paths, line ranges, and mise task names; it does not
prove the handoff covered every obligation.

### 3. Reconcile and report disagreements first

Compare the handoff with the snapshot and checker. Lead with every
contradiction: branch or SHA drift, a PR whose live state differs, dirty paths
the handoff omitted, or a stale citation.

Quote the handoff's own wording for the next task and traps. Preserve issue
numbers and explicit owed work. If everything agrees, say so in one line.

Use this tight shape:

```text
On <branch> at <sha> — clean|N uncommitted. <PR state.>

DISAGREEMENT: <only when one exists>

NEXT: <the next task, quoted>

OWED: <short list with issue numbers>

TRAPS: <the ones that can bite now, quoted>
```

When `$ARGUMENTS` is a nudge, print the header plus only the requested section.
`DISAGREEMENT` remains mandatory whenever reality contradicts the handoff.

### 4. Offer the next step

End by naming the next task and asking whether to start it. Orientation is the
whole action here; the user may have arrived with a different priority.

## What this does not do

It does not write, commit, or ship. It does not update the handoff;
`/session-handoff` owns the sending half.

It also does not certify coverage. `handoff-check` can validate every citation
while the handoff still omits an item, so reconcile important owed lists with
the prior handoff when completeness matters.

## See also

- `.claude/skills/session-handoff/SKILL.md` — write the same-clone handoff before `/clear`.
- `.claude/skills/resume/SKILL.md` — resume a tracked handoff on another surface.
- `.claude/rules/agent-artifact-conventions.md` — local versus tracked handoff storage.
