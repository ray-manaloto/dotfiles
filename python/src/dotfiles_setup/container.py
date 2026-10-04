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

import contextlib
import dataclasses
import json
import logging
import math
import os
import subprocess
import sys
import time
import uuid
from typing import TYPE_CHECKING

from dotfiles_setup import host_lock
from dotfiles_setup.devcontainer_names import resolve_names

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Smoke can take minutes (tier 2 runs pytest, tier 3 links + runs sanitizers
# and reaches github over ssh); bound it so a hang surfaces instead of blocking.
_SMOKE_TIMEOUT_S = 1800.0
_SMOKE_TIMEOUT_ELAPSED_RATIO = 0.9
_SMOKE_PROCESS_ERROR_LIMIT = 500


@dataclasses.dataclass(frozen=True)
class Check:
    """One named freshness assertion and its outcome."""

    name: str
    ok: bool
    detail: str


def _run(
    cmd: list[str], *, timeout: float | None = None, pass_fds: tuple[int, ...] = ()
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
        timeout=timeout,
        pass_fds=pass_fds,
    )


def _host_head(workspace: Path) -> str:
    return _run(["git", "-C", str(workspace), "rev-parse", "HEAD"]).stdout.strip()


def _host_branch(workspace: Path) -> str:
    return _run(
        ["git", "-C", str(workspace), "rev-parse", "--abbrev-ref", "HEAD"]
    ).stdout.strip()


def _running_container_ids(workspace: Path) -> tuple[str, ...]:
    names = resolve_names(workspace=workspace)
    out = _run(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            f"label={names.workspace_label}",
            "--filter",
            f"label={names.arch_label}",
        ]
    ).stdout.strip()
    return tuple(line for line in out.splitlines() if line)


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


# Executed with the image's system Python, not the mise shim. The same scanner
# protects the probing process and its ancestor chain on both operations.
_SMOKE_PROCESSES_PROGRAM = """
import json
import os
import signal
import sys
import time
from pathlib import Path

proc = Path("/proc")
mode, marker = sys.argv[1:]
protected = {os.getpid()}
parent = os.getppid()
while parent and parent not in protected:
    protected.add(parent)
    try:
        stat = (proc / str(parent) / "stat").read_text()
        parent = int(stat.rsplit(") ", 1)[1].split()[1])
    except (OSError, ValueError, IndexError):
        break

def matching():
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) in protected:
            continue
        try:
            state = (entry / "stat").read_text().rsplit(") ", 1)[1].split()[0]
            if state == "Z":
                continue
            if mode == "probe":
                argv = (entry / "cmdline").read_bytes().split(b"\\0")
                selected = bool(argv) and (
                    os.path.basename(argv[0]) == b"devcontainer-smoke.sh"
                    or (os.path.basename(argv[0]) in {b"bash", b"sh"}
                        and len(argv) > 1
                        and os.path.basename(argv[1]) == b"devcontainer-smoke.sh")
                )
            else:
                environment = (entry / "environ").read_bytes().split(b"\\0")
                selected = ("DOTFILES_SMOKE_RUN_ID=" + marker).encode() in environment
            if selected:
                found.append(int(entry.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            if mode == "probe":
                raise SystemExit("process probe unreadable: pid " + entry.name)
            continue
    return sorted(found)

pids = matching()
reaped = set()
if mode == "reap":
    for attempt in range(3):
        for pid in pids:
            try:
                fd = os.pidfd_open(pid)
                try:
                    # Bind signals to the kernel process identity, then recheck
                    # its marker. A recycled numeric pid cannot redirect SIGKILL.
                    current = (proc / str(pid) / "environ").read_bytes().split(b"\\0")
                    if ("DOTFILES_SMOKE_RUN_ID=" + marker).encode() in current:
                        signal.pidfd_send_signal(fd, signal.SIGKILL)
                        reaped.add(pid)
                finally:
                    os.close(fd)
            except (FileNotFoundError, ProcessLookupError):
                pass
        if not pids:
            break
        time.sleep(0.1)
        pids = matching()
print(json.dumps({"pids": pids, "reaped": len(reaped)}))
"""


def _smoke_process_error(message: str) -> str:
    """Keep bounded diagnostics without including the inline scanner program."""
    for program in (
        _SMOKE_PROCESSES_PROGRAM,
        repr(_SMOKE_PROCESSES_PROGRAM),
        json.dumps(_SMOKE_PROCESSES_PROGRAM),
    ):
        message = message.replace(program, "[inline scanner]")
    return message.strip()[:_SMOKE_PROCESS_ERROR_LIMIT]


