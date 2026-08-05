# Claude Code Subagent Surface — Deep Reference

**Status:** COMPLETE — all 9 briefed areas covered, open items enumerated at the end.
**Audience:** agent-team design for `ray-manaloto/dotfiles`
**Primary source:** `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/` (cited below as `$CC`)
**Companion report (read first, not re-derived here):** `docs/research/kb/reports/agents/harness-settings-reference.md` — 16 frontmatter fields, env-var tables, partial mode-applicability matrix.

## Source discipline

- `$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.
- Every claim carries `file:line`. A claim without one is labelled **UNVERIFIED**.
- Every absence claim is control-armed: a known-present term grepped with the **same command shape**, plus a freshly-invented known-absent term. Controls are invented per-run and are **not** reused from earlier reports (a published control string is in the corpus and stops discriminating).
- Enumerations are done **by shape** (regex over the token class), not by grepping the names I expected to find.

**Global control arm for this report** (run once, applies to every `grep -c` below):

```
grep -c -i 'subagent'  $CC/sub-agents.md   → 276   (known-present)
grep -c -i 'qwzzlemop' $CC/sub-agents.md   → 0     (known-absent, invented this run)
```

The probe discriminates in both directions.

## 1. Tool filtering — the two filters

`$CC/sub-agents.md:324` states the count explicitly and it is exactly two:

> "Subagents inherit the built-in tools and MCP tools available in the main conversation, **narrowed by two filters**: the first removes a short list of tools from every subagent, and the second reduces the built-in tool set for subagents that run in the background, which is the default. **Forks skip both filters** and receive the main conversation's exact tool pool."

Control arm for "exactly two, no third": `grep -n -i 'filter' $CC/sub-agents.md` returns 6 hits (`324`, `336`, `444`, `1041`, `1163`, `1199`). `444` is MCP-server filtering (`--strict-mcp-config`), `1041` is the fork comparison table pointing back at this same section, and `1163`/`1199` are SQL prose in an example agent. No third tool filter exists in the page.

### Filter 1 — removed from EVERY subagent (`sub-agents.md:326–334`)

Nine entries. Three are **conditional**, which is the load-bearing part:

| Tool | Condition | Line |
|---|---|---|
| `Agent` | Removed **only at the [depth limit](#8-every-limit-and-its-failure-message)**. In a **fork** the tool stays listed but *returns an error instead of spawning* | `326` |
| `AskUserQuestion` | Unconditional | `327` |
| `EndConversation` | Unconditional — "can end only the main conversation" | `328` |
| `EnterPlanMode` | Unconditional | `329` |
| `ExitPlanMode` | Removed **unless** the subagent's `permissionMode` is `plan` | `330` |
| `ScheduleWakeup` | Unconditional | `331` |
| `TaskOutput` | Unconditional | `332` |
| `WaitForMcpServers` | Unconditional | `333` |
| `Workflow` | Unconditional | `334` |

"even when listed in the `tools` field" (`324`) — filter 1 is not overridable by frontmatter.

### Filter 2 — background subagents (`sub-agents.md:336`)

This filter is an **allowlist of built-ins**, not a removal list. A background subagent "keeps every MCP tool but only these built-in tools" — **19 tools**:

`Read`, `Grep`, `Glob`, `Bash`, `PowerShell`, `Edit`, `Write`, `NotebookEdit`, `WebFetch`, `WebSearch`, `TodoWrite`, `Skill`, `ToolSearch`, `EnterWorktree`, `ExitWorktree`, `Monitor`, `TaskStop`, `SendMessage`, `Artifact`

Plus `Agent` and `ExitPlanMode`, which "follow the first filter's conditions wherever the subagent runs" (`336`) — i.e. they are *not* governed by filter 2 at all, so a background subagent below the depth limit still has `Agent`.

Three consequences stated in the same line, each of which matters for team design:

1. **Every other built-in is removed** "whether inherited or **listed in the `tools` field**" — so filter 2 is also not overridable by frontmatter.
2. **"The same definition can resolve to different tools in the foreground and the background."** An agent definition is therefore not a stable capability contract; the capability depends on where it ran.
3. **"The removal reports no error"** unless it empties the `tools` list entirely (→ `$CC/errors.md`, §8). A definition listing only removed tools degrades **silently**.

### Filter 2 addendum — agent-team teammates (`sub-agents.md:338`)

> "Teammates in agent teams additionally keep the task tools and cron tools: `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `CronCreate`, `CronDelete`, and `CronList`."

Seven additions. Note the asymmetry: `TaskStop` is in the base background set (`336`), the other four `Task*` verbs are teammate-only. `TaskOutput` is removed by **filter 1** and is therefore *never* available to a teammate.

### The prior measurement: CONFIRMED, with one measured discrepancy

The brief asks me to confirm or refute "a teammate running with the background set". I am myself a teammate in this session, so this is a first-party observation of my own tool pool.

**Confirmed** — my pool is the background set plus the teammate task/cron block:

- Present and background-set: `Read`, `Bash`, `Edit`, `Write`, `NotebookEdit`, `WebFetch`, `WebSearch`, `Skill`, `ToolSearch`, `EnterWorktree`, `ExitWorktree`, `Monitor`, `TaskStop`, `SendMessage`, `Artifact` — 15 of 19.
- Present and teammate-only (`338`): all 7 of `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `CronCreate`, `CronDelete`, `CronList`. **7/7 — this is the strongest confirmation in the observation**, because those tools appear in no other documented set.
- Present: `Agent` — consistent with `326` (I am below the depth limit).
- Absent: every one of filter 1's unconditional entries. `AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `ScheduleWakeup`, `TaskOutput`, `WaitForMcpServers`, `Workflow` — **7/7 absent**, exactly as `327–334` predicts. (`EndConversation` is named in my system prompt as a deferred tool retrievable via `ToolSearch`, which is a *harness-prompt* mention, not an available tool; treat that as a caveat on this one row rather than a refutation.)
- Absent: `ExitPlanMode` — consistent with `330`, since my `permissionMode` is not `plan`.

**Discrepancy — 4 of the 19 documented background built-ins are absent from my pool:** `Grep`, `Glob`, `TodoWrite`, `PowerShell`.

- `PowerShell` is explained by platform (this host is `darwin`); not a doc discrepancy.
- `Grep`, `Glob`, `TodoWrite` are **genuinely absent** and are documented as kept.

⚠️ **This is a discrepancy, not a refutation, and I cannot close it from inside.** Filter 2 is an *upper bound* on built-ins, and it composes with the `tools`/`disallowedTools` fields (`340–360`) and with whatever the spawning lead passed. A lead that spawned me with an explicit narrower `tools` list produces exactly this observation with the docs being entirely correct. I have no visibility into my own spawn parameters, so the honest verdict is:

> **The teammate tool set matches the documented background set + teammate additions on 22 of 26 rows and on all 14 filter-1 predictions. The 3 unexplained absences (`Grep`, `Glob`, `TodoWrite`) are consistent with either an explicit narrowing at spawn time or a doc/implementation gap; distinguishing them requires reading the spawn call, which a subagent cannot see.**

Design consequence regardless of which it is: **do not assume `Grep`/`Glob` in a teammate brief.** Write briefs against `Bash` (`grep`/`rg` as shell commands), which was present. That is what this report was researched with.

## 2. `AskUserQuestion` removal and the escalation path

### Confirmed, twice, from two independent pages

1. `$CC/sub-agents.md:327` — `AskUserQuestion` is listed in filter 1, removed from **every** subagent "even when listed in the `tools` field" (`324`).
2. `$CC/agent-sdk__user-input.md:839` — under **Limitations**: *"**Subagents**: `AskUserQuestion` is not currently available in subagents spawned via the Agent tool"*.

Two routes, same answer. No page in the corpus contradicts it (18 files mention `AskUserQuestion`; none carves out a subagent exception).

A third, easily-missed instance: `$CC/sub-agents.md:455` — under `permissionMode: dontAsk`, `AskUserQuestion` is **denied even if you've explicitly allowed it**. So there are two independent mechanisms that remove it, and `dontAsk` removes it from the *main* session too.

### The escalation path: there is NO documented one. This is a real gap.

I looked for one by shape, not by expectation, and control-armed the zero.

```
grep -c -i 'AskUserQuestion' $CC/agent-teams.md  → 0     ← the question
grep -c -i 'escalat'         $CC/agent-teams.md  → 0     ← the question
grep -c -i 'teammate'        $CC/agent-teams.md  → 127   ← control (present)
grep -c    'SendMessage'     $CC/agent-teams.md  → 2     ← control (present, low-frequency)
grep -rl   'vrompkiz'        $CC/               → 0     ← control (invented, absent)
grep -rl   'Bash'            $CC/               → 87    ← control (present, same shape)
```

Both arms fire. **`agent-teams.md` — the page that governs multi-agent work — never once uses the word "escalate" and never mentions `AskUserQuestion`.** The 127-hit control proves the file is about teammates and the probe can see it.

### Is `SendMessage` to the lead the documented path? NO — the docs say the opposite

This is the sharpest finding in this section, and it inverts the natural assumption.

`$CC/agent-teams.md:265`:

> "When one agent sends another a message over `SendMessage`, the receiving agent is told **it came from another Claude session, not from you**. A teammate **cannot approve a permission prompt or supply consent on your behalf**, and a teammate that was denied an action **cannot relay it to another teammate to bypass the check**. In auto mode, the classifier treats an approval claim relayed from another agent as **untrusted input** rather than confirmation from you."

`$CC/tools-reference.md:47` says the same at the tool level:

> "A receiver **never treats a message from another agent as your consent or approval**." … "As of v2.1.198, a subagent treats a message from the agent that launched it as **normal task direction** rather than as a peer request."

So `SendMessage` is a **work-routing** channel, deliberately hardened *against* being a consent channel. Using it to ask the lead "may I do X?" gets you the lead's answer, which is explicitly **not** the human's answer.

### What the actual escalation path is

Assembled from the pages; the synthesis is mine, each component is cited.

| Situation | Documented mechanism | Cite |
|---|---|---|
| Teammate hits a **permission prompt** | It surfaces **in the lead session**, and the human approves it there. Not the teammate's problem to route. | `agent-teams.md:267`, `:393` |
| Teammate needs **plan approval** | Structured `plan_approval_response` protocol message; **the lead decides autonomously**, with no prompt to the human. The human influences it only by pre-loading criteria into the lead's prompt. | `agent-teams.md:154`, `:156`, `:267` |
| Teammate needs a **decision** (the `AskUserQuestion` case) | **Nothing.** No mechanism documented. | control-armed zero above |
| Teammate **finishes or fails** | Idle notification to the lead automatically; since v2.1.198 an API-error turn-end notifies the lead **with the error text**. | `agent-teams.md:276` |
| Subagent (non-team) wants to reach a peer | Sibling roster system-reminder lists `main` + every named agent as valid `to` values — **only if its tools include `SendMessage`** and at least one other agent has a name. Snapshot at start; later-named agents never appear. | `sub-agents.md:925` |

**The gap, stated plainly:** a delegated agent that needs a human decision has *no* documented way to get one. Its only outbound channel is `SendMessage`, and `SendMessage` is documented as carrying no consent authority. The design must therefore treat every delegated agent as **decision-incapable** and either (a) resolve every decision in the brief before spawning, or (b) have the agent **return** with the decision unmade and let the lead — which *does* have `AskUserQuestion` — ask.

