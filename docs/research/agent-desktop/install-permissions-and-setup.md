---
okf_version: "0.2"
type: "report"
title: "agent-desktop install, permissions and setup on macOS"
description: "mise install, the helper binary, TCC grants, env vars and state."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# agent-desktop: install, permissions and setup (macOS)

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Paths are relative to the repo root (`vercel-labs/agent-desktop`, main 6660fba) unless marked "installed". Tags: [code], [docs], [both], [inferred].
Installed binary: v1.1.0 (mise github backend, `agent-desktop-qeahdwgd`). Host: macOS 27.2 (`sw_vers`: 27.2, build 26B123), arm64.

## 1. Verdict on our install

Our install is complete and correctly set up. Nothing missing explains the inert actions. [both]

- Both files are present, side by side, same dir, same mtime: `agent-desktop` and `agent-desktop-macos-helper` (installed `ls -la`). [inferred from ls]
- The CLI finds the helper by looking in its own directory (`clipboard_helper_identity.rs:30-48`). [code] mise runs it through a shim (`~/.local/share/mise/shims/agent-desktop`), but `current_exe()` is the real install path, so the colocated helper is found. [inferred]
- Helper file checks (`clipboard_helper_identity.rs:76-112`): owner = us, no group/world write, executable, one hard link, no dangerous ACL, all parent dirs not group/world writable. Our files are `-rwxr-xr-x <user>`, nlink 1, every ancestor is `drwxr-xr-x` owned by us or root. They pass by inspection. [code + installed stat] (I did not run a clipboard command to prove it live.)
- `status`: accessibility granted, screen_recording granted, automation `unknown`, state_root `~/.agent-desktop`, supported_surfaces include window, focused, menu, menubar, sheet, popover, alert, dock, menu-bar-extras. [installed run]
- `permissions` gives the same three states. [installed run]
- State root exists, mode 0700, with `latest_snapshot_id`, `refstore.lock`, `snapshots/`, `sessions/trial/` (a snapshot namespace with no manifest; `session list` returns `[]`). Normal. [both: `apps/docs/content/docs/configuration.mdx` "State root"]

## 2. How permission state is decided

All in `crates/macos/src/system/permissions/mod.rs`. [code]

| Permission | API called | Lines | Meaning |
|---|---|---|---|
| accessibility | `AXIsProcessTrusted()` | 21-23, 208-210 | granted/denied only |
| screen_recording | `CGPreflightScreenCaptureAccess()` | 34-42, 212-214 | granted/denied only |
| automation | `AEDeterminePermissionToAutomateTarget` for `com.apple.systemevents`, ask_user=0 | 75-107, 216-218 | status 0 granted; -1743 denied; -600 and -1744 and anything else `unknown` (241-250) |

- `permissions` and `status` never prompt (`report`, lines 132-141). [code] [docs `platforms/macos.mdx` "Grant and check permissions"]
- `permissions --request` is the only prompting path. It re-executes the CLI itself as a "permission helper" (env marker `AGENT_DESKTOP_PERMISSION_HELPER` etc.) and prompts for Accessibility, Screen Recording, then Automation (`permission_helper.rs:30-70`, `mod.rs:143-176`). The helper checks its parent PID and identity (`permission_helper.rs:136-155`). [code]
- `permissions --guide` opens System Settings with an on-screen panel (`permission_guide.rs:15-52`). It covers Accessibility and Screen Recording only. It picks the "nearest ancestor that runs from an app bundle" as the host to show (`permission_guide.rs:127-150`). [code]
- Automation is used for exactly one feature: opening Notification Center through `osascript` and System Events (`notifications/nc_session.rs:66, 277-285`). No other command calls `require_automation_permission`. [code, grep]
- Why `automation: unknown` is harmless for CLion: it only means macOS would prompt. It is not used by click/expand/scroll/focus-window/press. [code]
- No code reads or mentions Input Monitoring / Listen Event / IOHID / `kTCCService*`. [code, grep over whole repo returned nothing]

### What permission each CLion-relevant path needs
- AX reads and writes (snapshot, get, click via AXPress, expand, set-value, AXFrontmost, AXRaise) need only Accessibility trust. A missing grant yields `kAXErrorAPIDisabled`, mapped to `PERM_DENIED` (`system/focus.rs:186-204`, `system/key_dispatch.rs:167-182`). [code]
- Observed results from the main session (snapshot works, `focus-window` writes AXFrontmost and raises) prove AX read and write trust works for the herdr-core-charged process. The inert actions came back as `ACTION_FAILED`, `ACTION_NOT_SUPPORTED` or `delivered_verified` with no change, not `PERM_DENIED`. So the permission layer is not the cause of those. [inferred, strong]
- `screenshot` needs Screen Recording; it works. [docs + observed]
- Synthetic keys and mouse (`press`, and anything `--headed`) post CGEvents: `post_to_pid` when `--app` is given, else `CGEventTapLocation::HID` (`input/keyboard/keyboard_event.rs:134-140`). The event source is `HIDSystemState` (line 129-132). The code does not check any permission for posting. macOS gates event posting under the Accessibility class [inferred], so our Accessibility grant should cover it, but the tool has no preflight that proves it. Unverified: a silent drop of posted events cannot be excluded from the code alone. Only a live test tells.

