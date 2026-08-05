# Claude Code 2.1.222 — Subagent Orchestration and Context Surface

**Version under test:** `/Users/rmanaloto/.local/share/claude/versions/2.1.222` (271,289,792 bytes, mtime 2026-08-04)
**Docs corpus:** `$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code` (174 `.md` + `docs_manifest.json`)
**Date:** 2026-08-05
**Scope:** does the subagent surface support a DAG-shaped multi-agent framework with cross-session durability?

## Control arms (run before any absence claim)

| Probe shape | Known-present arm | Freshly-invented known-absent arm | Discriminates? |
|---|---|---|---|
| `grep -rlF <tok> $CC/*.md` | `subagent` → **87 files** | `Kwvbzt9Qrxm` → **0** | YES |
| `find ~/.claude/projects -type d -name X` | `subagents` → **72 dirs** | `zqvhbn7subagents` → **0** | YES |

The brief's premise re-verified: `SendUserMessage` → **0 across all 174 doc pages** (same command shape that
returns 87 for `subagent`). The docs are incomplete; nothing below rests on docs alone where the binary can speak.

## Findings table

| Verdict | Claim | Corpus + control arm |
|---|---|---|
| CONFIRMED | Nesting default is **3** layers below main | binary `var g$u=3`; `$CC/sub-agents.md:863` |
| **CONFIRMED (undocumented)** | Absent the env var, depth comes from a **remote feature gate** `tengu_hazel_trellis`, cached and `MAY_BE_STALE` | binary `Jre()` body; token absent from all 174 doc pages (control: `subagent`→87) |
| CONFIRMED | Session cap **200**, concurrent cap **20**, web-search cap 200 | binary `cx_=20,ux_=200,dx_=200` |
| **CONFIRMED (undocumented)** | A remote gate `tengu_amber_kestrel` **disables the concurrency cap entirely** | binary concurrency check body |
| CONFIRMED | At the depth limit the `Agent` tool is **withheld**; a fork keeps it but it **errors** | `$CC/sub-agents.md:863` |
| **CONFIRMED (crux)** | **Teammates cannot spawn teammates** — "the team roster is **flat**" | binary error string; `$CC/agent-teams.md` § Limitations |
| CONFIRMED | An in-process **teammate cannot spawn a background agent** | binary `subagent_teammate_background_denied`; `$CC/agent-teams.md` § Limitations |
| REFUTED | "Structured/typed output exists for subagents outside the Workflow tool" | 17-field frontmatter table has **no** schema field; `--json-schema` is session-scoped |
| CONFIRMED | Workflow `agent()` **does** take a `schema` option | `$CC/workflows.md:290` |
| CONFIRMED | Chaining is **caller-relayed only** — no typed edge between subagents | `$CC/sub-agents.md:834-840` |
| CONFIRMED | Subagent transcripts persist, keyed by **sessionId** | 2,077 `agent-*.jsonl` on disk (control: 0) |
| **CONFIRMED (blocker)** | Resume is **within-session only** — no cross-session subagent handle | `$CC/sub-agents.md:973`; disk layout |
| CONFIRMED | A fork **shares the parent prompt cache**; a named subagent gets a separate one | `$CC/sub-agents.md:1045,1047` |
| CONFIRMED | **A fork can't spawn further forks** | `$CC/sub-agents.md:1053` |
| CONFIRMED | `CLAUDE_CODE_FORK_SUBAGENT=1` **removes** `run_in_background` from the Agent tool | `$CC/sub-agents.md:784` |
| CONFIRMED | Output scanning **never removes or rewords**; it cannot reject a result | `$CC/sub-agents.md:797-802` |
| CONFIRMED | Workflow runtime has its **own** caps: 16 concurrent, 1,000 per run | `$CC/workflows.md` § Behavior and limits |

---

## Q1 — Chain subagents: is there anything beyond hand-relaying?

**No. Chaining is caller-relayed prose.** `$CC/sub-agents.md:834-840` verbatim:

> #### Chain subagents
> For multi-step workflows, ask Claude to use subagents in sequence. Each subagent completes its task
> and returns results to Claude, which then passes relevant context to the next subagent.
> `Use the code-reviewer subagent to find performance issues, then use the optimizer subagent to fix them`

That is the entire documented mechanism: the orchestrator reads agent A's free-text report and writes agent B's
prompt. There is **no edge object, no typed artifact, no schema on the boundary**.

**Structured output — REFUTED for subagents, CONFIRMED for workflows.** Enumerated by shape rather than by
expected name (`grep -roE '\b(outputSchema|output_schema|outputFormat|output_format|json_schema|jsonSchema)\b'`
over all 174 pages):

- Every hit is in `agent-sdk__structured-outputs.md`, `agent-sdk__python.md`, `agent-sdk__typescript.md`
  (session-level `outputFormat: {type:'json_schema'}`) or one unrelated `changelog.md:2418` line about
  `claude mcp serve` clients validating an MCP `outputSchema`.
- The subagent frontmatter table (`$CC/sub-agents.md:276-294`) enumerates **17 fields**: `name`, `description`,
  `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`,
  `background`, `effort`, `isolation`, `color`, `initialPrompt`. **None is a schema/output field.**
