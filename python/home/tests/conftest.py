"""The scratch toolchain (tests/scratch_toolchain.py) as the hometools commands see it, in-process."""

import contextlib
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from .roll_world import World
from .scratch_toolchain import Scratch, Session

# pytest's and coverage's own variables stay; every other one comes from the scratch toolchain.
KEEP = ("PYTEST_", "COV_CORE_")


@pytest.fixture(scope="session")
def session(tmp_path_factory: pytest.TempPathFactory) -> Session:
    if sys.platform != "darwin":
        pytest.skip("the commands check a macOS Homebrew toolchain")
    return Session(tmp_path_factory.mktemp("session"))


@pytest.fixture
def toolchain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, session: Session) -> Iterator[Scratch]:
    """A healthy scratch toolchain, its fragment rendered, with the settings its file tasks' headers set."""
    tc = Scratch(tmp_path, session)
    for name in [name for name in os.environ if not name.startswith(KEEP)]:
        monkeypatch.delenv(name)
    for name, value in tc.env().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("TOOLCHAIN_BREW_PREFIX", str(tc.prefix))
    for name, value in tc.settings.items():
        monkeypatch.setenv(f"TOOLCHAIN_{name.upper()}", value)
    with contextlib.chdir(tc.home / "elsewhere"):
        tc.render()
        yield tc


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    """The roll tests' scratch herdr world (tests/roll_world.py); its processes end with the test."""
    made = World(tmp_path, monkeypatch)
    yield made
    made.stop()
