"""The running IDE through agent-desktop (windows, the one activation) and jbax (background AX)."""

import json
import os
import subprocess
import time
from typing import Any

# A GUI JetBrains IDE; helper processes such as `clion stdioMcpServer` show no foreground presentation.
BUNDLE_PREFIX = "com.jetbrains."
# A project frame is wider than this; the IDE's toolbar strips and popups are narrower.
FRAME_MIN_WIDTH = 1000
# Seconds before a hung agent-desktop, rea or jbax is a failure instead of a hang.
TIMEOUT = 60


class IdeError(Exception):
    """A step that found the IDE in a state it cannot act on; the CLI reports it as one failure line."""


def tool(*args: str) -> Any:  # noqa: ANN401 - a JSON document whose shape the caller knows
    return json.loads(subprocess.run(args, capture_output=True, text=True, check=True, timeout=TIMEOUT).stdout)


def agent_desktop(*args: str) -> Any:  # noqa: ANN401 - agent-desktop's data member
    return tool("agent-desktop", *args)["data"]


def jbax(*args: str) -> None:
    """jbax prints one JSON object and exits non-zero when it refuses; its refusal is an IdeError, not a crash."""
    command = [os.environ.get("JBAX", "jbax"), *args]
    done = subprocess.run(command, capture_output=True, text=True, check=False, timeout=TIMEOUT)
    if not done.stdout:  # pragma: no cover - #502 MVP: a jbax crash prints no JSON; no live run crashes it
        raise subprocess.CalledProcessError(done.returncode, command, stderr=done.stderr)
    result = json.loads(done.stdout)
    if not result["ok"]:
        msg = f"{result['error']} (jbax exit {done.returncode})"
        raise IdeError(msg)


def pid() -> int:
    for app in agent_desktop("list-apps")["apps"]:
        if app.get("bundle_id", "").startswith(BUNDLE_PREFIX) and app.get("presentation") == "foreground":
            return int(app["pid"])
    # #502 MVP: a live run has an IDE by definition; covering this needs a stand-in agent-desktop.
    msg = "no JetBrains IDE is running"  # pragma: no cover - see above
    raise IdeError(msg)  # pragma: no cover - see above


def app_path(ide: int) -> str:
    """The .app bundle, from the process's executable (rea binds its evidence to it)."""
    executable = subprocess.run(["ps", "-o", "comm=", "-p", str(ide)], capture_output=True, text=True, check=True)
    return executable.stdout.strip().split(".app/", 1)[0] + ".app"


def windows() -> list[dict[str, Any]]:
    return agent_desktop("list-windows")


def settings_window(ide: int, listed: list[dict[str, Any]] | None = None) -> str | None:
    listed = windows() if listed is None else listed
    return next((w["id"] for w in listed if w.get("pid") == ide and w.get("title") == "Settings"), None)


def focused(listed: list[dict[str, Any]]) -> str | None:
    return next((w["id"] for w in listed if w.get("is_focused")), None)


def open_settings(ide: int) -> tuple[str, bool]:
    """Open Settings with the shortest activation, then hand the front back.

    AppKit drops a menu item's AXPress while the app is inactive, so the IDE must come forward. The menu
    item is resolved first, in the background; one batch activates, presses and hands back. Showing the
    dialog can re-activate the IDE after that, so the front is handed back once more if needed.
    """
    listed = windows()
    if open_window := settings_window(ide, listed):
        return open_window, True
    previous = focused(listed)
    frame = next(w["id"] for w in listed if w.get("pid") == ide and w["bounds"]["width"] > FRAME_MIN_WIDTH)
    item = agent_desktop("find", "--surface", "menubar", "--window-id", frame, "--name", "Settings…", "--exact")
    hand_back = [{"command": "focus-window", "args": {"window_id": previous}}] if previous else []
    steps = [
        {"command": "focus-window", "args": {"window_id": frame}},
        {"command": "click", "args": {"ref_id": item["matches"][0]["ref_id"]}},
        *hand_back,
    ]
    agent_desktop("batch", json.dumps(steps), "--stop-on-error")
    deadline = time.monotonic() + 4
    while (window := settings_window(ide)) is None and time.monotonic() < deadline:
        time.sleep(0.1)
    if window is None:  # pragma: no cover - #502 MVP: live-only guard; a working IDE opens Settings
        msg = "Settings did not open"
        raise IdeError(msg)
    # Showing the dialog can re-activate the IDE after the batch, so hand the front back again.
    if hand_back:  # pragma: no branch - #502 MVP: a person at the machine always has some window in front
        agent_desktop("batch", json.dumps(hand_back), "--stop-on-error")
    return window, previous is None or focused(windows()) == previous
