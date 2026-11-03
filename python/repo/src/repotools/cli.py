"""The repotools command: argv[0] names a generated Command, its generated model parses the rest."""

import subprocess
import sys
from collections.abc import Sequence

from pydantic_settings import CliApp, CliSettingsSource

from . import gates, main_guard, pane_approval, zero_bash
from .models import (
    Command,
    CommitText,
    Failure,
    Fingerprint,
    MainGuard,
    MainGuardArmed,
    MainGuardInstall,
    MainGuardRemove,
    Options,
    PanePin,
    PrivacyScan,
    PrText,
    ReviewApproved,
    ReviewPython,
    ZeroBash,
)

OPTIONS: dict[Command, type[Options]] = {
    Command.pane_fingerprint: CommitText,
    Command.pane_pin: PanePin,
    Command.pane_approved: CommitText,
    Command.pr_fingerprint: PrText,
    Command.pr_approved: PrText,
    Command.pr_create: PrText,
    Command.zero_bash: ZeroBash,
    Command.review_python: ReviewPython,
    Command.review_python_approved: ReviewApproved,
    Command.privacy_scan: PrivacyScan,
    Command.main_guard: MainGuard,
    Command.main_guard_install: MainGuardInstall,
    Command.main_guard_remove: MainGuardRemove,
    Command.main_guard_armed: MainGuardArmed,
}
APPROVED = {Command.pane_approved, Command.pr_approved}


def parse(argv: Sequence[str]) -> tuple[Command, Options]:
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


def run(command: Command, options: Options) -> None:
    if isinstance(options, ZeroBash):
        found = zero_bash.findings()
        sys.stdout.writelines(finding.model_dump_json() + "\n" for finding in found)
        if options.strict and found:
            raise SystemExit(1)
    elif isinstance(options, ReviewPython):
        gates.review(options)
    elif isinstance(options, ReviewApproved):
        gates.approved()
    elif isinstance(options, PrivacyScan):
        gates.privacy_scan(options)
    elif isinstance(options, MainGuard | MainGuardInstall | MainGuardRemove | MainGuardArmed):
        main_guard.dispatch(options)
    elif isinstance(options, PanePin):
        pane_approval.pin(options)
    elif isinstance(options, PrText) and command is Command.pr_create:
        pane_approval.create(options)
    elif command in APPROVED:
        pane_approval.check(options)
    else:
        sys.stdout.write(Fingerprint(fingerprint=pane_approval.fingerprint(options)).model_dump_json() + "\n")


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
