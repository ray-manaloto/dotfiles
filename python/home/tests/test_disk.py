"""disk-watch in-process: the real free space of a scratch HOME against a line set above or below it."""

# lsof, osascript and hc are stood in by tests/stand_in.py (CODING_STANDARDS 2): osascript would show a real
# notification and hc would type into a real terminal. The free space, the state file and the JSON lines are real.

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
LS = "hc ls --json"
GET = "hc get t2 --json"
LSOF = "lsof -nP +L1 -F pcs"
# Two processes holding deleted files open; a line before any p line and an f line are skipped.
LISTING = "s5\np10\ncbig\nf1\ns3000000000\ns2000000000\np20\ncsmall\ns1000000000\n"
CHIEF = {"address": "t2", "state": "live", "where": "chief-of-staff / chief-of-staff"}


class Tools:
    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def answer(self, calls: dict[str, dict[str, object]]) -> None:
        script = {json.dumps(shlex.split(call)): answer for call, answer in calls.items()}
        (self.folder / "script.json").write_text(json.dumps(script))

    def calls(self) -> list[str]:
        log = self.folder / "calls.jsonl"
        return [shlex.join(json.loads(line)) for line in log.read_text().splitlines()] if log.exists() else []

    def remove(self, name: str) -> None:
        (self.folder / name).unlink()


@pytest.fixture
def tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Tools:
    """A scratch HOME, and lsof, osascript and hc stood in ahead of this Python on PATH."""
    folder = tmp_path / "stand-in"
    folder.mkdir()
    for name in ("lsof", "osascript", "hc"):
        (folder / name).symlink_to(STAND_IN)
    (tmp_path / "home").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PATH", f"{folder}:{Path(sys.executable).parent}")
    monkeypatch.setenv("STAND_IN", str(folder))
    for name in ("DISK_WATCH_CHECKS", "DISK_WATCH_MIN_FREE_GB", "DISK_WATCH_EVERY"):
        monkeypatch.delenv(name, raising=False)
    tools = Tools(folder)
    tools.answer({})
    return tools


def foreground(*argv: str) -> dict[str, object]:
    return {"stdout": json.dumps({"foreground": {"argv": list(argv)}})}


def everything(send: dict[str, object] | None = None) -> dict[str, dict[str, object]]:
    """Every call a low check makes, each answering as it does when all is well."""
    return {
        LSOF: {"stdout": LISTING},
        "osascript": {},
        LS: {"stdout": json.dumps({"terminals": [CHIEF]})},
        GET: foreground("/opt/bin/claude", "--brief"),
        "hc send t2": send or {},
    }


def script(tools: Tools, calls: dict[str, dict[str, object]]) -> None:
    """calls in shell form; the osascript and hc send keys gain the alert text the check will send."""
    free = shutil.disk_usage(Path.home()).free
    text = disk.message(free, LOW, disk.holders(LISTING))
    title = json.dumps("Disk low")
    keyed = {}
    for call, answer in calls.items():
        if call == "osascript":
            keyed[json.dumps(["osascript", "-e", f"display notification {json.dumps(text)} with title {title}"])] = (
                answer
            )
        elif call == "hc send t2":
            keyed[json.dumps(["hc", "send", "t2", text])] = answer
        else:
            keyed[json.dumps(shlex.split(call))] = answer
    (tools.folder / "script.json").write_text(json.dumps(keyed))


def state() -> dict[str, object]:
    return json.loads((Path.home() / disk.STATE).read_text())


def test_a_check_above_the_line_alerts_nobody_and_clears_the_state(tools: Tools) -> None:
    (Path.home() / disk.STATE).parent.mkdir(parents=True)
    (Path.home() / disk.STATE).write_text('{"alerted_at": 5.0}')
    done = disk.check(min_free=OK)
    assert (done.alert, done.holders, done.told) == (False, [], [])
    assert done.free_bytes > 0
    assert state() == {"alerted_at": None}
    assert tools.calls() == []


