# Copyright (c) 2026 Raymond Manaloto
"""Tests for the RE2-aware renovate config gate (dotfiles_setup.renovate_validate).

Two layers, mirroring ``test_bash_budget.py``: isolated logic tests that inject
at the ``run_validator`` boundary, and real-repo guards that drive the actual
``renovate-config-validator``.

The property under test is unusual and worth naming: the gate's own check is
**inverted**. :func:`engine_rejects_lookahead` asks the validator to FAIL, and a
zero exit is the alarm. So the tests that matter most are the ones pinning that
the canary is genuinely RE2-invalid (otherwise the gate silently becomes a
check that can only pass — see ``.claude/rules/probes-need-a-control-arm.md``)
and that a degraded engine short-circuits BEFORE the real config is ever
reported as valid.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import renovate_validate

REPO_ROOT = Path(__file__).parent.parent

# The RE2-unsupported constructs Renovate's docs call out. A canary must use one
# of these or it proves nothing.
_RE2_UNSUPPORTED = re.compile(r"\(\?=|\(\?!|\(\?<=|\(\?<!|\\[1-9]")


def _canary_patterns() -> list[str]:
    managers = renovate_validate.RE2_CANARY_CONFIG["customManagers"]
    assert isinstance(managers, list)
    return [s for m in managers for s in m["matchStrings"]]


# --------------------------------------------------------------------------
# The canary must stay a real canary
# --------------------------------------------------------------------------


def test_canary_actually_contains_an_re2_unsupported_construct() -> None:
    """If the canary loses its lookahead the gate can only ever pass.

    This is the neutering regression: someone "tidies" the pattern, every arm
    still goes green, and the gate is dead. Bind the construct itself.
    """
    patterns = _canary_patterns()
    assert patterns, "canary declares no matchStrings"
    assert any(_RE2_UNSUPPORTED.search(p) for p in patterns), (
        f"canary patterns carry no RE2-unsupported construct: {patterns}"
    )


def test_canary_is_valid_for_js_regexp() -> None:
    """The canary must be invalid for RE2 ONLY — not malformed in general.

    A pattern that is simply broken would fail on both engines, so the gate
    would report "healthy" on a degraded one. Python's ``re`` supports
    lookaround just as JS does, so compiling here proves the pattern's only
    sin is a construct RE2 lacks.
    """
    for pattern in _canary_patterns():
        re.compile(pattern.replace("(?<currentValue>", "(?P<currentValue>"))


def test_canary_manager_matches_no_real_file() -> None:
    """The canary must be inert if it ever escaped into a real Renovate run."""
    managers = renovate_validate.RE2_CANARY_CONFIG["customManagers"]
    assert isinstance(managers, list)
    for manager in managers:
        for glob in manager["managerFilePatterns"]:
            assert "never-matches" in glob


# --------------------------------------------------------------------------
# Isolated logic — inject at the subprocess boundary
# --------------------------------------------------------------------------


def _fake_runs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    canary_rc: int,
    real_rc: int = 0,
) -> list[Path]:
    """Record every validated path; answer the canary and the real config."""
    seen: list[Path] = []

    def fake(config_path: Path) -> renovate_validate.ValidatorRun:
        seen.append(config_path)
        is_canary = config_path.parent != REPO_ROOT
        rc = canary_rc if is_canary else real_rc
        return renovate_validate.ValidatorRun(rc, f"fake output rc={rc}")

    monkeypatch.setattr(renovate_validate, "run_validator", fake)
    return seen


def test_degraded_engine_fails_even_though_the_config_is_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canary rc=0 means JS RegExp fallback: fail, whatever the config says."""
    _fake_runs(monkeypatch, canary_rc=0, real_rc=0)
    assert renovate_validate.renovate_validate_main(REPO_ROOT) == 1


def test_degraded_engine_never_validates_the_real_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordering is a safety property, not a style choice.

    If the real validation ran first it would print a green line, and the
    failure mode this module exists for would be reported as a pass with a
    footnote. Assert the real config is never even reached.
    """
    seen = _fake_runs(monkeypatch, canary_rc=0, real_rc=0)
    renovate_validate.renovate_validate_main(REPO_ROOT)
    assert all(p.parent != REPO_ROOT for p in seen), (
        f"real config was validated despite a degraded engine: {seen}"
    )


def test_healthy_engine_and_valid_config_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_runs(monkeypatch, canary_rc=1, real_rc=0)
    assert renovate_validate.renovate_validate_main(REPO_ROOT) == 0


def test_healthy_engine_propagates_a_real_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuine config error must still fail — the gate is additive."""
    _fake_runs(monkeypatch, canary_rc=1, real_rc=7)
    assert renovate_validate.renovate_validate_main(REPO_ROOT) == 7


def test_missing_config_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        renovate_validate,
        "run_validator",
        lambda _p: renovate_validate.ValidatorRun(1, ""),
    )
    assert renovate_validate.renovate_validate_main(tmp_path) == 1


# --------------------------------------------------------------------------
# Real-repo guards — drive the actual validator
# --------------------------------------------------------------------------

_VALIDATOR = shutil.which(renovate_validate.VALIDATOR)
_needs_validator = pytest.mark.skipif(
    _VALIDATOR is None, reason=f"{renovate_validate.VALIDATOR} not on PATH"
)


@_needs_validator
def test_the_real_engine_rejects_the_canary() -> None:
    """The end-to-end arm: a healthy RE2 engine must refuse the lookahead.

    A failure here means the validator on PATH has lost its OPTIONAL ``re2``
    dependency and every regex in renovate.json is going unchecked (#644) —
    which is precisely the condition the gate reports, so this test failing IS
    the finding, not a flaky test.
    """
    run = renovate_validate.engine_rejects_lookahead()
    assert run.returncode != 0, (
        "the validator accepted a negative lookahead, so it is running without "
        f"RE2. Reinstall renovate to restore its optional re2 dep.\n{run.output}"
    )


@_needs_validator
def test_the_repo_config_passes_the_full_gate() -> None:
    """This repo's renovate.json must validate under a confirmed-RE2 engine."""
    assert renovate_validate.renovate_validate_main(REPO_ROOT) == 0


@_needs_validator
def test_cli_wires_end_to_end() -> None:
    """The `renovate-validate` subcommand must exist and dispatch."""
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            "python",
            "dotfiles-setup",
            "renovate-validate",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_canary_config_is_serialisable() -> None:
    """The canary is written as JSON; a non-serialisable value would crash."""
    json.dumps(renovate_validate.RE2_CANARY_CONFIG)
