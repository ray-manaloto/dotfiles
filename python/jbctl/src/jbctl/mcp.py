"""The IDE's MCP server as ground truth: initialize and tools/list only, never a tool call."""

import json
from typing import Any

import httpx

ROUTER = "execute_tool"
HEADERS = {"Accept": "application/json, text/event-stream"}
HELLO = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "jbctl", "version": "0"}}


def post(url: str, body: dict[str, Any], session: str | None, timeout: float = 5) -> tuple[str | None, dict[str, Any]]:
    """One JSON-RPC request; a notification's reply has no body, so its result is {}."""
    headers = HEADERS | ({"Mcp-Session-Id": session} if session else {})
    response = httpx.post(url, json=body, headers=headers, timeout=timeout)
    response.raise_for_status()
    # A streamable-HTTP reply is one JSON message, or server-sent events: blank-line separated, each event's
    # data: lines joined with newlines are one JSON message. The reply is the message that carries a result.
    if response.headers.get("content-type", "").split(";")[0].strip() == "text/event-stream":
        events = response.text.replace("\r\n", "\n").split("\n\n")
        data = [
            "\n".join(d.removeprefix("data:").removeprefix(" ") for d in e.splitlines() if d.startswith("data:"))
            for e in events
        ]
        messages = [json.loads(d) for d in data if d]
    else:
        messages = [response.json()] if response.content else []
    return response.headers.get("Mcp-Session-Id"), next((m["result"] for m in messages if "result" in m), {})


def initialize(url: str, timeout: float = 5) -> tuple[str | None, dict[str, Any]]:
    return post(url, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": HELLO}, None, timeout)


def answers(url: str) -> bool:
    """Whether an MCP server answers initialize at url; anything else on the port (or nothing) is a no."""
    try:
        return "serverInfo" in initialize(url, timeout=1)[1]
    except httpx.HTTPError, ValueError:
        return False


def tool_names(url: str) -> list[str]:
    """The names tools/list gives, every page of them. VIA_ROUTER lists only the router tool (execute_tool); DIRECT
    lists every tool."""
    session, _ = initialize(url)
    post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    names: list[str] = []
    cursor: str | None = None
    seen: set[str] = set()
    request = 1  # initialize was 1: each request in the session gets a fresh id
    while True:
        request += 1
        params = {} if cursor is None else {"cursor": cursor}
        listed = post(url, {"jsonrpc": "2.0", "id": request, "method": "tools/list", "params": params}, session)[1]
        if "tools" not in listed:  # an error reply, or a result without the list
            msg = f"{url}: tools/list returned no tool list"
            raise ValueError(msg)
        names += [tool["name"] for tool in listed["tools"]]
        # Only a missing nextCursor ends the list; an empty string is still a cursor, and null is not one.
        if "nextCursor" not in listed:
            return names
        match listed["nextCursor"]:
            case str() as cursor if cursor not in seen:
                seen.add(cursor)
            case str() as repeated:  # a server paging in a circle would keep this loop going forever
                msg = f"{url}: tools/list repeated cursor {repeated}"
                raise ValueError(msg)
            case _:
                msg = f"{url}: tools/list gave a nextCursor that is not text"
                raise ValueError(msg)
