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
`paths:` string, or unparsable YAML that merely contains a `paths:` line).
Reconciling the three is a separate ticket. `tests/test_rule_registry.py`
carries a live tripwire asserting all three currently agree on the real
corpus, rather than silently letting that agreement rot.

Traversal and path spelling are pinned to match
`instructions_report.scoped_rules_on_disk` exactly (C1) — that function is a
SECOND parser of the same frontmatter, and #917 shipped three independent
bugs that coexisted precisely because nothing asserted the two sides agreed.
`tests/test_rule_registry.py`'s real-repo agreement test is what closes that
class here.

Unlike `scoped_rules_on_disk`, this module never silently drops a rule it
cannot parse or read: malformed frontmatter and an unreadable file both
become `load_class == "malformed"` records (C3), carrying the parser's
error message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

#: Matches `instructions_report._FRONTMATTER_RE` exactly (C1): a leading
#: frontmatter block, tolerating an EOF-terminated block with no trailing
#: newline (real fixture: `tests/test_instructions_report.py`'s
#: `eof_frontmatter` case).
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)

#: ATX heading line, e.g. "## Why this rule is eager (...)". Matched only
#: OUTSIDE fenced code blocks (C5's fence hazard) and only after the
#: frontmatter block has been stripped (C5's setext hazard: an unstripped
#: closing `---` reads as a phantom H2 underline).
_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

#: Same fence-detection shape as `doc_refs._doc_lines` (C5): a fenced code
#: block toggles on any line whose stripped form starts with ``` — nested
#: fence depth is not tracked because markdown fences don't nest.
_FENCE_RE = re.compile(r"^\s*```")

#: C5 — a heading qualifies as an eager-reason anchor iff its lowercased,
#: backtick-stripped text contains one of these substrings. Deliberately
#: excludes "why this rule exists" (12 rules in the corpus carry it) —
#: that heading justifies the rule's CONTENT, not its load class.
_EAGER_HEADING_MARKERS = ("eager", "paths:-scoped")

#: C6 — the inject set lives here, not in frontmatter. Seeded with the two
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


@dataclass(frozen=True)
class RuleRecord:
    """One `.claude/rules/*.md` file's parsed identity.

    Field names are pinned — later tickets (#927/#928/#929-#932) read them.
    """

    rule_id: str
    path: str
    load_class: str
    globs: tuple[str, ...]
    eager_reason: str | None
    eager_reason_heading: str | None
    malformed_detail: str | None
    inject: bool


@dataclass(frozen=True)
class RuleRegistry:
    """The full corpus, sorted by path."""

    records: tuple[RuleRecord, ...]

    def by_id(self, rule_id: str) -> RuleRecord | None:
        """Return the record whose `rule_id` matches, or None."""
        for record in self.records:
            if record.rule_id == rule_id:
                return record
        return None

    def by_load_class(self, load_class: str) -> tuple[RuleRecord, ...]:
        """Return every record with the given `load_class`."""
        return tuple(r for r in self.records if r.load_class == load_class)


def _strip_frontmatter(text: str) -> tuple[str, re.Match[str] | None]:
    """Return (body-only text, the frontmatter match or None).

    The body starts at the frontmatter match's end so the closing `---`
    never masquerades as a setext H2 underline (C5).
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
    tracked and never scanned for headings (C5) — `doc_refs._doc_lines` is
    the shape mirrored here.
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
            return heading_line, section
    if heading_idx is not None:
        section = "\n".join(lines[heading_idx + 1 :]).strip("\n")
        return heading_line, section
    return None, None


def _build_record(path: Path, rules_dir: Path) -> RuleRecord:
    project_root = rules_dir.parent.parent
    rel_path = str(path.relative_to(project_root))
    rule_id = path.stem
    inject = rel_path in INJECT_PATHS

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return RuleRecord(
            rule_id=rule_id,
            path=rel_path,
            load_class="malformed",
            globs=(),
            eager_reason=None,
            eager_reason_heading=None,
            malformed_detail=str(exc),
            inject=inject,
        )

    body, match = _strip_frontmatter(text)

    if match is None:
        # No frontmatter at all — well-formed eager rule (C3), not malformed.
        heading, reason = _find_eager_reason(body)
        return RuleRecord(
            rule_id=rule_id,
            path=rel_path,
            load_class="eager",
            globs=(),
            eager_reason=reason,
            eager_reason_heading=heading,
            malformed_detail=None,
            inject=inject,
        )

    try:
        front = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return RuleRecord(
            rule_id=rule_id,
            path=rel_path,
            load_class="malformed",
            globs=(),
            eager_reason=None,
            eager_reason_heading=None,
            malformed_detail=str(exc),
            inject=inject,
        )

    if isinstance(front, dict) and isinstance(front.get("paths"), list):
        return RuleRecord(
            rule_id=rule_id,
            path=rel_path,
            load_class="scoped",
            globs=tuple(front["paths"]),
            eager_reason=None,
            eager_reason_heading=None,
            malformed_detail=None,
            inject=inject,
        )

    # Frontmatter parsed but has no `paths` list (C4): eager, not malformed.
    heading, reason = _find_eager_reason(body)
    return RuleRecord(
        rule_id=rule_id,
        path=rel_path,
        load_class="eager",
        globs=(),
        eager_reason=reason,
        eager_reason_heading=heading,
        malformed_detail=None,
        inject=inject,
    )


def build_registry(rules_dir: Path) -> RuleRegistry:
    """Parse every `.md` under `rules_dir` into a `RuleRegistry`.

    Traversal matches `instructions_report.scoped_rules_on_disk` exactly
    (C1): `rglob("*.md", recurse_symlinks=True)`, symlinks never resolved.
    """
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
