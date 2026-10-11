# Copyright (c) 2026 Raymond Manaloto
"""Tests for the devcontainer freshness gate (dotfiles_setup.container)."""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import shutil
import signal
import subprocess
import sys
import textwrap
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import container, host_lock, sync

_WORKSPACE = Path("/workspaces-host/dotfiles")


@pytest.fixture(autouse=True)
def fake_workspace_stream(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Route only the synthetic workspace through the existing fake Docker."""
    original_dir = container.process_stream.new_run_dir
    original_stream = container.process_stream.run_streamed

    def run_dir(workspace: Path, label: str) -> Path:
        if workspace != _WORKSPACE:
            return original_dir(workspace, label)
        result = tmp_path / f"{label}-{uuid.uuid4().hex}"
        result.mkdir(mode=0o700)
        return result

    def streamed(
        command: Sequence[str],
        *,
        cwd: Path,
        log_path: Path,
        timeout_s: float | None = None,
        pass_fds: tuple[int, ...] = (),
    ) -> container.process_stream.StreamResult:
        if cwd != _WORKSPACE:
            return original_stream(
                command,
                cwd=cwd,
                log_path=log_path,
                timeout_s=timeout_s,
                pass_fds=pass_fds,
            )
        completed = vars(container)["_run"](list(command))
        log_path.write_text(completed.stdout or "")
        stdout_path = log_path.with_name("stdout.log")
        stderr_path = log_path.with_name("stderr.log")
        stdout_path.write_text(completed.stdout or "")
        stderr_path.write_text(completed.stderr or "")
        return container.process_stream.StreamResult(
            returncode=completed.returncode,
            timed_out=False,
            duration_s=0.0,
            log_path=log_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

    monkeypatch.setattr(container.process_stream, "new_run_dir", run_dir)
    monkeypatch.setattr(container.process_stream, "run_streamed", streamed)


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
            if "/usr/bin/python3" in cmd:
                return _cp('{"pids": [], "reaped": 0}')
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
    assert runner.smoke_command[:3] == ["docker", "exec", "-e"]
    uuid.UUID(runner.smoke_command[3].removeprefix("DOTFILES_SMOKE_RUN_ID="))
    assert runner.smoke_command[4:] == [
        "--workdir",
        "/workspaces/dotfiles",
        "cafef00dbeef",
        "timeout",
        "--kill-after=30s",
        "1800s",
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
def smoke_system(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Real subprocess boundaries and isolated state; never reach Docker."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    bindir = tmp_path / "bin"
    bindir.mkdir()
    git = shutil.which("git", path=os.defpath) or shutil.which("git")
    assert git is not None, "smoke fixture requires git on os.defpath or PATH"
    (bindir / "git").symlink_to(git)
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
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
        root = Path(os.environ["SMOKE_STATE"])
        identity_file = root / "identity"
        identity = (json.loads(identity_file.read_text()) if identity_file.exists()
                    else {"id": "cafef00dbeef", "dest": "/workspaces/fixture"})
        if args[0] in {"ps", "inspect"}:
            with (root / "identity-queries").open("a") as log:
                log.write(json.dumps(args) + "\n")
        if args[0] == "ps":
            print(identity["id"] + "\trunning\tfixture"
                  if "--format" in args else identity["id"])
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
                                   "Destination": identity["dest"]}]))
            else:
                print("sha256:fixture-overlay")
        elif args[0] == "exec":
            import shutil
            import signal
            import subprocess

            root = Path(os.environ["SMOKE_STATE"])
            path = Path(os.environ["DOTFILES_LOCK_DIR"]) / "heavy-gate.lock"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a+") as handle:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    state = "busy"
                else:
                    state = "free"
            with (root / "calls").open("a") as log:
                log.write(json.dumps({"args": args, "slot": state}) + "\n")
            proc = root / "proc"
            proc.mkdir(exist_ok=True)
            if "/usr/bin/python3" in args:
                program = args[args.index("-c") + 1]
                if os.environ.get("SMOKE_PROBE_ERROR") or (
                    args[-2] == "reap" and os.environ.get("SMOKE_REAP_ERROR")
                ):
                    form = os.environ.get("SMOKE_ERROR_PROGRAM")
                    inline = (repr(program) if form == "repr"
                              else json.dumps(program) if form == "json"
                              else program if form else "")
                    print(os.environ.get("SMOKE_PROCESS_ERROR", "proc unavailable")
                          + inline,
                          file=sys.stderr)
                    sys.exit(2)
                sys.argv = ["probe", *args[-2:]]
                # Execute the shipped scanner against a Docker-boundary proc sandbox.
                # Actual signal delivery is retained; proc disappearance follows kill.
                if os.environ.get("SMOKE_PROTECTED"):
                    for pid, parent in [(os.getpid(), os.getppid()), (os.getppid(), 0)]:
                        row = proc / str(pid)
                        row.mkdir(exist_ok=True)
                        (row / "stat").write_text(f"{pid} (probe) S {parent}")
                        (row / "cmdline").write_bytes(b"devcontainer-smoke.sh")
                        (row / "environ").write_bytes(
                            f"DOTFILES_SMOKE_RUN_ID={args[-1]}".encode() + b"\0")
                native_read_bytes = Path.read_bytes
                def read_bytes(path):
                    if (os.environ.get("SMOKE_UNREADABLE") and
                            path.name == "cmdline" and path.parent.name == "999999"):
                        raise PermissionError("isolated proc command read denied")
                    return native_read_bytes(path)
                Path.read_bytes = read_bytes
                native_kill = os.kill
                pidfds = {}
                def pidfd_open(pid):
                    fd = os.open(proc / str(pid) / "environ", os.O_RDONLY)
                    pidfds[fd] = pid
                    if os.environ.get("SMOKE_PID_RECYCLED"):
                        (proc / str(pid) / "environ").write_bytes(b"OTHER_RUN=1")
                    return fd
                def send_signal(fd, sig):
                    pid = pidfds[fd]
                    if pid != int((root / "child-pid").read_text()):
                        message = f"attempt to kill protected/foreign pid {pid}"
                        raise RuntimeError(message)
                    if os.environ.get("SMOKE_SURVIVOR"):
                        return
                    native_kill(pid, sig)
                    shutil.rmtree(proc / str(pid))
                os.pidfd_open = pidfd_open
                signal.pidfd_send_signal = send_signal
                exec(program.replace('Path("/proc")', f"Path({str(proc)!r})"))
                sys.exit(0)
            Path(os.environ["SMOKE_LOCK_PROBE"]).write_text(state)
            inherited = []
            for fd in range(3, 256):
                try:
                    if os.fstat(fd).st_ino == path.stat().st_ino:
                        inherited.append(fd)
                except OSError:
                    pass
            (root / "fds").write_text(json.dumps(inherited))
            marker = next(arg.split("=", 1)[1] for arg in args
                          if arg.startswith("DOTFILES_SMOKE_RUN_ID="))
            (root / "marker").write_text(marker)
            os.environ["DOTFILES_SMOKE_RUN_ID"] = marker
            mode = os.environ.get("SMOKE_MODE", "success")
            if mode in {"timeout", "inner124", "inner137", "inner_group"}:
                # GNU timeout counts command startup within its budget.
                # Do not add a second full budget after the child handshake.
                inner_deadline = time.monotonic() + float(args[-2][:-1])
                child_ready = root / "child-ready"
                grand_path = root / "grand-pid"
                setup = ""
                if mode == "inner_group":
                    setup = (
                        "import subprocess, sys; "
                        "grand = subprocess.Popen([sys.executable, '-c', "
                        f"'import time; time.sleep(60)', {str(grand_path)!r}]); "
                        f"Path({str(grand_path)!r}).write_text(str(grand.pid)); "
                    )
                child = subprocess.Popen(
                    [sys.executable, "-c",
                     "import time; from pathlib import Path; " + setup +
                     f"Path({str(child_ready)!r}).touch(); time.sleep(60)"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                deadline = time.monotonic() + 20
                while not child_ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                if not child_ready.exists():
                    raise SystemExit("child handshake failed")
                row = proc / str(child.pid)
                row.mkdir()
                (row / "stat").write_text(f"{child.pid} (smoke child) S 0")
                (row / "cmdline").write_bytes(b"uv\0pytest\0")
                (row / "environ").write_bytes(
                    f"DOTFILES_SMOKE_RUN_ID={marker}".encode() + b"\0")
                (root / "child-pid").write_text(str(child.pid))
                (root / "ready").touch()
                os.write(1, os.environ.get(
                    "SMOKE_OUTPUT", "starting suite\nstill running\n").encode())
                os.write(2, b"old stderr warning\xff\n")
                if mode == "timeout":
                    time.sleep(60)
                inner_delay = os.environ.get("SMOKE_INNER_DELAY")
                time.sleep(float(inner_delay) if inner_delay is not None else
                           max(0, inner_deadline - time.monotonic()))
                if mode == "inner_group" and "timeout" in args:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=20)
                    shutil.rmtree(row)
                sys.exit(137 if mode == "inner137" else 124)
            stdout = os.environ.get("SMOKE_OUTPUT", "devcontainer smoke: tiers 1-3 OK")
            stderr = os.environ.get("SMOKE_STDERR", "")
            print("FAIL: wrong image identity" if mode == "failure" else stdout)
            print(stderr, file=sys.stderr)
            sys.exit(1 if mode in {"failure", "diagnostic"} else 0)
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
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("SMOKE_STATE", str(state))
    monkeypatch.setenv("DOTFILES_LOCK_DIR", str(tmp_path / "locks"))
    monkeypatch.delenv("DOTFILES_LOCK_HOLDER_HEAVY_GATE", raising=False)
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "30")
    monkeypatch.setenv("DOTFILES_HEAVY_GATE_WAIT", "0")
    yield workspace
    for name in ("child-pid", "grand-pid"):
        child_pid = state / name
        if child_pid.exists():
            pid = child_pid.read_text()
            command = subprocess.run(
                ["ps", "-p", pid, "-o", "command="],
                check=False,
                capture_output=True,
                text=True,
            )
            if str(state) in command.stdout:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(int(pid), signal.SIGKILL)


def test_smoke_fixture_uses_path_when_defpath_has_no_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """A mise-provided PATH git still initializes the isolated public gate."""
    git = shutil.which("git", path=os.defpath) or shutil.which("git")
    assert git is not None, "regression control requires a working git"
    path_bin = tmp_path / "path-git"
    path_bin.mkdir()
    (path_bin / "git").symlink_to(git)
    monkeypatch.setenv("PATH", f"{path_bin}:{os.environ['PATH']}")
    monkeypatch.setattr(os, "defpath", str(tmp_path / "empty-default-path"))
    assert shutil.which("git", path=os.defpath) is None
    workspace = request.getfixturevalue("smoke_system")
    assert container.verify_latest_main(workspace) == 0


def test_completed_failure_reports_stderr_only_cause(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Progress on stdout must not hide a stderr-only mise panic."""
    monkeypatch.setenv("SMOKE_MODE", "diagnostic")
    monkeypatch.setenv("SMOKE_OUTPUT", "tier 2 starting")
    monkeypatch.setenv("SMOKE_STDERR", "mise Rust panic: src/git.rs:193")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    assert "mise Rust panic: src/git.rs:193" in check.detail


@pytest.mark.parametrize("entrypoint", ["checks", "verify", "sync"])
def test_smoke_timeout_public_paths(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    entrypoint: str,
) -> None:
    """A real sleeping docker becomes a bounded Check/rc, never a traceback."""
    monkeypatch.setenv("SMOKE_MODE", "timeout")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1")
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
    assert "old stderr" not in detail
    assert "reaped 1 in-container processes" in detail
    state = Path(os.environ["SMOKE_STATE"])
    assert (state / "ready").exists()
    assert not (state / "proc" / (state / "child-pid").read_text()).exists()
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
            if args and isinstance(args[0], list) and "timeout" in args[0]:
                observed.append(kwargs.get("timeout_s"))
            return run(*args, **kwargs)

        return wrapped

    monkeypatch.setattr(
        container.process_stream,
        "run_streamed",
        recording(container.process_stream.run_streamed),
    )
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", configured)
    assert container.verify_latest_main(smoke_system) == 0
    assert observed == [1890.0]


def test_smoke_timeout_output_is_bounded(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMOKE_MODE", "timeout")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1")
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
            deadline = time.monotonic() + 30
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
            stdout, stderr = holder.communicate(timeout=30)
            assert holder.returncode == 0, stderr
            assert "PASS  smoke-tiers-1-3" in stdout
        finally:
            release.touch()
            holder.communicate(timeout=30)
    with host_lock.held(host_lock.HEAVY_GATE, "after holder", wait_s=0):
        pass


class _SmokeCall(TypedDict):
    args: list[str]
    slot: str


def _smoke_calls() -> list[_SmokeCall]:
    path = Path(os.environ["SMOKE_STATE"]) / "calls"
    return [json.loads(line) for line in path.read_text().splitlines()]


def _proc_row(root: Path, pid: int, *, command: str, marker: str) -> Path:
    row = root / "proc" / str(pid)
    row.mkdir(parents=True)
    (row / "stat").write_text(f"{pid} (fixture) S 0")
    (row / "cmdline").write_bytes(command.encode() + b"\0")
    (row / "environ").write_bytes(f"DOTFILES_SMOKE_RUN_ID={marker}".encode() + b"\0")
    return row


@pytest.mark.parametrize("mode", ["inner124", "inner137", "inner_group"])
def test_inner_timeout_and_marker_cleanup(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """The inner timeout and reap are visible through the public gate."""
    monkeypatch.setenv("SMOKE_MODE", mode)
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "3")
    monkeypatch.setenv("SMOKE_PROTECTED", "1")
    root = Path(os.environ["SMOKE_STATE"])
    unrelated = _proc_row(root, 999999, command="pytest", marker="other-run")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    assert "smoke timed out after 3 seconds (in-container timeout):" in check.detail
    assert "dev-rebuild" not in check.detail
    expected_reaped = 0 if mode == "inner_group" else 1
    assert f"reaped {expected_reaped} in-container processes" in check.detail
    assert unrelated.exists()
    assert (root / "ready").exists()
    assert not (root / "proc" / (root / "child-pid").read_text()).exists()
    calls = _smoke_calls()
    assert all(call["slot"] == "busy" for call in calls)
    exec_args = next(call["args"] for call in calls if "--workdir" in call["args"])
    assert exec_args[-4:] == [
        "timeout",
        "--kill-after=1s",
        "3s",
        "scripts/devcontainer-smoke.sh",
    ]
    assert calls[-1]["args"][-2] == "reap"
    assert len(json.loads((root / "fds").read_text())) == 1
    if mode == "inner_group":
        grand_pid = (root / "grand-pid").read_text()
        status = subprocess.run(
            ["ps", "-p", grand_pid, "-o", "stat="],
            check=False,
            capture_output=True,
            text=True,
        )
        assert status.returncode != 0 or status.stdout.strip().startswith("Z")


@pytest.mark.parametrize("marker", ["", "other-run"])
@pytest.mark.parametrize(
    "command",
    [
        "/workspaces/scripts/devcontainer-smoke.sh",
        "/bin/bash\0scripts/devcontainer-smoke.sh",
        "/bin/sh\0/workspaces/scripts/devcontainer-smoke.sh",
    ],
)
def test_preflight_refuses_existing_smoke_without_killing(
    smoke_system: Path, marker: str, command: str
) -> None:
    root = Path(os.environ["SMOKE_STATE"])
    row = _proc_row(root, 999999, command=command, marker=marker)
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    assert check.detail == "smoke already running in cafef00dbeef (pids 999999)"
    assert row.exists()
    assert not (root / "marker").exists()
    assert len(_smoke_calls()) == 1
    assert _smoke_calls()[0]["args"][-2] == "probe"


@pytest.mark.parametrize(
    "command",
    [
        "python\0-c\0print('devcontainer-smoke.sh')",
        "agent\0message about scripts/devcontainer-smoke.sh",
        "grep\0devcontainer-smoke.sh",
        "vim\0scripts/devcontainer-smoke.sh",
        "bash\0-c\0echo scripts/devcontainer-smoke.sh",
        "sh\0-c\0echo scripts/devcontainer-smoke.sh",
        "/bin/not-devcontainer-smoke.sh\0scripts/devcontainer-smoke.sh",
    ],
)
def test_preflight_ignores_mentions_of_smoke_script(
    smoke_system: Path, command: str
) -> None:
    root = Path(os.environ["SMOKE_STATE"])
    row = _proc_row(root, 999999, command=command, marker="other-run")
    assert container.verify_latest_main(smoke_system) == 0
    assert row.exists()
    assert (root / "marker").exists()


@pytest.mark.parametrize("mode", ["inner124", "inner137"])
def test_early_timeout_like_exit_reports_rc_and_still_reaps(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """An early inner rc is classified by the injected clock, never wall time.

    Under host load the real fixture round-trip can exceed 0.9 * T, which
    would flip this into the timeout branch (seen at load ~230 under Rosetta).
    """
    readings = iter((0.0, 0.0))
    monkeypatch.setattr(
        container, "time", SimpleNamespace(monotonic=lambda: next(readings))
    )
    monkeypatch.setenv("SMOKE_MODE", mode)
    monkeypatch.setenv("SMOKE_INNER_DELAY", "0")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "3")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    rc = "124" if mode == "inner124" else "137"
    assert f"smoke exited with rc {rc}:" in check.detail
    assert "timed out" not in check.detail
    assert "reaped 1 in-container processes" in check.detail
    assert "old stderr warning" in check.detail


@pytest.mark.parametrize("mode", ["inner124", "inner137"])
@pytest.mark.parametrize("elapsed", [2.699, 2.7])
def test_inner_timeout_classification_at_ninety_percent(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    elapsed: float,
) -> None:
    """The independent clock pins both sides of 0.9 * the three-second bound."""
    readings = iter((0.0, elapsed))
    monkeypatch.setattr(
        container, "time", SimpleNamespace(monotonic=lambda: next(readings))
    )
    monkeypatch.setenv("SMOKE_MODE", mode)
    monkeypatch.setenv("SMOKE_INNER_DELAY", "0")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "3")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    if elapsed == 2.7:
        assert "smoke timed out after 3 seconds (in-container timeout):" in check.detail
    else:
        rc = "124" if mode == "inner124" else "137"
        assert f"smoke exited with rc {rc}:" in check.detail
        assert "timed out" not in check.detail
    assert "reaped 1 in-container processes" in check.detail


