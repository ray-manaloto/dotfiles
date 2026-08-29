# Copyright (c) 2026 Raymond Manaloto
"""Tests for the read-only session-state snapshot."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import main as cli_main
from dotfiles_setup import session_state

if TYPE_CHECKING:
    from typing import Literal, TypedDict, Unpack

    import pytest

    class _RunKwargs(TypedDict):
        cwd: Path
        capture_output: bool
        text: Literal[True]
        errors: str
        check: bool
        timeout: int


_GIT_TIMEOUT = 30


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        timeout=_GIT_TIMEOUT,
    )


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
                {"conclusion": "SUCCESS"},
                {"state": "SUCCESS"},
                {"status": "IN_PROGRESS"},
            ],
        }
    ]
    monkeypatch.setattr(
        session_state,
        "_gh",
        lambda _args, _root: (0, json.dumps(rows)),
    )

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
    monkeypatch.setattr(
        session_state,
        "_gh",
        lambda _args, _root: (0, json.dumps(rows)),
    )

    snapshot = session_state.gather(repo)

    assert snapshot.pr is not None
    assert snapshot.pr.checks_summary == "0/0 passing"


def test_malformed_pr_rows_are_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    monkeypatch.setattr(session_state, "_gh", lambda _args, _root: (0, '"not a list"'))

    assert session_state.gather(repo).pr == session_state.PullRequest(
        session_state.PrState.UNVERIFIABLE
    )


def test_non_dict_check_rollup_is_unknown_instead_of_crashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    rows = [{"number": 42, "title": "Bad rollup", "statusCheckRollup": ["bad"]}]
    monkeypatch.setattr(
        session_state,
        "_gh",
        lambda _args, _root: (0, json.dumps(rows)),
    )

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
    monkeypatch.setattr(
        session_state,
        "_gh",
        lambda _args, _root: (0, json.dumps(rows)),
    )

    assert session_state.gather(repo).pr == session_state.PullRequest(
        session_state.PrState.UNVERIFIABLE
    )


def test_empty_pr_result_is_none_but_gh_timeout_is_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    monkeypatch.setattr(session_state, "_gh", lambda _args, _root: (0, "[]"))
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
