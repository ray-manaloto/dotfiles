"""The generated Config, loaded from the [env] of this project's mise.toml, and the paths it implies."""

import os
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from . import proc
from .log import P2996Error
from .models import Config

# bootstrap.cmake, patches/, reflection.cpp and review-log.md sit beside the modules.
RESOURCES = Path(__file__).parent
PROJECT = RESOURCES.parents[1]


def load(environ: Mapping[str, str] = os.environ) -> Config:
    """Field <name> comes from P2996_<NAME>."""
    names = {field: f"P2996_{field.upper()}" for field in Config.model_fields}
    if missing := [name for name in names.values() if name not in environ]:
        msg = f"p2996: {', '.join(missing)} unset; run the p2996 tasks through mise"
        raise P2996Error(msg)
    return Config.model_validate({field: environ[name] for field, name in names.items()})


def src(cfg: Config) -> Path:
    return cfg.cache / "source"


def checkout(cfg: Config, commit: str) -> Path:
    """One prepared tree per commit; it appears whole, by rename, and never changes after that."""
    return src(cfg) / commit


def build_dir(cfg: Config) -> Path:
    return cfg.cache / "build"


def build_tree(cfg: Config, commit: str) -> Path:
    return build_dir(cfg) / commit


def last_build(cfg: Config) -> Path:
    """Link to the newest successful build; clean removes it with the rest of build_dir."""
    return build_dir(cfg) / "last"


def bin_dir(cfg: Config) -> Path:
    return cfg.root / "bin"


def link(path: Path, target: str) -> None:
    """Point path at target in one rename, whatever link was there."""
    new = path.with_name(f".{path.name}.{uuid4().hex}")
    new.symlink_to(target)
    new.replace(path)


async def git(repo: Path, *args: str) -> str:
    return await proc.output("git", "-C", repo, *args)
