# Copyright (c) 2026 Raymond Manaloto
"""InstructionsLoaded report: eager / fired / never-fired, from real sessions.

Turns the JSONL records `instructions_observer.py` appends into three
answers a static gate cannot give (#917):

- **eager** — files that loaded at ``session_start`` (the unscoped corpus,
  today's baseline before #916's migration).
- **fired** — scoped rules (a ``paths:`` frontmatter block) actually seen
  loading via ``path_glob_match`` in a real session.
- **never_fired** — scoped rules present on disk that NO recorded session has
  ever loaded. A rule scoped with a glob that matches nothing is, on disk,
  indistinguishable from one loading fine; this is the one measurement that
  tells them apart, per C6 (`.claude/rules/probes-need-a-control-arm.md`).

This side has no hot-path constraint — it runs on demand
(`dotfiles-setup instructions-report` / `mise run instructions-report`), so
normal project imports are fine here.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

#: Kept identical to instructions_observer._RECORDS_DIRNAME. Not imported
#: from there — that module is stdlib-only by contract (C1), and importing
#: it here would be harmless today but couples the hot-path module's import
#: graph to whatever this one grows into later.
_RECORDS_DIRNAME = ".agent/instructions-loaded"
_RULES_SUBDIR = (".claude", "rules")

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class RuleLoadReport:
    """The three answers: what loaded eagerly, what fired, what never fired."""

    eager: tuple[str, ...]
    fired: tuple[str, ...]
    never_fired: tuple[str, ...]
    by_reason: Mapping[str, int]


def _default_project_root() -> Path:
    """Same resolution order as the observer: env var, then this module's repo root."""
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        candidate = Path(env_root)
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parent.parent.parent.parent


def scoped_rules_on_disk(rules_dir: Path) -> tuple[str, ...]:
    """Repo-relative paths of every rule file with a `paths:` frontmatter list.

    Args:
        rules_dir: The `.claude/rules/` directory.
    """
    project_root = rules_dir.parent.parent
    scoped: list[str] = []
    for path in sorted(rules_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        match = _FRONTMATTER_RE.match(text)
        if not match:
            continue
        try:
            front = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            continue
        if isinstance(front, dict) and isinstance(front.get("paths"), list):
            scoped.append(str(path.relative_to(project_root)))
    return tuple(scoped)


def _iter_records(records_dir: Path) -> Iterable[dict]:
    """Yield every well-formed JSON object across every session's JSONL file.

    A malformed line (partial write, corrupt JSON) is skipped rather than
    raising — this is a report over BEST-EFFORT data, and one bad line must
    not hide every other record in the file.
    """
    if not records_dir.is_dir():
        return
    for jsonl_path in sorted(records_dir.glob("*.jsonl")):
        try:
            lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def build_report(records: Iterable[dict], scoped: Iterable[str]) -> RuleLoadReport:
    """Partition observed records against the scoped-rules-on-disk set (C6)."""
    scoped_set = set(scoped)
    eager: set[str] = set()
    fired: set[str] = set()
    by_reason: Counter[str] = Counter()
    for record in records:
        reason = record.get("load_reason")
        if isinstance(reason, str):
            by_reason[reason] += 1
        file_path = record.get("file_path")
        if not isinstance(file_path, str):
            continue
        if reason == "session_start":
            eager.add(file_path)
        elif reason == "path_glob_match" and file_path in scoped_set:
            fired.add(file_path)
    never_fired = tuple(sorted(scoped_set - fired))
    return RuleLoadReport(
        eager=tuple(sorted(eager)),
        fired=tuple(sorted(fired)),
        never_fired=never_fired,
        by_reason=dict(sorted(by_reason.items())),
    )


def run_report(project_root: Path, *, json_output: bool = False) -> int:
    """Build and render the report for one project root. Always returns 0.

    A report over data that does not exist yet (no session has run since
    this observer was wired) is legitimate output — "0 records, N rules
    unaccounted for" — not a failure.
    """
    records_dir = project_root / _RECORDS_DIRNAME
    rules_dir = project_root.joinpath(*_RULES_SUBDIR)
    scoped = scoped_rules_on_disk(rules_dir)
    records = list(_iter_records(records_dir))
    report = build_report(records, scoped)
    if json_output:
        sys.stdout.write(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(_render(report))
    return 0


def _render(report: RuleLoadReport) -> str:
    lines = [f"eager (session_start): {len(report.eager)}"]
    lines.extend(f"  {path}" for path in report.eager)
    lines.append(f"fired (scoped, seen via path_glob_match): {len(report.fired)}")
    lines.extend(f"  {path}" for path in report.fired)
    lines.append(
        "never fired (scoped, on disk, never observed loading): "
        f"{len(report.never_fired)}"
    )
    lines.extend(f"  {path}" for path in report.never_fired)
    lines.append("by load_reason:")
    lines.extend(f"  {reason}: {count}" for reason, count in report.by_reason.items())
    return "\n".join(lines) + "\n"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dotfiles-setup instructions-report",
        description="InstructionsLoaded observer report: eager / fired / never-fired.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Repo root (default: $CLAUDE_PROJECT_DIR, else this module's own repo)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON output instead of the human-readable report",
    )
    return parser


def instructions_report_main(argv: list[str] | None = None) -> int:
    """CLI entrypoint (`dotfiles-setup instructions-report` / `python -m` direct)."""
    args = _build_arg_parser().parse_args(argv)
    project_root = args.project_root or _default_project_root()
    return run_report(project_root, json_output=args.json)


if __name__ == "__main__":
    raise SystemExit(instructions_report_main())
