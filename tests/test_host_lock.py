# Copyright (c) 2026 Raymond Manaloto
"""Tests for the host-wide advisory locks (dotfiles_setup.host_lock).

Every contention arm uses a REAL second process: ``flock`` semantics between
processes (and a kernel release on holder death) are the whole point, and an
in-process double could not show either. The lock directory comes from
``tests/conftest.py``'s ``isolated_host_locks``, inherited by the children.
"""

from __future__ import annotations

import io
import os
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import gate_result, host_lock

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_HOLD = (
    "import sys, time\n"
    "from dotfiles_setup import host_lock\n"
    "with host_lock.held(host_lock.HEAVY_GATE, sys.argv[1]):\n"
    "    print('held', flush=True)\n"
    "    time.sleep(float(sys.argv[2]))\n"
)


def _holder(label: str, seconds: float) -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOLD, label, str(seconds)],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    assert proc.stdout.readline().strip() == "held"
    return proc


@pytest.fixture
def holder() -> Iterator[subprocess.Popen[str]]:
    proc = _holder("other-gate", 60)
    yield proc
    proc.kill()
    proc.wait()


def test_a_free_lock_records_its_holder_and_exports_the_pid() -> None:
    env_name = host_lock.holder_env_name(host_lock.HEAVY_GATE)
    with host_lock.held(host_lock.HEAVY_GATE, "me"):
        record = host_lock.read_holder(host_lock.HEAVY_GATE)
        assert record.startswith(f"{os.getpid()}\tme\t")
        assert os.environ[env_name] == str(os.getpid())
    assert env_name not in os.environ


def test_a_waiter_names_the_holder_and_runs_after_it_releases() -> None:
    proc = _holder("gate-A", 1.5)
    out = io.StringIO()
    started = time.monotonic()
    try:
        with host_lock.held(host_lock.HEAVY_GATE, "gate-B", wait_s=30, out=out):
            waited = time.monotonic() - started
            record = host_lock.read_holder(host_lock.HEAVY_GATE)
    finally:
        proc.wait()
    assert f"held by pid {proc.pid} (gate-A" in out.getvalue()
    assert "acquired after" in out.getvalue()
    assert waited >= 0.5
    assert record.startswith(f"{os.getpid()}\tgate-B")


def test_a_busy_lock_times_out_without_running_the_block(
    holder: subprocess.Popen[str],
) -> None:
    ran: list[bool] = []
    with (
        pytest.raises(host_lock.HostLockTimeoutError, match="other-gate"),
        host_lock.held(host_lock.HEAVY_GATE, "late", wait_s=0.3, out=io.StringIO()),
    ):
        ran.append(True)
    assert ran == []
    assert holder.poll() is None


def test_zero_wait_fails_at_once_and_prints_no_waiting_line(
    holder: subprocess.Popen[str],
) -> None:
    _ = holder
    out = io.StringIO()
    started = time.monotonic()
    with (
        pytest.raises(host_lock.HostLockTimeoutError),
        host_lock.held(host_lock.HEAVY_GATE, "now", wait_s=0, out=out),
    ):
        pass
    assert time.monotonic() - started < 1
    assert out.getvalue() == ""


def test_a_killed_holder_releases_the_lock() -> None:
    proc = _holder("doomed", 60)
    proc.send_signal(signal.SIGKILL)
    proc.wait()
    with host_lock.held(host_lock.HEAVY_GATE, "next", wait_s=2, out=io.StringIO()):
        assert host_lock.read_holder(host_lock.HEAVY_GATE).startswith(str(os.getpid()))


_CHILD_RUN = (
    "from dotfiles_setup.host_lock import host_lock_main\n"
    "raise SystemExit(host_lock_main(['run', '--wait', '1', '--', 'true']))\n"
)


def test_a_descendant_of_the_holder_re_enters() -> None:
    with host_lock.held(host_lock.HEAVY_GATE, "ship") as fd:
        assert fd is not None
        child = subprocess.run(
            [sys.executable, "-c", _CHILD_RUN], check=False, pass_fds=(fd,)
        )
    assert child.returncode == 0


def test_the_same_child_without_the_holder_export_waits_and_times_out() -> None:
    """Control arm for re-entry: only the export lets the child in."""
    name = host_lock.holder_env_name(host_lock.HEAVY_GATE)
    with host_lock.held(host_lock.HEAVY_GATE, "ship") as fd:
        assert fd is not None
        env = {k: v for k, v in os.environ.items() if k != name}
        child = subprocess.run(
            [sys.executable, "-c", _CHILD_RUN], check=False, env=env, pass_fds=(fd,)
        )
    assert child.returncode == 124


