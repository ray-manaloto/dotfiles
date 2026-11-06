"""Start a program as the shell task did: its stderr goes to the task's, and a failure stops the task."""

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from .config import ToolchainError


def finished(
    argv: tuple[str | Path, ...],
    env: Mapping[str, str] | None = None,
    stdout: int | None = None,
    stderr: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """argv run to the end; one that can't start or exits non-zero raises ToolchainError."""
    try:
        done = subprocess.run(argv, env=env, stdout=stdout, stderr=stderr, text=True, check=False)
    except OSError as failed:
        msg = f"{argv[0]}: {failed.strerror}"
        raise ToolchainError(msg) from None
    if done.returncode:
        msg = f"{argv[0]} exited {done.returncode}"
        raise ToolchainError(msg)
    return done


def run(*argv: str | Path, env: Mapping[str, str] | None = None, merge: bool = False) -> str:
    """argv's stdout (and stderr, merged), its trailing newlines dropped as $(...) drops them."""
    stderr = subprocess.STDOUT if merge else None
    return finished(argv, env=env, stdout=subprocess.PIPE, stderr=stderr).stdout.rstrip("\n")


def call(*argv: str | Path) -> None:
    """argv with the task's own stdout and stderr, so its output shows as it runs."""
    finished(argv)


def head(*argv: str | Path) -> None:
    """The first line of argv's stdout, as | head -n 1 printed it."""
    for line in run(*argv).splitlines()[:1]:
        out(line)


def out(line: str) -> None:
    """One line on the task's stdout, flushed so it keeps its place among the programs' own output."""
    sys.stdout.write(f"{line}\n")
    sys.stdout.flush()


def compiler_env() -> dict[str, str]:
    """The environment clang-p2996 needs to load its default config (env -u SDKROOT -u CLANG_NO_DEFAULT_CONFIG)."""
    return {k: v for k, v in os.environ.items() if k not in {"SDKROOT", "CLANG_NO_DEFAULT_CONFIG"}}
