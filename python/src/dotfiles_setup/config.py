# Copyright (c) 2026 Raymond Manaloto
"""Centralized configuration for dotfiles setup.

All environment variables and hardcoded paths are consolidated here
so that the rest of the codebase receives typed, validated config
via dependency injection rather than reading os.environ directly.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MiseConfig(BaseSettings):
    """Mise tool-manager configuration."""

    model_config = SettingsConfigDict(env_prefix="MISE_")

    install_path: Path = Path("/usr/local/bin/mise")
    shell: str | None = None


class ContainerConfig(BaseSettings):
    """Devcontainer and Docker image configuration."""

    model_config = SettingsConfigDict(env_prefix="DOTFILES_")

    image: str = "dotfiles-dev-local"
    base_image: str = "ghcr.io/ray-manaloto/dotfiles-devcontainer:dev"
    host_state_dir: Path | None = None
    ssh_port: int = 4444


# Paths that live inside the container at well-known locations.
# Declared here (with S108 per-file-ignore in pyproject.toml) so that
# no other module needs inline lint suppressions for /tmp references.
# Bind-mounted from the host at ``~/.local/state/dotfiles`` so the
# container's R1 sshd can read the staged authorized_keys file.
CONTAINER_HOST_STATE_DIR = Path("/tmp/dotfiles-host-state")

DEFAULT_HOST_STATE_DIR = Path.home() / ".local" / "state" / "dotfiles"


def host_state_dir(config: DotfilesConfig | None = None) -> Path:
    """Resolve the devcontainer runtime state directory.

    Lives here rather than in :mod:`dotfiles_setup.docker` (#893) because
    :mod:`dotfiles_setup.devcontainer_names` needs it to compose the secrets
    env-file path, and ``docker`` already imports ``devcontainer_names`` — so
    keeping it there forced a function-level import to dodge the cycle.
    ``config`` is a leaf module, which makes it the honest home for a path
    every layer resolves.

    Args:
        config: Optional config; defaults to env-var lookup for backward compat.
    """
    if config is not None and config.container.host_state_dir is not None:
        return config.container.host_state_dir
    raw_dir = os.environ.get("DOTFILES_HOST_STATE_DIR")
    if raw_dir:
        return Path(raw_dir)
    is_devcontainer = (config is not None and config.devcontainer) or os.environ.get(
        "DEVCONTAINER"
    ) == "true"
    if is_devcontainer:
        return CONTAINER_HOST_STATE_DIR
    return DEFAULT_HOST_STATE_DIR


class DotfilesConfig(BaseSettings):
    """Root configuration aggregating all subsystems.

    Instantiate once at the CLI entry point and pass to subsystems
    via constructor/function parameters.
    """

    mise: MiseConfig = Field(default_factory=MiseConfig)
    container: ContainerConfig = Field(default_factory=ContainerConfig)

    # Standalone env vars (no prefix group)
    devcontainer: bool = False  # env: DEVCONTAINER
    ssh_auth_sock: Path | None = None  # env: SSH_AUTH_SOCK
    expected_user: str | None = None  # env: EXPECTED_USER
    expected_uid: int | None = None  # env: EXPECTED_UID
    expected_gid: int | None = None  # env: EXPECTED_GID
