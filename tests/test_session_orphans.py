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

MCP_SERVER_ARGV = (
    "node /Users/alice/.npm/_npx/abc123/node_modules/.bin/mcp-pdf-server --stdio"
)
WAIT_LOOP_ARGV = (
    "zsh -c 'deadline=$((SECONDS+600)); "
    "while [ $SECONDS -lt $deadline ]; do sleep 5; done'"
)
WAIT_GROUP_ROWS = (
    f"  330   100       06:00 S    {WAIT_LOOP_ARGV}\n"
    "  331   330       00:04 S    /bin/sleep 5\n"
)

HEALTHY_PS_TREE = (
    """\
    1     0 01-00:00:00 Ss   /sbin/launchd
  100     1    01:00:00 S    /usr/local/bin/claude
  200   100       10:00 S    zsh -c dotfiles-setup session-orphans
  201   200       09:59 S    dotfiles-setup session-orphans
  202   201       00:00 S    ps -eo pid=,ppid=,etime=,stat=,args=
"""
    "  310   100       08:00 S    "
    "npm exec @modelcontextprotocol/server-pdf --stdio    \n"
    f"  311   310       07:59 S    {MCP_SERVER_ARGV}\n"
    "  320   100       07:00 S    caffeinate -i -t 300\n"
    f"{WAIT_GROUP_ROWS}"
)


def _runner() -> Callable[[Sequence[str]], str]:
    return lambda _command: PS_TREE


