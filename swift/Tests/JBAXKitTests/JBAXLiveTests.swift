// Live integration tests against a running JetBrains IDE, opt-in with JBAX_PID (its pid). By default nothing
// brings the IDE forward: Settings opens through its station socket. Only the debug route
// (JETBRAINS_FOREGROUND=1) opens it from the menu bar, once, briefly. No keys, no pointer. The IDE must be on
// DIRECT ("ACP agents only"); the dialog is closed with Cancel, so nothing is applied.
import AppKit
import Foundation
import Testing

@testable import JBAXKit

private let live = !(ProcessInfo.processInfo.environment["JBAX_PID"] ?? "").isEmpty
private let foreground = ProcessInfo.processInfo.environment["JETBRAINS_FOREGROUND"] == "1"

@Test func usageErrors() throws {
  #expect(try LiveIDE.jbax().code == 64)
  #expect(try LiveIDE.jbax("combo", "nope").code == 64)
  #expect(try LiveIDE.jbax("bogus", "1").code == 64)
  let missing = try LiveIDE.jbax("select", "1", "--label", LiveIDE.router)
  #expect(missing.code == 64)
  #expect(missing.json["ok"] as? Bool == false)
  #expect(try LiveIDE.jbax("press", "1", "--label", "OK", "--window", "nowhere").code == 64)
}

@Test func windowKinds() {
  #expect(windowKind(title: "a project", subrole: "AXStandardWindow") == "frame")
  // The Welcome screen, with the version and superuser suffixes the title may carry.
  #expect(windowKind(title: "Welcome to CLion", subrole: "AXStandardWindow") == "welcome")
  #expect(windowKind(title: "Welcome to CLion 2026.3 (Administrator)", subrole: "AXStandardWindow") == "welcome")
  #expect(windowKind(title: "Settings", subrole: "AXDialog") == "settings")
  #expect(windowKind(title: "", subrole: "AXUnknown") == "popup")
  #expect(windowKind(title: "Rename", subrole: "AXDialog") == "other")
  // Nothing AX could not read becomes a project window.
  #expect(windowKind(title: nil, subrole: "AXStandardWindow") == "unknown")
  #expect(windowKind(title: "a project", subrole: nil) == "unknown")
  #expect(windowKind(title: "", subrole: "AXStandardWindow") == "unknown")
}

@Test func backgroundRisks() {
  let frame: [String: Any] = ["kind": "frame", "minimized": false, "modal": false]
  func with(_ change: [String: Any]) -> [String: Any] { frame.merging(change) { $1 } }
  let unsure = "1 project windows, 1 minimized, modal or unknown, 0 others"
  #expect(backgroundRisk([frame, frame]) == nil)
  #expect(backgroundRisk([]) == "0 project windows, 0 minimized, modal or unknown, 0 others")
  #expect(backgroundRisk([with(["minimized": true])]) == unsure)
  #expect(backgroundRisk([with(["modal": true])]) == unsure)
  // A flag AX could not read is reported as null: unknown is not safe.
  #expect(backgroundRisk([with(["minimized": NSNull()])]) == unsure)
  // The projectless Welcome screen, a dialog of any size, an open popup.
  #expect(backgroundRisk([with(["kind": "welcome"])]) == "0 project windows, 0 minimized, modal or unknown, 1 others")
  let other = "1 project windows, 0 minimized, modal or unknown, 1 others"
  #expect(backgroundRisk([frame, with(["kind": "other"])]) == other)
  #expect(backgroundRisk([frame, with(["kind": "popup"])]) == other)
}

