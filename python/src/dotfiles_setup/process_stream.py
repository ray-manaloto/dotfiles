# Copyright (c) 2026 Raymond Manaloto
"""Stream a bounded child into a private artifact and the live terminal."""

from __future__ import annotations

import contextlib
import io
import os
import re
import selectors
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import BinaryIO

_CHUNK_SIZE = 65536
_TERM_GRACE_S = 5.0
_DRAIN_GRACE_S = 5.0
_DARWIN_REAP_GRACE_S = 0.5


@dataclass(frozen=True)
class StreamResult:
    """The child's real return code and timeout observation."""

    returncode: int
    timed_out: bool
    duration_s: float
    log_path: Path
    stdout_path: Path
    stderr_path: Path


def new_run_dir(repo_root: Path, label: str) -> Path:
    """Create one private, collision-resistant artifact directory."""
    safe = re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-")[:48] or "run"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    parent = repo_root / ".agent" / "gate-results" / "runs"
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    result = parent / f"{safe}-{stamp}-{uuid.uuid4().hex[:8]}"
    result.mkdir(mode=0o700)
    return result


def terminate_group(process: subprocess.Popen[bytes]) -> None:
    """Bound cleanup of the child and descendants in its process group."""
    # A leader may exit while a descendant still holds the output pipe. The
    # process group survives its leader, so `process.poll()` is not a cleanup
    # test and `wait()` on that leader is not a descendant cleanup test.
    _send_group_signal(process, signal.SIGTERM)
    expires_at = time.monotonic() + _TERM_GRACE_S
    while time.monotonic() < expires_at:
        if not _group_alive(process):
            break
        time.sleep(0.05)
    else:
        _send_group_signal(process, signal.SIGKILL)
    process.wait(timeout=_TERM_GRACE_S)


def _send_group_signal(process: subprocess.Popen[bytes], signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass
    except PermissionError:
        if not _darwin_group_gone_after_reap(process):
            raise


def _group_alive(process: subprocess.Popen[bytes]) -> bool:
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        if _darwin_group_gone_after_reap(process):
            return False
        raise
    return True


def _darwin_group_gone_after_reap(process: subprocess.Popen[bytes]) -> bool:
    """Accept XNU's zombie-only EPERM only if reaping removes the group.

    XNU returns EPERM for signal zero when a process group has only zombies.
    Reap our leader first. A persistent EPERM could also be a real permission
    failure for a descendant, so only ESRCH proves cleanup succeeded.
    """
    if sys.platform != "darwin":
        return False
    if process.poll() is None:
        try:
            process.wait(timeout=_DARWIN_REAP_GRACE_S)
        except subprocess.TimeoutExpired:
            return False
    if process.poll() is None:
        return False
    expires_at = time.monotonic() + _DARWIN_REAP_GRACE_S
    while True:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            if time.monotonic() >= expires_at:
                return False
            time.sleep(0.01)
            continue
        return False


def _live_chunk(chunk: bytes) -> None:
    """Forward every chunk, including output without a newline, immediately."""
    try:
        descriptor = sys.stderr.fileno()
    except AttributeError, OSError, io.UnsupportedOperation:
        sys.stderr.write(chunk.decode(errors="replace"))
        sys.stderr.flush()
        return
    view = memoryview(chunk)
    while view:
        view = view[os.write(descriptor, view) :]


def _drain_output(
    process: subprocess.Popen[bytes],
    log: BinaryIO,
    stdout_log: BinaryIO,
    stderr_log: BinaryIO,
    deadline: float | None,
) -> bool:
    """Tee all available bytes until EOF or the child deadline expires."""
    if process.stdout is None or process.stderr is None:
        msg = "streamed child has no output pipes"
        raise RuntimeError(msg)
    timed_out = False
    drain_deadline: float | None = None
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ, stdout_log)
        selector.register(process.stderr, selectors.EVENT_READ, stderr_log)
        while selector.get_map():
            now = time.monotonic()
            if deadline is not None and now >= deadline and not timed_out:
                timed_out = True
                terminate_group(process)
                drain_deadline = time.monotonic() + _DRAIN_GRACE_S
            if drain_deadline is not None and now >= drain_deadline:
                break
            remaining = (
                None if deadline is None or timed_out else max(0.0, deadline - now)
            )
            interval = 0.25 if remaining is None else min(0.25, remaining)
            for key, _ in selector.select(timeout=interval):
                chunk = os.read(key.fd, _CHUNK_SIZE)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                log.write(chunk)
                key.data.write(chunk)
                _live_chunk(chunk)
    return timed_out


def run_streamed(
    command: Sequence[str],
    *,
    cwd: Path,
    log_path: Path,
    timeout_s: float | None = None,
    pass_fds: tuple[int, ...] = (),
) -> StreamResult:
    """Run, tee raw bytes, and retain a complete log across exit or timeout.

    The child owns a process group so timeout and caller interruption can
    terminate nested commands. No shell or line-buffering layer is involved.
    The caller's lock descriptor is passed to the child when provided.
    """
    log_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stdout_path = log_path.with_name("stdout.log")
    stderr_path = log_path.with_name("stderr.log")
    started = time.monotonic()
    with contextlib.ExitStack() as stack:
        log = stack.enter_context(_open_private(log_path))
        stdout_log = stack.enter_context(_open_private(stdout_path))
        stderr_log = stack.enter_context(_open_private(stderr_path))
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            pass_fds=pass_fds,
            start_new_session=True,
        )
        deadline = None if timeout_s is None else started + timeout_s
        install_term_handler = threading.current_thread() is threading.main_thread()
        previous_term = signal.getsignal(signal.SIGTERM)

        def interrupt(signum: int, _frame: object) -> None:
            raise SystemExit(128 + signum)

        if install_term_handler:
            signal.signal(signal.SIGTERM, interrupt)
        try:
            timed_out = _drain_output(process, log, stdout_log, stderr_log, deadline)
            if timed_out:
                returncode = process.wait(timeout=_TERM_GRACE_S)
            else:
                remaining = (
                    None if deadline is None else max(0.0, deadline - time.monotonic())
                )
                try:
                    returncode = process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    terminate_group(process)
                    returncode = process.returncode
        except BaseException:
            with contextlib.suppress(Exception):
                terminate_group(process)
            raise
        finally:
            if install_term_handler:
                signal.signal(signal.SIGTERM, previous_term)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
    return StreamResult(
        returncode=returncode,
        timed_out=timed_out,
        duration_s=time.monotonic() - started,
        log_path=log_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )


def _open_private(path: Path) -> BinaryIO:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(descriptor, "wb", buffering=0)
