# Copyright (c) 2026 Raymond Manaloto
"""Live GitHub facts for a PR or issue number, shared by the handoff tools.

``handoff_check`` compares prose claims ("#1449 auto-merge armed") against
these facts, and ``session_state`` renders the same facts in the same claim
words.  Both call :func:`run_gh` through this module's attribute at call time,
so one ``monkeypatch.setattr(pr_facts, "run_gh", fake)`` reaches every GitHub
read in unit tests.

A failed or malformed lookup is returned as a ``str`` detail, never as a
default :class:`PrFacts`: a lookup that did not answer is not a pass.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from typing import TYPE_CHECKING

from dotfiles_setup import child_env

if TYPE_CHECKING:
    from pathlib import Path

GH_TIMEOUT = 120

_PASS_VALUES = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED", "PASS"})
_FAIL_VALUES = frozenset(
    {
        "FAILURE",
        "ERROR",
        "CANCELLED",
        "TIMED_OUT",
        "ACTION_REQUIRED",
        "STARTUP_FAILURE",
    }
)


def run_gh(args: list[str], repo_root: Path) -> tuple[int, str]:
    """Run one bounded GitHub read; failures become an unverifiable state."""
    try:
        proc = subprocess.run(
            ["gh", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=GH_TIMEOUT,
            env=child_env.without_git_context(),
        )
    except subprocess.TimeoutExpired:
        return 124, "gh lookup timed out"
    except OSError as exc:
        return 127, str(exc)
    if proc.returncode == 0:
        return 0, proc.stdout or ""
    return proc.returncode, proc.stderr or proc.stdout or "no diagnostic"


class CheckBucket(StrEnum):
    """Where one statusCheckRollup entry lands (values: pass, fail, pending)."""

    PASS = auto()
    FAIL = auto()
    PENDING = auto()


def classify_check(check: dict[str, object]) -> CheckBucket:
    """Bucket one rollup entry by its conclusion, state, or status.

    Why not gh's own ``bucket``: ``gh pr view/list --json`` expose only
    ``statusCheckRollup``, never ``bucket`` (that is ``gh pr checks``).  The
    mapping also deliberately differs from gh's: CANCELLED and STARTUP_FAILURE
    count as failing here (gh buckets them ``cancel``/``pending``), because a
    handoff's RED means "will not merge as-is".
    """
    value = check.get("conclusion") or check.get("state") or check.get("status")
    if not isinstance(value, str):
        return CheckBucket.PENDING
    upper = value.upper()
    if upper in _PASS_VALUES:
        return CheckBucket.PASS
    if upper in _FAIL_VALUES:
        return CheckBucket.FAIL
    return CheckBucket.PENDING


@dataclass(frozen=True)
class CheckCounts:
    """Per-bucket counts of a PR's checks."""

    passed: int
    failing: int
    pending: int

    @property
    def total(self) -> int:
        """Every counted check."""
        return self.passed + self.failing + self.pending


def _started_at(check: dict[str, object]) -> str:
    """ISO-8601 start time; a missing or non-string one sorts OLDEST."""
    value = check.get("startedAt")
    return value if isinstance(value, str) else ""


def _dedupe_key(check: dict[str, object]) -> tuple[str | None, ...]:
    """``context`` for a status, else ``(name, workflowName)`` for a check run."""
    context = check.get("context")
    if isinstance(context, str) and context:
        return ("context", context)
    name = check.get("name")
    workflow = check.get("workflowName")
    return (
        "run",
        name if isinstance(name, str) else None,
        workflow if isinstance(workflow, str) else None,
    )


def _latest_checks(rollup: list[dict[str, object]]) -> list[dict[str, object]]:
    """Drop re-run duplicates the way gh does, keeping the newest per key.

    Mirrors ``eliminateDuplicates`` in cli/cli ``pkg/cmd/pr/checks/aggregate.go``
    (lines 96-120 at ``e9542451``): newest ``startedAt`` first, then the first
    entry per key.  gh also keys a check run on its workflow run's EVENT, which
    ``gh pr view/list --json statusCheckRollup`` does not expose, so two runs of
    one workflow job from different events collapse to one here.
    """
    seen: set[tuple[str | None, ...]] = set()
    latest: list[dict[str, object]] = []
    for check in sorted(rollup, key=_started_at, reverse=True):
        key = _dedupe_key(check)
        if key in seen:
            continue
        seen.add(key)
        latest.append(check)
    return latest


def count_checks(rollup: object) -> CheckCounts | None:
    """Count a statusCheckRollup's latest checks; None unless a list of dicts."""
    if not isinstance(rollup, list):
        return None
    if not all(isinstance(check, dict) for check in rollup):
        return None
    buckets = [classify_check(check) for check in _latest_checks(rollup)]
    return CheckCounts(
        passed=buckets.count(CheckBucket.PASS),
        failing=buckets.count(CheckBucket.FAIL),
        pending=buckets.count(CheckBucket.PENDING),
    )


class ItemKind(Enum):
    """GitHub numbers PRs and issues from one sequence."""

    PR = "pr"
    ISSUE = "issue"


@dataclass(frozen=True)
class PrFacts:
    """What GitHub says about one number right now."""

    number: int
    kind: ItemKind
    state: str
    auto_merge: bool
    checks: CheckCounts


def _first_line(text: str) -> str:
    """Keep a diagnostic to its first non-blank line."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return "no diagnostic"


def _json_object(out: str) -> dict[str, object] | None:
    """Decode a JSON object, failing closed on anything else."""
    try:
        value = json.loads(out)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def fetch_facts(repo_root: Path, number: int) -> PrFacts | str:
    """Return the live facts for ``number``, or a str saying why it is unverifiable.

    The issues endpoint answers for both kinds; a ``pull_request`` key marks a
    PR, whose state, auto-merge and checks then come from ``gh pr view``.
    """
    rc, out = run_gh(["api", f"repos/{{owner}}/{{repo}}/issues/{number}"], repo_root)
    if rc != 0:
        return f"gh api exited {rc}: {_first_line(out)}"
    item = _json_object(out)
    if item is None:
        return f"malformed gh api answer for #{number}"
    if "pull_request" in item:
        return _fetch_pr(repo_root, number)
    state = item.get("state")
    if not isinstance(state, str):
        return f"malformed gh api answer for #{number}: no state"
    return PrFacts(
        number,
        ItemKind.ISSUE,
        state.upper(),
        auto_merge=False,
        checks=CheckCounts(0, 0, 0),
    )


def _fetch_pr(repo_root: Path, number: int) -> PrFacts | str:
    """Read a PR's state, auto-merge request and check rollup."""
    rc, out = run_gh(
        [
            "pr",
            "view",
            str(number),
            "--json",
            "state,autoMergeRequest,statusCheckRollup",
        ],
        repo_root,
    )
    if rc != 0:
        return f"gh pr view exited {rc}: {_first_line(out)}"
    pr = _json_object(out)
    if pr is None:
        return f"malformed gh pr view answer for #{number}"
    state = pr.get("state")
    checks = count_checks(pr.get("statusCheckRollup"))
    if not isinstance(state, str) or checks is None:
        return f"malformed gh pr view answer for #{number}: state or checks"
    return PrFacts(
        number,
        ItemKind.PR,
        state.upper(),
        pr.get("autoMergeRequest") is not None,
        checks,
    )
