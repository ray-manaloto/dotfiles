"""The command line: argument parsing and the failures it reports on stderr."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from workflowtools.cli import main


def failure(capsys: pytest.CaptureFixture[str], argv: list[str] | None) -> str:
    with pytest.raises(SystemExit) as stop:
        main(argv)
    assert stop.value.code == 1
    return json.loads(capsys.readouterr().err)["error"]


@pytest.mark.parametrize("argv", [[], ["lint"]])
def test_the_first_argument_must_name_a_check(capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
    assert failure(capsys, argv) == (
        "workflowtools: the first argument is one of frontmatter, skill-table, tickets, settings-local"
    )


def test_an_unknown_option_is_a_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert "unrecognized arguments: --nope" in failure(capsys, ["frontmatter", "--nope"])


def test_a_bad_listing_is_a_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert "listing" in failure(capsys, ["tickets", "--listing", "all"])


def test_outside_a_repository_git_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert failure(capsys, ["frontmatter"]).startswith("git failed: fatal: not a git repository")


@pytest.mark.usefixtures("repo")
def test_a_missing_status_table_is_a_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert "docs/agents/issue-tracker.md" in failure(capsys, ["tickets"])


@pytest.mark.usefixtures("repo")
def test_the_console_script_runs() -> None:
    script = Path(sys.executable).parent / "workflowtools"
    done = subprocess.run([script, "settings-local"], capture_output=True, check=False, text=True)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")
