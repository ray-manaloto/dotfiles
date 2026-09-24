# Copyright (c) 2026 Raymond Manaloto
"""Read Claude and codex plugin state without exposing stored values."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

PluginHarness = Literal["claude", "codex"]
PluginLocationKind = Literal[
    "enabled",
    "declared-marketplace",
    "installed",
    "known-marketplace",
    "cache",
    "codex-plugin",
    "codex-marketplace",
    "codex-hook-trust",
    "unreadable",
]
_CACHE_KEY_PARTS = 2


@dataclass(frozen=True)
class PluginLocation:
    """One key-bearing location in which a watched plugin appears."""

    harness: PluginHarness
    kind: PluginLocationKind
    where: str
    key: str
    detail: str = ""


@dataclass(frozen=True)
class _Unreadable:
    reason: str


def plugin_name(key: str) -> str:
    """Return the bare plugin name from a ``name@marketplace`` selector."""
    return key.split("@", 1)[0]


def _wanted(names: Iterable[str]) -> frozenset[str]:
    return frozenset(plugin_name(str(name)) for name in names)


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        return _Unreadable(type(exc).__name__)


def _unreadable(
    harness: PluginHarness, where: str, loaded: object, names: frozenset[str]
) -> list[PluginLocation]:
    if not isinstance(loaded, _Unreadable):
        return []
    return [
        PluginLocation(
            harness=harness,
            kind="unreadable",
            where=where,
            key=", ".join(sorted(names)),
            detail=loaded.reason,
        )
    ]


def settings_locations(
    names: Iterable[str], sources: Mapping[str, Mapping[str, object]]
) -> list[PluginLocation]:
    """Locate enabled plugins and marketplace declarations in settings maps."""
    wanted = _wanted(names)
    found: list[PluginLocation] = []
    for label, settings in sources.items():
        enabled = settings.get("enabledPlugins")
        if isinstance(enabled, dict):
            found.extend(
                PluginLocation("claude", "enabled", label, str(key))
                for key, on in enabled.items()
                if on is True and plugin_name(str(key)) in wanted
            )
        marketplaces = settings.get("extraKnownMarketplaces")
        if isinstance(marketplaces, dict):
            found.extend(
                PluginLocation("claude", "declared-marketplace", label, str(key))
                for key in marketplaces
                if str(key) in wanted
            )
    return found


def _claude_cache_locations(
    names: frozenset[str], plugins_dir: Path
) -> list[PluginLocation]:
    cache = plugins_dir / "cache"
    found: list[PluginLocation] = []
    for name in sorted(names):
        try:
            present = (cache / name).exists()
        except OSError as exc:
            found.append(
                PluginLocation(
                    "claude",
                    "unreadable",
                    "~/.claude/plugins/cache",
                    name,
                    type(exc).__name__,
                )
            )
            continue
        if present:
            found.append(
                PluginLocation(
                    "claude",
                    "cache",
                    f"~/.claude/plugins/cache/{name}",
                    name,
                )
            )
    return found


def claude_state_locations(names: Iterable[str], home: Path) -> list[PluginLocation]:
    """Locate watched keys in Claude's two state files and cache."""
    wanted = _wanted(names)
    plugins_dir = home / ".claude" / "plugins"
    installed_path = plugins_dir / "installed_plugins.json"
    installed_label = "~/.claude/plugins/installed_plugins.json"
    installed = _load_json(installed_path)
    found = _unreadable("claude", installed_label, installed, wanted)
    plugins = installed.get("plugins") if isinstance(installed, dict) else None
    if isinstance(plugins, dict):
        for key, entries in plugins.items():
            if plugin_name(str(key)) not in wanted:
                continue
            scopes = sorted(
                {
                    str(entry.get("projectPath") or entry.get("scope"))
                    for entry in (entries if isinstance(entries, list) else [])
                    if isinstance(entry, dict)
                }
            )
            found.append(
                PluginLocation(
                    "claude",
                    "installed",
                    installed_label,
                    str(key),
                    ", ".join(scopes) or "no scope recorded",
                )
            )

    known_label = "~/.claude/plugins/known_marketplaces.json"
    known = _load_json(plugins_dir / "known_marketplaces.json")
    found.extend(_unreadable("claude", known_label, known, wanted))
    if isinstance(known, dict):
        found.extend(
            PluginLocation("claude", "known-marketplace", known_label, str(key))
            for key in known
            if str(key) in wanted
        )
    found.extend(_claude_cache_locations(wanted, plugins_dir))
    return found


