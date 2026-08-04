# Harness Settings Reference for Agent Teams — Claude Code 2.1.221

**Status:** COMPLETE — Part 1 (Tables A–D) and Part 2 (project audit) both written.
**Date:** 2026-08-04
**Harness version:** `2.1.221 (Claude Code)` — measured via `claude --version`
**Repo:** `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch `research/agent-team-design`

## Source discipline

Three tiers, in the order consulted. Where they disagree, **the live doc wins** and the
disagreement is called out inline.

| Tier | Source | Citation form |
|---|---|---|
| 1 | Offline vendor snapshot | `$CC/<page>.md:<line>` where `$CC = ~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code` |
| 2 | Live docs | `https://code.claude.com/docs/en/<page>.md` |
| 3 | Release notes | `gh api repos/anthropics/claude-code/releases` |

Any claim without a `file:line` or URL is labelled **UNVERIFIED**.

---

## Part 1 — The knobs

### Offline-vs-live staleness: measured, and the brief's example CORRECTED

The brief said the offline copy was wrong about nesting depth (5 → 1 → 3). **It is not.**
Offline `$CC/sub-agents.md:862` already reads "up to **three** layers below the main
conversation", and `$CC/sub-agents.md:886` already carries the v2.1.219 note. The live copy
says the same at the same lines. The offline snapshot is current on that point.

What the raw `diff` counts actually measure is a **rendering difference**: the offline `.md`
retains MDX `{/* min-version: X */}` comments that the live `.md` endpoint strips. Control arm
— stripping those comments before diffing collapses most pages to zero:

| Page | raw changed lines | after stripping `min-version` comments |
|---|---|---|
| `agent-teams.md` | 12 | **0** |
| `worktrees.md` | 8 | **0** |
| `agents.md` | 2 | **0** |
| `model-config.md` | 38 | 8 |
| `costs.md` | 10 | 8 |
| `skills.md` | 25 | 11 |
| `permission-modes.md` | 64 | 12 |
| `workflows.md` | 24 | 10 |
| `sub-agents.md` | 128 | 60 |
| `hooks.md` | 118 | 94 |
| `settings.md` | 387 | 297 |
| `env-vars.md` | 620 | 620 (pure table re-formatting — see below) |

Method: `perl -pe 's/\{\/\*\s*min-version:[^*]*\*\/\}//g'` on the offline file, then
`diff … | grep -c '^[<>]'`.

**`env-vars.md`'s 620 is not staleness either.** Control arm — extract every env-var-shaped
token from both copies and set-difference them in both directions:

```
comm -13 <(offline tokens) <(live tokens)   →  (empty)
comm -23 <(offline tokens) <(live tokens)   →  (empty)
```

Identical variable sets in both directions. The diff is table column-width churn.

**Where live genuinely wins:** `settings.md` (297), `hooks.md` (94) and `sub-agents.md` (60).
The two real content additions in `sub-agents.md` are two rows added to the built-in "Other"
agent table for the `claude` agent's role as the default for a dispatched background session
(live `sub-agents.md:77,80`) — absent from offline. Every Part 1 claim below is cited to the
**live** copy.

---

### Table A — Subagent frontmatter fields

Source: live `https://code.claude.com/docs/en/sub-agents.md`, "Supported frontmatter fields"
table at lines 277–294. Only `name` and `description` are required (`sub-agents.md:275`).

| Field | Req | What it does | Default | Allowed values | Min version / notes |
|---|---|---|---|---|---|
| `name` | **Yes** | Unique identifier. Hooks receive it as `agent_type`. Filename need not match. | — | lowercase letters + hyphens; **no `:`** (reserved for plugin scoping) | A name containing `:` is **not loaded** and logs a debug error as of **v2.1.218**; accepted before that (`sub-agents.md:279`) |
| `description` | **Yes** | Tells Claude when to delegate here. Include "use proactively" to encourage delegation (`sub-agents.md:702`). | — | free text | — |
| `tools` | No | Allowlist of tools. | inherits every tool available to subagents | comma list of tool names; `Agent(type,…)`; `mcp__<server>` / `mcp__<server>__*` patterns | If **nothing** in the list resolves, the subagent **refuses to launch** with an error naming the entries — as of **v2.1.208**; before that it launched tool-less (`sub-agents.md:364`) |
| `disallowedTools` | No | Denylist, subtracted from the inherited or specified pool. | — | same syntax as `tools`; `mcp__*` removes every MCP tool | Applied **first**, then `tools` resolves against the remainder; a tool in both is removed (`sub-agents.md:362`) |
| `model` | No | Model for this subagent. | **`inherit`** | `sonnet`, `opus`, `haiku`, `fable`, a full ID (`claude-opus-5`), or `inherit` | Resolution order: `CLAUDE_CODE_SUBAGENT_MODEL` → per-invocation `model` param → frontmatter → main conversation (`sub-agents.md:305-310`) |
| `permissionMode` | No | Permission mode while active. | inherits from parent | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan`, `manual` | `manual` (alias of `default`) needs **v2.1.200+**. **Ignored for plugin subagents.** Parent `bypassPermissions`/`acceptEdits`/`auto` **override it** (`sub-agents.md:284,467`) |
| `maxTurns` | No | Cap on agentic turns before the subagent stops. | unbounded (undocumented numeric default) | positive integer | `sub-agents.md:285` |
| `skills` | No | Skills **preloaded into context at startup** — full content injected, not just the description. | none preloaded | list of skill names | Cannot preload a skill with `disable-model-invocation: true`, incl. bundled `/verify` and `/code-review`. Missing/disabled skills are skipped with a debug warning (`sub-agents.md:487,489`) |
| `mcpServers` | No | MCP servers for this subagent — inline definitions or string references to already-configured servers. | none extra | list; inline uses `.mcp.json` schema (`stdio`/`http`/`sse`/`ws`) | **Ignored for plugin subagents.** Inline servers connect at subagent start, disconnect at finish; string refs share the parent connection (`sub-agents.md:287,404`) |
| `hooks` | No | Lifecycle hooks scoped to this subagent. | none | same shape as `settings.json` `hooks` | **Ignored for plugin subagents.** A project-level agent's frontmatter hooks need **workspace trust** as of **v2.1.218**; untrusted → subagent still runs, hooks skipped + debug error. `Stop` is auto-converted to `SubagentStop` (`sub-agents.md:288,625,657`) |
| `memory` | No | Persistent memory directory surviving across conversations. | disabled | `user` → `~/.claude/agent-memory/<name>/`; `project` → `.claude/agent-memory/<name>/`; `local` → `.claude/agent-memory-local/<name>/` | **Inert if auto memory is off** (`autoMemoryEnabled` false or `CLAUDE_CODE_DISABLE_AUTO_MEMORY`). Enabling force-enables Read/Write/Edit and injects the first 200 lines / 25 KB of `MEMORY.md` (`sub-agents.md:518,523,524`) |
| `background` | No | Force this subagent to always run as a background task. | unset — **Claude chooses, and as of v2.1.198 defaults to background** | `true` | Background subagents get a **reduced built-in tool set** (`sub-agents.md:290,338`) |
| `effort` | No | Effort level while this subagent is active; overrides the session level. | inherits from session | `low`, `medium`, `high`, `xhigh`, `max` (availability depends on model) | `sub-agents.md:291` |
| `isolation` | No | Run in a temporary git worktree — isolated repo copy. | none (runs in the parent's cwd) | `worktree` | Branches from your **default branch**, *not* the parent's `HEAD`. Auto-cleaned if unchanged. As of **v2.1.203** a command escaping to the main checkout **fails**; as of **v2.1.210** the check covers the whole repo, and for Bash it also inspects `git -C`, `--git-dir`, `GIT_DIR`/`GIT_WORK_TREE`, and `cd` (`sub-agents.md:292,267,269,271`) |
| `color` | No | Display color in the task list and transcript. | — | `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan` | `sub-agents.md:293` |
| `initialPrompt` | No | Auto-submitted as the first user turn **only when the agent runs as the main session agent** (`--agent` or the `agent` setting). | — | free text; commands and skills are processed | Prepended to any user-provided prompt (`sub-agents.md:294`) |
| `prompt` | JSON only | The system prompt, for `--agents` JSON / SDK `agents`. Equivalent to the markdown body. | — | free text | `sub-agents.md:224` |

**Scope precedence** (`sub-agents.md:162-168`) — highest first:

| Priority | Location | Scope |
|---|---|---|
| 1 | Managed settings `.claude/agents/` | Organization-wide |
| 2 | `--agents` CLI flag (JSON) | Current session, never written to disk |
| 3 | `.claude/agents/` | Current project |
| 4 | `~/.claude/agents/` | All your projects |
| 5 | Plugin `agents/` directory | Where the plugin is enabled |

Project scope is discovered by **walking up from cwd**, so every `.claude/agents/` between cwd
and the repo root is scanned; nearest-to-cwd wins on a name collision (v2.1.178+,
`sub-agents.md:172`). Both project and user scopes are scanned **recursively**, but the
subfolder does **not** namespace the agent — identity comes only from `name`, and two files
under one scope sharing a name load nondeterministically by filesystem read order
(`sub-agents.md:178,180`). Plugin subfolders **do** namespace: `agents/review/security.md` in
`my-plugin` registers as `my-plugin:review:security` (`sub-agents.md:182`).

**Three separate limits, three separate variables** (`sub-agents.md:893`):

| Limit | Default | Variable | Min version |
|---|---|---|---|
| Nesting depth | **3** layers below the main conversation | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | var needs v2.1.217; **default 3 since v2.1.219** |
| Total per session | **200** | `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | v2.1.212 |
| Concurrent | **20** | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | v2.1.217 |