## 3. What the helper binary is for

- `agent-desktop-macos-helper` is the clipboard helper, not a permission helper. Source: `crates/macos/src/bin/agent-desktop-macos-helper.rs:1-3` calls `clipboard_helper_from_env`, exported at `crates/macos/src/lib.rs:11`. [code]
- It runs clipboard-get/set/clear in a separate, validated process (`input/clipboard/clipboard_helper_client.rs:13-40`, protocol in `clipboard_helper_protocol.rs`). Operations are `clear`, `read:<fmt>`, `write:<fmt>`. [code]
- The CLI refuses clipboard commands if the helper is missing or fails the file checks (`clipboard_helper_identity.rs:46-48`: "No colocated packaged helper was found"). [code]
- `AGENT_DESKTOP_MACOS_HELPER_PATH` overrides discovery; it must be absolute and the basename must be exactly `agent-desktop-macos-helper` (`clipboard_helper_identity.rs:21-27, 61-63`). [code] [docs `configuration.mdx` env table]
- The helper build id must match the CLI's (`BUILD_IDENTITY`, `clipboard_helper_protocol.rs:6`). Both come from the same v1.1.0 archive, so they match. [inferred]
- No other command uses it. `type`, `click`, `press`, `focus-window` do not touch the clipboard (grep of `input/keyboard` and `actions` for "clipboard" returned nothing). So a missing or broken helper could not make a tree click or expand inert. [code, grep]
- Release archives and npm ship both files; docs say "extract the executable and its platform helper into one directory" (`docs/install.md` "Release archives"). [docs]

## 4. Environment variables and config

There is no config file. [docs `configuration.mdx` line 6] Variables read by the code (grep of `std::env::var*`): [code]

| Variable | Effect | Where |
|---|---|---|
| `AGENT_DESKTOP_HOME` | absolute path; relocates state root; must be a private dir we own | `crates/core/src/storage/state_root.rs:13,33` |
| `AGENT_DESKTOP_SESSION` | session id fallback | `src/main.rs:176` |
| `AGENT_DESKTOP_AGENT_ID` | subagent id fallback; required for desktop actions in a multi-agent session [docs] | `src/main.rs:187` |
| `AGENT_DESKTOP_MACOS_HELPER_PATH` | helper override | `clipboard_helper_identity.rs:21` |
| `RUST_LOG` | stderr log filter [docs] | tracing setup |
| internal only | `AGENT_DESKTOP_INTERACTION_LEASE_FD`, `AGENT_DESKTOP_PERMISSION_*`, `AGENT_DESKTOP_MACOS_HELPER_TOKEN` and similar | adapter/helper plumbing |

- No environment variable or setting switches on any extra capability or loosens a policy. The only policy switch is the per-call `--headed` flag, and `--force` for quit shortcuts. [code, grep; docs `configuration.mdx`]
- The interaction lock lives outside the state root (under `/tmp`); we have `/tmp/agent-desktop-501`. All agents of one user share it. [docs `configuration.mdx` last line; installed `ls /tmp`] Consequence: concurrent agent-desktop actions from several sessions serialize on this lock. [inferred]

## 5. Sessions and state on disk

- Layout: `latest_snapshot_id`, `snapshots/<id>/refmap.json`, `sessions/<id>/{session.json, snapshots/, trace/, clipboard/}` (`configuration.mdx` "Layout"). [docs]
- `session start` returns an id and does not activate it for later processes; you pass `--session` or set `AGENT_DESKTOP_SESSION` (`agent-desktop --help` "REF IDs"; `sessions.mdx`). [both]
- Session selection order: `--session`, then env, then global namespace (`sessions.mdx`). [docs]
- A session adds ref isolation and traces. It adds no capability to act on an app. [docs `sessions.mdx` intro]
- `cursor-overlay enable` draws a click-through overlay window; it "never moves the OS pointer or activates an app" (`skills/agent-desktop-macos/SKILL.md` "Cursor overlay"). It is presentation only and requires a session. [docs]
- Ref durability: refs carry a private AX remote token, so a ref resolves back to the same element across processes. Evidence is `probes/macos/FINDINGS.md` M1-1..M1-13 on macOS 26.4 (Finder, a SwiftUI fixture, Safari, Chrome). A token is an address, not a capability (M1-11). Nothing about Java/Swing. [docs/probe]
- `docs/solutions/runtime-errors/2026-09-20-xcode-project-disclosure.md` is a close relative of our tree problem: Xcode navigator `expand` returned `ACTION_FAILED` because the adapter ignored `AXValue` on `AXDisclosureTriangle`. That was fixed in the adapter (state reader) and is likely in v1.1.0. A lesson, not proof, for CLion: read the raw AX attributes of the tree item (`get --property states`, role/actions) before deciding the action is inert. [docs]

