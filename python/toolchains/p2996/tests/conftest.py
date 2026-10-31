"""Real fixtures: a local git upstream with a p2996 branch, and stand-in executables on PATH.

No mocking library: every test runs the real git, cmake, ninja and Apple clang. Only tools that
cannot run in a test (the hours-long clang-p2996 itself, a paid Codex session) are replaced by
small executables that do the same observable job.
"""

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest

from p2996 import build, cli, config, install, source
from p2996.log import configure
from p2996.models import Build, Config, Install, Source

TINY_CMAKE = """\
cmake_minimum_required(VERSION 3.20)
project(tiny C)
add_executable(tiny main.c)
install(TARGETS tiny)
"""

# A whole toy toolchain shaped like the real one: a main build with two runtime sub-builds, tools in
# bin, headers in include, libraries in lib, so the real install runs over real build trees.
TOY_CMAKE = """\
cmake_minimum_required(VERSION 3.20)
project(toy NONE)
add_subdirectory(builtins runtimes/builtins-bins)
add_subdirectory(runtimes runtimes/runtimes-bins)
install(PROGRAMS tools/clang tools/clang++ tools/clang-p2996 tools/clang++-p2996 tools/llvm-ar DESTINATION bin)
"""

# Stands in for clang++-p2996 (a real one takes hours to build): reports its default config the way
# clang --version does, and compiles by writing the executable the shipped sample would become.
COMPILER = """\
#!/bin/sh
# version=@VERSION@
here="$(dirname "$0")"
if [ "$1" = --version ]; then
  echo "clang version 23.0.0 (p2996 stand-in @VERSION@)"
  if [ -f "$here/arm64-apple-darwin-clang++.cfg" ]; then
    echo "Configuration file: $here/arm64-apple-darwin-clang++.cfg"
  fi
  exit 0
fi
while [ "$#" -gt 1 ]; do
  [ "$1" = -o ] && out="$2"
  shift
done
printf '#!/bin/sh\\necho "reflection value=@ANSWER@"\\n' > "$out"
chmod +x "$out"
"""

# What ROOT/bin shows for a toy release: link name -> the tool in the prefix's bin. The unsuffixed
# clang and clang++ are kept for the runtimes sub-build (DL-760) and must not reach ROOT/bin.
LINKS = {
    "arm64-apple-darwin.cfg": "arm64-apple-darwin.cfg",
    "arm64-apple-darwin-clang++.cfg": "arm64-apple-darwin-clang++.cfg",
    "clang-p2996": "clang-p2996",
    "clang++-p2996": "clang++-p2996",
    "llvm-ar-p2996": "llvm-ar",
    "runtime-tool-p2996": "runtime-tool",
}

# One file per part of a view; each carries version=<release>.
MARKS = {"bin": "bin/clang++-p2996", "include": "include/c++/v1/meta", "lib": "lib/libc++.txt"}


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return done.stdout.strip()


def versions(top: Path) -> dict[str, str | None]:
    """Which release each part of a view came from; None when the part is missing."""
    found: dict[str, str | None] = {}
    for part, name in MARKS.items():
        file = top / name
        mark = re.search(r"version=(\S+)", file.read_text()) if file.exists() else None
        found[part] = mark[1] if mark else None
    return found


def whole(version: str) -> dict[str, str | None]:
    """versions() of a view that comes entirely from one release."""
    return dict.fromkeys(MARKS, version)


def tools(top: Path) -> set[str]:
    """The names a view's bin holds, whether or not they resolve."""
    return {path.name for path in (top / "bin").iterdir()} if (top / "bin").is_dir() else set()


def tree(top: Path) -> dict[str, tuple[int, str | None, int]]:
    """Every path under top with its type, content and mtime: equal snapshots mean untouched."""
    found: dict[str, tuple[int, str | None, int]] = {}
    for here, dirs, files in top.walk():
        for path in (here / name for name in dirs + files):
            info = path.lstat()
            content = None
            if path.is_symlink():
                content = str(path.readlink())
            elif path.is_file():
                content = hashlib.sha256(path.read_bytes()).hexdigest()
            found[str(path.relative_to(top))] = (stat.S_IFMT(info.st_mode), content, info.st_mtime_ns)
    return found


