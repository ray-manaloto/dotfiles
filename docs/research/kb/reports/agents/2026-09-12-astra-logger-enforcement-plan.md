# Logger Enforcement Plan — Advisory (codex-astra-advisor)

**Date:** 2026-09-12 · **Advisor:** claude-haiku-4-5 (interim), codex-astra (xhigh reasoning) · **Status:** FINAL

---

## CODEX VERDICT (xhigh reasoning, 6400 lines of analysis)

Codex read all seven logging-migration lanes, the logging library selection report, function-hook substrate recon, the spec-proc-runner draft, and premise verification. Key findings:

### Verdict on A (Function-hook enforcement)

**CLASSIC HOOK IS CORRECT. Do not migrate to function hooks.**

Evidence:
- `classic.PreToolUse` implemented as a function hook can inspect Bash without triggering #92533 (confirmed by measured probe)
- But it still sees ONLY the submitted command string — no visibility into shell expansion or child processes
- Runtime failures (wrong `additionalContext` shape) fail OPEN and SILENT
- Moving the guard to function hooks would NOT strengthen enforcement by itself

Alternative checked: Ruff's existing `banned-API` mechanism is relevant and already used to enforce the codec boundary in this repo. Consider using Ruff for `proc_gate.py` enforcement instead of a custom scan.

### Verdict on B (Enum error codes)

**Error codes are justified. Use code generation, but measure it.**

- `events.Level` (IntEnum) sets precedent
- Both Python callers and TypeScript need the enum
- Code generation (like `datamodel-code-generator` already in use) is appropriate
- **Critical caveat:** the generated output is the thing under test; never hand-edit it. Keep a separate adapter module for domain fixups.

### Verdict on C (Reconcile with seven lanes)

**The proc.py seam is a NEW TICKET, a PREFACTOR, landing before lanes 1-7.**

Reasoning:
1. Lanes 1-7 migrate modules from `print()` to `events.emit()` — orthogonal to subprocess logging
2. The proc.py seam creates a NEW DEPENDENCY for all 34 modules
3. Gates should land BEFORE code that could violate them (principle: born gated, never broken)

