# Copyright (c) 2026 Raymond Manaloto
"""Tests for the scoped session handoff citation checker."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import handoff_check, pr_facts
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
    "carrier",
    [
        "## Next task\nDo the thing\n",
        "## NEXT TASK — do X\n",
        "## 🚀: Next-task: do X\n",
        "NEXT: do the thing\n",
        "Next task: do the thing\n",
    ],
)
def test_task_carrier_is_forbidden_in_a_handoff(tmp_path: Path, carrier: str) -> None:
    repo = _repo(tmp_path)

    findings = handoff_check.check(repo, carrier)

    assert [item.verdict for item in findings] == [
        handoff_check.Verdict.FORBIDDEN_TASK_CARRIER
    ]


@pytest.mark.parametrize(
    "text",
    [
        "The next task is X, according to the historical report.\n",
        "## Where the next task lives\n",
        "## What the audit says beyond the next task\n",
        "next-task without a colon is prose\n",
        "```text\nNEXT: this is example data\n```\n",
    ],
)
def test_prose_and_fenced_examples_are_not_task_carriers(
    tmp_path: Path, text: str
) -> None:
    repo = _repo(tmp_path)
    assert handoff_check.check(repo, text) == []


def test_unclosed_fence_is_reported_instead_of_hiding_the_remainder(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)

    findings = handoff_check.check(repo, "```text\nNEXT: hidden by broken markdown\n")

    assert [item.verdict for item in findings] == [handoff_check.Verdict.UNCLOSED_FENCE]


def test_plan_without_next_session_heading_is_missing_active_plan(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    (repo / "task_plan.md").write_text("# Plan\n\n## Phase 1\n")

    findings = handoff_check.check(repo, "State only.\n")

    assert [item.verdict for item in findings] == [
        handoff_check.Verdict.MISSING_ACTIVE_PLAN
    ]


def _attested(repo: Path, extra: str = "") -> handoff_check.Attestation:
    """Write an attestation the way `plan-attest` does; return its --show view."""
    digest = hashlib.sha256((repo / "task_plan.md").read_bytes()).hexdigest()
    (repo / ".plan-attestation").write_text(digest + "\n" + extra)
    return handoff_check.Attestation("./task_plan.md", "./.plan-attestation")


def _plan(repo: Path, phase: int = 7) -> None:
    (repo / "task_plan.md").write_text(f"# Plan\n\n## Phase {phase} — NEXT SESSION\n")


def test_attested_plan_has_no_plan_finding(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _plan(repo)
    state = _attested(repo)

    assert handoff_check.check(repo, "State only.\n", show=lambda _: state) == []


def test_plan_edited_after_attestation_is_unattested(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _plan(repo)
    state = _attested(repo)
    _plan(repo, phase=8)

    findings = handoff_check.check(repo, "State only.\n", show=lambda _: state)

    assert [item.verdict for item in findings] == [
        handoff_check.Verdict.UNATTESTED_PLAN
    ]
    assert "does not match its attestation" in findings[0].detail


@pytest.mark.parametrize("extra", ["extra\n", "\x1c"])
def test_trailing_content_after_the_digest_is_unattested(
    tmp_path: Path, extra: str
) -> None:
    """The hook strips only C-locale whitespace and NUL, then compares the whole file.

    U+001C is whitespace to Python's ``str.split`` but not to ``tr [:space:]``,
    so a checker using ``split`` would pass what the hook rejects.
    """
    repo = _repo(tmp_path)
    _plan(repo)
    state = _attested(repo, extra=extra)

    findings = handoff_check.check(repo, "State only.\n", show=lambda _: state)

    assert [item.verdict for item in findings] == [
        handoff_check.Verdict.UNATTESTED_PLAN
    ]


def test_native_whitespace_around_the_digest_is_accepted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _plan(repo)
    state = _attested(repo, extra=" \t\r\x0b\x0c\x00\n")

    assert handoff_check.check(repo, "State only.\n", show=lambda _: state) == []


def test_slug_selection_is_rejected_even_when_the_slug_is_attested(
    tmp_path: Path,
) -> None:
    """The root plan is the task authority; a slug the plugin resolves is a finding."""
    repo = _repo(tmp_path)
    _plan(repo)
    slug = repo / ".planning" / "ticket"
    slug.mkdir(parents=True)
    (slug / "task_plan.md").write_text("# Ticket plan\n")
    (slug / ".attestation").write_text(
        hashlib.sha256((slug / "task_plan.md").read_bytes()).hexdigest() + "\n"
    )
    state = handoff_check.Attestation(
        "./.planning/ticket/task_plan.md", "./.planning/ticket/.attestation"
    )

    findings = handoff_check.check(repo, "State only.\n", show=lambda _: state)

    assert [item.verdict for item in findings] == [
        handoff_check.Verdict.UNATTESTED_PLAN
    ]
    assert "not the root task_plan.md" in findings[0].detail


@pytest.mark.parametrize(
    ("state", "fragment"),
    [
        (handoff_check.Attestation(None, None), "has no attestation"),
        (
            handoff_check.Attestation(None, None, "plugin absent"),
            "cannot read the planning-with-files attestation: plugin absent",
        ),
    ],
)
def test_missing_or_unreadable_attestation_is_unattested(
    tmp_path: Path, state: handoff_check.Attestation, fragment: str
) -> None:
    repo = _repo(tmp_path)
    _plan(repo)

    findings = handoff_check.check(repo, "State only.\n", show=lambda _: state)

    assert [item.verdict for item in findings] == [
        handoff_check.Verdict.UNATTESTED_PLAN
    ]
    assert fragment in findings[0].detail


def test_parse_show_reads_the_plugin_output() -> None:
    shown = (
        f"Plan: ./task_plan.md\nAttestation: ./.plan-attestation\nSHA-256: {'a' * 64}\n"
    )
    assert handoff_check.parse_show(shown) == handoff_check.Attestation(
        "./task_plan.md", "./.plan-attestation"
    )
    missing = "[plan-attest] No attestation set for ./task_plan.md.\n"
    assert handoff_check.parse_show(missing) == handoff_check.Attestation(None, None)


def test_fresh_clone_without_plan_has_no_active_plan_finding(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert handoff_check.check(repo, "State only.\n") == []


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


@pytest.mark.parametrize(
    "text",
    [
        "ghcr.io/devcontainers/features/sshd:1",
        "# syntax=docker/dockerfile:1.7",
        "/etc/hosts:1",
    ],
)
def test_check_ignores_slash_containing_non_allowlisted_citations(
    tmp_path: Path, text: str
) -> None:
    """The subdirectory rule is scoped to Makefile/Dockerfile, not any bareword.

    Regression pin: a broader "any extensionless word with a slash" rule
    admitted OCI image references and the Docker syntax directive as false
    citations (found by cold review after the ticket's own broader wording).
    """
    repo = _repo(tmp_path)

    assert handoff_check.check(repo, text) == []


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


def test_main_reports_handoff_file_read_failure_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The other #834 arm: the handoff file itself, not a cited file, fails."""
    repo = _repo(tmp_path)
    handoff = repo / "handoff.md"
    handoff.write_text("No citations here.\n")
    original_read_text = Path.read_text

    def read_text_with_failure(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        if path == handoff:
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


def test_render_ok_line_keeps_its_prefix_and_counts_claims() -> None:
    assert handoff_check.render([], source="h.md", claims_checked=3) == (
        "handoff-check: OK — h.md citations resolve; 3 PR claim(s) match GitHub"
    )
    assert handoff_check.render([], source="h.md").endswith(
        "; 0 PR claim(s) match GitHub"
    )


# --- PR/issue state claims (S29-H) -------------------------------------------


def _pr(
    number: int,
    state: str = "OPEN",
    *,
    auto_merge: bool = False,
    checks: tuple[int, int, int] = (0, 0, 0),
) -> pr_facts.PrFacts:
    """``checks`` is (passed, failing, pending)."""
    return pr_facts.PrFacts(
        number,
        pr_facts.ItemKind.PR,
        state,
        auto_merge=auto_merge,
        checks=pr_facts.CheckCounts(*checks),
    )


def _issue(number: int, state: str) -> pr_facts.PrFacts:
    return pr_facts.PrFacts(
        number,
        pr_facts.ItemKind.ISSUE,
        state,
        auto_merge=False,
        checks=pr_facts.CheckCounts(0, 0, 0),
    )


def _words(text: str) -> list[tuple[int, str]]:
    return [
        (claim.number, claim.word.value)
        for claim in handoff_check.extract_claims(text, source="h")
    ]


def test_extract_claims_reads_every_word_in_its_window() -> None:
    assert _words("- #1454 MERGED + landed; #1449 OPEN, auto-merge armed, RED") == [
        (1454, "MERGED"),
        (1454, "landed"),
        (1449, "auto-merge armed"),
        (1449, "OPEN"),
        (1449, "RED"),
    ]


def test_extract_claims_masks_armed_before_the_bare_word() -> None:
    assert _words("#1 armed auto-merge") == [(1, "auto-merge armed")]
    assert _words("#1 auto-merge armed, auto-merge") == [
        (1, "auto-merge armed"),
        (1, "auto-merge"),
    ]
    assert _words("#1 → auto-merge") == [(1, "auto-merge")]


@pytest.mark.parametrize(
    "text",
    [
        "#1 auto-merges when ready",
        "#1 was auto-merged",
        "#1 Open Merged Closed Red",
        "KB#814 MERGED",
        "ray-manaloto/knowledge-base#12 MERGED",
        "`mise run land -- <PR#>` MERGED",
        "##12 MERGED",
        "`#1449 OPEN`",
        "~~#1449 OPEN~~",
        "#1449 ~~OPEN~~ `RED`",
        "```\n#1449 OPEN\n```",
        "no reference MERGED",
    ],
)
def test_extract_claims_ignores_non_claims(text: str) -> None:
    assert _words(text) == []


def test_extract_claims_is_case_rules_and_dedupes() -> None:
    assert _words("#7 GREEN and Landed, green again, MERGED MERGED") == [
        (7, "MERGED"),
        (7, "landed"),
        (7, "green"),
    ]


def test_extract_claims_window_ends_at_the_next_reference() -> None:
    assert _words("#1435 + #963 CLOSED") == [(963, "CLOSED")]


def test_extract_claims_reports_source_file_lines() -> None:
    claims = handoff_check.extract_claims(
        "one\n```\n#1 OPEN\n```\n#2 MERGED\n", source="task_plan.md", line_offset=100
    )
    assert claims == [
        handoff_check.Claim(2, handoff_check.ClaimWord.MERGED, "task_plan.md", 105)
    ]


def test_active_section_spans_the_last_next_session_heading() -> None:
    plan = (
        "# Plan\n## Old NEXT SESSION\n#1 OPEN\n## Done\n"
        "## Phase 9 — NEXT SESSION\nbody\n### sub\nmore\n## Later\ntail\n"
    )
    assert handoff_check.active_section(plan) == (
        "## Phase 9 — NEXT SESSION\nbody\n### sub\nmore\n"
    )
    assert handoff_check.active_section("## A NEXT SESSION\nto eof") == (
        "## A NEXT SESSION\nto eof"
    )
    assert handoff_check.active_section("## Nothing\n") is None


@pytest.mark.parametrize(
    ("word", "facts", "holds"),
    [
        ("OPEN", _pr(1, "OPEN"), True),
        ("OPEN", _pr(1, "MERGED"), False),
        ("MERGED", _pr(1, "MERGED"), True),
        ("CLOSED", _pr(1, "MERGED"), False),
        ("CLOSED", _pr(1, "CLOSED"), True),
        ("landed", _pr(1, "MERGED"), True),
        ("landed", _pr(1, "OPEN", auto_merge=True), False),
        ("auto-merge armed", _pr(1, "OPEN", auto_merge=True), True),
        ("auto-merge armed", _pr(1, "OPEN", auto_merge=True, checks=(0, 2, 0)), True),
        ("auto-merge armed", _pr(1, "MERGED", auto_merge=True), False),
        ("auto-merge armed", _pr(1, "OPEN"), False),
        ("auto-merge", _pr(1, "OPEN", auto_merge=True, checks=(0, 0, 3)), True),
        ("auto-merge", _pr(1, "OPEN", auto_merge=True, checks=(0, 2, 0)), False),
        ("auto-merge", _pr(1, "MERGED", auto_merge=True), False),
        ("RED", _pr(1, checks=(0, 1, 0)), True),
        ("RED", _pr(1, checks=(5, 0, 0)), False),
        ("green", _pr(1, checks=(5, 0, 0)), True),
        ("green", _pr(1, checks=(5, 0, 1)), False),
        ("green", _pr(1, checks=(5, 1, 0)), False),
        ("green", _pr(1), False),
        ("OPEN", _issue(1, "OPEN"), True),
        ("CLOSED", _issue(1, "OPEN"), False),
        ("MERGED", _issue(1, "CLOSED"), None),
        ("auto-merge", _issue(1, "OPEN"), None),
        ("green", _issue(1, "OPEN"), None),
    ],
)
def test_claim_holds_semantics(
    word: str, facts: pr_facts.PrFacts, holds: object
) -> None:
    assert handoff_check.claim_holds(handoff_check.ClaimWord(word), facts) is holds


def _attested_plan(repo: Path, text: str) -> handoff_check.Attestation:
    (repo / "task_plan.md").write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    (repo / ".plan-attestation").write_text(digest + "\n")
    return handoff_check.Attestation("task_plan.md", ".plan-attestation")


def test_claims_in_handoff_and_active_plan_are_judged_once_per_number(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    state = _attested_plan(
        repo,
        "## Old\n#1454 OPEN\n## NEXT SESSION\nWATCH: #1449 CI → auto-merge\n"
        "#963 CLOSED, #1454 landed\n",
    )
    live = {
        1449: _pr(1449, "OPEN", auto_merge=True, checks=(12, 2, 0)),
        1454: _pr(1454, "MERGED", auto_merge=True, checks=(13, 0, 0)),
        963: _issue(963, "CLOSED"),
    }
    fetched: list[int] = []

    def facts(_root: Path, number: int) -> pr_facts.PrFacts | str:
        fetched.append(number)
        return live[number]

    findings, checked = handoff_check.check_with_claims(
        repo,
        "- #1454 auto-merge armed\n- #1449 OPEN, RED\n",
        show=lambda _: state,
        facts=facts,
        source=".agent/plans/session-x.md",
    )

    assert findings == [
        handoff_check.Finding(
            handoff_check.Verdict.PR_CLAIM_MISMATCH,
            "#1454 auto-merge armed (.agent/plans/session-x.md:1)",
            "GitHub reports PR #1454 state=MERGED auto-merge=yes checks "
            "fail:0 pending:0 pass:13",
        ),
        handoff_check.Finding(
            handoff_check.Verdict.PR_CLAIM_MISMATCH,
            "#1449 auto-merge (task_plan.md:4)",
            "GitHub reports PR #1449 state=OPEN auto-merge=yes checks "
            "fail:2 pending:0 pass:12",
        ),
    ]
    assert checked == 6
    assert sorted(fetched) == [963, 1449, 1454]


def test_failed_lookup_is_one_unverifiable_finding_per_number(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    findings, checked = handoff_check.check_with_claims(
        repo,
        "#5 OPEN, green\n#5 RED\n#6 MERGED\n",
        facts=lambda _root, number: (
            "gh api exited 1: boom" if number == 5 else _pr(6, "MERGED")
        ),
    )

    assert findings == [
        handoff_check.Finding(
            handoff_check.Verdict.PR_CLAIM_UNVERIFIABLE,
            "#5",
            "GitHub lookup failed (gh api exited 1: boom) — 3 claim(s) unchecked; "
            "a failed lookup is never a pass",
        )
    ]
    assert checked == 1


def test_claim_deadline_expiry_is_unverifiable_without_a_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    monkeypatch.setattr(handoff_check, "CLAIMS_DEADLINE_S", 0.0)

    def never(_root: Path, number: int) -> pr_facts.PrFacts | str:
        message = f"fetched #{number} after the deadline"
        raise AssertionError(message)

    findings = handoff_check.check(repo, "#5 OPEN\n#5 RED\n#6 MERGED\n", facts=never)

    assert findings == [
        handoff_check.Finding(
            handoff_check.Verdict.PR_CLAIM_UNVERIFIABLE,
            f"#{number}",
            "claim-check deadline (0 s) expired before lookup",
        )
        for number in (5, 6)
    ]


def test_default_facts_resolve_through_the_patched_run_gh(tmp_path: Path) -> None:
    """facts=None must reach pr_facts.run_gh at call time (the pinned seam)."""
    repo = _repo(tmp_path)
    monkeypatch = pytest.MonkeyPatch()
    calls: list[list[str]] = []

    def fake(args: list[str], _root: Path) -> tuple[int, str]:
        calls.append(args)
        return 1, "HTTP 401: Bad credentials"

    monkeypatch.setattr(pr_facts, "run_gh", fake)
    try:
        findings = handoff_check.check(repo, "#9 MERGED\n")
    finally:
        monkeypatch.undo()

    assert calls == [["api", "repos/{owner}/{repo}/issues/9"]]
    assert [finding.verdict for finding in findings] == [
        handoff_check.Verdict.PR_CLAIM_UNVERIFIABLE
    ]


def test_main_counts_matching_claims_and_fails_on_a_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)
    (repo / "good.md").write_text("- #3 MERGED, landed\n")
    (repo / "stale.md").write_text("- #3 auto-merge armed\n")

    def fake(args: list[str], _root: Path) -> tuple[int, str]:
        if args[0] == "api":
            return 0, '{"state": "closed", "pull_request": {}}'
        return 0, (
            '{"state": "MERGED", "autoMergeRequest": {}, '
            '"statusCheckRollup": [{"conclusion": "SUCCESS"}]}'
        )

    monkeypatch.setattr(pr_facts, "run_gh", fake)

    assert handoff_check.main(["good.md"], repo) == 0
    assert capsys.readouterr().out == (
        "handoff-check: OK — good.md citations resolve; 2 PR claim(s) match GitHub\n"
        "handoff-check: info — task_plan.md absent (fresh clone); "
        "active-plan checks skipped\n"
    )

    assert handoff_check.main(["stale.md"], repo) == 1
    out = capsys.readouterr().out
    assert "- pr_claim_mismatch: `#3 auto-merge armed (stale.md:1)` — " in out
    assert "state=MERGED auto-merge=yes checks fail:0 pending:0 pass:1" in out
