# Copyright (c) 2026 Raymond Manaloto
"""Execute the coordinator-handoff function hook through the pinned Bun runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
HARNESS = REPO_ROOT / "tests" / "fixtures" / "coordinator_handoff_hook" / "harness.ts"
_BUN_TIMEOUT_S = 90
#: Every arm the harness runs; a dropped block changes the count and fails here.
_EXPECTED_ARMS = 40
_REGRESSIONS = [
    "s1-probe-three-measurements-one-command",
    "s1-dry-run-once-per-preview-level",
    "s4-lane-at-most-two-role-queries",
    "r4-role-cache-keyed-by-session",
    "r4-event-getter-fail-open",
    "r3-list-failure-releases-level",
    "r3-release-failure-visible",
    "r1-already-launched-heartbeat",
    "r4-concurrent-first-role-query",
    "s1-dry-run-toast-once",
    "s4-transient-miss-recovers-at-limit",
    "t5-negative-role-cache-expires-at-ten-minutes",
    "s2-launch-in-progress-heartbeat",
    "t4-failed-probe-releases-and-reports-failure",
    "t4-probe-done-only-after-command-resolution",
    "t4-release-failure-never-reports-probe-done",
    "t4-confirmation-failure-keeps-accurate-error",
]


def test_coordinator_handoff_hook_behaviour_under_bun() -> None:
    """The production register must pass every pre-filter, fire and error arm."""
    completed = subprocess.run(
        ["mise", "exec", "--", "bun", "run", str(HARNESS)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=_BUN_TIMEOUT_S,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout) == {
        "arms": _EXPECTED_ARMS,
        "regressions": _REGRESSIONS,
    }
