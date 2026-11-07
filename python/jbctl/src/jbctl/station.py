"""The IDE's station socket: the station plugin's HTTP server on a per-user Unix socket, as Toolbox uses it."""

# Each running IDE binds jb.station.ij.<pid>.sock; requests are HTTP/1.1 POSTs with JSON bodies and no token
# (station-plugin.jar's plugin.xml declares /exit, /showNotification, /focus and /protocolHandler). jbctl sends
# only /protocolHandler, which runs a jetbrains:// command in the IDE without going through LaunchServices, so
# the IDE is not activated the way `open jetbrains://...` activates it.

import http.client
import json
import os
import socket
import tempfile
from pathlib import Path
from typing import Any

# _CS_DARWIN_USER_TEMP_DIR in the macOS SDK's unistd.h: the JVM's temporary folder. os.confstr_names does not
# list it. JBCTL_STATION_DIR replaces it, for a stand-in IDE.
DARWIN_USER_TEMP_DIR = 65537


def folder() -> Path:
    return Path(os.environ.get("JBCTL_STATION_DIR") or os.confstr(DARWIN_USER_TEMP_DIR) or tempfile.gettempdir())


class Connection(http.client.HTTPConnection):
    """HTTP over the IDE's Unix socket."""

    def __init__(self, path: Path, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


def post(pid: int, endpoint: str, body: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
    """The HTTP status and JSON reply of one request to the station of the IDE with this pid."""
    connection = Connection(folder() / f"jb.station.ij.{pid}.sock", timeout)
    try:
        connection.request("POST", endpoint, json.dumps(body), {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read() or b"{}")
    finally:
        connection.close()
