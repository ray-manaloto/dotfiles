# Claude Code 2.1.222 — the surface the documentation does not cover

**Agent:** claude-code-expert-cli-surface
**Version under test:** 2.1.222 — `/Users/rmanaloto/.local/share/claude/versions/2.1.222`, Mach-O 64-bit arm64, 271,289,792 bytes
**Docs corpus:** `$CC = ~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code` (175 files)
**Date:** 2026-08-05

Existence claims come from a byte-scan of the binary. Semantics claims come from
the surrounding minified JS (the bundle ships readable source). Behaviour claims
are marked as live-probe.

---

## Findings table

| verdict | claim | corpus + control arm |
|---|---|---|
| CONFIRMED | `strings -n6 \| grep -Fc` **undercounts** — it counts lines, not occurrences (12 vs 16 for `SendUserMessage`); macOS `strings` without `-a` also skips part of the file | binary; control: fresh absent term `qwzvfrb7`→0/0, known-present `permission-mode`→84 |
| CONFIRMED | `--brief` and `CLAUDE_CODE_BRIEF` are **the same knob**; entitlement additionally gated by server flag `tengu_kairos_brief` | binary source `Sjn()` / `rfn()` verbatim below |
| CONFIRMED | `SendUserMessage` **is live on this host right now, without `--brief`** — dispatched in a plain `claude -p` run via the `PEWTER_OWL` path | live probe: `--debug-file` log shows `tool_dispatch_start tool=SendUserMessage … outcome=ok`; control: same probe with `--brief` and without both show it |
| CONFIRMED | A **subagent (Agent tool) does NOT get `SendUserMessage`** — it gets `SendMessage` | live probe, `--forward-subagent-text` + `stream-json`; subagent self-report lists 15 built-ins incl. the similarly-named `SendMessage`, `TaskStop`, `Monitor` — control: those three are real and correctly named, so the report discriminates |
| NEEDS-PROBE | The *mechanism* excluding it from subagents | `briefStandalone` is used for transcript compaction, not tool filtering; no subagent filter located |
| CONFIRMED | `--help` is **not** the flag surface: 43 flag specs are registered with `.hideHelp()` and appear in neither `--help` nor (21 of them) any doc page | binary regs; control: `--allowedTools` initially missed → extractor fixed for single-quoted descs, then found |
| CONFIRMED | 2 **hidden root subcommands**: `remote-control`, `import-conversations` | live `--help`; control: real `doctor` prints own usage, fresh nonsense `zqfxv9` falls through to root help |
| CONFIRMED | **368 of 614** `CLAUDE_*`/`ANTHROPIC_*` env-var names in the binary appear in **zero** doc page (60%) | binary raw-token scan vs all 175 pages; control: `ANTHROPIC_API_KEY` present in both |
| REFUTED | "26 env vars are documented but absent from the binary" — an artifact of probing only *read* sites | control: `CLAUDE_PROJECT_DIR`=26 hits, `CLAUDE_PLUGIN_ROOT`=43, `CLAUDE_SKILL_DIR`=6 in the binary; fresh absent `zzqq7x4v`=0. Real doc-only residue is **4**, not 26 |
| REFUTED | "`autoDreamEnabled`, `skipWorkflowUsageWarning`, `skipAutoPermissionPrompt` are inert" — **all three are live settings keys** with zod schemas, `describe()` strings and multi-scope reads | binary source verbatim below |
| CONFIRMED | ≥23 settings keys are read by the binary and named in **no** doc page, incl. three that govern multi-agent work | binary settings band vs all 175 pages; control: 9/11 known-documented keys captured by the same extractor |
| CONFIRMED | Undocumented **tools**: `SendUserMessage` (0 doc files), `ListAgents` (0), `SendUserFile` (1) | binary + `grep -rlw` over docs; control: `Agent`→128 files, fresh `Zqvxk9Tool`→0 |
| CONFIRMED (hazard) | With `SendUserMessage` live, **`claude -p` stdout can be just `Sent.`** — the real answer went into the tool call | live probe: a subagent-delegation prompt returned stdout `'Sent.\n'` at rc=0 |
| REFUTED | `--tools <name>` can be used to test whether a tool name is real | control: `--tools Zqvxk9Tool` → rc=0, same output as `--tools Read`. Unknown names are silently ignored — the probe can only pass |
| **REFUTED** | the inherited *"7 flags exist only in the CLI"* — re-derived, it is **2** (`--brief`, `--file`), and only **1** (`--brief`) is absent from every doc page | see F2b; control: `--model` → 16 doc files |

---

## F0 — Method: how these counts were taken (and the defect in the prescribed probe)

```
== grep -Fc  (matching LINES)          == 12
== grep -Fo | wc -l  (OCCURRENCES)     == 16
== python3 mmap+re.finditer byte-scan  == 16
== control, fresh known-absent 'qwzvfrb7' == 0 / 0
== control, known-present 'permission-mode' == 84
```
macOS `strings` default scope: 408,583 lines; `strings -a`: 426,691. Every count
below is `re.finditer` over `mmap` of the whole file.

**Re-runnable at the next version:** point `BIN` at the new binary and re-run the
four extractors (option registrations, env tokens, settings band, `.command()`),
then diff each against the docs tree with `grep -rlw`.

---

## F1 — `--brief` / `SendUserMessage`, in full

### The tool is real, and it was renamed

