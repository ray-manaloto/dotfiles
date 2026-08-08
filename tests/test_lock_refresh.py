# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.lock_refresh`.

The stage/collect helpers behind the CI lock-refresh job (#160 T8).
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup.lock_refresh import (
    _merge_shared_tools,
    collect_system_lock,
    merged_system_config_tools,
    pinned_mise_version,
    stage_system_lock_dir,
    strip_provenance,
)

if TYPE_CHECKING:
    from pathlib import Path

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
    with pytest.raises(ValueError, match=r"shared\.toml"):
        _merge_shared_tools(_SYSTEM_TOML, "[settings]\nx = 1\n")
    with pytest.raises(ValueError, match=r"mise-system\.toml"):
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
    """A truncated regen must never overwrite the committed lock.

    Rate-limit or interrupt truncation is the failure this guards against.
    """
    repo = _mini_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    stage_system_lock_dir(repo, stage)
    (stage / "mise.lock").write_text('[[tools.hk]]\nversion = "1.46.0"\n')
    with pytest.raises(ValueError, match="missing tools"):
        collect_system_lock(repo, stage)
    assert (repo / ".devcontainer" / "mise-system.lock").read_text() == _LOCK


def test_strip_provenance_removes_keys_and_tables() -> None:
    """Provenance keys AND provenance sub-tables must both be dropped.

    The image disables attestation verification, and mise's locked
    install fail-closes on a lock that requires it (jdx/mise#10694).
    """
    lock = (
        '[[tools.python]]\nversion = "3.14.6"\n\n'
        '[tools.python."platforms.linux-x64"]\n'
        'checksum = "sha256:abc"\n'
        'provenance = "github-attestations"\n\n'
        '[[tools.cosign-tool]]\nversion = "1.0"\n\n'
        '[tools.cosign-tool."platforms.linux-x64"]\n'
        'provenance = "cosign"\n\n'
        '[[tools.ghalint]]\nversion = "1.5.6"\n\n'
        '[tools.ghalint."platforms.linux-x64".provenance.slsa]\n'
        'source_uri = "github.com/x/y"\n\n'
        '[[tools.hk]]\nversion = "1.49.0"\n'
    )
    stripped = strip_provenance(lock)
    parsed = tomllib.loads(stripped)
    assert set(parsed["tools"]) == {"python", "cosign-tool", "ghalint", "hk"}
    assert "provenance" not in stripped
    assert parsed["tools"]["python"][0]["platforms.linux-x64"] == {
        "checksum": "sha256:abc"
    }


def test_collect_strips_provenance(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    stage_system_lock_dir(repo, stage)
    regenerated = _LOCK + 'provenance = "github-attestations"\n'
    (stage / "mise.lock").write_text(regenerated)
    collect_system_lock(repo, stage)
    committed = (repo / ".devcontainer" / "mise-system.lock").read_text()
    assert "provenance" not in committed
    assert tomllib.loads(committed)["tools"].keys() == {"conda:git", "hk"}


def test_merged_system_config_tools_unions_both(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    assert merged_system_config_tools(repo) == {"conda:git", "hk"}
