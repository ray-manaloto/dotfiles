# Copyright (c) 2026 Raymond Manaloto
"""Validate the mechanically checkable citations in a session handoff.

This is intentionally a small, read-only linter.  It checks repo-relative
``file:line`` citations, ``mise run <task>`` names, and PR/issue state claims
("#1449 auto-merge armed") in the handoff and the active section of
``task_plan.md`` against live GitHub facts.  It does not attempt to prove that
a handoff is complete or reconcile claims across handoff versions.

A claim is judged when the check runs, not when it was written: a handoff that
was true at write time fails at resume once GitHub moves.  That is the drift it
exists to catch.  A GitHub lookup that fails is a finding, never a pass.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import pr_facts
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
_LEVEL_TWO_HEADING = re.compile(r"(?m)^##\s")
_FENCE_MARKER = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(`+).*?\1")
_STRIKETHROUGH = re.compile(r"~~.*?~~")
_CLAIM_REFERENCE = re.compile(r"(?<![\w#/])#(?P<n>\d+)\b")
# A number glued to a word ("KB#814", "owner/repo#12") names another repo: it is
# never a reference, but it ends the previous reference's window.
_GLUED_REFERENCE = re.compile(r"(?<=\w)#\d+")
# A reference written after a space-separated KB qualifier ("KB #509",
# "knowledge-base PR #611") names a knowledge-base number.
_FOREIGN_QUALIFIER = re.compile(
    r"\b(?:KB|kb|knowledge-base)[ \t]+(?:(?:PR|pr|issue|Issue)[ \t]+)?$"
)
# Negated or past forms ("was RED", "never MERGED", "auto-merge disarmed") are
# masked before the claim patterns run: they are not present-state claims.
_NEGATED_CLAIM = re.compile(
    r"(?i)\b(?:was|were|not|never|no longer)\s+"
    r"(?:auto-merge(?:\s+armed)?|OPEN|MERGED|CLOSED|RED|green|landed)\b"
    r"|\bauto-merge\s+(?:disarmed|disabled|off|cancelled|canceled)\b"
)
# No NEW lookup starts after this many seconds; a lookup already in flight can
# add up to 2 x pr_facts.GH_TIMEOUT (worst case ~540 s in total).
CLAIMS_DEADLINE_S = 300.0
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
# inject-plan.sh's `tr -d '\r\n[:space:]'` (C locale), as the plugin's own
# inject-plan.py spells it (`_WS_BYTES`, plus NUL). NOT Python's str.split():
# that also drops U+001C-U+001F, so a digest followed by one would pass here
# while the hook reports the plan tampered.
_NATIVE_WS = frozenset(b" \t\n\r\x0b\x0c\x00")


def _strip_native_ws(data: bytes) -> bytes:
    """Drop exactly the bytes the plugin's hook drops before comparing digests."""
    return bytes(b for b in data if b not in _NATIVE_WS)


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
    PR_CLAIM_MISMATCH = "pr_claim_mismatch"
    PR_CLAIM_UNVERIFIABLE = "pr_claim_unverifiable"


@dataclass(frozen=True)
class Finding:
    """One stale citation and the reason it failed validation."""

    verdict: Verdict
    citation: str
    detail: str


def handoff_key(path: Path) -> tuple[str, int] | None:
    """Return a handoff's (date, letter order) identity; None for any other name.

    Only the basename counts, so ``session-2026-09-29c.md`` and
    ``session-2026-09-29-c.md`` name the same handoff wherever they live.
    """
    match = _HANDOFF_RE.fullmatch(path.name)
    if match is None:
        return None
    suffix = match.group("suffix")
    suffix_order = 0 if suffix is None else ord(suffix.lower()) - ord("a") + 1
    return match.group("date"), suffix_order


def newest_handoff(repo_root: Path, *, exclude: Path | None = None) -> Path | None:
    """Return the newest local handoff by ISO date and optional letter suffix.

    ``exclude`` is skipped by :func:`handoff_key`, not by path — the handoff
    being written is not "the previous handoff", however its name is spelled.
    It may be a bare filename or any path; a basename that is not a handoff
    name raises ValueError rather than silently excluding nothing.
    """
    excluded = None
    if exclude is not None:
        excluded = handoff_key(exclude)
        if excluded is None:
            message = f"not a session-YYYY-MM-DD[-x].md handoff name: {exclude}"
            raise ValueError(message)
    plans = repo_root / ".agent" / "plans"
    if not plans.is_dir():
        return None

    candidates: list[tuple[tuple[str, int], Path]] = []
    for path in plans.glob("session-*.md"):
        key = handoff_key(path)
        if key is None or key == excluded:
            continue
        candidates.append((key, path))
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


