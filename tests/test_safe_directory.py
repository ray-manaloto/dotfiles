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


def _committed_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "git-workspace"
    workspace.mkdir()
    (workspace / ".chezmoiroot").write_text("home\n")
    (workspace / "home").mkdir()
    (workspace / "tracked").write_text("fixture\n")
    subprocess.run(["git", "init", str(workspace)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(workspace), "add", ".chezmoiroot", "tracked"],
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
    return workspace


def _render_gitconfig(workspace: Path, destination: Path) -> None:
    rendered = subprocess.run(
        ["chezmoi", f"--source={workspace}", "execute-template"],
        input=GITCONFIG_TEMPLATE.read_text(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    destination.write_text(rendered)


def _smoke_env(workspace: Path, gitconfig: Path) -> dict[str, str]:
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1",
        "WORKSPACE_FOLDER": str(workspace),
    }


def test_gitconfig_renders_the_current_chezmoi_working_tree(
    tmp_path: Path,
) -> None:
    source = _committed_workspace(tmp_path)
    rendered_gitconfig = tmp_path / "rendered.gitconfig"
    _render_gitconfig(source, rendered_gitconfig)

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

    source_dir = source / "home"
    assert safe_directories == [str(source)]
    assert str(source_dir) not in safe_directories


def test_smoke_refuses_dubious_ownership_before_tier_one(
    tmp_path: Path,
) -> None:
    workspace = _committed_workspace(tmp_path)
    unsafe_gitconfig = tmp_path / "unsafe.gitconfig"
    unsafe_gitconfig.write_text("")

    result = subprocess.run(
        ["bash", str(SMOKE_SCRIPT)],
        env=_smoke_env(workspace, unsafe_gitconfig),
        check=False,
        capture_output=True,
        text=True,
    )
    diagnostics = result.stdout + result.stderr

    assert result.returncode == 1
    assert PREFLIGHT_MARKER in result.stdout
    assert "detected dubious ownership" in diagnostics
    assert "git cannot open the workspace" in diagnostics
    assert "safe.directory" in diagnostics
    assert str(workspace) in diagnostics
    assert "::group::Tier 1" not in result.stdout


def test_rendered_safe_directory_clears_ownership_preflight(
    tmp_path: Path,
) -> None:
    workspace = _committed_workspace(tmp_path)
    rendered_gitconfig = tmp_path / "rendered.gitconfig"
    _render_gitconfig(workspace, rendered_gitconfig)
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    uv_stub = stub_bin / "uv"
    uv_stub.write_text("#!/bin/sh\nexit 86\n")
    uv_stub.chmod(0o755)

    result = subprocess.run(
        ["bash", str(SMOKE_SCRIPT)],
        env={
            **_smoke_env(workspace, rendered_gitconfig),
            "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
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
