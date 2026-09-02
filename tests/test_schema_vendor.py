# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.schema_vendor` (ITEM 11)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import schema_vendor
from dotfiles_setup.schema_vendor import (
    SchemaEntry,
    _read_setup_mise_pin,
    _read_shared_toml_pin,
    _read_uv_lock_pin,
    _source_url,
    check_drift,
    current_pin,
    load_sources,
    refresh,
)

if TYPE_CHECKING:
    from pathlib import Path


def _seed_repo(
    tmp_path: Path,
    *,
    typos_version: str = "1.50.1",
    ruff_version: str = "0.16.5",
    mise_version: str = "2026.9.0",
) -> Path:
    """Build a minimal repo tree with the three pin sources + sources.toml."""
    (tmp_path / ".config/mise/conf.d").mkdir(parents=True)
    (tmp_path / ".config/mise/conf.d/shared.toml").write_text(
        f'[tools]\ntypos = "{typos_version}"\n'
    )
    (tmp_path / "python").mkdir(parents=True)
    (tmp_path / "python/uv.lock").write_text(
        "[[package]]\n"
        'name = "ruff"\n'
        f'version = "{ruff_version}"\n'
        "\n"
        "[[package]]\n"
        'name = "other-pkg"\n'
        'version = "9.9.9"\n'
    )
    (tmp_path / ".github/actions/setup-mise").mkdir(parents=True)
    (tmp_path / ".github/actions/setup-mise/action.yml").write_text(
        "runs:\n"
        "  using: composite\n"
        "  steps:\n"
        "    - uses: jdx/mise-action@deadbeef\n"
        "      with:\n"
        f'        version: "{mise_version}"\n'
    )
    (tmp_path / "schemas").mkdir(parents=True)
    (tmp_path / "schemas/sources.toml").write_text(
        "[[schema]]\n"
        'tool = "mise"\n'
        'file = "schemas/mise.json"\n'
        f'version = "{mise_version}"\n'
        'source = "https://example.invalid/mise.json"\n'
        'pin_source = ".github/actions/setup-mise/action.yml"\n'
        "\n"
        "[[schema]]\n"
        'tool = "ruff"\n'
        'file = "schemas/ruff.json"\n'
        f'version = "{ruff_version}"\n'
        'source = "https://example.invalid/ruff.json"\n'
        'pin_source = "python/uv.lock"\n'
        "\n"
        "[[schema]]\n"
        'tool = "typos"\n'
        'file = "schemas/typos.json"\n'
        f'version = "{typos_version}"\n'
        'source = "https://example.invalid/typos.json"\n'
        'pin_source = ".config/mise/conf.d/shared.toml"\n'
    )
    for tool in ("mise", "ruff", "typos"):
        (tmp_path / f"schemas/{tool}.json").write_text('{"type": "object"}')
    return tmp_path


# ──────────────────────────────────────────────────────────────────────
# Pin resolvers
# ──────────────────────────────────────────────────────────────────────


def test_read_shared_toml_pin_reads_bare_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_repo(tmp_path, typos_version="1.50.1")
    monkeypatch.setattr(schema_vendor, "_project_root", lambda: tmp_path)
    assert _read_shared_toml_pin("typos") == "1.50.1"


def test_read_shared_toml_pin_absent_tool_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(schema_vendor, "_project_root", lambda: tmp_path)
    assert _read_shared_toml_pin("no-such-tool") is None


def test_read_uv_lock_pin_finds_the_named_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_repo(tmp_path, ruff_version="0.16.5")
    monkeypatch.setattr(schema_vendor, "_project_root", lambda: tmp_path)
    assert _read_uv_lock_pin("ruff") == "0.16.5"
    assert _read_uv_lock_pin("other-pkg") == "9.9.9"
    assert _read_uv_lock_pin("not-in-lock") is None


def test_read_setup_mise_pin_matches_the_quoted_version_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_repo(tmp_path, mise_version="2026.9.0")
    monkeypatch.setattr(schema_vendor, "_project_root", lambda: tmp_path)
    assert _read_setup_mise_pin() == "2026.9.0"


def test_read_setup_mise_pin_none_when_key_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    action_dir = tmp_path / ".github/actions/setup-mise"
    action_dir.mkdir(parents=True)
    (action_dir / "action.yml").write_text("runs:\n  using: composite\n")
    monkeypatch.setattr(schema_vendor, "_project_root", lambda: tmp_path)
    assert _read_setup_mise_pin() is None


def test_current_pin_dispatches_by_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(schema_vendor, "_project_root", lambda: tmp_path)
    assert current_pin("typos") == "1.50.1"
    assert current_pin("ruff") == "0.16.5"
    assert current_pin("mise") == "2026.9.0"