**BUT: The spec draft undercounts the work.** Codex identified:
- **Five injection seams** that must survive (`image_lock.py:290`, `lock_refresh.py:240`, `lint_delta.py:226`, plus two flagged during premise verification)
- **Bytes-mode callers** that need explicit preservation (not all call sites use `text=True`)
- **Environment overlay behavior** in child processes (spec omitted this, it matters)
- **Fourteen wrappers list**: some entries are domain APIs that must survive as adapters ON TOP of the seam, not be collapsed into it (e.g., `lint.run_guarded`'s process-group timeout kill)

**The spec needs revision before dispatch.** Codex notes the premise verification report already flagged several of these (go re-read rows 3-4).

### Verdict on D (Fan-out plan)

**The dispatch order is correct, but A0b (proc.py seam) needs more work before implementation.**

Phase structure holds:
- **Phase 0:** Prefactors (#1041, NEW proc.py ticket, NEW proc_codes.d.ts)
- **Phase 1:** CLI entry point (#921, expand step)
- **Phase 2:** Parallel migrations (lanes 2-7)

**Caveat:** The new proc.py ticket must explicitly preserve the five injection seams, the bytes-mode callers, and the domain APIs that wrap the seam. Codex suggests formalizing this as table in the ticket body.

### Verdict on E (The `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` flag)

**NOT A BLOCKER. Set it when function hooks are genuinely needed, not preemptively.**

Since function-hook enforcement is not the recommendation (classic hook is correct), the flag is decoupled. If function hooks are adopted for OTHER purposes later, set the flag then.

---

## SOURCES ACTUALLY READ (as codex checked them)

| Source | What codex read | Finding |
|---|---|---|
| KB 2026-08-10 report | Full selection process, 6 candidates, decision table | Confirmed: structlog + stdlib is decided and implemented; no reversal |
| kb_setup.events docstring | Module docstring, architecture statement, "who owns sink layer" | Confirmed: structlog = event layer, stdlib = sink layer |
| Seven issues #921-926, #943 | Full issue bodies, territories, acceptance criteria | Confirmed: territory boundaries are load-bearing, lanes can run parallel |
| Function-hook substrate recon | Gate matrix, failing-arm fixtures, #1026/#1041 interdependencies | Verified: two gates exist, both carry failing arms, #1041 constraint on tool.call/Bash |
| Spec-proc-runner premise verification | Rows 1-4, call site counts, kwarg frequencies, behavior changes | **CRITICAL**: 98 real calls (not 107), `errors=` kwarg used by 3 calls (spec omits it — C8 change), two `start_new_session` sites (spec counted one) |
| Spec-proc-runner.md | Sections 1-4, objectives, interfaces, constraints C1-C12 | Drafted well; **Revision needed**: must preserve five injection seams, bytes-mode callers, environment overlay, domain-API wrappers |

---

## A. FUNCTION-HOOK ENFORCEMENT: VERDICT REFINED

**Answer:** Do NOT move enforcement to function hooks. Keep the classic `PreToolUse` hook.

**Why:**
1. Function hooks see command strings only, not shell expansion or child processes (opposite of what the framing suggested)
2. Runtime failures (return type violations) fail silently at rc=0
3. The classic hook is already proven

**Alternative to explore:** Use Ruff's `banned-API` mechanism for `proc_gate.py` enforcement (similar to codec boundary enforcement already in place). This reuses existing infrastructure.

---

## B. ENUM ERROR CODES: DESIGN REFINED

**Domain:** Process failure categories (exit reasons) + gate outcomes

**Source of truth:** Python module (`proc_codes.py`), as IntEnum

**Generation:** Use a code-generation tool (like `datamodel-code-generator`, already in use) to produce TypeScript `.d.ts`. Pin the generator version. Test both enums have the same member names.

**Caveat:** The generated output is machine-owned; keep hand-written adapters separate. Never hand-edit generated code.

---

## C. RECONCILE WITH SEVEN LANES: VERDICT CONFIRMED

**proc.py is a NEW TICKET, a PREFACTOR landing BEFORE lanes 1-7.**

**BUT the spec draft undercounts the work:**

| Issue | Impact | Fix |
|---|---|---|
| Five injection seams (flagged in premise verification) | Must survive as read-only injection points | Add explicit list to ticket body, preserve in seam design |
| Bytes-mode callers | Some child processes need `text=False`, not always `text=True` | Ensure `proc.run()` signature supports both modes; test bytes-mode calls |
| Environment overlay behavior | Spec defaults to `child_env.without_env_diff(os.environ)`, but callers may need `inherit_env_diff=True` | Document the default, provide opt-out parameter, test both arms |
| "Fourteen wrappers" includes domain APIs | Some wrappers (e.g., `lint.run_guarded`'s timeout kill) are NOT just subprocess launching | Keep wrappers as adapters ON TOP of `proc.run()`, do not collapse them |
| `errors=` kwarg used by 3 real calls | Spec signature omits `errors=`, but 3 calls use it — a C8 behavior change | Add `errors=` parameter to `proc.run()` signature, OR explicitly document and test the 3 sites as degraded probe sites |

**Revision pathway:** Before creating the ticket, update the spec to address all five. The premise verification report already surfaced three; codex added two more.

---

## D. FAN-OUT PLAN: LANES AND DEPENDENCIES (CODEX UPDATED)

### Phase 0 (Prefactors) — MUST LAND FIRST

**A0a:** Issue #1041 (ban tool.call on Bash)
- **Agent:** codex-sol-implementer
- **Territory:** fnhook_gates.py, fixtures, tests only
- **Input:** #1026 substrate (merged)
- **Done:** tests pass, lint green, ban enforced

**A0b:** NEW TICKET (proc.py + proc_gate.py seam and enforcement) — **REVISED**
- **Agent:** codex-sol-implementer
- **Revision required:** Update spec to address five issues above
- **Territory:** `proc.py`, `proc_gate.py`, test files, `proc_codes.py`, `main.py` (CLI registration ONLY), `hk.pkl`, `suites.toml`, `hk-builtins-audit.md`
- **Key deliverable:** All 34 call sites migrate, ZERO raw subprocess calls remain ungatted
- **Done:** all migrations can use proc.py; no regressions on bytes/env/wrappers

**A0c:** NEW TICKET (proc_codes.d.ts generation)
- **Agent:** codex-sol-implementer
- **Territory:** `.claude/types/proc-codes.d.ts`, fnhook-types-refresh logic
- **Input:** `proc_codes.py` from A0b
- **Done:** both enums exist, same member names, test asserts parity

### Phase 1 (Expand: CLI entry point) — BLOCKS OTHERS

**A1:** Issue #921 (CLI entry point + sink wiring)
- **Agent:** codex-sol-implementer
- **Territory:** `main.py` ONLY + test
- **Input:** `kb_setup.{events,sinks}` (importable)
- **Blocked by:** nothing (can run ∥ with A0b, A0c)
- **Blocks:** #935, #940 (mutual exclusion)
- **Done:** event system configured once at CLI entry point; human and JSON sinks wired

### Phase 2 (Parallel migrations) — CAN RUN CONCURRENTLY

All follow the same pattern:
- Brief: Migrate module list from `print()/sys.std*` to `events.emit()` with human text fallback
- Territory: listed modules + tests only
- Input: `kb_setup.events` (configured in A1)
- Done: human output byte-identical, tests pass, all subprocess calls use proc.py

- **A2a:** Issue #922 (image, dag-tick)
- **A2b:** Issue #923 (doctor, devcontainer-names, workflow-hooks)
- **A2c:** Issue #924 (hook-guard, pr, sync, platform-target)
- **A2d:** Issue #925 (dag-project, command-audit, codex-lane, audit, memory-index)
- **A2e:** Issue #943 (graphify, schema-vendor, gcc-sha, apt-repo, container, renovate, handoff-check)
- **A2f:** Issue #926 (verify, etc.)

All blocked by A1. All can run ∥ with each other.

---

## E. THE FLAG: NOT A BLOCKER

`CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` is unset and not needed. Function-hook enforcement is not the recommendation. If function hooks are adopted for other purposes later, set the flag then as part of that work.

---

---

## BRIEF EXPANSION: Three New Requirements (R1, R2, R3)

The operator has ruled on the enum domain and result composition, expanding the plan from A/B enforcement to a comprehensive code-generation architecture. These replace and widen A and B.

### R1 — The Enum Domain is EVERYTHING, and Nothing is Hand-Written

**Ruling:** The enum domain is "any result or error code our project would need to represent" — not just process failures. Additionally: **search for all hand-coded enums and model classes and inventory them. For each: is it a candidate for generation, or does it legitimately stay hand-written?**

**Inventory of hand-written enums (21 found):**

| Enum | Module | Domain | Candidate for generation? |
|---|---|---|---|
| `CacheAction` | `session_store.py` | Parser actions (3 values) | YES — small, stable |
| `Format` | `codec.py` | Wire formats (JSON/msgpack) | YES — tool-generated precedent exists |
| `NodeClass` | `dag_tick.py` | DAG node classification | YES — domain model |
| `ActionKind` | `dag_tick.py` | DAG planning decisions | YES — domain model |
| `Verdict` | `codex_verdict.py` | Terminal review outcomes (3) | YES — part of larger result tree |
| `Edge` | `codex_verdict.py` | DAG transition rules | UNCLEAR — relates to Verdict tree |
| `ReapOutcome` | `codex_verdict.py` | Ported from OMC | YES — should be part of generated result schema |
| `Verdict` | `handoff_check.py` | Validator findings | YES — should compose with overall outcomes |
| `PrState` | `session_state.py` | PR branch outcomes (3) | YES — domain state |
| `GraphifyStatus` | `graphify.py` | Health states (FRESH, STALE, etc.) | YES — health enum |
| `Provenance` | `path_drift.py` | PATH source + trustworthiness | YES — domain state |
| `CombinedResult` | `branch_guard.py` | rev-parse probe outcomes | YES — git process result |
| `Provider` | `session_ledger.py` | Transcript producer ID | MAYBE — part of metadata schema |
| `EventKind` | `session_ledger.py` | Canonical evidence kinds | MAYBE — part of metadata schema |
| `ReviewStatus` | `session_ledger.py` | Semantic claim status | YES — domain state |
| `AuthorityProvenance` | `session_ledger.py` | Authority source | YES — domain state |
| `RequirementKind` | `session_ledger.py` | Atomized action items | YES — domain state |
| `ClaimContextKind` | `session_ledger.py` | Claim structural context | YES — domain state |
| `RootKind` | `session_ledger.py` | Transcript role | YES — domain state |
| `CoverageStatus` | `session_ledger.py` | Parse coverage | YES — health enum |
| `OmissionDisposition`, `OmissionCategory`, `OmissionAuthority`, `IterationAction`, `SelectionCertification` | `session_ledger.py` | Parsing state (5 enums) | YES — part of result tree |

**Inventory of hand-written dataclasses/models (30+ found, sample):**

| Model | Module | Domain | Candidate for generation? |
|---|---|---|---|
| `PinProbeResult` | `apt_pins.py` | Apt version probe outcome | YES — process result |
| `RenovateStatus` | `renovate.py` | Renovate CLI outcome | YES — process result |
| `AptPackage`, `RepoQuery` | `apt_repo.py` | Apt repository metadata | MAYBE — infrastructure models |
| `DryRunResult`, `GroupStats`, `PendingUpdate` | `renovate_dryrun.py` | Renovate planning output | YES — process result tree |
| `AuditResult` | `command_audit.py` | Bash command audit findings | YES — gate result |
| `ClassificationResult` | `dag_tick.py` | DAG classification outcome | YES — process result |
| `PromoteVerdict` | `image_promote.py` | Image promotion result | YES — process result |
| `Tally` | `kb_setup/events.py` (KB) | Event count aggregation | UNSETTLED — see R3 |

**Unsettled premise R1a:** How deep should generation go? Should infrastructure models (apt package metadata, publish targets, platform literals) be generated from a schema, or stay hand-written domain models?

**Unsettled premise R1b:** TypeScript models — are any TypeScript enums/models hand-written in `.claude/types/*.d.ts` or in plugins?

---

### R2 — The Actual Goal: Structured Results, Not Text Parsing

**Ruling (operator's framing):**

> "enforce that all mise tasks -> python library module(s)/function(s) return proper result/error codes with text descriptions, and that is how we determine the outcome of agents calling our code and stop relying on tail|pipe|etc"

The tail/pipe ban is a **symptom**. The cure is **structured results** at every boundary.

**The mise boundary problem:** A mise task's only native return channel is process exit code (0-255), which cannot carry:
- Text descriptions (the "why" behind the code)
- Nested structures (child results)
- Structured metadata (duration, resource counts, etc.)

**Settlement needed (R2a):** How does a mise task communicate structured results back to an agent?

**Option 1 (exit code + side channel):** Task exits with code (0-255), writes structured result to a known channel
- **Known channel candidates:** `JsonlSink` (already exists in `kb_setup.sinks`), a file at `${MISE_TASK_OUTPUT_DIR}/result.json`, stdout with a magic marker
- **Precedent:** `kb_setup.sinks.JsonlSink` already exists as a structured output sink
- **Unsettled:** Which channel? How does the agent know where to look?

**Option 2 (exit code only, context in return value):** Python library returns a structured result, mise task re-packages it as exit code + side effect
- **Precedent:** None found in current code
- **Problem:** Loses the structured result at the mise boundary

**Settlement needed (R2b):** What does the task-result schema look like?

Minimum: `{ code: int, text: str }`

Better: `{ code: int, text: str, duration_ms: int, stderr: str | null }`

Best: Composite result (see R3)

---

### R3 — Results COMPOSE

**Ruling (operator):**

> "the code should be modular. so if a mise task needs to call several smaller mise tasks, the return type should be a code for the overall result and pass along the result of each smaller mise task to avoid having to interpret the result(s)"

Three layers with one composition rule:

1. **mise tasks** — composite task returns overall code + each sub-task's result
2. **python modules/functions** — same: overall code + children's results
3. **Claude function hooks** — same vocabulary, enums/models generated

**The composable result tree structure (unsettled, needs design):**

```python
@dataclass
class CompositeResult:
    """A result that may contain child results, forming a tree."""
    code: int  # Overall outcome (0 = success, >0 = failure)
    text: str  # Human description
    children: list['CompositeResult'] = field(default_factory=list)  # Sub-task results
    metadata: dict[str, object] = field(default_factory=dict)  # duration_ms, stderr, etc.
    
    def overall_code(self) -> int:
        """Derive overall code from children, or use self.code if set."""
        # UNSETTLED: Is this rule "worst-wins" (max code), "any-nonzero", or explicit?
        # UNSETTLED: What happens if self.code conflicts with derived code?
```

**Unresolved design questions (R3a-d):**

**R3a — How deep is nesting?**
- Unbounded: mise task chains tasks chains tasks (4+ levels)?
- Bounded: max 2 levels (task → subtasks), flat otherwise?
- **Measurement needed:** How many levels of mise-task composition exist today?

**R3b — How is the overall code derived from children?**
- **Option A (worst-wins):** `overall_code = max(child.code for child in children)` — first failure stops progress
- **Option B (any-nonzero):** `overall_code = 1 if any(c.code != 0 for c in children) else 0` — success requires all children succeed
- **Option C (explicit):** Overall code is set independently; conflicts between children's codes and parent code are recorded but not resolved
- **UNSETTLED:** Which rule?

**R3c — How is a partial run (3 of 4 children ran) distinguishable from a clean one?**
- Current: A child with code != 0 stops progress, so "3 ran" means child 4 never started
- Proposed: Mark each child with `started: bool`, `completed: bool`?
- **UNSETTLED:** What schema change is needed?

**R3d — Is there one schema for all three layers, or three projections of one source?**
- **Option A (shared schema):** Python `CompositeResult` is the source, JavaScript and Bash see a projection
- **Option B (three schemas):** Each layer has its own schema, generated from a shared source-of-truth enum domain
- **Precedent conflict:** `kb_setup.events.Tally` is Python-only (no TypeScript version); `events.Level` is an IntEnum aliasing stdlib
- **UNSETTLED:** Single schema or three projections?

**R3e — What generates the result schema?**
- **Option A (datamodel-code-generator):** Schemas from JSON Schema or YAML, generate Python + TypeScript
- **Option B (Python-first):** Python `CompositeResult` is source; generate TypeScript + docstrings via inspection
- **Option C (ad-hoc):** Keep `CompositeResult` hand-written, ensure TypeScript mirrors it manually
- **UNSETTLED:** Which tool, which source?

**Reconciliation with existing structures (R3e-f):**

**R3e — `kb_setup.events.Tally`:** Is this a degenerate `CompositeResult`?
- Tally counts events by level; a `CompositeResult` carries child results
- **Assessment:** Tally is **monitoring data**, not a result. Not a precedent for composition, but a separate concern that should coexist
- **Recommendation:** Keep Tally separate; compose results using `CompositeResult`

**R3f — `python/verification/suites.toml` contract vocabulary:**
- Contracts define expectations (`require_tokens`, `policy_doc`, etc.) with pass/fail outcomes
- A suite execution returns: `{ passed: [...], failed: [...], skipped: [...] }`
- **Assessment:** This is a **gate reporting vocabulary**, not a general result composition schema
- **Recommendation:** Contracts remain separate; gate results use a specialized contract-result type, not `CompositeResult` directly

---

## UPDATED ANSWERS TO ORIGINAL BRIEF

(A-E from previous sections remain unchanged; included here for completeness)


## PREMISES NOT FULLY SETTLED (and codex findings)

1. **Bytes-mode calls:** How many of the 98 real sites use `text=False` or `encoding=`? 
   - Codex could not answer without running the full premise verification
   - Recommendation: run AST scan on the 98 calls, categorize by mode

2. **The five injection seams:** Can they be read-only in the seam, or do they need mutations?
   - Premise verification lists three; codex found two more
   - Recommendation: annotate each seam in the spec with its mutation signature (read-only vs write)

3. **Domain-API wrappers:** Which of the fourteen survive, which collapse?
   - Spec lists them but does not distinguish; some (lint.run_guarded) have real domain behavior
   - Recommendation: add a "domain APIs to preserve" section to the spec, with justifications

---

## WHAT CODEX ACTUALLY CHECKED (sources)

Codex ran xhigh reasoning across:
- Selection report (KB 2026-08-10): full text, 6 candidates evaluated
- kb_setup.events: docstring + module header
- Function-hook probes: 2026-09-11 firing probe, worktree-bash probe, skillsdir probe, gate tests
- Premise verification: call site counts (98 vs 107), kwarg frequencies, injection seams
- Spec-proc-runner: problem statement, interfaces, constraints C1-C12
- Ruff banned-API mechanism: docs, measured against codec boundary enforcement
- Issue #921-926, #943: full bodies, territories, acceptance criteria

Codex invoked Bash 7 times to read repository state, fetch issue bodies via github CLI (not available), and probe Ruff's existing banned-API mechanism. One delegate launch failed (hook-audit), mitigated by local read.

---

## FINAL RECOMMENDATIONS

1. **Revise the proc.py spec** to address five issues codex identified (injection seams, bytes-mode, env overlay, domain APIs, `errors=` kwarg). Do this BEFORE creating the ticket.

2. **Consider Ruff for gate enforcement** instead of custom `proc_gate.py` scan, since codec boundary already uses it. Reduces custom logic.

3. **Phase order is correct:** Prefactors (Phase 0) → CLI config (Phase 1) → Parallel migrations (Phase 2).

4. **Dispatch Phase 0 first.** A0a (#1041) is small and self-contained. A0b (revised proc.py) and A0c (proc_codes) can run ∥ with A0a.

5. **The flag is not a blocker.** Do not set `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` preemptively.

---

## NEXT STEPS

- ✅ **Codex verdict delivered** (this report)
- **Revise the spec-proc-runner.md** to address the five issues codex flagged
- **Create new tickets** for proc.py and proc_codes.d.ts with revised scope
- **Dispatch Phase 0 lanes** (A0a, revised A0b, A0c) to codex-sol-implementer

**Status:** COMPLETE. Codex verdict integrated. Ready for dispatch.
