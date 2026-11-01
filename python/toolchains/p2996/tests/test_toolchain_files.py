"""cmake/toolchains: real cmake, ninja and compilers over a project that names no compiler and no flag."""

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from p2996 import config

TOOLCHAINS = config.PROJECT.parents[2] / "cmake/toolchains"

# A consumer: the compilers, the flags and, unless a test adds it, the language standard all have to
# come from the toolchain file. The two checks run the program inside try_compile and try_run; they
# are macros, so the minimum is 4.4 for CMP0219, which keeps the program's \n.
CMAKE = """\
cmake_minimum_required(VERSION 4.4)
project(toy C CXX)
@STANDARD@
include(CheckCXXSourceCompiles)
include(CheckCXXSourceRuns)
file(READ main.cpp program)
check_cxx_source_compiles("${program}" PROGRAM_COMPILES)
check_cxx_source_runs("${program}" PROGRAM_RUNS)
add_library(part OBJECT part.c)
add_executable(toy main.cpp $<TARGET_OBJECTS:part>)
@OPTIONS@
message(STATUS "environment CC=$ENV{CC} CXX=$ENV{CXX}")
"""

# The lines cpp/CMakeLists.txt has: a project that asks for C++26 itself must work too.
STANDARD = """\
set(CMAKE_CXX_STANDARD 26)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
"""

# A target that sets its options outright, which drops whatever add_compile_options put on the directory.
TARGET_OPTIONS = "set_property(TARGET toy PROPERTY COMPILE_OPTIONS -Wall)"

# <meta>, ^^ and [: :], plus a throw through libc++abi and libunwind.
SAMPLE = (config.RESOURCES / "reflection.cpp").read_text()

# template for needs more than -freflection; glaze, simdjson and rosetta all use it.
EXPANSION_SOURCE = """\
#include <meta>
#include <print>
struct Point { int x; int y; };
int main() {
    Point point{3, 4};
    constexpr auto members = std::define_static_array(
        std::meta::nonstatic_data_members_of(^^Point, std::meta::access_context::current()));
    template for (constexpr auto member : members)
        std::println("{}={}", std::meta::identifier_of(member), point.[:member:]);
}
"""

# Does not compile without -std=c++26: g++-16 defaults to C++20.
CXX26_SOURCE = """\
#include <cstdio>
#include <inplace_vector>
template <typename... Ts> constexpr auto first(Ts... xs) { return xs...[0]; }
int main() {
    std::inplace_vector<int, 2> values{first(26, 0)};
    std::printf("c++%d\\n", values[0]);
}
"""

# Does not compile without -freflection: GCC keeps ^^ and <meta> behind the flag.
GCC_REFLECTION_SOURCE = """\
#include <meta>
#include <print>
struct Point { int x; int y; };
int main() {
    Point point{3, 4};
    std::println("{}={}", std::meta::identifier_of(^^Point::x), point.[:^^Point::x:]);
}
"""

# toolchain file, C compiler, C++ compiler, main.cpp, what the program prints.
CLANG = ("clang-p2996.toolchain.cmake", "clang-p2996", "clang++-p2996", SAMPLE, "reflection value=43\n")
EXPANSION = ("clang-p2996.toolchain.cmake", "clang-p2996", "clang++-p2996", EXPANSION_SOURCE, "x=3\ny=4\n")
GCC = ("gcc-16.toolchain.cmake", "gcc-16", "g++-16", CXX26_SOURCE, "c++26\n")
GCC_REFLECTION = ("gcc-16.toolchain.cmake", "gcc-16", "g++-16", GCC_REFLECTION_SOURCE, "x=3\n")

# The global default the files leave alone. Neither is a compiler, so a file that falls back on them
# fails its configure.
GLOBAL_CC = "global-default-cc"
GLOBAL_CXX = "global-default-c++"

