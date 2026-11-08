"""One pass over a running JetBrains IDE, opt-in: JBCTL_IDE names it by its Toolbox shell script (e.g. clion)."""

# test_live_background never brings the IDE forward: Settings opens through the station socket. Only
# test_live_foreground does, once, through the menu bar, and only with JETBRAINS_FOREGROUND=1. Settings end as
# they started: router-direct only commits DIRECT, which the run requires up front.

import os
import shutil
import time
from pathlib import Path
from typing import Any

import pytest

from jbctl import ide, lifecycle, mcp

from .conftest import run

IDE = os.environ.get("JBCTL_IDE", "")
pytestmark = pytest.mark.skipif(not IDE, reason="set JBCTL_IDE to a running IDE's Toolbox script name")


def jb(capsys: pytest.CaptureFixture[str], command: str, *argv: str) -> tuple[int, list[dict[str, Any]], str]:
    """A jbctl command against the IDE under test."""
    return run(capsys, command, "--ide", IDE, *argv)


@pytest.fixture
def live(capsys: pytest.CaptureFixture[str]) -> int:
    """The IDE under test's pid, once it is known to start from DIRECT with Settings closed."""
    # Without jbax every Settings step, the Cancel included, fails after Settings is open.
    assert shutil.which(os.environ.get("JBAX", "jbax")), "install jbax first (mise run //swift:install)"
    code, [resolved], _ = jb(capsys, "resolve")
    assert code == 0
    assert len(mcp.tool_names(resolved["ide"]["mcp_url"])) > 1, "start from DIRECT, so the run changes nothing"
    # An open dialog may hold the user's unapplied edits: never cancel it on their behalf.
    assert ide.settings_window(resolved["ide"]["pid"]) is None, "close Settings first"
    return resolved["ide"]["pid"]


