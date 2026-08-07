# Claude Code expertise — lazy / progressive loading of instruction context (2026-08-07, v2.1.224)

Corpora consulted: offline vendor docs (184 pages), shipped binary (2.1.222 / 2.1.223 / 2.1.224 all on disk), `claude --help`, live probe.

**Status: COMPLETE.** All six questions settled. Written incrementally.

## Headline

`.claude/rules/` is a **genuine, first-class harness mechanism**, and `paths:`
frontmatter **is** honoured as lazy scoping — **measured live on this machine at
2.1.224**, not merely doc-asserted. The repo's `rule_scoped` class is **not** a
fiction, and `md-size-budgets.md`'s claim that scoping works is correct.

Three things the design must absorb:

1. **There is no directory-entry trigger.** Lazy instructions load on a **file
   read**, never on `cd`. The one event that fires on `cd` (`CwdChanged`) cannot
   deliver context at all.
2. **Lazy instructions do not survive `/compact`.** Only root `CLAUDE.md` is
   re-injected. A scoped rule that hasn't matched since the last compaction is
   simply absent.
3. **No mechanism triggers on judgment.** For the ~86% of eager bytes that exist
   because no glob predicts them, the only real substitute is a **skill with a
   sharp description** — the model's own relevance decision.

## Verdict table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | CONFIRMED | `.claude/rules/*.md` is a real harness mechanism, not a repo convention | docs 14 of 184 pages (control `CLAUDE.md` → 67); binary `claude/rules` → 9 (control fresh `zzkflorbnaxq7712` → 0) |
| 2 | **CONFIRMED (live)** | `paths:` frontmatter genuinely lazy-scopes a rule | 3-arm `InstructionsLoaded` probe on disjoint-glob fixture; each arm loads one scoped rule and excludes the other |
| 3 | CONFIRMED | `InstructionsLoaded` fires with 5 load reasons and is the audit instrument | binary → 27 in both 2.1.222 and 2.1.224; `hooks.md:312` |
| 4 | **REFUTED** | "Entering a directory loads its instructions" | measured: trigger is a file read 3 levels deep; `CwdChanged` has no context lane (`hooks.md:802`, `:948`) |
| 5 | CONFIRMED | Lazy instructions are NOT re-injected after `/compact` | `memory.md:447-449` |
| 6 | CONFIRMED | `paths:` also works on `SKILL.md` | `skills.md:273`; 2nd route `changelog.md:218` |
| 7 | CONFIRMED | Hook `additionalContext` warns against imperative phrasing (prompt-injection defenses) | `hooks.md` § Add context for Claude |

## Q1 — `.claude/rules/*.md`: real mechanism, and `paths:` is honoured

**Falsifiable claim attacked:** "`.claude/rules/` is a repo convention that
Claude Code knows nothing about; `paths:` frontmatter is inert."

**REFUTED on every axis.**

Docs corpus: `.claude/rules` appears in **14 of 184** doc pages
(`permissions.md`, `changelog.md`, `glossary.md`, `plugins-reference.md`,
`claude-directory.md`, `context-window.md`, `hooks-guide.md`,
`cloud-environments.md`, `memory.md`, `features-overview.md`, `hooks.md`,
`large-codebases.md`, `agent-sdk__claude-code-features.md`, `env-vars.md`).
Control arm: `CLAUDE.md` → 67 pages with the same command shape, so the probe
discriminates.

