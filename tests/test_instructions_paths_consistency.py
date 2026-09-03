# Copyright (c) 2026 Raymond Manaloto
"""S4: the observer's normalization and the report's scan must agree.

They must agree on how they spell a scoped rule's path. Nothing before this
asserted that `instructions_observer.build_record`'s
normalized `file_path` and `instructions_report.scoped_rules_on_disk`'s
listing describe the SAME rule the SAME way. That single missing contract
is what let S1 and S3 exist independently in the #917 round-2 cold review —
each side's own tests could pass while the two sides silently disagreed,
because neither side's tests ever compared the two spellings directly. This
file is that comparison, for a plain rule, a nested rule, and a symlinked
one — the three shapes the review exercised.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import instructions_observer as obs
from dotfiles_setup import instructions_report as report

_FRONTMATTER = '---\npaths:\n  - "hk.pkl"\n---\n\nbody\n'


def _observer_spelling(project_root: Path, rel_path: str) -> str | None:
    """What the observer would write for `rel_path`, loaded as an absolute path."""
    abs_path = str(project_root / rel_path)
    record = obs.build_record(
        {"file_path": abs_path}, project_root=project_root, now="t"
    )
    return record["file_path"]


def test_paired_paths_plain_rule(tmp_path: Path) -> None:
    project_root = tmp_path
    rules_dir = project_root / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "plain-rule.md").write_text(_FRONTMATTER, encoding="utf-8")

    observer_spelling = _observer_spelling(project_root, ".claude/rules/plain-rule.md")
    report_listing = report.scoped_rules_on_disk(rules_dir)

    assert observer_spelling == ".claude/rules/plain-rule.md"
    assert observer_spelling in report_listing


def test_paired_paths_nested_rule(tmp_path: Path) -> None:
    project_root = tmp_path
    rules_dir = project_root / ".claude" / "rules"
    nested = rules_dir / "nested"
    nested.mkdir(parents=True)
    (nested / "nested-rule.md").write_text(_FRONTMATTER, encoding="utf-8")

    observer_spelling = _observer_spelling(
        project_root, ".claude/rules/nested/nested-rule.md"
    )
    report_listing = report.scoped_rules_on_disk(rules_dir)

    assert observer_spelling == ".claude/rules/nested/nested-rule.md"
    assert observer_spelling in report_listing


def test_paired_paths_symlinked_rule(tmp_path: Path) -> None:
    """The exact S3 scenario.

    A `.claude/rules/` subdir that is physically a symlink to somewhere
    outside the repo tree.
    """
    project_root = tmp_path
    rules_dir = project_root / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    real_target = tmp_path / "elsewhere"
    real_target.mkdir()
    (real_target / "shared-rule.md").write_text(_FRONTMATTER, encoding="utf-8")
    (rules_dir / "shared").symlink_to(real_target, target_is_directory=True)

    observer_spelling = _observer_spelling(
        project_root, ".claude/rules/shared/shared-rule.md"
    )
    report_listing = report.scoped_rules_on_disk(rules_dir)

    assert observer_spelling == ".claude/rules/shared/shared-rule.md"
    assert observer_spelling in report_listing, (observer_spelling, report_listing)


def test_paired_paths_real_repo_scoped_rules(tmp_path: Path) -> None:
    """The two real scoped rules on disk today, driven end to end.

    An absolute path built from THIS repo's own tree, normalized by the
    observer, must be exactly what the report already lists.
    """
    del tmp_path
    project_root = Path(__file__).parent.parent
    rules_dir = project_root / ".claude" / "rules"
    report_listing = report.scoped_rules_on_disk(rules_dir)
    for rel_path in (
        ".claude/rules/ci-local-parity.md",
        ".claude/rules/md-size-budgets.md",
    ):
        observer_spelling = _observer_spelling(project_root, rel_path)
        assert observer_spelling == rel_path
        assert observer_spelling in report_listing
