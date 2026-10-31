"""The build id: what CMake found after configure, in one fixed source and build folder."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import anyio
import pytest

from p2996 import build, config, install, proc, source
from p2996.log import P2996Error
from p2996.models import Build, Config, Install, Source

from .conftest import TINY_CMAKE, Recipe, Upstream, events, git

pytestmark = pytest.mark.anyio

BUILD_ONCE = """
import sys
from pathlib import Path

import anyio

from p2996 import build, config
from p2996.log import configure
from p2996.models import Build

configure()
anyio.run(build.run, config.load(), Build(commit=sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
"""

EXTERNAL_MAIN = """\
cmake_minimum_required(VERSION 3.20)
project(toy NONE)
include(ExternalProject)
ExternalProject_Add(sub
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/sub
  BINARY_DIR ${CMAKE_BINARY_DIR}/runtimes/@FOLDER@
  CMAKE_ARGS ${RUNTIMES_CMAKE_ARGS}
  BUILD_COMMAND ""
  INSTALL_COMMAND "")
"""

EXTERNAL_SUB = """\
cmake_minimum_required(VERSION 3.20)
project(sub NONE)
set(TOY_ABI stable CACHE STRING "")
file(WRITE ${CMAKE_BINARY_DIR}/abi "${TOY_ABI}\\n")
"""

RECORD_COMPILE = 'add_custom_target(record ALL COMMAND sh -c "echo x >> ${CMAKE_BINARY_DIR}/compiled" VERBATIM)\n'


@pytest.fixture
def bootstrap(tmp_path: Path) -> Path:
    file = tmp_path / "bootstrap.cmake"
    file.write_text(config.BOOTSTRAP.read_text())
    return file


class Ids:
    """Runs the real build and returns the id it logged."""

    def __init__(
        self, cfg: Config, patches: Path, bootstrap: Path, upstream: Upstream, logs: pytest.CaptureFixture[str]
    ) -> None:
        self.cfg, self.patches, self.bootstrap, self.logs = cfg, patches, bootstrap, logs
        self.commit = git(upstream.path, "rev-parse", "HEAD")

    async def event(self, commit: str | None = None) -> dict:
        await build.run(self.cfg, Build(commit=commit or self.commit), self.patches, self.bootstrap)
        return [e for e in events(self.logs)[0] if e["event"] in ("build done", "build skipped")][-1]

    async def id(self, commit: str | None = None) -> str:
        return (await self.event(commit))["id"]

    def add(self, line: str) -> None:
        with self.bootstrap.open("a") as file:
            file.write(f"{line}\n")


@pytest.fixture
def ids(cfg: Config, patches: Path, bootstrap: Path, upstream: Upstream, logs: pytest.CaptureFixture[str]) -> Ids:
    return Ids(cfg, patches, bootstrap, upstream, logs)


async def test_two_commits_share_one_source_and_build_folder(cfg: Config, ids: Ids, upstream: Upstream) -> None:
    first = await ids.event(upstream.release("v1"))
    cache = (cfg.cache / "build/work/CMakeCache.txt").read_text()
    second = await ids.event(upstream.release("v2"))
    assert first["id"] != second["id"]
    assert first["build"] == second["build"] == str(cfg.cache / "build/work")
    assert (cfg.cache / "source/work/.git").exists()
    prefix = next(line for line in cache.splitlines() if line.startswith("CMAKE_INSTALL_PREFIX:"))
    assert prefix in (cfg.cache / "build/work/CMakeCache.txt").read_text()


async def test_a_comment_in_the_recipe_keeps_the_id(ids: Ids) -> None:
    before = await ids.id()
    ids.add("# Only a comment.")
    assert await ids.id() == before


async def test_a_changed_setting_changes_the_id(ids: Ids) -> None:
    before = await ids.id()
    ids.add('set(P2996_TEST_SETTING ON CACHE BOOL "" FORCE)')
    assert await ids.id() != before


async def test_an_outside_tool_replaced_in_place_changes_the_id(ids: Ids, tmp_path: Path) -> None:
    tool = tmp_path / "tools/lua"
    tool.parent.mkdir()
    tool.write_text("5.4\n")
    ids.add(f'set(LUA_EXECUTABLE "{tool}" CACHE FILEPATH "" FORCE)')
    before = await ids.id()
    tool.write_text("5.5\n")
    assert await ids.id() != before


async def test_the_same_tool_at_another_path_keeps_the_id(ids: Ids, tmp_path: Path) -> None:
    one, two = tmp_path / "one/lua", tmp_path / "two/lua"
    for file in (one, two):
        file.parent.mkdir()
        file.write_text("5.5\n")
    ids.add(f'set(LUA_EXECUTABLE "{one}" CACHE FILEPATH "" FORCE)')
    before = await ids.id()
    ids.bootstrap.write_text(ids.bootstrap.read_text().replace(str(one), str(two)))
    assert await ids.id() == before


async def test_a_file_cmake_read_outside_the_source_counts_by_content(
    ids: Ids, upstream: Upstream, tmp_path: Path
) -> None:
    extra = tmp_path / "extra.cmake"
    extra.write_text("# one\n")
    commit = upstream.write("llvm/CMakeLists.txt", TINY_CMAKE + f'include("{extra}")\n')
    before = await ids.id(commit)
    extra.write_text("# two\n")
    assert await ids.id(commit) != before


async def test_the_launcher_and_job_counts_do_not_change_the_id(ids: Ids) -> None:
    before = await ids.id()
    ids.add('set(CMAKE_C_COMPILER_LAUNCHER "" CACHE STRING "" FORCE)')
    ids.add('set(LLVM_PARALLEL_COMPILE_JOBS 8 CACHE STRING "" FORCE)')
    assert await ids.id() == before


async def test_two_project_paths_give_the_same_id(
    cfg: Config, ids: Ids, patches: Path, bootstrap: Path, tmp_path: Path
) -> None:
    # Two worktrees: their own venv path and nanobind folder, one interpreter, one uv.lock. Each is a
    # real process running its own copy of the package.
    ids.add('set(NB_DIR "$ENV{P2996_TEST_PROJECT}/.venv/lib" CACHE INTERNAL "" FORCE)')
    interpreter = await anyio.Path(sys.executable).resolve()
    site = next(path for path in sys.path if path.endswith("site-packages"))
    settings = {f"P2996_{name.upper()}": str(value) for name, value in cfg.model_dump().items()}
    found = []
    for name in ("one", "two"):
        project = tmp_path / name
        shutil.copytree(config.PROJECT / "src", project / "src")
        shutil.copy(config.PROJECT / "uv.lock", project)
        python = project / ".venv/bin/python"
        python.parent.mkdir(parents=True)
        python.symlink_to(str(interpreter))
        env = {**os.environ, **settings, "PYTHONPATH": f"{project / 'src'}:{site}", "P2996_TEST_PROJECT": str(project)}
        done = await proc.run(python, "-c", BUILD_ONCE, ids.commit, patches, bootstrap, env=env)
        lines = [line for line in done.stdout.decode().splitlines() if '"build done"' in line]
        found.append(json.loads(lines[-1])["id"])
    assert found[0] == found[1]


async def test_the_inputs_file_says_what_the_id_covers(cfg: Config, ids: Ids) -> None:
    name = await ids.id()
    inputs = json.loads((cfg.cache / "build/work/p2996-inputs.json").read_text())
    version = await proc.output("cmake", "--version")
    assert inputs["commit"] == ids.commit
    assert inputs["cmake"] in version
    assert inputs["compilers"]["C"]
    assert inputs["uv_lock"] == hashlib.sha256((config.PROJECT / "uv.lock").read_bytes()).hexdigest()
    assert "notes.patch" in inputs["patches"]
    assert any(path.endswith("/ninja") for path in inputs["files"].values())
    assert name.endswith(hashlib.sha256((cfg.cache / "build/work/p2996-inputs.json").read_bytes()).hexdigest()[:12])


async def test_an_installed_id_skips_the_compile(cfg: Config, ids: Ids, upstream: Upstream) -> None:
    # The toy compiles nothing, so this step records each compile the build runs.
    upstream.release("v1")
    toy = (upstream.path / "llvm/CMakeLists.txt").read_text()
    commit = upstream.write("llvm/CMakeLists.txt", toy + RECORD_COMPILE)
    compiled = cfg.cache / "build/work/compiled"
    name = await ids.id(commit)
    await install.run(cfg, Install())
    assert (cfg.root / "current").readlink() == Path(f"{name}/view")
    assert compiled.read_text() == "x\n"
    again = await ids.event(commit)
    assert again["event"] == "build skipped"
    assert again["id"] == name
    assert compiled.read_text() == "x\n"


async def test_a_stray_file_in_the_source_folder_does_not_survive_a_build(cfg: Config, ids: Ids) -> None:
    await ids.id()
    stray = cfg.cache / "source/work/llvm/stray.c"
    stray.write_text("int stray;\n")
    await ids.id()
    assert not stray.exists()


async def test_a_failed_build_cannot_be_installed(cfg: Config, ids: Ids, upstream: Upstream) -> None:
    await ids.id(upstream.release("v1"))
    with pytest.raises(P2996Error):
        await ids.id(upstream.release("v2", fail=True))
    with pytest.raises(P2996Error, match="no successful build"):
        await install.run(cfg, Install())


async def test_the_build_needs_no_basedirs_and_turns_precompiled_headers_off(
    cfg: Config, ids: Ids, recipe: Recipe, logs: pytest.CaptureFixture[str]
) -> None:
    await ids.id()
    assert "CMAKE_DISABLE_PRECOMPILE_HEADERS:BOOL=ON" in (cfg.cache / "build/work/CMakeCache.txt").read_text()
    await build.run(cfg, Build(commit=ids.commit, dry_run=True), recipe.patches, ids.bootstrap)
    assert "SCCACHE_BASEDIRS" not in events(logs)[0][-1]


async def test_a_standalone_source_voids_the_last_build(
    cfg: Config, ids: Ids, patches: Path, upstream: Upstream
) -> None:
    await ids.id(upstream.release("v1"))
    await source.run(cfg, Source(commit=upstream.release("v2")), patches)
    with pytest.raises(P2996Error, match="no successful build"):
        await install.run(cfg, Install())


async def test_a_source_that_failed_to_patch_voids_the_last_build(
    cfg: Config, ids: Ids, patches: Path, upstream: Upstream
) -> None:
    await ids.id(upstream.release("v1"))
    broken = upstream.write("notes.txt", "one\nchanged\nthree\n")
    with pytest.raises(P2996Error, match="no longer applies"):
        await source.run(cfg, Source(commit=broken), patches)
    with pytest.raises(P2996Error, match="no successful build"):
        await install.run(cfg, Install())


@pytest.mark.parametrize("name", ["usr/include/stdio.h", "usr/lib/libSystem.tbd", "SDKSettings.json"])
async def test_an_sdk_file_replaced_in_place_changes_the_id(
    ids: Ids, upstream: Upstream, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    # The toy compiles nothing, so an empty stand-in SDK is enough; only its bytes differ between builds.
    sdk = tmp_path / "MacOSX.sdk"
    for file in ("usr/include/stdio.h", "usr/lib/libSystem.tbd", "SDKSettings.json"):
        (sdk / file).parent.mkdir(parents=True, exist_ok=True)
        (sdk / file).write_text("one\n")
    (sdk / "usr/lib/libz.tbd").symlink_to("libSystem.tbd")
    monkeypatch.setenv("SDKROOT", str(sdk))
    commit = upstream.release("v1")
    before = await ids.id(commit)
    (sdk / name).write_text("two\n")
    assert await ids.id(commit) != before


@pytest.mark.parametrize("folder", ["builtins-bins", "runtimes-bins"])
async def test_a_removed_runtime_setting_does_not_survive_in_the_sub_build(
    cfg: Config, ids: Ids, upstream: Upstream, folder: str
) -> None:
    # A separate CMake cache, as LLVM's runtimes have; add_subdirectory in the toy cannot show this.
    commit = upstream.commit(
        {
            "llvm/CMakeLists.txt": EXTERNAL_MAIN.replace("@FOLDER@", folder),
            "llvm/sub/CMakeLists.txt": EXTERNAL_SUB,
        }
    )
    plain = ids.bootstrap.read_text()
    ids.add('set(RUNTIMES_CMAKE_ARGS "-DTOY_ABI=unstable" CACHE STRING "" FORCE)')
    await ids.id(commit)
    abi = cfg.cache / f"build/work/runtimes/{folder}/abi"
    assert abi.read_text() == "unstable\n"
    ids.bootstrap.write_text(plain)
    ids.add('set(RUNTIMES_CMAKE_ARGS "" CACHE STRING "" FORCE)')
    await ids.id(commit)
    assert abi.read_text() == "stable\n"


async def test_an_unchanged_runtime_setting_stays_in_the_sub_build(cfg: Config, ids: Ids, upstream: Upstream) -> None:
    # The sub-build's arguments stay the same, so its removed cache must still be written again from them.
    commit = upstream.commit(
        {
            "llvm/CMakeLists.txt": EXTERNAL_MAIN.replace("@FOLDER@", "runtimes-bins"),
            "llvm/sub/CMakeLists.txt": EXTERNAL_SUB,
        }
    )
    ids.add('set(RUNTIMES_CMAKE_ARGS "-DTOY_ABI=unstable" CACHE STRING "" FORCE)')
    await ids.id(commit)
    await ids.id(commit)
    sub_build = cfg.cache / "build/work/runtimes/runtimes-bins"
    assert (sub_build / "abi").read_text() == "unstable\n"
    assert "TOY_ABI:STRING=unstable" in (sub_build / "CMakeCache.txt").read_text()


@pytest.mark.parametrize("changed", ["lib/libpython3.15.dylib", "include/python3.15/Python.h"])
async def test_python_linked_library_or_header_replaced_in_place_changes_the_id(
    ids: Ids, tmp_path: Path, changed: str
) -> None:
    # The two records FindPython writes for what lldb links and includes; the interpreter stays the same.
    home = tmp_path / "python"
    for name in ("lib/libpython3.15.dylib", "include/python3.15/Python.h"):
        (home / name).parent.mkdir(parents=True, exist_ok=True)
        (home / name).write_text("one\n")
    ids.add(f'set(_Python3_LIBRARY_RELEASE "{home}/lib/libpython3.15.dylib" CACHE INTERNAL "" FORCE)')
    ids.add(f'set(_Python3_INCLUDE_DIR "{home}/include/python3.15" CACHE INTERNAL "" FORCE)')
    before = await ids.id()
    (home / changed).write_text("two\n")
    assert await ids.id() != before


def linked_python(home: Path) -> str:
    """The cache record for an include folder whose header and subfolder are links into another folder."""
    include = home / "include/python3.15"
    include.mkdir(parents=True)
    (home / "store/internal").mkdir(parents=True)
    for name in ("Python.h", "internal/core.h"):
        (home / "store" / name).write_text("one\n")
    (include / "Python.h").symlink_to(home / "store/Python.h")
    (include / "internal").symlink_to(home / "store/internal")
    return f'set(_Python3_INCLUDE_DIR "{include}" CACHE INTERNAL "" FORCE)'


@pytest.mark.parametrize("changed", ["Python.h", "internal/core.h"])
async def test_a_python_header_behind_a_link_changes_the_id(ids: Ids, tmp_path: Path, changed: str) -> None:
    ids.add(linked_python(tmp_path / "python"))
    before = await ids.id()
    (tmp_path / "python/store" / changed).write_text("two\n")
    assert await ids.id() != before


async def test_a_link_back_up_the_include_folder_ends_and_a_broken_link_counts(ids: Ids, tmp_path: Path) -> None:
    ids.add(linked_python(tmp_path / "python"))
    include = tmp_path / "python/include/python3.15"
    (include / "self").symlink_to(include)
    (include / "broken").symlink_to("gone.h")
    before = await ids.id()
    (include / "broken").unlink()
    (include / "broken").symlink_to("elsewhere.h")
    assert await ids.id() != before


async def test_removing_a_link_back_up_changes_the_id(ids: Ids, tmp_path: Path) -> None:
    ids.add(linked_python(tmp_path / "python"))
    include = tmp_path / "python/include/python3.15"
    (include / "self").symlink_to(include)
    before = await ids.id()
    (include / "self").unlink()
    assert await ids.id() != before


async def test_pointing_a_link_at_another_folder_above_changes_the_id(ids: Ids, tmp_path: Path) -> None:
    ids.add(linked_python(tmp_path / "python"))
    include = tmp_path / "python/include/python3.15"
    (include / "nested").mkdir()
    (include / "nested/up").symlink_to(include)
    before = await ids.id()
    (include / "nested/up").unlink()
    (include / "nested/up").symlink_to(include / "nested")
    assert await ids.id() != before


async def test_a_link_back_up_keeps_the_id_when_the_folder_moves(ids: Ids, tmp_path: Path) -> None:
    plain = ids.bootstrap.read_text()
    found = []
    for home in (tmp_path / "one", tmp_path / "two"):
        ids.bootstrap.write_text(plain)
        ids.add(linked_python(home))
        include = home / "include/python3.15"
        (include / "Python.h").unlink()
        (include / "internal").unlink()
        (include / "Python.h").write_text("one\n")
        (include / "self").symlink_to(include)
        found.append(await ids.id())
    assert found[0] == found[1]
