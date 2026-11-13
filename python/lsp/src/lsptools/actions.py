"""Each mise run lsp action: native mise and claude commands do the work, and every finding is a named Check."""

import asyncio
import shutil
import tempfile
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from . import probe, tools
from .models import Action, Check, PluginServer, Registry, Report, Reports, Server, Source

# A server as its plugin declares it, and the plugin's install folder its ${CLAUDE_PLUGIN_ROOT} stands for.
type Declared = tuple[PluginServer, Path]


def registry() -> Registry:
    return Registry.model_validate_json(resources.files("lsptools").joinpath("servers.json").read_text())


def find(name: str) -> Server:
    for server in registry().servers:
        if server.name == name:
            return server
    known = ", ".join(server.name for server in registry().servers)
    msg = f"no language server {name!r} in lsptools/servers.json (known: {known})"
    raise ValueError(msg)


def report(action: Action, server: Server, checks: list[Check]) -> Report:
    return Report(action=action, server=server.name, ok=all(check.ok for check in checks), checks=checks)


def installed(server: Server) -> Check:
    """mise installs it: a global [tools] entry, or a [bootstrap.packages] entry in the installed state."""
    if server.source is Source.tool:
        tool = tools.global_tool(server.package)
        if tool is None:
            return Check(name="mise", ok=False, detail=f"{server.package} is not an installed global mise tool")
        return Check(name="mise", ok=True, detail=f"{server.package} {tool['version']} at {tool['install_path']}")
    package = tools.bootstrap_package(server.package)
    if package is None or package.get("state") != "installed":
        state = package.get("state") if package else "not declared"
        return Check(name="mise", ok=False, detail=f"{server.package} in [bootstrap.packages]: {state}")
    return Check(name="mise", ok=True, detail=f"{server.package} {package['installed_version']} (mise bootstrap)")


def configured(server: Server) -> tuple[list[Check], Declared | None]:
    """Claude Code runs it: the plugin is enabled and declares the server; the declaration when it does."""
    entry = tools.plugin_entry(tools.plugins(), server.plugin)
    if entry is None:
        return [Check(name="plugin", ok=False, detail=f"{server.plugin} is not installed")], None
    enabled = Check(name="plugin", ok=entry.get("enabled") is True, detail=f"{server.plugin} ({entry.get('scope')})")
    declared = tools.servers_of(entry).get(server.name)
    if declared is None:
        return [enabled, Check(name="lspServers", ok=False, detail=f"{server.plugin} declares no {server.name}")], None
    root = Path(str(entry["installPath"]))
    argv = probe.command_of(declared, root)
    resolved = shutil.which(argv[0])
    found = Check(name="command", ok=resolved is not None, detail=f"{' '.join(argv)} ({resolved or 'not on PATH'})")
    return [enabled, found], (declared, root)


def status(server: Server) -> Report:
    checks, _ = configured(server)
    return report(Action.status, server, [installed(server), *checks])


def which(server: Server) -> Report:
    """The chain Claude Code follows: plugin, command, the binary it resolves to, and the mise install behind it."""
    checks, declared = configured(server)
    if declared is not None:
        extensions = ", ".join(sorted(declared[0].extension_to_language))
        checks.append(Check(name="extensions", ok=True, detail=extensions))
    return report(Action.which, server, [*checks, installed(server)])


def has_update(server: Server) -> Report:
    newer = (tools.tool_update if server.source is Source.tool else tools.bootstrap_update)(server.package)
    detail = f"{server.package} can move to {newer}" if newer else f"{server.package} is current"
    # ok means "nothing to do", so a scheduled check fails exactly when an update is waiting.
    return report(Action.has_update, server, [Check(name="update", ok=newer is None, detail=detail)])


def probed(server: Server, *, smoke: bool) -> list[Check]:
    checks, declared = configured(server)
    # No declaration, or a command that is not on PATH (configured's last check): there is nothing to start.
    if declared is None or not checks[-1].ok:
        return checks
    folder = Path(tempfile.mkdtemp(prefix=f"lsp-{server.name}-"))
    try:
        fixture = resources.files("lsptools").joinpath("fixtures", server.fixture)
        shutil.copytree(str(fixture), folder, dirs_exist_ok=True)
        argv = probe.command_of(*declared)
        return [*checks, *asyncio.run(probe.session(argv, folder, server.probe if smoke else None))]
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def health(server: Server) -> Report:
    return report(Action.health, server, probed(server, smoke=False))