⚠️ **Direct consequence for this repo.** `.claude/rules/clarify-before-acting.md` requires the `AskUserQuestion` *tool* whenever input is needed, and `dotfiles_setup.ask_quality` **denies** a malformed ask via PreToolUse. Neither can fire inside a subagent, because the tool is not there. The rule's own gate is structurally unreachable from delegated work — the enforcement layer covers the lead only. Any team design that delegates judgment-shaped work delegates it past that gate. Option (b) above is the only shape that preserves it.

⚠️ Second-order: the same is true of `feedback_always_offer_clickable_next_step` (every turn with a fork ends in `AskUserQuestion`). A teammate structurally cannot comply. Do not write that requirement into a teammate brief; it can only be satisfied by the lead.

## 3. Forks

**Definition** (`sub-agents.md:1004`): "A fork is a subagent that inherits the entire conversation so far instead of starting fresh. This **drops the input isolation** that subagents otherwise provide: a fork sees the same system prompt, tools, model, and message history as the main session… The fork's own tool calls still stay out of your conversation and only its final result comes back."

So a fork is **input-transparent, output-isolated** — the mirror image of a named subagent, which is input-isolated and output-isolated.

### Invocation and the command rename

| Version | Command | Cite |
|---|---|---|
| v2.1.212+ | `/subtask` | `:997`, `:1013` |
| v2.1.161 – v2.1.211 | `/fork` | `:999`, `:1013` |
| v2.1.117 – v2.1.160 | `/fork`, but required `CLAUDE_CODE_FORK_SUBAGENT=1` unless a server-side rollout enabled it | `:999` |

⚠️ **`/fork` did not disappear — it was repurposed, and the two meanings are opposites.** On v2.1.212+ `/fork` "copies the whole session into a new **background session**" (a separate session with its own budget), while `/subtask` starts the forked *subagent* (`:997`). Exception: "When agent view is turned off, `/subtask` isn't available and **`/fork` starts the forked subagent instead**" (`:997`). A doc or script written before v2.1.212 that says `/fork` means the subagent is now wrong in the default configuration.

### `CLAUDE_CODE_FORK_SUBAGENT`

Tri-state, and it does more than gate the feature (`:1006`, `:1008–1011`, `:1052`):

- `=1` — enables fork mode explicitly, in "interactive mode, non-interactive mode, and the Agent SDK" (`:1006`, `:1052`).
- `=0` — disables fork mode **everywhere, including any server-side rollout** (`:1052`). This is the only documented way to opt out of the staged rollout.
- unset — staged rollout decides.

**Enabling it changes two unrelated things** (`:1008`):

1. Claude can spawn a fork by requesting the `fork` subagent type explicitly. Untyped requests still get `general-purpose`; named subagents still spawn normally (`:1010`).
2. ⚠️ **Every subagent runs in the background — fork or not** (`:1011`). And `:783`: "the frontmatter `background` field has no effect, because fork mode **removes the `run_in_background` parameter from the `Agent` tool**." `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` takes precedence and keeps them in the foreground (`:783`, `:1011`).

That second effect is the trap: setting this variable to get forks silently forces **every** named subagent in the session into the background, which per §1 **changes their tool sets**. A definition that worked in the foreground can resolve to fewer tools purely because someone enabled forks.

### What a fork inherits — and the two things it does NOT

`sub-agents.md:1038–1044` (the comparison table), plus `:916`, `:933`:

| | Fork | Named subagent |
|---|---|---|
| Context | Full conversation history | Fresh context + delegation prompt |
| System prompt and tools | **Same as main session** | From the definition, filtered for background runs |
| Model | Same as main session | From the `model` field |
| Permissions | Prompts surface in your terminal | Prompts surface in your main session (background) |
| Prompt cache | **Shared with main session** | Separate cache |

Also inherited, called out separately because they are exceptions to the "some state never reaches a subagent" list: the **output style** reaches a fork (`:933`) and the full conversation reaches it (`:916`).

**NOT inherited / not available:**

- **A fork can't spawn further forks** (`:1052`). Flat, one level, unconditionally.
- `Agent` **at the depth limit**: "A fork at the limit keeps `Agent` in its inherited tool list, but the tool returns an **error** instead of spawning" (`:862`, `:326`). This is a distinct failure shape from a named subagent, which simply doesn't have the tool — a fork's `Agent` looks available and fails at call time.

### Tool filtering: a fork skips BOTH filters

`:324` — "**Forks skip both filters** and receive the main conversation's exact tool pool." Restated at `:770` ("Background subagents run with a smaller built-in tool set than foreground subagents, **except for conversation forks**").

So a fork is the **only** way to get a delegated agent with `AskUserQuestion`, `Workflow`, `TaskOutput`, `EnterPlanMode`, `ScheduleWakeup`, `WaitForMcpServers`, or `EndConversation` — those are filter-1 removals and filter 1 does not apply to forks.

⚠️ **UNVERIFIED nuance, flagged rather than asserted.** `:324`/`:770` say forks skip both filters and get the main conversation's *exact* pool. `:326` and `:328` nonetheless describe fork-specific behavior for `Agent` (errors instead of spawning) and note `EndConversation` "can end only the main conversation". Whether a fork's `AskUserQuestion` actually reaches the human, or whether it is present-but-inert like its `Agent`, is **not stated anywhere in the corpus**. Given `agent-sdk__user-input.md:839` scopes its limitation to "subagents spawned via the Agent tool" — which a Claude-spawned fork is — I would not build an escalation path on a fork's `AskUserQuestion` without probing it live. Recorded as an open item.

### Prompt-cache reuse

`:1046` — "Because a fork's system prompt and tool definitions are identical to the parent, its **first request reuses the parent's prompt cache**. This makes forking **cheaper** than spawning a fresh subagent for tasks that need the same context." Cross-ref: `/docs/en/prompt-caching#subagents-and-the-cache`.

This is the one place the docs make an explicit cost claim favouring one delegation shape over another. It cuts against the usual instinct that a fresh subagent is cheaper because its context is smaller: for *the same task context*, the fork wins because the cache hit is free and re-explaining is not.

### How forks count against the limits

Three different answers depending on who started it (`:895`, `:907`):

| What | Session limit (200) | Concurrency limit (20) |
|---|---|---|
| Fork Claude spawns via the `Agent` tool | **Counts** (`:895`) | Counts, and **can be blocked** |
| In-session fork **you** start with `/subtask` | **Counts** — "it spends the same budget" — but the limit "blocks only subagents Claude spawns with the Agent tool, so **your own `/subtask` still starts after Claude reaches the limit**" (`:895`) | "takes a slot while it runs and is **never blocked** by the limit" (`:907`) |
| Session you create with `/fork` (v2.1.212+ meaning) | **Doesn't count** — "runs as a separate background session with its own budget" (`:895`) | Own budget |

The `/subtask` row is the subtle one: it **decrements** the budget but is **not gated** by it. A human can therefore drive the session count past the point where Claude can no longer delegate, and the only symptom is Claude's own `Agent` calls starting to fail.

### Steering a running fork (`:1021–1032`)

Panel below the prompt input, one row per fork plus one for main:

| Key | Action |
|---|---|
| `↑`/`↓` | Move between rows |
| `Enter` | Open the fork's transcript and **send it follow-up messages** |
| `x` | Dismiss a finished fork or stop a running one |
| `Esc` | Return focus to the prompt input |

With a transcript open, follow-up text and **skills** go to that agent, but **built-in commands still run in the main conversation** (`:1032`). As of v2.1.199, `/model` and `/fast` typed in that view show a notice that they change the main conversation, rather than silently doing so.

`isolation: "worktree"` can be passed when Claude spawns a fork through the Agent tool, so its edits land in a separate worktree (`:1048`).

## 4. Background subagents

### The default flipped in v2.1.198

`sub-agents.md:770` — "As of v2.1.198, **subagents run in the background by default**. Claude runs a subagent in the foreground when it needs the result before continuing. Background subagents run with a smaller built-in tool set than foreground subagents, except for conversation forks, and they surface every permission prompt in your main session."

Restated in the frontmatter table at `:288`: `background: true` means "always run this subagent as a background task, **even when Claude needs its result right away**. When unset, Claude chooses, and as of v2.1.198 it runs subagents in the background by default."

So `background` is a three-state field in practice: `true` = forced background; unset = Claude's judgment, defaulting background; and there is **no documented `background: false`**. To get a guaranteed foreground subagent the documented levers are `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` (`:781`) or asking Claude directly (`:776`).

⚠️ **The consequential half of this flip is §1, not scheduling.** Because the background set is a *smaller built-in tool set*, v2.1.198 silently changed what tools an unchanged agent definition resolves to. `:336` names the mechanism: "the same definition can resolve to different tools in the foreground and the background", and "**the removal reports no error**".

### How results return

`:772` (v2.1.211) — "A background subagent's results reach Claude as a **completion notification in a later turn**. Claude waits for that notification before reporting the subagent's results, and if you ask about progress first, it reports that the subagent is still running. Before v2.1.211, Claude sometimes reported results for a background subagent that hadn't finished."

That last sentence is a fixed defect worth carrying: pre-2.1.211, a lead could report a subagent's results **before the subagent finished**. Any project doc that describes the older behaviour is stale.

For forks specifically: "When it finishes, its result arrives as a message in your main conversation" (`:1019`).

### How permission prompts surface

Version-dependent, and the earlier behaviour was silently destructive (`:768`):

| Version | Behaviour on a background subagent's permission-needing tool call |
|---|---|
| < v2.1.186 | **Auto-denied** any tool call that would have prompted |
| ≥ v2.1.186 | "the prompt surfaces in your main session and **names the subagent that is asking**. Approve to let the subagent continue, or press **Esc to deny that one tool call without stopping the subagent**" |

Esc denying *one call* rather than killing the agent is the important detail for a team design — a denial is recoverable, not terminal.

For **agent teams** the same shape holds via a different page: "Teammate permission prompts appear in the lead session, so approve them there yourself" (`agent-teams.md:267`), and "Teammate permission requests bubble up to the lead, which can create friction. **Pre-approve common operations in your permission settings before spawning teammates**" (`agent-teams.md:393`).

### Interaction with agent view / `/tasks`

`:779` (v2.1.208) — "A background subagent that completes **stays listed in `/tasks`**, marked done and sorted below running work, until the session cleans up its task list. Its detail view stays open when the subagent finishes. **Subagents that fail or that you stop leave the list.**"

⚠️ **That asymmetry is an observability hazard.** Completed agents persist in the view; **failed** ones disappear from it. The list is therefore biased toward success — you cannot audit failures from `/tasks`, only from the transcripts (`:967`) or the completion message. Before v2.1.208 even completed ones vanished immediately.

Named background subagents currently running also appear in the **@-mention typeahead**, with their status next to the name (`:725`).

### Turning it off, and the precedence chain

- `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` disables all background task functionality (`:781`).
- It **takes precedence over fork mode** and keeps subagents in the foreground (`:783`).
- Under `CLAUDE_CODE_FORK_SUBAGENT=1`, every subagent is background and `background:` frontmatter is inert, because fork mode removes the `run_in_background` parameter from the `Agent` tool (`:783`).

