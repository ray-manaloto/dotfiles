# Feature Review: Astra Predecessor Comparison
**Date:** 2026-09-21  
**Reviewers:** codex-astra-advisor (this lane, read-only)  
**Scope:** claudex-loop 2.1.0 vs fable-orchestrator 1.21.0 vs our current sdlc-team  
**Goal:** Decide feature-by-feature what our version should take from predecessors

---

## Executive Summary

Three distinct orchestration patterns observed:

1. **claudex-loop** (chaseai-yt): Cross-provider skill-based workflows (Claude ↔ Codex) with structured plan/review cycles, round budgets, fresh sessions for cross-family review.
2. **fable-orchestrator** (plugin): Architect-as-orchestrator with three heavyweight phases (advisor consult → premise verification → typed-dispatch implementation), CLI-wrapping lanes, premise-first spec contract.
3. **Our sdlc-team**: Lightweight typed dispatch (spec → six specialists → settlement), detached launch + reap, basic report format.

Our version is **minimal and functional**; predecessors provide **depth in different directions** (claudex-loop on workflow rigor, fable-orchestrator on spec validation). The feature matrix below identifies what each does well and what we're missing.

---

## Feature Matrix (29 rows)

| Feature | Source | What it does | We have it? (file:line) | Ruling | Why | Cost/Risk |
|---------|--------|------------|---------|--------|-----|-----------|
| **PREMISES block validation** | fable-orch `codex-implementer.md:34-42` | Preflight gate: spec must carry `PREMISES` heading; abort before launch if missing | **NO** | **MIGRATE** | #1202 & premise-verification show this is load-bearing; every spec reaching codex must state its facts | Medium: add block/attestation checks at `sdlc_team.py` preflight |
| **PREMISES-VERIFIED attestation** | fable-orch `codex-implementer.md:42` | Gate: if spec has E-row (emission) or SECURITY marker, must carry `PREMISES-VERIFIED: <path>` line to premise-verifier's report | **NO** | **MIGRATE** | premise verification must complete before implementation; attestation path proves it ran | Medium: add attestation gate like PREMISES block |
| **Premise-verifier agent** | fable-orch `premise-verifier.md` | Cold pre-dispatch spec checker: L/I/P/E/A row types, CONFIRMED/REFUTED/UNVERIFIABLE verdicts, hunts missing premises | **NO** (Claude-only read) | **KEEP-AS-IS** | fable-advisor is read-only; Claude premise-verifier is a specialized lens. Our codex lanes are writable. This is a Claude-side tool, not codex-team scope | Low: no change; it's in the partner Claude workflow |
| **Advisor agent (read-only)** | fable-orch `fable-advisor.md` + ours `codex-sol-advisor.md` | Commitment-boundary decisions at read-only (code+code only); gives verdict + single deciding risk | **YES** | **KEEP-AS-IS** | We have `codex-sol-advisor` + `codex-astra-advisor` mirrored; works well | Low: maintain current pair |
| **Four-phase workflow** | claudex-loop `SKILL.md:44-91` | Recon → Settle requirements → Plan review (multi-round) → Build & inspect | **PARTIAL** | **DROP** | Our team has six domain-specialists, not phases. Phases assume one task; our router splits multi-domain work. Different model | Low: we route by domain, not phase—this is architectural choice, not a feature gap |
| **Round budgets (review/fix/inspect)** | claudex-loop `README.md:126-128` | MAX_ROUNDS (5), MAX_FIX_ROUNDS (2), MAX_INSPECTION_ROUNDS (2) as tunables | **NO** | **ENHANCE** | Prevents endless retry loops. Our timeout is wall-clock only. | Low-Medium: add round counters to settlement; codex's own iteration count already caps it |
| **Proof command evidence grading** | claudex-loop `SKILL.md:80-91` + fable-orch `codex-implementer.md:174` | Grade as `captured` (log shows it ran + passed), `captured-fail` (ran + failed), `claim-only` (model claims but no log) | **NO** | **MIGRATE** | Proves verification actually ran. #1202's real evidence came from grading, not trust. | Medium: run verification at settlement, parse log for pass/fail signal, report grade |
| **Fresh session for cross-family review** | claudex-loop `SKILL.md:80-91`, line 86 | Inspector always uses OTHER provider in fresh session; never reuses builder's session | **NO** | **ENHANCE** | Prevents blind spots (same model sees same things). fable-orch has no explicit rule here—claudex-loop does. | Low-Medium: document that each six-specialist lane is *fresh* (already true; needs documenting) |
| **Stability anchors (git baseline/branch)** | fable-orch `codex-implementer.md:107-118` | Record baseline commit, branch name, pre-existing dirt BEFORE launch; re-verify after. Catches foreign commits. | **NO** | **MIGRATE** | Prevents silently absorbing another writer's work. Measured incident 2026-09-16. | Medium: add `git rev-parse HEAD`, `git branch --show-current`, re-check at settlement |
| **Licensed dissent (spec conflicts code)** | fable-orch `codex-implementer.md:199` | Codex can stop mid-run saying "spec contradicts the code"; this is SUCCESS, not failure. Report it, never relaunch. | **YES** | **KEEP-AS-IS** | `codex-sdlc-team.md:45` documents stop-on-dissent clause; `sdlc_team.py` never relaunches. Already in place. | Low: no change needed |
| **Evidence discipline (read log, not notification)** | fable-orch `codex-implementer.md:174-175` | Never trust codex's message; machine-captured log is the source of truth. Grade from actual output. | **PARTIAL** | **ENHANCE** | We capture output; we don't parse verification command results. Documentation exists but implementation incomplete. | Medium: parse `$OUT` for proof-command success/failure signal |
| **Detached launch + reap supervision** | fable-orch + ours `sdlc_team.py` | Launch via supervisor, wait in bounded slices, reap at end. Process outlives the turn if needed. | **YES** | **KEEP-AS-IS** | `sdlc_team.py:dispatch()` detaches; `_reap_lane()` cleans up. Working. | Low: maintain current impl |
| **Codex CLI flag validation** | fable-orch `codex-implementer.md:163-172` + our `ai-cli-invocation.md` | Supervisor enforces `--sandbox workspace-write`, `-c model_reasoning_effort=<level>`, specific flags only. Validate levels. | **YES** | **KEEP-AS-IS** | `sdlc_team.py` and `ai-cli-invocation.md` both validate. Supervisor enforces. | Low: maintain |
| **FAST MODE and EFFORT tunables** | fable-orch `codex-implementer.md:140-142` | TIMEOUT, FAST MODE, EFFORT lines in dispatch; supervisor prefixes env vars accordingly | **YES** | **KEEP-AS-IS** | `sdlc_team.py:47`, `:69` pass these through. Already wired. | Low: maintain |
| **Spec verbatim pass-through (no rewrites)** | fable-orch `codex-implementer.md:38, 51-73` | Never paraphrase/summarize/reorder spec before handing to codex. Use `cat`, never heredoc transcript. | **YES** | **KEEP-AS-IS** | `sdlc_team.py` uses prompt file + `cat`. Verbatim principle upheld. | Low: maintain |
| **Worktree isolation** | fable-orch `codex-implementer.md:122` | If spec runs in `isolation: worktree`, copy per-machine config (`.env`, `local.properties`, etc.) from parent checkout | **PARTIAL** | **ENHANCE** | `sdlc_team.py` doesn't document worktree provisioning. Codex isolation exists but seaming is manual. | Low: document per-machine file copying in settlement spec |
| **Report format (structured fields)** | fable-orch `codex-implementer.md:180-193` | Codex Report with STATUS, OBJECTIVE, CHANGES, VERIFIED (grade), COMMIT (hash or reason), PROCESS (reap output), REASON, GAPS | **YES** | **ENHANCE** | We have `SdlcTeamSettlement` but fields are less structured. VERIFIED grade is missing. | Low-Medium: add `verified_grade` field to settlement schema |
| **Commit ownership control** | fable-orch `codex-implementer.md:36` | Spec can say `COMMIT: caller` to leave tree uncommitted; lane owns commit by default. | **YES** | **KEEP-AS-IS** | `sdlc_team.py:38` mentions; settlement reports it. Working. | Low: maintain |
| **Spec part validation (missing parts list)** | fable-orch `codex-implementer.md:34-36` | If spec missing 6 of 7 parts (PREMISES always required), list gaps in process block, flag in report | **NO** | **DROP** | Our specs are fully-formed before dispatch; we don't handle partial specs. Different use case. | Low: out of scope—our architect pre-writes complete specs |
| **Codex CLI model override** | fable-orch `codex-implementer.md:143` | Fourth arg to supervisor: custom codex model (default gpt-5.6-sol). Slug mapping. | **YES** | **KEEP-AS-IS** | `sdlc_team.py` passes through; supervisor accepts it. Already wired. | Low: maintain |
| **Process-spawn MCP (never native registration)** | our `.claude/rules/research-doc-sources.md` lane 2 | MCP for our own tools: prefer CLI then mcp2cli, not native registration (per-conversation schema tax) | **YES** | **KEEP-AS-IS** | Our doc sources rule already bans lane-2 native MCP. Upheld in practice. | Low: maintain |
| **Failure-mode signatures for transient retries** | our `.claude/rules/persistence-gate-retry.md` | DNS/image-store transients retryable; REAL defects (build-time failures, R-invariant regression) are not | **NO** | **DROP** | Applies to devcontainer gates, not codex-lane verification. Out of scope. | Low: external rule, not codex-team feature |
| **Cross-family review rule (different vendor for review)** | our `.claude/CLAUDE.md` line 62 | No `codex-*` lane is cold-review lens for codex diff (same family blind spots); Claude Opus is the third family | **YES** | **KEEP-AS-IS** | Documented; enforced by not wiring codex as a cold reviewer of codex diffs. Correct doctrine. | Low: maintain as architectural principle |
| **Escape-hatch tool set** | our `claude-doctor` hook (`register.ts:113`) + `fnhook_gates` | Tools permitted to Run/Read under deny: AskUserQuestion, SendUserMessage only. No Edit/Write. | **NO (codex scope)** | **KEEP-AS-IS** | This is a Claude-side hook mechanism. Codex has different permissions model. Not applicable. | Low: no change needed |
| **Hook event budget (10s, $ calls free)** | fable-orch + ours `.claude/CLAUDE.md` + #1202 | PreToolUse hook has 10s budget; `$.process.run` calls are free (up to 90s). Budget overrun fails OPEN (deny drops). | **NO (codex scope)** | **KEEP-AS-IS** | Codex has its own resource model (xhigh reasoning, sandbox, timeout). Not applicable here. | Low: no change needed |
| **Untracked `.agent/` ephemeral state** | our `.claude/rules/agent-artifact-conventions.md` | Working artifacts in `.agent/` (gitignored, swept by `git clean`); durable reports in `docs/research/kb/reports/agents/` | **YES** | **KEEP-AS-IS** | `sdlc_team.py` respects this; reports go to tracked dir. Already upheld. | Low: maintain |
| **Settlement reconciliation (spawn vs rollout)** | our `sdlc_team.py` reconcile_spawns | Verify claimed spawns (in settlement JSON) match rollout files on disk (recon vs reality). Fail closed if mismatch. | **YES** | **KEEP-AS-IS** | `reconcile_spawns()` does exactly this. Prevents silent lane failures. | Low: maintain |