def _visible_lines(text: str) -> tuple[list[str], str | None]:
    """Blank fenced code blocks; return the lines and any unclosed fence token."""
    visible: list[str] = []
    fence: tuple[str, int] | None = None
    fence_citation = ""
    for line in text.splitlines(keepends=True):
        marker = _FENCE_MARKER.match(line)
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
    return visible, (fence_citation if fence is not None else None)


def _task_carrier_findings(text: str) -> list[Finding]:
    """Reject the first handoff line that attempts to carry the next task."""
    visible, unclosed_fence = _visible_lines(text)
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
    if unclosed_fence is not None:
        findings.append(
            Finding(
                Verdict.UNCLOSED_FENCE,
                unclosed_fence,
                "fenced code block reaches end of file without a closing fence",
            )
        )
    return findings


def active_phase(text: str) -> str | None:
    """Return the last level-two heading containing ``NEXT SESSION``."""
    matches = list(_ACTIVE_HEADING.finditer(text))
    return matches[-1].group("heading").strip() if matches else None


def _active_section_span(plan_text: str) -> tuple[int, str] | None:
    """Return (lines before the section, section text) for the active phase."""
    matches = list(_ACTIVE_HEADING.finditer(plan_text))
    if not matches:
        return None
    start = matches[-1].start()
    heading_end = plan_text.find("\n", start)
    body_start = len(plan_text) if heading_end == -1 else heading_end + 1
    following = _LEVEL_TWO_HEADING.search(plan_text, body_start)
    end = len(plan_text) if following is None else following.start()
    return plan_text.count("\n", 0, start), plan_text[start:end]


def active_section(plan_text: str) -> str | None:
    """Return the active phase from its heading to the next ``##`` heading or EOF.

    ``###`` headings stay inside the section; None when no heading is active.
    """
    span = _active_section_span(plan_text)
    return None if span is None else span[1]


class ClaimWord(Enum):
    """The PR/issue state words a handoff or plan may assert."""

    OPEN = "OPEN"
    MERGED = "MERGED"
    CLOSED = "CLOSED"
    RED = "RED"
    GREEN = "green"
    LANDED = "landed"
    AUTO_MERGE_ARMED = "auto-merge armed"
    AUTO_MERGE = "auto-merge"


# Applied in order; each hit is masked before the next pattern runs, so
# "auto-merge armed" never also yields a bare "auto-merge".
_CLAIM_PATTERNS: tuple[tuple[re.Pattern[str], ClaimWord], ...] = (
    (
        re.compile(r"(?i)\b(?:auto-merge\s+armed|armed\s+auto-merge)\b"),
        ClaimWord.AUTO_MERGE_ARMED,
    ),
    (re.compile(r"(?i)\bauto-merge\b(?![\w-])"), ClaimWord.AUTO_MERGE),
    (re.compile(r"\bOPEN\b"), ClaimWord.OPEN),
    (re.compile(r"\bMERGED\b"), ClaimWord.MERGED),
    (re.compile(r"\bCLOSED\b"), ClaimWord.CLOSED),
    (re.compile(r"\bRED\b"), ClaimWord.RED),
    (re.compile(r"(?i)\blanded\b"), ClaimWord.LANDED),
    (re.compile(r"(?i)\bgreen\b"), ClaimWord.GREEN),
)


@dataclass(frozen=True)
class Claim:
    """One state word asserted about one number at one source line."""

    number: int
    word: ClaimWord
    source: str
    line: int


@dataclass(frozen=True)
class ClaimTally:
    """How many claims were judged, and which were skipped as not applicable."""

    checked: int
    skipped: tuple[Claim, ...]  # claim_holds(...) is None: a PR-only word on an ISSUE


def _blank(match: re.Match[str]) -> str:
    """Replace a span with spaces so later patterns cannot see it."""
    return " " * len(match.group(0))


def _window_words(window: str) -> list[ClaimWord]:
    """Return each distinct claim word in one reference window."""
    window = _NEGATED_CLAIM.sub(_blank, window)
    words: list[ClaimWord] = []
    for pattern, word in _CLAIM_PATTERNS:
        window, hits = pattern.subn(_blank, window)
        if hits and word not in words:
            words.append(word)
    return words