def smoke(server: Server) -> Report:
    return report(Action.smoke, server, probed(server, smoke=True))


def claims() -> dict[str, list[str]]:
    """Each file extension and the enabled plugins whose language servers claim it."""
    found: dict[str, set[str]] = {}
    for entry in tools.plugins():
        if entry.get("enabled") is not True:
            continue
        for declared in tools.servers_of(entry).values():
            for extension in declared.extension_to_language:
                found.setdefault(extension, set()).add(str(entry["id"]))
    return {extension: sorted(owners) for extension, owners in found.items()}


def conflicts() -> Reports:
    """Two enabled plugins claiming one extension: Claude Code then picks one of them silently."""
    checks = [
        Check(name=extension, ok=len(owners) == 1, detail=", ".join(owners))
        for extension, owners in sorted(claims().items())
    ]
    one = Report(action=Action.conflicts, server="*", ok=all(check.ok for check in checks), checks=checks)
    return Reports(action=Action.conflicts, ok=one.ok, reports=[one])


def verify(server: Server) -> Report:
    """Everything: installed by mise, run by an enabled plugin, the only owner of its extensions, and smoke passes."""
    checks = [installed(server), *probed(server, smoke=True)]
    _, declared = configured(server)
    owners = claims()
    for extension in declared[0].extension_to_language if declared else {}:
        others = [owner for owner in owners.get(extension, []) if owner != server.plugin]
        checks.append(Check(name=f"owner {extension}", ok=not others, detail=", ".join(others) or server.plugin))
    return report(Action.verify, server, checks)


def doctor() -> Reports:
    reports = [verify(server) for server in registry().servers]
    return Reports(action=Action.doctor, ok=all(each.ok for each in reports), reports=reports)


def mise_write(server: Server, argv: list[str], config: Path) -> Check:
    """One mise command against the worktree's global config, never the live one."""
    code, out, err = tools.run(argv, {"MISE_GLOBAL_CONFIG_FILE": str(config)})
    last = ((err or out).strip().splitlines() or ["done"])[-1]
    return Check(name=" ".join(argv[:3]), ok=code == 0, detail=f"{server.package}: {last}")


def change(action: Action, server: Server, start: Path) -> Report:
    """add, update or remove: the pin and its lock line in the worktree, then the plugin in Claude Code."""
    if server.source is Source.bootstrap:
        msg = f"{server.package} is a [bootstrap.packages] entry: change it with mise bootstrap packages"
        raise ValueError(msg)
    config = tools.write_target(start)
    steps: dict[Action, list[list[str]]] = {
        Action.add: [["mise", "use", "-g", f"{server.package}@latest"], ["mise", "lock", "--global", server.package]],
        Action.update: [["mise", "upgrade", "--bump", server.package], ["mise", "lock", "--global", server.package]],
        Action.remove: [["mise", "unuse", "-g", "--no-prune", server.package]],
    }
    checks = [mise_write(server, argv, config) for argv in steps[action]]
    if not all(check.ok for check in checks):
        skipped = Check(name="plugin", ok=False, detail=f"{server.plugin} not changed: a mise step failed")
        return report(action, server, [*checks, skipped])
    plugin: Callable[[], Check] = {
        Action.add: lambda: enable(server),
        Action.update: lambda: Check(name="plugin", ok=True, detail=f"{server.plugin} unchanged"),
        Action.remove: lambda: disable(server),
    }[action]
    return report(action, server, [*checks, plugin()])


def enable(server: Server) -> Check:
    entry = tools.plugin_entry(tools.plugins(), server.plugin)
    verb = "install" if entry is None else "enable"
    if entry is not None and entry.get("enabled") is True:
        return Check(name="plugin", ok=True, detail=f"{server.plugin} already enabled")
    code, out, err = tools.run(["claude", "plugin", verb, server.plugin, "--scope", "user"])
    undo = "uninstall" if verb == "install" else "disable"
    detail = f"{verb}: {last_line(err or out)}; undo: claude plugin {undo} {server.plugin}"
    return Check(name="plugin", ok=code == 0, detail=detail)


def disable(server: Server) -> Check:
    code, out, err = tools.run(["claude", "plugin", "disable", server.plugin, "--scope", "user"])
    detail = f"disable: {last_line(err or out)}; undo: claude plugin enable {server.plugin}"
    return Check(name="plugin", ok=code == 0, detail=detail)


def last_line(said: str) -> str:
    return (said.strip().splitlines() or ["no output"])[-1]
