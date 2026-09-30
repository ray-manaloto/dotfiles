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

The repo's open PRs and the PRs merged since the previous handoff are rendered
in the claim words ``handoff-check`` verifies ("#1449 OPEN, auto-merge armed,
RED"), so a State section pasted from this output checks itself.

Every render carries a ``generated`` stamp.  The next run starts its merged-since
window at the previous handoff's stamp, not at its mtime: a handoff edited after
its State was pasted would otherwise hide the merges in between from both.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

from dotfiles_setup import child_env, handoff_check, pr_facts

_GIT_TIMEOUT = 30
_SHA_ABBREV = 7
_STATUS_PREFIX_LENGTH = 3
_PR_LIST_LIMIT = "100"
_SINCE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_FALLBACK_WINDOW = timedelta(hours=24)
_GENERATED_STAMP = re.compile(r"^- \*\*generated\*\*: (\S+)\s*$", re.MULTILINE)

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
class PrSummary:
    """One repo PR, open or merged, in the facts handoff-check verifies."""

    number: int
    title: str
    author: str
    state: str
    auto_merge: bool
    checks: pr_facts.CheckCounts | None
    merged_at: str | None


@dataclass(frozen=True)
class Snapshot:
    """The repo state needed to reconcile a session handoff.

    ``open_prs``/``merged_prs`` are None when GitHub did not answer usably, or
    when PR lookups were not requested (``pr`` is then None too).  A list that
    filled ``--limit`` may be truncated, and says so.
    """

    branch: str | None
    clean: bool
    dirty_paths: tuple[str, ...]
    commits: tuple[Commit, ...]
    pr: PullRequest | None
    open_prs: tuple[PrSummary, ...] | None
    merged_prs: tuple[PrSummary, ...] | None
    since: str | None
    since_source: str | None
    generated_at: str
    open_truncated: bool = False
    merged_truncated: bool = False


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
            env=child_env.without_git_context(),
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


def _checks_summary(row: dict[str, object]) -> str | None:
    """Summarize a well-formed statusCheckRollup as ``N/M passing``."""
    counts = pr_facts.count_checks(row.get("statusCheckRollup"))
    if counts is None:
        return None
    return f"{counts.passed}/{counts.total} passing"


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
    rc, out = pr_facts.run_gh(
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


def _author(row: dict[str, object]) -> str:
    """Return the row's author login (a bot renders as ``app/<name>``)."""
    author = row.get("author")
    login = author.get("login") if isinstance(author, dict) else None
    return login if isinstance(login, str) else "unknown"


def _summaries(
    state: str, args: list[str], repo_root: Path
) -> tuple[tuple[PrSummary, ...], bool] | None:
    """Run one ``gh pr list --state <state>``; any malformed row fails the whole.

    The bool is True when the answer filled ``--limit``: the list may be
    truncated, and GitHub does not say whether it is.
    """
    rc, out = pr_facts.run_gh(
        ["pr", "list", "--limit", _PR_LIST_LIMIT, "--state", state, *args], repo_root
    )
    if rc != 0:
        return None
    rows = _pr_rows(out)
    if rows is None:
        return None
    summaries: list[PrSummary] = []
    for row in rows:
        number = row.get("number")
        title = row.get("title")
        merged_at = row.get("mergedAt")
        if not isinstance(number, int) or isinstance(number, bool):
            return None
        rollup = row.get("statusCheckRollup")
        summaries.append(
            PrSummary(
                number=number,
                title=title if isinstance(title, str) else "",
                author=_author(row),
                state=state.upper(),
                auto_merge=row.get("autoMergeRequest") is not None,
                checks=None if rollup is None else pr_facts.count_checks(rollup),
                merged_at=merged_at if isinstance(merged_at, str) else None,
            )
        )
    return tuple(summaries), len(rows) >= int(_PR_LIST_LIMIT)


def _open_prs(repo_root: Path) -> tuple[tuple[PrSummary, ...], bool] | None:
    """Every open PR in the repo, with auto-merge and check facts."""
    return _summaries(
        "open",
        [
            "--json",
            "number,title,author,autoMergeRequest,statusCheckRollup",
        ],
        repo_root,
    )


def _merged_prs(
    repo_root: Path, since: str
) -> tuple[tuple[PrSummary, ...], bool] | None:
    """PRs merged at or after ``since`` (an ISO-8601 UTC timestamp)."""
    return _summaries(
        "merged",
        [
            "--search",
            f"merged:>={since}",
            "--json",
            "number,title,author,mergedAt",
        ],
        repo_root,
    )


def _format_since(moment: datetime) -> str:
    """Render a moment as ``YYYY-MM-DDTHH:MM:SSZ`` in UTC."""
    return moment.astimezone(UTC).strftime(_SINCE_FORMAT)


def parse_since(value: str) -> str | None:
    """Normalize an ISO-8601 ``--since`` value to UTC; None when unparsable.

    A value without an offset is read as UTC.
    """
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return _format_since(moment)


def _display(path: Path, repo_root: Path) -> str:
    """A path relative to the repo when it is inside it."""
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _generated_stamp(handoff: Path) -> str | None:
    """The last parsable ``- **generated**:`` stamp in a handoff, else None.

    An unreadable file has no stamp: the caller falls back to its mtime.
    """
    try:
        text = handoff.read_text(errors="replace")
    except OSError:
        return None
    for match in reversed(list(_GENERATED_STAMP.finditer(text))):
        stamp = parse_since(match.group(1))
        if stamp is not None:
            return stamp
    return None


def default_since(
    repo_root: Path, now: datetime, *, exclude: Path | None = None
) -> tuple[str, str]:
    """The newest handoff's generated stamp (else its mtime), or ``now`` - 24 h.

    ``exclude`` is the handoff being written: once it exists it is the newest,
    and its own time would collapse the merged-since window to "now".
    """
    handoff = handoff_check.newest_handoff(repo_root, exclude=exclude)
    if handoff is None:
        return _format_since(now - _FALLBACK_WINDOW), "24h fallback"
    excluding = (
        "" if exclude is None else f" (excluding {_display(exclude, repo_root)})"
    )
    stamp = _generated_stamp(handoff)
    if stamp is not None:
        return stamp, f"{handoff.relative_to(repo_root)} generated stamp{excluding}"
    mtime = datetime.fromtimestamp(handoff.stat().st_mtime, tz=UTC)
    return _format_since(mtime), f"{handoff.relative_to(repo_root)} mtime{excluding}"


def utc_now() -> datetime:
    """The clock :func:`gather` reads once; tests pin it by patching this name."""
    return datetime.now(UTC)


def gather(
    repo_root: Path,
    *,
    limit: int = DEFAULT_COMMITS,
    with_pr: bool = True,
    since: str | None = None,
    for_handoff: Path | None = None,
) -> Snapshot:
    """Gather a read-only session snapshot from git and, optionally, GitHub.

    ``since`` wins over ``for_handoff``, which only excludes that handoff when
    the window defaults to the previous handoff's stamp or mtime.
    """
    now = utc_now()
    generated_at = _format_since(now)
    branch = _current_branch(repo_root)
    dirty_paths = _dirty_paths(repo_root)
    commits = _recent_commits(repo_root, limit)
    if not with_pr:
        return Snapshot(
            branch=branch,
            clean=not dirty_paths,
            dirty_paths=dirty_paths,
            commits=commits,
            pr=None,
            open_prs=None,
            merged_prs=None,
            since=None,
            since_source=None,
            generated_at=generated_at,
        )
    if since is None:
        since, since_source = default_since(repo_root, now, exclude=for_handoff)
    else:
        since_source = "--since"
    pr = _pull_request(repo_root, branch)
    open_prs = _open_prs(repo_root)
    merged_prs = _merged_prs(repo_root, since)
    return Snapshot(
        branch=branch,
        clean=not dirty_paths,
        dirty_paths=dirty_paths,
        commits=commits,
        pr=pr,
        open_prs=None if open_prs is None else open_prs[0],
        merged_prs=None if merged_prs is None else merged_prs[0],
        since=since,
        since_source=since_source,
        generated_at=generated_at,
        open_truncated=open_prs is not None and open_prs[1],
        merged_truncated=merged_prs is not None and merged_prs[1],
    )


def _check_word(checks: pr_facts.CheckCounts | None) -> str:
    """The check word handoff-check parses, with its counts."""
    if checks is None:
        return "checks unknown"
    if checks.failing >= 1:
        word = "RED"
    elif checks.total >= 1 and checks.pending == 0:
        word = "green"
    elif checks.total >= 1:
        word = "PENDING"
    else:
        word = "no checks"
    return (
        f"{word} (fail:{checks.failing} pending:{checks.pending} pass:{checks.passed})"
    )


def _code(text: str) -> str:
    """Free text inside one code span, so no word in it reads as a claim."""
    return "`" + text.replace("`", "'") + "`"


def _title(summary: PrSummary) -> str:
    """A PR title as a code span."""
    return _code(summary.title)


def _count(items: tuple[PrSummary, ...], *, truncated: bool) -> str:
    """The list size, flagged when it filled ``--limit``."""
    if truncated:
        return (
            f"{len(items)}, TRUNCATED at --limit {_PR_LIST_LIMIT} — "
            "list may be incomplete"
        )
    return str(len(items))


def _open_row(summary: PrSummary) -> str:
    """One open PR in the claim grammar handoff-check parses."""
    words = ["OPEN"]
    if summary.auto_merge:
        words.append("auto-merge armed")
    words.append(_check_word(summary.checks))
    return (
        f"  - #{summary.number} {', '.join(words)} — "
        f"{_title(summary)} (@{summary.author})"
    )


def _merged_row(summary: PrSummary) -> str:
    """One merged PR in the claim grammar handoff-check parses."""
    when = f" {summary.merged_at}" if summary.merged_at else ""
    return f"  - #{summary.number} MERGED{when} — {_title(summary)} (@{summary.author})"


def _render_repo_prs(snapshot: Snapshot) -> list[str]:
    """The repo-wide open and merged-since lists."""
    if snapshot.pr is None:
        return [
            "- **open PRs**: not requested (--no-pr)",
            "- **merged since**: not requested (--no-pr)",
        ]
    lines: list[str] = []
    if snapshot.open_prs is None:
        lines.append("- **open PRs**: UNVERIFIABLE — gh did not return a usable answer")
    elif not snapshot.open_prs:
        lines.append("- **open PRs**: none")
    else:
        count = _count(snapshot.open_prs, truncated=snapshot.open_truncated)
        lines.append(f"- **open PRs** ({count}):")
        lines.extend(_open_row(summary) for summary in snapshot.open_prs)

    heading = f"- **merged since** {snapshot.since} ({snapshot.since_source})"
    if snapshot.merged_prs is None:
        lines.append(f"{heading}: UNVERIFIABLE — gh did not return a usable answer")
    elif not snapshot.merged_prs:
        lines.append(f"{heading}: none")
    else:
        count = _count(snapshot.merged_prs, truncated=snapshot.merged_truncated)
        lines.append(f"{heading} ({count}):")
        lines.extend(_merged_row(summary) for summary in snapshot.merged_prs)
    return lines


def render(snapshot: Snapshot) -> str:
    """Render a snapshot as a compact, paste-ready Markdown block."""
    branch = (
        "- **branch**: HEAD (detached — not on a branch)"
        if snapshot.branch is None
        else f"- **branch**: `{snapshot.branch}`"
    )
    lines = [branch, f"- **generated**: {snapshot.generated_at}"]
    if snapshot.clean:
        lines.append("- **tree**: clean")
    else:
        lines.append(f"- **tree**: dirty ({len(snapshot.dirty_paths)} paths)")
        lines.extend(f"  - `{path}`" for path in snapshot.dirty_paths)

    if snapshot.commits:
        lines.append("- **recent commits**:")
        lines.extend(
            f"  - `{commit.sha[:_SHA_ABBREV]}` {_code(commit.subject)}"
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
        title = f" — {_code(snapshot.pr.title)}" if snapshot.pr.title else ""
        checks = (
            f" (checks: {snapshot.pr.checks_summary})"
            if snapshot.pr.checks_summary
            else ""
        )
        lines.append(f"- **open PR**: #{snapshot.pr.number}{title}{checks}")
    lines.extend(_render_repo_prs(snapshot))
    return "\n".join(lines)


def main(args: list[str], repo_root: Path) -> int:
    """Run ``session-state [--no-pr] [--since <ISO>] [--for <handoff>]``."""
    with_pr = True
    since: str | None = None
    for_handoff: Path | None = None
    unknown: list[str] = []
    remaining = iter(args)
    for arg in remaining:
        if arg == "--no-pr":
            with_pr = False
        elif arg == "--for":
            value = next(remaining, None)
            if value is None:
                sys.stderr.write("session-state: --for needs a handoff path\n")
                return 2
            requested = Path(value)
            if handoff_check.handoff_key(requested) is None:
                sys.stderr.write(
                    "session-state: --for must name a "
                    "session-YYYY-MM-DD[-x].md handoff\n"
                )
                return 2
            for_handoff = requested if requested.is_absolute() else repo_root / value
        elif arg == "--since":
            value = next(remaining, None)
            since = None if value is None else parse_since(value)
            if since is None:
                sys.stderr.write(
                    "session-state: --since needs an ISO-8601 timestamp, "
                    f"got {value!r}\n"
                )
                return 2
        else:
            unknown.append(arg)
    if unknown:
        sys.stderr.write(f"session-state: unknown argument(s): {', '.join(unknown)}\n")
        return 2
    try:
        snapshot = gather(
            repo_root, with_pr=with_pr, since=since, for_handoff=for_handoff
        )
        sys.stdout.write(render(snapshot) + "\n")
    except RuntimeError as exc:
        sys.stderr.write(f"session-state: {exc}\n")
        return 1
    return 0
