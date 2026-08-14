# Copyright (c) 2026 Raymond Manaloto
"""Fail-closed single-writer ownership for one Git common directory (#753).

The retained ``flock`` is the exclusion primitive. A loopback challenge binds
the canonical receipt to the process that actually owns that lock. Receipt,
audit, and in-flight state are immutable content-addressed generations; one
atomic pointer publishes the three files as a transaction.
"""

from __future__ import annotations

import errno
import fcntl
import functools
import hashlib
import json
import os
import pwd
import shlex
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import uuid
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterator, Mapping

SCHEMA = "dotfiles.writer-lease.v2"
STATE_DIRNAME = "codex-writer-lease"
LOCK_FILENAME = "writer.lock"
STATE_LOCK_FILENAME = "state.lock"
CURRENT_FILENAME = "current"
RECEIPT_FILENAME = "receipt.json"
AUDIT_FILENAME = "audit.jsonl"
INFLIGHT_FILENAME = "inflight.json"
TRANSITIONS = ("initial", "handoff", "recovery")
MUTATION_TOOLS = frozenset({"Bash", "apply_patch", "Edit", "Write", "NotebookEdit"})
_AUDIT_EVENTS = frozenset({"acquired", "released", "tool_started", "tool_finished"})
_SHA256_LENGTH = 64
_REPOSITORY_IDENTITY_FIELD_COUNT = 3
_PRIVATE_DIR_MODE = 0o700
_PRIVATE_FILE_MODE = 0o600
_CHALLENGE_TIMEOUT_SECONDS = 0.5
_STATE_LOCK_RETRY_SECONDS = 3.0
_STATE_LOCK_RETRY_INTERVAL_SECONDS = 0.01
_MAX_TCP_PORT = 65535
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONTAINER_GIT_LOCK = _PROJECT_ROOT / ".devcontainer" / "mise-system.lock"
CONTAINER_GIT_INSTALL_ROOT = Path("/usr/local/share/mise/installs/conda-git")
_GENERATION_PREFIX = "gen-"
_RECLAIM_PREFIX = ".reclaim-"
_GENERATION_FILES = frozenset({RECEIPT_FILENAME, AUDIT_FILENAME, INFLIGHT_FILENAME})
_RECEIPT_KEYS = frozenset(
    {
        "acquired_at",
        "branch",
        "common_dir",
        "handoff_sha256",
        "holder_port",
        "holder_token",
        "lease_id",
        "owner",
        "pid",
        "prior_receipt_sha256",
        "schema",
        "task_id",
        "transition",
        "worktree",
    }
)
_AUDIT_KEYS = frozenset(
    {
        "at",
        "event",
        "prior_receipt_sha256",
        "receipt_sha256",
        "schema",
        "seq",
        "task_id",
        "tool_name",
        "tool_use_id",
        "transition",
    }
)
_INFLIGHT_KEYS = frozenset({"receipt_sha256", "session_id", "started_at", "tool_name"})
_LOCK_TOKEN_KEYS = frozenset({"holder_port", "holder_token", "pid", "schema"})


class LeaseError(RuntimeError):
    """A fail-closed lease state, acquisition, or ownership result."""


@dataclass(frozen=True)
class RepositoryIdentity:
    """Git-derived repository and worktree identity."""

    common_dir: Path
    worktree: Path
    branch: str


@dataclass(frozen=True)
class LeaseRequest:
    """Caller identity and content-addressed coordination handoff."""

    task_id: str
    owner: str
    handoff_sha256: str
    expected_prior_receipt_sha256: str | None
    expected_transition: str | None = None


@dataclass(frozen=True)
class StateSnapshot:
    """One atomically published ownership-state generation."""

    receipt: dict[str, Any]
    receipt_sha256: str
    audit: tuple[dict[str, Any], ...]
    inflight: dict[str, dict[str, str]]
    generation: str
    active_receipt_sha256: str | None


@dataclass(frozen=True)
class HolderEndpoint:
    """Challenge endpoint facts published by the live holder."""

    token: str
    port: int


@dataclass(frozen=True)
class _LeaseHandle:
    """The acquired descriptor and bytes needed for transactional rollback."""

    state_dir: Path
    fd: int
    previous_bytes: bytes


@dataclass(frozen=True)
class AuditEvent:
    """Fields for one canonical audit append."""

    event: str
    receipt_sha256: str
    task_id: str
    transition: str = ""
    prior_receipt_sha256: str = ""
    tool_name: str = ""
    tool_use_id: str = ""


@dataclass(frozen=True)
class HookInvocation:
    """Validated common fields from a Codex or Claude hook payload."""

    event: str
    identity: RepositoryIdentity
    session_id: str
    tool_name: str
    tool_use_id: str
    tool_input: object


@dataclass
class _History:
    """Mutable accumulator used only while validating immutable audit bytes."""

    active: str | None = None
    last_receipt: str = ""
    open_tools: dict[str, dict[str, str]] = field(default_factory=dict)


class _HolderServer:
    """Loopback challenge server proving which process owns the flock."""

    def __init__(self, holder_token: str) -> None:
        self._holder_token = holder_token
        self._stopped = threading.Event()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(4)
        self._socket.settimeout(0.2)
        self.port = int(self._socket.getsockname()[1])
        self._thread = threading.Thread(
            target=self._serve,
            name="writer-lease-holder-challenge",
            daemon=True,
        )

    def start(self) -> None:
        """Start answering bounded holder challenges."""
        self._thread.start()

    def close(self) -> None:
        """Stop accepting challenges and close the loopback endpoint."""
        self._stopped.set()
        self._socket.close()
        self._thread.join(timeout=1)

    def _serve(self) -> None:
        while not self._stopped.is_set():
            try:
                connection, _address = self._socket.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with connection:
                connection.settimeout(_CHALLENGE_TIMEOUT_SECONDS)
                try:
                    raw = connection.recv(4096)
                    payload = json.loads(raw)
                    nonce = payload.get("nonce") if isinstance(payload, dict) else None
                    if not isinstance(nonce, str) or not nonce:
                        continue
                    connection.sendall(
                        _canonical_bytes(
                            {
                                "holder_token": self._holder_token,
                                "nonce": nonce,
                                "schema": SCHEMA,
                            }
                        )
                    )
                except json.JSONDecodeError, OSError:
                    continue


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate_sha256(value: str, *, name: str) -> None:
    if (
        len(value) != _SHA256_LENGTH
        or value.lower() != value
        or any(char not in "0123456789abcdef" for char in value)
    ):
        message = f"{name} must be a lowercase SHA-256 digest"
        raise LeaseError(message)


