"""A JetBrains Toolbox install, named by its shell script (clion, pycharm, clion1), to the running IDE."""

# Toolbox has no CLI or query API for its installs: its MCP server is a hub for MCP servers the user adds, and
# its station socket serves registered IDEs. It publishes state.json and one channel file per install, neither
# documented (read as Toolbox 3.9.1 writes them). Every IntelliJ-based product has the same shape.

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import psutil

from . import mcp, station
from .ide import IdeError
from .models import Install, Lifetime

# JBCTL_TOOLBOX replaces this, for a stand-in Toolbox.
TOOLBOX = Path.home() / "Library/Application Support/JetBrains/Toolbox"
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
FORCE_ENABLE = "idea.mcp.server.force.enable"


def entries() -> dict[str, list[tuple[dict[str, Any], dict[str, Any]]]]:
    """Toolbox's IDE installs by shell-script name, each as its state.json record and its intellij extension.

    state.json is what Toolbox publishes about its installs. It lacks the script name, which is the shell
    extension's `name` in the install's channel file (clion, clion1, clion2); that extension's `baseName` and
    `tool.intelliJProperties.shellScriptName` are the product's (clion for all three).
    """
    root = Path(os.environ.get("JBCTL_TOOLBOX") or TOOLBOX)
    found: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for tool in json.loads((root / "state.json").read_text())["tools"]:
        # Tools that are not IntelliJ IDEs (Fleet, dotTrace, Junie CLI) have no product code, and an IDE without the
        # station plugin (Android Studio) has no socket to reach it through.
        if tool["productCode"] and (Path(tool["installLocation"]) / "Contents/plugins/station-plugin").is_dir():
            channel = json.loads((root / "channels" / f"{tool['channelId']}.json").read_text())
            extensions = {extension["type"]: extension for extension in channel["tool"]["extensions"]}
            if "shell" in extensions:
                found.setdefault(extensions["shell"]["name"], []).append((tool, extensions["intellij"]))
    return found


def installs() -> list[Install]:
    """Every Toolbox IDE: an install with a product code and a shell script, by script name."""
    return [read(script, *matches[0]) for script, matches in sorted(entries().items()) if len(matches) == 1]


def install(script: str) -> Install:
    """The one install whose Toolbox shell script is `script`."""
    found = entries()
    matches = found.get(script, [])
    if len(matches) != 1:
        msg = f"Toolbox has {len(matches)} installs named {script}; its IDEs are {', '.join(sorted(found))}"
        raise IdeError(msg)
    return read(script, *matches[0])


def read(script: str, tool: dict[str, Any], intellij: dict[str, Any]) -> Install:
    """An install as its app has it: Toolbox's record, checked against product-info.json and the launcher's options."""
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
    return Install(
        script=script,
        tool_id=tool["toolId"],
        launch=tool["launchCommand"],
        app=str(app),
        product_code=code,
        build=build,
        config=str(config),
        properties=properties,
    )


def lifetimes(app: Path) -> list[Lifetime]:
    """The IDEs running from `app`: processes of this user that own a station socket, started from inside the app.

    The station socket marks an IDE's main process, not its helpers (fsnotifier, `clion stdioMcpServer`). A socket
    file outlives its IDE and its pid can be reused, so the process must have the socket open, as clion-ctl
    checked it.
    """
    inside = f"{app.resolve()}/Contents/MacOS/"
    found: list[Lifetime] = []
    for pid, socket in station.sockets().items():
        info = snapshot(pid, "cmdline", "uids", "create_time")
        # Gone (a socket file left behind), another user's process that reused the pid (its connections would be
        # AccessDenied), or started from elsewhere. argv[0] is the path it was started as, which may go through a
        # symlink (/tmp, a linked Applications folder), so its real path is compared.
        argv, uids = (info or {}).get("cmdline") or [], (info or {}).get("uids")
        if not (info and uids and uids.real == os.getuid() and argv and os.path.realpath(argv[0]).startswith(inside)):
            continue
        if str(socket) in {connection.laddr for connection in psutil.Process(pid).net_connections("unix")}:
            found.append(Lifetime(pid=pid, created=info["create_time"], socket=str(socket)))
    return found


def snapshot(pid: int, *attrs: str) -> dict[str, Any] | None:
    """A process's attributes (None for one it may not read), or None when the process ended while it was read.

    psutil reports a process that ends mid-read as NoSuchProcess, and psutil 7.2.2 on Python 3.15 sometimes as a
    SystemError from its C code (proc_cmdline, seen in a live run while other processes exited): either way the
    process is not running, which is what callers ask.
    """
    try:
        return psutil.Process(pid).as_dict(list(attrs), ad_value=None)
    except psutil.NoSuchProcess:
        return None
    except SystemError as error:
        # Only psutil's proc_cmdline failure, and only for a process that has in fact gone; anything else propagates.
        if "proc_cmdline" in str(error) and not psutil.pid_exists(pid):
            return None
        raise


def running(app: Path) -> int:
    """The pid of the one IDE running from `app`."""
    pids = [lifetime.pid for lifetime in lifetimes(app)]
    if len(pids) != 1:
        msg = f"{len(pids)} running IDEs are from {app}; want exactly one"
        raise IdeError(msg)
    return pids[0]


def listening(pid: int) -> set[int]:
    """The TCP ports the process listens on."""
    connections = psutil.Process(pid).net_connections("tcp")
    return {connection.laddr.port for connection in connections if connection.status == psutil.CONN_LISTEN}


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


def mcp_enabled(found: Install) -> bool:
    """Whether the IDE's MCP server is turned on, as the plugin decides: -Didea.mcp.server.force.enable=true (any
    case), or enableMcpServer in options/mcpServer.xml, off until it is saved on."""
    if found.properties.get(FORCE_ENABLE, "").lower() == "true":
        return True
    settings = Path(found.config) / "options/mcpServer.xml"
    if not settings.exists():
        return False
    # The user's own IDE settings file.
    saved = ET.parse(settings).find(".//component[@name='McpServerSettings']/option[@name='enableMcpServer']")  # noqa: S314
    return saved is not None and saved.attrib.get("value") == "true"


def mcp_answers(pid: int, port: int) -> bool:
    """Whether pid holds the port and an MCP server answers initialize there: only its own port is asked."""
    return port in listening(pid) and mcp.answers(f"http://127.0.0.1:{port}/stream")


def mcp_url(found: Install, pid: int) -> str:
    """The IDE's own MCP endpoint: the port its settings give, checked to be this pid's and to answer initialize."""
    port, source = mcp_port(found)
    if not mcp_answers(pid, port):
        msg = f"pid {pid} has no MCP server on port {port} ({source})"
        raise IdeError(msg)
    return f"http://127.0.0.1:{port}/stream"
