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


def _full_settings() -> dict:
    """A minimally-complete, passing settings shape for tampering in tests."""
    return {
        "hooks": {
            "PreToolUse": [_hook("Bash", "bash scripts/pretooluse-guard.sh")],
            "SessionStart": [
                _hook(
                    "startup|resume",
                    'if [ "$CLAUDE_CODE_REMOTE" = "true" ]; then '
                    "bash scripts/web-setup.sh; fi",
                )
            ],
            "SessionEnd": [
                _hook(
                    None, "mise run command-audit -- --output .agent/command-audit.md"
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


def test_wrong_command_fails(tmp_path: Path) -> None:
    settings = _full_settings()
    settings["hooks"]["SessionStart"] = [_hook("startup|resume", "bash other.sh")]
    failures = _wiring(tmp_path, settings)
    assert any("SessionStart" in f for f in failures)


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
