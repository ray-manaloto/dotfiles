"""The cbm CLI: install and verify the live agent setup."""

import signal
import sys
from collections.abc import Sequence
from types import FrameType

from . import config, setup
from .events import emit
from .models import Command, Done, Error, ErrorCode, Outcome


def parse(args: Sequence[str]) -> Command:
    if len(args) != 1 or args[0] not in set(Command):
        msg = f"usage: cbm {{{','.join(Command)}}}"
        raise ValueError(msg)
    return Command(args[0])


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
