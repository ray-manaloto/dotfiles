import json
import subprocess
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
import pytest

from p2996 import config, status
from p2996.models import Config, Status

from .conftest import events, fails, tree

pytestmark = pytest.mark.anyio

# The last step waits for a file named go, so a test can read the tree while ninja runs in it.
OUTER = """\
rule run
  command = $cmd
build a: run
  cmd = touch a
build b: run
  cmd = touch b
build c: run
  cmd = touch c
build d: run || c
  cmd = while [ ! -f go ]; do sleep 0.05; done; touch d
"""
NESTED = """\
rule run
  command = $cmd
build x: run
  cmd = touch x
build y: run
  cmd = touch y
"""


def ninja(folder: Path, *args: str) -> None:
    subprocess.run(["ninja", "-C", str(folder), *args], check=True, capture_output=True)


def wait_for_lock(folder: Path) -> None:
    """Block until ninja started a step in folder."""
    deadline = time.monotonic() + 30
    while not (folder / ".ninja_lock").exists():
        assert time.monotonic() < deadline, f"no ninja run in {folder}"
        time.sleep(0.05)


def wait_for(path: Path, text: str) -> None:
    """Block until text is in path: ninja logged that step."""
    deadline = time.monotonic() + 30
    while not path.is_file() or text not in path.read_text():
        assert time.monotonic() < deadline, f"no {text!r} in {path}"
        time.sleep(0.05)


@asynccontextmanager
async def ninja_running(folder: Path, *args: str) -> AsyncGenerator[None]:
    """A ninja run in folder for the block; its waiting step ends with the block, however the block ends."""
    async with await anyio.open_process(["ninja", *args, "-C", str(folder)]) as running:
        try:
            yield
        finally:
            (folder / "go").touch()
            with anyio.move_on_after(30):
                await running.wait()
            if running.returncode is None:
                running.kill()
                await running.wait()
    assert running.returncode == 0


@pytest.fixture
def folder(cfg: Config) -> Path:
    """A main tree whose earlier run built a and b, and a finished runtimes sub-build."""
    built = config.build_tree(cfg)
    nested = built / "runtimes" / "runtimes-bins"
    nested.mkdir(parents=True)
    (built / "build.ninja").write_text(OUTER)
    (nested / "build.ninja").write_text(NESTED)
    ninja(built, "a", "b")
    ninja(nested)
    return built


async def test_status_reads_a_running_tree_and_a_finished_sub_build(
    cfg: Config, folder: Path, logs: pytest.CaptureFixture[str]
) -> None:
    # ps gives a process's start in whole seconds: the run before must end a second before this one starts.
    await anyio.sleep(1.1)
    async with ninja_running(folder, "-j1"):
        # This run built c and now waits in d.
        await anyio.to_thread.run_sync(wait_for, folder / ".ninja_log", "\tc\t")
        before = tree(folder)
        await status.run(cfg, Status())
        assert tree(folder) == before
    main, nested, stats = events(logs)[0]
    assert main["event"] == "tree status"
    # Only this run's step counts: a and b were the run before.
    assert (main["tree"], main["path"], main["running"]) == ("build", str(folder), True)
    assert (main["outputs"], main["last"]) == (1, "c")
    assert 0 <= main["idle_s"] < 30
    assert (nested["tree"], nested["running"], nested["outputs"], nested["last"]) == ("runtimes", False, 2, None)
    assert stats["event"] == "sccache stats"
    for count in ("compile_requests", "hits", "misses", "compile_fails", "cache_write_errors"):
        assert isinstance(stats[count], int)


async def test_a_running_build_counts_no_step_before_it_logs_one(
    cfg: Config, folder: Path, logs: pytest.CaptureFixture[str]
) -> None:
    ninja(folder, "c")
    await anyio.sleep(1.1)
    # d, this run's only step, waits from the start: the log holds earlier runs only.
    async with ninja_running(folder, "d"):
        await anyio.to_thread.run_sync(wait_for_lock, folder)
        await status.run(cfg, Status())
    main, _, _ = events(logs)[0]
    assert (main["running"], main["outputs"], main["last"]) == (True, 0, None)


