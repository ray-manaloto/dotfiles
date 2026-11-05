"""Roadmap tickets checked against real files, real git and an executable GitHub seam."""

import hashlib
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from workflowtools import roadmap
from workflowtools.cli import main

from .conftest import report, write

URL = "https://github.com/o/r/issues/"
SKIPPED = {
    "check": "tickets",
    "reason": "origin is not a GitHub repository: the GitHub scope was not checked",
}


@pytest.fixture(autouse=True)
def plan_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PWF_PLAN_ROOT", raising=False)
    monkeypatch.delenv("PLAN_ID", raising=False)


def ticket(number: int, *, checked: bool = False, plan: str | None = None, blocked: str = "none") -> str:
    association = f" — PLAN_ID {plan}" if plan else ""
    box = "x" if checked else " "
    return f"- [{box}] #{number} Ticket {number} ({URL}{number}){association} — blocked by {blocked}\n"


def write_roadmap(root: Path, lines: str, *, spec: int = 9, name: str = "task_plan.md") -> None:
    write(root, {name: f"## group:example — spec #{spec}\n\n{lines}"})


def finding(detail: str, *, path: str = "task_plan.md") -> dict[str, str]:
    return {"path": path, "check": "tickets", "detail": detail}


def test_a_line_without_an_issue_link_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, "- [ ] #10 No link\n")
    assert report(capsys, "tickets") == [
        finding("line 3: a ticket line needs #N <title> (<issue link>)"),
        SKIPPED,
        {"exit": "1"},
    ]


def test_a_link_to_another_number_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10).replace(f"{URL}10", f"{URL}11"))
    assert report(capsys, "tickets")[0] == finding("line 3: #10 links to issue 11")


def test_a_ticket_line_without_blocked_by_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, f"- [ ] #9 Spec ({URL}9)\n- [ ] #10 Ticket ({URL}10)\n")
    assert report(capsys, "tickets") == [
        finding('line 4: #10 needs "— blocked by none" or "— blocked by #M, ..."'),
        SKIPPED,
        {"exit": "1"},
    ]


def test_a_ticket_listed_twice_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10) + ticket(10))
    assert report(capsys, "tickets")[0] == finding("line 4: #10 is already on line 3")


def test_a_missing_roadmap_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert report(capsys, "tickets") == [finding(f"no roadmap at {repo / 'task_plan.md'}"), {"exit": "1"}]


@pytest.mark.parametrize(
    ("text", "args", "detail"),
    [
        ("## Parked\n- [ ] bad\n", [], "the roadmap has no spec section"),
        ("## spec #8 Other\n", ["--spec", "9"], "the roadmap has no section for spec #9"),
    ],
)
def test_a_roadmap_without_a_spec_section_fails(
    repo: Path, capsys: pytest.CaptureFixture[str], text: str, args: list[str], detail: str
) -> None:
    write(repo, {"task_plan.md": text})
    assert report(capsys, "tickets", *args) == [finding(detail), {"exit": "1"}]


def test_lines_outside_spec_sections_are_not_read(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        repo,
        {
            "task_plan.md": "- [ ] before\n## spec #9 Work\nprose\n- plain bullet\n\n"
            + ticket(10)
            + "## Parked\n- [ ] malformed\n# Next\n- [ ] also malformed\n"
        },
    )
    assert report(capsys, "tickets") == [SKIPPED, {"exit": "0"}]


def test_the_roadmap_option_reads_that_file(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10), name="other.md")
    assert report(capsys, "tickets", "--roadmap", "other.md") == [SKIPPED, {"exit": "0"}]
    write_roadmap(repo, "- [ ] bad\n", name="other.md")
    assert report(capsys, "tickets", "--roadmap", "other.md")[0] == finding(
        "line 3: a ticket line needs #N <title> (<issue link>)", path="other.md"
    )


def test_spec_option_checks_only_that_section(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10) + "## spec #20 Other\n- [ ] bad\n")
    assert report(capsys, "tickets", "--spec", "9") == [SKIPPED, {"exit": "0"}]


def test_a_listing_keeps_line_numbers_and_local_notes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10, plan="a", blocked="#2, #1; ignore #99"))
    assert report(capsys, "tickets", "--listing", "open") == [
        SKIPPED,
        {
            "kind": "ticket",
            "number": 10,
            "title": "Ticket 10",
            "url": f"{URL}10",
            "spec": 9,
            "line": 3,
            "checked": False,
            "plan_id": "a",
            "blocked_by": [2, 1],
            "state": None,
        },
        {"exit": "0"},
    ]


