---
name: research-with-verification-gap-fill
description: "Use when parallel research lanes will feed a load-bearing recommendation: follow them with one independent verification pass that re-probes the claims the recommendation hinges on and names the questions no lane answered."
---

# Research with a verification gap-fill

Parallel lanes each answer their own question, so their findings can be
individually correct, mutually consistent, and still leave unasked the
question the recommendation depends on. One independent verification pass
after the fan-out catches that; in the run this skill came from it halved the
scope of the recommended change.

## Shape

- **Lanes.** Split the goal into independent questions. Give each lane its
  question and the probes you expect it to run, and ask for findings with
  evidence and confidence. Route lanes per the `codex-sdlc-team` skill's
  routing doctrine (research is a read-only `Explore`/`Agent` lane).
- **Verifier.** After every lane returns, hand ONE verifier that did not do the
  research the verbatim findings, the original goal, and the claims the
  recommendation hinges on. Ask it for: contradictions between lanes; an
  independent re-probe of each load-bearing claim, not a re-read of the lanes'
  citations; the questions the recommendation needs that no lane answered;
  and the smallest correct recommendation given the verified evidence.
- **Persist.** Briefs and reports go verbatim under
  `docs/research/kb/reports/agents/` at receipt
  (`.claude/rules/agent-report-persistence.md`). The synthesized report
  carries the verifier's reconciled recommendation, not the lanes' raw output.

## When not to use it

A simple lookup, an answer already in the codebase or git history, or a cheap
reversible decision where the verification pass costs more than being wrong.

## See also

- `docs/research/runs/research-20260407-ssh-devcontainer/report.md` — the run this came from.
- `.claude/rules/probes-need-a-control-arm.md` — re-probe with both arms.
