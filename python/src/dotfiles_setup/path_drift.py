# Copyright (c) 2026 Raymond Manaloto
"""PATH-drift preflight: does this shell resolve the tools mise currently pins?

A long-lived interactive shell caches its mise activation. After a dependency
bump lands and ``mise install`` runs, the shell keeps the OLD install directory
on ``$PATH``, so every command typed into it — and every child it spawns,
including Claude Code and its Bash tool — executes a stale binary while
``mise which`` truthfully reports the new one. Nothing errors. The gate that
runs is simply not the gate you pinned.

Four occurrences before this module existed (#596): hk 1.52.0 against a 1.54.0
pin, twice in session 2026-08-05g (spurious ``test_hk_builtins_audit`` failures
that cost a diagnosis cycle each); ``renovate-config-validator`` 44.13.2 against
44.14.10 and ``uv`` 0.12.2 against 0.12.3 on 2026-08-08, both surviving an
``mise install`` that exited 0; and 14 tools at once when this module was
written, hk / uv / python / npm:renovate among them.

Why this cannot live in ``mise run lint`` or any other mise task
----------------------------------------------------------------

**Measured, and it inverts the issue's stated fix shape.** ``mise exec`` and
``mise run <task>`` both *replace* the stale install directory in ``$PATH``
before the child starts — the stale entry is gone, not merely reordered::

    ambient shell          command -v hk -> .../installs/hk/1.54.0/hk
    under `mise run <task>` command -v hk -> .../installs/hk/1.54.1/hk

So a preflight wired into ``mise run lint`` observes a repaired ``PATH`` and can
only ever report clean: a check with one face, which
``.claude/rules/probes-need-a-control-arm.md`` rule 9 exists to refuse.
``__MISE_ORIG_PATH`` does not rescue it either — it holds the PRISTINE
pre-activation ``PATH`` (measured: zero ``installs/`` entries) and is
byte-identical inside and outside ``mise exec``.

Two consequences shape this module:

1. **The ambient ``PATH`` must be captured by the caller** before mise rewrites
   it, and handed over in :data:`AMBIENT_PATH_ENV`. The SessionStart hook in
   ``.claude/settings.json`` does exactly that.
2. **The probe must know when it is blind.** ``mise run <task>`` sets
   ``MISE_TASK_NAME`` (with ``MISE_TASK_DIR`` / ``MISE_TASK_FILE`` /
   ``MISE_PROJECT_ROOT``); an ambient shell has none of them. That marker is a
   non-circular blindness detector — present, with no captured ambient ``PATH``,
   means :data:`Provenance.BLIND`, which is reported as such and **never** as
   "no drift found".

How the comparison works
------------------------

Not ``mise which <tool>`` versus ``command -v <tool>``, which needs a
tool-to-binary-name map and one subprocess per tool. Instead: one
``mise ls --current --json`` gives every active tool's ``install_path``, whose
last two components are ``<slug>/<version>``. Every ``$PATH`` entry under the
same installs root parses the same way. A slug present in both with **no version
in common** is drift, named with both versions.

That enumerates rather than asserting a tool list
(``feedback_enumerate_dont_assert_the_list``): the five tools the issue names
are the ones that happen to have drifted so far, not the ones that can. Measured
on the authoring host: 147 of 148 active tools had a ``$PATH`` entry, **zero**
``$PATH`` slugs were unknown to mise, and 14 were drifted — so the shape is
precise, not noisy. The one tool with no ``$PATH`` entry (``rust``) is benign
and is why :func:`absent_findings` is opt-in rather than reported by default.

Shims are excluded by construction: ``~/.local/share/mise/shims/<bin>`` resolves
the version at exec time, so it is never stale.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

#: The caller captures the pre-mise ``PATH`` here. Without it, a process started
#: by ``mise run``/``mise exec`` sees a repaired ``PATH`` and cannot see drift.
AMBIENT_PATH_ENV = "DOTFILES_AMBIENT_PATH"

#: Set by ``mise run <task>`` and absent from an ambient shell (measured). Its
#: presence proves mise rewrote the environment, so an inherited ``PATH`` is
#: mise's answer rather than the shell's.
MISE_TASK_MARKER = "MISE_TASK_NAME"

#: One subprocess for every active tool's resolved install directory.
MISE_LS_COMMAND = ("mise", "ls", "--current", "--json")

#: ``<slug>/<version>`` — the shallowest install path that names a version.
_SLUG_VERSION_DEPTH = 2

_MISE_TIMEOUT_S = 60.0

#: Tools whose staleness silently weakens a gate rather than merely annoying
#: someone. Overridable via ``doctor.toml``'s ``[path_drift] gate_tools``; every
#: name here has actually drifted at least once (#596).
DEFAULT_GATE_TOOLS: tuple[str, ...] = ("hk", "uv", "python", "ruff", "npm:renovate")


class Provenance(Enum):
    """Where the ``PATH`` under examination came from, and whether to trust it."""

    #: Handed over explicitly — the caller captured it before mise ran.
    EXPLICIT = "explicit"
    #: Inherited from the process environment, with no sign mise rewrote it.
    INHERITED = "inherited"
    #: Inherited, but ``MISE_TASK_MARKER`` proves mise rewrote it. Unusable.
    BLIND = "blind"


@dataclass(frozen=True)
class Drift:
    """One tool whose ``$PATH`` version is not among mise's active versions."""

    tool: str
    slug: str
    path_versions: tuple[str, ...]
    active_versions: tuple[str, ...]

    def describe(self) -> str:
        """``hk 1.54.0 on PATH, mise resolves 1.54.1``."""
        return (
            f"{self.tool} {'/'.join(self.path_versions)} on PATH, "
            f"mise resolves {'/'.join(self.active_versions)}"
        )


