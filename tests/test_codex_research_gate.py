# Copyright (c) 2026 Raymond Manaloto
"""Public hook-wire controls for the Codex research coverage gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).parent.parent / "scripts" / "codex-research-gate.py"


def _invoke(tmp_path: Path, event: dict[str, object]) -> dict[str, object]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
        timeout=3,
        check=True,
    )
    return json.loads(result.stdout)


def test_research_turn_requires_receipt_and_allows_honest_failure(
    tmp_path: Path,
) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    started = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Research Codex hooks",
        },
    )
    submit_output = started["hookSpecificOutput"]
    assert isinstance(submit_output, dict)
    context = submit_output["additionalContext"]
    assert isinstance(context, str)
    assert "--strict-five" in context
    blocked = _invoke(tmp_path, {**base, "hook_event_name": "Stop"})
    assert blocked["decision"] == "block"
    reason = blocked["reason"]
    assert isinstance(reason, str)
    assert "Research coverage failed" in reason
    incomplete = _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "Stop",
            "stop_hook_active": True,
            "last_assistant_message": (
                "RESEARCH INCOMPLETE: Exa authentication failed."
            ),
        },
    )
    assert "systemMessage" in incomplete


def test_unrelated_turn_and_heartbeat_do_not_trigger_gate(tmp_path: Path) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-2"}
    assert (
        _invoke(
            tmp_path,
            {
                **base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Format this sentence",
            },
        )
        == {}
    )
    assert _invoke(tmp_path, {**base, "hook_event_name": "Stop"}) == {}
    assert (
        _invoke(
            tmp_path,
            {
                **base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "<heartbeat>research</heartbeat>",
            },
        )
        == {}
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Compare uv and Poetry for Python dependency management.", "gated"),
        ("Find the latest fnox version.", "gated"),
        ("Research Codex agent workflows.", "gated"),
        ("Print the current directory.", "ordinary"),
        ("Rename the variable sources to inputs.", "ordinary"),
        ("Compare these two local functions.", "ordinary"),
    ],
)
def test_research_trigger_matches_external_requests(
    tmp_path: Path, prompt: str, expected: str
) -> None:
    result = _invoke(
        tmp_path,
        {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
        },
    )
    assert bool(result) is (expected == "gated")


def test_malformed_manifest_returns_block_decision(tmp_path: Path) -> None:
    base = {"session_id": "session-1", "turn_id": "turn-1"}
    _invoke(
        tmp_path,
        {
            **base,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Research Codex hooks",
        },
    )
    manifest = (
        tmp_path
        / ".codex"
        / "research-coverage"
        / "session-1"
        / "turn-1"
        / "manifest.json"
    )
    manifest.write_text("[]", encoding="utf-8")
    result = _invoke(tmp_path, {**base, "hook_event_name": "Stop"})
    assert result["decision"] == "block"
    reason = result["reason"]
    assert isinstance(reason, str)
    assert "malformed research manifest" in reason
