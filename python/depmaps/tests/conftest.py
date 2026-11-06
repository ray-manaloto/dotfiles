"""Fixtures: a real git repository with tagged releases, a registry for it, and the real cbm."""

# No mocking library and no cbm stand-in: depmaps runs the cbm of mise's global pin, and git.
# The tests keep the real HOME. Every cbm process meets the one account-wide daemon, and a run from a
# temporary HOME brings a second cache root into it, which the live daemon refuses (python/cbm/tests/conftest.py,
# src/daemon/bootstrap.c:243-255 at v0.12.1). So the maps go to the real cbm cache under a dependency name
# no one else uses, and each test deletes its cbm projects when it ends. DEP_MAPS_* point everything else
# (registry, store, lockfile) into the test's own folder.

import json
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

# The installed command, as `uv run depmaps` and the mise tasks start it.
DEPMAPS = Path(sys.executable).parent / "depmaps"
CBM = Path.home() / ".local/share/mise/installs/github-deus-data-codebase-memory-mcp/global/codebase-memory-mcp"
TIMEOUT = 120
# Seconds: far longer than a whole run of this suite.
STALE = 3600
VERSIONS = ("1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.9.0", "1.10.0", "1.11.0")

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
        self.name = f"dmtest-{uuid.uuid4().hex[:12]}"
        self.registry, self.lock, self.store = root / "deps.json", root / "mise.lock", root / "store"
        self.names = [self.name]

    def deps(self, deps: dict[str, dict[str, Any]]) -> None:
        self.names += [name for name in deps if name not in self.names]
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


def cbm_tool(name: str, arguments: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CBM), "cli", "--quiet", name, json.dumps(arguments)], capture_output=True, text=True,
        timeout=TIMEOUT, check=False,
    )  # fmt: skip


def database(project: str) -> Path:
    return Path(os.environ.get("CBM_CACHE_DIR") or Path.home() / ".cache/codebase-memory-mcp") / f"{project}.db"


def delete(project: str) -> str:
    """Delete one cbm project and return cbm's status, deleted or not_found. A reply that isn't cbm's
    JSON raises, and the next session's sweep deletes what that left behind."""
    done = cbm_tool("delete_project", {"project": project})
    # A project already gone is an error reply, which cbm prints on stderr (src/main.c:711-736 at 0.12.1).
    return json.loads(done.stdout or done.stderr)["status"]


@pytest.fixture(scope="session", autouse=True)
def sweep() -> None:
    """Delete the projects of an earlier run that was killed before its teardown. Only this suite names
    projects dmtest-<12 hex>-v<version>, so nothing else in the live cache matches. A map younger than
    STALE may belong to a run still going in another checkout, so it waits for a later sweep."""
    for db in database("dmtest-").parent.glob("dmtest-*-v*.db"):
        try:
            age = time.time() - db.stat().st_mtime
        except FileNotFoundError:  # that run's own teardown deleted it after the glob
            continue
        if age > STALE:
            assert delete(db.name.removesuffix(".db")) in {"deleted", "not_found"}, db


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Env]:
    root = tmp_path.resolve()
    for key in [key for key in os.environ if key.startswith(("GIT_", "DEP_MAPS_"))]:
        monkeypatch.delenv(key)
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
    yield found
    # Runs when the test fails too. Every reply is collected before any is checked, so a status other
    # than deleted or not_found leaves none of the rest behind.
    replies = [delete(f"{name}-v{version}") for name in found.names for version in VERSIONS]
    assert all(reply in {"deleted", "not_found"} for reply in replies), replies
