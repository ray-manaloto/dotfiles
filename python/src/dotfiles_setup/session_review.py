# Copyright (c) 2026 Raymond Manaloto
"""Find what a session did BY HAND that should have been code (#654).

The meta-layer over #650-#653: all four of those were found by performing this
review manually on 2026-08-08, which is itself the argument for automating it.

Two lanes, and they find **disjoint** things — running one is a partial answer,
which is why the default runs both:

**Lane 1 — the transcript mine.** :mod:`dotfiles_setup.command_audit` already
recovers every Bash call from this project's transcripts and classifies it. It
asks *"should this become a **guard redirect**?"*; this module asks *"should
this become a **skill**?"* — the same corpus, a different verdict, so the miner
is reused rather than re-written. The ranking differs on purpose: the audit
ranks by raw frequency, while a skill candidate is ranked by **how many
distinct sessions** the shape appears in. A shape run thirty times in one
session is one task someone was grinding through; a shape that reappears across
three sessions is a *workflow*, and only the second kind keeps costing.

**Lane 2 — the narrative pass** over ``.agent/notepad.md``, the session
handoffs, and the tracked goal history, for **reasoning sinks that leave no
repeated command**. This lane is
not optional. The best 2026-08-08 find (#650, regenerating the image locks) was
~15 turns of reading CI config, transcribing a recipe, running it on the wrong
platform, measuring the damage, reverting and re-running in a container —
**there was no repeated one-liner to count**. Frequency is a proxy for cost and
a poor one; the expensive thing was reasoning.

The inverse holds too, which is why lane 1 is not optional either: an agent
writing its own notepad does not reliably remember every one-off it ran, and
the transcript does.

Lane 2 is deliberately a **surfacer, not a judge**. It matches the phrases this
repo's own notes use when recording a manual slog ("by hand", "~N turns",
"re-derived", "cost a cycle") and hands the passages to the reader. A regex
cannot tell an expensive slog from a sentence describing one, and pretending
otherwise would produce a confident list of non-candidates.

⚠️ **The honest test, inherited from #607/#608 (*"prose was not the lever"*):
a candidate that cannot name a concrete session cost it would have avoided is
not a candidate.** :func:`render_report` puts that field in the template so it
has to be filled in rather than assumed.

Deviation from the issue's stated shape, recorded here rather than silently:
it specified ``--since <ref>``, which cannot work for lane 2 — ``.agent/`` is
**gitignored**, so no git ref can bound a corpus git has never tracked. Lane 1
is bounded by ``--sessions N`` instead (the miner's own window), and lane 2 by
which files you point it at.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import command_audit, session_ledger

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

logger = logging.getLogger(__name__)
_MAX_LOGGED_OMISSIONS = 20

#: Classes worth proposing a skill for. ``mise`` and ``diagnostic`` commands are
#: already canonical or already cheap; ``blocked`` never ran and ``pre_rule``
#: has a task today, so neither is evidence of manual work.
CANDIDATE_KINDS = frozenset({"one_off", "bypass"})

#: A shape seen fewer times than this is noise — #266 records that the raw
#: one-off list is known-noisy, and this module inherits that caveat.
MIN_OCCURRENCES = 3
MAX_REVIEW_ITERATIONS = 5

#: Shell CONSTRUCTS, not commands. `command_audit`'s grouping keys off the first
#: two words, which is right for a guard audit (it asks what BINARY ran) and
#: wrong here: a loop or a redirect heads as `while [` or `-c <`, which names no
#: workflow at all. Measured on this project 2026-08-08 — these shapes took 5 of
#: the top 8 rows and none was a candidate.
_SHELL_CONSTRUCTS = frozenset(
    {
        "while",
        "for",
        "if",
        "case",
        "{",
        "(",
        "-c",
        "<<",
        "python3",
        "bash",
        "sh",
        "export",
    }
)

#: Harness mechanics rather than project work: scratchpad setup and the in-turn
#: poll loop `.claude/rules/long-running-command-hangs.md` rule 2 REQUIRES. They
#: recur in every session by construction, so ranking them would put the thing
#: an agent is instructed to do at the top of a list of things it should stop
#: doing.
_HARNESS_SHAPES = frozenset({"mkdir -p", "sleep", "rm -f", "cat >", "echo"})

#: A "shape" longer than this is a pasted literal (an `export VAR=/very/long/…`),
#: not a shape. Grouping on it produces one row per invocation.
MAX_SHAPE_CHARS = 40

#: The notepad is append-only ACROSS sessions — 2,400+ lines here — so scanning
#: all of it answers "what has this repo ever done by hand", not "what did THIS
#: session". A tail is a real bound and the report states it, per
#: `.claude/rules/probes-need-a-control-arm.md` rule 3.
DEFAULT_TAIL_LINES = 400

#: Where a session records its own manual work and goal changes. The tracked
#: goal history makes accepted pivots visible to the same review without
#: relying on a caller to opt it in.
DEFAULT_NARRATIVE_PATHS: tuple[str, ...] = (
    ".agent/notepad.md",
    ".agent/plans/session-*.md",
    "docs/agents/goal-history.md",
)
GOAL_HISTORY_PATH = "docs/agents/goal-history.md"
GOAL_HISTORY_FIELDS: tuple[str, ...] = (
    "Iteration ID",
    "Prior goal digest",
    "Current goal digest",
    "Changed requirement",
    "Reason",
    "Evidence",
    "Affected tickets",
    "Disposition",
    "Topology and ownership",
)
_GOAL_HISTORY_ENTRY = re.compile(r"(?m)^## (?P<title>\d{4}-\d{2}-\d{2} — [^\n]+)\n")

#: Phrases this repo's notes actually use when recording a slog, each paired
#: with what it usually indicates. Matched case-insensitively.
NARRATIVE_MARKERS: tuple[tuple[str, str], ...] = (
    (r"by hand|hand-rolled|hand-transcrib|hand-check", "work done manually"),
    (r"re-deriv|rederiv|transcrib\w* the recipe", "knowledge rebuilt from scratch"),
    (r"~?\d+\s+turns", "a multi-turn reasoning sink"),
    (r"cost a cycle|cost a diagnosis|diagnosis cycle", "a repeated diagnosis"),
    (r"manually|one at a time|one by one", "an unautomated repetition"),
    (r"had to be re-run|re-ran it|ran it again", "a retry loop"),
)

#: Phrasings that mention manual work in order to FORBID it. A handoff saying
#: "do NOT re-derive this" is an instruction, not a record of a slog — measured
#: on the first live run, these were 9 of 17 lane-2 rows and none was a
#: candidate. Suppression is checked before the markers, so a line carrying both
#: reads as the instruction it is.
NARRATIVE_SUPPRESSORS: tuple[str, ...] = (
    r"do\s*n[o']?t\s+re-?deriv",
    r"no need to re-?deriv",
    r"rather than re-?deriv",
    r"replaces? (?:the )?hand-rolled",
    r"over hand-rolled",
    r"instead of (?:a )?hand-rolled",
)

_COMPILED_SUPPRESSORS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in NARRATIVE_SUPPRESSORS
)

#: How many session handoffs to read. Handoffs are PER-SESSION and this repo has
#: 40+ of them, so the glob's natural behaviour is to scan the archive and
#: answer "what has this repo ever done by hand". Newest-first, one by default.
DEFAULT_HANDOFF_LIMIT = 1

_COMPILED_MARKERS = tuple(
    (re.compile(pattern, re.IGNORECASE), meaning)
    for pattern, meaning in NARRATIVE_MARKERS
)


@dataclass(frozen=True)
class NarrativeScope:
    """What lane 2 reads, as one value.

    Grouped rather than passed as three parameters because they are always
    chosen together — widening the corpus without widening the tail answers a
    question nobody asked.
    """

    patterns: Sequence[str] = DEFAULT_NARRATIVE_PATHS
    tail_lines: int | None = DEFAULT_TAIL_LINES
    glob_limit: int = DEFAULT_HANDOFF_LIMIT


@dataclass(frozen=True)
class LaneChoice:
    """Which lanes to run. One value because they are one decision.

    Both flags true is refused rather than resolved: the lanes are disjoint, so
    any interpretation would be a guess about intent and guessing wrong loses a
    whole class of finding.
    """

    transcript_only: bool = False
    narrative_only: bool = False
    requirements_only: bool = False
    source_repo_root: Path | None = None
    dispositions: Path | None = None
    semantic_dispositions: Path | None = None
    session_id: str | None = None
    codex_session_id: str | None = None
    receipt_run_id: str = ""
    max_iterations: int = 1
    rebuild_cache: bool = False


#: Defaults as module-level singletons, so the entry point can declare them
#: without constructing a value in its own signature.
BOTH_LANES = LaneChoice()
DEFAULT_NARRATIVE_SCOPE = NarrativeScope()


@dataclass(frozen=True)
class ShapeCandidate:
    """One command shape that recurred, and how widely."""

    shape: str
    occurrences: int
    sessions: int
    example: str

    @property
    def cross_session(self) -> bool:
        """True when the shape outlived a single session — the durable signal."""
        return self.sessions > 1

    def render(self) -> str:
        """One table row: sessions first, because that is the ranking key."""
        signal = "workflow" if self.cross_session else "one grind"
        example = command_audit.truncate(self.example, 60)
        return (
            f"| {self.sessions} | {self.occurrences} | {signal} | "
            f"`{self.shape}` | `{example}` |"
        )


@dataclass(frozen=True)
class NarrativeHit:
    """A passage in a session's own notes that reads like manual work."""

    path: str
    line_number: int
    meaning: str
    line: str

    def render(self) -> str:
        """One table row: a clickable ``path:line``, the reading, the passage."""
        return (
            f"| `{self.path}:{self.line_number}` | {self.meaning} | "
            f"{command_audit.truncate(self.line, 90)} |"
        )


