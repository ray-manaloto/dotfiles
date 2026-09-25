# Copyright (c) 2026 Raymond Manaloto
"""Plan and apply bounded native-first plugin removal steps."""

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
from dotfiles_setup.plugin_state import marketplace_name, plugin_name

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

APPLY_TIMEOUT = 15
_HOOK_KEY_INDEX = 2
_HOOK_PATH_PARTS = 3


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


def _safe_selector(selector: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", selector)


def _archive_path(repo_root: Path, selector: str) -> Path:
    name = _safe_selector(selector)
    return (
        repo_root / ".agent" / "state" / f"plugin-removal-{name}.{_utc_stamp()}.tar.gz"
    )


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
                f"claude plugin marketplace remove {marketplace}",
                marketplace,
                _marketplace_projects(inv),
            )
        )
    if inv.codex_cli:
        steps.append(
            _step("remove-codex-plugin", f"codex plugin remove {plugin}", plugin)
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


def plan(inv: PluginInventory, *, repo_root: Path) -> RemovalPlan:
    """Build the ordered native-first removal plan for an inventory."""
    plugin = inv.plugin
    name = plugin_name(plugin)
    blockers = list(inv.errors)
    blockers.extend(
        f"installed plugin depends on target: {dependent}"
        for dependent in inv.dependent_plugins
    )
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
    has_backup_material = bool(removal_targets)
    if has_backup_material:
        archive = _archive_path(repo_root, plugin)
        steps.append(_step("backup-cache", "tarfile + manifest", str(archive)))

    uninstall_steps, scope_blockers = _installed_steps(inv)
    steps.extend(uninstall_steps)
    blockers.extend(scope_blockers)

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


def _absolute_install_path(raw: str, home: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else home / ".claude" / "plugins" / path


def _lexically_within(path: Path, root: Path) -> bool:
    absolute = path.absolute()
    absolute_root = root.absolute()
    return absolute == absolute_root or absolute.is_relative_to(absolute_root)


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
    name = plugin_name(selector)
    marketplace = marketplace_name(selector)
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
            if not _lexically_within(cache_unit, claude_cache):
                message = f"recorded Claude cache is outside cache root: {cache_unit}"
                raise ValueError(message)
            _existing_source("claude-cache", cache_unit, sources)

    _existing_source("claude-cache", claude_cache / marketplace / name, sources)
    _existing_source(
        "codex-cache",
        home / ".codex" / "plugins" / "cache" / marketplace / name,
        sources,
    )
    data_id = _safe_selector(selector)
    _existing_source("claude-data", claude_plugins / "data" / data_id, sources)
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
                "dereferenced": link_target is not None,
            }
        )
    payload = {
        "createdAt": datetime.now(UTC).isoformat(),
        "plugin": selector,
        "paths": rows,
    }
    return encode(payload, fmt=Format.JSON)


def backup_cache(selector: str, *, home: Path, dest: Path) -> StepResult:
    """Back up exact plugin cache and data paths with a manifest."""
    step = _step("backup-cache", "tarfile + manifest", str(dest))
    try:
        sources = _removal_sources(selector, home)
    except (OSError, ValueError) as exc:
        return StepResult(step, 1, f"cache discovery failed: {exc}")
    if not sources:
        return StepResult(step, 1, f"no cache or data exists for {selector}")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(dest, "x:gz") as archive:
            archive.dereference = True
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


def _atomic_write(path: Path, content: bytes) -> None:
    descriptor, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
    except BaseException:
        with suppress(FileNotFoundError):
            temp.unlink()
        raise


def _backup_bytes(path: Path, content: bytes) -> Path:
    backup = path.with_name(f"{path.name}.{_utc_stamp()}.bak")
    try:
        backup.lstat()
    except FileNotFoundError:
        pass
    else:
        message = f"backup already exists: {backup}"
        raise FileExistsError(message)
    _atomic_write(backup, content)
    return backup


