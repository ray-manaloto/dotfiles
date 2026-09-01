# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.mise_config_context` (PostToolUse injector).

The point of every test here is the NEGATIVE arm. A reminder hook that fires on
everything is noise nobody reads, and one that fires on nothing is
indistinguishable from not being installed — and nothing would report either.
So each in-scope assertion is paired with an out-of-scope one that must stay
silent.
"""

from __future__ import annotations

import io
import json
import os
import time
from pathlib import Path

import pytest
from dotfiles_setup.mise_config_context import (
    CONTEXT,
    MARKER_MAX_AGE_SECONDS,
    MISE_CONFIG_GLOBS,
    STATE_DIR,
    already_seen,
    build_payload,
    matches,
    mise_config_context_main,
)

IN_SCOPE = (
    "mise.toml",
    "mise.local.toml",
    ".config/mise/config.toml",
    ".config/mise/conf.d/shared.toml",
    ".devcontainer/mise-system.toml",
    ".devcontainer/mise-runtime.toml",
)

OUT_OF_SCOPE = (
    "README.md",
    "AGENTS.md",
    "docker-bake.hcl",
    "python/src/dotfiles_setup/lint.py",
    # Lockfiles are generated artifacts: editing one is not a place where a
    # native-vs-custom decision is being made, so the reminder would be noise.
    "mise.lock",
    ".config/mise/mise.lock",
    ".devcontainer/mise-system.lock",
    # A near-miss on the glob: same directory, not a mise config.
    ".devcontainer/devcontainer.json",
)


@pytest.mark.parametrize("rel", IN_SCOPE)
def test_mise_config_paths_match(tmp_path: Path, rel: str) -> None:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("")
    assert matches(str(target), tmp_path)


@pytest.mark.parametrize("rel", OUT_OF_SCOPE)
def test_other_paths_do_not_match(tmp_path: Path, rel: str) -> None:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("")
    assert not matches(str(target), tmp_path)


def test_a_mise_toml_outside_the_repo_does_not_match(tmp_path: Path) -> None:
    """Containment, not basename.

    A global `~/.config/mise/config.toml` is not this project's decision to
    govern, and a basename check would claim it.
    """
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "mise.toml").write_text("")
    repo = tmp_path / "repo"
    repo.mkdir()
    assert not matches(str(elsewhere / "mise.toml"), repo)


def test_payload_is_a_valid_posttooluse_response(tmp_path: Path) -> None:
    (tmp_path / "mise.toml").write_text("")
    payload = build_payload(str(tmp_path / "mise.toml"), tmp_path)
    assert payload is not None
    out = payload["hookSpecificOutput"]
    assert isinstance(out, dict)
    assert out["hookEventName"] == "PostToolUse"
    assert str(tmp_path / "mise.toml") in str(out["additionalContext"])


def test_out_of_scope_payload_is_none(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("")
    assert build_payload(str(tmp_path / "README.md"), tmp_path) is None


def test_context_is_phrased_as_statements_not_commands() -> None:
    """Claude Code surfaces imperative hook text to the user instead of using it.

    Its docs: text "framed as out-of-band system commands can trigger Claude's
    prompt-injection defenses". This pins the phrasing so a later edit cannot
    quietly turn the reminder into a directive and neuter it.
    """
    body = CONTEXT.lower()
    for imperative in ("you must", "always ", "never ", "do not ", "stop and "):
        assert imperative not in body, f"imperative phrasing: {imperative!r}"


def test_context_names_the_rule_and_the_local_docs(tmp_path: Path) -> None:
    """The hook carries the CONDITIONAL half; the rule itself is already eager.

    Asserted against the RENDERED text, not the template: the template holds
    `{docs}`, so checking it would pass while the reader saw a placeholder.
    """
    (tmp_path / "mise.toml").write_text("")
    payload = build_payload(str(tmp_path / "mise.toml"), tmp_path)
    assert payload is not None
    out = payload["hookSpecificOutput"]
    assert isinstance(out, dict)
    rendered = str(out["additionalContext"])
    assert "use-tool-builtins.md" in rendered
    assert "knowledge-base/sources/mise/docs" in rendered
    for placeholder in ("{path}", "{docs}"):
        assert placeholder not in rendered, f"unrendered {placeholder}"
    # It must not restate the rule body — that would duplicate eager context.
    assert len(rendered) < 1500


def test_main_emits_json_for_an_in_scope_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "mise.toml").write_text("")
    event = {"tool_input": {"file_path": str(tmp_path / "mise.toml")}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    assert mise_config_context_main(tmp_path) == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]


def test_main_is_silent_for_an_out_of_scope_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "README.md").write_text("")
    event = {"tool_input": {"file_path": str(tmp_path / "README.md")}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    assert mise_config_context_main(tmp_path) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("raw", ["", "not json", '{"tool_input": null}', "{}"])
def test_malformed_input_exits_zero_and_says_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    raw: str,
) -> None:
    """A reminder hook must never turn a malformed payload into a visible error."""
    monkeypatch.setattr("sys.stdin", io.StringIO(raw))
    assert mise_config_context_main(tmp_path) == 0
    assert capsys.readouterr().out == ""


def test_globs_cover_every_tracked_mise_config() -> None:
    """The glob set must not silently fall behind the repo's real config files.

    Control-armed: this walks the actual tree rather than trusting the list, so
    adding `.config/mise/conf.d/<new>.toml` without widening the globs fails
    here instead of going unnoticed.
    """
    repo = Path(__file__).resolve().parent.parent
    real = [
        p
        for p in (
            repo / "mise.toml",
            repo / ".devcontainer" / "mise-system.toml",
            repo / ".devcontainer" / "mise-runtime.toml",
            *sorted((repo / ".config" / "mise" / "conf.d").glob("*.toml")),
        )
        if p.exists()
    ]
    assert real, "control arm: found no mise config files at all — probe is broken"
    for path in real:
        assert matches(str(path), repo), f"{path} is not covered by MISE_CONFIG_GLOBS"


def test_glob_list_has_no_duplicates() -> None:
    assert len(set(MISE_CONFIG_GLOBS)) == len(MISE_CONFIG_GLOBS)


# --- session-scoped dedup (the reminder is worth reading once, not ten times)


def _event(root: Path, session: str | None = "S1") -> dict[str, object]:
    payload: dict[str, object] = {"tool_input": {"file_path": str(root / "mise.toml")}}
    if session is not None:
        payload["session_id"] = session
    return payload


def test_second_edit_in_the_same_session_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "mise.toml").write_text("")
    for expected in (True, False, False):
        monkeypatch.setattr(
            "sys.stdin", io.StringIO(json.dumps(_event(tmp_path, "S1")))
        )
        assert mise_config_context_main(tmp_path) == 0
        emitted = bool(capsys.readouterr().out)
        assert emitted is expected


def test_a_different_session_is_told_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "mise.toml").write_text("")
    for session in ("S1", "S2"):
        monkeypatch.setattr(
            "sys.stdin", io.StringIO(json.dumps(_event(tmp_path, session)))
        )
        assert mise_config_context_main(tmp_path) == 0
        assert capsys.readouterr().out, f"session {session} should be told once"


def test_a_missing_session_id_still_emits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing to key on: an un-deduplicated reminder beats a disabled one."""
    (tmp_path / "mise.toml").write_text("")
    for _ in range(2):
        monkeypatch.setattr(
            "sys.stdin", io.StringIO(json.dumps(_event(tmp_path, None)))
        )
        assert mise_config_context_main(tmp_path) == 0
        assert capsys.readouterr().out


