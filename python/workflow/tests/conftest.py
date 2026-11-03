"""Real git repositories for every test, and the command line run in-process."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from workflowtools.cli import main


@pytest.fixture(autouse=True)
def no_hook_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """A pre-commit hook exports GIT_DIR and friends, and they would point every test's git at the real checkout."""
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", root], check=True)
    monkeypatch.chdir(root)
    return root


def write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def add(root: Path, files: dict[str, str]) -> None:
    write(root, files)
    subprocess.run(["git", "-C", root, "add", "-f", "."], check=True)


def report(capsys: pytest.CaptureFixture[str], *args: str) -> list[dict[str, str]]:
    """Run a command; its stdout JSON lines, and SystemExit's code as a string under the "exit" key of a last line."""
    try:
        main(list(args))
        code = 0
    except SystemExit as stop:
        code = stop.code
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    return [*lines, {"exit": str(code)}]
