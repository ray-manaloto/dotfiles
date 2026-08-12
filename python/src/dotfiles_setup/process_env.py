# Copyright (c) 2026 Raymond Manaloto
"""Explicit child-process boundaries for credentials and Git-local state.

Git deliberately exports repository-local variables to hooks. Those variables
must not escape into a test suite that creates disposable repositories: a
fixture's ``git init`` or ``git config`` can otherwise mutate the repository
whose pre-push hook launched pytest.

The isolation boundary derives Git's complete local-variable set from Git
itself, removes credentials, and changes only the child environment. It never
prints values or mutates its parent process.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from dotfiles_setup.child_env import clean_env

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


def command_after_separator(command: Sequence[str]) -> tuple[str, ...]:
    """Normalize argparse ``REMAINDER`` while requiring a real command."""
    normalized = tuple(command[1:] if command and command[0] == "--" else command)
    if not normalized:
        msg = "a command is required after --"
        raise ValueError(msg)
    return normalized


def git_local_env_names(*, cwd: Path | None = None) -> frozenset[str]:
    """Ask the installed Git which variables carry repository-local state.

    Git owns this list. Deriving it avoids a hand-maintained list that silently
    misses a variable added by a later Git release. Discovery itself cannot
    inherit Git-local state, and failure is closed because a partial scrub is
    the destructive state.
    """
    discovery_env = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    result = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"],
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=discovery_env,
    )
    if result.returncode != 0:
        msg = f"git rev-parse --local-env-vars failed rc={result.returncode}"
        raise RuntimeError(msg)
    names = frozenset(line for line in result.stdout.splitlines() if line)
    if not names:
        msg = "git rev-parse --local-env-vars returned no variables"
        raise RuntimeError(msg)
    return names


def git_isolated_env(
    base: Mapping[str, str] | None = None,
    *,
    local_names: frozenset[str] | None = None,
) -> dict[str, str]:
    """Return a credential-free environment without Git-local variables."""
    source = dict(os.environ if base is None else base)
    names = git_local_env_names() if local_names is None else local_names
    cleaned = clean_env(source)
    return {name: value for name, value in cleaned.items() if name not in names}


def run_git_isolated(command: Sequence[str], *, cwd: Path | None = None) -> int:
    """Run a test command unable to inherit its caller's Git repository."""
    completed = subprocess.run(command, check=False, cwd=cwd, env=git_isolated_env())
    return completed.returncode
