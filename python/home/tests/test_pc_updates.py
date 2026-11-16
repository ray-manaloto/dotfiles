"""pc-doctor's pending-updates line, with ssh stood in by tests/stand_in.py: each source alone, together and broken."""

# The exit codes and empty outputs follow what the PC printed through the doctor's ssh argv on 2026-11-16 (yay 13.0.1,
# checkupdates from pacman-contrib 1.13.1). The PC had nothing waiting, so the listings follow the tools' source:
# checkupdates lists `<name> <old> -> <new>` and exits 0, exits 2 when nothing waits and 1 when it cannot sync its
# temporary database (checkupdates.sh.in:150-181). yay -Qua lists the same shape plus an age badge when the AUR gave
# a last-modified time (print.go:173-179; FormatAgeTag and FormatDuration, pkg/text/time.go), and exits 0; it exits 1
# both when nothing waits (an empty error, which yay does not print) and when the AUR query failed (the error on
# stderr after " -> ", pkg/text/service.go:94-100, aur rpc/query.go:103), and it prints only after the whole query
# (print.go:122-200, pkg/upgrade/service.go:60-191, main.go). Exit 1 with no output at all is therefore the only
# "none"; any other output or exit is unknown for that source.

import json
from pathlib import Path

import pytest

from .test_pc_doctor import CHECKUPDATES, YAY, answer, doctor

NONE_OFFICIAL = {"code": 2}
NONE_AUR = {"code": 1}
OFFICIAL = {"stdout": "linux 6.17.1.arch1-1 -> 6.17.2.arch1-1\nmesa 1:25.2.4-1 -> 1:25.2.5-1\n"}
# yay's age badges in each of FormatDuration's shapes, and a line with none (no LastModified from the AUR).
AUR = {
    "stdout": "foo-bin 1.0-1 -> 1.1-1 [2d]\n"
    "bar-git r10.abc-1 -> r12.def-1 [38d8h]\n"
    "baz 2.0-1 -> 2.1-1 [1h30m]\n"
    "qux 0.9-1 -> 1.0-1 [45m]\n"
    "old 1-1 -> 2-1\n"
    "skew 1-1 -> 1-2 [-5m]\n"  # the PC's clock ahead of the AUR's: FormatDuration of a negative age
}
LISTED = [
    "official:linux 6.17.1.arch1-1 -> 6.17.2.arch1-1",
    "official:mesa 1:25.2.4-1 -> 1:25.2.5-1",
    "aur:foo-bin 1.0-1 -> 1.1-1",
    "aur:bar-git r10.abc-1 -> r12.def-1",
    "aur:baz 2.0-1 -> 2.1-1",
    "aur:qux 0.9-1 -> 1.0-1",
    "aur:old 1-1 -> 2-1",
    "aur:skew 1-1 -> 1-2",
]
AUR_DOWN = {
    "stderr": ' -> request failed: Get "https://aur.archlinux.org/rpc?arg%5B%5D=foo-bin&type=info&v=5": '
    "dial tcp: lookup aur.archlinux.org: no such host\n",
    "code": 1,
}
MISSING = {"stderr": "bash: line 1: yay: command not found\n", "code": 127}


def updates(capfd: pytest.CaptureFixture[str]) -> tuple[int, dict[str, object], str]:
    """The doctor's exit code (the bootstrap calls answer healthy), this line as a dict, and stderr."""
    code, lines, err = doctor(capfd)
    [line] = [line for line in lines if line.check == "pending-updates"]
    return code, line.model_dump(mode="json"), err


def run(
    ssh: Path, capfd: pytest.CaptureFixture[str], official: object, aur: object
) -> tuple[int, dict[str, object], str]:
    """The doctor with checkupdates and yay -Qua answering as given."""
    answer(ssh, {CHECKUPDATES: official, YAY: aur})
    return updates(capfd)


