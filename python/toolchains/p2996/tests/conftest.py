"""Real fixtures: a local git upstream with a p2996 branch, and stand-in executables on PATH.

No mocking library: every test runs the real git, cmake, ninja and Apple clang. Only tools that
cannot run in a test (the hours-long clang-p2996 itself, a paid Codex session) are replaced by
small executables that do the same observable job.
"""

import json
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from p2996.log import configure
from p2996.models import Config

TINY_CMAKE = """\
cmake_minimum_required(VERSION 3.20)
project(tiny C)
add_executable(tiny main.c)
install(TARGETS tiny)
"""


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return done.stdout.strip()


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

    def write(self, name: str, text: str) -> str:
        file = self.path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
        git(self.path, "add", name)
        git(self.path, "commit", "-q", "-m", f"write {name}")
        return git(self.path, "rev-parse", "HEAD")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def logs(capsys: pytest.CaptureFixture[str]) -> pytest.CaptureFixture[str]:
    """The real JSON logging, pointed at pytest's captured streams."""
    configure()
    return capsys


def events(capsys: pytest.CaptureFixture[str]) -> tuple[list[dict], list[dict]]:
    """The JSON events logged so far: (stdout, stderr)."""
    out, err = capsys.readouterr()
    return [json.loads(line) for line in out.splitlines()], [json.loads(line) for line in err.splitlines()]


@pytest.fixture
def upstream(tmp_path: Path) -> Upstream:
    return Upstream(tmp_path / "upstream")


@pytest.fixture
def cfg(tmp_path: Path, upstream: Upstream) -> Config:
    return Config(
        remote=upstream.url,
        branch="p2996",
        root=tmp_path / "root",
        cache=tmp_path / "cache",
        lock=tmp_path / "state/heavy-gate.lock",
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