```js
var CU="SendUserMessage", QXr="Brief",
    Vss="You ended the turn without calling SendUserMessage.",
    Kss="Send a message to the user",
    Yss="Send a message the user will read. Text outside this tool is visible in the detail view, but most won't open it — the answer lives here.\n\n`message` supports markdown. `attachments` accepts two forms per entry: a file path string (absolute or cwd-relative) … or the exact {file_uuid, file_name, size, is_image} object a device tool like `attach_file` returned to you …\n\n`status` labels intent: 'normal' when replying to what they just …"
```
Exported names: `BRIEF_TOOL_NAME`, `LEGACY_BRIEF_TOOL_NAME`, `DESCRIPTION`,
`BRIEF_TOOL_PROMPT`, `BRIEF_PROACTIVE_SECTION`, `BRIEF_ENFORCE_SENTINEL`,
`PEWTER_OWL_TOOL_PROMPT`.

The rename is part of the same batch as `Task→Agent`:
```js
a8i={Task:"Agent",KillShell:"TaskStop",KillBash:"TaskStop",AgentOutputTool:"TaskOutput",
     BashOutputTool:"TaskOutput",AgentOutput:"TaskOutput",BashOutput:"TaskOutput",
     ListPeers:"ListAgents",Brief:"SendUserMessage",
     ListMcpResources:"ListMcpResourcesTool",ReadMcpResource:"ReadMcpResourceTool",
     ReadMcpResourceDir:"ReadMcpResourceDirTool"};
```

### Tool definition — no agent-scope predicate

```js
$0p=ms({name:CU,aliases:[QXr],
  searchHint:"send a message to the user — your primary visible output channel",
  briefStandalone:!0, maxResultSizeChars:1e5, userFacingName(){return""},
  get inputSchema(){return z3t()?T_b():v_b()},
  isEnabled(){return z3t()||ayt()},
  isConcurrencySafe(){return!0}, isReadOnly(){return!0},
  async description(){return Kss},
  async prompt(){return z3t()?Yss:Jss},
  mapToolResultToToolResultBlockParam(e,t){…return{…content:`Message delivered to user.${n}`}}
```

### Enablement — two independent paths

```js
function rfn(){return te.CLAUDE_CODE_BRIEF||hEe("tengu_kairos_brief",!1,T_y)}   // isBriefEntitled
function z3t(){return hfe()&&rfn()||XUs()}                                     // isBriefEnabled
function v_y(e){if(!e.includes(CU)&&!e.includes(QXr))return!1;if(ayt())return!1;return rfn()}  // shouldToolsListOptInToBrief
function w_y(){let e=Qe("tengu_kairos_brief_stop_hook_text","");return typeof e==="string"&&e.length>0?e:E_y}
var T_y=300000;   // 5-min gate cache

function zId(e){if(te.CLAUDE_CODE_PEWTER_OWL!==void 0)return te.CLAUDE_CODE_PEWTER_OWL;
  if(Sn())return!1;let t=S_y();if(t!==""&&!ao(Zi()).includes(t))return!1;
  return Qe(`tengu_${e}`,!1)||hR()?.[e]===!0}
function ayt(){if(te.CLAUDE_CODE_PEWTER_OWL_TOOL!==void 0)return te.CLAUDE_CODE_PEWTER_OWL_TOOL;
  return zId("pewter_owl_tool")}     // isPewterOwlTool
function XUs(){return zId("pewter_owl_brief")}   // isPewterOwlBrief
```

**`--brief` vs `CLAUDE_CODE_BRIEF`: same knob.**
```js
function Sjn(e){let t=e.brief,r=te.CLAUDE_CODE_BRIEF;if(!t&&!r)return;
  let{isBriefEntitled:n}=(Vne(),Wr(Zwe));let o=n();if(o)h8e(!0);
  N("tengu_brief_mode_enabled",{enabled:o,gated:!o,source:ge(r?"env":"flag")})}
```
Either arms brief mode; telemetry records only `source: "env" | "flag"`. **Values:**
`te.CLAUDE_CODE_BRIEF` is used as a bare truthy in `rfn()` and as a boolean in the
renderer (`CMk=te.CLAUDE_CODE_BRIEF; if(hfe()&&(CMk||Qe("tengu_kairos_brief",!1))…)`),
so it is a presence/truthy flag, not an enum. Contrast `CLAUDE_CODE_PEWTER_OWL`,
which is tested `!==void 0` and returned directly (tri-state: unset / forced-on /
forced-off).

**Enforcement.** `BRIEF_ENFORCE_SENTINEL` plus the default stop text:
> *In brief mode, plain assistant text is hidden from the user — only
> SendUserMessage reaches them. Call it now with your substantive reply for this
> turn. Do not mention this reminder; the message should read as if you wrote it
> unprompted, addressing only what the user actually asked. If you genuinely have
> nothing useful to tell the user, you may end the turn without calling it.*

**Proactive system-prompt section** (`BRIEF_PROACTIVE_SECTION`), verbatim:
> `## Talking to the user` … *SendUserMessage is where your replies go. Text
> outside it is visible if the user expands the detail view, but most won't —
> assume unread. … every time the user says something, the reply they actually
> read comes through SendUserMessage. Even for "hi". Even for "thanks". … ack →
> work → result.*

**Second mode — PEWTER_OWL.** Same tool, different prompt (`Jss`):
> *Send a message the user will read verbatim. Use this for content they need to
> see exactly as written **between tool calls** — a generated code snippet, a
> specific value, a direct reply to something they asked mid-task. Don't use it
> for routine narration … **or for your final answer** — normal text reaches them
> for those.*

