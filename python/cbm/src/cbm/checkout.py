"""Refuse live installs outside the primary checkout on main unless explicitly opted in."""

import os
import subprocess
from pathlib import Path

from . import config, process

CHECKOUT_FIELDS = 4  # Git dir, common dir, worktree flag, verified commit ID.
DEFAULT_GIT_TIMEOUT = 10
GIT_LOCATION = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
)  # fmt: skip


def install_timeout() -> float:
    message = f"cbm: CBM_INSTALL_GIT_TIMEOUT_SECONDS must be greater than 0 and at most {DEFAULT_GIT_TIMEOUT}"
    try:
        timeout = float(os.environ.get("CBM_INSTALL_GIT_TIMEOUT_SECONDS", DEFAULT_GIT_TIMEOUT))
    except ValueError:
        raise config.SettingError(message) from None
    if not 0 < timeout <= DEFAULT_GIT_TIMEOUT:
        raise config.SettingError(message)
    return timeout


def install_refusal() -> str | None:
    timeout = install_timeout()
    if os.environ.get("CBM_INSTALL_ALLOW_NON_MAIN") == "1":
        return None
    try:
        cwd = Path.cwd()
    except OSError as error:
        return f"cbm: current directory discovery could not run: {error}"
    # Mise pins cwd to the task's checkout, but a directly invoked CLI can load code from elsewhere.
    for label, folder in (("current directory", cwd), ("running package", Path(__file__).resolve().parent)):
        if message := checkout_refusal(folder, timeout):
            return f"cbm: {label}: {message}"
    return None


def checkout_refusal(folder: Path, timeout: float) -> str | None:
    refusal = (
        "install requires the primary checkout on main; run there or explicitly set "
        "CBM_INSTALL_ALLOW_NON_MAIN=1 to allow changing the live setup from another checkout"
    )
    # Remove location overrides, preserving Git configuration such as safe.directory.
    env = {key: value for key, value in os.environ.items() if key not in GIT_LOCATION}
    try:
        branch = process.run(
            "git", "symbolic-ref", "-q", "HEAD",
            env=env, cwd=folder, input_text=None, capture_output=True, timeout=timeout,
        )  # fmt: skip
        done = branch
        if not branch.returncode:
            done = process.run(
                "git", "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir",
                "--is-inside-work-tree", "--verify", "--quiet", "HEAD^{commit}",
                env=env, cwd=folder, input_text=None, capture_output=True, timeout=timeout,
            )  # fmt: skip
    # Startup, timeout and undecodable output refuse before any setup change.
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError) as error:
        return f"git checkout discovery could not run: {error}"
    # A detached HEAD or unborn branch is a policy refusal; rev-parse --verify --quiet
    # exits 1 without a diagnostic (git/git v2.56.0 builtin/rev-parse.c:581-585, 1168-1190).
    if done.returncode == 1:
        return refusal
    if done.returncode:
        return f"git checkout discovery exited {done.returncode}: {done.stderr.strip()}"
    # git/git v2.56.0 worktree.c:68-79 compares gitdir with commondir to identify linked worktrees.
    # setup.c:321-342: a linked worktree reads its commondir file; the primary uses
    # gitdir itself. builtin/rev-parse.c:1031-1078 exposes those paths and whether cwd is a worktree.
    lines = done.stdout.removesuffix("\n").split("\n")
    if (
        len(lines) == CHECKOUT_FIELDS
        and lines[0] == lines[1]
        and lines[2] == "true"
        and branch.stdout == "refs/heads/main\n"
    ):
        return None
    return refusal
