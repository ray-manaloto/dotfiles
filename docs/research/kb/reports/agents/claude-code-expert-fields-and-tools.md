# Claude Code subagent configuration surface — 2.1.222

- Version under test: **2.1.222** (`/Users/rmanaloto/.local/share/claude/versions/2.1.222`, 271,289,792 bytes)
- Docs corpus: `$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code` (**174** `.md` files — the brief said 175; `ls | wc -l` counts 175 entries, `glob *.md` returns 174)
- Date: 2026-08-05

STATUS: COMPLETE.

## Findings table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| F1 | CONFIRMED | `$CC/sub-agents.md` § Supported frontmatter fields documents **exactly 16** fields | corpus 3, row-shape scan; control = 18 pipe rows, 2 unmatched (header+separator) |
| F2 | REFUTED | "sixteen fields" is the complete list — the binary parses **19** file-frontmatter fields (`observer`, `observerMessage`, `observeSubagents` undocumented) | corpus 1 zod `cVu` + file parser; control `zzqwvfrx-nope`→0 vs `AskUserQuestion`→18 files |
| F3 | REFUTED | `isolation` only accepts `worktree` — binary enum is `["worktree","remote"]` | corpus 1 @243821330 |
| F4 | CONFIRMED | Exactly **3** frontmatter rows carry "Ignored for plugin subagents" | corpus 3, qualifier-shape sweep over all 16 rows |
| F5 | CONFIRMED-with-correction | `plugins-reference.md:74` lists 11 plugin fields; `color` and `initialPrompt` are omitted there but not marked ignored in `sub-agents.md` | corpora 3+1 |
| F6 | REFUTED | The always-removed tool list is 9 items — the real set is **11** (`ConnectGitHub`, `propose_skills`, `RefreshMcpTools` undocumented) | corpus 1 `ax_`/`grb`, all vars resolved to string literals |
| F6b | REFUTED | The background keep-list is 19 tools — real set is **25** (adds `StructuredOutput`, `REPL`, `SearchPlugins`, `SearchSkills`, `ListPlugins`, `ListSkills`) | corpus 1 `lx_` |
| F7 | CONFIRMED | MCP tools bypass **both** subagent filters | corpus 1: `AH(a)` is the first predicate in `grb` |
| F8 | CONFIRMED | `AskUserQuestion` is genuinely absent from every subagent, unconditionally; `--brief`/`SendUserMessage` does **not** restore the ability to ask | corpora 1+2+3 |
| F8b | NEW | `SendUserMessage` survives filter 1 but **not** filter 2 — a background subagent (the default since v2.1.198) loses it; only a foreground subagent gets it | corpus 1: `CU` in neither `xKe` nor `Hpr` |
| F9 | CONFIRMED | Spawn depth default **3**, concurrent **20**, per-session **200** | corpus 1 `Jre`/`U$u`/`Enn` |
| F10 | REFUTED | "a teammate can reference a subagent from project, user, **plugin**, or CLI scope" — `win()` rejects plugin- and built-in-sourced definitions silently | corpus 1 @249122521 vs corpus 3 `agent-teams.md` |
| F10b | NEW | A teammate honours only **body + `tools` + `model`**; `permissionMode` is overwritten with `"default"`, `memory` is telemetry-only, 10 fields are dropped | corpus 1 `Rgb` definition object `D` |
| F11 | NEW | `memory:` silently force-adds **Write, Edit, Read** to an explicit `tools:` allowlist | corpus 1, both parsers; partially implied by `sub-agents.md:523` |
| F12 | NEW | Agent-source precedence: built-in < plugin < user < project(addl dir) < project < flagSettings < policySettings | corpus 1 `sht()` |
| F13 | REFUTED | `--agents` JSON accepts `color` — it is not in the schema and is silently stripped | corpus 1; control = the *file* parser's colour handler, which the same probe found |
| F14 | REFUTED | "7 CLI flags exist that `cli-reference.md` never mentions" — measures as **2** (via `--help`) or **62** (via binary registrations); never 7 | corpora 1+2+3; control `--model`✓ / `--qqzzvv`✗ |
| F15 | CONFIRMED | `skills:` injects full skill content at startup; cannot preload `disable-model-invocation: true` skills incl. bundled `/verify` and `/code-review`; missing skills are skipped with a debug-log warning only | corpus 3 |
| F16 | CONFIRMED | `SubagentStart` **cannot** block; `SubagentStop` **can** (`decision:"block"` re-instructs the subagent) | corpus 3 `hooks.md:785,796,947,2128,2170` |
| F17 | CONFIRMED | `Agent(type,...)` allowlist works **only** for `--agent` main-thread agents; ignored inside subagent definitions | corpus 3 `sub-agents.md:399` + corpus 1 |
| F18 | CONFIRMED | Packaging a team of agents as a plugin is **not viable** when they need per-agent hooks or MCP servers | corpora 1+3 |

## F1 — the documented 16 fields (enumerated by row shape)

Probe: match `^\|\s*` + backticked name + `\|\s*(Yes|No)\s*\|` inside the section
bounded by `#### Supported frontmatter fields` (L272) and the next `^#{1,4} ` heading (L294).

Control arm: the same scan reports **ALL PIPE ROWS: 18**, of which 2 are unmatched
(L276 header `| Field | Required | Description |`, L277 separator). So the shape
match captured every data row and rejected exactly the two non-rows.

