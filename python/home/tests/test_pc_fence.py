"""pc-doctor's fence-drops line, with ssh stood in by tests/stand_in.py, and the fence's own rules on real iptables."""

# Ticket #741. The answers follow what iptables v1.8.13 (nf_tables) printed on the PC for `sudo -n iptables -t mangle
# -S` and `sudo -n ip6tables -t mangle -S` (2026-11-17): tailscaled's CONNMARK rules in PREROUTING and OUTPUT, and
# the fence's drops. The fence-tier tests (opt-in, //home:fence-integration, as they start Docker) run the rules files
# and the slot template's checks from config.pc.toml on the same iptables in a throwaway Arch Linux container, in its
# own network namespace.

import json
import shlex
import subprocess
import threading
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest

from hometools import pcfence

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


# The real thing: config.pc.toml's rules files and the slot template's ExecStartPre checks, run by the PC's iptables
# version (Arch Linux's iptables 1.8.13, nf_tables) in a container with its own network namespace. NET_ADMIN is that
# namespace's only extra capability; nothing reaches this Mac's own rules.

CONFIG = Path(__file__).resolve().parents[3] / "unix/home/.config/mise/config.pc.toml"
# Pinned by digest (#741 review, 2026-11-17): Arch Linux base 20261108.0.623074, the image these tests were written
# on, which ships iptables 1.8.13 (nf_tables), the PC's version. Read with docker image inspect on the pulled image.
# The fixture checks the version, so a wrong image fails loudly. Move the pin when the PC's iptables moves: to an
# Arch base image that ships the PC's new version, and VERSION with it.
IMAGE = "archlinux:base-20261108.0.623074@sha256:d4594bb2300cba11f41c2f27923eb56f63d9988909c402f9c95517d1e362c899"
VERSION = "v1.8.13 (nf_tables)"
FILES = tomllib.loads(CONFIG.read_text())["bootstrap"]["files"]


def checks() -> list[list[str]]:
    """The slot template's iptables checks, each as the argv systemd runs (systemd splits words as shlex does here)."""
    unit = FILES["/etc/systemd/system/gha-slot@.service"]["content"]
    pre = [shlex.split(text.removeprefix("ExecStartPre=")) for text in unit.splitlines() if "ExecStartPre=" in text]
    return [argv for argv in pre if "tables" in argv[0]]


