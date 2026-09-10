# Copyright (c) 2026 Raymond Manaloto
"""Tests for the .agents/skills mirror generator (dotfiles_setup.skills_mirror).

Two layers, matching test_bash_budget.py's shape: isolated fixture-tree tests
(a throwaway `.claude/skills/`+`.agents/skills/` pair under tmp_path, so both
the pass AND the fail arm of `--check` are exercised without touching the
real repo) and real-repo guards (the real tree must currently be drift-free,
regeneration must be idempotent, and the two named corruptions from the
generator's docstring must stay unproducible).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import skills_mirror

REPO_ROOT = Path(__file__).parent.parent


def _write_skill(root: Path, side: str, name: str, body: str) -> None:
    path = root / f".{side}" / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# --- isolated fixture-tree tests -------------------------------------------


def test_check_returns_zero_on_a_freshly_regenerated_tree(tmp_path: Path) -> None:
    _write_skill(tmp_path, "claude", "widget", "See `.claude/rules/foo.md`.\n")
    assert skills_mirror.find_drift(tmp_path) == ["widget"]
    written = skills_mirror.write_mirror(tmp_path)
    assert written == ["widget"]
    assert skills_mirror.find_drift(tmp_path) == []


def test_check_returns_one_naming_the_skill_after_a_realistic_mutation(
    tmp_path: Path,
) -> None:
    """Rot looks like a DELETED sentence, not a renamed identifier.

    A rename leaves the original as a substring and a substring check would
    no-op (probes-need-a-control-arm.md rule 2).
    """
    source_body = (
        "# Widget\n\n"
        "First sentence carries the real content.\n"
        "Second sentence is the one that will go missing from the mirror.\n"
    )
    _write_skill(tmp_path, "claude", "widget", source_body)
    skills_mirror.write_mirror(tmp_path)
    assert skills_mirror.find_drift(tmp_path) == []

    # Simulate rot: hand-edit the mirror to DROP the second sentence, the way
    # a human mirror falls behind a source edit — never rename a token.
    mirror_path = tmp_path / ".agents" / "skills" / "widget" / "SKILL.md"
    mirror_path.write_text(
        "# Widget\n\nFirst sentence carries the real content.\n",
        encoding="utf-8",
    )
    drifted = skills_mirror.find_drift(tmp_path)
    assert drifted == ["widget"]


def test_render_leaves_oh_my_claudecode_intact() -> None:
    source = "inspired-by: oh-my-claudecode:sciomc\n\nSee `oh-my-claudecode:sciomc`.\n"
    rendered = skills_mirror.render(source, "research-with-verification-gap-fill")
    assert "oh-my-claudecode" in rendered
    assert "oh-my-Codex" not in rendered
    assert "oh-my-codex" not in rendered


def test_graphify_is_exempt_even_though_the_two_copies_differ_wildly(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path, "claude", "graphify", "claude body\n" * 400)
    _write_skill(tmp_path, "agents", "graphify", "DELIBERATE STUB, unrelated body\n")
    assert "graphify" not in [p.name for p, _ in skills_mirror.mirror_paths(tmp_path)]
    assert skills_mirror.find_drift(tmp_path) == []
    assert skills_mirror.write_mirror(tmp_path) == []
    # And the exempt file is untouched — not merely absent from the report.
    stub = (tmp_path / ".agents" / "skills" / "graphify" / "SKILL.md").read_text()
    assert stub == "DELIBERATE STUB, unrelated body\n"


def test_regeneration_is_idempotent(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "claude",
        "widget",
        "See `.claude/skills/other/SKILL.md` and Claude Code itself.\n",
    )
    first = skills_mirror.write_mirror(tmp_path)
    assert first == ["widget"]
    before = (tmp_path / ".agents" / "skills" / "widget" / "SKILL.md").read_bytes()
    second = skills_mirror.write_mirror(tmp_path)
    assert second == []
    after = (tmp_path / ".agents" / "skills" / "widget" / "SKILL.md").read_bytes()
    assert before == after


def test_generator_never_deletes_an_unmanaged_agents_skill(tmp_path: Path) -> None:
    _write_skill(tmp_path, "claude", "widget", "body\n")
    _write_skill(tmp_path, "agents", "clear-prep", "codex-only, no .claude source\n")
    skills_mirror.write_mirror(tmp_path)
    assert (
        tmp_path / ".agents" / "skills" / "clear-prep" / "SKILL.md"
    ).read_text() == "codex-only, no .claude source\n"


def test_claude_rules_and_agents_citations_are_not_rewritten() -> None:
    """Assert paths with no per-platform copy stay untouched.

    `.claude/rules/`, `.claude/agents/` and bare `~/.claude` have no
    per-platform copy — see the module docstring's RESPEC-1 evidence.
    """
    source = (
        "See `.claude/rules/do-not.md` and `.claude/agents/adversarial-critic.md`. "
        "A bare install mutates `~/.claude`.\n"
    )
    rendered = skills_mirror.render(source, "some-unrelated-skill")
    assert ".claude/rules/do-not.md" in rendered
    assert ".claude/agents/adversarial-critic.md" in rendered
    assert "~/.claude" in rendered
    assert ".codex/rules/" not in rendered
    assert ".Codex/" not in rendered


def test_claude_skills_prefix_rewrites_to_the_real_mirror_location() -> None:
    rendered = skills_mirror.render(
        "See `.claude/skills/other/SKILL.md`.\n", "some-unrelated-skill"
    )
    assert rendered == "See `.agents/skills/other/SKILL.md`.\n"


# --- real-repo guards -------------------------------------------------------


def test_real_tree_is_drift_free() -> None:
    drift = skills_mirror.find_drift(REPO_ROOT)
    assert drift == [], f"run `mise run skills-mirror` to fix: {drift}"


def test_real_tree_regeneration_is_a_no_op() -> None:
    assert skills_mirror.write_mirror(REPO_ROOT) == []


def test_exempt_and_codex_only_never_appear_in_mirror_paths() -> None:
    managed = {
        source.parent.name for source, _ in skills_mirror.mirror_paths(REPO_ROOT)
    }
    assert managed.isdisjoint(skills_mirror.EXEMPT)
    assert managed.isdisjoint(skills_mirror.CODEX_ONLY)


def test_codex_only_skills_have_no_claude_source() -> None:
    for name in skills_mirror.CODEX_ONLY:
        assert not (REPO_ROOT / ".claude" / "skills" / name).exists()
        assert (REPO_ROOT / ".agents" / "skills" / name / "SKILL.md").is_file()


def test_graphify_mirror_stays_the_deliberate_stub() -> None:
    stub = (REPO_ROOT / ".agents" / "skills" / "graphify" / "SKILL.md").read_text()
    assert "DELIBERATE STUB" in stub


def test_per_file_patterns_each_match_their_rendered_source_at_least_once() -> None:
    """Assert no PER_FILE pattern has silently gone stale.

    A pattern matching ZERO times means the source moved out from under the
    override — re-derive it, don't widen the match. (Some patterns, like
    `session-handoff` -> `clear-prep`, are deliberately global substring
    rewrites and legitimately match more than once.)
    """
    for skill, rewrites in skills_mirror.PER_FILE.items():
        source_path = REPO_ROOT / ".claude" / "skills" / skill / "SKILL.md"
        if not source_path.is_file():
            continue
        text = source_path.read_text(encoding="utf-8")
        placeholders: dict[str, str] = {}
        for index, literal in enumerate(skills_mirror.PROTECTED):
            placeholder = f"\x00PROTECTED{index}\x00"
            placeholders[placeholder] = literal
            text = text.replace(literal, placeholder)
        for old, new in skills_mirror.RULES:
            text = text.replace(old, new)
        for placeholder, literal in placeholders.items():
            text = text.replace(placeholder, literal)
        for old, _new in rewrites:
            count = text.count(old)
            assert count >= 1, (
                f"{skill}: PER_FILE pattern matched {count} times: {old!r}"
            )
            text = text.replace(old, _new)