---

## Top 5 Most Critical Features (Loss = High Operational Cost)

1. **PREMISES block + attestation validation** (rows 1–2)  
   *Why:* Spec without facts stated → implementation without constraints. Premise verification is our only pre-launch correctness gate. Loss means no safety rails.

2. **Proof command evidence grading** (row 7)  
   *Why:* "Codex said it worked" is not evidence. Measured failure in #1202: tests passed, gates failed, model claimed success. Grading separates real from claimed.

3. **Stability anchors (baseline/branch/foreign commits)** (row 9)  
   *Why:* Two writers on one checkout. Measured 2026-09-16: another lane rewrote implementer's work. Anchors catch this. Loss = silent data corruption.

4. **Licensed dissent (stop on spec↔code conflict)** (row 10)  
   *Why:* Codex refusing a broken spec is SUCCESS, not failure. Relaunching it = infinite loop. Treating dissent as error is the common failure mode.

5. **Cross-family review rule** (row 23)  
   *Why:* codex-sol-implementer reviewed by codex-sol-reviewer = both miss the same thing. Claude Opus is the third family. Rule prevents false confidence.

---

## Top 5 Dead Weight Features (No Loss to Drop)

1. **Four-phase workflow (recon/settle/review/build)** (row 5)  
   *Why:* Assumes one task; our router splits by domain (six specialties). Architectural mismatch. We don't need phases; we route by expertise.