```
(278, 'name', 'Yes')          (286, 'mcpServers', 'No')
(279, 'description', 'Yes')   (287, 'hooks', 'No')
(280, 'tools', 'No')          (288, 'memory', 'No')
(281, 'disallowedTools', 'No')(289, 'background', 'No')
(282, 'model', 'No')          (290, 'effort', 'No')
(283, 'permissionMode', 'No') (291, 'isolation', 'No')
(284, 'maxTurns', 'No')       (292, 'color', 'No')
(285, 'skills', 'No')         (293, 'initialPrompt', 'No')
ROW COUNT: 16
```

Enum VALUES are inside the Description column, never in the field column, so the
row-shape match cannot conflate `permissionMode` with `acceptEdits`/`plan`/`auto`.

## F2 — the binary parses 19 frontmatter fields; 3 are undocumented

`$CC` grep for `observer` / `observeSubagents` — see F2b below.

Binary zod schema (offset 243820500-243821600), the programmatic agent-definition
object `cVu`, verbatim:

```
cVu=Te(()=>E.object({description:E.string().min(1,"Description cannot be empty"),
tools:E.array(E.string()).optional(),disallowedTools:E.array(E.string()).optional(),
prompt:E.string().min(1,"Prompt cannot be empty"),
model:E.string().trim().min(1,"Model cannot be empty").transform((e)=>e.toLowerCase()==="inherit"?"inherit":e).optional(),
effort:E.union([E.enum(lH),E.number().int()]).optional(),
permissionMode:E.preprocess(rH,E.enum(FW)).optional(),
mcpServers:E.array(lVu()).optional(),
hooks:hae().optional(),
maxTurns:E.number().int().positive().optional(),
skills:E.array(E.string()).optional(),
initialPrompt:E.string().optional(),
memory:E.enum(["user","project","local"]).optional(),
background:E.boolean().optional(),
isolation:E.enum(["worktree","remote"]).optional(),
observer:E.string().optional().transform(...),
observerMessage:E.string().optional().transform(...),
observeSubagents:E.boolean().optional()}))
```

The markdown-file parser (offset ~243819100-243820000) reads the same names off the
frontmatter object `r` and additionally handles `color`:

```
let j=r.observer,V=typeof j==="string"&&j.trim()?j.trim():void 0,
K=r.observerMessage,q=typeof K==="string"&&K.trim()?K:void 0,
U=r.observeSubagents,F=...
...a&&typeof a==="string"&&mA.includes(a)&&{color:a}
```

So: **file frontmatter = the documented 16 + `observer` + `observerMessage` +
`observeSubagents` = 19.** `color` exists only on the file path (not in `cVu`);
`prompt` exists only on the programmatic path (the markdown body replaces it).

`initialPrompt`'s binary describe string is stricter than the docs row:
`"Auto-submitted first message when this agent runs as the main session (via
--agent or settings). Not read when spawned as a subagent."`

## F3 — `isolation` accepts `remote`

`isolation:E.enum(["worktree","remote"])`. `$CC/sub-agents.md:291` documents only
`worktree`; `plugins-reference.md:74` states "The only valid `isolation` value is
`"worktree"`" — true for plugin agents at most, false for the schema.

## F4 — plugin-ignored rows, enumerated by shape

Regex sweep of every row's Description for `Ignored for [^.]*` plus version and
default qualifiers:

```
L278 name             Yes :: Before v2.1.218, such names were accepted
L282 model            No  :: Defaults to `inherit`
L283 permissionMode   No  :: Ignored for [plugin subagents]; requires Claude Code v2.1.200 or later
L286 mcpServers       No  :: Ignored for [plugin subagents]
L287 hooks            No  :: Ignored for [plugin subagents]
L289 background       No  :: as of v2.1.198 it runs subagents in the background by default
L290 effort           No  :: Default: inherits from session
L293 initialPrompt    No  :: when this agent runs as the main session agent (via `--agent` or the `agent` setting)
```

Exactly 3 "Ignored for plugin subagents". No other row carries a mode qualifier
except `initialPrompt`, which is main-session-only.

## F5 — plugins-reference disagrees with sub-agents on plugin field support

`$CC/plugins-reference.md:74` verbatim:

> Plugin agents support `name`, `description`, `model`, `effort`, `maxTurns`,
> `tools`, `disallowedTools`, `skills`, `memory`, `background`, and `isolation`
> frontmatter fields. The only valid `isolation` value is `"worktree"`. For
> security reasons, `hooks`, `mcpServers`, and `permissionMode` are not supported
> for plugin-shipped agents.

That is 11 named + 3 excluded = 14. The 16-row table minus the 3 ignored = 13,
so `color` and `initialPrompt` are unaccounted for in the plugin list. NEEDS-PROBE
against the binary.

## F2b — `observer` / `observerMessage` / `observeSubagents` have ZERO doc coverage

```
docs-files-containing 'observeSubagents': 0
docs-files-containing 'observerMessage': 0
docs-files-containing 'observer:': 0
docs-files-containing 'SendUserMessage': 0
docs-files-containing 'zzqwvfrx-nope': 0      <- fresh known-absent control
docs-files-containing 'AskUserQuestion': 18   <- known-present control
```