def test_an_unwritable_state_dir_emits_rather_than_going_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A broken marker store must be NOISY, not quietly disabled.

    A repeating reminder is visible and fixable; a gate that stopped firing is
    neither, and nothing would report it.
    """
    (tmp_path / "mise.toml").write_text("")

    def _boom(*_args: object, **_kwargs: object) -> None:
        msg = "read-only"
        raise OSError(msg)

    monkeypatch.setattr(Path, "mkdir", _boom)
    for _ in range(2):
        monkeypatch.setattr(
            "sys.stdin", io.StringIO(json.dumps(_event(tmp_path, "S1")))
        )
        assert mise_config_context_main(tmp_path) == 0
        assert capsys.readouterr().out


def test_stale_markers_are_pruned(tmp_path: Path) -> None:
    state = tmp_path / STATE_DIR
    state.mkdir(parents=True)
    stale = state / "OLD.seen"
    stale.write_text("")
    old = time.time() - MARKER_MAX_AGE_SECONDS - 60
    os.utime(stale, (old, old))
    fresh = state / "RECENT.seen"
    fresh.write_text("")

    already_seen(tmp_path, "NEW")

    assert not stale.exists(), "a marker past the age floor should be swept"
    assert fresh.exists(), "a fresh marker must survive"


def test_each_agent_in_one_session_is_told_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Subagents share a session_id but do not share tool results.

    Keyed on session alone, the first agent consumed the reminder for every
    sibling — confirmed by replay in a cold review.
    """
    (tmp_path / "mise.toml").write_text("")
    for agent in ("A", "B"):
        event = {
            "session_id": "S1",
            "agent_id": agent,
            "tool_input": {"file_path": str(tmp_path / "mise.toml")},
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
        assert mise_config_context_main(tmp_path) == 0
        assert capsys.readouterr().out, f"agent {agent} should be told once"
    # ...and still only once each.
    event = {
        "session_id": "S1",
        "agent_id": "A",
        "tool_input": {"file_path": str(tmp_path / "mise.toml")},
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    assert mise_config_context_main(tmp_path) == 0
    assert capsys.readouterr().out == ""


def test_settings_wires_this_hook_without_depending_on_a_mise_task() -> None:
    """The live integration, asserted — deleting it left every test green.

    It must NOT invoke `mise run`: the task is defined in mise.toml, one of the
    files this hook guards, so a wholesale Write replacing that file would
    delete the task before PostToolUse could run it.
    """
    repo = Path(__file__).resolve().parent.parent
    settings = json.loads((repo / ".claude" / "settings.json").read_text())
    entries = settings.get("hooks", {}).get("PostToolUse", [])
    assert entries, "PostToolUse hook is not wired at all"
    commands = [
        h.get("command", "")
        for entry in entries
        for h in entry.get("hooks", [])
        if "mise-config-context" in h.get("command", "")
    ]
    assert commands, "no PostToolUse hook invokes mise-config-context"
    for command in commands:
        assert "mise run" not in command, "hook must not depend on a mise.toml task"
        assert "dotfiles-setup mise-config-context" in command
    matchers = [e.get("matcher", "") for e in entries]
    assert any("Write" in m and "Edit" in m for m in matchers)
    timeouts = [h.get("timeout") for e in entries for h in e.get("hooks", [])]
    assert all(t for t in timeouts), "an untimed hook can hang every write"
