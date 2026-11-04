---
okf_version: "0.2"
type: "report"
title: "agent-desktop tree, refs and surfaces"
description: "Remote AX token refs, surfaces such as the menubar, and frontmost requirements, from source."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# agent-desktop: tree, refs and surfaces (for the CLion problem)

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Source: a local clone of vercel-labs/agent-desktop, main 6660fba (v1.1.0 d3dc190 plus 5 commits).
All paths are relative to that repo root. Line numbers are from the files as read; some are approximate ranges.
Tags: [code] read in source, [docs] stated in docs, [both], [inferred] my reasoning.
The problem: in an IDE project, `get_file_problems` answers fast only when CLion is frontmost.
Nothing here was run against any app. Only source was read.

## (a) Background app menubar: read and press without focus

- Reading a menubar needs no frontmost check. `menubar_for_pid` builds the app element from the pid and asks for its menu bar. [code] crates/macos/src/tree/surfaces.rs:17-28
- `resolve_window_surface` maps the Menubar surface to `menubar_for_pid`. [code] crates/macos/src/tree/query/mod.rs:198-
- Menubar, menu, sheet, popover, alert and focused are "process surfaces". They can be read without a window. [code] crates/core/src/snapshot/mod.rs (`is_process_surface`)
- Menu-bar click chain is AXPress only (`MENUBAR_CLICK_CHAIN`). No CGClick step. [code] crates/macos/src/actions/chain/chain_defs.rs
- CGClick steps are skipped unless headed. `step_allowed` and `chain_step_exec.rs:79-83`. So a headless click on a menu item is AXPress. [code] crates/macos/src/actions/chain/mod.rs, chain_step_exec.rs:79-83; [docs] apps/docs/content/docs/guides/headed-mode.mdx:19
- Opening a menubar menu: `open_menubar_menu` needs AXSelected to be settable on the AXMenuBarItem. [code] crates/macos/src/tree/surfaces.rs:42-59
- Menu tracking: while a menu is open, other reads can fail. [code] crates/macos/src/actions/chain/chain_menu_steps.rs
- `is_menu_open` and `wait_for_menu` exist for waiting on menu state. [code] surfaces.rs:259, crates/macos/src/system/wait.rs
- Docs say surfaces work on background apps through AX. [docs] apps/docs/content/docs/surfaces.mdx
- Answer: yes in principle. Menubar read and AXPress on an item need no focus in code. Whether CLion (JBR/Swing) exposes a real AX menubar is not shown by the source. [inferred]
- Caution: AXPress on a menu bar item may show the menu on screen, and the app may need to be active to track it. Not shown in code. [inferred]

## (b) AXEnhancedUserInterface / AXManualAccessibility

- Two attribute names: MANUAL and ENHANCED. [code] crates/macos/src/tree/renderer_probe.rs:3-4
- `choose_attribute` checks whether MANUAL is settable on the app element, then ENHANCED. [code] renderer_probe.rs:56-65
- `activation_needed`: for a non-web surface with ENHANCED, activation is needed only if the readback is `Some(false)`. For MANUAL: `!web_surface && absence_proven`. [code] renderer_probe.rs:30-47
- A test shows native apps that advertise ENHANCED are supported. So it is not Chromium-only. [code] renderer_probe.rs:254
- Setting: `activate` and `enable_attribute` set the attribute to true on the app element. ENHANCED sleeps 2 s to settle. Skipped if already true. Error if ENHANCED reads back false. [code] crates/macos/src/system/renderer_activation.rs:7-31, 33-76
- Trigger: only when a tree read fails and the error says the renderer is not ready, then core retries once. Retry backoff 25 to 400 ms. [code] crates/core/src/tree/renderer_accessibility.rs:20-47, 65-79
- In `observe_tree`: activation fires when `renderer_ready || (activation_eligible && tree.is_complete())`. Window surface roots are eligible. Element roots are not. [code] crates/macos/src/tree/query/mod.rs:48-74, 112, 145
- Chromium detection by bundle frameworks (Electron / CEF) is only used at launch time and in the permission guide. It does not gate the attribute. [code] crates/macos/src/system/renderer_kind.rs:1-80; launch.rs:147,165; permission_guide.rs:140
- So: yes, it can be set on a non-Chromium app if that app advertises the attribute as settable. Whether JBR advertises it is not shown by source. [inferred]
- Effect on a Java app is unknown. Setting AXEnhancedUserInterface is known to change some apps' behaviour (more AX tree, window animation changes). Nothing in the source says what JBR does. [inferred]
- Note: it is set without asking, as a side effect of a snapshot or find on a window surface. It is a write to the target app. [code]

## (c) How refs are resolved

- Refs are tokens, not paths. A ref stores a remote token string ("axtok1:" plus hex) made with private symbols `_AXUIElementRemoteTokenCreate` and `_AXUIElementCreateWithRemoteToken`. [code] crates/macos/src/tree/resolve/{mod.rs,retained.rs,retained_resolve.rs}
- Resolution is strict and token-only. No path or search fallback. [code] resolve/mod.rs
- Verification after resolve is weak: `token_mismatch` compares pid, role and native id only. A different element with the same role and id passes. [code] crates/macos/src/tree/resolve/resolve_errors.rs
- Failure maps to stale-ref errors. [code] resolve_errors.rs
- Refs come from the last snapshot. A ref from an old snapshot works only if the element still exists in the app. [inferred]

## (d) AX attributes readable that could reveal CLion state

