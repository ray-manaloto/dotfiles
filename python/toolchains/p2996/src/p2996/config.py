"""The generated Config, loaded from the [env] of this project's mise.toml, and the paths it implies."""

import os
import subprocess
from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path

from .models import Config

# bootstrap.cmake, patches/, reflection.cpp and review-log.md sit beside the modules.
RESOURCES = Path(__file__).parent
PROJECT = RESOURCES.parents[1]


def load(environ: Mapping[str, str] = os.environ) -> Config:
    """Field <name> comes from P2996_<NAME>."""
    names = [f"P2996_{field.name.upper()}" for field in fields(Config)]
    if missing := [name for name in names if name not in environ]:
        msg = f"p2996: {', '.join(missing)} unset; run the p2996 tasks through mise"
        raise SystemExit(msg)
    return Config(*(environ[name] for name in names))


def src(cfg: Config) -> Path:
    return Path(cfg.cache) / "source"


def build_dir(cfg: Config) -> Path:
    return Path(cfg.cache) / "build"


def bin_dir(cfg: Config) -> Path:
    return Path(cfg.root) / "bin"


def commit(cfg: Config) -> str:
    """The commit checked out in the cache; build and install use it, never a fresh lookup."""
    return git(src(cfg), "rev-parse", "HEAD")


def prefix(cfg: Config) -> Path:
    return Path(cfg.root) / commit(cfg)


def git(repo: Path, *args: str, check: bool = True) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], check=check, capture_output=True, text=True)
    return done.stdout.strip()
