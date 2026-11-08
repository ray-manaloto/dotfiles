"""A stand-in for an IDE's MCP server, in-process (mcp_server) or as a stand-in IDE process (run as a script)."""

# The script is started through a stand-in .app's launcher (tests/conftest.py), so jbctl finds it the way it finds
# a real IDE: by the station socket it owns, its executable inside the app, its built-in web server's /api/about,
# and the loopback port that answers MCP. Its station answers /exit as an IDE's does: it quits, or relaunches
# itself through the same launcher.

import errno
import json
import os
import socketserver
import sys
import threading
from collections.abc import Iterator, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

INITIALIZE = {
    "protocolVersion": "2025-06-18",
    "capabilities": {"tools": {"listChanged": True}},
    "serverInfo": {"name": "stand-in", "version": "0"},
}
DIRECT = ["execute_tool", "get_file_problems", "list_directory_tree"]
# A cursor is the server's own opaque text: this one has a quote, a backslash, a newline and JSON punctuation.
CURSOR = 'next"},{\\\n'


class NotMcp(BaseHTTPRequestHandler):
    """Another listener in the IDE (its web server, say): it has no POST handler, so it answers 501."""

    # The base class names the parameter format; keeping the name keeps the override compatible.
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - see above
        """Keep the test output clean."""


def handler(
    tools: list[str] | None,
    *,
    sse: bool,
    page: int | None = None,
    cursors: Sequence[object] = (),
) -> type[BaseHTTPRequestHandler]:
    """Answers initialize and tools/list the way the IDE's streamable-HTTP MCP server does; with tools None,
    tools/list gets a JSON-RPC error instead. With page, tools/list gives that many tools at a time, and while more
    are left a nextCursor: cursors[0] for the second page, cursors[1] for the third. Only a cursor it issued, exactly
    as issued, gets a page; any other gets a JSON-RPC error. A cursor listed twice comes back twice."""

    class Handler(NotMcp):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if "id" not in body:  # a notification: accepted, no body
                self.send_response(202)
                self.end_headers()
                return
            if body["method"] == "initialize":
                outcome = {"result": INITIALIZE}
            elif tools is None:
                outcome = {"error": {"code": -32601, "message": "Method not found"}}
            else:
                params = body.get("params", {})
                if "cursor" in params and params["cursor"] not in cursors:
                    outcome = {"error": {"code": -32602, "message": "Invalid cursor"}}
                else:
                    index = list(cursors).index(params["cursor"]) + 1 if "cursor" in params else 0
                    size = page or len(tools)
                    start, end = index * size, (index + 1) * size
                    listed: dict[str, object] = {"tools": [{"name": n} for n in tools[start:end]]}
                    outcome = {"result": listed | ({"nextCursor": cursors[index]} if end < len(tools) else {})}
            # Pretty-printed, as a server may send it: the client must parse whole JSON messages, not lines.
            reply = json.dumps({"jsonrpc": "2.0", "id": body["id"], **outcome}, indent=2)
            self.send_response(200)
            self.send_header("Mcp-Session-Id", "session-1")
            self.send_header("Content-Type", "text/event-stream" if sse else "application/json")
            self.end_headers()
            # An SSE event carries a multi-line message as one data: line per line.
            event = "".join(f"data: {line}\r\n" for line in reply.splitlines())
            self.wfile.write((f"event: message\r\n{event}\r\n" if sse else reply).encode())

    return Handler


def serve(handler_class: type[BaseHTTPRequestHandler]) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    # A short poll, so shutdown() in a fixture's teardown returns at once.
    threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True).start()
    return server


def mcp_server(
    tools: list[str] | None, *, sse: bool, page: int | None = None, cursors: Sequence[object] = ()
) -> Iterator[str]:
    server = serve(handler(tools, sse=sse, page=page, cursors=cursors))
    yield f"http://127.0.0.1:{server.server_port}/stream"
    server.shutdown()
    server.server_close()  # a closed socket, so no later lsof finds it listening


