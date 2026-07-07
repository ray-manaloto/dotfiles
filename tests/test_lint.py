"""Tests for `dotfiles_setup.lint` (guarded hk runner)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest
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