def _snapshots(
    paths: Iterable[Path],
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
            _backup_bytes(path, content)
    except OSError as exc:
        return snapshots, f"backup failed before edit: {type(exc).__name__}"
    return snapshots, None


def _restore_snapshots(snapshots: dict[Path, bytes | None]) -> str | None:
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


def _remove_json_key_line(text: str, key: str) -> str | None:
    encoded_key = re.escape(json.dumps(key))
    pattern = re.compile(
        rf"^(?P<indent>\s*){encoded_key}\s*:\s*[^,\n]+(?P<comma>,?)\s*$"
    )
    lines = text.splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines) if pattern.match(line.rstrip("\r\n"))
    ]
    if len(matches) != 1:
        return None
    index = matches[0]
    matched = pattern.match(lines[index].rstrip("\r\n"))
    if matched is None:
        return None
    had_comma = bool(matched.group("comma"))
    del lines[index]
    if not had_comma:
        for previous in range(index - 1, -1, -1):
            body = lines[previous].rstrip("\r\n")
            if not body.strip():
                continue
            newline = lines[previous][len(body) :]
            if body.rstrip().endswith(","):
                trimmed = body.rstrip()
                lines[previous] = trimmed[:-1] + body[len(trimmed) :] + newline
            break
    return "".join(lines)


def _without_json_key(value: object, section: str | None, key: str) -> object:
    changed = copy.deepcopy(value)
    if not isinstance(changed, dict):
        return changed
    table: object = changed if section is None else changed.get(section)
    if isinstance(table, dict):
        table.pop(key, None)
    return changed


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
    stripped = _without_json_key(current_value, section, key)
    if isinstance(stripped, dict) and section in stripped and stripped[section] == {}:
        stripped.pop(section)
    if stripped:
        return f"{path} changed beyond the requested key"
    try:
        path.unlink()
    except OSError as exc:
        return f"{path} cleanup failed: {type(exc).__name__}"
    return None


def _minimal_goal_bytes(
    path: Path,
    original: bytes,
    original_value: object,
    expected: object,
    goal: tuple[str | None, str],
) -> tuple[bytes | None, str | None]:
    section, key = goal
    table = (
        original_value
        if section is None
        else (original_value.get(section) if isinstance(original_value, dict) else None)
    )
    if not isinstance(table, dict) or key not in table:
        return original, None
    minimal = _remove_json_key_line(original.decode(), key)
    if minimal is None:
        return None, f"{path} has no unique line for {key}"
    minimal_bytes = minimal.encode()
    minimal_value, error = _json_value(minimal_bytes, str(path))
    if error is not None or minimal_value != expected:
        return None, f"{path} minimal edit does not match the goal state"
    return minimal_bytes, None


def _verified_current_goal(
    path: Path,
    original_value: object,
    current: bytes | None,
    section: str | None,
    key: str,
) -> tuple[object | None, str | None]:
    if current is None:
        return None, f"{path} was removed by the CLI"
    current_value, error = _json_value(current, str(path))
    if error is not None:
        return None, error
    expected = _without_json_key(original_value, section, key)
    current_without_key = _without_json_key(current_value, section, key)
    original_has_section = (
        isinstance(original_value, dict) and section in original_value
    )
    if (
        section is not None
        and not original_has_section
        and isinstance(current_without_key, dict)
        and current_without_key.get(section) == {}
    ):
        current_without_key.pop(section)
    if current_without_key != expected:
        return None, f"{path} changed beyond the requested key"
    return expected, None


def _apply_existing_json_goal(
    path: Path,
    original: bytes,
    current: bytes | None,
    section: str | None,
    key: str,
) -> str | None:
    original_value, error = _json_value(original, str(path))
    if error is not None:
        return error
    expected, error = _verified_current_goal(
        path, original_value, current, section, key
    )
    if error is not None:
        return error
    if expected is None:
        return f"{path} has no verifiable goal state"
    minimal_bytes, error = _minimal_goal_bytes(
        path, original, original_value, expected, (section, key)
    )
    if error is not None or minimal_bytes is None:
        return error
    try:
        _atomic_write(path, minimal_bytes)
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


