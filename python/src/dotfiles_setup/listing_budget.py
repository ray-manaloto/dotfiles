# Copyright (c) 2026 Raymond Manaloto
"""The STANDING cost of the skill and agent listings — the eager class no gate saw.

Claude Code keeps every discovered skill's ``name`` + ``description`` (+
``when_to_use``) and every agent type's ``name`` + ``description`` in context
**every turn**, so the model can decide what is relevant. Only the chosen
skill's body ever loads. That listing is real, standing, per-session context.

``kb-setup md-budget`` cannot see it, and the gap is structural rather than an
oversight: it sweeps ``git ls-files`` in ONE repo, so it governs this project's
24 skills and is blind to every enabled third-party plugin — and blind to
``.claude/agents/*.md`` entirely, which ``classify()`` returns ``None`` for.

Measured on this host 2026-08-07, against the ``enabledPlugins`` set rather than
the plugin cache: **skills ~21,065 B + agents ~8,809 B ≈ 29,874 B (~7,470
tokens)** standing, on top of the 125,376 B of eager repo markdown and
``MEMORY.md``'s 21,704 B.

⚠️ **The measurement that must not be repeated.** The first pass globbed
``~/.claude/plugins/cache`` and reported **2,164 skills / 531 agents /
~174,820 tokens** — a 20x overstatement, because the cache holds EVERY VERSION of
EVERY plugin including disabled ones. The session's own startup line ("39 skills
· 31 agents") was the control arm that caught it. This module therefore resolves
through ``enabledPlugins``, never by walking the cache: a number that counts
things the harness never loads is worse than no number, because it redirects
work at a problem that does not exist. See
``.claude/rules/probes-need-a-control-arm.md`` rule 3 — a bound-limited search is
suspect, and so is an unbounded one reported as if it were bounded.

Why this lives in the DOCTOR and not in ``hk``/CI: every input is host state
(``~/.claude/plugins``, which plugins this operator enables). A CI runner has
none of it, so a gate there could only ever report zero — the same reason
``doctor.toml`` exists at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from kb_setup.md_budget import SKILL_DESCRIPTION_MAX, skill_description

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable
    from pathlib import Path

__all__ = [
    "SKILL_DESCRIPTION_MAX",
    "ListingEntry",
    "collect_listing",
    "over_cap",
    "total_chars",
]

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---(\n|$)", re.DOTALL)


@dataclass(frozen=True)
class ListingEntry:
    """One row of a listing, and what it costs standing."""

    kind: str
    """``"skill"`` or ``"agent"``."""

    source: str
    """``"project"`` or ``"plugin:<name>"``."""

    name: str

    chars: int
    """``len(name) + len(description)`` — what the listing actually carries."""

    desc_chars: int
    """What the 1,536 HARD cap applies to.

    For a skill that is ``description`` + ``when_to_use`` COMBINED, because the
    harness appends the second to the first in the listing; for an agent it is
    ``description`` alone, there being no second field. Said as "the description
    alone" until 2026-08-07 (#640), which was true only of agents.
    """

    path: str


def _frontmatter(raw: str) -> str:
    match = _FRONTMATTER_RE.match(raw)
    return match.group(1) if match else ""


def _field(front: str, name: str) -> str:
    match = re.search(
        rf"^{name}:\s*(.*?)(?=\n[A-Za-z_-]+:|\Z)", front, re.DOTALL | re.MULTILINE
    )
    return match.group(1).strip() if match else ""


def _read(path: Path) -> str | None:
    """File text, or ``None`` when it cannot be read.

    A dangling symlink in the plugin cache is normal (one was hit on the first
    run), and a listing measurement must not crash the doctor over it.
    """
    try:
        return path.read_text(errors="replace")
    except OSError:
        return None


def _version_key(name: str) -> tuple[int, ...]:
    """Sort key for a cache directory named like a version.

    Non-numeric names (``builder-skills`` pins a git sha, ``5f76017788f3``) sort
    below every numeric one rather than raising.
    """
    parts = name.split(".")
    if not all(part.isdigit() for part in parts):
        return (-1,)
    return tuple(int(part) for part in parts)


def plugin_root(home: Path, plugin_id: str) -> Path | None:
    """The cache directory Claude Code loads an enabled plugin from.

    ⚠️ **Do NOT resolve this by mtime.** The cache keeps every version ever
    installed side by side — antigravity had **eight** — and the version
    directory's own mtime does not move when a file inside it changes, so an
    mtime heuristic silently picks an arbitrary one. It was wrong here on the
    first try: it selected ``0.20.0`` while the live version was ``0.22.2``, and
    an edit was made to the wrong file. The doctor's own output disagreeing with
    that edit is what surfaced it.

    Resolution is the **highest numeric version directory** — deterministic,
    and it reproduces what the session actually loaded.

    ⚠️ ``~/.claude/plugins/installed_plugins.json`` looks like the authoritative
    answer and was rejected on evidence. It is Claude Code's own record, with an
    explicit ``installPath`` and ``version`` — but it is scoped PER PROJECT and
    **disagreed with reality** when checked: it records ``mattpocock-skills``
    1.2.0 for this repo (1.2.3 for the sibling knowledge-base), while the
    session running in this repo loaded **1.2.3**, and it carries no entry at
    all for ``antigravity`` under this project though the plugin is enabled here
    and its agents were listed. A record that disagrees with the observed load
    is not a source of truth, so the version-max rule — which matched the
    observed load in both cases — is used instead. Preferring the record
    because it is "official" would have been `use-tool-builtins.md` applied
    without checking that the built-in is correct.
    """
    plugin_name, _, marketplace = plugin_id.partition("@")
    if not marketplace:
        return None
    base = home / ".claude" / "plugins" / "cache" / marketplace / plugin_name
    if not base.is_dir():
        return None
    versions = [d for d in base.iterdir() if d.is_dir()]
    if not versions:
        return None
    return max(versions, key=lambda d: _version_key(d.name))


def _scan(root: Path, kind: str, source: str) -> list[ListingEntry]:
    """Every listable ``kind`` under one plugin/project root."""
    base = root / ("skills" if kind == "skill" else "agents")
    if not base.is_dir():
        return []
    pattern = "SKILL.md" if kind == "skill" else "*.md"
    entries: list[ListingEntry] = []
    for path in sorted(base.rglob(pattern)):
        raw = _read(path)
        if raw is None:
            continue
        front = _frontmatter(raw)
        if kind == "skill":
            # description + when_to_use — BOTH, because the cap is on their sum.
            # Upstream now reads both fields (the pin moved past that fix), so
            # this reuses it rather than carrying a second implementation.
            desc = skill_description(raw)
            name = _field(front, "name") or path.parent.name
        else:
            desc = _field(front, "description")
            name = _field(front, "name") or path.stem
        if not desc:
            continue
        entries.append(
            ListingEntry(
                kind=kind,
                source=source,
                name=name,
                chars=len(name) + len(desc),
                desc_chars=len(desc),
                path=str(path),
            )
        )
    return entries


def collect_listing(
    repo_root: Path, home: Path, plugin_ids: Iterable[str]
) -> tuple[ListingEntry, ...]:
    """Every skill and agent whose listing row is standing context here."""
    entries: list[ListingEntry] = []
    for kind in ("skill", "agent"):
        entries.extend(_scan(repo_root / ".claude", kind, "project"))
    seen: set[str] = set()
    for plugin_id in plugin_ids:
        name = plugin_id.partition("@")[0]
        if name in seen:
            continue
        seen.add(name)
        root = plugin_root(home, plugin_id)
        if root is None:
            continue
        for kind in ("skill", "agent"):
            entries.extend(_scan(root, kind, f"plugin:{name}"))
    return tuple(entries)


def total_chars(entries: Iterable[ListingEntry]) -> int:
    """Standing characters across a listing."""
    return sum(entry.chars for entry in entries)


def over_cap(entries: Iterable[ListingEntry]) -> list[ListingEntry]:
    """Entries whose listed text exceeds the HARD 1,536-character cap.

    "Listed text" is ``desc_chars`` — for a skill, ``description`` +
    ``when_to_use`` combined.

    This is the only limit in the whole instruction system that TRUNCATES rather
    than merely costs, and it fails silently — the tail is cut, taking the
    keywords the model matches on with it. Measured case: an agent's description
    ran 1,789 chars and the 253 characters cut were its NEGATIVE example ("below
    the break-even — just do it directly"), so truncation removed the half of the
    trigger that says when NOT to use it.
    """
    return [entry for entry in entries if entry.desc_chars > SKILL_DESCRIPTION_MAX]
