# Copyright (c) 2026 Raymond Manaloto
"""Repo-owned installer for graphify's per-platform skill surface.

**Why this exists.** ``graphify install`` / ``graphify <platform> install`` /
``graphify hook install`` / ``graphify --watch`` are banned against this repo
(``do-not.md`` #8): a bare install mutates ``~/.claude`` (~43 KB of skill
files plus an appended ``~/.claude/CLAUDE.md``), and a codex-platform install
ALSO appends the line-budgeted root ``AGENTS.md`` — this repo's size gate
rejects that append. ``CLAUDE_CONFIG_DIR`` is not containment; both writes
are hardcoded into graphify's installer, not into the underlying skill-copy
mechanics it wraps.

This module reimplements ONLY that underlying copy — a packaged
``SKILL.md``, its optional ``references/`` sidecar, and a
``.graphify_version`` stamp, written into a caller-supplied project
directory — and never the ``AGENTS.md``/``CLAUDE.md`` append, the
``~/.claude`` write, or the ``.codex/hooks.json`` patch graphify's installer
also performs. WHICH platform maps to WHICH relative destination and
reference bundle is read straight from graphify's own ``_PLATFORM_CONFIG``
(``graphify.install``, imported **read-only** — its install *functions* are
never called), so this repo's placement table cannot silently drift from
what the installed graphify version itself declares.

Platform and target directory are both parameters (never hard-coded), per
``.claude/rules/agent-artifact-conventions.md`` rule 6 — this repo's own case
(this repo's root) is only ever the CLI layer's *default*, in
:func:`graphify_skill_install_main`.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import ModuleType

try:
    from graphify import install as _graphify_install
except ImportError as exc:  # pragma: no cover - environment defect, not a code path
    _graphify_install: ModuleType | None = None
    _IMPORT_ERROR: ImportError | None = exc
else:
    _IMPORT_ERROR = None

_MISSING_GRAPHIFY_MESSAGE = (
    "the `graphify` package is not importable in this environment"
)

#: The distribution name graphify ships under — mirrors
#: ``dotfiles_setup.graphify._runtime_version``'s own lookup, so the version
#: this module stamps and the version ``graphify_health`` reports about the
#: running package can never name two different distributions.
_DIST_NAME = "graphifyy"


class UnsafePlacementError(ValueError):
    """A platform's declared ``skill_dst`` resolves outside ``project_dir``.

    Python's ``Path.__truediv__`` replaces the left operand outright when
    the right operand is absolute, and never collapses ``..`` segments —
    so ``project_dir / cfg["skill_dst"]`` alone is not containment, only a
    string join that happens to look like one for well-behaved input. This
    is raised instead of silently writing (or silently skipping) whenever
    the destination's PARENT — the directory every write in
    :func:`install_skill` actually targets — does not resolve strictly
    beneath ``project_dir``.

    Note the parent, not the destination: a ``skill_dst`` of ``""`` or
    ``"."`` resolves to ``project_dir`` itself, whose parent is one
    directory ABOVE the target. That case raises, and an earlier revision
    of this guard exempted it — which is how the ``references/`` bundle
    could be written outside the target with no error.
    """


@dataclass(frozen=True)
class SkillPlacement:
    """Where one platform's packaged graphify skill (+ references) belong."""

    #: The platform key (a `graphify.install._PLATFORM_CONFIG` entry).
    platform: str
    #: Absolute destination for SKILL.md, under the caller's project_dir.
    skill_dst: Path
    #: Absolute source SKILL.md inside the installed graphify package.
    skill_src: Path
    #: Absolute source references/ dir, or None for a monolith platform.
    refs_src: Path | None


def _require_graphify() -> ModuleType:
    """The ``graphify.install`` module — imported read-only, never invoked.

    Raises loudly rather than resolving to nothing when graphify is not
    installed, so a caller sees a clear error instead of a confusing
    downstream ``KeyError``/``AttributeError``.
    """
    if _graphify_install is None:
        raise ModuleNotFoundError(_MISSING_GRAPHIFY_MESSAGE) from _IMPORT_ERROR
    return _graphify_install


