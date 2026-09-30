# Copyright (c) 2026 Raymond Manaloto
"""Tests for the read-only session-state snapshot."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import handoff_check, pr_facts, session_state
from dotfiles_setup import main as cli_main

if TYPE_CHECKING:
    from typing import Literal, TypedDict, Unpack

    class _RunKwargs(TypedDict):
        cwd: Path
        capture_output: bool
        text: Literal[True]
        errors: str
        check: bool
        timeout: int
        env: dict[str, str]


_GIT_TIMEOUT = 30
_GIT_REPOSITORY_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        timeout=_GIT_TIMEOUT,
    )


def _fake_gh(
    monkeypatch: pytest.MonkeyPatch,
    *,
    branch: str = "[]",
    open_prs: str = "[]",
    merged_prs: str = "[]",
) -> list[list[str]]:
    """Answer each ``gh pr list`` query with its own payload; record every call."""
    calls: list[list[str]] = []

    def fake(args: list[str], _root: Path) -> tuple[int, str]:
        calls.append(args)
        if "--head" in args:
            return 0, branch
        if "open" in args:
            return 0, open_prs
        if "merged" in args:
            return 0, merged_prs
        message = f"unexpected gh call: {args}"
        raise AssertionError(message)

    monkeypatch.setattr(pr_facts, "run_gh", fake)
    return calls


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "work/123")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    (tmp_path / "tracked.txt").write_text("one\n")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-q", "-m", "initial subject")
    return tmp_path


def test_gather_reads_real_git_state_without_pr(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot = session_state.gather(repo, with_pr=False)

    assert snapshot.branch == "work/123"
    assert snapshot.clean
    assert snapshot.dirty_paths == ()
    assert [commit.subject for commit in snapshot.commits] == ["initial subject"]
    assert len(snapshot.commits[0].sha) == 40
    assert snapshot.pr is None


def test_gather_ignores_inherited_git_repository_redirects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_path = tmp_path / "target"
    target_path.mkdir()
    target = _repo(target_path)

    decoy_path = tmp_path / "decoy"
    decoy_path.mkdir()
    decoy = _repo(decoy_path)
    _git(decoy, "branch", "-m", "decoy/456")
    (decoy / "tracked.txt").write_text("decoy\n")
    _git(decoy, "add", "tracked.txt")
    _git(decoy, "commit", "-q", "-m", "decoy subject")

    decoy_git_dir = decoy / ".git"
    redirects = {
        "GIT_DIR": decoy_git_dir,
        "GIT_WORK_TREE": decoy,
        "GIT_INDEX_FILE": decoy_git_dir / "index",
        "GIT_OBJECT_DIRECTORY": decoy_git_dir / "objects",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": decoy_git_dir / "objects",
        "GIT_COMMON_DIR": decoy_git_dir,
    }
    for name, value in redirects.items():
        monkeypatch.setenv(name, str(value))

    snapshot = session_state.gather(target, with_pr=False)

    assert snapshot.branch == "work/123"
    assert [commit.subject for commit in snapshot.commits] == ["initial subject"]


def test_gh_scrubs_only_git_repository_redirects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)

    for name in _GIT_REPOSITORY_ENV_VARS:
        monkeypatch.setenv(name, f"decoy-{name}")
    monkeypatch.setenv("SESSION_STATE_PRESERVED", "present")
    expected_env = os.environ.copy()
    for name in (*_GIT_REPOSITORY_ENV_VARS, "__MISE_DIFF"):
        expected_env.pop(name, None)

    real_run = subprocess.run

    def capture_run(
        cmd: list[str], **kwargs: Unpack[_RunKwargs]
    ) -> subprocess.CompletedProcess[str]:
        if cmd[0] == "gh":
            assert kwargs["env"] == expected_env
            return subprocess.CompletedProcess(cmd, 0, "[]", "")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(session_state.subprocess, "run", capture_run)

    snapshot = session_state.gather(repo, with_pr=True)

    assert snapshot.pr is not None
    assert snapshot.pr.state is session_state.PrState.NONE


def test_gather_reports_dirty_paths_and_honors_limit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _git(repo, "mv", "tracked.txt", "renamed.txt")
    (repo / "new.txt").write_text("new\n")

    snapshot = session_state.gather(repo, limit=1, with_pr=False)

    assert not snapshot.clean
    assert set(snapshot.dirty_paths) == {"tracked.txt", "renamed.txt", "new.txt"}
    assert len(snapshot.commits) == 1


def test_gather_uses_none_only_for_detached_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _git(repo, "checkout", "--detach", "-q")

    snapshot = session_state.gather(repo, with_pr=False)

    assert snapshot.branch is None
    assert "detached" in session_state.render(snapshot)


def test_open_pr_and_check_summary_are_structured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    rows = [
        {
            "number": 42,
            "title": "Resume safely",
            "statusCheckRollup": [
                {"name": "lint", "conclusion": "SUCCESS"},
                {"context": "ci/legacy", "state": "SUCCESS"},
                {"name": "build", "status": "IN_PROGRESS"},
            ],
        }
    ]
    _fake_gh(monkeypatch, branch=json.dumps(rows))

    snapshot = session_state.gather(repo)

    assert snapshot.pr == session_state.PullRequest(
        session_state.PrState.OPEN,
        number=42,
        title="Resume safely",
        checks_summary="2/3 passing",
    )
    rendered = session_state.render(snapshot)
    assert "#42" in rendered
    assert "2/3 passing" in rendered


def test_successful_gh_warning_does_not_corrupt_pr_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    rows = [{"number": 42, "title": "Valid stdout", "statusCheckRollup": []}]
    real_run = subprocess.run

    def gh_with_stderr(
        cmd: list[str], **kwargs: Unpack[_RunKwargs]
    ) -> subprocess.CompletedProcess[str]:
        if cmd[0] == "gh":
            return subprocess.CompletedProcess(
                cmd,
                0,
                json.dumps(rows),
                "upgrade notice on stderr\n",
            )
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(session_state.subprocess, "run", gh_with_stderr)

    assert session_state.gather(repo).pr == session_state.PullRequest(
        session_state.PrState.OPEN,
        number=42,
        title="Valid stdout",
        checks_summary="0/0 passing",
    )


def test_empty_check_rollup_is_known_zero_not_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    rows = [{"number": 42, "title": "No checks yet", "statusCheckRollup": []}]
    _fake_gh(monkeypatch, branch=json.dumps(rows))

    snapshot = session_state.gather(repo)

    assert snapshot.pr is not None
    assert snapshot.pr.checks_summary == "0/0 passing"


def test_malformed_pr_rows_are_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _fake_gh(monkeypatch, branch='"not a list"')

    assert session_state.gather(repo).pr == session_state.PullRequest(
        session_state.PrState.UNVERIFIABLE
    )


def test_non_dict_check_rollup_is_unknown_instead_of_crashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    rows = [{"number": 42, "title": "Bad rollup", "statusCheckRollup": ["bad"]}]
    _fake_gh(monkeypatch, branch=json.dumps(rows))

    assert session_state.gather(repo).pr == session_state.PullRequest(
        session_state.PrState.OPEN,
        number=42,
        title="Bad rollup",
        checks_summary=None,
    )


def test_boolean_pr_number_is_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    rows = [{"number": True, "title": "Boolean number", "statusCheckRollup": []}]
    _fake_gh(monkeypatch, branch=json.dumps(rows))

    assert session_state.gather(repo).pr == session_state.PullRequest(
        session_state.PrState.UNVERIFIABLE
    )


def test_empty_pr_result_is_none_but_gh_timeout_is_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _fake_gh(monkeypatch)
    assert session_state.gather(repo).pr == session_state.PullRequest(
        session_state.PrState.NONE
    )

    real_run = subprocess.run

    def timeout_gh(
        cmd: list[str], **kwargs: Unpack[_RunKwargs]
    ) -> subprocess.CompletedProcess[str]:
        if cmd[0] == "gh":
            assert kwargs["timeout"] == 120
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])
        return real_run(
            cmd,
            cwd=kwargs["cwd"],
            capture_output=kwargs["capture_output"],
            text=kwargs["text"],
            errors=kwargs["errors"],
            check=kwargs["check"],
            timeout=kwargs["timeout"],
            env=kwargs["env"],
        )

    monkeypatch.undo()
    monkeypatch.setattr(session_state.subprocess, "run", timeout_gh)
    assert session_state.gather(repo).pr == session_state.PullRequest(
        session_state.PrState.UNVERIFIABLE
    )


def test_session_state_main_and_top_level_parser(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    args = cli_main.setup_parser().parse_args(["session-state", "--no-pr"])
    assert args.command == "session-state"
    assert args.no_pr is True

    assert session_state.main(["--no-pr"], repo) == 0
    output = capsys.readouterr().out
    assert "`work/123`" in output
    assert "not requested (--no-pr)" in output


def test_session_state_main_reports_git_log_failure_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _git(tmp_path, "init", "-q", "-b", "work")

    assert session_state.main(["--no-pr"], tmp_path) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("session-state: git log -n 8")


def test_pr_state_values_preserve_the_three_way_contract() -> None:
    assert {state.value for state in session_state.PrState} == {
        "none",
        "open",
        "unverifiable",
    }


_OPEN_ROWS = [
    {
        "number": 1449,
        "title": "Update `image` inputs",
        "author": {"login": "app/renovate"},
        "autoMergeRequest": {"mergeMethod": "SQUASH"},
        "statusCheckRollup": [
            {"name": "build", "conclusion": "FAILURE"},
            {"name": "lint", "conclusion": "SUCCESS"},
            {"name": "smoke", "conclusion": "SKIPPED"},
        ],
    },
    {
        "number": 1141,
        "title": "Add service",
        "author": {"login": "sortakool"},
        "autoMergeRequest": None,
        "statusCheckRollup": [
            {"name": "lint", "conclusion": "SUCCESS"},
            {"context": "coderabbit", "state": "NEUTRAL"},
        ],
    },
    {
        "number": 1200,
        "title": "Still running",
        "author": {"login": "sortakool"},
        "autoMergeRequest": None,
        "statusCheckRollup": [
            {"name": "lint", "conclusion": "SUCCESS"},
            {"name": "build", "status": "IN_PROGRESS"},
        ],
    },
    {
        "number": 1201,
        "title": "Nothing ran",
        "author": {"login": "sortakool"},
        "autoMergeRequest": None,
        "statusCheckRollup": [],
    },
]
_MERGED_ROWS = [
    {
        "number": 1455,
        "title": "Update betterleaks",
        "author": {"login": "app/renovate"},
        "mergedAt": "2026-09-29T22:30:00Z",
    }
]


def test_open_and_merged_prs_render_in_the_claim_grammar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    calls = _fake_gh(
        monkeypatch,
        open_prs=json.dumps(_OPEN_ROWS),
        merged_prs=json.dumps(_MERGED_ROWS),
    )

    snapshot = session_state.gather(repo, since="2026-09-29T22:15:03Z")
    rendered = session_state.render(snapshot)

    assert snapshot.since_source == "--since"
    assert "- **open PRs** (4):" in rendered
    assert (
        "  - #1449 OPEN, auto-merge armed, RED (fail:1 pending:0 pass:2) — "
        "`Update 'image' inputs` (@app/renovate)"
    ) in rendered
    assert (
        "  - #1141 OPEN, green (fail:0 pending:0 pass:2) — `Add service` (@sortakool)"
    ) in rendered
    assert "  - #1200 OPEN, PENDING (fail:0 pending:1 pass:1)" in rendered
    assert "  - #1201 OPEN, no checks (fail:0 pending:0 pass:0)" in rendered
    assert (
        "- **merged since** 2026-09-29T22:15:03Z (--since) (1):\n"
        "  - #1455 MERGED 2026-09-29T22:30:00Z — `Update betterleaks` (@app/renovate)"
    ) in rendered
    open_call, merged_call = calls[1], calls[2]
    assert open_call[:5] == ["pr", "list", "--limit", "100", "--state"]
    assert "open" in open_call
    assert "number,title,author,autoMergeRequest,statusCheckRollup" in open_call
    assert "merged:>=2026-09-29T22:15:03Z" in merged_call
    assert "number,title,author,mergedAt" in merged_call


def test_rendered_pr_rows_verify_themselves_through_handoff_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The row grammar IS the claim grammar: every rendered row must hold."""
    repo = _repo(tmp_path)
    _fake_gh(
        monkeypatch,
        open_prs=json.dumps(_OPEN_ROWS),
        merged_prs=json.dumps(_MERGED_ROWS),
    )
    snapshot = session_state.gather(repo, since="2026-09-29T00:00:00Z")
    assert snapshot.open_prs is not None
    assert snapshot.merged_prs is not None
    facts = {
        summary.number: pr_facts.PrFacts(
            summary.number,
            pr_facts.ItemKind.PR,
            summary.state,
            auto_merge=summary.auto_merge,
            checks=summary.checks or pr_facts.CheckCounts(0, 0, 0),
        )
        for summary in (*snapshot.open_prs, *snapshot.merged_prs)
    }

    claims = handoff_check.extract_claims(
        session_state.render(snapshot), source="state"
    )

    words = {(claim.number, claim.word.value) for claim in claims}
    assert words == {
        (1449, "OPEN"),
        (1449, "auto-merge armed"),
        (1449, "RED"),
        (1141, "OPEN"),
        (1141, "green"),
        (1200, "OPEN"),
        (1201, "OPEN"),
        (1455, "MERGED"),
    }
    assert all(
        handoff_check.claim_holds(claim.word, facts[claim.number]) for claim in claims
    )


