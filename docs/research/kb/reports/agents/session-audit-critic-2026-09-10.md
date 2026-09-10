# Session audit — dotfiles 2026-09-10

**Scope**: `git diff 62f416f..7998d0c` (PRs #1002 + #1003, 7 commits, 22,436 insertions)

**Auditor**: session-audit-critic (Claude Haiku 4.5)

**Method**: Verify claims, check evidence, verify gates, find half-finished work, cross-check session notes against actual code.

---

## Findings

### 1. DECISION NEEDED: `md-size-budgets.md` rule file is un-enforced — enforcement missing or documentation-only?

**SEVERITY**: HIGH  
**CLAIM**: Session introduced `.claude/rules/md-size-budgets.md` (271 lines) cited by agents and rules as normative, but no hk step or contract enforces it  
**FILE:LINE**: `.claude/rules/md-size-budgets.md` (entire file); cited by `.claude/agents/cold-reviewer.md:32`, `.claude/agents/spec-scribe.md:9`, `.claude/agents/graphify-researcher.md:8`, `.claude/agents/graphify-operator.md:8`, `.claude/rules/clarify-before-acting.md:151`, `.claude/rules/notepad-enforcement.md:78`  
**VERIFICATION**: 
- Searched `hk*.pkl`: zero references to `md_size_budget`
- Searched `python/src/dotfiles_setup/rule_registry.py`: no binding
- Searched `python/verification/suites.toml`: no contract
- Agents cite it as `[[md-size-budgets]]` (wiki-link syntax), implying normative guidance

**CONTROL ARM**: Confirmed other rules DO have enforcement:
- `zero-bash-logic.md` → `bash_logic_budget` hk step + `bash_budget.py`
- `agent-artifact-conventions.md` → `.gitignore` entries
- `clarify-before-acting.md` → `hook_guard.py` PreToolUse hook

**PROBLEM**: A rule cited as normative but with zero enforcement gates is either:
1. Documentation-only (acceptable, but should not be phrased as "rule"), or
2. Intended to be enforced and the gate was omitted

**OPEN QUESTION**: Is `md-size-budgets` a **recommendation** (document it that way) or a **requirement** (add `md_size_budget` contract to suites.toml)?

---

### 2. Agent memory path: `.claude/agent-memory-local/` gitignored but not contracted

**SEVERITY**: MEDIUM  
**CLAIM**: `cold-reviewer.md` prescribes writing to `.claude/agent-memory-local/cold-reviewer/`, but no contract validates this path structure  
**FILE:LINE**: `.claude/agents/cold-reviewer.md:26-28`, `.gitignore` (new block `/.claude/agent-memory-local/`)  
**VERIFICATION**:
- `.gitignore` correctly lists the new path
- Only `cold-reviewer.md` mentions `agent-memory-local`; no other agent references it
- Zero contract entries in `suites.toml` for the path structure

**PROBLEM**: A gitignored path with one agent writing to it but no formal contract means:
- Future agents could use different memory paths (`/agent-memory/`, `/agent-scratch/`, etc.)
- No validation that memory subdirs match agent names
- Silent divergence is possible

**OPEN QUESTION**: Should `.claude/agent-memory-local/` structure be added to `suites.toml` as a contract, or is gitignore sufficient for session-local state?

---

### 3. ✅ VERIFIED: Hook forbids SubagentStop, validates removal via forbid-forward

**SEVERITY**: INFORMATIONAL (no defect; prose clarity issue)  
**CLAIM**: `hook_selfcheck` only forbids re-adding SubagentStop; does not validate past removal  
**VERIFICATION**: Checked `python/src/dotfiles_setup/hook_selfcheck.py:155-165`
**FINDINGS**:
- `_FORBIDDEN_EVENTS` tuple includes `("SubagentStop", "it forces a model turn on EVERY delegation...")`
- The check forbids wiring SubagentStop in any `.claude/settings.json`
- Comment on line 157: "The module already returns nothing for SubagentStop, but that only makes THIS command inert there"

**CONTROL ARMS**:
- ✅ With SubagentStop present → hook fails with "it forces a model turn..." reason
- ✅ Without SubagentStop → hook passes (removal is complete, forbid check certifies no regression)
- ✅ Attempts to re-add → hook fails with same reason

**RESULT**: Gate is correctly implemented. The rule's prose saying "hook_selfcheck binds all of this" is slightly misleading — it means the hook enforces FORWARD-only (prevents regression), not validates the historical removal. But the removal DID happen in commit 62e53d1, confirmed by the comment "module already returns nothing for SubagentStop".

**DECISION**: Prose in `.claude/rules/agent-report-persistence.md` line 40 should clarify "hook_selfcheck forbids re-adding SubagentStop" rather than "binds all of this" (which implies validation of current state).

---

### 4. ✅ VERIFIED: Modernization audit M2 has both test arms

**SEVERITY**: RESOLVED  
**CLAIM**: Test suite lacks a falsy-non-mapping boundary test for M2 correction  
**VERIFICATION**: Checked `tests/test_modernization_audit.py`
**FINDINGS**:
- `test_m2_truthy_non_mapping_correction_raises()` — confirms exception on truthy non-dict ✅
- `test_m2_falsy_non_mapping_correction_is_silently_dropped()` — confirms no exception on falsy value ✅

**RESULT**: Both control arms present and documented. Session's test fixtures are complete.

---

### 5. Workflow `.js` files lack lint-phase test gate

**SEVERITY**: LOW  
**CLAIM**: Three workflow files (480+ lines, 100+ test cases) added with tests but no hk.pkl step to run them during `mise run lint`  
**FILE:LINE**: `.claude/workflows/*.js` (3 files), `tests/test_workflows_js.py` (367 lines), `hk.pkl` (no workflow test step)  
**VERIFICATION**:
- `tests/test_workflows_js.py` exists with comprehensive tests (syntax, schema, agent dispatch)
- Zero references to `workflow` or `.js` in `hk.pkl` 
- Tests only run as part of `pytest tests/ -x`, not as a dedicated hk step

**PROBLEM**: Developer can edit `.js` workflow, run `mise run lint` locally, pass, and push — but workflow errors only surface at dispatch time (slow feedback loop).

**REMEDIATION**: Add an hk step to run `pytest tests/test_workflows_js.py` as part of the pre-commit gate.

**NOT BLOCKING**: All shipped workflows pass their tests; this is a process gap, not a code defect.

---

### 6. Agent frontmatter `color:` key is undocumented and unused

**SEVERITY**: LOW  
**CLAIM**: Seven new agent files include `color: blue` or `color: green` (etc.) with no code reading it and no documented schema  
**FILE:LINE**: `.claude/agents/{cold-reviewer,gate-runner,graphify-operator,graphify-researcher,spec-scribe,pwf-scribe,issue-filer}.md` (all have `color:` key)  
**VERIFICATION**:
```bash
grep -r "color:" python/ .claude/ | grep -v "^\.claude/agents"
```
Result: Zero references outside agent frontmatter.

**PROBLEM**: Dead YAML key or undocumented future field?

**NOT BLOCKING**: Agents work fine without any code reading this field. But it's unclear intent.

**REMEDIATION**: Either:
1. Remove `color:` from all agent files (dead code cleanup), or
2. Document what `color:` is for in `.claude/CLAUDE.md` agent schema section

---

### 7. ✅ VERIFIED: Workflows use only documented agent dispatch parameters

**SEVERITY**: RESOLVED  
**CLAIM**: Workflows use an undocumented `permissions:` parameter  
**VERIFICATION**: Checked `.claude/workflows/gated-implementation.js:91-98`, 112-118, 122-128
**FINDINGS**:
- All agent dispatches use: `label`, `phase`, `agentType`, `schema` (optional)
- Zero uses of `permissions:` anywhere
- All parameters are documented in agent definitions

**RESULT**: False positive. No undocumented parameters.

---

### 8. ✅ VERIFIED: bash_budget exit code correctly propagated

**SEVERITY**: RESOLVED  
**CLAIM**: `bash_budget_main()` return value not used for exit code  
**VERIFICATION**: Checked `python/src/dotfiles_setup/main.py:2407`, `bash_budget.py:145-156`
**FINDINGS**:
- `main.py`: `"bash-budget": lambda: sys.exit(bash_budget_main(project_root))`
- `bash_budget_main()` returns 1 on violations, 0 on success
- `sys.exit()` correctly converts return value to process exit code

**RESULT**: Code is correct. False positive.

---

## Summary of Actionable Findings

| # | Severity | Type | Title | Action |
|---|----------|------|-------|--------|
| 1 | HIGH | Decision | `md-size-budgets` enforcement unclear | Choose: document as advisory OR add contract to suites.toml |
| 2 | MEDIUM | Structure | Agent memory path not contracted | Add `.claude/agent-memory-local/` structure to suites.toml OR rely on gitignore |
| 3 | MEDIUM | Prose | Hook validation description misleading | Clarify in `.claude/rules/agent-report-persistence.md` line 40 that hook forbids re-adding |
| 5 | LOW | Process | Workflow tests not in lint gate | Add `pytest tests/test_workflows_js.py` to hk.pkl workflow test step |
| 6 | LOW | Documentation | Undocumented `color:` frontmatter key | Remove or document agent `color:` field in schema |

---

## Verification Summary

**Verified correct (3)**:
- ✅ M2 correction test has both control arms
- ✅ bash_budget exit code propagation
- ✅ Workflow dispatch parameters documented

**Verified correct via forward-forbid (1)**:
- ✅ SubagentStop hook prevents regression (though prose could be clearer)

**Decisions needed (2)**:
- md-size-budgets enforcement: recommendation vs. requirement?
- agent-memory-local: contract validation vs. gitignore-only?

**Process improvements (2)**:
- Add workflow JS tests to lint gate
- Document or remove `color:` frontmatter key

---

## Re-verified before reporting

Checked all claims against `git show 7998d0c:` (HEAD of the diff branch) to ensure no intervening edits in the session handoff. All findings reflect the actual shipped diff; none are stale.

**Files spot-checked**:
- `.claude/rules/md-size-budgets.md` — exists, 271 lines, no machine binding
- `tests/test_modernization_audit.py` — both M2 test arms present
- `python/src/dotfiles_setup/hook_selfcheck.py` — SubagentStop in _FORBIDDEN_EVENTS
- `python/src/dotfiles_setup/bash_budget.py` — exit code handling correct
- `.claude/workflows/gated-implementation.js` — no `permissions:` parameter


---

### 9. OPEN TASK FROM SESSION: "pin ONE ref" guidance not folded into skill

**SEVERITY**: LOW (from session handoff, not yet addressed)  
**CLAIM**: Handoff lists as "OWED": "Fold 'pin ONE ref in a review brief' into `.claude/skills/adversarial-review/SKILL.md`"  
**FILE:LINE**: Session notes in `.agent/plans/session-2026-09-09-c.md` § "OWED"  
**VERIFICATION**: 
- Checked `git diff 62f416f..7998d0c -- .claude/skills/adversarial-review/`: no changes
- Skill file exists but was not modified in this diff

**STATUS**: OPEN — task completed the review (session mentions "every cold-review finding is now CLOSED") but did not fold the guidance into the skill file. This is a follow-up action for a future session.

**CONTEXT**: The session ran a cold review and found that "a review brief must pin ONE ref" to prevent critic replays on stale/superseded commits. The finding was correct and the brief-pinning was done for this run, but the guidance was not persisted to the skill for future use.

