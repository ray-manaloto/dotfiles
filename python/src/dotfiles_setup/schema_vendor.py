# Copyright (c) 2026 Raymond Manaloto
"""Offline drift check + refresh for the vendored config schemas (ITEM 11).

``mise.toml``, ``ruff.toml`` and ``typos.toml`` each carry a first-line
``#:schema ./schemas/<tool>.json`` directive (taplo, wired via hk's ``taplo``
builtin, ``hk.pkl:167``). The referenced files are vendored under
``schemas/`` rather than pointed at a remote URL, because taplo does NOT
cache schemas between runs — measured: a second ``taplo lint`` with the
network blocked still returns rc=1 "failed to fetch schema". A remote
``#:schema`` would make ``mise run lint`` a per-run network dependency and a
red gate whenever the schema host is unreachable.

``schemas/sources.toml`` records, per vendored file, the tool, the version it
was fetched at, the exact source URL, and where this module reads that tool's
CURRENT pin from (``pin_source`` — informational; :data:`_PIN_RESOLVERS` is
the code). Two entry points:

* :func:`check_drift` — OFFLINE. Compares the recorded version in
  ``sources.toml`` against the tool's current pin, read from the same three
  local files the pin actually lives in (:mod:`tomllib` on
  ``.config/mise/conf.d/shared.toml`` for ``typos``, :mod:`tomllib` on
  ``python/uv.lock`` for ``ruff`` — the only local record of its resolved
  version, since ``ruff`` itself floats unpinned in ``python/pyproject.toml``
  — and a regex on ``.github/actions/setup-mise/action.yml`` for ``mise``).
  No network call; two local facts compared. Wired into ``mise run verify``
  via the ``schema_drift`` handler in :mod:`dotfiles_setup.verify`.
* :func:`refresh` — re-downloads every vendored schema at the CURRENT pin and
  rewrites the JSON file + its ``sources.toml`` record when the version or
  bytes changed. Network-using; the ``schema-refresh`` job in
  ``.github/workflows/refresh.yml`` runs it in CI, mirroring
  ``lock-refresh``/``image-lock-pr`` in the same workflow, never the lint
  gate.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from dotfiles_setup import _project_root

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = logging.getLogger(__name__)

#: Where the vendored-schema manifest lives, relative to the project root.
SOURCES_PATH = "schemas/sources.toml"

#: Network fetch timeout for `refresh` — CI-only, never on the lint path.
_FETCH_TIMEOUT_S = 30.0


def _read_shared_toml_pin(tool: str) -> str | None:
    """Read a tool's version from the shared host<->image mise fragment."""
    path = _project_root() / ".config/mise/conf.d/shared.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    value = data.get("tools", {}).get(tool)
    if isinstance(value, dict):
        version = value.get("version")
        return version if isinstance(version, str) else None
    return value if isinstance(value, str) else None


def _read_uv_lock_pin(package: str) -> str | None:
    """Read a package's resolved version out of the committed uv lockfile.

    ``ruff`` itself is an unpinned dependency in ``python/pyproject.toml``
    (``uv lock --upgrade-package ruff`` resolves latest on demand); the lock
    file is the only local record of the version actually in use.
    """
    path = _project_root() / "python/uv.lock"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    for entry in data.get("package", []):
        if entry.get("name") == package:
            version = entry.get("version")
            return version if isinstance(version, str) else None
    return None


#: Matches `version: "2026.9.0"` inside the pinned-`mise-action` step of
#: setup-mise/action.yml. Narrow (a quoted `version:` key) rather than a
#: bare digit scan, so an unrelated `version:` elsewhere in the file (there
#: is exactly one today) would be caught by the module's own tests, not
#: silently matched.
_SETUP_MISE_VERSION_RE = re.compile(r'^\s*version:\s*"([^"]+)"\s*$', re.MULTILINE)


def _read_setup_mise_pin() -> str | None:
    """Read the mise version pinned for CI/the image (``jdx/mise-action``)."""
    path = _project_root() / ".github/actions/setup-mise/action.yml"
    match = _SETUP_MISE_VERSION_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


#: One resolver per vendored tool. A tool absent here is unresolvable, and
#: :func:`check_drift` reports that explicitly rather than treating it as
#: clean (`.claude/rules/probes-need-a-control-arm.md` rule 4 — a lookup that
#: cannot answer is not a "no").
_PIN_RESOLVERS: dict[str, Any] = {
    "typos": lambda: _read_shared_toml_pin("typos"),
    "ruff": lambda: _read_uv_lock_pin("ruff"),
    "mise": _read_setup_mise_pin,
}


def current_pin(tool: str) -> str | None:
    """Return the tool's current pinned version, or ``None`` if unresolvable."""
    resolver = _PIN_RESOLVERS.get(tool)
    return resolver() if resolver is not None else None


@dataclass(frozen=True)
class SchemaEntry:
    """One row of ``schemas/sources.toml``."""

    tool: str
    file: str
    version: str
    source: str
    pin_source: str


def load_sources(root: Path | None = None) -> list[SchemaEntry]:
    """Parse ``schemas/sources.toml`` into :class:`SchemaEntry` rows."""
    project_root = root if root is not None else _project_root()
    path = project_root / SOURCES_PATH
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [
        SchemaEntry(
            tool=row["tool"],
            file=row["file"],
            version=row["version"],
            source=row["source"],
            pin_source=row["pin_source"],
        )
        for row in data.get("schema", [])
    ]


