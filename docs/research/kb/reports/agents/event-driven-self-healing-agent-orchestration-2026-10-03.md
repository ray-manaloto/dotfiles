# Event-driven, self-healing agent orchestration — how others automate the coordinator (2026-10-03)

Synthesis node of `/research-sweep-run` (Opus, effort high). Question: how do other projects,
frameworks, plugins and skills run a **fully automated** multi-agent coding workflow, especially
an orchestrator that self-heals, self-optimizes and self-learns, triggered by **events** rather
than a cron/`/loop`? Context: the coordinator auto-handoff (#1583, a `session.measure`
function-hook plugin) did not fire because the coordinator started ~45 s before the plugin
reached the main checkout, and at 98% context with auto-compact off it could no longer act
(`docs/research/kb/reports/agents/coordinator-auto-handoff-not-firing-2026-10-03.md`). The
only fallback was a session-scoped `/loop` cron inside the watcher session.

## Answer

**The sweep is INCOMPLETE.** Four mandatory stages did not fully run: (1) the GitHub
code-search health control `repo:cli/cli filename:README.md` was RATE-LIMITED (HTTP 403), so
none of the empty code-search controls is armed; (2) the langgraph README control was also
RATE-LIMITED; (3) `All-Hands-AI/OpenHands` redirects to `OpenHands/OpenHands`, so its issue
search failed with HTTP 422 and never ran; (4) `ruvnet/claude-flow` redirects to `ruvnet/ruflo`,
same failure. The OpenHands and claude-flow/ruflo dimensions are therefore unknown, not empty.

With that caveat, the evidence points one way:

1. **The restart trigger has to live outside the session it restarts.** Every working
   "self-healing" design found puts the watchdog in a separate, supervised process: the
   Claude Code background supervisor itself (restarts processes that exited unexpectedly),
   `claude-tmux-dog` (an external `cdog` process fed by hooks, brought back at login by
   launchd), Podiom (a long-running Go daemon that shells out to `claude`/`codex`), Composio
   Agent Orchestrator (a desktop workspace that owns the worker sessions). None of them relies
   on a hook *inside* the dying agent as the only trigger. This is the same thing the side
   agent's note said about the watcher's `/loop`.
