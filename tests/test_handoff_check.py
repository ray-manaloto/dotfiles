# Copyright (c) 2026 Raymond Manaloto
"""Tests for the scoped session handoff citation checker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import handoff_check
from dotfiles_setup import main as cli_main

_COMMAND_TIMEOUT = 30


def _repo(tmp_path: Path) -> Path:
    subprocess.run(
        ["git", "init", "-q", "-b", "work"],
        cwd=tmp_path,
        check=True,
        timeout=_COMMAND_TIMEOUT,
    )
    return tmp_path


def _task_listing(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    output: str,
) -> None:
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert cmd == ["mise", "tasks", "ls"]
        assert kwargs["cwd"] == repo
        assert kwargs["timeout"] == _COMMAND_TIMEOUT
        return subprocess.CompletedProcess(cmd, 0, output, "")

    monkeypatch.setattr(handoff_check.subprocess, "run", fake_run)


def test_check_reports_missing_paths_and_bad_line_ranges(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    docs = repo / "docs"
    docs.mkdir()
    (docs / "short.md").write_text("one\ntwo\n")

    findings = handoff_check.check(
        repo,
        "Valid docs/short.md:2; missing `docs/gone.md:1`; stale docs/short.md:3-4.",
    )

    assert findings == [
        handoff_check.Finding(
            handoff_check.Verdict.MISSING_PATH,
            "docs/gone.md:1",
            "repo-relative path 'docs/gone.md' does not exist",
        ),
        handoff_check.Finding(
            handoff_check.Verdict.BAD_LINE_RANGE,
            "docs/short.md:3-4",
            "cited lines 3-4 are outside the file's 1-2 range",
        ),
    ]


@pytest.mark.parametrize(
    ("citation", "relative_path", "contents", "expected"),
    [
        ("Makefile:10", "Makefile", "line\n" * 10, []),
        (
            "Makefile:10",
            "Makefile",
            None,
            [
                handoff_check.Finding(
                    handoff_check.Verdict.MISSING_PATH,
                    "Makefile:10",
                    "repo-relative path 'Makefile' does not exist",
                )
            ],
        ),
        (
            ".devcontainer/Dockerfile:5-10",
            ".devcontainer/Dockerfile",
            "line\n" * 10,
            [],
        ),
        (
            ".devcontainer/Dockerfile:5-10",
            ".devcontainer/Dockerfile",
            "line\n" * 9,
            [
                handoff_check.Finding(
                    handoff_check.Verdict.BAD_LINE_RANGE,
                    ".devcontainer/Dockerfile:5-10",
                    "cited lines 5-10 are outside the file's 1-9 range",
                )
            ],
        ),
    ],
)
def test_check_validates_allowlisted_extensionless_path_citations(
    tmp_path: Path,
    citation: str,
    relative_path: str,
    contents: str | None,
    expected: list[handoff_check.Finding],
) -> None:
    repo = _repo(tmp_path)
    if contents is not None:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)

    assert handoff_check.check(repo, f"See {citation}") == expected


def test_check_ignores_non_allowlisted_bare_extensionless_words(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)

    assert handoff_check.check(repo, "see LICENSE:1") == []


def test_check_rejects_existing_path_outside_repo_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _repo(repo)
    (tmp_path / "outside.txt").write_text("outside\n")

    findings = handoff_check.check(repo, "See ../outside.txt:1")

    assert [finding.verdict for finding in findings] == [
        handoff_check.Verdict.MISSING_PATH
    ]


def test_check_ignores_numeric_ratios_as_path_citations(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    assert handoff_check.check(repo, "load 13.5:2, ratio 2.5:1") == []


def test_check_ignores_mise_flags_and_documented_cross_repo_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)

    def unexpected_run(
        *_args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        message = "mise tasks ls should not run for ignored citations"
        raise AssertionError(message)

    monkeypatch.setattr(handoff_check.subprocess, "run", unexpected_run)

    assert (
        handoff_check.check(
            repo,
            "mise run -C /some/path kb-currency-check and mise run kb-ship",
        )
        == []
    )


def test_check_parses_real_headerless_task_listing_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path)
    _task_listing(
        monkeypatch,
        repo,
        "lint Run lint\nsession-state Print state\n",
    )

    findings = handoff_check.check(
        repo,
        "Run mise run lint, skip out-of-scope mise run deps:python, then "
        "mise run missing-task -- --check.",
    )

    assert findings == [
        handoff_check.Finding(
            handoff_check.Verdict.UNKNOWN_TASK,
            "mise run missing-task",
            "mise task 'missing-task' is not listed by mise tasks ls",
        )
    ]


def test_newest_handoff_orders_by_date_then_letter_without_mtime(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    plans = repo / ".agent" / "plans"
    plans.mkdir(parents=True)
    for name in (
        "session-2026-08-28z.md",
        "session-2026-08-29.md",
        "session-2026-08-29b.md",
        "session-2026-08-29c.md",
        "session-2026-08-29d.md",
        "session-2026-08-29-e.md",
        "session-not-a-date.md",
    ):
        (plans / name).write_text(name)

    # The unhyphenated form is what every real handoff in this repo uses
    # (`agent-artifact-conventions.md` documents the hyphenated form; real
    # practice never uses it) — the regex must accept both, and the
    # hyphenated `-e` still orders after the unhyphenated `d`.
    assert handoff_check.newest_handoff(repo) == plans / "session-2026-08-29-e.md"


def test_main_prints_explicit_no_handoff_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)

    assert handoff_check.main([], repo) == 0
    assert "no handoff found" in capsys.readouterr().out


def test_main_checks_a_specific_handoff_and_parser_wiring(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    (repo / "notes.md").write_text("one\n")
    handoff = repo / "handoff.md"
    handoff.write_text("See notes.md:1 and run mise run lint.\n")
    _task_listing(monkeypatch, repo, "lint Run lint\n")

    parsed = cli_main.setup_parser().parse_args(["handoff-check", "handoff.md"])
    assert parsed.command == "handoff-check"
    assert parsed.path == "handoff.md"

    assert handoff_check.main(["handoff.md"], repo) == 0
    assert "OK" in capsys.readouterr().out


def test_main_reports_cited_file_read_failure_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    cited = repo / "notes.md"
    cited.write_text("one\n")
    handoff = repo / "handoff.md"
    handoff.write_text("See notes.md:1.\n")
    original_read_text = Path.read_text

    def read_text_with_failure(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        if path == cited:
            message = "permission denied"
            raise OSError(message)
        return original_read_text(
            path,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    monkeypatch.setattr(Path, "read_text", read_text_with_failure)

    assert handoff_check.main(["handoff.md"], repo) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "handoff-check: permission denied\n"


def test_render_preserves_exact_citation_text() -> None:
    finding = handoff_check.Finding(
        handoff_check.Verdict.BAD_LINE_RANGE,
        "python/src/foo.py:42-58",
        "range is stale",
    )
    output = handoff_check.render([finding], source="handoff.md")
    assert "`python/src/foo.py:42-58`" in output
    assert "bad_line_range" in output
