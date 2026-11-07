"""git on a dependency's bare clone: clone, fetch a tag, worktrees, diffs."""

import subprocess
from pathlib import Path

from .events import DepmapsError
from .models import ErrorCode
from .process import run

# git ls-remote --exit-code exits 2 when origin has no matching ref, so a missing tag is told apart from
# an origin that can't be read, such as offline.
NO_SUCH_REF = 2


def call(*args: str | Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return run("git", *args, cwd=cwd, timeout=None)
    except OSError as error:
        raise DepmapsError(ErrorCode.git_failed, f"depmaps: git: {error}") from None


def failed(args: tuple[str | Path, ...], done: subprocess.CompletedProcess[str]) -> DepmapsError:
    shown = " ".join(str(arg) for arg in args)
    return DepmapsError(ErrorCode.git_failed, f"depmaps: git {shown}: {done.stderr.strip()}")


def git(*args: str | Path, cwd: Path) -> str:
    done = call(*args, cwd=cwd)
    if done.returncode:
        raise failed(args, done)
    return done.stdout


def tagged(bare: Path, tag: str) -> str | None:
    done = call("rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}", cwd=bare)
    return done.stdout.strip() if done.returncode == 0 else None


def commit(repo: str, bare: Path, tag: str) -> str:
    """The commit the tag points at: from the bare clone, cloning it and fetching the tag as needed."""
    if not bare.exists():
        bare.parent.mkdir(parents=True, exist_ok=True)
        git("clone", "--bare", "--quiet", repo, bare, cwd=bare.parent)
    found = tagged(bare, tag)
    if found is not None:
        return found
    listed = ("ls-remote", "--exit-code", "origin", f"refs/tags/{tag}")
    done = call(*listed, cwd=bare)
    if done.returncode == NO_SUCH_REF:
        raise DepmapsError(ErrorCode.version_unavailable, f"depmaps: {repo} has no tag {tag}")
    if done.returncode:
        raise failed(listed, done)
    # A bare clone has no fetch refspec, so a release tagged after the clone is fetched by name.
    git("fetch", "--quiet", "origin", f"refs/tags/{tag}:refs/tags/{tag}", cwd=bare)
    return git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}", cwd=bare).strip()