def check_drift(root: Path | None = None) -> list[str]:
    """Return one human-readable finding per drifted or unresolvable entry.

    Empty list means every vendored schema's recorded version matches the
    tool's current pin. Makes NO network call — every fact compared is
    already on disk.
    """
    findings: list[str] = []
    for entry in load_sources(root):
        pin = current_pin(entry.tool)
        if pin is None:
            findings.append(
                f"{entry.tool}: could not resolve the current pin from "
                f"{entry.pin_source} — schema_vendor._PIN_RESOLVERS may need "
                f"a new entry"
            )
        elif pin != entry.version:
            findings.append(
                f"{entry.tool}: {entry.file} is vendored at {entry.version}, "
                f"but the current pin ({entry.pin_source}) is {pin} — run "
                f"`mise run schema-vendor-refresh`"
            )
    return findings


def _source_url(tool: str, version: str) -> str:
    """Build the tagged raw-GitHub URL a fresh vendor of `tool` fetches from."""
    if tool == "mise":
        return f"https://raw.githubusercontent.com/jdx/mise/v{version}/schema/mise.json"
    if tool == "ruff":
        return f"https://raw.githubusercontent.com/astral-sh/ruff/{version}/ruff.schema.json"
    if tool == "typos":
        return f"https://raw.githubusercontent.com/crate-ci/typos/v{version}/config.schema.json"
    msg = f"schema_vendor: no source-URL template for tool {tool!r}"
    raise ValueError(msg)


def _render_sources_toml(entries: list[SchemaEntry]) -> str:
    """Re-render ``schemas/sources.toml`` in its authored shape."""
    header = (
        "# Vendored-schema provenance (#160, ITEM 11). Read by\n"
        "# `dotfiles_setup.schema_vendor` — both the offline drift check (wired into\n"
        "# `mise run verify`) and the network-using `schema-vendor refresh` command\n"
        "# that `refresh.yml`'s `schema-refresh` job runs in CI. Never hand-edit the\n"
        "# `version`/`source` fields; run `mise run schema-vendor-refresh` and let it\n"
        "# rewrite this file alongside the vendored JSON.\n"
        "#\n"
        "# `pin_source` names where `schema_vendor.current_pin()` reads the tool's\n"
        "# CURRENT version from — informational here, the resolver itself is code.\n"
    )
    blocks = [
        "[[schema]]\n"
        f'tool = "{e.tool}"\n'
        f'file = "{e.file}"\n'
        f'version = "{e.version}"\n'
        f'source = "{e.source}"\n'
        f'pin_source = "{e.pin_source}"\n'
        for e in entries
    ]
    return header + "\n" + "\n".join(blocks)


def _curl_fetch(url: str) -> bytes:
    """Fetch `url` with curl and return the raw body.

    Subprocess is this repo's blessed fetch mechanism (see
    `gcc_sha._default_fetcher`, `p2996_refresh`'s git ls-remote) — no HTTP
    client dependency is introduced. `-f` makes an HTTP error status a
    non-zero curl exit rather than a "successful" fetch of an error page.

    Raises:
        RuntimeError: when curl exits non-zero.
    """
    # url is one of the three raw.githubusercontent.com templates built by
    # _source_url, never external input.
    proc = subprocess.run(
        ["curl", "-fsSL", "--connect-timeout", str(int(_FETCH_TIMEOUT_S)), url],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors="replace").strip()
        msg = f"curl failed (rc={proc.returncode}) fetching {url}: {stderr}"
        raise RuntimeError(msg)
    return proc.stdout


def refresh(
    root: Path | None = None,
    *,
    fetcher: Callable[[str], bytes] | None = None,
) -> list[str]:
    """Re-download every vendored schema at its current pin.

    Rewrites a vendored JSON file (and its ``sources.toml`` row) only when
    the pin moved or the fetched bytes differ from what's on disk. Returns
    the list of tools that changed. Network-using — CI (`schema-refresh`
    job) only, never the lint gate. `fetcher` is a test seam: a callable
    `(url) -> bytes`, defaulting to :func:`_curl_fetch`.
    """
    project_root = root if root is not None else _project_root()
    fetch = fetcher if fetcher is not None else _curl_fetch
    entries = load_sources(project_root)
    changed: list[str] = []
    new_entries: list[SchemaEntry] = []
    for entry in entries:
        pin = current_pin(entry.tool)
        if pin is None:
            logger.error(
                "schema_vendor refresh: cannot resolve current pin for %s "
                "(%s) — leaving vendored",
                entry.tool,
                entry.pin_source,
            )
            new_entries.append(entry)
            continue
        url = _source_url(entry.tool, pin)
        fetched = fetch(url)
        schema_path = project_root / entry.file
        existing = schema_path.read_bytes() if schema_path.exists() else None
        if pin != entry.version or fetched != existing:
            schema_path.write_bytes(fetched)
            new_entries.append(
                SchemaEntry(
                    tool=entry.tool,
                    file=entry.file,
                    version=pin,
                    source=url,
                    pin_source=entry.pin_source,
                )
            )
            changed.append(entry.tool)
        else:
            new_entries.append(entry)
    if changed:
        (project_root / SOURCES_PATH).write_text(
            _render_sources_toml(new_entries), encoding="utf-8"
        )
    return changed


def check_main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``dotfiles-setup schema-vendor check``."""
    del argv
    findings = check_drift()
    if findings:
        for finding in findings:
            sys.stderr.write(f"schema-vendor: {finding}\n")
        return 1
    sys.stdout.write("schema-vendor: all vendored schemas match their current pins\n")
    return 0


def refresh_main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``dotfiles-setup schema-vendor refresh``."""
    del argv
    changed = refresh()
    if changed:
        sys.stdout.write(f"schema-vendor: refreshed {', '.join(changed)}\n")
    else:
        sys.stdout.write("schema-vendor: no drift, nothing refreshed\n")
    return 0
