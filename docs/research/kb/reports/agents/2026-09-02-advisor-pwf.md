# Advisory Verdict: PWF Refactor Proposal (D1–D6)

**Author:** codex-advisor  
**Reviewed:** pwf-refactor-draft.md + supporting evidence (upstream-audit, pwf-codex-hooks, codex-install-review, review-attest)  
**Status:** VERDICT COMPLETE — read in full before acting.

---

## Per-Decision Verdicts

### D1 — Adopt slug mode  
**Status:** ⚠️ **AMEND** — condition the approval on resolving the worktree boundary question.

**The risk:** Slug mode does NOT solve the concurrency hazard at the isolation boundaries the draft identifies. The draft correctly names three defects:
1. `.active_plan` is overwritten unconditionally by `init-session.sh:369` — creating plan B repoints every unpinned agent
2. An INVALID `PLAN_ID` falls through silently (resolve-plan-dir.sh), no error raised
3. Resolution falls through to mtime order (newest-by-mtime), and mtime is not deterministic under concurrent writes

D1 argues "PLAN_ID per terminal is mandatory", which is TRUE for slug-mode semantics — but the draft does NOT propose to enforce it, and the repo's "no-shell-export for CLAUDE_*" rule (Q3) means `PLAN_ID` cannot live in settings — it must be per-terminal manual export. That is a working constraint, but it is not a solution; it is a **reliance on human discipline**. 

**The decision becomes: should this discipline live in `.claude/CLAUDE.md` + agent briefs (current proposal) or should it be ENFORCED via git worktrees (the alternative)?**

Per `review-attest.md:138-149`, multiple agent sessions DO share one legacy `task_plan.md` currently. Worktrees would provide **hard isolation** — each worktree gets its own plan file, zero human discipline required. The draft's upstream-audit finds (#77, #234) that slug-mode was the upstream's answer to this, but the drift-through-mtime and fall-silent-on-INVALID-ID defects remain unfixed by slug-mode itself.

**Recommendation:** Accept D1 IF the sequencing (§4) puts D1 last, after D6's `planning-check` is wired to detect mtime drift, so that "went to newest mtime" is DETECTABLE not silent. AND pair D1 adoption with a documented `PLAN_ID` pinning pattern in `.claude/CLAUDE.md` so the human discipline is discoverable, not tribal.

**ALTERNATIVE I cannot recommend without evidence:** Evaluate whether git worktrees (`git worktree add …`) would provide the isolation boundary without the slug-mode defects, and whether `planning-check` could detect worktree-crossing writes just as well. The draft never addressed this; it is worth a one-line probe: does the plugin have existing tests or docs for worktree separation? (Upstream-audit touched on multi-session collision, not worktrees specifically.)

---

### D2 — Codex lanes: `PLANNING_DISABLED=1`  
**Status:** ✅ **APPROVE**

**The risk:** Removal of lane planning context. But the evidence is clear:
- Verified both arms (142 bytes → 0 bytes) in pwf-codex-hooks.md
- Every lane today is read-only research with no legitimate reason to write `task_plan.md`
- A lane that genuinely needs plan context gets its own slug + `PLAN_ID` (reversible per invocation)
- This is the plugin's own recommended shape for `codex exec` lanes (codex.md, "Opting out for one-shot runs")

**Net risk:** Zero. The cost is zero, the reversibility is proven, and the use case does not exist yet.

---

### D3 — File role contract  
**Status:** ✅ **APPROVE**

**The risk:** None. This is configuration — documenting upstream's split in the lane briefs.

The upstream split is finer than the repo's current "lane returns go in progress.md" (per MEMORY.md feedback):
- `task_plan.md` = coordinator only (phases, checkboxes, current phase, distilled decisions)
- `findings.md` = anyone (research, analysis, evidence, technical findings)
- `progress.md` = anyone (chronological outcomes, actions, errors, test results)

This fixes the #1 pain (lane returns landing in wrong file) and costs nothing but updating briefs.

---

### D4 — Attestation stays human-invoked. Exception clause.  
**Status:** ⚠️ **AMEND** — tighten the exception.

**The exception as stated:** "An agent may run `attest-plan.sh` when the operator has approved an exact displayed diff+hash in the same turn and explicitly directed it."

**The risk:** This exception erodes the boundary it exists to protect — the hash is a human-approval gate against an agent blessing its own rewrite.

**Why the exception is still SAFE, but only narrowly:**
- The exception requires BOTH conditions: operator approval of exact diff+hash (means operator READ and DECIDED) AND explicit direction (means operator NAMED the action)
- The boundary holds because the human still makes the DECISION; the agent only EXECUTES what was already approved
- The narrow scope is crucial: "exact displayed diff+hash" means the operator saw a unified diff and a specific hash, not "the agent says it checked the hash"

**TIGHTEN it this way for safety:** 
1. Add to the brief: "Exception applies ONLY when operator has run `/plan-attest confirm <actual-hash>` OR explicitly run the script by name (`./scripts/attest-plan.sh`). Never attest as a side effect of another command."
2. Add to `.claude/CLAUDE.md` or the agent definition: "`/plan-attest` output must be acknowledged by operator before proceeding; no agent may re-run it in the same turn."

This keeps the exception (it is operationally useful for corrections) but prevents the drift where "the operator said I should fix the plan" gets read as "the operator approved an exact hash".

---

### D5 — PostToolUse noise — file upstream  
**Status:** ✅ **APPROVE**

**The risk:** None that can be avoided here.

The evidence is airtight (pwf-codex-hooks.md Q1):
- Constant string, unthrottled, matcher `Write|Edit|Bash`
- Emitted via `systemMessage` (goes to USER, not model)
- No knob silences it alone
- The only escape is caching an editable version (not tracked, lost on update) or filing upstream

