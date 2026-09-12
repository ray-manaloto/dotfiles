# Function-hook implementations in the wild — GitHub code-search harvest

**Lane:** `fnhook-codesearch` · **Date:** 2026-09-11 · **Branch:** `feat/function-hooks-probe`

Data-collection sweep of public GitHub for real Claude Code **function hook**
implementations. Raw bytes for every file cited here are on disk under
`.agent/kb/raw/fnhook-harvest-*`; the merged search hit list is
`.agent/kb/raw/fnhook-harvest-hits.md`.

Labels: **QUOTED** = verbatim bytes from the fetched file. **PARAPHRASED** =
my summary of bytes I read. **INFERRED** = my conclusion, not stated by the
source.

## Method and control arms

All searches ran through `gh api -X GET search/code`, authenticated. Every
call returned `rc=0`; no rate-limit or auth failure occurred, so every zero
below is an answer rather than a missing probe.

| Arm | Query | `total_count` |
|---|---|---|
| POSITIVE control | `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | **10960** |
| NEGATIVE control | `ZZQQXXVVBBNNMM_nonexistent_token_20260911` (invented fresh for this run) | **0** |

The same command shape returns five figures on a token known to be present
and zero on a token invented for this run, so the probe discriminates in
both directions.

| # | Query | `total_count` |
|---|---|---|
| q1 | `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` | 77 |
| q2 | `tengu_plugin_hooks_modules` | 77 (a *different* 77 — diffed) |
| q3 | `"export const register" claude-code path:hooks` | 2 |
| q4 | `filename:hooks.json "modules"` | 625 (noisy) |
| q5 | `"classic.PreToolUse"` | **4** |
| q6 | `"classic.SessionStart"` | **3** |
| q7 | `"PreToolUse" "modules" filename:hooks.json` | 173 |
| q8 | `filename:hooks.json path:.claude/skills` | 118 |
| q9 | `"tool.call" "register" extension:ts` | 6400 (useless) |
| q10 | `"next.to(" claude-code` | **4** |
| q11 | `repo:anthropics/claude-code "modules"` | 16 |

## Repos harvested (bytes on disk)

Every file below was fetched via `raw.githubusercontent.com` at the SHA or ref
named, and saved under `.agent/kb/raw/fnhook-harvest-*`. `pushed_at` read from
`gh api repos/<r>` at harvest time — all are days old, so none is a stale
example targeting a dead API shape.

| owner/repo | pushed_at | stars | what was fetched |
|---|---|---|---|
| `anthropics/claude-code` | 2026-09-11T19:17:55Z | 144786 | **`mods/` — 3 complete function-hook plugins**, 580 blobs |
| `asgeirtj/system_prompts_leaks` | 2026-09-09T22:44:38Z | 64909 | `claude-code.d.ts` (302 KB, 7966 lines) — the API's own declarations |
| `yonatangross/orchestkit` | 2026-09-11T14:49:35Z | 236 | `scripts/validate-fn-hooks-canary.sh` |
| `lossless-claude/lcm` | 2026-09-12T02:24:12Z | 26 | `hooks/lcm-hooks.ts` (498 ln), `hooks.json`, `docs/hook-protocol.md` |
| `TheSmokeDev/taskchad-os` | 2026-09-11T00:29:58Z | 24 | `.claude/scripts/runtime/claude_function_hooks.py` |
| `pleaseai/honmoon` | 2026-09-12T02:09:02Z | 4 | `hooks/honmoon.ts` (634 ln), `hooks.json` |
| `noopz/commonplace` | 2026-09-05T06:24:55Z | 3 | `hooks/register.ts` (824 ln), `hooks.json`, `scripts/lib/module-gate.ts` |
| `djnsty23/claude-auto-dev` | 2026-09-12T02:27:24Z | 3 | `hooks/fn/autodev-fn.mjs` (155 ln), `hooks.json` |
| `bsamiee/Rasm` | 2026-09-11T03:19:54Z | 0 | `.claude/plugins/function-hooks/hooks/register.ts` (5.8 KB), `hooks.json` |
| `mahuebel/segmem` | 2026-09-11T17:34:59Z | 0 | `hooks/hooks.ts` (233 ln), `hooks.json` |
| `dodi-hq/dodi-skills` | 2026-09-08T08:45:47Z | 0 | `dodi-dev/hooks/hooks.js` (88 ln), `hooks.json` |
| `cam-douglas/hermes-playground` | 2026-09-12T02:03:21Z | 0 | `projects/gland/hook/gland.mjs` (506 ln), `data/92533.json` |

**12 repos with fetched bytes**, of which **10 carry a real `register` module**
(`anthropics/claude-code` counts as three). `davila7/claude-code-templates` was
deliberately skipped — a sibling lane owns it.

---

# The four open questions

## Q1 — Fail-open mitigation

### There is a first-class API for it, and NOBODY in the wild uses it

**QUOTED** — `asgeirtj/system_prompts_leaks` —
`Anthropic/claude-code/skills/plugin-authoring/reference/claude-code.d.ts:4571-4585`:

```typescript
/**
 * What `on(...)` returns for a hook of type `F`: the registration, which
 * takes one `.catch` (CatchHandler); without it a failed hook is absent.
 *
 * A second `.catch` on one registration throws, as does one after
 * register() returned and one on `engine.create`, whose hook has no budget
 * and whose failure is the load's.
 */
export type Registration<F> = {
    /**
     * Sets the handler run when the hook throws or overruns its budget; its
     * answer within the grace stands as the hook's result for the dispatch.
     */
    readonly catch: (handler: CatchHandler<F>) => void;
};
```

and `:640-654`:

```typescript
/**
 * The handler `on(...).catch(handler)` takes for a hook of type `F`: the
 * hook's `($, e, next)`, run afresh when it throws, misreturns or overruns.
 *
 * `next` carries `error` and `called` (Caught) and is replay-safe. A return
 * within the grace is the hook's result, held to the event's shape as the
 * hook's is; `undefined` stands for `await next(e)`, the hook absent.
 */
