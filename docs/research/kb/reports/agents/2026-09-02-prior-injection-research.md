# Prior Research: Context Injection, De-duplication, and Hook State

Ground truth sources: session memory files, prior research artifacts, git history, GitHub issues, hook implementation code

**Status: incremental findings as of 2026-09-02**

## 1. Planning-with-Files Injection De-duplication

### Measured facts

**Source:** `project_session_2026-08-31` (Lane D measurement)

- **Cold-start injection overhead:**
  - Legacy PWF mode: **4,016 B** per turn start
  - Autonomous inject-smart mode: **2,858 B** per turn start (30% reduction)
  - Per-tool-call overhead: legacy **1,520 B** → autonomous **0 B** (fully eliminated)

- **State key:** autonomous inject-smart mode keys de-duplication on `.mode` file presence (tracked, reviewed project setting)

- **Attestation requirement:** Autonomous mode refuses to inject an UNATTESTED plan (`inject-plan.sh:986-991`); every plan edit requires re-attestation

**Quote:** "~285,000 B off this session's shape" (commit d20b035 on branch chore/pwf-autonomous-inject-smart, unshipped; all gates green)

### Three plugin facts from code inspection

1. ⚠️ **The completion gate arms on SUBSTRING match** (`inject-plan.sh:837`, `grep -q 'gate'`) — any occurrence enables it, including inside "delegate" or a comment. Recommendation: keep `.mode` free of that substring.

2. ⚠️ **Gated mode has an oracle split** (`inject-plan.sh` attestation path vs Stop hook path). Injection checks attestation; Stop path does not. A tampered plan reports `PLAN TAMPERED` to injection and `ALL PHASES COMPLETE` to Stop. Locked decision: **gated mode stays OFF**.

3. ⚠️ **Attestation state is mandatory for autonomous mode only.** Without `attest-plan.sh`, body silently stops being injected — flagged but UNVERIFIED whether this bites in practice.

### Prior decision: autonomous inject-smart shipped

**Commit:** d20b035 on branch `chore/pwf-autonomous-inject-smart` (not yet pushed to main as of 2026-08-31)

**Status:** Green gates (lint/pytest/verify). The mode was never the "big lever" — Lane A measured only 3 items DUPLICATED against 42 UNIQUE across all plugin injection. Total plugin replacement value: ~59 KB of same-clone handoff/resume overhead.

**Comparison to native harness:** Lane C found comparable/better alternatives in native harness (`--continue`/`--resume`, Remote Control) plus two real supersessions: `SubagentStop`/`TeammateIdle` hooks + `claude plugin eval` (18,506 B).

### Real instruction-surface mass is elsewhere

- **Verification surface:** 297,946 B (neither plugin-related)
- **Orchestration stack:** 179,014 B (neither plugin-related)

**Source:** Lane C of 2026-08-31 session explicitly refused to retire: requirement/evidence closure, semantic command guard, doc-refs, memory-index curation, verification contracts.

### GitHub issue #283 — context injection scoping

**State:** OPEN

**Title:** "context: 15 unscoped .claude/rules/*.md load every session (~16k est. tok); paths: frontmatter already proven on 4"

**Finding:** 15 unscoped rules, 4 already proven to work with `paths:` frontmatter

---

## 2. Rule Scoping and Eager Context Budget

### Measurement session 2026-08-31 — Lane D

**Cold-start instruction overhead:** 157,575 bytes = **19.70%** of a 200k-token window

- Margin to degradation threshold: **2,425 bytes** (at 4 bytes/token assumption)
- With planning file present: 20.19% (over threshold)

**Key finding:** "The plugin was never the big lever" — only 59 KB of overlap with native harness alternatives.

### Top-five eager cuts identified

**Total savings if implemented: 34,346 B** (cold start 19.70% → ~15.40%)

| Cut | Bytes | Strategy |
|---|---:|---|
| `research-doc-sources.md` → auto-relevant research | 8,258 | Move case history to `docs/rules-evidence/` |
| `mise-tasks-only.md` → directive + task map | 7,166 | Move enforcement layers to `docs/rules-evidence/` |
| `probes-need-a-control-arm.md` → keep judgment, move casebook | 7,139 | Move case tables to `docs/rules-evidence/` |
| `secrets-out-of-the-shell-env.md` → current posture only | 6,873 | Move historical context to `docs/rules-evidence/` |
| `.claude/CLAUDE.md` → strip reference inventories | 4,910 | Move registry/inventory to tracked file |

**Source:** project_session_2026-08-31, Lane D report with line-level block anchors

**Commit:** `91ab945` "perf(context): trim the top-five eager instruction files, 12,591 B (#880)" — **partial implementation**, 12.6 KB actually cut (leaves ~21.7 KB of the 34.3 KB uncut)

### Prior decision: eager rules remain unscoped

**Locked decision** (project_session_2026-08-31): No paths-scoping of rules; gated mode stays OFF; no other skill can safely take `disable-model-invocation: true`

