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
    home.mkdir(exist_ok=True)
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


@pytest.mark.parametrize(
    ("manifest_request", "status"),
    [
        (None, "error"),
        ("turn-1", "error"),
        ("stale-turn", "error"),
        ("turn-1", "empty_unverified"),
        ("turn-1", "oversize-manifest"),
        ("turn-1", "deep-manifest"),
    ],
)
def test_failed_wrapper_records_only_safe_same_request_incomplete_metadata(
    tmp_path: Path, manifest_request: str | None, status: str
) -> None:
    """CG-36c F3: failed native bootstrap/provider execution is durable and private."""
    home = tmp_path / "home"
    home.mkdir()
    marker = home / ".codex/research-coverage/session-1/turn-1/required.json"
    bound = {
        "turn_id": "turn-1",
        "scope": "research",
        "policy": "strict-five-v2",
        "prompt_sha256": "a" * 64,
    }
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps(bound))
    if manifest_request is not None:
        (marker.parent / "manifest.json").write_text(
            json.dumps(
                {
                    "request_id": manifest_request,
                    "strict_five": True,
                    "policy_version": "strict-five-v2",
                    "sources": [
                        {
                            "source": "exa",
                            "status": "error"
                            if status.endswith("manifest")
                            else status,
                            "reason": _NOISE,
                        }
                    ],
                }
            )
        )
    manifest = marker.parent / "manifest.json"
    if status == "oversize-manifest":
        raw = manifest.read_bytes()
        manifest.write_bytes(raw + b" " * (1024 * 1024 + 1 - len(raw)))
    elif status == "deep-manifest":
        manifest.write_bytes(b"[" * 1100 + b"]" * 1100)
    result, _ = _wrapper(
        tmp_path,
        [
            "topic",
            "--strict-five",
            "--request-id",
            "turn-1",
            "--out",
            str(marker.parent),
        ],
        23,
    )
    assert result.returncode == 23
    expected_routes = [{"route": "fnox", "error_class": "ProcessExitError"}]
    if manifest_request == "turn-1" and not status.endswith("manifest"):
        expected_routes.append({"route": "exa", "error_class": "ProviderError"})
    assert json.loads(marker.read_text()) == {
        **bound,
        "outcome": {
            "status": "INCOMPLETE",
            "coverage_complete": False,
            "request_id": "turn-1",
            "failed_routes": expected_routes,
        },
    }
    assert marker.stat().st_mode & 0o777 == 0o600
    assert _NOISE not in marker.read_text() + result.stdout + result.stderr
