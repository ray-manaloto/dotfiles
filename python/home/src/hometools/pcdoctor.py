"""pc-doctor: the PC's drift from the dotfiles `pc` config environment, read over ssh; it never changes anything."""

# Spec #633, ticket #634, and the result contract spec #729 asks this ticket to define once for every pc:doctor
# check. Each check prints one PcDoctorLine: fail when it saw the problem, unknown when it could not look (ssh failed,
# a tool was missing, a command timed out, output did not parse). The exit code is herdr-doctor's table: 1 when any
# line failed, 3 when none failed and any was unknown, 0 otherwise. Diagnostics go to stderr. Every command has a
# time limit, PC_DOCTOR_TIMEOUT seconds; a timeout is unknown, never a pass.
#
# The PC selects the environment itself (env = ["pc"] in its ~/.config/mise/miserc.local.toml), so the doctor never
# passes -E pc: a PC that lost its selection must not read as healthy. Only entries whose origin names the pc
# environment are judged. The PC's other configs (Omarchy's /etc/mise/conf.d lists lazy tools that are mostly not
# installed) make a plain `status --missing` exit 1 on a healthy PC; those differences go to stderr instead.

import math
import os
import subprocess
import sys
from collections.abc import Callable
from functools import partial

from . import pcupdates
from .models import BootstrapEntry, BootstrapPlanReport, BootstrapStatusReport, Failure, PcDoctorLine, Result

