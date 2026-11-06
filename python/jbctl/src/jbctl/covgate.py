"""A coverage gate for llvm-cov JSON exports (jbax, Swift): every source file present, each covered enough."""

# llvm-cov can leave out whole files (-ignore-filename-regex) but not lines (llvm-project#33625). So no line is
# marked: every file under the sources folder must be in the export, at the minimum share of lines and of
# regions, except Foreground.swift when asked to skip it, the only file the schema lets anyone skip (only the
# debug route reaches it). A file the export lacks (one the test binary does not link) fails rather than drops
# out. Swift exports carry no branch records, so this gate is lines and regions only.

import json
from collections.abc import Sequence
from pathlib import Path

from .models import Coverage, FileCoverage


def check(report: Path, sources: Path, skip: Sequence[str], minimum: float) -> Coverage:
    data = json.loads(report.read_text())["data"][0]["files"]
    exported = {Path(file["filename"]).resolve(): file["summary"] for file in data}
    files: list[FileCoverage] = []
    short: list[str] = []
    for source in sorted(path for path in sources.resolve().rglob("*.swift") if path.name not in skip):
        summary = exported.get(source)
        if summary is None:
            short.append(f"{source}: not in the export")
            continue
        lines = [summary["lines"]["covered"], summary["lines"]["count"]]
        regions = [summary["regions"]["covered"], summary["regions"]["count"]]
        files.append(FileCoverage(file=str(source), lines=lines, regions=regions))
        if not lines[1] or min(lines[0] / lines[1], regions[0] / max(regions[1], 1)) * 100 < minimum:
            short.append(f"{source}: lines {lines[0]}/{lines[1]}, regions {regions[0]}/{regions[1]}")
    if not files:
        short.append(f"{sources}: no Swift source in the export")
    return Coverage(files=files, short=short)