So: brief mode = the tool is the ONLY visible channel; pewter-owl = the tool is an
EXTRA mid-turn channel and plain text still reaches the user.

### Who can call it — LIVE PROBE

Top-level, on this host, **without any flag**:
```
2026-08-05T05:37:19.189Z [DEBUG] Hook PreToolUse:SendUserMessage (PreToolUse) success:
2026-08-05T05:37:19.190Z [INFO] [Stall] tool_dispatch_start tool=SendUserMessage toolUseId=toolu_01H91… permissionDecisionMs=1
2026-08-05T05:37:19.190Z [INFO] [Stall] tool_dispatch_end   tool=SendUserMessage toolUseId=toolu_01H91… outcome=ok durationMs=0
2026-08-05T05:37:19.230Z [DEBUG] Hook PostToolUse:SendUserMessage (PostToolUse) success:
```
Identical in the `--brief` and non-`--brief` arms ⇒ enabled here via `ayt()`
(pewter-owl), not brief. It is also **hookable** — PreToolUse/PostToolUse fire.

Subagent, via `--forward-subagent-text --output-format stream-json`, the subagent's
own reported tool list, verbatim:
```
Agent, Bash, Edit, Read, Skill, ToolSearch, Write, EnterWorktree, ExitWorktree,
Monitor, NotebookEdit, SendMessage, TaskStop, WebFetch, WebSearch, mcp__MCP_DOCKER__…
```
`SendUserMessage` **absent**; `SendMessage` present. Control: the list names
`TaskStop`, `Monitor`, `EnterWorktree` — all real, correctly spelled — so the
report is not hallucinating names wholesale.

**Answer to the design question the prior work got wrong:** agent-to-user
communication is *not* impossible — but it is a **top-level-session** channel. A
`SendUserMessage` from inside an `Agent` delegation is not available. For a
**teammate** (a separate `claude` process launched with the hidden
`--agent-id/--agent-name/--team-name/--teammate-mode` flags) the gates are
evaluated in that process and `CLAUDE_CODE_BRIEF` is inherited through the
environment — **NEEDS-PROBE**, not measured here.

**Operational hazard (CONFIRMED, live):** with the tool live, a `claude -p` run
delegating to a subagent returned stdout `'Sent.\n'` at rc=0 — the substantive
answer went into the `SendUserMessage` call, not stdout. Anything scripting
`claude -p` and parsing stdout can silently receive a receipt instead of a result.

---

## F2 — The other six flags from the motivating finding

All verified present in `--help` of 2.1.222 (verbatim):

| flag | what it does |
|---|---|
| `--allowedTools, --allowed-tools <tools...>` | *Comma or space-separated list of tool names to allow (e.g. "Bash(git \*) Edit")* — `--allowed` is not a flag; the alias is `--allowedTools` |
| `--disallowedTools, --disallowed-tools <tools...>` | deny list, same syntax |
| `--file <specs...>` | *File resources to download at startup. Format: `file_id:relative_path`* (e.g. `--file file_abc:doc.txt`) — the claude.ai file-attachment plumbing |
| `--autocompact <auto\|tokens>` | *Auto-compact window size (auto, or 100k–1M tokens)*. Parser rejects anything else: *"It must be 'auto', or between 100k and 1M (e.g. 500k, 200000, or 200 as shorthand)"* |
| `--debug-file <path>` | *Write debug logs to a specific file path (implicitly enables debug mode)* — **LIVE-VERIFIED**: wrote a 51,365-byte log for a one-word prompt |
| `--remote-control-session-name-prefix <prefix>` | *Prefix for auto-generated Remote Control session names (default: hostname)*. `claude remote-control --help` additionally reveals the env form: **`CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX`** |

### F2b — REFUTED: the inherited "7 CLI-only flags" number

I re-derived it rather than repeating it (inherited numbers carry no control arm).
Counting `` `--flag `` literals in `cli-reference.md` and long flags in root
`--help`:

```
root --help option lines           59
root --help distinct long flags    62      (brief said 52)
cli-reference.md distinct flags    94      (brief said 85)

