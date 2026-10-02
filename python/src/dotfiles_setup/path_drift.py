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


# --------------------------------------------------------------------------- #
# Native-only binaries — the same ambient PATH, a different question
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class NativeTool:
    """Where one native-only binary must resolve, and what may compete with it.

    ``native`` is POSITIVE: the first ``PATH`` hit's real path must equal or sit
    under one of these (``~`` expanded). "Not under mise" is not enough — a
    Homebrew cask or an npm-global copy is just as much not the native install.
    ``specs`` are the mise tool specs that have put, or through the registry
    could put, a competing copy on ``PATH``; they drive the leftover-directory
    warning and map an install-directory slug back to an uninstall argument.
    """

    native: tuple[str, ...]
    specs: tuple[str, ...] = ()


#: Ray's ruling (2026-10-01): on the Mac host these come ONLY from the vendor's
#: native installer. Locations measured on the authoring host:
#: ``~/.local/bin/agy`` is a regular Mach-O file; ``~/.local/bin/codex`` links
#: into ``~/.codex/packages/standalone/releases/<ver>/bin/codex``;
#: ``~/.local/bin/claude`` links to ``~/.local/share/claude/versions/<ver>``.
#: Overridable through ``doctor.toml``'s ``[path_drift.native_only.<binary>]``.
#:
#: The devcontainer has its own native-CLI check (``native_clis_container``, on a
#: sibling branch); once both land, a shared per-tool table can replace this one.
DEFAULT_NATIVE_ONLY: dict[str, NativeTool] = {
    "agy": NativeTool(
        native=("~/.local/bin/agy",),
        specs=("antigravity-cli", "aqua:google-antigravity/antigravity-cli"),
    ),
    "codex": NativeTool(
        native=("~/.codex/packages/standalone",),
        specs=(
            "codex",
            "npm:@openai/codex",
            "aqua:openai/codex",
            "github:openai/codex",
        ),
    ),
    "claude": NativeTool(
        native=("~/.local/share/claude/versions",),
        specs=(
            "claude",
            "claude-code",
            "npm:@anthropic-ai/claude-code",
            "github:anthropics/claude-code",
            "aqua:anthropics/claude-code",
            "http:claude",
        ),
    ),
}

#: Where mise keeps data when nothing moves it: the per-user default and the
#: system-wide one this host also has. ``MISE_DATA_DIR`` and the installs root
#: ``mise ls`` reports are added on top, never instead.
_USER_MISE_DATA = (".local", "share", "mise")
_SYSTEM_MISE_DATA = Path("/usr/local/share/mise")
_MISE_SUBDIRS = ("installs", "shims")

#: Path components that name a non-native package manager, checked against both
#: the ``PATH`` entry and the resolved target so a finding can name the source.
_FOREIGN_SOURCES: tuple[tuple[str, str], ...] = (
    ("Caskroom", "a Homebrew cask"),
    ("Cellar", "Homebrew"),
    ("homebrew", "Homebrew"),
    ("node_modules", "an npm global install"),
    (".bun", "a bun global install"),
    (".volta", "Volta"),
    (".yarn", "a yarn global install"),
)


def mise_slug(spec: str) -> str:
    """The install-directory name mise gives a tool spec.

    ``npm:@openai/codex`` -> ``npm-openai-codex``; a registry short name is its
    own slug. Matches every directory measured on this host
    (``npm:@devcontainers/cli`` -> ``npm-devcontainers-cli``,
    ``aqua:astral-sh/uv`` -> ``aqua-astral-sh-uv``).
    """
    return spec.replace("@", "").replace(":", "-").replace("/", "-")


def mise_data_dirs(
    environ: Mapping[str, str],
    *,
    home: Path,
    installs_root: Path | None = None,
) -> tuple[Path, ...]:
    """Every mise data directory a competing binary could live under."""
    candidates: list[Path] = []
    if installs_root is not None:
        candidates.append(installs_root.parent)
    if environ.get("MISE_DATA_DIR"):
        candidates.append(Path(environ["MISE_DATA_DIR"]))
    xdg = environ.get("XDG_DATA_HOME")
    candidates.append(Path(xdg) / "mise" if xdg else home.joinpath(*_USER_MISE_DATA))
    candidates.append(_SYSTEM_MISE_DATA)
    return tuple(dict.fromkeys(candidates))


