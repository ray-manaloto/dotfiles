# Claude Code expertise — the plugin extraction boundary for the autonomous DAG framework (2026-08-05, v2.1.222)

`claude --version` → **`2.1.222 (Claude Code)`**
Binary audited: `~/.local/share/claude/versions/2.1.222` (271,289,792 bytes)

**Corpora consulted:** installed binary (plugin loader + zod schemas, byte-scanned with `python3`) ·
`claude --help` · offline docs `$CC` (175 pages) · the maintained ledger in
`.claude/agents/claude-code-expert.md`. No live probe was needed for any headline claim; the two
claims that would need one are marked `SUSPECT` / `NEEDS-PROBE` with the probe written out.

`$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.

---

## Verdict table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | **CONFIRMED** | **The ledger row is incomplete: a plugin agent loses SEVEN frontmatter fields, not three** — `permissionMode`/`hooks`/`mcpServers` warn; **`initialPrompt`, `observer`, `observerMessage`, `observeSubagents` are dropped SILENTLY** — plus `isolation` narrowed `{worktree,remote}`→`{worktree}` | binary: full schema `oT_()` (19 fields) vs plugin loader `zzu()`; control arm = `memory`/`effort`/`maxTurns` read 3× each in the *same* 2,100-byte body while the 4 silent fields read 0. Second route: local loader `fVu()` spreads all 4 |
| 2 | **CONFIRMED** | **A plugin `settings.json` is parsed as a 2-key `.pick(...).strip()` of the full settings schema** — `env` and `permissions` are discarded with **no error and no warning** | binary verbatim `O7u=["agent","subagentStatusLine"]` + `zB_=Te(()=>BW().pick(...).strip())`; control arm = `env:` and `permissions:` both present in `BW()` |
| 3 | **CONFIRMED** | **Plugin settings are the BASE layer — lowest precedence of every source**, seeded before user/project/local/flag/policy merge on top | binary `S8i()`: `let r=$Gn(),n={};if(r)n=CJ(n,r,gae);` then the scope loop |
| 4 | **CONFIRMED** | Plugin **agents** are the lowest-priority agent scope (5 of 5); a same-named `.claude/agents/` file wins | `$CC/sub-agents.md:167` |
| 5 | **CONFIRMED** | **Plugin hooks fire inside subagents** and reach the whole event surface incl. `SubagentStart`/`SubagentStop`/`TeammateIdle`/`TaskCreated`/`TaskCompleted` | `$CC/hooks.md:257,264`; `$CC/sub-agents.md:614`; `$CC/plugins-reference.md:115-147`; binary `load_plugin_hooks` into the one registry |
| 6 | **SUSPECT** | Plugin hooks also apply *inside a teammate's own turn* | one route only: `$CC/agent-teams.md:260` "Teammates load skills and MCP servers from your project and user settings, the same as a regular session" + plugins are settings-enabled. **Probe written out below.** |
| 7 | **CONFIRMED** | **Workflows ARE plugin-carriable**, namespaced `/<plugin>:<workflow>` | `$CC/workflows.md:209-213`; manifest `workflows` field `$CC/plugins-reference.md:528` |
| 8 | **CONFIRMED** | A plugin's **`bin/` is appended to the Bash tool's PATH — LAST**, so any project binary of the same name shadows it | binary `GAs()` → `ma.join(t.path,"bin")`; `Xay()` → `t=[t,...l].join(":")` |
| 9 | **CONFIRMED** | A plugin root **`CLAUDE.md` is not loaded as project context** | `$CC/plugins-reference.md:847` |
| 10 | **CONFIRMED** | The framework's real env-pin names are `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` — **not** the names I first guessed | shape-enumeration of all 439 `CLAUDE_CODE_*` tokens; control arm = freshly invented `ZZQFRESHCTRL8811` → 0, `CLAUDE_CODE_TASK_LIST_ID` → 5 |
| 11 | **CONFIRMED** | **`observer` is gated by `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS`** — and that gate is an env var, i.e. a settings `env` pin, i.e. **not plugin-carriable either** | binary token enumeration; F2 |
| 12 | **CONFIRMED (ledger, cited not re-derived)** | Plugin agents **cannot be team teammates**; `permissionMode`/`mcpServers`/`hooks` ignored for plugin subagents | ledger rows, v2.1.222 / v2.1.221 |

---

## 1. What plugin scope KEEPS vs STRIPS

### 1a. Agents — the ledger's three is really seven

**The full agent frontmatter schema is `oT_()`, exactly 19 fields** (binary @242559700 — this
independently re-confirms the ledger's "frontmatter is 19 fields, not 16" row):

```
name  description  model  tools  disallowedTools  color  effort  permissionMode
mcpServers  hooks  maxTurns  skills  initialPrompt  memory  background
isolation  observer  observerMessage  observeSubagents
```

**The plugin agent loader is `zzu()`** (binary @243772500–243774600). Verbatim, the only drop it
announces:

```js
for(let V of["permissionMode","hooks","mcpServers"])
  if(c[V]!==void 0)
    C(`Plugin agent file ${e} sets ${V}, which is ignored for plugin agents. Use .claude/agents/ for this level of control.`,{level:"warn"});
