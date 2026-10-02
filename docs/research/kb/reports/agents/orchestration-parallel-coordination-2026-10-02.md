# How one Claude Code session should coordinate parallel work (2026-10-02)

Question (Ray, 2026-10-02): how should ONE main Claude Code session coordinate
parallel work while keeping its own context and token spend low? Compared:
Agent-tool subagents (foreground/background, `fork`), `/subtask`, `/fork`,
`claude --bg` + `claude attach/logs` + cross-session `SendMessage`, agent teams,
the Workflow tool, git worktrees (`isolation: worktree`), and Herdr.

Lane: `orchestration-research` (teammate of `team-lead`), research-sweep in-lane
steps (no Workflow tool in this lane). Claude Code measured: **2.1.287**.

## Answer

Most of this coordinator's context goes on **results flowing back into it**. The
mechanism matters less. Every
approach is cheap to *launch*. They differ in what lands in the coordinator's
window afterwards and how many approvals they generate. For this repo:

1. **Default to in-session subagents that write their report to a file and return a
   short pointer**. Our `agent-report-persistence.md` already mandates the report
   file, so the return message can be a few lines. Subagent output stays in the
   subagent's context, and only the final report comes back
   (`$CC/sub-agents.md` "Isolate high-volume operations").
2. **Use a saved Workflow when a fan-out has more than ~5 agents or the findings need
   cross-checking**: "Claude's context holds only the final answer" (`workflows.md`
   "When to use a workflow"). The repo already has four
   (`.claude/workflows/{gated-implementation,graphify-refresh,modernization-audit,research-sweep-run}.js`).
3. **Use `claude --bg` sessions launched inside pre-made worktrees for long
   implementation lanes** (the `parallel-work-split` skill §5). Monitor them with
   `claude agents --json --all`, a polled state field, and read the lane's report
   file. **Do not depend on `SendMessage` for results** until the
   permission-class mismatch below is fixed.
4. Use **`fork`/`/subtask`** only for read-only side tasks that truly need the
   conversation, and never nested. Use **`/fork`** only to branch the whole
   session onto an alternative path.
5. **Agent teams** are what this session runs on, but they are experimental and the
   most expensive per worker. Keep them for a lead that must steer peers mid-task.
6. Use **Herdr** for cross-vendor lanes (codex/agy/claude in panes) and for a human-visible
   control surface. Its result channel is screen scraping, so hand results back as files.

### Why the SendMessage approval friction happens (root cause, derived)

`crossSessionInbound` is unset in user, project and local settings (probed: 0
matches), so Claude Code decides **per message from the two sessions'
permission-mode classes** (`cross-session-messaging.md` "Control inbound messages"):

> **The receiving session prompts for permissions**: Claude Code delivers each
> message. It holds one for your approval only when the sending session identifies
> itself as bypassing permission prompts.
> **The receiving session bypasses permission prompts**: Claude Code holds each
> message for your approval. It delivers one only when the sending session
> identifies itself as also bypassing.

`~/.claude/settings.json` sets `"defaultMode": "auto"`, so a `claude --bg` worker
starts in auto, which counts as prompting. This coordinator runs in `bypassPermissions`. **Both
directions are therefore held.** Three fixes, cheapest first:

| Fix | Effect | Who decides |
|---|---|---|
| Run the coordinator in the **same class** as its workers. Both `auto` delivers both ways | Removes the friction with no config change | Ray (launch habit) |
| Launch workers with `claude --bg --settings '{"crossSessionInbound":"accept"}' …` | Coordinator→worker delivered. Worker→bypass-coordinator still held | per launch, repo-documentable |
| `crossSessionInbound: "accept"` in **user** settings | Everything delivered to every session on this machine | Ray (user-level file). A project or local value can only be *stricter* (`settings-reference.md:5011,5024`) |

