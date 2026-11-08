# Herdr core socket cutover with a verified checklist

*   **Author:** Ray Manaloto
*   **Status:** Reviewed (EGM review 2026-11-07: Stages 5-9, Codex rounds 10-12; see consolidated_review_report.md and resolve_changelog.md)
*   **Date:** 2026-11-07
*   **Public copy:** terminal ids are replaced by A1-A7 (the T2/T3 sessions) or a description, session ids and local evidence paths are dropped; the private original keeps them.
*   **Runbook:** a local runbook, not in this repository, holds every step, command and rollback. This design says what is built and why. It does not copy the runbook.

--------------------------------------------------------------------------------

## Overview

This Mac runs one herdr-core (`hc` 0.1.18). It is the background program that owns every terminal and agent session. Herdr.app 0.1.13 is the window that shows them. The window and the core find each other through a Unix socket file.

The core and the window look for that socket in different places. The core listens at `~/.local/run/herdr-core/default.sock`. A Herdr window opened from the Dock, and every new login shell, look at `~/.local/state/herdr-core/default/default.sock`. So each time the window is reopened from the Dock, it shows a "Herdr needs herdr-core" screen while 34 terminals are still running (observed 2026-11-07).

This design moves the core to the default path, the one everything else already uses. A moved core can't keep its running programs, so the agent sessions are first drained and later resumed by session ID.

Two tools prove the result, and they are split on purpose:

- **A small permanent doctor.** `mise run herdr:doctor` (hometools `herdr-doctor`) is read-only. It prints pass or fail for checks that are true at any time. It never writes a file and never runs `hc`.
- **A one-time cutover script.** It is local and not committed. It runs the stages, holds the receipts and the baseline, and calls the doctor for its JSON. It is deleted with the drain records.

The work lands in the dotfiles repo (`~/dev/github/ray-manaloto/dotfiles`) as two pull requests, one before the move and one after.

The window disappearing on its own at about 11:31 to 11:40 today is a separate problem with an unknown cause. This design does not fix it. It adds one owner-run, logged relaunch before the drain so the next disappearance leaves evidence (Track W).

## The Problem

**What the owner sees.** The Herdr window disappeared during work. Reopened from the Dock, it showed "Herdr needs herdr-core … Install it for me". The sessions were still running, but the window could not reach them. The screen also invites a click on "Install it for me", which the owner must not press. The only way back today is to quit the window and relaunch it with the socket path given by hand:
`open --env HC_SOCKET="$HOME/.local/run/herdr-core/default.sock" ~/Applications/Herdr.app`.
It has happened before, and the Nov 4 to 6 work stopped short of a lasting fix.

**Why it happens.**

- hc chooses its socket in this order (`paths.rs:28-34`):
  1. `HC_SOCKET`;
  2. the `socket` key in `~/.config/herdr-core/config.toml`;
  3. `$XDG_RUNTIME_DIR/herdr-core/<session>.sock`;
  4. otherwise `~/.local/state/herdr-core/default/default.sock`.
- The running core (pid 40030) was started on Nov 4 at 09:00:13 (`ps` start time). The launch route is open (Q2). Its environment still had `XDG_RUNTIME_DIR=~/.local/run`. That export came from the retiring `macos-development-environment` repo (`macos-dev-env.zsh:35`).
- Login shells no longer set it. The core kept the value it started with, and so did every program it launched.
- So the only processes on the old path are the core itself and its children. The Dock, new shells and `env -i` all resolve to the default path.

**Why the fix is not just "restart the core".**

- A scratch test showed that `hc server restart` is refused when the caller's path differs from the core's.
- It also showed that `hc server stop` followed by a start at another path ends every running program. A kept terminal comes back only as an empty `sh`.
- So the move costs one restart of every program. The design limits that cost: before the stop, only sessions with a recorded, recently checked resume ID are still running.

**What else the owner asked to settle at the same time.**

- Every reference to the retiring projects should leave dotfiles, so agents stop treating them as live. Those projects are `macos-development-environment`, `claude-code-marketplace` and `knowledge-base`.
- The herdr skills in each AI harness folder should be checked.
- The install's health should be checkable with a mise task.

**Why it matters.** A window that can't find its core looks like lost work, and the screen it shows points toward an action that is off-limits. Every relaunch costs a manual workaround. Under time pressure today, a workaround-related command killed a working session (a working session at 12:03:54).

## Goals

Each goal is a check in `mise run herdr:doctor` or in the cutover script. The check table in the Technical Plan gives its ID.

*   **G1. One core, at the default path, from a clean environment.**
    - Exactly one core process holds `~/.local/state/herdr-core/default/default.sock`. `core.lock`, which holds a socket path, not a pid, names that same socket. The pid and start time don't change between gates, except at the one authorized transition after the zero-core barrier (`--accept-new-core`, P-IDENTITY).
    - Its terminals inherit no `CLAUDECODE`, `CLAUDE_CODE_*`, `XDG_RUNTIME_DIR` or `HC_SOCKET` (V6).
*   **G2. The old path is retired.** `lsof +D ~/.local/run/herdr-core` is empty (V5). `XDG_RUNTIME_DIR` is absent from new login shells and from `launchctl getenv` (V1).
*   **G3. A Dock launch reaches the core with no workaround.** The window shows its spaces, not the install screen. `herdr-app ls` succeeds, and the window's environment has no `HC_SOCKET` (V7, V8).
*   **G4. `hc` works from every kind of shell with nothing extra set.**
    - A new Terminal.app login shell, a Claude tool shell and a Codex tool shell all reach the same core pid (V2, V9).
    - Codex shells meet this once the codex-fnox change is deployed (S5.8), which is after the move and before any Codex session is resumed. A running Codex session keeps the options it started with.
*   **G5. Working and waiting sessions are back in place.**
    - Each T2 and T3 session (A1, A2, A3, A4, A5, A6, A7) runs again with the same session ID, cwd, space name and tab name.
    - Each answers a **new** `MAINT-POST-...` nonce in a completed turn appended after the history size recorded before the stop, in the file of the expected ID (V12).
*   **G6. New Claude tabs write their transcripts** without the `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE` flag. This is proven by a new entry appended to the file, not by its modification time (V13).
*   **G7. The checks exist, can fail, and can't do harm.**
    - The doctor runs read-only checks and never calls `hc` (V15). It reads versions from Info.plist and the `current` symlink, not from `hc --version`.
    - On today's state it fails the expected list of checks. After the move it passes.
    - A check that can't observe what it needs reports UNKNOWN, which blocks green.
    - The doctor's code is held to 100% coverage, with real tools wherever a test can run them and stand-ins only for pgrep, launchctl and hc. The cutover script is checked by hand and by Codex, not by hk.
    - Negative tests run only inside a clean `env -i` scratch environment whose socket is checked before each command.
    - The existing `.claude/skills/verify/SKILL.md` gains a herdr section that runs the doctor.
*   **G8. Dotfiles stops pointing at retired projects.** No reference to `claude-code-marketplace`, `knowledge-base` or `macos-development-environment` remains outside the allowlist table below (V11). That includes an owner decision on the `miserc.toml:29` mirror line.
*   **G9. The herdr skills are present and current** in `~/.claude/skills`, `~/.agents/skills` (Codex), the agy folder under `~/.gemini`, and `~/.config/opencode/skills` (V10). They are pinned to the installed hc version, and the install hook updates a skill that already exists.
*   **G10. The next window disappearance leaves evidence.**
    - Before the drain, the owner relaunches Herdr once from Terminal.app with output sent to `~/Library/Logs/Herdr/herdr-app.log` (Track W).
    - The primary crash evidence is macOS's own crash report in `~/Library/Logs/DiagnosticReports/Herdr*`. The log file is secondary, because it may be empty at info level.
    - This is a one-time capture. A permanent LaunchAgent is a follow-up (Non-Goals).
*   **G11. No lost agent work (T1-T3).** This covers agent sessions. The close rule per tier:
    - **T0 shells:** no transcript and no token. They close after fresh scrollback is saved. A running command in a shell is ended only with the owner's OK, recorded in the manifest.
    - **T1 to T3 agents:** the rules below.
    - No agent program ends unless its session ID, cwd and fresh scrollback (taken just before the close) are recorded.
    - It must also have answered a new checkpoint token that was saved to its transcript, or written a handoff note that the owner accepted.
    - The stop happens only when every manifest row has its scrollback file and every waiting or working session has a recorded transcript size.

## Non-Goals

