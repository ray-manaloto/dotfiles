# Copyright (c) 2026 Raymond Manaloto
"""Behavioral contract for single-owner Python dependencies."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.dependency_ownership import audit_dependency_ownership


def _write_project(tmp_path: Path, *, duplicate_graphify: bool) -> None:
    python = tmp_path / "python"
    python.mkdir()
    (python / "pyproject.toml").write_text(
        '[project]\ndependencies = ["graphifyy[all]==0.9.41", "msgspec==0.21.1"]\n'
    )
    graphify_tool = (
        '"pipx:graphifyy" = { version = "0.9.41", extras = ["all"] }\n'
        if duplicate_graphify
        else ""
    )
    (tmp_path / "mise.toml").write_text(
        '[tools]\npython = "3.14"\n'
        + graphify_tool
        + '\n[deps.uv]\nauto = true\ndir = "python"\nrun = "uv sync --locked"\n'
    )


def test_python_dependency_has_one_owner_and_locked_mise_materialization(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path, duplicate_graphify=False)

    result = audit_dependency_ownership(tmp_path)

    assert result.ok
    assert result.duplicate_packages == ()
    assert result.uv_provider_locked


def test_duplicate_python_package_in_mise_is_rejected(tmp_path: Path) -> None:
    _write_project(tmp_path, duplicate_graphify=True)

    result = audit_dependency_ownership(tmp_path)

    assert not result.ok
    assert result.duplicate_packages == ("graphifyy",)


def test_unlocked_mise_uv_provider_is_rejected(tmp_path: Path) -> None:
    _write_project(tmp_path, duplicate_graphify=False)
    mise = tmp_path / "mise.toml"
    mise.write_text(mise.read_text().replace("uv sync --locked", "uv sync"))

    result = audit_dependency_ownership(tmp_path)

    assert not result.ok
    assert not result.uv_provider_locked


def test_repository_dependency_ownership_is_valid() -> None:
    repo_root = Path(__file__).parent.parent

    result = audit_dependency_ownership(repo_root)

    assert result.ok, result
    assert "graphifyy" in result.python_packages
    assert "graphifyy" not in result.mise_python_packages
