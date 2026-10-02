# Copyright (c) 2026 Raymond Manaloto
"""Tests for the merged per-tool-call PreToolUse hook (dotfiles_setup.hook_dispatch).

Two layers: :func:`hook_dispatch.dispatch` in process (which half decides for
which tool), and the REAL wired wrapper ``scripts/pretooluse-guard.sh`` driven
through ``/bin/bash`` exactly as ``.claude/settings.json`` runs it, including
its two fallbacks (``uv run`` when the venv is absent, a recorded fail-open when
nothing can run).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from dotfiles_setup import hook_dispatch

_ROOT = Path(__file__).parent.parent.absolute()
_WRAPPER = _ROOT / "scripts" / "pretooluse-guard.sh"
_DENIED = "gh pr create --fill"
_NUDGE = (
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":'
    '"MANDATORY: graphify-out/graph.json exists. You MUST run '
    '`graphify query \\"q\\"` first."}}\n'
)


def _payload(tool: str, **tool_input: str) -> str:
    return json.dumps({"tool_name": tool, "tool_input": tool_input})


@pytest.fixture
def graphify_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace graphify's subprocess (the boundary) and record each kind asked."""
    kinds: list[str] = []

    def fake_run(
        args: list[str], *, cwd: Path, stdin: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        _ = cwd, stdin
        kinds.append(args[-1])
        return subprocess.CompletedProcess(args, 0, stdout=_NUDGE, stderr="")

    monkeypatch.setattr("dotfiles_setup.graphify_hook._run", fake_run)
    return kinds


def test_a_denied_bash_call_denies_and_skips_graphify(
    tmp_path: Path, graphify_calls: list[str]
) -> None:
    out = hook_dispatch.dispatch(tmp_path, _payload("Bash", command=_DENIED))
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert graphify_calls == []


def test_an_allowed_bash_call_gets_the_search_nudge(
    tmp_path: Path, graphify_calls: list[str]
) -> None:
    out = hook_dispatch.dispatch(tmp_path, _payload("Bash", command="rg x src/"))
    assert "permissionDecision" not in out
    assert "mise run graphify-query" in out
    assert graphify_calls == ["search"]


@pytest.mark.parametrize(
    ("tool", "kind"), [("Grep", "search"), ("Read", "read"), ("Glob", "read")]
)
def test_graphify_tools_are_nudged_never_decided(
    tmp_path: Path, graphify_calls: list[str], tool: str, kind: str
) -> None:
    # A Read/Grep payload that would DENY if it reached the Bash guard as a
    # command: proves these tools never route through the policy guard.
    out = hook_dispatch.dispatch(tmp_path, _payload(tool, command=_DENIED))
    assert "permissionDecision" not in out
    assert graphify_calls == [kind]


@pytest.mark.parametrize("tool", ["Edit", "Write", "NotebookEdit", "AskUserQuestion"])
def test_guard_only_tools_never_spawn_graphify(
    tmp_path: Path, graphify_calls: list[str], tool: str
) -> None:
    hook_dispatch.dispatch(tmp_path, _payload(tool, file_path=str(tmp_path / "f")))
    assert graphify_calls == []


def test_an_unknown_tool_is_silent(tmp_path: Path, graphify_calls: list[str]) -> None:
    assert hook_dispatch.dispatch(tmp_path, _payload("Task", prompt="x")) == ""
    assert graphify_calls == []


def test_a_payload_without_tool_name_keeps_the_legacy_bash_shape(
    tmp_path: Path, graphify_calls: list[str]
) -> None:
    out = hook_dispatch.dispatch(tmp_path, json.dumps({"command": _DENIED}))
    assert '"deny"' in out
    assert graphify_calls == []


def _wrapper(
    payload: str, tmp_path: Path, **env: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(_WRAPPER)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(_ROOT),
            "DOTFILES_GUARD_FAILOPEN_LOG": str(tmp_path / "fail-open.log"),
            **env,
        },
        timeout=120,
    )


def test_wrapper_fast_path_denies_and_allows(tmp_path: Path) -> None:
    denied = _wrapper(_payload("Bash", command=_DENIED), tmp_path)
    allowed = _wrapper(_payload("Edit", file_path=str(tmp_path / "f")), tmp_path)
    assert denied.returncode == 0, denied.stderr
    assert '"permissionDecision": "deny"' in denied.stdout
    assert allowed.returncode == 0, allowed.stderr
    assert allowed.stdout == ""
    assert not (tmp_path / "fail-open.log").exists()


def test_wrapper_falls_back_to_uv_run_without_the_venv(tmp_path: Path) -> None:
    """No venv interpreter at the resolved path: `uv run` still decides."""
    denied = _wrapper(
        _payload("Bash", command=_DENIED),
        tmp_path,
        UV_PROJECT_ENVIRONMENT=str(tmp_path / "no-venv"),
    )
    assert denied.returncode == 0, denied.stderr
    assert '"permissionDecision": "deny"' in denied.stdout


def test_wrapper_fails_open_and_records_it_when_nothing_can_run(tmp_path: Path) -> None:
    """No venv AND no uv on PATH: allow (rc 0, silent) and log the fail-open."""
    result = _wrapper(
        _payload("Bash", command=_DENIED),
        tmp_path,
        UV_PROJECT_ENVIRONMENT=str(tmp_path / "no-venv"),
        PATH="/usr/bin:/bin",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "interpreter-absent" in (tmp_path / "fail-open.log").read_text()