def _mise_subdir_index(path: Path, data_dirs: tuple[Path, ...]) -> int | None:
    """Index of the ``installs``/``shims`` component that makes ``path`` mise's.

    The known data directories first, then the SHAPE ``…/mise/installs/…`` or
    ``…/mise/shims/…`` — a data directory nobody declared (another config's
    ``MISE_DATA_DIR``) still produces that shape, and missing it would pass a
    mise copy as something else.
    """
    parts = path.parts
    for data in data_dirs:
        for sub in _MISE_SUBDIRS:
            if path.is_relative_to(data / sub):
                return len((data / sub).parts) - 1
    for i in range(len(parts) - 1):
        if parts[i] == "mise" and parts[i + 1] in _MISE_SUBDIRS:
            return i + 1
    return None


def is_mise_path(path: Path, data_dirs: tuple[Path, ...]) -> bool:
    """True when ``path`` sits under a mise installs or shims directory."""
    return _mise_subdir_index(path, data_dirs) is not None


def which_all(binary: str, path_value: str) -> tuple[Path, ...]:
    """``which -a``: every executable ``binary`` on ``path_value``, in order."""
    hits: list[Path] = []
    for raw in dict.fromkeys(path_value.split(os.pathsep)):
        if not raw:
            continue
        candidate = Path(raw) / binary
        if candidate.is_file() and os.access(candidate, os.X_OK):
            hits.append(candidate)
    return tuple(hits)


def _from_mise(hit: Path, data_dirs: tuple[Path, ...]) -> bool:
    """A hit is mise's when its directory OR its resolved target is mise's.

    The target matters because a symlink in ``~/.local/bin`` pointing into an
    installs directory would otherwise pass as something else.
    """
    return is_mise_path(hit.parent, data_dirs) or is_mise_path(hit.resolve(), data_dirs)


def native_roots(tool: NativeTool, home: Path) -> tuple[Path, ...]:
    """``tool.native`` with ``~`` expanded against ``home`` and resolved."""
    return tuple(
        (home / raw[2:] if raw.startswith("~/") else Path(raw)).resolve()
        for raw in tool.native
    )


def is_native(hit: Path, roots: tuple[Path, ...]) -> bool:
    """True when ``hit``'s real path equals or sits under a native root."""
    real = hit.resolve()
    return any(real.is_relative_to(root) for root in roots)


def uninstall_spec(
    hit: Path, specs: tuple[str, ...], data_dirs: tuple[Path, ...]
) -> str | None:
    """The ``mise uninstall`` argument for a mise hit, from ITS install slug.

    A shim names no install, so ``None``: ``mise which`` has to say which one.
    """
    by_slug = {mise_slug(spec): spec for spec in specs}
    for path in (hit.parent, hit.resolve()):
        index = _mise_subdir_index(path, data_dirs)
        if index is None or path.parts[index] != "installs":
            continue
        if len(path.parts) > index + 1:
            slug = path.parts[index + 1]
            return by_slug.get(slug, slug)
    return None


def foreign_source(hit: Path) -> str:
    """Which package manager a non-native, non-mise hit most likely came from."""
    parts = {*hit.parts, *hit.resolve().parts}
    for marker, label in _FOREIGN_SOURCES:
        if marker in parts:
            return label
    return "an unrecognised source"


def _uninstall_advice(binary: str, spec: str | None) -> str:
    if spec is None:
        return (
            f"Fix: `mise which {binary}` names the install behind the shim; "
            f"then `mise uninstall --all <that tool> && mise reshim`."
        )
    return f"Fix: `mise uninstall --all {spec} && mise reshim`."


