# Copyright (c) 2026 Raymond Manaloto
"""Tests for the session-start mod's judgement (spec §8 verification additions)."""

from __future__ import annotations

import fcntl
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import reap
from dotfiles_setup import session_common as sc
from dotfiles_setup import session_start as ss
from dotfiles_setup.main import setup_parser

SESSION = "11111111-aaaa-4000-8000-000000000001"
_NS = 1_000_000_000
#: 2026-10-02 16:31:03.123456789 in Chicago (CDT, -05).
NOW = int(datetime(2026, 10, 2, 21, 31, 3, tzinfo=UTC).timestamp()) * _NS + 123_456_789
STAMP = "20261002T163103.123456789-05"
FOREGROUND = (
    reap.Process(pid=100, ppid=1, age_s=1, state="S", command="claude"),
    reap.Process(pid=201, ppid=100, age_s=1, state="S", command="python"),
)


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


def _job(jobs_dir: Path, name: str, *, name_source: str = "user") -> None:
    path = jobs_dir / SESSION[:8] / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"sessionId": SESSION, "name": name, "nameSource": name_source}),
        encoding="utf-8",
    )


def _decide(
    tmp_path: Path,
    cwd: Path,
    *,
    interactive: bool = True,
    session_id: str = SESSION,
    timeout_s: float = sc.STATE_LOCK_TIMEOUT_S,
) -> ss.StartDecision:
    return ss.decide(
        ss.StartRequest(session_id=session_id, cwd=cwd, interactive=interactive),
        ss.StartDeps(
            state_dir=tmp_path / "state",
            jobs_dir=tmp_path / "jobs",
            now_ns=NOW,
            processes=FOREGROUND,
            self_pid=201,
            lock_timeout_s=timeout_s,
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
    assert (
        ss.mark_renamed(SESSION, name, tmp_path / "state", jobs_dir=tmp_path / "jobs")
        == 0
    )
    done = _decide(tmp_path, repo)
    assert (done.action, done.prefix) == ("already-ran", None)


def test_mark_renamed_refuses_without_a_decision(tmp_path: Path) -> None:
    """Nothing to mark: rc 2, and an invalid id is refused too."""
    assert (
        ss.mark_renamed(SESSION, "x", tmp_path / "state", jobs_dir=tmp_path / "jobs")
        == 2
    )
    assert (
        ss.mark_renamed("../x", "x", tmp_path / "state", jobs_dir=tmp_path / "jobs")
        == 2
    )


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
    tmp_path: Path,
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hook's exact argv shapes parse and answer through `main`."""
    # `main` builds StartDeps without `processes`, so an "auto" record falls
    # through to reap.snapshot() of the REAL tree; under a named claude caller
    # that read "nonconforming" instead of "defer". Pin an empty tree.
    monkeypatch.setattr(reap, "snapshot", lambda: ())
    state = str(tmp_path / "state")
    _job(tmp_path / "jobs", "auto-session", name_source="auto")
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
            "--jobs-dir",
            str(tmp_path / "jobs"),
        ]
    )
    _job(tmp_path / "jobs", "n", name_source="auto")
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


@pytest.mark.parametrize(
    "case",
    [
        (
            "user-conforming",
            "claude bg-pty-host --bg-spare",
            "keep",
            f"dotfiles-{STAMP}.lane",
        ),
        ("user-other", "claude bg-pty-host --bg-spare", "nonconforming", "lane-g"),
        ("auto", "claude bg-pty-host --bg-spare", "defer", None),
        ("absent", "claude bg-pty-host --bg-spare", "unknown", None),
        ("absent", "claude --bg-spare", "unknown", None),
        ("absent", "claude -n lane-g", "nonconforming", "lane-g"),
        (
            "absent",
            f"claude --name dotfiles-{STAMP}.lane",
            "keep",
            f"dotfiles-{STAMP}.lane",
        ),
        ("absent", "claude --name=lane-g", "nonconforming", "lane-g"),
        ("auto", "claude -n lane-g", "nonconforming", "lane-g"),
        ("absent", "claude", "defer", None),
        ("absent", "claude -n", "unknown", None),
        ("absent", "claude --name=", "unknown", None),
        ("absent", 'claude --name "unfinished', "unknown", None),
    ],
)
def test_r10_name_provenance_table_preserves_user_names_and_unknown_spares(
    tmp_path: Path,
    repo: Path,
    case: tuple[str, str, str, str | None],
) -> None:
    """Auto names are not -n names; missing spare records cannot authorize rename."""
    record, argv, action, name = case
    if record == "user-conforming":
        _job(tmp_path / "jobs", f"dotfiles-{STAMP}.lane")
    elif record == "user-other":
        _job(tmp_path / "jobs", "lane-g")
    elif record == "auto":
        _job(tmp_path / "jobs", "auto-session", name_source="auto")
    processes = (
        reap.Process(pid=100, ppid=1, age_s=1, state="S", command=argv),
        FOREGROUND[1],
    )
    decision = ss.decide(
        ss.StartRequest(SESSION, repo),
        ss.StartDeps(
            state_dir=tmp_path / "state",
            jobs_dir=tmp_path / "jobs",
            now_ns=NOW,
            processes=processes,
            self_pid=201,
        ),
    )
    assert (decision.action, decision.name) == (action, name)
    if action == "unknown":
        assert decision.prefix is None


