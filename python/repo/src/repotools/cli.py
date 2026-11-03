"""The repotools command: argv[0] names a generated Command, its generated model parses the rest."""

import subprocess
import sys
from collections.abc import Sequence

from pydantic_settings import CliApp, CliSettingsSource

from . import pane_approval
from .models import Command, Failure, Fingerprint, NoOptions, PanePin

OPTIONS: dict[Command, type[NoOptions | PanePin]] = {
    Command.pane_fingerprint: NoOptions,
    Command.pane_pin: PanePin,
    Command.pane_approved: NoOptions,
}


def parse(argv: Sequence[str]) -> tuple[Command, NoOptions | PanePin]:
    if not argv or argv[0] not in set(Command):
        msg = f"repotools: the first argument is one of {', '.join(Command)}"
        raise ValueError(msg)
    command = Command(argv[0])
    model = OPTIONS[command]
    cli = CliSettingsSource(
        # CliApp.run documents BaseModel input; CliSettingsSource's annotation says BaseSettings only.
        model,  # ty: ignore[invalid-argument-type]
        cli_prog_name=f"repotools {command.value}",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_exit_on_error=False,
    )
    return command, CliApp.run(model, cli_args=list(argv[1:]), cli_settings_source=cli)


def run(command: Command, options: NoOptions | PanePin) -> None:
    if isinstance(options, PanePin):
        pane_approval.pin(options)
    elif command is Command.pane_approved:
        pane_approval.check()
    if command is not Command.pane_approved:
        sys.stdout.write(Fingerprint(fingerprint=pane_approval.fingerprint()).model_dump_json() + "\n")


def main(argv: Sequence[str] | None = None) -> None:
    try:
        run(*parse(sys.argv[1:] if argv is None else argv))
    except subprocess.CalledProcessError as error:
        sys.stderr.write(Failure(error=f"{error.cmd[0]} failed: {error.stderr}").model_dump_json() + "\n")
        raise SystemExit(1) from None
    except (ValueError, OSError) as error:  # the refusals, pydantic's and json's errors, and unreadable files
        sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
