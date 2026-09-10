# Copyright (c) 2026 Raymond Manaloto
"""Behavioral compatibility tests for the modernization-audit aggregator."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import modernization_audit

if TYPE_CHECKING:
    import pytest

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
