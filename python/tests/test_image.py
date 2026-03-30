"""Tests for image smoke test module."""

from __future__ import annotations

from dotfiles_setup.image import build_smoke_script


def test_build_smoke_script_returns_bash() -> None:
    """Verify build_smoke_script produces a valid bash smoke script."""
    script = build_smoke_script()
    assert script.startswith("set -euo pipefail")
    assert "mise" in script
    assert "hk" in script
