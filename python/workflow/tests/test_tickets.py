"""workflowtools tickets, on .scratch tickets and the status table."""

from pathlib import Path

import pytest

from .conftest import report, write

STATUSES = """| Status | Meaning | Unblocks |
|---|---|---|
| `needs-triage` | new | no |
| `ready-for-agent` | specified | no |
| `claimed` | taken | no |
| `done` | merged | yes |
| `wontfix` | dropped | no |
"""
PR = "https://github.com/o/r/pull/7"


def tickets(root: Path, files: dict[str, str], table: str = STATUSES) -> None:
    write(root, {"docs/agents/issue-tracker.md": table})
    write(root, {f".scratch/{name}.md": text for name, text in files.items()})


def ticket(status: str, blocked: str | None = "None") -> str:
    return f"# T\n\nStatus: {status}\n" + ("" if blocked is None else f"**Blocked by:** {blocked}\n")


def details(capsys: pytest.CaptureFixture[str], *args: str) -> list[str | None]:
    return [line.get("detail") or line.get("path") for line in report(capsys, "tickets", *args)]


def test_no_status_table_is_reported(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tickets(repo, {}, table="# Tracker\n")
    assert details(capsys) == ["has no status table", None]


def test_an_unknown_feature_is_reported(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tickets(repo, {})
    assert report(capsys, "tickets", "--feature", "x") == [
        {"path": ".scratch/x", "check": "tickets", "detail": "no such feature"},
        {"exit": "1"},
    ]


def test_clean_tickets_pass(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tickets(
        repo,
        {
            "f/issues/01-a": f"**Status:** done {PR}\n",
            "f/issues/02-b": ticket("done pre-workflow"),
            "f/issues/03-c": ticket("ready-for-agent", "01, 02 (see 99)"),
            "f/issues/04-d": ticket("wontfix", "05"),
            "f/issues/05-e": ticket("wontfix", "None (dropped)"),
            "f/notes.md": "not a ticket\n",
        },
    )
    assert report(capsys, "tickets") == [{"exit": "0"}]


@pytest.mark.parametrize(
    ("files", "found"),
    [
        ({"f/issues/a": ticket("done")}, "name must start with a two-digit ticket number"),
        ({"f/issues/01-a": ticket("claimed"), "f/issues/01-b": ticket("claimed")}, "number 01 is used twice in f"),
        ({"f/issues/01-a": "no status\n"}, "needs exactly one Status line, found 0"),
        ({"f/issues/01-a": ticket("claimed") + "Status: done\n"}, "needs exactly one Status line, found 2"),
        ({"f/issues/01-a": ticket("started")}, "status 'started' is not in docs/agents/issue-tracker.md"),
        ({"f/issues/01-a": ticket("done")}, "done needs its PR link"),
        ({"f/issues/01-a": ticket("claimed") + "Blocked by: None\n"}, "more than one Blocked by line"),
        ({"f/issues/01-a": ticket("claimed", "later")}, "Blocked by needs ticket numbers or None"),
        ({"f/issues/01-a": ticket("claimed", "02")}, "blocker 02 is not another ticket in f"),
        ({"f/issues/01-a": ticket("claimed", "01")}, "blocker 01 is not another ticket in f"),
        (
            {"f/issues/01-a": ticket("claimed", "02"), "f/issues/02-b": ticket("needs-triage")},
            "is claimed but blocker 02 is needs-triage",
        ),
        (
            {"f/issues/01-a": ticket("ready-for-agent", "02"), "f/issues/02-b": ticket("wontfix")},
            "blocker 02 is wontfix, so this ticket can never start",
        ),
    ],
)
def test_a_bad_ticket_is_reported(
    repo: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str], found: str
) -> None:
    tickets(repo, files)
    assert found in details(capsys)


def test_a_cycle_is_reported_once(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tickets(
        repo,
        {
            "f/issues/01-a": ticket("ready-for-agent", "02"),
            "f/issues/02-b": ticket("ready-for-agent", "01"),
            "f/issues/03-c": ticket("ready-for-agent", "01, 02"),
        },
    )
    assert report(capsys, "tickets", "--listing", "open") == [
        {"path": ".scratch/f", "check": "tickets", "detail": "Blocking edges form a cycle: 01 -> 02 -> 01"},
        {"exit": "1"},
    ]


LISTED = {
    "f/issues/01-a": ticket(f"done {PR}"),
    "f/issues/02-b": ticket("ready-for-agent", "01"),
    "f/issues/03-c": ticket("ready-for-agent", "04"),
    "f/issues/04-d": ticket("claimed"),
    "f/issues/05-e": ticket("wontfix", None),
    "g/issues/01-a": ticket("needs-triage"),
    "g/issues/02-b": ticket("ready-for-agent"),
}


@pytest.mark.parametrize(
    ("args", "paths"),
    [
        (["--listing", "frontier"], ["f/issues/02-b", "g/issues/02-b"]),
        (["--listing", "frontier", "--feature", "g"], ["g/issues/02-b"]),
        (["--listing", "open"], ["f/issues/02-b", "f/issues/03-c", "f/issues/04-d", "g/issues/01-a", "g/issues/02-b"]),
        ([], []),
    ],
)
def test_a_clean_check_lists_tickets(
    repo: Path, capsys: pytest.CaptureFixture[str], args: list[str], paths: list[str]
) -> None:
    tickets(repo, LISTED)
    assert report(capsys, "tickets", *args) == [*({"path": f".scratch/{p}.md"} for p in paths), {"exit": "0"}]
