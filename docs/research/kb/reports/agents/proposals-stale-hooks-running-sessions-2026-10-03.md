# Proposals — stale hooks in running sessions (2026-10-03)

Read-only review (no source edited, no /reload-plugins run, no session touched). Report written incrementally.

## Evidence log (incremental)

- E1 `.claude/skills/session-start/hooks/register.ts:221-224` — on `session.start` (interactive) the mod already queues
  `/reload-skills` then `/reload-plugins --force` via `$.command.run` when python's decide says `reload: true` (once per session id).
- E2 live arms report arm A (`docs/research/kb/reports/agents/live-arms-coordinator-auto-handoff-2026-10-02.md`): a module-queued
  `/reload-plugins --force` really ran ("Prompt from the session-start plugin", `Reloaded: 17 plugins · 87 skills · 33 agents · 15 hooks`)
  => a hooks module CAN trigger a reload of itself (positive arm measured on 2.1.288).
- E3 coordinator-handoff mod heartbeat strings: `handoff N%/30%`, `handoff fired @N%`, `handoff n/a (not coordinator)`, `handoff ERROR:` (register.ts header + belowStatus).