*   **Finding why the window disappeared.** The cause is unknown. The prime suspect, closing a space's last tab with `--confirmed true`, didn't crash an isolated window within 10 minutes. This design adds capture (Track W) and one reported check (V14, a space close after the move). V14 doesn't decide whether the cutover is done.
*   **The mise LaunchAgent for the window (follow-up, out of PR B).** A LaunchAgent (`dev.mise.herdr-app`, `keep_alive_on_failure`, 30-second throttle, a `herdr:open` task) would start Herdr with logging and keep launchd's exit record. It is a separate change after the cutover, with its own PR. Q7 below keeps the evidence that it works: a launchd-started Herdr ran as a GUI app, a SIGKILL left `Killed: 9` in `launchctl print`, and a normal quit exited 0 with no relaunch. Open points for that PR: a Dock click while the launchd copy runs is untested, and the app wrote nothing at info level in every capture so far, so the log may still be empty.
*   **Resuming idle sessions.** T0 shells and T1 idle agents are closed with their resume IDs saved in the manifest. They can be resumed later by ID, but not as part of this work.
*   **Installing hc from dotfiles.** Today the only install path is the app's first-run installer, the forbidden button. A dotfiles-managed installer needs its own design. For now the doctor only checks the installed versions.
*   **The config `socket` pin, a reboot, or automatic rollback.** The owner chose a full cutover, an in-place stop and a Dock-or-manual start, and "pause and ask" on the first failure.
*   **Changing the retiring repos.** They are not edited. The only check is that nothing applies them again.
*   **Guarding the core's automatic start after the cutover (C-M18).** After S8, a crash, reboot or hc self-update can again let whichever client connects first start the core, with its own environment. This design does not pick a designated core starter. The permanent doctor's V2 (no routing input) shows it at the next `/verify` when the new core's starter set a routing input. V6 can't: cleanup removes the drain folder and the cutover script that produce its receipt, so `/verify` reports V6 as SKIP from then on, and a core started with an inherited environment that routes nothing differently stays unseen. `docs/agents/herdr-core.md` (item 12) says so.
*   **Changing Codex's `shell_environment_policy`.** It stays `inherit = "core"`. `inherit = "all"` would expose much more of the environment to tool shells.
*   **Any change to Claude Code plugins or marketplaces.** They need the owner's separate OK under the standing rule.

## Open Questions

These must be answered, read-only, in step S0.1 before anything is stopped. Step S1.1 is blocked until the S0 results table is filled.

*   **Q1. Can the Dock start a core? ANSWERED 2026-11-07 for the direct start only.** The launchd route that a real Dock click uses is not yet proven.
    - **From source:** the app runs `hc connect` (app v0.1.13 `hc.rs:277`), which calls `connect_or_start` (core v0.1.18 `cli.rs:829`). That starts a core unless `core.lock` names a socket that still accepts connections (`client.rs:108-118`). That case is this morning's "needs herdr-core" screen.
    - **Scratch test:** an isolated Herdr, with no `XDG_RUNTIME_DIR` (as from the Dock), started a core at the state-folder socket in about 2 seconds.
    - **Condition for S5:** the old core must be fully stopped, so its socket refuses connections, before Herdr is opened.
    - **Who starts the new core (review C-B1).** Only the owner's own Dock click, or the `env -i ... hc server start` fallback. The coordinator never runs `open -a Herdr`, because `open(1)` passes the caller's environment to the app. A Claude session would seed the new core with `CLAUDECODE` and `CLAUDE_CODE_*`.
    - If V6 is red at S5.6, the new core is still empty. Stop it, start it again with the `env -i` fallback, and run V6 again before resuming any session.
*   **Q2. What does stopping the old core need?** Does `hc server stop` reach it with `HC_SOCKET` alone, or with `XDG_RUNTIME_DIR` too? Does the stop remove `core.lock`? Is the core a launchd KeepAlive job that launchd might restart at the old path?
*   **Q3. What does a new core bring back?** Does it restore the kept terminals' records and `herdr.space`/`herdr.tab` labels from the state folder? Do space IDs survive, or only names?
*   **Q4. A probe that starts nothing.** Is there a command that prints the core pid without starting a core? What are the exact process names of the core, the holders and the app?
*   **Q5. Where does `claude-hc` live? ANSWERED 2026-11-07: nowhere.** No `claude-hc` exists. Claude tabs run `claude --dangerously-skip-permissions --brief --resume <id>` directly. `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE` is set only per process, so the resume argv sets it explicitly.
*   **Q6. Will A2 and A3 finish?** Their long shell commands must either end, or be written down and given up with the owner's OK.
*   **Q8. How can we see a core's real environment? ANSWERED 2026-11-07: `hc-safe <p> <s> -- exec --env HC_V6_NONCE=<nonce> /usr/bin/env`, parsed by variable name. Partly proven; one residual.** `ps eww` on the core can hide variables that launchd restored after exec (`codex-env-findings.md:22,65-67`), so V6 needs a probe terminal inside the core.
    - **Original probe.** A scratch core was started with canary variables only in its start environment. The probes ran from a canary-free `env -i` client. The canaries showed up in the probe output, so the probe sees the core's environment, not the client's (scratchpad `v6-probe-test.sh`, lines 12-24).
    - **Negative control (2026-11-07, review C-B2 accepted).** A clean scratch core was probed from a deliberately dirty client (`CLAUDECODE`, `CLAUDE_CODE_CHILD_SESSION`, `HC_SOCKET` and a canary set) through an `hc-safe`-style sandbox. The probe returned 18 env lines and 0 client variables. Real core 40030 was unchanged. Evidence: `s0-q8-v6-negative-control.txt` (local evidence).
    - **Residual.** V6 is not yet shown on a core that the Dock or launchd started, which is the kind S5 creates. It is checked live at S5.6, with the restart branch from Q1 if it is red.
*   **Q9. Does the `hc-safe` sandbox really block autostart? ANSWERED 2026-11-07 (scratch core, both start routes): yes.** The sandbox is `(version 1)(allow default)(deny process-fork)`; it replaced the idea of denying the herdr-core binary (Alternative I). With no core, a sandboxed `hc ls` exits 5 "cannot start core: Operation not permitted" on the direct route, and on the launchd route it fails the same way without loading a job. Against a live core, ls, get, send, read and run --bg all work.
*   **Q7. Can the mise LaunchAgent start a GUI app? ANSWERED 2026-11-07 (temporary scratch job, 3 runs): yes.** This is evidence for the follow-up, not part of this work.
    - A launchd-started Herdr ran as a working GUI app. `ls` and `status` answered, `shot` rendered a frame, and it started its own core.
    - After a SIGKILL, `launchctl print` showed `last terminating signal = Killed: 9` and `runs = 2`, and `KeepAlive {SuccessfulExit=false}` relaunched the window.
    - The log goes to stdout, not stderr. When idle, the app writes nothing at info or debug level.
    - `kill -SEGV` did not end the app, so crash tests must use SIGKILL or SIGABRT.
    - A normal quit exits 0 and is not relaunched (`last exit code = 0`, `runs = 1`).
    - Untested: a Dock click while the launchd copy runs.

### S0 results

S1.1 does not start until every row marked "Blocked on S0" is filled (none left as of 2026-11-07) from the read-only S0.1 run. "Known" rows stay as written. Rows marked "Deferred to S5.6" are live-cutover residuals: they do not block S1.1, and the S5.6 gate with its guarded retry checks them (Codex round 11, finding 4).

