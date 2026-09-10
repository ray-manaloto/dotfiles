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

**Last updated:** 2026-09-10 — codex output RECOVERED and merged by the coordinator at session handoff.

⚠️ **Provenance:** the lane that commissioned this never merged codex's answer. Codex
completed and wrote `/tmp/codex-roles-output.md` (32,663 bytes) at 02:44; the lane went idle
still reporting "in progress", leaving the only copy in volatile `/tmp`. Recovered verbatim
below during `/session-handoff`. This is the failure mode
`.claude/rules/agent-report-persistence.md` rule 1b exists to prevent — deliver before idle —
and it is the second time in this session a lane's finished work nearly died in scratch space.

---

# Codex output (verbatim, `gpt-5.6-sol` @ xhigh)

# SDLC Roles for Codex

**Research date:** September 10, 2026  
**Target:** `gpt-5.6-sol`, reasoning effort `xhigh`

**Recommendation:** Make Codex the default producer for bounded implementation, investigation, testing, and drafting. Keep Claude for independent checks of consequential Codex-authored work. Most additional SDLC roles should be task-specific contracts carried by existing agents, rather than new entries in the standing roster.

The highest-leverage next step is **qualifying the existing implementation lane**, followed by test authoring and CI triage. `codex-implementer` already exists; a Codex cold reviewer exists too.

This is a research proposal, not a production certification. I inspected the local definitions, workflows, selected execution reports, installed CLI, and current vendor documentation. Graphify and the live listing measurement were blocked by filesystem restrictions. No files were written in this read-only session.

## 1. Role catalogue

The catalogue describes **34 dispatchable responsibilities**, not 34 recommended agents. It covers the practical SDLC surface; specialist domains can add further contracts.

In the table:

- **X** means Sol at `xhigh`, the requested evaluation baseline.
- **O**, **S**, and **H** mean displaced Opus, Sonnet, and Haiku turns.
- Displacement ranges are **gross planning assumptions per bounded assignment**, before supervision, review, retries, and caching. Overlapping rows must not be added together.
- Model-fit statements are recommendations to test, not measured superiority over Claude.

