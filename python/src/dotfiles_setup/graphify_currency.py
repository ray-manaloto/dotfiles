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
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from dotfiles_setup import graphify_skill
from dotfiles_setup.path_drift import Provenance, resolve_ambient_path

DIST = "graphifyy"
MISE_TOOL = "pipx:graphifyy"
GITHUB_REPO = "Graphify-Labs/graphify"
RECEIPT_DIR = Path("docs/receipts/graphify")

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
class ReleaseNote:
    """One upstream release and the metadata preserved in its receipt."""

    version: str
    tag: str
    published_at: str
    body: str


@dataclass(frozen=True)
class _Probe:
    value: str | None
    error: str = ""
    path: str | None = None
    provenance_note: str = ""


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


def _require_latest(*, run: Run) -> str:
    """Return the latest version or fail closed with the probe diagnostic."""
    probe = _latest_probe(run=run)
    if probe.value is None:
        message = f"latest UNVERIFIABLE: {probe.error}"
        raise GraphifyCurrencyError(message)
    return probe.value


def _path_binary_probe(
    *,
    run: Run,
    environ: Mapping[str, str] | None = None,
) -> _Probe:
    resolved_environ = os.environ if environ is None else environ
    ambient_path, provenance = resolve_ambient_path(resolved_environ)
    if provenance is Provenance.BLIND:
        provenance_note = "mise-resolved PATH; stale-activation blind"
        path_label = "mise-resolved PATH"
    else:
        provenance_note = "ambient PATH"
        path_label = "ambient PATH"
    # ``uv run`` prepends its project venv after the agent shell has already
    # resolved its ambient PATH.  That injected entry is never the host binary
    # this axis measures, even when no mise marker is present to make the
    # inherited fallback BLIND.
    venv_bins = {str(Path(sys.executable).parent)}
    if virtual_env := resolved_environ.get("VIRTUAL_ENV"):
        venv_bins.add(str(Path(virtual_env) / "bin"))
    ambient_path = os.pathsep.join(
        entry for entry in ambient_path.split(os.pathsep) if entry not in venv_bins
    )
    binary = shutil.which("graphify", path=ambient_path)
    if binary is None:
        return _Probe(
            None,
            f"path-binary UNVERIFIABLE (graphify absent from {path_label})",
            provenance_note=provenance_note,
        )
    try:
        result = run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_PATH_TIMEOUT_SECONDS,
            env={"PATH": ambient_path},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _Probe(
            None,
            f"path-binary UNVERIFIABLE ({exc})",
            path=binary,
            provenance_note=provenance_note,
        )
    output = f"{result.stdout}\n{result.stderr}"
    match = _VERSION_RE.search(output)
    error = ""
    if result.returncode != 0:
        detail = result.stderr.strip() or (
            f"graphify --version exited {result.returncode}"
        )
        error = detail
    elif match is None:
        error = "graphify --version returned no usable version"
    else:
        try:
            Version(match.group(1))
        except InvalidVersion:
            error = f"graphify --version returned {match.group(1)!r}"
    if error:
        return _Probe(
            None,
            f"path-binary UNVERIFIABLE ({error})",
            path=binary,
            provenance_note=provenance_note,
        )
    if match is None:
        return _Probe(
            None,
            "path-binary UNVERIFIABLE (graphify --version returned no usable version)",
            path=binary,
            provenance_note=provenance_note,
        )
    return _Probe(
        match.group(1),
        path=binary,
        provenance_note=provenance_note,
    )


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
) -> list[ReleaseNote]:
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

    notes: list[tuple[Version, ReleaseNote]] = []
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
            published_at = row.get("published_at")
            if not isinstance(published_at, str) or not published_at:
                message = f"gh api release {tag} has no published_at"
                raise GraphifyCurrencyError(message)
            notes.append(
                (
                    release_version,
                    ReleaseNote(
                        version=str(release_version),
                        tag=tag,
                        published_at=published_at,
                        body=body if isinstance(body, str) else "",
                    ),
                )
            )
    notes.sort(key=lambda item: item[0])
    if not any(version == high_version for version, _ in notes):
        message = f"gh api returned no release for target version {high}"
        raise GraphifyCurrencyError(message)
    return [note for _, note in notes]


def write_release_receipts(
    project_root: Path,
    notes: list[ReleaseNote],
) -> tuple[Path, ...]:
    """Write one tracked, verbatim upstream release receipt per version."""
    receipt_dir = project_root / RECEIPT_DIR
    receipt_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for note in notes:
        receipt = receipt_dir / f"{note.version}.md"
        header = (
            f"# Graphify {note.tag} release receipt\n\n"
            "Written by `mise run graphify-update`.\n\n"
            f"- Tag: `{note.tag}`\n"
            f"- Published at: `{note.published_at}`\n\n"
            "## Release notes (verbatim)\n\n"
        )
        receipt.write_text(f"{header}{note.body}\n", encoding="utf-8")
        written.append(receipt)
    return tuple(written)


