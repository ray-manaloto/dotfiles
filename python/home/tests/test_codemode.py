"""claude-code-mode through the installed hometools command: it replaces itself with a stand-in claude on PATH."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hometools import codemode

HOMETOOLS = Path(sys.executable).parent / "hometools"  # what uv installed from [project.scripts]
VENV_BIN = Path(sys.prefix) / "bin"
# A claude that records what it was started with, then exits.
CLAUDE = """import json, os, sys
json.dump({"argv": sys.argv[1:], "cwd": os.getcwd(), "env": dict(os.environ)}, open(os.environ["RECORD"], "w"))
"""


@pytest.fixture
def stand_in(tmp_path: Path) -> Path:
    folder = tmp_path / "bin"
    folder.mkdir()
    (folder / "claude").write_text(f"#!{sys.executable}\n{CLAUDE}")
    (folder / "claude").chmod(0o755)
    return folder


def launch(tmp_path: Path, path: str, *args: str, **env: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    """hometools claude-code-mode as a herdr tab opened by a Claude session would start it: under uv run's venv,
    with that session's markers inherited."""
    record = tmp_path / "record.json"
    inherited = {
        "HOME": str(tmp_path),
        "PATH": path,
        "RECORD": str(record),
        "KEEP_ME": "yes",
        "VIRTUAL_ENV": str(Path(sys.prefix)),
        "UV_RUN_RECURSION_DEPTH": "1",
        **dict.fromkeys(codemode.INHERITED, "parent"),
        # coverage measures the started process only when it finds its own variables (pyproject [tool.coverage.run]).
        **{name: value for name, value in os.environ.items() if name.startswith("COVERAGE_")},
        **env,
    }
    done = subprocess.run([HOMETOOLS, "claude-code-mode", *args], capture_output=True, check=False, text=True,
                          env=inherited)  # fmt: skip
    return done, json.loads(record.read_text()) if record.exists() else {}


def test_claude_starts_in_code_mode_in_the_folder_with_the_prompt(tmp_path: Path, stand_in: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    path = os.pathsep.join([str(VENV_BIN), str(stand_in), "/usr/bin", "/bin"])
    done, seen = launch(tmp_path, path, "--folder", str(work), "fix the tests")
    assert done.returncode == 0, done.stderr
    settings = '{"remoteControlAtStartup":false,"env":{"CLAUDE_CODE_PLUGIN_DIRS":""},'
    settings += '"enabledPlugins":{"code-modernization@claude-plugins-official":false}}'
    assert seen["argv"] == ["--settings", settings, "--", "fix the tests"]
    assert Path(seen["cwd"]).resolve() == work.resolve()
    env = seen["env"]
    assert env[codemode.VARIABLE] == "1"
    assert env["KEEP_ME"] == "yes"
    assert not codemode.INHERITED & env.keys()
    assert not {"VIRTUAL_ENV", "UV_RUN_RECURSION_DEPTH"} & env.keys()
    assert env["PATH"].split(os.pathsep) == [str(stand_in), "/usr/bin", "/bin"]


def test_without_a_folder_or_prompt_it_starts_where_mise_was_called(tmp_path: Path, stand_in: Path) -> None:
    caller = tmp_path / "caller"
    caller.mkdir()
    done, seen = launch(tmp_path, f"{stand_in}{os.pathsep}/usr/bin", MISE_ORIGINAL_CWD=str(caller))
    assert done.returncode == 0, done.stderr
    assert len(seen["argv"]) == 2  # --settings and its JSON, no prompt
    assert Path(seen["cwd"]).resolve() == caller.resolve()


def test_an_option_shaped_prompt_stays_the_prompt(tmp_path: Path, stand_in: Path) -> None:
    done, seen = launch(tmp_path, str(stand_in), "--folder", str(tmp_path), "--", "--dangerously-skip-permissions")
    assert done.returncode == 0, done.stderr
    assert seen["argv"][2:] == ["--", "--dangerously-skip-permissions"]


def test_a_missing_folder_is_refused(tmp_path: Path, stand_in: Path) -> None:
    done, seen = launch(tmp_path, str(stand_in), "--folder", str(tmp_path / "gone"))
    assert done.returncode == 2
    assert json.loads(done.stderr)["error"] == f"claude-code-mode: {tmp_path / 'gone'} is not a folder"
    assert seen == {}


def test_no_claude_on_path_is_a_named_failure(tmp_path: Path) -> None:
    done, _ = launch(tmp_path, str(tmp_path / "empty"), "--folder", str(tmp_path))
    assert done.returncode == 127
    error = json.loads(done.stderr)["error"]
    assert error == "claude-code-mode: claude could not start: No such file or directory"


def test_a_stray_npm_claude_is_refused(tmp_path: Path, stand_in: Path) -> None:
    stray = tmp_path / ".local/share/mise/installs/node-x/lib/node_modules/@anthropic-ai/claude-code"
    stray.mkdir(parents=True)
    done, seen = launch(tmp_path, str(stand_in), "--folder", str(tmp_path))
    assert done.returncode == 3
    error = json.loads(done.stderr)["error"]
    assert error == f"claude-code-mode: Claude Code outside its native install at {stray}; run claude:doctor"
    assert seen == {}
