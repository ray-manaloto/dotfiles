# Copyright (c) 2026 Raymond Manaloto
"""hk hook presence: the doctor's `hk-hooks` check and the module under it.

Real git repos, never mocks: the question is what `git config` answers for a
checkout, and that is only answered by git. The autouse `isolated_git_config`
fixture gives each test an empty global scope, so "global install" arms write
into THAT file (`GIT_CONFIG_GLOBAL`) and never the developer's `~/.gitconfig`.
"""

import os
import subprocess
import tomllib
from pathlib import Path

import pytest
from dotfiles_setup import doctor, hk_hooks

_ALL = ["pre-commit", "commit-msg", "pre-push"]


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _add_hook(root: Path, event: str, *, scope: str) -> None:
    # Belt and braces for `--global`: refuse unless GIT_CONFIG_GLOBAL points into
    # a pytest tmp tree, so this module cannot rewrite the developer's real
    # ~/.gitconfig even when run without conftest's `isolated_git_config`
    # (cold review of 42a699c8, N5: a `--noconftest` run did exactly that).
    if scope == "--global":
        target = os.environ.get("GIT_CONFIG_GLOBAL", "")
        assert "pytest-of-" in target, f"refusing a --global write to {target!r}"
    subprocess.run(
        ["git", "-C", str(root), "config", scope, f"hook.hk-{event}.event", event],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "config",
            scope,
            f"hook.hk-{event}.command",
            f"hk run {event} --from-hook",
        ],
        check=True,
    )


def _setup(root: Path, required: object = _ALL) -> doctor.Setup:
    baseline: dict[str, object] = {}
    if required is not None:
        baseline["hk_hooks"] = {"required": required}
    return doctor.Setup(
        repo_root=root,
        baseline=baseline,
        servers=(),
        settings={},
        local_settings={},
        fnox=doctor.FnoxState(exists=False),
        environ=os.environ,
    )


def test_a_fresh_clone_reports_every_missing_event(tmp_path: Path) -> None:
    """The motivating case: no postinstall, no global install → all missing."""
    findings = doctor.check_hk_hooks(_setup(_repo(tmp_path)))

    assert len(findings) == 1
    assert "pre-commit, commit-msg, pre-push" in findings[0]
    assert "hk install --global --mise" in findings[0]


def test_a_local_install_satisfies_the_check(tmp_path: Path) -> None:
    """CONTROL ARM for the one above: the same repo with all three installed."""
    root = _repo(tmp_path)
    for event in _ALL:
        _add_hook(root, event, scope="--local")

    assert doctor.check_hk_hooks(_setup(root)) == []


def test_a_global_install_counts_and_a_missing_pre_push_is_named(
    tmp_path: Path,
) -> None:
    """The live shape: another project's global install lacks pre-push."""
    root = _repo(tmp_path)
    for event in ("pre-commit", "commit-msg"):
        _add_hook(root, event, scope="--global")

    findings = doctor.check_hk_hooks(_setup(root))

    assert len(findings) == 1
    assert "for pre-push —" in findings[0]


def test_a_non_hk_hook_does_not_count(tmp_path: Path) -> None:
    """Another hook manager's `hook.<name>` entry is not an hk hook."""
    root = _repo(tmp_path)
    for key, value in (
        ("hook.lefthook-pre-push.event", "pre-push"),
        ("hook.lefthook-pre-push.command", "lefthook run pre-push"),
    ):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)

    assert hk_hooks.event_has_hk_hook(root, "pre-push") is False


def test_a_disabled_global_hook_is_reported_missing(tmp_path: Path) -> None:
    """`hook.<name>.enabled = false` means it will not run (codex review, P2)."""
    root = _repo(tmp_path)
    for event in _ALL:
        _add_hook(root, event, scope="--global")
    subprocess.run(
        ["git", "-C", str(root), "config", "hook.hk-pre-commit.enabled", "false"],
        check=True,
    )

    findings = doctor.check_hk_hooks(_setup(root))

    assert len(findings) == 1
    assert "for pre-commit —" in findings[0]


def _legacy_shim(root: Path, event: str, body: str, *, executable: bool) -> None:
    script = root / ".git" / "hooks" / event
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(0o755 if executable else 0o644)


def test_a_legacy_hk_shim_counts(tmp_path: Path) -> None:
    """`hk install --legacy` (auto on Git < 2.54) writes hookdir scripts (P2)."""
    root = _repo(tmp_path)
    for event in _ALL:
        _legacy_shim(root, event, f'exec hk run {event} "$@"', executable=True)

    assert doctor.check_hk_hooks(_setup(root)) == []


def test_a_foreign_or_non_executable_hookdir_script_does_not_count(
    tmp_path: Path,
) -> None:
    """CONTROL ARMS for the shim case: not hk's, or git will not run it."""
    root = _repo(tmp_path)
    _legacy_shim(root, "pre-commit", "exec lefthook run pre-commit", executable=True)
    _legacy_shim(root, "pre-push", 'exec hk run pre-push "$@"', executable=False)

    assert hk_hooks.event_has_hk_hook(root, "pre-commit") is False
    assert hk_hooks.event_has_hk_hook(root, "pre-push") is False


def test_an_unreadable_config_is_reported_not_read_as_missing(tmp_path: Path) -> None:
    """A git error must never masquerade as "no hooks installed"."""
    not_a_repo = tmp_path / "missing-dir"

    with pytest.raises(hk_hooks.HookConfigUnreadableError):
        hk_hooks.event_has_hk_hook(not_a_repo, "pre-commit")
    findings = doctor.check_hk_hooks(_setup(not_a_repo))
    assert findings
    assert "could not read git hook config" in findings[0]


def test_an_empty_baseline_is_loud(tmp_path: Path) -> None:
    """A check with nothing to check says so rather than passing."""
    findings = doctor.check_hk_hooks(_setup(_repo(tmp_path), required=None))

    assert findings
    assert "[hk_hooks].required" in findings[0]


def test_the_live_baseline_names_every_hook_hk_pkl_defines() -> None:
    """doctor.toml's list tracks the hook events hk.pkl actually declares."""
    root = Path(__file__).resolve().parent.parent
    baseline = tomllib.loads((root / "doctor.toml").read_text())
    required = baseline["hk_hooks"]["required"]
    hk_pkl = (root / "hk.pkl").read_text()

    assert required, "an empty list would make this loop pass vacuously"

    for event in required:
        assert f'  ["{event}"] {{' in hk_pkl
