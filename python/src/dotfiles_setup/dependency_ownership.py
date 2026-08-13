# Copyright (c) 2026 Raymond Manaloto
"""Verify that Python packages have one declarative owner."""

from __future__ import annotations

import logging
import re
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_PACKAGE_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_PYTHON_TOOL_PREFIXES = ("pipx:", "pip:", "uvx:")
logger = logging.getLogger(__name__)


def _canonical_name(value: str) -> str:
    match = _PACKAGE_NAME.match(value)
    if match is None:
        return ""
    return re.sub(r"[-_.]+", "-", match.group(1)).lower()


def _python_project(repo_root: Path) -> tuple[Path, str]:
    nested = repo_root / "python" / "pyproject.toml"
    if nested.is_file():
        return nested, "python"
    return repo_root / "pyproject.toml", "."


def _declared_python_packages(pyproject: Path) -> tuple[str, ...]:
    values = tomllib.loads(pyproject.read_text())
    project = values.get("project", {})
    requirements = list(project.get("dependencies", ()))
    for group in values.get("dependency-groups", {}).values():
        if isinstance(group, list):
            requirements.extend(group)
    names = {
        name
        for requirement in requirements
        if isinstance(requirement, str)
        if (name := _canonical_name(requirement))
    }
    return tuple(sorted(names))


def _mise_python_packages(tools: object) -> tuple[str, ...]:
    if not isinstance(tools, dict):
        return ()
    names: set[str] = set()
    for key in tools:
        if not isinstance(key, str) or not key.startswith(_PYTHON_TOOL_PREFIXES):
            continue
        package = key.split(":", maxsplit=1)[1].split("[", maxsplit=1)[0]
        if name := _canonical_name(package):
            names.add(name)
    return tuple(sorted(names))


@dataclass(frozen=True)
class DependencyOwnershipResult:
    """Result of the single-owner and locked-materialization audit."""

    python_packages: tuple[str, ...]
    mise_python_packages: tuple[str, ...]
    duplicate_packages: tuple[str, ...]
    uv_provider_locked: bool

    @property
    def ok(self) -> bool:
        """Return whether every enforced ownership invariant holds."""
        return not self.duplicate_packages and self.uv_provider_locked


def audit_dependency_ownership(repo_root: Path) -> DependencyOwnershipResult:
    """Audit Python declarations and mise's locked uv materialization boundary."""
    pyproject, expected_dir = _python_project(repo_root)
    python_packages = _declared_python_packages(pyproject)
    mise_values = tomllib.loads((repo_root / "mise.toml").read_text())
    mise_packages = _mise_python_packages(mise_values.get("tools"))
    duplicates = tuple(sorted(set(python_packages) & set(mise_packages)))
    uv_provider = mise_values.get("deps", {}).get("uv", {})
    uv_locked = (
        isinstance(uv_provider, dict)
        and uv_provider.get("auto") is True
        and uv_provider.get("dir", ".") == expected_dir
        and uv_provider.get("run") == "uv sync --locked"
    )
    return DependencyOwnershipResult(
        python_packages,
        mise_packages,
        duplicates,
        uv_locked,
    )


def dependency_ownership_main(repo_root: Path) -> int:
    """Render audit failures at the CLI boundary."""
    result = audit_dependency_ownership(repo_root)
    if result.duplicate_packages:
        logger.error(
            "Python package(s) also declared as mise tools: %s",
            ", ".join(result.duplicate_packages),
        )
    if not result.uv_provider_locked:
        logger.error("mise [deps.uv] must auto-run uv sync --locked")
    return 0 if result.ok else 1