class Station(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def station(flags: set[str]) -> type[BaseHTTPRequestHandler]:
    """Answers /exit: --refuse with HTTP 503; --deaf never quits; --stubborn quits only when forced; --hangup
    closes the connection without an answer."""

    class Handler(NotMcp):
        def do_POST(self) -> None:
            if "--hangup" in flags:
                self.close_connection = True
                return
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path != "/exit":  # the only endpoint jbctl's lifecycle sends
                self.send_error(404)
                return
            reply = json.dumps({"immediate": False}).encode()
            self.send_response(503 if "--refuse" in flags else 200)
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            self.wfile.write(reply)
            if "--refuse" in flags or "--deaf" in flags or ("--stubborn" in flags and not body["force"]):
                return
            if body["restart"]:
                launcher = os.environ["STANDIN_LAUNCH"]
                # --restart-not-ready: the relaunched IDE never answers /api/about.
                again = [arg for arg in sys.argv[1:] if arg != "--restart-not-ready"]
                again += ["--no-about"] if "--restart-not-ready" in flags else []
                os.posix_spawn(launcher, [launcher, *again], os.environ, setsid=True)
            threading.Timer(0.1, os._exit, [0]).start()

    return Handler


def about(flags: set[str]) -> type[BaseHTTPRequestHandler]:
    """The built-in web server's /api/about, with the build from the app's product-info.json; --busy: HTTP 429,
    --old: another build, --garbage: not JSON, --die-asked: the IDE ends 1.9 s into the first request, unanswered."""
    info = Path(os.environ["STANDIN_LAUNCH"]).parents[1] / "Resources/product-info.json"
    build = "0.0" if "--old" in flags else json.loads(info.read_text())["buildNumber"]
    reply = "<html>" if "--garbage" in flags else json.dumps({"productName": "Fake", "buildNumber": build})

    class Handler(NotMcp):
        def do_GET(self) -> None:
            if self.path != "/api/about":
                self.send_error(404)
                return
            if "--die-asked" in flags:  # within jbctl's 2 s request timeout, and after a shorter --timeout
                threading.Event().wait(1.9)
                os._exit(0)
            self.send_response(429 if "--busy" in flags else 200)
            self.end_headers()
            self.wfile.write(reply.encode())

    return Handler


class Hangup(socketserver.BaseRequestHandler):
    """A listener that does not speak HTTP (--not-http): it closes each connection without a word."""

    def handle(self) -> None:
        self.request.close()


def web(handler_class: type[socketserver.BaseRequestHandler]) -> socketserver.TCPServer:
    """Bound in the built-in server's range, as an IDE's is: 63342 or a free port after it."""
    for port in range(63343, 63362):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler_class)
        except OSError as error:
            if error.errno != errno.EADDRINUSE:
                raise
            continue
        threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True).start()
        return server
    msg = "no free port for the stand-in's web server"
    raise OSError(msg)


if __name__ == "__main__":
    # argv: flags (--mcp and --http each add a loopback listener) and an IDE's own arguments (project paths, written
    # to STANDIN_RECORD when it is set). Prints the listeners' ports as one JSON line, then serves until /exit, or
    # with --stdin until stdin closes.
    flags = {arg for arg in sys.argv[1:] if arg.startswith("--")}
    if record := os.environ.get("STANDIN_RECORD"):
        Path(record).write_text(json.dumps([arg for arg in sys.argv[1:] if not arg.startswith("--")]))
    kinds = [arg for arg in sys.argv[1:] if arg in {"--mcp", "--http"}]
    servers = [serve(handler(DIRECT, sse=False) if kind == "--mcp" else NotMcp) for kind in kinds]
    if "--no-about" not in flags:
        web(Hangup if "--not-http" in flags else about(flags))
    if "--no-station" not in flags:
        path = Path(os.environ["JBCTL_STATION_DIR"]) / f"jb.station.ij.{os.getpid()}.sock"
        threading.Thread(target=Station(str(path), station(flags)).serve_forever, args=(0.05,), daemon=True).start()
    sys.stdout.write(json.dumps([server.server_port for server in servers]) + "\n")
    sys.stdout.flush()
    if "--die" in flags:  # long enough for jbctl to see it come up
        threading.Event().wait(2)
    elif "--stdin" in flags:
        sys.stdin.read()
    else:
        threading.Event().wait()
