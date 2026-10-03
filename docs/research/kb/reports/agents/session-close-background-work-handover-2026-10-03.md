# Closing a session without losing its background work, and handing that work to a successor

Research synthesis, 2026-10-03. Question: how should a multi-session Claude Code setup (a coordinator, a
watcher or a fan-out lane) close a session without losing its background work, and can a successor
session take that work over? "Background work" here means four things: harness background Bash
(ship/land/push), in-process Agent subagents, Workflow runs, and detached codex lanes
(`mise run sdlc-team`).

Host: Claude Code 2.1.288 (`~/.claude/jobs/*/state.json` `cliVersion`). The offline vendor docs
(`$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`) have a
changelog that stops at **2.1.273**. Release notes from 2.1.274 to 2.1.288 come from the fan-out's
releases raw file (`.agent/kb/raw/research-fanout/claude-stop-background-subagent/github-releases.raw`).

## Answer

**The sweep finished: no mandatory gaps, no failed reads, and every required source ran. Several
questions are still open, though (see Gaps). The most important one: does a background Agent subagent
that is running when a user runs `claude stop` die, or is it carried to the session's next process? No
source settles it.**

1. **Claude Code has no native cross-PROCESS way to move background work to a different session.**
   (Corrected in Verification: the original wording, "no way ... to a different session", was refuted.
   `/branch` moves in-flight background subagents and background Bash into a NEW session id inside the
   same process, `$CC/sessions.md:183-190`. It does not help a separately launched successor process.)
   Across processes it only carries work forward within the same session, from one process to the
   next. That happens in three cases:
   - You background a session with `←` or `/background`. Its "running background shell commands,
     backgrounded subagents, dynamic workflows, scheduled tasks ... carry over" (`$CC/agent-view.md:409`).
   - The supervisor stops, restarts or updates the session's process. Shells and workflows have been
     handed over since v2.1.196. Background subagents have been handed over since v2.1.198, and
     `CLAUDE_CODE_DISABLE_BG_EXIT_HANDOFF=1` turns this off (`$CC/env-vars.md:240`,
     `$CC/agent-view.md:752`).
   - `claude respawn` or a resume of that same session id.

   Deleting the session (`claude rm`) "stops everything it carried over" (`$CC/agent-view.md:752`).
   `/branch` (in-process, new session id; original left on disk) is a fourth native carry-over, but it
   needs the running process, so a coordinator that stops cannot use it to feed a successor process.
   `/fork` creates an independent session and does not carry background work.
   A successor launched as a separate process is a different session, so for it the only native routes are:
   - (a) read the old session's files (`subagents/agent-<id>.jsonl`, logs, settlement files);
   - (b) `SendMessage` the old **session**. It cannot message the old session's subagents:
     `ListAgents` lists only "agents running inside the current session"
     (`$CC/cross-session-messaging.md:123`), and a reply to a subagent-written message "reaches that
     session's main conversation, not the subagent" (`:200`);
   - (c) subscribe with `notify_when_idle` to hear when the old session goes idle or exits. This is
     one-shot, lasts at most 12 h, and only a main conversation can subscribe (`:92-117`);
   - (d) resume the old session itself, which brings its carried work back into **that** session.

