# Agent Report Persistence: Verbatim, At Receipt

Every **findings-bearing** subagent report — research, review, audit,
verification, or any report carrying findings, decisions, evidence tables,
or probe output — MUST be persisted **verbatim** to disk at the moment it
is received, not summarized into the notepad and not deferred to session
end.

## Why this rule exists

Session 2026-07-05: an 11-agent release-notes sweep produced 13 detailed
reports (syntax sketches, file:line misconfiguration tables, probe
transcripts, a backend status matrix). The notepad got condensed summaries
as the work progressed, but the full reports existed **only in the
session's context window** — one `/clear` away from being lost. A manual
round-2 pass recovered them; this rule makes that recovery unnecessary.

Condensation is lossy in exactly the way that hurts later: the summary
keeps the conclusion but drops the evidence, the exact command lines, and
the file:line anchors the implementing session needs.

## Rules

1. **Persist at receipt.** When a findings-bearing agent's final report
   arrives, write it verbatim to
   `.omc/research/<topic>/agents/<agent-name>.md` (or the artifact
   directory of the active research effort) in the SAME turn — before
   acting on its content.
2. **Verbatim means verbatim.** Keep the agent's tables, evidence links,
   probe output, and repos-touched enumeration intact. Annotating
   decisions inline afterwards (e.g. "DECIDED: option A") is encouraged;
   trimming evidence is not.
3. **Notepad entries are additive, not substitutes.** The notepad gets the
   running condensed finding (per `notepad-enforcement.md`); the artifact
   file holds the full report. Both, every time.
4. **Mechanical agents are exempt.** A delegation whose entire value is
   its immediate effect (a fan-out grep, a file-move helper) needs no
   artifact; its outcome is visible in the caller's next action. When in
   doubt, persist.
5. **Clear-prep audits coverage.** The `/clear-prep` skill enumerates the
   session's agent launches and requires each findings-bearing one to map
   to an on-disk artifact (or an explicit N/A note in the handoff) before
   the resume prompt is printed.

## Applies to

All Agent-tool delegations in this repo — research sweeps, adversarial
verification passes, code-review agents, audit agents — regardless of
which skill or workflow launched them.

## See also

- `.claude/rules/notepad-enforcement.md` — the sibling rule for condensed
  as-you-go findings; this rule covers the full-fidelity layer.
- `.claude/rules/research-repo-enumeration.md` — every persisted report
  ends with its repos-touched enumeration.
- `.claude/rules/omc-directory-conventions.md` — `.omc/research/` is the
  standard home for research artifacts.
- `.claude/skills/clear-prep/SKILL.md` — the coverage audit gate.
