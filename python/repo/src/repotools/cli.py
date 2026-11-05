"""The repotools command: argv[0] names a generated Command, its generated model parses the rest."""

import subprocess
import sys
from collections.abc import Callable, Sequence

from pydantic_settings import CliApp, CliSettingsSource

from . import gates, main_guard, pane_approval, te_carry, te_receipts, te_report, te_review, zero_bash
from .models import (
    Command,
    CommitText,
    ErrorCode,
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
    PublicFailure,
    ReviewApproved,
    ReviewPython,
    TeReviewCarry,
    TeReviewCollect,
    TeReviewCommand,
    TeReviewReceiptsCommand,
    TeReviewReceiptsDraft,
    TeReviewReport,
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
# te-review takes a subcommand first, one word or receipts and its own word; each has its own model.
TE_REVIEW: dict[tuple[str, ...], type[Options]] = {
    (TeReviewCommand.collect,): TeReviewCollect,
    (TeReviewCommand.report,): TeReviewReport,
    (TeReviewCommand.receipts, TeReviewReceiptsCommand.draft): TeReviewReceiptsDraft,
    (TeReviewCommand.carry,): TeReviewCarry,
}
# The te-review subcommands each one module's function runs.
TE_REVIEW_RUNS: dict[type[TeReviewReceiptsDraft | TeReviewCarry], Callable[..., None]] = {
    TeReviewReceiptsDraft: te_receipts.draft,
    TeReviewCarry: te_carry.carry,
}
APPROVED = {Command.pane_approved, Command.pr_approved}


def parse(argv: Sequence[str]) -> tuple[Command, Options]:
    if not argv or argv[0] not in set(Command):
        msg = f"repotools: the first argument is one of {', '.join(Command)}"
        raise ValueError(msg)
    command, words = Command(argv[0]), 1
    if command is Command.te_review:
        given = [key for key in TE_REVIEW if tuple(argv[1 : 1 + len(key)]) == key]
        if not given:
            msg = f"repotools te-review: the next arguments are one of {', '.join(map(' '.join, TE_REVIEW))}"
            raise ValueError(msg)
        model, words = TE_REVIEW[given[0]], 1 + len(given[0])
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
    try:
        return command, CliApp.run(model, cli_args=list(argv[words:]), cli_settings_source=cli)
    # A te-review report argument may be private, and the mode is unknown until parsing succeeds, so a
    # parse error is the code only, whatever mode the arguments ask for.
    except ValueError as error:
        if model is not TeReviewReport:
            raise
        refusal = te_review.TeReviewError(ErrorCode.BAD_ARGUMENTS, str(error))
        refusal.public = True
        raise refusal from None


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
    elif isinstance(options, TeReviewCollect | TeReviewReport):
        te_report.dispatch(options)
    elif isinstance(options, TeReviewReceiptsDraft | TeReviewCarry):
        TE_REVIEW_RUNS[type(options)](options)
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
    except te_review.TeReviewError as error:
        failure = PublicFailure(code=error.failure.code) if error.public else error.failure
        sys.stderr.write(failure.model_dump_json() + "\n")
        raise SystemExit(1) from None
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr
        sys.stderr.write(Failure(error=f"{error.cmd[0]} failed: {stderr}").model_dump_json() + "\n")
        raise SystemExit(1) from None
    # The refusals, pydantic's, json's and tomllib's errors (ValueError subclasses), and unreadable files.
    except (ValueError, OSError) as error:
        sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
