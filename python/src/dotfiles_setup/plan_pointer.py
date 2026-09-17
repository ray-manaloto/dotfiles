# Copyright (c) 2026 Raymond Manaloto
"""Publish a tracked digest pointer to the active planning-with-files phase."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

PLAN_PATH = "task_plan.md"
POINTER_PATH = "docs/agents/plan-pointer.json"
_ACTIVE_HEADING = re.compile(r"(?im)^##\s+(?P<heading>[^\n]*NEXT SESSION[^\n]*)\s*$")


def active_phase(text: str) -> str | None:
    """Return the last level-two heading containing ``NEXT SESSION``."""
    matches = list(_ACTIVE_HEADING.finditer(text))
    return matches[-1].group("heading").strip() if matches else None


def payload(plan_bytes: bytes, *, recorded_at: datetime) -> dict[str, str] | None:
    """Build the task-text-free pointer payload, or ``None`` without a phase."""
    phase = active_phase(plan_bytes.decode(errors="replace"))
    if phase is None:
        return None
    return {
        "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "active_phase": phase,
        "recorded_at": recorded_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }


def write(
    repo_root: Path,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    """Refresh the tracked pointer and print a machine-readable failure token."""
    plan = repo_root / PLAN_PATH
    if not plan.is_file():
        sys.stderr.write(f"missing_active_plan: {PLAN_PATH} is absent\n")
        return 1
    plan_bytes = plan.read_bytes()
    data = payload(plan_bytes, recorded_at=now())
    if data is None:
        sys.stderr.write("missing_active_plan: no ## heading contains NEXT SESSION\n")
        return 1
    destination = repo_root / POINTER_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, separators=(",", ":")) + "\n")
    sys.stdout.write(
        f"plan-pointer: {POINTER_PATH} -> {data['active_phase']} "
        f"({data['plan_sha256']})\n"
    )
    return 0


def main(repo_root: Path) -> int:
    """CLI entry point."""
    return write(repo_root)
