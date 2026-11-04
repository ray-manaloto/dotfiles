"""The cbm CLI: live install/verify commands and parsed upgrade/accept entry points."""

import argparse
import signal
import sys
from collections.abc import Sequence
from functools import partial
from types import FrameType

from . import config, setup
from .events import emit
from .models import Command, Done, Error, ErrorCode, Outcome, UpgradeStep

SETUP_COMMANDS = (Command.install, Command.verify)


def parse(args: Sequence[str]) -> Command:
    # Keep the original usage event for the existing commands and unknown top-level names.
    usage = f"usage: cbm {{{','.join(SETUP_COMMANDS)}}}"
    if not args or args[0] not in set(Command):
        raise ValueError(usage)
    command = Command(args[0])
    if command in SETUP_COMMANDS:
        if len(args) != 1:
            raise ValueError(usage)
        return command
    parser = argparse.ArgumentParser(
        prog=f"cbm {command}", add_help=False, allow_abbrev=False, exit_on_error=False,
        formatter_class=partial(argparse.HelpFormatter, width=200),
    )  # fmt: skip
    if command is Command.upgrade:
        parser.add_argument("step", nargs="?", choices=list(UpgradeStep))
        parser.add_argument("--candidate")
    else:
        parser.add_argument("change_id")
        parser.add_argument("--reason", required=True)
        parser.add_argument("--public-reason", required=True)
    usage = parser.format_usage().strip()
    try:
        options, remaining = parser.parse_known_args(args[1:])
    except argparse.ArgumentError:
        raise ValueError(usage) from None
    if remaining or (
        command is Command.upgrade and options.candidate is not None and options.step != UpgradeStep.trial
    ):
        raise ValueError(usage)
    return command


def stop(sig: int, _frame: FrameType | None) -> None:
    # Ctrl-C and SIGTERM end through SystemExit, so the launcher is restored (SIGKILL cannot be). A second
    # signal, such as the one mise forwards to the same group, is ignored so it cannot cut the restore short.
    for each in (signal.SIGINT, signal.SIGTERM):
        signal.signal(each, signal.SIG_IGN)
    raise SystemExit(128 + sig)


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        command = parse(args)
    except ValueError as error:
        emit(Error(code=ErrorCode.invalid_usage, message=str(error)))
        raise SystemExit(2) from None
    if command not in SETUP_COMMANDS:
        emit(Error(code=ErrorCode.command_failed, message=f"cbm: {command} is not implemented yet"))
        raise SystemExit(1)
    try:
        cfg = config.load()
    except config.SettingError as error:
        emit(Error(code=ErrorCode.invalid_setting, message=str(error)))
        raise SystemExit(2) from None
    for each in (signal.SIGINT, signal.SIGTERM):
        signal.signal(each, stop)
    failed = 0
    if command is Command.install:
        try:
            failed = setup.install(cfg)
        except setup.InstallError as error:
            emit(Error(code=error.code, message=str(error), path=error.path))
            raise SystemExit(1) from None
    failed += setup.verify(cfg)
    if failed:
        checks = "check" if failed == 1 else "checks"
        message = f"cbm: {command.value} failed: {failed} {checks} failed"
    else:
        message = f"cbm: {command.value} passed"
    emit(Done(command=command, failed=failed, outcome=Outcome.failed if failed else Outcome.done, message=message))
    if failed:
        raise SystemExit(1)