=== in root --help, NOT in cli-reference.md ===
--brief
--file
=== ... and not in ANY of the 175 doc pages ===
--brief
(control: --model appears in 16 doc pages)
```

Per-flag cross-check of the inherited list:

| flag | in `cli-reference.md` | in any doc page | verdict |
|---|---|---|---|
| `--brief` | 0 | **0** | CLI-only ✔ |
| `--file` | 0 | 2 | cli-reference-only |
| `--allowedTools` / `--allowed-tools` | 1 / 1 | 10 / 3 | **documented — claim wrong** |
| `--disallowed*` | 2 | 9 | **documented — claim wrong** |
| `--autocompact` | 1 | 4 | **documented — claim wrong** |
| `--debug-file` | 1 | 7 | **documented — claim wrong** |
| `--remote-control-session-name-prefix` | 1 | 4 | **documented — claim wrong** |

`--allowed` / `--disallowed` are not flag names at all — the specs are
`--allowedTools, --allowed-tools <tools...>`, so a probe splitting on the comma
manufactures two flags that do not exist. **The motivating finding's headline
(`--brief`/`SendUserMessage` undocumented) holds; its supporting count does not.**
The real gap is not in root `--help` at all — it is the `.hideHelp()` tier (F3)
and the env-var surface (F5).

⚠️ **`--tools` cannot be used to test whether a tool name exists.** Control arm:
`--tools Read`, `--tools SendUserMessage`, `--tools Zqvxk9Tool` all → rc=0, stdout
`OK`. Unknown names are silently discarded — a probe that can only pass.

---

## F3 — The bigger class the brief did not know about: `.hideHelp()` flags

Flags registered as `new Rd("--x","desc").hideHelp()` are absent from `--help`
entirely. **43 hidden specs** found; **21 have zero hits in any of the 175 doc
pages** (and that doc-side count is a generous substring match).

Verbatim registration excerpt:
```js
t.addOption(new Rd("--enable-auto-mode","(deprecated) Opt in to auto mode").hideHelp()),
t.addOption(new Rd("--brief","Enable SendUserMessage tool for agent-to-user communication")),
t.addOption(new Rd("--channels <servers...>","MCP servers whose channel notifications (inbound push) should register this session. Space-separated server names.").hideHelp()),
t.addOption(new Rd("--dangerously-load-development-channels <servers...>","Load channel servers not on the approved allowlist. For local channel development only. Shows a confirmation dialog at startup.").hideHelp()),
t.addOption(new Rd("--agent-id <id>","Teammate agent ID").hideHelp())
```

**The multi-agent block — every one hidden, every one 0 doc hits:**

| flag | description (verbatim) |
|---|---|
| `--agent-id <id>` | Teammate agent ID |
| `--agent-name <name>` | Teammate display name |
| `--team-name <name>` | Team name for teammate coordination |
| `--agent-color <color>` | Teammate UI color |
| `--agent-type <type>` | Custom agent type for this teammate |
| `--parent-session-id <id>` | Parent session ID for analytics correlation |
| `--plan-mode-required` | Require plan mode before implementation |

⇒ **a teammate is launched as a separate `claude` process with these flags.**
Corroborated by the session-init parser:
```js
function xiv(e){…return{agentId,agentName,teamName,agentColor,planModeRequired,
  parentSessionId, teammateMode: r==="auto"||r==="tmux"||r==="iterm2"||r==="in-process"?r:void 0,
  agentType}}
```
`teammateMode ∈ {auto, tmux, iterm2, in-process}`.

**Other notable hidden flags (0 doc hits unless noted):**

| flag | description |
|---|---|
| `--append-subagent-system-prompt <prompt>` | *Append a system prompt to every Task-tool subagent's system prompt, propagated to nested subagents (only works with --print). Implies `CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT=1`.* (3 doc hits) |
| `--plan-mode-instructions <instructions>` | *Custom workflow body for plan mode. Replaces the default code-implementation phases in the plan-mode system reminder; the read-only enforcement preamble and ExitPlanMode protocol footer are always kept.* |
| `--advisor <model>` | *Enable the server-side advisor tool with the specified model (alias or full ID).* |
| `--managed-settings <json>` | *Policy-tier settings JSON from a spawning parent process (SDK use only)* |
| `--permission-prompt-tool <tool>` | *MCP tool to use for permission prompts (only works with --print)* |
| `--max-turns <turns>` | *Maximum number of agentic turns in non-interactive mode…* |
| `--thinking <mode>` / `--thinking-display <display>` | `enabled\|adaptive\|disabled` / `summarized\|omitted` |
| `--session-mirror` | *Emit transcript_mirror frames on stdout (SDK-internal; set by ProcessTransport when sessionStore is configured)* |
| `--sdk-url <url>` | *Use remote WebSocket endpoint for SDK I/O streaming.* Runtime error text: *"This flag is reserved for Remote Control worker processes connecting to Anthropic's backend"* |
| `--rewind-files <user-message-id>` | *Restore files to state at the specified user message and exit (requires --resume)* |
| `--resume-session-at <message id>` | *When resuming, only messages up to and including the assistant message with `<message.id>`* |
| `--reply-on-resume` | *…set by /background mid-turn so the fork continues the in-flight turn* |
| `--workload <tag>` | *Workload tag for billing-header attribution (cc_workload)…* |
| `--init` / `--init-only` / `--maintenance` | Run Setup hooks with a given trigger |
| `--plugin-dir-no-mcp <path>` | like `--plugin-dir` but the engine will not read the plugin's `.mcp.json` |
| `--cowork` | *Use cowork_plugins directory* |
| `--teleport [session]`, `--cloud [...]`, `--remote [...]` | cloud/teleport session attach |
| `--prefill <text>`, `--deep-link-origin`, `--deep-link-repo <slug>` | deep-link trampoline |
| `--enable-auth-status`, `--system-prompt-file`, `--append-system-prompt-file`, `--interview`, `-i/--interactive`, `-d2e/--debug-to-stderr`, `--max-thinking-tokens` | misc |

**Counting method.** Extract every `\.option\("<spec>",<desc>` and
`new X\("<spec>",<desc>\)<chain>` from the binary (both `"` and `'` description
quoting), mark `hideHelp` from the chain. Result: **201 registration sites,
195 unique (spec, description) pairs, 162 unique specs, 43 hidden.**
_Control arm:_ the first extractor missed `--allowedTools` (single-quoted
description) — added, re-run, found. Residual limitation: flags built from a table
rather than a literal call are not captured, so **162 is a floor.**

---

## F4 — Subcommand surface

Root `--help` lists **13** commands. The binary registers **45** distinct
`.command()` names across all levels. Two are **hidden root commands**:

| command | evidence |
|---|---|
| `remote-control` | `claude remote-control --help` prints its own usage: *"Remote Control - Control local sessions from claude.ai/code or the Claude mobile app"*, options `--name`, `--remote-control-session-name-prefix` (env: `CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX`), `-c/--continue` |
| `import-conversations` | `Usage: claude import-conversations [options] <exportPath>` — options `--cwd <dir>` (*Archive directory the imported sessions anchor to*), `--dry-run`. **0 hits in any doc page** |