# What a caller hands in. A guard breaks the compile if its flag is gone; the rpath lands in the binary.
CALLER_CXX = "-DCALLER_CXX"
CALLER_C = "-DCALLER_C"
CALLER_RPATH = "@loader_path/caller"
CALLER_LINK = f"-Wl,-rpath,{CALLER_RPATH}"
GUARD_CXX = "#ifndef CALLER_CXX\n#error caller C++ flags are gone\n#endif\n"
GUARD_C = "#ifndef CALLER_C\n#error caller C flags are gone\n#endif\n"

HOST_PATH = re.compile(r"/(?:Users|home|opt|usr|Library|private|Applications)/|~/|ENV\{HOME\}|\.local/")
VERSION = re.compile(r"\d+\.\d+|(?:clang|clang\+\+|gcc|g\+\+|llvm)-\d+")
# The one version allowed: the -16 of the compiler names, so gcc-16.2 stays visible to VERSION.
GCC_NAME = re.compile(r"(?:gcc|g\+\+)-16(?!\.?\d)")


def which(tool: str) -> Path:
    """Where PATH finds tool; a missing tool fails the test, it never skips it."""
    found = shutil.which(tool)
    assert found, f"{tool} is not on PATH"
    return Path(found)


def ok(done: subprocess.CompletedProcess[str]) -> subprocess.CompletedProcess[str]:
    assert done.returncode == 0, done.stdout + done.stderr
    return done


def run(*argv: str | Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(arg) for arg in argv], env=env, check=False, capture_output=True, text=True)


class Toy:
    """A consumer project in a temp folder, configured and built through one toolchain file."""

    def __init__(self, top: Path, spec: tuple[str, str, str, str, str]) -> None:
        self.top = top
        self.out = top / "build"
        self.file, self.cc, self.cxx, self.program, self.prints = spec
        self.part = "int part(void) { return 0; }\n"

    def configure(self, *caller: str, standard: str = "", options: str = "") -> subprocess.CompletedProcess[str]:
        self.top.mkdir(exist_ok=True)
        (self.top / "CMakeLists.txt").write_text(CMAKE.replace("@STANDARD@", standard).replace("@OPTIONS@", options))
        (self.top / "main.cpp").write_text(self.program)
        (self.top / "part.c").write_text(self.part)
        toolchain = f"-DCMAKE_TOOLCHAIN_FILE={TOOLCHAINS / self.file}"
        layout = ["-S", self.top, "-B", self.out, "-G", "Ninja"]
        return run("cmake", "--fresh", *layout, toolchain, "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", *caller)

    def build(self) -> subprocess.CompletedProcess[str]:
        return run("cmake", "--build", self.out)

    def output(self) -> str:
        return ok(run(self.out / "toy")).stdout

    def compilers(self) -> tuple[Path, Path]:
        """What compiled part.c and main.cpp, as compile_commands.json names them."""
        entries = json.loads((self.out / "compile_commands.json").read_text())
        used = {Path(entry["file"]).name: Path(shlex.split(entry["command"])[0]) for entry in entries}
        return used["part.c"], used["main.cpp"]

    def cached(self, name: str) -> str:
        found = re.search(rf"^{name}:\w+=(.*)$", (self.out / "CMakeCache.txt").read_text(), re.MULTILINE)
        assert found, f"{name} is not in CMakeCache.txt"
        return found[1]


@pytest.fixture(autouse=True)
def shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """A consumer's shell: CC and CXX hold the global default, and no flag arrives from outside."""
    monkeypatch.setenv("CC", GLOBAL_CC)
    monkeypatch.setenv("CXX", GLOBAL_CXX)
    for name in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "SDKROOT", "CLANG_NO_DEFAULT_CONFIG"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(params=[CLANG, GCC], ids=["clang-p2996", "gcc-16"])
def toy(request: pytest.FixtureRequest, tmp_path: Path) -> Toy:
    return Toy(tmp_path / "toy", request.param)


@pytest.fixture(
    params=[CLANG, EXPANSION, GCC, GCC_REFLECTION],
    ids=["clang-p2996", "template-for", "gcc-16", "gcc-reflection"],
)
def probe(request: pytest.FixtureRequest, tmp_path: Path) -> Toy:
    return Toy(tmp_path / "toy", request.param)