def test_repo_pr_lookups_fail_closed_as_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)

    def failing(args: list[str], _root: Path) -> tuple[int, str]:
        if "--head" in args:
            return 0, "[]"
        return 1, "HTTP 502"

    monkeypatch.setattr(pr_facts, "run_gh", failing)
    snapshot = session_state.gather(repo, since="2026-09-29T00:00:00Z")
    rendered = session_state.render(snapshot)

    assert snapshot.open_prs is None
    assert snapshot.merged_prs is None
    assert (
        "- **open PRs**: UNVERIFIABLE — gh did not return a usable answer" in rendered
    )
    assert (
        "- **merged since** 2026-09-29T00:00:00Z (--since): UNVERIFIABLE — "
        "gh did not return a usable answer"
    ) in rendered


def test_one_malformed_repo_row_fails_the_whole_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    rows = [*_OPEN_ROWS, {"number": "1", "title": "string number"}]
    _fake_gh(monkeypatch, open_prs=json.dumps(rows))

    snapshot = session_state.gather(repo, since="2026-09-29T00:00:00Z")

    assert snapshot.open_prs is None
    assert snapshot.merged_prs == ()


def test_no_pr_renders_both_repo_lists_as_not_requested(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    rendered = session_state.render(session_state.gather(repo, with_pr=False))

    assert "- **open PRs**: not requested (--no-pr)" in rendered
    assert "- **merged since**: not requested (--no-pr)" in rendered


def test_default_since_uses_the_newest_handoff_mtime(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    plans = repo / ".agent" / "plans"
    plans.mkdir(parents=True)
    older = plans / "session-2026-09-29.md"
    newest = plans / "session-2026-09-29b.md"
    older.write_text("old\n")
    newest.write_text("new\n")
    stamp = datetime(2026, 9, 29, 22, 15, 3, tzinfo=UTC).timestamp()
    os.utime(newest, (stamp, stamp))
    os.utime(older, (stamp + 3600, stamp + 3600))

    since, source = session_state.default_since(repo, datetime.now(UTC))

    assert since == "2026-09-29T22:15:03Z"
    assert source == ".agent/plans/session-2026-09-29b.md mtime"


def test_default_since_falls_back_to_24h_without_a_handoff(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 30, 1, 2, 3, tzinfo=UTC)

    assert session_state.default_since(repo, now) == (
        "2026-09-29T01:02:03Z",
        "24h fallback",
    )


def test_gather_defaults_since_from_the_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    calls = _fake_gh(monkeypatch)

    snapshot = session_state.gather(repo)

    assert snapshot.since_source == "24h fallback"
    assert f"merged:>={snapshot.since}" in calls[2]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-29T22:00:00Z", "2026-09-29T22:00:00Z"),
        ("2026-09-29T15:00:00-07:00", "2026-09-29T22:00:00Z"),
        ("2026-09-29T22:00:00", "2026-09-29T22:00:00Z"),
        ("2026-09-29", "2026-09-29T00:00:00Z"),
        ("yesterday", None),
    ],
)
def test_parse_since_normalizes_to_utc(value: str, expected: str | None) -> None:
    assert session_state.parse_since(value) == expected


