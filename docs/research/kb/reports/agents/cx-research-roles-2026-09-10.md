# SDLC Roles Research for Codex — 2026-09-10

**Status:** Research in progress (codex xhigh effort, ~15 min remaining).

**Goal:** Identify all possible SDLC roles codex (gpt-5.6-sol) could enable to conserve Claude tokens, propose full re-architecture including which Claude lanes codex should replace, and deliver a sequenced adoption plan.

**Research approach:** 
- Inventory existing 16 Claude agents + 5 codex agents + 3 workflows + skills
- Run codex research at xhigh effort on role catalogue, takeover candidates, token economics, adoption plan
- Persist findings incrementally per `agent-report-persistence.md` rule 1b
- Deliver before idle per rule 2

---

## Phase 1: Existing Inventory

### Claude Lanes (11 agents)

| Agent | Model | Effort | Role | Status |
|-------|-------|--------|------|--------|
| adversarial-critic | opus | high | Attacks proposals (rules, gates, hooks, fixes); tests if they catch motivating defects | production |
| claude-code-expert | opus | high | Claude Code harness authority (harness, plugins, hooks, settings, flags) | production |
| cold-reviewer | opus | xhigh | Cold diff review by ref; cites severity/claim/file:line | production |
| dockerfile-reviewer | sonnet | — | Reviews Dockerfile + BuildKit for devcontainer builds | production |
| graphify-researcher | opus | high | Installed-feature inventory (commands, flags, exports, MCP tools) | production |
| staleness-auditor | opus | high | Audits prose (rules, AGENTS.md, docs) for stale claims; file:line + control arm | production |
| spec-scribe | opus | high | Seven-part spec drafting from architect notes | production |
| pwf-scribe | sonnet | medium | Planning-with-files scribe; writes findings/progress + deltas | production |
| graphify-operator | sonnet | medium | Runs mise task list; reports graph deltas | production |
| gate-runner | haiku | low | Runs gates with file-captured exits; reports first failure | production |
| issue-filer | sonnet | medium | GitHub issue/comment drafting (guarded); never creates PRs | production |

### Codex Lanes (5 agents, all model: haiku)

| Agent | Effort | Role | Status |
|-------|--------|------|--------|
| codex-adversarial-critic | — | Attacks proposals; gpt-5.6-sol substitute for Claude lane | experimental |
| codex-advisor | — | Verdict at commitment boundary (migration/API/architecture) | experimental |
| codex-claude-code-expert | high | Claude Code harness authority; gpt-5.6-sol substitute | experimental |
| codex-operator | — | Runs ONE named mise task (land/automerge/sync/verify-local) | experimental |
| codex-staleness-auditor | — | Audits prose for stale claims; gpt-5.6-sol substitute | experimental |

**Note:** All five codex lanes are **token-constrained substitutes** — none are additive new roles. Five Claude lanes have codex twins but no new capability.

### Workflows (3)

**1. gated-implementation**
- **Purpose:** Orchestrate spec → implementation → gates → review → optional critique
- **Phases:** Implement (codex-implementer), Gates (gate-runner), Review (cold-reviewer), Critique (codex-adversarial-critic)
- **Input:** ratified spec file, premises, verification commands list
- **Output:** commit SHA, gate results (rc/logs), review findings, critique verdicts
- **Implication:** Proves codex-implementer exists and is integrated into validated workflows

**2. graphify-refresh**
- **Purpose:** Inventory Graphify features, run ordered tasks, optionally audit stale prose
- **Phases:** Research (optional; graphify-researcher), Operate (graphify-operator), Audit (optional; staleness-auditor)
- **Input:** task list, stale terms to audit, optional research brief
- **Output:** feature inventory, task results, stale findings
- **Implication:** Established workflow for coordinating graph-dependent operations

**3. modernization-audit**
- **Purpose:** 5-phase whole-repo audit for custom vs native features
- **Phases:** Gap fetch, Find (per-unit), Verify (3 lenses), Synthesize (md + toml), Critique (completeness)
- **Input:** module/rule/group lists, corpus paths, gap sources, pins
- **Output:** findings JSON, report md, report toml, counts, critique gaps
- **Implication:** Demonstrates multi-phase, multi-lens verification pattern; potential template for new role orchestration

### Key Constraints

- **Listing budget:** doctor.toml caps agent + skill listing at 41,305 chars (context cost every session)
- **New machinery justification:** `.claude/rules/use-tool-builtins.md` requires written justification
- **Skill architecture:** skill → mise task → python library; no bash logic
- **Codex sandbox:** read-only or workspace-write available (full-auto gated)
- **Codex model:** gpt-6-astra is the latest (as of brief); gpt-5.6-sol is the pinned "deep research" model

---

## Phase 2: SDLC Coverage Gap Analysis

**Confirmed to exist:**
- ✅ Implementation (codex-implementer exists, integrated in gated-implementation workflow)
- ✅ Proposal adversarial review (codex-adversarial-critic + Claude adversarial-critic)
- ✅ Specification authoring (spec-scribe, opus)
- ✅ Gate execution (gate-runner)
- ✅ Cold diff review (cold-reviewer, opus xhigh)
- ✅ Staleness auditing (staleness-auditor, codex-staleness-auditor)
- ✅ Harness expertise (claude-code-expert, codex-claude-code-expert)
- ✅ Graphify integration (graphify-operator, graphify-researcher)
- ✅ Issue filing (issue-filer)

**Gaps potentially exploitable by new codex roles:**
- Test authoring (no agent; codex opportunity)
- Refactoring / cleanup (no agent; codex opportunity)
- Migration execution (no agent; codex opportunity)
- Dependency/currency work (no agent; codex opportunity)
- CI triage / debugging (no agent; codex opportunity)
- Documentation authoring (no agent; codex opportunity)
- Release management (no agent; codex opportunity)
- Incident response / triage (no agent; codex opportunity)
- Security review (no agent; codex opportunity)
- Performance optimization (no agent; codex opportunity)

**Codex research will deliver:**
1. Full role catalogue with input/output contracts for each gap
2. Model/effort recommendation (codex gpt-5.6-sol vs Claude Opus/Sonnet/Haiku)
3. Token displacement estimate per role
4. Defect risk assessment per role
5. Which Claude lanes codex should **replace** (with conflict-of-interest caveat)
6. Which lanes must **stay with Claude** (harness checks on codex work, spec authoring, etc.)
7. Sequenced adoption plan (phases, success criteria, stop conditions)

---

## Incremental Findings (Codex output awaited)

_Waiting for codex research output. Expected completion: ~2026-09-10 13:00 UTC_

---

## Final Deliverable Sections (Pending)

1. **Role catalogue** — table: role | owns | input | output | model/effort | displacement | risk
2. **Codex takeover candidates** — table: lane | should_codex_replace | reasoning | conflict_of_interest_caveat
3. **What stays with Claude** — list with justifications
4. **Token economics estimate** — by role, with caveats (unmeasured per-lane cost)
5. **Sequenced adoption plan** — phases, KPIs, stop conditions

---

## Appendix: GitHub Repos Touched (to be added with codex findings)

_Will enumerate all repos whose source or docs were consulted during research._

---

**Last updated:** 2026-09-10 12:55 UTC (codex research in progress; incremental persistence active)