export type CatchHandler<F> = F extends ($: infer D, e: infer E, next: infer N) => infer R ? ($: D, e: E, next: N & Caught) => R | undefined | Promise<Awaited<R> | undefined> : never;
```

The engine's own statement of the failure mode, `:2100-2102`:

> At every one, a hook that fails (throws, overruns its budget, answers a
> wrong shape) is skipped: the hooks beneath and core run in its place, or
> its last `next` result stands; the failure is reported, naming it.

**Usage in the wild: zero.** `CatchHandler claude-code` returns `total_count=8`
and the only relevant hit is the `.d.ts` itself; grepping all 10 harvested
modules for an `on(...).catch(...)` registration returns **0**. Not one of the
three upstream `mods/` uses it either.

⚠️ Caveat on that null: GitHub code search cannot express "`.catch` attached to
an `on(...)` call", so the 0 rests on (a) the `CatchHandler` identifier search
and (b) a full read of 10 harvested modules. A module I did not fetch could use
it. The positive/negative control arms above establish the search works; they do
not establish that this *particular* query shape is sufficient.

### What people actually do instead — three distinct patterns

**Pattern A — DUAL WIRING: declare `modules` AND classic `hooks` in the same
`hooks.json`, so a dead module degrades to the old behaviour rather than to
nothing.** Four of the eight third-party plugins do this
(`noopz/commonplace`, `mahuebel/segmem`, `pleaseai/honmoon`,
`djnsty23/claude-auto-dev`). It is the single most common mitigation found.

**QUOTED** — `noopz/commonplace` — `scripts/lib/module-gate.ts` (whole file is
the rationale; this is its header):

```typescript
/**
 * Whether the in-process hooks module is live for THIS session.
 *
 * WHY THIS IS NOT JUST AN ENV-VAR CHECK
 * `hooks/hooks.json` wires both the shell hooks and the in-process module on
 * purpose, so a broken module degrades to current behaviour rather than to
 * nothing. That only works if exactly one of the two does each job, and the
 * shell scripts decided by reading CLAUDE_CODE_ENABLE_FUNCTION_HOOKS.
 *
 * That gate is incomplete: the module ALSO loads for anyone in the
 * `tengu_plugin_hooks_modules` rollout, with no env var set anywhere. Such a
 * session would run both wirings — two prompt-context blocks per prompt, and
 * two concurrent index rebuilds per vault write, which is the exact race
 * v1.57.1 was written to remove.
 *
 * So the module announces itself instead of being inferred. At session start it
 * writes its session id to `<vault>/.wiki/<MODULE_MARKER>`, and a shell hook
 * stands down when that id matches the one on its own stdin payload. Comparing
 * ids rather than timestamps means no staleness window to tune: a marker left
 * behind by a previous session simply does not match.
 */
```

and its explicit fail direction:

```typescript
/**
 * True when the in-process module is handling this session's hooks.
 *
 * Fails OPEN (returns false, shell hook proceeds) on anything unreadable: a
 * missing marker is the normal case for the large majority of users, and
 * treating an unreadable one as "module is live" would silently disable the
 * shell hooks that are the whole plugin for them.
 */
```

`lossless-claude/lcm` converges on the same design independently —
**QUOTED**, `hooks/lcm-hooks.ts:1-6`:

```
// hooks/lcm-hooks.ts — lcm's function-hooks module (Claude Code early access).
//
// Loaded only when CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1. It claims the session in a temp-dir
// file at session.start, and while that claim stands the PostToolUse, PostToolUseFailure,
// UserPromptSubmit and Stop command hooks stay silent (functionHooksOwnSession in
// src/hooks/session-claim.ts) and this module does their work through the daemon:
```

and its ordering constraint, `:353-354`:

```typescript
    // Awaited, unlike the health probe: a command hook that runs before the claim lands
    // would record the same events this module is about to record.
```

**Pattern B — A VISIBLE LIVENESS TELL: make the module's absence observable in
the UI, because the failure is silent.** `djnsty23/claude-auto-dev` states the
whole problem and its answer in four lines —
**QUOTED**, `plugins/autodev-core/hooks/fn/autodev-fn.mjs:41-44`:

```
// A hook that throws is skipped and `next`'s result stands, so a defect here
// degrades to "no redaction on this call", never to a broken tool. The cost
// of that is silence, which is why the status line exists: its absence is the
// tell that the module is not running.
```

`$.ui.status` is written at both `session.start` and `turn.complete`, so a dead
module is visible on the prompt within one turn. `mahuebel/segmem` does the
same with `$.ui.status` / `$.ui.toast`, and every one of its `$.process.run`
calls has an `$.ui.log` failure branch.

**Pattern C — A CONTRACT CANARY in CI: pin the registered events and `$` calls
and fail the build when upstream moves them.** This is the only *mechanical*
mitigation found, and `yonatangross/orchestkit` (236 stars) is the sole
instance.

**QUOTED** — `scripts/validate-fn-hooks-canary.sh:1-20`:

```bash
#!/usr/bin/env bash
# Assert the upstream Function Hooks module contract has not moved (#3917).
#
# Runs `claude plugin validate` on tests/fixtures/fn-hooks-canary and requires
# the reported events and $ capabilities to match exactly. A rename or removal
# upstream turns this red, which is the point: OrchestKit is not migrating, so
# this is the mechanical half of "keep watching".
#
# Offline. No model call, no API key. Skips cleanly when the CLI is absent.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE="$REPO_ROOT/tests/fixtures/fn-hooks-canary"

