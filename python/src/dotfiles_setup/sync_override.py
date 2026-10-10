# Copyright (c) 2026 Raymond Manaloto
"""Private, live override for one canonical devcontainer sync operation.

The override preserves the source devcontainer document, removes its terminal
repository smoke command, and waits for setup and post-start hooks before the
explicit sync verification. Direct ``mise run up`` retains the source behavior.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import select
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

OVERRIDE_PATH_ENV = "DOTFILES_SYNC_OVERRIDE_CONFIG"
OWNER_FD_ENV = "DOTFILES_SYNC_OWNER_FD"

_SMOKE_SUFFIX = " && scripts/devcontainer-smoke.sh"
_POST_CREATE_LINE = re.compile(
    r'(?m)^(?P<prefix>[ \t]*"postCreateCommand"[ \t]*:[ \t]*)'
    r'(?P<value>"(?:\\.|[^"\\])*")(?P<suffix>[ \t]*,?[ \t]*)$'
)
_WAIT_FOR_LINE = re.compile(r'(?m)^[ \t]*"waitFor"[ \t]*:')
_OVERRIDE_NAME = re.compile(r"\.sync-override-[A-Za-z0-9_-]+\.json")
_PRIVATE_FILE_MODE = 0o600


class SyncOverrideError(ValueError):
    """The source document or inherited override context is invalid."""


def derive_sync_override(source: str) -> str:
    """Remove terminal smoke and await setup before the explicit sync smoke.

    The narrow shape is intentional. If the lifecycle command becomes an
    array, object, or differently ordered string, sync must stop rather than
    accidentally omitting setup or another lifecycle hook.
    """
    matches = list(_POST_CREATE_LINE.finditer(source))
    if len(matches) != 1 or _WAIT_FOR_LINE.search(source):
        reason = "expected exactly one string postCreateCommand"
        raise SyncOverrideError(reason)
    match = matches[0]
    if not match.group("suffix").rstrip().endswith(","):
        reason = "postCreateCommand must be followed by another property"
        raise SyncOverrideError(reason)
    command = json.loads(match.group("value"))
    if not command.endswith(_SMOKE_SUFFIX):
        reason = "postCreateCommand does not end with repository smoke"
        raise SyncOverrideError(reason)
    setup = command[: -len(_SMOKE_SUFFIX)]
    if not setup or "scripts/devcontainer-smoke.sh" in setup:
        reason = "unrecognized postCreateCommand smoke shape"
        raise SyncOverrideError(reason)
    indent = match.group("prefix").partition('"')[0]
    replacement = (
        match.group("prefix")
        + json.dumps(setup)
        + match.group("suffix")
        + "\n"
        + indent
        + '"waitFor": "postStartCommand",'
    )
    return source[: match.start()] + replacement + source[match.end() :]


@dataclass(frozen=True)
class ActiveSyncOverride:
    """Temporary config and live owner descriptor for one sync operation."""

    path: Path
    owner_fd: int

    def child_env(self, base: Mapping[str, str]) -> dict[str, str]:
        """Add the override context to a child process environment."""
        env = dict(base)
        env[OVERRIDE_PATH_ENV] = str(self.path)
        env[OWNER_FD_ENV] = str(self.owner_fd)
        return env


@contextlib.contextmanager
def active_sync_override(workspace: Path) -> Iterator[ActiveSyncOverride]:
    """Give only descendants of this live owner access to the override.

    The pipe's writer remains private to this process. The reader is passed
    explicitly through mise to nested ``up`` tasks; EOF revokes it if this
    operation ends or its owner dies. The generated file sits beside the
    source config so native relative paths keep their original meaning.
    """
    directory = workspace / ".devcontainer"
    source = (directory / "devcontainer.json").read_text(encoding="utf-8")
    content = derive_sync_override(source)
    read_fd, write_fd = os.pipe()
    os.set_blocking(read_fd, False)
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".sync-override-",
            suffix=".json",
            dir=directory,
            delete=False,
        ) as stream:
            path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        yield ActiveSyncOverride(path=path, owner_fd=read_fd)
    finally:
        os.close(write_fd)
        os.close(read_fd)
        if path is not None:
            path.unlink(missing_ok=True)


def active_override_from_env(workspace: Path, env: Mapping[str, str]) -> Path | None:
    """Accept an override only from a live inherited owner and exact source.

    A path or environment variable on its own is never permission to skip the
    lifecycle smoke. Missing, closed, readable, or non-pipe descriptors fail.
    """
    path_text = env.get(OVERRIDE_PATH_ENV)
    fd_text = env.get(OWNER_FD_ENV)
    if path_text is None and fd_text is None:
        return None
    if not path_text or not fd_text or not fd_text.isdecimal():
        reason = "incomplete sync override owner context"
        raise SyncOverrideError(reason)
    fd = int(fd_text)
    try:
        descriptor = os.fstat(fd)
        readable, _, _ = select.select([fd], [], [], 0)
    except (OSError, ValueError) as exc:
        reason = "sync override owner is unavailable"
        raise SyncOverrideError(reason) from exc
    if not stat.S_ISFIFO(descriptor.st_mode) or readable:
        reason = "sync override owner is no longer active"
        raise SyncOverrideError(reason)

    path = Path(path_text)
    source_path = workspace / ".devcontainer" / "devcontainer.json"
    if (
        not _OVERRIDE_NAME.fullmatch(path.name)
        or path.parent.resolve() != source_path.parent.resolve()
    ):
        reason = "sync override path is outside the source directory"
        raise SyncOverrideError(reason)
    try:
        file_info = path.lstat()
        if (
            not stat.S_ISREG(file_info.st_mode)
            or stat.S_IMODE(file_info.st_mode) != _PRIVATE_FILE_MODE
            or file_info.st_uid != os.getuid()
            or file_info.st_nlink != 1
        ):
            reason = "sync override file has unsafe ownership or mode"
            raise SyncOverrideError(reason)
        expected = derive_sync_override(source_path.read_text(encoding="utf-8"))
        actual = path.read_text(encoding="utf-8")
    except OSError as exc:
        reason = "sync override file could not be verified"
        raise SyncOverrideError(reason) from exc
    if actual != expected:
        reason = "sync override no longer matches the source config"
        raise SyncOverrideError(reason)
    return path
