# Copyright (c) 2026 Raymond Manaloto
"""Plan and apply bounded native-first plugin removal steps.

Two file classes are treated differently (spec r3, N2):

* HARNESS-OWNED files under ``~/.claude/plugins/`` and ``~/.codex/``
  (``installed_plugins.json``, ``known_marketplaces.json``, codex config): the
  native CLI is authoritative. They are backed up before a native call but are
  never minimal-diffed or restored afterwards; the goal state is verified by
  re-reading them.
* REPO/USER settings files (``<project>/.claude/settings*.json`` and
  ``~/.claude/settings.json``): snapshotted in memory, and after the CLI runs
  the ORIGINAL text minus the key's whole member span is written back, checked
  for JSON equivalence with the CLI's result, and restored from memory on
  failure.

Every backup lands under ``<repo_root>/.agent/state/plugin-remove/<UTC stamp>/``
mirroring the source path (N3), never beside the edited file.
"""

from __future__ import annotations

import argparse
import copy
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.codec import Format, encode
from dotfiles_setup.plugin_inventory import (
    PluginInventory,
    inventory,
    marketplace_memberships,
)
from dotfiles_setup.plugin_state import (
    data_id,
    marketplace_name,
    parse_selector,
    plugin_name,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

APPLY_TIMEOUT = 15
_NEW_FILE_MODE = 0o600
_JSON_WHITESPACE = " \t\r\n"
_HOOK_PREFIX = ("hooks", "state")
_PLUGIN_PREFIX = ("plugins",)
_SETTINGS_KEY_STEP = "remove-settings-key"


@dataclass(frozen=True)
class RemovalStep:
    """One named mutation with a display command/action and exact target."""

    name: str
    argv_or_action: str
    target: str
    context: tuple[str, ...] = ()


@dataclass(frozen=True)
class RemovalPlan:
    """Ordered removal steps plus conditions that make apply unsafe."""

    plugin: str
    steps: tuple[RemovalStep, ...]
    blockers: tuple[str, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class StepResult:
    """The observed return code and diagnostic for one removal step."""

    step: RemovalStep
    rc: int
    detail: str


@dataclass(frozen=True)
class _BackupRecord:
    archive: Path
    sources: tuple[tuple[str, Path], ...]


_BACKUPS: dict[tuple[Path, str], _BackupRecord] = {}


def _step(
    name: str,
    argv_or_action: str,
    target: str,
    context: Iterable[str] = (),
) -> RemovalStep:
    return RemovalStep(name, argv_or_action, target, tuple(context))


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def _backup_root(repo_root: Path) -> Path:
    """One timestamped, gitignored directory for a run's backups (N3)."""
    return repo_root / ".agent" / "state" / "plugin-remove" / _utc_stamp()


def _archive_path(repo_root: Path, selector: str) -> Path:
    return _backup_root(repo_root) / f"plugin-removal-{data_id(selector)}.tar.gz"


# --------------------------------------------------------------------------
# Containment (N1): every deleted path stays inside the plugin's own roots.
# --------------------------------------------------------------------------


def _allowed_roots(selector: str, home: Path) -> tuple[Path, ...]:
    """The three roots a removal may touch, anchored at the resolved harness bases.

    Only the harness-owned base (``~/.claude/plugins/cache`` etc.) is resolved;
    the ``<marketplace>/<plugin>`` components are appended literally, so a
    symlinked marketplace directory cannot move the root along with it.
    """
    name, marketplace = parse_selector(selector)
    claude = home / ".claude" / "plugins"
    return (
        Path(os.path.realpath(claude / "cache")) / marketplace / name,
        Path(os.path.realpath(home / ".codex" / "plugins" / "cache"))
        / marketplace
        / name,
        Path(os.path.realpath(claude / "data")) / data_id(selector),
    )


def _deletion_location(path: Path) -> Path | None:
    """Where deleting ``path`` acts: its resolved parent plus its own name.

    The final component is NOT followed: a symlinked top-level source is
    unlinked, never traversed, so the link's own location is what matters.
    """
    absolute = path.absolute()
    if absolute.name in {"", ".", ".."}:
        return None
    return Path(os.path.realpath(absolute.parent)) / absolute.name


def _contained(path: Path, selector: str, home: Path) -> bool:
    location = _deletion_location(path)
    if location is None:
        return False
    return any(
        location == root or location.is_relative_to(root)
        for root in _allowed_roots(selector, home)
    )


# --------------------------------------------------------------------------
# File primitives: atomic write (N7), mirrored backups (N3), snapshots.
# --------------------------------------------------------------------------


def _atomic_write(path: Path, content: bytes) -> None:
    """Write via temp + fsync + replace, keeping the mode bits and any symlink."""
    target = Path(os.path.realpath(path)) if path.is_symlink() else path
    try:
        mode: int | None = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        mode = None
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    temp = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temp.chmod(_NEW_FILE_MODE if mode is None else mode)
        temp.replace(target)
    except BaseException:
        with suppress(FileNotFoundError):
            temp.unlink()
        raise


def _mirrored(backup_root: Path, path: Path) -> Path:
    absolute = path.absolute()
    return backup_root.joinpath(*absolute.parts[1:])


def _backup_bytes(path: Path, content: bytes, backup_root: Path) -> Path:
    """Exclusively create a mirrored backup; never overwrite an earlier one."""
    destination = _mirrored(backup_root, path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    candidate = destination
    for index in range(1, 1000):
        try:
            descriptor = os.open(
                candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _NEW_FILE_MODE
            )
        except FileExistsError:
            candidate = destination.with_name(f"{destination.name}.{index}")
            continue
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return candidate
    message = f"no free backup name for {path}"
    raise FileExistsError(message)


def _snapshots(
    paths: Iterable[Path], backup_root: Path
) -> tuple[dict[Path, bytes | None], str | None]:
    snapshots: dict[Path, bytes | None] = {}
    try:
        for path in dict.fromkeys(paths):
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                snapshots[path] = None
                continue
            snapshots[path] = content
            _backup_bytes(path, content, backup_root)
    except OSError as exc:
        return snapshots, f"backup failed before edit: {type(exc).__name__}"
    return snapshots, None


def _restore_snapshots(snapshots: dict[Path, bytes | None]) -> str | None:
    """Restore REPO/USER settings from memory; never used on harness-owned files."""
    try:
        for path, content in snapshots.items():
            if content is None:
                with suppress(FileNotFoundError):
                    path.unlink()
            else:
                _atomic_write(path, content)
    except OSError as exc:
        return type(exc).__name__
    return None


# --------------------------------------------------------------------------
# Planning.
# --------------------------------------------------------------------------


def _watchlist(repo_root: Path) -> tuple[frozenset[str], str | None]:
    path = repo_root / "doctor.toml"
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return frozenset(), f"doctor.toml is unreadable ({type(exc).__name__})"
    section = data.get("removed_plugins", {})
    names = section.get("names", []) if isinstance(section, dict) else []
    if not isinstance(names, list):
        return frozenset(), "doctor.toml [removed_plugins].names is not a list"
    return frozenset(str(item) for item in names), None


def _directory(path: Path) -> tuple[bool, str | None]:
    try:
        mode = path.stat().st_mode
    except FileNotFoundError:
        return False, "missing"
    except OSError as exc:
        return False, type(exc).__name__
    return stat.S_ISDIR(mode), None


def _installed_steps(inv: PluginInventory) -> tuple[list[RemovalStep], list[str]]:
    steps: list[RemovalStep] = []
    blockers: list[str] = []
    seen: set[tuple[str, str]] = set()
    for location in inv.locations:
        if (
            location.harness != "claude"
            or location.kind != "installed"
            or location.key != inv.plugin
        ):
            continue
        scope = location.scope
        project = location.detail if scope in {"project", "local"} else ""
        identity = (scope, project)
        if identity in seen:
            continue
        seen.add(identity)
        if scope == "user":
            steps.append(
                _step(
                    "uninstall-user-scope",
                    (
                        f"claude plugin uninstall {inv.plugin} --scope user "
                        "--keep-data --json"
                    ),
                    "user",
                )
            )
            continue
        if scope not in {"project", "local"}:
            blockers.append(
                f"installed entry for {inv.plugin} has unsupported scope {scope!r}"
            )
            continue
        if not project:
            blockers.append(
                f"installed {scope} entry for {inv.plugin} has no projectPath"
            )
            continue
        is_directory, error = _directory(Path(project))
        if not is_directory:
            blockers.append(
                f"installed {scope} entry projectPath is unusable: {project} ({error})"
            )
            continue
        steps.append(
            _step(
                f"uninstall-{scope}-scope",
                (
                    f"claude plugin uninstall {inv.plugin} --scope {scope} "
                    "--keep-data --json"
                ),
                project,
            )
        )
    return steps, blockers


def _settings_key_steps(inv: PluginInventory, home: Path) -> list[RemovalStep]:
    """Row 8: an enabled key with no install record still gets a removal step."""
    installs = [
        location
        for location in inv.locations
        if location.kind == "installed" and location.key == inv.plugin
    ]
    user_installed = any(location.scope == "user" for location in installs)
    installed_projects = {
        location.detail for location in installs if location.scope != "user"
    }
    targets: list[Path] = []
    user_settings = home / ".claude" / "settings.json"
    if not user_installed and any(
        location.kind == "enabled"
        and location.where == "~/.claude/settings.json"
        and location.key == inv.plugin
        for location in inv.locations
    ):
        targets.append(user_settings)
    targets.extend(
        path
        for path in inv.enabling_settings
        if str(path.parent.parent) not in installed_projects
    )
    return [
        _step(_SETTINGS_KEY_STEP, "settings goal-state edit", str(path))
        for path in dict.fromkeys(targets)
    ]


def _has_location(inv: PluginInventory, kind: str, *, key: str | None = None) -> bool:
    return any(
        location.kind == kind and (key is None or location.key == key)
        for location in inv.locations
    )


def _marketplace_projects(inv: PluginInventory) -> tuple[str, ...]:
    projects = {str(path.parent.parent) for path in inv.project_settings}
    projects.update(
        location.detail
        for location in inv.locations
        if location.kind == "installed"
        and location.scope in {"project", "local"}
        and location.detail
    )
    return tuple(sorted(projects))


def _marketplace_plan(inv: PluginInventory) -> tuple[list[RemovalStep], list[str]]:
    plugin = inv.plugin
    marketplace = marketplace_name(plugin)
    steps: list[RemovalStep] = []
    notes: list[str] = []
    claude_siblings = sorted(
        value for value in inv.claude_marketplace_plugins if value != plugin
    )
    codex_siblings = sorted(
        value for value in inv.codex_marketplace_plugins if value != plugin
    )
    claude_marketplace = any(
        location.harness == "claude"
        and location.kind in {"declared-marketplace", "known-marketplace"}
        and location.marketplace == marketplace
        for location in inv.locations
    )
    if claude_siblings:
        notes.append("marketplace kept: still used by " + ", ".join(claude_siblings))
    elif claude_marketplace:
        steps.append(
            _step(
                "remove-claude-marketplace",
                f"claude plugin marketplace remove {marketplace} --scope <each>",
                marketplace,
                _marketplace_projects(inv),
            )
        )
    if inv.codex_cli:
        steps.append(
            _step("remove-codex-plugin", f"codex plugin remove {plugin}", plugin)
        )
    elif _has_location(inv, "codex-plugin", key=plugin):
        steps.append(
            _step(
                "remove-codex-config-plugin",
                "config.toml text edit + TOML reparse",
                plugin,
            )
        )
    if codex_siblings:
        notes.append(
            "codex marketplace kept: still used by " + ", ".join(codex_siblings)
        )
    elif _has_location(inv, "codex-marketplace", key=marketplace):
        steps.append(
            _step(
                "remove-codex-marketplace",
                f"codex plugin marketplace remove {marketplace}",
                marketplace,
            )
        )
    return steps, notes


def _dependency_blockers(inv: PluginInventory) -> list[str]:
    enabled = set(inv.enabled_dependents)
    return [
        (
            f"installed plugin depends on target: {dependent} ("
            + (
                "enabled in at least one scope"
                if dependent in enabled
                else "installed but enabled nowhere; re-enabling it would break"
            )
            + ")"
        )
        for dependent in inv.dependent_plugins
    ]


def plan(
    inv: PluginInventory, *, repo_root: Path, home: Path | None = None
) -> RemovalPlan:
    """Build the ordered native-first removal plan for an inventory."""
    plugin = inv.plugin
    name, _marketplace = parse_selector(plugin)
    actual_home = home or Path.home()
    blockers = list(inv.errors)
    blockers.extend(_dependency_blockers(inv))
    blockers.extend(
        f"Claude data directory id collides with installed plugin: {collision}"
        for collision in inv.data_collisions
    )
    notes = [
        f"auto-installed dependency kept: {dependency}"
        for dependency in inv.auto_dependencies
    ]
    steps: list[RemovalStep] = []
    removal_targets = tuple(
        dict.fromkeys(
            location.where
            for location in inv.locations
            if location.kind in {"cache", "data"}
        )
    )
    blockers.extend(
        f"removal target escapes the plugin's cache/data roots: {target}"
        for target in removal_targets
        if not _contained(Path(target), plugin, actual_home)
    )
    has_backup_material = bool(removal_targets)
    if has_backup_material:
        archive = _archive_path(repo_root, plugin)
        steps.append(_step("backup-cache", "tarfile + manifest", str(archive)))

    uninstall_steps, scope_blockers = _installed_steps(inv)
    steps.extend(uninstall_steps)
    blockers.extend(scope_blockers)
    steps.extend(_settings_key_steps(inv, actual_home))

    marketplace_steps, marketplace_notes = _marketplace_plan(inv)
    steps.extend(marketplace_steps)
    notes.extend(marketplace_notes)
    if _has_location(inv, "codex-hook-trust"):
        steps.append(
            _step("remove-codex-hook-trust", "text edit + TOML reparse", plugin)
        )
    if has_backup_material:
        steps.append(
            _step(
                "remove-orphan-cache",
                "remove exact backed-up paths",
                ", ".join(removal_targets),
            )
        )

    watched, watch_error = _watchlist(repo_root)
    if watch_error is not None:
        blockers.append(watch_error)
    elif name not in watched:
        steps.append(_step("add-to-watchlist", "doctor.toml text edit", name))
    return RemovalPlan(plugin, tuple(steps), tuple(blockers), tuple(notes))


# --------------------------------------------------------------------------
# Cache and data backup / removal.
# --------------------------------------------------------------------------


def _absolute_install_path(raw: str, home: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else home / ".claude" / "plugins" / path


def _existing_source(
    kind: str, path: Path, sources: dict[Path, tuple[str, Path]]
) -> None:
    try:
        path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        message = f"cannot inspect removal source {path}: {type(exc).__name__}"
        raise OSError(message) from exc
    sources.setdefault(path, (kind, path))


def _removal_sources(selector: str, home: Path) -> tuple[tuple[str, Path], ...]:
    name, marketplace = parse_selector(selector)
    claude_plugins = home / ".claude" / "plugins"
    claude_cache = claude_plugins / "cache"
    sources: dict[Path, tuple[str, Path]] = {}
    registry = claude_plugins / "installed_plugins.json"
    try:
        loaded = json.loads(registry.read_text())
    except FileNotFoundError:
        loaded = {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        message = f"installed registry unreadable: {type(exc).__name__}"
        raise OSError(message) from exc
    plugins = loaded.get("plugins") if isinstance(loaded, dict) else None
    entries = plugins.get(selector, []) if isinstance(plugins, dict) else []
    if isinstance(entries, list):
        for entry in entries:
            raw_install = entry.get("installPath") if isinstance(entry, dict) else None
            if not isinstance(raw_install, str) or not raw_install:
                continue
            cache_unit = _absolute_install_path(raw_install, home).parent
            _existing_source("claude-cache", cache_unit, sources)

    _existing_source("claude-cache", claude_cache / marketplace / name, sources)
    _existing_source(
        "codex-cache",
        home / ".codex" / "plugins" / "cache" / marketplace / name,
        sources,
    )
    _existing_source(
        "claude-data", claude_plugins / "data" / data_id(selector), sources
    )
    escaped = [
        str(path)
        for _kind, path in sources.values()
        if not _contained(path, selector, home)
    ]
    if escaped:
        message = "removal source escapes the plugin's roots: " + ", ".join(escaped)
        raise ValueError(message)
    return tuple(sources.values())


def _manifest_bytes(selector: str, sources: tuple[tuple[str, Path], ...]) -> bytes:
    rows: list[dict[str, object]] = []
    for kind, source in sources:
        link_target: str | None = None
        if source.is_symlink():
            link_target = str(source.readlink())
        rows.append(
            {
                "kind": kind,
                "path": str(source),
                "symlinkTarget": link_target,
                "dereferenced": False,
            }
        )
    payload = {
        "createdAt": datetime.now(UTC).isoformat(),
        "plugin": selector,
        "paths": rows,
    }
    return encode(payload, fmt=Format.JSON)


def backup_cache(selector: str, *, home: Path, dest: Path) -> StepResult:
    """Back up exact plugin cache and data paths with a manifest.

    Links are archived AS links (``dereference=False``) and their targets are
    recorded in the manifest: a link target is an external checkout that is
    never deleted, so its content needs no backup.
    """
    step = _step("backup-cache", "tarfile + manifest", str(dest))
    try:
        sources = _removal_sources(selector, home)
    except (OSError, ValueError) as exc:
        return StepResult(step, 1, f"cache discovery failed: {exc}")
    if not sources:
        return StepResult(step, 1, f"no cache or data exists for {selector}")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.touch(mode=_NEW_FILE_MODE, exist_ok=False)
        with tarfile.open(dest, "w:gz") as archive:
            archive.dereference = False
            for _kind, source in sources:
                archive.add(source, arcname=str(source.relative_to(home)))
            manifest = _manifest_bytes(selector, sources)
            info = tarfile.TarInfo("plugin-removal-manifest.json")
            info.size = len(manifest)
            info.mtime = int(datetime.now(UTC).timestamp())
            archive.addfile(info, io.BytesIO(manifest))
    except (OSError, tarfile.TarError, ValueError) as exc:
        return StepResult(step, 1, f"cache backup failed: {type(exc).__name__}")
    _BACKUPS[(home.resolve(), selector)] = _BackupRecord(dest, sources)
    return StepResult(step, 0, f"backed up {len(sources)} path(s) with manifest")


def _selector_installed(plugin: str, home: Path) -> tuple[bool, str | None]:
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    try:
        loaded = json.loads(path.read_text())
    except FileNotFoundError:
        return False, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"installed registry unreadable: {type(exc).__name__}"
    if not isinstance(loaded, dict):
        return False, "installed registry has an invalid shape"
    plugins = loaded.get("plugins")
    if not isinstance(plugins, dict):
        return False, "installed registry has no plugins object"
    entries = plugins.get(plugin, [])
    if not isinstance(entries, list):
        return False, "installed registry entry has an invalid shape"
    return bool(entries), None


def _delete_backup_sources(record: _BackupRecord, selector: str, home: Path) -> int:
    """Delete exactly the recorded set, re-checking containment per path (TOCTOU)."""
    removed = 0
    for _kind, path in record.sources:
        if not _contained(path, selector, home):
            message = f"removal path escaped the plugin's roots before delete: {path}"
            raise PermissionError(message)
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            path.unlink()
        else:
            shutil.rmtree(path)
        removed += 1
    return removed


def _prune_marketplace_cache(selector: str, home: Path) -> None:
    marketplace_dir = (
        home / ".claude" / "plugins" / "cache" / marketplace_name(selector)
    )
    try:
        with os.scandir(marketplace_dir) as entries:
            empty = next(entries, None) is None
    except FileNotFoundError:
        return
    if empty:
        marketplace_dir.rmdir()


def remove_orphan_cache(
    selector: str, *, home: Path, prune_claude_marketplace: bool = False
) -> StepResult:
    """Remove only the backed-up path set after proving the plugin is absent."""
    step = _step("remove-orphan-cache", "remove exact backed-up paths", selector)
    record = _BACKUPS.get((home.resolve(), selector))
    if record is None:
        return StepResult(step, 1, "refusing cache removal without a prior backup")
    try:
        record.archive.lstat()
    except OSError as exc:
        return StepResult(step, 1, f"backup archive unavailable: {type(exc).__name__}")
    installed, error = _selector_installed(selector, home)
    if error is not None:
        return StepResult(step, 1, error)
    if installed:
        return StepResult(step, 1, "refusing cache removal while plugin is installed")
    try:
        removed = _delete_backup_sources(record, selector, home)
        if prune_claude_marketplace:
            _prune_marketplace_cache(selector, home)
    except OSError as exc:
        return StepResult(step, 1, f"cache removal failed: {exc}")
    return StepResult(step, 0, f"removed {removed} backed-up path(s)")


# --------------------------------------------------------------------------
# Native CLI plumbing.
# --------------------------------------------------------------------------


def _native_raw(
    step: RemovalStep, argv: list[str], *, cwd: Path | None = None
) -> tuple[StepResult, str]:
    command = ["mise", "exec", "--", *argv]
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=APPLY_TIMEOUT,
            check=False,
        )
    except FileNotFoundError:
        return StepResult(step, 1, "`mise` is not on PATH"), ""
    except subprocess.TimeoutExpired:
        return StepResult(step, 1, f"timed out after {APPLY_TIMEOUT}s"), ""
    except (OSError, UnicodeDecodeError, subprocess.SubprocessError) as exc:
        return StepResult(step, 1, f"command failed: {type(exc).__name__}"), ""
    detail = " ".join(result.stderr.strip().split())[:500]
    return StepResult(step, result.returncode, detail or "ok"), result.stdout


def _native(
    step: RemovalStep, argv: list[str], *, cwd: Path | None = None
) -> StepResult:
    result, _stdout = _native_raw(step, argv, cwd=cwd)
    return result


# --------------------------------------------------------------------------
# JSON goal state: original text minus the key's whole member span (N2).
# --------------------------------------------------------------------------


def _skip_json_space(text: str, index: int) -> int:
    while index < len(text) and text[index] in _JSON_WHITESPACE:
        index += 1
    return index


def _json_string_end(text: str, index: int) -> int:
    index += 1
    while index < len(text):
        character = text[index]
        if character == "\\":
            index += 2
            continue
        if character == '"':
            return index + 1
        index += 1
    message = "unterminated JSON string"
    raise ValueError(message)


def _json_value_end(text: str, index: int) -> int:
    if index >= len(text):
        message = "missing JSON value"
        raise ValueError(message)
    if text[index] == '"':
        return _json_string_end(text, index)
    if text[index] in "{[":
        depth = 0
        while index < len(text):
            character = text[index]
            if character == '"':
                index = _json_string_end(text, index)
                continue
            if character in "{[":
                depth += 1
            elif character in "}]":
                depth -= 1
                if depth == 0:
                    return index + 1
            index += 1
        message = "unbalanced JSON value"
        raise ValueError(message)
    while index < len(text) and text[index] not in ",}]" + _JSON_WHITESPACE:
        index += 1
    return index


@dataclass(frozen=True)
class _Member:
    key: str
    key_start: int
    value_start: int
    value_end: int


def _object_members(text: str, opening: int) -> tuple[list[_Member], int]:
    """Members of the object whose ``{`` is at ``opening``, plus its ``}`` index."""
    if text[opening] != "{":
        message = "expected a JSON object"
        raise ValueError(message)
    members: list[_Member] = []
    index = _skip_json_space(text, opening + 1)
    if index < len(text) and text[index] == "}":
        return members, index
    while index < len(text):
        if text[index] != '"':
            message = "expected a JSON member key"
            raise ValueError(message)
        key_end = _json_string_end(text, index)
        key = json.loads(text[index:key_end])
        colon = _skip_json_space(text, key_end)
        if colon >= len(text) or text[colon] != ":":
            message = "expected ':' after a JSON key"
            raise ValueError(message)
        value_start = _skip_json_space(text, colon + 1)
        value_end = _json_value_end(text, value_start)
        members.append(_Member(str(key), index, value_start, value_end))
        after = _skip_json_space(text, value_end)
        if after < len(text) and text[after] == ",":
            index = _skip_json_space(text, after + 1)
            continue
        if after < len(text) and text[after] == "}":
            return members, after
        break
    message = "malformed JSON object"
    raise ValueError(message)


def _without_member(text: str, opening: int, key: str) -> str | None:
    members, closing = _object_members(text, opening)
    indexes = [index for index, member in enumerate(members) if member.key == key]
    if len(indexes) != 1:
        return None
    index = indexes[0]
    member = members[index]
    if len(members) == 1:
        return text[: opening + 1] + text[closing:]
    if index < len(members) - 1:
        return text[: member.key_start] + text[members[index + 1].key_start :]
    return text[: members[index - 1].value_end] + text[member.value_end :]


def _remove_json_member_span(text: str, section: str | None, key: str) -> str | None:
    """Delete ``key``'s WHOLE member span (brace-matched, string-aware)."""
    try:
        top = _skip_json_space(text, 0)
        if section is None:
            return _without_member(text, top, key)
        members, _closing = _object_members(text, top)
        owners = [member for member in members if member.key == section]
        if len(owners) != 1 or text[owners[0].value_start] != "{":
            return None
        return _without_member(text, owners[0].value_start, key)
    except ValueError, IndexError:
        return None


def _without_json_key(value: object, section: str | None, key: str) -> object:
    changed = copy.deepcopy(value)
    if not isinstance(changed, dict):
        return changed
    table: object = changed if section is None else changed.get(section)
    if isinstance(table, dict):
        table.pop(key, None)
    return changed


def _normalized(value: object, section: str | None) -> object:
    """Treat an absent section and an empty one as the same goal state."""
    if section is not None and isinstance(value, dict) and value.get(section) == {}:
        trimmed = dict(value)
        trimmed.pop(section)
        return trimmed
    return value


def _json_value(content: bytes, label: str) -> tuple[object | None, str | None]:
    try:
        return json.loads(content), None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"{label}: {type(exc).__name__}"


def _optional_bytes(path: Path) -> tuple[bytes | None, str | None]:
    try:
        return path.read_bytes(), None
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"{path} unreadable after CLI: {type(exc).__name__}"


def _apply_missing_json_goal(
    path: Path, current: bytes | None, section: str | None, key: str
) -> str | None:
    if current is None:
        return None
    current_value, error = _json_value(current, str(path))
    if error is not None:
        return error
    stripped = _normalized(_without_json_key(current_value, section, key), section)
    if stripped:
        return f"{path} changed beyond the requested key"
    try:
        path.unlink()
    except OSError as exc:
        return f"{path} cleanup failed: {type(exc).__name__}"
    return None


def _goal_text(
    original_text: str,
    original_value: object,
    current_goal: object,
    goal: tuple[str | None, str],
) -> tuple[str | None, str | None]:
    """The original text minus the key's span, JSON-equal to the CLI's result."""
    section, key = goal
    table = (
        original_value
        if section is None
        else (original_value.get(section) if isinstance(original_value, dict) else None)
    )
    if not isinstance(table, dict) or key not in table:
        return original_text, None
    minimal = _remove_json_member_span(original_text, section, key)
    if minimal is None:
        return None, f"no unique member span for {key}"
    try:
        minimal_value = json.loads(minimal)
    except json.JSONDecodeError:
        return None, "minimal edit is not valid JSON"
    if (
        section is not None
        and isinstance(minimal_value, dict)
        and minimal_value.get(section) == {}
        and isinstance(current_goal, dict)
        and section not in current_goal
    ):
        dropped = _remove_json_member_span(minimal, None, section)
        if dropped is not None:
            minimal = dropped
            minimal_value = _without_json_key(minimal_value, None, section)
    if _normalized(minimal_value, section) != _normalized(current_goal, section):
        return None, "minimal edit does not match the CLI's result"
    return minimal, None


def _existing_goal_text(
    path: Path,
    original: bytes,
    current: bytes | None,
    goal: tuple[str | None, str],
) -> tuple[str | None, str | None]:
    section, key = goal
    if current is None:
        return None, f"{path} was removed by the CLI"
    original_value, error = _json_value(original, str(path))
    current_value, current_error = _json_value(current, str(path))
    if error is not None or current_error is not None:
        return None, error or current_error
    current_goal = _without_json_key(current_value, section, key)
    expected = _without_json_key(original_value, section, key)
    if _normalized(current_goal, section) != _normalized(expected, section):
        return None, f"{path} changed beyond the requested key"
    text, error = _goal_text(original.decode(), original_value, current_goal, goal)
    if error is not None or text is None:
        return None, f"{path} {error}"
    return text, None


def _apply_existing_json_goal(
    path: Path,
    original: bytes,
    current: bytes | None,
    section: str | None,
    key: str,
) -> str | None:
    text, error = _existing_goal_text(path, original, current, (section, key))
    if error is not None or text is None:
        return error
    if text.encode() == current:
        return None
    try:
        _atomic_write(path, text.encode())
    except OSError as exc:
        return f"{path} goal write failed: {type(exc).__name__}"
    return None


def _apply_json_goal(
    path: Path,
    original: bytes | None,
    *,
    section: str | None,
    key: str,
) -> str | None:
    current, error = _optional_bytes(path)
    if error is not None:
        return error
    if original is None:
        return _apply_missing_json_goal(path, current, section, key)
    return _apply_existing_json_goal(path, original, current, section, key)


def _last_json_object(stdout: str) -> dict[str, object] | None:
    for line in reversed(stdout.splitlines()):
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            return loaded
    return None


# --------------------------------------------------------------------------
# Uninstall (settings = class b; the registry = class a, never restored).
# --------------------------------------------------------------------------


def _scope_absent(
    plugin: str, scope: str, project: Path | None, registry: Path
) -> tuple[bool, str | None]:
    try:
        loaded = json.loads(registry.read_text())
    except FileNotFoundError:
        return True, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"installed registry unreadable: {type(exc).__name__}"
    plugins = loaded.get("plugins") if isinstance(loaded, dict) else None
    entries = plugins.get(plugin, []) if isinstance(plugins, dict) else []
    if not isinstance(entries, list):
        return False, "installed registry entry has an invalid shape"
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("scope") != scope:
            continue
        if project is None or entry.get("projectPath") == str(project):
            return False, None
    return True, None


def _scope_settings(scope: str, home: Path, project: Path | None) -> list[Path]:
    if scope == "user":
        return [home / ".claude" / "settings.json"]
    if project is None:
        return []
    return [
        project / ".claude" / "settings.json",
        project / ".claude" / "settings.local.json",
    ]


def _settings_goals(
    snapshots: dict[Path, bytes | None], *, section: str, key: str
) -> str | None:
    """Apply the goal state to every snapshotted settings file; restore on failure."""
    for path, original in snapshots.items():
        error = _apply_json_goal(path, original, section=section, key=key)
        if error is not None:
            restore_error = _restore_snapshots(snapshots)
            if restore_error is not None:
                error += f"; restore failed: {restore_error}"
            return error
    return None


def _cli_uninstall(
    step: RemovalStep,
    argv: list[str],
    project: Path | None,
    snapshots: dict[Path, bytes | None],
) -> StepResult | None:
    result, stdout = _native_raw(step, argv, cwd=project)
    if result.rc != 0:
        restore_error = _restore_snapshots(snapshots)
        detail = result.detail
        if restore_error is not None:
            detail += f"; restore failed: {restore_error}"
        return StepResult(step, result.rc, detail)
    payload = _last_json_object(stdout)
    if payload is None or payload.get("outcome") != "ok":
        _restore_snapshots(snapshots)
        return StepResult(step, 1, "CLI returned no successful JSON result")
    return None


def _uninstall_scope(
    plugin: str,
    scope: str,
    *,
    home: Path,
    backup_root: Path,
    project: Path | None = None,
) -> StepResult:
    target = str(project) if project is not None else "user"
    argv = ["claude", "plugin", "uninstall", plugin, "--scope", scope]
    argv += ["--keep-data", "--json"]
    step = _step(f"uninstall-{scope}-scope", " ".join(argv), target)
    settings = _scope_settings(scope, home, project)
    if not settings:
        return StepResult(step, 1, f"{scope} scope requires a project path")
    registry = home / ".claude" / "plugins" / "installed_plugins.json"
    _harness, harness_error = _snapshots([registry], backup_root)
    snapshots, backup_error = _snapshots(settings, backup_root)
    if harness_error is not None or backup_error is not None:
        return StepResult(step, 1, harness_error or backup_error or "backup failed")
    failure = _cli_uninstall(step, argv, project, snapshots)
    if failure is not None:
        return failure
    goal_error = _settings_goals(snapshots, section="enabledPlugins", key=plugin)
    if goal_error is not None:
        return StepResult(step, 1, goal_error)
    absent, error = _scope_absent(plugin, scope, project, registry)
    if error is not None or not absent:
        return StepResult(
            step, 1, error or "installed scope survived uninstall (registry re-read)"
        )
    return StepResult(step, 0, f"removed {scope} scope and verified goal state")


def uninstall_project_scope(
    plugin: str,
    project: Path,
    *,
    home: Path | None = None,
    repo_root: Path | None = None,
) -> StepResult:
    """Use Claude's CLI while preserving one-key diffs in both settings files.

    The registry post-condition reads the REAL home's ``installed_plugins.json``
    (N5): a project has no registry of its own.
    """
    return _uninstall_scope(
        plugin,
        "project",
        home=home or Path.home(),
        backup_root=_backup_root(repo_root or Path.cwd()),
        project=project,
    )


def remove_settings_key(plugin: str, path: Path, *, backup_root: Path) -> StepResult:
    """Delete one exact ``enabledPlugins`` key from a settings file, minimal diff."""
    step = _step(_SETTINGS_KEY_STEP, "settings goal-state edit", str(path))
    snapshots, backup_error = _snapshots([path], backup_root)
    if backup_error is not None:
        return StepResult(step, 1, backup_error)
    error = _apply_json_goal(
        path, snapshots[path], section="enabledPlugins", key=plugin
    )
    if error is not None:
        restore_error = _restore_snapshots(snapshots)
        if restore_error is not None:
            error += f"; restore failed: {restore_error}"
        return StepResult(step, 1, error)
    try:
        remaining = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return StepResult(step, 1, f"{path} unreadable after edit: {exc}")
    enabled = remaining.get("enabledPlugins") if isinstance(remaining, dict) else None
    if isinstance(enabled, dict) and plugin in enabled:
        _restore_snapshots(snapshots)
        return StepResult(step, 1, f"{path} still names {plugin}")
    return StepResult(step, 0, "removed one settings key")


def remove_local_override(
    plugin: str, project: Path, *, repo_root: Path | None = None
) -> StepResult:
    """Delete one exact key from a project's gitignored local settings."""
    result = remove_settings_key(
        plugin,
        project / ".claude" / "settings.local.json",
        backup_root=_backup_root(repo_root or Path.cwd()),
    )
    step = _step("remove-local-override", "text edit", str(project))
    return StepResult(step, result.rc, result.detail)


# --------------------------------------------------------------------------
# Claude marketplace removal, one native call per declared scope (N2).
# --------------------------------------------------------------------------


def _declares(path: Path, marketplace: str) -> tuple[bool, str | None]:
    try:
        loaded = json.loads(path.read_text())
    except FileNotFoundError:
        return False, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"{path} unreadable ({type(exc).__name__})"
    declared = (
        loaded.get("extraKnownMarketplaces") if isinstance(loaded, dict) else None
    )
    return isinstance(declared, dict) and marketplace in declared, None


def _registered(known: Path, marketplace: str) -> tuple[bool, str | None]:
    try:
        loaded = json.loads(known.read_text())
    except FileNotFoundError:
        return False, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"known_marketplaces.json unreadable ({type(exc).__name__})"
    return isinstance(loaded, dict) and marketplace in loaded, None


def _marketplace_scopes(
    marketplace: str, *, home: Path, repo_root: Path, step: RemovalStep
) -> tuple[list[tuple[str, Path, Path]], str | None]:
    """(scope, cwd, settings file) for every scope whose settings declare it."""
    calls: list[tuple[str, Path, Path]] = []
    for raw_project in step.context:
        project = Path(raw_project)
        for scope, name in (
            ("project", "settings.json"),
            ("local", "settings.local.json"),
        ):
            path = project / ".claude" / name
            declared, error = _declares(path, marketplace)
            if error is not None:
                return [], error
            if declared:
                calls.append((scope, project, path))
    user_settings = home / ".claude" / "settings.json"
    declared, error = _declares(user_settings, marketplace)
    if error is not None:
        return [], error
    if declared:
        calls.append(("user", repo_root, user_settings))
    return calls, None


def _scoped_marketplace_removal(
    step: RemovalStep,
    marketplace: str,
    call: tuple[str, Path, Path],
    backup_root: Path,
) -> StepResult | None:
    scope, cwd, path = call
    snapshots, backup_error = _snapshots([path], backup_root)
    if backup_error is not None:
        return StepResult(step, 1, backup_error)
    result = _native(
        step,
        ["claude", "plugin", "marketplace", "remove", marketplace, "--scope", scope],
        cwd=cwd,
    )
    if result.rc != 0:
        _restore_snapshots(snapshots)
        return StepResult(step, result.rc, f"--scope {scope} in {cwd}: {result.detail}")
    error = _apply_json_goal(
        path, snapshots[path], section="extraKnownMarketplaces", key=marketplace
    )
    if error is not None:
        restore_error = _restore_snapshots(snapshots)
        if restore_error is not None:
            error += f"; restore failed: {restore_error}"
        return StepResult(step, 1, error)
    return None


def _harness_registration_goal(
    step: RemovalStep,
    marketplace: str,
    context: tuple[Path, Path, Path],
    *,
    user_called: bool,
) -> StepResult | None:
    """Re-read the harness-owned registry; drop a leftover user registration."""
    known, repo_root, backup_root = context
    registered, error = _registered(known, marketplace)
    if error is None and registered and not user_called:
        user_settings = known.parent.parent / "settings.json"
        failure = _scoped_marketplace_removal(
            step, marketplace, ("user", repo_root, user_settings), backup_root
        )
        if failure is not None:
            return failure
        registered, error = _registered(known, marketplace)
    if error is not None:
        return StepResult(step, 1, error)
    if registered:
        detail = f"known_marketplaces.json still registers {marketplace}"
        return StepResult(step, 1, detail + " after native removal")
    return None


def _remove_claude_marketplace_step(
    marketplace: str,
    *,
    home: Path,
    step: RemovalStep,
    repo_root: Path,
    backup_root: Path,
) -> StepResult:
    plugins_dir = home / ".claude" / "plugins"
    known = plugins_dir / "known_marketplaces.json"
    _harness, harness_error = _snapshots(
        [known, plugins_dir / "installed_plugins.json"], backup_root
    )
    calls, error = _marketplace_scopes(
        marketplace, home=home, repo_root=repo_root, step=step
    )
    if harness_error is not None or error is not None:
        return StepResult(step, 1, harness_error or error or "preparation failed")
    for call in calls:
        failure = _scoped_marketplace_removal(step, marketplace, call, backup_root)
        if failure is not None:
            return failure
    failure = _harness_registration_goal(
        step,
        marketplace,
        (known, repo_root, backup_root),
        user_called=any(call[0] == "user" for call in calls),
    )
    if failure is not None:
        return failure
    scopes = ", ".join(sorted({call[0] for call in calls})) or "user"
    return StepResult(
        step, 0, f"removed marketplace ({scopes}) and verified every declaration"
    )


def remove_claude_marketplace(
    marketplace: str, *, repo_root: Path | None = None
) -> StepResult:
    """Remove a Claude marketplace from its user declaration through the CLI."""
    step = _step(
        "remove-claude-marketplace",
        f"claude plugin marketplace remove {marketplace} --scope <each>",
        marketplace,
    )
    root = repo_root or Path.cwd()
    return _remove_claude_marketplace_step(
        marketplace,
        home=Path.home(),
        step=step,
        repo_root=root,
        backup_root=_backup_root(root),
    )


# --------------------------------------------------------------------------
# codex: native calls on a harness-owned config (backed up, never restored).
# --------------------------------------------------------------------------


def _codex_table(
    config: Path, table: str
) -> tuple[dict[str, object] | None, str | None]:
    try:
        parsed = tomllib.loads(config.read_text())
    except FileNotFoundError:
        return {}, None
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return None, f"codex config unreadable: {type(exc).__name__}"
    value = parsed.get(table)
    return (value if isinstance(value, dict) else {}), None


def remove_codex_plugin(
    plugin: str, *, home: Path | None = None, repo_root: Path | None = None
) -> StepResult:
    """Remove an installed codex plugin through the native CLI."""
    step = _step("remove-codex-plugin", f"codex plugin remove {plugin}", plugin)
    actual_home = home or Path.home()
    config = actual_home / ".codex" / "config.toml"
    _snapshot, backup_error = _snapshots(
        [config], _backup_root(repo_root or Path.cwd())
    )
    if backup_error is not None:
        return StepResult(step, 1, backup_error)
    result = _native(step, ["codex", "plugin", "remove", plugin])
    if result.rc != 0:
        return result
    plugins, error = _codex_table(config, "plugins")
    if plugins is None:
        return StepResult(step, 1, error or "codex config unreadable")
    if plugin in plugins:
        return StepResult(step, 1, "codex plugin survived native removal")
    return StepResult(step, 0, "codex plugin absent after native removal")


def remove_codex_marketplace(
    marketplace: str, *, home: Path | None = None, repo_root: Path | None = None
) -> StepResult:
    """Remove a codex marketplace through the native CLI."""
    step = _step(
        "remove-codex-marketplace",
        f"codex plugin marketplace remove {marketplace}",
        marketplace,
    )
    actual_home = home or Path.home()
    config = actual_home / ".codex" / "config.toml"
    _snapshot, backup_error = _snapshots(
        [config], _backup_root(repo_root or Path.cwd())
    )
    if backup_error is not None:
        return StepResult(step, 1, backup_error)
    result = _native(step, ["codex", "plugin", "marketplace", "remove", marketplace])
    if result.rc != 0:
        return result
    marketplaces, error = _codex_table(config, "marketplaces")
    if marketplaces is None:
        return StepResult(step, 1, error or "codex config unreadable")
    if marketplace in marketplaces:
        return StepResult(step, 1, "codex marketplace survived native removal")
    return StepResult(step, 0, "codex marketplace absent after native removal")


# --------------------------------------------------------------------------
# codex config text edits with no native command (hook trust, stray plugin).
# --------------------------------------------------------------------------


def _trusted_hook_key(key: str, plugin: str, home: Path) -> bool:
    if key.startswith(f"{plugin}:"):
        return True
    cache_dir = (
        home
        / ".codex"
        / "plugins"
        / "cache"
        / marketplace_name(plugin)
        / plugin_name(plugin)
    )
    absolute = Path(key).absolute()
    return absolute == cache_dir or absolute.is_relative_to(cache_dir)


def _single_key_path(value: object) -> tuple[str, ...]:
    parts: list[str] = []
    current = value
    while isinstance(current, dict) and len(current) == 1:
        key, current = next(iter(current.items()))
        parts.append(str(key))
    return tuple(parts)


def _header_parts(line: str) -> tuple[str, ...] | None:
    stripped = line.strip()
    if not stripped.startswith("[") or not stripped.endswith("]"):
        return None
    try:
        return _single_key_path(tomllib.loads(stripped + "\n"))
    except tomllib.TOMLDecodeError:
        return None


def _assignment_parts(line: str) -> tuple[str, ...] | None:
    body = line.split("#", 1)[0]
    if "=" not in body:
        return None
    left = body.split("=", 1)[0].strip()
    try:
        return _single_key_path(tomllib.loads(f"{left} = 0\n"))
    except tomllib.TOMLDecodeError:
        return None


def _table_keys(parsed: object, prefix: tuple[str, ...]) -> dict[str, object]:
    current: object = parsed
    for part in prefix:
        current = current.get(part) if isinstance(current, dict) else None
    return current if isinstance(current, dict) else {}


def _entry_key(full: tuple[str, ...], prefix: tuple[str, ...]) -> str | None:
    if len(full) > len(prefix) and full[: len(prefix)] == prefix:
        return full[len(prefix)]
    return None


def _without_toml_entries(
    text: str, prefix: tuple[str, ...], targets: set[str]
) -> tuple[str, int]:
    """Drop every header table and assignment whose key path is prefix + target.

    The full key path is the enclosing header plus the assignment's own dotted
    key, so ``[hooks]`` + ``state."k" = {...}`` resolves exactly like
    ``[hooks.state]`` + ``"k" = {...}`` and a root ``hooks.state."k" = ...``.
    """
    kept: list[str] = []
    removed = 0
    dropping = False
    current_header: tuple[str, ...] = ()
    for line in text.splitlines(keepends=True):
        header = _header_parts(line)
        if header is not None:
            current_header = header
            dropping = _entry_key(header, prefix) in targets
            if dropping:
                removed += 1
                continue
        if dropping:
            continue
        parts = _assignment_parts(line)
        if (
            parts is not None
            and _entry_key((*current_header, *parts), prefix) in targets
        ):
            removed += 1
            continue
        kept.append(line)
    return "".join(kept), removed


def _rollback(
    step: RemovalStep, path: Path, original: bytes, reason: str
) -> StepResult:
    try:
        _atomic_write(path, original)
    except OSError as exc:
        return StepResult(
            step, 1, f"config edit and restore failed: {type(exc).__name__}"
        )
    return StepResult(step, 1, f"config edit rolled back: {reason}")


def _read_codex_config(
    step: RemovalStep, path: Path
) -> tuple[bytes, str, dict[str, object]] | StepResult:
    try:
        original = path.read_bytes()
        original_text = original.decode()
        parsed = tomllib.loads(original_text)
    except FileNotFoundError:
        return StepResult(step, 0, "codex config absent")
    except (OSError, UnicodeDecodeError) as exc:
        return StepResult(step, 1, f"codex config unreadable: {type(exc).__name__}")
    except tomllib.TOMLDecodeError:
        return StepResult(step, 1, "codex config is invalid TOML")
    return original, original_text, parsed


def _commit_codex_edit(
    step: RemovalStep,
    path: Path,
    edit: tuple[bytes, str, Path],
    selection: tuple[tuple[str, ...], Callable[[str], bool]],
) -> StepResult | None:
    """Write the edit, re-parse it, and roll back from memory if anything remains."""
    original, changed, backup_root = edit
    prefix, matches = selection
    try:
        _backup_bytes(path, original, backup_root)
    except OSError as exc:
        return StepResult(step, 1, f"config backup failed: {type(exc).__name__}")
    try:
        _atomic_write(path, changed.encode())
        reparsed = tomllib.loads(path.read_text())
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return _rollback(step, path, original, type(exc).__name__)
    if any(matches(str(key)) for key in _table_keys(reparsed, prefix)):
        return _rollback(step, path, original, "matching entries remain")
    return None


def _edit_codex_config(
    step: RemovalStep,
    home: Path,
    backup_root: Path,
    selection: tuple[tuple[str, ...], Callable[[str], bool]],
) -> StepResult:
    """Remove matching entries under ``prefix``; verify by re-parse, else roll back."""
    prefix, matches = selection
    path = home / ".codex" / "config.toml"
    loaded = _read_codex_config(step, path)
    if isinstance(loaded, StepResult):
        return loaded
    original, original_text, parsed = loaded
    targets = {str(key) for key in _table_keys(parsed, prefix) if matches(str(key))}
    if not targets:
        return StepResult(step, 0, "no matching entries")
    changed, count = _without_toml_entries(original_text, prefix, targets)
    if count == 0:
        return StepResult(
            step, 1, "entries remain in a form the text editor cannot remove"
        )
    failure = _commit_codex_edit(
        step, path, (original, changed, backup_root), selection
    )
    return failure or StepResult(step, 0, f"removed {count} entry(s)")


def remove_codex_hook_trust(
    plugin: str, *, home: Path, repo_root: Path | None = None
) -> StepResult:
    """Delete selector and cache-path hook forms atomically, with rollback."""
    step = _step("remove-codex-hook-trust", "text edit + TOML reparse", plugin)
    return _edit_codex_config(
        step,
        home,
        _backup_root(repo_root or Path.cwd()),
        (_HOOK_PREFIX, lambda key: _trusted_hook_key(key, plugin, home)),
    )


def remove_codex_config_plugin(
    plugin: str, *, home: Path, repo_root: Path | None = None
) -> StepResult:
    """Row 8: drop a ``[plugins."<sel>"]`` table the codex CLI does not list."""
    step = _step(
        "remove-codex-config-plugin", "config.toml text edit + TOML reparse", plugin
    )
    return _edit_codex_config(
        step,
        home,
        _backup_root(repo_root or Path.cwd()),
        (_PLUGIN_PREFIX, lambda key: key == plugin),
    )


# --------------------------------------------------------------------------
# doctor.toml watchlist: insert into the existing array text (N6).
# --------------------------------------------------------------------------


def _array_span(text: str, start: int) -> tuple[int, int] | None:
    opening = text.find("[", start)
    if opening < 0:
        return None
    quote: str | None = None
    escaped = False
    comment = False
    for index in range(opening + 1, len(text)):
        character = text[index]
        comment, handled = _comment_scan(character, comment=comment)
        if handled:
            continue
        quote, escaped, handled = _quote_scan(character, quote=quote, escaped=escaped)
        if handled:
            continue
        if character == "#":
            comment = True
        elif character in {'"', "'"}:
            quote = character
        elif character == "]":
            return opening, index + 1
    return None


def _comment_scan(character: str, *, comment: bool) -> tuple[bool, bool]:
    if not comment:
        return False, False
    return character != "\n", True


def _quote_scan(
    character: str, *, quote: str | None, escaped: bool
) -> tuple[str | None, bool, bool]:
    if quote is None:
        return None, False, False
    if quote == '"' and character == "\\" and not escaped:
        return quote, True, True
    if character == quote and not escaped:
        return None, False, True
    return quote, False, True


def _last_array_element(
    text: str, opening: int, closing: int
) -> tuple[int | None, bool]:
    """End of the last array element, and whether a comma follows it."""
    last_end: int | None = None
    comma_after = False
    index = opening + 1
    while index < closing:
        character = text[index]
        if character == "#":
            newline = text.find("\n", index)
            index = closing if newline < 0 else newline
            continue
        if character in {'"', "'"}:
            end = index + 1
            while end < closing and (
                text[end] != character or (character == '"' and text[end - 1] == "\\")
            ):
                end += 1
            last_end, comma_after, index = end + 1, False, end + 1
            continue
        if character == ",":
            comma_after = True
        elif character not in " \t\r\n":
            end = index
            while end < closing and text[end] not in ",# \t\r\n":
                end += 1
            last_end, comma_after, index = end, False, end
            continue
        index += 1
    return last_end, comma_after


def _insert_array_item(text: str, span: tuple[int, int], item: str) -> str:
    opening, closing_end = span
    closing = closing_end - 1
    last_end, comma_after = _last_array_element(text, opening, closing)
    if last_end is None:
        return text[: opening + 1] + item + text[opening + 1 :]
    if "\n" not in text[last_end:closing]:
        return text[:last_end] + ", " + item + text[last_end:]
    line_start = text.rfind("\n", 0, last_end) + 1
    indent_match = re.match(r"[ \t]*", text[line_start:])
    indent = indent_match.group() if indent_match else ""
    if not comma_after:
        text = text[:last_end] + "," + text[last_end:]
        closing += 1
    close_line = text.rfind("\n", 0, closing) + 1
    addition = f"{indent}{item}{',' if comma_after else ''}\n"
    if text[close_line:closing].strip():
        return text[:closing] + "\n" + addition + text[closing:]
    return text[:close_line] + addition + text[close_line:]


def _watchlist_section_change(
    original: str, existing: object, name: str
) -> tuple[str | None, str | None]:
    if not isinstance(existing, list):
        return None, "removed_plugins names is not a list"
    section_match = re.search(r"(?ms)^\[removed_plugins\]\s*$.*?(?=^\[|\Z)", original)
    if section_match is None:
        return None, "removed_plugins section could not be located"
    names_match = re.search(r"(?m)^names\s*=", section_match.group())
    if names_match is None:
        return None, "removed_plugins names could not be located"
    start = section_match.start() + names_match.end()
    span = _array_span(original, start)
    if span is None:
        return None, "removed_plugins names array is incomplete"
    return _insert_array_item(original, span, json.dumps(name)), None


def _watchlist_change(
    original: str, parsed: dict[str, object], name: str
) -> tuple[str | None, str | None]:
    section = parsed.get("removed_plugins")
    existing = section.get("names") if isinstance(section, dict) else None
    if isinstance(existing, list) and name in existing:
        return None, "already watched"
    if not isinstance(section, dict):
        changed = original.rstrip() + (
            f"\n\n[removed_plugins]\nnames = [{json.dumps(name)}]\n"
        )
        return changed, None
    return _watchlist_section_change(original, existing, name)


def _write_watchlist(
    step: RemovalStep,
    path: Path,
    original: bytes,
    changed: str,
    context: tuple[str, list[object], Path],
) -> StepResult:
    name, existing, backup_root = context
    try:
        checked = tomllib.loads(changed)
        section = checked.get("removed_plugins")
        names = section.get("names") if isinstance(section, dict) else None
        if not isinstance(names, list) or name not in names:
            return StepResult(step, 1, "watchlist verification did not find the name")
        if names != [*existing, name]:
            return StepResult(step, 1, "watchlist verification found other changes")
        _backup_bytes(path, original, backup_root)
        _atomic_write(path, changed.encode())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        try:
            _atomic_write(path, original)
        except OSError:
            return StepResult(step, 1, "watchlist edit and restore failed")
        return StepResult(step, 1, f"watchlist edit failed: {type(exc).__name__}")
    return StepResult(step, 0, "watchlist updated and verified")


def add_to_watchlist(
    name: str, *, repo_root: Path, backup_root: Path | None = None
) -> StepResult:
    """Insert one bare name into ``doctor.toml``'s array text and verify it landed."""
    step = _step("add-to-watchlist", "doctor.toml text edit", name)
    path = repo_root / "doctor.toml"
    try:
        original = path.read_bytes()
        original_text = original.decode()
        parsed = tomllib.loads(original_text)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return StepResult(step, 1, f"doctor.toml unreadable: {type(exc).__name__}")
    changed, change_error = _watchlist_change(original_text, parsed, name)
    if changed is None:
        rc = 0 if change_error == "already watched" else 1
        return StepResult(step, rc, change_error or "watchlist change failed")
    section = parsed.get("removed_plugins")
    existing = section.get("names") if isinstance(section, dict) else None
    return _write_watchlist(
        step,
        path,
        original,
        changed,
        (
            name,
            list(existing) if isinstance(existing, list) else [],
            backup_root or _backup_root(repo_root),
        ),
    )


# --------------------------------------------------------------------------
# Apply.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _RunContext:
    plugin: str
    home: Path
    repo_root: Path
    backup_root: Path
    prune_claude_marketplace: bool


def _fresh_marketplace_guard(
    step: RemovalStep, plugin: str, *, home: Path
) -> StepResult | None:
    claude, codex, errors = marketplace_memberships(plugin, home=home)
    if errors:
        return StepResult(step, 1, errors[0])
    members = claude if step.name == "remove-claude-marketplace" else codex
    installed = sorted(members)
    if installed:
        return StepResult(
            step, 1, "marketplace still has installed plugins: " + ", ".join(installed)
        )
    return None


def _run_uninstall_step(step: RemovalStep, run: _RunContext) -> StepResult | None:
    scope_by_step = {
        "uninstall-user-scope": "user",
        "uninstall-project-scope": "project",
        "uninstall-local-scope": "local",
    }
    scope = scope_by_step.get(step.name)
    if scope is None:
        return None
    project = None if scope == "user" else Path(step.target)
    return _uninstall_scope(
        run.plugin,
        scope,
        home=run.home,
        backup_root=run.backup_root,
        project=project,
    )


def _run_marketplace_step(step: RemovalStep, run: _RunContext) -> StepResult | None:
    marketplace = marketplace_name(run.plugin)
    if step.name == "remove-claude-marketplace":
        guard = _fresh_marketplace_guard(step, run.plugin, home=run.home)
        return guard or _remove_claude_marketplace_step(
            marketplace,
            home=run.home,
            step=step,
            repo_root=run.repo_root,
            backup_root=run.backup_root,
        )
    if step.name == "remove-codex-marketplace":
        guard = _fresh_marketplace_guard(step, run.plugin, home=run.home)
        return guard or remove_codex_marketplace(
            marketplace, home=run.home, repo_root=run.repo_root
        )
    return None


_EDIT_HANDLERS: dict[str, Callable[[RemovalStep, _RunContext], StepResult]] = {
    "backup-cache": lambda step, run: backup_cache(
        run.plugin, home=run.home, dest=Path(step.target)
    ),
    "remove-local-override": lambda step, run: remove_settings_key(
        run.plugin,
        Path(step.target) / ".claude" / "settings.local.json",
        backup_root=run.backup_root,
    ),
    _SETTINGS_KEY_STEP: lambda step, run: remove_settings_key(
        run.plugin, Path(step.target), backup_root=run.backup_root
    ),
    "remove-codex-plugin": lambda _step, run: remove_codex_plugin(
        run.plugin, home=run.home, repo_root=run.repo_root
    ),
    "remove-codex-config-plugin": lambda _step, run: remove_codex_config_plugin(
        run.plugin, home=run.home, repo_root=run.repo_root
    ),
    "remove-codex-hook-trust": lambda _step, run: remove_codex_hook_trust(
        run.plugin, home=run.home, repo_root=run.repo_root
    ),
    "remove-orphan-cache": lambda _step, run: remove_orphan_cache(
        run.plugin,
        home=run.home,
        prune_claude_marketplace=run.prune_claude_marketplace,
    ),
    "add-to-watchlist": lambda _step, run: add_to_watchlist(
        plugin_name(run.plugin),
        repo_root=run.repo_root,
        backup_root=run.backup_root,
    ),
}


def _run_edit_step(step: RemovalStep, run: _RunContext) -> StepResult | None:
    handler = _EDIT_HANDLERS.get(step.name)
    return None if handler is None else handler(step, run)


def _run_step(step: RemovalStep, run: _RunContext) -> StepResult:
    result = (
        _run_uninstall_step(step, run)
        or _run_marketplace_step(step, run)
        or _run_edit_step(step, run)
    )
    if result is None:
        return StepResult(step, 1, f"unknown removal step: {step.name}")
    return StepResult(step, result.rc, result.detail)


def apply(plan: RemovalPlan, *, home: Path, repo_root: Path) -> list[StepResult]:
    """Apply ordered removal steps, stopping immediately at the first failure."""
    if plan.blockers:
        blocked = _step("blocked", "resolve blockers", plan.plugin)
        return [StepResult(blocked, 2, plan.blockers[0])]
    parse_selector(plan.plugin)
    backup_step = next(
        (step for step in plan.steps if step.name == "backup-cache"), None
    )
    backup_root = (
        Path(backup_step.target).parent
        if backup_step is not None
        else _backup_root(repo_root)
    )
    results: list[StepResult] = []
    claude_marketplace_removed = False
    for step in plan.steps:
        run = _RunContext(
            plan.plugin, home, repo_root, backup_root, claude_marketplace_removed
        )
        result = _run_step(step, run)
        results.append(result)
        if result.rc != 0:
            break
        if step.name == "remove-claude-marketplace":
            claude_marketplace_removed = True
    return results


def _print_plan(removal_plan: RemovalPlan) -> None:
    sys.stdout.write(f"plugin: {removal_plan.plugin}\n")
    sys.stdout.write(f"steps: {len(removal_plan.steps)}\n")
    for step in removal_plan.steps:
        sys.stdout.write(f"- {step.name}: {step.target}\n")
    sys.stdout.write(f"blockers: {len(removal_plan.blockers)}\n")
    for blocker in removal_plan.blockers:
        sys.stdout.write(f"- {blocker}\n")
    sys.stdout.write(f"notes: {len(removal_plan.notes)}\n")
    for note in removal_plan.notes:
        sys.stdout.write(f"- {note}\n")


def plugin_remove_main(argv: Sequence[str]) -> int:
    """CLI entry point; dry-run unless ``--apply`` is explicitly present."""
    parser = argparse.ArgumentParser(prog="plugin-remove")
    parser.add_argument("plugin")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        parse_selector(args.plugin)
    except ValueError as exc:
        parser.error(str(exc))
    home = Path.home()
    repo_root = Path.cwd()
    try:
        inv = inventory(args.plugin, home=home, root=home / "dev" / "github")
        removal_plan = plan(inv, repo_root=repo_root)
    except ValueError as exc:
        parser.error(str(exc))
    if not args.apply:
        if args.json:
            sys.stdout.buffer.write(encode(removal_plan, fmt=Format.JSON) + b"\n")
        else:
            _print_plan(removal_plan)
        return 1 if removal_plan.blockers else 0
    results = apply(removal_plan, home=home, repo_root=repo_root)
    if args.json:
        sys.stdout.buffer.write(encode(results, fmt=Format.JSON) + b"\n")
    else:
        for result in results:
            sys.stdout.write(f"{result.step.name}: rc={result.rc} {result.detail}\n")
    return next((result.rc for result in results if result.rc != 0), 0)
