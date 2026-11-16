import shlex
import sys
from pathlib import Path

import anyio
import pytest

from p2996 import build, config, proc
from p2996.log import P2996Error
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


async def test_jobs_overrides_the_job_count_for_one_run(
    cfg: Config, recipe: Recipe, upstream: Upstream, patches: Path, logs: pytest.CaptureFixture[str]
) -> None:
    await recipe.source(git(upstream.path, "rev-parse", "HEAD"))
    await build.run(cfg, Build(dry_run=True, jobs=cfg.jobs + 2), patches)
    [dry] = events(logs)[0]
    assert dry["compile"].endswith(f" --parallel {cfg.jobs + 2}")


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
    assert "LLDB_USE_SYSTEM_DEBUGSERVER:BOOL=OFF\n" in cache
    assert f"LLDB_CODESIGN_IDENTITY:STRING={cfg.codesign}\n" in cache
    assert "LLVM_INSTALL_UTILS:BOOL=ON\n" in cache
    assert (built / "tiny").is_file()


@pytest.mark.parametrize(
    "identity",
    [
        "p2996 no such certificate",
        # A certificate with no private key beside it: an interrupted setup leaves this.
        "Apple Root CA",
    ],
)
async def test_build_stops_before_configure_when_the_codesign_identity_cannot_sign(
    cfg: Config, recipe: Recipe, upstream: Upstream, identity: str
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    await recipe.source(head)
    unusable = cfg.model_copy(update={"codesign": identity})
    with pytest.raises(P2996Error, match=rf"{identity} in .* cannot sign; .*macos-setup-codesign\.sh"):
        await build.run(unusable, Build(commit=head), recipe.patches)
    assert not (config.build_tree(cfg) / "CMakeCache.txt").exists()


async def test_build_prepares_the_commit_it_is_given(recipe: Recipe, upstream: Upstream) -> None:
    old = upstream.write("a.txt", "old\n")
    upstream.write("a.txt", "new\n")
    assert (await recipe.build(old))["commit"] == old


def test_the_libpython_rpath_names_the_major_minor_link_that_holds_the_same_library(tmp_path: Path) -> None:
    hashed = tmp_path / "python-abc123" / "lib"
    hashed.mkdir(parents=True)
    (hashed / "libpython3.15.dylib").write_bytes(b"lib")
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "3.15").symlink_to("../python-abc123")
    assert build.python_libdir(hashed, "libpython3.15.dylib", "3.15") == tmp_path / "python" / "3.15" / "lib"


def test_the_libpython_rpath_keeps_libdir_when_the_link_holds_another_library(tmp_path: Path) -> None:
    hashed = tmp_path / "python-abc123" / "lib"
    other = tmp_path / "python" / "3.15" / "lib"
    for folder in (hashed, other):
        folder.mkdir(parents=True)
        (folder / "libpython3.15.dylib").write_bytes(b"lib")
    assert build.python_libdir(hashed, "libpython3.15.dylib", "3.15") == hashed
    assert build.python_libdir(hashed, "libpython3.15.dylib", "3.16") == hashed


async def test_include_what_you_use_is_configured_as_an_external_project(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    await recipe.ship(upstream.release("v1"))
    cache = (config.build_tree(cfg) / "CMakeCache.txt").read_text()
    assert "LLVM_EXTERNAL_PROJECTS:STRING=iwyu\n" in cache
    # Builtin headers from the installed prefix, not from the build tree the next commit reuses.
    assert "IWYU_RESOURCE_RELATIVE_TO:STRING=iwyu\n" in cache
    assert f"LLVM_EXTERNAL_IWYU_SOURCE_DIR:PATH={config.iwyu_checkout(cfg)}\n" in cache


async def test_a_compile_sccache_failed_to_zip_runs_once_more_and_the_build_finishes(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    await recipe.source(upstream.release("v1", zip_failures=1))
    await build.run(cfg, Build(), recipe.patches)
    out, [retry] = events(recipe.logs)
    assert (retry["level"], retry["event"]) == ("warning", "compile retry")
    assert retry["code"] != 0
    assert retry["reason"] == "failed to zip up compiler outputs"
    assert out[-1]["event"] == "build done"
    assert (config.build_tree(cfg) / "zip-failure.count").read_text() == "2\n"
    # The log holds the newest run: the retry that passed, not the failure before it.
    log_text = config.build_log(cfg).read_text()
    assert "zip-failure" in log_text
    assert "failed to zip up" not in log_text


async def test_a_second_zip_failure_fails_the_build_after_one_retry(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    head = upstream.release("v1", zip_failures=2)
    await recipe.source(head)
    with pytest.raises(P2996Error, match=f"{head} with include-what-you-use .* failed to compile"):
        await build.run(cfg, Build(), recipe.patches)
    assert [event["event"] for event in events(recipe.logs)[1]] == ["compile retry"]
    assert (config.build_tree(cfg) / "zip-failure.count").read_text() == "2\n"
    assert not config.last_build(cfg).exists()


async def test_any_other_compile_failure_is_not_retried(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    await recipe.source(upstream.release("v1", fail=True))
    with pytest.raises(P2996Error, match="failed to compile"):
        await build.run(cfg, Build(), recipe.patches)
    assert events(recipe.logs)[1] == []
