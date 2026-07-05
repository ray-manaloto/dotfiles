"""Tests for the GHCR retention planner (#160 T12.5, decision 13)."""

from __future__ import annotations

from typing import Any

from dotfiles_setup.ghcr_cleanup import plan_cleanup


def _version(vid: int, created: str, *tags: str) -> dict[str, Any]:
    return {
        "id": vid,
        "created_at": created,
        "metadata": {"container": {"tags": list(tags)}},
    }


_HASH = "0123456789abcdef"


def test_untagged_versions_are_never_deleted() -> None:
    plan = plan_cleanup([_version(1, "2026-07-01T00:00:00Z")])
    assert plan.delete == []
    assert "untagged" in plan.keep_reasons[1]


def test_protected_tags_are_never_deleted() -> None:
    plan = plan_cleanup(
        [
            _version(1, "2026-07-01T00:00:00Z", "dev"),
            _version(2, "2026-06-01T00:00:00Z", "latest"),
        ],
        keep_per_family=0,
    )
    assert plan.delete == []


def test_non_hash_family_tags_are_never_deleted() -> None:
    plan = plan_cleanup(
        [_version(1, "2026-07-01T00:00:00Z", "pr-123")], keep_per_family=0
    )
    assert plan.delete == []
    assert "non-hash-family" in plan.keep_reasons[1]


def test_keeps_newest_n_per_family_and_deletes_the_rest() -> None:
    versions = [
        _version(1, "2026-07-04T00:00:00Z", f"base-{_HASH}"),
        _version(2, "2026-07-03T00:00:00Z", f"base-{_HASH}"),
        _version(3, "2026-07-02T00:00:00Z", f"base-{_HASH}"),
        _version(4, "2026-07-01T00:00:00Z", f"p2996-{_HASH}"),
    ]
    plan = plan_cleanup(versions, keep_per_family=2)
    assert [v["id"] for v in plan.delete] == [3]
    assert 4 in plan.keep_reasons  # p2996 family has its own window


def test_windows_are_per_family_not_global() -> None:
    versions = [
        _version(1, "2026-07-04T00:00:00Z", f"base-{_HASH}"),
        _version(2, "2026-07-03T00:00:00Z", f"dev-{_HASH}"),
        _version(3, "2026-07-02T00:00:00Z", f"p2996-{_HASH}"),
    ]
    plan = plan_cleanup(versions, keep_per_family=1)
    assert plan.delete == []


def test_multi_tag_version_kept_while_any_family_window_open() -> None:
    versions = [
        _version(1, "2026-07-04T00:00:00Z", f"base-{_HASH}"),
        _version(2, "2026-07-03T00:00:00Z", f"base-{_HASH}", f"dev-{_HASH}"),
    ]
    plan = plan_cleanup(versions, keep_per_family=1)
    # id=2's base tag is past the window but its dev tag is within — kept.
    assert plan.delete == []
