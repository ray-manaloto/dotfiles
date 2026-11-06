// jbax: background accessibility for JetBrains (JBR/Swing) IDEs. Nothing here activates the IDE.
import ApplicationServices
import Foundation

/// One command's outcome: the process exit code and the JSON object it prints.
public struct Outcome: Sendable {
  public let code: Int32
  public let json: String
}

/// Exit codes; jbctl puts the code in its failure text.
enum Exit: Int32 {
  case success = 0
  case notFound = 1
  case refused = 2
  case notChanged = 3
  case backgroundUnreachable = 4
  case axError = 5
  case usage = 64
}

struct Failure: Error {
  let exit: Exit
  let message: String
  var info: [String: any Sendable] = [:]
}

/// Window kinds. Text is reported only from Settings and untitled popups; other windows hold project text.
enum Scope: String {
  case settings, popup, frame

  init?(window: AXUIElement) {
    let title = Accessibility.string(window, "AXTitle") ?? ""
    let standard = Accessibility.string(window, "AXSubrole") == "AXStandardWindow"
    switch (title, standard) {
    case ("Settings", _): self = .settings
    case ("", false): self = .popup
    case (_, true): self = .frame
    default: return nil
    }
  }

  func shown(_ text: String) -> String { self == .frame ? "<redacted>" : text }
}

private let usageText =
  "usage: jbax <combo|select|press|popup|focus-owner> <pid> [--label L] [--row R] [--window settings|frame|popup] [--dry-run]"

/// Runs one command line (without the program name).
public func run(_ args: [String]) -> Outcome {
  do throws(Failure) {
    return finish(.success, try dispatch(args))
  } catch {
    var info: [String: Any] = error.info
    info["error"] = error.message
    return finish(error.exit, info)
  }
}

private func finish(_ exit: Exit, _ info: [String: Any]) -> Outcome {
  var info = info
  info["ok"] = exit == .success
  if exit != .success { info["exit"] = Int(exit.rawValue) }
  // Every value is a string, number, bool, array or NSNull, so serialization cannot fail.
  let data = (try? JSONSerialization.data(withJSONObject: info, options: [.sortedKeys])) ?? Data()
  return Outcome(code: exit.rawValue, json: String(bytes: data, encoding: .utf8) ?? "{}")
}

private struct Args {
  let command: String
  let accessibility: Accessibility
  let options: [String]

  init(_ argv: [String]) throws(Failure) {
    guard argv.count >= 2, let pid = pid_t(argv[1]), pid > 0 else { throw Failure(exit: .usage, message: usageText) }
    command = argv[0]
    accessibility = Accessibility(pid: pid)
    options = Array(argv.dropFirst(2))
  }

  func value(_ name: String) throws(Failure) -> String {
    guard let index = options.firstIndex(of: name), index + 1 < options.count else {
      throw Failure(exit: .usage, message: "\(command) needs \(name)")
    }
    return options[index + 1]
  }

  func flag(_ name: String) -> Bool { options.contains(name) }

  func window() throws(Failure) -> (AXUIElement, Scope) {
    let name = flag("--window") ? try value("--window") : "settings"
    guard let scope = Scope(rawValue: name) else { throw Failure(exit: .usage, message: "bad --window \(name)") }
    guard let window = accessibility.windows.first(where: { Scope(window: $0) == scope }) else {
      throw Failure(exit: .notFound, message: "no \(name) window open")
    }
    return (window, scope)
  }
}

private func dispatch(_ argv: [String]) throws(Failure) -> [String: Any] {
  let args = try Args(argv)
  switch args.command {
  case "combo": return try combo(args)
  case "select": return try select(args)
  case "press": return try press(args)
  case "popup": return popup(args)
  case "focus-owner": return focusOwner(args)
  default: throw Failure(exit: .usage, message: usageText)
  }
}

// MARK: combo boxes

/// A JComboBox as JBR exposes it: AXPopUpButton → child 0 (the popup) → AXMenuItem → AXList → rows.
private struct Combo {
  let element: AXUIElement
  let popup: AXUIElement
  let rows: [[String]]

  init(_ prefix: String, in window: AXUIElement) throws(Failure) {
    let found = Accessibility.descendants(window).first {
      Accessibility.role($0) == "AXPopUpButton" && Accessibility.label($0).hasPrefix(prefix)
    }
    guard let element = found, let popup = Accessibility.children(element).first else {
      throw Failure(exit: .notFound, message: "no combo labelled \(prefix)")
    }
    let list = Accessibility.children(popup).flatMap(Accessibility.children).first {
      Accessibility.role($0) == "AXList"
    }
    self.element = element
    self.popup = popup
    rows = list.map { Accessibility.children($0).map { Accessibility.rowText($0) } } ?? []
  }

