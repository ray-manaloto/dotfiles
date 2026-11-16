---
okf_version: "0.2"
type: "report"
title: "Claude Code /restart for the rolling restart"
description: "What a probe and the 2.1.325 binary show about /restart, and how the rolling restart uses it for a session with Remote Control off."
---

# Claude Code `/restart` for the rolling restart

Claude Code 2.1.325, probed 2026-11-15 on one throwaway Haiku test tab (Remote Control off, opened by the guarded
test-tab launcher without its `--tools` flag). The roll uses it for a session it can restart in place; every other session keeps
the handshake, `/exit` and resume by `roll:start`.

## What a probe showed

- `/restart` restarts the session in its own process: the pid, `ps` start time and the session record's
  `procStart` stay the same. The screen said "Session resumed".
- What changes: `startedAt` in `~/.claude/sessions/<pid>.json` (milliseconds since the epoch) moves to the
  restart, and the argv gains `--resume <session id>`.
- The environment survives (the tab's exported `HC_TERMINAL_ID` was still set), and so do `--settings`,
  `--model`, `--effort`, `--permission-mode` and the plugin folders.
- `-n` is not carried over: a name the user gave the session can be lost.
- A session with no conversation yet came back as a new session.
- It refuses under a `--tools` allowlist.

## What the binary's strings say (not confirmed by a run)

- It restarts on the installed version: its messages include "Can't restart on the installed version", "The
  installed version wasn't found" (`no_launcher`) and the event `tengu_update_relaunch`. No newer version was
  installed during the probe, so a version switch is unproven: the roll checks the record's `version` against the
  installed one after every restart.
- It refuses, leaving the session as it was, while Remote Control is connected, for a version on hold, for a
  launch file it can't read, for an unsaved session or a missing folder, over Remote Control, and for a session
  with restrictions a restart can't carry over (a tool allowlist). The refusals the roll recognises contain "Can't
  restart", "Couldn't restart", "/restart isn't available", "Can't switch to the new version" or "Couldn't save this
  session to disk"; the roll counts only one below the handshake's answer, which carries a token new to each
  attempt, so a refusal left on the screen by an earlier attempt is never taken for this one.
- Unprobed: `/restart` with a scheduled task or a background job running (`active_tasks` appears in the strings).

## How the roll uses it

`roll:stop` restarts in place only a Claude session whose record has `bridgeSessionId` null (Remote Control off)
and a `nameSource` other than `user`: today, a `claude:code-mode` session, which the `/exit` path skips because
its resume would lose Code Mode's variable. After the handshake it sends `/restart` untagged, and the result is
`restarted` when the record shows a later `startedAt` with the same `sessionId` and name; `failed-name-lost` or
`failed-session-changed` otherwise, and `skipped-restart-refused` (with the refusal line) when the screen shows
one. A refusal never falls back to `/exit` in the same run.

Since `/restart` keeps the process and its `ps` start time, `roll:stop` takes a Claude session's start time as the
later of that and its record's `startedAt`, so a session restarted after the plugins changed is current on the
next roll.

`roll:start` resumes nothing for a restarted session. `roll:verify` checks it by its record instead of a resume
prompt: `startedAt` after the plugin mark, the same `sessionId`, the installed `version`, and `--resume <session id>`
in its argv, plus the usual dialog and folder checks.
