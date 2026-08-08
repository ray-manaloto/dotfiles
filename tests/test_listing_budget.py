# Copyright (c) 2026 Raymond Manaloto
"""Tests for the skill/agent listing budget — the standing class no gate saw.

Every test here drives a FIXTURE tree rather than the real `~/.claude`, because
the module's whole subject is host state and a test that read the operator's
live plugin cache would pass or fail for reasons unrelated to the code.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dotfiles_setup import doctor
from dotfiles_setup.listing_budget import (
    SKILL_DESCRIPTION_MAX,
    collect_listing,
    over_cap,
    plugin_root,
    total_chars,
)


def _skill(root: Path, name: str, description: str, when_to_use: str = "") -> None:
    path = root / "skills" / name
    path.mkdir(parents=True, exist_ok=True)
    extra = f"when_to_use: {when_to_use}\n" if when_to_use else ""
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n{extra}---\n\nBody.\n"
    )


def _agent(root: Path, name: str, description: str) -> None:
    path = root / "agents"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{name}.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nBody.\n"
    )


def test_project_skills_and_agents_are_both_counted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "alpha", "does alpha things")
    _agent(repo / ".claude", "beta", "does beta things")

    entries = collect_listing(repo, tmp_path / "home", [])

    assert {(e.kind, e.name) for e in entries} == {
        ("skill", "alpha"),
        ("agent", "beta"),
    }
    assert all(e.source == "project" for e in entries)
    # The listing carries name + description, not the body.
    assert total_chars(entries) == len("alpha") + len("does alpha things") + len(
        "beta"
    ) + len("does beta things")


def test_when_to_use_counts_toward_the_cost(tmp_path: Path) -> None:
    """The cap is on description + when_to_use COMBINED, so the cost must be too."""
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "alpha", "short", when_to_use="also this")

    (entry,) = collect_listing(repo, tmp_path / "home", [])

    assert "also this" not in entry.name
    assert entry.desc_chars == len("short also this")


def test_body_size_does_not_change_the_listing_cost(tmp_path: Path) -> None:
    """A 50 KB SKILL.md costs the same standing as a 1 KB one — only the body differs.

    This is the whole premise of progressive disclosure, so it is asserted rather
    than assumed: if it were false, moving a rule's bytes into a skill would buy
    nothing.
    """
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "alpha", "does alpha things")
    before = total_chars(collect_listing(repo, tmp_path / "home", []))

    path = repo / ".claude" / "skills" / "alpha" / "SKILL.md"
    path.write_text(path.read_text() + "\n" + ("x" * 50_000))

    assert total_chars(collect_listing(repo, tmp_path / "home", [])) == before


def test_only_enabled_plugins_are_counted(tmp_path: Path) -> None:
    """The 20x-overstatement guard.

    The first real measurement globbed the whole plugin cache and reported 2,164
    skills. The cache holds every version of every plugin, enabled or not — so a
    plugin present on disk but absent from the enabled list must contribute
    nothing.
    """
    home = tmp_path / "home"
    cache = home / ".claude" / "plugins" / "cache"
    _skill(cache / "mkt" / "wanted" / "1.0.0", "kept", "counted")
    _skill(cache / "mkt" / "unwanted" / "1.0.0", "dropped", "not counted")

    entries = collect_listing(tmp_path / "repo", home, ["wanted@mkt"])

    assert [e.name for e in entries] == ["kept"]
    assert entries[0].source == "plugin:wanted"


def test_the_newest_numeric_version_wins_not_the_newest_mtime(tmp_path: Path) -> None:
    """The defect this module was written around.

    An mtime heuristic picked 0.20.0 while the live plugin was 0.22.2, and an
    edit went to the wrong file. Touching a file INSIDE a version directory does
    not move that directory's own mtime, so mtime cannot see it — the arm below
    makes the superseded directory the most recently modified one and confirms
    the resolver is not fooled.
    """
    home = tmp_path / "home"
    base = home / ".claude" / "plugins" / "cache" / "mkt" / "plug"
    for version in ("0.20.0", "0.22.2", "0.9.0"):
        _skill(base / version, "s", f"version {version}")
    # Make the SUPERSEDED directory the newest by mtime — the trap.
    (base / "0.20.0").touch()

    resolved = plugin_root(home, "plug@mkt")
    assert resolved is not None
    assert resolved.name == "0.22.2"


def test_a_non_numeric_version_directory_does_not_raise(tmp_path: Path) -> None:
    """`builder-skills` pins a git sha, not a version."""
    home = tmp_path / "home"
    base = home / ".claude" / "plugins" / "cache" / "mkt" / "plug"
    _skill(base / "5f76017788f3", "s", "sha-pinned")

    resolved = plugin_root(home, "plug@mkt")
    assert resolved is not None
    assert resolved.name == "5f76017788f3"


def test_an_unreadable_file_is_skipped_not_fatal(tmp_path: Path) -> None:
    """A dangling symlink in the cache is normal; it must not crash the doctor."""
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "alpha", "fine")
    broken = repo / ".claude" / "skills" / "gone"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").symlink_to(tmp_path / "nowhere")

    assert [e.name for e in collect_listing(repo, tmp_path / "home", [])] == ["alpha"]


# --------------------------------------------------------------------------- #
# The cap — both arms
# --------------------------------------------------------------------------- #


def test_over_cap_flags_a_truncating_description(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "fat", "x" * (SKILL_DESCRIPTION_MAX + 1))

    (flagged,) = over_cap(collect_listing(repo, tmp_path / "home", []))

    assert flagged.name == "fat"


def test_a_description_exactly_at_the_cap_is_not_flagged(tmp_path: Path) -> None:
    """The passing arm: the boundary is inclusive, so `== cap` must be silent."""
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "edge", "x" * SKILL_DESCRIPTION_MAX)

    assert over_cap(collect_listing(repo, tmp_path / "home", [])) == []


# --------------------------------------------------------------------------- #
# The doctor check — both arms
# --------------------------------------------------------------------------- #


def _setup(listing: tuple, baseline: dict) -> doctor.Setup:
    return doctor.Setup(
        repo_root=Path("/nonexistent"),
        baseline=baseline,
        servers=(),
        settings={},
        local_settings={},
        fnox=doctor.read_fnox(Path("/nonexistent/fnox.toml")),
        environ={},
        listing=listing,
    )


def test_check_is_silent_under_the_ceiling(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "alpha", "small")
    listing = collect_listing(repo, tmp_path / "home", [])

    assert (
        doctor.check_listing_budget(_setup(listing, {"listing": {"max_chars": 999}}))
        == []
    )


def test_check_reports_when_the_listing_exceeds_the_ceiling(tmp_path: Path) -> None:
    """The FAILING arm — without it this check could only ever pass."""
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "alpha", "x" * 200)
    listing = collect_listing(repo, tmp_path / "home", [])

    (finding,) = doctor.check_listing_budget(
        _setup(listing, {"listing": {"max_chars": 10}})
    )

    assert "STANDING context" in finding
    assert "> 10" in finding


def test_an_absent_ceiling_disables_only_the_total_not_the_cap(tmp_path: Path) -> None:
    """No `[listing]` section must not silently disable the truncation finding."""
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "fat", "x" * (SKILL_DESCRIPTION_MAX + 1))
    listing = collect_listing(repo, tmp_path / "home", [])

    findings = doctor.check_listing_budget(_setup(listing, {}))

    assert len(findings) == 1
    assert "TRUNCATED SILENTLY" in findings[0]


@pytest.mark.parametrize("ceiling", ["34000", 34000.5, None])
def test_a_non_int_ceiling_is_ignored_rather_than_crashing(
    tmp_path: Path, ceiling: object
) -> None:
    """A mistyped ceiling is ignored rather than crashing the doctor.

    It fails open here and loudly elsewhere — `run_checks` records a crashed
    check — but this path simply skips the total.
    """
    repo = tmp_path / "repo"
    _skill(repo / ".claude", "alpha", "x" * 200)
    listing = collect_listing(repo, tmp_path / "home", [])

    assert (
        doctor.check_listing_budget(
            _setup(listing, {"listing": {"max_chars": ceiling}})
        )
        == []
    )
