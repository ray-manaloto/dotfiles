# Copyright (c) 2026 Raymond Manaloto
"""Native mise sidecar integrity, including missing and escaped graph controls."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from dotfiles_setup.lock_sidecars import verify_lock_sidecars

if TYPE_CHECKING:
    from pathlib import Path

_GRAPH_DIGEST = (
    "sha256:dbab12665d98aef021ba64953c61b0ed8a908cfb56a1c01e2fcb4b052b71a2a1"
)


def _graph(tmp_path: Path) -> tuple[Path, Path, Path]:
    graph = tmp_path / ".mise/locks/pypi-yamllint/1.38.0"
    graph.mkdir(parents=True)
    (graph / "uv.lock").write_bytes(b"version = 1\n")
    (graph / "pyproject.toml").write_text('[project]\nname = "yamllint"\n')
    lock = tmp_path / "mise.lock"
    lock.write_text(
        'lockfile_version = 3\n[[tools."pypi:yamllint"]]\n'
        'version = "1.38.0"\n'
        'uv = { path = ".mise/locks/pypi-yamllint/1.38.0", '
        f'digest = "{_GRAPH_DIGEST}" }}\n'
    )
    return lock, graph.parent.parent, graph


def test_a_complete_native_graph_is_accepted(tmp_path: Path) -> None:
    lock, root, graph = _graph(tmp_path)
    verified = verify_lock_sidecars(lock, root, require_format=3)
    assert tuple(item.directory for item in verified) == (graph,)
    assert set(verified[0].files) == {graph / "uv.lock", graph / "pyproject.toml"}


def test_a_changed_graph_or_missing_manifest_is_rejected(tmp_path: Path) -> None:
    lock, root, graph = _graph(tmp_path)
    (graph / "uv.lock").write_text("changed\n")
    with pytest.raises(ValueError, match="digest mismatch"):
        verify_lock_sidecars(lock, root, require_format=3)
    (graph / "uv.lock").write_bytes(b"version = 1\n")
    (graph / "pyproject.toml").unlink()
    with pytest.raises(ValueError, match="incomplete"):
        verify_lock_sidecars(lock, root, require_format=3)


@pytest.mark.parametrize("filename", ["uv.lock", "pyproject.toml"])
def test_a_graph_file_symlink_cannot_escape_the_sidecar_root(
    tmp_path: Path, filename: str
) -> None:
    lock, root, graph = _graph(tmp_path)
    outside = tmp_path / f"outside-{filename}"
    outside.write_bytes((graph / filename).read_bytes())
    (graph / filename).unlink()
    (graph / filename).symlink_to(outside)
    with pytest.raises(ValueError, match="incomplete"):
        verify_lock_sidecars(lock, root, require_format=3)


def test_a_lock_reference_cannot_leave_its_sidecar_root(tmp_path: Path) -> None:
    lock, root, _ = _graph(tmp_path)
    lock.write_text(lock.read_text().replace(".mise/locks/", "../"))
    with pytest.raises(ValueError, match="escapes"):
        verify_lock_sidecars(lock, root, require_format=3)


def test_a_graph_directory_symlink_inside_the_root_is_rejected(tmp_path: Path) -> None:
    lock, root, graph = _graph(tmp_path)
    actual = graph.parent / "actual"
    graph.rename(actual)
    graph.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="contains a symlink"):
        verify_lock_sidecars(lock, root, require_format=3)


def test_version_three_is_required_for_the_migrated_locks(tmp_path: Path) -> None:
    lock, root, _ = _graph(tmp_path)
    lock.write_text(lock.read_text().replace("lockfile_version = 3", ""))
    with pytest.raises(ValueError, match="expected mise lock format 3"):
        verify_lock_sidecars(lock, root, require_format=3)
