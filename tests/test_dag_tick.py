"""Tests for the launchd watchdog tick (dotfiles_setup.dag_tick, #578).

Pure/table-driven tests cover the terminal predicate, `classify()`,
`strip_respawn_env()`, `gate_status()`, and `plan()` directly — no
subprocess, no filesystem. The census-enrichment and action-execution paths
are exercised against `tmp_path` fixtures with `subprocess` monkeypatched;
none of these tests invoke the real `claude` binary or mutate anything on
this host.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import dag_tick

if TYPE_CHECKING:
    from collections.abc import Mapping

# ---------------------------------------------------------------------------
# is_terminal() — the 7 terminal-predicate arms from docs/receipts/565.md
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "tempo", "queued_prompt", "expected"),
    [
        ("done", "idle", False, True),
        ("failed", "idle", False, True),
        ("stopped", "idle", False, True),
        ("killed", "idle", False, False),
        ("blocked", "idle", False, False),
        ("done", "active", False, False),
        ("done", "idle", True, False),
    ],
)
def test_terminal_predicate_arms(
    state: str, tempo: str, *, queued_prompt: bool, expected: bool
) -> None:
    assert dag_tick.is_terminal(state, tempo, queued_prompt=queued_prompt) is expected


# ---------------------------------------------------------------------------
# classify() — see docstring for the precedence order it encodes
# ---------------------------------------------------------------------------


def _node(
    *,
    node_id: str = "abc123",
    state: str | None = "blocked",
    tempo: str | None = "idle",
    queued_prompt: bool = False,
) -> dag_tick.Node:
    return dag_tick.Node(
        node_id=node_id, state=state, tempo=tempo, queued_prompt=queued_prompt
    )


def test_classify_done_regardless_of_pid_alive() -> None:
    node = _node(state="done", tempo="idle")
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.DONE
    )
    assert (
        dag_tick.classify(node, pid_alive=True, state_age_s=None)
        is dag_tick.NodeClass.DONE
    )


def test_classify_dead_when_not_terminal_and_pid_not_alive() -> None:
    node = _node(state="blocked", tempo="idle")
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.DEAD
    )


def test_classify_wedged_when_active_and_stale() -> None:
    node = _node(state="blocked", tempo="active")
    result = dag_tick.classify(
        node, pid_alive=True, state_age_s=200.0, stall_after_s=120.0
    )
    assert result is dag_tick.NodeClass.WEDGED


def test_classify_alive_when_active_but_not_yet_stale() -> None:
    node = _node(state="blocked", tempo="active")
    result = dag_tick.classify(
        node, pid_alive=True, state_age_s=10.0, stall_after_s=120.0
    )
    assert result is dag_tick.NodeClass.ALIVE


def test_classify_alive_default() -> None:
    node = _node(state="blocked", tempo="idle")
    result = dag_tick.classify(node, pid_alive=True, state_age_s=None)
    assert result is dag_tick.NodeClass.ALIVE


def test_classify_active_with_unknown_age_is_alive_not_wedged() -> None:
    node = _node(state="blocked", tempo="active")
    result = dag_tick.classify(node, pid_alive=True, state_age_s=None)
    assert result is dag_tick.NodeClass.ALIVE


# ---------------------------------------------------------------------------
# strip_respawn_env() — both directions
# ---------------------------------------------------------------------------


def test_strip_respawn_env_removes_denylist_and_bg_prefix() -> None:
    env: dict[str, str] = {
        "PATH": "/usr/bin",
        "CLAUDE_CODE_SESSION_KIND": "background",
        "CLAUDE_BG_SOURCE": "daemon",
        "CLAUDE_BG_ISOLATION": "none",
        "CLAUDE_BG_BACKEND": "daemon",
        "CLAUDE_CODE_SESSION_NAME": "x",
        "CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1",
        "CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS": "100",
        "CLAUDE_CODE_RESUME_PROMPT": "hi",
        "CLAUDE_CODE_RESUME_SOURCE_ALIVE": "1",
        "CLAUDE_BG_POST_CLEAR_RESPAWN": "1",
        "CLAUDE_BG_SESSION_PERMISSION_RULES": "{}",
        "CLAUDE_BG_MEMORY_TOGGLED_OFF": "1",
        "CLAUDE_JOB_DIR": "job-dir-marker",
        "CLAUDE_BG_UNLISTED_BUT_PREFIXED": "still dies",
    }
    assert dag_tick.strip_respawn_env(env) == {"PATH": "/usr/bin"}


def test_strip_respawn_env_preserves_control_vars() -> None:
    env: Mapping[str, str] = {
        "PATH": "/usr/bin",
        "HOME": "/Users/x",
        "AWS_REGION": "us-east-1",
    }
    result = dag_tick.strip_respawn_env(env)
    assert result == dict(env)
    assert result is not env


def test_strip_respawn_env_defaults_to_os_environ(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("CLAUDE_BG_SOURCE", "daemon")
    result = dag_tick.strip_respawn_env()
    assert result["PATH"] == "/usr/bin"
    assert "CLAUDE_BG_SOURCE" not in result


# ---------------------------------------------------------------------------
# gate_status() — the three faces
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stderr_text", "expected"),
    [
        (
            "No job matching 'zzbogus'. Run 'claude agents' to list running sessions.",
            "on",
        ),
        ("'logs' is disabled by CLAUDE_CODE_DISABLE_AGENT_VIEW.", "off"),
        ("'logs' is disabled by the 'disableAgentView' setting.", "off"),
        ("some unrelated error message", "unknown"),
        ("", "unknown"),
    ],
)
def test_gate_status_three_faces(stderr_text: str, expected: str) -> None:
    assert dag_tick.gate_status(stderr_text) == expected


# ---------------------------------------------------------------------------
# plan() — the classification -> action table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("node_class", "pid_alive", "expected_kind"),
    [
        (dag_tick.NodeClass.DEAD, False, dag_tick.ActionKind.RESPAWN),
        (dag_tick.NodeClass.DEAD, True, dag_tick.ActionKind.RESPAWN),
        (dag_tick.NodeClass.DONE, True, dag_tick.ActionKind.STOP),
        (dag_tick.NodeClass.DONE, False, None),
        (dag_tick.NodeClass.WEDGED, True, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.WEDGED, False, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.ALIVE, True, None),
        (dag_tick.NodeClass.ALIVE, False, None),
    ],
)
def test_plan_maps_classification_to_actions(
    node_class: dag_tick.NodeClass,
    *,
    pid_alive: bool,
    expected_kind: dag_tick.ActionKind | None,
) -> None:
    node = dag_tick.ClassifiedNode("abc123", node_class, pid_alive=pid_alive)
    actions = dag_tick.plan([node])
    if expected_kind is None:
        assert actions == []
    else:
        assert [action.kind for action in actions] == [expected_kind]
        assert actions[0].node_id == "abc123"


def test_plan_is_pure_and_order_preserving() -> None:
    nodes = [
        dag_tick.ClassifiedNode("dead-1", dag_tick.NodeClass.DEAD, pid_alive=False),
        dag_tick.ClassifiedNode("alive-1", dag_tick.NodeClass.ALIVE, pid_alive=True),
        dag_tick.ClassifiedNode("done-1", dag_tick.NodeClass.DONE, pid_alive=True),
    ]
    actions = dag_tick.plan(nodes)
    assert [a.node_id for a in actions] == ["dead-1", "done-1"]


# ---------------------------------------------------------------------------
# try_acquire_lock() — lock contention (second flock fails)
# ---------------------------------------------------------------------------


def test_lock_contention_second_acquire_fails(tmp_path: Path) -> None:
    lock_path = tmp_path / "dag-tick.lock"
    first = dag_tick.try_acquire_lock(lock_path)
    assert first is not None
    try:
        second = dag_tick.try_acquire_lock(lock_path)
        assert second is None
    finally:
        first.close()


def test_lock_release_allows_reacquire(tmp_path: Path) -> None:
    lock_path = tmp_path / "dag-tick.lock"
    first = dag_tick.try_acquire_lock(lock_path)
    assert first is not None
    first.close()
    second = dag_tick.try_acquire_lock(lock_path)
    assert second is not None
    second.close()


# ---------------------------------------------------------------------------
# read_roster, pid_is_alive, and background_pid_alive — daemon liveness
# ---------------------------------------------------------------------------


def test_read_roster_missing_file_returns_none(tmp_path: Path) -> None:
    assert dag_tick.read_roster(tmp_path) is None


def test_read_roster_malformed_json_returns_none(tmp_path: Path) -> None:
    (tmp_path / "roster.json").write_text("{not json")
    assert dag_tick.read_roster(tmp_path) is None


def test_read_roster_non_dict_workers_returns_none(tmp_path: Path) -> None:
    (tmp_path / "roster.json").write_text(json.dumps({"workers": "nope"}))
    assert dag_tick.read_roster(tmp_path) is None


def test_read_roster_parses_workers_and_skips_bad_entries(tmp_path: Path) -> None:
    (tmp_path / "roster.json").write_text(
        json.dumps(
            {
                "proto": 1,
                "supervisorPid": 1,
                "workers": {
                    "abc123": {"pid": 999, "procStart": "Wed Jul 15 10:54:17 2026"},
                    "bad-entry": "not-a-dict",
                    "no-pid": {"procStart": "x"},
                },
            }
        )
    )
    roster = dag_tick.read_roster(tmp_path)
    assert roster == {
        "abc123": dag_tick.RosterWorker(pid=999, proc_start="Wed Jul 15 10:54:17 2026")
    }


def test_pid_is_alive_true_for_self() -> None:
    assert dag_tick.pid_is_alive(os.getpid()) is True


def test_pid_is_alive_false_for_a_dead_pid() -> None:
    assert dag_tick.pid_is_alive(999_999) is False


def test_background_pid_alive_none_roster_is_conservative_true() -> None:
    assert dag_tick.background_pid_alive("abc123", None) is True


def test_background_pid_alive_missing_entry_is_false() -> None:
    assert dag_tick.background_pid_alive("abc123", {}) is False


def test_background_pid_alive_checks_the_roster_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dag_tick, "pid_is_alive", lambda pid: pid == 111)
    alive_roster = {"abc123": dag_tick.RosterWorker(pid=111, proc_start=None)}
    dead_roster = {"abc123": dag_tick.RosterWorker(pid=222, proc_start=None)}
    assert dag_tick.background_pid_alive("abc123", alive_roster) is True
    assert dag_tick.background_pid_alive("abc123", dead_roster) is False


# ---------------------------------------------------------------------------
# load_state_json — reading one job's state.json off disk
# ---------------------------------------------------------------------------


def test_load_state_json_missing_returns_none_none(tmp_path: Path) -> None:
    data, mtime = dag_tick.load_state_json(tmp_path, "nope")
    assert data is None
    assert mtime is None


def test_load_state_json_malformed_returns_none_none(tmp_path: Path) -> None:
    job_dir = tmp_path / "abc123"
    job_dir.mkdir()
    (job_dir / "state.json").write_text("{not json")
    data, mtime = dag_tick.load_state_json(tmp_path, "abc123")
    assert data is None
    assert mtime is None


def test_load_state_json_non_dict_returns_none_none(tmp_path: Path) -> None:
    job_dir = tmp_path / "abc123"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps(["not", "a", "dict"]))
    data, mtime = dag_tick.load_state_json(tmp_path, "abc123")
    assert data is None
    assert mtime is None


def test_load_state_json_parses_and_returns_mtime(tmp_path: Path) -> None:
    job_dir = tmp_path / "abc123"
    job_dir.mkdir()
    state_path = job_dir / "state.json"
    state_path.write_text(json.dumps({"state": "blocked", "tempo": "idle"}))
    data, mtime = dag_tick.load_state_json(tmp_path, "abc123")
    assert data == {"state": "blocked", "tempo": "idle"}
    assert mtime == pytest.approx(state_path.stat().st_mtime)


# ---------------------------------------------------------------------------
# classify_background_rows — census enrichment + classification, end to end
# ---------------------------------------------------------------------------


def _write_state(jobs_dir: Path, node_id: str, payload: dict[str, object]) -> None:
    job_dir = jobs_dir / node_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "state.json").write_text(json.dumps(payload))


def test_classify_background_rows_missing_state_json_is_conservative_alive(
    tmp_path: Path,
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    jobs_dir.mkdir()
    daemon_dir.mkdir()
    rows: list[dict[str, object]] = [{"id": "ghost", "kind": "background"}]
    result = dag_tick.classify_background_rows(
        rows,
        jobs_dir=jobs_dir,
        daemon_dir=daemon_dir,
        stall_after_s=120.0,
        verbose=True,
    )
    assert result.classified == [
        dag_tick.ClassifiedNode("ghost", dag_tick.NodeClass.ALIVE, pid_alive=True)
    ]
    assert any("missing/unparseable" in note for note in result.notes)


def test_classify_background_rows_dead_when_no_roster_entry(tmp_path: Path) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()
    # A READABLE roster that simply does not name this node — the "even when
    # its process has exited" case the harness's own docs describe. A missing
    # roster FILE is a different case (conservative ALIVE) — see the sibling
    # test below.
    (daemon_dir / "roster.json").write_text(json.dumps({"workers": {}}))
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}],
        jobs_dir=jobs_dir,
        daemon_dir=daemon_dir,
        stall_after_s=120.0,
        verbose=False,
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.DEAD
    assert result.notes == []


def test_classify_background_rows_missing_roster_file_is_conservative_alive(
    tmp_path: Path,
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()  # exists, but no roster.json inside it
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}],
        jobs_dir=jobs_dir,
        daemon_dir=daemon_dir,
        stall_after_s=120.0,
        verbose=False,
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.ALIVE


def test_classify_background_rows_skips_row_with_no_usable_id(tmp_path: Path) -> None:
    result = dag_tick.classify_background_rows(
        [{"kind": "background"}],
        jobs_dir=tmp_path,
        daemon_dir=tmp_path,
        stall_after_s=120.0,
        verbose=False,
    )
    assert result.classified == []
    assert result.notes  # anomaly note recorded regardless of --verbose


def test_classify_background_rows_wedged_note_always_prints(tmp_path: Path) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()
    (daemon_dir / "roster.json").write_text(
        json.dumps({"workers": {"abc123": {"pid": os.getpid(), "procStart": "x"}}})
    )
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "active"})
    state_path = jobs_dir / "abc123" / "state.json"
    stale = state_path.stat().st_mtime - 300
    os.utime(state_path, (stale, stale))
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}],
        jobs_dir=jobs_dir,
        daemon_dir=daemon_dir,
        stall_after_s=120.0,
        verbose=False,
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.WEDGED
    assert any("WEDGED abc123" in note for note in result.notes)


# ---------------------------------------------------------------------------
# execute_respawn() / execute_stop() — monkeypatched subprocess only
# ---------------------------------------------------------------------------


class _FakeCompleted:
    """Stand-in for `subprocess.CompletedProcess` in monkeypatched tests."""

    def __init__(self, *, returncode: int, stderr: str = "", stdout: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout


def test_execute_respawn_spawns_when_no_evidence_of_life(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()
    # A READABLE roster naming no worker — real negative evidence, distinct
    # from a missing/unreadable roster file (which is conservative ALIVE and
    # would wrongly skip the respawn this test is checking for).
    (daemon_dir / "roster.json").write_text(json.dumps({"workers": {}}))
    calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)
    line = dag_tick.execute_respawn(
        "abc123", claude_bin="claude", daemon_dir=daemon_dir
    )
    assert calls == [["claude", "respawn", "abc123"]]
    assert "RESPAWN abc123" in line


def test_execute_respawn_crashed_mid_activity_respawns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The watchdog's primary recovery case (#578 respec round 1).

    A process crashes while its last-written state.json still reads
    `tempo:"active"` with in-flight work — a dead process never updates
    that file again. A fresh roster read confirms the pid is dead, so this
    MUST respawn.

    Before this fix, `execute_respawn`'s fresh re-check also read this exact
    state.json and skipped whenever `tempo == "active"` or in-flight counts
    were nonzero — which deadlocked precisely this node, forever, every 60s.
    The state.json below is written to document that shape; the fresh
    re-check is now deliberately PID-liveness only and never reads it —
    that absence of a read is the fix.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()
    (daemon_dir / "roster.json").write_text(json.dumps({"workers": {}}))
    _write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})
    calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)
    line = dag_tick.execute_respawn(
        "abc123", claude_bin="claude", daemon_dir=daemon_dir
    )
    assert calls == [["claude", "respawn", "abc123"]]
    assert "RESPAWN abc123" in line


def test_execute_respawn_skips_when_pid_alive_now(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()
    (daemon_dir / "roster.json").write_text(
        json.dumps({"workers": {"abc123": {"pid": os.getpid()}}})
    )

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "must not spawn when the fresh re-check finds the pid alive"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail)
    line = dag_tick.execute_respawn(
        "abc123", claude_bin="claude", daemon_dir=daemon_dir
    )
    assert "SKIP respawn abc123" in line


def test_execute_stop_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0),
    )
    line = dag_tick.execute_stop("abc123", claude_bin="claude")
    assert line == "dag-tick: STOP abc123 (rc=0)"


def test_execute_stop_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=1, stderr="boom"),
    )
    line = dag_tick.execute_stop("abc123", claude_bin="claude")
    assert "FAILED rc=1" in line
    assert "boom" in line


# ---------------------------------------------------------------------------
# run_tick() — full wiring, subprocess monkeypatched throughout
# ---------------------------------------------------------------------------


def _tick_args(**overrides: object) -> argparse.Namespace:
    base: dict[str, object] = {
        "cwd": None,
        "dry_run": False,
        "claude_bin": "claude",
        "stall_after": 120.0,
        "verbose": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_run_tick_exits_zero_silently_when_lock_is_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lock_path = tmp_path / "dag-tick.lock"
    holder = dag_tick.try_acquire_lock(lock_path)
    assert holder is not None
    monkeypatch.setattr(dag_tick, "LOCK_PATH", lock_path)

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "subprocess must never be touched while the lock is held"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fail)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail)
    try:
        assert dag_tick.run_tick(_tick_args()) == 0
    finally:
        holder.close()


def test_run_tick_skips_when_gate_is_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(dag_tick, "LOCK_PATH", tmp_path / "dag-tick.lock")
    census_called = False

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        nonlocal census_called
        if argv[1] == "agents":
            census_called = True
        return _FakeCompleted(
            returncode=1,
            stderr="'logs' is disabled by CLAUDE_CODE_DISABLE_AGENT_VIEW.",
        )

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    assert dag_tick.run_tick(_tick_args()) == 0
    assert census_called is False


def _fake_run_for_one_dead_node(argv: list[str], **_kwargs: object) -> _FakeCompleted:
    if argv[1] == "logs":
        return _FakeCompleted(returncode=1, stderr="No job matching 'zzbogus'.")
    if argv[1] == "agents":
        census = json.dumps([{"id": "dead1", "kind": "background", "cwd": "/x"}])
        return _FakeCompleted(returncode=0, stdout=census)
    msg = f"unexpected subprocess.run call: {argv}"
    raise AssertionError(msg)


def test_run_tick_dry_run_reports_without_spawning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(dag_tick, "LOCK_PATH", tmp_path / "dag-tick.lock")
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()
    # Real negative evidence — a readable roster naming no worker — so the
    # node classifies DEAD rather than the conservative-ALIVE a missing
    # roster FILE would produce.
    (daemon_dir / "roster.json").write_text(json.dumps({"workers": {}}))
    monkeypatch.setattr(dag_tick, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(dag_tick, "DAEMON_DIR", daemon_dir)
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "idle"})

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "dry-run must never spawn"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)

    assert dag_tick.run_tick(_tick_args(dry_run=True)) == 0
    captured = capsys.readouterr()
    assert "[dry-run] would respawn dead1" in captured.out


def test_run_tick_respawns_a_dead_node(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(dag_tick, "LOCK_PATH", tmp_path / "dag-tick.lock")
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()
    (daemon_dir / "roster.json").write_text(json.dumps({"workers": {}}))
    monkeypatch.setattr(dag_tick, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(dag_tick, "DAEMON_DIR", daemon_dir)
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "idle"})
    popen_calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        popen_calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)

    assert dag_tick.run_tick(_tick_args()) == 0
    assert popen_calls == [["claude", "respawn", "dead1"]]
