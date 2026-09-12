# Upstream issue anthropics/claude-code#91870 — Function Hooks

Fetched 2026-09-11 via `gh issue view 91870 -R anthropics/claude-code --json ...`
(rc=0) and `gh api repos/anthropics/claude-code/issues/91870/comments --paginate`.
Raw dump: `.agent/kb/raw/fnhooks-upstream-91870.md` (161 comments, full verbatim
bodies) and `.agent/kb/raw/fnhooks-upstream-91870.json` (raw `gh` JSON).

- **Title (QUOTED):** "Function Hooks - make plugins 10x more powerful"
- **State:** OPEN, created 2026-09-03T18:00:23Z, 161 comments as of fetch (2026-09-11).
- **Author:** `poteat` (display name "Alice T'Poteat"). `author_association` on
  both the issue and every one of poteat's comments is **`CONTRIBUTOR`**, not
  `MEMBER`/`OWNER` — GitHub's own field does **not** corroborate insider status,
  even though the post text claims it ("I was asked to get feedback... regarding
  an internal proposal we have", later "We're now committed to shipping..."). Flag
  this as **SUSPECT**: the content reads as an Anthropic staffer running a public
  design RFC, and dozens of commenters treat poteat's replies as authoritative
  (poteat answers technical questions about the shipped prototype, cites specific
  internal build numbers, and other commenters reference `--debug-file` output
  that matches poteat's descriptions) — but `author_association` alone does not
  prove employment.

## What the issue is (QUOTED from body)

Not a bug report — a **feature design RFC / community-feedback thread** for a
major new plugin mechanism called "Function Hooks", product-branded "Claude
Mods". Opening line: "Function Hooks let you modify CC very deeply, while
still being safe through side-effect tracking over a parameterized `$` object,
and while composing neatly using a registration-order-based 'next' continuation
model a la Express, or Koa." A "Community Update: Sep 9, 2026" was later
prepended to the body: "We're now committed to shipping function hooks, on the
scale of weeks... we are going to be calling this functionality 'Claude Mods'...
A mod is just a plugin that uses function hooks."

## Enablement (QUOTED, cross-corroborated by multiple independent commenters)

- **Env var:** `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` — from the OP's community
  update ("folks who want to test and give feedback may use
  `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude`") and independently measured by
  commenter `cwschroeder` (comment #100, 2.1.261): *"Without the env flag the
  module is skipped silently: `hooks modules not loaded: rollout flag
  (tengu_plugin_hooks_modules) is off`. The plugin loads fine and nobody
  notices. `settings.json` `env` does enable it."*
- **Growthbook/rollout flag name:** `tengu_plugin_hooks_modules` — the internal
  gate name surfaced in that same debug-log string. This matches the naming
  convention (`tengu_*`) already known from prior Claude Code rollout flags.
- **Also requires** `--plugin-dir <dir>` pointing at a directory containing
  `.claude-plugin/plugin.json` + `hooks/hooks.json` with `{"modules": [...]}`
  referencing a `.ts`/`.js` module that exports `register`.
- **Version it first shipped in (QUOTED, `frsorrentino` #76):** "I read the
  prototype shipped in 2.1.260 behind `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`, and
  ran it" — so **2.1.260** is the first version multiple commenters could
  actually exercise it in, not just read about. Later measurements are pinned
  to 2.1.261 (`deafsquad`, `cwschroeder`), 2.1.263 (`42tahara`, `Spencer-Morley`,
  `muloka`), and 2.1.267 (`sirmaelstrom`, referencing generated `.d.ts` types).

## Working code (VERBATIM, from poteat and measuring commenters)

Type-safe glob + tier-skip pattern (poteat, comment #131):

```ts
// shell hooks only, no function hook interference
on("classic.*", ($, e, next) => {
  // e is a union of all classic hooks
  return next.to(e, "core")
})
```

Reproducer for the three "skip" failure modes — throw, budget overrun, wedged
(`42tahara`, comment #135, confirmed working on 2.1.263):

```ts
// hooks-handlers/probe.ts
import type { Register } from "claude-code";
export const register: Register = (on) => {
  on("tool.call", { tool: "Bash" }, async ($, e, next) => {
    if (e.command.includes("SLEEP")) await $.clock.sleep(60000); // budget overrun
    if (e.command.includes("SPIN"))  { const t = Date.now(); while (Date.now() - t < 60000) {} } // wedged
    return next(e);
  });
};
```
```
CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude -p --plugin-dir <dir> --debug-file ./d.log "run: echo SLEEP"
```

A "fail-closed via race" pattern poteat proposed as a workaround for the
fail-open-on-timeout default (comment #142):

```ts
on("tool.call", { tool: "Bash" }, async ($, e, next) => {
  const ok = await Promise.race([
    $.http.fetch("https://policy.internal/check", { method: "POST", body: e.input.command })
      .then(r => r.status === 200, () => false),
    $.clock.sleep(8_000).then(() => false),
  ])
  return ok ? next(e) : { deny: "policy did not approve in time" }
})
```

Concurrency pattern for a future `tool.check` event (poteat, comment #155):

```ts
on('tool.check', async ($, e, next) => {
  const beneath = next(e)                 // everyone below starts now
  if (await isDestructive(e.input))
    return { decision: 'deny', reason: 'destructive command' }
  return beneath
})
```

No `register.ts`/`hooks.json` full manifest was posted verbatim by poteat in
the body — commenters describe the shape (`.claude-plugin/plugin.json` +
`hooks/hooks.json` = `{"modules": ["./probe.ts"]}`) rather than pasting a full
file (**PARAPHRASED**, `deafsquad` #82, `frsorrentino` #76).

## `classic.*` event namespace (QUOTED — this is the key finding for our
question about `classic.SessionStart`)

poteat, comment #131, answering a request to "keep the shell-hook path alive
as a compatibility layer": *"Our internal prototype now introduces a
`classic.PreToolUse` event (and the others, 1:1), which 'wraps' the core shell
hooks you already have configured, and has the same in/out data interface."*

- **`classic.*` is a compatibility wrapper namespace, one event per existing
  classic (shell/command) hook, 1:1.** `classic.PreToolUse` was the only
  concretely named example; poteat says "and the others, 1:1" without
  enumerating them, so **`classic.SessionStart` is not explicitly named
  anywhere in this thread — it is implied by "the others, 1:1", not confirmed
  by name.** Mark `classic.SessionStart` specifically as **INFERRED**, not
  QUOTED.
- Independently corroborated as real (not just design prose) by `42tahara`
  (#133, 2.1.263): *"`classic.*` wrapping the shell hooks 1:1 means we don't
  have to migrate to benefit — if `e` on `classic.PreToolUse` is typed, the
  same check lands on our existing Python hooks."* — but note `42tahara`'s own
  next comment (#133) frames this as conditional/not yet fully run, and
  `Spencer-Morley` (#134) says explicitly *"I haven't run the prototype... I'll
  run them unmodified under the flag and report what the debug file says"* —
  i.e., even the compatibility-wrapper claim is corroborated for
  `classic.PreToolUse` specifically, not verified end-to-end by anyone in this
  thread for the full classic event set.
- Tier model (QUOTED, poteat #131): five tiers — `[prepend] [user] [append]
  [builtin] [core]` — with a `next.to(e, tierName)` primitive to skip
  intervening tiers, and intersection-of-lowest-declared-tier semantics when
  multiple prepend plugins skip to different tiers.

## Full event/capability enumeration (QUOTED, `Spencer-Morley` #139, corrected
from an earlier partial extraction in #136 — read the correction, not #136)

Extracted from the shipped binary via `grep -aoc` anchored on a literal array
member to force a full-array match (methodologically the strongest evidence in
the thread — a byte-level grep against the shipped `claude.exe`, not the PDF
or prose):

**20 events:**
```
PreToolUse, tool.call, ui.render, ui.resolve, ui.press, ui.input, ui.select,
agent.offer, agent.spawn, prompt.submit, prompt.section, prompt.context,
tool.describe, skill.prompt, attribution.text, session.start, turn.start,
turn.step, turn.complete, engine.create
```

**36 capabilities** (this is the answer to our question about whether
`session.authorize` and `flag.value` appear — **both do**, confirming they
exist in the shipped capability list, which is directly relevant background
to our tracked #92469 "generated declarations omit `session.authorize` and
`flag.value`" — see cross-reference note below):
```
model.complete, model.classify, model.fork, audio.play, audio.speak, mcp.call,
session.cwd, session.model, session.turnCount, session.id, session.messages,
session.repo, session.surface, session.authorize, turn.abort, flag.value,
tool.list, tool.register, agent.list, ui.toast, ui.status, ui.log, ui.notice,
ui.invalidate, fs.readFile, fs.writeFile, fs.listDir, fs.exists, fs.stat,
fs.ancestors, store.get, store.set, store.delete, store.keys, http.fetch,
process.run
```

Note: `Spencer-Morley` explicitly retracted an *earlier* published version of
both lists in this same comment (#139), stating the earlier extraction method
(reading a decoded byte-window) dropped `ui.select` from the events and the
**first thirteen** entries from the capabilities list. **Use the #139 lists
above, not any list quoted from #136.** Also noted: `fs.readFile` is
confirmed still the live name on 2.1.263, so poteat's stated intent (#131) to
rename it to `fs.read` "has not landed" as of that build.

## Reported defects / behavioral findings (measured by commenters against the
shipped 2.1.26x prototype — distinguish from "the thread demonstrates X with a
reproducer", which every row below is)

1. **Fail-open on timeout/wedge, fail-closed on load failure — an asymmetry**
   (`Spencer-Morley`, #135/#136, 2.1.263, measured with `--debug-file`):
   - A hook exceeding its budget (measured **10000ms**) or wedged (heartbeat
     unanswered within **5000ms**) is *skipped*, logged as `hook failed: ...
     (tool.call; skipped; what is below it ran in its place)`, and **the
     guarded tool still runs** — "Loud, but bypassed."
   - A capability missing at load time instead fails **closed**: `"unloaded,
     its withholdings kept while it is declared"`.
   - `durban01` (#137) proposes a fix: an opt-in `onFailure: "deny"` per
     registration. poteat (#142) counter-proposes a `.catch()` chained off
     `on(...)` as the general mechanism, explicitly unresolved/still being
     designed as of the fetch date ("I'm not sure yet; it's complicated").
2. **A forgotten `return next(e)` silently no-ops rather than blocking**
   (`gbrussich52`, #111, 2.1.261, full before/after table with `--debug-file`
   evidence): a hook that returns `{}`/`undefined`/an arbitrary object without
   ever calling `next()` is logged at ERROR (`hook failed: returned neither {
   result } nor { deny }... skipped; what is below it ran in its place`), and
   the tool call proceeds and **the model is told it succeeded** — i.e. a
   buggy hook that forgets to forward degrades to "hook had no effect", not to
   an error surfaced to the model.
3. **Command-hook `updatedInput` precedence changed / is confusing**
   (`deafsquad`, #82, 2.1.260 native Windows): two command (classic) hooks
   both rewriting `updatedInput` on the same matcher — "Last-wins by list
   order, silent," contradicting an earlier assumption of first-wins; the
   debug file logs each hook as `success` and never mentions the earlier one
   being overwritten. This is about the **classic/command hook** engine, not
   function hooks per se, but was measured as part of this thread's fact-check
   chain.
4. **Performance**: function hooks are much cheaper than spawning shell/Python
   hooks (`deafsquad` #82 table): pass-through overhead per hook is ~1-4ms for
   25 chained function hooks vs. ~50ms per spawned command hook process; 8
   command hooks at 50ms sleep each ≈ 401ms vs. 8 function hooks with
   `$.clock.sleep(50)` each ≈ 424ms (comparable once the hooks themselves
   sleep, but command hooks pay a large fixed spawn tax function hooks don't).
5. **Usage/token accounting is not exposed on any event** (`frsorrentino`,
   #76, measured against 2.1.260): `turn.complete` carries `{answer,
   durationMs, aborted, turnId, reason}` with **no token usage field**, and
   subagent (`Workflow`) token usage is invisible in the parent's
   `toolUseResult` — "9.2M fresh input tokens invisible in one session."
6. **`session.repo()` returns `null` for any non-git VCS or secondary working
   copy** (`muloka`, #119, 2.1.263, four-row table: plain git, jj colocated, jj
   not colocated, `jj workspace add` — the last two return `null` even when a
   git backend exists in the primary tree). Filed as a design gap, not
   labeled a bug per se, but a concretely reproduced limitation.

## Maintainer statements (QUOTED — poteat only; no other `anthropics/*`-affiliated
account posted in this thread, and `author_association` does not confirm poteat's employment — see caveat above)

- On filesystem/admin restriction: *"It can, unless your org admin has
  installed a plugin that hooks onto `fs.read` to restrict it."* (#131)
- On `classic.*`: quoted in full above (#131).
- On fail-open/fail-closed for timeouts: proposed `.catch()` on `on(...)`
  registrations as the general mechanism, explicitly **not finalized** (#142):
  *"I'm not sure yet; it's complicated which is why I wanted to avoid it
  haha."*
- On concurrency / `tool.check` (a **not-yet-shipped** event, per `sirmaelstrom`
  #158 who could not find it in 2.1.267's generated types): poteat describes it
  prospectively (#155) as the mechanism to let a guard start `next(e)` before
  its own check completes.

## Relation to our tracked issues #92533 and #92469

**Neither #92533 nor #92469 is mentioned anywhere in this issue's body or its
161 comments** (checked via a full-text grep of both numbers across the raw
JSON — zero hits), and neither appears in the GitHub cross-reference timeline
(`gh api .../timeline`, `cross-referenced` events) — the only same-repo
cross-reference is **anthropics/claude-code#93426**, an unrelated bug about
`.in_use/<pid>` files polluting the plugin cache. So: **#91870 is DISTINCT
from both tracked issues at the graph level — no direct link exists.**

That said, #91870's content is load-bearing background for both:

- **#92469** ("generated declarations omit `session.authorize` and
  `flag.value`"): this thread's #139 capability list, extracted directly from
  the shipped binary, **confirms both `session.authorize` and `flag.value`
  exist as real, shipped capabilities** on `$` — i.e., #92469's claim that the
  generated `.d.ts` omits them is consistent with these being real runtime
  capabilities that the type-generation step (mentioned by `42tahara` #133 —
  `import("claude-code")` npm placeholder, `.d.ts` emitted via `/plugin-types`)
  may simply not be covering yet. This thread does not itself report the
  omission — it independently establishes that the two capability names are
  real, which is the fact #92469 needs to be a defect rather than confusion
  about the shape.
- **#92533** (a `tool.call` hook reaching Bash breaks every Bash call inside an
  `Agent(isolation:"worktree")` subagent): **not discussed at all** in this
  thread. No commenter tests function hooks inside a worktree-isolated
  subagent; `agent.spawn`/`agent.offer` events are named (in the capability
  list and by `frsorrentino` #76) but no worktree-isolation interaction is
  measured here. **UNANSWERED** by this issue.

## Linked issues found (via GitHub cross-reference timeline)

Only one cross-reference lands in `anthropics/claude-code` itself:

| # | Repo | Title | Relation |
|---|---|---|---|
| anthropics/claude-code#93426 | anthropics/claude-code | "[BUG] Claude Code writes `.in_use/<pid>` and `.orphaned_at` into the versioned plugin cache after install..." | Unrelated plugin-cache bug; mentions #91870 only in passing, not a function-hooks defect |

All other 22 cross-references are from third-party repos (community trackers,
blog/changelog issues, "daily radar" digest issues in Chinese, and other
projects' internal tracking of function hooks as a dependency) — none are
`anthropics/claude-code` issues, so they don't bear on our tracked defects.
Full list with `gh issue view <n> -R anthropics/claude-code --json title,state`
was not run because none of the 22 are in this repo (that check only applies
to same-repo issue numbers, and there are none besides #93426, already
checked: `gh issue view 93426 -R anthropics/claude-code` was not additionally
queried for state — **NOT DONE**, flag as an open follow-up if needed).

## Version numbers named in the thread

2.1.260 (first version commenters could run the prototype against, per
`frsorrentino` #76 and `deafsquad` #82), 2.1.261 (`deafsquad`, `cwschroeder`,
`gbrussich52`), 2.1.263 (`42tahara`, `Spencer-Morley`, `muloka`), 2.1.267
(`sirmaelstrom`, referencing generated types — `tool.check` absent from that
build's types). No fixed/GA version is stated; the 2026-09-09 community update
says only "shipping... on the scale of weeks."

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the issue itself (#91870), its 161 comments, and the one same-repo cross-referenced bug (#93426), fetched for this review.
