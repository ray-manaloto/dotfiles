---
okf_version: "0.2"
type: "report"
title: "Opening and navigating CLion Settings"
description: "Why Settings can't be opened with the IDE inactive, the shortest activation route, and background page navigation through the search field."
resource: "https://github.com/JetBrains/intellij-community"
version: "intellij-community ebd238636 / CLion 2026.3"
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [clion, intellij, settings, macos, accessibility, rea]
---

# Opening and navigating Settings

## Opening: needs activation

| attempt (CLion inactive) | result |
|---|---|
| AXPress on the menu-bar "Settings…" (×3) | returns success, nothing opens, nothing in idea.log |
| the same AXPress after `focus-window` on a project frame | Settings opens at once |
| AXPress on the frame's "IDE and Project Settings" gear button | its ListPopup **opens in the background** (CG layer 101) |
| AXPress on that popup's "Settings…" row | only selects the row (AXSelectedChildrenChanged) |
| CGEventPostToPid click on the row (with and without window-under-pointer fields) | ignored, no AX events |

Activation test: after a background press, bringing CLion forward showed **no** pending dialog, and an
immediate active press opened it. So IntelliJ's ENABLED latch wasn't stuck, and **AppKit drops the menu
item's AXPress for an inactive app**.

Source (dotfiles-c6):
- The menu item is JBR's app-menu Preferences item (ApplicationDelegate.m:165-168, :426-428 →
  `_AppEventHandler` handlePreferences → `MacOSApplicationProvider.kt:78-99`, `submit()` :200-230).
  None of these check whether the app is active.
- `submit()` drops a call only when ENABLED is false (a Settings task is still running), when
  components aren't loaded, or when the focus owner is in a modal context.
- ListPopup runs a row only via `_handleSelect(true)` (ListPopupImpl.java:516-528). Its callers are
  Enter, mouseReleased, a mnemonic or shortcut, auto-select on show, and test mode.
- REST on 63342: no Settings handler and no action-by-id handler.
- `jetbrains://clion/settings?name=…|page_id=…|search=…` (OpenSettingsJbProtocolService.kt) exists,
  delivered via openURL or via the launcher's first argument. It always calls `AppIcon.requestFocus`,
  which activates with IgnoringOtherApps, even under `open -g`.

**Shortest route:** `open-settings.sh`.
1. Resolve the menu item ref while CLion is in the background.
2. In one agent-desktop batch: `focus-window` on a project frame → `click @item` → `focus-window`
   back to the previously focused window.
3. Re-check after the dialog appears, because showing it can re-activate CLion, and hand the front
   back again.

Measured 1.19–2.72 s with CLion in front. Settings reopens on the last page used.

## Navigating: works in the background

- **Settings search field**: rea `key-entry` (AXValue) on the top-level AXTextField "Search", set to a
  page name. Settings switches to that page. Setting it back to "" keeps the page and restores the
  full tree. Tested Exposed Tools → Keymap → Exposed Tools, with Herdr frontmost.
- **Breadcrumb as a page check**: the top-level, labelled AXButtons with no actions, e.g. `AI`,
  `MCP Server`, `Exposed Tools`. A top-level page shows one, e.g. `Keymap`. The swap lands
  asynchronously, so poll.
- Settings tree rows: the expandable rows expose AXPress and the leaf rows expose none. AXPress on a
  row **completed but changed nothing** in the background, so use search.
- The brief's "AXPress on a visible link navigates" still holds for links (AXLink).

## Closing

- AXPress on Cancel or OK works in the background. A rea scenario's after-capture then fails with
  "Selected window is absent". Accept that only when the window is gone.
