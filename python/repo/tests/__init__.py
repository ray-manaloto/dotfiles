"""Run CLI and subprocess regressions with a deadline outside the process under test."""

import os
import signal
import subprocess
import sys
from typing import BinaryIO

STOP = """
import signal
def stop(signum, frame):
    raise SystemExit(124)
signal.signal(signal.SIGTERM, stop)
"""


def run_python(code: str, *, stdin: BinaryIO | None = None) -> subprocess.CompletedProcess[bytes]:
    command = [sys.executable, "-c", STOP + code]
    with subprocess.Popen(
        command, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    ) as child:
        try:
            stdout, stderr = child.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            # Terminate the owned group; the handler lets subprocess.run reap its Git child.
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.communicate()
            raise
    return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