HOST = "pc"  # the ssh alias (~/.ssh/config.d/tailnet.conf); its real name stays in Doppler
ENVIRONMENT = "pc"
# -n: no stdin for ssh to read. BatchMode: never a password or host-key prompt. ConnectTimeout bounds the
# connection; the time limit below bounds the whole call.
SSH = ("ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, "--")
LIMIT, DEFAULT_LIMIT = "PC_DOCTOR_TIMEOUT", 120
SSH_FAILED = 255
USAGE = 2


def limit() -> float:
    """The time limit in seconds; a value that is not a finite positive number stops the doctor before any call."""
    text = os.environ.get(LIMIT, str(DEFAULT_LIMIT))
    try:
        seconds = float(text)
    except ValueError:
        seconds = 0.0
    # nan, inf and 1e999 (inf) parse, but subprocess cannot wait for them.
    if not math.isfinite(seconds) or seconds <= 0:
        sys.stderr.write(
            Failure(error=f"pc-doctor: {LIMIT}={text!r} is not a finite positive number of seconds").model_dump_json()
            + "\n"
        )
        raise SystemExit(USAGE)
    return seconds


def on_pc(argv: tuple[str, ...], seconds: float) -> subprocess.CompletedProcess[str] | str:
    """argv run on the PC, or why it could not run; the PC's stderr goes to the doctor's."""
    try:
        done = subprocess.run((*SSH, *argv), capture_output=True, text=True, timeout=seconds, check=False)
    except subprocess.TimeoutExpired:
        return f"ssh {HOST} {' '.join(argv)} timed out after {seconds:g} s"
    except OSError as failed:
        return f"ssh: {failed.strerror}"
    sys.stderr.write(done.stderr)
    if done.returncode == SSH_FAILED:
        return f"ssh {HOST} failed (exit {SSH_FAILED})"
    return done


def remote(argv: tuple[str, ...], seconds: float) -> subprocess.CompletedProcess[str] | str:
    """mise bootstrap argv run on the PC, or why it could not run."""
    return on_pc(("mise", "bootstrap", *argv), seconds)


def planned(stdout: str) -> list[BootstrapEntry]:
    """Every resource of mise bootstrap plan --json; ValueError if it is not that report."""
    return BootstrapPlanReport.model_validate_json(stdout).resources


def statuses(stdout: str) -> list[BootstrapEntry]:
    """The files part of mise bootstrap status --json, the one part pc declares (a ticket adding a part reads its
    list here too); ValueError if it is not that report."""
    return BootstrapStatusReport.model_validate_json(stdout).files


# Each check: its name, its mise bootstrap arguments, the exit codes that are an answer, not an error, and the reader
# of its report (a report that does not validate is unknown, so only a valid empty one reads as unselected).
# status --missing exits 1 when anything differs; plan --detailed-exitcode exits 2 when it would change something
# and 1 when planning failed or a resource's state is unknown.
CHECKS = (
    ("bootstrap-status", ("status", "--missing", "--json"), {0, 1}, statuses),
    ("bootstrap-plan", ("plan", "--json", "--detailed-exitcode"), {0, 2}, planned),
)
# The checks beyond mise bootstrap, each in its own module: a function of the ssh runner that returns its line.
LINES = (pcupdates.line,)


def mine(entries: list[BootstrapEntry]) -> list[tuple[str | None, str]]:
    """(action, <kind>:<name>) for each entry the pc environment declares."""
    return [(e.action, f"{e.id.kind}:{e.id.name}") for e in entries if e.origin and ENVIRONMENT in e.origin.environment]


def judge(
    check: str, done: subprocess.CompletedProcess[str], answers: set[int], read: Callable[[str], list[BootstrapEntry]]
) -> PcDoctorLine:
    """One line from mise's JSON report: drift in a pc entry fails, anything it could not read is unknown."""
    why = ""
    try:
        named = mine(read(done.stdout))
    except ValueError as failed:
        # A report that is not mise's: no JSON, not an object, no files or resources list (such as {}), or an entry
        # without an id: pydantic's ValidationError, a ValueError, for each. Only a valid empty report is unselected.
        named, why = None, f"mise's output did not parse: {type(failed).__name__} (exit {done.returncode})"
    # An entry with no action is one mise did not judge: unknown, never drift.
    drift = [name for action, name in named or () if action not in {"noop", "unknown", None}]
    unread = [name for action, name in named or () if action in {"unknown", None}]
    if named is not None and done.returncode and not drift and not unread:
        sys.stderr.write(f"pc-doctor: {check}: mise exited {done.returncode} for entries outside the pc environment\n")
    if named is None:
        result, detail = Result.unknown, why
    elif drift:
        result, detail = Result.fail, f"{len(drift)} pc entries differ from dotfiles"
    elif done.returncode not in answers:
        # An error exit: an empty report then proves nothing, so it is not read as an unselected environment.
        result, detail = Result.unknown, f"mise bootstrap exited {done.returncode}"
    elif not named:
        result, detail = Result.fail, "no entry from the pc environment: the PC does not select it (miserc.local.toml)"
    elif unread:
        result, detail = Result.unknown, f"mise could not read the state of {len(unread)} pc entries"
    else:
        result, detail = Result.pass_, f"{len(named)} pc entries match dotfiles"
    return PcDoctorLine(check=check, result=result, detail=detail, culprits=drift or unread)


def code(lines: list[PcDoctorLine]) -> int:
    """1 when any line failed, 3 when none failed and any was unknown, 0 otherwise (herdr-doctor's table)."""
    results = {line.result for line in lines}
    if Result.fail in results:
        return 1
    return 3 if Result.unknown in results else 0


def doctor() -> None:
    """One JSON line per check on stdout, and the exit code of the checks."""
    seconds = limit()
    lines = []

    def emit(made: PcDoctorLine) -> None:
        sys.stdout.write(made.model_dump_json() + "\n")
        sys.stdout.flush()
        lines.append(made)

    for check, argv, answers, read in CHECKS:
        done = remote(argv, seconds)
        if isinstance(done, str):
            emit(PcDoctorLine(check=check, result=Result.unknown, detail=done, culprits=[]))
        else:
            emit(judge(check, done, answers, read))
    for line in LINES:
        emit(line(partial(on_pc, seconds=seconds)))
    raise SystemExit(code(lines))
