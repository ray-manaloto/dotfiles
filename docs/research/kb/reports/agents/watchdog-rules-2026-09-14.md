# Watchdog Rules Consolidation (2026-09-14)

## Brief

Build consolidated **requirements + prohibitions list** for a real-time PreToolUse hook guard. Rank by "has bitten us, and nothing currently stops it." Focus on:

1. **Violations already occurring** (evidence in transcripts, telemetry, session-review)
2. **Mechanically enforceable at tool-call time** (hook input-only, no intent inference)
3. **Technical debt shapes recurring**: tools pinned at N sites (drift), checks that can only pass, probes with no control arms, gates failing open
4. **Architecture enforcement**: skill→mise→python modules; TypeScript function hooks (currently unguarded)

## Status

Starting — will track:
- `.agent/kb/raw/` — extracted violation evidence
- Root `findings.md` (append-only) — per-finding notes
- This file (updated after each source)

## Plan

1. **Read existing hook rules** (hook_guard.py `_RULES`) — baseline
2. **Mine command-audit.md** — one-off commands that bypass guards
3. **Mine session-review artifacts** — real violations with session IDs
4. **Mine project memory** — recurrent failure patterns (feedback_*)
5. **Mine eager rules** — gaps where rules exist but nothing enforces them
6. **Produce ranked table** — high-impact, low-enforcement violations
7. **Classify** — mechanically enforceable vs needs other layers

---

## Findings

_To be populated as sources are mined._

## Consolidated Watchdog Rules Table

**Ranking**: By impact + lack of current enforcement. Only entries with real evidence of violation.

### Tier 0: Silent Enforcement Gaps (Guard Itself Failing)

| Requirement | Evidence | Currently Enforced By | Mechanically Detectable? | Proposed Rule |
|---|---|---|---|---|
| **PreToolUse hook must not fail silently** | 158 guard-error-rc=1 in command-audit.md; commands allowed despite intent to block | Only manual log inspection | PARTIAL (can log errors, not prevent) | Monitor hook stderr/rc; hard-fail on error vs soft-allow. Separate rule: hook must report its own failures visibly. |
| **Guard runner must be available** | 1 interpreter-absent failure | None | YES | Probe: hook runner present before session startup; subagent brief includes runner check |

### Tier 1: Violations With Zero Enforcement Currently

| Requirement | Evidence | Currently Enforced By | Mechanically Detectable? | Proposed Rule |
|---|---|---|---|---|
| **TypeScript function hooks must not exceed a complexity budget** | `.claude/skills/claude-doctor/hooks/register.ts` and `plugin-health/hooks/plugin-health.ts` contain TS logic; `bash_logic_budget` hk step covers ONLY `.sh` files | NOTHING | YES (AST depth, token count) | New hk step: `typescript_hook_budget` in `hk.pkl`, allowlist entries in `python/src/dotfiles_setup/bash_budget.py` (rename to `logic_budget.py`). Track per-file token count; fail on growth past baseline. |
| **Tools pinned at N sites must use a central source** | Chezmoi mismatch 2026-09-14 (mise.toml vs mise-runtime.toml vs Dockerfile); hk pinned in 3 files; mise pinned in 2+ | None — manual review only | YES (grep + parse version strings) | New verification contract: `pin.sync-across-sources`. Lists canonical pin site (mise.toml) + mirror sites (Dockerfile, hk-image.pkl, etc.); asserts all match. |
| **One-off commands with >N occurrences must become mise tasks** | 4,381 one-off candidates in command-audit.md; top shapes repeat 100+ times (mkdir 762, python3 540, while 213) | Command-audit report only (advisory) | YES (group by shape, count in transcripts) | New hk step or suites.toml contract: `one_off_frequency`. Scans command-audit.md; fails if any shape exceeds threshold (e.g., 50 occurrences) without a corresponding mise task. |

### Tier 2: Violations With Partial Enforcement

| Requirement | Evidence | Currently Enforced By | Mechanically Detectable? | Proposed Rule |
|---|---|---|---|---|
| **Tool changes must keep version-scoped hints in sync** | Stale docs naming a removed flag; version-only checks that never fail | None — ruled out as unmaintainable in tool-currency rule | NO (requires intent inference) | Document as non-enforceable; implement offline drift check (`mise run tool-currency`) as the sole enforcement. |
| **Gates must have a control arm** | probes-need-a-control-arm.md documents 5 false negatives; #644 canary test | Documented via rule; no mechanical gate | PARTIAL (contract `per_path_tokens` enforces some shapes) | Extend verification contracts to detect: (a) absence claims without positive control probes; (b) tests that pass only on stubs. New contract: `probes.require_control_arm`. |
| **Checks must not be tautological** | Tests passing on empty/stub implementations (e.g., `bash -c ""` "passes") | Test harness only (manual design) | PARTIAL (`require_tokens` + audit catches some) | No mechanical fix; remains design discipline. Add to test-design review checklist. |

