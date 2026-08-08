# Copyright (c) 2026 Raymond Manaloto
"""Auto-bump `CLANG_P2996_REF` to the latest `bloomberg/clang-p2996` HEAD.

clang-p2996 publishes **no releases or tags**; its default branch is ~a
year stale and the active P2996 work lives on the **`p2996`** branch. So
"latest stable" is defined as that branch's HEAD commit.

The SHA stays **pinned** in `docker-bake.hcl` (reproducible, hermetic).
This module only rewrites the pin to a newer HEAD when one exists — it
does NOT resolve "latest" at build time. The pinned SHA feeds the
content-addressed cache key in `p2996_hash.py`, so:

- SHA unchanged -> same hash -> `:p2996-<hash>` cache **hit** -> no rebuild.
- SHA changed   -> new hash  -> cache **miss** -> exactly one rebuild.

The scheduled `.github/workflows/refresh.yml` (`p2996-refresh` job) runs
this, then opens a PR via `peter-evans/create-pull-request` when the file
actually changed.

See `.devcontainer/P2996-CACHE.md` and issue #100 for the full design.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from dotfiles_setup.p2996_hash import _extract_bake_variable

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = logging.getLogger(__name__)

CLANG_P2996_REPO = "https://github.com/bloomberg/clang-p2996"
TRACKED_BRANCH = "p2996"
BAKE_VARIABLE = "CLANG_P2996_REF"
GIT_SHA1_LEN = 40

# Rewrites only the quoted SHA inside the variable block, preserving the
# surrounding HCL formatting. Mirrors `_extract_bake_variable`'s shape.
_PINNED_REF_PATTERN = re.compile(
    r'(variable\s+"' + re.escape(BAKE_VARIABLE) + r'"\s*\{[^}]*?'
    r'default\s*=\s*")([0-9a-fA-F]+)(")',
    re.DOTALL,
)


@dataclass(frozen=True)
class RefreshResult:
    """Outcome of a refresh attempt."""

    changed: bool
    old_ref: str
    new_ref: str

    def as_json(self) -> str:
        """Render the result as a one-line JSON object."""
        return json.dumps(asdict(self))


def _validate_sha(value: str, source: str) -> str:
    """Return `value` if it is a full 40-char lowercase-hex git SHA-1.

    Raises:
        ValueError: when `value` is not a well-formed full SHA-1.
    """
    if len(value) != GIT_SHA1_LEN or not all(c in "0123456789abcdef" for c in value):
        msg = (
            f"{source} must be a {GIT_SHA1_LEN}-char lowercase-hex git SHA-1; "
            f"got {value!r}"
        )
        raise ValueError(msg)
    return value


def _default_runner(repo_url: str, branch: str) -> str:
    """Run `git ls-remote <repo_url> refs/heads/<branch>` and return stdout.

    Raises:
        subprocess.CalledProcessError: when git exits non-zero (stderr logged).
    """
    cmd = ["git", "ls-remote", repo_url, f"refs/heads/{branch}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        logger.exception(
            "git ls-remote failed (rc=%d). stderr:\n%s", exc.returncode, exc.stderr
        )
        raise
    return result.stdout


def fetch_latest_ref(
    runner: Callable[[str, str], str] | None = None,
    *,
    repo_url: str = CLANG_P2996_REPO,
    branch: str = TRACKED_BRANCH,
) -> str:
    """Resolve the HEAD SHA of `branch` on `repo_url` via git ls-remote.

    `runner` is a test seam: a callable `(repo_url, branch) -> stdout`.

    Raises:
        ValueError: when ls-remote returns no matching ref or a malformed SHA.
    """
    run = runner or _default_runner
    stdout = run(repo_url, branch)
    first_line = stdout.strip().splitlines()[0] if stdout.strip() else ""
    sha = first_line.split()[0].lower() if first_line else ""
    if not sha:
        msg = (
            f"git ls-remote returned no ref for refs/heads/{branch} on "
            f"{repo_url}; got {stdout!r}"
        )
        raise ValueError(msg)
    return _validate_sha(sha, f"ls-remote SHA for refs/heads/{branch}")


def read_pinned_ref(repo_root: Path) -> str:
    """Read the currently-pinned `CLANG_P2996_REF` from docker-bake.hcl."""
    bake_text = (repo_root / "docker-bake.hcl").read_text()
    return _extract_bake_variable(bake_text, BAKE_VARIABLE)


def replace_pinned_ref(bake_text: str, new_ref: str) -> str:
    """Return `bake_text` with the `CLANG_P2996_REF` default set to `new_ref`.

    Raises:
        ValueError: when the variable block is missing (so a silent no-op
            rewrite can never mask a renamed/removed pin).
    """
    new_text, count = _PINNED_REF_PATTERN.subn(rf"\g<1>{new_ref}\g<3>", bake_text)
    if count != 1:
        msg = (
            f"expected exactly one {BAKE_VARIABLE} default in docker-bake.hcl, "
            f"found {count}"
        )
        raise ValueError(msg)
    return new_text


def refresh(
    repo_root: Path,
    *,
    runner: Callable[[str, str], str] | None = None,
) -> RefreshResult:
    """Bump the pinned ref to the latest `p2996` HEAD if it has advanced.

    Writes `docker-bake.hcl` only when the SHA changed, so an unchanged
    HEAD leaves the file byte-identical (no spurious PR).
    """
    bake_path = repo_root / "docker-bake.hcl"
    bake_text = bake_path.read_text()
    old_ref = _extract_bake_variable(bake_text, BAKE_VARIABLE)
    new_ref = fetch_latest_ref(runner)
    if new_ref == old_ref:
        logger.info(
            "%s already at latest %s HEAD %s", BAKE_VARIABLE, TRACKED_BRANCH, new_ref
        )
        return RefreshResult(changed=False, old_ref=old_ref, new_ref=new_ref)
    bake_path.write_text(replace_pinned_ref(bake_text, new_ref))
    logger.info("Bumped %s: %s -> %s", BAKE_VARIABLE, old_ref, new_ref)
    return RefreshResult(changed=True, old_ref=old_ref, new_ref=new_ref)
