# Copyright (c) 2026 Raymond Manaloto
"""Assert that every pin site for one logical tool carries the same version.

``mise outdated`` reads the manifest, so it cannot see a tool pinned somewhere
the manifest does not reach: a minimum-version floor file, a pkl ``amends``
URL, a Dockerfile ``ARG``, a vendored schema's source tag. Every drift on
2026-09-14 lived in exactly that blind spot, and one of them broke every
devcontainer bring-up on main for seven hours.

The registry is ``pin-parity.toml`` at the repository root; its header carries
the case history. This module is the thin checker over it, and the
``pin-parity`` mise task is the thin caller over this module
(``.claude/rules/mise-tasks-only.md``, ``.claude/rules/zero-bash-logic.md``).

A site whose pattern matches NOTHING is a failure, not a pass. That direction
matters more than the comparison: a silently-unmatched site turns this into a
check that can only pass, which is the shape
``.claude/rules/probes-need-a-control-arm.md`` rule 1 exists to reject.
"""

from __future__ import annotations

import logging
import re
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_NAME = "pin-parity.toml"


@dataclass(frozen=True)
class SiteReading:
    """Every version string one pattern found in one file."""

    path: str
    versions: tuple[str, ...]

    @property
    def matched(self) -> bool:
        """Whether the pattern found anything at all in this file."""
        return bool(self.versions)


@dataclass(frozen=True)
class ToolVerdict:
    """The parity outcome for one logical tool across all of its sites."""

    tool: str
    readings: tuple[SiteReading, ...]
    missing_files: tuple[str, ...]

    @property
    def unmatched(self) -> tuple[str, ...]:
        """Sites whose pattern found no version — a broken or rotted pattern."""
        return tuple(r.path for r in self.readings if not r.matched)

    @property
    def distinct(self) -> tuple[str, ...]:
        """Every distinct version any site carries, sorted."""
        seen: dict[str, None] = {}
        for reading in self.readings:
            for version in reading.versions:
                seen[version] = None
        return tuple(sorted(seen))

    @property
    def ok(self) -> bool:
        """True only when every site was readable and they all agree."""
        return not self.missing_files and not self.unmatched and len(self.distinct) == 1

    def failure_reason(self) -> str:
        """One line naming why this tool failed, or empty when it passed."""
        if self.missing_files:
            absent = ", ".join(self.missing_files)
            return f"declared site(s) absent from the tree: {absent}"
        if self.unmatched:
            rotted = ", ".join(self.unmatched)
            return (
                f"pattern matched nothing in {rotted} — the file moved, was "
                "reformatted, or the pattern rotted; a site that cannot be "
                "read is not a site that agrees"
            )
        if len(self.distinct) > 1:
            return f"pin drift across sites: {', '.join(self.distinct)}"
        return ""


def load_registry(project_root: Path) -> dict[str, object]:
    """Read ``pin-parity.toml``; raise if it is absent or unreadable."""
    with (project_root / REGISTRY_NAME).open("rb") as handle:
        return tomllib.load(handle)


def read_site(project_root: Path, path: str, pattern: str) -> SiteReading | None:
    """Collect every version this pattern finds, or ``None`` if absent."""
    target = project_root / path
    if not target.is_file():
        return None
    found = re.findall(pattern, target.read_text(encoding="utf-8"), re.MULTILINE)
    return SiteReading(path=path, versions=tuple(found))


def check_tool(
    project_root: Path, tool: str, sites: list[dict[str, str]]
) -> ToolVerdict:
    """Read every declared site for one tool and compare what they carry."""
    readings: list[SiteReading] = []
    missing: list[str] = []
    for site in sites:
        path = str(site["path"])
        reading = read_site(project_root, path, str(site["pattern"]))
        if reading is None:
            missing.append(path)
        else:
            readings.append(reading)
    return ToolVerdict(
        tool=tool, readings=tuple(readings), missing_files=tuple(missing)
    )


def _sites_of(spec: object) -> list[dict[str, str]]:
    """Narrow one registry entry's ``sites`` list out of raw TOML types."""
    if not isinstance(spec, dict):
        return []
    raw = spec.get("sites", [])
    if not isinstance(raw, list):
        return []
    return [site for site in raw if isinstance(site, dict)]


def check_all(project_root: Path) -> list[ToolVerdict]:
    """Every tool in the registry, in declaration order."""
    tools = load_registry(project_root).get("tools", {})
    if not isinstance(tools, dict):
        message = f"{REGISTRY_NAME}: [tools] must be a table"
        raise TypeError(message)
    return [
        check_tool(project_root, name, _sites_of(spec)) for name, spec in tools.items()
    ]


def format_report(verdicts: list[ToolVerdict]) -> str:
    """Human-readable result; every site and what it carries, drift first."""
    lines: list[str] = []
    for verdict in sorted(verdicts, key=lambda v: (v.ok, v.tool)):
        lines.append(f"{'OK  ' if verdict.ok else 'DRIFT'} {verdict.tool}")
        lines.extend(
            f"       {r.path}: {', '.join(r.versions) if r.matched else '(no match)'}"
            for r in verdict.readings
        )
        lines.extend(f"       {p}: (file absent)" for p in verdict.missing_files)
        if not verdict.ok:
            lines.append(f"    -> {verdict.failure_reason()}")
    return "\n".join(lines)


def pin_parity_main(project_root: Path) -> int:
    """Report every tool's pin sites; ``rc`` is the verdict (0 = all agree)."""
    verdicts = check_all(project_root)
    logger.info("%s", format_report(verdicts))
    drifted = [v for v in verdicts if not v.ok]
    if not drifted:
        logger.info("pin-parity OK: %d tool(s), every site agrees", len(verdicts))
        return 0
    logger.error(
        "pin-parity FAILED for %d of %d tool(s): %s",
        len(drifted),
        len(verdicts),
        ", ".join(v.tool for v in drifted),
    )
    logger.error(
        "Bump every site for a tool in ONE change. Renovate sees each site as "
        "a separate dependency, so group them in renovate.json packageRules "
        "as well, or the next bump splits again."
    )
    return 1
