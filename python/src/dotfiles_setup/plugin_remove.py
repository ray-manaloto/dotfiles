# Copyright (c) 2026 Raymond Manaloto
"""Plan and apply bounded native-first plugin removal steps."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.codec import Format, encode
from dotfiles_setup.plugin_inventory import PluginInventory, inventory

if TYPE_CHECKING:
    from collections.abc import Sequence

APPLY_TIMEOUT = 15
_BACKED_UP_CACHES: set[tuple[Path, str]] = set()
_HOOK_HEADER = re.compile(r'^\[hooks\.state\."((?:[^"\\]|\\.)*)"\]\s*$')


@dataclass(frozen=True)
class RemovalStep:
    """One named mutation with a display command/action and exact target."""

    name: str
    argv_or_action: str
    target: str


@dataclass(frozen=True)
class RemovalPlan:
    """Ordered removal steps plus conditions that make apply unsafe."""

    plugin: str
    steps: tuple[RemovalStep, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class StepResult:
    """The observed return code and diagnostic for one removal step."""

    step: RemovalStep
    rc: int
    detail: str


def _step(name: str, argv_or_action: str, target: str) -> RemovalStep:
    return RemovalStep(name=name, argv_or_action=argv_or_action, target=target)


def _archive_path(repo_root: Path, name: str) -> Path:
    return repo_root / ".agent" / "state" / f"plugin-cache-{name}.tar.gz"


def _watchlist(repo_root: Path) -> tuple[frozenset[str], str | None]:
    path = repo_root / "doctor.toml"
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return frozenset(), f"doctor.toml is unreadable ({type(exc).__name__})"
    section = data.get("removed_plugins", {})
    names = section.get("names", []) if isinstance(section, dict) else []
    if not isinstance(names, list):
        return frozenset(), "doctor.toml [removed_plugins].names is not a list"
    return frozenset(str(item) for item in names), None


def _project_steps(inv: PluginInventory) -> list[RemovalStep]:
    steps: list[RemovalStep] = []
    seen_projects: set[Path] = set()
    for settings_path in inv.project_settings:
        project = settings_path.parent.parent
        if settings_path.name == "settings.local.json":
            steps.append(_step("remove-local-override", "text edit", str(project)))
        elif project not in seen_projects:
            seen_projects.add(project)
            steps.append(
                _step(
                    "uninstall-project-scope",
                    f"claude plugin uninstall {inv.plugin} --scope project --json",
                    str(project),
                )
            )
    return steps


def _has_location(inv: PluginInventory, kind: str, *, key: str | None = None) -> bool:
    return any(
        location.kind == kind and (key is None or location.key == key)
        for location in inv.locations
    )


def plan(inv: PluginInventory, *, repo_root: Path) -> RemovalPlan:
    """Build the ordered native-first removal plan for an inventory."""
    plugin = inv.plugin
    name, marketplace = plugin.split("@", 1)
    blockers = list(inv.errors)
    steps: list[RemovalStep] = []
    has_cache = _has_location(inv, "cache")
    if has_cache:
        archive = _archive_path(repo_root, name)
        steps.append(_step("backup-cache", "tarfile", str(archive)))
    steps.extend(_project_steps(inv))

    claude_marketplace = any(
        location.harness == "claude"
        and location.kind in {"declared-marketplace", "known-marketplace"}
        and location.key == marketplace
        for location in inv.locations
    )
    if claude_marketplace:
        steps.append(
            _step(
                "remove-claude-marketplace",
                f"claude plugin marketplace remove {marketplace}",
                marketplace,
            )
        )
    if inv.codex_cli:
        steps.append(
            _step(
                "remove-codex-plugin",
                f"codex plugin remove {plugin}",
                plugin,
            )
        )
    if _has_location(inv, "codex-marketplace", key=marketplace):
        steps.append(
            _step(
                "remove-codex-marketplace",
                f"codex plugin marketplace remove {marketplace}",
                marketplace,
            )
        )
    if _has_location(inv, "codex-hook-trust"):
        steps.append(
            _step("remove-codex-hook-trust", "text edit + TOML reparse", plugin)
        )
    if has_cache:
        steps.append(_step("remove-orphan-cache", "remove backed-up cache", name))

    watched, watch_error = _watchlist(repo_root)
    if watch_error is not None:
        blockers.append(watch_error)
    elif name not in watched:
        steps.append(_step("add-to-watchlist", "doctor.toml text edit", name))
    return RemovalPlan(plugin, tuple(steps), tuple(blockers))


def _cache_paths(name: str, home: Path) -> tuple[Path, ...]:
    found: list[Path] = []
    claude = home / ".claude" / "plugins" / "cache" / name
    if claude.exists():
        found.append(claude)
    codex = home / ".codex" / "plugins" / "cache"
    if codex.exists():
        try:
            marketplaces = tuple(path for path in codex.iterdir() if path.is_dir())
        except OSError:
            return tuple(found)
        found.extend(path / name for path in marketplaces if (path / name).exists())
    return tuple(found)


def backup_cache(name: str, *, home: Path, dest: Path) -> StepResult:
    """Back up exact plugin cache directories into one tar.gz archive."""
    step = _step("backup-cache", "tarfile", str(dest))
    sources = _cache_paths(name, home)
    if not sources:
        return StepResult(step, 1, f"no cache exists for {name}")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(dest, "w:gz") as archive:
            for source in sources:
                archive.add(source, arcname=str(source.relative_to(home)))
    except (OSError, tarfile.TarError, ValueError) as exc:
        return StepResult(step, 1, f"cache backup failed: {type(exc).__name__}")
    _BACKED_UP_CACHES.add((home.resolve(), name))
    return StepResult(step, 0, f"backed up {len(sources)} cache location(s)")


def _native_raw(
    step: RemovalStep, argv: list[str], *, cwd: Path | None = None
) -> tuple[StepResult, str]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=APPLY_TIMEOUT,
            check=False,
        )
    except FileNotFoundError:
        return StepResult(step, 1, f"`{argv[0]}` is not on PATH"), ""
    except subprocess.TimeoutExpired:
        return StepResult(step, 1, f"timed out after {APPLY_TIMEOUT}s"), ""
    except (OSError, subprocess.SubprocessError) as exc:
        return StepResult(step, 1, f"command failed: {type(exc).__name__}"), ""
    detail = " ".join(result.stderr.strip().split())[:500]
    return StepResult(step, result.returncode, detail or "ok"), result.stdout


def _native(
    step: RemovalStep, argv: list[str], *, cwd: Path | None = None
) -> StepResult:
    result, _stdout = _native_raw(step, argv, cwd=cwd)
    return result


def _remove_enabled_line(text: str, plugin: str) -> str | None:
    encoded_key = re.escape(json.dumps(plugin))
    pattern = re.compile(
        rf"^(?P<indent>\s*){encoded_key}\s*:\s*(?:true|false)\s*(?P<comma>,?)\s*$"
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


def _last_json_object(stdout: str) -> dict[str, object] | None:
    for line in reversed(stdout.splitlines()):
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            return loaded
    return None


def _read_json_text(
    step: RemovalStep, path: Path, label: str
) -> tuple[str | None, object | None, StepResult | None]:
    try:
        text = path.read_text()
        return text, json.loads(text), None
    except (OSError, json.JSONDecodeError) as exc:
        error = StepResult(step, 1, f"{label}: {type(exc).__name__}")
        return None, None, error


def _write_minimal_cli_result(
    step: RemovalStep,
    plugin: str,
    original: str,
    cli_text: str,
    cli_result: object,
) -> StepResult:
    path = Path(step.target) / ".claude" / "settings.json"
    minimal = _remove_enabled_line(original, plugin)
    if minimal is None:
        return StepResult(step, 1, "original settings has no unique plugin line")
    try:
        minimal_result = json.loads(minimal)
    except json.JSONDecodeError as exc:
        return StepResult(step, 1, f"minimal settings is invalid JSON: {exc.msg}")
    if minimal_result != cli_result:
        path.write_text(cli_text)
        return StepResult(step, 1, "minimal settings differs from CLI result")
    try:
        path.write_text(minimal)
    except OSError as exc:
        path.write_text(cli_text)
        return StepResult(
            step, 1, f"minimal settings write failed: {type(exc).__name__}"
        )
    return StepResult(step, 0, "removed one settings key; CLI state retained")


def uninstall_project_scope(plugin: str, project: Path) -> StepResult:
    """Use Claude's CLI while preserving a one-key settings diff."""
    settings_path = project / ".claude" / "settings.json"
    step = _step(
        "uninstall-project-scope",
        f"claude plugin uninstall {plugin} --scope project --json",
        str(project),
    )
    original, _original_result, read_error = _read_json_text(
        step, settings_path, "settings unreadable"
    )
    if read_error is not None or original is None:
        return read_error or StepResult(step, 1, "settings unreadable")
    result, stdout = _native_raw(
        step,
        ["claude", "plugin", "uninstall", plugin, "--scope", "project", "--json"],
        cwd=project,
    )
    if result.rc != 0:
        return result
    cli_text, cli_result, cli_error = _read_json_text(
        step, settings_path, "CLI settings result unreadable"
    )
    if cli_error is not None or cli_text is None:
        return cli_error or StepResult(step, 1, "CLI settings result unreadable")
    payload = _last_json_object(stdout)
    if payload is None or payload.get("outcome") != "ok":
        return StepResult(step, 1, "CLI returned no successful JSON result")
    return _write_minimal_cli_result(step, plugin, original, cli_text, cli_result)


