# Copyright (c) 2026 Raymond Manaloto
"""Read Claude and codex plugin state without exposing stored values."""

from __future__ import annotations

import json
import os
import re
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
    "data",
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
    marketplace: str = ""
    scope: str = ""


@dataclass(frozen=True)
class _Unreadable:
    reason: str


def plugin_name(key: str) -> str:
    """Return the bare plugin name from a ``name@marketplace`` selector."""
    return key.split("@", 1)[0]


def marketplace_name(key: str) -> str:
    """Return the marketplace half of a selector, or an empty string."""
    return key.partition("@")[2]


def _selectors(names: Iterable[str]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (plugin_name(str(value)), marketplace_name(str(value))) for value in names
    )


def _matches_selector(key: str, wanted: tuple[tuple[str, str], ...]) -> bool:
    name = plugin_name(key)
    marketplace = marketplace_name(key)
    return any(
        name == wanted_name
        and (not wanted_marketplace or marketplace == wanted_marketplace)
        for wanted_name, wanted_marketplace in wanted
    )


def _wanted_marketplaces(wanted: tuple[tuple[str, str], ...]) -> frozenset[str]:
    return frozenset(marketplace or name for name, marketplace in wanted)


def _wanted_names(wanted: tuple[tuple[str, str], ...]) -> frozenset[str]:
    return frozenset(name for name, _marketplace in wanted)


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _Unreadable(type(exc).__name__)


def _unreadable(
    harness: PluginHarness,
    where: str,
    loaded: object,
    wanted: tuple[tuple[str, str], ...],
) -> list[PluginLocation]:
    if not isinstance(loaded, _Unreadable):
        return []
    labels = sorted(
        f"{name}@{marketplace}" if marketplace else name for name, marketplace in wanted
    )
    return [
        PluginLocation(
            harness=harness,
            kind="unreadable",
            where=where,
            key=", ".join(labels),
            detail=loaded.reason,
        )
    ]


def _stat_location(
    harness: PluginHarness,
    kind: PluginLocationKind,
    path: Path,
    key: str,
    *,
    marketplace: str = "",
) -> list[PluginLocation]:
    try:
        path.lstat()
    except FileNotFoundError:
        return []
    except OSError as exc:
        return [
            PluginLocation(
                harness,
                "unreadable",
                str(path),
                key,
                type(exc).__name__,
                marketplace,
            )
        ]
    return [PluginLocation(harness, kind, str(path), key, "", marketplace)]


def settings_locations(
    names: Iterable[str], sources: Mapping[str, Mapping[str, object]]
) -> list[PluginLocation]:
    """Locate enabled plugins and marketplace declarations in settings maps."""
    wanted = _selectors(names)
    wanted_marketplaces = _wanted_marketplaces(wanted)
    found: list[PluginLocation] = []
    for label, settings in sources.items():
        enabled = settings.get("enabledPlugins")
        if isinstance(enabled, dict):
            found.extend(
                PluginLocation(
                    "claude",
                    "enabled",
                    label,
                    str(key),
                    marketplace=marketplace_name(str(key)),
                )
                for key, on in enabled.items()
                if on is True and _matches_selector(str(key), wanted)
            )
        marketplaces = settings.get("extraKnownMarketplaces")
        if isinstance(marketplaces, dict):
            found.extend(
                PluginLocation(
                    "claude",
                    "declared-marketplace",
                    label,
                    str(key),
                    marketplace=str(key),
                )
                for key in marketplaces
                if str(key) in wanted_marketplaces
            )
    return found


def _install_path(raw: object, plugins_dir: Path) -> Path | None:
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else plugins_dir / path


