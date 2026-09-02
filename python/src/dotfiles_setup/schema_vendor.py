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

import hashlib
import logging
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotfiles_setup import _project_root

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

#: Where the vendored-schema manifest lives, relative to the project root.
SOURCES_PATH = "schemas/sources.toml"

#: Network fetch timeout for `refresh` — CI-only, never on the lint path.
_FETCH_TIMEOUT_S = 30.0


def _read_shared_toml_pin(tool: str, root: Path) -> str | None:
    """Read a tool's version from the shared host<->image mise fragment."""
    path = root / ".config/mise/conf.d/shared.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    value = data.get("tools", {}).get(tool)
    if isinstance(value, dict):
        version = value.get("version")
        return version if isinstance(version, str) else None
    return value if isinstance(value, str) else None


def _read_uv_lock_pin(package: str, root: Path) -> str | None:
    """Read a package's resolved version out of the committed uv lockfile.

    ``ruff`` itself is an unpinned dependency in ``python/pyproject.toml``
    (``uv lock --upgrade-package ruff`` resolves latest on demand); the lock
    file is the only local record of the version actually in use.
    """
    path = root / "python/uv.lock"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    for entry in data.get("package", []):
        if entry.get("name") == package:
            version = entry.get("version")
            return version if isinstance(version, str) else None
    return None


#: Matches `version: "2026.9.0"` inside the pinned-`mise-action` step of
#: setup-mise/action.yml. Narrow (a quoted `version:` key) rather than a
#: bare digit scan. The file carries TWO `jdx/mise-action` steps (a warm-path
#: and a cold-path call) that both pin the same version today, so the
#: first-match regex is correct by agreement, not because there is only one
#: `version:` key — a future divergence between the two steps would need
#: this regex anchored to a specific step, not just a comment fix.
_SETUP_MISE_VERSION_RE = re.compile(r'^\s*version:\s*"([^"]+)"\s*$', re.MULTILINE)


def _read_setup_mise_pin(root: Path) -> str | None:
    """Read the mise version pinned for CI/the image (``jdx/mise-action``)."""
    path = root / ".github/actions/setup-mise/action.yml"
    match = _SETUP_MISE_VERSION_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


#: One resolver per vendored tool. A tool absent here is unresolvable, and
#: :func:`check_drift` reports that explicitly rather than treating it as
#: clean (`.claude/rules/probes-need-a-control-arm.md` rule 4 — a lookup that
#: cannot answer is not a "no"). Each resolver takes the project root so a
#: caller can point `current_pin` at a fixture tree instead of the live repo.
_PIN_RESOLVERS: dict[str, Any] = {
    "typos": lambda root: _read_shared_toml_pin("typos", root),
    "ruff": lambda root: _read_uv_lock_pin("ruff", root),
    "mise": _read_setup_mise_pin,
}


def current_pin(tool: str, root: Path | None = None) -> str | None:
    """Return the tool's current pinned version, or ``None`` if unresolvable."""
    resolver = _PIN_RESOLVERS.get(tool)
    if resolver is None:
        return None
    project_root = root if root is not None else _project_root()
    return resolver(project_root)


@dataclass(frozen=True)
class SchemaEntry:
    """One row of ``schemas/sources.toml``."""

    tool: str
    file: str
    version: str
    source: str
    pin_source: str
    sha256: str


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
            sha256=row["sha256"],
        )
        for row in data.get("schema", [])
    ]


def _file_sha256(path: Path) -> str | None:
    """Hash a vendored schema's bytes, or ``None`` if it does not exist.

    Purely local — the whole offline-drift design rests on this needing no
    network call, unlike opening the file at all as JSON, which would.
    """
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_drift(root: Path | None = None) -> list[str]:
    """Return one human-readable finding per drifted or unresolvable entry.

    Checks TWO independent things per entry: the recorded ``version``
    against the tool's current pin, and the recorded ``sha256`` against the
    vendored file's actual bytes on disk. The version check alone cannot see
    a vendored file that was truncated, corrupted, or replaced with an
    unrelated (even validly-parsing) JSON document while ``sources.toml``
    kept its old, now-untrue, version string — the hash is what actually
    verifies the bytes taplo will load. Empty list means every vendored
    schema is both version-current and byte-identical to what was recorded.
    Makes NO network call — every fact compared is already on disk.
    """
    findings: list[str] = []
    project_root = root if root is not None else _project_root()
    for entry in load_sources(project_root):
        pin = current_pin(entry.tool, project_root)
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
        actual_sha = _file_sha256(project_root / entry.file)
        if actual_sha != entry.sha256:
            findings.append(
                f"{entry.tool}: {entry.file} bytes do not match the recorded "
                f"sha256 in schemas/sources.toml (expected {entry.sha256}, "
                f"got {actual_sha!r}) — the vendored file was edited or "
                f"corrupted outside `mise run schema-vendor-refresh`"
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
        "# Vendored-schema provenance (ITEM 11). Read by\n"
        "# `dotfiles_setup.schema_vendor` — both the offline drift check (wired into\n"
        "# `mise run verify`) and the network-using `schema-vendor refresh` command\n"
        "# that `refresh.yml`'s `schema-refresh` job runs in CI. Never hand-edit the\n"
        "# `version`/`source`/`sha256` fields; run\n"
        "# `mise run schema-vendor-refresh` and let it rewrite this file alongside\n"
        "# the vendored JSON.\n"
        "#\n"
        "# `pin_source` names where `schema_vendor.current_pin()` reads the tool's\n"
        "# CURRENT version from — informational here, the resolver itself is code.\n"
        "# `sha256` is the vendored file's own hash, verified offline by\n"
        "# `check_drift` — it is what actually proves the bytes on disk are what was\n"
        "# fetched, since the version string alone cannot detect a hand-edited or\n"
        "# corrupted file.\n"
    )
    blocks = [
        "[[schema]]\n"
        f'tool = "{e.tool}"\n'
        f'file = "{e.file}"\n'
        f'version = "{e.version}"\n'
        f'source = "{e.source}"\n'
        f'pin_source = "{e.pin_source}"\n'
        f'sha256 = "{e.sha256}"\n'
        for e in entries
    ]
    return header + "\n" + "\n".join(blocks)


