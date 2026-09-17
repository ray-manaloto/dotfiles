# Copyright (c) 2026 Raymond Manaloto
"""Regression coverage for the devcontainer workspace trust preflight (#1183)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.absolute()
GITCONFIG_TEMPLATE = REPO_ROOT / "home" / "dot_gitconfig.tmpl"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "devcontainer-smoke.sh"
PREFLIGHT_MARKER = "[preflight] git workspace safe.directory"


def test_gitconfig_renders_the_current_chezmoi_working_tree(
    tmp_path: Path,
) -> None:
    source = tmp_path / "alternate-clone-name"
    source.mkdir()

    rendered = subprocess.run(
        [
            "chezmoi",
            f"--source={source}",
            "execute-template",
        ],
        input=GITCONFIG_TEMPLATE.read_text(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    rendered_gitconfig = tmp_path / "rendered.gitconfig"
    rendered_gitconfig.write_text(rendered)

    safe_directories = subprocess.run(
        [
            "git",
            "config",
            "--file",
            str(rendered_gitconfig),
            "--get-all",
            "safe.directory",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert safe_directories == [str(source)]


def test_smoke_fails_before_tier_one_when_git_cannot_open_workspace(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "not-a-git-workspace"
    workspace.mkdir()

    result = subprocess.run(
        ["bash", str(SMOKE_SCRIPT)],
        env={**os.environ, "WORKSPACE_FOLDER": str(workspace)},
        check=False,
        capture_output=True,
        text=True,
    )
    diagnostics = result.stdout + result.stderr

    assert result.returncode == 1
    assert PREFLIGHT_MARKER in result.stdout
    assert "git cannot open the workspace" in diagnostics
    assert "safe.directory" in diagnostics
    assert str(workspace) in diagnostics
    assert "::group::Tier 1" not in result.stdout


def test_smoke_runs_workspace_preflight_before_tier_one(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "git-workspace"
    workspace.mkdir()
    subprocess.run(["git", "init", str(workspace)], check=True, capture_output=True)
    (workspace / "tracked").write_text("fixture\n")
    subprocess.run(
        ["git", "-C", str(workspace), "add", "tracked"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(workspace),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    uv_stub = stub_bin / "uv"
    uv_stub.write_text("#!/bin/sh\nexit 86\n")
    uv_stub.chmod(0o755)

    result = subprocess.run(
        ["bash", str(SMOKE_SCRIPT)],
        env={
            **os.environ,
            "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
            "WORKSPACE_FOLDER": str(workspace),
        },
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 86
    assert PREFLIGHT_MARKER in result.stdout
    assert "::group::Tier 1" in result.stdout
    assert result.stdout.index(PREFLIGHT_MARKER) < result.stdout.index(
        "::group::Tier 1"
    )
    assert "git cannot open the workspace" not in result.stderr
