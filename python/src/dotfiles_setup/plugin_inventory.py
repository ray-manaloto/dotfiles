# Copyright (c) 2026 Raymond Manaloto
"""Inventory a plugin across harness state, repositories, and native CLIs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.codec import Format, encode
from dotfiles_setup.plugin_state import (
    PluginLocation,
    data_id,
    locate,
    marketplace_name,
    parse_selector,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

PROBE_TIMEOUT = 10
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
    enabled_dependents: tuple[str, ...] = ()
    enabling_settings: tuple[Path, ...] = ()


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
) -> tuple[list[str], dict[str, bool], str | None]:
    """Rows for ``selector`` plus every listed id mapped to "enabled in any scope"."""
    payload, error = _run_json(["claude", "plugin", "list", "--json"], timeout)
    if error is not None:
        return [], {}, error
    if not isinstance(payload, list):
        return [], {}, "claude plugin list --json returned a non-array payload"
    rows: list[str] = []
    selectors: dict[str, bool] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id")
        if isinstance(entry_id, str) and "@" in entry_id:
            selectors[entry_id] = (
                selectors.get(entry_id, False) or entry.get("enabled") is True
            )
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
    try:
        wanted_name, wanted_marketplace = parse_selector(selector)
    except ValueError as exc:
        return [], set(), str(exc)
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


def _json_file(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text()), None
    except FileNotFoundError:
        return None, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"{path} is unreadable ({type(exc).__name__})"


def _resolved_dependencies(
    dependencies: object, declaring_marketplace: str, source: str
) -> tuple[set[tuple[str, str]], str | None]:
    """Resolve documented dependency items to ``(name, marketplace)`` pairs.

    ``$CC/plugin-dependencies.md:40-46``: an item is a bare name string or an
    object ``{name, version?, marketplace?}``; ``name`` resolves in the
    DECLARING plugin's marketplace unless ``marketplace`` names another one.
    ``version`` never affects which plugin is meant.
    """
    if dependencies is None:
        return set(), None
    if not isinstance(dependencies, list):
        return set(), f"{source} dependencies is not an array"
    resolved: set[tuple[str, str]] = set()
    for item in dependencies:
        if isinstance(item, str) and item:
            resolved.add((item, declaring_marketplace))
            continue
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name:
            return resolved, f"{source} has an unsupported dependency item"
        marketplace = item.get("marketplace")
        resolved.add(
            (
                name,
                marketplace
                if isinstance(marketplace, str) and marketplace
                else declaring_marketplace,
            )
        )
    return resolved, None


def _manifest_dependencies(
    path: Path, declaring_marketplace: str
) -> tuple[set[tuple[str, str]], str | None]:
    loaded, error = _json_file(path)
    if error is not None or loaded is None:
        return set(), error
    if not isinstance(loaded, dict):
        return set(), f"{path} is not a JSON object"
    return _resolved_dependencies(
        loaded.get("dependencies"), declaring_marketplace, str(path)
    )


def _marketplace_entries(
    home: Path, marketplace: str, cache: dict[str, tuple[dict[str, object], str | None]]
) -> tuple[dict[str, object], str | None]:
    """Map plugin name -> marketplace entry, from the marketplace's own catalog."""
    if marketplace in cache:
        return cache[marketplace]
    known, error = _json_file(home / ".claude" / "plugins" / "known_marketplaces.json")
    entries: dict[str, object] = {}
    record = known.get(marketplace) if isinstance(known, dict) else None
    location = record.get("installLocation") if isinstance(record, dict) else None
    if error is None and isinstance(location, str) and location:
        catalog_path = Path(location) / ".claude-plugin" / "marketplace.json"
        catalog, error = _json_file(catalog_path)
        plugins = catalog.get("plugins") if isinstance(catalog, dict) else None
        if isinstance(plugins, list):
            for plugin in plugins:
                name = plugin.get("name") if isinstance(plugin, dict) else None
                if isinstance(name, str):
                    entries[name] = plugin
    cache[marketplace] = (entries, error)
    return entries, error


def _plugin_dependencies(
    home: Path,
    key: str,
    entries: object,
    catalogs: dict[str, tuple[dict[str, object], str | None]],
) -> tuple[set[tuple[str, str]], list[str]]:
    """Dependencies declared in ``plugin.json`` OR the marketplace entry."""
    marketplace = marketplace_name(key)
    dependencies: set[tuple[str, str]] = set()
    errors: list[str] = []
    if isinstance(entries, list):
        for entry in entries:
            raw_install = entry.get("installPath") if isinstance(entry, dict) else None
            if not isinstance(raw_install, str) or not raw_install:
                continue
            install = Path(raw_install)
            if not install.is_absolute():
                install = home / ".claude" / "plugins" / install
            found, error = _manifest_dependencies(
                install / ".claude-plugin" / "plugin.json", marketplace
            )
            dependencies.update(found)
            if error is not None:
                errors.append(error)
    catalog, error = _marketplace_entries(home, marketplace, catalogs)
    if error is not None:
        errors.append(error)
    entry = catalog.get(key.split("@", 1)[0])
    if isinstance(entry, dict):
        found, error = _resolved_dependencies(
            entry.get("dependencies"),
            marketplace,
            f"marketplace {marketplace} entry {key}",
        )
        dependencies.update(found)
        if error is not None:
            errors.append(error)
    return dependencies, errors


