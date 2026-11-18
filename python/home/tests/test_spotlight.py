"""spotlight-check against a stand-in mdfind that indexes the folders a test chooses; the probes are real files."""

import json
import os
import sys
from pathlib import Path

import pytest

from hometools import spotlight
from hometools.cli import main

# Why a stand-in (CODING_STANDARDS 2): real mdfind answers from the Spotlight index, which a system daemon fills on its
# own schedule (7 s to about 2.5 min for a new file in the 2026-11-16 probes), and which folder it skips depends on the
# Search Privacy list, which no test can set up: it needs Full Disk Access even for root. The stand-in does the same
# observable job as `mdfind -name NAME`: one absolute path per line for each indexed file whose name contains NAME.
# The real tool was run through this task on the Mac (PR body): the control was found and the two excluded folders
# were not.
# mdfind -name NAME: every file under $INDEXED (folders split by os.pathsep) whose name contains NAME. Each call is
# counted in $CALLS; with $LATE set, the first call finds nothing, as when Spotlight hasn't caught up yet; with
# $PROBES_LATE set, the first call finds only the control file, as when Spotlight indexes it before the probes.
MDFIND = """import os, sys
from pathlib import Path
calls = Path(os.environ["CALLS"])
calls.write_text(calls.read_text() + "x" if calls.exists() else "x")
if os.environ.get("LATE") and calls.read_text() == "x":
    raise SystemExit(0)
first = calls.read_text() == "x"
for root in filter(None, os.environ.get("INDEXED", "").split(os.pathsep)):
    for path in sorted(Path(root).rglob("*" + sys.argv[2] + "*")):
        if not (os.environ.get("PROBES_LATE") and first and "-control" not in path.name):
            print(path)
"""


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A home with an mdfind stand-in first on PATH and the tracked folders under it."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "mdfind").write_text(f"#!{sys.executable}\n{MDFIND}")
    (bin_ / "mdfind").chmod(0o755)
    # open URL: records the URL instead of opening System Settings.
    opened = tmp_path / "opened"
    (bin_ / "open").write_text(f'#!{sys.executable}\nimport sys\nopen({str(opened)!r}, "w").write(sys.argv[1])\n')
    (bin_ / "open").chmod(0o755)
    monkeypatch.setenv("PATH", os.pathsep.join([str(bin_), os.environ["PATH"]]))
    monkeypatch.setenv("CALLS", str(tmp_path / "calls"))
    home = tmp_path / "home"
    for folder in ("dev/github", "dev/tmp", "Documents"):
        (home / folder).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPOTLIGHT_SETTLE", "0")
    return home


def indexed(monkeypatch: pytest.MonkeyPatch, home: Path, *folders: str) -> None:
    monkeypatch.setenv("INDEXED", os.pathsep.join(str(home / folder) for folder in folders))


def run(capsys: pytest.CaptureFixture[str]) -> tuple[int, dict, str]:
    try:
        main(["spotlight-check"])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capsys.readouterr()
    return code, json.loads(out), err


def test_folders_spotlight_skips_pass(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    indexed(monkeypatch, home, "Documents")
    code, line, err = run(capsys)
    assert code == 0, err
    assert line == {
        "control_indexed": True,
        "folders": [{"folder": "~/dev/github", "excluded": True}, {"folder": "~/dev/tmp", "excluded": True}],
    }
    assert not list(home.rglob("spotlight-probe-*"))  # every probe file is gone


def test_an_indexed_folder_fails_and_says_where_to_add_it(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    indexed(monkeypatch, home, "Documents", "dev/tmp")
    code, line, err = run(capsys)
    assert code == 1
    assert line["folders"][1] == {"folder": "~/dev/tmp", "excluded": False}
    assert "Spotlight still indexes ~/dev/tmp. The agent rules (AGENTS.md, Bulky scratch and Spotlight)" in err
    assert (home.parent / "opened").read_text() == spotlight.SETTINGS


def test_the_daily_run_opens_no_window(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    indexed(monkeypatch, home, "Documents", "dev/tmp")
    monkeypatch.setenv("SPOTLIGHT_NO_OPEN", "1")
    code, _, err = run(capsys)
    assert code == 1
    assert "Spotlight still indexes ~/dev/tmp." in err
    assert not (home.parent / "opened").exists()


def test_without_the_control_indexed_nothing_is_proved(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    indexed(monkeypatch, home)
    monkeypatch.setenv("SPOTLIGHT_SECONDS", "0")
    code, line, err = run(capsys)
    assert code == 3
    assert line["control_indexed"] is False
    assert {entry["excluded"] for entry in line["folders"]} == {None}  # no control, so no folder proved either way
    assert "nothing proved" in err


def test_it_polls_until_spotlight_catches_up(home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    indexed(monkeypatch, home, "Documents")
    monkeypatch.setenv("LATE", "1")
    result = spotlight.check(("~/dev/github", "~/absent"), "~/Documents", 30, settle=0, poll=0)
    assert result.control_indexed
    assert result.folders[0].excluded is True
    assert result.folders[1].excluded is None  # no such folder: nothing to probe
    assert (tmp_path / "calls").read_text() == "xx"


def test_a_probe_indexed_after_the_control_still_fails(
    home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    indexed(monkeypatch, home, "Documents", "dev/tmp")
    monkeypatch.setenv("PROBES_LATE", "1")
    result = spotlight.check(("~/dev/tmp",), "~/Documents", 30, settle=30, poll=0)
    assert result.folders[0].excluded is False  # without the settle wait it would have read as excluded
    assert (tmp_path / "calls").read_text() == "xx"


def test_a_folder_reached_through_a_symlink_is_matched_by_its_real_path(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (home / "scratch").symlink_to(home / "dev/tmp")
    indexed(monkeypatch, home, "Documents", "dev/tmp")
    result = spotlight.check(("~/scratch",), "~/Documents", 30, settle=0, poll=0)
    assert result.folders[0].excluded is False
