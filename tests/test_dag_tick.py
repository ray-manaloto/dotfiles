"""Tests for the launchd watchdog tick (dotfiles_setup.dag_tick, #578).

Pure/table-driven tests cover the terminal predicate, `classify()`,
`strip_respawn_env()`, `gate_status()`, and `plan()` directly — no
subprocess, no filesystem. The census-enrichment and action-execution paths
are exercised against `tmp_path` fixtures with `subprocess` monkeypatched;
none of these tests invoke the real `claude` binary or mutate anything on
this host.

#578 respec round 3 (injection seam, `tests/AGENTS.md` § Mocking): every
test that used to monkeypatch this module's own `LOCK_PATH`/`JOBS_DIR`/
`DAEMON_DIR` globals, or `pid_is_alive`, now constructs a
`dag_tick.TickContext` against `tmp_path` (`_ctx()`) and/or injects a fake
liveness predicate instead — `subprocess` and `os.environ` stay the only
things monkeypatched here, since those are external system boundaries, not
our own module. `_roster()` dedups the repeated mkdir+roster.json fixture
writes.
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
# Shared fixtures
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


def _write_state(jobs_dir: Path, node_id: str, payload: dict[str, object]) -> None:
    job_dir = jobs_dir / node_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "state.json").write_text(json.dumps(payload))


def _roster(tmp_path: Path, workers: dict[str, int]) -> Path:
    """Write a readable `roster.json` under `tmp_path/"daemon"`.

    Names each `node_id -> pid` in `workers` (an empty dict is a readable
    roster naming NO worker — real negative pid evidence, distinct from a
    missing/unreadable roster FILE, which is conservative ALIVE). Returns
    the daemon dir, since every caller needs it for `_ctx()` /
    `classify_background_rows` too. Dedups the ~10 repeated
    mkdir+roster.json writes this file used to carry (#578 respec round 3).
    """
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir(exist_ok=True)
    payload = {"workers": {node_id: {"pid": pid} for node_id, pid in workers.items()}}
    (daemon_dir / "roster.json").write_text(json.dumps(payload))
    return daemon_dir


def _ctx(tmp_path: Path, **overrides: object) -> dag_tick.TickContext:
    """A `TickContext` scoped to `tmp_path`.

    The injection seam (#578 respec round 3) that replaces monkeypatching
    `LOCK_PATH`/`JOBS_DIR`/`DAEMON_DIR` on the module.
    """
    base: dict[str, object] = {
        "claude_bin": "claude",
        "cwd": "/x",
        "jobs_dir": tmp_path / "jobs",
        "daemon_dir": tmp_path / "daemon",
        "lock_path": tmp_path / "dag-tick.lock",
        "stall_after_s": 120.0,
        "max_age_s": dag_tick.DEFAULT_MAX_AGE_SECONDS,
        "dry_run": False,
        "verbose": False,
    }
    base.update(overrides)
    return dag_tick.TickContext(**base)


def _tick_args(**overrides: object) -> argparse.Namespace:
    base: dict[str, object] = {
        "cwd": None,
        "dry_run": False,
        "claude_bin": "claude",
        "stall_after": 120.0,
        "max_age": dag_tick.DEFAULT_MAX_AGE_SECONDS,
        "verbose": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class _FakeCompleted:
    """Stand-in for `subprocess.CompletedProcess` in monkeypatched tests."""

    def __init__(self, *, returncode: int, stderr: str = "", stdout: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout


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
# plan() — the classification -> action table, incl. --max-age (round 3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("node_class", "pid_alive", "state_age_s", "expected_kind"),
    [
        (dag_tick.NodeClass.DEAD, False, 10.0, dag_tick.ActionKind.RESPAWN),
        (dag_tick.NodeClass.DEAD, True, 10.0, dag_tick.ActionKind.RESPAWN),
        (dag_tick.NodeClass.DEAD, False, 999_999.0, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.DEAD, False, None, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.DONE, True, 10.0, dag_tick.ActionKind.STOP),
        (dag_tick.NodeClass.DONE, False, 10.0, None),
        (dag_tick.NodeClass.WEDGED, True, 10.0, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.WEDGED, False, 10.0, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.ALIVE, True, 10.0, None),
        (dag_tick.NodeClass.ALIVE, False, 10.0, None),
    ],
)
def test_plan_maps_classification_to_actions(
    node_class: dag_tick.NodeClass,
    *,
    pid_alive: bool,
    state_age_s: float | None,
    expected_kind: dag_tick.ActionKind | None,
) -> None:
    node = dag_tick.ClassifiedNode(
        "abc123", node_class, pid_alive=pid_alive, state_age_s=state_age_s
    )
    actions = dag_tick.plan([node], max_age_s=100.0)
    if expected_kind is None:
        assert actions == []
    else:
        assert [action.kind for action in actions] == [expected_kind]
        assert actions[0].node_id == "abc123"


def test_plan_is_pure_and_order_preserving() -> None:
    nodes = [
        dag_tick.ClassifiedNode(
            "dead-1", dag_tick.NodeClass.DEAD, pid_alive=False, state_age_s=10.0
        ),
        dag_tick.ClassifiedNode(
            "alive-1", dag_tick.NodeClass.ALIVE, pid_alive=True, state_age_s=10.0
        ),
        dag_tick.ClassifiedNode(
            "done-1", dag_tick.NodeClass.DONE, pid_alive=True, state_age_s=10.0
        ),
    ]
    actions = dag_tick.plan(nodes, max_age_s=100.0)
    assert [a.node_id for a in actions] == ["dead-1", "done-1"]


def test_plan_over_age_dead_reason_names_the_age() -> None:
    node = dag_tick.ClassifiedNode(
        "abc123", dag_tick.NodeClass.DEAD, pid_alive=False, state_age_s=200_000.0
    )
    actions = dag_tick.plan([node], max_age_s=86400.0)
    assert actions[0].kind is dag_tick.ActionKind.LOG
    assert "stale beyond --max-age" in actions[0].reason
    assert "200000s" in actions[0].reason
    assert "not crash recovery" in actions[0].reason


def test_plan_no_age_dead_reason_says_unknown_age() -> None:
    node = dag_tick.ClassifiedNode(
        "abc123", dag_tick.NodeClass.DEAD, pid_alive=False, state_age_s=None
    )
    actions = dag_tick.plan([node], max_age_s=86400.0)
    assert actions[0].kind is dag_tick.ActionKind.LOG
    assert "unknown age" in actions[0].reason


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


def test_try_acquire_lock_does_not_truncate_existing_content(tmp_path: Path) -> None:
    """#578 respec round 2 lock-mode fix.

    Opening in "w" mode truncates on open, before flock is even attempted —
    a second process's `open("w")` would zero another holder's bytes out
    from under it. "a" does not truncate.
    """
    lock_path = tmp_path / "dag-tick.lock"
    lock_path.write_text("PREVIOUS-CONTENT")
    handle = dag_tick.try_acquire_lock(lock_path)
    assert handle is not None
    handle.close()
    assert lock_path.read_text() == "PREVIOUS-CONTENT"


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


def test_background_pid_alive_defaults_to_real_pid_is_alive() -> None:
    alive_roster = {"abc123": dag_tick.RosterWorker(pid=os.getpid(), proc_start=None)}
    dead_roster = {"abc123": dag_tick.RosterWorker(pid=999_999, proc_start=None)}
    assert dag_tick.background_pid_alive("abc123", alive_roster) is True
    assert dag_tick.background_pid_alive("abc123", dead_roster) is False


def test_background_pid_alive_checks_the_injected_predicate() -> None:
    """#578 respec round 3: inject a fake predicate.

    Instead of monkeypatching `dag_tick.pid_is_alive`
    (`tests/AGENTS.md` § Mocking — never mock our own module; inject).
    """

    def _fake_is_alive(pid: int) -> bool:
        return pid == 111

    alive_roster = {"abc123": dag_tick.RosterWorker(pid=111, proc_start=None)}
    dead_roster = {"abc123": dag_tick.RosterWorker(pid=222, proc_start=None)}
    assert (
        dag_tick.background_pid_alive("abc123", alive_roster, is_alive=_fake_is_alive)
        is True
    )
    assert (
        dag_tick.background_pid_alive("abc123", dead_roster, is_alive=_fake_is_alive)
        is False
    )


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


def test_classify_background_rows_missing_state_json_is_conservative_alive(
    tmp_path: Path,
) -> None:
    ctx = _ctx(tmp_path, verbose=True)
    rows: list[dict[str, object]] = [{"id": "ghost", "kind": "background"}]
    result = dag_tick.classify_background_rows(rows, ctx)
    assert result.classified == [
        dag_tick.ClassifiedNode(
            "ghost", dag_tick.NodeClass.ALIVE, pid_alive=True, state_age_s=None
        )
    ]
    assert any("missing/unparseable" in note for note in result.notes)


def test_classify_background_rows_dead_when_no_roster_entry(tmp_path: Path) -> None:
    daemon_dir = _roster(tmp_path, {})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.DEAD
    # A FRESH DEAD node produces no note by itself (not stale, not
    # --verbose) — the stale-DEAD note is covered by its own test below.
    assert result.notes == []


def test_classify_background_rows_missing_roster_file_is_conservative_alive(
    tmp_path: Path,
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()  # exists, but no roster.json inside it
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.ALIVE


def test_classify_background_rows_skips_row_with_no_usable_id(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    result = dag_tick.classify_background_rows([{"kind": "background"}], ctx)
    assert result.classified == []
    assert result.notes  # anomaly note recorded regardless of --verbose


def test_classify_background_rows_wedged_note_always_prints(tmp_path: Path) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "active"})
    state_path = jobs_dir / "abc123" / "state.json"
    stale = state_path.stat().st_mtime - 300
    os.utime(state_path, (stale, stale))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.WEDGED
    assert any("WEDGED abc123" in note for note in result.notes)


def test_classify_background_rows_stale_dead_note_always_prints(
    tmp_path: Path,
) -> None:
    """#578 respec round 3 (--max-age): an over-age DEAD node's note.

    It is unconditional (mirroring WEDGED's), so an operator sees WHY it
    was not respawned even without --verbose.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    state_path = jobs_dir / "abc123" / "state.json"
    ancient = state_path.stat().st_mtime - 100_000  # ~27.8h — over the 24h default
    os.utime(state_path, (ancient, ancient))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.DEAD
    assert any(
        "stale beyond --max-age" in note and "abc123" in note for note in result.notes
    )


# ---------------------------------------------------------------------------
# The crashed-mid-activity case, driven through the real chain (round 3)
# ---------------------------------------------------------------------------


def test_crashed_mid_activity_flows_through_to_respawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The watchdog's primary recovery case.

    #578 respec round 1, reworked round 3 per the cold review's
    inert-fixture finding (probes rule 8). Drives the crash SHAPE through
    the real chain — classify_background_rows -> plan -> execute_respawn —
    instead of writing a state.json that `execute_respawn` cannot read (it
    hasn't since round 1). A process
    crashes while its last-written state.json still reads `tempo:"active"`
    with in-flight work; the roster is readable and names no worker for
    this node (real negative pid evidence). The control-arm test right
    below proves this SAME fixture shape produces a DIFFERENT result when
    the pid IS live.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert len(result.classified) == 1
    classified = result.classified[0]
    assert classified.node_class is dag_tick.NodeClass.DEAD
    assert classified.state_age_s is not None
    assert classified.state_age_s < ctx.max_age_s  # fresh crash, not stale

    actions = dag_tick.plan(result.classified, max_age_s=ctx.max_age_s)
    assert [a.kind for a in actions] == [dag_tick.ActionKind.RESPAWN]

    calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)
    line = dag_tick.execute_respawn(actions[0].node_id, ctx)
    assert calls == [["claude", "respawn", "abc123"]]
    assert "RESPAWN abc123" in line


def test_crashed_mid_activity_control_arm_live_pid_is_alive(tmp_path: Path) -> None:
    """Control arm for the test above.

    Probes rule 8: the fixture must be able to produce the OTHER result.
    Same `tempo:"active"` + in-flight state.json shape, but the roster now
    names a live pid — the node must classify ALIVE, not DEAD, proving the
    fixture actually discriminates.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    _write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.ALIVE


# ---------------------------------------------------------------------------
# gate_preflight() / read_census() — missing binary + distinct failure logs
# ---------------------------------------------------------------------------


def test_gate_preflight_missing_binary_returns_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "run", _raise_missing)
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.gate_preflight(ctx)
    assert result == "unknown"
    assert any("gate preflight" in record.getMessage() for record in caplog.records)


def test_read_census_missing_binary_returns_empty_and_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "run", _raise_missing)
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    assert any(
        "unavailable for census" in record.getMessage() for record in caplog.records
    )


def test_read_census_nonzero_rc_logs_rc_and_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=17, stderr="permission denied"),
    )
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "rc=17" in message and "permission denied" in message for message in messages
    )


def test_read_census_invalid_json_logs_distinct_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0, stdout="{not json"),
    )
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    assert any("not valid JSON" in record.getMessage() for record in caplog.records)


def test_read_census_non_list_top_level_logs_distinct_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0, stdout=json.dumps({"a": 1})),
    )
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    assert any("not a list" in record.getMessage() for record in caplog.records)


def test_read_census_healthy_empty_fleet_is_silent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Control arm for the four failure-log tests above.

    A genuinely empty fleet (rc=0, a real empty JSON array) must produce
    ZERO warnings — this is exactly the case the fix must not turn noisy.
    """
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0, stdout="[]"),
    )
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    assert caplog.records == []


# ---------------------------------------------------------------------------
# execute_respawn() / execute_stop() — monkeypatched subprocess only
# ---------------------------------------------------------------------------


def test_execute_respawn_spawns_when_no_evidence_of_life(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)
    calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)
    line = dag_tick.execute_respawn("abc123", ctx)
    assert calls == [["claude", "respawn", "abc123"]]
    assert "RESPAWN abc123" in line


