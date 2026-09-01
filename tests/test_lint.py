# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.lint` (guarded hk runner)."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import lint as lint_module
from dotfiles_setup.devcontainer_names import workspace_hash
from dotfiles_setup.lint import (
    DEFAULT_TIMEOUT_SECONDS,
    TIMEOUT_ENV_VAR,
    TIMEOUT_EXIT_CODE,
    resolve_timeout,
    run_guarded,
)

if TYPE_CHECKING:
    from pathlib import Path

# A short timeout the kill-path tests can trip quickly without flaking.
_SHORT_TIMEOUT = 1
_SLEEP_LONGER_THAN_TIMEOUT = 30


# ──────────────────────────────────────────────────────────────────────
# resolve_timeout
# ──────────────────────────────────────────────────────────────────────


def test_resolve_timeout_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TIMEOUT_ENV_VAR, raising=False)
    assert resolve_timeout() == DEFAULT_TIMEOUT_SECONDS


def test_resolve_timeout_cli_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "300")
    assert resolve_timeout(120) == 120


def test_resolve_timeout_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "450")
    assert resolve_timeout() == 450


def test_resolve_timeout_rejects_non_integer_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "soon")
    with pytest.raises(ValueError, match="not an integer"):
        resolve_timeout()


@pytest.mark.parametrize("bad", [0, -5])
def test_resolve_timeout_rejects_non_positive_cli(bad: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        resolve_timeout(bad)


# ──────────────────────────────────────────────────────────────────────
# run_guarded
# ──────────────────────────────────────────────────────────────────────


def test_run_guarded_returns_command_exit_code(tmp_path: Path) -> None:
    log_file = tmp_path / "hk.log"
    rc = run_guarded(30, command=("sh", "-c", "exit 7"), log_file=log_file)
    assert rc == 7


def test_run_guarded_passes_through_success(tmp_path: Path) -> None:
    rc = run_guarded(30, command=("true",), log_file=tmp_path / "hk.log")
    assert rc == 0


def test_run_guarded_kills_on_timeout(tmp_path: Path) -> None:
    start = time.monotonic()
    rc = run_guarded(
        _SHORT_TIMEOUT,
        command=("sleep", str(_SLEEP_LONGER_THAN_TIMEOUT)),
        log_file=tmp_path / "hk.log",
    )
    elapsed = time.monotonic() - start
    assert rc == TIMEOUT_EXIT_CODE
    # The sleep was killed, not waited out.
    assert elapsed < _SLEEP_LONGER_THAN_TIMEOUT


def test_run_guarded_truncates_log_each_run(tmp_path: Path) -> None:
    log_file = tmp_path / "hk.log"
    log_file.write_text("stale content from a previous run\n")
    run_guarded(30, command=("true",), log_file=log_file)
    # The command writes nothing to HK_LOG_FILE, so truncation leaves it empty.
    assert log_file.read_text() == ""


# ──────────────────────────────────────────────────────────────────────
# run_guarded — default (workspace-scoped) log path (#895)
# ──────────────────────────────────────────────────────────────────────


def test_run_guarded_explicit_log_file_is_used_verbatim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit `log_file` gets no derivation, symlink, or prune side effect.

    Strengthened per #895 respec F1: the pre-change signature already
    honoured an explicit `log_file` verbatim, so a bare truncation check
    can't fail on revert. Pointing `LOG_DIR` at a directory this run never
    touches (it never derives anything) is what actually fails if derivation
    ever becomes unconditional.
    """
    log_dir = tmp_path / "state"
    monkeypatch.setattr(lint_module, "LOG_DIR", log_dir)
    log_file = tmp_path / "custom.log"

    rc = run_guarded(30, command=("true",), log_file=log_file)

    assert rc == 0
    # The explicit path is the ONLY thing this run touched in tmp_path.
    assert list(tmp_path.iterdir()) == [log_file]
    # LOG_DIR itself was never created — no stable symlink, no legacy-file
    # check, no prune scan.
    assert not log_dir.exists()


def test_run_guarded_default_scopes_by_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two different workspaces get different per-run files that never collide."""
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path / "state")
    ws1, ws2 = tmp_path / "ws1", tmp_path / "ws2"
    ws1.mkdir()
    ws2.mkdir()

    state_dir = tmp_path / "state"
    stable1 = state_dir / f"hk-lint-{workspace_hash(ws1)}.log"
    stable2 = state_dir / f"hk-lint-{workspace_hash(ws2)}.log"

    run_guarded(
        30, command=("sh", "-c", 'printf ws1 > "$HK_LOG_FILE"'), project_root=ws1
    )
    assert stable1.resolve().read_text() == "ws1"

    run_guarded(
        30, command=("sh", "-c", 'printf ws2 > "$HK_LOG_FILE"'), project_root=ws2
    )
    assert stable2.resolve().read_text() == "ws2"

    # ws2's run must not have touched, truncated, or overwritten ws1's file.
    assert stable1.resolve().read_text() == "ws1"
    assert stable1.resolve() != stable2.resolve()


