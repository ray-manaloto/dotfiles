# Copyright (c) 2026 Raymond Manaloto
"""Behavioral boundaries for canonical sync's private lifecycle override."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import devcontainer_launch
from dotfiles_setup.devcontainer_names import (
    ARCH_LABEL_ENV_VAR,
    WORKSPACE_LABEL_ENV_VAR,
    resolve_names,
)
from dotfiles_setup.sync_override import (
    OVERRIDE_PATH_ENV,
    OWNER_FD_ENV,
    active_sync_override,
)

if TYPE_CHECKING:
    import pytest


def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workspace = tmp_path / "dotfiles"
    config_dir = workspace / ".devcontainer"
    config_dir.mkdir(parents=True)
    source = Path(__file__).parent.parent / ".devcontainer" / "devcontainer.json"
    (config_dir / "devcontainer.json").write_bytes(source.read_bytes())
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("USER", "sync-test")
    monkeypatch.setenv("DOTFILES_PLATFORM", "linux/amd64/v2")
    names = resolve_names(workspace=workspace)
    monkeypatch.setenv(WORKSPACE_LABEL_ENV_VAR, names.workspace_label)
    monkeypatch.setenv(ARCH_LABEL_ENV_VAR, names.arch_label)
    return workspace


def test_direct_and_sync_owned_launch_preserve_lifecycle_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direct up keeps smoke; a live sync owner omits only that one command."""
    workspace = _workspace(tmp_path, monkeypatch)
    source_path = workspace / ".devcontainer" / "devcontainer.json"
    original = source_path.read_bytes()
    calls: list[tuple[list[str], dict[str, str]]] = []

    def record(
        command: list[str], *, env: dict[str, str], cwd: Path, check: bool
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == workspace
        assert check is False
        calls.append((command, env))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(devcontainer_launch.subprocess, "run", record)
    monkeypatch.delenv(OVERRIDE_PATH_ENV, raising=False)
    monkeypatch.delenv(OWNER_FD_ENV, raising=False)
    assert devcontainer_launch.launch_main() == 0
    direct_command, _ = calls[-1]
    assert direct_command[:6] == [
        "fnox",
        "exec",
        "--non-interactive",
        "--",
        "devcontainer",
        "up",
    ]
    labels = [
        direct_command[index + 1]
        for index, value in enumerate(direct_command)
        if value == "--id-label"
    ]
    assert labels == [
        os.environ[WORKSPACE_LABEL_ENV_VAR],
        os.environ[ARCH_LABEL_ENV_VAR],
    ]
    assert "--override-config" not in direct_command
    assert b" && scripts/devcontainer-smoke.sh" in original
    assert devcontainer_launch.launch_main(rebuild=True) == 0
    rebuild_command, _ = calls[-1]
    assert "--override-config" not in rebuild_command
    assert rebuild_command[-2:] == ["--remove-existing-container", "--build-no-cache"]

    with active_sync_override(workspace) as owner:
        monkeypatch.setenv(OVERRIDE_PATH_ENV, str(owner.path))
        monkeypatch.setenv(OWNER_FD_ENV, str(owner.owner_fd))
        assert stat.S_IMODE(owner.path.stat().st_mode) == 0o600
        assert devcontainer_launch.launch_main() == 0
        owned_command, child_env = calls[-1]
        assert owned_command[owned_command.index("--override-config") + 1] == str(
            owner.path
        )
        assert b"scripts/devcontainer-smoke.sh" not in owner.path.read_bytes()
        assert b'"waitFor": "postStartCommand"' in owner.path.read_bytes()
        assert b"scripts/devcontainer-smoke.sh" in source_path.read_bytes()
        assert b"onCreateCommand" in owner.path.read_bytes()
        assert b"postStartCommand" in owner.path.read_bytes()
        assert OVERRIDE_PATH_ENV not in child_env
        assert OWNER_FD_ENV not in child_env

    assert source_path.read_bytes() == original
    assert not owner.path.exists()
    assert devcontainer_launch.launch_main() == 2
    assert len(calls) == 3


def test_override_rejects_path_without_a_live_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An environment path alone cannot skip direct-up lifecycle smoke."""
    workspace = _workspace(tmp_path, monkeypatch)
    monkeypatch.setenv(OVERRIDE_PATH_ENV, str(workspace / ".devcontainer" / "x"))
    monkeypatch.delenv(OWNER_FD_ENV, raising=False)
    assert devcontainer_launch.launch_main() == 2


def test_override_rejects_tampered_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A live descriptor does not authorize a modified override document."""
    workspace = _workspace(tmp_path, monkeypatch)
    with active_sync_override(workspace) as owner:
        monkeypatch.setenv(OVERRIDE_PATH_ENV, str(owner.path))
        monkeypatch.setenv(OWNER_FD_ENV, str(owner.owner_fd))
        owner.path.write_text("{}", encoding="utf-8")
        assert devcontainer_launch.launch_main() == 2
