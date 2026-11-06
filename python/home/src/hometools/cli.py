"""The hometools CLI: one command per global toolchain task."""

import argparse
import sys
from collections.abc import Sequence

from . import config, toolchain
from .models import Bootstrap, Command, Failure, Verify


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hometools")
    parser.add_argument("command", type=Command, choices=list(Command))
    command = parser.parse_args(argv).command
    try:
        if command is Command.toolchain_verify:
            toolchain.verify(config.load(Verify))
        else:
            toolchain.bootstrap(config.load(Bootstrap))
    except config.ToolchainError as failed:
        sys.stderr.write(Failure(error=str(failed)).model_dump_json() + "\n")
        raise SystemExit(1) from None
