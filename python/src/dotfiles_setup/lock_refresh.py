# Copyright (c) 2026 Raymond Manaloto
"""Staging + collection helpers for the CI lock-refresh job (#160 T8).

Three lockfiles keep this repo reproducible, and none can be refreshed by
the hosted Renovate app (it cannot run `mise lock` — admin allowlist — and
does not know `mise-system.lock` by name):

- ``mise.lock`` (repo root) — host/CI tools; regenerated in place with the
  runner's mise (`mise lock`).
- ``.devcontainer/mise-system.lock`` — the image's 100+ tools. MUST be
  generated on linux-x64 with the image's pinned MISE_VERSION (macOS mise
  silently omits linux-x64 conda checksums; lock formats are not
  cross-version compatible). The stage/collect pair here reproduces the
  image's merged-config layout as a throwaway project directory so a
  pinned mise binary can `mise lock -C <stage>` against it.
- ``.devcontainer/devcontainer-lock.json`` — devcontainer features;
  regenerated via `devcontainer upgrade`.

The staging is a single merged project config:

    <stage>/mise.toml          <- mise-system.toml with shared.toml's [tools]
                                  spliced into its [tools] table
    <stage>/mise.runtime.toml  <- mise-runtime.toml (runtime tier, #160 T9)
    <stage>/mise.lock          <- .devcontainer/mise-system.lock (seed)
    <stage>/mise.runtime.lock  <- .devcontainer/mise-runtime.lock (seed)

The splice (not a conf.d copy) is load-bearing: in a PROJECT layout the
conf.d fragment would live in a different config dir
(.config/mise/conf.d/) and mise writes one lock PER CONFIG DIR — the
shared tools would land in a separate .config/mise/mise.lock (empirically
verified, T9 regen). The IMAGE merges conf.d inside $MISE_CONFIG_DIR and
reads a single mise.lock covering both, so the staged lock must cover the
union — which the single merged file produces.

Seeding the committed locks lets repeated `mise lock` runs converge under
GitHub rate limits instead of starting cold each time.
"""

from __future__ import annotations

import re
import shutil
import tomllib
from typing import TYPE_CHECKING

from dotfiles_setup.lock_integrity import committed_text, regressions
from dotfiles_setup.platform_target import declared_lock_platforms

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

_MISE_VERSION_RE = re.compile(r"^ARG MISE_VERSION=(\S+)$", re.MULTILINE)
_SYSTEM_TOML = ".devcontainer/mise-system.toml"
_SYSTEM_LOCK = ".devcontainer/mise-system.lock"
_RUNTIME_TOML = ".devcontainer/mise-runtime.toml"
_RUNTIME_LOCK = ".devcontainer/mise-runtime.lock"
_SHARED_TOML = ".config/mise/conf.d/shared.toml"
# The MISE_ENV under which the runtime tier's config/lock resolve (#160 T9):
# staged as mise.runtime.toml, locked to mise.runtime.lock. `mise lock` must
# run with MISE_ENV=runtime to cover both tiers in one pass.
RUNTIME_ENV = "runtime"


def pinned_mise_version(dockerfile: Path) -> str:
    """Return the image's pinned MISE_VERSION from the Dockerfile ARG.

    The system lock must be (re)generated with this exact version — lock
    formats are not cross-version compatible and `mise install --locked`
    in the image rejects a lock written by a different mise.

    Raises:
        ValueError: when the ARG is absent (fail loud — a silent fallback
            to "latest" would regenerate an unconsumable lock).
    """
    match = _MISE_VERSION_RE.search(dockerfile.read_text())
    if match is None:
        msg = f"ARG MISE_VERSION=<version> not found in {dockerfile}"
        raise ValueError(msg)
    return match.group(1)


def stage_system_lock_dir(repo_root: Path, stage_dir: Path) -> str:
    """Stage the image's merged mise config as a throwaway project dir.

    Writes a single merged ``mise.toml`` (system config with the shared
    fragment's ``[tools]`` spliced in — see module docstring for why a
    conf.d copy does NOT work), the runtime tier config, and the committed
    locks as convergence seeds.

    Returns:
        The pinned MISE_VERSION the caller must run `mise lock` with.
    """
    version = pinned_mise_version(repo_root / ".devcontainer" / "Dockerfile")
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "mise.toml").write_text(
        _merge_shared_tools(
            (repo_root / _SYSTEM_TOML).read_text(),
            (repo_root / _SHARED_TOML).read_text(),
        )
    )
    shutil.copyfile(repo_root / _SYSTEM_LOCK, stage_dir / "mise.lock")
    # Runtime tier (#160 T9): staged under the project-layout env name so
    # `MISE_ENV=runtime mise lock` writes mise.runtime.lock beside mise.lock
    # (probe-verified per-env lock behavior). Seed the committed lock when
    # present (first regen after the tier split starts cold).
    shutil.copyfile(repo_root / _RUNTIME_TOML, stage_dir / f"mise.{RUNTIME_ENV}.toml")
    runtime_lock = repo_root / _RUNTIME_LOCK
    if runtime_lock.exists():
        shutil.copyfile(runtime_lock, stage_dir / f"mise.{RUNTIME_ENV}.lock")
    return version


