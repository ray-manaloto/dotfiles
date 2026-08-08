# Copyright (c) 2026 Raymond Manaloto
"""Tests for the Renovate status signal (dotfiles_setup.renovate)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import renovate
from dotfiles_setup.renovate import RenovateStatus


def test_missing_permissions_all_present() -> None:
    granted = {
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "checks": "write",
        "statuses": "write",
        "metadata": "read",
    }
    assert renovate.permission_gaps({"permissions": granted}) == []


def test_missing_permissions_flags_gaps() -> None:
    # pull_requests granted read-only, issues absent entirely.
    granted = {"contents": "write", "pull_requests": "read", "checks": "write"}
    missing = renovate.permission_gaps({"permissions": granted})
    assert "pull_requests=write" in missing
    assert "issues=write" in missing
    assert "statuses=write" in missing
    assert "contents=write" not in missing


def test_missing_permissions_no_permissions_key() -> None:
    # A malformed record with no permissions is fully missing, not a crash.
    assert renovate.permission_gaps({}) == [
        f"{name}={want}" for name, want in renovate.REQUIRED_PERMISSIONS.items()
    ]


def test_status_healthy_requires_install_and_full_privileges() -> None:
    assert RenovateStatus(repo="o/r", owner="o", installed=False).healthy is False
    assert (
        RenovateStatus(
            repo="o/r", owner="o", installed=True, missing_permissions=["issues=write"]
        ).healthy
        is False
    )
    assert RenovateStatus(repo="o/r", owner="o", installed=True).healthy is True


def test_render_report_not_installed_points_to_install_url() -> None:
    report = renovate.render_report(
        RenovateStatus(
            repo="ray-manaloto/dotfiles", owner="ray-manaloto", installed=False
        )
    )
    assert "NOT installed" in report
    assert "github.com/apps/renovate" in report


def test_render_report_verifies_mend_app_id() -> None:
    report = renovate.render_report(
        RenovateStatus(
            repo="o/r",
            owner="o",
            installed=True,
            app_id=renovate.RENOVATE_APP_ID,
            repository_selection="all",
            open_prs=[{"number": "190", "title": "update mise"}],
            merged_prs=[{"number": "191", "title": "update lefthook"}],
        )
    )
    assert "verified Mend-hosted Renovate" in report
    assert "Open update PRs (1)" in report
    assert "#190 update mise" in report
    assert "Recently merged (1)" in report


def test_render_report_warns_on_unexpected_app_id() -> None:
    report = renovate.render_report(
        RenovateStatus(repo="o/r", owner="o", installed=True, app_id=9999)
    )
    assert "not the expected" in report
    assert str(renovate.RENOVATE_APP_ID) in report
