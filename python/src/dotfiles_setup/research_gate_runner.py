# Copyright (c) 2026 Raymond Manaloto
"""Run research through the pinned, noninteractive fnox research profile."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotfiles_setup import research_gate_outcome
from dotfiles_setup.codex_research_gate import record_incomplete


def _record_failure(argv: list[str], repo_root: Path, error: str) -> None:
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--request-id")
    parser.add_argument("--strict-five", action="store_true")
    try:
        args, _ = parser.parse_known_args(argv)
        if not args.strict_five or args.out is None or args.request_id is None:
            return
        out = args.out.expanduser()
        if not out.is_absolute():
            out = repo_root / out
        failures = (
            research_gate_outcome.failed_routes(out / "manifest.json", args.request_id)
            if error == "ProcessExitError"
            else [{"route": "fnox", "error_class": error}]
        )
        record_incomplete(out / "required.json", args.request_id, failures)
    except (OSError, ValueError, TypeError, argparse.ArgumentError) as exc:
        sys.stderr.write(
            f"research-gate: INCOMPLETE outcome unavailable ({type(exc).__name__})\n"
        )


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
        error = type(exc).__name__
        if error not in {"FileNotFoundError", "PermissionError", "TimeoutError"}:
            error = "OSError"
        _record_failure(argv, repo_root, error)
        sys.stderr.write(f"research-gate: invocation failed ({type(exc).__name__})\n")
        return 1
    if completed.returncode != 0:
        _record_failure(argv, repo_root, "ProcessExitError")
    sys.stdout.write(f"research-gate: invocation exited {completed.returncode}\n")
    return completed.returncode


if __name__ == "__main__":
    root = Path(os.environ.get("MISE_PROJECT_ROOT", Path.cwd())).resolve()
    raise SystemExit(main(sys.argv[1:], root))
