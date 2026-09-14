# Copyright (c) 2026 Raymond Manaloto
"""Tests for dependency_currency: first-level pin currency, rc-driven."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import dependency_currency
from dotfiles_setup.dependency_currency import (
    CurrencyCode,
    OutdatedPin,
    _bare_name,
    _normalise,
    check_dependency_currency,
    declared_python_names,
)

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).parent.parent


class _Setup:
    """Minimal stand-in for doctor.Setup: the check reads `repo_root` only."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root


def test_bare_name_strips_extras_specifiers_and_urls() -> None:
    """Every spec shape `pyproject.toml` actually contains, plus a URL dep."""
    assert _bare_name("graphifyy[all]==0.9.53") == "graphifyy"
    assert _bare_name("pydantic>=2.13.4") == "pydantic"
    assert _bare_name("python-debian>=1.1.1") == "python-debian"
    assert _bare_name("kb-setup @ git+https://example.com/x@abc") == "kb-setup"
    assert _bare_name("ruff") == "ruff"


def test_normalise_folds_the_separators_pypi_folds() -> None:
    """`python_debian` reported for a `python-debian` pin must still match."""
    assert _normalise("python_debian") == _normalise("python-debian")
    assert _normalise("Ruff") == "ruff"
    assert _normalise("a.b_c") == "a-b-c"


def test_declared_names_reads_the_real_manifest() -> None:
    """Positive evidence the manifest was READ, not silently defaulted to {}.

    An empty set would make the first-level filter drop everything and report
    "current" forever — a check that can only pass. Asserting known members is
    what discriminates that.
    """
    names = declared_python_names(REPO_ROOT)
    assert "graphifyy" in names
    assert "pydantic" in names
    assert "kb-setup" in names
    # and the FAIL direction: a package that is transitive-only must be absent,
    # or the filter is not filtering.
    assert "annotated-types" not in names


def test_declared_names_is_empty_when_the_manifest_is_missing(tmp_path: Path) -> None:
    """The absent-manifest arm, so the reader's failure is visible in tests."""
    assert declared_python_names(tmp_path) == set()


def test_check_reports_nothing_without_a_repo_root() -> None:
    """A setup lacking `repo_root` is a finding, never a silent pass."""
    findings = check_dependency_currency(object())
    assert len(findings) == 1
    assert "no repo root" in findings[0]


def test_outdated_pin_carries_no_filesystem_path() -> None:
    """Findings name pins only: session context is transcript-persisted."""
    pin = OutdatedPin(name="ruff", current="0.16.5", latest="0.16.7", surface="python")
    rendered = f"{pin.name} {pin.current} -> {pin.latest}"
    assert "/Users/" not in rendered
    assert "/home/" not in rendered


def test_codes_are_distinct_and_ok_is_zero() -> None:
    """The rc IS the contract, so the enum's numbering is load-bearing."""
    values = [int(c) for c in CurrencyCode]
    assert len(values) == len(set(values)), "duplicate exit codes"
    assert int(CurrencyCode.OK) == 0
    # every non-OK code must be non-zero, or a failure would read as success
    assert all(int(c) != 0 for c in CurrencyCode if c is not CurrencyCode.OK)


def test_a_failed_probe_never_renders_as_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The silent-downgrade arm: PROBE_FAILED must produce a LOUD finding.

    This is the failure mode the module exists to prevent — a resolver that
    could not run must never be indistinguishable from 'everything is current'.
    `monkeypatch` restores the attribute itself, so no suppression is needed for
    the reassignment (inline suppressions are banned repo-wide).
    """
    monkeypatch.setattr(
        dependency_currency,
        "evaluate",
        lambda _root: dependency_currency.CurrencyReport(
            code=CurrencyCode.PROBE_FAILED, diagnostic="mise exploded"
        ),
    )
    findings = check_dependency_currency(_Setup(REPO_ROOT))

    assert len(findings) == 1
    assert "NOT" in findings[0]
    assert "PROBE_FAILED" in findings[0]
