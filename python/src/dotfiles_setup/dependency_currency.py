# Copyright (c) 2026 Raymond Manaloto
"""Dependency currency: are this project's FIRST-LEVEL pins up to date?

Two surfaces, both read as structured JSON and both judged by the child's exit
code — never by parsing human output:

- ``mise outdated -b --local -J`` for tool pins (``mise.toml`` and the merged
  ``.config/mise/conf.d/*.toml``).
- ``uv pip list --outdated --format json`` for Python pins.

**First-level only, deliberately.** A transitive package being behind is the
resolver's business, not a pin this repo controls: the project venv reports 47
outdated distributions while only a handful are declared in ``pyproject.toml``.
Reporting the transitive set would be noise nobody can act on, and a doctor that
cries wolf is one nobody reads (the reasoning ``doctor.toml``'s ``[listing]``
section already applies to its own ceiling).

⚠️ **``uv tree --outdated --format json`` cannot be used, measured 2026-09-13.**
The flag is silently ignored under ``--format json``: every one of the 144
resolution entries carries only ``dependencies``/``kind``/``name``/``source``/
``version``/``wheels`` — no ``latest``, no ``outdated``. The TEXT form does
carry it (``graphifyy[all] v0.9.53 (latest: v0.9.61)``), so the only way to use
that command would be to scrape human output, which is exactly what this module
exists to avoid. ``uv pip list --outdated --format json`` returns
``{name, version, latest_version, latest_filetype}`` and is used instead.

⚠️ **Point ``uv pip list`` at the project interpreter explicitly.** Without
``--python``, it resolved the *system* CPython and reported a single outdated
package (``pip``) — a confidently wrong "almost current" answer. The control
that caught it: the project venv reports 47.
"""

from __future__ import annotations

import enum
import json
import logging
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

#: Each probe spawns a network-touching resolver, so both are bounded.
PROBE_TIMEOUT = 180

#: Cap on any diagnostic copied into a report rendered into session context.
_DIAGNOSTIC_MAX_CHARS = 500


class CurrencyCode(enum.IntEnum):
    """Exit code and classification. Returned as the process exit code."""

    OK = 0
    OUTDATED = 1  # a first-level pin is behind — the actionable state
    PROBE_UNAVAILABLE = 2  # `mise` or `uv` not executable
    PROBE_FAILED = 3  # ran, non-zero rc
    MALFORMED_PAYLOAD = 4  # rc 0, undecodable or wrong shape
    MANIFEST_INVALID = 5  # pyproject.toml unreadable / ill-typed


@dataclass(frozen=True, kw_only=True)
class OutdatedPin:
    """One first-level pin that is behind, named without any local path."""

    name: str
    current: str
    latest: str
    surface: str  # "mise" or "python"


@dataclass(kw_only=True)
class CurrencyReport:
    """Observable facts only. Never a recommendation to bump."""

    code: int
    outdated: list[OutdatedPin] = field(default_factory=list)
    diagnostic: str | None = None