Probe discriminates in both directions. `grep -rnF observer $CC/` returns **nothing**
(not even a substring hit), so the absence is not a spelling artefact.

## F6 — the two tool filters, resolved from the binary

The authoritative filter is `grb(...)` at binary offset **247674663**, verbatim:

```js
function grb({tools:e,isBuiltIn:t,isAsync:r=!1,isTeammate:n=!1,permissionMode:o,agentDepth:i=0}){
  let s=e.filter((a)=>{
    if(AH(a))return!0;                       // MCP tool -> bypasses EVERY filter
    if(rl(a,HL)&&o==="plan")return!0;        // ExitPlanMode kept iff permissionMode==="plan"
    if(xKe.has(a.name))return!1;             // ALL_AGENT_DISALLOWED_TOOLS
    if(!t&&pTo.has(a.name))return!1;         // CUSTOM_AGENT_DISALLOWED_TOOLS (non-built-in agents)
    if(rl(a,ri))return i<Jre();              // Agent: only below the depth limit
    if(r&&!Hpr.has(a.name)){                 // background/async: keep-list only
      if(Vc()&&n&&j$u.has(a.name))return!0;  // teammate extras
      return!1;
    }
    return!0;
  });
  if(o==="plan"&&!s.some((a)=>rl(a,HL)))s.push(Nj);
  return s;
}
```

Exported set names (offset 249851955):
`ALL_AGENT_DISALLOWED_TOOLS:()=>xKe`, `CUSTOM_AGENT_DISALLOWED_TOOLS:()=>pTo`,
`ASYNC_AGENT_ALLOWED_TOOLS:()=>Hpr`, `COORDINATOR_MODE_ALLOWED_TOOLS:()=>fTo`,
`REPL_ONLY_TOOLS:()=>gLt`.

Bindings (offset 241598450):

```js
xKe=ax_("external"), pTo=new Set([...xKe]);
Hpr=lx_("external");
j$u=new Set([s9,NUe,$G,w7,Qf,SR,BU,Uft]), fTo=new Set([ri,_$,Qf,f_,Bx])
```

### Filter 1 — `ALL_AGENT_DISALLOWED_TOOLS` (`ax_`)

```js
function ax_(e){return new Set([Xre,HL,Ale,bm,Cpr,CKe,qft,mhe, ...e!=="ant"?[Bx]:[], M_,qU])}
```

| var | tool | in `$CC/sub-agents.md:325-335`? |
|---|---|---|
| `Xre` | `TaskOutput` | yes (L333) |
| `HL` | `ExitPlanMode` | yes (L331) |
| `Ale` | `EnterPlanMode` | yes (L330) |
| `bm` | `AskUserQuestion` | yes (L328) |
| `Cpr` | **`ConnectGitHub`** | **NO — undocumented** |
| `CKe` | **`propose_skills`** | **NO — undocumented** |
| `qft` | `WaitForMcpServers` | yes (L334) |
| `mhe` | **`RefreshMcpTools`** | **NO — undocumented** |
| `Bx` | `Workflow` | yes (L335) — but **only when the build flavour is not `"ant"`** |
| `M_` | `ScheduleWakeup` | yes (L332) |
| `qU` | `EndConversation` | yes (L329) |

`Agent` (`ri`) is not in this set; it is the separate `agentDepth < Jre()` branch.
Docs list 9 items; the real set is **11** (10 for `"ant"` builds, where `Workflow`
moves into the background keep-list instead).

`pTo` is currently `new Set([...xKe])` — content-identical, and the `xKe` test runs
first, so the `isBuiltIn` distinction is presently a **no-op**. It is nonetheless a
real code path: a future divergence would apply only to non-built-in agents.

### Filter 2 — `ASYNC_AGENT_ALLOWED_TOOLS` (`lx_`), the background keep-list

```js
function lx_(e){return new Set([ys,NX,lj,np,h0,dp,...pre,Ol,uu,u0,dg,f_,Aw,Yre,kpr,D_,Rw,_$,Qf,
                                ...e==="ant"?[Bx]:[], OO, ...sTo])}
```

Resolved (`pre=[fi,bs]`, `sTo=["SearchPlugins","SearchSkills","ListPlugins","ListSkills"]`):

`Read, WebSearch, TodoWrite, Grep, WebFetch, Glob, Bash, PowerShell, Edit, Write,
NotebookEdit, Skill, StructuredOutput, ToolSearch, EnterWorktree, ExitWorktree, REPL,
Monitor, TaskStop, SendMessage, [Workflow if "ant"], Artifact, SearchPlugins,
SearchSkills, ListPlugins, ListSkills`

= **25** for external builds (26 counting `Workflow` on `"ant"`). The doc (L337) lists
19 and omits: **`StructuredOutput`, `REPL`, `SearchPlugins`, `SearchSkills`,
`ListPlugins`, `ListSkills`**. (`SearchPlugins`/`SearchSkills`/`ListPlugins`/`ListSkills`
are further gated by `isPluginSkillToolAdvertised`.)

### Teammate extras — `j$u`

`TaskCreate, TaskGet, TaskList, TaskUpdate, SendMessage, CronCreate, CronDelete, CronList`
= 8. Doc L339 lists 7 and omits `SendMessage` — which is harmless there only because
`SendMessage` is already in the background keep-list. Gated by `Vc()` =
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env **and** the `tengu_amber_flint` gate.

