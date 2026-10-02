# Fan-out lane completion detection: which signal says a lane is FINISHED, BLOCKED or IDLE

- **Date:** 2026-10-02 (Claude Code 2.1.287 observed by the requester; codex-cli 0.160.0 probed here)
- **Question:** How do multi-agent orchestrators and parallel fan-out tools reliably tell a background
  lane is finished, blocked on a human, or idle at its prompt, and which completion protocol should the
  fan-out skill (`.claude/skills/parallel-work-split/SKILL.md` §6) adopt so its watcher ends only when
  every lane is truly finished and never misses a lane blocked on a permission prompt or a question?
- **Trigger:** lane KB2 finished at 12:13 ("I need nothing from you right now") yet `claude agents`
  listed it `blocked`; a second lane finished at 12:33 and read `state=working, status=idle`.
- **Supersedes:** an earlier draft at this same path (12:55) cited stablyai/orca, priivacy-ai/spec-kitty,
  harshanandak/forge and seemseam/claude_codex_bridge. None of those are in this sweep's inputs (claims,
  triage, manifests or mirrors), so their claims are **unverified here** and were not carried forward.

## Answer

**The sweep is INCOMPLETE.** The verification pass (see Verification) downgraded the headline: the
documented `state == done` was wrongly demoted on a misattributed issue, and the recommended protocol is
a design synthesis, untested. Two mandatory items did not run: (1) the dependency re-run for
`smtg-ai/claude-squad` against `asheshgoplani/agent-deck` (and a probe run here refutes the premise
behind it; see Conflicts), and (2) the README control `repo:BloopAI/vibe-kanban filename:README.md`,
which was **RATE-LIMITED** (HTTP 403), not 0. No source code was read for claude-squad, crystal, uzi or
agentsview, and only one detector PR was read for ccmanager. Every statement below about those tools is
limited to issue and PR metadata.

**No single Claude Code field reliably says "finished".**

1. **`state` is the documented completion signal; whether it misreads today is UNCONFIRMED.** The docs say
   a finished turn reads `done`, never `blocked` (`links/1.md:572`, `:575`), and name
   `claude agents --json --all` as the supported read. The only evidence against it on the supported
   surface is the requester's uncaptured note that `claude agents` listed KB2 as `blocked` on 2.1.287;
   that may be the human display rather than `--json` `state`. **Struck:** the earlier claim that open issue
   #87882 shows finished sessions reading `blocked` through this surface. That issue (filed against
   2.1.233, 0 comments) is about `~/.claude/jobs/<id>/state.json`, which the docs call "not a stable
   interface"; in it `claude agents --json` was the accurate source and its stated workaround is to read
   `state` from `agents --json`. Open issue #64036 is a third-party account that `state` is a classifier
   verdict that can lag real activity. "`state` alone cannot end the watcher" is a prudent design
   inference, not a documented or confirmed fact.
2. **`working` + `idle` is documented, not a bug.** `working` covers "between steps of work it drives on
   its own, such as a `/loop` iteration or a wait on CI". The Stop hook's `background_tasks` and
   `session_crons` exist to tell "done" apart from "paused waiting for background work". So
   `working/idle` means "maybe waiting on its own work", never "done".
3. **`status == "waiting"` with `waitingFor` is the only signal that comes from a real open dialog.**
   It is present only while the process is alive and a prompt is open (permission prompt, input needed,
   sandbox request, worker request, dialog open). It is the right trigger for "blocked on a human, act
   now". It still cannot be the whole blocked detector, because:
   - a lane that asks its question **in plain prose** ends its turn, and #85192 (v2.1.220, confirmed by
     the maintainer and reproduced on 2.1.232) reports such a session as `idle` with no waiting marker.
     Qualification: a question asked through the question tool DOES surface as `status: waiting`,
     `waitingFor: input needed`, so requiring the question tool is a native alternative to a verdict
     file; the docs (`:571`) also list "a question it asked" under `state: blocked`;
   - `status` and `waitingFor` vanish once the supervisor stops an idle process, about an hour after the
     session goes unattached.
4. **Push signals are lossy or scoped and cannot be the only completion signal:**
   - Notification `agent_completed` fires only while agent view is open in a terminal.
   - `idle_prompt` is a 60-second typing timer.
   - `SendMessage notify_when_idle` is one-shot, turn-finished rather than task-finished, expires after
     12 hours, works only from the main conversation, and is degraded by `hold` or `refuse`.
   - Cross-session messages are deduplicated and capped at 50.
   - #79570, #20754 and #92095 document lost or unboundedly delayed completion wakes.
