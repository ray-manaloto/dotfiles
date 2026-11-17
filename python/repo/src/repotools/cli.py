"""The repotools command: argv[0] names a generated Command, its generated model parses the rest."""

import subprocess
import sys
from collections.abc import Callable, Sequence

from pydantic_settings import CliApp, CliSettingsSource

from . import (
    fnox_refs,
    gates,
    main_guard,
    merge,
    scratch_env,
    shell,
    test_times,
    tools_install,
    trust,
    zero_bash,
)
from .models import (
    Command,
    Failure,
    FnoxRefs,
    MainGuard,
    MainGuardArmed,
    MainGuardInstall,
    MainGuardRemove,
    Options,
    PrivacyScan,
    PrMerge,
    PrText,
    ScratchEnv,
    ShellApply,
    ShellRollback,
    TestTimes,
    ToolsInstall,
    Trust,
    ZeroBash,
)

OPTIONS: dict[Command, type[Options]] = {
    Command.pr_create: PrText,
    Command.pr_merge: PrMerge,
    Command.zero_bash: ZeroBash,
    Command.privacy_scan: PrivacyScan,
    Command.main_guard: MainGuard,
    Command.main_guard_install: MainGuardInstall,
    Command.main_guard_remove: MainGuardRemove,
    Command.main_guard_armed: MainGuardArmed,
    Command.shell_apply: ShellApply,
    Command.shell_rollback: ShellRollback,
    Command.tools_install: ToolsInstall,
    Command.test_times: TestTimes,
    Command.trust: Trust,
    Command.fnox_refs: FnoxRefs,
}
# The commands that take no options, by their model.
NO_OPTIONS: dict[type[Options], Callable[[], None]] = {
    ToolsInstall: tools_install.run,
    TestTimes: test_times.report,
    Trust: trust.run,
    FnoxRefs: fnox_refs.report,
}


def parse(argv: Sequence[str]) -> Options | ScratchEnv:
    if not argv or argv[0] not in set(Command):
        msg = f"repotools: the first argument is one of {', '.join(Command)}"
        raise ValueError(msg)
    command = Command(argv[0])
    # scratch-env takes the folder, then the command, by position. CliApp reads a field by position only when its
    # annotation carries CliPositionalArg (pydantic-settings 2.16.2 sources/providers/cli.py:352,955), which
    # datamodel-codegen cannot write into the generated model, so the schema's model validates them here.
    if command is Command.scratch_env:
        return ScratchEnv.model_validate({"folder": argv[1] if argv[1:] else "", "command": argv[2:]})
    model = OPTIONS[command]
    cli = CliSettingsSource(
        # CliApp.run documents BaseModel input; CliSettingsSource's annotation says BaseSettings only.
        model,  # ty: ignore[invalid-argument-type]
        cli_prog_name=f"repotools {command.value}",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_exit_on_error=False,
    )
    return CliApp.run(model, cli_args=list(argv[1:]), cli_settings_source=cli)


def run(options: Options) -> None:
    if isinstance(options, ZeroBash):
        zero_bash.report(options)
    elif isinstance(options, PrivacyScan):
        gates.privacy_scan(options)
    elif isinstance(options, MainGuard | MainGuardInstall | MainGuardRemove | MainGuardArmed):
        main_guard.dispatch(options)
    elif isinstance(options, ShellApply | ShellRollback):
        shell.dispatch(options)
    elif isinstance(options, PrMerge):
        merge.merge(options)
    elif isinstance(options, PrText):
        merge.create(options)
    else:
        NO_OPTIONS[type(options)]()


def main(argv: Sequence[str] | None = None) -> None:
    try:
        options = parse(sys.argv[1:] if argv is None else argv)
        if isinstance(options, ScratchEnv):  # parsed by position, so it stays out of run()
            scratch_env.run(options)
        else:
            run(options)
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr
        sys.stderr.write(Failure(error=f"{error.cmd[0]} failed: {stderr}").model_dump_json() + "\n")
        raise SystemExit(1) from None
    # The refusals, pydantic's, json's and tomllib's errors (ValueError subclasses), and unreadable files.
    except (ValueError, OSError) as error:
        sys.stderr.write(Failure(error=str(error)).model_dump_json() + "\n")
        raise SystemExit(1) from None
