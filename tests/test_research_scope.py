# Copyright (c) 2026 Raymond Manaloto
"""Public caller research-scope directive controls."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.research_scope import directive, near_miss


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
    assert directive(prompt) is None


@pytest.mark.parametrize(
    ("prompt", "scope"),
    [
        ("[research-scope: implementation]\nResearch uv", "implementation"),
        ("[research-scope: text-edit]\nReword the README", "text-edit"),
        ("[research-scope: research]\nImplement the bump", "research"),
        ("[research-scope: research]\r\nImplement the bump", "research"),
        ("[research-scope: local-only]\nInvestigate", "local-only"),
        ("[research-scope: anything]\nResearch uv", None),
        ("> [research-scope: implementation]\nResearch uv", None),
        ("Research uv\n[research-scope: implementation]", None),
        (" [research-scope: implementation]\nResearch uv", None),
    ],
)
def test_directive_is_read_only_from_exact_caller_first_line(
    prompt: str, scope: str | None
) -> None:
    assert directive(prompt) == scope


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("[research-scope: research]\nFix it.", False),
        ("Fix it.\n[research-scope: researc]", False),
        ("[research] notes", False),
        ("﻿ [Research-Scope: research]\nFix it.", True),
        ("[research-scope: bogus]\nFix it.", True),
    ],
)
def test_near_miss_flags_only_an_inexact_first_line_directive(
    prompt: str, *, expected: bool
) -> None:
    assert near_miss(prompt) is expected
