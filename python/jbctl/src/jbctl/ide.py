"""The IDE that toolbox.py found: its station socket, agent-desktop (windows) and jbax (background AX)."""

import json
import math
import os
import subprocess
import time
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from typing import Any

from . import station

# A project frame is larger than this; the IDE's toolbar strips (as wide as a frame, 33 px high) and popups are not.
FRAME_MIN_WIDTH = 1000
FRAME_MIN_HEIGHT = 300
# The one opt-in for the route that brings the IDE forward (opening Settings from the menu bar), off by default:
# the default runs are fully background, and the foreground route is for debugging when a headless one fails.
FOREGROUND = "JETBRAINS_FOREGROUND"
# Seconds before a hung agent-desktop, rea, jbax, ps or lsof is a failure instead of a hang.
TIMEOUT = 60
DAY = 86400


def helper_timeout() -> float:
    """TIMEOUT, or JBCTL_TIMEOUT when set (a slow machine; the tests set 0 to make a real helper time out)."""
    raw = os.environ.get("JBCTL_TIMEOUT")
    if not raw:
        return TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    # nan, inf and huge values overflow the wait (OverflowError, not a Failure line); a negative one means nothing.
    if not 0 <= value <= DAY:
        msg = f"JBCTL_TIMEOUT is {raw!r}; want seconds from 0 to {DAY}"
        raise ValueError(msg)
    return value


class IdeError(Exception):
    """A step that cannot find the IDE --ide names, or finds it in a state it cannot act on; one failure line."""


def tool(*args: str) -> Any:  # noqa: ANN401 - a JSON document whose shape the caller knows
    return json.loads(subprocess.run(args, capture_output=True, text=True, check=True, timeout=helper_timeout()).stdout)


def agent_desktop(*args: str) -> Any:  # noqa: ANN401 - agent-desktop's data member
    return tool("agent-desktop", *args)["data"]


def jbax(*args: str) -> dict[str, Any]:
    """jbax prints one JSON object and exits non-zero when it refuses; its refusal is an IdeError, not a crash."""
    command = [os.environ.get("JBAX", "jbax"), *args]
    done = subprocess.run(command, capture_output=True, text=True, check=False, timeout=helper_timeout())
    # A jbax that crashed prints no JSON. Not covered: no test can make the real jbax crash, and the owner ruled
    # out a stand-in; it stays visible in the coverage report.
    if not done.stdout:
        msg = f"jbax printed nothing (exit {done.returncode}): {done.stderr.strip()}"
        raise IdeError(msg)
    result = json.loads(done.stdout)
    if not result["ok"]:
        msg = f"{result['error']} (jbax exit {done.returncode})"
        raise IdeError(msg)
    return result


def windows() -> list[dict[str, Any]]:
    return agent_desktop("list-windows")


def settings_window(ide: int, listed: list[dict[str, Any]] | None = None) -> str | None:
    listed = windows() if listed is None else listed
    return next((w["id"] for w in listed if w.get("pid") == ide and w.get("title") == "Settings"), None)


def opened_record(ide: int) -> Path:
    """Where settings-open records the Settings window it opened for this IDE, for the later steps to check."""
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return state / "jbctl" / f"settings-{ide}"


def owned(ide: int, window: str) -> str:
    """The record for this window: the IDE process's start time, then the window id."""
    # A pid and a window id are unique only within one login session (a reboot reuses both): the start time binds
    # them to this run of the IDE.
    started = subprocess.run(["ps", "-o", "lstart=", "-p", str(ide)], capture_output=True, text=True, check=True,
                             timeout=helper_timeout()).stdout.strip()  # fmt: skip
    return f"{started}\n{window}"


def own_settings(ide: int) -> str:
    """The open Settings window, if jbctl opened it; any other may hold the user's unapplied edits."""
    window = settings_window(ide)
    if window is None:
        msg = "Settings is not open (jbctl settings-open)"
        raise IdeError(msg)
    record = opened_record(ide)
    if not record.exists() or record.read_text() != owned(ide, window):
        msg = "this Settings window was not opened by jbctl settings-open, so jbctl leaves it alone"
        raise IdeError(msg)
    return window


def focused(listed: list[dict[str, Any]]) -> str | None:
    return next((w["id"] for w in listed if w.get("is_focused")), None)


