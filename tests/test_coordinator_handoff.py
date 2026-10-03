# Copyright (c) 2026 Raymond Manaloto
"""Tests for the coordinator auto-handoff judgement (spec §5.1 and §5.4 retire arms)."""

from __future__ import annotations

import fcntl
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, get_args

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import coordinator_handoff as ch
from dotfiles_setup import reap
from dotfiles_setup import session_common as sc
from dotfiles_setup import session_start as ss
from dotfiles_setup.main import setup_parser

SESSION = "abcdef12-0000-4000-8000-000000000001"
OTHER_SESSION = "abcdef12-ffff-4000-8000-000000000002"
COORDINATOR = "dotfiles-20261002T163103.123456789-05.coordinator"
_NS = 1_000_000_000
_LIVE_WAIT_S = 5.0
_ZERO_TASKS = {"tasks": 0}


def _ns(moment: datetime, nanos: int) -> int:
    """Epoch time in ns for a UTC wall time plus a sub-second part."""
    return int(moment.timestamp()) * _NS + nanos


def _job(
    jobs_dir: Path,
    *,
    session_id: str = SESSION,
    name: object = COORDINATOR,
    record_id: str | None = None,
    in_flight: object = _ZERO_TASKS,
) -> None:
    record: dict[str, object] = {
        "sessionId": record_id or session_id,
        "name": name,
        "template": "bg",
    }
    if in_flight is not None:
        record["inFlight"] = in_flight
    path = jobs_dir / session_id[:8] / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def _decide(
    tmp_path: Path, percent: float, env: dict[str, str] | None = None
) -> ch.Decision:
    return ch.decide(
        ch.DecideRequest(SESSION, percent),
        env=env or {},
        jobs_dir=tmp_path / "jobs",
        state_dir=tmp_path / "state",
    )


@pytest.fixture
def coordinator_jobs(tmp_path: Path) -> Path:
    """A jobs dir holding THIS session's record, named as a coordinator."""
    jobs = tmp_path / "jobs"
    _job(jobs)
    return jobs


# ── configuration ────────────────────────────────────────────────────────────


def test_config_defaults_are_30_and_5() -> None:
    """No env: the ratified defaults, no warnings."""
    cfg = ch.load_config({})
    assert (cfg.limit_pct, cfg.step_pct, cfg.warnings) == (30.0, 5.0, ())


def test_config_reads_valid_values() -> None:
    """Valid numbers in (0, 100] are taken as given."""
    cfg = ch.load_config({ch.ENV_LIMIT: "40", ch.ENV_STEP: "2.5"})
    assert (cfg.limit_pct, cfg.step_pct, cfg.warnings) == (40.0, 2.5, ())


@pytest.mark.parametrize("raw", ["abc", "0", "-5", "101", "nan", "inf", "1e400"])
def test_bad_env_values_fall_back_and_warn(raw: str) -> None:
    """Anything outside (0, 100] falls back to the default AND is reported."""
    cfg = ch.load_config({ch.ENV_LIMIT: raw, ch.ENV_STEP: raw})
    assert (cfg.limit_pct, cfg.step_pct) == (30.0, 5.0)
    assert len(cfg.warnings) == 2
    assert all(raw in warning for warning in cfg.warnings)


def test_blank_env_value_is_unset_not_a_warning() -> None:
    """An empty value means "not configured", not "misconfigured"."""
    assert ch.load_config({ch.ENV_LIMIT: "  "}).warnings == ()


# ── levels ───────────────────────────────────────────────────────────────────


def test_next_and_fired_levels() -> None:
    """The limit first, then limit + k*step; float noise never drops a step."""
    cfg = ch.load_config({})
    assert ch.next_level(None, cfg) == 30.0
    assert ch.next_level(30.0, cfg) == 35.0
    assert ch.fired_level(30.0, cfg) == 30.0
    assert ch.fired_level(34.999, cfg) == 30.0
    assert ch.fired_level(35.0, cfg) == 35.0
    assert ch.fired_level(47.0, cfg) == 45.0
    tenths = ch.load_config({ch.ENV_LIMIT: "0.3", ch.ENV_STEP: "0.1"})
    assert ch.fired_level(0.4, tenths) == pytest.approx(0.4)


# ── decide ───────────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("coordinator_jobs")
def test_fires_at_exactly_the_limit_and_not_below(tmp_path: Path) -> None:
    """29.9 is silent, 30.0 fires and records 30."""
    below = _decide(tmp_path, 29.9)
    assert (below.fire, below.reason, below.level) == (False, "below-limit", 30.0)
    at = _decide(tmp_path, 30.0)
    assert (at.fire, at.reason, at.level, at.name) == (True, "fire", 30.0, COORDINATOR)


@pytest.mark.usefixtures("coordinator_jobs")
def test_refires_only_at_the_next_step(tmp_path: Path) -> None:
    """After a 30 fire: 34.9 is silent (next 35), 35.0 fires and records 35."""
    assert _decide(tmp_path, 30.0).fire
    held = _decide(tmp_path, 34.9)
    assert (held.fire, held.reason, held.level) == (False, "below-next-step", 35.0)
    again = _decide(tmp_path, 35.0)
    assert (again.fire, again.level) == (True, 35.0)


