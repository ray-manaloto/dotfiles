# Copyright (c) 2026 Raymond Manaloto
"""Tests for the light graphify nudge module used by the merged PreToolUse hook."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import graphify_hook

if TYPE_CHECKING:
    import pytest

_MANDATORY = (
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
    '"additionalContext":"MANDATORY: graphify-out/graph.json exists. You MUST run '
    '`graphify query \\"q\\"` first."}}\n'
)
_STALE = (
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":'
    '"graphify-out/graph.json exists but may be STALE for this file. Run '
    '`graphify update`."}}\n'
)


def _counting_run(monkeypatch: pytest.MonkeyPatch, stdout: str) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(
        args: list[str], *, cwd: Path, stdin: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        _ = cwd, stdin
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr("dotfiles_setup.graphify_hook._run", fake_run)
    return calls


def test_search_after_the_session_nudge_does_not_spawn_graphify(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The second search in a session costs no graphify process at all."""
    calls = _counting_run(monkeypatch, _MANDATORY)
    payload = '{"session_id":"s1","tool_input":{"pattern":"x"}}'
    first = graphify_hook.nudge(tmp_path, "search", payload)
    second = graphify_hook.nudge(tmp_path, "search", payload)
    assert "mise run graphify-query" in first
    assert second == ""
    assert len(calls) == 1


def test_read_after_the_session_nudge_still_spawns_for_stale_notices(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Control arm: READ keeps spawning — its stale-file notice is per file."""
    calls = _counting_run(monkeypatch, _MANDATORY)
    payload = '{"session_id":"s2","tool_input":{"file_path":"a.py"}}'
    assert graphify_hook.nudge(tmp_path, "search", payload)
    calls_after_first = len(calls)
    stale_calls = _counting_run(monkeypatch, _STALE)
    out = graphify_hook.nudge(tmp_path, "read", payload)
    assert calls_after_first == 1
    assert len(stale_calls) == 1
    assert "mise run graphify-rebuild" in out


def test_a_session_less_search_always_spawns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No session id, nothing to key the skip on: every call asks graphify."""
    calls = _counting_run(monkeypatch, _MANDATORY)
    for _ in range(2):
        assert graphify_hook.nudge(tmp_path, "search", "{}")
    assert len(calls) == 2


def test_a_timed_out_graphify_yields_no_nudge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def slow(
        args: list[str], *, cwd: Path, stdin: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        _ = cwd, stdin
        raise subprocess.TimeoutExpired(args, 10.0)

    monkeypatch.setattr("dotfiles_setup.graphify_hook._run", slow)
    assert graphify_hook.nudge(tmp_path, "search", "{}") == ""


def test_the_binary_is_the_venv_graphify_not_a_path_lookup() -> None:
    """Run from the venv interpreter directly, PATH would find the mise shim."""
    binary = Path(graphify_hook.graphify_binary())
    assert binary.parent == Path(sys.executable).parent
    assert binary.name == "graphify"


def test_real_graphify_search_emits_only_the_general_nudge(tmp_path: Path) -> None:
    """The premise of the search skip, asserted against the LOCKED graphify.

    graphify's search branch can print only its general ``MANDATORY`` nudge, so
    once a session has that nudge a further search spawn is pure cost. If an
    upgrade makes search emit anything else (a per-file notice, a deny), this
    goes red before the skip can swallow it.
    """
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text('{"nodes": [], "links": []}')
    for payload in (
        {"tool_name": "Grep", "tool_input": {"pattern": "x"}},
        {"tool_name": "Bash", "tool_input": {"command": "rg needle src/"}},
    ):
        result = subprocess.run(
            [graphify_hook.graphify_binary(), "hook-guard", "search"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        hook = json.loads(result.stdout)["hookSpecificOutput"]
        assert set(hook) == {"hookEventName", "additionalContext"}, hook
        assert hook["additionalContext"].startswith("MANDATORY:")
    # Control arm: the same probe on a non-search Bash command prints nothing.
    quiet = subprocess.run(
        [graphify_hook.graphify_binary(), "hook-guard", "search"],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "true"}}),
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert quiet.stdout == ""
