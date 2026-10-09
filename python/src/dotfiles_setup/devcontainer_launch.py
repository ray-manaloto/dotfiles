# Copyright (c) 2026 Raymond Manaloto
"""Launch the native devcontainer CLI with the task's resolved identity."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotfiles_setup import child_env
from dotfiles_setup.devcontainer_names import (
    ARCH_LABEL_ENV_VAR,
    WORKSPACE_LABEL_ENV_VAR,
    resolve_names,
)
from dotfiles_setup.sync_override import (
    OVERRIDE_PATH_ENV,
    OWNER_FD_ENV,
    active_override_from_env,
)


def launch_main(*, rebuild: bool = False) -> int:
    """Run native up; only an inherited live sync owner may omit lifecycle smoke.

    ``mise run up`` and ``mise run dev-rebuild`` still own their existing task
    environment, name/port resolution and known-host cleanup. This narrow
    boundary selects a verified private override for canonical sync and keeps
    every direct invocation on the original devcontainer configuration.
    """
    workspace = Path.cwd().resolve()
    try:
        names = resolve_names(workspace=workspace)
    except ValueError as exc:
        sys.stderr.write(f"devcontainer launch: {exc}\n")
        return 2
    expected = {
        WORKSPACE_LABEL_ENV_VAR: names.workspace_label,
        ARCH_LABEL_ENV_VAR: names.arch_label,
    }
    for key, value in expected.items():
        if os.environ.get(key) != value:
            sys.stderr.write(
                f"devcontainer launch: {key} does not match the resolved workspace\n"
            )
            return 2
    try:
        override = active_override_from_env(workspace, os.environ)
    except ValueError as exc:
        sys.stderr.write(f"devcontainer launch: {exc}\n")
        return 2

    command = [
        "fnox",
        "exec",
        "--non-interactive",
        "--",
        "devcontainer",
        "up",
        "--workspace-folder",
        ".",
        "--id-label",
        names.workspace_label,
        "--id-label",
        names.arch_label,
    ]
    if override is not None:
        command.extend(("--override-config", str(override)))
    if rebuild:
        command.extend(("--remove-existing-container", "--build-no-cache"))

    env = child_env.without_git_context()
    env.pop(OVERRIDE_PATH_ENV, None)
    env.pop(OWNER_FD_ENV, None)
    try:
        return subprocess.run(command, env=env, cwd=workspace, check=False).returncode
    except OSError as exc:
        sys.stderr.write(f"devcontainer launch: native CLI unavailable: {exc}\n")
        return 127