def extract_claims(text: str, *, source: str, line_offset: int = 0) -> list[Claim]:
    """Extract state claims from visible text: no fences, code spans, or strikethrough.

    A reference is ``#<digits>`` not preceded by a word character, ``#`` or
    ``/``.  Its window is the rest of its line up to the next reference, or up
    to the next number glued to a word (``KB#814``, ``owner/repo#12``), which
    names another repo and so yields no claim itself.  ``/#N`` (the second
    number of ``#A/#B``) neither is a reference nor ends the window, so
    ``#1454/#1453 MERGED`` claims MERGED for #1454 only.

    A reference after a space-separated KB qualifier (``KB #509``,
    ``knowledge-base PR #611``) still ends the previous window but yields no
    claim.  Only the KB spellings are recognised: any other repo name followed
    by a space (``owner/repo #12``, ``other-repo #5``) is still read as a
    dotfiles number.  Negated or past forms (``was RED``, ``never MERGED``,
    ``auto-merge disarmed``) are not claims.
    """
    visible, _unclosed = _visible_lines(text)
    claims: list[Claim] = []
    for index, raw in enumerate(visible):
        line = _STRIKETHROUGH.sub(_blank, _INLINE_CODE.sub(_blank, raw.rstrip("\n")))
        references = list(_CLAIM_REFERENCE.finditer(line))
        boundaries = sorted(
            [
                *(reference.start() for reference in references),
                *(glued.start() for glued in _GLUED_REFERENCE.finditer(line)),
            ]
        )
        for reference in references:
            if _FOREIGN_QUALIFIER.search(line, 0, reference.start()):
                continue
            window_end = next(
                (start for start in boundaries if start > reference.start()),
                len(line),
            )
            claims.extend(
                Claim(int(reference.group("n")), word, source, line_offset + index + 1)
                for word in _window_words(line[reference.end() : window_end])
            )
    return claims


def claim_holds(word: ClaimWord, facts: pr_facts.PrFacts) -> bool | None:
    """Judge one claim against live facts; None when the word does not apply.

    ``landed`` checks only that the PR is MERGED: the post-merge ``mise run
    land`` validation is not recorded on GitHub, so this is a necessary
    condition, not proof of a land.  ``autoMergeRequest`` persists after a
    merge, so both auto-merge words also require the PR to be OPEN, and the
    bare word (which predicts a merge) also requires no failing check.
    """
    if facts.kind is pr_facts.ItemKind.ISSUE:
        if word in {ClaimWord.OPEN, ClaimWord.CLOSED}:
            return facts.state == word.value
        return None
    checks = facts.checks
    armed = facts.state == "OPEN" and facts.auto_merge
    verdicts = {
        ClaimWord.OPEN: facts.state == "OPEN",
        ClaimWord.MERGED: facts.state == "MERGED",
        ClaimWord.CLOSED: facts.state == "CLOSED",
        ClaimWord.LANDED: facts.state == "MERGED",
        ClaimWord.AUTO_MERGE_ARMED: armed,
        ClaimWord.AUTO_MERGE: armed and checks.failing == 0,
        ClaimWord.RED: checks.failing >= 1,
        ClaimWord.GREEN: (
            checks.total >= 1 and checks.failing == 0 and checks.pending == 0
        ),
    }
    return verdicts[word]


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
            raw = (repo_root / state.attestation).read_bytes()
            attested = _strip_native_ws(raw).decode(errors="replace")
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


def _describe(facts: pr_facts.PrFacts) -> str:
    """Render the live facts a mismatch is judged against."""
    if facts.kind is pr_facts.ItemKind.ISSUE:
        return f"GitHub reports issue #{facts.number} state={facts.state}"
    checks = facts.checks
    return (
        f"GitHub reports PR #{facts.number} state={facts.state} "
        f"auto-merge={'yes' if facts.auto_merge else 'no'} checks "
        f"fail:{checks.failing} pending:{checks.pending} pass:{checks.passed}"
    )


def _plan_claims(repo_root: Path) -> list[Claim]:
    """Claims in the active section of task_plan.md, with file line numbers."""
    plan_path = repo_root / "task_plan.md"
    if not plan_path.is_file():
        return []
    span = _active_section_span(plan_path.read_text(errors="replace"))
    if span is None:
        return []
    line_offset, section = span
    return extract_claims(section, source="task_plan.md", line_offset=line_offset)


