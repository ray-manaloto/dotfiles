# Antigravity lab evidence and delivery — 2026-10-12

This collection preserves 21 session reports captured October 10–11, 2026.
The nine full/brief pairs and three comparison/status reports were promoted
byte for byte. Their dates, observations, limitations and research failures
remain part of the evidence.

## Report index

| Research lane | Complete report | Brief |
| --- | --- | --- |
| antigravity-lab: offline | [Full](agents/antigravity-lab-offline-20261011.md) | [Brief](agents/antigravity-lab-offline-20261011-brief.md) |
| antigravity-lab: runtime | [Full](agents/antigravity-lab-runtime-20261011.md) | [Brief](agents/antigravity-lab-runtime-20261011-brief.md) |
| antigravity-lab: verifier | [Full](agents/antigravity-lab-verifier-20261011.md) | [Brief](agents/antigravity-lab-verifier-20261011-brief.md) |
| antigravity-takeover: history | [Full](agents/antigravity-takeover-history-20261011.md) | [Brief](agents/antigravity-takeover-history-20261011-brief.md) |
| antigravity-takeover: repo | [Full](agents/antigravity-takeover-repo-20261011.md) | [Brief](agents/antigravity-takeover-repo-20261011-brief.md) |
| antigravity-takeover: verifier | [Full](agents/antigravity-takeover-verifier-20261011.md) | [Brief](agents/antigravity-takeover-verifier-20261011-brief.md) |
| lab-otel: history | [Full](agents/lab-otel-history-20261011.md) | [Brief](agents/lab-otel-history-20261011-brief.md) |
| lab-otel: logs | [Full](agents/lab-otel-logs-20261011.md) | [Brief](agents/lab-otel-logs-20261011-brief.md) |
| lab-otel: verifier | [Full](agents/lab-otel-verifier-20261011.md) | [Brief](agents/lab-otel-verifier-20261011-brief.md) |

- [Native lab status and history](antigravity-lab-status-history-20261011.md).
- [Telemetry versus AgentsView](agents/telemetry-versus-agentsview-20261011.md).
- [AgentsView project examples](agents/agentsview-project-examples-2026-10-10.md).

The status reports are captured observations. They do not establish current
execution, imported archive coverage, or successful delivery of every item
discussed in the Antigravity work ledger.

## Subsequent local delivery

On October 12, the lab history reader landed on local `main` as
`c5abc9f1b7d8866cf8201ea279225c602133fe4a`. Its audit and handoff documents
landed separately as `79fa8e9f5061dcb8510f31e163c348c9793b671c`.
The lab repository has no configured remote; these are local deliveries.

The maintained checkout is
`test.results.20260929.worktrees/antigravity-session-history` beside the
original lab folder. Its canonical
`.agents/skills/antigravity-session-history/SKILL.md` is the installed Codex
skill target. The tracked receipt is
`docs/reports/07-session-history-delivery-20261012.md`.

Both lab deliveries passed the full 276-test project suite and bounded full
hk gate. Native commit hooks, fast-forward merges and feature-branch
retirement exited 0. Each landed offline doctor reported 16 passes with zero
warnings and failures. The documentation delivery also passed OKF validation.

The reader supplies native Antigravity history, supported AgentsView reads,
and telemetry evidence with explicit coverage and missingness. W1's broader
harvester/backfill/synthesis work, W2–W7, and the seven telemetry findings
retain their existing acceptance criteria. The original dirty continuation
checkout was preserved.

## Research coverage

Historical reports retain `RESEARCH INCOMPLETE` where Context7 exhausted its
quota, GitHub Discussions lacked a verified control, or Firecrawl used a
provisional fallback. Publishing those reports does not complete those audits.

A separate October 12 delivery-fix fanout ran through native fnox profile
`codex_research` and the maintained strict-five task. It exited 0 with Exa,
Context7, Firecrawl Developer and Last30Days results, and controlled GitHub
results. Firecrawl Search still returned HTTP 402 before provisional Serper
fallback; the Git hook mirror used provisional webclaw. That newer receipt
does not replace the earlier reports' research scope or failures.

The lab's tracked delivery receipt records the executed tools and source
checks. Raw execution receipts remain local under the existing `.agent/`
artifact conventions.
