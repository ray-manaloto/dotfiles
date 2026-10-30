from pathlib import Path

import pytest

from p2996 import config
from p2996.log import P2996Error
from p2996.models import Config

from .conftest import Upstream, git

pytestmark = pytest.mark.anyio


def test_load_reads_one_variable_per_field() -> None:
    environ = {
        "P2996_REMOTE": "https://example.invalid/p2996.git",
        "P2996_BRANCH": "p2996",
        "P2996_ROOT": "/opt/p2996",
        "P2996_CACHE": "/var/cache/p2996",
        "P2996_LOCK": "/var/lock/heavy",
        "UNRELATED": "ignored",
    }
    assert config.load(environ) == Config(
        remote="https://example.invalid/p2996.git",
        branch="p2996",
        root=Path("/opt/p2996"),
        cache=Path("/var/cache/p2996"),
        lock=Path("/var/lock/heavy"),
    )


def test_load_names_every_missing_variable() -> None:
    with pytest.raises(P2996Error, match="P2996_ROOT, P2996_CACHE, P2996_LOCK unset"):
        config.load({"P2996_REMOTE": "r", "P2996_BRANCH": "b"})


def test_paths_follow_root_and_cache(cfg: Config) -> None:
    assert config.src(cfg) == cfg.cache / "source"
    assert config.build_dir(cfg) == cfg.cache / "build"
    assert config.bin_dir(cfg) == cfg.root / "bin"


async def test_prefix_is_named_after_the_checked_out_commit(cfg: Config, upstream: Upstream) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    cfg.cache.mkdir(parents=True)
    git(cfg.cache, "clone", "-q", upstream.url, "source")
    assert await config.commit(cfg) == head
    assert await config.prefix(cfg) == cfg.root / head
