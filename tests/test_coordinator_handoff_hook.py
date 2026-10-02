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
_EXPECTED_ARMS = 23


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
    assert json.loads(completed.stdout) == {"arms": _EXPECTED_ARMS}
