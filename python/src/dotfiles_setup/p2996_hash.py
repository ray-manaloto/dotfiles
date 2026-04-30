"""Compute the content-addressed hash for the P2996 cache image.

The hash captures every input that affects the `clang-builder` Dockerfile
stage. When inputs are unchanged, CI re-uses the cached image
`ghcr.io/<owner>/<repo>:p2996-<hash16>` instead of recompiling clang
from source.

See `HashInputs` for the field set, and `compute_hash` for the canonical
ordering that determines the output digest. The cold-compile baseline
and operator workflow live in `.devcontainer/P2996-CACHE.md`.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

HASH_LENGTH = 16
SCHEMA_VERSION = 1
RECORD_SEPARATOR = "\x1f"  # ASCII unit separator — never appears in inputs
SHA256_HEX_LEN = 64


@dataclass(frozen=True)
class HashInputs:
    """Materialized inputs that go into the P2996 cache hash."""

    clang_p2996_ref: str
    base_image: str
    platform: str
    dockerfile_digest: str
    bake_digest: str
    snapshot_digest: str

    def __post_init__(self) -> None:
        """Reject empty literals + non-64-hex digests at construction.

        Catches the two highest-impact bug classes that would otherwise
        produce a stable-but-wrong hash: empty inputs flowing through
        and mis-shaped digests (e.g., a `_file_digest` callsite that
        accidentally returned a path string instead of a hex digest).
        """
        for field_name in ("clang_p2996_ref", "base_image", "platform"):
            value = getattr(self, field_name)
            if not value:
                msg = f"HashInputs.{field_name} must be non-empty"
                raise ValueError(msg)
        for field_name in ("dockerfile_digest", "bake_digest", "snapshot_digest"):
            value = getattr(self, field_name)
            if len(value) != SHA256_HEX_LEN or not all(
                c in "0123456789abcdef" for c in value
            ):
                msg = (
                    f"HashInputs.{field_name} must be {SHA256_HEX_LEN}-char "
                    f"lowercase hex; got {len(value)} chars"
                )
                raise ValueError(msg)


def _extract_bake_variable(bake_text: str, name: str) -> str:
    """Pull the default value of a top-level `variable` block from bake HCL.

    Args:
        bake_text: docker-bake.hcl content.
        name: variable name, e.g. `CLANG_P2996_REF`.

    Returns:
        The default-string value.

    Raises:
        ValueError: when the variable is missing or has no string default.
    """
    pattern = (
        r'variable\s+"' + re.escape(name) + r'"\s*\{[^}]*?'
        r'default\s*=\s*"([^"]*)"'
    )
    match = re.search(pattern, bake_text, re.DOTALL)
    if match is None:
        msg = f"variable {name!r} not found with string default in docker-bake.hcl"
        raise ValueError(msg)
    return match.group(1)


def _file_digest(path: Path) -> str:
    """Return the hex sha256 of `path`'s bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gather_inputs(repo_root: Path) -> HashInputs:
    """Read every input that contributes to the P2996 cache hash.

    Args:
        repo_root: Repository root directory.

    Returns:
        Materialized inputs.
    """
    bake_path = repo_root / "docker-bake.hcl"
    dockerfile_path = repo_root / ".devcontainer" / "Dockerfile"
    snapshot_path = repo_root / ".devcontainer" / "mise-system-resolved.json"

    bake_text = bake_path.read_text()
    return HashInputs(
        clang_p2996_ref=_extract_bake_variable(bake_text, "CLANG_P2996_REF"),
        base_image=_extract_bake_variable(bake_text, "BASE_IMAGE"),
        platform=_extract_bake_variable(bake_text, "PLATFORM"),
        dockerfile_digest=_file_digest(dockerfile_path),
        bake_digest=_file_digest(bake_path),
        snapshot_digest=_file_digest(snapshot_path),
    )


def compute_hash(inputs: HashInputs) -> str:
    """Reduce the inputs to a 16-char content-addressed hash.

    Args:
        inputs: HashInputs from `gather_inputs`.

    Returns:
        Lowercase hex string of length `HASH_LENGTH`.
    """
    canonical = RECORD_SEPARATOR.join(
        [
            f"schema={SCHEMA_VERSION}",
            f"clang_p2996_ref={inputs.clang_p2996_ref}",
            f"base_image={inputs.base_image}",
            f"platform={inputs.platform}",
            f"dockerfile={inputs.dockerfile_digest}",
            f"bake={inputs.bake_digest}",
            f"snapshot={inputs.snapshot_digest}",
        ],
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:HASH_LENGTH]


def compute_repo_hash(repo_root: Path) -> str:
    """Top-level helper: gather inputs from `repo_root` and compute the hash."""
    return compute_hash(gather_inputs(repo_root))
