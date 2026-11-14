"""disk-snapshot and disk-guard against real folders, the real dust, ps and lsof, and the real data volume."""

import fcntl
import json
import os
import time
from pathlib import Path

import pytest

from hometools import disk
from hometools.cli import main


def hometools(capfd: pytest.CaptureFixture[str], command: str) -> tuple[int, str, str]:
    try:
        main([command])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, out, err


def tree(root: Path, files: int, size: int = 1) -> Path:
    """root/a/b with files files of size bytes each."""
    deep = root / "a/b"
    deep.mkdir(parents=True)
    for n in range(files):
        (deep / f"f{n}").write_bytes(b"x" * size)
    return root


def test_the_guard_passes_with_space_and_names_free_and_floor() -> None:
    passed = disk.guard(floor=1)
    assert passed.floor_gib == 1
    assert passed.free_gib == disk.free_gib() >= 1


def test_the_guard_refuses_under_the_floor_and_says_why() -> None:
    with pytest.raises(ValueError, match=r"GiB free, under the 1000000 GiB floor") as low:
        disk.guard(floor=1_000_000)
    assert "disk:snapshot" in str(low.value)


def test_the_floor_is_monits_threshold_unless_the_environment_sets_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISK_FLOOR_GIB", "")
    if disk.free_gib() >= 100:
        assert disk.guard().floor_gib == 100
    else:
        with pytest.raises(ValueError, match="under the 100 GiB floor"):
            disk.guard()