2. **Spec part validation (missing parts list)** (row 19)  
   *Why:* Architects pre-write complete specs; we don't handle partial ones. Different use case. No operational value for us.

3. **Failure-mode signatures for transient retries** (row 21)  
   *Why:* Applies to devcontainer persistence gate, not codex verification. Out of scope for this team.

4. **Escape-hatch tool set** (row 24)  
   *Why:* Claude-side hook mechanism. Codex has different permissions model. Not applicable.

5. **Hook event budget details** (row 25)  
   *Why:* Claude-side process model. Codex operates differently. Documentation doesn't apply here.

---

## Contradictions with Repo Rules

### Contradiction 1: `ai-cli-invocation.md` vs fable-orch sandbox
**Sides:**
- **Repo rule** (`.claude/rules/ai-cli-invocation.md:62`): "Measured 2026-09-12, ... `-s workspace-write` → RC=1 (file not created, BLOCKED for git-tree writes), `-s danger-full-access` → RC=0 (works)."
- **fable-orch** (`codex-implementer.md:167`): "Never `danger-full-access`" is stated as a sane default for generic repos.

**Evidence:** 2026-09-12, live probe on THIS repo during #1026 showed that every gate (`mise run lint`, `pytest`, `mise uninstall`) writes outside the working tree. `workspace-write` blocks all of them. File: `codex-sol-implementer.md:65-80`.