_Control arm:_ real command `doctor --help` → own usage; fresh nonsense
`claude zqfxv9 --help` → falls through to root help. `config`, `critique`, `eval`,
`init`, `serve`, `setup`, `tag`, `validate` all fell through ⇒ they are *sub*-
subcommands (`claude plugin eval|init|tag|validate`, `claude mcp …`), not hidden
root commands.

Hidden filter mechanism, verbatim:
`t.commands.filter((i)=>!(("_hidden"in i)&&i._hidden))`.

**Doc coverage per root command** (`grep -rho "claude <cmd>"` over 175 pages;
control: `claude zqfxv9` → 0):
`agents` 174 hits/23 files · `mcp` 166/19 · `plugin` 127/20 · `update` 47/16 ·
`doctor` 42/14 · `auth` 28/7 · `auto-mode` 22/5 · `remote-control` 22/8 ·
`setup-token` 16/11 · `ultrareview` 15/7 · `install` 14/8 · `project` 12/5 ·
`gateway` 10/4 · **`import` 0/0** · **`import-conversations` 0/0**.

`claude import` is a *shown* root command with **zero** documentation.

Undocumented subcommand flags worth naming: `claude plugin eval` carries a whole
eval harness (`--ablation`, `--judge-model`, `--threshold`, `--runs`, `--report`,
`--publish-report`, `--max-cost-usd`, `--scaffold`, `--case`, `--tag`,
`--output-dir`) — an entire testing surface with no doc page.

---

## F5 — Environment variables

**Method.** Binary side = every `(?<![A-Za-z0-9_])(CLAUDE|ANTHROPIC)_[A-Z0-9_]{2,60}(?![A-Za-z0-9_])`
token (existence authority). Doc side = the same regex over **all 175 pages**
(deliberately generous — `env-vars.md` alone is much smaller).

| set | count |
|---|---|
| `CLAUDE_*`/`ANTHROPIC_*` names in the binary | **614** |
| named anywhere in the 175 doc pages | **254** |
| named in `env-vars.md` alone | **223** |
| **in binary, in NO doc page** | **368 (60%)** |
| in binary, not in `env-vars.md` | **394 (64%)** |
| in docs, not in binary | 8 → really **4** (see below) |

_Control arm:_ `ANTHROPIC_API_KEY` present in both sets.

**REFUTED sub-claim.** A first pass probing only *read* sites
(`process.env.X`, the `te.X` accessor, the env-module manifest) reported **26**
doc-only vars. That is a probe artifact: vars the harness **sets for child
processes** have no read site. Control:

```
CLAUDE_PROJECT_DIR   26      CLAUDE_PLUGIN_ROOT  43
CLAUDE_SESSION_ID     3      CLAUDE_SKILL_DIR     6
CLAUDE_CODE_ENABLE_AUTO_MODE  7    zzqq7x4v (fresh control)  0
```
After switching to raw-token existence the doc-only residue is 8, of which
`ANTHROPIC_DEFAULT_`, `CLAUDE_CODE_USE_` are prose prefixes and
`CLAUDE_PLUGIN_OPTION_WEBHOOK_URL`, `CLAUDE_MODEL` are examples. **Genuinely
documented-but-gone from 2.1.222 (4):** `CLAUDE_BASH_NO_LOGIN`,
`CLAUDE_CODE_CONNECT_TIMEOUT_MS`, `CLAUDE_CODE_ENABLE_OPUS_4_7_FAST_MODE`,
`CLAUDE_CODE_OPUS_4_6_FAST_MODE_OVERRIDE`.

### Undocumented and load-bearing for multi-agent work

```
CLAUDE_CODE_COORDINATOR_MODE           CLAUDE_CODE_COORDINATOR_EXTRA_TOOLS
CLAUDE_CODE_COORDINATOR_PROPAGATE_NESTED_MEMORY
CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS   CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS*
CLAUDE_CODE_WORKFLOWS                  CLAUDE_CODE_WORKFLOW_SIZE_WARNING_AGENTS
CLAUDE_CODE_WORKFLOW_SIZE_WARNING_TOKENS
CLAUDE_CODE_PLAN_V2_AGENT_COUNT        CLAUDE_CODE_PLAN_V2_EXPLORE_AGENT_COUNT
CLAUDE_CODE_SUBAGENT_CACHE_EVICT       CLAUDE_CODE_FORK_SUBAGENT
CLAUDE_CODE_FORWARD_SUBAGENT_TEXT      CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT
CLAUDE_CODE_BRIEF   CLAUDE_CODE_BRIEF_UPLOAD
CLAUDE_CODE_PEWTER_OWL   CLAUDE_CODE_PEWTER_OWL_TOOL
CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME    CLAUDE_WORKFLOW_NAME_ONLY
CLAUDE_REMOTE_WORKFLOW_SCRIPT          CLAUDE_REMOTE_WORKFLOW_ARGS
CLAUDE_BRIDGE_* (9)                    CLAUDE_CODE_REMOTE_* (8)
CLAUDE_CODE_AGENT   CLAUDE_AGENTS_SELECT   CLAUDE_CODE_AGENT_PROXY_*
```
`*` = already set in this repo's own `settings.json` env block (seen in the live
debug log), i.e. we are **already depending on an undocumented variable**.