```

…and the `isolation` narrowing, verbatim:

```js
let O=c.isolation==="worktree"?"worktree":void 0,
```

**Token census inside `zzu()`'s 2,100-byte body — control-armed.** `memory`, `effort`, `maxTurns`
are read in the *same* body, so a 0 is a real absence and not a blind probe:

| Field | count in `zzu()` | Verdict |
|---|---:|---|
| `memory` | 3 | KEPT (control arm — the probe can see) |
| `effort` | 3 | KEPT (control arm) |
| `maxTurns` | 3 | KEPT (control arm) |
| `disallowedTools` | 3 | KEPT |
| `tools`, `skills`, `background`, `model`, `description`, `name` | 1–2 | KEPT |
| `color` | 2 | KEPT — ⚠️ a **12th** field; the docs' allow-list names only 11 |
| `isolation` | 2 | **NARROWED** to `worktree` (schema allows `remote`) |
| `permissionMode` | 1 | **STRIPPED, warned** |
| `hooks` | 1 | **STRIPPED, warned** |
| `mcpServers` | 1 | **STRIPPED, warned** |
| **`initialPrompt`** | **0** | **STRIPPED SILENTLY** |
| **`observer`** | **0** | **STRIPPED SILENTLY** |
| **`observerMessage`** | **0** | **STRIPPED SILENTLY** |
| **`observeSubagents`** | **0** | **STRIPPED SILENTLY** |

**Second route, different construction:** the local (project/user) loader `fVu()` (binary
@243820225) spreads `...V!==void 0&&{observer:V}, ...q!==void 0&&{observerMessage:q},
...F!==void 0&&{observeSubagents:F}` and `...H!==void 0&&{initialPrompt:H}` into its return object.
`zzu()`'s return object has none of them. Two independent code paths, same answer.

**Why the four silent ones matter to this framework** — their own `.describe()` strings, verbatim
from the binary:

> `observer` — "Agent type auto-spawned as a background observer whenever this agent runs."
> `observerMessage` — "Supplemental postamble appended (after the harness-owned default) to each activity digest sent to the observer."
> `observeSubagents` — "If false, subagents this agent spawns do not inherit its observer. Defaults to true."
> `initialPrompt` — "Auto-submitted first message when this agent runs as the main session (via `--agent` or settings). Not read when spawned as a subagent."

`observer` is the harness's own **built-in telemetry/escalation mechanism** — an agent that watches
another agent's activity digest. `initialPrompt` is how a **durable DAG node** (a `--agent` main
session) gets its opening instruction without a human typing it. Both are exactly what the framework
wants, and **neither survives plugin packaging, silently.**

> ⚠️ **Correction to record.** This overturns nothing in the ledger, but it makes one row
> under-count. The ledger row *"`permissionMode` / `mcpServers` / `hooks` are ignored for
> plugin-scoped subagents"* should be amended to *"…and `initialPrompt`, `observer`,
> `observerMessage`, `observeSubagents` are dropped silently; `isolation` is narrowed to
> `worktree`."* The original row was derived from `$CC/sub-agents.md:282-287` — the docs enumerate
> only the three that *warn*. **Enumerating by SHAPE from the loader found four more.**

### 1b. Plugin `hooks.json` — everything fires, including inside subagents

`$CC/plugins-reference.md:115-147` lists **29 events** a plugin `hooks/hooks.json` can register,
including every one this framework needs: `SessionStart`, `Setup`, `PreToolUse`, `PostToolUse`,
`SubagentStart`, `SubagentStop`, `Stop`, `StopFailure`, **`TeammateIdle`**, **`TaskCreated`**,
**`TaskCompleted`**, `PermissionRequest`, `PermissionDenied`, `SessionEnd`, `WorktreeCreate/Remove`.

Five hook **types** are available: `command`, `http`, `mcp_tool`, `prompt` (LLM-evaluated),
`agent` (agentic verifier). The events that support all five include `PreToolUse`, `Stop`,
`SubagentStop`, `TaskCompleted`, `TaskCreated`, **`TeammateIdle`** (`$CC/hooks.md:2957-2970`).

**Subagents: CONFIRMED.** `$CC/hooks.md:264` — "Hooks from settings files, managed policy settings,
and plugins also run inside subagents." Same statement at `$CC/sub-agents.md:614`. Binary corroborates
a single registry: `t9e()` calls `cnr("load_plugin_hooks", …)` into the same collection every event
reads, gated only by safe-mode and `allowManagedHooksOnly`.

**Teammates: SUSPECT.** No doc sentence says plugin hooks fire inside a teammate's turn.
`$CC/agent-teams.md:260` says *"Teammates load skills and MCP servers from your project and user
settings, the same as a regular session"* — which implies a full settings load and therefore plugin
load, but it is one route and it names skills/MCP, not hooks.
**Probe:** in a scratch dir, install a `--plugin-dir` plugin whose `hooks/hooks.json` registers a
`PreToolUse` matcher `Bash` writing `$(date) $CLAUDE_AGENT_TYPE` to a file; launch with
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, spawn a teammate that runs one `Bash` call, and read the
file. Control arm: the same plugin's hook must fire for the *lead's* Bash call in the same run.

**Blockable events, so real enforcement:** `TeammateIdle` exit 2 keeps the teammate working;
`{"continue": false, "stopReason": …}` stops it (`$CC/hooks.md:2415, 2440-2443`). `SubagentStop` can
block (ledger, CONFIRMED). `SubagentStart` cannot — it can only inject context (ledger).

⚠️ **The one thing a plugin's hooks cannot do**: managed settings `allowManagedHooksOnly` disables
**plugin hooks** while leaving managed settings-file hooks running (`$CC/hooks.md:266`; binary string
`"Skipping plugin hooks - allowManagedHooksOnly is enabled and no managed plugins"`). Safe mode
disables them too. A project `settings.json` hook is not subject to the plugin-specific gate.

### 1c. Skills, commands, workflows

All three are cleanly plugin-carriable.

* **Skills** — `skills/<name>/SKILL.md`. Namespaced `plugin-name:skill-name`, so they **cannot
  collide** with project/user skills (`$CC/skills.md:122`). This is the *least* lossy component.
* **Commands** — `commands/*.md` flat files; same namespace.
* **Workflows** — `workflows/` at the plugin root, or the `workflows` manifest field. Runs as
  `/<plugin>:<workflow>` (`$CC/workflows.md:209-213`). ⚠️ Workflows are separately gated by the
  `disableWorkflows`/`enableWorkflows` **settings** keys — which a plugin cannot set (F2).

### 1d. MCP servers

Carriable (`.mcp.json` at plugin root or inline `mcpServers`), start automatically when the plugin is
enabled. Two constraints that bite:

* Hooks targeting the plugin's own server must use the **scoped** name
  `mcp__plugin_<plugin>_<server>__<tool>`, and an `mcp_tool` hook's `server` field takes
  `plugin:<plugin>:<server>`. *"A matcher written against the bare server key never fires."*
  (`$CC/plugins-reference.md:157`.)
* A **project-scope** `@skills-dir` plugin's MCP servers go through per-server approval, its LSP
  servers need workspace trust, and its **background monitors do not load at all**
  (`$CC/plugins-reference.md:393-399`). Personal scope has none of these restrictions.

Relevant ledger row, cited not re-derived: the MCP predicate is the **first** check in the agent tool
filter and returns true unconditionally — `mcp__*` tools bypass both agent tool filters.

### 1e. Statusline and LSP

* **`statusLine`**: **NOT plugin-carriable.** It is a plain settings key, and the plugin
  `settings.json` pick allows only `agent` and `subagentStatusLine`.
* **`subagentStatusLine`**: **IS plugin-carriable** — one of the two allowed keys.
* **LSP**: fully carriable via `.lsp.json` / `lspServers`. First-registered server wins a file
  extension; a project-scope plugin's LSP needs workspace trust.

### 1f. The full plugin-carried surface, enumerated by shape

From the manifest schema (`$CC/plugins-reference.md:521-537`) and the file-locations table (`:851-865`),
cross-checked against the binary's implicit-layout constant
`Q7u = ["agents","output-styles","themes","hooks","monitors"]` (the dirs auto-discovered with no manifest):

`skills` · `commands` · `agents` · `workflows` · `hooks` · `mcpServers` · `outputStyles` ·
`lspServers` · `experimental.themes` · `experimental.monitors` · `userConfig` · `channels` ·
`dependencies` · `bin/` · `settings.json` (2 keys) · `${CLAUDE_PLUGIN_DATA}` persistent dir.

---

## 2. What a plugin CANNOT carry at all — the permanent project-scoped shim

**This is the sharpest finding of the audit, and the binary states it in one line.**

```js
var O7u; var D7u = v(() => { O7u = ["agent","subagentStatusLine"] });
...
zB_ = Te(() => BW().pick(Object.fromEntries(O7u.map((e)=>[e,!0]))).strip());
```

`BW()` is the **full settings schema**. `.pick({agent, subagentStatusLine}).strip()` means a plugin's
`settings.json` is validated against a two-key projection and **every other key is discarded with no
error and no warning**. Control arm confirming the probe is aimed right: `env:Ifg().optional()
.describe("Environment variables to set for Claude Code sessions")` and
`permissions:Kpc(e).optional().describe("Tool usage permissions configuration")` are both keys of
`BW()` (binary @239848456 and @239849539) — so they are exactly the kind of thing `.strip()` eats.

Therefore, **permanently project-scoped, forever**:

| Surface | Why a plugin cannot carry it |
|---|---|
| **`env` block** — every env pin | stripped by the 2-key pick |
| **`permissions.allow / deny / ask / defaultMode`** | stripped by the 2-key pick |
| **`hooks` in settings** | plugin hooks come from `hooks/hooks.json`, but they are the *only* kind subject to `allowManagedHooksOnly`/safe-mode suppression |
| **`statusLine`, `disableWorkflows`/`enableWorkflows`, `workflowSizeGuideline`, `baseRef`, `bgIsolation`, `sparsePaths`, `disableAllHooks`, `additionalDirectories`, everything else** | stripped by the 2-key pick |
| **`enabledPlugins`** | a plugin cannot enable itself; someone's settings file must |
| **`pluginConfigs`** — even the plugin's own `userConfig` values | read from **user settings / `--settings` / managed only**; project `.claude/settings.json` entries are **ignored** since v2.1.207 (`$CC/plugins-reference.md:594-602`) |
| **project context (`CLAUDE.md`, `.claude/rules/*.md`)** | a plugin-root `CLAUDE.md` is not loaded (`$CC/plugins-reference.md:847`); a plugin ships instructions only as skills |
| **agent `permissionMode` / `hooks` / `mcpServers` / `initialPrompt` / `observer` / `observerMessage` / `observeSubagents`; `isolation: remote`** | §1a |
| **team teammates** | plugin agents cannot be teammates (ledger, CONFIRMED against `agent-teams.md`) |

⚠️ **Anything that reaches the framework as an environment variable is in this column by
construction**, because the only in-repo way to set one is the settings `env` block. That covers
**all four** of the caller's named pins:

| Pin | Real token (shape-enumerated, control-armed) |
|---|---|
| spawn depth | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` |
| concurrency | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (+ `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`) |
| task-list id | `CLAUDE_CODE_TASK_LIST_ID` |
| baseRef | `baseRef` is a **settings key**, not an env var (binary settings-key table) — still stripped |
| observer gate | `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS` |
| teams gate | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` (ledger: bare truthiness — `"0"` **enables**) |

> **Control arm for the token census:** freshly invented `ZZQFRESHCTRL8811` → **0** matches;
> `CLAUDE_CODE_TASK_LIST_ID` → **5**; `baseRef` → **40**. The probe discriminates. It also **refuted
> my own first guesses** — `CLAUDE_CODE_MAX_AGENT_DEPTH` and `CLAUDE_CODE_MAX_CONCURRENT_AGENTS`
> both returned 0. Enumerating all 439 `CLAUDE_CODE_*` tokens by shape gave the real names.

⚠️ **And the env block itself is fragile on one path** (ledger, CONFIRMED): in `exec`
background-launch mode the child's env is stripped of **every** `CLAUDE_*` except `CLAUDE_JOB_DIR`,
`CLAUDE_CONFIG_DIR`, `CLAUDE_BG_PTY_AUTH`. Pins must live in the settings `env` block, never in
exported shell vars — which reinforces that this column stays in `.claude/settings.json`.

---

## 3. Precedence when a plugin and the project define the same thing

**The project wins, every time, on every axis.** Four independent mechanisms:

| Axis | Precedence | Evidence |
|---|---|---|
| **settings** | **plugin < user < project < local < `--settings` < managed** — plugin settings are the *seed* the scope loop merges onto | binary `S8i()`: `let r=$Gn(),n={};if(r)n=CJ(n,r,gae);` then `for(let c of VVr(e)){…n=CJ(n,p,gae)}` |
| **agents** | managed(1) > `--agents`(2) > `.claude/agents/`(3) > `~/.claude/agents/`(4) > **plugin(5, lowest)** | `$CC/sub-agents.md:167` |
| **skills** | **no conflict possible** — plugin skills are namespaced `plugin:skill` | `$CC/skills.md:122` |
| **hooks** | **no override — they MERGE.** Every source's entries are additive | `$CC/hooks.md:268` |
| **`bin/`** | plugin bin dirs are appended **last** to PATH ⇒ a project binary of the same name wins | binary `Xay()`: `t=[t,...l].filter(Boolean).join(":")` |
| **plugin vs plugin** | last plugin loaded wins a settings key, with a debug warning `Plugin "<name>" overrides setting "<key>" (previously set by another plugin)` | binary `eU_()` |
| **`--plugin-dir` vs installed** | the local `--plugin-dir` copy wins for that session (except managed force-enable/disable) | `$CC/plugins.md:328` |

Two consequences worth stating plainly:

1. **Extraction is non-destructive and reversible.** Because plugin settings are the base layer and
   plugin agents are the lowest scope, the project can always override anything the plugin ships —
   including during migration, without uninstalling.
2. **Hooks are the exception that makes duplication dangerous.** Hooks *merge*; they do not
   override. If the same enforcement hook ships in both `.claude/settings.json` and the extracted
   plugin, **it runs twice**. For a blocking `SubagentStop` / `TeammateIdle` gate that is not
   idempotent — it is a double block. **Move a hook; never copy it.**

---

## 4. The boundary — two columns

| Component | Can move to the plugin later | Stays project-scoped **forever** |
|---|---|---|
| **Role agent definitions** | ✅ The **body**, `description`, `tools`, `disallowedTools`, `skills`, `model`, `effort`, `maxTurns`, `memory`, `background`, `color`, `isolation: worktree` | ❌ `permissionMode`, `hooks`, `mcpServers` (warned) · `initialPrompt`, `observer`, `observerMessage`, `observeSubagents` (**silent**) · `isolation: remote` · **any agent that must be a team teammate** |
| **Workflow scripts** | ✅ `workflows/` → `/<plugin>:<name>`; helper executables in `bin/` (PATH, appended last) | ❌ the `enableWorkflows` / `disableWorkflows` / `workflowSizeGuideline` settings that gate them |
| **Session-hook enforcement (`SubagentStop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`)** | ✅ `hooks/hooks.json` carries all of them, blocking semantics intact, and they fire inside subagents. Prefer this once proven — **but move, never copy** | ❌ keep in project settings if you need immunity from `allowManagedHooksOnly` / safe-mode plugin suppression, or if the teammate-path question (SUSPECT #6) is load-bearing and unprobed |
| **Env pins** (spawn depth, concurrency, `baseRef`, task-list id, observer/teams gates) | ❌ **nothing** | ✅ **ALL of it.** `env` and `baseRef` are stripped by the 2-key `.pick().strip()`. This is the permanent shim, and it is the one the DAG substrate depends on |
| **Escalation surfaces** | ✅ **channels** (manifest `channels` + a bundled MCP server) — a genuinely plugin-carriable human-escalation path · ✅ `PermissionRequest` / `PermissionDenied` hooks · ✅ `Notification` hooks | ❌ `permissions.*` rules (allow/deny/ask/defaultMode) · ❌ `AskUserQuestion` is unconditionally absent from any delegated agent regardless of packaging (ledger) · ❌ channels are **main-agent-only** and not agent-to-agent (ledger) |
| **Telemetry** | ✅ `PostToolUse`/`SessionEnd`/`Stop` hooks writing artifacts · ✅ `experimental.monitors` (⚠️ **do not load at all for a project-scope `@skills-dir` plugin**) · ✅ `subagentStatusLine` (one of the two allowed settings keys) | ❌ **the `observer` mechanism entirely** — the frontmatter fields are silently dropped *and* its `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS` gate is an env var · ❌ OTEL env vars · ❌ `statusLine` |
| **Agent-memory stores** | ✅ the agent's `memory: user\|project\|local` field is read by the plugin loader | ❌ the store's own `MEMORY.md` — the ledger's CONFIRMED row: `memory:` writes a topic file, but **nothing reads it without the store's own `MEMORY.md`**, which lives in the project · ❌ a plugin-root `CLAUDE.md` is not context |

### The one-sentence rule

> **Anything expressed as a settings key or an environment variable stays in
> `.claude/settings.json` forever; anything expressed as a file under a component directory can
> move.** The 2-key `.pick().strip()` is the entire boundary, and it fails silently — so the
> project-scoped shim is not a migration leftover, it is a permanent, documented artifact.

### Sequencing advice for the extraction

1. **Extract skills first** — namespaced, zero collision risk, zero precedence surprise.
2. **Then workflows and `bin/`** — namespaced too; watch the PATH-last shadowing.
3. **Then role agents**, and at that moment **audit each definition for the seven lost fields**.
   `claude --debug` surfaces the three warned ones; **nothing surfaces the four silent ones**, so
   grep the agent files for `initialPrompt|observer|observerMessage|observeSubagents` before moving
   them and re-home whatever hits into `.claude/agents/`.
4. **Hooks last, and by MOVE.** Delete from `.claude/settings.json` in the same commit that adds
   them to `hooks/hooks.json`, or blocking gates double-fire.
5. **Never move the `env` block.** It is not extractable at this version and there is no roadmap
   signal in the binary that it will be.

### Cheap regression check for a future version

Re-run these three, in order — each is one command and each is the load-bearing fact:

```
python3 -c "import re;B=open('<binary>','rb').read();print(re.findall(rb'O7u=\[[^\]]*\]',B))"   # the 2-key pick
python3 -c "...count initialPrompt|observer inside the zzu() body..."                            # the silent 4
python3 -c "...check S8i() still seeds n from \$Gn() BEFORE the scope loop..."                    # plugin = base layer
```

---

## Ledger entries to append

```
| **A plugin agent loses SEVEN frontmatter fields, not three** — `permissionMode`/`hooks`/`mcpServers` WARN; **`initialPrompt`, `observer`, `observerMessage`, `observeSubagents` are dropped SILENTLY**; `isolation` narrowed `{worktree,remote}`→`{worktree}`. `color` is a 12th kept field the docs' allow-list omits | CONFIRMED | binary: schema `oT_()` (19) vs plugin loader `zzu()`; control arm = `memory`/`effort`/`maxTurns` read 3× in the same 2,100-byte body while the 4 read 0; second route = local loader `fVu()` spreads all 4 | 2.1.222 | 2026-08-05 |
| **A plugin `settings.json` is `BW().pick({agent,subagentStatusLine}).strip()`** — `env`, `permissions`, `statusLine`, `baseRef` and every other key are discarded with NO error and NO warning | CONFIRMED | binary `O7u=["agent","subagentStatusLine"]`; control arm: `env:` and `permissions:` both present in `BW()` | 2.1.222 | 2026-08-05 |
| **Plugin settings are the BASE layer — lowest precedence of all sources**, seeded before user/project/local/flag/policy merge onto them ⇒ extraction is always project-overridable and reversible | CONFIRMED | binary `S8i()`: `let r=$Gn(),n={};if(r)n=CJ(n,r,gae);` then the scope loop | 2.1.222 | 2026-08-05 |
| **Hooks MERGE across sources, they do not override** ⇒ shipping the same blocking hook in both project settings and a plugin fires it TWICE. Move a hook, never copy it | CONFIRMED | `$CC/hooks.md:268` | 2.1.222 | 2026-08-05 |
| A plugin's `bin/` is appended to the Bash PATH **last**, so a project binary of the same name shadows it; `isBuiltin` plugins are excluded | CONFIRMED | binary `GAs()` + `Xay()` `t=[t,...l].join(":")` | 2.1.222 | 2026-08-05 |
| Workflows ARE plugin-carriable as `/<plugin>:<workflow>`; skills are namespaced `plugin:skill` so they cannot collide; plugin agents are the LOWEST agent scope (5 of 5) | CONFIRMED | `$CC/workflows.md:209`; `$CC/skills.md:122`; `$CC/sub-agents.md:167` | 2.1.222 | 2026-08-05 |
| **The real spawn-control env names are `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`**; `observer` is gated by `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS` | CONFIRMED | shape-enumeration of all 439 `CLAUDE_CODE_*` tokens; control arm fresh `ZZQFRESHCTRL8811`→0 vs `CLAUDE_CODE_TASK_LIST_ID`→5. REFUTES the guessed `CLAUDE_CODE_MAX_AGENT_DEPTH`/`..._CONCURRENT_AGENTS` (both 0) | 2.1.222 | 2026-08-05 |
| `pluginConfigs` (a plugin's own `userConfig` values) are read ONLY from user settings, `--settings` and managed — project `.claude/settings.json` entries are IGNORED since v2.1.207 | CONFIRMED | `$CC/plugins-reference.md:594-602` | 2.1.222 | 2026-08-05 |
| A project-scope `@skills-dir` plugin's **background monitors do not load at all**; its MCP servers need per-server approval and its LSP servers need workspace trust | CONFIRMED | `$CC/plugins-reference.md:393-399` | 2.1.222 | 2026-08-05 |
| Do plugin hooks fire inside a TEAMMATE's own turn? | SUSPECT | one route: `$CC/agent-teams.md:260` "teammates load ... from project and user settings, the same as a regular session"; probe in report §1b | 2.1.222 | 2026-08-05 |
```

---

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed binary v2.1.222 (`~/.local/share/claude/versions/2.1.222`) was byte-scanned for the plugin loader, the agent frontmatter zod schema, the plugin settings pick, the settings merge order, and the `CLAUDE_CODE_*` token census; `claude --version` read from the same install.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the offline vendor doc tree `sources/agent-harness-docs/docs/claude-code` (175 pages) supplied `plugins-reference.md`, `plugins.md`, `sub-agents.md`, `settings.md`, `hooks.md`, `agent-teams.md`, `workflows.md`, `skills.md`.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: the maintained ledger `.claude/agents/claude-code-expert.md` (cited, not re-derived) and the report path.