### Coordinator mode — `fTo` (undocumented)

`COORDINATOR_MODE_ALLOWED_TOOLS = {Agent, TaskStop, SendMessage, StructuredOutput, Workflow}`,
gated by `CLAUDE_CODE_COORDINATOR_MODE`. Zero doc hits for `COORDINATOR_MODE`.

### `REPL_ONLY_TOOLS` — `gLt = new Set([Read, Glob, Grep, Bash, PowerShell, NotebookEdit])`

## F7 — MCP tools bypass BOTH filters

`AH(e){return e.name?.startsWith("mcp__")||e.isMcp===!0}` is the **first** predicate in
`grb`, returning `true` unconditionally. So `tools:`/`disallowedTools:` still shape the
pool upstream, but neither subagent filter can remove an MCP tool. This matches the doc's
"a background subagent keeps every MCP tool" and extends it: filter 1 cannot remove MCP
tools either.

## F8 — `AskUserQuestion` is absent unconditionally; `--brief`/`SendUserMessage` does NOT restore it

`AskUserQuestion` (`bm`) sits in `ALL_AGENT_DISALLOWED_TOOLS` with no conditional
whatsoever — no permissionMode escape (unlike `ExitPlanMode`), no depth escape (unlike
`Agent`), no build-flavour escape (unlike `Workflow`). **CONFIRMED absent for every
subagent, teammate, plugin agent and background agent.** Forks are the sole exception:
`$CC/sub-agents.md:325` — "Forks skip both filters and receive the main conversation's
exact tool pool."

`SendUserMessage` is a **different tool** and is **not in either disallowed set**:

```js
$0p=ms({name:CU,aliases:[QXr],searchHint:"send a message to the user — your primary
visible output channel",briefStandalone:!0,...,isEnabled(){return z3t()||ayt()},...})
var CU="SendUserMessage",QXr="Brief"   // alias map: Brief:"SendUserMessage"
```

Gates:

```js
function z3t(){return hfe()&&rfn()||XUs()}                 // isBriefEnabled
function rfn(){return te.CLAUDE_CODE_BRIEF||hEe("tengu_kairos_brief",!1,T_y)}  // isBriefEntitled
function ayt(){if(te.CLAUDE_CODE_PEWTER_OWL_TOOL!==void 0)return te.CLAUDE_CODE_PEWTER_OWL_TOOL;
               return zId("pewter_owl_tool")}
```

CLI (offset 260891460): `new Rd("--brief","Enable SendUserMessage tool for agent-to-user communication")`

So the accurate statement is:

- `AskUserQuestion` — the tool that **asks the user a question and blocks on the answer** —
  is removed from every subagent, always. There is no flag that brings it back.
- `SendUserMessage` — **one-way agent→user output**, no answer — is session-gated by
  `--brief` / `CLAUDE_CODE_BRIEF` / `CLAUDE_CODE_PEWTER_OWL_TOOL`, and when enabled it
  survives filter 1. It does **not** survive filter 2: `CU` is absent from
  `ASYNC_AGENT_ALLOWED_TOOLS`, so a **background** subagent loses it. Since v2.1.198
  subagents run in the background by default, the practical answer is that a subagent
  gets `SendUserMessage` only when it runs in the **foreground**.
- `--brief` therefore does not give a subagent a way to *ask*; it gives a foreground
  subagent a way to *tell*.

Refusal strings (offset 244416572), verbatim:

```
`. ${e} is not available inside subagents. Complete the task with the tools provided and
 return findings to the orchestrator.`
`. ${e} is not enabled in this session — write your message as normal assistant text instead.`
```

The first fires for `xKe` members (AskUserQuestion), the second for `CU` when brief is off.

Workflow subagents are told the opposite (offset 249204970):
`"Do NOT use SendUserMessage to deliver your answer. Put your answer in your final text response."`

## F9 — spawn-depth and concurrency constants

```js
function Jre(){let e=te.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH; ... }  var g$u=3
function U$u(){return te.CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS??cx_}   var cx_=20
function Enn(){return te.CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION??ux_}  var ux_=200
function q$u(){return te.CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION??dx_} var dx_=200
```

Default spawn depth **3**, concurrent **20**, per-session **200**.

## F10 — TEAMMATE mode honours only 3 of the 19 fields (undocumented)

Two gates, both in the binary, neither in the docs.

### Gate 1 — a built-in or plugin agent CANNOT be a teammate

`win(e){return e.source!=="built-in"&&e.source!=="plugin"}` (offset 242398358).
In the in-process teammate spawn path (offset 249122521):

```js
let h;if(s){let R=t.options.agentDefinitions.activeAgents.find((P)=>P.agentType===s);
  if(R&&win(R))h=R;
  C(`[handleSpawnInProcess] agent_type=${s}, found=${!!h}`)}
```

If the named `agent_type` resolves to a **built-in** or **plugin** agent, `h` stays
`undefined` and the teammate spawns with **no definition at all** — silently, with only
a debug-log line. The same guard is in the teammate *resume* path (offset 249447289),
where a miss sets `l="agent_type_unresolved"` and substitutes a stub
`{agentType, whenToUse:"", tools:[], getSystemPrompt:()=>"", source:"projectSettings"}`.