Depth history (`sub-agents.md:887-888`): v2.1.172–2.1.216 nested up to **five** layers,
unchangeable; v2.1.217–2.1.218 defaulted to **one**; v2.1.219 raised it to **three**. At the
depth limit the `Agent` tool is **withheld** from every subagent except a fork, where it stays
listed but errors on use (`sub-agents.md:862`).

At the session limit the Agent tool fails with `Subagent spawn limit reached`; `/clear` resets
the count (`sub-agents.md:899,901`). Counting toward it: nested subagents, forks, background
subagents, subagents that a **workflow's agents** spawn with the Agent tool, and `/subtask`.
**Not** counting: `/fork` (separate background session), and agents a **workflow script** spawns
with `agent()` — workflows have their own per-run limit (`sub-agents.md:897`).

At the concurrent limit spawning fails with `Concurrent subagent limit reached` and Claude is
told not to retry. **Sessions with `ultracode` active are exempt — the limit is not enforced**
(`sub-agents.md:905`). A `/subtask` fork **takes a slot but is never blocked**, and **resuming**
a finished subagent takes a fresh slot without checking, so resumes can push the running count
past the limit (`sub-agents.md:909-910`). Workflow agents and **agent-team teammates follow
their own limits instead** (`sub-agents.md:912`).

**Tool filtering — two filters, and they bite differently in background vs foreground**
(`sub-agents.md:326-340`). Filter 1 removes from *every* subagent, even if listed in `tools`:
`Agent` (at the depth limit), `AskUserQuestion`, `EndConversation`, `EnterPlanMode`,
`ExitPlanMode` (unless `permissionMode: plan`), `ScheduleWakeup`, `TaskOutput`,
`WaitForMcpServers`, `Workflow`. Filter 2 applies to **background** subagents — which is the
default — and reduces the built-in set to exactly: `Read`, `Grep`, `Glob`, `Bash`, `PowerShell`,
`Edit`, `Write`, `NotebookEdit`, `WebFetch`, `WebSearch`, `TodoWrite`, `Skill`, `ToolSearch`,
`EnterWorktree`, `ExitWorktree`, `Monitor`, `TaskStop`, `SendMessage`, `Artifact` (every MCP
tool is kept). **The same definition therefore resolves to different tools in the foreground and
the background, and the removal is silent.** Forks skip both filters. Teammates additionally
keep `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `CronCreate`, `CronDelete`, `CronList`
(`sub-agents.md:340`).

> **Consequence for a 9-role team:** if you rely on `AskUserQuestion` inside a delegated agent,
> it is not there — filter 1 removes it unconditionally. This repo's
> `.claude/rules/clarify-before-acting.md` makes "always use the AskUserQuestion **tool**" an
> unconditional rule, and the guard at `ask_quality.py` policies its shape. A subagent cannot
> comply. See Part 2.

### Table B — Environment variables

**Enumerated by shape, not by expectation.** `grep -oE '\b[A-Z][A-Z0-9_]{4,}\b'` over live
`env-vars.md` yields **329** distinct uppercase tokens; the agent-relevant subset below was
then filtered from that full set plus the same shape-grep over `sub-agents.md`,
`agent-teams.md`, `workflows.md`, `model-config.md`, `settings.md` and `agent-view.md`.
All rows cite live `https://code.claude.com/docs/en/env-vars.md` unless noted.

#### B1 — Gate variables (turn a capability on or off)

| Variable | Default | Effect / behaviour at the limit | Min ver |
|---|---|---|---|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | **unset = teams OFF** | `1` enables agent teams. Without it: **no team is set up at session start, no team directories are written, and Claude does not spawn or propose teammates** (`agent-teams.md:10`). This is the single load-bearing switch. | — |
| `CLAUDE_CODE_FORK_SUBAGENT` | server-side rollout | `1` lets Claude spawn `fork` subagents (inherit full parent context); `0` disables **everywhere including any server-side rollout**. `/subtask` works without it. A fork can't spawn further forks (`sub-agents.md:1054`). | — |
| `CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS` | unset | `1` removes the built-in Explore and Plan subagents; Claude searches directly instead. **Custom subagents named `Explore`/`Plan` are unaffected.** | v2.1.198 |
| `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS` | unset | `1` removes *all* built-in subagent types. **Only applies in non-interactive mode (`-p`)** — inert in an interactive session. | — |
| `CLAUDE_CODE_DISABLE_AGENT_VIEW` | unset | `1` turns off background agents + agent view: `claude agents`, `--bg`, `/background`, the on-demand supervisor. Equivalent to the `disableAgentView` setting. | — |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | unset | `1` disables **all** background task functionality — including `run_in_background` on Bash **and subagent tools**, auto-backgrounding, and Ctrl+B. Since subagents default to background as of v2.1.198, this materially changes delegation. | — |
| `CLAUDE_CODE_DISABLE_WORKFLOWS` | unset | `1` disables Workflows. Equivalent to `disableWorkflows`. | — |
| `CLAUDE_CODE_ENABLE_TASKS` | **`1` (Task tools are the default)** | `0` reverts to legacy `TodoWrite`. Task tools = `TaskCreate`/`TaskUpdate`/`TaskGet`/`TaskList` — the shared task list agent teams coordinate through. | default since v2.1.142 |
| `CLAUDE_CODE_DISABLE_CRON` | unset | `1` disables scheduled tasks: `/loop` and the cron tools go away and **already-running tasks stop mid-session**. Teammates otherwise keep `CronCreate`/`CronDelete`/`CronList`. | — |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | unset | `1` disables auto memory — **and with it the subagent `memory` frontmatter field entirely** (`sub-agents.md:518`). `0` forces it on even under `--bare` / `autoMemoryEnabled: false`. | — |
| `CLAUDE_CODE_ENABLE_AUTO_MODE` | — | **INERT.** "Accepted for compatibility with older releases and **has no effect**." Auto mode is available by default on every provider. Was required v2.1.158–2.1.206. | — |
| `CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT` | unset | `1` enables appending text to **every** subagent system prompt, including nested ones. `--append-subagent-system-prompt` sets it automatically. | v2.1.205 |
| `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT` | unset | `1` emits subagent text + thinking blocks in `claude -p --output-format stream-json`. Unlike the flag, the variable is **silently ignored** outside that mode so process-wide setting is safe. | v2.1.211 |
| `CLAUDE_CODE_DISABLE_ADVISOR_TOOL` | unset | `1` disables the advisor tool; `/advisor` unavailable, `advisorModel` ignored, `--advisor` accepted-but-no-op. | — |

#### B2 — Numeric limits (what happens at the limit is the load-bearing part)

