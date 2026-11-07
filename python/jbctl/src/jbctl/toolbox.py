"""A JetBrains Toolbox install, named by its shell script (clion, pycharm, clion1), to the running IDE."""

# Toolbox has no CLI or query API for its installs: its MCP server is a hub for MCP servers the user adds, and
# its station socket serves registered IDEs. It publishes state.json and one channel file per install, neither
# documented (read as Toolbox 3.9.1 writes them). Every IntelliJ-based product has the same shape.

import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from . import mcp, station
from .ide import IdeError, helper_timeout
from .models import Install

# JBCTL_TOOLBOX replaces this, for a stand-in Toolbox.
TOOLBOX = Path.home() / "Library/Application Support/JetBrains/Toolbox"
STATION = re.compile(r"jb\.station\.ij\.(\d+)\.sock")
# The MCP plugin's default port is 64342 plus an offset for the platform prefix (McpServerSettingsKt.getPortOffset,
# CLion 263.7307.209); a prefix it does not list gets 0, as does "idea", the prefix when none is set.
BASE_PORT = 64342
OFFSETS = {
    "CLion": 20,
    "DataGrip": 60,
    "GoLand": 80,
    "PhpStorm": 100,
    "Python": 120,
    "Rider": 140,
    "Ruby": 160,
    "RustRover": 180,
    "WebStorm": 200,
}
FORCE_PORT = "idea.mcp.server.force.port"


def install(script: str) -> Install:
    """The one install whose Toolbox shell script is `script`.

    state.json is what Toolbox publishes about its installs. It lacks the script name, which is the shell
    extension's `name` in the install's channel file (clion, clion1, clion2); that extension's `baseName` and
    `tool.intelliJProperties.shellScriptName` are the product's (clion for all three).
    """
    root = Path(os.environ.get("JBCTL_TOOLBOX") or TOOLBOX)
    found: dict[str, list[tuple[dict, dict]]] = {}
    for tool in json.loads((root / "state.json").read_text())["tools"]:
        # Tools that are not IntelliJ IDEs (Fleet, dotTrace, Junie CLI) have no product code.
        if tool["productCode"]:
            channel = json.loads((root / "channels" / f"{tool['channelId']}.json").read_text())
            extensions = {extension["type"]: extension for extension in channel["tool"]["extensions"]}
            if "shell" in extensions:
                found.setdefault(extensions["shell"]["name"], []).append((tool, extensions["intellij"]))
    matches = found.get(script, [])
    if len(matches) != 1:
        msg = f"Toolbox has {len(matches)} installs named {script}; its IDEs are {', '.join(sorted(found))}"
        raise IdeError(msg)
    tool, intellij = matches[0]
    app, code, build = Path(tool["installLocation"]), tool["productCode"], tool["buildNumber"]
    # Toolbox's record can lag the app (an update in progress, a hand-moved bundle): the app has the last word.
    info = json.loads((app / "Contents/Resources/product-info.json").read_text())
    if (info["productCode"], info["buildNumber"]) != (code, build):
        says = f"{info['productCode']} {info['buildNumber']}"
        msg = f"{app}: Toolbox records {code} {build}, its product-info.json says {says}"
        raise IdeError(msg)
    default_config = Path(intellij["defaultConfigDirectories"]["idea.config.path"])
    launch = info["launch"][0]
    options = Path(launch["vmOptionsFilePath"])
    # The launcher's order (XPlatLauncher default.rs): the app's own .vmoptions, then one user file (Toolbox's
    # <app>.vmoptions beside the bundle, else <config>/<launcher>.vmoptions), then product-info's arguments.
    # <PRODUCT>_VM_OPTIONS and IJ_JAVA_OPTIONS come from the running IDE's environment, which jbctl cannot see.
    users = [file for file in (app.with_name(f"{app.name}.vmoptions"), default_config / options.name) if file.is_file()]
    lines: list[str] = []
    for file in [app / "Contents/Resources" / options, *users[:1]]:
        lines += [line.strip() for line in file.read_text().splitlines()]
    lines += launch.get("additionalJvmArguments", [])
    properties = dict(line[2:].split("=", 1) for line in lines if line.startswith("-D") and "=" in line)
    # As PathManager reads it: surrounding quotes stripped, a leading ~/ is the home folder, then normalized.
    configured = properties.get("idea.config.path", "").strip('"')
    if configured.startswith("~/"):
        configured = str(Path.home() / configured[2:])
    # A relative path is relative to the IDE's working directory, which jbctl cannot know.
    if configured and not Path(configured).is_absolute():
        msg = f"{app}: idea.config.path {configured!r} is relative; only an absolute or ~/ path can be resolved"
        raise IdeError(msg)
    config = Path(os.path.normpath(configured)) if configured else default_config
    return Install(app=str(app), product_code=code, build=build, config=str(config), properties=properties)


