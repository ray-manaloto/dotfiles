# Copyright (c) 2026 Raymond Manaloto
"""Reap wedged processes by pattern and age, without killing your own shell.

On 2026-08-08 this host accumulated **1,174** wedged ``mise/shims/git``
processes, each with a stuck ``fnox export --format json`` child — 2,362 to
clear, oldest 1d10h (#653; the cause is knowledge-base#243, still open). The
cleanup was written by hand, under time pressure, in a throwaway script. Four
pieces of it are destructive to get wrong, and re-deriving them under pressure
is exactly when they get got wrong:

* **ancestor-chain protection** — walk ``ppid`` from this process to init and
  exclude that chain, or the reap kills the shell that launched it;
* **an age floor** — ``etime`` parsed across every ``ps`` format, so anything
  younger than N seconds (i.e. possibly live work) is spared;
* **exact matching under a pattern you supply**, never ``pkill`` on a
  substring;
* **TERM, then KILL**, re-checking liveness in between.

What this tool does NOT claim
-----------------------------

**A reap does not fix load.** Those 2,362 processes were ``stat=S`` at 0:00.03
CPU — sleeping, not burning CPU. The 1-minute average moved 7.98 → 7.02, and
the 5/15-minute figures were still decaying from the **kill transient**, which
spiked the 1-minute average to **137.96** the instant they were signalled. What
a reap definitively removes is **PID and memory pressure**, so that is what
:func:`format_plan` says. Any wording that implies a load fix is wrong.

Why dry-run is the default
--------------------------

``--kill`` is required to signal anything (Ray, 2026-08-08b), matching this
repo's posture for destructive verbs: ``mise run lock`` refuses its bare form,
``mise run lock-image`` refuses the wrong host. The flag is named for the
irreversible thing it does rather than a neutral ``--apply``.

Two safety properties beyond the four above
-------------------------------------------

**PID reuse is checked, not assumed away.** Between the snapshot that selects
victims and the signal that kills them, the kernel may recycle a PID onto an
unrelated process. So :func:`reap` re-snapshots immediately before signalling
and only signals a PID whose **command string still matches** the one selected
(:func:`confirm_targets`). A PID that changed identity is dropped, not killed.

**An empty snapshot is an error, not an all-clear.** A ``ps`` that failed,
timed out, or returned nothing it could parse exits non-zero and says it could not
see — never "nothing matched"
(``.claude/rules/probes-need-a-control-arm.md`` rule 9).
"""

from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

logger = logging.getLogger(__name__)

#: One line per process: pid, ppid, elapsed time, state, full argv. ``args``
#: last because it is the only field that contains spaces.
PS_COMMAND: tuple[str, ...] = ("ps", "-eo", "pid=,ppid=,etime=,stat=,args=")

_PS_TIMEOUT_S = 30.0
_PS_FIELDS = 5

#: ``DD-HH:MM:SS`` is the widest ``ps`` elapsed-time form: days, then three
#: colon-separated segments. More than that is not a shape ``ps`` produces.
_MAX_ETIME_SEGMENTS = 3

#: Never signalled, on any host, whatever the pattern says.
INIT_PID = 1

#: Seconds a process must have been alive before it is eligible. A floor rather
#: than zero: the pile this tool exists for was over a day old, while anything
#: seconds-young is plausibly live work — including a child of this very run.
DEFAULT_MIN_AGE_S = 300

#: Seconds between TERM and the liveness re-check that decides on KILL.
DEFAULT_GRACE_S = 5.0


class ReapError(RuntimeError):
    """The process table could not be read — distinct from "nothing matched"."""


@dataclass(frozen=True)
class Process:
    """One row of the process table, as ``ps`` reported it."""

    pid: int
    ppid: int
    age_s: int
    state: str
    command: str

    def describe(self) -> str:
        """``12345 (1d10h, S) /path/to/git ...`` — one auditable line."""
        return f"{self.pid:>7} ({format_age(self.age_s)}, {self.state}) {self.command}"


def parse_etime(text: str) -> int | None:
    """Seconds from any ``ps`` elapsed-time format, or ``None`` if unparsable.

    Four shapes exist across the platforms this repo runs on: ``SS``,
    ``MM:SS``, ``HH:MM:SS`` and ``DD-HH:MM:SS``. Getting this wrong in the
    lenient direction is what turns an age floor into no age floor, so an
    unrecognised shape returns ``None`` and its process is **excluded** rather
    than assumed old.
    """
    raw = text.strip()
    if not raw:
        return None
    days = 0
    if "-" in raw:
        day_text, _, raw = raw.partition("-")
        try:
            days = int(day_text)
        except ValueError:
            return None
    parts = raw.split(":")
    if len(parts) > _MAX_ETIME_SEGMENTS:
        return None
    try:
        values = [int(part) for part in parts]
    except ValueError:
        return None
    seconds = 0
    for value in values:
        seconds = seconds * 60 + value
    return days * 86400 + seconds


