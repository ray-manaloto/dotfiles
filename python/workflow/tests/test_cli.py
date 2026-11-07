"""The command line: argument parsing and the failures it reports on stderr."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from workflowtools.cli import main

from .conftest import report


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


@pytest.mark.parametrize("feature", ["..", "../x", "*", "a/b"])
def test_a_feature_must_be_one_folder_name(capsys: pytest.CaptureFixture[str], feature: str) -> None:
    assert "feature" in failure(capsys, ["tickets", "--feature", feature])


def test_outside_a_repository_git_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert failure(capsys, ["frontmatter"]).startswith("git failed: fatal: not a git repository")


def test_a_git_error_reading_the_origin_fails_instead_of_skipping(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "task_plan.md").write_text("# Roadmap\n")
    with (repo / ".git" / "config").open("a") as config:
        config.write('[remote "origin"\n')
    assert failure(capsys, ["tickets"]).startswith("git failed: fatal: bad config line")


def test_a_missing_roadmap_is_a_finding_through_the_cli(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert report(capsys, "tickets") == [
        {"path": "task_plan.md", "check": "tickets", "detail": f"no roadmap at {repo / 'task_plan.md'}"},
        {"exit": "1"},
    ]


@pytest.mark.usefixtures("repo")
def test_the_console_script_runs() -> None:
    script = Path(sys.executable).parent / "workflowtools"
    done = subprocess.run([script, "settings-local"], capture_output=True, check=False, text=True)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


@pytest.mark.parametrize(
    "options",
    [["--listing", "open", "--rebuild"], ["--listing", "frontier", "--plan"], ["--rebuild", "--plan"]],
)
def test_two_ticket_modes_at_once_fail(capsys: pytest.CaptureFixture[str], options: list[str]) -> None:
    assert "workflowtools tickets: use one of --listing, --rebuild, --plan" in failure(capsys, ["tickets", *options])


@pytest.mark.parametrize("spec", ["0", "-1"])
def test_a_spec_below_one_is_refused(capsys: pytest.CaptureFixture[str], spec: str) -> None:
    assert "greater than or equal to 1" in failure(capsys, ["tickets", "--spec", spec])
