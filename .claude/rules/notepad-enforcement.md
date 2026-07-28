# Notepad Enforcement: Agents Must Record Findings

All agents performing research, debugging, or multi-step analysis MUST write
findings to the notepad immediately — not at session end.

## The notepad is a file, not a tool

The notepad is **`.agent/notepad.md`** (gitignored). Write to it with the ordinary
Write/Edit tools, appending as you go.

Do **not** reach for the `oh-my-claudecode` notepad MCP tools this rule used to
name: that plugin is disabled, so they are absent from every session (measured:
**0 invocations across 941 transcripts**). A rule naming a mechanism nobody can
invoke is indistinguishable from no rule at all.
Detail: `docs/rules-evidence/notepad-enforcement.md`.

## Rules

1. **Write findings as you go**: After each significant discovery, append it to
   `.agent/notepad.md`. Mark critical items so they survive a skim.

2. **What to record**: Root causes found, design decisions made, dead ends
   explored, verification results, and any context the next agent will need.

3. **Never batch findings**: Do not accumulate findings in memory and write
   them all at session end. Each finding should be persisted within the same
   step it was discovered.

4. **Research agents especially**: Any multi-file analysis or research sweep
   MUST write intermediate findings before proceeding to the next file or step.

## Why

2026-04-05: agents performed extensive analysis but did NOT write to the
notepad. When context was lost, every finding had to be re-derived.

**Verification:** after an agent completes work, check `.agent/notepad.md`. Empty
or stale relative to the work performed means it did not comply.

## See also

- `.claude/rules/agent-report-persistence.md` — the full-fidelity layer; this
  rule covers the running condensed findings.
- `.claude/rules/agent-artifact-conventions.md` — where each artifact type lives.
