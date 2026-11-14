---
name: herdr-shutdown
description: Prepare every herdr agent session for a Mac reboot or full stop and stop them one at a time in a safe order (roll:stop takes chief-of-staff first; run from its own tab, it skips that tab, which you /exit last by hand). Use when the owner asks to reboot, restart, shut down or "close everything" while lead/child Claude or Codex tabs are running in Herdr, when the Mac is frozen or out of memory/swap and a reboot is planned, or before any planned power-off — even if they only say "get the leads ready to restart". Pairs with herdr-startup, which reopens everything afterwards.
---

# herdr-shutdown

The coordinator (chief of staff) runs this. Goal: every agent session can be resumed exactly where it
stopped after a reboot, and nothing a session still needs is lost. The pairing skill `herdr-startup`
does the reverse.

Why the steps matter:
- A reboot ends every shell, background job and paused (SIGSTOP) process. Only conversation transcripts
  and files on disk survive, so each session must write down what it was doing.
- macOS clears `/private/tmp` at reboot, and every Claude session scratchpad lives under
  `/private/tmp/claude-501/`. Evidence and drafts kept there are lost unless copied out.
- Session ids are the only way back into the exact conversation. `mise run roll:snapshot` reads them from the
  live processes (`~/.claude/sessions/<pid>.json` for Claude, the open rollout file for Codex, the `-s ses_...`
  argv for OpenCode), so take the snapshot while everything is still running.

The steps are global mise tasks (`hometools roll`, `python/home/src/hometools/roll/` in dotfiles). Each prints its
plan and changes nothing without `--apply`; `--sessions a,b` and `--exclude c` pick spaces. Each `--apply` run logs
to `~/.local/state/dotfiles/roll/runs.jsonl` and `~/.local/state/dotfiles/roll/<run-id>/<step>.log`.

## Steps

1. **Pause heavy work.** `hc send` every lead and child: no new builds, test suites, mass deletes or scans.
   Check the foreground first (`hc get <t> --json`); a tab with an open question can't take a send — retry later.
2. **Ask for a Resume block.** Each lead adds `## Resume after reboot` at the top of its lane page
   (`wiki/lanes/*.md`): tab name (tNN), session id, cwd/worktree, branch, what is staged/uncommitted, the
   in-flight step, the next step, how to rerun any paused job, and the same for each child it supervises
   (keep or close). No commits, pushes or deletes. Each replies "ready for reboot".
3. **Save scratchpads.** Each session copies anything it still needs or cites from its scratchpad to
   `~/.local/state/scratch-keep/<tab-name>/` (`cp -R`, no deletes), updates the paths, and replies
   "scratch saved". Save your own the same way.
4. **Snapshot the graph** once everyone is ready: `mise run roll:snapshot --apply`.
   It writes `wiki/sessions/graph.json` (atomically, with a timestamped copy beside it) and `ledger.md` (space, tab, terminal, kind, session id, cwd, and
   which lane pages list it as a child) and prints `agents_without_session`, which must be empty. If a
   second map exists (e.g. herdr-ledger's `pre-reboot-snapshot.tsv`), diff the session ids against it.
   It also prints `work_elsewhere`: a worker session whose own checkout is clean while the worktree its lane
   bullet names has staged or uncommitted work (leads and `-coord` tabs are skipped; they belong in main). Ask
   that session's lead to confirm, then move the tab into that worktree (close with `--id`, reopen with the same
   `--resume`) before stopping the sessions, so the restore reopens it there. Closed projects are kept in the graph.
5. **Stop the sessions** — dry run first, then apply: `mise run roll:stop` then `mise run roll:stop --apply`.
   Each session is asked for a stop point (Resume block, then READY-TO-RESTART) and then sent `/exit`; its background
   work goes to the run folder's `background/`. Order, one session at a time: chief-of-staff first (the coordinator,
   found by name: its space and tab are both `chief-of-staff`), then each space's children before its leads (`-lead`,
   `-coord`, `-v2`). The tab running the task is never stopped: run from chief-of-staff's own tab, it skips that tab,
   so `/exit` chief-of-staff last, by hand. It never closes a tab, checks every terminal against `herdr-app ls` and
   its foreground against the harness right before acting, and leaves a session already current running.
6. **Tell the owner** the counts (sessions captured, sessions stopped), where the graph is, and the two
   commands for after the reboot:
   - close the chief of staff: `/exit` in its tab;
   - after the reboot, in Herdr: `claude --permission-mode auto --resume <coordinator session id>`,
     then say "run herdr-startup".

Never run `hc server stop`, never pkill/killall, and always pass `--id` to `herdr-app do`.