def _validate_timestamp(value: str, *, name: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        message = f"{name} is invalid"
        raise LeaseError(message) from exc
    if parsed.tzinfo is None:
        message = f"{name} is not timezone-aware"
        raise LeaseError(message)


def _locked_git_version(payload: object) -> str:
    if not isinstance(payload, dict):
        message = "container Git lock root is not a table"
        raise LeaseError(message)
    try:
        entries = payload["tools"]["conda:git"]
    except (KeyError, TypeError) as exc:
        message = "container Git lock does not declare conda:git"
        raise LeaseError(message) from exc
    if not isinstance(entries, list) or len(entries) != 1:
        message = "container Git lock must bind exactly one conda:git entry"
        raise LeaseError(message)
    entry = entries[0]
    if not isinstance(entry, dict) or entry.get("backend") != "conda:git":
        message = "container Git lock conda:git backend is invalid"
        raise LeaseError(message)
    version = entry.get("version")
    if not isinstance(version, str) or not version:
        message = "container Git lock conda:git version is invalid"
        raise LeaseError(message)
    return version


@functools.cache
def container_git_executable(
    lock_path: Path = _CONTAINER_GIT_LOCK,
    *,
    install_root: Path = CONTAINER_GIT_INSTALL_ROOT,
) -> Path:
    """Derive the one conda-Git executable path from the committed lock."""
    try:
        with lock_path.open("rb") as stream:
            payload = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        message = f"container Git lock is unreadable: {exc}"
        raise LeaseError(message) from exc
    return install_root / _locked_git_version(payload) / "bin" / "git"


def trusted_git_executables(
    *,
    platform: str = sys.platform,
    filesystem_root: Path = Path("/"),
    lock_path: Path = _CONTAINER_GIT_LOCK,
) -> tuple[Path, ...]:
    """Return the one platform-authorized Git executable contract."""
    if platform == "darwin":
        return (filesystem_root / "usr" / "bin" / "git",)
    if platform.startswith("linux"):
        install_root = filesystem_root / CONTAINER_GIT_INSTALL_ROOT.relative_to("/")
        return (container_git_executable(lock_path, install_root=install_root),)
    message = f"unsupported writer-lease platform: {platform}"
    raise LeaseError(message)


@functools.cache
def git_executable(
    *,
    platform: str = sys.platform,
    filesystem_root: Path = Path("/"),
    lock_path: Path = _CONTAINER_GIT_LOCK,
) -> Path:
    """Resolve the platform's sole authorized Git executable exactly once."""
    (candidate,) = trusted_git_executables(
        platform=platform,
        filesystem_root=filesystem_root,
        lock_path=lock_path,
    )
    try:
        resolved = candidate.resolve(strict=True)
        metadata = resolved.stat()
    except OSError as exc:
        message = (
            f"trusted {platform.title()} Git executable is unavailable: {candidate}"
        )
        raise LeaseError(message) from exc
    if stat.S_ISREG(metadata.st_mode) and os.access(resolved, os.X_OK):
        return resolved
    message = f"trusted {platform.title()} Git executable is unavailable: {candidate}"
    raise LeaseError(message)


def _git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            [str(git_executable()), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        message = f"git could not resolve repository identity: {exc}"
        raise LeaseError(message) from exc
    if result.returncode != 0 or not result.stdout.strip():
        detail = result.stderr.strip() or f"git exited {result.returncode}"
        message = f"git could not resolve repository identity: {detail}"
        raise LeaseError(message)
    return result.stdout.strip()


def repository_identity(cwd: Path) -> RepositoryIdentity:
    """Return Git's shared repository identity and current worktree facts."""
    start = cwd.resolve()
    lines = _git(
        start,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
        "--show-toplevel",
        "--abbrev-ref",
        "HEAD",
    ).splitlines()
    if len(lines) != _REPOSITORY_IDENTITY_FIELD_COUNT:
        message = "git returned an incomplete repository identity"
        raise LeaseError(message)
    return RepositoryIdentity(
        Path(lines[0]).resolve(),
        Path(lines[1]).resolve(),
        lines[2],
    )


def _validate_private_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        message = f"unsafe writer lease directory: {exc}"
        raise LeaseError(message) from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != _PRIVATE_DIR_MODE
    ):
        message = (
            f"unsafe writer lease directory: {path} must be an owned 0700 directory"
        )
        raise LeaseError(message)


def _validate_private_directory_fd(fd: int, name: str) -> None:
    metadata = os.fstat(fd)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != _PRIVATE_DIR_MODE
    ):
        message = (
            f"unsafe writer lease directory: {name} must be an owned 0700 directory"
        )
        raise LeaseError(message)


def _open_private_directory(path: Path) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        message = f"unsafe writer lease directory: {exc}"
        raise LeaseError(message) from exc
    try:
        _validate_private_directory_fd(fd, str(path))
    except Exception:
        os.close(fd)
        raise
    return fd


def _open_private_directory_at(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        message = f"unsafe writer lease directory {name}: {exc}"
        raise LeaseError(message) from exc
    try:
        _validate_private_directory_fd(fd, name)
    except Exception:
        os.close(fd)
        raise
    return fd


def _state_directory(common_dir: Path, *, create: bool) -> Path | None:
    path = common_dir / STATE_DIRNAME
    try:
        path.lstat()
    except FileNotFoundError:
        if not create:
            return None
        with suppress(FileExistsError):
            path.mkdir(mode=_PRIVATE_DIR_MODE)
    except OSError as exc:
        message = f"unsafe writer lease directory: {exc}"
        raise LeaseError(message) from exc
    _validate_private_directory(path)
    return path


def _validate_private_regular(fd: int, path: Path) -> None:
    metadata = os.fstat(fd)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != _PRIVATE_FILE_MODE
    ):
        message = f"unsafe writer lease path: {path} must be an owned 0600 regular file"
        raise LeaseError(message)


def _open_private_regular(
    path: Path,
    *,
    read_write: bool,
    create: bool,
    exclusive: bool = False,
) -> int:
    flags = (os.O_RDWR if read_write else os.O_RDONLY) | os.O_CLOEXEC | os.O_NONBLOCK
    flags |= getattr(os, "O_NOFOLLOW", 0)
    if create:
        flags |= os.O_CREAT
    if exclusive:
        flags |= os.O_EXCL
    try:
        fd = os.open(path, flags, _PRIVATE_FILE_MODE)
    except OSError as exc:
        message = f"unsafe writer lease path {path}: {exc}"
        raise LeaseError(message) from exc
    try:
        _validate_private_regular(fd, path)
    except Exception:
        os.close(fd)
        raise
    return fd


