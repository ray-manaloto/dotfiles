# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.p2996_refresh`."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup.p2996_refresh import (
    GIT_SHA1_LEN,
    RefreshResult,
    fetch_latest_ref,
    read_pinned_ref,
    refresh,
    replace_pinned_ref,
)

if TYPE_CHECKING:
    from pathlib import Path

OLD_SHA = "9ffb96e3ce362289008e14ad2a79a249f58aa90a"
NEW_SHA = "a56e7036fc1dcc8d4325f79230809b6ee678e5f2"


def _seed_bake(tmp_path: Path, ref: str = OLD_SHA) -> Path:
    """Write a docker-bake.hcl whose CLANG_P2996_REF default is `ref`."""
    (tmp_path / "docker-bake.hcl").write_text(
        'variable "BASE_IMAGE" {\n  default = "ubuntu:26.04"\n}\n\n'
        'variable "CLANG_P2996_REF" {\n'
        "  # Pinned commit SHA for Bloomberg's clang-p2996 fork.\n"
        f'  default = "{ref}"\n'
        "}\n",
    )
    return tmp_path


# ──────────────────────────────────────────────────────────────────────
# fetch_latest_ref
# ──────────────────────────────────────────────────────────────────────


def test_fetch_latest_ref_parses_sha_from_ls_remote() -> None:
    def runner(_url: str, _branch: str) -> str:
        return f"{NEW_SHA}\trefs/heads/p2996\n"

    assert fetch_latest_ref(runner) == NEW_SHA


def test_fetch_latest_ref_lowercases_sha() -> None:
    def runner(_url: str, _branch: str) -> str:
        return f"{NEW_SHA.upper()}\trefs/heads/p2996\n"

    assert fetch_latest_ref(runner) == NEW_SHA


def test_fetch_latest_ref_rejects_empty_output() -> None:
    with pytest.raises(ValueError, match="no ref"):
        fetch_latest_ref(lambda _u, _b: "")


def test_fetch_latest_ref_rejects_malformed_sha() -> None:
    with pytest.raises(ValueError, match="SHA-1"):
        fetch_latest_ref(lambda _u, _b: "not-a-sha\trefs/heads/p2996\n")


# ──────────────────────────────────────────────────────────────────────
# read_pinned_ref / replace_pinned_ref
# ──────────────────────────────────────────────────────────────────────


def test_read_pinned_ref(tmp_path: Path) -> None:
    assert read_pinned_ref(_seed_bake(tmp_path)) == OLD_SHA


def test_replace_pinned_ref_swaps_only_the_sha(tmp_path: Path) -> None:
    bake_text = (_seed_bake(tmp_path) / "docker-bake.hcl").read_text()
    new_text = replace_pinned_ref(bake_text, NEW_SHA)
    assert NEW_SHA in new_text
    assert OLD_SHA not in new_text
    # Surrounding HCL (comment, other variable) is preserved.
    assert "ubuntu:26.04" in new_text
    assert "Bloomberg's clang-p2996 fork" in new_text


def test_replace_pinned_ref_is_idempotent_for_same_sha(tmp_path: Path) -> None:
    bake_text = (_seed_bake(tmp_path) / "docker-bake.hcl").read_text()
    assert replace_pinned_ref(bake_text, OLD_SHA) == bake_text


def test_replace_pinned_ref_raises_when_variable_missing() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        replace_pinned_ref('variable "OTHER" { default = "x" }\n', NEW_SHA)


# ──────────────────────────────────────────────────────────────────────
# refresh orchestration
# ──────────────────────────────────────────────────────────────────────


def test_refresh_bumps_and_writes_when_head_advanced(tmp_path: Path) -> None:
    repo = _seed_bake(tmp_path)
    result = refresh(repo, runner=lambda _u, _b: f"{NEW_SHA}\trefs/heads/p2996\n")
    assert result == RefreshResult(changed=True, old_ref=OLD_SHA, new_ref=NEW_SHA)
    assert read_pinned_ref(repo) == NEW_SHA


def test_refresh_is_noop_when_already_latest(tmp_path: Path) -> None:
    repo = _seed_bake(tmp_path)
    before = (repo / "docker-bake.hcl").read_text()
    result = refresh(repo, runner=lambda _u, _b: f"{OLD_SHA}\trefs/heads/p2996\n")
    assert result.changed is False
    # File is left byte-identical so create-pull-request sees no diff.
    assert (repo / "docker-bake.hcl").read_text() == before


def test_refresh_result_as_json_roundtrips() -> None:
    result = RefreshResult(changed=True, old_ref=OLD_SHA, new_ref=NEW_SHA)
    parsed = json.loads(result.as_json())
    assert parsed == {"changed": True, "old_ref": OLD_SHA, "new_ref": NEW_SHA}


def test_old_and_new_shas_are_full_length() -> None:
    assert len(OLD_SHA) == GIT_SHA1_LEN
    assert len(NEW_SHA) == GIT_SHA1_LEN