def test_run_guarded_stable_symlink_points_at_this_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path)
    project_root = tmp_path / "ws"
    project_root.mkdir()

    run_guarded(30, command=("true",), project_root=project_root)

    stable = tmp_path / f"hk-lint-{workspace_hash(project_root)}.log"
    per_run = tmp_path / f"hk-lint-{workspace_hash(project_root)}-{os.getpid()}.log"
    assert stable.is_symlink()
    assert stable.resolve() == per_run.resolve()


def test_run_guarded_replaces_pre_existing_regular_file_at_stable_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A legacy plain file at the stable path becomes a symlink; rc unaffected.

    No explicit migration branch exists (or should) — `os.replace`/
    `Path.replace` subsumes replacing a regular file with a symlink, so this
    asserts the OUTCOME rather than any particular code path (#895 invariant
    5: an explicit unlink-then-relink branch would reintroduce the very race
    this scoping closes).
    """
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path)
    project_root = tmp_path / "ws"
    project_root.mkdir()
    stable = tmp_path / f"hk-lint-{workspace_hash(project_root)}.log"
    stable.write_text("legacy plain file, not a symlink\n")
    assert not stable.is_symlink()

    rc = run_guarded(30, command=("true",), project_root=project_root)

    assert rc == 0
    assert stable.is_symlink()


def test_run_guarded_removes_legacy_fixed_log_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pre-#895 single fixed `hk-lint.log` is removed, not left as a decoy.

    #895 respec F2: a survivor of the old code would otherwise be permanently
    frozen (the new prune glob requires `-<pid>.log` and can never match the
    bare legacy name), lying silently at the exact path every persisted doc
    still tells an agent to read.
    """
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path)
    project_root = tmp_path / "ws"
    project_root.mkdir()
    legacy = tmp_path / "hk-lint.log"
    legacy.write_text("frozen body from before #895\n")

    rc = run_guarded(30, command=("true",), project_root=project_root)

    assert rc == 0
    assert not legacy.exists()


# ──────────────────────────────────────────────────────────────────────
# _prune_old_logs (#895 respec F1/F5) — the only file-deleting code here
# ──────────────────────────────────────────────────────────────────────


def test_prune_old_logs_deletes_log_older_than_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale per-run log for THIS workspace is deleted.

    Mutation arm: comment out `candidate.unlink()` in `_prune_stale` (leave
    the age check in place) — this test then fails because `stale` survives.
    """
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path)
    project_root = tmp_path / "ws"
    project_root.mkdir()
    h = workspace_hash(project_root)
    current = tmp_path / f"hk-lint-{h}-{os.getpid()}.log"
    current.write_text("current run")
    stale = tmp_path / f"hk-lint-{h}-999999.log"
    stale.write_text("stale run")
    old = time.time() - lint_module._PRUNE_MAX_AGE_SECONDS - 3600
    os.utime(stale, (old, old))

    lint_module._prune_old_logs(project_root, current)

    assert not stale.exists()
    assert current.exists()


def test_prune_old_logs_spares_a_fresh_concurrent_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh per-run log from a second, still-live run is NOT deleted.

    This is the concurrency property #895 exists to protect: without the
    age floor, this run's own prune pass would delete a sibling run's LIVE
    log. Mutation arm: delete the `if age < _PRUNE_MAX_AGE_SECONDS: continue`
    guard in `_prune_stale` (unlink unconditionally) — this test then fails
    because `live_sibling` is gone.
    """
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path)
    project_root = tmp_path / "ws"
    project_root.mkdir()
    h = workspace_hash(project_root)
    current = tmp_path / f"hk-lint-{h}-{os.getpid()}.log"
    current.write_text("current run")
    live_sibling = tmp_path / f"hk-lint-{h}-424242.log"
    live_sibling.write_text("a second run, started moments ago")  # mtime = now

    lint_module._prune_old_logs(project_root, current)

    assert live_sibling.exists()