def test_current_pin_unknown_tool_returns_none() -> None:
    assert current_pin("not-a-vendored-tool") is None


# ──────────────────────────────────────────────────────────────────────
# load_sources / check_drift
# ──────────────────────────────────────────────────────────────────────


def test_load_sources_parses_every_row(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    entries = load_sources(tmp_path)
    assert {e.tool for e in entries} == {"mise", "ruff", "typos"}
    assert all(isinstance(e, SchemaEntry) for e in entries)


def test_check_drift_clean_when_versions_match(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    assert check_drift(tmp_path) == []


def test_check_drift_reports_a_stale_vendored_version(tmp_path: Path) -> None:
    # sources.toml still records typos 1.49.0; the pin has moved to 1.50.1.
    _seed_repo(tmp_path, typos_version="1.50.1")
    sources = tmp_path / "schemas/sources.toml"
    stale = sources.read_text().replace('version = "1.50.1"', 'version = "1.49.0"', 1)
    sources.write_text(stale)
    findings = check_drift(tmp_path)
    assert len(findings) == 1
    assert "typos" in findings[0]
    assert "1.49.0" in findings[0]
    assert "1.50.1" in findings[0]


def test_check_drift_reports_an_unresolvable_pin(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    sources = tmp_path / "schemas/sources.toml"
    broken = sources.read_text().replace('tool = "ruff"', 'tool = "not-a-tool"', 1)
    sources.write_text(broken)
    findings = check_drift(tmp_path)
    assert len(findings) == 1
    assert "not-a-tool" in findings[0]
    assert "could not resolve" in findings[0]


# ──────────────────────────────────────────────────────────────────────
# _source_url
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("tool", "version", "expected"),
    [
        (
            "mise",
            "2026.9.0",
            "https://raw.githubusercontent.com/jdx/mise/v2026.9.0/schema/mise.json",
        ),
        (
            "ruff",
            "0.16.5",
            "https://raw.githubusercontent.com/astral-sh/ruff/0.16.5/ruff.schema.json",
        ),
        (
            "typos",
            "1.50.1",
            "https://raw.githubusercontent.com/crate-ci/typos/v1.50.1/config.schema.json",
        ),
    ],
)
def test_source_url_matches_the_real_tag_shape(
    tool: str, version: str, expected: str
) -> None:
    assert _source_url(tool, version) == expected


def test_source_url_raises_for_an_unknown_tool() -> None:
    with pytest.raises(ValueError, match="no source-URL template"):
        _source_url("not-a-tool", "1.0.0")


# ──────────────────────────────────────────────────────────────────────
# refresh (network fetch stubbed via the `fetcher` seam)
# ──────────────────────────────────────────────────────────────────────


def test_refresh_is_a_noop_when_nothing_drifted(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    calls: list[str] = []

    def fetcher(url: str) -> bytes:
        calls.append(url)
        return b'{"type": "object"}'

    changed = refresh(tmp_path, fetcher=fetcher)
    assert changed == []
    # Every entry's pin matches its recorded version, but bytes are still
    # compared, so the fetcher IS called for each tool.
    assert len(calls) == 3


def test_refresh_rewrites_the_schema_and_sources_toml_on_drift(
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path, ruff_version="0.16.5")
    sources = tmp_path / "schemas/sources.toml"
    # Record a stale ruff version; the pin (uv.lock) still says 0.16.5.
    stale = sources.read_text().replace('version = "0.16.5"', 'version = "0.16.4"', 1)
    sources.write_text(stale)

    def fetcher(url: str) -> bytes:
        if "ruff" in url:
            return b'{"type": "object", "new": true}'
        return b'{"type": "object"}'

    changed = refresh(tmp_path, fetcher=fetcher)
    assert changed == ["ruff"]
    rewritten = (tmp_path / "schemas/ruff.json").read_text()
    assert rewritten == '{"type": "object", "new": true}'
    reloaded = {e.tool: e for e in load_sources(tmp_path)}
    assert reloaded["ruff"].version == "0.16.5"
    # The two undrifted entries are untouched.
    assert reloaded["mise"].version == "2026.9.0"
    assert reloaded["typos"].version == "1.50.1"


def test_refresh_leaves_an_unresolvable_tool_vendored_and_uncounted(
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path)
    sources = tmp_path / "schemas/sources.toml"
    broken = sources.read_text().replace('tool = "ruff"', 'tool = "not-a-tool"', 1)
    sources.write_text(broken)

    def fetcher(url: str) -> bytes:
        del url
        return b'{"type": "object"}'

    changed = refresh(tmp_path, fetcher=fetcher)
    assert "not-a-tool" not in changed