def _read_fd(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _write_fd(fd: int, raw: bytes) -> None:
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    view = memoryview(raw)
    while view:
        written = os.write(fd, view)
        view = view[written:]
    os.fsync(fd)


@contextmanager
def _state_lock(
    state_dir: Path,
    *,
    create: bool,
    exclusive: bool,
    retry_seconds: float = 0.0,
) -> Iterator[None]:
    fd = _open_private_regular(
        state_dir / STATE_LOCK_FILENAME,
        read_write=create or exclusive,
        create=create,
    )
    operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    deadline = time.monotonic() + retry_seconds
    try:
        acquired = False
        while not acquired:
            try:
                fcntl.flock(fd, operation | fcntl.LOCK_NB)
                acquired = True
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    message = "writer lease state transaction is busy"
                    raise LeaseError(message) from exc
                time.sleep(min(_STATE_LOCK_RETRY_INTERVAL_SECONDS, remaining))
        yield
    finally:
        os.close(fd)


def _read_private_file(path: Path) -> bytes:
    fd = _open_private_regular(path, read_write=False, create=False)
    try:
        return _read_fd(fd)
    finally:
        os.close(fd)


def _read_private_file_at(parent_fd: int, name: str) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        message = f"unsafe writer lease path {name}: {exc}"
        raise LeaseError(message) from exc
    try:
        _validate_private_regular(fd, Path(name))
        return _read_fd(fd)
    finally:
        os.close(fd)


def _write_new_private_file(path: Path, raw: bytes) -> None:
    fd = _open_private_regular(
        path,
        read_write=True,
        create=True,
        exclusive=True,
    )
    try:
        _write_fd(fd, raw)
    finally:
        os.close(fd)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _validate_receipt(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != _RECEIPT_KEYS:
        message = "writer lease receipt has an unexpected schema"
        raise LeaseError(message)
    strings = _RECEIPT_KEYS - {"holder_port", "pid"}
    if any(not isinstance(payload.get(key), str) for key in strings):
        message = "writer lease receipt field types are invalid"
        raise LeaseError(message)
    required = strings - {"prior_receipt_sha256"}
    if any(not payload[key] for key in required):
        message = "writer lease receipt has an empty required field"
        raise LeaseError(message)
    if payload["schema"] != SCHEMA:
        message = "writer lease receipt schema is unsupported"
        raise LeaseError(message)
    _validate_receipt_numbers(payload)
    _validate_receipt_identifiers(payload)
    return payload


def _validate_receipt_numbers(payload: dict[str, Any]) -> None:
    for name in ("holder_port", "pid"):
        if type(payload.get(name)) is not int or payload[name] <= 0:
            message = f"writer lease receipt {name} is invalid"
            raise LeaseError(message)
    if payload["holder_port"] > _MAX_TCP_PORT:
        message = "writer lease receipt holder_port is invalid"
        raise LeaseError(message)


def _validate_receipt_identifiers(payload: dict[str, Any]) -> None:
    _validate_sha256(payload["handoff_sha256"], name="receipt handoff digest")
    _validate_sha256(payload["holder_token"], name="receipt holder token")
    if payload["prior_receipt_sha256"]:
        _validate_sha256(payload["prior_receipt_sha256"], name="receipt prior digest")
    if payload["transition"] not in TRANSITIONS:
        message = "writer lease receipt transition is invalid"
        raise LeaseError(message)
    _validate_timestamp(payload["acquired_at"], name="receipt acquisition timestamp")
    try:
        lease_id = uuid.UUID(payload["lease_id"])
    except ValueError as exc:
        message = "writer lease receipt lease ID is invalid"
        raise LeaseError(message) from exc
    if str(lease_id) != payload["lease_id"]:
        message = "writer lease receipt lease ID is not canonical"
        raise LeaseError(message)


def _validate_inflight(payload: object) -> dict[str, dict[str, str]]:
    if not isinstance(payload, dict):
        message = "writer lease in-flight state is invalid"
        raise LeaseError(message)
    validated: dict[str, dict[str, str]] = {}
    for tool_use_id, entry in payload.items():
        if not isinstance(tool_use_id, str) or not tool_use_id:
            message = "writer lease in-flight tool ID is invalid"
            raise LeaseError(message)
        if not isinstance(entry, dict) or set(entry) != _INFLIGHT_KEYS:
            message = "writer lease in-flight entry has an unexpected schema"
            raise LeaseError(message)
        if any(
            not isinstance(entry.get(key), str) or not entry[key]
            for key in _INFLIGHT_KEYS
        ):
            message = "writer lease in-flight entry fields are invalid"
            raise LeaseError(message)
        _validate_sha256(entry["receipt_sha256"], name="in-flight receipt digest")
        _validate_timestamp(entry["started_at"], name="in-flight start timestamp")
        validated[tool_use_id] = dict(entry)
    return validated


def _parse_audit(raw: bytes) -> tuple[dict[str, Any], ...]:
    if not raw:
        return ()
    if not raw.endswith(b"\n"):
        message = "writer lease audit is not newline-terminated"
        raise LeaseError(message)
    events: list[dict[str, Any]] = []
    for expected_seq, line in enumerate(raw.splitlines(), start=1):
        events.append(_parse_audit_event(line, expected_seq))
    return tuple(events)


def _parse_audit_event(line: bytes, expected_seq: int) -> dict[str, Any]:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        message = "writer lease audit contains malformed JSON"
        raise LeaseError(message) from exc
    if not isinstance(payload, dict) or set(payload) != _AUDIT_KEYS:
        message = "writer lease audit event has an unexpected schema"
        raise LeaseError(message)
    if _canonical_bytes(payload) != line:
        message = "writer lease audit event is not canonical JSON"
        raise LeaseError(message)
    if payload.get("schema") != SCHEMA or payload.get("seq") != expected_seq:
        message = "writer lease audit sequence or schema is invalid"
        raise LeaseError(message)
    string_keys = _AUDIT_KEYS - {"seq"}
    if any(not isinstance(payload.get(key), str) for key in string_keys):
        message = "writer lease audit field types are invalid"
        raise LeaseError(message)
    if payload["event"] not in _AUDIT_EVENTS:
        message = "writer lease audit event is unsupported"
        raise LeaseError(message)
    _validate_timestamp(payload["at"], name="audit timestamp")
    _validate_sha256(payload["receipt_sha256"], name="audit receipt digest")
    if payload["prior_receipt_sha256"]:
        _validate_sha256(payload["prior_receipt_sha256"], name="audit prior digest")
    return payload


def _validate_history(
    audit: tuple[dict[str, Any], ...],
    inflight: dict[str, dict[str, str]],
    receipt_digest: str,
) -> str | None:
    history = _History()
    for event in audit:
        kind = event["event"]
        if kind == "acquired":
            _validate_acquired(history, event)
        elif kind == "released":
            _validate_released(history, event)
        elif kind == "tool_started":
            _validate_tool_started(history, event)
        else:
            _validate_tool_finished(history, event)
    if history.last_receipt != receipt_digest:
        message = "writer lease audit does not terminate at the current receipt"
        raise LeaseError(message)
    if history.open_tools != inflight:
        message = "writer lease audit and in-flight state disagree"
        raise LeaseError(message)
    return history.active


def _validate_acquired(history: _History, event: dict[str, Any]) -> None:
    transition = event["transition"]
    if transition not in TRANSITIONS:
        message = "writer lease audit acquisition transition is invalid"
        raise LeaseError(message)
    if event["prior_receipt_sha256"] != history.last_receipt:
        message = "writer lease audit receipt chain is invalid"
        raise LeaseError(message)
    if transition == "initial" and history.last_receipt:
        message = "writer lease audit repeats an initial acquisition"
        raise LeaseError(message)
    if transition == "handoff" and history.active is not None:
        message = "writer lease audit labels an unreleased owner as handoff"
        raise LeaseError(message)
    if transition == "recovery" and history.active != history.last_receipt:
        message = "writer lease audit recovery lacks a stale active owner"
        raise LeaseError(message)
    if history.open_tools:
        message = "writer lease audit transfers with in-flight tools"
        raise LeaseError(message)
    history.active = event["receipt_sha256"]
    history.last_receipt = event["receipt_sha256"]


def _validate_released(history: _History, event: dict[str, Any]) -> None:
    if history.active != event["receipt_sha256"] or history.open_tools:
        message = "writer lease audit releases a non-active or busy owner"
        raise LeaseError(message)
    history.active = None


def _validate_tool_started(history: _History, event: dict[str, Any]) -> None:
    tool_use_id = event["tool_use_id"]
    if (
        history.active != event["receipt_sha256"]
        or not tool_use_id
        or tool_use_id in history.open_tools
    ):
        message = "writer lease audit tool start is invalid"
        raise LeaseError(message)
    history.open_tools[tool_use_id] = {
        "receipt_sha256": event["receipt_sha256"],
        "session_id": event["task_id"],
        "started_at": event["at"],
        "tool_name": event["tool_name"],
    }


def _validate_tool_finished(history: _History, event: dict[str, Any]) -> None:
    tool_use_id = event["tool_use_id"]
    entry = history.open_tools.get(tool_use_id)
    if (
        history.active != event["receipt_sha256"]
        or entry is None
        or entry["session_id"] != event["task_id"]
        or entry["tool_name"] != event["tool_name"]
    ):
        message = "writer lease audit tool finish is invalid"
        raise LeaseError(message)
    del history.open_tools[tool_use_id]


def _generation_digest(
    receipt_raw: bytes,
    audit_raw: bytes,
    inflight_raw: bytes,
) -> str:
    return _sha256(receipt_raw + b"\0" + audit_raw + b"\0" + inflight_raw)


def _read_snapshot(state_dir: Path) -> StateSnapshot | None:
    current_path = state_dir / CURRENT_FILENAME
    try:
        current_raw = _read_private_file(current_path)
    except LeaseError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            legacy = any(
                (state_dir / name).exists()
                for name in (RECEIPT_FILENAME, AUDIT_FILENAME)
            )
            if legacy:
                message = (
                    "unsafe legacy writer lease state requires preserved migration"
                )
                raise LeaseError(message) from exc
            return None
        raise
    try:
        generation = current_raw.decode("ascii")
    except UnicodeDecodeError as exc:
        message = "writer lease current generation is invalid"
        raise LeaseError(message) from exc
    if not generation.startswith(_GENERATION_PREFIX):
        message = "writer lease current generation is invalid"
        raise LeaseError(message)
    generation_digest = generation.removeprefix(_GENERATION_PREFIX)
    _validate_sha256(generation_digest, name="generation digest")
    generation_dir = state_dir / generation
    _validate_private_directory(generation_dir)
    receipt_raw = _read_private_file(generation_dir / RECEIPT_FILENAME)
    audit_raw = _read_private_file(generation_dir / AUDIT_FILENAME)
    inflight_raw = _read_private_file(generation_dir / INFLIGHT_FILENAME)
    if _generation_digest(receipt_raw, audit_raw, inflight_raw) != generation_digest:
        message = "writer lease generation digest does not match its files"
        raise LeaseError(message)
    try:
        receipt_payload = json.loads(receipt_raw)
        inflight_payload = json.loads(inflight_raw)
    except json.JSONDecodeError as exc:
        message = "writer lease generation contains malformed JSON"
        raise LeaseError(message) from exc
    receipt = _validate_receipt(receipt_payload)
    if _canonical_bytes(receipt) != receipt_raw:
        message = "writer lease receipt is not canonical JSON"
        raise LeaseError(message)
    inflight = _validate_inflight(inflight_payload)
    if _canonical_bytes(inflight) != inflight_raw:
        message = "writer lease in-flight state is not canonical JSON"
        raise LeaseError(message)
    audit = _parse_audit(audit_raw)
    receipt_digest = _sha256(receipt_raw)
    active = _validate_history(audit, inflight, receipt_digest)
    return StateSnapshot(receipt, receipt_digest, audit, inflight, generation, active)


def _audit_bytes(events: tuple[dict[str, Any], ...]) -> bytes:
    return b"".join(_canonical_bytes(event) + b"\n" for event in events)


def _names_at(directory_fd: int) -> tuple[str, ...]:
    with os.scandir(directory_fd) as entries:
        return tuple(entry.name for entry in entries)


def _generation_directories(state_fd: int) -> tuple[str, ...]:
    generations: list[str] = []
    for name in _names_at(state_fd):
        if not name.startswith(_GENERATION_PREFIX):
            continue
        generation_fd = _open_private_directory_at(state_fd, name)
        try:
            children = set(_names_at(generation_fd))
            if children != _GENERATION_FILES:
                message = f"unsafe writer lease generation contents: {name}"
                raise LeaseError(message)
            for child in children:
                _read_private_file_at(generation_fd, child)
        finally:
            os.close(generation_fd)
        generations.append(name)
    return tuple(generations)


def _remove_reclaim_directory(state_fd: int, name: str) -> None:
    reclaim_fd = _open_private_directory_at(state_fd, name)
    try:
        children = set(_names_at(reclaim_fd))
        if not children.issubset(_GENERATION_FILES):
            message = f"unsafe writer lease reclaim contents: {name}"
            raise LeaseError(message)
        for child in children:
            _read_private_file_at(reclaim_fd, child)
        for child in children:
            os.unlink(child, dir_fd=reclaim_fd)
        os.fsync(reclaim_fd)
    finally:
        os.close(reclaim_fd)
    os.rmdir(name, dir_fd=state_fd)


def _debt(kind: str, name: str) -> dict[str, str]:
    return {"kind": kind, "name": name}


def _cleanup_debt(state_fd: int, *, keep: str) -> tuple[dict[str, str], ...]:
    debt: list[dict[str, str]] = []
    for name in sorted(_names_at(state_fd)):
        if name.startswith(_RECLAIM_PREFIX):
            try:
                reclaim_fd = _open_private_directory_at(state_fd, name)
                try:
                    children = set(_names_at(reclaim_fd))
                finally:
                    os.close(reclaim_fd)
            except LeaseError:
                debt.append(_debt("malformed_reclaim", name))
            else:
                kind = (
                    "reclaim_pending"
                    if children.issubset(_GENERATION_FILES)
                    else "malformed_reclaim"
                )
                debt.append(_debt(kind, name))
        elif name.startswith(_GENERATION_PREFIX) and name != keep:
            debt.append(_debt("superseded_generation", name))
    return tuple(debt)


def reclaim_generations_anchored(
    state_fd: int,
    superseded: tuple[str, ...],
    *,
    keep: str,
) -> tuple[dict[str, str], ...]:
    """Reclaim superseded state relative to one already-validated directory fd."""
    debt: list[dict[str, str]] = []
    try:
        names = _names_at(state_fd)
    except OSError:
        return (_debt("reclaim_scan_failed", "state"),)
    for stale in names:
        if not stale.startswith(_RECLAIM_PREFIX):
            continue
        try:
            _remove_reclaim_directory(state_fd, stale)
        except LeaseError, OSError:
            debt.append(_debt("reclaim_pending", stale))
    for old in superseded:
        if old == keep:
            continue
        reclaim = f"{_RECLAIM_PREFIX}{uuid.uuid4().hex}"
        try:
            os.rename(
                old,
                reclaim,
                src_dir_fd=state_fd,
                dst_dir_fd=state_fd,
            )
            os.fsync(state_fd)
            _remove_reclaim_directory(state_fd, reclaim)
        except LeaseError, OSError:
            debt.append(_debt("reclaim_pending", reclaim))
    try:
        os.fsync(state_fd)
        debt.extend(_cleanup_debt(state_fd, keep=keep))
    except LeaseError, OSError:
        debt.append(_debt("reclaim_scan_failed", "state"))
    unique = {(item["kind"], item["name"]): item for item in debt}
    return tuple(unique[key] for key in sorted(unique))


def _publish_generation_anchored(
    state_dir: Path,
    state_fd: int,
    receipt: Mapping[str, object],
    audit: tuple[dict[str, Any], ...],
    inflight: Mapping[str, object],
) -> StateSnapshot:
    superseded = _generation_directories(state_fd)
    receipt_raw = _canonical_bytes(receipt)
    audit_raw = _audit_bytes(audit)
    inflight_raw = _canonical_bytes(inflight)
    digest = _generation_digest(receipt_raw, audit_raw, inflight_raw)
    generation = f"{_GENERATION_PREFIX}{digest}"
    generation_dir = state_dir / generation
    try:
        generation_dir.mkdir(mode=_PRIVATE_DIR_MODE)
    except FileExistsError:
        _validate_private_directory(generation_dir)
        if (
            _read_private_file(generation_dir / RECEIPT_FILENAME) != receipt_raw
            or _read_private_file(generation_dir / AUDIT_FILENAME) != audit_raw
            or _read_private_file(generation_dir / INFLIGHT_FILENAME) != inflight_raw
        ):
            message = "writer lease generation digest collision"
            raise LeaseError(message) from None
    else:
        _write_new_private_file(generation_dir / RECEIPT_FILENAME, receipt_raw)
        _write_new_private_file(generation_dir / AUDIT_FILENAME, audit_raw)
        _write_new_private_file(generation_dir / INFLIGHT_FILENAME, inflight_raw)
        _fsync_directory(generation_dir)

    current = state_dir / CURRENT_FILENAME
    if current.exists():
        _read_private_file(current)
    descriptor, temp_name = tempfile.mkstemp(prefix=".current.", dir=state_dir)
    temp = Path(temp_name)
    try:
        os.fchmod(descriptor, _PRIVATE_FILE_MODE)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(generation.encode("ascii"))
            stream.flush()
            os.fsync(stream.fileno())
        validation_fd = _open_private_regular(temp, read_write=False, create=False)
        os.close(validation_fd)
        temp.replace(current)
        _fsync_directory(state_dir)
    finally:
        temp.unlink(missing_ok=True)
    snapshot = _read_snapshot(state_dir)
    if snapshot is None:
        message = "writer lease transaction did not publish a generation"
        raise LeaseError(message)
    reclaim_generations_anchored(state_fd, superseded, keep=generation)
    return snapshot


def _publish_generation(
    state_dir: Path,
    receipt: Mapping[str, object],
    audit: tuple[dict[str, Any], ...],
    inflight: Mapping[str, object],
) -> StateSnapshot:
    state_fd = _open_private_directory(state_dir)
    try:
        return _publish_generation_anchored(
            state_dir,
            state_fd,
            receipt,
            audit,
            inflight,
        )
    finally:
        os.close(state_fd)


def _event(
    audit: tuple[dict[str, Any], ...],
    value: AuditEvent,
) -> tuple[dict[str, Any], ...]:
    entry = {
        "at": _now(),
        "event": value.event,
        "prior_receipt_sha256": value.prior_receipt_sha256,
        "receipt_sha256": value.receipt_sha256,
        "schema": SCHEMA,
        "seq": len(audit) + 1,
        "task_id": value.task_id,
        "tool_name": value.tool_name,
        "tool_use_id": value.tool_use_id,
        "transition": value.transition,
    }
    return (*audit, entry)


def _derive_transition(
    prior: StateSnapshot | None,
    expected_prior_receipt_sha256: str | None,
) -> tuple[str, str]:
    if prior is None:
        if expected_prior_receipt_sha256 is not None:
            message = "initial acquisition forbids a prior receipt digest"
            raise LeaseError(message)
        return "initial", ""
    if expected_prior_receipt_sha256 is None:
        message = "prior receipt exists; its exact digest is required"
        raise LeaseError(message)
    _validate_sha256(
        expected_prior_receipt_sha256,
        name="expected prior receipt digest",
    )
    if expected_prior_receipt_sha256 != prior.receipt_sha256:
        message = "expected prior receipt digest does not match stored receipt"
        raise LeaseError(message)
    if prior.inflight:
        message = (
            "prior writer still has in-flight mutation tools; "
            "drain them before transfer"
        )
        raise LeaseError(message)
    transition = "handoff" if prior.active_receipt_sha256 is None else "recovery"
    return transition, prior.receipt_sha256


def _new_receipt(
    identity: RepositoryIdentity,
    request: LeaseRequest,
    holder: HolderEndpoint,
    transition: str,
    prior_receipt_sha256: str,
) -> dict[str, object]:
    return {
        "acquired_at": _now(),
        "branch": identity.branch,
        "common_dir": str(identity.common_dir),
        "handoff_sha256": request.handoff_sha256,
        "holder_port": holder.port,
        "holder_token": holder.token,
        "lease_id": str(uuid.uuid4()),
        "owner": request.owner,
        "pid": os.getpid(),
        "prior_receipt_sha256": prior_receipt_sha256,
        "schema": SCHEMA,
        "task_id": request.task_id,
        "transition": transition,
        "worktree": str(identity.worktree),
    }


def _lock_token(receipt: Mapping[str, object]) -> dict[str, object]:
    return {
        "holder_port": receipt["holder_port"],
        "holder_token": receipt["holder_token"],
        "pid": receipt["pid"],
        "schema": SCHEMA,
    }


def _read_lock_token(fd: int) -> dict[str, Any]:
    raw = _read_fd(fd)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        message = "writer lease lock has an invalid holder token"
        raise LeaseError(message) from exc
    if not isinstance(payload, dict) or set(payload) != _LOCK_TOKEN_KEYS:
        message = "writer lease lock holder token has an unexpected schema"
        raise LeaseError(message)
    if _canonical_bytes(payload) != raw or payload.get("schema") != SCHEMA:
        message = "writer lease lock holder token is not canonical"
        raise LeaseError(message)
    if not isinstance(payload.get("holder_token"), str):
        message = "writer lease lock holder token is invalid"
        raise LeaseError(message)
    _validate_sha256(payload["holder_token"], name="lock holder token")
    for name in ("holder_port", "pid"):
        if type(payload.get(name)) is not int or payload[name] <= 0:
            message = f"writer lease lock {name} is invalid"
            raise LeaseError(message)
    return payload


def _challenge_holder(port: int, token: str) -> bool:
    nonce = uuid.uuid4().hex
    try:
        with socket.create_connection(
            ("127.0.0.1", port), timeout=_CHALLENGE_TIMEOUT_SECONDS
        ) as connection:
            connection.sendall(_canonical_bytes({"nonce": nonce}) + b"\n")
            connection.settimeout(_CHALLENGE_TIMEOUT_SECONDS)
            raw = connection.recv(4096)
        payload = json.loads(raw)
    except json.JSONDecodeError, OSError:
        return False
    return payload == {"holder_token": token, "nonce": nonce, "schema": SCHEMA}


def _holder_is_live(state_dir: Path, snapshot: StateSnapshot) -> bool:
    lock_fd = _open_private_regular(
        state_dir / LOCK_FILENAME,
        read_write=False,
        create=False,
    )
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                raise
        else:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            return False
        token = _read_lock_token(lock_fd)
    finally:
        os.close(lock_fd)
    receipt = snapshot.receipt
    if token != _lock_token(receipt) or snapshot.active_receipt_sha256 is None:
        return False
    return _challenge_holder(receipt["holder_port"], receipt["holder_token"])


def _owned_snapshot(
    identity: RepositoryIdentity,
    *,
    task_id: str,
    handoff_sha256: str | None,
) -> tuple[Path, StateSnapshot]:
    state_dir = _state_directory(identity.common_dir, create=False)
    if state_dir is None:
        message = "no writer lease state exists for this Git common directory"
        raise LeaseError(message)
    snapshot = _read_snapshot(state_dir)
    if snapshot is None or not _holder_is_live(state_dir, snapshot):
        message = "receipt is not bound to the live holder"
        raise LeaseError(message)
    receipt = snapshot.receipt
    if receipt["common_dir"] != str(identity.common_dir):
        message = "receipt Git common directory identity does not match"
        raise LeaseError(message)
    if receipt["worktree"] != str(identity.worktree):
        message = "live lease worktree identity does not match"
        raise LeaseError(message)
    if receipt["task_id"] != task_id:
        message = "live lease task identity does not match"
        raise LeaseError(message)
    if handoff_sha256 is not None and receipt["handoff_sha256"] != handoff_sha256:
        message = "live lease handoff digest does not match"
        raise LeaseError(message)
    return state_dir, snapshot


def _acquire_writer_lock(state_dir: Path) -> tuple[int, bytes]:
    lease_fd = _open_private_regular(
        state_dir / LOCK_FILENAME,
        read_write=True,
        create=True,
    )
    try:
        fcntl.flock(lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        os.close(lease_fd)
        if exc.errno in {errno.EACCES, errno.EAGAIN}:
            message = "a live writer already owns this Git common directory"
            raise LeaseError(message) from exc
        raise
    return lease_fd, _read_fd(lease_fd)


def _publish_new_holder(
    identity: RepositoryIdentity,
    lease: _LeaseHandle,
    request: LeaseRequest,
    endpoint: HolderEndpoint,
) -> StateSnapshot:
    with _state_lock(lease.state_dir, create=True, exclusive=True):
        prior = _read_snapshot(lease.state_dir)
        transition, prior_digest = _derive_transition(
            prior, request.expected_prior_receipt_sha256
        )
        if (
            request.expected_transition is not None
            and request.expected_transition != transition
        ):
            message = (
                f"audit facts require {transition}, not {request.expected_transition}"
            )
            raise LeaseError(message)
        receipt = _new_receipt(
            identity,
            request,
            endpoint,
            transition,
            prior_digest,
        )
        receipt_digest = _sha256(_canonical_bytes(receipt))
        audit = prior.audit if prior is not None else ()
        audit = _event(
            audit,
            AuditEvent(
                event="acquired",
                receipt_sha256=receipt_digest,
                task_id=request.task_id,
                transition=transition,
                prior_receipt_sha256=prior_digest,
            ),
        )
        _write_fd(lease.fd, _canonical_bytes(_lock_token(receipt)))
        try:
            return _publish_generation(lease.state_dir, receipt, audit, {})
        except Exception:
            _write_fd(lease.fd, lease.previous_bytes)
            raise


@contextmanager
def _release_signals(release_requested: threading.Event) -> Iterator[None]:
    def _release(_signum: int, _frame: object) -> None:
        release_requested.set()

    previous_term = signal.signal(signal.SIGTERM, _release)
    previous_int = signal.signal(signal.SIGINT, _release)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)


def _release_when_drained(
    state_dir: Path,
    lease_fd: int,
    snapshot: StateSnapshot,
    request: LeaseRequest,
) -> None:
    while True:
        with _state_lock(
            state_dir,
            create=False,
            exclusive=True,
            retry_seconds=_STATE_LOCK_RETRY_SECONDS,
        ):
            current = _read_snapshot(state_dir)
            if current is None or current.receipt_sha256 != snapshot.receipt_sha256:
                message = "writer lease state changed beneath the live holder"
                raise LeaseError(message)
            if not current.inflight:
                audit = _event(
                    current.audit,
                    AuditEvent(
                        event="released",
                        receipt_sha256=current.receipt_sha256,
                        task_id=request.task_id,
                    ),
                )
                _publish_generation(
                    state_dir,
                    current.receipt,
                    audit,
                    current.inflight,
                )
                _write_fd(lease_fd, b"")
                return
        time.sleep(0.05)


def hold(cwd: Path, *, request: LeaseRequest) -> int:
    """Acquire, publish, and retain one repository writer lease."""
    if not request.task_id.strip() or not request.owner.strip():
        message = "task ID and owner must be non-empty"
        raise LeaseError(message)
    _validate_sha256(request.handoff_sha256, name="handoff digest")
    identity = repository_identity(cwd)
    state_dir = _state_directory(identity.common_dir, create=True)
    if state_dir is None:
        message = "writer lease state directory could not be created"
        raise LeaseError(message)
    lease_fd, previous_lock_bytes = _acquire_writer_lock(state_dir)
    lease = _LeaseHandle(state_dir, lease_fd, previous_lock_bytes)
    holder_token = os.urandom(32).hex()
    server = _HolderServer(holder_token)
    server.start()
    try:
        snapshot = _publish_new_holder(
            identity,
            lease,
            request,
            HolderEndpoint(holder_token, server.port),
        )
        sys.stdout.write(
            _canonical_bytes(
                {
                    "receipt": snapshot.receipt,
                    "receipt_sha256": snapshot.receipt_sha256,
                    "status": "held",
                }
            ).decode("utf-8")
            + "\n"
        )
        sys.stdout.flush()
        release_requested = threading.Event()
        with _release_signals(release_requested):
            release_requested.wait()
            _release_when_drained(state_dir, lease_fd, snapshot, request)
        return 0
    finally:
        server.close()
        os.close(lease_fd)


def check(cwd: Path, *, task_id: str, handoff_sha256: str) -> int:
    """Fail closed unless the named task owns the live lease in this worktree."""
    _validate_sha256(handoff_sha256, name="handoff digest")
    identity = repository_identity(cwd)
    state_dir = _state_directory(identity.common_dir, create=False)
    if state_dir is None:
        message = "no writer lease state exists for this Git common directory"
        raise LeaseError(message)
    with _state_lock(state_dir, create=False, exclusive=False):
        _state, snapshot = _owned_snapshot(
            identity,
            task_id=task_id,
            handoff_sha256=handoff_sha256,
        )
    sys.stdout.write(
        _canonical_bytes(
            {
                "receipt_sha256": snapshot.receipt_sha256,
                "status": "owned",
                "task_id": task_id,
                "worktree": str(identity.worktree),
            }
        ).decode("utf-8")
        + "\n"
    )
    return 0


def status(cwd: Path) -> int:
    """Report live/stale/absent ownership without creating or changing state."""
    identity = repository_identity(cwd)
    state_dir = _state_directory(identity.common_dir, create=False)
    if state_dir is None:
        payload = {
            "cleanup_debt": [],
            "common_dir": str(identity.common_dir),
            "state": "absent",
            "worktree": str(identity.worktree),
        }
    else:
        with _state_lock(state_dir, create=False, exclusive=False):
            snapshot = _read_snapshot(state_dir)
            if snapshot is None:
                state = "absent"
                payload = {
                    "cleanup_debt": [],
                    "common_dir": str(identity.common_dir),
                    "state": state,
                    "worktree": str(identity.worktree),
                }
            else:
                state = "live" if _holder_is_live(state_dir, snapshot) else "stale"
                state_fd = _open_private_directory(state_dir)
                try:
                    cleanup_debt = list(
                        _cleanup_debt(state_fd, keep=snapshot.generation)
                    )
                finally:
                    os.close(state_fd)
                payload = {
                    "cleanup_debt": cleanup_debt,
                    "common_dir": str(identity.common_dir),
                    "handoff_sha256": snapshot.receipt["handoff_sha256"],
                    "inflight": sorted(snapshot.inflight),
                    "owner": snapshot.receipt["owner"],
                    "receipt_sha256": snapshot.receipt_sha256,
                    "state": state,
                    "task_id": snapshot.receipt["task_id"],
                    "transition": snapshot.receipt["transition"],
                    "worktree": str(identity.worktree),
                }
    sys.stdout.write(_canonical_bytes(payload).decode("utf-8") + "\n")
    return 0


@functools.cache
def mise_executable() -> Path:
    """Resolve mise once from the explicit host/container install contract."""
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    candidates = (home / ".local" / "bin" / "mise", Path("/usr/local/bin/mise"))
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            metadata = resolved.stat()
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode) and os.access(resolved, os.X_OK):
            return resolved
    expected = ", ".join(str(path) for path in candidates)
    message = f"no trusted mise executable is available; expected one of: {expected}"
    raise LeaseError(message)


def _bootstrap_options(options: list[str]) -> dict[str, str] | None:
    allowed = {
        "--expected-prior-receipt-sha256",
        "--handoff-sha256",
        "--owner",
        "--task-id",
    }
    valid_length = len(options) in {6, 8}
    keys = options[::2]
    if not valid_length or any(key not in allowed for key in keys):
        return None
    values = dict(zip(keys, options[1::2], strict=True))
    required = {"--handoff-sha256", "--owner", "--task-id"}
    optional = required | {"--expected-prior-receipt-sha256"}
    return values if set(values) in (required, optional) else None


def _valid_bootstrap_digests(values: Mapping[str, str]) -> bool:
    try:
        _validate_sha256(values["--handoff-sha256"], name="handoff digest")
        prior = values.get("--expected-prior-receipt-sha256")
        if prior is not None:
            _validate_sha256(prior, name="expected prior receipt digest")
    except LeaseError:
        return False
    return True


def _bootstrap_command(
    command: object,
    identity: RepositoryIdentity,
    session_id: str,
) -> bool:
    if not isinstance(command, str):
        return False
    try:
        arguments = shlex.split(command, posix=True)
        mise = str(mise_executable())
    except LeaseError, ValueError:
        return False
    prefix = [mise, "-C", str(identity.worktree), "run"]
    if arguments == [*prefix, "writer-lease-status"]:
        return True
    if arguments[: len(prefix) + 2] != [*prefix, "writer-lease-hold", "--"]:
        return False
    values = _bootstrap_options(arguments[len(prefix) + 2 :])
    if values is None or not _valid_bootstrap_digests(values):
        return False
    return (
        values["--task-id"] == session_id and values["--owner"] == f"codex:{session_id}"
    )


def _begin_tool(
    identity: RepositoryIdentity,
    *,
    session_id: str,
    tool_name: str,
    tool_use_id: str,
) -> None:
    state_dir = _state_directory(identity.common_dir, create=False)
    if state_dir is None:
        message = "no writer lease state exists for this Git common directory"
        raise LeaseError(message)
    with _state_lock(
        state_dir,
        create=False,
        exclusive=True,
        retry_seconds=_STATE_LOCK_RETRY_SECONDS,
    ):
        _state, snapshot = _owned_snapshot(
            identity,
            task_id=session_id,
            handoff_sha256=None,
        )
        existing = snapshot.inflight.get(tool_use_id)
        if existing is not None:
            if (
                existing["session_id"] == session_id
                and existing["tool_name"] == tool_name
            ):
                return
            message = "tool-use ID is already owned by another in-flight mutation"
            raise LeaseError(message)
        audit = _event(
            snapshot.audit,
            AuditEvent(
                event="tool_started",
                receipt_sha256=snapshot.receipt_sha256,
                task_id=session_id,
                tool_name=tool_name,
                tool_use_id=tool_use_id,
            ),
        )
        inflight = dict(snapshot.inflight)
        inflight[tool_use_id] = {
            "receipt_sha256": snapshot.receipt_sha256,
            "session_id": session_id,
            "started_at": audit[-1]["at"],
            "tool_name": tool_name,
        }
        _publish_generation(state_dir, snapshot.receipt, audit, inflight)


def _finish_tool(
    identity: RepositoryIdentity,
    *,
    session_id: str,
    tool_name: str,
    tool_use_id: str,
) -> None:
    state_dir = _state_directory(identity.common_dir, create=False)
    if state_dir is None:
        message = "writer lease state disappeared before tool completion"
        raise LeaseError(message)
    with _state_lock(
        state_dir,
        create=False,
        exclusive=True,
        retry_seconds=_STATE_LOCK_RETRY_SECONDS,
    ):
        snapshot = _read_snapshot(state_dir)
        if snapshot is None:
            message = "writer lease receipt disappeared before tool completion"
            raise LeaseError(message)
        entry = snapshot.inflight.get(tool_use_id)
        if entry is None:
            message = "tool completion has no matching in-flight mutation"
            raise LeaseError(message)
        if entry["session_id"] != session_id or entry["tool_name"] != tool_name:
            message = "tool completion identity does not match its in-flight mutation"
            raise LeaseError(message)
        inflight = dict(snapshot.inflight)
        del inflight[tool_use_id]
        audit = _event(
            snapshot.audit,
            AuditEvent(
                event="tool_finished",
                receipt_sha256=snapshot.receipt_sha256,
                task_id=session_id,
                tool_name=tool_name,
                tool_use_id=tool_use_id,
            ),
        )
        _publish_generation(state_dir, snapshot.receipt, audit, inflight)


def _hook_fields(payload: object) -> HookInvocation:
    if not isinstance(payload, dict):
        message = "malformed hook payload"
        raise LeaseError(message)
    event = payload.get("hook_event_name")
    session_id = payload.get("session_id")
    cwd = payload.get("cwd", str(Path.cwd()))
    tool_name = payload.get("tool_name")
    tool_use_id = payload.get("tool_use_id")
    tool_input = payload.get("tool_input")
    if event not in {"PreToolUse", "PostToolUse", "PostToolUseFailure"}:
        message = "unsupported hook event"
        raise LeaseError(message)
    for name, value in (
        ("session identity", session_id),
        ("working directory", cwd),
        ("tool name", tool_name),
        ("tool-use ID", tool_use_id),
    ):
        if not isinstance(value, str) or not value:
            message = f"missing hook {name}"
            raise LeaseError(message)
    return HookInvocation(
        event,
        repository_identity(Path(cwd)),
        cast("str", session_id),
        cast("str", tool_name),
        cast("str", tool_use_id),
        tool_input,
    )


def hook_decision(payload: object) -> str | None:
    """Apply the synchronous Pre/Post tool ownership state machine."""
    try:
        invocation = _hook_fields(payload)
        if invocation.tool_name not in MUTATION_TOOLS:
            return None
        if (
            invocation.event == "PreToolUse"
            and invocation.tool_name == "Bash"
            and isinstance(invocation.tool_input, dict)
            and _bootstrap_command(
                invocation.tool_input.get("command"),
                invocation.identity,
                invocation.session_id,
            )
        ):
            return None
        if invocation.event == "PreToolUse":
            _begin_tool(
                invocation.identity,
                session_id=invocation.session_id,
                tool_name=invocation.tool_name,
                tool_use_id=invocation.tool_use_id,
            )
        else:
            _finish_tool(
                invocation.identity,
                session_id=invocation.session_id,
                tool_name=invocation.tool_name,
                tool_use_id=invocation.tool_use_id,
            )
    except LeaseError as exc:
        return f"Writer lease denied this tool call: {exc}."
    return None


def pretooluse_decision(
    session_id: str,
    tool_input: Mapping[str, object],
    *,
    tool_name: str = "Edit",
    tool_use_id: str = "legacy-direct-mutation",
) -> str | None:
    """Claude-compatible adapter for the shared PreToolUse state machine."""
    if not session_id or not tool_use_id:
        return None
    return hook_decision(
        {
            "cwd": str(Path.cwd()),
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "tool_input": tool_input,
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
        }
    )


def codex_pretooluse_decision(payload: object) -> str | None:
    """Backward-compatible name for the native Codex hook entrypoint."""
    return hook_decision(payload)


def writer_lease_main(args: argparse.Namespace, cwd: Path) -> int:
    """Dispatch the writer-lease CLI group with stable fail-closed errors."""
    try:
        if args.lease_operation == "hold":
            return hold(
                cwd,
                request=LeaseRequest(
                    task_id=args.task_id,
                    owner=args.owner,
                    handoff_sha256=args.handoff_sha256,
                    expected_prior_receipt_sha256=args.expected_prior_receipt_sha256,
                    expected_transition=args.expected_transition,
                ),
            )
        if args.lease_operation == "check":
            return check(
                cwd,
                task_id=args.task_id,
                handoff_sha256=args.handoff_sha256,
            )
        if args.lease_operation == "status":
            return status(cwd)
    except LeaseError as exc:
        sys.stderr.write(f"writer-lease: {exc}\n")
        return 2
    sys.stderr.write("writer-lease: requires hold, check, or status\n")
    return 2
