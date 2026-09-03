# Copyright (c) 2026 Raymond Manaloto
"""Tests for the InstructionsLoaded report side (#917).

Covers `scoped_rules_on_disk` (frontmatter parsing, incl. recursion through
real AND symlinked subdirs, and EOF-terminated frontmatter), `build_report`
(the eager/fired/loaded_other_reason/never_fired partition, its two-bucket
invariant, and S1's reason-blind "observed at all" membership test), the C6
control-armed never-fired fixture, the never_fired-only sufficiency gate
(S2), and the CLI end-to-end including `--project-root` (R6). The paired
observer<->report path-spelling invariant (S4) lives in its own file,
`test_instructions_paths_consistency.py`.
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


def test_scoped_rules_on_disk_recurses_into_symlinked_subdirs(tmp_path: Path) -> None:
    """S3: `Path.rglob` defaults `recurse_symlinks=False` on Python 3.13+.

    A rules subdirectory that is PHYSICALLY a symlink — the documented
    sharing pattern the observer's R7 fix (`_normalize_path`) names as its
    whole reason for staying lexical rather than calling `.resolve()` — was
    silently invisible to this function even though R8 already made it
    recurse real subdirectories. Without `recurse_symlinks=True` a
    symlinked rule appears in NO report bucket at all.
    """
    real_target = tmp_path / "elsewhere"
    real_target.mkdir()
    _write_rule(real_target, "shared-rule", paths=["mise.toml"])
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "shared").symlink_to(real_target, target_is_directory=True)
    result = report.scoped_rules_on_disk(rules_dir)
    assert ".claude/rules/shared/shared-rule.md" in result


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
# build_report — the partition, R1/S1's two-bucket invariant, S2's gate.
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


def test_build_report_s1_null_load_reason_removes_from_never_fired() -> None:
    """S1: `load_reason: null` must STILL remove a rule from never_fired.

    This is the observer's own shape whenever the harness omits the key —
    `_string_or_none` writes `None`, and `tests/test_instructions_observer.py`
    already asserts that record shape (`test_build_record_missing_fields_are_none`).
    The old gate was `isinstance(reason, str) and file_path in scoped_set`,
    so `never_fired` was really "scoped minus everything observed with a
    STRING reason" — not "by ANY reason" as documented. Reproduces the exact
    repro from round 2: a record for a scoped rule EXISTS, and the rule was
    still reported never-fired.
    """
    records = [
        {"file_path": "CLAUDE.md", "load_reason": "session_start"},
        {"file_path": ".claude/rules/foo.md", "load_reason": None},
    ]
    result = report.build_report(records, scoped=(".claude/rules/foo.md",))
    assert result.never_fired == ()
    assert ".claude/rules/foo.md" in result.loaded_other_reason


def test_build_report_r1_two_bucket_invariant_fuzz() -> None:
    """R1/S1's invariant, checked directly and generically across reasons.

    A scoped rule must never appear in more than one of fired /
    loaded_other_reason / never_fired, across a battery of reasons —
    including S1's non-string/missing shapes (`None`, a wrong-typed int),
    which the reason-blind membership test must still remove from
    never_fired.
    """
    scoped = tuple(f".claude/rules/rule-{i}.md" for i in range(7))
    reasons: list[object] = [
        "session_start",
        "path_glob_match",
        "include",
        "compact",
        "nested_traversal",
        None,
        123,
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
    """S2 respec: counts DISTINCT `session_id` values, not `session_start` events.

    30 session_start records sharing ONE session_id must read as exactly 1
    session — every eager instruction file emits its own session_start
    record per session, so event-counting let a single session satisfy the
    threshold on its own (the false positive #917 exists to prevent).
    """
    records = [
        {"file_path": f"r{i}", "load_reason": "session_start", "session_id": "s1"}
        for i in range(30)
    ]
    result = report.build_report(records, scoped=())
    assert result.sessions_observed == 1
    assert result.never_fired_sufficient is False


def test_build_report_sessions_observed_distinct_ids_reach_threshold() -> None:
    """Three distinct session_id values ARE three sessions.

    A genuinely dead scoped rule is named in `never_fired` once they do.
    """
    records = [
        {"file_path": "a", "load_reason": "session_start", "session_id": "s1"},
        {"file_path": "b", "load_reason": "session_start", "session_id": "s2"},
        {"file_path": "c", "load_reason": "session_start", "session_id": "s3"},
    ]
    result = report.build_report(records, scoped=(".claude/rules/dead.md",))
    assert result.sessions_observed == 3
    assert result.never_fired_sufficient is True
    assert result.never_fired == (".claude/rules/dead.md",)


def test_build_report_sessions_observed_ignores_null_session_id() -> None:
    """S2's probed regression: `session_id: null` must not freeze coverage at 0.

    Records with no usable `session_id` (missing, null, non-string) are
    indistinguishable from one another and so contribute AT MOST ONE
    pseudo-session in total — never zero, so this corpus of 5 such records
    reads as exactly 1 session, not 5 and not 0.
    """
    records = [
        {
            "file_path": f"rule-{i}.md",
            "load_reason": "session_start",
            "session_id": None,
        }
        for i in range(5)
    ]
    result = report.build_report(records, scoped=())
    assert result.sessions_observed == 1
    assert result.never_fired_sufficient is False


def test_build_report_sessions_observed_unidentified_plus_distinct_ids() -> None:
    """Unidentified session_start records add AT MOST ONE session.

    This is on top of any distinct real `session_id` values also observed.
    """
    records = [
        {"file_path": "a", "load_reason": "session_start", "session_id": "s1"},
        {"file_path": "b", "load_reason": "session_start", "session_id": "s2"},
        {"file_path": "c", "load_reason": "session_start", "session_id": None},
        {"file_path": "d", "load_reason": "session_start"},  # missing session_id
    ]
    result = report.build_report(records, scoped=())
    assert result.sessions_observed == 3


def test_build_report_sessions_observed_whitespace_ids_are_one_pseudo_session() -> None:
    r"""U1: whitespace-only session_ids must not be counted as distinct sessions.

    `""`, `" "`, `"\t"` all reduce to nothing under
    `instructions_observer.usable_session_id` — the same predicate
    `session_filename` uses to collapse them into ONE `unknown.jsonl` file
    — so the report must also count them as one pseudo-session, not three.
    """
    records = [
        {"file_path": f"r{i}", "load_reason": "session_start", "session_id": sid}
        for i, sid in enumerate(("", " ", "\t"))
    ]
    result = report.build_report(records, scoped=(".claude/rules/dead.md",))
    assert result.sessions_observed == 1
    assert result.never_fired_sufficient is False
    # `never_fired` is still computed on the dataclass (S2) — only the
    # JSON/render layer withholds it when insufficient (`_json_payload`).
    assert result.never_fired == (".claude/rules/dead.md",)


def test_build_report_sessions_observed_one_real_plus_unusable_ids() -> None:
    """U1: one real id plus assorted unusable ones is one real + one pseudo."""
    records = [
        {"file_path": "a", "load_reason": "session_start", "session_id": "s1"},
        {"file_path": "b", "load_reason": "session_start", "session_id": ""},
        {"file_path": "c", "load_reason": "session_start", "session_id": None},
    ]
    result = report.build_report(records, scoped=())
    assert result.sessions_observed == 2
    assert result.never_fired_sufficient is False


def test_build_report_sessions_observed_three_real_ids_fires_gate() -> None:
    """Three genuinely distinct real ids still reach the threshold.

    And a dead scoped rule is named — the gate must still be reachable,
    not just safe.
    """
    records = [
        {"file_path": "a", "load_reason": "session_start", "session_id": "sess-1"},
        {"file_path": "b", "load_reason": "session_start", "session_id": "sess-2"},
        {"file_path": "c", "load_reason": "session_start", "session_id": "sess-3"},
    ]
    result = report.build_report(records, scoped=(".claude/rules/dead.md",))
    assert result.sessions_observed == 3
    assert result.never_fired_sufficient is True
    assert result.never_fired == (".claude/rules/dead.md",)


def test_build_report_zero_session_start_records_is_insufficient() -> None:
    records = [
        {"file_path": "a", "load_reason": "path_glob_match", "session_id": "s1"},
    ]
    result = report.build_report(records, scoped=())
    assert result.sessions_observed == 0
    assert result.never_fired_sufficient is False
    assert result.never_fired_min_sessions == 3


def test_build_report_never_fired_sufficient_boundary() -> None:
    """The threshold is inclusive: N-1 distinct sessions insufficient, N sufficient."""
    threshold = report.build_report([], scoped=()).never_fired_min_sessions
    below = [
        {
            "file_path": f"r{i}",
            "load_reason": "session_start",
            "session_id": f"s{i}",
        }
        for i in range(threshold - 1)
    ]
    at = [
        {
            "file_path": f"r{i}",
            "load_reason": "session_start",
            "session_id": f"s{i}",
        }
        for i in range(threshold)
    ]
    assert report.build_report(below, scoped=()).never_fired_sufficient is False
    assert report.build_report(at, scoped=()).never_fired_sufficient is True


def test_build_report_never_fired_still_computed_when_insufficient() -> None:
    """The raw partition is always mathematically correct (S2).

    Only the RENDERING layer withholds it. `build_report` itself never
    hides data — a scoped rule with zero observed loads is genuinely in
    `never_fired` regardless of how much coverage exists; whether to TRUST
    that claim is `never_fired_sufficient`'s job, checked by the caller.
    """
    result = report.build_report([], scoped=(".claude/rules/some-rule.md",))
    assert result.never_fired == (".claude/rules/some-rule.md",)
    assert result.never_fired_sufficient is False


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
    """Fixture with `never_fired_min_sessions` DISTINCT sessions.

    AT the S2 threshold, so `never_fired` is trusted enough to print in the
    tests that exercise it below.
    """
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
    threshold = report.build_report([], scoped=()).never_fired_min_sessions
    for i in range(threshold):
        session_id = f"session-{i}"
        _write_record(
            records_dir,
            session_id,
            {
                "session_id": session_id,
                "file_path": "CLAUDE.md",
                "load_reason": "session_start",
            },
        )
    return tmp_path


def test_run_report_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project_root = _build_fixture(tmp_path)
    rc = report.run_report(project_root, json_output=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["never_fired_sufficient"] is True
    assert payload["eager"] == ["CLAUDE.md"]
    assert payload["fired"] == [".claude/rules/fired-rule.md"]
    assert payload["never_fired"] == [".claude/rules/dead-glob-rule.md"]
    assert payload["sessions_observed"] == payload["never_fired_min_sessions"]


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


def test_run_report_no_records_yet_never_fired_hidden_but_others_shown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """S2: zero session_start events -> `never_fired` withheld, not the whole report.

    Zero records means zero session_start events, so `never_fired` is
    withheld (`null`, S5), but `eager`/`fired`/`loaded_other_reason` are
    ALWAYS printed as their real (here, truthfully empty) values, never
    omitted.

    Previously (R2) the WHOLE report was suppressed on this input, which
    over-corrected: it hid three POSITIVE fields that were correct from the
    first record onward, on the strength of the one field — `never_fired`,
    an ABSENCE claim — that genuinely needed more coverage.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "some-rule", paths=["hk.pkl"])
    rc = report.run_report(tmp_path, json_output=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["never_fired_sufficient"] is False
    assert payload["sessions_observed"] == 0
    assert payload["eager"] == []
    assert payload["fired"] == []
    assert payload["loaded_other_reason"] == []
    assert payload["never_fired"] is None


def test_run_report_positive_buckets_shown_when_never_fired_insufficient(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """S2's core acceptance case.

    Real records exist with zero session_start (e.g. the hook wired
    mid-session — the exact live-repo shape both respec rounds measured) —
    the POSITIVE buckets must still print; only `never_fired` is withheld.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "mid-session-rule", paths=["hk.pkl"])
    records_dir = tmp_path / ".agent" / "instructions-loaded"
    _write_record(
        records_dir,
        "s1",
        {
            "session_id": "s1",
            "file_path": ".claude/rules/mid-session-rule.md",
            "load_reason": "include",
        },
    )
    rc = report.run_report(tmp_path, json_output=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sessions_observed"] == 0
    assert payload["never_fired_sufficient"] is False
    assert payload["never_fired"] is None
    assert payload["loaded_other_reason"] == [".claude/rules/mid-session-rule.md"]


def test_run_report_no_records_human_readable_names_no_rules_but_not_insufficient(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "some-rule", paths=["hk.pkl"])
    rc = report.run_report(tmp_path, json_output=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "NOT SHOWN" in out
    assert "some-rule.md" not in out
    assert "eager (session_start): 0" in out


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
