"""The command line run in-process, stand-in MCP servers, and a stand-in Toolbox with a stand-in IDE."""

import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from jbctl.cli import main

from .standin import DIRECT, mcp_server

STANDIN = Path(__file__).with_name("standin.py")


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


@pytest.fixture
def via_router() -> Iterator[str]:
    yield from mcp_server(["execute_tool"], sse=True)


@pytest.fixture
def direct() -> Iterator[str]:
    yield from mcp_server(DIRECT, sse=False)


@pytest.fixture
def no_tool_list() -> Iterator[str]:
    """A server that answers initialize but replies to tools/list with a JSON-RPC error."""
    yield from mcp_server(None, sse=False)


def install(root: Path, channel: str, app: Path, script: str | None, product: str | None = "FK") -> None:
    """One install, in the shape Toolbox 3.9.1 writes (only the fields jbctl reads): state.json and its channel."""
    state = root / "state.json"
    tools = json.loads(state.read_text())["tools"] if state.exists() else []
    tool = {"channelId": channel, "installLocation": str(app), "productCode": product, "buildNumber": "263.1.2"}
    state.write_text(json.dumps({"tools": [*tools, tool]}))
    config = {"idea.config.path": str(app.parent / f"{channel}-config")}
    extensions = [{"type": "intellij", "defaultConfigDirectories": config}]
    extensions += [{"type": "shell", "name": script}] if script else []
    (root / "channels" / f"{channel}.json").write_text(json.dumps({"tool": {"extensions": extensions}}))


def product_info(app: Path, *jvm: str) -> None:
    """The app's product-info.json; jvm is its launch entry's additionalJvmArguments."""
    launch = {"vmOptionsFilePath": "../bin/fake.vmoptions", "additionalJvmArguments": list(jvm)}
    info = {"productCode": "FK", "buildNumber": "263.1.2", "launch": [launch]}
    (app / "Contents/Resources/product-info.json").write_text(json.dumps(info))


def settings(config: Path, *options: str) -> None:
    """options/mcpServer.xml as the MCP plugin saves it; each option is name=value."""
    lines = "".join(f'<option name="{o.split("=")[0]}" value="{o.split("=")[1]}" />' for o in options)
    (config / "options").mkdir(parents=True, exist_ok=True)
    (config / "options/mcpServer.xml").write_text(
        f'<application><component name="McpServerSettings">{lines}</component></application>'
    )


# Ide and Start type the start fixture's handle: a running process (subprocess.Popen) and its ports, which no
# JSON Schema can describe, so they are not generated models.
class Ide(NamedTuple):
    process: subprocess.Popen[str]
    # The loopback ports of the listeners asked for, in order.
    ports: list[int]


Start = Callable[..., Ide]


@pytest.fixture
def toolbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A stand-in Toolbox: the install `fake` (fake.app), a second one of the product (fake1), an install with
    no shell script, and a non-IDE tool. Each app's own .vmoptions sets no MCP port."""
    root = tmp_path / "toolbox"
    (root / "channels").mkdir(parents=True)
    for name, script in (("fake", "fake"), ("fake-2", "fake1"), ("bare", None)):
        app = tmp_path / f"{name}.app"
        for folder in ("Resources", "MacOS", "bin"):
            (app / "Contents" / folder).mkdir(parents=True)
        (app / "Contents/bin/fake.vmoptions").write_text("-Xmx2048m\n-Dsun.io.useCanonCaches\n-Dfake.app=1\n")
        product_info(app, "-Didea.platform.prefix=Fake")
        install(root, name, app, script)
    install(root, "profiler", tmp_path / "Profiler.app", "prof", product=None)
    # A channel file Toolbox left behind for a tool it no longer lists: state.json decides.
    (root / "channels" / "gone.json").write_text('{"tool": {"extensions": [{"type": "shell", "name": "gone"}]}}')
    monkeypatch.setenv("JBCTL_TOOLBOX", str(root))
    station = tmp_path / "station"
    station.mkdir()
    # A socket left behind by an IDE that has ended (this pid runs python, not an app), and an unrelated file.
    (station / f"jb.station.ij.{os.getpid()}.sock").touch()
    (station / "jb.station.other").touch()
    monkeypatch.setenv("JBCTL_STATION_DIR", str(station))
    return tmp_path


@pytest.fixture
def start(toolbox: Path) -> Iterator[Start]:
    """Starts a stand-in IDE from fake.app's Contents/MacOS, with its station socket and the listeners asked for."""
    started: list[subprocess.Popen[str]] = []

    def launch(*listeners: str) -> Ide:
        # Resolved, as a real install's path is: the process's path is compared with the app's.
        executable = (toolbox / "fake.app/Contents/MacOS").resolve() / "fake"
        executable.unlink(missing_ok=True)
        executable.symlink_to(sys.executable)
        process = subprocess.Popen(
            [executable, "-I", STANDIN, *listeners], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        started.append(process)
        assert process.stdout
        ports = json.loads(process.stdout.readline())
        (toolbox / "station" / f"jb.station.ij.{process.pid}.sock").touch()
        return Ide(process, ports)

    yield launch
    for process in started:
        process.communicate("")  # closing stdin ends it
