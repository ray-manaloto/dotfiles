"""The cbm command: `cbm install` runs CBM's installer then verifies; `cbm verify` only verifies."""

import signal
import sys
from collections.abc import Sequence
from types import FrameType

from . import config, setup
from .events import emit
from .models import Command, Done, Error


def stop(sig: int, _frame: FrameType | None) -> None:
    # Ctrl-C and SIGTERM end through SystemExit, so the launcher is restored (SIGKILL cannot be). A second
    # signal, such as the one mise forwards to the same group, is ignored so it cannot cut the restore short.
    for each in (signal.SIGINT, signal.SIGTERM):
        signal.signal(each, signal.SIG_IGN)
    raise SystemExit(128 + sig)


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] not in set(Command):
        emit(Error(message=f"usage: cbm {{{','.join(Command)}}}"))
        raise SystemExit(2)
    command = Command(args[0])
    try:
        cfg = config.load()
    except config.SettingError as error:
        emit(Error(message=str(error)))
        raise SystemExit(2) from None
    for each in (signal.SIGINT, signal.SIGTERM):
        signal.signal(each, stop)
    failed = 0
    if command is Command.install:
        try:
            failed = setup.install(cfg)
        except setup.InstallError as error:
            emit(Error(message=str(error), path=error.path))
            raise SystemExit(1) from None
    failed += setup.verify(cfg)
    emit(Done(command=command, failed=failed))
    if failed:
        raise SystemExit(1)
