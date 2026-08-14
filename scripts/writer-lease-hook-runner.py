#!/usr/bin/python3
# Copyright (c) 2026 Raymond Manaloto
"""Pinned, environment-independent bridge into the project writer hook.

This file intentionally stays compatible with macOS's system Python. It reads
the hook payload before locating the repository-local environment and executes
a fixed argv with a fixed minimal environment. Bridge failures serialize as a
fail-closed hook decision instead of becoming skipped hooks.
"""

import json
import os
import pathlib
import pwd
import stat
import subprocess
import sys
from typing import NoReturn


class RunnerError(RuntimeError):
    """A deterministic failure at the pinned hook bridge boundary."""


def _deny(event: str, reason: str) -> None:
    if event in {"PostToolUse", "PostToolUseFailure"}:
        payload = {"continue": False, "stopReason": reason}
    else:
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")


def _fail(message: str) -> NoReturn:
    raise RunnerError(message)


def _root(cwd: object) -> pathlib.Path:
    if not isinstance(cwd, str) or not cwd:
        _fail("hook cwd is missing")
    current = pathlib.Path(cwd).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    _fail("hook cwd is outside a Git worktree")
    raise RunnerError


def _load_payload(raw: bytes) -> dict:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        _fail("hook payload is not an object")
    return payload


def _invoke(raw: bytes, payload: dict) -> bytes:
    root = _root(payload.get("cwd", ""))
    home = pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir)
    python_candidates = (
        root / "python" / ".venv" / "bin" / "python",
        home / ".venvs" / "dotfiles-python" / "bin" / "python",
    )
    python = next((path for path in python_candidates if path.is_file()), None)
    hook = root / "python" / "src" / "dotfiles_setup" / "codex_writer_lease_hook.py"
    if python is None:
        _fail("pinned project Python is unavailable")
    metadata = python.stat()
    if not stat.S_ISREG(metadata.st_mode) or not os.access(python, os.X_OK):
        _fail("pinned project Python is not executable")
    if not hook.is_file():
        _fail("tracked writer hook entrypoint is unavailable")
    result = subprocess.run(
        [str(python), "-I", "-S", str(hook)],
        input=raw,
        cwd=root,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        check=False,
        timeout=8,
    )
    if result.returncode != 0 or (not result.stdout and result.stderr):
        _fail("writer hook subprocess failed closed")
    return result.stdout


def main() -> int:
    """Dispatch one native hook payload into the pinned project runtime."""
    raw = sys.stdin.buffer.read()
    event = "PreToolUse"
    try:
        payload = _load_payload(raw)
        payload_event = payload.get("hook_event_name")
        if isinstance(payload_event, str):
            event = payload_event
        output = _invoke(raw, payload)
    except (
        json.JSONDecodeError,
        OSError,
        RunnerError,
        subprocess.SubprocessError,
        UnicodeDecodeError,
    ) as exc:
        _deny(event, f"Writer lease enforcement failed closed: {exc}.")
        return 0
    else:
        sys.stdout.buffer.write(output)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
