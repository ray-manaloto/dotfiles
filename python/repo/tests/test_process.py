"""The concurrent pipe transport through real child processes."""

import os
import signal
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import assert_type

import pytest

from repotools import process
from tests import run_python


def test_uncaptured_stdout_is_inherited_and_absent_from_the_result(capfd: pytest.CaptureFixture[str]) -> None:
    done = process.run([sys.executable, "-c", "print('inherited')"], b"", capture_stdout=False, timeout=5)
    assert_type(done, subprocess.CompletedProcess[bytes | None])
    assert done.returncode == 0
    assert done.stdout is None
    assert done.stderr == b""
    assert capfd.readouterr().out == "inherited\n"


def test_binary_input_and_both_output_pipes_progress_independently(tmp_path: Path) -> None:
    data = b"nul\x00crlf\r\nlf\n\xff" * 16384
    path = tmp_path / "input"
    path.write_bytes(data)
    # This real Python workload fills each output before reading a large stdin, including binary bytes.
    workload = (
        "import sys; sys.stdout.buffer.write(b'o' * 131072); sys.stdout.flush(); "
        "sys.stderr.buffer.write(b'e' * 131072); sys.stderr.flush(); "
        "sys.stdout.buffer.write(sys.stdin.buffer.read())"
    )
    code = (
        "import sys\nfrom repotools.process import run\n"
        f"done = run([sys.executable, '-c', {workload!r}], sys.stdin.buffer.read(), timeout=5)\n"
        "sys.stdout.buffer.write(done.stdout)\nsys.stderr.buffer.write(done.stderr)\n"
    )
    with path.open("rb") as source:
        done = run_python(code, stdin=source)
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    assert done.stdout == b"o" * 131072 + data
    assert done.stderr == b"e" * 131072


def test_an_early_git_exit_reports_its_status_and_error() -> None:
    done = run_python(
        "import subprocess, sys\nfrom repotools.process import run\n"
        "try:\n    run(['git', 'cat-file', '--not-an-option'], b'x' * 1048576)\n"
        "except subprocess.CalledProcessError as error:\n"
        "    sys.stdout.buffer.write(error.stderr)\n    raise SystemExit(error.returncode)\n"
    )
    assert done.returncode == 129
    assert done.stdout  # The caller forwards Git's stderr without depending on its locale.
    assert done.stderr == b""


def test_timeout_propagates_and_releases_the_blocked_writer() -> None:
    workload = "import time; time.sleep(60)"
    done = run_python(
        "import subprocess, sys\nfrom repotools.process import run\n"
        f"try:\n    run([sys.executable, '-c', {workload!r}], b'x' * 1048576, timeout=0.5)\n"
        "except subprocess.TimeoutExpired:\n    print('timed out')\n"
    )
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    assert done.stdout == b"timed out\n"
    assert done.stderr == b""


def test_interrupt_before_writer_submission_reaps_the_child() -> None:
    # Trace only to deliver a real SIGINT in the otherwise tiny gap after Popen, before submit.
    code = (
        "import inspect, os, signal, sys\nfrom repotools.process import run\n"
        "source, start = inspect.getsourcelines(run)\n"
        "target = start + next(i for i, line in enumerate(source) if 'writing = pool.submit(' in line)\n"
        "def interrupt(frame, event, arg):\n"
        "    if event == 'line' and frame.f_code is run.__code__ and frame.f_lineno == target:\n"
        "        global child_pid\n        child_pid = frame.f_locals['child'].pid\n"
        "        sys.settrace(None)\n        os.kill(os.getpid(), signal.SIGINT)\n"
        "    return interrupt\n"
        "sys.settrace(interrupt)\n"
        "try:\n    run([sys.executable, '-c', 'import time; time.sleep(60)'], b'x')\n"
        "except KeyboardInterrupt:\n    print('interrupted')\n"
        "try:\n    os.kill(child_pid, 0)\n"
        "except ProcessLookupError:\n    print('reaped')\n"
        "else:\n    os.kill(child_pid, signal.SIGKILL)\n    os.waitpid(child_pid, 0)\n"
    )
    done = run_python(code)
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    assert done.stdout == b"interrupted\nreaped\n"
    assert done.stderr == b""


def test_interrupt_reaps_the_ready_child_and_releases_the_blocked_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # A relative socket name avoids AF_UNIX's short path limit under pytest's temporary directory.
    with socket.socket(socket.AF_UNIX) as ready:
        ready.bind("ready")
        ready.listen()
        ready.settimeout(15)  # The external supervisor also bounds the entire invocation.
        workload = (
            "import os, socket, sys, time; time.sleep(1); sys.stdin.buffer.read(1); "
            "ready = socket.socket(socket.AF_UNIX); ready.connect('ready'); "
            "ready.sendall(f'{os.getppid()} {os.getpid()}'.encode()); ready.close(); time.sleep(60)"
        )
        code = (
            "import sys\nfrom repotools.process import run\n"
            f"try:\n    run([sys.executable, '-c', {workload!r}], b'x' * 1048576)\n"
            "except KeyboardInterrupt:\n    print('interrupted')\n"
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            running = pool.submit(run_python, code)
            with ready.accept()[0] as connection, connection.makefile() as message:
                caller_pid, child_pid = map(int, message.read().split())
            os.kill(caller_pid, signal.SIGINT)
            done = running.result()
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    assert done.stdout == b"interrupted\n"
    assert done.stderr == b""
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)