def _prepare_uninstall(
    plugin: str,
    scope: str,
    home: Path,
    project: Path | None,
) -> tuple[RemovalStep, list[Path], dict[Path, bytes | None]] | StepResult:
    target = str(project) if project is not None else "user"
    step = _step(
        f"uninstall-{scope}-scope",
        (f"claude plugin uninstall {plugin} --scope {scope} --keep-data --json"),
        target,
    )
    if scope == "user":
        settings = [home / ".claude" / "settings.json"]
    elif project is None:
        return StepResult(step, 1, f"{scope} scope requires a project path")
    else:
        settings = [
            project / ".claude" / "settings.json",
            project / ".claude" / "settings.local.json",
        ]
    registry = home / ".claude" / "plugins" / "installed_plugins.json"
    snapshots, backup_error = _snapshots([registry, *settings])
    if backup_error is not None:
        return StepResult(step, 1, backup_error)
    return step, settings, snapshots


def _uninstall_scope(
    plugin: str,
    scope: str,
    *,
    home: Path,
    project: Path | None = None,
) -> StepResult:
    preparation = _prepare_uninstall(plugin, scope, home, project)
    if isinstance(preparation, StepResult):
        return preparation
    step, settings, snapshots = preparation
    registry = home / ".claude" / "plugins" / "installed_plugins.json"
    result, stdout = _native_raw(
        step,
        [
            "claude",
            "plugin",
            "uninstall",
            plugin,
            "--scope",
            scope,
            "--keep-data",
            "--json",
        ],
        cwd=project,
    )
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
    for path in settings:
        goal_error = _apply_json_goal(
            path,
            snapshots[path],
            section="enabledPlugins",
            key=plugin,
        )
        if goal_error is not None:
            restore_error = _restore_snapshots(snapshots)
            if restore_error is not None:
                goal_error += f"; restore failed: {restore_error}"
            return StepResult(step, 1, goal_error)
    absent, error = _scope_absent(plugin, scope, project, registry)
    if error is not None or not absent:
        _restore_snapshots(snapshots)
        return StepResult(step, 1, error or "installed scope survived uninstall")
    return StepResult(step, 0, f"removed {scope} scope and verified goal state")


def uninstall_project_scope(plugin: str, project: Path) -> StepResult:
    """Use Claude's CLI while preserving one-key diffs in both settings files."""
    return _uninstall_scope(plugin, "project", home=project, project=project)


def remove_local_override(plugin: str, project: Path) -> StepResult:
    """Delete one exact key from a project's gitignored local settings."""
    step = _step("remove-local-override", "text edit", str(project))
    path = project / ".claude" / "settings.local.json"
    snapshots, backup_error = _snapshots([path])
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
    return StepResult(step, 0, "removed one local settings key")


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


def _delete_backup_sources(record: _BackupRecord) -> int:
    removed = 0
    for _kind, path in record.sources:
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            continue
        if path.is_symlink() or not stat.S_ISDIR(mode):
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
        removed = _delete_backup_sources(record)
        if prune_claude_marketplace:
            _prune_marketplace_cache(selector, home)
    except OSError as exc:
        return StepResult(step, 1, f"cache removal failed: {type(exc).__name__}")
    return StepResult(step, 0, f"removed {removed} backed-up path(s)")


def _marketplace_settings_paths(home: Path, step: RemovalStep) -> tuple[Path, ...]:
    paths = {home / ".claude" / "settings.json"}
    for raw_project in step.context:
        project = Path(raw_project)
        paths.add(project / ".claude" / "settings.json")
        paths.add(project / ".claude" / "settings.local.json")
    return tuple(sorted(paths))


