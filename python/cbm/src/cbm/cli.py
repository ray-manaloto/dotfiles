"""The cbm CLI: install and verify the live agent setup."""

import signal
import sys
from collections.abc import Sequence
from types import FrameType

from . import checkout, config, setup
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


def report_install_refusal(message: str, *, interrupted: bool = False) -> None:
    emit(Error(code=ErrorCode.install_checkout_refused, message=message))
    result = "interrupted" if interrupted else "failed"
    emit(Done(command=Command.install, failed=1, outcome=Outcome.failed,
              message=f"cbm: install refused: checkout check {result}"))  # fmt: skip


def check_install_checkout() -> None:
    try:
        message = checkout.install_refusal()
    except SystemExit:  # A signal's SystemExit reaches here after subprocess.run cleans up its child.
        report_install_refusal("cbm: git checkout discovery interrupted", interrupted=True)
        raise
    if message:
        report_install_refusal(message)
        raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        command = parse(args)
    except ValueError as error:
        emit(Error(code=ErrorCode.invalid_usage, message=str(error)))
        raise SystemExit(2) from None
    for each in (signal.SIGINT, signal.SIGTERM):
        signal.signal(each, stop)
    try:
        if command is Command.install:
            check_install_checkout()
        cfg = config.load()
    except config.SettingError as error:
        emit(Error(code=ErrorCode.invalid_setting, message=str(error)))
        raise SystemExit(2) from None
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
