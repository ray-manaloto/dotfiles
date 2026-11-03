"""The repotools command: argv[0] names a generated Command, its generated model parses the rest."""

import subprocess
import sys
from collections.abc import Sequence

from pydantic_settings import CliApp, CliSettingsSource

from . import pane_approval, zero_bash
from .models import Command, Failure, Fingerprint, NoOptions, PanePin, ZeroBash

OPTIONS: dict[Command, type[NoOptions | PanePin | ZeroBash]] = {
    Command.pane_fingerprint: NoOptions,
    Command.pane_pin: PanePin,
    Command.pane_approved: NoOptions,
    Command.zero_bash: ZeroBash,
}


def parse(argv: Sequence[str]) -> tuple[Command, NoOptions | PanePin | ZeroBash]:
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


def run(command: Command, options: NoOptions | PanePin | ZeroBash) -> None:
    if isinstance(options, ZeroBash):
        found = zero_bash.findings()
        sys.stdout.writelines(finding.model_dump_json() + "\n" for finding in found)
        if options.strict and found:
            raise SystemExit(1)
        return
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
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr
        sys.stderr.write(Failure(error=f"{error.cmd[0]} failed: {stderr}").model_dump_json() + "\n")
        raise SystemExit(1) from None
    # The refusals, pydantic's, json's and tomllib's errors (ValueError subclasses), and unreadable files.
    except (ValueError, OSError) as error:
        sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
