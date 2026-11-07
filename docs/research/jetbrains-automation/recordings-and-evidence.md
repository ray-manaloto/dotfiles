---
okf_version: "0.2"
type: "report"
title: "Recordings and evidence"
description: "What was recorded while the owner changed the setting by hand and during the agent runs: AX notifications, input events, video, agent-desktop traces."
resource: "spike working folder (local, untracked)"
version: "2026-11-05"
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [recording, accessibility, macos, evidence]
---

# Recordings and evidence

## Recorders

- `axwatch <pid>` (spike probe): an AXObserver for 18 notifications (focus, value, menu, window created,
  selection, …), plus a 250 ms poll of the combo value and Apply's enabled state. Text from windows
  other than Settings and its popups is written as `<redacted>`.
- `inputtap <pid> <x> <y>` (spike probe): a listen-only CGEventTap. It logs only events delivered to CLion, and
  keys only as keycodes plus modifiers. Input Monitoring was already granted.
- `screencapture -v -k -V 900 -R<window rect>`: the Settings rectangle, so the separate popup window
  is included. A background job ignores SIGINT; let `-V` end it.
- An agent-desktop session with `--screenshots`. `AGENT_DESKTOP_HOME` was set to a folder inside the working folder, so
  its artifacts stay local; the directory must be 0700. A `snapshot` every 2 s.
- agent-desktop's trace logs only agent-desktop's own commands. It cannot see the owner's input.

## The owner's keyboard run (AX and input logs)

| t (s) | input | AX | effect |
|---|---|---|---|
| 263.12 | click on the combo | AXWindowCreated (popup, AXUnknown) + AXMenuOpened | the list opens; focus is on the combo |
| 264.38 | key 126 (Up) | AXSelectedChildrenChanged on the combo | highlight → row 0 |
| 265.37 | key 36 (Return) | popup destroyed | commit; Apply enabled at 265.63 |
| 280.05 | click on Apply | focus → Apply → OK | Apply disabled at 280.15 |

- The owner's earlier mouse run was reverted before Apply. The rows were at window y≈128 and 153,
  with the list anchored at screen y≈329.
- The agent-desktop headed test showed the same pattern: AXMenuOpened plus a focus change on the
  mouse-click, and Apply enabled after Up/Up/Return.
- Event sources: the owner's events have `src_pid=0`; agent-desktop's mouse-click carries its own
  pid. Keys from `press` (CGEventPostToPid) **never pass the session event tap**, yet Swing got them.
- Up twice from "All agents" ended on row 0, so the list does not wrap.

## Files

The video, AX and input logs, screenshots, agent-desktop traces and rea maps stayed in the spike's local
working folder. They are not tracked, because they show window contents and project text.
