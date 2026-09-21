# Copyright (c) 2026 Raymond Manaloto
"""Execute the claude-doctor function hook through the pinned Bun runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
HARNESS = REPO_ROOT / "tests" / "fixtures" / "claude_doctor_hook" / "harness.ts"
CLAUDE_REGISTER = (
    REPO_ROOT / ".claude" / "skills" / "claude-doctor" / "hooks" / "register.ts"
)
AGENTS_REGISTER = (
    REPO_ROOT / ".agents" / "skills" / "claude-doctor" / "hooks" / "register.ts"
)
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
    case_alias_exercised = payload["case_alias_exercised"]
    case_alias_skipped_reason = payload["case_alias_skipped_reason"]
    assert case_alias_exercised or (
        isinstance(case_alias_skipped_reason, str) and case_alias_skipped_reason
    ), "the case-alias arm must run or name why the filesystem cannot exercise it"
    assert payload["arms"] == 42 + int(case_alias_exercised)


def test_claude_doctor_hook_copies_are_byte_identical() -> None:
    """The hand-maintained .agents copy must never drift from production."""
    assert CLAUDE_REGISTER.read_bytes() == AGENTS_REGISTER.read_bytes()
