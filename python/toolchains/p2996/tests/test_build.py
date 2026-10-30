import fcntl
import subprocess
import sys
from pathlib import Path

import pytest

from p2996 import build, config, source
from p2996.models import Config


def test_dry_run_prints_both_cmake_commands(cfg: Config, patches: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source.run(cfg, None, patches)
    capsys.readouterr()
    build.run(cfg, dry_run=True)
    configure, compile_ = capsys.readouterr().out.splitlines()
    assert configure.startswith("P2996_SDK=/")
    lua = subprocess.run(["mise", "where", "lua"], check=True, capture_output=True, text=True).stdout.strip()
    assert f" LUA_DIR={lua} " in configure
    assert (Path(lua) / "include/lua.h").is_file()
    assert f"-C {config.RESOURCES / 'bootstrap.cmake'}" in configure
    assert f"-DCMAKE_INSTALL_PREFIX={config.prefix(cfg)}" in configure
    assert f"-DPython3_EXECUTABLE={sys.executable}" in configure
    assert compile_ == f"cmake --build {config.build_dir(cfg)} --parallel 4"
    assert not config.build_dir(cfg).exists()


def test_build_configures_with_the_real_bootstrap_cache_and_compiles(cfg: Config, patches: Path) -> None:
    source.run(cfg, None, patches)
    build.run(cfg, dry_run=False)
    cache = (config.build_dir(cfg) / "CMakeCache.txt").read_text()
    assert "CMAKE_OSX_DEPLOYMENT_TARGET:STRING=27.0" in cache
    assert f"CMAKE_INSTALL_PREFIX:PATH={config.prefix(cfg)}" in cache
    assert (config.build_dir(cfg) / "tiny").is_file()


def test_build_refuses_while_another_heavy_build_holds_the_lock(cfg: Config, patches: Path) -> None:
    source.run(cfg, None, patches)
    lock = Path(cfg.lock)
    lock.parent.mkdir(parents=True)
    with lock.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(SystemExit, match="another heavy build holds the lock"):
            build.run(cfg, dry_run=False)
    assert not config.build_dir(cfg).exists()
