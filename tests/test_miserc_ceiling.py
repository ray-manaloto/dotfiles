# Copyright (c) 2026 Raymond Manaloto
"""Exercise the shipped mise ceiling with real discovery and a leaking control."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
_MISE_TIMEOUT = 120


@pytest.fixture
def mise_layout(tmp_path: Path) -> tuple[Path, Path]:
    """Mirror a main checkout and its nested Claude Code worktree."""
    main = tmp_path / "main"
    worktree = main / ".claude" / "worktrees" / "wt"
    worktree.mkdir(parents=True)
    shipped_miserc = (REPO_ROOT / ".miserc.toml").read_bytes()
    (main / ".miserc.toml").write_bytes(shipped_miserc)
    (worktree / ".miserc.toml").write_bytes(shipped_miserc)
    (main / "mise.toml").write_text(
        '[tasks.ceiling-from-main]\nrun = "true"\n', encoding="utf-8"
    )
    (worktree / "mise.toml").write_text(
        '[tasks.ceiling-from-wt]\nrun = "true"\n', encoding="utf-8"
    )
    return main, worktree


def _task_info(cwd: Path, main: Path, task: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("MISE_CEILING_PATHS", None)
    env.pop("MISE_IGNORED_CONFIG_PATHS", None)
    env["MISE_TRUSTED_CONFIG_PATHS"] = str(main)
    return subprocess.run(
        ["mise", "tasks", "info", "--json", task],
        cwd=cwd,
        env=env,
        timeout=_MISE_TIMEOUT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_worktree_does_not_inherit_main_checkout_config(
    mise_layout: tuple[Path, Path],
) -> None:
    main, worktree = mise_layout
    inherited = _task_info(worktree, main, "ceiling-from-main")
    assert inherited.returncode != 0, inherited.stdout
    own = _task_info(worktree, main, "ceiling-from-wt")
    assert own.returncode == 0, own.stderr
    assert "Failed to render template in miserc" not in own.stderr


def test_worktree_without_the_line_inherits_main_config(
    mise_layout: tuple[Path, Path],
) -> None:
    main, worktree = mise_layout
    (worktree / ".miserc.toml").unlink()
    inherited = _task_info(worktree, main, "ceiling-from-main")
    assert inherited.returncode == 0, inherited.stderr


def test_main_checkout_keeps_its_own_config(mise_layout: tuple[Path, Path]) -> None:
    main, _worktree = mise_layout
    own = _task_info(main, main, "ceiling-from-main")
    assert own.returncode == 0, own.stderr


def test_ceiling_works_from_a_worktree_subdirectory(
    mise_layout: tuple[Path, Path],
) -> None:
    main, worktree = mise_layout
    subdirectory = worktree / "sub"
    subdirectory.mkdir()
    inherited = _task_info(subdirectory, main, "ceiling-from-main")
    assert inherited.returncode != 0, inherited.stdout
