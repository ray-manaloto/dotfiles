"""Copy a checkout's files, never what git ignores, for tests that need the repo outside the real checkout.

A copy of the whole folder takes every build output with it. On 2026-11-13 a worktree's swift/.build held a 24 GB
compilation cache (CompilationCache.noindex/.../data.v1); nine copies at once under pytest -n auto took free space
from 279 GiB to 32 GiB. The tracked files and the untracked ones git does not ignore are a few hundred MB.
"""

import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def copy_checkout(dest: Path, source: Path = REPO) -> Path:
    """dest holding source's tracked files and its untracked, unignored ones (git ls-files --exclude-standard)."""
    listed = subprocess.run(
        ["git", "-C", source, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    dest.mkdir(parents=True)
    for name in sorted(set(listed.split("\0")[:-1])):
        path = source / name
        if path.is_symlink() or path.exists():  # a file deleted but not yet staged is gone
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest / name, follow_symlinks=False)
    return dest