Resulting precedence: `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` > `CLAUDE_CODE_FORK_SUBAGENT` > frontmatter `background` > Claude's judgment (default background).

### The agent-teams exception — no background subagents from an in-process teammate

`agent-teams.md:426`: "an in-process teammate's own subagents run in the **foreground**. Asking for a background one, whether with `run_in_background` or a subagent definition that sets `background: true`, **returns an error**, because a teammate's background work can't outlive the lead's process."

Two consequences for a team design:

1. A teammate's own subagents get the **foreground** (larger) tool set, so an agent definition behaves *differently* depending on whether the lead or a teammate spawned it.
2. A definition carrying `background: true` is **not portable into a team** — it errors when a teammate uses it. Do not put `background: true` in a definition intended for both paths.

### API errors (`:787–792`)

As of v2.1.199 an API-error death is reported as a failure rather than as findings. The two shapes differ:

- **Foreground**: partial text output is returned with a note that the subagent was cut off. As of v2.1.200, a subagent that produced nothing — or **whose only output was tool calls** — fails with `Agent terminated early due to an API error` plus the detail. (In v2.1.199 exactly, the tool-calls-only shape returned an empty partial result with only the cut-off note.)
- **Background**: "the subagent is **marked failed**, and the message Claude receives when it ends names the API error and **includes the subagent's last output**, so partial work isn't lost."

Recovery: retry, or resume the subagent (`:792`).

### Output scanning (v2.1.210+, `:794–805`)

Every subagent's final report is scanned before Claude reads it, because "text from those sources can carry instructions aimed at the main conversation". The scan **never removes or rewords anything**; it makes two visible changes:

- **Backslash insertion** into text imitating harness output — a `<system-reminder>` tag, or a line starting with `Human:` / `Assistant:`.
- **A marker line** prefixed `[harness: subagent output matched instruction-shaped pattern(s):` when the report imitates such a tag **or mentions permission settings** like `bypassPermissions` or `--dangerously-skip-permissions`. The text itself stays as written.

`:801` is explicit that this is not a security boundary: "The scan doesn't judge whether content is malicious… a tool call the report leads Claude to make still goes through the session's permission checks and sandboxing. **It isn't a substitute for restricting what a subagent can reach.**"

⚠️ Practical note for this repo: a report that *discusses* `bypassPermissions` — which several `.claude/rules/` files and this very report do — will acquire the marker line when returned by a subagent. That is expected and benign, but it means agent reports about permission policy are visibly annotated.

## 5. `memory`

`memory` is a frontmatter field taking one of three scope values. It "gives the subagent a persistent directory that survives across conversations" (`sub-agents.md:495`).

### The three scopes and their exact paths (`sub-agents.md:510–514`)

| Scope | Path | Version-controlled? | Use when |
|---|---|---|---|
| `user` | `~/.claude/agent-memory/<name-of-agent>/` | no (home dir) | learnings should apply across all projects |
| `project` | `.claude/agent-memory/<name-of-agent>/` | **yes — `claude-directory.md:381` badges it `committed`** | project-specific and shareable via VCS |
| `local` | `.claude/agent-memory-local/<name-of-agent>/` | no | project-specific but not checked in |

`<name-of-agent>` is the frontmatter `name`, not the filename (`:277` establishes `name` is the identity). The directory contains a `MEMORY.md` (`claude-directory.md:396`). Directories are "**only created for subagents that set the `memory:` frontmatter field**" (`claude-directory.md:386`).

`project` is the documented recommended default (`:526`).

### What gets written, and by what mechanism

There is **no dedicated memory tool**. `:522` — "**Read, Write, and Edit tools are automatically enabled** so the subagent can manage its memory files." Corroborated for the main-session feature at `agent-sdk__claude-code-features.md:96`: "The agent writes new memories there with the standard `Write` and `Edit` tools rather than a dedicated memory tool, so those tools must be enabled for the agent to save memories."

⚠️ **This is a capability side-effect, not just a storage feature.** Setting `memory:` on a subagent **grants it `Write` and `Edit`**. A definition intended to be read-only (`tools: Read, Grep, Glob`) that also sets `memory: project` is no longer read-only. The docs state the enabling plainly at `:522` but never flag the interaction with a restrictive `tools` list — treat it as an unstated hazard. For this repo's read-only reviewer/auditor agents, `memory:` and "read-only" are in tension.

Content is otherwise agent-authored: the docs give only prompting advice (`:527–536`) — ask it to consult memory before work and update it after, or bake the instruction into the agent's markdown body.

### When it is read

`:521` — the system prompt includes "**the first 200 lines or 25KB of `MEMORY.md`** in the memory directory, **whichever comes first**, with instructions to curate `MEMORY.md` if it exceeds that limit." Confirmed independently at `claude-directory.md:384`: "First 200 lines (capped at 25KB) of MEMORY.md loaded into the subagent system prompt when it runs."

`:520` — the system prompt also includes read/write instructions for the directory.

Note this is the **same budget shape** as main-session auto memory (`claude-directory.md:545`: "The first 200 lines, or 25KB, whichever comes first, are read"), and the same one this repo's `MEMORY.md` curation work (`project_memory_index_curation`, #476) already operates under. A subagent's `MEMORY.md` inherits that constraint independently, per agent.

⚠️ For main-session auto memory, `claude-directory.md:545` adds that "**Topic files like debugging.md are read on demand, not at startup**". The corpus does **not** state whether a subagent's non-`MEMORY.md` files get the same on-demand treatment or are simply inert until the agent reads them itself. Marked UNVERIFIED.

### Interaction with `CLAUDE_CODE_DISABLE_AUTO_MEMORY` — the field is gated, and the gate is tri-state

`sub-agents.md:516` is unambiguous:

> "Subagent memory is **part of auto memory**: if you turn auto memory off, with the `autoMemoryEnabled` setting or `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, **the `memory` field has no effect** and the subagent launches **without the memory instructions or the memory tool access** described below."

So disabling auto memory silently makes every `memory:` declaration inert — *and* revokes the `Write`/`Edit` grant from `:522`. An agent whose definition assumes it can write its memory will find those tools missing, with no error naming the cause.

The gate has **three** states, not two (`env-vars.md:220`):

| Value | Effect |
|---|---|
| `1` | Disable auto memory. "Claude does not create or load auto memory files." |
| `0` | ⚠️ **Force auto memory ON** "even when `--bare` mode or `autoMemoryEnabled: false` would otherwise disable it" |
| unset | `autoMemoryEnabled` decides (default `true`, `settings.md:236`) |

`=0` is an **override, not a no-op**. A settings-level `autoMemoryEnabled: false` can be defeated by an env var — relevant to this repo, where `env` blocks in `settings.json` and mise-injected environment both reach the harness.

`autoMemoryEnabled` defaults `true` and is togglable mid-session via `/memory` (`settings.md:236`, `memory.md:344`). Per-project disable is `autoMemoryEnabled: false` in that project's settings (`memory.md:344–348`).

### Can an agent read another agent's memory?

**Not documented either way — and the filesystem layout says yes by default.**

Control-armed search across `sub-agents.md` and `memory.md`, same command shape:

```
"another agent's memory"  → 0, 0    ← the question
"other agents"            → 0, 0    ← the question
"isolat"                  → 11, 1   ← control, present
"sandbox"                 → 1, 2    ← control, present
"agent-memory"            → 3, 0    ← control, present in sub-agents.md
```

The controls fire; the probe can see these files. There is genuinely **no isolation statement**.

What the docs *do* establish, which settles it in practice:

1. The scopes are **sibling subdirectories under one shared parent** (`:512–514`, `claude-directory.md:389` shows `agent-memory/` → `<agent-name>/` → `MEMORY.md`). Nothing partitions them.
2. Access is via the **ordinary `Read`/`Write`/`Edit` tools** (`:522`), which are governed by the normal permission system and reach any path the agent is allowed to touch.
3. `.claude/agent-memory/` is inside the project tree and `committed` (`claude-directory.md:381`), so a `project`-scoped memory is an ordinary tracked repo file.

**Conclusion:** an agent with `Read` and a path can read another agent's `MEMORY.md`; nothing in the documented design prevents it. What the docs guarantee is only *automatic* separation — "**each subagent reads and writes its own MEMORY.md, not yours**" (`claude-directory.md:384`), i.e. only its own is auto-loaded into its system prompt.

Design consequence: **treat subagent memory as a shared, readable channel, not as private state.** If cross-agent knowledge sharing is wanted, a `project`-scoped memory is a legitimate mechanism for it (and, being committed, is reviewable in a diff). If privacy is wanted, `memory:` does not provide it. ⚠️ Note also that a `project` memory is auto-generated *and* committed — an agent writing to it produces uncommitted repo changes, which interacts with this repo's `branch_guard` (writes to repo files while on the default branch are denied).

## 6. Per-subagent `hooks`

### Which events are available: ALL 30

`sub-agents.md:627` — "**All hook events are supported.**" Independently at `hooks.md:570` — "All hook events are supported. For subagents, `Stop` hooks are automatically converted to `SubagentStop`."

Enumerated **by shape**, not by expectation (this is the exact trap the brief warns about — a prior session missed 18 of 29 by grepping for the events it expected):

```
awk 'NR>935 && /^### /' hooks.md    → 42 headings, of which the first 30 are events
```

Cross-checked against a **second independent shape**: the `#### Exit code 2 behavior per event` table (`hooks.md:706–737`) has exactly **30 rows**, and the two sets are identical. Two routes, same 30 — the enumeration is closed.

| # | Event | # | Event | # | Event |
|---|---|---|---|---|---|
| 1 | `SessionStart` | 11 | `PostToolBatch` | 21 | `ConfigChange` |
| 2 | `Setup` | 12 | `PermissionDenied` | 22 | `CwdChanged` |
| 3 | `InstructionsLoaded` | 13 | `Notification` | 23 | `FileChanged` |
| 4 | `UserPromptSubmit` | 14 | **`SubagentStart`** | 24 | `WorktreeCreate` |
| 5 | `UserPromptExpansion` | 15 | **`SubagentStop`** | 25 | `WorktreeRemove` |
| 6 | `MessageDisplay` | 16 | `TaskCreated` | 26 | `PreCompact` |
| 7 | `PreToolUse` | 17 | `TaskCompleted` | 27 | `PostCompact` |
| 8 | `PermissionRequest` | 18 | `Stop` | 28 | `SessionEnd` |
| 9 | `PostToolUse` | 19 | `StopFailure` | 29 | `Elicitation` |
| 10 | `PostToolUseFailure` | 20 | `TeammateIdle` | 30 | `ElicitationResult` |

`sub-agents.md:629–633` names only the three "most common for subagents" — `PreToolUse`, `PostToolUse`, `Stop`. **That is a convenience list, not the available set.** Reading it as the set is precisely the 18-of-29 failure mode.

### How frontmatter hooks differ from project hooks

| | Frontmatter `hooks:` | `settings.json` hooks |
|---|---|---|
| Lifetime | "only run while that specific subagent is active and are **cleaned up when it finishes**" (`sub-agents.md:617`) | Session-wide |
| Also fires inside subagents? | n/a | **Yes** — "a `PreToolUse` hook in `settings.json` also runs before every tool a subagent uses" (`:613`) |
| Sources | the agent file | settings files, **managed policy settings, and plugins** all apply inside subagents (`:613`) |
| `Stop` semantics | **auto-converted to `SubagentStop`** at runtime (`:633`, `:655`, `hooks.md:570`) | `Stop` stays `Stop` |
| Trust required | **yes for project-level** (below) | workspace trust as usual |
| Plugin subagents | **ignored entirely** (`:229`) | unaffected |