def test_prune_old_logs_spares_a_symlink_even_with_an_old_target_mtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A symlink matching the per-run name shape is never pruned by age.

    Covers the real stable symlink defensively: it never matches the
    `hk-lint-<hash>-*.log` glob by name (`_prune_old_logs`'s docstring), so
    this plants a symlink that WOULD match, to isolate the `is_symlink()`
    guard from the naming exclusion. Mutation arm: delete the
    `if skip_symlinks and candidate.is_symlink(): continue` line in
    `_prune_stale` — with the guard gone, the age check alone no longer
    protects it (its own `lstat` mtime, set old below via
    `follow_symlinks=False`, is what the age check reads), so this test then
    fails because the symlink is gone.
    """
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path)
    project_root = tmp_path / "ws"
    project_root.mkdir()
    h = workspace_hash(project_root)
    current = tmp_path / f"hk-lint-{h}-{os.getpid()}.log"
    current.write_text("current run")
    old_target = tmp_path / "old-target.log"
    old_target.write_text("old")
    stray_symlink = tmp_path / f"hk-lint-{h}-777777.log"
    stray_symlink.symlink_to(old_target)
    old = time.time() - lint_module._PRUNE_MAX_AGE_SECONDS - 3600
    os.utime(stray_symlink, (old, old), follow_symlinks=False)

    lint_module._prune_old_logs(project_root, current)

    assert stray_symlink.is_symlink()
    assert old_target.exists()  # replace/unlink on the link must not follow it


def test_prune_old_logs_spares_another_workspaces_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale per-run log that belongs to a DIFFERENT workspace is untouched.

    Mutation arm: widen the glob in `_prune_old_logs` from
    `hk-lint-{hash}-*.log` to `hk-lint-*.log` — this test then fails because
    `other_workspace_log` is gone.
    """
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path)
    ws1 = tmp_path / "ws1"
    ws1.mkdir()
    ws2 = tmp_path / "ws2"
    ws2.mkdir()
    current = tmp_path / f"hk-lint-{workspace_hash(ws1)}-{os.getpid()}.log"
    current.write_text("current run")
    other_workspace_log = tmp_path / f"hk-lint-{workspace_hash(ws2)}-13579.log"
    other_workspace_log.write_text("a different clone's stale run")
    old = time.time() - lint_module._PRUNE_MAX_AGE_SECONDS - 3600
    os.utime(other_workspace_log, (old, old))

    lint_module._prune_old_logs(ws1, current)

    assert other_workspace_log.exists()


def test_prune_old_logs_removes_a_stale_orphaned_tmp_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `.tmp-<pid>` symlink left by a run killed mid-replace is swept.

    #895 respec F5: `_update_stable_symlink`'s temp link is only ever cleared
    by a LATER run reusing the same pid; this sweep is the general case.
    Mutation arm: drop the `tmp_links` glob/sweep from `_prune_old_logs`
    (call `_prune_stale` only on `per_run`) — this test then fails because
    `orphan` survives.
    """
    monkeypatch.setattr(lint_module, "LOG_DIR", tmp_path)
    project_root = tmp_path / "ws"
    project_root.mkdir()
    h = workspace_hash(project_root)
    current = tmp_path / f"hk-lint-{h}-{os.getpid()}.log"
    current.write_text("current run")
    target = tmp_path / f"hk-lint-{h}-000001.log"
    target.write_text("orphaned run's real log")
    orphan = tmp_path / f"hk-lint-{h}.log.tmp-000001"
    orphan.symlink_to(target)
    old = time.time() - lint_module._PRUNE_MAX_AGE_SECONDS - 3600
    os.utime(orphan, (old, old), follow_symlinks=False)

    lint_module._prune_old_logs(project_root, current)

    assert not orphan.exists()