@dataclass(frozen=True)
class Report:
    """The outcome of one comparison, including the case where it saw nothing."""

    provenance: Provenance
    drifts: tuple[Drift, ...] = ()
    tools_compared: int = 0
    error: str | None = None

    @property
    def usable(self) -> bool:
        """False when the probe could not see the shell it is asked about."""
        return self.provenance is not Provenance.BLIND and self.error is None

    def gate_drifts(
        self, gate_tools: tuple[str, ...] = DEFAULT_GATE_TOOLS
    ) -> tuple[Drift, ...]:
        """The subset whose staleness degrades a gate rather than an ergonomic."""
        wanted = set(gate_tools)
        return tuple(d for d in self.drifts if d.tool in wanted or d.slug in wanted)


def resolve_ambient_path(
    environ: Mapping[str, str],
    *,
    ambient_path: str | None = None,
) -> tuple[str, Provenance]:
    """Pick the ``PATH`` to examine and say how much it can be trusted.

    Precedence is explicit argument, then :data:`AMBIENT_PATH_ENV`, then the
    inherited ``PATH`` — and the inherited one is downgraded to
    :attr:`Provenance.BLIND` when :data:`MISE_TASK_MARKER` shows mise rewrote it.
    """
    if ambient_path is not None:
        return ambient_path, Provenance.EXPLICIT
    captured = environ.get(AMBIENT_PATH_ENV)
    if captured:
        return captured, Provenance.EXPLICIT
    inherited = environ.get("PATH", "")
    if environ.get(MISE_TASK_MARKER):
        return inherited, Provenance.BLIND
    return inherited, Provenance.INHERITED


