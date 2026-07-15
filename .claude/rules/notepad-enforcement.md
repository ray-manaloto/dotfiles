# Notepad Enforcement: Agents Must Record Findings

All agents performing research, debugging, or multi-step analysis MUST write
findings to the notepad immediately — not at session end.

## The notepad is a file, not a tool

The notepad is **`.omc/notepad.md`** (gitignored). Write to it with the ordinary
Write/Edit tools, appending as you go.

Until 2026-07-15 this rule named
`mcp__plugin_oh-my-claudecode_t__notepad_write_working` / `..._write_priority`.
Those tools ship with the `oh-my-claudecode` plugin, which is **disabled** — so
they are absent from every session, and a `/doctor` scan measured **zero
invocations across 941 transcripts**. The rule was unfollowable as written; the
notepad file itself stayed current because sessions wrote it by hand. Naming the
real mechanism is the fix. If OMC is ever re-enabled, its notepad tools write
this same file — the rule does not change.

## Rules

1. **Write findings as you go**: After each significant discovery, append it to
   `.omc/notepad.md`. Mark critical items so they survive a skim.

2. **What to record**: Root causes found, design decisions made, dead ends
   explored, verification results, and any context the next agent will need.

3. **Never batch findings**: Do not accumulate findings in memory and write
   them all at session end. Each finding should be persisted within the same
   step it was discovered.

4. **Research agents especially**: Any multi-file analysis or research sweep
   MUST write intermediate findings before proceeding to the next file or step.

## Why

In the 2026-04-05 session, the python-pro agent and debugger team performed
extensive analysis but did NOT write to notepad. When context was lost, their
findings had to be re-derived. This policy prevents that waste.

## Verification

After an agent completes work, check `.omc/notepad.md` for findings. If it is
empty or stale relative to the work performed, the agent did not comply.

## See also

- `.claude/rules/agent-report-persistence.md` — the full-fidelity layer; this
  rule covers the running condensed findings.
- `.claude/rules/omc-directory-conventions.md` — where each artifact type lives.
