# Copyright (c) 2026 Raymond Manaloto
"""Deterministically aggregate modernization-audit artifacts.

This is the tracked form of the audit run's scratch aggregator. It preserves
the original file formats and survival rule while making both input and output
paths explicit for fresh clones and isolated tests.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

LENSES = ("coverage", "risk", "currency")
MIN_VERDICTS = 2
REFUTED_LIMIT = 2

type JsonMap = dict[str, Any]
type VerdictIndex = defaultdict[str, dict[str, dict[str, JsonMap]]]


@dataclass(frozen=True)
class AggregateResult:
    """The counts printed by the original scratch aggregator."""

    units: int
    findings: int
    by_disposition: dict[str, int]
    survived: dict[str, int]
    refuted: int
    unverified_contested: int
    verdict_files: int
    aggregate_bytes: int
    malformed_verdict_files: tuple[dict[str, str], ...]
    corrections_applied: int

    def stdout_payload(self) -> dict[str, object]:
        """Return the insertion-ordered JSON payload used by the CLI."""
        return {
            "units": self.units,
            "findings": self.findings,
            "by_disposition": self.by_disposition,
            "survived": self.survived,
            "refuted": self.refuted,
            "unverified_contested": self.unverified_contested,
            "verdict_files": self.verdict_files,
            "aggregate_bytes": self.aggregate_bytes,
            "malformed_verdict_files": list(self.malformed_verdict_files),
            "corrections_applied": self.corrections_applied,
        }


def _read_json_object(path: Path) -> JsonMap:
    """Read one JSON object, preserving the scratch script's permissive shape."""
    return cast("JsonMap", json.loads(path.read_text(encoding="utf-8")))


def _load_findings(audit_dir: Path) -> dict[str, JsonMap]:
    """Load finding files in deterministic filename order."""
    return {
        path.stem: _read_json_object(path)
        for path in sorted(audit_dir.glob("findings/*.json"))
    }


def _load_verdicts(
    audit_dir: Path,
) -> tuple[VerdictIndex, list[dict[str, str]]]:
    """Load verdict indexes and report malformed files loudly."""
    verdicts: VerdictIndex = defaultdict(dict)
    malformed: list[dict[str, str]] = []
    for path in sorted(audit_dir.glob("verdicts/*.json")):
        if "--" not in path.stem:
            continue
        unit, lens = path.stem.rsplit("--", 1)
        try:
            data = _read_json_object(path)
        except json.JSONDecodeError as error:
            malformed.append({"file": path.name, "error": str(error)})
            sys.stderr.write(
                f"WARNING: malformed verdict file dropped: {path.name}: {error}\n"
            )
            continue
        entries = cast("list[JsonMap]", data.get("verdicts", []))
        verdicts[unit][lens] = {
            cast("str", entry["id"]): entry
            for entry in entries
            if isinstance(entry, dict) and "id" in entry
        }
    return verdicts, malformed


def _load_corrections(audit_dir: Path) -> JsonMap:
    """Load synthesis-stage citation corrections when present."""
    path = audit_dir / "corrections.json"
    if not path.exists():
        return {}
    return {
        key: value
        for key, value in _read_json_object(path).items()
        if not key.startswith("_")
    }


def _correction_value(corrections: JsonMap, finding_id: str, key: str) -> str:
    """Read one optional correction value from the dynamic audit payload."""
    correction = corrections.get(finding_id) or {}
    if not isinstance(correction, dict):
        return ""
    return str(correction.get(key, ""))


def _verdicts_for(
    verdicts: VerdictIndex, unit: str, finding_id: str
) -> list[tuple[str, JsonMap]]:
    """Return this finding's verdicts in the original fixed lens order."""
    return [
        (lens, verdicts[unit][lens][finding_id])
        for lens in LENSES
        if lens in verdicts[unit] and finding_id in verdicts[unit][lens]
    ]