def _platform_config() -> dict[str, Any]:
    """Graphify's own per-platform placement table.

    ``_PLATFORM_CONFIG`` is private by graphify's own naming — deliberately
    read anyway (never called), because it is the vendor's OWN source of the
    placement table and so cannot drift from what a real
    ``graphify <platform> install`` would do. This module carries the one
    documented ``SLF001`` per-file allowance for exactly this access
    (``python/pyproject.toml``, mirroring the ``codec.py``/``TID251``
    precedent).
    """
    return _require_graphify()._PLATFORM_CONFIG


def known_platforms() -> tuple[str, ...]:
    """Every platform name graphify's own installer knows about, sorted.

    Straight from ``_PLATFORM_CONFIG``'s keys — never a hand-maintained list,
    so it cannot drift from what the installed graphify version actually
    ships. ``gemini`` is deliberately absent: it has no ``_PLATFORM_CONFIG``
    entry (it installs claude's monolith body via a different code path this
    module does not replicate).
    """
    return tuple(sorted(_platform_config()))


def _package_root() -> Path:
    """The installed graphify package directory — source of every packaged file."""
    module = _require_graphify()
    if module.__file__ is None:
        message = "graphify.install has no __file__"
        raise ModuleNotFoundError(message)
    return Path(module.__file__).parent


def resolve_placement(platform: str, *, project_dir: Path) -> SkillPlacement:
    """Resolve where ``platform``'s skill file belongs, straight from graphify's table.

    Verified against graphify 0.9.53's ``_platform_skill_destination``: every
    project-scoped branch there — including the ones special-cased ahead of
    the generic ``_PLATFORM_CONFIG`` lookup (``opencode``, ``hermes``,
    ``devin``, ``amp``, ``agents``, ``antigravity``) — resolves to
    ``project_dir / cfg["skill_dst"]`` — the same join used here, but then
    resolved and checked for containment (see ``UnsafePlacementError``
    below): an absolute or ``..``-laden ``skill_dst`` would otherwise walk
    the join outside ``project_dir``, since ``Path.__truediv__`` neither
    rejects an absolute right operand nor collapses ``..``. Only ``gemini``
    (no ``_PLATFORM_CONFIG`` entry) is not representable this way.

    Args:
        platform: A key of graphify's ``_PLATFORM_CONFIG`` (see
            :func:`known_platforms`).
        project_dir: The directory this skill is scoped to. Has no default
            here — the CLI layer (:func:`graphify_skill_install_main`)
            defaults it to this repo's root, so a caller outside this repo
            can still point it elsewhere.

    Raises:
        KeyError: ``platform`` is not one ``_PLATFORM_CONFIG`` declares —
            deliberately, rather than silently resolving to nothing.
        UnsafePlacementError: ``skill_dst``'s *parent directory* — every
            write in :func:`install_skill` targets ``skill_dst.parent``,
            never ``skill_dst`` itself as a directory — does not resolve
            inside ``project_dir``. Covers an absolute ``skill_dst`` (which
            replaces ``project_dir`` outright under ``/``), one laden with
            enough ``..`` segments to walk back out, AND a ``skill_dst`` of
            ``""``/``"."`` (which resolves to ``project_dir`` itself, so its
            *parent* is one directory ABOVE ``project_dir`` — checking
            ``skill_dst`` alone would let this one through). Never silently
            written, never silently skipped.
    """
    cfg = _platform_config()[platform]
    root = _package_root()
    refs_bundle = cfg.get("skill_refs")
    refs_src = (
        (root / "skills" / str(refs_bundle) / "references") if refs_bundle else None
    )
    project_root = project_dir.resolve()
    skill_dst = (project_dir / cfg["skill_dst"]).resolve()
    # Every write in install_skill() targets skill_dst.parent (mkdir,
    # copytree, the .graphify_version stamp, the temp-file + rename for
    # SKILL.md itself) — so the parent, not skill_dst, is what must be
    # contained. A skill_dst of "" or "." resolves to project_root itself,
    # whose parent sits ONE DIRECTORY ABOVE project_root; checking skill_dst
    # alone (an `== project_root` exemption) would wave that case through
    # and let every write land outside project_dir.
    if not skill_dst.parent.is_relative_to(project_root):
        message = (
            f"platform {platform!r} declares skill_dst {cfg['skill_dst']!r}, "
            f"which resolves to {skill_dst} — its parent directory "
            f"{skill_dst.parent} is outside project_dir {project_root}. "
            f"Refusing to write."
        )
        raise UnsafePlacementError(message)
    return SkillPlacement(
        platform=platform,
        skill_dst=skill_dst,
        skill_src=root / cfg["skill_file"],
        refs_src=refs_src if refs_src is not None and refs_src.is_dir() else None,
    )