- The CLI has `--json-schema <schema>` — but it is **session-scoped** (the whole `claude -p` run's final output),
  not per-subagent.

The one real typed mechanism is the **Workflow** runtime, `$CC/workflows.md:289-295` verbatim:

```javascript
const found = await agent('List every .ts file under src/routes/.', {
  schema: { type: 'object', required: ['files'], properties: { files: { type: 'array', items: { type: 'string' } } } },
})
const audits = await pipeline(found.files, file =>
  agent(`Audit ${file} for missing authentication checks.`, { label: file }),
)
```

This is the only place in the product where one agent's output is **typed** and fed programmatically into the
next agent's fan-out. It is exactly the DAG primitive — and it is inside the Workflow tool, which the brief
scopes out. `$CC/workflows.md:302`: an `agent()` call **resolves to `null`** if stopped or on an unrecoverable
API error, and `pipeline()` keeps the `null` — so error handling is caller-side too.

## Q2 — Nesting rules, depth variable, what is withheld (the DAG crux)

**Can a subagent fan out? YES — up to depth 3 by default, on the plain-subagent path only.**

`$CC/sub-agents.md:863-865` verbatim:

> By default, a subagent can spawn subagents of its own, up to three layers below the main conversation. At the
> depth limit, Claude Code withholds the `Agent` tool from every subagent except a [fork](#fork-the-current-conversation),
> so a subagent at the limit does its delegated work itself and returns one summary. A fork at the limit keeps
> `Agent` in its inherited tool list, but the tool returns an error instead of spawning.
> Nested subagents suit a delegated task that itself splits into parallel subtasks, such as a reviewer subagent
> that dispatches a verifier per finding, so the intermediate output never reaches your main conversation.
> **Only the top-level subagent's summary returns to you.**

Binary, verbatim (the resolution function):

```
function Jre(){let e=te.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH;if(e!==void 0)return e;
if(Dbs===null){let{getFeatureValue_CACHED_MAY_BE_STALE:t}=(Zr(),Wr(wpr)),r=t(jk_,g$u);
Dbs=typeof r==="number"&&Number.isInteger(r)&&r>=1?r:g$u}return Dbs}
var g$u=3,jk_="tengu_hazel_trellis",Dbs=null;
```

Three facts, only the first documented:

1. Default `g$u = 3`. Env var wins outright (`if(e!==void 0)return e`), validated `Integer && >=1`.
2. **UNDOCUMENTED:** with no env var the depth is a **server-side feature-gate value** (`tengu_hazel_trellis`),
   read from a cache explicitly named `getFeatureValue_CACHED_MAY_BE_STALE`. *The effective nesting depth on a
   given machine is not knowable from the docs and can change without a client update.* Control arm:
   `tengu_hazel_trellis` → 0 hits across all 174 doc pages, against `subagent` → 87. **Pin it explicitly in
   `settings.json` if a DAG depends on it.**
3. Enforcement is a spawn-time throw, verbatim:

```
throw me("subagent_launch","subagent_depth_cap"),new jHe(`Subagent nesting limit reached (depth ${m} of ${h}).
Complete this task directly using your tools instead of spawning another agent. If the user explicitly requested
deeper nesting, ask them to raise CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH.`)
```

**How a nested result reaches the top: it does not.** Only the top-level subagent's summary returns
(`:865`). Intermediate output is deliberately absorbed — that is the stated feature ("the intermediate output
never reaches your main conversation"). For a DAG this cuts both ways: context stays clean, but **the
orchestrator cannot see or route depth-2 results**. One escape hatch, added 2.1.220 (`changelog.md`, verbatim):

> Added nested subagent forwarding in stream-json: subagents spawned at depth-2+ now appear when
> `--forward-subagent-text` is set, keyed by their spawning Agent `tool_use` id

So in `--print --output-format=stream-json` mode with `--forward-subagent-text`, an external driver **can**
observe the whole tree with parent linkage (`parent_tool_use_id`). That is observability, not routing.

**The hard nesting ban — teammates.** Binary, verbatim:

```
let w=!!l.teammateContext;
if((w||!!bVe())&&i)throw me("subagent_launch","subagent_nested_teammate"),
new jHe("Teammates cannot spawn other teammates — the team roster is flat.
To spawn a subagent instead, omit the `name` parameter.");
if(w&&o===!0)throw me("subagent_launch","subagent_teammate_background_denied"),
new jHe("In-process teammates cannot spawn background agents.
Use run_in_background=false for synchronous subagents.");
```

Corroborated in `$CC/agent-teams.md` § Limitations:

> * **No nested teams**: teammates cannot spawn their own teammates. Only the lead can manage the team.
> * **No background subagents from in-process teammates**: … Asking for a background one, whether with
>   `run_in_background` or a subagent definition that sets `background: true`, returns an error, **because a
>   teammate's background work can't outlive the lead's process**.
> * **One team per session**: … You can't create additional named teams or share a team across sessions.
> * **Lead is fixed**: the main session is the lead for its lifetime.

**Net:** the `name` parameter is the switch. Passing `name` makes a **teammate** — flat roster, no fan-out,
foreground-only children. Omitting it makes an ordinary **subagent** — which *can* fan out, to depth 3.
A DAG must therefore be built on unnamed subagents, and accept that it loses `SendMessage`-addressability by
name (see Q4).

## Q3 — What loads at startup (the ~78–85k cost), and can it be reduced?

`$CC/sub-agents.md:919-936` enumerates a non-fork subagent's initial context — six items, verbatim headings:

* **System prompt** — the agent's own prompt plus appended environment details, *not* the full Claude Code system prompt.
* **Task message** — the delegation prompt.
* **CLAUDE.md files** — "**every level of the CLAUDE.md hierarchy** the main conversation loads, including
  `~/.claude/CLAUDE.md`, project rules, `CLAUDE.local.md`, and managed policy files."
* **Git status** — snapshot from the start of the parent session.
* **Preloaded skills** — "**full content** of any skill named in the agent's `skills` field."
* **Sibling roster** — system reminder listing `main` + every other named agent; only when tools include
  `SendMessage` and ≥1 other agent has a name; **a snapshot taken when the subagent starts**, so agents named
  later never appear (v2.1.206+).

**This is the ~78–85k answer for this repo**: the CLAUDE.md hierarchy here is large (root `AGENTS.md` at 200
lines + ~15 eager `.claude/rules/*.md`), and it is re-injected into **every** subagent.

**Documented reduction levers — thin.** `$CC/sub-agents.md:928` verbatim:

> Explore and Plan are the only subagents that omit CLAUDE.md and git status. **There is no frontmatter field
> or per-agent setting to change which agents skip them.**

So the only in-product ways down are:

| Lever | Effect | Anchor |
|---|---|---|
| Use built-in `Explore` / `Plan` | Skips CLAUDE.md **and** git status | `:928` |
| Use a **fork** | Shares the parent prompt cache → cheap, but inherits *everything* | `:1047` |
| Don't set `skills:` | Avoids full-skill-body injection | `:925` |
| `includeGitInstructions: false` | Drops the git-status block only | `:924` |
| `--bare` (session level) | Skips hooks, LSP, auto-memory, **CLAUDE.md auto-discovery** | `claude --help` |
| `--exclude-dynamic-system-prompt-sections` | Moves cwd/env/memory-paths/git-status out of the system prompt into the first user message — improves **cache reuse**, doesn't reduce tokens | `claude --help` |

**Never reaches a non-fork subagent** (`:932-936`): output style, **auto memory** (the main conversation's
`MEMORY.md` — a subagent needs its own `memory:` field), and the parent's context-window size (a subagent's
window is sized by *its own* model).

Undocumented, present in the binary and worth knowing: `CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT`,
`CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_CACHE_EVICT`, `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS`,
`CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS`. None appear in the docs corpus with the same grep shape that finds
`subagent` in 87 files. **NEEDS-PROBE** — existence is not semantics.

## Q4 — Resume: identifier, and does it survive the parent session? (the durability blocker)

**Mechanism (CONFIRMED):** `SendMessage` with the agent's **ID or name** as `to` (`$CC/sub-agents.md:946`).
Notable properties, all verbatim from `:944-966`:

* "The built-in Explore and Plan agents are **one-shot and return no agent ID**, so they can't be resumed."
* "A completed subagent that receives a `SendMessage` **auto-resumes in the background** without a new `Agent`
  invocation. The same applies to a subagent that Claude stopped with the `TaskStop` tool."
* v2.1.191+: "a subagent **you** stopped yourself … **doesn't auto-resume**. The `SendMessage` call returns a
  refusal telling Claude the agent was cancelled."
* v2.1.199+: `SendMessage` verifies "that a name still refers to the same agent it reached earlier"; if a newer
  agent took the name it **refuses the send**. "The check is scoped to the current conversation and **resets on
  `/clear`**." → **name is not a stable key; the agent ID is.**
* Resuming "starts a new run of the agent under the same ID" and (`:909`) "takes a **fresh slot without checking
  the limit**, so resumes can push the running count past it."
* v2.1.198+: an agent-sent message is normal task direction, **but** "no message from any agent counts as your
  approval for a pending permission prompt, and no agent message can change a subagent's permission settings,
  `CLAUDE.md`, or configuration."

**Durability — REFUTED for cross-session.** `$CC/sub-agents.md:968,970-974` verbatim:

> …find IDs in the transcript files at `~/.claude/projects/{project}/{sessionId}/subagents/`. Each transcript is
> stored as `agent-{agentId}.jsonl`.
> * **Main conversation compaction**: when the main conversation compacts, subagent transcripts are unaffected.
> * **Session persistence**: subagent transcripts **persist within their session**. You can resume a subagent
>   after restarting Claude Code **by resuming the same session**.
> * **Automatic cleanup**: Claude Code deletes subagent transcripts after the `cleanupPeriodDays` retention
>   period, 30 days by default.

Empirically confirmed on this machine (control-armed):

```
find ~/.claude/projects -type d -name 'subagents'      → 72 dirs
find ~/.claude/projects -type d -name 'zqvhbn7subagents' → 0      (control arm, freshly invented)
find ~/.claude/projects -type f -name 'agent-*.jsonl'  → 2077 files
oldest: .../4aa2e774-.../subagents/workflows/wf_349dd9f6-91e/agent-a76525f7a3f5e4404.jsonl
newest: .../7e75e5ce-.../subagents/agent-a74191c42a65298be.jsonl
```

The path is `{sessionId}/subagents/` — **the agent ID is namespaced under a session ID**. (Workflow agents get
their own `subagents/workflows/wf_<runid>/` subtree.) So:

- **Survives a process restart? YES** — but only via `claude --resume <sessionId>`, which rehydrates the *parent*
  conversation and with it the agent handles.
- **Survives the parent session ending / a different session? NO.** There is no cross-session agent handle. The
  `SendMessage` name check is explicitly "scoped to the current conversation and resets on `/clear`". A new
  session cannot address a prior session's subagent.
- Agent **teams** are worse: `$CC/agent-teams.md` § Limitations — "**No session resumption with in-process
  teammates**: `/resume` and `/rewind` do not restore in-process teammates. After resuming a session, the lead
  may attempt to message teammates that no longer exist."

**The one durable unit is the *session*, not the subagent.** `claude --bg` / `/fork` create real background
**sessions** (own row in `claude agents`, own budget, `claude attach` id, JSON-listable via
`claude agents --json`). `$CC/sub-agents.md:896`: "A session you create with `/fork` **doesn't count** [toward
the 200 cap]; it runs as a separate background session with its own budget."

## Q5 — Auto-compaction

`$CC/sub-agents.md:976-993` verbatim: "Subagents support automatic compaction using the same logic as the main
conversation. Compaction triggers under the same conditions, and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` applies to
subagents as well." Logged in the subagent transcript as:

```json
{"type":"system","subtype":"compact_boundary","compactMetadata":{"trigger":"auto","preTokens":167189}}
```

`$CC/env-vars.md:189` adds a constraint the subagent page omits: the override "**can't raise the threshold**, so
values above the default percentage are ignored", and it "applies only in sessions that compact before the
model's context limit."

**What is preserved:** the docs say compaction uses "the same logic as the main conversation" and do not
enumerate a subagent-specific retention rule. `$CC/sub-agents.md:972` guarantees only that main-conversation
compaction leaves subagent transcripts **unaffected** (separate files). **NEEDS-PROBE** — no doc anchor states
what survives *a subagent's own* compaction beyond the general mechanism. For a long-running DAG node, treat
mid-run compaction as lossy and require the node to persist findings to disk incrementally.

Relevant: `CLAUDE_AUTO_BACKGROUND_TASKS=1` "moves subagents to the background after running for approximately
two minutes" (`$CC/env-vars.md:190`).

## Q6 — Forks: cheaper? Confirm/refute, and every stated limitation

**CONFIRMED — a fork shares the parent's prompt cache; a named subagent does not.**
`$CC/sub-agents.md:1039-1047`, the comparison table verbatim:

| | Fork | Named subagent |
|---|---|---|
| Context | Full conversation history | Fresh context with the prompt you pass |
| System prompt and tools | Same as main session | From the subagent's definition file, filtered for background runs |
| Model | Same as main session | From the subagent's `model` field |
| Permissions | Prompts surface in your terminal | Prompts surface in your main session when running in the background |
| **Prompt cache** | **Shared with main session** | **Separate cache** |

`:1047` verbatim: "Because a fork's system prompt and tool definitions are identical to the parent, its first
request **reuses the parent's prompt cache**. This makes forking **cheaper** than spawning a fresh subagent for
tasks that need the same context."

**Quantification: the docs give NONE.** No number, ratio, or token figure accompanies the claim on this page.
`$CC/prompt-caching.md#subagents-and-the-cache` is the cross-reference. I did not measure it here, so any
figure would be an inherited number without a control arm — **NEEDS-PROBE** if a cost model depends on it.
Note the asymmetry: a fork is cheaper *for tasks needing the same context*, but it inherits the **entire**
conversation, so for a small task from a large parent it is strictly more input tokens than a fresh 5k-prompt
subagent. Cheapness is conditional, not absolute.

**Every stated limitation** (enumerated, not guessed):

1. `:1053` — "**A fork can't spawn further forks.**"
2. `:1005` — "This **drops the input isolation** that subagents otherwise provide: a fork sees the same system
   prompt, tools, model, and message history as the main session."
3. `:1043` — model is **fixed to the main session's**; no per-fork model.
4. `:1002` — "Letting Claude itself spawn forks is **experimental and may change** in future releases."
5. `:1053` — `CLAUDE_CODE_FORK_SUBAGENT=0` "disables fork mode everywhere, **including any server-side rollout**."
6. `:863` — a fork at the depth limit **keeps `Agent` in its tool list but the tool returns an error** (a
   silent-looking failure mode: the tool is present and non-functional).
7. `:998` — `/subtask` requires v2.1.212+; when agent view is off, `/subtask` isn't available and `/fork` starts
   the forked subagent instead. Before v2.1.212 the command was `/fork`.
8. `:896` — an in-session `/subtask` fork **counts** against the 200 session cap; `:908` — it **takes a
   concurrency slot but is never blocked by** the concurrent limit.
9. `changelog.md` 2.1.220 — "Changed sessions forked with `/fork` to create a **new worktree of their own**
   instead of working in the original session's checkout."
10. `:1049` — when Claude spawns a fork via the Agent tool it may pass `isolation: "worktree"`.

Binary corroboration of the enablement precedence, verbatim:

```
function Ax_(){if(Ple())return"disabled";
if(tr(process.env.CLAUDE_CODE_FORK_SUBAGENT))return"env";
if($u(process.env.CLAUDE_CODE_FORK_SUBAGENT))return"disabled";
if(Sn())return"disabled";
if(Qe(wx_,!1))return"gb_rollout";return"disabled"}
```

Order: a hard disable wins, then the env var (truthy → `"env"`, falsy → `"disabled"`), then a second disable
condition, then a **server-side rollout gate** (`gb_rollout`), else disabled. So fork mode, like nesting depth,
is partly server-controlled when the env var is unset.

## Q7 — Foreground/background, the real caps, and what `CLAUDE_CODE_FORK_SUBAGENT` does to them

**Default is background** since v2.1.198 (`$CC/sub-agents.md:771`): "Claude runs a subagent in the foreground
when it needs the result before continuing. Background subagents run with a **smaller built-in tool set** than
foreground subagents, except for conversation forks, and they surface every permission prompt in your main
session."

`:773` — "A background subagent's results reach Claude as a **completion notification in a later turn**. Claude
waits for that notification before reporting the subagent's results." (Before v2.1.211 Claude sometimes
fabricated results for an unfinished background subagent.)

