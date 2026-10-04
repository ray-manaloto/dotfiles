# Session autostart lane — why fan-out sessions parked or vanished, and the fixes (2026-10-03)

Lane: `dotfiles-20261003T103159.259690000-05.session-autostart`, branch
`feat/session-autostart-no-prompts`. Engine `claude --version` → 2.1.288. `$CC` =
`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.
Companion: `claude-code-expert-autostart-stall-review-2026-10-03.md` (binary-level read; its
"requester unattributed" for the coordinator kill is closed below).

Status: dag-tick fix IMPLEMENTED; launch-recipe, tmp-read and keep-alive items await the live
arms ("SLOT autostart"). This file is the incremental record; sections are appended as arms run.

## Working notes (verbatim from the lane's findings.md)

# Findings — session-autostart lane (2026-10-03)

CC=~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code ; engine 2.1.288

## Lifecycle (item 4 + coordinator addendum)
- $CC/agent-view.md:745-750 supervisor: a session "finished or waiting for your next message, and unattached for about an hour" has its PROCESS STOPPED; resumes on attach/reply. Working / paused on permission prompt / attached / PINNED (Ctrl+T) are not stopped.
- $CC/agent-view.md:136-138 sessions preserved across sleep; shutdown stops them (:806-).
- $CC/agent-view.md:914-917 limitation: sessions are local, preserved across sleep, stop on shutdown.
- $CC/cross-session-messaging.md:69 idle (live) session gets a new turn from a message; :266 inbox socket bound PER SESSION process. Hypothesis: an idle-reaped (stopped) bg session has no inbox socket => cross-session messages cannot reach/wake it. TO VERIFY with timeline + ListAgents.
- EVIDENCE coordinator 7541ae79: last turn ended 03:30:32Z (timeline state=done); ~/.claude/daemon.log:715 `bg settled 7541ae79 (killed)` at 03:31:28Z (56s later, NOT an idle retire); resumed only at 15:23:52Z `claimed-spare 7541ae79 (fleet)` (Ray attach). No kill/stop command in any transcript 03:29-03:32Z, none in ~/.zsh_history (Ray's shell `exit` at 01:37Z). OS log window 22:31:20-32 local has no line for the presumed host pid 52972 (control: pid 89113 present) — but host pid attribution is itself uncertain. => CAUSE UNATTRIBUTED; the condition has passed so this probe cannot speak to it. While stopped: no process => no inbox socket ($CC/cross-session-messaging.md:125 "appears only when it binds an inbox socket") => peers saw "no live coordinator".
- EVIDENCE lanes: daemon.log 06:05Z-12:33Z: `bg retire <id>: idle-prompt, idle 8h` (e686b1fe, 88910d3b, 45bec37a, a6fef20a, 9652109a, a0d2bdd6, 6fae0fec) and `retire <id>: settled, idle 8h` (ec69effd, 53b8d22d, 5361f892, dc62b079, b7d40872). So the supervisor retires a bg worker after 8h idle, INCLUDING ones sitting on a prompt (`idle-prompt`; 6fae0fec llvm lane state=blocked). Docs ($CC/agent-view.md:745-748) say ~1h for done/unattached and that permission-prompt sessions are kept — observed engine 2.1.288 retires both at 8h. Pin (Ctrl+T in agent view, $CC/agent-view.md:257,305) is the only documented keep-alive; no CLI/settings key found.

## Item 1 — EnterWorktree outside .claude/worktrees
- $CC/worktrees.md:43 + $CC/tools-reference.md:31: entering a path outside `.claude/worktrees/` ALWAYS prompts; "An EnterWorktree permission rule or 'don't ask again' doesn't suppress this prompt; only bypassPermissions skips it" (since v2.1.206; changelog.md:2015). => NO allow-rule/setting fix exists.
- $CC/agent-view.md:494-497: bg isolation is SKIPPED when the session is already inside a linked git worktree "whether Claude created it under .claude/worktrees/ or you created it with git worktree add somewhere else". So a lane launched with cwd=its sibling worktree never NEEDS EnterWorktree.
- Root cause of the 7 parked lanes: the bg-session system prompt says "use EnterWorktree ... unless your cwd is already under .claude/worktrees/" — a sibling worktree is not under that path, so the model calls EnterWorktree(path=its own cwd / sibling) -> prompt. Fix candidates: (C, narrowest) launch flag `--disallowedTools EnterWorktree` so the tool doesn't exist for lanes; (A) project deny `EnterWorktree` — breaks main-checkout bg sessions that need it to edit; (B) move lane worktrees under `<repo>/.claude/worktrees/` — design fork.

## Item 2 — reading own bg-task output
- EVIDENCE audit-000 (7934b36e, mode=auto): 00:49:48Z Bash `cp /private/tmp/claude-501/<proj>/<session>/tasks/aad77cd4d3494a2c5.output /Users/rmanaloto/.claude/jobs/7934b36e/tmp/...` -> prompt "outside the allowed working directories", answered by Ray, result at 00:59:57Z (10 min parked). Tool was BASH (cp), not Read.
- No native setting makes Bash `cp` of a path outside working dirs auto-approved in auto mode except widening working dirs (additionalDirectories) or an allow rule; whether `Read(//private/tmp/claude-501/**)` covers a Bash cp source arg in auto mode is UNPROVEN -> needs live arm. `CLAUDE_CODE_TMPDIR` cannot be set from project settings env (changelog.md:869); user/shell only.
- Coordinator 15:4xZ: claude-code-expert review is landing at docs/research/kb/reports/agents/claude-code-expert-autostart-stall-review-2026-10-03.md — input; wait for it before finalizing.

## Item 3 — workspace trust
- $CC/permissions.md:648: in a worktree, trust is keyed on the MAIN checkout's root. ~/.claude.json: dotfiles=True, knowledge-base=True (parent ray-manaloto=True). => sibling worktrees inherit trust; no trust dialog for new lane worktrees. No change needed. (Arm: the throwaway lane must reach a tool call.)

## Coordinator asks (a) keep-alive while waiting for GO, (b) detector + relaunch
- (a) EVIDENCE: the watch session 998ab91b (`/loop 10m`) ticked every 10 min from 03:01Z through 15:30Z, never retired (no `retire 998ab91b` in daemon.log), while 12 idle lanes were retired at idle 8h. $CC/agent-view.md:~124 + state table: a /loop session sleeping between iterations counts as `working`. => a lane parked for a GO stays alive if it ends its turn under a self-wake (/loop or session cron), at a token cost per tick. Retire classes seen: `settled` (turn done, waiting for next message = waiting on GO) and `idle-prompt` (parked on a permission/dialog).
- (b) NATIVE relaunch exists: `claude respawn <id>` "Restart a session, running or stopped ... resumes its saved conversation" ($CC/agent-view.md manage-sessions table). Also attach/reply resumes a stopped session. A retired session has no inbox socket, so SendMessage cannot wake it. Detector = compare `claude agents --json --all` (rows with state but no `pid`) to the lane manifest, then `claude respawn <id>`. Needs a live arm on a throwaway: retire can't be forced quickly, so use `claude stop` + `claude respawn` as the proxy and say so.
- A KILLED coordinator (7541ae79, `settled (killed)`) ≡ stopped; it is respawnable by id too (Ray's attach at 15:23Z did that). Peers can't wake it; only respawn/attach.

## ROOT CAUSE of the coordinator kill: OUR OWN dag-tick watchdog (CONFIRMED)
- LaunchAgent `dev.mise.dotfiles-dag-tick` IS LOADED (`launchctl list`; plist in ~/Library/LaunchAgents), firing `mise run dag-tick` every 60s from the dotfiles MAIN checkout (mise.toml [tasks.dag-tick] ~:710, [bootstrap.macos.launchd.agents.dotfiles-dag-tick] ~:1560). python/src/dotfiles_setup/dag_tick.py:8-10: "`claude stop` for a DONE node whose process is still lingering".
- ~/Library/Logs/dotfiles-dag-tick.log (no timestamps) STOP sequence: ... 5b131dfd, 98eb9783 ×2, 299c066f, fa4a142a, 98eb9783 ×2, 7541ae79 ×2 (:71486-87), 5b131dfd (:71643), 7541ae79 (:71880). daemon.log `(killed)` sequence: 5b131dfd 18:49, 98eb9783 19:08/19:30, 299c066f 20:09, fa4a142a 21:37, 98eb9783 21:54/21:55, 7541ae79 22:02/22:03, 5b131dfd 00:38, 7541ae79 03:31:28. ORDER MATCHES one-to-one for every dag-tick STOP. Control: the 02:52-02:55 kills (coordinator probes, stopped by the coordinator itself) have no dag-tick STOP line.
- Mechanism: a coordinator that ends a turn waiting for messages reads `state=done`; dag-tick's DONE class + lingering pid => `claude stop` => process gone => no inbox socket => peers "not reachable" for 12h. The census is `--cwd <main checkout>`, so lanes in sibling worktrees were NOT stopped by it (their loss is the native 8h retire).
- Expert report (claude-code-expert-autostart-stall-review) listed the requester as unattributed (agent-view x / claude stop / RC) — this closes that SUSPECT.
- dag-project (dev.mise.dotfiles-dag-project): only `gh` label/comment calls (dag_project.py:33-37, :566); never claude stop/respawn/rm. No kill path.
- dag_tick fix: STOP removed; tests 275 passed rc=0; mutation arm (HEAD dag_tick.py) -> new test FAILS with [['claude','stop','done1']] rc=1; restored.

## GitHub repos touched

_None so far._ Local binary logs, transcripts, launchd logs and offline docs only. The
research sweep (`research-sweep-autostart-2026-10-03.md`) carries its own enumeration.
