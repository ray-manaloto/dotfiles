# Copyright (c) 2026 Raymond Manaloto
"""Tests for the Codex SDLC agent schema and roster gate."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import codex_agent_validate as cav
from dotfiles_setup import main as cli

if TYPE_CHECKING:
    from pathlib import Path


def _write_schema(repo_root: Path) -> None:
    """Write an independent minimal schema exercising the production contract."""
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "description", "developer_instructions"],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "developer_instructions": {"type": "string"},
            "model_reasoning_effort": {"$ref": "#/definitions/ReasoningEffort"},
            "mcp_servers": {"type": "object"},
        },
        "definitions": {
            "ReasoningEffort": {"type": "string", "minLength": 1},
        },
    }
    schema_path = repo_root / "schemas" / "codex-agent.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text(json.dumps(schema))


def _agent_text(name: str) -> str:
    """Return one valid agent document for the named roster member."""
    return (
        f'name = "{name}"\n'
        'description = "routing description"\n'
        'model_reasoning_effort = "high"\n'
        'developer_instructions = "review instructions"\n'
    )


def _write_valid_roster(repo_root: Path) -> dict[str, Path]:
    """Create an isolated complete SDLC roster and return paths by declared name."""
    _write_schema(repo_root)
    directory = repo_root / ".codex" / "agents"
    directory.mkdir(parents=True)
    paths: dict[str, Path] = {}
    for name in sorted(cav.EXPECTED_SDLC_ROSTER):
        path = directory / f"codex-{name}.toml"
        path.write_text(_agent_text(name))
        paths[name] = path
    return paths


def test_find_violations_accepts_the_roster_and_rejects_a_deleted_member(
    tmp_path: Path,
) -> None:
    """The gate must fail by declared name when a whole agent file disappears."""
    paths = _write_valid_roster(tmp_path)
    assert cav.find_violations(tmp_path) == []

    missing = "sdlc-python-specialist"
    paths[missing].unlink()
    violations = cav.find_violations(tmp_path)
    assert violations == [f"missing SDLC agent name {missing!r}"]


def test_find_violations_enforces_required_unknown_and_typed_properties(
    tmp_path: Path,
) -> None:
    """Realistic malformed agent shapes must each make the schema gate red."""
    paths = _write_valid_roster(tmp_path)
    target = paths["sdlc-config-specialist"]

    target.write_text(
        'name = "sdlc-config-specialist"\n'
        'description = "routing description"\n'
        'model_reasoning_effort = "high"\n'
    )
    violations = cav.find_violations(tmp_path)
    assert any(
        "missing required key 'developer_instructions'" in violation
        for violation in violations
    )

    target.write_text(
        _agent_text("sdlc-config-specialist") + 'unknown_setting = "typo"\n'
    )
    violations = cav.find_violations(tmp_path)
    assert any("unexpected key 'unknown_setting'" in v for v in violations)

    target.write_text(
        _agent_text("sdlc-config-specialist") + 'mcp_servers = ["context7"]\n'
    )
    violations = cav.find_violations(tmp_path)
    assert any("mcp_servers: expected object, got list" in v for v in violations)


def test_find_violations_rejects_an_unexpected_declared_name(
    tmp_path: Path,
) -> None:
    """Roster identity comes from each TOML name, not its codex-prefixed filename."""
    paths = _write_valid_roster(tmp_path)
    target = paths["sdlc-image-specialist"]
    target.write_text(_agent_text("sdlc-invented-specialist"))

    violations = cav.find_violations(tmp_path)
    assert "missing SDLC agent name 'sdlc-image-specialist'" in violations
    assert "unexpected SDLC agent name 'sdlc-invented-specialist'" in violations


def test_find_violations_reports_invalid_toml_instead_of_raising(
    tmp_path: Path,
) -> None:
    """A silently dropped malformed agent must become a named gate violation."""
    paths = _write_valid_roster(tmp_path)
    target = paths["sdlc-workflows-specialist"]
    target.write_text('name = "unterminated\n')

    violations = cav.find_violations(tmp_path)
    assert any(
        ".codex/agents/codex-sdlc-workflows-specialist.toml: invalid TOML:" in v
        for v in violations
    )
    assert "missing SDLC agent name 'sdlc-workflows-specialist'" in violations


def test_validate_main_has_real_clean_and_missing_roster_exit_arms(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The production entry point must expose violations through rc and stderr."""
    paths = _write_valid_roster(tmp_path)
    assert cav.validate_main([str(tmp_path)]) == 0
    clean = capsys.readouterr()
    assert "6 SDLC agents valid" in clean.out
    assert clean.err == ""

    missing = "sdlc-documentation-specialist"
    paths[missing].unlink()
    assert cav.validate_main([str(tmp_path)]) == 1
    failed = capsys.readouterr()
    assert f"missing SDLC agent name '{missing}'" in failed.err
    assert failed.out == ""


def test_dotfiles_setup_dispatches_the_validator_with_the_selected_root(
    tmp_path: Path,
) -> None:
    """The registered public subcommand must preserve both validator exit arms."""
    paths = _write_valid_roster(tmp_path)
    args = cli.setup_parser().parse_args(["codex-agent-validate"])
    config = cli.DotfilesConfig.model_construct()

    with pytest.raises(SystemExit) as clean_exit:
        cli.run_command(args, tmp_path, config=config)
    assert clean_exit.value.code == 0

    paths["sdlc-dispatcher"].unlink()
    with pytest.raises(SystemExit) as failed_exit:
        cli.run_command(args, tmp_path, config=config)
    assert failed_exit.value.code == 1
