"""Tests for the doc path-reference checker (#160 T13, validation J)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from dotfiles_setup.doc_refs import (
    DOC_PATHSPECS,
    _is_path_candidate,
    _tracked_files,
    declared_mise_tasks,
    declared_skills,
    find_local_only_refs,
    find_unresolved_refs,
    find_unresolved_skill_refs,
    find_unresolved_task_refs,
)

_TOP = frozenset({".devcontainer", ".claude", "python", "tests", "docs", "home"})
_ROOT = Path(__file__).parent.parent


def test_repo_paths_are_candidates() -> None:
    assert _is_path_candidate(".devcontainer/Dockerfile", _TOP)
    assert _is_path_candidate("mise.toml", _TOP)
    assert _is_path_candidate("ci.yml:93", _TOP)
    assert _is_path_candidate("python/src/dotfiles_setup/lint.py", _TOP)


def test_non_paths_are_not_candidates() -> None:
    # Dotted variables, domains, owner/repo slugs, commands, globs,
    # abbreviations, and extension mentions must all stay out of scope.
    for span in (
        "chezmoi.os",
        "containers.dev/llms.txt",
        "docs.anthropic.com/mcp",
        "jdx/mise",
        "run/exec/stop/rm/build",
        "mise run lint",
        "**/*.md",
        "python/.../p2996_hash.py",
        ".md",
        ".sh.tmpl",
        "--watch",
    ):
        assert not _is_path_candidate(span, _TOP), span


def test_real_tree_has_zero_unresolved_refs() -> None:
    """The repo's own docs must stay reference-clean — this is the gate."""
    unresolved = find_unresolved_refs(Path(__file__).parent.parent)
    assert unresolved == [], [f"{r.doc}:{r.line}: {r.ref}" for r in unresolved]


def test_scope_covers_every_doc_with_real_content() -> None:
    """Pin WHICH files the gate reads, not just that they are clean.

    The zero-unresolved test above passes just as happily when a file is
    silently out of scope, so it cannot detect a coverage hole on its own —
    the control arm this suite's own `tests/AGENTS.md` demands.

    `.claude/CLAUDE.md` is the case that matters: it is the only `CLAUDE.md`
    with real content (the root one is locked byte-exactly to `@AGENTS.md` by
    `claude_md_import_stub`, and every subdir one is that same stub), it is
    stub-EXEMPT so Claude-specific config lives there, and it is where the
    fable-orchestrator trigger sits — the declaration whose absence went
    undetected and opened #354. It was outside `DOC_PATHSPECS` until
    2026-07-24.
    """
    scanned = set(_tracked_files(Path(__file__).parent.parent, DOC_PATHSPECS))
    assert ".claude/CLAUDE.md" in scanned
    assert "AGENTS.md" in scanned
    assert "python/AGENTS.md" in scanned
    # The vendored graphify skill is excluded on purpose (it cites its own
    # generated runtime files); keep that exclusion honest.
    assert ".claude/skills/graphify/SKILL.md" not in scanned


def test_no_doc_ref_resolves_only_on_this_machine() -> None:
    """Fail HERE when a doc cites a gitignored file, not in CI.

    `find_unresolved_refs` accepts a ref via a filesystem stat, so an artifact
    that is present locally and gitignored resolves on a dev box and vanishes
    in a fresh checkout. That is not hypothetical: adding `.claude/CLAUDE.md`
    to `DOC_PATHSPECS` passed every local gate and then failed CI on its
    `graphify-out/graph.json` citation (PR #359) — the exact local/CI
    divergence `.claude/rules/clean-git-state.md` exists to prevent.

    Every such ref must be a justified `_ALLOWED_ABSENT` entry, which is a
    reviewable diff, rather than an accident of one machine's working tree.
    """
    local_only = find_local_only_refs(Path(__file__).parent.parent)
    assert local_only == [], [f"{r.doc}:{r.line}: {r.ref}" for r in local_only]


# ---------------------------------------------------------------------------
# Named-artifact refs (#354 PR 1) — the refs `find_unresolved_refs` cannot see
# ---------------------------------------------------------------------------
#
# The path checker only considers spans that LOOK like a file path: a span
# containing whitespace is disqualified up front (`_NON_PATH_CHARS`), and a
# bare name with no extension and no `/` never becomes a candidate. So
# `mise run <task>` and a skill cited by name are both structurally invisible
# to it — control-armed below, because "the existing gate covers this" is
# exactly the assumption that leaves a declaration unobserved (#354).
#
# The scanners read the doc corpus through `git ls-files`, so a fixture tree
# has to be a git repo with the file staged. `_plant` does both; nothing is
# committed, because the index is what `ls-files` reports.

_MISE_STUB = '[tasks.lint]\nrun = "true"\n'


def _plant(root: Path, name: str, text: str) -> None:
    if not (root / ".git").exists():
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)


def test_task_and_skill_refs_are_invisible_to_the_path_checker() -> None:
    """Control arm: prove the GAP is real before gating it.

    If either of these were already a path candidate, the two scanners below
    would be duplicated coverage dressed up as new coverage.
    """
    assert not _is_path_candidate("mise run lint", _TOP)
    assert not _is_path_candidate("tool-currency-check", _TOP)
    # ...while a genuine path still is, so the probe discriminates.
    assert _is_path_candidate(".claude/skills/mintlify/SKILL.md", _TOP)