Verbatim, from `applyCoordinatorToolFilter`:
```js
let t=Dkl?.isCcrCoordinator()??!1, r=te.CLAUDE_CODE_BRIEF,
    n=new Set((process.env.CLAUDE_CODE_COORDINATOR_EXTRA_TOOLS??"").split(",").map((i)=>i.trim()).filter(Boolean));
… return e.filter((i)=>fTo.has(i.name)||rBT(i.name)||t&&U2m(i)||oBT(i)||tmn(i)||o&&AH(i)||r&&eBT.has(i.name)||n.has(i.name))
… eBT=new Set([CU,yEe]);   // SendUserMessage, SendUserFile
```

Other undocumented clusters: memory (`CLAUDE_CODE_DISABLE_ORG_MEMORY`,
`_DISABLE_MEMORY_{BULK_INFLATE,MASS_DELETE_HOLD,PERIODIC_RESYNC,STREAM_LIST}`,
`_FORCE_EVALUATE_MEMORY`, `_MEMORY_PUSH_DELETE_MODE`, `CLAUDE_COWORK_MEMORY_*` ×4),
sandbox (`CLAUDE_CODE_FORCE_SANDBOX`, `_SANDBOXED`, `_BASH_SANDBOX_SHOW_INDICATOR`),
plugin sync (`CLAUDE_CODE_SYNC_PLUGINS*` ×5), skills
(`CLAUDE_CODE_INVOKED_SKILLS`, `_SKILL_NAME`, `_DISABLE_CLAUDE_{API,CODE}_SKILL`).

---

## F6 — Settings keys

**Method.** The settings zod band (binary offsets 239,840,000–239,940,000) yields
**203** `key:E.<type>` names. _Control:_ 9 of 11 known-documented keys captured
(`apiKeyHelper`, `model`, `statusLine`, `outputStyle`, `cleanupPeriodDays`,
`includeCoAuthoredBy`, `forceLoginMethod`, `enableAllProjectMcpServers`, …);
`permissions`/`hooks`/`env` missed (separate schema builders) ⇒ **203 is a floor**.
Fresh nonsense key `zqvv8k` → 0.

**21 keys from that band + 2 from the gated `shape()` blocks appear in NO doc page:**

| key | verbatim `describe()` |
|---|---|
| `skipWorkflowUsageWarning` | *@internal Whether the user has accepted the multi-agent workflow usage warning. **Until set, auto permission mode prompts before running a workflow.*** |
| `enableWorkflows` | *Enable or disable the Workflows feature for this user. Unset = default by plan once the feature is available.* |
| `isolatePeerMachines` | ***Require explicit approval before SendMessage can reach a peer session on another machine via Remote Control*** |
| `doneMeansMerged` | *@internal When true, Claude keeps working until the PR is ready for you to merge, a cron/Monitor is armed to resume later, or it hands you a self-contained next step.* |
| `defaultView` | *Default transcript view: chat (SendUserMessage checkpoints only) or transcript (full)* |
| `skipAutoPermissionPrompt` | *Whether the user has accepted the auto mode opt-in dialog* |
| `useAutoModeDuringPlan` | *Whether plan mode uses auto mode semantics when auto mode is available (default: true)* |
| `autoDreamEnabled` | *Enable background memory consolidation (auto-dream). When set, overrides the server-side default.* |
| `autoUploadSessions` | *Mirror local sessions to claude.ai as view-only (no remote control)* |
| `precomputeCompactionEnabled` | *Precompute the compaction summary in the background before it is needed. Only applies when auto-compact is on.* |
| `promptSuggestionEnabled` | *When false, prompt suggestions are disabled…* |
| `proxyAuthHelper` | *Shell command that outputs a Proxy-Authorization header value (EAP)* |
| `daemonColdStart` | *When no background service is running: 'transient' spawns one for this login session; 'ask' offers to install it persistently* |
| `terminalTitleFromRename` | *Whether /rename updates the terminal tab title (defaults to true)…* |
| `totalTokensReminderBudget` | *@internal Starting budget (tokens) for totalTokensReminder 'padded-countdown' mode. Defaults to 15000000. Server-controlled via GrowthBook; env var `CLAUDE_CODE_TOTAL_TOKENS_REMINDER_BUDGET` overrides.* |
| `breakReminder`, `breakThresholdMinutes`, `quietHours`, `intervalMinutes` | wellbeing nudges |
| `feedbackDrafts` | *Whether to show tips in the spinner* |
| `showMessageTimestamps`, `totalTokensReminder`, `totalTokensReminderAfterUserTurn`, `xaaIdp` | (`xaaIdp`: *IdP issuer URL for OIDC discovery*) |

### REFUTED — the three keys previously called inert

