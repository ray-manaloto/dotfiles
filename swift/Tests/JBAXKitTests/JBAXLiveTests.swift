// Live integration tests against the running JetBrains IDE, opt-in with JBAX_LIVE=1 because they need
// the IDE open and bring it forward once, for a few seconds: AppKit drops a menu press for an inactive
// app, and only keys reach a dropdown's second row. Everything else runs with the IDE in the background.
// Settings are left as found: the dialog is closed with Cancel, so nothing is applied.
import AppKit
import Foundation
import Testing

private let live = ProcessInfo.processInfo.environment["JBAX_LIVE"] == "1"

@Test func usageErrors() throws {
  #expect(try LiveIDE.jbax().code == 64)
  #expect(try LiveIDE.jbax("combo", "nope").code == 64)
  #expect(try LiveIDE.jbax("bogus", "1").code == 64)
  let missing = try LiveIDE.jbax("select", "1", "--label", LiveIDE.router)
  #expect(missing.code == 64)
  #expect(missing.json["ok"] as? Bool == false)
  #expect(try LiveIDE.jbax("press", "1", "--label", "OK", "--window", "nowhere").code == 64)
}

/// One pass over a live IDE, in the order that needs a single activation.
@Test(.enabled(if: live, "set JBAX_LIVE=1 with a JetBrains IDE running"))
func liveSession() throws {
  let ide = try LiveIDE.pid
  let pid = String(ide)
  try #require(NSWorkspace.shared.frontmostApplication?.processIdentifier != ide, "start with the IDE behind")
  // An open dialog may hold the user's unapplied edits: never cancel it on their behalf.
  try #require(try LiveIDE.settingsWindow() == nil, "close Settings first")
  // Registered before anything opens, so a failure part-way still closes the dialog; Cancel applies nothing.
  defer { if (try? LiveIDE.settingsWindow()) != nil { _ = try? LiveIDE.jbax("press", pid, "--label", "Cancel") } }

  // Background, nothing open.
  #expect(try LiveIDE.jbax("focus-owner", pid).json["focus_owner"] is NSNull)
  let closed = try LiveIDE.jbax("combo", pid, "--label", LiveIDE.router)
  #expect(closed.code == 1)
  #expect(try LiveIDE.jbax("popup", pid).json["popups"] as? Int == 0)

  // Background: a ListPopup opens and its rows read, but they only run on Enter or a click.
  let gear = try LiveIDE.jbax("press", pid, "--label", "IDE and Project Settings", "--window", "frame")
  #expect(gear.json["pressed"] as? String == "<redacted>")
  Thread.sleep(forTimeInterval: 1)
  let rows = try #require(try LiveIDE.jbax("popup", pid).json["rows"] as? [[String]])
  #expect(rows.contains { $0.contains("Settings…") })

  // The one activation: open Settings (which also closes the popup), put "All agents" into the dialog
  // with keys, and read Java's focus owner while the IDE is active.
  let session = try LiveIDE.openSettingsForTest()
  #expect((session.focusOwner["role"] as? String)?.isEmpty == false)
  #expect(session.focusOwner["window"] as? String == "settings")

  // Background again.
  let combo = try LiveIDE.jbax("combo", pid, "--label", LiveIDE.router)
  #expect(combo.json["rows"] as? [[String]] == [[LiveIDE.direct], [LiveIDE.viaRouter]])
  #expect(combo.json["popup_child_selectable"] as? Bool == true)
  try #require(combo.json["value"] as? String == LiveIDE.viaRouter, "the dialog shows All agents")
  #expect(try LiveIDE.jbax("combo", pid, "--label", "No such combo").code == 1)

  #expect(try LiveIDE.jbax("select", pid, "--label", LiveIDE.router, "--row", "No such row").code == 2)
  let unreachable = try LiveIDE.jbax("select", pid, "--label", LiveIDE.router, "--row", LiveIDE.viaRouter)
  #expect(unreachable.code == 4)
  #expect(unreachable.json["row_index"] as? Int == 1)
  let dry = try LiveIDE.jbax("select", pid, "--label", LiveIDE.router, "--row", LiveIDE.direct, "--dry-run")
  #expect(dry.json["changed"] as? Bool == false)
  #expect(dry.json["before"] as? String == LiveIDE.viaRouter)

  let commit = try LiveIDE.jbax("select", pid, "--label", LiveIDE.router, "--row", LiveIDE.direct)
  #expect(commit.code == 0)
  #expect(commit.json["changed"] as? Bool == true)
  #expect(commit.json["after"] as? String == LiveIDE.direct)

  #expect(try LiveIDE.jbax("press", pid, "--label", "No such button").code == 1)
  let cancel = try LiveIDE.jbax("press", pid, "--label", "Cancel")
  #expect(cancel.json["window"] as? String == "settings")
  Thread.sleep(forTimeInterval: 1)
  #expect(try LiveIDE.settingsWindow() == nil)
  #expect(NSWorkspace.shared.frontmostApplication?.processIdentifier != ide, "the front was handed back")
}
