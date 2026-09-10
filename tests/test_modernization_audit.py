# Copyright (c) 2026 Raymond Manaloto
"""Behavioral compatibility tests for the modernization-audit aggregator."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import modernization_audit

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "modernization_audit"


def _audit_copy(tmp_path: Path, name: str) -> Path:
    """Copy the immutable fixture because aggregation writes side outputs."""
    target = tmp_path / name
    shutil.copytree(FIXTURE_ROOT, target)
    return target


def _row(audit_dir: Path, finding_id: str) -> dict[str, object]:
    """Read one row from the public aggregate side output."""
    payload = cast(
        "dict[str, object]",
        json.loads((audit_dir / "aggregate.json").read_text(encoding="utf-8")),
    )
    rows = cast("list[dict[str, object]]", payload["rows"])
    return next(row for row in rows if row["id"] == finding_id)


def test_fixture_regenerates_the_oracle_bytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The tracked port reproduces the original scratch script's artifacts."""
    audit_dir = _audit_copy(tmp_path, "audit")
    toml_out = tmp_path / "regenerated.toml"

    result = modernization_audit.aggregate(audit_dir, toml_out)

    assert toml_out.read_bytes() == (FIXTURE_ROOT / "expected.toml").read_bytes()
    expected_summary = (FIXTURE_ROOT / "expected-summary.json").read_bytes()
    assert (audit_dir / "summary.json").read_bytes() == expected_summary.removesuffix(
        b"\n"
    )
    assert (audit_dir / "existing-verdicts.json").read_text(encoding="utf-8") == (
        '["alpha--coverage", "alpha--risk", "beta--currency"]'
    )
    assert result.units == 2
    assert result.findings == 3
    assert result.by_disposition == {"refactor": 1, "keep": 1, "retire": 1}
    assert result.survived == {"refactor": 1}
    assert result.refuted == 1
    assert result.verdict_files == 3
    assert result.corrections_applied == 1
    assert result.malformed_verdict_files[0]["file"] == "beta--risk.json"
    assert "WARNING: malformed verdict file dropped: beta--risk.json" in (
        capsys.readouterr().err
    )


def test_mutated_second_refutation_flips_survival(tmp_path: Path) -> None:
    """Two refuted votes must kill a finding that survives with only one."""
    audit_dir = _audit_copy(tmp_path, "mutated")
    risk_path = audit_dir / "verdicts" / "alpha--risk.json"
    risk = cast("dict[str, object]", json.loads(risk_path.read_text(encoding="utf-8")))
    verdicts = cast("list[dict[str, object]]", risk["verdicts"])
    verdicts[0]["refuted"] = True
    risk_path.write_text(json.dumps(risk), encoding="utf-8")

    modernization_audit.aggregate(audit_dir, tmp_path / "mutated.toml")

    row = _row(audit_dir, "alpha-1")
    assert row["refuted_votes"] == 2
    assert row["survived"] is False


def test_cli_resolves_relative_paths_and_prints_the_original_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI boundary keeps old defaults but accepts explicit isolated paths."""
    _audit_copy(tmp_path, "audit")

    rc = modernization_audit.modernization_audit_main(
        tmp_path, audit_dir="audit", toml_out="result.toml"
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == 0
    assert payload["units"] == 2
    assert payload["findings"] == 3
    assert payload["survived"] == {"refactor": 1}
    assert payload["malformed_verdict_files"][0]["file"] == "beta--risk.json"
    assert (tmp_path / "result.toml").read_bytes() == (
        FIXTURE_ROOT / "expected.toml"
    ).read_bytes()


def test_m9_bare_cli_defaults_toml_from_the_audit_run_stamp(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """m9 FAIL arm (the bug as reported).

    A bare CLI invocation (no --toml) must still write the TOML the task's
    own description promises, deriving the path from the audit run's
    `args.json` stamp rather than silently skipping it at rc=0.
    """
    audit_dir = _audit_copy(tmp_path, "audit")
    (audit_dir / "args.json").write_text(
        json.dumps({"stamp": "2026-01-02"}), encoding="utf-8"
    )

    rc = modernization_audit.modernization_audit_main(tmp_path, audit_dir="audit")

    assert rc == 0
    expected = tmp_path / "docs" / "research" / "kb" / "reports"
    expected = expected / "modernization-audit-2026-01-02.toml"
    assert expected.read_bytes() == (FIXTURE_ROOT / "expected.toml").read_bytes()
    capsys.readouterr()


def test_m9_bare_cli_without_a_usable_stamp_requires_explicit_toml(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Control arm: no default path means no silent skip.

    No args.json (or no stamp in it) means no default path can be derived,
    so the CLI must fail loudly (rc=1) rather than silently skip the TOML.
    """
    _audit_copy(tmp_path, "audit")

    rc = modernization_audit.modernization_audit_main(tmp_path, audit_dir="audit")

    assert rc == 1
    assert "pass --toml explicitly" in capsys.readouterr().err
    assert not (tmp_path / "docs").exists()


