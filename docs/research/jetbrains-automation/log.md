# Directory Update Log

## 2026-11-05
* **Creation**: from the spike session's notes and local recordings (untracked), and the
  JBR / intellij-community source answers from dotfiles-c6. No dotfiles repo files were written.
* **Results**: DIRECT set three ways, each after the owner reset it to "All agents":
  * headed: a physical click on the dropdown, then Up/Up/Return;
  * foreground headless: Tab, then Space/Down/Return;
  * background: AXSelected on the dropdown's child 0, then AXPress OK.
  * Verified each time by MCP `tools/list` (1 tool → 88) and by `mcpToolFilter.xml` being removed.
* **Added**: rea installed and patched (launch-time fallback, same-size window disambiguation, Swing
  labels). Background Settings navigation found: rea key-entry into the Settings search field.
* **Added**: `jbctl` first cut. It runs `router-direct` end to end, with only the Settings opening
  bringing CLion forward.
* **Rejected**:
  * background keys (JBR rejects non-mouse focus requests while the app is inactive);
  * AXPress on popup rows (only selects);
  * tree-row AXPress for navigation (inert in the background);
  * `jetbrains://…/settings` as a background opener (always activates);
  * Frida on CLion (hardened runtime, SIP on).
* **Failed**:
  * menu-bar "Settings…" AXPress while CLion is inactive (AppKit drops it);
  * a CGEventPostToPid click on a popup row (ignored);
  * the first `--headed click @ref` on the dropdown (target point not proven; `mouse-click --xy`
    worked).
* **Added**: `--ide <Toolbox shell-script name>` for every IDE command and `jbctl resolve`. Toolbox channel
  file, then `product-info.json`, then the station-socket pid, then the one loopback listener that answers MCP
  `initialize`; it refuses when anything is ambiguous. This replaces "the first `com.jetbrains.*` app",
  which had only matched CLion by list order with PyCharm and WebStorm running. See [[tools]].
* **Live runs** (owner's go, headless):
  * jbctl 9/9 at 100%. They found two bugs, both fixed: a second "Search" field on Exposed Tools, and a
    banner's Dismiss link in the breadcrumb.
  * jbax 2/2, but `select`'s commit path is not covered: headless, the dropdown cannot be put on "All
    agents" (row 1). The JBR source has only AXSelected, which highlights a list row or commits row 0, and
    the Swing `BasicComboPopup` commits only on a mouse release or Enter.
* **Changed**: `resolve` no longer probes every listener of the pid. It takes the port from the plugin's own
  order: forced port, then `mcpServer.xml`, then the platform-prefix default. It then checks that the pid
  listens there and answers `initialize`. Measured: CLion 64362 (default), PyCharm 64463 (saved, because its
  default 64462 was CLion's private port), WebStorm 64542 (default).
* **Found**: Settings opens in the background through the IDE's station socket (`POST /protocolHandler`,
  `jetbrains://idea/settings?name=...`); one live run kept the front app. See [[settings-open-and-navigation]].
  Reviewed with a Codex peer, and we agreed:
  * the station route is the default;
  * the menu route is kept only behind `JETBRAINS_FOREGROUND=1`;
  * `name=` and not `page_id=`, because `page_id=` can block on a modal dialog;
  * `check_background` fails closed on states that may activate the IDE.
* **Fixed** (peer review):
  * the JVM options now follow the launcher (`<app>.vmoptions` beside the bundle, else
    `<config>/<launcher>.vmoptions`, then `product-info` arguments; lines trimmed);
  * a `-Didea.config.path` option moves `mcpServer.xml`, read as PathManager does;
  * the Swift live tests are one ordered test, so the two can no longer run in parallel against the IDE.
* **Changed** (with a Codex peer and the owner): no code is marked to reach a coverage gate, except the debug route
  that brings the IDE forward.
  * jbctl marks only that route, with `# pragma: foreground` in `ide.py`, and `mise run //jbctl:markers` (part of
    `//jbctl:check`) fails on any other pragma. The old `no cover` guards are gone.
  * jbax keeps its foreground-only commands (`focus-owner`, `popup`) in `Foreground.swift`. That is the one file
    the gate skips, because llvm-cov can leave out files but not lines (llvm-project#33625). No line is marked.
  * `jbctl coverage-gate` requires every other `Sources/JBAXKit/*.swift` file to be in the export. A missing or
    empty file fails.
  * Everything else that a run cannot reach stays visible as uncovered, under measured #502 MVP floors: jbctl 98.08%
    (three guards, among them a jbax crash, and the move to the page asked for), jbax 87% of lines and regions (AX and JSON failure fallbacks, plus states no working IDE
    produces).
  * The owner rejected a stand-in `agent-desktop` for the debug route, so the real route is proven only by
    `--foreground` runs.
