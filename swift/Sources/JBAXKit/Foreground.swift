// The jbax commands whose output depends on the IDE being in front, so only the debug route
// (JETBRAINS_FOREGROUND=1, mise --foreground) reaches all of them: Java has a focus owner only while the IDE is
// active, and the tests open a popup only on that route (one opened in the background stays until the IDE is next
// used). llvm-cov can leave out whole files but not lines, so this file is the one the coverage gate skips
// (swift/mise.toml); nothing else is excused.
import ApplicationServices
import Foundation

/// Rows of the IDE's open popup windows (ListPopups, dropdown lists): readable in the background,
/// but a row only runs on Enter or a real click.
func popup(_ args: Args) -> [String: Any] {
  let popups = args.accessibility.windows.filter { Scope(window: $0) == .popup }
  let rows = popups.flatMap {
    Accessibility.descendants($0, maxDepth: 20).filter { Accessibility.role($0) == "AXRow" }
  }
  let texts = rows.map { Accessibility.rowText($0) }
  return ["popups": popups.count, "rows": texts]
}

/// JBR reports Java's focus owner here. While the IDE is inactive it is an empty element: keys go nowhere.
func focusOwner(_ args: Args) -> [String: Any] {
  guard let element = Accessibility.element(args.accessibility.app, "AXFocusedUIElement"),
    !Accessibility.role(element).isEmpty
  else {
    return ["focus_owner": NSNull()]
  }
  let window = Accessibility.element(element, "AXWindow")
  let scope = window.flatMap { Scope(window: $0) } ?? .frame
  return [
    "focus_owner": [
      "role": Accessibility.role(element), "label": scope.shown(Accessibility.label(element)), "window": scope.rawValue,
    ]
  ]
}