def open_settings(ide: int, page: str) -> tuple[str, bool]:
    """Open Settings on `page`, and say whether the front app is the one that had it before.

    By default through the IDE's station socket, which leaves the IDE in the background. With
    JETBRAINS_FOREGROUND=1, through the menu bar instead, which brings the IDE forward: for debugging a headless
    failure only, never as an automatic fallback.
    """
    listed = windows()
    # A dialog jbctl did not open may hold the user's unapplied edits, which a later Cancel or OK would discard or
    # save: refuse it rather than reuse it.
    if settings_window(ide, listed):
        msg = "a Settings window is already open; close it first, since jbctl drives only a dialog it opened"
        raise IdeError(msg)
    previous = focused(listed)
    hand_back = [{"command": "focus-window", "args": {"window_id": previous}}] if previous else []
    foreground = os.environ.get(FOREGROUND) == "1"
    if not foreground:
        check_background(ide)
        open_from_station(ide, page)
    else:  # pragma: foreground - the debug route, which the default runs never take
        open_from_menu(ide, listed, hand_back)
    window, deadline = None, time.monotonic() + 4
    while window is None and time.monotonic() < deadline:
        time.sleep(0.1)
        window = settings_window(ide)
    if window is None:
        msg = "Settings did not open"
        raise IdeError(msg)
    opened_record(ide).parent.mkdir(parents=True, exist_ok=True)
    opened_record(ide).write_text(owned(ide, window))
    # Showing the dialog can re-activate the IDE after the menu route's batch, so hand the front back again.
    if foreground and hand_back:  # pragma: foreground - the debug route's second hand-back
        agent_desktop("batch", json.dumps(hand_back), "--stop-on-error")
    # With no focused window before, the front is unchanged only if none is focused now either.
    return window, focused(windows()) == previous


def frames(ide: int, listed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The IDE's project windows, minimized ones included."""
    return [
        w
        for w in listed
        if w.get("pid") == ide and w["bounds"]["width"] > FRAME_MIN_WIDTH and w["bounds"]["height"] > FRAME_MIN_HEIGHT
    ]


def check_background(ide: int) -> None:
    """Refuse the states in which showing Settings may bring the IDE forward; `jbax windows` names them."""
    if risk := jbax("windows", str(ide))["unsafe"]:
        msg = f"Settings may bring the IDE forward from this state ({risk}); only visible project windows are safe"
        raise IdeError(msg)


def open_from_station(ide: int, page: str) -> None:
    """POST the settings command to the IDE's station socket: no LaunchServices, so no activation.

    name= returns once the dialog is scheduled (invokeLater); page_id= instead waits for the dialog to show,
    which a modal Settings turns into a wait until it closes. The host is a placeholder: the IDE reads only the
    command (JBProtocolCommand.execute), so one URI serves every product.
    """
    uri = "jetbrains://idea/settings?" + urllib.parse.urlencode({"name": page}, quote_via=urllib.parse.quote)
    status, reply = station.post(ide, "/protocolHandler", {"uri": uri}, helper_timeout())
    # The IDE reports a refused command as exit code 0 with a message.
    if status != HTTPStatus.OK or reply.get("exitCode") != 0 or reply.get("message"):
        msg = f"the IDE did not open Settings on {page}: HTTP {status} {reply}"
        raise IdeError(msg)


def open_from_menu(  # pragma: foreground - the debug route (JETBRAINS_FOREGROUND=1)
    ide: int, listed: list[dict[str, Any]], hand_back: list[dict[str, Any]]
) -> None:
    """Debug route: activate the IDE, press the menu bar's Settings…, and hand the front back.

    AppKit drops a menu item's AXPress while the app is inactive. The item is resolved in the background first;
    one batch activates, presses and hands back.
    """
    frame = frames(ide, listed)[0]["id"]
    item = agent_desktop("find", "--surface", "menubar", "--window-id", frame, "--name", "Settings…", "--exact")
    steps = [
        {"command": "focus-window", "args": {"window_id": frame}},
        {"command": "click", "args": {"ref_id": item["matches"][0]["ref_id"]}},
        *hand_back,
    ]
    agent_desktop("batch", json.dumps(steps), "--stop-on-error")