**Rationale:** "Scoped to `.devcontainer/**`/`.claude/**` until 2026-07-15, which meant validating after a python-only edit never loaded it" — scoped rules are absent exactly when needed. `md-size-budgets.md` documents the "trigger test."

### Existing pattern: `md-size-budgets.md` and `docs/rules-evidence/`

**Pattern established:** Move case history, archaeology, and worked examples out of eager rules into tracked `docs/rules-evidence/` siblings

- One `<rule>.md` per `.claude/rules/<rule>.md`
- Rule keeps directive, operative constraints, and one canonical worked example
- Cross-repo citations resolve to `docs/rules-evidence/` (not external links)

**Commits implementing this pattern:**
- (search findings pending)

---

## 3. Existing Hook State Conventions

### Session state storage — current implementation

**Files found:**
- `python/src/dotfiles_setup/session_ledger.py` — ledger of sessions
- `python/src/dotfiles_setup/session_review.py` — review contracts
- `python/src/dotfiles_setup/classifier_tables.py` — classification state
- `python/src/dotfiles_setup/workflow_hooks.py` — hook workflow state

**Canonical directory:** `.agent/state/sessions/{id}/` (gitignored, swept by `git clean -xdf`)

**Verification needed:** Exact state key structure, per-turn vs per-session scope, and any known failure modes

---

## 4. GitHub Issues on Injection, Scoping, and Context Budget

### Issue #283 — Unscoped rules loading every session

**State:** OPEN

**Link:** #283

**Quote:** "context: 15 unscoped .claude/rules/*.md load every session (~16k est. tok); paths: frontmatter already proven on 4"

### Issue #640 — md_size_budget measurement defect

**State:** OPEN

**Title:** "md_size_budget measures `description` alone: the installed kb-setup pin predates its own when_to_use fix"

### Issue #570 — Clarify-before-acting escalation

**State:** OPEN

**Title:** "Add the escalation clause to `clarify-before-acting`"

### Issue #566 — Cold-start token cost measurement

**State:** OPEN

**Title:** "Measure the cold-start token cost of a lean DAG node"

### Issue #577 — Context-gate threshold and restart contract

**State:** OPEN

**Title:** "Grill the context-gate threshold and the restart contract"

### Issue #576 — Budget guardrails and concurrency caps

**State:** OPEN

**Title:** "Grill budget guardrails and fan-out concurrency caps"

---

## 5. Git History — paths: Frontmatter and Rules-Evidence Moves

### Commit 91ab945 — "perf(context): trim the top-five eager instruction files, 12,591 B (#880)"

**What:** Partial implementation of Lane D cuts. Only 12.6 KB of 34.3 KB identified cuts.

**Followed by:** Commit `638739f` (same message, earlier)

### Commit 8aa893e — docs(audit): persist the four-lane plugin and maintenance audit

**What:** Persisted the 2026-08-31 session's four-lane audit reports to `docs/research/kb/reports/agents/2026-08-31-lane{A,B,C,D}-*.md`

---

## Summary of Prior Conclusions

### Decisions that must be honoured

1. **Autonomous inject-smart mode (pwf)** — proven effective (30% turn-start reduction), still unshipped on d20b035; gated mode stays OFF
2. **No paths-scoping of rules** — scoped rules are absent when needed; eager corpus stays eager
3. **md-size-budgets.md pattern established** — move casebook to `docs/rules-evidence/`, keep directive in eager rule

### Measurements available for reuse

1. **Cold-start instruction surface:** 157,575 B = 19.70% of 200k window (2,425 B margin)
2. **Top-five cuts identified:** 34,346 B opportunity (only 12.6 KB implemented)
3. **PWF injection overhead:** 4,016 B (legacy) → 2,858 B (autonomous), per-tool 1,520 B → 0 B

### Unimplemented proposals in the repo

1. **The remaining 21.7 KB of Lane D cuts** (34.3 - 12.6 = 21.7 KB) still uncut
2. **Path-scoping rules behind explicit frontmatter flag** — flagged as contradicting prior locked decision
3. **Parity check across Codex surface** — not yet researched

### Contradiction flags for the forming plan

**PLAN NOW FORMING:** path-scope the rule corpus, keep some rules eager behind explicit frontmatter flag with stated reason, target ~halving 127KB eager corpus, gate in hk, apply same classification to Codex surface

**PRIOR LOCKED DECISION THAT CONTRADICTS:** "Scoped rules are absent exactly when needed" (2026-07-15 evidence in md-size-budgets.md); "Gated mode stays OFF" (pwf attestation oracle split concern)

**ACTION REQUIRED:** Review whether the new plan's frontmatter flag + stated-reason mechanism resolves the earlier trigger-test failure, or whether the locked decision remains binding.

---

## Next findings to gather

- [ ] Exact session_ledger.py state-key structure (per-turn vs per-session scope)
- [ ] Any documented failure modes in hook state management
- [ ] Full set of commits implementing `docs/rules-evidence/` pattern
- [ ] Whether `disable-model-invocation: true` remains unavailable for new skills
- [ ] The trigger-test evidence in md-size-budgets.md (full quote)

