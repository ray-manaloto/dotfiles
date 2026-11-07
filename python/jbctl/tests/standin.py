"""A stand-in for an IDE's MCP server, in-process (mcp_server) or as a stand-in IDE process (run as a script)."""

# The script is started from a stand-in .app (tests/conftest.py's start fixture), so jbctl finds it the way it
# finds a real IDE: by its station socket, its executable inside the app, and the loopback port that answers MCP.

import json
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

INITIALIZE = {
    "protocolVersion": "2025-06-18",
    "capabilities": {"tools": {"listChanged": True}},
    "serverInfo": {"name": "stand-in", "version": "0"},
}
DIRECT = ["execute_tool", "get_file_problems", "list_directory_tree"]


class NotMcp(BaseHTTPRequestHandler):
    """Another listener in the IDE (its web server, say): it has no POST handler, so it answers 501."""

    # The base class names the parameter format; keeping the name keeps the override compatible.
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - see above
        """Keep the test output clean."""


def handler(tools: list[str] | None, *, sse: bool) -> type[BaseHTTPRequestHandler]:
    """Answers initialize and tools/list the way the IDE's streamable-HTTP MCP server does; with tools None,
    tools/list gets a JSON-RPC error instead."""

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
                outcome = {"result": {"tools": [{"name": n} for n in tools]}}
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


def mcp_server(tools: list[str] | None, *, sse: bool) -> Iterator[str]:
    server = serve(handler(tools, sse=sse))
    yield f"http://127.0.0.1:{server.server_port}/stream"
    server.shutdown()
    server.server_close()  # a closed socket, so no later lsof finds it listening


if __name__ == "__main__":
    # argv: one loopback listener per word, "mcp" or "http". Prints their ports as one JSON line, then serves
    # until stdin closes.
    servers = [serve(handler(DIRECT, sse=False) if kind == "mcp" else NotMcp) for kind in sys.argv[1:]]
    sys.stdout.write(json.dumps([server.server_port for server in servers]) + "\n")
    sys.stdout.flush()
    sys.stdin.read()