| Item | Literal needed | Status |
|---|---|---|
| Direct-start of a core from the app (Q1) | starts at the state-folder socket in about 2 s | Known |
| Launchd/Dock-start route (Q1, Q8) | V6 clean on a Dock-started core | Deferred to S5.6 (V6 gate plus the guarded `env -i` retry) |
| Stop verb and its environment (Q2) | `HC_SOCKET="$HOME/.local/run/herdr-core/default.sock" hc server stop` → `{"stopped":true}`, exit 0. `XDG_RUNTIME_DIR` is not needed (scratch core started through `XDG_RUNTIME_DIR`, stopped with `HC_SOCKET` alone). The old socket file is removed. **`core.lock` stays and still names the old socket**, which then refuses connections, so the next start may proceed and rewrites it. **No launchd restart risk:** the real core (pid 40030, argv `hc --hc-launchd /tmp/hc-launchd-40025-…/ready`, parent 1) has no job in `launchctl list`. The transient job is gone, so nothing relaunches it. | Answered 2026-11-07 (`s01-scratch.txt`, read-only launchctl) |
| What a new core restores (Q3) | A new core at a **different socket path** but the same state folder brings back **kept** terminals (`--keep`) as live, with their labels (`herdr.space=s1` survived). Non-kept terminals come back as `finished`. Terminal records live in the state folder (`terminals.json`), not under the socket path. So the real new core at `~/.local/state/herdr-core/default/default.sock` reads the same records. This matches `hc --help`: "stop parks kept terminals; next core start gives them shells". | Answered 2026-11-07 (`s01-scratch.txt`) |
| Core, holder and app process names (Q4) | **Core:** `hc --hc-launchd …/ready` when launchd-started (real core 40030), `hc serve` when started directly (scratch). **Holders:** `hc hold --socket …` (pid 40486, the *current* holder, 23 terminals) and `herdr-core hold --socket …` (pid 79687, a *non-current* holder still holding 9 terminals). **Window client:** `herdr-core connect` (pid 37773). **App:** `…/Herdr.app/Contents/MacOS/Herdr`. Core count = the `lsof` listener pid plus an argv match on `hc --hc-launchd` or `hc serve`, never `pgrep -x`. | Answered 2026-11-07 |
| `core.lock` path | `~/.local/state/herdr-core/default/core.lock`, containing the old socket path today (observed 2026-11-07) | Known |
| Pid-only probe (Q4) | `hc server status --json` under `deny process-fork`. Live: prints `pid`, `version`, `uptime_ms`, `live`, `holders`. No core: exit 5 "cannot start core: Operation not permitted", and nothing starts. It does not print the socket; the socket comes from `lsof`. V9 uses `hc-safe --own-env <p> <s> -- server status --json`. | Answered 2026-11-07 (`s01-scratch.txt`) |
| `claude-hc` location and flags (Q5) | **There is no `claude-hc`.** It is not on `PATH`, not in `~/.local/bin`, and dotfiles, `~/.config` and the app's `programs.json` don't mention it (programs.json defines only `codex`). Claude tabs run `claude --dangerously-skip-permissions --brief --resume <id>` directly (A4 argv). `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE` is set in no config, only per process (A3). | Answered 2026-11-07 |
| Long shell commands (Q6) | A2 and A3 end or are given up | Drain-time (S3), not discoverable in S0. Does not block S1.1. |
| V6 probe by name (Q8) | canary test plus negative control. **Exact nonce form (scratch, 2026-11-07):** `hc-safe <p> <s> -- exec --env HC_V6_NONCE=<nonce> /usr/bin/env`, exit 0. The nonce line appears, and the core's start-environment canaries (`CLAUDECODE`, `HC_V6_CANARY`, `XDG_RUNTIME_DIR`) appear, so the probe reports the core's environment. The `/usr/bin/env HC_V6_NONCE=<n> /usr/bin/env` form also works. The `--env` form is the one used. | Known (residual above) |
| Sandbox blocks autostart (Q9) | both start routes | Known |
| `hc-safe` from agent tool shells (C-M10) | The sandboxed `hc server status --json` with `HC_SOCKET` set to the old socket: **(a) Claude tool shell in herdr-core (a Claude tab, 2.1.318): works**, exit 0, pid 40030. **(b) Codex full-access tool shell (a Codex tab): works**, exit 0, pid 40030. **(c) Codex `-s read-only` tool shell (fresh tab a fresh read-only Codex tab, since closed): fails** with `sandbox-exec: sandbox_apply: Operation not permitted`, exit 71: Codex's own seatbelt can't be nested. So read-only Codex shells (reviewers) use the `lsof` V3/V4 plus V2 routing-input fallback, and their V9 is **BLOCKED**, never a pass. | Answered 2026-11-07 |
| hc and Herdr versions | hc 0.1.18 from `~/.local/share/herdr-core/current/Contents/Info.plist`; Herdr 0.1.13 from `~/Applications/Herdr.app/Contents/Info.plist` | Known |
| `hc-safe`'s own exit codes, outside hc's | There is no local hc source to prove which codes hc 0.1.18 can return; observed hc codes are 0, 2 and 5. **Change:** `hc-safe` uses its own codes 80 (`core-gone`, which covers a pid or socket mismatch), 81 (usage), 82 (sandbox refused), and passes hc's own codes through. Then no proof is needed. | Resolved by design change 2026-11-07 |

## Critical User Journeys (CUJs)

### CUJ 1: Reopen Herdr from the Dock

*   **Given**: The move is done. Herdr is quit. Nothing in launchd or the shell sets `HC_SOCKET` or `XDG_RUNTIME_DIR`.
*   **When**: The owner clicks Herdr in the Dock.
*   **Then**:
    - The window opens on its spaces, not on "needs herdr-core".
    - `herdr-app ls` lists them.
    - The app's environment has no `HC_SOCKET`.

### CUJ 2: Use `hc` from any new shell

*   **Given**: The move is done and PR B is applied.
*   **When**: The owner opens a new Terminal.app tab and runs `hc ls`. A Claude agent and a Codex agent each run `hc ls` from their tool shells.
*   **Then**: All three succeed, and all three report the same core pid. No shell has `HC_SOCKET` set.

### CUJ 3: A working session continues after the move

*   **Given**: A1 had finished, or stopped at a clean point, before the move. Its session ID, cwd, space and tab name are in the manifest, and its transcript was checked as recent.
*   **When**: The coordinator reopens it after the move with `claude --dangerously-skip-permissions --brief --resume <id>` in the same space, tab name and cwd. It then sends a new `MAINT-POST-...` nonce.
*   **Then**: The session answers with that nonce in a finished turn. That turn is appended after the transcript size recorded before the stop, in the same ID's file. It picks up its own task list from where it stopped.

### CUJ 4: A check fails during the move

*   **Given**: The old core is stopped, and the doctor reports V3 red: nothing listens at the default path.
*   **When**: The coordinator reaches that stop point.
*   **Then**:
    - It runs no further step and starts no core.
    - It tells the owner which check failed and gives the doctor's JSON line.
    - It offers the written options from the runbook: the fallback start, or the R5 rollback.
    - It waits for the owner to choose.
    - If the owner picks rollback, everything that could reconnect is quit first: the window, Orca and CLion. Then the new core is stopped, and the doctor must show zero cores and no listeners before the old-path core starts. A fresh workaround window is launched last.

### CUJ 5: The window disappears again

*   **Given**: The owner relaunched Herdr from Terminal.app before the drain, with output going to `~/Library/Logs/Herdr/herdr-app.log`.
*   **When**: The window disappears.
*   **Then**:
    - `~/Library/Logs/DiagnosticReports/Herdr*` is checked first. A crash leaves a report there.
    - The log file is checked second. It may be empty.
    - There is no launchd exit record and no automatic relaunch. The owner reopens the window by hand.
    - The sessions are still running in the core.
    - The owner notes the time and what was being closed. That evidence goes into a `herdr-app feedback` report.

## Technical Plan (Architecture)

### Before and after

```text
TODAY (split)                                         AFTER THE CUTOVER
-------------                                         -----------------
herdr-core (pid 40030, Nov 4)                         herdr-core (new, owner Dock or env -i, clean env)
  env: XDG_RUNTIME_DIR=~/.local/run,                    env: no XDG_RUNTIME_DIR, no CLAUDE_*, no HC_SOCKET
       CLAUDE_CODE_CHILD*, CLAUDECODE                   listens: ~/.local/state/herdr-core/default/default.sock
  listens: ~/.local/run/herdr-core/default.sock                ^        ^          ^           ^
     ^            ^                                            |        |          |           |
     |            |                                     Herdr.app   login shell  Claude tool  Codex tool shell
 workaround   its own children                         (Dock)       (nothing    shell        (codex-fnox no
 window       (HC_TERMINAL_SOCKET,                                    set)                     longer sets
 (HC_SOCKET)  Codex -c HC_SOCKET)                                                              HC_SOCKET)

Dock app, new shells, env -i  ──> ~/.local/state/...   everything resolves the same path by rule 4 of
  (nothing listens) ──> "needs herdr-core"            paths.rs:28-34: no HC_SOCKET, no config pin,
                                                       no XDG_RUNTIME_DIR -> the default path
```

