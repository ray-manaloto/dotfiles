"""Run an external program with an explicit environment, working folder and I/O policy."""

import subprocess
from collections.abc import Mapping
from pathlib import Path


def run(
    *argv: Path | str,
    env: Mapping[str, str],
    cwd: Path,
    input_text: str | None,
    capture_output: bool,
    timeout: float | None,
) -> subprocess.CompletedProcess[str]:
    # Callers translate startup/timeouts into the event appropriate to their step. The installer
    # inherits stdio and has no timeout; probes capture output and have a bounded wait.
    return subprocess.run(
        [str(arg) for arg in argv], env=env, cwd=cwd, input=input_text, capture_output=capture_output,
        timeout=timeout, text=True, check=False,
    )  # fmt: skip
