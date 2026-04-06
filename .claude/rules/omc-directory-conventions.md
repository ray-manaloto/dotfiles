# OMC Directory Conventions: Use Standard Paths

All OMC artifacts must go in the correct `.omc/` subdirectory. Do not create
ad-hoc directories under `.omc/`. The standard structure is:

| Path | Purpose | Examples |
|------|---------|---------|
| `.omc/state/` | General state files | Active mode tracking, session IDs |
| `.omc/state/sessions/{id}/` | Per-session state | Deep-interview state, trace state |
| `.omc/notepad.md` | Working notepad | Agent findings, intermediate notes |
| `.omc/project-memory.json` | Project memory | Cross-session project knowledge |
| `.omc/plans/` | Plans and handoffs | Session resume plans, ralplan output, consensus plans |
| `.omc/specs/` | Specs from deep-dive/interview | `deep-dive-{slug}.md`, `deep-dive-trace-{slug}.md` |
| `.omc/research/` | Research artifacts | External context findings, doc lookups |
| `.omc/skills/` | Learned project skills | Expertise and workflow skill files |
| `.omc/logs/` | Execution logs | Agent run logs, pipeline traces |

## Rules

1. **No ad-hoc directories**: Do not create `.omc/handoffs/`, `.omc/temp/`, `.omc/output/`,
   or any directory not listed above. Map your artifact to the closest standard path.

2. **Session handoffs go in plans/**: A handoff is a "what to do next" document — that's a plan.
   Name convention: `session-{date}.md` or `session-{date}-{letter}.md`.

3. **Agent findings go in notepad**: Not in memory, not in standalone files. Use the notepad
   MCP tools (`notepad_write_working`, `notepad_write_priority`).

4. **Specs from deep-dive/interview go in specs/**: Not in plans, not in research.

5. **Learned skills go in skills/**: Not in plans, not in research. Use the learner skill format.
