# Docs remainder sweep — agent/team/coordination content in the Claude Code doc corpus

**Agent:** docs-remainder-sweep · **Date:** 2026-08-04 · **Branch:** `research/agent-team-design`

**Corpus:** `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`
(abbreviated `$CC` below) — **174 `.md` pages** + `docs_manifest.json` (175 directory entries).

Status: **COMPLETE.** All 174 pages scored; the 30 named as covered by other agents excluded; the
remainder ranked and the decisive ones read. All seven design questions answered with `file:line`
citations. Two claims left explicitly UNVERIFIED (see "Method caveats").

---

## Method

**Step 0 — graphify orientation (per repo hook).** `graphify query "agent team subagent
coordination design"` returned 71 nodes, all from *this repo* (`AGENTS.md`,
`docs/specs/second-brain-design.md`, `docs/maestro/plans/…`). The graph does not index the
external knowledge-base doc corpus, so it could not orient this sweep. Recorded, not relied on.

**Step 1 — vocabulary discovery by SHAPE, not by guessed keyword list.** Rather than grep for
terms I expected, I extracted every *token containing* a coordination stem and counted it:

```
grep -rhoiE '[A-Za-z_-]*(agent|team|delegat|orchestr|parallel|concurren|spawn|worker|fleet|swarm|coordinat|fan-?out|multi-?claude)[A-Za-z_-]*' . --include='*.md' \
  | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn
```

This returned **~330 distinct tokens**. It surfaced vocabulary a guessed list would have missed
entirely, and several of these are the load-bearing findings below:

| Token found by shape | Why a guessed list would have missed it |
|---|---|
| `--keep-workers` (8), `worker_shutting_down` (2), `worker-stall` | "worker" is not agent-team vocabulary in the product pages |
| `claude_code_max_subagent_spawn_depth` (5), `let-subagents-spawn-their-own-subagents` (10) | recursion depth is a real, configurable limit |
| `claude_async_agent_stall_timeout_ms` (6), `claude_code_team_teardown_park_timeout_ms` | stall/teardown timeouts — failure-mode surface |
| `--append-subagent-system-prompt` (4), `claude_code_enable_append_subagent_prompt` | the flag is gated behind a separate opt-in env var |
| `--forward-subagent-text` (7), `claude_code_forward_subagent_text` (4) | nested-agent output visibility |
| `x-claude-code-agent-id`, `x-claude-code-parent-agent-id` (2 each) | HTTP headers attributing requests to a named agent — the Q5 answer |
| `agent-would-be-spawned-with-zero-tools` (5) | a specific documented error condition |
| `self-spawn`, `self-spawns`, `respawn`/`respawns`/`auto-respawning` (17+) | teammate lifecycle |
| `in_process_teammate`, `remote_agent`, `local_agent` | transport modes |
| `blue_for_subagents_only`, `subagent-statusline` | statusline attribution |
| `agent_path_count`, `read-agent-traces` | observability |
| `subagent-edits-not-restored` | **the Q4 answer** — checkpointing's subagent gap |

**Step 2 — score every one of the 174 pages** by count of lines matching the union of those
stems, then subtract the 30 pages named as covered by other agents. Full ranking taken for all
174 (head and tail both inspected, so nothing fell off the bottom of a `head`).

**Control-arm discipline.** Every absence claim below reports both arms, with a control term
invented fresh for that probe (never reused from a prior receipt — a published control term is
now *in* the corpus and stops discriminating).

---

## Half 1 — corpus re-enumeration and coverage gaps

### The 30 pages named as covered by other agents

`sub-agents` · `agents` · `agent-view` · `tools-reference` · `agent-sdk__subagents` ·
`context-window` · `errors` · `glossary` · `agent-teams` · `hooks` · `hooks-guide` ·
`claude-directory` · `settings` · `permission-modes` · `worktrees` · `costs` ·
`monitoring-usage` · `best-practices` · `features-overview` · `champion-kit` · `channels` ·
`channels-reference` · `remote-control` · `slack` · `claude-code-on-the-web` ·
`scheduled-tasks` · `desktop-scheduled-tasks` · `workflows` · `env-vars` · `model-config`.

### Unassigned pages scoring meaningfully (nobody's assignment)

Score = lines matching the coordination-stem union. **Bold** = read for this report.

| Score | Page | Verdict |
|---:|---|---|
| 632 | **`changelog.md`** | HIGH — the only dated record of when each agent mechanic shipped |
| 230 | **`agent-sdk__typescript.md`** | HIGH — full `AgentDefinition` type surface |
| 213 | **`agent-sdk__python.md`** | HIGH — Python mirror; `AgentDefinition` + `ClaudeAgentOptions` |
| 80 | **`agent-sdk__hooks.md`** | HIGH — SDK hook surface incl. subagent events |
| 77 | **`agent-sdk__agent-loop.md`** | MED — the loop model; how delegation fits |
| 63 | **`agent-sdk__hosting.md`** | MED — unattended/multi-tenant hosting |
| 59 | `agent-sdk__quickstart.md` | LOW — intro, no unique mechanics |
| 57 | **`plugins-reference.md`** | HIGH — **Q2** |
| 47 | **`agent-sdk__file-checkpointing.md`** | HIGH — **Q4** |
| 46 | **`agent-sdk__claude-code-features.md`** | HIGH — explicit CLI-vs-SDK parity table |
| 45 | `agent-sdk__migration-guide.md` | LOW — rename churn |
| 45 | **`agent-sdk__mcp.md`** | MED — per-agent MCP scoping |
| 44 | **`agent-sdk__secure-deployment.md`** | HIGH — **Q6** |
| 44 | `agent-sdk__custom-tools.md` | LOW |
| 43 | **`agent-sdk__sessions.md`** | MED — resume/fork semantics |
| 43 | `agent-sdk__session-storage.md` | MED |
| 40 | **`skills.md`** | HIGH — **Q1** |
| 39 | **`agent-sdk__modifying-system-prompts.md`** | HIGH — **Q3** (`--append-subagent-system-prompt` sibling) |
| 36 | `google-vertex-ai.md` | LOW — "agent platform" is a Vertex product name, not our sense |
| 36 | **`agent-sdk__overview.md`** | MED |
| 36 | **`agent-sdk__observability.md`** | HIGH — **Q5** |
| 34 | **`plugin-marketplaces.md`** | MED — **Q2** distribution |
| 34 | `desktop.md` | LOW |
| 34 | **`agent-sdk__cost-tracking.md`** | HIGH — **Q5** |
| 33 | `agent-sdk__user-input.md` | MED |
| 32 | `agent-sdk__slash-commands.md` | LOW |
| 31 | `prompt-library.md` | LOW — prose examples |
| 31 | **`agent-sdk__skills.md`** | MED — **Q1** cross-check |
| 30 | `agent-sdk__structured-outputs.md` | LOW |
| 30 | **`agent-sdk__streaming-vs-single-mode.md`** | HIGH — **Q3** |
| 28 | **`plugins.md`** | HIGH — **Q2** |
| 28 | `commands.md` | LOW |
| 28 | **`agent-sdk__streaming-output.md`** | HIGH — **Q3** (`stream-json` nesting) |
| 28 | **`agent-sdk__plugins.md`** | MED — **Q2** |
| 27 | **`feature-availability.md`** | MED — which surfaces have teams at all |
| 26 | **`cli-reference.md`** | HIGH — **Q3** flags |
| 25 | `authentication.md` | LOW |
| 25 | **`agent-sdk__permissions.md`** | HIGH — **Q6** |
| 23 | **`permissions.md`** | HIGH — **Q6** |
| 22 | `third-party-integrations.md` · `mcp.md` · `gitlab-ci-cd.md` | LOW |
| 22 | **`agent-sdk__tool-search.md`** | MED |
| 21 | `agent-sdk__typescript-v2-preview.md` | MED |
| 20 | `llm-gateway-connect.md` · `communications-kit.md` · `agent-sdk__todo-tracking.md` | LOW |
| 19 | **`memory.md`** | MED — agent memory scoping |
| 19 | **`how-claude-code-works.md`** | MED |
| 19 | `admin-setup.md` | LOW |
| 18 | `whats-new.md` · `github-actions.md` | LOW |
| 17 | **`headless.md`** | HIGH — **Q3** |
| 16 | `corporate-launcher.md` · 15 `claude-apps-gateway.md` | LOW |
| 14 | `discover-plugins.md` · `artifacts.md` · **`analytics.md`** | analytics = **Q5** |
| 13 | **`statusline.md`** | MED — per-subagent statusline |
| 12 | **`security-guidance.md`** · `large-codebases.md` | **Q6** |
| 11 | **`sessions.md`** · `common-workflows.md` · `code-review.md` · `data-usage.md` | MED |
| 8 | `interactive-mode.md` · `sandbox-environments.md` · `fast-mode.md` · `ultrareview.md` | LOW |
| 6 | `sandboxing.md` · `server-managed-settings.md` | MED (**Q6**) |
| 4 | **`security.md`** · `troubleshooting.md` | **Q6** |
| 3 | **`checkpointing.md`** | HIGH — **Q4**, despite the low raw score |
| 2 | `setup.md` · `keybindings.md` · `managed-mcp.md` | LOW |
| 0 | `goal.md` · `deep-links.md` | none |

