# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.script_guard` (write-time new-bash deny).

Every deny is paired with an allow. A guard that denies everything is
indistinguishable from a broken repo, and one that denies nothing is
indistinguishable from not being installed — neither reports itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dotfiles_setup import bash_budget, script_guard


def _write(root: Path, rel: str, content: str = "") -> dict[str, object]:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    return {"file_path": str(target), "content": content}


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A throwaway repo root the guard treats as its own."""
    monkeypatch.setattr(script_guard, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(script_guard.branch_guard, "is_ignored", lambda _p, _r: False)
    return tmp_path


def test_a_new_shell_script_is_denied(repo: Path) -> None:
    reason = script_guard.decide(_write(repo, "scripts/foo.sh", "#!/bin/bash\n"))
    assert reason is not None
    assert "scripts/foo.sh" in reason
    assert "zero-bash-logic" in reason


def test_an_extensionless_script_is_denied_by_its_shebang(repo: Path) -> None:
    """The case a `*.sh` pathspec cannot see.

    `bash_budget`'s SCOPE_PATHSPECS are glob-based, so `scripts/deploy` with a
    bash shebang is invisible to the commit-time budget entirely.
    """
    reason = script_guard.decide(
        _write(repo, "scripts/deploy", "#!/usr/bin/env bash\n")
    )
    assert reason is not None
    assert "scripts/deploy" in reason


def test_an_allowlisted_script_is_permitted(repo: Path) -> None:
    """Editing a sanctioned wrapper stays allowed; the budget governs growth."""
    listed = next(iter(bash_budget.ALLOWLIST))
    assert script_guard.decide(_write(repo, listed, "#!/bin/bash\n")) is None


def test_the_allowlist_is_not_duplicated_in_this_module() -> None:
    """One source of truth. Two lists drift, and the drift is invisible.

    Control-armed: the allowlist is non-empty, so a passing assertion means the
    guard really consults it rather than there being nothing to consult.
    """
    assert bash_budget.ALLOWLIST, "control arm: allowlist is empty — probe is broken"
    source = Path(script_guard.__file__).read_text()
    for listed in bash_budget.ALLOWLIST:
        assert listed not in source, f"{listed} is hard-coded in script_guard"


@pytest.mark.parametrize(
    ("rel", "content"),
    [
        ("python/src/dotfiles_setup/x.py", "x = 1\n"),
        ("docs/notes.md", "# notes\n"),
        ("mise.toml", "[tools]\n"),
        # A python file that merely QUOTES a shebang must not be denied.
        ("python/src/dotfiles_setup/y.py", 'DOC = "#!/bin/bash"\n'),
    ],
)
def test_non_shell_files_are_permitted(repo: Path, rel: str, content: str) -> None:
    assert script_guard.decide(_write(repo, rel, content)) is None


def test_vendored_plugins_are_exempt(repo: Path) -> None:
    assert script_guard.decide(_write(repo, "plugins/x/y.sh", "#!/bin/bash\n")) is None


@pytest.mark.usefixtures("repo")
def test_a_script_outside_the_repo_is_not_our_business(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    payload: dict[str, object] = {
        "file_path": str(elsewhere / "foo.sh"),
        "content": "#!/bin/bash\n",
    }
    assert script_guard.decide(payload) is None


def test_a_gitignored_script_is_permitted(
    monkeypatch: pytest.MonkeyPatch, repo: Path
) -> None:
    """A throwaway probe in the scratchpad must not be blocked."""
    monkeypatch.setattr(script_guard.branch_guard, "is_ignored", lambda _p, _r: True)
    assert script_guard.decide(_write(repo, "scripts/tmp.sh", "#!/bin/bash\n")) is None


@pytest.mark.parametrize(
    "first",
    ["#!/bin/bash", "#!/usr/bin/env bash", "#!/bin/sh", "#!/usr/bin/env zsh"],
)
def test_a_shell_shebang_is_recognised(first: str) -> None:
    assert script_guard.has_shell_shebang(f"{first}\nbody\n")


@pytest.mark.parametrize(
    "first",
    ["#!/usr/bin/env python3", "#!/usr/bin/python", "# not a shebang", ""],
)
def test_a_non_shell_first_line_is_not_a_shell_shebang(first: str) -> None:
    """A non-shell first line is not a shell shebang.

    The python arms are the ones that matter: a python script carrying its own
    shebang must not be denied as bash.
    """
    assert not script_guard.has_shell_shebang(f"{first}\nbody\n")


def test_a_shebang_below_the_first_line_is_not_a_shebang() -> None:
    """Otherwise a python file documenting one would be denied."""
    assert not script_guard.has_shell_shebang("x = 1\n#!/bin/bash\n")


@pytest.mark.parametrize("tool", ["Edit", "Write", "NotebookEdit"])
def test_handles_the_write_tools(tool: str) -> None:
    assert script_guard.handles(tool)


@pytest.mark.parametrize("tool", ["Bash", "Read", "Grep", "AskUserQuestion"])
def test_does_not_handle_other_tools(tool: str) -> None:
    assert not script_guard.handles(tool)


@pytest.mark.parametrize("payload", [{}, {"file_path": ""}, {"file_path": 42}])
def test_a_malformed_payload_fails_open(payload: dict[str, object]) -> None:
    """Never block a write because the guard could not read its own input."""
    assert script_guard.decide(payload) is None


def test_edit_tool_content_key_is_read(repo: Path) -> None:
    """`Edit` carries `new_string`, not `content` — both must be inspected."""
    payload: dict[str, object] = {
        "file_path": str(repo / "scripts" / "deploy"),
        "new_string": "#!/bin/bash\necho hi\n",
    }
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    assert script_guard.decide(payload) is not None
