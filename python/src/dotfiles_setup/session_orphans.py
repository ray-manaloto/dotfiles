# Copyright (c) 2026 Raymond Manaloto
"""Audit and optionally reap processes descended from the active Claude session.

At handoff, every session-local wait loop is an orphan, including a loop whose
condition carries a deadline. Boundedness changes the audit label, not whether
the process belongs to the session being closed.
Only argv-visible loops are classifiable; a ``zsh -c source ...snapshot...``
wrapper whose argv contains the loop is classified as that WAIT-LOOP.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum

from dotfiles_setup import hook_guard, reap

logger = logging.getLogger(__name__)
_CLAUDE_COMMAND = re.compile(r"(?:^|[/\s])claude(?:\s|$)", re.IGNORECASE)
_SHELL_COMMAND = re.compile(r"(?:^|[/\s])(?:bash|zsh|dash|sh)(?:\s|$)", re.IGNORECASE)


class HarnessParentRequirement(Enum):
    """The already-classified parent needed to admit a harness child."""

    SESSION_ROOT = "session root"
    HARNESS = "harness"


@dataclass(frozen=True)
class HarnessChildShape:
    """One command shape whose parent proves harness ownership."""

    name: str
    command_pattern: re.Pattern[str]
    parent_requirement: HarnessParentRequirement


@dataclass(frozen=True)
class WaitLoopChildShape:
    """One inert direct-child command owned by a WAIT-LOOP."""

    name: str
    command_pattern: re.Pattern[str]


@dataclass(frozen=True)
class ShapedProcess:
    """A process together with the reviewed shape that admitted it."""

    process: reap.Process
    shape_name: str


# Each pattern is a full command line, not a substring allowlist. The launcher
# and its server are the measured PDF MCP pair; the server additionally needs
# an already-admitted HARNESS parent so an unrelated node process cannot pass.
HARNESS_CHILD_SHAPES = (
    HarnessChildShape(
        "MCP server launcher",
        re.compile(r"^(?:/[^\s]+/)?npm exec @modelcontextprotocol/server-pdf --stdio$"),
        HarnessParentRequirement.SESSION_ROOT,
    ),
    HarnessChildShape(
        "MCP server process",
        re.compile(
            r"^(?:/[^\s]+/)?node "
            r"/Users/[^/\s]+/\.npm/_npx/[A-Za-z0-9]+/node_modules/\.bin/"
            r"mcp-pdf-server --stdio$"
        ),
        HarnessParentRequirement.HARNESS,
    ),
    # The harness renews this exact five-minute macOS sleep inhibitor.
    HarnessChildShape(
        "caffeinate inhibitor",
        re.compile(r"^(?:/[^\s]+/)?caffeinate -i -t 300$"),
        HarnessParentRequirement.SESSION_ROOT,
    ),
)

# A shell loop's direct sleep is inert bookkeeping, but broader descendants
# may be real work and deliberately remain subject to HARNESS/OTHER handling.
WAIT_LOOP_CHILD_SHAPES = (
    WaitLoopChildShape(
        "sleep",
        re.compile(r"^(?:/[^\s]+/)?sleep [0-9]+(?:\.[0-9]+)?[smh]?$"),
    ),
)


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
    wait_loop_children: tuple[ShapedProcess, ...]
    harness: tuple[ShapedProcess, ...]
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
    wait_loop_children: list[ShapedProcess] = []
    harness: list[ShapedProcess] = []
    harness_ids: set[int] = set()
    other: list[reap.Process] = []
    # These ordered exits are the classification precedence contract:
    # WAIT-LOOP > direct typed child > parent-qualified HARNESS > OTHER.
    for process in descendants:
        if process.pid in wait_ids:
            continue
        match_command = process.command.rstrip()
        wait_shape = next(
            (
                shape
                for shape in WAIT_LOOP_CHILD_SHAPES
                if process.ppid in wait_ids
                and shape.command_pattern.fullmatch(match_command)
            ),
            None,
        )
        if wait_shape is not None:
            wait_loop_children.append(ShapedProcess(process, wait_shape.name))
            continue
        harness_shape = next(
            (
                shape
                for shape in HARNESS_CHILD_SHAPES
                if shape.command_pattern.fullmatch(match_command)
                and (
                    (
                        shape.parent_requirement
                        is HarnessParentRequirement.SESSION_ROOT
                        and process.ppid == root_pid
                    )
                    or (
                        shape.parent_requirement is HarnessParentRequirement.HARNESS
                        and process.ppid in harness_ids
                    )
                )
            ),
            None,
        )
        if harness_shape is not None:
            harness.append(ShapedProcess(process, harness_shape.name))
            harness_ids.add(process.pid)
            continue
        other.append(process)
    allowed_other = tuple(process for process in other if process.pid in allowed_pids)
    return OrphanPlan(
        root_pid=root_pid,
        descendants=descendants,
        wait_loops=wait_loops,
        wait_loop_children=tuple(wait_loop_children),
        harness=tuple(harness),
        other=tuple(other),
        allowed_other=allowed_other,
        protected_pids=protected,
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
    ]
    for item in plan.wait_loops:
        lines.append(
            "    WAIT-LOOP "
            + (
                "unbounded "
                if hook_guard.is_unbounded_wait_loop(
                    hook_guard.mask_shell_syntax(item.command)
                )
                else "bounded "
            )
            + item.describe()
        )
        lines.extend(
            f"      WAIT-LOOP child {child.shape_name} {child.process.describe()}"
            for child in plan.wait_loop_children
            if child.process.ppid == item.pid
        )
    lines.append(f"  HARNESS: {len(plan.harness)}")
    lines.extend(
        f"    HARNESS {item.shape_name} {item.process.describe()}"
        for item in plan.harness
    )
    lines.append(f"  OTHER: {len(plan.other)}")
    lines.extend(
        f"    {'ALLOWED' if item in plan.allowed_other else 'BLOCK'} OTHER "
        f"{item.describe()}"
        for item in plan.other
    )
    return "\n".join(lines)


def main(
    request: OrphanRequest,
    *,
    runtime: reap.Runtime | None = None,
    self_pid: int | None = None,
) -> int:
    """Print a dry-run plan; with ``--kill``, reap WAIT-LOOP groups only."""
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
    reapable = (
        *plan.wait_loops,
        *(item.process for item in plan.wait_loop_children),
    )
    if request.kill and reapable:
        selection = reap.Selection(
            targets=reapable,
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
    elif reapable:
        logger.info("session-orphans: DRY RUN — no WAIT-LOOP was signalled")
    if plan.blocking_other:
        logger.error(
            "session-orphans: BLOCK — allow every OTHER pid explicitly with --allow"
        )
    return 1 if plan.blocking_other or survivors else 0