def test_no_updates_pass_with_an_empty_list(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = run(ssh, capfd, NONE_OFFICIAL, NONE_AUR)
    assert code == 0
    assert (line["result"], line["items"], line["culprits"]) == ("pass", [], [])
    assert line["detail"] == "official: none waiting; aur: none waiting"


def test_waiting_updates_pass_with_the_list(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = run(ssh, capfd, OFFICIAL, AUR)
    assert code == 0
    assert (line["result"], line["items"], line["culprits"]) == ("pass", LISTED, [])
    assert line["detail"] == "official: 2 waiting; aur: 6 waiting"


def test_an_aur_outage_is_unknown_and_the_official_list_stands(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, err = run(ssh, capfd, OFFICIAL, AUR_DOWN)
    assert code == 3
    assert (line["result"], line["items"], line["culprits"]) == ("unknown", LISTED[:2], ["aur"])
    assert line["detail"] == "official: 2 waiting; aur: unknown (yay -Qua exited 1 with an error)"
    assert "no such host" in err


def test_a_failed_sync_is_unknown_and_the_aur_answer_stands(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    failed = {"stderr": "==> ERROR: Cannot fetch updates\n", "code": 1}
    code, line, _ = run(ssh, capfd, failed, NONE_AUR)
    assert code == 3
    assert (line["result"], line["items"], line["culprits"]) == ("unknown", [], ["official"])
    assert line["detail"] == "official: unknown (checkupdates exited 1); aur: none waiting"


@pytest.mark.parametrize(
    ("official", "aur", "culprits"),
    [
        # Killed mid-listing (the time limit, a dropped connection): lines on stdout, but no clean exit.
        ({"stdout": OFFICIAL["stdout"], "code": 143}, AUR, ["official"]),
        (NONE_OFFICIAL, {"stdout": "foo-bin 1.0-1 -> 1.1-1\n", "code": 143}, ["aur"]),
        # A listing cut inside its last line.
        ({"stdout": "linux 6.17.1.arch1-1 -> 6.17.2.arch1-1\nmesa 1:25.2.4-1 ->"}, AUR, ["official"]),
    ],
    ids=["official-killed", "aur-killed", "official-cut-line"],
)
def test_partial_output_is_unknown_for_that_source(
    ssh: Path, capfd: pytest.CaptureFixture[str], official: object, aur: object, culprits: list[str]
) -> None:
    code, line, _ = run(ssh, capfd, official, aur)
    assert (code, line["result"], line["culprits"]) == (3, "unknown", culprits)
    stands = LISTED[2:] if culprits == ["official"] else []
    assert line["items"] == stands


@pytest.mark.parametrize(
    ("official", "aur", "culprit"),
    [
        ({"stdout": "not an update\n"}, NONE_AUR, "official"),
        ({"stdout": "linux 1 -> 2 [2d]\n"}, NONE_AUR, "official"),
        (NONE_OFFICIAL, {"stdout": "foo 1 -> 2 (Orphaned)\n"}, "aur"),
        (NONE_OFFICIAL, {"stdout": "foo 1 -> 2 [2 days]\n"}, "aur"),
        ({"code": 0}, NONE_AUR, "official"),
        ({"stdout": "linux 1 -> 2\n", "code": 2}, NONE_AUR, "official"),
        (NONE_OFFICIAL, {"stdout": "<html>502 Bad Gateway</html>\n"}, "aur"),
        (NONE_OFFICIAL, {"code": 0}, "aur"),
        (NONE_OFFICIAL, {"stdout": "foo-bin 1.0-1 -> 1.1-1\n", "code": 1}, "aur"),
    ],
    ids=[
        "official-garbage",
        "official-age-badge",
        "aur-not-a-badge",
        "aur-badge-with-words",
        "official-exit-0-empty",
        "official-none-with-lines",
        "aur-garbage",
        "aur-exit-0-empty",
        "aur-error-with-lines",
    ],
)
def test_malformed_output_is_unknown_and_the_other_source_stands(
    ssh: Path,
    capfd: pytest.CaptureFixture[str],
    official: object,
    aur: object,
    culprit: str,
) -> None:
    code, line, _ = run(ssh, capfd, official, aur)
    assert (code, line["result"], line["culprits"], line["items"]) == (3, "unknown", [culprit], [])
    other = "aur" if culprit == "official" else "official"
    assert f"{other}: none waiting" in str(line["detail"])


def test_a_missing_tool_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = run(ssh, capfd, NONE_OFFICIAL, MISSING)
    assert (code, line["result"], line["culprits"]) == (3, "unknown", ["aur"])
    assert line["detail"] == "official: none waiting; aur: unknown (yay was not found on the PC's PATH)"


def test_a_timeout_is_unknown_never_none(
    ssh: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PC_DOCTOR_TIMEOUT", "1")
    answer(ssh, {CHECKUPDATES: NONE_OFFICIAL | {"sleep": 30}, YAY: NONE_AUR})
    code, line, _ = updates(capfd)
    assert (code, line["result"], line["culprits"]) == (3, "unknown", ["official"])
    assert "timed out after 1 s" in str(line["detail"])


def test_an_ssh_failure_is_unknown_for_both(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    down = {"stderr": "ssh: connect to host pc port 22: Connection refused\n", "code": 255}
    answer(ssh, {CHECKUPDATES: down, YAY: down})
    code, line, _ = updates(capfd)
    assert (code, line["result"], line["culprits"], line["items"]) == (3, "unknown", ["official", "aur"], [])


def test_the_line_applies_nothing(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # Its only calls on the PC are the two queries: no pacman -Sy on the live database, no yay -Syu.
    answer(ssh, {CHECKUPDATES: OFFICIAL, YAY: AUR})
    updates(capfd)
    calls = [json.loads(call) for call in (ssh / "calls.jsonl").read_text().splitlines()]
    mine = [call[8:] for call in calls if call[8:10] != ["mise", "bootstrap"]]
    assert mine == [["checkupdates"], ["yay", "-Qua"]]


def test_a_hostile_package_line_comes_out_inert(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # CODING_STANDARDS 9: the PC's output lands in one JSON string per item; quotes and backslashes stay inside it.
    hostile = 'x"},{"check":"forged","result":"pass\\ 1 -> 2'
    code, line, _ = run(ssh, capfd, {"stdout": hostile + "\n"}, NONE_AUR)
    assert (code, line["items"]) == (0, [f"official:{hostile}"])
