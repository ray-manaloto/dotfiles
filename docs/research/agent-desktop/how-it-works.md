---
okf_version: "0.2"
type: "report"
title: "How agent-desktop works on macOS"
description: "The observe, ref, act, verify loop, headless vs headed, key input, focus and permissions, from source."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# How agent-desktop works on macOS

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Source: repo at main 6660fba (v1.1.0 + 5 commits). Tags: [code] [docs] [both] [inferred].
Reader pages: [actions](actions-and-delivery.md), [input and focus](physical-input-and-focus.md), [tree and surfaces](tree-refs-and-surfaces.md), [documented limits](documented-behaviour-and-limits.md), [setup](install-permissions-and-setup.md), [JetBrains side](jetbrains-side.md).

## The loop: observe, ref, act, verify
1. Observe. `snapshot` reads the Accessibility (AX) tree of a window or a surface (menubar, sheet, popover, ...). Reads do not need the app to be frontmost (crates/macos/src/tree/surfaces.rs:17-28; no frontmost check in read paths) [code].
2. Ref. Interactive elements get refs like `@e12`. A ref is a remote AX token (`axtok1:` hex), resolved by token only, no path fallback (crates/macos/src/tree/resolve/*) [code].
3. Act. Each command runs a chain of steps, tried in order, and stops at the first that is delivered (crates/macos/src/actions/chain/chain_defs.rs) [code].
4. Verify. Only some actions are read back (SetValue, Clear, TypeText, Check, Uncheck, Toggle, Expand, Collapse: crates/core/src/actions/post_action.rs:7-139). Click and Scroll have no core read-back. `press` is always delivered_unverified [code].

## Headless vs headed
- Default is headless: AX actions and AX attribute writes only. It fails closed and never substitutes physical input (guides/headed-mode.mdx:11,19; CONCEPTS.md:236) [both].
- `--headed` only changes policy: it allows focus steal and cursor moves (crates/core/src/actions/interaction_policy.rs) [code].
- Headed click: raise the window, then a real CGEvent click at the element centre (chain_step_exec.rs:79-85, physical_click.rs) [code].
- Expand/collapse never go physical, even headed (chain_disclosure_steps.rs:22-67) [code].
- AX success is not proof of effect. The app can say OK and do nothing (platforms/macos.mdx:64) [docs].

## Key input
- `press <combo> --app X` headless: needs an AXFocusedUIElement (waits up to 500 ms), then CGEvent post_to_pid. No focus change. Bare return/escape use AXConfirm/AXCancel first. (crates/macos/src/system/key_dispatch.rs:22-66,126-143) [code]
- Headless press with `--window-id` on a background app is refused: macOS has no `press_key_for_window` override, and the core default demands that window be the focused one (crates/core/src/adapter/system.rs:241-285; grep shows only a Linux override). [code, verified this pass]. Live, `--app` alone is blind (see results); don't use it.
- Headed press with a modifier first AXPresses the matching menu item (key_dispatch.rs:33-37). docs macos.mdx:53 says press never runs a menu item. The code wins [code vs docs].
- Raw `--xy` mouse needs `--headed`, posts to the HID tap (real pointer), no focus call (crates/macos/src/input/mouse/mod.rs:131-174) [code].

## Focus
- `focus-window` = set AXFrontmost, poll up to 500 ms, AXRaise the window (fallback AXMain), verify (crates/macos/src/system/focus.rs:61-73) [code].
- No private SkyLight APIs. No activate-without-raise primitive is reachable from the CLI [code].
- No focus or cursor restore anywhere except Notification Center cleanup (nc_session.rs:143-149). The caller hands focus back [code].

## Permissions
- Three checks: AXIsProcessTrusted, CGPreflightScreenCaptureAccess, Automation for System Events (crates/macos/src/system/permissions/mod.rs:21-107) [code].
- Missing grants show as PERM_DENIED, not ACTION_FAILED (system/focus.rs:186-204). Our inert actions are not permission failures [inferred, strong].
- The helper binary is a clipboard helper only. It cannot cause inert actions (crates/macos/src/bin/agent-desktop-macos-helper.rs:1-3) [code].
- Automation is used only for Notification Center (nc_session.rs:66) [code].
- No env var or config adds an input route [both].

## Other features
- `mcp` (main only) spawns the same binary per call and adds no capability (src/mcp/call.rs:25-35) [both]. v1.1.0 rejects it.
- Sessions are a ref namespace and trace. The cursor overlay is a drawn overlay, it does not move the pointer (SKILL.md:57) [both].
- Main vs v1.1.0 in actions: only #503 (container-level row selection with AXSelectedRows, container_select.rs:70-124). Input, focus and permissions are identical [code].
