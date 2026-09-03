# Copyright (c) 2026 Raymond Manaloto
"""Tests for the InstructionsLoaded report side (#917).

Covers `scoped_rules_on_disk` (frontmatter parsing), `build_report`
(eager/fired/never-fired partitioning), and the C6 control-armed
never-fired fixture: a scoped rule with a PLAUSIBLE glob that never
matched must appear in `never_fired`, and a scoped rule that DID fire
must not — built as a fixture no real `.claude/rules/` tree is mutated to
produce (`probes-need-a-control-arm.md` rule 8: the dead glob must be one
that COULD have fired, not a configuration nothing could ever trigger).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import instructions_report as report

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).parent.parent


def _write_rule(rules_dir: Path, name: str, *, paths: list[str] | None) -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)
    if paths is None:
        body = f"# {name}\n\nno frontmatter.\n"
    else:
        globs = "\n".join(f'  - "{g}"' for g in paths)
        body = f"---\npaths:\n{globs}\n---\n\n# {name}\n\nscoped rule body.\n"
    (rules_dir / f"{name}.md").write_text(body, encoding="utf-8")


def _write_record(records_dir: Path, session: str, record: dict) -> None:
    records_dir.mkdir(parents=True, exist_ok=True)
    path = records_dir / f"{session}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


# --------------------------------------------------------------------------
# scoped_rules_on_disk
# --------------------------------------------------------------------------


def test_scoped_rules_on_disk_finds_paths_frontmatter(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "scoped-a", paths=["hk.pkl", "**/CLAUDE.md"])
    _write_rule(rules_dir, "unscoped-b", paths=None)
    result = report.scoped_rules_on_disk(rules_dir)
    assert result == (".claude/rules/scoped-a.md",)


def test_scoped_rules_on_disk_ignores_frontmatter_without_paths_key(
    tmp_path: Path,
) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "other-frontmatter.md").write_text(
        "---\ntitle: something\n---\n\nbody\n", encoding="utf-8"
    )
    assert report.scoped_rules_on_disk(rules_dir) == ()


def test_scoped_rules_on_disk_empty_dir(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    assert report.scoped_rules_on_disk(rules_dir) == ()


def test_scoped_rules_on_disk_against_the_real_repo() -> None:
    """Real-repo sanity: exactly the two scoped rules on disk today (premise)."""
    result = report.scoped_rules_on_disk(REPO_ROOT / ".claude" / "rules")
    assert ".claude/rules/ci-local-parity.md" in result
    assert ".claude/rules/md-size-budgets.md" in result


# --------------------------------------------------------------------------
# build_report / C6 — the never-fired control arm.
# --------------------------------------------------------------------------


def test_build_report_eager_from_session_start() -> None:
    records = [{"file_path": "CLAUDE.md", "load_reason": "session_start"}]
    result = report.build_report(records, scoped=())
    assert result.eager == ("CLAUDE.md",)
    assert result.fired == ()
    assert result.by_reason == {"session_start": 1}


def test_build_report_c6_fired_vs_never_fired_control_arm() -> None:
    """The control-armed fixture C6.

    Requires: a scoped rule that DID fire (via a real path_glob_match
    record) must be excluded from never_fired; a scoped rule with a
    PLAUSIBLE but dead glob that never matched must appear in it. Both
    rules are equally "real" — only the observed records differ, so this
    proves the partition discriminates rather than defaulting one way.
    """
    scoped = (
        ".claude/rules/fired-rule.md",
        ".claude/rules/dead-glob-rule.md",
    )
    records = [
        {
            "file_path": ".claude/rules/fired-rule.md",
            "load_reason": "path_glob_match",
            "globs": ["mise.toml"],
        },
        # A session_start record for an UNSCOPED file — must not leak into
        # fired/never_fired accounting for the scoped set.
        {"file_path": "CLAUDE.md", "load_reason": "session_start"},
    ]
    result = report.build_report(records, scoped=scoped)
    assert result.fired == (".claude/rules/fired-rule.md",)
    assert result.never_fired == (".claude/rules/dead-glob-rule.md",)
    assert ".claude/rules/fired-rule.md" not in result.never_fired


def test_build_report_path_glob_match_outside_scoped_set_is_not_fired() -> None:
    """A path_glob_match record for a file not in the scoped set.

    (e.g. a CLAUDE.md loaded via nested_traversal, mislabeled) must not
    count as a scoped rule firing.
    """
    records = [
        {
            "file_path": "some/other/CLAUDE.md",
            "load_reason": "path_glob_match",
            "globs": ["**/CLAUDE.md"],
        }
    ]
    result = report.build_report(records, scoped=(".claude/rules/real-rule.md",))
    assert result.fired == ()
    assert result.never_fired == (".claude/rules/real-rule.md",)


def test_build_report_by_reason_counts_every_reason() -> None:
    records = [
        {"load_reason": "session_start", "file_path": "a"},
        {"load_reason": "session_start", "file_path": "b"},
        {"load_reason": "compact", "file_path": "a"},
        {"load_reason": "nested_traversal", "file_path": "c"},
    ]
    result = report.build_report(records, scoped=())
    assert result.by_reason == {"compact": 1, "nested_traversal": 1, "session_start": 2}


def test_build_report_malformed_records_are_tolerated() -> None:
    records = [
        {"load_reason": 123, "file_path": "a"},  # wrong type, dropped from by_reason
        {"load_reason": "session_start", "file_path": None},  # non-string path, dropped
        {},
    ]
    result = report.build_report(records, scoped=())
    assert result.eager == ()
    # The 123 int reason never counts; the session_start record DOES count in
    # by_reason even though its file_path is None (reason-counting and
    # path-validity are independent), and never lands in `eager`.
    assert result.by_reason == {"session_start": 1}


# --------------------------------------------------------------------------
# run_report / CLI end-to-end
# --------------------------------------------------------------------------


def _build_fixture(tmp_path: Path) -> Path:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "fired-rule", paths=["mise.toml"])
    _write_rule(rules_dir, "dead-glob-rule", paths=["nonexistent-trigger-file.pkl"])
    records_dir = tmp_path / ".agent" / "instructions-loaded"
    _write_record(
        records_dir,
        "s1",
        {
            "file_path": ".claude/rules/fired-rule.md",
            "load_reason": "path_glob_match",
            "globs": ["mise.toml"],
        },
    )
    _write_record(
        records_dir, "s1", {"file_path": "CLAUDE.md", "load_reason": "session_start"}
    )
    return tmp_path


def test_run_report_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root = _build_fixture(tmp_path)
    rc = report.run_report(project_root, json_output=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eager"] == ["CLAUDE.md"]
    assert payload["fired"] == [".claude/rules/fired-rule.md"]
    assert payload["never_fired"] == [".claude/rules/dead-glob-rule.md"]


def test_run_report_human_readable_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root = _build_fixture(tmp_path)
    rc = report.run_report(project_root, json_output=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "fired-rule.md" in out
    assert "dead-glob-rule.md" in out
    assert "never fired" in out


def test_run_report_no_records_yet_is_not_a_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A report over zero observed sessions is legitimate output, not rc!=0."""
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "some-rule", paths=["hk.pkl"])
    rc = report.run_report(tmp_path, json_output=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["never_fired"] == [".claude/rules/some-rule.md"]
    assert payload["eager"] == []


def test_instructions_report_main_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root = _build_fixture(tmp_path)
    rc = report.instructions_report_main(
        ["--project-root", str(project_root), "--json"]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["fired"] == [".claude/rules/fired-rule.md"]
