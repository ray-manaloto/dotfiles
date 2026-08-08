# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.gcc_sha`."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import gcc_sha
from dotfiles_setup.gcc_sha import (
    SHA256_HEX_LEN,
    RepairResult,
    compute_sha,
    gcc_sha_main,
    parse_pins,
    repair,
    replace_sha,
)

if TYPE_CHECKING:
    from pathlib import Path

DEB = "gcc-latest_17.0.0-20260705git88752b86ff1a.deb"
OLD_SHA = "a" * SHA256_HEX_LEN
NEW_SHA = "b" * SHA256_HEX_LEN


def _seed_dockerfile(tmp_path: Path, *, deb: str = DEB, sha: str = OLD_SHA) -> Path:
    """Write a .devcontainer/Dockerfile with the gcc-latest ARGs."""
    devcontainer = tmp_path / ".devcontainer"
    devcontainer.mkdir(parents=True, exist_ok=True)
    (devcontainer / "Dockerfile").write_text(
        "FROM ubuntu:26.04 AS devcontainer\n"
        "# renovate: datasource=custom.gcc-latest depName=gcc-latest\n"
        f"ARG GCC_LATEST_DEB={deb}\n"
        f"ARG GCC_LATEST_DEB_SHA256={sha}\n"
        'RUN curl -fLOSs "https://kayari.org/gcc-latest/${GCC_LATEST_DEB}"\n',
    )
    return tmp_path


# ──────────────────────────────────────────────────────────────────────
# parse_pins
# ──────────────────────────────────────────────────────────────────────


def test_parse_pins_extracts_deb_and_sha(tmp_path: Path) -> None:
    root = _seed_dockerfile(tmp_path)
    deb, sha = parse_pins((root / ".devcontainer" / "Dockerfile").read_text())
    assert deb == DEB
    assert sha == OLD_SHA


def test_parse_pins_raises_when_deb_missing() -> None:
    text = f"ARG GCC_LATEST_DEB_SHA256={OLD_SHA}\n"
    with pytest.raises(ValueError, match="GCC_LATEST_DEB="):
        parse_pins(text)


def test_parse_pins_raises_when_sha_missing() -> None:
    text = f"ARG GCC_LATEST_DEB={DEB}\n"
    with pytest.raises(ValueError, match="GCC_LATEST_DEB_SHA256"):
        parse_pins(text)


# ──────────────────────────────────────────────────────────────────────
# replace_sha
# ──────────────────────────────────────────────────────────────────────


def test_replace_sha_rewrites_only_the_digest() -> None:
    text = f"ARG GCC_LATEST_DEB={DEB}\nARG GCC_LATEST_DEB_SHA256={OLD_SHA}\n"
    out = replace_sha(text, NEW_SHA)
    assert f"ARG GCC_LATEST_DEB_SHA256={NEW_SHA}" in out
    assert OLD_SHA not in out
    # The filename ARG is untouched.
    assert f"ARG GCC_LATEST_DEB={DEB}" in out


def test_replace_sha_raises_when_arg_missing() -> None:
    with pytest.raises(ValueError, match="expected exactly one"):
        replace_sha("FROM ubuntu:26.04\n", NEW_SHA)


# ──────────────────────────────────────────────────────────────────────
# compute_sha
# ──────────────────────────────────────────────────────────────────────


def test_compute_sha_uses_fetcher_and_returns_digest() -> None:
    seen: list[str] = []

    def fetcher(url: str) -> str:
        seen.append(url)
        return NEW_SHA

    result = compute_sha(DEB, fetcher)
    assert result == NEW_SHA
    assert seen == [f"https://kayari.org/gcc-latest/{DEB}"]


def test_compute_sha_rejects_malformed_digest() -> None:
    with pytest.raises(ValueError, match="lowercase-hex sha256"):
        compute_sha(DEB, lambda _url: "not-a-sha")


# ──────────────────────────────────────────────────────────────────────
# repair
# ──────────────────────────────────────────────────────────────────────


def test_repair_no_change_leaves_file_byte_identical(tmp_path: Path) -> None:
    root = _seed_dockerfile(tmp_path)
    before = (root / ".devcontainer" / "Dockerfile").read_text()
    result = repair(root, fetcher=lambda _url: OLD_SHA)
    assert result.changed is False
    assert result.old_sha == OLD_SHA
    assert result.new_sha == OLD_SHA
    assert (root / ".devcontainer" / "Dockerfile").read_text() == before


def test_repair_rewrites_on_drift(tmp_path: Path) -> None:
    root = _seed_dockerfile(tmp_path)
    result = repair(root, fetcher=lambda _url: NEW_SHA)
    assert result.changed is True
    assert result.old_sha == OLD_SHA
    assert result.new_sha == NEW_SHA
    assert (
        f"ARG GCC_LATEST_DEB_SHA256={NEW_SHA}"
        in (root / ".devcontainer" / "Dockerfile").read_text()
    )


def test_repair_check_mode_detects_drift_without_writing(tmp_path: Path) -> None:
    root = _seed_dockerfile(tmp_path)
    before = (root / ".devcontainer" / "Dockerfile").read_text()
    result = repair(root, fetcher=lambda _url: NEW_SHA, write=False)
    assert result.changed is True
    assert (root / ".devcontainer" / "Dockerfile").read_text() == before


# ──────────────────────────────────────────────────────────────────────
# RepairResult / gcc_sha_main
# ──────────────────────────────────────────────────────────────────────


def test_repair_result_as_json_shape() -> None:
    result = RepairResult(changed=True, deb=DEB, old_sha=OLD_SHA, new_sha=NEW_SHA)
    payload = json.loads(result.as_json())
    assert payload == {
        "changed": True,
        "deb": DEB,
        "old_sha": OLD_SHA,
        "new_sha": NEW_SHA,
    }


def test_gcc_sha_main_check_returns_1_on_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _seed_dockerfile(tmp_path)
    monkeypatch.setattr(gcc_sha, "_default_fetcher", lambda _url: NEW_SHA)
    rc = gcc_sha_main(root, check=True)
    assert rc == 1
    # check mode never mutates.
    assert OLD_SHA in (root / ".devcontainer" / "Dockerfile").read_text()


def test_gcc_sha_main_repair_returns_0_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _seed_dockerfile(tmp_path)
    monkeypatch.setattr(gcc_sha, "_default_fetcher", lambda _url: NEW_SHA)
    rc = gcc_sha_main(root, check=False)
    assert rc == 0
    assert NEW_SHA in (root / ".devcontainer" / "Dockerfile").read_text()
