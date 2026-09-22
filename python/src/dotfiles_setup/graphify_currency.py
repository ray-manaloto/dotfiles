# Copyright (c) 2026 Raymond Manaloto
"""Graphify package, skill-surface, and PATH currency management.

The lockfile is the repository's only Graphify version pin. This module owns
the deterministic update/check workflow around that pin; graph rebuilding
stays in :mod:`dotfiles_setup.graphify` so package currency never silently
mutates the graph.
"""

from __future__ import annotations

import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from dotfiles_setup import graphify_skill

DIST = "graphifyy"
MISE_TOOL = "pipx:graphifyy"
GITHUB_REPO = "Graphify-Labs/graphify"
RECEIPT_DIR = Path(".agent/graphify")

_VERSION_RE = re.compile(r"\b(\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*))\b")
_LATEST_TIMEOUT_SECONDS = 30
_GH_TIMEOUT_SECONDS = 60
_UV_TIMEOUT_SECONDS = 300
_PATH_TIMEOUT_SECONDS = 10

type Run = Callable[..., subprocess.CompletedProcess[str]]


class GraphifyCurrencyError(RuntimeError):
    """Raised when Graphify currency cannot be established or updated safely."""


@dataclass(frozen=True)
class Versions:
    """Observed Graphify versions across the repository and host seams."""

    locked: str
    installed: str
    latest: str | None
    path_binary: str | None


@dataclass(frozen=True)
class Drift:
    """One actionable Graphify currency or skill-surface mismatch."""

    kind: str
    detail: str


@dataclass(frozen=True)
class _Probe:
    value: str | None
    error: str = ""
    absent: bool = False


def locked_version(project_root: Path) -> str:
    """Return the single Graphify version recorded in ``python/uv.lock``."""
    lock_path = project_root / "python/uv.lock"
    try:
        with lock_path.open("rb") as handle:
            payload = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        message = f"cannot read {lock_path}: {exc}"
        raise GraphifyCurrencyError(message) from exc

    packages = payload.get("package")
    if not isinstance(packages, list):
        message = f"{lock_path} has no package entries"
        raise GraphifyCurrencyError(message)
    matches = [
        package.get("version")
        for package in packages
        if isinstance(package, dict) and package.get("name") == DIST
    ]
    if len(matches) != 1 or not isinstance(matches[0], str):
        message = (
            f"{lock_path} must contain exactly one {DIST!r} package entry; "
            f"found {len(matches)}"
        )
        raise GraphifyCurrencyError(message)
    try:
        Version(matches[0])
    except InvalidVersion as exc:
        message = f"{lock_path} carries invalid {DIST} version {matches[0]!r}"
        raise GraphifyCurrencyError(message) from exc
    return matches[0]


def installed_version() -> str:
    """Return the Graphify distribution version installed in this uv project."""
    return importlib.metadata.version(DIST)


