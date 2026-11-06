"""The map store: <store>/<dep>/.repo.git, and per version a worktree, its cbm map and manifest.json."""

import json
import re
import shutil
from pathlib import Path

from pydantic import ValidationError

from . import cbm
from .events import DepmapsError
from .git import commit, git
from .models import Config, Dep, ErrorCode, Manifest


def bare(cfg: Config, name: str) -> Path:
    # A version starts with a letter or digit (registry.VERSION), so no version folder, in any case, is this one.
    return cfg.store / name / ".repo.git"


def folder(cfg: Config, name: str, version: str) -> Path:
    return cfg.store / name / version


def manifest(cfg: Config, name: str, version: str) -> Manifest | None:
    """The version's manifest, or None when it has no map. A manifest that can't be read, isn't valid or
    names another map is an invalid_manifest error, never taken for a missing one."""
    path = folder(cfg, name, version) / "manifest.json"
    if not path.exists():
        return None
    try:
        found = Manifest.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as error:
        raise DepmapsError(ErrorCode.invalid_manifest, f"depmaps: {path}: {error}") from None
    if (found.dep, found.version) != (name, version):
        message = f"depmaps: {path} is the map of {found.dep} {found.version}"
        raise DepmapsError(ErrorCode.invalid_manifest, message)
    return found


def mapped(cfg: Config, name: str, version: str) -> bool:
    """The version has its manifest and its cbm map: cbm's cache can lose a map the store still lists."""
    found = manifest(cfg, name, version)
    return found is not None and cbm.database(found.project).exists()


def order(version: str) -> list[str | int]:
    """A version's sort key: its runs of digits as numbers, so 2026.11.10 follows 2026.11.9.

    re.split with a group puts the text runs at even places and the digit runs at odd ones, so two keys
    compare text with text and number with number.
    """
    return [int(part) if index % 2 else part for index, part in enumerate(re.split(r"(\d+)", version))]


def maps(cfg: Config, name: str) -> list[Manifest]:
    """Every map of the dependency, oldest version first, whatever order they were built in."""
    found = [
        each
        for child in (cfg.store / name).glob("*/manifest.json")
        if (each := manifest(cfg, name, child.parent.name)) is not None  # None: removed since the glob
    ]
    return sorted(found, key=lambda each: order(each.version))


def remove(cfg: Config, name: str, version: str) -> None:
    """Delete the cbm project, the worktree and the folder (manifest.json last, so a failure leaves it listed)."""
    target = folder(cfg, name, version)
    cbm.delete(cfg, f"{name}-v{version}")
    if (target / "src").exists():
        git("worktree", "remove", "--force", target / "src", cwd=bare(cfg, name))
    shutil.rmtree(target)


def build(cfg: Config, name: str, dep: Dep, version: str) -> Manifest:
    tag = dep.tag.replace("{version}", version)
    sha = commit(dep.repo, bare(cfg, name), tag)
    target = folder(cfg, name, version)
    if target.exists():  # an earlier map, or one cut short: rebuild it from nothing
        remove(cfg, name, version)
    target.mkdir(parents=True)
    source = target / "src"
    # A worktree folder deleted by hand stays registered, and add refuses its path until pruned.
    git("worktree", "prune", cwd=bare(cfg, name))
    git("worktree", "add", "--detach", "--quiet", source, sha, cwd=bare(cfg, name))
    project = f"{name}-v{version}"
    cbm_version = cbm.version(cfg)
    cbm.index(cfg, source, project)
    artifact = json.loads((source / ".codebase-memory/artifact.json").read_text())
    made = Manifest(
        dep=name, version=version, tag=tag, commit=sha, project=project, cbm_version=cbm_version,
        schema_version=artifact["schema_version"], indexed_at=artifact["indexed_at"],
        nodes=artifact["nodes"], edges=artifact["edges"],
    )  # fmt: skip
    (target / "manifest.json").write_text(made.model_dump_json(indent=2) + "\n")
    return made


def prune(cfg: Config, name: str, pinned: str) -> list[str]:
    """Keep the pinned version and the highest version below it; remove the rest, oldest first. A map
    newer than the pin, left by a pin moved back, goes too."""
    versions = [each.version for each in maps(cfg, name)]
    below = [version for version in versions if order(version) < order(pinned)]
    keep = {pinned, *below[-1:]}
    gone = [version for version in versions if version not in keep]
    for version in gone:
        remove(cfg, name, version)
    return gone
