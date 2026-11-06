// Live-IDE fixture: the JetBrains IDE under test. Settings opens through its station socket; the debug route
// (JETBRAINS_FOREGROUND=1) opens it from the menu bar through agent-desktop and hands the front back.
import AppKit
import ApplicationServices
import Foundation
import Testing

@testable import JBAXKit

enum LiveIDE {
  static let router = "Enable router-only mode for:"
  static let direct = "ACP agents only"
  static let viaRouter = "All agents"

  /// The IDE under test: `mise run //swift:coverage <ide>` resolves the Toolbox install with `jbctl resolve`
  /// and passes its pid, so the test never guesses among several running JetBrains IDEs.
  static var pid: pid_t {
    get throws {
      try #require(ProcessInfo.processInfo.environment["JBAX_PID"].flatMap { pid_t($0) }, "JBAX_PID")
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

  /// Runs agent-desktop steps as one batch, so a focus-window and the click after it cannot be split.
  static func batch(_ steps: [[String: Any]]) throws {
    let json = try #require(String(bytes: try JSONSerialization.data(withJSONObject: steps), encoding: .utf8))
    _ = try agentDesktop("batch", json, "--stop-on-error")
  }

  static func frameWindow() throws -> String {
    let pid = try pid
    let frame = try windows().first {
      let bounds = $0["bounds"] as? [String: Double] ?? [:]
      return $0["pid"] as? Int == Int(pid) && bounds["width", default: 0] > 1000 && bounds["height", default: 0] > 300
    }
    return try #require(frame?["id"] as? String)
  }

  /// Opens Settings on `page` through the IDE's station socket (as `jbctl settings-open` does): the IDE stays
  /// in the background. Like jbctl, it first requires the one state measured to stay there: project windows only,
  /// none minimized or modal (`jbax windows`).
  static func openSettingsFromStation(_ page: String) throws -> String {
    let pid = try pid
    let risk = try jbax("windows", String(pid)).json["unsafe"]
    try #require(risk is NSNull, "only project windows open, none minimized or modal")
    // The IDE's per-user temporary folder (confstr), not this process's TMPDIR, which a harness may change.
    var buffer = [CChar](repeating: 0, count: Int(PATH_MAX))
    confstr(_CS_DARWIN_USER_TEMP_DIR, &buffer, buffer.count)
    let folder = try #require(String(bytes: buffer.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }, encoding: .utf8))
    let name = try #require(page.addingPercentEncoding(withAllowedCharacters: .alphanumerics))
    let curl = Process()
    curl.executableURL = URL(fileURLWithPath: "/usr/bin/curl")
    curl.arguments = [
      "-sf", "--max-time", "10", "--unix-socket", folder + "jb.station.ij.\(pid).sock", "-X", "POST",
      "-H", "Content-Type: application/json", "-d", "{\"uri\": \"jetbrains://idea/settings?name=\(name)\"}",
      "http://localhost/protocolHandler",
    ]
    let output = Pipe()
    curl.standardOutput = output
    try curl.run()
    let data = output.fileHandleForReading.readDataToEndOfFile()
    curl.waitUntilExit()
    // The IDE reports a refused command as exit code 0 with a message.
    let reply = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
    let opened = curl.terminationStatus == 0 && reply["exitCode"] as? Int == 0 && reply["message"] == nil
    try #require(opened, "the station opened Settings")
    return try waitForSettings()
  }

  static func waitForSettings() throws -> String {
    var settings: String?
    for _ in 0..<40 where settings == nil {
      Thread.sleep(forTimeInterval: 0.1)
      settings = try settingsWindow()
    }
    return try #require(settings, "Settings opened")
  }

  /// The debug route (JETBRAINS_FOREGROUND=1), then the front goes back to whatever had it: open Settings from
  /// the menu bar (AppKit drops a menu press for an inactive app) and read Java's focus owner while the IDE is
  /// active. The router page is then reached in the background.
  static func openSettingsFromMenu() throws -> (settings: String, focusOwner: [String: Any]) {
    let previous = try focusedWindow()
    let frame = try frameWindow()
    let found = try agentDesktop("find", "--surface", "menubar", "--window-id", frame, "--name", "Settings…", "--exact")
    let item = try #require(((found["data"] as? [String: Any])?["matches"] as? [[String: Any]])?.first?["ref_id"])
    try batch([
      ["command": "focus-window", "args": ["window_id": frame]], ["command": "click", "args": ["ref_id": item]],
    ])
    let window = try waitForSettings()
    let owner = try jbax("focus-owner", String(try pid)).json["focus_owner"] as? [String: Any]
    if let previous { _ = try agentDesktop("focus-window", "--window-id", previous) }
    try goto("Exposed Tools")
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
