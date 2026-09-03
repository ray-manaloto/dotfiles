# Copyright (c) 2026 Raymond Manaloto
"""Tests for the rule registry (#918).

Covers the three-way `load_class` partition (scoped / eager / malformed),
C2's real-repo agreement with `instructions_report.scoped_rules_on_disk`
(both a synthetic-corpus check and the two swallow-divergence control arms),
C2b's real-corpus three-way tripwire against
`kb_setup.md_budget.has_paths_frontmatter`, C5's heading-anchored eager-reason
extraction (incl. its fence and setext hazards), C6's inject set, and C1's
traversal/path-spelling parity.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import instructions_report as report
from dotfiles_setup import rule_registry as registry
from kb_setup.md_budget import has_paths_frontmatter

REPO_ROOT = Path(__file__).parent.parent
REAL_RULES_DIR = REPO_ROOT / ".claude" / "rules"


def _write_rule(
    rules_dir: Path,
    name: str,
    *,
    paths: list[str] | None,
    eof_frontmatter: bool = False,
) -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)
    if paths is None:
        body = f"# {name}\n\nno frontmatter.\n"
    elif eof_frontmatter:
        globs = "\n".join(f'  - "{g}"' for g in paths)
        body = f"---\npaths:\n{globs}\n---"
    else:
        globs = "\n".join(f'  - "{g}"' for g in paths)
        body = f"---\npaths:\n{globs}\n---\n\n# {name}\n\nscoped rule body.\n"
    (rules_dir / f"{name}.md").write_text(body, encoding="utf-8")


# --------------------------------------------------------------------------
# C4 — three-way partition basics
# --------------------------------------------------------------------------


def test_scoped_record_carries_globs(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "scoped-a", paths=["hk.pkl", "**/CLAUDE.md"])
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("scoped-a")
    assert record is not None
    assert record.load_class == "scoped"
    assert record.globs == ("hk.pkl", "**/CLAUDE.md")
    assert record.eager_reason is None
    assert record.eager_reason_heading is None
    assert record.malformed_detail is None


def test_no_frontmatter_is_eager_not_malformed(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "plain", paths=None)
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("plain")
    assert record is not None
    assert record.load_class == "eager"
    assert record.globs == ()
    assert record.malformed_detail is None


def test_frontmatter_without_paths_key_is_eager(tmp_path: Path) -> None:
    """C4: frontmatter that parses but lacks `paths` is eager, not malformed."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "other-frontmatter.md").write_text(
        "---\ntitle: something\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("other-frontmatter")
    assert record is not None
    assert record.load_class == "eager"
    assert record.malformed_detail is None


def test_paths_not_a_list_is_eager_not_malformed(tmp_path: Path) -> None:
    """C4: `paths:` present but not a list — still eager, never malformed."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "string-paths.md").write_text(
        "---\npaths: not-a-list\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("string-paths")
    assert record is not None
    assert record.load_class == "eager"
    assert record.globs == ()
    assert record.malformed_detail is None


def test_eof_terminated_frontmatter_still_scoped(tmp_path: Path) -> None:
    """C4: matches `instructions_report.py:59`'s tolerated EOF-terminated shape."""
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "eof-rule", paths=["hk.pkl"], eof_frontmatter=True)
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("eof-rule")
    assert record is not None
    assert record.load_class == "scoped"
    assert record.globs == ("hk.pkl",)


