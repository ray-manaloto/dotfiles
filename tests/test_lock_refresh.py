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
    coverage_baseline,
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


# --------------------------------------------------------------------------- #
# #648 — platform coverage, the axis a tool-only predicate cannot see
# --------------------------------------------------------------------------- #

# A tool with entries on both platforms, plus the conda section where the
# macOS-regen damage actually lands. Shaped like the real lock, not minimal:
# the failure being guarded is "same tools, fewer platforms", so a fixture with
# one platform could not exhibit it at all (arm the FIXTURE, not just the probe).
_COVERED = (
    '[[tools."conda:git"]]\nversion = "2.0"\n\n'
    '[tools."conda:git"."platforms.linux-x64"]\nchecksum = "sha256:a"\n\n'
    '[tools."conda:git"."platforms.macos-x64"]\nchecksum = "sha256:b"\n\n'
    '[[tools.hk]]\nversion = "1.46.0"\n\n'
    '[tools.hk."platforms.linux-x64"]\nchecksum = "sha256:c"\n\n'
    '[conda-packages.linux-x64.git]\nurl = "https://example.invalid/g"\n'
)
# The 2026-08-08 damage in miniature: every tool still present (so the tool
# check passes), every linux entry gone.
_DARWIN_TRUNCATED = (
    '[[tools."conda:git"]]\nversion = "2.0"\n\n'
    '[tools."conda:git"."platforms.macos-x64"]\nchecksum = "sha256:b"\n\n'
    '[[tools.hk]]\nversion = "1.46.0"\n'
)


def _covered_repo(tmp_path: Path) -> Path:
    repo = _mini_repo(tmp_path)
    (repo / ".devcontainer" / "mise-system.lock").write_text(_COVERED)
    return repo


def test_collect_refuses_a_lock_that_lost_platform_coverage(tmp_path: Path) -> None:
    """#648: the tool count does not move, so only the platform axis sees it."""
    repo = _covered_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    stage_system_lock_dir(repo, stage)
    (stage / "mise.lock").write_text(_DARWIN_TRUNCATED)
    # Control arm for the claim above: the tool-only predicate is SATISFIED by
    # this input, so a passing tool check is not what makes the test green.
    assert merged_system_config_tools(repo) <= set(
        tomllib.loads(_DARWIN_TRUNCATED)["tools"]
    )
    with pytest.raises(ValueError, match="LOST platform coverage"):
        collect_system_lock(repo, stage)
    assert (repo / ".devcontainer" / "mise-system.lock").read_text() == _COVERED


def test_collect_accepts_a_regen_that_kept_coverage(tmp_path: Path) -> None:
    """The pass arm: same platforms, bumped version, is a legitimate regen."""
    repo = _covered_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    stage_system_lock_dir(repo, stage)
    bumped = _COVERED.replace('version = "2.0"', 'version = "2.1"')
    (stage / "mise.lock").write_text(bumped)
    collect_system_lock(repo, stage)
    assert (repo / ".devcontainer" / "mise-system.lock").read_text() == bumped


def test_collect_measures_coverage_after_stripping_provenance(tmp_path: Path) -> None:
    """Compare like with like, or the check measures the stripping instead.

    The committed lock is provenance-stripped; the stage lock is not. Feeding
    the raw stage text to the coverage predicate would be a different string
    on every run for reasons that have nothing to do with coverage.
    """
    repo = _covered_repo(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()
    stage_system_lock_dir(repo, stage)
    with_provenance = _COVERED.replace(
        '[tools.hk."platforms.linux-x64"]\nchecksum = "sha256:c"\n',
        '[tools.hk."platforms.linux-x64"]\nchecksum = "sha256:c"\n'
        'provenance = "github-attestations"\n',
    )
    (stage / "mise.lock").write_text(with_provenance)
    collect_system_lock(repo, stage)
    written = (repo / ".devcontainer" / "mise-system.lock").read_text()
    assert "provenance" not in written


def test_coverage_baseline_prefers_head_over_the_working_tree(tmp_path: Path) -> None:
    """A run that already overwrote the file must not be graded on its own damage.

    Without the HEAD preference the baseline IS the truncated file, so the
    comparison is truncated-vs-truncated and reports no loss.
    """
    repo = _covered_repo(tmp_path)
    # Not a git repo, so `git show HEAD:` fails and the fallback is the file.
    assert coverage_baseline(repo, ".devcontainer/mise-system.lock") == _COVERED
    (repo / ".devcontainer" / "mise-system.lock").write_text(_DARWIN_TRUNCATED)
    assert (
        coverage_baseline(repo, ".devcontainer/mise-system.lock") == _DARWIN_TRUNCATED
    )


def test_coverage_baseline_is_none_only_when_there_is_nothing_to_compare(
    tmp_path: Path,
) -> None:
    repo = _mini_repo(tmp_path)
    assert coverage_baseline(repo, ".devcontainer/does-not-exist.lock") is None