def test_the_command_passes_over_the_floor(capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISK_FLOOR_GIB", "1")
    code, out, err = hometools(capfd, "disk-guard")
    assert (code, err) == (0, "")
    assert json.loads(out)["floor_gib"] == 1


def test_the_command_fails_with_one_error_under_the_floor(
    capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DISK_FLOOR_GIB", "1000000")
    code, out, err = hometools(capfd, "disk-guard")
    assert (code, out) == (1, "")
    assert json.loads(err)["error"].startswith(f"disk-guard: {disk.DATA} has ")


def test_dust_lists_the_biggest_folders_first(tmp_path: Path) -> None:
    root = tree(tmp_path / "r", 3, 1 << 20)
    (root / "small").mkdir()
    text, stopped = disk.biggest(root, 30)
    lines = text.splitlines()
    assert (lines[0], stopped) == (f"== {root}", False)
    assert lines[1].endswith(f"  {root}")
    assert lines[2].endswith(f"  {root}/a")
    assert lines[3].endswith(f"  {root}/a/b")
    assert lines[-1].endswith(f"  {root}/small")


def test_a_root_stopped_at_its_limit_has_no_totals(tmp_path: Path) -> None:
    root = tree(tmp_path / "r", 3000)
    assert disk.biggest(root, 1e-6) == (f"== {root} (stopped at its time limit: no totals)\n", True)


def test_a_folder_name_that_looks_like_a_report_line_stays_inert(tmp_path: Path) -> None:
    """A newline in a name could forge a size line; the name is JSON-quoted on its own line instead."""
    root = tmp_path / "r"
    (root / "two\n999.0 GiB  /fake").mkdir(parents=True)
    text, _ = disk.biggest(root, 30)
    lines = text.splitlines()
    assert not any(line.startswith("999.0 GiB") for line in lines)
    assert lines[-1].endswith(json.dumps(f"{root}/two\n999.0 GiB  /fake"))


def test_a_root_dust_cannot_measure_is_named_and_the_snapshot_goes_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tree(tmp_path / "r", 1)
    monkeypatch.setenv("PATH", str(tmp_path / "no-dust"))
    assert disk.biggest(root, 30) == (f"== {root}: dust failed (FileNotFoundError)\n", False)


@pytest.mark.parametrize(("out", "error"), [("not json", ValueError), ("[]", TypeError), ("{}", KeyError)])
def test_output_that_is_not_dusts_tree_is_refused(out: str, error: type[Exception]) -> None:
    with pytest.raises(error):
        disk.ranked(out)


def test_a_missing_root_says_so(tmp_path: Path) -> None:
    assert disk.biggest(tmp_path / "gone", 30) == (f"== {tmp_path / 'gone'}: not a folder\n", False)


def test_a_command_past_its_limit_is_stopped() -> None:
    assert disk.bounded(["sleep", "30"], 0.2) == ("", True)
    assert disk.bounded(["echo", "hi"], 30) == ("hi\n", False)


def test_big_open_keeps_regular_files_of_a_gib_or_more() -> None:
    lsof = "\n".join(
        [
            "p10", "cwriter", "f3", "tREG", f"s{3 * disk.GIB}", "n/data/big",
            "f4", "tREG", "s10", "n/data/small",
            "f5", "tPIPE", "n->0x1",
            "p11", "cother", "f6", "tREG", f"s{disk.GIB}", "n/data/one",
            "f7", "tFIFO", "n/data/fifo",
            "f8", "tREG", f"s{disk.GIB}", "n/data/one",
        ]
    )  # fmt: skip
    assert disk.big_open(lsof) == [
        "     3.0 GiB  pid 10 writer  /data/big",
        "     1.0 GiB  pid 11 other  /data/one",
    ]


def test_a_folder_name_taken_in_the_same_second_gets_a_number(tmp_path: Path) -> None:
    assert disk.fresh(tmp_path, "T").name == "T"
    assert disk.fresh(tmp_path, "T").name == "T-2"
    assert disk.fresh(tmp_path).name.endswith("Z")


def test_a_thousandth_snapshot_in_one_second_is_refused(tmp_path: Path) -> None:
    (tmp_path / "T").mkdir()
    for n in range(2, 1000):
        (tmp_path / f"T-{n}").mkdir()
    with pytest.raises(FileExistsError, match="999 snapshots"):
        disk.fresh(tmp_path, "T")


def test_a_snapshot_writes_a_new_folder_and_deletes_nothing(tmp_path: Path) -> None:
    parent = tmp_path / "alerts"
    earlier = parent / "earlier"
    earlier.mkdir(parents=True)
    (earlier / "kept").write_text("kept")
    root = tree(tmp_path / "r", 2)
    first = disk.snapshot(parent, [root, tmp_path / "gone"], 30, str(tmp_path))
    second = disk.snapshot(parent, [root], 30, str(tmp_path))
    assert first.timed_out == second.timed_out == []
    assert first.folder != second.folder
    folder = Path(first.folder or "")
    assert sorted(p.name for p in folder.iterdir()) == ["folders.txt", "free.txt", "lsof.txt", "ps.txt"]
    assert folder.stat().st_mode & 0o777 == 0o700
    assert f"== {root}\n" in (folder / "folders.txt").read_text()
    assert f"== {tmp_path / 'gone'}: not a folder" in (folder / "folders.txt").read_text()
    assert (folder / "ps.txt").read_text().startswith("  PID")
    assert "== deleted while still open (lsof +L1)" in (folder / "lsof.txt").read_text()
    assert (folder / "free.txt").read_text().startswith(f"{tmp_path}: ")
    assert (earlier / "kept").read_text() == "kept"


def test_a_root_past_its_limit_is_named(tmp_path: Path) -> None:
    root = tree(tmp_path / "r", 3000)
    done = disk.snapshot(tmp_path / "alerts", [root], 1e-6, str(tmp_path))
    assert done.timed_out == [str(root)]


def test_a_snapshot_while_another_runs_writes_nothing(tmp_path: Path) -> None:
    parent = tmp_path / "alerts"
    parent.mkdir()
    with (parent / ".lock").open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        done = disk.snapshot(parent, [tmp_path], 30, str(tmp_path))
    assert (done.folder, done.timed_out) == (None, [])
    assert [p.name for p in parent.iterdir()] == [".lock"]


def test_the_roots_and_output_follow_home_and_xdg_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    assert disk.output() == tmp_path / ".local/state/dotfiles/disk-alerts"
    assert disk.roots()[:3] == [tmp_path / "tmp", Path("/private/tmp"), tmp_path / ".cache"]
    assert disk.roots()[-1] == tmp_path / "dev"
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert disk.output() == tmp_path / "state/dotfiles/disk-alerts"


def test_the_command_writes_under_the_state_folder(
    capfd: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real command, with the real roots and data volume; the limit keeps it short."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("DISK_SNAPSHOT_SECONDS", "5")
    code, out, err = hometools(capfd, "disk-snapshot")
    assert (code, err) == (0, "")
    folder = Path(json.loads(out)["folder"])
    assert folder.parent == tmp_path / "state/dotfiles/disk-alerts"
    assert (folder / "folders.txt").is_file()
    assert os.access(folder / "lsof.txt", os.R_OK)


def write_mib(path: Path, mib: int) -> None:
    """mib MiB of incompressible data, forced to disk, so macOS counts it as this process's disk writes."""
    with path.open("wb") as out:
        out.write(os.urandom(mib * disk.MIB))
        out.flush()
        os.fsync(out.fileno())


def mine(found: dict[str, tuple[int, int, str]]) -> tuple[str, int]:
    key = next(key for key, (pid, _, _) in found.items() if pid == os.getpid())
    return key, found[key][1]


def test_the_counters_see_this_processes_own_writes_and_leave_out_roots(tmp_path: Path) -> None:
    key, before = mine(disk.written())
    write_mib(tmp_path / "w", 8)
    again, after = mine(disk.written())
    assert again == key
    assert after - before >= 8 * disk.MIB
    # launchd is root's: macOS refuses another user's counters.
    assert all(pid != 1 for pid, _, _ in disk.written().values())


def test_the_writers_are_the_most_written_first_and_a_new_process_counts_from_its_start() -> None:
    now = {
        "10:1": (10, 5 * disk.MIB, "/bin/small"),
        "11:1": (11, 900 * disk.MIB, "/bin/big"),
        "12:7": (12, 300 * disk.MIB, "/bin/new"),
        "13:1": (13, disk.MIB - 1, "/bin/idle"),
    }
    before = {"10:1": 2 * disk.MIB, "11:1": 100 * disk.MIB, "12:6": 290 * disk.MIB}
    assert [(w.pid, w.written_mib) for w in disk.writers(before, now)] == [(11, 800), (12, 300), (10, 3)]
    many = {f"{n}:1": (n, (n + 1) * disk.MIB, "/bin/x") for n in range(20)}
    assert [w.pid for w in disk.writers({}, many)] == list(range(19, 19 - disk.WRITERS, -1))


def test_the_first_line_has_no_drop_and_the_next_names_this_process(tmp_path: Path) -> None:
    calls: list[str] = []
    folder = tmp_path / "alerts"
    first = disk.sample(folder, snap=lambda: calls.append("snap"))
    assert (first.drop_gib, first.snapshot, first.free_gib == disk.free_gib()) == (None, False, True)
    assert folder.stat().st_mode & 0o777 == 0o700
    write_mib(tmp_path / "w", 8)
    second = disk.sample(folder, snap=lambda: calls.append("snap"))
    assert second.drop_gib is not None
    assert second.drop_gib < disk.DROP_GIB
    assert any(w.pid == os.getpid() and w.written_mib >= 8 for w in second.writers)
    lines = (folder / "samples.jsonl").read_text().splitlines()
    assert [json.loads(line)["at"] for line in lines] == [first.at, second.at]
    assert calls == []


def test_a_drop_of_twenty_gib_starts_a_snapshot(tmp_path: Path) -> None:
    calls: list[str] = []
    higher = disk.DiskSample(at="then", free_gib=disk.free_gib() + 50, drop_gib=None, writers=[], snapshot=False)
    (tmp_path / "samples.jsonl").write_text(higher.model_dump_json() + "\n")
    dropped = disk.sample(tmp_path, snap=lambda: calls.append("snap"))
    assert dropped.drop_gib is not None
    assert dropped.drop_gib >= 50
    assert dropped.snapshot
    assert calls == ["snap"]


def test_unreadable_state_starts_afresh(tmp_path: Path) -> None:
    (tmp_path / "samples.jsonl").write_text("not json\n")
    (tmp_path / "written.json").write_text("[1, 2]")
    fresh_start = disk.sample(tmp_path, snap=lambda: None)
    assert fresh_start.drop_gib is None
    (tmp_path / "written.json").write_text("{")
    assert disk.sample(tmp_path, snap=lambda: None).drop_gib is not None


def test_a_full_log_moves_aside(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(disk, "LOG_BYTES", 10)
    disk.sample(tmp_path, snap=lambda: None)
    disk.sample(tmp_path, snap=lambda: None)
    assert len((tmp_path / "samples.jsonl.1").read_text().splitlines()) == 1
    assert len((tmp_path / "samples.jsonl").read_text().splitlines()) == 1


def test_spawn_starts_the_command_without_waiting(tmp_path: Path) -> None:
    marker = tmp_path / "ran"
    disk.spawn(["/usr/bin/touch", str(marker)])
    for _ in range(100):
        if marker.exists():
            break
        time.sleep(0.05)
    assert marker.exists()


def test_the_log_command_writes_one_line_under_the_state_folder(
    capfd: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    code, out, err = hometools(capfd, "disk-log")
    assert (code, err) == (0, "")
    log = tmp_path / "state/dotfiles/disk-alerts/samples.jsonl"
    assert json.loads(log.read_text()) == json.loads(out)
