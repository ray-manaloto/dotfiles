"""The hometools CLI: one command per global task it does the work of."""

import argparse
import sys
from collections.abc import Sequence

from . import config, disk, herdr, monit, opencode, toolchain, update
from .models import Bootstrap, Command, Failure, Verify

# These end a failure with one Failure event, as the rest do, and keep their shell tasks' exit codes; herdr-doctor
# reports each input it could not read as unknown in its own JSON line and exits with its checks' code.
UPDATES = {
    Command.update_brew: update.brew,
    Command.update_check: update.check,
    Command.herdr_doctor: herdr.doctor,
    Command.opencode_jouet: opencode.sync,
    Command.disk_snapshot: disk.run_snapshot,
    Command.disk_guard: disk.run_guard,
    Command.disk_log: disk.run_log,
    Command.monit_alert: monit.run_alert,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hometools")
    parser.add_argument("command", type=Command, choices=list(Command))
    args = parser.parse_args(argv)
    command = args.command
    if command in UPDATES:
        UPDATES[command]()
        return
    try:
        if command is Command.toolchain_verify:
            toolchain.verify(config.load(Verify))
        else:
            toolchain.bootstrap(config.load(Bootstrap))
    except config.ToolchainError as failed:
        sys.stderr.write(Failure(error=str(failed)).model_dump_json() + "\n")
        raise SystemExit(1) from None
