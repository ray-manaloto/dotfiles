# Copyright (c) 2026 Raymond Manaloto
"""Deadline-bound polling for files and shell commands."""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = logging.getLogger(__name__)
DEFAULT_INTERVAL_S = 15.0
MIN_INTERVAL_S = 1.0
TIMEOUT_EXIT_CODE = 124
PROCESS_TERM_GRACE_S = 0.2


@dataclass(frozen=True)
class WaitRequest:
    """One bounded condition: exactly one of ``file`` and ``command`` is set."""

    deadline_s: float
    file: Path | None = None
    command: str | None = None
    interval_s: float = DEFAULT_INTERVAL_S

    def target(self) -> str:
        """Human-readable condition for timeout diagnostics."""
        return (
            f"file {self.file}"
            if self.file is not None
            else f"command {self.command!r}"
        )


def _run_command(command: str, timeout_s: float) -> int:
    """Run one shell predicate within the polling budget."""
    process = subprocess.Popen(
        ["sh", "-c", command],
        start_new_session=True,
    )
    try:
        return process.wait(timeout=max(timeout_s, 0.001))
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=PROCESS_TERM_GRACE_S)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        return TIMEOUT_EXIT_CODE


def wait(
    request: WaitRequest,
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    command_runner: Callable[[str, float], int] = _run_command,
) -> int:
    """Poll until success or return the conventional timeout status 124."""
    if request.deadline_s <= 0:
        logger.error("bounded-wait: --deadline must be greater than zero")
        return 2
    if request.interval_s < MIN_INTERVAL_S:
        logger.error(
            "bounded-wait: --interval must be at least %.0f second",
            MIN_INTERVAL_S,
        )
        return 2
    if (request.file is None) == (request.command is None):
        logger.error("bounded-wait: exactly one of --file and --cmd is required")
        return 2

    expires_at = monotonic() + request.deadline_s
    while True:
        remaining = expires_at - monotonic()
        if request.file is not None:
            satisfied = request.file.exists()
        else:
            command = request.command or ""
            satisfied = remaining > 0 and command_runner(command, remaining) == 0
        if satisfied:
            logger.info("bounded-wait: satisfied %s", request.target())
            return 0

        remaining = expires_at - monotonic()
        if remaining <= 0:
            logger.error(
                "bounded-wait: DEADLINE EXPIRED after %.3fs waiting on %s",
                request.deadline_s,
                request.target(),
            )
            return TIMEOUT_EXIT_CODE
        sleeper(min(request.interval_s, remaining))


def main(request: WaitRequest) -> int:
    """CLI seam kept separate from argparse wiring in :mod:`main`."""
    return wait(request)