def _write_local_result(
    step: RemovalStep,
    path: Path,
    plugin: str,
    original: str,
    expected: dict[str, object],
) -> StepResult:
    minimal = _remove_enabled_line(original, plugin)
    if minimal is None:
        return StepResult(step, 1, "local settings has no unique plugin line")
    try:
        if json.loads(minimal) != expected:
            return StepResult(step, 1, "local minimal edit changed other settings")
        path.write_text(minimal)
    except (OSError, json.JSONDecodeError) as exc:
        return StepResult(step, 1, f"local settings edit failed: {type(exc).__name__}")
    return StepResult(step, 0, "removed one local settings key")


def remove_local_override(plugin: str, project: Path) -> StepResult:
    """Delete one exact key from a project's gitignored local settings."""
    step = _step("remove-local-override", "text edit", str(project))
    path = project / ".claude" / "settings.local.json"
    try:
        original = path.read_text()
    except FileNotFoundError:
        return StepResult(step, 0, "no local override")
    except OSError as exc:
        return StepResult(step, 1, f"local settings unreadable: {type(exc).__name__}")
    try:
        expected = json.loads(original)
    except json.JSONDecodeError as exc:
        return StepResult(step, 1, f"local settings invalid JSON: {exc.msg}")
    enabled = expected.get("enabledPlugins") if isinstance(expected, dict) else None
    if not isinstance(enabled, dict) or plugin not in enabled:
        return StepResult(step, 0, "local override absent")
    del enabled[plugin]
    return _write_local_result(step, path, plugin, original, expected)


