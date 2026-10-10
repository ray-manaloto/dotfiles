# Copyright (c) 2026 Raymond Manaloto
"""Verify mise's native npm/PyPI lock sidecars before shipping a lockfile.

``mise lock --sidecars --json`` supplies the inventory, but its ``exists``
field checks presence only. A locked install rejects a mismatched digest; this
small preflight makes the same failure visible before an image is built.
"""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

_GRAPH_FILES = {
    "uv": ("uv.lock", "pyproject.toml"),
    "aube": ("aube-lock.yaml", "package.json"),
}
NATIVE_LOCK_FORMAT = 3


@dataclass(frozen=True)
class VerifiedGraph:
    """A graph directory and the only two files approved for collection."""

    directory: Path
    files: tuple[Path, Path]


def _verify_graph(
    lock_path: Path, root: Path, tool: str, graph: str, reference: object
) -> VerifiedGraph:
    if not isinstance(reference, dict):
        msg = f"{lock_path}: malformed {graph} reference for {tool}"
        raise TypeError(msg)
    rel_path = reference.get("path")
    digest = reference.get("digest")
    if not isinstance(rel_path, str) or not isinstance(digest, str):
        msg = f"{lock_path}: incomplete {graph} reference for {tool}"
        raise TypeError(msg)
    relative = Path(rel_path)
    if relative.is_absolute() or ".." in relative.parts:
        msg = f"{lock_path}: {tool} sidecar escapes {root}: {rel_path}"
        raise ValueError(msg)
    candidate = lock_path.parent
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            msg = f"{lock_path}: {tool} sidecar contains a symlink: {candidate}"
            raise ValueError(msg)
    directory = candidate.resolve()
    if not directory.is_relative_to(root):
        msg = f"{lock_path}: {tool} sidecar escapes {root}: {rel_path}"
        raise ValueError(msg)
    native_name, manifest_name = _GRAPH_FILES[graph]
    native = directory / native_name
    manifest = directory / manifest_name
    if (
        native.is_symlink()
        or manifest.is_symlink()
        or not native.is_file()
        or not manifest.is_file()
    ):
        msg = f"{lock_path}: {tool} sidecar is incomplete at {directory}"
        raise ValueError(msg)
    actual = (
        "sha256:"
        + hashlib.sha256(native.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    )
    if actual != digest:
        msg = f"{lock_path}: {tool} sidecar digest mismatch at {native}"
        raise ValueError(msg)
    return VerifiedGraph(directory, (native, manifest))


def verify_lock_sidecars(
    lock_path: Path, sidecar_root: Path, *, require_format: int | None = None
) -> tuple[VerifiedGraph, ...]:
    """Return referenced graph directories, refusing missing or changed graphs.

    mise records a graph directory relative to its lockfile and hashes the
    native lockfile with CRLF normalized to LF. Confining each reference to
    ``sidecar_root`` also prevents a copied lock from reading host paths.
    """
    document = tomllib.loads(lock_path.read_text())
    version = document.get("lockfile_version", 0)
    if require_format is not None and version != require_format:
        msg = f"{lock_path}: expected mise lock format {require_format}, got {version}"
        raise ValueError(msg)
    root = sidecar_root.resolve()
    found: set[VerifiedGraph] = set()
    for tool, entries in document.get("tools", {}).items():
        if not isinstance(entries, list):
            msg = f"{lock_path}: malformed tool entries for {tool}"
            raise TypeError(msg)
        for entry in entries:
            if not isinstance(entry, dict):
                msg = f"{lock_path}: malformed tool entry for {tool}"
                raise TypeError(msg)
            for graph in _GRAPH_FILES:
                reference = entry.get(graph)
                if reference is None:
                    continue
                found.add(_verify_graph(lock_path, root, tool, graph, reference))
    return tuple(sorted(found, key=lambda graph: str(graph.directory)))
