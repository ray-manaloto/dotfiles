"""pc-doctor's fence-drops line: the job fence's three mangle drops on the PC, each present exactly once."""

# Ticket #741. gha-fence.service (cpp-standard's mise.pc.toml) sets them at boot: the IPv4 and IPv6 mangle INPUT
# drops that keep job containers off the host's tailscaled (UDP 41641, which tailscaled's ts-input accepts ahead of
# ufw), and the IPv4 mangle FORWARD drop to tailscale0. A missing drop is a hole in the fence; a second copy means
# something other than the unit added it (the launcher's check-then-insert, racing in several slots), so both fail and
# are named.
#
# iptables -S needs root, so each listing runs as `sudo -n`: it never waits for a password, and a sudo that wants one
# exits 1, which is unknown. iptables v1.8.13 prints each rule in its own canonical order (the IPv6 rule's
# `! -p ipv6-icmp` before `-m conntrack`), which is how the rules files and the slot template's checks spell them.

import subprocess
from collections.abc import Callable

from .models import PcDoctorLine, Result

CHECK = "fence-drops"
# Each program's one listing, and the drops it must hold, as -S prints them.
DROPS = {
    "iptables": (
        "-A INPUT -i br-gha -m conntrack --ctstate NEW -j DROP",
        "-A FORWARD -i br-gha -o tailscale0 -j DROP",
    ),
    "ip6tables": ("-A INPUT -i br-gha ! -p ipv6-icmp -m conntrack --ctstate NEW -j DROP",),
}
# Every -S listing of a table with an INPUT chain prints its policy first; output without it is not that listing.
LISTED = "-P INPUT "

# pcdoctor's ssh runner (on_pc with its time limit): argv run on the PC, or why it could not run.
type Run = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str] | str]


def copies(listed: str, rule: str) -> int:
    """How many lines of an -S listing are exactly this rule."""
    return listed.splitlines().count(rule.strip())


def unknown(detail: str) -> PcDoctorLine:
    return PcDoctorLine(check=CHECK, result=Result.unknown, detail=detail, culprits=[])


def line(run: Run) -> PcDoctorLine:
    """Fail naming each drop that is not present exactly once; unknown when a listing could not be read."""
    culprits, unread = [], []
    for program, drops in DROPS.items():
        argv = ("sudo", "-n", program, "-t", "mangle", "-S")
        listed = run(argv)
        if isinstance(listed, str):
            unread.append(listed)
        elif listed.returncode:
            unread.append(f"{' '.join(argv)} exited {listed.returncode}")
        elif not any(text.startswith(LISTED) for text in listed.stdout.splitlines()):
            unread.append(f"{' '.join(argv)} printed no mangle INPUT chain")
        else:
            culprits += [
                f"{program} -t mangle {rule}: {n} copies" for rule in drops if (n := copies(listed.stdout, rule)) != 1
            ]
    total = sum(map(len, DROPS.values()))
    # A drop seen missing or doubled is a fail even when the other family's listing could not be read.
    if unread and not culprits:
        return unknown("; ".join(unread))
    if culprits:
        detail = f"fence drops missing or duplicated: {len(culprits)} of {total}"
        if unread:
            detail += f" (not read: {'; '.join(unread)})"
        return PcDoctorLine(check=CHECK, result=Result.fail, detail=detail, culprits=culprits)
    detail = f"each of the {total} fence drops is present once"
    return PcDoctorLine(check=CHECK, result=Result.pass_, detail=detail, culprits=[])
