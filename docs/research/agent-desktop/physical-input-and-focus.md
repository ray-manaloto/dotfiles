---
okf_version: "0.2"
type: "report"
title: "agent-desktop physical input and focus"
description: "press routes, focus-window, and the absence of focus restore, from source."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# Physical input and focus (agent-desktop, macOS)

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Scope: repo clone at main 6660fba. Paths are relative to the repo root.
Between v1.1.0 and main, none of the input, focus, key-dispatch or physical-click files changed
(`git diff --stat v1.1.0..HEAD` on crates/macos/src/input, system/focus.rs, system/key_dispatch.rs,
core/commands/press.rs shows only ax_perform.rs, chain/activate_descendant.rs, select/container_select.rs). [code]
So everything below holds for the installed v1.1.0 as well.

## 1. Policy model (what --headed means)

- Three policies: headless (no focus steal, no cursor move), focus_fallback (focus only), headed (both).
  crates/core/src/actions/interaction_policy.rs:9-33. [code]
- `--headed` is a global flag. It sets `InteractionPolicy::headed()`.
  crates/core/src/context/mod.rs:110-117. [code]
- `physical_input_policy()` is headless joined with the flag. So `press` is headless unless `--headed` is given.
  crates/core/src/context/mod.rs:230-236. [code]
- Docs: "`--headed` is a permission ... take focus, move the real cursor, and synthesize keys and pointer events."
  apps/docs/content/docs/guides/headed-mode.mdx:7. [docs]

## 2. `press <combo> --app X` (headless, the default)

Flow, crates/core/src/commands/press.rs:17-74: [code]
1. Parse combo; block quit/lock combos unless `--force` (line 24).
2. Resolve the app; take an interaction lease; revalidate the process (lines 28-36).
3. Not headed: skip focus (line 37 is false). With `--window-id` it calls `press_key_for_window` (line 53); without it, `press_key_for_app` (line 55).
4. After the key, `follow_caret_after_key` runs (line 66; overlay only).

`press_key_for_app` on macOS is `press_for_app` in crates/macos/src/system/key_dispatch.rs:22-66. Steps: [code]
1. Menu shortcut: only if `policy.allow_focus_steal` and the combo has a modifier (lines 33, 97-99).
   Headless skips this. Headed walks the app menu bar for a matching `AXMenuItemCmdChar` and does `AXPress` on it
   (crates/macos/src/system/key_dispatch_menu.rs:16-57). No key is sent in that case.
2. Simple key action: bare `return`/`enter` becomes `AXConfirm`, bare `escape`/`esc` becomes `AXCancel`, on the app's
   `AXFocusedUIElement`, only if that element advertises the action (lines 45-49, 83-110). This is a semantic call, no key event.
3. Otherwise it needs a focused element: it polls `AXFocusedUIElement` of the app for up to 500 ms, else error
   "Application has no verified focused element for keyboard delivery" (lines 56-57, 126-143, 112-124).
   Headless error text suggests `--headed` or the menu bar route (lines 118-123).
4. Then `synthesize_key(combo, Some(pid))` (line 59).
5. If `allow_focus_steal` (headed), it first calls `verify_app_focused` (line 52-55). Headless skips this check. [code]

The delivery primitive: `CGEvent::post_to_pid(pid)` when a pid is given, else `post(CGEventTapLocation::HID)`.
crates/macos/src/input/keyboard/keyboard_event.rs:134-140. Step label in the result is "CGEventPostToPid".
crates/macos/src/system/key_dispatch.rs:62. [code]
- Event source: `CGEventSourceStateID::HIDSystemState` (keyboard_event.rs:129-132). [code]
- Down event, 4 ms pause (`KEY_SETTLE`), up event; a drop guard sends key-up if the down was sent (keyboard_event.rs:6, 79-115). [code]
- Modifiers are set as event flags on the key event, not as separate modifier key presses (keyboard_event.rs:21-23, mouse/mod.rs:16-26). [code]
- Key code comes from a name table (input/keyboard/keyboard_map.rs, via mod.rs:15). Standalone key-down/key-up are refused: input/keyboard/mod.rs:25-41. [code]
- Result is always `delivered_unverified`, `verified=false` (key_dispatch.rs:60-65, 74-81). [code]