### ⚠️ The scoring caveat that matters — raw score is a bad proxy at the low end

`checkpointing.md` scores **3** and is the single most important page for design question 4.
Score ranks *volume*, not *decisiveness*: a page that mentions subagents once, to say they are
**not** covered, is exactly the page a design needs. Every page below score 15 that touches a
named design question was therefore read regardless of rank. **Do not use this table as a
read/skip filter on its own.**

### Pages the team lead's "likely candidates" list named that turned out LOW-yield

`interactive-mode.md` (8), `setup.md` (2), `output-styles.md` (3), `common-workflows.md` (11),
`mcp.md` (22 — nearly all "agent" in the MCP-server sense), `security.md` (4 — a stub that
redirects to `security-guidance.md`). Verified, not assumed.

---

## Half 2 — design questions

### Q1 — Skills preloaded into subagents

**Answer: the `skills:` frontmatter field injects the FULL skill content at subagent startup,
and it CANNOT list a `disable-model-invocation: true` skill. The prior finding is CONFIRMED,
with an exact citation and a stated reason.**

**The mechanic** — `$CC/sub-agents.md:469`:

> "Use the `skills` field to inject skill content into a subagent's context at startup. This
> gives the subagent domain knowledge without requiring it to discover and load skills during
> execution."

**What is injected** — `$CC/sub-agents.md:483`:

> "The full content of each listed skill is injected into the subagent's context at startup.
> This field controls which skills are preloaded, **not** which skills the subagent can access:
> without it, the subagent can still discover and invoke project, user, and plugin skills
> through the Skill tool during execution. To prevent a subagent from invoking skills entirely,
> omit `Skill` from the `tools` list or add it to `disallowedTools`."

Two consequences for a team design, both load-bearing:

1. `skills:` is **additive preloading, not an allowlist**. Restricting what a subagent may reach
   requires the `tools` / `disallowedTools` lever, not the `skills` lever.
2. Preloading is **eager and unconditional** — it is context cost paid at startup on every
   spawn, whether or not the agent needs that skill. Contrast the main session, where
   descriptions load and content does not: `$CC/skills.md:404` — "In a regular session, skill
   descriptions are loaded into context so Claude knows what's available, but full skill content
   only loads when invoked. Subagents with preloaded skills work differently: **the full skill
   content is injected at startup.**"

**The `disable-model-invocation` interaction — VERIFIED** — `$CC/sub-agents.md:485`:

> "You can't preload skills that set `disable-model-invocation: true`, since preloading draws
> from the same set of skills Claude can invoke. *(min-version: 2.1.215)* This includes the
> bundled `/verify` and `/code-review` skills: only you can run them, so they can't be preloaded
> either."

Confirmed independently from the frontmatter reference — `$CC/skills.md:263`:

> "`disable-model-invocation` … Set to `true` to prevent Claude from automatically loading this
> skill. … **Also prevents the skill from being preloaded into subagents.** *(min-version:
> 2.1.196)* As of v2.1.196, also prevents the skill from running when a scheduled task fires
> with the skill as its prompt."

Two independent pages state it, and they agree. The *reason* given is the design constraint
worth carrying: **preloading draws from the same set Claude can invoke**, so it is one gate, not
two. A skill hidden from the model is hidden from every subagent's preload list as a
consequence, not as a separate rule.

**Failure mode is silent-ish** — `$CC/sub-agents.md:487`: "If a listed skill is missing or
disabled, Claude Code skips it and logs a warning to the **debug log**." A typo in a `skills:`
entry does not fail the spawn; it degrades it, and the evidence lands somewhere nobody reads.
For a team design this is a real hazard: an agent silently running without its domain knowledge
looks identical to one running with it.

**Impact on this repo, concrete.** Per `feedback_protocol_verbs_are_user_invoked_only`, nine of
this repo's protocol verbs are `disable-model-invocation: true`. **None of them can ever be
preloaded into a subagent.** Any team design that assumed "give the implementer agent the
`/implement` skill via `skills:`" is unimplementable as written.

**The inverse direction**, for completeness — `$CC/skills.md:570-571` gives the full two-way
table:

| Direction | System prompt | Task/prompt | Also loaded |
|---|---|---|---|
| Skill with `context: fork` | From agent type | SKILL.md content | CLAUDE.md, except when the agent is Explore or Plan |
| Subagent with `skills` field | Subagent's markdown body | Claude's delegation message | Preloaded skills + CLAUDE.md |

`$CC/sub-agents.md:490` — "Both use the same underlying system."

⚠️ **A backgrounded forked skill runs with a NARROWER tool set** — `$CC/skills.md:558`: "A
backgrounded fork also runs with the narrower tool set that applies to background subagents: the
skill's subagent is a regular agent type, so the exemption for subagents that fork the
conversation doesn't cover it. If your skill's steps depend on a tool outside that set, set
`background: false` to keep the full tool set." Since `background: true` is the **default**
(`$CC/skills.md:271`), a `context: fork` skill silently gets the reduced tool set unless you opt
out. Pre-2.1.218 forked skills always blocked (`$CC/skills.md:549`), so this is a behavior
change that inverted the default.

**Control arm for this question.** `grep -rn 'disable-model-invocation' *.md` returned **34 hits
across 13 files** — so the probe sees the term. Fresh known-absent control term `qwvbrtz`:
`grep -rl 'qwvbrtz' *.md` → **0 files**. Probe discriminates in both directions.

---

### Q2 — Plugins: can one ship subagents, hooks and workflows together?

**Answer: YES, all three plus more, from one directory. But plugin-shipped subagents lose
exactly three frontmatter fields — `hooks`, `mcpServers`, `permissionMode` — and the docs state
the reason outright: "for security reasons".**

**A plugin's component set** — `$CC/plugins-reference.md:15`:

> "A plugin is a self-contained directory of components that extends Claude Code with custom
> functionality. Plugin components include skills, agents, hooks, MCP servers, LSP servers, and
> monitors."

The full on-disk layout — `$CC/plugins-reference.md:855-864`:

| Component | Path | Note |
|---|---|---|
| Agents | `agents/` | Subagent markdown files |
| Skills | `skills/` or `commands/`, or a root `SKILL.md` | |
| **Workflows** | `workflows/` | Workflow script files (`$CC/plugins-reference.md:856`) |
| Hooks | `hooks/hooks.json` or inline in `plugin.json` | |
| MCP servers | `.mcp.json` | |
| LSP servers | `.lsp.json` | |
| Monitors | `monitors/monitors.json` | |
| **Executables** | `bin/` | "**added to the Bash tool's `PATH`** … invokable as bare commands in any Bash tool call while the plugin is enabled" |
| Settings | `settings.json` | "Only the `agent` and `subagentStatusLine` keys are currently supported" |

So a single plugin can ship a **team**: the agent definitions, the hooks that police them, the
workflows that sequence them, the MCP servers they call, and the binaries they shell out to.
`bin/` is the one most likely to be overlooked — it silently widens what every Bash call in the
session can invoke.