### Gate 2 — the synthesized teammate definition drops nearly everything

`Rgb` (in-process teammate runner) builds its own definition `D` from the resolved
definition `i`, verbatim:

```js
let D={agentType:t.agentName,
       whenToUse:`In-process teammate: ${t.agentName}`,
       getSystemPrompt:()=>O,
       tools:i?.tools?yo([...i.tools,Qf,s9,NUe,$G,w7]):["*"],
       source:"projectSettings",
       permissionMode:"default",
       ...i?.model&&{model:i.model}},
```

and the system prompt is assembled as:

```js
if(i){let X=i.getSystemPrompt();if(X)B.push(`\n# Custom Agent Instructions\n${X}`);
      if(i.memory)N("tengu_agent_memory_loaded",{...!1,scope:ge(i.memory),source:we("in-process-teammate")})}
```

| Field | Teammate behaviour |
|---|---|
| body / system prompt | **honoured** — appended under `# Custom Agent Instructions` |
| `tools` | **honoured**, force-unioned with `SendMessage, TaskCreate, TaskGet, TaskList, TaskUpdate`; absent ⇒ `["*"]` |
| `model` | **honoured** |
| `memory` | **telemetry only** — `tengu_agent_memory_loaded` is emitted and nothing is loaded |
| `permissionMode` | **overwritten** with `"default"` |
| `disallowedTools`, `skills`, `mcpServers`, `hooks`, `maxTurns`, `effort`, `background`, `isolation`, `initialPrompt`, `observer*` | **dropped** — not read anywhere in `D` |
| `color` | comes from the team colour assignment (`t.color`), not the field |
| `source` | forced to `"projectSettings"` |

The registry entry's mode is `e.permissionMode??kgb(hn(t).mode,s)` where
`kgb(e,t){if(t)return"plan";if(e==="plan"||e==="dontAsk")return"default";return e}` —
so a teammate can never run in `dontAsk`.

## F11 — `memory:` silently widens a `tools:` allowlist with Write, Edit, Read

Both parsers do this (`pVu`, programmatic; and the markdown parser at 243819107):

```js
if(Mm()&&n.memory&&o!==void 0){let l=new Set(o);for(let c of[uu,Ol,ys])if(!l.has(c))o=[...o,c]}
```

`uu=Write, Ol=Edit, ys=Read`. Declaring `memory:` on an agent with an explicit `tools:`
allowlist grants it **Write, Edit and Read** whether or not they were listed. Zero doc
coverage (`grep -c "memory" ` on `$CC/sub-agents.md` § Enable persistent memory says
nothing about tools).

## F12 — agent-source precedence (last write wins)

`sht(e)` (offset 242399155) partitions by `source` and merges into one Map in this order,
later overwriting earlier:

```js
let t=...==="built-in", r=...==="plugin", n=...==="userSettings",
    i=[...projectSettings&&fromAdditionalDirectory, ...projectSettings&&!fromAdditionalDirectory],
    s=...==="policySettings", a=...==="flagSettings",
    l=[t,r,n,i,a,s],c=new Map;
for(let u of l)for(let d of u)c.set(d.agentType,d);
```

Effective precedence, lowest → highest:
**built-in < plugin < userSettings < projectSettings(additional dir) <
projectSettings(main) < flagSettings < policySettings**.

A plugin agent is overridden by any user or project agent of the same name, and
`policySettings` (managed policy) wins outright.

## F13 — `--agents` JSON does NOT support `color` (docs say it does)

`$CC/sub-agents.md:223` verbatim:

> The `--agents` flag accepts JSON with the same frontmatter fields as file-based
> subagents: `description`, `prompt`, `tools`, `disallowedTools`, `model`,
> `permissionMode`, `mcpServers`, `hooks`, `maxTurns`, `skills`, `initialPrompt`,
> `memory`, `effort`, `background`, `isolation`, and `color`.

The `--agents` path parses through `pVu(e,t,r="flagSettings")` → `cVu().parse(t)`.
`cVu` (F2) has **no `color` key**, and `pVu`'s returned object spreads
`model, effort, permissionMode, mcpServers, hooks, maxTurns, skills, initialPrompt,
background, memory, isolation, observer, observerMessage, observeSubagents` — no `color`.
Zod `.object()` strips unknown keys, so `color` is silently dropped.

Control arm: the **markdown-file** parser *does* handle colour
(`...a&&typeof a==="string"&&mA.includes(a)&&{color:a}`), so the probe can see a `color`
handler when one exists — it found one on the file path and none on the JSON path.

Conversely `--agents` JSON **does** accept the three undocumented `observer*` fields.

## F14 — undocumented CLI flags: the "7" figure does not reproduce

Two measurements, both control-armed (`--model` present, `--qqzzvv` absent):

| method | result |
|---|---|
| flags in `claude --help` (62) not in `cli-reference.md` | **2**: `--brief`, `--file` |
| flags registered in the binary (145) not in `cli-reference.md` | **62** |
| flags registered in the binary not shown by `--help` (i.e. `hideHelp()`) | **87** |

