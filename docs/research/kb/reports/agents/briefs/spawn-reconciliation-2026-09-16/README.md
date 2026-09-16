# Briefs — spawn reconciliation (task_plan.md 6c P0, issue #1142 decision 2), 2026-09-16

The questions that produced the reports in `../../*spawn*2026-09-16.md`,
`../../premise-verifier-spawn-2026-09-16.md`, `../../cold-review-22bee5a-2026-09-16.md`,
`../../codex-review-301472a-2026-09-16.md`, `../../fable-advisor-spawn-reconciliation-2026-09-16.md`
and `../../sdlc-live-settlement-probe-2026-09-16.md` (agent-report-persistence.md rule 1: briefs are in
scope because reports without their briefs are unreproducible).

| artifact | what it is |
|---|---|
| `spec-v1-as-first-verified.md` | the first seven-part spec sent to the premise-verifier |
| `spec-v5.md` | the ratified spec the first implementer lane received (v2–v5 corrections marked inline) |
| `spec-v7-respec.md` | respec round 1 after the cold review of `22bee5a` (nine confirmed findings; v6→v7 corrections marked) |
| `spec-v8-addendum.md` | the arm-11 rule clarification + inherited-tree description given to the Opus fallback lane |
| `live-settlement-review-spec.md`, `live-settlement-request.json` | the review-mode `mise run sdlc-team` request that produced the first live settlement |
| `codex-lane-preambles.md` | the dispatch preambles of the three direct codex launches (lanes 2, 3, 4) |
| `agent-prompts.md` | the prompts handed to the verifier, reviewers, advisor, gate-runner and the Opus lane |

Chronology and outcomes: `docs/research/kb/reports/agents/codex-sol-implementer-spawn-reconciliation-2026-09-16.md`
(lane history) and the session memory `project_session_2026-09-16.md` (session b).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under change; every brief targets its `python/src/dotfiles_setup/sdlc_team.py` and `lane_result.py`.
- [openai/codex](https://github.com/openai/codex) — rollout record shape, `CODEX_HOME`, and the exec banner, read from the offline codex docs corpus and from local session files; not fetched live.
