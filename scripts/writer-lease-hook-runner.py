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


def _open_root(candidate: pathlib.Path) -> int:
    """Open one unchanged plain directory and bind its inode."""
    metadata = candidate.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        _fail("writer hook runtime root is not a plain directory")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(candidate, flags)
    opened = os.fstat(fd)
    if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
        os.close(fd)
        _fail("writer hook runtime root changed while it was opened")
    return fd


def _open_relative(root_fd: int, parts: tuple[str, ...], *, kind: str) -> int:
    """Open a no-symlink path relative to one already-bound root."""
    fd = os.dup(root_fd)
    try:
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
            if index < len(parts) - 1:
                flags |= os.O_DIRECTORY
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        mode = os.fstat(fd).st_mode
        valid = (
            stat.S_ISREG(mode)
            if kind == "file"
            else stat.S_ISREG(mode) or stat.S_ISDIR(mode)
        )
        if not valid:
            _fail(f"writer hook runtime component is not a plain {kind}")
    except BaseException:
        os.close(fd)
        raise
    else:
        return fd


def _runtime(cwd: object) -> tuple[pathlib.Path, int, int]:
    """Bind exactly one complete runtime and its hook entrypoint."""
    if not isinstance(cwd, str) or not cwd:
        _fail("hook cwd is missing")
    current = pathlib.Path(cwd).resolve()
    candidates: list[tuple[pathlib.Path, int, int]] = []
    for candidate in (current, *current.parents):
        root_fd: int | None = None
        hook_fd: int | None = None
        try:
            root_fd = _open_root(candidate)
            git_fd = _open_relative(root_fd, (".git",), kind="file or directory")
            os.close(git_fd)
            runner_fd = _open_relative(
                root_fd, ("scripts", "writer-lease-hook-runner.py"), kind="file"
            )
            os.close(runner_fd)
            hook_fd = _open_relative(
                root_fd,
                ("python", "src", "dotfiles_setup", "codex_writer_lease_hook.py"),
                kind="file",
            )
        except (
            OSError,
            RunnerError,
        ):
            if hook_fd is not None:
                os.close(hook_fd)
            if root_fd is not None:
                os.close(root_fd)
            continue
        candidates.append((candidate, root_fd, hook_fd))
    if len(candidates) == 1:
        return candidates[0]
    for _candidate, root_fd, hook_fd in candidates:
        os.close(hook_fd)
        os.close(root_fd)
    if candidates:
        _fail("hook cwd has ambiguous complete writer-hook runtimes")
    _fail("hook cwd has no complete tracked writer-hook runtime")
    raise RunnerError


def _load_payload(raw: bytes) -> dict:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        _fail("hook payload is not an object")
    return payload


def _invoke(raw: bytes, payload: dict) -> bytes:
    root, root_fd, hook_fd = _runtime(payload.get("cwd", ""))
    try:
        home = pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir)
        python_candidates = (
            root / "python" / ".venv" / "bin" / "python",
            home / ".venvs" / "dotfiles-python" / "bin" / "python",
        )
        python = next((path for path in python_candidates if path.is_file()), None)
        if python is None:
            _fail("pinned project Python is unavailable")
        metadata = python.stat()
        if not stat.S_ISREG(metadata.st_mode) or not os.access(python, os.X_OK):
            _fail("pinned project Python is not executable")
        hook = root / "python" / "src" / "dotfiles_setup" / "codex_writer_lease_hook.py"
        bootstrap = (
            "import os,sys;"
            "p=sys.argv[1];f=int(sys.argv[2]);"
            "b=os.fdopen(f,'rb',closefd=False).read();"
            "g={'__name__':'__main__','__file__':p,'__package__':None};"
            "exec(compile(b,p,'exec'),g)"
        )
        result = subprocess.run(
            [str(python), "-I", "-S", "-c", bootstrap, str(hook), str(hook_fd)],
            input=raw,
            cwd=root,
            env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            capture_output=True,
            check=False,
            timeout=8,
            pass_fds=(hook_fd,),
        )
        if result.returncode != 0 or (not result.stdout and result.stderr):
            _fail("writer hook subprocess failed closed")
        return result.stdout
    finally:
        os.close(hook_fd)
        os.close(root_fd)


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
