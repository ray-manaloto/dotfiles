"""Fixtures: a real git repository with tagged releases, a registry for it, and the real cbm."""

# No mocking library and no cbm stand-in: depmaps runs the cbm of mise's global pin, and git. Each test gives
# cbm a cache and a daemon rendezvous of its own, in its own folder: CBM_CACHE_DIR moves the cache
# (src/foundation/platform.c:635-648 at v0.12.1) and CBM_RUNTIME_DIR the rendezvous, which every cbm process
# otherwise shares account-wide (src/daemon/bootstrap.c:238-246). So no test meets the user's live daemon or
# cache, and the maps go when the folder does. DEP_MAPS_* point everything else (registry, store, lockfile)
# into the test's own folder too.

import json
import os
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def no_hook_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """A pre-commit hook exports GIT_DIR and friends; a test's `git init` under them writes core.worktree into the
    real repository's shared config, and every checkout of it then works on the wrong folder."""
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)


# The installed command, as `uv run depmaps` and the mise tasks start it.
DEPMAPS = Path(sys.executable).parent / "depmaps"
PACKAGE = Path(__file__).parents[1]
CBM = Path.home() / ".local/share/mise/installs/github-deus-data-codebase-memory-mcp/global/codebase-memory-mcp"
TIMEOUT = 120

CORE_1_0 = """\
def keep(count):
    total = 0
    for index in range(count):
        total += index * 2 + count - 1
    return total


def gone():
    return 0


def tiny():
    return 1


def shape(a):
    return a


class Box:
    def size(self):
        return 3
"""

# 1.1.0: gone removed, fresh added, shape gains a parameter, tiny's body changes; keep and Box.size only move.
CORE_1_1 = """\
def keep(count):
    total = 0
    for index in range(count):
        total += index * 2 + count - 1
    return total


def fresh():
    return [1, 2]


def tiny():
    return 2


def shape(a, b):
    return a


class Box:
    def size(self):
        return 3
"""


def git(folder: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=Depmaps Test", "-c", "user.email=depmaps@example.invalid", *args],
        cwd=folder, env=os.environ.copy(), capture_output=True, text=True, check=True, timeout=TIMEOUT,
    )  # fmt: skip
    return done.stdout


def release(repo: Path, version: str, files: dict[str, str | None]) -> None:
    """Commit these files (None deletes one) and tag the commit v<version>."""
    for name, text in files.items():
        path = repo / name
        if text is None:
            git(repo, "rm", "--quiet", name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        git(repo, "add", name)
    git(repo, "commit", "--quiet", "-m", f"Release {version}")
    git(repo, "tag", f"v{version}")


def events(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines()]


class Env:
    """One test's registry, lockfile and store, and the dependency name it maps under."""

    def __init__(self, root: Path, repo: Path) -> None:
        self.root, self.repo = root, repo
        self.name, self.spare = (f"dmtest-{uuid.uuid4().hex[:8]}" for _ in range(2))
        self.registry, self.lock, self.store = root / "deps.json", root / "mise.lock", root / "store"

    def deps(self, deps: dict[str, dict[str, Any]]) -> None:
        """Write the registry."""
        self.registry.write_text(json.dumps({"deps": deps}))

    def dep(self, **extra: object) -> dict[str, object]:
        """The fixture repository, its version from the lockfile's fixture:tool."""
        return {"repo": str(self.repo), "tag": "v{version}", "version": {"lock": "fixture:tool"}, **extra}

    def pin(self, version: str) -> None:
        self.lock.write_text(f'[[tools."fixture:tool"]]\nversion = "{version}"\nbackend = "fixture:tool"\n')

    def folder(self, version: str, name: str | None = None) -> Path:
        return self.store / (name or self.name) / version

    def run(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(DEPMAPS), *args], env=os.environ.copy(), stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=TIMEOUT, cwd=cwd or self.root, check=False,
        )  # fmt: skip

    def task(self, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        """The package's mise task of that name, as a person starts it; stderr keeps depmaps' lines and
        drops mise's own, which start with the task's name in brackets."""
        done = subprocess.run(
            ["mise", "run", f"//depmaps:{name}", *args], env=os.environ.copy(), stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=TIMEOUT, cwd=PACKAGE, check=False,
        )  # fmt: skip
        mine = "".join(line for line in done.stderr.splitlines(keepends=True) if not line.startswith("[//"))
        return subprocess.CompletedProcess(done.args, done.returncode, done.stdout, mine)


def cbm_tool(name: str, arguments: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CBM), "cli", "--quiet", name, json.dumps(arguments)], capture_output=True, text=True,
        timeout=TIMEOUT, check=False,
    )  # fmt: skip


def database(project: str) -> Path:
    return Path(os.environ.get("CBM_CACHE_DIR") or Path.home() / ".cache/codebase-memory-mcp") / f"{project}.db"


@pytest.fixture
def runtime() -> Iterator[Path]:
    """cbm's runtime folder, which must exist: a short one under /tmp, as the socket path inside it must
    fit sun_path (src/daemon/ipc.c:836 at v0.12.1; 104 bytes on macOS), which pytest's tmp_path overruns."""
    with tempfile.TemporaryDirectory(prefix="cbm-", dir="/tmp") as folder:
        yield Path(folder)


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runtime: Path) -> Env:
    root = tmp_path.resolve()
    for key in [key for key in os.environ if key.startswith(("GIT_", "DEP_MAPS_"))]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("CBM_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("CBM_CACHE_DIR", str(root / "cbm-cache"))  # cbm makes this folder itself
    # Real git without the machine's identity, hooks, signing or URL rewrites, for the fixture and depmaps alike.
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    repo = root / "upstream"
    repo.mkdir()
    git(repo, "init", "--quiet", "--initial-branch=main")
    files: dict[str, str | None] = {"core.py": CORE_1_0, "settings.toml": "a = 1\n", "notes.md": "one\n"}
    files |= {"schema/a.json": '{"a": 1}\n', "schema/old.json": "{}\n"}
    release(repo, "1.0.0", files)
    files = {
        "core.py": CORE_1_1,
        "settings.toml": "a = 2\n",
        "notes.md": "two\n",
        "schema/new.json": '{"n": [1, 2, 3]}\n',
    }
    files |= {"schema/a.json": None, "schema/b.json": '{"a": 1}\n', "schema/old.json": None}
    release(repo, "1.1.0", files)
    release(repo, "1.2.0", {"notes.md": "three\n"})
    found = Env(root, repo)
    monkeypatch.setenv("DEP_MAPS_REGISTRY", str(found.registry))
    monkeypatch.setenv("DEP_MAPS_LOCK", str(found.lock))
    monkeypatch.setenv("DEP_MAPS_STORE", str(found.store))
    found.deps({found.name: found.dep(files=["settings.toml", "schema/*.json"])})
    found.pin("1.0.0")
    return found