Doc claim: "`press cmd+s --app "TextEdit"` sends keys to one app without focusing it."
apps/docs/content/docs/platforms/macos.mdx:78 and `press --help` ("keys go to its process without focusing it"). [both]
Doc conflict: macos.mdx:53 says `press` "always physical keyboard input; it never runs a menu item". Code runs a menu item
by `AXPress` in headed mode with a modifier combo (key_dispatch.rs:33-37, 97-99). Headless does not. [code vs docs]

`press --app X --window-id ID` headless: macOS does not override `press_key_for_window`, so the default in
crates/core/src/adapter/system.rs:228-285 applies. It refuses unless that exact window is the focused window
("exact_window_focus_unconfirmed"; the suggestion says retry with `--headed`). Do NOT use `--window-id` for a background app.
(grep shows no macOS impl of `press_key_for_window`.) [code]

Unscoped `press COMBO` (no `--app`): `execute_global_action` posts to the HID tap, not to a pid.
crates/macos/src/actions/adapter.rs:41-56. The keys go to whatever app is frontmost. [code]

### Does a Java/AWT app accept PID-posted key events while not active?

- The source does not say. No file, doc or probe mentions Java, Swing, AWT or JetBrains for macOS.
  (grep of probes/, docs/, CHANGELOG.md, skills/, apps/docs; hits are Linux/Windows or unrelated.) [code]
- agent-desktop itself does not test that the target app is active in the headless path. It only reads the app's
  `AXFocusedUIElement` (key_dispatch.rs:56-57). So it will post the event even if the app is behind. [code]
- Whether the app handles it is up to the app. A PID-posted event goes to that process's event queue, but AppKit
  routes key events to the key window, and an inactive app may have no key window. [inferred, from general AppKit behavior, not from this repo]
  Needs a live test. A good probe: `press --app CLion <combo>` with CLion behind, then read the result with `get`/`snapshot`. **Live result: rejected. The keys land in whichever window and field had focus last, unverified; see [results](results.md).**
- The readback is weak: the report is only `delivered_unverified`, so success of the CLI call proves delivery to the
  process, not that CLion acted. [code]

## 3. `--headed` step by step

