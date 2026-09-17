# Copyright (c) 2026 Raymond Manaloto
"""Audit and optionally reap processes descended from the active Claude session.

At handoff, every session-local wait loop is an orphan, including a loop whose
condition carries a deadline. Boundedness changes the audit label, not whether
the process belongs to the session being closed.
Only argv-visible loops are classifiable; a ``zsh -c source ...snapshot...``
wrapper is OTHER and is left to #1171.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

from dotfiles_setup import hook_guard, reap

logger = logging.getLogger(__name__)
_CLAUDE_COMMAND = re.compile(r"(?:^|[/\s])claude(?:\s|$)", re.IGNORECASE)
_SHELL_COMMAND = re.compile(r"(?:^|[/\s])(?:bash|zsh|dash|sh)(?:\s|$)", re.IGNORECASE)


@dataclass(frozen=True)
class OrphanRequest:
    """Scope and mutation authority for one descendant census."""

    root_pid: int | None = None
    kill: bool = False
    allowed_pids: frozenset[int] = frozenset()


@dataclass(frozen=True)
class OrphanPlan:
    """Typed descendant partition, suitable for a human-readable audit plan."""

    root_pid: int
    descendants: tuple[reap.Process, ...]
    wait_loops: tuple[reap.Process, ...]
    other: tuple[reap.Process, ...]
    allowed_other: tuple[reap.Process, ...]
    protected_pids: frozenset[int]

    @property
    def blocking_other(self) -> tuple[reap.Process, ...]:
        """OTHER descendants that were not explicitly allowed by pid."""
        allowed = {item.pid for item in self.allowed_other}
        return tuple(item for item in self.other if item.pid not in allowed)


def _session_root(processes: tuple[reap.Process, ...], self_pid: int) -> int | None:
    by_pid = {process.pid: process for process in processes}
    for pid in reap.ancestor_pids(processes, self_pid):
        process = by_pid.get(pid)
        if process is not None and _CLAUDE_COMMAND.search(process.command):
            return pid
    return None


def build_plan(
    processes: tuple[reap.Process, ...],
    *,
    root_pid: int,
    self_pid: int,
    allowed_pids: frozenset[int] = frozenset(),
) -> OrphanPlan:
    """Select root descendants while protecting the caller and its whole tree."""
    by_pid = {process.pid: process for process in processes}
    own_chain = frozenset(reap.ancestor_pids(processes, self_pid))
    own_subtree = frozenset({self_pid, *reap.descendant_pids(processes, self_pid)})
    protected = own_chain | own_subtree | {reap.INIT_PID}
    descendant_ids = tuple(
        pid for pid in reap.descendant_pids(processes, root_pid) if pid not in protected
    )
    descendants = tuple(by_pid[pid] for pid in descendant_ids if pid in by_pid)
    wait_loops = tuple(
        process
        for process in descendants
        if _SHELL_COMMAND.search(process.command)
        and hook_guard.is_audit_wait_loop(hook_guard.mask_shell_syntax(process.command))
    )
    wait_ids = {process.pid for process in wait_loops}
    other = tuple(process for process in descendants if process.pid not in wait_ids)
    allowed_other = tuple(process for process in other if process.pid in allowed_pids)
    return OrphanPlan(
        root_pid,
        descendants,
        wait_loops,
        other,
        allowed_other,
        protected,
    )


def format_plan(plan: OrphanPlan) -> str:
    """Render the complete descendant partition before any process is signalled."""
    lines = [
        (
            f"session-orphans plan: root={plan.root_pid} "
            f"descendants={len(plan.descendants)}"
        ),
        "  protected caller chain: "
        + ", ".join(str(pid) for pid in sorted(plan.protected_pids)),
        f"  WAIT-LOOP: {len(plan.wait_loops)}",
        *(
            "    WAIT-LOOP "
            + (
                "unbounded "
                if hook_guard.is_unbounded_wait_loop(
                    hook_guard.mask_shell_syntax(item.command)
                )
                else "bounded "
            )
            + item.describe()
            for item in plan.wait_loops
        ),
        f"  OTHER: {len(plan.other)}",
        *(
            f"    {'ALLOWED' if item in plan.allowed_other else 'BLOCK'} OTHER "
            f"{item.describe()}"
            for item in plan.other
        ),
    ]
    return "\n".join(lines)


def main(
    request: OrphanRequest,
    *,
    runtime: reap.Runtime | None = None,
    self_pid: int | None = None,
) -> int:
    """Print a dry-run plan; with ``--kill``, reap only WAIT-LOOP descendants."""
    runtime = reap.Runtime() if runtime is None else runtime
    caller_pid = os.getpid() if self_pid is None else self_pid
    try:
        processes = reap.snapshot(runtime.runner)
    except reap.ReapError:
        logger.exception("session-orphans could not read the process table")
        return 2
    root_pid = request.root_pid or _session_root(processes, caller_pid)
    if root_pid is None:
        logger.error("session-orphans: no claude ancestor found; pass --root PID")
        return 2
    if root_pid not in {process.pid for process in processes}:
        logger.error(
            "session-orphans: root pid %d is not in the process table", root_pid
        )
        return 2

    plan = build_plan(
        processes,
        root_pid=root_pid,
        self_pid=caller_pid,
        allowed_pids=request.allowed_pids,
    )
    logger.info("%s", format_plan(plan))
    survivors = False
    if request.kill and plan.wait_loops:
        selection = reap.Selection(
            targets=plan.wait_loops,
            protected_set=plan.protected_pids,
            scanned=len(processes),
        )
        try:
            result = reap.reap(selection, runtime=runtime)
        except reap.ReapError:
            logger.exception("session-orphans aborted before signalling")
            return 2
        if result.survivors:
            logger.error(
                "session-orphans: %d WAIT-LOOP process(es) survived KILL",
                len(result.survivors),
            )
            survivors = True
    elif plan.wait_loops:
        logger.info("session-orphans: DRY RUN — no WAIT-LOOP was signalled")
    if plan.blocking_other:
        logger.error(
            "session-orphans: BLOCK — allow every OTHER pid explicitly with --allow"
        )
    return 1 if plan.blocking_other or survivors else 0
