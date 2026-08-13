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

**Lane 2 — the narrative pass** over ``.agent/notepad.md`` and the session
handoffs, for **reasoning sinks that leave no repeated command**. This lane is
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

import json
import logging
import re
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

#: Where a session records its own manual work. Both are gitignored, which is
#: exactly why `--since <ref>` cannot bound them.
DEFAULT_NARRATIVE_PATHS: tuple[str, ...] = (
    ".agent/notepad.md",
    ".agent/plans/session-*.md",
)

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
    session_id: str | None = None
    codex_session_id: str | None = None
    receipt_run_id: str = ""
    max_iterations: int = 1


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
    never bounded — the notepad is the one file you always want.
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
        text, offset = tail_text(path.read_text(errors="replace"), tail_lines)
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
    selected_only = sum(
        (transcript_only, narrative_only, lanes.requirements_only), start=0
    )
    if sessions < 1:
        logger.error("--sessions must be at least 1")
    elif not 1 <= lanes.max_iterations <= MAX_REVIEW_ITERATIONS:
        logger.error("--max-iterations must be between 1 and 5")
    elif selected_only > 1:
        logger.error(
            "--transcript-only, --narrative-only, and --requirements-only are "
            "mutually exclusive; the default keeps the two automation lanes"
        )
    if (
        sessions < 1
        or not 1 <= lanes.max_iterations <= MAX_REVIEW_ITERATIONS
        or selected_only > 1
    ):
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
    dispositions: tuple[session_ledger.PreventionDisposition, ...] = ()
    if lanes.dispositions is not None:
        try:
            dispositions = session_ledger.load_dispositions(
                lanes.dispositions,
                repo_root=source_repo_root,
                run_id=lanes.receipt_run_id,
            )
        except OSError, TypeError, ValueError, json.JSONDecodeError:
            logger.exception("invalid prevention dispositions")
            return 2
    coverage = session_ledger.build_requirement_coverage(
        source_repo_root,
        dispositions=dispositions,
        selection=session_ledger.CoverageSelection(
            limit=sessions,
            codex_session_id=codex_session_id,
            require_active_identity=True,
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
            selection=session_ledger.CoverageSelection(
                limit=sessions,
                codex_session_id=codex_session_id,
                require_active_identity=True,
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
    try:
        evidence = coverage.to_json()
        cutoffs = coverage.cutoffs_to_json()
        cutoff_segments = coverage.cutoff_segments_to_json()
    except ValueError:
        logger.exception("bounded evidence reference artifact could not be written")
        return 1
    written = command_audit.write_report(report, repo_root, destination)
    evidence_path = written.with_suffix(written.suffix + ".evidence.json")
    cutoff_path = written.with_suffix(written.suffix + ".cutoffs.json")
    iteration_path = written.with_suffix(written.suffix + ".iteration.json")
    evidence_path.write_text(evidence)
    for index, segment in enumerate(cutoff_segments, start=1):
        segment_path = cutoff_path.with_name(f"{cutoff_path.name}.{index:04d}.json")
        segment_path.write_text(segment)
    cutoff_path.write_text(cutoffs)
    iteration = replace(
        iteration,
        artifacts=(
            session_ledger.artifact_ref(written, kind="report"),
            session_ledger.artifact_ref(evidence_path, kind="evidence"),
            session_ledger.artifact_ref(cutoff_path, kind="cutoffs"),
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
