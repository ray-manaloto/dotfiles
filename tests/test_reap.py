# Copyright (c) 2026 Raymond Manaloto
"""Tests for the ancestor-protected process reaper (#653).

The module is destructive, so the tests are written around the four ways it
could destroy the wrong thing rather than around its happy path: an ancestor
chain that is not excluded (it kills the shell that ran it), an age floor that
does not hold (it kills live work), a pattern that matches more than it names,
and a PID that was recycled between the plan and the signal.

Every arm is paired. The protection tests assert both that the protected PID is
spared AND that an unprotected sibling with the identical command IS selected —
without the second half, a `select()` that returned nothing at all would pass.

`ps` output is injected as real observed text (macOS `ps -eo
pid=,ppid=,etime=,stat=,args=`, including the padded columns and the
`DD-HH:MM:SS` form), and no test signals a real process: `killer` is a
parameter, so the TERM-then-KILL escalation is driven end to end against a
recorded call list.
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import reap

# Real shapes, transcribed from `ps -eo pid=,ppid=,etime=,stat=,args=` on the
# authoring host — padded PID column, three etime formats, argv with spaces.
PS_SAMPLE = """\
    1     0 05-10:54:57 Ss   /sbin/launchd
  500     1    35:02:11 S    /usr/sbin/distnoted agent
 6001   500       02:30 S    /Users/x/.local/share/mise/shims/git rev-parse
 6002  6001 01-10:00:00 S    fnox export --format json
 6003     1 01-10:00:05 S    fnox export --format json
 6004     1          09 S    fnox export --format json