They **compose** rather than replace: when an agent runs as the main session via `--agent`, "they run alongside any hooks defined in `settings.json`" (`:620`). Frontmatter hooks fire both when the agent is a subagent (Agent tool or @-mention) and when it is the main session (`:620`).

⚠️ **Workspace-trust gate, new in v2.1.218** (`:623–625`): a **project-level** subagent's frontmatter hooks run only after you accept the workspace trust dialog for the folder containing the agent file. `~/.claude/agents/` and `--agents` definitions are **exempt**. A `--add-dir` folder outside the trusted repo needs **separate** trust — "its `.claude/agents/` hooks don't inherit the workspace's grant."

**Until trusted, the subagent still runs and its hooks are silently skipped**, with only a debug-log error. That is a fail-open: a frontmatter hook used as a guard is not a guard until the folder is trusted, and nothing in the transcript says so. Before v2.1.218 they ran untrusted, including non-interactively.

### `SubagentStart` / `SubagentStop` matchers

Both match on **agent type** (`sub-agents.md:661–664`, `hooks.md:233–235`). Accepted values: `general-purpose`, `Explore`, `Plan`, custom agent names, or plugin-scoped names (`hooks.md:233`).

The matcher value is the frontmatter **`name`**, not the filename, for project/user agents; for plugin agents it is the **plugin-scoped identifier** such as `my-plugin:db-agent` (`sub-agents.md:666`, `hooks.md:643`).

⚠️ **Two anchoring traps, both of which produce over-firing:**

1. "A scoped name contains a colon, so it is evaluated as an **unanchored regular expression**; anchor it with `^` and `$`, as in `^my-plugin:db-agent$`" (`sub-agents.md:666`).
2. "A hyphenated matcher like `db-agent` matches exactly on v2.1.195 or later. On earlier versions it is evaluated as an unanchored regular expression and **also fires for any agent type that contains it, such as `prod-db-agent`**" (`sub-agents.md:692`).

Input payloads (`hooks.md:2014`, `:2048`):

- `SubagentStart` receives `agent_id` + `agent_type` on top of the common fields.
- `SubagentStop` receives `stop_hook_active`, `agent_id`, `agent_type`, **`agent_transcript_path`**, and **`last_assistant_message`**. `transcript_path` is the *main session's*; `agent_transcript_path` is the subagent's own, in a nested `subagents/` folder. `last_assistant_message` "contains the text content of the subagent's final response, **so hooks can access it without parsing the transcript file**".
- `SubagentStop` also gets `background_tasks` and `session_crons` (v2.1.145+), both **scoped to the parent session, not the subagent** (`:2050`).

`hooks.md:632` adds a durable caveat: the transcript file "is written **asynchronously and may lag** the in-memory conversation", so a hook needing the final assistant text must use `last_assistant_message`, **not** read the transcript. That is a ready-made false-negative generator for any hook that greps the transcript file.

### Can a hook refuse to START an agent? NO.

Unambiguous, from two places:

- `hooks.md:2027` — "**SubagentStart hooks can't block subagent creation**, but they can inject context into the subagent."
- `hooks.md:724`, the exit-code-2 table — `SubagentStart` | **Can block? No** | "Shows stderr to user only".

And the failure is quiet in a specific way (`hooks.md:739`): on exit 2, "the stderr renders in the transcript as a `<hook name> hook error` notice… **Claude doesn't see it**, and the session or subagent proceeds. For `SubagentStart`, the notice appears in **the subagent's own transcript, not in the parent conversation**." So a lead spawning a misbehaving agent gets no signal at all. (Before v2.1.199 it went to the debug log only.)

What `SubagentStart` **can** do: inject context, via `hookSpecificOutput.additionalContext` (`hooks.md:2027`, `:874`). `:874` confirms `SessionStart`/`Setup`/`SubagentStart` are the "Context only" class — "**No blocking or decision control**".

**The nearest thing to refusing an agent is a `PreToolUse` hook on the `Agent` tool**, which *can* block (`hooks.md:709`) — that fires in the parent before the spawn, not in the agent. This is exactly the shape this repo already uses (`hook_guard.py` on `Bash|AskUserQuestion`); extending its matcher to `Agent` is the supported way to gate which agents may be spawned. The declarative alternative is `permissions.deny: ["Agent(name)"]` (`sub-agents.md:588–602`) or `--disallowedTools "Agent(Explore)"`.

### `SubagentStop` CAN block — and blocking means "keep working"

`hooks.md:713` — `SubagentStop` | **Can block? Yes** | "Prevents the subagent from stopping."

`hooks.md:2069` gives the semantics, which are not "abort": "Returning `decision: "block"` with a `reason` **keeps the subagent running and delivers `reason` to the subagent as its next instruction**." Non-error feedback that also continues it uses `hookSpecificOutput.additionalContext` with `hookEventName: "SubagentStop"`.

⚠️ **To inject context into the PARENT after a subagent returns, `SubagentStop` is the wrong hook** — it runs inside the subagent. `hooks.md:2069`: "use a **`PostToolUse` hook on the `Agent` tool** instead."

This is the mechanism that could enforce a delivery contract on delegated work — e.g. a `SubagentStop` hook that checks the report file exists and returns `decision: "block"` with "write your report to <path> before stopping" otherwise. Directly relevant to `feedback_agent_team_delivery_discipline` (agents dying or idling without reporting): that failure is *machine-preventable* at `SubagentStop`, where today it is carried by prose in the agent definition alone.

⚠️ Scope limit: `SubagentStop` does **not** fire for agent-team **teammates** — the teammate-idle event is a separate one, `TeammateIdle` (`hooks.md` event 20), which is also blockable ("Prevents the teammate from going idle, so it continues working", `hooks.md:713` region). A delivery gate must be wired at **both** events to cover both delegation shapes.

## 7. Scope and precedence

### There are FIVE scopes, not four

The brief says "the four subagent scopes". Enumerated by shape from the table at `sub-agents.md:160–166`, there are **five**, and the fifth (plugins) is the one that carries the restrictions in §7.4:

| Priority | Location | Scope | How created |
|---|---|---|---|
| 1 (highest) | Managed settings (`.claude/agents/` inside the managed settings dir, `:224`) | Organization-wide | Deployed via managed settings |
| 2 | `--agents` CLI flag | Current session only, **not saved to disk** (`:182`) | JSON at launch |
| 3 | `.claude/agents/` | Current project | File |
| 4 | `~/.claude/agents/` | All your projects | File |
| 5 (lowest) | Plugin's `agents/` directory | Where the plugin is enabled | Installed with the plugin |

"When multiple subagents share the same name, Claude Code uses the one from the **higher-priority** location" (`:158`). Managed definitions "take precedence over project and user subagents with the same name" (`:224`).

### Discovery, and the walk-up

- **Project agents are discovered by walking UP from the cwd** — "every `.claude/agents/` between there and the repository root is scanned" (`:170`). As of v2.1.178, when nested dirs define the same `name`, **the definition closest to the working directory wins**.
- **`--add-dir` directories are also scanned**: a `.claude/agents/` inside an added dir loads alongside project subagents (`:172`).
- **Both project and user dirs are scanned recursively** (`:176`). Subfolders are organisational only — "identity comes **only** from the `name` frontmatter field", so `agents/review/x.md` and `agents/x.md` are the same agent if `name` matches.
- **Plugin dirs are recursive too, but the subfolder IS part of the identity** (`:180`): `agents/review/security.md` in `my-plugin` registers as `my-plugin:review:security`. This is the one place the path affects the name — an asymmetry easy to get wrong.

### Name collisions — the undefined case

`:178` is the important one:

> "Keep `name` values unique across the whole tree: if two files under the **same** `.claude/agents/` directory, including its subfolders, declare the same name, Claude Code loads **only one of them, chosen by filesystem read order rather than a documented precedence**."

So there are two distinct collision regimes:

| Collision | Resolution |
|---|---|
| Across **scopes** | Documented — priority table above |
| Across **nested project dirs** | Documented — closest to cwd wins (v2.1.178+) |
| Within the **same** directory tree | ⚠️ **Undefined — filesystem read order.** Non-deterministic in principle |

Detection: `/doctor` "reports files in the same directory that share a name and proposes renaming or removing all but one" as of v2.1.205 (`:178`). Before that, `/doctor` showed which definition was active.

Related hard constraint (v2.1.218+, `:277`): **`name` can't contain `:`** — reserved for plugin scoping. "Claude Code doesn't load a file whose name contains one and **logs an error to the debug log**." A silent non-load whose only signal is the debug log; before v2.1.218 such names were accepted.

### The directory watcher's start-time limitation

`:239–245` — Claude Code watches `~/.claude/agents/` and `.claude/agents/`; edits are picked up "within a few seconds… **with no restart needed**".

**Two cases still need a restart:**

1. ⚠️ "The watcher covers **only directories that existed when the session started**, so after creating a scope's **first** agent file in a **new** `agents` directory, restart to load it." Restated at `:140`: "This happens only when `~/.claude/agents/` didn't exist before the session started, because a running session doesn't detect a newly created `agents` directory."
2. Sessions started with `--disable-slash-commands` **don't watch these directories at all**.

The practical shape: *editing* an agent is live; *creating the very first agent in a scope* is not. That is exactly the moment a user is most likely to be iterating, and the failure mode is "Claude can't find the new subagent" with no error.

### Plugin subagent restrictions — three fields silently ignored

`:229`, verbatim:

> "For security reasons, plugin subagents **don't support the `hooks`, `mcpServers`, or `permissionMode` frontmatter fields. These fields are ignored when loading agents from a plugin.**"

Confirmed independently in the frontmatter table itself, which marks each one "Ignored for plugin subagents": `permissionMode` (`:282`), `mcpServers` (`:285`), `hooks` (`:286`).

**Ignored, not rejected** — no error, no warning documented. A plugin agent carrying a `PreToolUse` guard in its frontmatter runs **with that guard silently absent**. For a team design that vendors agents through plugins, this means a plugin-shipped agent cannot carry its own enforcement; the guard must live in `settings.json` (which does fire inside subagents, `:613`).

Documented workarounds (`:229`): copy the agent file into `.claude/agents/` or `~/.claude/agents/`, or add rules to `permissions.allow` — with the caveat that "these rules apply to **the entire session**, not only the plugin subagent."

### Agent-team teammates: a sixth, different applicability set

`:232` — subagent definitions from **any** scope can be referenced when spawning a teammate; the teammate "uses its `tools` and `model`, with the definition's body **appended** to the teammate's system prompt as additional instructions."

But the applicable field set differs again (`agent-teams.md:255`, `:258`):

- **Applied**: `tools` allowlist, `model`, body (appended, not replacing).
- **Always available regardless of `tools`**: "Team coordination tools such as `SendMessage` and the task management tools" (`agent-teams.md:255`).
- ⚠️ **NOT applied**: "The **`skills` and `mcpServers`** frontmatter fields in a subagent definition are **not applied** when that definition runs as a teammate. Teammates load skills and MCP servers from your project and user settings, the same as a regular session" (`agent-teams.md:258`).

