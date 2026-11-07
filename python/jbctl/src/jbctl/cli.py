"""The jbctl command: argv[0] names a generated Command, its generated model parses the rest."""

import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx
import psutil
from pydantic_settings import CliApp, CliSettingsSource

from . import covgate, ide, lifecycle, mcp, rea, toolbox
from .models import (
    Action,
    CheckDirect,
    Command,
    CoverageGate,
    Event,
    Failure,
    Ide,
    Map,
    Options,
    ReaPatch,
    Resolve,
    Restart,
    RouterDirect,
    SettingsGoto,
    SettingsOpen,
    SettingsPress,
    Start,
    Status,
    Stop,
)

OPTIONS: dict[Command, type[Options]] = {
    Command.resolve: Resolve,
    Command.map: Map,
    Command.settings_open: SettingsOpen,
    Command.settings_goto: SettingsGoto,
    Command.settings_press: SettingsPress,
    Command.router_direct: RouterDirect,
    Command.check_direct: CheckDirect,
    Command.rea_patch: ReaPatch,
    Command.coverage_gate: CoverageGate,
    Command.status: Status,
    Command.start: Start,
    Command.stop: Stop,
    Command.restart: Restart,
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


def open_settings(app: Path, pid: int, page: str) -> str:
    """Settings on `page`, whichever route opened it: the breadcrumb says so."""
    window, restored = ide.open_settings(pid, page)
    number = int(window.removeprefix("w-"))
    crumbs = rea.breadcrumb(rea.observe(str(app), pid, number))
    # The station route opens Settings on the page; the menu route opens it on the page it showed last, and a
    # station open can still be landing, which only some headless runs see.
    if crumbs[-1:] != [page]:
        crumbs = rea.goto(str(app), pid, number, page)
    emit(Event(settings_window=window, front_restored=restored, breadcrumb=crumbs))
    return window


def goto(app: Path, pid: int, window: str, page: str) -> None:
    emit(Event(breadcrumb=rea.goto(str(app), pid, int(window.removeprefix("w-")), page)))


def press(pid: int, label: str) -> None:
    ide.jbax("press", str(pid), "--label", label)
    emit(Event(pressed=label))


def check(url: str) -> None:
    """Exit 1 unless the MCP server lists more than the router tool (DIRECT)."""
    tools = mcp.tool_count(url)
    direct = tools > 1
    emit(Event(tools=tools, direct=direct))
    if not direct:
        raise SystemExit(1)


def run(options: Options) -> None:
    """Print one JSON line per completed step; exit 1 when the IDE did not end up as asked."""
    match options:
        case ReaPatch():
            helper = Path(options.helper) if options.helper else rea.installed_helper()
            emit(Event(patch=rea.patch(helper)))
        case CoverageGate():
            result = covgate.check(Path(options.report), Path(options.sources), options.skip, options.minimum)
            emit(Event(coverage=result))
            if result.short:
                raise SystemExit(1)
        case CheckDirect(mcp_url=str() as url):
            check(url)
        case CheckDirect(ide=str() as name):
            check(toolbox.mcp_url(*toolbox.resolve(name)))
        # The schema cannot carry "--ide or --mcp-url": datamodel-codegen turns an anyOf of required fields into a
        # union of two models (CheckDirect1 | CheckDirect2), and CliApp parses one model class per command.
        case CheckDirect():
            msg = "check-direct needs --ide or --mcp-url"
            raise ValueError(msg)
        case Status():
            emit(Event(ides=lifecycle.status(options)))
        case Start() | Stop() | Restart():
            cycle(options)
        case _:
            drive(options)


# EX_TEMPFAIL, as the AgentsView controller uses for STARTUP_PENDING: an IDE is up but not ready yet.
NOT_READY = 75


def cycle(options: Start | Stop | Restart) -> None:
    """One line per IDE; exit 1 when any was refused, else 75 when any runs but was not ready in time."""
    actions = set()
    for result in lifecycle.act(options):
        emit(Event(lifecycle=result))
        actions.add(result.action)
    if Action.refused in actions:
        raise SystemExit(1)
    if actions & {Action.started_not_ready, Action.restarted_not_ready}:
        raise SystemExit(NOT_READY)


def drive(options: Resolve | Map | SettingsOpen | SettingsGoto | SettingsPress | RouterDirect) -> None:
    """The commands that act on the IDE that --ide names (a Toolbox shell-script name)."""
    found, pid = toolbox.resolve(options.ide)
    app = Path(found.app)
    match options:
        case Resolve():
            url = toolbox.mcp_url(found, pid)
            emit(Event(ide=Ide(app=str(app), product_code=found.product_code, build=found.build, pid=pid, mcp_url=url)))
        case Map():
            out = Path(options.out)
            snapshot = rea.observe(str(app), pid, options.window)
            with out.open("x") as file:  # never overwrite an earlier map
                json.dump(snapshot, file, indent=1)
            emit(Event(map=str(out), nodes=len(snapshot["nodes"])))
        case SettingsOpen():
            open_settings(app, pid, options.page)
        case SettingsGoto():
            goto(app, pid, ide.own_settings(pid), options.page)
        case SettingsPress():
            ide.own_settings(pid)
            press(pid, options.label)
        case _:  # RouterDirect, the one model left
            open_settings(app, pid, "Exposed Tools")
            ide.jbax("select", str(pid), "--label", ROUTER_MODE, "--row", DIRECT)
            emit(Event(selected=DIRECT))
            # OK, not Apply: Apply's enabled state is not refreshed while the IDE is inactive.
            press(pid, "OK")
            check(options.mcp_url or toolbox.mcp_url(found, pid))


def main(argv: Sequence[str] | None = None) -> None:
    try:
        run(parse(sys.argv[1:] if argv is None else argv))
    except subprocess.CalledProcessError as error:
        sys.stderr.write(Failure(error=f"{error.cmd[0]} failed: {error.stderr}").model_dump_json() + "\n")
        raise SystemExit(1) from None
    except subprocess.TimeoutExpired as error:
        # Not the command: its arguments, and JBAX's path, carry text from outside.
        failure = Failure(error=f"a helper did not answer within {error.timeout:g} s")
        sys.stderr.write(failure.model_dump_json() + "\n")
        raise SystemExit(1) from None
    # IdeError: the IDE is not in a state the step can act on. ValueError: pydantic's and json's errors.
    # OSError: an unreadable helper or an existing map file. httpx.HTTPError: an unreachable station or MCP
    # endpoint. psutil.Error: a process that ended or is not this user's while jbctl read it.
    except (ide.IdeError, ValueError, OSError, httpx.HTTPError, psutil.Error) as error:
        sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