Upstream bugs make held messages worse than an extra click. #85888 (OPEN): a
held message to a **background** recipient has no approval UI and stays parked
forever. #85503 (OPEN): `SendMessage` returns `success:true` before the inbound
decision, and the held notice arrives about 5 minutes later. #94624 (OPEN): messages
are silently dropped despite `success:true`.

## Decision table

| Mechanism | Coordinator context cost | Isolation | How results return | Approval friction | Failure modes (evidence) | Use in this repo when |
|---|---|---|---|---|---|---|
| **Subagent, non-fork** (Agent tool, our typed agents) | Brief + final report only. Many detailed reports "can consume significant context" (`sub-agents.md` Run parallel research warning) | Own context. Loads CLAUDE.md+rules (not Explore/Plan). Same checkout unless `isolation` | Agent-tool result (fg) or completion notification (bg). Fork mode is on by default, so **all spawns are background** and `run_in_background` is removed | Background subagents surface **every** prompt in main. A session-lasting grant applies to the whole session | Interrupting a turn kills in-flight bg subagents silently (#78151 OPEN). Bg subagent stalls with `completed` and no text (#83848 OPEN) | Research, review, gates (`gate-runner`, `cold-reviewer`, `Explore`). Report to file, return ≤10 lines |
| **Fork** (`subagent_type: "fork"`, `/subtask`) | Result only, but the fork **replays the whole conversation**. "~5-10x the token cost of a fresh … subagent" (#88841 OPEN, inherited figure, unverified). Shares the prompt cache, so the first request is cheaper than a fresh agent (`sub-agents.md` "How forks differ") | Same tools/model/system prompt as main. Can take `isolation: "worktree"`. Can't fork again | Message into main conversation | Prompts surface in your terminal. Runs under the parent's mode since 2.1.285 (fixed #95155, still open on tracker) | Context-inheriting fork made 2 **unrequested commits** (edobry/minsky `block-nested-fork-dispatch.ts`). Auto-spawned forks burn quota (#79735) | Read-only side task that needs the conversation. Never nested. Never for "wait/report back" |
| **`/fork`** (copy session to a new background session, v2.1.212+) | Zero after the fork (independent). Cache likely rebuilt: session forks mint a new session id, and the scratchpad path in the system prompt changes (#77306 OPEN; applying it to `/fork` is **inference**) | New bg session. Moves into its own worktree before editing | Only via cross-session messaging, or you attach | Same messaging-class rules as `--bg` | Same as `--bg` | Try an alternative approach from the current state |
| **`claude --bg`** + `attach`/`logs`/`agents --json` | **Zero** until you read `logs` or a message arrives. Separate quota ("roughly ten times as fast" for 10 agents, `agent-view.md` Limitations) | Full separate session. Auto-moves into `.claude/worktrees/` before editing, **unless already in a linked worktree** (our skill launches inside one) | `claude agents --json --all` state (`working/blocked/done/failed/stopped`, `waitingFor`) is "the supported way to read session state from outside". Results go to files or messages | Starts like a fresh `claude` in that dir (user `auto`). Messaging is held across classes (see root cause). Bypass needs a one-time interactive disclaimer | By default a bg session **commits and pushes without asking** and may open a draft PR, unless the task or CLAUDE.md says otherwise (`agent-view.md` "How file edits are isolated"). Held msg to bg recipient parked forever (#85888). Delivery can kill the recipient's bg Bash (#91139 OPEN) | Long implementation lanes from `parallel-work-split` (brief says STOP AT commit, no push) |
| **Agent teams** (enabled here by project `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) | Every teammate message lands in the lead's context. "Significantly more tokens". Teammates load CLAUDE.md/MCP/skills at spawn (`agent-teams.md` Token usage). Delivery can trigger a full cache rewrite (#80604 OPEN, 3/44) | Own context. **No worktree isolation**, so partition files | `SendMessage` to lead plus shared task list | Prompts bubble to lead. Teammates inherit the lead's mode (bypass lead means bypass teammates) | Experimental: no resume of in-process teammates, task status lags, one team per session, no nesting. Messages leak across sessions (#95954 OPEN) | A lead must steer several peers mid-task. Note: **any named Agent call from main becomes a teammate** while the flag is on |
| **Workflow tool** (`.claude/workflows/*.js`) | **Lowest per agent**: intermediate results stay in script variables, only the final answer returns | Script runtime. Per-agent `isolation` | Final return value. `/workflows` shows per-agent tokens | Pauses only for agent permission prompts. No mid-run user input | `Large workflow` warning at >25 agents or >1.5M tokens. Resumable only in the same session. Cache TTL 5 min unless `subagentPromptCacheTtl=1h` | ≥5 homogeneous agents, cross-checked findings, repeatable pipelines (`/research-sweep-run`, `/gated-implementation`) |
| **Git worktrees** (`isolation: worktree`, `git worktree add`) | None (a property, not a channel). Before 2.1.286, isolated subagents loaded CLAUDE.md+imports **twice** (fixed) | File isolation only | n/a | n/a | Claude-created worktrees deleted with the session. Commit first | Any parallel writer. Our lanes use `../dotfiles.worktrees/<lane>-<date>` |
| **Herdr** (0.9.3; this session runs inside it, `HERDR_ENV=1`) | Coordinator pays for **every line it reads** (`agent read --lines N`). Docs fallback: have the agent write Markdown and reply with the path | Separate processes in panes. `herdr worktree create` makes a grouped worktree workspace | Screen scrape plus lifecycle state (`idle/working/blocked/done/unknown`). `agent prompt --wait` | `blocked` means an approval/question UI was detected. `agent prompt` refuses a blocked agent. You answer in the pane | No fleet event stream yet, so polling (herdr #4027 OPEN). AskUserQuestion reports idle under a custom agent (#4573). Closing a pane kills Claude before SessionEnd hooks (#4851). **Local:** Claude integration outdated v9<v10, server 0.9.1 vs client 0.9.3 | Cross-vendor lanes (codex/agy/opencode) and human-visible supervision. Results by file |

## Evidence

| Claim | Source | Quote / measurement |
|---|---|---|
| Five parallel approaches + worktrees/messaging/`/batch` as supports | `.agent/kb/raw/cc-docs-2026-10-01/ccdocs/agents.md` | "Claude Code has five ways to work on several tasks at once: subagents, agent view, agent teams, dynamic workflows, and projects." |
| `/subtask` = forked subagent; `/fork` = copy session to background | same | "Start one with `/subtask` … To copy the whole session into a new background session … use `/fork`." |
| Fork mode on by default, so all spawns run in background | `ccdocs/sub-agents.md` (Run subagents in foreground or background) | "Where fork mode is on, as it is by default in an interactive session, Claude Code runs the subagent in the background … Claude can't ask for the foreground." |
| Fork shares prompt cache | `ccdocs/sub-agents.md` (How forks differ) | "its first request reuses the parent's prompt cache. This makes forking cheaper than spawning a fresh subagent for tasks that need the same context." |
| Many results consume coordinator context | `ccdocs/sub-agents.md` (Run parallel research) | "Running many subagents that each return detailed results can consume significant context" |
| Workflow keeps intermediate results out of context | `ccdocs/workflows.md` | "A workflow script holds the loop, the branching, and the intermediate results itself, so Claude's context holds only the final answer." |
| Workflow limits | `ccdocs/workflows.md` (Behavior and limits, Cost) | 16 concurrent agents by default; `Large workflow` warning at >25 agents or >1.5M tokens |
| bg session state for scripts | `ccdocs/agent-view.md` (Read session state from a script) | "`claude agents --json` is the supported way to read session state from outside Claude Code" |
| bg session commits/pushes by default | `ccdocs/agent-view.md` (How file edits are isolated) | "Commit and push: Claude commits without asking, and pushes the branch when the repository has a remote." / "Your git instructions take precedence" |
| bg skips own worktree inside a linked worktree | same | "The session is already inside a linked git worktree, whether Claude created it … or you created it with `git worktree add`" |
| Messaging class rule | `ccdocs/cross-session-messaging.md` | quoted in Answer |
| Project can't loosen inbound | `ccdocs/settings-reference.md:5011` | "A project or local value applies only when it's stricter than the value managed settings, the `--settings` flag, or user settings give." |
| `notify_when_idle` scope | `ccdocs/cross-session-messaging.md` | "Only the Claude in your main conversation can subscribe, and only to your sessions on this machine." 12 h expiry |
| Local settings | `~/.claude/settings.json`, `.claude/settings.json` (count-only probes) | `defaultMode: "auto"` (user); `crossSessionInbound` absent in user/project/local; `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` (project) |
| Teams token cost | `ccdocs/costs.md` (Agent team token costs) | "Use Sonnet for teammates … Keep teams small … Shut down teammates when their work is done." |
| 2.1.285 fork permission fix | `ccdocs/../rel-v2.1.285.md` | "Fixed fork subagents not keeping the session's plan mode or `dontAsk` mode" |
| 2.1.286 worktree double-load fix | `rel-v2.1.286.md` | "Fixed subagents spawned with worktree isolation loading the project CLAUDE.md and its imports a second time" |
| Herdr result channel | `docs/research/kb/raw/herdr-docs-2026-10-02/pages/agent-automation.mdx` | "If a full response is still unavailable, ask the agent to write it as Markdown in a temporary directory and reply only with the file path" |
| Herdr live state | `herdr status`, `herdr integration status` | client 0.9.3 / server 0.9.1 (`endpoint_compatible: yes`); `claude: outdated (v9 < v10)`; `codex: current (v8)` |
| Real-world nested-fork guard | github.com/edobry/minsky `.claude/hooks/block-nested-fork-dispatch.ts` | "The fork inherited the full implementation context and made 2 unrequested commits to the shared session branch." |
| Real-world no-op dispatch guard | github.com/jcdendrite/claude-config `.claude/plans/detect-noop-fork-dispatch.md` | PreToolUse deny on `Agent` for dispatches "spawned solely to wait … or report back immediately" |
| Real-world agent-view policy | github.com/Chachamaru127/claude-code-harness `docs/agent-view-policy.md` | `claude agents --json` limited to diagnostics/scripting; teammate spawns via the Agent tool |

Fan-out manifests (scratchpad, `research-fanout`, all rc=0):
`scratchpad/orch/fan{1..7}/manifest.json`. The queries were claude-code "background session",
"cross-session message", "fork subagent", "subtask", "agent teams tokens";
herdr "claude code", "orchestrate agents". The full query set, counts and
controls are in `docs/research/saved-searches/orchestration-2026-10-02.toml`.

## Conflicts resolved

- **#95155 (fork writes in plan mode) is OPEN on the tracker, but 2.1.285's release note says it is fixed.** I trusted the release note, because shipped source beats an issue thread.
- **The docs call forks "cheaper", while #88841 calls them 5-10x more expensive.** Both are true. A fork is cheaper than a fresh agent *that needs the same context*. It costs more than a fresh agent that does *not* need the context. The 5-10x figure is the reporter's and is unverified here.
- **#77306 (session forks forfeit the cache) predates 2.1.287.** I did not measure whether `/fork` still forfeits it, so that row is labeled inference.

## Gaps (control-armed)

- **No local token measurement** per mechanism. Every cost claim comes from vendor docs or issue reports, and no `/usage` A/B was run. Next step: run one identical read-only task as a subagent, a fork, a `--bg` session and a 1-agent workflow, and compare `/usage` attribution.
- **anthropics/claude-code discussions returned `empty_unverified`** because the repo has `has_discussions=false`. Control: herdrdev/herdr (`true`) returned 15. So "no discussions" there means the feature is off, not that nothing was found.
- **Code-search `total_count` is not a hit count.** `"subagent_type" "fork"` reported 41,664 but **0/5 and 0/10** re-fetched hits matched; the tuned `subagent_type fork path:.claude` matched 3/10. Every code row records `verified n/m`. The controls discriminate: health 9, must-hit 26,624, fresh-nonce absent 0. Two queries were 403 rate-limited on the first pass and re-run. They are recorded as rate-limited, never as 0.
- **`notify_when_idle` under the class-mismatch default** is unverified. The docs cover explicit `hold`/`refuse` but not the unset default.
- **Herdr Claude integration v10 and the 0.9.1 server** were not upgraded. The fix is user-level (`~/.claude/hooks`, user `settings.json`), so it needs Ray's decision.

## Recommendation for this repo

1. Adopt the decision table above. Keep **shipping serial** (`parallel-work-split` skill: one `mise run ship` per repo from the main checkout).
2. **Fix the messaging friction by launch habit first.** Run the coordinator in `auto` (same class as `claude --bg` workers), or launch workers with `--permission-mode bypassPermissions` when the coordinator must stay in bypass. If Ray wants messaging regardless of class, the knob is user-level `crossSessionInbound: "accept"`. A project file cannot loosen it.
3. Extend the `parallel-work-split` skill (branch `feat/parallel-work-split-skill`, §5) with three things. (a) Monitor lanes with `claude agents --json --all` (`state`/`waitingFor`) under `mise run bounded-wait`. (b) Results come from the lane's report file, never from `claude logs` scraping. (c) A class note: launch `--bg` workers in the coordinator's permission class.
4. Consider a PreToolUse guard against **nested** `fork` dispatch, the minsky pattern. That would be a #1482-adjacent item. It is not proposed as a change here.
5. Note that `.agent/plans/parallel-lane-plan-2026-10-02.md` lanes A–J are file-disjoint `--bg` candidates. Lane C/D (`test_workflows_js.py`) stays sequenced as that plan says.

## Provenance

In-lane research-sweep (no Workflow tool available to this teammate). Step 00: the newer
CC mirror `.agent/kb/raw/cc-docs-2026-10-01/ccdocs/` (225 pages), which has
`agents.md`, `agent-view.md`, `cross-session-messaging.md` and `workflows.md`. Herdr
mirror: `docs/research/kb/raw/herdr-docs-2026-10-02/` (24 files + llms.txt/llms-full.txt).

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issues/PRs/releases for bg sessions, fork, cross-session messaging, teams (discussions disabled)
- [herdrdev/herdr](https://github.com/herdrdev/herdr) — official docs at v0.9.3, issues/discussions/releases
- [edobry/minsky](https://github.com/edobry/minsky) — nested-fork PreToolUse guard (real-world failure)
- [jcdendrite/claude-config](https://github.com/jcdendrite/claude-config) — no-op dispatch guard plan
- [Chachamaru127/claude-code-harness](https://github.com/Chachamaru127/claude-code-harness) — agent-view usage policy
- [cli/cli](https://github.com/cli/cli) — code-search health control only
- Code-search hit repos sampled for verification (no content used beyond the match): zebbern/claude-code-guide, stormzhang/ai-coding-guide, Cranot/claude-code-guide, Snailclimb/JavaGuide, luongnv89/claude-howto, dyoshikawa/rulesync, WebisityStudio/claude-codex-mcp-bridge, Atmosphere/atmosphere, forcedotcom/salesforcedx-vscode, coleam00/Archon, Donchitos/Claude-Code-Game-Studios, openaddresses/openaddresses, danielmiessler/LifeOS, ohmyzsh/ohmyzsh, trailofbits/claude-code-config, kousen/claude-code-training, oxsecurity/megalinter
