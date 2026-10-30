import fcntl
import sys
from pathlib import Path

import pytest

from p2996 import build, config, proc, source
from p2996.log import P2996Error
from p2996.models import Build, Config, Source

from .conftest import events

pytestmark = pytest.mark.anyio


async def test_dry_run_logs_both_cmake_commands(cfg: Config, patches: Path, logs: pytest.CaptureFixture[str]) -> None:
    await source.run(cfg, Source(), patches)
    logs.readouterr()
    await build.run(cfg, Build(dry_run=True))
    [dry] = events(logs)[0]
    assert dry["event"] == "build dry run"
    assert dry["P2996_SDK"].startswith("/")
    lua = await proc.output("mise", "where", "lua")
    assert dry["LUA_DIR"] == lua
    assert (Path(lua) / "include/lua.h").is_file()
    assert f"-C {config.RESOURCES / 'bootstrap.cmake'}" in dry["configure"]
    assert f"-DCMAKE_INSTALL_PREFIX={await config.prefix(cfg)}" in dry["configure"]
    assert f"-DPython3_EXECUTABLE={sys.executable}" in dry["configure"]
    assert dry["compile"] == f"cmake --build {config.build_dir(cfg)} --parallel 4"
    assert not config.build_dir(cfg).exists()


async def test_build_configures_with_the_real_bootstrap_cache_and_compiles(cfg: Config, patches: Path) -> None:
    await source.run(cfg, Source(), patches)
    await build.run(cfg, Build())
    cache = (config.build_dir(cfg) / "CMakeCache.txt").read_text()
    assert "CMAKE_OSX_DEPLOYMENT_TARGET:STRING=27.0" in cache
    assert f"CMAKE_INSTALL_PREFIX:PATH={await config.prefix(cfg)}" in cache
    assert (config.build_dir(cfg) / "tiny").is_file()


async def test_build_refuses_while_another_heavy_build_holds_the_lock(cfg: Config, patches: Path) -> None:
    await source.run(cfg, Source(), patches)
    cfg.lock.parent.mkdir(parents=True)
    with cfg.lock.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(P2996Error, match="another heavy build holds the lock"):
            await build.run(cfg, Build())
    assert not config.build_dir(cfg).exists()
