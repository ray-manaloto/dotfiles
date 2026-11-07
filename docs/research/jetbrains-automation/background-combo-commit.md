---
okf_version: "0.2"
type: "report"
title: "Background dropdown commit via AXSelected"
description: "Committing a Swing JComboBox with no focus and no activation: AXSelected on the popup child calls setSelectedIndex(0). Row-0 only, guarded."
resource: "https://github.com/JetBrains/JetBrainsRuntime"
version: "jbr-release-25.0.4.1b635.79"
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [jbr, swing, jcombobox, accessibility, background]
---

# Background dropdown commit

## Mechanism

- Setting AXSelected=true on an element runs `CAccessibility.requestSelection`
  (CAccessibility.java:565-583). It takes the element's index in its **Java accessible parent**:
  - if that parent is a JList, it calls `JList.setSelectedIndex`, which only highlights;
  - otherwise it calls `parent.getAccessibleSelection().addAccessibleSelection(i)`.
- The combo's AX child 0 is its popup. `BasicComboBoxUI.getAccessibleChild` case 0 parents it to the
  combo, and `Component.getAccessibleIndexInParent` returns 0.
- `AccessibleJComboBox.addAccessibleSelection(0)` runs `clearAccessibleSelection()` and then
  `JComboBox.this.setSelectedIndex(0)` (JComboBox.java:2045-2049). That is a **real commit**
  (ActionEvent + ItemEvent) and needs no focus.

AX path from the combo: child 0 `AXPopUpButton` (the popup) → `AXMenuItem` → `AXList` → 2 rows.

## Live proof (16:05)

- Precondition: the owner set "All agents" + Apply. tools/list = 1.
- the spike probe `selpoke` (AXSelected on child 0; now `jbax select`): a screenshot showed "ACP agents only" (Swing, not only AX).
  tools/list was still 1, because nothing was applied yet.
- Apply stayed disabled: its state is not refreshed while CLion is inactive. AXPress **OK** closed
  Settings, tools/list = 88, and `mcpToolFilter.xml` was absent.
- Herdr stayed the focused app at every check.

## Limits and guard

- **It only ever commits row 0.** If an IDE update reorders the options or inserts one above, the raw
  call would silently commit the wrong value.
- `jbax select` is the guarded form (it replaced the spike's `set-direct-bg`):
  1. it reads row labels from the popup's AXList (readable while the popup is hidden) and refuses
     (exit 2) unless row 0 is exactly "ACP agents only";
  2. after the commit it re-reads the combo value (exit 3 on a mismatch).
- Dry-run against a live dialog: `rows: 2 [["ACP agents only"], ["All agents"]]`, exit 0.
- After every run, the jbctl DIRECT check must report DIRECT (tools/list > 1).
- Dead ends:
  - AXSelected on a list row, and AXSelectedChildren: both end in `JList.setSelectedIndex`;
  - `accessibilitySelectedChildren` (ComboBoxAccessibility.m) only reads the value.