def is_reportable_shape(shape: str) -> bool:
    """Does this grouping key name a workflow a skill could replace?

    Three rejections, each measured on the first live run rather than guessed:
    a shell construct (`while [`, `for i`) names the syntax and not the work; a
    harness mechanic (`mkdir -p` the scratchpad, the mandated poll loop) recurs
    by construction in every session; and an over-long key is a pasted literal
    that groups with nothing.
    """
    head = shape.split(" ", 1)[0]
    return (
        len(shape) <= MAX_SHAPE_CHARS
        and head not in _SHELL_CONSTRUCTS
        and shape not in _HARNESS_SHAPES
        # Anywhere in the shape, not just the head: `group_key` keeps two words,
        # so an assignment lands in the SECOND one (`export FOO=/long/path`) and
        # a head-only check waves it through.
        and "=" not in shape
    )


def shape_candidates(
    commands: Iterable[command_audit.BashCommand],
    *,
    kinds: frozenset[str] = CANDIDATE_KINDS,
    min_occurrences: int = MIN_OCCURRENCES,
) -> list[ShapeCandidate]:
    """Recurring non-canonical command shapes, ranked by session spread.

    Sessions first, then occurrences: a shape confined to one session may be a
    task someone was grinding through once, while a shape that comes back is a
    workflow, and only the second keeps costing. Both numbers are reported so
    the reader can disagree with the ranking.
    """
    occurrences: Counter[str] = Counter()
    sessions: defaultdict[str, set[str]] = defaultdict(set)
    examples: dict[str, str] = {}
    for bc in commands:
        if command_audit.classify(bc) not in kinds:
            continue
        shape = command_audit.group_key(bc.command)
        if not is_reportable_shape(shape):
            continue
        occurrences[shape] += 1
        sessions[shape].add(bc.session)
        examples.setdefault(shape, bc.command)
    candidates = [
        ShapeCandidate(shape, count, len(sessions[shape]), examples[shape])
        for shape, count in occurrences.items()
        if count >= min_occurrences
    ]
    candidates.sort(key=lambda c: (c.sessions, c.occurrences), reverse=True)
    return candidates


