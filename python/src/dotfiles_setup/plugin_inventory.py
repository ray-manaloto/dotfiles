# Copyright (c) 2026 Raymond Manaloto
"""Inventory a plugin across harness state, repositories, and native CLIs."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.codec import Format, encode
from dotfiles_setup.plugin_state import (
    PluginLocation,
    locate,
    marketplace_name,
    plugin_name,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

PROBE_TIMEOUT = 10
_SELECTOR_ERROR = "plugin selector must be name@marketplace"
HISTORICAL_PATHSPECS: tuple[str, ...] = (
    ":!docs/research",
    ":!docs/agents/goal-history.md",
    ":!docs/receipts",
    ":!docs/specs",
    ":!docs/direction",
    ":!docs/artifacts",
    ":!docs/rules-evidence",
)


@dataclass(frozen=True)
class RepoReference:
    """One live tracked repository reference to a plugin name."""

    repo: Path
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class PluginInventory:
    """Complete read-only inventory for one exact plugin selector."""

    plugin: str
    locations: tuple[PluginLocation, ...]
    claude_cli: tuple[str, ...]
    codex_cli: tuple[str, ...]
    project_settings: tuple[Path, ...]
    worktree_settings: tuple[Path, ...]
    stale_worktrees: tuple[Path, ...]
    references: tuple[RepoReference, ...]
    errors: tuple[str, ...]
    claude_marketplace_plugins: tuple[str, ...] = ()
    codex_marketplace_plugins: tuple[str, ...] = ()
    dependent_plugins: tuple[str, ...] = ()
    auto_dependencies: tuple[str, ...] = ()
    data_collisions: tuple[str, ...] = ()


@dataclass(frozen=True)
class _RepoTopology:
    bases: tuple[Path, ...]
    worktrees: tuple[Path, ...]
    stale: tuple[Path, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class _InstalledMetadata:
    marketplace_plugins: tuple[str, ...]
    dependent_plugins: tuple[str, ...]
    auto_dependencies: tuple[str, ...]
    data_collisions: tuple[str, ...]
    errors: tuple[str, ...]


def _diagnostic(text: str) -> str:
    collapsed = " ".join(text.strip().split())
    return collapsed[:500]


def _decoded(value: str | bytes) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else value


def _run_json(argv: list[str], timeout: int) -> tuple[object | None, str | None]:
    command = ["mise", "exec", "--", *argv]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return None, "`mise` is not on PATH"
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s: {' '.join(command)}"
    except (OSError, UnicodeDecodeError, subprocess.SubprocessError) as exc:
        return None, f"could not run `{argv[0]}`: {type(exc).__name__}"
    if result.returncode != 0:
        return None, (
            f"{' '.join(command)} exited {result.returncode}: "
            f"{_diagnostic(result.stderr)}"
        )
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"{' '.join(command)} returned invalid JSON: {exc.msg}"


def _claude_cli_inventory(
    selector: str, *, timeout: int
) -> tuple[list[str], set[str], str | None]:
    payload, error = _run_json(["claude", "plugin", "list", "--json"], timeout)
    if error is not None:
        return [], set(), error
    if not isinstance(payload, list):
        return [], set(), "claude plugin list --json returned a non-array payload"
    rows: list[str] = []
    selectors: set[str] = set()
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id")
        if isinstance(entry_id, str) and "@" in entry_id:
            selectors.add(entry_id)
        if entry_id != selector:
            continue
        rows.append(
            f"{selector} scope={entry.get('scope')!s} enabled={entry.get('enabled')!s}"
        )
    return rows, selectors, None


def claude_cli_rows(name: str, *, timeout: int) -> tuple[list[str], str | None]:
    """Return sanitized exact-id rows from ``claude plugin list --json``."""
    rows, _selectors, error = _claude_cli_inventory(name, timeout=timeout)
    return rows, error


def _codex_cli_inventory(
    selector: str, *, timeout: int
) -> tuple[list[str], set[str], str | None]:
    if "@" not in selector:
        return [], set(), f"codex plugin selector must be name@marketplace: {selector}"
    wanted_name = plugin_name(selector)
    wanted_marketplace = marketplace_name(selector)
    payload, error = _run_json(["codex", "plugin", "list", "--json"], timeout)
    if error is not None:
        return [], set(), error
    if not isinstance(payload, dict) or not isinstance(payload.get("installed"), list):
        return [], set(), "codex plugin list --json returned no installed array"
    rows: list[str] = []
    selectors: set[str] = set()
    for entry in payload["installed"]:
        if not isinstance(entry, dict):
            continue
        entry_name = entry.get("name")
        marketplace = entry.get("marketplaceName")
        plugin_id = entry.get("pluginId")
        if isinstance(entry_name, str) and isinstance(marketplace, str):
            expected = f"{entry_name}@{marketplace}"
            if plugin_id != expected:
                return (
                    [],
                    set(),
                    (
                        "codex plugin list --json pluginId mismatch for "
                        f"{entry_name}@{marketplace}"
                    ),
                )
            if entry.get("installed") is True:
                selectors.add(expected)
        if (
            entry_name == wanted_name
            and marketplace == wanted_marketplace
            and entry.get("installed") is True
        ):
            rows.append(f"{selector} enabled={entry.get('enabled')!s}")
    return rows, selectors, None


def codex_cli_rows(name: str, *, timeout: int) -> tuple[list[str], str | None]:
    """Return exact-selector installed rows from ``codex plugin list --json``."""
    rows, _selectors, error = _codex_cli_inventory(name, timeout=timeout)
    return rows, error


def _data_id(selector: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", selector)


def _manifest_dependencies(path: Path) -> tuple[set[str], str | None]:
    found: set[str] = set()
    error: str | None = None
    try:
        loaded = json.loads(path.read_text())
    except FileNotFoundError:
        loaded = None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        loaded = None
        error = f"{path} is unreadable ({type(exc).__name__})"
    if loaded is not None and error is None:
        if not isinstance(loaded, dict):
            error = f"{path} is not a JSON object"
        else:
            dependencies = loaded.get("dependencies")
            if isinstance(dependencies, dict):
                found = {str(key) for key in dependencies}
            elif isinstance(dependencies, list):
                found = {str(value) for value in dependencies if isinstance(value, str)}
            elif dependencies is not None:
                error = f"{path} dependencies has an unsupported shape"
    return found, error


def _manifest_paths(home: Path, plugins: dict[object, object]) -> dict[str, set[Path]]:
    manifests: dict[str, set[Path]] = {}
    for raw_key, entries in plugins.items():
        key = str(raw_key)
        paths: set[Path] = set()
        if isinstance(entries, list):
            for entry in entries:
                raw_install = (
                    entry.get("installPath") if isinstance(entry, dict) else None
                )
                if not isinstance(raw_install, str) or not raw_install:
                    continue
                install = Path(raw_install)
                if not install.is_absolute():
                    install = home / ".claude" / "plugins" / install
                paths.add(install / ".claude-plugin" / "plugin.json")
        manifests[key] = paths
    return manifests


def _dependency_evidence(
    manifests: dict[str, set[Path]], selector: str, auto_plugins: set[str]
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    dependencies_by_plugin: dict[str, set[str]] = {}
    errors: list[str] = []
    for key, paths in manifests.items():
        dependencies: set[str] = set()
        for path in paths:
            found, error = _manifest_dependencies(path)
            dependencies.update(found)
            if error is not None:
                errors.append(error)
        dependencies_by_plugin[key] = dependencies
    dependents = {
        key
        for key, dependencies in dependencies_by_plugin.items()
        if key != selector and selector in dependencies
    }
    auto_dependencies = dependencies_by_plugin.get(selector, set()) & auto_plugins
    return (
        tuple(sorted(dependents)),
        tuple(sorted(auto_dependencies)),
        tuple(errors),
    )


def _installed_metadata(home: Path, selector: str) -> _InstalledMetadata:
    registry = home / ".claude" / "plugins" / "installed_plugins.json"
    try:
        loaded = json.loads(registry.read_text())
    except FileNotFoundError:
        return _InstalledMetadata((), (), (), (), ())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _InstalledMetadata(
            (),
            (),
            (),
            (),
            (
                (
                    "~/.claude/plugins/installed_plugins.json is unreadable "
                    f"({type(exc).__name__})"
                ),
            ),
        )
    plugins = loaded.get("plugins") if isinstance(loaded, dict) else None
    if not isinstance(plugins, dict):
        return _InstalledMetadata(
            (),
            (),
            (),
            (),
            ("~/.claude/plugins/installed_plugins.json has no plugins object",),
        )

    marketplace = marketplace_name(selector)
    marketplace_plugins = {
        str(key)
        for key, entries in plugins.items()
        if marketplace_name(str(key)) == marketplace
        and isinstance(entries, list)
        and bool(entries)
    }
    colliding = {
        str(key)
        for key, entries in plugins.items()
        if str(key) != selector
        and _data_id(str(key)) == _data_id(selector)
        and isinstance(entries, list)
        and bool(entries)
    }
    auto_plugins = {
        str(key)
        for key, entries in plugins.items()
        if isinstance(entries, list)
        and any(
            isinstance(entry, dict) and entry.get("auto") is True for entry in entries
        )
    }
    dependents, auto_dependencies, errors = _dependency_evidence(
        _manifest_paths(home, plugins), selector, auto_plugins
    )
    return _InstalledMetadata(
        tuple(sorted(marketplace_plugins)),
        dependents,
        auto_dependencies,
        tuple(sorted(colliding)),
        errors,
    )


def marketplace_memberships(
    selector: str, *, home: Path, timeout: int = PROBE_TIMEOUT
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Re-read marketplace memberships from all three harness sources."""
    metadata = _installed_metadata(home, selector)
    _claude_rows, claude_ids, claude_error = _claude_cli_inventory(
        selector, timeout=timeout
    )
    _codex_rows, codex_ids, codex_error = _codex_cli_inventory(
        selector, timeout=timeout
    )
    marketplace = marketplace_name(selector)
    claude = set(metadata.marketplace_plugins)
    claude.update(item for item in claude_ids if marketplace_name(item) == marketplace)
    codex = {item for item in codex_ids if marketplace_name(item) == marketplace}
    errors = list(metadata.errors)
    errors.extend(error for error in (claude_error, codex_error) if error is not None)
    return tuple(sorted(claude)), tuple(sorted(codex)), tuple(errors)


