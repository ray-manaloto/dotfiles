"""disk-watch in-process: the real free space of a scratch HOME against a line set above or below it."""

# lsof and osascript are stood in by tests/stand_in.py (CODING_STANDARDS 2): osascript would show a real
# notification. The free space, the state file, the alert file and the JSON lines are real.

import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hometools import disk
from hometools.cli import main

STAND_IN = Path(__file__).with_name("stand_in.py")
LOW = 10**18  # more than any disk holds: every check is below the line
OK = 0
LSOF = "lsof -nP +L1 -F pcs"
# Two processes holding deleted files open; a line before any p line and an f line are skipped.
LISTING = "s5\np10\ncbig\nf1\ns3000000000\ns2000000000\np20\ncsmall\ns1000000000\n"


class Tools:
    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def calls(self) -> list[str]:
        log = self.folder / "calls.jsonl"
        return [shlex.join(json.loads(line)) for line in log.read_text().splitlines()] if log.exists() else []

    def remove(self, name: str) -> None:
        (self.folder / name).unlink()


@pytest.fixture
def tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Tools:
    """A scratch HOME, and lsof and osascript stood in ahead of this Python on PATH."""
    folder = tmp_path / "stand-in"
    folder.mkdir()
    for name in ("lsof", "osascript"):
        (folder / name).symlink_to(STAND_IN)
    (tmp_path / "home").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PATH", f"{folder}:{Path(sys.executable).parent}")
    monkeypatch.setenv("STAND_IN", str(folder))
    for name in ("DISK_WATCH_CHECKS", "DISK_WATCH_MIN_FREE_GB", "DISK_WATCH_EVERY"):
        monkeypatch.delenv(name, raising=False)
    tools = Tools(folder)
    script(tools)
    return tools


def script(tools: Tools, notification: dict[str, object] | None = None) -> None:
    """lsof lists LISTING; osascript answers the notification a low check will post."""
    text = disk.message(shutil.disk_usage(Path.home()).free, LOW, disk.holders(LISTING))
    post = f"display notification {json.dumps(text)} with title {json.dumps('Disk low')}"
    calls = {
        json.dumps(shlex.split(LSOF)): {"stdout": LISTING},
        json.dumps(["osascript", "-e", post]): notification or {},
    }
    (tools.folder / "script.json").write_text(json.dumps(calls))


def state() -> dict[str, object]:
    return json.loads((Path.home() / disk.STATE).read_text())


def alert() -> dict[str, object]:
    return json.loads((Path.home() / disk.ALERT).read_text())


def test_a_low_check_writes_the_alert_file_and_notifies_naming_the_biggest_holders(tools: Tools) -> None:
    done = disk.check(min_free=LOW, now=lambda: 1000.0)
    assert (done.alert, done.told) == (True, ["alert-file", "notification"])
    held = [{"pid": 10, "command": "big", "bytes": 5 * disk.GB}, {"pid": 20, "command": "small", "bytes": disk.GB}]
    assert [h.model_dump() for h in done.holders] == held
    written = alert()
    text = str(written.pop("text"))
    assert written == {"at": 1000.0, "free_bytes": done.free_bytes, "min_free_bytes": LOW, "holders": held}
    assert "big pid 10 5 GB, small pid 20 1 GB" in text
    assert text in tools.calls()[-1]
    assert state() == {"alerted_at": 1000.0}
    # Written whole, then renamed: no temporary file is left beside it.
    assert sorted(p.name for p in (Path.home() / disk.FOLDER).iterdir()) == ["alert.json", "state.json"]


def test_a_check_above_the_line_removes_the_alert_and_clears_the_state(tools: Tools) -> None:
    disk.check(min_free=LOW, now=lambda: 5.0)
    done = disk.check(min_free=OK)
    assert (done.alert, done.holders, done.told) == (False, [], [])
    assert done.free_bytes > 0
    assert state() == {"alerted_at": None}
    assert not (Path.home() / disk.ALERT).exists()
    assert len(tools.calls()) == 2  # only the low check's lsof and osascript


@pytest.mark.usefixtures("tools")
def test_an_alert_repeats_only_after_the_repeat_interval() -> None:
    disk.check(min_free=LOW, now=lambda: 1000.0)
    quiet = disk.check(min_free=LOW, now=lambda: 1000.0 + disk.REPEAT - 1)
    assert (quiet.alert, quiet.told) == (False, [])
    assert (state(), alert()["at"]) == ({"alerted_at": 1000.0}, 1000.0)
    again = disk.check(min_free=LOW, now=lambda: 1000.0 + disk.REPEAT)
    assert again.alert
    assert (state(), alert()["at"]) == ({"alerted_at": 1000.0 + disk.REPEAT}, 1000.0 + disk.REPEAT)


@pytest.mark.usefixtures("tools")
def test_an_unreadable_state_file_counts_as_no_alert_yet() -> None:
    (Path.home() / disk.FOLDER).mkdir(parents=True)
    (Path.home() / disk.STATE).write_text("not json")
    assert disk.check(min_free=LOW, now=lambda: 1.0).alert


