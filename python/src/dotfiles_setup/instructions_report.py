# Copyright (c) 2026 Raymond Manaloto
"""InstructionsLoaded report: eager / fired / never-fired, from real sessions.

Turns the JSONL records `instructions_observer.py` appends into the answers a
static gate cannot give (#917):

- **eager** — files that loaded at ``session_start`` (the unscoped corpus,
  today's baseline before #916's migration).
- **fired** — scoped rules (a ``paths:`` frontmatter block) actually seen
  loading via ``path_glob_match`` — the static gate's own trigger path.
- **loaded_other_reason** — scoped rules observed loading, but never via
  ``path_glob_match`` (``session_start``, ``include``, ``compact``,
  ``nested_traversal``). Reported separately from `fired` rather than folded
  into it, because "loaded" and "loaded via the mechanism the gate checks"
  are different facts.
- **never_fired** — scoped rules present on disk that NO recorded session has
  observed loading by ANY reason. A rule scoped with a glob that matches
  nothing is, on disk, indistinguishable from one loading fine; this is the
  one measurement that tells them apart, per C6
  (`.claude/rules/probes-need-a-control-arm.md`).

A rule can never appear in more than one of `fired` / `loaded_other_reason` /
`never_fired` in the same report (R1) — `build_report`'s own partition
guarantees this by construction: `never_fired` is defined as the scoped set
MINUS everything observed loading, never computed independently.

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
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

#: Kept identical to instructions_observer._RECORDS_DIRNAME /
#: _ERROR_LOG_NAME. Not imported from there — that module is stdlib-only by
#: contract (C1), and importing it here would be harmless today but couples
#: the hot-path module's import graph to whatever this one grows into later.
_RECORDS_DIRNAME = ".agent/instructions-loaded"
_ERROR_LOG_NAME = "errors.log"
_RULES_SUBDIR = (".claude", "rules")

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


@dataclass(frozen=True)
class RuleLoadReport:
    """The partition, plus the provenance needed to trust it (R5)."""

    eager: tuple[str, ...]
    fired: tuple[str, ...]
    loaded_other_reason: tuple[str, ...]
    never_fired: tuple[str, ...]
    by_reason: Mapping[str, int]
    sessions_observed: int
    records_read: int
    records_malformed: int
    first_ts: str | None
    last_ts: str | None
    errors_log_lines: int
    insufficient_data: bool


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

    R8: recursive (``rglob``) — nested `.claude/rules/` subdirectories are a
    documented sharing mechanism, so a non-recursive glob would silently
    never see scoped rules filed under one.

    Args:
        rules_dir: The `.claude/rules/` directory.
    """
    project_root = rules_dir.parent.parent
    scoped: list[str] = []
    for path in sorted(rules_dir.rglob("*.md")):
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