def _truncate(text: str) -> str:
    """A bounded single-line diagnostic. Display only; never branched on."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= _DIAGNOSTIC_MAX_CHARS:
        return collapsed
    return collapsed[: _DIAGNOSTIC_MAX_CHARS - 1] + "…"


def _run_json(
    argv: list[str], cwd: Path | None, timeout: int = PROBE_TIMEOUT
) -> tuple[CurrencyCode, object, str]:
    """Run ``argv`` and decode its stdout as JSON.

    The rc IS the contract: a non-zero exit is ``PROBE_FAILED`` regardless of
    what the child printed, and stderr is captured for display only.
    """
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return CurrencyCode.PROBE_UNAVAILABLE, None, f"{argv[0]} is not on PATH"
    except subprocess.TimeoutExpired:
        return CurrencyCode.PROBE_UNAVAILABLE, None, f"{argv[0]} timed out"
    except (OSError, subprocess.SubprocessError) as exc:
        return CurrencyCode.PROBE_UNAVAILABLE, None, _truncate(str(exc))

    if result.returncode != 0:
        return CurrencyCode.PROBE_FAILED, None, _truncate(result.stderr)

    try:
        return CurrencyCode.OK, json.loads(result.stdout), ""
    except ValueError as exc:
        return CurrencyCode.MALFORMED_PAYLOAD, None, _truncate(str(exc))


def declared_python_names(project_root: Path) -> set[str]:
    """Distribution names this repo declares directly in ``pyproject.toml``.

    Extras and version specifiers are stripped, and the name is normalised the
    way PyPI does (``_`` and ``.`` fold to ``-``, case-insensitively) so
    ``python-debian`` matches a reported ``python_debian``.
    """
    manifest = project_root / "python" / "pyproject.toml"
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        logger.debug("dependency_currency: unreadable manifest: %s", exc)
        return set()

    raw: list[str] = []
    project = data.get("project")
    if isinstance(project, dict):
        deps = project.get("dependencies")
        if isinstance(deps, list):
            raw.extend(d for d in deps if isinstance(d, str))
    groups = data.get("dependency-groups")
    if isinstance(groups, dict):
        for members in groups.values():
            if isinstance(members, list):
                raw.extend(d for d in members if isinstance(d, str))
    return {_normalise(_bare_name(spec)) for spec in raw if _bare_name(spec)}


def _bare_name(spec: str) -> str:
    """``graphifyy[all]==0.9.53`` -> ``graphifyy``; a URL spec -> its name."""
    head = spec.split("@", 1)[0].strip()
    for sep in ("[", "=", ">", "<", "!", "~", ";", " "):
        head = head.split(sep, 1)[0]
    return head.strip()


def _normalise(name: str) -> str:
    """PyPI name normalisation, so `_`/`.` variants compare equal."""
    return name.lower().replace("_", "-").replace(".", "-")


def python_outdated(project_root: Path) -> tuple[CurrencyCode, list[OutdatedPin], str]:
    """First-level Python pins that are behind."""
    venv_python = project_root / "python" / ".venv" / "bin" / "python"
    code, payload, diagnostic = _run_json(
        [
            "uv",
            "pip",
            "list",
            "--outdated",
            "--format",
            "json",
            "--python",
            str(venv_python),
        ],
        cwd=project_root,
    )
    if code is not CurrencyCode.OK:
        return code, [], diagnostic
    if not isinstance(payload, list):
        return CurrencyCode.MALFORMED_PAYLOAD, [], "expected a JSON array"

    declared = declared_python_names(project_root)
    pins: list[OutdatedPin] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or _normalise(name) not in declared:
            continue
        pins.append(
            OutdatedPin(
                name=name,
                current=str(entry.get("version", "")),
                latest=str(entry.get("latest_version", "")),
                surface="python",
            )
        )
    return CurrencyCode.OK, sorted(pins, key=lambda p: p.name), ""


def mise_outdated(project_root: Path) -> tuple[CurrencyCode, list[OutdatedPin], str]:
    """First-level tool pins that are behind.

    ``--local`` already scopes the answer to configs this project declares, so
    every returned row is first-level by construction.
    """
    code, payload, diagnostic = _run_json(
        ["mise", "outdated", "-b", "--local", "-J"], cwd=project_root
    )
    if code is not CurrencyCode.OK:
        return code, [], diagnostic

    # The payload is an object keyed by tool name; tolerate a list too, since a
    # shape change here must not read as "everything is current".
    if isinstance(payload, dict):
        rows = list(payload.values())
    elif isinstance(payload, list):
        rows = payload
    else:
        return CurrencyCode.MALFORMED_PAYLOAD, [], "expected a JSON object or array"

    pins: list[OutdatedPin] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        latest = row.get("latest") or row.get("bump")
        current = row.get("current") or row.get("requested")
        if isinstance(name, str) and latest and current and latest != current:
            pins.append(
                OutdatedPin(
                    name=name,
                    current=str(current),
                    latest=str(latest),
                    surface="mise",
                )
            )
    return CurrencyCode.OK, sorted(pins, key=lambda p: p.name), ""


def evaluate(project_root: Path) -> CurrencyReport:
    """Both surfaces, merged. A failed probe never reads as 'current'."""
    worst = CurrencyCode.OK
    pins: list[OutdatedPin] = []
    notes: list[str] = []
    for probe in (mise_outdated, python_outdated):
        code, found, diagnostic = probe(project_root)
        if code is not CurrencyCode.OK:
            worst = code
            if diagnostic:
                notes.append(f"{probe.__name__}: {diagnostic}")
            continue
        pins.extend(found)

    if worst is not CurrencyCode.OK:
        return CurrencyReport(
            code=worst, outdated=pins, diagnostic="; ".join(notes) or None
        )
    return CurrencyReport(
        code=CurrencyCode.OUTDATED if pins else CurrencyCode.OK, outdated=pins
    )


def check_dependency_currency(setup: object) -> list[str]:
    """Doctor LIVE check: first-level pins that are behind.

    LIVE because both probes spawn a network-touching resolver — the same reason
    ``mcp-health`` and ``plugin-health`` live there rather than in ``CHECKS``.
    """
    project_root = getattr(setup, "repo_root", None)
    if project_root is None:
        return ["dependency-currency: no repo root on the setup object"]

    report = evaluate(project_root)
    if report.code is CurrencyCode.OK:
        return []
    if report.code is not CurrencyCode.OUTDATED:
        return [
            f"dependency-currency: could not establish currency "
            f"({CurrencyCode(report.code).name}) — this is NOT 'everything is "
            f"current'. {report.diagnostic or ''}".strip()
        ]

    by_surface: dict[str, list[str]] = {}
    for pin in report.outdated:
        by_surface.setdefault(pin.surface, []).append(
            f"{pin.name} {pin.current} -> {pin.latest}"
        )
    return [
        f"dependency-currency: {surface} pins behind: {', '.join(items)}"
        for surface, items in sorted(by_surface.items())
    ]


def dependency_currency_main(*, project_root: Path | None = None) -> int:
    """Print the report as JSON; return the code as the process exit code."""
    root = project_root or Path.cwd()
    report = evaluate(root)
    payload = {
        "code": int(report.code),
        "outdated": [
            {
                "name": p.name,
                "current": p.current,
                "latest": p.latest,
                "surface": p.surface,
            }
            for p in report.outdated
        ],
    }
    if report.diagnostic:
        payload["diagnostic"] = report.diagnostic
    sys.stdout.write(json.dumps(payload) + "\n")
    return int(report.code)
