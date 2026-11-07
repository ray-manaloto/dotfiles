"""A server reply or a text file verify cannot use fails only its own check by name, never with a traceback."""

import json
import os
from pathlib import Path

import pytest

from .conftest import check_after, events, launcher

MCP = "MCP server answers over stdio: the mise build, every read-only tool"
SCOUT = "codebase-memory-scout"
# Each plain text file verify reads, and the one check that reads it.
TEXT_FILES = {
    f".claude/agents/{SCOUT}.md": f"Claude agent {SCOUT}: present, read-only CBM tools only",
    ".codex/AGENTS.md": "Codex AGENTS.md has the CBM managed block, pointing at the skill",
    f".config/opencode/agents/{SCOUT}.md": f"OpenCode agent {SCOUT}: a subagent, read-only CBM tools only",
    ".config/opencode/AGENTS.md": "OpenCode AGENTS.md has the CBM managed block, pointing at the skill",
    ".config/opencode/plugins/cbm-augment.ts": "OpenCode plugin cbm-augment runs the launcher",
}
AS_ROOT = pytest.mark.skipif(os.geteuid() == 0, reason="root reads a mode 0o000 file, so the read would not fail")
# A JSON value that is not an object, in each form it can take.
NOT_OBJECTS = [4, [], [1], "x", True, None]


def fault(home: Path, at: str, value: object) -> None:
    """Make the stand-in server put this value at one place in its replies (conftest.py, HOME/mcp-fault)."""
    (home / "mcp-fault").write_text(json.dumps({"at": at, "value": value}))


@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_a_reply_line_that_is_not_an_object_is_an_error_event_and_fails_only_the_serves_check(
    home: Path, value: object
) -> None:
    done = check_after(home, lambda: fault(home, "line", value), MCP)
    [error] = events(done.stderr)
    assert error["code"] == "invalid_mcp_response"
    assert error["message"] == "cbm: the MCP server answered a JSON line that is not an object"
    assert error["path"] == str(launcher(home))


# Where inside the replies a value of the wrong shape goes: either request's result, the server info, the tool list, a
# tool entry, a tool's name (a text name is a well-formed one) or each reply's id (one that is not the request's).
INSIDE = [
    (at, value)
    for at in ("initialize", "tools/list", "serverInfo", "tools", "tool", "name", "id")
    for value in NOT_OBJECTS
    if not (at == "name" and isinstance(value, str))
]


@pytest.mark.parametrize(("at", "value"), INSIDE)
def test_a_reply_of_another_shape_inside_fails_only_the_serves_check(home: Path, at: str, value: object) -> None:
    done = check_after(home, lambda: fault(home, at, value), MCP)
    assert done.stderr == ""
    [detail] = [event["detail"] for event in events(done.stdout) if event.get("name") == MCP]
    # The reply that lost its shape answers nothing: the version, the tools, or both when no id matches.
    assert detail.startswith("no version, ") == (at in ("initialize", "serverInfo", "id"))
    assert (", 0 tools" in detail) == (at in ("tools/list", "tools", "tool", "name", "id"))


def unreadable(path: Path, kind: str) -> None:
    """Turn the installed file into one verify cannot read as text."""
    if kind == "folder":
        path.unlink()
        path.mkdir()
    elif kind == "fifo":
        path.unlink()
        os.mkfifo(path)
    elif kind == "invalid utf-8":
        path.write_bytes(path.read_bytes() + b"\xff\n")
    else:
        path.chmod(0o000)


@pytest.mark.parametrize("rel", TEXT_FILES)
@pytest.mark.parametrize(
    "kind",
    [
        "folder",
        "fifo",
        "invalid utf-8",
        pytest.param("mode 0o000", marks=AS_ROOT),
    ],
)
def test_a_text_file_verify_cannot_read_is_unreadable_file_and_fails_only_its_check(
    home: Path, rel: str, kind: str
) -> None:
    path = home / rel
    # A FIFO is never opened, so verify cannot block on it; the call's own timeout would fail the test.
    done = check_after(home, lambda: unreadable(path, kind), TEXT_FILES[rel])
    [error] = events(done.stderr)
    assert error["code"] == "unreadable_file"
    assert error["path"] == str(path)
    assert error["message"].startswith("cbm: cannot read: ")
