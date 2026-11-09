"""repotools test-times through its command line, over a real mise project's history and logs."""

import json
import subprocess
from pathlib import Path

import pytest

from repotools.cli import main

# Hostile but valid text from mise: a test id with quotes, a backslash, a tab, a control character and a JSON
# record of its own, and a task name with a quote and a backslash. Each must come back as one value, unchanged.
HOSTILE = '0.05s call     tests/test_b.py::test_x["a\\"b\tc\x01"] {"task":"injected","runs":9}'
ODD = 'odd "q\\ name:test'
# What the logged test task prints: a pytest run's durations block between other output and the summary rule.
OUTPUT = (
    "collected 3 items",
    "===== slowest 3 durations =====",
    "2.50s call     tests/test_a.py::test_slow",
    "",
    "0.10s setup    tests/test_a.py::test_fast",
    HOSTILE,
    "===== 3 passed in 2.70s =====",
    "after the summary",
)
# Five tasks run by real mise: three logged test tasks (one prints that block from a file, as one command, the way
# pytest is one: mise also logs each command line, `$ ...`), one test task whose output goes straight to the
# terminal (so mise keeps no log), and a task that is not a test.
PROJECT = f"""\
[settings]
task.logs = true

[tasks.test]
output = "prefix"
run = "cat output.txt"

[tasks."plain:test"]
output = "prefix"
run = "echo no durations here"

[tasks.'{ODD}']
output = "prefix"
run = "echo odd"

[tasks."raw:test"]
output = "interleave"
run = "echo straight to the terminal"

[tasks.build]
output = "prefix"
run = "echo built"
"""


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "mise.toml").write_text(PROJECT)
    (root / "output.txt").write_text("\n".join(OUTPUT) + "\n")
    monkeypatch.setenv("MISE_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("MISE_TRUSTED_CONFIG_PATHS", str(root))
    monkeypatch.setenv("MISE_CEILING_PATHS", str(tmp_path))
    monkeypatch.setenv("MISE_AUTO_INSTALL", "0")
    monkeypatch.chdir(root)
    for task in ("test", "plain:test", ODD, "raw:test", "build"):
        subprocess.run(["mise", "run", task], check=True, capture_output=True)
    return root


@pytest.mark.usefixtures("project")
def test_each_test_task_gets_its_history_and_slowest_tests(capsys: pytest.CaptureFixture[str]) -> None:
    main(["test-times"])
    rows = {row["task"]: row for row in map(json.loads, capsys.readouterr().out.splitlines())}
    assert set(rows) == {"test", "plain:test", ODD, "raw:test"}
    assert rows["test"]["slowest"] == [
        "2.50s call     tests/test_a.py::test_slow",
        "0.10s setup    tests/test_a.py::test_fast",
        HOSTILE,
    ]
    assert (rows["plain:test"]["slowest"], rows[ODD]["slowest"], rows["raw:test"]["slowest"]) == ([], [], [])
    assert {(row["runs"], row["failures"], row["last_status"]) for row in rows.values()} == {(1, 0, "ok")}
    assert all(isinstance(row["median_ms"], int) for row in rows.values())


def test_a_history_mise_cannot_read_is_one_error_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mise.toml").write_text("[tasks.test\n")  # not TOML: every mise command refuses the folder
    monkeypatch.setenv("MISE_TRUSTED_CONFIG_PATHS", str(tmp_path))
    monkeypatch.setenv("MISE_CEILING_PATHS", str(tmp_path.parent))
    with pytest.raises(SystemExit) as stop:
        main(["test-times"])
    assert stop.value.code == 1
    [event] = map(json.loads, capsys.readouterr().err.splitlines())
    assert event["error"].startswith("mise failed: ")
