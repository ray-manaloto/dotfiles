import shlex
import sys
from pathlib import Path

import anyio
import pytest

from p2996 import build, config, proc
from p2996.models import Build, Config

from .conftest import Recipe, Upstream, events, git

pytestmark = pytest.mark.anyio


def option(command: str, name: str) -> str:
    """The value after name in a logged command line."""
    parts = shlex.split(command)
    return parts[parts.index(name) + 1]


async def test_build_compiles_through_sccache(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    await recipe.ship(upstream.release("v1"))
    cache = (config.build_tree(cfg) / "CMakeCache.txt").read_text()
    sccache = await proc.output("mise", "which", "sccache")
    assert f"CMAKE_C_COMPILER_LAUNCHER:STRING={sccache}\n" in cache
    assert f"CMAKE_CXX_COMPILER_LAUNCHER:STRING={sccache}\n" in cache


async def test_dry_run_logs_both_cmake_commands(
    cfg: Config, recipe: Recipe, upstream: Upstream, patches: Path, logs: pytest.CaptureFixture[str]
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    checkout = (await recipe.source(head))["checkout"]
    await build.run(cfg, Build(dry_run=True), patches)
    [dry] = events(logs)[0]
    assert dry["event"] == "build dry run"
    assert dry["P2996_SDK"].startswith("/")
    lua = await proc.output("mise", "where", "lua")
    assert dry["LUA_DIR"] == lua
    assert (Path(lua) / "include/lua.h").is_file()
    assert f"-C {config.RESOURCES / 'bootstrap.cmake'}" in dry["configure"]
    assert option(dry["configure"], "-S") == f"{checkout}/llvm"
    assert f"-DCMAKE_INSTALL_PREFIX={cfg.root / 'current'}" in dry["configure"]
    assert f"-DPython3_EXECUTABLE={sys.executable}" in dry["configure"]
    built = option(dry["configure"], "-B")
    assert dry["compile"] == f"cmake --build {built} --parallel {cfg.jobs}"
    assert not await anyio.Path(built).exists()


async def test_the_job_count_reaches_the_compile_pool(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    await recipe.ship(upstream.release("v1"))
    cache = (config.build_tree(cfg) / "CMakeCache.txt").read_text()
    assert f"LLVM_PARALLEL_COMPILE_JOBS:STRING={cfg.jobs}\n" in cache


async def test_zstd_is_linked_statically_from_the_managed_tool(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    await recipe.ship(upstream.release("v1"))
    cache = (config.build_tree(cfg) / "CMakeCache.txt").read_text()
    managed = Path(await proc.output("mise", "where", "conda:zstd-static"))
    assert "LLVM_ENABLE_ZSTD:STRING=FORCE_ON\n" in cache
    assert "LLVM_USE_STATIC_ZSTD:BOOL=ON\n" in cache
    assert f"zstd_LIBRARY:FILEPATH={managed}/lib/libzstd.a\n" in cache
    assert f"zstd_STATIC_LIBRARY:FILEPATH={managed}/lib/libzstd.a\n" in cache
    assert f"zstd_INCLUDE_DIR:PATH={managed}/include\n" in cache
    assert (managed / "lib/libzstd.a").is_file()
    assert (managed / "include/zstd.h").is_file()


async def test_version_names_the_remote_the_source_came_from(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    await recipe.ship(upstream.release("v1"))
    assert f"CLANG_REPOSITORY_STRING:STRING={cfg.remote}\n" in (config.build_tree(cfg) / "CMakeCache.txt").read_text()


async def test_build_configures_with_the_real_bootstrap_cache_and_compiles(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    await recipe.source(head)
    built = Path((await recipe.build(head))["build"])
    cache = (built / "CMakeCache.txt").read_text()
    assert "CMAKE_OSX_DEPLOYMENT_TARGET:STRING=27.0" in cache
    assert f"CMAKE_INSTALL_PREFIX:PATH={cfg.root / 'current'}\n" in cache
    assert (built / "tiny").is_file()


async def test_build_prepares_the_commit_it_is_given(recipe: Recipe, upstream: Upstream) -> None:
    old = upstream.write("a.txt", "old\n")
    upstream.write("a.txt", "new\n")
    assert (await recipe.build(old))["commit"] == old
