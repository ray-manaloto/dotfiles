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
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import skills_mirror

if TYPE_CHECKING:
    import pytest

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


def test_mutating_a_mirrored_reference_file_makes_check_fail_and_name_it(
    tmp_path: Path,
) -> None:
    """`references/**` is copied verbatim; a drifted copy must be caught.

    Team-lead follow-up (session 2026-09-10): `context7-cli/references/*.md`
    is mirrored today but the original generator only walked `SKILL.md`.
    """
    _write_skill(tmp_path, "claude", "widget", "See references.\n")
    ref_source = tmp_path / ".claude" / "skills" / "widget" / "references" / "setup.md"
    ref_source.parent.mkdir(parents=True, exist_ok=True)
    ref_source.write_text("Run `tool --claude` to set up.\n", encoding="utf-8")

    assert skills_mirror.find_drift(tmp_path) == ["widget"]
    written = skills_mirror.write_mirror(tmp_path)
    assert written == ["widget"]
    assert skills_mirror.find_drift(tmp_path) == []

    # The reference copy is verbatim: a real CLI flag survives untouched.
    ref_dest = tmp_path / ".agents" / "skills" / "widget" / "references" / "setup.md"
    assert ref_dest.read_text(encoding="utf-8") == ref_source.read_text(
        encoding="utf-8"
    )
    assert "--claude" in ref_dest.read_text(encoding="utf-8")

    # Rot: hand-edit the mirrored reference file out from under the source.
    ref_dest.write_text("Run `tool --codex` to set up.\n", encoding="utf-8")
    assert skills_mirror.find_drift(tmp_path) == ["widget"]


def test_graphify_reference_files_are_never_mirrored(tmp_path: Path) -> None:
    _write_skill(tmp_path, "claude", "graphify", "claude body\n")
    ref_source = (
        tmp_path / ".claude" / "skills" / "graphify" / "references" / "query.md"
    )
    ref_source.parent.mkdir(parents=True, exist_ok=True)
    ref_source.write_text("graphify-only reference\n", encoding="utf-8")

    assert skills_mirror.reference_paths(tmp_path) == []
    skills_mirror.write_mirror(tmp_path)
    assert not (
        tmp_path / ".agents" / "skills" / "graphify" / "references" / "query.md"
    ).exists()


# --- real-repo guards -------------------------------------------------------


def test_real_tree_is_drift_free() -> None:
    """F3: never run the WRITER on the real repo — read-only `find_drift`.

    This test used to call `write_mirror(REPO_ROOT)` directly and assert an
    empty result. `write_mirror` is the writer: the instant the real tree
    drifted, running `pytest` would silently rewrite tracked files.
    `find_drift` proves the same "nothing to regenerate" fact without ever
    touching disk.
    """
    drift = skills_mirror.find_drift(REPO_ROOT)
    assert drift == [], f"run `mise run skills-mirror` to fix: {drift}"


def test_context7_cli_references_are_covered_verbatim() -> None:
    """The three real `context7-cli/references/*.md` files stay byte-identical.

    `--claude` at `.claude/skills/context7-cli/references/setup.md` is an
    argument to a real command; the generator must never rewrite it.
    """
    pairs = skills_mirror.reference_paths(REPO_ROOT)
    names = {source.name for source, _ in pairs}
    assert names == {"docs.md", "setup.md", "skills.md"}
    for source, destination in pairs:
        assert "context7-cli" in str(source)
        assert destination.read_bytes() == source.read_bytes()


def test_graphify_references_are_absent_from_reference_paths() -> None:
    managed_skills = {
        source.parent.parent.name
        for source, _ in skills_mirror.reference_paths(REPO_ROOT)
    }
    assert "graphify" not in managed_skills
    assert not (REPO_ROOT / ".agents" / "skills" / "graphify" / "references").exists()


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
    """Assert no PER_FILE pattern has silently gone stale, on the real repo.

    A pattern matching ZERO times means the source moved out from under the
    override — re-derive it, don't widen the match. (Some patterns, like
    `session-handoff` -> `clear-prep`, are deliberately global substring
    rewrites and legitimately match more than once.) This is the same check
    `find_stale_per_file` runs; kept here too so a failure names the exact
    assertion under pytest, without depending on --check's exit code.
    """
    assert skills_mirror.find_stale_per_file(REPO_ROOT) == []


