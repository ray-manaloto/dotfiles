# Copyright (c) 2026 Raymond Manaloto
"""Validate the mechanically checkable citations in a session handoff.

This is intentionally a small, read-only linter.  It checks repo-relative
``file:line`` citations and ``mise run <task>`` names; it does not attempt to
prove that a handoff is complete or reconcile claims across handoff versions.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.plan_attest import PluginNotInstalledError, resolve_attest_script

if TYPE_CHECKING:
    from collections.abc import Callable

_MISE_TIMEOUT = 30
_HANDOFF_RE = re.compile(
    r"^session-(?P<date>\d{4}-\d{2}-\d{2})(?:-?(?P<suffix>[A-Za-z]))?\.md$"
)
_PATH_CITATION_RE = re.compile(
    r"(?<![\w./:-])(?P<citation>(?:Makefile|Dockerfile|"
    r"[\w./-]*/(?:Makefile|Dockerfile)|"
    r"[\w./-]+\.[A-Za-z]\w*):(?P<start>\d+)"
    r"(?:-(?P<end>\d+))?)(?![\w-])"
)
_TASK_CITATION_RE = re.compile(
    r"\bmise[ \t]+run[ \t]+(?P<name>[A-Za-z0-9][\w-]*)(?![\w:-])"
)
_TASK_CARRIER_HEADING = re.compile(
    r"(?im)^#{1,6}[ \t]+(?:[^\w\s]+[ \t]*)*next[ -]task\b"
    r"(?:[ \t]*:)?(?:[ \t]+.*)?$"
)
_TASK_CARRIER_LINE = re.compile(r"(?im)^[ \t]*(?:next:|next[ -]task[ \t]*:)[ \t]*.*$")
_ACTIVE_HEADING = re.compile(r"(?im)^##\s+(?P<heading>[^\n]*NEXT SESSION[^\n]*)\s*$")
# planning-with-files' own attestation replaced the retired tracked pointer
# (Ray, 2026-09-28c). WHICH plan and attestation file are live is the plugin's
# decision (--target, $PLAN_ID, .planning/.active_plan, newest slug, then the
# root plan), so this gate asks the plugin's own `attest-plan.sh --show` rather
# than re-deriving that order: the answer is then the plan the hook injects.
# The root plan is this repo's sole task authority, so a selection that resolves
# anywhere else is itself a finding. The digest is read from the attestation
# FILE and whitespace-stripped whole, exactly as the plugin's inject-plan.sh
# compares it — a matching first line with trailing junk is still tampered.
_SHOW_PLAN = re.compile(r"(?m)^Plan: (?P<value>.+)$")
_SHOW_FILE = re.compile(r"(?m)^Attestation: (?P<value>.+)$")


@dataclass(frozen=True)
class Attestation:
    """What the plugin reports: the resolved plan and its attestation file."""

    plan: str | None
    attestation: str | None
    error: str | None = None


def parse_show(output: str) -> Attestation:
    """Parse ``attest-plan.sh --show``; missing fields mean "not attested"."""
    plan = _SHOW_PLAN.search(output)
    attestation = _SHOW_FILE.search(output)
    return Attestation(
        plan.group("value").strip() if plan else None,
        attestation.group("value").strip() if attestation else None,
    )


def show_attestation(repo_root: Path) -> Attestation:
    """Ask the installed pwf plugin which plan is attested, and with what digest."""
    try:
        script = resolve_attest_script(Path.home())
    except PluginNotInstalledError as exc:
        return Attestation(None, None, str(exc))
    try:
        completed = subprocess.run(
            ["sh", str(script), "--show"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=_MISE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Attestation(None, None, f"attest-plan.sh --show failed: {exc}")
    return parse_show(completed.stdout)


class Verdict(Enum):
    """Every finding this scoped validator can emit."""

    OK = "ok"
    MISSING_PATH = "missing_path"
    BAD_LINE_RANGE = "bad_line_range"
    UNKNOWN_TASK = "unknown_task"
    FORBIDDEN_TASK_CARRIER = "forbidden_task_carrier"
    UNCLOSED_FENCE = "unclosed_fence"
    MISSING_ACTIVE_PLAN = "missing_active_plan"
    UNATTESTED_PLAN = "unattested_plan"


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


def _task_carrier_findings(text: str) -> list[Finding]:
    """Reject the first handoff line that attempts to carry the next task."""
    visible: list[str] = []
    fence: tuple[str, int] | None = None
    fence_citation = ""
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s*(?P<fence>`{3,}|~{3,})", line)
        if marker is not None:
            token = marker.group("fence")
            if fence is None:
                fence = (token[0], len(token))
                fence_citation = token
            elif token[0] == fence[0] and len(token) >= fence[1]:
                fence = None
            visible.append("\n" if line.endswith("\n") else "")
        elif fence is None:
            visible.append(line)
        else:
            visible.append("\n" if line.endswith("\n") else "")
    check_text = "".join(visible)
    matches = [
        *_TASK_CARRIER_HEADING.finditer(check_text),
        *_TASK_CARRIER_LINE.finditer(check_text),
    ]
    findings: list[Finding] = []
    if matches:
        match = min(matches, key=lambda item: item.start())
        findings.append(
            Finding(
                Verdict.FORBIDDEN_TASK_CARRIER,
                match.group(0).strip(),
                "task_plan.md is the only task carrier; handoffs carry state and "
                "evidence",
            )
        )
    if fence is not None:
        findings.append(
            Finding(
                Verdict.UNCLOSED_FENCE,
                fence_citation,
                "fenced code block reaches end of file without a closing fence",
            )
        )
    return findings


def active_phase(text: str) -> str | None:
    """Return the last level-two heading containing ``NEXT SESSION``."""
    matches = list(_ACTIVE_HEADING.finditer(text))
    return matches[-1].group("heading").strip() if matches else None


def _plan_findings(
    repo_root: Path, show: Callable[[Path], Attestation]
) -> list[Finding]:
    """Require an active plan phase and a current planning-with-files attestation."""
    plan_path = repo_root / "task_plan.md"
    if not plan_path.is_file():
        return []
    plan_bytes = plan_path.read_bytes()
    if active_phase(plan_bytes.decode(errors="replace")) is None:
        return [
            Finding(
                Verdict.MISSING_ACTIVE_PLAN,
                "task_plan.md",
                "no ## heading contains NEXT SESSION",
            )
        ]

    state = show(repo_root)
    if state.error is not None:
        detail = f"cannot read the planning-with-files attestation: {state.error}"
    elif state.plan is None or state.attestation is None:
        detail = "the active plan has no attestation"
    elif (repo_root / state.plan).resolve() != plan_path.resolve():
        detail = (
            f"planning-with-files resolves {state.plan}, not the root task_plan.md "
            "that is the task authority; clear the slug selection"
        )
    else:
        try:
            attested = "".join((repo_root / state.attestation).read_text().split())
        except OSError as exc:
            attested = None
            detail = f"{state.attestation} is unreadable: {exc}"
        else:
            detail = "task_plan.md does not match its attestation (edited after it)"
        if attested == hashlib.sha256(plan_bytes).hexdigest():
            return []
    return [
        Finding(
            Verdict.UNATTESTED_PLAN,
            state.plan or "task_plan.md",
            f"{detail}; run `mise run plan-attest` once no writer is live",
        )
    ]


def check(
    repo_root: Path,
    text: str,
    *,
    show: Callable[[Path], Attestation] = show_attestation,
) -> list[Finding]:
    """Return only non-OK citation, task-carrier, and active-plan findings."""
    return [
        *_task_carrier_findings(text),
        *_plan_findings(repo_root, show),
        *_path_findings(repo_root, text),
        *_task_findings(repo_root, text),
    ]


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
    except (RuntimeError, OSError) as exc:
        sys.stderr.write(f"handoff-check: {exc}\n")
        return 1
    rendered = render(findings, source=source)
    if not (repo_root / "task_plan.md").is_file():
        rendered += (
            "\nhandoff-check: info — task_plan.md absent (fresh clone); "
            "active-plan checks skipped"
        )
    sys.stdout.write(rendered + "\n")
    return 1 if findings else 0
