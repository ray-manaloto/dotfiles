# Copyright (c) 2026 Raymond Manaloto
"""Host-wide advisory locks: one heavy gate at a time, one command-audit at a time.

Every clone, worktree and background session on this Mac shares one CPU budget.
Before this module "one heavy run at a time" was advisory prose only: on
2026-10-02 two concurrent suites plus seven SessionEnd transcript scans drove the
load average to 128 and turned a 57 s knowledge-base test run into ~13 minutes
(`docs/research/kb/reports/agents/host-load-review-2026-10-02.md`).

The primitive is ``fcntl.flock`` on a file at a WELL-KNOWN path, so every
checkout serialises against every other one — a per-checkout path would only
serialise a clone against itself. The kernel drops the lock when the holding
descriptor closes, which includes the holder crashing or being killed, so a
dead holder can never wedge the host. The same pattern guards the codex lane
directory (``codex_lane.prepare_lane_run``).

Two properties are deliberate:

- **Bounded wait, loudly.** A waiter prints which pid/command holds the lock and
  gives up after ``DOTFILES_HEAVY_GATE_WAIT`` seconds (default one hour) with
  :class:`HostLockTimeoutError`, never silently and never forever
  (`long-running-command-hangs.md`).
- **Re-entrant for descendants.** ``mise run ship`` holds the heavy-gate lock
  across ``git push``, and that push runs the pre-push suite, which takes the
  same lock. The holder exports its pid in :func:`holder_env_name`; a descendant
  that finds the lock busy AND recorded under that same pid is running inside
  the holder and proceeds. A stale export cannot unlock anything: if the lock is
  actually free the descendant simply acquires it.

Scope: ONE filesystem. Inside the devcontainer the default path is on the
container's own home volume, so container runs do not queue against host runs
even though they share the CPU (cold review 2026-10-02, finding 11).

``DOTFILES_LOCK_DIR`` relocates every lock (the test suite points it at a
per-test directory so tests never contend with a real gate on the host).
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import math
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

__all__ = [
    "COMMAND_AUDIT",
    "HEAVY_GATE",
    "HostLockTimeoutError",
    "held",
    "holder_env_name",
    "host_lock_main",
    "inherited_heavy_lock_fd",
    "lock_path",
    "read_holder",
]

HEAVY_GATE = "heavy-gate"
COMMAND_AUDIT = "command-audit"

LOCK_DIR_ENV = "DOTFILES_LOCK_DIR"
LOCK_FD_ENV = "DOTFILES_HEAVY_GATE_FD"
WAIT_ENV = "DOTFILES_HEAVY_GATE_WAIT"
DEFAULT_WAIT_S = 3600.0
_MIN_CHILD_FD = 3
_POLL_S = 1.0
_REMIND_EVERY_S = 60.0


class HostLockTimeoutError(RuntimeError):
    """The lock stayed held by someone else for the whole bounded wait."""


def lock_dir() -> Path:
    """The directory every host lock lives in (``$XDG_STATE_HOME/dotfiles``)."""
    if explicit := os.environ.get(LOCK_DIR_ENV):
        return Path(explicit)
    xdg = os.environ.get("XDG_STATE_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "state") / "dotfiles"


def lock_path(name: str) -> Path:
    """The lock file for ``name``."""
    return lock_dir() / f"{name}.lock"


def holder_env_name(name: str) -> str:
    """The variable a holder exports so its descendants can re-enter."""
    return "DOTFILES_LOCK_HOLDER_" + name.upper().replace("-", "_")


def inherited_heavy_lock_fd() -> int | None:
    """Validate the live inherited heavy-lock descriptor for a nested child."""
    raw = os.environ.get(LOCK_FD_ENV)
    if raw is None:
        return None
    if not raw.isdecimal() or int(raw) < _MIN_CHILD_FD:
        msg = "invalid inherited heavy-gate descriptor"
        raise RuntimeError(msg)
    descriptor = int(raw)
    try:
        opened = os.fstat(descriptor)
        expected = lock_path(HEAVY_GATE).stat()
    except OSError as exc:
        msg = "inherited heavy-gate descriptor is not live"
        raise RuntimeError(msg) from exc
    if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino):
        msg = "inherited heavy-gate descriptor targets another file"
        raise RuntimeError(msg)
    return descriptor


def default_wait_s() -> float:
    """``DOTFILES_HEAVY_GATE_WAIT`` seconds, or one hour."""
    raw = os.environ.get(WAIT_ENV, "")
    try:
        value = float(raw) if raw else DEFAULT_WAIT_S
    except ValueError:
        return DEFAULT_WAIT_S
    # `nan`/`inf` parse as floats and would make the bounded wait unbounded.
    return value if math.isfinite(value) else DEFAULT_WAIT_S


def read_holder(name: str) -> str:
    """The holder record (``pid<TAB>label<TAB>since``), or ``""`` when none."""
    try:
        return lock_path(name).read_text().strip()
    except OSError:
        return ""


def _holder_pid(record: str) -> str:
    return record.split("\t", 1)[0] if record else ""


def _try_lock(fd: int) -> bool:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


def _describe(record: str) -> str:
    pid, _, rest = record.partition("\t")
    label, _, since = rest.partition("\t")
    if since:
        return f"pid {pid} ({label}, since {since})"
    return record or "an unknown holder"


@contextlib.contextmanager
def held(
    name: str,
    label: str,
    *,
    wait_s: float | None = None,
    out: TextIO | None = None,
) -> Iterator[int | None]:
    """Hold host lock ``name`` for the duration of the block.

    Yields the locked descriptor, or None when re-entering an ancestor's hold.
    Pass it to a child (``pass_fds``) so the lock outlives a killed parent:
    flock belongs to the open file description, and the kernel releases it
    only when EVERY descriptor sharing it is closed.

    Args:
        name: Which lock (:data:`HEAVY_GATE`, :data:`COMMAND_AUDIT`).
        label: What this holder is doing; shown to anyone who waits on it.
        wait_s: Seconds to wait for a busy lock; ``0`` means do not wait.
            Defaults to :func:`default_wait_s`.
        out: Where the waiting notice goes (default stderr).

    Raises:
        HostLockTimeoutError: the lock stayed busy for the whole wait.
    """
    stream = sys.stderr if out is None else out
    budget = default_wait_s() if wait_s is None else wait_s
    if not math.isfinite(budget):
        budget = DEFAULT_WAIT_S
    path = lock_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    env_name = holder_env_name(name)
    # "a", never "w": "w" truncates on open, zeroing the record of a process
    # that already holds the lock (flock is advisory) — codex_lane's reasoning.
    with path.open("a+") as handle:
        fd = handle.fileno()
        if not _try_lock(fd):
            record = read_holder(name)
            inherited = os.environ.get(env_name, "")
            if inherited and inherited == _holder_pid(record):
                # Busy, and held by the process we descend from: re-enter.
                yield None
                return
            _wait_for(fd, name, budget, stream)
        handle.seek(0)
        handle.truncate()
        since = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        handle.write(f"{os.getpid()}\t{label}\t{since}\n")
        handle.flush()
        previous = os.environ.get(env_name)
        previous_fd = os.environ.get(LOCK_FD_ENV) if name == HEAVY_GATE else None
        os.environ[env_name] = str(os.getpid())
        if name == HEAVY_GATE:
            os.environ[LOCK_FD_ENV] = str(fd)
        try:
            yield fd
        finally:
            if previous is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = previous
            if name == HEAVY_GATE:
                if previous_fd is None:
                    os.environ.pop(LOCK_FD_ENV, None)
                else:
                    os.environ[LOCK_FD_ENV] = previous_fd
            fcntl.flock(fd, fcntl.LOCK_UN)


def _wait_for(fd: int, name: str, budget: float, stream: TextIO) -> None:
    """Poll the busy lock until it frees or ``budget`` seconds pass."""
    if budget <= 0:
        msg = f"{name} lock is held by {_describe(read_holder(name))}"
        raise HostLockTimeoutError(msg)
    started = time.monotonic()
    stream.write(
        f"==> waiting for {name} lock held by {_describe(read_holder(name))} "
        f"(up to {budget:.0f}s; {lock_path(name)})\n"
    )
    stream.flush()
    next_reminder = started + _REMIND_EVERY_S
    while True:
        now = time.monotonic()
        if now - started >= budget:
            msg = (
                f"{name} lock still held by {_describe(read_holder(name))} after "
                f"{budget:.0f}s ({lock_path(name)})"
            )
            raise HostLockTimeoutError(msg)
        time.sleep(min(_POLL_S, max(budget - (now - started), 0.0)))
        if _try_lock(fd):
            waited = time.monotonic() - started
            stream.write(f"==> {name} lock acquired after {waited:.0f}s\n")
            stream.flush()
            return
        if time.monotonic() >= next_reminder:
            stream.write(
                f"==> still waiting for {name} lock "
                f"({time.monotonic() - started:.0f}s): "
                f"{_describe(read_holder(name))}\n"
            )
            stream.flush()
            next_reminder += _REMIND_EVERY_S


def host_lock_main(argv: Sequence[str] | None = None) -> int:
    """``dotfiles-setup heavy-gate {run,status}`` — the CLI the hooks reach.

    ``run [--label L] [--wait S] -- CMD...`` runs CMD under the heavy-gate lock
    and returns its exit code, or 124 when the wait expired. ``status`` prints
    the current holder record (rc 0) or ``free`` (rc 1).
    """
    parser = argparse.ArgumentParser(prog="dotfiles-setup heavy-gate")
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="Run a command under the heavy-gate lock")
    run.add_argument("--label", default="")
    run.add_argument("--wait", type=float, default=None)
    run.add_argument("command", nargs=argparse.REMAINDER)
    sub.add_parser("status", help="Print the current heavy-gate holder")
    args = parser.parse_args(argv)
    if args.action == "status":
        path = lock_path(HEAVY_GATE)
        busy = path.is_file() and not _probe_free(path)
        sys.stdout.write((read_holder(HEAVY_GATE) if busy else "free") + "\n")
        return 0 if busy else 1
    command = list(args.command[1:] if args.command[:1] == ["--"] else args.command)
    if not command:
        parser.error("a command is required after --")
    label = args.label or " ".join(command)[:120]
    try:
        with held(HEAVY_GATE, label, wait_s=args.wait) as fd:
            effective_fd = fd if fd is not None else inherited_heavy_lock_fd()
            fds = () if effective_fd is None else (effective_fd,)
            return subprocess.run(command, check=False, pass_fds=fds).returncode
    except HostLockTimeoutError as exc:
        sys.stderr.write(f"FAIL  {exc}\n")
        return 124


def _probe_free(path: Path) -> bool:
    """Whether nobody holds ``path`` right now (takes and drops it at once)."""
    with path.open("a+") as handle:
        if _try_lock(handle.fileno()):
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            return True
    return False
