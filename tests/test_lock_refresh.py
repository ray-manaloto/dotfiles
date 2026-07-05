"""Tests for `dotfiles_setup.lock_refresh` — the stage/collect helpers behind
the CI lock-refresh job (#160 T8).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles_setup.lock_refresh import (
    collect_system_lock,
    merged_system_config_tools,
    pinned_mise_version,
    stage_system_lock_dir,
)

_SYSTEM_TOML = '[tools]\n"conda:git" = "latest"\n'
_SHARED_TOML = '[tools]\nhk = "1.46.0"\n'
_LOCK = '[[tools."conda:git"]]\nversion = "2.0"\n\n[[tools.hk]]\nversion = "1.46.0"\n'


def _mini_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".devcontainer").mkdir(parents=True)
    (repo / ".config" / "mise" / "conf.d").mkdir(parents=True)
    (repo / ".devcontainer" / "Dockerfile").write_text(
        "FROM ubuntu\nARG MISE_VERSION=2026.7.0\n"
    )
    (repo / ".devcontainer" / "mise-system.toml").write_text(_SYSTEM_TOML)
    (repo / ".config" / "mise" / "conf.d" / "shared.toml").write_text(_SHARED_TOML)
    (repo / ".devcontainer" / "mise-system.lock").write_text(_LOCK)
    return repo


def test_pinned_mise_version_parses_arg(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("ARG FOO=1\nARG MISE_VERSION=2026.7.0\n")
    assert pinned_mise_version(dockerfile) == "2026.7.0"


def test_pinned_mise_version_missing_raises(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM ubuntu\n")
    with pytest.raises(ValueError, match="ARG MISE_VERSION"):
        pinned_mise_version(dockerfile)


def test_stage_copies_project_layout_and_returns_version(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    assert stage_system_lock_dir(repo, stage) == "2026.7.0"
    assert (stage / "mise.toml").read_text() == _SYSTEM_TOML
    assert (
        stage / ".config" / "mise" / "conf.d" / "shared.toml"
    ).read_text() == _SHARED_TOML
    assert (stage / "mise.lock").read_text() == _LOCK


def test_collect_copies_valid_lock_back(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    stage_system_lock_dir(repo, stage)
    regenerated = _LOCK.replace('version = "2.0"', 'version = "2.1"')
    (stage / "mise.lock").write_text(regenerated)
    collect_system_lock(repo, stage)
    assert (repo / ".devcontainer" / "mise-system.lock").read_text() == regenerated


def test_collect_refuses_partial_lock(tmp_path: Path) -> None:
    """A truncated regen (rate limit, interrupt) must never overwrite the
    committed lock."""
    repo = _mini_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    stage_system_lock_dir(repo, stage)
    (stage / "mise.lock").write_text('[[tools.hk]]\nversion = "1.46.0"\n')
    with pytest.raises(ValueError, match="missing tools"):
        collect_system_lock(repo, stage)
    assert (repo / ".devcontainer" / "mise-system.lock").read_text() == _LOCK


def test_merged_system_config_tools_unions_both(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    assert merged_system_config_tools(repo) == {"conda:git", "hk"}
