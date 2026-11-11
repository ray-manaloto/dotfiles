---
name: herdr-startup
description: Reopen every herdr space, tab and agent session after a Mac reboot or a herdr-shutdown, resuming each Claude/Codex conversation exactly where it stopped, then verify and restart the coordinator's check-ins. Use when the owner says the Mac is back, "resumed", "start everything again", "restore the leads", or after herdr-shutdown ran — even if they only ask to "bring the tabs back".
---

# herdr-startup

The coordinator runs this right after the owner resumes it (`claude --permission-mode auto --resume <id>`).
Input: `wiki/sessions/graph.json`, written by `herdr-shutdown/scripts/snapshot.py` before the reboot.

## Steps

0. **Read the trackers first:** `wiki/sessions/open-issues.md` (every open issue) and `wiki/sessions/on-restore.md`
   (messages to send each project when it is restored).
1. **Check herdr is up.** `hc server status` and `herdr-app ls` must answer. If the core is down, ask the
   owner before `hc server start`; never `hc server stop`.
2. **Dry run:** `python3 -I ~/.claude/skills/herdr-startup/scripts/restore.py`. Read the plan: one line per
   tab, agents resume by session id (`claude --resume <id> "<resume prompt>"`, `codex-hc resume <id>`),
   shells reopen plain, shells in folders the reboot removed (scratchpads under `/private/tmp`) are skipped.
   The coordinator's own tab is skipped; it is already running.
   To restore only some projects: `--list` shows the spaces in the graph, `--spaces dotfiles,glaze-fix`
   restores just those (use it to bring one project back first, e.g. while a fix lands), `--only t26j` picks
   single terminals by their old address. Run the rest later with the other space names.
3. **Apply:** `restore.py --apply`. It reuses spaces by name (creating missing ones), types the resume
   command into a tab herdr already restored with an idle shell, and otherwise opens a new tab. A
   multi-pane tab comes back as separate tabs (`<name>-2`, ...). Its report ends with `wrong_folder`: any
   session herdr opened in another folder (a new space's first tab can inherit the previous space's folder).
   Have that session reach a stopping point, then `herdr-app do tab.close --id <tab> --confirmed true` and
   `tab.new` in the right folder with the same resume argv (`hc send` cannot run `/exit`: it arrives as chat).
4. **Verify each agent.** `hc ls`, then `hc read <t>` per agent tab: the resume prompt arrived (turn ≥ 1)
   and it is not stuck on a dialog (Codex "Trust this folder": ask the owner first). Re-send the prompt with
   `hc send` where it did not arrive. Codex reviewer panes: re-pin with `repotools pane-pin` if the session
   id changed.
5. **Restore your own duties:** re-create the 30-minute check-in cron from
   `wiki/playbooks/restart-chief-of-staff.md`, confirm the mods loaded (side-notes log for your session), and
   update tab ids in the leads' briefs if they changed.
6. **Report to the owner:** sessions resumed vs in the graph, anything skipped and why, tabs waiting on the
   owner. Then tell leads that heavy work may resume only if memory and swap are healthy
   (`sysctl vm.swapusage`).

One chief of staff, ever: resume it by name (`claude --permission-mode auto --resume chief-of-staff "/herdr-startup"`), never start a second one.

## Rolling restart (no reboot): load a new Claude Code or new plugins

Use this when Claude Code or the marketplaces/plugins were updated and every session must pick them up, one tab
at a time, without stopping work. Scripts in `scripts/`:

- `checks.py versions`: per Claude tab, is it on the installed version and did it start after
  `installed_plugins.json` last changed? Exits 1 when any tab is stale.
- `checks.py busy`: per agent tab, its status and any background jobs. MCP servers and LSPs don't count. A tab
  is safe to restart only when it is done or idle and has no jobs.
- `checks.py graph`: live tabs ↔ `graph.json` ↔ lane pages. Run `herdr-shutdown/scripts/snapshot.py` first,
  because tab ids change on every restore.
- `roll.py --spaces a,b`: dry run of the order (each space's children first, its lead last) and who is safe
  now. `--apply` restarts each tab in place:
  1. busy gate
  2. stop-point handshake (the tab writes its Resume block and ends with READY-TO-RESTART, or BUSY-KEEP-ME)
  3. busy gate again
  4. `/exit`
  5. `restore.py --apply --rolling --only <t>` (same tab, same id)
  6. versions check

  Busy and BUSY-KEEP-ME tabs are skipped and listed; never interrupt them, and retry them later.

Order:
1. **Chief of staff first, by the owner.** Before it exits, it records its own background jobs and
   crons in `wiki/playbooks/restart-chief-of-staff.md` (they die with it). The owner then runs /exit and
   `claude --permission-mode auto --resume chief-of-staff "/herdr-startup rolling"`, and it re-arms them.
2. **Then each space,** one at a time. Restart a lead only when its children are done.

Codex tabs are left alone; they don't load Claude plugins. Run `checks.py versions` at the end; it should
report `stale: 0`, apart from the tabs that were skipped.

Found 2026-11-11: a session-only cron **survives `claude --resume` of the same session**. The chief-of-staff's
old check-in cron fired again after its rolling restart. After a resume, run CronList before re-creating a cron,
and delete duplicates and stale ones (CronDelete), so a check-in doesn't fire twice.