def test_no_origin_skips_and_says_so(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10))
    assert report(capsys, "tickets") == [SKIPPED, {"exit": "0"}]


def test_require_github_turns_a_skip_into_exit_2(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10))
    assert report(capsys, "tickets", "--require-github") == [SKIPPED, {"exit": "2"}]


def issue(number: int, state: str = "open") -> dict[str, object]:
    return {"number": number, "title": f"GitHub title {number}", "state": state, "html_url": f"{URL}{number}"}


def responses(*children: dict[str, object]) -> dict[str, object]:
    return {
        "repos/o/r/issues/9": {**issue(9), "body": "Extra fields are accepted"},
        "repos/o/r/issues/9/sub_issues": [list(children)],
        **{f"repos/o/r/issues/{child['number']}/dependencies/blocked_by": [[]] for child in children},
    }


def unavailable(detail: str) -> dict[str, str]:
    return {"kind": "github-unavailable", "check": "tickets", "repo": "o/r", "detail": detail}


def test_a_spec_split_into_two_sections_lists_both(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10) + "## more of spec #9\n" + ticket(11))
    lines = report(capsys, "tickets", "--listing", "open")
    assert lines[0] == SKIPPED
    assert [(line["number"], line["spec"], line["line"]) for line in lines[1:-1]] == [(10, 9, 3), (11, 9, 5)]
    assert lines[-1] == {"exit": "0"}


def test_a_clean_roadmap_matches_github(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, f"- [ ] #9 Local title ({URL}9)\n" + ticket(10) + ticket(11, checked=True))
    data = responses(issue(10), issue(11, "closed"))
    data["repos/o/r/issues/9/sub_issues"] = [[issue(10)], [issue(11, "closed")]]
    log = gh_stand_in(data, set())
    assert report(capsys, "tickets") == [{"exit": "0"}]
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        ["api", "repos/o/r/issues/9"],
        ["api", "--paginate", "--slurp", "repos/o/r/issues/9/sub_issues"],
        ["api", "--paginate", "--slurp", "repos/o/r/issues/10/dependencies/blocked_by"],
        ["api", "--paginate", "--slurp", "repos/o/r/issues/11/dependencies/blocked_by"],
    ]


def test_gh_missing_is_reported_unavailable_and_exits_2(
    roadmap_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, ticket(10))
    git = shutil.which("git")
    assert git is not None
    directory = tmp_path / "nogh"
    directory.mkdir()
    (directory / "git").symlink_to(git)
    monkeypatch.setenv("PATH", str(directory))
    assert report(capsys, "tickets") == [unavailable("gh is not installed"), {"exit": "2"}]


@pytest.mark.parametrize(
    "endpoint", ["repos/o/r/issues/9", "repos/o/r/issues/9/sub_issues", "repos/o/r/issues/10/dependencies/blocked_by"]
)
def test_gh_failing_is_reported_unavailable_and_exits_2(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    endpoint: str,
) -> None:
    write_roadmap(roadmap_repo, ticket(10))
    log = gh_stand_in(responses(issue(10)), {endpoint})
    assert report(capsys, "tickets") == [unavailable("HTTP 503"), {"exit": "2"}]
    assert json.loads(log.read_text().splitlines()[-1])[-1] == endpoint


@pytest.mark.parametrize(
    ("endpoint", "value"),
    [
        ("repos/o/r/issues/9", "<not json>"),
        ("repos/o/r/issues/9", {"number": 9}),
        ("repos/o/r/issues/9", {**issue(9), "state": "unknown"}),
        ("repos/o/r/issues/9/sub_issues", "<not json>"),
        ("repos/o/r/issues/9/sub_issues", [issue(10)]),
        ("repos/o/r/issues/10/dependencies/blocked_by", [[{"number": 3}]]),
    ],
)
def test_gh_output_that_is_not_json_is_unavailable(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    endpoint: str,
    value: object,
) -> None:
    write_roadmap(roadmap_repo, ticket(10))
    log = gh_stand_in({**responses(issue(10)), endpoint: value}, set())
    assert report(capsys, "tickets") == [unavailable("gh returned output that is not the expected JSON"), {"exit": "2"}]
    assert json.loads(log.read_text().splitlines()[-1])[-1] == endpoint


