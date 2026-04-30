"""Tests for `dotfiles_setup.p2996_hash`."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from dotfiles_setup.p2996_hash import (
    HASH_LENGTH,
    HashInputs,
    _extract_bake_variable,
    compute_hash,
    compute_repo_hash,
    gather_inputs,
)


def _stub_inputs(**overrides: str) -> HashInputs:
    base = {
        "clang_p2996_ref": "9ffb96e3ce362289008e14ad2a79a249f58aa90a",
        "base_image": "ubuntu:26.04",
        "platform": "linux/amd64/v2",
        "dockerfile_digest": "a" * 64,
        "bake_digest": "b" * 64,
        "snapshot_digest": "c" * 64,
    }
    base.update(overrides)
    return HashInputs(**base)


def test_hash_is_stable_for_fixed_inputs() -> None:
    inputs = _stub_inputs()
    assert compute_hash(inputs) == compute_hash(inputs)
    assert len(compute_hash(inputs)) == HASH_LENGTH


def test_hash_changes_when_clang_ref_changes() -> None:
    base = _stub_inputs()
    bumped = _stub_inputs(clang_p2996_ref="0000000000000000000000000000000000000000")
    assert compute_hash(base) != compute_hash(bumped)


def test_hash_changes_when_snapshot_digest_changes() -> None:
    base = _stub_inputs()
    bumped = _stub_inputs(snapshot_digest="d" * 64)
    assert compute_hash(base) != compute_hash(bumped)


def test_hash_changes_when_dockerfile_digest_changes() -> None:
    base = _stub_inputs()
    bumped = _stub_inputs(dockerfile_digest="e" * 64)
    assert compute_hash(base) != compute_hash(bumped)


def test_hash_changes_when_platform_changes() -> None:
    base = _stub_inputs()
    bumped = _stub_inputs(platform="linux/arm64")
    assert compute_hash(base) != compute_hash(bumped)


def test_hash_is_lowercase_hex() -> None:
    digest = compute_hash(_stub_inputs())
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)


def test_extract_bake_variable_simple() -> None:
    bake = """
    variable "BASE_IMAGE" {
      default = "ubuntu:26.04"
    }
    """
    assert _extract_bake_variable(bake, "BASE_IMAGE") == "ubuntu:26.04"


def test_extract_bake_variable_with_comment() -> None:
    bake = """
    # Pinned commit SHA for Bloomberg's clang-p2996 fork.
    variable "CLANG_P2996_REF" {
      default = "9ffb96e3ce362289008e14ad2a79a249f58aa90a"
    }
    """
    assert (
        _extract_bake_variable(bake, "CLANG_P2996_REF")
        == "9ffb96e3ce362289008e14ad2a79a249f58aa90a"
    )


def test_extract_bake_variable_missing_raises() -> None:
    bake = 'variable "OTHER" { default = "x" }'
    with pytest.raises(ValueError, match="not found"):
        _extract_bake_variable(bake, "MISSING_VAR")


def test_gather_and_compute_repo_hash_roundtrip(tmp_path: Path) -> None:
    bake = tmp_path / "docker-bake.hcl"
    bake.write_text(
        'variable "BASE_IMAGE" { default = "ubuntu:26.04" }\n'
        'variable "PLATFORM" { default = "linux/amd64/v2" }\n'
        'variable "CLANG_P2996_REF" { default = "abc123" }\n',
    )
    devcontainer = tmp_path / ".devcontainer"
    devcontainer.mkdir()
    (devcontainer / "Dockerfile").write_text("FROM ubuntu:26.04\n")
    (devcontainer / "mise-system-resolved.json").write_text(
        '{"schema_version": 1, "tools": {"conda:cmake": "4.3.2"}}\n',
    )

    inputs = gather_inputs(tmp_path)
    assert inputs.clang_p2996_ref == "abc123"
    assert inputs.base_image == "ubuntu:26.04"
    assert inputs.platform == "linux/amd64/v2"

    digest_a = compute_repo_hash(tmp_path)
    digest_b = compute_repo_hash(tmp_path)
    assert digest_a == digest_b
    assert len(digest_a) == HASH_LENGTH


def test_repo_hash_changes_when_dockerfile_modified(tmp_path: Path) -> None:
    bake = tmp_path / "docker-bake.hcl"
    bake.write_text(
        'variable "BASE_IMAGE" { default = "ubuntu:26.04" }\n'
        'variable "PLATFORM" { default = "linux/amd64/v2" }\n'
        'variable "CLANG_P2996_REF" { default = "abc123" }\n',
    )
    devcontainer = tmp_path / ".devcontainer"
    devcontainer.mkdir()
    dockerfile = devcontainer / "Dockerfile"
    dockerfile.write_text("FROM ubuntu:26.04\n")
    (devcontainer / "mise-system-resolved.json").write_text(
        '{"schema_version": 1, "tools": {}}\n',
    )

    before = compute_repo_hash(tmp_path)
    dockerfile.write_text("FROM ubuntu:26.04\nRUN echo new\n")
    after = compute_repo_hash(tmp_path)
    assert before != after


def test_hash_inputs_rejects_empty_literal() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        _stub_inputs(clang_p2996_ref="")


def test_hash_inputs_rejects_short_digest() -> None:
    with pytest.raises(ValueError, match="64-char"):
        _stub_inputs(dockerfile_digest="a" * 63)


def test_hash_inputs_rejects_uppercase_digest() -> None:
    with pytest.raises(ValueError, match="64-char"):
        _stub_inputs(snapshot_digest="A" * 64)


def test_gather_inputs_missing_dockerfile_raises(tmp_path: Path) -> None:
    bake = tmp_path / "docker-bake.hcl"
    bake.write_text(
        'variable "BASE_IMAGE" { default = "ubuntu:26.04" }\n'
        'variable "PLATFORM" { default = "linux/amd64/v2" }\n'
        'variable "CLANG_P2996_REF" { default = "abc" }\n',
    )
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "mise-system-resolved.json").write_text("{}\n")
    # No Dockerfile created.
    with pytest.raises(FileNotFoundError):
        gather_inputs(tmp_path)


def test_gather_inputs_missing_snapshot_raises(tmp_path: Path) -> None:
    bake = tmp_path / "docker-bake.hcl"
    bake.write_text(
        'variable "BASE_IMAGE" { default = "ubuntu:26.04" }\n'
        'variable "PLATFORM" { default = "linux/amd64/v2" }\n'
        'variable "CLANG_P2996_REF" { default = "abc" }\n',
    )
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "Dockerfile").write_text("FROM ubuntu\n")
    # No snapshot file created.
    with pytest.raises(FileNotFoundError):
        gather_inputs(tmp_path)


def test_gather_inputs_bake_missing_required_var_raises(tmp_path: Path) -> None:
    bake = tmp_path / "docker-bake.hcl"
    bake.write_text('variable "BASE_IMAGE" { default = "ubuntu:26.04" }\n')
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "Dockerfile").write_text("FROM ubuntu\n")
    (tmp_path / ".devcontainer" / "mise-system-resolved.json").write_text("{}\n")
    with pytest.raises(ValueError, match="not found"):
        gather_inputs(tmp_path)


def test_cli_p2996_hash_subcommand_returns_16_char_hex() -> None:
    # Smoke-test the CLI dispatch path that CI consumes via
    # `hash=$(uv run --project python dotfiles-setup p2996-hash)`. A
    # typo in the dispatch table or a refactor that switches to logger
    # output instead of stdout would silently break CI without this.
    result = subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.main", "p2996-hash"],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    output = result.stdout.strip()
    assert len(output) == HASH_LENGTH, (
        f"expected {HASH_LENGTH}-char hex digest from CLI, got {output!r}"
    )
    assert re.fullmatch(r"[0-9a-f]+", output), (
        f"expected lowercase-hex digest from CLI, got {output!r}"
    )
