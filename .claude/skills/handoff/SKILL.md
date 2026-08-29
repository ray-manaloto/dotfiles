---
name: handoff
description: "Write a CROSS-SURFACE session handoff to a tracked path and push it, so a session on another surface (web, desktop, or CLI) can continue with zero context loss. Use when ending a session whose work must be picked up on a DIFFERENT machine/surface. For same-machine /clear continuity use /session-handoff instead. Invoke as /handoff [next-task]."
disable-model-invocation: true
argument-hint: "[one-line description of the next task, optional]"
---

# Handoff — Cross-Surface Session Handoff

Claude Code sessions do NOT transfer across surfaces: the web app, desktop
app, and CLI each keep their own local history, and there is no built-in
cross-device resume (confirmed against the official docs). The only state that
crosses the boundary is what you **commit to the branch**. `/session-handoff` writes
its handoff to `.agent/plans/`, which is gitignored and this-clone-only — perfect
for a same-machine `/clear`, useless for web->desktop. This skill writes the
handoff to a **tracked** path and pushes it, so the next surface just pulls.

`$ARGUMENTS` (optional) is the next task; if empty, infer it from the open PR /
plan and state your guess explicitly.

## Steps

### 1. Do the doc-sync + validation discipline from `/session-handoff`
Follow `.claude/skills/session-handoff/SKILL.md` steps 1-4 (snapshot state; update
every doc your changes touched; run the relevant gates — `mise run lint`,
pytest, `dotfiles-setup verify run` — all green). Do NOT duplicate that logic
here; this skill only changes WHERE the handoff lives and that it is pushed.

### 2. Write the tracked handoff
Write `docs/handoffs/session-{YYYY-MM-DD}[-letter].md` (append a letter if one
exists for today). It must be **self-sufficient** — the resume line only points
here. Fill the template in `docs/handoffs/README.md`:
- **State at handoff** — branch, PR #, HEAD sha, CI/gate results (real `rc` /
  API `conclusion`, never a piped tail).
- **What shipped** — commits + what each did.
- **Next task** — `$ARGUMENTS` or your stated inference, with preload pointers
  (plan/spec/issue/PR links, exact file paths).
- **Open decisions** — anything awaiting the user, with your recommendation.
- **Gotchas** — non-obvious traps, in-flight autonomous processes (Renovate
  PRs, running GHA) that the next session should inventory not wait on.

### 3. Self-verify the handoff
Every path it cites exists; every `file:line` is real; every `mise run {task}`
it names exists (`mise tasks ls`); gate results match the recorded `rc`. A
wrong detail costs the next session more than a missing one.

### 4. Commit + push (this is the cross-surface part)
Stage the handoff and the doc updates from step 1 (specific paths — never
`git add .`; `.claude/rules/do-not.md`). Commit + push per
`.claude/skills/git-branch-commit-push-workflow/SKILL.md` (plain git,
`git push -u origin {branch}`). Unlike `/session-handoff`, the handoff IS committed,
because a tracked-but-unpushed handoff still can't cross surfaces.

> **Bricked web session caveat:** if Bash/git is blocked (the Claude-web
> "brick" — see `docs/web-brick-fix-handoff.md`), push the handoff via the
> GitHub MCP API (`push_files`) instead. If even that is unavailable, send the
> handoff file to the user directly (SendUserFile) as a hedge and say so.

### 5. Emit the resume line for the OTHER surface
Print exactly (single line the user pastes on the receiving surface after
`git pull`):

```text
/resume docs/handoffs/session-{date}.md
```

Then one line: *"On your other machine: `git fetch && git checkout {branch} &&
git pull`, open Claude Code in the repo, paste that."*

## Checklist

- [ ] `/session-handoff` steps 1-4 done: docs synced, relevant gates green.
- [ ] Handoff written to `docs/handoffs/session-{date}.md` (TRACKED), self-sufficient.
- [ ] Handoff self-verified (paths, file:line, task names, gate rcs).
- [ ] Handoff + doc updates committed AND pushed (or API-pushed if git is bricked).
- [ ] Resume line printed for the receiving surface.

## See also

- `.claude/skills/resume/SKILL.md` — the receiving side.
- `.claude/skills/session-handoff/SKILL.md` — same-machine `/clear` handoff (`.agent/plans/`).
- `docs/handoffs/README.md` — the protocol + the handoff template.
- `.claude/skills/git-branch-commit-push-workflow/SKILL.md` — the commit/push path.
