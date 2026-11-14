"""The repotools command: argv[0] names a generated Command, its generated model parses the rest."""

import subprocess
import sys
from collections.abc import Callable, Sequence

from pydantic_settings import CliApp, CliSettingsSource

from . import (
    fnox_refs,
    gates,
    main_guard,
    pane_approval,
    scratch_env,
    shell,
    test_times,
    tools_install,
    trust,
    zero_bash,
)
from .models import (
    Command,
    CommitText,
    Failure,
    Fingerprint,
    FnoxRefs,
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
    ScratchEnv,
    ShellApply,
    ShellRollback,
    TestTimes,
    ToolchainGate,
    ToolsInstall,
    Trust,
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
    Command.shell_apply: ShellApply,
    Command.shell_rollback: ShellRollback,
    Command.toolchain_gate: ToolchainGate,
    Command.tools_install: ToolsInstall,
    Command.test_times: TestTimes,
    Command.trust: Trust,
    Command.fnox_refs: FnoxRefs,
}
APPROVED = {Command.pane_approved, Command.pr_approved}
# The commands that take no options, by their model.
NO_OPTIONS: dict[type[Options], Callable[[], None]] = {
    ToolsInstall: tools_install.run,
    TestTimes: test_times.report,
    Trust: trust.run,
    FnoxRefs: fnox_refs.report,
}


def parse(argv: Sequence[str]) -> tuple[Command, Options | ScratchEnv]:
    if not argv or argv[0] not in set(Command):
        msg = f"repotools: the first argument is one of {', '.join(Command)}"
        raise ValueError(msg)
    command = Command(argv[0])
    # scratch-env takes the folder, then the command, by position. CliApp reads a field by position only when its
    # annotation carries CliPositionalArg (pydantic-settings 2.16.2 sources/providers/cli.py:352,955), which
    # datamodel-codegen cannot write into the generated model, so the schema's model validates them here.
    if command is Command.scratch_env:
        return command, ScratchEnv.model_validate({"folder": argv[1] if argv[1:] else "", "command": argv[2:]})
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
        zero_bash.report(options)
    elif isinstance(options, ReviewPython | ReviewApproved | PrivacyScan | ToolchainGate):
        gates.dispatch(options)
    elif isinstance(options, MainGuard | MainGuardInstall | MainGuardRemove | MainGuardArmed):
        main_guard.dispatch(options)
    elif isinstance(options, ShellApply | ShellRollback):
        shell.dispatch(options)
    elif isinstance(options, PanePin):
        pane_approval.pin(options)
    elif isinstance(options, PrText) and command is Command.pr_create:
        pane_approval.create(options)
    elif isinstance(options, ToolsInstall | TestTimes | Trust | FnoxRefs):
        NO_OPTIONS[type(options)]()
    elif command in APPROVED:
        pane_approval.check(options)
    else:
        sys.stdout.write(Fingerprint(fingerprint=pane_approval.fingerprint(options)).model_dump_json() + "\n")


def main(argv: Sequence[str] | None = None) -> None:
    try:
        command, options = parse(sys.argv[1:] if argv is None else argv)
        if isinstance(options, ScratchEnv):  # parsed by position, so it stays out of run()
            scratch_env.run(options)
        else:
            run(command, options)
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr
        sys.stderr.write(Failure(error=f"{error.cmd[0]} failed: {stderr}").model_dump_json() + "\n")
        raise SystemExit(1) from None
    # The refusals, pydantic's, json's and tomllib's errors (ValueError subclasses), and unreadable files.
    except (ValueError, OSError) as error:
        sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