```js
// autoDreamEnabled
autoDreamEnabled:E.boolean().optional().describe("Enable background memory consolidation (auto-dream). When set, overrides the server-side default.")
function fMo(){if(!sUs())return!1;let e=co().autoDreamEnabled;if(e!==void 0)return e;return bxd()?.enabled===!0}
function Ke(){…let tt=Be&&co().autoDreamEnabled===void 0;Mi("userSettings",{autoDreamEnabled:Be}),B(Be),N("tengu_auto_dream_toggled",{enabled:Be,is_first_enable:tt})}

// skipWorkflowUsageWarning
skipWorkflowUsageWarning:E.boolean().optional().describe("@internal Whether the user has accepted the multi-agent workflow usage warning. Until set, auto permission mode prompts before running a workflow.")
function JZn(){return!!(Mr("userSettings")?.skipWorkflowUsageWarning||Mr("localSettings")?.skipWorkflowUsageWarning||Mr("flagSettings")?.skipWorkflowUsageWarning||Mr("policySettings")?.skipWorkflowUsageWarning)}
// plus an error path: "Failed to persist skipWorkflowUsageWarning:" and telemetry "tengu_workflow_usage_warning_accepted"

// skipAutoPermissionPrompt
skipAutoPermissionPrompt:E.boolean().optional().describe("Whether the user has accepted the auto mode opt-in dialog")
function GJa(){return!["policySettings","userSettings","flagSettings"].some((t)=>Mr(t)?.skipAutoPermissionPrompt===!0)&&!Lt().hasSeenAutoModeEntryWarning}
async function Bah(){…if(t?.skipAutoPermissionPrompt&&t?.permissions?.defaultMode!=="auto"){await Mi("userSettings",{skipAutoPermissionPrompt:void 0})…}}
```
All three: zod schema + `describe()` + multi-scope reads + persistence + telemetry.
The earlier "all four are inert" inference generalised from *"0 doc hits"* to
*"no implementation"*. Binary count answers existence; **only a call-site read
answers liveness.** `CLAUDE_CODE_BRIEF` was the fourth, already known real.

Gated feature shapes (also undocumented as a mechanism):
```js
wfg=["autoMode","deepLink","voice","briefView","screenReader"]
briefView:{buildGate:()=>!0,shape:()=>({defaultView:E.enum(["chat","transcript"]).optional()…})}
```

---

## F7 — Undocumented tools

| tool | binary occurrences | doc files naming it |
|---|---|---|
| `SendUserMessage` | 16 | **0** |
| `ListAgents` (rename of `ListPeers`) | 5 | **0** |
| `SendUserFile` | 9 | 1 |
| `SendMessage` | 85 | 7 |
| `Agent` (control) | 2739 | 128 |
| `Zqvxk9Tool` (fresh absent control) | — | 0 |

`SendUserFile` definition, verbatim:
```js
var yEe="SendUserFile", Pbs="Send one or more files to the user",
Obs="Send files to the user. Use this when the file *is* the deliverable — a generated diagram, a report, a screenshot, a built artifact — and you want it surfaced, not just mentioned. Paths can be absolute or relative to the current w…"
isEnabled(){if(Ln()!=="firstParty"||Ra())return!1;if(!Qe("tengu_send_user_file",!0))return!1;
  return(fk()||!!process.env.CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE||tr(process.env.CLAUDE_CODE_REMOTE)||W2e())&&!z3t()}
```
Note `&& !z3t()` — `SendUserFile` is the **non-brief** file channel; in brief mode
attachments go through `SendUserMessage`'s `attachments` parameter instead.

---

## F8 — How wide is the gap (answer to Q6)

Stated per axis with the counting method, so it can be re-run at 2.1.223:

| axis | binary | documented | undocumented | % |
|---|---|---|---|---|
| CLI flag specs (registration sites) | ≥162 | 62 long flags in root `--help`; 94 in `cli-reference.md` | 43 `.hideHelp()`, **21 with 0 doc hits**; only **1** root-`--help` flag (`--brief`) is undocumented | ≥26% hidden from `--help` |
| root subcommands | 15 reachable | 13 in `--help` | 2 hidden + `import` (0 doc hits) | ~20% |
| `CLAUDE_*`/`ANTHROPIC_*` env names | 614 | 254 (all pages) / 223 (`env-vars.md`) | **368** | **60%** |
| settings keys (zod band) | ≥203 | 182 | **≥21** (+2 gated) | ≥11% |
| built-in tool names sampled | — | — | 2 of 10 sampled have 0 doc files | — |

**Defensible characterisation:** the documentation covers the *supported* surface
reasonably well (settings ~89%, subcommands ~87%) but is far behind on
**environment variables (40% covered)** and blind to an entire **hidden-flag tier**
whose contents are precisely the multi-agent / teammate / coordinator / workflow
machinery. The gap is not uniform noise — it is concentrated exactly where
multi-agent orchestration lives.

**Re-run recipe:** four extractors over the binary (option registrations with both
quote styles; `(CLAUDE|ANTHROPIC)_[A-Z0-9_]+` raw tokens; `key:E.` over the settings
band; `.command("…")`), each diffed against `grep -rlw` over `$CC/`, each with a
fresh known-absent control term **invented at run time**.

---

## Undocumented surface