def narrative_paths(
    repo_root: Path,
    patterns: Sequence[str] = DEFAULT_NARRATIVE_PATHS,
    *,
    glob_limit: int = DEFAULT_HANDOFF_LIMIT,
) -> list[Path]:
    """Resolve the narrative corpus, newest-first for globs.

    A glob is bounded because it resolves to the handoff ARCHIVE: this repo has
    40+ ``session-*.md`` files, and reading all of them answers what the repo
    has ever done by hand rather than what this session did. A literal path is
    never bounded — the notepad and tracked goal history are files you always
    want. Their content is still bounded by :func:`tail_text`.
    """
    found: list[Path] = []
    for pattern in patterns:
        if any(ch in pattern for ch in "*?["):
            matches = sorted(
                repo_root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
            )
            found.extend(matches[:glob_limit] if glob_limit else matches)
        elif (repo_root / pattern).is_file():
            found.append(repo_root / pattern)
    return found


def narrative_hits(text: str, path: str) -> list[NarrativeHit]:
    """Passages that read like recorded manual work, one hit per line at most.

    One hit per line even when several markers fire: the unit a reader acts on
    is the passage, and three rows pointing at one sentence would inflate the
    apparent evidence for a candidate rather than describe it.
    """
    hits: list[NarrativeHit] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if any(pattern.search(line) for pattern in _COMPILED_SUPPRESSORS):
            continue
        for pattern, meaning in _COMPILED_MARKERS:
            if pattern.search(line):
                hits.append(NarrativeHit(path, number, meaning, line.strip()))
                break
    return hits