### Tier 3: Already Enforced (Baseline, Include for Completeness)

| Requirement | Evidence | Currently Enforced By | Since |
|---|---|---|---|
| Canonical mise tasks over one-off commands (ship, land, automerge, lint, fmt, test, etc.) | 59 guard denials working; 0 bypasses | hook_guard.py + PreToolUse | 2026-07-07 |
| No git hook suppression (--no-verify, -n, HK_SKIP_HOOKS outside CI) | Tested in #400 | hook_guard.py + pre-commit hk step + git ruleset | 2026-07-27 |
| No gate commands piped to pagers (preserves exit codes) | 33 denials working | hook_guard.py | 2026-07-21 |
| No backgrounded mise run on Mac (prevents reaping) | 17 denials working | hook_guard.py | 2026-07-21 |
| No secret-value substitution in printing (${VAR:-X} leak) | 1 denial working | hook_guard.py | 2026-08-02 |
| No bare `graphify` (must use `mise run graphify-query/update`) | User compliance only (no guard) | graphify-first.md rule (advisory) | N/A — **UNGUARDED** |
| No chezmoi apply/update on Mac host | Legacy shell guards (exited 1) → consolidated into hook_guard | hook_guard.py | 2026-07-07 |
| No npx (use mise binaries directly) | Consolidated into hook_guard | hook_guard.py | 2026-07-07 |

---

## Mechanically Enforceable Watchdog Rules (Ready for Implementation)

### High Priority (Silent Failures Today)

1. **Hook fail-open detection** — if PreToolUse hook itself errors, log visibly and fail closed, not silently allow
   - Rule shape: Cannot be a PreToolUse rule (it would need to run BEFORE the hook); belongs in settings.json `PreToolUse` error handling or `Hook` system itself
   - Proposed: Settings change + documentation that `permissionDecision: "deny"` on hook error

2. **TypeScript function hook complexity budget** — like bash_logic_budget, but for `.ts` in `.claude/skills/*/hooks/`
   - Rule shape: New `hk` step `typescript_hook_budget` (list-driven allowlist + per-file token count)
   - Estimated effort: Reuse bash_budget.py structure, add TS AST/token counter

3. **Tool pin sync across sites** — chezmoi, hk, mise pinned at N places must match
   - Rule shape: New verification contract in suites.toml, lists mirrors to canonical pin
   - Estimated effort: 3-5 hours (grep + version parse + test)

4. **One-off frequency gate** — commands that recur 50+ times without a mise task
   - Rule shape: New suites.toml contract scanning command-audit.md output
   - Estimated effort: 2-3 hours (threshold algorithm + test)

### Medium Priority (Enforcement Exists But Fails Open)

5. **Guard health check at session start** — verify hook runner is available
   - Rule shape: SessionStart hook that probes hook runner, warns/errors if missing
   - Estimated effort: 1 hour (shell probe)

6. **Control-arm detection in contracts** — fail tests/contracts that have only one reachable path
   - Rule shape: Extend suites.toml contract language; new `require_control_arm` handler
   - Estimated effort: 4-6 hours (AST inspection for test structure)

### Lower Priority (Need Clarity or Are Non-Enforceable)

