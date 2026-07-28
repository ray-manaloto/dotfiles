"""Tests for the contract-token uniqueness gate (#394 step 4)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import token_audit
from dotfiles_setup.token_audit import (
    AMBIGUITY_ALLOWED,
    MANIFEST,
    find_ambiguous,
    find_violations,
    token_audit_main,
)

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_the_real_manifest_has_no_unexplained_ambiguity() -> None:
    """The gate itself. A failure here names the token and what to do."""
    assert find_violations(ROOT) == []


def test_every_allowlist_entry_is_still_ambiguous() -> None:
    """A stale entry must fail, so the map cannot rot (bash_budget's rule)."""
    keys = {a.key for a in find_ambiguous(ROOT)}
    assert set(AMBIGUITY_ALLOWED) <= keys


def test_the_allowlist_is_not_empty_and_every_entry_carries_a_reason() -> None:
    assert AMBIGUITY_ALLOWED
    assert all(reason.strip() for reason in AMBIGUITY_ALLOWED.values())


def _fixture(
    tmp_path: Path,
    tokens: str,
    body: str,
    monkeypatch: pytest.MonkeyPatch | None = None,
) -> Path:
    """A one-suite manifest, with the real allowlist swapped out.

    The allowlist names real repo paths, so against a fixture tree every entry
    reads as stale — which would drown the assertion under 18 unrelated lines.
    """
    if monkeypatch is not None:
        monkeypatch.setattr(token_audit, "AMBIGUITY_ALLOWED", {})
    (tmp_path / "python/verification").mkdir(parents=True)
    (tmp_path / MANIFEST).write_text(
        "[[suite]]\n"
        'name = "demo.suite"\n'
        'handler = "require_tokens"\n'
        'paths = ["target.txt"]\n'
        f'per_path_tokens = {{ "target.txt" = [{tokens}] }}\n'
    )
    (tmp_path / "target.txt").write_text(body)
    return tmp_path


def test_a_token_matching_twice_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixture(tmp_path, '"wire"', "wire here\nand wire there\n", monkeypatch)
    problems = find_violations(tmp_path)
    assert len(problems) == 1
    assert "matches 2x" in problems[0]


def test_a_token_matching_once_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control arm: without it the gate could be flagging everything."""
    _fixture(tmp_path, '"wire"', "wire here\nand nothing there\n", monkeypatch)
    assert find_violations(tmp_path) == []


def test_a_token_matching_zero_times_is_also_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Absent is not once. `require_tokens` fails too, but say WHY here."""
    _fixture(tmp_path, '"wire"', "nothing at all\n", monkeypatch)
    problems = find_violations(tmp_path)
    assert len(problems) == 1
    assert "matches 0x" in problems[0]


def test_main_returns_one_when_a_binding_is_ambiguous(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixture(tmp_path, '"wire"', "wire here\nand wire there\n", monkeypatch)
    assert token_audit_main(tmp_path) == 1


def test_main_returns_zero_on_the_real_repo() -> None:
    assert token_audit_main(ROOT) == 0


def test_an_allowlisted_entry_that_became_unique_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stale-entry direction, proved rather than asserted."""
    shutil.copytree(ROOT / "python/verification", tmp_path / "python/verification")
    monkeypatch.setattr(
        token_audit,
        "AMBIGUITY_ALLOWED",
        {**AMBIGUITY_ALLOWED, ("demo.suite", "gone.txt", "nope"): "stale on purpose"},
    )
    problems = find_violations(tmp_path)
    assert [p for p in problems if "is allowlisted but now matches exactly once" in p]
