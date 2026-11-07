"""coverage-gate on an llvm-cov JSON export and the source folder it must cover, as files on disk."""

import json
from pathlib import Path

import pytest

from .conftest import run


def summary(lines_covered: int, lines: int, regions_covered: int, regions: int) -> dict[str, dict[str, int]]:
    """An export file summary, as llvm-cov writes it (only the fields the gate reads)."""
    return {
        "lines": {"covered": lines_covered, "count": lines},
        "regions": {"covered": regions_covered, "count": regions},
    }


def export(tmp_path: Path, summaries: dict[str, tuple[int, int, int, int]]) -> tuple[Path, Path]:
    """Sources/A.swift and Sources/B.swift on disk; the export lists the named ones with (lines covered, lines,
    regions covered, regions), plus a test file outside Sources that the gate never looks at."""
    sources = tmp_path / "Sources"
    sources.mkdir()
    for name in ("A.swift", "B.swift"):
        (sources / name).write_text("func f() {}\n")
    files = [{"filename": str(sources / name), "summary": summary(*counts)} for name, counts in summaries.items()]
    files.append({"filename": str(tmp_path / "T.swift"), "summary": summary(0, 9, 0, 9)})
    report = tmp_path / "jbax.json"
    report.write_text(json.dumps({"data": [{"files": files}]}))
    return report, sources


def gate(capsys: pytest.CaptureFixture[str], report: Path, sources: Path) -> tuple[int, dict[str, object]]:
    code, [event], _ = run(capsys, "coverage-gate", "--report", str(report), "--sources", str(sources))
    return code, event["coverage"]


def test_every_source_fully_covered_passes(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    report, sources = export(tmp_path, {"A.swift": (10, 10, 4, 4), "B.swift": (3, 3, 1, 1)})
    code, coverage = gate(capsys, report, sources)
    assert (code, coverage["short"]) == (0, [])
    assert coverage["files"] == [
        {"file": str(sources.resolve() / "A.swift"), "lines": [10, 10], "regions": [4, 4]},
        {"file": str(sources.resolve() / "B.swift"), "lines": [3, 3], "regions": [1, 1]},
    ]


@pytest.mark.parametrize(
    ("summaries", "short"),
    [
        ({"A.swift": (10, 10, 4, 4), "B.swift": (3, 3, 1, 2)}, "B.swift: lines 3/3, regions 1/2"),
        ({"A.swift": (9, 10, 4, 4), "B.swift": (3, 3, 1, 1)}, "A.swift: lines 9/10, regions 4/4"),
        # A file the test binary does not link is missing from the export: it fails, it does not drop out.
        ({"A.swift": (10, 10, 4, 4)}, "B.swift: not in the export"),
        ({"A.swift": (0, 0, 0, 0), "B.swift": (3, 3, 1, 1)}, "A.swift: lines 0/0, regions 0/0"),
    ],
)
def test_a_file_short_of_full_coverage_fails(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, summaries: dict[str, tuple[int, int, int, int]], short: str
) -> None:
    report, sources = export(tmp_path, summaries)
    code, coverage = gate(capsys, report, sources)
    assert (code, coverage["short"]) == (1, [f"{sources.resolve()}/{short}"])


@pytest.mark.parametrize("decoded", [{}, {"data": []}, {"data": [{}]}, []])
def test_a_report_that_is_not_an_export_is_a_failure(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, decoded: object
) -> None:
    # A hostile but valid file name: a quote and a newline stay inert in the one Failure line.
    report = tmp_path / 'jb"ax\n.json'
    report.write_text(json.dumps(decoded))
    code, events, error = run(capsys, "coverage-gate", "--report", str(report), "--sources", str(tmp_path))
    assert (code, events, error) == (1, [], f"{report}: not an llvm-cov JSON export (no data[0].files)")


def test_a_folder_with_no_exported_source_fails(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    report, _ = export(tmp_path, {})
    empty = tmp_path / "Empty"
    empty.mkdir()
    assert gate(capsys, report, empty) == (1, {"files": [], "short": [f"{empty}: no Swift source in the export"]})


def test_a_skipped_file_and_a_lower_minimum(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """A skipped Foreground.swift is not looked for; the rest is gated at the minimum."""
    report, sources = export(tmp_path, {"A.swift": (19, 20, 10, 10), "B.swift": (3, 3, 1, 1)})
    (sources / "Foreground.swift").write_text("func g() {}\n")
    argv = ["coverage-gate", "--report", str(report), "--sources", str(sources), "--skip", '["Foreground.swift"]']
    assert run(capsys, *argv, "--minimum", "95")[0] == 0
    code, [event], _ = run(capsys, *argv, "--minimum", "96")
    assert (code, event["coverage"]["short"]) == (1, [f"{sources.resolve()}/A.swift: lines 19/20, regions 10/10"])


def test_only_foreground_swift_may_be_skipped(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Skipping any other file would be marking code out of the count to reach the gate."""
    report, sources = export(tmp_path, {"A.swift": (10, 10, 4, 4), "B.swift": (3, 3, 1, 1)})
    code, events, error = run(
        capsys, "coverage-gate", "--report", str(report), "--sources", str(sources), "--skip", "B.swift"
    )
    assert (code, events, "Foreground.swift" in error) == (1, [], True)
