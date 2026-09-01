# Copyright (c) 2026 Raymond Manaloto
"""Tests for host-side devcontainer SSH runtime preparation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import docker
from dotfiles_setup.devcontainer_names import DevcontainerNames, resolve_names


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


def test_down_degrades_gracefully_when_docker_daemon_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The legacy down verb reports a failed lookup without stop/rm attempts."""
    monkeypatch.setattr(docker.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(docker, "resolve_names", lambda **_kw: object())

    def failed_lookup(_names: object) -> list[str]:
        raise subprocess.CalledProcessError(1, "docker")

    monkeypatch.setattr(docker, "teardown_container_ids", failed_lookup)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        docker.subprocess,
        "run",
        lambda args, **_kw: calls.append(args) or _completed(args),
    )

    with (
        caplog.at_level("ERROR", logger="dotfiles_setup.docker"),
        pytest.raises(SystemExit) as excinfo,
    ):
        docker.DevContainerManager(tmp_path).down()

    assert excinfo.value.code == 1
    assert calls == []
    assert "could not list devcontainers" in caplog.text


# --------------------------------------------------- #893 scoped secrets file


def _names(workspace: str, platform: str = "linux/amd64/v2") -> DevcontainerNames:
    return resolve_names(workspace=Path(workspace), user="u", platform=platform, env={})


def test_env_file_differs_per_workspace_and_per_arch(tmp_path: Path) -> None:
    """#893: the secrets path must carry BOTH scoping dimensions.

    Control arm for the uniqueness claim: one sample cannot show a path is
    unique, so this resolves three — two clones and two arches — and requires
    all three to differ. Before #893 all three were `doppler.env`.
    """
    a_amd = docker.doppler_env_file(_names("/ws/clone-a"), tmp_path)
    b_amd = docker.doppler_env_file(_names("/ws/clone-b"), tmp_path)
    a_arm = docker.doppler_env_file(_names("/ws/clone-a", "linux/arm64/v8"), tmp_path)

    assert len({a_amd, b_amd, a_arm}) == 3
    assert a_amd.parent == tmp_path
    assert a_amd.name.startswith("doppler-")
    assert a_amd.name.endswith(".env")


def test_secrets_download_writes_atomically_and_leaves_no_temp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The env file appears whole, and the temp file never survives."""
    monkeypatch.setattr(
        docker.subprocess,
        "run",
        lambda args, **_kw: _completed(args, stdout="A=1\nB=2\n"),
    )
    names = _names("/ws/clone-a")
    path = docker.download_doppler_env(names, tmp_path, env={})

    assert path.read_text() == "A=1\nB=2\n"
    assert list(tmp_path.glob("*.tmp")) == []


def test_two_clones_get_separate_secrets_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """#893 REGRESSION ARM: the cross-clone overwrite, driven end to end.

    Clone A's project resolves to secrets `A=1`; clone B's to `B=2`. Before
    #893 both wrote `doppler.env`, so B's download replaced A's file and A's
    container was started from B's secrets — silently, since `--env-file`
    reads whatever is there.

    Two workspaces are load-bearing here: with one clone the old code and the
    new code are indistinguishable.
    """
    secrets = {"proj-a": "A=1\n", "proj-b": "B=2\n"}

    def fake_run(args: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        project = args[args.index("--project") + 1]
        return _completed(args, stdout=secrets[project])

    monkeypatch.setattr(docker.subprocess, "run", fake_run)

    a = docker.download_doppler_env(
        _names("/ws/clone-a"), tmp_path, env={"DOPPLER_PROJECT": "proj-a"}
    )
    b = docker.download_doppler_env(
        _names("/ws/clone-b"), tmp_path, env={"DOPPLER_PROJECT": "proj-b"}
    )

    assert a != b
    assert a.read_text() == "A=1\n"
    assert b.read_text() == "B=2\n"


def test_empty_download_fails_the_bring_up(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The old `&& [ -s … ] &&` guard survives as an explicit error.

    An empty env file reaching `--env-file` is a container with no secrets
    and no complaint, which is why the shell chain guarded it.
    """
    monkeypatch.setattr(
        docker.subprocess, "run", lambda args, **_kw: _completed(args, stdout="   \n")
    )
    with pytest.raises(docker.SecretsDownloadError):
        docker.download_doppler_env(_names("/ws/clone-a"), tmp_path, env={})


def test_failed_download_fails_the_bring_up(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        docker.subprocess,
        "run",
        lambda args, **_kw: _completed(args, returncode=1),
    )
    with pytest.raises(docker.SecretsDownloadError):
        docker.download_doppler_env(_names("/ws/clone-a"), tmp_path, env={})