@pytest.mark.usefixtures("coordinator_jobs")
def test_a_jump_records_the_highest_level_crossed(tmp_path: Path) -> None:
    """30 → 47 records 45, so the next fire is at 50, not 35/40/45."""
    assert _decide(tmp_path, 30.0).fire
    jump = _decide(tmp_path, 47.0)
    assert (jump.fire, jump.level) == (True, 45.0)
    assert not _decide(tmp_path, 49.9).fire
    assert _decide(tmp_path, 50.0).fire


@pytest.mark.usefixtures("coordinator_jobs")
def test_state_is_persisted_before_the_fire_is_returned(tmp_path: Path) -> None:
    """The fired level is on disk when decide returns, with last_seen."""
    decision = _decide(tmp_path, 31.0)
    state = json.loads((tmp_path / "state" / f"{SESSION}.json").read_text())
    assert decision.fire
    assert state["last_fired"] == 30.0
    assert state["last_seen"]["percent"] == 31.0


def test_last_seen_is_written_even_below_and_for_a_lane(tmp_path: Path) -> None:
    """A reader can tell "never measured" from "measured, below"."""
    _job(tmp_path / "jobs", name="dotfiles-lane.feature")
    decision = _decide(tmp_path, 5.0)
    state = json.loads((tmp_path / "state" / f"{SESSION}.json").read_text())
    assert decision.reason == "not-coordinator"
    assert state["last_seen"]["percent"] == 5.0
    assert "last_fired" not in state


@pytest.mark.parametrize(
    ("name", "record_id"),
    [
        ("dotfiles-lane-g.feature", None),  # a lane-shaped name
        ("kb-20261002T163103.123456789-05.coordinator", None),  # the KB's coordinator
        (COORDINATOR, OTHER_SESSION),  # mismatched sessionId
        (42, None),  # a non-string name
    ],
)
def test_non_coordinators_never_fire_even_at_90(
    tmp_path: Path, name: object, record_id: str | None
) -> None:
    """The role check reads the record and fails closed."""
    _job(tmp_path / "jobs", name=name, record_id=record_id)
    decision = _decide(tmp_path, 90.0)
    assert (decision.fire, decision.reason) == (False, "not-coordinator")


def test_a_missing_or_unreadable_record_never_fires(tmp_path: Path) -> None:
    """No record, or garbage in it, is "not a coordinator"."""
    assert _decide(tmp_path, 90.0).reason == "not-coordinator"
    record = tmp_path / "jobs" / SESSION[:8] / "state.json"
    record.parent.mkdir(parents=True)
    record.write_text("{not json", encoding="utf-8")
    assert _decide(tmp_path, 90.0).reason == "not-coordinator"


@pytest.mark.usefixtures("coordinator_jobs")
def test_bad_env_reaches_the_decision_warnings(tmp_path: Path) -> None:
    """A fallback is never silent: the warning travels to the hook."""
    decision = _decide(tmp_path, 30.0, {ch.ENV_STEP: "abc"})
    assert decision.fire
    assert len(decision.warnings) == 1
    assert ch.ENV_STEP in decision.warnings[0]


@pytest.mark.usefixtures("coordinator_jobs")
def test_a_failed_state_write_never_fires(tmp_path: Path) -> None:
    """No state, no signal: a fire that cannot be recorded is withheld."""
    (tmp_path / "state").write_text("a file where the dir should be", encoding="utf-8")
    decision = _decide(tmp_path, 40.0)
    assert (decision.fire, decision.reason) == (False, "state-write-failed")
    assert any("state write failed" in warning for warning in decision.warnings)


def test_invalid_session_ids_and_percents_are_refused(tmp_path: Path) -> None:
    """A session id becomes a filename; a NaN percent is not a measurement."""
    traversal = ch.decide(
        ch.DecideRequest("../../etc", 90.0),
        env={},
        jobs_dir=tmp_path,
        state_dir=tmp_path,
    )
    assert traversal.reason == "invalid-session-id"
    nan = _decide(tmp_path, float("nan"))
    assert nan.reason == "invalid-percent"
    assert not (tmp_path / "state").exists()


def test_decision_json_shape() -> None:
    """The hook's parseDecision depends on exactly these keys and types."""
    decision = ch.Decision(
        fire=True,
        reason="fire",
        level=30.0,
        session_id=SESSION,
        name=COORDINATOR,
        percent=30.0,
        warnings=("w",),
    )
    assert json.loads(decision.to_json()) == {
        "fire": True,
        "reason": "fire",
        "level": 30.0,
        "session_id": SESSION,
        "name": COORDINATOR,
        "percent": 30.0,
        "warnings": ["w"],
    }


# ── names ────────────────────────────────────────────────────────────────────


def test_successor_name_golden_in_cdt() -> None:
    """16:31:03 CDT is 21:31:03 UTC; the offset is -05."""
    now = _ns(datetime(2026, 10, 2, 21, 31, 3, tzinfo=UTC), 123_456_789)
    assert ch.successor_name(now) == COORDINATOR


