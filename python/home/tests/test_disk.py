"""disk-snapshot and disk-guard against real folders, the real du, ps and lsof, and the real data volume."""

import fcntl
import json
import os
import sys
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


def test_the_floor_is_monits_threshold() -> None:
    assert disk.FLOOR_GIB == 100


def test_the_command_passes_over_the_floor(capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(disk, "FLOOR_GIB", 1)
    code, out, err = hometools(capfd, "disk-guard")
    assert (code, err) == (0, "")
    assert json.loads(out)["floor_gib"] == 1


def test_the_command_fails_with_one_error_under_the_floor(
    capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(disk, "FLOOR_GIB", 1_000_000)
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


def test_a_folder_name_with_a_newline_is_one_entry(tmp_path: Path) -> None:
    """dust's JSON keeps a newline inside a name, where du's lines would split it."""
    root = tmp_path / "r"
    (root / "two\nlines").mkdir(parents=True)
    text, _ = disk.biggest(root, 30)
    assert text.count("two\nlines") == 1


def test_a_root_dust_cannot_measure_is_named_and_the_snapshot_goes_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tree(tmp_path / "r", 1)
    monkeypatch.setenv("PATH", str(tmp_path / "no-dust"))
    assert disk.biggest(root, 30) == (f"== {root}: dust failed (FileNotFoundError)\n", False)


def test_output_that_is_not_dusts_tree_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stand-in dust on PATH, a Python script, that prints something other than its JSON tree."""
    root = tree(tmp_path / "r", 1)
    fake = tmp_path / "bin/dust"
    fake.parent.mkdir()
    fake.write_text(f"#!{sys.executable} -I\nprint('not json')\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake.parent}{os.pathsep}{os.environ['PATH']}")
    assert disk.biggest(root, 30) == (f"== {root}: dust failed (JSONDecodeError)\n", False)


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
    monkeypatch.setattr(disk, "SECONDS", 5)
    code, out, err = hometools(capfd, "disk-snapshot")
    assert (code, err) == (0, "")
    folder = Path(json.loads(out)["folder"])
    assert folder.parent == tmp_path / "state/dotfiles/disk-alerts"
    assert (folder / "folders.txt").is_file()
    assert os.access(folder / "lsof.txt", os.R_OK)
