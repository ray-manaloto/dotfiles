"""Tests for the host-side hook self-check (dotfiles_setup.hook_selfcheck).

The self-check drives the WIRED hook entrypoints end-to-end; it is the
ship/land ``hook-selfcheck`` gate. Unit tests cover the pure helpers (wiring
parse, JSON extraction, in-process decide smoke); one integration test runs
the whole thing against the real repo so a wiring/wrapper regression fails
the gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import hook_selfcheck

_REPO = Path(__file__).parent.parent
_REAL_SETTINGS = _REPO / ".claude" / "settings.json"


def test_real_settings_wiring_passes() -> None:
    assert hook_selfcheck.check_settings_wiring(_REAL_SETTINGS) == []


def test_guard_decisions_smoke_passes() -> None:
    assert hook_selfcheck.check_guard_decisions() == []


def _wiring(tmp_path: Path, settings: dict) -> list[str]:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(settings))
    return hook_selfcheck.check_settings_wiring(path)


def _hook(matcher: str | None, command: str) -> dict:
    entry: dict[str, object] = {"hooks": [{"type": "command", "command": command}]}
    if matcher is not None:
        entry["matcher"] = matcher
    return entry


_ANCHOR = '"${CLAUDE_PROJECT_DIR:-.}"'


def _full_settings() -> dict:
    """A minimally-complete, passing settings shape for tampering in tests.

    Every command anchors its paths to ``$CLAUDE_PROJECT_DIR`` — hooks run in
    the session's cwd, so the unanchored form silently fails open in a
    cross-repo session (#343).
    """
    return {
        "hooks": {
            "PreToolUse": [
                _hook(
                    "Bash|AskUserQuestion",
                    f"bash {_ANCHOR}/scripts/pretooluse-guard.sh",
                )
            ],
            "SessionStart": [
                _hook(
                    "startup|resume",
                    'if [ "$CLAUDE_CODE_REMOTE" = "true" ]; then '
                    f"bash {_ANCHOR}/scripts/web-setup.sh; else "
                    f"mise -C {_ANCHOR} run tool-currency-check; "
                    f"mise -C {_ANCHOR} run doctor; fi",
                )
            ],
            "SessionEnd": [
                _hook(
                    None,
                    f"mise -C {_ANCHOR} run command-audit -- "
                    f"--output {_ANCHOR}/.agent/command-audit.md",
                )
            ],
        }
    }


def test_synthetic_full_settings_passes(tmp_path: Path) -> None:
    assert _wiring(tmp_path, _full_settings()) == []


def test_missing_event_fails(tmp_path: Path) -> None:
    settings = _full_settings()
    del settings["hooks"]["PreToolUse"]
    failures = _wiring(tmp_path, settings)
    assert any("PreToolUse" in f for f in failures)


def test_missing_matcher_fails(tmp_path: Path) -> None:
    settings = _full_settings()
    # Strip the Bash matcher off PreToolUse — a tool event without a matcher
    # fires on every tool, which the check must reject.
    settings["hooks"]["PreToolUse"] = [_hook(None, "bash scripts/pretooluse-guard.sh")]
    failures = _wiring(tmp_path, settings)
    assert any("PreToolUse" in f and "matcher" in f for f in failures)


def test_partial_matcher_fails(tmp_path: Path) -> None:
    """A matcher covering only SOME guarded tools must fail.

    The realistic regression: someone reverts PreToolUse to ``"Bash"`` and the
    ask-quality gate goes silently absent for AskUserQuestion. A check that
    merely looked for ``"Bash"`` somewhere in the matcher would still pass.
    """
    settings = _full_settings()
    settings["hooks"]["PreToolUse"] = [
        _hook("Bash", f"bash {_ANCHOR}/scripts/pretooluse-guard.sh")
    ]
    failures = _wiring(tmp_path, settings)
    assert any("AskUserQuestion" in f for f in failures)
    assert not any("'Bash'" in f for f in failures)


def test_wrong_command_fails(tmp_path: Path) -> None:
    settings = _full_settings()
    settings["hooks"]["SessionStart"] = [_hook("startup|resume", "bash other.sh")]
    failures = _wiring(tmp_path, settings)
    assert any("SessionStart" in f for f in failures)


def test_session_start_without_the_doctor_fails(tmp_path: Path) -> None:
    """The #418 project doctor is wired ONLY here, so only this can protect it.

    It reads ``~/.config/fnox`` and ``~/.claude``, so it can never be an hk step
    or a CI job — settings.json is its single point of failure.
    """
    settings = _full_settings()
    settings["hooks"]["SessionStart"] = [
        _hook("startup|resume", f"mise -C {_ANCHOR} run tool-currency-check")
    ]
    failures = _wiring(tmp_path, settings)
    assert any("SessionStart" in f and "run doctor" in f for f in failures)


def test_session_start_without_the_currency_check_fails(tmp_path: Path) -> None:
    """Its sibling checkup — the doctor delegates pin drift to it, so it must run."""
    settings = _full_settings()
    settings["hooks"]["SessionStart"] = [
        _hook("startup|resume", f"mise -C {_ANCHOR} run doctor")
    ]
    failures = _wiring(tmp_path, settings)
    assert any("SessionStart" in f and "tool-currency-check" in f for f in failures)


def test_missing_session_end_fails(tmp_path: Path) -> None:
    """The recurring command-audit loop must stay wired (SessionEnd hook)."""
    settings = _full_settings()
    del settings["hooks"]["SessionEnd"]
    failures = _wiring(tmp_path, settings)
    assert any("SessionEnd" in f for f in failures)


def test_session_end_without_output_path_fails(tmp_path: Path) -> None:
    """A SessionEnd that drops `--output` would print to a debug log, not the report."""
    settings = _full_settings()
    settings["hooks"]["SessionEnd"] = [_hook(None, "mise run command-audit")]
    failures = _wiring(tmp_path, settings)
    assert any("SessionEnd" in f and "command-audit.md" in f for f in failures)


def test_unreadable_settings_fails(tmp_path: Path) -> None:
    failures = hook_selfcheck.check_settings_wiring(tmp_path / "nope.json")
    assert len(failures) == 1


def test_selfcheck_main_passes_on_real_repo() -> None:
    """End-to-end: drives the real wrappers; the ship/land gate itself."""
    assert hook_selfcheck.hook_selfcheck_main(_REPO) == 0


# --- #343: hooks run in the session's cwd, not the project root -------------
#
# A hook command naming a bare relative path resolves against whatever
# directory the session happens to be in. Measured: 125 Bash calls the guard
# denies executed unchecked while the cwd was a sibling repo, because
# `bash scripts/pretooluse-guard.sh` was not there (rc=127) and a non-zero
# non-2 PreToolUse exit is a NON-BLOCKING error that lets the call proceed.


@pytest.mark.parametrize(
    "event",
    ["PreToolUse", "SessionStart", "SessionEnd"],
)
def test_unanchored_hook_command_fails(tmp_path: Path, event: str) -> None:
    """The FAIL direction: strip the anchor off any event and it must go red."""
    settings = _full_settings()
    for entry in settings["hooks"][event]:
        for hook in entry["hooks"]:
            hook["command"] = hook["command"].replace(_ANCHOR, ".")
    failures = _wiring(tmp_path, settings)
    assert any(event in f and "CLAUDE_PROJECT_DIR" in f for f in failures), failures


def test_anchored_hook_command_passes(tmp_path: Path) -> None:
    """The PASS direction, so the check above is not merely always-red."""
    assert _wiring(tmp_path, _full_settings()) == []


def test_a_newly_added_hook_must_also_be_anchored(tmp_path: Path) -> None:
    """The check reads the whole hook block, not a fixed list of known events.

    A hook added later is the likeliest way this defect returns, so it must be
    covered without anyone remembering to extend a list.
    """
    settings = _full_settings()
    settings["hooks"]["PostToolUse"] = [_hook("Bash", "bash scripts/something-new.sh")]
    failures = _wiring(tmp_path, settings)
    assert any("PostToolUse" in f and "CLAUDE_PROJECT_DIR" in f for f in failures)


def test_real_wrapper_denies_from_a_foreign_cwd() -> None:
    """The arm the old end-to-end check could not run: deny with cwd != repo.

    Both pre-existing arms passed ``cwd=project_root``, which is precisely why
    the defect survived — the probe could only ever exercise the one directory
    where the relative paths happened to resolve.
    """
    wrapper = str(_REPO / hook_selfcheck.PRETOOLUSE_WRAPPER)
    assert hook_selfcheck.check_offroot_arm(_REPO, wrapper) == []
