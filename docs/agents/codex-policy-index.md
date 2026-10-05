---
name: codex-policy-index
description: Explicit policy read map for Codex sessions in this repository.
---

# Codex policy index

This is the explicit policy bridge for the root `AGENTS.md`. Before any work,
READ this index, all eager policies below in order, and the scoped policies
matching files you intend to read, create or edit. Open each target explicitly.
Markdown links are pointers; they do not inject their targets into Codex context.
Canonical rule files remain authoritative; this index does not replace them.

## Eager policies — READ before work

1. [Do Not — Project Invariants](../../.claude/rules/do-not.md) — READ the full rule.
2. [Zero-Skip Policy: No Warning/Error/Issue Shall Be Dismissed](../../.claude/rules/zero-skip-policy.md) — READ the full rule.
3. [Probes Need a Control Arm: A Check That Can Only Pass Is Not a Check](../../.claude/rules/probes-need-a-control-arm.md) — READ the full rule.
4. [Verify Before Advancing: All Applicable Checks Green First](../../.claude/rules/verify-before-advancing.md) — READ the full rule.
5. [Clarify Before Acting: Ask Until Sure on Ambiguous Work](../../.claude/rules/clarify-before-acting.md) — READ the full rule.
6. [Agent Artifact Conventions: Where Working Files Go](../../.claude/rules/agent-artifact-conventions.md) — READ the full rule.
7. [Notepad Enforcement: Persist Findings While They Are Fresh](../../.claude/rules/notepad-enforcement.md) — READ the full rule.
8. [Agent Report Persistence: Verbatim, At Receipt](../../.claude/rules/agent-report-persistence.md) — READ the full rule.
9. [Zero-Bash-Logic: No New Bash, No Growth of Existing](../../.claude/rules/zero-bash-logic.md) — READ the full rule.
10. [Research Existing Tools/Services Before Building Custom](../../.claude/rules/use-tool-builtins.md) — READ the full rule.
11. [Tool Currency & Native-First: Research Release Notes Before Building or Keeping Custom Code](../../.claude/rules/tool-currency-and-native-first.md) — READ the full rule.
12. [Research Doc Sources: Preference Chain](../../.claude/rules/research-doc-sources.md) — READ the full rule.
13. [Research Repo Enumeration: List Every Touched Repo](../../.claude/rules/research-repo-enumeration.md) — READ the full rule.
14. [Graphify First](../../.claude/rules/graphify-first.md) — READ the full rule.
15. [Real Integration Evidence](../../.claude/rules/real-integration-evidence.md) — READ the full rule.
16. [Secrets in the Shell Environment](../../.claude/rules/secrets-out-of-the-shell-env.md) — READ the full rule.
17. [AI CLI Invocation Policy](../../.claude/rules/ai-cli-invocation.md) — READ the full rule.
18. [The codex SDLC Team: Six Specialists codex Itself Orchestrates](../../.claude/rules/codex-sdlc-team.md) — READ the full rule.
19. [Mise Tasks Only: No One-Off Commands for Canonical Workflows](../../.claude/rules/mise-tasks-only.md) — READ the full rule.
20. [Clean Git State Before Validation](../../.claude/rules/clean-git-state.md) — READ the full rule.
21. [Local-First: Reproduce the Failure Locally Before Spending a CI Round-Trip](../../.claude/rules/local-devcontainer-first.md) — READ the full rule.
22. [Long-Running Commands: Never Run Blind — Bound Every Run](../../.claude/rules/long-running-command-hangs.md) — READ the full rule.
23. [gh CLI: Auto-Merge and land Own CI Waits; Read State One-Shot](../../.claude/rules/gh-cli-watch.md) — READ the full rule.
24. [Append-Only Goal History](../../.claude/rules/goal-history.md) — READ the full rule.
25. [Persistence Gate: Retry Once on Transient DNS](../../.claude/rules/persistence-gate-retry.md) — READ the full rule.

Also READ [.claude/CLAUDE.md](../../.claude/CLAUDE.md) for provider context,
canonical orchestration routing, guard limitations and project registrations.
Preserve root and nested `CLAUDE.md` import stubs: W0 retains the current
`@AGENTS.md` route and AGENTS/CLAUDE pair contracts.
Read the applicable nested `AGENTS.md` before work in `.devcontainer/`,
`.github/workflows/`, `python/`, `python/src/dotfiles_setup/` or `tests/`.
The absence of Codex hook enforcement does not waive these repository policies.

## Scoped policies — READ before matching file work

These are the complete current `paths:`-scoped rule set. Treat an intended read,
creation or edit matching any pattern as a read trigger; re-read after context loss.
If a new rule is added, inspect its frontmatter and maintain this map in that change.