def tail_text(text: str, tail_lines: int | None) -> tuple[str, int]:
    """The last ``tail_lines`` lines, plus the line number they start at.

    The offset is returned rather than discarded so a hit still points at its
    real line — a report whose line numbers are relative to a window is a
    citation nobody can open.
    """
    lines = text.splitlines()
    if tail_lines is None or len(lines) <= tail_lines:
        return text, 0
    return "\n".join(lines[-tail_lines:]), len(lines) - tail_lines


def _field_value(block: str, field: str, pattern: str) -> str | None:
    match = re.search(rf"(?m)^- \*\*{re.escape(field)}:\*\* {pattern}$", block)
    return match.group(1) if match else None


def _goal_text(block: str, title: str) -> tuple[str, list[str]]:
    goal_start = block.find("### Current goal\n")
    workflow_start = block.find("### Current workflow\n")
    if goal_start < 0 or workflow_start <= goal_start:
        return "", [f"{title}: missing ordered current goal/workflow sections"]
    goal_lines = (
        block[goal_start + len("### Current goal\n") : workflow_start]
        .strip()
        .splitlines()
    )
    quoted = [line[2:] for line in goal_lines if line.startswith("> ")]
    if not quoted or len(quoted) != len([line for line in goal_lines if line]):
        return "", [f"{title}: current goal must be a Markdown quote"]
    return "\n".join(quoted), []


def _iteration_errors(
    block: str,
    title: str,
    index: int,
    prior_current_digest: str | None,
    seen_ids: set[str],
) -> tuple[list[str], str | None]:
    errors = [
        f"{title}: {kind} {field}"
        for field in GOAL_HISTORY_FIELDS
        if (count := block.count(f"- **{field}:**")) != 1
        for kind in ("missing" if count == 0 else "duplicate",)
    ]
    iteration_id = _field_value(block, "Iteration ID", r"`([^`]+)`")
    if iteration_id in seen_ids:
        errors.append(f"{title}: duplicate Iteration ID value")
    if iteration_id:
        seen_ids.add(iteration_id)

    goal_text, goal_errors = _goal_text(block, title)
    errors.extend(goal_errors)
    if block.count("```mermaid") != 1:
        errors.append(f"{title}: expected exactly one Mermaid workflow")

    current_digest = _field_value(
        block, "Current goal digest", r"`sha256:([0-9a-f]{64})`"
    )
    if block.count("- **Current goal digest:**") == 1 and not current_digest:
        errors.append(f"{title}: malformed Current goal digest")
    if goal_text and current_digest:
        computed = hashlib.sha256(goal_text.encode()).hexdigest()
        if computed != current_digest:
            errors.append(f"{title}: Current goal digest does not match goal text")

    prior_digest = _field_value(block, "Prior goal digest", r"`([^`]+)`")
    if block.count("- **Prior goal digest:**") == 1 and not prior_digest:
        errors.append(f"{title}: malformed Prior goal digest")
    expected_prior = (
        "NONE (bootstrap)"
        if index == 0
        else f"sha256:{prior_current_digest or 'MISSING'}"
    )
    if prior_digest != expected_prior:
        errors.append(f"{title}: Prior goal digest breaks the digest chain")
    return errors, current_digest


def goal_history_errors(text: str) -> tuple[str, ...]:
    """Return structural and digest-chain defects in a goal-history document."""
    matches = list(_GOAL_HISTORY_ENTRY.finditer(text))
    if not matches:
        return ("goal history has no dated iteration",)
    errors: list[str] = []
    seen_ids: set[str] = set()
    prior_current_digest: str | None = None
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block_errors, prior_current_digest = _iteration_errors(
            text[match.end() : end],
            match.group("title"),
            index,
            prior_current_digest,
            seen_ids,
        )
        errors.extend(block_errors)
    return tuple(errors)