def _merge_shared_tools(system_text: str, shared_text: str) -> str:
    """Splice the shared fragment's ``[tools]`` body into the system config.

    Text-level (no TOML serialization): the shared body — everything after
    its ``[tools]`` header — is inserted at the end of the system config's
    ``[tools]`` table, i.e. just before the next ``[`` section header.

    Raises:
        ValueError: when either file's structure defeats the splice points
            (fail loud rather than staging a lock input missing 20 tools).
    """
    shared_header = re.search(r"^\[tools\]\s*$", shared_text, re.MULTILINE)
    if shared_header is None:
        msg = "shared.toml has no [tools] table — splice point missing"
        raise ValueError(msg)
    shared_body = shared_text[shared_header.end() :].strip("\n")
    system_header = re.search(r"^\[tools\]\s*$", system_text, re.MULTILINE)
    if system_header is None:
        msg = "mise-system.toml has no [tools] table — splice point missing"
        raise ValueError(msg)
    next_section = re.search(r"^\[", system_text[system_header.end() :], re.MULTILINE)
    if next_section is None:
        msg = "mise-system.toml has no section after [tools] — splice point missing"
        raise ValueError(msg)
    insert_at = system_header.end() + next_section.start()
    return (
        system_text[:insert_at]
        + "# --- spliced from .config/mise/conf.d/shared.toml (lock staging) ---\n"
        + shared_body
        + "\n\n"
        + system_text[insert_at:]
    )


def collect_system_lock(repo_root: Path, stage_dir: Path) -> None:
    """Copy the regenerated stage lock back to `.devcontainer/mise-system.lock`.

    Validates before writing, on **two** axes — a truncated or partial lock
    (rate limits, an interrupted run, the wrong host OS) must never overwrite
    the committed one:

    1. **tool coverage** — every tool of the merged config is locked;
    2. **platform coverage** — no tool present in both the committed lock and
       the candidate lost a platform, and no conda platform family vanished.

    Axis 2 is #648, and axis 1 alone is why it was needed: a regen run on macOS
    dropped ``mise-system.lock``'s ``linux-x64`` occurrences 131 -> 64 and
    ``mise-runtime.lock``'s 35 -> 12 while the **tool count never moved** (49
    and 22, unchanged), so a tool-only predicate returned rc=0 on a near-51%
    coverage loss. The correct predicate already existed in
    :mod:`dotfiles_setup.lock_integrity`; it simply was not being called here.

    Raises:
        ValueError: when the stage lock is missing tools from the config, or
            lost platform coverage relative to the committed lock.
    """
    # The OS families the image config declares — the guard compares only
    # within them, so pruning a platform the image can never satisfy is not
    # read as damage. See `_collect_one`.
    families = {name.split("-", 1)[0] for name in declared_lock_platforms(repo_root)}
    _collect_one(
        stage_dir / "mise.lock",
        repo_root / _SYSTEM_LOCK,
        merged_system_config_tools(repo_root),
        coverage_baseline(repo_root, _SYSTEM_LOCK),
        families=families or None,
    )
    _collect_one(
        stage_dir / f"mise.{RUNTIME_ENV}.lock",
        repo_root / _RUNTIME_LOCK,
        runtime_config_tools(repo_root),
        coverage_baseline(repo_root, _RUNTIME_LOCK),
        families=families or None,
    )


def coverage_baseline(repo_root: Path, rel_path: str) -> str | None:
    """The bytes to measure a candidate lock's coverage against.

    ``HEAD`` first, on purpose: a run that already overwrote the working-tree
    lock would otherwise be compared against its own damage and certified
    clean. The on-disk file is the fallback rather than "no check at all",
    because an untracked lock or a non-git checkout must not silently disable
    the guard — a weaker baseline still catches the 51% truncation this exists
    for, whereas ``None`` catches nothing.
    """
    from_git = committed_text(repo_root, rel_path)
    if from_git is not None:
        return from_git
    path = repo_root / rel_path
    return path.read_text() if path.exists() else None


