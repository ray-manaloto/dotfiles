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


def test_identity_follows_the_commit_and_the_recipe(tmp_path: Path) -> None:
    patches, bootstrap = tmp_path / "patches", tmp_path / "bootstrap.cmake"
    patches.mkdir()
    (patches / "a.patch").write_text("one\n")
    bootstrap.write_text("set(A 1)\n")
    first = config.identity("a" * 40, patches, bootstrap)
    assert first.startswith("a" * 40 + "-")
    assert config.identity("a" * 40, patches, bootstrap) == first
    assert config.identity("b" * 40, patches, bootstrap) != first
    (patches / "a.patch").write_text("two\n")
    second = config.identity("a" * 40, patches, bootstrap)
    assert second != first
    bootstrap.write_text("set(A 2)\n")
    assert config.identity("a" * 40, patches, bootstrap) != second