def _latest_probe(*, run: Run) -> _Probe:
    try:
        result = run(
            ["mise", "latest", MISE_TOOL],
            capture_output=True,
            text=True,
            check=False,
            timeout=_LATEST_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _Probe(None, str(exc))
    if result.returncode != 0:
        detail = result.stderr.strip() or f"mise latest exited {result.returncode}"
        return _Probe(None, detail)
    candidate = result.stdout.strip()
    if not candidate:
        return _Probe(None, "mise latest returned empty stdout")
    try:
        Version(candidate)
    except InvalidVersion:
        return _Probe(None, f"mise latest returned invalid version {candidate!r}")
    return _Probe(candidate)


def latest_version(run: Run = subprocess.run) -> str | None:
    """Return ``mise latest pipx:graphifyy`` stdout, or ``None`` on failure."""
    return _latest_probe(run=run).value


def _require_latest(*, run: Run) -> str:
    """Return the latest version or fail closed with the probe diagnostic."""
    probe = _latest_probe(run=run)
    if probe.value is None:
        message = f"latest UNVERIFIABLE: {probe.error}"
        raise GraphifyCurrencyError(message)
    return probe.value


def _path_binary_probe(*, run: Run) -> _Probe:
    binary = shutil.which("graphify")
    if binary is None:
        return _Probe(None, absent=True)
    try:
        result = run(
            ["graphify", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_PATH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _Probe(None, str(exc))
    output = f"{result.stdout}\n{result.stderr}"
    match = _VERSION_RE.search(output)
    if result.returncode != 0:
        detail = result.stderr.strip() or (
            f"graphify --version exited {result.returncode}"
        )
        return _Probe(None, detail)
    if match is None:
        return _Probe(None, "graphify --version returned no usable version")
    try:
        Version(match.group(1))
    except InvalidVersion:
        return _Probe(None, f"graphify --version returned {match.group(1)!r}")
    return _Probe(match.group(1))


def path_binary_version(run: Run = subprocess.run) -> str | None:
    """Return the user-global PATH Graphify version, or ``None`` if absent."""
    return _path_binary_probe(run=run).value


def _json_documents(raw: str) -> Iterable[Any]:
    """Yield each JSON document emitted by ``gh api --paginate``."""
    decoder = json.JSONDecoder()
    remaining = raw.lstrip()
    while remaining:
        try:
            value, offset = decoder.raw_decode(remaining)
        except json.JSONDecodeError as exc:
            message = f"gh api returned invalid JSON: {exc}"
            raise GraphifyCurrencyError(message) from exc
        yield value
        remaining = remaining[offset:].lstrip()


def _release_rows(raw: str) -> Iterable[dict[str, Any]]:
    for document in _json_documents(raw):
        pages = document if isinstance(document, list) else [document]
        for page in pages:
            rows = page if isinstance(page, list) else [page]
            for row in rows:
                if isinstance(row, dict):
                    yield row


def release_notes_between(
    low: str,
    high: str,
    run: Run = subprocess.run,
) -> list[tuple[str, str]]:
    """Fetch public Graphify GitHub release notes in ``(low, high]``."""
    low_version = Version(low)
    high_version = Version(high)
    try:
        result = run(
            ["gh", "api", f"repos/{GITHUB_REPO}/releases", "--paginate"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        message = f"gh api failed: {exc}"
        raise GraphifyCurrencyError(message) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or f"gh api exited {result.returncode}"
        message = f"gh api failed: {detail}"
        raise GraphifyCurrencyError(message)

    notes: list[tuple[Version, str, str]] = []
    for row in _release_rows(result.stdout):
        tag = row.get("tag_name")
        if not isinstance(tag, str):
            continue
        candidate = tag.removeprefix("v")
        try:
            release_version = Version(candidate)
        except InvalidVersion:
            continue
        if low_version < release_version <= high_version:
            body = row.get("body")
            notes.append((release_version, tag, body if isinstance(body, str) else ""))
    notes.sort(key=lambda item: item[0])
    if not any(version == high_version for version, _, _ in notes):
        message = f"gh api returned no release for target version {high}"
        raise GraphifyCurrencyError(message)
    return [(tag, body) for _, tag, body in notes]


def write_release_receipt(
    project_root: Path,
    notes: list[tuple[str, str]],
    *,
    high: str,
) -> Path:
    """Write the fetched release-note review receipt below ``.agent/``."""
    receipt_dir = project_root / RECEIPT_DIR
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = receipt_dir / f"release-notes-{high}.md"
    sections = [f"# Graphify release notes through {high}", ""]
    for tag, body in notes:
        sections.extend((f"## {tag}", "", body.strip() or "_No release notes._", ""))
    receipt.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return receipt


def upgrade_lock(project_root: Path, run: Run = subprocess.run) -> None:
    """Upgrade the Graphify lock entry with native uv, then sync the project."""
    commands = (
        ["uv", "lock", "--project", "python", "--upgrade-package", DIST],
        ["uv", "sync", "--project", "python"],
    )
    for command in commands:
        try:
            result = run(
                command,
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=_UV_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            message = f"{' '.join(command)} failed: {exc}"
            raise GraphifyCurrencyError(message) from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exited {result.returncode}"
            message = f"{' '.join(command)} failed: {detail}"
            raise GraphifyCurrencyError(message)


def _skill_drifts(project_root: Path) -> tuple[Drift, ...]:
    try:
        skill_drifts = graphify_skill.check_skills(project_root)
    except (
        KeyError,
        ModuleNotFoundError,
        FileNotFoundError,
        ValueError,
        OSError,
    ) as exc:
        return (Drift("skill-bytes", f"UNVERIFIABLE: {exc}"),)
    return tuple(
        Drift(
            "stamp" if drift.path.name == ".graphify_version" else "skill-bytes",
            f"{drift.path.relative_to(project_root)}: {drift.reason} — "
            "run `mise run graphify-update`",
        )
        for drift in skill_drifts
    )


def _check_with_versions(project_root: Path) -> tuple[Versions, tuple[Drift, ...]]:
    drifts: list[Drift] = []
    try:
        locked = locked_version(project_root)
    except GraphifyCurrencyError as exc:
        locked = "UNVERIFIABLE"
        drifts.append(Drift("lock-behind-latest", f"UNVERIFIABLE: {exc}"))

    try:
        installed = installed_version()
    except importlib.metadata.PackageNotFoundError as exc:
        installed = "UNVERIFIABLE"
        drifts.append(Drift("installed!=locked", f"UNVERIFIABLE: {exc}"))

    latest_probe = _latest_probe(run=subprocess.run)
    if latest_probe.value is None:
        drifts.append(
            Drift(
                "lock-behind-latest",
                f"UNVERIFIABLE: {latest_probe.error}",
            )
        )
    elif locked != "UNVERIFIABLE" and Version(latest_probe.value) > Version(locked):
        drifts.append(
            Drift(
                "lock-behind-latest",
                f"graphifyy locked {locked}, latest {latest_probe.value} — "
                "run `mise run graphify-update`",
            )
        )

    if locked != "UNVERIFIABLE" and installed not in ("UNVERIFIABLE", locked):
        drifts.append(
            Drift(
                "installed!=locked",
                f"installed graphifyy {installed} != locked {locked} — "
                "run `uv sync --project python`",
            )
        )

    drifts.extend(_skill_drifts(project_root))

    path_probe = _path_binary_probe(run=subprocess.run)
    if path_probe.value is None and not path_probe.absent:
        drifts.append(Drift("path-binary", f"UNVERIFIABLE: {path_probe.error}"))
    elif path_probe.value is not None and locked not in (
        "UNVERIFIABLE",
        path_probe.value,
    ):
        drifts.append(
            Drift(
                "path-binary",
                f"PATH graphify {path_probe.value} != locked {locked} — update "
                "the user-global mise pin",
            )
        )

    versions = Versions(
        locked=locked,
        installed=installed,
        latest=latest_probe.value,
        path_binary=path_probe.value,
    )
    return versions, tuple(drifts)


def check(project_root: Path) -> tuple[Drift, ...]:
    """Return every read-only Graphify currency and skill-surface drift."""
    return _check_with_versions(project_root)[1]


def _refresh_skills(project_root: Path) -> None:
    try:
        written = graphify_skill.refresh_skills(project_root)
    except (
        KeyError,
        ModuleNotFoundError,
        FileNotFoundError,
        ValueError,
        OSError,
    ) as exc:
        message = f"graphify skill refresh failed: {exc}"
        raise GraphifyCurrencyError(message) from exc
    if written:
        for path in written:
            sys.stdout.write(f"skill refreshed -> {path}\n")
    else:
        sys.stdout.write(f"graphify skills current ({installed_version()})\n")


def _require_updated_lock(updated: str, latest: str) -> None:
    """Fail when native uv did not move the single lock pin to the target."""
    if Version(updated) != Version(latest):
        message = f"uv locked {updated}, expected latest {latest}"
        raise GraphifyCurrencyError(message)


def graphify_update_main(project_root: Path) -> int:
    """Update the Graphify lock and managed skill surfaces, never the graph."""
    try:
        locked = locked_version(project_root)
        latest = _require_latest(run=subprocess.run)

        if Version(latest) > Version(locked):
            sys.stdout.write(f"graphifyy locked {locked}, latest {latest}\n")
            notes = release_notes_between(locked, latest, run=subprocess.run)
            receipt = write_release_receipt(project_root, notes, high=latest)
            sys.stdout.write(f"release notes -> {receipt} ({len(notes)} releases)\n")
            upgrade_lock(project_root, run=subprocess.run)
            updated = locked_version(project_root)
            _require_updated_lock(updated, latest)
            sys.stdout.write(
                f"graphifyy lock updated to {updated}; environment synced\n"
            )
        elif Version(latest) == Version(locked):
            sys.stdout.write(
                f"graphifyy locked {locked}, latest {latest} — already current\n"
            )
        else:
            sys.stdout.write(
                f"graphifyy locked {locked} is ahead of latest {latest}; no downgrade\n"
            )

        _refresh_skills(project_root)
    except (GraphifyCurrencyError, InvalidVersion) as exc:
        sys.stderr.write(f"graphify update failed: {exc}\n")
        return 1
    return 0


def graphify_check_main(project_root: Path) -> int:
    """Print Graphify currency drift and return nonzero when any exists."""
    versions, drifts = _check_with_versions(project_root)
    latest = versions.latest if versions.latest is not None else "UNVERIFIABLE"
    sys.stdout.write(f"graphifyy locked {versions.locked}, latest {latest}\n")
    for drift in drifts:
        sys.stdout.write(f"graphify drift [{drift.kind}] {drift.detail}\n")
    if not drifts:
        sys.stdout.write("graphify currency current\n")
    return 1 if drifts else 0


def graphify_upgrade_main(project_root: Path) -> int:
    """Update currency, then rebuild the graph; stop at the first failure."""
    update_rc = graphify_update_main(project_root)
    if update_rc != 0:
        return update_rc
    graphify = importlib.import_module("dotfiles_setup.graphify")
    return graphify.graphify_rebuild_main(project_root)
