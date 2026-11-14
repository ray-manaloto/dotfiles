"""disk-snapshot, disk-log and disk-guard: find what fills the data volume, and keep heavy tests off a nearly full one.

disk-snapshot runs from monit's low-space rule (unix/home/.config/mise/config.toml, the monitrc entry). On
2026-11-13 the volume fell from about 315 GiB to 42 GiB free and was back within minutes, and nothing recorded what
had written it. So each run writes one new folder under ~/.local/state/dotfiles/disk-alerts:

- folders.txt: the biggest folders, two levels down, under each root in roots(), measured by dust (the Rust du, a
  global mise tool; on ~/.cache it took 17 s where du took 59 s), one root after another and each stopped at its
  time limit. dust is multithreaded and disk-bound: all nine roots at once took 163 s, one after another 111 s.
  dust prints its JSON tree only when it finishes, so a stopped root has no totals;
- ps.txt: every process, highest CPU first;
- lsof.txt: regular files of 1 GiB or more held open, and files deleted while still open (lsof +L1): a
  write-then-delete shows there while the writer runs.

It never deletes anything and never writes into an existing folder. A lock keeps two runs from overlapping: a second
run while one is going prints a null folder and exits 0, since monit may fire again before the first ends.

disk-guard exits 1 when the data volume has less than FLOOR_GIB free, so the heavy test tasks that depend on it
(//python:test and //p2996:test, and so hk check --all) stop before they start.
"""

import contextlib
import ctypes
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Generator, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .models import DiskGuard, DiskSample, DiskSnapshot, Failure, Writer

DATA = "/System/Volumes/Data"
# monit's alert threshold (100 GB in monitrc, and monit's GB is 1024^3). DISK_FLOOR_GIB overrides it for one run.
FLOOR_GIB = 100
GIB = 1 << 30
# Each command's time limit: dust per root, ps and each lsof. The roots run one after another, beside ps and lsof,
# so a run is bounded by len(roots()) * SECONDS: 9 minutes for the nine roots; 111 s measured on 2026-11-13.
# DISK_SNAPSHOT_SECONDS overrides it for one run.
SECONDS = 60
FOLDER_LINES = 40
PS_LINES = 80
LSOF_LINES = 200
BIG = GIB


def free_gib(path: str = DATA) -> int:
    """Space a normal user can still write (f_bavail), in GiB, as monit counts space free on macOS."""
    found = os.statvfs(path)
    return found.f_bavail * found.f_frsize // GIB


def setting(name: str, default: int) -> int:
    """An integer from the environment, or default when it is unset or empty."""
    return int(os.environ.get(name) or default)


def guard(floor: int | None = None, path: str = DATA) -> DiskGuard:
    floor = setting("DISK_FLOOR_GIB", FLOOR_GIB) if floor is None else floor
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
    # The temporary folders first (where a test run writes) and ~/dev last (the slowest, about a minute).
    mine = [".cache", "Library/Caches", ".local/share", ".local/state", "Library/Containers", ".tart", "dev"]
    temporary = Path(os.environ.get("TMPDIR") or tempfile.gettempdir())
    return [temporary, Path("/private/tmp")] + [home / name for name in mine]


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


def flatten(node: dict[str, object]) -> Iterator[tuple[int, str]]:
    """Each folder in dust's JSON tree, with its size in bytes (-o b prints "<n>B")."""
    yield int(str(node["size"]).removesuffix("B")), str(node["name"])
    children = node.get("children")
    for child in children if isinstance(children, list) else []:
        yield from flatten(child)


def inert(name: str) -> str:
    """name as one line of the report: a name with a newline or other control character is JSON-quoted."""
    return name if name.isprintable() else json.dumps(name, ensure_ascii=False)


def ranked(out: str) -> list[str]:
    """dust's JSON tree as report lines, largest first; ValueError, KeyError or TypeError when it isn't one."""
    # Largest first; on a tie the enclosing folder, the shorter path, comes first.
    sizes = sorted(flatten(json.loads(out)), key=lambda item: (-item[0], item[1]))
    return [f"{size / GIB:8.1f} GiB  {inert(name)}" for size, name in sizes[:FOLDER_LINES]]


def biggest(root: Path, seconds: float) -> tuple[str, bool]:
    """root's biggest folders, two levels down, largest first, in GiB with one decimal."""
    if not root.is_dir():
        return f"== {root}: not a folder\n", False
    argv = ["dust", "-x", "-d", "2", "-n", str(FOLDER_LINES), "-p", "-j", "-o", "b", str(root)]
    # One root that dust can't measure (no dust on PATH, an early exit, output that isn't its JSON tree) is named
    # and skipped, so the rest of the snapshot is still written.
    try:
        out, stopped = bounded(argv, seconds)
        if stopped:
            return f"== {root} (stopped at its time limit: no totals)\n", True
        lines = ranked(out)
    except (OSError, ValueError, KeyError, TypeError) as failed:
        return f"== {root}: dust failed ({type(failed).__name__})\n", False
    return f"== {root}\n" + "".join(f"{line}\n" for line in lines), False


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
    limit = setting("DISK_SNAPSHOT_SECONDS", SECONDS) if seconds is None else seconds
    # ps.txt holds whole command lines: the folders are the user's alone.
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with locked(parent) as mine:
        if not mine:
            return DiskSnapshot(folder=None, timed_out=[])
        folder = fresh(parent)
        (folder / "free.txt").write_text(f"{data}: {free_gib(data)} GiB free\n")
        with ThreadPoolExecutor(max_workers=4) as pool:
            sizes = pool.submit(lambda: [biggest(root, limit) for root in where])
            ps = pool.submit(bounded, ["ps", "-Ao", "pid,ppid,etime,%cpu,rss,command", "-r"], limit)
            files = pool.submit(bounded, ["lsof", "-nP", "-F", "pcnst", data], limit)
            unlinked = pool.submit(bounded, ["lsof", "-nP", "+L1"], limit)
            measured = sizes.result()
            (folder / "folders.txt").write_text("".join(text for text, _ in measured))
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