def test_reentrant_cli_preserves_the_ancestor_descriptor() -> None:
    """A nested gate passes the original lease through without unlocking it."""
    child = (
        "from dotfiles_setup.host_lock import inherited_heavy_lock_fd; "
        "raise SystemExit(0 if inherited_heavy_lock_fd() is not None else 9)"
    )
    with host_lock.held(host_lock.HEAVY_GATE, "ship"):
        assert (
            host_lock.host_lock_main(
                ["run", "--wait", "1", "--", sys.executable, "-c", child]
            )
            == 0
        )
        assert host_lock.read_holder(host_lock.HEAVY_GATE).startswith(
            f"{os.getpid()}\tship"
        )


def test_inherited_descriptor_rejects_a_closed_or_wrong_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An environment number alone cannot authorize lock re-entry."""
    monkeypatch.setenv(host_lock.LOCK_FD_ENV, "99999")
    with pytest.raises(RuntimeError, match="not live"):
        host_lock.inherited_heavy_lock_fd()
    with (
        host_lock.held(host_lock.HEAVY_GATE, "right-file"),
        (tmp_path / "wrong").open("w") as wrong,
    ):
        monkeypatch.setenv(host_lock.LOCK_FD_ENV, str(wrong.fileno()))
        with pytest.raises(RuntimeError, match="another file"):
            host_lock.inherited_heavy_lock_fd()


def test_a_stale_export_cannot_unlock_a_lock_someone_else_holds(
    holder: subprocess.Popen[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inherited pid that is NOT the recorded holder buys nothing."""
    _ = holder
    monkeypatch.setenv(host_lock.holder_env_name(host_lock.HEAVY_GATE), "1")
    with (
        pytest.raises(host_lock.HostLockTimeoutError),
        host_lock.held(host_lock.HEAVY_GATE, "x", wait_s=0.2, out=io.StringIO()),
    ):
        pass


def test_cli_status_reports_free_and_held(holder: subprocess.Popen[str]) -> None:
    status = subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.main", "heavy-gate", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert status.returncode == 0, status.stderr
    assert f"{holder.pid}\tother-gate" in status.stdout
    holder.kill()
    holder.wait()
    free = subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.main", "heavy-gate", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert free.returncode == 1
    assert free.stdout.strip() == "free"


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf"])
def test_a_non_finite_wait_falls_back_to_the_bounded_default(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv(host_lock.WAIT_ENV, raw)
    assert host_lock.default_wait_s() == host_lock.DEFAULT_WAIT_S


def test_the_child_keeps_the_lock_when_its_wrapper_is_killed(tmp_path: Path) -> None:
    """`heavy-gate run` hands the locked fd to its child (pass_fds)."""
    pidfile = tmp_path / "child.pid"
    child = (
        "import os, sys, time\n"
        "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
        "time.sleep(30)\n"
    )
    wrapper = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import sys\n"
                "from dotfiles_setup.host_lock import host_lock_main\n"
                "raise SystemExit(host_lock_main(['run', '--', *sys.argv[1:]]))\n"
            ),
            sys.executable,
            "-c",
            child,
            str(pidfile),
        ]
    )
    child_pid = 0
    try:
        deadline = time.monotonic() + 10
        while not pidfile.is_file() or not pidfile.read_text():
            assert time.monotonic() < deadline, "the child never started"
            time.sleep(0.05)
        child_pid = int(pidfile.read_text())
        wrapper.send_signal(signal.SIGKILL)
        wrapper.wait()
        with (
            pytest.raises(host_lock.HostLockTimeoutError),
            host_lock.held(host_lock.HEAVY_GATE, "x", wait_s=0.3, out=io.StringIO()),
        ):
            pass
    finally:
        wrapper.kill()
        if child_pid:
            os.kill(child_pid, signal.SIGKILL)


def test_cli_run_returns_the_command_rc() -> None:
    rc = host_lock.host_lock_main(
        ["run", "--", sys.executable, "-c", "raise SystemExit(3)"]
    )
    assert rc == 3


def test_a_heavy_gate_waits_out_its_bound_without_starting(
    holder: subprocess.Popen[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`gate run pytest` behind a busy lock: TIMED_OUT, the child never ran."""
    _ = holder
    monkeypatch.setenv(host_lock.WAIT_ENV, "0.3")
    marker = tmp_path / "ran"
    monkeypatch.setitem(gate_result.GATE_COMMANDS, "pytest", ("touch", str(marker)))
    result = gate_result.run_gate(tmp_path, "pytest")
    assert result.status is gate_result.GateStatus.TIMED_OUT
    assert "other-gate" in result.failures[0]
    assert not marker.exists()


def test_a_light_gate_runs_without_the_lock(
    holder: subprocess.Popen[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Control arm: a non-heavy gate is not queued behind the same holder."""
    _ = holder
    monkeypatch.setenv(host_lock.WAIT_ENV, "0.3")
    marker = tmp_path / "ran"
    monkeypatch.setitem(
        gate_result.GATE_COMMANDS, "pin-actions", ("touch", str(marker))
    )
    result = gate_result.run_gate(tmp_path, "pin-actions")
    assert result.status is gate_result.GateStatus.PASSED
    assert marker.exists()
