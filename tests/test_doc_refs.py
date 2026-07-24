"""Tests for the doc path-reference checker (#160 T13, validation J)."""

from __future__ import annotations

from pathlib import Path

from dotfiles_setup.doc_refs import (
    DOC_PATHSPECS,
    _is_path_candidate,
    _tracked_files,
    find_unresolved_refs,
)

_TOP = frozenset({".devcontainer", ".claude", "python", "tests", "docs", "home"})


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