def _data_id(selector: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", selector)


def _orphan_claude_cache_locations(
    wanted: tuple[tuple[str, str], ...], plugins_dir: Path, seen: set[Path]
) -> list[PluginLocation]:
    cache_root = plugins_dir / "cache"
    found: list[PluginLocation] = []
    for name, marketplace in wanted:
        if marketplace:
            candidates = ((marketplace, cache_root / marketplace / name),)
        else:
            try:
                with os.scandir(cache_root) as entries:
                    candidates = tuple(
                        (entry.name, Path(entry.path) / name)
                        for entry in entries
                        if entry.is_dir(follow_symlinks=False)
                    )
            except FileNotFoundError:
                continue
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
        for candidate_marketplace, candidate in candidates:
            if candidate in seen:
                continue
            selector = f"{name}@{candidate_marketplace}"
            locations = _stat_location(
                "claude",
                "cache",
                candidate,
                selector,
                marketplace=candidate_marketplace,
            )
            if locations and locations[0].kind == "cache":
                seen.add(candidate)
            found.extend(locations)
    return found


def _installed_claude_locations(
    wanted: tuple[tuple[str, str], ...], plugins_dir: Path, installed: object
) -> tuple[list[PluginLocation], set[Path], set[str]]:
    label = "~/.claude/plugins/installed_plugins.json"
    found: list[PluginLocation] = []
    seen_cache: set[Path] = set()
    seen_data: set[str] = set()
    plugins = installed.get("plugins") if isinstance(installed, dict) else None
    if not isinstance(plugins, dict):
        return found, seen_cache, seen_data
    for raw_key, entries in plugins.items():
        key = str(raw_key)
        if not _matches_selector(key, wanted):
            continue
        marketplace = marketplace_name(key)
        if not isinstance(entries, list):
            found.append(
                PluginLocation(
                    "claude",
                    "unreadable",
                    label,
                    key,
                    "invalid entries",
                    marketplace,
                )
            )
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                found.append(
                    PluginLocation(
                        "claude",
                        "unreadable",
                        label,
                        key,
                        "invalid entry",
                        marketplace,
                    )
                )
                continue
            scope = str(entry.get("scope") or "")
            project = str(entry.get("projectPath") or "")
            detail = project or ("auto" if entry.get("auto") is True else "")
            found.append(
                PluginLocation(
                    "claude",
                    "installed",
                    label,
                    key,
                    detail,
                    marketplace,
                    scope,
                )
            )
            install_path = _install_path(entry.get("installPath"), plugins_dir)
            if install_path is None:
                continue
            cache_unit = install_path.parent
            if cache_unit not in seen_cache:
                seen_cache.add(cache_unit)
                found.extend(
                    _stat_location(
                        "claude",
                        "cache",
                        cache_unit,
                        key,
                        marketplace=marketplace,
                    )
                )
        data_id = _data_id(key)
        if data_id not in seen_data:
            seen_data.add(data_id)
            data_path = plugins_dir / "data" / data_id
            found.extend(
                _stat_location(
                    "claude", "data", data_path, key, marketplace=marketplace
                )
            )
    return found, seen_cache, seen_data


def _claude_data_locations(
    wanted: tuple[tuple[str, str], ...],
    plugins_dir: Path,
    seen_data: set[str],
) -> list[PluginLocation]:
    found: list[PluginLocation] = []
    for name, marketplace in wanted:
        if marketplace:
            selector = f"{name}@{marketplace}"
            data_id = _data_id(selector)
            if data_id not in seen_data:
                found.extend(
                    _stat_location(
                        "claude",
                        "data",
                        plugins_dir / "data" / data_id,
                        selector,
                        marketplace=marketplace,
                    )
                )
            continue
        data_root = plugins_dir / "data"
        try:
            with os.scandir(data_root) as entries:
                candidates = tuple(
                    Path(entry.path)
                    for entry in entries
                    if entry.name.startswith(f"{_data_id(name)}-")
                )
        except FileNotFoundError:
            candidates = ()
        except OSError as exc:
            found.append(
                PluginLocation(
                    "claude",
                    "unreadable",
                    "~/.claude/plugins/data",
                    name,
                    type(exc).__name__,
                )
            )
            candidates = ()
        for candidate in candidates:
            found.extend(_stat_location("claude", "data", candidate, name))
    return found


def claude_state_locations(names: Iterable[str], home: Path) -> list[PluginLocation]:
    """Locate watched keys in Claude's state files, cache, and data directory."""
    wanted = _selectors(names)
    wanted_marketplaces = _wanted_marketplaces(wanted)
    plugins_dir = home / ".claude" / "plugins"
    installed_label = "~/.claude/plugins/installed_plugins.json"
    installed = _load_json(plugins_dir / "installed_plugins.json")
    found = _unreadable("claude", installed_label, installed, wanted)
    installed_found, seen_cache, seen_data = _installed_claude_locations(
        wanted, plugins_dir, installed
    )
    found.extend(installed_found)

    known_label = "~/.claude/plugins/known_marketplaces.json"
    known = _load_json(plugins_dir / "known_marketplaces.json")
    found.extend(_unreadable("claude", known_label, known, wanted))
    if isinstance(known, dict):
        found.extend(
            PluginLocation(
                "claude",
                "known-marketplace",
                known_label,
                str(key),
                marketplace=str(key),
            )
            for key in known
            if str(key) in wanted_marketplaces
        )
    found.extend(_orphan_claude_cache_locations(wanted, plugins_dir, seen_cache))
    found.extend(_claude_data_locations(wanted, plugins_dir, seen_data))
    return found


def _codex_cache_locations(
    wanted: tuple[tuple[str, str], ...], home: Path
) -> list[PluginLocation]:
    cache_root = home / ".codex" / "plugins" / "cache"
    found: list[PluginLocation] = []
    for name, marketplace in wanted:
        if marketplace:
            candidates = ((marketplace, cache_root / marketplace / name),)
        else:
            try:
                with os.scandir(cache_root) as entries:
                    candidates = tuple(
                        (entry.name, Path(entry.path) / name)
                        for entry in entries
                        if entry.is_dir(follow_symlinks=False)
                    )
            except FileNotFoundError:
                continue
            except OSError as exc:
                return [
                    PluginLocation(
                        "codex",
                        "unreadable",
                        "~/.codex/plugins/cache",
                        name,
                        type(exc).__name__,
                    )
                ]
        for candidate_marketplace, candidate in candidates:
            selector = f"{name}@{candidate_marketplace}"
            found.extend(
                _stat_location(
                    "codex",
                    "cache",
                    candidate,
                    selector,
                    marketplace=candidate_marketplace,
                )
            )
    return found


def _hook_selector(key: str, home: Path) -> str:
    selector = key.split(":", 1)[0]
    if "@" in selector:
        return selector
    cache_root = home / ".codex" / "plugins" / "cache"
    path = Path(key)
    try:
        relative = path.relative_to(cache_root)
    except ValueError:
        return ""
    if len(relative.parts) < _CACHE_KEY_PARTS:
        return ""
    return f"{relative.parts[1]}@{relative.parts[0]}"


def codex_config_locations(names: Iterable[str], home: Path) -> list[PluginLocation]:
    """Locate all matching plugin, marketplace, hook-trust, and cache keys."""
    wanted = _selectors(names)
    wanted_marketplaces = _wanted_marketplaces(wanted)
    path = home / ".codex" / "config.toml"
    label = "~/.codex/config.toml"
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError:
        return _codex_cache_locations(wanted, home)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return [
            PluginLocation(
                "codex",
                "unreadable",
                label,
                ", ".join(sorted(_wanted_names(wanted))),
                type(exc).__name__,
            )
        ]

    found: list[PluginLocation] = []
    plugins = data.get("plugins", {})
    if isinstance(plugins, dict):
        for raw_key, table in plugins.items():
            key = str(raw_key)
            if not _matches_selector(key, wanted):
                continue
            enabled = table.get("enabled") if isinstance(table, dict) else None
            found.append(
                PluginLocation(
                    "codex",
                    "codex-plugin",
                    label,
                    key,
                    f"enabled={enabled!s}".lower(),
                    marketplace_name(key),
                )
            )

    hooks = data.get("hooks", {})
    state = hooks.get("state", {}) if isinstance(hooks, dict) else {}
    if isinstance(state, dict):
        for raw_key in state:
            key = str(raw_key)
            selector = _hook_selector(key, home)
            if selector and _matches_selector(selector, wanted):
                found.append(
                    PluginLocation(
                        "codex",
                        "codex-hook-trust",
                        label,
                        key,
                        selector,
                        marketplace=marketplace_name(selector),
                    )
                )

    marketplaces = data.get("marketplaces", {})
    if isinstance(marketplaces, dict):
        found.extend(
            PluginLocation(
                "codex",
                "codex-marketplace",
                label,
                str(key),
                marketplace=str(key),
            )
            for key in marketplaces
            if str(key) in wanted_marketplaces
        )
    found.extend(_codex_cache_locations(wanted, home))
    return found


def locate(
    names: Iterable[str],
    *,
    home: Path,
    settings_sources: Mapping[str, Mapping[str, object]],
) -> list[PluginLocation]:
    """Return every named plugin location across settings and harness state."""
    selectors = tuple(str(name) for name in names)
    return (
        settings_locations(selectors, settings_sources)
        + claude_state_locations(selectors, home)
        + codex_config_locations(selectors, home)
    )
