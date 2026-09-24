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
    return [
        _message(location)
        for location in locate(names, home=home, settings_sources=settings_sources)
    ]
