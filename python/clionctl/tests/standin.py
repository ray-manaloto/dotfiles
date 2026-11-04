"""A stand-in IDE: the station socket and POST /exit that CLion's station plugin serves, in an app bundle."""

# A real IDE cannot start in a test (minutes, a licence, a GUI session), so this does the station's observable job.
# conftest copies it into Contents/MacOS of a bundle; Contents/Resources/standin.json says where to bind the socket,
# which TCP port to hold, and what /exit does:
# - obey: quit, or with restart true launch the bundle again with open -n, as IDE restarts go through a new process;
# - dialog: answer 200 and keep running, as an IDE whose quit waits on a question;
# - quit: quit even when asked to restart, so no new process comes;
# - missing: 404 with X-Station-Failure no-endpoint, as an IDE without the endpoint;
# - hangup: close the connection without an answer.
# It writes argv-<pid>.json and exit-<pid>.json (the /exit body) next to standin.json, and leaves its socket file
# behind when it ends, as the IDE does.

import json
import os
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from socketserver import UnixStreamServer

RESOURCES = Path(sys.argv[0]).resolve().parents[1] / "Resources"
CONFIG = json.loads((RESOURCES / "standin.json").read_text())
# The /exit bodies answered with 200; the main loop serves until there is one.
EXITS: list[dict] = []


class Station(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if CONFIG["mode"] == "hangup":
            self.close_connection = True
            return
        if self.path != "/exit" or CONFIG["mode"] == "missing":
            self.send_response(404)
            self.send_header("X-Station-Failure", "no-endpoint")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        (RESOURCES / f"exit-{os.getpid()}.json").write_text(json.dumps(body))
        reply = b'{"immediate":false}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)
        EXITS.append(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - the base class names it format
        """No access log: a Unix socket's client address is empty, which the default log cannot format."""


def main() -> None:
    (RESOURCES / f"argv-{os.getpid()}.json").write_text(json.dumps(sys.argv[1:]))
    port = CONFIG.get("mcp_port")
    held = socket.create_server(("127.0.0.1", port)) if port else None
    server = UnixStreamServer(str(Path(CONFIG["folder"]) / f"jb.station.ij.{os.getpid()}.sock"), Station)
    while not EXITS:
        server.handle_request()
    if CONFIG["mode"] == "dialog":
        time.sleep(3600)
    if held:
        held.close()
    if CONFIG["mode"] == "obey" and EXITS[0]["restart"]:
        subprocess.run(["/usr/bin/open", "-n", str(RESOURCES.parents[1])], check=True)
    server.server_close()


main()