The authoritative section is `memory.md:175-267` ("Organize rules with
`.claude/rules/`"). Verbatim, the load semantics:

- `memory.md:197` — "Rules without `paths` frontmatter are **loaded at launch
  with the same priority as `.claude/CLAUDE.md`**."
- `memory.md:218` — "Rules without a `paths` field are loaded unconditionally
  and apply to all files. **Path-scoped rules trigger when Claude reads files
  matching the pattern, not on every tool use.** As of v2.1.198, matching also
  works when Claude reaches a file through a symlinked path."
- `memory.md:185` — all `.md` files are discovered **recursively**, so
  subdirectories are supported for organisation.
- `memory.md:267` — user-level `~/.claude/rules/` load **before** project rules,
  giving project rules higher priority.

So the repo's split is real: an unscoped rule is eager, a `paths:`-scoped rule
is lazy and read-triggered.

### Constraints on `paths:` that the repo does not currently document

- **Brace-expansion budget** (`memory.md:243`): a rule's whole `paths` list
  shares one budget of **1,000 expanded patterns and 4 MiB**. Patterns without
  braces don't count. A pattern that would exceed the budget is used
  **unexpanded**, and its literal braces then match nothing — a silent
  no-op. Before v2.1.217 an over-braced `paths` value **stalled or crashed the
  CLI at startup**.
- **`[` is a bracket expression** (`memory.md:245`): `photos [2024/**` is
  invalid, matches nothing, and the rule's other patterns keep working. Escape
  as `\[`. Before v2.1.207 one invalid pattern made **the Read tool fail for
  every file the rule was evaluated against**.
- **`--setting-sources`** (`memory.md:199`): project rules are skipped if
  `project` is excluded. Before v2.1.211, on-demand rules (path-scoped, and
  rules in nested `.claude/rules/`) loaded **even when `project` was excluded**.

### Compaction behaviour — the load-bearing caveat

`memory.md:447`, verbatim:

> Project-root CLAUDE.md survives compaction: after `/compact`, Claude re-reads
> it from disk and re-injects it into the session. **Nested CLAUDE.md files in
> subdirectories and rules with `paths:` frontmatter are not re-injected
> automatically; they reload the next time Claude reads a file in that
> subdirectory or a file matching the rule's patterns.**

This is the real cost of moving a rule from eager to `paths:`-scoped: it is not
merely "loads later", it is **"can silently vanish mid-session"**. The doc says
so directly at `memory.md:449` — "If an instruction disappeared after
compaction, it was ... a path-scoped rule that hasn't matched a file since."

## Q2 — What triggers a nested `CLAUDE.md` load? Is there a directory-entry trigger?

**Falsifiable claim attacked:** "Entering a directory (a `cd`) loads that
directory's instructions."

**REFUTED. There is no directory-entry instruction-loading trigger.** The
trigger is a **file read**, not a directory entry.

The harness enumerates its own load reasons — this is the single most useful
artifact in the whole investigation, because it is the complete set, stated by
the code rather than inferred. `hooks.md:312`, the `InstructionsLoaded` matcher
row:

| Event | Matcher runs against | Values |
|---|---|---|
| `InstructionsLoaded` | load reason | `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact` |

Five reasons, and **not one of them is a directory entry**:

- `session_start` — eager load at launch (root + all parents, unscoped rules)
- `nested_traversal` — a nested `CLAUDE.md` pulled in **because Claude read a
  file in that subdirectory**
- `path_glob_match` — a `paths:`-scoped rule matched a file Claude read
- `include` — an `@path` import pulled from a parent instruction file
- `compact` — re-injection after compaction (root CLAUDE.md only, see Q1)

Binary control-armed: `nested_traversal` → **9** and `path_glob_match` → **9**
occurrences in both 2.1.222 and 2.1.224; fresh invented control
`qqvexnorbil5591` → **0**. `load_reason` → 7, `trigger_file_path` → 4.

Verbatim, `memory.md:157`:

> Claude also discovers `CLAUDE.md` and `CLAUDE.local.md` files in
> subdirectories under your current working directory. Instead of loading them
> at launch, **they are included when Claude reads files in those
> subdirectories.**

And `large-codebases.md:74`: "loads each subdirectory's file on demand **when it
reads files there**."

### A directory-entry EVENT does exist — but it cannot carry context

This is the nuance that matters for Ray's ask, and it is easy to get wrong.
`CwdChanged` is a real hook event (`hooks.md:58`):

> `CwdChanged` — When the working directory changes, for example when Claude
> executes a `cd` command. Useful for reactive environment management with tools
> like direnv.

It fires on **every** directory change and supports no matcher
(`hooks.md:308`). **But it has no context lane.** Two independent routes:

- `hooks.md:802` — CwdChanged: "Shows stderr to user only"
- `hooks.md:948` — CwdChanged is in the "None / No decision control. Used for
  side effects like logging or cleanup" group

So `CwdChanged` can run `direnv`, write to `CLAUDE_ENV_FILE`
(`hooks.md:1127`, `hooks.md:2547` — and those variables persist into subsequent
Bash commands), or log. It **cannot inject instruction text for Claude**.

**Bottom line for Ray's "when entering a directory":** the harness gives you
directory-*scoped* instructions (nested `CLAUDE.md`, path-scoped rules), and it
delivers them on **first file read in that scope**, which in practice is the
moment the instructions become relevant. A literal `cd`-triggered load is not
available, and the event that does fire on `cd` is observability-only.

### Does it survive `/compact`?

**No — and this is the sharpest edge in the whole design.** `memory.md:447`
(quoted verbatim in Q1): root `CLAUDE.md` is re-read from disk and re-injected;
**nested `CLAUDE.md` and `paths:`-scoped rules are not.** They reload only on
the next matching file read. `compact` is one of the five `load_reason` values,
so the re-injection is observable — and its absence for lazy files is
observable too.

## Q3 — Skills: how progressive disclosure actually works

Three tiers, and the model sees different things at each.

**Tier 1 — always in context: the skill listing.** Claude sees every discovered
skill's **name + `description` + `when_to_use`**, nothing else
(`large-codebases.md:367`: "Claude picks a skill by reading every discovered
skill's name and description, and only the chosen skill's full content loads
into context").

**Tier 2 — on invocation: the `SKILL.md` body** loads in full.

**Tier 3 — on demand: `references/` sub-files**, read with the Read tool only
if the body points at them.

### The caps, measured from the docs

- **1,536 characters** — the combined `description` + `when_to_use` text is
  truncated at this per-skill cap in the listing (`skills.md:259-260`).
  Configurable via `skillListingMaxDescChars`.
- **A global listing budget** on top of the per-skill cap — raise it with
  `skillListingBudgetFraction` (e.g. `0.02` = 2% of context) or the
  `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var as a fixed character count
  (`skills.md:949`).
- **`skillOverrides` → `"name-only"`** lists a low-priority skill **without its
  description**, freeing budget for others (`skills.md:949`). This is a real
  lever the repo is not using.

### ⭐ A skill can be path-gated — `paths:` is a SKILL.md field too

`skills.md:273`, verbatim:

> `paths` — Glob patterns that limit when this skill is activated. Accepts a
> comma-separated string or a YAML list. **When set, Claude loads the skill
> automatically only when working with files matching the patterns.** Uses the
> same format as path-specific rules.

Corroborated independently by `changelog.md:218`, which describes the
brace-expansion OOM fix as applying to "a `CLAUDE.md` **or `SKILL.md`** paths
frontmatter value" — so the same expander serves both. That is a second route to
the same fact.

⚠️ **Trap** (`skills.md:275`): `metadata` is a free-form map, but "Don't reuse
frontmatter field names such as `paths` as keys."

### Context isolation: `context: fork`

`skills.md` frontmatter table: `context: fork` runs the skill in a forked
subagent context, `agent` picks the subagent type, and `background` (default
**`true`**, requires v2.1.218+) controls whether the caller waits.
`changelog.md:200` records the default flip: "Changed skills with
`context: fork` to run in the background by default; opt out per skill with
`background: false`." This keeps a heavyweight skill's reads out of the main
conversation entirely.

## ⭐ LIVE PROBE — `paths:` scoping MEASURED WORKING on this machine, this version

Docs are one route. This is the second, and it is the one that settles it.

**Instrument:** an `InstructionsLoaded` hook injected via `--settings` (a
scratchpad file — no repo file was modified), logging
`load_reason | memory_type | file_path | trigger_file_path | globs`.

**Fixture:** the repo's own two `paths:`-scoped rules, whose globs are
**disjoint** — so each arm must load one rule and *not* the other. That is the
control arm built into the fixture itself, in both directions.

| Rule | `paths:` globs |
|---|---|
| `ci-local-parity.md` | `.github/workflows/*.yml`, `hk.pkl`, `mise.toml`, `.devcontainer/mise-system.toml` |
| `md-size-budgets.md` | `hk.pkl`, `**/CLAUDE.md`, `**/AGENTS.md`, `.claude/rules/*.md`, `.claude/skills/**/SKILL.md` |

### Arm A — `Read mise.toml`

```
path_glob_match | Project | .../.claude/rules/ci-local-parity.md
  |trig= .../mise.toml
  |globs= ['.github/workflows/*.yml', 'hk.pkl', 'mise.toml', '.devcontainer/mise-system.toml']
```

`md-size-budgets.md` — **ABSENT**. 23 `session_start` loads (21 unscoped rules +
`CLAUDE.md` + `.claude/CLAUDE.md`), 1 `include` (`AGENTS.md`), 1
`path_glob_match`.

### Arm B — `Read python/CLAUDE.md`

```
path_glob_match | Project | .../.claude/rules/md-size-budgets.md
  |trig= .../python/CLAUDE.md
  |globs= ['hk.pkl', '**/CLAUDE.md', '**/AGENTS.md', '.claude/rules/*.md', '.claude/skills/**/SKILL.md']
include         | Project | .../python/AGENTS.md |trig= .../python/CLAUDE.md
```

`ci-local-parity.md` — **ABSENT**. The exact complement of arm A.

### Arm C — `Read python/src/dotfiles_setup/lint.py`

```
nested_traversal | Project | .../python/CLAUDE.md
  |trig= .../python/src/dotfiles_setup/lint.py
include          | Project | .../python/AGENTS.md
  |trig= .../python/src/dotfiles_setup/lint.py
```

Neither scoped rule fired. And note the trigger file is **three directory
levels below** `python/CLAUDE.md` — nested traversal matches anywhere in the
subtree, not just the immediate directory.

### What this establishes

1. **`paths:` frontmatter is genuinely honoured.** Not inert. The repo's
   `rule_scoped` class is real, and `md-size-budgets.md`'s assertion that
   scoping works is **correct**.
2. **The three arms discriminate in both directions** — each loads one scoped
   rule and excludes the other, and arm C excludes both. A probe that could only
   say "loaded" would have shown the same thing for all three.
3. **`@import` chains lazily too.** `python/CLAUDE.md` is the one-line stub
   `@AGENTS.md`; reading a python source file pulled in `python/AGENTS.md` with
   `load_reason: include` and the *source file* as the trigger. So the repo's
   stub-plus-AGENTS.md pattern already lazy-loads correctly — the import does
   not force eagerness at the nested level.
4. **21 of 23 rules are confirmed eager**, exactly as the byte accounting said.

⚠️ **Method note for re-running:** `--settings` is a *flag*-scope source and
hooks **merge** across sources, so this probe adds an `InstructionsLoaded` hook
without disturbing the repo's own hooks. It requires no repo edit.

## Q4 — Hooks as a disclosure lane

**Yes — `additionalContext` is a supported, documented way to deliver rule text
at the moment of need.** But it carries four constraints that bear directly on
whether this repo's rules can move there.

### Which events can inject context, and where it lands

`hooks.md:911-916` places the injected reminder per event:

| Event group | Reminder appears |
|---|---|
| `SessionStart`, `Setup`, `SubagentStart` | start of conversation, before first prompt |
| `UserPromptSubmit`, `UserPromptExpansion` | alongside the submitted prompt |
| `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch` | next to the tool result |
| `Stop`, `SubagentStop` | end of the turn; conversation continues so Claude can act on it |

Delivery mechanics (`hooks.md:898`): "Claude Code wraps the string in a **system
reminder** and inserts it into the conversation at the point where the hook
fired. Claude reads the reminder on the next model request, but it doesn't
appear as a chat message."

### The four constraints

1. **10,000-character cap** (`hooks.md:838`, `:918`). Over that, Claude Code
   writes the text to a file and passes **a path plus a short preview** instead.
   For reference, this repo's largest single rule
   (`secrets-out-of-the-shell-env.md`) is well past that — it could not be
   delivered inline as one blob.
2. ⚠️ **Imperative phrasing can trigger prompt-injection defenses.**
   `hooks.md` § "Add context for Claude", verbatim:

   > Write the text as factual statements rather than imperative system
   > instructions. Phrasing such as "The deployment target is production" or
   > "This repo uses `bun test`" reads as project information. **Text framed as
   > out-of-band system commands can trigger Claude's prompt-injection defenses,
   > which causes Claude to surface the text to you instead of treating it as
   > context.**

   This is the single biggest obstacle to moving this repo's rules into hooks.
   Our rules are written as imperatives — "Never add ignore rules", "You MUST
   run local validation", "Do NOT bulk `git add .`". That is precisely the
   register the docs warn about. A hook-delivered rule corpus would need
   rewriting into declarative form, or it risks being surfaced to Ray as
   suspicious text instead of obeyed.

3. **The docs explicitly steer static rules away from hooks.** Same section:
   "For instructions that never change, prefer CLAUDE.md. **It loads without
   running a script** and is the standard place for static project conventions."
   Hooks are positioned for *environment state*, not for a rule library.

4. **Resume replays stale text.** For mid-session events, `--continue`/`--resume`
   "replays the saved text rather than re-running the hook for past turns".
   `SessionStart` hooks *do* re-run on resume (`source: "resume"`).

### The glob-scoped hook lane — `if:` conditions

`hooks.md:414` — a hook entry accepts an `if:` field using **permission-rule
syntax**, e.g. `"Bash(git *)"` or `"Edit(*.ts)"`. The hook command runs only if
the tool call matches.

⚠️ **Only evaluated on tool events**: `PreToolUse`, `PostToolUse`,
`PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`. **On other
events, a hook with `if` set never runs** — a silent no-op if you attach one to
`UserPromptSubmit`.

⚠️ `changelog.md:319`: single-segment `dir/**` `if:` conditions now match only
`<cwd>/dir`; write `**/dir/**` for any-depth matching. `deny`/`ask` permission
rules keep their any-depth match — so the two syntaxes **diverge**.

This gives a genuine **action-triggered** delivery lane: `PreToolUse` with
`if: "Edit(**/*.py)"` returning `additionalContext` delivers a rule at the
moment of the edit — earlier and more precisely than a file-read glob.

### `UserPromptSubmit` timeout — a fail-open hazard

`hooks.md:1229`: `UserPromptSubmit` has a **30-second default timeout** (vs 600s
elsewhere), and on timeout the hook is cancelled and **its `additionalContext`
is discarded — the prompt still reaches Claude without that context**. A
rule-delivery hook on this event fails *open* and silently. The transcript shows
a notice, but the turn proceeds ungoverned.

## Q5 — What is new since 2.1.206 bearing on context loading

From `changelog.md` (this tree covers through 2.1.224, August 7 2026):

| Version | Change |
|---|---|
| 2.1.198 | `paths:` matching works through **symlinked** paths into the project dir |
| 2.1.207 | Fixed: one invalid `[` glob made **the Read tool fail for every file** the rule was evaluated against; now it matches nothing and siblings keep working |
| 2.1.211 | Fixed nested `.claude/rules/*.md` loading **even when setting sources excluded project settings**; also `.claude/settings.local.json` now loads repo-wide, not only from the starting directory |
| 2.1.217 | Brace expansion in `CLAUDE.md`/`SKILL.md` `paths:` is now **budget-bounded** (1,000 patterns / 4 MiB); previously many brace groups **OOM-killed or stalled the CLI at startup** |
| 2.1.218 | `background: false` opt-out for `context: fork` skills; boolean frontmatter accepts `yes/no/on/off/1/0` |
| ~2.1.219 | Skills with `context: fork` **run in the background by default** |
| 2.1.223 | Auto-compact keeps sessions on unrecognized model IDs within the assumed window (`CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1` restores old behaviour) |

**Net:** every one of these is a *hardening* of the lazy-loading path. The
mechanism was rough as recently as 2.1.207–2.1.217 (a bad glob could break the
Read tool; an over-braced `paths:` could crash startup at launch). On **2.1.224
those are all fixed**, which is a meaningful part of why adopting scoping now is
safer than it would have been in July.

### Debugging surfaces

- **`/context`** (`debug-your-config.md:15`) — "shows everything occupying the
  context window ... system prompt, system tools, MCP tools, custom subagents
  with the source each loaded from, **memory files**, skills, and conversation
  messages. Run it first to confirm whether your CLAUDE.md, rules, or skill
  descriptions are present at all." This is the direct read-out of the byte
  budget this whole exercise is about.
- **`debug-your-config.md:30`** explicitly anticipates the confusion:
  "Subdirectory CLAUDE.md files load on demand when Claude reads a file in that
  directory with the Read tool, not at session start" — so a missing file in
  `/context` is expected, not a bug.
- **`InstructionsLoaded` hook** (`memory.md:432`) — "log exactly which
  instruction files are loaded, when they load, and why. This is useful for
  debugging path-specific rules or lazy-loaded files in subdirectories." This is
  the instrument used above, and it is worth wiring permanently.
- **`/doctor`**, **`/hooks`**, **`/mcp`** — the rest of the config-debug set.
- **`claudeMdExcludes`** (`memory.md:323`, `large-codebases.md:147`) — glob-based
  exclusion of CLAUDE.md **and rules** files, e.g. `"**/packages/legacy-*/**"`.

## Q6 — Ranked: which mechanisms can carry a JUDGMENT-triggered rule?

The hard class: a rule no glob predicts — "a warning is about to be dismissed",
"you are about to hand-roll something a tool already does". This is ~86% of the
repo's eager bytes and the stated reason those rules are eager.

**The honest headline: no mechanism triggers on judgment.** Every lazy
mechanism the harness offers keys on an *observable event* — a file read, a tool
call, a prompt's text. Judgment is not an observable event. What follows is
ranked by how well each **proxies** it.

| # | Mechanism | Trigger | Can carry judgment-triggered rules? |
|---|---|---|---|
| 1 | **Eager (unscoped rule / root CLAUDE.md)** | session start, always present | **Yes — the only mechanism that genuinely can.** Cost is the entire problem. |
| 2 | **Skill, description-triggered** | model reads name+description each turn and decides | **Closest real substitute.** The model itself judges relevance from a ≤1,536-char description — that IS judgment-triggered dispatch. Cost: only the description is standing (~a few hundred bytes vs the full rule). Risk: it is a model decision, so it can miss. |
| 3 | **`PreToolUse` hook + `if:` + `additionalContext`** | a matching tool call is about to happen | **Partly.** Catches *action*-shaped judgment ("about to run `gh pr merge`", "about to write a `# noqa`") — this repo already proves the pattern with `hook_guard`. Deterministic and unmissable, but only for rules expressible as a tool-call pattern. Constrained by the imperative-phrasing warning (Q4). |
| 4 | **`paths:`-scoped rule** | Claude reads a matching file | **No, but strong for the file-shaped subset.** Deterministic and measured working. Useless for a rule whose trigger is a decision, not a file. |
| 5 | **Nested `CLAUDE.md`** | Claude reads a file in that subtree | **No.** Same limit as #4, coarser. Good for area conventions. |
| 6 | **`UserPromptSubmit` hook** | every prompt | Could inject rules conditioned on prompt keywords — but fails open on a 30s timeout, and re-injecting a corpus every turn recreates the eager cost with extra latency. |
| 7 | **`SessionStart` `additionalContext`** | session start | Equivalent to eager, but pays a script run and does not survive compaction re-injection the way root CLAUDE.md does. **No advantage.** |
| 8 | **`CwdChanged`** | `cd` | **Cannot deliver context at all** (Q2). Environment side effects only. |

### The recommendation this ranking implies

Split the eager corpus by **trigger shape**, not by size:

- **File-shaped** rules (`ci-local-parity`, `devcontainer`, `persistence-gate-retry`,
  `local-devcontainer-first`, `zero-bash-logic`) → `paths:`-scoped rules.
  Measured working, deterministic, zero model judgment.
- **Action-shaped** rules (`mise-tasks-only`, `do-not`, `gh-cli-watch`) → already
  hook-enforced; the *prose* can follow the enforcement into `PreToolUse`
  `additionalContext`, rewritten declaratively.
- **Judgment-shaped** rules (`zero-skip-policy`, `use-tool-builtins`,
  `probes-need-a-control-arm`, `clarify-before-acting`,
  `verify-before-advancing`) → **skills with sharp descriptions**, keeping only
  a one-line directive eager. This is the only lane that preserves the trigger.
- **Keep genuinely eager**: the short directive lines that must never be absent.

⚠️ **The compaction tax applies to everything you move** (Q1/Q2): a
`paths:`-scoped rule that has not matched a file *since the last compaction* is
simply not in context. For a rule whose whole job is to fire at an unpredictable
moment, that is a real correctness cost, not just a latency one. This is the
strongest argument for keeping the judgment-shaped directives eager and moving
only their **evidence and archaeology** out — which is what
`docs/rules-evidence/` was already built to do.

## Corrections to the existing ledger

Nothing in `.claude/agents/claude-code-expert.md`'s ledger is contradicted by
2.1.224. Two **additions** are warranted (see below) — the ledger had no rows at
all on instruction loading, `InstructionsLoaded`, or `paths:` scoping.

## Ledger entries to append

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| **`paths:` frontmatter on `.claude/rules/*.md` is genuinely honoured** — MEASURED, not doc-asserted | CONFIRMED | live `InstructionsLoaded` probe, 3 arms: `mise.toml`→`ci-local-parity` only; `python/CLAUDE.md`→`md-size-budgets` only; `lint.py`→neither. Disjoint-glob fixture arms it both ways | 2.1.224 | 2026-08-07 |
| **The complete set of instruction load reasons is 5**: `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact` — enumerated by the harness's own matcher, not inferred | CONFIRMED | `$CC/hooks.md:312`; binary `nested_traversal`/`path_glob_match` → 9/9 in both 2.1.222 and 2.1.224, control fresh `qqvexnorbil5591` → 0 | 2.1.224 | 2026-08-07 |
| ⚠️ **There is NO directory-entry instruction trigger.** Nested `CLAUDE.md` loads on a FILE READ anywhere in the subtree (measured 3 levels deep), never on `cd` | CONFIRMED | live arm C; `$CC/memory.md:157`, `large-codebases.md:74` | 2.1.224 | 2026-08-07 |
| **`CwdChanged` fires on every `cd` but has NO context lane** — stderr-to-user only, no decision control, no `additionalContext`. It can only do env side effects via `CLAUDE_ENV_FILE` | CONFIRMED | `$CC/hooks.md:58, :308, :802, :948` — two independent routes to the no-decision-control fact | 2.1.224 | 2026-08-07 |
| ⚠️ **Lazy instructions do NOT survive `/compact`** — root `CLAUDE.md` is re-read and re-injected; nested `CLAUDE.md` and `paths:`-scoped rules are not, and reload only on the next matching read | CONFIRMED | `$CC/memory.md:447-449` | 2.1.224 | 2026-08-07 |
| **`@import` chains lazily** — a nested `CLAUDE.md` stub's `@AGENTS.md` loads with `load_reason: include` and the *triggering source file* as `trigger_file_path` | CONFIRMED | live arms B and C | 2.1.224 | 2026-08-07 |
| ⭐ **`paths:` is a `SKILL.md` frontmatter field too** — a skill can be path-gated for automatic activation | CONFIRMED | `$CC/skills.md:273`; second route `changelog.md:218` names "`CLAUDE.md` **or `SKILL.md`** paths frontmatter" in the brace-budget fix | 2.1.224 | 2026-08-07 |
| ⚠️ **Hook `additionalContext` warns AGAINST imperative phrasing** — "text framed as out-of-band system commands can trigger Claude's prompt-injection defenses, which causes Claude to surface the text to you instead of treating it as context". This repo's rules are written in exactly that register | CONFIRMED | `$CC/hooks.md` § Add context for Claude | 2.1.224 | 2026-08-07 |
| Hook `additionalContext` is capped at **10,000 chars**; overflow is written to a file and replaced by a path + preview | CONFIRMED | `$CC/hooks.md:838, :918` | 2.1.224 | 2026-08-07 |
| ⚠️ **A hook `if:` condition is evaluated ONLY on tool events** (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`). On any other event a hook with `if` set **never runs** | CONFIRMED | `$CC/hooks.md:414` | 2.1.224 | 2026-08-07 |
| ⚠️ **`UserPromptSubmit` fails OPEN**: 30 s default timeout (vs 600 s elsewhere); on timeout its `additionalContext` is **discarded and the prompt proceeds** | CONFIRMED | `$CC/hooks.md:1229` | 2.1.224 | 2026-08-07 |
| Skill listing shows name + `description` + `when_to_use`, capped at **1,536 chars/skill**; global budget via `skillListingBudgetFraction` / `SLASH_COMMAND_TOOL_CHAR_BUDGET`; `skillOverrides: "name-only"` lists a skill without its description | CONFIRMED | `$CC/skills.md:259-260, :949` | 2.1.224 | 2026-08-07 |
| `paths:` brace expansion is budget-bounded at **1,000 patterns / 4 MiB**; an over-budget pattern is used **unexpanded** and matches nothing. Pre-2.1.217 it OOM-killed/stalled the CLI at startup | CONFIRMED | `$CC/memory.md:243`; `changelog.md:218` | 2.1.224 | 2026-08-07 |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the shipped CLI bundles (2.1.222 / 2.1.223 / 2.1.224) byte-scanned for load-reason tokens, and the live `InstructionsLoaded` probe
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the offline `agent-harness-docs` claude-code doc tree (184 pages) that is the semantics corpus
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the fixture: its 23 rules, 2 of them `paths:`-scoped with disjoint globs, and its 6 `CLAUDE.md` files