def _remove_claude_marketplace_step(
    marketplace: str, *, home: Path, step: RemovalStep
) -> StepResult:
    settings = _marketplace_settings_paths(home, step)
    known = home / ".claude" / "plugins" / "known_marketplaces.json"
    registry = home / ".claude" / "plugins" / "installed_plugins.json"
    snapshots, backup_error = _snapshots([known, registry, *settings])
    if backup_error is not None:
        return StepResult(step, 1, backup_error)
    result = _native(step, ["claude", "plugin", "marketplace", "remove", marketplace])
    if result.rc != 0:
        _restore_snapshots(snapshots)
        return result
    goal_paths = [
        (known, None),
        *((path, "extraKnownMarketplaces") for path in settings),
    ]
    for path, section in goal_paths:
        error = _apply_json_goal(
            path, snapshots[path], section=section, key=marketplace
        )
        if error is not None:
            restore_error = _restore_snapshots(snapshots)
            if restore_error is not None:
                error += f"; restore failed: {restore_error}"
            return StepResult(step, 1, error)
    return StepResult(step, 0, "removed marketplace and verified declarations")


def remove_claude_marketplace(marketplace: str) -> StepResult:
    """Remove a Claude marketplace through the native CLI."""
    step = _step(
        "remove-claude-marketplace",
        f"claude plugin marketplace remove {marketplace}",
        marketplace,
    )
    return _remove_claude_marketplace_step(marketplace, home=Path.home(), step=step)


