"""The generated Config, loaded from the [env] of this project's mise.toml, and the paths it implies."""

import os
from collections.abc import Mapping
from pathlib import Path

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


def build_dir(cfg: Config) -> Path:
    return cfg.cache / "build"


def bin_dir(cfg: Config) -> Path:
    return cfg.root / "bin"


async def commit(cfg: Config) -> str:
    """The commit checked out in the cache; build and install use it, never a fresh lookup."""
    return await git(src(cfg), "rev-parse", "HEAD")


async def prefix(cfg: Config) -> Path:
    return cfg.root / await commit(cfg)


async def git(repo: Path, *args: str) -> str:
    return await proc.output("git", "-C", repo, *args)
