"""pc-doctor's privileged-containers line: a running container on the PC's Docker daemon with --privileged fails."""

# Spec #729, ticket #731. On 2026-11-16 a --privileged container ran apt, and a package's post-install script applied
# the image's kernel settings to the PC itself. This is a point-in-time check: it cannot see a container that came and
# went between runs (the kernel-settings line catches what such a container left behind).
#
# --host names the PC's own daemon: it overrides DOCKER_HOST and DOCKER_CONTEXT (Docker 29.9.2, read on the PC), so an
# inherited context can never return a convincing empty list. Two calls over ssh: ps lists the running ids, then one
# inspect reads them all. A container removed in between is named by inspect's "No such container" and skipped; any
# other gap between the two is an incomplete listing, unknown. The inspect output holds each container's environment,
# so none of it is ever echoed: a parse error reports only its type, as pcdoctor's judge does.

import re
import subprocess
from collections.abc import Callable

from pydantic import TypeAdapter

from .models import DockerContainer, PcDoctorLine, Result

CHECK = "privileged-containers"
DOCKER = ("docker", "--host", "unix:///var/run/docker.sock")
# ps --no-trunc prints full ids; nothing else is passed back to the PC's shell, so only these are.
ID = re.compile(r"[0-9a-f]{64}")
GONE = re.compile(r"^Error response from daemon: No such container: ([0-9a-f]{64})$", re.MULTILINE)
# docker/cli v29.9.2 (the PC's client, a82e5289) cli/command/inspect/inspector.go:99-103: inspect exits 1 when any
# lookup failed, after printing the rest; 64 is a bad template, anything else is not docker's answer at all.
LOOKUP_FAILED = 1
CONTAINERS = TypeAdapter(list[DockerContainer])


# pcdoctor's ssh runner (on_pc with its time limit): argv run on the PC, or why it could not run. The stderr it
# returns is also echoed to the doctor's.
type Run = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str] | str]


def unknown(detail: str) -> PcDoctorLine:
    return PcDoctorLine(check=CHECK, result=Result.unknown, detail=detail, culprits=[])


def running(run: Run) -> list[str] | str:
    """The full ids docker ps lists on the PC, or why it could not list them."""
    listed = run((*DOCKER, "ps", "--quiet", "--no-trunc"))
    if isinstance(listed, str):
        return listed
    if listed.returncode:
        return f"docker ps exited {listed.returncode}"
    ids = listed.stdout.split()
    if not all(ID.fullmatch(i) for i in ids):
        return "docker ps printed something other than container ids"
    return ids


def judge(ids: list[str], inspected: subprocess.CompletedProcess[str]) -> PcDoctorLine:
    """Fail on any privileged container seen; otherwise unknown unless each listed id was inspected or is gone."""
    try:
        seen = CONTAINERS.validate_json(inspected.stdout)
    except ValueError as failed:
        return unknown(f"docker container inspect's output did not parse: {type(failed).__name__}")
    privileged = [
        f"container:{c.Name.removeprefix('/')} image:{c.Config.Image}" for c in seen if c.HostConfig.Privileged
    ]
    gone = set(GONE.findall(inspected.stderr))
    # A privileged container is a fail even in a listing that did not complete.
    if privileged:
        detail = f"privileged containers running: {len(privileged)}"
        return PcDoctorLine(check=CHECK, result=Result.fail, detail=detail, culprits=privileged)
    # Exit 1 is an answer only when it named a vanished container; any other exit, or any other gap, is an incomplete
    # listing.
    answered = inspected.returncode == 0 or (inspected.returncode == LOOKUP_FAILED and gone)
    if {c.Id for c in seen} | gone != set(ids) or not answered:
        return unknown(
            f"docker container inspect did not account for every listed container (exit {inspected.returncode})"
        )
    detail = f"none of {len(seen)} running containers is privileged"
    if gone:
        detail += f" ({len(gone)} gone before inspect, skipped)"
    return PcDoctorLine(check=CHECK, result=Result.pass_, detail=detail, culprits=[])


def line(run: Run) -> PcDoctorLine:
    """Fail naming each privileged running container and its image; unknown when the listing could not complete."""
    ids = running(run)
    if isinstance(ids, str):
        return unknown(ids)
    if not ids:
        return PcDoctorLine(check=CHECK, result=Result.pass_, detail="no running container", culprits=[])
    inspected = run((*DOCKER, "container", "inspect", *ids))
    return unknown(inspected) if isinstance(inspected, str) else judge(ids, inspected)