| Canonical rule | Exact paths | Read condition |
|---|---|---|
| [ci-local-parity](../../.claude/rules/ci-local-parity.md) | `.github/workflows/*.yml`, `hk.pkl`, `mise.toml`, `.devcontainer/mise-system.toml` | Before matching workflow, hook or tool configuration work; preserve CI/local check parity. |
| [md-size-budgets](../../.claude/rules/md-size-budgets.md) | `hk.pkl`, `**/CLAUDE.md`, `**/AGENTS.md`, `.claude/rules/*.md`, `.claude/skills/**/SKILL.md` | Before matching instruction, rule, skill or budget configuration work; measure load-class lines/bytes and every AGENTS.md character limit. |

## Canonical skills and orchestration

Codex project skills are generated under `.agents/skills/`; author changes in
`.claude/skills/`, then run `mise run skills-mirror` and
`mise run skills-mirror -- --check`. Never hand-edit mirrors or create a third corpus.
Names/descriptions support discovery; READ a relevant skill's full `SKILL.md`
before following its workflow. A skill listing is discovery evidence, not proof
that the full skill or any rule reached context.

| Purpose | Codex entrypoint | Authoritative source |
|---|---|---|
| Implementation routing and review tiers | [codex-sdlc-team](../../.agents/skills/codex-sdlc-team/SKILL.md) | [.claude/skills/codex-sdlc-team/SKILL.md](../../.claude/skills/codex-sdlc-team/SKILL.md) |
| Coordinator transfer and card snapshot | [coordinator-handoff](../../.agents/skills/coordinator-handoff/SKILL.md) | [.claude/skills/coordinator-handoff/SKILL.md](../../.claude/skills/coordinator-handoff/SKILL.md) |
| Session handoff | [session-handoff](../../.agents/skills/session-handoff/SKILL.md) | [.claude/skills/session-handoff/SKILL.md](../../.claude/skills/session-handoff/SKILL.md) |
| Gated delivery | [pr-workflow](../../.agents/skills/pr-workflow/SKILL.md) | [.claude/skills/pr-workflow/SKILL.md](../../.claude/skills/pr-workflow/SKILL.md) |

READ [session orchestration](session-orchestration.md) for shared Claude/Codex
recovery, cards, ship queue, SLOT GO and hand-back. Codex coordinator plan/queue
writes are **blocked until B2**; a handoff or newest session never grants authority.

## Instruction budgets and load proof

Root `AGENTS.md` must remain at most 12,000 Unicode characters; its received
UTF-8 bytes also need to fit the runtime `project_doc_max_bytes` budget together
with other selected instruction files. These are different measurements.
The primary Codex loader chooses an instruction candidate per directory;
`project_doc_fallback_filenames` supplies alternatives, not an additive rule loader.
See the [adopted design](../specs/codex-takeover-phaseB-design.md#w5a--explicit-policy-bootstrap-proposed)
and [pinned primary loader](https://github.com/openai/codex/blob/823ea830c0fd418b09ff02d36cad9a1fff66465b/codex-rs/core/src/agents_md.rs).

A runtime proof must use a fresh isolated, persisted Codex session, record its
actual byte limit, eager and matching scoped-rule reads, and a discovered project
skill. Its removed-bootstrap control must lose the asserted policy load evidence.
Record blockers or truncation honestly; file existence, links, configuration
schema defaults and synthetic markers are insufficient runtime evidence.

## Key Files

| File | Purpose |
|------|---------|
| `mise.toml` + `.config/mise/conf.d/shared.toml` | Host tool versions + tasks; the tools shared with the image (hk, pkl, linters, python, uv, chezmoi, bun) live in the exact-pinned shared fragment both host and image merge (#160 T5) |
| `mise.lock` | Locked tool versions for reproducible installs |
| `mise.local.toml` | Gitignored per-clone overrides (e.g., `BASE_IMAGE`). See `mise.local.toml.example` |
| `hk.pkl` | Project git hook config; imports `hk-common.pkl`; enforces `no_lint_skip`, `require_pipefail`, `bash_logic_budget`, `claude_md_import_stub`, `claude_agents_md_pairs` |
| `hk-common.pkl` | Shared step definitions (hygiene, safety, security, typos) reused by `hk.pkl` and `hk-image.pkl` |
| `hk-image.pkl` | Image-only hook config for devcontainer validation |
| `docker-bake.hcl` | BuildKit bake config (`dev`, `dev-load` build targets + `base`/`p2996-cache` CI stages); `IMAGE_REF` consolidates registry+image |
| `renovate.json` · `currency.toml` · `rule-sync.toml` | Declarative sets: Renovate deps; deep-tracked tools (`mise run tool-currency`); the cross-repo shared set (`mise run rule-sync`, #354) |
| `AGENTS.md` | Agent-agnostic project instructions (this file) |
| `CLAUDE.md` | Thin `@AGENTS.md` import stub for Claude Code |
