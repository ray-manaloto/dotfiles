# Copyright (c) 2026 Raymond Manaloto
"""Select native pytest policy and retain one complete report set per run."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import host_lock, process_stream

if TYPE_CHECKING:
    from collections.abc import Sequence

_CHUNK_SIZE = 65536


class _InterruptedError(Exception):
    """Carry a signal number out of a blocked pipe read."""

    def __init__(self, signum: int) -> None:
        self.signum = signum
        super().__init__(signum)


def _private_write(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(payload)


def _pytest_command(run_dir: Path, test_args: Sequence[str]) -> list[str]:
    """Select the native config and all three pytest-owned report paths."""
    selected = list(test_args)
    if selected[:1] == ["--"]:
        selected.pop(0)
    if not selected:
        selected = ["tests/"]
    return [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        "python/pyproject.toml",
        "--rootdir=.",
        f"--junitxml={run_dir / 'junit.xml'}",
        f"--report-log={run_dir / 'report.jsonl'}",
        f"--log-file={run_dir / 'controller.log'}",
        *selected,
    ]


def _execute(
    root: Path,
    command: list[str],
    env: dict[str, str],
    console: Path,
    lock_fd: int | None,
) -> tuple[int, bool]:
    """Tee raw pytest output and forward interruptions to its own group."""

    def interrupt(signum: int, _frame: object) -> None:
        raise _InterruptedError(signum)

    previous_term = signal.signal(signal.SIGTERM, interrupt)
    try:
        descriptor = os.open(console, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb", buffering=0) as output:
            process = subprocess.Popen(
                command,
                cwd=root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                pass_fds=() if lock_fd is None else (lock_fd,),
            )
            if process.stdout is None:
                msg = "pytest child has no stdout pipe"
                raise RuntimeError(msg)
            try:
                while chunk := os.read(process.stdout.fileno(), _CHUNK_SIZE):
                    output.write(chunk)
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
                return process.wait(), False
            except (KeyboardInterrupt, _InterruptedError) as error:
                process_stream.terminate_group(process)
                return (
                    128 + error.signum if isinstance(error, _InterruptedError) else 130,
                    True,
                )
            except BaseException:
                process_stream.terminate_group(process)
                raise
            finally:
                process.stdout.close()
    finally:
        signal.signal(signal.SIGTERM, previous_term)


def _record_outcome(
    run_dir: Path,
    details: dict[str, object],
) -> None:
    """Publish the invocation verdict and its artifact paths even on interrupt."""
    payload = {
        **details,
        "console": str(run_dir / "console.log"),
        "junit": str(run_dir / "junit.xml"),
        "report": str(run_dir / "report.jsonl"),
        "workers": str(run_dir / "workers"),
    }
    _private_write(
        run_dir / "invocation.json",
        (json.dumps(payload, indent=2) + "\n").encode(),
    )
    sys.stderr.write(
        f"[pytest][end] label={details['label']} rc={details['returncode']} "
        f"elapsed={details['duration_s']}s "
        f"artifact={run_dir}\n"
    )
    sys.stderr.flush()


def run_pytest(repo_root: Path, label: str, test_args: Sequence[str]) -> int:
    """Run pytest with an explicit config and unique private artifacts."""
    root = repo_root.resolve(strict=True)
    if not (root / "python" / "pyproject.toml").is_file():
        sys.stderr.write(
            f"pytest config missing: {root / 'python' / 'pyproject.toml'}\n"
        )
        return 2
    arch = os.uname().machine
    run_dir = process_stream.new_run_dir(root, f"pytest-{label}-{arch}")
    (run_dir / "workers").mkdir(mode=0o700)
    command = _pytest_command(run_dir, test_args)
    env = dict(os.environ)
    env["DOTFILES_PYTEST_RUN_DIR"] = str(run_dir)
    # xdist imports setproctitle, whose default Linux behavior overwrites
    # /proc/PID/environ. Docker smoke reaps descendants by its inherited marker.
    env["SPT_NOENV"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    lock_fd = host_lock.inherited_heavy_lock_fd()
    started = time.monotonic()
    sys.stderr.write(
        f"[pytest][start] label={label} arch={arch} console={run_dir / 'console.log'} "
        f"junit={run_dir / 'junit.xml'} report={run_dir / 'report.jsonl'} "
        f"workers={run_dir / 'workers'}\n"
    )
    sys.stderr.flush()
    previous_umask = os.umask(0o077)
    interrupted = False
    returncode = 1
    try:
        returncode, interrupted = _execute(
            root, command, env, run_dir / "console.log", lock_fd
        )
    finally:
        os.umask(previous_umask)
        elapsed = time.monotonic() - started
        _record_outcome(
            run_dir,
            {
                "label": label,
                "arch": arch,
                "returncode": returncode,
                "interrupted": interrupted,
                "duration_s": elapsed,
                "command": command,
            },
        )
    return returncode


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: label one managed pytest invocation and pass through test arguments."""
    parser = argparse.ArgumentParser(prog="python -m dotfiles_setup.pytest_runner")
    parser.add_argument("--label", default="manual")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)
    return run_pytest(options.repo_root, options.label, options.pytest_args)


if __name__ == "__main__":
    raise SystemExit(main())