The binary-registration set includes subcommand flags (`claude agents`, `claude plugin`,
`claude setup-token`), so 62 overstates "CLI flags" as `cli-reference.md` scopes them.
Neither number is 7. Subagent-relevant flags registered but absent from `--help`:
`--agent-type`, `--agent-name`, `--agent-color`, `--agent-id`, `--team-name`,
`--teammate-mode`, `--plan-mode-required`, `--plan-mode-instructions`,
`--parent-session-id`, `--task-budget`, `--max-turns`, `--append-subagent-system-prompt`
(the last is documented in `sub-agents.md:262` but hidden from help).

`--brief` in `--help`, verbatim:

```
  --brief                               Enable SendUserMessage tool for
                                        agent-to-user communication
```

## F15 — `skills:` preload (Q4)

`$CC/sub-agents.md:468-492`. Mechanism: the **full content** of each named skill is
injected into the subagent's context at startup, not just the description (L285, L484).

Stated limits, verbatim:

- L484: "This field controls which skills are preloaded, not which skills the subagent
  can access: without it, the subagent can still discover and invoke project, user, and
  plugin skills through the Skill tool during execution. To prevent a subagent from
  invoking skills entirely, omit `Skill` from the `tools` list or add it to
  `disallowedTools`."
- L486: "You can't preload skills that set `disable-model-invocation: true`, since
  preloading draws from the same set of skills Claude can invoke. **This includes the
  bundled `/verify` and `/code-review` skills**: only you can run them, so they can't be
  preloaded either."
- L488: "If a listed skill is missing or disabled, Claude Code skips it and logs a
  warning to the debug log." — a silent-by-default failure.
- L280: "To preload Skills into context, use the `skills` field rather than listing
  `Skill` here."
- L491: inverse of `context: fork` in a skill; same underlying system.

⚠️ **`skills:` is dropped on the teammate path** — F10, and `$CC/agent-teams.md`
§ Use subagent definitions for teammates confirms it.

## F16 — hooks (Q5)

**Frontmatter hooks** (`$CC/sub-agents.md:616-656`):

- Run only while that subagent is active; cleaned up when it finishes (L618).
- Fire both when spawned via the Agent tool / @-mention **and** when the agent is the
  main session via `--agent` or the `agent` setting; in the latter case alongside
  `settings.json` hooks (L621).
- **Workspace trust gate** (L624-626): a *project*-level subagent's frontmatter hooks
  need the workspace-trust dialog accepted for the containing folder. User-level
  (`~/.claude/agents/`) and `--agents` definitions run without it. `--add-dir` folders
  outside the trusted repo need separate trust. Untrusted ⇒ the subagent still runs, the
  hooks are **skipped**, and an error goes to the debug log. Before v2.1.218 they ran
  untrusted.
- All hook events supported; `Stop` in frontmatter is auto-converted to `SubagentStop`
  (L634, L656).

**Project-level subagent-lifecycle hooks** (`$CC/sub-agents.md:658-694`):

| Event | Matcher input | Can it block? |
|---|---|---|
| `SubagentStart` | agent type name | **NO** — `$CC/hooks.md:796` "No / Shows stderr to user only"; `:2128` "SubagentStart hooks can't block subagent creation, but they can inject context"; `:947` "No blocking or decision control" |
| `SubagentStop` | agent type name | **YES** — `$CC/hooks.md:785` "Prevents the subagent from stopping"; `:2170` `decision:"block"` + `reason` "keeps the subagent running and delivers `reason` to the subagent as its next instruction" |

Matcher value = the frontmatter `name`, or the **plugin-scoped** identifier
(`my-plugin:db-agent`) for plugin agents. A scoped name contains `:` so it is an
**unanchored regex** — anchor it (`^my-plugin:db-agent$`). A hyphenated matcher like
`db-agent` matches exactly only on v2.1.195+ (L667, L693).

`$CC/hooks.md:812` — for `SubagentStart`, exit-code-2 stderr renders in the **subagent's
own** transcript, not the parent's, and Claude does not see it.

`$CC/hooks.md:2170` — to inject context into the **parent** after a subagent returns,
use a `PostToolUse` hook on the `Agent` tool, not `SubagentStop`.

`$CC/sub-agents.md:614` — hooks from settings files, managed policy settings **and
plugins** all apply inside subagents.

## F17 — restrict / disable / scope MCP (Q6)

| Mechanism | Config location | Semantics |
|---|---|---|
| **Restrict which subagents can be spawned** | the spawning agent's `tools:` frontmatter | `Agent(worker, researcher)` = allowlist. `$CC/sub-agents.md:399`: applies **only** to an agent running as the main thread via `claude --agent`; inside a subagent definition the parenthesised type list is **ignored** and bare `Agent` merely permits spawning. Omitting `Agent` entirely blocks all spawning. Binary: `if(n!==ri\|\|!o)return null; ... return t?{allowedAgentTypes:t}:{}` at offset 247674663 — parsed only from `Agent(...)` rules. |
| **Disable specific subagents** | `permissions.deny` in settings, or `--disallowedTools` | `"deny": ["Agent(Explore)","Agent(my-custom-agent)"]` (L589-603). Works for built-in and custom. Denylist complement of the above. |
| **Scope MCP servers to a subagent** | `mcpServers:` frontmatter | Entries are inline definitions **or** string references. Inline: connected at subagent start, disconnected at finish, `stdio`/`http`/`sse`/`ws`, same schema as `.mcp.json`. String: shares the parent session's connection. L435: defining inline keeps the server's tool descriptions out of the **main** conversation's context. L437-445: `--strict-mcp-config`, `--bare`, enterprise managed MCP, and `allowedMcpServers`/`deniedMcpServers` all apply to frontmatter servers as of v2.1.153; managed settings apply to every subagent; `--strict-mcp-config` does **not** filter servers passed inline via `--agents`/SDK. Binary also rejects reserved server names and the internal `sse-ide`/`ws-ide` transports with a warning (offset 242398395). |

