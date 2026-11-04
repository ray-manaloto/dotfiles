"""The clion-ctl command: argv[0] names a generated Command, its generated model parses the rest."""

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import anyio
from pydantic import BaseModel
from pydantic_settings import CliApp, CliSettingsSource

from .models import Command, Done, Event, Failure, Ide, Options, Reason, Restart, Start, Status, Stop
from .station import Refused, alive, exit_ide, poll, running

OPTIONS: dict[Command, type[Options]] = {
    Command.status: Status,
    Command.start: Start,
    Command.stop: Stop,
    Command.restart: Restart,
}


def parse(argv: Sequence[str]) -> Options:
    if not argv or argv[0] not in set(Command):
        msg = f"clion-ctl: the first argument is one of {', '.join(Command)}"
        raise ValueError(msg)
    command = Command(argv[0])
    model = OPTIONS[command]
    cli = CliSettingsSource(
        # CliApp.run documents BaseModel input; CliSettingsSource's annotation says BaseSettings only.
        model,  # ty: ignore[invalid-argument-type]
        cli_prog_name=f"clion-ctl {command.value}",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_exit_on_error=False,
    )
    return CliApp.run(model, cli_args=list(argv[1:]), cli_settings_source=cli)


def resolved(app: str | None) -> str | None:
    return None if app is None else str(Path(app).resolve())


async def select(pid: int | None, app: str | None) -> Ide:
    """The one running IDE that --pid and --app pick; with neither, the only one running."""
    found = await running()
    chosen = [ide for ide in found if pid in {None, ide.pid} and resolved(app) in {None, ide.app}]
    if not chosen:
        raise Refused(Reason.no_ide, f"no running IDE matches pid {pid} app {app}", pid)
    if len(chosen) > 1:
        pids = ", ".join(f"{ide.pid} ({ide.app})" for ide in chosen)
        raise Refused(Reason.ambiguous, f"several IDEs match, pick one with --pid or --app: {pids}")
    return chosen[0]


async def arrival(app: str | None, before: set[int], port: int | None) -> Ide:
    """A new IDE of app, not among the pids before, that listens on port when one is given."""

    async def check() -> Ide | None:
        return next(
            (ide for ide in await running() if ide.pid not in before and ide.app == app and port in {None, *ide.ports}),
            None,
        )

    return await poll(check)


async def start(options: Start) -> Done:
    app = resolved(options.app)
    if not (Path(options.app).suffix == ".app" and await anyio.Path(options.app).is_dir()):
        raise Refused(Reason.no_app, f"{options.app} is not an .app bundle")
    found = await running()
    # A second launch of a running IDE hands its arguments to the first one and quits, so no new IDE would come.
    if same := [ide.pid for ide in found if ide.app == app]:
        raise Refused(Reason.running, f"{app} already runs as pid {same[0]}", same[0])
    project = ["--args", options.project] if options.project else []
    try:
        await anyio.run_process(["/usr/bin/open", "-n", options.app, *project])
    except subprocess.CalledProcessError as error:
        raise Refused(Reason.no_app, f"open failed: {error.stderr.decode().strip()}") from None
    ide: Ide | None = None
    with anyio.move_on_after(options.timeout):
        ide = await arrival(app, {ide.pid for ide in found}, options.mcp_port)
    if ide is None:
        raise Refused(Reason.not_started, f"{app} did not come up within {options.timeout}s")
    return Done(event=Event.started, pid=ide.pid, previous_pid=None, app=ide.app, ports=ide.ports)


async def stop(options: Stop) -> Done:
    ide = await select(options.pid, options.app)
    await exit_ide(ide, restart=False)

    async def gone() -> bool | None:
        return None if alive(ide.pid) else True

    with anyio.move_on_after(options.timeout) as wait:
        await poll(gone)
    if wait.cancelled_caught:
        raise Refused(Reason.still_running, still(ide.pid, options.timeout), ide.pid)
    return Done(event=Event.stopped, pid=ide.pid, previous_pid=None, app=ide.app, ports=[])


async def restart(options: Restart) -> Done:
    ide = await select(options.pid, options.app)
    before = {other.pid for other in await running()}
    await exit_ide(ide, restart=True)
    new: Ide | None = None
    with anyio.move_on_after(options.timeout):
        new = await arrival(ide.app, before, options.mcp_port)
    if new is None and alive(ide.pid):
        raise Refused(Reason.still_running, still(ide.pid, options.timeout), ide.pid)
    if new is None:
        raise Refused(Reason.not_started, f"pid {ide.pid} ended, no new IDE came up within {options.timeout}s", ide.pid)
    return Done(event=Event.restarted, pid=new.pid, previous_pid=ide.pid, app=new.app, ports=new.ports)


def still(pid: int, timeout: float) -> str:
    return (
        f"pid {pid} still runs after {timeout}s: the IDE may be asking a question (a running process, unsaved "
        "work); answer it in the IDE or wait. Nothing was killed."
    )


async def run(options: Options) -> list[BaseModel]:
    match options:
        case Start():
            return [await start(options)]
        case Stop():
            return [await stop(options)]
        case Restart():
            return [await restart(options)]
        case _:
            return list(await running())


def main(argv: Sequence[str] | None = None) -> None:
    try:
        options = parse(sys.argv[1:] if argv is None else argv)
    # pydantic's errors (ValueError subclasses) for arguments that do not parse.
    except ValueError as error:
        sys.stderr.write(Failure(error=Reason.usage, detail=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
    try:
        lines = anyio.run(run, options)
    except Refused as refused:
        sys.stderr.write(refused.failure.model_dump_json() + "\n")
        raise SystemExit(1) from None
    sys.stdout.writelines(line.model_dump_json() + "\n" for line in lines)