async def test_a_running_step_that_restat_logs_late_still_counts(
    cfg: Config, folder: Path, logs: pytest.CaptureFixture[str]
) -> None:
    # c changes its output late under restat, so it logs that mtime instead of its start; e, quick, ends after it.
    manifest = OUTER.replace("cmd = touch c", "cmd = sleep 0.3; touch c\n  restat = 1").replace(
        "d: run || c", "d: run || e"
    )
    (folder / "build.ninja").write_text(manifest + "build e: run || c\n  cmd = touch e\n")
    await anyio.sleep(1.1)
    async with ninja_running(folder, "-j1"):
        await anyio.to_thread.run_sync(wait_for, folder / ".ninja_log", "\te\t")
        await status.run(cfg, Status())
    main, _, _ = events(logs)[0]
    assert (main["running"], main["outputs"], main["last"]) == (True, 2, "e")


async def test_a_finished_tree_counts_each_logged_step_once_in_any_line_order(
    cfg: Config, folder: Path, logs: pytest.CaptureFixture[str]
) -> None:
    (folder / "go").touch()
    ninja(folder)
    # Rebuild a until the log holds over 100 entries, then start a run with nothing to do: ninja recompacts the
    # log as it starts (src/build_log.cc:314-321, 359-369), writing it in hash-map order, and appends nothing.
    log_file = folder / ".ninja_log"
    while len(log_file.read_text().splitlines()) <= 101:  # The version line plus 100 entries.
        (folder / "a").unlink()
        ninja(folder, "a")
    before = len(log_file.read_text().splitlines())
    ninja(folder)
    assert len(log_file.read_text().splitlines()) < before
    await status.run(cfg, Status())
    main, _, _ = events(logs)[0]
    assert (main["running"], main["outputs"], main["last"]) == (False, 4, None)


async def test_an_output_name_stays_inert_in_the_json_event(
    cfg: Config, folder: Path, logs: pytest.CaptureFixture[str]
) -> None:
    # The step's output name comes from the build: quotes, a backslash and a terminal escape.
    name = 'lib"x\\y\x1b[31m.a'
    # It ends after c and before d, which waits.
    manifest = OUTER.replace("d: run || c", f"d: run || {name}")
    (folder / "build.ninja").write_text(f"{manifest}rule touch\n  command = touch $out\nbuild {name}: touch || c\n")
    await anyio.sleep(1.1)
    async with ninja_running(folder, "-j1", "d"):
        await anyio.to_thread.run_sync(wait_for, folder / ".ninja_log", f"\t{name}\t")
        await status.run(cfg, Status())
    lines = logs.readouterr().out.splitlines()
    # One JSON object per line: nothing in the name broke a line or the encoding.
    assert len(lines) == 3
    assert json.loads(lines[0])["last"] == name


def test_status_without_a_ninja_log_says_how_to_start_one(env: Config, logs: pytest.CaptureFixture[str]) -> None:
    assert fails(["status"], logs)["event"] == (
        f"p2996 status: no ninja log in {config.build_tree(env)}; mise run //p2996:build starts one"
    )


async def test_a_tree_whose_log_holds_no_step_yet(cfg: Config, folder: Path, logs: pytest.CaptureFixture[str]) -> None:
    # What ninja leaves after recompacting a log whose steps are all gone.
    (folder / ".ninja_log").write_text("# ninja log v7\n")
    await status.run(cfg, Status())
    main, _, _ = events(logs)[0]
    assert (main["outputs"], main["last"]) == (0, None)


async def test_records_ninja_is_still_writing_are_skipped(
    cfg: Config, folder: Path, logs: pytest.CaptureFixture[str]
) -> None:
    # A record with too few fields, then one still without its newline, after the real ones for a and b.
    with (folder / ".ninja_log").open("a") as log_file:
        log_file.write("0\t12\n0\t5\t1794837410756997227\tc")
    await status.run(cfg, Status())
    main, _, _ = events(logs)[0]
    assert (main["running"], main["outputs"]) == (False, 2)
