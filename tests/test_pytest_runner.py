# Copyright (c) 2026 Raymond Manaloto
"""Real failure and interruption controls for the managed pytest runner."""

from __future__ import annotations

import json
import os
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_RUNS = _ROOT / ".agent" / "gate-results" / "runs"


def _command(label: str, test_file: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "dotfiles_setup.pytest_runner",
        "--label",
        label,
        "--",
        str(test_file),
        "-n",
        "0",
    ]


def _new_run(label: str, before: set[Path]) -> Path:
    found = set(_RUNS.glob(f"pytest-{label}-*")) - before
    assert len(found) == 1
    return found.pop()


def test_failure_keeps_junit_report_and_true_rc() -> None:
    test_file = _ROOT / ".agent" / "state" / f"test_runner_fail_{os.getpid()}.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_red():\n    assert 1 == 2\n")
    label = f"failure-control-{os.getpid()}"
    before = set(_RUNS.glob(f"pytest-{label}-*"))
    try:
        result = subprocess.run(
            _command(label, test_file),
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        test_file.unlink(missing_ok=True)
    run_dir = _new_run(label, before)
    details = json.loads((run_dir / "invocation.json").read_text())
    junit = (run_dir / "junit.xml").read_text()
    assert result.returncode == details["returncode"] == 1
    assert "assert 1 == 2" in result.stdout
    assert "assert 1 == 2" in (run_dir / "console.log").read_text()
    assert 'failures="1"' in junit
    assert "<failure " in junit
    assert (run_dir / "report.jsonl").stat().st_size > 0


def test_sigterm_stops_pytest_and_records_interruption(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child.pid"
    test_file = _ROOT / ".agent" / "state" / f"test_runner_slow_{os.getpid()}.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "import os, time\nfrom pathlib import Path\n"
        "def test_slow():\n"
        f"    Path({str(child_pid_file)!r}).write_text(str(os.getpid()))\n"
        "    time.sleep(60)\n"
    )
    label = f"interrupt-control-{os.getpid()}"
    before = set(_RUNS.glob(f"pytest-{label}-*"))
    # The runner's start banner can exceed a Darwin pipe's capacity. Keep
    # both streams draining to files while this fixture waits for its marker.
    with (
        (tmp_path / "runner.stdout.log").open("wb") as stdout_log,
        (tmp_path / "runner.stderr.log").open("wb") as stderr_log,
    ):
        runner = subprocess.Popen(
            _command(label, test_file),
            cwd=_ROOT,
            stdout=stdout_log,
            stderr=stderr_log,
        )
        try:
            deadline = time.monotonic() + 20
            while not child_pid_file.is_file():
                assert runner.poll() is None
                assert time.monotonic() < deadline, "slow test never started"
                time.sleep(0.05)
            child_pid = int(child_pid_file.read_text())
            runner.send_signal(signal.SIGTERM)
            runner.wait(timeout=15)
        finally:
            if runner.poll() is None:
                runner.send_signal(signal.SIGTERM)
                try:
                    runner.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    runner.kill()
                    runner.wait(timeout=5)
            test_file.unlink(missing_ok=True)
    run_dir = _new_run(label, before)
    details = json.loads((run_dir / "invocation.json").read_text())
    status = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(child_pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode == 0 and not status.stdout.strip().startswith("Z"):
        os.kill(child_pid, signal.SIGKILL)
    assert runner.returncode == details["returncode"] == 143
    assert details["interrupted"] is True
    assert status.returncode != 0 or status.stdout.strip().startswith("Z")


def test_slow_stack_and_phase_logs_survive_a_green_run() -> None:
    """A slow test emits a stack without aborting and records all three phases."""
    test_file = _ROOT / ".agent" / "state" / f"test_runner_stack_{os.getpid()}.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "import logging, time, pytest\n"
        "@pytest.fixture\n"
        "def phases():\n"
        "    logging.getLogger('probe').debug('PHASE_SETUP')\n"
        "    yield\n"
        "    logging.getLogger('probe').debug('PHASE_TEARDOWN')\n"
        "def test_slow(phases):\n"
        "    logging.getLogger('probe').debug('PHASE_CALL')\n"
        "    time.sleep(1.5)\n"
    )
    label = f"stack-control-{os.getpid()}"
    before = set(_RUNS.glob(f"pytest-{label}-*"))
    try:
        result = subprocess.run(
            [*_command(label, test_file), "-o", "faulthandler_timeout=1"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    finally:
        test_file.unlink(missing_ok=True)
    run_dir = _new_run(label, before)
    log = (run_dir / "controller.log").read_text()
    console = (run_dir / "console.log").read_text()
    assert result.returncode == 0
    assert "Timeout" in console
    assert "test_slow" in console
    assert "PHASE_SETUP" in log
    assert "PHASE_CALL" in log
    assert "PHASE_TEARDOWN" in log
    assert 'tests="1"' in (run_dir / "junit.xml").read_text()


def test_repeated_runs_get_distinct_private_artifacts() -> None:
    """The second invocation cannot overwrite the first report set."""
    test_file = _ROOT / ".agent" / "state" / f"test_runner_repeat_{os.getpid()}.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "import logging\n"
        "def test_green():\n"
        "    logging.getLogger('probe').info('REPEAT_GREEN')\n"
        "    assert True\n"
    )
    label = f"repeat-control-{os.getpid()}"
    seen = set(_RUNS.glob(f"pytest-{label}-*"))
    runs = []
    try:
        for _ in range(2):
            result = subprocess.run(
                _command(label, test_file),
                cwd=_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            assert result.returncode == 0
            run_dir = _new_run(label, seen)
            runs.append(run_dir)
            seen.add(run_dir)
    finally:
        test_file.unlink(missing_ok=True)
    assert runs[0] != runs[1]
    for run_dir in runs:
        assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
        for name in ("console.log", "controller.log", "junit.xml", "report.jsonl"):
            path = run_dir / name
            assert path.stat().st_size > 0
            assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_setup_and_teardown_failures_keep_phase_evidence() -> None:
    """The runner retains reports when fixtures fail on either side of call."""
    test_file = _ROOT / "tests" / f"test_runner_phases_{os.getpid()}.py"
    test_file.write_text(
        "import logging, pytest\n"
        "@pytest.fixture\n"
        "def setup_fails():\n"
        "    logging.getLogger('probe').debug('BEFORE_SETUP_FAILURE')\n"
        "    raise RuntimeError('SETUP_FAILURE_MARKER')\n"
        "@pytest.fixture\n"
        "def teardown_fails():\n"
        "    logging.getLogger('probe').debug('BEFORE_CALL')\n"
        "    yield\n"
        "    logging.getLogger('probe').debug('BEFORE_TEARDOWN_FAILURE')\n"
        "    raise RuntimeError('TEARDOWN_FAILURE_MARKER')\n"
        "def test_setup(setup_fails):\n"
        "    pass\n"
        "def test_teardown(teardown_fails):\n"
        "    pass\n"
    )
    label = f"phase-failures-{os.getpid()}"
    before = set(_RUNS.glob(f"pytest-{label}-*"))
    try:
        result = subprocess.run(
            _command(label, test_file),
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        test_file.unlink(missing_ok=True)
    run_dir = _new_run(label, before)
    details = json.loads((run_dir / "invocation.json").read_text())
    console = (run_dir / "console.log").read_text()
    log = (run_dir / "controller.log").read_text()
    junit = (run_dir / "junit.xml").read_text()
    assert result.returncode == details["returncode"] == 1
    assert "SETUP_FAILURE_MARKER" in console
    assert "TEARDOWN_FAILURE_MARKER" in console
    assert "BEFORE_SETUP_FAILURE" in log
    assert "BEFORE_TEARDOWN_FAILURE" in log
    assert '<testsuite name="pytest" errors="2"' in junit
    assert (run_dir / "report.jsonl").stat().st_size > 0


def test_xdist_worker_crash_keeps_other_worker_logs() -> None:
    """A dead worker remains visible while surviving workers keep their logs."""
    test_file = _ROOT / "tests" / f"test_runner_worker_crash_{os.getpid()}.py"
    test_file.write_text(
        "import os\n"
        "def test_crash():\n"
        "    os._exit(7)\n"
        "def test_survivor():\n"
        "    assert True\n"
    )
    label = f"worker-crash-{os.getpid()}"
    before = set(_RUNS.glob(f"pytest-{label}-*"))
    try:
        result = subprocess.run(
            [*_command(label, test_file)[:-2], "-n", "2", "--max-worker-restart=0"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    finally:
        test_file.unlink(missing_ok=True)
    run_dir = _new_run(label, before)
    details = json.loads((run_dir / "invocation.json").read_text())
    console = (run_dir / "console.log").read_text()
    worker_logs = sorted((run_dir / "workers").glob("gw*.log"))
    assert result.returncode == details["returncode"] != 0
    assert "worker" in console.lower()
    assert len(worker_logs) >= 2
    assert all(path.stat().st_size > 0 for path in worker_logs)
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in worker_logs)
    assert (run_dir / "report.jsonl").stat().st_size > 0
