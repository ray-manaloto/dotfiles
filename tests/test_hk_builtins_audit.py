# Copyright (c) 2026 Raymond Manaloto
"""Tests for the generated hk-builtins audit."""

from __future__ import annotations

from pathlib import Path

from dotfiles_setup import hk_builtins_audit as audit

ROOT = Path(__file__).resolve().parent.parent


def test_the_committed_doc_matches_the_generator() -> None:
    """The gate itself: if this fails, run `mise run hk-audit`."""
    assert audit.hk_builtins_audit_main(ROOT, check=True) == 0


def test_not_adopted_names_are_real_builtins_and_none_are_wired() -> None:
    available = audit.available_builtins()
    assert len(available) > 100, "hk builtins returned an implausibly short list"
    wired = audit.wired_builtins(ROOT, available)
    assert audit.stale_entries(available, wired) == []


def test_stale_entries_fires_on_a_name_that_is_not_a_builtin() -> None:
    """Control arm: the staleness check must be able to return the other answer."""
    problems = audit.stale_entries(["ruff", "gitleaks"], {})
    assert problems, "a NOT_ADOPTED map full of non-builtins produced no complaint"
    assert all("not a builtin" in p for p in problems)


def test_stale_entries_fires_when_a_declined_builtin_is_wired() -> None:
    declined = next(iter(audit.NOT_ADOPTED))
    problems = audit.stale_entries(list(audit.NOT_ADOPTED), {declined: ["hk.pkl"]})
    assert [p for p in problems if "IS wired" in p]


def test_wired_builtins_finds_the_scanners_and_names_their_config() -> None:
    wired = audit.wired_builtins(ROOT, audit.available_builtins())
    assert wired["gitleaks"] == ["hk-common.pkl"]
    # betterleaks is host-only and lives in the project config: hk-common.pkl
    # is spread into hk-image.pkl, and a tool referenced there must also be in
    # the image — which costs a cold base rebuild.
    assert wired["betterleaks"] == ["hk.pkl"]


def test_a_custom_step_is_not_reported_as_a_wired_builtin() -> None:
    """`ruff_format` is a custom step sharing a builtin's name.

    Conflating the two is exactly what the hand-written audit did.
    """
    available = audit.available_builtins()
    assert "ruff_format" in available
    assert "ruff_format" not in audit.wired_builtins(ROOT, available)
    assert "ruff_format" in audit.defined_steps(ROOT)


def test_check_mode_fails_on_a_modified_doc(tmp_path: Path) -> None:
    """Both arms of the gate, against a copy so the real doc is untouched."""
    for name in (*audit.CONFIGS, "docs/hk-builtins-audit.md"):
        src = ROOT / name
        dst = tmp_path / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text())
    assert audit.hk_builtins_audit_main(tmp_path, check=True) == 0

    doc = tmp_path / audit.DOC_PATH
    doc.write_text(doc.read_text().replace("## Wired builtins", "## Wired builtinz"))
    assert audit.hk_builtins_audit_main(tmp_path, check=True) == 1
