---
okf_version: "0.2"
type: "report"
title: "Avenues for a background CLion (pre-trial)"
description: "Ranked agent-desktop avenues before the live trials; superseded by results.md."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# Avenues for a background CLion

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Binary: `AD=~/.local/share/mise/installs/agent-desktop-<hash>/agent-desktop` (v1.1.0). All commands below are for the main session to run; this pass ran none that touch an app.
Tags: [code] [docs] [inferred]. See [how-it-works](how-it-works.md) and the reader pages in this folder.

## What the source says about the cause
- Nothing in agent-desktop's read paths needs the app to be frontmost [code]. The frontmost need is on the CLion side or unknown.
- The open-source MCP path for get_file_problems (collectLintFiles -> runMainPasses) has no focus gate in the code the JetBrains reader read; staleness from VFS sync on frame activation (SaveAndSyncHandlerImpl.kt:305-332,559-650) is a candidate. The C++ path (Nova/clangd) is closed source and unverified [code + inferred]. See [jetbrains-side](jetbrains-side.md).
- JBR AXPress is fire-and-forget on the EDT and reports success first; outline rows always report selected (OutlineRowAccessibility.m:72-90). So delivered_verified on a tree click means nothing [code].
- JBR has no AXDisclosing setter and no scroll action. Headless expand and scroll cannot work [code]. Do not retry them.
- Setup: install is complete (CLI and helper colocated, grants OK). No setup fix applies. Do not grant Automation, do not reinstall [code + installed stat].

## Ranked avenues
Rank = likelihood x low intrusiveness.

### 1. Diagnose with the existing MCP first (no agent-desktop)
Call get_file_problems with a longer timeout and read timedOut / notAnalyzedReason. Then A/B one file, foreground vs background. Source: AnalysisToolset.kt:114-140, LintFilesAnalysisSupport.kt:467-591.
- Expected: tells whether failure is timeout, staleness or not-analysed.
- Risk: none for background leg. Foreground leg steals focus (developer's choice).
- Owner OK: only for the foreground leg.

### 2. Headless menubar route
```
$AD list-surfaces --app CLion
$AD snapshot --app CLion --surface menubar -i
$AD click @<ref of an Analyze / Inspect / Reload item>        # headless AXPress
```
- Expected: menubar read needs no frontmost (tree/surfaces.rs:17-28). Click is AXPress only, CGClick skipped headless (chain_defs.rs MENUBAR_CLICK_CHAIN) [code]. Whether JBR exposes the screen menu bar, and whether the item runs unfocused, is untested.
- Verify: re-run get_file_problems on an un-analysed file; check the IDE state with `snapshot`.
- Risk: runs an IDE command; a menu may draw. No cursor, no focus. Choose a harmless item.
- Owner OK: no, if the item is read-only/inspection. Yes for anything that edits.

### 3. Headless key by PID (rejected)
**Rejected after live tests (see [results](results.md)): keys land in whichever window and field had focus last, unverified. Don't use this.**

The source reading was: `press <combo> --app CLion` posts by pid; `--window-id` is refused for a background app.
- Expected: needs AXFocusedUIElement in CLion; then CGEvent post_to_pid, step label CGEventPostToPid, always delivered_unverified (key_dispatch.rs:56-66) [code]. Whether AWT processes a PID key while inactive is not in the repo.
- With `--window-id` it is refused for a background app (core adapter/system.rs:241-285) [code].
- Verify: observe the effect in CLion by `snapshot`/get. Choose a combo whose effect is visible and harmless (for example opening a tool window).
- Risk: keystroke lands in CLion's focused component; a wrong combo edits the editor.
- Owner OK: advisable, since it injects input into the IDE.

### 4. Read-only probes of AX behaviour
```
$AD focus @<editor ref>                  # headless AXFocused write; likely ACTION_FAILED
$AD snapshot --app CLion -i --include-bounds
$AD get @<ref> ; $AD is @<ref> ...
```
- Expected: focus only works if AXFocused is settable (chain_defs.rs FOCUS_CHAIN) [code]. Even if it works it does not activate the app.
- Risk: none to low. Owner OK: no.

### 5. Main build (6660fba) headless select on a tree row
Build outside this repo, then `agent-desktop select @<row>` or click. #503 writes AXSelectedRows on the container and reads it back (container_select.rs:70-124) [code].
- Expected: truthful selection if the tree container allows the write; otherwise ACTION_FAILED. Selecting a row probably does not trigger analysis [inferred].
- Risk: none. Owner OK: needs approval to build/run an unreleased binary.

### 6. Short focus steal (known to work)
```
$AD list-windows --app CLion
$AD focus-window --window-id <clion id>
# run get_file_problems
$AD focus-window --window-id <previous app window id>
```
or `$AD --headed press <combo> --app CLion`, which raises then posts the key (cmd.rs press.rs:37-55).
- Expected: error check answers in about 1 s (observed). About 3 s of visible focus steal.
- Verify: get_file_problems returns. Risk: steals focus, may swallow the user's typing. No cursor move.
- Owner OK: yes.

### 7. Headed click on a tree row
`$AD --headed click @<ref>` raises CLion, moves the real cursor, sends a real click (physical_click.rs). Selects the row truthfully via Swing. Cursor is not restored.
- Risk: cursor moves, focus steal, can click the wrong thing. Owner OK: yes.

### 8. Expand a tree node physically
Only routes: `--headed click` on the disclosure triangle or `--headed press right` with the row focused. `expand` itself never goes physical (chain_disclosure_steps.rs:22-67). Needs CLion frontmost.
- Risk: cursor + focus. Owner OK: yes.

### 9. Open the target file before the check (issue #3085 workaround)
Make the file the selected editor. Via an MCP open-file tool, if the CLion MCP offers one, this needs no focus. Via the UI it needs a click (avenue 7) [docs + inferred].
- Owner OK: no for an MCP tool; yes for UI.

### 10. IDE settings (report only)
Sync-on-frame-activation, background sync, and registry `vfs.background.refresh.on.idle` may explain stale results [code, SaveAndSyncHandlerImpl.kt]. Changing them is an IDE settings change.
- Owner OK: yes. Not recommended before avenue 1 shows staleness.

### Low value, skip
- `launch CLion`: no-op on a running app unless `--activate` (focus steal) (launch_bridge.m:154-163).
- `session`, `cursor-overlay`, `mcp`, `batch`: no new capability. `batch` only shortens the steal.
- `permissions --guide/--request`: nothing missing; would open System Settings.
- Raw `--headed mouse-click --xy`: moves cursor, likely activates CLion; no advantage over avenue 7.
- minimize/restore: speculative, visible.

## Real limits
- No command activates an app without AXRaise, and no restore of focus or cursor (focus.rs:61-73; nc_session.rs:143-149).
- Headless physical input is refused. Per-ref physical click/type refuse unless the app is frontmost (physical_target.rs:34-40).
- Tool cannot confirm CLion did the work: press is unverified; tree-row click verification is trivial on JBR.
- Nothing in docs, probes or tests covers Java/Swing/JetBrains or macOS 27.
