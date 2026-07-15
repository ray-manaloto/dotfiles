"""Memory-index checker: shorten MEMORY.md without silently destroying facts.

``MEMORY.md`` is the auto-memory index at
``$CLAUDE_CONFIG_DIR/projects/<encoded-cwd>/memory/`` (default ``~/.claude``).
Only its **first 200 lines or first 25KB, whichever comes first**, are loaded at
the start of every conversation; the topic files it links are not loaded at all
until Claude reads them on demand. So the index is a scarce, capped resource
that has to be kept short — and *shortening it is the dangerous part*.

**A naive trim is silently lossy.** Measured 2026-07-14, not theorized: four
facts (``#244``, ``#186``, ``#194``, ``8010c61``) lived ONLY in an index hook
and were one edit away from being destroyed, because the topic file each hook
linked to never mentioned them. Nothing warns you — the trimmed line simply
reads better afterwards. Hence the operation this module exists to gate:

    verify each distinctive fact survives in the linked topic file
    → migrate (or correct) what doesn't → THEN shorten.

The check-then-trim order is the whole point; the verify step is easy to skip
and silent when skipped.

Findings are split by whether the fact survives ANYWHERE else in the memory
directory, because a bare "not in the linked file" verdict is mostly noise:

- ``index_only`` — the fact exists nowhere but the index hook. Shortening that
  hook destroys it. The only class that fails the check.
- ``elsewhere`` — the fact is in a *different* memory file, so a trim cannot
  destroy it; the link just points somewhere less specific. Informational.

This module reports the observation and stops there — it never says "migrate
this". The distinction matters: the checker's first real hit was an index hook
claiming CI went green at ``3adff36`` while its topic file said ``c2cecd7`` (a
later commit). The fact was genuinely index-only, but the fix was to *correct a
stale index*, not to push an outdated sha down into a file that had already
superseded it. Migrate-vs-correct-vs-drop needs a human who can tell which side
is stale; a tool that prescribes is a tool that confidently does the wrong one.

A distinctive fact is one you cannot re-derive from the surrounding prose:
issue/PR refs, commit shas, and byte sizes. The classes are deliberately narrow.
An earlier prototype extracted looser patterns and **over-reported** — it cried
``25.8GB`` missing when the topic file wrote ``25.8 GB`` with a space — and a
checker that cries wolf gets ignored, which costs more than the facts it would
have caught. Matching is normalized per class (see :func:`fact_present`) rather
than by raw string, so spacing and sha length do not manufacture findings.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dotfiles_setup.command_audit import encode_cwd, transcripts_base

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# The documented auto-load ceiling: 200 lines OR 25KB, whichever comes first.
# Content past it is not loaded at session start — an entry beyond the cutoff is
# invisible, which is the same silent loss this module exists to prevent, just
# by a different route.
#
# BOTH caps are enforced, via :func:`load_cutoff_line`. An earlier revision
# checked only the line count, on the stated belief that lines were the nearer
# ceiling — a belief this repo asserted twice over data that said otherwise
# (60% of the line budget vs 82% of the byte budget: bytes bind first). At the
# index's ~149 bytes/line the 25KB cap lands near line 168 and the 200-line cap
# is never reached, so the unenforced axis was the ONLY one that could fire. The
# checker reported `OVER` in its own table and still exited 0.
LINE_BUDGET = 200
BYTE_BUDGET = 25_000

# The index's one entry shape: `- [Title](file.md) — hook`. Both the em dash and
# a plain `--` are accepted; the hook is everything after it.
_ENTRY = re.compile(
    r"^-\s*\[(?P<title>[^\]]+)\]\((?P<target>[^)]+)\)\s*(?:—|--)\s*(?P<hook>.+)$"
)

# A line that is plainly a linked list item but did NOT match _ENTRY (a `:`
# separator, a missing hook, a stray bracket). Such a line is invisible to every
# other check here — its facts are never compared and its link is never
# resolved — while the report still claims to have audited the index. A silent
# coverage hole is precisely what this module exists to prevent, so an unparsed
# line is reported and fails rather than being skipped quietly.
_LINK_ITEM = re.compile(r"^-\s*\[[^\]]+\]\([^)]+\)")

# An issue/PR ref. Unambiguous by construction.
_ISSUE = re.compile(r"#\d+")

# A commit sha: 7-40 hex chars with at least one DIGIT *and* at least one [a-f].
# Both lookaheads are load-bearing, against opposite false positives:
#   - the digit rules out English words — `acceded` and `facade` are pure [a-f];
#   - the letter rules out plain numbers — every decimal digit is also hex, so a
#     digit-only test read `20260714` (a `research-YYYYMMDD-*` slug, this repo's
#     own directory convention), an 11-digit GHA run id, and `1234567 files` as
#     commit shas. Worse, `_sha_present`'s prefix match then answered "present"
#     for any file containing a shorter unrelated number.
# The trade: ~4% of 7-char abbreviated shas are all-digits ((10/16)^7) and are no
# longer extracted, so their facts go unchecked. Chosen deliberately — a missed
# check is one fact; a class that cries wolf on every date slug is the whole
# report's credibility, and the narrow classes exist precisely to protect it.
_SHA = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")

# A byte size, e.g. `17.5 GB` / `25.8GB` / `38GB`. Units are a closed set: an
# open `[A-Za-z]{1,3}` suffix matches the start of ordinary words after any
# number ("4 facts"), and each imprecise class costs the report its credibility.
_SIZE = re.compile(r"\b(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>[KMGT]i?B|B)\b")

_MEMORY_INDEX = "MEMORY.md"


@dataclass(frozen=True)
class Fact:
    """One distinctive token lifted out of an index hook.

    ``kind`` selects the matching strategy in :func:`fact_present` — the same
    literal compares differently as a sha (prefix-tolerant) than as an issue
    ref (exact), so the kind travels with the value rather than being re-guessed
    at each comparison.
    """

    kind: str
    value: str


@dataclass(frozen=True)
class IndexEntry:
    """One `- [Title](file.md) — hook` line of the index."""

    line_no: int
    title: str
    target: str
    hook: str


@dataclass(frozen=True)
class Finding:
    """A hook fact with no counterpart in the topic file the hook links to."""

    entry: IndexEntry
    fact: Fact
    elsewhere: tuple[str, ...]

    @property
    def severity(self) -> str:
        """``index_only`` when nothing else records the fact, else ``elsewhere``."""
        return "elsewhere" if self.elsewhere else "index_only"


@dataclass(frozen=True)
class MemoryIndexResult:
    """The outcome of one index audit."""

    lines: int
    size: int
    entries: int
    findings: tuple[Finding, ...]
    broken: tuple[IndexEntry, ...]
    orphans: tuple[str, ...]
    beyond_budget: tuple[IndexEntry, ...]
    unparsed: tuple[tuple[int, str], ...]

    @property
    def index_only(self) -> tuple[Finding, ...]:
        """Findings whose fact would be destroyed by shortening the hook."""
        return tuple(f for f in self.findings if f.severity == "index_only")

    @property
    def elsewhere(self) -> tuple[Finding, ...]:
        """Findings whose fact survives in some other memory file."""
        return tuple(f for f in self.findings if f.severity == "elsewhere")

    @property
    def over_cap(self) -> bool:
        """True when the index exceeds a cap, so its tail does not load at all."""
        return self.lines > LINE_BUDGET or self.size > BYTE_BUDGET

    @property
    def ok(self) -> bool:
        """True when nothing would be lost and nothing went unchecked.

        Orphans and ``elsewhere`` findings are excluded on purpose — neither
        destroys a fact, and failing on them would train the reader to ignore
        the exit code. ``unparsed`` IS included: a line no check could see makes
        a clean report a false claim of coverage. So is ``over_cap``: a report
        that prints ``OVER`` in its own budget table and then exits 0 is telling
        the reader two opposite things.
        """
        return not (
            self.index_only
            or self.broken
            or self.beyond_budget
            or self.unparsed
            or self.over_cap
        )


def memory_dir(
    project_root: Path, env: dict[str, str] | None = None, home: Path | None = None
) -> Path:
    """The auto-memory directory for ``project_root``.

    A sibling of the transcripts under the same encoded-project dir, so the
    env-aware base resolution and the path encoding are reused from
    :mod:`dotfiles_setup.command_audit` rather than re-derived (and re-broken)
    here. ``CLAUDE_CONFIG_DIR`` is honoured for the same reason it is there:
    ``~/.claude`` is a default, not a constant.
    """
    base = transcripts_base(env, home)
    return base / encode_cwd(project_root) / "memory"


def load_memories(directory: Path) -> dict[str, str]:
    """Every topic file in ``directory`` as ``{filename: text}``.

    ``MEMORY.md`` is excluded: it is the thing under audit, and leaving it in
    would make every fact trivially "present somewhere" — the index always
    contains its own hooks.
    """
    out: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        if path.name == _MEMORY_INDEX:
            continue
        try:
            out[path.name] = path.read_text(errors="replace")
        except OSError:
            continue
    return out


def parse_index(text: str) -> list[IndexEntry]:
    """Every entry line of the index.

    The `##` section headings are not captured: a finding is located by line
    number and target, so the section would be a field nothing reads.
    """
    entries: list[IndexEntry] = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        entry = _ENTRY.match(raw.strip())
        if entry:
            entries.append(
                IndexEntry(
                    line_no=line_no,
                    title=entry["title"],
                    target=entry["target"],
                    hook=entry["hook"],
                )
            )
    return entries


def load_cutoff_line(text: str) -> int:
    """The last line of ``text`` that auto-loads — whichever cap binds first.

    Bytes are accumulated with line endings included (``keepends=True``), since
    the newline is a byte the loader pays for too. Returns the line BEFORE the
    one that breaches :data:`BYTE_BUDGET`, or :data:`LINE_BUDGET` when the byte
    cap is never reached — so the caller can treat the smaller of the two as the
    cutoff without special-casing which one fired.
    """
    total = 0
    for line_no, line in enumerate(text.splitlines(keepends=True), 1):
        total += len(line.encode())
        if total > BYTE_BUDGET:
            return line_no - 1
    return LINE_BUDGET


def unparsed_lines(text: str) -> list[tuple[int, str]]:
    """Linked list items that :func:`parse_index` could not read, with line nos.

    These are the lines the audit would otherwise skip in silence — see
    :data:`_LINK_ITEM`.
    """
    return [
        (line_no, line)
        for line_no, raw in enumerate(text.splitlines(), 1)
        if (line := raw.strip()) and _LINK_ITEM.match(line) and not _ENTRY.match(line)
    ]


def distinctive_facts(hook: str) -> list[Fact]:
    """The facts in ``hook`` that prose cannot re-derive, de-duplicated.

    Order is stable (issues, then shas, then sizes) so a report diffs cleanly
    between runs.
    """
    found: list[Fact] = []
    seen: set[tuple[str, str]] = set()
    for kind, matches in (
        ("issue", _ISSUE.findall(hook)),
        ("sha", _SHA.findall(hook)),
        ("size", [f"{m['n']}{m['unit']}" for m in _SIZE.finditer(hook)]),
    ):
        for value in matches:
            key = (kind, value)
            if key not in seen:
                seen.add(key)
                found.append(Fact(kind, value))
    return found


def _sha_present(text: str, value: str) -> bool:
    """True when ``text`` holds a sha that is a prefix of ``value`` or vice versa.

    Abbreviated shas are written at whatever length the author found readable,
    so an index hook's ``8010c61`` and a topic file's ``8010c61f2`` are the same
    fact. Comparing the raw strings would report a difference in typing habits
    as a lost fact.
    """
    return any(
        s.startswith(value) or value.startswith(s) for s in set(_SHA.findall(text))
    )


def _size_present(text: str, value: str) -> bool:
    """True when ``text`` states the same size, with or without a space.

    The prototype's one real flaw: `25.8GB` in a hook and `25.8 GB` in the file
    are one fact, and reporting them as two is the false positive that gets a
    checker ignored.
    """
    match = _SIZE.match(value)
    if match is None:  # unreachable: value came from _SIZE
        return False
    pattern = rf"\b{re.escape(match['n'])}\s*{re.escape(match['unit'])}\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def fact_present(text: str, fact: Fact) -> bool:
    """True when ``text`` records ``fact``, compared per-kind rather than raw."""
    if fact.kind == "sha":
        return _sha_present(text, fact.value)
    if fact.kind == "size":
        return _size_present(text, fact.value)
    return re.search(rf"{re.escape(fact.value)}\b", text) is not None


def _elsewhere(files: dict[str, str], target: str, fact: Fact) -> tuple[str, ...]:
    """Memory files other than ``target`` that record ``fact``.

    Only for globally-unique identifiers. An issue ref or a sha names the same
    thing in every file, so finding one elsewhere really does mean the fact
    survives a trim. A **size does not** — `17.5 GB` of container image and
    `17.5 GB` of free disk are different facts that happen to share a number, and
    treating the coincidence as survival would downgrade a genuinely index-only
    measurement to informational and pass. Sizes therefore never qualify, and an
    unmatched one stays ``index_only``.
    """
    if fact.kind == "size":
        return ()
    return tuple(
        name
        for name, text in sorted(files.items())
        if name != target and fact_present(text, fact)
    )


def _audit_entry(entry: IndexEntry, files: dict[str, str]) -> Iterator[Finding]:
    """Every fact in ``entry`` that its linked topic file does not record.

    Title AND hook: the whole `- [Title](file.md) — hook` line is what a curator
    rewrites, and the index really does carry facts in titles (`PR #140 MERGED`,
    `GHA redesign epic #116 COMPLETE`). Scanning only the hook would let
    shortening a title destroy an issue ref with the report still clean.
    """
    body = files[entry.target]
    for fact in distinctive_facts(f"{entry.title} {entry.hook}"):
        if not fact_present(body, fact):
            yield Finding(entry, fact, _elsewhere(files, entry.target, fact))


def audit_index(index_text: str, files: dict[str, str]) -> MemoryIndexResult:
    """Audit the index against the topic files it links.

    Pure: the caller does the IO. ``files`` maps filename → text.

    ``MEMORY.md`` is dropped here rather than merely documented as the caller's
    job, because including it defeats the whole check *quietly*: the index
    contains every hook, so every fact would resolve as "recorded somewhere" and
    the report would come back clean. A silent all-pass is the one failure this
    module cannot afford, so the invariant is enforced where it is relied on.
    """
    topics = {k: v for k, v in files.items() if k != _MEMORY_INDEX}
    entries = parse_index(index_text)
    cutoff = min(load_cutoff_line(index_text), LINE_BUDGET)
    findings: list[Finding] = []
    broken: list[IndexEntry] = []
    for entry in entries:
        if entry.target not in topics:
            broken.append(entry)
            continue
        findings.extend(_audit_entry(entry, topics))
    linked = {e.target for e in entries}
    return MemoryIndexResult(
        lines=len(index_text.splitlines()),
        size=len(index_text.encode()),
        entries=len(entries),
        findings=tuple(findings),
        broken=tuple(broken),
        orphans=tuple(sorted(set(topics) - linked)),
        beyond_budget=tuple(e for e in entries if e.line_no > cutoff),
        unparsed=tuple(unparsed_lines(index_text)),
    )


def inbound_refs(name: str, files: dict[str, str]) -> list[str]:
    """Memory files citing ``name``, by `[[wikilink]]` or by filename.

    Deleting a memory is the other half of curation, and it has the same silent
    failure mode as trimming: ``feedback_colima_recommendation`` looked purely
    archival, but two memories cited it and it still held a live fact. Callers
    check this before deleting so a citation cannot rot unnoticed.

    A `[[link]]` to a memory that does not exist is NOT reported anywhere: the
    memory instructions define a dangling wikilink as a marker for a memory
    worth writing later, so it is intent, not breakage.

    Matching is a bare boundary-anchored **stem**, which subsumes every citation
    form the memories actually use — ``[[stem]]``, ``[[stem|Alias]]``,
    ``` `stem` ``` and ``stem.md`` all contain the stem at word boundaries. An
    earlier revision required either the brackets or the ``.md`` suffix and so
    missed the bare-backtick form: measured against the live memory dir, 4 real
    citations (of 130) were invisible, and one memory that IS cited was reported
    as having no inbound refs — the exact false reassurance that precedes a
    delete. This is safe only because memory stems are long snake_case; a
    one-character stem would collide with prose, which the tests pin.
    """
    stem = name.removesuffix(".md")
    pattern = re.compile(rf"\b{re.escape(stem)}\b")
    return [
        other
        for other, text in sorted(files.items())
        if other != name and pattern.search(text)
    ]


def _budget_line(label: str, used: int, cap: int) -> str:
    pct = round(100 * used / cap)
    state = "OVER" if used > cap else "ok"
    return f"| {label} | {used:,} | {cap:,} | {pct}% | {state} |"


def _findings_table(findings: tuple[Finding, ...]) -> list[str]:
    return [
        "| index line | fact | kind | links to | also in |",
        "|---:|---|---|---|---|",
        *(
            f"| {f.entry.line_no} | `{f.fact.value}` | {f.fact.kind} | "
            f"`{f.entry.target}` | {', '.join(f.elsewhere) or '—'} |"
            for f in findings
        ),
        "",
    ]


def _budget_section(result: MemoryIndexResult) -> list[str]:
    """The load-ceiling table plus a note naming whichever cap binds first."""
    nearer = (
        "lines" if result.lines / LINE_BUDGET >= result.size / BYTE_BUDGET else "bytes"
    )
    lines = [
        "| budget | used | cap | used | state |",
        "|---|---:|---:|---:|---|",
        _budget_line("lines", result.lines, LINE_BUDGET),
        _budget_line("bytes", result.size, BYTE_BUDGET),
        "",
        f"**{result.entries}** entries. Auto-load stops at 200 lines *or* 25KB, "
        f"whichever comes first — **{nearer}** is the nearer ceiling here. "
        "Anything past the cutoff is not loaded at session start.",
        "",
    ]
    if result.beyond_budget:
        lines += [
            "### 🚨 Entries past the load cutoff (not loaded at all)",
            "",
            *(
                f"- line {e.line_no}: [{e.title}]({e.target})"
                for e in result.beyond_budget
            ),
            "",
        ]
    return lines


def _index_only_section(result: MemoryIndexResult) -> list[str]:
    if not result.index_only:
        return [
            "_None — every distinctive fact in an entry's title or hook is also "
            "in the file it links to, so shortening one cannot destroy it._",
            "",
        ]
    return [
        "Each fact below exists **only in the index entry**. Shortening that "
        "line destroys it, and nothing will warn you. Resolve each one BEFORE "
        "trimming — but read both sides first: the fix is to migrate the fact "
        "into the topic file when the index is right, or to correct the hook "
        "when the topic file already supersedes it (a hook claiming CI green at "
        "`3adff36` against a file saying `c2cecd7` was the staler of the two).",
        "",
        *_findings_table(result.index_only),
    ]


def render_report(result: MemoryIndexResult) -> str:
    """A markdown report: the budget, then what a trim would cost."""
    lines = [
        "# Memory index — curation check",
        "",
        *_budget_section(result),
        "## 🚨 Index-only facts (a trim would destroy these)",
        "",
        *_index_only_section(result),
    ]
    if result.unparsed:
        lines += [
            "## 🚨 Unreadable entries (skipped by every check above)",
            "",
            "These look like index entries but do not match "
            "`- [Title](file.md) — hook`, so nothing above examined them: their "
            "facts were never compared and their links were never resolved. Fix "
            "the line — usually a missing `—` separator — and re-run, or the "
            "clean result above is only true of the lines it could read.",
            "",
            *(f"- line {n}: `{line}`" for n, line in result.unparsed),
            "",
        ]
    if result.broken:
        lines += [
            "## Broken links (entry points at a file that does not exist)",
            "",
            *(f"- line {e.line_no}: [{e.title}]({e.target})" for e in result.broken),
            "",
        ]
    if result.elsewhere:
        lines += [
            "## Facts filed under a different memory (informational)",
            "",
            "Safe to trim — the fact survives elsewhere. Worth a look only if "
            "the hook is pointing at the wrong file.",
            "",
            *_findings_table(result.elsewhere),
        ]
    if result.orphans:
        lines += [
            "## Unindexed memories (informational)",
            "",
            "These files exist but no index entry links them. Nothing is lost, "
            "but an unindexed memory is one Claude has no reason to open.",
            "",
            *(f"- `{name}`" for name in result.orphans),
            "",
        ]
    lines += [
        "---",
        "",
        "Curation order is **verify → migrate/correct → THEN shorten**. Before "
        "deleting a memory, run `--refs <name>` — a citation from another "
        "memory, or a live fact inside an otherwise-archived one, is the same "
        "silent loss by a different route. See "
        "`.claude/skills/memory-index-curation/SKILL.md`.",
    ]
    return "\n".join(lines) + "\n"


def render_refs(name: str, refs: list[str], *, known: bool) -> str:
    """The inbound-citation answer for ``--refs``."""
    lines = [f"# Inbound refs — `{name}`", ""]
    if not known:
        lines += [
            f"`{name}` is not a memory file in this project's memory directory.",
            "",
        ]
    if refs:
        lines += [
            f"**{len(refs)}** memory file(s) cite it. Repoint or absorb each "
            "before deleting — and re-read the file itself for any live fact "
            "that would go with it:",
            "",
            *(f"- `{r}`" for r in refs),
        ]
    else:
        lines += [
            "_No inbound citations._ Still re-read the file before deleting: an "
            "archived memory can hold a fact that is still true.",
        ]
    return "\n".join(lines) + "\n"


def memory_index_main(
    project_root: Path, *, output: Path | None = None, refs: str | None = None
) -> int:
    """Check the memory index; report to stdout or ``output``.

    Returns 1 when a trim would destroy a fact (index-only), when an entry links
    nowhere, or when entries have fallen past the auto-load cutoff — i.e. only
    for the silent-loss cases. ``--refs`` is a query and always returns 0.
    """
    directory = memory_dir(project_root)
    if not directory.is_dir():
        sys.stdout.write(
            f"memory-index: no memory directory at {directory} "
            "(set CLAUDE_CONFIG_DIR if your Claude config lives elsewhere)\n"
        )
        return 0
    files = load_memories(directory)
    if refs is not None:
        name = refs if refs.endswith(".md") else f"{refs}.md"
        sys.stdout.write(
            render_refs(name, inbound_refs(name, files), known=name in files)
        )
        return 0
    index = directory / _MEMORY_INDEX
    if not index.is_file():
        sys.stdout.write(f"memory-index: no {_MEMORY_INDEX} in {directory}\n")
        return 0
    result = audit_index(index.read_text(errors="replace"), files)
    text = render_report(result)
    if output is None:
        sys.stdout.write(text)
    else:
        dest = output if output.is_absolute() else project_root / output
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        sys.stdout.write(
            f"memory-index: wrote {dest} ({result.lines} lines, {result.size:,} B, "
            f"{len(result.index_only)} index-only, {len(result.broken)} broken)\n"
        )
    return 0 if result.ok else 1
