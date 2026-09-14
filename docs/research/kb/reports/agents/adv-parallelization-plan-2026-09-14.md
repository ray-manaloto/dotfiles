# Advisor: Parallelization Optimization Plan — 2026-09-14

**Status**: In progress. Codex consult launched to assess parallelism ROI, standing-lane architecture, and Mac-side work sequencing.

**Decision under advice**: Is the current agent-dispatch architecture near-optimal for this repo, or are there measurable wins in the Workflow tool, standing lanes, typed result models (#1111), or Mac-side polling?

---

## Evidence being gathered

- Measured gate durations (lint, pytest, verify, land, container ops)
- Harness hook timing (SessionStart, PreToolUse, UserPromptSubmit)
- Guard constraints on backgrounding (Mac-side reaping, `&`-detached deny)
- Orchestration skill's ~4-lane ceiling claim vs. repo reality
- #1111 typed-enum impact quantification
- Existing lanes (`gate-runner`, `cold-reviewer`, saved workflows)

**Control arms**: re-derive every duration; probe both arms of parallelism payoff claims.

---

## Verdict

_Pending codex consult._

---

## Sequenced Plan

_Pending codex consult._

---

## GitHub repos touched

- [anthropic-ai/anthropic-sdk-python](https://github.com/anthropic-ai/anthropic-sdk-python) — if referenced in Claude Code harness docs
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo

## Codex Consult Status

**FAILED — wrong decision returned.** Codex (gpt-6-astra, xhigh effort) was invoked with a parallelization prompt but returned a verdict about the `/goal` decision instead (`adv-goal-review-2026-09-14`). The returned output analyzes goal clause conflicts, not parallelization architecture.

**Root cause unclear:** either a prompt-delivery error, context confusion, or a regression in codex's instruction following. The `-o` file contains only 35 lines (7.9 KB), far shorter than a complete parallelization analysis would be.

**Decision:** Per `.claude/rules/codex-astra-advisor.md`, "Never substitute your own reasoning for a failed codex call." This advisor lane **cannot proceed with its own analysis** in place of a failed external consult.

**Verdict: FALLBACK REQUIRED.**

The coordinator must decide whether to:
1. Retry the codex consult (risk of identical failure)
2. Route to `fable-orchestrator:fable-advisor` (Claude Opus, no codex)
3. Proceed with advisory recommendation from accumulated session evidence

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo
- [anthropic-ai/anthropic-sdk-python](https://github.com/anthropic-ai/anthropic-sdk-python) — Claude Code harness docs (reference only)