The design adds no new long-running part. It removes the one input that split the path (`XDG_RUNTIME_DIR` in the core's environment) and adds read-only checks that prove the result.

### Components

| Component | Kind | Lives in | Role |
|---|---|---|---|
| `herdr:doctor` | mise file task (Python launcher) + `hometools herdr-doctor` | `unix/home/.config/mise/tasks/herdr/doctor`, `python/home/src/hometools/herdr.py` | Permanent, read-only, pass/fail. Checks V1, V2, V3, V4, V5, V7, V10, V11, V15. Never writes a file, never runs `hc`. One JSON line plus an exit code. |
| Cutover script | local Python, not in git | `~/.local/state/dotfiles/herdr-update-socket/drain-2026-11-07/cutover.py` | Stages `pre-move`, `post-move`, `post-cutover`, `final` with allowed-red sets. Receipts V6, V8, V9, V12, V13 and their producers. The P-IDENTITY `baseline.json`. `--accept-new-core --target default\|old`. The zero-core barrier record. Completed-turn validation (it may copy logic from repotools `pane_approval.py`). Calls the doctor for its JSON. Checked by hand and by Codex, not by hk. |
| herdr section of `/verify` | Claude Code repo skill | `.claude/skills/verify/SKILL.md` (existing file, new section) | Runs `mise run herdr:doctor`, then the checks that need a live agent through the cutover script or `hc-safe`. |
| hk step | hk linter entry | `hk.pkl` | One `herdr` step with deletion-aware selection (see "hk mechanism"). It runs unit and contract tests only. |
| `hc-safe` | Python launcher | `unix/home/.local/bin/hc-safe` | Pid-checked, sandboxed `hc` calls for the coordinator and `/verify`. |
| codex-fnox | launcher script | `unix/home/.local/bin/codex-fnox` | Drops only its `HC_SOCKET` line. Deployed after the move and before any Codex resume (S5.8). |
| Drain records | local files, not in git | `~/.local/state/dotfiles/herdr-update-socket/drain-2026-11-07/` | `manifest.txt`, `scrollback/`, `handoff/`, `snapshot/`, `receipts/`, `resume-commands.md`, `stage5-runbook.md`, `cutover.py`. Private session names stay out of the repo. |
| Coordinator | this Claude session, hosted by Rex | outside herdr-core | Runs every stage. It runs the S5.3 stop and the S5.5 `env -i` fallback start **only after the owner's explicit OK at that step**. It never opens the app (review C-B1). It pauses and asks the owner at each stop point. The owner keeps the go (S5.1), quitting apps (S5.2), the Terminal.app relaunch (Track W) and attesting the window. |

### The checks

The doctor owns the checks it can observe from outside. The cutover script owns the checks that need a receipt. "Input" is what the check reads.

| ID | Observes | Run by | Input |
|---|---|---|---|
| V1 | `XDG_RUNTIME_DIR` absent from new login shells and `launchctl getenv` | doctor | `env -i ... /bin/zsh -lic` probe; `launchctl getenv` (read-only) |
| V2 | No routing input is set, so every environment resolves the default path | doctor | The environments of the Dock app, a login shell and `env -i`. Green means: no `HC_SOCKET`, no `socket` key in the herdr-core config, no `XDG_RUNTIME_DIR`, default `HC_SESSION` and `XDG_STATE_HOME`. The doctor does not copy hc's path rules. The login shell runs sandboxed, so a value a herdr program would compute there can't be seen: a scan of the zsh startup files, a tripwire and not a proof, makes V2 unknown when they visibly name a herdr program or hold compiled `.zwc` code (O3). V9 login is the authoritative routing check. |
| V3 | A listener exists at the default socket, exactly one holder | doctor | `test -S`, `lsof` on `~/.local/state/herdr-core/default/default.sock` |
| V4 | Exactly one core process, equal to the listener, and `core.lock` names the default socket | doctor | `pgrep -a -f` on the core argv (`hc` or `herdr-core` followed by `--hc-launchd`, or by `serve` when started directly; S0 Q4), the V3 listener pid, `core.lock` read as a path, `ps -o lstart=` |
| V5 | The old path is retired (a missing folder counts as empty and passes) | doctor | `lsof +D ~/.local/run/herdr-core` |
| V6 | The core's terminals inherit a clean environment | cutover script | Receipt: a probe terminal running `/usr/bin/env` through `hc-safe`, parsed by variable name |
| V7 | The Herdr app environment has no `HC_SOCKET` | doctor | The app pid's environment from the kernel (`sysctl` KERN_PROCARGS2); `ps eww` joins the strings with spaces and can't be split back. Unknown with no window running |
| V8 | A Dock launch reaches the core | cutover script | Receipt: the owner's attestation file plus `herdr-app ls` |
| V9 | `hc` reaches the same core pid from every shell kind | cutover script | Receipt per shell, from `hc-safe --own-env ... ls` in the shell's own environment |
| V10 | The herdr skill is present and current in four folders | doctor | `test -f` on each `SKILL.md`; tag compared with the hc version from Info.plist |
| V11 | No retired-project references outside the allowlist | doctor | `rg` over the repo, minus the allowlist table below |
| V12 | A resumed session is back in place | cutover script | Receipt from the manifest, `hc-safe` labels, and the history file after the recorded size |
| V13 | A new Claude tab writes its transcript | cutover script | Receipt: a new `end_turn` entry with a fresh nonce after the recorded size |
| V14 | The window survives one space close | `/verify` | Reported only, never decides "done" |
| V15 | The doctor cannot start a core | doctor | Structural guard: `herdr.py` does not name `hc` as a program and does not call `subprocess` with it; core count and socket files are equal before and after a doctor run |

**Versions without running hc.** The doctor reads the hc version from `~/.local/share/herdr-core/current/Contents/Info.plist` (`CFBundleShortVersionString`, today 0.1.18), where `current` is a symlink to the active build. It reads the Herdr version from `~/Applications/Herdr.app/Contents/Info.plist` (today 0.1.13). The symlink target is a hash directory, so the version comes from the plist, not from the directory name.

**V11 allowlist.** The allowlist lives in `herdr.py`, beside the check, and every entry has a reason.

| Path | Why it stays |
|---|---|
| `docs/research/lsp/data/saved-searches.json:3` | Records where the data came from. |
| `GLOSSARY.md:5,13,171` | Describes the sunset as history. |
| `docs/agents/issue-tracker.md:43` | `from-marketplace` is a live issue label. |
| `unix/home/.config/mise/miserc.toml:29` | The mirror folder still holds hundreds of repos with their own `mise.toml`. The entry stops mise from loading them. Only its comment changes. |
| `python/tests/test_mise_trust.py:24` (`MIRROR`) | Tests that the kept `miserc.toml:29` entry really ignores the mirror. It must name the real path. |
| `python/tests/test_mise_trust.py:30` (`.codex/worktrees/new2/claude-code-marketplace`) | A fixture for "a Codex copy of a repo that is not dotfiles". The repo name is incidental, but it matches the real Codex worktrees on this Mac. |
| `python/home/src/hometools/herdr.py` (the pattern and allowlist constants) and `python/home/tests/test_herdr_doctor.py` (V11 fixtures) | The checker's own patterns and test data. Matched by path, not by line. |

**Removed or rewritten by PR B (not allowlisted):** `config.toml:150` (drop the "(claude-code-marketplace D154)" note from the hk pin comment), `config.toml:373,468` (item 15(b)), `mise.toml:74` (item 17). Tree checked 2026-11-07 at dotfiles `f27a5e2` with `rg -i` over the V11 patterns: these 13 lines are every match, so after PR B only allowlisted lines remain (Codex round 11, finding 7).

### How the doctor sees without touching

The doctor's rule: **never run `hc`.** hc starts a core itself when a connection fails (`client.rs:85-99`), and `HC_SOCKET` doesn't stop that. So every check reads the system from outside:

```text
routing    = does any environment set HC_SOCKET / XDG_RUNTIME_DIR / HC_SESSION / XDG_STATE_HOME,
             or does ~/.config/herdr-core/config.toml have a `socket` key?   # any input unreadable -> UNKNOWN
listeners  = lsof on the default socket path                                 # who holds it
cores      = pgrep -f on core argv, cross-checked with the lsof listener pid # how many (names vary: hc, herdr-core)
lockpath   = read core.lock                                                  # the socket path the core advertised (NOT a pid)
started    = ps -o lstart= -p <listener pid>                                 # start time, to detect a replaced core
old_holders= lsof +D ~/.local/run/herdr-core                                 # anything left on the old path
window     = pgrep -x <Herdr name>; sysctl KERN_PROCARGS2 -> HC_SOCKET?
versions   = Info.plist of the current symlink target and of Herdr.app
```

The doctor prints one JSON line and exits with a code:

```json
{"observation": {"hc": "0.1.18", "app": "0.1.13", "skill_tag": "v0.1.17",
  "skills_missing": ["~/.gemini/antigravity-cli/skills/herdr-core", "~/.config/opencode/skills/herdr-core"],
  "cores": [40030], "listeners": [], "lock_path": "~/.local/run/herdr-core/default.sock",
  "core_started": "Wed Nov  4 09:00:13 2026", "old_path_holders": [40030, 40486, 79687],
  "windows": [{"pid": 37548, "hc_socket": "~/.local/run/herdr-core/default.sock"}],
  "routing": [{"where": "app 37548", "name": "HC_SOCKET", "value": "~/.local/run/herdr-core/default.sock"}],
  "references": ["mise.toml:74", "unix/home/.config/mise/config.toml:150"], "guard": [], "unchanged": true,
  "unknown": []},
 "checks": {"V1": "pass", "V2": "fail", "V3": "fail", "V4": "fail", "V5": "fail", "V7": "fail", "V10": "fail", "V11": "fail", "V15": "pass"}}
```

This is today's pre-move state. V3 is red because nothing listens at the default path. V4 is red because the one core holds the old path. The doctor has no stage, no allowed-red set and no verdict field. Exit codes: 0 all pass, 1 any fail, 2 usage error, 3 any UNKNOWN and none failed.

### The cutover script and its stages

The cutover script applies a stage's allowed-red set to the doctor's JSON plus its own receipts. Its verdict is `stage-pass` only when the failing set equals the stage's allowed set and nothing is UNKNOWN. Anything else is `stage-fail`, with the unexpected reds, unexpected greens and UNKNOWNs named.

| Stage | When | Allowed red set | Notes |
|---|---|---|---|
| `pre-move` | S2.1, S4.3 | V2, V3, V4, V5, V6, V7, V9, V10, V11, V13 | V1 and V15 must be green. V8, V12 and V14 are not evaluated. |
| `post-move` | S5.6 | none of V3 to V7 | Partial run: V3 to V7 only, with the V6 receipt. V8 is not required yet. |
| `post-cutover` | S7.1 | V10, V11 | Before PR B. V8 is first required green here. |
| `final` | S8.3 | none | After PR B. |
| `rollback` | R5 step (5), only with `--accept-new-core --target old` | V2, V3, V4, V5, V7, V10, V11 | Accepts the restored old-path core (Codex round 12, finding 1). V1, V15 and identity (exactly one core, at `~/.local/run/herdr-core/default.sock`) must be green. V6 is judged by the `CLAUDE*`-only rule, because `XDG_RUNTIME_DIR` is expected there. Receipts: V6 only. A `stage-pass` here is required before R5 resumes any session. |

Receipts are bound to the core pid and start time and are valid for 10 minutes. A required check with no valid receipt is UNKNOWN. Before each gate the script collects fresh V6 evidence (step E6 in the runbook).

### Session tiers

| Tier | What it is | Drain | After the move |
|---|---|---|---|
| T0 | Idle shells | Closed first, resume data saved | Not resumed |
| T1 | Idle agents | Closed with resume ID saved | Not resumed in this work |
| T2 | Waiting agents, settled by the owner | Checkpoint token saved, then closed | Resumed one at a time (S6) |
| T3 | Working agents | Reach a clean point first (A1 waits to finish) | Resumed one at a time (S6) |

### How steps talk to a core: `hc-safe`

hc has no option to turn off autostart, and `HC_SOCKET` doesn't stop it. So every hc call in the drain, resume and checks (`get`, `read`, `ls`, `send`, `run`) goes through `hc-safe`:

```text
usage: hc-safe [--own-env] <expected-core-pid> <socket> -- <hc args...>
```

1. It refuses unless `lsof` shows exactly one listener on that socket, with the expected pid.
2. It runs hc with `subprocess.run` (not exec) under `sandbox-exec -p '(version 1)(allow default)(deny process-fork)'`. hc and the core are the same binary, so the binary itself can't be blocked. Talking to an existing core needs no new process, but starting one does. So if the core disappears between the check and the call, autostart fails instead of starting a second core.
3. Because it does not exec, it can check the listener pid again after the call and report a replaced core.

| Exit | Meaning |
|---|---|
| 0 | hc succeeded and the listener pid is unchanged |
| 80 | `core-gone`: the pre-check failed, hc reported exit 5 `unavailable`, or the listener changed during the call |
| 81 | Usage error in `hc-safe`'s own arguments, for example a non-numeric pid. argparse's default exit 2 is overridden, because hc's clap also uses 2. |
| 82 | `sandbox-exec` is missing or refused to apply. It printed `sandbox_apply: Operation not permitted` with exit 71, as in a Codex `-s read-only` shell (S0, C-M10). The caller marks the check **BLOCKED**. |
| other | hc's own exit code, passed through |

`--own-env` skips the `HC_SOCKET` injection, so a call tests the shell's real routing (V9). It still runs under the sandbox and still checks the pid before and after. Its codes 80 to 82 are outside hc's observed codes (0, 2, 5), so no source proof is needed (S0, 2026-11-07).

### Track W: capturing the next window disappearance

The window disappears for an unknown reason. Before the S3 drain, the owner relaunches Herdr once from Terminal.app. The coordinator does not run it, because Claude's environment would leak into the app (C-B1).

The current window (pid 37548) carries `CLAUDECODE=1` and `HC_SOCKET`, so the relaunch also gives it a clean environment. The command, run by the owner:

```text
/usr/bin/env -i HOME="$HOME" USER="$USER" LOGNAME="$USER" PATH="$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin" HC_SOCKET="$HOME/.local/run/herdr-core/default.sock" /usr/bin/open -a Herdr --stdout ~/Library/Logs/Herdr/herdr-app.log --stderr ~/Library/Logs/Herdr/herdr-app.log
```

Rules:

- **(a) Precondition.** `cutover.py baseline check` exits 0. The baseline was created at S2.1, and the old core is unchanged since (Codex round 11, finding 6).
- **(b) Quit first.** The owner quits the current window with Cmd-Q and confirms no Herdr process remains. `open -a` with Herdr already running only brings the existing window forward.
- **(c) After the relaunch.** `herdr-app ls` lists the same spaces as before, and there is still exactly one core, with no new listener at `~/.local/state/herdr-core/default/default.sock`. If either fails, stop and ask.
- **(d) Temporary value.** `HC_SOCKET` in this command is a pre-move value only. After S5 the window is started from the Dock with no `HC_SOCKET`.

Why `HC_SOCKET` is needed: `env -i` strips it. The window then looks at the default path, shows "needs herdr-core", or can start a second, empty core there.

Evidence (`verify-relaunch.txt` (local evidence), scratch core, `open -n`):

- Observed 2026-11-07: with `env -i` plus `HC_SOCKET` set to the old socket, the window attached, one core remained and nothing listened on the default path. Pass.
- Observed 2026-11-07: without `HC_SOCKET`, the window "did not answer". hc said "XDG_RUNTIME_DIR or HC_SOCKET differs from where the core started; set HC_SOCKET to the first path". `core.lock` named the live old socket, so no second core started, but the window was broken.

Limits:

- There is no launchd exit record and no automatic relaunch.
- Observed 2026-11-07: the premise is not proven. The `open --stdout` log was 0 bytes after 8 seconds, and earlier captures (S0 Q1, Q7) gave 0 to 1 lines at `HERDR_APP_LOG=info`. The window log may be empty at info level.
- So the primary crash evidence is the macOS crash report in `~/Library/Logs/DiagnosticReports/Herdr*`. The log file is secondary.

### The cutover, as stages

```text
S0 discover (read-only: answers Q1-Q9; fills the S0 results table)
 |   S1.1 is blocked until that table is filled
 |
S1 PR A: doctor + herdr hk step + /verify section + hc-safe
 |   S1.4 before commit: herdr-unit passes; doctor fails exactly {V10, V11} on the static checks
 |   -> merged, applied (dry run first)
 |   S1.6 live shells unchanged (socket/process checks or hc-safe only; sandbox-denied = BLOCKED)
 |
S2 red run: E6 -> cutover.py pre-move == stage-pass; V15 green
 |   S2.2 prove V1, V10, V15 can fail (scratch methods)
 |   Track W: owner quits the window and relaunches it from Terminal.app (rules a-d)
 |
S3 drain, one terminal at a time:
 |   fresh scrollback -> new MAINT-PRE token saved (or handoff + owner OK) -> close by explicit tab id
 |   T0 shells -> T1 idle -> T2 settled by owner -> T3 reach a clean point (A1 waits to finish)
 |
S4 snapshot: pids, holders, scrollback for every row, transcript sizes, resume commands, runbook
 |
S5 owner go (only if the V6 probe and Q1 are proven) -> quit all clients (S5.2 hard gate: no Herdr process remains) -> owner OK -> coordinator stops old core -> zero-core barrier
 |   -> owner starts new core (Dock click, else env -i hc server start) -> V6 probe
 |   -> cutover.py post-move (V3-V7) -> owner sees window
 |   -> S5.8 deploy codex-fnox change
 |
S6 resume T2/T3 one at a time: same space, tab, cwd, ID -> new MAINT-POST nonce after recorded size
 |
S7 /verify: E6 -> cutover.py post-cutover == stage-pass (only V10, V11 red); V9 from new shells; V12, V13; V14 reported
 |
S8 PR B: retired-project references, skill pins and hook, codex-fnox in git -> E6 -> /verify, cutover.py final == stage-pass
```

Each arrow is a check. A failed check stops the coordinator at that point. Nothing rolls back on its own: the owner chooses between the written fallback and the R5 rollback.

The checklist is built on four shared procedures in the runbook, and every step calls them instead of restating them:

- **P-SEND:** message only a confirmed agent;
- **P-RECOVER:** reopen the tab with resume argv, set a new history baseline, have the session read its handoff, then a fresh nonce, with an owner-approved replacement mapping as the fallback;
- **P-GATE:** the cutover script collects every receipt the stage needs, then gives the verdict;
- **P-IDENTITY:** the core baseline is created at S2.1 (`baseline init`), verified at W0 and S4.3, and changes only at an authorized transition that consumes a fresh zero-core barrier (S5.6 `--target default`, R5 `--target old`).

### Why each part is shaped this way

- **The checks run outside hc.** The failure being fixed is "a client can't reach the core". A checker that uses an hc client inherits the same failure and can start a second core while it tries.
- **The permanent part is small.** Only checks that stay true after the cutover live in the repo. Stages, receipts, the baseline and the barrier exist only for one move, so they stay local and are deleted with it.
- **PR A comes before the drain.** hk reads commit approval from the pinned Codex reviewer session's rollout (`python/repo/src/repotools/pane_approval.py:98-112`), and that session runs in a Herdr terminal. The drain closes terminals. As AGENTS.md says, each worktree has one pinned reviewer (`//repo:pane-pin`), resumed read-only (`codex resume <id> -s read-only`) for each commit in that worktree. The cutover is the one exception: the drain ends the PR A worktree's reviewer with every other terminal, and no commit is made during S5, when no core runs. So PR B's worktree pins its own reviewer in the new core, and resumes it for every PR B commit. (Corrected 2026-11-07: the C-M9 step "resume the reviewer after the move" had nothing to resume, because the reviewer pinned then had already been closed.) The checks must also be shown red on today's state before the move, or a green result after it proves nothing.
- **One stop, then a start from a clean environment.** The scratch test showed that programs can't survive a socket move. A stop and clean start is the one way to drop both `XDG_RUNTIME_DIR` and the inherited `CLAUDE_CODE_*` variables.
- **Resume by ID instead of keeping processes.** Claude and Codex both keep their history on disk under a session ID. The drain makes sure that history is current, so the restart costs only in-memory state that was checked as empty.
- **The coordinator runs outside the core.** This session's parent chain is Rex, not herdr-core, so it survives the stop. A pasteable runbook covers the case where it doesn't.

## Risks and Mitigations

| ID | Risk | Mitigation |
|---|---|---|
| R1 | A check starts a second core | The doctor never runs `hc` (V15). Other calls go through `hc-safe` with the deny-fork sandbox. |
| R2 | The coordinator's environment leaks into the new core | The owner starts it (Dock click or `env -i` fallback). V6 is checked at S5.6, with a restart branch. |
| R3 | A session is lost during the drain | Fresh scrollback, a saved nonce or accepted handoff, closing by explicit tab id only. |
| R4 | The new core fails to come up | Stop point at the failed check. The owner picks the fallback start or R5. |
| R5 | Rollback reconnects a client to the wrong core | See the paragraph below. |
| R6 | Relaunch without `HC_SOCKET` points at the empty default socket, giving the install screen or a second core | The Track W command sets `HC_SOCKET` to the old socket. Rules (a) to (d) check the core count before and after. |
| R7 | The window log is empty and the crash is not explained | Crash reports in `~/Library/Logs/DiagnosticReports/Herdr*` are the primary evidence. |
| R8 | The doctor's code drifts from the check table or breaks the 100% coverage gate | Tests for each `observe()` branch, real tools where a test can run them; the structural guard test for V15. |
| R9 | The current window (pid 37548, started 12:00:08) has `CLAUDECODE=1` and `HC_SOCKET=old` because it was relaunched from a Claude session (observed 2026-11-07). If it is still open when the core stops, it reconnects through `HC_SOCKET` and may autostart a core at the OLD path carrying `CLAUDECODE` | S5.2 is a hard gate: all clients are quit and no Herdr process remains before the stop. The pre-drain Terminal relaunch with `env -i` also clears this environment. |

**R5, rollback.** If the new core cannot be made healthy, the old-path core is rebuilt. Everything that could reconnect to a core is quit first: the window, Orca, CLion. The new core is stopped, and the cutover script records a zero-core barrier after the doctor shows no cores and no listeners. Only then is a core started at the old path, with `--accept-new-core --target old` replacing the baseline, and a fresh workaround window is launched last. A rollback that skips the barrier could leave two cores, so the script rejects a baseline change without its barrier record.

### Glossary

| Term | Meaning |
|---|---|
| Rex | The terminal host that runs the coordinator, outside herdr-core, so the coordinator survives the stop. |
| Reviewer pane | The pinned Codex reviewer session that hk asks for approval. It is a Herdr terminal and is closed by the drain. |
| Coordinator | The Claude session that runs the stages. |
| S0 to S8 | Cutover stages: discover, PR A, red run, drain, snapshot, stop and start, resume, green run, PR B. |
| P-SEND, P-RECOVER, P-GATE, P-IDENTITY | Shared procedures in the runbook. |
| E6 | Fresh V6 evidence collected before each gate. |
| R0 to R8, RW | Rollback steps in the runbook. |
| T0 to T3 | Session tiers (see the tier table). |
| Zero-core barrier | A record that no core and no listener existed, required before a new baseline. |
| Track W | The owner-run, logged relaunch before the drain. |
| V1 to V15 | The checks in the check table. |

## Alternatives Considered

Each alternative was weighed during the brainstorm, during the Codex review rounds, or in today's scratch tests. "Rejected by author" means the owner chose against it.

### Alternative A: Pin the socket in `~/.config/herdr-core/config.toml`

*   **What:** set `socket = "~/.local/run/herdr-core/default.sock"`. Every client, the Dock app included, would then find the running core.
*   **Pros:** no restart and no drain. Nothing is lost.
*   **Cons:**
    - It keeps the old path alive.
    - A global `socket` pin overrides `HC_SESSION`, so a test core started with only `HC_SESSION` would hit the real core (`paths.rs:28-34`).
    - The core keeps its inherited `CLAUDE_CODE_*` and `XDG_RUNTIME_DIR`.
    - The pin must be removed later, or it points at a dead socket.
*   **Reason for rejection:** Rejected by author. The goal is one socket path everywhere, a clean core environment and the old path retired.

### Alternative B: Reboot instead of an in-place stop

*   **Pros:** every app starts with a clean environment.
*   **Cons:** it closes everything on the Mac, and login items or restored windows could bring the old environment back. It kills working sessions mid-run unless they are drained first anyway.
*   **Reason for rejection:** Rejected by author. A stop plus a fresh start gives the same clean core with far less disruption.

### Alternative C: Keep the `open --env HC_SOCKET=...` workaround

*   **Pros:** nothing changes, and it works today.
*   **Cons:** every Dock launch fails and has to be repaired by hand. New shells still can't reach the core.
*   **Reason for rejection:** Rejected by author. It is the problem, not a fix.

### Alternative D: `launchctl setenv HC_SOCKET` or an `XDG_RUNTIME_DIR` LaunchAgent

*   **Pros:** the Dock app would inherit the right path with no core restart.
*   **Cons:** it is a global variable for every GUI app, used to fix one client. It has the same `HC_SESSION`-override problem as the pin.
*   **Reason for rejection:** rejected Nov 4 in the shared Claude/Codex review, and the author kept that decision.

### Alternative E: `hc server restart` in place

*   **Pros:** a single command.
*   **Cons:** it is refused when the caller's socket path differs from the core's (scratch test), and it would keep the inherited environment anyway.
*   **Reason for rejection:** it doesn't work across a path change.

### Alternative F: Move the core without a drain

*   **Pros:** fast.
*   **Cons:** a socket move ends every running program. In-flight work in 34 live terminals would be lost.
*   **Reason for rejection:** Rejected by author. "No work lost" is a hard requirement.

### Alternative G: A temporary symlink from the default path to the old socket

*   **Pros:** the Dock would work now, while the drain waits for A1.
*   **Cons:** unproven. hc may compare the `core.lock` path as a string, and a leftover link could block the new core's socket from binding.
*   **Reason for rejection:** not adopted. It could be tested on a scratch core if the wait for A1 becomes costly.

### Alternative H: Doctor checks that call `hc`

*   **Pros:** simpler checks, which ask the core directly.
*   **Cons:** an hc client starts a core when it can't connect, so a check could start the very second core it is meant to detect.
*   **Reason for rejection:** rejected in review. The doctor reads sockets and processes from outside, and calls that must go inside the core use `hc-safe`.

### Alternative I: Block autostart by denying the herdr-core binary in the sandbox

*   **Pros:** it looks targeted.
*   **Cons:** `hc` and the core are the same binary, so this also blocks every client call.
*   **Reason for rejection:** replaced by `(deny process-fork)`, tested on both start routes.

### Alternative J: Only a pre-check (listener pid) before each hc call, with no sandbox

*   **Pros:** no `sandbox-exec` dependency.
*   **Cons:** a race. If the core dies between the check and the call, autostart still happens.
*   **Reason for rejection:** Rejected by author in favour of the sandbox. It stays as the documented fallback if `sandbox-exec` ever disappears.

### Alternative K: Codex `shell_environment_policy.inherit = "all"`

*   **Pros:** config only, with no wrapper.
*   **Cons:** tool shells would see far more of the environment, including fnox-loaded secrets.
*   **Reason for rejection:** Rejected by author. codex-fnox drops only its `HC_SOCKET` line after the move.

### Alternative L: Window log through `launchctl setenv HERDR_APP_LOG`

*   **Pros:** the Dock icon keeps working as before.
*   **Cons:** `HERDR_APP_LOG` only sets the level, and the app writes to stdout. A Dock launch throws stdout away. It also changes every later GUI launch.
*   **Reason for rejection:** replaced by the owner-run Terminal.app relaunch with output redirected (Track W), and later by the LaunchAgent follow-up.

### Alternative M: A Dock launcher shim

*   **Pros:** every reopen would be logged.
*   **Cons:** a new app to maintain, which can drift from Herdr.app across updates.
*   **Reason for rejection:** Rejected by author.

### Alternative N: One dotfiles PR carrying everything

*   **Pros:** one review and one merge.
*   **Cons:** removing the `miserc.toml` mirror line changes mise behaviour, and skill hooks run on apply, both right before the riskiest step.
*   **Reason for rejection:** Rejected by author. PR A goes in before the move. PR B goes in after it.

### Alternative O: Replace the bundled `/verify` with a new committed file

*   **Pros:** a clean, herdr-only recipe.
*   **Cons:** `.claude/skills/verify/SKILL.md` already exists and holds the shell, python and jbctl checks.
*   **Reason for rejection:** Rejected by author. A herdr section is added to the existing file instead.

### Alternative P: Merge #394 (zero-bash Codex launcher) before the cutover

*   **Pros:** the launcher rewrite lands sooner.
*   **Cons:** #394 deletes codex-fnox and codex-hc, which S5.8 edits, R5 restores, and every Codex resume uses.
*   **Reason for rejection:** Rejected by author. #394 is held until the `final` gate passes.

### Alternative Q: Kill A1 now and resume it later

*   **Pros:** the move could happen today.
*   **Cons:** the 12:03 accident showed it loses in-flight subagent work.
*   **Reason for rejection:** Rejected by author. Wait for A1 to finish, or ask it to stop at its next clean point.

### Alternative R: Copy hc's socket resolver into the doctor

*   **Pros:** the doctor could compute the path for any environment.
*   **Cons:** a copy is pinned to one hc version and can be incomplete even at that version. It needs its own tests against a real hc, and it grows with every upstream change.
*   **Reason for rejection:** Rejected by author. V2 is green when no routing input is set, which needs no copy of the rules.

### Alternative S: mise `[doctor.checks]` for the herdr checks

*   **Pros:** the checks would run inside `mise doctor`.
*   **Cons:** the global pre-push hook runs `mise doctor` in every repo, so herdr checks there could block every push, in repos that have nothing to do with herdr.
*   **Reason for rejection:** Rejected by author. The doctor is a separate `mise run herdr:doctor`.

### Alternative T: One committed doctor for everything, including stages and receipts

*   **Pros:** one tool.
*   **Cons:** stages, receipts, the baseline and `--accept-new-core` serve one cutover. Committed, they need models, a schema and tests that outlive it, and the doctor would have to write files.
*   **Reason for rejection:** Rejected by author. They live in the local `cutover.py`.

### Alternative U: Run two cores side by side and move sessions gradually

*   **Pros:** no single hard stop; sessions could move one at a time.
*   **Cons:** two cores is the failure the doctor exists to detect. Terminals are owned by one core, so a session cannot move between them without ending. Clients choose a core by path, so both cores would be reachable from some shell.
*   **Reason for rejection:** not adopted. It adds the second-core risk (R1) for no saving, since each program restarts either way.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

Everything lands in `~/dev/github/ray-manaloto/dotfiles`, except the local cutover script and drain records, which hold private session names. Paths are relative to the repo root unless they start with `~`. There is no production code in this document.

The work follows the dotfiles repo's existing patterns:

- **File tasks** are thin Python launchers that hand off to the `hometools` package. The model is `unix/home/.config/mise/tasks/toolchain/verify`.
- **Tests** run through mise tasks (`//home:unit`). No bare `python`, `pytest` or `uv` is run.
- **No mocking.** Tests use the stand-ins in `python/home/tests/stand_in.py`.
- **hk mechanism.** One hk `herdr` step with deletion-aware selection, the pattern of the `home` step at `hk.pkl:79` and Codex r10-2: `glob = null`, plus a gate task that lists changed files with `git diff --cached --name-only --no-renames -z` (`python/repo/src/repotools/gates.py`). A deleted herdr file therefore still runs the step. There is no `--repo` mode on the doctor. The step runs `//home:herdr-unit` only. It is in both the common linters and the pre-commit override, with `profiles = List("!ci")`.

### PR A: lands before the drain (S1)

#### 1. `unix/home/.config/mise/tasks/herdr/doctor` (Create)

*   **Type / Scope:** mise file task, a Python launcher shaped like `tasks/toolchain/verify`.
*   **Proposed Changes:** `#MISE description="Check herdr-core and Herdr.app wiring without ever starting a core"`. It takes no stage flags. It runs the package environment's own python with `-I -B`, never uv and never a sync, so the run writes nothing; with no environment it exits 2 naming `mise run //home:sync`. Exit codes: 0, 1, 2, 3 as above.

#### 2. `python/home/src/hometools/herdr.py` (Create)

*   **Type / Scope:** Python module, the doctor's logic. Small and read-only.
*   **Proposed Changes:**
    - `observe() -> Observation`. It reads from outside only and never runs `hc`: `lsof`, `pgrep -a -f` on argv, `ps -o lstart=`, `core.lock` as a path, `lsof +D`, the app pid's environment (`sysctl` KERN_PROCARGS2), `launchctl getenv XDG_RUNTIME_DIR` (read-only), a login-shell probe under `sandbox-exec` after a plain-text tripwire scan of the zsh startup files (O3), both Info.plist files, and the config file for a `socket` key.
    - One function per check V1, V2, V3, V4, V5, V7, V10, V11, V15, each returning pass, fail or unknown.
    - The V11 allowlist table.
    - Output: one JSON line. It writes no file.

#### 3. `python/home/schema/hometools.schema.json` (Modify), then `models.py` (Regenerate)

*   **Proposed Changes:** `models.py` is generated, and `//home:lint` runs `codegen --check`. So define only `Command.herdr_doctor`, `Observation` and `DoctorReport` in the schema, then run `mise run //home:codegen`. There are no stage, receipt, baseline or target models.

#### 4. `python/home/src/hometools/cli.py` (Modify)

*   **Proposed Changes:** add `herdr-doctor` to the dispatch. Failures end with one `Failure` JSON line, as `toolchain-verify` does.

#### 5. `python/home/tests/test_herdr_doctor.py` (Create)

*   **Type / Scope:** unit tests under the 100% coverage gate (`--cov-fail-under=100` in `pyproject.toml`). Real lsof, ps, the kernel environment, sandboxed zsh and git on processes and files the test owns; `stand_in.py` only for pgrep and launchctl.
*   **Stand-in cases, one per `observe()` branch:**

| Branch | Stand-in case |
|---|---|
| lsof on the default socket | one holder; no holder; two holders |
| pgrep for the core | zero, one, two cores |
| ps start time | present; process gone |
| core.lock | names default; names old path; missing; unreadable (UNKNOWN) |
| old-path holders | empty; one or more holders |
| app environment | no `HC_SOCKET`; `HC_SOCKET` set; no app running; environment withheld by the kernel, as for a platform binary (UNKNOWN) |
| login-shell probe and `launchctl getenv` | `unset`; set; command fails (UNKNOWN) |
| routing inputs (V2) | none set (green); `HC_SOCKET`; config `socket` key; `XDG_RUNTIME_DIR`; non-default `HC_SESSION`; `XDG_STATE_HOME`; unreadable config (UNKNOWN) |
| Info.plist | both readable; missing; no version key (UNKNOWN); symlink target broken |
| skills (V10) | four present with matching tag; one missing; stale tag |
| references (V11) | clean; hit in allowlist; hit outside it |
| structural guard (V15) | `herdr.py` text names no `hc` program and no `subprocess` use with it; a planted reference fails |

#### 6. `python/home/tests/test_herdr_contract.py` (Create)

*   **Proposed Changes:** file-contract checks: the launcher has its `#MISE description` and hands off to `hometools herdr-doctor`; `.claude/skills/verify/SKILL.md` has the herdr section; `hc-safe` is Python, uses `subprocess.run` and contains `(deny process-fork)`.

#### 7. `unix/home/.local/bin/hc-safe` (Create) and its `[dotfiles]` link in the root `mise.toml`

*   **Type / Scope:** Python launcher, used by the coordinator and by `/verify`. Behavior, usage line and exit-code table are in the Technical Plan.

#### 8. `hk.pkl` (Modify)

*   **Proposed Changes:** add the deletion-aware `["herdr"]` step described above. The glob covers the herdr task folder, `hc-safe`, `herdr.py`, the herdr tests, the verify skill and the mise config. This sits near the #472 lane's `profiles = List("!ci")` change, and whichever PR lands second rebases.

#### 9. `python/home/mise.toml` and `python/home/pyproject.toml` (Modify)

*   **Proposed Changes:** a `herdr-unit` task that runs lint, then the two herdr test files with `--no-cov`, so it never shares coverage files with the home suite that hk may run beside it. The 100% gate stays on the full `test`, which `//home:check` runs. No `herdr_live` marker exists, because the live proofs now belong to the cutover script's scratch runs.

#### 10. `python/repo/tests/` hook-routing regression test (Create)

*   **Proposed Changes:** a test that `hk.pkl`'s pre-commit linters include the `herdr` step, and that deleting or changing only the doctor launcher, only `hc-safe` or only `herdr.py` selects the step.

#### 11. `.claude/skills/verify/SKILL.md` (Modify)

*   **Proposed Changes:** a "Herdr core" section. It runs `mise run herdr:doctor`, and for a cutover run it calls the cutover script's gate. It never sends to a shell and never runs bare `hc`. It reports SKIP for cutover-only checks when the drain folder is absent.

#### 12. `docs/agents/herdr-core.md` (Create)

*   **Proposed Changes:** how hc picks its socket; why the doctor never calls hc and reads versions from Info.plist; `hc-safe`; how to read the doctor's JSON; the test-core isolation rule; "never press Install it for me".

### Local, not in git: the cutover (S2 to S7)

#### 13. `~/.local/state/dotfiles/herdr-update-socket/drain-2026-11-07/cutover.py` (Create)

*   **Proposed Changes:** the script described in Components, with the command, file and exit-code contract in the brief's **P-CUTOVER** table (`concepts_brief.md` (local evidence)):
    - `baseline init` / `baseline check`;
    - `receipt v6|v8|v9|v12|v13`. The V6 receipt is bound by a nonce and by the same core identity before and after, because `hc-safe … exec` creates no terminal;
    - `barrier record --transition default|old`. Each barrier is consumed by exactly one committed transition;
    - `gate --expect <stage> … [--accept-new-core --target default|old]`, where stage `rollback` exists only for `--target old` (R5);
    - `recover`. An accepted transition is a journaled, all-or-nothing update: copy the old baseline, atomically rename the new one into place, then commit and consume the barrier. A `pending` journal blocks every other command until `recover` finishes or undoes it.

    A missing, stale or mismatched artifact is always `stage-fail`. The baseline is created at S2.1 and only verified after that. It also holds the scratch proofs that used to be committed live tests, run through the existing `//repo:scratch-env` (`python/repo/src/repotools/scratch_env.py`) with each case's `HC_SESSION`, `SSH_CONNECTION=hc-scratch` and routing variables, plus one added check that every scratch socket lies under the scratch root (C-M20): direct and launchd start blocked, control autostart, live calls work, V6 canary and negative control. It is checked by hand and by Codex, not by hk. The folder also holds the rebuilt `manifest.txt`, `scrollback/`, `handoff/`, `receipts/`, `snapshot/`, `resume-commands.md`, `rollback-commands.md` and `stage5-runbook.md`. It is never committed.

### PR B: lands after the `post-cutover` gate passes (S8)

#### 14. `unix/home/.local/bin/codex-fnox` (Modify)

*   **Proposed Changes:** remove only the `-c "shell_environment_policy.set.HC_SOCKET=..."` line. `HC_TERMINAL_SOCKET`, `HC_TERMINAL_ID`, `HC_SCOPE` and `HC_SESSION` stay. `~/.local/bin/codex-fnox` is a **symlink** (root `mise.toml:107`, `mode = "symlink"`) to `~/dev/github/ray-manaloto/dotfiles/unix/home/.local/bin/codex-fnox` in the main checkout, so there is no separate deployed copy (C-M23). S5.8 edits that one file in the main checkout, after saving a copy to the drain folder. PR B commits the same one-line change. The symlink must keep pointing at the main checkout, never at a worktree. Lines 2-5 (the comment) are updated in PR B only. Because the edit stays uncommitted in a checkout other sessions share, `cutover.py fnox check` (link target, 0 `HC_SOCKET` lines, recorded hash) runs before every Codex resume and at `post-cutover`. A freeze on `git stash/reset/checkout/switch/restore` in the main checkout lasts until PR B merges (side review, 2026-11-07).

#### 15. `unix/home/.config/mise/config.toml` (Modify)

*   **Proposed Changes:**
    - **(a) Skill pin:** line 519's skill hook pins `herdr-core#v0.1.18`, matching the installed hc. It updates an existing skill instead of skipping it, and installs into all four harness folders.
    - **(b) Comments:** lines 373 and 468 point at the issue in this repo, not at `knowledge-base #418`. Line 150's hk pin comment drops "(claude-code-marketplace D154)" (V11).
    - The LaunchAgent is not here. It is the follow-up in Non-Goals.

#### 15b. `python/tests/test_herdr_app.py` (Modify)

*   **Proposed Changes:** the skill-hook change breaks this test's offline fixtures. Provide the pinned `herdr-core#v0.1.18` offline repo in `setUp` for every hook test, add a test that an existing stale skill is replaced, and extend the expected folders and discovery to all four harness folders.

#### 16. `unix/home/.config/mise/miserc.toml` (Modify)

*   **Proposed Changes:** keep the `claude-code-marketplace/offline` entry at line 29 (owner decision). Only its comment changes, to say the project is retired and the folder is a read-only mirror that mise must never load.

#### 17. Retired-project references (Modify)

*   `mise.toml:74` (the comment "Marketplace saved searches"): reword so it doesn't name the retired repo as live.
*   Entries in the V11 allowlist table stay as they are.

#### 18. `~/.config/opencode/AGENTS.md` (outside the repo; owner decision)

*   **Proposed Changes:** remove the unmanaged leftover `mise:hc-codex` block at lines 1-3. This happens only with the owner's OK.

### Verification Plan

*   **Unit and contract tests:** `mise run //home:herdr-unit`, run by the hk `herdr` step on every commit touching herdr files. The full `//home:check` keeps the 100% coverage gate.
*   **Static analysis:** `ruff` and `ty` through the package's existing mise tasks.
*   **Pre-commit gate for PR A (S1.4):** `//home:herdr-unit` passes, and the doctor's static checks fail with exactly V10 and V11.
*   **Live shells unchanged (S1.6):** after applying PR A, one old-core Claude shell and one Codex tool shell pass socket and process checks or `hc-safe` calls. A sandbox-denied socket is BLOCKED, never a pass or a retry.
*   **Checks can fail (S2.2):** V1, V10 and V15 each go red under the scratch methods in the runbook's Testing strategy.
*   **Live gates:** the cutover script's stage gates at S2.1 and S4.3 (`pre-move`), S5.6 (`post-move`), S7.1 (`post-cutover`) and S8.3 (`final`). Each must give `stage-pass`.
*   **Done:** S8.3 gives `stage-pass` for `final`, and the owner confirms the Dock launch (V8) and that the sessions are back.
