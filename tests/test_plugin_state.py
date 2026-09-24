# Copyright (c) 2026 Raymond Manaloto
"""Behavioral tests for bounded, key-only plugin state readers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dotfiles_setup.plugin_state import (
    claude_state_locations,
    codex_config_locations,
    locate,
    plugin_name,
)

if TYPE_CHECKING:
    from pathlib import Path

_NAME = "example-plugin"
_PLUGIN = "example-plugin@example-plugin"


def _home(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "plugins").mkdir(parents=True)
    (tmp_path / ".codex").mkdir()
    return tmp_path


def test_plugin_name_splits_only_the_selector_suffix() -> None:
    assert plugin_name(_PLUGIN) == _NAME
    assert plugin_name(_NAME) == _NAME


def test_fixture_home_yields_every_location_kind(tmp_path: Path) -> None:
    home = _home(tmp_path)
    claude = home / ".claude" / "plugins"
    (claude / "installed_plugins.json").write_text(
        json.dumps({"plugins": {_PLUGIN: [{"projectPath": "/repo"}]}})
    )
    (claude / "known_marketplaces.json").write_text(json.dumps({_NAME: {"source": {}}}))
    (claude / "cache" / _NAME).mkdir(parents=True)
    (home / ".codex" / "plugins" / "cache" / _NAME / _NAME).mkdir(parents=True)
    (home / ".codex" / "config.toml").write_text(
        f'[plugins."{_PLUGIN}"]\nenabled = true\n'
        f'[hooks.state."{_PLUGIN}:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "not-reported"\n'
        f'[marketplaces.{_NAME}]\nsource = "not-reported"\n'
    )

    locations = locate(
        [_NAME],
        home=home,
        settings_sources={
            "project": {
                "enabledPlugins": {_PLUGIN: True},
                "extraKnownMarketplaces": {_NAME: {"source": {}}},
            }
        },
    )

    assert {location.kind for location in locations} == {
        "enabled",
        "declared-marketplace",
        "installed",
        "known-marketplace",
        "cache",
        "codex-plugin",
        "codex-marketplace",
        "codex-hook-trust",
    }
    rendered = repr(locations)
    assert "not-reported" not in rendered


def test_unreadable_registry_is_a_location_not_absence(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text("{trunc")

    locations = claude_state_locations([_NAME], home)

    assert locations == [
        next(location for location in locations if location.kind == "unreadable")
    ]
    assert locations[0].where == "~/.claude/plugins/installed_plugins.json"
    assert locations[0].detail == "JSONDecodeError"


def test_disabled_codex_plugin_and_its_state_are_not_findings(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".codex" / "plugins" / "cache" / _NAME / _NAME).mkdir(parents=True)
    (home / ".codex" / "config.toml").write_text(
        f'[plugins."{_PLUGIN}"]\nenabled = false\n'
        f'[hooks.state."{_PLUGIN}:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "not-reported"\n'
        f'[marketplaces.{_NAME}]\nsource = "not-reported"\n'
    )

    assert codex_config_locations([_NAME], home) == []
