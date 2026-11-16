"""The hometools CLI: one command per global task it does the work of."""

import argparse
import sys
from collections.abc import Sequence

from . import codemode, config, disk, herdr, monit, nativeclaude, opencode, roll, spotlight, toolchain, update
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
    Command.claude_doctor: nativeclaude.main,
    Command.spotlight_check: spotlight.run,
}


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hometools")
    parser.add_argument("command", type=Command, choices=list(Command))
    # Everything after the command, --help included, however the command was spelled (hometools -- roll ...): roll and
    # claude-code-mode hand it to their own parsers; every other command takes none.
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command
    if command is Command.roll:
        raise SystemExit(roll.main(args.rest))
    if command is Command.claude_code_mode:
        codemode.main(args.rest)  # replaces this process with claude, or exits with one Failure event
    if args.rest:
        parser.error(f"unrecognized arguments: {' '.join(args.rest)}")
    if command in UPDATES:
        UPDATES[command]()
        return
    toolchains = {
        Command.toolchain_verify: lambda: toolchain.verify(config.load(Verify)),
        Command.bootstrap_toolchain: lambda: toolchain.bootstrap(config.load(Bootstrap)),
    }
    try:
        toolchains[command]()
    except config.ToolchainError as failed:
        sys.stderr.write(Failure(error=str(failed)).model_dump_json() + "\n")
        raise SystemExit(1) from None