| Variable | Default | At the limit | Parse behaviour | Min ver |
|---|---|---|---|---|
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | **3** | Agent tool is **withheld** from subagents at depth (a fork keeps it listed but it errors). Set `1` to turn nesting off. | positive whole number in **plain digits**; anything else ignored → **the limit can be adjusted but never removed** | var v2.1.217; default 3 since **v2.1.219** (was 1 in 217–218, was 5 and unchangeable in 2.1.172–216) |
| `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | **200** | Agent tool fails `Subagent spawn limit reached`; error tells Claude to finish the work itself. `/clear` resets. | positive whole number, **no upper bound**; **does not accept scientific notation or digit separators**; anything else ignored | v2.1.212 |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | **20** | Spawn fails `Concurrent subagent limit reached`, Claude told not to retry; succeeds again when the count drops. **Sessions with `ultracode` active are exempt.** | positive whole number; anything else ignored → cap adjustable, not disable-able | v2.1.217 |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | **10** | Max read-only tools **and subagents** executing in parallel. Distinct from the 20-cap: this is the parallel-execution scheduler, that is the spawn gate. | — | — |
| `CLAUDE_CODE_MAX_TURNS` | uncapped | Caps agentic turns when no explicit limit is passed. `--max-turns` takes precedence. **A non-positive-integer value is rejected at startup with an error**, not silently treated as "no cap". | strict | — |
| `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` | **8** | Max consecutive times a `Stop`/`SubagentStop` hook may block a turn before Claude Code **overrides it and ends the turn anyway**. `0` disables the cap. | — | — |
| `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` | **1500 ms** | Budget for `SessionEnd` hooks; auto-raised to the highest per-hook `timeout` in settings files, **capped at 60 s**. **Plugin hook timeouts do NOT raise the budget.** Applies to exit, `/clear`, and `/resume` switching. | — | — |
| `CLAUDE_CODE_TEAM_TEARDOWN_PARK_TIMEOUT_MS` | **10000** | How long a **non-interactive** session waits at exit for its team to tear down. Accepts **1000–60000**; out-of-range is ignored and the default applies. | range-clamped-by-rejection | v2.1.206 |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | model default | Per-agent context budget; each teammate/subagent has its own window. | — | — |

#### B3 — Model / effort routing

| Variable | Default | Effect | Min ver |
|---|---|---|---|
| `CLAUDE_CODE_SUBAGENT_MODEL` | unset | The model for **all subagents, agent teams, AND workflow agents** — one variable covers all three execution modes. **Highest precedence**: beats the per-invocation `model` param and the definition's `model` frontmatter. Setting it to `inherit` == leaving it unset (as of v2.1.196; before that `inherit` was an override). | — |
| `CLAUDE_CODE_EFFORT_LEVEL` | model default | `low`\|`medium`\|`high`\|`xhigh`\|`max`\|`auto`. **Takes precedence over `/effort` and the `effortLevel` setting.** | — |
| `CLAUDE_CODE_ALWAYS_ENABLE_EFFORT` | unset | `1` sends the effort parameter even for unrecognised model IDs (LLM gateways). Models that reject it at the API are still excluded so requests don't fail. | — |

Model allowlisting: an org `availableModels` allowlist is checked against the env var, the
per-invocation parameter **and** the frontmatter; a value resolving to an excluded model is
**skipped silently** and the subagent runs on the inherited model instead
(`sub-agents.md:314`).

#### B4 — Coordination / process hygiene

| Variable | Default | Effect | Notes |
|---|---|---|---|
| `CLAUDE_CODE_TASK_LIST_ID` | session-derived | Share one task list **across sessions** — set the same ID in several Claude Code instances to coordinate. The only documented cross-session coordination primitive besides teams. | — |
| `CLAUDE_CODE_CHILD_SESSION` | set to `1` by CC itself | Set in subprocesses CC spawns via Bash, PowerShell, Monitor, **hook commands**, and statusline commands. **Not** set for stdio MCP subprocesses. Unlike `CLAUDECODE`, only CC sets it, so it reliably distinguishes a nested session. | Useful to make a hook behave differently inside a subagent's Bash |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` | unset | `1` strips Anthropic + cloud-provider credentials from subprocess envs (Bash tool, hooks, MCP stdio). Parent keeps them. On Linux also isolates the PID namespace, **as a side effect breaking `ps`/`pgrep`/`kill` against host processes**. | Directly relevant to this repo's 50-credentials-in-every-child posture |
| `CLAUDE_CODE_SCRIPT_CAPS` | unset | JSON `{"substring": limit}` capping per-session script invocations — **only when `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is set.** Substring-matched. **`xargs`/`find -exec` fan-out is NOT detected** — defence in depth, not a boundary. | Gated on another var, an easy inert-setting trap |

### Table C — `settings.json` keys

**Enumerated by shape**, not by expectation: `grep -oE '^\| \`[a-zA-Z][a-zA-Z0-9_.]*\`'` over
live `settings.md` yields **211** distinct keys. The agent/team-relevant subset follows.
Citations are live `https://code.claude.com/docs/en/settings.md`.

#### C0 — Precedence (settings.md:659–691)

Highest to lowest:

| # | Scope | File |
|---|---|---|
| 1 | **Managed** | server-managed / MDM / `managed-settings.json` — **cannot be overridden by anything, including CLI args** |
| 2 | Command line | `--settings <file-or-json>` |
| 3 | Local project | `.claude/settings.local.json` |
| 4 | Shared project | `.claude/settings.json` |
| 5 | User | `~/.claude/settings.json` |

Within the managed tier only **one** source wins and the rest are ignored rather than merged:
`policyHelper` output > remote > MDM/OS policy > file-based > HKCU registry (`settings.md:664`).

**Merge semantics are per-type and there are two exceptions** (`settings.md:696-701`):
scalars from a higher scope override; **arrays concatenate and deduplicate across scopes**, so a
lower scope can *add* to `permissions.allow` that a higher scope set. The exceptions are
`fallbackModel` (ordered chain — highest-precedence file supplies the whole value) and
`availableModels` (a managed definition applies as-is and lower scopes cannot extend it).

**Settings reload without a restart** for most keys, including `permissions`, `hooks` and
`apiKeyHelper`, across user/project/local/managed, and a `ConfigChange` hook fires per detected
change (`settings.md:177`). Verify what actually loaded with `/status` → `Setting sources`; a
file with broken JSON **does not appear at all** (`settings.md:172,704`).

#### C1 — Team and subagent keys

