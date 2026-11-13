"""What runs without an IDE: argument parsing, the MCP check, and the rea helper patch."""

from pathlib import Path

import pytest

from jbctl import rea

from .conftest import run
from .standin import CURSOR


@pytest.mark.parametrize("argv", [[], ["click"]])
def test_the_first_argument_must_name_a_command(capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
    code, events, error = run(capsys, *argv)
    assert (code, events, bool(error)) == (1, [], True)


def test_a_required_option_is_enforced(capsys: pytest.CaptureFixture[str]) -> None:
    code, events, error = run(capsys, "settings-goto")
    assert (code, events, bool(error)) == (1, [], True)


def test_check_direct_reads_the_tool_list(capsys: pytest.CaptureFixture[str], direct: str) -> None:
    assert run(capsys, "check-direct", "--mcp-url", direct) == (0, [{"tools": 3, "direct": True, "router": True}], "")


def test_check_direct_fails_while_router_only(capsys: pytest.CaptureFixture[str], via_router: str) -> None:
    assert run(capsys, "check-direct", "--mcp-url", via_router) == (
        1,
        [{"tools": 1, "direct": False, "router": True}],
        "",
    )


def test_check_direct_reports_a_missing_router_tool(capsys: pytest.CaptureFixture[str], unrouted: str) -> None:
    """DIRECT without execute_tool is still DIRECT: the router field says a router-only skill cannot run."""
    assert run(capsys, "check-direct", "--mcp-url", unrouted) == (
        0,
        [{"tools": 2, "direct": True, "router": False}],
        "",
    )


def test_check_direct_reads_every_page(capsys: pytest.CaptureFixture[str], paged: str) -> None:
    """The second page, with the router tool, comes only if the cursor goes back exactly as sent, empty or not: only
    a missing nextCursor ends the list."""
    assert run(capsys, "check-direct", "--mcp-url", paged) == (0, [{"tools": 3, "direct": True, "router": True}], "")


def test_a_cursor_that_is_not_text_is_a_failure(capsys: pytest.CaptureFixture[str], number_cursor: str) -> None:
    assert run(capsys, "check-direct", "--mcp-url", number_cursor) == (
        1,
        [],
        f"{number_cursor}: tools/list gave a nextCursor that is not text",
    )


def test_a_repeated_cursor_is_a_failure(capsys: pytest.CaptureFixture[str], stuck: str) -> None:
    """The server's cursor stays inert in the one Failure line (run parses stderr as a single JSON object)."""
    assert run(capsys, "check-direct", "--mcp-url", stuck) == (1, [], f"{stuck}: tools/list repeated cursor {CURSOR}")


def test_a_tools_list_without_a_tool_list_is_a_failure(capsys: pytest.CaptureFixture[str], no_tool_list: str) -> None:
    """The URL in the failure is the caller's text: JSON-significant characters stay inert in one Failure line."""
    url = no_tool_list + '?q="},{\\'
    assert run(capsys, "check-direct", "--mcp-url", url) == (1, [], f"{url}: tools/list returned no tool list")


def test_an_unreachable_mcp_server_is_a_failure(capsys: pytest.CaptureFixture[str]) -> None:
    code, events, error = run(capsys, "check-direct", "--mcp-url", "http://127.0.0.1:9/stream")
    assert (code, events, bool(error)) == (1, [], True)


def test_rea_patch_applies_once(capsys: pytest.CaptureFixture[str], pristine: Path) -> None:
    assert run(capsys, "rea-patch", "--helper", str(pristine)) == (0, [{"patch": "applied"}], "")
    assert rea.MARKER in pristine.read_text()
    assert run(capsys, "rea-patch", "--helper", str(pristine)) == (0, [{"patch": "already"}], "")


def test_rea_patch_refuses_a_changed_helper(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    helper = tmp_path / "ReaNativeUI.swift"
    helper.write_text("func observe() {}\n")
    code, events, error = run(capsys, "rea-patch", "--helper", str(helper))
    assert (code, events, bool(error)) == (1, [], True)
    assert helper.read_text() == "func observe() {}\n"