| name | kind | what it does | binary hits | doc hits (files) |
|---|---|---|---|---|
| `SendUserMessage` | tool | primary visible reply channel; brief mode makes it the ONLY one | 16 | 0 |
| `SendUserFile` | tool | deliver files to the user; disabled in brief mode | 9 | 1 |
| `ListAgents` | tool | rename of `ListPeers` | 5 | 0 |
| `--brief` | flag (shown) | enable `SendUserMessage` | — | 0 |
| `CLAUDE_CODE_BRIEF` | env | same knob as `--brief`; truthy | 9+ | 0 |
| `CLAUDE_CODE_PEWTER_OWL` / `_PEWTER_OWL_TOOL` | env | tri-state force of the mid-turn variant | 10 | 0 |
| `--agent-id/-name/--team-name/--agent-color/--agent-type/--parent-session-id/--plan-mode-required` | hidden flags | how a **teammate process** is launched | — | 0 each |
| `--teammate-mode <mode>` | hidden flag | `auto\|tmux\|iterm2\|in-process` | — | 3 |
| `--append-subagent-system-prompt` | hidden flag | inject prompt into every subagent, nested | — | 3 |
| `--plan-mode-instructions` | hidden flag | replace plan-mode workflow body | — | 0 |
| `--advisor <model>` | hidden flag | server-side advisor tool | — | 4 (substr) |
| `--channels` / `--dangerously-load-development-channels` | hidden flags | MCP inbound-push channel registration | — | 6 / 3 |
| `--managed-settings <json>` | hidden flag | policy-tier settings from a spawning parent | — | 0 |
| `--session-mirror`, `--sdk-url` | hidden flags | SDK/Remote-Control internals | — | 0 / 1 |
| `--rewind-files`, `--resume-session-at`, `--reply-on-resume` | hidden flags | resume/rewind surface | — | 0 |
| `--workload <tag>` | hidden flag | billing attribution (`cc_workload`) | — | 1 |
| `claude remote-control` | hidden root cmd | drive local sessions from claude.ai/mobile | — | 22 hits/8 files (cmd itself undocumented as a subcommand) |
| `claude import-conversations <exportPath>` | hidden root cmd | import a conversation archive | — | 0 |
| `claude import` | shown root cmd | import config from another AI agent | — | **0** |
| `claude plugin eval …` | subcommand | full plugin eval harness (11 flags) | — | 0 for its flags |
| `skipWorkflowUsageWarning` | setting | gates the multi-agent workflow warning | 9 | 0 |
| `enableWorkflows` | setting | Workflows feature toggle | — | 0 |
| `isolatePeerMachines` | setting | approval before `SendMessage` crosses machines | — | 0 |
| `doneMeansMerged` | setting | keep working until PR is mergeable | — | 0 |
| `defaultView` | setting | `chat` (SendUserMessage checkpoints) vs `transcript` | 26 | 0 |
| `skipAutoPermissionPrompt`, `useAutoModeDuringPlan` | settings | auto-mode opt-in state | 5 / — | 0 |
| `autoDreamEnabled` | setting | background memory consolidation | 5 | 0 |
| `CLAUDE_CODE_COORDINATOR_EXTRA_TOOLS` | env | extra tools past the coordinator filter | — | 0 |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | env | **already set in this repo's settings.json** | — | 0 |
| `CLAUDE_CODE_WORKFLOW_SIZE_WARNING_{AGENTS,TOKENS}` | env | thresholds behind the workflow warning | — | 0 |
| `CLAUDE_CODE_PLAN_V2_{AGENT,EXPLORE_AGENT}_COUNT` | env | plan-v2 fan-out width | — | 0 |
| `CLAUDE_CODE_TOTAL_TOKENS_REMINDER_BUDGET` | env | overrides `totalTokensReminderBudget` | — | 0 |
| `CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX` | env | env form of the `--remote-control-session-name-prefix` flag | — | 0 |
| +336 further `CLAUDE_*`/`ANTHROPIC_*` names | env | see `scratchpad/undoc2.txt` | — | 0 |

---

## Ledger entries to append

1. **`SendUserMessage` exists, is LIVE on this host without any flag, and is
   top-level-only.** A subagent's tool list has `SendMessage` but not
   `SendUserMessage` (measured). Any design that declared agent-to-user
   communication impossible is wrong at the top level and right for subagents —
   re-judge the ticket written to work around it.
2. **`claude -p` stdout can be `Sent.`** once `SendUserMessage` is live: the answer
   goes into the tool call. Scripts parsing `-p` stdout can silently get a receipt.
   Use `--output-format stream-json` and read the tool input, or set
   `CLAUDE_CODE_PEWTER_OWL=0`.
3. **`--help` is not the flag surface.** 43 flags are `.hideHelp()`. When asking
   "can Claude Code do X", grep the binary's option registrations, not `--help`.
4. **`strings | grep -Fc` counts LINES.** Use `grep -Fo | wc -l` or a byte-scan;
   and macOS `strings` needs `-a` to see the whole file.
5. **Binary presence ≠ liveness.** The "four inert user-scope keys" conclusion came
   from `0 doc hits` + a count. Three of the four are live with zod schemas,
   multi-scope reads and telemetry. Existence needs a count; liveness needs a
   **call site**.
6. **`--tools <name>` silently ignores unknown names** — it cannot be used as a
   tool-existence probe (control-armed: a fresh nonsense name behaves identically
   to `Read`).
7. **A teammate is a separate `claude` process** launched with hidden
   `--agent-id/--agent-name/--team-name/--agent-color/--agent-type/--parent-session-id/--teammate-mode`;
   `teammateMode ∈ {auto, tmux, iterm2, in-process}`. This is the documented-nowhere
   substrate under the agent-team work in #546/#547.
8. **This repo already sets an undocumented env var** — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`
   appears in our `settings.json` env block; it is in 0 doc pages, so it has no
   stability contract.
9. **60% of the harness's env-var names are undocumented** (368/614), concentrated
   in coordinator / workflow / memory / remote clusters.
10. **`isolatePeerMachines`** is the only control over `SendMessage` reaching a peer
    session on another machine, and it is undocumented.
11. **An inherited count is not a measurement.** The "7 CLI-only flags" figure was
    6/7 wrong on re-derivation — `--allowed`/`--disallowed` are not flag names
    (comma-split artifacts of `--allowedTools, --allowed-tools <tools...>`), and
    four others are in `cli-reference.md`. The headline it supported was still
    right, which is exactly why the number survived unchecked.

---

## GitHub repos touched

_None._ All corpora were local: the installed Claude Code binary, its `--help`
output, and the offline `agent-harness-docs` doc tree in the sibling
knowledge-base clone (`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs`).
