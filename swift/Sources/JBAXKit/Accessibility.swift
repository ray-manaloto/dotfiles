// Thin reads over the macOS accessibility API for one JBR/Swing process.
import ApplicationServices

struct Accessibility {
  let app: AXUIElement

  init(pid: pid_t) {
    app = AXUIElementCreateApplication(pid)
    AXUIElementSetMessagingTimeout(app, 1.0)
  }

  var windows: [AXUIElement] { (Self.attr(app, "AXWindows") as? [AXUIElement]) ?? [] }

  static func attr(_ element: AXUIElement, _ name: String) -> AnyObject? {
    var value: AnyObject?
    return AXUIElementCopyAttributeValue(element, name as CFString, &value) == .success ? value : nil
  }

  static func string(_ element: AXUIElement, _ name: String) -> String? { attr(element, name) as? String }

  /// An attribute that holds one element (AXWindow, AXFocusedUIElement).
  static func element(_ element: AXUIElement, _ name: String) -> AXUIElement? {
    guard let value = attr(element, name), CFGetTypeID(value) == AXUIElementGetTypeID() else {
      return nil
    }
    return unsafeDowncast(value, to: AXUIElement.self)
  }

  static func children(_ element: AXUIElement) -> [AXUIElement] {
    (attr(element, "AXChildren") as? [AXUIElement]) ?? []
  }

  static func role(_ element: AXUIElement) -> String { string(element, "AXRole") ?? "" }

  /// JBR puts a Swing component's accessible name in AXDescription; native controls use AXTitle.
  static func label(_ element: AXUIElement) -> String {
    ["AXTitle", "AXDescription"].lazy.compactMap { string(element, $0) }.first { !$0.isEmpty } ?? ""
  }

  static func actions(_ element: AXUIElement) -> [String] {
    var names: CFArray?
    AXUIElementCopyActionNames(element, &names)
    return (names as? [String]) ?? []
  }

  static func settable(_ element: AXUIElement, _ name: String) -> Bool {
    var settable = DarwinBoolean(false)
    AXUIElementIsAttributeSettable(element, name as CFString, &settable)
    return settable.boolValue
  }

  /// A list row's visible text: every title, description and string value in its subtree, deduplicated.
  static func rowText(_ element: AXUIElement) -> [String] { Array(Set(texts(element))).sorted() }

  private static func texts(_ element: AXUIElement, depth: Int = 0) -> [String] {
    guard depth <= 4 else { return [] }
    let own = ["AXTitle", "AXDescription", "AXValue"].compactMap { string(element, $0) }.filter { !$0.isEmpty }
    return own + children(element).flatMap { texts($0, depth: depth + 1) }
  }

  /// Depth-first elements of a subtree, root first, read lazily so `first(where:)` stops at its match.
  static func descendants(_ root: AXUIElement, maxDepth: Int = 45) -> some Sequence<AXUIElement> {
    sequence(state: [(element: root, depth: 0)]) { pending in
      guard let next = pending.popLast() else { return nil }
      if next.depth < maxDepth { pending += children(next.element).reversed().map { ($0, next.depth + 1) } }
      return next.element
    }
  }
}