def _codex_cache_locations(names: frozenset[str], home: Path) -> list[PluginLocation]:
    cache_root = home / ".codex" / "plugins" / "cache"
    if not cache_root.exists():
        return []
    try:
        marketplaces = tuple(path for path in cache_root.iterdir() if path.is_dir())
    except OSError as exc:
        return [
            PluginLocation(
                "codex",
                "unreadable",
                "~/.codex/plugins/cache",
                ", ".join(sorted(names)),
                type(exc).__name__,
            )
        ]
    found: list[PluginLocation] = []
    for marketplace in marketplaces:
        for name in sorted(names):
            plugin_dir = marketplace / name
            try:
                present = plugin_dir.exists()
            except OSError as exc:
                found.append(
                    PluginLocation(
                        "codex",
                        "unreadable",
                        f"~/.codex/plugins/cache/{marketplace.name}/{name}",
                        f"{name}@{marketplace.name}",
                        type(exc).__name__,
                    )
                )
                continue
            if present:
                found.append(
                    PluginLocation(
                        "codex",
                        "cache",
                        f"~/.codex/plugins/cache/{marketplace.name}/{name}",
                        f"{name}@{marketplace.name}",
                    )
                )
    return found


def _hook_plugin_name(key: str, home: Path) -> str:
    selector = key.split(":", 1)[0]
    if "@" in selector:
        return plugin_name(selector)
    cache_root = home / ".codex" / "plugins" / "cache"
    path = Path(key)
    try:
        relative = path.relative_to(cache_root)
    except ValueError:
        return ""
    return relative.parts[1] if len(relative.parts) >= _CACHE_KEY_PARTS else ""


def codex_config_locations(names: Iterable[str], home: Path) -> list[PluginLocation]:
    """Locate enabled plugin, marketplace, hook-trust, and cache keys in codex."""
    wanted = _wanted(names)
    path = home / ".codex" / "config.toml"
    label = "~/.codex/config.toml"
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError:
        return _codex_cache_locations(wanted, home)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [
            PluginLocation(
                "codex",
                "unreadable",
                label,
                ", ".join(sorted(wanted)),
                type(exc).__name__,
            )
        ]

    found: list[PluginLocation] = []
    disabled: set[str] = set()
    plugins = data.get("plugins", {})
    if isinstance(plugins, dict):
        for key, table in plugins.items():
            bare = plugin_name(str(key))
            if bare not in wanted:
                continue
            enabled = table.get("enabled", True) if isinstance(table, dict) else True
            if enabled is False:
                disabled.add(bare)
            else:
                found.append(PluginLocation("codex", "codex-plugin", label, str(key)))

    hooks = data.get("hooks", {})
    state = hooks.get("state", {}) if isinstance(hooks, dict) else {}
    if isinstance(state, dict):
        found.extend(
            PluginLocation("codex", "codex-hook-trust", label, str(key))
            for key in state
            if _hook_plugin_name(str(key), home) in wanted - disabled
        )

    marketplaces = data.get("marketplaces", {})
    if isinstance(marketplaces, dict):
        found.extend(
            PluginLocation("codex", "codex-marketplace", label, str(key))
            for key in marketplaces
            if str(key) in wanted and str(key) not in disabled
        )
    found.extend(_codex_cache_locations(wanted - disabled, home))
    return found


def locate(
    names: Iterable[str],
    *,
    home: Path,
    settings_sources: Mapping[str, Mapping[str, object]],
) -> list[PluginLocation]:
    """Return every named plugin location across settings and harness state."""
    return (
        settings_locations(names, settings_sources)
        + claude_state_locations(names, home)
        + codex_config_locations(names, home)
    )
