"""pc-doctor's fence-drops line, with ssh stood in by tests/stand_in.py."""

# Ticket #741. The answers follow what iptables v1.8.13 (nf_tables) printed on the PC for `sudo -n iptables -t mangle
# -S` and `sudo -n ip6tables -t mangle -S` (2026-11-17): tailscaled's CONNMARK rules in PREROUTING and OUTPUT, and
# the fence's drops. The fence's rules files and the slot template's checks moved to cpp-standard with the PC's
# config (machine-bootstrap migration, Phase 3). cpp-standard keeps the test that they name the same drops as this
# doctor; the opt-in Docker tests of the rules on real iptables were dropped, not moved.

import json
from pathlib import Path

import pytest

from .test_pc_doctor import FENCE4, FENCE6, answer, doctor

CHECK = "fence-drops"
CONNMARK = (
    "-A PREROUTING -m conntrack --ctstate RELATED,ESTABLISHED -m connmark ! --mark 0x0/0xff0000 -j CONNMARK "
    "--restore-mark --nfmask 0xff0000 --ctmask 0xff0000\n"
    "-A OUTPUT -m conntrack --ctstate NEW -m mark ! --mark 0x0/0xff0000 -j CONNMARK --save-mark --nfmask 0xff0000 "
    "--ctmask 0xff0000\n"
)
POLICIES = "".join(f"-P {chain} ACCEPT\n" for chain in ("PREROUTING", "INPUT", "FORWARD", "OUTPUT", "POSTROUTING"))
INPUT4 = "-A INPUT -i br-gha -m conntrack --ctstate NEW -j DROP\n"
FORWARD4 = "-A FORWARD -i br-gha -o tailscale0 -j DROP\n"
INPUT6 = "-A INPUT -i br-gha ! -p ipv6-icmp -m conntrack --ctstate NEW -j DROP\n"


def listing(*rules: str) -> dict[str, object]:
    return {"stdout": POLICIES + CONNMARK + "".join(rules)}


def line(capfd: pytest.CaptureFixture[str]) -> tuple[int, str, str, list[str], str]:
    """The exit code, then this check's result, detail and culprits, then stderr."""
    code, lines, err = doctor(capfd)
    (mine,) = [made for made in lines if made.check == CHECK]
    return code, mine.result.value, mine.detail, mine.culprits, err


def test_each_drop_once_passes(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {FENCE4: listing(INPUT4, FORWARD4), FENCE6: listing(INPUT6)})
    code, result, detail, culprits, _ = line(capfd)
    assert (code, result, culprits) == (0, "pass", [])
    assert detail == "each of the 3 fence drops is present once"