def _base_repos(root: Path) -> list[Path]:
    repos: list[Path] = []
    try:
        with os.scandir(root) as root_entries:
            owners = tuple(
                Path(entry.path)
                for entry in root_entries
                if entry.is_dir(follow_symlinks=False)
            )
        for owner in owners:
            with os.scandir(owner) as owner_entries:
                for entry in owner_entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    repo = Path(entry.path)
                    try:
                        (repo / ".git").lstat()
                    except FileNotFoundError:
                        continue
                    repos.append(repo)
    except FileNotFoundError:
        return []
    except OSError as exc:
        message = f"cannot enumerate repositories under {root}: {exc}"
        raise RuntimeError(message) from exc
    return sorted(repos)


def _worktree_rows(repo: Path) -> tuple[list[Path], list[Path], str | None]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [], [], f"git worktree list timed out for {repo}"
    except (OSError, subprocess.SubprocessError) as exc:
        return [], [], f"git worktree list failed for {repo}: {type(exc).__name__}"
    if result.returncode != 0:
        return (
            [],
            [],
            (
                f"git worktree list failed for {repo} (rc={result.returncode}): "
                f"{_diagnostic(result.stderr)}"
            ),
        )

    present: list[Path] = []
    stale: list[Path] = []
    for record in result.stdout.split("\n\n"):
        lines = record.splitlines()
        worktree_line = next(
            (line for line in lines if line.startswith("worktree ")), None
        )
        if worktree_line is None:
            continue
        path = Path(worktree_line.removeprefix("worktree "))
        try:
            path.stat()
        except FileNotFoundError:
            if any(line.startswith("prunable") for line in lines):
                stale.append(path)
        except OSError as exc:
            return [], [], f"worktree path unreadable for {repo}: {type(exc).__name__}"
        else:
            present.append(path)
    return present, stale, None


