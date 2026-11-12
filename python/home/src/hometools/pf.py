"""pf:load, pf:confirm, pf:unload and pf:status: the Tailscale-only pf anchor that mise bootstrap writes."""

# mise's [bootstrap.files] writes the rules file and the boot LaunchDaemon (global config.toml, "pf anchor");
# these commands load, confirm and remove them. Every load arms a revert that flushes the anchor after
# REVERT_SECONDS unless pf:confirm runs first, so rules that lock the owner out undo themselves. The boot daemon
# is turned on only by pf:confirm, so a restart never loads rules nobody confirmed.
# pf facts from Apple's kernel (xnu bsd/net/pf_ioctl.c): pfctl -E takes an enable reference that stays after
# pfctl exits and does not fail when pf is already on; anyone's pfctl -d stops pf and drops every reference.

import subprocess
import sys

from . import proc
from .config import ToolchainError
from .models import PfStatus

# Under com.apple/, which /etc/pf.conf evaluates (anchor "com.apple/*"); 100 sorts before Apple's own
# 200.AirDrop and 250.ApplicationFirewall, so these quick rules decide first.
ANCHOR = "com.apple/100.dotfiles-tailnet"
RULES = "/etc/pf.anchors/dotfiles-tailnet"
LABEL = "dev.dotfiles.pf-tailnet"
PLIST = f"/Library/LaunchDaemons/{LABEL}.plist"
# /var/run is emptied at every boot.
CONFIRMED = "/var/run/dotfiles-pf-tailnet.confirmed"
PFCTL = "/sbin/pfctl"
REVERT_SECONDS = 120
# launchctl print's exit code for a service it does not know.
NOT_LOADED = 113

# Runs as root, detached: argv is seconds, the confirm file, pfctl and the anchor. It ignores the hangup a closed
# terminal sends, so closing the window does not cancel the revert.
REVERT = """\
import os, signal, subprocess, sys, time
signal.signal(signal.SIGHUP, signal.SIG_IGN)
seconds, confirmed, pfctl, anchor = sys.argv[1:]
time.sleep(int(seconds))
if not os.path.exists(confirmed):
    subprocess.run([pfctl, "-a", anchor, "-F", "all"], check=False)
"""


def load() -> None:
    """Check the rules, arm the revert, load the anchor and turn pf on."""
    # pfctl parses without root; a broken file stops here, before anything changes.
    proc.call("pfctl", "-n", "-a", ANCHOR, "-f", RULES)
    proc.call("sudo", "rm", "-f", CONFIRMED)
    proc.call("sudo", "-b", sys.executable, "-I", "-c", REVERT, str(REVERT_SECONDS), CONFIRMED, PFCTL, ANCHOR)
    proc.call("sudo", PFCTL, "-a", ANCHOR, "-f", RULES)
    if not enabled():
        proc.call("sudo", PFCTL, "-E")
    proc.out(
        f"pf:load: rules loaded; they revert in {REVERT_SECONDS} s. Test ssh, Screen Sharing and file sharing "
        "over Tailscale from another device, then run: mise run pf:confirm"
    )


def confirm() -> None:
    """Keep the loaded rules: stop the revert and load them at every boot."""
    if not rules():
        msg = "pf:confirm: no rules are loaded (the revert already ran?); run: mise run pf:load"
        raise ToolchainError(msg)
    proc.call("sudo", "touch", CONFIRMED)
    proc.call("sudo", "launchctl", "enable", f"system/{LABEL}")
    if not boot():
        proc.call("sudo", "launchctl", "bootstrap", "system", PLIST)
    proc.out("pf:confirm: rules kept; a restart loads them again")


def unload() -> None:
    """Remove the rules now and stop loading them at boot; pf itself stays on."""
    if boot():
        proc.call("sudo", "launchctl", "bootout", f"system/{LABEL}")
    proc.call("sudo", "launchctl", "disable", f"system/{LABEL}")
    proc.call("sudo", PFCTL, "-a", ANCHOR, "-F", "all")
    proc.out("pf:unload: rules removed; the boot daemon is off")


def status() -> None:
    """One JSON line; exit 1 unless pf is on with the rules loaded and the boot daemon is loaded."""
    report = PfStatus(enabled=enabled(), rules=len(rules()), boot=boot())
    proc.out(report.model_dump_json())
    if not (report.enabled and report.rules and report.boot):
        raise SystemExit(1)


def enabled() -> bool:
    return "Status: Enabled" in proc.run("sudo", PFCTL, "-s", "info")


def rules() -> list[str]:
    """The anchor's rules. pfctl fails on an anchor that does not exist, and pf drops an anchor once it is
    flushed, so the parent's list of anchors is read first (xnu DIOCGETRULES; pf_remove_if_empty_ruleset)."""
    parent, _, _ = ANCHOR.partition("/")
    anchors = proc.run("sudo", PFCTL, "-a", parent, "-s", "Anchors").split()
    if ANCHOR not in anchors:
        return []
    return proc.run("sudo", PFCTL, "-a", ANCHOR, "-s", "rules").splitlines()


def boot() -> bool:
    """Whether launchd has the boot daemon loaded; launchctl print needs no root."""
    done = subprocess.run(
        ["launchctl", "print", f"system/{LABEL}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )
    if done.returncode not in {0, NOT_LOADED}:
        msg = f"launchctl exited {done.returncode}"
        raise ToolchainError(msg)
    return done.returncode == 0
