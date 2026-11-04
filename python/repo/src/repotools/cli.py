"""The repotools command: argv[0] names a generated Command, its generated model parses the rest."""

import subprocess
import sys
from collections.abc import Sequence

from pydantic_settings import CliApp, CliSettingsSource

from . import gates, main_guard, pane_approval, te_review, zero_bash
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
    TeReviewCollect,
    TeReviewCommand,
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
# te-review takes a subcommand word first; each has its own model.
TE_REVIEW: dict[TeReviewCommand, type[Options]] = {TeReviewCommand.collect: TeReviewCollect}
APPROVED = {Command.pane_approved, Command.pr_approved}


def parse(argv: Sequence[str]) -> tuple[Command, Options]:
    if not argv or argv[0] not in set(Command):
        msg = f"repotools: the first argument is one of {', '.join(Command)}"
        raise ValueError(msg)
    command, words = Command(argv[0]), 1
    if command is Command.te_review:
        if len(argv) < 2 or argv[1] not in set(TeReviewCommand):  # noqa: PLR2004 -- te-review and its word
            msg = f"repotools te-review: the next argument is one of {', '.join(TeReviewCommand)}"
            raise ValueError(msg)
        model, words = TE_REVIEW[TeReviewCommand(argv[1])], 2
    else:
        model = OPTIONS[command]
    cli = CliSettingsSource(
        # CliApp.run documents BaseModel input; CliSettingsSource's annotation says BaseSettings only.
        model,  # ty: ignore[invalid-argument-type]
        cli_prog_name=" ".join(["repotools", *argv[:words]]),
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_exit_on_error=False,
    )
    return command, CliApp.run(model, cli_args=list(argv[words:]), cli_settings_source=cli)


def run(command: Command, options: Options) -> None:
    if isinstance(options, ZeroBash):
        found = zero_bash.findings()
        sys.stdout.writelines(finding.model_dump_json() + "\n" for finding in found)
        if options.strict and found:
            raise SystemExit(1)
    elif isinstance(options, ReviewPython | ReviewApproved | PrivacyScan):
        gates.dispatch(options)
    elif isinstance(options, MainGuard | MainGuardInstall | MainGuardRemove | MainGuardArmed):
        main_guard.dispatch(options)
    elif isinstance(options, TeReviewCollect):
        te_review.collect(options)
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
    except te_review.CollectError as error:
        sys.stderr.write(error.failure.model_dump_json() + "\n")
        raise SystemExit(1) from None
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr
        sys.stderr.write(Failure(error=f"{error.cmd[0]} failed: {stderr}").model_dump_json() + "\n")
        raise SystemExit(1) from None
    # The refusals, pydantic's, json's and tomllib's errors (ValueError subclasses), and unreadable files.
    except (ValueError, OSError) as error:
        sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
