# Copyright (c) 2026 Raymond Manaloto
"""Tests for the tracked plan digest pointer."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import plan_pointer
from dotfiles_setup.main import setup_parser


def test_last_next_session_heading_is_the_only_recorded_phase(tmp_path: Path) -> None:
    plan = tmp_path / "task_plan.md"
    plan.write_text(
        "# Plan\n\n## Phase 1 — NEXT SESSION\nold task text\n"
        "\n## Notes\nnot active\n\n## Phase 7 — Next Session\nsecret task body\n"
    )
    frozen = datetime(2026, 9, 16, 12, 30, tzinfo=UTC)

    assert plan_pointer.write(tmp_path, now=lambda: frozen) == 0

    pointer = json.loads((tmp_path / plan_pointer.POINTER_PATH).read_text())
    assert pointer == {
        "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
        "active_phase": "Phase 7 — Next Session",
        "recorded_at": "2026-09-16T12:30:00Z",
    }
    assert "secret task body" not in json.dumps(pointer)


def test_missing_active_heading_fails_without_writing_a_pointer(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "task_plan.md").write_text("# Plan\n\n## Phase 1\n")

    assert plan_pointer.write(tmp_path) == 1
    assert not (tmp_path / plan_pointer.POINTER_PATH).exists()
    captured = capsys.readouterr()
    assert "missing_active_plan" in captured.err


def test_public_cli_registers_plan_pointer() -> None:
    parsed = setup_parser().parse_args(["plan-pointer"])
    assert parsed.command == "plan-pointer"