#: The hk hygiene builtins (``hk-common.pkl`` ``hygiene`` group) that can
#: rewrite a vendored JSON file, as their ``hk util`` subcommand names. The
#: vendored bytes are put through these BEFORE being hashed, so the file on
#: disk is already a fixed point of the lint gate.
#:
#: Why this exists: ruff's and typos' upstream schemas ship with NO trailing
#: newline (measured — ruff 0.16.5 ends ``}\n}``, while mise's ends ``\n}\n``).
#: Writing those bytes verbatim and hashing them made ``end-of-file-fixer``
#: and the ``sha256`` integrity check mutually exclusive: fixing the newline
#: broke `check_drift`, and leaving it broke `mise run lint`. Normalising
#: first makes both gates agree, and keeps `check_drift` running over EVERY
#: vendored file rather than exempting these two from the lint gate.
#: Each entry is the ``hk util`` subcommand plus the args that make it WRITE.
#: The vocabulary is NOT uniform, and assuming it is costs a silent rc=2:
#: three fixers write only under ``--fix``, while ``fix-smart-quotes`` writes
#: BY DEFAULT and takes ``--check`` to do the opposite. Verified against each
#: subcommand's own ``--help``, not inferred from a sibling.
_HK_HYGIENE_FIXERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("trailing-whitespace", ("--fix",)),
    ("end-of-file-fixer", ("--fix",)),
    ("mixed-line-ending", ("--fix",)),
    ("fix-smart-quotes", ()),
)


def _hygiene_normalize(data: bytes, root: Path) -> bytes:
    """Return `data` as hk's hygiene builtins would leave it on disk.

    Runs the real fixers (:data:`_HK_HYGIENE_FIXERS`) over a scratch copy
    rather than reimplementing their rules in Python, so this cannot drift
    from what ``mise run lint`` enforces (`use-tool-builtins.md`). The file
    is written, fixed in place, and read back.

    Raises:
        RuntimeError: when an ``hk util`` fixer exits non-zero for a reason
            other than "I fixed something" (rc 1), which would otherwise let
            an unnormalised file through and re-break the lint gate.
    """
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "schema.json"
        scratch.write_bytes(data)
        for fixer, write_args in _HK_HYGIENE_FIXERS:
            proc = subprocess.run(
                ["hk", "util", fixer, *write_args, str(scratch)],
                capture_output=True,
                check=False,
                cwd=root,
            )
            # hk's fixers exit 1 when they CHANGED the file, which is the
            # expected outcome here, not a failure. Anything else (missing
            # binary, bad flag) must be loud — a silently skipped fixer
            # reintroduces exactly the deadlock this function removes.
            if proc.returncode not in (0, 1):
                stderr = proc.stderr.decode(errors="replace").strip()
                msg = (
                    f"hk util {fixer} failed (rc={proc.returncode}) "
                    f"normalizing a vendored schema: {stderr}"
                )
                raise RuntimeError(msg)
        return scratch.read_bytes()


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
    the pin moved or the fetched bytes differ from what's on disk. Fetched
    bytes are put through :func:`_hygiene_normalize` FIRST, so the recorded
    ``sha256`` describes the file as the lint gate leaves it — comparison,
    write and hash all use the same normalized form, which keeps the
    "nothing drifted" fast path honest. Returns
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
        pin = current_pin(entry.tool, project_root)
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
        fetched = _hygiene_normalize(fetch(url), project_root)
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
                    sha256=hashlib.sha256(fetched).hexdigest(),
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
