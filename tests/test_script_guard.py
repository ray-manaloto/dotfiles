# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.script_guard` (write-time new-bash deny).

Every deny is paired with an allow. A guard that denies everything is
indistinguishable from a broken repo, and one that denies nothing is
indistinguishable from not being installed — neither reports itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dotfiles_setup import bash_budget, branch_guard, hook_guard, script_guard


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


# --- regressions from the cold review of e949f5c
#
# Every test above calls `script_guard.decide` directly, so reverting the one
# dispatch line in hook_guard.py left the whole suite green while the guard was
# unreachable. These drive the real dispatch and the real settings wiring.


def test_the_dispatch_actually_reaches_this_guard() -> None:
    """Reverting the hook_guard dispatch must fail a test, not pass silently."""
    root = script_guard.repo_root()
    payload: dict[str, object] = {
        "file_path": str(root / "scripts" / "definitely-new-probe.sh"),
        "content": "#!/bin/bash\n",
    }
    assert hook_guard.decide_payload("Write", payload) is not None


def test_the_dispatch_still_reaches_the_branch_guard(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Chaining must not shadow the guard it was chained behind."""
    calls: list[str] = []

    def _spy(_tool_input: dict[str, object]) -> str | None:
        calls.append("branch")
        return None

    monkeypatch.setattr(branch_guard, "decide", _spy)
    neutral: dict[str, object] = {"file_path": str(tmp_path / "x.py")}
    hook_guard.decide_payload("Write", neutral)
    assert calls == ["branch"]


def test_an_existing_file_is_never_denied() -> None:
    """The contract is to stop NEW bash, not to freeze what exists.

    `home/dot_local/bin/executable_claude` is a tracked bash wrapper that cannot
    enter the allowlist — the commit gate would call the entry stale — so
    denying it would be an outage with no escape hatch.
    """
    root = script_guard.repo_root()
    existing = root / "home" / "dot_local" / "bin" / "executable_claude"
    if not existing.exists():  # pragma: no cover - control arm
        pytest.skip("fixture file absent; this probe would prove nothing")
    payload: dict[str, object] = {
        "file_path": str(existing),
        "content": "#!/usr/bin/env bash\n",
    }
    assert script_guard.decide(payload) is None


def test_a_new_script_with_a_non_shell_suffix_is_denied(repo: Path) -> None:
    """`scripts/deploy.txt` holding bash passed BOTH layers before this."""
    assert script_guard.decide(_write(repo, "scripts/deploy.txt", "#!/bin/bash\n"))


@pytest.mark.parametrize(
    "shebang",
    ["#!/BIN/BASH", "#!/bin/bash\t-e", "#!/usr/bin/env  bash", "#!/bin/ash"],
)
def test_shell_shebang_variants_that_really_execute(shebang: str) -> None:
    """Case and tab forms run fine on this host; the guard must see them."""
    assert script_guard.has_shell_shebang(f"{shebang}\nbody\n")


@pytest.mark.parametrize(
    "shebang",
    ["#!/usr/bin/env notbash", "#!/usr/bin/env -S python -c bash", "#!/usr/bin/env"],
)
def test_non_shell_shebangs_are_not_denied(shebang: str) -> None:
    """`"notbash".endswith("bash")` is why the token is parsed, not suffixed."""
    assert not script_guard.has_shell_shebang(f"{shebang}\nbody\n")


def test_an_allowlisted_script_survives_a_case_variant_path() -> None:
    """This host's filesystem is case-insensitive; the allowlist compare was not."""
    root = script_guard.repo_root()
    listed = next(iter(bash_budget.ALLOWLIST))
    payload: dict[str, object] = {
        "file_path": str(root / listed.upper()),
        "content": "#!/bin/bash\n",
    }
    assert script_guard.decide(payload) is None
