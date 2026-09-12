# `anthropics/claude-code#92533` on 2.1.269 — LIVE, and wildcard observers trigger it

**Date:** 2026-09-11 · **Session:** `dotfiles-20260911.001` · **Branch:** `feat/function-hooks-probe`
**Companion to:** `2026-09-11-function-hooks-firing-probe.md` (same harness, same binary)

Four-arm probe of the one open question that decides whether the audit-log shape is
adoptable here. **All claims MEASURED against `~/.local/share/claude/versions/2.1.269`.**

## Two findings, both previously unestablished

1. **#92533 reproduces on the version this repo deploys.** #1020 records the upstream
   report as against 2.1.263 and says *"its applicability to the version this repo deploys
   is UNVERIFIED locally."* It is now verified: live on 2.1.269.
2. **Wildcard observers DO trigger it.** #1020's adoption restriction — *"no `tool.call`
   registration whose matcher includes Bash, wildcard observers included"* — was explicitly
   *"defensible policy pending a deployed-version test, not established current
   incompatibility."* The wildcard half is now MEASURED, not policy.

## Method

A throwaway git repo in the scratchpad (`git init`, one commit) — **not this repository**,
because the probe creates real worktrees. Each arm is one `-p` session told to dispatch an
`Agent` with `isolation: "worktree"` that runs `pwd` and `true` through Bash, then emit
`WT_OK <pwd>` or `WT_FAIL <error>`.

```
claude -p '<prompt>' --permission-mode bypassPermissions [--plugin-dir <arm>] \
  --settings '{"env":{"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS":"1"}}' \
  --debug-file <path> < /dev/null
```

Every arm's hook is a **pure passthrough** — `async (_$, e, next) => next(e)` — so nothing
the handler does can explain a failure. Only the *registration* differs.

## Results

| Arm | Registration (`plugin validate` readback) | Result | rc |
|---|---|---|---|
| **A** | *none — control* | **`WT_OK /…/.claude/worktrees/agent-ae9270b028eeba13e`** | 0 |
| **B** | `tool.call{tool=Bash}` — the upstream minimal reproducer | **`WT_FAIL`** | 0 |
| **C** | `*` — `universal-audit-log`'s shape | **`WT_FAIL`** | 0 |
| **D** | `tool.call` (no matcher) — `tool-timing-badge` / `secret-redactor:65`'s shape | **`WT_FAIL`** | 0 |
| **E** | `classic.*` — the shape `anthropics/claude-code`'s own `mods/sec-default` uses | **`WT_OK`** | 0 |
| **F** | `classic.PreToolUse{tool=Bash}` — the `hook_guard` migration shape | **`WT_OK`** (hook fired 2×) | 0 |

**Arm A is the control that proves a worktree subagent CAN run Bash here; arm B is the
control that proves the probe can SEE the breakage.** Without B, a passing C would be
worthless — it could mean "wildcards are safe" or "this probe cannot detect #92533 at all".
Both directions are armed, so C and D are evidence.

### The failure text (arms C and D, verbatim)

> `WT_FAIL The working-directory isolation context for this agent was lost, so this command
> would run in the parent session's directory instead of this agent's worktree
> (/…/.claude/worktrees/agent-a4c8b86d1c24dfde7). Refusing to run it. Retry the command; if
> this keeps failing, report that worktree isolation was lost.`

Worth reading closely: **Bash is not broken — the agent's cwd-isolation context is lost, and
Bash refuses rather than run in the wrong directory.** That is a safety refusal, which is
why it hits *every* Bash call rather than some. It also means the failure is loud, not
silent — unlike every other function-hooks failure mode measured so far.

## 🔴 The defect is specific to NATIVE `tool.call` — the classic bridge is SAFE

Arms E and F are the ones that change the adoption answer.

- **E** registers `classic.*`, a glob that *includes* `classic.PreToolUse` and therefore
  bridges to the Bash dispatch. Worktree Bash **works**.
- **F** registers `classic.PreToolUse` with a literal `{tool:"Bash"}` matcher — the exact shape
  a `hook_guard` migration would use — and the debug log confirms it was genuinely exercised,
  not merely loaded:

  ```
  hooks module wt-classic-pretooluse-bash loaded (worker, environment 1, tier user); events: classic.PreToolUse
  hooks module wt-classic-pretooluse-bash classic.PreToolUse settled in 4.8ms (worker hop, next() included)
  hooks module wt-classic-pretooluse-bash classic.PreToolUse settled in 0.6ms (worker hop, next() included)
  ```

  Two settles — one per Bash call the worktree subagent made. It ran on those exact calls and
  isolation survived.