def test_a_local_finding_exits_1_even_when_github_is_unavailable(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, "- [ ] broken\n")
    gh_stand_in({}, {"repos/o/r/issues/9"})
    assert report(capsys, "tickets", "--require-github") == [
        finding("line 3: a ticket line needs #N <title> (<issue link>)"),
        unavailable("HTTP 503"),
        {"exit": "1"},
    ]


@pytest.mark.parametrize("args", [[], ["--require-github"]])
def test_a_non_github_origin_skips_and_says_so(
    roadmap_repo: Path, capsys: pytest.CaptureFixture[str], args: list[str]
) -> None:
    subprocess.run(["git", "remote", "set-url", "origin", "/some/path"], check=True)
    write_roadmap(roadmap_repo, ticket(10))
    assert report(capsys, "tickets", *args) == [SKIPPED, {"exit": "2" if args else "0"}]


@pytest.mark.parametrize("remote", ["https://github.com/o/r.git", "git@github.com:o/r.git", "https://github.com/o/r/"])
def test_require_github_with_a_matching_roadmap_exits_0(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    remote: str,
) -> None:
    subprocess.run(["git", "remote", "set-url", "origin", remote], check=True)
    write_roadmap(roadmap_repo, ticket(10))
    gh_stand_in(responses(issue(10)), set())
    assert report(capsys, "tickets", "--require-github") == [{"exit": "0"}]


def test_a_sub_issue_without_a_roadmap_line_fails(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, ticket(10))
    gh_stand_in(responses(issue(10), issue(11)), set())
    assert report(capsys, "tickets") == [finding("spec #9: sub-issue #11 has no roadmap line"), {"exit": "1"}]


def test_a_line_that_is_not_a_sub_issue_fails(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, ticket(10))
    gh_stand_in({**responses(), "repos/o/r/issues/10/dependencies/blocked_by": [[]]}, set())
    assert report(capsys, "tickets") == [finding("line 3: #10 is not a sub-issue of spec #9"), {"exit": "1"}]


@pytest.mark.parametrize(("checked", "state"), [(False, "closed"), (True, "open")])
def test_a_checkbox_against_the_issue_state_fails(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    *,
    checked: bool,
    state: str,
) -> None:
    write_roadmap(roadmap_repo, ticket(10, checked=checked))
    gh_stand_in(responses(issue(10, state)), set())
    assert report(capsys, "tickets") == [finding(f"line 3: #10 is {state} on GitHub"), {"exit": "1"}]


@pytest.mark.parametrize(("blockers", "expected"), [([], "none"), ([3, 2], "#2, #3")])
def test_blockers_that_differ_from_github_fail(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    blockers: list[int],
    expected: str,
) -> None:
    write_roadmap(roadmap_repo, ticket(10, blocked="#1; ignore #2 and #3"))
    blocked_by = [[issue(n) for n in blockers]]
    gh_stand_in({**responses(issue(10)), "repos/o/r/issues/10/dependencies/blocked_by": blocked_by}, set())
    assert report(capsys, "tickets") == [finding(f"line 3: #10 is blocked by {expected} on GitHub"), {"exit": "1"}]


def test_blocker_notes_are_not_compared(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, ticket(10, blocked="#2, #1, #2 (ignore #99)"))
    blocked_by = [[issue(1)], [issue(2)]]
    gh_stand_in({**responses(issue(10)), "repos/o/r/issues/10/dependencies/blocked_by": blocked_by}, set())
    assert report(capsys, "tickets") == [{"exit": "0"}]


def test_a_link_to_another_repository_fails(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, ticket(10).replace("github.com/o/r", "github.com/else/where"))
    gh_stand_in(responses(issue(10)), set())
    assert report(capsys, "tickets") == [finding("line 3: #10 links to else/where, not the origin o/r"), {"exit": "1"}]


def test_github_scope_follows_the_spec_option(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, ticket(10) + "## spec #20 Other\n- [ ] malformed\n")
    log = gh_stand_in(responses(issue(10)), set())
    assert report(capsys, "tickets", "--spec", "9", "--require-github") == [{"exit": "0"}]
    assert len(log.read_text().splitlines()) == 3