def test_healthy_harness_and_wait_loop_children_do_not_block(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    processes = reap.parse_processes(HEALTHY_PS_TREE)

    plan = session_orphans.build_plan(processes, root_pid=100, self_pid=201)
    rc = session_orphans.main(
        session_orphans.OrphanRequest(root_pid=100),
        runtime=reap.Runtime(
            runner=lambda _command: HEALTHY_PS_TREE,
            sleeper=lambda _seconds: None,
        ),
        self_pid=201,
    )

    assert rc == 0
    assert {item.pid for item in plan.wait_loops} == {330}
    assert {item.process.pid for item in plan.wait_loop_children} == {331}
    assert {item.process.pid for item in plan.harness} == {310, 311, 320}
    assert not plan.other
    assert "WAIT-LOOP child sleep" in caplog.text
    assert "HARNESS MCP server launcher" in caplog.text
    assert "HARNESS MCP server process" in caplog.text
    assert "HARNESS caffeinate inhibitor" in caplog.text


def test_every_typed_shape_ignores_trailing_whitespace() -> None:
    process_table = HEALTHY_PS_TREE
    server_command = (
        "node /Users/alice/.npm/_npx/abc123/node_modules/.bin/mcp-pdf-server --stdio"
    )
    for command in (server_command, "caffeinate -i -t 300", "/bin/sleep 5"):
        process_table = process_table.replace(f"{command}\n", f"{command} \t \n")
    processes = reap.parse_processes(process_table)

    plan = session_orphans.build_plan(processes, root_pid=100, self_pid=201)

    assert {item.process.pid for item in plan.wait_loop_children} == {331}
    assert {item.process.pid for item in plan.harness} == {310, 311, 320}
    assert not plan.other


def test_harness_command_text_without_required_parent_blocks() -> None:
    wrong_parent_rows = (
        "  600   100       05:00 S    zsh -c active-work\n"
        "  610   600       04:00 S    "
        "npm exec @modelcontextprotocol/server-pdf --stdio\n"
        f"  620   100       03:00 S    {MCP_SERVER_ARGV}\n"
        "  630   600       02:00 S    caffeinate -i -t 300\n"
    )
    process_table = PS_TREE.replace(
        "  300   100       20:00 S    sh -c 'until [ -f x ]; do sleep 1; done'\n"
        "  400   100       30:00 S    codex exec --full-auto task\n",
        wrong_parent_rows,
    )
    processes = reap.parse_processes(process_table)

    plan = session_orphans.build_plan(processes, root_pid=100, self_pid=201)
    rc = session_orphans.main(
        session_orphans.OrphanRequest(root_pid=100),
        runtime=reap.Runtime(
            runner=lambda _command: process_table,
            sleeper=lambda _seconds: None,
        ),
        self_pid=201,
    )

    assert rc == 1
    assert not plan.harness
    assert {item.pid for item in plan.other} == {600, 610, 620, 630}


def test_wait_loop_only_admits_a_direct_typed_sleep_child() -> None:
    unsafe_rows = """\
  340   330       03:00 S    mise run ship
  341   340       02:59 S    uv run --project python dotfiles-setup pr ship
  360   330       02:00 S    sleep 5; rm -rf x
  361   330       01:00 S    sleep --help
  600   100       05:00 S    zsh -c active-work
  350   600       00:05 S    /bin/sleep 5
"""
    process_table = HEALTHY_PS_TREE + unsafe_rows
    processes = reap.parse_processes(process_table)

    plan = session_orphans.build_plan(processes, root_pid=100, self_pid=201)
    rc = session_orphans.main(
        session_orphans.OrphanRequest(root_pid=100),
        runtime=reap.Runtime(
            runner=lambda _command: process_table,
            sleeper=lambda _seconds: None,
        ),
        self_pid=201,
    )
    partition_ids = (
        {item.pid for item in plan.wait_loops},
        {item.process.pid for item in plan.wait_loop_children},
        {item.process.pid for item in plan.harness},
        {item.pid for item in plan.other},
    )

    assert rc == 1
    assert partition_ids[1] == {331}
    assert partition_ids[3] == {340, 341, 350, 360, 361, 600}
    assert set.union(*partition_ids) == {item.pid for item in plan.descendants}
    assert sum(len(items) for items in partition_ids) == len(set.union(*partition_ids))


def test_kill_targets_the_wait_loop_and_its_sleep_but_not_harness() -> None:
    signalled: list[tuple[int, int]] = []
    without_wait_group = HEALTHY_PS_TREE.replace(WAIT_GROUP_ROWS, "")
    assert without_wait_group != HEALTHY_PS_TREE
    tables = iter([HEALTHY_PS_TREE, HEALTHY_PS_TREE, without_wait_group])

    def runner(_command: Sequence[str]) -> str:
        return next(tables, without_wait_group)

    rc = session_orphans.main(
        session_orphans.OrphanRequest(root_pid=100, kill=True),
        runtime=reap.Runtime(
            runner=runner,
            killer=lambda pid, sig: signalled.append((pid, sig)),
            sleeper=lambda _seconds: None,
        ),
        self_pid=201,
    )

    assert rc == 0
    assert signalled == [(330, signal.SIGTERM), (331, signal.SIGTERM)]


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
            "sh -c 'deadline=$((SECONDS+600)); "
            "while [ $SECONDS -lt $deadline ]; do sleep 5; done'"
        ),
    )
    counter = reap.Process(
        pid=302,
        ppid=100,
        age_s=10,
        state="S",
        command="sh -c 'while [ $i -lt 40 ]; do sleep 1; done'",
    )
    read_loop = reap.Process(
        pid=303,
        ppid=100,
        age_s=10,
        state="S",
        command="sh -c 'while read -r line; do sleep 1; done'",
    )
    processes = (*reap.parse_processes(PS_TREE), bounded, counter, read_loop)
    plan = session_orphans.build_plan(processes, root_pid=100, self_pid=201)

    rendered = session_orphans.format_plan(plan)
    assert {item.pid for item in plan.wait_loops} == {300, 301}
    assert {item.pid for item in plan.other} == {302, 303, 400}
    assert "WAIT-LOOP unbounded     300" in rendered
    assert "WAIT-LOOP bounded     301" in rendered
    assert "BLOCK OTHER     302" in rendered
    assert "BLOCK OTHER     303" in rendered


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
