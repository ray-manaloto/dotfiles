# Copyright (c) 2026 Raymond Manaloto
"""Reject a lockfile that LOST platform coverage (#370).

A whole-file re-lock re-resolves for the platform it runs on, and macOS mise
cannot write ``linux-x64`` conda entries (jdx/mise#7700 — the same defect
:mod:`dotfiles_setup.lock_refresh` records in its module docstring for the image
lock, and that ``mise.toml`` cites when os-gating ``conda:ffmpeg``). So a
whole-file re-lock on the Mac host silently strips every linux conda entry from
``mise.lock``. The devcontainer is linux/amd64, so those are exactly the entries
the image needs.

Measured 2026-07-29 on mise 2026.7.16, from a clean checkout, real writes
hash-compared against the committed bytes:

===============================  =======  ==========  =========  ============
action                             conda   linux-x64   checksum   macos-arm64
===============================  =======  ==========  =========  ============
baseline                             962         628       1129            18
``mise lock biome`` (scoped)         962         628       1129            18
``mise install biome``               417          80        584           107
``mise lock`` (bare, no change)      427          80        594           107
``mise lock`` (bare, +1 new tool)    427          84        604           108
===============================  =======  ==========  =========  ============

Three consequences shape this module:

- **BOTH the bare lock and any install are destructive.** Only the *scoped*
  form is safe. ``mise lock --dry-run`` does NOT expose this: it reports
  "would update <tool> for linux-x64" across all 11 platforms and leaves the
  file byte-identical, so it is a probe that can only reassure. The write is
  what had to be measured.
- **The gate targets the ARTIFACT, not a command.** ``auto_install = true``
  means any task can reach the re-lock path, so no command allowlist can bound
  the damage; a check on the committed bytes covers every route into it.
- **It is a REGRESSION check, not a floor.** Absolute counts would need a
  magic number maintained by hand, and would fire on every legitimate tool
  addition or removal. The damage class is specifically *"same tool, fewer
  platforms"*, which only shows up against the committed version.

Adding a tool, removing a tool, and bumping a version all pass. Dropping a
platform from a tool that stayed, or losing a conda platform family, fails.
"""

from __future__ import annotations

import logging
import re
import subprocess
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Every lockfile whose platform coverage is load-bearing. The host pair is what
# a stray `mise install` on this Mac rewrites; the image pair is refreshed by CI
# on linux-x64 (see lock_refresh.py) and must never be re-locked from macOS.
LOCKFILES: tuple[str, ...] = (
    "mise.lock",
    ".config/mise/mise.lock",
    ".devcontainer/mise-system.lock",
    ".devcontainer/mise-runtime.lock",
)

# `[tools.<name>."platforms.<platform>"]` — the tool name is bare or quoted
# (backend-qualified names like `aqua:jackchuka/mdschema` are quoted).
_TOOL_PLATFORM_RE = re.compile(
    r'^\[tools\.(?P<name>"[^"]+"|[^.\]]+)\."platforms\.(?P<platform>[^"]+)"\]',
    re.MULTILINE,
)
# `[conda-packages.<platform>.<package>]` — the conda section is flat per
# platform, and is where the #370 damage lands (137 x 4 linux-x64 variants).
_CONDA_PLATFORM_RE = re.compile(
    r"^\[conda-packages\.(?P<platform>[a-z0-9-]+)\.",
    re.MULTILINE,
)


def tool_platforms(lock_text: str) -> dict[str, set[str]]:
    """Map each locked tool to the set of platforms it has entries for."""
    found: dict[str, set[str]] = {}
    for match in _TOOL_PLATFORM_RE.finditer(lock_text):
        name = match.group("name").strip('"')
        found.setdefault(name, set()).add(match.group("platform"))
    return found


def conda_platforms(lock_text: str) -> set[str]:
    """The platforms the ``[conda-packages]`` section covers."""
    return {m.group("platform") for m in _CONDA_PLATFORM_RE.finditer(lock_text)}


def regressions(committed: str, candidate: str) -> list[str]:
    """Platform coverage lost between the committed and candidate lockfiles.

    Only tools present in BOTH are compared: a tool that was removed
    outright is a legitimate config change, not a coverage regression.
    """
    lost: list[str] = []
    before, after = tool_platforms(committed), tool_platforms(candidate)
    for name in sorted(before.keys() & after.keys()):
        missing = before[name] - after[name]
        if missing:
            lost.append(
                f"tool {name}: lost platform(s) {sorted(missing)} "
                f"({len(before[name])} -> {len(after[name])} entries)"
            )
    conda_missing = conda_platforms(committed) - conda_platforms(candidate)
    if conda_missing:
        lost.append(
            f"[conda-packages]: lost platform(s) {sorted(conda_missing)} — "
            "macOS mise cannot write linux conda entries (jdx/mise#7700), so "
            "this is the signature of a `mise install` run on the host"
        )
    return lost