def test_declared_mise_tasks_are_read_from_this_repo_only() -> None:
    """Task names come from the repo's own config, never from `mise tasks`.

    Shelling out to mise would resolve against the invoking user's GLOBAL
    config too — this machine's `mise tasks` lists four `update:*` tasks that
    exist in no file in this repo. A doc in this repo must cite a task this
    repo declares, so the binding is the tracked config, not the environment.
    """
    tasks = declared_mise_tasks(_ROOT)
    assert "lint" in tasks
    assert "verify-local" in tasks
    # An alias is a real way to invoke a task: `down` is `stop`, and three
    # docs cite it. Dropping aliases would report those three as broken.
    assert "down" in tasks
    assert "stop" in tasks
    # A task that only ever existed in the user's global mise config.
    assert "update:brew" not in tasks


def test_declared_skills_are_the_directories_on_disk() -> None:
    control = declared_skills(_ROOT)
    assert "tool-currency-check" in control
    assert "graphify" in control
    assert "no-such-skill" not in control


def test_real_tree_has_zero_unresolved_task_refs() -> None:
    """The gate: every `mise run <task>` cited in a doc must be runnable."""
    unresolved = find_unresolved_task_refs(_ROOT)
    assert unresolved == [], [f"{r.doc}:{r.line}: {r.ref}" for r in unresolved]


def test_real_tree_has_zero_unresolved_skill_refs() -> None:
    """The gate: every skill cited by name in a doc must exist."""
    unresolved = find_unresolved_skill_refs(_ROOT)
    assert unresolved == [], [f"{r.doc}:{r.line}: {r.ref}" for r in unresolved]


def test_task_scanner_catches_a_planted_bad_ref(tmp_path: Path) -> None:
    """Arm the FAIL direction on a REALISTIC break.

    The regression this guards is a task being renamed or deleted while the
    docs keep citing the old name — so the fixture cites a name that is not
    declared, which is precisely what a rename leaves behind.
    """
    _plant(tmp_path, "mise.toml", _MISE_STUB)
    _plant(tmp_path, "AGENTS.md", "Run `mise run lint` then `mise run gone-task`.\n")
    found = {r.ref for r in find_unresolved_task_refs(tmp_path)}
    # `lint` IS declared, so it must not be reported — otherwise the scanner
    # is just "everything is broken" and its green runs mean nothing.
    assert found == {"gone-task"}


def test_task_scanner_reads_fenced_blocks_too(tmp_path: Path) -> None:
    """The repo's own Quick Start lists tasks in a ```bash fence, not backticks.

    Scanning only inline spans would leave the single most-read task list in
    the repo unguarded.
    """
    _plant(tmp_path, "mise.toml", _MISE_STUB)
    _plant(tmp_path, "AGENTS.md", "```bash\nmise run lint\nmise run gone-task\n```\n")
    assert [r.ref for r in find_unresolved_task_refs(tmp_path)] == ["gone-task"]


def test_task_scanner_ignores_a_bare_mise_run_mention(tmp_path: Path) -> None:
    """`mise run` with no task name is prose, and the next word is not a task.

    Without this, `mise-tasks-only.md`'s "add a `mise run` task" reports a
    task called `task`. A gate that invents violations gets switched off.
    """
    _plant(tmp_path, "mise.toml", _MISE_STUB)
    _plant(tmp_path, "AGENTS.md", "then add a `mise run` task for it\n")
    assert find_unresolved_task_refs(tmp_path) == []


def test_skill_scanner_catches_a_planted_bad_ref(tmp_path: Path) -> None:
    _plant(tmp_path, "AGENTS.md", "See the `no-such-skill` skill.\n")
    assert [r.ref for r in find_unresolved_skill_refs(tmp_path)] == ["no-such-skill"]


def test_skill_scanner_reads_wikilinks(tmp_path: Path) -> None:
    """`[[name]]` is the other citation form the rules actually use."""
    _plant(tmp_path, "AGENTS.md", "see [[no-such-skill]] for the procedure\n")
    assert [r.ref for r in find_unresolved_skill_refs(tmp_path)] == ["no-such-skill"]


def test_wikilink_resolves_against_rules_as_well_as_skills(tmp_path: Path) -> None:
    """A `[[name]]` legitimately points at either a rule or a skill.

    `[[zero-skip-policy]]` is a RULE. Resolving wikilinks against skills alone
    would report every one of them as broken.
    """
    _plant(tmp_path, ".claude/rules/my-rule.md", "x\n")
    _plant(tmp_path, "AGENTS.md", "see [[my-rule]]\n")
    assert find_unresolved_skill_refs(tmp_path) == []


def test_backticked_wikilink_is_a_syntax_mention_not_a_citation(tmp_path: Path) -> None:
    """`memory-index-curation` writes ``[[wikilink]]`` to NAME the syntax.

    Treating that as a citation would demand a skill literally called
    `wikilink` — a false positive from the live tree, found by running the
    scanner against it before wiring it up.
    """
    _plant(tmp_path, "AGENTS.md", "A `[[wikilink]]` to a deleted memory rots.\n")
    assert find_unresolved_skill_refs(tmp_path) == []


def test_plugin_namespaced_skill_is_out_of_scope(tmp_path: Path) -> None:
    """`plugin:skill` names a PLUGIN's skill, which this repo does not ship.

    Live instance: `oh-my-claudecode:sciomc`. Its presence depends on an
    installed plugin, so a repo-local existence check can only be wrong.
    """
    _plant(tmp_path, "AGENTS.md", "the `oh-my-claudecode:sciomc` skill\n")
    assert find_unresolved_skill_refs(tmp_path) == []
