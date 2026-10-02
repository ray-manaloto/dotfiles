# Copyright (c) 2026 Raymond Manaloto
"""Tests for the session-start mod's judgement (spec §8 verification additions)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import session_start as ss
from dotfiles_setup.main import setup_parser

SESSION = "11111111-aaaa-4000-8000-000000000001"
_NS = 1_000_000_000
#: 2026-10-02 16:31:03.123456789 in Chicago (CDT, -05).
NOW = int(datetime(2026, 10, 2, 21, 31, 3, tzinfo=UTC).timestamp()) * _NS + 123_456_789
STAMP = "20261002T163103.123456789-05"


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real repository on `main` with one commit and no remote."""
    path = tmp_path / "repo"
    path.mkdir()
    _git("init", "-q", "-b", "main", cwd=path)
    _git("commit", "-q", "--allow-empty", "-m", "root", cwd=path)
    return path


def _job(jobs_dir: Path, name: str) -> None:
    path = jobs_dir / SESSION[:8] / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"sessionId": SESSION, "name": name}), encoding="utf-8")


def _decide(
    tmp_path: Path, cwd: Path, *, interactive: bool = True, session_id: str = SESSION
) -> ss.StartDecision:
    return ss.decide(
        ss.StartRequest(session_id=session_id, cwd=cwd, interactive=interactive),
        ss.StartDeps(
            state_dir=tmp_path / "state", jobs_dir=tmp_path / "jobs", now_ns=NOW
        ),
    )


# ── the four naming actions ──────────────────────────────────────────────────


def test_keep_a_conforming_dash_n_name(tmp_path: Path, repo: Path) -> None:
    """Q1a: a conforming `-n` name is kept; the reloads still run."""
    name = f"kb-{STAMP}.lane-x"
    _job(tmp_path / "jobs", name)
    decision = _decide(tmp_path, repo)
    assert (decision.action, decision.reload, decision.name) == ("keep", True, name)


def test_nonconforming_dash_n_name_is_never_renamed(tmp_path: Path, repo: Path) -> None:
    """Q1a: lanes are addressed by their name, so it is only reported."""
    _job(tmp_path / "jobs", "dotfiles-20261002b.coordinator")
    decision = _decide(tmp_path, repo)
    assert (decision.action, decision.name, decision.prefix) == (
        "nonconforming",
        "dotfiles-20261002b.coordinator",
        None,
    )


def test_rename_off_the_default_branch_uses_the_branch_slug(
    tmp_path: Path, repo: Path
) -> None:
    """Q2a: no `-n` name on a feature branch → `<project>-<ts>.<slug>`."""
    _git("checkout", "-q", "-b", "feat/coordinator/auto-handoff", cwd=repo)
    decision = _decide(tmp_path, repo)
    assert (decision.action, decision.reload) == ("rename", True)
    assert decision.name == f"dotfiles-{STAMP}.coordinator-auto-handoff"
    assert ss.is_conforming(decision.name)


def test_defer_on_the_default_branch(tmp_path: Path, repo: Path) -> None:
    """Q2a: no `-n` name on the default branch → the first prompt names it."""
    decision = _decide(tmp_path, repo)
    assert (decision.action, decision.name, decision.prefix) == (
        "defer",
        None,
        f"dotfiles-{STAMP}",
    )


def test_default_branch_comes_from_origin_head(tmp_path: Path, repo: Path) -> None:
    """origin/HEAD decides the default: on `trunk` defer, on `main` rename."""
    _git("update-ref", "refs/remotes/origin/trunk", "HEAD", cwd=repo)
    _git(
        "symbolic-ref",
        "refs/remotes/origin/HEAD",
        "refs/remotes/origin/trunk",
        cwd=repo,
    )
    assert _decide(tmp_path, repo).action == "rename"
    _git("checkout", "-q", "-b", "trunk", cwd=repo)
    assert _decide(tmp_path, repo, session_id="22222222-bbbb").action == "defer"


def test_detached_head_and_non_repositories_defer(tmp_path: Path, repo: Path) -> None:
    """No branch to name the session after: defer to the first prompt."""
    _git("checkout", "-q", "--detach", cwd=repo)
    assert _decide(tmp_path, repo).action == "defer"
    plain = tmp_path / "plain"
    plain.mkdir()
    assert _decide(tmp_path, plain, session_id="33333333-cccc").action == "defer"


@pytest.mark.parametrize(
    ("branch", "slug"),
    [
        ("feat/x", "x"),
        ("fix/a/b", "a-b"),
        ("docs/handoff-2026-10-02", "handoff-2026-10-02"),
        ("chore/deps", "deps"),
        ("refactor/one", "one"),
        ("test/two", "two"),
        ("feature/x", "feature-x"),  # not a stripped prefix
        ("ops/feat/x", "ops-feat-x"),  # only a LEADING prefix is stripped
        ("feat/fix/x", "fix-x"),  # and only one
    ],
)
def test_feature_slug(branch: str, slug: str) -> None:
    """Strip one leading type prefix; every `/` becomes `-`."""
    assert ss.feature_slug(branch) == slug


