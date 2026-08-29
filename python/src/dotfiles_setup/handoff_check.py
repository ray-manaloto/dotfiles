# Copyright (c) 2026 Raymond Manaloto
"""Validate the mechanically checkable citations in a session handoff.

This is intentionally a small, read-only linter.  It checks repo-relative
``file:line`` citations and ``mise run <task>`` names; it does not attempt to
prove that a handoff is complete or reconcile claims across handoff versions.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_MISE_TIMEOUT = 30
_HANDOFF_RE = re.compile(
    r"^session-(?P<date>\d{4}-\d{2}-\d{2})(?:-?(?P<suffix>[A-Za-z]))?\.md$"
)
_PATH_CITATION_RE = re.compile(
    r"(?<![\w./:-])(?P<citation>[\w./-]+\.[A-Za-z]\w*:(?P<start>\d+)"
    r"(?:-(?P<end>\d+))?)(?![\w-])"
)
_TASK_CITATION_RE = re.compile(
    r"\bmise[ \t]+run[ \t]+(?P<name>[A-Za-z0-9][\w-]*)(?![\w:-])"
)


class Verdict(Enum):
    """Every finding this scoped validator can emit."""

    OK = "ok"
    MISSING_PATH = "missing_path"
    BAD_LINE_RANGE = "bad_line_range"
    UNKNOWN_TASK = "unknown_task"


@dataclass(frozen=True)
class Finding:
    """One stale citation and the reason it failed validation."""

    verdict: Verdict
    citation: str
    detail: str


def newest_handoff(repo_root: Path) -> Path | None:
    """Return the newest local handoff by ISO date and optional letter suffix."""
    plans = repo_root / ".agent" / "plans"
    if not plans.is_dir():
        return None

    candidates: list[tuple[tuple[str, int], Path]] = []
    for path in plans.glob("session-*.md"):
        match = _HANDOFF_RE.fullmatch(path.name)
        if match is None:
            continue
        suffix = match.group("suffix")
        suffix_order = 0 if suffix is None else ord(suffix.lower()) - ord("a") + 1
        candidates.append(((match.group("date"), suffix_order), path))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _path_findings(repo_root: Path, text: str) -> list[Finding]:
    """Check each independently matched repo-relative ``file:line`` citation."""
    root = repo_root.resolve()
    findings: list[Finding] = []
    for match in _PATH_CITATION_RE.finditer(text):
        citation = match.group("citation")
        path_text, _separator, _line_text = citation.rpartition(":")
        candidate = (root / path_text).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            findings.append(
                Finding(
                    Verdict.MISSING_PATH,
                    citation,
                    f"repo-relative path {path_text!r} does not exist",
                )
            )
            continue

        start = int(match.group("start"))
        end_text = match.group("end")
        end = int(end_text) if end_text is not None else start
        line_count = len(candidate.read_text(errors="replace").splitlines())
        if start < 1 or end < start or end > line_count:
            findings.append(
                Finding(
                    Verdict.BAD_LINE_RANGE,
                    citation,
                    f"cited lines {start}-{end} are outside the file's "
                    f"1-{line_count} range",
                )
            )
    return findings


def _mise_task_names(repo_root: Path) -> set[str]:
    """Read task names from the first column of a bounded ``mise tasks ls``."""
    try:
        proc = subprocess.run(
            ["mise", "tasks", "ls"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=_MISE_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        message = f"mise tasks ls failed: {exc}"
        raise RuntimeError(message) from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "no diagnostic").strip()
        message = f"mise tasks ls exited {proc.returncode}: {detail}"
        raise RuntimeError(message)

    names: set[str] = set()
    for line in proc.stdout.splitlines():
        fields = line.split()
        if not fields:
            continue
        names.add(fields[0])
    return names


def _task_findings(repo_root: Path, text: str) -> list[Finding]:
    """Check each independent ``mise run <name>`` match against live tasks."""
    # .claude/rules/mise-tasks-only.md reserves kb- for sibling-repo tasks.
    matches = [
        match
        for match in _TASK_CITATION_RE.finditer(text)
        if not match.group("name").startswith("kb-")
    ]
    if not matches:
        return []
    known = _mise_task_names(repo_root)
    return [
        Finding(
            Verdict.UNKNOWN_TASK,
            match.group(0),
            f"mise task {match.group('name')!r} is not listed by mise tasks ls",
        )
        for match in matches
        if match.group("name") not in known
    ]


def check(repo_root: Path, text: str) -> list[Finding]:
    """Return only non-OK path/line/task findings for one handoff body."""
    return [*_path_findings(repo_root, text), *_task_findings(repo_root, text)]


def render(findings: list[Finding], *, source: str) -> str:
    """Render the findings list, including an explicit clean result."""
    if not findings:
        return f"handoff-check: OK — {source} citations resolve"
    lines = [f"handoff-check: {len(findings)} finding(s) in {source}"]
    lines.extend(
        f"- {finding.verdict.value}: `{finding.citation}` — {finding.detail}"
        for finding in findings
    )
    return "\n".join(lines)


def main(args: list[str], repo_root: Path) -> int:
    """Check a named handoff, or the newest local handoff when omitted."""
    if len(args) > 1:
        sys.stderr.write("handoff-check: expected at most one handoff path\n")
        return 2

    if args:
        requested = Path(args[0])
        handoff = requested if requested.is_absolute() else repo_root / requested
        source = args[0]
    else:
        handoff = newest_handoff(repo_root)
        if handoff is None:
            sys.stdout.write(
                "handoff-check: no handoff found in .agent/plans/ "
                "(fresh clone or no local handoff)\n"
            )
            return 0
        source = str(handoff.relative_to(repo_root))

    if not handoff.is_file():
        sys.stderr.write(f"handoff-check: handoff not found: {source}\n")
        return 1
    try:
        findings = check(repo_root, handoff.read_text(errors="replace"))
    except RuntimeError as exc:
        sys.stderr.write(f"handoff-check: {exc}\n")
        return 1
    sys.stdout.write(render(findings, source=source) + "\n")
    return 1 if findings else 0
