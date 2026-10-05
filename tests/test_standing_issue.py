# Copyright (c) 2026 Raymond Manaloto
"""Control exact-title standing issue updates at the subprocess boundary."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from dotfiles_setup import main, standing_issue

TITLE = "LLVM major currency (daily)"
REPO = "owner/repo"
BODY = Path("report.md")
SEARCH = [
    "gh",
    "issue",
    "list",
    "--repo",
    REPO,
    "--state",
    "open",
    "--search",
    f'in:title "{TITLE}"',
    "--json",
    "number,title",
]


@pytest.mark.parametrize("exact", [False, True])
def test_upsert_selects_only_exact_title(*, exact: bool) -> None:
    calls = []
    issues = [{"number": 8, "title": TITLE + " old"}]
    if exact:
        issues.append({"number": 9, "title": TITLE})

    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 0, json.dumps(issues) if len(calls) == 1 else "", ""
        )

    assert (
        standing_issue.standing_issue_main(
            repo=REPO, title=TITLE, body_file=BODY, runner=run
        )
        == 0
    )
    expected = (
        ["gh", "issue", "edit", "9", "--repo", REPO, "--body-file", str(BODY)]
        if exact
        else [
            "gh",
            "issue",
            "create",
            "--repo",
            REPO,
            "--title",
            TITLE,
            "--body-file",
            str(BODY),
            "--label",
            "dependencies,needs-triage",
        ]
    )
    assert calls == [SEARCH, expected]


@pytest.mark.parametrize("exact", [False, True])
def test_close_exact_match_or_noop(*, exact: bool) -> None:
    calls = []
    issues = [{"number": 8, "title": TITLE if exact else TITLE + " old"}]

    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 0, json.dumps(issues) if len(calls) == 1 else "", ""
        )

    assert (
        standing_issue.standing_issue_main(
            repo=REPO, title=TITLE, close_comment="Current", runner=run
        )
        == 0
    )
    expected = (
        [SEARCH, ["gh", "issue", "close", "8", "--repo", REPO, "--comment", "Current"]]
        if exact
        else [SEARCH]
    )
    assert calls == expected


@pytest.mark.parametrize("failure", ["search", "mutation", "json"])
def test_errors_do_not_become_absence(failure: str) -> None:
    calls = []

    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        failed = (failure == "search" and len(calls) == 1) or (
            failure == "mutation" and len(calls) == 2
        )
        return subprocess.CompletedProcess(
            argv,
            7 if failed else 0,
            "bad-json" if failure == "json" else "[]",
            "failed" if failed else "",
        )

    assert standing_issue.standing_issue_main(
        repo=REPO, title=TITLE, body_file=BODY, runner=run
    ) == (1 if failure == "json" else 7)
    assert len(calls) == (2 if failure == "mutation" else 1)


@pytest.mark.parametrize(
    ("body", "comment"),
    [
        (None, None),
        (BODY, "Current"),
    ],
)
def test_invalid_arguments_do_not_run(
    *, body: Path | None, comment: str | None
) -> None:
    def run(_: list[str]) -> subprocess.CompletedProcess[str]:
        pytest.fail("invalid arguments must not reach gh")

    assert (
        standing_issue.standing_issue_main(
            repo=REPO,
            title=TITLE,
            body_file=body,
            close_comment=comment,
            runner=run,
        )
        == 1
    )


def test_cli_dispatch_uses_argv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert kwargs["check"] is False
        assert kwargs["text"] is True
        assert kwargs["timeout"] == 120
        return subprocess.CompletedProcess(argv, 0, "[]", "")

    monkeypatch.setattr(subprocess, "run", run)
    args = main.setup_parser().parse_args(
        [
            "standing-issue",
            "--repo",
            REPO,
            "--title",
            TITLE,
            "--close",
            "--close-comment",
            "Current",
        ]
    )
    with pytest.raises(SystemExit) as result:
        main.run_command(args, tmp_path)
    assert result.value.code == 0
    assert calls == [SEARCH]


def test_cli_close_requires_comment(tmp_path: Path) -> None:
    args = main.setup_parser().parse_args(
        [
            "standing-issue",
            "--repo",
            REPO,
            "--title",
            TITLE,
            "--close",
        ]
    )
    with pytest.raises(SystemExit) as result:
        main.run_command(args, tmp_path)
    assert result.value.code == 1