def test_stale_per_file_pattern_fails_check_and_names_the_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F8: a PER_FILE pattern that stops matching must fail `--check`.

    Before this fix, `hk.pkl` had no `test` step and nothing but `pytest`
    ever ran `test_per_file_patterns_each_match_their_rendered_source_at_
    least_once` above — so `mise run lint` and pre-commit could ship a
    silently-stale override. `find_stale_per_file` (and `skills_mirror_main`
    calling it under `--check`) is what makes the hk step itself the
    enforcing site.
    """
    _write_skill(tmp_path, "claude", "widget", "unrelated content\n")
    monkeypatch.setattr(
        skills_mirror,
        "PER_FILE",
        {"widget": (("this pattern never appears", "replacement"),)},
    )
    skills_mirror.write_mirror(tmp_path)
    assert skills_mirror.find_stale_per_file(tmp_path) == ["widget"]
    assert skills_mirror.skills_mirror_main(tmp_path, check=True) == 1


def test_render_leaves_protected_literals_intact() -> None:
    """The real invariant behind the retired `PROTECTED` masking pass (F2).

    Applying `RULES` alone to `oh-my-claudecode` and `code.claude.com`
    already leaves both unchanged — no rule matches either literal's
    lowercase, unspaced "claude" — so a masking pass around them protected
    nothing (proven: emptying `PROTECTED` on the pre-fix module left this
    exact assertion passing). Asserting the outcome directly, with no
    masking step in `render()` at all, is what actually fails the moment a
    future rule addition matches either literal.
    """
    rendered = skills_mirror.render(
        "inspired-by: oh-my-claudecode:sciomc\n\n"
        "See `oh-my-claudecode:sciomc` and code.claude.com.\n",
        "some-unrelated-skill",
    )
    assert "oh-my-claudecode" in rendered
    assert "oh-my-Codex" not in rendered
    assert "oh-my-codex" not in rendered
    assert "code.claude.com" in rendered
    assert "code.Codex.com" not in rendered


def test_render_is_idempotent_across_the_real_skill_corpus() -> None:
    """F4: `render(render(x, s), s) == render(x, s)` for every managed skill.

    Before the fix, `session-handoff` was the sole exception: its
    `PER_FILE` reversion reintroduced a bare `Claude-side` literal, which a
    SECOND render pass then rewrote via `RULES`' `Claude` -> `Codex` rule —
    so re-rendering an already-rendered mirror silently changed it. The
    fixed wording uses `.claude`-side, which no `RULES` entry matches.
    """
    for source, _destination in skills_mirror.mirror_paths(REPO_ROOT):
        skill = source.parent.name
        text = source.read_text(encoding="utf-8")
        once = skills_mirror.render(text, skill)
        twice = skills_mirror.render(once, skill)
        assert twice == once, f"{skill}: render() is not idempotent"


def test_find_drift_reports_an_unmanaged_ghost_skill(tmp_path: Path) -> None:
    """F6: an orphan `.agents/skills/<name>/SKILL.md` must be reported.

    Before this fix, `find_drift` only ever walked `.claude/skills/`
    (`mirror_paths`/`reference_paths`), so a file dropped directly into
    `.agents/skills/` with no `.claude` counterpart — and not `EXEMPT` or
    `CODEX_ONLY` — was invisible to it. `CODEX_ONLY` (`clear-prep`,
    `codex-task-orchestration`) and `EXEMPT` (`graphify`) must still be
    left alone; they are the legitimate cases this check exempts.
    """
    _write_skill(tmp_path, "claude", "widget", "body\n")
    skills_mirror.write_mirror(tmp_path)
    _write_skill(tmp_path, "agents", "ghost-skill", "no .claude source at all\n")
    _write_skill(tmp_path, "agents", "clear-prep", "codex-only, legitimate\n")
    _write_skill(tmp_path, "agents", "graphify", "DELIBERATE STUB\n")
    drift = skills_mirror.find_drift(tmp_path)
    assert drift == ["ghost-skill"]
