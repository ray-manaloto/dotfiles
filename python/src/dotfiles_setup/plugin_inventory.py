# Copyright (c) 2026 Raymond Manaloto
"""Inventory a plugin across harness state, repositories, and native CLIs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.codec import Format, encode
from dotfiles_setup.plugin_state import PluginLocation, locate, plugin_name

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


@dataclass(frozen=True)
class _RepoTopology:
    bases: tuple[Path, ...]
    worktrees: tuple[Path, ...]
    stale: tuple[Path, ...]
    errors: tuple[str, ...]


def _diagnostic(text: str) -> str:
    collapsed = " ".join(text.strip().split())
    return collapsed[:500]


def _run_json(argv: list[str], timeout: int) -> tuple[object | None, str | None]:
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return None, f"`{argv[0]}` is not on PATH"
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s: {' '.join(argv)}"
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run `{argv[0]}`: {type(exc).__name__}"
    if result.returncode != 0:
        return None, (
            f"{' '.join(argv)} exited {result.returncode}: {_diagnostic(result.stderr)}"
        )
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"{' '.join(argv)} returned invalid JSON: {exc.msg}"


def claude_cli_rows(name: str, *, timeout: int) -> tuple[list[str], str | None]:
    """Return sanitized exact-id rows from ``claude plugin list --json``."""
    payload, error = _run_json(["claude", "plugin", "list", "--json"], timeout)
    if error is not None:
        return [], error
    if not isinstance(payload, list):
        return [], "claude plugin list --json returned a non-array payload"
    rows: list[str] = []
    for entry in payload:
        if not isinstance(entry, dict) or entry.get("id") != name:
            continue
        scope = entry.get("scope")
        enabled = entry.get("enabled")
        rows.append(f"{name} scope={scope!s} enabled={enabled!s}")
    return rows, None


def codex_cli_rows(name: str, *, timeout: int) -> tuple[list[str], str | None]:
    """Return exact-selector installed rows from ``codex plugin list --json``."""
    if "@" not in name:
        return [], f"codex plugin selector must be name@marketplace: {name}"
    wanted_name, wanted_marketplace = name.split("@", 1)
    payload, error = _run_json(["codex", "plugin", "list", "--json"], timeout)
    if error is not None:
        return [], error
    if not isinstance(payload, dict) or not isinstance(payload.get("installed"), list):
        return [], "codex plugin list --json returned no installed array"
    rows: list[str] = []
    for entry in payload["installed"]:
        if not isinstance(entry, dict):
            continue
        entry_name = entry.get("name")
        marketplace = entry.get("marketplaceName")
        plugin_id = entry.get("pluginId")
        if isinstance(entry_name, str) and isinstance(marketplace, str):
            expected = f"{entry_name}@{marketplace}"
            if plugin_id != expected:
                return [], (
                    "codex plugin list --json pluginId mismatch for "
                    f"{entry_name}@{marketplace}"
                )
        if (
            entry_name == wanted_name
            and marketplace == wanted_marketplace
            and entry.get("installed") is True
        ):
            rows.append(f"{name} enabled={entry.get('enabled')!s}")
    return rows, None


def _base_repos(root: Path) -> list[Path]:
    if not root.exists():
        return []
    repos: list[Path] = []
    try:
        owners = tuple(path for path in root.iterdir() if path.is_dir())
        for owner in owners:
            repos.extend(
                path
                for path in owner.iterdir()
                if path.is_dir() and (path / ".git").exists()
            )
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
        if any(line.startswith("prunable") for line in lines) and not path.exists():
            stale.append(path)
        elif path.exists():
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
            text=True,
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
            f"{_diagnostic(result.stderr)}"
        )
        raise RuntimeError(message)
    found: list[RepoReference] = []
    for row in result.stdout.splitlines():
        path, line_text, text = row.split(":", 2)
        found.append(RepoReference(repo, path, int(line_text), text))
    return found


def _load_user_settings(home: Path) -> tuple[dict[str, object], str | None]:
    path = home / ".claude" / "settings.json"
    try:
        loaded = json.loads(path.read_text())
    except FileNotFoundError:
        return {}, None
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"~/.claude/settings.json is unreadable ({type(exc).__name__})"
    if not isinstance(loaded, dict):
        return {}, "~/.claude/settings.json is not a JSON object"
    return loaded, None


def _enabled_in_settings(path: Path, plugin: str) -> tuple[bool, str | None]:
    try:
        loaded = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"{path} is unreadable ({type(exc).__name__})"
    if not isinstance(loaded, dict):
        return False, f"{path} is not a JSON object"
    enabled = loaded.get("enabledPlugins")
    return isinstance(enabled, dict) and enabled.get(plugin) is True, None


def _settings_paths(repo: Path) -> tuple[Path, ...]:
    settings_dir = repo / ".claude"
    if not settings_dir.exists():
        return ()
    try:
        return tuple(sorted(settings_dir.glob("settings*.json")))
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
                enabled, error = _enabled_in_settings(path, plugin)
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
    errors: list[str] = []
    user_settings, user_error = _load_user_settings(home)
    if user_error is not None:
        errors.append(user_error)
    locations = locate(
        [name],
        home=home,
        settings_sources={"~/.claude/settings.json": user_settings},
    )
    errors.extend(
        f"{location.where} is unreadable ({location.detail})"
        for location in locations
        if location.kind == "unreadable"
    )

    claude_rows, claude_error = claude_cli_rows(plugin, timeout=PROBE_TIMEOUT)
    codex_rows, codex_error = codex_cli_rows(plugin, timeout=PROBE_TIMEOUT)
    errors.extend(error for error in (claude_error, codex_error) if error is not None)

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
        errors=tuple(errors),
    )


def _print_inventory(result: PluginInventory) -> None:
    sys.stdout.write(
        "\n".join(
            (
                f"plugin: {result.plugin}",
                f"locations: {len(result.locations)}",
                f"claude_cli: {len(result.claude_cli)}",
                f"codex_cli: {len(result.codex_cli)}",
                f"project_settings: {len(result.project_settings)}",
                f"worktree_settings: {len(result.worktree_settings)}",
                f"stale_worktrees: {len(result.stale_worktrees)}",
                f"references: {len(result.references)}",
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
