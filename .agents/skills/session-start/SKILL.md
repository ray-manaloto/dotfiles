---
name: session-start
description: "The session-start mod: on each new interactive session it reloads skills and plugins and names the session <project>-<Chicago ISO ns>.<feature>. Reference for what the hook did and how to read its status line; it runs by itself."
disable-model-invocation: true
---

# session-start — reload and name every new session

`.agents/skills/session-start/hooks/register.ts` fires on `session.start` in interactive sessions (bg
included; `-p` and the SDK skip). Python decides, once per session id —
`mise run session-start -- decide --session-id <id> --cwd <dir>`, state in
`.agent/state/session-start/<id>.json`, written before it answers. Spec:
`docs/specs/coordinator-auto-handoff-2026-10-02.md` §8.

1. Queue `/reload-skills`, then `/reload-plugins --force`: a bg session is a
   pre-started spare whose skill and plugin state can predate the claim.
2. Name the session `<project>-<yyyyMMdd'T'HHmmss.SSSSSSSSSX>.<feature>`
   (America/Chicago; `dotfiles` here, `kb` in the knowledge-base):

| Answer | When | What the hook does |
|---|---|---|
| `keep` | the `-n` name already conforms | nothing |
| `rename` | no `-n` name, off the default branch | `/rename` with the branch slug (`feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/` stripped, `/` → `-`) |
| `defer` | no `-n` name, on the default branch | at the first prompt, `/rename` with a ≤5-word model slug (fallback `session`), then `session-start renamed` |
| `nonconforming` | a `-n` name outside the convention | never renames — lanes are addressed by name; status + toast |

A reload re-fires `session.start`; the second answer is `already-ran`, which
queues nothing and carries a still-pending `defer` prefix.

## Reading the status line

- `session-start ok`
- `session-start ok (renamed)`
- `session-start ok (name at first prompt)`
- `session-start: name not in convention`
- `session-start ERROR: <reason>`

Function-hook failures are otherwise silent, so a missing entry means the hook
did not run.

The `-n` name is read from the bg job record (`~/.claude/jobs/<id8>/state.json`);
a foreground `claude -n` session has no record, so it is treated as unnamed.
