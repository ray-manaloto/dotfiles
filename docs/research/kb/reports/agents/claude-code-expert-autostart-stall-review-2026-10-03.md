# Claude Code expertise — bg autostart / overnight stall review (2026-10-03, v2.1.288)

Status: FINAL (the coordinator stopped the run at the turn limit). Everything not settled by a probe is marked
**UNVERIFIED**. Engine: `claude --version` → `2.1.288 (Claude Code)`; binary
`~/.local/share/claude/versions/2.1.288` (BUILD_TIME 2026-10-02T16:42:03Z, GIT_SHA 17fe1eb7).

Corpora consulted: binary byte-scan (python regex, offsets cited); `~/.claude/daemon.log`;
`~/.claude/jobs/*/state.json` + `timeline.jsonl`; session transcripts under `~/.claude/projects/`; codex
rollouts under `~/.codex/sessions`; offline docs `$CC` =
`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.
Not done (turn limit): `pmset -g log`, reading user/project settings, the 2.1.28x changelog, live
probes of the permission dialogs. Machine sleep does not matter to the findings below. The daemon log
shows the 8 h retire sweeps firing all night at :xx:55, so the supervisor was awake.

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | CONFIRMED (mechanism) / SUSPECT (who) | Coordinator 7541ae79 was **explicitly killed** via the daemon control socket at 03:31:28Z, 56 s after its last turn. It was not idle-retired, it did not crash, it was not shed for low memory, and sleep did not stop it | `daemon.log:715` `bg settled 7541ae79 (killed)` with NO `bg retire` line; control: 12 retired sessions each show `bg retire …` then `(done)` |
| 2 | CONFIRMED | 9 lanes (+3) were **idle-retired** after 8 h because they are Remote-Control-bridged. The non-bridged grace is 1 h | `daemon.log` retire lines; binary constants `ar=3600000`, `sr=28800000` @193516223 |
| 3 | CONFIRMED | A settled (killed/retired) session **cannot be woken by SendMessage**: no process means no inbox socket | watcher + audit-000 sends → `No agent named … is reachable`; `$CC/cross-session-messaging.md:124` |
| 4 | CONFIRMED | A session with an in-flight **`session_cron`** (`/loop`, CronCreate) is exempt from idle retire | binary `retireIfSettled` → `{retired:!1,reason:"session-cron"}` @193421685; live control: the `/loop` watcher 998ab91b was never retired |
| 5 | CONFIRMED | "exit code -1" = the command finished while its owning session's process was gone, so the result is unknown, not a failure | task output `[process exited while detached; exit code unknown]` |
| 6 | CONFIRMED (caller-supplied anchor, not re-read by me) | EnterWorktree to a path outside `.claude/worktrees/` always prompts | `$CC/worktrees.md:43` (per coordinator) + 7 parked lanes |
| 7 | UNVERIFIED | Reading `/private/tmp/claude-501/<proj>/<session>/tasks/*.output` prompts because that path is outside the allowed directories | lane reports only; no probe run |
| 8 | UNVERIFIED | Respawning or launching in an untrusted worktree fails with `workspace_untrusted` | binary string `job_respawn","workspace_untrusted"` @193265525; not probed |

---

## 1. Root causes

### 1a. Coordinator unresponsive overnight

Timeline: `~/.claude/jobs/7541ae79/timeline.jsonl`. The last entry before the gap is
`2026-10-03T03:30:32.690Z done 'IWYU lock drift fixed in PR; devcontainer-cap shipping'`, and the next is
`2026-10-03T15:24:11.769Z working 'Re-syncing state after resume'`.

`~/.claude/daemon.log`:
```
[2026-10-03T03:31:28.639Z] [bg] bg settled 7541ae79 (killed)
...
[2026-10-03T15:23:52.375Z] [bg] bg claimed-spare 7541ae79 (fleet)      <- Ray's reply/attach restarted it
```

The binary's settle logger (`function Ze` @193530016: `` a(`bg settled ${short} (${w})`) ``) maps each
path to one log shape:

| Path | Outcome logged |
|---|---|
| idle retire (`retireIfSettled` → `Ve()`) | `bg retire <id>: <cause>, idle Nh` then `(done)` |
| low-memory retire | same, suffixed `[low memory]` |
| process vanished (`checkPid` ESRCH) | `(crashed)`, then a respawn |
| crash while state.json is terminal (`doSpawnUnlessSettledOnDisk`) | `f_("done")="success"` → `(done)` |
| control-socket op `kill` (`case"kill":` @192653095 → `n.kill(sig, h.handoff?"handoff":"killed")`) | **`(killed)`** |

The coordinator's state.json read `done`, so a crash would have logged `(done)`. The `(killed)` line with
no retire line means an **explicit kill**. The callers of that op (`Hge()` @193118261) are `claude stop`
and `claude kill <id>`, agent view's `x` key (`fleet_view_stop_job`), `claude rm <id>`, `claude respawn`
(no respawn followed here), and failed-dispatch cleanup.

**SUSPECT: the requester is unattributed.** Three searches came up empty:

- every tool_use in `~/.claude/projects/**/*.jsonl`, 03:20–03:32Z, for `kill|claude stop|stop |daemon|pkill|respawn|claude rm|7541ae79|53012`: 0 executed matches;
- every `~/.codex/sessions` rollout touched since 01:31Z, for `claude (stop|rm|kill|respawn|daemon)`: spec prose only;
- `~/.claude/history.jsonl`: 0 prompts 03:20–03:40Z.

The repo has exactly one programmatic `claude stop`: `coordinator_handoff.py:1167`, the successor-only
`retire` gate. No successor was spawned (the daemon log shows no spawn between 02:56Z and 15:23Z).

That leaves three candidates no on-disk log can tell apart: agent view's `x` key, a hand-typed
`claude stop`, or a stop/archive from the Remote Control surface (the session is bridged:
`bridgeSessionId` is set). The daemon logs no requester.

Why it stayed dead for 12 h: nothing in the engine restarts a settled session when a peer messages it.

- `$CC/cross-session-messaging.md:124`: "A session appears only when it binds an inbox socket."
- Senders got `{"success":false,"message":"No agent named 'dotfiles-20261002b.coordinator' is reachable."}` (watcher at 03:31:47Z, audit-000 at 03:34:10Z).
- Only attach, a reply from agent view, `claude respawn`, or `claude --resume <id> --bg` starts a process (`$CC/agent-view.md:123`, `:450-458`).

Contributing design gap: the coordinator ended its turn in a terminal `done` state while a ship it owned was
still running. Nothing was scheduled to wake it, and no external process watched it.

### 1b. Nine lanes "vanished": idle retire, by design

`~/.claude/daemon.log` (verbatim; three more were retired too: 88910d3b, 45bec37a, 6fae0fec):
```
06:05:54Z bg retire e686b1fe: idle-prompt, idle 8h   (fnox-provider)
07:10:54Z bg retire ec69effd: settled, idle 8h       (worktree-ergonomics)
08:18:55Z bg retire 53b8d22d: settled, idle 8h       (host-load)
08:36:55Z bg retire 5361f892: settled, idle 8h       (cc-repoint)
08:47:55Z bg retire dc62b079: settled, idle 8h       (s29-00b)
08:51:55Z bg retire a6fef20a: idle-prompt, idle 8h   (audit-s29)
10:36:55Z bg retire b7d40872: settled, idle 8h       (kb fix-838)
11:28:55Z bg retire 9652109a: idle-prompt, idle 8h   (devcontainer-cap)
11:30:55Z bg retire a0d2bdd6: idle-prompt, idle 8h   (kb ship)
```

**Mechanism** (binary `retireIfSettled` @193421685): the retire threshold is
`I = n.bridgeSessionId ? Math.max(e,s) : e`. The constants @193516223 are `ar=3600000` (1 h, the normal
grace), `sr=28800000` (8 h, the bridged grace), `Je=60000` (the low-memory grace) and `bt=28800000`.
`$CC/agent-view.md:748` says "about an hour"; that is true only for non-bridged sessions.

**Exemptions:** `attached`, `pinned` (`~/.claude/jobs/pins.json`, currently `[]`, set with Ctrl+T),
`recent-input`, `inflight` (tasks or queued > 0), `session-cron`, `routine`.

**Why they look gone:**

- `claude agents --json` without `--all` omits completed sessions (`$CC/agent-view.md:705`).
- `claude logs` reads only the live process's in-memory ring (`:486`), so it answers "job not found".
- `ListAgents` shows only the stale Remote Control record, as "offline". A send to it "arrives only after that session's machine reconnects" (`$CC/cross-session-messaging.md:162`), which never happens for a retired local process.
- The coordinator's own 15:24:35Z send to devcontainer-cap returned `"a Claude session on another machine, over Remote Control; not confirmed read"`.

All job dirs still exist, and every state is `done/idle`. No work was lost.

### 1c. Permission dialogs

- **(a) EnterWorktree relocation** (caller fact, `$CC/worktrees.md:43`, not re-read by me): entering a worktree outside `.claude/worktrees/` always asks. A lane launched from the main checkout that then calls EnterWorktree on `../dotfiles.worktrees/<lane>` hits this every time.
  - It parks the session indefinitely. Per `$CC/agent-view.md:747`, a session paused on a permission prompt or other dialog keeps its process and is never retired.
  - It is a guaranteed human step. The structural fix is never to call EnterWorktree: launch the lane with its cwd already inside the worktree.
- **(b) Reading its own task output** under `/private/tmp/claude-501/...`: **UNVERIFIED**, since I ran no probe. Plausible cause: `/private/tmp` is not among the session's working directories (cwd plus `--add-dir`/`additionalDirectories`), so `Read` prompts even though the harness's own notice says "use Read on that file path".
- **(c) Workspace trust: UNVERIFIED.**
  - `$CC/agent-view.md:37` and `:970`: `claude agents` in an untrusted directory shows the trust dialog.
  - The binary has `job_respawn … workspace_untrusted` @193265525, which suggests a respawn into an untrusted cwd is refused, with the prompt queued.
  - A new `../dotfiles.worktrees/<name>` path is a new workspace. Whether it inherits trust from the parent repo was not probed.

### 1d. "exit code -1" background tasks

Two verbatim task outputs:

- `b2c0mz3ar.output` is `[process exited while detached; exit code unknown]`;
- `brypddljx.output` ends with the same line.

Both were reported as `completed (exit code -1)` at 15:23:55Z, when the restarted process adopted them.
`$CC/agent-view.md:752` says background shell commands "carry over to its next process", but no process
owned these two commands when they finished, so their rc was lost.

**-1 is a sentinel, not a failure.** The ship's real result was `rc=1`, in
`~/.claude/jobs/7541ae79/tmp/ship-cap.log`. Always read the rc your command wrote to its own log; this repo
already has that rule.

---

## 2. Fixes, ranked

1. **Launch every lane with cwd = its worktree; never call EnterWorktree in a lane.** Scope: the launch recipe and briefs; no setting.
   - Why narrowest: it removes the relocation prompt structurally. No permission loosening, and the deny rules stay.
   - Arm: launch one throwaway lane from the main checkout whose brief says "EnterWorktree ../dotfiles.worktrees/x". `claude agents --json` shows `status: waiting, waitingFor: permission prompt`. The same brief launched with `cd ../dotfiles.worktrees/x && claude --bg …` and no EnterWorktree reaches `done` with no `waitingFor`.
   - Alternative: create worktrees under `<repo>/.claude/worktrees/`. EnterWorktree into those does not relocate (caller fact `$CC/worktrees.md:43`), but it changes the repo's worktree layout and cleanup (`$CC/agent-view.md:907`).
2. **Keep the coordinator's process alive with a session cron.** Scope: the coordinator's first action is `/loop 10m <cheap inbox+fleet check>`, or a CronCreate job.
   - Why: `retireIfSettled` returns `reason:"session-cron"`, so the coordinator is never idle-retired.
   - Live control: the `/loop` watcher 998ab91b survived the night while 12 sessions were retired.
   - Each tick is a real turn, so it also notices dead lanes with no inbound message.
   - It does NOT protect against an explicit `claude stop` or `x`; fix 3 covers that.
   - Arm: two throwaway bg sessions, one with `/loop 10m echo tick` and one without. After the grace (1 h unbridged, 8 h bridged), the daemon log shows `bg retire` only for the second.
   - Pinning (Ctrl+T, or `pins.json`) also exempts a session, but it needs a human keystroke. `~/.claude/jobs/*` is "not a stable interface" (`$CC/agent-view.md:729`), so do not write `pins.json` from code.
3. **An external watchdog that restarts a dead coordinator with a prompt.** Scope: a user launchd agent (`~/Library/LaunchAgents`) every 5–10 min, running a repo `mise run` task (python, zero-bash).
   - It reads `claude agents --json --all`. If the coordinator row has no `pid`, or a terminal `state`, while the handoff inbox has unread entries, it runs `claude --resume <full sessionId> --bg "<inbox digest>"` from the coordinator's cwd.
   - Why this verb: `claude respawn <id>` brings back the conversation IDLE, without continuing (ledger 2.1.222 row "respawn on a truly stopped node comes back IDLE"). `--resume … --bg "<prompt>"` both restarts and gives it the turn (`$CC/agent-view.md:450-458`, v2.1.257+).
   - **UNVERIFIED on 2.1.288** whether `--resume --bg` continues in place for a session that is already a bg job, or forks with a `note:`. Probe it on a throwaway session first.
   - `crossSessionInbound` survives, because `respawnFlags` already carry `--settings {"crossSessionInbound":"accept"}` (coordinator state.json).
   - **Do not** use `CronCreate` as the watchdog: it is session-only and dies with the process (ledger). `claude daemon install` is disabled in this version (binary string "Service install is disabled in this version").
   - Arm: `claude stop` a throwaway coordinator. Within one watchdog period, `daemon.log` shows `claimed-spare <id>`, and the transcript has a new user turn carrying the digest. With the watchdog unloaded, nothing happens.
4. **Treat retired lanes as normal; detect them correctly.**
   - Watchers must poll `claude agents --json --all`. "Done and no pid" means retired, not lost.
   - To give a retired lane new work, use the same `--resume <sessionId> --bg "<prompt>"`, not SendMessage: SendMessage to the offline bridge record never lands.
   - Arm: SendMessage to a retired lane returns `Remote Control; not confirmed read`, while `--resume --bg` produces a new turn.
5. **Task-output reads (UNVERIFIED cause).** Narrowest option: in each lane brief, have long commands write their log and rc into the worktree's `.agent/logs/` or `$CLAUDE_JOB_DIR/tmp` and read that, instead of the harness `/private/tmp/claude-501/...` path.
   - If a settings change is wanted, the narrowest is a user-scope `permissions.allow` entry `Read(//private/tmp/claude-501/**)`. It must be user scope because the path is machine- and uid-specific. Project deny rules are unaffected.
   - Arm: in a bg lane, Read a task `.output` with and without the rule; `waitingFor: permission prompt` appears only without it.
6. **Workspace trust (UNVERIFIED).** Before launch, open each new worktree path once with a human, or have the launch recipe reuse long-lived worktree directories that are already trusted.
   - Arm: `claude --bg` in a brand-new `git worktree add` path. Check whether `claude agents --json` shows `blocked` with `dialog open`, or the respawn path's `workspace_untrusted`.
7. **Never end a coordinator turn as `done` while it owns a running ship or land.** It should either wait in-turn on a bounded poll or keep a `/loop` (fix 2), so the result is read. A task notification can arrive 12 h late (finding 1d).

**Keep, untouched:** all project deny rules, guards and hook_guard. None of the fixes above loosens them.

---

## 3. Canonical lane-launch recipe

```bash
# 1. worktree first (sibling layout kept; or <repo>/.claude/worktrees/<lane> if adopting native layout)
git -C ~/dev/github/ray-manaloto/dotfiles worktree add ../dotfiles.worktrees/<lane> -b <branch> origin/main
# 2. launch FROM the worktree, so cwd == worktree (no EnterWorktree, no relocation prompt)
cd ~/dev/github/ray-manaloto/dotfiles.worktrees/<lane> && \
claude --bg -n "<repo>-<ISO>.<lane>" \
  --settings '{"crossSessionInbound":"accept"}' \
  "<brief: never EnterWorktree; write logs+rc under .agent/logs/; report via SendMessage to <coordinator> AND append to handoff-inbox>"
```

- Keep every `CLAUDE_*` pin in the settings `env` block, never a shell export: `exec` launch mode strips them (ledger).
- Coordinator: launch from the main checkout as today, with the same `--settings`, and make its first action `/loop 10m <inbox+fleet tick>` (fix 2).
- `--permission-mode` was not evaluated; this run made no change to it.

## 4. Watchdog / keep-alive

- **What natively wakes a session:** a cross-session message, or a background-task completion, starts a new turn only in a session whose process is LIVE (`$CC/cross-session-messaging.md:95`, "When the receiving session is idle, Claude Code starts a new turn with the message").
- **Nothing wakes a settled session.** No `crossSessionInbound`/`dialogExpiry` value, and no env var found, revives a killed or retired process.
- **Keep-alive:** a `/loop` or CronCreate inside the coordinator (exemption `session-cron`). This beats `refreshInterval` tricks or pins.
- **Relaunch:** an external launchd job running a mise task (fix 3). A cloud routine has no local file access, and Desktop scheduled tasks need the app open (ledger).
- **Dead-lane detection from the coordinator's `/loop` tick:**
  - a row with `state` ∈ {done, stopped, failed} and no `pid` is retired or stopped;
  - re-task it with `claude --resume <sessionId> --bg "<prompt>"`;
  - `blocked` with `waitingFor: permission prompt` needs a human (escalate via SendUserMessage);
  - a heartbeat gap while `tempo==active` is a hang (ledger: detected, never auto-recovered).

## 5. Open questions only a human can answer

1. Did you stop the coordinator around 22:31 local on 10-02? It could have been agent view `x`, `claude stop`, or Remote Control/claude.ai. The engine does not record who sent the kill.
2. May a user launchd agent run a watchdog that relaunches the coordinator with `claude --resume … --bg`? It would outlive sessions and spend tokens unattended.
3. Should bg sessions keep Remote Control bridging? It stretches the idle grace from 1 h to 8 h, but it makes retired peers look "offline but sendable".
4. Should worktrees move to `<repo>/.claude/worktrees/` (native layout, no relocation prompt), or stay as siblings with the "launch inside" rule?
5. May a user-scope `Read(//private/tmp/claude-501/**)` allow rule be added, if the redirect-to-own-log approach is not enough?

## Ledger entries to append

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| Idle-retire grace is 1 h normally and **8 h for Remote-Control-bridged** sessions (`I = bridgeSessionId ? max(ar,sr) : ar`, `ar=3600000`, `sr=28800000`); low-memory grace 60 s | CONFIRMED | binary @193421685 / @193516223; daemon.log `idle 8h` ×12 | 2.1.288 | 2026-10-03 |
| `retireIfSettled` exemptions: attached, pinned, recent-input, inflight, **session-cron**, routine; a `/loop` session is never idle-retired | CONFIRMED | binary; live: the /loop watcher survived while 12 were retired | 2.1.288 | 2026-10-03 |
| `bg settled <id> (killed)` with no `bg retire` line = an explicit control-socket kill (stop/x/rm/respawn), never idle, crash or low memory; the requester is not logged | CONFIRMED | binary `Ze`, `case"kill"`, `Hge` callers | 2.1.288 | 2026-10-03 |
| SendMessage to a retired or killed local session fails (`not reachable`), or goes to its offline Remote Control twin and never lands | CONFIRMED | two transcripts | 2.1.288 | 2026-10-03 |
| Task notification `exit code -1` = `[process exited while detached; exit code unknown]` | CONFIRMED | task output files | 2.1.288 | 2026-10-03 |

## GitHub repos touched

_None._ Local binary, logs, transcripts and offline docs only.