@pytest.mark.parametrize(
    "name",
    [
        f"dotfiles-{STAMP}.coordinator",
        f"kb-{STAMP}.lane",
        "dotfiles-20260115T090507.000000042-06.x",
        "kb-20260115T090507.000000042Z.x",
        "kb-20260115T090507.000000042+0530.x",
    ],
)
def test_conforming_names(name: str) -> None:
    """The §8 regex accepts every offset form the formatter can emit."""
    assert ss.is_conforming(name)


@pytest.mark.parametrize(
    "name",
    [
        "dotfiles-20261002b.coordinator",
        f"other-{STAMP}.x",
        "dotfiles-20261002T163103.123456-05.x",  # 6-digit fraction
        f"dotfiles-{STAMP}.",  # empty feature
        f"dotfiles-{STAMP}",  # no feature
    ],
)
def test_nonconforming_names(name: str) -> None:
    """The control arm: near-misses fail the convention."""
    assert not ss.is_conforming(name)


# ── once per session, and the reload interplay ───────────────────────────────


def test_second_call_is_already_ran_without_a_reload(
    tmp_path: Path, repo: Path
) -> None:
    """Q4a: state is written before answering, so a re-fire never re-reloads."""
    _git("checkout", "-q", "-b", "feat/x", cwd=repo)
    first = _decide(tmp_path, repo)
    state = json.loads((tmp_path / "state" / f"{SESSION}.json").read_text())
    assert state["action"] == "rename"
    again = _decide(tmp_path, repo)
    assert (again.action, again.reload, again.name, again.prefix) == (
        "already-ran",
        False,
        first.name,
        None,
    )


def test_a_pending_defer_survives_a_reload_until_marked(
    tmp_path: Path, repo: Path
) -> None:
    """already-ran carries the defer prefix until `renamed` is recorded."""
    _decide(tmp_path, repo)
    pending = _decide(tmp_path, repo)
    assert (pending.action, pending.prefix) == ("already-ran", f"dotfiles-{STAMP}")
    name = f"dotfiles-{STAMP}.lock-refresh"
    assert ss.mark_renamed(SESSION, name, tmp_path / "state") == 0
    done = _decide(tmp_path, repo)
    assert (done.action, done.prefix) == ("already-ran", None)


def test_mark_renamed_refuses_without_a_decision(tmp_path: Path) -> None:
    """Nothing to mark: rc 2, and an invalid id is refused too."""
    assert ss.mark_renamed(SESSION, "x", tmp_path / "state") == 2
    assert ss.mark_renamed("../x", "x", tmp_path / "state") == 2


def test_non_interactive_is_a_no_op(tmp_path: Path, repo: Path) -> None:
    """Q3a: `-p`/SDK sessions: no reload, no name, no state."""
    decision = _decide(tmp_path, repo, interactive=False)
    assert (decision.action, decision.reload) == ("non-interactive", False)
    assert not (tmp_path / "state").exists()


def test_invalid_session_id_and_failed_state_write(tmp_path: Path, repo: Path) -> None:
    """Neither answers with a reload; a failed write is reported."""
    assert _decide(tmp_path, repo, session_id="../../x").action == "invalid-session-id"
    (tmp_path / "state").write_text("a file where the dir should be", encoding="utf-8")
    failed = _decide(tmp_path, repo)
    assert (failed.action, failed.reload) == ("state-write-failed", False)
    assert failed.warnings


def test_decision_json_shape() -> None:
    """The hook's parseStart depends on exactly these keys."""
    decision = ss.StartDecision(
        action="defer", reload=True, name=None, prefix="p", session_id=SESSION
    )
    assert json.loads(decision.to_json()) == {
        "action": "defer",
        "reload": True,
        "name": None,
        "prefix": "p",
        "session_id": SESSION,
        "warnings": [],
    }


# ── CLI ──────────────────────────────────────────────────────────────────────


def test_cli_decide_and_renamed(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The hook's exact argv shapes parse and answer through `main`."""
    state = str(tmp_path / "state")
    decide_args = setup_parser().parse_args(
        [
            "session-start",
            "decide",
            "--session-id",
            SESSION,
            "--cwd",
            str(repo),
            "--state-dir",
            state,
            "--jobs-dir",
            str(tmp_path / "jobs"),
        ]
    )
    assert ss.main(decide_args, tmp_path) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "defer"
    renamed_args = setup_parser().parse_args(
        [
            "session-start",
            "renamed",
            "--session-id",
            SESSION,
            "--name",
            "n",
            "--state-dir",
            state,
        ]
    )
    assert ss.main(renamed_args, tmp_path) == 0
    non_interactive = setup_parser().parse_args(
        [
            "session-start",
            "decide",
            "--session-id",
            SESSION,
            "--cwd",
            str(repo),
            "--non-interactive",
        ]
    )
    assert ss.main(non_interactive, tmp_path) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "non-interactive"