2. **Claude Code does not ship the in-session primitive you would want, and the four
   requests for it are closed without being built (not a maintainer ruling).** Hooks cannot
   spawn subagents or background agents (#64898, closed *not_planned* 2026-08-13).
   Orchestrators get no push notice when a subagent dies (#87142, closed *not_planned*
   2026-09-20; v2.1.199 has since shipped a subagent API-error failure notification, so part of
   that gap is addressed). A parent session is not woken when a child session's turn ends
   (#62631, closed *not_planned* 2026-08-02). Session auto-restart with context persistence
   (#38210) was closed *not_planned* 2026-05-05. **All four were closed by `github-actions[bot]`
   with the `stale` label (inactivity)**, so "not_planned" here means nobody pushed them, not
   that Anthropic declined. See Verification.
3. **What Claude Code ships covers process *death* and, inside the process, auto-compaction,
   but not a *wedged* coordinator.** The supervisor restarts a background session's process
   that "exited unexpectedly while the supervisor is running" (`agent-view.md:749`); a session
   the user backgrounded and then killed is marked stopped, not restarted. `claude respawn
   <id>` "resumes its saved conversation" (`agent-view.md:695`). Neither line says what happens
   to context size; a resumed coordinator will normally auto-compact on its next turn
   (`context-window.md:1618-1632`; this repo deliberately leaves `DISABLE_AUTO_COMPACT` unset,
   though in this incident auto-compact was off). The real native gap is narrower than "full
   context": a coordinator that is stuck, blocked or too full to take a turn has not "exited
   unexpectedly", so the supervisor does not restart it, and compaction can stop with a
   "thrashing" error when one large output refills the context. This repo hands off at a 30%
   policy threshold, not at the hard limit. `claude agents --json --all` is the documented way
   to read state from outside; the docs tell callers to **poll** it (`agent-view.md:720`;
   `~/.claude/jobs/` files are explicitly not a stable interface, `:731`). The documented push
   signal, `Notification` with `agent_completed`/`agent_needs_input`, "fires only while agent
   view is open" (`hooks-guide.md:193-194`). That is a statement about that one hook, not about
   all push signals: a background session is a full Claude Code process, and its own settings
   hooks (`Stop`, `StopFailure`, `SessionEnd`) run inside it and can push a file or webhook
   outward. Not tested live for a `--bg` session. A worktree-isolated background session also
   opens a draft PR when it finishes (`agent-view.md:989`), a GitHub-side event.
4. **Two native details matter for the current failure.** `settings.json` hooks reload live
   without a restart (`settings.md:584`), while the plugin function hook needed a session
   start or `/reload-plugins`. And a statusLine command receives
   `context_window.used_percentage` on every update (`statusline.md:186`). A context-threshold
   *producer* wired through settings hooks/statusLine would therefore have reached the
   coordinator that started 45 s early. Neither helps once the session is too full to take a
   turn, so the *consumer* (the code that starts the successor) still has to be external.
5. **"AI software factories" are queue-, webhook- or CI-event-driven, plus cron.** Examples:
   GitHub Agentic Workflows (`github/gh-aw`, Actions-event-triggered; a third-party post shows
   it fixing CI failures on its own), OpenAI's internal factory (a third-party report says
   agents babysit PR comments the way CI does), Composio AO, and kai-linux/agent-os. agent-os
   is **cron-driven** despite its "zero human intervention" headline: its README mentions
   cron 16 times, and its incident scanner runs every 6 h.
6. **Self-learning loops are retrospective jobs that write proposals, not live
   self-modification.** agent-os files `autonomous-fix` issues from a 6-hourly incident scan
   and lists "retrospectives" as its current maturity level. A third-party post (Adaptive)
   describes an insights→evolution agent that rewrites system prompts. This repo already has
   the same shape: the SessionEnd `command-audit` loop, plus the proposed Retrospect phase
   (#1502).

**Recommendation in one line:** replace the session-scoped `/loop` with a **launchd
`KeepAlive` supervisor** (declared via `mise bootstrap`). It should watch transcripts and an
inbox **by events**, and call `claude --bg` for a successor. See *Recommendation* for the
ranked list.

### On the user's meta-question: does `research-sweep-run` have these phases yet?

| Requested phase | Status in `.claude/workflows/research-sweep-run.js` | Evidence |
|---|---|---|
| Search GitHub **issues / PRs / discussions** | **Present** (MANDATORY). The `Dependencies` phase runs `github-issues,github-discussions,github-releases` for the repo and every related repo. PRs arrive through the issues search, and the `Read` phase reads issues, PRs and discussions with `gh api` / `gh api graphql`. | `research-sweep-run.js:7`, `:105`, `:302`, `:325`, `:470`. This run's SWE-agent dependency row returned PRs #1564/#1563 through `github-issues`. |
| **Saved GitHub searches** that can be re-run to find newer examples | **Not added.** No phase, and no reference to `saved-searches`/`watches` anywhere in the workflow, the research-sweep skill, `python/src` or `mise.toml` (grep rc=1; the control term `research-fanout` hits 7× in the same file). One hand-written record exists, `docs/research/saved-searches/orchestration-2026-10-02.toml`, in the draft `[[watch]]` schema. Nothing reads it. | Issue **#1502** is OPEN: "research-sweep-run: add Retrospect phase (proposal file only) and Saved-searches phase (reads N1 watches.toml)". It is blocked on the unbuilt N1 `github-watch` (header of the TOML). |
| Discussions coverage actually working | **Partial.** For every `anthropics/claude-code`, langgraph, SWE-agent, OpenHands and claude-flow dependency run, `github-discussions` returned `empty_unverified` (its canary also returned 0). It returned real rows for `openai/codex`, `microsoft/autogen` and `smtg-ai/claude-squad`. | Dependency manifests below. |

## Evidence

### Claims (each kept to what kind of statement it is)

| Claim | Kind | URL or file:line | Quote |
|---|---|---|---|
| Claude Code hook lifecycle includes SessionStart/SessionEnd, Stop, StopFailure, SubagentStop, TeammateIdle, PreCompact/PostCompact, FileChanged, Notification | **SHIPS (vendor docs)** | KB `$CC/hooks.md:37-69` | "`StopFailure` — When the turn ends due to an API error"; "`SessionEnd` — When a session terminates" |
| `settings.json` hooks hot-reload; plugin function hooks load at session start or `/reload-plugins` | **SHIPS (docs)** + repo spec | `$CC/settings.md:584`; spec P7 cited in the handoff-failure report | "reloads them when they change … including edits to `permissions`, `hooks`" |
| statusLine gets live context % | **SHIPS (docs)** | `$CC/statusline.md:186` | "`context_window.used_percentage` — Pre-calculated percentage of context window used" |
| Supervisor restarts unexpectedly-exited background sessions | **SHIPS (docs)** | `$CC/agent-view.md:749` | "Exited unexpectedly while the supervisor is running: the supervisor restarts the process" |
| `claude respawn` resumes the saved conversation (that a full context stays full is an inference, not stated; resumed sessions auto-compact) | **SHIPS (docs)** | `$CC/agent-view.md:695` | "The restarted session resumes its saved conversation" |
| External state is read by polling `claude agents --json` | **SHIPS (docs)** | `$CC/agent-view.md:720` | "Poll `claude agents --json --all` … read each entry's `state`, `status`, and `waitingFor`" |
| `agent_completed` push only while agent view is open | **SHIPS (docs)** | `$CC/hooks-guide.md:194` | "A background session finishes or fails. Fires only while agent view is open" |
| Hooks cannot spawn subagents/background agents; request declined | **ISSUE (closed not_planned 2026-08-13, stale-bot auto-close)** | https://github.com/anthropics/claude-code/issues/64898 | "Allow hooks to spawn subagents / background agents (programmatic dispatch from hook events)" |
| No reliable subagent death signal for orchestrators; declined | **ISSUE (closed not_planned 2026-09-20, stale-bot auto-close; v2.1.199 shipped a subagent API-error notification)** | https://github.com/anthropics/claude-code/issues/87142 | "currently has no reliable way to learn when a subagent crashes or its connection drops mid-run" |
| No parent wake-up when a child session's turn ends; declined | **ISSUE (closed not_planned 2026-08-02, stale-bot auto-close)** | https://github.com/anthropics/claude-code/issues/62631 | "no mechanism for a child's turn-end or idle-waiting state to wake or notify the parent" |
| Session auto-restart with context persistence; declined | **ISSUE (closed not_planned 2026-05-05, stale-bot auto-close)** | https://github.com/anthropics/claude-code/issues/38210 | title |
| `claude respawn` silently failing on "request too large" — fixed | **ISSUE (closed completed; maintainer comment 2026-05-27)** | https://github.com/anthropics/claude-code/issues/59806 | "Addressed by a merged fix. Please reopen with a fresh repro" |
| Peer-requested context reset (one session hands another a clean context) | **ISSUE (OPEN, proposal)** | https://github.com/anthropics/claude-code/issues/88160 | title |
| Per-agent autocompact + protocol to compact an exhausted teammate | **ISSUE (OPEN, proposal)** | https://github.com/anthropics/claude-code/issues/86716 | "the lead's only documented remedy is to kill the process and spawn a replacement" |
| Field measurement: 65 subagents / 11 fleets / ~11.6 M tokens / 3 session-limit strikes | **ISSUE (OPEN, third-party field report; inherited number, not re-derived)** | https://github.com/anthropics/claude-code/issues/84323 | quoted in claims JSON |
| Background completion notifications lost across CLI restart | **ISSUE (OPEN)** | https://github.com/anthropics/claude-code/issues/75438 | title |
| claude-tmux-dog: hooks (Stop/StopFailure/SessionStart/SessionEnd) push events to an external `cdog`; stall health check; "death-loop rebuild"; compaction at 80%; launchd autostart | **SHIPS (project README; 11 stars, pushed 2026-07-31)** | https://github.com/SnowAIGirl/claude-tmux-dog | "Claude Code hooks (`Stop` / `StopFailure` / `SessionStart` / `SessionEnd`) push events to cdog"; "N consecutive fast Stops (default 8 in 2m) → nuclear rebuild" |
| Composio AO: respawn-resume of a dead worker for the same issue | **PROPOSED, NOT merged** (PR closed, `merged=false`) | https://github.com/ComposioHQ/agent-orchestrator/pull/819 | "When a worker session dies … the new worker now attempts to resume from the previous session" |
| agent-os: issues→PRs, self-healing CI; self-heal of stuck-merge counter | **SHIPS (README + commit; 5 stars)**, **cron-driven** | https://github.com/kai-linux/agent-os ; commit bc58277 | "Every cron entrypoint sources `bin/common_env.sh`"; "treat it as an orchestrator-side fault … auto-reset the counter" |
| agent-os: 6-hourly incident scanner files `autonomous-fix` issues; retrospectives = current maturity level | **SHIPS (README)** | https://github.com/kai-linux/agent-os | "the incident scanner reads the last 24h of runtime signals … and files self-fix issues labeled `autonomous-fix`" |
| Podiom: durable sessions that survive process death, shared ledger, embedded scheduler, daemon + web UI | **THIRD-PARTY self-description (its maintainer, in a claude-squad discussion)** | https://github.com/smtg-ai/claude-squad/discussions/316 | "sessions that survive process death and provider/profile switches … an embedded scheduler" |
| postbag: Claude↔Codex letters, woken via `codex queue`, "without a daemon or polling" | **THIRD-PARTY project announcement** | https://github.com/openai/codex/discussions/44109 | "Delivery uses each vendor's own wake-up mechanism, `codex queue` on the Codex side" |
| session-peer / myc / Lians: inter-session messaging, shared task queue, cross-agent memory | **THIRD-PARTY announcements (not read in full)** | https://github.com/openai/codex/discussions/50547 , /45725 , /39282 | titles |
| claude-squad: tmux + git worktree isolation and a TUI | **THIRD-PARTY description (Podiom maintainer)**. This run has no evidence that claude-squad is event-driven. | https://github.com/smtg-ai/claude-squad/discussions/316 | "isolates sessions with tmux + git worktrees plus a TUI" |
| claude-squad `cs serve` HTTP+SSE API + OTEL | **PROPOSED (draft RFC PR)** | https://github.com/smtg-ai/claude-squad/pull/283 | title |
| GitHub Agentic Workflows used for self-healing CI | **THIRD-PARTY blog**; the repo exists (`github/gh-aw`, 5340 stars) | https://pascoal.net/2026/03/12/self-healing-ci-using-gh-aw/ | "Wait for next CI failure → Agentic workflow triggers & fixes it automatically" |
| OpenAI's agentic software factory: agents babysit PR comments like CI | **THIRD-PARTY report (newsletter)** | https://newsletter.pragmaticengineer.com/p/openai-software-factory | "the coding agent babysits the comments and updates the PR to fix issues surfaced" |
| "Self-healing software factory" (Ona) | **THIRD-PARTY database entry**. Only the title and snippet were read. | https://www.zenml.io/llmops-database/building-a-self-healing-software-factory-with-ai-agents | "Software Factory built Memo … using AI agents on the Ona platform over a 10-day development period" |
| Mend: LangGraph CI-healing agent | **SHIPS per repo description (not read beyond it)** | https://github.com/omkesti/Mend | "diagnose failures, push fixes to a branch, and monitor CI until green" |
| SWE-agent deterministic pre-tool-call policy hook | **PROPOSED (RFC issue)**, not shipped | https://github.com/SWE-agent/SWE-agent/issues/1526 | "RFC: deterministic execution boundaries for tool calls" |
| GNAP (git-native agent protocol) for LangGraph/AutoGen | **THIRD-PARTY proposal in issues**, not shipped by LangGraph/AutoGen | https://github.com/langchain-ai/langgraph/issues/7174 ; https://github.com/microsoft/autogen/issues/7398 | "GNAP … extends LangGraph's coordination model to cross-runtime, cross-machine deployments" |
| AutoGen loop-prevention relies on step counters | **OPINION (discussion)** | https://github.com/microsoft/autogen/discussions/8135 | "everyone is relying on basic Python step_counters" |
| Codex lacks a first-class Monitor tool | **ISSUE (feature request)** | https://github.com/openai/codex/issues/44855 | "add a first-class `monitor` capability to Codex, similar to Claude Code's Monitor tool" |
| launchd `WatchPaths` is race-prone; `QueueDirectories` keeps a job alive while a dir is non-empty | **SHIPS (OS man page, measured locally)** | `man launchd.plist` (WatchPaths, QueueDirectories) | "Use of this key is highly discouraged, as filesystem event monitoring is highly race-prone" |
| `mise bootstrap` launchd agents know `keep_alive`, `queue_directories`, `run_at_load`, `start_calendar_interval` (no `watch_paths`) | **MEASURED (strings of `~/.local/bin/mise`; control: known keys `start_interval`/`working_directory` hit 2/5×)** | `~/.local/bin/mise` | `keep_alive` ×6, `queue_directories` ×4, `watch_paths` 0 |
| This repo already runs launchd agents via `mise bootstrap`, interval-driven (`start_interval = 60` dag-tick, `300` another) | **SHIPS (repo)** | `mise.toml:1538-1545`, `:1585` | `start_interval = 60` |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `SessionEnd filename:settings.json path:.claude` | query | planner | 1880 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | planner | 29 | 0 |
| `qvzjwk8xpl7tmn3rf` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | RATE-LIMITED | 1 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | workflow | 29 | 0 |
| `repo:openai/codex filename:README.md` | must-hit | workflow | 54 | 0 |
| `repo:All-Hands-AI/OpenHands filename:README.md` | must-hit | workflow | 0 | 0 |
| `repo:SWE-agent/SWE-agent filename:README.md` | must-hit | workflow | 12 | 0 |
| `repo:langchain-ai/langgraph filename:README.md` | must-hit | workflow | RATE-LIMITED | 1 |
| `repo:ruvnet/claude-flow filename:README.md` | must-hit | workflow | 0 | 0 |
| `repo:smtg-ai/claude-squad filename:README.md` | must-hit | workflow | 2 | 0 |
| `repo:microsoft/autogen filename:README.md` | must-hit | workflow | 52 | 0 |

Notes: no separate CODE SEARCH NOTES were supplied. The health control was rate-limited, so the
two `0` README rows (OpenHands, claude-flow) **cannot** be read as "code search does not index
it". Both repos redirect (to `OpenHands/OpenHands` and `ruvnet/ruflo`), which is the more
likely cause, but this run did not re-query them. The planner's 1,880-hit
`SessionEnd … settings.json` query shows SessionEnd hooks are widely configured. Its hits were
not re-fetched and grepped, so 1,880 is `total_count`, not a confirmed hit count.

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| anthropics/claude-code | event-driven agent orchestration | 0 | `.agent/kb/raw/research-fanout/event-driven-self-healing-agent-orchestration-2026-10-03/deps/anthropics--claude-code/1/manifest.json` |
| anthropics/claude-code | codex | 0 | `…/deps/anthropics--claude-code/2/manifest.json` |
| anthropics/claude-code | OpenHands | 0 | `…/deps/anthropics--claude-code/3/manifest.json` |
| anthropics/claude-code | SWE-agent | 0 | `…/deps/anthropics--claude-code/4/manifest.json` |
| anthropics/claude-code | langgraph | 0 | `…/deps/anthropics--claude-code/5/manifest.json` |
| anthropics/claude-code | claude-flow | 0 | `…/deps/anthropics--claude-code/6/manifest.json` |
| anthropics/claude-code | claude-squad | 0 | `…/deps/anthropics--claude-code/7/manifest.json` |
| anthropics/claude-code | autogen | 0 | `…/deps/anthropics--claude-code/8/manifest.json` |
| openai/codex | claude-code | 0 | `…/deps/openai--codex/1/manifest.json` |
| All-Hands-AI/OpenHands | claude-code | 0 | `…/deps/All-Hands-AI--OpenHands/1/manifest.json` |
| SWE-agent/SWE-agent | claude-code | 0 | `…/deps/SWE-agent--SWE-agent/1/manifest.json` |
| langchain-ai/langgraph | claude-code | 0 | `…/deps/langchain-ai--langgraph/1/manifest.json` |
| ruvnet/claude-flow | claude-code | 0 | `.agent/kb/raw/research-fanout/event-driven-self-healing-agent-orchestration-2026-10-03/deps/ruvnet--claude-flow/1/manifest.json` |
| smtg-ai/claude-squad | claude-code | 0 | `…/deps/smtg-ai--claude-squad/1/manifest.json` |
| microsoft/autogen | claude-code | 0 | `…/deps/microsoft--autogen/1/manifest.json` |

(`…` = `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-completion-20261002/.agent/kb/raw/research-fanout/event-driven-self-healing-agent-orchestration-2026-10-03`.)
`rc=0` is the agent's exit code, not per-source success. Inside the manifests, `github-issues`
**errored** (HTTP 422) for OpenHands and claude-flow, and `github-releases` errored for
`openai/codex` (stream CANCEL).

Primary fan-out manifests: `coordinator-agent-auto-restart-context-limit-hook/manifest.json`
(exa ok 10, firecrawl-developer ok 10, last30days ok 1) and
`ai-software-factory-issue-to-pr-agents-self-healing-orchestr/manifest.json` (exa ok 10,
firecrawl-search ok 10, **context7 error "exited 1"**).

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| _(none: the MIRRORS input was empty because the caller supplied no links to mirror)_ | — | — | — | — |

## Conflicts resolved

- **claude-tmux-dog: "No polling, no timers, no filesystem watchers — pure event-driven"
  vs. its own config.** The same README configures `pane_watcher.interval: 30` and
  `stall_timeout: "5m"`. I trusted the config, because it describes what runs. The lifecycle
  events really are hook-pushed, but context detection polls the TUI's `↑ tokens` every 30 s.
- **Triage headline "auto-resume worker sessions on respawn" (Composio AO PR #819) vs. the
  PR record.** The API shows `state=closed, merged=false`. I trusted the PR record: this is
  **not** shipped through that PR. Whether another PR shipped it is a gap.
- **#59806 (respawn silently fails on "request too large") vs. its closure.** A maintainer
  closed it on 2026-05-27 as "Addressed by a merged fix". Newer beats older, so I treat
  respawn-after-overflow as working. That does not refute point 3 of the Answer: per the docs,
  respawn still resumes the full conversation.
- **Read-phase claim "Claude Squad enables event-driven parallel agent execution … deterministic
  session lifecycle management".** The quote it cites, from a third party (the Podiom
  maintainer), says only tmux + worktrees + TUI. I downgraded the claim to that.
- **Read-phase claim "SWE-agent implements … pre-tool-call policy hooks".** The source is an RFC
  issue, so I relabeled it as PROPOSED.
- **Read-phase claim "LangGraph … extended by GNAP".** GNAP is a third-party proposal filed as
  issues against LangGraph and AutoGen. Neither project ships it.
- **Read-phase claim citing #64898 for the hook list.** The issue is a declined feature
  request. I re-sourced the hook list from the vendor docs (`$CC/hooks.md`) and kept #64898
  only as evidence that hook→agent spawn is not planned.
- **agent-os "zero human intervention" vs. its README.** The README is explicitly cron-driven
  and recommends a "supervised pilot" before "turn on … the full cron loop". It is a factory
  pattern, but not an event-driven one.

## Gaps

Mandatory gaps (the sweep is incomplete because of these):
- Code search health control `repo:cli/cli filename:README.md` was RATE-LIMITED (HTTP 403),
  not 0. Every empty code-search result in this run is unarmed.
- langgraph README control was RATE-LIMITED (HTTP 403), not 0.
- `All-Hands-AI/OpenHands` redirects to `OpenHands/OpenHands`, so the issue search 422'd. Re-run
  with `repo=OpenHands/OpenHands`. OpenHands' restart/resume model is **unknown**.
- `ruvnet/claude-flow` redirects to `ruvnet/ruflo`, so the issue search 422'd. Re-run with
  `ruvnet/ruflo`. Only its releases list was read (v3.41–v3.51.1, active as of 2026-10-02);
  its swarm self-healing features are **unknown**.

Unverified empties, named as gaps rather than as "nothing found":
- context7 for the ai-software-factory query: `error` (exited 1).
- github-discussions for `claude-agents-json-state-done-blocked-stop-hook-idle`: empty_unverified, count 0.
- herdr (`ogulcancelik/herdr`): GitHub sources errored, and the rest are empty_unverified.
- devflowinc/uzi, kenn-io/agentsview, kbwo/ccmanager: empty_unverified.
- ruvnet/claude-flow: error plus empty_unverified. The README code search count of 0 is unarmed.
- langchain-ai/langgraph: discussions empty_unverified, and code search rate-limited.
- All-Hands-AI/OpenHands: error plus empty_unverified. The README code search count of 0 is unarmed.
- openai/codex: the releases source errored.
- SWE-agent/SWE-agent: discussions empty_unverified.
- anthropics/claude-code deps 1–8: `github-discussions` was empty_unverified on every run (the
  canary also returned 0). The discussions dimension for claude-code is therefore unverified.
- The code-search health check was rate-limited, so the empty controls are not armed (repeat of
  the mandatory gap).

Other gaps:
- Composio AO: issue #816 is closed and PR #819 was closed unmerged. Whether respawn-resume
  shipped some other way is unknown, and the AO issue search returned 422 (the repo may have
  been renamed or moved).
- Whether `claude --bg` sessions execute a `statusLine` command at all (no TUI attached) is
  **unverified**. That decides whether statusLine can be a context-% producer for a background
  coordinator.
- Whether `mise bootstrap`'s `keep_alive`/`queue_directories` keys map one-to-one onto the
  launchd keys was inferred from binary strings only. Read the mise docs or source before relying on it.
- No source read here describes a **context-window-full** trigger built into any framework.
  Only claude-tmux-dog (TUI scraping at 80%) and this repo's `session.measure` hook address it.
  "No framework handles it natively" is therefore **unverified**: it rests on a bounded corpus
  with unarmed code-search controls.
- The read stage covered 1 batch (haiku). Podiom, myc, Lians, session-peer, gh-aw and Mend
  were not read beyond their announcement or description.

Critic gaps (appended by the reconcile node; each with its next probe):
- Whether `claude --bg` sessions run a `statusLine` command (no TUI) is unverified; it decides
  if statusLine can produce context-percent for a background coordinator. Next: start a
  throwaway `claude --bg` with a statusLine that appends to a file; cross-check
  `statusline.md` and `agent-view.md`.
- mise bootstrap launchd keys (`keep_alive`, `queue_directories`) were inferred only from
  binary strings; their mapping onto launchd `KeepAlive` dict forms and `QueueDirectories`
  was never read from docs or source. Recommendations 1 and 2 depend on it. Next: read the
  mise docs/source for `bootstrap.macos.launchd.agents`, then run `mise bootstrap` with a
  dummy agent and inspect the plist with `plutil -p`.
- Recommendation 1 assumes the coordinator transcript JSONL carries a `usage` block from which
  context percent can be computed, and that FSEvents is usable from Python (watchdog or
  fsevents). Neither was verified, nor compared with the `session.measure` value. Next: tail a
  live coordinator transcript under `~/.claude/projects`, compute percent from the last
  assistant usage, compare, and prototype a watchdog observer.
- The Claude Code Monitor tool, `/loop`, and `claude --bg` event hooks were not checked as
  in-session event sources, and it is unverified whether `Stop`/`StopFailure` fire for a `--bg`
  session that is stuck or full. Next: read `hooks.md`/`agent-view.md` for hook firing in
  `--bg` sessions; test a settings.json Stop hook against a full-context `--bg` session.
- The sweep was incomplete (rate-limited controls; OpenHands and claude-flow issue searches
  422'd after repo renames), so every empty result stays unarmed. Next: re-run with
  `OpenHands/OpenHands` and `ruvnet/ruflo`, wait out the rate limit and re-run the
  `repo:cli/cli` and langgraph controls, and check ruflo swarm self-healing and OpenHands
  resume/restart.
- Never read from a primary source: gh-aw (existence only), Mend, Podiom, postbag, myc, Lians,
  session-peer, Ona self-healing factory, the OpenAI factory (newsletter only), Composio AO.
  Next: read the gh-aw docs (triggers, safe-outputs, CI-failure workflow), the Podiom and
  Composio AO READMEs/source for restart and resume, the OpenAI factory primary post, and
  whether AO respawn-resume shipped through a PR other than #819.
- Non-Claude, non-GitHub frameworks were not searched: Temporal/durable-execution agent
  runners, Erlang-style supervisor trees, Kubernetes operators or systemd watchdogs for agents,
  Codex hooks/`codex queue`/automations, Devin, Cursor background agents, Sweep, Copilot coding
  agent. This is the supervisor-tree and self-optimize half of the question and the Codex lane
  side.
- Self-learning coverage is thin (agent-os cron and one Adaptive post). No primary source was
  read for lessons-learned memory, DSPy/GEPA prompt optimization, Reflexion-style
  retrospectives, Voyager-style skill libraries, or Claude Code auto-memory. "No framework
  handles a full context window natively" rests on a bounded corpus.
- The saved-searches and Retrospect phases for research-sweep-run are absent; the status claim
  rests on a grep, and the one TOML record has no reader. GitHub has no public saved-search
  API, so non-interactive driving is unconfirmed. Next: re-grep at current main HEAD and open
  worktrees; check #1502 and N1 status.
- Vendor-issue claims rely on closure state at one read. #59806 was "addressed by a merged
  fix" but no release confirming it was checked, and the installed Claude Code version versus
  the KB docs mirror was never confirmed. Next: `claude --version`, diff the mirror date against
  the changelog, find the release with the #59806 fix.

## Recommendation (ranked by fit for this repo)

These recommendations are my synthesis. Items 1–3 reuse machinery the repo already owns
(launchd via `mise bootstrap`, `claude agents --json`, `claude --bg`, settings hooks), which
satisfies `use-tool-builtins.md`. The custom code is justified because no shipped native
primitive restarts a wedged or too-full coordinator, and #64898, #87142, #62631 and #38210 are
closed without being built. Those closures were stale-bot auto-closes, not vendor rulings
(see Verification), so re-check for a native trigger before building more than the minimal
supervisor, and expect Stop/StopFailure/SessionEnd settings hooks to be a usable push source
inside `--bg` sessions (untested).

1. **A launchd `KeepAlive` coordinator supervisor that runs outside Claude** (best fit). One
   always-on python process (`dotfiles-setup coordinator-supervisor`, declared under
   `[bootstrap.macos.launchd.agents]` with `keep_alive` instead of `start_interval`). Inside
   it, use **FSEvents** (not launchd `WatchPaths`, which the man page calls race-prone) on:
   (a) the coordinator's transcript JSONL, reading the last assistant `usage` to compute
   context % without the session's cooperation; and (b) `.agent/state/coordinator-handoff/`.
   On threshold, a `state=failed`, or a `blocked` state with `Prompt is too long`, it runs the
   existing handoff (`claude --bg` successor from the main checkout, handoff inbox as the
   brief). This turns the side agent's warning into the fix. It survives session
   end/`/clear`/overnight, has no 7-day expiry, and launchd restarts the supervisor itself if
   it dies. **Carry the dag-tick lesson into it**: the supervisor may only *start* successors
   and must never `claude stop` a session it did not launch.
2. **Make the in-session producer reload-proof.** Move the threshold check, or a thin copy of
   it, from the function-hook plugin into a `settings.json` command hook (`Stop`,
   `StopFailure`, `PostCompact`, `SessionStart`) that hot-reloads (`settings.md:584`). Have it
   write an event file into a `queue_directories` inbox that a launchd job consumes. This
   closes the "coordinator started 45 s before the hook landed" hole. It still cannot fire
   once the session cannot take a turn, which is why item 1 is primary.
3. **Use `claude agents --json --all` as the supervisor's state source**, not the files under
   `~/.claude/jobs/` (`agent-view.md:130`). Treat the `Notification` `agent_completed` hook as
   best-effort only, because it fires only while agent view is open.
4. **Adopt claude-tmux-dog's recovery ladder as a pattern, not as a dependency** (11 stars,
   tmux-bound): nudge, then compact, then a "death-loop rebuild" after N fast Stops, then
   suspend on fatal errors (auth/billing). Map it onto the supervisor's states. A coordinator
   that ends turns quickly 8 times in 2 minutes is poisoned and needs a fresh successor, not a
   respawn.
5. **For the factory side, keep the triggers event-native in GitHub.** The repo already uses
   auto-merge, `workflow_run` and Renovate. Evaluate `github/gh-aw` for "CI failed → agent
   opens a fix PR" before building anything (third-party evidence only so far). agent-os is
   worth reading for its stuck-merge self-heal (attempt counter reset plus alert), not as a
   runtime.
6. **Self-learning: land #1502's Retrospect phase as a proposal-file writer**, matching
   agent-os's incident-scanner → `autonomous-fix` issue loop and this repo's `command-audit`.
   Never let the loop edit prompts or config directly.
7. **Re-run the incomplete parts**: OpenHands as `OpenHands/OpenHands`, claude-flow as
   `ruvnet/ruflo`, and the rate-limited code-search controls. Build the **Saved-searches
   phase** (#1502, which needs N1 `watches.toml`) so the searches here become re-runnable
   watches. Add queries for `"QueueDirectories" claude`, `"claude agents --json"`, and
   `"KeepAlive" "claude --bg"`.

## Verification

Five load-bearing claims went through a refute pass (5 refuters), a critic and an adjudicator.
All three steps ran (FAILED STAGES: none). Verdict key: confirmed, UPHELD misleading
(qualified in place), UPHELD refuted (none occurred), overturned by the adjudicator, unverified.

| # | Claim | Verdict | Evidence and how the text changed |
|---|---|---|---|
| 1 | Claude Code will not ship an in-session restart trigger; #64898, #87142, #62631, #38210 all closed not_planned | **UPHELD misleading** (adjudicated) | State and `state_reason=not_planned` hold for all four. Each was closed by `github-actions[bot]` with the `stale` label, so these are inactivity auto-closes, not maintainer decisions. Two closure dates in the draft were wrong: #64898 closed 2026-08-13 (not 2026-09-29), #38210 closed 2026-05-05 (not 2026-06-24). #87142's body says v2.1.199 already shipped a subagent API-error notification. Answer point 2, the evidence rows and the Recommendation intro were rewritten: "declined"/"the vendor will not ship" struck. Control: all four returned the fields; the freshly invented token returned 0 in the docs grep. |
| 2 | Supervisor restarts an exited process; respawn resumes the conversation, so a full coordinator returns full; native covers death, not context exhaustion | **UPHELD misleading** (adjudicated) | `agent-view.md:695` and `:749` quotes are accurate; `:749` adds that a backgrounded-then-killed session is marked stopped. "Comes back still full" is an inference. `context-window.md:1618-1632` documents native auto-compaction. The real gap is a wedged/blocked/too-full coordinator (not "exited unexpectedly") and compaction thrashing. Answer point 3 rewritten. Control: present term 49 hits, fresh absent token 0. |
| 3 | The only push signal (`agent_completed`/`agent_needs_input`) fires only while agent view is open; read state by polling `claude agents --json --all` | **UPHELD misleading** (adjudicated) | Quotes accurate (`hooks-guide.md:193-194`, `hooks.md:2272-2273`, `agent-view.md:720`, `:731`). "Only" overreaches: in-session `Stop`/`StopFailure`/`SessionEnd` settings hooks can push signals outward and nothing in the docs ties them to agent view; the report's own Recommendation 2 relies on that. Not tested live in a `--bg` session. Also omitted: `claude logs`/`attach` pull reads, the draft-PR event, version gating (v2.1.198+). Answer point 3 qualified. |
| 4 | settings.json hooks hot-reload; the plugin function hook loads only at session start or `/reload-plugins`; a settings-hook producer would have reached the coordinator that started 45 s early | **Overturned by the adjudicator** (confirmed) | `settings.md:584` and `plugins-reference.md:407` say opposite things for the two mechanisms, as claimed. The third clause is a hedged inference ("would therefore"), and the report states its limit. No live settings-hook test was run. No text change. |
| 5 | research-sweep-run has a mandatory issues/PRs/discussions phase (Dependencies) but no saved-searches phase; #1502 is OPEN and blocked on unbuilt N1 `watches.toml`; the only saved-search record is a TOML nothing reads | **Overturned by the adjudicator** (confirmed) | `research-sweep-run.js:7` marks Dependencies MANDATORY; no saved-search/watches reference found (the three grep hits are Mirror-stage); #1502 OPEN. The report already discloses per-repo scope and the draft `[[watch]]` schema. The refuter's extra point (the Retrospect half of #1502 is not blocked on N1 but is also absent) is noted here for completeness. |

Not re-verified by this pass (status **unverified**): the claude-tmux-dog, agent-os, Podiom,
postbag, gh-aw, Mend and Composio AO rows (README or third-party descriptions, labelled as such
in the Evidence table); the 1,880 `total_count`; the mise binary-strings measurement; the 65
subagents / 11.6 M token field figure (inherited, not re-derived).

**How the conclusion changes.** The headline holds: the restart trigger must live outside the
session it restarts, and the research-sweep-run saved-searches phase is still missing. Three
supports are weaker. (a) The justification for custom code is no longer "the vendor refused":
the requests lapsed under a stale bot and a partial fix shipped, so a native trigger may still
arrive and the supervisor should stay minimal. (b) Native handling is better than stated:
auto-compaction exists, so the gap is a wedged or blocked coordinator, not a merely full one.
(c) "Only agent view gets push signals" is too strong: settings `Stop`/`StopFailure`/
`SessionEnd` hooks are a plausible event-driven producer for `--bg` sessions, which supports
Recommendation 2 but must be tested before it is relied on.

## Provenance

Full ROUTING (every node that ran, including this reconcile node).

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| deps:openai/codex | general-purpose | sonnet | low |
| deps:All-Hands-AI/OpenHands | general-purpose | sonnet | low |
| deps:SWE-agent/SWE-agent | general-purpose | sonnet | low |
| deps:langchain-ai/langgraph | general-purpose | sonnet | low |
| deps:ruvnet/claude-flow | general-purpose | sonnet | low |
| deps:smtg-ai/claude-squad | general-purpose | sonnet | low |
| deps:microsoft/autogen | general-purpose | sonnet | low |
| triage | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

The synthesize node also ran its own control-armed probes. It read issue state for 15
claude-code issues through `gh api` (control: issue 999999999 → rc=1). It checked Composio PR
#819 `merged=false`. It read the READMEs of claude-tmux-dog, agent-os and AO, and the Podiom
and postbag discussions through GraphQL. It confirmed `github/gh-aw` exists (control: a bogus
repo returned 404). It grepped the KB offline Claude Code docs, `man launchd.plist`, and the
strings in the mise binary.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — hook/agent-view/respawn docs (KB mirror); issues #64898 #87142 #62631 #38210 #59806 #88160 #86716 #84323 #75438 #61523 #79127
- [openai/codex](https://github.com/openai/codex) — discussions postbag #44109, session-peer #50547, myc #45725, Lians #39282; issue #44855 (monitor)
- [smtg-ai/claude-squad](https://github.com/smtg-ai/claude-squad) — discussion #316 (Podiom), RFC PR #283 (`cs serve`)
- [SnowAIGirl/claude-tmux-dog](https://github.com/SnowAIGirl/claude-tmux-dog) — external hook-fed watchdog, recovery ladder, launchd autostart
- [ComposioHQ/agent-orchestrator](https://github.com/ComposioHQ/agent-orchestrator) — PR #819 (closed unmerged), issue #816
- [kai-linux/agent-os](https://github.com/kai-linux/agent-os) — cron-driven issue→PR factory; commit bc58277 stuck-merge self-heal
- [github/gh-aw](https://github.com/github/gh-aw) — GitHub Agentic Workflows (existence only)
- [omkesti/Mend](https://github.com/omkesti/Mend) — CI-healing agent (description only)
- [SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) — RFC #1526
- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) — GNAP issue #7174
- [microsoft/autogen](https://github.com/microsoft/autogen) — discussion #8135, GNAP issue #7398
- [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) — redirect to OpenHands/OpenHands; search failed (gap)
- [ruvnet/claude-flow](https://github.com/ruvnet/claude-flow) — redirect to ruvnet/ruflo; releases only
- [Podiom/Podiom](https://github.com/Podiom/Podiom) — named via discussion #316 (not read)
- [parasxos/postbag](https://github.com/parasxos/postbag) — named via discussion #44109 (not read)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #1502, `research-sweep-run.js`, `docs/research/saved-searches/orchestration-2026-10-02.toml`, `mise.toml` launchd agents