def remove_claude_marketplace(marketplace: str) -> StepResult:
    """Remove a Claude marketplace through the native CLI."""
    step = _step(
        "remove-claude-marketplace",
        f"claude plugin marketplace remove {marketplace}",
        marketplace,
    )
    return _native(step, ["claude", "plugin", "marketplace", "remove", marketplace])


def remove_orphan_cache(name: str, *, home: Path) -> StepResult:
    """Remove exact plugin caches only after this process backed them up."""
    step = _step("remove-orphan-cache", "remove backed-up cache", name)
    if (home.resolve(), name) not in _BACKED_UP_CACHES:
        return StepResult(step, 1, "refusing cache removal without a prior backup")
    paths = _cache_paths(name, home)
    try:
        for path in paths:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    except OSError as exc:
        return StepResult(step, 1, f"cache removal failed: {type(exc).__name__}")
    return StepResult(step, 0, f"removed {len(paths)} cache location(s)")


def remove_codex_plugin(plugin: str) -> StepResult:
    """Remove an installed codex plugin through the native CLI."""
    step = _step("remove-codex-plugin", f"codex plugin remove {plugin}", plugin)
    return _native(step, ["codex", "plugin", "remove", plugin])


def remove_codex_marketplace(marketplace: str) -> StepResult:
    """Remove a codex marketplace through the native CLI."""
    step = _step(
        "remove-codex-marketplace",
        f"codex plugin marketplace remove {marketplace}",
        marketplace,
    )
    return _native(step, ["codex", "plugin", "marketplace", "remove", marketplace])


def _decode_header_key(line: str) -> str | None:
    match = _HOOK_HEADER.match(line.strip())
    if match is None:
        return None
    try:
        decoded = json.loads(f'"{match.group(1)}"')
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, str) else None


def _trusted_hook_key(key: str, plugin: str, home: Path) -> bool:
    if key.startswith(f"{plugin}:"):
        return True
    name, marketplace = plugin.split("@", 1)
    cache_dir = home / ".codex" / "plugins" / "cache" / marketplace / name
    try:
        return Path(key).is_relative_to(cache_dir)
    except OSError, ValueError:
        return False


def _without_hook_tables(text: str, plugin: str, home: Path) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    kept: list[str] = []
    removed = 0
    dropping = False
    for line in lines:
        if line.lstrip().startswith("["):
            key = _decode_header_key(line)
            dropping = key is not None and _trusted_hook_key(key, plugin, home)
            if dropping:
                removed += 1
        if not dropping:
            kept.append(line)
    return "".join(kept), removed