def _dependency_evidence(
    home: Path, plugins: dict[object, object], selector: str, auto_plugins: set[str]
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Installed dependents of ``selector`` and its own auto-installed deps.

    A dependent is any OTHER plugin present in ``installed_plugins.json``
    (any scope, enabled or not): re-enabling a disabled dependent would break.
    """
    target = parse_selector(selector)
    catalogs: dict[str, tuple[dict[str, object], str | None]] = {}
    dependents: set[str] = set()
    own: set[tuple[str, str]] = set()
    errors: list[str] = []
    for raw_key, entries in plugins.items():
        key = str(raw_key)
        installed = isinstance(entries, list) and bool(entries)
        if not installed and key != selector:
            continue
        dependencies, found_errors = _plugin_dependencies(home, key, entries, catalogs)
        errors.extend(found_errors)
        if key == selector:
            own = dependencies
        elif target in dependencies:
            dependents.add(key)
    auto_dependencies = {f"{name}@{market}" for name, market in own} & auto_plugins
    return (
        tuple(sorted(dependents)),
        tuple(sorted(auto_dependencies)),
        tuple(dict.fromkeys(errors)),
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
        and data_id(str(key)) == data_id(selector)
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
        home, plugins, selector, auto_plugins
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
    return _parse_grep_z(repo, payload)


def _parse_grep_z(repo: Path, payload: bytes) -> list[RepoReference]:
    """Parse ``git grep -z -n`` output in ONE forward pass (linear time).

    Records are ``path NUL line NUL text LF``. A path never contains NUL and a
    matched line never contains LF, but the TEXT can contain NUL: ``-I`` only
    inspects a file's first 8000 bytes, so a binary file (measured: a ``.pgm``
    in a live repo) yields matched lines with embedded NULs. So the cursor finds
    the two NULs after the path and then the LF, instead of splitting on NUL.
    Each ``find`` starts at the cursor, so the whole payload is scanned once.
    """
    malformed = f"git grep returned malformed output for {repo}"
    found: list[RepoReference] = []
    cursor = 0
    while cursor < len(payload):
        path_end = payload.find(b"\0", cursor)
        line_end = payload.find(b"\0", path_end + 1) if path_end >= 0 else -1
        text_end = payload.find(b"\n", line_end + 1) if line_end >= 0 else -1
        if text_end < 0:
            raise RuntimeError(malformed)
        try:
            line = int(_decoded(payload[path_end + 1 : line_end]))
        except ValueError as exc:
            message = f"git grep returned an invalid line number for {repo}"
            raise RuntimeError(message) from exc
        found.append(
            RepoReference(
                repo,
                _decoded(payload[cursor:path_end]),
                line,
                _decoded(payload[line_end + 1 : text_end]),
            )
        )
        cursor = text_end + 1
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


def _matches_settings(path: Path, plugin: str) -> tuple[bool, bool, str | None]:
    """Return (enables-or-declares, enables, error) for one settings file."""
    try:
        loaded = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, False, f"{path} is unreadable ({type(exc).__name__})"
    if not isinstance(loaded, dict):
        return False, False, f"{path} is not a JSON object"
    enabled = loaded.get("enabledPlugins")
    marketplaces = loaded.get("extraKnownMarketplaces")
    enables = isinstance(enabled, dict) and enabled.get(plugin) is True
    declares = (
        isinstance(marketplaces, dict) and marketplace_name(plugin) in marketplaces
    )
    return enables or declares, enables, None


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
) -> tuple[list[Path], list[Path], list[Path]]:
    project_settings: list[Path] = []
    worktree_settings: list[Path] = []
    enabling_settings: list[Path] = []
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
                matched, enables, error = _matches_settings(path, plugin)
                if error is not None:
                    errors.append(error)
                elif matched:
                    target = worktree_settings if is_worktree else project_settings
                    target.append(path)
                    if enables and not is_worktree:
                        enabling_settings.append(path)
    return project_settings, worktree_settings, enabling_settings


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
    name, marketplace = parse_selector(plugin)
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

    project_settings, worktree_settings, enabling_settings = _collect_settings(
        plugin, topology, errors
    )
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
        enabled_dependents=tuple(
            dependent
            for dependent in metadata.dependent_plugins
            if claude_ids.get(dependent) is True
        ),
        enabling_settings=tuple(sorted(enabling_settings)),
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