Filing upstream is correct. The repo's edit-the-cache workaround would guarantee the nudge comes back on plugin update, so filing upstream is the durable path.

---

### D6 — Build `planning-check`  
**Status:** ✅ **APPROVE**

**The risk:** None. This is a new safety check with clear scope.

Key constraints respected:
- Classifies on presence/absence of `===BEGIN-PWF-DATA` framing (anchored, not substring-matched)
- Never writes attestation (keep the check read-only and human-driven)
- Lives in `python/src/dotfiles_setup/planning.py` + `mise run planning-check` + doctor integration
- No new bash (zero-bash-logic rule honored)

The framing anchor directly addresses FINDING A (substring-match false positive in `plan-doctor.sh`). This check will catch real drift without the false positives.

---

## Sequencing Verdict

**As stated (D3+D2 today, D5 today, D6 next session, D1 last):** ✅ **CORRECT**

The ordering respects dependencies:
1. **D3+D2 today** — configuration, zero risk, no downstream dependencies
2. **D5 today** — file a bug, no repo changes, no downstream dependencies
3. **D6 next session** — introduces the drift detector that makes D1 safe
4. **D1 last** — slug migration can assume drift is detectable (D6 is live) and human discipline is documented (revised D4 exception scope)

This sequence ensures D1 is not applied until the safety layer (D6) is in place to detect its edge cases.

---

## Open Questions Verdict

### Q1: Is D1 worth it at all, given the defects even slug mode doesn't close?

**Answer:** Conditional YES. D1 is worth it IF:
1. D6's drift detector is live first, so concurrent-write damage is detectable
2. `PLAN_ID` pinning discipline is documented in `.claude/CLAUDE.md` as an operating expectation
3. A worktree boundary is evaluated as an alternative (one-line probe: does upstream have worktree tests?)

The defects (.active_plan repointing, mtime fallthrough, silent invalid-PLAN_ID) remain whether D1 is applied or not. They are upstream bugs, not repo configuration. But with D6's detector live, the repo can see them and respond (alert the operator, file a new upstream issue). Without D6, they remain invisible.

**If the worktree alternative is ruled out, D1 is net-positive:** slug-mode is upstream's own prescribed remedy, and the repo's documentation of `PLAN_ID` discipline + D6's detector provide the visibility and discipline upstream's own docs assume.

### Q2: D2 removes lane planning context. Is that loss worth paying?

**Answer:** YES. No lane to date has needed planning context. Codex lanes are read-only research; they should not be writing `task_plan.md`. If a lane ever needs plan context (a future implementer lane, e.g.), it gets its own slug and explicitly opts in — no change to D2, just the *exception* to it, already named in the draft.

### Q3: Is there a durable per-session `PLAN_ID` mechanism compatible with the no-shell-export rule?

**Answer:** NO per-session automatic mechanism. But that is BY DESIGN, not a defect.

The no-shell-export rule exists to prevent credentials drifting between sessions. `PLAN_ID` is NOT a credential; it is a workflow choice (which plan slug am I running my agents under?). Making it shell-exported would put it in the exact blast radius the rule was written to avoid.

**The durable mechanism is:**
1. `.claude/CLAUDE.md` or the agent definition documents the pattern: open a terminal, `export PLAN_ID=<date>-<slug>`, run your agents
2. The agent briefs include this step as a prerequisite
3. A human who wants to use slug-mode does this once per terminal, and all their agents use it

This is the SAME discipline upstream assumes in their docs ("pin THIS terminal"). It is not automatic, but it is discoverable and documented.

**Alternative (less preferred):** per-worktree isolation via git worktrees, which would require no discipline — each worktree has its own `task_plan.md` by definition. Evaluate this if the slug-mode discipline feels too fragile.

### Q4: Does anything conflict with fable-orchestrator lane doctrine in CLAUDE.md?

**Answer:** NO.

The fable-orchestrator doctrine specifies which lane runs which implementation (codex at xhigh effort). The PWF refactor specifies how lanes manage plan state (`PLANNING_DISABLED=1`, optional per-lane slugs). These are orthogonal — the implementer lane can still run codex at xhigh; it will just do so with `PLANNING_DISABLED=1` set by default, and can opt into its own slug if it needs plan context.

---

## What is MISSING from the draft

1. **Worktree alternative not explored.** The draft jumps to slug-mode as the only parallel-session isolation mechanism. A single-line probe (does upstream have worktree tests, or any mention of per-worktree isolation?) would answer whether that boundary is viable here.

2. **D4 exception scope not tightened.** The exception is operationally useful but needs explicit guard rails to prevent "the operator said fix it" drifting into "the operator approved this exact hash". Suggest adding to the agent definition or CLAUDE.md.

3. **Downstream checklist for D1 landing missing.** Once D1 ships, what needs to happen?
   - Migrate this session's agents to `PLAN_ID=…` pinning
   - Test concurrent-session writes via two agents with different `PLAN_ID` values
   - Verify D6's drift detector fires on a deliberate concurrent write
   - Document the `PLAN_ID` pattern in `.claude/CLAUDE.md`

4. **D6's integration with the doctor not specified.** The draft says "wire into doctor" but doesn't say whether drift becomes a hard failure (block `verify-local`?) or a loud warning. That is a subsequent decision, but naming it avoids surprises.

---

## Final Verdict

**APPROVE D2, D3, D5, D6 as stated.** 
**AMEND D1 to condition approval on (a) D6 being live first, (b) `PLAN_ID` discipline documented in CLAUDE.md, and (c) one-line worktree alternative check.** 
**AMEND D4 to tighten exception scope in agent definition/CLAUDE.md.**

**Sequencing is correct as stated.** No changes needed.

