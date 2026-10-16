# Copyright (c) 2026 Raymond Manaloto
"""Bounded local evidence reads that never follow links or block on FIFOs."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

MANIFEST_LIMIT = 1024 * 1024


def read_regular_bounded(path: Path, limit: int) -> bytes:
    """Walk directories by descriptor, then inspect and cap the opened leaf."""
    absolute = path.absolute()
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(absolute.anchor, directory_flags)
    try:
        for component in absolute.parts[1:-1]:
            child = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
        flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
        leaf = os.open(absolute.name, flags, dir_fd=directory)
    finally:
        os.close(directory)
    with os.fdopen(leaf, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            message = "research evidence is not a regular file"
            raise OSError(message)
        if info.st_size > limit:
            message = "research evidence too large"
            raise ValueError(message)
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        message = "research evidence too large"
        raise ValueError(message)
    return raw