**`CLAUDE_CODE_FORK_SUBAGENT` — CONFIRMED, it removes the option.** `:784` verbatim:

> When `CLAUDE_CODE_FORK_SUBAGENT` is set to `1`, **every subagent runs in the background** and the frontmatter
> `background` field **has no effect**, because fork mode **removes the `run_in_background` parameter from the
> `Agent` tool**. `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` takes precedence over fork mode and keeps subagents in
> the foreground.

So there are two overrides and they compose: fork mode forces background; `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`
beats it and forces foreground.

**The caps, from the binary (authoritative over the docs):**

```
function U$u(){return te.CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS??cx_}
function Enn(){return te.CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION??ux_}
function q$u(){return te.CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION??dx_}
var xKe,pTo,Hpr,cx_=20,ux_=200,dx_=200,j$u,fTo;
```

| Limit | Default | Env var | On breach |
|---|---|---|---|
| Depth | **3** | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | throw `Subagent nesting limit reached (depth N of M).` |
| Per session | **200** | `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | throw `Subagent spawn limit reached (N of M agents spawned).` |
| Concurrent | **20** | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | throw `Concurrent subagent limit reached. You can run N subagents at once. Do not retry.` |
| Workflow concurrent | **16** (fewer on low-core machines) | — | `$CC/workflows.md` § Behavior and limits |
| Workflow per run | **1,000** | — | same |

Concurrency-check body, verbatim — note **two** bypasses:

```
H=()=>{let ut=U$u();if(l.taskRegistry.getConcurrentSubagents()<ut)return;
if(Qe("tengu_amber_kestrel",!1))return;
let Ve=l.getAppState();if(aX(l.rootToolSurface.mainLoopModel,Ve.effortValue,Ve.ultracode))return;
return me("subagent_launch","subagent_concurrency_cap"),new jHe(`Concurrent subagent limit reached...`)}
```

- `tengu_amber_kestrel` — **undocumented remote gate that disables the concurrency cap outright.**
  (Control: 0 hits across 174 doc pages, vs `subagent` → 87.)
- `aX(mainLoopModel, effortValue, ultracode)` — the documented ultracode exemption (`:904`).

Counting rules that bite a DAG (`:896`, `:906-911`):
- Nested subagents, forks, and background subagents **all count** toward the 200.
- `/subtask` counts; a `/fork` **background session does not** (separate budget).
- Workflow `agent()` spawns **don't** count (workflows have their own per-run limit) — but subagents that a
  workflow's agents spawn *with the Agent tool* **do**.
- A **finished subagent still counts.** `/clear` resets the count.
- **Resuming** a finished subagent "takes a fresh slot **without checking the limit**" — resumes can push the
  running count past the concurrency cap.
- Session-cap validation: unlike depth, the binary applies `??` to the raw env value with no visible integer
  validation at that site.

## Q8 — Subagent output scanning: can it reject a result?

**No. CONFIRMED it cannot reject.** `$CC/sub-agents.md:797-802` verbatim:

> Claude Code scans each subagent's final report before Claude reads it. … **The scan never removes or rewords
> anything**; it makes two kinds of change you may notice in a report:
> * **Backslash insertion**: … inserts a backslash into text that imitates Claude Code's own output, such as a
>   `<system-reminder>` tag or a line starting with `Human:` or `Assistant:` …
> * **Marker line**: … prepends a line starting with
>   `[harness: subagent output matched instruction-shaped pattern(s):` when the report imitates a tag like
>   `<system-reminder>` or mentions permission settings such as `bypassPermissions` or
>   `--dangerously-skip-permissions`. Permission-setting mentions get the marker line, but **the text itself
>   stays as written**.
> The scan **doesn't judge whether content is malicious**, and it doesn't change what an instruction in a report
> can do … It **isn't a substitute for restricting what a subagent can reach**.

Requires v2.1.210+ (`:805`). **Implication for a DAG:** there is no validation gate on an edge. A malformed or
schema-violating agent result is delivered as-is; any contract enforcement must be written by the orchestrator.

## Q9 — Changelog since v2.1.199 (enumerated by shape)

Method: sliced `changelog.md:11-645` (2.1.222 → 2.1.199, 635 lines), then grepped a broad shape
(`subagent|sub-agent|agent tool|fork|nest|spawn|SendMessage|TaskStop|resume|team|workflow|/subtask|/tasks|background agent|depth|concurren`)
rather than an anticipated list. Orchestration-relevant entries, verbatim:

**Nesting / limits — the defaults moved three times in ~20 releases:**
- 2.1.217: "Added a cap on concurrently-running subagents (default 20, override with `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`) so one message can't fan out unbounded background agents"
- 2.1.217: "Changed subagents to **no longer spawn nested subagents by default**; set `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to allow deeper nesting"
- 2.1.219: "Subagents can now spawn nested subagents **up to depth 3 by default (was 1)**; set `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` to disable nesting"
- 2.1.212: "Added a per-session cap on subagent spawns (default 200, override with `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`) to stop runaway delegation loops; `/clear` resets the budget"
- 2.1.217: "Fixed `--max-budget-usd` not stopping background subagents: once the cap is reached, new spawns are denied and running background agents are halted"

**Fork / `/subtask` rename:**
- 2.1.212: "`/fork` now copies your conversation into a **new background session** (its own row in `claude agents`) while you keep working; **the in-session subagent it used to launch is now `/subtask`**"
- 2.1.220: "Changed sessions forked with `/fork` to create a **new worktree of their own** instead of working in the original session's checkout"
- 2.1.212: "Changed `SessionStart` hooks to report source `\"fork\"` when a session begins as a fork instead of `\"resume\"`"
- 2.1.211: "Fixed fork-session lineage being lost after compaction in headless and SDK sessions"

**Observability of the tree (matters most for a DAG):**
- 2.1.220: "Added **nested subagent forwarding in stream-json**: subagents spawned at **depth-2+** now appear when `--forward-subagent-text` is set, **keyed by their spawning Agent `tool_use` id**"
- 2.1.211: "Added `--forward-subagent-text` flag and `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT` environment variable to include subagent text and thinking in stream-json output"
- 2.1.215: "Added reasoning effort to the `subagentStatusLine` payload"
- 2.1.202: "Added `workflow.run_id` and `workflow.name` OpenTelemetry attributes to telemetry emitted by workflow-spawned agents, so a workflow run's activity can be reconstructed from OTel data"

**Resume / SendMessage:**
- 2.1.222: "Fixed `SendMessage` rejecting a long summary — it now **truncates instead**, so sends no longer fail on a character limit"
- 2.1.222: "Improved auto mode safety: messages sent to other agent sessions via `SendMessage` are now **evaluated by the permission classifier before dispatch**"
- 2.1.199: "Fixed `SendMessage` silently misrouting when a re-spawned agent reuses a previous agent's name — the tool now detects the mismatch and asks the caller to retarget"
- 2.1.205: "Fixed background agents staying shown as \"failed\" or \"completed\" in the agent list after being resumed with `SendMessage`"
- 2.1.211: "Fixed subagents spawned with an explicit model override reverting to the parent's model when resumed or sent a follow-up message"
- 2.1.203: "Fixed `TaskStop` and `TaskOutput` failing to find background agents **spawned by another agent** — errors now list running agents by id and description"
- 2.1.204: "Fixed returning to `claude agents` silently stopping running subagents and re-running the prompt from scratch — their work now carries over"

**Permission / isolation semantics:**
- 2.1.211: "**Deprecated the Task tool's `mode` parameter (now ignored)**; subagents inherit the parent session's permission mode by default"
- 2.1.222: "Fixed worktree-isolated sessions and their subagents being able to run destructive git commands against the main checkout; isolation now applies to file edits and Bash in every session type"
- 2.1.217: "Fixed worktree-isolated subagents redirecting git into the shared checkout via `git -C`, `--git-dir`, or `GIT_DIR`/`GIT_WORK_TREE`"
- 2.1.222: "Fixed PreToolUse auto-allow hooks bypassing tool restrictions in background agent tasks"
- 2.1.207: "Hardened the Agent tool against indirect prompt injection via content a subagent read" (→ became output scanning in 2.1.210)

**Behavioural, worth knowing before designing a delegation policy:**
- 2.1.204: "Improved subagent behavior: agents are now **less likely to re-delegate their entire task to another subagent**"
- 2.1.219: "Changed `/code-review` to run as a background subagent"
- 2.1.220: "Changed dynamic workflows to default to a medium size guideline (**aim for fewer than 15 agents**)"
- 2.1.199: "Fixed subagents **reporting API errors (e.g. usage limit reached) as successful results**"
- 2.1.200: "Fixed subagents cut off by a rate limit **before producing any text** returning an empty result instead of failing cleanly"

## Verdict: can a DAG-shaped multi-agent pipeline with cross-session durability be built on subagents alone?

**No — and the blocker is durability, not shape.**

**The DAG shape is achievable, with caveats.** Fan-out of fan-out works: an unnamed subagent can spawn its own
subagents to **depth 3** by default, and a reviewer-dispatching-a-verifier-per-finding pattern is the docs' own
example (`:865`). Fan-in works by the orchestrator collecting results. Width is bounded at **20 concurrent /
200 per session**, both raisable. So a bounded DAG of ≤200 nodes, ≤3 deep, ≤20 wide is buildable **today**.

Four things constrain the shape, in descending severity:

1. **Edges are untyped free text.** There is no schema, artifact, or contract on a subagent boundary — the
   frontmatter table has 17 fields and none of them is an output schema, and output scanning explicitly
   *cannot reject* a result. Every edge is "the orchestrator reads prose and writes the next prompt." The only
   typed edge in the product is workflow `agent(prompt, {schema})`, which is out of scope here.
2. **Depth-2+ results are invisible to the orchestrator.** By design, only the top-level subagent's summary
   returns. A true DAG needs the orchestrator to route intermediate nodes' outputs — it cannot. The only escape
   is `--forward-subagent-text` in stream-json (2.1.220), which is *observation* by an external driver, not
   in-session routing.
3. **Named agents can't nest at all.** The moment you use `name` to get a stable, addressable handle, you get a
   **teammate** — "the team roster is flat", no fan-out, foreground-only children, one team per session, fixed
   lead. Addressability and fan-out are mutually exclusive on the same node.
4. **Two limits are server-controlled.** Nesting depth (`tengu_hazel_trellis`) and the concurrency-cap bypass
   (`tengu_amber_kestrel`) are remote feature-gate values read from a cache named `MAY_BE_STALE`, neither
   documented. A framework that assumes depth 3 without pinning `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` can have
   its topology changed underneath it by a server-side flag flip.

**What actually blocks it: there is no cross-session agent handle.** Subagent transcripts live at
`~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl` — the agent ID is **namespaced under
a session ID** (verified on disk: 2,077 transcripts, control-armed). Resume is `SendMessage(to: id|name)`, and
its name-identity check is explicitly "scoped to the current conversation and **resets on `/clear`**". The docs
state persistence as "within their session … by resuming the same session." Agent teams are strictly worse:
`/resume` **does not restore in-process teammates** at all. So:

- Restarting the CLI and running `claude --resume <sessionId>` preserves subagent handles. **That is the only
  durable path**, and it is durability of the *parent session*, not of the agents.
- A **different** session — a scheduled run, a CI job, a fresh terminal, a post-`/clear` continuation — cannot
  address any prior subagent. The graph dies with its parent conversation.
- Retention is 30 days (`cleanupPeriodDays`) even for the transcripts that do persist.

**The shape that does satisfy both requirements** is to make each durable DAG node a **background session**
rather than a subagent: `claude --bg` / `/fork` produce real sessions with their own row in `claude agents`,
their own budget (explicitly excluded from the 200 cap), a `claude attach` id, and `claude agents --json` for
scripted enumeration — plus `--json-schema` for a typed final result per node, which subagents do not have. That
moves orchestration outside the harness (an external driver spawning and joining sessions), using subagents only
*within* a node for context isolation. Alternatively, the **Workflow** runtime gives typed `agent(…, {schema})`
edges and `pipeline()` fan-out with 16-concurrent/1,000-per-run limits — but it is resumable only *within the
same session*, so it solves the typing problem and not the durability one.

**Summary:** subagents give you a DAG that is bounded, untyped at the edges, opaque below depth 1, and
**session-mortal**. Cross-session durability requires sessions, not subagents.

## Ledger entries to append

```
claim | verdict | evidence | version | date
Subagent nesting default is 3 layers below main | CONFIRMED | binary `var g$u=3`; $CC/sub-agents.md:863 | 2.1.222 | 2026-08-05
Nesting depth falls back to remote gate `tengu_hazel_trellis` (MAY_BE_STALE) when env var unset — UNDOCUMENTED | CONFIRMED | binary Jre(); 0 doc hits vs control `subagent`=87 files | 2.1.222 | 2026-08-05
Session subagent cap 200 / concurrent cap 20 / web-search cap 200 | CONFIRMED | binary `cx_=20,ux_=200,dx_=200` | 2.1.222 | 2026-08-05
Remote gate `tengu_amber_kestrel` disables the concurrency cap entirely — UNDOCUMENTED | CONFIRMED | binary concurrency-check body; 0 doc hits | 2.1.222 | 2026-08-05
At the depth limit the Agent tool is withheld; a fork keeps it but it errors | CONFIRMED | $CC/sub-agents.md:863 | 2.1.222 | 2026-08-05
Teammates cannot spawn teammates — "the team roster is flat" | CONFIRMED | binary `subagent_nested_teammate` string; $CC/agent-teams.md Limitations | 2.1.222 | 2026-08-05
In-process teammates cannot spawn background agents | CONFIRMED | binary `subagent_teammate_background_denied`; agent-teams.md | 2.1.222 | 2026-08-05
Passing `name` to the Agent tool makes a teammate, forfeiting fan-out | CONFIRMED | binary "To spawn a subagent instead, omit the `name` parameter" | 2.1.222 | 2026-08-05
No structured/typed output mechanism for subagents (17-field frontmatter has none) | REFUTED (that one exists) | $CC/sub-agents.md:276-294; shape-grep of all 174 pages | 2.1.222 | 2026-08-05
Workflow agent() DOES take a `schema` option — the only typed agent edge | CONFIRMED | $CC/workflows.md:289-291 | 2.1.222 | 2026-08-05
Chaining subagents is caller-relayed free text only | CONFIRMED | $CC/sub-agents.md:834-840 | 2.1.222 | 2026-08-05
Only the top-level subagent's summary returns; depth-2+ output never reaches main | CONFIRMED | $CC/sub-agents.md:865 | 2.1.222 | 2026-08-05
Depth-2+ subagents observable via --forward-subagent-text stream-json, keyed by parent tool_use id | CONFIRMED | changelog.md 2.1.220 | 2.1.222 | 2026-08-05
Subagent startup loads the FULL CLAUDE.md hierarchy; only Explore/Plan skip it, with no setting to change that | CONFIRMED | $CC/sub-agents.md:923,928 | 2.1.222 | 2026-08-05
Auto memory never reaches a non-fork subagent; needs its own `memory:` field | CONFIRMED | $CC/sub-agents.md:935 | 2.1.222 | 2026-08-05
Sibling roster is a snapshot at subagent start; later-named agents never appear | CONFIRMED | $CC/sub-agents.md:926 | 2.1.222 | 2026-08-05
Subagent resume is SendMessage(to: agentId|name); Explore/Plan return no ID and cannot resume | CONFIRMED | $CC/sub-agents.md:944,946 | 2.1.222 | 2026-08-05
SendMessage name-identity check is scoped to the current conversation and resets on /clear | CONFIRMED | $CC/sub-agents.md:964 | 2.1.222 | 2026-08-05
Resuming a subagent takes a fresh concurrency slot WITHOUT checking the limit | CONFIRMED | $CC/sub-agents.md:909 | 2.1.222 | 2026-08-05
Subagent transcripts are namespaced under sessionId — no cross-session handle | CONFIRMED | $CC/sub-agents.md:968,973; 2077 agent-*.jsonl on disk, control 0 | 2.1.222 | 2026-08-05
Agent teams do NOT survive /resume — in-process teammates are not restored | CONFIRMED | $CC/agent-teams.md Limitations | 2.1.222 | 2026-08-05
A /fork background session does NOT count toward the 200 session cap | CONFIRMED | $CC/sub-agents.md:896 | 2.1.222 | 2026-08-05
Forks share the parent prompt cache; named subagents get a separate one | CONFIRMED | $CC/sub-agents.md:1045,1047 | 2.1.222 | 2026-08-05
Docs give NO quantification of fork cache savings | CONFIRMED (absence) | shape-grep of sub-agents.md fork sections | 2.1.222 | 2026-08-05
A fork cannot spawn further forks | CONFIRMED | $CC/sub-agents.md:1053 | 2.1.222 | 2026-08-05
CLAUDE_CODE_FORK_SUBAGENT=1 removes run_in_background from the Agent tool; DISABLE_BACKGROUND_TASKS overrides it | CONFIRMED | $CC/sub-agents.md:784 | 2.1.222 | 2026-08-05
Fork enablement falls back to a server-side rollout gate when env var unset | CONFIRMED | binary Ax_() precedence chain | 2.1.222 | 2026-08-05
Subagent output scanning never removes or rewords and cannot reject a result | CONFIRMED | $CC/sub-agents.md:797-802 | 2.1.222 | 2026-08-05
CLAUDE_AUTOCOMPACT_PCT_OVERRIDE applies to subagents but can only LOWER the threshold | CONFIRMED | $CC/sub-agents.md:978; $CC/env-vars.md:189 | 2.1.222 | 2026-08-05
What survives a subagent's OWN compaction is unstated | NEEDS-PROBE | no doc anchor beyond "same logic as main" | 2.1.222 | 2026-08-05
Workflow runtime caps: 16 concurrent agents, 1000 per run | CONFIRMED | $CC/workflows.md Behavior and limits | 2.1.222 | 2026-08-05
Task tool `mode` parameter deprecated and ignored since 2.1.211 | CONFIRMED | changelog.md 2.1.211 | 2.1.222 | 2026-08-05
SendUserMessage: 0 hits across all 174 doc pages (docs incomplete) | CONFIRMED | grep control: `subagent`=87 files, invented token=0 | 2.1.222 | 2026-08-05
Undocumented subagent env vars exist (ENABLE_APPEND_SUBAGENT_PROMPT, SUBAGENT_CACHE_EVICT, SUBAGENT_MODEL, ...) | NEEDS-PROBE | binary shape-scan of CLAUDE_*/ANTHROPIC_* (615 distinct) | 2.1.222 | 2026-08-05
DAG-shaped pipeline with cross-session durability on subagents alone | REFUTED | session-namespaced agent IDs + no cross-session handle | 2.1.222 | 2026-08-05
```

## GitHub repos touched

_None._ All corpora were local: the installed Claude Code binary
(`~/.local/share/claude/versions/2.1.222`), its `--help` surface, the offline vendor doc tree
(`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`), and the local
transcript store (`~/.claude/projects/`). No repository source or remote host was consulted.
