"""Tests for the doc path-reference checker (#160 T13, validation J)."""

from __future__ import annotations

from pathlib import Path

from dotfiles_setup.doc_refs import _is_path_candidate, find_unresolved_refs

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