def _collect_one(
    stage_lock: Path,
    dest: Path,
    config_tools: set[str],
    committed: str | None,
    *,
    families: Collection[str] | None = None,
) -> None:
    stage_text = stage_lock.read_text()
    locked_tools = set(tomllib.loads(stage_text).get("tools", {}))
    missing = config_tools - locked_tools
    if missing:
        msg = (
            f"stage lock {stage_lock.name} is missing tools "
            f"(refusing to collect): {sorted(missing)}"
        )
        raise ValueError(msg)
    # What is about to be written, not what the stage holds: the committed file
    # is provenance-stripped, so comparing raw stage text would measure the
    # stripping rather than the coverage.
    candidate = strip_provenance(stage_text)
    # ``committed`` is the git-tracked bytes, never the working tree — a regen
    # that already overwrote the file would otherwise be compared against its
    # own damage and certified clean.
    # Bounded to the OS families the image config declares: the committed image
    # locks carry macOS entries the image can never satisfy, and dropping those
    # is the FIX (they made every regen demand `conda:linux-perf` for
    # `macos-x64`). Within linux the guard keeps its full #370 strength.
    lost = (
        regressions(committed, candidate, families=families)
        if committed is not None
        else []
    )
    if lost:
        detail = "; ".join(lost)
        msg = (
            f"stage lock {stage_lock.name} LOST platform coverage relative to "
            f"the committed {dest.name} (refusing to collect): {detail}. The "
            f"usual cause is regenerating on macOS — mise cannot write the "
            f"linux conda entries there (jdx/mise#7700), and the tool count "
            f"does not move, so this is invisible to a tool-only check (#648). "
            f"Regenerate on a linux host of the image's architecture."
        )
        raise ValueError(msg)
    dest.write_text(candidate)


def strip_provenance(lock_text: str) -> str:
    """Drop provenance entries so the lock matches the image's verification.

    The image intentionally disables attestation verification
    (`github_attestations = false` / `slsa = false` in mise-system.toml —
    no reliable token in buildkit, #160 T7 decision 16), but `mise lock`
    2026.7.0 records provenance regardless of those settings (empirically
    verified: stripped entries are re-recorded on the next pass), and
    `mise install --locked` fail-closes when the lock requires provenance
    the settings won't verify (jdx/mise#10694 downgrade-attack guard).
    Producer-side normalization keeps the committed image locks consistent
    with the consumer's settings. Host locks (mise.lock,
    .config/mise/mise.lock) keep their provenance — hosts verify.

    Raises:
        ValueError: when a provenance key survives the strip (format
            drift in a future mise lock schema — fail loud, never land a
            lock the image build would reject).
    """
    lines = lock_text.splitlines(keepends=True)
    out: list[str] = []
    in_provenance_table = False
    for line in lines:
        if line.startswith("["):
            in_provenance_table = ".provenance" in line or '"provenance' in line
        if in_provenance_table or line.startswith("provenance = "):
            continue
        out.append(line)
    stripped = "".join(out)
    if _has_provenance_key(tomllib.loads(stripped)):
        msg = "provenance key survived strip — mise.lock schema drifted"
        raise ValueError(msg)
    return stripped


def _has_provenance_key(node: object) -> bool:
    if isinstance(node, dict):
        return any(
            key == "provenance" or _has_provenance_key(value)
            for key, value in node.items()
        )
    if isinstance(node, list):
        return any(_has_provenance_key(item) for item in node)
    return False


def merged_system_config(repo_root: Path) -> dict[str, object]:
    """Return the image's merged BASE config tools table (system + shared).

    Name -> pin value (a version string or a `{version = ..., ...}` table).
    `shared.toml` is spread last so a tool declared in both wins from the
    shared fragment, matching how the image merges `conf.d/` over the system
    `config.toml`. The name-only view (`merged_system_config_tools`) and the
    version-drift gate both read from this one merge.
    """
    system = tomllib.loads((repo_root / _SYSTEM_TOML).read_text()).get("tools", {})
    shared = tomllib.loads((repo_root / _SHARED_TOML).read_text()).get("tools", {})
    return {**system, **shared}


def merged_system_config_tools(repo_root: Path) -> set[str]:
    """Return the tool keys of the image's merged BASE config (system + shared)."""
    return set(merged_system_config(repo_root))


def runtime_config_tools(repo_root: Path) -> set[str]:
    """Return the tool keys of the runtime tier config (#160 T9)."""
    runtime = tomllib.loads((repo_root / _RUNTIME_TOML).read_text())
    return set(runtime.get("tools", {}))