def _git_bytes(repo_root: Path, *args: str) -> tuple[int, bytes]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
    )
    return result.returncode, result.stdout


def _is_git_checkout(repo_root: Path) -> bool:
    rc, answer = _git_bytes(repo_root, "rev-parse", "--is-inside-work-tree")
    return rc == 0 and answer.strip() == b"true"


def _authorized_goal_history_base(repo_root: Path) -> str | None:
    rc, resolved = _git_bytes(repo_root, "merge-base", "HEAD", "origin/main")
    return resolved.decode().strip() if rc == 0 and resolved.strip() else None


def _history_blob(repo_root: Path, revision: str) -> bytes | None:
    rc, blob = _git_bytes(repo_root, "show", f"{revision}:{GOAL_HISTORY_PATH}")
    return blob if rc == 0 else None


def _revision_blob_error(blob: bytes, revision: str, *, bootstrap: bool) -> str | None:
    try:
        text = blob.decode()
    except UnicodeDecodeError:
        return f"{revision} goal history is not UTF-8"
    if errors := goal_history_errors(text):
        return f"{revision} has invalid goal history: " + "; ".join(errors)
    if bootstrap and len(list(_GOAL_HISTORY_ENTRY.finditer(text))) != 1:
        return f"{revision} bootstrap must contain exactly one iteration"
    return None


def _committed_append_only_error(
    repo_root: Path, base: str
) -> tuple[str | None, bytes | None]:
    previous = _history_blob(repo_root, base)
    rc, raw_revisions = _git_bytes(
        repo_root, "rev-list", "--first-parent", "--reverse", f"{base}..HEAD"
    )
    if rc != 0:
        return "cannot enumerate first-parent history from authorized baseline", None
    for revision in raw_revisions.decode().splitlines():
        blob = _history_blob(repo_root, revision)
        if previous is not None and blob is None:
            return f"{revision} deletes the goal history", None
        if blob is None:
            continue
        if error := _revision_blob_error(blob, revision, bootstrap=previous is None):
            return error, None
        if previous is not None and not blob.startswith(previous):
            return f"{revision} rewrites prior goal-history bytes", None
        previous = blob
    return None, previous


def _append_only_error(repo_root: Path, current: bytes, text: str) -> str | None:
    base = _authorized_goal_history_base(repo_root)
    if base is None:
        return "cannot resolve the fixed origin/main goal-history baseline"

    error, committed = _committed_append_only_error(repo_root, base)
    if error:
        return error
    if committed is not None:
        if not current.startswith(committed):
            return "working goal history rewrites committed HEAD bytes"
        return None

    prior = _field_value(text, "Prior goal digest", r"`([^`]+)`")
    is_single_bootstrap = (
        len(list(_GOAL_HISTORY_ENTRY.finditer(text))) == 1
        and prior == "NONE (bootstrap)"
    )
    if is_single_bootstrap:
        return None
    return "baseline lacks goal history; bootstrap requires exactly one iteration"


def scan_narrative(
    repo_root: Path,
    patterns: Sequence[str] = DEFAULT_NARRATIVE_PATHS,
    *,
    tail_lines: int | None = DEFAULT_TAIL_LINES,
    glob_limit: int = DEFAULT_HANDOFF_LIMIT,
) -> list[NarrativeHit]:
    """Every narrative hit across the resolved corpus, bounded to the tail.

    The bound matters and is not hygiene: the notepad accumulates across every
    session this repo has had, so an unbounded scan answers a different
    question than the one asked and buries this session under its own history.
    """
    hits: list[NarrativeHit] = []
    for path in narrative_paths(repo_root, patterns, glob_limit=glob_limit):
        full_text = path.read_text(errors="replace")
        text, offset = tail_text(full_text, tail_lines)
        rel = str(path.relative_to(repo_root))
        hits.extend(
            NarrativeHit(hit.path, hit.line_number + offset, hit.meaning, hit.line)
            for hit in narrative_hits(text, rel)
        )
    return hits


