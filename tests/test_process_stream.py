# Copyright (c) 2026 Raymond Manaloto
"""Live subprocess output and bounded descendant cleanup controls."""

from __future__ import annotations

import os
import selectors
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import process_stream
from dotfiles_setup.process_stream import run_streamed

_REPO_ROOT = Path(__file__).parent.parent


def test_stdout_and_stderr_remain_separate_in_private_artifacts(tmp_path: Path) -> None:
    """The live combined log does not erase timeout's stdout preference."""
    result = run_streamed(
        [
            sys.executable,
            "-c",
            "import sys; print('OUT'); print('ERR', file=sys.stderr)",
        ],
        cwd=tmp_path,
        log_path=tmp_path / "console.log",
        timeout_s=5,
    )
    assert result.returncode == 0
    assert result.stdout_path.read_text() == "OUT\n"
    assert result.stderr_path.read_text() == "ERR\n"
    assert b"OUT" in result.log_path.read_bytes()
    assert b"ERR" in result.log_path.read_bytes()
    for path in (result.log_path, result.stdout_path, result.stderr_path):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_darwin_eperm_requires_reap_then_esrch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A persistent permission error never counts as a cleaned process group."""
    monkeypatch.setattr(process_stream.sys, "platform", "darwin")

    def reaped(*, timeout: float) -> int:
        assert timeout > 0
        return 0

    leader = cast(
        "subprocess.Popen[bytes]",
        SimpleNamespace(pid=1234, poll=lambda: 0, wait=reaped),
    )

    def denied(_pid: int, _signal: int) -> None:
        raise PermissionError

    monkeypatch.setattr(process_stream.os, "killpg", denied)
    with pytest.raises(PermissionError):
        process_stream.terminate_group(leader)

    def gone(_pid: int, signum: int) -> None:
        if signum == 0:
            raise ProcessLookupError
        raise PermissionError

    monkeypatch.setattr(process_stream.os, "killpg", gone)
    process_stream.terminate_group(leader)
    with pytest.raises(PermissionError):
        process_stream.terminate_group(
            cast(
                "subprocess.Popen[bytes]",
                SimpleNamespace(pid=1234, poll=lambda: None, wait=reaped),
            )
        )


def test_darwin_transient_eperm_waits_for_reap_and_esrch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A leader exiting just after signal zero is reaped before cleanup verdict."""
    monkeypatch.setattr(process_stream.sys, "platform", "darwin")
    returncode: int | None = None
    zero_checks = 0

    def poll() -> int | None:
        return returncode

    def wait(*, timeout: float) -> int:
        nonlocal returncode
        assert 0 < timeout <= 5
        returncode = 0
        return 0

    leader = cast(
        "subprocess.Popen[bytes]",
        SimpleNamespace(pid=1234, poll=poll, wait=wait),
    )

    def transient(_pid: int, signum: int) -> None:
        nonlocal zero_checks
        if signum == 0:
            zero_checks += 1
            if zero_checks > 1:
                raise ProcessLookupError
        raise PermissionError

    monkeypatch.setattr(process_stream.os, "killpg", transient)
    process_stream.terminate_group(leader)
    assert returncode == 0
    assert zero_checks == 3


def test_chunk_without_newline_reaches_terminal_before_child_exit(
    tmp_path: Path,
) -> None:
    """A writer that has not exited still has its first chunk visible live."""
    program = (
        "import sys,time; "
        "sys.stdout.write('FIRST'); sys.stdout.flush(); "
        "time.sleep(2); print('SECOND')"
    )
    driver = (
        "import sys; from pathlib import Path; "
        "from dotfiles_setup.process_stream import run_streamed; "
        "r=run_streamed([sys.executable,'-c',sys.argv[2]], "
        "cwd=Path(sys.argv[1]),log_path=Path(sys.argv[1])/'console.log',"
        "timeout_s=10); sys.exit(r.returncode)"
    )
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT / "python" / "src")}
    with subprocess.Popen(
        [sys.executable, "-c", driver, str(tmp_path), program],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as parent:
        assert parent.stderr is not None
        with selectors.DefaultSelector() as selector:
            selector.register(parent.stderr, selectors.EVENT_READ)
            assert selector.select(timeout=5), "first un-terminated chunk was buffered"
        assert parent.stderr.read(5) == b"FIRST"
        assert parent.poll() is None
        parent.communicate(timeout=10)
        assert parent.returncode == 0
    assert (tmp_path / "console.log").read_bytes() == b"FIRSTSECOND\n"


def test_exited_leader_cannot_hide_a_term_ignoring_descendant(
    tmp_path: Path,
) -> None:
    """A descendant-held pipe triggers the deadline even after leader rc 0."""
    child_program = (
        "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "time.sleep(30)"
    )
    leader_program = (
        "import subprocess,sys; "
        f"child=subprocess.Popen([sys.executable,'-c',{child_program!r}]); "
        "print(child.pid,flush=True)"
    )
    log_path = tmp_path / "console.log"
    started = time.monotonic()
    result = run_streamed(
        [sys.executable, "-c", leader_program],
        cwd=tmp_path,
        log_path=log_path,
        timeout_s=2,
    )
    elapsed = time.monotonic() - started
    child_pid = int(log_path.read_text().strip())
    status = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(child_pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.timed_out
    assert elapsed < 10
    assert status.returncode != 0 or status.stdout.strip().startswith("Z")


def test_closed_pipe_does_not_replace_the_child_deadline(tmp_path: Path) -> None:
    """A silent child can close both streams and still hit the real deadline."""
    program = "import os,time; os.close(1); os.close(2); time.sleep(8)"
    started = time.monotonic()
    result = run_streamed(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        log_path=tmp_path / "silent.log",
        timeout_s=0.5,
    )
    assert result.timed_out
    assert result.returncode != 0
    assert time.monotonic() - started < 5


def test_sigterm_to_streamer_reaps_its_separate_child_group(tmp_path: Path) -> None:
    """An interrupted wrapper leaves no live test worker behind."""
    pid_file = tmp_path / "child.pid"
    child = (
        "import os,sys,time; from pathlib import Path; "
        "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(30)"
    )
    driver = (
        "import sys; from pathlib import Path; "
        "from dotfiles_setup.process_stream import run_streamed; "
        "run_streamed([sys.executable,'-c',sys.argv[2],sys.argv[3]], "
        "cwd=Path(sys.argv[1]),log_path=Path(sys.argv[1])/'console.log',"
        "timeout_s=60)"
    )
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT / "python" / "src")}
    with subprocess.Popen(
        [sys.executable, "-c", driver, str(tmp_path), child, str(pid_file)],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as parent:
        deadline = time.monotonic() + 5
        while not pid_file.is_file():
            assert time.monotonic() < deadline, "child never reached the probe"
            time.sleep(0.05)
        child_pid = int(pid_file.read_text())
        time.sleep(0.1)
        parent.send_signal(signal.SIGTERM)
        parent.communicate(timeout=10)
        status = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(child_pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        if status.returncode == 0 and not status.stdout.strip().startswith("Z"):
            os.kill(child_pid, signal.SIGKILL)
        assert parent.returncode == 143
        assert status.returncode != 0 or status.stdout.strip().startswith("Z")