# Measured on CC 2.1.263, 2026-09-08. Order is the module's registration order.
EXPECTED_HOOKS='tool.call{tool=Bash}, PreToolUse{}, session.start{}, engine.create{}, prompt.submit{}'
EXPECTED_CALLS='$.ui.log'
```

Two of its own control-arm notes are worth lifting verbatim:

```bash
# Capture rc around the parse. `grep` exits 1 on no match, and under
# `set -euo pipefail` a failing pipeline inside a command substitution kills the
# script: measured, a non-semver banner exited 1 with EMPTY output, which the CI
# step then reports as DRIFT. A version we could not read is its own outcome and
# must never be indistinguishable from a contract change.
```

```bash
# Capture rc separately: a swallowed non-zero here would read as a clean pass.
```

It also pins the floor version with a reason —

```bash
# The event vocabulary this fixture pins lands at 2.1.259, the same release that
# first carries CLAUDE_CODE_ENABLE_FUNCTION_HOOKS. Measured across seven binaries
# (#3917): at 2.1.251 and 2.1.257 the `modules` key is parsed but `session.start`
# is "not an event", so an older host fails here for a reason that is not drift.
# Skip rather than fail, and name the version so the skip is never mistaken for a
# pass.
MIN_CC="2.1.259"
```

**INFERRED:** `claude plugin validate <dir>` printing a per-module
`<file> hooks: …` and `<file> calls: …` line is the mechanism that makes a
contract canary cheap. `djnsty23/claude-auto-dev` independently reports the
runtime half — **QUOTED**, `autodev-fn.mjs:36-38`:

```
// inline. `claude plugin validate <plugin-dir>` lists what this file hooks and
// calls; an op it did not list is refused at run time.
```

**Pattern D (upstream, not third-party) — FAIL CLOSED where the hook is a
security control.** `anthropics/claude-code`'s `sec-default` states it twice.
**QUOTED**, `mods/sec-default/README.md`:

> A subject's provenance is the event's pinned `e.provider`; policy is read
> through `$.settings.read({ source: "policy" })`, one read serving a burst;
> both fail closed, so an unreadable policy counts as a policy in force.

and `mods/sec-default/hooks/register.ts` docstring: *"Provenance is the event's
pinned `provider`; policy is `$.settings.read`, memoized per burst; fail
closed."* Note the `tool.list` hook deliberately `.catch(() => undefined)`s the
policy read and lets `managedToolsRestored` decide — **QUOTED**:

```typescript
  on('tool.list', async ($, e, next) =>
    Policy.managedToolsRestored(
      await readPolicy(() => $.settings.read(Policy.SOURCE)).catch(
        () => undefined,
      ),
      await next.to(e, 'append'),
      await next(e),
    ),
  )
```

with the README's rule for that `undefined`: *"With no policy to read, or a
refusal from either listing, the organization's listing stands whole."*

### Nobody mitigates the `next(e)` omission

**INFERRED.** No repo guards against a handler forgetting `return next(e)`. The
discipline observed instead is structural: every third-party handler either
returns `next(e)` on its last line or is a `try { … } finally { }` around it.
`anthropics/claude-code`'s `diff` mod uses the `finally` form —
**QUOTED**, `mods/diff/hooks/register.ts`:

```typescript
  on('tool.call', { tool: [...Tools.SHELL_TOOLS] }, async ($, e, next) => {
    try {
      return await next(e)
    } finally {
      if (host && isPaneOpen) {
        scheduleRefresh(host)
      }
    }
  })
```

`noopz/commonplace` puts the guard inside the `catch` instead —
**QUOTED**, `hooks/register.ts:265-273`:

```typescript
  on("tool.call", { tool: "Bash" }, async ($: any, e: any, next: any) => {
    try {
      const verdict = checkBashCommand(String(e?.command ?? ""));
      if (verdict) return verdict;
    } catch {
      /* a broken guard must never block a command */
    }
    return next(e);
  });
```

## Q2 — Bash exposure (`anthropics/claude-code#92533`)

**Six of the ten harvested modules register a `tool.call` matcher that reaches
Bash — including Anthropic's own `diff` mod.** Every one of these is broken
inside an `Agent(isolation: "worktree")` subagent by #92533.