So one definition file has **at least four** distinct behaviours depending on execution path: foreground subagent, background subagent, main session (`--agent`), and teammate. `skills:` works in three of them and not the fourth; `hooks:` works in three and not for plugins; `background: true` errors outright on the teammate path (§4).

## 8. Every limit and its failure message

Enumerated by shape (`grep -rn 'CLAUDE_CODE_MAX[A-Z_]*'` over `env-vars.md` + `settings.md`), then filtered to the agent-relevant ones. The sweep also returned `MAX_CONTEXT_TOKENS`, `MAX_OUTPUT_TOKENS`, `MAX_RETRIES`, `MAX_WEB_SEARCHES_PER_SESSION`, `MAX_THINKING_TOKENS` — real limits, out of scope here, listed so the enumeration is visibly complete rather than curated.

### Master table

| Limit | Default | Variable | Failure | Cite |
|---|---|---|---|---|
| **Spawn depth** | **3** layers below main (v2.1.219+) | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | ⚠️ **No message.** The `Agent` tool is *withheld*. A fork keeps it and gets an **error** on call | `sub-agents.md:862`, `:866`, `env-vars.md:280` |
| **Per-session count** | **200** | `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | `Subagent spawn limit reached` — "the error tells Claude to complete the remaining work directly with its own tools" | `sub-agents.md:893`, `:897` |
| **Concurrency** | **20** running | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | `Concurrent subagent limit reached` — "the error tells Claude **not to retry**" | `sub-agents.md:903` |
| **Tool-use concurrency** | **10** | `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | Not documented | `env-vars.md:281` |
| **`maxTurns`** | none | frontmatter `maxTurns`; session-wide `CLAUDE_CODE_MAX_TURNS` / `--max-turns` | Not documented for the frontmatter field | `sub-agents.md:283`, `env-vars.md:282` |

### ⚠️ The real parallelism cap is 10, not 20

`env-vars.md:281`: `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` — "Maximum number of read-only tools **and subagents** that can execute in parallel (**default: 10**)."

This sits **below** the 20-agent concurrency limit and is never mentioned on `sub-agents.md`, which presents 20 as *the* concurrency limit and enumerates "three separate limits" (`:891`) without it. Two pages, two different numbers, and the smaller one binds.

The practical read: **a team fanning out more than ~10 agents will serialise at 10** long before the documented 20-agent ceiling refuses a spawn — and it will do so *silently*, since no failure message is documented for this limit. A "why is my 16-agent fan-out not actually parallel" investigation would find nothing on `sub-agents.md`.

I have **not** measured this and the interaction with the 20-cap is not stated (does a queued agent occupy a concurrency slot?). Recorded as an open item; do not present the 10 as a measured throughput number.

### Depth limit — details

- Default **3** since v2.1.219. History (`:885–886`, `env-vars.md:280`): v2.1.172–216 nested up to **5** layers and **could not be changed**; v2.1.217–218 defaulted to **1** (nesting effectively off). Three different defaults in three version bands — any inherited claim about nesting depth needs its version.
- `1` turns nesting off (`:876`).
- At the limit, "Claude Code **withholds the `Agent` tool** from every subagent except a fork, so a subagent at the limit does its delegated work itself and returns one summary" (`:862`). **There is no error** — the capability is simply absent, which is why an agent at depth cannot report being blocked.
- A fork at the limit "keeps `Agent` in its inherited tool list, but the tool **returns an error** instead of spawning" (`:862`).
- Per-agent opt-out without touching the limit: omit `Agent` from `tools` or add it to `disallowedTools` (`:878`).
- Only the **top-level** subagent's summary returns to the main conversation (`:864`).
- ⚠️ **Agent teams do not nest at all**: "**No nested teams**: teammates cannot spawn their own teammates. Only the lead can manage the team" (`agent-teams.md:425`). A teammate can still spawn *subagents* (foreground only, §4).

### Session count — what does and does not count

From `:895`, which is unusually precise:

**Counts:** nested subagents, forks, background subagents, subagents that a *workflow's agents* spawn with the Agent tool, an in-session `/subtask` fork, **and finished subagents** ("A finished subagent still counts" — the budget is cumulative, not concurrent).

**Doesn't count:** a session created with `/fork` (separate background session, own budget); agents a **workflow script** spawns with `agent()` ("workflows have their own per-run limit").

**Asymmetry:** the limit "blocks only subagents Claude spawns with the Agent tool, so your own `/subtask` **still starts** after Claude reaches the limit."

Reset: `/clear` resets the count — "If work that can still spawn subagents survives the clear, such as a running workflow, **the count carries over** instead" (`:899`).

`env-vars.md:279` adds parsing detail that matters for a `settings.json` `env` block: the variable "**doesn't take the scientific notation or digit-separator spellings**. Anything else is ignored and the default applies, so the cap can be **raised but not turned off**." A typo silently reverts to 200.

### Concurrency limit — the two things that bypass it

`:905–908`: the limit blocks only Claude's `Agent` spawns, but other runs **occupy the same slots**:

- An in-session `/subtask` fork "takes a slot while it runs and is **never blocked** by the limit."
- ⚠️ "**Resuming a subagent** that already finished **takes a fresh slot without checking the limit, so resumes can push the running count past it.**"

So the running count can legitimately exceed 20. Any monitor asserting `running <= 20` would be a probe that can fire falsely.

Also exempt: "Sessions with **ultracode** active are exempt: the limit isn't enforced there" (`:903`). Workflow agents and agent-team teammates "follow their own limits instead" (`:910`) — those limits are not stated on this page.

`env-vars.md:275`: same parsing note — positive whole number in plain digits, "the variable can adjust the cap but **can't disable it**."

### `maxTurns`

Frontmatter: "Maximum number of agentic turns before the subagent stops" (`sub-agents.md:283`); identical wording in the SDK at `agent-sdk__subagents.md:177`. Passable via `--agents` JSON (`:222`).

⚠️ **No failure message is documented, and `errors.md` has no entry for it** (shape-based sweep of `^### ` headings in `errors.md` matching agent/limit/turn terms returned `Agent terminated early due to an API error`, `Agent would be spawned with zero tools`, `Context exceeds the token limit`, `Memory index is over its read limit` — **no turn-limit entry**). So a `maxTurns` stop is documented only as "the subagent stops", with no stated signal distinguishing it from normal completion. **A `maxTurns`-truncated agent may be indistinguishable from a finished one**, which is a live hazard for any design that treats a returned report as complete. UNVERIFIED whether a marker exists.

The session-wide sibling `CLAUDE_CODE_MAX_TURNS` behaves differently and *is* validated: "A value that is not a positive integer is **rejected at startup with an error** rather than treated as no cap" (`env-vars.md:282`). `--max-turns` takes precedence when both are set.

### The zero-tools refusal — and its fail-open

Not a "limit" in the counting sense, but it is the documented failure for a mis-specified agent, and it has a gap.

`errors.md:1398` — "Every entry in the subagent's `tools` list failed to match a usable tool, so Claude Code refused to launch the subagent." The message **groups entries by cause**:

- **Unrecognized** — matches no tool name (typo: `Grpe` for `Grep`).
- **Not available to subagents** — a real tool subagents can't use. ⚠️ "**Background subagents keep a smaller built-in tool set, so an entry that only a foreground subagent can use lands here when the subagent would run in the background, which is the default.**" This is §1's filter 2 surfacing as a user-visible error.
- **Matched no tools in this session** — valid but nothing matches now: `mcp__github__*` with no server connected, or `Agent` at the depth limit.

Verbatim message (`errors.md:1418`):

```
Agent 'code-reviewer' would be spawned with zero tools — refusing. Its tools list
resolved to nothing: unrecognized [Grpe]. Fix the agent's tools frontmatter or
pass a different subagent_type.
```

⚠️ **The refusal has two documented holes** (`errors.md:1408`): "Omitting the `tools` field never triggers this refusal. If you leave the `tools` list **empty**, or **`disallowedTools` removes every entry in it**, Claude Code **skips the refusal and launches the subagent without tools**."

Omitting is correct (it means "inherit everything"). But an **empty list**, and a `disallowedTools` that eats the whole `tools` list, both produce a **toolless agent with no error** — the exact silent failure the v2.1.208 refusal was added to prevent. `errors.md:1416` confirms the pre-2.1.208 behaviour was "the subagent launched with no tools and could return an empty or confusing result"; for these two shapes that behaviour is still current.

`errors.md:1406` also names concrete tools background subagents drop — "such as **`LSP` or `TaskCreate`**" — an independent confirmation of §1's filter 2 from a different page, and a reminder that `LSP` exists and is foreground-only. (`TaskCreate` is dropped for a plain background subagent but restored for a **teammate**, per `sub-agents.md:338` — so the same entry is an error in one context and fine in another.)

## 9. Observability — `agent-view.md` in full, and `errors.md`

### ⚠️ First, a scope correction: `agent-view.md` is NOT about subagents

The brief asks for `agent-view.md` "in full" as the answer to subagent observability. Read in full, **it documents a different feature.** `agent-view.md:9`:

> "Agent view, opened with `claude agents`, is one screen for **all your background sessions**… **Each background session is a full Claude Code conversation** that keeps running without a terminal attached."

The disambiguation is explicit — the page has a troubleshooting entry titled "**`claude agents` lists subagents instead of opening agent view**" (`:682`), i.e. printing your subagents is the *failure* mode of that command. And `:21` sends you elsewhere "to compare agent view with subagents, agent teams, and worktrees".

**So there are three separate observability surfaces, and they do not overlap:**

| Surface | Watches | Documented in |
|---|---|---|
| **Agent view** (`claude agents`) | background **sessions** (full conversations, own supervisor process) | `agent-view.md` |
| **Subagent panel** + `/tasks` | subagents and forks **inside one session** | `sub-agents.md:779`, `:880`, `:1021–1032` |
| **Agent panel** below the prompt | agent-team **teammates** | `agent-teams.md:80`, `:163` |

Answering "what can I see of my subagents?" from `agent-view.md` would be answering from the wrong page. Both are reported below.

### What the SUBAGENT surface actually shows

This is the honest answer to "an agent you can't SEE is an agent you can't improve."

**The subagent panel** (`sub-agents.md:880`): "shows the full tree: each row displays a `(+N)` count of descendants, and as of v2.1.193, opening a row shows that subagent's **siblings and direct children with a path back to `main`**."

**`/tasks`** (`:779`, v2.1.208+): completed background subagents stay listed, marked done, sorted below running work; the detail view stays open on completion.

**Transcripts** (`:967`, `:969–973`) — the highest-fidelity surface, and the only one that is durable:

- Path: **`~/.claude/projects/{project}/{sessionId}/subagents/`**, each file **`agent-{agentId}.jsonl`**.
- Unaffected by main-conversation compaction — "They're stored in separate files."
- Persist within their session; a subagent can be resumed after restarting Claude Code by resuming the session.
- Deleted after `cleanupPeriodDays`, **default 30 days**.
- Compaction events appear inline as `{"type":"system","subtype":"compact_boundary","compactMetadata":{"trigger":"auto","preTokens":167189}}` (`:981–992`) — so context pressure per subagent is measurable from the transcript.

