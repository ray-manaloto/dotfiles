from pathlib import Path

import pytest

from p2996 import config
from p2996.log import P2996Error
from p2996.models import Config

ENVIRON = {
    "P2996_REMOTE": "https://example.invalid/p2996.git",
    "P2996_BRANCH": "p2996",
    "P2996_ROOT": "/opt/p2996",
    "P2996_CACHE": "/var/cache/p2996",
}


def test_load_reads_one_variable_per_field() -> None:
    assert config.load({**ENVIRON, "UNRELATED": "ignored"}) == Config.model_validate(
        {
            "remote": "https://example.invalid/p2996.git",
            "branch": "p2996",
            "root": Path("/opt/p2996"),
            "cache": Path("/var/cache/p2996"),
        }
    )


def test_load_names_every_missing_variable() -> None:
    with pytest.raises(P2996Error, match=r"p2996: P2996_ROOT, P2996_CACHE unset"):
        config.load({"P2996_REMOTE": "r", "P2996_BRANCH": "b"})


def test_paths_follow_root_and_cache(cfg: Config) -> None:
    assert config.src(cfg) == cfg.cache / "source"
    assert config.build_dir(cfg) == cfg.cache / "build"
    assert config.bin_dir(cfg) == cfg.root / "bin"