| Key | Default | What it does | Settable where | Notes |
|---|---|---|---|---|
| `teammateMode` | **`in-process`** | Teammate display: `in-process`, `auto`, `tmux`, `iterm2`. | any scope; `--teammate-mode` overrides for one session | Default changed **from `auto` in v2.1.179** — an upgraded session that used to open split panes now stays in one terminal. `iterm2` added v2.1.186 and needs the `it2` CLI. |
| `teammateDefaultModel` | unset | Default model for teammates when the spawn prompt doesn't name one. **`null` = inherit the lead's `/model`.** | any scope; `/config` → "Default teammate model" | **Teammates do NOT inherit the lead's `/model` by default** (`agent-teams.md:141`) — this key is how you make them. |
| `agent` | unset | Run the **main thread** as a named subagent, and set the default agent for sessions dispatched from `claude agents`. Applies that subagent's system prompt, tool restrictions **and model**. | any scope | The system prompt **replaces** the default CC system prompt entirely (`sub-agents.md:737`). `initialPrompt` frontmatter only fires on this path. |
| `disableAgentView` | `false` | Turns off background agents + agent view: `claude agents`, `--bg`, `/background`, the on-demand supervisor. | any scope, "typically managed" | ≡ `CLAUDE_CODE_DISABLE_AGENT_VIEW=1` |
| `disableWorkflows` | `false` | Disables dynamic workflows + bundled workflow commands. | any scope | ≡ `CLAUDE_CODE_DISABLE_WORKFLOWS=1` |
| `workflowSizeGuideline` | **`medium`** | Agent count Claude aims for in workflows it writes. `unrestricted`\|`small`\|`medium`\|`large`. | any scope | **Advice to the model, NOT an enforced cap.** Requires **v2.1.219**; on 2.1.202–218 it must be set in `/config` instead — setting it in JSON on an older build is inert. |
| `workflowKeywordTriggerEnabled` | `true` | Whether typing `ultracode` in a prompt triggers a dynamic workflow. | any scope | Trigger keyword was `workflow` before v2.1.160. |
| `ultracode` | — | ⚠️ **NOT READ FROM `settings.json` AT ALL.** Only via `/effort ultracode`, `--settings`, or an SDK control request; `claude --effort ultracode` (v2.1.203+) to start with it on. | **nowhere in a settings file** | A textbook inert setting: writing it into `.claude/settings.json` looks correct and does nothing. Matters because **ultracode sessions are exempt from the 20-concurrent-subagent cap.** |
| `effortLevel` | model default | Persists effort across sessions: `low`\|`medium`\|`high`\|`xhigh`. | any scope | `--effort` and `CLAUDE_CODE_EFFORT_LEVEL` **override it**. Note the settings key does **not** accept `max`, while the env var and frontmatter `effort` do. |
| `env` | `{}` | Environment variables injected into the session — **this is how every Table B variable is set declaratively.** | any scope | The only file-based route to `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. |
| `model` / `fallbackModel` / `availableModels` | — | Session model, overload chain (max 3), org allowlist. | any scope (`availableModels` also managed) | `availableModels` is checked against subagent frontmatter/env/param and an excluded value is **silently skipped** (`sub-agents.md:314`). |
| `permissions.defaultMode` | `default` | `default`\|`acceptEdits`\|`plan`\|`auto`\|`dontAsk`\|`bypassPermissions`\|`manual`. | any scope **except**: `auto` is **ignored in project and local settings** so a repo can't grant itself auto mode — set it in `~/.claude/settings.json` | `--permission-mode` overrides for one session. `manual` needs v2.1.200. Teammates start from the **lead's** mode; you cannot set per-teammate modes at spawn (`agent-teams.md:263,428`). |
| `permissions.deny` | `[]` | `Agent(<name>)` entries block a specific subagent type — built-in or custom. Denying the bare `Agent` tool blocks **all** delegation. | any scope (arrays merge across scopes) | `sub-agents.md:590,87` |
| `disableBypassPermissionsMode` | unset | `"disable"` blocks `bypassPermissions` and `--dangerously-skip-permissions`. | **any scope**, typically managed | Relevant because a lead in `bypassPermissions` propagates it to **every** teammate (`agent-teams.md:263`). |
| `autoMemoryEnabled` | `true` | Auto memory on/off. | any scope | **Turning it off silently disables every subagent's `memory` frontmatter field** (`sub-agents.md:518`). |
| `autoMemoryDirectory` | `~/.claude/…` | Custom auto-memory location. | user; from **project/local only after accepting workspace trust** | — |
| `hooks` | `{}` | Session-wide hooks — **these fire inside subagents too**, including `PreToolUse` before every subagent tool call. | any scope + plugins + managed | `sub-agents.md:615`. This is the mechanism by which this repo's guard binds teammates. |
| `disableAllHooks` | `false` | Kills all hooks and any custom statusline. | any scope | — |
| `skills` | — | Skill directories. | — | Teammates load skills from **project and user settings, the same as a regular session** — the agent definition's `skills:` field is ignored on that path (`agent-teams.md:258`). |
| `skillOverrides` | `{}` | Per-skill visibility: `on`\|`name-only`\|`user-invocable-only`\|`off`. | `/skills` writes to `.claude/settings.local.json` | **Does not apply to plugin skills.** |
| `strictPluginOnlyCustomization` | unset | Array locking a surface to plugin+managed sources only. With `"agents"` locked, `~/.claude/agents/` and `.claude/agents/` are **skipped entirely** (`settings.md:1186`). | managed-ish | The one key that can make every project agent definition vanish. |
| `askUserQuestionTimeout` | `"never"` | Idle time before an unanswered `AskUserQuestion` auto-continues: `60s`\|`5m`\|`10m`\|`never`. | **user settings only — not read from project or local** | v2.1.200+. Note subagents never see this tool at all (filter 1). |
| `cleanupPeriodDays` | `30` | Retention for session files — **and the agent-team task list under `~/.claude/tasks/{team}/`** (`agent-teams.md:235`). Minimum 1; `0` is a validation error. | any scope | Also governs orphaned-worktree removal. |
| `plansDirectory` | `~/.claude/plans` | Where plan files go. | any scope | Relevant to the teammate plan-approval flow. |
| `worktree.baseRef` | **`fresh`** (= `origin/<default-branch>`) | Which ref new worktrees branch from. `head` = current local HEAD. **Applies to `--worktree`, the `EnterWorktree` tool, AND subagent `isolation: worktree`.** | any scope | This is why `isolation: worktree` branches from the default branch, not the parent's HEAD — and why an agent-team member on a feature branch gets a worktree **without the branch's commits** unless you set `"head"`. |
| `worktree.bgIsolation` | **`worktree`** | Background sessions are **blocked from `Edit`/`Write` in the main checkout until `EnterWorktree` is called**. `none` lets them edit in place. | any scope | v2.1.143+. |
| `worktree.sparsePaths` / `worktree.symlinkDirectories` | none | Sparse-checkout dirs / dirs symlinked from the main repo into each worktree. | any scope | Sparse worktrees enable `extensions.worktreeConfig` in the shared `.git/config` — a repo-wide side effect. |
| `agentPushNotifEnabled` | `false` | Proactive push to phone when Remote Control is connected. | any scope | v2.1.119+. |

### Table D — Which frontmatter field applies in which execution mode

Three modes: **S** = plain subagent (Agent tool / @-mention), **T** = agent-team teammate
referencing a subagent definition, **W** = agent inside a dynamic Workflow script.

Legend: `DOCUMENTED-APPLIES` / `DOCUMENTED-IGNORED` / `UNDOCUMENTED`. **No cell is guessed.**
Where a cell is UNDOCUMENTED, the settling experiment is given below the table.

| Field | S (subagent) | T (teammate) | W (workflow agent) |
|---|---|---|---|
| body / system prompt | **DOCUMENTED-APPLIES** — *replaces* the CC system prompt (`sub-agents.md:261`) | **DOCUMENTED-APPLIES, but APPENDED not replaced** (`agent-teams.md:255`) | **UNDOCUMENTED** — D1 |
| `name` | DOCUMENTED-APPLIES (`sub-agents.md:279`) | DOCUMENTED-APPLIES — recorded as the member's agent type in team config (`agent-teams.md:241`) | **UNDOCUMENTED** — D1 |
| `description` | DOCUMENTED-APPLIES | **UNDOCUMENTED** — the lead names the type explicitly, so the auto-delegation description may be unused — D2 | **UNDOCUMENTED** — D1 |
| `tools` | DOCUMENTED-APPLIES (`sub-agents.md:281`), narrowed by both filters (`:326-338`) | **DOCUMENTED-APPLIES** (`agent-teams.md:255`) — **but `SendMessage`, the task tools and the cron tools are force-added regardless** (`agent-teams.md:255`, `sub-agents.md:340`) | **DOCUMENTED-IGNORED-ish**: workflow agents "inherit your tool allowlist" (`workflows.md:179`); per-definition `tools` is not mentioned — D1 |
| `disallowedTools` | DOCUMENTED-APPLIES, resolved *before* `tools` (`sub-agents.md:362`) | **UNDOCUMENTED** — only `tools` is named — D3 | **UNDOCUMENTED** — D1 |
| `model` | DOCUMENTED-APPLIES, 3rd in precedence (`sub-agents.md:305-310`) | **DOCUMENTED-APPLIES** (`agent-teams.md:255`). Overridden by `CLAUDE_CODE_SUBAGENT_MODEL`, which explicitly covers teams (env-vars, `CLAUDE_CODE_SUBAGENT_MODEL`) | **DOCUMENTED-IGNORED by default**: "Every agent in a workflow uses your session's model unless the script routes a stage to a different one or `CLAUDE_CODE_SUBAGENT_MODEL` is set, which overrides both" (`workflows.md:359`) |
| `permissionMode` | DOCUMENTED-APPLIES, **unless** the parent is `bypassPermissions`/`acceptEdits`/`auto` (`sub-agents.md:467`). Ignored for plugin subagents | **DOCUMENTED-IGNORED**: "Teammates start with the lead's permission settings… you can't set per-teammate modes at spawn time" (`agent-teams.md:263,428`) | **DOCUMENTED-IGNORED**: "The subagents the workflow spawns **always run in `acceptEdits`** mode… regardless of your session's mode" (`workflows.md:179`) |
| `skills` | DOCUMENTED-APPLIES (`sub-agents.md:286`) | **DOCUMENTED-IGNORED** — explicit: "The `skills` and `mcpServers` frontmatter fields… are **not applied** when that definition runs as a teammate. Teammates load skills and MCP servers from your project and user settings" (`agent-teams.md:258`) | **UNDOCUMENTED** — D1 |
| `mcpServers` | DOCUMENTED-APPLIES (`sub-agents.md:287`); ignored for plugin subagents | **DOCUMENTED-IGNORED** — same sentence (`agent-teams.md:258`) | **UNDOCUMENTED** — D1 |
| `hooks` | DOCUMENTED-APPLIES; needs workspace trust for project-scope as of v2.1.218 (`sub-agents.md:625`); ignored for plugin subagents | **UNDOCUMENTED** — the exclusion note names only `skills` and `mcpServers`, so `hooks` is neither confirmed nor excluded — D4 | **UNDOCUMENTED** — D1 |
| `memory` | DOCUMENTED-APPLIES; **inert if auto memory is off** (`sub-agents.md:518`) | **UNDOCUMENTED** — D5 | **UNDOCUMENTED** — D1 |
| `maxTurns` | DOCUMENTED-APPLIES (`sub-agents.md:285`) | **UNDOCUMENTED** — a teammate is a full session, not a bounded turn budget — D6 | **UNDOCUMENTED** — D1 |
| `effort` | DOCUMENTED-APPLIES, overrides session effort (`sub-agents.md:291`) | **CONFLICT / UNDOCUMENTED**: "Teammates **inherit the lead's effort level**" (`agent-teams.md:143`), and `/effort` while viewing a teammate applies to that teammate's later turns (`agent-teams.md:167`). Whether a definition's `effort` beats inheritance is unstated — D7 | **UNDOCUMENTED** — D1 |
| `background` | DOCUMENTED-APPLIES; default is background as of v2.1.198 (`sub-agents.md:290`) | **DOCUMENTED-IGNORED for the teammate itself** (a teammate is a separate session, not a background task) — **and an in-process teammate's OWN subagents cannot be backgrounded at all: "Asking for a background one, whether with `run_in_background` or a subagent definition that sets `background: true`, returns an error"** (`agent-teams.md:426`) | **UNDOCUMENTED** — workflow agents run in the background by construction (`workflows.md:13`) — D1 |
| `isolation` | DOCUMENTED-APPLIES; branches from `worktree.baseRef` (default the **default branch**), not the parent HEAD (`sub-agents.md:292`, `settings.md worktree.baseRef`) | **UNDOCUMENTED** — D8 | **UNDOCUMENTED** — D1 |
| `color` | DOCUMENTED-APPLIES (`sub-agents.md:293`) | **UNDOCUMENTED** — D9 | **UNDOCUMENTED** — D1 |
| `initialPrompt` | **DOCUMENTED-IGNORED as a plain subagent** — the field fires "when this agent runs as **the main session agent** (via `--agent` or the `agent` setting)" (`sub-agents.md:294`) | **UNDOCUMENTED** — a teammate is a full session but is not launched via `--agent`; the field's scoping clause suggests no, but the docs do not say — D10 | **UNDOCUMENTED** — D1 |

#### The settling experiments

Each is a single observable check. Run with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` where a
teammate is involved.

- **D1 (whole W column).** The public docs never state that a workflow `agent()` call can
  reference a **subagent definition** at all — `workflows.md:300` documents only
  `agent(prompt, {label})`, and the SDK `WorkflowInput` schema
  (`$CC/agent-sdk__typescript.md:2484`) exposes only `script`/`name`/`scriptPath`/`args`/
  `resumeFromRunId`. **Experiment:** ask Claude for a workflow whose script calls
  `agent('…', { agentType: 'staleness-auditor' })`, then read the persisted script under
  `~/.claude/projects/<session>/` and the run's `transcriptDir` to see whether the agent booted
  with that definition's system prompt. If `agentType` is not an accepted option, the whole W
  column collapses to "definitions do not apply; workflows take prompts, not agent types."