## F18 — subagent scope + plugin packaging (Q7)

Documented priority (`$CC/sub-agents.md:161-167`): managed settings (1) > `--agents` (2)
> `.claude/agents/` (3) > `~/.claude/agents/` (4) > plugin `agents/` (5, lowest).
Binary `sht()` (F12) agrees and adds `flagSettings` and `policySettings` above project.

**What packaging as a plugin gains:** distribution and versioning via a marketplace;
recursive `agents/` scanning where a subfolder becomes part of the scoped id
(`agents/review/security.md` → `my-plugin:review:security`, L181); @-mention typeahead
under the scoped name.

**What it loses:**

1. `hooks`, `mcpServers`, `permissionMode` are **ignored** — "For security reasons"
   (L229-231, `plugins-reference.md:74`). The escape hatch the docs give is copying the
   file into `.claude/agents/` or `~/.claude/agents/`, or session-wide
   `permissions.allow` rules that are *not* scoped to the agent.
2. **Lowest precedence** — any same-named user or project agent silently wins.
3. **Cannot be used as an agent-team teammate** (F10 gate 1) — `win()` excludes
   `source==="plugin"`. `$CC/agent-teams.md` § Use subagent definitions for teammates
   says you *can* reference "project, user, **plugin**, or CLI-defined". **REFUTED by
   the binary.**
4. Matchers for `SubagentStart`/`SubagentStop` must use the scoped name and be anchored.

**Verdict on the question asked — is packaging viable for a team that needs per-agent
hooks and MCP servers? NO.** The two capabilities are exactly the two the plugin loader
strips, and the third loss (no teammate use) removes the team path as well. Ship such a
team as `.claude/agents/` files in the repo (or `--agents` JSON), and use the plugin only
for agents that need neither.

## The complete field reference (19 fields), with values and defaults

| Field | Required | Values | Default | Applies in |
|---|---|---|---|---|
| `name` | Yes | lowercase + hyphens; no `:`; must not start with `-` | — | all (key of the JSON object on the `--agents`/SDK path) |
| `description` | Yes | free text (min length 1) | — | all |
| `tools` | No | tool names, `Agent(type,...)`, `mcp__<server>`, `mcp__<server>__*` | inherit subagent pool | all; **teammate honours it** (force-unioned with 5 team tools) |
| `disallowedTools` | No | same grammar, plus `mcp__*` | none | all except teammate (dropped) |
| `model` | No | `sonnet`\|`opus`\|`haiku`\|`fable`\|full id\|`inherit` | `inherit` | all incl. teammate |
| `permissionMode` | No | `default`\|`acceptEdits`\|`auto`\|`dontAsk`\|`bypassPermissions`\|`plan`\|`manual`(alias of `default`, v2.1.200+) | inherit | **not** plugin, **not** teammate (forced `default`) |
| `maxTurns` | No | positive integer | unbounded | not plugin-listed; not teammate |
| `skills` | No | array of skill names; `disable-model-invocation` skills rejected | none | not teammate |
| `mcpServers` | No | array of name strings or inline `{name: config}` (`stdio`/`http`/`sse`/`ws`) | none | **not** plugin, **not** teammate |
| `hooks` | No | hook-config object; `Stop`→`SubagentStop` | none | **not** plugin, **not** teammate; project-level trust gate |
| `memory` | No | `user`\|`project`\|`local` | off | telemetry-only on the teammate path; **force-adds Write/Edit/Read** |
| `background` | No | boolean | Claude chooses; background by default since v2.1.198 | not teammate |
| `effort` | No | `low`\|`medium`\|`high`\|`xhigh`\|`max`, or an integer | inherit session | not teammate |
| `isolation` | No | **`worktree`\|`remote`** (docs say `worktree` only) | none | not teammate |
| `color` | No | `red`\|`blue`\|`green`\|`yellow`\|`purple`\|`orange`\|`pink`\|`cyan` | none | **file frontmatter only** — silently dropped from `--agents` JSON; teammate colour comes from team assignment |
| `initialPrompt` | No | string | none | **main-session only** (`--agent` / `agent` setting); "Not read when spawned as a subagent" |
| `observer` | No | non-empty string (agent type) | none | **UNDOCUMENTED** — spawns an observer agent (`isObserver:!0`, `observerTaskId`, `armingPermissionMode`) |
| `observerMessage` | No | non-empty string | none | **UNDOCUMENTED** |
| `observeSubagents` | No | boolean | none | **UNDOCUMENTED** |
| `prompt` | Yes* | string (min 1) | — | `--agents`/SDK **only** — replaces the markdown body |

## Ledger entries to append