def test_a_failing_notification_still_writes_the_alert_file(tools: Tools) -> None:
    script(tools, {"code": 1})
    assert disk.check(min_free=LOW).told == ["alert-file"]


def test_an_unwritable_alert_file_still_notifies_and_leaves_no_partial_file(tools: Tools) -> None:
    (Path.home() / disk.ALERT).mkdir(parents=True)  # a folder where the file goes: the rename fails
    done = disk.check(min_free=LOW, now=lambda: 3.0)
    assert done.told == ["notification"]
    assert [p.name for p in (Path.home() / disk.FOLDER).iterdir() if p.name.startswith(".")] == []
    assert state() == {"alerted_at": 3.0}
    assert tools.calls()[-1].startswith("osascript")


def test_an_unwritable_state_file_alerts_again_at_the_next_check(tools: Tools) -> None:
    (Path.home() / disk.STATE).mkdir(parents=True)  # a folder where the state goes: it can't be read or written
    assert disk.check(min_free=LOW, now=lambda: 1.0).told == ["alert-file", "notification"]
    assert disk.check(min_free=LOW, now=lambda: 2.0).told == ["alert-file", "notification"]
    assert len([call for call in tools.calls() if call.startswith("osascript")]) == 2


def test_without_osascript_the_alert_file_still_goes_out(tools: Tools) -> None:
    tools.remove("osascript")
    done = disk.check(min_free=LOW, now=lambda: 7.0)
    assert done.told == ["alert-file"]
    assert alert()["at"] == 7.0


def test_without_lsof_the_alert_names_no_holders(tools: Tools) -> None:
    tools.remove("lsof")
    assert disk.holders(disk.read("lsof")) == []
    assert disk.message(disk.GB, LOW, []).endswith("Deleted files held open: none found")


def test_a_process_name_reaches_the_alert_text_without_shell_characters() -> None:
    (held,) = disk.holders("p7\nc`rm -rf ~`<x>$(y)\ns1000000000\n")
    assert held.command == "`rm -rf ~`<x>$(y)"
    assert "_rm -rf ___x___y_ pid 7 1 GB" in disk.message(0, LOW, [held])


def test_holders_keeps_only_the_top_five() -> None:
    listing = "".join(f"p{pid}\ncp{pid}\ns{pid}\n" for pid in range(1, 9))
    assert [h.pid for h in disk.holders(listing)] == [8, 7, 6, 5, 4]


@pytest.mark.usefixtures("tools")
def test_the_command_prints_one_json_line_per_check(
    capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The service runs with no count and checks until stopped; a count of 2 ends after the second check."""
    monkeypatch.setenv("DISK_WATCH_CHECKS", "2")
    monkeypatch.setenv("DISK_WATCH_EVERY", "0")
    monkeypatch.setenv("DISK_WATCH_MIN_FREE_GB", "0")
    main(["disk-watch"])
    lines = capfd.readouterr().out.splitlines()
    assert [json.loads(line)["min_free_bytes"] for line in lines] == [0, 0]


LAUNCHER = Path(__file__).resolve().parents[3] / "unix/home/.config/mise/tasks/disk/watch"


def test_the_launcher_runs_the_watch_from_this_checkouts_package(tmp_path: Path) -> None:
    """The task the service runs: one check above a line of 0 GB, in a scratch HOME, as one JSON line."""
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "DISK_WATCH_CHECKS": "1", "DISK_WATCH_MIN_FREE_GB": "0"}
    done = subprocess.run([LAUNCHER], capture_output=True, text=True, check=False, env=env)
    assert (done.returncode, done.stderr) == (0, "")
    (line,) = done.stdout.splitlines()
    assert json.loads(line) | {"free_bytes": 0} == {
        "free_bytes": 0,
        "min_free_bytes": 0,
        "alert": False,
        "holders": [],
        "told": [],
    }
    assert json.loads((tmp_path / disk.STATE).read_text()) == {"alerted_at": None}
    assert not (tmp_path / disk.ALERT).exists()


def test_the_launcher_takes_no_arguments() -> None:
    done = subprocess.run([sys.executable, "-I", LAUNCHER, "--once"], capture_output=True, text=True, check=False)
    assert (done.returncode, done.stdout) == (2, "")
    assert json.loads(done.stderr) == {"error": "disk:watch takes no arguments"}


def test_the_launcher_says_when_the_package_has_no_environment(tmp_path: Path) -> None:
    copy = tmp_path / "unix/home/.config/mise/tasks/disk/watch"
    copy.parent.mkdir(parents=True)
    shutil.copy2(LAUNCHER, copy)
    done = subprocess.run([sys.executable, "-I", copy], capture_output=True, text=True, check=False)
    assert (done.returncode, done.stdout) == (2, "")
    want = f"disk:watch: {tmp_path.resolve()}/python/home/.venv has no hometools; run: mise run //home:sync"
    assert json.loads(done.stderr) == {"error": want}
