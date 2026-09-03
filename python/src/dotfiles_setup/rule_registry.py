# Copyright (c) 2026 Raymond Manaloto
"""Rule registry: parse `.claude/rules/*.md` into structured records (#918).

Single source of truth **for #916's consumers** — the #927 gate, the #928
write-trigger dispatcher, and the #929-#932 corpus lanes — of what every
instruction rule under `.claude/rules/` IS: its id, its repo-relative path,
its load class, its `paths:` globs when scoped, the stated reason it is
eager when it is not, and whether the write-hook should inject it. Those
tickets read this module instead of re-parsing markdown themselves.

This is deliberately NOT the source of truth for the md-size-budget gate.
That gate runs a THIRD, independent load-class classifier
(`kb_setup.md_budget.has_paths_frontmatter`, in the knowledge-base repo)
which already disagrees with both this registry and
`instructions_report.scoped_rules_on_disk` on some frontmatter shapes (a
`paths:` string, a `paths:` dict, a `paths:` null, or unparsable YAML that
merely contains a `paths:` line). Reconciling the three is tracked by
**issue #951**, not this ticket. `tests/test_rule_registry.py` carries a
live tripwire asserting all three currently agree on the real corpus,
rather than silently letting that agreement rot.

Traversal and path spelling are pinned to match
`instructions_report.scoped_rules_on_disk` exactly (C1) — that function is a
SECOND parser of the same frontmatter, and #917 shipped three independent
bugs that coexisted precisely because nothing asserted the two sides agreed.
`tests/test_rule_registry.py`'s real-repo agreement test is what closes that
class here.

Unlike `scoped_rules_on_disk`, this module never silently drops a rule it
cannot parse or read: malformed frontmatter, an unreadable file, and a file
whose bytes cannot be decoded as UTF-8 (even with a BOM) all become
`load_class == "malformed"` records (C3), carrying the parser's error
message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    #: The three-way partition. A string-typed annotation (via `from
    #: __future__ import annotations`) so this alias, TYPE_CHECKING-only,
    #: costs nothing at runtime — `ty` reads it, `ty check` catches a typo
    #: as an error rather than an always-empty `by_load_class()` result (D3).
    LoadClass = Literal["scoped", "eager", "malformed"]

#: Matches `instructions_report._FRONTMATTER_RE` exactly (C1): a leading
#: frontmatter block, tolerating an EOF-terminated block with no trailing
#: newline (real fixture: `tests/test_instructions_report.py`'s
#: `eof_frontmatter` case).
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)

#: ATX heading line, e.g. "## Why this rule is eager (...)". Matched only
#: OUTSIDE fenced code blocks (a `#`-prefixed bash comment inside a fence
#: must never be mistaken for a heading) and only after the frontmatter
#: block has been stripped — the parser is ATX-only with NO setext
#: detection anywhere in this module, so the real reason to strip
#: frontmatter first is that a `#`-prefixed YAML COMMENT inside the
#: frontmatter block would otherwise be misread as an ATX heading, not any
#: risk from the closing `---` (there is no setext reader to fool).
#: CommonMark permits up to three leading spaces before the `#`s (A3);
#: the regex tolerates that indent so a legitimately-indented heading is
#: never silently invisible to `_find_eager_reason`.
_ATX_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*\S)\s*$")

#: Same fence-detection shape as `doc_refs._doc_lines`: a fenced code block
#: toggles on any line whose stripped form opens a backtick OR tilde fence
#: (CommonMark supports both; nested fence depth is not tracked because
#: markdown fences don't nest, and an unbalanced fence swallowing the rest
#: of the file is real CommonMark behaviour, not a bug to guard against).
_FENCE_RE = re.compile(r"^\s*(```|~~~)")

#: A heading qualifies as an eager-reason anchor iff its lowercased,
#: backtick-stripped text contains one of these substrings — a purely
#: POSITIVE substring match (A2: this is not an exclusion list; there is
#: no code path that excludes anything). A bare "## Why this rule exists"
#: heading (12 rules in the corpus carry it) simply never CONTAINS either
#: marker, so it fails to qualify on its own content, not because it was
#: filtered out. A heading that also asserts eagerness in its own text
#: (e.g. "## Why this rule exists (and is eager)") correctly DOES qualify
#: — that is a heading genuinely asserting its load class, not a case to
#: special-case away.
_EAGER_HEADING_MARKERS = ("eager", "paths:-scoped")

#: The inject set lives here, not in frontmatter. Seeded with the two
#: currently-scoped rules (repo-relative POSIX paths, matching
#: `RuleRecord.path`'s spelling) as the pilot. #916 decision 1 pins
#: `paths:` as the only frontmatter key; do not add a second one to carry
#: this instead.
INJECT_PATHS: frozenset[str] = frozenset(
    {
        ".claude/rules/ci-local-parity.md",
        ".claude/rules/md-size-budgets.md",
    }
)

#: Rules whose eager rationale IS stated in the corpus but NOT in a form
#: `_find_eager_reason`'s heading-anchored matcher can see (C5 forbids a
#: blockquote/prose detector, by operator decision) — so their records
#: report `eager_reason=None` even though a human reading the file would
#: not call them unjustified. Recorded here, keyed by `"<path>:<line>"`,
#: so a future #927 gate can suppress a false "unjustified eager rule"
#: finding for exactly these two instead of either filing a false
#: accusation or silently building the prose detector the operator ruled
#: out. Reconciling the prose into a real heading is #929-#932's debt, not
#: this ticket's.
KNOWN_UNDETECTED_EAGER_REASONS: frozenset[str] = frozenset(
    {
        # "> **EAGER on purpose** — ..." — a leading blockquote.
        ".claude/rules/ai-cli-invocation.md:3",
        # "...and it is why this rule stays eager..." — inline prose.
        ".claude/rules/clarify-before-acting.md:92",
    }
)


@dataclass(frozen=True)
class RuleRecord:
    """One `.claude/rules/*.md` file's parsed identity.

    Field names are pinned — later tickets (#927/#928/#929-#932) read them.

    `globs == () and load_class == "scoped"` is a real, reachable
    combination: a `paths: []` frontmatter block is syntactically a scoped
    rule (isinstance-of-list, matching `scoped_rules_on_disk`'s predicate
    exactly, per C1/C4), but a scoped rule with zero globs can never match
    a written path — almost certainly an authoring mistake. It is already
    distinguishable from every OTHER `globs == ()` case (eager, malformed)
    by `load_class` alone: a consumer that wants to flag this footgun
    checks `load_class == "scoped" and not globs`.
    """

    rule_id: str
    path: str
    load_class: LoadClass
    globs: tuple[str, ...]
    eager_reason: str | None
    eager_reason_heading: str | None
    malformed_detail: str | None
    inject: bool
    #: WHOLE-file byte length as it sits ON DISK (frontmatter included),
    #: `path.stat().st_size` — NOT `len(decoded_text.encode())`, which
    #: would undercount a CRLF-terminated file by one byte per line once
    #: `read_text`'s universal-newline translation has already collapsed
    #: `\r\n` to `\n`. `0` only when the file could not be opened at all
    #: (the `OSError` arm — no bytes were ever read); a file that opened
    #: but failed to DECODE as UTF-8 still reports its real on-disk size.
    body_bytes: int


@dataclass(frozen=True)
class RuleRegistry:
    """The full corpus, sorted by path."""

    records: tuple[RuleRecord, ...]

    def by_id(self, rule_id: str) -> RuleRecord | None:
        """Return the record whose `rule_id` matches, or None.

        Raises `ValueError` on more than one match — e.g. two same-stem
        files in different nested subdirectories, a documented sharing
        mechanism (C1) — rather than silently answering about whichever
        one happens to sort first (D1). Callers that need every match
        should filter `.records` directly.
        """
        matches = [r for r in self.records if r.rule_id == rule_id]
        if len(matches) > 1:
            msg = (
                f"rule_id {rule_id!r} is ambiguous across nested "
                f"subdirectories: {[m.path for m in matches]!r}"
            )
            raise ValueError(msg)
        return matches[0] if matches else None

    def by_load_class(self, load_class: LoadClass) -> tuple[RuleRecord, ...]:
        """Return every record with the given `load_class`."""
        return tuple(r for r in self.records if r.load_class == load_class)


def _strip_frontmatter(text: str) -> tuple[str, re.Match[str] | None]:
    """Return (body-only text, the frontmatter match or None).

    The body starts at the frontmatter match's end so a `#`-prefixed YAML
    comment inside the frontmatter block is never scanned as an ATX
    heading by `_find_eager_reason` (see `_ATX_HEADING_RE`'s docstring).
    """
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return text, None
    return text[match.end() :], match


def _qualifying_eager_heading(heading_text: str) -> bool:
    """C5: heading-anchored only — no blockquote/prose detection."""
    normalized = heading_text.lower().replace("`", "")
    return any(marker in normalized for marker in _EAGER_HEADING_MARKERS)


def _find_eager_reason(body: str) -> tuple[str | None, str | None]:
    """Scan `body` (frontmatter already stripped) for a qualifying ATX heading.

    Returns (heading_line, section_body_text) for the FIRST qualifying
    heading found, or (None, None) if none qualifies. Fenced code blocks are
    tracked and never scanned for headings — `doc_refs._doc_lines` is the
    shape mirrored here. `section_body_text` is normalised to `None` rather
    than `""` when the qualifying heading has no body before the next
    heading (or EOF) — the pinned interface never returns an empty string.
    """
    lines = body.splitlines()
    in_fence = False
    heading_idx: int | None = None
    heading_level = 0
    heading_line: str | None = None
    for idx, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading_match = _ATX_HEADING_RE.match(line)
        if heading_match is None:
            continue
        if heading_idx is None and _qualifying_eager_heading(heading_match.group(2)):
            heading_idx = idx
            heading_level = len(heading_match.group(1))
            heading_line = line.strip()
            continue
        if heading_idx is not None and len(heading_match.group(1)) <= heading_level:
            # A heading of the same or higher level ends the section.
            section = "\n".join(lines[heading_idx + 1 : idx]).strip("\n")
            return heading_line, section or None
    if heading_idx is not None:
        section = "\n".join(lines[heading_idx + 1 :]).strip("\n")
        return heading_line, section or None
    return None, None


def _disk_size(path: Path) -> int:
    """Bytes on disk, or 0 if even `stat` fails."""
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _malformed(
    rule_id: str, rel_path: str, detail: str, *, inject: bool, body_bytes: int
) -> RuleRecord:
    return RuleRecord(
        rule_id=rule_id,
        path=rel_path,
        load_class="malformed",
        globs=(),
        eager_reason=None,
        eager_reason_heading=None,
        malformed_detail=detail,
        inject=inject,
        body_bytes=body_bytes,
    )


class _UnreadableSourceError(Exception):
    """Raised by `_read_source` — carries what a `malformed` record needs."""

    def __init__(self, detail: str, body_bytes: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.body_bytes = body_bytes


def _read_source(path: Path) -> tuple[str, int]:
    r"""Return (decoded text, on-disk byte count), or raise `_UnreadableSourceError`.

    `utf-8-sig` strips a leading UTF-8 BOM if present and behaves exactly
    like `utf-8` otherwise — without it, a BOM'd file's `\A---\n` never
    matches and a genuinely scoped rule silently reports `eager`. This
    deliberately diverges from `scoped_rules_on_disk`, which stays
    BOM-blind (plain `utf-8`); the real corpus has no BOM'd file, so the
    two still agree there, but this registry is the more correct of the
    two on this one shape (see the C2 test's docstring).
    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        # No bytes were readable at all — nothing to measure.
        raise _UnreadableSourceError(str(exc), 0) from exc
    except UnicodeDecodeError as exc:
        # The file WAS opened and read; only decoding failed, so the
        # on-disk byte count is still knowable.
        raise _UnreadableSourceError(str(exc), _disk_size(path)) from exc
    return text, _disk_size(path)


def _build_record(path: Path, rules_dir: Path) -> RuleRecord:
    project_root = rules_dir.parent.parent
    rel_path = str(path.relative_to(project_root))
    rule_id = path.stem
    inject = rel_path in INJECT_PATHS

    try:
        text, body_bytes = _read_source(path)
    except _UnreadableSourceError as exc:
        return _malformed(
            rule_id, rel_path, exc.detail, inject=inject, body_bytes=exc.body_bytes
        )

    body, match = _strip_frontmatter(text)

    load_class: LoadClass = "eager"
    globs: tuple[str, ...] = ()
    eager_reason_heading: str | None = None
    eager_reason: str | None = None

    if match is None:
        # No frontmatter at all — well-formed eager rule (C3), not malformed.
        eager_reason_heading, eager_reason = _find_eager_reason(body)
    else:
        try:
            front = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            return _malformed(
                rule_id, rel_path, str(exc), inject=inject, body_bytes=body_bytes
            )

        if isinstance(front, dict) and isinstance(front.get("paths"), list):
            raw_globs = front["paths"]
            if not all(isinstance(g, str) for g in raw_globs):
                return _malformed(
                    rule_id,
                    rel_path,
                    f"paths: list contains a non-string item: {raw_globs!r}",
                    inject=inject,
                    body_bytes=body_bytes,
                )
            load_class = "scoped"
            globs = tuple(raw_globs)
        else:
            # Frontmatter parsed but has no `paths` list (C4) — including a
            # `paths:` key holding a string, a dict, or a YAML null: eager,
            # not malformed.
            eager_reason_heading, eager_reason = _find_eager_reason(body)

    return RuleRecord(
        rule_id=rule_id,
        path=rel_path,
        load_class=load_class,
        globs=globs,
        eager_reason=eager_reason,
        eager_reason_heading=eager_reason_heading,
        malformed_detail=None,
        inject=inject,
        body_bytes=body_bytes,
    )


def build_registry(rules_dir: Path) -> RuleRegistry:
    """Parse every `.md` under `rules_dir` into a `RuleRegistry`.

    Traversal matches `instructions_report.scoped_rules_on_disk` exactly
    (C1): `rglob("*.md", recurse_symlinks=True)`, symlinks never resolved.

    Raises `NotADirectoryError` if `rules_dir` does not exist or is not a
    directory (A1). `Path.rglob` on a missing path silently yields zero
    matches, so a mistyped `rules_dir` would otherwise be indistinguishable
    from a real corpus that genuinely has no rules — exactly the ambiguity
    this module exists to eliminate for every downstream consumer. This is
    a deliberate DIVERGENCE from `scoped_rules_on_disk`, which stays silent
    here too (`_iter_records`'s sibling check is the pattern followed);
    this module chooses loud because a caller passing the wrong path is a
    caller bug, not absent data.
    """
    if not rules_dir.is_dir():
        msg = f"rules_dir does not exist or is not a directory: {rules_dir}"
        raise NotADirectoryError(msg)
    records = tuple(
        sorted(
            (
                _build_record(path, rules_dir)
                for path in rules_dir.rglob("*.md", recurse_symlinks=True)
            ),
            key=lambda record: record.path,
        )
    )
    return RuleRegistry(records=records)