For `press --app X --headed` (press.rs:37-49): [code]
1. `focus_exact_window` (with `--window-id`) or `focus_process_window` (finds the process's window) in
   crates/core/src/actions/headed_focus.rs:37-70. It resolves the live window strictly, checks same pid and process instance,
   then calls `adapter.focus_window(&live, lease)`.
2. macOS `focus_window_impl` (crates/macos/src/system/focus.rs:61-73):
   a. Find the window's AX element.
   b. `focus_app(pid)`: read `AXFrontmost` on the app element. If already true, do nothing (line 20-22).
      Else set `AXFrontmost = true` with AX, and poll `AXFrontmost` for up to 500 ms (lines 24-38, `VERIFY_LIMIT` line 7).
   c. `raise_window`: perform `AXRaise` on the window; if that is not enough, set `AXMain = true` and poll `AXMain`
      (crates/macos/src/system/window/window_ops.rs:222-257).
   d. `verify_app_focused`: read `AXFrontmost` again.
3. Then `press_key_for_app` with the headed policy: menu `AXPress` try (modifier combos), else `verify_app_focused`, check
   focused element, `post_to_pid`.

The `focus-window` command uses the same `focus_window_impl` plus a confirm loop: up to 750 ms, poll every 50 ms,
needs 2 confirmations that the window is the focused window (crates/core/src/system/window_focus.rs:5-60). [code]
`focus-window` selects by `--window-id`, `--title` (substring) or `--app` (must be a single match).
crates/core/src/commands/focus_window.rs:12-48. [code]

There is no cursor warp in `press --headed`. Keyboard events do not move the cursor. [code]
Cursor movement happens only in pointer paths (`click` physical fallback, `mouse-click`, `mouse-move`, `hover`, `drag`, `mouse-wheel`):
see section 5.

### What focus_window does NOT use
- No `NSRunningApplication.activate...`, no `SkyLight`/`SLPS...` private APIs, no `NSWorkspace.activate`, no `CGSSetFrontProcess`.
  grep of crates for `activateWithOptions|activateIgnoring|SLPS|SkyLight|CGEventPost|AXRaise|AXFrontmost` finds only the AX
  paths above and `NSRunningApplication` for pid lookup, `terminate`, and `isFinishedLaunching`
  (crates/macos/src/system/appkit_bridge.m:34, 56). [code]
- The only other app-activation path is `NSWorkspace openApplicationAtURL` with `configuration.activates`, used by `launch`:
  crates/macos/src/system/launch_bridge.m:154-163, fed by `options.activate` (launch_workspace.rs:21). [code]
  `launch` default is `activate=false`, `attach_if_running=true` (crates/core/src/system/launch_options.rs:34-35).
  `launch --activate` "brings the app forward and waits for a window" per `launch --help`. [both]
  Private `_AXUIElementGetWindow` is used only to map windows (crates/macos/src/system/window/window_bridge.rs:34). [code]

## 4. Is there any activation without raising, or with another app visually in front?

- No mode in the source does that. `focus-window` always does AXFrontmost then AXRaise (focus.rs:68-71). [code]
- `focus_app` alone (AXFrontmost without AXRaise) exists as a private function, and as `ensure_app_focused`
  (focus.rs:10-12). Its only caller is Notification Center cleanup (crates/macos/src/notifications/nc_session.rs:206). It is
  not reachable from any CLI command. [code]
  What `AXFrontmost=true` does visually is decided by macOS (it activates the app, which normally brings its windows forward). [inferred]
- No `--no-raise`/background-activate flag in `focus-window --help`, `press --help`, `launch --help`. [code, binary --help]
- `AXFocused` set on an element (`focus @ref`) is the semantic route: `ax_focus_or_err` sets `AXFocused=true` on the element
  (crates/macos/src/actions/ax_helpers.rs:115-117). It does not activate the app. Whether CLion's AX bridge honors it for a
  background app is untested. `focus` is "semantic under --headed" (skills/agent-desktop-macos/SKILL.md:39;
  apps/docs/.../macos.mdx:42). [both]

## 5. Restore of focus and cursor

- Focus restore exists in one place: Notification Center. It records the previous frontmost app and re-activates it with
  `ensure_app_focused` on cleanup (nc_session.rs:143-149, 183-207; doc: macos.mdx:79). [both]
- No focus restore in `focus-window`, `press --headed`, or headed click/type. After `focus-window`, the target stays frontmost. [code]
  (grep for restore/previous/saved focus in crates/core and crates/macos finds only nc_session.rs.)
- No cursor restore anywhere. Pointer events leave the real cursor at the target point. [code]
  Grep for saved/restored cursor position found nothing; `verify_position` only reads the pointer back
  (crates/macos/src/input/mouse/mouse_move.rs:40-64).
- The "agent cursor overlay" is a separate drawn overlay, "presentation only", and "a headed command hides it while it
  dispatches real input" (headed-mode.mdx:90). It is not the real cursor. [docs]
- So the 3 s focus hand-back seen so far was done by the caller (focus-window on the other app), not by the tool.

## 6. Raw `--xy` input

- Raw coordinates need `--headed` for every mouse command; headless returns POLICY_DENIED, nothing sent.
  apps/docs/.../commands/mouse.mdx:7-18; crates/core/src/commands/mouse_click.rs:25 (`require_cursor_policy`). [both]
- "Raw coordinates carry no window identity and never focus an app; a ref target focuses its exact window first."
  mouse.mdx:18; headed-mode.mdx:20; skills/agent-desktop-macos/SKILL.md:39 ("Raw `--xy` input never changes focus"). [both]
  Code: `mouse_click::execute` takes a point and calls `dispatch_mouse_event_with_cursor` only; no `focus_*` call in the file
  (crates/core/src/commands/mouse_click.rs:20-51). [code]
- Mechanism (macOS): CGEvent mouse events posted at the HID tap, i.e. the real system pointer, not to a pid.
  Click: two `MouseMoved` events (one point left, then the target; 10 ms each), read the pointer position back for up to 100 ms,
  then down/up with click-state set, 10 ms between, 30 ms between repeat clicks.
  crates/macos/src/input/mouse/mod.rs:131-174; mouse_move.rs:10-64. [code]
- Because HID events go to whatever window is under the pointer at the OS level, a click lands in the app that owns that
  screen point. Clicking a background window's visible area may make macOS activate that app (normal OS click behavior). [inferred]
- Wheel: cursor moved to the point first, then line-unit scroll events (up to 10 lines per event, 1000 max) posted to HID, with the point set on the event.
  crates/macos/src/input/mouse/mouse_scroll.rs:7-47, 3-4. [code]
- Drag: destination app is never focused first (mouse.mdx:83). [docs]
- `mouse-down`/`mouse-up`, `key-down`/`key-up` always refuse in stateless mode (mouse/mod.rs:54, 80-92; keyboard/mod.rs:25-41). [code]
- Per-ref physical click (`click --headed` on a ref, or the AX-failed fallback) is stricter: it requires BOTH cursor and focus
  permission, the app frontmost and the window `AXMain`, a bounds read, a hit test at the final point, and a process-identity check.
  crates/macos/src/actions/physical_click.rs:14-60; physical_target.rs:11-82; focus.rs:43-58, 84-98. [code]
  It refuses with "Target application lost focus before physical input delivery" if the app is not frontmost, so it cannot click in a background window. [code]
  Exception: apps with a non-Regular activation policy (menu bar apps, Dock, system panels) skip the focus check (physical_target.rs:89-131). [code]

## 7. Physical typing and clipboard

- `type` headless = `AXSelectedText` write (semantic), `type --headed` = physical, PID-targeted Unicode text, in 32-unit chunks
  with `CGEventPostToPid` (crates/macos/src/actions/type_text.rs:8-27; keyboard_event.rs:28-55, 9). [code]
- Physical typing (`physical_keyboard.rs`) requires `allow_focus_steal` (line 58-63), verifies `AXFrontmost` and `AXMain` of
  the window (lines 79-82), sets `AXFocused` on the element, and waits up to 500 ms for `AXFocusedUIElement` to match (lines 84-94, 125-145).
  So headed typing into a background app fails with "Target application lost focus ..." unless the app is already frontmost. [code]
  (Headed core first calls focus_window, so in practice headed typing steals focus first.)
- Clipboard (`clipboard-get/set/clear`) uses NSPasteboard through a helper; it does not touch focus (crates/macos/src/input/clipboard/*). [code]
  It could be paired with a PID-posted `cmd+v`, but only to a text field; not relevant to the analysis trigger.

## Limits

1. No command activates an app without AXRaise. `focus-window` = `AXFrontmost` + `AXRaise` (+ `AXMain` fallback). focus.rs:61-73;
   window_ops.rs:222-257. [code]
2. No restore of previous focus or cursor, except Notification Center cleanup. nc_session.rs:143-149. [code]
3. Headless `press --app` delivers only: (a) `AXConfirm`/`AXCancel` for bare return/escape on the focused element, or (b) a
   PID-posted CGEvent. No menu shortcut run in headless mode. key_dispatch.rs:33-49, 97-110. [code]
4. `press --window-id` on a background app is refused (window must be the focused window). system.rs:228-285. [code]
5. Physical per-ref click/type refuse unless the app is frontmost and the window is main. physical_target.rs:34-40; physical_keyboard.rs:79-94. [code]
6. Raw `--xy` input moves the real cursor, posts to the HID tap, and cannot target a pid or window. mouse/mod.rs:156,167; mouse_move.rs:28. [code]
7. Standalone key-down/key-up and mouse-down/mouse-up never deliver. [code]
8. Blocked combos need `--force`: cmd+q, cmd+shift+q, cmd+alt+esc, ctrl+cmd+q, cmd+shift+delete, with superset matching.
   crates/macos/src/input/blocked_combo.rs:3-31. (Relevant if testing CLion shortcuts; not a likely blocker.) [code]
9. All physical results are `delivered_unverified`; the tool cannot say whether CLion acted. [both]
10. Nothing in the repo covers Java/AWT/Swing on macOS for PID-posted keys. [code, grep]

## Avenues for the CLion problem

Ordered by intrusiveness, least first. "Effect" is what the source says will happen, then what is unknown.

1. Headless `press` by pid. **Rejected after live tests (see [results](results.md)): keys land in whichever window and field had focus last, unverified. Don't use this.**
   - Mechanism: after an AXFocusedUIElement check, `CGEvent.post_to_pid` key down/up (key_dispatch.rs:56-59; keyboard_event.rs:134-140).
   - Source says: posts to CLion's pid without activating it. For bare `return`/`escape` it calls AXConfirm/AXCancel instead (no key event).
   - Unknown: whether JBR/AWT acts on key events while CLion is inactive; whether it triggers analysis of the file. Needs a live test.
   - Needs first: CLion must report an `AXFocusedUIElement` (up to 500 ms wait). If not, error "no verified focused element".
   - Intrusiveness: none (no cursor, no focus). Keystrokes go into CLion if they land. Pick a combo with no side effects first.
   - Confidence: mechanism high [code]; effect on CLion low [inferred].

2. `agent-desktop focus @ref` (headless, on an editor/tree element) then `press ... --app CLion` **Live result: rejected. The keys land in whichever window and field had focus last, unverified; see [results](results.md).**
   - Mechanism: AX `AXFocused=true` on the element (ax_helpers.rs:115-117). Semantic, no activation.
   - Source says: sets the in-app focused element if CLion's AX bridge allows it; may be ACTION_NOT_SUPPORTED. Earlier results already show
     tree-item actions are inert, so low odds. [inferred]
   - Intrusiveness: none. Confidence: low.

3. Menu bar route, headless: `snapshot --app CLion --surface menubar -i`, then `click @ref` on a menu item (headless AXPress).
   - Mechanism: AXPress on a menu item (semantic). Docs recommend this for shortcuts: key_dispatch.rs:118-123; macos.mdx:53 ("click the item instead").
   - Source says: AX actions go to the process without focus. If JBR exposes the macOS screen menu bar (native NSMenu), items like
     Code > Inspect Code or Analyze may run. Whether the action triggers file analysis is unknown. (Another agent covers surfaces.)
   - Intrusiveness: none. Confidence: medium that it is deliverable; unknown whether it fixes analysis.

4. `agent-desktop --headed press <combo> --app "CLion"` (or with `--window-id`)
   - Mechanism: `focus_window_impl` (AXFrontmost + AXRaise), then menu-item AXPress for modifier combos, else PID-posted key (press.rs:37-55).
   - Source says: CLion becomes frontmost (about 0.6 s, as seen with `focus-window`). Nothing restores previous focus.
   - Intrusiveness: focus steal; no cursor move. Caller must hand focus back (`focus-window` on the other app).
   - Confidence: high [code]. This is the same cost as the existing `focus-window` workaround, so it only helps if you need the key.

5. `focus-window --window-id <CLion>` then `focus-window --window-id <previous app>` (current workaround)
   - Mechanism: section 3. Total visible focus steal about 3 s. Confidence high.
   - No variant keeps the other app visually in front. Limit 1.

6. `launch CLion` (no `--activate`)
   - Mechanism: `NSWorkspace openApplicationAtURL`, `activates=false`, attach to running instance (launch_bridge.m:154-163;
     launch_options.rs:34-35). For an already-running app this should be a no-op. It may re-deliver `--arg` values to the running CLion
     (inferred: Launch Services passes arguments only to a new instance, so probably ignored). Not a fix for analysis. [inferred]
   - `launch --activate`: activates and waits for a window. Focus steal. No advantage over focus-window.
   - Intrusiveness: none/focus steal. Confidence low.

7. `--headed mouse-click --xy X,Y` on a visible CLion window area
   - Mechanism: HID CGEvents at the real pointer (mouse/mod.rs:131-174). Cursor moves and is not restored. A click on an inactive
     app's visible window will likely activate it (normal OS behavior). [inferred]
   - Intrusiveness: cursor moves and probable focus steal. Confidence: medium. Worse than `focus-window`; not recommended.

8. `--headed click @ref`, `--headed type`
   - Refuse unless the app is frontmost (physical_target.rs:34-40; physical_keyboard.rs:79-94), but headed core runs focus_window first,
     so they behave as avenue 4 plus a cursor move for click. Intrusiveness: focus steal and cursor move.

9. Notification Center path (the only built-in focus restore): not applicable to CLion.

Net finding for this area: the tool has exactly one background-capable physical channel for CLion, `press --app` with
`CGEventPostToPid` (avenue 1). Everything else either is semantic AX (avenues 2, 3) or steals focus (4-8). The open test is avenue 1
on CLion while it is behind another app, then check whether the error check answers for an un-analysed file. **Live result: rejected. The keys land in whichever window and field had focus last, unverified; see [results](results.md).**

## Open questions
- Does JBR (AWT) process a PID-posted `CGEventPostToPid` key event while CLion is not the active app? Not in repo. Needs live test.
- Does CLion expose `AXFocusedUIElement` while in the background? If not, avenue 1 fails with "no verified focused element".
- Does a Cmd-modifier combo posted this way fire an IDE action (keymap handled in Java), or does JBR drop it without a key window?
- Does `AXFocused` set on a CLion editor element succeed headless?
- Does CLion's Analyze/Inspect menu items get exposed in `--surface menubar` and does AXPress run them in the background?
