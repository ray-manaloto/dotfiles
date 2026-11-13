"""disk-snapshot and disk-guard: find what fills the data volume, and keep heavy test tasks off a nearly full one.

disk-snapshot runs from monit's low-space rule (unix/home/.config/mise/config.toml, the monitrc entry). On
2026-11-13 the volume fell from about 315 GiB to 42 GiB free and was back within minutes, and nothing recorded what
had written it. So each run writes one new folder under ~/.local/state/dotfiles/disk-alerts:

- du.txt: the biggest folders, two levels down, under each root in ROOTS, every root measured at once and each
  stopped at its time limit (a timed-out root keeps the lines du printed so far);
- ps.txt: every process, highest CPU first;
- lsof.txt: regular files of 1 GiB or more held open, and files deleted while still open (lsof +L1): a
  write-then-delete shows there while the writer runs.

It never deletes anything and never writes into an existing folder. A lock keeps two runs from overlapping: a second
run while one is going prints a null folder and exits 0, since monit may fire again before the first ends.

disk-guard exits 1 when the data volume has less than FLOOR_GIB free, so the heavy test tasks that depend on it
(//python:test and //p2996:test, and so hk check --all) stop before they start.
"""

import contextlib
import fcntl
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Generator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .models import DiskGuard, DiskSnapshot, Failure

DATA = "/System/Volumes/Data"
# monit's alert threshold (100 GB in monitrc, and monit's GB is 1024^3).
FLOOR_GIB = 100
GIB = 1 << 30
# Each command's time limit: du per root, ps and each lsof. All roots run at once, so a run takes about this long.
SECONDS = 60
DU_LINES = 40
PS_LINES = 80
LSOF_LINES = 200
BIG = GIB


def free_gib(path: str = DATA) -> int:
    """Space a normal user can still write (f_bavail), in GiB, as monit counts space free on macOS."""
    found = os.statvfs(path)
    return found.f_bavail * found.f_frsize // GIB


def guard(floor: int | None = None, path: str = DATA) -> DiskGuard:
    floor = FLOOR_GIB if floor is None else floor
    free = free_gib(path)
    if free < floor:
        msg = (
            f"disk-guard: {path} has {free} GiB free, under the {floor} GiB floor. Heavy test runs write and delete "
            f"tens of GiB at a time, and the volume fell to 42 GiB free on 2026-11-13; free space first "
            f"(mise run disk:snapshot shows the biggest folders) or run a focused test."
        )
        raise ValueError(msg)
    return DiskGuard(free_gib=free, floor_gib=floor)


def roots() -> list[Path]:
    """Where the space went on this Mac before: caches, tool installs, state, checkouts and temporary folders."""
    home = Path.home()
    mine = [".cache", "Library/Caches", ".local/share", ".local/state", "dev", "Library/Containers", ".tart"]
    temporary = Path(os.environ.get("TMPDIR") or tempfile.gettempdir())
    return [home / name for name in mine] + [temporary, Path("/private/tmp")]


def output() -> Path:
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return state / "dotfiles/disk-alerts"


def bounded(argv: Sequence[str], seconds: float) -> tuple[str, bool]:
    """argv's stdout, or what it printed before its time limit, and whether the limit stopped it."""
    with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace") as proc:
        try:
            out, _ = proc.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            return out, True
    return out, False


def du(root: Path, seconds: float) -> tuple[str, bool]:
    """root's biggest folders, two levels down, largest first, in GiB with one decimal."""
    if not root.is_dir():
        return f"== {root}: not a folder\n", False
    out, stopped = bounded(["du", "-xk", "-d", "2", str(root)], seconds)
    sizes = []
    lines = out.splitlines()
    # du stopped mid-line leaves a cut last line: its size may be cut short too, so it is dropped.
    for line in lines[:-1] if stopped else lines:
        # A line du was writing when it was stopped still starts with its whole size.
        kib, _, name = line.partition("\t")
        # A folder name with a newline in it leaves a fragment with no size: skipped.
        if kib.isdigit():
            sizes.append((int(kib), name))
    # Largest first; on a tie the enclosing folder, the shorter path, comes first.
    sizes.sort(key=lambda item: (-item[0], item[1]))
    note = " (stopped at its time limit: partial)" if stopped else ""
    lines = [f"{kib / (1 << 20):8.1f} GiB  {name}" for kib, name in sizes[:DU_LINES]]
    return f"== {root}{note}\n" + "".join(f"{line}\n" for line in lines), stopped


