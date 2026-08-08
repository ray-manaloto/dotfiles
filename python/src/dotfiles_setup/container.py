# Copyright (c) 2026 Raymond Manaloto
"""Devcontainer freshness gate: is the running container on the latest code?

The verify-before-advancing rule (`.claude/rules/verify-before-advancing.md`)
requires that validation runs against the *latest code of the working branch*
(the PR branch during a PR, ``main`` on main) in a *current* container. A
container that is stale — mounting a different tree, or built on an outdated
base ``:dev`` — is not a valid validation environment, and a green check
against it is a false positive.

This gate asserts three facts, each a HARD check reported as a :class:`Check`:

1. ``container-running`` — a devcontainer is up for this workspace.
2. ``workspace-bind-mount`` — it bind-mounts *this* workspace, so the source
   the container sees is the host working tree (the branch's latest code),
   live.
3. ``smoke-tiers-1-3`` — ``scripts/devcontainer-smoke.sh`` passes in the
   container. This is the authoritative base-currency gate: the smoke's tier-1
   image-identity check (PR #140, "Gap A") compares the *in-image*
   ``config.toml`` hash against the repo ``mise-system.toml`` and hard-fails a
   stale/outdated base, so "the base is current" is enforced against the
   actually-running image, not a tag-digest proxy.

Base-currency is therefore a hard block by design: a container built on a base
that predates the current ``mise-system.toml`` fails smoke and this gate.

Logic lives here (Python), not in the mise task, per the repo's zero-bash-logic
policy; the ``verify-container-latest`` task is a thin caller.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# devcontainer-cli labels every container it creates with the host workspace
# folder; this is the join key between "a running container" and "this repo".
_LOCAL_FOLDER_LABEL = "devcontainer.local_folder"

# Smoke can take minutes (tier 2 runs pytest, tier 3 links + runs sanitizers
# and reaches github over ssh); bound it so a hang surfaces instead of blocking.
_SMOKE_TIMEOUT_S = 1800.0


@dataclasses.dataclass(frozen=True)
class Check:
    """One named freshness assertion and its outcome."""

    name: str
    ok: bool
    detail: str


def _run(
    cmd: list[str], *, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, capture_output=True, text=True, check=False, timeout=timeout
    )


def _host_head(workspace: Path) -> str:
    return _run(["git", "-C", str(workspace), "rev-parse", "HEAD"]).stdout.strip()


def _host_branch(workspace: Path) -> str:
    return _run(
        ["git", "-C", str(workspace), "rev-parse", "--abbrev-ref", "HEAD"]
    ).stdout.strip()


def _running_container_id(workspace: Path) -> str | None:
    out = _run(
        ["docker", "ps", "-q", "--filter", f"label={_LOCAL_FOLDER_LABEL}={workspace}"]
    ).stdout.strip()
    return out.splitlines()[0] if out else None


def _bind_mount_dest(container_id: str, workspace: Path) -> str | None:
    """Destination where ``container_id`` bind-mounts ``workspace`` (or None)."""
    raw = _run(
        ["docker", "inspect", container_id, "--format", "{{json .Mounts}}"]
    ).stdout.strip()
    if not raw:
        return None
    for mount in json.loads(raw):
        if mount.get("Type") == "bind" and mount.get("Source") == str(workspace):
            return mount.get("Destination")
    return None


def _run_smoke(workspace: Path) -> tuple[bool, str]:
    res = _run(
        [
            "devcontainer",
            "exec",
            "--workspace-folder",
            str(workspace),
            "scripts/devcontainer-smoke.sh",
        ],
        timeout=_SMOKE_TIMEOUT_S,
    )
    if res.returncode == 0:
        return True, "tiers 1-3 OK"
    combined = (res.stdout + res.stderr).strip().splitlines()
    # Surface the first FAIL line if present, else the tail.
    fails = [line for line in combined if "FAIL" in line]
    tail = fails[:1] or combined[-3:]
    return False, " | ".join(tail) if tail else "smoke failed (no output)"


def verify_latest(workspace: Path, *, run_smoke: bool = True) -> list[Check]:
    """Assert the running devcontainer is on the latest branch code + base.

    Returns the ordered list of checks. Short-circuits the remaining checks
    when no container is running (there is nothing to validate).
    """
    branch = _host_branch(workspace)
    head = _host_head(workspace)
    logger.info("verify-latest: branch=%s HEAD=%s", branch, head[:8])

    container_id = _running_container_id(workspace)
    if container_id is None:
        return [
            Check(
                "container-running",
                ok=False,
                detail=f"no running devcontainer for {workspace} (run `mise run up`)",
            )
        ]

    checks = [
        Check(
            "container-running",
            ok=True,
            detail=f"{container_id[:12]} up for {workspace}",
        )
    ]

    dest = _bind_mount_dest(container_id, workspace)
    checks.append(
        Check(
            "workspace-bind-mount",
            ok=dest is not None,
            detail=(
                f"host tree live at {dest} ({branch}@{head[:8]})"
                if dest is not None
                else f"container does not bind-mount {workspace} (source not live)"
            ),
        )
    )

    if run_smoke:
        smoke_ok, smoke_detail = _run_smoke(workspace)
        checks.append(
            Check(
                "smoke-tiers-1-3",
                ok=smoke_ok,
                detail=(
                    smoke_detail
                    if smoke_ok
                    else f"{smoke_detail} — stale base? `mise run dev-rebuild`"
                ),
            )
        )

    return checks


def verify_latest_main(workspace: Path, *, run_smoke: bool = True) -> int:
    """CLI entry: print each check and return 1 if any failed, else 0."""
    checks = verify_latest(workspace, run_smoke=run_smoke)
    failed = [c for c in checks if not c.ok]
    for check in checks:
        marker = "PASS" if check.ok else "FAIL"
        sys.stdout.write(f"{marker}  {check.name}: {check.detail}\n")
    if failed:
        sys.stdout.write(
            f"\nverify-container-latest: {len(failed)} check(s) failed — the "
            "running devcontainer is NOT a valid validation environment for "
            "the latest branch code. Resolve before advancing (see "
            ".claude/rules/verify-before-advancing.md).\n"
        )
        return 1
    sys.stdout.write(
        "\nverify-container-latest: OK — container on latest branch code "
        "+ current base.\n"
    )
    return 0