def _installed_version() -> str:
    try:
        return version(_DIST_NAME)
    except PackageNotFoundError:
        return "unknown"


def install_skill(platform: str, *, project_dir: Path) -> Path:
    """Copy the packaged SKILL.md (+ references/ sidecar) into ``project_dir``.

    Project-scoped ONLY: writes exactly three things under
    ``skill_dst.parent`` — ``SKILL.md``, an optional ``references/`` sidecar,
    and ``.graphify_version`` — and touches nothing outside that directory.
    ``resolve_placement`` enforces this: it raises ``UnsafePlacementError``
    rather than returning a placement outside ``project_dir``, so this is a
    checked invariant, not merely a convention this function happens to
    follow. That confinement is the whole reason this function can exist
    where ``graphify install`` cannot (do-not.md #8): no ``~/.claude`` write, no
    ``AGENTS.md``/``CLAUDE.md`` append, no ``.codex/hooks.json`` patch.

    A destination that already differs from the packaged source is backed up
    to ``SKILL.md.bak`` first (mirrors graphify's own installer, which added
    this after a wholesale-replace destroyed a locally hand-edited SKILL.md
    with no warning). SKILL.md itself is written last via a temp-file +
    atomic rename, so an interrupted install never leaves a half-written
    SKILL.md in place.

    The ``references/`` sidecar deliberately gets NO diff-check or backup —
    it is unconditionally ``rmtree``'d and recopied on every install. This
    mirrors graphify's own ``_install_skill_references``, which does the
    same unconditional replace: the SKILL.md ``.bak`` exists because a real
    incident showed users hand-edit that one file, and no such incident (or
    hand-editing workflow) exists for the packaged references/ bundle, which
    this repo treats as read-only vendor content. If that assumption ever
    stops holding, add the same diff-check/backup treatment here.
    """
    placement = resolve_placement(platform, project_dir=project_dir)
    if not placement.skill_src.is_file():
        message = (
            f"graphify package is missing {placement.skill_src} — reinstall graphify"
        )
        raise FileNotFoundError(message)
    placement.skill_dst.parent.mkdir(parents=True, exist_ok=True)

    if placement.refs_src is not None:
        refs_dst = placement.skill_dst.parent / "references"
        if refs_dst.exists():
            shutil.rmtree(refs_dst)
        shutil.copytree(placement.refs_src, refs_dst)

    if (
        placement.skill_dst.exists()
        and placement.skill_dst.read_bytes() != placement.skill_src.read_bytes()
    ):
        backup = placement.skill_dst.parent / f"{placement.skill_dst.name}.bak"
        shutil.copy2(placement.skill_dst, backup)

    tmp_dst = placement.skill_dst.parent / f"{placement.skill_dst.name}.tmp"
    shutil.copy(placement.skill_src, tmp_dst)
    tmp_dst.replace(placement.skill_dst)

    (placement.skill_dst.parent / ".graphify_version").write_text(
        _installed_version(), encoding="utf-8"
    )
    return placement.skill_dst


def graphify_skill_install_main(
    project_root: Path, *, platform: str, project_dir: Path | None = None
) -> int:
    """CLI entry point: ``dotfiles-setup graphify skill-install <platform>``.

    ``project_dir`` defaults to ``project_root`` (this repo) — the one place
    this repo's own case is hard-coded, per
    ``.claude/rules/agent-artifact-conventions.md`` rule 6.
    """
    target = project_dir if project_dir is not None else project_root
    try:
        dst = install_skill(platform, project_dir=target)
    except KeyError:
        sys.stderr.write(
            f"error: {platform!r} is not a platform graphify's own installer "
            f"knows about. Known: {', '.join(known_platforms())}\n"
        )
        return 1
    except (ModuleNotFoundError, FileNotFoundError, UnsafePlacementError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    sys.stdout.write(f"graphify skill installed -> {dst}\n")
    return 0