5. **What other tools do:**

   | Tool | Evidence level | Approach and its failure mode |
   |---|---|---|
   | ccmanager | **ships** (merged PR #322) | Screen-scrapes the PTY for prompt markers. That PR exists because a new prompt shape was read as `idle` while blocked. |
   | herdr | **ships** (fixed bug #1281) | Reads the terminal title for Codex. It reported `idle` while Codex was visibly working. |
   | vibe-kanban | **third-party** account of its source, in open issue #2495 | Keys on the stream-json `result` message plus an explicit executor exit signal. Its Claude executor never signals, so sessions stay "running" forever. |
   | agent-deck | **ships** socket delivery (PR #2100) | Sends to Claude targets over Claude Code's messaging socket. Its staged Codex status evidence (discussion #1794) is only a **proposal**. |

   The common lesson: scraping the screen or title is fragile (shown only by single bug reports; no
   source code was read). That an explicit completion message is robust is a design inference: no
   examined tool ships a lane-written sentinel and shows it working.
6. **Codex is the easy case.** `codex exec` (0.160.0, probed here) runs to completion. The process exit
   is the completion signal, `-o/--output-last-message <FILE>` writes the final message, and `--json`
   streams JSONL events. The Codex hook-parity work (#21753) is still OPEN.

**Recommended protocol (detailed under Recommendation; PROPOSED HERE, UNTESTED).** Make the documented
`state == done` from a **level-triggered poll of `claude agents --json --all`** the primary signal, and use
a **lane-written verdict file** (the docs sanction a self-written file for progress, not specifically for
completion) plus a branch commit as corroboration and as the only carrier of a lane's own question:

- **FINISHED** is `state == done`, no live dialog, with a `done` verdict and a corroborating commit on
  the lane branch. A `done` verdict without `state == done` is FINISHED-UNCONFIRMED: alert once and
  re-poll, never exit silently.
- **BLOCKED** is any of: a live dialog (`status == "waiting"`), a `needs-input` verdict, or a lane that
  stopped without writing any verdict.
- Treat push notices only as hints that trigger an earlier poll.
- Alert on state *transitions*, never on every poll.

If KB2 really reads `state=blocked` on `--json`, the verdict plus commit gives a fail-closed alert instead
of a silent exit or an endless re-send; the first step must be to capture KB2's real `--json` `state`.
The "stops the blocked-forever loop" benefit is conditional on that capture and is untested.

## Evidence

### Documentation contract (Claude Code, mirrored offline)

| Claim | Source | Quote |
|---|---|---|
| A finished turn reads `done`, never `blocked`. | `links/1.md:575` (agent-view) | "A session that finished its turn and is waiting for your next instruction reads `done`, not `blocked`. `blocked` always means the session needs something from you before it can continue." |
| `blocked` is broader than prompts: it also covers errors and a missing first prompt. `waitingFor` is set only for an open prompt in a live process. | `links/1.md:571` | "an error only you can clear such as an expired login, or its first prompt if you started it without one. When the wait is an open prompt in a live process, `waitingFor` names it" |
| `working` covers self-driven waits. | `links/1.md:570` | "A turn is running, or the session is between steps of work it drives on its own, such as a `/loop` iteration or a wait on CI." |
| `done` is defined independently of whether the process is alive. | `links/1.md:572` | "The last turn finished what you asked for and the session is ready for your next prompt, whether or not its process is still alive" |
| `pid`/`status` exist only while the process is alive; `waitingFor` only when `status` is `waiting`. | `links/1.md:560-561` | "`pid`, `status` \| While the process is alive" / "`waitingFor` \| When `status` is `waiting`" |
| Without `--all`, completed sessions are omitted. | `links/1.md:553` | "Add `--all` to also include completed background sessions" |
| `claude agents --json --all` is the supported read for a supervising session. | `links/1.md:566` | "`claude agents --json` is the supported way to read session state from outside Claude Code … Poll `claude agents --json --all`" |
| A self-written progress file is the documented pattern; `state.json` writes are overwritten. | `links/1.md:575` | "If you want a session to report progress in its own words, have it write a file of its own, for example under `$CLAUDE_JOB_DIR/tmp`, instead of editing `state.json`." |
| The UI has separate Idle and Completed rows; the JSON `state` has no `idle` value. | `links/1.md:121-122`, `:559` | "Idle \| Dimmed \| The session has nothing to do and is ready for your next prompt" / "Completed \| Green \| The task finished successfully" |
| A reply does not answer a permission prompt; it waits in the queue. | `links/1.md:183` | "replying doesn't answer it. Your reply waits in the queue. To answer the dialog, attach with `→`" |
| A finished lane and a lane that asked a question look the same at the process level; both are stopped after about an hour. | `links/1.md:586` | "A session that ended its turn by asking you a question counts as waiting for your next message." |
| After a shutdown, `failed` and `stopped` can mean "host died", not lane failure. | `links/1.md:637` | "Within 48 hours, the session shows as failed. Attach or reply to it and it restarts from where it left off." |
| An open PR moves a row to "Ready for review". `gh pr merge` output does not create a link. | `links/1.md:150`, `:163`, `:203` | "a session moves to `Ready for review` when it has an open pull request" / "`gh pr merge` is the common case" |
| `agent_completed` fires only while agent view is open. | `links/2.md:1972` | "A background session finishes or fails. Fires only while agent view is open in a terminal" |
| `permission_prompt` is delayed; `PermissionRequest` is the immediate hook. | `links/2.md:1981` | "To run a hook immediately when Claude asks for permission to use a tool, use PermissionRequest instead." |
| `idle_prompt` is a timer. | `links/2.md:1982` | "Expect `idle_prompt` about 60 seconds after Claude finishes responding, and only if you haven't typed since." |
| Stop does not fire on interrupt; API errors go to StopFailure. | `links/2.md:2211-2213` | "Does not run if the stoppage occurred due to a user interrupt. API errors fire StopFailure instead." |
| Stop's `background_tasks`/`session_crons` separate "done" from "paused". | `links/2.md:2219` | "let hooks distinguish 'session is done' from 'session is paused waiting for background work to wake it back up'" |
| The transcript may lack the final message at Stop time. | `links/2.md:2219`, `:638` | "the transcript file isn't guaranteed to include the final message at Stop time on all versions." |
| SessionEnd has no decision control and a shared 1.5 s budget. | `links/2.md:281`, `:896`; claim set | "`SessionEnd` hooks share a 1.5-second budget" |
| `notify_when_idle` means turn-finished with nothing queued, and also fires on exit. | `links/3.md:68`, `:78` | "send back one notice when that session next goes idle or exits. Idle here means the session finished a turn with nothing queued." |
| A notice subscription expires after 12 hours. | `links/3.md:86` | "If no notice arrives within 12 hours, Claude Code drops the subscription and tells Claude" |
| `refuse` or `hold` on either side kills or degrades the notice. | `links/3.md:88-89` | "the subscription expires unanswered after 12 hours" / "the watched session leaves the one-line status out" |
| Only the main conversation may subscribe. | `links/3.md:91` | "Only the Claude in your main conversation can subscribe, and only to your sessions on this machine." |
| Held messages expire. | `links/3.md:184` | "Past the deadline: Claude Code drops the message and reports it as expired to a sender it can reach." |
| Message loops are throttled, deduplicated and capped. | `links/3.md:274` | "drops identical repeats arriving within a short window, and queues at most 50 accepted messages" |
| **Absence:** none of the three caller pages describes a completion-sentinel protocol or any Codex mechanism. | re-run here | `grep -c -i sentinel links/2.md` → 0; control `grep -c -i idle_prompt links/2.md` → 5, so the probe discriminates. (Claim set: same result across `links/1-3.md`.) |

### Upstream reports (Claude Code issues; issue claims, not shipped code)

| Claim | URL | Quote | State (read 2026-10-02) |
|---|---|---|---|
| `state.json` (NOT `agents --json`) reads `blocked` for a merely idle session; in the same issue `claude agents --json` was accurate and is the stated workaround. Filed against 2.1.233, 0 comments. | https://github.com/anthropics/claude-code/issues/87882 | "`blocked` cannot be distinguished from 'idle, waiting for input', so every finished-but-not-exited session reads as blocked." | OPEN; bug, has repro, area:agent-view |
| A plain-prose question reports `idle`. | https://github.com/anthropics/claude-code/issues/85192 | "a session that just asked the user a question and is waiting reports `idle`." (v2.1.220) | OPEN |
| `state` comes from a stale text classifier. | https://github.com/anthropics/claude-code/issues/64036 | "driven by a stale, sticky text-classifier verdict persisted in each job's `state.json`" | OPEN |
| `state` and `tempo` are separate axes; a mid-turn `AskUserQuestion` sets only tempo/block. | https://github.com/anthropics/claude-code/issues/83705 | "the dialog writer sets `tempo: 'blocked'` + `needs` + `block: {questions}` and never touches state" | not re-read |
| Wake signals are edge-triggered and lossy. | https://github.com/anthropics/claude-code/issues/79570 | "edge-triggered, no ack, no idle re-poll" | closed and locked (manifest snippet) |
| Parallel completion notices are dropped. | https://github.com/anthropics/claude-code/issues/20754 | "Only 1 out of 3 agents sent a notification upon completion." | not re-read |
| Child completions queue against an idle parent. | https://github.com/anthropics/claude-code/issues/92095 | "delays of 1m44s, 12m06s, 48m34s and 11h35m" | not re-read |
| Subagents are not woken by background Bash completion. | https://github.com/anthropics/claude-code/issues/78782 | "The subagent sits idle forever while its finished work sits unread on disk." | not re-read |
| `completed` fires with live Monitor children. | https://github.com/anthropics/claude-code/issues/86085 | "'completed' fires with live Monitor children, terminal events dropped" | not re-read |
| Subagents report `completed` with no final text. | https://github.com/anthropics/claude-code/issues/83848 | "the outer harness still reports `status: completed`" | not re-read |
| There is no documented external API for working/idle/blocked. | https://github.com/anthropics/claude-code/issues/94620 | "There's no built-in, documented way for an external process to answer…" | OPEN |
| There is no "needs input, sleeping" indicator. | https://github.com/anthropics/claude-code/issues/86082 | title | not re-read |
| A finished agent is still shown as alive. | https://github.com/anthropics/claude-code/issues/74090 | "the UI shows the agent as alive while the main agent believes it finished long ago." | not re-read |

### Other orchestrators (each row says whether it SHIPS, PROPOSES, or is a THIRD-PARTY account)

| Tool | Kind | Claim | Source | Quote |
|---|---|---|---|---|
| ccmanager | **SHIPS** (PR merged 2026-08-10) | Claude state is classified by PTY screen markers. A missed prompt shape was misread as idle. | https://github.com/kbwo/ccmanager/pull/322 | "These prompts contain none of the markers the Claude state detector currently keys on … so ccmanager reports the session as idle while it is actually blocked" |
| herdr | **SHIPS** (bug closed `completed` 2026-07-13) | Codex state comes from the OSC terminal title; a static title misreported a working turn as idle. | https://github.com/herdrdev/herdr/issues/1281 | "While Codex visibly shows 'Working (... • esc to interrupt)', `herdr agent list` reports the pane as idle." |
| vibe-kanban | **THIRD-PARTY account of its source** (issue OPEN) | Completion is the stream-json `result` message plus the executor `exit_signal`. The Claude executor has none; the Codex executor does. | https://github.com/BloopAI/vibe-kanban/issues/2495 | "Claude Code in `-p --output-format=stream-json` mode does not exit after completing a task — it stays alive waiting for more messages on stdin." |
| agent-deck | **SHIPS** socket send (PR #2100); **PROPOSES** Codex status staging (#1794) | Delivers to Claude targets over Claude Code's messaging socket; staged Codex status evidence is a proposal. | https://github.com/asheshgoplani/agent-deck/pull/2100 ; https://github.com/asheshgoplani/agent-deck/discussions/1794 | titles only; bodies not read |
| Lunavect | **THIRD-PARTY** (show-and-tell discussion) | A menu bar app lists Codex and Claude sessions as working, waiting for approval or input, or response ready. | https://github.com/openai/codex/discussions/49253 | "lists Codex and Claude Code sessions with their state: working, waiting for approval or input, or response ready." |
| Codex hooks | **PROPOSES** (issue OPEN) | Full Claude Code hook parity for Codex. | https://github.com/openai/codex/issues/21753 | "every major lifecycle transition is observable" |
| codex exec | **SHIPS** (probed here, codex-cli 0.160.0) | Run-to-completion process with a final-message file and a JSONL event stream. | `mise exec -- codex exec --help` (rc=0), lines 103-107 | "--json  Print events to stdout as JSONL" / "-o, --output-last-message <FILE>  Specifies file where the last message from the agent should be written" |
| this repo | **SHIPS** | Typed lane receipts merged from self-report, hook events and session files. | `python/src/dotfiles_setup/lane_result.py:2`, `schemas/lane-result.json` | "Typed receipts and source-attributed agent DAGs for SDLC lanes." |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `waitingFor permission prompt state blocked` | query | planner | 110 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | planner | 29 | 0 |
| `qvxzpl9wtk4brn7 agentstate` | known-absent | planner | 0 | 0 |
| `repo:smtg-ai/claude-squad filename:tmux.go` | query | planner | 1 | 0 |
| `repo:kbwo/ccmanager filename:Detector` | query | planner | 2 | 0 |
| `repo:asheshgoplani/agent-deck hook status` | query | planner | 480 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | workflow | 29 | 0 |
| `repo:smtg-ai/claude-squad filename:README.md` | must-hit | workflow | 2 | 0 |
| `repo:kbwo/ccmanager filename:README.md` | must-hit | workflow | 6 | 0 |
| `repo:asheshgoplani/agent-deck filename:README.md` | must-hit | workflow | 16 | 0 |
| `repo:stravu/crystal filename:README.md` | must-hit | workflow | 3 | 0 |
| `repo:BloopAI/vibe-kanban filename:README.md` | must-hit | workflow | RATE-LIMITED | 1 |
| `repo:devflowinc/uzi filename:README.md` | must-hit | workflow | 1 | 0 |
| `repo:kenn-io/agentsview filename:README.md` | must-hit | workflow | 10 | 0 |
| `repo:openai/codex filename:README.md` | must-hit | workflow | 54 | 0 |
| `repo:ogulcancelik/herdr filename:README.md` | must-hit | workflow | 10 | 0 |

Notes:

- No separate CODE SEARCH NOTES were supplied with the input.
- The known-absent control returned 0 while every must-hit except vibe-kanban returned >0, so the search
  discriminates.
- The `tmux.go` (1) and `Detector` (2) hits were counted but never fetched (see Gaps).

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| anthropics/claude-code | agent lane completion blocked idle | 0 | `.agent/kb/raw/research-fanout/fanout-lane-completion-detection-2026-10-02/deps/anthropics--claude-code/1/manifest.json` |
| anthropics/claude-code | claude-squad | 0 | `…/deps/anthropics--claude-code/2/manifest.json` |
| anthropics/claude-code | ccmanager | 0 | `…/deps/anthropics--claude-code/3/manifest.json` |
| anthropics/claude-code | agent-deck | 0 | `…/deps/anthropics--claude-code/4/manifest.json` |
| anthropics/claude-code | crystal | 0 | `…/deps/anthropics--claude-code/5/manifest.json` |
| anthropics/claude-code | vibe-kanban | 0 | `…/deps/anthropics--claude-code/6/manifest.json` |
| anthropics/claude-code | uzi | 0 | `…/deps/anthropics--claude-code/7/manifest.json` |
| anthropics/claude-code | agentsview | 0 | `…/deps/anthropics--claude-code/8/manifest.json` |
| anthropics/claude-code | codex | 0 | `…/deps/anthropics--claude-code/9/manifest.json` |
| anthropics/claude-code | herdr | 0 | `…/deps/anthropics--claude-code/10/manifest.json` |
| smtg-ai/claude-squad | claude-code | 0 | `…/deps/smtg-ai--claude-squad/1/manifest.json` |
| kbwo/ccmanager | claude-code | 0 | `…/deps/kbwo--ccmanager/1/manifest.json` |
| asheshgoplani/agent-deck | claude-code | 0 | `…/deps/asheshgoplani--agent-deck/1/manifest.json` |
| stravu/crystal | claude-code | 0 | `…/deps/stravu--crystal/1/manifest.json` |
| BloopAI/vibe-kanban | claude-code | 0 | `…/deps/BloopAI--vibe-kanban/1/manifest.json` |
| devflowinc/uzi | claude-code | 0 | `…/deps/devflowinc--uzi/1/manifest.json` |
| kenn-io/agentsview | claude-code | 0 | `.agent/kb/raw/research-fanout/fanout-lane-completion-detection-2026-10-02/deps/kenn-io--agentsview/1/manifest.json` (given relative) |
| openai/codex | claude-code | 0 | `…/deps/openai--codex/1/manifest.json` |
| ogulcancelik/herdr | claude-code | 0 | `…/deps/kenn-io--agentsview/1/manifest.json` (**as supplied; wrong path**, see Conflicts; the real file is `…/deps/ogulcancelik--herdr/1/manifest.json`) |

`…` = `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-completion-20261002/.agent/kb/raw/research-fanout/fanout-lane-completion-detection-2026-10-02`.

Per-source results inside those manifests:

- **anthropics/claude-code:** discussions `empty_unverified` (canary 0) in all 10 runs; releases
  `empty_verified` in all 10; issues 0 for `uzi` and `agentsview` (control returned 10).
- **herdr:** issues errored (HTTP 422); discussions `empty_unverified`; releases ok, and they resolve to
  `herdrdev/herdr`.
- **uzi, ccmanager, agentsview:** discussions `empty_unverified`.
- **openai/codex:** releases `empty_verified`.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://code.claude.com/docs/en/agent-view | `docs/research/kb/raw/fanout-lane-completion-detection-2026-10-02/links/1.md` | 0 | 145050 | — |
| https://code.claude.com/docs/en/hooks | `docs/research/kb/raw/fanout-lane-completion-detection-2026-10-02/links/2.md` | 0 | 268882 | — |
| https://code.claude.com/docs/en/cross-session-messaging | `docs/research/kb/raw/fanout-lane-completion-detection-2026-10-02/links/3.md` | 0 | 38981 | — |

All three caller links are mirrored and cited above.

## Conflicts resolved

1. **Docs say `done`; we observe `blocked`.**
   - Docs: agent-view `links/1.md:575`.
   - Against: the requester's uncaptured 2.1.287 note. Issue #87882 does NOT support it (verification
     found it concerns `state.json`, was filed against 2.1.233, and recommends reading `state` from
     `claude agents --json`).
   - **Resolution (revised after verification): unresolved.** The docs are the only evidence about the
     supported `--json` surface; the observation is uncaptured and may be the human display. Capture
     `claude agents --json --all` for KB2 before deciding. Until then keep `state == done` as the primary
     signal and add corroboration (verdict, commit) rather than ignoring `state`.
2. **`working` + `idle` "after finishing".** This is not a conflict with the docs. `links/1.md:570`
   defines `working` to include self-driven waits, and the Stop hook's `background_tasks` (`links/2.md:2219`)
   is the documented way to tell them apart. The 12:33 lane most plausibly had an in-flight background
   task, monitor or cron. That is inferred, not measured: this sweep did not inspect that lane.
3. **Is a question "blocked" or "idle"?**
   - The docs list "a question it asked" under `blocked` (`:571`).
   - #85192 (v2.1.220) measured a prose question reading `idle` with no waiting marker.
   - #83705 says `AskUserQuestion` sets `tempo`/`block` rather than `state`.

   **Resolution:** only a live **dialog** reliably surfaces as `status: waiting` + `waitingFor`
   (`:560-561`). A prose question has no dialog, so no field reliably marks it. The protocol must
   therefore make a lane **write** its question rather than rely on any field. #85192 is older
   (v2.1.220), so it may since have changed; that has not been re-measured here.
4. **`smtg-ai/claude-squad` "redirects to agent-deck"** (mandatory gap) **vs the manifest.** The manifest
   holds claude-squad-shaped items (#312, discussion #318). A probe run here,
   `gh api repos/smtg-ai/claude-squad --jq .full_name`, returned `smtg-ai/claude-squad`. The control
   arm, the same call on `ogulcancelik/herdr`, returned `herdrdev/herdr`, so the probe *can* show a
   redirect. **Trusted: the probe** (primary API over a planner note). The redirect premise is refuted.
   The gap still stands, because no claude-squad source code was read.
5. **The herdr dependency row points at the agentsview manifest.** The DEPENDENCY RUNS input lists the
   kenn-io/agentsview manifest for `ogulcancelik/herdr`. The real herdr manifest exists at
   `deps/ogulcancelik--herdr/1/manifest.json` and was read here: issues HTTP 422, discussions empty, and
   releases under `herdrdev/herdr`. This is an input-wiring defect, recorded as-is in the table.
6. **vibe-kanban mechanics** come only from an OPEN issue that quotes its source (`claude.rs:380`,
   `codex.rs:554-558`). Neither the code nor a merged PR was read, so this is a **third-party account**,
   not a verified "ships" claim.
7. **The earlier draft at this path** recommended `/stop`-to-finish and waiting for a terminal state.
   That rested on sources outside this sweep's inputs, and it conflicts with the docs' own guidance (a
   self-written file, `links/1.md:575`). **Not carried forward.**

## Gaps

- **MANDATORY:** the dependency re-run of `smtg-ai/claude-squad` against `asheshgoplani/agent-deck` did
  not run. Its premise is refuted by the probe in Conflicts #4, but claude-squad's detection code
  remains unread.
- **MANDATORY:** the code search `repo:BloopAI/vibe-kanban filename:README.md` was RATE-LIMITED
  (HTTP 403), not 0.
- `claude-agents-json-state-done-blocked-stop-hook-idle:github-discussions` was `empty_unverified`
  (canary 0 items). Unknown, not "nothing found".
- `anthropics--claude-code/1-10:github-discussions` was `empty_unverified` in all 10 manifests (canary 0).
- `anthropics--claude-code/7:github-issues` (query `uzi`) was `empty_verified` with no relevant hit:
  how uzi detects completion is a gap.
- `anthropics--claude-code/8:github-issues` (query `agentsview`) was `empty_verified`: whether
  agentsview has a session-outcome field is a gap.
- `devflowinc--uzi/1:github-discussions`, `kbwo--ccmanager/1:github-discussions` and
  `kenn-io--agentsview/1:github-discussions` were all `empty_unverified` (canary 0).
- `ogulcancelik--herdr/1:github-issues` errored (`gh` HTTP 422 Validation Failed; herdr moved to
  `herdrdev/herdr`), and `ogulcancelik--herdr/1:github-discussions` was `empty_unverified`. herdr's
  detection code was not read; only issue #1281 was.
- Planner code search `repo:BloopAI/vibe-kanban filename:README.md` was rate-limited (rc 1); this is the
  same gap as the mandatory item above.
- **No source code** (tmux.go, Detector, hook status) was read for claude-squad, ccmanager, agent-deck,
  crystal or uzi. Only issue and PR metadata was gathered; ccmanager's detector is known only through
  PR #322's description.
- claude-squad `tmux.go` (count 1) and ccmanager `Detector` (count 2) were counted but never fetched.
- The kenn-io/agentsview manifest path appeared twice in the task list (once relative); it was read once.
- **Codex:** the event names in `codex exec --json` (for example a turn-completed event), how Codex
  approval requests surface in `exec` mode, and the app-server `turn/completed` notification were not
  verified. No generated app-server schema exists locally, and `grep` for `turn/completed` in `schemas/`
  returned rc=1 while the control `properties` matched. Whether a `codex exec` lane can block on a human
  at all is unverified.
- The two triggering lanes (KB2 and the 12:33 lane) were not re-inspected. Their `background_tasks`,
  their `waitingFor` at the time, and whether KB2's process was alive are unknown.
- Triage hits not read: daintree.org docs, agent-island.dev seven-state taxonomy, Prowl
  `agent-detection.md`, #90093, #92264.

Critic gaps (appended; each with its next probe):

- **No primary source code read** for claude-squad, ccmanager, agent-deck, crystal, uzi, herdr or
  agentsview; the "PTY scraping is fragile" lesson rests on single bug reports. Next: fetch
  `smtg-ai/claude-squad` `session/tmux/tmux.go`, ccmanager's Claude state detector
  (`src/services/stateDetector/*`), herdr's Codex title parser; record idle/working/waiting rules and whether
  any reads hooks or transcripts.
- **agentsview "session outcome" never examined**; the only probe was a claude-code issue search. Next: read
  `kenn-io/agentsview` schema/README (outcome, status, ended_at) and query the local archive for KB2 and
  the 12:33 lane.
- **The triggering lanes were never re-inspected** (background_tasks, waitingFor, pid liveness, raw
  `state.json`); the 12:33 background-task explanation is inferred. Next: `claude agents --json --all` plus
  `~/.claude/jobs/<id>/state.json` for both; check recorded Stop payloads and pid liveness.
- **Protocol rows unvalidated on 2.1.287**: `status == waiting` for AskUserQuestion and permission prompts,
  disappearance of `status`/`waitingFor` after the ~1 h idle stop, and whether #85192 / #87882 still
  reproduce. Next: a controlled `claude --bg` experiment (permission prompt, prose question,
  AskUserQuestion, clean finish), polling `claude agents --json --all` every 5 s, re-tested after idle stop.
- **Release currency unconfirmed**: changelog entries after 2.1.220 were not read; discussions queries were
  all `empty_unverified`. Next: `gh release list -R anthropics/claude-code`, grep CHANGELOG between 2.1.220
  and latest for "agents", "blocked", "state"; check linked PRs on #87882; `claude --version`.
- **Codex coverage thin**: `codex exec --json` event names, approval surfacing in exec mode, app-server
  `turn/completed` unverified; #21753 is only a proposal. Next: `codex-schema` skill
  (`mise run codex-schema-generate`), then `codex exec --json` on an approval-needing and a finishing prompt.
- **Several issues quoted from manifest snippets only, never re-read** (#83705, #20754, #92095, #78782,
  #86085, #83848, #86082, #74090); #79570 is "closed and locked" so a fix may exist. Next:
  `gh issue view <n> -R anthropics/claude-code --json state,closedAt,labels,comments` for each.
- **Other-orchestrator evidence lopsided**: vibe-kanban mechanics third-party only; agent-deck PR #2100 and
  discussion #1794 read by title; crystal and uzi have no findings; triage hits unread, so the
  "ships"/"proposes" labels for agent-deck are unverified. Next: read vibe-kanban `claude.rs`/`codex.rs`,
  agent-deck PR #2100 and #1794 in full, Prowl `agent-detection.md`; retry the rate-limited search.
- **Recommended mechanisms untested**: Stop/SessionEnd hooks as a done signal (payload fields, firing on
  `/stop` and crash, 1.5 s budget), `gh pr list --head` vs "Ready for review", `notify_when_idle`; and the
  repo's `lane_result.py` / `schemas/lane-result.json` were not compared with the proposed LANE-VERDICT line,
  which may duplicate an existing receipt format. Next: read those two files and decide whether to reuse the
  receipt schema; prototype a Stop hook writing a receipt and test normal finish, interrupt and kill.
- **Evidence tiers merged**: no tool shipping an explicit-completion-message protocol was examined; the
  recommendation is a design synthesis and the question-mark hedge rests on one third-party issue (#64036).
  Next: find a project that uses a lane-written sentinel or report file in production (the docs'
  `$CLAUDE_JOB_DIR` pattern is the nearest), cite it as shipped, and keep the protocol labelled "proposed
  here, untested" until the controlled experiment has run.

## Recommendation

Adopt the following **"documented `state` + verdict file + level-triggered poll" protocol** in
`parallel-work-split` §5 (the brief) and §6 (monitor). It is a **design synthesis proposed here and
untested**, not something other projects were shown to validate. It needs no new tooling beyond
`claude agents --json --all`, `mise run bounded-wait` and `git`. Step 0, before relying on it: run
`claude agents --json --all` and read `state.json` for KB2 and the 12:33 lane to learn the real `state`.

**1. The brief adds a VERDICT field, written by the lane as its LAST act.** The lane writes its report
file (the brief's PERSIST path; the docs sanction a self-written file for *progress*, `links/1.md:575`;
using it for a completion verdict is this project's inference) ending with one machine-readable line:

```
LANE-VERDICT: done|needs-input|failed  commit=<sha|none>  question=<one line or ->
```

The brief also forbids two things:

- **Asking a question in prose and ending the turn.** A lane that needs a human either uses the
  question tool (surfaces as `status: waiting`, `waitingFor: input needed`) or writes `needs-input`
  with the question first. A prose question is invisible to `status`/`waitingFor` (Conflicts #3).
- **Ending its final message with a question mark.** This is a hedge against classifier-driven
  `state`, which is a third-party claim (#64036); it is a mitigation, not a guarantee.

**2. The watcher classifies every lane on every poll.** It reads `claude agents --json --all` (never
without `--all`, `:553`) plus the verdict file, and applies the first matching row:

| # | Condition | Class | Watcher action |
|---|---|---|---|
| 1 | `status == "waiting"` (`waitingFor` set) | BLOCKED-LIVE | Alert at once with `waitingFor`. A permission prompt needs an attach; SendMessage cannot answer it (`:183`). Never counts as finished, whatever the verdict file says. |
| 2 | verdict `needs-input` | BLOCKED-ASKED | Alert with the question from the file. |
| 3 | verdict `failed`, or `state` in {`failed`, `stopped`} with no `done` verdict | TERMINAL-FAIL | Alert. Terminal for watcher exit, but reported as failure. Remember `failed` can mean the host died (`:637`). |
| 4 | `state == "done"`, verdict `done`, and `commit` reachable on the lane branch | FINISHED | Terminal. (Struck: "ignore `state`, `blocked` is the #87882 bug"; #87882 concerns `state.json`, not `--json`.) |
| 4b | verdict `done` and `commit` reachable, but `state != "done"` (e.g. `blocked`) | FINISHED-UNCONFIRMED | Alert once with the observed `state`, keep polling; treat as terminal only after the operator confirms or `state` becomes `done`. This is the KB2 case if it reproduces on `--json`. |
| 5 | `state == "working"` | RUNNING | Keep waiting. With `status == "idle"`, it is waiting on its own background work (`:570`). Alert only past a stale-age bound. |
| 6 | anything else (`state` in {`done`, `blocked`}, no verdict; a `done` state with no verdict is UNREPORTED too, since a verdict is still required for the lane's own report) | UNREPORTED-STOP | Alert once. The lane ended a turn without a verdict, which could be a prose question, an error, or a forgotten report. SendMessage the lane to write its verdict. **Never** counts as finished. |

**3. Exit only when every lane is FINISHED or TERMINAL-FAIL.** Alert on a lane's class *change*, not on
every poll. That ends the 30-minute "blocked" re-sends, which cross-session messaging would partly
deduplicate anyway (`links/3.md:274`).

**4. Keep push signals, but only as wake-ups.** `SendMessage notify_when_idle`, from the main
conversation only, may shorten the wait to the next poll. It must never replace the poll: it is
edge-triggered and lossy (#79570), expires after 12 hours (`links/3.md:86`), and means turn-finished
rather than task-finished. Do not use `agent_completed` (needs agent view open) or `idle_prompt` (a
60-second timer).

**5. PR existence is not the completion signal here.** The brief's STOP AT forbids lanes from opening
PRs, so the corroborator is a commit on the lane branch instead. Use agent view's "Ready for review" PR
signal only if a future brief lets a lane open its own PR, and even then remember that `gh pr merge`
output does not link (`:150`).

**6. Codex lanes use process exit plus the `-o` file** (`codex exec`, 0.160.0). This matches what the
repo's `lane_result.py` and `sdlc-team` settlement already do, and it fails closed when evidence is
inconsistent.

**7. Optional hardening, not needed for v1.** A lane-side `Stop` + `StopFailure` hook could append
`last_assistant_message`, `background_tasks` length and the error type to `$CLAUDE_JOB_DIR/tmp`. That
would automate rule 6's "why did it stop" question. Stop does not fire on interrupt (`links/2.md:2211`),
so it can supplement the verdict file but never replace it.

**Why this beats each alternative:**

- It keeps the documented `state == done` as the primary signal and adds corroboration, rather than
  discarding it on an unconfirmed observation.
- It takes "blocked on a human" from the one field fed by a real dialog, plus an explicit lane
  declaration.
- It treats silence as "unreported", never as "done", which is the lesson of #79570, #83848 and
  vibe-kanban #2495.
- It avoids the screen-scraping fragility that ccmanager #322 and herdr #1281 show in shipped code.

## Verification

Verdict key: CONFIRMED, UPHELD-MISLEADING (omission qualified in the text above), UPHELD-REFUTED (none),
OVERTURNED (adjudicator reversed the refuter), UNVERIFIED. The critic and adjudicator both ran.

| # | Claim | Verdict | Evidence and effect |
|---|---|---|---|
| 1 | Docs say finished reads `done`; #87882 and the 2.1.287 observation show finished sessions reading `blocked`, so `state` alone cannot end the watcher. | **UPHELD-MISLEADING** (docs half CONFIRMED, issue half misattributed) | `links/1.md:572`, `:575` confirm the docs. #87882 is OPEN, 0 comments, filed against 2.1.233, about `state.json` ("not a stable interface"); its own text says `claude agents --json` was accurate and recommends reading `state` from it. The 2.1.287 KB2 observation is uncaptured. Omitted: other signals (`status`, `waitingFor`, `--all`). Effect: Answer #1, Conflicts #1 and protocol row 4 corrected; "state alone cannot end the watcher" is a design inference. |
| 2 | `waitingFor` only when `status == waiting`; `pid`/`status` only while alive; a live dialog is the only field-level blocked-on-human signal fed by a real prompt. | **OVERTURNED** (refuter said misleading; adjudicator: not misleading) | `links/1.md:560-561`, `:571`; #85192 maintainer comment independently confirms. The claim is scoped to "fed by a real open prompt", which is accurate; `state` is covered elsewhere. No change. |
| 3 | A prose question ends the turn as `idle`, not waiting (#85192, OPEN); so a lane must declare itself in a verdict file. | **UPHELD-MISLEADING** (factual core CONFIRMED, conclusion overreaches) | #85192 OPEN, reproduced 2.1.220 and 2.1.232. Omitted: the question tool surfaces as `waiting`/`input needed`; docs list "a question it asked" under `state: blocked`. The verdict file is one mitigation, not the only one. Not re-measured on 2.1.287. Effect: Answer #3 and protocol brief item qualified. |
| 4 | Push signals cannot be the sole protocol (`agent_completed` only with agent view open; `notify_when_idle` one-shot, turn-finished, 12 h, main-conversation-only). | **CONFIRMED** | `links/2.md:1972`, `links/3.md:68`, `:86`, `:91`; offline docs `hooks.md:2273`, `cross-session-messaging.md:110`, `:117`; control arms run (present terms hit, a fresh absent term did not). No change. |
| 5 | Docs sanction a self-written progress file because `state.json` writes are overwritten, the basis for LANE-VERDICT as primary FINISHED signal. | **UPHELD-MISLEADING** (narrow sentence CONFIRMED) | `links/1.md:575` sanctions the file for progress, not as a completion verdict. The same section (`:566-572`) names `agents --json --all` `state` as the supported supervisor read. Effect: protocol reordered so `state == done` is primary and the verdict file is corroboration; the row-4 "ignore `state`" struck. |
| 6 | Other rows (docs quotes, issue states for #64036, #83705, #79570, #20754, #92095, #78782, #86085, #83848, #86082, #74090, ccmanager #322, herdr #1281, vibe-kanban #2495, agent-deck, codex #21753). | **UNVERIFIED** (not adjudicated) | Several quoted from manifest snippets only and not re-read; see Gaps. |

Net change to the conclusion: the verdict file and branch commit stay as a fail-closed corroborator and as
the only carrier for a lane's prose question, but the documented `state == done` is restored as the
primary completion signal, and the headline "no single field is reliable" is downgraded to "no
single field is shown unreliable on the supported surface; the KB2 observation needs capturing".

## Provenance

Full routing (every node that ran, including the reconcile node that wrote this section; no stage failed).

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| deps:smtg-ai/claude-squad | general-purpose | sonnet | low |
| deps:kbwo/ccmanager | general-purpose | sonnet | low |
| deps:asheshgoplani/agent-deck | general-purpose | sonnet | low |
| deps:stravu/crystal | general-purpose | sonnet | low |
| deps:BloopAI/vibe-kanban | general-purpose | sonnet | low |
| deps:devflowinc/uzi | general-purpose | sonnet | low |
| deps:kenn-io/agentsview | general-purpose | sonnet | low |
| deps:openai/codex | general-purpose | sonnet | low |
| deps:ogulcancelik/herdr | general-purpose | sonnet | low |
| mirror:1/3 | general-purpose | haiku | (default) |
| mirror:2/3 | general-purpose | haiku | (default) |
| mirror:3/3 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
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

The synthesize node also ran its own probes:

- issue and PR states via `gh api` for #87882, #85192, #64036, vibe-kanban #2495, ccmanager #322,
  herdr #1281 and codex #21753;
- body reads of ccmanager #322, herdr #1281 and vibe-kanban #2495;
- repo redirect probes for claude-squad and herdr;
- `codex exec --help` (0.160.0);
- `grep` with control arms over the mirrors and `schemas/`.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): agent-view/hooks/messaging docs (via code.claude.com) and issues #87882, #85192, #64036, #83705, #79570, #20754, #92095, #78782, #86085, #83848, #94620, #86082, #74090, #75888, #71369.
- [kbwo/ccmanager](https://github.com/kbwo/ccmanager): PR #322, a PTY state detector marker for permission prompts.
- [herdrdev/herdr](https://github.com/herdrdev/herdr) (formerly ogulcancelik/herdr): issue #1281, OSC-title Codex state misread; releases.
- [BloopAI/vibe-kanban](https://github.com/BloopAI/vibe-kanban): issue #2495, the executor completion signal via the stream-json `result` message.
- [asheshgoplani/agent-deck](https://github.com/asheshgoplani/agent-deck): PR #2100 messaging-socket send; discussion #1794 Codex status proposal.
- [openai/codex](https://github.com/openai/codex): issue #21753 hook parity; discussion #49253 Lunavect; `codex exec` CLI help.
- [smtg-ai/claude-squad](https://github.com/smtg-ai/claude-squad): dependency issues and discussions metadata; redirect probe.
- [stravu/crystal](https://github.com/stravu/crystal): dependency issues, discussions and releases metadata only.
- [devflowinc/uzi](https://github.com/devflowinc/uzi): dependency issues metadata only.
- [kenn-io/agentsview](https://github.com/kenn-io/agentsview): dependency issues and releases metadata only.
- [cli/cli](https://github.com/cli/cli): code-search health control only.

## Addendum (coordinator, 2026-10-02): mandatory gaps closed and KB2 capture

- **vibe-kanban README control re-run:** `gh api -X GET search/code -f q='repo:BloopAI/vibe-kanban filename:README.md' --jq .total_count` returned **6**, rc=0. The earlier 403 was a rate limit; the control passes.
- **claude-squad redirect:** `gh api -i repos/smtg-ai/claude-squad` returned **HTTP/2.0 200 OK** with no redirect, so the "redirects to asheshgoplani/agent-deck" gap was a false positive from the dependency stage. Its source was still not read; that gap stands.
- **KB2 capture (partial):** the lane watcher's `claude agents --json --all` tick earlier on 2026-10-02 read `kb-20261002.lane-KB2` as `state: "blocked"` with no `waitingFor`. At that moment `claude logs` showed the lane idle at its prompt after "done 12:13 PM" and "1 shell still running". `status` was not recorded on that tick. So the misread was on the `--json` surface, not only on `state.json`. Two later ticks read KB2 as `working/busy` (it had been resumed), then `done/idle`.
- **Lane G:** read as `state: "working"`, `status: "idle"` for over an hour after its log said "done 12:33 PM". This fits the documented "working = driving its own background work" (Answer #2). An idle `working` lane therefore needs the verdict file to be classified.
