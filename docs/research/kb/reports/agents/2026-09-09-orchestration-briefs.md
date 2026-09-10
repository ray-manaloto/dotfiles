# Briefs handed to agents — session dotfiles-20260909.001 (2026-09-09/10)

Per `.claude/rules/agent-report-persistence.md` rule 5: every findings-bearing agent's BRIEF and REPORT on disk. Reports: `pr-briefs-2026-09-09.md`, `premises-A1-2026-09-09.md`, `premises-A2-2026-09-09.md`, `cold-review-241737d-2026-09-09.md` (this directory); the audit report + TOML under `docs/research/kb/reports/`; the codex lanes' dispatch content is the spec files under `docs/specs/orchestration-pr-a-2026-09-09/` plus the control lines quoted below.

## pr-briefs (general-purpose, opus) — distil the audit's scheduling into PR briefs
Read-only distillation of `## Scheduling proposal` and `## Rule refactors proposed` in `docs/research/kb/reports/modernization-audit-2026-09-09.md` under the rulings in `.agent/plans/grilling-2026-09-09.md`, writing `docs/research/kb/reports/agents/pr-briefs-2026-09-09.md` with sections: PR A in-scope by theme (agent frontmatter / workflows / tasks-hk-suites / roster-blocking rules / skills twins), PR A deferred (one-liners with reason), PR B in-scope (only the pipefail-aware exit-code-masking class and its carriers) and deferred, PR C (16 findings), rule refactors PR A must ship (change + motivating defect per rule), counts table, GitHub repos touched. Target 6–10 KB, hard max 14 KB (delivered 20.1 KB; accepted — the overflow was the per-rule motivating defects the critic replay needs). Write early, update as you go; cite finding ids exactly; invent nothing.

## premises-A1 (fable-orchestrator:premise-verifier) — verify spec A-1
Cold verification of `spec-A1.md` (now `docs/specs/orchestration-pr-a-2026-09-09/spec-A1.md`): every PREMISES row against the files, then hunt unlisted premises (agnix accepting the frontmatter keys, `maxTurns`/`effort`/`skills`/`memory` honoured at the installed Claude Code, workflow `agentType` resolving project agents, `mise exec -- node`, the STEP 0 string in `modernization-audit.js`). Return per-row verdicts + MISSING list; never edit. Result: 13/15 CONFIRMED, A1 REFUTED, 17 missing premises — see `premises-A1-2026-09-09.md`.

## codex-A1 (fable-orchestrator:codex-implementer) — implement spec A-1
Dispatch text: `SPEC FILE: <scratchpad>/spec-A1.md`, `EFFORT: xhigh`, `TIMEOUT: 3600`, `PREMISES-VERIFIED: <scratchpad>/premises-A1-report.md`, then the spec's `## 7. PREMISES` block restated verbatim. Follow-up rulings sent mid-run: relocate the temporary "Until Claude tokens reset…" paragraph of `.claude/CLAUDE.md` into `.claude/token-routing.md` via `@import` (agnix CC-MEM-009 strict), keep every `orchestration.*`-contract-bound line in place, re-run lint-docs/lint/verify/pytest/parity, one lane commit. Result: commit `241737d1`.

## cold-review-A1 (general-purpose, opus, effort high) — cold review of 241737d1 by ref
Review the DIFF ONLY of `241737d1c001cec3c6247fed7ff8b01da7abe608` against its parent with no description of intent; read-only probes allowed (lint-docs, single-file pytest, `mise exec -- bun run`, doctor, KB docs); look for frontmatter keys/values the harness rejects or that contradict each other, lost trigger keywords, unreachable workflow control flow (nulls, stage arity, unknown agentType, meta/phase mismatches, Date/Math.random), prompts that paraphrase what must pass verbatim, a python port that changed behaviour vs its tests and the saved TOML, tests that pass for the wrong reason, definition-bound contract tokens, a raised doctor ceiling whose justification mismatches the measurement, unaccounted file edits. Findings as severity + claim + file:line + verification; write `cold-review-241737d-2026-09-09.md` incrementally. Result: 0 CRITICAL / 4 MAJOR / 7 MINOR / 5 NIT.

## gate-smoke and gate-smoke-arm (gate-runner, new roster) — real-invocation evidence
Run `mise run lint-docs` and `mise run verify` (pass arm), then `sh -c 'echo …; exit 3'` and `sh -c 'echo ok'` (fail arm), each captured as `<cmd> > <log> 2>&1; echo "rc=$?" >> <log>` under the scratchpad; report command / rc read from the log / log path / first failing step; fix nothing. Results: rc 0 / 0 and rc 3 / 0 — the role discriminates.

## premises-A2 (fable-orchestrator:premise-verifier) — verify spec A-2
Cold verification of `spec-A2.md` at `241737d1`: every PREMISES row, then the unlisted ones (`plansDirectory` documented at the installed version, `SubagentStop`/`SubagentStart` + `additionalContext` semantics, `askUserQuestionTimeout`, what `hook_selfcheck._SETTINGS_WIRING` asserts, the report subsection anchors, existing `docs/rules-evidence/` notes, the six rules' sizes vs the 24,000-byte budget). Result in 4 parts: 9/9 L rows CONFIRMED (4 anchors drifted), A2 CONFIRMED with a durability cost, one premise REFUTED (md-size-budgets.md is scoped → :95 row), M1–M12 — see `premises-A2-2026-09-09.md`.

## codex-A2 (fable-orchestrator:codex-implementer) — implement spec A-2
Dispatch text: `SPEC FILE: <scratchpad>/spec-A2.md`, `EFFORT: xhigh`, `TIMEOUT: 3600`, `PREMISES-VERIFIED: <scratchpad>/premises-A2-report.md`, then the spec's `## 7. PREMISES` block restated verbatim (the copy in `docs/specs/orchestration-pr-a-2026-09-09/spec-A2.md` is the file as dispatched).

## Workflow runs (modernization-audit) — not agents, but the briefs live in the script
`.claude/workflows/modernization-audit.js` carries every stage prompt (gap fetch, finder per unit kind, three verifier lenses, synthesis, critic). Runs: `wf_8311dfc3-94e` (run 1 + failed resume), `wf_04b74e6a-c86` (run 2), `wf_8f33f02d-f7d` (run 3 + round-4 resume). Args: `.agent/kb/audit/args.json`, `.agent/kb/audit/args-run3.json`.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited repo; issues #993–#1000
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline doc corpus; issue #734
