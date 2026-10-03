# Copyright (c) 2026 Raymond Manaloto
"""Execute the session-start function hook through the pinned Bun runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
HARNESS = REPO_ROOT / "tests" / "fixtures" / "session_start_hook" / "harness.ts"
_BUN_TIMEOUT_S = 90
#: Every arm the harness runs; a dropped block changes the count and fails here.
_EXPECTED_ARMS = 33
_REGRESSIONS = [
    "r11-answered-object-text",
    "r11-unanswered-object-fallback",
    "r12-rename-resolution-before-record",
    "r12-rejected-rename-stays-pending",
    "r12-first-prompt-recovers-persisted-prefix",
    "r10-name-unknown-no-rename",
    "r12-repeat-start-recovers-unconfirmed-name",
    "s5-failed-pending-read-retries",
    "t5-pending-recovery-stops-after-three-failures",
    "t5-third-pending-read-can-succeed",
]


def test_session_start_hook_behaviour_under_bun() -> None:
    """The production register must pass every reload, naming and error arm."""
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