_CANDIDATE_TEMPLATE = """\
### <name>: <one line>

- **Done by hand:** <what the session actually did, with turn/attempt count>
- **Cost avoided:** <the CONCRETE cost — a wrong-platform run, a re-derivation,
  a spurious red gate. A candidate that cannot fill this line is not one.>
- **Proposed triple:** skill `<name>` -> `mise run <task>` -> `dotfiles_setup.<module>`
"""


def render_report(
    shapes: Sequence[ShapeCandidate],
    hits: Sequence[NarrativeHit],
    *,
    transcripts_scanned: int,
    tail_lines: int | None,
    lanes: tuple[str, ...],
) -> str:
    """The markdown report: evidence from both lanes, then the write-up template.

    The template ships with the report rather than living only in the skill so
    that a candidate written straight into this file still has to state its
    avoided cost.
    """
    out = [
        "# Session review — what was done by hand that should be code",
        "",
        (
            f"Lanes run: {', '.join(lanes)}. Transcript window: "
            f"{transcripts_scanned} transcript file(s) — roots plus their nested "
            f"subagent transcripts, so this is NOT a session count. Narrative "
            f"window: "
            + (f"last {tail_lines} lines per file." if tail_lines else "whole file.")
        ),
        "",
        "## Lane 1 — recurring command shapes",
        "",
    ]
    if shapes:
        out += [
            (
                "Ranked by SESSION SPREAD first: a shape confined to one session "
                "may be a single grind, while one that comes back is a workflow."
            ),
            "",
            "| sessions | uses | signal | shape | example |",
            "|---|---|---|---|---|",
            *(candidate.render() for candidate in shapes),
        ]
    else:
        out.append(
            "_No shape recurred often enough to rank. That is a real result "
            "only if lane 2 also came back thin — a reasoning sink leaves no "
            "repeated command._"
        )
    out += ["", "## Lane 2 — passages that read like manual work", ""]
    if hits:
        out += [
            (
                "Surfaced, NOT judged: a regex cannot tell an expensive slog from "
                "a sentence describing one. Read the passage before believing it."
            ),
            "",
            "| where | reads like | line |",
            "|---|---|---|",
            *(hit.render() for hit in hits),
        ]
    else:
        out.append("_No narrative marker fired._")
    out += [
        "",
        "## Write up each candidate like this",
        "",
        _CANDIDATE_TEMPLATE,
        (
            "The **Cost avoided** line is the gate (#607/#608): a candidate that "
            "cannot name a concrete cost it would have prevented is a preference, "
            "not a finding."
        ),
        "",
    ]
    return "\n".join(out)


def _lane_configuration_error(lanes: LaneChoice, sessions: int) -> str | None:
    selected_only = sum(
        (lanes.transcript_only, lanes.narrative_only, lanes.requirements_only), start=0
    )
    if sessions < 1:
        return "--sessions must be at least 1"
    if not 1 <= lanes.max_iterations <= MAX_REVIEW_ITERATIONS:
        return "--max-iterations must be between 1 and 5"
    if selected_only > 1:
        return (
            "--transcript-only, --narrative-only, and --requirements-only are "
            "mutually exclusive; the default keeps the two automation lanes"
        )
    return None


def _review_preflight_error(
    repo_root: Path, lanes: LaneChoice, sessions: int
) -> str | None:
    if error := _lane_configuration_error(lanes, sessions):
        return error
    history = repo_root / GOAL_HISTORY_PATH
    git_checkout = _is_git_checkout(repo_root)
    if git_checkout and not history.is_file():
        return f"missing required {GOAL_HISTORY_PATH}"
    if not history.is_file():
        return None
    text = history.read_text()
    if errors := goal_history_errors(text):
        return "invalid goal history: " + "; ".join(errors)
    if git_checkout and (
        error := _append_only_error(repo_root, history.read_bytes(), text)
    ):
        return "invalid goal history: " + error
    return None