**Ruling:** **Our repo is NOT generic.** Our gates require full access. fable-orch's rule is correct for general use; our implementation correctly overrides it. **No change needed**—our rule is documented and defensible.

### Contradiction 2: Premise verification as Claude vs codex
**Sides:**
- **Repo routing** (`.claude/CLAUDE.md` line 62, table): Premise verification is listed as a Claude-only tool (`fable-orchestrator:premise-verifier`).
- **fable-orch `codex-implementer`** (line 34-42): Expects PREMISES block and attestation in spec, gating dispatch itself.

**Evidence:** premise-verifier is read-only (`.claude/agents/codex-sol-advisor.md` mirrors fable-advisor as read-only). It can read code to verify claims. Codex writable lanes cannot serve as premise-verifiers (their job is implementation, not critique). History shows premise verification happened before #1202 implementation dispatch.

**Ruling:** **No contradiction—division of labor is correct.** Premise verification is Claude-side. Our codex-team just needs to validate that it ran (attestation line). **No change needed**.

### Contradiction 3: Report format completeness
**Sides:**
- **fable-orch report** (`codex-implementer.md:180-193`): Includes VERIFIED (grade), PROCESS (reap output), REASON (on timeout only).
- **Our settlement** (`sdlc_team.py` `SdlcSettledStatus`): STATUS only; missing VERIFIED grade and PROCESS.

**Evidence:** #1202 remediation graded proof-command results (captured vs claim-only). Our `SdlcTeamSettlement` has no `verified_grade` field. Fable-orch showed this is load-bearing for honest reporting.

**Ruling:** **MIGRATE**: Add `verified_grade` field to settlement. Low cost; immediate value for future review.

---

## Codex Lane Specific Insights

### What Codex Actually Needs from the Wrapper

1. **Verbatim spec arrival** — Codex is a text-in, code-out system. Rewrites break it. ✅ We do this.
2. **Proof-command grading** — Codex can't judge its own work. The log does. ✅ We capture log, but don't grade it yet.
3. **Stop on dissent, never retry** — Codex saying "the spec is wrong" is wisdom, not failure. ✅ We handle this.
4. **Stability anchors** — Shared checkout needs boundary markers. ✅ Missing; should add.
5. **Clear verdict on whether to trust output** — CAPTURED (log proves it) vs CLAIM-ONLY (model says it). ✅ Missing.

### What Codex Doesn't Need from Predecessors

- **Round budgets** — Codex has its own iteration limits internally; our timeout is sufficient.
- **Phases** — Our specialist routing replaces phases; simpler and more flexible.
- **Fresh sessions per cycle** — Codex keeps state internally (context); reuse is fine.

---

## Cost/Risk Summary

| Feature | Cost to add | Risk if missing | Recommendation |
|---------|----------|----------------|-----------------|
| PREMISES + attestation validation | Medium (2 gate checks) | **HIGH** — specs enter without fact statements | **MIGRATE immediately** |
| Proof-command evidence grading | Medium (log parsing + grade enum) | **HIGH** — can't tell real from claimed | **MIGRATE immediately** |
| Stability anchors | Medium (3 git calls, re-check) | **HIGH** — can absorb other writers' work silently | **MIGRATE soon** |
| Round budgets | Low (add counters to settlement) | Low — timeout + codex's internal limits usually sufficient | **ENHANCE if time** |
| Verified grade in settlement | Low (add field, minor parsing) | Low — affects reporting only, not safety | **ENHANCE soon** |
| Worktree provisioning docs | Low (document existing behavior) | Low — it works; just undocumented | **ENHANCE (docs only)** |

---

## Final Assessment

**Current state:** Our sdlc-team is **lightweight and functional**. It routes work, launches codex, and reports results.

**What's missing:** **Pre-launch validation** (premises) and **post-launch grading** (proof commands). These are the gates that fable-orchestrator and claudex-loop both emphasized.

**Recommendation:** Add the three "MIGRATE immediately" features (PREMISES validation, attestation check, evidence grading). Cost is 30–40% more code; payoff is catching spec defects before dispatch and proving gates actually ran.

**Do not adopt:** Phases, round budgets (redundant with timeout), or cross-family review rule (already documented separately). Our architecture is correct; predecessors just solve different problems.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; all features, implementation, and rules
- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — workflow phases, round budgets, proof-command grading, fresh sessions
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — premise verification, attestation, evidence grading, stability anchors, CLI wrapping discipline