**This closes an item #1020 lists as explicitly unverified.** That issue says: *"the safety of a
`classic.PreToolUse` bridge reaching Bash is **UNVERIFIED** too — it is not an established
workaround."* It is now established, by measurement, on 2.1.269.

So the restriction is narrower than #1020 states it. The correct rule is:

> **No NATIVE `tool.call` registration that can reach Bash** — literal matcher, bare
> `on("tool.call")`, or `on("*")`. The `classic.*` namespace is unaffected, matcher included.

### The vendor's own mod is built exactly this way

`anthropics/claude-code` ships `mods/sec-default/hooks/register.ts` (verified by
`gh api repos/anthropics/claude-code/contents/mods/sec-default/hooks`; control arm: `README.md`
resolves in the same repo). It registers **twelve** hooks and **not one is `tool.call`**:

```ts
on('classic.*',        ($, e, next) => next.to(e, 'append'))
on('prompt.section',   ($, e, next) => next.to(e, 'append'))
on('prompt.context',   ($, e, next) => next.to(e, 'append'))
on('skill.prompt',     ($, e, next) => next.to(e, 'append'))
on('attribution.text', ($, e, next) => next.to(e, 'append'))
on('settings.read',    ($, e, next) => next.to(e, 'append'))
on('tool.describe',    ($, e, next) => pastUsers(e, next))
on('command.describe', ($, e, next) => pastUsers(e, next))
on('agent.offer',      ($, e, next) => pastUsers(e, next))
on('agent.spawn',      ($, e, next) => pastUsers(e, next))
on('tool.register',    async ($, e, next) => { /* tier-aware deny */ })
on('tool.list',        async ($, e, next) => { /* restore managed tools */ })
```

Its own doc comment states the posture — *"Three moves: continue past the user tier
(`next.to(e, "append")`), refuse a user-tier caller by name, or pass… policy is
`$.settings.read`, memoized per burst; **fail closed**."*

### 🔴 CORRECTION — "the vendor never registers `tool.call`" was WRONG

An earlier revision of this report generalised the sentence above into *"the vendor observes
broadly through `classic.*` and engine events, and never registers `tool.call`."* **That was a
universal claim drawn from a one-mod sample, and it is false.**

`anthropics/claude-code` ships **three** mods, not one — `mods/{sec-default,diff,telemetry}`
(verified: `gh api repos/anthropics/claude-code/contents/mods` → `README.md`, `diff`,
`sec-default`, `telemetry`). And `mods/diff/hooks/register.ts` registers native `tool.call`
**twice**, one of them naming Bash:

```ts
on('tool.call', { tool: [...Tools.EDITING_TOOLS] }, async ($, e, next) => { … })   // :514
on('tool.call', { tool: [...Tools.SHELL_TOOLS]  }, async ($, e, next) => { … })   // :536
```
```ts
// mods/diff/hooks/tools/shell-tools.ts
export const SHELL_TOOLS = ['Bash', 'PowerShell'] as const
```

That is precisely arm B's shape. So the vendor ships a mod carrying the registration this probe
measures as breaking worktree subagents.

**What this does and does not change.** It does **not** touch arms A-F: those are measurements of
this binary's behaviour and stand on their own. What it refutes is the *inference from vendor
practice* — "Anthropic avoids `tool.call`, therefore so should we." They do not avoid it.

Three readings are open and this probe does not settle between them: the `diff` mod's use may
simply not have met a worktree subagent; #92533 may have a nuance these arms did not capture; or
that tree may be unreleased work that never ran against 2.1.269 (the harvest lane reports the
`mods/` tree pushed 2026-09-11 — the same day, so it may postdate the deployed binary entirely).

**The lesson is the one this session already caught once.** An hour earlier I criticised a review
lane for asserting *"not a worktree-isolation blocker"* — a negative nothing established. Then I
asserted *"never registers `tool.call`"* from a single file. Same defect, same session. A
universal claim about a corpus needs the corpus enumerated first: `contents/mods` is one call.