def session_review_main(
    repo_root: Path,
    *,
    lanes: LaneChoice = BOTH_LANES,
    sessions: int = command_audit.DEFAULT_SESSION_LIMIT,
    output: Path | None = None,
    narrative: NarrativeScope = DEFAULT_NARRATIVE_SCOPE,
) -> int:
    """Run the requested lanes and write (or print) the report.

    Asking for both ``--transcript-only`` and ``--narrative-only`` is refused
    rather than silently resolved: the two flags mean opposite things, so any
    interpretation would be a guess about intent, and the lanes are disjoint
    enough that guessing wrong loses the finding.
    """
    transcript_only, narrative_only = lanes.transcript_only, lanes.narrative_only
    if preflight_error := _review_preflight_error(repo_root, lanes, sessions):
        logger.error("%s", preflight_error)
        return 2

    if lanes.requirements_only:
        return _requirements_review(repo_root, lanes, sessions, output)

    shapes: list[ShapeCandidate] = []
    hits: list[NarrativeHit] = []
    lane_names: list[str] = []
    scanned = 0
    if not narrative_only:
        lane_names.append("transcript")
        base = command_audit.transcripts_base()
        paths = command_audit.project_transcripts(base, repo_root, limit=sessions)
        scanned = len(paths)
        shapes = shape_candidates(command_audit.iter_bash_commands(paths))
    if not transcript_only:
        lane_names.append("narrative")
        hits = scan_narrative(
            repo_root,
            narrative.patterns,
            tail_lines=narrative.tail_lines,
            glob_limit=narrative.glob_limit,
        )

    report = render_report(
        shapes,
        hits,
        transcripts_scanned=scanned,
        tail_lines=narrative.tail_lines if not transcript_only else None,
        lanes=tuple(lane_names),
    )
    if not transcript_only and not narrative_only:
        return _requirements_review(
            repo_root,
            lanes,
            sessions,
            output,
            automation_report=report,
        )
    if output is None:
        logger.info("%s", report)
        return 0
    written = command_audit.write_report(report, repo_root, output)
    logger.info(
        "session-review: %d shape(s) and %d passage(s) -> %s",
        len(shapes),
        len(hits),
        written,
    )
    return 0


def _load_review_dispositions(
    lanes: LaneChoice, source_repo_root: Path
) -> tuple[
    tuple[session_ledger.PreventionDisposition, ...],
    tuple[session_ledger.SemanticDisposition, ...],
]:
    """Load the two independent reviewed-decision inputs."""
    prevention = (
        session_ledger.load_dispositions(
            lanes.dispositions,
            repo_root=source_repo_root,
            run_id=lanes.receipt_run_id,
        )
        if lanes.dispositions is not None
        else ()
    )
    semantic = (
        session_ledger.load_semantic_dispositions(lanes.semantic_dispositions)
        if lanes.semantic_dispositions is not None
        else ()
    )
    return prevention, semantic