def committed_text(repo_root: Path, rel_path: str) -> str | None:
    """The lockfile as of ``HEAD``, or None when it is not tracked there."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"HEAD:{rel_path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def check_lockfiles(
    repo_root: Path, lockfiles: tuple[str, ...] = LOCKFILES
) -> list[str]:
    """Findings across every lockfile — empty means no coverage was lost."""
    findings: list[str] = []
    for rel_path in lockfiles:
        path = repo_root / rel_path
        if not path.exists():
            continue
        committed = committed_text(repo_root, rel_path)
        if committed is None:
            # Untracked at HEAD (a brand-new lockfile) — nothing to regress
            # against. Its first commit establishes the baseline.
            logger.debug("%s not tracked at HEAD — skipping", rel_path)
            continue
        findings.extend(
            f"{rel_path}: {finding}"
            for finding in regressions(committed, path.read_text())
        )
    return findings


def main(repo_root: Path, lockfiles: tuple[str, ...] = LOCKFILES) -> int:
    """Exit 1 when any lockfile lost platform coverage relative to HEAD."""
    findings = check_lockfiles(repo_root, lockfiles)
    if not findings:
        logger.info("lock-integrity OK: every lockfile kept its platform coverage")
        return 0
    for finding in findings:
        logger.error("lock-integrity: %s", finding)
    logger.error(
        "A lockfile lost platform coverage. Both a bare `mise lock` and any "
        "`mise install` do this on macOS (#370): they re-lock the whole file "
        "for THIS platform and drop the linux conda entries the amd64 "
        "devcontainer needs. Repair: `git checkout -- <lockfile>` to restore "
        "the committed bytes, then re-lock only what changed with "
        '`mise run lock -- "<backend/name>"` per tool — scoped locking is '
        "measured safe. Verify with this command."
    )
    return 1


def declared_host_tools(repo_root: Path) -> set[str]:
    """Tool keys of the host config — root ``mise.toml`` + the shared fragment.

    These are exactly the strings ``mise lock`` accepts: a key is whatever the
    config wrote, short (``biome``) or backend-qualified
    (``aqua:jackchuka/mdschema``).
    """
    keys: set[str] = set()
    for rel_path in ("mise.toml", ".config/mise/conf.d/shared.toml"):
        path = repo_root / rel_path
        if path.exists():
            keys |= set(tomllib.loads(path.read_text()).get("tools", {}))
    return keys


def scoped_lock_main(repo_root: Path, tools: list[str]) -> int:
    """Re-lock exactly the named tools, then assert coverage held.

    The canonical task refuses the bare form because **bare ``mise lock`` is
    itself destructive** — measured 2026-07-29 on mise 2026.7.16 with every
    tool installed and no config change: conda entries 962 -> 427, ``linux-x64``
    628 -> 80, a 1063/3744 diff. ``mise lock --dry-run`` does NOT reveal this;
    it cheerfully reports "would update <tool> for linux-x64" for all 11
    platforms, so the dry run is a probe that can only reassure.

    Scoped ``mise lock "<backend/name>"`` is the safe form (verified by real
    write: 11 platform entries updated, conda section byte-identical), and a
    tool name must be the FULL backend-qualified key as written in the config —
    a bare short name exits 0 having silently done nothing.
    """
    if not tools:
        logger.error(
            "lock: refusing to run a bare `mise lock` — it re-locks the WHOLE "
            "lockfile for this platform and drops the linux conda entries the "
            "amd64 devcontainer needs (#370; measured linux-x64 628 -> 80). "
            'Name the tool(s) instead: mise run lock -- "aqua:jackchuka/mdschema" '
            "— the FULL backend-qualified key from the config, since a bare "
            "short name exits 0 having done nothing."
        )
        return 1
    # A name mise does not recognise makes `mise lock` exit 0 having done
    # NOTHING (measured: `mise lock definitely:not/a-tool` -> rc 0, empty diff;
    # the same trap fires on a short name for a backend-qualified key, e.g.
    # `mise lock betterleaks`). A silent no-op is indistinguishable from success
    # by exit code alone, so validate against the config before shelling out.
    declared = declared_host_tools(repo_root)
    unknown = [tool for tool in tools if tool not in declared]
    if unknown:
        logger.error(
            "lock: not declared in the host config: %s. `mise lock` exits 0 "
            "without locking anything for a name it does not recognise, so this "
            "would look like success. Use the FULL key as written in mise.toml "
            "/ .config/mise/conf.d/shared.toml.",
            unknown,
        )
        return 1
    for tool in tools:
        result = subprocess.run(
            ["mise", "lock", tool],
            cwd=repo_root,
            check=False,
        )
        if result.returncode != 0:
            logger.error("lock: `mise lock %s` failed (rc=%d)", tool, result.returncode)
            return result.returncode
    return main(repo_root)
