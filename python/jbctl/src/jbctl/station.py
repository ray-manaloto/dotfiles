"""The IDE's station socket: the station plugin's HTTP server on a per-user Unix socket, as Toolbox uses it."""

# Each running IDE binds jb.station.ij.<pid>.sock; requests are HTTP/1.1 POSTs with JSON bodies and no token
# (station-plugin.jar's plugin.xml declares /exit, /showNotification, /focus and /protocolHandler). jbctl sends
# /protocolHandler, which runs a jetbrains:// command in the IDE without going through LaunchServices, so the IDE
# is not activated the way `open jetbrains://...` activates it, and /exit, the request Toolbox's Quit sends.

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import httpx

# _CS_DARWIN_USER_TEMP_DIR in the macOS SDK's unistd.h: the JVM's temporary folder. os.confstr_names does not
# list it. JBCTL_STATION_DIR replaces it, for a stand-in IDE.
DARWIN_USER_TEMP_DIR = 65537
SOCKET = re.compile(r"jb\.station\.ij\.(\d+)\.sock")


def folder() -> Path:
    return Path(os.environ.get("JBCTL_STATION_DIR") or os.confstr(DARWIN_USER_TEMP_DIR) or tempfile.gettempdir())


def sockets() -> dict[int, Path]:
    """Every station socket file by the pid in its name; a file outlives its IDE, so the pid may be gone or reused."""
    return {int(found[1]): path for path in folder().iterdir() if (found := SOCKET.fullmatch(path.name))}


def post(pid: int, endpoint: str, body: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
    """The HTTP status and JSON reply of one request to the station of the IDE with this pid."""
    transport = httpx.HTTPTransport(uds=str(folder() / f"jb.station.ij.{pid}.sock"))
    with httpx.Client(transport=transport, base_url="http://localhost", timeout=timeout) as client:
        response = client.post(endpoint, json=body)
    return response.status_code, response.json() if response.content else {}
