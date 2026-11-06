"""One pass over a running JetBrains IDE, opt-in with JBCTL_LIVE=1."""

# It brings the IDE forward once, for about a second, to open Settings. Every other step runs with the
# IDE in the background, and its settings end as they started: router-direct only commits DIRECT, which
# the run requires up front.

import os
from pathlib import Path

import pytest

from jbctl import ide, mcp

from .conftest import run

pytestmark = pytest.mark.skipif(os.environ.get("JBCTL_LIVE") != "1", reason="set JBCTL_LIVE=1 with an IDE running")
LIVE_MCP = "http://127.0.0.1:64362/stream"


def test_live_session(capsys: pytest.CaptureFixture[str], tmp_path: Path, via_router: str) -> None:
    pid = ide.pid()
    assert mcp.tool_count(LIVE_MCP) > 1, "start from DIRECT, so the run changes nothing"
    # An open dialog may hold the user's unapplied edits: never cancel it on their behalf.
    assert ide.settings_window(pid) is None, "close Settings first"
    try:
        session(capsys, tmp_path, via_router, pid)
    finally:
        # A failure part-way must not leave a changed dialog open; Cancel applies nothing.
        if ide.settings_window(pid):
            run(capsys, "settings-press", "--label", "Cancel")
    assert run(capsys, "check-direct", "--mcp-url", LIVE_MCP)[0] == 0


def session(capsys: pytest.CaptureFixture[str], tmp_path: Path, via_router: str, pid: int) -> None:
    # Nothing open: the Settings steps refuse.
    for refused in (["settings-press", "--label", "OK"], ["settings-goto", "--page", "Keymap"]):
        code, events, error = run(capsys, *refused)
        assert (code, events, bool(error)) == (1, [], True)

    # The one activation, then everything in the background.
    code, [opened], _ = run(capsys, "settings-open")
    assert code == 0
    assert opened["front_restored"] is True
    assert run(capsys, "settings-open") == (0, [opened], "")

    assert run(capsys, "settings-goto", "--page", "Keymap") == (0, [{"breadcrumb": ["Keymap"]}], "")
    window = opened["settings_window"].removeprefix("w-")
    code, [mapped], _ = run(capsys, "map", "--window", window, "--out", str(tmp_path / "settings.json"))
    assert code == 0
    assert mapped["nodes"] > 100
    before = Path(mapped["map"]).read_text()
    assert run(capsys, "map", "--window", window, "--out", mapped["map"])[0] == 1  # never overwrites
    assert Path(mapped["map"]).read_text() == before
    assert run(capsys, "settings-goto", "--page", "No such page")[0] == 1
    # A real tool failure (rea refuses a window that does not exist) is one failure line, not a crash.
    code, events, error = run(capsys, "map", "--window", "1", "--out", str(tmp_path / "none.json"))
    assert (code, events, "rea" in error) == (1, [], True)
    assert run(capsys, "settings-press", "--label", "No such button")[0] == 1
    assert ide.settings_window(pid) is not None, "refusals leave the dialog open"

    # router-direct against a router-only stand-in: every IDE step runs, then the check fails.
    code, events, _ = run(capsys, "router-direct", "--mcp-url", via_router)
    assert code == 1
    assert events == [
        opened,
        {"breadcrumb": ["AI", "MCP Server", "Exposed Tools"]},
        {"selected": "ACP agents only"},
        {"pressed": "OK"},
        {"tools": 1, "direct": False},
    ]
    assert ide.settings_window(pid) is None
