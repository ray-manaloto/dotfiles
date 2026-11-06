---
okf_version: "0.2"
type: "report"
title: "Opening and navigating CLion Settings"
description: "Opening Settings in the background through the IDE's station socket, why the menu route needs activation, and background page navigation through the search field."
resource: "https://github.com/JetBrains/intellij-community"
version: "intellij-community ebd238636 / CLion 2026.3"
timestamp: "2026-11-06T02:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [clion, intellij, settings, macos, accessibility, rea]
---

# Opening and navigating Settings

## Opening in the background: the station socket (the default)

Each running IDE's station plugin serves HTTP on `$(getconf DARWIN_USER_TEMP_DIR)jb.station.ij.<pid>.sock`.
`POST /protocolHandler` with `{"uri": "jetbrains://idea/settings?name=<page>"}` runs the IDE's `settings` protocol
command without LaunchServices. LaunchServices (`open jetbrains://...`) was what activated the IDE before.

- **Measured once, 2026-11-05 (CLion 2026.3, a project open, nothing else of CLion's open):** reply
  `{"exitCode":0}`. Settings opened unfocused on AI > MCP Server > Exposed Tools, and the frontmost app never
  changed (sampled every 50 ms for 8 s). This is one state, not a guarantee.
- **The host is a placeholder.** `JBProtocolCommand.execute` reads only the command, `parts[1]`, so
  `jetbrains://idea/...` serves every product. [code]
- **`name=` and not `page_id=`.** `name=` matches the display name (`SearchConfigurableByNameHelper`, case-insensitive;
  first match breadth-first; localized) and returns once the dialog is scheduled with `invokeLater`. `page_id=`
  (here `com.intellij.mcpserver.settings.filter`) is locale-independent, but it waits on the EDT for the dialog to
  show, and a modal Settings turns that into a wait until the dialog closes. [code]
- **Reply checks.** The IDE reports a refused command as exit code 0 with a `message`. jbctl requires HTTP 200,
  `exitCode` 0 and no message, then waits for the window. [code]
- **States that may still bring it forward.** `NonModalWindowWrapper.show` de-iconifies and fronts frames.
  `jbax windows` reports `unsafe` (a reason, or null) from its `backgroundRisk`, and jbctl and the Swift test
  refuse unless it is null: only project frames, each with `minimized` and `modal` explicitly false. A flag AX cannot read is null, and null is refused. A dialog or popup of any size is
  `other`, so it refuses too. The projectless Welcome screen is also a titled standard window. With no project
  open, Settings opens for the default project. jbax recognizes it by the title prefix `Welcome to `, compared
  inside jbax and never printed. The full title may add the product's full name, a version and a superuser
  suffix. A window whose title or subrole AX cannot read, or a standard window with an empty title, is `unknown`
  and refused. The title is localized, so a non-English Welcome screen is not recognized: a known gap. An
  existing Settings window is refused, never reused: it may hold the user's unapplied edits. A frame on another Space is NOT_RUN.
  [code + inference]
- **Debug route.** The menu-bar route below runs only with `JETBRAINS_FOREGROUND=1`, and never as a fallback.

## The menu route: needs activation (debug only, JETBRAINS_FOREGROUND=1)

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