def test_successor_name_golden_in_cst() -> None:
    """09:05:07 CST is 15:05:07 UTC; the offset is -06; ns keep 9 digits."""
    now = _ns(datetime(2026, 1, 15, 15, 5, 7, tzinfo=UTC), 42)
    assert ch.successor_name(now) == "dotfiles-20260115T090507.000000042-06.coordinator"


def test_stamped_name_takes_a_project_and_a_feature() -> None:
    """One formatter for both mods (§8)."""
    now = _ns(datetime(2026, 10, 2, 21, 31, 3, tzinfo=UTC), 123_456_789)
    assert ch.stamped_name("kb", "lane-x", now) == (
        "kb-20261002T163103.123456789-05.lane-x"
    )


def test_legacy_names_sort_after_new_ones() -> None:
    """P6: lexical order is NOT recency — the reason no lookup sorts names."""
    legacy = "dotfiles-20261002b.coordinator"
    assert max(COORDINATOR, legacy) == legacy


def test_session_name_requires_the_matching_record(tmp_path: Path) -> None:
    """The name comes back only when ``sessionId`` matches exactly."""
    _job(tmp_path, name=COORDINATOR)
    assert ch.session_name(SESSION, tmp_path) == COORDINATOR
    assert ch.session_name(OTHER_SESSION, tmp_path) is None
    assert ch.session_name("nope", tmp_path) is None


# ── queued questions ─────────────────────────────────────────────────────────


def test_queued_questions_section_is_extracted_to_the_next_h2() -> None:
    """The body, sub-headings included, up to the next level-2 heading."""
    text = (
        "# Handoff\n\n## Queued questions\n\n### Q1\n1. Pick A (Recommended)\n"
        "PRO: x CON: y `a.md`\n\n## Gotchas\n- g\n"
    )
    assert ch.queued_questions(text) == (
        "### Q1\n1. Pick A (Recommended)\nPRO: x CON: y `a.md`"
    )


@pytest.mark.parametrize(
    "text", ["# Handoff\n\n## Gotchas\n- g\n", "## Queued questions\n\n## Next\n"]
)
def test_absent_or_empty_queued_questions_is_none(text: str) -> None:
    """No section, or an empty one, is None — the brief then says so."""
    assert ch.queued_questions(text) is None


# ── census ───────────────────────────────────────────────────────────────────


def _proc(pid: int, ppid: int, command: str) -> reap.Process:
    return reap.Process(pid=pid, ppid=ppid, age_s=60, state="S", command=command)


TREE = (
    _proc(1, 0, "/sbin/launchd"),
    _proc(100, 1, "/Users/x/.local/bin/claude --bg"),
    _proc(200, 100, "/bin/zsh -c mise run coordinator-handoff -- launch"),
    _proc(
        201, 200, "uv run --project python dotfiles-setup coordinator-handoff launch"
    ),
    _proc(300, 100, "/bin/zsh -c mise run ship > logs/ship.log 2>&1"),
    _proc(301, 300, "mise run ship"),
    _proc(302, 301, "uv run --project python dotfiles-setup pr ship"),
    _proc(400, 100, "/bin/zsh -c cat .agent/plans/main-checkout-ship-queue.md"),
    _proc(500, 100, "mise run land -- 1571"),
    _proc(900, 1, "mise run sync"),
)


def test_census_records_outermost_heavy_runs_under_the_session_root() -> None:
    """One entry per logical run, its log; never the caller or an outsider."""
    runs = ch.census(TREE, self_pid=201, runner=_Recorder(0))
    assert runs == (
        ch.HeavyRun(
            300, "/bin/zsh -c mise run ship > logs/ship.log 2>&1", "logs/ship.log"
        ),
        ch.HeavyRun(500, "mise run land -- 1571", None),
    )


def test_census_without_a_claude_ancestor_refuses() -> None:
    """An empty census would read as "nothing live" — so no root raises."""
    with pytest.raises(ch.CoordinatorHandoffError):
        ch.census(TREE, self_pid=900)


@pytest.mark.parametrize(
    "command",
    [
        "mise run ship",
        "mise run verify-local",
        "mise run bounded-wait -- --deadline 60 --file x",
        "mise run kb-land -- 9",
        "sh -c 'mise run land -- 5'",
        "uv run --project python dotfiles-setup pr land 5",
        "uv run kb-setup ship",
    ],
)
def test_heavy_regex_matches_every_heavy_run(command: str) -> None:
    """Each named long operation, as a task or as its python entrypoint."""
    assert ch.HEAVY_COMMAND_RE.search(command)


@pytest.mark.parametrize(
    "command",
    [
        "cat .agent/plans/main-checkout-ship-queue.md",
        "mise run shipit",
        "mise run lint",
        "mise run sync-full",
        "dotfiles-setup coordinator-handoff launch",
    ],
)
def test_heavy_regex_ignores_lookalikes(command: str) -> None:
    """The control arm: near-misses are not heavy runs."""
    assert ch.HEAVY_COMMAND_RE.search(command) is None


# ── launch ───────────────────────────────────────────────────────────────────


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def checkouts(tmp_path: Path) -> tuple[Path, Path]:
    """A real main checkout and one linked worktree of it."""
    main = tmp_path / "main"
    main.mkdir()
    _git("init", "-q", "-b", "main", cwd=main)
    _git("commit", "-q", "--allow-empty", "-m", "root", cwd=main)
    lane = tmp_path / "lane"
    _git("worktree", "add", "-q", "-b", "lane", str(lane), cwd=main)
    return main.resolve(), lane