/// One ordered pass over a live IDE (one test, so nothing runs against the IDE in parallel).
@Test(.enabled(if: live, "mise run //swift:coverage <ide> sets JBAX_PID"))
func liveSession() throws {
  let ide = try LiveIDE.pid
  let pid = String(ide)
  try #require(NSWorkspace.shared.frontmostApplication?.processIdentifier != ide, "start with the IDE behind")
  // An open dialog may hold the user's unapplied edits: never cancel it on their behalf.
  try #require(try LiveIDE.settingsWindow() == nil, "close Settings first")
  // Registered before anything opens, so a failure part-way still closes the dialog; Cancel applies nothing.
  defer { if (try? LiveIDE.settingsWindow()) != nil { _ = try? LiveIDE.jbax("press", pid, "--label", "Cancel") } }

  // Nothing open.
  #expect(try LiveIDE.jbax("focus-owner", pid).json["focus_owner"] is NSNull)
  #expect(try LiveIDE.jbax("combo", pid, "--label", LiveIDE.router).code == 1)
  #expect(try LiveIDE.jbax("popup", pid).json["popups"] as? Int == 0)

  if foreground {
    // A ListPopup opens in the background and its rows read (they run only on Enter or a click); it stays open
    // until the IDE is used, so only this route, which activates the IDE, tries it.
    let gear = try LiveIDE.jbax("press", pid, "--label", "IDE and Project Settings", "--window", "frame")
    #expect(gear.json["pressed"] as? String == "<redacted>")
    Thread.sleep(forTimeInterval: 1)
    let rows = try #require(try LiveIDE.jbax("popup", pid).json["rows"] as? [[String]])
    #expect(rows.contains { $0.contains("Settings…") })
    // The one activation: open Settings (which also closes the popup) and read Java's focus owner while active.
    let session = try LiveIDE.openSettingsFromMenu()
    #expect((session.focusOwner["role"] as? String)?.isEmpty == false)
    #expect(session.focusOwner["window"] as? String == "settings")
  } else {
    _ = try LiveIDE.openSettingsFromStation("Exposed Tools")
  }

  // Background again.
  let combo = try LiveIDE.jbax("combo", pid, "--label", LiveIDE.router)
  #expect(combo.json["rows"] as? [[String]] == [[LiveIDE.direct], [LiveIDE.viaRouter]])
  #expect(combo.json["popup_child_selectable"] as? Bool == true)
  try #require(combo.json["value"] as? String == LiveIDE.direct, "start from DIRECT (ACP agents only)")
  #expect(try LiveIDE.jbax("combo", pid, "--label", "No such combo").code == 1)

  #expect(try LiveIDE.jbax("select", pid, "--label", LiveIDE.router, "--row", "No such row").code == 2)
  let unreachable = try LiveIDE.jbax("select", pid, "--label", LiveIDE.router, "--row", LiveIDE.viaRouter)
  #expect(unreachable.code == 4)
  #expect(unreachable.json["row_index"] as? Int == 1)
  let dry = try LiveIDE.jbax("select", pid, "--label", LiveIDE.router, "--row", LiveIDE.direct, "--dry-run")
  #expect(dry.json["changed"] as? Bool == false)
  #expect(dry.json["before"] as? String == LiveIDE.direct)
  // Already on row 0: nothing to commit.
  let same = try LiveIDE.jbax("select", pid, "--label", LiveIDE.router, "--row", LiveIDE.direct)
  #expect(same.code == 0)
  #expect(same.json["changed"] as? Bool == false)

  #expect(try LiveIDE.jbax("press", pid, "--label", "No such button").code == 1)
  let cancel = try LiveIDE.jbax("press", pid, "--label", "Cancel")
  #expect(cancel.json["window"] as? String == "settings")
  Thread.sleep(forTimeInterval: 1)
  #expect(try LiveIDE.settingsWindow() == nil)
  try commitOnHarmlessDropdown(pid)
  #expect(NSWorkspace.shared.frontmostApplication?.processIdentifier != ide, "the front was handed back")
}

/// A real background commit (the router dropdown is already on row 0), on a dropdown that is not: Notifications'
/// IDE-wide "Notification location:". Cancel discards it, and a second look shows the value unchanged.
private func commitOnHarmlessDropdown(_ pid: String) throws {
  let location = "Notification location:"
  _ = try LiveIDE.openSettingsFromStation("Notifications")
  let shown = try LiveIDE.jbax("combo", pid, "--label", location).json
  let first = try #require((shown["rows"] as? [[String]])?.first?.first)
  let before = try #require(shown["value"] as? String)
  try #require(before != first, "\(location) starts on a row other than its first")
  let commit = try LiveIDE.jbax("select", pid, "--label", location, "--row", first)
  #expect(commit.code == 0)
  #expect(commit.json["changed"] as? Bool == true)
  #expect(commit.json["after"] as? String == first)
  #expect(try LiveIDE.jbax("press", pid, "--label", "Cancel").code == 0)
  Thread.sleep(forTimeInterval: 1)
  // Cancel applied nothing: the dialog opens again on the old value.
  _ = try LiveIDE.openSettingsFromStation("Notifications")
  #expect(try LiveIDE.jbax("combo", pid, "--label", location).json["value"] as? String == before)
  #expect(try LiveIDE.jbax("press", pid, "--label", "Cancel").code == 0)
  Thread.sleep(forTimeInterval: 1)
  #expect(try LiveIDE.settingsWindow() == nil)
}