def big_open(lsof: str) -> list[str]:
    """Regular files of BIG or more in lsof -F pcnst output: one line each, pid and command first.

    lsof -F prints a process set (p, c) and then one file set per open file, each starting with its descriptor (f);
    a file set has no s field when lsof has no size for it (a pipe or socket), so each f starts a file afresh.
    """
    found, pid, command, kind, size = [], "", "", "", 0
    for field in lsof.splitlines():
        tag, value = field[:1], field[1:]
        if tag == "p":
            pid = value
        elif tag == "c":
            command = value
        elif tag == "f":
            kind, size = "", 0
        elif tag == "t":
            kind = value
        elif tag == "s":
            size = int(value)
        elif tag == "n" and kind == "REG" and size >= BIG:
            found.append((size, f"{size / GIB:8.1f} GiB  pid {pid} {command}  {value}"))
    # One line per process and file: a file held on several descriptors is listed once.
    return [line for _, line in sorted(set(found), reverse=True)]


@contextlib.contextmanager
def locked(folder: Path) -> Generator[bool]:
    """True while this run holds the snapshot lock; False when another run has it."""
    with (folder / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def fresh(parent: Path, stamp: str | None = None) -> Path:
    """A new folder named by the UTC time; a second run in the same second gets -2, -3, and so on."""
    stamp = stamp or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    for n in range(1, 1000):
        folder = parent / (stamp if n == 1 else f"{stamp}-{n}")
        try:
            folder.mkdir(mode=0o700)
        except FileExistsError:
            continue
        return folder
    msg = f"{parent}: 999 snapshots in one second"
    raise FileExistsError(msg)


def snapshot(parent: Path, where: Sequence[Path], seconds: float | None = None, data: str = DATA) -> DiskSnapshot:
    seconds = SECONDS if seconds is None else seconds
    # ps.txt holds whole command lines: the folders are the user's alone.
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with locked(parent) as mine:
        if not mine:
            return DiskSnapshot(folder=None, timed_out=[])
        folder = fresh(parent)
        (folder / "free.txt").write_text(f"{data}: {free_gib(data)} GiB free\n")
        with ThreadPoolExecutor(max_workers=len(where) + 3) as pool:
            sizes = [pool.submit(du, root, seconds) for root in where]
            ps = pool.submit(bounded, ["ps", "-Ao", "pid,ppid,etime,%cpu,rss,command", "-r"], seconds)
            files = pool.submit(bounded, ["lsof", "-nP", "-F", "pcnst", data], seconds)
            unlinked = pool.submit(bounded, ["lsof", "-nP", "+L1"], seconds)
            measured = [future.result() for future in sizes]
            (folder / "du.txt").write_text("".join(text for text, _ in measured))
            (folder / "ps.txt").write_text("".join(f"{line}\n" for line in ps.result()[0].splitlines()[:PS_LINES]))
            big = big_open(files.result()[0])[:LSOF_LINES]
            gone = unlinked.result()[0].splitlines()[:LSOF_LINES]
            (folder / "lsof.txt").write_text(
                f"== open regular files of {BIG // GIB} GiB or more\n"
                + "".join(f"{line}\n" for line in big)
                + "== deleted while still open (lsof +L1)\n"
                + "".join(f"{line}\n" for line in gone)
            )
        late = [str(root) for root, (_, stopped) in zip(where, measured, strict=True) if stopped]
        return DiskSnapshot(folder=str(folder), timed_out=late)


def run_snapshot() -> None:
    sys.stdout.write(snapshot(output(), roots()).model_dump_json() + "\n")


def run_guard() -> None:
    try:
        sys.stdout.write(guard().model_dump_json() + "\n")
    except ValueError as low:
        sys.stderr.write(Failure(error=str(low)).model_dump_json() + "\n")
        raise SystemExit(1) from None
