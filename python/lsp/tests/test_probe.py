"""health, smoke, verify and doctor: the real servers started the way their plugins start them."""

import asyncio
import os
import shutil
import subprocess
import sys
import unicodedata
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

from lsptools import actions, probe

from .conftest import Lsp, World, needs_brew

SLEEPER = {"typescript": {"command": "sleep", "args": ["600"], "extensionToLanguage": {".ts": "typescript"}}}
EXITS = Path(__file__).with_name("exits_on_shutdown.py")


def names(result: dict[str, Any]) -> list[tuple[str, bool]]:
    (report,) = result["reports"]
    return [(check["name"], check["ok"]) for check in report["checks"]]


def test_smoke_asks_tsc_about_the_fixture(world: World, lsp: Lsp) -> None:
    world.dotfiles()
    result = lsp("smoke", "typescript")
    assert result.code == 0, result.out
    lines = result.out.splitlines()
    assert lines[3].startswith("  ok  initialize: typescript-go ")
    assert lines[3].endswith("/tsc --lsp --stdio")
    assert lines[4:] == [
        "  ok  documentSymbol: greet",
        "  ok  hover: function greet(name: string): string",
        "  ok  definition: 1 location(s)",
        "  ok  references: 3 in a.ts, b.ts",
        "  ok  shutdown: clean",
    ]


def test_health_only_initializes(world: World, lsp: Lsp) -> None:
    world.dotfiles()
    result = lsp("health", "typescript", "--json")
    assert result.code == 0
    assert names(result.json()) == [("plugin", True), ("command", True), ("initialize", True), ("shutdown", True)]


def test_a_server_that_dies_on_shutdown_is_noted_not_failed(world: World, lsp: Lsp) -> None:
    server = {"command": sys.executable, "args": [str(EXITS)], "extensionToLanguage": {".ts": "typescript"}}
    world.market("dotfiles", {"typescript-native-lsp": {"lsp": {"typescript": server}}})
    result = lsp("health", "typescript")
    assert result.code == 0, result.out
    last = result.out.splitlines()[-1]
    assert last.startswith("  ok  shutdown: not clean: Server process ")
    assert last.endswith("exited with return code: 2; stderr: panic: assignment to entry in nil map")


@pytest.mark.usefixtures("world")
def test_health_without_the_plugin_starts_nothing(lsp: Lsp) -> None:
    result = lsp("health", "typescript", "--json")
    assert result.code == 1
    assert names(result.json()) == [("plugin", False)]


def test_a_server_that_exits_is_reported_with_its_stderr(world: World, lsp: Lsp) -> None:
    world.dotfiles()
    world.monkeypatch.delenv("TS_LSP_TSC")
    result = lsp("health", "typescript")
    assert result.code == 1
    (line,) = [line for line in result.out.splitlines() if "server:" in line]
    assert line.startswith("  FAIL  server: Server process ")
    assert line.endswith(
        "exited with return code: 1; stderr: typescript-native-lsp: TS_LSP_TSC is unset or not executable; it comes "
        "from the global mise config, so start Claude Code from a shell where mise is active"
    )


def test_a_server_that_never_answers_is_killed(world: World, lsp: Lsp) -> None:
    world.market("dotfiles", {"typescript-native-lsp": {"lsp": SLEEPER}})
    world.monkeypatch.setenv("LSPTOOLS_REQUEST_SECONDS", "2")
    result = lsp("health", "typescript")
    assert result.code == 1
    assert result.out.splitlines()[-1] == "  FAIL  server: no answer within 2 s; stderr: nothing on stderr"
    table = subprocess.run(["ps", "-A", "-o", "ppid=,command="], capture_output=True, text=True, check=True).stdout
    assert not [row for row in table.splitlines() if row.split(None, 1) == [str(os.getpid()), "sleep 600"]]


def test_verify_fails_when_another_plugin_claims_an_extension(world: World, lsp: Lsp) -> None:
    world.dotfiles()
    world.market("tests", {"also-ts": {"lsp": {"ts": {"command": "x", "extensionToLanguage": {".ts": "typescript"}}}}})
    result = lsp("verify", "typescript")
    assert result.code == 1
    assert "  FAIL  owner .ts: also-ts@tests" in result.out
    assert "  ok  owner .tsx: typescript-native-lsp@dotfiles" in result.out
    assert "  ok  references: 3 in a.ts, b.ts" in result.out


@needs_brew
def test_doctor_verifies_every_server(world: World, lsp: Lsp) -> None:
    world.dotfiles()
    result = lsp("doctor", "--json").json()
    assert result["ok"] is False
    typescript, clangd = result["reports"]
    assert (typescript["server"], typescript["ok"]) == ("typescript", True)
    assert (clangd["server"], clangd["ok"]) == ("clangd", False)
    assert ("plugin", False) in [(check["name"], check["ok"]) for check in clangd["checks"]]


@pytest.mark.skipif(shutil.which("clangd") is None, reason="clangd comes from mise bootstrap's brew:llvm")
def test_the_cpp_fixture_answers_clangd(tmp_path: Path) -> None:
    """The clangd plugin comes from claude-plugins-official, a name only Anthropic's GitHub marketplace may take, so a
    scratch Claude Code config can't install it: this asks clangd itself about the fixture smoke opens."""
    clangd = actions.find("clangd")
    shutil.copytree(str(resources.files("lsptools").joinpath("fixtures", clangd.fixture)), tmp_path, dirs_exist_ok=True)
    # The plugin starts clangd with --background-index (its marketplace entry).
    checks = asyncio.run(probe.session(["clangd", "--background-index"], tmp_path, clangd.probe))
    assert [(check.name, check.ok) for check in checks] == [
        ("initialize", True),
        ("documentSymbol", True),
        ("hover", True),
        ("definition", True),
        ("references", True),
        ("shutdown", True),
    ]
    assert checks[-2].detail.endswith(" in greet.hpp, main.cpp")


def test_a_command_not_on_path_is_not_started(world: World, lsp: Lsp) -> None:
    missing = {"typescript": {"command": "no-such-lsp-server", "extensionToLanguage": {".ts": "typescript"}}}
    world.market("dotfiles", {"typescript-native-lsp": {"lsp": missing}})
    health = lsp("health", "typescript", "--json")
    assert health.code == 1
    assert names(health.json()) == [("plugin", True), ("command", False)]
    verify = lsp("verify", "typescript", "--json")
    assert verify.code == 1
    assert names(verify.json()) == [("mise", True), ("plugin", True), ("command", False), ("owner .ts", True)]


def test_text_output_shows_a_servers_control_characters_inert(world: World, lsp: Lsp) -> None:
    said = r"printf '\033]0;x\007boom\nmore' >&2; exit 1"
    server = {"command": "sh", "args": ["-c", said], "extensionToLanguage": {".ts": "typescript"}}
    world.market("dotfiles", {"typescript-native-lsp": {"lsp": {"typescript": server}}})
    result = lsp("health", "typescript")
    assert result.code == 1
    assert len(result.out.splitlines()) == 1 + len(names(lsp("health", "typescript", "--json").json()))
    assert not [char for char in result.out if unicodedata.category(char) == "Cc" and char != "\n"]
    assert result.out.splitlines()[-1].endswith(r"exited with return code: 1; stderr: \x1b]0;x\x07boom more")