@pytest.fixture
def handoff(tmp_path: Path) -> Path:
    """A tracked-handoff stand-in with one queued question."""
    path = tmp_path / "session-2026-10-02c.md"
    path.write_text(
        "# Handoff\n\n## Queued questions\n\n1. Keep X? (Recommended: yes)\n",
        encoding="utf-8",
    )
    return path


class _Recorder:
    def __init__(self, rc: int) -> None:
        self.rc = rc
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(
        self, argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if argv[0] == "git":
            assert kwargs["timeout"] == sc.MAIN_CHECKOUT_TIMEOUT_S
            return subprocess.run(
                argv,
                capture_output=True,
                text=True,
                check=False,
                timeout=sc.MAIN_CHECKOUT_TIMEOUT_S,
            )
        if argv[0] == "lsof":
            return subprocess.CompletedProcess(argv, 1, "", "")
        self.calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, self.rc)


def _deps(
    tmp_path: Path,
    cwd: Path,
    lines: list[str],
    *,
    runner: _Recorder,
    self_pid: int = 201,
) -> ch.LaunchDeps:
    return ch.LaunchDeps(
        state_dir=tmp_path / "state",
        jobs_dir=tmp_path / "jobs",
        projects_dir=tmp_path / "projects",
        cwd=cwd,
        processes=TREE,
        self_pid=self_pid,
        now_ns=_ns(datetime(2026, 10, 2, 21, 31, 3, tzinfo=UTC), 7),
        runner=runner,
        out=lines.append,
    )


@pytest.mark.usefixtures("coordinator_jobs")
def test_launch_dry_run_prints_argv_from_the_main_checkout(
    tmp_path: Path, checkouts: tuple[Path, Path], handoff: Path
) -> None:
    """Dry run: argv + cwd = the main checkout, nothing recorded or executed."""
    main, lane = checkouts
    runner = _Recorder(0)
    transcript = tmp_path / "projects" / "-slug" / f"{SESSION}.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text("{}\n", encoding="utf-8")
    lines: list[str] = []
    deps = _deps(tmp_path, lane, lines, runner=runner)

    assert ch.launch(handoff, SESSION, dry_run=True, deps=deps) == 0

    output = "".join(lines)
    argv = json.loads(output.split("\n", 1)[0].removeprefix("argv: "))
    assert argv[:6] == [
        "claude",
        "--bg",
        "-n",
        "dotfiles-20261002T163103.000000007-05.coordinator",
        "--settings",
        '{"crossSessionInbound":"accept"}',
    ]
    assert f"cwd: {main}\n" in output
    brief = argv[6]
    assert str(transcript) in brief
    assert str(handoff.resolve()) in brief
    assert str(main / ".agent/plans/main-checkout-ship-queue.md") in brief
    assert "pid 300: /bin/zsh -c mise run ship > logs/ship.log 2>&1" in brief
    assert "(log: logs/ship.log)" in brief
    assert "Keep X? (Recommended: yes)" in brief
    assert "never by sorting names" in brief
    assert "Ask Ray ONLY for human-intervention items" in brief
    assert str(main / ".agent/plans/handoff-inbox") in brief
    assert "HOST SLOT" in brief
    assert '"anything else?"' in brief
    assert "--accept-inflight" in brief
    assert "DRY RUN" in output
    assert runner.calls == []
    assert not (tmp_path / "state" / f"{SESSION}.json").exists()


@pytest.mark.usefixtures("coordinator_jobs")
def test_launch_records_the_census_then_runs_claude(
    tmp_path: Path, checkouts: tuple[Path, Path], handoff: Path
) -> None:
    """State before signal; the rc is claude's."""
    main, lane = checkouts
    runner = _Recorder(7)
    deps = _deps(tmp_path, lane, [], runner=runner)
    assert ch.launch(handoff, SESSION, dry_run=False, deps=deps) == 7
    argv, kwargs = runner.calls[0]
    assert argv[:2] == ["claude", "--bg"]
    assert kwargs["cwd"] == main
    state = json.loads((tmp_path / "state" / f"{SESSION}.json").read_text())
    assert [run["pid"] for run in state["census"]] == [300, 500]
    assert state["launch"]["successor"] == argv[3]


def test_launch_refuses_a_non_coordinator(
    tmp_path: Path, checkouts: tuple[Path, Path], handoff: Path
) -> None:
    """A lane-named session never launches a successor."""
    _job(tmp_path / "jobs", name="dotfiles-lane.feature")
    runner = _Recorder(0)
    deps = _deps(tmp_path, checkouts[1], [], runner=runner)
    assert ch.launch(handoff, SESSION, dry_run=False, deps=deps) == 2
    assert runner.calls == []


