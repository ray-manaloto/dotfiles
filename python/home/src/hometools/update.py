"""update-brew and update-check: upgrade Homebrew with the toolchain held (DL-595), and the read-only drift check."""

import json
import subprocess
import sys
from typing import NoReturn

from .models import Failure
from .proc import out
from .toolchain import PINNED

# update:check's exit codes, kept distinct because collapsing them is how the 2026-08-24 defect happened: a
# check that could not run must never read as green.
IN_SYNC, DRIFT, COULD_NOT_CHECK = 0, 1, 2


def stop(error: str, code: int) -> NoReturn:
    """The one JSON error event the command ends with, and the exit code its shell task had."""
    sys.stderr.write(Failure(error=error).model_dump_json() + "\n")
    raise SystemExit(code)


def step(*argv: str, stdout: int | None = None) -> str:
    """argv run as a `set -e` step: a failure stops the task with argv's exit status as the shell gives it."""
    try:
        done = subprocess.run(argv, stdout=stdout, text=True, check=False)
    except OSError as failed:
        stop(f"{argv[0]}: {failed.strerror}", 127)
    # subprocess gives a signal's death as -N; the shell's status, and so the task's exit code, is 128 + N.
    code = done.returncode if done.returncode >= 0 else 128 - done.returncode
    if code:
        stop(f"{' '.join(argv)} exited {code}", code)
    return done.stdout or ""


def brew() -> None:
    """Refuse unless every toolchain package is pinned, then update and upgrade the rest and verify the toolchain."""
    pinned = set(step("brew", "list", "--pinned", stdout=subprocess.PIPE).splitlines())
    for name in PINNED:
        if name not in pinned:
            fix = f"run 'brew pin {name}' or do a planned toolchain upgrade (DL-595)"
            stop(f"update:brew: {name} is not pinned; {fix}", 1)
    # --yes: brew can prompt (casks that need confirmation), and update:all runs this with no terminal.
    for argv in (("brew", "update"), ("brew", "upgrade", "--yes"), ("mise", "run", "toolchain:verify")):
        step(*argv)


def report(source: str, *argv: str) -> dict[str, object]:
    """argv's JSON report, printed; a source that can't start, fails or answers no JSON object can't be checked.

    Unreadable output exits 2 where the shell task exited 0, its jq test failing and `&& drift=1` skipped: a false
    green the task's contract forbids (owner, 2026-11-06).
    """
    try:
        done = subprocess.run(argv, stdout=subprocess.PIPE, text=True, check=False)
    except OSError:
        done = None
    text = done.stdout if done is not None and done.returncode == 0 else ""
    try:
        answer = json.loads(text)
    except json.JSONDecodeError:
        answer = None
    if not isinstance(answer, dict):
        stop(f"update:check: '{source}' failed — COULD NOT CHECK", COULD_NOT_CHECK)
    out(text.rstrip("\n"))
    return answer


def check() -> None:
    """Print and gate every source: brew's outdated formulae and casks, mise's outdated tools, mise's upgrades."""
    # Not gated: mise's newer versions outside the configured ranges, pinned on purpose (`mise upgrade --bump`).
    formulae = report("brew outdated", "brew", "outdated", "--json")
    tools = report("mise outdated", "mise", "outdated", "--json")
    drift = bool(formulae.get("formulae") or formulae.get("casks") or tools)
    # Its exit code is the answer: non-zero when an upgrade is due.
    try:
        upgrades = subprocess.run(("mise", "upgrade", "--dry-run-code"), check=False).returncode
    except OSError as failed:
        # The shell task's `|| drift=1` counted a mise that can't start as drift; its error is the one event.
        sys.stderr.write(Failure(error=f"mise: {failed.strerror}").model_dump_json() + "\n")
        upgrades = 127
    raise SystemExit(DRIFT if drift or upgrades else IN_SYNC)
