import threading
from concurrent.futures import ThreadPoolExecutor
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
    "P2996_JOBS": "8",
}


def test_load_reads_one_variable_per_field() -> None:
    assert config.load({**ENVIRON, "UNRELATED": "ignored"}) == Config.model_validate(
        {
            "remote": "https://example.invalid/p2996.git",
            "branch": "p2996",
            "root": Path("/opt/p2996"),
            "cache": Path("/var/cache/p2996"),
            "jobs": 8,
        }
    )


def test_load_names_every_missing_variable() -> None:
    with pytest.raises(P2996Error, match=r"p2996: P2996_ROOT, P2996_CACHE, P2996_JOBS unset"):
        config.load({"P2996_REMOTE": "r", "P2996_BRANCH": "b"})


def test_paths_follow_root_and_cache(cfg: Config) -> None:
    assert config.src(cfg) == cfg.cache / "source"
    assert config.build_dir(cfg) == cfg.cache / "build"
    assert config.bin_dir(cfg) == cfg.root / "bin"


def test_link_replaces_the_old_link_with_no_gap_and_leaves_nothing_else(tmp_path: Path) -> None:
    link = tmp_path / "current"
    config.link(link, "a")
    started, done = threading.Event(), threading.Event()

    def reader() -> int:
        reads = 0
        while not done.is_set():
            assert str(link.readlink()) in ("a", "b")  # FileNotFoundError here means a gap.
            reads += 1
            started.set()
        return reads

    with ThreadPoolExecutor(1) as pool:
        reading = pool.submit(reader)
        assert started.wait(10)
        try:
            for turn in range(2000):
                config.link(link, "ab"[turn % 2])
        finally:
            done.set()
        assert reading.result() > 0
    assert link.readlink() == Path("b")
    assert [path.name for path in tmp_path.iterdir()] == ["current"]