2. **Claude Code drains background work natively in only one case: headless `-p`.** There it waits
   for background subagents and workflows, but after 10 idle minutes
   (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`) it "stops whatever is still running and drops its partial
   result" (`$CC/headless.md:71`). Issue #98170 reports that this kills subagents that are still
   working, while the run reports success with exit 0.

   For interactive and `--bg` sessions, there is no hook that can hold a session open until its work
   drains:
   - `SessionEnd` has no decision control and a 1.5 s default budget (`$CC/hooks.md:3344-3349`).
   - `SubagentStop` does not fire when a subagent is killed by `TaskStop` or by "Exit and stop tasks"
     (#92716, open).
   - Exiting interactively shows a "Background work is running" dialog (`$CC/agent-view.md:380`). That
     dialog is a prompt for a human, not a drain.

3. **This repo's retire gate cannot see two of the four kinds of background work.**
   - The census records only shell runs that match `HEAVY_COMMAND_RE`
     (`python/src/dotfiles_setup/coordinator_handoff.py:115-123`). That pattern has **no `sdlc-team`**
     alternative (0 matches in the file; control: `bounded-wait` has 4), so detached codex lanes are
     recorded only if the handoff prose mentions them.
   - The independent `inFlight.tasks` block (`:1056-1083`) reads harness `state.json`. The original
     claim that no agent kind was observed was REFUTED in verification: a scan of all 54 job records
     found `local_agent` in `4daaf7e1` (tasks 1) and `97ffeddb` (tasks 4, with `local_workflow` and
     `local_bash`). `_in_flight_blocks` (`:1066-1083`) blocks on any `inFlight.tasks != 0` regardless
     of kind unless `--accept-inflight` is passed, so a running background subagent DOES block retire.
   - What stays true: the census regex lacks `sdlc-team`, and a detached codex supervisor is a separate
     surface from harness `inFlight`, so codex lanes are still invisible to both. (Caveat: both
     `local_agent` records were written near the report's own time, so they are probably the live
     review agents; this explains the earlier miss.)

4. **Recommendation, in short:** make **B** the primary mechanism, add a narrow **A**, run a two-arm
   test of **C** before adopting it, and reject **D** (see Recommendation).
   - B: long work runs only on runners that survive the coordinator, meaning `claude --bg` lane
     sessions or detached processes that write settlement files.
   - A: retire stays blocked until each old-session subagent has settled or its report has been
     recovered verbatim, with a deadline. The census also gains `sdlc-team`.

## Evidence

| Claim | URL or file:line | Quote |
|---|---|---|
| A process stop or restart hands shells, workflows and background subagents to the same session's next process | `$CC/agent-view.md:752` | "When a session's process stops or restarts, the background shell commands, dynamic workflows, and background subagents Claude started in it carry over to its next process; running monitors and shell commands a subagent started stop with the process. Deleting the session stops everything it carried over." |
| Background subagents joined that handover in v2.1.198, and it is scoped to supervisor stop, restart or update | `$CC/env-vars.md:240` | "stop a background session's running background shell commands, dynamic workflows, and, as of v2.1.198, background subagents when the supervisor stops, restarts, or updates that session's process, instead of handing them to the session's next process" |
| Backgrounding moves in-flight work into a fresh process of the same conversation | `$CC/agent-view.md:409` | "Backgrounding starts a fresh process that resumes from the saved conversation, and in-flight work moves to it ... A subagent moves together with everything it started" |
| Workflow subagents restart from the beginning when a session is backgrounded | `$CC/agent-view.md:411` | "subagents that were still running start over from the beginning, so the tokens they used so far are spent again" |
| `claude stop` racing a respawn was fixed so that the stop holds | `$CC/changelog.md:2163` (v2.1.199) | "Fixed `claude stop` being silently undone when it raced a background-agent respawn — the respawn now honors the stop" |
| `/clear` keeps background agent and bash tasks | `$CC/changelog.md:4702` | "Fixed `/clear` killing background agent/bash tasks — only foreground tasks are now cleared" |
| A fresh conversation clears session crons, and resume restores `CronCreate` tasks but never background Bash or monitors | `$CC/scheduled-tasks.md:208` | "Starting a fresh conversation clears all session-scoped tasks. When you resume ... Claude Code restores the tasks scheduled with `CronCreate` ... Background Bash and monitor tasks are never restored on resume." |
| `-p` waits on background subagents and workflows, then kills them after a 10-minute idle ceiling | `$CC/headless.md:71` | "By default the wait ends after 10 minutes of continuous idle waiting ... Claude Code stops whatever is still running and drops its partial result." |
| `SessionEnd` cannot block termination | `$CC/hooks.md:3344` | "SessionEnd hooks have no decision control. They can't block session termination but can perform cleanup tasks." |
| `ListAgents` reaches only the current session's subagents | `$CC/cross-session-messaging.md:123` | "Subagents: agents running inside the current session." |
| A reply to a subagent's cross-session message goes to that session's main conversation | `$CC/cross-session-messaging.md:200` | "A reply to it reaches that session's main conversation, not the subagent." |
| `notify_when_idle` is a one-shot idle-or-exit notice that only a main conversation can request | `$CC/cross-session-messaging.md:92,117` | "send back one notice when that session next goes idle or exits" / "Only the Claude in your main conversation can subscribe" |
| A subagent resumes by agent ID; name checks reset on `/clear`; transcripts persist per session | `$CC/sub-agents.md:1072,1090,1094-1100` | "Claude uses the `SendMessage` tool with the agent's ID or name as the `to` field to resume it" / "resets on `/clear`" / "You can resume a subagent after restarting Claude Code by resuming the same session." |
| A subagent the user stopped is not auto-resumed | `$CC/sub-agents.md:1080` | "A subagent you stopped yourself, with `x` in `/tasks` or an SDK `stop_task` request, doesn't auto-resume." |
| (Release note, not in offline docs) The VS Code Stop button now ends only the current turn | releases raw, v2.1.286 | "[VSCode] Changed Stop and Escape to end only the current turn; background agents keep running" |
| (Release note) The background-command time limit now applies only to unattended sessions | releases raw, v2.1.288 | "Changed the background command time limit to apply only in unattended sessions (`-p`, Agent SDK, CI, cloud)" |
| (Release note) Subagents' background commands no longer have a 1 h cap | releases raw, v2.1.260 | "Removed the one-hour time limit on background commands started by subagents" |
| Headless sessions exit "success" right after dispatching subagents, orphaning the work | https://github.com/anthropics/claude-code/issues/85066 | "the session terminated 6–15 seconds later with \"subtype\": \"success\", \"is_error\": false. No review was ever produced." |
| `-p` kills subagents that are still working at 600 s and reports success | https://github.com/anthropics/claude-code/issues/98170 | "subagents that are actively working ... are killed exactly 600 s after the main thread went quiet ... exit code 0." |
| A subagent cannot hand back its report after its parent exits | https://github.com/anthropics/claude-code/issues/98241 | "{\"success\":false,\"message\":\"Nothing was sent: the agent that spawned you is no longer running.\"}" |
| A second handback after resume is rejected, and the result is lost | https://github.com/anthropics/claude-code/issues/96849 | "your report was already delivered (SubagentHandback delivers one report). Use SendMessage for anything further, then stop." |
| `SubagentStop` does not fire on `TaskStop` or "Exit and stop tasks" | https://github.com/anthropics/claude-code/issues/92716 | "It does not fire when the parent session kills the subagent with TaskStop, and it does not fire when the session exits through the 'Exit and stop tasks' choice" |
| A subagent's background Bash outlives the subagent | https://github.com/anthropics/claude-code/issues/93889 | "They ran for 45 to 60 minutes after their agents had finished." |
| Only `SendMessage` wakes an idle teammate | https://github.com/anthropics/claude-code/issues/77300 | "never re-invoked by: 1) Monitor tool events ... nor 2) completion notifications of its own background Bash tasks" |
| A background subagent stalls silently, and a `SendMessage` status request goes unanswered | https://github.com/anthropics/claude-code/issues/98846 | "It was 'queued for delivery at its next tool round' but never answered" |
| Desktop sessions with background work stay alive forever, with unconsumed task notifications | https://github.com/anthropics/claude-code/issues/86443 | "transcripts of every affected session end with queue-operation: enqueue entries carrying task-notification payloads that are never consumed" |
| Scheduled Desktop sessions never exit | https://github.com/anthropics/claude-code/issues/72308 | "They accumulate indefinitely — one per scheduled fire" |
| Windows: auto-backgrounded Bash is orphaned at session end | https://github.com/anthropics/claude-code/issues/92583 | "the underlying Windows process is orphaned" |
| `idle_prompt` fires while background work is still running (fixed in 2.1.288 per release notes) | https://github.com/anthropics/claude-code/issues/98373 ; releases raw v2.1.288 | "fires while the session is still waiting on background agents" / "Fixed `idle_prompt` notification hooks firing while background agents are still running" |
| A runaway agent could not be stopped from inside the product | https://github.com/anthropics/claude-code/issues/98708 | "The only thing that stopped it was the user closing the VS Code window" |
| The census pattern covers shell heavy runs only, with no `sdlc-team` | `python/src/dotfiles_setup/coordinator_handoff.py:115-123` | "`ship|land|sync|verify-local|verify-container-latest|bounded-wait|automerge`" (grep `sdlc-team` = 0; control `bounded-wait` = 4) |
| The census records the outermost heavy descendants of the old session's process tree | `coordinator_handoff.py:590-600` | "The outermost heavy descendants of this session, minus the caller's chain." |
| `inFlight` blocks retire, and blocks when unreadable unless `--accept-inflight` is passed | `coordinator_handoff.py:1056-1083,1086-1095` | "Whether harness tasks in flight block retire on their own (item 16)" / "Unknown inFlight also blocks unless accepted." |
| Measured: `inFlight` lists task kinds | `~/.claude/jobs/97ffeddb/state.json` (2.1.288) | `{"tasks": 3, "queued": 0, "kinds": ["local_workflow", "local_bash"], "drainableMonitors": 0}` |
| Measured: `inFlight` can list a session cron | `~/.claude/jobs/7585361b/state.json` (watcher, 2.1.288, `working`) | `{"tasks": 1, ..., "kinds": ["session_cron"]}` |
| Measured: a `fan` entry for a subagent can keep `doneAt=null` after the subagent delivered, so `fan` is not a liveness signal | `~/.claude/jobs/38ae1474/state.json` fan `a0f95423fe3795b17`; last record of `.../38ae1474-.../subagents/agent-a0f95423fe3795b17.jsonl` (15:46:08Z) | `{"success":true,"message":"Report delivered to your caller."}`; the session stopped at 21:01:41Z with `inFlight` absent |
| The successor waits on or adopts each recorded run, and retires only through the gate | `.claude/skills/coordinator-handoff/SKILL.md:61-100` | "settles each recorded run, and retires this session through `mise run coordinator-handoff -- retire` — never a bare `claude stop`." |
| A retired coordinator was revived by its own session cron | https://github.com/ray-manaloto/dotfiles/issues/1609 | "`state.json` read `inFlight: {tasks: 0, kinds: []}` while the cron was live" |
| Third-party proposal: a cross-vendor session messaging CLI | https://github.com/openai/codex/discussions/50547 | "Send a message through the destination agent's native inbox or queue." |
| Third-party proposal: letters between sessions using vendor wake-up mechanisms | https://github.com/openai/codex/discussions/44109 | "Delivery uses each vendor's own wake-up mechanism ... without a daemon or polling." |
| Third-party proposal: a job board or operator web app | https://github.com/openai/codex/discussions/49981 | "starts Codex (or Claude Code, or any CLI agent) in web terminals" |
| Third-party proposal: Podiom, a durable-session and scheduler layer | https://github.com/smtg-ai/claude-squad/discussions/316 | "an open-source Go orchestration layer for local Claude Code and Codex CLI agents" |
| Feature request: a native peer address for Codex↔Claude | https://github.com/openai/codex/issues/48803 | "copy one session-specific `Peer address: uds:…`, and give it to Claude Code" |

These three kinds of claim are kept separate on purpose:

- **What Anthropic ships and documents:** the `$CC` rows and the release notes.
- **What users report as defects:** the issue rows. These are third-party observations, not vendor
  statements.
- **What other projects propose:** the codex and claude-squad discussions. These are announcements of
  messaging and operator layers. None of them documents a succession, drain or lease protocol in the
  text that was read.

### Code search

| Query | Role | Source | Count | rc |
|---|---|---|---|---|
| `claude stop background subagent repo:anthropics/claude-code` | query (armed) | planner | 3 | 0 |
| `SessionEnd background task drain repo:anthropics/claude-code` | query (armed) | planner | 1 | 0 |
| `hooks repo:anthropics/claude-code` | must-hit | planner | 164 | 0 |
| `qvzxplorgnak9931 repo:anthropics/claude-code` | known-absent | planner | 0 (control arm, expected 0, discriminates against the 164 above) | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | workflow | 29 | 0 |
| `repo:smtg-ai/claude-squad filename:README.md` | must-hit | workflow | 2 | 0 |
| `repo:ruvnet/ruflo filename:README.md` | must-hit | workflow | 157 | 0 |
| `repo:openai/codex filename:README.md` | must-hit | workflow | 54 | 0 |

No row was rate-limited. The known-absent token above now appears in this tracked file, so it is used
up for any local grep of this repo. Invent a fresh one next time.

- Note: anthropics/claude-code has discussions disabled (repos API), so github-discussions cannot be
  searched there. This is not a gap.

### Dependency-repo fan-out

| Repo | Query | Required sources failed | Manifest |
|---|---|---|---|
| anthropics/claude-code | claude stop background subagent | none | `.agent/kb/raw/research-fanout/research--kb--reports--agents--session-close-background-work-handover-2026-10-03/deps/anthropics--claude-code/1/manifest.json` |
| anthropics/claude-code | claude-squad | none (hits are off-topic, e.g. #78063, #97515) | `.../deps/anthropics--claude-code/2/manifest.json` |
| anthropics/claude-code | ruflo | none (hits are off-topic) | `.../deps/anthropics--claude-code/3/manifest.json` |
| anthropics/claude-code | codex | none (hits are off-topic, e.g. #99266) | `.../deps/anthropics--claude-code/4/manifest.json` |
| smtg-ai/claude-squad | claude-code | none | `.../deps/smtg-ai--claude-squad/1/manifest.json` |
| ruvnet/ruflo | claude-code | none | `.../deps/ruvnet--ruflo/1/manifest.json` |
| openai/codex | claude-code | none (github-releases `empty_verified`, 0) | `.../deps/openai--codex/1/manifest.json` |

There were two topic manifests as well:
- `.agent/kb/raw/research-fanout/claude-stop-background-subagent/manifest.json`: issues ok 10,
  releases ok 10, discussions `empty_unverified`.
- `.agent/kb/raw/research-fanout/background-tasks-session-exit-drain/manifest.json`: issues ok 10,
  releases ok 3, discussions `empty_unverified`.

### Offline mirrors

| Link | Mirror file | rc | Bytes | Failure |
|---|---|---|---|---|
| _(no input rows: MIRRORS was empty, so no links were provided to mirror)_ | | | | |

## Conflicts resolved

1. **"Retire `inFlight` is blind to crons" (#1609) against a measured `session_cron` kind.**
   - #1609 saw `inFlight: {tasks: 0, kinds: []}` on 30d222ef while a cron was live.
   - On the same CLI (2.1.288), the watcher 7585361b shows `kinds: ["session_cron"]`, tasks 1.
   - Both are first-hand measurements, so I trusted both. The conclusion: `inFlight` **sometimes**
     counts session crons. It is not structurally blind; it is unreliable. Possibly a cron only counts
     while it is firing or queued, but that is unverified.
   - The fix #1609 rules on, `CronDelete` before idle enforced by a Stop hook, is still needed. It
     should not depend on `inFlight` seeing crons.
2. **"Carry over to the next process" (`$CC/agent-view.md:752`) against "Background Bash and monitor
   tasks are never restored on resume" (`$CC/scheduled-tasks.md:208`).**
   - Both are vendor docs from the same corpus. I read them as describing different paths: the
     supervisor handing a process over (stop, restart, update of a `--bg` session) versus a
     `claude --resume` that starts a new process.
   - I trusted both within their scope. The result: whether a **user** `claude stop` followed by a
     later resume restores a subagent is not settled by either.
3. **"A running Agent subagent dies on `claude stop`" versus "it is carried over".**
   - Vendor docs (v2.1.198 env-var row) say background subagents are handed over when "the supervisor
     stops ... that session's process".
   - Issue #98241 (a user report) shows a background subagent still running after its parent exited,
     but unable to deliver its result.
   - I trusted the docs for "handed to the same session", and the issue for "a successor cannot receive
     it". Neither shows a successor receiving the report, which is the part this question depends on.
4. **Dates:** the offline changelog ends at 2.1.273. The release notes from 2.1.274 to 2.1.288 are
   newer, so where they changed behaviour (v2.1.286 Stop button, v2.1.288 time limit, v2.1.288
   `idle_prompt` fix) I trusted them over the older text.
5. **The claim that in-process subagent reports "survive" at `subagents/<agentId>.jsonl`.**
   - The input claim quotes `docs/agent-team.md` with an `agent-{agentId}.jsonl` filename.
   - Vendor docs (`$CC/sub-agents.md:1094`) confirm `agent-{agentId}.jsonl`, and so does the measured
     38ae1474 path. The task's `subagents/<agentId>.jsonl` spelling is missing the `agent-` prefix.
   - A file glob for `<agentId>.jsonl` would match nothing, so recovery code must use `agent-<id>.jsonl`.

## Gaps

- **G1 (central and unanswered):** does a **running** background Agent subagent survive a
  user-initiated `claude stop` of a `--bg` session, and if so, where does its report land?
  - The docs cover supervisor stop, restart and update, but are ambiguous about user stop.
  - The one local datum (38ae1474) cannot answer it: that subagent delivered before the session
    stopped.
  - #92716 and #98170 are only indirect evidence.
  - A live two-arm test is needed: spawn a long background subagent, `claude stop`, then check
    whether the `agent-<id>.jsonl` mtime keeps advancing. Control: the same test without stopping.
- **G2 (CLOSED by verification):** `inFlight.kinds` does report `local_agent` (`4daaf7e1`, `97ffeddb`)
  and retire blocks on it. The original "no agent kind in 53 records" was wrong (54 records scanned).
  Residual: no snapshot was taken against a known-plain single background subagent, and
  `97ffeddb`'s `local_agent` is probably the review agents.
- **G3:** does `/clear` deliver the completion notification of a background subagent that is still
  running to the post-clear conversation? Can a `--bg` session be made to `/clear` itself with no human
  (for example a mod queueing the command; #1592 shows the session-start mod queues
  `/reload-skills`)? Both are unverified.
- **G4:** discussions for the `background-tasks-session-exit-drain` topic: `empty_unverified`
  (query `claude-code`, count 0). This is a gap, not "nothing found".
- **G5:** discussions for the `claude-stop-background-subagent` topic: `empty_unverified` (count 0).
  Because anthropics/claude-code has discussions disabled, this gap is likely structural, but the
  control did not prove that.
- **G6:** discussions for anthropics--claude-code/1, /2, /3 and /4: `empty_unverified`, count 0 each.
- **G7:** of the code-search hits, only 1 came back for the `SessionEnd ... drain` query, and the 3
  hits for `claude stop background subagent` were not examined. Neither result is verified as
  exhaustive.
- **G8:** the fan-out had no manifest for Anthropic docs pages on `claude stop`, `--bg`,
  `SendMessage`, `SubagentStop` or `SessionEnd`. This synthesis partly filled that from the offline
  `$CC` corpus. That corpus lags the installed CLI (changelog through 2.1.273, installed 2.1.288), so
  any `$CC` statement may be stale.
- **G9:** no manifest covers a succession, lease or drain workflow in claude-squad or ruflo, so
  anything about them is unverified. The text read from the third-party messaging projects (Podiom,
  session-peer, postbag, Agent 007) shows **no** proven succession or lease protocol. That only
  covers what was read; their source code was not read.
- **G10:** what `claude rm` does to session crons is undocumented (#1609, citing
  `tools-reference.md:25-27`).
- No MIRROR GAP, CODE SEARCH GAP or MANDATORY GAP rows were provided, so none are listed.

### Critic gaps (appended by reconcile)

- **C1 (= G1):** whether a RUNNING background Agent subagent survives a user `claude stop`, and where
  its report lands. Only indirect evidence (#92716, #98170, #98241); the one local datum (`38ae1474`)
  had already delivered. Next probe: live two-arm test (spawn a long background subagent in a `--bg`
  session, `claude stop` it, watch `agent-<id>.jsonl` mtime and the parent transcript; control without
  stop; then `claude respawn`/resume and see whether the report is delivered).
- **C2:** the offline vendor docs (`$CC`) stop at changelog 2.1.273 while the host is 2.1.288. Key
  semantic claims (`agent-view.md:752`, `env-vars.md:240`, `cross-session-messaging.md`, `hooks.md`
  SessionEnd/SubagentStop) were never re-read from the live docs or CLI; the 2.1.274-288 notes come from
  a raw fan-out file, not the primary releases. Next probe: fetch code.claude.com docs live,
  `gh api repos/anthropics/claude-code/releases` for 2.1.274-2.1.288, diff against `$CC`, and run
  `claude stop --help` / `claude --help` on 2.1.288.
- **C3:** issue status (open/closed/fixed-in-version) and maintainer responses for #98170, #98241,
  #96849, #92716, #85066, #86443 were not confirmed; "fixed in 2.1.288" rests on release notes only.
  Next probe: `gh issue view <n> --comments --json state,closedAt,comments,timelineItems` for each,
  check linked PRs, re-test on 2.1.288.
- **C4:** no proven succession, drain or lease workflow from other orchestrators was examined.
  claude-squad, ruflo, Podiom, session-peer and postbag were read only as announcement text; sources
  were not read; generic orchestrators (Temporal-style leases, leader election analogues, aider,
  OpenHands, crewAI, LangGraph checkpoint resume, Conductor, Claude Agent SDK session resume) were not
  swept. Next probe: read claude-squad and ruflo source for kill/pause/resume/daemon code, search each
  repo's issues for orphan/handoff/resume/lease/heartbeat, add OpenHands/LangGraph/Temporal docs.
- **C5:** the claim that in-process subagent reports are recoverable only from the old session is
  checked from docs only. Untested: `SendMessage` by agentId from another session,
  `claude --resume <old> --fork-session`, Agent SDK resume/fork, teams/teammates (`TeamCreate`),
  `claude attach`/`claude logs`, `/tasks`, `claude agents`, and SubagentStop/SessionEnd hook payload
  fields (`transcript_path`, `agent_id`) that a hook could use to persist reports. Next probe: try
  each from a second session against a live agentId; inspect real hook payloads; evaluate a
  SubagentStop hook that writes the report to a settlement file (cheap native persistence for option A).
- **C6:** option C (`/clear`) and G3 remain untested. The `inFlight`/retire code path (`:1056-1083`)
  has now been read (see Verification), but its tests were not, and no fixture or live snapshot of a
  plain background subagent exists. Next probe: read the tests, craft a `local_agent` fixture, take a
  real `state.json` while a plain background Agent runs, run a `/clear` arm.
- **C7:** detached codex lane claims (survive `claude stop`, leave settlement files; `sdlc-team`
  returns a supervisor pid) are asserted from prior knowledge and not re-verified; no caller link is
  cited for the sdlc-team detach/settlement contract. Next probe: read the sdlc-team mise task and
  skill, run a detached lane, `claude stop` the dispatcher, confirm rc/settlement files and pid liveness.
- **C8:** discussions were never searched with a verified control (G4-G6), and the proposed saved
  searches were not executed, so their must-hit/known-absent arming and counts are unknown; `gh`
  `search/issues` OR/quoted-term behaviour and PR search (`is:pr`) were not validated. Next probe: run
  each saved search via `gh api` with the must-hit (`SubagentHandback` >= 2) and a fresh absent token;
  add `is:pr` variants and GraphQL `search(type:DISCUSSION)` on repos with discussions enabled.

## Recommendation

| Option | Verdict | Why |
|---|---|---|
| **A** Drain subagents with a deadline, widen the census, block retire until each report is persisted | **Adopt, narrowed** | Only the old session can receive its subagents' reports (`$CC/cross-session-messaging.md:123,200`; #98241). So retire must wait or recover. Do not use the `fan.doneAt` field as the signal: it was measured to stay `null` after delivery. Use the subagent transcripts instead. A subagent counts as settled when its last record is a `SubagentHandback` result or a final assistant message with no tool use; otherwise it counts as live while `agent-<id>.jsonl` mtime advances. On the deadline, recover the last report verbatim into `docs/research/kb/reports/agents/` and block with the agent IDs named. Also add `sdlc-team` (and the supervisor pid the dispatch returns) to the census. |
| **B** Long work only on detached runners that report to the newest coordinator by name | **Adopt as primary** | `claude --bg` lane sessions survive a coordinator `claude stop`. They are reachable by name through `ListAgents`/`SendMessage`, and the successor can `notify_when_idle` on them. Detached shell and codex runners already leave rc and settlement files. One limit: a non-Claude runner cannot `SendMessage`, so "report by name" means file settlement plus the successor reading it, not a push. The newest coordinator is found by name pattern and recency, which the skill already does (`coordinator_handoff.py:696`). In-process Agent subagents stay for short, bounded work only. |
| **C** Same-session `/clear` handoff | **Test before adopting** | Same process, so background agent and bash tasks survive (`$CC/changelog.md:4702`), and session crons are cleared (`$CC/scheduled-tasks.md:208`), which would close the #1609 class. Unverified: notification delivery after the clear (G3), whether an unattended `/clear` is possible, and the fact that `SendMessage` name binding resets on `/clear` (agent IDs still work). It also replaces the existing successor design, which is a larger change. |
| **D** Status quo | **Reject** | The census misses codex lanes (no `sdlc-team`). `inFlight` does count `local_agent` tasks and blocks retire (verified; the earlier "may not count subagents" doubt is struck), but it counts crons inconsistently (Conflict 1), and it cannot tell a delivered subagent from a live one (`fan` entries get no completion marker), so `--accept-inflight` can still kill or strand reports without anyone noticing. |

Run G1 and G3 as live two-arm tests (control: no stop or clear) before writing code for A or C, per
`.claude/rules/real-integration-evidence.md`.

### Proposed tunable, rerunnable GitHub saved searches

Template (use `gh api`, not `gh search issues --repo`, which returns 0 silently here). `$DATE` sets
the window:

```bash
gh api -X GET search/issues -f sort=updated -f per_page=50 \
  -f q="repo:anthropics/claude-code is:issue <TERMS> updated:>=$DATE" \
  --jq '.total_count, (.items[] | [.number, .state, .updated_at, .title] | @tsv)'
```

| Name | TERMS | Tracks |
|---|---|---|
| stop-vs-subagent | `"claude stop" subagent` | G1, whether user stop kills or hands over subagents |
| handback | `SubagentHandback` (must-hit: #96849, #98241) | reports lost after parent exit or resume |
| exit-handoff | `"DISABLE_BG_EXIT_HANDOFF" OR "carry over" background` | changes to the handover semantics |
| subagentstop-gaps | `SubagentStop TaskStop` | #92716-class hook gaps |
| idle-notify | `notify_when_idle` | the cross-session completion notice |
| revive | `"claimed-spare" OR "claude stop" revive OR cron` | the #1609 / #64744 / #82107 class |
| print-drain | `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` | the #98170 headless drain |
| ours | `repo:ray-manaloto/dotfiles coordinator-handoff retire` (swap the repo qualifier) | our own open items |

Scan the release notes:

```bash
gh api repos/anthropics/claude-code/releases --paginate --jq '.[] | .tag_name as $t | .body | split("\n")[] | select(test("claude stop|carry over|carries over|background subagent|SubagentStop|SessionEnd|handoff|respawn|/clear";"i")) | "\($t) \(.)"'
```

Arm every run with a must-hit (`SubagentHandback` ≥ 2) and a freshly invented known-absent token. This
fits as `research-sweep` inputs; building a new tool for it is not proposed here.

## Verification

Five refuters, one critic and one adjudicator ran; no stage failed. Four load-bearing claims were
checked (the adjudicator split the headline claim from the other three).

| Claim | Status | Evidence |
|---|---|---|
| Answer 1: no native way to move background work to a different session; only same-session next-process carry-over | **UPHELD as refuted and misleading** (adjudicator agreed) | `$CC/sessions.md:183-190`: `/branch` prints a new session id, leaves the original "unchanged on disk", switches the running process to write to the new one, and "In-flight background subagents and background Bash commands: Keep running. Their output appears in the new branch you switched into, not in the original session." The cited `agent-view.md:409,752` and `env-vars.md:240` lines are accurate. `/fork` (`agent-view.md:384-394`) is independent and does not carry background work. Omission: the accurate claim is "no native cross-PROCESS handoff to a different session; `/branch` is a native in-process move to a new session id." |
| Answer 3 / G2: `inFlight.kinds` had no agent kind (unarmed), so retire-on-Agent-subagent is unverified and the safe assumption is that it does not block | **UPHELD as refuted and misleading** (adjudicator agreed) | The regex half holds (`sdlc-team` count 0, control `bounded-wait` 4). The kinds half is false: of 54 `~/.claude/jobs/*/state.json`, `4daaf7e1` has `{tasks:1, kinds:[local_agent]}` and `97ffeddb` has `{tasks:4, kinds:[local_workflow, local_bash, local_agent]}`. `_in_flight_blocks` (`coordinator_handoff.py:1066-1083`) blocks on any `tasks != 0` regardless of kind unless `--accept-inflight`. Omission: sdlc-team is a detached codex supervisor, a separate surface from harness `inFlight`. Caveat: both records date from near the report's own time. |
| Answer 2: no hook can hold an interactive or `--bg` session open until work drains; SessionEnd has no decision control; SubagentStop misses TaskStop; only `-p` waits, with a 600 s ceiling | **Confirmed** (refuter flagged misleading; **overturned by the adjudicator**) | `hooks.md:3344-3349`, `headless.md:71`, #92716 re-read and agree. The refuter's Stop-hook point (`background_tasks` payload, `decision:"block"`, 8-block cap, `asyncRewake`) is per-TURN, not close-time, so it cannot hold a closing session until drain. Refinement only: SessionEnd budget is raisable to 60 s but still non-blocking; the `-p` ceiling is configurable (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`, 0 = none). |
| Evidence row 115: a finished subagent's `fan` entry kept `doneAt=null`, so `fan` is not a liveness signal; G1 unanswered | **Confirmed** (refuter flagged refuted and misleading; **overturned by the adjudicator**) | The refuter claimed the schema has no `doneAt` key. The adjudicator found `doneAt` set on finished entries in other jobs (`299c066f` agent, `a2ccbbc5` agent and shell, 31 workflow entries in `97ffeddb`). In `38ae1474` the entry for `a0f95423fe3795b17` has the key absent (not literally null) after delivery at 15:46:08Z. Wording nit only: "absent" is more exact than "null". The shell entry in the same file also lacks a marker. G1 remains undocumented. |
| Other Evidence-table rows (agent-view, env-vars, sub-agents, cross-session-messaging line 123/200, hooks, scheduled-tasks, issue quotes, #1609) | **Unverified in this pass** | Not individually re-probed here. The `cross-session-messaging.md:123,200` rows were independently re-read by a refuter and confirmed (subagents "running inside the current session"; reply reaches the main conversation), which also qualifies as: old subagents remain resumable by resuming the old session (`sub-agents.md:1062`) and their transcripts persist at `subagents/agent-<id>.jsonl`, so the work is not lost, only not messageable from a new session. |

### How the conclusion changes

- The central finding survives in narrower form: a **separately launched successor process** still has
  no native way to adopt another session's background work. The sentence "no way to a different
  session" is struck; `/branch` is a native in-process exception, and option C (`/clear`) is no
  longer the only in-process idea.
- Answer 3 is weaker than first written: the retire gate does block on a running `local_agent`, so the
  subagent half of option A's census concern is largely already covered. What remains uncovered is
  `sdlc-team` codex lanes (census regex plus a separate surface) and the lack of a completion marker
  that distinguishes a delivered subagent from a live one.
- Option A's narrowing still applies, but its stated need shifts from "make the gate see subagents" to
  "make the gate distinguish settled from live, and persist each report before `--accept-inflight`".
  B stays primary; D stays rejected, for the reasons updated in the table above.
- The sweep is not INCOMPLETE on mandatory grounds (no mandatory gaps), but the critic gaps C1-C8
  remain open, the first being G1.

## Provenance

| Node | agentType | Model | Effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| deps:smtg-ai/claude-squad | general-purpose | sonnet | low |
| deps:ruvnet/ruflo | general-purpose | sonnet | low |
| deps:openai/codex | general-purpose | sonnet | low |
| triage | Explore | sonnet | low |
| read:1/2 | Explore | haiku | (default) |
| read:2/2 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): issues on background-work loss,
  `SubagentHandback`, `SubagentStop`; release notes v2.1.274–2.1.288; offline docs mirror (via
  knowledge-base).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline
  `agent-harness-docs` corpus (`$CC`).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `coordinator_handoff.py`, the
  coordinator-handoff skill, issues #1609, #1606, #1592.
- [openai/codex](https://github.com/openai/codex): discussions 50547, 44109, 49981; issue 48803
  (cross-session messaging proposals).
- [smtg-ai/claude-squad](https://github.com/smtg-ai/claude-squad): discussion 316 (Podiom).
- [ruvnet/ruflo](https://github.com/ruvnet/ruflo): issue 145 (hooks lifecycle; no succession
  protocol found in the text read).
- [cli/cli](https://github.com/cli/cli): code-search health probe only.