- **D2 `description` on T.** Define two agents whose only difference is `description`, spawn a
  teammate by type name, and ask it to print its own system prompt preamble. If the description
  text appears, it applies.
- **D3 `disallowedTools` on T.** Define an agent with `tools: Read, Bash` and
  `disallowedTools: Bash`; spawn it as a teammate and tell it to run `echo hi`. Denied ⇒ applies.
- **D4 `hooks` on T.** Give the definition a `PreToolUse` hook on `Bash` that exits 2 with a
  distinctive message; spawn as a teammate and have it run any Bash command. The message
  appearing ⇒ applies.
- **D5 `memory` on T.** Definition with `memory: project`; spawn as a teammate and tell it to
  write a note to its memory. Check whether `.claude/agent-memory/<name>/` is created.
- **D6 `maxTurns` on T.** Definition with `maxTurns: 2`; give the teammate a task needing five
  tool calls. Stopping after two ⇒ applies.
- **D7 `effort` on T.** Set the lead to `/effort low` and the definition to `effort: max`. Spawn
  the teammate, then read `~/.claude/teams/<team>/config.json` and the teammate's transcript for
  the effort actually sent. (This is the one cell where the docs actively point the other way —
  treat "inherits the lead" as the working assumption until measured.)
- **D8 `isolation` on T.** Definition with `isolation: worktree`; spawn as a teammate and have it
  print `git rev-parse --show-toplevel`. A path under the worktree root ⇒ applies.
- **D9 `color` on T.** Definition with `color: pink`; spawn and look at the agent panel row.
- **D10 `initialPrompt` on T.** Definition with `initialPrompt: "Say PINEAPPLE first."`; spawn as
  a teammate with an unrelated task. `PINEAPPLE` in its first turn ⇒ applies.

#### Mode-level facts that are not frontmatter but change team design

| Fact | S | T | W |
|---|---|---|---|
| Loads `CLAUDE.md` | Yes, except built-in Explore/Plan which skip it (`sub-agents.md:33`) | **Yes** — "teammates read `CLAUDE.md` files from their working directory" (`agent-teams.md:432`) and load "the same project context as a regular session: CLAUDE.md, MCP servers, and skills" (`agent-teams.md:271`) | UNDOCUMENTED |
| Inherits lead's conversation history | No | **No** (`agent-teams.md:271`) | No — script variables hold intermediate results (`workflows.md:308`) |
| Can spawn its own workers | Yes, to depth 3 | **No nested teams** (`agent-teams.md:425`); it *can* spawn subagents, but **never background ones** (`:426`) | Its Agent-tool spawns count against the 200 session cap (`sub-agents.md:897`) |
| Concurrency cap | 20 (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), ultracode exempt | **Own limits, unspecified** — "agent team teammates follow their own limits instead" (`sub-agents.md:912`); the docs give only *advice*: start with 3–5 (`agent-teams.md:340`) | **16 concurrent, 1,000 total per run** (`workflows.md:322-323`) — hard runtime caps |
| Session-total cap | 200 | not stated | 1,000/run; `agent()` calls **do not** count against the 200 (`sub-agents.md:897`) |
| Survives `/resume` | n/a | **No** — "`/resume` and `/rewind` do not restore in-process teammates" (`agent-teams.md:421`) | Resumable **same session only** via `resumeFromRunId`; replay re-runs every agent started after the first unfinished one (`workflows.md:336`) |
| Permission prompts | surface in the main session, naming the subagent (v2.1.186+) | **surface in the LEAD session** — approve them there (`agent-teams.md:267`) | can pause a run mid-flight; **there is no other mid-run user input** (`workflows.md:320`) |

---

## Part 2 — Audit of this project

Files read: `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude/settings.json`,
`.claude/agents/*.md`, `.claude/CLAUDE.md`, `AGENTS.md`, all 23 `.claude/rules/*.md`,
`python/src/dotfiles_setup/hook_guard.py`, `scripts/graphify-hook-guard.sh`.
**No managed settings tier exists on this host** — `/Library/Application Support/ClaudeCode/`
does not exist, so precedence tier 1 is empty and project settings are the effective ceiling.

Version check: `claude --version` → **2.1.221**, which is the newest release
(`gh api repos/anthropics/claude-code/releases` → `v2.1.221` published 2026-08-04T00:14:23Z).
Every "requires vX" note in Part 1 is therefore satisfied.

### 2.0 A live measurement of Table D, taken from inside this report

**This agent is running as an agent-team teammate in the session that commissioned the report.**
Its own tool inventory is a direct observation of what a teammate gets — the D-column cells the
docs leave open. Reading the tool list in this agent's own system prompt:

