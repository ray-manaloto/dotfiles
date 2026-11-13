"""mise run lsp <action> [server] [--json]: the same command for a person, a skill and a doctor check."""

import argparse
import logging
import sys
import unicodedata
from collections.abc import Callable, Sequence
from pathlib import Path

from . import actions
from .models import Action, Failure, Report, Reports, Server

# doctor and conflicts look at every server; the rest take one.
WHOLE = {Action.doctor: actions.doctor, Action.conflicts: actions.conflicts}
ONE: dict[Action, Callable[[Server], Report]] = {
    Action.status: actions.status,
    Action.which: actions.which,
    Action.has_update: actions.has_update,
    Action.health: actions.health,
    Action.smoke: actions.smoke,
    Action.verify: actions.verify,
}
CHANGES = {Action.add, Action.update, Action.remove}


def text(result: Reports) -> str:
    lines = []
    for each in result.reports:
        lines.append(f"{'ok' if each.ok else 'FAIL'}  {each.action.value} {each.server}")
        lines += [
            f"  {'ok' if check.ok else 'FAIL'}  {inert(check.name)}: {inert(check.detail)}" for check in each.checks
        ]
    return "\n".join(lines) + "\n"


def inert(said: str) -> str:
    """Control characters (Unicode Cc: ESC, BEL, newline) as \\xNN, so each check is one line and a terminal acts on
    none of a server's or plugin's text (CODING_STANDARDS 9); other text, "→" included, stays as it is."""
    return "".join(f"\\x{ord(char):02x}" if unicodedata.category(char) == "Cc" else char for char in said)


def outcome(action: Action, server: str | None) -> Reports:
    if action in WHOLE:
        return WHOLE[action]()
    found = actions.find(str(server))
    one = actions.change(action, found, Path.cwd()) if action in CHANGES else ONE[action](found)
    return Reports(action=action, ok=one.ok, reports=[one])


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="lsptools",
        description="Manage and check the language servers Claude Code runs",
        epilog="LSPTOOLS_COMMAND_SECONDS and LSPTOOLS_REQUEST_SECONDS, when set, limit each command (default 300 s)"
        " and each server request (default 60 s).",
    )
    parser.add_argument("action", type=Action, choices=list(Action), metavar="action")
    parser.add_argument("server", nargs="?", help="a name in lsptools/servers.json; doctor and conflicts take none")
    parser.add_argument("--json", action="store_true", help="print the Reports JSON instead of text")
    args = parser.parse_args(argv)
    # pygls logs each server notification and request it has no handler for (publishDiagnostics,
    # client/registerCapability) to stderr; the checks already say what matters.
    logging.getLogger("pygls").setLevel(logging.CRITICAL)
    if (args.action in WHOLE) != (args.server is None):
        parser.error(f"{args.action.value} takes {'no server' if args.action in WHOLE else 'one server'}")
    try:
        result = outcome(args.action, args.server)
    except ValueError as failed:
        sys.stderr.write(Failure(error=str(failed)).model_dump_json() + "\n")
        raise SystemExit(2) from None
    sys.stdout.write(result.model_dump_json(indent=2) + "\n" if args.json else text(result))
    raise SystemExit(0 if result.ok else 1)