**Steering** (`:1032`): open a subagent's or fork's transcript and type; follow-ups and **skills** go to that agent, but built-in commands still run in the main conversation.

**Cosmetic**: `color` sets the subagent's colour in the task list and transcript (`:291`) — 8 values. Trivial, but it is the only per-agent affordance the panel offers.

### ⚠️ What the subagent surface does NOT show — the real gaps

1. **Failed subagents leave the `/tasks` list** (`:779`). Completed ones persist; failures vanish. The list is **success-biased** and cannot be used to audit failures.
2. ~~**No live token/cost figure per subagent.**~~ ⚠️ **CORRECTED — this was wrong, see §9A.** Per-subagent `tokenCount`, `model`, `contextWindowSize` and `effort` are exposed live via `subagentStatusLine` (`statusline.md:1028–1032`), and per-agent cost attribution exists via OTEL `agent_id` / `parent_agent_id` and the gateway headers. What is true is narrower: **none of it is on by default** — every one of those surfaces requires configuration.
3. **No aggregate view across subagents in the default UI.** Agent view's row summaries, state icons, PR linkage and notifications are **session-level features that do not apply to subagents**. The subagent panel's default row is only `name · description · token count` (`statusline.md:1017`) — replaceable, but only by writing a `subagentStatusLine` command.
4. **A `SubagentStart` hook's exit-2 stderr goes to the subagent's own transcript, not the parent** (`hooks.md:739`) — a spawn-time complaint is invisible where you are looking.
5. **A `maxTurns` truncation has no documented signal** (§8).
6. **Nothing shows a subagent's tool set.** Given §1 — filter 2 removes tools **with no error** and the same definition resolves differently in foreground vs background — there is no surface that answers "what tools does this running agent actually have?"

Gap 6 is the one I would flag hardest for a team design: the harness silently varies the single most important property of a delegated agent and exposes no way to observe it.

### 🔎 Reconciling this repo's canonical control-arm example

`.claude/rules/probes-need-a-control-arm.md` opens with: *"`find … -name 'agent-*.jsonl'` reported 'AGENT DEAD, no transcript' — teammate transcripts are `<uuid>.jsonl`, so the glob can never match."*

`sub-agents.md:967` documents subagent transcripts as **exactly `agent-{agentId}.jsonl`**. Both are correct, and together they sharpen the lesson rather than undermining it:

> **`agent-*.jsonl` is the right glob for a SUBAGENT and the wrong glob for a TEAMMATE.** The probe wasn't using a name that never exists — it was using the *other feature's* naming convention. That is a subtler failure than a typo and a better example: the probe was well-formed, just aimed at the wrong surface.

The durable rule for this repo: **when probing for an agent's transcript, first establish which surface it is on** (subagent → `{sessionId}/subagents/agent-{id}.jsonl`; teammate → `<uuid>.jsonl`), then arm the probe against a known-live agent of *that same kind*. I have not re-verified the teammate path from the docs — the corpus does not state it — so the `<uuid>.jsonl` half remains an inherited, unre-derived claim from the rule file and is labelled as such.

### `agent-view.md` in full — what the session-level view has that subagents don't

Reported because it is the design target: this is what mature agent observability looks like in this harness, and none of it reaches subagents.

**Session state** (`:105–130`), a two-axis icon:

| State | Icon | Meaning |
|---|---|---|
| Working | Animated | actively running tools or generating |
| Needs input | Yellow | waiting on something only you can provide — a question, a permission decision, a sandbox network prompt (v2.1.212+), an MCP elicitation, a managed-settings prompt, or an MCP auth prompt (v2.1.216+) |
| Idle | Dimmed | nothing to do, ready for a prompt |
| Completed | Green | finished successfully |
| Failed | Red | ended with an error |
| Stopped | Grey | stopped with `Ctrl+X` / `claude stop`, or its process ended externally |

Separately the icon **shape** reports process liveness: `✻`/`✽` alive; `∙` process exited (you can still peek/reply/attach, "Claude restarts from where it left off"); `✢` a `/loop` session sleeping, showing run count and countdown.

⚠️ **That second axis is precisely the "is it alive" question this repo's `feedback_agent_spawn_liveness` memory exists for — and it is a first-class, documented UI signal at the session level with no subagent equivalent.**

**Row summaries** (`:138–147`): generated by a **Haiku-class model**. Updates at most once per 15s from the session's own output *without* a model request; the model rewrites a fresh summary at end-of-turn and every few minutes during a long turn. A working row shows what it says it's doing; a blocked row shows the question. ⚠️ **Cost note**: "The end-of-turn summary and each mid-turn rewrite are one short Haiku-class request through your normal provider, **billed** … under the same data usage terms as the session itself."

**Pull-request linkage** (`:148–166`): a `#1234` label at the row edge, hyperlinked, colour-coded — yellow (waiting on checks/review, or checks failed), green (checks passed, no blocking review), purple (merged), grey (draft/closed). Multiple PRs collapse to `3 PRs`. ⚠️ Directly relevant to this repo's `ship`/`land` flow: linkage comes from **`gh` command output**, so "a `gh` command whose captured output names no pull request doesn't create a link; **`gh pr merge` is the common case, because it prints its result only to an interactive terminal**."

**Peek and reply** (`:167–186`): `Space` opens a panel showing the exact question (waiting), the result (finished), or the full status sentence (working), plus linked PRs and a `waiting 3m` counter. Predefined choices render as a numbered list answerable by keypress; a **permission prompt shows as text with no numbered options**. An undeliverable reply is **saved and sent as the session's next prompt** — except one prefixed `!`, which isn't saved because the saved text would arrive as a plain prompt rather than a Bash command.

**Notifications** (`:130` region): while agent view is open, Claude Code notifies through the configured terminal channel when a local background session **starts needing input, finishes, or fails**. Scheduled/`/loop` sessions notify only when they need input. The terminal tab title carries the awaiting-input count.

**Durability** (`:105` region, `:590–675`): a supervisor process runs sessions with no terminal attached; state persists on disk across auto-updates, supervisor restarts and machine **sleep** (processes resume on wake). A session that slept mid-response can come back unresponsive; opening it restarts the process and continues the interrupted response.

**Turn it off** (`:676`): `disableAgentView: true` or `CLAUDE_CODE_DISABLE_AGENT_VIEW`; enforceable via managed settings. ⚠️ Cross-effect from §3: with agent view off, **`/subtask` is unavailable and `/fork` starts the forked subagent instead** (`sub-agents.md:997`).

**Limitations** (`:776–782`), verbatim-sourced:

- "**Rate limits apply**: background sessions consume your subscription usage the same as interactive sessions, so running ten agents in parallel uses quota **roughly ten times as fast** as running one."
- "**Sessions are local**: they run on your machine. Preserved across sleep but **stop if the machine shuts down**."
- "**Claude-created worktrees are deleted with the session**: commit changes before deleting a session that edited files in its own worktree." A worktree with unpushed commits, or uncommitted changes under `claude rm`, is kept with the session.
- Research preview since v2.1.139; "interface and keyboard shortcuts may change."

Recovery note (`:700`): shutdown makes running sessions **show as failed**; attach/peek/reply restarts them from where they left off. So "Failed" at the session level is not always terminal — a monitor treating red as fatal would be wrong.

### What `errors.md` says about agent failures

Shape-based sweep of `^### ` headings in `errors.md` matching agent/task/tool/spawn/limit returned **two** agent-specific entries (plus adjacent generic ones). Both are covered above with full text: **`Agent terminated early due to an API error`** (`errors.md:290`, §4) and **`Agent would be spawned with zero tools`** (`errors.md:1398`, §8).

⚠️ **The notable result is what is NOT there.** No entry for: the depth limit (capability silently withheld), `maxTurns` exhaustion, `Subagent spawn limit reached`, or `Concurrent subagent limit reached` — the last two exist as message strings in `sub-agents.md:897`/`:903` but have **no `errors.md` section explaining what to do**. A user hitting a concurrency ceiling has no troubleshooting entry to find.

One adjacent entry worth carrying: **`Session agent no longer available`** (`sub-agents.md:737`) — resuming a session whose `--agent` definition has been deleted "continues with the default tools and system prompt and shows a warning naming the agent." ⚠️ **Fail-open**: a session pinned to a restrictive agent silently reverts to **full default tools** if the definition disappears. For a read-only auditor agent, deleting the file *widens* its capability rather than blocking it.

## 9A. The observability surfaces that are OFF BY DEFAULT

Added on a second pass after the lead named six candidate surfaces. **Seven of eight are real; one is not.** Existence sweep, corpus-wide file counts, controls invented fresh this run:

| Token | Files | Verdict |
|---|---|---|
| `forward-subagent-text` | 5 | ✅ real |
| `FORWARD_SUBAGENT_TEXT` | 4 | ✅ real |
| `x-claude-code-agent-id` | 2 | ✅ real |
| `x-claude-code-parent-agent-id` | 2 | ✅ real |
| `agent_path_count` | 1 | ✅ real — **but not agent observability**, see below |
| `read-agent-traces` | 1 | ✅ real — a doc anchor, not a knob |
| `subagent-statusline` | 1 | ✅ real — an example script path; the **setting** is `subagentStatusLine` |
| `blue_for_subagents_only` | **0** | ❌ **REFUTED — does not exist in the corpus** |
| — controls — | | |
| `zblarnthok` (invented) | 0 | absent, as expected |
| `x-claude-code-frobnicator` (invented) | 0 | absent, as expected |
| `agent_wibble_count` (invented) | 0 | absent, as expected |
| `SubagentStop` (known-present) | 11 | present |
| `CLAUDE_CODE_FORK_SUBAGENT` (known-present) | 4 | present |

Both arms fire, so the `blue_for_subagents_only` zero is a real negative rather than a blind probe. Do not build on that token.

**This section is the answer to "an agent you can't SEE is an agent you can't improve."** The visibility exists — it is just not wired up by default. The gap is configuration, not capability.

### 9A.1 `subagentStatusLine` — the per-agent telemetry that already exists

`statusline.md:1015–1036`. A `settings.json` setting that "renders a custom row body for **each subagent** shown in the agent panel below the prompt", replacing the default `name · description · token count` row.

```json
{ "subagentStatusLine": { "type": "command", "command": "~/.claude/subagent-statusline.sh" } }
```

The command "runs once per refresh tick and receives **all visible subagent rows** as a single JSON object on stdin", with the base hook fields, a `columns` width, and a `tasks` array. **Each task carries** (`statusline.md:1028`):

`id`, `name`, `type`, `status`, `description`, `label`, `startTime`, `model`, `effort`, `contextWindowSize`, `tokenCount`, `tokenSamples`, `cwd`

That is 13 fields per live subagent, refreshed on a tick. Specifically:

- **`tokenCount` + `contextWindowSize`** — "computed the same way as the main status line's `context_window.context_window_size`, **so you can render a per-row percentage from `tokenCount`**" (`:1030`). Live context pressure per agent. Requires v2.1.205+; **omitted for a task whose model isn't resolved yet**.
- **`model`** — the *resolved* model ID, which settles §1's "what is this agent actually running" question for the model axis.
- **`effort`** — v2.1.214+. ⚠️ "reports the **configured value as written**: if the model doesn't support that level, the effort Claude Code actually applies **may differ**." So it is a declaration, not a measurement. Absent when the subagent inherits the session effort.
- **`startTime`** + **`status`** — the two fields needed to distinguish *stalled* from *working*, which the default row cannot express.
- **`tokenSamples`** — undocumented beyond the name. UNVERIFIED shape.

