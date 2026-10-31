import shlex
import sys
from pathlib import Path

import anyio
import pytest

from p2996 import build, config, proc
from p2996.models import Build, Config

from .conftest import Recipe, Upstream, events, git, tree

pytestmark = pytest.mark.anyio


def option(command: str, name: str) -> str:
    """The value after name in a logged command line."""
    parts = shlex.split(command)
    return parts[parts.index(name) + 1]


async def test_dry_run_logs_both_cmake_commands(
    cfg: Config, recipe: Recipe, upstream: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    checkout = (await recipe.source(head))["checkout"]
    await build.run(cfg, Build(dry_run=True))
    [dry] = events(logs)[0]
    assert dry["event"] == "build dry run"
    assert dry["P2996_SDK"].startswith("/")
    lua = await proc.output("mise", "where", "lua")
    assert dry["LUA_DIR"] == lua
    assert (Path(lua) / "include/lua.h").is_file()
    assert f"-C {config.RESOURCES / 'bootstrap.cmake'}" in dry["configure"]
    assert option(dry["configure"], "-S") == f"{checkout}/llvm"
    assert f"-DCMAKE_INSTALL_PREFIX={cfg.root / head}" in dry["configure"]
    assert f"-DPython3_EXECUTABLE={sys.executable}" in dry["configure"]
    built = option(dry["configure"], "-B")
    assert dry["compile"] == f"cmake --build {built} --parallel 4"
    assert not await anyio.Path(built).exists()


async def test_build_configures_with_the_real_bootstrap_cache_and_compiles(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    await recipe.source(head)
    built = Path((await recipe.build(head))["build"])
    cache = (built / "CMakeCache.txt").read_text()
    assert "CMAKE_OSX_DEPLOYMENT_TARGET:STRING=27.0" in cache
    assert f"CMAKE_INSTALL_PREFIX:PATH={cfg.root / head}" in cache
    assert (built / "tiny").is_file()


async def test_two_commits_build_in_separate_trees(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    old = upstream.release("v1")
    head = upstream.release("v2")
    old_checkout = (await recipe.source(old))["checkout"]
    head_checkout = (await recipe.source(head))["checkout"]
    # Built after the newer commit was prepared: the build follows its argument, not the last source.
    old_done = await recipe.build(old)
    old_tree = Path(old_done["build"])
    before = tree(old_tree)

    head_done = await recipe.build(head)
    head_tree = Path(head_done["build"])

    assert head_tree != old_tree
    assert tree(old_tree) == before
    assert (old_done.get("commit"), head_done.get("commit")) == (old, head)
    assert f"CMAKE_HOME_DIRECTORY:INTERNAL={old_checkout}/llvm" in (old_tree / "CMakeCache.txt").read_text()
    assert f"CMAKE_HOME_DIRECTORY:INTERNAL={head_checkout}/llvm" in (head_tree / "CMakeCache.txt").read_text()
    assert f"CMAKE_INSTALL_PREFIX:PATH={cfg.root / old}" in (old_tree / "CMakeCache.txt").read_text()
    assert f"CMAKE_INSTALL_PREFIX:PATH={cfg.root / head}" in (head_tree / "CMakeCache.txt").read_text()
