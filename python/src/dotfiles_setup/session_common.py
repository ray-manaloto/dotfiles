# Copyright (c) 2026 Raymond Manaloto
"""Shared session identity, names, repository resolution and locked state.

Use the OS's advisory flock and atomic replace rather than a homegrown lock
protocol. The stable .json.lock inode covers the entire read-modify-write;
locking the JSON inode itself would stop protecting it after replacement.
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    Runner = Callable[..., subprocess.CompletedProcess[str]]

CHICAGO = ZoneInfo("America/Chicago")
PROJECT = "dotfiles"
SHORT_ID_LEN = 8
MAIN_CHECKOUT_TIMEOUT_S = 30
STATE_LOCK_TIMEOUT_S = 10.0
_LOCK_POLL_S = 0.05
_NS_PER_S = 1_000_000_000
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_MINUTE = 60
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,}$")


class SessionError(RuntimeError):
    """A required session or repository fact could not be established."""


class StateLockedError(OSError):
    """The bounded exclusive state lock could not be acquired."""


class StateUnreadableError(OSError):
    """Existing session state could not be read or decoded safely."""


def valid_session_id(session_id: str) -> bool:
    """Whether the id can safely become a state-file name."""
    return bool(_SESSION_ID_RE.fullmatch(session_id))


def read_json(path: Path) -> object:
    """Read optional harness JSON, failing closed when it is unavailable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None


def job_record_path(session_id: str, jobs_dir: Path) -> Path:
    """The harness job path; callers validate the full id before using it."""
    return jobs_dir / session_id[:SHORT_ID_LEN] / "state.json"


def job_record(session_id: str, jobs_dir: Path) -> dict[str, Any] | None:
    """Only a record carrying the exact full session id is trusted."""
    if not valid_session_id(session_id):
        return None
    data = read_json(job_record_path(session_id, jobs_dir))
    return (
        data if isinstance(data, dict) and data.get("sessionId") == session_id else None
    )


def session_name(session_id: str, jobs_dir: Path) -> str | None:
    """The exact job's top-level name, or None on any doubt."""
    record = job_record(session_id, jobs_dir)
    name = None if record is None else record.get("name")
    return name if isinstance(name, str) else None


def default_jobs_dir() -> Path:
    """The harness background-job directory."""
    return Path.home() / ".claude" / "jobs"


def read_state(path: Path) -> dict[str, Any]:
    """Missing state is new; corrupt or unreadable state must never reset it."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        msg = f"unreadable state {path}: {exc}"
        raise StateUnreadableError(msg) from exc
    if not isinstance(data, dict):
        msg = f"state {path} is not a JSON object"
        raise StateUnreadableError(msg)
    return data


def write_state(path: Path, state: Mapping[str, Any]) -> None:
    """Atomically replace JSON; callers hold state_lock for their transaction."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", "utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def state_lock(
    path: Path, *, timeout_s: float = STATE_LOCK_TIMEOUT_S
) -> Iterator[None]:
    """Exclusive flock on <state file>.lock, with a ten-second default bound."""
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    with path.with_suffix(path.suffix + ".lock").open("a", encoding="utf-8") as lock:
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                    raise
                if time.monotonic() >= deadline:
                    msg = f"state-locked: {path} after {timeout_s:g}s"
                    raise StateLockedError(msg) from exc
                time.sleep(min(_LOCK_POLL_S, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def now_iso() -> str:
    """Chicago wall time for state-file stamps."""
    return datetime.now(CHICAGO).isoformat(timespec="seconds")


def _offset_suffix(offset_s: int) -> str:
    if offset_s == 0:
        return "Z"
    sign = "+" if offset_s > 0 else "-"
    hours, rest = divmod(abs(offset_s), _SECONDS_PER_HOUR)
    minutes = rest // _SECONDS_PER_MINUTE
    return f"{sign}{hours:02d}{minutes:02d}" if minutes else f"{sign}{hours:02d}"


def chicago_stamp(now_ns: int) -> str:
    """Chicago yyyyMMdd'T'HHmmss.<9-digit ns><ISO X offset>."""
    seconds, nanos = divmod(now_ns, _NS_PER_S)
    moment = datetime.fromtimestamp(seconds, tz=CHICAGO)
    offset = moment.utcoffset()
    offset_s = 0 if offset is None else int(offset.total_seconds())
    return f"{moment:%Y%m%dT%H%M%S}.{nanos:09d}{_offset_suffix(offset_s)}"


def stamped_name(project: str, feature: str, now_ns: int) -> str:
    """One session-name formatter for both independently loaded plugins."""
    return f"{project}-{chicago_stamp(now_ns)}.{feature}"


def main_checkout(cwd: Path, *, runner: Runner | None = None) -> Path:
    """First git worktree porcelain entry, resolved from the caller's repo."""
    try:
        result = (runner or subprocess.run)(
            ["git", "-C", str(cwd), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=MAIN_CHECKOUT_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"git worktree list failed: {exc}"
        raise SessionError(msg) from exc
    if result.returncode != 0:
        msg = f"git worktree list exited {result.returncode}: {result.stderr.strip()}"
        raise SessionError(msg)
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            return Path(line.removeprefix("worktree ")).resolve()
    msg = "git worktree list printed no worktree entry"
    raise SessionError(msg)
