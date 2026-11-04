---
okf_version: "0.2"
type: "report"
title: "agent-desktop documented behaviour and limits"
description: "The agent-desktop docs set against the code, including conflicts."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# agent-desktop: documented behaviour and limits

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Repo: vercel-labs/agent-desktop at main 6660fba (v1.1.0 + 5 commits). Paths are relative to the repo root.
Tags: [code] read in source, [docs] stated in docs, [both], [inferred].
Docs root: apps/docs/content/docs (D/ below).

## 1. Command list (60 names, same on every OS)

Source: D/commands/index.mdx, D/index.mdx ("the same 60 command names"). [docs]
Four are reserved and fail closed everywhere: key-down, key-up, mouse-down, mouse-up. [docs]

- Observation: snapshot (-i, --compact, --skeleton, --root, --surface, --wait-for), find, get, is, screenshot, list-surfaces. [docs: commands/observation.mdx]
- Interaction (ref actions): click, double-click, triple-click, right-click, type, clear, set-value, select, toggle, check, uncheck, expand, collapse, focus, scroll-to, hover, drag. [docs: commands/interaction.mdx, mouse.mdx]
- Keyboard: press COMBO (--app, --window-id, --force), key-down, key-up (reserved). [docs: commands/keyboard.mdx]
- Scroll: scroll (native AX headless on macOS). [docs: commands/scroll.mdx:29]
- Mouse: mouse-move, mouse-click and similar; need --headed; mouse-down/up reserved. [docs: commands/mouse.mdx]
- App and window: launch (--activate, --cdp, --arg, --env), close-app, list-apps, list-windows, focus-window, resize/move/minimize/maximize/restore windows. [docs: commands/app-window.mdx]
- Wait: wait MS, --element/--predicate, --window, --text, --menu, --menu-closed, --event, --notification. [docs: commands/wait.mdx]
- batch: JSON array, 64 entries, 1 MiB in, 4 MiB out, 60000 ms, not atomic, --stop-on-error, --headed applies to all entries. [docs: commands/batch.mdx, guides/batch.mdx]
- Notifications: list/dismiss/action; mutations always need --headed. [docs: commands/notifications.mdx]
- Clipboard: get/set/clear. [docs: commands/clipboard.mdx]
- System: status, permissions (--request, --guide), version, skills, session (start/list/end/gc), trace (show/export), cursor-overlay, open-system-surface. [docs: commands/system.mdx]
- mcp: `agent-desktop mcp` serves each command as a `desktop_<name>` tool over stdio; global flags only on the server command line; at most 8 concurrent calls. Not in the 60-command table. Added after v1.1.0 (git log v1.1.0..HEAD: 6660fbac "feat: agent-desktop mcp (#519)"). [docs: guides/mcp.mdx] [code: git log]
- jev-desktop: not a CLI command. A skill for an optional helper that needs a clone and an API key. [docs: skills.mdx]

Global flags and env: --headed, --app, --window-id, --surface, --session / AGENT_DESKTOP_SESSION, --agent-id / AGENT_DESKTOP_AGENT_ID, --trace PATH, --trace-strict, --debug --screenshot PATH.html, --timeout-ms (auto-wait 5000 ms, batch 60000 ms), wait uses --timeout (30000 ms). [docs: configuration.mdx, sessions.mdx, guides/traces.mdx, guides/waiting.mdx]

## 2. Documented limits, guarantees, caveats

