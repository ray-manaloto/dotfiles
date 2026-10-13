# Copyright (c) 2026 Raymond Manaloto
"""Git environments scoped to disposable proof subprocesses."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from dotfiles_setup.process_env import git_isolated_env

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def scratch_git_env(
    config_dir: Path, *, checkout: Path, base: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Create fresh config and return a scratch-only child environment.

    ``config_dir`` must not exist; its lifecycle belongs to the caller. Reuse
    the returned environment for every Git subprocess in that proof. The
    parent environment and its Git configuration remain unchanged.
    """
    env = git_isolated_env(base)
    config_dir = config_dir.resolve()
    config_dir.mkdir(mode=0o700)
    gitconfig = config_dir / "gitconfig"
    gitconfig.write_text("[user]\n\tname = T\n\temail = t@example.com\n")
    env["GIT_CONFIG_GLOBAL"] = str(gitconfig)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    template_dir = config_dir / "empty-template"
    template_dir.mkdir(mode=0o700)
    env["GIT_TEMPLATE_DIR"] = str(template_dir)
    # Native Git quotes arbitrary checkout paths safely in its own format.
    subprocess.run(
        [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            str(checkout.resolve()),
        ],
        cwd=config_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return env
