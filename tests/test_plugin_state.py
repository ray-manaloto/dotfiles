# Copyright (c) 2026 Raymond Manaloto
"""Behavioral tests for bounded, key-only plugin state readers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dotfiles_setup.plugin_state import (
    claude_state_locations,
    codex_config_locations,
    locate,
    marketplace_name,
    plugin_name,
)

if TYPE_CHECKING:
    from pathlib import Path

_NAME = "alpha"
_MARKETPLACE = "market"
_PLUGIN = f"{_NAME}@{_MARKETPLACE}"


def _home(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "plugins").mkdir(parents=True)
    (tmp_path / ".codex").mkdir()
    return tmp_path


def test_selector_helpers_keep_the_two_halves_distinct() -> None:
    assert plugin_name(_PLUGIN) == _NAME
    assert plugin_name(_NAME) == _NAME
    assert marketplace_name(_PLUGIN) == _MARKETPLACE
    assert marketplace_name(_NAME) == ""


def test_data_id_replaces_every_non_ascii_identifier_character(tmp_path: Path) -> None:
    home = _home(tmp_path)
    selector = "plügïn@mårket"
    data = home / ".claude" / "plugins" / "data" / "pl-g-n-m-rket"
    data.mkdir(parents=True)

    locations = claude_state_locations([selector], home)

    assert [(location.kind, location.where) for location in locations] == [
        ("data", str(data))
    ]


def test_fixture_home_yields_every_location_kind_and_scope(tmp_path: Path) -> None:
    home = _home(tmp_path)
    claude = home / ".claude" / "plugins"
    version = claude / "cache" / _MARKETPLACE / _NAME / "1.0.0"
    version.mkdir(parents=True)
    (claude / "data" / "alpha-market").mkdir(parents=True)
    (claude / "installed_plugins.json").write_text(
        json.dumps(
            {
                "plugins": {
                    _PLUGIN: [
                        {
                            "scope": "project",
                            "projectPath": "/repo",
                            "installPath": str(version),
                        },
                        {
                            "scope": "user",
                            "installPath": str(version),
                        },
                    ],
                    "alpha@other-market": [
                        {
                            "scope": "user",
                            "installPath": str(
                                claude / "cache" / "other-market" / _NAME / "1.0.0"
                            ),
                        }
                    ],
                }
            }
        )
    )
    (claude / "known_marketplaces.json").write_text(
        json.dumps({_MARKETPLACE: {"source": {}}})
    )
    (home / ".codex" / "plugins" / "cache" / _MARKETPLACE / _NAME).mkdir(parents=True)
    (home / ".codex" / "plugins" / "cache" / "other-market" / _NAME).mkdir(parents=True)
    (home / ".codex" / "config.toml").write_text(
        f'[plugins."{_PLUGIN}"]\nenabled = true\n'
        f'[hooks.state."{_PLUGIN}:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "not-reported"\n'
        f'[marketplaces.{_MARKETPLACE}]\nsource = "not-reported"\n'
    )

    locations = locate(
        [_PLUGIN],
        home=home,
        settings_sources={
            "project": {
                "enabledPlugins": {
                    _PLUGIN: True,
                    "alpha@other-market": True,
                },
                "extraKnownMarketplaces": {
                    _MARKETPLACE: {"source": {}},
                    "other-market": {"source": {}},
                },
            }
        },
    )

    assert {location.kind for location in locations} == {
        "enabled",
        "declared-marketplace",
        "installed",
        "known-marketplace",
        "cache",
        "data",
        "codex-plugin",
        "codex-marketplace",
        "codex-hook-trust",
    }
    assert {
        location.scope for location in locations if location.kind == "installed"
    } == {"project", "user"}
    assert all(location.marketplace == _MARKETPLACE for location in locations)
    assert "other-market" not in repr(locations)
    assert "not-reported" not in repr(locations)


def test_unreadable_registry_is_a_location_not_absence(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text("{trunc")

    locations = claude_state_locations([_PLUGIN], home)

    assert locations == [
        next(location for location in locations if location.kind == "unreadable")
    ]
    assert locations[0].where == "~/.claude/plugins/installed_plugins.json"
    assert locations[0].detail == "JSONDecodeError"


def test_permission_denied_cache_is_unreadable_not_absent(tmp_path: Path) -> None:
    home = _home(tmp_path)
    cache_root = home / ".codex" / "plugins" / "cache"
    cache_root.mkdir(parents=True)
    cache_root.chmod(0)
    try:
        locations = codex_config_locations([_PLUGIN], home)
    finally:
        cache_root.chmod(0o700)

    assert len(locations) == 1
    assert locations[0].kind == "unreadable"
    assert locations[0].where.endswith(f"/{_MARKETPLACE}/{_NAME}")


def test_disabled_codex_plugin_still_reports_all_inventory_state(
    tmp_path: Path,
) -> None:
    home = _home(tmp_path)
    (home / ".codex" / "plugins" / "cache" / _MARKETPLACE / _NAME).mkdir(parents=True)
    (home / ".codex" / "config.toml").write_text(
        f'[plugins."{_PLUGIN}"]\nenabled = false\n'
        f'[hooks.state."{_PLUGIN}:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "not-reported"\n'
        f'[marketplaces.{_MARKETPLACE}]\nsource = "not-reported"\n'
    )

    locations = codex_config_locations([_PLUGIN], home)

    assert {location.kind for location in locations} == {
        "codex-plugin",
        "codex-hook-trust",
        "codex-marketplace",
        "cache",
    }
    plugin = next(item for item in locations if item.kind == "codex-plugin")
    assert plugin.detail == "enabled=false"