## Consequence: the examples-review verdict on `universal-audit-log` is REFUTED

`2026-09-11-fnhooks-examples-review.md` states, of `universal-audit-log.ts:39`'s `on("*")`:

> *"Matcher is `"*"` (all events). Agnostic to tool type. **NO Bash-specific blocker.** …
> **Not a worktree-isolation blocker**, but a general fail-open risk."*

and ranks it **#1 TEMPLATE** for the issue-retrieval use case. Arm C measures the opposite.
The lane asserted a negative that nothing established; #1020's own text calls wildcard
observers in-scope.

**Enumerating registrations, not grepping for `Bash`, is what found it.** A `grep Bash`
over the ten examples returns 4 files; enumerating every `on(...)` call returns **6**:

| File | Registration | Reaches Bash |
|---|---|---|
| `admin-capability-lockdown.ts:60,65` | `{tool:"Bash"}` ×2 | literal |
| `block-destructive-commands.ts:40` | `{tool:"Bash"}` | literal |
| `npm-to-pnpm-rewriter.ts:36` | `{tool:"Bash"}` | literal |
| `secret-redactor.ts:56` + `:65` | `{tool:"Bash"}` **and a bare `on("tool.call")`** | literal + wildcard |
| `tool-timing-badge.tsx:35` | bare `on("tool.call")` | **wildcard** |
| `universal-audit-log.ts:39` | `on("*")` | **wildcard** |
| `protected-paths-guard.ts:49` | `{tool:["Edit","Write","MultiEdit","NotebookEdit"]}` | no |
| `large-edit-confirmation.ts:20` | `{tool:["Edit","Write","MultiEdit"]}` | no |
| `webfetch-cache.ts:31` | `{tool:"WebFetch"}` | no |
| `websearch-to-exa.ts:27` | `{tool:"WebSearch"}` | no |

**6 of 10 are blocked, not 5.** The four clean ones are exactly the four that name a
non-Bash tool list explicitly.

## How much this actually costs THIS repo — scoped honestly

**No committed agent definition sets `isolation: worktree`.** Grepping `.claude/agents/*.md`
and `.claude/skills/*/SKILL.md` returns only prose *about* isolation (a capability table in
`claude-code-expert.md`, a section heading in `git-branch-commit-push-workflow`), never a
frontmatter `isolation: worktree`. Control arm: 16 agent files match `description`, so the
grep works. There is no `.worktreeinclude`.

But the `Agent` tool accepts `isolation` **per call**, and `agent-artifact-conventions.md:66`
documents worktree delegates as available. So the honest statement is: **adopting any
`tool.call` function hook would silently remove an option this repo documents and can invoke
at any dispatch site** — not "breaks something we run today".

## What this means for adoption

- A function hook may register `classic.PreToolUse` (measured enforcing, in the companion
  report) or a `tool.call` matcher naming **only non-Bash tools**. `protected-paths-guard`'s
  shape is the clean precedent.
- A **native** wildcard observer — `on("*")` or a bare `on("tool.call")` — is **not available**
  while worktree delegation is.
- **But `classic.*` IS available** (arm E), so a session-wide observer over the 33 classic
  events costs nothing. For both of this repo's use cases — session-start retrieval and the
  `PreToolUse` guard — the classic namespace is the right one anyway, so the practical cost of
  the restriction is close to zero.
- **`hook_guard` can migrate** via `classic.PreToolUse`, Bash matcher included, without losing
  worktree delegation (arm F).
- Vendor practice is **not** an argument either way here (see the correction above); the arms are.
- The restriction is now a measured fact about 2.1.269, so it should be re-tested on a version
  bump rather than carried forward as policy. The probe is four commands; re-run it.

## Limits

One machine, one binary, `-p` sessions only; n=1 per arm. Not tested: whether a
`classic.PreToolUse` registration (rather than native `tool.call`) reaching Bash triggers the
same loss — #1020 calls that UNVERIFIED and this probe did not close it. Not tested:
interactive sessions, or `isolation: "remote"`.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — #92533 is the defect reproduced here; #1020's restriction derives from it.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; #1020 carries the adoption restriction this probe converts from policy to measurement.
- [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) — source of the ten reviewed examples whose registration enumeration is tabled above.
