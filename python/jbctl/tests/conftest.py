"""The command line run in-process, stand-in MCP servers, and a stand-in Toolbox with a stand-in IDE."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import psutil
import pytest

from jbctl.cli import main
from jbctl.mcp import ROUTER

from .standin import CURSOR, DIRECT, mcp_server

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
def unrouted() -> Iterator[str]:
    """DIRECT without the router tool, as a server that never lists execute_tool would answer."""
    yield from mcp_server([tool for tool in DIRECT if tool != ROUTER], sse=False)


@pytest.fixture(params=[(CURSOR, True), ("", False)], ids=["quoted-sse", "empty-json"])
def paged(request: pytest.FixtureRequest) -> Iterator[str]:
    """DIRECT two tools a page, with the router tool alone on the last page. Its cursor holds JSON-significant
    characters, or is empty: a cursor still, since nextCursor is there."""
    cursor, sse = request.param
    yield from mcp_server([*DIRECT[1:], DIRECT[0]], sse=sse, page=2, cursors=[cursor])


@pytest.fixture(params=[{"page": 2}, None], ids=["object", "null"])
def number_cursor(request: pytest.FixtureRequest) -> Iterator[str]:
    """A server whose nextCursor is there but not text, as the protocol says it must be: an object, or null."""
    yield from mcp_server(DIRECT, sse=False, page=2, cursors=[request.param])


@pytest.fixture
def stuck() -> Iterator[str]:
    """A pager, one tool a page, that hands out the same cursor for the second page and the third."""
    yield from mcp_server(DIRECT, sse=False, page=1, cursors=[CURSOR, CURSOR])


@pytest.fixture
def no_tool_list() -> Iterator[str]:
    """A server that answers initialize but replies to tools/list with a JSON-RPC error."""
    yield from mcp_server(None, sse=False)


def install(  # noqa: PLR0913 - one parameter per field a test varies
    root: Path, channel: str, app: Path, script: str | None, product: str | None = "FK", *, tool_id: str = "Fake"
) -> None:
    """One install, in the shape Toolbox 3.9.1 writes (only the fields jbctl reads): state.json and its channel."""
    state = root / "state.json"
    tools = json.loads(state.read_text())["tools"] if state.exists() else []
    tool = {
        "channelId": channel,
        "toolId": tool_id,
        "installLocation": str(app),
        "launchCommand": str(app / "Contents/MacOS/fake"),
        "productCode": product,
        "buildNumber": "263.1.2",
    }
    state.write_text(json.dumps({"tools": [*tools, tool]}))
    config = {"idea.config.path": str(app.parent / f"{channel}-config")}
    extensions = [{"type": "intellij", "defaultConfigDirectories": config}]
    extensions += [{"type": "shell", "name": script}] if script else []
    (root / "channels" / f"{channel}.json").write_text(json.dumps({"tool": {"extensions": extensions}}))


def launcher(app: Path, standin: Path = STANDIN) -> Path:
    """The app's executable, as Toolbox's launchCommand names it: it starts the stand-in IDE under its own name, so
    the process's argv[0] is inside the app as a real IDE's is. The paths are shell-quoted, whatever they hold."""
    path = app / "Contents/MacOS/fake"
    command = f"{shlex.quote(sys.executable)} -I {shlex.quote(str(standin))}"
    path.write_text(f'#!/bin/sh\nSTANDIN_LAUNCH="$0" exec -a "$0" {command} "$@"\n')
    path.chmod(0o755)
    return path


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
def toolbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A stand-in Toolbox: the install `fake` (fake.app), a second one of the product (fake1), an install with
    no shell script, and a non-IDE tool. Each app's own .vmoptions sets no MCP port."""
    root = tmp_path / "toolbox"
    (root / "channels").mkdir(parents=True)
    for name, script in (("fake", "fake"), ("fake-2", "fake1"), ("bare", None)):
        app = tmp_path / f"{name}.app"
        for folder in ("Resources", "MacOS", "bin", "plugins/station-plugin"):
            (app / "Contents" / folder).mkdir(parents=True)
        (app / "Contents/bin/fake.vmoptions").write_text("-Xmx2048m\n-Dsun.io.useCanonCaches\n-Dfake.app=1\n")
        product_info(app, "-Didea.platform.prefix=Fake")
        launcher(app)
        install(root, name, app, script)
    install(root, "profiler", tmp_path / "Profiler.app", "prof", product=None)
    # A channel file Toolbox left behind for a tool it no longer lists: state.json decides.
    (root / "channels" / "gone.json").write_text('{"tool": {"extensions": [{"type": "shell", "name": "gone"}]}}')
    monkeypatch.setenv("JBCTL_TOOLBOX", str(root))
    # A Unix socket's path is at most 104 bytes on macOS, more than a pytest folder leaves room for.
    station = Path(tempfile.mkdtemp(prefix="jbs", dir="/tmp"))
    # A socket left behind by an IDE that has ended (this pid runs python, not an app), and an unrelated file.
    (station / f"jb.station.ij.{os.getpid()}.sock").touch()
    (station / "jb.station.other").touch()
    monkeypatch.setenv("JBCTL_STATION_DIR", str(station))
    # jbctl's lifecycle locks and Settings records, kept out of the user's own state folder.
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    yield tmp_path
    shutil.rmtree(station)
    # Stand-in IDEs that jbctl started or restarted run in their own session until /exit; end any left over.
    for process in psutil.process_iter(["cmdline"]):
        if (process.info["cmdline"] or [""])[0].startswith(str(tmp_path)):
            process.terminate()


@pytest.fixture
def start(toolbox: Path) -> Iterator[Start]:
    """Starts a stand-in IDE from fake.app's Contents/MacOS, with its station socket and the listeners asked for."""
    started: list[subprocess.Popen[str]] = []

    def launch(*flags: str) -> Ide:
        """flags: the stand-in's (--mcp, --http, --stubborn, ...); it ends when the test ends, or on /exit."""
        process = subprocess.Popen(
            [toolbox / "fake.app/Contents/MacOS/fake", "--stdin", *flags],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        started.append(process)
        assert process.stdout
        return Ide(process, json.loads(process.stdout.readline()))

    yield launch
    for process in started:
        process.communicate("")  # closing stdin ends it, if /exit has not
