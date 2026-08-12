# Copyright (c) 2026 Raymond Manaloto
"""Tests for the Git-isolated pre-push child-process boundary."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import process_env

_OPAQUE_VALUE = "opaque-value"


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed rc={result.returncode}: {result.stderr}"
        raise RuntimeError(msg)
    return result.stdout.strip()


def _init_repo(path: Path) -> None:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "Env Safety Test")
    _git(path, "config", "user.email", "env-safety@example.invalid")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(path, "add", "tracked.txt")
    _git(path, "commit", "-m", "initial")


def _fingerprint(repo: Path) -> tuple[str, ...]:
    """Fingerprint every outer-repository surface the reproduced bug changed."""
    git_dir = Path(_git(repo, "rev-parse", "--absolute-git-dir"))
    common_dir = Path(_git(repo, "rev-parse", "--git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = (repo / common_dir).resolve()
    index = git_dir / "index"
    hook = git_dir / "hooks" / "pre-push"
    refs = tuple(
        (str(path.relative_to(git_dir)), path.read_bytes().hex())
        for path in sorted((git_dir / "refs").rglob("*"))
        if path.is_file()
    )
    packed_refs = git_dir / "packed-refs"
    return (
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "symbolic-ref", "HEAD"),
        str(git_dir),
        str(common_dir),
        (common_dir / "config").read_bytes().hex(),
        repr(refs),
        packed_refs.read_bytes().hex() if packed_refs.exists() else "ABSENT",
        index.read_bytes().hex(),
        hook.read_bytes().hex(),
        (repo / "tracked.txt").read_bytes().hex(),
        _git(repo, "status", "--porcelain=v1"),
    )


def _fingerprint_without_hook(repo: Path) -> tuple[str, str]:
    """Small fingerprint for the deliberately destructive isolated control."""
    git_dir = Path(_git(repo, "rev-parse", "--absolute-git-dir"))
    return (
        (git_dir / "config").read_bytes().hex(),
        _git(repo, "config", "--get", "core.bare"),
    )


@pytest.mark.parametrize("raw", [(), ("--",)])
def test_command_after_separator_requires_a_command(raw: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="command is required"):
        process_env.command_after_separator(raw)


def test_git_isolated_env_uses_the_derived_git_set_and_drops_credentials() -> None:
    local = frozenset({"GIT_DIR", "GIT_FUTURE_LOCAL_STATE"})
    base = {
        "PATH": "/usr/bin",
        "GIT_DIR": "/outer/.git",
        "GIT_FUTURE_LOCAL_STATE": "future",
        "GITHUB_TOKEN": _OPAQUE_VALUE,
        "ORDINARY": "kept",
    }
    cleaned = process_env.git_isolated_env(base, local_names=local)
    assert cleaned == {"PATH": "/usr/bin", "ORDINARY": "kept"}


def test_git_local_env_discovery_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        process_env.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "failure"),
    )
    with pytest.raises(RuntimeError, match="failed rc=1"):
        process_env.git_local_env_names()


def test_real_pre_push_poison_cannot_modify_outer_repository(tmp_path: Path) -> None:
    """The public pre-push task scrubs all Git-local variables before pytest."""
    project = Path(__file__).parent.parent.resolve()
    outer = tmp_path / "outer"
    remote = tmp_path / "remote.git"
    disposable = tmp_path / "disposable"
    plugin_dir = tmp_path / "plugin"
    marker = tmp_path / "probe-ran"
    _init_repo(outer)
    disposable.mkdir()
    plugin_dir.mkdir()
    (plugin_dir / "poison_probe.py").write_text(
        "import os\n"
        "import subprocess\n"
        "from pathlib import Path\n"
        "def pytest_sessionstart(session):\n"
        '    subprocess.run(["git", "-C", os.environ["PROBE_REPO"], '
        '"-c", "core.bare=false", "init"], check=True)\n'
        '    Path(os.environ["PROBE_MARKER"]).write_text("ran\\n")\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "--bare", str(remote)], check=True)
    _git(outer, "remote", "add", "origin", str(remote))
    _git(outer, "push", "-u", "origin", "HEAD")
    (outer / "tracked.txt").write_text("next\n", encoding="utf-8")
    _git(outer, "commit", "-am", "next")

    hook = Path(_git(outer, "rev-parse", "--git-path", "hooks/pre-push"))
    if not hook.is_absolute():
        hook = outer / hook
    local_names = process_env.git_local_env_names(cwd=outer)
    poison_lines = "\n".join(
        f'export {name}="$outer_git_dir"' for name in sorted(local_names)
    )
    hook.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        'outer_git_dir="$(git rev-parse --absolute-git-dir)"\n'
        f"{poison_lines}\n"
        f'export PYTHONPATH="{plugin_dir}"\n'
        'export PYTEST_PLUGINS="poison_probe"\n'
        f'export PROBE_REPO="{disposable}"\n'
        f'export PROBE_MARKER="{marker}"\n'
        f'cd "{project}"\n'
        "exec mise run test-hook-isolated -- --collect-only\n",
        encoding="utf-8",
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    before = _fingerprint(outer)

    _git(outer, "push", "--dry-run", "origin", "HEAD")

    assert _fingerprint(outer) == before
    assert (disposable / ".git").is_dir()
    assert marker.read_text(encoding="utf-8") == "ran\n"


def test_poisoned_git_env_mutation_reaches_outer_without_scrub(tmp_path: Path) -> None:
    """Control: removing the isolation reproduces mutation of the outer repo."""
    outer = tmp_path / "outer"
    disposable = tmp_path / "disposable"
    _init_repo(outer)
    disposable.mkdir()
    before = _fingerprint_without_hook(outer)
    env = dict(os.environ)
    env["GIT_DIR"] = _git(outer, "rev-parse", "--absolute-git-dir")
    env["GIT_WORK_TREE"] = str(outer)

    subprocess.run(
        ["git", "-C", str(disposable), "config", "core.bare", "true"],
        check=True,
        env=env,
    )

    assert _fingerprint_without_hook(outer) != before
    assert _git(outer, "config", "--get", "core.bare") == "true"


def test_mise_and_pre_push_wiring_use_the_public_boundary() -> None:
    """Dropping the boundary from the real hook wiring must fail this gate."""
    root = Path(__file__).parent.parent
    mise = (root / "mise.toml").read_text(encoding="utf-8")
    hk = (root / "hk.pkl").read_text(encoding="utf-8")
    assert "[tasks.test-hook-isolated]" in mise
    assert (
        "uv run --project python dotfiles-setup process git-isolated -- "
        "uv run --project python pytest tests/ -x -q"
    ) in mise
    assert 'check = "mise run test-hook-isolated"' in hk