- **Present:** `Agent`, `Artifact`, `Bash`, `Edit`, `Read`, `Skill`, `ToolSearch`, `Write`, plus
  deferred `NotebookEdit`, `WebFetch`, `WebSearch`, `Monitor`, `EnterWorktree`, `ExitWorktree`,
  `TaskStop`, `SendMessage`, `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `CronCreate`,
  `CronDelete`, `CronList`, and every MCP tool.
- **Absent:** `AskUserQuestion`, `EnterPlanMode`, `ExitPlanMode`, `ScheduleWakeup`, `TaskOutput`,
  `WaitForMcpServers`, `Workflow`.

That set is **exactly** filter 2's background built-in list (`sub-agents.md:338`) plus the task
and cron tools teammates additionally keep (`sub-agents.md:340`), minus filter 1's removals
(`sub-agents.md:326-336`). So: **a teammate runs with the BACKGROUND tool set, not the
foreground one** — a fact neither `agent-teams.md` nor `sub-agents.md` states outright.

One discrepancy, reported as observed rather than explained: `EndConversation` **is** offered
(deferred) to this teammate, while filter 1 lists it as removed from every subagent. Either
teammates are exempt from that one removal, or the tool is listed-but-erroring the way `Agent` is
for a fork. Not settled here.

**Caveat and control arm.** This is n=1, self-observed, on 2.1.221 with this repo's settings. The
control arm is that the *absences* are not a generic empty list — `Agent`, `SendMessage` and the
task tools **are** present, so the inventory discriminates. Confirm on a second session before
building on it.

### 2.1 What is already set, and where

| Setting | User `~/.claude/settings.json` | Project `.claude/settings.json` | Local `.claude/settings.local.json` | Effective | Verdict |
|---|---|---|---|---|---|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `"1"` | `"1"` | — | `1` | ✅ **Agree.** Teams are on. Redundant but harmless — project wins and says the same thing. |
| `CLAUDE_CODE_FORK_SUBAGENT` | `"1"` | — | — | `1` | ✅ Forks enabled session-wide. Note a fork **inherits the full parent context** and reuses its prompt cache (`sub-agents.md:1048`) — the cheapest way to hand a teammate the lead's context, and the only path that skips both tool filters. |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | — | `"1"` | — | `1` | ✅ Loads `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md` and `CLAUDE.local.md` from `--add-dir` directories. With `knowledge-base` and `macos-development-environment` both added, **every teammate inherits three repos' rule sets.** See 2.4 — this is a real context cost multiplied by 9. |
| `teammateMode` | `"tmux"` | `"auto"` | — | **`auto`** | ⚠️ **CONFLICT — project silently overrides the user's explicit choice.** Precedence is project (4) > user (5). `"tmux"` means "split panes, auto-detecting tmux or iTerm2"; `"auto"` means "split panes **only if already inside** a tmux session, or iTerm2 with `it2` on PATH — otherwise fall back to in-process". So a plain-terminal launch gets in-process teammates even though user settings asked for tmux panes. Fix by removing the project key or matching it. |
| `permissions.defaultMode` | `"auto"` | — | — | `auto` | ✅ **Correct scope.** `auto` is *ignored* in project and local settings by design (`settings.md defaultMode`), so it had to be at user scope, and it is. Consequence: **every teammate starts in auto mode** (`agent-teams.md:263`), and a teammate's own `permissionMode` frontmatter is then **ignored entirely** — "the subagent inherits auto mode and any `permissionMode` in its frontmatter is ignored" (`sub-agents.md:467`). |
| `agentPushNotifEnabled` | `true` | — | — | `true` | ✅ Long-running teammate completion notifications reach the phone. |
| `hooks.PreToolUse` (guard) | — | 3 entries | — | all 3 | ✅ Fires inside every teammate — `settings.json` hooks apply in subagents (`sub-agents.md:615`). See 2.4. |
| `permissions.allow` | 22 rules | 7 MCP rules | 103 rules | **all 132, merged** | ✅ Arrays **concatenate and deduplicate across scopes** (`settings.md:696`), so the local allowlist is live for teammates too. This directly serves `agent-teams.md:393` ("pre-approve common operations before spawning teammates"). |
| `permissions.additionalDirectories` | — | `knowledge-base` | `macos-development-environment` | both | ✅ merged. |
| `enabledPlugins` | 15 entries | 21 entries | 2 entries | project wins per key | ⚠️ Three-way overlap; `explanatory-output-style` and `learning-output-style` are `true` in project and `false` in local — **local wins (tier 3 > tier 4), so they are OFF.** Deliberate or not, the project file's `true` is dead. |
| `skillOverrides` | — | — | 13 skills `"off"` | 13 off | ✅ Applies to teammates via user/project settings — note **teammates load skills from settings, not from an agent definition's `skills:` field** (`agent-teams.md:258`). |

### 2.2 Set but INERT — the failure mode this repo has a history of

Each verified with a **control arm**: grep live `settings.md` / `env-vars.md` for the key, and
grep for a key known to be present with the identical command shape.

| Item | Where | Evidence | Verdict |
|---|---|---|---|
| `ENABLE_CLAUDEAI_MCP_SERVERS: "false claude"` | `~/.claude/settings.json` env | Doc: "Set to **`false`** to disable claude.ai MCP servers… Enabled by default for logged-in users." The value here is the seven-character string `false claude`, not `false`. | 🔴 **INERT — and it fails in the permissive direction.** The evident intent was to disable claude.ai MCP servers; a value that isn't `false` almost certainly leaves them **enabled**. Looks like a shell paste accident (`false` + a stray `claude`). Not mine to fix — flagging only, per `feedback_no_user_level_file_updates`. Verify with `/mcp` or `claude mcp list`, and prefer the documented per-project alternative `disableClaudeAiConnectors`. |
| `autoDreamEnabled: true` | `~/.claude/settings.json` | **0 hits** in live `settings.md`. Control arm: `teammateMode` → 1 hit, `skipDangerousModePermissionPrompt` → 1 hit, `remoteControlAtStartup` → 1 hit with the same command shape. | 🟡 **Undocumented key.** Either a removed feature or never-public. Assume inert. |
| `skipWorkflowUsageWarning: true` | `~/.claude/settings.json` | **0 hits**, same control arm. Live `workflows.md:354` says the token warning is governed by "two settings" but names them elsewhere. | 🟡 Undocumented; likely superseded. If the goal is fewer workflow warnings, the documented lever is `workflowSizeGuideline`. |
| `skipAutoPermissionPrompt: true` | `~/.claude/settings.json` | **0 hits**, same control arm. | 🟡 Undocumented. |
| `CLAUDE_CODE_BRIEF: "1"` | `~/.claude/settings.json` env | **0 hits** across *every* live page fetched, not just `env-vars.md`. Control arm: `CLAUDE_CODE_NO_FLICKER` → found in `env-vars.md` **and** `settings.md`; `CLAUDE_CODE_NEW_INIT` → found. | 🟡 Undocumented env var. |
| `teammateMode: "auto"` | `.claude/settings.json` | Documented and live — but it **overrides** the user's `"tmux"`. | ⚠️ Not inert; it is the *user's* setting that is inert. Same class of defect, opposite direction. |
| Bundled `/verify` and `/code-review` skills | — | `sub-agents.md:487`: skills with `disable-model-invocation: true` **cannot be preloaded** via a definition's `skills:` field. | ℹ️ Constrains team design: a reviewer teammate cannot be given `/code-review` by preloading. Matches memory `feedback_protocol_verbs_are_user_invoked_only`. |

**One historical inert-lane claim is now CLEAR.** `.claude/CLAUDE.md` documents that the
fable-orchestrator "mode line is inert without the trigger" and that the trigger was added
2026-07-24. Both lines are present in `.claude/CLAUDE.md` today, so that specific defect is
fixed — it remains the right precedent for the class, not a live finding.

### 2.3 Absent, and what it costs a 9-role team

| Missing | Where it would go | Why it matters at 9 roles |
|---|---|---|
| `teammateDefaultModel` | user or project settings | **Teammates do NOT inherit the lead's `/model`** (`agent-teams.md:141`). Nothing here sets a default, so 9 teammates land on the harness default rather than a deliberate choice. At Opus-5 rates × 9 independent context windows this is the single largest unmanaged cost lever. Set `"sonnet"` for breadth roles, or `null` to explicitly follow the lead. |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | project `env` | Default 20. Fine for 9 teammates — **but teammates follow their own unspecified limits** (`sub-agents.md:912`), and this cap governs the *subagents those teammates spawn*. With nesting at depth 3 and 9 teammates each able to fan out, 20 is reachable. |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | project `env` | Default **3** as of v2.1.219 — this repo inherits it silently. A 9-role team where each role also nests 3 deep is a large, unbudgeted tree. Consider pinning `"2"` (or `"1"`) explicitly so a future default change doesn't move under you. Precedent: the default has changed **three times in five releases** (5 → 1 → 3). |
| `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | project `env` | Default 200. A long team session with fan-out can hit it; the failure is a hard `Subagent spawn limit reached` mid-run. |
| `worktree.baseRef` | project settings | **Default is `"fresh"` = `origin/<default-branch>`.** Any teammate or subagent given `isolation: worktree` branches from `origin/main`, **not from the working branch** — so on a feature branch it gets a tree without the branch's commits. For this repo, where all work must be on a branch (see 2.4), `"head"` is almost certainly the intended value. **Highest-value absent setting after `teammateDefaultModel`.** |
| `worktree.symlinkDirectories` | project settings | Each worktree duplicates the checkout. With `.venv`/`node_modules`/`graphify-out` this is expensive × N agents. |
| `workflowSizeGuideline` | project settings | Default `medium`. Requires v2.1.219 — satisfied at 2.1.221, so it is now settable from a file for the first time. |
| A team-role agent set in `.claude/agents/` | project | Only **2** definitions exist (`dockerfile-reviewer`, `staleness-auditor`) for a **9**-role team. Reusable roles are exactly what `agent-teams.md:239,247` says to use definitions for. |
| `~/.claude/agents/` | user scope | **The directory does not exist.** Beyond having no user-scope roles, `sub-agents.md:142` warns the watcher covers only directories that existed at session start — so the first agent file created there **will not be picked up without a restart**. Create the directory before the session that needs it. |
| `CLAUDE_CODE_TASK_LIST_ID` | — | Not needed for one team (a session has exactly one team), but it is the only documented way to share a task list across sessions if the design ever outgrows one lead. |

### 2.4 Conflicts between an agent team and this repo's own rules

Ordered by how hard each bites.

**1. 🔴 `AskUserQuestion` does not exist inside a teammate — but the rule requiring it is
unconditional.** `.claude/rules/clarify-before-acting.md` states *"Whenever you need input, use the
`AskUserQuestion` TOOL — never options in prose. This is the **mechanism** rule and it is
unconditional."* Filter 1 removes `AskUserQuestion` from every delegated agent
(`sub-agents.md:329`), and this teammate's own tool list confirms it is absent (§2.0). So **every
teammate is structurally incapable of obeying rule 2's mechanism**, and the only compliant move —
falling back to prose options — is what the rule forbids. The `ask_quality` gate never fires
because the tool is never called; the rule's own text concedes *"what no hook can see is an ask
that never happened."* **Resolution needed before a 9-role team ships:** state in the rule that a
teammate escalates by `SendMessage` to the lead, and that the **lead** owns every
`AskUserQuestion`. Today the rule reads as a requirement nine agents will violate silently.

**2. 🔴 The branch guard blocks a teammate's writes, and teammates share one checkout.**
`hook_guard.decide_payload` (`python/src/dotfiles_setup/hook_guard.py:793`) routes
`Edit`/`Write`/`NotebookEdit` to `branch_guard.decide`, denying writes to repo files while on the
default branch. Memory `project_session_2026-08-03-h` already records the exact failure: *"The
write guard blocks SUBAGENT report writes on `main` — branch BEFORE spawning."* At 9 teammates
this scales from an annoyance to a total loss, because `agent-report-persistence.md` requires each
findings-bearing agent to **persist verbatim at receipt** — nine simultaneous denials, each
discovered only after the work is done. **Mitigation is already correct here** (this session is on
`research/agent-team-design`) but it is a per-session precondition with no gate. Consider a
`SubagentStart` hook that refuses to start a writing teammate on the default branch, so the denial
lands *before* the work rather than after.

**3. 🟠 Teammates share the working directory — nothing isolates them.** `agent-teams.md:370`:
*"Two teammates editing the same file leads to overwrites."* There is no `worktree.bgIsolation`
equivalent for teammates and no per-teammate `isolation` documented (Table D, cell D8). Combined
with `worktree.baseRef` defaulting to `fresh` (§2.3), the two available isolation stories are both
unconfigured. For a 9-role team, **disjoint file ownership has to be enforced by the spawn prompt**,
because nothing in the config enforces it.

**4. 🟠 The PreToolUse guard runs on every tool call of every teammate — 9× the latency.**
`.claude/settings.json:28-59` wires **three** PreToolUse hook entries covering
`Bash|AskUserQuestion|Edit|Write|NotebookEdit`, `Bash|Grep`, and `Read|Glob` — so a Bash call
fires **two** hook processes and a Read fires one. Memory `project_session_2026-08-03-f` measures
the write guard at **~340 ms/edit** and flags reducing it as the next task. That cost is paid
independently in every teammate's process. Nine teammates doing read-heavy research multiply a
per-call tax that was measured for one session. This is a real, quantified reason to finish that
optimisation *before* scaling the team, not after.

**5. 🟠 The graphify nudge is injected into every teammate's every Bash/Grep/Read/Glob.**
`scripts/graphify-hook-guard.sh` emits `MANDATORY: graphify-out/graph.json exists. You MUST run
graphify query…` as PreToolUse `additionalContext`. Observed **7 times** in this single agent's
run. Multiplied across 9 teammates × a long session this is a nontrivial, entirely repeated
context spend — and for teammates working outside the graph's scope (like this one, reading vendor
docs in a sibling repo) it is pure noise. Consider scoping the matcher, or making the nudge
one-shot per agent.

