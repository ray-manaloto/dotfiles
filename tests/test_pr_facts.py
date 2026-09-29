# Copyright (c) 2026 Raymond Manaloto
"""Tests for the shared GitHub PR/issue facts layer (no network)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import pr_facts

_ROOT = Path("/nonexistent-repo-root")


# Truth table for `pr_facts.classify_check`, bound by the classifier_axes
# REGISTRY entry: its one axis, `check`, is crossed as the partition the code
# reads — which key supplies the value (conclusion > state > status), its
# type, and which value set it falls in. Every CheckBucket is reached.
_CLASSIFY_CHECK_TABLE: list[tuple[dict[str, object], pr_facts.CheckBucket]] = [
    ({"conclusion": "SUCCESS"}, pr_facts.CheckBucket.PASS),
    ({"conclusion": "neutral"}, pr_facts.CheckBucket.PASS),
    ({"conclusion": "SKIPPED"}, pr_facts.CheckBucket.PASS),
    ({"state": "PASS"}, pr_facts.CheckBucket.PASS),
    ({"conclusion": "FAILURE"}, pr_facts.CheckBucket.FAIL),
    ({"state": "ERROR"}, pr_facts.CheckBucket.FAIL),
    ({"conclusion": "CANCELLED"}, pr_facts.CheckBucket.FAIL),
    ({"conclusion": "TIMED_OUT"}, pr_facts.CheckBucket.FAIL),
    ({"conclusion": "ACTION_REQUIRED"}, pr_facts.CheckBucket.FAIL),
    ({"conclusion": "STARTUP_FAILURE"}, pr_facts.CheckBucket.FAIL),
    ({"status": "IN_PROGRESS"}, pr_facts.CheckBucket.PENDING),
    ({"conclusion": "", "status": "QUEUED"}, pr_facts.CheckBucket.PENDING),
    ({"conclusion": 7}, pr_facts.CheckBucket.PENDING),
    ({}, pr_facts.CheckBucket.PENDING),
    ({"conclusion": "SUCCESS", "state": "FAILURE"}, pr_facts.CheckBucket.PASS),
]


@pytest.mark.parametrize(("check", "bucket"), _CLASSIFY_CHECK_TABLE)
def test_classify_check_buckets(
    check: dict[str, object], bucket: pr_facts.CheckBucket
) -> None:
    assert pr_facts.classify_check(check) is bucket


def test_classify_check_table_reaches_every_bucket() -> None:
    assert {bucket for _check, bucket in _CLASSIFY_CHECK_TABLE} == set(
        pr_facts.CheckBucket
    )


def test_check_bucket_values() -> None:
    assert [bucket.value for bucket in pr_facts.CheckBucket] == [
        "pass",
        "fail",
        "pending",
    ]


def test_count_checks_counts_each_bucket() -> None:
    counts = pr_facts.count_checks(
        [
            {"conclusion": "SUCCESS"},
            {"conclusion": "FAILURE"},
            {"conclusion": "FAILURE"},
            {"status": "IN_PROGRESS"},
        ]
    )
    assert counts == pr_facts.CheckCounts(passed=1, failing=2, pending=1)
    assert counts is not None
    assert counts.total == 4


@pytest.mark.parametrize("rollup", [None, "x", {"conclusion": "SUCCESS"}, ["bad"]])
def test_count_checks_fails_closed_on_malformed_rollups(rollup: object) -> None:
    assert pr_facts.count_checks(rollup) is None


def test_count_checks_empty_is_known_zero() -> None:
    assert pr_facts.count_checks([]) == pr_facts.CheckCounts(0, 0, 0)


def _completed(
    rc: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["gh"], rc, stdout, stderr)


def test_run_gh_is_bounded_and_scrubs_git_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "/decoy")
    seen: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["cmd"] = cmd
        seen.update(kwargs)
        return _completed(0, "out", "warning")

    monkeypatch.setattr(pr_facts.subprocess, "run", fake_run)

    assert pr_facts.run_gh(["pr", "list"], _ROOT) == (0, "out")
    assert seen["cmd"] == ["gh", "pr", "list"]
    assert seen["timeout"] == 120
    assert seen["cwd"] == _ROOT
    env = seen["env"]
    assert isinstance(env, dict)
    assert "GIT_DIR" not in env


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (_completed(1, "", "HTTP 404"), (1, "HTTP 404")),
        (_completed(2, "only stdout", ""), (2, "only stdout")),
        (_completed(3), (3, "no diagnostic")),
    ],
)
def test_run_gh_failure_keeps_the_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    result: subprocess.CompletedProcess[str],
    expected: tuple[int, str],
) -> None:
    monkeypatch.setattr(pr_facts.subprocess, "run", lambda *_a, **_k: result)
    assert pr_facts.run_gh(["api", "x"], _ROOT) == expected


def test_run_gh_timeout_and_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, 120)

    monkeypatch.setattr(pr_facts.subprocess, "run", timeout)
    assert pr_facts.run_gh(["api", "x"], _ROOT) == (124, "gh lookup timed out")

    def missing(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        message = "gh: not found"
        raise FileNotFoundError(message)

    monkeypatch.setattr(pr_facts.subprocess, "run", missing)
    assert pr_facts.run_gh(["api", "x"], _ROOT) == (127, "gh: not found")


def _fake_gh(
    monkeypatch: pytest.MonkeyPatch, answers: dict[str, tuple[int, str]]
) -> list[list[str]]:
    """Answer ``gh api`` and ``gh pr view`` by their first argument."""
    calls: list[list[str]] = []

    def fake(args: list[str], _root: Path) -> tuple[int, str]:
        calls.append(args)
        return answers[args[0]]

    monkeypatch.setattr(pr_facts, "run_gh", fake)
    return calls


def test_fetch_facts_reads_an_issue_from_the_issues_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_gh(monkeypatch, {"api": (0, json.dumps({"state": "open"}))})

    assert pr_facts.fetch_facts(_ROOT, 963) == pr_facts.PrFacts(
        963,
        pr_facts.ItemKind.ISSUE,
        "OPEN",
        auto_merge=False,
        checks=pr_facts.CheckCounts(0, 0, 0),
    )
    assert calls == [["api", "repos/{owner}/{repo}/issues/963"]]


def test_fetch_facts_reads_a_pr_through_pr_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = {
        "state": "OPEN",
        "autoMergeRequest": {"mergeMethod": "SQUASH"},
        "statusCheckRollup": [{"conclusion": "FAILURE"}, {"conclusion": "SUCCESS"}],
    }
    calls = _fake_gh(
        monkeypatch,
        {
            "api": (0, json.dumps({"state": "open", "pull_request": {}})),
            "pr": (0, json.dumps(view)),
        },
    )

    assert pr_facts.fetch_facts(_ROOT, 1449) == pr_facts.PrFacts(
        1449,
        pr_facts.ItemKind.PR,
        "OPEN",
        auto_merge=True,
        checks=pr_facts.CheckCounts(passed=1, failing=1, pending=0),
    )
    assert calls[1] == [
        "pr",
        "view",
        "1449",
        "--json",
        "state,autoMergeRequest,statusCheckRollup",
    ]


def test_fetch_facts_null_auto_merge_request_is_not_armed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = {"state": "MERGED", "autoMergeRequest": None, "statusCheckRollup": []}
    _fake_gh(
        monkeypatch,
        {
            "api": (0, json.dumps({"state": "closed", "pull_request": {}})),
            "pr": (0, json.dumps(view)),
        },
    )

    facts = pr_facts.fetch_facts(_ROOT, 1)
    assert isinstance(facts, pr_facts.PrFacts)
    assert facts.state == "MERGED"
    assert facts.auto_merge is False


@pytest.mark.parametrize(
    ("answers", "detail"),
    [
        (
            {"api": (1, "HTTP 404: Not Found\nmore")},
            "gh api exited 1: HTTP 404: Not Found",
        ),
        ({"api": (0, "not json")}, "malformed gh api answer for #5"),
        ({"api": (0, "[]")}, "malformed gh api answer for #5"),
        ({"api": (0, "{}")}, "malformed gh api answer for #5: no state"),
        (
            {"api": (0, '{"pull_request": {}}'), "pr": (124, "gh lookup timed out")},
            "gh pr view exited 124: gh lookup timed out",
        ),
        (
            {"api": (0, '{"pull_request": {}}'), "pr": (0, "nope")},
            "malformed gh pr view answer for #5",
        ),
        (
            {
                "api": (0, '{"pull_request": {}}'),
                "pr": (0, '{"state": "OPEN", "statusCheckRollup": ["bad"]}'),
            },
            "malformed gh pr view answer for #5: state or checks",
        ),
    ],
)
def test_fetch_facts_failures_are_unverifiable_strings(
    monkeypatch: pytest.MonkeyPatch,
    answers: dict[str, tuple[int, str]],
    detail: str,
) -> None:
    _fake_gh(monkeypatch, answers)
    assert pr_facts.fetch_facts(_ROOT, 5) == detail