"""


def _table() -> tuple[reap.Process, ...]:
    return reap.parse_processes(PS_SAMPLE)


def _runner(output: str = PS_SAMPLE) -> Callable[[Sequence[str]], str]:
    def run(_command: Sequence[str]) -> str:
        return output

    return run


# --------------------------------------------------------------------------- #
# etime parsing — the age floor is only as good as this
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("09", 9),
        ("02:30", 150),
        ("35:02:11", 126131),
        ("01-10:00:00", 122400),
        ("05-10:54:57", 471297),
    ],
)
def test_every_ps_elapsed_format_parses_to_seconds(text: str, expected: int) -> None:
    assert reap.parse_etime(text) == expected


@pytest.mark.parametrize("text", ["", "  ", "abc", "1:2:3:4", "x-01:00", "01:xx"])
def test_an_unparsable_age_is_none_so_its_process_is_excluded(text: str) -> None:
    # None rather than 0 and never a large fallback: an age this module cannot
    # establish must fail toward SPARING the process, not toward reaping it.
    assert reap.parse_etime(text) is None


def test_a_row_with_an_unparsable_age_is_dropped_from_the_table() -> None:
    table = reap.parse_processes(PS_SAMPLE + " 7000 1 not-a-time S fnox export\n")
    assert 7000 not in {process.pid for process in table}


# --------------------------------------------------------------------------- #
# Parsing the table
# --------------------------------------------------------------------------- #


def test_the_full_argv_survives_parsing_including_its_spaces() -> None:
    by_pid = {process.pid: process for process in _table()}
    assert by_pid[6002].command == "fnox export --format json"
    assert by_pid[6001].command.endswith("shims/git rev-parse")
    assert by_pid[6001].ppid == 500


def test_an_empty_process_table_is_an_error_not_an_all_clear() -> None:
    # A ps that saw nothing is a probe that failed. Folding it into "no targets"
    # is the shape `probes-need-a-control-arm.md` rule 9 exists to refuse.
    with pytest.raises(reap.ReapError, match="could not see"):
        reap.parse_processes("")


def test_a_failing_ps_raises_rather_than_returning_an_empty_table() -> None:
    reason = "no such binary"

    def explode(_command: Sequence[str]) -> str:
        raise OSError(reason)

    with pytest.raises(OSError, match=reason):
        reap.run_ps(explode)


# --------------------------------------------------------------------------- #
# Ancestor protection — the destructive one
# --------------------------------------------------------------------------- #


def test_the_whole_ancestor_chain_is_protected_up_to_init() -> None:
    assert reap.ancestor_pids(_table(), 6002) == (6002, 6001, 500, 1)


def test_a_ppid_cycle_terminates_instead_of_hanging() -> None:
    cyclic = (
        reap.Process(pid=10, ppid=11, age_s=99, state="S", command="a"),
        reap.Process(pid=11, ppid=10, age_s=99, state="S", command="b"),
    )
    assert set(reap.ancestor_pids(cyclic, 10)) == {10, 11}


def test_init_is_protected_even_when_the_walk_never_reaches_it() -> None:
    orphan = (reap.Process(pid=42, ppid=999, age_s=99, state="S", command="a"),)
    assert reap.INIT_PID in reap.protected_pids(orphan, self_pid=42)


def test_a_protected_process_is_spared_while_its_twin_is_selected() -> None:
    # Both arms on one axis: 6002 and 6003 run the IDENTICAL command and are the
    # same age. The only difference is that 6002 is an ancestor of the reaper.
    table = _table()
    selection = reap.select(
        table,
        pattern="fnox export",
        min_age_s=60,
        protected=reap.protected_pids(table, self_pid=6002),
    )
    assert {process.pid for process in selection.protected} == {6002}
    assert {process.pid for process in selection.targets} == {6003}


def test_without_the_protected_set_the_reaper_would_select_its_own_ancestor() -> None:
    # The control arm for the test above: this is what the bug looks like.
    selection = reap.select(_table(), pattern="fnox export", min_age_s=60)
    assert 6002 in {process.pid for process in selection.targets}


# --------------------------------------------------------------------------- #
# The age floor
# --------------------------------------------------------------------------- #


def test_a_process_younger_than_the_floor_is_bucketed_not_targeted() -> None:
    selection = reap.select(_table(), pattern="fnox export", min_age_s=60)
    assert {process.pid for process in selection.too_young} == {6004}
    assert 6004 not in {process.pid for process in selection.targets}


def test_lowering_the_floor_admits_the_young_process() -> None:
    selection = reap.select(_table(), pattern="fnox export", min_age_s=5)
    assert 6004 in {process.pid for process in selection.targets}


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #


def test_the_pattern_matches_against_the_full_argv_not_the_basename() -> None:
    selection = reap.select(_table(), pattern="--format json", min_age_s=0)
    assert len(selection.targets) == 3


def test_full_match_refuses_a_substring_that_search_would_accept() -> None:
    search = reap.select(_table(), pattern="fnox export", min_age_s=0)
    exact = reap.select(_table(), pattern="fnox export", min_age_s=0, full_match=True)
    assert search.targets
    assert not exact.targets


def test_full_match_accepts_the_complete_command() -> None:
    exact = reap.select(
        _table(),
        pattern=r"fnox export --format json",
        min_age_s=0,
        full_match=True,
    )
    assert len(exact.targets) == 3


# --------------------------------------------------------------------------- #
# PID reuse between the plan and the signal
# --------------------------------------------------------------------------- #


def test_a_pid_whose_command_changed_is_dropped_rather_than_signalled() -> None:
    targets = (reap.Process(pid=6003, ppid=1, age_s=999, state="S", command="fnox"),)
    recycled = (reap.Process(pid=6003, ppid=1, age_s=1, state="S", command="ssh"),)
    valid, dropped = reap.confirm_targets(targets, recycled, protected=frozenset({1}))
    assert not valid
    assert {process.pid for process in dropped} == {6003}


def test_an_unchanged_pid_is_confirmed() -> None:
    targets = (reap.Process(pid=6003, ppid=1, age_s=999, state="S", command="fnox"),)
    valid, dropped = reap.confirm_targets(targets, targets, protected=frozenset({1}))
    assert {process.pid for process in valid} == {6003}
    assert not dropped


def test_a_target_that_became_protected_is_dropped() -> None:
    targets = (reap.Process(pid=6003, ppid=1, age_s=999, state="S", command="fnox"),)
    valid, _ = reap.confirm_targets(targets, targets, protected=frozenset({6003}))
    assert not valid


# --------------------------------------------------------------------------- #
# Signalling — TERM, re-check, KILL
# --------------------------------------------------------------------------- #


def _recording_killer(calls: list[tuple[int, int]]) -> Callable[[int, int], None]:
    def kill(pid: int, sig: int) -> None:
        calls.append((pid, sig))

    return kill


def _runtime(
    calls: list[tuple[int, int]],
    *,
    runner: Callable[[Sequence[str]], str] | None = None,
    killer: Callable[[int, int], None] | None = None,
) -> reap.Runtime:
    """Every effectful seam substituted, so no test signals a real process."""
    return reap.Runtime(
        runner=_runner() if runner is None else runner,
        killer=_recording_killer(calls) if killer is None else killer,
        sleeper=lambda _s: None,
    )


def test_a_process_that_dies_on_term_is_never_sent_kill() -> None:
    calls: list[tuple[int, int]] = []
    # Snapshot 1 confirms the target, snapshot 2 (after the grace wait) is the
    # liveness re-check — and by then TERM has worked, so 6003 is gone.
    gone = PS_SAMPLE.replace(" 6003 ", " 9999 ")
    tables = iter([PS_SAMPLE, gone])

    def runner(_command: Sequence[str]) -> str:
        return next(tables, gone)

    table = _table()
    selection = reap.select(
        table,
        pattern="fnox export --format json",
        min_age_s=60,
        protected=reap.protected_pids(table, self_pid=6002),
    )
    result = reap.reap(selection, runtime=_runtime(calls, runner=runner))
    assert calls == [(6003, signal.SIGTERM)]
    assert not result.killed


def test_a_survivor_of_term_is_escalated_to_kill() -> None:
    calls: list[tuple[int, int]] = []
    table = _table()
    selection = reap.select(
        table,
        pattern="fnox export --format json",
        min_age_s=60,
        protected=reap.protected_pids(table, self_pid=6002),
    )
    result = reap.reap(selection, runtime=_runtime(calls))
    assert calls == [(6003, signal.SIGTERM), (6003, signal.SIGKILL)]
    assert {process.pid for process in result.killed} == {6003}
    # The table never changes in this fixture, so it is still there afterwards —
    # and the module reports that rather than claiming success.
    assert {process.pid for process in result.survivors} == {6003}


def test_a_process_that_exited_between_plan_and_signal_is_tolerated() -> None:
    def vanishing(_pid: int, _sig: int) -> None:
        raise ProcessLookupError

    table = _table()
    selection = reap.select(
        table,
        pattern="fnox export --format json",
        min_age_s=60,
        protected=reap.protected_pids(table, self_pid=6002),
    )
    result = reap.reap(selection, runtime=_runtime([], killer=vanishing))
    assert not result.signalled


# --------------------------------------------------------------------------- #
# The CLI contract: dry run by default
# --------------------------------------------------------------------------- #


def test_the_default_run_signals_nothing() -> None:
    calls: list[tuple[int, int]] = []
    rc = reap.reap_main(
        reap.ReapRequest(pattern="fnox export", min_age_s=60),
        runtime=_runtime(calls),
    )
    assert rc == 0
    assert calls == []


def test_kill_is_what_makes_it_signal() -> None:
    # The other arm of the same axis, so "signals nothing" cannot be passing
    # because the selection was empty.
    calls: list[tuple[int, int]] = []
    reap.reap_main(
        reap.ReapRequest(pattern="fnox export", min_age_s=60, kill=True),
        runtime=_runtime(calls),
    )
    assert calls


def test_the_cli_path_protects_the_ancestor_chain() -> None:
    # Written because a mutation demanded it: deleting `protected=` from
    # reap_main's select() call broke NOTHING — every other protection test
    # drives select() directly, so the wiring on the path a user actually
    # invokes was unasserted (`.claude/rules` mutation discipline, §5 rule 32).
    # 6002 and 6003 are the same command and the same age; only 6002 is an
    # ancestor of the reaper, so exactly one of them may be signalled.
    calls: list[tuple[int, int]] = []
    reap.reap_main(
        reap.ReapRequest(
            pattern="fnox export --format json",
            min_age_s=60,
            kill=True,
            signal_name="KILL",
        ),
        runtime=_runtime(calls),
        self_pid=6002,
    )
    assert {pid for pid, _sig in calls} == {6003}


def test_strict_reports_a_dry_run_that_found_targets() -> None:
    assert (
        reap.reap_main(
            reap.ReapRequest(pattern="fnox export", min_age_s=60, strict=True),
            runtime=_runtime([]),
        )
        == 1
    )


def test_an_unreadable_process_table_exits_two_not_zero() -> None:
    def blind(_command: Sequence[str]) -> str:
        return ""

    assert (
        reap.reap_main(
            reap.ReapRequest(pattern="fnox export"),
            runtime=_runtime([], runner=blind),
        )
        == 2
    )


def test_the_signal_choice_kill_does_not_escalate_twice() -> None:
    calls: list[tuple[int, int]] = []
    reap.reap_main(
        reap.ReapRequest(
            pattern="fnox export --format json",
            min_age_s=60,
            kill=True,
            signal_name="KILL",
        ),
        runtime=_runtime(calls),
    )
    assert {sig for _pid, sig in calls} == {signal.SIGKILL}


# --------------------------------------------------------------------------- #
# The plan is the audit trail
# --------------------------------------------------------------------------- #


def test_the_plan_prints_the_protected_set_so_the_exclusion_is_auditable() -> None:
    table = _table()
    selection = reap.select(
        table,
        pattern="fnox export",
        min_age_s=60,
        protected=reap.protected_pids(table, self_pid=6002),
    )
    plan = reap.format_plan(selection, pattern="fnox export", min_age_s=60)
    assert "protected PIDs (self + ancestors + init): 1, 500, 6001, 6002" in plan
    assert "TARGETS: 1" in plan
    assert "TOO YOUNG" in plan


def test_the_plan_states_the_load_caveat_rather_than_implying_a_load_fix() -> None:
    # The issue's own caveat, kept in the tool's mouth: a reap removes PID and
    # memory pressure, and signalling thousands of sleepers SPIKES load.
    plan = reap.format_plan(reap.Selection(), pattern="x", min_age_s=1)
    assert "does NOT fix load" in plan
    assert "PID and MEMORY pressure" in plan


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(9, "9s"), (150, "2m30s"), (7200, "2h00m"), (122400, "1d10h")],
)
def test_ages_are_formatted_for_a_human_reading_the_plan(
    seconds: int, expected: str
) -> None:
    assert reap.format_age(seconds) == expected
