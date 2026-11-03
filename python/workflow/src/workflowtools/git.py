"""git, run checked, and the paths every check starts from."""

import subprocess
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, check=True, text=True).stdout


def top() -> Path:
    return Path(git("rev-parse", "--show-toplevel").strip())


def tracked(*pathspecs: str) -> list[str]:
    """Paths in the index, relative to the top, that match a pathspec."""
    return [path for path in git("-C", str(top()), "ls-files", "-z", "--", *pathspecs).split("\0") if path]


def staged(path: str) -> str:
    """The index's copy of a path: what a commit would hold, whatever the worktree has."""
    blob = subprocess.run(["git", "-C", str(top()), "show", f":{path}"], capture_output=True, check=True)
    return blob.stdout.decode(errors="replace")