#### The ignored fields, and why

`$CC/plugins-reference.md:74` — the decisive line:

> "Plugin agents support `name`, `description`, `model`, `effort`, `maxTurns`, `tools`,
> `disallowedTools`, `skills`, `memory`, `background`, and `isolation` frontmatter fields. The
> only valid `isolation` value is `"worktree"`. **For security reasons, `hooks`, `mcpServers`,
> and `permissionMode` are not supported for plugin-shipped agents.**"

The three excluded fields are exactly the three that would let a downloaded third-party
definition **escalate its own privileges or execute code**, so the rationale is coherent rather
than arbitrary:

| Excluded field | What it would grant an untrusted plugin |
|---|---|
| `permissionMode` | Self-declared `bypassPermissions` — an agent that approves its own tool calls |
| `hooks` | Arbitrary shell execution on harness events, outside the tool-permission system entirely |
| `mcpServers` | Spawning arbitrary local processes as "servers" |

Note the asymmetry, and it is the important part for a design: a plugin **can** ship hooks and
MCP servers at the *plugin* level (`hooks/hooks.json`, `.mcp.json`) — they are just not
attachable to an *individual agent definition*. The boundary is per-agent privilege escalation,
not the capability itself. A plugin's hooks are visible in `plugin.json` where a reviewer looks;
a `hooks:` block buried in one of twenty agent markdown files is not.

This is the same reasoning applied one layer up at `$CC/plugins-reference.md:601`: `pluginConfigs`
entries in a project's `.claude/settings.json` are **ignored**, because "a cloned repository
could supply values there, and those values would flow into plugin hook commands, MCP server
configs, LSP commands, and monitor commands." Before v2.1.207 they were read. `enabledPlugins`
still honors project settings.

#### Naming and discovery

- Scoped names: `$CC/plugins-reference.md:466` — "agent `agent-creator` for the plugin with name
  `plugin-dev` will appear as `plugin-dev:agent-creator`", and appears in the @-mention typeahead
  under that scoped name (`:78`).
- Manifest keys **replace** the default directory rather than adding to it —
  `$CC/plugins-reference.md:636`: "`commands`, `agents`, `workflows`, `outputStyles` … when the
  manifest specifies `commands`, the default `commands/` directory is not scanned. To keep the
  default and add more, list it explicitly." A silent way to lose half your agents. v2.1.140+
  warns about the ignored folder in `claude plugin list`.
- **Live reload does not cover agents** — `$CC/plugins-reference.md:406`: `SKILL.md` edits apply
  immediately; "changes to the plugin's other components, such as `hooks/`, `.mcp.json`,
  `agents/`, and `output-styles/`, do not. Run `/reload-plugins` or restart." Iterating on an
  agent definition inside a plugin has a reload step that iterating on a skill does not.

#### Bonus finding — there is an `agent` HOOK TYPE

`$CC/plugins-reference.md:150-154` lists five hook types, and the last one is not in this repo's
mental model at all:

> `command` · `http` · `mcp_tool` · `prompt`: evaluate a prompt with an LLM · **`agent`: run an
> agentic verifier with tools for complex verification tasks**