def run_mise_ls() -> tuple[dict[str, object], str | None]:
    """``mise ls --current --json`` parsed, or ``({}, reason)`` when it fails."""
    try:
        result = subprocess.run(
            MISE_LS_COMMAND,
            capture_output=True,
            text=True,
            check=False,
            timeout=_MISE_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {}, f"could not run {' '.join(MISE_LS_COMMAND)}: {exc}"
    if result.returncode != 0:
        return {}, f"{' '.join(MISE_LS_COMMAND)} exited {result.returncode}"
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {}, f"could not parse {' '.join(MISE_LS_COMMAND)} output: {exc}"
    return (parsed if isinstance(parsed, dict) else {}), None


@dataclass(frozen=True)
class ActiveTool:
    """A mise tool that is active here, and the versions it resolves to."""

    tool: str
    slug: str
    versions: frozenset[str]


def active_tools(
    listing: Mapping[str, object],
) -> tuple[dict[str, ActiveTool], Path | None]:
    """Index ``mise ls --current --json`` by install-directory slug.

    Returns the index plus the installs root, derived from the paths themselves
    rather than hard-coded — ``MISE_DATA_DIR`` moves it, and a root guessed from
    ``$HOME`` would silently match nothing on a host that has.
    """
    by_slug: dict[str, ActiveTool] = {}
    root: Path | None = None
    for tool, raw in listing.items():
        for entry in raw if isinstance(raw, list) else []:
            install = entry.get("install_path") if isinstance(entry, dict) else None
            if not isinstance(install, str) or not install:
                continue
            path = Path(install)
            root = path.parent.parent
            slug, version = path.parent.name, path.name
            existing = by_slug.get(slug)
            versions = (existing.versions if existing else frozenset()) | {version}
            by_slug[slug] = ActiveTool(tool=tool, slug=slug, versions=versions)
    return by_slug, root


def path_versions(path_value: str, installs_root: Path) -> dict[str, frozenset[str]]:
    """Slug -> versions that ``path_value`` points at under ``installs_root``.

    A shim directory is not under the installs root, so it drops out here rather
    than needing a special case: it resolves its version at exec time and can
    never be stale.
    """
    found: dict[str, set[str]] = {}
    for raw in path_value.split(os.pathsep):
        if not raw:
            continue
        try:
            parts = Path(raw).relative_to(installs_root).parts
        except ValueError:
            continue
        if len(parts) < _SLUG_VERSION_DEPTH:
            continue
        found.setdefault(parts[0], set()).add(parts[1])
    return {slug: frozenset(versions) for slug, versions in found.items()}


def compare(
    ambient: dict[str, frozenset[str]],
    active: dict[str, ActiveTool],
) -> tuple[Drift, ...]:
    """Slugs both sides know about, with **no version in common**.

    Intersection rather than equality: a slug mise does not consider active is
    not drift (it is simply a tool this directory does not declare), and a slug
    with one shared version is being resolved correctly.
    """
    drifts = [
        Drift(
            tool=tool.tool,
            slug=slug,
            path_versions=tuple(sorted(versions)),
            active_versions=tuple(sorted(tool.versions)),
        )
        for slug, versions in ambient.items()
        if (tool := active.get(slug)) is not None and not (versions & tool.versions)
    ]
    return tuple(sorted(drifts, key=lambda d: d.tool))


def absent_findings(
    ambient: dict[str, frozenset[str]],
    active: dict[str, ActiveTool],
) -> tuple[str, ...]:
    """Active tools with no ``$PATH`` entry at all — opt-in, because it is noisy.

    Measured 1 of 148 on the authoring host (``rust``, whose binaries are not
    published directly under the install directory), so reporting it every
    session would be crying wolf. Kept as a function because on another host the
    same signature would mean a tool the shell never picked up at all.
    """
    return tuple(
        sorted(tool.tool for slug, tool in active.items() if slug not in ambient)
    )


def check_path_drift(
    *,
    environ: Mapping[str, str] | None = None,
    ambient_path: str | None = None,
    listing: Mapping[str, object] | None = None,
) -> Report:
    """Compare the ambient ``PATH`` with mise's current resolution.

    Every input is injectable so a test drives the whole comparison without a
    subprocess and without touching the host's real ``PATH``.
    """
    environ = os.environ if environ is None else environ
    path_value, provenance = resolve_ambient_path(environ, ambient_path=ambient_path)
    if provenance is Provenance.BLIND:
        return Report(provenance=provenance)
    error: str | None = None
    if listing is None:
        listing, error = run_mise_ls()
    if error is not None:
        return Report(provenance=provenance, error=error)
    active, installs_root = active_tools(listing)
    if installs_root is None:
        return Report(
            provenance=provenance,
            error="mise reported no active tool with an install path",
        )
    ambient = path_versions(path_value, installs_root)
    return Report(
        provenance=provenance,
        drifts=compare(ambient, active),
        tools_compared=len(ambient),
    )


BLIND_ADVICE = (
    f"PATH-drift check is BLIND: {MISE_TASK_MARKER} is set, so mise already "
    f"rewrote PATH for this process and the shell's own resolution is not "
    f"visible here. This is NOT 'no drift'. Have the caller capture it: "
    f'{AMBIENT_PATH_ENV}="$PATH" mise run <task>'
)


def drift_advice(drifts: tuple[Drift, ...], *, gate: tuple[Drift, ...]) -> str:
    """The one-line summary a caller prints, gate-critical tools named first."""
    lead = ", ".join(d.describe() for d in (gate or drifts))
    extra = len(drifts) - len(gate) if gate else 0
    tail = f" (+{extra} more tool(s) drifted)" if extra > 0 else ""
    gate_note = "GATE-CRITICAL: " if gate else ""
    return (
        f"{gate_note}{len(drifts)} tool(s) resolve to a STALE version in this "
        f"shell's PATH — {lead}{tail}. This shell's mise activation is cached "
        f"from before the last install, so gates run the old binary while "
        f"`mise which` reports the new one (#596). Fix: start a new shell "
        f"(`exec $SHELL`), or prefix the command with `mise exec --`."
    )


def path_drift_main(
    *,
    ambient_path: str | None = None,
    strict: bool = False,
    verbose: bool = False,
) -> int:
    """CLI entry: report drift; ``2`` when blind, ``1`` on drift under strict.

    Blind is its own exit code and is never folded into success — a probe that
    could not see is not a probe that saw nothing.
    """
    report = check_path_drift(ambient_path=ambient_path)
    if report.provenance is Provenance.BLIND:
        logger.error("%s", BLIND_ADVICE)
        return 2
    if report.error is not None:
        logger.error("PATH-drift check could not run: %s", report.error)
        return 2
    if report.drifts:
        logger.error("%s", drift_advice(report.drifts, gate=report.gate_drifts()))
        for drift in report.drifts:
            logger.error("  stale: %s", drift.describe())
        return 1 if strict else 0
    if verbose:
        logger.info(
            "PATH-drift: OK — %d mise tool(s) on PATH all match the active "
            "version (provenance=%s)",
            report.tools_compared,
            report.provenance.value,
        )
    return 0