**6. 🟡 `mise run ship` / `land` / `automerge` are single-writer verbs with no team story.**
`mise-tasks-only.md` redirects `gh pr create`/`merge` to `mise run ship`/`land`, and
`feedback_ship_gates_before_push_automerge_race` records that **once `ship` arms auto-merge the
branch is CLOSED** — a later push races the merge and was measured losing a fix on 2026-08-04
(#544 merged at the pre-fix SHA). With 9 teammates able to run Bash, **any teammate calling `ship`
ends the branch for all of them.** Nothing in the guard prevents a teammate from doing so. The
rule set assumes one writer; the team has nine. **Recommend: the spawn prompt forbids `ship`/`land`
outright and reserves both for the lead.**

**7. 🟡 MCP two-lane policy is already satisfied — and the mechanism is worth knowing.**
`do-not.md` #11 / `research-doc-sources.md` restrict MCP for our own lookups. Nothing here
registers a server for that purpose, and `project_mcp_json_exception` records `.mcp.json` as
empty. Note the team-specific mechanism: **a teammate's `mcpServers` frontmatter is ignored**
(`agent-teams.md:258`), so teammates get exactly the plugin-provided servers the session already
has — the lane-1 servers. No new exposure from going to 9 agents.

**8. 🟡 Zero-bash-logic constrains what a team can build, not how it runs.**
`zero-bash-logic.md` allowlists every `scripts/*.sh` with a per-file `max_lines` budget. Adding a
`SubagentStart`/`TeammateIdle` hook script (the natural way to enforce items 1 and 2 above) means
either an allowlist entry with justification or — the rule's stated default answer — putting the
logic in `python/` behind a thin wrapper, exactly as `pretooluse-guard.sh` already does. **Follow
the existing pattern; do not add a fourth bash script.**

**9. 🟡 `notepad-enforcement.md` names a single shared file.** All findings go to
`.agent/notepad.md`. Nine teammates appending to one file in one checkout is the file-conflict
case `agent-teams.md:370` warns about, and there is no locking (the harness locks *task claims*,
not files — `agent-teams.md:178`). Give each role its own notepad path, or route findings through
`agent-report-persistence.md`'s per-agent path
`docs/research/kb/reports/agents/<agent-name>.md`, which is already one-file-per-agent and
therefore conflict-free. This report follows that path.

**10. 🟢 Report persistence is correctly wired for teams already.**
`agent-report-persistence.md` rule 1b requires **incremental** persistence and puts the
requirement in the **agent definition** rather than the brief, citing two agents that died holding
everything in memory. `.claude/agents/staleness-auditor.md` carries it. Any new team-role
definition must carry the same line — and the brief for this task did too, which is why this file
was skeletoned first and appended section by section.

### 2.5 Recommended minimal diff

Nothing below is applied — this report edits only itself.

```jsonc
// .claude/settings.json
{
  "env": {
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2",   // pin it; default moved 5→1→3 in 5 releases
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "20"   // pin the value you actually want
  },
  "teammateDefaultModel": "sonnet",  // or null to follow the lead; today it is unset
  "worktree": {
    "baseRef": "head",               // else isolation:worktree branches off origin/main
    "symlinkDirectories": [".venv", "node_modules", "graphify-out"]
  }
  // REMOVE "teammateMode": "auto" — it overrides the user's "tmux"
}
```

Plus, outside settings: create `~/.claude/agents/` **before** the team session; give each of the 9
roles a definition carrying the incremental-persistence line; and resolve the
`clarify-before-acting` mechanism conflict (§2.4 item 1) in the rule text.

---

### 2.6 Control-armed absence sweep

Every "absent" claim in §2.3 re-run as one command across **all three** settings scopes
concatenated (`.claude/settings.json`, `.claude/settings.local.json`, `~/.claude/settings.json`),
same command shape for every row.

**Control arm:** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` with the identical grep returns **1 hit in
`.claude/settings.json` and 1 in `~/.claude/settings.json`**. The probe can therefore see a
present key, so a zero below is a real absence and not a blind probe.

| Setting | Occurrences across all 3 scopes | Default in force | Load-bearing at 9 roles? |
|---|---|---|---|
| `CLAUDE_CODE_SUBAGENT_MODEL` | **0** | unset | ⚠️ **Yes.** It is the *highest-precedence* model control and the only one that covers subagents, teammates **and** workflow agents in a single key. Unset means each of the three modes resolves separately. |
| `teammateDefaultModel` | **0** | unset | 🔴 **Yes — the biggest gap.** Teammates do not inherit the lead's `/model` (`agent-teams.md:141`), so nine windows land on the harness default by accident rather than choice. |
| `CLAUDE_CODE_EFFORT_LEVEL` / `effortLevel` | **0** / **0** | model default | ⚠️ Moderate. Teammates inherit the lead's effort (`agent-teams.md:143`), so the lead's `/effort` silently sets the bill for all nine. Pinning it makes that explicit. |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | **0** | **3** | ⚠️ Yes. Inherited silently, and this default moved **5 → 1 → 3 across v2.1.216–219**. Nine roles each nesting 3 deep is a large unbudgeted tree that a future default change can resize without a diff. |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | **0** | **20** | ⚠️ Yes. Teammates follow *their own unspecified limits* (`sub-agents.md:912`); this cap governs the subagents those nine teammates spawn, and 9 × fan-out reaches 20 easily. |
| `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | **0** | **200** | 🟡 Possible. Fails hard mid-run with `Subagent spawn limit reached`. |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | **0** | **10** | 🟡 Distinct from the 20-cap — this is the parallel-execution scheduler for read-only tools *and* subagents. On a research-heavy team it is the throughput ceiling that actually binds first. |
| `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` | **0** | **8** | 🟢 Low. Relevant only if a `TeammateIdle`/`SubagentStop` hook is added to enforce §2.4 items 1–2; then the cap is how many times that hook may push a teammate back to work before the harness overrides it. |
| `CLAUDE_CODE_TASK_LIST_ID` | **0** | session-derived | 🟢 Not needed — a session has exactly one team (`agent-teams.md:424`). It is only the escape hatch if the design ever outgrows one lead. |
| `workflowSizeGuideline` | **0** | **`medium`** | 🟢 Low, and newly settable: it requires **v2.1.219** and this host is on 2.1.221, so a file-based value would take effect for the first time. Advice to the model, not a cap. |
| `disableAgentView` | **0** | `false` (agent view ON) | 🟢 Correct as-is — background agents and `/background` stay available, which a team wants. |
| `autoMemoryEnabled` | **0** | **`true`** | 🟢 Correct as-is, and load-bearing in the *negative*: setting it `false` would silently disable the `memory:` frontmatter field on every role definition (`sub-agents.md:518`). Leave it alone. |

### 2.7 The Fable gate — a real live inert declaration

The lead asked specifically about `.claude/CLAUDE.md` § "Cross-vendor orchestration". **It is
inert on this session, by design, and the file says so.** The two lines are:

> *"When the session model is **Fable**, without being reminded: non-trivial implementation runs
> the fable-orchestrator architect-as-orchestrator flow…"*
> *"fable-orchestrator: implementation lane = codex"*

and the file's own commentary: *"The first line is the **trigger**, and it is Fable-gated by
design — sessions on other models read the condition and skip the flow. Default `/model` is
**Opus 5** for everyday work; switch to **Fable 5** deliberately to arm this flow."*

This session's model is `claude-opus-5[1m]`. The trigger's condition is false, so the lane
declaration does nothing here.

**My earlier §2.2 entry under-read this.** I recorded the historical defect as fixed — the mode
line had been present without a trigger until 2026-07-24, and the trigger is there now — and
stopped. That is true but answers a different question. The sharper finding, and the one that
matters for a team:

1. **The gate is model-scoped, and teammate models are unset.** Teammates do not inherit the
   lead's `/model` (`agent-teams.md:141`) and `teammateDefaultModel` is absent (§2.6). So even a
   lead deliberately on Fable 5 does **not** arm this flow in its teammates — each teammate
   resolves its own model, and any that lands off Fable reads the trigger and skips. A 9-role team
   would have to spawn roles on Fable explicitly for the declared lane to mean anything.
2. **All nine teammates load and pay for it regardless.** Teammates read `CLAUDE.md` from their
   working directory (`agent-teams.md:432`) and load the same project context as a regular session
   (`:271`). So the block is injected into nine context windows, where in eight-or-nine of them the
   condition is false.
3. **The cost is measured, not estimated.** `uv run --project python kb-setup md-budget` reports
   **51 instruction files, ~124,761 bytes (~31,190 tokens) of eager context every session** — for
   *this repo alone*. `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD: "1"`
   (`.claude/settings.json:3`) adds `CLAUDE.md`, `.claude/CLAUDE.md` and `.claude/rules/*.md` from
   both `--add-dir` repos on top, so ~31k tokens is a **floor**, not the total. Multiplied by nine
   independent teammates that is on the order of **280k+ tokens of eager instruction context
   before a single teammate does any work** — the concrete form of `agent-teams.md:284`'s warning
   that "token usage scales with the number of active teammates".

Not a recommendation to delete anything — the gate is correct and deliberate. The point is that
**eager instruction context is the one cost that multiplies by team size**, and this repo's eager
corpus is now large enough that it deserves a look before scaling to nine.

**The other two suspects are simply not set** (§2.6 command, same control arm):

- `CLAUDE_CODE_ENABLE_AUTO_MODE` — **0 occurrences.** Good: Table B flags it as
  accepted-but-no-op ("has no effect", auto mode is on by default on every provider). Had it been
  set it would have been a textbook false-comfort setting. Auto mode is actually reached here the
  correct way, via `permissions.defaultMode: "auto"` at **user** scope (§2.1).
- `CLAUDE_CODE_SCRIPT_CAPS` — **0 occurrences.** Also correct, because it would have been inert:
  it is only honoured *when `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is set*, and that is 0 too (§2.9).
  A per-script call cap declared without its enabling variable is exactly the shape this section
  hunts for; it does not occur here.

### 2.8 `md_size_budget` does NOT cover this report — settled empirically

The lead asked whether a new `docs/*.md` falls inside the budget. **It does not**, and this was
settled by running the gate rather than reading the glob.

- The rule's own frontmatter (`.claude/rules/md-size-budgets.md:1-8`) scopes it to `hk.pkl`,
  `**/CLAUDE.md`, `**/AGENTS.md`, `.claude/rules/*.md`, `.claude/skills/**/SKILL.md`.
- Its five budget classes (`:90-96`) are `eager_root`, `rule_unscoped`, `nested`, `rule_scoped`,
  `skill`. **There is no `docs/**` class.**
- Empirically: `uv run --project python kb-setup md-budget` → `51 instruction files checked`,
  **`rc=0`**, and `grep -c 'harness-settings-reference'` over its output → **0**. This 62,734-byte
  file is not in scope.

**Control arm:** the gate is not merely silent — it reported checking 51 files and printed a real
byte total, so it ran and found files. A zero mention of this report is therefore a genuine
out-of-scope result, not a dead probe.

This is the right outcome and worth stating positively: `agent-artifact-conventions.md` designates
`docs/research/kb/reports/` for persisted verbatim agent reports, and
`agent-report-persistence.md` rule 2 requires them to stay **verbatim**. A size gate over that
tree would be in direct conflict with the rule that the record must not be trimmed. The two rules
agree. A 9-role team can persist nine full reports there without tripping anything.

One adjacent constraint that *does* bind and is easy to miss: `hk-common.pkl` excludes
`docs/research/runs/**` and `docs/research/kb/**` from every hk builtin
(`agent-artifact-conventions.md` § "Two things that must NOT be normalised") — so typo-fixers and
whitespace normalisers will not rewrite an agent's archived output. Do not "fix" that exclusion.

### 2.9 `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` — mechanics only, no recommendation

**Current state: absent.** 0 occurrences across all three settings scopes (§2.6 sweep, same
control arm). It is therefore **off**, and every subprocess inherits the full parent environment.

That interacts directly with this host's deliberate posture.
`.claude/rules/secrets-out-of-the-shell-env.md` records that Ray **reversed** the exec-only stance
on 2026-08-02: all **50** credentials are `env = true`, i.e. present in every terminal and
inherited by every child process, *by design*, to satisfy the stated requirement that they be
*"in sync and available to all terminals and ai/llm agents"*. The rule is explicit that this is
not to be "fixed" back.

**What turning the variable on WOULD change** (live `env-vars.md`,
`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`):

- It strips **Anthropic and cloud-provider credentials** from the environment of subprocesses —
  the Bash tool, hook commands, and MCP stdio servers. The parent Claude process keeps them for
  its own API calls.
- Every subagent and teammate Bash call is a subprocess, so the strip applies to all nine roles
  uniformly. There is no per-agent granularity.
- It would enable `CLAUDE_CODE_SCRIPT_CAPS`, which is inert without it — that is the only way to
  get per-script invocation caps.
- **On Linux it additionally runs Bash subprocesses in an isolated PID namespace**, and the
  documented side effect is that `ps`, `pgrep` and `kill` **cannot see or signal host processes**.
  For this repo that is not hypothetical: `.claude/rules/long-running-command-hangs.md` rule 4
  instructs agents to detect a wedged process and **kill it and its process group**, and the fnox
  incident in the secrets rule was diagnosed by counting **190 stuck processes**. Both of those
  diagnostic moves would break inside the namespace. The devcontainer is Linux; the Mac host is
  not, so this would bite in-container and not on the host.

**What it would NOT change:**

- It scrubs *Anthropic and cloud-provider* credentials specifically — it is **not** a general
  50-secret scrubber. The rest of the fnox set would still be inherited, so it does not deliver
  the confinement that `#432`/`#441` explored and does not restore the pre-reversal posture.
- It does nothing about the two surfaces the secrets rule says are now the *only* protection:
  rule 1 (never write an environment dump into a tracked file, gated by `no_env_dump`) and rule 7
  (a probe's own stdout — print `${VAR:+SET}` or `[ -n "$VAR" ]`, **never** `${VAR:-x}` or
  `${VAR:=x}`, which emit the value). Those bind every one of nine teammates exactly as they bind
  a single session, and nine agents running ad-hoc probes is nine times the exposure surface for
  rule 7 — the failure that already cost four live credential rotations on 2026-08-02.
- It does not touch `__MISE_DIFF`, the zlib+base64 blob that carries the whole environment delta
  in a form **no secret scanner reads** (measured: gitleaks 2 → 0, betterleaks 1 → 0). The
  existing `without_env_diff()` helper is what strips that, and it is wired at two call sites only.

**No recommendation is offered on flipping it**, per the request. The decision belongs with the
posture in `secrets-out-of-the-shell-env.md`, which is Ray's and was made deliberately.

## Open items and UNVERIFIED claims

Labelled per this repo's evidence policy — every claim above carries a `file:line` or URL except
these.

- **UNVERIFIED:** that a teammate's `hooks`, `memory`, `maxTurns`, `effort`, `isolation`, `color`,
  `description`, `disallowedTools` and `initialPrompt` frontmatter apply. Marked `UNDOCUMENTED` in
  Table D with experiments D2–D10; none were run.
- **UNVERIFIED:** the entire W (workflow-agent) column. Experiment D1 settles whether a workflow
  `agent()` call can reference a subagent definition at all. The public docs document only
  `agent(prompt, {label})` (`workflows.md:300`) and `WorkflowInput`
  (`$CC/agent-sdk__typescript.md:2484`).
- **UNVERIFIED:** that `ENABLE_CLAUDEAI_MCP_SERVERS: "false claude"` leaves claude.ai MCP servers
  enabled. The doc states `false` disables them and they are on by default; that the malformed
  value fails the check is inference, not measurement. Settle with `claude mcp list` or `/mcp`.
- **UNVERIFIED:** that `autoDreamEnabled`, `skipWorkflowUsageWarning`, `skipAutoPermissionPrompt`
  and `CLAUDE_CODE_BRIEF` are inert. What is measured is that they are **absent from the live
  docs** with a passing control arm — absence from documentation is not proof of absence from the
  binary.
- **n=1:** the §2.0 teammate tool inventory is one self-observation on 2.1.221 with this repo's
  settings. Reproduce before building on it.
- **Not re-derived:** the ~340 ms/edit branch-guard cost is quoted from memory
  `project_session_2026-08-03-f`, not measured here. Labelled inherited per
  `probes-need-a-control-arm.md` rule 6.
- **Measured here, once:** the ~124,761 bytes / ~31,190 tokens of eager context (§2.7) is this
  session's own `kb-setup md-budget` run over **this repo's 51 instruction files only**. The
  ×9-teammates figure derived from it is arithmetic on that number, not an observation of nine
  teammates, and it **excludes** the sibling-repo rules that
  `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` pulls in — so it is a floor.
- **UNVERIFIED:** that a teammate spawned on a non-Fable model actually skips the
  fable-orchestrator flow (§2.7). What is verified is that the trigger is written as
  model-conditional, that `.claude/CLAUDE.md` itself asserts non-Fable sessions skip it, and that
  `teammateDefaultModel` is unset. The behaviour of a live non-Fable teammate was not observed.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — release list and the
  v2.1.219/220/221 changelogs via `gh api repos/anthropics/claude-code/releases`; the source of the
  nesting-depth-3 and `workflowSizeGuideline` confirmations.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited repo: settings
  files, `.claude/agents/`, `.claude/rules/`, `hook_guard.py`, `graphify-hook-guard.sh`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the offline
  vendor doc tree at `sources/agent-harness-docs/docs/claude-code`, used as tier 1 and as the
  staleness control arm.
- [mkusaka/it2](https://github.com/mkusaka/it2) — named by `agent-teams.md:109,127` as the
  required CLI for `teammateMode: "iterm2"`; relevant to the `teammateMode` conflict in §2.1.
- [tmux/tmux](https://github.com/tmux/tmux) — the split-pane backend `teammateMode: "auto"`/`"tmux"`
  depends on.
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — enabled plugin whose
  declared-but-inert lane is this repo's precedent for the §2.2 defect class.

_Non-GitHub source consulted: `https://code.claude.com/docs/en/*.md` (live vendor docs), which is
the authority wherever it disagrees with the offline tree._