class Netns:
    """A sleeping container whose network namespace holds the rules; each call is one docker exec, no shell."""

    def __init__(self, folder: Path) -> None:
        for name in ("fence.rules", "fence6.rules"):
            (folder / name).write_text(FILES[f"/etc/gha-runner/{name}"]["content"])
        started = subprocess.run(
            (
                "docker", "run", "--detach", "--rm", "--platform", "linux/amd64", "--network", "none",
                "--cap-add", "NET_ADMIN", "--volume", f"{folder}:/etc/gha-runner:ro", IMAGE, "sleep", "600",
            ),
            capture_output=True, text=True, check=True,
        )  # fmt: skip
        self.id = started.stdout.strip()

    def run(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(("docker", "exec", self.id, *argv), capture_output=True, text=True, check=False)

    def ok(self, *argv: str) -> str:
        done = self.run(*argv)
        assert done.returncode == 0, done.stderr
        return done.stdout

    def apply(self) -> None:
        """What gha-fence.service's two ExecStart lines run."""
        unit = FILES["/etc/systemd/system/gha-fence.service"]["content"]
        for text in unit.splitlines():
            if text.startswith("ExecStart="):
                argv = shlex.split(text.removeprefix("ExecStart="))
                self.ok(Path(argv[0]).name, *argv[1:])

    def stop(self) -> None:
        subprocess.run(("docker", "rm", "--force", self.id), capture_output=True, check=False)


def test_the_doctor_the_unit_and_the_slot_checks_name_the_same_drops() -> None:
    # One rule, three places: the rules files add it (-A), the slot template checks it (-C), the doctor counts it as
    # -S prints it. The fence-tier tests below prove that spelling is what iptables prints.
    added = {
        program: [text for text in FILES[f"/etc/gha-runner/{name}"]["content"].splitlines() if text.startswith("-A ")]
        for program, name in (("iptables", "fence.rules"), ("ip6tables", "fence6.rules"))
    }
    assert added == {program: list(drops) for program, drops in pcfence.DROPS.items()}
    checked = [[argv[0].rsplit("/", 1)[1], " ".join(argv[3:]).replace("-C ", "-A ", 1)] for argv in checks()]
    assert checked == [[program, rule] for program, drops in pcfence.DROPS.items() for rule in drops]


@pytest.fixture
def netns(tmp_path: Path) -> Iterator[Netns]:
    made = Netns(tmp_path)
    try:
        # The rules are proved on the PC's iptables or not at all.
        for program in ("iptables", "ip6tables"):
            assert made.ok(program, "-V").strip() == f"{program} {VERSION}"
    except AssertionError:
        made.stop()
        raise
    yield made
    made.stop()


def two_copies(ns: Netns) -> None:
    """The PC before #741: tailscaled's CONNMARK rule, the runtime INPUT drop, and the FORWARD drop twice."""
    ns.ok("iptables", "-t", "mangle", "-A", "PREROUTING", *shlex.split(CONNMARK.splitlines()[0])[2:])
    ns.ok("iptables", "-t", "mangle", "-I", "INPUT", "1", *shlex.split(INPUT4)[2:])
    for _ in range(2):
        ns.ok("iptables", "-t", "mangle", "-I", "FORWARD", "1", *shlex.split(FORWARD4)[2:])


@pytest.mark.fence
def test_the_unit_leaves_one_copy_of_each_drop_from_two(netns: Netns) -> None:
    two_copies(netns)
    for _ in range(2):  # a start, then a restart
        netns.apply()
        v4, v6 = netns.ok("iptables", "-t", "mangle", "-S"), netns.ok("ip6tables", "-t", "mangle", "-S")
        assert [pcfence.copies(v4, rule) for rule in (INPUT4, FORWARD4)] == [1, 1]
        assert pcfence.copies(v6, INPUT6) == 1
        # tailscaled's rule in another chain stays.
        assert CONNMARK.splitlines()[0].split(" -j ")[0] in v4


@pytest.mark.fence
def test_no_drop_is_missing_while_the_unit_restarts(netns: Netns) -> None:
    # One reader lists the chains as fast as it can while the unit restarts again and again; every listing it gets
    # holds each drop once. The restore is one nf_tables transaction, so no listing can see the chain between its -F
    # and its -A.
    two_copies(netns)
    netns.apply()
    seen: list[tuple[int, int]] = []
    failed: list[str] = []
    done = threading.Event()

    def read() -> None:
        # A failed listing is recorded, not asserted: an assert in this thread would end it without failing the test.
        while not done.is_set():
            listed = netns.run("iptables", "-t", "mangle", "-S")
            if listed.returncode:
                failed.append(listed.stderr)
            else:
                seen.append((pcfence.copies(listed.stdout, INPUT4), pcfence.copies(listed.stdout, FORWARD4)))

    reader = threading.Thread(target=read)
    reader.start()
    try:
        for _ in range(15):
            netns.apply()
    finally:
        done.set()
        reader.join()
    assert failed == []
    # Enough listings to overlap the restarts, not one sample taken before them.
    assert len(seen) >= 10
    assert set(seen) == {(1, 1)}


@pytest.mark.fence
def test_a_broken_rules_file_changes_nothing(netns: Netns, tmp_path: Path) -> None:
    # The whole file is one transaction: a bad last line rejects the -F lines before it too.
    two_copies(netns)
    before = netns.ok("iptables", "-t", "mangle", "-S")
    broken = FILES["/etc/gha-runner/fence.rules"]["content"].replace("COMMIT", "-A FORWARD -j NO-SUCH-CHAIN\nCOMMIT")
    (tmp_path / "fence.rules").write_text(broken)
    assert netns.run("iptables-restore", "--noflush", "/etc/gha-runner/fence.rules").returncode != 0
    assert netns.ok("iptables", "-t", "mangle", "-S") == before


@pytest.mark.fence
def test_the_slot_checks_pass_only_with_the_drops(netns: Netns) -> None:
    # The slot template's three iptables checks are what a fenced PC answers yes to, and a bare one no.
    assert len(checks()) == 3
    assert all(netns.run(Path(argv[0]).name, *argv[1:]).returncode == 1 for argv in checks())
    netns.apply()
    assert all(netns.run(Path(argv[0]).name, *argv[1:]).returncode == 0 for argv in checks())
