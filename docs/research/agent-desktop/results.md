---
okf_version: "0.2"
type: "report"
title: "Live results: CLion error checks in the background"
description: "Background CLion error checks with agent-desktop and CLion MCP: the isInActiveProject cause, live runs, stale answers and the agreed procedure."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# Live results: CLion error checks in the background (2026-11-03)

CLion 2026.3 RC on macOS 27.2, agent-desktop 1.1.0. One Claude session and one Codex session tested independently, then agreed on the procedure below.
- The tests used a small CMake repro project and a larger CMake project.

## Cause

- `DaemonCodeAnalyzerImpl.isValidEditor` calls `isInActiveProject`. Codex read this in CLion's bytecode.
  - With one project open, it returns true straight away.
  - With two or more projects open, it needs an active AWT window that belongs to the editor's project.
  - `EditorTrackerImpl` clears the active editors when that window loses focus.
- So "CLion must be frontmost" is true only when several projects are open.
- The open-source reading in [jetbrains-side](jetbrains-side.md) missed this gate.

## What the live runs showed

CLion was behind another app throughout. Measurements stay in the private project and aren't published here.
- **Two projects open:** checks of the repro project's files timed out, even after `open_file_in_editor`. The editor showed "Analyzing…" stuck.
- **One project open:** checks of files opened through MCP with `projectPath` answered without CLion coming to the front. Two sessions saw this independently.
- **Several projects:** `focus-window --window-id`, then the check, then focus back works, but the focus change is visible.

## Stale answers after an outside edit

- In the background, CLion picks up an edit made by another tool several seconds late. Until then, `read_file` over MCP returns the old text.
- During that gap, `get_file_problems` answers promptly for the old text. A freshly planted syntax error came back clean.
- Once `read_file` matched the disk, the next check was right.
- So an empty `errors` list means the check completed, not that it saw the current text. Matching the text is a guard, not proof. The acceptance test is a planted change.

## The procedure both sessions agreed

1. **Take a shared lock**, so two agents never drive CLion at once.
2. **Get the open projects.** Call `execute_tool` without `projectPath`; the error lists the open projects by absolute path. Refuse if any other project is open.
3. **Find the project's window** with `agent-desktop list-windows --app CLion`. Match the title `<project name> – <file>`, and require exactly one match.
4. **Open the file in that project:** `open_file_in_editor` with `projectPath`. Then wait until the window title names the file.
5. **Wait until CLion's copy matches the disk**, by polling `read_file`.
6. **Run `get_file_problems` with `projectPath`.**
   - Reject any answer that has no `errors` list, names a different `filePath`, or has a `timedOut` that isn't a boolean.
   - Retry when it times out.
7. **Record the front app before and after.**
- **Keystrokes:** none.
- **Several projects open:** use an explicit fallback. `focus-window --window-id` on the project's window, and in a `finally`, focus the exact window that was in front before. Refuse if that window can't be identified.

## agent-desktop findings

- **`press <keys> --app CLion`:** posts to the process (`CGEventPostToPid`) and reports `delivered_unverified`.
  - The keys land in whichever CLion window and field had focus last. A test with `cmd+shift+o` showed no popup and changed nothing.
  - Don't use it to target a specific project.
- **`press --window-id`:** refuses a background window, with `STALE_REF`, `exact_window_focus_unconfirmed` and `physical_delivery_started:false` (`crates/core/src/adapter/system.rs:241-286`). Keep that fail-closed route, and never fall back to `--app`.
- **`snapshot -i`:** reads the main window in the background (85 refs in 0.44 s), and `get` and `screenshot --window-id` work.
- **`snapshot --surface menubar`:** reads CLion's native menu bar in the background (729 refs in 2.1 s).
- **Swing tree and editor:**
  - A tree `click` reports `delivered_verified` but has no effect, whether CLion is in front or behind.
  - A tree `expand` returns `ACTION_FAILED`.
  - An editor `scroll` returns `ACTION_NOT_SUPPORTED` (`scroll_advertised_but_inert`).
- **"About CLion":** a headless click opened the About window, and its Close button closed it. That was with two projects open. With one project open, Codex's click produced no window. Not generalised.
- **Native close button:** a headless AXPress on a project window's close button closed that project.
- **`focus-window --window-id`:** works in about 0.6 s, and the error check answers right after it.
- **Permissions:** tccd charges agent-desktop to `herdr-core` when it's started from a herdr tab, so the grants go to `herdr-core`.

## Not tried, by either session

- `--headed`;
- `select`, `set-value`, `focus`, `batch` and sessions;
- the `mcp` subcommand on main;
- CLion's "Support screen readers" setting. Per JetBrains' docs it adapts controls, keyboard and tooltips, and nothing suggests it affects analysis.

None is needed for the procedure.

## Gaps

- **Freshness:** not shown for files inside a CMake target after an outside edit. The planted-change test used a file outside every target, so only syntax errors showed.
- **Timeouts:** no coroutine stack was captured, so it's not known which internal wait stalls.
- **YouTrack IJPL-231204:** unread; scraping failed on every engine.
- **Codex's provider searches** (Exa, Firecrawl, Last30Days, Context7, GitHub): not run, because its research secrets profile was missing.
