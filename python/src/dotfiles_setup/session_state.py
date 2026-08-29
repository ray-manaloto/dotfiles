# Copyright (c) 2026 Raymond Manaloto
"""Paste-ready branch/tree/commit/PR state for post-clear reconciliation.

``mise run session-state`` replaces the hand-formatted state block in a
session handoff with one read-only snapshot.  The data and rendering layers
stay separate so callers can compare state without parsing prose back into
facts.

A failed ``gh`` lookup is deliberately not rendered as "no open PR".  Only a
successful query returning an empty list earns :attr:`PrState.NONE`; command
failure, timeout, malformed JSON, and detached HEAD are all
:attr:`PrState.UNVERIFIABLE`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_GIT_TIMEOUT = 30
_GH_TIMEOUT = 120
_SHA_ABBREV = 7
_STATUS_PREFIX_LENGTH = 3

DEFAULT_COMMITS = 8


class PrState(Enum):
    """The three distinct outcomes of asking GitHub for a branch PR."""

    NONE = "none"
    OPEN = "open"
    UNVERIFIABLE = "unverifiable"


@dataclass(frozen=True)
class PullRequest:
    """The open pull request for the branch, when GitHub answered."""

    state: PrState
    number: int | None = None
    title: str | None = None
    checks_summary: str | None = None


@dataclass(frozen=True)
class Commit:
    """One recent commit, newest first in a :class:`Snapshot`."""

    sha: str
    subject: str


@dataclass(frozen=True)
class Snapshot:
    """The repo state needed to reconcile a session handoff."""

    branch: str | None
    clean: bool
    dirty_paths: tuple[str, ...]
    commits: tuple[Commit, ...]
    pr: PullRequest | None


def _git(args: list[str], repo_root: Path) -> tuple[int, str, str]:
    """Run one bounded git metadata read in ``repo_root``."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=_GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        message = f"git {' '.join(args)} failed: {exc}"
        raise RuntimeError(message) from exc
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _git_output(args: list[str], repo_root: Path) -> str:
    """Return stdout for a successful git read, otherwise fail with context."""
    rc, out, err = _git(args, repo_root)
    if rc != 0:
        detail = err.strip() or out.strip() or "no diagnostic"
        message = f"git {' '.join(args)} exited {rc}: {detail}"
        raise RuntimeError(message)
    return out


def _current_branch(repo_root: Path) -> str | None:
    """Return the branch name, or None only when HEAD is detached."""
    rc, out, _err = _git(["symbolic-ref", "--quiet", "--short", "HEAD"], repo_root)
    branch = out.strip()
    if rc == 0 and branch:
        return branch

    verify_rc, _verify_out, verify_err = _git(
        ["rev-parse", "--verify", "HEAD"], repo_root
    )
    if verify_rc == 0:
        return None
    detail = verify_err.strip() or "HEAD is unreadable"
    message = f"could not resolve the current branch: {detail}"
    raise RuntimeError(message)


def _dirty_paths(repo_root: Path) -> tuple[str, ...]:
    """Return the path field from each ``git status --porcelain`` record."""
    # Quoted filenames with special characters remain a documented v1 limitation.
    out = _git_output(["status", "--porcelain", "--no-renames"], repo_root)
    return tuple(
        line[_STATUS_PREFIX_LENGTH:]
        for line in out.splitlines()
        if len(line) > _STATUS_PREFIX_LENGTH
    )


def _recent_commits(repo_root: Path, limit: int) -> tuple[Commit, ...]:
    """Return up to ``limit`` commits, with an unambiguous NUL field split."""
    if limit < 1:
        return ()
    out = _git_output(["log", "-n", str(limit), "--format=%H%x00%s"], repo_root)
    commits: list[Commit] = []
    for line in out.splitlines():
        sha, separator, subject = line.partition("\0")
        if sha and separator:
            commits.append(Commit(sha=sha, subject=subject))
    return tuple(commits)


