"""Tests for `dotfiles_setup.lock_refresh` — the stage/collect helpers behind
the CI lock-refresh job (#160 T8).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles_setup.lock_refresh import (
    _merge_shared_tools,
    collect_system_lock,
    merged_system_config_tools,
    pinned_mise_version,
    stage_system_lock_dir,
)

_SYSTEM_TOML = '[tools]\n"conda:git" = "latest"\n\n[settings]\nexperimental = true\n'
_SHARED_TOML = '[tools]\nhk = "1.46.0"\n'
_RUNTIME_TOML = '[tools]\nbats = "latest"\n'
_LOCK = '[[tools."conda:git"]]\nversion = "2.0"\n\n[[tools.hk]]\nversion = "1.46.0"\n'
_RUNTIME_LOCK = '[[tools.bats]]\nversion = "1.12.0"\n'


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
    (repo / ".devcontainer" / "mise-runtime.toml").write_text(_RUNTIME_TOML)
    (repo / ".devcontainer" / "mise-runtime.lock").write_text(_RUNTIME_LOCK)
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


def test_stage_merges_configs_and_returns_version(tmp_path: Path) -> None:
    import tomllib

    repo = _mini_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    assert stage_system_lock_dir(repo, stage) == "2026.7.0"
    # The staged project config is ONE merged file: a conf.d copy would put
    # the shared tools in a different config dir and mise would lock them
    # into a separate lockfile (empirically verified — see module docstring).
    merged = tomllib.loads((stage / "mise.toml").read_text())
    assert set(merged["tools"]) == {"conda:git", "hk"}
    assert (stage / "mise.runtime.toml").read_text() == _RUNTIME_TOML
    assert (stage / "mise.runtime.lock").read_text() == _RUNTIME_LOCK
    assert (stage / "mise.lock").read_text() == _LOCK


def test_merge_shared_tools_requires_splice_points() -> None:
    import pytest as _pytest

    with _pytest.raises(ValueError, match="shared.toml"):
        _merge_shared_tools(_SYSTEM_TOML, "[settings]\nx = 1\n")
    with _pytest.raises(ValueError, match="mise-system.toml"):
        _merge_shared_tools("[settings]\nx = 1\n", _SHARED_TOML)


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
