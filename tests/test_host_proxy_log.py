"""Regression test: host SSH proxy log is wired to stdout/stderr.

Gating test for PR 1. Proves Popen is invoked with append-mode log fd and
stderr merged into stdout, so BRIDGE_UNREACHABLE writes land in the log file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from dotfiles_setup import docker as docker_mod


def test_host_ssh_proxy_log_nonzero_after_single_connection(tmp_path: Path) -> None:
    """initialize_host_ssh_runtime must open log in append mode and wire stderr=STDOUT."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    fake_sock = tmp_path / "ssh-agent.sock"
    fake_sock.touch()

    observed_kwargs: dict[str, object] = {}
    observed_mode: dict[str, str] = {}

    real_open = Path.open

    def spy_open(
        self: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> object:
        if self.name == "host-ssh-proxy.log":
            observed_mode["mode"] = mode
        return real_open(
            self,
            mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    fake_proc = MagicMock()
    fake_proc.pid = 12345

    def fake_popen(*args: object, **kwargs: object) -> MagicMock:
        observed_kwargs.update(kwargs)
        return fake_proc

    with (
        patch.object(docker_mod, "host_state_dir", return_value=state_dir),
        patch.object(docker_mod, "_collect_public_keys_from_agent", return_value=[]),
        patch.object(
            docker_mod, "_resolve_host_ssh_auth_sock", return_value=str(fake_sock)
        ),
        patch.object(docker_mod, "_choose_host_ssh_proxy_port", return_value=49999),
        patch.object(docker_mod, "_wait_for_tcp_port", return_value=True),
        patch.object(Path, "open", spy_open),
        patch("dotfiles_setup.docker.subprocess.Popen", side_effect=fake_popen),
    ):
        docker_mod.initialize_host_ssh_runtime()

    assert observed_mode.get("mode") == "a", (
        f"expected append mode, got {observed_mode.get('mode')!r}"
    )
    assert observed_kwargs.get("stderr") is subprocess.STDOUT, (
        "stderr must be merged into stdout so BRIDGE_UNREACHABLE lands in log"
    )
    assert observed_kwargs.get("stdout") is not None
