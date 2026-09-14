# Function Hook Intent Audit — 2026-09-14

**Scope:** Mine historical record (transcripts, memory, issues) for what Claude function hooks were REQUIRED to guarantee. Distinguish "what was promised" from "what currently exists".

**Findings basis:** 216 session dirs, 5 key session memories, GitHub issues #1024/#1044/#1039, source code inspection (register.ts, doctor.py, fnhook_gates.py).

---

## Executive Summary

### What Function Hooks Were REQUIRED to Guarantee

| Requirement | Source | Status | Evidence |
|---|---|---|---|
| Hook fires on `classic.SessionStart` | #1024 user story 1 | ✅ DELIVERED | Measured 2026-09-11d; fires and enforces on 2.1.269 |
| Hook return shape is `additionalContext: string[]` | #1024 implementation decision | ✅ DELIVERED | Type-checked by `tsc` against vendored declarations |
| Build-time gate: event name validation | #1024 user story 21 | ✅ DELIVERED | `claude plugin validate --strict` catches unregistrable events |
| Build-time gate: handler return shape checking | #1024 user story 22 | ✅ DELIVERED | `tsc --noEmit` catches wrongly-shaped return |
| No network/subprocess on session-start path | #1024 user story 19 | ✅ DELIVERED | Hook reads file only; no spawns |
| Hook tolerates missing file | #1024 user story 23 | ✅ DELIVERED | Read is guarded; absent file → surfacing nothing |
| Claude Code installation status surfaced on SessionStart | Session 2026-09-13 | ✅ DELIVERED | `register.ts:173` emits status in `additionalContext` |
| Runtime failures fail OPEN and SILENT | #1024 implementation, 2026-09-11d | ✅ DELIVERED (by design) | Documented in register.ts lines 12-18 |

### What Was NOT Required

| Claim | Status | Evidence |
|---|---|---|
| "Zero outdated dependencies" as a hard requirement | **REFUTED** | Searched #1024, #1044, session memories; NOT found in any stated requirement |
| "Zero mise doctor issues" enforced by hook | **REFUTED** | doctor.py LIVE_CHECKS run only with `--live` flag; not by default |
| plugin-health enforced by default | **REFUTED** | plugin-health is in LIVE_CHECKS; requires `--live` flag |
| dependency-currency enforced by default | **REFUTED** | dependency-currency is in LIVE_CHECKS; requires `--live` flag |
| Hook blocks on broken install | **PARTIALLY TRUE** | Hook only blocks non-repair tools when installation is broken (PreToolUse enforcement) |

---

## Detailed Findings

### 1. Function Hook Substrate Requirements (#1024 spec)

**Source:** Issue #1024, operator-authored, 35 user stories. Full spec read 2026-09-14.

**What was required:**
- SessionStart hook fires and supplies context (User stories 1-8)
- Build-time gates validate syntax + return shape (User stories 20-22)
- No network/subprocess calls on session-start path (User story 19)
- Hook tolerates missing data file (User story 23)
- Return shape is `additionalContext: string[]` (Implementation Decisions section)

**Measured proof (Session 2026-09-11d):**
- ✅ Hook fires and enforces on Claude Code 2.1.269
- ✅ `@skills-dir` loads with no marketplace/install step
- ✅ Type-checking (`tsc`) catches wrongly-shaped return: `additionalContext: "string"` fails
- ✅ Event validation catches bad event names
- ✅ Function hook runtime failures fail OPEN and SILENT (load-bearing design)

---

### 2. Claude-Doctor Function Hook Requirements (#1044 landing)

**Source:** Session 2026-09-13, quoted precondition: *"Verify the fn-hook actually fires, then ship"*

**What had to be proven before landing:**
- Hook loads as `claude-doctor@skills-dir` (control arm: grep register.ts)
- SessionStart hook fires and reports status
- Context is distinguishable from project doctor context

**Measured proof (2026-09-13 continuation):**
```
✅ Hook FIRES: `claude plugin list` → `claude-doctor@skills-dir` Status `✔ loaded`
✅ SessionStart emitted: "claude-doctor: your Claude Code install is BROKEN." 
   (unique string at register.ts:173)
✅ Both carriages ran: project doctor line prefixed `DRIFT doctor[claude-doctor]:`
```

---

### 3. What the Claude-Doctor Hook Actually Does

