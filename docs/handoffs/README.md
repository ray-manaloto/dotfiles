# Cross-Surface Session Handoffs

Claude Code sessions are **surface-local and non-portable** — the web app,
desktop app, and CLI each keep their own conversation history, and there is no
built-in cross-device resume (confirmed against the official Claude Code docs,
2026-07-10). The canonical way to continue work on a different surface is
therefore: **commit the state to the branch + leave a handoff doc, then check
out the branch on the other surface and read it.**

This directory holds those handoff docs. Unlike `.omc/plans/session-*.md`
(which `/clear-prep` writes — gitignored, this-clone-only, for same-machine
`/clear`), these are **tracked and pushed**, so they survive `git pull` on
another machine.

## The two-command protocol

**Ending a session (any surface):**
```
/handoff "the next task in one line"
```
Writes `docs/handoffs/session-<date>.md`, syncs docs, runs the gates, commits,
and pushes.

**Starting on another surface:**
```bash
git fetch && git checkout <branch> && git pull
```
then, in Claude Code:
```
/resume docs/handoffs/session-<date>.md      # or just /resume for the newest
```
Pulls, reads the handoff, restates the plan, and continues.

## Which handoff mechanism to use

| Situation | Use | Lands in |
|---|---|---|
| `/clear` and keep going on the **same machine** | `/clear-prep` | `.omc/plans/` (gitignored) |
| Continue on a **different surface** (web ↔ desktop ↔ CLI) | `/handoff` → `/resume` | `docs/handoffs/` (tracked) |

They share the same doc-sync + validation discipline; only the destination and
the push differ.

## Handoff template

Each `session-<YYYY-MM-DD>[-letter].md` should be self-sufficient (the resume
line only points here):

```markdown
# Session handoff — <YYYY-MM-DD>

## State at handoff
- Branch: `<branch>` · PR: #<n> (<draft/open>) · HEAD: `<sha>`
- Gates: lint <rc> · pytest <rc> · verify <rc> (real rc/conclusion, not a tail)
- Autonomous processes in flight (do NOT wait on): <Renovate PRs / GHA runs>

## What shipped this session
- `<sha>` — <what it did>
- ...

## Next task
<one-line task>. Preload: <plan/spec/issue/PR links + exact file paths>.

## Open decisions (awaiting the user)
1. <question> — recommendation: <...>

## Gotchas
- <non-obvious trap the next session must know>

## Resume
`/resume docs/handoffs/session-<date>.md`
```

## Why not something more automated?

There is no built-in web↔desktop session transfer to lean on — `--resume`/
`--continue` read per-machine local transcripts only, and Remote Control is a
live tunnel to a *running* local session, not a persisted handoff. The
git-branch-plus-handoff pattern here is exactly what the official docs
recommend; `/handoff` + `/resume` just package it into one command each way.

The one remaining manual dependency is the **web "brick"**: a cold Claude-web
session has no Python ≥3.14, so its PreToolUse guard fails closed and blocks
Bash/git — which is why a web session must push via the GitHub API instead of
`git`. Fixing that (see `docs/web-brick-fix-handoff.md`) makes `/handoff` run
under normal git on every surface.