def running(app: Path) -> int:
    """The pid of the IDE running from `app`: the one process with a station socket whose executable is in it.

    The station socket marks an IDE's main process, not its helpers (fsnotifier, `clion stdioMcpServer`); a
    socket file outlives its IDE, so the pid's executable is checked too.
    """
    stations = [found[1] for name in station.folder().iterdir() if (found := STATION.fullmatch(name.name))]
    # One ps for every station: pid and the path each was started from; a pid with no process prints nothing.
    listing = subprocess.run(
        ["ps", "-o", "pid=,comm=", "-p", ",".join(stations) or "0"],
        capture_output=True,
        text=True,
        check=False,
        timeout=helper_timeout(),
    ).stdout
    inside = f"{app.resolve()}/Contents/MacOS/"
    pids = [
        int(pid) for pid, path in (line.split(maxsplit=1) for line in listing.splitlines()) if path.startswith(inside)
    ]
    if len(pids) != 1:
        msg = f"{len(pids)} running IDEs are from {app}; want exactly one"
        raise IdeError(msg)
    return pids[0]


def resolve(script: str) -> tuple[Install, int]:
    """The install --ide names, and the pid of the IDE running from it."""
    found = install(script)
    return found, running(Path(found.app))


def mcp_port(found: Install) -> tuple[int, str]:
    """The port the MCP plugin binds, and where that comes from, in the plugin's order.

    A forced port (-Didea.mcp.server.force.port), else the saved setting (options/mcpServer.xml, written when the
    port is not the default, including when the default was busy at start and the next free one was taken), else
    the default for the platform prefix.
    """
    if forced := found.properties.get(FORCE_PORT):
        return int(forced), FORCE_PORT
    settings = Path(found.config) / "options/mcpServer.xml"
    if settings.exists():
        # The user's own IDE settings file.
        saved = ET.parse(settings).find(".//component[@name='McpServerSettings']/option[@name='mcpServerPort']")  # noqa: S314
        if saved is not None:
            return int(saved.attrib["value"]), str(settings)
    prefix = found.properties.get("idea.platform.prefix", "idea")
    return BASE_PORT + OFFSETS.get(prefix, 0), f"the {prefix} default"


def mcp_url(found: Install, pid: int) -> str:
    """The IDE's own MCP endpoint: the port its settings give, checked to be this pid's and to answer initialize."""
    port, source = mcp_port(found)
    url = f"http://127.0.0.1:{port}/stream"
    # lsof first: only a port this pid holds is sent initialize, never another IDE's. -b -w skips the kernel calls
    # that can block on mounted file systems (2 s instead of 0.06 s here) and their warnings.
    listening = subprocess.run(
        ["lsof", "-nP", "-b", "-w", "-a", "-p", str(pid), f"-iTCP@127.0.0.1:{port}", "-sTCP:LISTEN", "-t"],
        capture_output=True,
        check=False,
        timeout=helper_timeout(),
    )
    if not listening.stdout or not mcp.answers(url):
        msg = f"pid {pid} has no MCP server on port {port} ({source})"
        raise IdeError(msg)
    return url