def test_a_missing_drop_fails_naming_it(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # What a reboot without gha-fence.service leaves: the launcher re-adds only the FORWARD drop.
    answer(ssh, {FENCE4: listing(FORWARD4), FENCE6: listing()})
    code, result, detail, culprits, _ = line(capfd)
    assert (code, result) == (1, "fail")
    assert detail == "fence drops missing or duplicated: 2 of 3"
    assert culprits == [
        "iptables -t mangle -A INPUT -i br-gha -m conntrack --ctstate NEW -j DROP: 0 copies",
        "ip6tables -t mangle -A INPUT -i br-gha ! -p ipv6-icmp -m conntrack --ctstate NEW -j DROP: 0 copies",
    ]


def test_a_duplicated_drop_fails_naming_it(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # The PC on 2026-11-17: slots starting at once each passed the launcher's -C before any inserted.
    answer(ssh, {FENCE4: listing(INPUT4, FORWARD4, FORWARD4), FENCE6: listing(INPUT6)})
    code, result, detail, culprits, _ = line(capfd)
    assert (code, result) == (1, "fail")
    assert detail == "fence drops missing or duplicated: 1 of 3"
    assert culprits == ["iptables -t mangle -A FORWARD -i br-gha -o tailscale0 -j DROP: 2 copies"]


def test_a_near_miss_is_not_a_copy(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # A drop for every state, or one on another bridge, is not the fence's rule.
    near = ("-A INPUT -i br-gha -j DROP\n", "-A INPUT -i br-gha2 -m conntrack --ctstate NEW -j DROP\n")
    answer(ssh, {FENCE4: listing(*near, FORWARD4), FENCE6: listing(INPUT6)})
    code, result, _, culprits, _ = line(capfd)
    assert (code, result) == (1, "fail")
    assert culprits == ["iptables -t mangle -A INPUT -i br-gha -m conntrack --ctstate NEW -j DROP: 0 copies"]


def test_sudo_that_needs_a_password_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {FENCE4: {"stderr": "sudo: a password is required\n", "code": 1}})
    code, result, detail, _, err = line(capfd)
    assert (code, result, detail) == (3, "unknown", "sudo -n iptables -t mangle -S exited 1")
    assert "password is required" in err


def test_a_missing_ip6tables_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    missing = {"stderr": "sudo: ip6tables: command not found\n", "code": 1}
    answer(ssh, {FENCE4: listing(INPUT4, FORWARD4), FENCE6: missing})
    code, result, detail, _, _ = line(capfd)
    assert (code, result, detail) == (3, "unknown", "sudo -n ip6tables -t mangle -S exited 1")


def test_output_that_is_not_a_mangle_listing_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # No policy line for INPUT: whatever printed this was not iptables -S of the mangle table, so a missing drop in
    # it proves nothing.
    answer(ssh, {FENCE4: {"stdout": "# Warning: iptables-legacy tables present\n"}})
    code, result, detail, _, _ = line(capfd)
    assert (code, result, detail) == (3, "unknown", "sudo -n iptables -t mangle -S printed no mangle INPUT chain")


@pytest.mark.parametrize("hung", [FENCE4, FENCE6])
def test_a_timeout_is_unknown(
    hung: str, ssh: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PC_DOCTOR_TIMEOUT", "5")  # far above a stand-in call; the hung one sleeps 30 (#749)
    script = {FENCE4: listing(INPUT4, FORWARD4), FENCE6: listing(INPUT6)}
    script[hung] = script[hung] | {"sleep": 30}
    answer(ssh, script)
    code, result, detail, _, _ = line(capfd)
    assert (code, result) == (3, "unknown")
    assert detail.endswith("timed out after 5 s")


def test_an_ssh_failure_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {FENCE4: {"stderr": "ssh: connect to host pc port 22: Connection refused\n", "code": 255}})
    code, result, detail, _, _ = line(capfd)
    assert (code, result, detail) == (3, "unknown", "ssh pc failed (exit 255)")


def test_a_drop_seen_missing_fails_even_when_the_other_listing_is_unread(
    ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    answer(ssh, {FENCE4: listing(FORWARD4), FENCE6: {"stderr": "sudo: a password is required\n", "code": 1}})
    code, result, detail, culprits, _ = line(capfd)
    assert (code, result) == (1, "fail")
    assert detail == ("fence drops missing or duplicated: 1 of 3 (not read: sudo -n ip6tables -t mangle -S exited 1)")
    assert culprits == ["iptables -t mangle -A INPUT -i br-gha -m conntrack --ctstate NEW -j DROP: 0 copies"]


def test_sudo_never_prompts(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # A doctor that waited on a password prompt would hang until its time limit: every call is sudo -n.
    answer(ssh, {})
    line(capfd)
    calls = [json.loads(call) for call in (ssh / "calls.jsonl").read_text().splitlines()]
    fence = [call for call in calls if "sudo" in call]
    assert [call[call.index("sudo") :] for call in fence] == [
        ["sudo", "-n", "iptables", "-t", "mangle", "-S"],
        ["sudo", "-n", "ip6tables", "-t", "mangle", "-S"],
    ]