OpenAI currently positions Sol for complex coding, research, and document work. That supports evaluating these roles, but does not establish project-specific fidelity. [OpenAI model guidance](https://learn.chatgpt.com/docs/models)

| Role | Owns | Input contract | Output contract / success evidence | Model/effort fit | Displacement | Main risk |
|---|---|---|---|---|---|---|
| Requirements analyst | Acceptance criteria and unresolved questions | User objective, constraints, examples | Traceable criteria; assumptions explicitly marked | X: useful for conflicting requirements | O 1–3 | Inventing product decisions |
| Domain modeller | Concepts, invariants, state transitions | Domain examples, existing interfaces | Glossary, state model, counterexamples | X: relational reasoning | O 2–4 | Elegant but incorrect abstractions |
| Spec drafter | Seven-part implementation specification | Ratified decisions, source paths | Complete spec with fresh premise citations | X: suitable for synthesis | O 1–3 | Altering meaning while drafting |
| Premise researcher | Evidence behind proposed assumptions | Premise list, versions, source corpus | Each premise verified, refuted, or unknown; controls | X: strong investigation candidate | O 1–3 | Missing unstated premises; self-validation |
| Architecture advisor | Options and commitment recommendation | Decision, constraints, alternatives | Verdict, deciding risk, rejected alternatives | X: valuable for tradeoffs | O 1–3 | Confident advice built on incomplete evidence |
| Code mapper / impact analyst | Dependency and affected-surface map | Symbol/change scope, current graph and source | Callers, consumers, tests, coverage limits | X: useful across complex relationships | O 1–3 | Treating graph omissions as absence |
| Tooling / Graphify researcher | Installed-capability inventory | Installed version, package, CLI, release sources | Enumerated commands/flags/exports/tools with dispositions | X: suitable for exhaustive investigation | O 2–6 | Missing surfaces or confusing installed and upstream behavior |
| Implementer | Bounded production change | Ratified spec, file ownership, verification, commit ownership | Diff/ref, captured checks, deviations, settled process | X: primary takeover role | O 3–10 | Scope creep, missed requirements, incomplete settlement |
| Bug diagnostician | Reproducer and causal explanation | Failure, environment, logs, suspect revisions | Reproduction, discriminating controls, cause | X: valuable for competing hypotheses | O 2–6 | Mistaking correlation for cause |
| Regression-test author | Behavioral regression protection | Defect or acceptance criteria, public interfaces | Test fails on defect and passes on fix | X: useful for edge cases | S 2–6 | Tests that merely mirror implementation |
| Property / mutation-test author | Invariant and gate sensitivity evidence | Contract, production binding, mutation target | Meaningful failing mutation and passing control | X: high-value reasoning | O 2–5 | Vacuous properties or mutations at the wrong seam |
| Integration / E2E engineer | Real-client behavior verification | Running services, fixtures, journeys | Actual client execution and observed outcomes | X: useful across boundaries | S 2–5 | Replacing integration evidence with mocks |
| Refactoring engineer | Behavior-preserving structural change | Boundary, invariants, baseline tests | Smaller/deeper module boundary; preserved behavior | X: suitable for complex refactors | O 2–6 | Undeclared semantic changes |
| Migration engineer | Code/schema/config transition | Source/target versions, compatibility and rollback requirements | Rehearsal, reconciliation, compatibility and rollback evidence | X: suitable producer; independent review required | O 3–8 | Partial migration, data loss, incompatible rollback |
| Dependency / currency engineer | Upgrade assessment and bounded upgrade | Manifest scope, locks, release notes | Version delta, compatibility findings, correct locks, gates | X: useful for difficult upgrades | S 2–5 | Broad lock churn or outdated guidance |
| CI diagnostician | Failure classification and corrective brief | Exact run/job, logs, SHA, local equivalent | Decisive failure evidence, reproducer, proposed fix | X: strong early adoption candidate | O 1–4 | Treating aggregate green status as proof |
| Build / devcontainer engineer | Build configuration and environment changes | Bake/Docker configuration, platform and SSH invariants | CI image evidence and applicable R1/R2/R3 results | X: useful for interacting build constraints | S 2–5 | Host/container or architecture mismatch |
| Cold code reviewer | Defect findings against immutable code | Resolved base/head refs; no author narrative | Cited findings, severity, coverage and omissions | X: appropriate for Claude-authored code | O 1–4, conditional | Correlated misses on OpenAI-authored code |
| Security reviewer / threat modeller | Attack paths and defensive findings | Trust boundaries, code, threat assumptions | Reproducible findings and mitigation requirements | X: useful specialist analysis | O 2–6 | False negatives; same-producer assurance |
| Performance engineer | Bottleneck diagnosis and optimization | Representative workload, profiler, baseline | Before/after measurements with correctness checks | X: useful when diagnosis is difficult | O 2–6 | Optimizing noise or unrealistic workloads |
| UX / accessibility evaluator | Interaction defects and acceptance evidence | User journeys, UI, requirements | Reproduced issues and tested improvements | X: useful with browser evidence | S 2–4 | Judging screenshots without interaction testing |
| Documentation author | User/developer documentation | Verified behavior, audience, examples | Accurate procedures and executable examples | X: capable; often excessive for small edits | S 1–4 | Documenting intended rather than actual behavior |
| Staleness auditor | Claims invalidated by changed reality | Changed facts, prose scope, sources | Claim/falsifier/probe/control rows | X: strong candidate after qualification | O 2–5 | Confusing policy with platform capability |
| Adversarial proposal critic | Whether a proposal catches its motivating defect | Exact proposal, historical defect, control case | Replay-based verdict and residual gaps | X: suitable for Claude-authored proposals | O 1–3, conditional | Reviewing its own reasoning chain |
| Gate operator | Execution evidence | Exact command matrix and expected outcomes | One result per command, real exit, full log | Existing task first; X excessive | H 1–3 | Reporting wrapper exit as task exit |
| Graphify operator | Ordered graph operations | Repository task list, expected exits, baseline | Attempted-task ledger and graph deltas | Existing tasks first; X excessive | S 1–3 | Unapproved commands or stale graph claims |
| Release operator | Execution of an authorized release sequence | Approved ref, destination, task, prerequisites | Actual task exit and verified resulting state | Existing tasks first; X excessive | S 1–3 | Wrong ref, repeated side effects, partial completion |
| Incident investigator | Timeline, impact and causal hypotheses | Telemetry, deployment history, incident scope | Evidence timeline, cause confidence, mitigation options | X: useful for difficult incidents | O 2–6 | Acting beyond authority; premature root cause |
| Observability engineer | Useful telemetry and diagnostic coverage | Failure modes, existing telemetry, operational needs | Instrumentation plus demonstrated diagnostic value | X: useful for signal design | S 2–4 | Sensitive-data logging or unhelpful metrics |
| Issue / backlog drafter | Actionable tickets and deduplication | Confirmed findings, repository, triage conventions | Reviewable issue bodies and provenance | X: capable; excessive for routine formatting | S 1–2 | Filing speculative or duplicate issues |
| Planning / handoff scribe | Evidence-preserving records | Confirmed outcomes and coordinator instructions | Append-only findings/progress; proposed plan delta | X: capable; usually excessive | S 1–3 | Lost context, invented status, destructive rewrites |
| Agent evaluator | Role qualification and regression evidence | Task corpus, acceptance rubric, baseline | Outcomes, errors, usage and latency by case | X: useful analyst; independent grader needed | O 2–5 | Model grading its own success |
| Supply-chain evidence analyst | SBOM/license/provenance findings | Manifests, artifacts, scanner results, policy | Evidence inventory and unresolved obligations | X: useful interpretation; tools do enumeration | S 1–3 | Treating scan output as legal/security certification |
| Decommissioning engineer | Safe removal of obsolete capability | Consumers, replacement, retention requirements | Removal diff, consumer checks, rollback path | X: useful for hidden dependencies | O 2–5 | Deleting something still used |

Every dispatch should additionally identify the repository and revision, permitted writes, actual model/effort, resource limits, report destination, and the condition that makes the result **blocked or incomplete**. A test count alone is never the output contract.

## 2. Codex takeover candidates

### Inventory corrections

The local inventory contains **16 tracked Claude agent definitions**, **9 Codex TOMLs on disk, of which 5 are tracked**, and **3 tracked workflows**. Plugin agents expand that inventory.

**Implementation already exists and has execution history.** The configured route is `fable-orchestrator:codex-implementer` at `xhigh`. Its installed wrapper runs on Sonnet and invokes Sol. A recorded implementation produced code and tests, encountered sandbox restrictions, and required a caller correction before commit. This proves actual use, not flawless autonomous delivery. [Current routing](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/CLAUDE.md:64), [implementation receipt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-08-29h-codex-implementer-832.md:28)

**A Codex cold reviewer also exists:** `fable-orchestrator:codex-reviewer`. Its contract explicitly covers Claude-authored changes. There is no need to invent another project-local reviewer merely to obtain that capability. [Installed reviewer](/Users/rmanaloto/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.21.0/agents/codex-reviewer.md:1)

**The two configuration surfaces are different.** Claude-side wrappers explicitly invoke Sol at `xhigh`. The five hand-authored native Codex TOMLs set `model_reasoning_effort`, but omit actual `model` and `sandbox_mode` settings. Describing Sol/read-only inside their prompts does not pin those settings. Native configuration supports explicit pins; omitted settings depend on inherited configuration. [Native advisor definition](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/agents/codex-advisor.toml:11), [current Codex configuration semantics](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents)

**CLI capability differs from the brief.** Live probes returned:

- `codex --version` → `codex-cli 0.154.0`.
- `codex exec --full-auto --help` → exit **2**, unexpected argument.
- `codex exec --ephemeral --help` → exit **0**.

Consequently, `--full-auto` should not appear in the adoption design for this installed version.

**The configured Fable upstream is archived.** GitHub records archival on September 5, 2026. Preserve the installed capability while evaluating a supported native replacement; avoid adding more bespoke supervision to that dependency. [Fable repository](https://github.com/mar3co/fable-orchestrator)

### Replacement decisions

“Replace” below means changing the default route after qualification, not immediately deleting the fallback.

| Lane | should_codex_replace | Reasoning | conflict_noted |
|---|---|---|---|
| Implementation currently performed by Claude | **Yes** | Existing Sol lane already supplies the main mechanism; expand proven use | Retain Claude review of behavior-bearing Codex changes |
| `cold-reviewer` | **Conditional** | Use Codex for Claude-authored diffs; keep Claude for Codex-authored diffs | OpenAI reviewing OpenAI does not supply the intended vendor diversity |
| `staleness-auditor` | **Yes, after qualification** | Evidence-backed claim checking is a plausible Sol specialty | Claude checks consequential changes to Codex’s own instructions |
| `adversarial-critic` | **Conditional** | Codex can critique Claude-authored proposals | Codex-authored architecture needs a Claude challenge |
| `claude-code-expert` | **Yes, for routine research** | Harness expertise depends on current evidence, not the researcher’s vendor | Claude validates consequential Codex-produced harness changes |
| `spec-scribe` | **Yes, drafting portion** | Its existing job starts from ratified notes; semantic understanding is not Claude-exclusive | Keep independent premise checks and architect ratification |
| `graphify-researcher` | **Yes, after coverage qualification** | Command/flag/export enumeration is measurable | No self-certification of a Codex-authored Graphify integration |
| `dockerfile-reviewer` | **Conditional** | Codex can perform the domain review, especially for Claude-authored changes | It cannot replace the independent review of its own Dockerfile changes |
| `pwf-scribe` | **Prefer direct artifact handling; Codex if synthesis is needed** | Routine carriage does not merit Sol/xhigh | Protect shared files and coordinator-owned plans |
| `graphify-operator` | **Prefer direct repository tasks** | Exact task execution needs little model reasoning | Graph mutation and refresh success still need real evidence |
| `gate-runner` | **Prefer direct repository tasks** | Moving Haiku supervision to Sol/xhigh may increase total cost | Preserve complete matrix coverage and task exits |
| `issue-filer` | **Yes for drafting; native CLI for authorized filing** | Separate content judgment from the mechanical write | Preserve explicit repository and filing authority |
| Fable advisor | **Conditional Codex default** | Existing advisor can handle routine commitment questions | Claude should challenge Codex-led architectural decisions |
| Release/operator work | **Task-first; Codex interprets exceptions** | Existing `ship`/`automerge`/`land`/`sync` already own mechanics | Prompt scope alone does not constrain a full-access process |

The spec-scribe recommendation follows its actual contract: it drafts from ratified notes and does not approve or dispatch its own draft. [Spec-scribe definition](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/agents/spec-scribe.md:14)

### Are the five existing Codex lanes production-ready?

**The examined evidence cannot certify all five.** Presence, prior execution, and qualification are different statuses.

| Codex lane | Evidence found | Defensible status |
|---|---|---|
| Advisor | September 3 report records a successful Sol/xhigh invocation and populated output | Exercised; current-version qualification still needed |
| Adversarial critic | Historical receipt includes actual Sol runtime banner and findings, at `high` | Capability exercised; does not qualify the current `xhigh` wrapper |
| Staleness auditor | Definition and workflow route exist; recent report identifies its reasoning as local Haiku | Configured; examined recent report is not Sol evidence |
| Claude Code expert | Explicit wrapper and native definition exist | Configured; sufficient current execution proof not established in this review |
| Operator | Definition records prior sandbox probes and a real task-exit reporting failure | Operational history exists; fresh success/failure qualification needed |

Sources: [advisor execution](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-03-advisor-botprs-codex.md:111), [critic runtime receipt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codex-adversarial-437-source-of-truth.md:18), [Haiku-labelled staleness report](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/session-audit-staleness-2026-09-10.md:1), [operator failure history](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/agents/codex-operator.md:81).

### What the three workflows actually do

| Workflow | Actual responsibility | Adoption implication |
|---|---|---|
| `gated-implementation` | Spec → Codex implementation → gate matrix → Claude cold review → optional Codex critique | Reuse it, but independently evaluate gate exits and findings |
| `graphify-refresh` | Optional installed-feature research → ordered graph tasks → optional Codex staleness audit | Good bounded target for replacing research and supervisory work |
| `modernization-audit` | Gap collection → per-unit findings → three verification lenses → synthesis → completeness critique | Potentially large savings from moving discovery to Codex |

A significant distinction: `gated-implementation` assigns `status: complete` based on non-null phase results; it does not require zero gate exits or an empty review. Treat it as **completed orchestration**, not a shipping verdict. [Status calculation](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/workflows/gated-implementation.js:132)

The modernization workflow currently uses Opus finders, Sonnet verification lenses, and Opus synthesis/critique. Moving only the named five Codex lanes misses this potentially substantial Claude workload. [Finder and verifier routing](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/workflows/modernization-audit.js:134)

## 3. What stays with Claude

Retain these responsibilities because of their relationship to the producer, rather than because their role names imply exclusive Claude capability:

- **Cold review of consequential Codex-authored diffs.** Sol reviewing Astra, or Astra reviewing Sol, provides a different model but not a different vendor. The actual correlation of their errors is unmeasured here. Preserve the existing Claude boundary.
- **Independent review of Codex-authored proposals and consequential specs.** A fresh Codex context reduces priming, but does not establish independent validation of its own assumptions.
- **The additional error-path review for security, authentication, concurrency, and migrations.** Preserve the existing strong-Claude completeness pass while Codex produces these changes.
- **Premise verification and architectural ratification during initial adoption.** Codex may collect evidence and draft; Claude checks the consequential assumptions independently.
- **Qualification adjudication and exceptional escalation.** Claude or the owner resolves material disagreements, repeated failures, and proposed retirement of Claude assurance lanes.

Cross-vendor review is a useful design constraint, **not a guarantee of statistical independence or correctness**. Its value should be measured through unique confirmed findings.

There is no evidence-based reason to reserve all spec drafting, Graphify research, Dockerfile analysis, or harness documentation research permanently for Claude. Nor should Claude automatically control business priorities or authorize production actions; those remain with the owner.

The current repository already separates Codex implementation, Claude cold review, and Claude premise verification. [Existing routing boundary](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/CLAUDE.md:64)

## 4. Token economics estimate

### Per-role estimates

Using the prompt’s assumptions:

| Gross work displaced | Assumed Claude tokens avoided before overhead |
|---|---:|
| O 1–3: spec, advisor, premise or proposal assignment | 5K–30K |
| O 2–5: staleness or contract-testing assignment | 10K–50K |
| O 2–6: research, diagnosis, security or performance assignment | 10K–60K |
| O 3–10: implementation assignment | 15K–100K |
| S 1–3: scribing or operational supervision | 2K–15K |
| S 2–6: test-authoring assignment | 4K–30K |
| H 1–3: gate supervision | No supplied Haiku baseline; measure directly |

These estimates describe opportunities, not realized savings. “Full-context tokens per turn” is particularly uncertain: context size, cache hits, tool output, reasoning, and repeated turns can dominate.

A useful accounting identity is:

**Net Claude reduction = displaced Claude work − Claude dispatch/supervision − retained review − Claude rework − added listing overhead.**

For example, replacing six Opus work turns at an assumed 7.5K each displaces 45K tokens gross. If the new path consumes 15K in retained Claude supervision and review, the net reduction is 30K, or 67%. The Codex consumption is additional and must be counted separately.

The current statement that a Codex consult “costs no Claude tokens” is too broad: the five wrappers run on Haiku, and the plugin implementation/review wrappers run on Sonnet. Their reasoning, preflight, report handling, and parent interaction still use Claude. [Current wording](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/token-routing.md:6), [implementation wrapper](/Users/rmanaloto/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.21.0/agents/codex-implementer.md:1)

### Codex cost is separate from Claude displacement

The current published credit rates are:

| Model | Input / 1M tokens | Cached input / 1M | Output / 1M |
|---|---:|---:|---:|
| GPT-5.6 Sol | 100 credits | 10 credits | 500 credits |
| GPT-6 Astra | 250 credits | 25 credits | 1,250 credits |

At equal token volumes, Sol uses 40% of Astra’s listed credits. That does **not** establish savings against Claude subscriptions, or equal task quality and token consumption. The applicable plan and billing arrangement matter. [Current Codex pricing](https://learn.chatgpt.com/docs/pricing)

Measure input, cached input, output/reasoning usage where exposed, actual credits, elapsed time, retries, and accepted outcomes. Use **cost per accepted task**, not cost per invocation.

### Standing context and the 90% stop condition

The repository declares a **41,305-character** listing ceiling. Its recorded snapshot is **39,716 characters**, approximately **96.2%** of that ceiling. The requested 90% threshold is **37,174.5 characters**: the recorded snapshot already exceeds it by about **2,542 characters**. This snapshot may be stale; the fresh measurement failed during uv cache initialization. [Declared ceiling and recorded measurement](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/doctor.toml:152)

Therefore, **do not authorize net roster growth until current headroom is measured**. If the snapshot still holds, reduce listing cost first.

Further distinctions matter:

- The project collector counts names and descriptions, including enabled-plugin entries; it does not count entire agent bodies.
- Its collection covers Claude surfaces, not a complete measurement of native Codex context.
- Default doctor mode reports drift and exits zero. **`--strict` already exists** and returns failure on drift; use that before inventing another enforcement mechanism. [Collector](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/listing_budget.py:197), [doctor exit behavior](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/doctor.py:1285)
- Claude’s actual skill listing has its own truncation behavior. Compare the project estimate with `/context` and `/doctor`; moving details into another always-listed skill is not automatically a saving. [Claude skill-listing behavior](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short)

More agents can reduce coordinator context while increasing total tokens. Anthropic’s research system illustrates that tradeoff, but its published multipliers are not estimates for this repository. [Anthropic’s multi-agent research findings](https://www.anthropic.com/engineering/multi-agent-research-system)

## 5. Sequenced adoption plan

### Phase 1 — Establish the baseline and available headroom

Record the effective roster, loaded model/effort, permission settings, current listing measurement, and representative task costs.

Use the existing doctor with `--strict`; compare against the actual Claude listing. Resolve the 90% threshold before adding entries. Separate measured facts from defaults and prompt assertions.

**Exit:** A reproducible baseline, known available capacity, and explicit acceptance criteria.

### Phase 2 — Requalify the existing implementer on 0.154.0

Use the installed implementation lane on bounded real assignments covering:

1. A behavior change.
2. A regression test.
3. A refactor or dependency change.

Capture the actual Sol/xhigh runtime, file scope, verification evidence, process settlement, and commit ownership. Preserve Claude cold review. Include an expected-failure case that must remain failed.

**Exit:** Accepted changes with complete evidence; no silent fallback or fabricated success.

### Phase 3 — Qualify all five existing Codex lanes

Evaluate the Claude wrapper and native Codex route separately where both are intended for use.

| Lane | Required distinguishing case |
|---|---|
| Advisor | An attractive option invalidated by supplied evidence |
| Critic | A proposal that fails to catch its own motivating defect |
| Staleness auditor | A real stale claim alongside a valid project policy that must remain unflagged |
| Harness expert | Installed behavior that differs from older documentation |
| Operator | An underlying task that fails while its supervising process exits successfully |

Also test unavailable model, empty output, inaccessible evidence, and interrupted execution where relevant.

**Exit:** Correct outcomes, correct runtime attribution, and truthful failure handling. A well-written report alone does not qualify a lane.

### Phase 4 — Adopt one additional role per session

Recommended order:

1. Regression-test author.
2. CI diagnostician.
3. Dependency/currency engineer.
4. Graphify feature researcher.
5. Documentation and spec drafting.

Use the existing implementer for writing roles and bounded research dispatches for investigative roles. Introduce a dedicated agent only when repeated use demonstrates that its persistent contract improves outcomes enough to justify standing context.

**Exit per role:** Accepted real case, independent assessment, measured displacement, no new defect class.

### Phase 5 — Reduce wrapper overhead using native capabilities

Evaluate native Codex `worker`/`explorer` and explicit custom-agent configuration before building a new dispatcher.

The proposed target has four reusable execution shapes:

| Execution shape | Responsibilities carried by task-specific contracts |
|---|---|
| Writer | Implementation, tests, refactoring, migrations, documentation |
| Investigator | Diagnosis, currency, Graphify inventory, harness and staleness research |
| Reviewer / advisor | Cold review, proposal critique, architecture advice; routed by producer |
| Task operator | Exact repository task execution and evidence collection |

Preserve distinct output contracts even when they share an execution shape. Avoid collapsing specialist instructions into one vague general-purpose prompt.

Because Fable upstream is archived, compare native execution against its actual services: premise delivery, timeout handling, process settlement, evidence grading, and truthful failure reports. Preserve those outcomes before retiring the wrapper.

**Exit:** Equivalent observed behavior with lower supervisory cost. Any remaining custom mechanics need a written justification and the existing skill → mise task → Python architecture.

### Phase 6 — Move workflow volume, preserving independent checks

For `modernization-audit`, start by moving per-unit discovery to Sol. Retain Claude challenge of consequential retirement/refactor recommendations and final completeness.

Keep verification grouped by unit and lens. The workflow records the earlier failure where 420 findings multiplied into 1,260 verifier calls; changing models without bounding work would preserve that failure mode. [Recorded fan-out defect and current grouping](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/workflows/modernization-audit.js:124)

For `gated-implementation`, require the acceptance decision to inspect actual gate results, review coverage, findings, and the reviewed revision. For `graphify-refresh`, assess task completeness and graph state rather than accepting a returned array as success.

**Exit:** Lower cost per accepted workflow outcome without reduced coverage.

### Phase 7 — Retire qualified defaults and monitor regressions

Remove a Claude lane from routine discovery only after its replacement passes a predefined real-case suite and a monitored adoption period. Keep a documented fallback without duplicating every fallback in standing context.

“100% fidelity” should mean **100% of the named hard contracts passed in the evaluated cases**. No finite test set proves universal fidelity. Evaluate both the transcript and the resulting environment state, with independent grading. [Agent evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

**Stop conditions:**

- Listing reaches 90% of the declared ceiling, or current headroom is unknown before an addition.
- A replacement introduces a new defect class.
- Actual model, effort, permission, or evidence provenance cannot be established.
- A partial run or failed task is reported as success.
- Required independent review or coverage is lost.
- Cost per accepted task fails to improve over the agreed comparison window.

After a stop, return the affected responsibility to its prior route, reproduce the defect, and requalify the corrected replacement. Do not continue expanding adoption on the strength of aggregate green checks.

## 6. GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — agent definitions, workflows, listing collector, doctor, and execution reports.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — local harness documentation corpus.
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs) — offline Claude Code and Codex documentation; remote identity verified locally.
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — installed implementation/review contracts, supervisor, routing doctrine, and archival status.
- [openai/codex](https://github.com/openai/codex) — installed CLI and upstream product source.
- [mattpocock/skills](https://github.com/mattpocock/skills) — research methodology skill.

Additional primary sources were OpenAI’s model/configuration/pricing documentation and Anthropic’s Claude Code and agent-evaluation documentation.