def _requirements_review(
    repo_root: Path,
    lanes: LaneChoice,
    sessions: int,
    output: Path | None,
    automation_report: str = "",
) -> int:
    """Collect bounded native evidence and fail closed on every omission."""
    if lanes.requirements_only and lanes.source_repo_root is None:
        logger.error(
            "--requirements-only requires --source-repo-root so transcript cwd "
            "selection is explicit"
        )
        return 2
    source_repo_root = lanes.source_repo_root or repo_root
    codex_session_id = lanes.codex_session_id or lanes.session_id
    try:
        dispositions, semantic_dispositions = _load_review_dispositions(
            lanes, source_repo_root
        )
    except OSError, TypeError, ValueError, json.JSONDecodeError:
        logger.exception("invalid session-review dispositions")
        return 2
    coverage = session_ledger.build_requirement_coverage(
        source_repo_root,
        dispositions=dispositions,
        semantic_dispositions=semantic_dispositions,
        selection=session_ledger.CoverageSelection(
            limit=sessions,
            codex_session_id=codex_session_id,
            require_active_identity=True,
            rebuild_cache=lanes.rebuild_cache,
        ),
    )
    prior_dispositions: tuple[str, ...] = ()
    iteration = session_ledger.advance_iteration(
        coverage,
        number=1,
        context=session_ledger.IterationContext(
            lanes.max_iterations,
            str(source_repo_root.resolve()),
            codex_session_id or "",
        ),
        previous_disposition_ids=prior_dispositions,
    )
    for number in range(2, lanes.max_iterations + 1):
        if iteration.action != session_ledger.IterationAction.PREVENTION_RECORDED:
            break
        prior_dispositions = iteration.disposition_ids
        coverage = session_ledger.build_requirement_coverage(
            source_repo_root,
            dispositions=dispositions,
            semantic_dispositions=semantic_dispositions,
            selection=session_ledger.CoverageSelection(
                limit=sessions,
                codex_session_id=codex_session_id,
                require_active_identity=True,
                rebuild_cache=lanes.rebuild_cache,
            ),
        )
        iteration = session_ledger.advance_iteration(
            coverage,
            number=number,
            context=session_ledger.IterationContext(
                lanes.max_iterations,
                str(source_repo_root.resolve()),
                codex_session_id or "",
            ),
            previous_disposition_ids=prior_dispositions,
        )
    requirements_report = session_ledger.render_coverage(coverage)
    report = (
        f"{automation_report.rstrip()}\n\n{requirements_report}"
        if automation_report
        else requirements_report
    )
    destination = output or Path(".agent/session-review.md")
    written = command_audit.write_report(report, repo_root, destination)
    iteration_path = written.with_suffix(written.suffix + ".iteration.json")
    try:
        artifact_paths = _write_coverage_artifacts(coverage, written)
    except ValueError:
        logger.exception("bounded evidence reference artifact could not be written")
        return 1
    evidence_path, cutoff_path = artifact_paths[:2]
    iteration = replace(
        iteration,
        artifacts=(
            session_ledger.artifact_ref(written, kind="report"),
            *(
                session_ledger.artifact_ref(path, kind=kind)
                for path, kind in zip(
                    artifact_paths,
                    (
                        "evidence",
                        "cutoffs",
                        "claims",
                        "omissions",
                        "semantic_disposition_draft",
                    ),
                    strict=True,
                )
            ),
        ),
    )
    iteration_path.write_text(iteration.to_json())
    omissions = (
        *coverage.omissions,
        *session_ledger.disposition_omissions(coverage),
    )
    for omission in omissions[:_MAX_LOGGED_OMISSIONS]:
        logger.error("session-review incomplete: %s", omission)
    if len(omissions) > _MAX_LOGGED_OMISSIONS:
        logger.error(
            "session-review incomplete: %d additional omission(s); "
            "use the bounded report, evidence digest, and cutoff manifest",
            len(omissions) - _MAX_LOGGED_OMISSIONS,
        )
    logger.info(
        "session-review requirements: %d requirement(s), %d promise(s) -> %s; "
        "evidence %s; cutoffs %s; iteration %s",
        len(coverage.requirements),
        len(coverage.promises),
        written,
        evidence_path,
        cutoff_path,
        iteration_path,
    )
    converged = iteration.action == session_ledger.IterationAction.CONVERGED
    complete = coverage.status == session_ledger.CoverageStatus.COMPLETE
    return 0 if complete and converged else 1


def _write_segmented_artifact(
    path: Path, index: str, segments: tuple[str, ...]
) -> None:
    for number, segment in enumerate(segments, start=1):
        segment_path = path.with_name(f"{path.name}.{number:04d}.json")
        segment_path.write_text(segment)
        if (
            hashlib.sha256(segment_path.read_bytes()).hexdigest()
            != hashlib.sha256(segment.encode()).hexdigest()
        ):
            message = f"segment readback failed for {path.name}"
            raise ValueError(message)
    path.write_text(index)
    if path.read_text() != index:
        message = f"index readback failed for {path.name}"
        raise ValueError(message)


def _write_coverage_artifacts(
    coverage: session_ledger.RequirementCoverage, report_path: Path
) -> tuple[Path, Path, Path, Path, Path]:
    """Persist bounded indexes before the iteration references their digests."""
    evidence = report_path.with_suffix(report_path.suffix + ".evidence.json")
    cutoffs = report_path.with_suffix(report_path.suffix + ".cutoffs.json")
    claims = report_path.with_suffix(report_path.suffix + ".claims.json")
    omissions = report_path.with_suffix(report_path.suffix + ".omissions.json")
    semantic = report_path.with_suffix(
        report_path.suffix + ".semantic-dispositions.draft.json"
    )
    evidence.write_text(coverage.to_json())
    _write_segmented_artifact(
        cutoffs, coverage.cutoffs_to_json(), coverage.cutoff_segments_to_json()
    )
    _write_segmented_artifact(
        claims, coverage.claims_to_json(), coverage.claim_segments_to_json()
    )
    _write_segmented_artifact(
        omissions, coverage.omissions_to_json(), coverage.omission_segments_to_json()
    )
    _write_segmented_artifact(
        semantic,
        coverage.semantic_disposition_draft_to_json(),
        coverage.semantic_disposition_draft_segments_to_json(),
    )
    return evidence, cutoffs, claims, omissions, semantic
