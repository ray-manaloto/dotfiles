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

1. Queue a known `/rename` BEFORE `/reload-skills`, then `/reload-plugins --force`:
   a bg spare's skills/plugins can predate the claim. Record `renamed` and show
   success after `/rename` resolves and Python confirms the job record's name
   when one exists (foreground: resolution suffices). Rejection or a mismatched
   job name leaves naming pending.
2. Name the session `<project>-<yyyyMMdd'T'HHmmss.SSSSSSSSSX>.<feature>`
   (America/Chicago; `dotfiles` here, `kb` in the knowledge-base):

| Answer | When | What the hook does |
|---|---|---|
| `keep` | the `-n` name already conforms | nothing |
| `rename` | no `-n` name, off the default branch | `/rename` with the branch slug (`feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/` stripped, `/` → `-`) |
| `defer` | no `-n` name, on the default branch | at the first prompt, `/rename` with a ≤5-word model slug (fallback `session`), then `session-start renamed` |
| `nonconforming` | a `-n` name outside the convention | never renames — lanes are addressed by name; status + toast |
| `unknown` | no trusted job record and a bg spare (or unreadable argv) | never renames; status `session-start: name unknown` |

A changed-module reload can re-fire `session.start`; `already-ran` queues no
reload. The first `prompt.submit` also reads
`session-start pending --session-id <id>` once after a reload to recover the persisted prefix, even when start did
not re-fire. Failed pending reads get at most three attempts per session in a
module lifetime, then one terminal ERROR; reload the module to retry. Rejected
naming stays pending; confirmed naming clears it.

## Reading the status line

- `session-start ok`
- `session-start ok (renamed)`
- `session-start ok (name at first prompt)`
- `session-start pending rename`
- `session-start: name unknown`
- `session-start: name not in convention`
- `session-start ERROR: <reason>`

Function-hook failures are otherwise silent, so a missing entry means the hook
did not run.

A user name comes from a matching bg job record with `nameSource: "user"`, or
`-n`/`--name` in the nearest harness process's argv (reap/session-orphans).
Harness-generated job names do not count. Missing spare records fail closed;
foreground argv without `-n` can follow branch/prompt naming. The hook handles
both string and `{isAnswered, text}` completion results; vendor types need a
separate coordinator-owned refresh from 2.1.277 to the running 2.1.288.
