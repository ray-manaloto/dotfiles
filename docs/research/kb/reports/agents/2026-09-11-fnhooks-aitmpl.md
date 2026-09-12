# Function hooks — aitmpl.com sources (2026-09-11)

Status: COMPLETE

## Method note — the SPA shell trap

`curl` against both `https://www.aitmpl.com/function-hooks/` and
`https://www.aitmpl.com/blog/function-hooks-claude-code/` returns HTTP 200,
but the body is an Astro SPA shell with no rendered prose (confirmed:
`grep -c 'register|hooks.json|CLAUDE_CODE_ENABLE|classic\.'` on the raw HTML
= **0 hits** on both). Control arm: `llms.txt`, `/*.md` and guessed API paths
all returned the **same byte count as the site root** (60276 bytes) —
proof the framework serves a catch-all shell for any unknown/JS-only path,
not real per-page content. Site is open-source
(`davila7/claude-code-templates`, linked in the page's own JSON-LD), so the
real page bytes were pulled from GitHub via `gh api repos/.../contents/...`
instead — this is the SAME bytes the site serves to a JS-executing browser
(the blog's static HTML export is checked into
`dashboard/public/blog/function-hooks-claude-code/index.html`; the
`/function-hooks/` landing page is a generic `[...type].astro` listing
page with no unique prose, populated from
`dashboard/public/components/function-hooks.json`, which is a plain
catalog manifest, not an article).

Raw sources saved to `.agent/kb/raw/`:
- `fnhooks-aitmpl-landing-raw-shell.html` — the SPA shell curl actually got (source 1, unusable)
- `fnhooks-aitmpl-blog-raw.html` — the REAL rendered blog article HTML (source 2, from GitHub)
- `fnhooks-aitmpl-manifest.json` — the 10-entry catalog manifest backing `/function-hooks/`
- `fnhooks-repo-CLAUDE.md`, `fnhooks-repo-cli-tool-rule.md` — repo's own docs on how the catalog is built/installed
- `fnhooks-src-*.ts`/`.tsx` — all 10 complete hook source files (verbatim)

## ⚠️ Headline framing (QUOTED, from the blog's own lede):

> "Function hooks are not a shipped Claude Code feature. They are an internal
> Anthropic proposal published as a GitHub issue on September 3, 2026, asking
> the community for feedback. ... Every API name in this article is
> provisional and comes from the architecture PDF and the videos attached to
> anthropics/claude-code#91870."

Every `.ts` source file repeats this in its header comment (QUOTED, from
`fnhooks-src-universal-audit-log.ts`): "Function hooks are an Anthropic
proposal under community review: https://github.com/anthropics/claude-code/issues/91870
/ Every API name below is provisional." The repo's own `CLAUDE.md` (QUOTED):
"Anthropic proposal ..., **not a shipped feature**." "Keep the experimental
banner (listing page, detail page, blog) until Anthropic ships the feature."

**Currency caveat (found via a sibling teammate's shared fetch, not my
assigned sources):** `.agent/kb/raw/fnhooks-upstream-91870.md` (the real
GitHub issue, already on disk from a concurrent agent this session) shows
Anthropic posted a "Community Update: Sep 9, 2026" comment on that same issue
committing to ship, under the product name **"Claude Mods"** ("function hook"
staying the engineering term for the primitive underneath a Mod), "on the
scale of weeks." The aitmpl blog article predates or does not reflect that
update — it cites the issue's opening (Sep 3) and a "2.1.266" binary probe,
with no mention of "Claude Mods". Treat everything below as this project's
picture as of the article's own investigation date, one week stale against
the primary source.

---

## Enablement (QUOTED)

> "The videos in the issue show the feature behind an environment variable.
> The variable name comes from the demo, not from any documentation, so
> expect it to change:
> `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude`"

The article claims independent binary verification (QUOTED): "We ran
`strings` over Claude Code 2.1.266 and the flag name appears five times,
alongside the engine that reads it." This is the site's OWN claim, not
something I re-verified — no local binary probe was run for this task (out
of scope; the assignment was the two aitmpl.com pages).

Loading a hook module once written: **no plugin-marketplace/`enabledPlugins`
registration is described as required.** Two paths, both QUOTED:
1. Their own CLI flag: `npx claude-code-templates@latest --function-hook security/block-destructive-commands`, which "writes the plugin layout ... to `.claude/skills/<name>/`", then `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude --plugin-dir .claude/skills/block-destructive-commands`. The article adds a caveat (QUOTED): "Claude Code should also pick the directory up on its own as `<name>@skills-dir` on the next session, once you trust the workspace — but that auto-load is the one part of this flow we have not confirmed on a real binary, so reach for `--plugin-dir` if the hook does not fire."
2. Hand-built, no CLI needed (QUOTED, complete):
   ```
   mkdir -p .claude/plugins/secret-redactor/{.claude-plugin,hooks}
   cd .claude/plugins/secret-redactor
   echo '{"name":"secret-redactor","version":"0.0.1"}' > .claude-plugin/plugin.json
   echo '{"modules":["./secret-redactor.ts"]}' > hooks/hooks.json
   # then drop secret-redactor.ts next to hooks.json and run:
   CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude --plugin-dir .claude/plugins/secret-redactor
   ```
`--function-hook` requires `claude-code-templates 1.29.5` or newer (QUOTED).

## File layout (QUOTED, verbatim tree from the article)

```
my-plugin/
├── .claude-plugin/plugin.json
└── hooks/
 ├── hooks.json # { "modules": ["./my-hooks.ts"] }
 └── my-hooks.ts # export function register(on, options) { ... }
```
with `hooks/hooks.json` contents shown separately as:
```
{
 "modules": ["./my-hooks.ts"]
}
```
Module extension may be `.js`, `.ts`, `.jsx` or `.tsx` (QUOTED). `modules` is
"one new key" added to the existing shell-hook `hooks/hooks.json` shape —
"Your existing command hooks keep working next to the module" (QUOTED).

Confirmed by the actual catalog artifacts (not paraphrase — these are the
real repo files): every hook's `.json` sidecar is exactly
`{"description": "...", "modules": ["./<name>.ts"]}` (e.g.
`fnhooks-src` sidecar for `universal-audit-log`, pulled from
`cli-tool/components/function-hooks/observability/universal-audit-log.json`).

## `register` signature (QUOTED)

Minimal form, "listing 1 from the architecture doc" (QUOTED, complete):
```
export function register(on) {
 on("tool.call", ($, e, next) => {
 if (e.tool === "Bash" && e.command == "rm -rf /")
 return { deny: "Destructive command blocked by hook" }
 return next(e)
 })
}
```
Full form used by every real catalog hook:
`export function register(on: any, options: Record<string, any> = {}) { ... }`
— `options` is the plugin's `userConfig` (QUOTED).

`on(event, matcher?, handler)` — matcher is optional, "a partial of `e`,
matched structurally; an array matches when any element matches" (QUOTED).
Examples (QUOTED, verbatim):
```
on("tool.call", { tool: "Bash" }, ($, e, next) => { /* e.command is typed */ })
on("tool.call", { tool: ["Edit", "Write", "MultiEdit"] }, ($, e, next) => { /* any of the three */ })
on("ui.render", { component: "ToolUse", surface: "desktop" }, ($, e, next) => { /* one component, one surface */ })
```

Handler params `($, e, next)` (QUOTED):
- `$` — "the engine interface: everything a hook can see or do... `$.tool.call`, `$.ui.log`, `$.fs.read`. It is the only door." No ambient filesystem/network — "what a plugin did is exactly the calls it made on `$`."
- `e` — "the event: the argument the method was called with, as an immutable plain value... To change it, pass next a copy."
- `next` — "the continuation. Calling it runs the next hook registered on the event... You may call it once, many times, or never." Also carries `next.event`, `next.origin` (which plugin raised the dispatch), `next.signal` (an `AbortSignal`), and `next.is(type, e)` "for narrowing under `*`".

## Event names (QUOTED — the binary-surface table from the article)

The article's own "binary probe" table of nouns and their methods observed
in Claude Code 2.1.266 strings (their claim, unverified by me):

| Noun on `$` | Methods (QUOTED) |
|---|---|
| `$.fs` | `readFile`, `writeFile`, `listDir`, `exists`, `stat`, `ancestors` |
| `$.http` | `fetch` |
| `$.process` | `run` (`argv`, `cwd`, `env`, `stdin`, `timeoutMs`) |
| `$.model` | `complete`, `fork`, `classify` — with a per-plugin token budget |
| `$.store` | `get`, `set`, `delete` — JSON values only, capped at 4,194,304 characters, with a lock |
| `$.session` | `messages`, `cwd`, `model`, `turnCount`, `id`, `repo`, `surface`, `authorize` |
| `$.ui` | `render`, `ask`, `select`, `input`, `toast`, `notice`, `status`, `log`, `open`, `close`, `press`, `invalidate`, `resolve` |
| `$.tool` | `call`, `describe`, `list`, `register`, `output`, `execution` |
| `$.agent` | `list`, `spawn` |
| `$.command` | `list`, `register` — plus `command.run` and `command.describe` events |
| `$.prompt` | `submit`, plus `prompt.section` and `prompt.context` events |

**`classic.*` — QUOTED, exact sentence:** "Beside those, the binary knows
`engine.create`, `plugin.register`, `turn.complete`, and a **`classic.*`
namespace (`classic.PreToolUse`, `classic.SessionStart`, `classic.SessionEnd`,
`classic.Setup`)** — today's shell hooks, surfaced to function hooks as
events." **`classic.SessionStart` is explicitly named**, alongside
`classic.PreToolUse`, `classic.SessionEnd`, `classic.Setup` — that is the
complete `classic.*` enumeration given in the article; it does NOT list
`classic.PostToolUse`, `classic.Notification`, `classic.Stop`,
`classic.SubagentStop`, `classic.PreCompact`, or `classic.UserPromptSubmit`
even though those are real shell-hook events today — either the article's
enumeration is partial (most likely, since it says "the binary knows..." as
illustrative, not exhaustive) or those aren't yet surfaced; UNANSWERED which.

Events seen across the 10 shipped example hooks (QUOTED tool-call sites,
enumerated by shape not by expectation): `"*"`, `"tool.call"`, `"ui.render"`,
`"engine.create"`, `"plugin.register"`.

## Result vocabulary (QUOTED)

Deny shape used throughout every example: `return { deny: "<message>" }`
(a plain object with a `deny` string field) — e.g. from
`block-destructive-commands.ts`: `return { deny: 'Blocked by ... reason };`.
This is **not** the shell-hook `permissionDecision: "deny"/"allow"/"ask"`
vocabulary — the article draws the contrast explicitly (QUOTED, table row):
"Allow, deny, or inject text" (shell hooks) vs "Rewrite inputs, short-circuit,
return your own result" (function hooks).

**"Five placements, one event"** (QUOTED table):

| Placement | Shape (QUOTED) | Typical use (QUOTED) |
|---|---|---|
| `before` | `doWork(); return next(e)` | Log, validate, ask the user |
| `after` | `const r = await next(e); useResult(r); return r` | Redact output, time the call, audit |
| `during` | `const p = next(e); doWork(); return p` | Show a spinner while the tool runs |
| `instead` | `return { deny: "..." }` or `return ownResult` | Deny, serve from cache, replace a tool |
| `modifying` | `return next({ ...e, command: rewritten })` | Rewrite npm to pnpm, add a timeout |

No `preventContinuation`/`stopReason`/`additionalContext` tokens (the
classic shell-hook JSON-output vocabulary) appear anywhere in the article
text or the 10 `.ts` source files (checked by grep across all fetched
sources — 0 hits); the article never claims those exist as function-hook
concepts, only mentions `additionalContext` implicitly via
`prompt.section`/`prompt.context` events with no further detail
(UNANSWERED — the exact per-event result shape for those two events is not
given).

## Ordering — "order is nesting" (QUOTED)

> "Hooks registered on one event fold like middleware: `on(X, A), on(X, B),
> on(X, C)` becomes `X = A(B(C(core)))`. The first plugin registered sits on
> the outside, sees every event first and every result last, and nothing
> beneath it can bypass it."

Listing 5, the audit-log-as-one-hook example (QUOTED, complete):
```
on("*", ($, e, next) => {
 $.ui.log(`${next.origin} called ${next.event} at ${Date.now()}`)
 return next(e)
})
```
Capability withholding is done by hooking `engine.create` and returning
the `$` table without a given noun (e.g. `http`, `process`) — "A plugin
below cannot call what is not there" (QUOTED).

## Loader constraints / gotchas (QUOTED)

- `$.ui.log` "appears to be a TUI surface. In headless runs (`claude -p`, even with `--debug`) the hooks' log lines did not show up." Does NOT affect hooks writing through `$.fs.append` (e.g. `universal-audit-log`), but any hook reporting only via `$.ui.log` is silent in CI.
- Reentrancy is detected and specific: calling `$.model` from a `prompt.submit` hook, "2.1.266 tells you the call 'would wait on the turn this hook is holding'", then names outs: "answer `{ text }`, call `next(e)`, or defer to a later event such as `turn.complete`."
- Forward-compat landmine (QUOTED, attributed to "one maintainer"): "an unknown key in `hooks.json` makes older Claude Code versions **drop the whole file silently**. A `modules` key needs to be skipped, not rejected, by builds that predate it."
- `secret-redactor` limitations (QUOTED): matches "by shape, not by meaning" — `PASSWORD=hunter2` passes through untouched, no entropy/keyword heuristic; its connection-string pattern "redacts only the credentials" up to `@`, leaving host/port/db name exposed.
- Open questions the article explicitly flags as UNANSWERED by the proposal itself: fail-open vs fail-closed on a mid-chain throw; a generic hang budget for a slow non-model `await`; how far `$.fs` reaches / under whose permission settings; whether MCP tool calls go through `tool.call`; how a command-hook `deny` interacts with a function hook that already called `next`; no documented fake-`$`/fixture format for testing.

## Complete code examples (all 10, verbatim, saved to `.agent/kb/raw/fnhooks-src-*`)

Two shown in full above (`block-destructive-commands.ts` core logic,
`universal-audit-log.ts` listing). The article's own three "Shell hooks
cannot express this" trimmed snippets (QUOTED, complete):

1. Rewrite (npm→pnpm):
```
on("tool.call", { tool: "Bash" }, ($, e, next) => {
 const rewritten = e.command
 .replace(/\bnpm\s+(install|i|add)\b/g, "pnpm add")
 .replace(/\bnpx\s+/g, "pnpm dlx ")
 if (rewritten === e.command) return next(e)
 $.ui.log(`[npm-to-pnpm] ${e.command} -> ${rewritten}`)
 return next({ ...e, command: rewritten }) // events are immutable: forward a copy
})
```
2. Short-circuit (WebFetch cache):
```
const cache = new Map()

on("tool.call", { tool: "WebFetch" }, async ($, e, next) => {
 const key = `${e.url}\n${e.prompt}`
 const hit = cache.get(key)
 if (hit) return hit.result // nothing below runs: no network call at all
 const result = await next(e)
 if (result && !result.deny) cache.set(key, { result })
 return result
})
```
3. Draw (duration badge via JSX/Ink+DOM):
```
on("ui.render", { component: "ToolUse" }, async ($, e, next) => {
 const { Row, Badge } = $.ui.resolve(e) // the surface's own elements
 const rendered = await next(e) // whatever the engine drew
 return (
 <Row>
 {rendered}
 <Badge text={`${durationFor(e.props)} ms`} />
 </Row>
 )
})
```

The remaining 7 complete files were pulled unmodified from GitHub (not
paraphrased) and are on disk verbatim at `.agent/kb/raw/fnhooks-src-*.ts`:
`admin-capability-lockdown.ts`, `large-edit-confirmation.ts`,
`npm-to-pnpm-rewriter.ts`, `protected-paths-guard.ts`, `secret-redactor.ts`,
`tool-timing-badge.tsx`, `webfetch-cache.ts`, `websearch-to-exa.ts`.

## Catalog table (QUOTED, all 10 rows)

| Hook | Event(s) | Placement | What it does |
|---|---|---|---|
| security/block-destructive-commands | tool.call | instead | Denies rm -rf /, force push, hard reset, destructive SQL, disk formatting |
| security/secret-redactor | tool.call | after | Replaces keys, tokens, JWTs and connection strings in tool output before the model reads them |
| security/protected-paths-guard | tool.call | instead | Denies edits to .env, lockfiles, CI workflows and private keys, with an allow list |
| security/large-edit-confirmation | tool.call | before | Asks the user before editing a file over N lines, via the permissions primitive |
| productivity/npm-to-pnpm-rewriter | tool.call | modifying | Rewrites npm/npx to pnpm, yarn or bun |
| productivity/webfetch-cache | tool.call | instead / after | Serves repeated WebFetch calls from a session cache with TTL |
| observability/universal-audit-log | * | after | JSON line per event with origin, duration and outcome, including denials |
| ui/tool-timing-badge | tool.call, ui.render | after | Times every tool call and draws a colored badge next to the ToolUse row |
| integrations/websearch-to-exa | tool.call | instead | Replaces the built-in WebSearch with Exa through $.http, with fallback |
| enterprise/admin-capability-lockdown | engine.create, plugin.register, tool.call | after / instead | Withholds http and process from $, allowlists plugins, denies shell network commands |

## Unfetchable / unanswered

- The rendered `/function-hooks/` landing page prose could not be fetched by
  `curl` (SPA shell only) — its underlying source is a generic listing
  template with no unique text; substituted with the backing manifest JSON,
  which is a catalog, not prose. Nothing prose-shaped was lost.
- Exact result shape for `prompt.section`/`prompt.context` events: UNANSWERED.
- Whether `classic.PostToolUse`/`classic.Notification`/`classic.Stop`/etc.
  exist as `classic.*` names beside the four the article names: UNANSWERED.
- Independent verification of the "2.1.266 binary strings" claim: NOT
  attempted (out of scope for this fetch task; would need a live-probe
  lane per the standing corpus-ranking rule).

## GitHub repos touched

- [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) — source of both aitmpl.com pages (site is a thin Astro SPA over this repo's checked-in content/catalog); pulled the real blog HTML, the function-hooks manifest, and all 10 complete `.ts`/`.tsx` hook source files via `gh api repos/.../contents/...` since `curl` only returned the client-rendered SPA shell.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issue #91870 is the primary proposal both aitmpl pages are built on; not independently re-fetched by me (already present on disk from a concurrent teammate's fetch, `.agent/kb/raw/fnhooks-upstream-91870.md`), cited only for the currency caveat above.