@dataclass(frozen=True)
class NativeOnlyReport:
    """Native-only verdicts, split by how close each is to breaking the ruling."""

    provenance: Provenance
    failures: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def native_only_findings(
    binary: str,
    tool: NativeTool,
    path_value: str,
    data_dirs: tuple[Path, ...],
    *,
    home: Path,
) -> tuple[list[str], list[str]]:
    """``(failures, warnings)`` for one native-only binary."""
    failures: list[str] = []
    warnings: list[str] = []
    roots = native_roots(tool, home)
    expected = ", ".join(tool.native)
    hits = which_all(binary, path_value)
    native = [hit for hit in hits if is_native(hit, roots)]
    if not hits:
        failures.append(
            f"FAIL: `{binary}` is not on PATH at all; expected the native "
            f"install at {expected}. Reinstall it with the vendor's installer."
        )
    elif _from_mise(hits[0], data_dirs):
        spec = uninstall_spec(hits[0], tool.specs, data_dirs)
        failures.append(
            f"FAIL: `{binary}` resolves to mise's copy {hits[0]} first — it must "
            f"come only from its native installer ({expected}). "
            f"{_uninstall_advice(binary, spec)}"
        )
    elif not is_native(hits[0], roots):
        failures.append(
            f"FAIL: `{binary}` resolves first to {hits[0]} (-> "
            f"{hits[0].resolve()}), from {foreign_source(hits[0])} — not the "
            f"native install at {expected}. Remove that copy or put the native "
            f"one ahead of it on PATH."
        )
    if hits and not native:
        failures.append(
            f"FAIL: no native `{binary}` anywhere on PATH (expected under "
            f"{expected}; found {', '.join(map(str, hits))}). Reinstall it with "
            f"the vendor's installer."
        )
    if hits and is_native(hits[0], roots):
        later = [hit for hit in hits[1:] if _from_mise(hit, data_dirs)]
        if later:
            advice = _uninstall_advice(
                binary, uninstall_spec(later[0], tool.specs, data_dirs)
            )
            warnings.append(
                f"WARN: `{binary}` resolves natively, but mise's copy is also on "
                f"PATH ({', '.join(map(str, later))}) — one PATH reorder from "
                f"winning. {advice}"
            )
    for data in data_dirs:
        for spec in tool.specs:
            leftover = data / "installs" / mise_slug(spec)
            if leftover.is_dir():
                warnings.append(
                    f"WARN: mise install directory {leftover} exists for "
                    f"`{binary}` — a mise install of a native-only tool, on "
                    f"PATH or not. {_uninstall_advice(binary, spec)} If it "
                    f"comes back, look for a `{spec}` pin in an old worktree's "
                    f"mise config."
                )
    return failures, warnings


def check_native_only(
    native_only: Mapping[str, NativeTool] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    ambient_path: str | None = None,
    listing: Mapping[str, object] | None = None,
    home: Path | None = None,
) -> NativeOnlyReport:
    """Do ``agy``/``codex``/``claude`` resolve to their native installs only?

    Reads the same ambient ``PATH`` as :func:`check_path_drift` and is BLIND
    under the same condition: inside a mise task, ``PATH`` is mise's answer.
    """
    environ = os.environ if environ is None else environ
    native_only = DEFAULT_NATIVE_ONLY if native_only is None else native_only
    home = home or Path.home()
    path_value, provenance = resolve_ambient_path(environ, ambient_path=ambient_path)
    if provenance is Provenance.BLIND:
        return NativeOnlyReport(provenance=provenance)
    warnings: list[str] = []
    error: str | None = None
    if listing is None:
        listing, error = run_mise_ls()
    if error is not None:
        warnings.append(
            f"WARN: could not ask mise for its installs root ({error}); only the "
            f"default mise data directories were checked."
        )
    _, installs_root = active_tools(listing)
    data_dirs = mise_data_dirs(environ, home=home, installs_root=installs_root)
    failures: list[str] = []
    for binary, tool in native_only.items():
        fails, warns = native_only_findings(
            binary, tool, path_value, data_dirs, home=home
        )
        failures.extend(fails)
        warnings.extend(warns)
    return NativeOnlyReport(
        provenance=provenance, failures=tuple(failures), warnings=tuple(warnings)
    )


NATIVE_ONLY_BLIND_ADVICE = (
    f"native-only check is BLIND: {MISE_TASK_MARKER} is set and no ambient PATH "
    f"was captured, so mise's PATH is all this process can see. This is NOT a "
    f'pass. Capture it: {AMBIENT_PATH_ENV}="$PATH" mise run doctor'
)