# disk-log: one line a minute from monit (the monitrc entry), so a drop that is back within minutes still shows
# when it happened and which process wrote it. macOS counts each process's bytes written to disk since it started
# (proc_pid_rusage with RUSAGE_INFO_V2, as sysinfo's src/unix/apple/macos/process.rs reads it), and a user can read
# the counters of their own processes without root. A process that starts and exits between two lines is not
# counted, so a drop of DROP_GIB or more also starts disk-snapshot, which names open and deleted-but-open files.
DROP_GIB = 20
WRITERS = 8
MIB = 1 << 20
LOG_BYTES = 20 << 20
LIBPROC = "/usr/lib/libproc.dylib"
RUSAGE_INFO_V2 = 2
PATH_BYTES = 4096
SNAPSHOT = (sys.executable, "-c", "from hometools.cli import main; main(['disk-snapshot'])")
RUSAGE_FIELDS = (
    "user_time system_time pkg_idle_wkups interrupt_wkups pageins wired_size resident_size phys_footprint "
    "proc_start_abstime proc_exit_abstime child_user_time child_system_time child_pkg_idle_wkups "
    "child_interrupt_wkups child_pageins child_elapsed_abstime diskio_bytesread diskio_byteswritten"
)


class RusageInfoV2(ctypes.Structure):
    """struct rusage_info_v2 from <sys/resource.h>: a uuid, then 18 uint64 fields."""

    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(name, ctypes.c_uint64) for name in RUSAGE_FIELDS.split()]


def written() -> dict[str, tuple[int, int, str]]:
    """Each readable process's (pid, bytes written since it started, executable), keyed pid:start time so that a
    reused pid counts as a new process. Another user's processes (root's) are refused by macOS and left out."""
    lib = ctypes.CDLL(LIBPROC)
    room = lib.proc_listallpids(None, 0) * 2
    pids = (ctypes.c_int * room)()
    count = lib.proc_listallpids(pids, ctypes.sizeof(pids))
    found = {}
    for pid in pids[:count]:
        usage = RusageInfoV2()
        if lib.proc_pid_rusage(pid, RUSAGE_INFO_V2, ctypes.byref(usage)) != 0:
            continue
        path = ctypes.create_string_buffer(PATH_BYTES)
        lib.proc_pidpath(pid, path, PATH_BYTES)
        key = f"{pid}:{usage.proc_start_abstime}"
        found[key] = (pid, usage.diskio_byteswritten, path.value.decode(errors="replace"))
    return found


def writers(before: dict[str, int], now: dict[str, tuple[int, int, str]]) -> list[Writer]:
    """The WRITERS processes that wrote the most since before, and at least 1 MiB; most first."""
    grown = [(total - before.get(key, 0), pid, path) for key, (pid, total, path) in now.items()]
    top = sorted((item for item in grown if item[0] >= MIB), key=lambda item: (-item[0], item[1]))[:WRITERS]
    return [Writer(pid=pid, path=path, written_mib=size // MIB) for size, pid, path in top]


def spawn(argv: Sequence[str] = SNAPSHOT) -> None:
    """Start argv in its own session and don't wait: a snapshot takes minutes, and monit times a program out."""
    quiet = subprocess.DEVNULL
    subprocess.Popen(argv, stdin=quiet, stdout=quiet, stderr=quiet, start_new_session=True)


def sample(folder: Path, data: str = DATA, snap: Callable[[], None] = spawn) -> DiskSample:
    """Append one DiskSample to folder/samples.jsonl and keep each process's counter in folder/written.json for the
    next run. The log moves to samples.jsonl.1 past LOG_BYTES, about two weeks of lines."""
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    log, counters = folder / "samples.jsonl", folder / "written.json"
    previous = None
    with contextlib.suppress(FileNotFoundError, IndexError, ValueError):
        previous = DiskSample.model_validate_json(log.read_bytes().splitlines()[-1])
    before: dict[str, int] = {}
    with contextlib.suppress(FileNotFoundError, ValueError, AttributeError):
        before = {str(key): int(value) for key, value in json.loads(counters.read_text()).items()}
    now = written()
    free = free_gib(data)
    drop = None if previous is None else previous.free_gib - free
    record = DiskSample(
        at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        free_gib=free,
        drop_gib=drop,
        writers=writers(before, now),
        snapshot=drop is not None and drop >= DROP_GIB,
    )
    if record.snapshot:
        snap()
    if log.exists() and log.stat().st_size > LOG_BYTES:
        log.replace(folder / "samples.jsonl.1")
    with log.open("a") as out:
        out.write(record.model_dump_json() + "\n")
    counters.write_text(json.dumps({key: total for key, (_, total, _) in now.items()}))
    return record


def run_log() -> None:
    sys.stdout.write(sample(output()).model_dump_json() + "\n")
