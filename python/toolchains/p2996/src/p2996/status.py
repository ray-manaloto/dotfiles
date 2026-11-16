"""p2996 status: each build tree's ninja progress, read from ninja's own files without running ninja."""

import calendar
import json
import os
import time
from pathlib import Path

from . import proc
from .config import build_tree
from .log import P2996Error, log
from .models import Config, Status

MS = 1_000_000  # ns
# The main tree, then the nested builds LLVM runs inside one of its steps each.
TREES = {"build": Path(), "builtins": Path("runtimes/builtins-bins"), "runtimes": Path("runtimes/runtimes-bins")}


async def running() -> dict[str, int]:
    """Each folder a ninja process runs in (cmake --build starts it there), with its start in ns since the epoch."""
    # lsof exits 1 when no ninja runs.
    found = (await proc.run("lsof", "-a", "-c", "ninja", "-d", "cwd", "-Fpn", check=False)).stdout.decode()
    folders: dict[str, str] = {}
    pid = ""
    for line in found.splitlines():
        if line.startswith("p"):
            pid = line[1:]
        elif line.startswith("n"):
            folders[pid] = line[1:]
    if not folders:
        return {}
    # A ninja that ended since lsof saw it is missing here; ps then exits 1 and lists the others.
    env = os.environ | {"LC_ALL": "C", "TZ": "UTC"}
    listed = await proc.run("ps", "-o", "pid=,lstart=", "-p", ",".join(folders), env=env, check=False)
    starts: dict[str, int] = {}
    for line in listed.stdout.decode().splitlines():
        pid, lstart = line.split(maxsplit=1)
        lstart = lstart.strip()  # ps pads the column.
        # Whole seconds: the floor of when that ninja started, so before its run's clock started.
        at = calendar.timegm(time.strptime(lstart, "%a %b %d %H:%M:%S %Y")) * 1000 * MS
        starts[folders[pid]] = min(at, starts.get(folders[pid], at))
    return starts


def report(name: str, tree: Path, starts: dict[str, int]) -> None:
    # lsof names the folder as the file system resolves it.
    started = starts.get(os.path.realpath(tree))
    ninja_log = tree / ".ninja_log"
    # After the version line: start and end ms from the run's start, mtime, output, command hash; one line per
    # output of a step. Recompaction rewrites old lines in any order, so nothing here reads their order.
    # A record ninja is still writing has no newline yet, or too few fields: skipped, as ninja's own reader does
    # (ninja v1.13.2 src/build_log.cc:247-280).
    records = [line.split("\t") for line in ninja_log.read_text().split("\n")[1:-1]]
    lines = [line for line in records if len(line) == 5]  # noqa: PLR2004 - start, end, mtime, output, hash
    if started is not None:
        # A line's mtime is the wall clock in ns as its step started, or, for a restat step whose outputs changed,
        # their later mtime (ninja v1.13.2 src/build.cc:833-849, 916-948), so mtime less start is its run's start
        # or later. This run's lines: at or after the process started, less 1 ms plus 1000 ppm of the step's
        # start for a wall clock slewed against ninja's steady clock. Earlier runs started before it.
        lines = [line for line in lines if int(line[2]) - int(line[0]) * MS >= started - MS - int(line[0]) * MS // 1000]
    log.info(
        "tree status",
        tree=name,
        path=str(tree),
        running=started is not None,
        # Outputs this run has built, or every output a finished tree's builds have logged; a step can have several.
        outputs=len({line[3] for line in lines}),
        # The output of this run's step that ended last: one run's end times share one clock.
        last=max(lines, key=lambda line: int(line[1]))[3] if started is not None and lines else None,
        # Seconds since ninja last wrote its log here: a step ending, or a recompaction as a run starts.
        idle_s=round(time.time() - ninja_log.stat().st_mtime),
    )


async def run(cfg: Config, _: Status) -> None:
    # No ninja here, not even a dry run (README, Nothing else runs ninja in the build folder).
    top = build_tree(cfg)
    if not (top / ".ninja_log").is_file():
        msg = f"p2996 status: no ninja log in {top}; mise run //p2996:build starts one"
        raise P2996Error(msg)
    starts = await running()
    for name, folder in TREES.items():
        tree = top / folder
        if (tree / ".ninja_log").is_file():
            report(name, tree, starts)
    # --show-stats reads a running server and starts none (sccache v0.19.0 src/commands.rs:806-813).
    stats = json.loads(
        await proc.output(await proc.output("mise", "which", "sccache"), "--show-stats", "--stats-format=json")
    )["stats"]
    log.info(
        "sccache stats",
        compile_requests=stats["compile_requests"],
        hits=sum(stats["cache_hits"]["counts"].values()),
        misses=sum(stats["cache_misses"]["counts"].values()),
        compile_fails=stats["compile_fails"],
        cache_write_errors=stats["cache_write_errors"],
    )