Output protocol: one JSON line per row, `{"id": "<task id>", "content": "<row body>"}`. `content` renders as-is **including ANSI colors and OSC 8 hyperlinks**. Omit an `id` to keep default rendering; emit empty `content` to **hide** a row.

Gating (`:1036`): "The same trust and **`disableAllHooks`** gates that apply to `statusLine` apply here." Plugins can ship a default `subagentStatusLine`.

⚠️ **Adjacent trap** (`statusline.md:153`): "The event-driven triggers can go quiet when the main session is idle, **for example while a coordinator waits on background subagents**." Set `refreshInterval` (minimum `1`s) or the orchestrator's own status line freezes for exactly the duration of a fan-out — the period you most want to watch.

**Assessment: this is the single highest-value unwired surface for a team design.** A ~30-line script turns the subagent panel into a live dashboard of every agent's model, context %, effort and age. Nothing else in this report gives that much observability for that little work.

### 9A.2 Cost and trace attribution — `agent_id` / `parent_agent_id`

Two independent transports, both real.

**(a) LLM-gateway headers** (`llm-gateway-protocol.md:78–79`):

| Header | Meaning |
|---|---|
| `x-claude-code-agent-id` | "Identifier of the **subagent** that issued the request, present **only on requests from an agent Claude Code spawned inside the session**. Use it with the session ID to **attribute cost to parallel agents**" |
| `x-claude-code-parent-agent-id` | "Identifier of the agent that spawned the requesting agent, **present only for nested agents**" |

The presence rules are the useful part: absent ⇒ main session; `agent-id` without `parent-agent-id` ⇒ depth 1; both ⇒ nested. **The header pair alone reconstructs the spawn tree**, which is what §8's depth limit otherwise makes invisible.

**(b) OTEL spans and metrics** (`monitoring-usage.md:207–208`, `:239–240`, `:248`). The same two attributes ride `claude_code.llm_request` **and** `claude_code.tool` spans:

- `agent_id` — "Identifier of the subagent **or teammate** that issued the request / ran the tool. **Absent on the main session**."
- `parent_agent_id` — "Absent for the main session **and for agents spawned directly from it**."
- `subagent_type` — on Agent/Task tool spans (`:248`).
- `query_source` — `"main"` | `"subagent"` | `"auxiliary"` (`:530`), or a subagent name in the finer-grained events (`:206`, `:636`).
- `agent.name` — ⚠️ **redacted by default for your own agents**: "Built-in agent names and agents from **official-marketplace plugins appear verbatim**. Other **user-defined agent names are rep[laced]**" (`:533`). Same rule for `plugin.name` (`:535`). So a custom role's name does **not** reach your telemetry backend in the clear — you must join on `agent_id` instead. This would silently defeat a dashboard keyed on role name.

Span tree (`monitoring-usage.md:172–181`): each user prompt starts a `claude_code.interaction` root span; the Agent tool's subagent `claude_code.llm_request` / `claude_code.tool` spans hang beneath it. `monitoring-usage.md:1122` names the intended use directly — "Attributing spend to specific skills, plugins, or **subagent types** via the `skill.name`, `plugin.name`, and `agent.name` attributes."

`OTEL_LOG_TOOL_CONTENT=1` adds full tool input/output bodies as span events, truncated at 60 KB (`CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH`, v2.1.214+) (`agent-sdk__observability.md:242`). That is the only documented route to *what a subagent actually did*, tool call by tool call, outside its transcript.

⚠️ **`read-agent-traces` is a doc anchor** (`agent-sdk__observability.md:37`, `:242`), i.e. the "Read agent traces" section — not a flag or setting. Reported so it is not mistaken for a knob.

⚠️ **`agent_path_count` is a red herring for this purpose.** `monitoring-usage.md:928` defines it as "number of **agent directories the plugin declares**" — a *plugin inventory* metric. It counts declarations, not running agents, and tells you nothing about execution.

### 9A.3 `--forward-subagent-text` — live visibility into a deep tree

The closest thing to streaming observability, and it is **headless-only**.

`cli-reference.md:87`: "Emit subagent **text and thinking blocks** in the output stream as `assistant` and `user` messages with **`parent_tool_use_id` set**, so you can reconstruct each subagent's transcript. **Without this flag, Claude Code emits only subagent `tool_use` and `tool_result` blocks.** Requires `--print` and `--output-format stream-json`." v2.1.211+.

`headless.md:171` states the default plainly: "By default, Claude Code emits **only** subagent `tool_use` and `tool_result` blocks."

**Nested depth is covered, and that is the part the lead was right to chase** (`changelog.md:23`): "Added **nested subagent forwarding** in stream-json: subagents spawned at **depth-2+** now appear when `--forward-subagent-text` is set, **keyed by their spawning Agent `tool_use` id`**." So the full depth-3 tree is reconstructible — `parent_tool_use_id` is the join key.

The env var differs from the flag in one operationally important way (`env-vars.md:266`): `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT=1` gives "the same behavior… Use the variable when a harness invokes `claude` and can't pass the flag itself. **Unlike the flag, which exits with an error outside non-interactive mode with stream-json output, the variable is ig[nored]**."

⚠️ **The flag is a hard error in the wrong mode; the variable is silently ignored.** Setting the variable globally is therefore safe but proves nothing — it does nothing in an interactive session, which is where this repo's agent work happens. **This surface does not help an interactive team run at all.** It is for a CI/headless harness that wraps `claude -p`.

### 9A.4 Transcripts — and yes, `agent_transcript_path` is the documented way in

