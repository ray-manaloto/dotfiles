"""Tests for the autofix artifact applier (dotfiles_setup.autofix)."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import autofix


def _payload(additions: list[dict[str, str]], **extra: object) -> str:
    return json.dumps({"version": 1, "changes": {"additions": additions, **extra}})


def test_applies_additions(tmp_path: Path) -> None:
    payload = _payload(
        [{"path": "a/b.txt", "contents": base64.b64encode(b"hello\n").decode()}]
    )
    written = autofix.apply_autofix_artifact(payload, tmp_path)
    assert written == ["a/b.txt"]
    assert (tmp_path / "a/b.txt").read_bytes() == b"hello\n"


def test_rejects_traversal_paths(tmp_path: Path) -> None:
    payload = _payload(
        [{"path": "../evil.txt", "contents": base64.b64encode(b"x").decode()}]
    )
    with pytest.raises(ValueError, match="suspicious"):
        autofix.apply_autofix_artifact(payload, tmp_path)


def test_rejects_absolute_paths(tmp_path: Path) -> None:
    payload = _payload(
        [{"path": "/etc/passwd", "contents": base64.b64encode(b"x").decode()}]
    )
    with pytest.raises(ValueError, match="suspicious"):
        autofix.apply_autofix_artifact(payload, tmp_path)


def test_rejects_unknown_shape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unrecognized"):
        autofix.apply_autofix_artifact(json.dumps({"version": 2}), tmp_path)


def test_refuses_deletions(tmp_path: Path) -> None:
    payload = _payload(
        [{"path": "a.txt", "contents": base64.b64encode(b"x").decode()}],
        deletions=[{"path": "b.txt"}],
    )
    with pytest.raises(ValueError, match="deletions"):
        autofix.apply_autofix_artifact(payload, tmp_path)