class Upstream:
    """A non-bare repo standing in for bloomberg/clang-p2996, served over file://."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.mkdir()
        git(path, "init", "-q", "-b", "p2996")
        git(path, "config", "user.email", "test@example.invalid")
        git(path, "config", "user.name", "test")
        # Lets a shallow fetch name any commit, as GitHub allows.
        git(path, "config", "uploadpack.allowAnySHA1InWant", "true")
        self.write("llvm/CMakeLists.txt", TINY_CMAKE)
        self.write("llvm/main.c", "int main(void) { return 0; }\n")
        self.write("notes.txt", "one\ntwo\nthree\n")

    @property
    def url(self) -> str:
        return self.path.as_uri()

    def commit(self, files: dict[str, str]) -> str:
        for name, text in files.items():
            file = self.path / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
        git(self.path, "add", ".")
        git(self.path, "commit", "-q", "-m", f"write {', '.join(files)}")
        return git(self.path, "rev-parse", "HEAD")

    def write(self, name: str, text: str) -> str:
        return self.commit({name: text})

    def release(self, version: str, *, answer: int = 43, skip: str = "", fail: bool = False) -> str:
        """Commit a toy toolchain marked version; answer is what its compiled sample prints."""
        cmake = TOY_CMAKE
        if skip != "include":
            cmake += "install(FILES tools/meta DESTINATION include/c++/v1)\n"
        if skip != "lib":
            cmake += "install(FILES tools/libc++.txt DESTINATION lib)\n"
        if fail:
            cmake += "add_custom_target(broken ALL COMMAND false)\n"
        mark = f"version={version}\n"
        compiler = COMPILER.replace("@VERSION@", version).replace("@ANSWER@", str(answer))
        return self.commit(
            {
                "llvm/CMakeLists.txt": cmake,
                "llvm/builtins/CMakeLists.txt": "# This sub-build installs nothing, as in a build without builtins.\n",
                "llvm/runtimes/CMakeLists.txt": "install(PROGRAMS runtime-tool DESTINATION bin)\n",
                "llvm/runtimes/runtime-tool": "#!/bin/sh\n",
                "llvm/tools/clang": "#!/bin/sh\n",
                "llvm/tools/clang++": "#!/bin/sh\n",
                "llvm/tools/clang-p2996": "#!/bin/sh\n",
                "llvm/tools/clang++-p2996": compiler,
                "llvm/tools/llvm-ar": "#!/bin/sh\n",
                "llvm/tools/meta": f"// {mark}",
                "llvm/tools/libc++.txt": mark,
            }
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def isolated_git() -> Iterator[None]:
    """Inside a commit hook git exports GIT_DIR and friends, and the global config fires hk on every commit."""
    with pytest.MonkeyPatch.context() as patch:
        for name in [name for name in os.environ if name.startswith("GIT_")]:
            patch.delenv(name)
        patch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
        patch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        yield


@pytest.fixture(autouse=True)
def logs(capsys: pytest.CaptureFixture[str]) -> pytest.CaptureFixture[str]:
    """The real JSON logging, pointed at pytest's captured streams."""
    configure()
    return capsys


def events(capsys: pytest.CaptureFixture[str]) -> tuple[list[dict], list[dict]]:
    """The JSON events logged so far: (stdout, stderr)."""
    out, err = capsys.readouterr()
    return [json.loads(line) for line in out.splitlines()], [json.loads(line) for line in err.splitlines()]


def fails(argv: list[str], logs: pytest.CaptureFixture[str]) -> dict:
    """Run the CLI, expect exit 1, and return its one error event."""
    with pytest.raises(SystemExit) as exit_:
        cli.main(argv)
    assert exit_.value.code == 1
    out, [error] = events(logs)
    assert error["level"] == "error"
    assert all(e["level"] == "info" for e in out)
    return error


class Recipe:
    """The real steps over the toy upstream; each returns the JSON event it logged."""

    def __init__(self, cfg: Config, patches: Path, logs: pytest.CaptureFixture[str]) -> None:
        self.cfg = cfg
        self.patches = patches
        self.logs = logs

    def logged(self, name: str) -> dict:
        found = [event for event in events(self.logs)[0] if event["event"] == name]
        assert found, f"no {name!r} event"
        return found[-1]

    async def source(self, commit: str) -> dict:
        await source.run(self.cfg, Source(commit=commit), self.patches)
        return self.logged("source ready")

    async def build(self, commit: str) -> dict:
        await build.run(self.cfg, Build(commit=commit), self.patches)
        return self.logged("build done")

    async def ship(self, commit: str) -> str:
        """Prepare and build commit, the two steps before an install."""
        await self.source(commit)
        await self.build(commit)
        return commit

    async def install(self) -> dict:
        await install.run(self.cfg, Install())
        return self.logged("installed")


@pytest.fixture
def upstream(tmp_path: Path) -> Upstream:
    return Upstream(tmp_path / "upstream")


@pytest.fixture
def cfg(tmp_path: Path, upstream: Upstream) -> Config:
    # P2996_LOCK is what an older shell still exports: the package reads no such setting.
    return config.load(
        {
            "P2996_REMOTE": upstream.url,
            "P2996_BRANCH": "p2996",
            "P2996_ROOT": str(tmp_path / "root"),
            "P2996_CACHE": str(tmp_path / "cache"),
            "P2996_LOCK": str(tmp_path / "state/heavy-gate.lock"),
        }
    )


@pytest.fixture
def patches(tmp_path: Path) -> Path:
    """One zero-context patch against notes.txt, made the way the real patches are."""
    work = tmp_path / "patch-work"
    work.mkdir()
    (work / "notes.txt").write_text("one\ntwo\nthree\n")
    git(work, "init", "-q")
    git(work, "add", "notes.txt")
    (work / "notes.txt").write_text("one\nTWO\nthree\n")
    out = tmp_path / "patches"
    out.mkdir()
    (out / "notes.patch").write_text(git(work, "diff", "-U0") + "\n")
    return out


@pytest.fixture
def recipe(cfg: Config, patches: Path, logs: pytest.CaptureFixture[str]) -> Recipe:
    return Recipe(cfg, patches, logs)


@pytest.fixture
def env(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> Config:
    """The P2996_* variables mise.toml would set, for tests that go through the CLI."""
    for name, value in cfg.model_dump().items():
        monkeypatch.setenv(f"P2996_{name.upper()}", str(value))
    return cfg


def executable(path: Path, body: str) -> Path:
    """Write a Python script as an executable (the stand-ins for clang++-p2996 and codex)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(body))
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path
