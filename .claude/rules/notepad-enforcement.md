# Notepad Enforcement: Persist Findings While They Are Fresh

Agents doing research, debugging, or multi-step analysis MUST persist each
significant finding in the step that discovers it. Do not wait for session end.

## The active notepad is planning-with-files

The enabled planning-with-files plugin uses root `findings.md` for discoveries.
Its SessionStart hook re-injects the planning files on startup, resume,
`/clear`, and `/compact`, so the working record survives context turnover.
`.agent/notepad.md` remains the separate narrative corpus consumed by this
repository's session-review tooling; it is not the active findings queue.

For subagents, `.claude/settings.json` carries the rule through unscoped
`SubagentStart` and `SubagentStop` hooks. The start hook injects incremental
persistence before work begins; the stop hook reminds the delegate to deliver
before idle. A stop hook speaks to the delegate, not the coordinator, so the
parent still persists the received full report under the report-persistence
rule.

## Rules

1. **Write as you go.** After each root cause, decision, dead end, probe, or
   verification result, update `findings.md` before the next investigative
   step.
2. **Do not batch.** Context held only in a transcript or model memory is a
   recovery source, not the working record.
3. **Research delegates persist incrementally.** Write fetched sources and the
   report early; keep both current throughout the sweep.
4. **Read-only delegates report through the parent.** If filesystem tools are
   absent, return the finding immediately with its evidence so the coordinator
   can persist it. Never pretend a denied write succeeded.
5. **Account for skipped project instructions.** Built-in `Explore` and `Plan`
   subagents do not load project `CLAUDE.md`; the start hook is therefore the
   native carriage for this contract.
6. **Memory supplements files.** A-1 gives `memory: local` to
   `cold-reviewer`, `graphify-researcher`, and `spec-scribe`. Those memories can
   preserve agent-specific lessons, but do not replace `findings.md` or the
   tracked verbatim report.

The former guidance named `oh-my-claudecode` notepad MCP tools. That plugin was
disabled and those tools recorded zero invocations across 941 transcripts.
They are removed only because the enabled plugin, root file, hooks, and
read-only fallback now provide an observable replacement.

## Why

On 2026-04-05, extensive findings were not written down and all had to be
re-derived after context loss. The root file plus re-injection protects the
coordinator's condensed state; incremental source/report writes and subagent
hooks protect delegated work.

Native anchors re-read 2026-09-09: built-in instruction skipping at
`$CC/sub-agents.md:33`; start/stop behavior at `$CC/hooks.md:2283-2346`;
memory scopes at `$CC/sub-agents.md:563-598`; `/context` and compaction
behavior at `$CC/memory.md:421-462`. The plugin hooks and injection script were
also read from the enabled planning-with-files 3.17.2 installation.

## Applies to

All research, debugging, review, and multi-step analysis in the main session
and every delegated agent.

## See also

- `.claude/rules/agent-report-persistence.md` — tracked full-fidelity reports.
- `.claude/rules/agent-artifact-conventions.md` — location and durability.
- `docs/rules-evidence/notepad-enforcement.md` — probes and archaeology.