def upgrade_lock(project_root: Path, run: Run = subprocess.run) -> None:
    """Upgrade the Graphify lock entry with native uv, then sync the project."""

    def _run_checked(command: list[str]) -> None:
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

    _run_checked(["uv", "lock", "--project", "python", "--upgrade-package", DIST])
    _run_checked(["uv", "sync", "--project", "python"])


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


def _receipt_drift(project_root: Path, locked: str) -> Drift | None:
    receipt = project_root / RECEIPT_DIR / f"{locked}.md"
    if receipt.is_file():
        return None
    relative = receipt.relative_to(project_root)
    return Drift(
        "receipt-missing",
        f"receipt-missing: {relative} — run mise run graphify-update",
    )


def _check_with_versions(
    project_root: Path,
    *,
    offline: bool,
) -> tuple[Versions, tuple[Drift, ...], _Probe]:
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

    latest_probe = _Probe(None)
    if not offline:
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

    if locked != "UNVERIFIABLE" and (
        receipt_drift := _receipt_drift(project_root, locked)
    ):
        drifts.append(receipt_drift)

    drifts.extend(_skill_drifts(project_root))

    path_probe = _path_binary_probe(run=subprocess.run)
    if path_probe.value is None:
        drifts.append(Drift("path-binary", path_probe.error))
    elif path_probe.value is not None and locked not in (
        "UNVERIFIABLE",
        path_probe.value,
    ):
        drifts.append(
            Drift(
                "path-binary",
                f"path-binary {path_probe.path} reports {path_probe.value} != "
                f"locked {locked} — update the user-global mise pin",
            )
        )

    versions = Versions(
        locked=locked,
        installed=installed,
        latest=latest_probe.value,
        path_binary=path_probe.value,
    )
    return versions, tuple(drifts), path_probe


def check(project_root: Path, *, offline: bool = False) -> tuple[Drift, ...]:
    """Return every read-only Graphify currency and skill-surface drift."""
    return _check_with_versions(project_root, offline=offline)[1]


def _run(command: list[str], *, project_root: Path) -> None:
    """Run one post-sync CLI action in a fresh uv interpreter."""
    try:
        result = subprocess.run(
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
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode != 0:
        message = f"{' '.join(command)} exited {result.returncode}"
        raise GraphifyCurrencyError(message)


def _refresh_and_check_fresh(project_root: Path) -> None:
    _run(
        [
            "uv",
            "run",
            "--project",
            "python",
            "dotfiles-setup",
            "graphify",
            "refresh-skills",
        ],
        project_root=project_root,
    )
    _run(
        [
            "uv",
            "run",
            "--project",
            "python",
            "dotfiles-setup",
            "graphify",
            "check",
            "--offline",
        ],
        project_root=project_root,
    )


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
            receipts = write_release_receipts(project_root, notes)
            for receipt in receipts:
                sys.stdout.write(f"release notes -> {receipt}\n")
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

        _refresh_and_check_fresh(project_root)
    except (GraphifyCurrencyError, InvalidVersion) as exc:
        sys.stderr.write(f"graphify update failed: {exc}\n")
        return 1
    return 0


def graphify_check_main(project_root: Path, *, offline: bool = False) -> int:
    """Print Graphify currency drift and return nonzero when any exists."""
    versions, drifts, path_probe = _check_with_versions(
        project_root,
        offline=offline,
    )
    latest = (
        "SKIPPED (offline)"
        if offline
        else versions.latest
        if versions.latest is not None
        else "UNVERIFIABLE"
    )
    sys.stdout.write(f"graphifyy locked {versions.locked}, latest {latest}\n")
    path_version = versions.path_binary or "UNVERIFIABLE"
    sys.stdout.write(
        f"graphify path-binary: {path_probe.path or 'UNVERIFIABLE'} "
        f"(version={path_version}; {path_probe.provenance_note})\n"
    )
    for drift in drifts:
        sys.stdout.write(f"graphify drift [{drift.kind}] {drift.detail}\n")
    if not drifts:
        sys.stdout.write("graphify currency current\n")
    if not offline:
        graphify = importlib.import_module("dotfiles_setup.graphify")
        health = graphify.graphify_health(project_root)
        sys.stdout.write(
            f"graphify-health: {health.status} "
            f"(runtime={health.runtime_version}) {health.detail}\n"
        )
    return 1 if drifts else 0


def graphify_upgrade_main(project_root: Path) -> int:
    """Update currency, then rebuild the graph; stop at the first failure."""
    update_rc = graphify_update_main(project_root)
    if update_rc != 0:
        return update_rc
    graphify = importlib.import_module("dotfiles_setup.graphify")
    return graphify.graphify_rebuild_main(project_root)