def test_frontier_lists_open_tickets_whose_blockers_are_closed(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(
        roadmap_repo,
        ticket(9) + ticket(12, blocked="#3") + ticket(10, blocked="#1") + ticket(11) + ticket(13, checked=True),
    )
    gh_stand_in(
        {
            **responses(issue(10), issue(11), issue(12), issue(13, "closed")),
            "repos/o/r/issues/10/dependencies/blocked_by": [[issue(1, "closed")]],
            "repos/o/r/issues/12/dependencies/blocked_by": [[issue(3)]],
        },
        set(),
    )
    lines = report(capsys, "tickets", "--listing", "frontier", "--require-github")
    assert lines == [
        {
            "kind": "ticket",
            "number": 10,
            "title": "Ticket 10",
            "url": f"{URL}10",
            "spec": 9,
            "line": 5,
            "checked": False,
            "plan_id": None,
            "blocked_by": [1],
            "state": "open",
        },
        {
            "kind": "ticket",
            "number": 11,
            "title": "Ticket 11",
            "url": f"{URL}11",
            "spec": 9,
            "line": 6,
            "checked": False,
            "plan_id": None,
            "blocked_by": [],
            "state": "open",
        },
        {"exit": "0"},
    ]


def test_frontier_without_github_uses_checkboxes_and_holds_unknown_blockers(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(repo, ticket(10, checked=True) + ticket(12, blocked="#99") + ticket(11, blocked="#10") + ticket(13))
    lines = report(capsys, "tickets", "--listing", "frontier")
    assert lines[0] == SKIPPED
    assert [(line["number"], line["state"]) for line in lines[1:-1]] == [(11, None), (13, None)]
    assert lines[-1] == {"exit": "0"}


def test_open_lists_every_unchecked_ticket(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(9) + ticket(10, checked=True) + ticket(12, blocked="#99") + ticket(11))
    lines = report(capsys, "tickets", "--listing", "open")
    assert lines[0] == SKIPPED
    assert [line["number"] for line in lines[1:-1]] == [12, 11]
    assert lines[-1] == {"exit": "0"}


def test_a_listing_after_a_finding_lists_nothing(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, "- [ ] malformed\n" + ticket(10))
    assert report(capsys, "tickets", "--listing", "open") == [
        finding("line 3: a ticket line needs #N <title> (<issue link>)"),
        SKIPPED,
        {"exit": "1"},
    ]


def test_listing_with_github_unavailable_lists_nothing(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(roadmap_repo, ticket(10))
    gh_stand_in({}, {"repos/o/r/issues/9"})
    assert report(capsys, "tickets", "--listing", "open") == [unavailable("HTTP 503"), {"exit": "2"}]


def test_listing_that_requires_github_does_not_list_a_skipped_scope(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_roadmap(repo, ticket(10))
    assert report(capsys, "tickets", "--require-github", "--listing", "frontier") == [SKIPPED, {"exit": "2"}]


def write_plan(root: Path, plan_id: str, number: int) -> Path:
    folder = root.parent / f"{root.name}.plans" / ".planning" / plan_id
    write(folder, {"task_plan.md": f"# Goal\n\nImplement {URL}{number}\n"})
    return folder


def rebuilt(capsys: pytest.CaptureFixture[str], *args: str) -> str:
    main(["tickets", "--rebuild", *args])
    output = capsys.readouterr()
    assert output.err == ""
    return output.out


def expected_rebuild() -> str:
    return (
        f"## spec #9 GitHub title 9 ({URL}9)\n\n"
        f"- [ ] #9 GitHub title 9 ({URL}9)\n"
        f"- [ ] #10 GitHub title 10 ({URL}10) — PLAN_ID a — blocked by none\n"
        f"- [x] #11 GitHub title 11 ({URL}11) — blocked by #1, #2\n\n"
    )


def rebuild_data() -> dict[str, object]:
    return {
        **responses(issue(10), issue(11, "closed")),
        "repos/o/r/issues/11/dependencies/blocked_by": [[issue(2, "closed"), issue(1, "closed")]],
    }


def test_the_rebuilt_roadmap_has_the_same_links_and_plan_associations(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_plan(roadmap_repo, "a", 10)
    write_roadmap(roadmap_repo, ticket(9) + ticket(10, plan="a") + ticket(11, checked=True, blocked="#1, #2"))
    gh_stand_in(rebuild_data(), set())
    original, _, _ = roadmap.read(roadmap_repo / "task_plan.md")
    output = rebuilt(capsys)
    assert output == expected_rebuild()
    write(roadmap_repo, {"rebuilt.md": output})
    recovered, _, found = roadmap.read(roadmap_repo / "rebuilt.md")
    assert found == []
    assert {(line.number, line.url, line.plan_id) for line in recovered} == {
        (line.number, line.url, line.plan_id) for line in original
    }


def test_the_rebuilt_roadmap_passes_the_check(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_plan(roadmap_repo, "a", 10)
    write_roadmap(roadmap_repo, ticket(10, plan="a") + ticket(11, checked=True, blocked="#1, #2"))
    gh_stand_in(rebuild_data(), set())
    write(roadmap_repo, {"rebuilt.md": rebuilt(capsys)})
    assert report(capsys, "tickets", "--roadmap", "rebuilt.md", "--require-github") == [{"exit": "0"}]


@pytest.mark.usefixtures("repo")
def test_rebuild_needs_a_github_origin(capsys: pytest.CaptureFixture[str]) -> None:
    assert report(capsys, "tickets", "--rebuild", "--spec", "9") == [
        finding("--rebuild needs a GitHub origin"),
        {"exit": "1"},
    ]


@pytest.mark.parametrize("path", [None, "absent.md", "unreadable"])
def test_rebuild_with_spec_recovers_a_missing_roadmap(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    path: str | None,
) -> None:
    write_plan(roadmap_repo, "a", 10)
    (roadmap_repo / "unreadable").mkdir()
    gh_stand_in(rebuild_data(), set())
    args = ["--roadmap", path] if path is not None else []
    output = rebuilt(capsys, "--spec", "9", *args)
    assert output == expected_rebuild()
    assert not (roadmap_repo / "task_plan.md").exists()
    write(roadmap_repo, {"rebuilt.md": output})
    assert report(capsys, "tickets", "--roadmap", "rebuilt.md", "--require-github") == [{"exit": "0"}]


@pytest.mark.parametrize(
    "lines",
    [
        f"- [ ] broken\n- [ ] #10 Missing blockers ({URL}10)\n",
        ticket(10, checked=True, blocked="#99") + ticket(11, blocked="none"),
        ticket(10),
    ],
    ids=["malformed-lines", "stale-states-and-blockers", "new-sub-issues"],
)
def test_rebuild_recovers_from_local_drift(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    lines: str,
) -> None:
    write_plan(roadmap_repo, "a", 10)
    write_roadmap(roadmap_repo, lines)
    original = (roadmap_repo / "task_plan.md").read_bytes()
    gh_stand_in(rebuild_data(), set())
    assert rebuilt(capsys) == expected_rebuild()
    assert (roadmap_repo / "task_plan.md").read_bytes() == original


@pytest.mark.parametrize("text", [None, "## Parked\n- [ ] malformed\n"])
def test_rebuild_without_spec_and_without_a_roadmap_fails(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    text: str | None,
) -> None:
    if text is not None:
        write(roadmap_repo, {"task_plan.md": text})
    log = gh_stand_in({}, set())
    assert report(capsys, "tickets", "--rebuild") == [
        finding("--rebuild without a readable spec section needs --spec N"),
        {"exit": "1"},
    ]
    assert not log.exists()


@pytest.mark.parametrize("endpoint", ["repos/o/r/issues/9", "repos/o/r/issues/11/dependencies/blocked_by"])
@pytest.mark.usefixtures("roadmap_repo")
def test_rebuild_with_github_unavailable_exits_2_and_prints_no_markdown(
    gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str], endpoint: str
) -> None:
    gh_stand_in(rebuild_data(), {endpoint})
    assert report(capsys, "tickets", "--rebuild", "--spec", "9") == [unavailable("HTTP 503"), {"exit": "2"}]


@pytest.mark.parametrize("mode", [[], ["--rebuild"]])
def test_two_plans_naming_one_issue_fail(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    capsys: pytest.CaptureFixture[str],
    mode: list[str],
) -> None:
    first = write_plan(roadmap_repo, "a", 10)
    write_plan(roadmap_repo, "b", 10)
    write_roadmap(roadmap_repo, ticket(10, plan="a"))
    gh_stand_in(responses(issue(10)), set())
    assert report(capsys, "tickets", *mode) == [
        finding("plans a and b both name #10", path=str(first.parent)),
        {"exit": "1"},
    ]


def test_a_plan_id_whose_plan_names_another_issue_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_plan(repo, "a", 11)
    write_roadmap(repo, ticket(10, plan="a"))
    assert report(capsys, "tickets") == [finding("line 3: PLAN_ID a belongs to #11"), SKIPPED, {"exit": "1"}]


@pytest.mark.parametrize("named", [None, "other"])
def test_a_plan_for_a_line_without_its_plan_id_fails(
    repo: Path, capsys: pytest.CaptureFixture[str], named: str | None
) -> None:
    write_plan(repo, "a", 10)
    write_roadmap(repo, ticket(10, plan=named))
    assert report(capsys, "tickets") == [
        finding(f"line 3: #10 has plan a but its line names {named or 'none'}"),
        SKIPPED,
        {"exit": "1"},
    ]


def test_a_plan_without_a_goal_link_names_nothing(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = write_plan(repo, "a", 10)
    write(folder, {"task_plan.md": f"Notes about {URL}10\n"})
    write_roadmap(repo, ticket(10))
    assert report(capsys, "tickets") == [SKIPPED, {"exit": "0"}]


def test_a_missing_named_plan_is_allowed_by_the_check(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_roadmap(repo, ticket(10, plan="not-created"))
    assert report(capsys, "tickets") == [SKIPPED, {"exit": "0"}]


def test_pwf_plan_root_moves_the_planning_folder(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "external"
    write(root, {".planning/a/task_plan.md": f"Implement {URL}10\n"})
    monkeypatch.setenv("PWF_PLAN_ROOT", str(root))
    write_roadmap(repo, ticket(10))
    assert report(capsys, "tickets") == [
        finding("line 3: #10 has plan a but its line names none"),
        SKIPPED,
        {"exit": "1"},
    ]


def test_rebuild_preserves_spec_order_and_spec_plan_associations(
    roadmap_repo: Path, gh_stand_in: Callable[[dict[str, object], set[str]], Path], capsys: pytest.CaptureFixture[str]
) -> None:
    write_plan(roadmap_repo, "spec-plan", 20)
    write_roadmap(roadmap_repo, "## spec #9 Other\n", spec=20)
    spec = {"repos/o/r/issues/20": issue(20, "closed"), "repos/o/r/issues/20/sub_issues": [[]]}
    gh_stand_in({**responses(), **spec}, set())
    assert rebuilt(capsys) == (
        f"## spec #20 GitHub title 20 ({URL}20)\n\n"
        f"- [x] #20 GitHub title 20 ({URL}20) — PLAN_ID spec-plan\n\n"
        f"## spec #9 GitHub title 9 ({URL}9)\n\n- [ ] #9 GitHub title 9 ({URL}9)\n\n"
    )


def test_two_worktrees_resolve_their_own_plans_and_leave_the_roadmap_unchanged(
    roadmap_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    plans = {name: write_plan(roadmap_repo, name, number) for name, number in [("a", 10), ("b", 11)]}
    write_roadmap(roadmap_repo, ticket(10, plan="a") + ticket(11, plan="b"))
    before = hashlib.sha256((roadmap_repo / "task_plan.md").read_bytes()).hexdigest()
    workers = [tmp_path / "w1", tmp_path / "w2"]
    for folder in workers:
        subprocess.run(["git", "worktree", "add", "-q", "-b", folder.name, folder], check=True)
    for folder, (name, number) in zip(workers, [("a", 10), ("b", 11)], strict=True):
        monkeypatch.chdir(folder)
        monkeypatch.setenv("PLAN_ID", name)
        assert report(capsys, "tickets", "--plan", "--require-github") == [
            {"kind": "plan", "plan_id": name, "path": str(plans[name]), "issue": number, "url": f"{URL}{number}"},
            {"exit": "0"},
        ]
    assert hashlib.sha256((roadmap_repo / "task_plan.md").read_bytes()).hexdigest() == before
    for folder in [roadmap_repo, *workers]:
        assert (
            subprocess.run(
                ["git", "-C", folder, "status", "--porcelain"], check=True, capture_output=True, text=True
            ).stdout
            == ""
        )


@pytest.mark.parametrize("plan_id", [None, ""])
@pytest.mark.usefixtures("repo")
def test_plan_without_plan_id_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], plan_id: str | None
) -> None:
    if plan_id is not None:
        monkeypatch.setenv("PLAN_ID", plan_id)
    assert report(capsys, "tickets", "--plan") == [finding("PLAN_ID is not set"), {"exit": "1"}]


def test_plan_with_a_missing_roadmap_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PLAN_ID", "a")
    assert report(capsys, "tickets", "--plan") == [finding(f"no roadmap at {repo / 'task_plan.md'}"), {"exit": "1"}]


def test_plan_without_its_folder_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PLAN_ID", "a")
    write_roadmap(repo, ticket(10, plan="a"))
    assert report(capsys, "tickets", "--plan") == [
        finding(f"no plan at {repo.parent / 'repo.plans' / '.planning' / 'a'}"),
        {"exit": "1"},
    ]


def test_plan_on_no_roadmap_line_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PLAN_ID", "a")
    write_roadmap(repo, ticket(10, plan="another") + "## Parked\n" + ticket(11, plan="a"))
    assert report(capsys, "tickets", "--plan") == [finding("PLAN_ID a is on no roadmap line"), {"exit": "1"}]


def test_plan_never_calls_gh(
    roadmap_repo: Path,
    gh_stand_in: Callable[[dict[str, object], set[str]], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder = write_plan(roadmap_repo, "a", 10)
    monkeypatch.setenv("PLAN_ID", "a")
    write_roadmap(roadmap_repo, ticket(10, plan="a"))
    log = gh_stand_in({}, {"repos/o/r/issues/9"})
    assert report(capsys, "tickets", "--plan", "--require-github") == [
        {"kind": "plan", "plan_id": "a", "path": str(folder), "issue": 10, "url": f"{URL}10"},
        {"exit": "0"},
    ]
    assert not log.exists()


@pytest.mark.parametrize("malformed", ["- [ ] bad\n", "- [ ] bad — PLAN_ID a\n"])
def test_plan_stops_on_a_roadmap_finding(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], malformed: str
) -> None:
    write_plan(repo, "a", 10)
    monkeypatch.setenv("PLAN_ID", "a")
    write_roadmap(repo, malformed + ticket(10, plan="a"))
    assert report(capsys, "tickets", "--plan") == [
        finding("line 3: a ticket line needs #N <title> (<issue link>)"),
        {"exit": "1"},
    ]


def test_plan_ignores_drift_in_another_section(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = write_plan(repo, "a", 10)
    write_plan(repo, "unrelated-one", 20)
    write_plan(repo, "unrelated-two", 20)
    monkeypatch.setenv("PLAN_ID", "a")
    write_roadmap(repo, ticket(10, plan="a") + "## spec #20 Other\n- [ ] malformed\n" + ticket(20))
    assert report(capsys, "tickets", "--plan") == [
        {"kind": "plan", "plan_id": "a", "path": str(folder), "issue": 10, "url": f"{URL}10"},
        {"exit": "0"},
    ]


def test_plan_duplicates_in_its_section_stop_resolution(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = write_plan(repo, "a", 10)
    write_plan(repo, "b", 10)
    monkeypatch.setenv("PLAN_ID", "a")
    write_roadmap(repo, ticket(10, plan="a"))
    assert report(capsys, "tickets", "--plan") == [
        finding("plans a and b both name #10", path=str(folder.parent)),
        {"exit": "1"},
    ]


def test_plan_id_in_a_title_does_not_resolve_as_an_association(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_plan(repo, "a", 10)
    monkeypatch.setenv("PLAN_ID", "a")
    write_roadmap(repo, ticket(11).replace("Ticket 11", "Title — PLAN_ID a"))
    assert report(capsys, "tickets", "--plan") == [finding("PLAN_ID a is on no roadmap line"), {"exit": "1"}]


def test_local_findings_follow_roadmap_line_order(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_plan(repo, "a", 11)
    write_roadmap(repo, ticket(10, plan="a") + "- [ ] malformed\n")
    assert report(capsys, "tickets") == [
        finding("line 3: PLAN_ID a belongs to #11"),
        finding("line 4: a ticket line needs #N <title> (<issue link>)"),
        SKIPPED,
        {"exit": "1"},
    ]