- Tool only; no model, no GUI. "Limited to what apps expose ... cannot see a UI that publishes no accessibility tree." [docs: index.mdx]
- Headless is the default and is semantic only. It fails closed (ACTION_NOT_SUPPORTED or POLICY_DENIED). It never silently substitutes physical input. [docs: guides/headed-mode.mdx:11,19,22-23; CONCEPTS.md:236,238]
- Headed on macOS is "physical first" for click, right-click, type, clear, scroll. Core focuses the exact window first. expand, collapse, set-value, select, toggle, check, uncheck, focus, scroll-to stay semantic under --headed. Double/triple-click, hover, drag need --headed. Raw --xy never changes focus. [docs: platforms/macos.mdx:42; skills/agent-desktop-macos/SKILL.md:39]
- "AX return codes do not prove an effect. Finder returns success from an AXConfirm that does nothing." [docs: platforms/macos.mdx:64; SKILL.md:41]
- A readable tree does not prove actions are active. [docs: docs/solutions/runtime-errors/chromium-readable-tree-with-inactive-ax-actions.md]
- Delivery dispositions: not_delivered (retry safe); delivery_uncertain, delivered_unverified, delivered_verified (retry unsafe); unknown. [docs: errors-and-recovery.mdx]
- press is physical, always delivered_unverified. [docs: commands/keyboard.mdx:33]
- Post-action verification exists for set-value, clear, type, check, uncheck, toggle, expand, collapse. App commit is not verified. [docs: commands/interaction.mdx]
- Actionability: visible, stable, enabled, receives_events (polled up to 5000 ms); supported_action, policy, editable (terminal). [docs: commands/interaction.mdx:61-85]
- Refs: `@<snapshot_id>:eN`. On macOS each ref carries the element's own address; a gone element gives STALE_REF, details.kind retained_object_stale, never a look-alike. [docs: platforms/macos.mdx:53, snapshots-and-refs.mdx:150-166]
- Ref maps: 1 MB per map, 128 snapshots. [docs: snapshots-and-refs.mdx]
- Refs are not valid across sessions (SNAPSHOT_NOT_FOUND). [docs: sessions.mdx]
- Surfaces on macOS: window, focused, menu, menubar, sheet, popover, alert, dock, menu-bar-extras. A window-less background app is read through its process. [docs: surfaces.mdx:35,112]
- While a menu, sheet, alert or popover is open, refs from the window behind it are the wrong target. [docs: surfaces.mdx:7; platforms/macos.mdx:43]
- focus-window takes the foreground without --headed and needs two consecutive focused reads. launch --activate takes the foreground. [docs: commands/app-window.mdx:37,224-261]
- open-system-surface: dock and menu-bar-extras need no --headed on macOS. [docs: surfaces.mdx:160]
- Notification mutations always need --headed. [docs: commands/notifications.mdx]
- Quit shortcuts return POLICY_DENIED unless --force. [docs: platforms/macos.mdx / SKILL.md:55]
- cursor-overlay is presentation only: "never moves the OS pointer or activates an app". [docs: SKILL.md:57]
- Sessions are namespaces for snapshots and traces; multi-agent cursor mode needs --agent-id for actions. [docs: sessions.mdx:102]
- Trace redacts text/value/name/title; screenshots are not redacted. [docs: guides/traces.mdx]
- Chromium/Electron: renderer AX activation (AXManualAccessibility / AXEnhancedUserInterface) with a settle delay; launch --cdp. [docs: guides/chromium-and-electron.mdx] [code: crates/macos/src/tree/renderer_probe.rs:3-4; crates/macos/src/tree/query/mod.rs:62; crates/macos/src/system/renderer_activation.rs:11,40]
- Windows note, for contrast: minimized windows are not drivable; press --app writes to the foreground queue and cannot target a background process. [docs: platforms/windows.mdx:51,75]

## 3. Advertised-but-inert, Java, activation and focus

- Java/Swing/JetBrains: no mention anywhere. A grep for java, swing, jetbrains, jbr, intellij, clion across docs, skills, CONCEPTS, AGENTS, CHANGELOG, desktop-llms.txt and the site mirror found only "JavaScript" and Linux probe text. [docs: absence, grep]
- AXEnhancedUserInterface/AXManualAccessibility are set only by the renderer-activation path, which is gated on web surfaces and a "complete but empty" tree. Not applied to a Java app that already returns a tree. [code: crates/macos/src/tree/renderer_probe.rs:35-50; tree/query/mod.rs:57-70] [inferred for Java]
- Inert examples in the docs: Finder AXConfirm (macOS.mdx:64); Xcode AXDisclosureTriangle uses AXValue 0/1, so expand failed "All chain steps exhausted" (docs/solutions/runtime-errors/2026-09-20-xcode-project-disclosure.md); selection is not proof a file opened (same file); select needs Click advertised on the target, and a disclosure with unreadable state refuses (docs/solutions/runtime-errors/2026-09-20-native-command-reliability.md). [docs]
- The Xcode note says headless already defaults focus stealing and cursor movement to false, and that this is "not proof that arbitrary AX actions in arbitrary apps cannot activate their app". [docs]
- What takes the foreground: focus-window, launch --activate, --headed ref actions, open-system-surface (Windows/Linux), notification mutations. [docs]
- press --app, headless, macOS: keys go to the process by pid. Order in the code: (a) menu-bar shortcut AXPress only if allow_focus_steal (headed) and modifiers present; (b) bare return/escape become AXConfirm/AXCancel on the focused element if advertised; (c) otherwise CGEventPostToPid(pid) after the app reports an AXFocusedUIElement (500 ms wait), else ACTION_FAILED "no verified focused element". Headed adds verify_app_focused first. Result is always delivered_unverified. [code: crates/macos/src/system/key_dispatch.rs:22-66,100-125; crates/macos/src/input/keyboard/keyboard_event.rs:136]
- So `press cmd+s --app X` "without focusing it" (macOS.mdx:78) is true in the code: it posts to the pid and does not raise the window. [both]

## 4. Recovery ladder

