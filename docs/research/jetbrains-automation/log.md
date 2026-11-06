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