def test_execute_respawn_skips_when_pid_alive_now(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "must not spawn when the fresh re-check finds the pid alive"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail)
    line = dag_tick.execute_respawn("abc123", ctx)
    assert "SKIP respawn abc123" in line


def test_execute_respawn_missing_binary_returns_skip_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)

    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _raise_missing)
    line = dag_tick.execute_respawn("abc123", ctx)
    assert "SKIP respawn abc123" in line
    assert "claude binary unavailable" in line


def test_execute_stop_reports_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0),
    )
    line = dag_tick.execute_stop("abc123", ctx)
    assert line == "dag-tick: STOP abc123 (rc=0)"


def test_execute_stop_reports_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=1, stderr="boom"),
    )
    line = dag_tick.execute_stop("abc123", ctx)
    assert "FAILED rc=1" in line
    assert "boom" in line


def test_execute_stop_skips_when_pid_already_settled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Stop-side TOCTOU fix (#578 respec round 2).

    Classification can be up to one tick (60s) stale. If the node's pid is
    already gone by the time `execute_stop` runs (settled on its own, or
    reaped by something else), it must SKIP rather than issue a stop against
    a process that no longer exists — which would otherwise log a false
    FAILED line.
    """
    daemon_dir = _roster(tmp_path, {})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "must not issue a stop once the pid has already settled"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fail)
    line = dag_tick.execute_stop("abc123", ctx)
    assert "SKIP stop abc123" in line
    assert "settled" in line


def test_execute_stop_missing_binary_returns_skip_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)

    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "run", _raise_missing)
    line = dag_tick.execute_stop("abc123", ctx)
    assert "SKIP stop abc123" in line
    assert "claude binary unavailable" in line


# ---------------------------------------------------------------------------
# build_tick_context() — the args+defaults -> TickContext mapping
# ---------------------------------------------------------------------------


def test_build_tick_context_maps_args_and_module_defaults() -> None:
    args = _tick_args(
        claude_bin="/x/claude",
        cwd="/some/repo",
        stall_after=5.0,
        max_age=10.0,
        dry_run=True,
        verbose=True,
    )
    ctx = dag_tick.build_tick_context(args)
    assert ctx.claude_bin == "/x/claude"
    assert ctx.cwd == "/some/repo"
    assert ctx.jobs_dir == dag_tick.JOBS_DIR
    assert ctx.daemon_dir == dag_tick.DAEMON_DIR
    assert ctx.lock_path == dag_tick.LOCK_PATH
    assert ctx.stall_after_s == 5.0
    assert ctx.max_age_s == 10.0
    assert ctx.dry_run is True
    assert ctx.verbose is True


def test_build_tick_context_defaults_claude_bin_and_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dag_tick.shutil, "which", lambda _name: None)
    args = _tick_args(claude_bin=None, cwd=None)
    ctx = dag_tick.build_tick_context(args)
    assert ctx.claude_bin == dag_tick.DEFAULT_CLAUDE_BIN
    assert ctx.cwd == str(Path.cwd())


# ---------------------------------------------------------------------------
# execute_tick() — full wiring, subprocess monkeypatched throughout
#
# #578 respec round 3: exercises `execute_tick` directly against a
# `tmp_path`-scoped `TickContext` — zero monkeypatching of `LOCK_PATH`/
# `JOBS_DIR`/`DAEMON_DIR` on this module. `run_tick`'s own args->context
# wiring is covered separately by the `build_tick_context` tests above;
# the CLI's end-to-end truth is the live `--dry-run --verbose` smoke check
# in the verification bundle, which does exercise real host paths.
# ---------------------------------------------------------------------------


def test_execute_tick_exits_zero_silently_when_lock_is_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lock_path = tmp_path / "dag-tick.lock"
    holder = dag_tick.try_acquire_lock(lock_path)
    assert holder is not None
    ctx = _ctx(tmp_path, lock_path=lock_path)

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "subprocess must never be touched while the lock is held"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fail)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail)
    try:
        assert dag_tick.execute_tick(ctx) == 0
    finally:
        holder.close()


def test_execute_tick_skips_when_gate_is_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = _ctx(tmp_path)
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
    assert dag_tick.execute_tick(ctx) == 0
    assert census_called is False


def test_execute_tick_proceeds_when_gate_is_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Gate fail-open (#578 respec round 3).

    "unknown" must PROCEED, not skip — only the documented "off" face
    skips the tick. `read_census` is itself gated and logs its own
    failures, so it is the real gate.
    """
    ctx = _ctx(tmp_path)
    census_called = False

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        nonlocal census_called
        if argv[1] == "logs":
            return _FakeCompleted(returncode=1, stderr="an unrecognized wording")
        if argv[1] == "agents":
            census_called = True
            return _FakeCompleted(returncode=0, stdout="[]")
        msg = f"unexpected subprocess.run call: {argv}"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    with caplog.at_level("WARNING"):
        assert dag_tick.execute_tick(ctx) == 0
    assert census_called is True
    assert any("unknown" in record.getMessage() for record in caplog.records)


def _fake_run_for_one_dead_node(argv: list[str], **_kwargs: object) -> _FakeCompleted:
    if argv[1] == "logs":
        return _FakeCompleted(returncode=1, stderr="No job matching 'zzbogus'.")
    if argv[1] == "agents":
        census = json.dumps([{"id": "dead1", "kind": "background", "cwd": "/x"}])
        return _FakeCompleted(returncode=0, stdout=census)
    msg = f"unexpected subprocess.run call: {argv}"
    raise AssertionError(msg)


def test_execute_tick_dry_run_reports_without_spawning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir, dry_run=True)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "dry-run must never spawn"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)

    assert dag_tick.execute_tick(ctx) == 0
    captured = capsys.readouterr()
    assert "[dry-run] would respawn dead1" in captured.out


