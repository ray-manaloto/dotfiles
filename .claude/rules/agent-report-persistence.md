# Agent Report Persistence: Verbatim, At Receipt

Every findings-bearing subagent report—research, review, audit, verification,
decisions, evidence tables, or probe output—MUST be persisted verbatim when it
is received. Do not reduce it to a notepad summary or defer it to session end.

## Why this rule exists

On 2026-07-05, an 11-agent sweep produced 13 detailed reports that existed only
in context. On 2026-08-03, two agents died after about 40 minutes with nothing
written because incremental persistence was omitted from all four briefs. The
conclusion may survive condensation; exact commands, evidence, and file:line
anchors do not.

## Native carriage

`.claude/settings.json` registers unscoped `SubagentStart` and `SubagentStop`
hooks. The start hook injects the incremental-persistence and file-role
contract before every delegate's first prompt. With no matcher, it cannot
accidentally filter by agent type. The stop hook returns a deliver-before-idle
reminder once; recursive stop events pass so the hook cannot loop forever.

⚠️ **The stop reminder uses `additionalContext`, never `decision: "block"`.**
Both keep the delegate running under the same loop protections, but `block`
renders as a hook *error*, and a codex lane that had already delivered read
that as an objection and re-explained its compliance three times before it
could idle (#994). `additionalContext` is the documented channel for a hook
"working as designed and giving Claude guidance" and shows as plain `Stop hook
feedback` (`$CC/hooks.md:2549`; SubagentStop accepts it per `:2346`). A
reminder that reads as an accusation costs a turn and teaches the lane to argue.

`stop_hook_active` guards recursion within **one** continuation chain, not
across parent messages: a long-lived named agent pays this reminder once per
message it receives, not once per session.

`SubagentStart` is advisory and fails silently: its stderr appears only in the
subagent transcript. Therefore `_SETTINGS_WIRING` in
`python/src/dotfiles_setup/hook_selfcheck.py` and its present/deleted
registration tests are load-bearing. The required substrings must remain in
one settings entry; splitting the contract across entries fails selfcheck.

`SubagentStop` additional context reaches the **delegate**, not the
coordinator. Parent-side injection would require a `PostToolUse` hook on the
`Agent` tool, which this change does not add. The coordinator must still
persist a delivered report at receipt.

## Rules

1. **Persist at receipt, into the tracked destination.** Write a final report
   verbatim to `docs/research/kb/reports/agents/<agent-name>.md` in the same
   turn, before acting on it. Put fetched raw sources in
   `.agent/kb/raw/<slug>.md`.

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
   | Phases, checkboxes, current phase, distilled decisions | `task_plan.md` | **coordinator ONLY by default**; an agent whose definition explicitly emits a `DELTA` may propose one for the coordinator to apply |
   | Research, analysis, evidence, technical findings | `findings.md` | anyone |
   | Chronological outcomes, actions, errors, test results | `progress.md` | anyone |

   A delegate does not directly mutate `task_plan.md`; a designated scribe such
   as `pwf-scribe` emits a `DELTA`, and the coordinator applies it. Codex lanes
   remain mechanically isolated with `PLANNING_DISABLED=1` in
   `codex_lane.LANE_ENV_OVERRIDES`.

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

Native anchors re-read 2026-09-09: `hooks.md:314`, `:870`, `:888`,
`:2304-2317`, and `:2319-2346`; transcript paths at
`$CC/sub-agents.md:1051-1057`. Probe detail is in
`docs/rules-evidence/agent-report-persistence.md`.

## Applies to

All Agent-tool delegations in this repository, regardless of the skill or
workflow that launched them.

## See also

- `.claude/rules/notepad-enforcement.md` — condensed as-you-go findings.
- `.claude/rules/research-repo-enumeration.md` — report provenance.
- `.claude/rules/agent-artifact-conventions.md` — durable locations.
- `.claude/skills/session-handoff/SKILL.md` — coverage audit.
- `python/src/dotfiles_setup/hook_selfcheck.py` — hook output and wiring gate.
