# Copyright (c) 2026 Raymond Manaloto
"""Execute the claude-doctor function hook through the pinned Bun runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
HARNESS = REPO_ROOT / "tests" / "fixtures" / "claude_doctor_hook" / "harness.ts"
_BUN_TIMEOUT_S = 90


def test_claude_doctor_hook_behaviour_under_bun() -> None:
    """The production register function must pass every deny and repair arm."""
    completed = subprocess.run(
        ["mise", "exec", "--", "bun", "run", str(HARNESS)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=_BUN_TIMEOUT_S,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["arms"] == 20