## 6. The mcp server (main only; absent from our v1.1.0)

- `agent-desktop mcp` exists in main (commit 6660fba, `src/main.rs:87-88`, `src/mcp/`). Our installed binary answers `INVALID_ARGS ... unrecognized subcommand 'mcp'`. `git show v1.1.0:src/main.rs` has no "mcp". [code + installed run]
- It is a thin stdio wrapper: each tool call spawns this same binary as a child process with the server's global flags plus the tool's argv (`src/mcp/call.rs:25-35`). [code]
- So it adds no new reach. A tool "cannot pass a global flag" such as `--headed`; only the server's own command line can (`apps/docs/content/docs/guides/mcp.mdx` "Apply global flags once"). [both] For the CLion problem, `mcp` changes nothing about what AX can do.
- TCC note [inferred]: each tool call is a child of the `mcp` server, which is a child of the MCP client. The responsible app is whichever app tree launched the client, not herdr-core necessarily. A different launcher would need its own grant.

## 7. Differences between v1.1.0 and main that touch setup/actions

`git log v1.1.0..HEAD` (5 commits): mcp (#519); homebrew docs (#524); docs simplification (#481); cursor overlay drawn above menus (#511); "select list rows that only their container can select" (#503). [code]
- Permissions code and helper code are unchanged between the two (diff of `crates/macos` lists only actions/tree/cursor_overlay files). [code, `git diff v1.1.0 HEAD --stat -- crates/macos`]
- #503 is relevant to tree items: `actions/select/container_select.rs:1-80` writes `AXSelectedRows` (outline/table), `AXSelectedChildren` (list/browser column) or `AXSelectedCells` on the ancestor container for roles row/treeitem/cell/listitem/option/tab, verified by readback. In v1.1.0 that path is missing. A main build might make `click` or `select` work on a tree item where v1.1.0 only reports `delivered_verified` without effect. [code] [inferred for CLion; untested]

## 8. macOS 26/27 notes

- Probes ran on macOS 26.4 in a VM (`probes/macos/FINDINGS.md:17`). Our host is macOS 27.2. No probe covers 27. [code/probe]
- macOS 27 renames the Accessibility list to "Device Control and Data Access" (`permissions/mod.rs:3`; `skills/agent-desktop-macos/SKILL.md:23,31`; `troubleshooting.md` PERM_DENIED). That is a label change only. [both]
- `FINDINGS.md:37`: "behavior across macOS major versions" is not yet measured. [probe]
- The docs state the macOS page "was not run for these docs" (`platforms/macos.mdx:6`). [docs]
- No repo text mentions JetBrains, IntelliJ, CLion or Swing/AWT as a supported or tested app (grep: only unrelated hits in CSS/Windows overlay/lockfile). [code, grep]
- Chromium renderer activation (AXEnhancedUserInterface/ManualAccessibility) is keyed on Electron/CEF framework folders inside `Contents/Frameworks` (`system/renderer_kind.rs:5-34`). CLion has neither, so no equivalent "turn on accessibility" step exists for Java. [code]

## 9. TCC attribution (our herdr-core finding)

- Code agrees with it: TCC charges a command-line tool to the app that launched its process tree; the guide shows the nearest ancestor with an `.app` bundle, and for terminal servers outside LaunchServices it derives the bundle from the executable path (`permission_guide.rs:127-150`, comment "Terminal servers such as Rex Server are not registered with LaunchServices"). [code]
- If no ancestor is an app, the guide offers the `agent-desktop` binary itself (`troubleshooting.md` PERM_DENIED). [docs]
- Every CLI call is a fresh process (no command host; command host removed, leftovers killed by `process/legacy_host.rs`), so grants are re-read per call. [code]

## Limits

- Headless `scroll`, `expand` on an `AXOutline` row, and similar actions only try AX actions the element advertises; they stop when exhausted (`troubleshooting.md` ACTION_FAILED: "The semantic chain tries only the actions the element advertises, then stops"). If the app advertises an action and ignores it, the tool cannot know. [docs] The docs say so: "AX return codes do not prove an effect" (`platforms/macos.mdx` "What works headless"). [docs]
- No permission, env var or config can add an input route. All input paths are: AX actions, AX attribute writes, `CGEventPostToPid`, `CGEventPost(HID)`. [code]
- `key-down`, `key-up`, `mouse-down`, `mouse-up` fail closed in stateless mode (`--help`). [installed help]
- `press` headless needs an `AXFocusedUIElement` in the target app and sends the key by PID without focusing (`key_dispatch.rs:45-59`). For `return` and `escape` with no modifiers it first tries AXConfirm/AXCancel on the focused element (101-110). [code]
- `--headed press` with a modifier first tries to find the matching menu bar item by `AXMenuItemCmdChar` and `AXPress` it, with no key event (`key_dispatch.rs:33-44`, `key_dispatch_menu.rs:16-57`); only if none matches does it check the app is frontmost and send keys. [code]
- Nothing in the repo makes an app run background tasks that it ties to its own activation. The tool has no "app activated" notification, only AXFrontmost writes and AXRaise (`focus.rs:15-40, 61-73`). [code]
- Automation permission is irrelevant to every command except the Notification Center ones. [code]
- The macOS probe set never touched Java/Swing, or macOS 27. [probe]

## Avenues for the CLion problem (setup-related)

1. No setup fix found. The install is complete; do not spend time reinstalling, granting Automation, or adding the helper path. Expected effect on CLion: none. Risk: none. Confidence: high. [both]
2. `agent-desktop permissions --guide` / `--request`: do not run. They open System Settings or prompt, and nothing is missing. Risk: opens windows, steals focus. [code]
3. Try the v1.1.0 `--headed` tree click, with caution: `agent-desktop --headed click @ref` on a tree item. Per `macos.mdx` "What works headless", headed makes click physical first: core focuses the exact window, then a real click goes to the verified point (`SKILL.md` "What differs on macOS"). Expected: CLion comes to front (steals focus), cursor moves to the item, item selected, and CLion analysis runs because it is frontmost. This does not solve the "do it while behind another app" goal, it only moves focus. Risk: focus steal + cursor move. Confidence: medium.
4. Build or fetch main (6660fba) and test headless `click`/`select` on a tree row: #503 adds container-level selection by `AXSelectedRows`/`AXSelectedChildren` with readback (`container_select.rs:1-80`). This is the only code path in the repo that could change a tree item's selection without a physical event. Expected: if CLion's `AXOutline` makes `AXSelectedRows` writable, the click works and reports `delivered_verified` truthfully. Risk: none to the user (headless). Confidence: low-medium; selecting a tree row does not itself trigger analysis of a file unless it opens the file. Note the project rule: build from a tree outside this repo, never run scripts from inside the clone.
5. `--headed press cmd+<key> --app CLion` for a menu item with a shortcut: menu-bar `AXPress` path first (`key_dispatch.rs:33-44`). Expected: runs the menu item through AX without a key event; the app may or may not come to the front. A menu command that opens a file or runs inspection might trigger analysis. Risk: possible focus change; the command acts on CLion's current editor. Confidence: low. This was reported as untried.
6. Headless `press` by pid. **Rejected after live tests (see [results](results.md)): keys land in whichever window and field had focus last, unverified. Don't use this.** Source reading: it posts a key by PID with no focus change (`key_dispatch.rs:56-59`, `keyboard_event.rs:134-136`). Expected: key reaches CLion's key window, but it does not make CLion "active", so the on-activation analysis is unlikely to start. Risk: types into whichever editor CLion has focused; no cursor move. Confidence: low.
7. `mcp` (main only): no new capability (`src/mcp/call.rs:25-35`). Skip for this problem.
8. `session`, `cursor-overlay`: presentation/state only. No effect on CLion. Risk: overlay window drawn on screen (click-through). [docs]
9. `focus-window` then hand back (already measured, ~0.6 s each way): the one route that is known to work. Risk: visible focus steal ~3 s. [observed]

## Open questions

- Does posting a CGEvent from the herdr-core-charged process actually reach apps? Our Accessibility grant should cover it [inferred], but the code has no preflight; only a live `press --app` test shows it.
- Does CLion's tree expose `AXSelectedRows` as settable? Raw AX (outside this tool) would tell; main's #503 would use it.
- Does CLion trigger analysis from window activation (`windowDidBecomeKey`) rather than from AX events? Not answerable from this repo.
- Does the shim path change the process tree enough to change the TCC responsible process? Our tccd finding says herdr-core is charged; the code in `permission_guide.rs` follows ancestors, so it agrees. A shim is only an exec hop.
