"""pc-doctor's kernel-settings line: five kernel settings on the PC, read with sysctl, against their boot values."""

# Spec #729, ticket #730. A --privileged container's `sysctl --system` once applied its image's kernel defaults to
# the PC; a reboot put them back. data/pc-kernel.json keeps the values the PC boots with, read on 2026-11-16 after
# that reboot and matched to their sources: /usr/lib/sysctl.d (kernel.sysrq, fs.protected_regular, the
# systemd-coredump kernel.core_pattern), the kernel command line's loglevel=0 (kernel.printk's first field) and the
# kernel default (kernel.kptr_restrict). Only these five keys, so counters and per-interface keys never alarm.
# Values compare exactly, as sysctl prints them (kernel.printk tab-separated), so even a spacing change shows.

import subprocess
from collections.abc import Callable
from importlib.resources import files

from .models import PcDoctorLine, PcKernelBaseline, Result

CHECK = "kernel-settings"
NOT_FOUND = 127  # the PC's shell found no sysctl


def baseline() -> dict[str, str]:
    """Each key's boot value, in the file's order."""
    text = files(__package__).joinpath("data/pc-kernel.json").read_text()
    return PcKernelBaseline.model_validate_json(text).model_dump(by_alias=True)


def parsed(stdout: str) -> tuple[dict[str, str], int]:
    """sysctl's `key = value` lines, and how many other lines it printed (skipped, so a real change still shows)."""
    live, other = {}, 0
    for row in stdout.splitlines():
        key, sep, value = row.partition(" = ")
        if sep:
            live[key] = value
        else:
            other += 1
    return live, other


def line(run: Callable[[tuple[str, ...]], subprocess.CompletedProcess[str] | str]) -> PcDoctorLine:
    """Fail naming each key whose live value differs; unknown when sysctl could not be read for every key."""
    expected = baseline()
    done = run(("sysctl", *expected))
    if isinstance(done, str):
        return PcDoctorLine(check=CHECK, result=Result.unknown, detail=done, culprits=[])
    if done.returncode == NOT_FOUND:
        detail = f"sysctl is not on the PC (exit {NOT_FOUND})"
        return PcDoctorLine(check=CHECK, result=Result.unknown, detail=detail, culprits=[])
    live, other = parsed(done.stdout)
    changed = [key for key in expected if key in live and live[key] != expected[key]]
    unread = [key for key in expected if key not in live]
    if changed:
        # A confirmed change fails even when another key could not be read or a line did not parse.
        said = "; ".join(f"{key} is {live[key]!r}, expected {expected[key]!r}" for key in changed)
        return PcDoctorLine(check=CHECK, result=Result.fail, detail=said, culprits=[f"sysctl:{key}" for key in changed])
    if other:
        detail = f"{other} lines of sysctl's output did not parse (exit {done.returncode})"
        return PcDoctorLine(check=CHECK, result=Result.unknown, detail=detail, culprits=[f"sysctl:{k}" for k in unread])
    if unread or done.returncode:
        detail = f"sysctl could not read every key (exit {done.returncode})"
        return PcDoctorLine(check=CHECK, result=Result.unknown, detail=detail, culprits=[f"sysctl:{k}" for k in unread])
    detail = f"the {len(expected)} kernel settings match their boot values"
    return PcDoctorLine(check=CHECK, result=Result.pass_, detail=detail, culprits=[])
