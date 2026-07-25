# Deep Interview Spec: Local Validation Gate

## Metadata
- Rounds: 4
- Final Ambiguity Score: 11%
- Type: brownfield
- Generated: 2026-04-05
- Threshold: 20%
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.95 | 35% | 0.333 |
| Constraint Clarity | 0.85 | 25% | 0.213 |
| Success Criteria | 0.85 | 25% | 0.213 |
| Context Clarity | 0.90 | 15% | 0.135 |
| **Total Clarity** | | | **0.893** |
| **Ambiguity** | | | **10.7%** |

## Goal
Prevent CI failures that could have been caught locally by enforcing maximum local validation before git commit/push, closing local/CI environment divergence gaps, and blocking known anti-patterns (npx for mise tools) via `.claude/rules/` and Claude Code hooks.

## Constraints
- Enforcement via `.claude/rules/` (path-scoped and unconditional) + Claude Code hooks
- `.claude/rules/` triggers on file reads, NOT on events — use hooks for event-based enforcement
- hk pre-commit already has 40+ checks; do NOT duplicate, just ensure they run
- Zero-skip policy applies: never suppress hk failures without research + human approval
- Use mise binary names exclusively; block `npx` via Claude Code PreToolUse hook

## Non-Goals
- Running CI in Docker locally (too heavy)
- Fixing pre-existing contract-preflight failures (Phase 2 scope)
- Adding new linters beyond what hk.pkl already has
- Modifying hk.pkl or ci.yml (already correct from previous session)

## Acceptance Criteria
- [ ] `.claude/rules/local-validation-gate.md` created (unconditional rule)
  - Enforces `hk run pre-commit --all --stash none` before every git commit
  - Enforces `hk run pre-push --all` validation awareness before push
  - Requires research before escalating any hk failure to human
- [ ] `.claude/rules/ci-local-parity.md` created (path-scoped: ci.yml, hk.pkl, mise.toml)
  - Every `run:` in ci.yml lint job must have corresponding hk step
  - Every tool in hk `check` commands must be in mise.toml
  - Use mise binary names, never npx for mise-installed tools
- [ ] `.claude/rules/clean-git-state.md` created (unconditional rule)
  - Verify no unstaged deletions/modifications before committing
  - All file operations must be staged before running hk
- [ ] Claude Code hook added to block `npx` in Bash tool (PreToolUse hook)
- [ ] All rules pass `hk run pre-commit --all --stash none` locally
- [ ] CLAUDE.md updated to reference new rules

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| hk checks catch everything | Local env differs from CI (global tools, uncommitted deletions) | Close divergence gaps via rules + clean git state |
| npx is fine for mise tools | npx re-downloads in CI, bypasses mise binary | Block npx via hook, use binary names |
| CI failures are random | All 5 failures had specific local-catchable root causes | Systematic prevention via 3 rules + 1 hook |
| .claude/rules can trigger on events | Rules only trigger on file paths | Use hooks for event-based enforcement, rules for file-scoped guidance |

## Technical Context
### Existing Infrastructure
- `hk.pkl`: 40+ pre-commit builtins including agnix, pinact, pinact_update
- `mise.toml`: 19 tools including pinact, agnix, devcontainer CLI
- `.claude/rules/zero-skip-policy.md`: existing unconditional rule (no skip/suppress)
- `.claude/rules/ai-cli-invocation.md`: existing unconditional rule (CLI patterns)

### Root Causes Addressed
1. **CI checks not mirrored locally** → ci-local-parity.md (path-scoped)
2. **Global tools masking project gaps** → ci-local-parity.md (mise.toml completeness)
3. **Dirty git state** → clean-git-state.md (stage all changes first)
4. **npx anti-pattern** → Claude Code PreToolUse hook + ci-local-parity.md

### CI Failure Evidence (from 2026-04-05 session)
| CI Run | Error | Root Cause | Prevention |
|--------|-------|-----------|------------|
| ddbe42e | devcontainer CLI not found | Tool not in mise.toml | ci-local-parity rule |
| bbbde7a | agnix --strict errors | CI-only check not in hk | ci-local-parity rule |
| aa38231 | agnix config missing | No .agnix.toml exclusions | Already fixed |
| 47ca7a6 | Uncommitted deletion masked error | Dirty git state | clean-git-state rule |
| ad3de40 | npx re-downloads in CI | npx bypasses mise binary | PreToolUse hook |

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| hk check | core tool | builtins, check commands, glob patterns | Runs pre-commit/pre-push hooks |
| CI environment | external system | GHA runner, mise.toml-only tools, clean checkout | Runs same hk checks as local |
| Local environment | external system | macOS, global mise config, working tree state | Must match CI for checks to be equivalent |
| mise.toml | config | tools, settings, tasks | Defines project tool manifest for CI |
| git state | concept | staged, unstaged, committed, deleted | Divergence between local/CI |
| .claude/rules/ | config | path-scoped, unconditional, YAML frontmatter | Loaded on file read or session start |
| Claude Code hook | enforcement | PreToolUse, Bash matcher, command block | Blocks npx in Bash tool |
| .agnix.toml | config | tools, exclude patterns | Scopes agnix validation |

## Deliverables
1. `.claude/rules/local-validation-gate.md` — unconditional
2. `.claude/rules/ci-local-parity.md` — path-scoped (ci.yml, hk.pkl, mise.toml)
3. `.claude/rules/clean-git-state.md` — unconditional
4. Claude Code PreToolUse hook in `.claude/settings.json` — blocks npx
5. CLAUDE.md update — reference new rules

## Interview Transcript
<details>
<summary>Full Q&A (4 rounds)</summary>

### Round 1
**Q:** Should the solution focus on a Claude Code hook, CLAUDE.md policy, or both?
**A:** "Why won't it work as hk check?" — User wants hk to be the enforcement layer.
**Ambiguity:** 56% (Goal: 0.6, Constraints: 0.3, Criteria: 0.2, Context: 0.7)

### Round 2
**Q:** Which fix approach: CI-equivalent local, close divergence gaps, or divergence gate?
**A:** "All three, but use hk builtins for git state. Review the GHA errors and think about if each could have been caught locally."
**Ambiguity:** 35% (Goal: 0.8, Constraints: 0.5, Criteria: 0.5, Context: 0.8)

### Round 3
**Q:** Confirm deliverable list: 3 rules for validation gate, CI parity, and clean git state.
**A:** "Yes all three. Also create .claude/rules with path triggers. Don't allow skipping hk failures without research + human interview."
**Ambiguity:** 20% (Goal: 0.9, Constraints: 0.7, Criteria: 0.7, Context: 0.9)

### Round 4
**Q:** Confirm exact deliverables with the npx hook addition.
**A:** "Yes, but add a Claude lifecycle hook to prevent npx from ever being used in Bash tool."
**Ambiguity:** 11% (Goal: 0.95, Constraints: 0.85, Criteria: 0.85, Context: 0.9)

</details>
