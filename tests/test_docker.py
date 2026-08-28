# Copyright (c) 2026 Raymond Manaloto
"""Tests for host-side devcontainer SSH runtime preparation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import docker


def _completed(
    args: list[str], returncode: int = 0, stdout: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, "")


def test_agent_keys_use_launchd_socket_when_codex_omits_agent_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A GUI child without SSH_AUTH_SOCK recovers the user's launchd agent."""
    calls: list[tuple[list[str], dict[str, str] | None]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        env = kwargs.get("env")
        calls.append((args, env if isinstance(env, dict) else None))
        if args[0] == "/bin/launchctl":
            return _completed(args, stdout="/private/tmp/launchd-agent.sock\n")
        if isinstance(env, dict) and env.get("SSH_AUTH_SOCK"):
            return _completed(args, stdout="ssh-ed25519 public-key comment\n")
        return _completed(args, returncode=2)

    monkeypatch.setattr(docker.sys, "platform", "darwin")
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)
    monkeypatch.setenv("DOTFILES_HOST_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(docker.subprocess, "run", fake_run)

    result = docker.initialize_host_ssh_runtime()
    assert result["authorized_keys"] == "1"
    assert (tmp_path / "authorized_keys").read_text() == (
        "ssh-ed25519 public-key comment\n"
    )
    assert calls[-1][1] is not None
    assert calls[-1][1]["SSH_AUTH_SOCK"] == "/private/tmp/launchd-agent.sock"


def test_hostile_launchd_output_is_not_accepted_as_an_agent_socket(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Launchd output must be one absolute path, never command-shaped input."""
    calls: list[list[str]] = []

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[0] == "/bin/launchctl":
            return _completed(args, stdout="relative.sock\nsecond-line\n")
        return _completed(args, returncode=2)

    monkeypatch.setattr(docker.sys, "platform", "darwin")
    monkeypatch.setenv("DOTFILES_HOST_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(docker.subprocess, "run", fake_run)
    previous = tmp_path / "authorized_keys"
    previous.write_text("ssh-ed25519 previous-key comment\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="No SSH agent public keys"):
        docker.initialize_host_ssh_runtime()
    assert previous.read_text(encoding="utf-8") == (
        "ssh-ed25519 previous-key comment\n"
    )
    assert calls == [
        ["ssh-add", "-L"],
        ["/bin/launchctl", "getenv", "SSH_AUTH_SOCK"],
    ]


def test_loaded_inherited_agent_never_queries_launchd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An explicit working agent remains authoritative on every platform."""

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args[0] == "/bin/launchctl":
            message = "launchd must not replace a working agent"
            raise AssertionError(message)
        return _completed(args, stdout="ssh-ed25519 inherited-key comment\n")

    monkeypatch.setattr(docker.sys, "platform", "darwin")
    monkeypatch.setenv("DOTFILES_HOST_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(docker.subprocess, "run", fake_run)

    result = docker.initialize_host_ssh_runtime()
    assert result["authorized_keys"] == "1"
    assert (tmp_path / "authorized_keys").read_text() == (
        "ssh-ed25519 inherited-key comment\n"
    )


def test_inbound_probe_uses_recovered_agent_and_requires_exact_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public R1 probe signs through launchd and checks remote whoami."""
    ssh_envs: list[dict[str, str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        env = kwargs.get("env")
        if args[0] == "/bin/launchctl":
            return _completed(args, stdout="/private/tmp/launchd-agent.sock\n")
        if args[0] == "ssh-add":
            if isinstance(env, dict) and env.get("SSH_AUTH_SOCK"):
                return _completed(args, stdout="ssh-ed25519 public-key comment\n")
            return _completed(args, returncode=2)
        assert isinstance(env, dict)
        ssh_envs.append(env)
        return _completed(args, stdout="container-name\nrmanaloto\n")

    monkeypatch.setattr(docker.sys, "platform", "darwin")
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)
    monkeypatch.setattr(docker.subprocess, "run", fake_run)

    output = docker.verify_host_ssh_inbound(28050, "rmanaloto")
    assert output.endswith("rmanaloto\n")
    assert ssh_envs[0]["SSH_AUTH_SOCK"] == "/private/tmp/launchd-agent.sock"


def test_inbound_probe_rejects_wrong_remote_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful SSH process cannot pass R1 as a different remote user."""

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args[0] == "ssh-add":
            return _completed(args, stdout="ssh-ed25519 inherited-key comment\n")
        return _completed(args, stdout="container-name\nroot\n")

    monkeypatch.setattr(docker.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Inbound SSH verification failed"):
        docker.verify_host_ssh_inbound(28050, "rmanaloto")


def test_down_stops_and_removes_ids_from_teardown_container_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """#800 F3: down() must use the arch-scoped teardown lookup.

    Post-#677 containers carry no ``devcontainer.local_folder`` label
    (``--id-label`` replaces the CLI's inferred label set), so the old
    bare-folder filter this verb used stopped matching anything.
    ``resolve_names`` is stubbed out because ``teardown_container_ids`` is
    stubbed to ignore its argument here — the real value is exercised by
    ``devcontainer_names``'s own tests.
    """
    monkeypatch.setattr(docker.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(docker, "resolve_names", lambda **_kw: object())
    monkeypatch.setattr(docker, "teardown_container_ids", lambda _names: ["c1", "c2"])
    calls: list[list[str]] = []

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return _completed(args)

    monkeypatch.setattr(docker.subprocess, "run", fake_run)

    docker.DevContainerManager(tmp_path).down()

    assert calls == [
        ["/usr/bin/docker", "stop", "c1"],
        ["/usr/bin/docker", "rm", "-f", "c1"],
        ["/usr/bin/docker", "stop", "c2"],
        ["/usr/bin/docker", "rm", "-f", "c2"],
    ]


def test_down_with_no_containers_issues_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An empty teardown list must not shell out to docker at all."""
    monkeypatch.setattr(docker.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(docker, "resolve_names", lambda **_kw: object())
    monkeypatch.setattr(docker, "teardown_container_ids", lambda _names: [])

    def fake_run(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        msg = "no subprocess should run when there is nothing to tear down"
        raise AssertionError(msg)

    monkeypatch.setattr(docker.subprocess, "run", fake_run)

    docker.DevContainerManager(tmp_path).down()