def _build_rows(
    findings: dict[str, JsonMap],
    verdicts: VerdictIndex,
    corrections: JsonMap,
) -> tuple[list[JsonMap], dict[str, dict[str, int]]]:
    """Build aggregate rows and per-unit coverage."""
    rows: list[JsonMap] = []
    coverage: dict[str, dict[str, int]] = {}
    for unit, data in findings.items():
        counts: Counter[str] = Counter()
        unit_findings = cast("list[JsonMap]", data.get("findings", []))
        for finding in unit_findings:
            disposition = str(finding.get("disposition", "unknown"))
            finding_id = str(finding["id"])
            counts[disposition] += 1
            contested = disposition in ("retire", "refactor")
            found_verdicts = _verdicts_for(verdicts, unit, finding_id)
            refuted = sum(
                1 for _, verdict in found_verdicts if verdict.get("refuted") is True
            )
            survived = (
                len(found_verdicts) >= MIN_VERDICTS and refuted < REFUTED_LIMIT
                if contested
                else True
            )
            rows.append(
                {
                    "id": finding_id,
                    "unit": unit,
                    "kind": data.get("kind", ""),
                    "disposition": disposition,
                    "confidence": float(finding.get("confidence", 0) or 0),
                    "custom_thing": finding.get("custom_thing", ""),
                    "evidence": finding.get("evidence", ""),
                    "native_alternative": finding.get("native_alternative", ""),
                    "alternative_evidence": finding.get("alternative_evidence", ""),
                    "rationale": finding.get("rationale", ""),
                    "probe": finding.get("probe", "") or "",
                    "verify_votes": len(found_verdicts),
                    "refuted_votes": refuted,
                    "survived": survived,
                    "lenses_present": [lens for lens, _ in found_verdicts],
                    "verdict_reasons": {
                        lens: {
                            "refuted": verdict.get("refuted"),
                            "reason": verdict.get("reason", ""),
                            "evidence": verdict.get("evidence", ""),
                        }
                        for lens, verdict in found_verdicts
                    },
                    "schedule": "",
                    "correction": _correction_value(corrections, finding_id, "native"),
                    "correction_custom": _correction_value(
                        corrections, finding_id, "custom"
                    ),
                }
            )
        counts["contested_unverified"] = sum(
            1
            for finding in unit_findings
            if finding.get("disposition") in ("retire", "refactor")
            and not any(
                str(finding["id"]) in verdicts[unit].get(lens, {}) for lens in LENSES
            )
        )
        coverage[unit] = dict(counts)
    return rows, coverage


def _write_side_outputs(
    audit_dir: Path,
    rows: list[JsonMap],
    coverage: dict[str, dict[str, int]],
    existing: list[str],
) -> int:
    """Write the four side outputs and return aggregate.json's byte size."""
    aggregate_path = audit_dir / "aggregate.json"
    aggregate_path.write_text(
        json.dumps({"rows": rows, "coverage": coverage}, indent=0),
        encoding="utf-8",
    )
    (audit_dir / "coverage.json").write_text(
        json.dumps(coverage, indent=1), encoding="utf-8"
    )
    compact_keys = (
        "id",
        "unit",
        "kind",
        "disposition",
        "confidence",
        "verify_votes",
        "refuted_votes",
        "survived",
        "custom_thing",
        "native_alternative",
        "evidence",
        "alternative_evidence",
    )
    truncated = {
        "custom_thing",
        "native_alternative",
        "evidence",
        "alternative_evidence",
    }
    compact = [
        {
            key: str(row[key])[:160] if key in truncated else row[key]
            for key in compact_keys
        }
        for row in rows
    ]
    (audit_dir / "summary.json").write_text(
        json.dumps({"rows": compact, "coverage": coverage}, separators=(",", ":")),
        encoding="utf-8",
    )
    (audit_dir / "existing-verdicts.json").write_text(
        json.dumps(existing), encoding="utf-8"
    )
    return aggregate_path.stat().st_size