def test_execute_tick_respawns_a_dead_node(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    popen_calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        popen_calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)

    assert dag_tick.execute_tick(ctx) == 0
    assert popen_calls == [["claude", "respawn", "dead1"]]


def test_execute_tick_logs_instead_of_respawning_an_over_age_dead_node(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """#578 respec round 3 (--max-age), end to end.

    A DEAD node older than `max_age_s` gets a LOG line, never a respawn —
    and no `Popen` call.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "idle"})
    state_path = jobs_dir / "dead1" / "state.json"
    ancient = state_path.stat().st_mtime - 100_000
    os.utime(state_path, (ancient, ancient))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir, max_age_s=86400.0)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "an over-age DEAD node must never be respawned"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)

    assert dag_tick.execute_tick(ctx) == 0
    captured = capsys.readouterr()
    assert "stale beyond --max-age" in captured.out
    assert "respawn dead1" not in captured.out


def test_execute_tick_stops_a_done_node_with_live_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"done1": os.getpid()})
    _write_state(jobs_dir, "done1", {"state": "done", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    run_calls: list[list[str]] = []

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        if argv[1] == "logs":
            return _FakeCompleted(returncode=1, stderr="No job matching 'zzbogus'.")
        if argv[1] == "agents":
            census = json.dumps([{"id": "done1", "kind": "background", "cwd": "/x"}])
            return _FakeCompleted(returncode=0, stdout=census)
        run_calls.append(argv)
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    assert dag_tick.execute_tick(ctx) == 0
    assert run_calls == [["claude", "stop", "done1"]]
    captured = capsys.readouterr()
    assert "dag-tick: STOP done1 (rc=0)" in captured.out


def test_execute_tick_wedged_node_makes_no_action_subprocess_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"wedged1": os.getpid()})
    _write_state(jobs_dir, "wedged1", {"state": "blocked", "tempo": "active"})
    state_path = jobs_dir / "wedged1" / "state.json"
    stale = state_path.stat().st_mtime - 300
    os.utime(state_path, (stale, stale))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        if argv[1] == "logs":
            return _FakeCompleted(returncode=1, stderr="No job matching 'zzbogus'.")
        if argv[1] == "agents":
            census = json.dumps([{"id": "wedged1", "kind": "background", "cwd": "/x"}])
            return _FakeCompleted(returncode=0, stdout=census)
        msg = f"a WEDGED node must never trigger a claude verb: {argv}"
        raise AssertionError(msg)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "a WEDGED node must never trigger a claude verb"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)
    assert dag_tick.execute_tick(ctx) == 0
    captured = capsys.readouterr()
    assert "WEDGED wedged1" in captured.out
