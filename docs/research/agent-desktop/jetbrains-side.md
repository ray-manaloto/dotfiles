---
okf_version: "0.2"
type: "report"
title: "JetBrains side: JBR accessibility bridge and get_file_problems"
description: "The JBR AX bridge and the open-source get_file_problems path; its no-focus-gate conclusion is superseded by results.md."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# JetBrains side: JBR a11y bridge and `get_file_problems`

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Scope: why agent-desktop cannot make CLion's MCP `get_file_problems` work with the IDE in the background. This page covers the IDE side only. "An IDE project" means the project open in CLion.

Tags: [code] read in source, [docs] read in docs, [both], [inferred] my reasoning, not proven.

Paths below name the upstream file (JetBrainsRuntime, intellij-community, OpenJDK); copies were read locally and are not kept here.

## Short answer

1. The JBR bridge advertises actions it then runs asynchronously with no result. AX says "ok" no matter what happens on the Java side. [code]
2. Nothing in the open-source MCP lint path checks window focus. The frontmost-only behaviour must come from something else. The best candidates are stale VFS/PSI state after deactivation, or the closed-source CLion Nova backend. Neither is proven. [code] + [inferred]
3. "Support screen readers" does not gate AXPress. [code]

## Question A: the JBR accessibility bridge

### How actions are advertised and run

- Actions come from the Java `AccessibleAction`. The native side maps the action description string to an AX action. "toggleexpand" and "click" both become AXPress. [code] `jbr/JavaAccessibilityAction.m:99-109`, `jbr/CommonComponentAccessibility.m:618-679`
- `accessibilityPerformPress` calls into Java `CAccessibility.doAccessibleAction`. Java side is `LWCToolkit.invokeLater`, so it is fire and forget. The AX call returns success before the EDT runs the action. [code] `jbr/JavaAccessibilityAction.m:156-182`, `jbr/CAccessibility.java:149-175`
- Result: "delivered" from the AX layer means "queued". It says nothing about whether the tree expanded. This matches the "delivered_verified but nothing changed" and "inert" patterns seen in trials. [inferred from code]

### Tree rows

- IntelliJ `Tree` uses the stock Swing `AccessibleJTree`. `AccessibleJTreeNode.doAccessibleAction(0)` toggles expand. [code] `ij/Tree.java`, `jdk/JTree.java:5686-5752`
- So AXPress on a row can work if the EDT runs it and the node is the right one. Whether it did is only visible by re-reading the tree afterwards.
- `OutlineRowAccessibility.isAccessibilitySelected` always returns YES, so selected state is not usable as a signal. [code] `jbr/OutlineRowAccessibility.m:72-90`

### What JBR does not implement

- No `setAccessibilityDisclosed:`, so a write to AXDisclosing or AXExpanded has no native setter. [code] `jbr/OutlineRowAccessibility.m`, `jbr/CommonComponentAccessibility.m:1224-1278`
- No AXScrollToVisible and no scroll action on the scroll area. [code] `jbr/ScrollAreaAccessibility.m`
- agent-desktop does reference AXDisclosing, AXExpanded and AXScrollToVisible (`crates/macos/src/actions/chain/chain_disclosure_steps.rs:128`, `tree/properties/node_attribute_names.rs:26`, `actions/scroll_into_view.rs:170`). Its disclosure chain tries AXExpand, then a settable AXExpanded, then AXPress, and verifies by polling for 200 ms. On JBR the first two have nothing to bind to. Only AXPress is real. [code, both repos]

### Dependence on VoiceOver, "Support screen readers", active frame

- "Support screen readers" is `GeneralSettings.isSupportScreenReaders`, which calls `ScreenReader.setActive`. It changes editor focusability and how much text detail the a11y layer exposes. It is not read anywhere on the action path. [code] `ij/AccessibilityUtils.kt:31-91`, `ij/ScreenReaderStateManager.kt`, `ij/ScreenReader.java`, `ij/EditorComponentImpl.java:149-162`
- IntelliJ turns the setting on at startup if macOS says VoiceOver is on (`com.apple.universalaccess voiceOverOnOffKey`), or if `-Dforce.screen.reader.detection=true` is set. [code] `ij/ScreenReaderStateManager.kt`
- Active frame: the native element tree is built from the focused window's Java component. I found no code that makes AXPress depend on the frame being active. A background window still has a tree. [inferred]
- Not tested here: whether the tree is complete for a background window. That needs a live run.

## Question B: why `get_file_problems` seems to need CLion frontmost

### What the code does

