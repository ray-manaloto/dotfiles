# Agent Artifact Conventions: Where Working Files Go

Agent working artifacts live under **`.agent/`** (gitignored, machine-local).
Anything that must survive a clone is tracked under `docs/`. Do not create
ad-hoc directories in either tree.

> **Renamed from `.omc/` (2026-07-25).** That name belonged to a plugin that
> was not enabled. `.agent/` was control-armed before adoption; archaeology is
> in `docs/rules-evidence/agent-artifact-conventions.md`.

## Two plan locations, two durability contracts

- Claude Code harness plans stay at the documented default
  `~/.claude/plans`. They survive repository cleanup and sessions.
- `.agent/plans/` contains **our** handoffs and grilling outcomes, such as
  `session-{date}[-letter].md`. It is swept by `git clean -xdf`.

Do **not** set project `plansDirectory` to `.agent/plans`. Although the setting
is native, doing so would move harness-owned plans into the disposable tree and
reduce durability.

## Local, gitignored — swept by `git clean -xdf`

| Path | Purpose |
|---|---|
| `.agent/state/` | General and per-session state |
| `.agent/notepad.md` | Session-review's narrative notepad corpus |
| `.agent/plans/` | Our handoffs and grilling outcomes |
| `.agent/logs/` | Execution logs and pipeline traces |
| `.agent/command-audit.md` | SessionEnd one-off-command report |
| `.agent/kb/raw/` | Raw fetched sources backing a report |
| `.agent/kb/structured/` | Structured local extraction artifacts |
| `.agent/instructions-loaded/` | InstructionsLoaded observer state |
| `.agent/session-review/` | Session-review outputs |
| `.agent/telemetry/` | Local telemetry artifacts |

Claude Code's native local memory uses
`.claude/agent-memory-local/<agent-name>/` for agents with `memory: local`; it
is not `.agent/project-memory.json`. A-1 deliberately enables that scope for
`cold-reviewer`, `graphify-researcher`, and `spec-scribe`. `memory: project`
uses `.claude/agent-memory/<agent-name>/` and is version-controlled; `user`
uses `~/.claude/agent-memory/<agent-name>/`.

Native project/session state may also appear under `.claude/projects/`,
including task output, tool results, transcripts, and the session's
`subagents/` roster. Treat those as harness state, not authored report paths.

## Tracked, durable — survives a clone

| Path | Purpose |
|---|---|
| `docs/specs/` | Design specs and interview output |
| `docs/research/runs/` | Existing research-run artifacts |
| `docs/research/kb/raw/` | Promoted raw sources cited by durable docs |
| `docs/research/kb/reports/agents/` | New verbatim findings-bearing reports |
| `docs/handoffs/` | Cross-surface handoffs |
| `docs/adr/` | Product/domain decisions |
| `docs/rules-evidence/` | One evidence sibling per eager rule |

**Promote anything a rule, eval, or later session will cite.** The migration
found eager rules citing machine-local research, leaving every other clone with
a dead link. A citation that only one machine can open is not durable evidence.

## Worktrees and agent isolation

A subagent definition may set `isolation: worktree`, creating a temporary
worktree for that delegate. It sees the repository, plus untracked files named
by `.worktreeinclude`; it does not inherit arbitrary machine-local artifacts.
Place required inputs in tracked paths or explicitly include them. Never infer
that worktree cleanup promoted a report—it only removed the isolated worktree.

## Rules

1. **No ad-hoc directories.** Map each artifact to the closest declared path.
2. **A handoff is our plan artifact:** `.agent/plans/session-{date}.md`.
3. **Active findings use root `findings.md`** through the enabled
   planning-with-files plugin; `.agent/notepad.md` remains the session-review
   corpus. See `notepad-enforcement.md`.
4. **Specs go in `docs/specs/`.** Reports go in the tracked report tree.
5. **Skills use native loader locations.** Project skills live at
   `.claude/skills/<name>/SKILL.md`; personal skills at
   `~/.claude/skills/<name>/SKILL.md`; plugin skills come from enabled plugins;
   and skills in directories supplied by `--add-dir` are also discovered.
   Nested project skill directories are supported. Do not claim the loader
   scans arbitrary `.agent/` paths.
6. **Keep listing pressure visible.** The skill listing has its own character
   budget — every skill NAME always appears, but descriptions are shortened,
   and on overflow dropped least-used-first, which can strip the keywords
   Claude matches on (`$CC/skills.md:1050-1058`). It scales at 1% of the
   context window. Inspect `/context` (its Skills row reports the listing
   AFTER the budget is applied) and `/doctor`; treat
   `SLASH_COMMAND_TOOL_CHAR_BUDGET` as a diagnostic/user setting, not a project
   workaround. Never rely on every installed skill being listed.

   ⚠️ Earlier wording here claimed this budget is *shared with MCP tools*. The
   corpus does not say that: `$CC/env-vars.md:466` scopes it to "skill metadata
   shown to the Skill tool", and `$CC/skills.md:1050-1058` describes a
   skill-listing budget throughout. Corrected rather than re-anchored.
7. **Build reusable skills downward:** skill → mise task → Python library. The
   skill contains judgment; the task is the seam; mechanics are parameterized
   library functions. No bash logic. Author through the skill creator and
   writing-for-agents workflows rather than copying a stale template.
8. **Do not normalize records.** Verbatim reports and ingested source corpora
   preserve what was observed. Fix authored pointers, not archived evidence.

Native anchors re-read 2026-09-09: plan defaults at
`$CC/settings-reference.md:2709-2721`; skill locations and discovery at
`$CC/skills.md:111-175`, listing composition at `$CC/skills.md:337-338`, and
listing pressure at `$CC/skills.md:1050-1058`; memory scopes at
`$CC/sub-agents.md:563-598`; worktrees at `$CC/sub-agents.md:269-305` and
`$CC/worktrees.md:179-189`; native state at
`$CC/claude-directory.md:1493-1527`.

## Why this rule cannot be `paths:`-scoped

It is creation-triggered: it must govern the destination before a file exists.
A scoped version would be absent at the decision point, so it remains eager.

## Applies to

All agent-generated working, planning, memory, research, and handoff artifacts
for this repository.

## See also

- `.claude/rules/agent-report-persistence.md` — full-fidelity reports.
- `.claude/rules/notepad-enforcement.md` — live findings carriage.
- `.claude/rules/md-size-budgets.md` — eager/scoped load classes.
- `docs/rules-evidence/agent-artifact-conventions.md` — probes and rejected
  `plansDirectory` adoption.
