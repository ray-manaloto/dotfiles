# Copyright (c) 2026 Raymond Manaloto
"""Public caller submission binding and request-integrity controls."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.research_scope import bind_submission, validates_binding

_PROMPT = "[research-scope: local-only]\nInvestigate saved local research evidence."


def test_submission_binding_rechecks_actual_prompt_session_and_turn() -> None:
    binding = bind_submission(_PROMPT, "session-1", "turn-1")
    assert validates_binding(binding, "session-1", "turn-1", _PROMPT)
    assert not validates_binding(binding, "session-2", "turn-1", _PROMPT)
    assert not validates_binding(binding, "session-1", "turn-2", _PROMPT)
    assert not validates_binding(binding, "session-1", "turn-1", _PROMPT + "changed")


@pytest.mark.parametrize(
    "prompt",
    [
        "Research Codex hooks",
        "> [research-scope: local-only]\nResearch Codex hooks",
        "Quoted:\n[research-scope: local-only]\nResearch Codex hooks",
        "```\n[research-scope: local-only]\n```\nResearch Codex hooks",
        " [research-scope: local-only]\nResearch Codex hooks",
        "[research-scope: local-only] trailing text\nResearch Codex hooks",
    ],
)
def test_only_exact_caller_first_line_can_declare_scope(prompt: str) -> None:
    assert bind_submission(prompt, "session-1", "turn-1") is None


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("session_id", "session-2"),
        ("turn_id", "turn-2"),
        ("source", "Stop"),
        ("scope", "strict-five"),
        ("prompt_sha256", "0" * 64),
        ("binding_sha256", "0" * 64),
        ("prompt_sha256", None),
    ],
)
def test_changed_binding_is_refused(key: str, value: object) -> None:
    original = bind_submission(_PROMPT, "session-1", "turn-1")
    assert original is not None
    changed: dict[str, object] = {**original, key: value}
    assert not validates_binding(changed, "session-1", "turn-1")


@pytest.mark.parametrize("binding", [None, {}, [], {"scope": "local-only"}])
def test_absent_or_model_declared_scope_has_no_submission_authority(
    binding: object,
) -> None:
    assert not validates_binding(binding, "session-1", "turn-1")
