"""disk-watch: alert when the home volume runs low, naming the processes that hold deleted files open."""

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from .models import DiskCheck, DiskHolder, DiskState

GB = 1_000_000_000
MIN_FREE = 100 * GB
EVERY = 15 * 60
# While the volume stays low, the alert repeats this often; a check back above the line clears it.
REPEAT = 4 * 60 * 60
TOP = 5
# hc send waits while a person has an unsent draft in the box; the watch gives up rather than stall.
TIMEOUT = 60
CHIEF = "chief-of-staff"
# Under HOME, read at each check: the last alert time, so a restart does not repeat it early.
STATE = ".local/state/dotfiles/disk-watch.json"


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
    alert is typed into a terminal (no backticks or angle brackets, owner ruling 2026-11-07)."""
    return "".join(c if c.isascii() and (c.isalnum() or c in " ._+-") else "_" for c in name)


def message(free: int, min_free: int, held: list[DiskHolder]) -> str:
    """The alert's text: plain words only, since it is typed into a terminal and shown by osascript."""
    names = ", ".join(f"{plain(h.command)} pid {h.pid} {h.bytes // GB} GB" for h in held) or "none found"
    low = f"disk-watch: {free // GB} GB free on the home volume, below {min_free // GB} GB."
    return f"{low} Deleted files held open: {names}"


def notify(text: str) -> bool:
    """A macOS notification; False where osascript is missing or fails (Linux)."""
    if shutil.which("osascript") is None:
        return False
    script = f"display notification {json.dumps(text)} with title {json.dumps('Disk low')}"
    return read("osascript", "-e", script) is not None


def hc() -> str:
    """hc from PATH, else ~/.local/bin where Herdr installs it: the service gets launchd's PATH, which lacks it."""
    return shutil.which("hc", path=f"{os.environ.get('PATH', '')}{os.pathsep}{Path.home() / '.local/bin'}") or "hc"


def answer(*argv: str) -> dict:
    """An hc --json call's object; {} when hc fails or prints something else (the watch must outlive a bad hc)."""
    try:
        got = json.loads(read(hc(), *argv) or "{}")
    except ValueError:  # not JSON
        return {}
    return got if isinstance(got, dict) else {}


def chief() -> str | None:
    """The chief-of-staff terminal, only while Claude runs in it: text sent to a shell would run as a command."""
    for terminal in answer("ls", "--json").get("terminals", []):
        if terminal.get("state") == "live" and terminal.get("where") == f"{CHIEF} / {CHIEF}":
            argv = (answer("get", terminal["address"], "--json").get("foreground") or {}).get("argv") or []
            if argv and Path(argv[0]).name == "claude":
                return terminal["address"]
    return None


def tell(text: str) -> bool:
    """The alert sent to chief-of-staff's Claude session; False when it isn't running or the send fails."""
    terminal = chief()
    return terminal is not None and read(hc(), "send", terminal, text) is not None


def load(state: Path) -> DiskState:
    """The saved state; a missing or unreadable file means no alert went out yet."""
    try:
        return DiskState.model_validate_json(state.read_text())
    except OSError, ValueError:
        return DiskState(alerted_at=None)


def check(min_free: int = MIN_FREE, now: Callable[[], float] = time.time) -> DiskCheck:
    """One check: below min_free, alert unless one went out in the last REPEAT seconds."""
    state = Path.home() / STATE
    free = shutil.disk_usage(Path.home()).free
    last = load(state).alerted_at
    if free >= min_free:
        alerted_at, held, told = None, [], []
    else:
        held = holders(read("lsof", "-nP", "+L1", "-F", "pcs"))
        due = last is None or now() - last >= REPEAT
        told = [
            who
            for who, sent in (("notification", notify), (CHIEF, tell))
            if due and sent(message(free, min_free, held))
        ]
        alerted_at = now() if due else last
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(DiskState(alerted_at=alerted_at).model_dump_json())
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