Confirmed from §9: subagent transcripts live at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl` (`sub-agents.md:967`), survive main-conversation compaction, and are deleted after `cleanupPeriodDays` (default 30).

**Can the parent read them?** Yes, and the harness hands over the path rather than making you derive it. `hooks.md:2048`: `SubagentStop` receives **`agent_transcript_path`** — "the `transcript_path` is the **main session's** transcript, while **`agent_transcript_path` is the subagent's own**, stored in a nested `subagents/` folder."

So the documented pattern for parent-side inspection of a finished agent is a `SubagentStop` hook reading `agent_transcript_path`. They are ordinary files, so any agent with `Read` can also open them directly.

⚠️ **Two caveats that would break a naive implementation**, both already cited above and both load-bearing here:

1. `hooks.md:632` — the transcript "is written **asynchronously and may lag** the in-memory conversation", so a `SubagentStop` hook that reads `agent_transcript_path` for the agent's *final text* can race it. Use **`last_assistant_message`**, which the same event provides, for that specific need.
2. `SubagentStop` **does not fire for agent-team teammates** (§6) — `TeammateIdle` is the teammate event.

### 9A.5 `claude agents`, `--bg`, `/background`, and the supervisor

For completeness, since the lead asked and since §9 established these are *session*-level, not subagent-level.

**Entry points:**

| Command | Effect | Cite |
|---|---|---|
| `claude agents` | Open agent view. `--cwd <path>` filters to sessions under that dir; **`--json` prints active sessions as JSON** | `cli-reference.md:28`, `agent-view.md:78` |
| `claude --bg` / `--background` | Start a session straight to the background, return immediately, print the session ID and management commands | `cli-reference.md:70`, `agent-view.md:397` |
| `/background` (alias `/bg`) | Move the **current** conversation to the background, freeing your terminal | `agent-view.md:358`, `:362` |
| `/fork` | Send a **copy** to the background while you keep working where you are | `agent-view.md:358`, `:366` |
| `claude stop <id>` (alias `claude kill`) | Stop a background session | `cli-reference.md:45` |
| `claude rm <id>` | Remove from the list; **the transcript stays** locally, reachable via `claude --resume` | `cli-reference.md:43` |
| `claude daemon status` | Supervisor reachability, PID, version, socket dir, live session count | `agent-view.md:~665` |

Notable combinations: `claude --agent code-reviewer --bg "…"` runs a **defined subagent as a background session's main agent** (`agent-view.md:405–408`) — the one path that gives a role definition full session-level observability. `--name` labels it (`:416`). ⚠️ `--bg` is **rejected before session creation** when combined with `-p`/`--print` (v2.1.198+, `:403`) — the prompt is a positional argument, not a `-p` value. `--exec` runs a shell command as a PTY-backed background job instead of a Claude session (`cli-reference.md:84`).

**The supervisor** (`agent-view.md:594–600`): a **per-user** process, separate from your terminal and from agent view, started automatically the first time you background a session or open agent view; not managed directly. It **keeps one pre-warmed worker ready** so a dispatch starts without a cold launch — on dispatch it assigns that worker, applies the session's directory, settings and credentials, then starts a replacement. If a binary update removed the launching binary, the process starts the supervisor from another installed copy.

**State on disk** (`agent-view.md:655–675`):

| Path | Contents |
|---|---|
| `~/.claude/daemon.log` | Supervisor log |
| `~/.claude/daemon/roster.json` | Running background sessions, used to reconnect after restart |
| `~/.claude/jobs/<id>/state.json` | Per-session state shown in agent view |
| `~/.claude/jobs/<id>/tmp/` | Per-session scratch. **Writes here don't prompt for permission.** Removed with the session |

Each background session gets **`CLAUDE_JOB_DIR`** pointing at `~/.claude/jobs/<id>`, "so shell commands the session runs can write temporary files to `$CLAUDE_JOB_DIR/tmp` without colliding with parallel sessions."

⚠️ **`CLAUDE_CONFIG_DIR` forks the supervisor**: "the supervisor uses that directory instead of `~/.claude` and **runs as a separate instance with its own sessions**" (`:657`). Sessions dispatched under one config dir are invisible from the other — a ready-made "my background session vanished" incident.

Version-skew handling (`:669–673`): `claude daemon status` warns when the running supervisor version differs from the invoked `claude`; fix with `claude daemon stop --any` (or `claude daemon stop` when installed as an OS service). Sessions survive the mismatch — an older version updating `state.json` "preserves fields it doesn't recognize", and `roster.json` follows the same rule since v2.1.200.

**Turning it off** (`agent-view.md:676`): `disableAgentView: true` **or** `CLAUDE_CODE_DISABLE_AGENT_VIEW`; enforceable via managed settings. It disables "background agents **and** agent view **entirely**" — not just the UI. Cross-effect already noted in §3: with agent view off, `/subtask` is unavailable and **`/fork` reverts to starting the forked subagent** (`sub-agents.md:997`).

### 9A.6 Host-specific: fork mode is LIVE here

Verified on this machine, not assumed:

```
CLAUDE_CODE_FORK_SUBAGENT=1              ← set
CLAUDE_CODE_DISABLE_BACKGROUND_TASKS     ← unset
CLAUDE_CODE_DISABLE_AGENT_VIEW           ← unset
declared at: ~/.claude/settings.json:10  "CLAUDE_CODE_FORK_SUBAGENT": "1"
```

Per §3/§4, on this host **today**:

1. **Every subagent runs in the background**, fork or not (`sub-agents.md:1011`).
2. **`background:` frontmatter is inert** — fork mode removes the `run_in_background` parameter from the Agent tool (`:783`).
3. Therefore **filter 2 applies to every subagent this repo spawns** — the reduced 19-tool built-in set is the *only* set in play, and no agent definition can opt out.
4. `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` is unset, so nothing is overriding it.

⚠️ **Consequence for the team design: writing `background: true` (or expecting a foreground subagent) in any role definition is a no-op on this host.** Design against the background tool set as the *only* tool set, and note that a teammate spawning its own subagent is the one path that still gets the foreground set (`agent-teams.md:426`) — which on this host would be the sole source of tool-set variance.

## Cross-cutting: the recurring failure shape

Nine sections, one pattern worth naming on its own. **Almost every subagent constraint fails silently.**

| Mechanism | Failure signal | Cite |
|---|---|---|
| Filter 2 removes built-ins from a background agent | **none**, unless it empties the list | `sub-agents.md:336` |
| `tools` list is empty, or `disallowedTools` eats it | **none** — launches toolless | `errors.md:1408` |
| Plugin subagent's `hooks`/`mcpServers`/`permissionMode` | **none** — ignored | `sub-agents.md:229` |
| Project frontmatter hooks, folder untrusted | debug log only | `sub-agents.md:625` |
| `name` containing `:` | debug log only, file not loaded | `sub-agents.md:277` |
| `memory:` when auto memory is off | **none** — field inert, `Write`/`Edit` grant revoked | `sub-agents.md:516` |
| Preloaded skill missing or disabled | debug log warning | `sub-agents.md:487` |
| At the depth limit | **none** — `Agent` simply absent | `sub-agents.md:862` |
| `maxTurns` reached | **not documented** | §8 |
| `--agent` definition deleted on resume | warning, but **reverts to full default tools** | `sub-agents.md:737` |
| `SubagentStart` hook exit 2 | subagent's own transcript only | `hooks.md:739` |
| Failed subagent in `/tasks` | **leaves the list** | `sub-agents.md:779` |

Design implication: **a delegated agent cannot be trusted to report its own misconfiguration, and the parent gets no signal either.** Any team design needs an explicit capability self-check — an agent that states, in its report, what it could actually do — because no harness surface provides one.

## Open items and UNVERIFIED claims — the work queue

Every claim above that is UNVERIFIED, UNDOCUMENTED, or inherited, each with the one-line experiment that would settle it. Ordered by decision impact, not by section. **P1 = changes the design; P2 = changes an implementation detail; P3 = tidy-up.**

| # | P | Claim / question | § | Experiment that settles it |
|---|---|---|---|---|
| 1 | **P1** | Does a **fork's `AskUserQuestion`** actually reach the human, or is it present-but-inert like its `Agent` at depth? | 3, 2 | With `CLAUDE_CODE_FORK_SUBAGENT=1` (already set), run `/subtask ask me a multiple-choice question about X` and observe whether a prompt renders. Inert ⇒ error or silent no-op. |
| 2 | **P1** | **Is `AskUserQuestion` genuinely unreachable from every delegated path?** If so, `clarify-before-acting`'s `ask_quality` gate covers the lead only. | 2 | Spawn a general-purpose subagent instructed to call `AskUserQuestion`; confirm the tool is absent from its pool and that no prompt reaches the terminal. Control arm: same agent calls `Read`, which must succeed. |
| 3 | **P1** | **Real parallelism cap**: does `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` (10) bind before `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (20)? Does a queued agent hold a concurrency slot? | 8 | Spawn 16 trivial subagents that each log a timestamp to a distinct file; check whether start times cluster in two waves of ~10. Control arm: repeat with the var set to `16` and confirm one wave. |
| 4 | **P1** | **`maxTurns` exhaustion has no documented signal** — is a truncated report distinguishable from a complete one? | 8 | Spawn an agent with `maxTurns: 2` on a task needing ~6 turns; inspect the returned result and its transcript tail for any marker. If none, treat every delegated report as possibly truncated. |
| 5 | **P1** | `Grep`, `Glob`, `TodoWrite` absent from this teammate's pool despite being in the documented background set — explicit spawn-time narrowing, or a doc/impl gap? | 1 | The lead reports the `tools` value it passed when spawning this agent. If it passed none, it is a doc gap worth reporting upstream. |
| 6 | **P2** | **`tokenSamples`** in the `subagentStatusLine` `tasks` array — shape and meaning undocumented. | 9A.1 | Wire a `subagentStatusLine` script that dumps raw stdin to a file; spawn one subagent; read the JSON. Settles items 6 and 7 together. |
| 7 | **P2** | Are all 13 `tasks` fields actually populated in practice, and does `status` distinguish **stalled** from **working**? | 9A.1 | Same dump. Compare a working agent against one blocked on a permission prompt; diff the `status` values. |
| 8 | **P2** | **`agent.name` redaction** — are user-defined agent names really replaced in OTEL, making role-name dashboards impossible? | 9A.2 | Enable OTEL to a local collector, spawn a custom-named agent, inspect the `agent.name` attribute on its `claude_code.llm_request` span. Control arm: spawn `Explore`, whose name should appear verbatim. |
| 9 | **P2** | Subagent memory: are **non-`MEMORY.md` topic files** read on demand as they are for main-session auto memory, or inert? | 5 | Give an agent `memory: local`, write a `debugging.md` beside its `MEMORY.md` containing a distinctive token, and ask a question that token answers without naming the file. |
| 10 | **P2** | Does setting **`memory:` on a `tools: Read, Grep, Glob` agent** actually grant `Write`/`Edit`, breaking read-only intent? | 5 | Define exactly that agent and ask it to write a file outside its memory dir. If it can, "read-only + memory" is a contradiction to ban in role definitions. |
| 11 | **P2** | **Empty `tools: []`** and a `disallowedTools` that eats the whole list both launch a toolless agent with no error — still true on the installed version? | 8 | Define an agent with `tools: []`; spawn it; confirm it launches and returns something useless rather than erroring. Control arm: `tools: [Grpe]` must produce the zero-tools refusal. |
| 12 | **P2** | **Teammate transcript naming** (`<uuid>.jsonl`) — inherited from `.claude/rules/probes-need-a-control-arm.md`, **not re-derived by me**; the corpus documents only the subagent path. | 9 | `ls` the session dir while a teammate runs, and compare against `{sessionId}/subagents/agent-*.jsonl` for a subagent running at the same time. Fixes the rule file either way. |
| 13 | **P2** | **Agent-team teammate limits** — `sub-agents.md:910` says teammates "follow their own limits"; those limits appear on no page I read. | 8 | Grep `agent-teams.md` by shape for numeric caps; if absent, ask the lead to spawn teammates until refusal and record the message. |
| 14 | **P3** | Does a **plugin subagent's ignored `hooks`/`mcpServers`/`permissionMode`** really produce no warning? | 7 | Put a `PreToolUse` hook in a plugin agent's frontmatter, spawn it, and confirm the hook does not fire and nothing is logged outside the debug log. |
| 15 | **P3** | Does the **`--agent` definition-deleted fail-open** really restore *full default tools*? | 9 | Start `claude --agent <restrictive>`, delete the file, resume, and check whether `Write` is now available. A widening-on-delete is worth a rule if confirmed. |
| 16 | **P3** | **Version band.** All `min-version` markers I saw are ≤ v2.1.219; the companion report is captioned 2.1.221. I did **not** diff offline vs live. | — | `claude --version`, then diff the two `sub-agents.md` texts MDX-comment-stripped before relying on any post-2.1.219 behaviour. |

**Refuted, needs no experiment:** `blue_for_subagents_only` does not exist in the corpus (0 files; three invented controls also 0, two known-present controls 11 and 4). `agent_path_count` is real but is a **plugin-inventory** metric (`monitoring-usage.md:928`), not agent observability. `read-agent-traces` is a doc anchor, not a knob.

**Settled during this pass, previously open:** whether the parent can read a subagent's transcript (yes — `agent_transcript_path` on `SubagentStop`, `hooks.md:2048`); whether per-agent token spend is observable (yes — `subagentStatusLine.tasks[].tokenCount`, correcting my own §9 claim); and whether fork mode is active on this host (yes — `~/.claude/settings.json:10`).

### Original narrative list (retained)

Listed so nothing above is read as settled when it isn't.

1. **Does a fork's `AskUserQuestion` actually reach the human?** §3. Forks skip both filters (`sub-agents.md:324`), so the tool is present; but `agent-sdk__user-input.md:839` scopes its limitation to "subagents spawned via the Agent tool", which a Claude-spawned fork is. Present-but-inert is a real possibility (that is exactly what happens to a fork's `Agent` at the depth limit). **Needs a live probe**, and it matters: if it works, a fork is the only delegation shape that can ask the human, which would materially change a team design.
2. **`Grep`, `Glob`, `TodoWrite` absent from this teammate's pool** (§1) despite being in the documented background set. Explainable by an explicit `tools` narrowing at spawn, which I cannot see from inside. Resolvable by the lead reporting the spawn parameters it used.
3. **Interaction of `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` (10) with `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (20)** (§8). Does a subagent waiting on the tool-use gate hold a concurrency slot? Not stated. The "real cap is 10" reading follows from `env-vars.md:281`'s plain text but is **not measured** — do not cite it as a throughput figure.
4. **`maxTurns` exhaustion signal** (§8). No documented message, no `errors.md` entry. Whether a truncated report is distinguishable from a complete one is unknown and is a live correctness risk for delegated work.
5. **Subagent memory topic files** (§5). Main-session auto memory reads topic files on demand (`claude-directory.md:545`); whether subagent memory does the same, or only auto-loads `MEMORY.md`, is not stated.
6. **Teammate transcript naming** (§9). The `<uuid>.jsonl` claim is **inherited** from `.claude/rules/probes-need-a-control-arm.md` and I did **not** re-derive it — the corpus documents only the subagent path. Per that rule's own item 6, it is marked unverified rather than restated as mine.
7. **Agent-team teammate limits** (§8). `sub-agents.md:910` says teammates "follow their own limits instead"; those limits are not stated on any page I read.
8. **Version band.** Every `min-version` marker I encountered lands at **v2.1.219 or lower**; the companion `harness-settings-reference.md` is captioned 2.1.221. I did **not** diff the offline tree against live `code.claude.com` — per the brief, a byte-size difference is not staleness, and I had no finding that turned on a post-2.1.219 behaviour. Anyone extending this report into 2.1.220+ territory should verify live rather than assume this tree covers it.

## GitHub repos touched

_None._ Every source read was the offline vendor documentation tree at `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/` (Anthropic's Claude Code docs, mirrored from `code.claude.com/docs/en/`), plus first-party observation of this session's own tool pool. No GitHub repository source, README, issue tracker, or mintlify site was queried.

Pages read: `sub-agents.md` (in full), `agent-view.md`, `statusline.md`, `monitoring-usage.md`, `llm-gateway-protocol.md`, `headless.md`, `cli-reference.md`, `changelog.md`, `whats-new__2026-w29.md`, `agent-sdk__observability.md`, `agent-teams.md`, `hooks.md`, `errors.md`, `tools-reference.md`, `env-vars.md`, `settings.md`, `memory.md`, `claude-directory.md`, `agent-sdk__user-input.md`, `agent-sdk__subagents.md`, `agent-sdk__claude-code-features.md`, `agent-sdk__hosting.md`.