- `get_file_problems` (`AnalysisToolset.kt:114-140`) calls `collectLintFiles` (`:419-470`) under `withTimeoutOrNull` and `withBackgroundProgress`. [code]
- `collectLintFiles` (`LintFilesAnalysisSupport.kt:158-209`) calls `awaitExternalChangesAndIndexing`, then preparers, then `collectLintFileResults` (`:309-361`). [code]
- `awaitExternalChangesAndIndexing` (`analysis.util.kt:22-50`): mark suspicious files dirty, refresh through RefreshQueue, `commitAllDocuments`, `runWhenSmart`. [code]
- `runLintMainPasses` (`:467-591`): mutex, 20 s per file, up to 100 retries, cancelled by write actions. It calls `runMainPasses(psiFile, document, daemonIndicator)` inside `runInsideHighlightingSession` (`:593-625`). [code]
- `DaemonCodeAnalyzerImpl.runMainPasses` (`DaemonCodeAnalyzerImpl.java:495-541`) runs the highlighting passes directly. There is no editor-visibility or focus check in that path. [code]
- The docs say results can carry `timedOut`, `notAnalyzedReason` and `more`. [docs] `clion-mcp-doc.md:247`

### The timer daemon is gated, but this path bypasses it

- The timer-run daemon skips work for PowerSaveMode, no selected editors, and a project that is not the active one. [code] `DaemonCodeAnalyzerImpl.java:1235-1262`, `:1729-1750`
- `DaemonListeners` registers power-save (`:361-367`) and has no `ApplicationActivationListener`. So the daemon is not paused on app deactivation by that class. [code]
- `get_file_problems` calls `runMainPasses` itself, so those timer gates should not apply. [inferred]

### What does change on deactivation

- `SaveAndSyncHandlerImpl` saves on frame deactivation and refreshes the VFS on activation, subject to `isSyncOnFrameActivation` and `isBackgroundSync`. `UnfocusedBackgroundRefreshController` and registry `vfs.background.refresh.on.idle` control idle refresh. [code] `SaveAndSyncHandlerImpl.kt:305-332`, `:559-650`
- If edits happen on disk while CLion is in the background and sync-on-activation is the only refresh, PSI can be stale until CLion is activated. `awaitExternalChangesAndIndexing` does ask for a refresh, which should cover this. How well it works for a backgrounded app is unverified. [inferred]

### CLion Nova

- CLion 2026.3 runs Nova (Radler, a Rider.Backend process) plus a clangd process. Frontend and backend are closed source. [both] local `nova.txt`, `clion.vmoptions`
- For C++ files the problems likely come from the backend, not from the open-source daemon passes. The open-source gate analysis may therefore not describe C++ behaviour. [inferred]

### Prior reports

- Claude Code issue #3085, "ide:getDiagnostics times out if file is not active". The workaround is a PreToolUse hook that opens the file in the IDE. That is a different tool (Claude's own IDE bridge), but the same symptom. [docs]
- YouTrack IJPL-231204: scrape failed on every engine. Unread.

### Settings that might allow background checks

