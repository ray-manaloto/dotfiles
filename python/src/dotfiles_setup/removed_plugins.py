# Copyright (c) 2026 Raymond Manaloto
"""Fail when a REMOVED plugin reappears on the Claude or codex side (#1317).

fable-orchestrator was removed from both repos and from this Mac, and the codex
side's `claudex-loop` was disabled with it (spec #1310). Nothing in either repo
would notice a reinstall: `claude plugin install`, a codex `/plugins` click, or a
restored backup of `~/.codex/config.toml` would put the plugin back while every
repo gate stayed green. This module reads the four places a plugin can come back
and names each one; the doctor check in :mod:`dotfiles_setup.doctor` wires it to
SessionStart.

It reads config and state only, and it reports KEYS, never values:
`~/.codex/config.toml` is the operator's user-global codex config and may hold
credentials.
"""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path


def _plugin_name(key: str) -> str:
    """`name@marketplace` -> `name`; a bare name stays itself."""
    return key.split("@", 1)[0]


class _Unreadable:
    """A state file that exists but could not be read or parsed.

    A missing file is ordinary (nothing installed); an unreadable one is "never
    asked", and must surface as a finding rather than read as clean
    (`probes-need-a-control-arm.md` rule 4).
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        return _Unreadable(type(exc).__name__)


def _unchecked(label: str, loaded: object, names: frozenset[str]) -> list[str]:
    if isinstance(loaded, _Unreadable):
        wanted = ", ".join(sorted(names))
        return [f"{label} is unreadable ({loaded.reason}), so {wanted} went unchecked"]
    return []


def _settings_findings(
    names: frozenset[str], settings_sources: Mapping[str, Mapping[str, object]]
) -> list[str]:
    findings: list[str] = []
    for label, settings in settings_sources.items():
        enabled = settings.get("enabledPlugins")
        if isinstance(enabled, dict):
            findings.extend(
                f"{label} enables `{key}`"
                for key, on in enabled.items()
                if on is True and _plugin_name(str(key)) in names
            )
        # A marketplace declaration re-registers the plugin's source on startup
        # even while nothing enables it, and neither forbidden token matches it.
        extra = settings.get("extraKnownMarketplaces")
        if isinstance(extra, dict):
            findings.extend(
                f"{label} declares marketplace `{key}`"
                for key in extra
                if str(key) in names
            )
    return findings


def _claude_state_findings(names: frozenset[str], home: Path) -> list[str]:
    findings: list[str] = []
    plugins_dir = home / ".claude" / "plugins"
    installed = _load_json(plugins_dir / "installed_plugins.json")
    findings.extend(
        _unchecked("~/.claude/plugins/installed_plugins.json", installed, names)
    )
    plugins = installed.get("plugins") if isinstance(installed, dict) else None
    if isinstance(plugins, dict):
        for key, entries in plugins.items():
            if _plugin_name(str(key)) not in names:
                continue
            scopes = sorted(
                {
                    str(entry.get("projectPath") or entry.get("scope"))
                    for entry in (entries if isinstance(entries, list) else [])
                    if isinstance(entry, dict)
                }
            )
            findings.append(
                f"~/.claude/plugins/installed_plugins.json installs `{key}` "
                f"({', '.join(scopes) or 'no scope recorded'})"
            )
    known = _load_json(plugins_dir / "known_marketplaces.json")
    findings.extend(
        _unchecked("~/.claude/plugins/known_marketplaces.json", known, names)
    )
    if isinstance(known, dict):
        findings.extend(
            f"~/.claude/plugins/known_marketplaces.json registers marketplace `{key}`"
            for key in known
            if str(key) in names
        )
    # A cached copy stays loadable (`claude --plugin-dir`) after an uninstall.
    findings.extend(
        f"~/.claude/plugins/cache/{name} still holds a cached copy"
        for name in sorted(names)
        if (plugins_dir / "cache" / name).exists()
    )
    return findings


def _codex_findings(names: frozenset[str], home: Path) -> list[str]:
    path = home / ".codex" / "config.toml"
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError:
        return []
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return _unchecked(
            "~/.codex/config.toml", _Unreadable(type(exc).__name__), names
        )
    findings: list[str] = []
    #: Names whose codex plugin is present but explicitly `enabled = false` — the
    #: ruled "disable" for claudex-loop. Its marketplace and any hook trust codex
    #: keeps after a disable may then stay.
    disabled: set[str] = set()
    plugins = data.get("plugins", {})
    if isinstance(plugins, dict):
        for key, table in plugins.items():
            enabled = table.get("enabled", True) if isinstance(table, dict) else True
            if _plugin_name(str(key)) not in names:
                continue
            if enabled is False:
                disabled.add(_plugin_name(str(key)))
            else:
                findings.append(f"~/.codex/config.toml enables plugin `{key}`")
    hooks = data.get("hooks", {})
    state = hooks.get("state", {}) if isinstance(hooks, dict) else {}
    if isinstance(state, dict):
        findings.extend(
            f"~/.codex/config.toml trusts hook `{key}`"
            for key in state
            if _plugin_name(str(key).split(":", 1)[0]) in names - disabled
        )
    marketplaces = data.get("marketplaces", {})
    if isinstance(marketplaces, dict):
        findings.extend(
            f"~/.codex/config.toml registers marketplace `{key}`"
            for key in marketplaces
            if str(key) in names and str(key) not in disabled
        )
    return findings


def find_reappearances(
    names: Iterable[str],
    *,
    home: Path,
    settings_sources: Mapping[str, Mapping[str, object]],
) -> list[str]:
    """Every place a removed plugin is installed, enabled, registered or trusted.

    Args:
        names: Bare plugin names (`fable-orchestrator`, `claudex-loop`).
        home: The home directory whose `~/.claude` and `~/.codex` are read.
        settings_sources: Label -> parsed Claude settings (user, project, local).

    Returns:
        One human-readable finding per reappearance; empty when all are gone.
    """
    wanted = frozenset(names)
    return (
        _settings_findings(wanted, settings_sources)
        + _claude_state_findings(wanted, home)
        + _codex_findings(wanted, home)
    )
