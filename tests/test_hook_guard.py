"""Tests for the PreToolUse mise-tasks-only guard (dotfiles_setup.hook_guard)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import hook_guard


@pytest.mark.parametrize(
    ("command", "redirect_hint"),
    [
        ("npx agnix .", "mise-installed binary"),
        ("cd /tmp && npx cowsay hi", "mise-installed binary"),
        ("chezmoi apply", "devcontainer"),
        ("chezmoi update -v", "devcontainer"),
        ("hk run pre-commit --all --stash none", "mise run lint"),
        ("devcontainer up --workspace-folder .", "mise run up"),
        ("devcontainer build --workspace-folder .", "mise run dev-rebuild"),
        (
            "docker pull ghcr.io/ray-manaloto/dotfiles-devcontainer:dev",
            "mise run sync",
        ),
        ("gh pr create --fill", "mise run ship"),
        ("gh pr merge 42 --squash", "mise run land"),
    ],
)
def test_one_off_commands_denied_with_redirect(
    command: str, redirect_hint: str
) -> None:
    reason = hook_guard.decide(command)
    assert reason is not None
    assert redirect_hint in reason


@pytest.mark.parametrize(
    "command",
    [
        # Diagnostics and reads stay direct.
        "docker ps --filter label=x",
        "gh pr view 172 --json state",
        "gh pr checks 172 --watch",
        "chezmoi diff",
        "chezmoi execute-template < a.tmpl",
        "git status --porcelain",
        # The canonical forms themselves.
        "mise run lint",
        "mise run ship -- --title x",
        "uv run --project python pytest tests/test_pr.py -x -q",
        # The unwrapped form the permission engine hands the hook for the
        # canonical uv pytest command — MUST stay allowed (probe 2026-07-07).
        "pytest tests/ -x -q",
        # Substrings that must NOT false-positive.
        "docker pull ubuntu:24.04",
        "echo 'gh pr merge is wrapped by land'",
        "rg 'npx' docs/",
        "hk validate",
        # Prose mentions inside a commit message (probe 2026-07-07: the
        # unanchored chezmoi rule denied its own documenting commit).
        "git commit -m 'docs: chezmoi apply/update stays devcontainer-only'",
    ],
)
def test_legitimate_commands_allowed(command: str) -> None:
    assert hook_guard.decide(command) is None


def test_pretooluse_emits_deny_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(hook_guard, "_read_command", lambda: "gh pr create")
    assert hook_guard.pretooluse_main() == 0
    out = capsys.readouterr().out
    assert '"permissionDecision": "deny"' in out
    assert "mise run ship" in out


def test_pretooluse_silent_on_allowed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(hook_guard, "_read_command", lambda: "git status")
    assert hook_guard.pretooluse_main() == 0
    assert capsys.readouterr().out == ""
