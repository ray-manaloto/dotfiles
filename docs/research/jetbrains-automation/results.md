---
okf_version: "0.2"
type: "report"
title: "Results: setting CLion's MCP router-only mode to DIRECT"
description: "Every route tried to change Exposed Tools router-only mode, which worked, what stayed in the background, and how each was verified."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "CLion 2026.3 / agent-desktop 1.2.0 / rea-agents 6.8.0"
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [clion, jetbrains, macos, accessibility, agent-desktop, rea, mcp, swing]
---

# Results (2026-11-05)

## The setting

- Settings › AI › MCP Server › Exposed Tools › **"Enable router-only mode for:"** is a JComboBox
  exposed as AXPopUpButton. It has two rows: **row 0 "ACP agents only"** (DIRECT) and **row 1 "All
  agents"** (VIA_ROUTER).
- It is stored in `~/Library/Application Support/JetBrains/CLion2026.3/options/mcpToolFilter.xml` as
  `invocationMode`. DIRECT is the default: when DIRECT is saved, IntelliJ **deletes** the file.
  `CLion2026.2/…` is a stale older config dir.
- The file is written on save (at OK, or when settings are flushed), not on Apply.
- **Ground truth:** MCP `initialize` + `tools/list` on the IDE's own endpoint (`jbctl resolve`; CLion's was `127.0.0.1:64362/stream`), no tool calls.
  VIA_ROUTER returns 1 tool (`execute_tool`); DIRECT returned 88.

## Routes

| route | CLion forward? | result | evidence |
|---|---|---|---|
| owner by hand: click, Up, Return, Apply | yes | ✅ | Apply enabled 0.25 s after Return; tools/list 88 |
| agent-desktop headed: `--headed mouse-click --xy` on the combo centre, `press up/up/return`, AXPress Apply, AXPress OK | yes | ✅ | 15:47; `mcpToolFilter.xml` deleted at OK |
| agent-desktop headed `click @combo` (ref form) | yes | ❌ safe failure | actionability `stable` failed; "Physical input target could not be proven"; no click sent |
| foreground headless: `focus-window`, `press tab` (focus → combo), `space`, `down`, `return` | yes | ✅ value changed | AXFocusedUIElementChanged → combo; Apply enabled |
| **background: AXSelected on combo child 0, then AXPress OK** | **no** | ✅ | 16:05, Herdr frontmost throughout; tools/list 1 → 88 |
| background `select` / `focus` / AXPress on hidden popup rows | no | ❌ | `select` not supported; focus not granted; row press only highlights |
| background `press` keys | no | ❌ | Java focus owner is null while inactive; keys go nowhere |
| `jbctl settings router-direct` (rea-based) | only to open Settings, ~1.2–2.7 s | ✅ | 88 tools; Herdr frontmost at the end |

## What works in the background (CLion inactive)

- AXPress on buttons, links and checkboxes: Apply, OK, Cancel.
- AXValue writes to text fields, including the Settings search field. That makes it the
  **navigation route**.
- AXSelected on the combo's popup child: commits **row 0 only**.
- Reading anything over AX. Screenshots of a background window with `screencapture -l <CGWindowID>`.

## What needs CLion in front

- Opening Settings: AppKit drops the menu AXPress while the app is inactive. The shortest route is
  `open-settings.sh`, ~1.2 s.
- Any keyboard input: Tab, Return, arrows, shortcuts.
- Running a row in a popup or list (ListPopup runs rows only on Enter or a real click).
- Choosing dropdown rows other than 0.

## Gotchas found

- Apply's enabled state is **not refreshed while CLion is inactive**. Use OK, which applies every
  modified page itself.
- The AX value of the combo can go stale. AXSelected on a hidden popup row changes AX but not Swing.
  After real Swing changes, AX tracked correctly. Verify with a window screenshot or the external
  ground truth.
- A second process named "clion" (`clion stdioMcpServer`, started by an MCP client) makes
  `--app CLion` ambiguous. Use the pid, the bundle id or `--window-id`.
- Each Settings opening gets a new window id.
- The owner's terminal app tends to take the front back between commands. Keep `focus-window` and
  keys in one `batch`.
