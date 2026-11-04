"""Feed a child independently of draining its output, without writable temporary storage."""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import BinaryIO, cast


def write(stream: BinaryIO, data: bytes) -> None:
    with stream:
        stream.write(data)


def run(
    command: list[str], stdin: bytes, *, capture_stdout: bool = True, timeout: float | None = None
) -> subprocess.CompletedProcess[bytes | None]:
    # CPython 3.15.2's Windows _communicate uses writer/reader threads (Lib/subprocess.py:1788-1834, read offline).
    # macOS can report a small pipe writable without room for PIPE_BUF; no writer may block the reader.
    with (
        ThreadPoolExecutor(max_workers=1) as pool,
        subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE if capture_stdout else None, stderr=subprocess.PIPE
        ) as child,
    ):
        try:
            writing = pool.submit(write, cast("BinaryIO", child.stdin), stdin)  # PIPE guarantees a binary stream.
            child.stdin = None  # The writer owns it; communicate must neither flush nor close it.
            stdout, stderr = child.communicate(timeout=timeout)
        finally:
            # Also release and join a blocked writer on timeout, interruption, or a read failure.
            child.kill()  # A no-op after communicate has reaped a successful child.
            returncode = child.wait()
    done: subprocess.CompletedProcess[bytes | None] = subprocess.CompletedProcess(command, returncode, stdout, stderr)
    # Prefer a failed child's status and stderr to the resulting broken pipe; other write failures propagate.
    done.check_returncode()
    writing.result()
    return done
