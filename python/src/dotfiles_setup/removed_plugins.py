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


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except OSError, json.JSONDecodeError:
        return {}


def _settings_findings(
    names: frozenset[str], settings_sources: Mapping[str, Mapping[str, object]]
) -> list[str]:
    findings: list[str] = []
    for label, settings in settings_sources.items():
        enabled = settings.get("enabledPlugins")
        if not isinstance(enabled, dict):
            continue
        findings.extend(
            f"{label} enables `{key}`"
            for key, on in enabled.items()
            if on is True and _plugin_name(str(key)) in names
        )
    return findings


def _claude_state_findings(names: frozenset[str], home: Path) -> list[str]:
    findings: list[str] = []
    plugins_dir = home / ".claude" / "plugins"
    installed = _load_json(plugins_dir / "installed_plugins.json")
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
    if isinstance(known, dict):
        findings.extend(
            f"~/.claude/plugins/known_marketplaces.json registers marketplace `{key}`"
            for key in known
            if str(key) in names
        )
    return findings


def _codex_findings(names: frozenset[str], home: Path) -> list[str]:
    path = home / ".codex" / "config.toml"
    try:
        data = tomllib.loads(path.read_text())
    except OSError:
        return []
    except tomllib.TOMLDecodeError:
        wanted = ", ".join(sorted(names))
        return [f"~/.codex/config.toml does not parse, so {wanted} went unchecked"]
    findings: list[str] = []
    #: Names whose codex plugin is present but explicitly `enabled = false` — the
    #: ruled "disable" for claudex-loop. Its marketplace may then stay registered.
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
            if _plugin_name(str(key).split(":", 1)[0]) in names
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