def test_m2_truthy_non_mapping_correction_raises(tmp_path: Path) -> None:
    """M2 FAIL arm: a truthy non-mapping correction entry must raise loudly.

    Matches the oracle's crash boundary exactly —
    `(corrections.get(x['id']) or {}).get('native', '')` in
    `.agent/kb/audit/aggregate.py:57` raises `AttributeError` on a truthy
    non-dict (a str/int/list has no `.get`). Silently dropping the
    correction at rc=0 would leave the TOML shipping the defective pointer
    the .md report claims was corrected.
    """
    audit_dir = _audit_copy(tmp_path, "truthy-non-mapping-correction")
    corrections_path = audit_dir / "corrections.json"
    corrections = cast(
        "dict[str, object]", json.loads(corrections_path.read_text(encoding="utf-8"))
    )
    corrections["alpha-1"] = "a truthy string, not a mapping"
    corrections_path.write_text(json.dumps(corrections), encoding="utf-8")

    with pytest.raises(TypeError, match="alpha-1"):
        modernization_audit.aggregate(audit_dir, tmp_path / "out.toml")


def test_m2_falsy_non_mapping_correction_is_silently_dropped(tmp_path: Path) -> None:
    """Control arm: a FALSY non-mapping correction entry must not raise.

    An empty string here mirrors the oracle's `or {}`, which absorbs a
    falsy value silently — raising there would make the port LOUDER than
    the oracle it mirrors, a divergence in the opposite direction from the
    one this fix exists to close.
    """
    audit_dir = _audit_copy(tmp_path, "falsy-non-mapping-correction")
    corrections_path = audit_dir / "corrections.json"
    corrections = cast(
        "dict[str, object]", json.loads(corrections_path.read_text(encoding="utf-8"))
    )
    corrections["alpha-1"] = ""
    corrections_path.write_text(json.dumps(corrections), encoding="utf-8")

    modernization_audit.aggregate(audit_dir, tmp_path / "out.toml")

    row = _row(audit_dir, "alpha-1")
    assert row["correction"] == ""


def test_m3_integer_finding_id_matches_its_verdicts(tmp_path: Path) -> None:
    """M3 FAIL arm: an integer finding id must still match its verdicts.

    Reproduces the oracle's survival computation exactly —
    `survived={'refactor': 1}, refuted=1` on a contested finding with one
    confirming and one refuting lens, per the cold review's own arm. Before
    the fix, `_load_verdicts` keyed its index with a `cast("str", ...)` (a
    typing-only no-op, not a runtime coercion), so `"101"` never matched
    `101` and the finding lost every verdict.
    """
    audit_dir = _audit_copy(tmp_path, "int-finding-id")
    alpha_path = audit_dir / "findings" / "alpha.json"
    alpha_text = alpha_path.read_text(encoding="utf-8")
    alpha = cast("dict[str, object]", json.loads(alpha_text))
    findings = cast("list[dict[str, object]]", alpha["findings"])
    findings[0]["id"] = 101  # was the string "alpha-1"
    alpha_path.write_text(json.dumps(alpha), encoding="utf-8")

    for verdict_name in ("alpha--coverage.json", "alpha--risk.json"):
        verdict_path = audit_dir / "verdicts" / verdict_name
        verdict = cast(
            "dict[str, object]", json.loads(verdict_path.read_text(encoding="utf-8"))
        )
        verdicts = cast("list[dict[str, object]]", verdict["verdicts"])
        verdicts[0]["id"] = 101
        verdict_path.write_text(json.dumps(verdict), encoding="utf-8")

    corrections_path = audit_dir / "corrections.json"
    corrections = cast(
        "dict[str, object]", json.loads(corrections_path.read_text(encoding="utf-8"))
    )
    del corrections["alpha-1"]  # the correction key does not follow the id rename
    corrections_path.write_text(json.dumps(corrections), encoding="utf-8")

    result = modernization_audit.aggregate(audit_dir, tmp_path / "int-id.toml")

    assert result.survived == {"refactor": 1}
    assert result.refuted == 1
    row = _row(audit_dir, "101")
    assert row["verify_votes"] == 2
    assert row["refuted_votes"] == 1
    assert row["survived"] is True
