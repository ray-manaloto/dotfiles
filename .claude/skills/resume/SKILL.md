---
name: resume
description: "Resume work on a DIFFERENT surface (web <-> desktop <-> CLI) from a tracked cross-surface handoff written by /handoff. Pulls the branch, reads the latest docs/handoffs/session-*.md, restates the plan, and continues. Invoke as /resume [handoff-file]."
disable-model-invocation: true
argument-hint: "[path to a specific handoff file, optional]"
---

# Resume — Continue From a Cross-Surface Handoff

The receiving side of `/handoff`. Reconstructs working context on a fresh
surface from the tracked handoff on the branch (Claude Code has no built-in
cross-device session resume — the branch is the only carrier). `$ARGUMENTS`
(optional) is a specific handoff file; if empty, use the most recent one.

## Steps

### 1. Sync the branch
Get the latest branch state so the handoff and the files it references are
present locally:

```bash
git fetch origin
git checkout <branch>          # the branch named in the handoff / PR
git pull --ff-only
```

If you don't yet know the branch, list recent handoffs after a plain
`git fetch` and pick the newest, or ask the user which PR/branch to resume.

### 2. Find and read the handoff
Use `$ARGUMENTS` if given; else pick the newest
`docs/handoffs/session-*.md` (latest date, then latest letter suffix). **Read
it in full** — it is designed to be self-sufficient. Also open the preload
pointers it names (plan/spec/issue/PR) so you load the real working set, not
just the summary.

### 3. Restate the plan back to the user (3-6 lines)
Before doing any work, confirm you reconstructed context correctly: state the
branch/PR, what shipped, the next task, and any OPEN DECISIONS the handoff
flagged as awaiting the user. This catches a stale or wrong handoff before it
costs you.

### 4. Confirm the branch is green (if the handoff claims it is)
If the handoff reports gates green, and you are on a surface where the gates
run (desktop/CLI with the toolchain — NOT a bricked web session), optionally
re-confirm before building on top:

```bash
mise run lint
uv run --project python pytest tests/ -x -q
dotfiles-setup verify run
```

Trust the real `rc`/`conclusion`, never a piped tail
(`.claude/rules/verify-before-advancing.md`).

### 5. Continue
Proceed with the next task from the handoff. If it was ambiguous, resolve it
with the user (`AskUserQuestion`) before acting
(`.claude/rules/clarify-before-acting.md`).

## Checklist

- [ ] Branch fetched + checked out + pulled; handoff + referenced files present.
- [ ] Latest (or specified) `docs/handoffs/session-*.md` read in full + preload pointers opened.
- [ ] Plan/PR/next-task/open-decisions restated to the user for confirmation.
- [ ] Branch green re-confirmed where the gates can run.
- [ ] Next task under way (or ambiguity resolved with the user first).

## See also

- `.claude/skills/handoff/SKILL.md` — the sending side.
- `docs/handoffs/README.md` — the protocol + template.
- `.claude/rules/verify-before-advancing.md` — trust the artifact, not a tail.
