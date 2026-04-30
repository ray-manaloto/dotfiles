"""Capture mise system resolved versions to a deterministic snapshot file.

The snapshot lives at `.devcontainer/mise-system-resolved.json` and feeds
the P2996 cache hash. It captures resolved versions for every `conda:*`
tool defined in the system mise config so that conda-forge drift on
`"latest"` invalidates the cache deterministically.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

logger = logging.getLogger(__name__)

CONDA_PREFIX = "conda:"
SCHEMA_VERSION = 1


def filter_conda_resolved(mise_ls_data: dict) -> dict[str, str]:
    """Return sorted conda-tool→version map from `mise ls --json` output."""
    out: dict[str, str] = {}
    for key, entries in mise_ls_data.items():
        if not key.startswith(CONDA_PREFIX):
            continue
        if not entries:
            continue
        version = entries[0].get("version")
        if not version:
            continue
        out[key] = version
    return dict(sorted(out.items()))


def format_snapshot(resolved: dict[str, str]) -> str:
    """Render the snapshot to deterministic JSON ending in newline."""
    payload = {
        "schema_version": SCHEMA_VERSION,
        "tools": resolved,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_snapshot(text: str) -> dict[str, str]:
    """Extract the tools map from a snapshot file. Inverse of `format_snapshot`.

    Raises:
        TypeError: when the `tools` field is not a dict (corrupt snapshot).
        ValueError: when `schema_version` mismatches the current SCHEMA_VERSION
            (forces explicit migration when the schema evolves; prevents silent
            v1-reads-v2 drift).
    """
    payload = json.loads(text)
    schema_version = payload.get("schema_version")
    if schema_version is not None and schema_version != SCHEMA_VERSION:
        msg = (
            f"snapshot schema_version {schema_version!r} does not match "
            f"current SCHEMA_VERSION={SCHEMA_VERSION}; refresh the snapshot "
            f"or migrate the parser"
        )
        raise ValueError(msg)
    tools = payload.get("tools", {})
    if not isinstance(tools, dict):
        msg = f"snapshot has invalid tools field: {type(tools).__name__}"
        raise TypeError(msg)
    return tools


def capture(mise_ls_runner: Iterable[str] | None = None) -> dict[str, str]:
    """Run `mise ls --json` and return its filtered conda-tool map.

    `mise_ls_runner` is a test seam — defaults to `["mise", "ls", "--json"]`.
    Stderr is logged on subprocess failure (the default `CalledProcessError`
    message would otherwise hide it).
    """
    cmd = list(mise_ls_runner) if mise_ls_runner else ["mise", "ls", "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        logger.exception(
            "mise ls failed (rc=%d). stderr:\n%s", exc.returncode, exc.stderr
        )
        raise
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.exception(
            "mise ls returned non-JSON stdout (stderr was: %r)",
            result.stderr,
        )
        raise
    resolved = filter_conda_resolved(data)
    if not resolved:
        logger.warning(
            "filter_conda_resolved returned empty map from %d top-level "
            "keys (no conda:* tools found, or schema changed). Snapshot "
            "will be empty — verify mise ls --json shape.",
            len(data),
        )
    return resolved


def write_snapshot(output_path: Path, resolved: dict[str, str]) -> None:
    """Write the snapshot file at `output_path` with deterministic content."""
    output_path.write_text(format_snapshot(resolved))
    logger.info("Wrote snapshot to %s (%d tools)", output_path, len(resolved))
