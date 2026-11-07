---
okf_version: "0.2"
type: "report"
title: "Headed vs headless on a JBR/Swing IDE"
description: "Why keyboard and focus need an active IDE, why semantic AX actions don't, with the JBR source lines and the live observations."
resource: "https://github.com/JetBrains/JetBrainsRuntime"
version: "jbr-release-25.0.4.1b635.79"
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [jbr, swing, macos, accessibility, focus, agent-desktop]
---

# Headed vs headless

## The rule (JBR source, read by dotfiles-c6)

- `CPlatformWindow.rejectFocusRequest` (macosx/classes/sun/lwawt/macosx/CPlatformWindow.java:978-987)
  says "Cross-app activation requests are not allowed". It rejects **every focus request whose cause
  is not MOUSE_EVENT while the app is inactive**.
- `LWWindowPeer.requestWindowFocus` checks that first. `LWComponentPeer.requestFocus`
  (unix/classes/sun/lwawt/LWComponentPeer.java:904+) then rejects requests whose parent window isn't
  focused.
- AXFocused=true (agent-desktop `focus`) goes through `CAccessibility.requestFocus`
  (CAccessibility.java:549-562) to an `invokeLater` `Component.requestFocus()`. Its cause is not
  MOUSE_EVENT, so it is rejected while CLion is inactive.
- Result: **no Java focus owner exists while the IDE is inactive.** The app's AXFocusedUIElement (which
  reports Java `getFocusOwner`, CommonComponentAccessibility.m:1178) is an empty element.
- agent-desktop `press` is CGEventPostToPid, so keys go to the Java focus owner. With none, they go
  nowhere.

## Observed

| situation | Java focus owner | keys reach |
|---|---|---|
| CLion in the background | none: an empty AXFocusedUIElement | nothing; background `press up` changed nothing (screenshot) |
| background + `focus @combo` or `focus @tree` | still none | nothing |
| background + gear popup opened by AXPress | none; Java's focused window is the popup | nothing |
| after `focus-window` (CLion active) | the window's last focus owner (the tree in a fresh Settings) | that component; `press tab` moved it to the combo at once |
| after a physical click (headed) | the clicked component | it; macOS also activates the app |

- The brief said `press tab` doesn't move focus. That was true only while CLion was inactive.
- Java remembers the last focus owner per window. After Cmd-Tab away and back, focus returned to the
  combo (t=236.4 and 259.9 in the owner's recording).

## What this means for automation

- **Background-safe:** semantic AX that doesn't need focus: AXPress on buttons, links and
  checkboxes; AXValue on text fields; AXSelected on a combo's popup child (→
  `AccessibleJComboBox.addAccessibleSelection`); reading.
- **Needs activation:** any key; Settings opening (see the Settings page); running popup or list rows;
  dropdown rows other than 0.
- Headed clicks work because they are MOUSE_EVENTs and activate the app. "Headless" in agent-desktop
  only means no pointer or keyboard synthesis. `focus-window` still brings the app forward.
