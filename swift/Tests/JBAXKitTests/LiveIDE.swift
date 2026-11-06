// Live-IDE fixture: the running JetBrains IDE, driven through agent-desktop where activation is
// unavoidable (opening Settings, keys), and handed back to the previous front window afterwards.
import AppKit
import ApplicationServices
import Foundation
import Testing

@testable import JBAXKit

enum LiveIDE {
  static let router = "Enable router-only mode for:"
  static let direct = "ACP agents only"
  static let viaRouter = "All agents"

  /// The GUI JetBrains IDE (helper processes such as `clion stdioMcpServer` have no bundle).
  static var pid: pid_t {
    get throws {
      let app = NSWorkspace.shared.runningApplications.first {
        ($0.bundleIdentifier ?? "").hasPrefix("com.jetbrains.") && $0.activationPolicy == .regular
      }
      return try #require(app, "a running JetBrains IDE").processIdentifier
    }
  }

  /// Runs one jbax command in-process and decodes its JSON.
  static func jbax(_ args: String...) throws -> (code: Int32, json: [String: Any]) {
    let out = run(args)
    let json = try JSONSerialization.jsonObject(with: Data(out.json.utf8)) as? [String: Any]
    return (out.code, try #require(json))
  }

  static func agentDesktop(_ args: String...) throws -> [String: Any] {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
    process.arguments = ["agent-desktop"] + args
    let pipe = Pipe()
    process.standardOutput = pipe
    try process.run()
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    return try #require(try JSONSerialization.jsonObject(with: data) as? [String: Any])
  }

  static func windows() throws -> [[String: Any]] {
    try #require(try agentDesktop("list-windows")["data"] as? [[String: Any]])
  }

  static func focusedWindow() throws -> String? {
    try windows().first { $0["is_focused"] as? Bool == true }?["id"] as? String
  }

  static func settingsWindow() throws -> String? {
    let pid = try pid
    return try windows().first { $0["pid"] as? Int == Int(pid) && $0["title"] as? String == "Settings" }?["id"]
      as? String
  }

  /// Runs agent-desktop steps as one batch, so a focus-window and the keys after it cannot be split.
  static func batch(_ steps: [[String: Any]]) throws {
    let json = try #require(String(bytes: try JSONSerialization.data(withJSONObject: steps), encoding: .utf8))
    _ = try agentDesktop("batch", json, "--stop-on-error")
  }

  static func frameWindow() throws -> String {
    let pid = try pid
    let frame = try windows().first {
      $0["pid"] as? Int == Int(pid) && (($0["bounds"] as? [String: Double])?["width"] ?? 0) > 1000
    }
    return try #require(frame?["id"] as? String)
  }

  /// The test's single activation, then the front goes back to whatever had it:
  /// open Settings (AppKit drops a menu press for an inactive app), go to the router page, put
  /// "All agents" into the dialog with keys (only keys reach row 1; nothing is applied), and read
  /// Java's focus owner while the IDE is active.
  static func openSettingsForTest() throws -> (settings: String, focusOwner: [String: Any]) {
    let previous = try focusedWindow()
    let frame = try frameWindow()
    let found = try agentDesktop("find", "--surface", "menubar", "--window-id", frame, "--name", "Settings…", "--exact")
    let item = try #require(((found["data"] as? [String: Any])?["matches"] as? [[String: Any]])?.first?["ref_id"])
    try batch([
      ["command": "focus-window", "args": ["window_id": frame]], ["command": "click", "args": ["ref_id": item]],
    ])
    var settings: String?
    for _ in 0..<40 where settings == nil {
      Thread.sleep(forTimeInterval: 0.1)
      settings = try settingsWindow()
    }
    let window = try #require(settings, "Settings opened")
    try goto("Exposed Tools")
    try batch([
      ["command": "focus-window", "args": ["window_id": window]],
      ["command": "press", "args": ["combo": "tab", "window_id": window]],
      ["command": "press", "args": ["combo": "space", "window_id": window]],
      ["command": "wait", "args": ["ms": 300]],
      ["command": "press", "args": ["combo": "down"]],
      ["command": "wait", "args": ["ms": 200]],
      ["command": "press", "args": ["combo": "return"]],
    ])
    let owner = try jbax("focus-owner", String(try pid)).json["focus_owner"] as? [String: Any]
    if let previous { _ = try agentDesktop("focus-window", "--window-id", previous) }
    return (window, try #require(owner))
  }

  /// Settings opens on the last page used; this goes to `page` by typing its name into the Settings
  /// search field and clearing it, which also works in the background (tree rows don't).
  static func goto(_ page: String) throws {
    let settings = try #require(
      Accessibility(pid: try pid).windows.first { Accessibility.string($0, "AXTitle") == "Settings" })
    let search = try #require(
      Accessibility.children(settings).first {
        Accessibility.role($0) == "AXTextField" && Accessibility.string($0, "AXDescription") == "Search"
      })
    for text in [page, ""] {
      AXUIElementSetAttributeValue(search, "AXValue" as CFString, text as CFString)
      Thread.sleep(forTimeInterval: 1.5)
    }
  }
}