def _toml_quote(value: object) -> str:
    """Escape a TOML basic string exactly like the scratch aggregator."""
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _render_toml(
    rows: list[JsonMap],
    findings_count: int,
    totals: Counter[str],
    survived: Counter[str],
    malformed: list[dict[str, str]],
) -> str:
    """Render the deterministic TOML companion without a trailing newline."""
    refuted = sum(1 for row in rows if not row["survived"])
    unverified = sum(
        1
        for row in rows
        if row["disposition"] in ("retire", "refactor") and row["verify_votes"] == 0
    )
    malformed_note = (
        ": " + ", ".join(item["file"] for item in malformed)
        if malformed
        else " (every verdict file parsed)"
    )
    output = [
        "# Modernization audit findings — deterministic aggregate (no LLM)",
        (
            f"# units={findings_count} findings={len(rows)} "
            f"retire={totals['retire']} (survived {survived['retire']}) "
            f"refactor={totals['refactor']} (survived {survived['refactor']}) "
            f"keep={totals['keep']} unknown={totals['unknown']} "
            f"refuted={refuted} unverified_contested={unverified}"
        ),
        (
            "# Survival: a retire/refactor finding survives with >=2 lens "
            "verdicts and <2 refuted; keep/unknown are not voted on."
        ),
        f"# malformed_verdict_files={len(malformed)}{malformed_note}",
        (
            "# `correction` / `correction_custom` carry synthesis-stage citation "
            "repairs from .agent/kb/audit/corrections.json."
        ),
        (
            "# The finder's own evidence/alternative_evidence strings are NEVER "
            "edited; a correction is an additional field,"
        ),
        (
            "# so the defective pointer and its repair travel together in this "
            "file exactly as they do in the .md report."
        ),
        "",
    ]
    for row in rows:
        output.append("[[finding]]")
        output.extend(
            f"{key} = {_toml_quote(row[key])}"
            for key in ("id", "unit", "kind", "disposition")
        )
        output.append(f"confidence = {row['confidence']:.2f}")
        output.extend(
            f"{key} = {_toml_quote(row[key])}"
            for key in (
                "custom_thing",
                "evidence",
                "native_alternative",
                "alternative_evidence",
                "rationale",
                "probe",
                "correction",
                "correction_custom",
            )
        )
        output.append(f"verify_votes = {row['verify_votes']}")
        output.append(f"refuted_votes = {row['refuted_votes']}")
        output.append(f"survived = {'true' if row['survived'] else 'false'}")
        output.append(f"schedule = {_toml_quote(row['schedule'])}")
        output.append("")
    return "\n".join(output)


def aggregate(audit_dir: Path, toml_out: Path | None) -> AggregateResult:
    """Aggregate one audit directory and optionally write its TOML report."""
    findings = _load_findings(audit_dir)
    verdicts, malformed = _load_verdicts(audit_dir)
    rows, coverage = _build_rows(findings, verdicts, _load_corrections(audit_dir))
    existing = sorted(f"{unit}--{lens}" for unit in verdicts for lens in verdicts[unit])
    aggregate_bytes = _write_side_outputs(audit_dir, rows, coverage, existing)
    totals: Counter[str] = Counter(str(row["disposition"]) for row in rows)
    survived: Counter[str] = Counter(
        str(row["disposition"])
        for row in rows
        if row["survived"] and row["disposition"] in ("retire", "refactor")
    )
    if toml_out is not None:
        toml_out.parent.mkdir(parents=True, exist_ok=True)
        toml_out.write_text(
            _render_toml(rows, len(findings), totals, survived, malformed),
            encoding="utf-8",
        )
    return AggregateResult(
        units=len(findings),
        findings=len(rows),
        by_disposition=dict(totals),
        survived=dict(survived),
        refuted=sum(1 for row in rows if not row["survived"]),
        unverified_contested=sum(
            1
            for row in rows
            if row["disposition"] in ("retire", "refactor") and row["verify_votes"] == 0
        ),
        verdict_files=len(existing),
        aggregate_bytes=aggregate_bytes,
        malformed_verdict_files=tuple(malformed),
        corrections_applied=sum(
            1 for row in rows if row["correction"] or row["correction_custom"]
        ),
    )


def modernization_audit_main(
    project_root: Path,
    *,
    audit_dir: str = ".agent/kb/audit",
    toml_out: str | None = None,
) -> int:
    """CLI entry point for deterministic modernization-audit aggregation."""
    audit_path = Path(audit_dir)
    if not audit_path.is_absolute():
        audit_path = project_root / audit_path
    output_path = Path(toml_out) if toml_out is not None else None
    if output_path is not None and not output_path.is_absolute():
        output_path = project_root / output_path
    result = aggregate(audit_path, output_path)
    sys.stdout.write(json.dumps(result.stdout_payload()) + "\n")
    return 0