def _topology(root: Path) -> _RepoTopology:
    bases = _base_repos(root)
    base_keys = {path.resolve() for path in bases}
    worktrees: dict[Path, Path] = {}
    stale: dict[Path, Path] = {}
    errors: list[str] = []
    for repo in bases:
        present_rows, stale_rows, error = _worktree_rows(repo)
        if error is not None:
            errors.append(error)
            continue
        for path in present_rows:
            key = path.resolve()
            if key not in base_keys:
                worktrees.setdefault(key, path)
        for path in stale_rows:
            stale.setdefault(path.resolve(strict=False), path)
    return _RepoTopology(
        bases=tuple(bases),
        worktrees=tuple(sorted(worktrees.values())),
        stale=tuple(sorted(stale.values())),
        errors=tuple(errors),
    )


def discover_repos(root: Path) -> list[Path]:
    """Discover depth-two Git repositories plus their existing worktrees."""
    topology = _topology(root)
    if topology.errors:
        raise RuntimeError("; ".join(topology.errors))
    return [*topology.bases, *topology.worktrees]


def live_references(repo: Path, name: str) -> list[RepoReference]:
    """Return non-historical tracked references found by bounded ``git grep``."""
    argv = [
        "git",
        "-C",
        str(repo),
        "grep",
        "-I",
        "-z",
        "-n",
        "-F",
        "--",
        name,
        "--",
        ".",
        *HISTORICAL_PATHSPECS,
    ]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            timeout=PROBE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        message = f"git grep timed out for {repo}"
        raise RuntimeError(message) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        message = f"git grep failed for {repo}: {type(exc).__name__}"
        raise RuntimeError(message) from exc
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        message = (
            f"git grep failed for {repo} (rc={result.returncode}): "
            f"{_diagnostic(_decoded(result.stderr))}"
        )
        raise RuntimeError(message)
    payload = result.stdout
    if not isinstance(payload, bytes):
        payload = payload.encode()
    found: list[RepoReference] = []
    while payload:
        raw_path, path_separator, payload = payload.partition(b"\0")
        raw_line, line_separator, payload = payload.partition(b"\0")
        raw_text, record_separator, payload = payload.partition(b"\n")
        if not path_separator or not line_separator or not record_separator:
            message = f"git grep returned malformed output for {repo}"
            raise RuntimeError(message)
        path = _decoded(raw_path)
        line_text = _decoded(raw_line)
        try:
            line = int(line_text)
        except ValueError as exc:
            message = f"git grep returned an invalid line number for {repo}"
            raise RuntimeError(message) from exc
        found.append(RepoReference(repo, path, line, _decoded(raw_text)))
    return found


