"""A client config with the wrong shape at a nested level fails its own check by name, never with a traceback."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from .conftest import cbm, check_after

CLAUDE_HOOKS = "Claude has the 7 CBM hook groups, once each"
CLAUDE_MCP = "Claude MCP entry names the launcher, no args or env"
CODEX_MCP = "Codex MCP entry names the launcher, no args or env"
SCOUT = "Codex agent codebase-memory-scout: launcher, scout profile, read-only CBM tools only"
OPENCODE_MCP = "OpenCode MCP entry names the launcher, no args or env"
SERVER = "codebase-memory-mcp"
# A level that is not a table, in each JSON and TOML form it can take.
JSON_LEVELS = [4, [], [1], "x", True, None]
TOML_LEVELS = ["4", "[]", "[1]", '"x"', "true"]
# Groups a hooks list can hold that are not hook groups, or hold no hook entries.
MALFORMED_GROUPS = [1, None, {"hooks": 1}, {"matcher": "*", "hooks": [1, None, {"command": 2}, {"type": []}]}]


def settings(home: Path) -> Path:
    return home / ".claude/settings.json"


def role(home: Path) -> Path:
    return home / ".codex/agents/codebase-memory-scout.toml"


def role_head() -> str:
    """The scout role's own keys, as the installer writes them, before its MCP table."""
    return 'name = "codebase-memory-scout"\nsandbox_mode = "read-only"\n'


def edit_json(path: Path, change: Callable[[dict[str, Any]], object]) -> Callable[[], None]:
    def edit() -> None:
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value))

    return edit


def splice(path: Path, old: str, new: str) -> None:
    """Replace the first `old` in the stand-in's file with `new`, asserting that changed it: a change to what the
    stand-in writes then fails the test instead of leaving the file as it was."""
    text = path.read_text()
    spliced = text.replace(old, new, 1)
    assert spliced != text, f"{old!r} is not in {path}:\n{text}"
    path.write_text(spliced)


def quiet(done: subprocess.CompletedProcess[str]) -> None:
    """No error event and no traceback: stderr stays empty."""
    assert done.stderr == ""


@pytest.mark.parametrize(
    "hooks",
    [
        *JSON_LEVELS,
        {"SessionStart": 4},
        {"SessionStart": {"matcher": "startup"}},
        {"SessionStart": MALFORMED_GROUPS, "PreToolUse": [None], "PostToolUse": [{"matcher": "Read", "hooks": 4}]},
    ],
)
def test_malformed_claude_hook_levels_fail_only_the_hooks_check(home: Path, hooks: object) -> None:
    done = check_after(home, lambda: settings(home).write_text(json.dumps({"hooks": hooks})), CLAUDE_HOOKS)
    quiet(done)


def test_a_cbm_claude_hook_under_a_matcher_that_is_not_text_fails_the_hooks_check(home: Path) -> None:
    def change(value: dict[str, Any]) -> None:
        value["hooks"]["SessionStart"][0]["matcher"] = ["startup"]

    quiet(check_after(home, edit_json(settings(home), change), CLAUDE_HOOKS))


@pytest.mark.parametrize("level", ["mcpServers", SERVER])
@pytest.mark.parametrize("value", JSON_LEVELS)
def test_a_claude_mcp_level_that_is_not_an_object_fails_only_its_check(home: Path, level: str, value: object) -> None:
    path = home / ".claude.json"
    servers = value if level == "mcpServers" else {SERVER: value}
    quiet(check_after(home, lambda: path.write_text(json.dumps({"mcpServers": servers})), CLAUDE_MCP))


@pytest.mark.parametrize("level", ["mcp_servers", f"mcp_servers.{SERVER}"])
@pytest.mark.parametrize("value", TOML_LEVELS)
def test_a_codex_mcp_level_that_is_not_a_table_fails_only_its_check(home: Path, level: str, value: str) -> None:
    path = home / ".codex/config.toml"
    quiet(check_after(home, lambda: path.write_text(f"{level} = {value}\n"), CODEX_MCP))


@pytest.mark.parametrize("level", ["mcp_servers", f"mcp_servers.{SERVER}"])
@pytest.mark.parametrize("value", TOML_LEVELS)
def test_a_codex_role_mcp_level_that_is_not_a_table_fails_only_its_check(home: Path, level: str, value: str) -> None:
    quiet(check_after(home, lambda: role(home).write_text(f"{role_head()}{level} = {value}\n"), SCOUT))


@pytest.mark.parametrize("tools", ["[{ name = 1 }]", '[["search_graph"]]', '["search_graph", 1]', '"search_graph"'])
def test_codex_role_tools_that_are_not_names_fail_only_its_check(home: Path, tools: str) -> None:
    def edit() -> None:
        splice(role(home), 'enabled_tools = ["search_graph"]', f"enabled_tools = {tools}")

    quiet(check_after(home, edit, SCOUT))


@pytest.mark.parametrize("level", ["mcp", SERVER])
@pytest.mark.parametrize("value", JSON_LEVELS)
def test_an_opencode_mcp_level_that_is_not_an_object_fails_only_its_check(
    home: Path, level: str, value: object
) -> None:
    path = home / ".config/opencode/opencode.json"
    servers = value if level == "mcp" else {SERVER: value}
    quiet(check_after(home, lambda: path.write_text(json.dumps({"mcp": servers})), OPENCODE_MCP))


def test_malformed_entries_beside_the_cbm_entries_do_not_hide_them(home: Path) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0

    def claude_hooks(value: dict[str, Any]) -> None:
        hooks = value["hooks"]
        for groups in hooks.values():
            groups[:0] = MALFORMED_GROUPS
        hooks["Stop"] = 4

    def claude_servers(value: dict[str, Any]) -> None:
        value["mcpServers"] |= {"other": 4, "listed": [1], "text": "x", "none": None}

    edit_json(settings(home), claude_hooks)()
    edit_json(home / ".claude.json", claude_servers)()
    # The installer splices its entry into the text, trailing comma and all (stand-in, after cli.c:4091-4094), so
    # the other entries are spliced in the same way.
    opencode = home / ".config/opencode/opencode.json"
    others = '"other": 4, "listed": [1], "none": null, '
    splice(opencode, '{"mcp": {', '{"mcp": {' + others)
    config = home / ".codex/config.toml"
    config.write_text('[mcp_servers]\nother = 4\nlisted = [1]\ntext = "x"\n\n' + config.read_text())
    head = f"[mcp_servers.{SERVER}]"
    splice(role(home), head, f"[mcp_servers]\nother = 4\nlisted = [1]\n\n{head}")
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 0, done.stdout + done.stderr
    quiet(done)
