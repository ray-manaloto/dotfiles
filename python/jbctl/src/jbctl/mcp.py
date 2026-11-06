"""The IDE's MCP server as ground truth: initialize and tools/list only, never a tool call."""

import json
import urllib.request
from typing import Any

HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def post(url: str, body: dict[str, Any], session: str | None) -> tuple[str | None, str]:
    headers = HEADERS | ({"Mcp-Session-Id": session} if session else {})
    request = urllib.request.Request(url, json.dumps(body).encode(), headers, method="POST")  # noqa: S310 - the caller's local MCP URL
    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - the caller's local MCP URL
        return response.headers.get("Mcp-Session-Id"), response.read().decode()


def tool_count(url: str) -> int:
    """VIA_ROUTER lists only the router tool (execute_tool); DIRECT lists every tool."""
    hello = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "jbctl", "version": "0"}}
    session, _ = post(url, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": hello}, None)
    post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    _, text = post(url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, session)
    # A streamable-HTTP reply is either plain JSON or server-sent events with the JSON on a data: line.
    lines = [line.removeprefix("data:").strip() for line in text.splitlines() if '"result"' in line]
    return len(json.loads(lines[0])["result"]["tools"])
