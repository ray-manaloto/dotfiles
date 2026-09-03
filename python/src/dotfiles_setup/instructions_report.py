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

#: S2 — the minimum number of observed DISTINCT SESSIONS (by
#: ``session_id``) before `never_fired` is trusted enough to print. Below
#: this, an unfired scoped rule is indistinguishable from one this report
#: simply hasn't watched long enough. `eager`/`fired`/`loaded_other_reason`
#: are POSITIVE observations — true from a single record — and are never
#: gated on this threshold.
#:
#: Counting EVENTS instead of sessions was tried and found wrong: one
#: session emits one ``session_start`` record per eager instruction file
#: (~30 in this repo), so a single session satisfied the threshold on its
#: own — the false positive this whole feature exists to avoid. Counting
#: MUST therefore be by distinct ``session_id``, with one exception: a
#: corpus with ``session_id: null`` (or missing/non-string — #916's own
#: hook-wiring window produced exactly that shape) must still be able to
#: accumulate SOME coverage rather than being permanently unable to reach
#: the threshold, since those records are indistinguishable from one
#: another and cannot be counted separately. See `build_report`.
_MIN_SESSIONS_FOR_NEVER_FIRED = 3


@dataclass(frozen=True)
class RuleLoadReport:
    """The partition, plus the provenance needed to trust it (R5)."""

    eager: tuple[str, ...]
    fired: tuple[str, ...]
    loaded_other_reason: tuple[str, ...]
    never_fired: tuple[str, ...]
    by_reason: Mapping[str, int]
    sessions_observed: int
    never_fired_min_sessions: int
    never_fired_sufficient: bool
    records_read: int
    records_malformed: int
    first_ts: str | None
    last_ts: str | None
    errors_log_lines: int


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

    S3: ``recurse_symlinks=True`` — a symlinked rules subdirectory is the
    SAME documented sharing mechanism, and ``Path.rglob`` defaults to
    ``recurse_symlinks=False`` (Python 3.13+). Without this, the observer's
    R7 fix (which does NOT resolve through a symlink) and this function
    disagree on a symlinked rule: the observer reports it under its
    repo-relative symlinked path, this function never visits it at all, and
    the rule appears in no report bucket whatsoever — invisible, with no
    "insufficient data" signal either. `_normalize_path`'s R7 docstring
    names this exact scenario as its reason for existing, so the two sides
    must actually agree.

    Args:
        rules_dir: The `.claude/rules/` directory.
    """
    project_root = rules_dir.parent.parent
    scoped: list[str] = []
    for path in sorted(rules_dir.rglob("*.md", recurse_symlinks=True)):
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

    A rule counts as LOADED on any ``load_reason`` — including a MISSING or
    non-string one (S1: the observer itself writes ``load_reason: null``
    whenever the harness omits the key, via `_string_or_none`, and that
    shape is asserted by `tests/test_instructions_observer.py`) — so
    `never_fired` is computed as the scoped set MINUS every ``file_path``
    that appears in ANY record for it, never independently. `fired` /
    `loaded_other_reason` still partition on the reason string, but the
    membership test that removes a rule from `never_fired` is reason-blind:
    every rule that is `fired` or `loaded_other_reason` is, by construction,
    NOT `never_fired`.

    `sessions_observed` counts DISTINCT SESSIONS, not ``session_start``
    events (S2 respec) — one session emits one ``session_start`` record per
    eager instruction file, so counting events let a single session satisfy
    the threshold on its own. Distinct non-null string ``session_id``
    values among ``session_start`` records are counted individually;
    ``session_start`` records with no usable ``session_id`` (missing, null,
    or non-string) are indistinguishable from one another and so contribute
    AT MOST ONE additional pseudo-session in total — never zero, so a
    corpus where ``session_id`` is always null still accumulates coverage.

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
    session_ids: set[str] = set()
    has_unidentified_session = False
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
                session_ids.add(session_id)
            else:
                has_unidentified_session = True
        file_path = record.get("file_path")
        if not isinstance(file_path, str):
            continue
        if reason == "session_start":
            eager.add(file_path)
        if file_path in scoped_set:
            if reason == "path_glob_match":
                fired.add(file_path)
            else:
                loaded_other_reason.add(file_path)
    loaded_other_reason -= fired
    never_fired = tuple(sorted(scoped_set - fired - loaded_other_reason))
    sessions_observed = len(session_ids) + (1 if has_unidentified_session else 0)
    return RuleLoadReport(
        eager=tuple(sorted(eager)),
        fired=tuple(sorted(fired)),
        loaded_other_reason=tuple(sorted(loaded_other_reason)),
        never_fired=never_fired,
        by_reason=dict(sorted(by_reason.items())),
        sessions_observed=sessions_observed,
        never_fired_min_sessions=_MIN_SESSIONS_FOR_NEVER_FIRED,
        never_fired_sufficient=sessions_observed >= _MIN_SESSIONS_FOR_NEVER_FIRED,
        records_read=len(records),
        records_malformed=0,
        first_ts=min(timestamps) if timestamps else None,
        last_ts=max(timestamps) if timestamps else None,
        errors_log_lines=0,
    )


def run_report(project_root: Path, *, json_output: bool = False) -> int:
    """Build and render the report for one project root. Always returns 0.

    S2: only `never_fired` — an ABSENCE claim — is gated on sufficient
    ``session_start`` coverage (`_MIN_SESSIONS_FOR_NEVER_FIRED`). `eager`,
    `fired`, and `loaded_other_reason` are POSITIVE observations, each true
    the instant a single matching record exists, and are always printed.
    Gating the whole report (R2's original fix) suppressed real, correct
    output right alongside the unreliable one.
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
    """The JSON shape (S5): every key is ALWAYS present — never deleted.

    `never_fired` becomes ``null`` (not an omitted key, not an empty list —
    empty would claim "checked, zero found," which is a different, false
    claim) when `never_fired_sufficient` is False (S2); every other field,
    including the three positive-observation buckets, is always the real
    computed value.
    """
    payload = asdict(report)
    if not report.never_fired_sufficient:
        payload["never_fired"] = None
    return payload


def _render(report: RuleLoadReport) -> str:
    records_line = (
        f"records read: {report.records_read} "
        f"(malformed lines skipped: {report.records_malformed})"
    )
    lines = [
        f"sessions observed: {report.sessions_observed}",
        records_line,
        f"observed range: {report.first_ts or '-'} .. {report.last_ts or '-'}",
        f"errors.log lines: {report.errors_log_lines}",
        f"eager (session_start): {len(report.eager)}",
    ]
    lines.extend(f"  {path}" for path in report.eager)
    lines.append(f"fired (scoped, seen via path_glob_match): {len(report.fired)}")
    lines.extend(f"  {path}" for path in report.fired)
    lines.append(
        "loaded, other reason (scoped, seen but never via path_glob_match): "
        f"{len(report.loaded_other_reason)}"
    )
    lines.extend(f"  {path}" for path in report.loaded_other_reason)
    if report.never_fired_sufficient:
        lines.append(
            "never fired (scoped, on disk, never observed loading by any reason): "
            f"{len(report.never_fired)}"
        )
        lines.extend(f"  {path}" for path in report.never_fired)
    else:
        lines.append(
            "never fired: NOT SHOWN — insufficient coverage "
            f"({report.sessions_observed}/{report.never_fired_min_sessions} "
            "distinct sessions observed). A rule scoped with a dead glob "
            "is indistinguishable from one this report hasn't watched long "
            "enough yet."
        )
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
