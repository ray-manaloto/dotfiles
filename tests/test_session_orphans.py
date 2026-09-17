# Copyright (c) 2026 Raymond Manaloto
"""Tests for ancestry-scoped session orphan detection."""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import reap, session_orphans
from dotfiles_setup.main import setup_parser

PS_TREE = """\
    1     0 01-00:00:00 Ss   /sbin/launchd
  100     1    01:00:00 S    /usr/local/bin/claude
  200   100       10:00 S    zsh -c dotfiles-setup session-orphans
  201   200       09:59 S    dotfiles-setup session-orphans
  202   201       00:00 S    ps -eo pid=,ppid=,etime=,stat=,args=
  300   100       20:00 S    sh -c 'until [ -f x ]; do sleep 1; done'
  400   100       30:00 S    codex exec --full-auto task
  500     1       40:00 S    sh -c 'until [ -f outside ]; do sleep 1; done'
"""


def _runner() -> Callable[[Sequence[str]], str]:
    return lambda _command: PS_TREE


def test_fake_tree_classifies_wait_loop_and_blocks_other(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    rc = session_orphans.main(
        session_orphans.OrphanRequest(root_pid=100),
        runtime=reap.Runtime(runner=_runner(), sleeper=lambda _seconds: None),
        self_pid=201,
    )

    assert rc == 1
    assert "WAIT-LOOP unbounded     300" in caplog.text
    assert "BLOCK OTHER     400" in caplog.text
    assert "500" not in caplog.text
    assert " 200 " not in caplog.text
    assert " 202 " not in caplog.text


def test_caller_subtree_is_protected_without_hiding_sibling_waits() -> None:
    processes = reap.parse_processes(PS_TREE)

    plan = session_orphans.build_plan(processes, root_pid=100, self_pid=201)

    assert 202 in plan.protected_pids
    assert 202 not in {item.pid for item in plan.descendants}
    assert {item.pid for item in plan.wait_loops} == {300}


def test_allowing_every_other_descendant_clears_the_block() -> None:
    rc = session_orphans.main(
        session_orphans.OrphanRequest(
            root_pid=100,
            allowed_pids=frozenset({400}),
        ),
        runtime=reap.Runtime(runner=_runner(), sleeper=lambda _seconds: None),
        self_pid=201,
    )

    assert rc == 0


def test_kill_reaps_wait_loop_before_unallowed_other_blocks() -> None:
    signalled: list[tuple[int, int]] = []
    rc = session_orphans.main(
        session_orphans.OrphanRequest(root_pid=100, kill=True),
        runtime=reap.Runtime(
            runner=_runner(),
            killer=lambda pid, sig: signalled.append((pid, sig)),
            sleeper=lambda _seconds: None,
        ),
        self_pid=201,
    )

    assert rc == 1
    assert signalled == [(300, signal.SIGTERM), (300, signal.SIGKILL)]


def test_kill_happy_path_terms_then_rechecks_the_wait_loop() -> None:
    signalled: list[tuple[int, int]] = []
    without_wait = PS_TREE.replace(
        "  300   100       20:00 S    sh -c 'until [ -f x ]; do sleep 1; done'\n",
        "",
    )
    tables = iter([PS_TREE, PS_TREE, without_wait])

    def runner(_command: Sequence[str]) -> str:
        return next(tables, without_wait)

    rc = session_orphans.main(
        session_orphans.OrphanRequest(
            root_pid=100,
            kill=True,
            allowed_pids=frozenset({400}),
        ),
        runtime=reap.Runtime(
            runner=runner,
            killer=lambda pid, sig: signalled.append((pid, sig)),
            sleeper=lambda _seconds: None,
        ),
        self_pid=201,
    )

    assert rc == 0
    assert signalled == [(300, signal.SIGTERM)]


def test_kill_reports_a_wait_loop_that_survives_escalation() -> None:
    signalled: list[tuple[int, int]] = []
    rc = session_orphans.main(
        session_orphans.OrphanRequest(
            root_pid=100,
            kill=True,
            allowed_pids=frozenset({400}),
        ),
        runtime=reap.Runtime(
            runner=_runner(),
            killer=lambda pid, sig: signalled.append((pid, sig)),
            sleeper=lambda _seconds: None,
        ),
        self_pid=201,
    )

    assert rc == 1
    assert signalled == [(300, signal.SIGTERM), (300, signal.SIGKILL)]


def test_plan_labels_bounded_wait_loops_without_excluding_them() -> None:
    bounded = reap.Process(
        pid=301,
        ppid=100,
        age_s=10,
        state="S",
        command=(
            "sh -c 'while [ $SECONDS -lt $deadline ] && [ ! -f x ]; do sleep 1; done'"
        ),
    )
    processes = (*reap.parse_processes(PS_TREE), bounded)
    plan = session_orphans.build_plan(processes, root_pid=100, self_pid=201)

    rendered = session_orphans.format_plan(plan)
    assert {item.pid for item in plan.wait_loops} == {300, 301}
    assert "WAIT-LOOP unbounded     300" in rendered
    assert "WAIT-LOOP bounded     301" in rendered


def test_default_root_is_the_nearest_claude_ancestor() -> None:
    rc = session_orphans.main(
        session_orphans.OrphanRequest(allowed_pids=frozenset({400})),
        runtime=reap.Runtime(runner=_runner(), sleeper=lambda _seconds: None),
        self_pid=201,
    )
    assert rc == 0


def test_public_cli_exposes_root_kill_and_repeatable_allow() -> None:
    parsed = setup_parser().parse_args(
        ["session-orphans", "--root", "100", "--kill", "--allow", "400"]
    )
    assert parsed.root == 100
    assert parsed.kill
    assert parsed.allow == [400]
