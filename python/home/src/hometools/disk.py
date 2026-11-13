"""disk-watch: alert when the home volume runs low, naming the processes that hold deleted files open."""

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from .models import DiskAlert, DiskCheck, DiskHolder, DiskState

GB = 1_000_000_000
MIN_FREE = 100 * GB
EVERY = 15 * 60
# While the volume stays low, the alert repeats this often; a check back above the line clears it.
REPEAT = 4 * 60 * 60
TOP = 5
# lsof and osascript get this long; the watch goes on without them rather than stall.
TIMEOUT = 60
# Under HOME. The state keeps the last alert time, so a restart does not repeat it early. The alert file is how
# chief-of-staff hears of it: a background session with no terminal, reached by Claude only through SendMessage,
# which this service cannot call, so its check-in reads the file instead (chief-of-staff's identity ruling).
FOLDER = ".local/state/dotfiles/disk-watch"
STATE = f"{FOLDER}/state.json"
ALERT = f"{FOLDER}/alert.json"


def read(*argv: str) -> str | None:
    """argv's stdout; None when it can't start, exits non-zero or runs past TIMEOUT."""
    try:
        done = subprocess.run(
            argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, timeout=TIMEOUT
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    return done.stdout if done.returncode == 0 else None


def holders(listing: str | None) -> list[DiskHolder]:
    """The biggest holders in `lsof -nP +L1 -F pcs`: deleted files still open, summed per process."""
    sizes: dict[int, DiskHolder] = {}
    pid, command = 0, ""
    for line in (listing or "").splitlines():
        tag, value = line[:1], line[1:]
        if tag == "p":
            pid, command = int(value), ""
        elif tag == "c":
            command = value
        elif tag == "s" and pid:
            held = sizes.get(pid, DiskHolder(pid=pid, command=command, bytes=0))
            sizes[pid] = held.model_copy(update={"bytes": held.bytes + int(value)})
    return sorted(sizes.values(), key=lambda h: h.bytes, reverse=True)[:TOP]


def plain(name: str) -> str:
    """A process name with only letters, digits, space and ._+- kept: any program can name itself, and the
    alert's text is shown by osascript and read by an agent."""
    return "".join(c if c.isascii() and (c.isalnum() or c in " ._+-") else "_" for c in name)


def message(free: int, min_free: int, held: list[DiskHolder]) -> str:
    """The alert's text: plain words only."""
    names = ", ".join(f"{plain(h.command)} pid {h.pid} {h.bytes // GB} GB" for h in held) or "none found"
    low = f"disk-watch: {free // GB} GB free on the home volume, below {min_free // GB} GB."
    return f"{low} Deleted files held open: {names}"


def notify(text: str) -> bool:
    """A macOS notification; False where osascript is missing or fails (Linux)."""
    if shutil.which("osascript") is None:
        return False
    script = f"display notification {json.dumps(text)} with title {json.dumps('Disk low')}"
    return read("osascript", "-e", script) is not None


def publish(alert: Path, data: DiskAlert) -> bool:
    """The alert file, written to a temporary file and renamed so a reader never sees half of it. False when it
    can't be written: on a full disk the watch still posts the notification and keeps running."""
    partial = alert.with_name(f".{alert.name}.{os.getpid()}")
    try:
        alert.parent.mkdir(parents=True, exist_ok=True)
        partial.write_text(data.model_dump_json())
        partial.replace(alert)
    except OSError:  # no space, or the folder is not writable
        partial.unlink(missing_ok=True)
        return False
    return True


def load(state: Path) -> DiskState:
    """The saved state; a missing or unreadable file means no alert went out yet."""
    try:
        return DiskState.model_validate_json(state.read_text())
    except OSError, ValueError:
        return DiskState(alerted_at=None)


def check(min_free: int = MIN_FREE, now: Callable[[], float] = time.time) -> DiskCheck:
    """One check: below min_free, alert unless one went out in the last REPEAT seconds."""
    state, alert = Path.home() / STATE, Path.home() / ALERT
    free = shutil.disk_usage(Path.home()).free
    last = load(state).alerted_at
    if free >= min_free:
        alerted_at, held, told = None, [], []
        alert.unlink(missing_ok=True)
    else:
        held = holders(read("lsof", "-nP", "+L1", "-F", "pcs"))
        due = last is None or now() - last >= REPEAT
        alerted_at, told = last, []
        if due:
            alerted_at, text = now(), message(free, min_free, held)
            data = DiskAlert(at=alerted_at, free_bytes=free, min_free_bytes=min_free, holders=held, text=text)
            sent = (("alert-file", lambda: publish(alert, data)), ("notification", lambda: notify(text)))
            told = [who for who, send in sent if send()]
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(DiskState(alerted_at=alerted_at).model_dump_json())
    except OSError:  # a full disk: keep running and alert again next check rather than crash and restart
        pass
    return DiskCheck(free_bytes=free, min_free_bytes=min_free, alert=bool(told), holders=held, told=told)


def watch(every: int = EVERY, checks: int = 0, min_free: int = MIN_FREE) -> None:
    """Check every `every` seconds, one JSON line each; stop after `checks` of them (0: never)."""
    done = 0
    while True:
        sys.stdout.write(check(min_free=min_free).model_dump_json() + "\n")
        sys.stdout.flush()
        done += 1
        if done == checks:
            return
        time.sleep(every)


def main() -> None:
    """DISK_WATCH_CHECKS, DISK_WATCH_EVERY and DISK_WATCH_MIN_FREE_GB let a test run a few quick checks."""
    watch(
        every=int(os.environ.get("DISK_WATCH_EVERY", str(EVERY))),
        checks=int(os.environ.get("DISK_WATCH_CHECKS", "0")),
        min_free=int(os.environ.get("DISK_WATCH_MIN_FREE_GB", str(MIN_FREE // GB))) * GB,
    )