def _gh(args: list[str], repo_root: Path) -> tuple[int, str]:
    """Run one bounded GitHub read; failures become an unverifiable state."""
    try:
        proc = subprocess.run(
            ["gh", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=_GH_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 124, "gh lookup timed out"
    except OSError as exc:
        return 127, str(exc)
    if proc.returncode == 0:
        return 0, proc.stdout or ""
    return proc.returncode, proc.stderr or proc.stdout or "no diagnostic"


def _checks_summary(row: dict[str, object]) -> str | None:
    """Summarize a well-formed statusCheckRollup as ``N/M passing``."""
    rollup = row.get("statusCheckRollup")
    if not isinstance(rollup, list):
        return None
    if not all(isinstance(check, dict) for check in rollup):
        return None

    passing_values = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED", "PASS"})
    passing = 0
    for check in rollup:
        value = check.get("conclusion") or check.get("state") or check.get("status")
        if isinstance(value, str) and value.upper() in passing_values:
            passing += 1
    return f"{passing}/{len(rollup)} passing"


def _pr_rows(out: str) -> list[dict[str, object]] | None:
    """Decode a strict list of GitHub PR rows, failing closed on other JSON."""
    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return None
    return rows


def _pull_request(repo_root: Path, branch: str | None) -> PullRequest:
    """Return the branch's open PR, preserving every unanswered outcome."""
    if branch is None:
        return PullRequest(PrState.UNVERIFIABLE)
    rc, out = _gh(
        [
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number,title,statusCheckRollup",
        ],
        repo_root,
    )
    if rc != 0:
        return PullRequest(PrState.UNVERIFIABLE)
    rows = _pr_rows(out)
    if rows is None:
        return PullRequest(PrState.UNVERIFIABLE)
    if not rows:
        return PullRequest(PrState.NONE)

    row = rows[0]
    number = row.get("number")
    title = row.get("title")
    if not isinstance(number, int) or isinstance(number, bool):
        return PullRequest(PrState.UNVERIFIABLE)
    return PullRequest(
        PrState.OPEN,
        number=number,
        title=title if isinstance(title, str) else None,
        checks_summary=_checks_summary(row),
    )


def gather(
    repo_root: Path,
    *,
    limit: int = DEFAULT_COMMITS,
    with_pr: bool = True,
) -> Snapshot:
    """Gather a read-only session snapshot from git and, optionally, GitHub."""
    branch = _current_branch(repo_root)
    dirty_paths = _dirty_paths(repo_root)
    return Snapshot(
        branch=branch,
        clean=not dirty_paths,
        dirty_paths=dirty_paths,
        commits=_recent_commits(repo_root, limit),
        pr=_pull_request(repo_root, branch) if with_pr else None,
    )


def render(snapshot: Snapshot) -> str:
    """Render a snapshot as a compact, paste-ready Markdown block."""
    branch = (
        "- **branch**: HEAD (detached — not on a branch)"
        if snapshot.branch is None
        else f"- **branch**: `{snapshot.branch}`"
    )
    lines = [branch]
    if snapshot.clean:
        lines.append("- **tree**: clean")
    else:
        lines.append(f"- **tree**: dirty ({len(snapshot.dirty_paths)} paths)")
        lines.extend(f"  - `{path}`" for path in snapshot.dirty_paths)

    if snapshot.commits:
        lines.append("- **recent commits**:")
        lines.extend(
            f"  - `{commit.sha[:_SHA_ABBREV]}` {commit.subject}"
            for commit in snapshot.commits
        )
    else:
        lines.append("- **recent commits**: none")

    if snapshot.pr is None:
        lines.append("- **open PR**: not requested (--no-pr)")
    elif snapshot.pr.state is PrState.NONE:
        lines.append("- **open PR**: none")
    elif snapshot.pr.state is PrState.UNVERIFIABLE:
        lines.append("- **open PR**: UNVERIFIABLE — gh did not return a usable answer")
    else:
        title = f" — {snapshot.pr.title}" if snapshot.pr.title else ""
        checks = (
            f" (checks: {snapshot.pr.checks_summary})"
            if snapshot.pr.checks_summary
            else ""
        )
        lines.append(f"- **open PR**: #{snapshot.pr.number}{title}{checks}")
    return "\n".join(lines)


def main(args: list[str], repo_root: Path) -> int:
    """Run ``session-state [--no-pr]`` and print the snapshot."""
    unknown = [arg for arg in args if arg != "--no-pr"]
    if unknown:
        sys.stderr.write(f"session-state: unknown argument(s): {', '.join(unknown)}\n")
        return 2
    try:
        sys.stdout.write(
            render(gather(repo_root, with_pr="--no-pr" not in args)) + "\n"
        )
    except RuntimeError as exc:
        sys.stderr.write(f"session-state: {exc}\n")
        return 1
    return 0
