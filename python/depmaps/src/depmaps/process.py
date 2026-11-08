"""Run an external program with an explicit environment, working folder and I/O policy."""

import os
import subprocess
from pathlib import Path


def run(*argv: Path | str, cwd: Path, timeout: float | None) -> subprocess.CompletedProcess[str]:
    # Callers turn a start failure, exit status or timeout into the event for their step. Clones,
    # fetches and indexing have no timeout: a large repository over a slow link takes as long as it takes.
    return subprocess.run(
        [str(arg) for arg in argv], env=dict(os.environ), cwd=cwd, stdin=subprocess.DEVNULL,
        capture_output=True, timeout=timeout, text=True, check=False,
    )  # fmt: skip