def _load_user_settings(home: Path) -> tuple[dict[str, object], str | None]:
    path = home / ".claude" / "settings.json"
    try:
        loaded = json.loads(path.read_text())
    except FileNotFoundError:
        return {}, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, f"~/.claude/settings.json is unreadable ({type(exc).__name__})"
    if not isinstance(loaded, dict):
        return {}, "~/.claude/settings.json is not a JSON object"
    return loaded, None


def _matches_settings(path: Path, plugin: str) -> tuple[bool, str | None]:
    try:
        loaded = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"{path} is unreadable ({type(exc).__name__})"
    if not isinstance(loaded, dict):
        return False, f"{path} is not a JSON object"
    enabled = loaded.get("enabledPlugins")
    marketplaces = loaded.get("extraKnownMarketplaces")
    return (
        (isinstance(enabled, dict) and enabled.get(plugin) is True)
        or (
            isinstance(marketplaces, dict) and marketplace_name(plugin) in marketplaces
        ),
        None,
    )


def _settings_paths(repo: Path) -> tuple[Path, ...]:
    settings_dir = repo / ".claude"
    try:
        with os.scandir(settings_dir) as entries:
            return tuple(
                sorted(
                    Path(entry.path)
                    for entry in entries
                    if entry.is_file(follow_symlinks=False)
                    and entry.name.startswith("settings")
                    and entry.name.endswith(".json")
                )
            )
    except FileNotFoundError:
        return ()
    except OSError as exc:
        message = f"cannot enumerate settings under {repo}: {exc}"
        raise RuntimeError(message) from exc


def _collect_settings(
    plugin: str, topology: _RepoTopology, errors: list[str]
) -> tuple[list[Path], list[Path]]:
    project_settings: list[Path] = []
    worktree_settings: list[Path] = []
    for is_worktree, repos in (
        (False, topology.bases),
        (True, topology.worktrees),
    ):
        for repo in repos:
            try:
                paths = _settings_paths(repo)
            except RuntimeError as exc:
                errors.append(str(exc))
                continue
            for path in paths:
                enabled, error = _matches_settings(path, plugin)
                if error is not None:
                    errors.append(error)
                elif enabled:
                    target = worktree_settings if is_worktree else project_settings
                    target.append(path)
    return project_settings, worktree_settings


def _collect_references(
    name: str, topology: _RepoTopology, errors: list[str]
) -> list[RepoReference]:
    references: list[RepoReference] = []
    for repo in topology.bases:
        try:
            references.extend(live_references(repo, name))
        except RuntimeError as exc:
            errors.append(str(exc))
    return references


