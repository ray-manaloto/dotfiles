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


def main_checkout() -> Path:
    """The main worktree, where Claude Code keeps a repository's project files; this one when the repository is bare."""
    first = git("worktree", "list", "--porcelain").split("\n\n")[0].splitlines()
    return top() if "bare" in first else Path(first[0].removeprefix("worktree "))


def staged(path: str) -> str:
    """The index's copy of a path, relative to the top: what a commit would hold, whatever the worktree has."""
    # Index paths are relative to the top from any directory; errors="replace" keeps stdout and stderr text.
    return subprocess.run(["git", "show", f":{path}"], capture_output=True, check=True, errors="replace").stdout