def test_load_class_partition_is_exhaustive_and_exclusive(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "scoped-a", paths=["hk.pkl"])
    _write_rule(rules_dir, "eager-a", paths=None)
    (rules_dir / "malformed-a.md").write_text(
        "---\npaths: [unterminated\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    assert len(reg.records) == 3
    classes = {r.load_class for r in reg.records}
    assert classes <= {"scoped", "eager", "malformed"}
    for record in reg.records:
        assert record.load_class in {"scoped", "eager", "malformed"}


# --------------------------------------------------------------------------
# C3 — both swallows must become malformed records, never silently dropped
# --------------------------------------------------------------------------


def test_unparsable_frontmatter_is_malformed_with_detail(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "bad-yaml.md").write_text(
        "---\npaths: [unterminated\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("bad-yaml")
    assert record is not None
    assert record.load_class == "malformed"
    assert record.malformed_detail
    assert record.globs == ()


def test_unreadable_file_is_malformed_with_detail(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("running as root: file mode has no read-permission effect")
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    target = rules_dir / "unreadable.md"
    target.write_text("---\npaths:\n  - hk.pkl\n---\n\nbody\n", encoding="utf-8")
    target.chmod(0o000)
    try:
        reg = registry.build_registry(rules_dir)
    finally:
        target.chmod(0o644)
    record = reg.by_id("unreadable")
    assert record is not None
    assert record.load_class == "malformed"
    assert record.malformed_detail


# --------------------------------------------------------------------------
# C2 — the registry-vs-scoped_rules_on_disk agreement is ASSERTED
# --------------------------------------------------------------------------


def test_scoped_agreement_against_real_repo() -> None:
    """C2 first bullet: set-equality against the live function, not a hardcoded list.

    This is strictly stronger than pinning filenames — it survives a rule
    being added or scoped without a test edit, and it is what closes the
    class #917 hit: two parsers of the same frontmatter silently disagreeing
    on path spelling.
    """
    reg = registry.build_registry(REAL_RULES_DIR)
    registry_scoped = {r.path for r in reg.records if r.load_class == "scoped"}
    disk_scoped = set(report.scoped_rules_on_disk(REAL_RULES_DIR))
    assert registry_scoped == disk_scoped


def test_diverges_from_scoped_rules_on_disk_on_unparsable_frontmatter(
    tmp_path: Path,
) -> None:
    """C2 second bullet: the control arm proving the swallow is actually fixed.

    `scoped_rules_on_disk` drops this file via `except yaml.YAMLError:
    continue`; the registry must record it as `malformed` instead. A test
    that only ever shows agreement cannot distinguish a working registry
    from a copy of the old function.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "bad-yaml.md").write_text(
        "---\npaths: [unterminated\n---\n\nbody\n", encoding="utf-8"
    )
    disk_scoped = set(report.scoped_rules_on_disk(rules_dir))
    assert ".claude/rules/bad-yaml.md" not in disk_scoped

    reg = registry.build_registry(rules_dir)
    record = reg.by_id("bad-yaml")
    assert record is not None
    assert record.load_class == "malformed"


def test_diverges_from_scoped_rules_on_disk_on_unreadable_file(
    tmp_path: Path,
) -> None:
    """C2 third bullet: the same divergence, second arm — an OSError swallow."""
    if os.geteuid() == 0:
        pytest.skip("running as root: file mode has no read-permission effect")
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    target = rules_dir / "unreadable.md"
    target.write_text("---\npaths:\n  - hk.pkl\n---\n\nbody\n", encoding="utf-8")
    target.chmod(0o000)
    try:
        disk_scoped = set(report.scoped_rules_on_disk(rules_dir))
        assert ".claude/rules/unreadable.md" not in disk_scoped

        reg = registry.build_registry(rules_dir)
    finally:
        target.chmod(0o644)
    record = reg.by_id("unreadable")
    assert record is not None
    assert record.load_class == "malformed"


# --------------------------------------------------------------------------
# C2b — the third classifier is a tripwire, never pinned as a contract
# --------------------------------------------------------------------------


def test_three_classifiers_agree_on_the_real_corpus() -> None:
    """A live tripwire, not a frozen contract (C2b).

    If this fails, the corpus moved under us — someone added a rule with
    `paths: "a-string"` or a typo'd frontmatter block — and that is a
    finding to report, not a reason to adjust this test. Encoding the known
    synthetic divergence as expected behaviour here would mean the correct
    upstream fix (reconciling all three) breaks this suite, which is the
    exact trap #917 hit.
    """
    reg = registry.build_registry(REAL_RULES_DIR)
    registry_scoped = {r.path for r in reg.records if r.load_class == "scoped"}
    disk_scoped = set(report.scoped_rules_on_disk(REAL_RULES_DIR))

    md_budget_scoped = set()
    for path in sorted(REAL_RULES_DIR.rglob("*.md", recurse_symlinks=True)):
        rel = str(path.relative_to(REAL_RULES_DIR.parent.parent))
        raw = path.read_text(encoding="utf-8")
        if has_paths_frontmatter(raw):
            md_budget_scoped.add(rel)

    assert registry_scoped == disk_scoped == md_budget_scoped
    assert registry_scoped == {
        ".claude/rules/ci-local-parity.md",
        ".claude/rules/md-size-budgets.md",
    }
    assert not any(r.load_class == "malformed" for r in reg.records)


# --------------------------------------------------------------------------
# C5 — heading-anchored eager reason only
# --------------------------------------------------------------------------


def test_eager_reason_extracted_from_qualifying_heading(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "eager-with-reason.md").write_text(
        "# Some Rule\n\n"
        "Some intro text.\n\n"
        "## Why this rule is eager (never `paths:`-scoped)\n\n"
        "Reason body line one.\n"
        "Reason body line two.\n\n"
        "## Applies to\n\n"
        "Everything.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("eager-with-reason")
    assert record is not None
    assert record.load_class == "eager"
    assert record.eager_reason_heading == (
        "## Why this rule is eager (never `paths:`-scoped)"
    )
    assert record.eager_reason == "Reason body line one.\nReason body line two."


def test_why_this_rule_exists_heading_does_not_qualify(tmp_path: Path) -> None:
    """C5: content-reason headings are explicitly excluded — not a false positive."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "content-reason-only.md").write_text(
        "# Some Rule\n\n## Why this rule exists\n\nBecause reasons.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("content-reason-only")
    assert record is not None
    assert record.load_class == "eager"
    assert record.eager_reason is None
    assert record.eager_reason_heading is None


def test_eager_reason_section_stops_at_same_level_heading(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "sectioned.md").write_text(
        "# Rule\n\n"
        "## Why this rule cannot be `paths:`-scoped\n\n"
        "Body content.\n\n"
        "## Next Section\n\n"
        "Not part of the reason.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("sectioned")
    assert record is not None
    assert record.eager_reason == "Body content."


def test_fenced_heading_lookalike_is_not_treated_as_heading(tmp_path: Path) -> None:
    """C5 fence hazard: a bash comment inside a fence must not truncate the body."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "fenced.md").write_text(
        "# Rule\n\n"
        "## Why this rule is eager (never `paths:`-scoped)\n\n"
        "Before the fence.\n\n"
        "```bash\n"
        "## this looks like a heading but is a bash comment\n"
        "echo hi\n"
        "```\n\n"
        "After the fence.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("fenced")
    assert record is not None
    assert record.eager_reason is not None
    assert "Before the fence." in record.eager_reason
    assert "After the fence." in record.eager_reason
    assert "this looks like a heading" in record.eager_reason


def test_setext_frontmatter_boundary_is_not_a_phantom_heading(tmp_path: Path) -> None:
    """C5 setext hazard: the closing `---` of frontmatter must not be read as an H2."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "scoped-with-body.md").write_text(
        "---\npaths:\n  - hk.pkl\n---\n\n"
        "# Scoped Rule\n\n"
        "## Why this rule is eager (never `paths:`-scoped)\n\n"
        "This text should never be reached for a scoped rule.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("scoped-with-body")
    assert record is not None
    # Scoped rules never carry an eager reason, by construction (C4).
    assert record.load_class == "scoped"
    assert record.eager_reason is None
    assert record.eager_reason_heading is None


def test_real_corpus_eager_reason_qualifying_headings() -> None:
    """Round-trip fixture pinned by the spec (C5).

    Named explicitly per C5's "do not assert a bare count" instruction.
    """
    reg = registry.build_registry(REAL_RULES_DIR)
    qualifying = {r.path for r in reg.records if r.eager_reason_heading is not None}
    assert qualifying == {
        ".claude/rules/clean-git-state.md",
        ".claude/rules/zero-skip-policy.md",
        ".claude/rules/agent-artifact-conventions.md",
    }


def test_real_corpus_known_non_qualifying_eager_rules() -> None:
    """C5: known-and-accepted non-detections — no blockquote/prose rescue."""
    reg = registry.build_registry(REAL_RULES_DIR)
    for rule_id in ("ai-cli-invocation", "clarify-before-acting"):
        record = reg.by_id(rule_id)
        assert record is not None
        assert record.load_class == "eager"
        assert record.eager_reason is None
        assert record.eager_reason_heading is None


# --------------------------------------------------------------------------
# C6 — inject set
# --------------------------------------------------------------------------


def test_inject_true_only_for_seeded_pilot_rules() -> None:
    reg = registry.build_registry(REAL_RULES_DIR)
    injected = {r.path for r in reg.records if r.inject}
    assert injected == {
        ".claude/rules/ci-local-parity.md",
        ".claude/rules/md-size-budgets.md",
    }


def test_inject_false_for_non_seeded_rule(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "not-in-inject-set", paths=["hk.pkl"])
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("not-in-inject-set")
    assert record is not None
    assert record.inject is False


# --------------------------------------------------------------------------
# C1 — traversal and path spelling, mirroring instructions_report's own tests
# --------------------------------------------------------------------------


def test_recurses_into_nested_subdirs(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "top-level", paths=["hk.pkl"])
    nested = rules_dir / "shared"
    _write_rule(nested, "nested-rule", paths=["mise.toml"])
    reg = registry.build_registry(rules_dir)
    paths = {r.path for r in reg.records}
    assert ".claude/rules/top-level.md" in paths
    assert ".claude/rules/shared/nested-rule.md" in paths


def test_recurses_into_symlinked_subdirs(tmp_path: Path) -> None:
    """S3 parity: `Path.rglob` defaults `recurse_symlinks=False` on 3.13+."""
    real_target = tmp_path / "elsewhere"
    real_target.mkdir()
    _write_rule(real_target, "shared-rule", paths=["mise.toml"])
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "shared").symlink_to(real_target, target_is_directory=True)
    reg = registry.build_registry(rules_dir)
    paths = {r.path for r in reg.records}
    assert ".claude/rules/shared/shared-rule.md" in paths


def test_records_sorted_by_path(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "zzz-last", paths=None)
    _write_rule(rules_dir, "aaa-first", paths=None)
    reg = registry.build_registry(rules_dir)
    paths = [r.path for r in reg.records]
    assert paths == sorted(paths)


def test_rule_id_matches_declared_rules_stem_spelling() -> None:
    """C6b: same `.stem` spelling as `doc_refs._declared_rules`."""
    reg = registry.build_registry(REAL_RULES_DIR)
    declared = {p.stem for p in REAL_RULES_DIR.glob("*.md")}
    non_nested_ids = {
        r.rule_id
        for r in reg.records
        if r.path.count("/") == 2  # ".claude/rules/<name>.md"
    }
    assert non_nested_ids == declared