7. **Bare graphify prevention** — cannot block at PreToolUse (it's a CLI, not a Bash call)
   - Rule shape: Would need to be in agent-internal logic or not at all
   - Proposed: SessionStart hook warns if graphify cache is stale; rely on rule enforcement via user judgment

---

## What Is NOT Mechanically Enforceable (And Should Remain Markdown Rules)

| What | Why | Recommended Enforcement |
|---|---|---|
| Research doc sources preference chain | Requires intent inference (which source the agent DECIDED to use) | Code review + rule documentation |
| Use-tool-builtins | Requires semantic intent ("did you look for native features?") | Code review + memory reinforcement |
| Tool currency checks | Requires comparing against upstream release notes | `mise run tool-currency` daily report + PR review |
| Probes with control arms | Requires human judgment of "adequate control" | Test-design review + rule documentation |
| Clarify-before-acting | Requires judging ambiguity level | Code review + AskUserQuestion gate |

---

## Summary: High-Impact Watchdog Additions (In Priority Order)

1. **Guard fail-open visibility** (Today: silent; 158 instances logged nowhere)
2. **TypeScript hook budget** (Today: unlimited; no guard exists)
3. **Tool pin sync** (Today: silent drift; 2026-09-14 example: chezmoi)
4. **One-off frequency gate** (Today: 4,381 hand-rolled commands unreported)
5. **Guard health check** (Today: 1 interpreter-absent; not probed)
6. **Control-arm detection in tests** (Today: tautological tests pass)

**Not included**: Bare graphify, research-doc-sources, use-tool-builtins, tool-currency checks (require user judgment or are already being reported via daily runs).

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — hook_guard.py rules, verification contracts, hk step definitions
- [jdx/mise](https://github.com/jdx/mise) — tool currency, release notes (research only)


---

## Appendix: Hooks and Subagent Messaging Research

**Scope addition per team lead (2026-09-14):** Consolidate existing research on Claude Code vs Codex hooks and on subagent messaging capabilities.

### A1. Hooks Research Summary

**Tracked document:** `docs/research/kb/reports/agents/res-hook-map-2026-09-14.md` (3 KB; complete equivalence map)

**Key findings:**

1. **Both Claude Code and Codex have SessionStart hooks** (1:1 equivalent):
   - Claude: Fires on `startup`, `resume`, `clear`, `compact` matchers; supports `command`, `http`, `mcp_tool`, `prompt` handlers
   - Codex: Fires on `startup`, `resume` matchers; supports `command` handler only
   - Both inject `additionalContext` into session

2. **Codex has NO function/module-hook equivalent** — only command-type hooks (shell commands)
   - Claude supports `type: command` and `type: prompt` (LLM reasoning injected into context)
   - Codex: Only `type: command` (shell subprocess)
   - **Control arm verified:** Codex `hooks.md` (38KB) grepped for `"type": "module"`, `function hook`, `register(`, `Register` — **0 hits**; known-present term `"type": "command"` → 10+ hits

3. **Session-start availability for watchdog spawning:**
   - Claude Code: Has SessionStart hook ✓; can wire function hooks to run at session init
   - Codex: Has SessionStart hook ✓; CAN wire shell commands; NO module-level init
   - **Both already wire `mise run doctor` at SessionStart** (`.claude/settings.json` + `.codex/hooks.json`)

4. **Codec equivalence table** (from res-hook-map):
   - 9 hooks are 1:1 equivalent: SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, SubagentStart, SubagentStop, Stop, PreCompact, PostCompact
   - Claude has 33 documented hook events; Codex has 11
   - Codex has no Setup, InstructionsLoaded, MessageDisplay, FileChanged, CwdChanged, DirectoryAdded, WorktreeCreate/Remove, ConfigChange, PreModelSwitch, PostModelSwitch, Elicitation, or TaskCreated/Completed equivalents

5. **Subagent blocking:**
   - **Both systems document SubagentStop as advisory-only** (cannot block) — res-hook-map line 206
   - **Codex SessionStart cannot block** — command hooks only; no `permissionDecision` field
   - Implication: Lifecycle hooks cannot prevent a subagent from spawning or completing; they can only inject context or report findings

**Conclusion:** A watchdog agent is NOT spawned via lifecycle hooks. Instead, hooks run commands that produce findings (via `mise run doctor` or custom scripts) and inject context into the session. The session itself handles the response.

### A2. Function Hooks: Design Constraints

**Tracked document:** `docs/research/kb/reports/agents/rec-fnhook-intent-2026-09-14.md` (9 KB; intent audit against #1024 spec)

**Key findings:**

1. **Function hooks were NOT required to spawn agents** — they run on SessionStart and report status
   - Requirement: "SessionStart hook fires and supplies context" (#1024 user story 1) ✓ DELIVERED
   - Implementation: `.claude/skills/claude-doctor/hooks/register.ts:181-203` — reads file, calls `claude doctor`, surfaces finding in `additionalContext`

2. **Runtime failures fail OPEN and SILENT — this is deliberate design** (rec-fnhook line 54, 169-182)
   - Documented in register.ts docstring: "Function-hook runtime failures are silent and fail open"
   - Consequence: Broken handler → hook skipped, tool proceeds, model told success
   - Control arm: `fnhook_gates.py` tests validate that invalid shapes fail build-time gates only

3. **plugin-health and dependency-currency do NOT run by default** (rec-fnhook line 100-126)
   - Both are in `LIVE_CHECKS`, NOT in `CHECKS`
   - SessionStart hook does NOT pass `live=True` flag
   - **Only run via:** `mise run doctor -- --live` (user-initiated) or in test contexts
   - **Therefore: Do NOT block session start by default**

4. **No "zero outdated dependencies" requirement was found** (rec-fnhook line 160)
   - Searched #1024, #1044, session memories; NOT found in any stated requirement
   - Status: REFUTED (dependencies are informational only)

**Consequence for watchdog implementation:** A watchdog agent cannot be spawned from a lifecycle hook to enforce things. Instead, hooks call `mise run doctor` or similar command-line tools that gather findings. The lead session reads those findings and decides what to do.

### A3. Subagent Messaging Capability (Correction)

**Research reference:** `docs/research/kb/reports/agents/docs-subagents-deep.md` (comprehensive surface reference)

**The claim I made incorrectly:** "Subagents cannot message other subagents."

**The correct statement** (from the SDK and docs):
- Subagents with `SendMessage` tool CAN message other named agents
- The harness provides `SendMessage` to **background subagents** (base pool, line `336` in subagent reference) AND to **teammates** (agent-team specific, line `338`)
- On spawn, subagents receive the active roster of other named agents as a system-reminder

**Key constraint (not a prohibition):**
- `SendMessage` is hardened **against being a consent channel** (`agent-teams.md:265`)
- A subagent cannot use `SendMessage` to the lead to ask permission; the lead approves via its own `AskUserQuestion` in the main session
- **`AskUserQuestion` is removed from every subagent** (filter 1, unconditional) — cannot ask at all inside a delegate

**Operational design consequence:** Subagents CAN coordinate via `SendMessage`, but decisions must flow through the lead (which has `AskUserQuestion`). Delegated work cannot make standalone judgment calls.

---

## Implications for Watchdog Rule Implementation

### 1. Watchdog Agent Cannot Be Spawned from a Lifecycle Hook

**Finding:** Both Claude Code and Codex hooks support SessionStart, but:
- They can run commands or inject context
- They cannot spawn agents or make approval decisions
- They are advisory-only (cannot block)

**Alternative design:** Wire a `SessionStart` hook to run `mise run doctor` or a custom watchdog CLI tool that writes findings to a file or stderr. The lead session reads those findings and routes work accordingly.

### 2. Function Hooks Fail Silent on Error

**Finding:** TypeScript function hooks are **advisory-only on failure**. A broken handler silently gets skipped.

**Implication for watchdog:** If using function hooks for visibility/reporting, wrap the handler in error-handling that always returns valid JSON. Never rely on hook errors to cause a session abort.

### 3. Watchdog Checks Should Be Non-Blocking by Default

**Finding:** The doctor architecture explicitly separates `CHECKS` (always) from `LIVE_CHECKS` (opt-in with `--live`). SessionStart runs only `CHECKS`.

**Implication:** High-volume/subprocess-heavy watchdog checks should go in `LIVE_CHECKS`, not in the SessionStart path. Keep SessionStart path file-only (read doctor.toml, read graphify cache, etc.).

---


**Alternative design approaches for watchdog enforcement:**

1. **PreToolUse hook spawning a watchdog agent** (LIVE docs `hooks.md:3442-3475`, `:3580`)
   - Event: `PreToolUse`
   - Handler type: `agent` (documented at line 3580: "spawns a subagent")
   - Capability: Can spawn an agent that inspects tool call and decides `{"ok": true/false}`
   - Advantage: Real-time enforcement at tool-call time
   - Disadvantage: Subprocess latency; every tool call blocks on agent spawn
   - **Codex equivalent: NONE** (Codex PreToolUse is `type: command` only; cannot spawn agents)

2. **SessionStart hook running advisory checks** (both systems support)
   - Approach: Hook runs `mise run doctor -- --live` (subprocess) and injects findings
   - Advantage: Both Claude and Codex support; no tool-call latency
   - Disadvantage: Checks run once per session, not per tool call; cannot block

3. **PreToolUse hook running command-only validation** (both systems support)
   - Approach: Hook runs a shell command that exits 0/non-zero; Claude respects exit code
   - Advantage: Both systems support; per-tool-call validation
   - Disadvantage: Codex hook exit codes may not block (requires verification); latency on every tool call

4. **Agent team with watchdog teammate** (Claude only)
   - Approach: Spawn a dedicated watchdog teammate at session start; route tool calls through it via `SendMessage`
   - Advantage: Structured team coordination; clear separation of concerns
   - Disadvantage: Tooling support required; operator approval needed for team-based design

---

## B. The 159 Guard Fail-Opens: What They Are

**Source location:** `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/command-audit.md`, lines 19-32 (summary table)

**Recorded as:** 
- `guard-error-rc=1`: 158 instances
- `interpreter-absent`: 1 instance
- Most recent: `2026-09-14T02:13:05Z`

**Where recorded:** Only in `command-audit.md` report; NOT in session transcripts or session-review metadata. The hook failed silently (allowed the command), so the only trace is in the audit aggregation.

**What shape they represent:**

| Metric | Value | Interpretation |
|---|---|---|
| Total sessions scanned | 50 | Commands from 50 recent sessions |
| Total commands audited | 19,256 | Includes diagnostic, gate, mise, one-off, and blocked |
| Guard fail-opens | 159 | Commands that matched a rule but guard could not run |
| **Commands that then passed** | 159 | Since guard did not run, no denial was issued |
| Rules that would have applied | Unknown (audit does not reconstruct) | Would require re-running guard against stored commands with a working guard |

**The audit cannot answer:** Which 159 commands would have been denied if the guard had run. The audit only knows the guard errored.

**Why it matters:**

- 0 bypasses **despite** the guard running (working correctly when it runs)
- But 159 **silent successes** where a denial may have been intended

**Operational consequence:** Guard fail-opens are the real risk class — a prohibition was intended but silently allowed. The 59 successful denials (working) prove the guard catches things when it runs; the 159 fail-opens prove it sometimes cannot.

**Remediation:** Log guard errors visibly (stderr or session context) so future audits can reconstruct which rules applied and which commands evaded due to guard failure, not due to guard design.

---

## C. Codex Hook Surface and Guard Capability

**Citation:** `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/hooks.md` (939 lines; fully read 2026-09-14)

**Complete Codex hook inventory by support type:**

| Event | Type Supported | Blocking | Tool Input | Output |
|---|---|---|---|---|
| SessionStart | `command` only | NO (advisory) | stdout/stdin | `additionalContext` injection |
| UserPromptSubmit | `command` only | NO | stdout/stdin | Context injection |
| PreToolUse | `command` only | ⚠️ UNCLEAR | stdout/stdin | Unknown if exit code blocks |
| PostToolUse | `command` only | NO | stdout/stdin | Context injection |
| PermissionRequest | `command` only | Possibly | stdout/stdin | `{"continue": true/false}` |
| SubagentStart | `command` only | ⚠️ UNCLEAR | stdout/stdin | Unknown |
| Stop | `command` only | NO (advisory) | stdout/stdin | Context injection |
| PreCompact | `command` only | Possibly | stdout/stdin | Unknown if blocking exit code supported |
| PostCompact | `command` only | NO (advisory) | stdout/stdin | Context injection |

**Key constraint:** Codex has **NO `type: agent` handler**. All hooks are `type: command` only (shell subprocess).

**Control arm for "command only":** 
- Grep `hooks.md` for `"type": "agent"` → **0 hits** (unknown-absent)
- Grep `hooks.md` for `"type": "command"` → **12+ hits** (known-present, discriminates)
- Grep `hooks.md` for `"type": "prompt"` → **1 hit** (mention only, not supported)
- Documented function/module hook → **0 hits** (unknown-absent)

**Can Codex be guarded at tool-call time?**

YES, but ONLY via command-type PreToolUse hooks:
- Hook runs shell command receiving JSON on stdin (tool name, input)
- Hook exits 0 (allow) or non-zero (block) — **if Codex honors it** ⚠️
- **VERIFICATION NEEDED:** Codex documentation does not explicitly state whether PreToolUse exit code blocks the tool call. Claude Code does (`hooks.md` in knowledge-base states this explicitly). Assume Codex supports it but verify before committing a guard to production.

**Can Codex run a PreToolUse hook that spawns an agent?** NO.
- Codex PreToolUse is `type: command` only
- Would need to be `type: agent` to spawn a subagent
- Codex has no `type: agent` support

**Implication:** A PreToolUse watchdog agent (Claude only) cannot be ported to Codex. Codex guards must be command-based, non-blocking, and advisory-only unless Codex PreToolUse exit codes block (unconfirmed).

---

## Summary: Three Guard Strategies and Their Reach

| Strategy | Claude | Codex | Blocking | Notes |
|---|---|---|---|---|
| **SessionStart advisory checks** | ✓ Works | ✓ Works | NO | Both systems; findings only; runs once per session |
| **PreToolUse command hook** | ✓ Works | ✓ Works (TBD) | MAYBE | Command-based validation; Codex blocking unconfirmed |
| **PreToolUse agent hook** | ✓ Works | ✗ Not supported | YES | Claude only; spawns watchdog agent per tool call |
| **Agent team watchdog teammate** | ✓ Works | ✗ Not supported | Manual | Claude only; team-based coordination |

---