| repo | file | matcher, QUOTED |
|---|---|---|
| **`anthropics/claude-code`** | `mods/diff/hooks/register.ts` | `on('tool.call', { tool: [...Tools.SHELL_TOOLS] }, …)` where `SHELL_TOOLS = ['Bash', 'PowerShell'] as const` |
| `noopz/commonplace` | `hooks/register.ts:265` | `on("tool.call", { tool: "Bash" }, async ($: any, e: any, next: any) => {` |
| `noopz/commonplace` | `hooks/register.ts:345` | `on("tool.call", async ($: any, e: any, next: any) => {` — **unmatched, so every tool incl. Bash** |
| `mahuebel/segmem` | `hooks/hooks.ts:150` and `:171` | `on("tool.call", { tool: "Bash" }, async ($, e, next) => {` — registered **twice** |
| `pleaseai/honmoon` | `hooks/honmoon.ts:27,632` | `const TOOL_MATCHER = { tool: ['Read', 'Bash', 'Grep', 'WebFetch'] } as const` |
| `djnsty23/claude-auto-dev` | `hooks/fn/autodev-fn.mjs:78` | `on('tool.call', { tool: 'Bash' }, async ($, e, next) => {` |
| `bsamiee/Rasm` | `.claude/plugins/function-hooks/hooks/register.ts` | `on('tool.call', ($, e, next) => …)` — **unmatched, so Bash included** |
| `yonatangross/orchestkit` | `tests/fixtures/fn-hooks-canary` (per the canary's pinned string) | `tool.call{tool=Bash}` |

Not exposed: `dodi-hq/dodi-skills` (`{ tool: "SendMessage" }` only), and
`anthropics/claude-code`'s `sec-default` and `telemetry` mods.

`cam-douglas/hermes-playground` carries a structured fixture of the bug itself.
**QUOTED**, `projects/gland/data/92533.json`:

```json
  "note": "Primary fixture alias for #92533. Any function-hook tool.call on Bash breaks Agent isolation: worktree — every Bash call refused with isolation context lost. Faceplate: stripped.",
  "version": "2.1.263",
  "retriesObserved": 6,
  "telemetry": ["tengu_agent_worktree_cwd_escape_blocked", "context_lost"],
  "expected": "A passthrough function hook on Bash should not change where the command runs; pwd should print <repo>/.claude/worktrees/agent-xxx.",
  "actual": "Every Bash call refused, including pwd and true. Read/Edit and MCP keep working.",
  "hooks": [
    { "event": "tool.call", "tool": "Bash", "passthrough": true, "body": "next(e)" }
  ],
```

and its log line:

```
"[hook] on(\"tool.call\", { tool: \"Bash\" }, async ($, e, next) => next(e)) — pure passthrough",
"[agent] Agent(isolation: \"worktree\") · pwd refused · true refused · 6 retries · Read/Edit/MCP still work",
```

**The bug needs no logic at all** — a pure passthrough is enough. **No repo in
this harvest mitigates or works around it.**

## Q3 — `@skills-dir` deployment: NOBODY does this

**Zero.** No public repo ships a function hook from
`.claude/skills/<name>/.claude-plugin/plugin.json`.

| probe | `total_count` | verdict |
|---|---|---|
| `filename:hooks.json path:.claude/skills` | 118 | the path shape is common — **positive arm, the query works** |
| `filename:plugin.json path:.claude/skills` | 1408 | a plugin manifest under a skill dir is very common |
| `"modules" filename:hooks.json path:.claude/skills` | **1** | **the one hit is a FALSE POSITIVE** |
| `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS path:.claude/skills` | **0** | |

The single `"modules"` hit, `chrisalbright/devops-wiki` —
`.claude/skills/project-wiki/hooks.json` — was fetched and read. It has **no
`modules` key**; the search matched the word inside a `"type": "prompt"` hook's
prose (*"new modules, renamed files"*). Its actual content is a classic `Stop`
prompt hook and a `SessionStart` command hook.

The probe discriminates in both directions here: `path:.claude/skills` alone
returns 118 and `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` alone returns 77, so their
intersection returning 0 is an answer, not a blind query.

**What the wild does instead:** every fetched function hook ships from either a
plugin root (`hooks/hooks.json` beside `.claude-plugin/plugin.json`) or a
nested plugin dir — `bsamiee/Rasm` uses
`.claude/plugins/function-hooks/hooks/register.ts`, which is the closest
observed analogue to a clone-ready in-repo path.

## Q4 — `classic.*` in the wild

Complete result sets, not samples.

**`classic.PreToolUse` — `total_count = 4`**, of which exactly **ONE is real
third-party code**:

1. `bsamiee/Rasm` — `.claude/plugins/function-hooks/hooks/register.ts` — **CODE**
2. `asgeirtj/system_prompts_leaks` — `claude-code.d.ts` — type declaration
3. `davila7/claude-code-templates` — `dashboard/public/blog/…/index.html` — blog prose
4. `pleaseai/honmoon` — `.please/docs/research/md/001-…md` — research doc, not code

**`classic.SessionStart` — `total_count = 3`**, of which **ZERO are
third-party code**: the same blog post, plus two files in our own
`ray-manaloto/dotfiles`.

`"next.to("` — `total_count = 4`: `anthropics/claude-code` ×2
(`mods/sec-default/hooks/register.ts`, `.../managed-tools-restored.ts`),
`asgeirtj/system_prompts_leaks` (the `.d.ts`), and our own knowledge-base. **No
third party uses `next.to` at all** — consistent with the upstream README's
statement that it is refused outside a managed tier.

The one real `classic.*` use is a **wildcard with a matcher on
`hook_event_name`**, not a `classic.PreToolUse` registration.
**QUOTED** — `bsamiee/Rasm`:

```typescript
    on(
        'classic.*',
        {
            ['hook_event_name']: [
                'PostToolUse',
                'PostToolUseFailure',
                'PostToolBatch',
                'SubagentStart',
                'SubagentStop',
                'UserPromptSubmit',
                'Stop',
                'PostCompact',
                'SessionEnd',
            ],
        },
        ($, e, next) =>
            next.is('!classic.PreToolUse', e) && opened.kind === 'open'
                ? record($, opened, e.hook_event_name, e, CLASSIC).then(() => next(e))
                : next(e),
    );
```

Note `next.is('!classic.PreToolUse', e)` — a **negated event predicate** on
`next`, a surface none of the other repos touch.

`anthropics/claude-code`'s `sec-default` uses the bare wildcard:
`on('classic.*', ($, e, next) => next.to(e, 'append'))`.

---

# Catalogue

## Event-name frequency (10 harvested modules)

Counted by `grep -oE "on\(\s*['\"][a-zA-Z.*]+['\"]"` across the three upstream
`mods/` registers and the seven third-party modules.

| event | registrations | who |
|---|---|---|
| `tool.call` | **14** | every repo except `sec-default`/`telemetry` |
| `session.start` | 6 | Rasm, commonplace, lcm, autodev, diff, (segmem via shell) |
| `prompt.submit` | 6 | commonplace, segmem, lcm, honmoon, autodev, diff |
| `prompt.context` | 4 | commonplace, segmem, lcm, sec-default |
| `agent.spawn` | 4 | commonplace, segmem, dodi, sec-default |
| `turn.complete` | 4 | commonplace, lcm, autodev, diff |
| `ui.render` | 3 | commonplace (`AbovePrompt`), diff (`PromptHint`, `Pane`) |
| `command.run` | 2 | diff (`{command: Names.COMMAND_NAME}`, `{command:['clear','resume']}`) |
| `attribution.text` | 2 | autodev (`{kind:'commit'}`), sec-default |
| `tool.describe` | 2 | commonplace (`{tool:'Agent'}`), sec-default |
| `skill.prompt` | 2 | commonplace, sec-default |
| `prompt.section` | 2 | lcm (`{name:'memory'}`), sec-default |
| `classic.*` | 2 | Rasm, sec-default |
| `turn.*` | 1 | Rasm |
| `engine.create` | 1 | telemetry |
| `tool.register`, `tool.list`, `command.describe`, `agent.offer`, `settings.read` | 1 each | sec-default only |

## Matcher shapes observed

| shape | example | source |
|---|---|---|
| none (all subjects) | `on('tool.call', ($, e, next) => …)` | Rasm, commonplace |
| single string | `{ tool: "Bash" }` | commonplace, segmem, autodev |
| array (one-of) | `{ tool: ['Read','Bash','Grep','WebFetch'] }` | honmoon |
| array from a const | `{ tool: [...Tools.EDITING_TOOLS] }` | `anthropics/claude-code` diff |
| non-`tool` key | `{ component: 'Pane' }`, `{ component: 'PromptHint' }` | diff |
| non-`tool` key | `{ component: "AbovePrompt" }` | commonplace |
| non-`tool` key | `{ command: ['clear','resume'] }` | diff |
| non-`tool` key | `{ name: "memory" }` (a `prompt.section`) | lcm |
| non-`tool` key | `{ kind: 'commit' }` (an `attribution.text`) | autodev |
| classic-event key | `{ ['hook_event_name']: ['PostToolUse', …] }` | Rasm |
| wildcard event | `'classic.*'`, `'turn.*'` | Rasm, sec-default |

**QUOTED** — `noopz/commonplace` on the array form, correcting its own docs:

> A one-of matcher keeps this off every other tool. Our own docs said the
> matcher could not express two tool names; it can.

## What handlers return

| return | meaning | source |
|---|---|---|
| `next(e)` | pass through | universal |
| `next({ ...e, field })` | rewrite the input, then pass | autodev (`command`), segmem (`prompt`), honmoon (`text`), commonplace |
| `{ deny: reason }` | refuse the call | Rasm, segmem, dodi, autodev, commonplace, sec-default |
| `{ result }` | answer the tool yourself | `.d.ts` `tool.call` docstring |
| `{ ...built, context: [...(built.context ?? []), notes] }` | add hidden post-result context | commonplace, segmem, autodev, honmoon |
| `{ text: '' }` | terminal, `next` never called | autodev: `on('attribution.text', { kind: 'commit' }, () => ({ text: '' }))` |
| `{ ...beneath, telemetry }` | extend the engine interface | `anthropics/claude-code` telemetry mod, on `engine.create` |
| a render tree `{ type, props, children }` | draw | commonplace, diff |

**QUOTED** — `noopz/commonplace` on the `context` channel:

> `context` is exactly the PostToolUse `additionalContext` channel: "what the
> model reads after the tool's result and the user never sees". No transcript
> noise.

## `next(e)` vs `next.to(e, tier)`

`next.to` appears in **only** `anthropics/claude-code`'s `sec-default`.
**QUOTED**, `mods/sec-default/README.md`:

> It is a plugin folder like any other, but its one move that matters,
> `next.to`, is refused outside a managed tier, so loading it with
> `--plugin-dir` seats a plugin that can only pass.

Tiers are `prepend` / `user` / `append`, read off `next.origin.tier` and
`e.provider.tier`. **QUOTED**, `mods/sec-default/hooks/past-users/past-users.ts`:

```typescript
export function pastUsers<E extends Provided.Provided, R>(
  e: E,
  next: Provided.ProvidedNext<E, R>,
): Promise<R> {
  const isUsers = USER_REACHABLE_TIERS.includes(e.provider?.tier)

  return isUsers ? next(e) : next.to(e, 'append')
}
```

Other `next` surfaces seen in real code: `next.origin.tier` (sec-default),
`next.trace` and `next.event` and `next.is('!classic.PreToolUse', e)` (Rasm).

## `$` capabilities called (counted across the harvested modules)

`$.process.run` 39 · `$.ui.log` 36 · `$.session.cwd` 25 · `$.session.id` 14 ·
`$.ui.resolve` 13 · `$.ui.invalidate` 11 · `$.ui.status` 9 · `$.tool.call` 9 ·
`$.plugin.root` 9 · `$.http.fetch` 9 · `$.ui.open` 8 · `$.tool.register` 8 ·
`$.settings.read` 8 · `$.ui.notice` 7 · `$.session.messages` 7 ·
`$.clock.now` 7 · `$.session.repo` 6 · `$.model.fork` 6 · `$.model.complete` 6 ·
`$.command.run` 6 · `$.clock.sleep` 6 · `$.ui.close` 5 · `$.model.classify` 5 ·
`$.fs.ancestors` 5 · `$.command.register` 5 · `$.agent.spawn` 5 ·
`$.agent.list` 5 · `$.ui.toast` 4 · `$.store.get` 4 · `$.fs.write` 4 ·
`$.fs.exists` 4 · `$.command.list` 4 · `$.audio.speak` 4 · `$.tool.list` 3 ·
`$.store.set` 3 · `$.session.usage` 3 · `$.session.surface` 3 ·
`$.session.compact` 3 · `$.prompt.submit` 3 · `$.fs.stat` 3

⚠️ **PARAPHRASED caveat:** this count includes occurrences in doc comments, not
only call sites, and `honmoon.ts`/`gland.mjs` carry long explanatory headers.
Treat it as a ranking of *which nouns people reach for*, not as a call census.

The `diff` mod's `session.start` is the single densest capability list — it
binds sixteen of them into one host object in one expression
(`$.clock.now/after/every/sleep`, `$.process.run`, `$.fs.stat/list/read`,
`$.store.get/set`, `$.session.messages`, `$.ui.invalidate/status/log/open/close`,
`$.command.register`, `$.telemetry.mark/log`).

---

# Gotchas the authors wrote down

These are the highest-value bytes in the harvest. All **QUOTED**.

### The static scanner constrains how you may write `$`

`noopz/commonplace` — `hooks/register.ts:34-40`:

```
 * SCANNER CONSTRAINTS
 * The static scanner requires `register` to be a top-level const function, `on`
 * to take string-literal event names, and `$` to appear only as `$.noun.verb()`
 * at a call site — never bound, spread, stored or returned. It MAY be passed to
 * a function declared in THIS file (see `ensureVaultPath`), but never across an
 * import, so helpers in `lib/` take plain values or a Ports object of arrows.
```

`lossless-claude/lcm` — `hooks/lcm-hooks.ts:20-21`:

```
// `claude plugin validate` reads this file statically: `$` may only be passed to a function
// declared at the top level, and calls on it must be spelled `$.noun.method(...)`.
```

`djnsty23/claude-auto-dev` — `autodev-fn.mjs:33-38`:

```
// THE SCANNER'S RULE, which shapes every line below: `$` is only ever spelled
// `$.noun.event(...)` at a call site. It is never passed to a helper, bound,
// or read, so the helpers in this directory are pure and every `$` call is
// inline. `claude plugin validate <plugin-dir>` lists what this file hooks and
// calls; an op it did not list is refused at run time.
```

### A second `on()` for the same event, from the same plugin, silently replaces the first

`pleaseai/honmoon` — `hooks/honmoon.ts:629-631`:

```
  // One registration covers both placements: on 2.1.263 a second
  // `on("tool.call", …)` from the same plugin silently replaces the first, so
  // the before-check (PreToolUse on Read) and the after-redaction share a hook.
```

⚠️ **Unresolved conflict worth flagging.** `mahuebel/segmem` registers
`on("tool.call", { tool: "Bash" }, …)` **twice** in one module
(`hooks/hooks.ts:150` and `:171`). If honmoon's measurement on 2.1.263 holds,
segmem's first Bash hook (`check-note`, which can `{ deny }`) is silently dead.
I did not run a probe to settle it; it is a cross-check disagreement between two
repos, and the sibling firing-probe lane is better placed to arm it.

### The budget covers your hook's own work, not the time inside `next(e)`

`pleaseai/honmoon` — `hooks/honmoon.ts:509-511`:

```
  // The host budgets only the hook's own work, not the time inside `next(e)`
  // (measured on 2.1.263). Mirror that: one budget before the tool, a fresh
  // one after, so a slow tool never denies its own redaction.
```

### Returning while `next` is still pending ABORTS what runs beneath

`noopz/commonplace` — `hooks/register.ts:731-733`:

```
  on("turn.complete", async ($: any, e: any, next: any) => {
    // Let everything beneath run first; `next` resolves to the engine's answer.
    // A hook that returns while its next is pending aborts what runs beneath.
    const base = await next(e);
```

Corroborated upstream — `.d.ts` `tool.call` docstring: *"a hook that returns
while its `next` is pending aborts what runs beneath."*

### `$.process.run` takes an argv and runs NO shell

`noopz/commonplace` — `hooks/register.ts:215-218`:

```
      // `tail | tee` as two execs, because $.process.run takes an argv and
      // runs NO shell — there is no pipe and no `>` to use. `tee` without
      // `-a` truncates, which is exactly the write half of a rotation.
```

Its options object carries `timeoutMs`, `stdin`, `cwd` and `env`
(default timeout 30s) — **QUOTED**:

```typescript
          // The pipeline reindexes and may run impact + cross-domain, which
          // the 30s default is not always enough for on a large vault.
          timeoutMs: 120_000,
          env: { COMMONPLACE_HOOK_CHILD: "1" },
```

### Function hooks are SERIAL where shell hooks are PARALLEL

`noopz/commonplace` — `hooks/register.ts:280-286`:

```
   *   1. SERIAL BY CONSTRUCTION. Claude Code runs matching shell hooks in
   *      PARALLEL, which is how two `index.ts --incremental` processes ended up
   *      writing the same .wiki/*.jsonl files at once (v1.57.1). A hook that
   *      awaits `next(e)` and then runs the script cannot race itself.
   *   2. ONE payload shape. The script is invoked directly, so there is no
   *      `tool_input` nesting to get wrong — the bug that made `post-write` a
   *      silent no-op on every vault write.
```

### `ui.render`: one bad prop kills the whole tree, silently

`noopz/commonplace` — `hooks/register.ts:692-712`:

```
    // `$.ui.resolve`/`next` return Promises — a missing await yields undefined
    // JSX tags and the whole tree fails validation silently.
```
```
    // Props are a strict allowlist (BoxProps / TextProps) and ONE bad prop
    // fails the whole tree — at which point the engine silently draws its own
    // component instead. No `key` anywhere: only Button accepts one.
```
```
    // `base` may be null when nothing beneath renders. A null in `children`
    // fails the tree's validation, and a failed tree draws NOTHING — so the
    // band would vanish in exactly the case where it is the only content.
```

### Pinned status is ENGINE state and survives a module reload

`noopz/commonplace` — `hooks/register.ts:669-678`:

```
    // Clear the pinned status line unconditionally, not just when we think we
    // set one. It is ENGINE-side state: it survives a module reload and a new
    // session, so module state is not a reliable record of whether one is up.
    // A stale line from a previous build sat pinned above the prompt for
    // several turns precisely because nothing cleared what module scope had
    // forgotten about.
```

Same file on `prompt.submit`:

```
   * Must pass the prompt through untouched — a hook that returns anything but
   * `next(e)` here can rewrite or drop what the user typed.
```

### `prompt.context` carries no reason for firing

`lossless-claude/lcm` — `hooks/lcm-hooks.ts:393-396`:

```
 * `prompt.context` replaces the SessionStart command hook's stdout. It fires once per
 * conversation and again after compaction and `/clear` — the three moments the command
 * hook ran — but carries no reason for firing, so the daemon decides which content to
 * return from the mark `/compact` left for this session.
```

### One module per plugin

`djnsty23/claude-auto-dev` — `autodev-fn.mjs:9-10`:

```
// Four things a shell hook structurally cannot do, in one module because the
// loader takes one module per plugin:
```

### Types are generated, not shipped — re-typecheck after every CC update

`lossless-claude/lcm` — `hooks/lcm-hooks.ts:16-19`:

```
// Types: run /plugin-types in a session, then `import type { Register } from "claude-code"`.
// They are written from the running build and not committed, so the check is on demand:
// `npm run typecheck:hooks`. Run it after a Claude Code update too — the API is early
// access, and a green run is the answer to whether the release moved anything under this.
```

`anthropics/claude-code` — `mods/README.md`, on stability:

> Early access: hooks modules load only where function hooks are enabled, and
> the API these mods are written against may change between releases without
> notice.

### A rewritten `tool.call` result loses core's renderer

`djnsty23/claude-auto-dev` — `autodev-fn.mjs:148-151`:

```
        // A rewritten result cannot carry core's `ref`: core renders it with the
        // tool's own mapper from `result` alone. An untouched result keeps the
        // object it got, so core uses its own messages verbatim.
        return changed ? { result: scrubbed, context } : { ...out, context };
```

### The rollout flag means the env var is NOT a reliable liveness test

`noopz/commonplace` — `scripts/lib/module-gate.ts` (quoted in full under Q1):
the module "ALSO loads for anyone in the `tengu_plugin_hooks_modules` rollout,
with no env var set anywhere."

---

# Three complete `register` modules, VERBATIM

## 1. `anthropics/claude-code` — `mods/sec-default/hooks/register.ts`

https://github.com/anthropics/claude-code/blob/main/mods/sec-default/hooks/register.ts

```typescript
import type { On } from 'claude-code'

import { pastUsers } from './past-users'
import Policy from './policy'
import { TOOL_REGISTER_REFUSAL } from './tool-register-refusal'

/**
 * The built-in's hooks, seated outermost: each keeps one control an
 * organization has today out of reach of the plugins a person installs.
 *
 * Three moves: continue past the user tier (`next.to(e, "append")`), refuse
 * a user-tier caller by name, or pass. Provenance is the event's pinned
 * `provider`; policy is `$.settings.read`, memoized per burst; fail closed.
 *
 * @param on the engine's registrar
 */
export function register(on: On) {
  const readPolicy = Policy.createPolicyMemo(Policy.POLICY_MEMO_MS)

  on('classic.*', ($, e, next) => next.to(e, 'append'))

  on('prompt.section', ($, e, next) => next.to(e, 'append'))
  on('prompt.context', ($, e, next) => next.to(e, 'append'))
  on('skill.prompt', ($, e, next) => next.to(e, 'append'))
  on('attribution.text', ($, e, next) => next.to(e, 'append'))

  on('settings.read', ($, e, next) => next.to(e, 'append'))

  on('tool.describe', ($, e, next) => pastUsers(e, next))
  on('command.describe', ($, e, next) => pastUsers(e, next))
  on('agent.offer', ($, e, next) => pastUsers(e, next))
  on('agent.spawn', ($, e, next) => pastUsers(e, next))

  on('tool.register', async ($, e, next) => {
    const isOrgs =
      next.origin.tier === 'prepend' || next.origin.tier === 'append'

    if (isOrgs) {
      return next.to(e, 'append')
    }

    const isRefused =
      next.origin.tier === 'user' &&
      (await Policy.decidedByPolicy(
        readPolicy(() => $.settings.read(Policy.SOURCE)),
        Policy.hasMcpAllowlist,
      ))

    return isRefused ? { deny: TOOL_REGISTER_REFUSAL } : next(e)
  })

  on('tool.list', async ($, e, next) =>
    Policy.managedToolsRestored(
      await readPolicy(() => $.settings.read(Policy.SOURCE)).catch(
        () => undefined,
      ),
      await next.to(e, 'append'),
      await next(e),
    ),
  )
}
```

Its manifest, `mods/sec-default/hooks/hooks.json`:

```json
{
  "description": "Security default: from the outermost seat, continues past the user tier on the organization's classic hooks, prompt content, settings and subjects, refuses a user-tier tool.register under an MCP allowlist, and restores the organization's tools in tool.list",
  "modules": ["./register.ts"]
}
```

## 2. `anthropics/claude-code` — `mods/telemetry/hooks/register.ts`

https://github.com/anthropics/claude-code/blob/main/mods/telemetry/hooks/register.ts

```typescript
import type { On } from 'claude-code'

import { telemetryOf } from './telemetry-of'

/**
 * Registers the plugin's one hook: its engine.create step adds
 * `$.telemetry` over the nouns beneath, the plugin's own `$` as core built.
 *
 * `log` runs after the fold, reaching `$.session` and `$.http` through the
 * nouns beneath; each is one call on them.
 *
 * @param on the engine's registrar
 */
export function register(on: On) {
  on('engine.create', async ($, e, next) => {
    const beneath = await next(e)

    return {
      ...beneath,
      telemetry: telemetryOf({
        authorize: () => beneath.session.authorize(),
        id: () => beneath.session.id(),
        model: () => beneath.session.model(),
        environment: async () => ({
          userType: await beneath.env.get('USER_TYPE'),
          disableTelemetry: await beneath.env.get('DISABLE_TELEMETRY'),
          disableNonessentialTraffic: await beneath.env.get(
            'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC',
          ),
          doNotTrack: await beneath.env.get('DO_NOT_TRACK'),
          customOauthUrl: await beneath.env.get('CLAUDE_CODE_CUSTOM_OAUTH_URL'),
          useBedrock: await beneath.env.get('CLAUDE_CODE_USE_BEDROCK'),
          useVertex: await beneath.env.get('CLAUDE_CODE_USE_VERTEX'),
          useFoundry: await beneath.env.get('CLAUDE_CODE_USE_FOUNDRY'),
          useAnthropicAws: await beneath.env.get(
            'CLAUDE_CODE_USE_ANTHROPIC_AWS',
          ),
          useAnthropicGoogleCloud: await beneath.env.get(
            'CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD',
          ),
          useMantle: await beneath.env.get('CLAUDE_CODE_USE_MANTLE'),
        }),
        fetch: (url, init) => beneath.http.fetch(url, init),
      }),
    }
  })
}
```

## 3. `bsamiee/Rasm` — `.claude/plugins/function-hooks/hooks/register.ts`

https://github.com/bsamiee/Rasm/blob/8d732ba810afa4a65e0acc63068345b2f5ac53aa/.claude/plugins/function-hooks/hooks/register.ts

The only third-party `classic.PreToolUse` reference in public GitHub, and the
only observed use of `next.is`. Full bytes are at
`.agent/kb/raw/fnhook-harvest-bsamiee-Rasm-register.ts.md`; its registration
block:

```typescript
const register: Register = (on) => {
    let opened: Opened = _closed('session.start has not run');

    on('session.start', ($, e, next) =>
        _open($).then((result) => {
            opened = result;
            _noted($, result);
            return next(e);
        }),
    );

    on('tool.call', ($, e, next) =>
        decide(
            e,
            (text: string) => $.process.run(SCAN, { stdin: text }),
            (path: string) => $.fs.exists(path),
        )
            .then((decision) => (decision.kind === 'deny' ? { deny: decision.reason.replace(_CTRL, ' ') } : next(decision.e)))
            .then<ToolCallResult>((answer) => _denied($, opened, e, next, answer)),
    );

    on(
        'classic.*',
        {
            ['hook_event_name']: [
                'PostToolUse',
                'PostToolUseFailure',
                'PostToolBatch',
                'SubagentStart',
                'SubagentStop',
                'UserPromptSubmit',
                'Stop',
                'PostCompact',
                'SessionEnd',
            ],
        },
        ($, e, next) =>
            next.is('!classic.PreToolUse', e) && opened.kind === 'open'
                ? record($, opened, e.hook_event_name, e, CLASSIC).then(() => next(e))
                : next(e),
    );

    on('turn.*', ($, e, next) => (opened.kind === 'open' ? record($, opened, next.event, e, TURN).then(() => next(e)) : next(e)));
};

export { register };
```

Its manifest is the minimal form — `hooks.json` entire:

```json
{
    "modules": ["./register.ts"]
}
```

## 4. `dodi-hq/dodi-skills` — `dodi-dev/hooks/hooks.js` (registration, complete)

https://github.com/dodi-hq/dodi-skills/blob/HEAD/dodi-dev/hooks/hooks.js

```javascript
/** @type {import('claude-code').Register} */
export const register = (on) => {
  const spawnedNames = new Set()

  // Observe: record the address a named spawn is routable by.
  on("agent.spawn", ($, e, next) => {
    if (e.name) spawnedNames.add(normalize(e.name))
    return next(e)
  })

  // Enforce: a SendMessage to one of this session's own subagents is refused.
  on("tool.call", { tool: "SendMessage" }, ($, e, next) => {
    const raw = String(e.to ?? "").trim()
    if (!raw) return next(e)
    const name = stripRef(raw)
    const n = normalize(name)
    // Any fold of "main" (bare or with a [ref]) reaches the lead or a peer
    // session: the resolver's exact-fold pass over its candidate index — which
    // always carries "main" — runs before prefix matching, and registerName
    // refuses every name that folds to "main", so no subagent can be reached
    // by any spelling of it.
    if (n === "main") return next(e)
    // Prefix matching mirrors the resolver: at least 3 characters, and exactly
    // one registered name starting with it.
    const prefixHits = n.length >= 3 ? [...spawnedNames].filter((s) => s.startsWith(n)).length : 0
    const isOwn =
      isAgentId(raw) ||
      isAgentId(name) ||
      (n.length > 0 && (spawnedNames.has(n) || prefixHits === 1))
    if (!isOwn) return next(e)
    return { deny: `dodi-dev no-re-entry rule: "${raw}"${DENY_TAIL}` }
  })
}
```

This module deliberately has **no Bash exposure** — its only `tool.call`
matcher is `SendMessage` — so it is one of the few that #92533 cannot break.

---

# The event namespace, from upstream's own prose

**QUOTED** — `anthropics/claude-code` — `mods/sec-default/README.md`, the
"everything else" row, which enumerates what `sec-default` deliberately passes:

> `prompt.submit`, `turn.*`, `tool.call`, `tool.check`, `command.run`,
> `command.register`, `session.*`, `ui.*`, `fs.*`, `http.fetch`, `process.run`,
> `store.*`, `clock.*`, `model.*`, `mcp.call`, `audio.*`, `agent.list`,
> `engine.create`.

Plus the twelve it hooks: `classic.*`, `prompt.section`, `prompt.context`,
`skill.prompt`, `attribution.text`, `settings.read`, `tool.describe`,
`command.describe`, `agent.offer`, `agent.spawn`, `tool.register`, `tool.list`.

Render components, from the `.d.ts` `RenderComponent` union: `AskUserQuestion`,
`UserMessage`, `AssistantMessage`, `ToolUse`, `ToolResult`, `ToolGroup`,
`Spinner`, `TurnDuration`, `InfoNotice`, `SessionMode`, `PromptHint`,
`AbovePrompt`, `Pane` — with *"`Pane` is the one component whose instances a
plugin opens (`$.ui.open`)"*.

Trace outcomes, from the `.d.ts`: `'caught' | 'expired' | 'kept' | 'passed' |
'rejected' | 'returned' | 'skipped'`, where `expired` = *"its budget ran out"*
and `caught` = *"it threw or its budget ran out, and its `.catch` …"*.

---

# What I did NOT establish

- **No firing probe was run.** Every claim here is source-derived or
  author-reported. The measured-engine claims belong to the sibling lane's
  `2026-09-11-function-hooks-firing-probe.md`.
- **The segmem double-registration conflict** (above) is unresolved.
- **The `.catch` null is query-shaped.** See the caveat under Q1.
- `q4` (`filename:hooks.json "modules"`, 625) and `q7` (173) were not walked to
  completion — both are dominated by unrelated JS using the word "modules", and
  the targeted queries (q3, q5, q6, q10, q12, q14) that *can* discriminate all
  returned small, fully-enumerated result sets.
- **`TheSmokeDev/taskchad-os`** (`claude_function_hooks.py`, 12 KB) and
  **`cam-douglas/hermes-playground`** (`gland.mjs`, 506 lines) were fetched and
  persisted but only skimmed; neither exports a `register`, so neither adds to
  the pattern catalogue. `mmzen/se_harness`'s ~60 debug transcripts were
  enumerated but not fetched — they are live `--debug` output of the flag, and
  are the best remaining lead for anyone wanting engine-side evidence.

---

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the upstream `mods/` tree: three complete function-hook plugins (`sec-default`, `diff`, `telemetry`), their manifests and READMEs; the canonical shape
- [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) — `claude-code.d.ts`, the API's own type declarations incl. `Registration.catch` / `CatchHandler` / `TraceOutcome`
- [bsamiee/Rasm](https://github.com/bsamiee/Rasm) — the only third-party `classic.PreToolUse` and `next.is` use in public GitHub
- [noopz/commonplace](https://github.com/noopz/commonplace) — the dual-wiring fail-open mitigation, the module-live marker, and the densest set of authored gotchas
- [lossless-claude/lcm](https://github.com/lossless-claude/lcm) — independent convergence on the session-claim stand-down; `docs/hook-protocol.md`
- [mahuebel/segmem](https://github.com/mahuebel/segmem) — dual wiring; two `tool.call{Bash}` registrations in one module
- [pleaseai/honmoon](https://github.com/pleaseai/honmoon) — the "second `on()` silently replaces the first" and "budget excludes `next(e)`" measurements
- [djnsty23/claude-auto-dev](https://github.com/djnsty23/claude-auto-dev) — the visible-liveness mitigation and the runtime capability allowlist note
- [dodi-hq/dodi-skills](https://github.com/dodi-hq/dodi-skills) — a complete small module with no Bash exposure
- [cam-douglas/hermes-playground](https://github.com/cam-douglas/hermes-playground) — a structured fixture of issue #92533
- [yonatangross/orchestkit](https://github.com/yonatangross/orchestkit) — the contract-canary CI gate, the only mechanical mitigation found
- [TheSmokeDev/taskchad-os](https://github.com/TheSmokeDev/taskchad-os) — `claude_function_hooks.py`, fetched, no `register` export
- [chrisalbright/devops-wiki](https://github.com/chrisalbright/devops-wiki) — fetched to disprove the single `.claude/skills` `"modules"` hit
- [mmzen/se_harness](https://github.com/mmzen/se_harness) — ~60 live `--debug` transcripts of the flag; enumerated, not fetched
- [ray-amjad/awesome-claude-code-function-hooks](https://github.com/ray-amjad/awesome-claude-code-function-hooks) — curated list; enumerated only
- [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) — enumerated and deliberately skipped (sibling lane owns it)
- [wandercom/kindex](https://github.com/wandercom/kindex), [renchris/claude-infrastructure](https://github.com/renchris/claude-infrastructure), [SApplefeld/claude-kit](https://github.com/SApplefeld/claude-kit), [n0rvyn/indie-toolkit](https://github.com/n0rvyn/indie-toolkit), [shcv/harness-investigations](https://github.com/shcv/harness-investigations), [phate45/claude-patching](https://github.com/phate45/claude-patching), [amitray007/claude-code-schema](https://github.com/amitray007/claude-code-schema), [TransmuteLabs/Catalyst-CC-Patch](https://github.com/TransmuteLabs/Catalyst-CC-Patch), [alternative-intelligence-cp/claude-skills](https://github.com/alternative-intelligence-cp/claude-skills) — appeared in the search results and are catalogued in `.agent/kb/raw/fnhook-harvest-hits.md`; documentation/analysis only, not fetched