def remove_codex_plugin(plugin: str, *, home: Path | None = None) -> StepResult:
    """Remove an installed codex plugin through the native CLI."""
    step = _step("remove-codex-plugin", f"codex plugin remove {plugin}", plugin)
    actual_home = home or Path.home()
    config = actual_home / ".codex" / "config.toml"
    snapshots, backup_error = _snapshots([config])
    if backup_error is not None:
        return StepResult(step, 1, backup_error)
    result = _native(step, ["codex", "plugin", "remove", plugin])
    if result.rc != 0:
        _restore_snapshots(snapshots)
        return result
    try:
        parsed = tomllib.loads(config.read_text())
    except FileNotFoundError:
        parsed = {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        _restore_snapshots(snapshots)
        return StepResult(step, 1, f"codex config unreadable: {type(exc).__name__}")
    plugins = parsed.get("plugins") if isinstance(parsed, dict) else None
    if isinstance(plugins, dict) and plugin in plugins:
        _restore_snapshots(snapshots)
        return StepResult(step, 1, "codex plugin survived native removal")
    return StepResult(step, 0, "codex plugin absent after native removal")


def remove_codex_marketplace(
    marketplace: str, *, home: Path | None = None
) -> StepResult:
    """Remove a codex marketplace through the native CLI."""
    step = _step(
        "remove-codex-marketplace",
        f"codex plugin marketplace remove {marketplace}",
        marketplace,
    )
    actual_home = home or Path.home()
    config = actual_home / ".codex" / "config.toml"
    snapshots, backup_error = _snapshots([config])
    if backup_error is not None:
        return StepResult(step, 1, backup_error)
    result = _native(step, ["codex", "plugin", "marketplace", "remove", marketplace])
    if result.rc != 0:
        _restore_snapshots(snapshots)
        return result
    try:
        parsed = tomllib.loads(config.read_text())
    except FileNotFoundError:
        parsed = {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        _restore_snapshots(snapshots)
        return StepResult(step, 1, f"codex config unreadable: {type(exc).__name__}")
    marketplaces = parsed.get("marketplaces") if isinstance(parsed, dict) else None
    if isinstance(marketplaces, dict) and marketplace in marketplaces:
        _restore_snapshots(snapshots)
        return StepResult(step, 1, "codex marketplace survived native removal")
    return StepResult(step, 0, "codex marketplace absent after native removal")


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
    return _lexically_within(Path(key), cache_dir)


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


def _hook_state(parsed: object) -> dict[str, object]:
    hooks = parsed.get("hooks") if isinstance(parsed, dict) else None
    state = hooks.get("state") if isinstance(hooks, dict) else None
    return state if isinstance(state, dict) else {}


def _header_hook_key(parts: tuple[str, ...] | None) -> str | None:
    if (
        parts is not None
        and len(parts) >= _HOOK_PATH_PARTS
        and parts[:_HOOK_KEY_INDEX] == ("hooks", "state")
    ):
        return parts[_HOOK_KEY_INDEX]
    return None


def _assignment_hook_key(
    parts: tuple[str, ...] | None, current_header: tuple[str, ...]
) -> str | None:
    if parts is None:
        return None
    if current_header == ("hooks", "state") and len(parts) == 1:
        return parts[0]
    if len(parts) >= _HOOK_PATH_PARTS and parts[:_HOOK_KEY_INDEX] == ("hooks", "state"):
        return parts[_HOOK_KEY_INDEX]
    return None


def _without_hook_tables(text: str, plugin: str, home: Path) -> tuple[str, int, bool]:
    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return text, 0, False
    targets = {
        str(key)
        for key in _hook_state(parsed)
        if _trusted_hook_key(str(key), plugin, home)
    }
    if not targets:
        return text, 0, True
    lines = text.splitlines(keepends=True)
    kept: list[str] = []
    removed = 0
    dropping_target: str | None = None
    current_header: tuple[str, ...] = ()
    for line in lines:
        header = _header_parts(line)
        if header is not None:
            current_header = header
            candidate = _header_hook_key(header)
            dropping_target = candidate if candidate in targets else None
            if dropping_target is not None:
                removed += 1
                continue
        if dropping_target is not None:
            continue
        candidate = _assignment_hook_key(_assignment_parts(line), current_header)
        if candidate in targets:
            removed += 1
            continue
        kept.append(line)
    return "".join(kept), removed, True


def _hook_rollback_result(
    step: RemovalStep, path: Path, original: bytes, reason: str
) -> StepResult:
    try:
        _atomic_write(path, original)
    except OSError as exc:
        return StepResult(
            step,
            1,
            f"hook-trust edit and restore failed: {type(exc).__name__}",
        )
    return StepResult(step, 1, f"hook-trust edit rolled back: {reason}")


def _write_hook_edit(
    step: RemovalStep,
    path: Path,
    original: bytes,
    edit: tuple[str, str, Path],
) -> StepResult | None:
    changed, plugin, home = edit
    try:
        _atomic_write(path, changed.encode())
        reparsed = tomllib.loads(path.read_text())
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return _hook_rollback_result(step, path, original, type(exc).__name__)
    remaining = [
        str(key)
        for key in _hook_state(reparsed)
        if _trusted_hook_key(str(key), plugin, home)
    ]
    if remaining:
        return _hook_rollback_result(step, path, original, "hook trust remains")
    return None


def _read_hook_config(step: RemovalStep, path: Path) -> tuple[bytes, str] | StepResult:
    try:
        original = path.read_bytes()
        return original, original.decode()
    except FileNotFoundError:
        return StepResult(step, 0, "codex config absent")
    except (OSError, UnicodeDecodeError) as exc:
        return StepResult(step, 1, f"codex config unreadable: {type(exc).__name__}")


def remove_codex_hook_trust(plugin: str, *, home: Path) -> StepResult:
    """Delete selector and cache-path hook forms atomically, with rollback."""
    step = _step("remove-codex-hook-trust", "text edit + TOML reparse", plugin)
    path = home / ".codex" / "config.toml"
    read_result = _read_hook_config(step, path)
    if isinstance(read_result, StepResult):
        return read_result
    original, original_text = read_result
    changed, count, parsed = _without_hook_tables(original_text, plugin, home)
    if not parsed:
        return StepResult(step, 1, "codex config is invalid TOML")
    if count == 0:
        return StepResult(step, 0, "no matching hook-trust entries")
    try:
        _backup_bytes(path, original)
    except OSError as exc:
        return StepResult(step, 1, f"hook-trust backup failed: {type(exc).__name__}")
    failure = _write_hook_edit(step, path, original, (changed, plugin, home))
    if failure is not None:
        return failure
    return StepResult(step, 0, f"removed {count} hook-trust entry(s)")


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
    replacement = json.dumps([*existing, name])
    return original[: span[0]] + replacement + original[span[1] :], None


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
    step: RemovalStep, path: Path, original: bytes, changed: str, name: str
) -> StepResult:
    try:
        checked = tomllib.loads(changed)
        section = checked.get("removed_plugins")
        names = section.get("names") if isinstance(section, dict) else None
        if not isinstance(names, list) or name not in names:
            return StepResult(step, 1, "watchlist verification did not find the name")
        _backup_bytes(path, original)
        _atomic_write(path, changed.encode())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        try:
            _atomic_write(path, original)
        except OSError:
            return StepResult(step, 1, "watchlist edit and restore failed")
        return StepResult(step, 1, f"watchlist edit failed: {type(exc).__name__}")
    return StepResult(step, 0, "watchlist updated and verified")


def add_to_watchlist(name: str, *, repo_root: Path) -> StepResult:
    """Append one bare name to ``doctor.toml`` and verify it landed."""
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
    return _write_watchlist(step, path, original, changed, name)


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


def _run_uninstall_step(
    step: RemovalStep, plugin: str, *, home: Path
) -> StepResult | None:
    scope_by_step = {
        "uninstall-user-scope": "user",
        "uninstall-project-scope": "project",
        "uninstall-local-scope": "local",
    }
    scope = scope_by_step.get(step.name)
    if scope is None:
        return None
    project = None if scope == "user" else Path(step.target)
    return _uninstall_scope(plugin, scope, home=home, project=project)


def _run_marketplace_step(
    step: RemovalStep, plugin: str, *, home: Path
) -> StepResult | None:
    marketplace = marketplace_name(plugin)
    if step.name == "remove-claude-marketplace":
        guard = _fresh_marketplace_guard(step, plugin, home=home)
        return guard or _remove_claude_marketplace_step(
            marketplace, home=home, step=step
        )
    if step.name == "remove-codex-marketplace":
        guard = _fresh_marketplace_guard(step, plugin, home=home)
        return guard or remove_codex_marketplace(marketplace, home=home)
    return None


def _run_step(
    step: RemovalStep,
    plugin: str,
    *,
    home: Path,
    repo_root: Path,
    prune_claude_marketplace: bool,
) -> StepResult:
    name = plugin_name(plugin)
    result = _run_uninstall_step(step, plugin, home=home)
    if result is None:
        result = _run_marketplace_step(step, plugin, home=home)
    if result is not None:
        return StepResult(step, result.rc, result.detail)
    match step.name:
        case "backup-cache":
            result = backup_cache(plugin, home=home, dest=Path(step.target))
        case "remove-local-override":
            result = remove_local_override(plugin, Path(step.target))
        case "remove-codex-plugin":
            result = remove_codex_plugin(plugin, home=home)
        case "remove-codex-hook-trust":
            result = remove_codex_hook_trust(plugin, home=home)
        case "remove-orphan-cache":
            result = remove_orphan_cache(
                plugin,
                home=home,
                prune_claude_marketplace=prune_claude_marketplace,
            )
        case "add-to-watchlist":
            result = add_to_watchlist(name, repo_root=repo_root)
        case _:
            return StepResult(step, 1, f"unknown removal step: {step.name}")
    return StepResult(step, result.rc, result.detail)


def apply(plan: RemovalPlan, *, home: Path, repo_root: Path) -> list[StepResult]:
    """Apply ordered removal steps, stopping immediately at the first failure."""
    if plan.blockers:
        blocked = _step("blocked", "resolve blockers", plan.plugin)
        return [StepResult(blocked, 2, plan.blockers[0])]
    results: list[StepResult] = []
    claude_marketplace_removed = False
    for step in plan.steps:
        result = _run_step(
            step,
            plan.plugin,
            home=home,
            repo_root=repo_root,
            prune_claude_marketplace=claude_marketplace_removed,
        )
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