def test_live_background(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, via_router: str, live: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Everything, Settings included, through the station socket and AX: no step brings the IDE forward."""
    monkeypatch.delenv(ide.FOREGROUND, raising=False)
    frame = ide.frames(live, ide.windows())[0]["id"]
    code, [mapped], _ = jb(capsys, "map", "--window", frame.removeprefix("w-"), "--out", str(tmp_path / "frame.json"))
    assert (code, mapped["nodes"] > 100) == (0, True)
    try:
        session(capsys, tmp_path, via_router, live)
    finally:
        # A failure part-way must not leave a changed dialog open; Cancel applies nothing. The test opened every
        # dialog there is (the fixture started with none), so it closes it with jbax, whoever opened it.
        if ide.settings_window(live):
            ide.jbax("press", str(live), "--label", "Cancel")
    assert jb(capsys, "check-direct")[0] == 0


@pytest.mark.skipif(os.environ.get(ide.FOREGROUND) != "1", reason=f"brings the IDE forward: set {ide.FOREGROUND}=1")
def test_live_foreground(capsys: pytest.CaptureFixture[str], live: int) -> None:
    """The debug route: Settings from the menu bar, which brings the IDE forward once, then the front goes back."""
    try:
        code, [opened], _ = jb(capsys, "settings-open", "--page", "Keymap")
        assert (code, opened["front_restored"], opened["breadcrumb"][-1]) == (0, True, "Keymap")
    finally:
        if ide.settings_window(live):
            ide.jbax("press", str(live), "--label", "Cancel")


def quits_refused(capsys: pytest.CaptureFixture[str], pid: int) -> None:
    """With Settings open, stop and restart refuse, and send the IDE nothing, so it keeps running with the dialog
    open. Settings is not AX-modal: the refusal rests on jbax's window kinds."""
    # Checked first, read-only, with the same check stop makes: were Settings not seen, stop would quit the IDE.
    assert lifecycle.dialogs(pid), "jbctl must see the open Settings window before stop is tried"
    # --check runs every guard and sends nothing, so even a race that closed Settings first could not quit the IDE.
    for command in ("stop", "restart"):
        code, [event], _ = jb(capsys, command, "--check")
        reason = event["lifecycle"]["reason"]
        assert (code, event["lifecycle"]["action"], "dialog or unreadable windows are open" in reason) == (
            1,
            "refused",
            True,
        )
    assert jb(capsys, "resolve")[1][0]["ide"]["pid"] == pid, "the IDE was sent nothing"


def session(capsys: pytest.CaptureFixture[str], tmp_path: Path, via_router: str, pid: int) -> None:
    # A page the IDE does not have: it says so, and no dialog opens.
    code, events, error = jb(capsys, "settings-open", "--page", "No such page")
    assert (code, events, "Settings page not found" in error) == (1, [], True)
    assert ide.settings_window(pid) is None
    # Nothing open: the Settings steps refuse.
    for refused in (["settings-press", "--label", "OK"], ["settings-goto", "--page", "Keymap"]):
        code, events, error = jb(capsys, *refused)
        assert (code, events, bool(error)) == (1, [], True)

    # Through the station socket: the front app stays the one that had it.
    code, [opened], _ = jb(capsys, "settings-open", "--page", "Exposed Tools")
    assert (code, opened["front_restored"], opened["breadcrumb"][-1]) == (0, True, "Exposed Tools")
    window = opened["settings_window"]
    # A record from another run of the IDE (same pid and window id, after a reboot, say) is not this dialog's.
    record = ide.opened_record(pid)
    mine = record.read_text()
    record.write_text("Mon Jan  1 00:00:00 2024\n" + window)
    code, events, error = jb(capsys, "settings-press", "--label", "Cancel")
    assert (code, events, "not opened by jbctl" in error) == (1, [], True)
    record.write_text(mine)
    # A dialog already open is refused, not reused: it could hold the user's unapplied edits.
    code, events, error = jb(capsys, "settings-open", "--page", "Keymap")
    assert (code, events, "already open" in error) == (1, [], True)

    # The breadcrumb ends with the page; a banner in the dialog can add its link (e.g. Dismiss) in front.
    code, [moved], _ = jb(capsys, "settings-goto", "--page", "Keymap")
    assert (code, moved["breadcrumb"][-1]) == (0, "Keymap")
    window = window.removeprefix("w-")
    code, [mapped], _ = jb(capsys, "map", "--window", window, "--out", str(tmp_path / "settings.json"))
    assert code == 0
    assert mapped["nodes"] > 100
    before = Path(mapped["map"]).read_text()
    assert jb(capsys, "map", "--window", window, "--out", mapped["map"])[0] == 1  # never overwrites
    assert Path(mapped["map"]).read_text() == before
    assert jb(capsys, "settings-goto", "--page", "No such page")[0] == 1
    # A real tool failure (rea refuses a window that does not exist) is one failure line, not a crash.
    code, events, error = jb(capsys, "map", "--window", "1", "--out", str(tmp_path / "none.json"))
    assert (code, events, "rea" in error) == (1, [], True)
    assert jb(capsys, "settings-press", "--label", "No such button")[0] == 1
    quits_refused(capsys, pid)
    assert ide.settings_window(pid) is not None, "refusals leave the dialog open"
    # router-direct opens its own dialog too, so it refuses this one; Cancel closes it, applying nothing.
    code, events, error = jb(capsys, "router-direct", "--mcp-url", via_router)
    assert (code, events, "already open" in error) == (1, [], True)
    assert jb(capsys, "settings-press", "--label", "Cancel") == (0, [{"pressed": "Cancel"}], "")
    assert ide.settings_window(pid) is None

    # router-direct against a router-only stand-in: every IDE step runs, then the check fails.
    code, events, _ = jb(capsys, "router-direct", "--mcp-url", via_router)
    assert code == 1
    assert events[0]["breadcrumb"][-3:] == ["AI", "MCP Server", "Exposed Tools"]
    assert events[1:] == [
        {"selected": "ACP agents only"},
        {"pressed": "OK"},
        {"tools": 1, "direct": False, "router": True},
    ]
    assert ide.settings_window(pid) is None

    # A dialog jbctl did not open, as the user's own would be: press and goto refuse it.
    ide.check_background(pid)
    ide.open_from_station(pid, "Keymap")
    for _ in range(40):
        if ide.settings_window(pid):
            break
        time.sleep(0.1)
    for refused in (["settings-press", "--label", "Cancel"], ["settings-goto", "--page", "Keymap"]):
        code, events, error = jb(capsys, *refused)
        assert (code, events, "not opened by jbctl" in error) == (1, [], True)
    assert ide.settings_window(pid) is not None, "refused, so still open"


def test_live_check_direct(capsys: pytest.CaptureFixture[str]) -> None:
    """Read-only: initialize and tools/list, no tool call. An IDE in DIRECT names the router tool as well (#563)."""
    code, [checked], error = jb(capsys, "check-direct")
    assert (code, error, checked["direct"], checked["router"]) == (0, "", True, True)


def test_live_skills_check(capsys: pytest.CaptureFixture[str]) -> None:
    """clion-debugger as the real install ships it (every IDE's air-plugin carries it); --check writes nothing."""

    def snapshot() -> list[tuple[str, int, int]]:
        """Every entry under the agents' skill folders, without following links: its path, size and change time."""
        folders = [Path.home() / ".agents/skills", Path.home() / ".claude/skills"]
        paths = [path for folder in folders if folder.is_dir() for path in folder.rglob("*")]
        return sorted((str(path), path.lstat().st_size, path.lstat().st_ctime_ns) for path in paths)

    before = snapshot()
    code, events, error = jb(capsys, "skills", "--skill", "clion-debugger", "--check")
    assert (code in {0, 1}, error) == (True, "")
    assert [(event["skill"]["agent"], event["skill"]["skill"]) for event in events] == [
        ("codex", "clion-debugger"),
        ("claude", "clion-debugger"),
    ]
    # Its metadata.json gives the version: the jar layout jbctl reads is the one the IDE ships.
    assert all(event["skill"]["install"] == IDE and event["skill"]["version"] for event in events)
    assert snapshot() == before