```
claude-code frontmatter field count is 16 per docs, 19 in the binary (observer/observerMessage/observeSubagents undocumented) | REFUTED (the "sixteen fields" claim) | zod cVu @243821330 + file parser @243819107; control zzqwvfrx-nope=0 vs AskUserQuestion=18 files | 2.1.222 | 2026-08-05
isolation accepts "remote" as well as "worktree" | REFUTED (docs say worktree only) | isolation:E.enum(["worktree","remote"]) @243821330 | 2.1.222 | 2026-08-05
ALL_AGENT_DISALLOWED_TOOLS has 11 entries, not the 9 documented; adds ConnectGitHub, propose_skills, RefreshMcpTools | REFUTED | ax_() @241598156, every var resolved to a string literal | 2.1.222 | 2026-08-05
ASYNC_AGENT_ALLOWED_TOOLS (background keep-list) has 25 entries, not 19; adds StructuredOutput, REPL, SearchPlugins, SearchSkills, ListPlugins, ListSkills | REFUTED | lx_() @241598156 | 2.1.222 | 2026-08-05
Workflow is excluded for subagents only on non-"ant" builds; on "ant" builds it moves into the background keep-list | CONFIRMED | ax_/lx_ branch on e==="ant" | 2.1.222 | 2026-08-05
MCP tools bypass BOTH subagent tool filters (AH() is the first predicate) | CONFIRMED | grb() @247674663 | 2.1.222 | 2026-08-05
AskUserQuestion is removed from every subagent unconditionally; no flag restores it | CONFIRMED | bm in xKe with no conditional; forks skip both filters per sub-agents.md:325 | 2.1.222 | 2026-08-05
--brief enables SendUserMessage (one-way agent->user), not asking; it survives filter 1 but NOT filter 2, so only a FOREGROUND subagent gets it | CONFIRMED | CU absent from xKe and from Hpr; --brief desc @260891460 | 2.1.222 | 2026-08-05
A plugin-sourced or built-in agent CANNOT be used as an agent-team teammate; win() rejects it silently | REFUTED (agent-teams.md says plugin scope works) | win() @242398358, used @249122521 and @249447289 | 2.1.222 | 2026-08-05
A teammate honours only body + tools + model; permissionMode is forced to "default", memory is telemetry-only, and disallowedTools/skills/mcpServers/hooks/maxTurns/effort/background/isolation/initialPrompt/observer* are dropped | CONFIRMED (docs cover only tools+model+skills+mcpServers) | Rgb() definition object D | 2.1.222 | 2026-08-05
Declaring memory: force-adds Write, Edit and Read to an explicit tools: allowlist | CONFIRMED | both parsers: if(Mm()&&n.memory&&o!==void 0){...for(let c of [uu,Ol,ys])} | 2.1.222 | 2026-08-05
Agent-source precedence is built-in < plugin < userSettings < projectSettings(addl) < projectSettings < flagSettings < policySettings | CONFIRMED | sht() @242399155, Map last-write-wins | 2.1.222 | 2026-08-05
--agents JSON silently drops `color` despite sub-agents.md:223 listing it | REFUTED | cVu has no color key; control = the file parser's mA.includes(a) colour handler | 2.1.222 | 2026-08-05
"7 CLI flags exist that cli-reference.md never mentions" does not reproduce: 2 by --help diff, 62 by binary-registration diff | REFUTED | 62 help flags / 145 registered flags vs cli-reference.md; control --model present, --qqzzvv absent | 2.1.222 | 2026-08-05
SubagentStart cannot block subagent creation; SubagentStop can, and decision:"block" re-instructs the subagent | CONFIRMED | $CC/hooks.md:785,796,947,2128,2170 | 2.1.222 | 2026-08-05
Agent(type,...) spawn allowlist applies only to a --agent main-thread agent; the type list is ignored inside a subagent definition | CONFIRMED | $CC/sub-agents.md:399 + allowedAgentTypes parse @247674663 | 2.1.222 | 2026-08-05
Project-level subagent frontmatter hooks require workspace trust (v2.1.218+); untrusted = hooks skipped silently, subagent still runs | CONFIRMED | $CC/sub-agents.md:624-626 | 2.1.222 | 2026-08-05
Packaging agents as a plugin is not viable when they need per-agent hooks or MCP servers: those three fields are stripped, precedence is lowest, and plugin agents cannot be teammates | CONFIRMED | plugins-reference.md:74, sub-agents.md:229-231, win() gate | 2.1.222 | 2026-08-05
Subagent spawn depth default 3 (CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH), concurrent 20, per-session 200 | CONFIRMED | Jre/U$u/Enn @241575902,241598450 | 2.1.222 | 2026-08-05
COORDINATOR_MODE_ALLOWED_TOOLS = {Agent, TaskStop, SendMessage, StructuredOutput, Workflow}, gated by CLAUDE_CODE_COORDINATOR_MODE; zero doc coverage | CONFIRMED | fTo @241598800 | 2.1.222 | 2026-08-05
CUSTOM_AGENT_DISALLOWED_TOOLS is currently content-identical to ALL_AGENT_DISALLOWED_TOOLS, so the isBuiltIn branch in grb is a no-op today | CONFIRMED | pTo=new Set([...xKe]) @241598450 | 2.1.222 | 2026-08-05
```

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the shipped 2.1.222 binary and `claude --help` are this product's; the offline doc tree mirrors its published docs.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `sources/agent-harness-docs/docs/claude-code`, the 174-page offline doc corpus (step 00 of the doc-source chain).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this report's home.