Generic (D/errors-and-recovery.mdx:111-116):
1. Read error.disposition.retry. Retry only when "safe".
2. STALE_REF / recovery refresh_snapshot_then_retry_original: snapshot again, retry.
3. inspect_state_then_retry_original: read the app state first.
4. request_explicit_policy_then_retry_original: POLICY_DENIED; get explicit policy (headed) only if the person accepts the side effect.
5. INVALID_ARGS, ACTION_NOT_SUPPORTED, PLATFORM_NOT_SUPPORTED, PERM_DENIED: change the input or environment; a retry will not help. ACTION_FAILED, INVALID_ARGS, AMBIGUOUS_TARGET never carry a recovery field.

macOS troubleshooting ladder for ACTION_FAILED (skills/agent-desktop-macos/references/troubleshooting.md): check the element is enabled; get bounds; retry with --headed if physical input is right; last resort `focus @ref` then `press return`. [docs]

Contradiction: headed-mode.mdx:78-86 says do not switch to headed to recover from a headless failure (cursor move, focus steal, double delivery). The macOS troubleshooting offers it as step 3. [docs]

ACTION_NOT_SUPPORTED has no escalation in the docs beyond "change the input"; the headed callout says headless failure usually means the semantic path is missing. [docs]

## 5. Pages read (38 under apps/docs/content/docs)

Full text: index, quick-start (skimmed), installation (skimmed), configuration, errors-and-recovery, snapshots-and-refs, skeleton-and-drill-down, surfaces, sessions, skills, platforms/macos, guides/headed-mode, guides/observe-act-verify, guides/chromium-and-electron, guides/waiting, guides/batch, guides/traces, guides/mcp, commands/index, commands/interaction, commands/app-window, commands/observation, commands/keyboard, commands/scroll, commands/mouse, commands/wait, commands/batch, commands/system, commands/notifications (partial), commands/clipboard (partial).
Targeted grep only (inert, advertis, activate, foreground, steal): changelog, json-output, platforms/windows, platforms/linux, ffi/index, ffi/api, ffi/build-and-link, ffi/ownership-and-threading.
Count: find reports 38 .mdx files. The last 8 were not read in full.

## 6. Limits (what it cannot do, with evidence)

- It cannot make a Java app analyse in the background by itself: nothing in the docs or code touches app activation state except the listed foreground-taking commands. [inferred from sections 2-3]
- It cannot drive a UI that publishes no AX tree; it does not match pixels. [docs: index.mdx]
- Headless physical input is refused, not emulated. [docs/code: CONCEPTS.md:236]
- AX success proves nothing; verify by reading. [docs: macOS.mdx:64]
- press is never verified. [docs: keyboard.mdx:33]
- Scroll/expand/click inert on CLion are not covered by any documented workaround; no Java guidance exists. [docs: absence]
- mcp, sessions, batch, cursor-overlay add no new capability to a single action. [docs]

## 7. Avenues for the CLion problem

1. Headless `press` by pid. **Rejected after live tests (see [results](results.md)): keys land in whichever window and field had focus last, unverified. Don't use this.** Source reading: it posts keys to the pid with CGEventPostToPid; no focus change, no cursor move. Needs CLion to report an AXFocusedUIElement. Could trigger an IDE action by shortcut without raising it, but analysis may still depend on frontmost state. Risk: keys delivered to whatever has focus inside CLion (an editor edit if the combo is wrong). Not run. [code]
2. `snapshot --app CLion --surface menubar` then `click @ref` on a menu item (e.g. an Inspect/Analyze entry). Semantic AXPress on a menu item, no pointer; the key_dispatch error text itself recommends this as the keyless route. Java menu bars may not be exposed as AXMenuBar. Not run. [code+docs]
3. `set-value` / `select` / `focus @ref` headless on editor or tree items. Semantic; "AX success can be inert". select needs Click advertised (docs/solutions/...native-command-reliability.md). Past trials: click was delivered_verified but inert.
4. `batch` of focus-window, the MCP check, focus-window on the previous app. Not a no-focus avenue; it only shortens the visible steal. focus-window is the documented known-working path (about 0.6 s). [docs+observed]
5. `--headed click @ref` on a tree item. Real click at the verified point after focusing the exact window: steals focus and moves the cursor. [docs]
6. `minimize` then `restore`: speculative; may trigger window-state events. Not documented. Visible to the user.
7. `wait --event focus-changed` and `get`: verification only.
8. mcp, cursor-overlay, sessions: no new capability. [docs]

## 8. Open questions

- Does CLion analyse on key events posted by pid, or only on window activation? Not answerable from this source.
- What available_actions did the CLion tree items advertise, and why do all report selected?
- Does the Java AX bridge expose AXMenuBar for CLion?
- Differences between v1.1.0 docs and main: only 5 commits (mcp, docs, overlay, select rows #503, homebrew).
