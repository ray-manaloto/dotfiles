# Copyright (c) 2026 Raymond Manaloto
"""Real Git controls for the public scratch-proof environment boundary."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import proof_git

_CHECKOUT = Path(__file__).resolve().parent.parent
_LOGGER = logging.getLogger(__name__)
_HOOK_MARKER = "P6_AMBIENT_HOOK_RAN"
_OPAQUE_VALUE = "synthetic-credential"


def _git(
    binary: Path, repo: Path, env: dict[str, str], *args: str
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(binary), "-C", str(repo), *args],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    _LOGGER.info("scratch git %s rc=%d", args[0], result.returncode)
    return result


def _repo(binary: Path, root: Path, env: dict[str, str]) -> None:
    root.mkdir()
    initialized = _git(binary, root, env, "init", "-q")
    assert initialized.returncode == 0, initialized.stderr


def _commit(
    binary: Path, root: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return _git(binary, root, env, "commit", "--allow-empty", "-m", "scratch proof")


def test_scratch_commit_excludes_ambient_hooks_without_disabling_ordinary_git(
    tmp_path: Path, direct_git_binary: Path
) -> None:
    hooks = tmp_path / "ambient-hooks"
    hooks.mkdir()
    hook = hooks / "pre-commit"
    hook.write_text(f"#!/bin/sh\necho {_HOOK_MARKER} >&2\nexit 1\n")
    hook.chmod(0o755)
    ambient_config = tmp_path / "ambient.gitconfig"
    ambient_config.write_text(
        "[user]\n\tname = Ambient\n\temail = ambient@example.invalid\n"
        f"[core]\n\thooksPath = {hooks}\n"
    )
    original_config = ambient_config.read_bytes()
    ambient = dict(os.environ, GIT_CONFIG_GLOBAL=str(ambient_config))
    original_env = ambient.copy()
    ordinary = tmp_path / "ordinary"
    _repo(direct_git_binary, ordinary, ambient)
    failed = _commit(direct_git_binary, ordinary, ambient)
    assert failed.returncode == 1, failed.stderr
    assert _HOOK_MARKER in failed.stderr

    isolated = proof_git.scratch_git_env(
        tmp_path / "isolation", checkout=_CHECKOUT, base=ambient
    )
    scratch = tmp_path / "scratch"
    _repo(direct_git_binary, scratch, isolated)
    passed = _commit(direct_git_binary, scratch, isolated)
    assert passed.returncode == 0, passed.stderr
    assert _HOOK_MARKER not in passed.stderr
    identity = _git(
        direct_git_binary, scratch, isolated, "log", "-1", "--format=%an <%ae>"
    )
    assert identity.stdout.strip() == "T <t@example.com>"
    safe = _git(
        direct_git_binary,
        scratch,
        isolated,
        "config",
        "--global",
        "--get-all",
        "safe.directory",
    )
    assert safe.stdout.splitlines() == [str(_CHECKOUT)]
    assert ambient == original_env
    assert ambient_config.read_bytes() == original_config
    still_failed = _commit(direct_git_binary, ordinary, ambient)
    assert still_failed.returncode == 1, still_failed.stderr
    assert _HOOK_MARKER in still_failed.stderr


def test_scratch_init_excludes_hooks_from_ambient_templates(
    tmp_path: Path, direct_git_binary: Path
) -> None:
    template = tmp_path / "ambient-template"
    hooks = template / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "pre-commit"
    hook.write_text(f"#!/bin/sh\necho {_HOOK_MARKER} >&2\nexit 1\n")
    hook.chmod(0o755)
    ambient = dict(os.environ, GIT_TEMPLATE_DIR=str(template))
    ordinary = tmp_path / "ordinary"
    _repo(direct_git_binary, ordinary, ambient)
    failed = _commit(direct_git_binary, ordinary, ambient)
    assert failed.returncode == 1, failed.stderr
    assert _HOOK_MARKER in failed.stderr

    isolated = proof_git.scratch_git_env(
        tmp_path / "isolation", checkout=_CHECKOUT, base=ambient
    )
    scratch = tmp_path / "scratch"
    _repo(direct_git_binary, scratch, isolated)
    passed = _commit(direct_git_binary, scratch, isolated)
    assert passed.returncode == 0, passed.stderr
    assert _HOOK_MARKER not in passed.stderr


@pytest.mark.parametrize("scope", ["global", "system", "parameters", "count"])
def test_scratch_commit_excludes_ambient_signing_configuration(
    tmp_path: Path, direct_git_binary: Path, scope: str
) -> None:
    config = tmp_path / "ambient.gitconfig"
    signer = tmp_path / "missing-signer"
    config.write_text(f"[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = {signer}\n")
    original = config.read_bytes()
    ambient = dict(os.environ)
    if scope == "global":
        ambient["GIT_CONFIG_GLOBAL"] = str(config)
    elif scope == "system":
        ambient["GIT_CONFIG_SYSTEM"] = str(config)
        ambient["GIT_CONFIG_NOSYSTEM"] = "0"
    elif scope == "parameters":
        ambient["GIT_CONFIG_PARAMETERS"] = (
            f"'commit.gpgsign=true' 'gpg.program={signer}'"
        )
    else:
        ambient.update(
            GIT_CONFIG_COUNT="2",
            GIT_CONFIG_KEY_0="commit.gpgsign",
            GIT_CONFIG_VALUE_0="true",
            GIT_CONFIG_KEY_1="gpg.program",
            GIT_CONFIG_VALUE_1=str(signer),
        )
    # Supply the same identity in both arms even when replacing the fixture config.
    ambient.update(
        GIT_AUTHOR_NAME="T",
        GIT_AUTHOR_EMAIL="t@example.com",
        GIT_COMMITTER_NAME="T",
        GIT_COMMITTER_EMAIL="t@example.com",
    )
    ordinary = tmp_path / "ordinary"
    _repo(direct_git_binary, ordinary, ambient)
    failed = _commit(direct_git_binary, ordinary, ambient)
    assert failed.returncode != 0
    assert "missing-signer" in failed.stderr

    isolated = proof_git.scratch_git_env(
        tmp_path / "isolation", checkout=_CHECKOUT, base=ambient
    )
    scratch = tmp_path / "scratch"
    _repo(direct_git_binary, scratch, isolated)
    passed = _commit(direct_git_binary, scratch, isolated)
    assert passed.returncode == 0, passed.stderr
    assert config.read_bytes() == original


def test_scratch_commit_cannot_use_the_callers_repository_or_index(
    tmp_path: Path, direct_git_binary: Path
) -> None:
    setup_env = proof_git.scratch_git_env(tmp_path / "setup", checkout=_CHECKOUT)
    outer = tmp_path / "outer"
    scratch = tmp_path / "scratch"
    _repo(direct_git_binary, outer, setup_env)
    _repo(direct_git_binary, scratch, setup_env)
    assert _commit(direct_git_binary, outer, setup_env).returncode == 0
    outer_config = (outer / ".git" / "config").read_bytes()
    outer_head = _git(direct_git_binary, outer, setup_env, "rev-parse", "HEAD").stdout
    ambient = dict(
        setup_env,
        GIT_DIR=str(outer / ".git"),
        GIT_WORK_TREE=str(outer),
        GIT_COMMON_DIR=str(outer / ".git"),
        GIT_INDEX_FILE=str(outer / "nonexistent" / "index"),
        GITHUB_TOKEN=_OPAQUE_VALUE,
        __MISE_DIFF="synthetic-diff",
    )
    redirected = _git(
        direct_git_binary, scratch, ambient, "rev-parse", "--show-toplevel"
    )
    assert Path(redirected.stdout.strip()).resolve() == outer.resolve()
    failed = _commit(direct_git_binary, scratch, ambient)
    assert failed.returncode == 128, failed.stderr
    assert "index.lock" in failed.stderr

    isolated = proof_git.scratch_git_env(
        tmp_path / "isolation", checkout=_CHECKOUT, base=ambient
    )
    passed = _commit(direct_git_binary, scratch, isolated)
    assert passed.returncode == 0, passed.stderr
    located = _git(direct_git_binary, scratch, isolated, "rev-parse", "--show-toplevel")
    assert Path(located.stdout.strip()).resolve() == scratch.resolve()
    assert "GITHUB_TOKEN" not in isolated
    assert "__MISE_DIFF" not in isolated
    assert (outer / ".git" / "config").read_bytes() == outer_config
    assert (
        _git(direct_git_binary, outer, setup_env, "rev-parse", "HEAD").stdout
        == outer_head
    )


def test_scratch_config_refuses_to_overwrite_existing_state(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    gitconfig = existing / "gitconfig"
    gitconfig.write_text("retained config\n")
    with pytest.raises(FileExistsError):
        proof_git.scratch_git_env(existing, checkout=_CHECKOUT)
    assert gitconfig.read_text() == "retained config\n"
