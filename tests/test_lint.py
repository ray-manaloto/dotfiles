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


def test_run_guarded_explicit_log_file_is_used_verbatim(tmp_path: Path) -> None:
    """An explicit `log_file` gets no derivation, symlink, or prune side effect."""
    log_file = tmp_path / "custom.log"
    rc = run_guarded(30, command=("true",), log_file=log_file)
    assert rc == 0
    # The explicit path is the ONLY thing this run touched in tmp_path.
    assert list(tmp_path.iterdir()) == [log_file]


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
