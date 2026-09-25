# Copyright (c) 2026 Raymond Manaloto
"""Report when a deliberately removed plugin reappears in harness state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dotfiles_setup.plugin_state import PluginLocation, locate

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path


def _message(location: PluginLocation) -> str:
    if location.kind == "installed":
        suffix = f"installs `{location.key}` ({location.detail})"
    elif location.kind == "unreadable":
        suffix = f"is unreadable ({location.detail}), so {location.key} went unchecked"
    else:
        actions = {
            "enabled": f"enables `{location.key}`",
            "declared-marketplace": f"declares marketplace `{location.key}`",
            "known-marketplace": f"registers marketplace `{location.key}`",
            "cache": "still holds a cached copy",
            "data": "still holds plugin data",
            "codex-plugin": f"enables plugin `{location.key}`",
            "codex-marketplace": f"registers marketplace `{location.key}`",
            "codex-hook-trust": f"trusts hook `{location.key}`",
        }
        suffix = actions[location.kind]
    return f"{location.where} {suffix}"


def find_reappearances(
    names: Iterable[str],
    *,
    home: Path,
    settings_sources: Mapping[str, Mapping[str, object]],
) -> list[str]:
    """Every place a removed plugin is installed, enabled, or registered."""
    locations = locate(names, home=home, settings_sources=settings_sources)
    disabled = {
        (location.key, location.marketplace)
        for location in locations
        if location.harness == "codex"
        and location.kind == "codex-plugin"
        and location.detail == "enabled=false"
    }

    def deliberately_disabled(location: PluginLocation) -> bool:
        if location.harness != "codex":
            return False
        if location.kind == "codex-plugin":
            selector = location.key
        elif location.kind == "codex-hook-trust":
            selector = location.detail
        elif location.kind == "cache":
            selector = location.key
        elif location.kind == "codex-marketplace":
            return any(
                marketplace == location.marketplace
                for _selector, marketplace in disabled
            )
        else:
            return False
        return (selector, location.marketplace) in disabled

    return [
        _message(location)
        for location in locations
        if not deliberately_disabled(location)
    ]
