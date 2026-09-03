# Copyright (c) 2026 Raymond Manaloto
"""Tests for the InstructionsLoaded report side (#917).

Covers `scoped_rules_on_disk` (frontmatter parsing, incl. recursion and
EOF-terminated frontmatter), `build_report` (the eager/fired/
loaded_other_reason/never_fired partition and its two-bucket invariant), the
C6 control-armed never-fired fixture, the insufficient-data gate (R2), and
the CLI end-to-end including `--project-root` (R6).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import instructions_report as report

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).parent.parent


def _write_rule(
    rules_dir: Path,
    name: str,
    *,
    paths: list[str] | None,
    eof_frontmatter: bool = False,
) -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)
    if paths is None:
        body = f"# {name}\n\nno frontmatter.\n"
    elif eof_frontmatter:
        # R9: frontmatter block with nothing after the closing `---` — no
        # trailing newline, no body.
        globs = "\n".join(f'  - "{g}"' for g in paths)
        body = f"---\npaths:\n{globs}\n---"
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


def test_scoped_rules_on_disk_recurses_into_nested_subdirs(tmp_path: Path) -> None:
    """R8: a documented sharing pattern — nested `.claude/rules/` subdirs."""
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "top-level", paths=["hk.pkl"])
    nested = rules_dir / "shared"
    _write_rule(nested, "nested-rule", paths=["mise.toml"])
    result = report.scoped_rules_on_disk(rules_dir)
    assert ".claude/rules/top-level.md" in result
    assert ".claude/rules/shared/nested-rule.md" in result


def test_scoped_rules_on_disk_handles_eof_terminated_frontmatter(
    tmp_path: Path,
) -> None:
    """R9: frontmatter whose closing `---` is the last bytes of the file."""
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "eof-rule", paths=["hk.pkl"], eof_frontmatter=True)
    result = report.scoped_rules_on_disk(rules_dir)
    assert result == (".claude/rules/eof-rule.md",)


def test_scoped_rules_on_disk_against_the_real_repo() -> None:
    """Real-repo sanity, with an R11 negative arm a stub cannot survive.

    The two scoped rules on disk today are found, AND a third, deliberately
    unscoped rule (this file's own sibling, `do-not.md`, which carries no
    `paths:` frontmatter) is NOT — a stub that returns every `.md` under the
    tree would pass the first two assertions but fail this one.
    """
    result = report.scoped_rules_on_disk(REPO_ROOT / ".claude" / "rules")
    assert ".claude/rules/ci-local-parity.md" in result
    assert ".claude/rules/md-size-budgets.md" in result
    assert ".claude/rules/do-not.md" not in result


# --------------------------------------------------------------------------
# build_report — the partition, R1's two-bucket invariant, R2's gate.
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


def test_build_report_r1_any_reason_counts_as_loaded() -> None:
    """R1: a rule loaded via ANY reason must not be reported never-fired.

    A scoped rule loaded via ANY reason (not just path_glob_match) must NOT
    appear in never_fired, and must appear in loaded_other_reason rather
    than silently vanishing. Reproduces the exact defect measured against
    the live repo: an `include`-loaded scoped rule reported as never-fired
    despite a record proving it loaded.
    """
    scoped = (".claude/rules/tests-agents-md.md",)
    records = [
        {"file_path": ".claude/rules/tests-agents-md.md", "load_reason": "include"},
    ]
    result = report.build_report(records, scoped=scoped)
    assert result.loaded_other_reason == (".claude/rules/tests-agents-md.md",)
    assert result.never_fired == ()
    assert result.fired == ()


def test_build_report_r1_session_start_and_scoped_never_conflict() -> None:
    """R1: a rule loaded at session_start must never ALSO read never-fired.

    A scoped rule loaded at session_start must not appear in BOTH `eager`
    (it does, since eager tracks the raw unscoped baseline) AND
    `never_fired` in the same report — the reproduced live-repo bug.
    """
    scoped = (".claude/rules/some-rule.md",)
    records = [
        {"file_path": ".claude/rules/some-rule.md", "load_reason": "session_start"},
    ]
    result = report.build_report(records, scoped=scoped)
    assert ".claude/rules/some-rule.md" in result.eager
    assert ".claude/rules/some-rule.md" not in result.never_fired
    assert ".claude/rules/some-rule.md" in result.loaded_other_reason


def test_build_report_r1_two_bucket_invariant_fuzz() -> None:
    """R1's invariant, checked directly and generically across reasons.

    A scoped rule must never appear in more than one of fired /
    loaded_other_reason / never_fired, across a battery of reasons.
    """
    scoped = tuple(f".claude/rules/rule-{i}.md" for i in range(5))
    reasons = [
        "session_start",
        "path_glob_match",
        "include",
        "compact",
        "nested_traversal",
    ]
    records = [
        {"file_path": scoped[i], "load_reason": reasons[i]} for i in range(len(scoped))
    ]
    result = report.build_report(records, scoped=scoped)
    buckets = [
        set(result.fired),
        set(result.loaded_other_reason),
        set(result.never_fired),
    ]
    for rule in scoped:
        memberships = sum(1 for bucket in buckets if rule in bucket)
        assert memberships == 1, (rule, buckets)
    # And every rule loaded via SOME reason, so none should be never_fired.
    assert result.never_fired == ()


def test_build_report_sessions_observed_counts_distinct_session_ids() -> None:
    records = [
        {"file_path": "a", "load_reason": "session_start", "session_id": "s1"},
        {"file_path": "b", "load_reason": "session_start", "session_id": "s1"},
        {"file_path": "c", "load_reason": "session_start", "session_id": "s2"},
        {"file_path": "d", "load_reason": "path_glob_match", "session_id": "s3"},
    ]
    result = report.build_report(records, scoped=())
    assert result.sessions_observed == 2
    assert result.insufficient_data is False


def test_build_report_zero_session_start_records_is_insufficient() -> None:
    records = [
        {"file_path": "a", "load_reason": "path_glob_match", "session_id": "s1"},
    ]
    result = report.build_report(records, scoped=())
    assert result.sessions_observed == 0
    assert result.insufficient_data is True


def test_build_report_first_last_ts_from_records() -> None:
    records = [
        {
            "file_path": "a",
            "load_reason": "session_start",
            "ts": "2026-09-03T02:00:00+00:00",
        },
        {
            "file_path": "b",
            "load_reason": "session_start",
            "ts": "2026-09-03T01:00:00+00:00",
        },
    ]
    result = report.build_report(records, scoped=())
    assert result.first_ts == "2026-09-03T01:00:00+00:00"
    assert result.last_ts == "2026-09-03T02:00:00+00:00"


def test_build_report_no_records_has_no_timestamps() -> None:
    result = report.build_report([], scoped=())
    assert result.first_ts is None
    assert result.last_ts is None
    assert result.records_read == 0


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
            "session_id": "s1",
            "file_path": ".claude/rules/fired-rule.md",
            "load_reason": "path_glob_match",
            "globs": ["mise.toml"],
        },
    )
    _write_record(
        records_dir,
        "s1",
        {"session_id": "s1", "file_path": "CLAUDE.md", "load_reason": "session_start"},
    )
    return tmp_path


def test_run_report_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root = _build_fixture(tmp_path)
    rc = report.run_report(project_root, json_output=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["insufficient_data"] is False
    assert payload["eager"] == ["CLAUDE.md"]
    assert payload["fired"] == [".claude/rules/fired-rule.md"]
    assert payload["never_fired"] == [".claude/rules/dead-glob-rule.md"]
    assert payload["sessions_observed"] == 1


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
    assert "sessions observed: 1" in out


def test_run_report_no_records_yet_is_insufficient_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R2: zero sessions observed -> insufficient_data, rule lists OMITTED.

    Previously this asserted `never_fired == [rule]` on zero records, which
    pinned the exact defect R2 reports: the live repo, wired mid-session,
    printed `eager: 0` and named two real scoped rules as never-fired on the
    strength of a report that had not observed a single full session.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "some-rule", paths=["hk.pkl"])
    rc = report.run_report(tmp_path, json_output=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["insufficient_data"] is True
    assert payload["sessions_observed"] == 0
    for key in ("eager", "fired", "loaded_other_reason", "never_fired"):
        assert key not in payload, f"{key} must be omitted, not printed empty"


def test_run_report_no_records_human_readable_names_no_rules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "some-rule", paths=["hk.pkl"])
    rc = report.run_report(tmp_path, json_output=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "insufficient data" in out
    assert "some-rule.md" not in out


def test_run_report_counts_malformed_lines_and_errors_log(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root = _build_fixture(tmp_path)
    records_dir = project_root / ".agent" / "instructions-loaded"
    with (records_dir / "s1.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("not json{{{\n")
    (records_dir / "errors.log").write_text(
        "2026-09-03T00:00:00+00:00 boom\n2026-09-03T00:00:01+00:00 boom2\n",
        encoding="utf-8",
    )
    rc = report.run_report(project_root, json_output=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["records_malformed"] == 1
    assert payload["errors_log_lines"] == 2


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


def test_instructions_report_main_cli_project_root_flag_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R6: `--project-root` must parse on its own, without `--json`."""
    project_root = _build_fixture(tmp_path)
    rc = report.instructions_report_main(["--project-root", str(project_root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "fired-rule.md" in out


def test_dotfiles_setup_cli_wires_project_root_end_to_end(tmp_path: Path) -> None:
    """R6, real subprocess through main.py, not the module directly.

    `dotfiles-setup instructions-report --project-root <dir>` used to exit
    rc=2 `usage:` — the subparser registered `--json` but not
    `--project-root`, though the module defines it. Drives the REAL CLI
    entrypoint, not `instructions_report_main` directly, so a regression in
    the `main.py` wiring (not just the module) is caught.
    """
    project_root = _build_fixture(tmp_path)
    res = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            "python",
            "dotfiles-setup",
            "instructions-report",
            "--project-root",
            str(project_root),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["fired"] == [".claude/rules/fired-rule.md"]