  var value: String { Accessibility.string(element, "AXValue") ?? "" }
}

private func combo(_ args: Args) throws(Failure) -> [String: Any] {
  let prefix = try args.value("--label")
  let (window, scope) = try args.window()
  let dropdown = try Combo(prefix, in: window)
  return [
    "label": scope.shown(Accessibility.label(dropdown.element)),
    "value": scope.shown(dropdown.value),
    "rows": dropdown.rows.map { $0.map(scope.shown) },
    "popup_child_selectable": Accessibility.settable(dropdown.popup, "AXSelected"),
  ]
}

/// AXSelected on the popup child runs AccessibleJComboBox.addAccessibleSelection(0), which is
/// JComboBox.setSelectedIndex(0): a real commit with no focus. Only row 0 is reachable, so the row's
/// text is the guard, and the value is read back afterwards.
private func select(_ args: Args) throws(Failure) -> [String: Any] {
  let prefix = try args.value("--label")
  let want = try args.value("--row")
  let (window, scope) = try args.window()
  let dropdown = try Combo(prefix, in: window)
  var info: [String: any Sendable] = [
    "rows": dropdown.rows.map { $0.map(scope.shown) }, "before": scope.shown(dropdown.value),
  ]
  guard let index = dropdown.rows.firstIndex(where: { $0.contains(want) }) else {
    throw Failure(exit: .refused, message: "no row reads \(want)", info: info)
  }
  info["row_index"] = index
  guard index == 0 else {
    throw Failure(exit: .backgroundUnreachable, message: "only row 0 can be committed in the background", info: info)
  }
  guard dropdown.value != want, !args.flag("--dry-run") else {
    info["changed"] = false
    return info
  }
  AXUIElementSetAttributeValue(dropdown.popup, "AXSelected" as CFString, kCFBooleanTrue)
  Thread.sleep(forTimeInterval: 0.5)
  let after = Accessibility.string(dropdown.element, "AXValue") ?? ""
  info["after"] = scope.shown(after)
  guard after == want else { throw Failure(exit: .notChanged, message: "value did not become \(want)", info: info) }
  info["changed"] = true
  return info
}

// MARK: buttons, popups, focus

private func press(_ args: Args) throws(Failure) -> [String: Any] {
  let want = try args.value("--label")
  let (window, scope) = try args.window()
  let hits = Accessibility.descendants(window).filter {
    Accessibility.role($0) == "AXButton" && Accessibility.label($0) == want
      && Accessibility.actions($0).contains("AXPress")
  }
  guard hits.count == 1 else {
    throw Failure(
      exit: hits.isEmpty ? .notFound : .refused, message: "want one button \(want)", info: ["found": hits.count])
  }
  let result = AXUIElementPerformAction(hits[0], kAXPressAction as CFString)
  guard result == .success else {
    throw Failure(exit: .axError, message: "AXPress on \(want) failed", info: ["ax_error": Int(result.rawValue)])
  }
  return ["pressed": scope.shown(want), "window": scope.rawValue]
}

/// Rows of the IDE's open popup windows (ListPopups, dropdown lists): readable in the background,
/// but a row only runs on Enter or a real click.
private func popup(_ args: Args) -> [String: Any] {
  let popups = args.accessibility.windows.filter { Scope(window: $0) == .popup }
  let rows = popups.flatMap { Accessibility.descendants($0, maxDepth: 20).filter { Accessibility.role($0) == "AXRow" } }
  return ["popups": popups.count, "rows": rows.map { Accessibility.rowText($0) }]
}

/// JBR reports Java's focus owner here. While the IDE is inactive it is an empty element: keys go nowhere.
private func focusOwner(_ args: Args) -> [String: Any] {
  guard let element = Accessibility.element(args.accessibility.app, "AXFocusedUIElement"),
    !Accessibility.role(element).isEmpty
  else {
    return ["focus_owner": NSNull()]
  }
  let scope = Accessibility.element(element, "AXWindow").flatMap { Scope(window: $0) } ?? .frame
  return [
    "focus_owner": [
      "role": Accessibility.role(element), "label": scope.shown(Accessibility.label(element)), "window": scope.rawValue,
    ]
  ]
}
