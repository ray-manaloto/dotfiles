"""The generated Config, loaded from the [env] of this project's mise.toml, and the paths it implies."""

import hashlib
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from . import proc
from .log import P2996Error
from .models import Config

# bootstrap.cmake, patches/, reflection.cpp and review-log.md sit beside the modules.
RESOURCES = Path(__file__).parent
PROJECT = RESOURCES.parents[1]
PATCHES = RESOURCES / "patches"
BOOTSTRAP = RESOURCES / "bootstrap.cmake"
BUILD = RESOURCES / "build.py"


def load(environ: Mapping[str, str] = os.environ) -> Config:
    """Field <name> comes from P2996_<NAME>."""
    names = {field: f"P2996_{field.upper()}" for field in Config.model_fields}
    if missing := [name for name in names.values() if name not in environ]:
        msg = f"p2996: {', '.join(missing)} unset; run the p2996 tasks through mise"
        raise P2996Error(msg)
    return Config.model_validate({field: environ[name] for field, name in names.items()})


def identity(commit: str, patches: Path = PATCHES, bootstrap: Path = BOOTSTRAP, script: Path = BUILD) -> str:
    """The commit and a digest of its recipe, so a changed patch, script or python gets new folders."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        msg = f"p2996: {commit} is not a full commit id"
        raise P2996Error(msg)
    digest = hashlib.sha256(sys.version.encode())
    for file in (*sorted(patches.glob("*.patch")), bootstrap, script):
        digest.update(file.name.encode())
        digest.update(file.read_bytes())
    return f"{commit}-{digest.hexdigest()[:12]}"


def src(cfg: Config) -> Path:
    return cfg.cache / "source"


def checkout(cfg: Config, name: str) -> Path:
    """One prepared tree per identity; it appears whole, by rename, and never changes after that."""
    return src(cfg) / name


def build_dir(cfg: Config) -> Path:
    return cfg.cache / "build"


def build_tree(cfg: Config, name: str) -> Path:
    return build_dir(cfg) / name


def last_build(cfg: Config) -> Path:
    """Link to the newest successful build; clean removes it with the rest of build_dir."""
    return build_dir(cfg) / "last"


def finished(cfg: Config, name: str) -> Path:
    """How many builds of an id finished; outside build_dir, so clean does not reuse a prefix."""
    return cfg.cache / "finished" / name


def prefix_name(cfg: Config, name: str) -> str:
    """ROOT/<name> for the first finished build of an id, ROOT/<name>.<n> for the nth."""
    file = finished(cfg, name)
    count = int(file.read_text()) if file.exists() else 1
    return name if count == 1 else f"{name}.{count}"


def started_build(cfg: Config) -> Path:
    """Link to the newest build that started, failed ones too; review-log reads its source tree from it."""
    return build_dir(cfg) / "started"


def bin_dir(cfg: Config) -> Path:
    return cfg.root / "bin"


def link(path: Path, target: str) -> None:
    """Point path at target in one rename, whatever link was there."""
    new = path.with_name(f".{path.name}.{uuid4().hex}")
    new.symlink_to(target)
    new.replace(path)


async def git(repo: Path, *args: str) -> str:
    return await proc.output("git", "-C", repo, *args)
