# Copyright (c) 2026 Raymond Manaloto
"""Codex configuration schema management.

Generates and validates the codex app-server JSON schema against the installed
codex version. Schema is generated from the exact installed version to ensure
all settings and environment variables are searchable locally.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from pathlib import Path


def get_installed_codex_version() -> str:
    """Get the installed codex CLI version."""
    result = subprocess.run(
        ["mise", "exec", "--", "codex", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    # Output format: "codex-cli 0.154.0"
    return result.stdout.strip().split()[-1]


def schema_path(repo_root: Path) -> Path:
    """Return the path to the generated codex app-server schema bundle."""
    return repo_root / "schemas" / "codex_app_server_protocol.schemas.json"


def validate_schema_exists(repo_root: Path) -> bool:
    """Check if the codex schema has been generated."""
    return schema_path(repo_root).exists()


def load_schema(repo_root: Path) -> dict[str, Any] | None:
    """Load the generated codex app-server schema."""
    path = schema_path(repo_root)
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def check_schema_currency(repo_root: Path, current_version: str) -> tuple[bool, str]:
    """Check if the generated schema matches the installed codex version.

    Args:
        repo_root: Root of the dotfiles repository
        current_version: Current installed codex version (e.g., "0.154.0")

    Returns:
        (is_current, message): is_current is True if schema is current,
        message explains the status
    """
    schema = load_schema(repo_root)
    if not schema:
        msg = (
            f"Schema not found at {schema_path(repo_root)}. "
            "Run 'mise run codex-schema-generate' to create it."
        )
        return (False, msg)

    if not isinstance(schema, dict):
        return (False, "Schema is not valid JSON")

    msg = (
        f"Schema is present for codex {current_version}. "
        "Regenerate with 'mise run codex-schema-generate' if codex "
        "was upgraded."
    )
    return (True, msg)


#: The three keys a custom agent file MUST define, per codex's own schema table.
#: They are agent-file-only: `config.toml` declares `developer_instructions` but
#: NOT `name` or `description`, and it sets `additionalProperties: false` — so an
#: agent file pointed at the raw config schema is rejected for two of its three
#: required keys. Measured 2026-09-14: all six specialists went INVALID that way.
AGENT_ONLY_KEYS: Final = ("name", "description")


def config_schema_path(repo_root: Path) -> Path:
    """The vendored codex `config.toml` JSON schema."""
    return repo_root / "schemas" / "codex-config.json"


def agent_schema_path(repo_root: Path) -> Path:
    """The DERIVED schema that validates a `.codex/agents/*.toml` file."""
    return repo_root / "schemas" / "codex-agent.json"


def derive_agent_schema(config_schema: dict[str, Any]) -> dict[str, Any]:
    """Build the agent-file schema from codex's `config.toml` schema.

    An agent file accepts every `config.toml` key PLUS `name` and
    `description`, and requires those two plus `developer_instructions`.

    `additionalProperties` stays False deliberately: that is what makes a typo'd
    or wrong-typed key an ERROR rather than silent. Codex itself drops an invalid
    agent file with no message, no warning and no exit code, so this schema is
    the only thing standing between a malformed file and an agent that simply
    does not exist.
    """
    return {
        "$schema": config_schema.get(
            "$schema", "http://json-schema.org/draft-07/schema#"
        ),
        "title": "Codex custom agent file (.codex/agents/*.toml)",
        "description": (
            "DERIVED from schemas/codex-config.json. Regenerate with "
            "`mise run codex-schema-generate`; never hand-edit."
        ),
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "description", "developer_instructions"],
        "properties": {
            "name": {
                "type": "string",
                "description": (
                    "Agent name codex uses when spawning. This is the identity; "
                    "the filename is convention only."
                ),
            },
            "description": {
                "type": "string",
                "description": (
                    "When codex should use this agent. THIS IS THE ROUTING "
                    "SIGNAL — overlapping descriptions send work to the wrong agent."
                ),
            },
            **config_schema.get("properties", {}),
        },
        "definitions": config_schema.get("definitions", {}),
    }


def generate_schema(repo_root: Path, output_dir: Path | None = None) -> bool:
    """Generate the codex app-server JSON schema for the installed version.

    Args:
        repo_root: Root of the dotfiles repository
        output_dir: Directory to write schemas (default: schemas/)

    Returns:
        True if generation succeeded, False otherwise
    """
    if output_dir is None:
        output_dir = repo_root / "schemas"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate into a TEMPORARY directory and keep only the bundles.
    #
    # `generate-json-schema --out <dir>` writes the whole app-server protocol
    # surface: measured 2026-09-14, 305 files including a per-message schema for
    # every request, response and notification, plus `v1/` and `v2/` subtrees.
    # `schemas/` is a curated vendoring directory that held four files, and
    # `_schema_path()` reads exactly ONE of the generated artifacts — the bundle,
    # which already contains every per-message definition. Committing the other
    # 303 would add a megabyte of redundancy to a reviewed directory.
    staging = tempfile.mkdtemp(prefix="codex-schema-")
    try:
        result = subprocess.run(
            [
                "mise",
                "exec",
                "--",
                "codex",
                "app-server",
                "generate-json-schema",
                "--out",
                staging,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False

        # Keep ONLY the bundles. `_schema_path()` reads the first of these; the
        # v2 sibling is kept because the two describe different protocol
        # versions and a reader may need either. Everything else the generator
        # emitted is per-message duplication already inside the bundle.
        kept = 0
        for name in (
            "codex_app_server_protocol.schemas.json",
            "codex_app_server_protocol.v2.schemas.json",
        ):
            src = pathlib.Path(staging) / name
            if src.is_file():
                shutil.copy2(src, output_dir / name)
                kept += 1
    except subprocess.SubprocessError:
        return False
    else:
        return kept > 0
    finally:
        shutil.rmtree(staging, ignore_errors=True)