def test_a_low_check_notifies_and_tells_chief_of_staff_naming_the_biggest_holders(tools: Tools) -> None:
    script(tools, everything())
    done = disk.check(min_free=LOW, now=lambda: 1000.0)
    assert done.alert
    assert done.told == ["notification", "chief-of-staff"]
    assert [(h.pid, h.command, h.bytes) for h in done.holders] == [(10, "big", 5 * disk.GB), (20, "small", disk.GB)]
    assert state() == {"alerted_at": 1000.0}
    assert "big pid 10 5 GB, small pid 20 1 GB" in tools.calls()[-1]


def test_an_alert_repeats_only_after_the_repeat_interval(tools: Tools) -> None:
    script(tools, everything())
    disk.check(min_free=LOW, now=lambda: 1000.0)
    quiet = disk.check(min_free=LOW, now=lambda: 1000.0 + disk.REPEAT - 1)
    assert (quiet.alert, quiet.told) == (False, [])
    assert state() == {"alerted_at": 1000.0}
    again = disk.check(min_free=LOW, now=lambda: 1000.0 + disk.REPEAT)
    assert again.alert
    assert state() == {"alerted_at": 1000.0 + disk.REPEAT}


def test_an_unreadable_state_file_counts_as_no_alert_yet(tools: Tools) -> None:
    script(tools, everything())
    (Path.home() / disk.STATE).parent.mkdir(parents=True)
    (Path.home() / disk.STATE).write_text("not json")
    assert disk.check(min_free=LOW, now=lambda: 1.0).alert


def test_a_shell_in_chief_of_staffs_tab_gets_nothing_typed_into_it(tools: Tools) -> None:
    script(tools, everything() | {GET: foreground("/bin/zsh")})
    done = disk.check(min_free=LOW)
    assert done.told == ["notification"]
    assert not any(call.startswith("hc send") for call in tools.calls())


@pytest.mark.parametrize(
    "terminals",
    [
        [],
        [CHIEF | {"state": "finished"}],
        [CHIEF | {"where": "other / other"}],
    ],
)
def test_no_live_chief_of_staff_tab_means_no_send(tools: Tools, terminals: list[dict[str, object]]) -> None:
    script(tools, everything() | {LS: {"stdout": json.dumps({"terminals": terminals})}})
    assert disk.check(min_free=LOW).told == ["notification"]


@pytest.mark.parametrize(
    "calls",
    [
        {LS: {"code": 1}},
        {GET: {"code": 1}},
        {GET: {"stdout": json.dumps({"foreground": None})}},
        {LS: {"stdout": "not json"}},
        {LS: {"stdout": "[]"}},
        {"hc send t2": {"code": 1}},
    ],
)
def test_a_failing_hc_call_skips_the_send_and_says_so(tools: Tools, calls: dict[str, dict[str, object]]) -> None:
    script(tools, everything() | calls)
    assert disk.check(min_free=LOW).told == ["notification"]


def test_without_osascript_or_hc_the_check_still_records_the_holders(tools: Tools) -> None:
    script(tools, everything())
    tools.remove("osascript")
    tools.remove("hc")
    done = disk.check(min_free=LOW, now=lambda: 7.0)
    assert (done.alert, done.told) == (False, [])
    assert len(done.holders) == 2
    # Nobody heard it, but it counts as sent: the next try waits out REPEAT like any other.
    assert state() == {"alerted_at": 7.0}


def test_a_failing_notification_leaves_only_chief_of_staff(tools: Tools) -> None:
    script(tools, everything() | {"osascript": {"code": 1}})
    assert disk.check(min_free=LOW).told == ["chief-of-staff"]


def test_without_lsof_the_alert_names_no_holders(tools: Tools) -> None:
    tools.remove("lsof")
    assert disk.holders(disk.read("lsof")) == []
    assert disk.message(disk.GB, LOW, []).endswith("Deleted files held open: none found")


def test_a_process_name_reaches_the_alert_without_shell_characters() -> None:
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
