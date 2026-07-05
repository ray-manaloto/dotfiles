"""Tests for `dotfiles_setup.bootstrap_packages` — the anti-drift guard that
keeps `[bootstrap.packages]` in sync with the Dockerfile's real apt-get list.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from dotfiles_setup.bootstrap_packages import (
    apt_packages_from_bootstrap,
    apt_packages_from_dockerfile,
)

_REPO_ROOT = Path(__file__).parent.parent
_MISE_SYSTEM_TOML = _REPO_ROOT / ".devcontainer" / "mise-system.toml"
_DOCKERFILE = _REPO_ROOT / ".devcontainer" / "Dockerfile"


def test_apt_packages_from_bootstrap_strips_prefix(tmp_path: Path) -> None:
    toml = tmp_path / "mise-system.toml"
    toml.write_text(
        "[bootstrap.packages]\n"
        '"apt:curl" = "latest"\n'
        '"apt:zsh" = "latest"\n'
        '"brew:jq" = "latest"\n'
    )
    assert apt_packages_from_bootstrap(toml) == ["curl", "zsh"]


def test_apt_packages_from_dockerfile_extracts_block(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        textwrap.dedent("""\
        RUN apt-get update && apt-get install -y --no-install-recommends \\
            build-essential \\
            curl \\
            zsh \\
            && rm -rf /var/lib/apt/lists/*
        """)
    )
    assert apt_packages_from_dockerfile(dockerfile) == [
        "build-essential",
        "curl",
        "zsh",
    ]


def test_apt_packages_from_dockerfile_missing_marker_raises(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM ubuntu:26.04\nRUN echo hi\n")
    with pytest.raises(ValueError, match="apt-get install marker not found"):
        apt_packages_from_dockerfile(dockerfile)


def test_bootstrap_packages_match_dockerfile_apt_list() -> None:
    """The declarative [bootstrap.packages] apt set MUST equal the Dockerfile's
    real apt-get install list — neither may drift (#160 T4)."""
    declared = apt_packages_from_bootstrap(_MISE_SYSTEM_TOML)
    installed = apt_packages_from_dockerfile(_DOCKERFILE)
    assert declared == installed, (
        "drift between [bootstrap.packages] and the Dockerfile apt-get list:\n"
        f"  only in [bootstrap.packages]: {sorted(set(declared) - set(installed))}\n"
        f"  only in Dockerfile apt-get:   {sorted(set(installed) - set(declared))}"
    )