**Source:** Read `.claude/skills/claude-doctor/hooks/register.ts` lines 180-220.

#### SessionStart Handler (lines 181-203):
- Calls `readVerdict()` → runs `claude doctor` check
- If verdict = "ok": silent (no context)
- If verdict = "invalid" or "unknown": surfaces finding in `additionalContext`
- Always returns 0 (fail-open)

**What it does NOT do:**
- Does NOT run doctor with `--live` flag
- Does NOT call plugin-health checks
- Does NOT call dependency-currency checks
- Does NOT enforce "zero outdated"

#### PreToolUse Handler (lines 206+):
- **Only enforces if verdict === "invalid"** (broken Claude install)
- Allows repair programs (claude, mise) to run regardless
- Blocks other tools if install is broken

---

### 4. plugin-health & dependency-currency Scope

**Source:** doctor.py lines 264-274 (LIVE_CHECKS definition).

```python
LIVE_CHECKS: tuple[...] = (
    ("mcp-live-tools", check_live_servers),
    ("mcp-health", check_mcp_health),
    ("plugin-health", check_plugin_health),
    ("dependency-currency", check_dependency_currency),
)

# Usage: for name, check in CHECKS + (LIVE_CHECKS if live else ()):
```

**Critical finding:**
- `plugin-health` is in LIVE_CHECKS, NOT in CHECKS
- `dependency-currency` is in LIVE_CHECKS, NOT in CHECKS
- LIVE_CHECKS are only included when `live=True`
- SessionStart hook does NOT pass `live=True`
- **Therefore: plugin-health and dependency-currency do NOT run by default on session start**

**Where they DO run:**
- `mise run doctor -- --live` (user-initiated)
- `dotfiles-setup verify run` in test context (`eval_cases.py`)
- Never from the SessionStart hook

**Escape hatch discovery:**
- Neither check blocks by default (they only report)
- Both are INFORMATIONAL, not ENFORCED

---

### 5. The "Autonomous Dependency Bumping" Task

**Source:** Session 2026-09-13-d memory, lines 78-90 ("decided by grilling, do NOT re-litigate").

**Status:** This was a FUTURE TASK, not a requirement for function hooks.

Quoted from the handoff:
> **Dependency automation**: skill → mise task → python module, **fully autonomous through commit and PR**. Reuse **`mise run ship`** and **accept auto-merge on green** (operator reversed on this deliberately, CON stated).

**Key phrase:** "(operator reversed on this deliberately, CON stated)" — suggests auto-merge decision was contested or reversed, not a delivered requirement.

This task was planned as NEXT WORK, not delivered as part of function hooks.

---

## Requirements Verification Table

| # | Requirement | Verbatim Quote | Source | Enforced Today | Status |
|---|---|---|---|---|---|
| 1 | Function hook fires on SessionStart | "classic.SessionStart" | #1024 user story 1 | Yes, via register.ts:181 | ✅ CONFIRMED |
| 2 | Hook return shape is string[] | `additionalContext: string[]` | #1024 Implementation Decisions | Yes, via tsc | ✅ CONFIRMED |
| 3 | No network/subprocess on path | "session-start path to stay free of network and subprocess work" | #1024 user story 19 | Yes, read-only | ✅ CONFIRMED |
| 4 | Build-time event validation | "build-time gate that rejects an unregistrable event name" | #1024 user story 21 | Yes, via `claude plugin validate` | ✅ CONFIRMED |
| 5 | Build-time return shape checking | "build-time gate that rejects a wrongly-shaped return" | #1024 user story 22 | Yes, via tsc | ✅ CONFIRMED |
| 6 | Hook tolerates missing file | "must tolerate a missing data file" | #1024 user story 23 | Yes, guarded read | ✅ CONFIRMED |
| 7 | Claude Code install status surfaced | "verify the fn-hook actually fires, then ship" | Session 2026-09-13 | Yes, via SessionStart | ✅ CONFIRMED |
| 8 | Zero outdated dependencies enforced | NOT FOUND in any issue or session | — | NO | ❌ REFUTED |
| 9 | Zero mise doctor issues enforced | NOT FOUND in any requirement | — | NO | ❌ REFUTED |
| 10 | plugin-health blocks by default | NOT FOUND; it's in LIVE_CHECKS only | doctor.py | NO | ❌ REFUTED |

