"""The jbctl command: argv[0] names a generated Command, its generated model parses the rest."""

import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic_settings import CliApp, CliSettingsSource

from . import ide, mcp, rea
from .models import (
    CheckDirect,
    Command,
    Event,
    Failure,
    Map,
    Options,
    ReaPatch,
    RouterDirect,
    SettingsGoto,
    SettingsOpen,
    SettingsPress,
)

OPTIONS: dict[Command, type[Options]] = {
    Command.map: Map,
    Command.settings_open: SettingsOpen,
    Command.settings_goto: SettingsGoto,
    Command.settings_press: SettingsPress,
    Command.router_direct: RouterDirect,
    Command.check_direct: CheckDirect,
    Command.rea_patch: ReaPatch,
}
ROUTER_MODE = "Enable router-only mode for:"
DIRECT = "ACP agents only"


def parse(argv: Sequence[str]) -> Options:
    if not argv or argv[0] not in set(Command):
        msg = f"jbctl: the first argument is one of {', '.join(Command)}"
        raise ValueError(msg)
    command = Command(argv[0])
    model = OPTIONS[command]
    cli = CliSettingsSource(
        # CliApp.run documents BaseModel input; CliSettingsSource's annotation says BaseSettings only.
        model,  # ty: ignore[invalid-argument-type]
        cli_prog_name=f"jbctl {command.value}",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_exit_on_error=False,
    )
    return CliApp.run(model, cli_args=list(argv[1:]), cli_settings_source=cli)


def emit(event: Event) -> None:
    sys.stdout.write(event.model_dump_json(exclude_none=True) + "\n")


def require_settings(pid: int) -> str:
    window = ide.settings_window(pid)
    if window is None:
        msg = "Settings is not open (jbctl settings-open)"
        raise ide.IdeError(msg)
    return window


def open_settings(pid: int) -> str:
    window, restored = ide.open_settings(pid)
    emit(Event(settings_window=window, front_restored=restored))
    return window


def goto(pid: int, window: str, page: str) -> None:
    emit(Event(breadcrumb=rea.goto(ide.app_path(pid), pid, int(window.removeprefix("w-")), page)))


def press(pid: int, label: str) -> None:
    ide.jbax("press", str(pid), "--label", label)
    emit(Event(pressed=label))


def check(url: str) -> None:
    """Exit 1 unless the MCP server lists more than the router tool (DIRECT)."""
    tools = mcp.tool_count(url)
    emit(Event(tools=tools, direct=tools > 1))
    if tools <= 1:
        raise SystemExit(1)


def run(options: Options) -> None:
    """Print one JSON line per completed step; exit 1 when the IDE did not end up as asked."""
    match options:
        case ReaPatch():
            helper = Path(options.helper) if options.helper else rea.installed_helper()
            emit(Event(patch=rea.patch(helper)))
            return
        case CheckDirect():
            check(options.mcp_url)
            return
    pid = ide.pid()
    match options:
        case Map():
            out = Path(options.out)
            snapshot = rea.observe(ide.app_path(pid), pid, options.window)
            with out.open("x") as file:  # never overwrite an earlier map
                json.dump(snapshot, file, indent=1)
            emit(Event(map=str(out), nodes=len(snapshot["nodes"])))
        case SettingsOpen():
            open_settings(pid)
        case SettingsGoto():
            goto(pid, require_settings(pid), options.page)
        case SettingsPress():
            require_settings(pid)
            press(pid, options.label)
        case RouterDirect():
            window = open_settings(pid)
            goto(pid, window, "Exposed Tools")
            ide.jbax("select", str(pid), "--label", ROUTER_MODE, "--row", DIRECT)
            emit(Event(selected=DIRECT))
            # OK, not Apply: Apply's enabled state is not refreshed while the IDE is inactive.
            press(pid, "OK")
            check(options.mcp_url)


def main(argv: Sequence[str] | None = None) -> None:
    try:
        run(parse(sys.argv[1:] if argv is None else argv))
    except subprocess.CalledProcessError as error:
        sys.stderr.write(Failure(error=f"{error.cmd[0]} failed: {error.stderr}").model_dump_json() + "\n")
        raise SystemExit(1) from None
    # IdeError: the IDE is not in a state the step can act on. ValueError: pydantic's and json's errors.
    # OSError: an unreadable helper, an existing map file, or an unreachable MCP endpoint (URLError).
    except (ide.IdeError, ValueError, OSError) as error:
        sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
