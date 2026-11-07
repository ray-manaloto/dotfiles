"""repotools toolchain-gate on a real repository: run for a change the toolchain tasks see, the reason otherwise."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from repotools.cli import main
from tests import clean_git_env

CONFIG = "unix/home/.config/mise/config.toml"
HELD = """# The global config.
[tools]
graphify = "0.9.103"
uv = "0.11.0"

[vars]
gcc = "16.2.0"
"""
SKIP = "toolchain-gate: nothing the toolchain tasks run from is staged; //home:check skipped\n"


def git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@e", *args], capture_output=True, check=True, text=True
    )
    return done.stdout


def put(path: str, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text)
    git("add", "--", path)


@pytest.fixture(autouse=True)
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository whose HEAD holds the global config, the file tasks and hometools."""
    clean_git_env(monkeypatch)
    git("init", "-q", "-b", "main", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    put(CONFIG, HELD)
    put("unix/home/.config/mise/tasks/toolchain/verify", "#!/usr/bin/env -S mise run\n")
    put("python/home/src/hometools/toolchain.py", "")
    put("README.md", "")
    git("commit", "-q", "-m", "one")
    return tmp_path


def gate(capsys: pytest.CaptureFixture[str]) -> tuple[str, str]:
    main(["toolchain-gate"])
    captured = capsys.readouterr()
    return captured.out, captured.err


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda: put("python/home/src/hometools/toolchain.py", "x = 1\n"), id="hometools"),
        pytest.param(lambda: git("rm", "-q", "unix/home/.config/mise/tasks/toolchain/verify"), id="a task deleted"),
        pytest.param(
            lambda: git("mv", "python/home/src/hometools/toolchain.py", "python/toolchain.py"), id="renamed away"
        ),
        pytest.param(lambda: put(CONFIG, HELD.replace('"16.2.0"', '"16.3.0"')), id="a toolchain var"),
        pytest.param(lambda: put(CONFIG, HELD.replace('"0.11.0"', '"0.12.0"')), id="a task tool pin"),
        pytest.param(lambda: put(CONFIG, HELD + '\n[tools.hk]\nversion = "2.9.0"\n'), id="a task tool added"),
        pytest.param(lambda: put(CONFIG, HELD + "\n[env]\nX = '1'\n"), id="another table"),
        pytest.param(lambda: git("rm", "-q", CONFIG), id="the config deleted"),
    ],
)
def test_a_change_the_toolchain_tasks_see_runs(
    change: Callable[[], object], capsys: pytest.CaptureFixture[str]
) -> None:
    change()
    assert gate(capsys) == ("run\n", "")


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda: put("README.md", "x\n"), id="another file"),
        pytest.param(lambda: put(CONFIG, HELD.replace('"0.9.103"', '"0.9.104"')), id="another pin"),
        pytest.param(lambda: put(CONFIG, HELD.replace("# The global config.", "# Moved.\n")), id="a comment"),
        pytest.param(lambda: put(CONFIG, HELD + '\n[tools.ruff]\nversion = "1"\n'), id="another tool added"),
    ],
)
def test_any_other_change_skips_with_the_reason(
    change: Callable[[], object], capsys: pytest.CaptureFixture[str]
) -> None:
    change()
    assert gate(capsys) == ("", SKIP)


def test_a_config_that_does_not_parse_fails(capsys: pytest.CaptureFixture[str]) -> None:
    put(CONFIG, "[vars\n")
    with pytest.raises(SystemExit, match="1"):
        main(["toolchain-gate"])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"].startswith("Expected ']'")


def test_no_head_fails(capsys: pytest.CaptureFixture[str]) -> None:
    # A first commit: only the config staged, so the gate reads HEAD's.
    git("checkout", "-q", "--orphan", "fresh")
    git("rm", "-q", "-r", "--cached", ".")
    put(CONFIG, HELD)
    with pytest.raises(SystemExit, match="1"):
        main(["toolchain-gate"])
    assert json.loads(capsys.readouterr().err)["error"].startswith("git failed: fatal: Not a valid object name HEAD")
