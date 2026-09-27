# Copyright (c) 2026 Raymond Manaloto
"""The autouse `isolated_git_config` fixture keeps machine-level git config out.

hk v2 recommends `hk install --global`, which writes `hook.hk-*` into
`~/.gitconfig`; without isolation every throwaway repo a test creates runs it
(the 2026-09-27 `test_branch_guard` failure). These tests contaminate `$HOME`
the way a real machine is, so deleting the fixture fails the first one.
"""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

_MARKER = "PROBE_GLOBAL_HOOK_RAN"


def _contaminated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(
        "[user]\n"
        "\tname = T\n"
        "\temail = t@example.com\n"
        '[hook "probe-pre-commit"]\n'
        # Quoted: an unquoted `;` starts a comment in git config, which
        # silently truncates the command to `echo` (exit 0).
        f'\tcommand = "echo {_MARKER} >&2; exit 1"\n'
        "\tevent = pre-commit\n"
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)


def _commit_in_throwaway_repo(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
    (repository / "tracked").write_text("fixture\n")
    subprocess.run(
        ["git", "-C", str(repository), "add", "tracked"],
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", "probe"],
        check=False,
        capture_output=True,
        text=True,
    )


def test_a_global_hook_in_home_does_not_reach_a_test_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the fixture active, `$HOME/.gitconfig` is never read."""
    _contaminated_home(tmp_path, monkeypatch)

    result = _commit_in_throwaway_repo(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _MARKER not in result.stderr


def test_the_probe_sees_the_global_hook_without_the_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CONTROL ARM: undo the fixture's override and the same hook fires.

    Without this arm the test above could pass because the probe hook never
    runs at all, rather than because the fixture blocks it.
    """
    _contaminated_home(tmp_path, monkeypatch)
    monkeypatch.delenv("GIT_CONFIG_GLOBAL")

    result = _commit_in_throwaway_repo(tmp_path)

    assert result.returncode != 0
    assert _MARKER in result.stderr


def test_the_fixture_keeps_this_checkout_a_safe_directory() -> None:
    """#1183: the replaced global config still trusts this repository."""
    root = Path(__file__).resolve().parent.parent
    listed = subprocess.run(
        ["git", "config", "--global", "--get-all", "safe.directory"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert str(root) in listed
