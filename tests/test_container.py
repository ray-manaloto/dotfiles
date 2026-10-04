# Copyright (c) 2026 Raymond Manaloto
"""Tests for the devcontainer freshness gate (dotfiles_setup.container)."""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import container, host_lock, sync

_WORKSPACE = Path("/workspaces-host/dotfiles")


def _cp(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


@dataclasses.dataclass(kw_only=True)
class _FakeDocker:
    """Routes container._run calls to canned outputs keyed by the command shape."""

    container_id: str | None = "cafef00dbeef"
    bind_source: str | None = str(_WORKSPACE)
    smoke_rc: int = 0
    smoke_out: str = "=== All smoke checks passed ===\n"
    head: str = "e61b3ea0"
    branch: str = "main"
    extra_container_ids: tuple[str, ...] = ()
    docker_ps_command: list[str] | None = None
    smoke_command: list[str] | None = None

    def __call__(
        self, cmd: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if cmd[:2] == ["git", "-C"]:
            return _cp((self.head if cmd[-1] == "HEAD" else self.branch) + "\n")
        if cmd[:3] == ["docker", "ps", "-q"]:
            self.docker_ps_command = cmd
            ids = (
                (self.container_id,) if self.container_id else ()
            ) + self.extra_container_ids
            return _cp("".join(f"{container_id}\n" for container_id in ids))
        if cmd[:2] == ["docker", "inspect"]:
            if self.bind_source is None:
                return _cp("[]")
            payload = [
                {
                    "Type": "bind",
                    "Source": self.bind_source,
                    "Destination": "/workspaces/dotfiles",
                }
            ]
            return _cp(json.dumps(payload))
        if cmd[:2] == ["docker", "exec"]:
            self.smoke_command = cmd
            return _cp(self.smoke_out, returncode=self.smoke_rc)
        msg = f"unexpected command: {cmd}"
        raise AssertionError(msg)


def _names(checks: list[container.Check]) -> dict[str, container.Check]:
    return {c.name: c for c in checks}


@pytest.mark.parametrize(
    ("platform", "arch_label"),
    [
        ("linux/amd64/v2", "label=dotfiles.arch=amd64"),
        ("linux/arm64/v8", "label=dotfiles.arch=arm64"),
    ],
)
def test_all_green_when_fresh(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    arch_label: str,
) -> None:
    """A running, bind-mounted container with green smoke passes all checks."""
    monkeypatch.setenv("DOTFILES_PLATFORM", platform)
    runner = _FakeDocker()
    monkeypatch.setattr(container, "_run", runner)
    checks = container.verify_latest(_WORKSPACE)

    assert all(c.ok for c in checks)
    assert {"container-running", "workspace-bind-mount", "smoke-tiers-1-3"} == set(
        _names(checks)
    )
    assert runner.docker_ps_command is not None
    assert "label=dotfiles.workspace=" in " ".join(runner.docker_ps_command)
    assert arch_label in runner.docker_ps_command
    assert runner.smoke_command is not None
    assert runner.smoke_command == [
        "docker",
        "exec",
        "--workdir",
        "/workspaces/dotfiles",
        "cafef00dbeef",
        "scripts/devcontainer-smoke.sh",
    ]


def test_duplicate_exact_identity_fails_before_inspect_or_smoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two containers with the same workspace+arch labels are ambiguous."""
    runner = _FakeDocker(extra_container_ids=("decafbadcafe",))
    monkeypatch.setattr(container, "_run", runner)

    checks = container.verify_latest(_WORKSPACE)

    assert checks == [
        container.Check(
            "container-identity-unique",
            ok=False,
            detail=(
                "2 running containers share this workspace+arch identity; "
                "run `mise run down` and start one explicitly"
            ),
        )
    ]
    assert runner.smoke_command is None


def test_no_container_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no running container, only the (failed) container-running check returns."""
    monkeypatch.setattr(container, "_run", _FakeDocker(container_id=None))
    checks = container.verify_latest(_WORKSPACE)

    assert len(checks) == 1
    assert checks[0].name == "container-running"
    assert checks[0].ok is False


def test_not_bind_mounted_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """A container that does not bind-mount the workspace fails source liveness."""
    monkeypatch.setattr(container, "_run", _FakeDocker(bind_source="/some/other/path"))

    assert (
        _names(container.verify_latest(_WORKSPACE))["workspace-bind-mount"].ok is False
    )


def test_stale_base_fails_via_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale base (smoke identity FAIL) hard-fails smoke-tiers-1-3."""
    monkeypatch.setattr(
        container,
        "_run",
        _FakeDocker(
            smoke_rc=1,
            smoke_out=(
                "[tier1] image identity\n  FAIL: in-image mise config X != repo Y\n"
            ),
        ),
    )
    smoke = _names(container.verify_latest(_WORKSPACE))["smoke-tiers-1-3"]

    assert smoke.ok is False
    assert "FAIL" in smoke.detail
    assert "dev-rebuild" in smoke.detail


def test_run_smoke_false_skips_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_smoke=False omits the smoke check (for a fast pre-check)."""
    monkeypatch.setattr(container, "_run", _FakeDocker())

    assert "smoke-tiers-1-3" not in _names(
        container.verify_latest(_WORKSPACE, run_smoke=False)
    )


def test_main_returns_1_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """verify_latest_main returns 1 when any check fails."""
    monkeypatch.setattr(container, "_run", _FakeDocker(smoke_rc=1))

    assert container.verify_latest_main(_WORKSPACE) == 1


def test_main_returns_0_when_all_green(monkeypatch: pytest.MonkeyPatch) -> None:
    """verify_latest_main returns 0 when every check passes."""
    monkeypatch.setattr(container, "_run", _FakeDocker())

    assert container.verify_latest_main(_WORKSPACE) == 0


@pytest.fixture
def smoke_system(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Real subprocess boundaries and isolated state; never reach Docker."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for command in (
        ["git", "init", "-q", str(workspace)],
        [
            "git",
            "-C",
            str(workspace),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
    ):
        subprocess.run(command, check=True, capture_output=True)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    docker = bindir / "docker"
    docker.write_text(
        f"#!{sys.executable}\n"
        + textwrap.dedent(r"""
        import fcntl
        import json
        import os
        import sys
        import time
        from pathlib import Path

        args = sys.argv[1:]
        if args[0] == "ps":
            print("cafef00dbeef\trunning\tfixture"
                  if "--format" in args else "cafef00dbeef")
        elif args[0] == "buildx":
            print(json.dumps("sha256:fixture"))
        elif args[:2] == ["image", "inspect"]:
            if args[-1] == "{{json .RepoDigests}}":
                print(json.dumps(["ghcr.io/ray-manaloto/dotfiles-devcontainer@sha256:fixture"]))
            else:
                print("sha256:fixture-image")
        elif args[0] == "inspect":
            if args[-1] == "{{json .Mounts}}":
                print(json.dumps([{"Type": "bind",
                                   "Source": os.environ["SMOKE_WORKSPACE"],
                                   "Destination": "/workspaces/fixture"}]))
            else:
                print("sha256:fixture-overlay")
        elif args[0] == "exec":
            path = Path(os.environ["DOTFILES_LOCK_DIR"]) / "heavy-gate.lock"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a+") as handle:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    state = "busy"
                else:
                    state = "free"
            Path(os.environ["SMOKE_LOCK_PROBE"]).write_text(state)
            if os.environ.get("SMOKE_MODE") == "timeout":
                output = os.environ.get(
                    "SMOKE_OUTPUT", "starting suite\nstill running\n")
                os.write(1, output.encode())
                os.write(2, b"partial stderr\xff\n")
                time.sleep(5)
            print("FAIL: wrong image identity"
                  if os.environ.get("SMOKE_MODE") == "failure"
                  else "devcontainer smoke: tiers 1-3 OK")
            sys.exit(1 if os.environ.get("SMOKE_MODE") == "failure" else 0)
        else:
            raise SystemExit(f"unexpected docker args: {args}")
    """)
    )
    docker.chmod(0o755)
    # Fail closed if a regression tries a lifecycle operation.
    mise = bindir / "mise"
    mise.write_text("#!/bin/sh\necho 'unexpected lifecycle operation' >&2\nexit 99\n")
    mise.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
    monkeypatch.setenv("DOTFILES_PLATFORM", "linux/amd64")
    monkeypatch.setenv("SMOKE_WORKSPACE", str(workspace))
    monkeypatch.setenv("SMOKE_LOCK_PROBE", str(tmp_path / "lock-probe"))
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1")
    monkeypatch.setenv("DOTFILES_HEAVY_GATE_WAIT", "0")
    return workspace


@pytest.mark.parametrize("entrypoint", ["checks", "verify", "sync"])
def test_smoke_timeout_public_paths(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    entrypoint: str,
) -> None:
    """A real sleeping docker becomes a bounded Check/rc, never a traceback."""
    monkeypatch.setenv("SMOKE_MODE", "timeout")
    if entrypoint == "checks":
        check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
        assert check.ok is False
        detail = check.detail
    elif entrypoint == "verify":
        assert container.verify_latest_main(smoke_system) == 1
        detail = capsys.readouterr().out
    else:
        assert sync.sync_main(smoke_system, sync.SyncOptions(tag="fixture")) == 1
        detail = capsys.readouterr().out
        assert "sync: verification failed" in detail
    assert "smoke timed out after 0.1 seconds" in detail
    assert "still running" in detail
    assert "partial stderr" in detail
    assert "dev-rebuild" not in detail
    assert "Traceback" not in detail
    assert Path(os.environ["SMOKE_LOCK_PROBE"]).read_text() == "busy"
    with host_lock.held(host_lock.HEAVY_GATE, "after timeout", wait_s=0):
        pass


@pytest.mark.parametrize("mode", ["success", "failure"])
def test_smoke_slot_held_and_released(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    """The fake executable independently attempts flock while smoke runs."""
    monkeypatch.setenv("SMOKE_MODE", mode)
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is (mode == "success")
    assert Path(os.environ["SMOKE_LOCK_PROBE"]).read_text() == "busy"
    if mode == "failure":
        assert "wrong image identity" in check.detail
        assert "dev-rebuild" in check.detail
    with host_lock.held(host_lock.HEAVY_GATE, "after smoke", wait_s=0):
        pass


@pytest.mark.parametrize("configured", ["bad", "nan", "inf", "-inf", "0", "-1", ""])
def test_smoke_invalid_timeout_uses_bounded_default(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
    configured: str,
) -> None:
    """Malformed overrides must not become immediate/unbounded deadlines."""
    observed: list[object] = []

    def recording[**P, R](run: Callable[P, R]) -> Callable[P, R]:
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if args and isinstance(args[0], list) and args[0][:2] == ["docker", "exec"]:
                observed.append(kwargs.get("timeout"))
            return run(*args, **kwargs)

        return wrapped

    monkeypatch.setattr(subprocess, "run", recording(subprocess.run))
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", configured)
    assert container.verify_latest_main(smoke_system) == 0
    assert observed == [1800.0]


def test_smoke_timeout_output_is_bounded(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMOKE_MODE", "timeout")
    monkeypatch.setenv("SMOKE_OUTPUT", "old line\n" + "x" * 6000 + "\nlast line")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    assert "last line" in check.detail
    assert "old line" not in check.detail
    assert len(check.detail) < 2100


def test_smoke_slot_contention_and_descendant_reentry(
    smoke_system: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Public heavy-gate command owns the slot; its child smoke reenters."""
    ready = tmp_path / "holder-ready"
    release = tmp_path / "holder-release"
    src = Path(__file__).parent.parent / "python" / "src"
    monkeypatch.setenv("PYTHONPATH", str(src))
    child = (
        "import sys, time; from pathlib import Path; "
        "from dotfiles_setup.container import verify_latest_main; "
        f"Path({str(ready)!r}).touch(); "
        f"release = Path({str(release)!r}); "
        "exec('while not release.exists(): time.sleep(0.01)'); "
        f"raise SystemExit(verify_latest_main(Path({str(smoke_system)!r})))"
    )
    command = [
        sys.executable,
        "-c",
        (
            "from dotfiles_setup.host_lock import host_lock_main; "
            "raise SystemExit(host_lock_main())"
        ),
        "run",
        "--label",
        "fixture-holder",
        "--",
        sys.executable,
        "-c",
        child,
    ]
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as holder:
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert ready.exists()
            assert sync.sync_main(smoke_system, sync.SyncOptions(tag="fixture")) == 1
            detail = capsys.readouterr().out
            assert "smoke host heavy-slot wait timed out" in detail
            assert "fixture-holder" in detail
            assert "dev-rebuild" not in detail
            assert not Path(os.environ["SMOKE_LOCK_PROBE"]).exists()
            release.touch()
            stdout, stderr = holder.communicate(timeout=5)
            assert holder.returncode == 0, stderr
            assert "PASS  smoke-tiers-1-3" in stdout
        finally:
            release.touch()
            holder.communicate(timeout=5)
    with host_lock.held(host_lock.HEAVY_GATE, "after holder", wait_s=0):
        pass
