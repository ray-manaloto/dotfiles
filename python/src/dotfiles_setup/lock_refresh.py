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

The staging layout mirrors how the repo root already merges its own config
(project ``mise.toml`` + ``.config/mise/conf.d/*.toml`` share ONE
``mise.lock``), so no TOML rewriting is needed — byte copies only:

    <stage>/mise.toml                        <- .devcontainer/mise-system.toml
    <stage>/.config/mise/conf.d/shared.toml  <- .config/mise/conf.d/shared.toml
    <stage>/mise.lock                        <- .devcontainer/mise-system.lock

Seeding the committed lock lets repeated `mise lock` runs converge under
GitHub rate limits instead of starting cold each time.
"""

from __future__ import annotations

import re
import shutil
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_MISE_VERSION_RE = re.compile(r"^ARG MISE_VERSION=(\S+)$", re.MULTILINE)
_SYSTEM_TOML = ".devcontainer/mise-system.toml"
_SYSTEM_LOCK = ".devcontainer/mise-system.lock"
_SHARED_TOML = ".config/mise/conf.d/shared.toml"


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

    Byte-copies the system config, the shared conf.d fragment, and the
    committed lock (as the convergence seed) into ``stage_dir`` using the
    project-layout paths mise merges natively.

    Returns:
        The pinned MISE_VERSION the caller must run `mise lock` with.
    """
    version = pinned_mise_version(repo_root / ".devcontainer" / "Dockerfile")
    conf_d = stage_dir / ".config" / "mise" / "conf.d"
    conf_d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(repo_root / _SYSTEM_TOML, stage_dir / "mise.toml")
    shutil.copyfile(repo_root / _SHARED_TOML, conf_d / "shared.toml")
    shutil.copyfile(repo_root / _SYSTEM_LOCK, stage_dir / "mise.lock")
    return version


def collect_system_lock(repo_root: Path, stage_dir: Path) -> None:
    """Copy the regenerated stage lock back to `.devcontainer/mise-system.lock`.

    Validates before writing: the stage lock must parse as TOML and cover
    every tool of the merged config — a truncated or partial lock (rate
    limits, interrupted run) must never overwrite the committed one.

    Raises:
        ValueError: when the stage lock is missing tools from the config.
    """
    stage_lock = stage_dir / "mise.lock"
    locked_tools = set(tomllib.loads(stage_lock.read_text()).get("tools", {}))
    config_tools = merged_system_config_tools(repo_root)
    missing = config_tools - locked_tools
    if missing:
        msg = f"stage lock is missing tools (refusing to collect): {sorted(missing)}"
        raise ValueError(msg)
    shutil.copyfile(stage_lock, repo_root / _SYSTEM_LOCK)


def merged_system_config_tools(repo_root: Path) -> set[str]:
    """Return the tool keys of the image's merged config (system + shared)."""
    system = tomllib.loads((repo_root / _SYSTEM_TOML).read_text())
    shared = tomllib.loads((repo_root / _SHARED_TOML).read_text())
    return set(system.get("tools", {})) | set(shared.get("tools", {}))