def remove_codex_hook_trust(plugin: str, *, home: Path) -> StepResult:
    """Delete selector and cache-path hook tables by text, with rollback."""
    step = _step("remove-codex-hook-trust", "text edit + TOML reparse", plugin)
    path = home / ".codex" / "config.toml"
    backup = path.with_name("config.toml.plugin-remove.bak")
    try:
        original = path.read_text()
    except FileNotFoundError:
        return StepResult(step, 0, "codex config absent")
    except OSError as exc:
        return StepResult(step, 1, f"codex config unreadable: {type(exc).__name__}")
    changed, count = _without_hook_tables(original, plugin, home)
    if count == 0:
        return StepResult(step, 0, "no matching hook-trust tables")
    try:
        backup.write_text(original)
        path.write_text(changed)
        tomllib.loads(changed)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        try:
            path.write_text(backup.read_text())
        except OSError:
            return StepResult(
                step,
                1,
                f"hook-trust edit and restore failed: {type(exc).__name__}",
            )
        return StepResult(step, 1, f"hook-trust edit rolled back: {type(exc).__name__}")
    return StepResult(step, 0, f"removed {count} hook-trust table(s)")


def add_to_watchlist(name: str, *, repo_root: Path) -> StepResult:
    """Append one bare name to ``doctor.toml`` and reparse the result."""
    step = _step("add-to-watchlist", "doctor.toml text edit", name)
    path = repo_root / "doctor.toml"
    try:
        original = path.read_text()
        parsed = tomllib.loads(original)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return StepResult(step, 1, f"doctor.toml unreadable: {type(exc).__name__}")
    section = parsed.get("removed_plugins")
    if isinstance(section, dict):
        names = section.get("names")
        if isinstance(names, list) and name in names:
            return StepResult(step, 0, "already watched")
        section_match = re.search(
            r"(?ms)^\[removed_plugins\]\s*$.*?(?=^\[|\Z)", original
        )
        if section_match is None:
            return StepResult(step, 1, "removed_plugins section could not be located")
        names_match = re.search(r"(?ms)^names\s*=\s*\[(.*?)\]", section_match.group())
        if names_match is None:
            return StepResult(step, 1, "removed_plugins names could not be located")
        insertion = ", " if names_match.group(1).strip() else ""
        position = section_match.start() + names_match.end(1)
        changed = (
            original[:position] + insertion + json.dumps(name) + original[position:]
        )
    else:
        changed = (
            original.rstrip() + f"\n\n[removed_plugins]\nnames = [{json.dumps(name)}]\n"
        )
    try:
        tomllib.loads(changed)
        path.write_text(changed)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return StepResult(step, 1, f"watchlist edit failed: {type(exc).__name__}")
    return StepResult(step, 0, "watchlist updated")


def _run_step(
    step: RemovalStep, plugin: str, *, home: Path, repo_root: Path
) -> StepResult:
    name, marketplace = plugin.split("@", 1)
    match step.name:
        case "backup-cache":
            result = backup_cache(name, home=home, dest=Path(step.target))
        case "uninstall-project-scope":
            result = uninstall_project_scope(plugin, Path(step.target))
        case "remove-local-override":
            result = remove_local_override(plugin, Path(step.target))
        case "remove-claude-marketplace":
            result = remove_claude_marketplace(marketplace)
        case "remove-codex-plugin":
            result = remove_codex_plugin(plugin)
        case "remove-codex-marketplace":
            result = remove_codex_marketplace(marketplace)
        case "remove-codex-hook-trust":
            result = remove_codex_hook_trust(plugin, home=home)
        case "remove-orphan-cache":
            result = remove_orphan_cache(name, home=home)
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
    for step in plan.steps:
        result = _run_step(step, plan.plugin, home=home, repo_root=repo_root)
        results.append(result)
        if result.rc != 0:
            break
    return results


def _print_plan(removal_plan: RemovalPlan) -> None:
    sys.stdout.write(f"plugin: {removal_plan.plugin}\n")
    sys.stdout.write(f"steps: {len(removal_plan.steps)}\n")
    for step in removal_plan.steps:
        sys.stdout.write(f"- {step.name}: {step.target}\n")
    sys.stdout.write(f"blockers: {len(removal_plan.blockers)}\n")
    for blocker in removal_plan.blockers:
        sys.stdout.write(f"- {blocker}\n")


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
        return 2 if inv.errors else 0
    results = apply(removal_plan, home=home, repo_root=repo_root)
    if args.json:
        sys.stdout.buffer.write(encode(results, fmt=Format.JSON) + b"\n")
    else:
        for result in results:
            sys.stdout.write(f"{result.step.name}: rc={result.rc} {result.detail}\n")
    return next((result.rc for result in results if result.rc != 0), 0)