def _smoke_processes(
    container_id: str, *, marker: str = "", lock_fd: int | None = None
) -> tuple[list[int], int, str]:
    """Probe script names or reap only this marker; fail closed on probe errors."""
    try:
        result = _run(
            [
                "docker",
                "exec",
                container_id,
                "/usr/bin/python3",
                "-c",
                _SMOKE_PROCESSES_PROGRAM,
                "reap" if marker else "probe",
                marker,
            ],
            timeout=10,
            pass_fds=() if lock_fd is None else (lock_fd,),
        )
        if result.returncode:
            return (
                [],
                0,
                _smoke_process_error(result.stderr) or f"exit {result.returncode}",
            )
        payload = json.loads(result.stdout)
        pids = payload["pids"]
        reaped = payload["reaped"]
        if not isinstance(pids, list) or not all(isinstance(pid, int) for pid in pids):
            return [], 0, "invalid process list"
        if not isinstance(reaped, int):
            return [], 0, "invalid reap count"
    except subprocess.TimeoutExpired as exc:
        return (
            [],
            0,
            _smoke_process_error(
                f"process {'reap' if marker else 'probe'} "
                f"timed out after {exc.timeout:g} seconds"
            ),
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return [], 0, _smoke_process_error(str(exc))
    return pids, reaped, ""


def _smoke_output(
    stdout: str | bytes | None, stderr: str | bytes | None, *, timed_out: bool = True
) -> str:
    """Prefer FAIL; use stdout for timeouts and combined streams for completed runs."""
    streams = [
        part.decode(errors="replace") if isinstance(part, bytes) else part or ""
        for part in (stdout, stderr)
    ]
    for stream in streams:
        for line in stream.splitlines():
            if "FAIL" in line:
                return line[-2000:]
    lines = (
        streams[0].strip().splitlines() or streams[1].strip().splitlines()
        if timed_out
        else (streams[0] + streams[1]).strip().splitlines()
    )
    return " | ".join(lines[-3:])[-2000:] or (
        "no partial output" if timed_out else "smoke failed (no output)"
    )


def _smoke_timeout_detail(
    container_id: str, marker: str, *, lock_fd: int | None
) -> str:
    pids, reaped, error = _smoke_processes(container_id, marker=marker, lock_fd=lock_fd)
    if error:
        return f"ORPHANS REMAIN: process reap unverified ({error})"
    if pids:
        return "ORPHANS REMAIN: pids " + ", ".join(map(str, pids))
    return f"reaped {reaped} in-container processes"


def _run_smoke(
    container_id: str, workspace_dest: str, *, lock_fd: int | None = None
) -> tuple[bool, str]:
    timeout = _SMOKE_TIMEOUT_S
    try:
        configured = float(os.environ.get("DOTFILES_SMOKE_TIMEOUT_S", timeout))
    except ValueError:
        configured = timeout
    if math.isfinite(configured) and configured > 0:
        timeout = configured
    pids, _, error = _smoke_processes(container_id, lock_fd=lock_fd)
    if error:
        return False, f"smoke process probe failed: {error}"
    if pids:
        return False, (
            f"smoke already running in {container_id[:12]} "
            f"(pids {', '.join(map(str, pids))})"
        )
    marker = str(uuid.uuid4())
    kill_after = max(1, min(30, 0.1 * timeout))
    grace = max(2, min(60, 0.1 * timeout))
    started = time.monotonic()
    try:
        res = _run(
            [
                "docker",
                "exec",
                "-e",
                f"DOTFILES_SMOKE_RUN_ID={marker}",
                "--workdir",
                workspace_dest,
                container_id,
                "timeout",
                f"--kill-after={kill_after:g}s",
                f"{timeout:g}s",
                "scripts/devcontainer-smoke.sh",
            ],
            timeout=timeout + kill_after + grace,
            pass_fds=() if lock_fd is None else (lock_fd,),
        )
    except subprocess.TimeoutExpired as exc:
        cleanup = _smoke_timeout_detail(container_id, marker, lock_fd=lock_fd)
        return False, (
            f"smoke timed out after {timeout:g} seconds: "
            f"{_smoke_output(exc.stdout, exc.stderr)}; {cleanup}"
        )
    if res.returncode == 0:
        return True, "tiers 1-3 OK"
    if res.returncode in {124, 137}:
        elapsed = time.monotonic() - started
        cleanup = _smoke_timeout_detail(container_id, marker, lock_fd=lock_fd)
        timed_out = elapsed >= _SMOKE_TIMEOUT_ELAPSED_RATIO * timeout
        status = (
            f"smoke timed out after {timeout:g} seconds (in-container timeout)"
            if timed_out
            else f"smoke exited with rc {res.returncode}"
        )
        output = _smoke_output(res.stdout, res.stderr, timed_out=timed_out)
        return False, f"{status}: {output}; {cleanup}"
    return False, (
        f"{_smoke_output(res.stdout, res.stderr, timed_out=False)}"
        " — stale base? `mise run dev-rebuild`"
    )


def verify_latest(workspace: Path, *, run_smoke: bool = True) -> list[Check]:
    """Assert the running devcontainer is on the latest branch code + base.

    Returns the ordered list of checks. Short-circuits the remaining checks
    when no container is running (there is nothing to validate).
    """
    slot = (
        host_lock.held(host_lock.HEAVY_GATE, f"container smoke {workspace}")
        if run_smoke
        else contextlib.nullcontext()
    )
    try:
        with slot as lock_fd:
            return _verify_latest_under_slot(
                workspace, run_smoke=run_smoke, lock_fd=lock_fd
            )
    except host_lock.HostLockTimeoutError as exc:
        return [
            Check(
                "smoke-tiers-1-3",
                ok=False,
                detail=f"smoke host heavy-slot wait timed out: {exc}",
            )
        ]


def _verify_latest_under_slot(
    workspace: Path, *, run_smoke: bool, lock_fd: int | None
) -> list[Check]:
    """Resolve every identity from current state after acquiring the host slot."""
    branch = _host_branch(workspace)
    head = _host_head(workspace)
    logger.info("verify-latest: branch=%s HEAD=%s", branch, head[:8])

    container_ids = _running_container_ids(workspace)
    if not container_ids:
        return [
            Check(
                "container-running",
                ok=False,
                detail=f"no running devcontainer for {workspace} (run `mise run up`)",
            )
        ]
    if len(container_ids) != 1:
        return [
            Check(
                "container-identity-unique",
                ok=False,
                detail=(
                    f"{len(container_ids)} running containers share this "
                    "workspace+arch "
                    "identity; run `mise run down` and start one explicitly"
                ),
            )
        ]
    container_id = container_ids[0]

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

    if run_smoke and dest is not None:
        smoke_ok, smoke_detail = _run_smoke(container_id, dest, lock_fd=lock_fd)
        checks.append(
            Check(
                "smoke-tiers-1-3",
                ok=smoke_ok,
                detail=smoke_detail,
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
