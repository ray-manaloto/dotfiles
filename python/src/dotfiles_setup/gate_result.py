# Copyright (c) 2026 Raymond Manaloto
"""Typed, durable results for declared repository gates."""

from __future__ import annotations

import argparse
import enum
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Final
from urllib.parse import quote

from dotfiles_setup import codec

__all__ = [
    "GATE_COMMANDS",
    "RESULTS_DIR",
    "STATUS_EXIT_CODES",
    "GateResult",
    "GateStatus",
    "gate_main",
    "generate_schema",
    "read_result",
    "result_path",
    "run_gate",
]


class GateStatus(enum.StrEnum):
    """The complete set of outcomes exposed by a gate result."""

    PASSED = "passed"
    FAILED = "failed"
    TOOL_MISSING = "tool_missing"
    TIMED_OUT = "timed_out"
    NOT_A_GATE = "not_a_gate"


class GateResult(codec.Struct, frozen=True):
    """One gate execution outcome and the command that produced it."""

    gate: str
    status: GateStatus
    returncode: int
    duration_s: float
    command: tuple[str, ...]
    failures: tuple[str, ...] = ()
    log_path: str | None = None


RESULTS_DIR: Final = ".agent/gate-results"

# This is policy data, not discovery. Unknown names never become commands.
GATE_COMMANDS: Final[dict[str, tuple[str, ...]]] = {
    "lint": ("mise", "run", "lint"),
    "pytest": ("uv", "run", "--project", "python", "pytest", "tests/", "-x", "-q"),
    "verify": ("mise", "run", "verify"),
    "lint-docs": ("mise", "run", "lint-docs"),
    "pin-actions": ("mise", "run", "pin-actions"),
}

# Shell-compatible exit codes let callers use the JSON or only the process rc.
STATUS_EXIT_CODES: Final[dict[GateStatus, int]] = {
    GateStatus.PASSED: 0,
    GateStatus.FAILED: 1,
    GateStatus.TOOL_MISSING: 127,
    GateStatus.TIMED_OUT: 124,
    GateStatus.NOT_A_GATE: 2,
}

_FAILURE_LINE = re.compile(r"\b(?:error|fail|failed|failure)\b", re.IGNORECASE)


def result_path(repo_root: Path, gate: str) -> Path:
    """Return the deterministic result path for ``gate`` below ``repo_root``."""
    safe_gate = quote(gate, safe="-_.")
    return repo_root / RESULTS_DIR / f"{safe_gate}.json"


def _log_path(repo_root: Path, gate: str) -> Path:
    """Return the deterministic human-readable output path for ``gate``."""
    safe_gate = quote(gate, safe="-_.")
    return repo_root / RESULTS_DIR / f"{safe_gate}.log"


def _status_for(
    returncode: int,
    *,
    known: bool = True,
    tool_missing: bool = False,
    timed_out: bool = False,
) -> GateStatus:
    """Derive exactly one status for every reachable termination state.

    A real child return code of zero passes. Every other real child return code
    defaults to ``FAILED``. An observed timeout takes precedence over that
    default while retaining the child's post-kill return code. Unknown names
    and missing executables have no child return code and use explicit
    sentinels.
    """
    if not known:
        return GateStatus.NOT_A_GATE
    if tool_missing:
        return GateStatus.TOOL_MISSING
    if timed_out:
        return GateStatus.TIMED_OUT
    if returncode == 0:
        return GateStatus.PASSED
    return GateStatus.FAILED


def _failure_lines(output: bytes) -> tuple[str, ...]:
    """Extract concise failure-bearing lines while retaining the full log."""
    text = output.decode(errors="replace")
    return tuple(line for line in text.splitlines() if _FAILURE_LINE.search(line))


def _write_result(repo_root: Path, result: GateResult) -> None:
    """Encode and atomically publish a typed result."""
    path = result_path(repo_root, result.gate)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_bytes(codec.encode(result) + b"\n")
    temporary.replace(path)


def run_gate(repo_root: Path, gate: str, timeout_s: float | None = None) -> GateResult:
    """Run one declared gate, capturing output without a shell pipeline.

    A process that starts retains its exact return code, including the
    post-``kill`` return code when it exceeds its deadline. Conventional 127
    and 2 sentinel values are used only when no child starts because the
    executable is missing or the gate name is unknown. The CLI maps the typed
    ``TIMED_OUT`` status to 124 independently of the child's return code.
    """
    command = GATE_COMMANDS.get(gate)
    if command is None:
        result = GateResult(
            gate=gate,
            status=_status_for(STATUS_EXIT_CODES[GateStatus.NOT_A_GATE], known=False),
            returncode=STATUS_EXIT_CODES[GateStatus.NOT_A_GATE],
            duration_s=0.0,
            command=(),
        )
        _write_result(repo_root, result)
        return result

    log_path = _log_path(repo_root, gate)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        process = subprocess.Popen(
            command,
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            output, _ = process.communicate(timeout=timeout_s)
            returncode = process.returncode
            if returncode is None:
                msg = "gate process was reaped without a return code"
                raise RuntimeError(msg)
            status = _status_for(returncode)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
            returncode = process.returncode
            if returncode is None:
                msg = "timed-out gate process was reaped without a return code"
                raise RuntimeError(msg) from None
            status = _status_for(returncode, timed_out=True)
    except FileNotFoundError as error:
        output = f"{error}\n".encode()
        returncode = STATUS_EXIT_CODES[GateStatus.TOOL_MISSING]
        status = _status_for(returncode, tool_missing=True)

    duration_s = time.perf_counter() - started
    log_path.write_bytes(output)
    result = GateResult(
        gate=gate,
        status=status,
        returncode=returncode,
        duration_s=duration_s,
        command=command,
        failures=_failure_lines(output),
        log_path=str(log_path),
    )
    _write_result(repo_root, result)
    return result


def read_result(repo_root: Path, gate: str) -> GateResult | None:
    """Read and validate a stored gate result, or return ``None`` if absent."""
    path = result_path(repo_root, gate)
    if not path.is_file():
        return None
    return codec.decode(path.read_bytes(), GateResult)


def generate_schema() -> dict[str, object]:
    """Generate the JSON Schema directly from the canonical result model."""
    return codec.schema(GateResult)


def _emit_result(result: GateResult) -> None:
    """Write one result as JSON to stdout."""
    sys.stdout.write(codec.encode(result).decode() + "\n")


def gate_main(argv: list[str] | None = None) -> int:
    """Run or read a gate result and return the status-derived exit code."""
    parser = argparse.ArgumentParser(prog="dotfiles-setup gate")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="action", required=True)

    run_parser = subparsers.add_parser("run", help="Run a declared gate")
    run_parser.add_argument("name")
    run_parser.add_argument("--timeout", type=float, default=None)

    read_parser = subparsers.add_parser("read", help="Read a stored gate result")
    read_parser.add_argument("name")

    args = parser.parse_args(argv)
    if args.action == "run":
        result = run_gate(args.repo_root, args.name, timeout_s=args.timeout)
    else:
        result = read_result(args.repo_root, args.name)
        if result is None:
            sys.stderr.write(f"no stored result for gate {args.name!r}\n")
            return STATUS_EXIT_CODES[GateStatus.NOT_A_GATE]

    _emit_result(result)
    return STATUS_EXIT_CODES[result.status]


if __name__ == "__main__":
    raise SystemExit(gate_main())