def _claim_findings(
    repo_root: Path,
    claims: list[Claim],
    facts: Callable[[Path, int], pr_facts.PrFacts | str],
    deadline_s: float,
) -> tuple[list[Finding], ClaimTally]:
    """Judge every claim, fetching each number once within one total deadline."""
    per_number: dict[int, int] = {}
    for claim in claims:
        per_number[claim.number] = per_number.get(claim.number, 0) + 1

    started = time.monotonic()
    answers: dict[int, pr_facts.PrFacts | str] = {}
    findings: list[Finding] = []
    checked = 0
    skipped: list[Claim] = []
    for claim in claims:
        if claim.number not in answers:
            if time.monotonic() - started >= deadline_s:
                answers[claim.number] = (
                    f"claim-check deadline ({deadline_s:g} s) expired before lookup"
                )
                findings.append(
                    Finding(
                        Verdict.PR_CLAIM_UNVERIFIABLE,
                        f"#{claim.number}",
                        str(answers[claim.number]),
                    )
                )
                continue
            answers[claim.number] = facts(repo_root, claim.number)
            answer = answers[claim.number]
            if isinstance(answer, str):
                findings.append(
                    Finding(
                        Verdict.PR_CLAIM_UNVERIFIABLE,
                        f"#{claim.number}",
                        f"GitHub lookup failed ({answer}) — "
                        f"{per_number[claim.number]} claim(s) unchecked; "
                        "a failed lookup is never a pass",
                    )
                )
        answer = answers[claim.number]
        if isinstance(answer, str):
            continue
        holds = claim_holds(claim.word, answer)
        if holds is None:
            skipped.append(claim)
            continue
        checked += 1
        if not holds:
            findings.append(
                Finding(
                    Verdict.PR_CLAIM_MISMATCH,
                    f"#{claim.number} {claim.word.value} ({claim.source}:{claim.line})",
                    _describe(answer),
                )
            )
    return findings, ClaimTally(checked, tuple(skipped))


def check_with_claims(
    repo_root: Path,
    text: str,
    *,
    show: Callable[[Path], Attestation] = show_attestation,
    facts: Callable[[Path, int], pr_facts.PrFacts | str] | None = None,
    source: str = "handoff",
) -> tuple[list[Finding], ClaimTally]:
    """Return every non-OK finding plus the tally of judged and skipped claims.

    A skipped claim (a PR-only word on an issue) never fails the check; it is
    counted and listed so it cannot pass invisibly.

    ``CLAIMS_DEADLINE_S`` is read at call time: no NEW lookup starts after it
    expires, but a lookup in flight can add up to 2 x ``pr_facts.GH_TIMEOUT``
    (worst case ~540 s), since each ``gh`` call is bounded only by that timeout.
    """
    findings = [
        *_task_carrier_findings(text),
        *_plan_findings(repo_root, show),
        *_path_findings(repo_root, text),
        *_task_findings(repo_root, text),
    ]
    claims = [
        *extract_claims(text, source=source),
        *_plan_claims(repo_root),
    ]
    claim_findings, tally = _claim_findings(
        repo_root,
        claims,
        pr_facts.fetch_facts if facts is None else facts,
        CLAIMS_DEADLINE_S,
    )
    return [*findings, *claim_findings], tally


def check(
    repo_root: Path,
    text: str,
    *,
    show: Callable[[Path], Attestation] = show_attestation,
    facts: Callable[[Path, int], pr_facts.PrFacts | str] | None = None,
    source: str = "handoff",
) -> list[Finding]:
    """Return only non-OK citation, task-carrier, active-plan, and claim findings."""
    return check_with_claims(repo_root, text, show=show, facts=facts, source=source)[0]


def render(
    findings: list[Finding], *, source: str, tally: ClaimTally | None = None
) -> str:
    """Render the findings list, including an explicit clean result.

    Every skipped claim gets an info line in both forms; skips never fail.
    """
    checked = 0 if tally is None else tally.checked
    skipped = () if tally is None else tally.skipped
    if findings:
        lines = [f"handoff-check: {len(findings)} finding(s) in {source}"]
        lines.extend(
            f"- {finding.verdict.value}: `{finding.citation}` — {finding.detail}"
            for finding in findings
        )
    else:
        ok = (
            f"handoff-check: OK — {source} citations resolve; "
            f"{checked} PR claim(s) match GitHub"
        )
        if skipped:
            ok += f"; {len(skipped)} skipped (PR-only word on an issue)"
        lines = [ok]
    lines.extend(
        f"handoff-check: info — skipped #{claim.number} {claim.word.value} "
        f"({claim.source}:{claim.line}): #{claim.number} is an issue, not a PR"
        for claim in skipped
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
        findings, tally = check_with_claims(
            repo_root, handoff.read_text(errors="replace"), source=source
        )
    except (RuntimeError, OSError) as exc:
        sys.stderr.write(f"handoff-check: {exc}\n")
        return 1
    rendered = render(findings, source=source, tally=tally)
    if not (repo_root / "task_plan.md").is_file():
        rendered += (
            "\nhandoff-check: info — task_plan.md absent (fresh clone); "
            "active-plan checks skipped"
        )
    sys.stdout.write(rendered + "\n")
    return 1 if findings else 0