@pytest.mark.parametrize("mode", ["timeout", "inner124", "inner137"])
def test_timeout_reports_survivors(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.setenv("SMOKE_MODE", mode)
    monkeypatch.setenv("SMOKE_SURVIVOR", "1")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1" if mode == "timeout" else "3")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    pid = (Path(os.environ["SMOKE_STATE"]) / "child-pid").read_text()
    assert check.ok is False
    assert f"ORPHANS REMAIN: pids {pid}" in check.detail
    assert "dev-rebuild" not in check.detail


def test_smoke_probe_failure_refuses_launch(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SMOKE_PROBE_ERROR", "1")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    assert check.detail == "smoke process probe failed: proc unavailable"
    assert not (Path(os.environ["SMOKE_STATE"]) / "marker").exists()


@pytest.mark.parametrize(
    ("stdout", "stderr", "expected"),
    [
        (
            "early\nfinal one\nfinal two\nfinal three",
            "old stderr warning",
            "final two | final three | old stderr warning",
        ),
        ("FAIL: first\nFAIL: second\nlast", "FAIL: stderr", "FAIL: first"),
        ("last stdout", "FAIL: stderr", "FAIL: stderr"),
        ("", "first\nsecond\nthird\nfourth", "second | third | fourth"),
        (
            "tier 2 starting",
            "mise Rust panic: src/git.rs:193",
            "tier 2 starting | mise Rust panic: src/git.rs:193",
        ),
        ("", "", "smoke failed (no output)"),
    ],
)
def test_completed_smoke_failure_preserves_stderr(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    stderr: str,
    expected: str,
) -> None:
    monkeypatch.setenv("SMOKE_MODE", "diagnostic")
    monkeypatch.setenv("SMOKE_OUTPUT", stdout)
    monkeypatch.setenv("SMOKE_STDERR", stderr)
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    suffix = " — stale base? `mise run dev-rebuild`"
    assert check.detail.endswith(suffix)
    output, separator, artifact = check.detail.removesuffix(suffix).partition(
        " (console="
    )
    assert output == expected
    assert separator == " (console="
    assert Path(artifact.removesuffix(")")).is_file()


def test_smoke_marker_changes_between_runs(smoke_system: Path) -> None:
    root = Path(os.environ["SMOKE_STATE"])
    assert container.verify_latest_main(smoke_system) == 0
    first = uuid.UUID((root / "marker").read_text())
    assert container.verify_latest_main(smoke_system) == 0
    second = uuid.UUID((root / "marker").read_text())
    assert first.version == second.version == 4
    assert first != second
    assert len(json.loads((root / "fds").read_text())) == 1


def test_identity_resolved_after_slot_and_fast_check_ignores_slot(
    smoke_system: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A waiting public CLI sees the id, mount and commit changed during wait."""
    root = Path(os.environ["SMOKE_STATE"])
    stderr_path = tmp_path / "waiting-stderr"
    src = Path(__file__).parent.parent / "python" / "src"
    monkeypatch.setenv("PYTHONPATH", str(src))
    env = dict(os.environ)
    env.pop("DOTFILES_LOCK_HOLDER_HEAVY_GATE", None)
    env["DOTFILES_HEAVY_GATE_WAIT"] = "30"
    child = (
        "from pathlib import Path; "
        "from dotfiles_setup.container import verify_latest_main; "
        f"raise SystemExit(verify_latest_main(Path({str(smoke_system)!r})))"
    )
    with (
        stderr_path.open("w+") as stderr,
        host_lock.held(host_lock.HEAVY_GATE, "identity-changing holder", wait_s=0),
    ):
        fast_env = {**env, "DOTFILES_HEAVY_GATE_WAIT": "0"}
        fast = subprocess.run(
            [sys.executable, "-c", child.replace(")))", "), run_smoke=False))")],
            env=fast_env,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert fast.returncode == 0, fast.stderr
        assert "smoke-tiers-1-3" not in fast.stdout
        (root / "identity-queries").unlink()
        process = subprocess.Popen(
            [sys.executable, "-c", child],
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
            env=env,
        )
        try:
            deadline = time.monotonic() + 30
            while (
                "waiting for heavy-gate" not in stderr_path.read_text()
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            assert "waiting for heavy-gate" in stderr_path.read_text()
            assert not (root / "identity-queries").exists()
            (root / "identity").write_text(
                json.dumps({"id": "decafbadcafe", "dest": "/workspaces/new"})
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(smoke_system),
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "--allow-empty",
                    "-qm",
                    "new head",
                ],
                check=True,
                capture_output=True,
            )
            head = subprocess.run(
                ["git", "-C", str(smoke_system), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except BaseException:
            process.kill()
            process.communicate(timeout=30)
            raise
    try:
        stdout, _ = process.communicate(timeout=30)
        assert process.returncode == 0, stderr_path.read_text()
        assert "decafbadcafe up" in stdout
        assert "/workspaces/new" in stdout
        assert head[:8] in stdout
        call = next(call for call in _smoke_calls() if "--workdir" in call["args"])
        assert call["args"][call["args"].index("--workdir") + 1 :][:2] == [
            "/workspaces/new",
            "decafbadcafe",
        ]
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=30)


def test_marker_rechecked_after_process_identity_is_bound(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A process whose marker changes before signaling is never killed."""
    monkeypatch.setenv("SMOKE_MODE", "inner124")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1")
    monkeypatch.setenv("SMOKE_PID_RECYCLED", "1")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    root = Path(os.environ["SMOKE_STATE"])
    pid = (root / "child-pid").read_text()
    assert check.ok is False
    assert "reaped 0 in-container processes" in check.detail
    assert (root / "proc" / pid / "environ").read_bytes() == b"OTHER_RUN=1"
    os.kill(int(pid), 0)


def test_reap_failure_reports_cleanup_unverified(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SMOKE_MODE", "inner124")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1")
    monkeypatch.setenv("SMOKE_REAP_ERROR", "1")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    assert "ORPHANS REMAIN: process reap unverified (proc unavailable)" in check.detail
    assert "dev-rebuild" not in check.detail


@pytest.mark.parametrize("mode", ["probe", "reap"])
@pytest.mark.parametrize("program_form", ["raw", "repr", "json", "long"])
def test_process_errors_are_bounded_and_exclude_inline_program(
    smoke_system: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    program_form: str,
) -> None:
    monkeypatch.setenv(
        "SMOKE_PROBE_ERROR" if mode == "probe" else "SMOKE_REAP_ERROR", "1"
    )
    monkeypatch.setenv("SMOKE_MODE", "inner124")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1")
    monkeypatch.setenv(
        "SMOKE_PROCESS_ERROR",
        "x" * 1000 if program_form == "long" else "scanner unavailable\n",
    )
    if program_form != "long":
        monkeypatch.setenv("SMOKE_ERROR_PROGRAM", program_form)
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    if program_form == "long":
        assert "x" * 500 in check.detail
        assert "x" * 501 not in check.detail
    else:
        assert "scanner unavailable" in check.detail
        assert "[inline scanner]" in check.detail
    assert "import json" not in check.detail
    assert "pidfd_send_signal" not in check.detail


@pytest.mark.parametrize("mode", ["probe", "reap"])
def test_process_timeout_omits_command_and_inline_program(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    def timing_out[**P, R](run: Callable[P, R]) -> Callable[P, R]:
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if (
                args
                and isinstance(args[0], list)
                and "/usr/bin/python3" in args[0]
                and args[0][-2] == mode
            ):
                raise subprocess.TimeoutExpired(args[0], 10)
            return run(*args, **kwargs)

        return wrapped

    monkeypatch.setattr(subprocess, "run", timing_out(subprocess.run))
    monkeypatch.setenv("SMOKE_MODE", "inner124")
    monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    assert f"process {mode} timed out after 10 seconds" in check.detail
    assert "import json" not in check.detail
    assert "/usr/bin/python3" not in check.detail
    assert "Command" not in check.detail


def test_unreadable_process_command_refuses_launch(
    smoke_system: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible process cannot establish that no smoke is running."""
    root = Path(os.environ["SMOKE_STATE"])
    row = _proc_row(
        root, 999999, command="bash\0scripts/devcontainer-smoke.sh", marker="other-run"
    )
    monkeypatch.setenv("SMOKE_UNREADABLE", "1")
    check = _names(container.verify_latest(smoke_system))["smoke-tiers-1-3"]
    assert check.ok is False
    assert check.detail == (
        "smoke process probe failed: process probe unreadable: pid 999999"
    )
    assert row.exists()
    assert not (root / "marker").exists()
    assert len(_smoke_calls()) == 1
