# Brief — handoff-automation research lane (Ray ruling 2026-10-03 ~14:10, via watcher 998ab91b)

Report BY NAME to the newest dotfiles coordinator (ListAgents recency; currently
dotfiles-20261003T140808.926861000-05.coordinator). Keep your own state file at
`<your worktree>/.agent/kb/raw/lanes/handoff-automation.md` (the main-checkout inbox is NOT writable from a worktree).

## Question
How does EVERY session — coordinator, watcher, fan-out lanes — run /session-handoff unattended, and how do its
changes get applied and merged to main so all other sessions pick them up, with ZERO human intervention?

## Hard requirements
- Run the research-sweep-run saved workflow (current main) FIRST, before designing anything (use-tool-builtins):
  best practices + existing solutions (Claude Code native features, plugins, issues/discussions, other projects).
- Persist incrementally: raw sources to .agent/kb/raw/, report early at
  docs/research/kb/reports/agents/session-handoff-automation-research-2026-10-03.md, updated as you go; end with
  `## GitHub repos touched`.
- RESEARCH ONLY: no implementation, no ship, no gates beyond what the workflow runs. Commit the report on your branch
  `research/session-handoff-automation`; the coordinator ships it.

## Inputs
- .agent/kb/raw/watcher-handoff-plan-2026-10-03.md (+ addendum: unattended /session-handoff for watchers AND every lane)
- #1583 role-check gap: only coordinators get the unattended handoff; observed live: llvm-23-bump lane status bar shows
  "coordinator-handoff: handoff ERROR: decide rc 2" and "session-start ERROR: pending rename failed … reload to retry".
- docs/research/kb/reports/agents/event-driven-self-healing-agent-orchestration-2026-10-03.md (launchd KeepAlive
  supervisor, reload-proof settings-hook producer)
- Observed cadence: 4 coordinator auto-handoffs today, ~every 20-60 min at 30% context.
- Lane-G gap: worktree-isolated lanes cannot write the main-checkout fallback inbox (.agent/plans/handoff-inbox/).
- Prior art: .claude/skills/coordinator-handoff/SKILL.md, python/src/dotfiles_setup/ coordinator_handoff*, #1609 (revival).

## Deliverable
Recommendation with options (PRO/CON, citations), the native mechanism(s) to adopt, what custom code survives and why,
and a proposed seven-part spec outline for the coordinator to ratify.
