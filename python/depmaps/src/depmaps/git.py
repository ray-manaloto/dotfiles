"""git on a dependency's bare clone: clone, fetch a tag, worktrees, diffs."""

from pathlib import Path

from .events import DepmapsError
from .models import ErrorCode
from .process import run


def git(*args: str | Path, cwd: Path) -> str:
    try:
        done = run("git", *args, cwd=cwd, timeout=None)
    except OSError as error:
        raise DepmapsError(ErrorCode.git_failed, f"depmaps: git: {error}") from None
    if done.returncode:
        shown = " ".join(str(arg) for arg in args)
        raise DepmapsError(ErrorCode.git_failed, f"depmaps: git {shown}: {done.stderr.strip()}")
    return done.stdout


def tagged(bare: Path, tag: str) -> str | None:
    done = run("git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}", cwd=bare, timeout=None)
    return done.stdout.strip() if done.returncode == 0 else None


def commit(repo: str, bare: Path, tag: str) -> str:
    """The commit the tag points at: from the bare clone, cloning it and fetching the tag as needed."""
    if not bare.exists():
        bare.parent.mkdir(parents=True, exist_ok=True)
        git("clone", "--bare", "--quiet", repo, bare, cwd=bare.parent)
    found = tagged(bare, tag)
    if found is None:
        # A bare clone has no fetch refspec, so a release tagged after the clone is fetched by name.
        run("git", "fetch", "--quiet", "origin", f"refs/tags/{tag}:refs/tags/{tag}", cwd=bare, timeout=None)
        found = tagged(bare, tag)
    if found is None:
        raise DepmapsError(ErrorCode.version_unavailable, f"depmaps: {repo} has no tag {tag}")
    return found