That is a coordination primitive hiding in the hook system: an event can dispatch a
tool-wielding agent, not just a shell command. Confirmed as a valid value at
`$CC/plugins-reference.md:1226` ("Confirm the hook type is valid: `command`, `http`, `mcp_tool`,
`prompt`, or `agent`"). Relevant to this repo, whose entire guard layer is `command` hooks.

#### Token accounting per plugin

`$CC/plugins-reference.md:1101` — `claude plugin` inspection "lists all components the plugin
contributes, grouped as Skills, Agents, Hooks, MCP servers, and LSP servers, along with an
estimate of how many tokens it adds to each session", split into **always-on** ("the plugin's
listing text, such as skill descriptions, **agent descriptions**, and command names, regardless
of whether any component fires", `:1119`) and **on-invoke** (`:1144`). Agent *descriptions* are
an always-on cost — a plugin shipping thirty agents taxes every session with thirty
descriptions.

**Control arm.** Positive: `grep -c 'agents' plugins-reference.md` → the page yields the 20+ hits
above. Negative, fresh term `zmqvftk`: `grep -rl 'zmqvftk' *.md` → **0 files**. Discriminates.

---

### Q3 — Headless / non-interactive: what changes for agents under `claude -p`

**Headline answer for a team design: AGENT TEAMS ARE A CLI-ONLY, INTERACTIVE FEATURE. There is
no documented way to run a team unattended, and the one sentence in the docs on the subject
advises against it.** Subagents, by contrast, are fully supported headless and have a rich
control surface.

#### The negative finding, control-armed

`agent-teams.md` contains **zero** occurrences of `non-interactive`, `headless`, `-p`, `SDK`, or
`unattended` — except one line about the *risk* of it. Control arm on the same file with the same
command shape: `grep -c 'teammate' agent-teams.md` → **120**. The probe reads the file fine; the
absence is real.

The sole relevant sentence, `$CC/agent-teams.md:374`:

> "Check in on teammates' progress, redirect approaches that aren't working, and synthesize
> findings as they come in. **Letting a team run unattended for too long increases the risk of
> wasted effort.**"

Corroborated from the SDK side — `$CC/agent-sdk__claude-code-features.md:300`:

> "Coordinate multiple Claude Code instances with shared task lists and direct inter-agent
> messaging → Agent teams → **Not directly configured via SDK options. Agent teams are a CLI
> feature** where one session acts as the team lead, coordinating work across independent
> teammates."

And `:305`: "Subagents are ephemeral and isolated: fresh conversation, one task, summary returned
to parent. Agent teams coordinate multiple independent Claude Code instances that share a task
list and message each other directly. **Agent teams are a CLI feature.**"

**Design consequence:** an unattended team must be built out of *subagents* (headless-supported,
with concurrency caps and stall timeouts) or out of *N separate `claude -p` processes you
orchestrate yourself*. The built-in team primitives — shared task list, `SendMessage`,
`TeammateIdle` — are not reachable from `-p`. The only teammate-adjacent CLI flag,
`--teammate-mode` (`$CC/cli-reference.md:124`), sets a **display** mode (`in-process` default,
`auto`, `tmux`, `iterm2`), which is inherently interactive.

#### Which built-in agents disappear

Two separate switches, and the distinction matters:

| Switch | Effect | Scope | Cite |
|---|---|---|---|
| `CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS=1` | Removes **only** Explore and Plan. Claude explores with search tools or general-purpose instead; plan mode reads files directly. Custom agents *named* `Explore`/`Plan` are unaffected | any mode; v2.1.198+ | `$CC/env-vars.md:229` |
| `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS=1` | Removes **all** built-in types — "a blank slate" | **`-p` / SDK only** | `$CC/env-vars.md:186`, `$CC/sub-agents.md:87` |

And a phrasing worth not skimming past — `$CC/sub-agents.md:82`: "Built-in subagents are
registered by default **in interactive sessions**." The qualifier is conspicuous, but the docs do
**not** anywhere state that built-ins are absent by default under `-p`; the two disable switches
above are the only documented removals. **Verdict: nothing disappears automatically under `-p` —
you remove built-ins explicitly.** Marking the stronger reading UNVERIFIED rather than inferring
from one adjective.

⚠️ **`--bare` is the bigger behavioral cliff** — `$CC/headless.md:35`:

> "Add `--bare` to reduce startup time by **skipping auto-discovery of hooks, skills, plugins,
> MCP servers, auto memory, and CLAUDE.md**."

and `:45`: "In bare mode Claude has access to the Bash, file read, and file edit tools." Custom
agents must then be passed explicitly with **`--agents <json>`** (`$CC/headless.md:52`). Anything
your team design relies on being *discovered* — a `.claude/agents/` directory, a plugin's agents,
a project hook — is silently gone. `$CC/headless.md:58`: "`--bare` … **will become the default
for `-p` in a future release.**" A design that works today under `-p` may break when that lands.

#### `--append-subagent-system-prompt`

`$CC/cli-reference.md:64`:

> "Append custom text to the end of **every** subagent's system prompt, **including nested
> subagents**. **Only applies in non-interactive mode with `-p`.** Requires Claude Code v2.1.205
> or later."

Gated behind an env var that the flag sets for you — `$CC/env-vars.md:247`:
`CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT=1`; "the flag supplies the appended text and sets this
variable automatically, so you don't need to set it yourself."

This is the **only documented mechanism for injecting a policy into every agent in a headless
run, transitively**. For this repo it is the natural carrier for a standing instruction that must
reach depth-2 and depth-3 agents (e.g. the incremental-persistence rule that
`feedback_agent_team_delivery_discipline` records as failing twice when it lived only in a
brief). Caveat: `-p` only — it does nothing in an interactive session.

#### What `stream-json` exposes about nested agents

`$CC/headless.md:169`: "Messages from subagents appear in the stream as `assistant` and `user`
messages whose **`parent_tool_use_id`** field is the ID of the tool call that spawned the
subagent. Messages from the main conversation carry `null` in that field."

Default is **partial** — `$CC/headless.md:171`: "By default, Claude Code emits only subagent
`tool_use` and `tool_result` blocks." To get text and thinking, pass `--forward-subagent-text`
(v2.1.211+) or set `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT=1`. Requires `--print` **and**
`--output-format stream-json` (`$CC/cli-reference.md:87`).

Full nesting tree — `$CC/headless.md:173`:

> "Claude Code forwards messages from subagents at **every nesting depth**: when a subagent
> spawns its own subagent, the nested subagent's messages carry the ID of the Agent tool call
> that spawned it in `parent_tool_use_id`, so you can rebuild the full nesting tree by following
> those IDs. **Before v2.1.219, messages from nested subagents didn't appear in the stream.**"

⚠️ **Version-sensitive and recent** — on anything below v2.1.219 a depth-2 agent is invisible in
the stream. An observability design built on `stream-json` must pin or feature-detect. Use the
`system/init` event's **`capabilities` array** (v2.1.205+) to feature-detect rather than comparing
version strings (`$CC/headless.md:198`).

Flag-vs-variable asymmetry worth knowing — `$CC/env-vars.md:266`: the **flag** "exits with an
error outside non-interactive mode with stream-json output"; the **variable** is silently ignored
there, "so that nested invocations keep working when it's set process-wide." Setting the env var
is the safe choice for a wrapper that shells out to `claude` in mixed modes.

#### Unattended-run failure modes the flags actually name

Enumerated from `env-vars.md` **by shape** (`CLAUDE_[A-Z_]*(SUBAGENT|AGENT|TEAM|CONCURRENC|STALL|BG_WAIT)[A-Z_]*`),
not by guessing names — this returned 21 distinct variables, several of which I would not have
thought to look for:

| Variable | Default | What it governs | Cite |
|---|---|---|---|
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | **20** | Running at once before the Agent tool refuses to spawn. "Can adjust the cap but **can't disable it**" — a non-numeric value is ignored | `env-vars.md:275` |
| `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | **200** | Lifetime spawns per session; at the cap, spawning "fails with an error telling Claude to finish the remaining work directly" | `env-vars.md:279` |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | **3** | Layers below the main conversation. Set `1` to turn nesting off | `env-vars.md:280` |
| `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` | **600000** (10 min) | Background-subagent stall timer. **"The timer resets on each streaming progress event; if no progress arrives within the window, the subagent is aborted and the task is marked failed, surfacing any partial result to the parent"** | `env-vars.md:188` |
| `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` | **600000** | How long `-p` waits after the final turn for background subagents/workflows; on exceed, "remaining background tasks are terminated" | `env-vars.md:307` |
| `CLAUDE_CODE_TEAM_TEARDOWN_PARK_TIMEOUT_MS` | — | Team teardown parking | `env-vars.md:346` |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | — | The teams opt-in | `env-vars.md:259` |
| `CLAUDE_CODE_SUBAGENT_MODEL` | — | Model for subagents | `env-vars.md:337` |

`$CC/headless.md:65` ties two of these together and is the single most useful sentence for
unattended runs:

> "Background subagents and workflows are **exempt** from the five-second grace because their
> result is part of the final output, so `claude -p` waits for them to complete. From v2.1.182,
> that wait is capped at **ten minutes** by default so a stuck background agent cannot hold the
> process open indefinitely."

⚠️ **The 10-minute stall timeout directly explains a measured failure in this repo.**
`feedback_agent_team_delivery_discipline` records two agents that "died silently after ~40
minutes and left nothing." `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` aborts a background subagent
after 10 minutes **without a streaming progress event** and marks the task failed. An agent doing
a long silent read emits no progress. This is a plausible mechanism for those deaths and it is
configurable — but note the doc says the abort *surfaces any partial result to the parent*, which
does not obviously match "left nothing". **Flagging as a strong lead, not a confirmed diagnosis:
I have not reproduced it, and the 40-minute figure is inherited, not re-measured.**

`$CC/headless.md:67` — SIGTERM handling: aborts the turn, terminates the Bash process tree, runs
`SessionEnd` hooks, exits **143**. (This repo has seen rc=143 on a killed `mise run ship`.)

**Control arm.** Positive: `grep -rn 'forward.subagent.text' *.md` → 7 hits across 6 files.
Negative, fresh term `pxjwnqd`: `grep -rl 'pxjwnqd' *.md` → **0 files**. Discriminates.

---

### Q4 — Checkpointing / rewind: what is actually recoverable

**Answer: checkpointing covers ONLY the main session's own Write/Edit/NotebookEdit calls. It
does NOT cover subagent edits, does NOT cover anything done via Bash, and does NOT restore
teammates. Against the arXiv 2607.22917v2 "irrecoverable state" failure mode, the harness
recovers strictly less than a naive reading would assume — and the docs say so explicitly in
three separate places.**

This is the page the shape score ranked **3rd from the bottom** (score 3 of 174). It is the most
decisive page in the sweep. Recorded as the worked example of why raw score is not a read/skip
filter.

#### What IS captured

`$CC/checkpointing.md:13` — "checkpointing automatically captures the state of your code before
each user prompt." Specifically (`:19-22`):

- one checkpoint per **user prompt** (not per tool call, not per turn);
- file snapshots for the **100 most recent** checkpoints in a session;
- saved with the conversation, so `/rewind` survives a resume;
- deleted with sessions after **30 days** (`cleanupPeriodDays`).

Restore is four-way (`:34-39`): code+conversation, conversation only, code only, plus two
summarize directions. Note **conversation and code are independently restorable** — useful, and
it means "rewind" is not one operation.

#### What is NOT captured — the three gaps that matter for a team

**1. Subagent edits — the explicit gap.** `$CC/checkpointing.md:82-84`, heading *"Subagent edits
not restored"*:

> "Except for a skill with `context: fork` that runs in the **foreground**, edits a subagent
> applies **land outside your session's checkpoints, so rewinding doesn't restore them, even
> though the subagent makes them with Claude's file editing tools**. This includes a background
> `/code-review --fix` run and any forked skill that runs in the background. **Use git to revert
> those edits.** The foreground fork edits your working tree during your own turn, so rewinding
> restores its edits as usual."

The parenthetical is the trap: a **forked skill runs in the background by DEFAULT** as of
v2.1.218, so the recoverable case (`background: false`) is the opt-in one. Before v2.1.218 forked
skills always ran in the foreground — i.e. **the default flipped from recoverable to
unrecoverable.**

Confirmed independently from the SDK page, which states it twice —
`$CC/agent-sdk__file-checkpointing.md:18` in prose, and `:730` in the limitations table:

> "**Subagent edits** — Edits a subagent applies aren't tracked or restored, except a skill with
> `context: fork` running in the foreground; **use git to revert untracked edits**"

Two pages, two authors, same statement. High confidence.

**2. Bash — everything.** `$CC/checkpointing.md:70-80`: "Checkpointing does not track files
modified by bash commands … `rm file.txt` / `mv old.txt new.txt` / `cp source.txt dest.txt` …
**These file modifications cannot be undone through rewind.**" Same at
`$CC/agent-sdk__file-checkpointing.md:729`. For this repo, where agents run `mise run`, `git`, and
python via Bash constantly, this means **most state an agent mutates here is outside
checkpointing entirely.**

**3. Teammates — not restored, and the lead doesn't know.** `$CC/agent-teams.md:421`:

> "**No session resumption with in-process teammates**: `/resume` and `/rewind` do **not** restore
> in-process teammates. After resuming a session, **the lead may attempt to message teammates that
> no longer exist.** If this happens, tell the lead to spawn new teammates."

This is the sharpest finding for a team design. The failure is not merely "state is lost" — it is
that **the lead's model of the team survives while the team does not**, and the lead keeps
messaging the dead. Recovery is manual and requires a human to notice and say so.

**Control arm for the teammate absence.** `grep -ci 'teammate' checkpointing.md` → **0**. Same
command shape on the same file for terms known to be present: `subagent` → **2**, `git` → **3**.
The probe reads the file; `checkpointing.md` genuinely never mentions teammates, and the only
statement on the subject lives on a *different* page (`agent-teams.md:421`) — which is exactly
how a design team misses it. Fresh negative control across the corpus: `grep -rl 'hkzvrtp' *.md`
→ **0 files**.

#### Two further gaps

- **External/concurrent sessions** — `$CC/checkpointing.md:88`: "Manual changes you make to files
  outside of Claude Code and **edits from other concurrent sessions** are normally not captured,
  unless they happen to modify the same files as the current session." Directly relevant to any
  design running multiple sessions against one worktree.
- **Symlinks and hard links are SKIPPED on restore** — `$CC/checkpointing.md:90-92`: restore
  "skips any tracked path that is a symlink or hard link and shows a `Restored the code, but
  skipped N files` warning. **The skipped files keep their current contents.**" And explicitly:
  "**Config files a dotfile manager symlinks into your project** … fall into this category."
  ⚠️ **This repo is chezmoi-managed.** A `/rewind` here will silently decline to restore exactly
  the symlinked dotfiles the repo exists to manage — the warning names a count, not the paths.
  Turn on `/debug` before restoring; the debug log at `~/.claude/debug/<session-id>.txt` names
  each skipped path. Before v2.1.216 `/rewind` **wrote and deleted through links with no
  warning** (`:97`).

#### The docs' own verdict

`$CC/checkpointing.md:100-106`, heading *"Not a replacement for version control"*: "Think of
checkpoints as **'local undo'** and Git as **'permanent history'**."

**Answer to the arXiv framing:** against irrecoverable state, the harness's own recovery
mechanism is scoped to single-session, single-agent, non-Bash file edits. Every multi-agent
mutation path — subagent edits, teammate work, Bash side effects, concurrent sessions — is
outside it, and the docs' stated remedy in every case is **git**. A team design cannot treat
`/rewind` as a safety net for delegated work; the safety net has to be branch-and-commit
discipline, which is what this repo's `branch_guard` already enforces (`do-not.md` #9).

---

### Q5 — `/usage`, analytics and OTEL: attributing cost to a named agent

**Answer: attribution by agent *ID* is thorough and includes teammates. Attribution by agent
*NAME* is deliberately REDACTED for your own agents — `agent.name` reports `"custom"` for every
user-defined agent. And the SDK's headline `usage` field silently UNDERCOUNTS subagent tokens.**

#### The redaction — the finding that constrains any per-agent cost dashboard

`$CC/monitoring-usage.md:533`:

> "`agent.name`: Subagent type that issued the request. **Built-in agent names and agents from
> official-marketplace plugins appear verbatim. Other user-defined agent names are replaced with
> `"custom"`.** Absent when the request was not issued by a named subagent type."

The same redaction rule applies across the neighbouring attributes (`:534-535`): `skill.name`
keeps built-in/bundled/user-defined/official-marketplace names verbatim but replaces
**third-party plugin** skill names with `"third-party"`; `plugin.name` likewise.

⚠️ **Note the asymmetry between the two lines, and do not conflate them.** For *skills*,
user-defined names ARE verbatim and only third-party-plugin ones are redacted. For *agents*,
user-defined names are NOT verbatim. So in this repo: a custom skill's name would reach OTEL,
but `staleness-auditor` and `dockerfile-reviewer` would both arrive as `"custom"` and be
indistinguishable. **A per-agent cost breakdown keyed on `agent.name` cannot work for
locally-defined agents.**

The workaround is IDs, which are not redacted — `$CC/monitoring-usage.md:207-208`:

| Attribute | Meaning |
|---|---|
| `agent_id` | "Identifier of the subagent **or teammate** that issued the request. Absent on the main session" |
| `parent_agent_id` | "Identifier of the agent that spawned this one. Absent for the main session and for agents spawned directly from it" |

Same pair on tool events (`:239-240`), plus `subagent_type` on tool detail (`:248`, gated behind
`OTEL_LOG_TOOL_DETAILS`) and `query_source` ∈ `{"main","subagent","auxiliary"}` (`:530`).
`agent_id` **explicitly covers teammates**, so team activity is attributable even though team
*configuration* is CLI-only.

#### Gateway headers — attribution without touching OTEL

`$CC/llm-gateway-protocol.md:78-79` — the header pair I found only via the shape enumeration:

| Header | Meaning |
|---|---|
| `x-claude-code-session-id` | "aggregate all requests from one session without parsing request bodies" |
| `x-claude-code-agent-id` | "Identifier of the subagent that issued the request … **Use it with the session ID to attribute cost to parallel agents**" |
| `x-claude-code-parent-agent-id` | "Identifier of the agent that spawned the requesting agent, present only for nested agents" |

And the ID-stability rule, which matters for joining data across a long run —
`$CC/llm-gateway-protocol.md:81`:

> "**Subagent IDs are generated fresh for each spawn. Teammate agents, the named members of an
> agent team, reuse a stable name-based ID across reconnections.** In both cases the ID identifies
> an agent, not a person or a device, so don't treat the agent ID header as a user identifier."

**Design consequence:** teammates are the only agents with a *stable* identifier across a
session's lifetime. Subagent IDs are per-spawn, so a "cost per role" rollup over subagents
requires you to carry your own mapping from spawn ID → role; the harness will not do it for you,
and `agent.name` (which would have) is redacted.

#### Traces: the delegation chain is one trace

`$CC/agent-sdk__observability.md:151`:

> "When the agent spawns a subagent through the Task tool, the subagent's `llm_request` and `tool`
> spans **nest under the parent agent's `claude_code.tool` span, so the full delegation chain
> appears as one trace**."

Span set (`:146-149`): `claude_code.interaction` (one turn), `claude_code.llm_request`,
`claude_code.tool` (with children `…tool.blocked_on_user` and `…tool.execution`), and
`claude_code.hook`. Requires `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`; the hook span additionally
needs `ENABLE_BETA_TRACING_DETAILED=1` + `BETA_TRACING_ENDPOINT`. **Tracing is beta** — "span
names and attributes may change between releases" (`:156`).

Confirmed in the changelog that this nesting was a fix, not original behavior —
`$CC/changelog.md:1390`: "Added `agent_id` and `parent_agent_id` attributes to
`claude_code.tool` OTEL spans, and **fixed trace parenting so background subagent spans nest
under the dispatching Agent tool span**." And `$CC/changelog.md:1623`: "API requests from
subagents now carry `x-claude-code-agent-id` / `x-claude-code-parent-agent-id` headers."

⚠️ **Two silent-loss traps in the telemetry path**, both at `$CC/agent-sdk__observability.md`:

- `:106` — "**The CLI fails silently on export errors by default**: if the endpoint is unreachable
  or rejects the data, the agent still runs normally and the CLI drops the telemetry without
  surfacing an error." Set `CLAUDE_CODE_OTEL_DIAG_STDERR=1` (v2.1.179+) to see them.
- `:118` — "**If your process is killed before the CLI shuts down, anything still in the batch
  buffer is lost.**" Metrics default to a 60s export interval; traces/logs 5s. For a short-lived
  agent, most of its telemetry may never leave the process. Directly relevant to any unattended
  team run that gets SIGTERM'd.

#### ⚠️ The SDK undercount — `usage` excludes subagents

`$CC/agent-sdk__cost-tracking.md:58-64`, and this is a genuine footgun:

> "The three result-level fields differ in what they count when the agent spawns subagents. **Use
> `modelUsage`, or `model_usage` in Python, for whole-tree token accounting; the `usage` field
> undercounts as soon as nesting occurs.**"

| Field | Subagent activity |
|---|---|
| `usage` | **Excluded.** "Counts only the top-level agent loop, so tokens consumed inside subagents are not added" |
| `total_cost_usd` | Included |
| `modelUsage` / `model_usage` | Included, **broken down by model** |

The obvious-looking field is the wrong one. Any cost measurement of a delegating design that
reads `usage` will report a number that looks plausible and is systematically low — a probe that
can only under-report. `modelUsage` is also the right field for a mixed-model team ("Haiku for
subagents and Opus for the main agent", `:156`).

Caveat the docs attach — `$CC/agent-sdk__cost-tracking.md:20`: "Use these fields for development
insight and approximate budgeting. **For authoritative billing, use the Usage and Cost API** or
the Usage page in the Claude Console. Do not bill end users or trigger financial decisions from
these fields."

#### `/usage` and the dashboards

- `/usage` **does** break down by subagent — `$CC/changelog.md:1320`: "`/usage` now shows a
  per-category breakdown of what's driving your limits usage — **skills, subagents, plugins**,
  and per-MCP-server cost." VS Code got the same at `$CC/changelog.md:918` ("cache misses, long
  context, subagents, and per-skill/agent/plugin/MCP breakdowns over the last 24h or 7d"). Both
  are **changelog-only claims** — I found no `costs.md`/`interactive-mode.md` prose describing
  the subagent category, so treat the exact UI as version-dependent.
- Advisor spend rolls into the session total — `$CC/advisor.md:128`: "Advisor usage counts toward
  the session totals shown by `/usage`."
- **`analytics.md` is out of scope for per-agent attribution.** It is entirely org/user-level:
  the Teams/Enterprise dashboard, contribution metrics, a leaderboard, and per-user spend export
  (`$CC/analytics.md:13-27`, `:193`, `:212`). Control-armed: `grep -niE 'agent|team|subagent'
  analytics.md` returns 14 lines, **every one** of which uses "team" in the *billing-plan* sense
  ("Claude for Teams", "team insights", "team members") — **zero** hits for subagent-level
  attribution. The probe sees the file; the content genuinely isn't there. `$CC/analytics.md:27`
  routes per-agent questions back to OTEL.
- Metric breakdown dimensions — `$CC/monitoring-usage.md:1111`: `claude_code.token.usage` can be
  broken down "by `type` (input/output), user, team, model, `skill.name`, `plugin.name`, or
  `agent.name`" — and `:1122` names "attributing spend to specific skills, plugins, or subagent
  types" as a supported use case. **That stated capability is exactly what the `:533` redaction
  removes for user-defined agents.** Two lines in the same file, in tension; `:533` is the
  specific rule and wins.
- Statusline gets `agent.name` too — `$CC/statusline.md:201`: "Agent name when running with the
  `--agent` flag or agent settings configured."

**Control arm.** Positive: `grep -rn 'agent_id' *.md` → hits in 9 files incl.
`llm-gateway-protocol.md`, `monitoring-usage.md`, `hooks.md`. Negative, fresh term `vtqzbmr`:
`grep -rl 'vtqzbmr' *.md` → **0 files**. Discriminates.

---

### Q6 — Security: delegated agents and permission boundaries

**Answer: permissions ratchet only one way — DOWNWARD from parent to child, never upward, and
never sideways between peers. An agent CANNOT escalate another agent's permissions, and the docs
say so explicitly, naming the confused-deputy attack it prevents. The real risk runs the other
direction: a permissive parent FORCES its mode onto every child, and that cannot be overridden.**

#### Can one agent escalate another's? — explicitly NO

`$CC/agent-teams.md:265` is the decisive passage, and it is unusually direct:

> "When one agent sends another a message over `SendMessage`, **the receiving agent is told it came
> from another Claude session, not from you. A teammate cannot approve a permission prompt or
> supply consent on your behalf, and a teammate that was denied an action cannot relay it to
> another teammate to bypass the check.** In auto mode, the classifier treats **an approval claim
> relayed from another agent as untrusted input** rather than confirmation from you."

Three separate controls in one paragraph, and each closes a distinct attack:

| Control | Attack closed |
|---|---|
| Inter-agent messages are labeled as machine-origin | An agent impersonating the user |
| A teammate cannot approve a prompt or consent on your behalf | Delegated consent laundering |
| A denied agent cannot relay the action to a peer | **Confused deputy / deny-shopping** |
| The auto-mode classifier treats relayed approval claims as untrusted | Social-engineering the classifier |

`$CC/agent-teams.md:267`: "Teammate permission prompts appear in the lead session, so approve
them there yourself. Plan approval is the designed exception: the lead session grants teammate
plan approvals **without a separate prompt to you.**" — so there is exactly **one** documented
authority the lead exercises without you, and it is scoped to plan approval, which by
construction gates a read-only→write transition rather than an arbitrary action.

⚠️ **The lead's plan approval is autonomous** — `$CC/agent-teams.md:156`: "The lead makes approval
decisions **autonomously**. To influence the lead's judgment, give it criteria in your prompt."
That is an LLM judging an LLM's plan, with no deterministic gate. For risky work the criteria go
in the prompt, and prompt-carried criteria are the weakest enforcement layer this repo
recognises (`mise-tasks-only.md`: "markdown alone is 'relying on the LLM', never the only layer").

#### The downward ratchet — the direction that IS dangerous

`$CC/sub-agents.md:449`: "Subagents **inherit the permission context from the main conversation
and can override the mode, except when the parent mode takes precedence** as described below."

`$CC/sub-agents.md:465`:

> "**If the parent uses `bypassPermissions` or `acceptEdits`, this takes precedence and can't be
> overridden.** If the parent uses auto mode, the subagent inherits auto mode and any
> `permissionMode` in its frontmatter is **ignored**: the classifier evaluates the subagent's tool
> calls with the same block and allow rules as the parent session."

Restated in the SDK docs — `$CC/agent-sdk__permissions.md:123`: "an `AgentDefinition`'s
`permissionMode` can override it, except when the parent uses `bypassPermissions`, `acceptEdits`,
or `auto`: those modes apply to **every** subagent and can't be overridden per subagent." And the
warning at `:125`:

> "Subagents may have **different system prompts and less constrained behavior** than your main
> agent, so inheriting `bypassPermissions` grants them **full, autonomous system access**."

⚠️ **The asymmetry an agent-team design must not miss.** A *permissive* parent mode is forced
downward and is un-overridable. A *restrictive* parent mode is NOT: the docs say subagents "can
override the mode" with only the three permissive parent modes listed as exceptions. So a
subagent definition carrying `permissionMode: bypassPermissions` under a `default`-mode parent
appears to get bypass. **I did not find a sentence stating a ceiling for that direction —
marking it UNVERIFIED rather than asserting it**, but it is the single most important thing to
test before shipping a design that loads third-party agent definitions. The mitigations that
*are* documented are the ones below.

What still prompts even under `bypassPermissions` — `$CC/sub-agents.md:462`: "Explicit `ask`
rules, connector tools your organization set to `ask`, MCP tools marked `requiresUserInteraction`,
and root and home directory removals such as `rm -rf /` still prompt." And the blast radius when
it is on — `$CC/sub-agents.md:460`: it allows writes to "`.git`, `.config/git`, `.claude`,
`.vscode`, `.idea`, `.husky`, `.cargo`, `.devcontainer`, `.yarn`, and `.mvn`." **A
`bypassPermissions` subagent can rewrite `.claude/` — i.e. edit the very settings and hooks that
constrain it.** For this repo, whose entire guard layer lives in `.claude/settings.json` +
`scripts/pretooluse-guard.sh`, that is a self-disabling path.

#### Teammates: same story, coarser

- `$CC/agent-teams.md:263`: "Teammates start with the lead's permission settings. **If the lead
  runs with `--dangerously-skip-permissions`, all teammates do too.** After spawning, you can
  change individual teammate modes, but **you can't set per-teammate modes at spawn time.**"
  Repeated at `:428`. So there is **no least-privilege spawn** for teammates — you cannot give the
  reviewer read-only and the implementer write at creation time; you spawn them all at the lead's
  level and downgrade afterwards, leaving a window.
- `$CC/agent-teams.md:211`: "you stay in control. Claude won't spawn teammates without your
  approval."
- `$CC/agent-teams.md:145-154`: plan-approval mode is the designed least-privilege pattern —
  "The teammate works in **read-only plan mode** until the lead approves their approach," with a
  reject→revise→resubmit loop.
- `$CC/agent-teams.md:323`: teammates "load project context automatically, including CLAUDE.md,
  MCP servers, and skills, but **they don't inherit the lead's conversation history.**"

#### The gates that actually constrain a delegated agent

| Lever | What it does | Cite |
|---|---|---|
| `Agent(AgentName)` deny rules | Block a specific subagent type, e.g. `"deny": ["Agent(Explore)"]` | `$CC/permissions.md:377-390` |
| `Agent(model:opus)`, `Agent(isolation:worktree)` | **Parameter-scoped** rules on the Agent tool itself — gate delegation by requested model or isolation | `$CC/permissions.md:100-101` |
| Deny the `Agent` tool | Stops all delegation | `$CC/sub-agents.md:84` |
| `Agent(agent_type)` in `tools` | Restrict which types a `--agent` main thread may spawn | `$CC/sub-agents.md:376` |
| `strictPluginOnlyCustomization` | "Block skills, agents, hooks, and MCP servers from user and project sources, so they can only come from plugins or managed settings" — `true`, or an array like `["skills","hooks"]` | `$CC/permissions.md:507` |
| `disableSideloadFlags` | Reject `--plugin-dir`, `--plugin-url`, **`--agents`**, `--mcp-config` at startup; without it "users can bypass `strictKnownMarketplaces` for a single run" | `$CC/permissions.md:501` |
| Plugin-agent field exclusion | `hooks`/`mcpServers`/`permissionMode` unsupported for plugin agents (see **Q2**) | `$CC/plugins-reference.md:74` |

⚠️ **Parameter-rule gotchas that make a gate silently not fire** — `$CC/permissions.md:106-110`:
only *direct* fields of the tool input are matchable (not nested); one parameter per rule
(`Agent(model:opus)` and `Agent(isolation:worktree)` must be two rules); **"a parameter the model
omits is never matched, so `Agent(model:*)` doesn't match a call that leaves `model` unset"**; and
the value is compared "against the literal input Claude sends, **before any normalization**", so
`Agent(model:opus)` matches the alias but **not a full model ID**. Every one of those is a way to
write a rule that can only pass — precisely the `probes-need-a-control-arm.md` failure shape, in
the permission system.

MCP restrictions do reach subagent frontmatter as of v2.1.153 (`$CC/sub-agents.md:435-443`), and
"managed-settings restrictions apply to every subagent regardless of how it is defined" — but
note the carve-out at `:443`: "`--strict-mcp-config` **doesn't filter servers you pass inline via
`--agents` or the SDK `agents` option**, since those are explicit caller input."

**`security.md` is a stub** — score 4, and its agent content is nil; the substance is in
`security-guidance.md`, which is about the **security-review plugin**, not about agent permission
boundaries. Its one relevant sentence is `$CC/security-guidance.md:85`: the end-of-turn review
diffs "everything that changed in the working tree during the turn, including changes from
Claude's edit tools, Bash commands, **and subagents**" — i.e. the security reviewer *does* see
subagent edits even though checkpointing (Q4) does not. Control-armed: `grep -ci 'subagent'
security-guidance.md` → 1, control `grep -ci 'review'` → high. The single hit is real, not a
probe failure.

**Control arm.** Positive: `grep -rn 'bypassPermissions' *.md` → present across `sub-agents.md`,
`agent-sdk__permissions.md`, `permission-modes.md`. Negative, fresh term `wnbqxlj`:
`grep -rl 'wnbqxlj' *.md` → **0 files**. Discriminates.

---

### Q7 — `agent-sdk__*`: mechanics the CLI docs omit, and where they disagree

The SDK pages are the **type reference** for the same engine — `$CC/agent-sdk__observability.md:22`:
"The Agent SDK **runs the Claude Code CLI as a child process** … The SDK does not produce
telemetry of its own." So an SDK type is describing the CLI's real behavior, and where the two
differ, the SDK page is usually the more complete one rather than a different product.

#### ⚠️ CONTRADICTION 1 — `isolation: "remote"` exists in the SDK types and NOWHERE in the CLI docs

| Source | Documented values |
|---|---|
| `$CC/agent-sdk__typescript.md:2262` | `isolation?: "worktree" \| "remote";` |
| `$CC/agent-sdk__python.md:2474` | `"isolation": "worktree" \| "remote" \| None,  # Isolation mode for the agent's changes` |
| `$CC/sub-agents.md:290` (frontmatter table) | **`worktree` only** — no mention of `remote` |
| `$CC/plugins-reference.md:74` | "The only valid `isolation` value is `"worktree"`" |
| `$CC/worktrees.md` | `worktree` only |

**Control arm.** Corpus-wide `grep -rn` for an `isolation`-adjacent `remote` returns exactly
**2 hits, both in the SDK type files**. Same command shape sees `isolation` **6 times in
`sub-agents.md`**, 2 in `plugins-reference.md`, 3 in each SDK file — so the probe reads the CLI
pages fine and the absence is real, not a blind spot.

Reconciliation: `plugins-reference.md:74` is scoped to **plugin-shipped** agents, so it is not
strictly contradictory — a plugin restriction, not a global one. But `sub-agents.md:222` claims
`--agents` JSON "accepts … the same frontmatter fields as file-based subagents" and enumerates
sixteen of them **including `isolation`**, while the frontmatter table it points at documents only
one of the two values the SDK type declares. **A second, cloud-backed isolation mode is a
first-class design option that a CLI-docs-only reading of this corpus would never surface.**
(It is also live in this very session's Agent tool schema, which describes `remote` as launching
the agent in a remote cloud environment, always backgrounded and gated by availability — an
external corroboration, though outside the assigned corpus.)

#### ⚠️ CONTRADICTION 2 — `TeammateIdle` is TypeScript-only in the SDK, but unqualified in the CLI docs

`$CC/agent-sdk__hooks.md:170` — event compatibility table: `TeammateIdle` → **Python SDK: No**,
TypeScript SDK: Yes. Corroborated at `$CC/agent-sdk__claude-code-features.md:285`: "The TypeScript
SDK supports additional hook events beyond Python, including `SessionStart`, `SessionEnd`,
**`TeammateIdle`**, and `TaskCompleted`."

`$CC/hooks.md:55`, `:244`, `:714`, `:2310` document `TeammateIdle` with no language caveat, since
the CLI is language-agnostic. Not a factual contradiction, but a **capability trap**: a team
design that leans on `TeammateIdle` to reassign idle workers is not portable to the Python SDK.
Given this repo is Python-first (`python/src/dotfiles_setup/`), that matters here specifically —
though note the *filesystem* hook path (a `command` hook in `settings.json`) is unaffected, since
that runs a process rather than a Python callback.

`TeammateIdle` semantics worth carrying regardless — `$CC/hooks.md:2314`: "When a `TeammateIdle`
hook exits with code **2**, the teammate **receives the stderr message as feedback and continues
working** instead of going idle. To stop the teammate entirely, return
`{"continue": false, "stopReason": "..."}`. TeammateIdle hooks don't support matchers and fire on
every occurrence." **This is the harness's built-in answer to the "agent went idle without
delivering" failure this repo has hit twice** (`feedback_agent_team_delivery_discipline`): a
deterministic hook that re-prompts an idling teammate. Strictly stronger than a prose rule in the
agent definition, because it is a gate rather than an instruction.

#### SDK-ONLY mechanics with no CLI counterpart

**`criticalSystemReminder_EXPERIMENTAL`** — `$CC/agent-sdk__typescript.md:780`, `:799`:
"Experimental: Critical reminder added to the system prompt." **Control-armed: 2 hits corpus-wide,
both in `agent-sdk__typescript.md`.** Not in the Python SDK, not in `sub-agents.md`. A per-agent
elevated-priority instruction channel — conceptually the per-agent analogue of
`--append-subagent-system-prompt`. Experimental and TS-only; do not design on it, but know it
exists.

**`disallowedTools` accepts MCP server-level patterns** — `$CC/agent-sdk__typescript.md:788`:
"MCP server-level patterns are also accepted: `mcp__server` or `mcp__server__*` removes every
tool from that server, and **`mcp__*` removes every MCP tool from any server**." A one-line way
to build an MCP-free agent. `$CC/sub-agents.md`'s `disallowedTools` row does not spell this out.

**A scoped deny rule survives `bypassPermissions`** — `$CC/agent-sdk__typescript.md:418`
(mirrored at `$CC/agent-sdk__python.md:836`): "A bare name such as `"Bash"` **removes the tool
from Claude's context**. A scoped rule such as `"Bash(rm *)"` **leaves the tool available and
denies matching calls in every permission mode, including `bypassPermissions`**." This is a
second Q6 answer and a better one than the mode system: the two forms are not
strength-ordered variants, they are **different mechanisms** — removal vs. interception — and
only the scoped form is un-bypassable. The CLI `permissions.md` does not state the
`bypassPermissions` guarantee this plainly.

**`model: 'inherit'`** — the SDK field table names `'fable'`, `'opus'`, `'sonnet'`, `'haiku'`,
`'inherit'`, or a full model ID; "If omitted or `'inherit'`, uses the main model."

**`effort` accepts an integer**, not just the named levels — SDK type:
`effort?: "low" | "medium" | "high" | "xhigh" | "max" | number`.

**`AgentMcpServerSpec` is a string OR an inline config** — `$CC/agent-sdk__typescript.md:801-806`:
either "a server name (string referencing a server from the parent's `mcpServers` config)" or an
inline record. The string form is a **reference to the parent's** server — i.e. per-agent MCP
scoping by name, which is the clean way to give one agent a server and not another.

**`tools` vs `skills`, stated as a rule** — `$CC/agent-sdk__typescript.md:787`: "To preload Skills
into the agent's context, use the `skills` field rather than listing `'Skill'` here." This sharpens Q1:
`Skill` in `tools` grants *runtime invocation*; `skills:` does *startup injection*. Different
mechanisms, easily conflated.

**`SubagentStop` carries `background_tasks` and `session_crons`** —
`$CC/agent-sdk__typescript.md:1780-1781` types them; `$CC/hooks.md:2050` and `:2198` confirm on
the CLI side (v2.1.145+) that they "let hooks distinguish **'session is done' from 'session is
done but work is still running'**". For a team teardown gate, that distinction is the whole
question. Also present on `Stop` (`$CC/hooks.md:2194`). Not an SDK/CLI conflict — both document
it — but the SDK gives the exact shape (`BackgroundTaskSummary`, `SessionCronSummary`).

#### The parity table — the single most useful page nobody was assigned

`$CC/agent-sdk__claude-code-features.md:293-302` maps goals to surfaces, and is where the
**agent-teams-are-CLI-only** fact (Q3) is stated most plainly (`:300`). Its subagent row (`:299`):
"Delegate an isolated subtask to a fresh context (research, review) → Subagents →
**`agents` parameter + `allowedTools: ["Agent"]`**" — note delegation requires *explicitly
allowing the `Agent` tool*, which is easy to forget when constructing a restricted `tools` list.

Hook-type guidance from the same page (`:281-282`) that the CLI hooks page states less directly:
filesystem hooks are "for sharing hooks between CLI and SDK sessions … **These fire in the main
agent and any subagents it spawns**"; programmatic callbacks "**also fire inside subagents**", and
their input "carries `agent_id` and `agent_type` fields that identify which agent fired the hook."
Matches `$CC/hooks.md:193`. ⚠️ **Every hook in this repo's `settings.json` therefore also runs
inside every subagent** — including `branch_guard`, which is why (per
`project_session_2026-08-03-h`) it blocks subagent report writes on `main`. The docs predicted
that; it was discovered empirically.

#### Sandbox escape, stated only in the SDK docs

`$CC/agent-sdk__python.md:3728` / `$CC/agent-sdk__typescript.md:4814`, verbatim:

> "If `permission_mode` is set to `bypassPermissions` **and** `allow_unsandboxed_commands` is
> enabled, the model can autonomously execute commands outside the sandbox without approval
> prompts (an explicit `ask` rule still forces one). **This combination effectively allows the
> model to escape sandbox isolation silently.**"

And `:3592` / `:4706`: "allowing `/var/run/docker.sock` effectively grants **full host system
access** through the Docker API, **bypassing sandbox isolation**." ⚠️ Directly relevant to this
repo, which is Docker-Desktop-based and mounts sockets into the devcontainer. This warning
appears **only** on the SDK pages — a Q6 answer that a CLI-only sweep would have missed entirely.

---

## Summary — the six things a team design should not ship without

1. **Agent teams cannot run unattended.** CLI-only, not SDK-configurable
   (`agent-sdk__claude-code-features.md:300`), zero headless documentation (control-armed), and
   the one relevant sentence advises against it (`agent-teams.md:374`). Build unattended work
   from **subagents** or from N orchestrated `claude -p` processes.
2. **`/rewind` does not cover delegated work.** Not subagent edits, not Bash, not teammates
   (`checkpointing.md:82`, `agent-teams.md:421`). Git is the only recovery path the docs offer —
   which validates this repo's branch-before-writing posture.
3. **`disable-model-invocation: true` skills can never be preloaded** (`sub-agents.md:485`). Nine
   of this repo's protocol verbs are in that class, so `skills:` cannot carry them into an agent.
4. **Permissions ratchet down only.** Peer escalation is explicitly blocked
   (`agent-teams.md:265`); a permissive parent is forced on every child and un-overridable
   (`sub-agents.md:465`); teammates have **no least-privilege spawn** (`agent-teams.md:263`).
5. **Per-agent cost attribution must key on `agent_id`, not `agent.name`** — user-defined agent
   names are redacted to `"custom"` (`monitoring-usage.md:533`) — and SDK `usage` **undercounts
   subagents**; use `modelUsage` (`agent-sdk__cost-tracking.md:58`).
6. **A `TeammateIdle` hook exiting 2 re-prompts an idling teammate** (`hooks.md:2314`). This is a
   deterministic gate for the exact delivery failure this repo has hit twice with prose rules.

### Method caveats, stated

- The corpus is a **local snapshot** of `code.claude.com/docs/en/*`, not a live fetch. Everything
  above is version-annotated where the docs annotate it; several mechanics are v2.1.211–2.1.219,
  i.e. very recent. I did **not** verify the snapshot's date against the live site — treat
  version-sensitive claims as "true as of this snapshot".
- Two claims are marked **UNVERIFIED** in-line and should not be repeated as findings: whether a
  subagent's `permissionMode` can exceed a *restrictive* parent (Q6), and whether built-in agents
  are absent by default under `-p` (Q3).
- The 40-minute agent-death correlation with `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` (Q3) is a
  **lead, not a diagnosis** — the 40-minute figure is inherited from a prior session's note and
  was not re-measured here, and the documented abort behavior ("surfacing any partial result to
  the parent") does not cleanly match the reported "left nothing".
- Every absence claim carries both arms with a control term invented fresh for that probe.
  Negative controls used, all returning 0 files: `qwvbrtz`, `zmqvftk`, `pxjwnqd`, `hkzvrtp`,
  `vtqzbmr`, `wnbqxlj`. **These are now published and are burned** — a future probe must invent
  new ones (`probes-need-a-control-arm.md`, rule 3).

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the offline
  `sources/agent-harness-docs/docs/claude-code` corpus that is the entire evidence base for this
  report; read only, nothing written.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; the report file
  is the only artifact written.

_No third-party repos were fetched. No network requests were made: the corpus is on disk and
`graphify` queried only the local project graph._