@pytest.mark.parametrize("args", [["--since", "not-a-date"], ["--since"]])
def test_main_rejects_an_unparsable_since(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], args: list[str]
) -> None:
    repo = _repo(tmp_path)

    assert session_state.main(args, repo) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("session-state: --since needs an ISO-8601")


def test_main_passes_a_normalized_since_to_the_merged_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    calls = _fake_gh(monkeypatch)
    args = cli_main.setup_parser().parse_args(
        ["session-state", "--since", "2026-09-29T15:00:00-07:00"]
    )
    assert args.since == "2026-09-29T15:00:00-07:00"

    assert session_state.main(["--since", args.since], repo) == 0

    assert "merged:>=2026-09-29T22:00:00Z" in calls[2]
    assert "(--since)" in capsys.readouterr().out


# --- S29-H round 1 (R2, R3, R5, R7-M1) ---------------------------------------


def _handoffs(repo: Path, stamps: dict[str, int]) -> Path:
    plans = repo / ".agent" / "plans"
    plans.mkdir(parents=True)
    for name, stamp in stamps.items():
        (plans / name).write_text("x\n")
        os.utime(plans / name, (stamp, stamp))
    return plans


_T_B = int(datetime(2026, 9, 29, 22, 15, 3, tzinfo=UTC).timestamp())
_T_C = _T_B + 3600


