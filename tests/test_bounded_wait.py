# Copyright (c) 2026 Raymond Manaloto
"""Tests for the deadline-bound polling helper."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import bounded_wait
from dotfiles_setup.main import setup_parser


class FakeClock:
    """A monotonic clock advanced only by the injected sleeper."""

    def __init__(self) -> None:
        """Start the fake clock at zero."""
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the current fake timestamp."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Advance without sleeping in real time."""
        self.now += seconds


def test_deadline_is_required_by_the_public_cli() -> None:
    with pytest.raises(SystemExit) as raised:
        setup_parser().parse_args(["bounded-wait", "--file", "missing"])
    assert raised.value.code == 2


def test_missing_file_expires_with_124_and_names_the_target(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = FakeClock()
    missing = tmp_path / "never-created"
    request = bounded_wait.WaitRequest(
        deadline_s=2,
        file=missing,
        interval_s=1,
    )

    rc = bounded_wait.wait(
        request,
        monotonic=clock.monotonic,
        sleeper=clock.sleep,
    )

    assert rc == 124
    assert str(missing) in caplog.text
    assert "DEADLINE EXPIRED" in caplog.text


def test_file_created_during_an_injected_sleep_succeeds(tmp_path: Path) -> None:
    clock = FakeClock()
    awaited = tmp_path / "ready"

    def create_then_advance(seconds: float) -> None:
        awaited.write_text("ready")
        clock.sleep(seconds)

    rc = bounded_wait.wait(
        bounded_wait.WaitRequest(deadline_s=5, file=awaited, interval_s=1),
        monotonic=clock.monotonic,
        sleeper=create_then_advance,
    )

    assert rc == 0
    assert clock.now == 1


def test_command_poll_has_the_remaining_deadline_as_its_own_timeout() -> None:
    clock = FakeClock()
    observed: list[float] = []

    def command(_text: str, timeout_s: float) -> int:
        observed.append(timeout_s)
        return 0

    rc = bounded_wait.wait(
        bounded_wait.WaitRequest(deadline_s=7, command="test -f ready"),
        monotonic=clock.monotonic,
        sleeper=clock.sleep,
        command_runner=command,
    )

    assert rc == 0
    assert observed == [7]


def test_interval_below_one_second_is_rejected() -> None:
    assert (
        bounded_wait.wait(
            bounded_wait.WaitRequest(
                deadline_s=2,
                command="true",
                interval_s=0.5,
            )
        )
        == 2
    )


def test_real_command_predicates_satisfy_or_expire() -> None:
    assert (
        bounded_wait.wait(
            bounded_wait.WaitRequest(deadline_s=1, command="true", interval_s=1)
        )
        == 0
    )
    assert (
        bounded_wait.wait(
            bounded_wait.WaitRequest(deadline_s=1, command="false", interval_s=1)
        )
        == bounded_wait.TIMEOUT_EXIT_CODE
    )


def test_timed_out_pipeline_leaves_no_surviving_process(tmp_path: Path) -> None:
    pid_path = tmp_path / "sleep.pid"
    command = f"sh -c 'echo $$ > {pid_path}; exec sleep 47' | cat"

    assert (
        bounded_wait.wait(
            bounded_wait.WaitRequest(deadline_s=1, command=command, interval_s=1)
        )
        == bounded_wait.TIMEOUT_EXIT_CODE
    )
    sleep_pid = int(pid_path.read_text())
    # A killed grandchild is re-parented to launchd, which reaps it
    # asynchronously; until then `kill(pid, 0)` still succeeds on the zombie.
    # Measured 2026-09-16: passes 5/5 alone, failed once as test 122 of the
    # full suite under load with a 1 s window — so poll longer and read the
    # state, treating a zombie (`Z`) as dead. Only a live, running survivor
    # is the defect this arm exists to catch.
    for _attempt in range(250):
        try:
            os.kill(sleep_pid, 0)
        except ProcessLookupError:
            break
        state = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(sleep_pid)],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if not state or state.startswith("Z"):
            break
        time.sleep(0.02)
    else:
        pytest.fail(f"timed-out predicate child {sleep_pid} survived")
