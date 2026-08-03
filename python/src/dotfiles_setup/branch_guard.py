"""Deny repo-file modifications made while sitting on the default branch.

``do-not.md`` #9 already says "do NOT commit onto the default branch — branch
FIRST", and it is enforced at *commit* time by hk's ``no_commit_to_branch``.
That layer is blind to the failure this module closes: **work accumulating on
``main`` before any commit is attempted**.

Session 2026-08-03-f produced it. ``mise run land`` leaves you on ``main``; two
sub-agents then wrote their reports straight into the working tree there, and
nothing said a word — the tree simply grew untracked files on the default
branch. It only becomes visible when something tries to commit, which is far too
late if the intervening work was expensive. Ray's instruction: *"all work should
be on a branch that can be on a pr"*, enforced *"whenever anything is modified on
the repo"*.

So this fires on ``Edit`` / ``Write`` / ``NotebookEdit`` — the moment a file is
about to change, not the moment it is about to be committed.

**What it deliberately ALLOWS**, because a guard that blocks these gets switched
off (``mise-tasks-only.md``: "a redirect that misfires on legitimate diagnostics
erodes trust in the guard"):

- anything **outside the repo** — the auto-memory dir, the session scratchpad;
- anything **git-ignored** — ``.agent/``, ``graphify-out/``, ``mise.local.toml``;
  these are machine-local by construction and can never go on a PR;
- everything, when **not on the default branch** (the normal case).

Like its siblings it fails **OPEN**: any error resolving git state allows the
call. A crashed guard must not brick every edit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Branches treated as protected when the remote's default cannot be resolved.
# `main` first: this repo's default (`AGENTS.md` — "Main branch (you will
# usually use this for PRs): main").
_FALLBACK_DEFAULTS = ("main", "master")

_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

_REASON = (
    "You are on the default branch ({branch}) and about to modify {path}.\n"
    "All work belongs on a branch that can become a PR — branch FIRST, then edit.\n"
    "\n"
    "    git checkout -b <type>/<slug>\n"
    "\n"
    "Then re-run this edit and ship with `mise run ship`.\n"
    "This is `.claude/rules/do-not.md` #9. `mise run land` leaves you on the "
    "default branch, which is how work ends up here unnoticed.\n"
    "Writes outside the repo and to git-ignored paths (.agent/, the scratchpad) "
    "are NOT affected by this guard."
)


def _git(args: list[str], cwd: Path) -> str | None:
    """Run a read-only git command, returning stripped stdout or None."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def repo_root(start: Path) -> Path | None:
    """Absolute root of the git worktree containing ``start``, or None.

    ``start`` routinely does NOT exist yet — a Write creating a new file, often
    inside a directory that does not exist either. So walk up to the first
    ancestor that IS a directory before asking git; running git with a
    nonexistent cwd just errors, and the guard would then fail open on exactly
    the case it was built for (caught by
    ``test_denies_a_new_untracked_file_on_default_branch``).
    """
    probe = start if start.is_dir() else start.parent
    while not probe.is_dir():
        parent = probe.parent
        if parent == probe:  # reached the filesystem root
            return None
        probe = parent
    out = _git(["rev-parse", "--show-toplevel"], probe)
    return Path(out).resolve() if out else None


def default_branch(root: Path) -> tuple[str, ...]:
    """Protected branch names for ``root``.

    Prefers the remote's advertised default; falls back to the conventional
    pair so the guard still works in a clone with no ``origin/HEAD`` ref.
    """
    out = _git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], root)
    if out and "/" in out:
        return (out.split("/", 1)[1],)
    return _FALLBACK_DEFAULTS


def is_ignored(path: Path, root: Path) -> bool:
    """True when git ignores ``path`` (so it can never reach a PR)."""
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", "--", str(path)],
            cwd=root,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return False
    return proc.returncode == 0


def _target(tool_input: dict[str, object]) -> Path | None:
    """The file a tool call is about to modify, absolute — or None."""
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError, RuntimeError:
        return None


def _protected(target: Path) -> tuple[Path, str] | None:
    """``(root, branch)`` when ``target`` sits in a repo on its default branch.

    None means "not our business": outside any repo (the scratchpad, the
    auto-memory dir), or on a feature branch, or on a detached HEAD — which is
    not a branch anyone ships from.
    """
    root = repo_root(target)
    if root is None or not target.is_relative_to(root):
        return None
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if branch is None or branch == "HEAD" or branch not in default_branch(root):
        return None
    return root, branch


def decide(tool_input: dict[str, object]) -> str | None:
    """Deny reason for an Edit/Write/NotebookEdit, or None to allow.

    Fails OPEN — every unresolvable step returns None.
    """
    target = _target(tool_input)
    if target is None:
        return None
    found = _protected(target)
    if found is None:
        return None
    root, branch = found
    if is_ignored(target, root):
        return None
    return _REASON.format(branch=branch, path=target.relative_to(root))


def handles(tool_name: str) -> bool:
    """True when ``tool_name`` is a file-modifying tool this guard covers."""
    return tool_name in _TOOLS
