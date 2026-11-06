"""The command line run in-process, and a stand-in MCP server (the real one needs a running IDE)."""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from jbctl.cli import main


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, list[dict[str, Any]], str]:
    """Exit code, stdout JSON lines, and the stderr failure (empty when none)."""
    try:
        main(list(argv))
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capsys.readouterr()
    lines = [json.loads(line) for line in out.splitlines()]
    return code, lines, json.loads(err)["error"] if err else ""


RESULTS = {
    "initialize": {
        "protocolVersion": "2025-06-18",
        "capabilities": {"tools": {"listChanged": True}},
        "serverInfo": {"name": "stand-in", "version": "0"},
    },
}


def mcp_server(tools: list[str], *, sse: bool) -> Iterator[str]:
    """Answers initialize and tools/list the way the IDE's streamable-HTTP MCP server does."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if "id" not in body:  # a notification: accepted, no body
                self.send_response(202)
                self.end_headers()
                return
            result = (
                RESULTS[body["method"]] if body["method"] != "tools/list" else {"tools": [{"name": n} for n in tools]}
            )
            reply = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result})
            self.send_response(200)
            self.send_header("Mcp-Session-Id", "session-1")
            self.send_header("Content-Type", "text/event-stream" if sse else "application/json")
            self.end_headers()
            self.wfile.write((f"event: message\ndata: {reply}\n\n" if sse else reply).encode())

        # The base class names the parameter format; keeping the name keeps the override compatible.
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - see above
            """Keep the test output clean."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/stream"
    server.shutdown()


@pytest.fixture
def via_router() -> Iterator[str]:
    yield from mcp_server(["execute_tool"], sse=True)


@pytest.fixture
def direct() -> Iterator[str]:
    yield from mcp_server(["execute_tool", "get_file_problems", "list_directory_tree"], sse=False)