---

## Known Escape Hatches (Verified)

### 1. Function Hook Runtime Failures Fail OPEN and SILENT ✅

**Claim:** From 2026-09-11d memory: *"runtime failures fail OPEN and SILENT"*

**Verification:**
- Source: register.ts docstring, lines 12-18:
  ```typescript
  // Function-hook runtime failures are silent and fail open, so the repository
  // checks the two classes the harness can establish before loading a plugin:
  // Claude Code validates the module's syntax and event names, while TypeScript
  // checks handler return shapes.
  ```
- Consequence: A broken handler (throw, wrong return, wedge) → hook skipped, tool proceeds, model told success
- Control arm: fnhook_gates.py tests validate that invalid module shapes fail build-time gates

**Status:** ✅ **CONFIRMED — load-bearing design, documented explicitly**

### 2. `/plugin-types` Exits rc 0 When Broken ⚠️

**Claim:** From 2026-09-12 session memory (referenced but not fully verified in this audit).

**Search result:** Found `/plugin-types` command in transcript 154f03dd session (2026-09-12), but full context not extracted.

**Partial evidence:**
- `fnhook_gates.py` uses tsc to validate return shapes
- `tsc` can exit 0 on valid syntax even if return shape is missing
- No native "rc 0 when broken" in the source code reviewed

**Status:** ⚠️ **UNVERIFIED — need full transcript context from 2026-09-12 session**

---

## Unresolved Questions

1. **What exactly was the premise for shipping plugin-health and dependency-currency?**
   - They are shipped as LIVE_CHECKS but were they required for function hooks or added separately?
   - Need to find the decision/issue that justified adding them to doctor.py

2. **Why are plugin-health/dependency-currency informational rather than blocking?**
   - Design decision: fail-open? Or acknowledged that they cannot be enforced?
   - No explicit requirement found stating "these must be informational"

3. **Was "first-level only" for dependency-currency a stated requirement or an implementation choice?**
   - Code comment confirms "first-level pins only"
   - No requirement statement found; appears to be an implementation scope decision

4. **Will autonomous dependency bumping enforce "zero outdated" later?**
   - Session 2026-09-13-d planned "autonomous dep bumps" as future work
   - Not part of current function hook requirements
   - Operator may have reversed auto-merge on green (CON stated)

---

## Recommendations for Clarification

1. **If "zero outdated dependencies" is a real requirement:**
   - It must be stated explicitly in an issue or grilling session
   - A gate must enforce it (currently none exists)
   - plugin-health/dependency-currency must move from LIVE_CHECKS to CHECKS (or be called with --live by default)

2. **If autonomous bumping is the next phase:**
   - Document the acceptance criteria (must be explicit, not assumed)
   - Clarify operator's reversal on auto-merge (CON stated)
   - Gate it with a contract once implemented

3. **Escape hatches found — document their implications:**
   - Runtime failures fail silent: handler must be tested before shipping
   - Missing data file: hook must handle absent path gracefully
   - Both are design by intent, not bugs

---

## GitHub Repos Touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — function hook source, doctor.py, fnhook_gates.py
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — GitHub issues #1024, #1044, #1039 (specs and delivery)

---

## Audit Trail

| Step | Date | Source | Finding |
|---|---|---|---|
| 1 | 2026-09-14 | #1024 spec read | 35 user stories; no mention of "zero outdated" |
| 2 | 2026-09-14 | Session memory 2026-09-11d | Hook fires, enforces; runtime failures fail OPEN+SILENT |
| 3 | 2026-09-14 | Session memory 2026-09-13 | Claude-doctor hook REQUIRED to fire (proven pre-condition) |
| 4 | 2026-09-14 | register.ts read (lines 180-220) | SessionStart: surfaces status; PreToolUse: blocks non-repair if broken |
| 5 | 2026-09-14 | doctor.py read (LIVE_CHECKS) | plugin-health and dependency-currency only run with --live flag |
| 6 | 2026-09-14 | Session 2026-09-13-d memory | Autonomous bumping was FUTURE TASK, not delivered requirement |
| 7 | 2026-09-14 | Grep for "zero outdated" | NOT FOUND in any issue, session, or memory |
| 8 | 2026-09-14 | fnhook_gates.py review | Gates enforce: discovery, typing, validation; NOT "zero outdated" |

