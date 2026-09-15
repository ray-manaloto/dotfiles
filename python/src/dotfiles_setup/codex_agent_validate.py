# Copyright (c) 2026 Raymond Manaloto
"""Validate the repository's Codex SDLC agents against their derived schema."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any, Final

from dotfiles_setup import _project_root
from dotfiles_setup.codex_schema import agent_schema_path

EXPECTED_SDLC_ROSTER: Final[frozenset[str]] = frozenset(
    {
        "sdlc-dispatcher",
        "sdlc-python-specialist",
        "sdlc-config-specialist",
        "sdlc-workflows-specialist",
        "sdlc-image-specialist",
        "sdlc-documentation-specialist",
    }
)

_AGENT_DIRECTORY: Final = Path(".codex/agents")
_AGENT_GLOB: Final = "codex-sdlc-*.toml"


def _json_type_matches(value: object, expected: str) -> bool:
    """Return whether a TOML value has the named JSON-schema primitive type."""
    if expected == "object":
        matches = isinstance(value, dict)
    elif expected == "array":
        matches = isinstance(value, list)
    elif expected == "string":
        matches = isinstance(value, str)
    elif expected == "boolean":
        matches = isinstance(value, bool)
    elif expected == "integer":
        matches = isinstance(value, int) and not isinstance(value, bool)
    elif expected == "number":
        matches = isinstance(value, int | float) and not isinstance(value, bool)
    elif expected == "null":
        matches = value is None
    else:
        matches = False
    return matches


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any] | None:
    """Resolve a local JSON pointer from the derived schema."""
    if not ref.startswith("#/"):
        return None
    current: object = schema
    for raw_token in ref[2:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            return None
        current = current[token]
    return current if isinstance(current, dict) else None


def _value_violations(
    value: object,
    constraint: dict[str, Any],
    schema: dict[str, Any],
    field: str,
) -> list[str]:
    """Validate one TOML value against the structural schema subset we use."""
    violations: list[str] = []

    ref = constraint.get("$ref")
    if isinstance(ref, str):
        resolved = _resolve_ref(schema, ref)
        if resolved is None:
            return [f"{field}: schema contains unresolved reference {ref!r}"]
        violations.extend(_value_violations(value, resolved, schema, field))

    all_of = constraint.get("allOf")
    if isinstance(all_of, list):
        for member in all_of:
            if isinstance(member, dict):
                violations.extend(_value_violations(value, member, schema, field))

    expected_type = constraint.get("type")
    expected_types = (
        [expected_type]
        if isinstance(expected_type, str)
        else expected_type
        if isinstance(expected_type, list)
        else []
    )
    named_types = [item for item in expected_types if isinstance(item, str)]
    if named_types and not any(_json_type_matches(value, item) for item in named_types):
        expected = " or ".join(named_types)
        violations.append(f"{field}: expected {expected}, got {type(value).__name__}")
        return violations

    enum = constraint.get("enum")
    if isinstance(enum, list) and value not in enum:
        violations.append(f"{field}: value {value!r} is not one of {enum!r}")

    min_length = constraint.get("minLength")
    if (
        isinstance(value, str)
        and isinstance(min_length, int)
        and len(value) < min_length
    ):
        violations.append(f"{field}: string is shorter than {min_length}")

    if isinstance(value, dict):
        violations.extend(_object_violations(value, constraint, schema, field))

    return violations


def _object_violations(
    value: dict[str, Any],
    constraint: dict[str, Any],
    schema: dict[str, Any],
    prefix: str,
) -> list[str]:
    """Validate required keys, property membership, and declared value shapes."""
    violations: list[str] = []
    required = constraint.get("required", [])
    properties = constraint.get("properties", {})

    if not isinstance(required, list) or not all(
        isinstance(item, str) for item in required
    ):
        return [f"{prefix}: schema has an invalid required list"]
    if not isinstance(properties, dict):
        return [f"{prefix}: schema has an invalid properties object"]

    violations.extend(
        f"{prefix}: missing required key {key!r}"
        for key in sorted(required)
        if key not in value
    )

    additional = constraint.get("additionalProperties", True)
    for key in sorted(value):
        field = f"{prefix}.{key}"
        property_schema = properties.get(key)
        if isinstance(property_schema, dict):
            violations.extend(
                _value_violations(value[key], property_schema, schema, field)
            )
        elif additional is False:
            violations.append(f"{prefix}: unexpected key {key!r}")
        elif isinstance(additional, dict):
            violations.extend(_value_violations(value[key], additional, schema, field))

    return violations


def _load_schema(repo_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load the derived agent schema without turning bad input into a traceback."""
    path = agent_schema_path(repo_root)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return (None, f"{path}: schema not found")
    except json.JSONDecodeError as exc:
        return (None, f"{path}: invalid JSON: {exc}")
    except OSError as exc:
        return (None, f"{path}: cannot be read: {exc}")
    if not isinstance(loaded, dict):
        return (None, f"{path}: schema root must be an object")
    return (loaded, None)


def find_violations(repo_root: Path) -> list[str]:
    """Return schema and roster violations for every tracked SDLC agent."""
    schema, schema_error = _load_schema(repo_root)
    if schema is None:
        return [schema_error or "codex agent schema could not be loaded"]

    violations: list[str] = []
    present_names: set[str] = set()
    directory = repo_root / _AGENT_DIRECTORY
    for path in sorted(directory.glob(_AGENT_GLOB)):
        rel = path.relative_to(repo_root).as_posix()
        try:
            parsed = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            violations.append(f"{rel}: invalid TOML: {exc}")
            continue
        except OSError as exc:
            violations.append(f"{rel}: cannot be read: {exc}")
            continue

        name = parsed.get("name")
        if isinstance(name, str):
            present_names.add(name)
        violations.extend(_object_violations(parsed, schema, schema, rel))

    violations.extend(
        f"missing SDLC agent name {name!r}"
        for name in sorted(EXPECTED_SDLC_ROSTER - present_names)
    )
    violations.extend(
        f"unexpected SDLC agent name {name!r}"
        for name in sorted(present_names - EXPECTED_SDLC_ROSTER)
    )

    return violations


def validate_main(argv: list[str] | None = None) -> int:
    """CLI entry point: return 0 for a valid roster and 1 for violations."""
    parser = argparse.ArgumentParser(prog="codex-agent-validate")
    parser.add_argument("repo_root", nargs="?", type=Path)
    args = parser.parse_args(argv)
    repo_root = args.repo_root or _project_root()

    violations = find_violations(repo_root)
    if violations:
        for violation in violations:
            sys.stderr.write(f"codex-agent-validate: {violation}\n")
        return 1

    sys.stdout.write(
        f"codex-agent-validate: {len(EXPECTED_SDLC_ROSTER)} SDLC agents valid\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(validate_main())