Report only. Changing any of these needs the developer's OK.
- Sync/refresh: `isSyncOnFrameActivation`, `isBackgroundSync`, registry `vfs.background.refresh.on.idle`. [code]
- Power Save Mode: off. [code]
- Open the target file in an editor in CLion (the #3085 workaround). It makes the file a selected editor for the timer daemon. [docs] + [inferred]
- Local options files read (read only): `advancedSettings.xml`, `mcpServer.xml`, `mcpToolFilter.xml`, `ide.general.xml`. I found nothing that sets a focus requirement.
- Could agent-desktop flip a setting? Only through the settings UI, which means focus, clicks and typing in CLion. That is not background work. [inferred]

## Limits

- The JBR bridge reports AX success for AXPress without waiting for the EDT. Only a re-read of the tree shows the effect. [code]
- No native setter for AXDisclosing/AXExpanded, and no scroll-to-visible action. Writes to them cannot work on JBR. [code]
- Selected state is always YES for outline rows, so it cannot confirm a click. [code]
- "Support screen readers" and VoiceOver change text detail and focusability, not action handling. Turning them on is unlikely to fix AXPress. [code]
- The open-source MCP path shows no focus gate, so I cannot cite code for "needs frontmost". The cause is unproven. [code]
- Nova and clangd internals are closed or unread. [inferred]
- I did not run anything against CLion. No live test of background behaviour was done in this pass.

## Avenues for the CLion problem

Intrusiveness scale: none, cursor moves, focus steal, keyboard to app, other.

1. `agent-desktop` AXPress on a tree row, then re-read the tree.
   - Mechanism: JBR queues `AccessibleAction` 0 on the EDT. [code] `jbr/CAccessibility.java:149-175`
   - Prediction: AX returns ok. The row expands if the EDT is alive and the node is the right one. Verify by re-reading.
   - Intrusiveness: none. Confidence: medium that it works, high that AX success is not proof.

2. Open the target file in CLion before calling `get_file_problems`, as in the #3085 hook.
   - Mechanism: makes the file a selected editor, which the timer daemon needs. [inferred]
   - Prediction: may fix empty or timed-out results, but may not need focus. Unknown.
   - Intrusiveness: focus steal if done by UI. Could be done through an MCP open-file tool, if CLion exposes one. Confidence: low to medium.

3. Call `get_file_problems` with a longer timeout and check `timedOut` and `notAnalyzedReason` in the result.
   - Mechanism: `withTimeoutOrNull` plus 20 s per-file limit. [code] `AnalysisToolset.kt:114-140`
   - Prediction: tells whether the failure is timeout, staleness or "not analyzed". That decides the next step.
   - Intrusiveness: none. Confidence: high that it gives information.

4. Run one controlled A/B: same file, same edit, CLion frontmost versus background, read `notAnalyzedReason`.
   - Mechanism: isolates focus from other variables. [inferred]
   - Intrusiveness: focus steal for the frontmost leg (the developer's own choice). Confidence: high.

5. Ask the developer to review the sync settings (`isSyncOnFrameActivation`, `isBackgroundSync`, `vfs.background.refresh.on.idle`).
   - Mechanism: stale VFS/PSI on deactivation. [code] `SaveAndSyncHandlerImpl.kt:305-332`, `:559-650`
   - Prediction: could make background results match foreground. Unproven.
   - Intrusiveness: other (changes IDE settings). Needs the developer's OK. Confidence: low to medium.

6. Do not rely on AXExpanded/AXDisclosing writes or scroll actions for JBR trees.
   - Mechanism: no native setter or action. [code]
   - Prediction: inert. Intrusiveness: none. Confidence: high.

## Searches run

This log is rebuilt from my notes at the compaction point. It is complete for outcomes, not for exact query strings. The full transcript has the exact calls.

| # | Search | Result |
|---|--------|--------|
| 1 | GitHub fetch of `AnalysisToolset.kt` (mcp-server toolsets) | found, read |
| 2 | Fetch of `LintFilesAnalysisSupport.kt`, `analysis.util.kt` | found, read |
| 3 | Fetch of `SaveAndSyncHandlerImpl.kt` | found, read |
| 4 | Fetch of `DaemonCodeAnalyzerImpl.java` | found, read |
| 5 | `gh api` commits listing with `?path=` | failed first on zsh glob, fixed by quoting |
| 6 | GitHub tree listing for `DaemonListeners` | truncated, no path. Replaced by `gh search code` |
| 7 | `gh search code` for `DaemonListeners` | found, no activation listener |
| 8 | JBR `libawt_lwawt/awt/a11y/*.m`, `CAccessibility.java` | found, read |
| 9 | JBR search for `setAccessibilityDisclosed`, scroll-to-visible | empty |
| 10 | IntelliJ `AccessibilityUtils.kt`, `ScreenReader*`, `EditorComponentImpl` | found, read |
| 11 | OpenJDK `JTree.java` | found, read |
| 12 | firecrawl developer search on `get_file_problems` and focus | no focus-gate hits |
| 13 | firecrawl search for Claude Code `getDiagnostics` | found issue #3085 |
| 14 | firecrawl scrape of YouTrack IJPL-231204 | failed, all engines. Not retried |
| 15 | CLion MCP docs | found, read |
| 16 | Local config read (`options/*.xml`, `clion.vmoptions`, `nova.txt`) | read only, no focus setting |
| 17 | Cross-check grep of agent-desktop crates for AXDisclosing, AXScrollToVisible, AXEnhancedUserInterface, AXManualAccessibility | AXDisclosing and AXScrollToVisible found. The other two: not confirmed in this pass |
| 18 | Search for source of Nova backend (Radler) | empty, closed source |

## Open questions

- What does the Nova backend do on deactivation? Closed source.
- Does a background CLion window expose a full AX tree, and does the EDT run queued actions promptly there?
- What does YouTrack IJPL-231204 say? Unread.
- Does agent-desktop's AXPress step get the right row (the verification poll is 200 ms, which may be short for an async EDT)?
- Is the frontmost need real for C++ files, or only for the Java-style daemon path? An A/B is needed.
