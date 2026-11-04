---
okf_version: "0.2"
type: "report"
title: "Critique of the agent-desktop source reading"
description: "Adversarial check of the source-reading claims, with gaps."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# Critique of the synthesis (adversarial completeness check)

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Repo: agent-desktop main 6660fba. Paths are relative to the repo root.

## Claims checked

1. Headless `press --window-id` on a background app is refused. CONFIRMED. `crates/core/src/adapter/system.rs:241-285` returns `refusal()` unless `focused_window` equals the named window. [code]
2. Headless `press --app` posts a CGEvent to the pid, always unverified, needs AXFocusedUIElement. CONFIRMED. `crates/macos/src/system/key_dispatch.rs:61-66` (step CGEventPostToPid, verified false); `:126-143` waits 500 ms for a focused element. [code]
3. Headless `press` with modifiers never AXPresses a menu item. CONFIRMED for headless: `uses_menu_shortcut` is `allow_focus_steal && !modifiers.is_empty()` (`key_dispatch.rs:97-99`). The synthesis' "docs conflict" note is right: in headed mode a modifier combo AXPresses a matching menu item without a CGEvent (`:34-41`), contradicting `apps/docs/.../macos.mdx` ("press never runs a menu item"). Missed value: headed `press cmd+...` of an IDE Analyze/Inspect shortcut becomes a semantic menu AXPress, no keystroke. Still needs headed policy; whether headed press raises the app first was not shown (only `verify_app_focused`, `:55-58`, which verifies and does not raise). [code]
4. Menubar click is AXPress only, headless. CONFIRMED. `chain_defs.rs:37-50`, MENUBAR_CLICK_CHAIN has one step `Action("AXPress")`; CGClick steps return NotDelivered when not headed (`chain_step_exec.rs:79-83`). [code]
5. `menubar_for_pid` needs no frontmost. CONFIRMED as far as reads: `crates/macos/src/tree/surfaces.rs:17-28` reads AXChildren of the app element for AXMenuBar. Whether JBR exposes it is unknown (correctly flagged). [code]
6. Per-ref physical click/type require frontmost app and main window. CONFIRMED. `crates/macos/src/actions/physical_target.rs:34-40` calls `verify_app_focused` and `verify_window_main`. [code]
7. `focus` is only AXFocused set. CONFIRMED. `chain_defs.rs:140-147` FOCUS_CHAIN is one SetBool step on AXFocused. It does not activate the app. [code]
8. `focus-window` = AXFrontmost + AXRaise, and verifies. CONFIRMED. `crates/macos/src/system/focus.rs:61-73`: `focus_app`, `raise_window`, `verify_app_focused`. No restore. [code]
9. "`expand` never goes physical" / headless expand cannot work on JBR. PARTLY UNVERIFIED. Docs table (macos.mdx, "What works headless") says expand, collapse, set-value, select, focus stay semantic under `--headed`. Matches the claim. "Cannot work on JBR" is [inferred] from the observed ACTION_FAILED; no code proof about JBR. Keep it labelled observed, not proven.
10. Verification weakness: tree rows report selected so delivered_verified is meaningless. UNVERIFIABLE in source (observation of JBR); the code claim that verification reads back selected state is plausible. Label [inferred].

Net: no claim found wrong. Two are over-stated as limits: "no command can activate without AXRaise" is true only for the commands read; `launch` of an already-running app and `open-system-surface` were not examined for activation side effects, and `focus-window` on a minimized window (AXMinimized handling in `crates/macos/src/system/window/window_ops.rs:126-141`, `window_ax_state.rs:22`) was not traced.

## Missing

Source areas or commands not covered or not considered:
- The `mcp` command (`src/mcp/mod.rs:1`): every leaf CLI command becomes an MCP tool, each call runs the CLI. So it adds no capability; it only helps the agent call tools directly. The synthesis lists it as an "avenue"; it is not one for the CLion problem. Also `tests/mcp_process.rs` not read.
- `batch` (`crates/core/src/commands/batch.rs`): can chain focus-window, a wait, then restore in one process, shortening the visible steal below the ~3 s observed. Not ranked. Check whether batch lets one command depend on the result of the previous (e.g. reading the previously focused window id).
- `list-windows` / `minimize` / `restore` / `move-window` / `resize-window`: could a CLion window moved off-screen or onto another display still count as frontmost-equivalent? Not analysed. Related question: does AXMinimized true/false restore trigger the IDE's frame-activation sync without taking frontmost? `window_ops.rs:126-141` sets AXMinimized semantically. Untested; cheap to try. Risk: window visibly minimises.
- `set-value` on the editor: `SET_VALUE_CHAIN` and the advice at `crates/core/src/actionability/evaluate.rs:225-235` say text fields lacking a semantic write action are not supported headless. Likely ACTION_NOT_SUPPORTED on Swing editors; not listed.
- `scroll-to` (`SCROLL_TO_CHAIN`, `scroll_into_view.rs`): a semantic reveal that may succeed where `scroll` is inert. Not considered. Relevant to making a file's viewport visible so daemon analysis runs for visible ranges.
- `wait`, `session`, `trace`, `cursor-overlay`: trace output for diagnosing inert actions was not used to rank anything. Low value for the fix but helps explain `delivered_verified` with no effect.
- `open-system-surface`, `launch` on an already-running app (may activate it); `close-app`.
- Second display / Space: `list-displays` exists. Whether an app on another Space counts as frontmost for IDE activation is a macOS question, not answered by the repo. Not tried.
- `--surface menu` / `menu_element_for_pid` (`surfaces.rs:30+`): reading an open menu; irrelevant unless a menu is opened by AXPress on a menubar item, then children are clickable. Worth a one-line mention as the second hop of avenue 2.
- Non-agent-desktop avenues: a dedicated IDE action to run an inspection on a file (CLion MCP might expose other tools); the JetBrains `idea`/`clion` command-line `inspect` runner; running clang-tidy directly. Not agent-desktop but they solve the stated problem without focus. The synthesis' item 1 touches the MCP only.
- Tests/probes: no evidence of tests on Java apps, so every JBR prediction is [inferred]. The synthesis states this; keep it prominent.

## Ranking comments

- Avenue 2 (menubar AXPress) is the most promising agent-desktop-only route; it needs no owner OK only if the menu item is read-only. An "Analyze" item opens a dialog in the IDE and changes state, so owner OK should be required.
- Avenue 3 (press by pid) is flagged needs_owner_ok: correct, since a keystroke into an unknown focused component can change files.
- Add: `batch` focus-steal shortening; AXMinimized restore trick; `scroll-to` on a tree row.
- Avenue 5 needs a build from main; the instructions say not to build tools from inside the offline clone. Build outside the repo is noted; the owner must approve.
