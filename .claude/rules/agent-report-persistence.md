# Agent Report Persistence: Verbatim, At Receipt

Every findings-bearing subagent report—research, review, audit, verification,
decisions, evidence tables, or probe output—MUST be persisted verbatim when it
is received. Do not reduce it to a notepad summary or defer it to session end.

## Why this rule exists

Case history: `docs/rules-evidence/agent-report-persistence.md`.

## Native carriage

`.claude/settings.json` carries this contract on two hooks, and **neither costs
a model turn**:

- an **unscoped `SubagentStart`** hook injects the incremental-persistence and
  file-role contract before every delegate's first prompt. With no matcher it
  cannot filter by agent type, so a new built-in, custom or plugin delegate is
  covered the day it appears.
- a **`PostToolUse` hook scoped to the `Agent` tool** reminds the *coordinator*
  to persist at receipt, right after a delegate returns — which is where rule 1
  puts that duty anyway.

⚠️ **There is deliberately NO `SubagentStop` hook. Adding one is a regression.**

`hook_selfcheck` binds all of this: `check_unscoped_events` fails a narrowed
`SubagentStart` matcher, the `PostToolUse` row fails a matcher widened off
`Agent`, every clause of the injected contract is a required token, and the
end-to-end check **forbids** the `decision` channel on every arm — because
`block` and `additionalContext` both keep a delegate running, so nothing
presence-shaped can tell them apart.

`SubagentStart` is advisory and fails silently: its stderr appears only in the
subagent transcript. Therefore `_SETTINGS_WIRING` in
`python/src/dotfiles_setup/hook_selfcheck.py` and its present/deleted
registration tests are load-bearing. The required substrings must remain in
one settings entry; splitting the contract across entries fails selfcheck.

## Rules

1. **Persist at receipt, into the tracked destination.** Write a final report
   verbatim to `docs/research/kb/reports/agents/<agent-name>.md` in the same
   turn, before acting on it. Put fetched raw sources in
   `.agent/kb/raw/<slug>.md`. The notification's `<output-file>` is the subagent
   transcript; the report is its LAST non-blank assistant text block.

   > **ONE path.** `docs/research/kb/` is tracked and clone-durable. Existing
   > artifacts stay where they are; new findings-bearing reports go there.

2. **Persist incrementally.** A research delegate writes each source as it is
   fetched and creates its report early, updating it as work proceeds. An
   agent that fails after 13 of 20 sources should leave 13 recoverable sources,
   not zero. Deliver the report before going idle.

3. **Respect file roles.** The start hook supplies this table to every
   delegate; briefs may add narrower ownership but may not weaken it.

   | Content | File | Who writes |
   |---|---|---|
   | Phases, checkboxes, current phase, distilled decisions | `task_plan.md` | **coordinator ONLY** |
   | Research, analysis, evidence, technical findings | `findings.md` | anyone, **append-only** |
   | Chronological outcomes, actions, errors, test results | `progress.md` | anyone, **append-only** |

   **No delegate writes `task_plan.md`, and there is no exception.** A scribe
   such as `pwf-scribe` proposes a change by writing a SEPARATE file —
   `.agent/plans/task_plan-delta-<stamp>.md`, naming the old anchor and the
   proposed text — which the coordinator reads and applies. Routing the
   proposal to its own path is what keeps the invariant machine-assertable:
   "coordinator only" stays a statement about one file, not a permission an
   agent definition can claim for itself. Codex lanes remain mechanically
   isolated with `PLANNING_DISABLED=1` in `codex_lane.LANE_ENV_OVERRIDES`.

   ⚠️ **"anyone writes" means anyone APPENDS.** Both files are shared with the
   coordinator and every other lane, both are gitignored, and neither has an
   undo. The
   `SubagentStart` contract now states append-only explicitly, and that clause
   is a required token of the end-to-end check.

4. **Verbatim means verbatim.** Preserve tables, evidence links, probes, and
   repos-touched enumeration. Add decision annotations afterwards; do not trim
   the source report.
5. **Notepad entries are additive.** `findings.md` carries the condensed,
   active-session record; the tracked report carries full fidelity.
6. **Mechanical agents are exempt.** A delegate whose entire value is an
   immediately visible file effect needs no report. When in doubt, persist.
7. **Audit the native roster at handoff.** Read the session's
   `subagents/` roster under the native project session directory. Map every
   findings-bearing launch to its brief and tracked report, or record an
   explicit N/A before producing the resume prompt.

Native transcripts make a missed delivery **recoverable** through
`agent_transcript_path`, but still untracked and vulnerable to cleanup. That is
a recovery route, not compliance and not a replacement for the tracked report.

## Applies to

All Agent-tool delegations in this repository, regardless of the skill or
workflow that launched them.

## See also

- `.claude/rules/notepad-enforcement.md` — condensed as-you-go findings.
- `.claude/rules/research-repo-enumeration.md` — report provenance.
- `.claude/rules/agent-artifact-conventions.md` — durable locations.
- `.claude/skills/session-handoff/SKILL.md` — coverage audit.
- `python/src/dotfiles_setup/hook_selfcheck.py` — hook output and wiring gate.