@pytest.mark.usefixtures("coordinator_jobs")
def test_launch_refuses_a_missing_handoff_or_a_blind_census(
    tmp_path: Path, checkouts: tuple[Path, Path], handoff: Path
) -> None:
    """No handoff, or no claude ancestor to census from: rc 2, nothing runs."""
    runner = _Recorder(0)
    missing = _deps(tmp_path, checkouts[1], [], runner=runner)
    assert ch.launch(tmp_path / "absent.md", SESSION, dry_run=False, deps=missing) == 2
    blind = _deps(tmp_path, checkouts[1], [], runner=runner, self_pid=900)
    assert ch.launch(handoff, SESSION, dry_run=False, deps=blind) == 2
    assert runner.calls == []


# ── retire ───────────────────────────────────────────────────────────────────


def _record_launch(state_dir: Path, runs: tuple[ch.HeavyRun, ...]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / f"{SESSION}.json").write_text(
        json.dumps(
            {
                "launch": {"at": "now", "successor": "s"},
                "census": [
                    {"pid": run.pid, "argv": run.argv, "log_path": run.log_path}
                    for run in runs
                ],
            }
        ),
        encoding="utf-8",
    )


def _retire(
    tmp_path: Path,
    processes: tuple[reap.Process, ...],
    request: ch.RetireRequest | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> int:
    return ch.retire(
        request or ch.RetireRequest(old_session_id=SESSION, dry_run=True),
        ch.RetireDeps(
            jobs_dir=tmp_path / "jobs",
            state_dir=tmp_path / "state",
            processes=processes,
            runner=runner,
        ),
    )


def _wait_for(predicate: Callable[[], bool]) -> None:
    deadline = time.monotonic() + _LIVE_WAIT_S
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    msg = "condition not reached within the bound"
    raise AssertionError(msg)


def _own_runs(pid: int) -> tuple[ch.HeavyRun, ...]:
    """This test process's heavy descendants with ``pid`` — the real census."""
    me = os.getpid()
    runs = ch.census(reap.snapshot(), self_pid=me, root_pid=me)
    return tuple(run for run in runs if run.pid == pid)


@pytest.mark.usefixtures("coordinator_jobs")
def test_retire_blocks_on_a_live_recorded_run_until_it_exits(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Real processes: a live heavy child blocks (rc 1, named); dead, rc 0."""
    log = tmp_path / "ship.log"
    child = subprocess.Popen(
        ["/bin/sh", "-c", f"sleep 30 > {log}; : mise run ship"],
        start_new_session=True,
    )
    try:
        _wait_for(lambda: bool(_own_runs(child.pid)))
        recorded = _own_runs(child.pid)
        assert recorded[0].log_path == str(log)
        _record_launch(tmp_path / "state", recorded)

        with caplog.at_level(logging.INFO):
            assert _retire(tmp_path, reap.snapshot()) == 1
        assert f"pid {child.pid}" in caplog.text
        assert str(log) in caplog.text
        assert (
            _retire(
                tmp_path,
                reap.snapshot(),
                ch.RetireRequest(SESSION, adopted=frozenset({child.pid}), dry_run=True),
            )
            == 0
        )
    finally:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()
    _wait_for(lambda: all(p.pid != child.pid for p in reap.snapshot()))
    assert _retire(tmp_path, reap.snapshot()) == 0


@pytest.mark.usefixtures("coordinator_jobs")
def test_retire_ignores_a_pid_reused_by_another_command(tmp_path: Path) -> None:
    """Same pid, different argv: not the recorded run, so it never blocks."""
    _record_launch(tmp_path / "state", (ch.HeavyRun(4242, "mise run ship", None),))
    assert _retire(tmp_path, (_proc(4242, 1, "vim notes.md"),)) == 0
    assert _retire(tmp_path, (_proc(4242, 1, "mise run ship"),)) == 1


@pytest.mark.parametrize(
    "case",
    [
        ({"tasks": 2}, False, 1),  # blocks on its own, census empty
        ({"tasks": 2}, True, 0),  # --accept-inflight overrides, deliberately
        ({"tasks": 0}, False, 0),
        ("garbage", False, 1),  # Unknown harness state blocks independently.
    ],
)
def test_in_flight_tasks_block_independently(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    case: tuple[object, bool, int],
) -> None:
    """Requirements item 16: in-flight harness tasks block with no live run."""
    in_flight, accept, rc = case
    _job(tmp_path / "jobs", in_flight=in_flight)
    _record_launch(tmp_path / "state", ())
    with caplog.at_level(logging.INFO):
        assert (
            _retire(
                tmp_path,
                (),
                ch.RetireRequest(SESSION, dry_run=True, accept_inflight=accept),
            )
            == rc
        )
    if in_flight == "garbage":
        assert "inFlight unknown" in caplog.text
    if accept:
        assert "--accept-inflight given" in caplog.text


def test_retire_refuses_a_non_coordinator_or_a_missing_launch(tmp_path: Path) -> None:
    """Exit 2 for a lane, and for a coordinator that never recorded a launch."""
    _job(tmp_path / "jobs", name="dotfiles-lane.feature")
    _record_launch(tmp_path / "state", ())
    assert _retire(tmp_path, ()) == 2
    _job(tmp_path / "jobs")
    (tmp_path / "state" / f"{SESSION}.json").unlink()
    assert _retire(tmp_path, ()) == 2


@pytest.mark.usefixtures("coordinator_jobs")
def test_retire_runs_claude_stop_with_the_short_id(tmp_path: Path) -> None:
    """Clear: `claude stop <id[:8]>`, and its rc is the answer."""
    _record_launch(tmp_path / "state", ())
    runner = _Recorder(3)
    assert _retire(tmp_path, (), ch.RetireRequest(SESSION), runner) == 3
    assert runner.calls[0][0] == ["claude", "stop", SESSION[:8]]


# ── CLI ──────────────────────────────────────────────────────────────────────


def test_cli_decide_prints_one_json_decision(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The hook's exact argv parses and answers JSON with rc 0."""
    _job(tmp_path / "jobs")
    args = setup_parser().parse_args(
        [
            "coordinator-handoff",
            "decide",
            "--session-id",
            SESSION,
            "--percent",
            "30",
            "--jobs-dir",
            str(tmp_path / "jobs"),
            "--state-dir",
            str(tmp_path / "state"),
        ]
    )
    assert ch.main(args, tmp_path) == 0
    assert json.loads(capsys.readouterr().out)["fire"] is True


def test_cli_name_prints_a_conforming_coordinator_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`name` emits the convention the session-start mod keeps."""
    args = setup_parser().parse_args(["coordinator-handoff", "name"])
    assert ch.main(args, tmp_path) == 0
    name = capsys.readouterr().out.strip()
    assert ch.COORDINATOR_NAME_RE.fullmatch(name)
    assert name.startswith("dotfiles-")


def test_cli_retire_parses_adopted_and_accept_inflight() -> None:
    """The successor's documented retire invocation parses."""
    args = setup_parser().parse_args(
        [
            "coordinator-handoff",
            "retire",
            "--old-session",
            SESSION,
            "--adopted",
            "11",
            "12",
            "--accept-inflight",
            "--dry-run",
        ]
    )
    assert (args.adopted, args.accept_inflight, args.dry_run) == ([11, 12], True, True)


def test_cli_name_emits_lane_names_in_the_same_convention(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """parallel-work-split prints lane names with the one shared formatter."""
    args = setup_parser().parse_args(
        ["coordinator-handoff", "name", "--project", "kb", "--feature", "lane-x"]
    )
    assert ch.main(args, tmp_path) == 0
    name = capsys.readouterr().out.strip()
    assert name.startswith("kb-")
    assert name.endswith(".lane-x")
    assert not ch.COORDINATOR_NAME_RE.fullmatch(name)


@pytest.mark.usefixtures("coordinator_jobs")
def test_r1_launched_session_never_fires_or_launches_a_second_successor(
    tmp_path: Path,
    checkouts: tuple[Path, Path],
    handoff: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A successful launch survives later measurements and duplicate launch attempts."""
    runner = _Recorder(0)
    deps = _deps(tmp_path, checkouts[1], [], runner=runner)
    assert ch.launch(handoff, SESSION, dry_run=False, deps=deps) == 0
    state_path = tmp_path / "state" / f"{SESSION}.json"
    launched = json.loads(state_path.read_text())
    decision = _decide(tmp_path, 90)
    assert (decision.fire, decision.reason) == (False, "already-launched")
    assert ch.launch(handoff, SESSION, dry_run=False, deps=deps) == 2
    assert f"already launched {launched['launch']['successor']}" in caplog.text
    assert len(runner.calls) == 1
    assert json.loads(state_path.read_text())["launch"] == launched["launch"]


@pytest.mark.usefixtures("coordinator_jobs")
def test_r2_worktree_decide_launch_and_main_retire_share_state(
    tmp_path: Path,
    checkouts: tuple[Path, Path],
    handoff: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The package-root argument cannot redirect state into another checkout."""
    main, lane = checkouts
    monkeypatch.chdir(lane)
    parser = setup_parser()
    args = parser.parse_args(
        [
            "coordinator-handoff",
            "decide",
            "--session-id",
            SESSION,
            "--percent",
            "30",
            "--jobs-dir",
            str(tmp_path / "jobs"),
        ]
    )
    assert ch.main(args, tmp_path / "foreign-package") == 0
    assert json.loads(capsys.readouterr().out)["fire"]
    state_dir = main / ch.STATE_SUBDIR
    assert (state_dir / f"{SESSION}.json").is_file()
    lines: list[str] = []
    deps = ch.LaunchDeps(
        cwd=lane,
        jobs_dir=tmp_path / "jobs",
        processes=TREE,
        self_pid=201,
        runner=_Recorder(0),
        out=lines.append,
    )
    assert ch.launch(handoff, SESSION, dry_run=False, deps=deps) == 0
    assert f"--state-dir {state_dir}" in "".join(lines)
    assert not (lane / ch.STATE_SUBDIR).exists()
    monkeypatch.chdir(main)
    retire_args = parser.parse_args(
        [
            "coordinator-handoff",
            "retire",
            "--old-session",
            SESSION,
            "--dry-run",
            "--jobs-dir",
            str(tmp_path / "jobs"),
        ]
    )
    assert ch.main(retire_args, tmp_path / "foreign-package") == 0


@pytest.mark.usefixtures("coordinator_jobs")
def test_r3_preview_and_release_do_not_spend_undelivered_levels(tmp_path: Path) -> None:
    """Preview is repeatable; release restores the previous committed threshold."""
    for _ in range(2):
        preview = ch.decide(
            ch.DecideRequest(SESSION, 30, no_commit=True),
            env={},
            jobs_dir=tmp_path / "jobs",
            state_dir=tmp_path / "state",
        )
        assert (preview.fire, preview.level) == (True, 30)
    path = tmp_path / "state" / f"{SESSION}.json"
    assert "last_fired" not in json.loads(path.read_text())
    assert _decide(tmp_path, 30).fire
    assert ch.release(SESSION, 30, state_dir=tmp_path / "state") == 0
    assert _decide(tmp_path, 30).fire
    assert _decide(tmp_path, 45).fire
    assert ch.release(SESSION, 30, state_dir=tmp_path / "state") == 0
    assert json.loads(path.read_text())["last_fired"] == 45
    assert ch.release(SESSION, 45, state_dir=tmp_path / "state") == 0
    assert json.loads(path.read_text())["last_fired"] == 30
    _record_launch(tmp_path / "state", ())
    launched = json.loads(path.read_text())
    launched.update({"last_fired": 30, "previous_fired": None})
    path.write_text(json.dumps(launched), encoding="utf-8")
    before = path.read_bytes()
    assert ch.release(SESSION, 30, state_dir=tmp_path / "state") == 0
    assert path.read_bytes() == before


@pytest.mark.usefixtures("coordinator_jobs")
def test_r5_decide_respects_an_external_lock_and_reports_the_bound(
    tmp_path: Path,
) -> None:
    """A real OS flock keeps a fire from bypassing another writer's transaction."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    with (state_dir / f"{SESSION}.json.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = time.monotonic()
        decision = _decide(tmp_path, 30)
        elapsed = time.monotonic() - started
    assert (decision.fire, decision.reason) == (False, "state-locked")
    assert sc.STATE_LOCK_TIMEOUT_S <= elapsed < sc.STATE_LOCK_TIMEOUT_S + 5
    assert not (state_dir / f"{SESSION}.json").exists()


@pytest.mark.parametrize("operation", ["release", "launch", "renamed"])
@pytest.mark.usefixtures("coordinator_jobs")
def test_r5_all_other_state_mutators_honor_an_external_lock(
    tmp_path: Path,
    checkouts: tuple[Path, Path],
    handoff: Path,
    caplog: pytest.LogCaptureFixture,
    operation: str,
) -> None:
    """Release, launch and confirmed naming cannot bypass a held transaction."""
    assert _decide(tmp_path, 30).fire
    path = tmp_path / "state" / f"{SESSION}.json"
    state = json.loads(path.read_text())
    state["action"] = "defer"
    path.write_text(json.dumps(state), encoding="utf-8")
    before = path.read_bytes()
    with path.with_suffix(".json.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if operation == "release":
            rc = ch.release(SESSION, 30, state_dir=tmp_path / "state")
        elif operation == "launch":
            rc = ch.launch(
                handoff,
                SESSION,
                dry_run=True,
                deps=_deps(tmp_path, checkouts[1], [], runner=_Recorder(0)),
            )
        else:
            rc = ss.mark_renamed(SESSION, "confirmed", tmp_path / "state")
    assert rc == (1 if operation == "renamed" else 2)
    assert "state-locked" in caplog.text
    assert path.read_bytes() == before


@pytest.mark.parametrize("failure", ["missing", "timeout", "nonzero"])
@pytest.mark.usefixtures("coordinator_jobs")
def test_r6_stop_failure_is_code_3_with_a_60_second_bound(
    tmp_path: Path,
    failure: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An operational stop failure is never confused with a live-work blocker."""
    _record_launch(tmp_path / "state", ())

    def failing_stop(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert argv == ["claude", "stop", SESSION[:8]]
        assert kwargs["timeout"] == 60
        if failure == "missing":
            msg = "claude missing"
            raise FileNotFoundError(msg)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, 60)
        return subprocess.CompletedProcess(argv, 7)

    assert _retire(tmp_path, (), ch.RetireRequest(SESSION), failing_stop) == 3
    assert (
        "stop failed" if failure != "nonzero" else "claude stop rc 7"
    ) in caplog.text


@pytest.mark.parametrize(
    "case",
    [
        ("git", "missing"),
        ("git", "timeout"),
        ("git", "nonzero"),
        ("ps", "missing"),
        ("ps", "timeout"),
        ("ps", "nonzero"),
    ],
)
@pytest.mark.usefixtures("coordinator_jobs")
def test_r6_launch_git_and_ps_failures_refuse_with_code_2(
    tmp_path: Path,
    checkouts: tuple[Path, Path],
    handoff: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, str],
) -> None:
    """Boundary failures never escape as tracebacks with an ambiguous code 1."""
    real_run = subprocess.run
    route, failure = case

    def failed_probe(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if argv[0] != route:
            return real_run(
                argv, capture_output=True, text=True, check=False, timeout=30
            )
        assert "timeout" in kwargs
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, 30)
        if failure == "missing":
            raise FileNotFoundError(route)
        return subprocess.CompletedProcess(argv, 4, "", "probe failed")

    monkeypatch.setattr(subprocess, "run", failed_probe)
    deps = ch.LaunchDeps(
        state_dir=tmp_path / "state",
        jobs_dir=tmp_path / "jobs",
        cwd=checkouts[1],
    )
    assert ch.launch(handoff, SESSION, dry_run=True, deps=deps) == 2


@pytest.mark.parametrize(
    "in_flight", [None, "bad", {}, {"tasks": "0"}, {"tasks": True}, {"tasks": -1}]
)
def test_r7_unknown_inflight_blocks_unless_explicitly_accepted(
    tmp_path: Path,
    in_flight: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Every unknown-schema arm blocks even an empty census."""
    _job(tmp_path / "jobs", in_flight=in_flight)
    _record_launch(tmp_path / "state", ())
    assert _retire(tmp_path, ()) == 1
    assert "inFlight unknown" in caplog.text
    assert (
        _retire(
            tmp_path, (), ch.RetireRequest(SESSION, dry_run=True, accept_inflight=True)
        )
        == 0
    )


@pytest.mark.parametrize(
    "form",
    [
        "mise run {task}",
        "mise -C /tmp/repo run {task}",
        "mise run -- {task}",
        'mise -C "/tmp/repo space" run -- {task}',
    ],
)
@pytest.mark.parametrize(
    "task",
    [
        "dev-rebuild",
        "up",
        "persistence",
        "gate",
        "lock-image",
        "lock-shared",
        "kb-ship",
        "kb-land",
        "ship",
        "land",
        "sync",
        "verify-local",
        "verify-container-latest",
        "bounded-wait",
        "automerge",
    ],
)
def test_r8_all_heavy_task_and_mise_forms_are_in_the_census(
    form: str, task: str
) -> None:
    """Table-driven coverage includes the long operations the baseline omitted."""
    command = form.format(task=task)
    assert ch.HEAVY_COMMAND_RE.search(command)
    assert (
        ch.HEAVY_COMMAND_RE.search(command.replace(task, task + "-lookalike")) is None
    )


@pytest.mark.parametrize("owner", [300, 301])
def test_r9_fd1_real_file_wins_over_unexpanded_redirect(
    tmp_path: Path, owner: int
) -> None:
    """Native lsof resolves the heavy process's stdout or its first descendant's."""
    log = tmp_path / "actual log.txt"
    log.touch()
    calls: list[list[str]] = []

    def lsof(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert kwargs["timeout"] == 10
        pid = int(argv[3])
        return subprocess.CompletedProcess(
            argv, 0, f"p{pid}\nf1\nn{log}\n" if pid == owner else "", ""
        )

    tree = (
        *TREE[:4],
        _proc(300, 100, 'zsh -c mise run ship > "$LOG"'),
        _proc(301, 300, "mise run ship"),
    )
    runs = ch.census(tree, self_pid=201, runner=lsof)
    assert runs == (ch.HeavyRun(300, 'zsh -c mise run ship > "$LOG"', str(log)),)
    assert calls[0] == ["lsof", "-a", "-p", "300", "-d", "1", "-Fn"]


def test_r9_unresolved_variable_log_is_marked_and_never_a_wait_target() -> None:
    """A missing/pipe/directory fd has only a clearly labelled redirect fallback."""
    tree = (*TREE[:4], _proc(300, 100, 'zsh -c mise run ship > "$LOG"'))
    runs = ch.census(tree, self_pid=201, runner=_Recorder(0))
    assert runs[0].log_path == "unexpanded:$LOG"


def test_r9_quoted_fallback_keeps_spaces_and_marks_variables() -> None:
    """A fallback stays usable or explicitly unresolved, including quoted spaces."""
    tree = (
        *TREE[:4],
        _proc(300, 100, 'zsh -c mise run ship > "$LOG/ship run.txt"'),
        _proc(400, 100, 'zsh -c mise run land > "logs/land run.txt"'),
    )
    runs = ch.census(tree, self_pid=201, runner=_Recorder(0))
    assert [run.log_path for run in runs] == [
        "unexpanded:$LOG/ship run.txt",
        "logs/land run.txt",
    ]


def test_r13_session_helpers_have_one_owner_and_typed_wire_vocabulary() -> None:
    """The independent session-start module uses the common formatter and lock."""
    assert ss.stamped_name is sc.stamped_name
    assert ss.stamped_name.__module__ == "dotfiles_setup.session_common"
    assert ch.main_checkout.__module__ == "dotfiles_setup.session_common"
    assert sc.valid_session_id(SESSION)
    assert not sc.valid_session_id("../escape")
    assert "already-launched" in get_args(ch.DecisionReason.__value__)
    assert "unknown" in get_args(ss.StartAction.__value__)


def test_r14_unattended_docs_require_an_early_docs_branch_pr() -> None:
    """The handoff entrypoint itself carries requirement 8, not just its caller."""
    text = (
        Path(__file__).parent.parent / ".claude/skills/session-handoff/SKILL.md"
    ).read_text()
    unattended = text.split("## Unattended run", 1)[1].split("## 1.", 1)[0]
    assert "docs branch" in unattended
    assert "PR early" in unattended
    assert "ssh keepalive" in unattended
