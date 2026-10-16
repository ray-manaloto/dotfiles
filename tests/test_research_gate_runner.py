# Copyright (c) 2026 Raymond Manaloto
"""Public command boundary controls for the profile-pinned research wrapper."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_MODULE = "dotfiles_setup.research_gate_runner"
_NOISE = "fixture-diagnostic-must-not-escape"


def _wrapper(
    tmp_path: Path, argv: list[str], rc: int, *, task: bool = False
) -> tuple[subprocess.CompletedProcess[str], Path]:
    binary = tmp_path / "bin"
    binary.mkdir()
    capture = tmp_path / "captured-argv.json"
    stub = binary / "fnox"
    stub.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "assert os.environ.get('FNOX_PROFILE') == 'codex_research'\n"
        "from pathlib import Path\n"
        f"Path({str(capture)!r}).write_text(json.dumps(sys.argv[1:]))\n"
        f"print({_NOISE!r})\n"
        f"print({_NOISE!r}, file=sys.stderr)\n"
        f"raise SystemExit({rc})\n"
    )
    stub.chmod(0o700)
    home = tmp_path / "home"
    home.mkdir()
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": str(binary) + os.pathsep + os.environ.get("PATH", ""),
        "PYTHONPATH": str(_ROOT / "python/src"),
        "FNOX_PROFILE": "fixture-wrong-profile",
    }
    command = [sys.executable, "-m", _MODULE]
    if task:
        config = tomllib.loads((_ROOT / "mise.toml").read_text())
        command = shlex.split(config["tasks"]["research-gate"]["run"])
    result = subprocess.run(
        [*command, *argv],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return result, capture


@pytest.mark.parametrize("task", [False, True], ids=["module", "mise-task-command"])
@pytest.mark.parametrize("child_rc", [0, 23])
def test_wrapper_pins_native_profile_forwards_argv_and_preserves_exit(
    tmp_path: Path, *, task: bool, child_rc: int
) -> None:
    """CG-36c F2: native fnox options cannot come from the calling agent."""
    forwarded = [
        "topic with spaces",
        "--strict-five",
        "--request-id",
        "turn-1",
        "--out",
        str(tmp_path / "evidence"),
        "--profile",
        "fixture-child-option",
    ]
    result, capture = _wrapper(tmp_path, forwarded, child_rc, task=task)
    assert result.returncode == child_rc
    assert capture.exists(), result.stderr
    assert json.loads(capture.read_text()) == [
        "--config",
        str(tmp_path / "home/.config/fnox/config.toml"),
        "--profile",
        "codex_research",
        "--no-defaults",
        "--no-daemon",
        "--non-interactive",
        "exec",
        "--",
        "mise",
        "-C",
        str(_ROOT),
        "run",
        "research-fanout",
        "--",
        *forwarded,
    ]
    assert _NOISE not in result.stdout + result.stderr
