"""The hometools CLI: one command per global task it does the work of."""

import argparse
import sys
from collections.abc import Sequence

from . import config, disk, herdr, secret, toolchain, update
from .models import Bootstrap, Command, Failure, Verify

# These end a failure with one Failure event, as the rest do, and keep their shell tasks' exit codes; herdr-doctor
# reports each input it could not read as unknown in its own JSON line and exits with its checks' code.
UPDATES = {
    Command.update_brew: update.brew,
    Command.update_check: update.check,
    Command.herdr_doctor: herdr.doctor,
    Command.disk_watch: disk.main,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hometools")
    parser.add_argument("command", type=Command, choices=list(Command))
    # secret-set's NAME, the one command that takes an argument.
    parser.add_argument("name", nargs="?")
    args = parser.parse_args(argv)
    command = args.command
    if (command is Command.secret_set) != (args.name is not None):
        parser.error("secret-set takes one NAME; the other commands take none")
    if command is Command.secret_set:
        secret.set_secret(args.name)
        return
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
