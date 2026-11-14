---
name: herdr-startup
description: Reopen every herdr space, tab and agent session after a Mac reboot or a herdr-shutdown, resuming each Claude/Codex conversation exactly where it stopped, then verify and restart the coordinator's check-ins. Use when the owner says the Mac is back, "resumed", "start everything again", "restore the leads", or after herdr-shutdown ran — even if they only ask to "bring the tabs back".
---

# herdr-startup

The coordinator runs this right after the owner resumes it (`claude --permission-mode auto --resume <id>`).
Input: `wiki/sessions/graph.json`, written by `mise run roll:snapshot --apply` before the reboot, and the run folder
`~/.local/state/dotfiles/roll/<run-id>/` that `roll:stop` wrote. The steps are global mise tasks (`hometools roll`);
without `--apply` each prints its plan and changes nothing.

## Steps

0. **Read the trackers first:** `wiki/sessions/open-issues.md` (every open issue) and `wiki/sessions/on-restore.md`
   (messages to send each project when it is restored).
1. **Check herdr is up.** `hc server status` and `herdr-app ls` must answer. If the core is down, ask the
   owner before `hc server start`; never `hc server stop`.
2. **Dry run:** `mise run roll:start --prompt reboot`. Read the plan: one line per agent session, resumed by
   session id (`claude --resume <id> "<resume prompt>"`, `codex-hc resume <id>`, OpenCode under its fnox proxy
   launcher with `opencode --standalone -s <id>`) in its own folder. Shells are not reopened. The tab running the
   task is skipped; you are already running. It resumes every chosen session of the saved graph (the last stop's
   run, else `wiki/sessions/graph.json`), stopped or not; a project closed before the snapshot comes back only when
   `--sessions` names it. `--sessions dotfiles,glaze-fix` restores just those spaces (bring one
   project back first, e.g. while a fix lands); run the rest later with the other names.
3. **Apply:** `mise run roll:start --prompt reboot --apply`. It reuses spaces and tabs by name, types the resume
   command into a tab whose terminal is a bare shell, and otherwise opens a new tab (or space). It exits non-zero
   on `failed-wrong-folder`: a session herdr opened in another folder (a new space's first tab can inherit the
   previous space's folder). Have that session reach a stopping point, then
   `herdr-app do tab.close --id <tab> --confirmed true` and `tab.new` in the right folder with the same resume argv
   (`hc send` cannot run `/exit`: it arrives as chat).
4. **Verify each agent.** `mise run roll:verify --prompt reboot` (with the same `--sessions` as the start): every
   session the start resumed from the saved graph runs, is current, got its resume prompt, waits on
   no trust or other dialog (Codex "Trust this folder": ask the owner first) and is in its folder. Re-send the prompt with
   `hc send` where it did not arrive. Codex reviewer panes: re-pin with `repotools pane-pin` if the session
   id changed.
5. **Restore your own duties:** re-create the 30-minute check-in cron from
   `wiki/playbooks/restart-chief-of-staff.md`, confirm the mods loaded (side-notes log for your session), and
   update tab ids in the leads' briefs if they changed.
6. **Report to the owner:** sessions resumed vs in the graph, anything skipped and why, tabs waiting on the
   owner. Then tell leads that heavy work may resume only if memory and swap are healthy
   (`sysctl vm.swapusage`).

One chief of staff, ever: resume it by name (`claude --permission-mode auto --resume chief-of-staff "/herdr-startup"`), never start a second one.

## Rolling restart (no reboot): update every harness and load it

`mise run roll:all` updates Claude Code, Codex, OpenCode, agy and every marketplace and plugin, then restarts each
session one at a time without stopping work. Steps (each also a task of its own: `roll:snapshot`, `roll:update`,
`roll:review`, `roll:stop`, `roll:start`, `roll:verify`):

1. snapshot: graph.json and the installed versions, into the run folder `~/.local/state/dotfiles/roll/<run-id>/`.
2. update: `update:claude`, `update:codex`, `update:agy` and `agents:update` (with `--skip opencode` while an
   excluded OpenCode session runs).
3. review: the changed items' release notes, one budget-capped Claude triage, written to `<run-id>/review.md`. A
   BREAKING item pauses `roll:all` before any session stops; read review.md, then rerun with `--accept-review`.
4. Per session: stop (left running when already current; foreground and busy gates, the stop-point handshake: the tab writes its Resume block and ends with
   READY-TO-RESTART or BUSY-KEEP-ME, both gates again, `/exit`), start (same tab, same session id), verify (also that
   the worktree's git status is as stop recorded it). Busy and
   BUSY-KEEP-ME tabs are skipped and listed; never interrupt them, and retry them later.

Order: chief-of-staff first. It records its background jobs and crons in the run folder (`background/`), exits,
and is resumed by name in its own tab: `claude --permission-mode auto --resume chief-of-staff "/herdr-startup rolling"`.
`roll:all` touches no space until it verifies. Then each space, its children before its leads.

Dry run first: `mise run roll:all` (add `--exclude <space>` to leave a project alone; its sessions are reported
`untouched` by their unchanged pid). Then, from a herdr tab of its own named `roll` (not a child of chief-of-staff,
so it survives chief-of-staff's exit):
`herdr-app do tab.new --space <space id> --name roll --folder ~ --argv '["env","MISE_TASK_TIMINGS=1","MISE_TASK_OUTPUT=prefix","mise","run","roll:all","--apply"]'`.
`roll:all --apply` refuses to run anywhere else.

### `/herdr-startup rolling`: chief-of-staff after its restart

1. Read the newest `~/.local/state/dotfiles/roll/<run-id>/review.md` and send the owner its BREAKING and REVISIT
   items.
2. Read `<run-id>/background/chief-of-staff--chief-of-staff--<session>.json` and re-arm what it lists (crons, loops,
   monitors), with the playbook `wiki/playbooks/restart-chief-of-staff.md`.
3. Watch the `roll` tab (`hc read`) until `roll:all` ends, then report its `failed-*` and `skipped-*` sessions.

Found 2026-11-11: a session-only cron **survives `claude --resume` of the same session**. The chief-of-staff's
old check-in cron fired again after its rolling restart. After a resume, run CronList before re-creating a cron,
and delete duplicates and stale ones (CronDelete), so a check-in doesn't fire twice.

## What changed from the old scripts

The tasks replace `herdr-shutdown/scripts/{snapshot,close}.py` and `herdr-startup/scripts/{restore,roll,checks}.py`.

- Codex and OpenCode sessions are stopped and resumed too, not only Claude.
- "Coordinator" means chief-of-staff by name (space and tab both `chief-of-staff`), never the tab that runs a step.
- Dropped: `checks.py graph`, `busy` and `versions` (now `roll:snapshot`, the busy gate in `roll:stop`, and
  `roll:verify`) and its `--ignore-footer`; `restore.py --list` (the spaces are in `ledger.md` and `graph.json`) and `--only`
  (pick spaces with `--sessions`; there is no per-terminal pick). A tab with several terminals is no longer reopened
  as one tab per terminal: start types into the session's own terminal, and a tab of the same name holding more than
  one terminal is `skipped-moved`.
- Kept: the proof that the worktree is unchanged, as `roll:verify`'s git status check against what `roll:stop`
  recorded.