def _iter_records(records_dir: Path) -> Iterable[tuple[dict | None, bool]]:
    """Yield ``(record_or_none, malformed)`` for every line across every session file.

    A malformed line (partial write, corrupt JSON, valid JSON that isn't an
    object) is NOT skipped silently — it yields ``(None, True)`` so the
    caller can count it (R5) — this is a report over BEST-EFFORT data, and
    one bad line must not hide every other record in the file, but it also
    must not vanish without a trace.
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
                yield None, True
                continue
            if isinstance(record, dict):
                yield record, False
            else:
                yield None, True


def _count_errors_log_lines(records_dir: Path) -> int:
    path = records_dir / _ERROR_LOG_NAME
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines() if line.strip())


def build_report(records: Iterable[dict], scoped: Iterable[str]) -> RuleLoadReport:
    """Partition observed records against the scoped-rules-on-disk set (C6, R1).

    A rule counts as LOADED on any ``load_reason`` — not only
    ``path_glob_match`` — so `never_fired` is computed as the scoped set
    MINUS everything observed loading by any reason, never independently.
    That is what makes the two-bucket invariant (never both `fired`/
    `loaded_other_reason` AND `never_fired`) hold by construction rather than
    by convention.

    `records_malformed`, `errors_log_lines` default to 0 here — they are
    properties of the FILES, not the parsed records, and `run_report` fills
    them in via `dataclasses.replace` after reading the records directory
    itself.
    """
    records = list(records)
    scoped_set = set(scoped)
    eager: set[str] = set()
    fired: set[str] = set()
    loaded_other_reason: set[str] = set()
    by_reason: Counter[str] = Counter()
    sessions_with_start: set[str] = set()
    timestamps: list[str] = []
    for record in records:
        reason = record.get("load_reason")
        if isinstance(reason, str):
            by_reason[reason] += 1
        ts = record.get("ts")
        if isinstance(ts, str):
            timestamps.append(ts)
        if reason == "session_start":
            session_id = record.get("session_id")
            if isinstance(session_id, str):
                sessions_with_start.add(session_id)
        file_path = record.get("file_path")
        if not isinstance(file_path, str):
            continue
        if reason == "session_start":
            eager.add(file_path)
        if isinstance(reason, str) and file_path in scoped_set:
            if reason == "path_glob_match":
                fired.add(file_path)
            else:
                loaded_other_reason.add(file_path)
    loaded_other_reason -= fired
    never_fired = tuple(sorted(scoped_set - fired - loaded_other_reason))
    return RuleLoadReport(
        eager=tuple(sorted(eager)),
        fired=tuple(sorted(fired)),
        loaded_other_reason=tuple(sorted(loaded_other_reason)),
        never_fired=never_fired,
        by_reason=dict(sorted(by_reason.items())),
        sessions_observed=len(sessions_with_start),
        records_read=len(records),
        records_malformed=0,
        first_ts=min(timestamps) if timestamps else None,
        last_ts=max(timestamps) if timestamps else None,
        errors_log_lines=0,
        insufficient_data=len(sessions_with_start) == 0,
    )


def run_report(project_root: Path, *, json_output: bool = False) -> int:
    """Build and render the report for one project root. Always returns 0.

    R2: when zero sessions have a recorded ``session_start`` (no session has
    been observed end-to-end since the hook was wired, or the records
    directory is empty), the partition is not meaningful — printing it as
    though it were would delete working rules on the strength of a hook that
    simply hadn't run yet for that session. That state renders as
    "insufficient data" and the rule lists are OMITTED, not printed empty.
    """
    records_dir = project_root / _RECORDS_DIRNAME
    rules_dir = project_root.joinpath(*_RULES_SUBDIR)
    scoped = scoped_rules_on_disk(rules_dir)
    records: list[dict] = []
    malformed = 0
    for record, is_malformed in _iter_records(records_dir):
        if is_malformed:
            malformed += 1
        elif record is not None:
            records.append(record)
    report = build_report(records, scoped)
    report = replace(
        report,
        records_malformed=malformed,
        errors_log_lines=_count_errors_log_lines(records_dir),
    )
    if json_output:
        sys.stdout.write(
            json.dumps(_json_payload(report), indent=2, sort_keys=True) + "\n"
        )
    else:
        sys.stdout.write(_render(report))
    return 0


def _json_payload(report: RuleLoadReport) -> dict:
    """The JSON shape — omits the rule-list fields entirely when insufficient (R2)."""
    payload = asdict(report)
    if report.insufficient_data:
        for key in ("eager", "fired", "loaded_other_reason", "never_fired"):
            del payload[key]
    return payload


def _render(report: RuleLoadReport) -> str:
    records_line = (
        f"records read: {report.records_read} "
        f"(malformed lines skipped: {report.records_malformed})"
    )
    header = [
        f"sessions observed: {report.sessions_observed}",
        records_line,
        f"observed range: {report.first_ts or '-'} .. {report.last_ts or '-'}",
        f"errors.log lines: {report.errors_log_lines}",
    ]
    if report.insufficient_data:
        header.append(
            "insufficient data: 0 sessions with a recorded session_start — "
            "no rule list is printed. A partial session (hook wired mid-run, "
            "or a fresh records directory) cannot tell 'never fires' from "
            "'never yet observed'."
        )
        return "\n".join(header) + "\n"
    lines = [*header, f"eager (session_start): {len(report.eager)}"]
    lines.extend(f"  {path}" for path in report.eager)
    lines.append(f"fired (scoped, seen via path_glob_match): {len(report.fired)}")
    lines.extend(f"  {path}" for path in report.fired)
    lines.append(
        "loaded, other reason (scoped, seen but never via path_glob_match): "
        f"{len(report.loaded_other_reason)}"
    )
    lines.extend(f"  {path}" for path in report.loaded_other_reason)
    lines.append(
        "never fired (scoped, on disk, never observed loading by any reason): "
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
