# Notepad Enforcement: Agents Must Record Findings

All agents performing research, debugging, or multi-step analysis MUST write
findings to the notepad immediately — not at session end.

## Rules

1. **Write findings as you go**: After each significant discovery, write to
   notepad via `mcp__plugin_oh-my-claudecode_t__notepad_write_working` or
   `mcp__plugin_oh-my-claudecode_t__notepad_write_priority` for critical items.

2. **What to record**: Root causes found, design decisions made, dead ends
   explored, verification results, and any context the next agent will need.

3. **Never batch findings**: Do not accumulate findings in memory and write
   them all at session end. Each finding should be persisted within the same
   step it was discovered.

4. **Research agents especially**: Agents running `/deepinit`, `/ai-slop-cleaner`,
   `/self-improve`, or any multi-file analysis MUST write intermediate findings
   to notepad before proceeding to the next file or step.

## Why

In the 2026-04-05 session, the python-pro agent and debugger team performed
extensive analysis but did NOT write to notepad. When context was lost, their
findings had to be re-derived. This policy prevents that waste.

## Verification

After an agent completes work, check notepad for findings. If the notepad is
empty or stale relative to the work performed, the agent did not comply.