def inventory(plugin: str, *, home: Path, root: Path) -> PluginInventory:
    """Inventory an exact plugin selector without mutating any discovered state."""
    if "@" not in plugin:
        message = _SELECTOR_ERROR
        raise ValueError(message)
    name = plugin_name(plugin)
    marketplace = marketplace_name(plugin)
    errors: list[str] = []
    user_settings, user_error = _load_user_settings(home)
    if user_error is not None:
        errors.append(user_error)
    locations = locate(
        [plugin],
        home=home,
        settings_sources={"~/.claude/settings.json": user_settings},
    )
    errors.extend(
        f"{location.where} is unreadable ({location.detail})"
        for location in locations
        if location.kind == "unreadable"
    )

    claude_rows, claude_ids, claude_error = _claude_cli_inventory(
        plugin, timeout=PROBE_TIMEOUT
    )
    codex_rows, codex_ids, codex_error = _codex_cli_inventory(
        plugin, timeout=PROBE_TIMEOUT
    )
    errors.extend(error for error in (claude_error, codex_error) if error is not None)

    metadata = _installed_metadata(home, plugin)
    errors.extend(metadata.errors)
    claude_marketplace_plugins = set(metadata.marketplace_plugins)
    claude_marketplace_plugins.update(
        item for item in claude_ids if marketplace_name(item) == marketplace
    )
    codex_marketplace_plugins = {
        item for item in codex_ids if marketplace_name(item) == marketplace
    }

    try:
        topology = _topology(root)
    except RuntimeError as exc:
        topology = _RepoTopology((), (), (), (str(exc),))
    errors.extend(topology.errors)

    project_settings, worktree_settings = _collect_settings(plugin, topology, errors)
    references = _collect_references(name, topology, errors)

    return PluginInventory(
        plugin=plugin,
        locations=tuple(locations),
        claude_cli=tuple(claude_rows),
        codex_cli=tuple(codex_rows),
        project_settings=tuple(sorted(project_settings)),
        worktree_settings=tuple(sorted(worktree_settings)),
        stale_worktrees=topology.stale,
        references=tuple(references),
        errors=tuple(dict.fromkeys(errors)),
        claude_marketplace_plugins=tuple(sorted(claude_marketplace_plugins)),
        codex_marketplace_plugins=tuple(sorted(codex_marketplace_plugins)),
        dependent_plugins=metadata.dependent_plugins,
        auto_dependencies=metadata.auto_dependencies,
        data_collisions=metadata.data_collisions,
    )


def _print_inventory(result: PluginInventory) -> None:
    location_counts: dict[str, int] = {}
    for location in result.locations:
        kind = location.kind.replace("-", "_")
        label = (
            kind
            if kind.startswith(f"{location.harness}_")
            else f"{location.harness}_{kind}"
        )
        location_counts[label] = location_counts.get(label, 0) + 1
    sys.stdout.write(
        "\n".join(
            (
                f"plugin: {result.plugin}",
                f"locations: {len(result.locations)}",
                *(
                    f"{label}: {count}"
                    for label, count in sorted(location_counts.items())
                ),
                f"claude_cli: {len(result.claude_cli)}",
                f"codex_cli: {len(result.codex_cli)}",
                f"project_settings: {len(result.project_settings)}",
                f"worktree_settings: {len(result.worktree_settings)}",
                f"stale_worktrees: {len(result.stale_worktrees)}",
                f"references: {len(result.references)}",
                (
                    "claude_marketplace_plugins: "
                    f"{len(result.claude_marketplace_plugins)}"
                ),
                f"codex_marketplace_plugins: {len(result.codex_marketplace_plugins)}",
                f"dependent_plugins: {len(result.dependent_plugins)}",
                f"auto_dependencies: {len(result.auto_dependencies)}",
                f"data_collisions: {len(result.data_collisions)}",
                f"errors: {len(result.errors)}",
            )
        )
        + "\n"
    )
    for error in result.errors:
        sys.stdout.write(f"error: {error}\n")


def plugin_inventory_main(argv: Sequence[str]) -> int:
    """CLI entry point for ``plugin-inventory <name@marketplace> [--json]``."""
    parser = argparse.ArgumentParser(prog="plugin-inventory")
    parser.add_argument("plugin")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = inventory(
            args.plugin,
            home=Path.home(),
            root=Path.home() / "dev" / "github",
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        sys.stdout.buffer.write(encode(result, fmt=Format.JSON) + b"\n")
    else:
        _print_inventory(result)
    return 2 if result.errors else 0
