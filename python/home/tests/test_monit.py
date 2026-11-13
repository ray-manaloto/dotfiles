"""monit-alert with a scripted osascript (tests/stand_in.py), so no test posts a real notification, and real files."""

import json
import os
from pathlib import Path

import pytest

from hometools import monit
from hometools.cli import main
from hometools.models import MonitAlert

STAND_IN = Path(__file__).with_name("stand_in.py")
RECORD = ".local/state/dotfiles/monit/alert.json"


def hometools(capfd: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    try:
        main(["monit-alert"])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, out, err


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch HOME and a scripted osascript; no MONIT_* variable set."""
    folder = tmp_path / "stand-in"
    folder.mkdir()
    (folder / "osascript").symlink_to(STAND_IN)
    monkeypatch.setenv("STAND_IN", str(folder))
    monkeypatch.setenv("MONIT_ALERT_OSASCRIPT", str(folder / "osascript"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    for name in ("MONIT_SERVICE", "MONIT_EVENT", "MONIT_DESCRIPTION", "MONIT_ALERT_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path / "home"


def script(service: str, description: str, reply: dict[str, object]) -> None:
    call = json.dumps(["osascript", *monit.NOTIFY, service, description])
    (Path(os.environ["STAND_IN"]) / "script.json").write_text(json.dumps({call: reply}))


def calls() -> list[list[str]]:
    lines = (Path(os.environ["STAND_IN"]) / "calls.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def test_notifies_with_the_text_as_arguments_and_records_the_alert(
    home: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    text = 'space free 90 GB "quoted" & tell application'
    monkeypatch.setenv("MONIT_SERVICE", "data")
    monkeypatch.setenv("MONIT_EVENT", "Resource limit matched")
    monkeypatch.setenv("MONIT_DESCRIPTION", text)
    script("data", text, {"code": 0})
    code, out, err = hometools(capfd)
    assert (code, err) == (0, "")
    written = json.loads((home / RECORD).read_text())
    assert written == json.loads(out)
    assert (written["service"], written["event"], written["description"]) == ("data", "Resource limit matched", text)
    assert written["at"].endswith("Z")
    # The text is the last argument, never part of the AppleScript.
    assert calls() == [["osascript", *monit.NOTIFY, "data", text]]
    assert sorted(p.name for p in (home / RECORD).parent.iterdir()) == ["alert.json"]
    assert (home / RECORD).parent.stat().st_mode & 0o777 == 0o700


def test_a_failed_notification_still_records_the_alert_and_fails(home: Path, capfd: pytest.CaptureFixture[str]) -> None:
    script("monit", "an alert with no description", {"code": 1, "stderr": "no notification\n"})
    code, out, err = hometools(capfd)
    assert (code, out) == (1, "")
    error = json.loads(err)["error"]
    assert error.startswith("monit-alert: notification: ")
    assert "exited 1: no notification" in error
    assert "alert.json" not in error
    written = json.loads((home / RECORD).read_text())
    assert (written["service"], written["event"]) == ("monit", "")


def test_names_both_steps_when_both_fail(
    home: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MONIT_ALERT_OSASCRIPT", str(home / "no-osascript"))
    # A file where the record's folder should be: the folder can't be made.
    (home / ".local/state/dotfiles").mkdir(parents=True)
    (home / ".local/state/dotfiles/monit").write_text("")
    code, _, err = hometools(capfd)
    assert code == 1
    error = json.loads(err)["error"]
    assert "notification: " in error
    assert "FileNotFoundError" in error
    assert f"alert.json: {home / RECORD}: " in error


def test_an_osascript_that_never_ends_is_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MONIT_ALERT_SECONDS", "1")
    assert monit.notify("data", "low", "/usr/bin/yes") == "/usr/bin/yes: TimeoutExpired"


def test_a_failed_replace_keeps_the_old_record_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    # A folder where the record goes: os.replace can't put a file over it.
    target = tmp_path / "alert.json"
    target.mkdir()
    (target / "keep").write_text("old")
    record = MonitAlert(at="2026-11-13T00:00:00Z", service="data", event="", description="low")
    why = monit.write(record, target)
    assert why is not None
    assert why.startswith(f"{target}: ")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["alert.json"]
    assert (target / "keep").read_text() == "old"


def test_the_record_lives_under_home(home: Path) -> None:
    assert monit.record_path() == home / RECORD
