# Agent Report Persistence: Verbatim, At Receipt

Every **findings-bearing** subagent report — research, review, audit,
verification, or any report carrying findings, decisions, evidence tables,
or probe output — MUST be persisted **verbatim** to disk at the moment it
is received, not summarized into the notepad and not deferred to session
end.

## Why this rule exists

Session 2026-07-05: an 11-agent sweep produced 13 detailed reports that
existed **only in the session's context window** — one `/clear` from
being lost. A manual round-2 pass recovered them.

Condensation is lossy in exactly the way that hurts later: the summary
keeps the conclusion but drops the evidence, the exact command lines, and
the file:line anchors the implementing session needs. Three incidents:
`docs/rules-evidence/agent-report-persistence.md`.

## Rules

1. **Persist at receipt, into `docs/research/kb/`.** When a findings-bearing agent's
   final report arrives, write it verbatim to
   `docs/research/kb/reports/agents/<agent-name>.md` in the SAME turn — before acting on
   its content. Sources the agent fetched go to `.agent/kb/raw/<slug>.md`.

   > **ONE path.** `docs/research/kb/` is tracked and survives a fresh clone;
   > the old `docs/research/runs/<topic>/agents/` does not. Existing artifacts
   > stay where they are; new ones go to `docs/research/kb/`.

1b. **Instruct agents to persist INCREMENTALLY, not at the end.** Tell a
   research delegation to write each source as it fetches it, and to write its
   report early and update it. Two agents that held everything in memory died
   silently after ~40 minutes and left **nothing**. An agent that dies having
   written 13 of 20 sources leaves 13; one planning to write at the end leaves
   0. Durable capture must be incremental, never end-of-run.

   ⚠️ **A rule nothing pushes into the prompt is not a layer.** On 2026-08-03 this
   requirement went into **none of four briefs**, two agents died and left nothing,
   and the one survivor persisted on its own initiative. Put it in the **agent
   definition** — `.claude/agents/staleness-auditor.md` carries it, so it rides
   every delegation instead of being remembered per-brief — and add one line to any
   ad-hoc brief. Pair it with **deliver before idle**: an agent that *finished* and
   went idle without sending its report was a total loss in the same run.
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
   **both its brief and its report** to an on-disk artifact (or an explicit
   N/A note in the handoff) before the resume prompt is printed.

## Applies to

All Agent-tool delegations in this repo — research sweeps, adversarial
verification passes, code-review agents, audit agents — regardless of
which skill or workflow launched them.

## See also

- `.claude/rules/notepad-enforcement.md` — the sibling rule for condensed
  as-you-go findings; this rule covers the full-fidelity layer.
- `.claude/rules/research-repo-enumeration.md` — every persisted report
  ends with its repos-touched enumeration.
- `.claude/rules/agent-artifact-conventions.md` — `docs/research/runs/` is the
  standard home for research artifacts.
- `.claude/skills/clear-prep/SKILL.md` — the coverage audit gate.