def test_default_since_excludes_the_handoff_being_written(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    plans = _handoffs(
        repo, {"session-2026-09-29b.md": _T_B, "session-2026-09-29c.md": _T_C}
    )
    now = datetime.now(UTC)

    assert session_state.default_since(repo, now) == (
        "2026-09-29T23:15:03Z",
        ".agent/plans/session-2026-09-29c.md mtime",
    )
    assert session_state.default_since(
        repo, now, exclude=plans / "session-2026-09-29c.md"
    ) == (
        "2026-09-29T22:15:03Z",
        (
            ".agent/plans/session-2026-09-29b.md mtime "
            "(excluding .agent/plans/session-2026-09-29c.md)"
        ),
    )


def test_main_for_accepts_a_handoff_that_does_not_exist_yet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    _handoffs(repo, {"session-2026-09-29b.md": _T_B})
    calls = _fake_gh(monkeypatch)

    assert (
        session_state.main(["--for", ".agent/plans/session-2026-09-29c.md"], repo) == 0
    )

    assert "merged:>=2026-09-29T22:15:03Z" in calls[2]
    assert (
        "(.agent/plans/session-2026-09-29b.md mtime "
        "(excluding .agent/plans/session-2026-09-29c.md))"
    ) in capsys.readouterr().out


def test_main_since_wins_over_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _handoffs(repo, {"session-2026-09-29b.md": _T_B})
    calls = _fake_gh(monkeypatch)

    assert (
        session_state.main(
            ["--for", "x.md", "--since", "2026-09-29T20:00:00Z"],
            repo,
        )
        == 0
    )
    assert "merged:>=2026-09-29T20:00:00Z" in calls[2]


def test_main_rejects_for_without_a_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    assert session_state.main(["--for"], repo) == 2
    assert capsys.readouterr().err == "session-state: --for needs a handoff path\n"


def test_branch_pr_and_commit_subjects_render_as_code_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pasted snapshot must not fail its own check on free text (R3)."""
    repo = _repo(tmp_path)
    (repo / "tracked.txt").write_text("two\n")
    _git(repo, "commit", "-qam", "revert #12 so it is MERGED `now` and RED")
    rows = [
        {"number": 42, "title": "Keep #7 `OPEN` and green", "statusCheckRollup": []}
    ]
    _fake_gh(monkeypatch, branch=json.dumps(rows))

    rendered = session_state.render(session_state.gather(repo, since="2026-09-29"))

    assert (
        "- **open PR**: #42 — `Keep #7 'OPEN' and green` (checks: 0/0 passing)"
    ) in rendered
    assert "` `revert #12 so it is MERGED 'now' and RED`" in rendered
    assert handoff_check.extract_claims(rendered, source="state") == []


def _rows(count: int) -> str:
    return json.dumps(
        [
            {"number": n, "title": "t", "author": {"login": "a"}, "mergedAt": "x"}
            for n in range(1, count + 1)
        ]
    )


def test_a_list_that_fills_the_limit_says_it_may_be_truncated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _fake_gh(monkeypatch, open_prs=_rows(100), merged_prs=_rows(100))

    snapshot = session_state.gather(repo, since="2026-09-29T00:00:00Z")
    rendered = session_state.render(snapshot)

    assert snapshot.open_truncated
    assert snapshot.merged_truncated
    assert (
        "- **open PRs** (100, TRUNCATED at --limit 100 — list may be incomplete):"
    ) in rendered
    assert (
        "- **merged since** 2026-09-29T00:00:00Z (--since) "
        "(100, TRUNCATED at --limit 100 — list may be incomplete):"
    ) in rendered


def test_a_list_below_the_limit_is_not_flagged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _fake_gh(monkeypatch, open_prs=_rows(99), merged_prs=_rows(99))

    snapshot = session_state.gather(repo, since="2026-09-29T00:00:00Z")
    rendered = session_state.render(snapshot)

    assert not snapshot.open_truncated
    assert not snapshot.merged_truncated
    assert "- **open PRs** (99):" in rendered
    assert "(--since) (99):" in rendered
    assert "TRUNCATED" not in rendered


def _dispatch(argv: list[str], repo: Path) -> object:
    """Run the real main.py parser + dispatch; return the SystemExit code."""
    args = cli_main.setup_parser().parse_args(argv)
    try:
        cli_main.run_command(args, repo)
    except SystemExit as exc:
        return exc.code
    message = "session-state dispatch did not exit"
    raise AssertionError(message)


def test_cli_dispatch_forwards_since(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M1: main.py must forward --since to session_state.main."""
    repo = _repo(tmp_path)
    calls = _fake_gh(monkeypatch)

    assert _dispatch(["session-state", "--since", "2026-09-29T20:00:00Z"], repo) == 0
    assert "merged:>=2026-09-29T20:00:00Z" in calls[2]


def test_cli_dispatch_forwards_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _handoffs(repo, {"session-2026-09-29b.md": _T_B, "session-2026-09-29c.md": _T_C})
    calls = _fake_gh(monkeypatch)

    code = _dispatch(
        ["session-state", "--for", ".agent/plans/session-2026-09-29c.md"], repo
    )

    assert code == 0
    assert "merged:>=2026-09-29T22:15:03Z" in calls[2]
