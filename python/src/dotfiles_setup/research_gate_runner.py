# Copyright (c) 2026 Raymond Manaloto
"""Run research through the pinned, noninteractive fnox research profile."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str], repo_root: Path) -> int:
    """Keep profile options before exec; forward only research-fanout arguments."""
    command = [
        "fnox",
        "--config",
        str(Path.home() / ".config/fnox/config.toml"),
        "--profile",
        "codex_research",
        "--no-defaults",
        "--no-daemon",
        "--non-interactive",
        "exec",
        "--",
        "mise",
        "-C",
        str(repo_root),
        "run",
        "research-fanout",
        "--",
        *argv,
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "FNOX_PROFILE": "codex_research"},
            check=False,
        )
    except OSError as exc:
        sys.stderr.write(f"research-gate: invocation failed ({type(exc).__name__})\n")
        return 1
    sys.stdout.write(f"research-gate: invocation exited {completed.returncode}\n")
    return completed.returncode


if __name__ == "__main__":
    root = Path(os.environ.get("MISE_PROJECT_ROOT", Path.cwd())).resolve()
    raise SystemExit(main(sys.argv[1:], root))