def test_r10_generated_name_can_be_renamed_on_a_feature_branch(
    tmp_path: Path, repo: Path
) -> None:
    """A job with a harness-generated name still follows the branch naming rule."""
    _git("checkout", "-q", "-b", "feat/real-task", cwd=repo)
    _job(tmp_path / "jobs", "auto-title", name_source="auto")
    decision = _decide(tmp_path, repo)
    assert (decision.action, decision.name) == ("rename", f"dotfiles-{STAMP}.real-task")


def test_r5_session_start_honors_the_same_external_state_lock(
    tmp_path: Path, repo: Path
) -> None:
    """Naming also waits for the native lock and fails visibly at its bound."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    with (state_dir / f"{SESSION}.json.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        decision = _decide(tmp_path, repo, timeout_s=0.05)
    assert (decision.action, decision.reload) == ("state-locked", False)


def test_r5_concurrent_starts_reload_only_once(tmp_path: Path, repo: Path) -> None:
    """One atomic naming claim, without lost JSON updates under overlapping calls."""
    with ThreadPoolExecutor(max_workers=8) as executor:
        decisions = list(executor.map(lambda _: _decide(tmp_path, repo), range(16)))
    assert sum(decision.reload for decision in decisions) == 1
    assert sum(decision.action == "already-ran" for decision in decisions) == 15


def test_r12_pending_recovers_across_reload_and_clears_only_after_confirmation(
    tmp_path: Path, repo: Path
) -> None:
    """Persistent prefix remains readable until the resolved rename is recorded."""
    _decide(tmp_path, repo)
    recovered = ss.pending(SESSION, tmp_path / "state")
    assert (recovered.reload, recovered.prefix) == (False, f"dotfiles-{STAMP}")
    assert ss.pending(SESSION, tmp_path / "state").prefix == recovered.prefix
    assert (
        ss.mark_renamed(
            SESSION,
            f"dotfiles-{STAMP}.task",
            tmp_path / "state",
            jobs_dir=tmp_path / "jobs",
        )
        == 0
    )
    assert ss.pending(SESSION, tmp_path / "state").prefix is None


def test_r12_known_rename_is_recoverable_until_confirmed(
    tmp_path: Path, repo: Path
) -> None:
    """A rejected branch-based rename can also be retried after reload."""
    _git("checkout", "-q", "-b", "feat/task", cwd=repo)
    first = _decide(tmp_path, repo)
    recovered = ss.pending(SESSION, tmp_path / "state")
    assert (recovered.action, recovered.reload, recovered.name) == (
        "rename",
        False,
        first.name,
    )
    assert (
        ss.mark_renamed(
            SESSION,
            f"dotfiles-{STAMP}.task",
            tmp_path / "state",
            jobs_dir=tmp_path / "jobs",
        )
        == 0
    )
    assert ss.pending(SESSION, tmp_path / "state").action == "already-ran"


@pytest.mark.parametrize(
    "record", ["missing", "matching", "different", "corrupt", "wrong-id"]
)
def test_s5_rename_confirmation_requires_matching_available_job(
    tmp_path: Path,
    repo: Path,
    record: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A resolved command cannot erase pending naming when its job name disagrees."""
    first = _decide(tmp_path, repo)
    assert first.action == "defer"
    name = f"dotfiles-{STAMP}.confirmed"
    jobs, state_dir = tmp_path / "jobs", tmp_path / "state"
    if record != "missing":
        _job(jobs, name if record == "matching" else "old-name", name_source="auto")
        job_path = jobs / SESSION[:8] / "state.json"
        if record == "corrupt":
            job_path.write_text("{")
        elif record == "wrong-id":
            job_path.write_text(
                json.dumps({"sessionId": "another-session", "name": name})
            )
    state_path = state_dir / f"{SESSION}.json"
    before = state_path.read_bytes()
    rc = ss.mark_renamed(SESSION, name, state_dir, jobs_dir=jobs)
    if record in {"missing", "matching"}:
        assert rc == 0
        assert ss.pending(SESSION, state_dir).prefix is None
    else:
        assert rc == 2
        assert "job name mismatch" in caplog.text
        assert state_path.read_bytes() == before
        assert ss.pending(SESSION, state_dir).prefix == first.prefix
        _job(jobs, name, name_source="auto")
        assert ss.mark_renamed(SESSION, name, state_dir, jobs_dir=jobs) == 0
        assert ss.pending(SESSION, state_dir).prefix is None
