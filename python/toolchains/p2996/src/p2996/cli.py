"""The p2996 command; mise.toml exposes each subcommand as a task with a usage spec."""

import argparse
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path

from . import build, config, install, review, source, verify
from .models import Command, Config


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="p2996")
    sub = top.add_subparsers(dest="command", required=True)
    sub.add_parser(Command.source).add_argument("--commit", help="build this commit, not the newest on P2996_BRANCH")
    sub.add_parser(Command.build).add_argument("--dry-run", action="store_true", help="print the cmake commands only")
    sub.add_parser(Command.install)
    sub.add_parser(Command.verify)
    sub.add_parser(Command.clean).add_argument("--source", action="store_true", help="also delete the checkout")
    review_log = sub.add_parser(Command.review_log)
    review_log.add_argument("log", type=Path)
    review_log.add_argument("--out", type=Path)
    return top


def clean(cfg: Config, *, with_source: bool) -> None:
    for path in (config.build_dir(cfg), config.src(cfg)) if with_source else (config.build_dir(cfg),):
        shutil.rmtree(path, ignore_errors=True)
        print(f"p2996 clean: removed {path}")


# One entry per generated Command; test_cli checks none is missing.
RUN: dict[Command, Callable[[Config, argparse.Namespace], None]] = {
    Command.source: lambda cfg, args: source.run(cfg, args.commit),
    Command.build: lambda cfg, args: build.run(cfg, dry_run=args.dry_run),
    Command.install: lambda cfg, _: install.run(cfg),
    Command.verify: lambda cfg, _: verify.run(cfg),
    Command.clean: lambda cfg, args: clean(cfg, with_source=args.source),
    Command.review_log: lambda cfg, args: review.run(cfg, args.log, args.out),
}


def main(argv: Sequence[str] | None = None) -> None:
    args = parser().parse_args(argv)
    RUN[Command(args.command)](config.load(), args)