- 23 attributes are read per node. [code] crates/macos/src/tree/properties/node_attribute_names.rs
- Child attribute sets per role. [code] crates/macos/src/tree/properties/element.rs
- State flags come from AXSelected, AXFocused and AXFocusedUIElement. [code] crates/macos/src/tree/state_reader.rs, build_context.rs
- `get` and `is` read properties (value, title, states) of one ref. [code] crates/core/src/commands/get.rs, is_check.rs
- Window titles, the focused element, the menubar items (item titles, enabled state, key equivalents), alerts, sheets and dialogs are all reachable. [code]
- Useful for state: a menubar menu's item enabled/disabled flags, window title (project and file), sheet or progress dialog presence via `list-surfaces`. [inferred]
- Tool-window content (problems list) is Swing. JBR often exposes it as a tree with AXSelected true for all items. [inferred, not in source]
- Reads are bounded: 64 KiB per field, 8 MiB total. An incomplete read gives AppUnresponsive. [code] crates/core/src/locator/live_locator/observation_budget.rs:3-7; crates/macos/src/tree/surface_read.rs

## Surfaces

- Surface kinds: window, focused, menu, menubar, sheet, popover, alert, dock, menu-bar-extras. [both] crates/macos/src/tree/surfaces.rs, shell_surface.rs, window_surface.rs; apps/docs/content/docs/surfaces.mdx
- `list-surfaces` enumerates them. [code] crates/macos/src/tree/surface_inventory.rs
- Dock and menu-bar-extras are hosted by system processes (MenuBarAgent, controlcenter, systemuiserver, "AXExtrasMenuBar"). Status items are excluded from click. [code] shell_surface.rs; actions/dispatch.rs
- Sheet, popover and alert are looked up by window and role. [code] surfaces.rs:161-177, 225-245
- Context menu: `context_menu_from_app`. [code] surfaces.rs:62-80
- `wait` has a menu wait. [code] wait.rs

## Frontmost handling

- No frontmost check found in the tree or surface read paths. AXFrontmost is read or written only in system/focus.rs and system/window/window_ax_state.rs (focus-window and window state). [code] grep of crates/macos/src
- Other frontmost hits (not examined in depth): tree/hit_test.rs, actions/physical_target.rs, notifications/nc_session.rs, workspace_apps and window_inventory files. hit_test and physical_target look to be headed-mode paths. [inferred]
- So the library does not itself require CLion to be frontmost for tree reads. If `get_file_problems` is fast only when frontmost, the cause is in CLion's own MCP/plugin side (for example throttled background threads or an inactive-window path), not in AX. [inferred]

## Selection and verification (relevant to false "delivered")

- `press_selection`: AXPress then reads AXSelected back. If it reads true, the result is DeliveredVerified. [code] crates/macos/src/actions/chain/press_selection.rs
- Container selection (main only, #503): SELECTION_ATTRIBUTES AXSelectedRows, AXSelectedChildren, AXSelectedCells, with a 300 ms settle. [code] crates/macos/src/actions/select/container_select.rs; selection_owner.rs; activate_descendant.rs guard
- If a Swing tree reports AXSelected true on every row, verification would pass with no real change. [inferred]

## Limits

- I did not run anything. No behaviour against CLion is observed.
- I did not read focus.rs, window_ax_state.rs, hit_test.rs or physical_target.rs in full.
- Line numbers for some files are ranges from reading, not exact for every claim.
- No source tells what JBR does with the two activation attributes or with AXPress on its menubar.
- Docs and code were checked for v1.1.0 plus 5 commits only.
- Refs verification weakness is from reading `token_mismatch`; not tested.

## Avenues for the CLion problem

Risk columns: cursor, focus, keyboard.

1. `agent-desktop list-surfaces --app <CLion>`
   - Code: enumerates surfaces by AX, read-only, no frontmost check. (surface_inventory.rs)
   - Expect: lists menubar, windows, any sheet or alert. Shows if CLion exposes AX at all while in the background.
   - Risk: cursor none, focus none. Confidence medium.
2. `agent-desktop snapshot --surface menubar --app <CLion>` (a read)
   - Code: `menubar_for_pid`, no frontmost check. Does not activate unless a window surface is requested.
   - Expect: menu bar item titles and, if exposed, enabled flags. Shows whether a Tools or Run menu entry for problems exists.
   - Risk: none to cursor or focus. Confidence medium. Note: this is a snapshot, which the task rules forbid me running now.
3. `agent-desktop click @ref` on a menubar item or menu item
   - Code: MENUBAR_CLICK_CHAIN is AXPress only. Headless skips CGClick.
   - Expect: AXPress opens or fires the item. May show a menu on screen. Could trigger an IDE action (for example Inspect Code) without focus.
   - Risk: cursor none; focus unlikely to change but a menu may appear; no keyboard. Confidence low-medium.
4. `agent-desktop get`/`is` on a window title or tool-window element
   - Code: reads AX properties only.
   - Expect: window title shows project and file, a cheap state signal. Problems-list content is likely poor in Swing.
   - Risk: none. Confidence medium.
5. `agent-desktop wait --menu` / `wait` for window or element change
   - Code: wait.rs polls AX.
   - Expect: a way to wait for CLion to finish a dialog or progress state without focusing it.
   - Risk: none. Confidence low-medium.
6. Window-surface snapshot (side effect)
   - Code: window surface roots are activation eligible. If the tree is incomplete or renderer not ready, core sets AXManualAccessibility or AXEnhancedUserInterface on CLion, with a 2 s sleep for ENHANCED.
   - Expect: could change CLion's AX behaviour for the rest of its run. It is a write to the app.
   - Risk: no cursor or focus, but a persistent app-side change. Confidence low on the effect.
7. `focus-window` (rejected here)
   - Code: sets AXFrontmost, via system/focus.rs.
   - Expect: would make CLion frontmost, which is the known fast case. Steals focus from a person.
   - Risk: focus steal. Confidence high that it works, but it is the intrusive path.