@pytest.fixture(params=["", STANDARD], ids=["standard-from-the-file", "standard-from-the-project"])
def standard(request: pytest.FixtureRequest) -> str:
    return request.param


def keeps_the_caller(toy: Toy, *caller: str) -> None:
    """The caller's flags and the file's own reach the compile, the link and try_compile together."""
    toy.program = GUARD_CXX + toy.program
    toy.part = GUARD_C + toy.part
    ok(toy.configure(*caller))
    ok(toy.build())
    assert toy.output() == toy.prints
    assert toy.cached("PROGRAM_COMPILES") == "1"
    assert toy.cached("PROGRAM_RUNS") == "1"
    assert f"path {CALLER_RPATH} (offset" in ok(run("otool", "-l", toy.out / "toy")).stdout


def test_a_project_builds_and_runs(probe: Toy, standard: str) -> None:
    ok(probe.configure(standard=standard))
    ok(probe.build())
    assert probe.output() == probe.prints
    assert probe.compilers() == (which(probe.cc), which(probe.cxx))


def test_try_compile_honours_the_file(probe: Toy, standard: str) -> None:
    ok(probe.configure(standard=standard))
    assert probe.cached("PROGRAM_COMPILES") == "1"
    assert probe.cached("PROGRAM_RUNS") == "1"


def test_a_target_may_set_its_own_options(probe: Toy) -> None:
    ok(probe.configure(options=TARGET_OPTIONS))
    ok(probe.build())
    assert probe.output() == probe.prints


def test_flags_from_the_environment_stay_beside_the_files(probe: Toy, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CXXFLAGS", CALLER_CXX)
    monkeypatch.setenv("CFLAGS", CALLER_C)
    monkeypatch.setenv("LDFLAGS", CALLER_LINK)
    keeps_the_caller(probe)


def test_flags_from_the_command_line_stay_beside_the_files(probe: Toy) -> None:
    keeps_the_caller(
        probe,
        f"-DCMAKE_CXX_FLAGS={CALLER_CXX}",
        f"-DCMAKE_C_FLAGS={CALLER_C}",
        f"-DCMAKE_EXE_LINKER_FLAGS={CALLER_LINK}",
    )


def test_the_program_runs_on_the_forks_libcxx(tmp_path: Path) -> None:
    prefix = which("clang++-p2996").resolve().parents[1]
    toy = Toy(tmp_path / "toy", CLANG)
    ok(toy.configure())
    ok(toy.build())
    # dyld also maps the system libc++ for libSystem, so only the fork's being loaded can be asserted.
    loaded = ok(run(toy.out / "toy", env={**os.environ, "DYLD_PRINT_LIBRARIES": "1"})).stderr
    assert f"{prefix}/lib/libc++.1" in loaded


def test_the_compilers_are_found_by_name_on_path(toy: Toy, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tools = {name: which(name) for name in (toy.cc, toy.cxx)}
    rest = [str(which("cmake").parent), str(which("ninja").parent), "/usr/bin", "/bin"]
    monkeypatch.setenv("PATH", os.pathsep.join(rest))
    missing = toy.configure()
    assert missing.returncode != 0
    assert toy.cc in missing.stdout + missing.stderr

    links = tmp_path / "links"
    links.mkdir()
    for name, path in tools.items():
        (links / name).symlink_to(path)
    monkeypatch.setenv("PATH", os.pathsep.join([str(links), *rest]))
    ok(toy.configure())
    assert toy.compilers() == (links / toy.cc, links / toy.cxx)


def test_cc_and_cxx_stay_the_global_default(toy: Toy) -> None:
    assert f"environment CC={GLOBAL_CC} CXX={GLOBAL_CXX}" in ok(toy.configure()).stdout


def test_the_file_holds_no_host_path_and_no_version(toy: Toy) -> None:
    text = (TOOLCHAINS / toy.file).read_text()
    assert HOST_PATH.findall(text) == []
    assert VERSION.findall(GCC_NAME.sub("", text)) == []
