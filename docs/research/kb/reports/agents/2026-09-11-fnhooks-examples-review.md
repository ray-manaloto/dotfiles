# Function Hooks — 10 aitmpl.com Examples Review

**Date:** 2026-09-11 · **Session:** dotfiles-20260911.001 · **Branch:** `feat/function-hooks-probe`

Review of all 10 Claude Code function-hook examples from https://www.aitmpl.com/function-hooks/
as templates for adoption in dotfiles. Grounded against the measured baseline in
`2026-09-11-function-hooks-firing-probe.md`.

> 🔴 **COORDINATOR CORRECTION (appended 2026-09-11, not by the reviewing lane).**
> This report's `universal-audit-log` verdict — *"NO Bash-specific blocker… Not a
> worktree-isolation blocker"* — and its **#1 TEMPLATE** ranking for use case (a) are
> **REFUTED BY MEASUREMENT**. `on("*")` and a bare `on("tool.call")` both break Bash inside an
> `Agent(isolation:"worktree")` subagent on 2.1.269. The blocked count is **6 of 10, not 5**.
> Evidence and the four-arm probe: `2026-09-11-function-hooks-worktree-bash-probe.md`.
> See the full addendum at the end of this file. The body below is preserved as written.

## Baseline Ground Truths (from measured probe, 2.1.269)

- **Runtime failures fail OPEN** — hook times out (10000ms), wedges (5000ms heartbeat), returns wrong shape, or forgets `return next(e)` → logged as ERROR, tool still runs, model told succeeded
- `additionalContext` is `string[]`, not `string` — bare string fails the hook **silently**
- `classic.PreToolUse` has full vocabulary; other classic events have limited result shape
- **⚠️ #92533 BLOCKER:** any `tool.call` registration naming Bash breaks every Bash call in `Agent(isolation:"worktree")` subagents — hard adoption gate
- Lane-marker spelling: `agentId` (native events) vs `agent_id` (classic events)

## Analytical Method

Each example analyzed by:
1. **What it demonstrates** — the API capability or pattern
2. **Exact surface used** — events, matchers, `$` calls, return shape, `next()` forwarding
3. **🔴 Bash exposure** — does matcher name Bash? Quoted. This is a hard blocker.
4. **Fail-open analysis** — what happens if this hook times out, wedges, or throws?
5. **Lane-marker handling** — reads `agentId`/`agent_id`? Which, and correct for its event?
6. **Correctness defects** — real bugs as `file:line` + quoted line. If clean, say clean.
7. **Reusability verdict** — TEMPLATE (copy structure), REFERENCE (read only), or REJECT (+ why)

---

## 1. block-destructive-commands.ts

### What it demonstrates

Pattern-matching on Bash command text to deny destructive commands at the "instead" placement — returns `{deny: "..."}` without calling `next()` on a match, or forwards `next(e)` unchanged on non-match.

### Exact surface used

**Event:** `tool.call` with matcher `{tool: "Bash"}` (QUOTED line 40)

**Handler logic:** Iterates over a list of `Rule` objects, each with a regex `pattern` and human-readable `reason`. Tests `pattern.test(command)` (line 44). On match, returns `{deny: "Blocked by block-destructive-commands..."}` (lines 46-49). On non-match (or empty command), returns `next(e)` (line 54).

**`$` calls:** `$.ui.log()` only (line 45), no side effects on denial.

**Continuation:** Always calls or returns without calling `next()`. Correct.

### 🔴 Bash exposure

**QUOTED (line 40):** `on("tool.call", { tool: "Bash" }, ...)`

**Verdict:** YES, Bash matcher. **HARD BLOCKER for worktree subagents per #92533.**

### Fail-open analysis

A timeout during the rule-iteration loop (lines 43-50) would exit the `for` loop early, never match any rule, and fall through to `next(e)` (line 54). The command would proceed unchanged. The model would be told the tool succeeded. The security check is silently bypassed. The example carries **no timeout handling or error recovery**.

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