---

## FINDING 2: THE TRIGGER-TEST EVIDENCE (Critical for forming plan)

**Source:** `.claude/rules/md-size-budgets.md` lines 132-150 (CONTROL-ARMED in same file)

### The rule for safe scoping

Path-scoped rules "trigger when Claude **reads** files matching the pattern". So scoping is safe only when the rule's trigger genuinely *is* reading a file.

Three trigger classes:

1. **File-triggered → safe to scope**
   - Examples: `ci-local-parity` (you read the workflow before editing), `md-size-budgets` itself
   - The rule loads because Claude is already reading a matching file

2. **Behaviour-triggered → MUST stay eager**
   - Examples: `zero-skip-policy`, `clean-git-state`, `do-not`, `verify-before-advancing`, `clarify-before-acting`, `probes-need-a-control-arm`
   - **Key quote:** "No glob predicts a decision"
   - These fire when a decision is about to be made, not when a file is read
   - If scoped, the rule would be absent exactly when needed (the decision happens without triggering a file read)

3. **Creation-triggered → CANNOT be scoped**
   - Examples: `zero-bash-logic` (governs *new* files), `agent-artifact-conventions` (governs *where to create*)
   - **Key quote:** "You never read the file first, so the rule would be absent exactly when it is needed"

### Why scoped rules failed in 2026-07-15

**Quote from md-size-budgets.md (lines 136-138):**
> "When it was scoped to `.devcontainer/**`/`.claude/**` until 2026-07-15, which meant validating after a python-only edit never loaded it" — this proves the failure mode: editing Python files outside the scoped paths means the rule never loads, even when you're about to run validation.

### The critical question for the forming plan

**The forming plan proposes:** path-scope rules, keep some behind explicit frontmatter flag with stated reason, target ~halving 127KB eager corpus.

**The trigger-test says:** only file-triggered rules can be safely scoped. Behaviour-triggered rules MUST stay eager or they are absent exactly when needed.

**Resolution path:** If the frontmatter flag controls whether a rule is INCLUDED in the eager load, it solves the problem. If it is only for documentation (rule is always included, flag just documents why), it solves nothing and is cargo-cult compliance.

**This is the hardest constraint the forming plan faces.** The test must pass: a rule kept eager via frontmatter flag should still be loadable to ALL sessions (or sessions whose behaviour might trigger it), not just those editing the flagged paths.

---

## FINDING 3: Hook State Conventions — partial findings

**Files discovered:**
- `python/src/dotfiles_setup/session_ledger.py` — session ledger (review/requirement tracking)
- `python/src/dotfiles_setup/session_review.py` — review contracts for transcript mining
- `python/src/dotfiles_setup/workflow_hooks.py` — hook workflow orchestration
- Canonical directory: `.agent/state/sessions/{id}/` (gitignored)

**First 100 lines of session_ledger.py:** The file is about "requirement and promise review" — mining command shapes from transcripts and normalizing between Claude JSONL and Codex JSONL. This is **not** the per-turn de-duplication state for injection.

**Verification needed:** Where does the PWF plugin store turn-level state? Is there a separate `~/.local/state/dotfiles/` directory or `.agent/state/` path that tracks which plans have already been injected this turn?

---

## Contradiction Found: two rules with contradictory scope guidance

### Rule 1: `md-size-budgets.md` (paths-scoped) — "File-triggered rules can be scoped; behaviour-triggered MUST stay eager"

### Rule 2: `ai-cli-invocation.md` (eager, no paths)

**Status:** Reviewed and consistent. This rule has **no paths** because its trigger is **behaviour-based** (invoking external AI CLIs from Bash) — covers Codex/Gemini/OpenCode invocation patterns. The rule fires by behaviour (calling a CLI), not by file-read, so scoping would make it absent when a developer hand-rolls a codex command outside the scoped paths.

No contradiction here — the evidence supports eager inclusion.

---

## Current State Summary

### Locked decisions (MUST be honoured)

1. Autonomous inject-smart mode (unshipped, d20b035) — 30% per-turn savings proven
2. Gated mode stays OFF (pwf attestation oracle split)
3. No paths-scoping of rules (trigger-test failure on 2026-07-15)
4. md-size-budgets.md pattern: move casebook to `docs/rules-evidence/`, keep directive eager

### Measurements available

1. Cold-start: 157,575 B = 19.70% of 200k window (margin: 2,425 B)
2. Top-five cuts: 34,346 B opportunity (12.6 KB implemented, 21.7 KB uncut)
3. PWF overhead: 4,016 B → 2,858 B (30% reduction)

### Hard constraints on forming plan

1. **Behaviour-triggered rules CANNOT be scoped.** Path-scoping makes them absent when needed.
2. **Frontmatter flag must GATE inclusion, not just document it.** Documenting "why eager" without controlling load is cargo-cult.
3. **The trigger-test must pass.** Read `.claude/rules/md-size-budgets.md` lines 132-150 before finalizing the frontmatter flag design.

