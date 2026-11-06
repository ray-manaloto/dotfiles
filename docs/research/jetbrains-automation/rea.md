---
okf_version: "0.2"
type: "report"
title: "rea (REA) on CLion"
description: "Installing rea-agents, the three local patches that let it read CLion, what it exposes, and what it can't do."
resource: "https://github.com/morluto/rea"
version: "rea-agents 6.8.0"
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [rea, accessibility, macos, clion, reverse-engineering]
---

# rea on CLion

## Install

- `npm i -g rea-agents@6.8.0` into the mise Node prefix. Frida's install script was blocked by npm
  `allow-scripts` and left blocked.
- `rea setup --client claude_code` was **not** applied: the agent's permission check blocked it as
  self-modification. Its plan: add `mcpServers.rea = {command: <prefix>/bin/rea, args: ["mcp"]}` to
  `~/.claude.json`, and the skill `~/.claude/skills/reverse-engineer-anything`. The owner can run
  `claude mcp add --scope user rea -- <prefix>/bin/rea mcp`.
- `rea doctor`: the static engines (Hopper, Ghidra, IDA, JADX, Kuna) are not installed.

## Local patches (`jbctl/rea-native-ui-clion.patch`, reapply with `jbctl/rea-patch.sh`)

The patches are to `bridge/native/ReaNativeUI.swift`:
1. **Launch time**: `NSRunningApplication.launchDate` is nil for this CLion process, so fall back to
   `sysctl KERN_PROC_PID` `p_starttime`. Unpatched: `process-identity-unavailable`.
2. **Same-size windows**: CLion's project frames all share one geometry, so filter by AXTitle == CG
   window name. Unpatched: `ambiguous-window`.
3. **Swing labels**: JBR puts accessible names in AXDescription, so report it when AXTitle is empty.
   Unpatched, every label is null.

## What rea gives

- `observe-native-ui`: a complete map of a layer-0 window (Settings: 569 nodes, complete), with
  path, role, label, value, actions and child count.
- `capture-native-ui-scenario`: ordered `click` (AXPress), `scroll` (AXIncrement/AXDecrement),
  `key-entry` (set AXValue) and `wait` steps, each with before and after captures. None of them
  activate the app.
- Findings made with it:
  - Settings search navigation works in the background;
  - tree-row AXPress is inert in the background;
  - project-frame rows expose no actions;
  - Settings expandable rows expose AXPress;
  - the breadcrumb is a page check.

## What rea can't do (gaps for upstream)

- No `select` (AXSelected) step: the dropdown commit needs it.
- Windows with layer ≠ 0 are refused, so no popups or dropdown lists.
- No key events, by design.
- Frida: CLion has hardened runtime, no `get-task-allow`, and SIP is on, so it can't attach.
- The macOS AX backend is `bridge/native/ReaNativeUI.swift`, driven from
  `src/native/NativeUiObservation.ts`. It never activates the app. Allowed actions: press,
  increment/decrement, value (ReaNativeUI.swift:111-115 before patching).