def format_age(seconds: int) -> str:
    """``1d10h`` / ``2h05m`` / ``45s`` — compact, for a human reading a plan."""
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    if days:
        return f"{days}d{hours:02d}h"
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def run_ps(runner: Callable[[Sequence[str]], str] | None = None) -> str:
    """Raw ``ps`` output, or raise :exc:`ReapError` naming what went wrong."""
    if runner is not None:
        return runner(PS_COMMAND)
    try:
        result = subprocess.run(
            PS_COMMAND,
            capture_output=True,
            text=True,
            check=False,
            timeout=_PS_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"could not run {' '.join(PS_COMMAND)}: {exc}"
        raise ReapError(msg) from exc
    if result.returncode != 0:
        detail = result.stderr.strip()
        msg = f"{' '.join(PS_COMMAND)} exited {result.returncode}: {detail}"
        raise ReapError(msg)
    return result.stdout


def parse_processes(output: str) -> tuple[Process, ...]:
    """Parse ``ps`` output, dropping rows whose age cannot be established.

    Raises :exc:`ReapError` when nothing at all parsed: a process table with
    zero rows means the probe failed, not that the host has no processes.
    """
    processes: list[Process] = []
    for line in output.splitlines():
        fields = line.split(maxsplit=_PS_FIELDS - 1)
        if len(fields) < _PS_FIELDS:
            continue
        pid_text, ppid_text, etime_text, state, command = fields
        age = parse_etime(etime_text)
        if age is None:
            logger.debug("unparsable etime %r for pid %s", etime_text, pid_text)
            continue
        try:
            pid, ppid = int(pid_text), int(ppid_text)
        except ValueError:
            continue
        processes.append(
            Process(pid=pid, ppid=ppid, age_s=age, state=state, command=command)
        )
    if not processes:
        msg = (
            "the process table parsed to zero rows — the probe could not see, "
            "which is NOT 'nothing matched'"
        )
        raise ReapError(msg)
    return tuple(processes)


def snapshot(
    runner: Callable[[Sequence[str]], str] | None = None,
) -> tuple[Process, ...]:
    """One parsed view of the process table."""
    return parse_processes(run_ps(runner))


def ancestor_pids(processes: Iterable[Process], start_pid: int) -> tuple[int, ...]:
    """``start_pid`` and every ancestor up to init, cycle-safe.

    A corrupt or racing table can present a ``ppid`` cycle; the ``seen`` set
    means that hangs nothing. Anything unreachable simply stops the walk, which
    fails toward protecting *fewer* processes — so :func:`protected_pids`
    always adds init separately rather than relying on the walk reaching it.
    """
    by_pid = {process.pid: process for process in processes}
    chain: list[int] = []
    seen: set[int] = set()
    current = start_pid
    while current > 0 and current not in seen:
        seen.add(current)
        chain.append(current)
        process = by_pid.get(current)
        if process is None:
            break
        current = process.ppid
    return tuple(chain)


def protected_pids(
    processes: Iterable[Process],
    *,
    self_pid: int | None = None,
    extra: Iterable[int] = (),
) -> frozenset[int]:
    """The set no pattern can ever select: self, its ancestors, init, extras."""
    pid = os.getpid() if self_pid is None else self_pid
    return frozenset(ancestor_pids(processes, pid)) | {INIT_PID} | set(extra)


@dataclass(frozen=True)
class Selection:
    """What a pattern selected, and everything it deliberately did not."""

    targets: tuple[Process, ...] = ()
    protected: tuple[Process, ...] = ()
    too_young: tuple[Process, ...] = ()
    protected_set: frozenset[int] = field(default_factory=frozenset)
    scanned: int = 0

    @property
    def oldest(self) -> Process | None:
        """The longest-lived target, or ``None`` when nothing was selected."""
        return max(self.targets, key=lambda p: p.age_s) if self.targets else None

    @property
    def youngest(self) -> Process | None:
        """The newest target — a value near the age floor means it is growing."""
        return min(self.targets, key=lambda p: p.age_s) if self.targets else None


def select(
    processes: Iterable[Process],
    *,
    pattern: str,
    min_age_s: int = DEFAULT_MIN_AGE_S,
    protected: frozenset[int] | None = None,
    full_match: bool = False,
) -> Selection:
    """Partition the table into targets, protected matches, and too-young ones.

    The three non-target buckets are kept rather than discarded because the
    plan has to be *auditable*: "42 matched, 3 protected, 7 too young" tells
    you the filters worked, while a bare target count cannot distinguish a
    working age floor from a broken one.
    """
    processes = tuple(processes)
    protected = frozenset() if protected is None else protected
    compiled = re.compile(pattern)
    matcher = compiled.fullmatch if full_match else compiled.search
    targets: list[Process] = []
    protected_hits: list[Process] = []
    young: list[Process] = []
    for process in processes:
        if matcher(process.command) is None:
            continue
        if process.pid in protected:
            protected_hits.append(process)
        elif process.age_s < min_age_s:
            young.append(process)
        else:
            targets.append(process)
    return Selection(
        targets=tuple(targets),
        protected=tuple(protected_hits),
        too_young=tuple(young),
        protected_set=protected,
        scanned=len(processes),
    )


#: Printed with every plan. The issue's own caveat, kept in the tool's mouth so
#: it cannot be lost when someone quotes the output.
LOAD_CAVEAT = (
    "NOTE: a reap removes PID and MEMORY pressure. It does NOT fix load average "
    "— wedged processes are typically sleeping (stat=S) at ~0 CPU, and "
    "signalling thousands of them spikes the 1-minute average (measured: 7.98 "
    "-> 137.96 at the moment of the kill, #653)."
)


def format_plan(selection: Selection, *, pattern: str, min_age_s: int) -> str:
    """The human-readable plan, including the protected set, before acting."""
    floor = format_age(min_age_s)
    protected_pid_list = ", ".join(str(pid) for pid in sorted(selection.protected_set))
    lines = [
        (
            f"reap plan: pattern={pattern!r} min-age={floor} "
            f"scanned={selection.scanned} process(es)"
        ),
        f"  protected PIDs (self + ancestors + init): {protected_pid_list}",
        f"  matched and PROTECTED (never signalled): {len(selection.protected)}",
        f"  matched but TOO YOUNG (< {floor}): {len(selection.too_young)}",
        f"  TARGETS: {len(selection.targets)}",
    ]
    oldest, youngest = selection.oldest, selection.youngest
    if oldest is not None and youngest is not None:
        lines.append(
            f"  target ages: oldest {format_age(oldest.age_s)}, "
            f"newest {format_age(youngest.age_s)}"
        )
    lines.extend(f"    {process.describe()}" for process in selection.protected)
    lines.extend(f"    target {process.describe()}" for process in selection.targets)
    lines.append(LOAD_CAVEAT)
    return "\n".join(lines)


def confirm_targets(
    targets: Iterable[Process],
    current: Iterable[Process],
    *,
    protected: frozenset[int],
) -> tuple[tuple[Process, ...], tuple[Process, ...]]:
    """Re-verify identity against a fresh table: ``(still_valid, dropped)``.

    A PID alone is not an identity — the kernel recycles them. A target is only
    signalled when the live table still shows that PID running the **same
    command**, and never when it has become protected in the meantime.
    """
    live = {process.pid: process for process in current}
    valid: list[Process] = []
    dropped: list[Process] = []
    for target in targets:
        found = live.get(target.pid)
        if found is None or found.command != target.command or found.pid in protected:
            dropped.append(target)
        else:
            valid.append(target)
    return tuple(valid), tuple(dropped)


@dataclass(frozen=True)
class ReapResult:
    """What was actually signalled, and what survived it."""

    signalled: tuple[Process, ...] = ()
    dropped: tuple[Process, ...] = ()
    killed: tuple[Process, ...] = ()
    survivors: tuple[Process, ...] = ()


@dataclass(frozen=True)
class Runtime:
    """The three effectful seams, bundled so a test substitutes all of them.

    Reading the table, sending a signal and waiting are the only things this
    module does to the world, so they travel together: a caller that overrides
    one almost always overrides the rest, and a test that overrides all three
    drives the destructive path without a single real signal.
    """

    runner: Callable[[Sequence[str]], str] | None = None
    killer: Callable[[int, int], None] = os.kill
    sleeper: Callable[[float], None] = time.sleep


@dataclass(frozen=True)
class Escalation:
    """The signal ladder: what to send first, what to send to survivors."""

    first: int = signal.SIGTERM
    second: int | None = signal.SIGKILL
    grace_s: float = DEFAULT_GRACE_S

    @classmethod
    def from_name(cls, name: str, *, grace_s: float = DEFAULT_GRACE_S) -> Escalation:
        """``TERM`` escalates to KILL; ``KILL`` has nothing left to escalate to."""
        if name.upper() == "KILL":
            return cls(first=signal.SIGKILL, second=None, grace_s=grace_s)
        return cls(first=signal.SIGTERM, second=signal.SIGKILL, grace_s=grace_s)


def reap(
    selection: Selection,
    *,
    runtime: Runtime | None = None,
    escalation: Escalation | None = None,
) -> ReapResult:
    """TERM the confirmed targets, then KILL whatever is still alive."""
    runtime = Runtime() if runtime is None else runtime
    escalation = Escalation() if escalation is None else escalation
    fresh = snapshot(runtime.runner)
    targets, dropped = confirm_targets(
        selection.targets, fresh, protected=selection.protected_set
    )
    signalled = _signal_all(targets, escalation.first, runtime.killer)
    if escalation.second is None or not signalled:
        return ReapResult(signalled=signalled, dropped=dropped)
    runtime.sleeper(escalation.grace_s)
    after = snapshot(runtime.runner)
    survivors, _ = confirm_targets(signalled, after, protected=selection.protected_set)
    killed = _signal_all(survivors, escalation.second, runtime.killer)
    remaining, _ = confirm_targets(
        killed, snapshot(runtime.runner), protected=selection.protected_set
    )
    return ReapResult(
        signalled=signalled, dropped=dropped, killed=killed, survivors=remaining
    )


def _signal_all(
    targets: Iterable[Process],
    sig: int,
    killer: Callable[[int, int], None],
) -> tuple[Process, ...]:
    """Signal each target, tolerating the ones that exited on their own."""
    sent: list[Process] = []
    for process in targets:
        try:
            killer(process.pid, sig)
        except (ProcessLookupError, PermissionError) as exc:
            logger.warning("could not signal %s: %s", process.pid, exc)
            continue
        sent.append(process)
    return tuple(sent)


@dataclass(frozen=True)
class ReapRequest:
    """What the operator asked for — one object, so the CLI seam stays narrow.

    ``kill`` defaults to false because that is the posture: the plan is free
    and the signal is not.
    """

    pattern: str
    min_age_s: int = DEFAULT_MIN_AGE_S
    kill: bool = False
    full_match: bool = False
    signal_name: str = "TERM"
    grace_s: float = DEFAULT_GRACE_S
    strict: bool = False


def reap_main(
    request: ReapRequest,
    *,
    runtime: Runtime | None = None,
    self_pid: int | None = None,
) -> int:
    """CLI entry: print the plan; signal only when ``request.kill`` is true.

    Exit codes: ``0`` fine, ``1`` targets found in dry-run under ``strict`` (or
    survivors after KILL), ``2`` the process table could not be read.

    ``self_pid`` exists because a mutation proved it had to: deleting the
    ``protected=`` argument from the :func:`select` call below broke **no
    test** — every protection test drove :func:`select` directly, so the wiring
    on the path a user actually invokes was unasserted. Injecting the pid makes
    the CLI path testable, and that mutation now fails
    (``test_the_cli_path_protects_the_ancestor_chain``).
    """
    runtime = Runtime() if runtime is None else runtime
    try:
        processes = snapshot(runtime.runner)
    except ReapError:
        logger.exception("reap could not run")
        return 2
    escalation = Escalation.from_name(request.signal_name, grace_s=request.grace_s)
    selection = select(
        processes,
        pattern=request.pattern,
        min_age_s=request.min_age_s,
        protected=protected_pids(processes, self_pid=self_pid),
        full_match=request.full_match,
    )
    logger.info(
        "%s",
        format_plan(selection, pattern=request.pattern, min_age_s=request.min_age_s),
    )
    if not request.kill:
        logger.info(
            "DRY RUN — nothing was signalled. Re-run with `--kill` to signal the "
            "%d target(s) above.",
            len(selection.targets),
        )
        return 1 if request.strict and selection.targets else 0
    if not selection.targets:
        logger.info("nothing to reap.")
        return 0
    try:
        result = reap(selection, runtime=runtime, escalation=escalation)
    except ReapError:
        logger.exception("reap aborted before signalling")
        return 2
    logger.info(
        "reaped: %d signalled with %s, %d escalated to KILL, %d dropped as "
        "changed identity, %d still alive.",
        len(result.signalled),
        signal.Signals(escalation.first).name,
        len(result.killed),
        len(result.dropped),
        len(result.survivors),
    )
    for process in result.survivors:
        logger.warning("still alive after KILL: %s", process.describe())
    return 1 if result.survivors else 0