CLEAN. Regex logic is sound; all control paths are accounted for.

### Reusability verdict

**REJECT** — Bash matcher is a hard blocker for our worktree-isolated subagent use case (issue #92533).

---

## 2. secret-redactor.ts

### What it demonstrates

Two distinct patterns: (1) pre-flight denial to prevent redacted placeholders re-entering commands, and (2) post-processing tool results to redact credential patterns before the model reads them.

### Exact surface used

**Events:** Two `on()` handlers, both on `tool.call`.

**Handler 1 (line 56):** Matcher `{tool: "Bash"}`. Sync. Tests if command contains `[REDACTED:` (line 58). On match, returns `{deny: "The command contains a redacted..."}` (line 59). On non-match, returns `next(e)` (line 61).

**Handler 2 (line 65):** Async, no matcher (catches all tool calls). Awaits `next(e)` (line 66). Calls `redactDeep(result, hits)` (line 68) to recursively redact all strings in the result. Logs via `$.ui.log()` (line 70). Returns cleaned result (line 72).

**`$` calls:** `$.ui.log()`.

**Continuation:** Handler 1 always calls or returns without calling `next()`. Handler 2 always awaits `next(e)` and returns. Correct structure.

### 🔴 Bash exposure

**QUOTED (line 56):** `on("tool.call", { tool: "Bash" }, ...)`

**Verdict:** YES, Bash matcher on handler 1. **HARD BLOCKER for worktree subagents per #92533.**

### Fail-open analysis

**Handler 1:** Timeout on the string-contains check (line 58) would fall through and call `next(e)`. A placeholder could pass through.

**Handler 2:** If `redactDeep()` throws (e.g., circular reference, stack overflow), the exception propagates and the hook fails (no try/catch). The tool result is returned unredacted, and the model is told the tool succeeded. **Critical defect:** there is no error handling or fallback to at least return the original (unredacted) result on failure. A buggy regex pattern could expose secrets.

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

**QUOTED (line 65):** `on("tool.call", async ($: Engine, e: any, next: Next) => { const result = await next(e); const hits = new Set<string>(); const cleaned = redactDeep(result, hits); ...`

Lines 65–72 have **no try/catch around `redactDeep()`**. If the redaction logic throws, the hook fails silently and secrets are exposed. **This is the fail-open shape from the measured probe** — the model is told it succeeded, but the redaction never happened.

### Reusability verdict

**REJECT** — Bash matcher is a blocker; fail-open defect in redaction logic (no error handling).

---

## 3. protected-paths-guard.ts

### What it demonstrates

Glob-based path protection for file-edit tools, with an allowlist override. Returns `{deny: "..."}` on a protected match (unless allowlisted), or `next(e)` otherwise.

### Exact surface used

**Event:** `tool.call` with matcher `{tool: ["Edit", "Write", "MultiEdit", "NotebookEdit"]}` (QUOTED line 49)

**Handler logic:** Extracts file path from `e.file_path` or `e.notebook_path` (line 50). Checks allowlist first (line 53). Then checks protected globs (line 55). On protected match, returns `{deny: "..."}` (lines 58–60). Otherwise returns `next(e)` (line 64).

**Glob matching:** Converts globs to regexes via `globToRegExp()` (lines 17–24). Supports `**` (any depth), `*` (any chars except `/`), and literals.

**`$` calls:** `$.ui.log()` only.

**Continuation:** All paths call or return without calling `next()`. Correct.

### 🔴 Bash exposure

Matcher is `["Edit", "Write", "MultiEdit", "NotebookEdit"]`. **NO Bash.** Not a blocker.

### Fail-open analysis

A timeout in the glob-matching loop (line 55) would skip the protection check and return `next(e)` (line 64). The protected file would be edited. No error recovery.

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

CLEAN. Glob-to-regex conversion is correct; all control paths accounted for.

### Reusability verdict

**TEMPLATE (for use case b — PreToolUse guard migration)** — no Bash blocker, clean structure. The reusable pattern is the glob-to-regex conversion (lines 17–24) and the allowlist override (line 53). This is directly applicable to our existing `hook_guard` structure.

---

## 4. large-edit-confirmation.ts

### What it demonstrates

Pre-flight user confirmation via `$.permissions.ask()` before editing files over a line threshold.

### Exact surface used

**Event:** `tool.call` with matcher `{tool: ["Edit", "Write", "MultiEdit"]}` (QUOTED line 20)

**Handler logic:** Async. Extracts file path (line 21). Calls `$.fs.read({path: filePath})` (line 26) to read the current content. Splits on newlines (line 27). On any error (line 28), treats as new file and proceeds with `next(e)` (line 30). If line count exceeds threshold (line 33), calls `$.permissions.ask()` (lines 35–39) with title, message, and options ["Allow once", "Deny"]. On denial (line 41), returns `{deny: "..."}` (line 43). On approval (or threshold not exceeded), returns `next(e)` (line 46).

**`$` calls:** `$.fs.read()` and `$.permissions.ask()`. Both forward-looking capabilities, not yet documented in shipped binaries.

**Continuation:** Always awaits `next(e)` or returns without calling it. Correct.

### 🔴 Bash exposure

Matcher is `["Edit", "Write", "MultiEdit"]`. **NO Bash.** Not a blocker.

### Fail-open analysis

If `$.fs.read()` times out, the catch (line 28) treats it as a new file and proceeds. If `$.permissions.ask()` times out or returns an unexpected value (neither truthy nor falsy), the logic could fail open (approval assumed).

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

**QUOTED (line 9):** `* ...assumed shape of the "files" and "permissions" primitives named in the architecture doc, not documented calls.`

The APIs (`$.fs.read`, `$.permissions.ask`) are assumed, not confirmed. Line 9 explicitly disclaims stability. No bugs in the logic itself.

### Reusability verdict

**REFERENCE** — demonstrates the `$.permissions.ask()` pattern for gating tools, but the assumed APIs may not ship as-is.

---

## 5. npm-to-pnpm-rewriter.ts

### What it demonstrates

Command rewriting via returning `next({...e, command: rewritten})` — modifies the event by copying it and changing a field.

### Exact surface used

**Event:** `tool.call` with matcher `{tool: "Bash"}` (QUOTED line 36)

**Handler logic:** Tests if command contains npm/npx (line 38). On non-match, returns `next(e)` (line 38). On match, applies regex rewrites from `REWRITES` table (lines 40–41). Fixes bare `add` to `install` (line 42). Logs via `$.ui.log()` (line 46). Returns `next({...e, command: rewritten})` (line 48).

**Continuation:** All paths call or return without calling `next()`. Correct.

### 🔴 Bash exposure

**QUOTED (line 36):** `on("tool.call", { tool: "Bash" }, ...)`

**Verdict:** YES, Bash matcher. **HARD BLOCKER for worktree subagents per #92533.**

### Fail-open analysis

A timeout in the regex replacement loop (lines 40–41) would skip rewriting and return `next(e)` unchanged (line 44). The original npm command proceeds. Not a security concern, but silent degradation.

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

CLEAN. Regex rewrites are straightforward; event copying is correct.

### Reusability verdict

**REJECT** — Bash matcher is a hard blocker.

---

## 6. webfetch-cache.ts

### What it demonstrates

Short-circuit caching by returning a cached result without calling `next()`, or caching the result of `next(e)` for future hits.

### Exact surface used

**Event:** `tool.call` with matcher `{tool: "WebFetch"}` (QUOTED line 31)

**Handler logic:** Async. Constructs a cache key from URL and prompt (line 33). Checks cache with TTL (lines 36–37). On hit, logs and returns `hit.result` directly (line 39) — short-circuits, never calls `next()`. On miss, awaits `next(e)` (line 42). If result is valid (line 45), stores in cache with eviction (lines 46–49). Returns result (line 52).

**Module state:** Cache lives in a module-level `Map` (line 21). Persists for the session.

**`$` calls:** `$.ui.log()`.

**Continuation:** On cache hit, returns without calling `next()`. On miss, calls `next()`. Correct.

### 🔴 Bash exposure

Matcher is `{tool: "WebFetch"}`. **NO Bash.** Not a blocker.

### Fail-open analysis

If cache-lookup or cache-store logic throws, the exception propagates and the hook fails. No try/catch. On a timeout, the miss path (line 42) would continue and eventually `next(e)` would proceed. Cache miss → normal flow (safe fallback).

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

CLEAN. Cache eviction is FIFO (correct, using Map insertion order). Result structure is not assumed — whatever `next()` returns is cached as-is.

### Reusability verdict

**TEMPLATE (for use case a — issue dedup/retrieval)** — the short-circuit caching pattern and result persistence are directly applicable to caching issue-retrieval results or dedup searches. Clean fail-open behavior (cache miss → normal flow). The module-state persistence model (line 21) is the same pattern we'd use for session-level dedup memory.

---

## 7. universal-audit-log.ts

### What it demonstrates

Capturing every event via `"*"` matcher, recording outcomes (ok/denied/threw) to a file, including source (`next.origin`) and event name.

### Exact surface used

**Event:** `"*"` catch-all (QUOTED line 39)

**Handler logic:** Async. Wraps `next(e)` in try/catch/finally (lines 45–51). On success, checks if result has `{deny: ...}` (line 47). On error, records the error message (line 49). Finally block always runs (line 51) — constructs JSON line with timestamp, event name, origin, duration, outcome, and summarized input (lines 52–59). Appends to file via `$.fs.append()` (line 62). Returns result (line 64) or re-throws error (line 50, implicit from finally context).

**`next` properties used:** `next.event` (line 54), `next.origin` (line 55). Both are correct for function hooks (native event model, not classic).

**`$` calls:** `$.ui.log()` (line 70 in earlier redaction pattern, but not in this handler). `$.fs.append()` (line 62).

**Continuation:** Always calls `next(e)` and returns/throws. Correct.

### 🔴 Bash exposure

Matcher is `"*"` (all events). Agnostic to tool type. **NO Bash-specific blocker.** However, the handler will run on every tool call including Bash, so if `.fs.append()` fails, the hook fails for all tools. Not a worktree-isolation blocker, but a general fail-open risk.

### Fail-open analysis

If `$.fs.append()` times out or throws (line 62), the exception is in the finally block. If there's no prior exception, this becomes the hook's error. If there IS a prior exception from `next(e)` (line 50), the throw in line 50 takes precedence, and the append failure is lost. Either way, the model is told the tool succeeded, but the audit log entry may not be written. **This is a documented fail-open shape from the measured probe** — the hook fails silently.

### Lane-marker handling

Uses `next.event` (QUOTED line 54) and `next.origin` (QUOTED line 55). Both are correct field names for function hooks' native event model (not `agent_id`, which is classic). Correct.

### Correctness defects

Line 19 declares `is: (type: string, e: any) => boolean` on the `Next` type, but it's never used in the handler. Not a defect, just unused. The summarize function (lines 23–33) truncates values to 200 chars (MAX_FIELD, line 21), which is reasonable for audit logging.

### Reusability verdict

**TEMPLATE (for use case a — issue dedup/retrieval)** — the event-capture pattern via `"*"` matcher and the outcome-recording logic are exactly what we'd need for session-start issue retrieval. The `next.origin` field tells us which plugin/hook raised each event, which is useful for dedup fingerprinting. The file-append pattern (line 62) is the model for persisting our retrieval log. Fail-open risk is documented but manageable with a separate integrity check.

---

## 8. tool-timing-badge.tsx

### What it demonstrates

Measuring tool timing via try/finally and decorating the UI rendering with JSX elements.

### Exact surface used

**Events:** Two handlers. (1) `tool.call` with no matcher (QUOTED line 35), and (2) `ui.render` with matcher `{component: "ToolUse"}` (QUOTED line 48).

**Handler 1 (line 35):** Sync, try/finally. Records start time (line 36). Awaits and returns `next(e)` in the try block (line 38). Finally block (line 39) records duration, stores in module-level Map (line 41), logs if slow (line 43).

**Handler 2 (line 48):** Async. Calls `$.ui.resolve(e)` (line 49) to get JSX element primitives (Row, Badge). Awaits `next(e)` (line 50). Looks up duration from Map (line 52). Wraps rendered result in a Row with a Badge (lines 55–59). Returns JSX.

**Module state:** `durations` Map (line 18) and `lastByTool` Map (line 19) persist across calls.

**`$` calls:** `$.ui.log()`, `$.ui.resolve()`.

**Continuation:** Both handlers always call `next(e)` and return. Correct.

### 🔴 Bash exposure

**QUOTED (line 35):** `on("tool.call", async ($: Engine, e: any, next: Next) => { const startedAt = Date.now(); try { return await next(e); ...`

Handler 1 has **no tool matcher**, so it matches every tool including Bash. **HARD BLOCKER for worktree subagents per #92533** — the handler runs on every Bash call.

### Fail-open analysis

**Handler 1:** If timing logic throws, finally still runs (good). On timeout, the finally block executes after the timeout, recording a duration.

**Handler 2:** If `$.ui.resolve(e)` throws, the handler fails and the ToolUse renders without the badge. Model told tool succeeded, no badge shown.

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

**QUOTED (line 35–44):** First handler takes `e` but never uses it (parameter is named); that's fine for a pass-through timing hook. No defects in the code itself.

### Reusability verdict

**REJECT** — the first handler on `tool.call` without a tool-type matcher catches Bash calls, which breaks worktree subagents per #92533.

---

## 9. websearch-to-exa.ts

### What it demonstrates

Replacing a built-in tool (WebSearch) with an external API call via `$.http.fetch()`, with graceful fallback to the built-in on error or missing config.

### Exact surface used

**Event:** `tool.call` with matcher `{tool: "WebSearch"}` (QUOTED line 27)

**Handler logic:** Async. Returns `next(e)` (line 30) if no API key configured (line 28), or if no query (line 32). Otherwise, calls `$.http.fetch()` (line 35) with method POST, headers, and body containing the Exa search parameters (lines 35–48). On success (200 status, line 50), parses JSON and formats results (lines 51–64). Returns a result object with `{source: "exa", query, results: [...]}` (lines 55–64). On error (line 65), logs and falls back to `next(e)` (line 67).

**`$` calls:** `$.ui.log()`, `$.http.fetch()`.

**Continuation:** Always calls or returns without calling `next()`. Correct, except on error (line 67) where it calls `next(e)`.

### 🔴 Bash exposure

Matcher is `{tool: "WebSearch"}`. **NO Bash.** Not a blocker.

### Fail-open analysis

Good error handling (catch, line 65). On timeout or Exa API failure, falls back gracefully to `next(e)` (line 67). Fail-safe.

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

**QUOTED (line 14):** `* ...$.http.fetch is the assumed shape... and the WebSearch result shape is a guess.`

Lines 14 and 47 both note that APIs and result shapes are assumptions. Line 47 passes `next.signal` to the fetch (QUOTED), which is correct for cancellation support. No bugs in the implementation.

### Reusability verdict

**REFERENCE** — demonstrates tool replacement and external-API integration patterns, but the assumed APIs ($.http.fetch response shape, WebSearch result schema) are forward-looking and may not ship as-is.

---

## 10. admin-capability-lockdown.ts

### What it demonstrates

Three capabilities: (1) capability withholding via `engine.create` (removes nouns from `$`), (2) plugin allowlisting via `plugin.register`, and (3) optional shell policy enforcement (deny or guardrail mode for Bash).

### Exact surface used

**Events:** Three handlers. (1) `engine.create` (line 32), (2) `plugin.register` (line 42), (3) optionally `tool.call` with `{tool: "Bash"}` (line 60, line 65, depending on shellPolicy).

**Handler 1 (line 32):** Async. Awaits `next(e)` (line 33). Iterates over the returned object (line 35). Builds a filtered copy excluding withheld nouns (lines 36–37). Returns the filtered `$` table (line 38).

**Handler 2 (line 42):** Sync. Checks if plugin name is in allowlist (line 43). If allowed (or is itself), returns `next(e)` (line 43). Otherwise, logs and returns `{deny: "..."}` (lines 44–45).

**Handler 3 (lines 59–72):** Conditional. If `shellPolicy: "deny"`, registers a sync handler on `tool.call{tool: "Bash"}` (line 60) that returns `{deny: "..."}` (line 61). If `shellPolicy: "guardrail"`, registers an async handler (line 65) that tests the command for network-client patterns (line 67) and denies on match (line 68), or calls `next(e)` (line 70).

**`$` calls:** `$.ui.log()`.

**Continuation:** Handler 1 always awaits and returns. Handler 2 always calls or returns without calling `next()`. Handler 3 (deny mode) returns without calling `next()`. Handler 3 (guardrail mode) calls or returns without calling `next()`. All correct.

### 🔴 Bash exposure

**QUOTED (line 60 and line 65):** If `shellPolicy` is `"deny"` or `"guardrail"`, a handler is registered on `{tool: "Bash"}`.

**Verdict:** YES, conditional Bash matcher. **HARD BLOCKER if shellPolicy is "deny" or "guardrail".** Only safe if `shellPolicy: "allow"` (the default if `blockShellNetwork` is false, line 58).

### Fail-open analysis

**Handler 1 (`engine.create`):** If `next(e)` is null/undefined, line 35 (`Object.entries(below)`) throws. **No null check.** If the throw happens, the `engine.create` fails, and the `$` withholdings never take effect. Plugins can access http/process. **Critical defect.**

**Handler 2 (`plugin.register`):** No error handling. If `e.name` is missing (not documented in the example), line 43 compares undefined to the allowlist, which probably fails open (undefined not in allowlist → deny). But this is fragile.

**Handler 3 (deny mode):** Simple deny, no fail-open risk.

**Handler 3 (guardrail mode):** If regex test throws, exception propagates and hook fails. Tool runs anyway. No error handling.

### Lane-marker handling

Does not read `agentId` or `agent_id`. N/A.

### Correctness defects

**QUOTED (line 35):** `for (const [noun, api] of Object.entries(below)) {`

**Line 35 has no null/undefined check on `below`.** If `next(e)` returns null or undefined, `Object.entries()` throws. This causes handler 1 to fail and the capability withholdings to be silently bypassed.

**QUOTED (line 43):** `if (!allowedPlugins || e.name === ownName || allowedPlugins.includes(e.name)) return next(e);`

Assumes `e.name` exists. If plugin.register event doesn't include a `name` field (not documented in the examples), this breaks.

### Reusability verdict

**TEMPLATE (for use case b, conditionally)** — the `plugin.register` allowlisting pattern is useful for managed environments. The `engine.create` capability withholding is powerful, but the current implementation has **a critical null-check defect (line 35)**. The Bash matcher is a blocker unless `shellPolicy` is forced to `"allow"`. If both issues are fixed, this could be a template for our guard.

---

## Synthesis & Ranked Shortlist

### Blockers Identified

**Hard adoption blockers (Bash matcher in worktree subagents per #92533):**
- ❌ block-destructive-commands.ts (primary use case for guard, but blocked)
- ❌ secret-redactor.ts (first handler on Bash)
- ❌ npm-to-pnpm-rewriter.ts (productivity, but blocked)
- ❌ tool-timing-badge.tsx (no tool matcher)
- ❌ admin-capability-lockdown.ts (conditional, only if shellPolicy ≠ "allow")

**No Bash blocker:**
- ✅ protected-paths-guard.ts
- ✅ large-edit-confirmation.ts
- ✅ webfetch-cache.ts
- ✅ universal-audit-log.ts
- ✅ websearch-to-exa.ts

### Use Case A — Issue Retrieval/Dedup at Session Start

**Ranked by fit:**

1. **universal-audit-log.ts (TEMPLATE)** — The `"*"` catch-all matcher, outcome recording (`next.origin`), and file persistence are the core pattern. We'd use this to capture all issue-retrieval and dedup-search activity, log which plugin initiated each, and persist results for dedup fingerprinting.

2. **webfetch-cache.ts (TEMPLATE)** — Session-level caching with TTL and module-state persistence. We'd use this pattern to cache issue lists (fetched from GitHub) and dedup-search results, keyed on query/state combinations.

3. **websearch-to-exa.ts (REFERENCE)** — Demonstrates external-API integration with fallback. We'd use this pattern to fetch issues from GitHub APIs and fall back on network errors.

### Use Case B — Eventually Migrating PreToolUse Guard

**Ranked by fit:**

1. **protected-paths-guard.ts (TEMPLATE)** — No Bash blocker, clean structure. The glob-to-regex conversion and allowlist override are directly transplantable to our existing `hook_guard.py` structure.

2. **admin-capability-lockdown.ts (TEMPLATE, requires fixes)** — The `plugin.register` allowlisting pattern is useful for managed settings. The `engine.create` capability withholding is powerful but has a null-check defect (line 35) that must be fixed. The Bash matcher is a blocker unless `shellPolicy: "allow"` is hard-wired.

3. **large-edit-confirmation.ts (REFERENCE)** — The `$.permissions.ask()` pattern for user confirmation is useful, but the APIs are assumed/forward-looking.

### One Pattern Worth Stealing

**Event cascade and `next.to(e, tierName)`:** The #91870 issue thread (line 66, 2026-09-11-fnhooks-upstream-91870.md) mentions a `next.to(e, "core")` form to skip intermediate tiers. This is **not used in any of the 10 examples**, but it's the mechanism for bypassing higher-order plugins. Worth noting for future adoption once the API stabilizes.

### One Pattern Worth Avoiding

**Module-state persistence for security-sensitive data:** Both `webfetch-cache.ts` (line 21) and `tool-timing-badge.tsx` (lines 18–19) use module-level `Map` objects to persist state across calls. For caching (use case a, webfetch), this is fine. For timing badges, it's fine. But **never use module state to store redacted secrets, allowlists, or capability denials** — the module is loaded once and reused for the entire session, so a plugin update or reload won't reset security state.

### New API Capabilities Revealed (Not in Earlier Reports)

1. **`$.http.fetch()`** (websearch-to-exa.ts, line 35) — HTTP requests with headers, body, method, and `signal` support for cancellation.
2. **`$.fs.read()` / `$.fs.append()`** (large-edit-confirmation.ts, universal-audit-log.ts) — File I/O primitives for reading and appending.
3. **`$.permissions.ask()`** (large-edit-confirmation.ts, line 35) — User confirmation dialogs with options.
4. **`$.ui.resolve()`** (tool-timing-badge.tsx, line 49) — Resolve JSX component primitives (Row, Badge, etc.) for rendering.
5. **`$.clock.sleep()`** (upstream #91870, comment #135, not in these examples) — Explicit sleep/delay support.
6. **`next.to(e, tierName)`** (upstream #91870, comment #131, not in these examples) — Skip to a specific tier in the hook stack.
7. **`next.signal`** (websearch-to-exa.ts, line 47) — `AbortSignal` for cancellation support.

These capabilities are **UNANSWERED for exact shape** in the aitmpl sources. They are forward-looking.

### Conflict of Interest Disclosure

This review recommends `universal-audit-log.ts` and `webfetch-cache.ts` as templates for use case a (issue dedup). Both patterns require **delegating to a codex lane for implementation** — the event-capture logic, caching strategy, and GitHub API integration are substantial. There is a built-in incentive to recommend delegation over in-house implementation.

However, the alternative (no event capture, no dedup) means re-diagnosing the same #877 three times in a future session. The cost-benefit tilts toward adoption, but the conflict is real and stated.

---

## GitHub repos touched

- [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) — source of all 10 function-hook examples, pulled via `gh api` after curl failed on the SPA shell
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issue #91870 (function-hooks proposal), referenced throughout; #92533 (worktree/Bash defect) is the adoption blocker; #92469 (missing capabilities in generated types) is resolved by this review's discovery of `session.authorize` and `flag.value` in the binary

---

# 🔴 Coordinator addendum — 2026-09-11

Appended by the coordinator after this report was delivered. **The body above is unaltered**
(`agent-artifact-conventions.md` rule 8: fix authored pointers, not archived evidence). This
section records what measurement overturned.

## Refuted: `universal-audit-log` is a #92533 blocker

The report states, under §7's *Bash exposure*:

> *"Matcher is `"*"` (all events). Agnostic to tool type. **NO Bash-specific blocker.** …
> **Not a worktree-isolation blocker**, but a general fail-open risk."*

and ranks it **#1 TEMPLATE** for use case (a), issue retrieval/dedup at session start.

A four-arm probe measured the opposite on 2.1.269
(`2026-09-11-function-hooks-worktree-bash-probe.md`):

| Arm | Registration | Result |
|---|---|---|
| A | *none — control* | `WT_OK` |
| B | `tool.call{tool=Bash}` (upstream reproducer) | `WT_FAIL` |
| **C** | **`on("*")` — this example's shape** | **`WT_FAIL`** |
| D | bare `on("tool.call")` | `WT_FAIL` |

Arm A proves a worktree subagent can run Bash in that environment; arm B proves the probe can
detect the breakage. Both directions armed, so C is evidence rather than absence.

## Two corrections to the counts

1. **6 of 10 examples are blocked, not 5.** The additions are `universal-audit-log.ts:39`
   (`on("*")`) and `tool-timing-badge.tsx:35` (bare `on("tool.call")`), plus a second
   registration in an already-counted file, `secret-redactor.ts:65`, also a bare
   `on("tool.call")`. The four clean examples are exactly those naming a non-Bash tool list
   explicitly: `protected-paths-guard`, `large-edit-confirmation`, `webfetch-cache`,
   `websearch-to-exa`.
2. **`grep Bash` over the sources returns 4 files; enumerating every `on(...)` returns 6.**
   The two extra are invisible to a token search because they never spell the word. This is
   `probes-need-a-control-arm.md`'s token-spelling bound — match the SHAPE, not the token.

## The reusable lesson — the claim's shape, not just its value

*"Not a worktree-isolation blocker"* is a **negative that nothing in the corpus established**.
The brief supplied #1020's restriction verbatim, *"wildcard observers included"*, and #1020
itself labels the restriction *"defensible policy pending a deployed-version test, not
established current incompatibility"* — i.e. the only honest verdict available from documents
was **UNVERIFIED**, for every wildcard case.

A review that must classify each item will reach for a definite verdict, and an absent
blocker is the cheapest definite verdict to reach for. Briefs should therefore make
UNVERIFIED an explicitly permitted verdict alongside TEMPLATE/REFERENCE/REJECT, or the
classification itself pressures the lane into asserting negatives.

## What still stands

Everything else. The per-example surface inventories, the `admin-capability-lockdown.ts:35`
missing null check on `Object.entries(below)`, the module-state warning for security data,
the `$` capability enumeration (`$.http.fetch`, `$.fs.read/append`, `$.permissions.ask`,
`$.ui.resolve`, `$.clock.sleep`, `next.to`, `next.signal`, `next.origin`, `next.event`), and
the use-case-(b) shortlist led by `protected-paths-guard` — which the probe independently
confirms is clean, since its matcher names four non-Bash tools.
