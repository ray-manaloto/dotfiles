"""The p2996 command: argv[0] names a generated Command, its generated model parses the rest (DL-762).

mise.toml exposes each command as a task with a usage spec; tests/test_usage.py keeps the two in step.
"""

import shutil
import subprocess
import sys
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import anyio
from pydantic import BaseModel
from pydantic_settings import CliApp, CliSettingsSource

from . import build, config, install, review, source, verify
from .log import P2996Error, configure, log
from .models import Build, Clean, Command, Config, Install, ReviewLog, Source, Verify


async def clean(cfg: Config, args: Clean) -> None:
    for path in (config.build_dir(cfg), config.src(cfg)) if args.source else (config.build_dir(cfg),):
        shutil.rmtree(path, ignore_errors=True)
        log.info("removed", path=str(path))


# One entry per generated Command; test_cli checks none is missing.
COMMANDS: dict[Command, tuple[type[BaseModel], Callable[[Config, Any], Awaitable[None]]]] = {
    Command.source: (Source, source.run),
    Command.build: (Build, build.run),
    Command.install: (Install, install.run),
    Command.verify: (Verify, verify.run),
    Command.clean: (Clean, clean),
    Command.review_log: (ReviewLog, review.run),
}


def parse(argv: Sequence[str]) -> tuple[Command, BaseModel]:
    if not argv or argv[0] not in set(Command):
        msg = f"p2996: the first argument is one of {', '.join(Command)}"
        raise P2996Error(msg)
    command = Command(argv[0])
    model = COMMANDS[command][0]
    # CliApp.run documents BaseModel input; CliSettingsSource's annotation says BaseSettings only.
    cli = CliSettingsSource(
        model,  # ty: ignore[invalid-argument-type]
        cli_prog_name=f"p2996 {command}",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_exit_on_error=False,
    )
    return command, CliApp.run(model, cli_args=list(argv[1:]), cli_settings_source=cli)


def main(argv: Sequence[str] | None = None) -> None:
    configure()
    try:
        command, args = parse(sys.argv[1:] if argv is None else argv)
        anyio.run(COMMANDS[command][1], config.load(), args)
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode().strip() if error.stderr else None
        log.error("command failed", command=[str(part) for part in error.cmd], code=error.returncode, stderr=stderr)
        raise SystemExit(1) from None
    except (P2996Error, ValueError) as error:  # ValueError: pydantic's parse and validation errors
        log.error(str(error))
        raise SystemExit(1) from None
