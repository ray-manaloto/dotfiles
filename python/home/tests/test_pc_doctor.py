"""pc-doctor in-process, with ssh stood in by tests/stand_in.py: each result, the exit table and the time limit."""

# The PC is a networked host, so ssh answers from a script (CODING_STANDARDS 2). The answers follow the JSON that
# mise 2026.11.8 printed on the PC for `bootstrap plan --json --detailed-exitcode` and `bootstrap status --missing
# --json` (2026-11-16), with the paths in origin replaced by placeholders.

import json
from pathlib import Path

import pytest

from hometools.cli import main
from hometools.models import PcDoctorLine

from . import pc_gpu

SSH = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "pc", "--", "mise", "bootstrap"]
PLAN = json.dumps([*SSH, "plan", "--json", "--detailed-exitcode"])
STATUS = json.dumps([*SSH, "status", "--missing", "--json"])
# Each later pc:doctor line's own calls (its cases are in tests/test_pc_<check>.py).
CHECKUPDATES = json.dumps([*SSH[:-2], "checkupdates"])
YAY = json.dumps([*SSH[:-2], "yay", "-Qua"])
KERNEL_KEYS = ("kernel.kptr_restrict", "kernel.sysrq", "kernel.printk", "kernel.core_pattern", "fs.protected_regular")
KERNEL = json.dumps([*SSH[:-2], "sysctl", *KERNEL_KEYS])
UNIT = "/etc/systemd/system/gha-slot@.service"
CULPRIT = f"file:{UNIT}"


def entry(action: str, environment: tuple[str, ...] = ("pc",), name: str = UNIT) -> dict[str, object]:
    origin = {"config": "~/.config/mise/config.pc.toml", "config_root": "~", "environment": list(environment)}
    return {"id": {"kind": "file", "name": name}, "action": action, "origin": origin, "phase": "post-packages"}


def plan(*entries: dict[str, object], code: int = 0) -> dict[str, object]:
    return {"stdout": json.dumps({"resources": list(entries), "summary": {}}), "code": code}


def status(*entries: dict[str, object], tools: tuple[dict[str, object], ...] = (), code: int = 0) -> dict[str, object]:
    report = {"files": list(entries), "services": [], "dotfiles": {"files": [], "edits": []}, "tools": list(tools)}
    return {"stdout": json.dumps(report), "code": code}


# One of the Omarchy system config's lazy tools, missing as on the PC: not declared by the pc environment.
LAZY: dict[str, object] = {"tool": "amp", "requested_version": "latest", "state": "missing", "installed": False}
SSH_FAILED = {"stderr": "ssh: connect to host pc port 22: Connection refused\n", "code": 255}


# Every line answers healthy unless a test scripts its call: one entry per call, so a test of one line still reads
# every other line as pass and the exit code stays that line's.
HEALTHY: dict[str, object] = {
    PLAN: plan(entry("noop")),
    STATUS: status(entry("noop")),
    CHECKUPDATES: {"code": 2},
    YAY: {"code": 1},
    # gpu-cdi (#732): its seven calls on a PC set up as dotfiles declares (tests/pc_gpu.py).
    **pc_gpu.HEALTHY,
    # kernel-settings (#730): sysctl with the PC's boot values (procps-ng 4.0.7; kernel.printk tab-separated).
    KERNEL: {
        "stdout": "kernel.kptr_restrict = 0\nkernel.sysrq = 16\nkernel.printk = 0\t4\t1\t4\n"
        "kernel.core_pattern = |/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h %d %F %I\n"
        "fs.protected_regular = 1\n"
    },
}


def answer(folder: Path, script: dict[str, object]) -> None:
    (folder / "script.json").write_text(json.dumps(HEALTHY | script))


def doctor(capfd: pytest.CaptureFixture[str]) -> tuple[int, list[PcDoctorLine], str]:
    """The exit code, each stdout line read as the contract's model (so every line keeps the contract), and stderr."""
    try:
        main(["pc-doctor"])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, [PcDoctorLine.model_validate_json(line) for line in out.splitlines()], err


def bootstrap(lines: list[PcDoctorLine]) -> list[PcDoctorLine]:
    """The lines this file is about; the others answer healthy."""
    return [line for line in lines if line.check.startswith("bootstrap-")]


def results(lines: list[PcDoctorLine]) -> dict[str, str]:
    return {line.check: line.result.value for line in bootstrap(lines)}


def test_a_matching_pc_passes_every_line(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {PLAN: plan(entry("noop")), STATUS: status(entry("noop"))})
    code, lines, _ = doctor(capfd)
    assert code == 0
    assert results(lines) == {"bootstrap-status": "pass", "bootstrap-plan": "pass"}
    assert all(line.culprits == [] for line in bootstrap(lines))


def test_a_drifted_file_fails_and_is_named(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {PLAN: plan(entry("update"), code=2), STATUS: status(entry("update"), code=1)})
    code, lines, _ = doctor(capfd)
    assert code == 1
    assert results(lines) == {"bootstrap-status": "fail", "bootstrap-plan": "fail"}
    assert all(line.culprits == [CULPRIT] for line in bootstrap(lines))


def test_a_hostile_culprit_name_comes_out_inert(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # CODING_STANDARDS 9: the name comes from the PC's mise; quotes, backslashes and a newline must stay inside one
    # JSON string, so stdout still holds exactly one event per check.
    hostile = '/etc/a"b\\\\c\nd"},{"check":"forged","result":"pass'
    answer(ssh, {PLAN: plan(entry("update", name=hostile), code=2), STATUS: status(entry("noop"))})
    code, lines, _ = doctor(capfd)
    assert (code, [line.check for line in bootstrap(lines)]) == (1, ["bootstrap-status", "bootstrap-plan"])
    assert lines[1].culprits == [f"file:{hostile}"]


def test_differences_outside_the_pc_environment_are_not_judged(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    other = entry("create", environment=(), name="/etc/elsewhere.conf")
    answer(ssh, {PLAN: plan(entry("noop"), other, code=2), STATUS: status(entry("noop"), tools=(LAZY,), code=1)})
    code, lines, err = doctor(capfd)
    assert (code, results(lines)) == (0, {"bootstrap-status": "pass", "bootstrap-plan": "pass"})
    assert "outside the pc environment" in err


def test_an_unselected_environment_fails_instead_of_reading_as_green(
    ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    # What the PC printed before it selected pc: an empty plan that exits 0.
    answer(ssh, {PLAN: plan(), STATUS: status(tools=(LAZY,), code=1)})
    code, lines, _ = doctor(capfd)
    assert code == 1
    assert results(lines) == {"bootstrap-status": "fail", "bootstrap-plan": "fail"}
    assert all("no entry from the pc environment" in line.detail for line in bootstrap(lines))


def test_an_ssh_failure_is_unknown_and_exits_3(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {PLAN: SSH_FAILED, STATUS: SSH_FAILED})
    code, lines, err = doctor(capfd)
    assert code == 3
    assert results(lines) == {"bootstrap-status": "unknown", "bootstrap-plan": "unknown"}
    assert "Connection refused" in err


def test_a_timeout_is_unknown_never_a_pass(
    ssh: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PC_DOCTOR_TIMEOUT", "1")
    hung = plan(entry("noop")) | {"sleep": 30}
    answer(ssh, {PLAN: hung, STATUS: status(entry("noop"))})
    code, lines, _ = doctor(capfd)
    assert code == 3
    assert results(lines) == {"bootstrap-status": "pass", "bootstrap-plan": "unknown"}
    assert "timed out after 1 s" in lines[1].detail


def test_mixed_fail_and_unknown_exits_1(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {PLAN: plan(entry("update"), code=2), STATUS: SSH_FAILED})
    code, lines, _ = doctor(capfd)
    assert (code, results(lines)) == (1, {"bootstrap-status": "unknown", "bootstrap-plan": "fail"})


@pytest.mark.parametrize(
    "stdout",
    ["not json", "[]", "{}", json.dumps({"resources": [{"origin": {"environment": ["pc"]}, "action": "noop"}]})],
    ids=["not-json", "not-an-object", "no-envelope", "entry-without-id"],
)
def test_output_that_does_not_parse_is_unknown(stdout: str, ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {PLAN: {"stdout": stdout}, STATUS: status(entry("noop"))})
    code, lines, _ = doctor(capfd)
    assert (code, results(lines)) == (3, {"bootstrap-status": "pass", "bootstrap-plan": "unknown"})
    assert "did not parse" in lines[1].detail


def test_an_entry_mise_could_not_read_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {PLAN: plan(entry("unknown"), code=1), STATUS: status(entry("noop"))})
    code, lines, _ = doctor(capfd)
    assert (code, results(lines)) == (3, {"bootstrap-status": "pass", "bootstrap-plan": "unknown"})
    assert lines[1].culprits == [CULPRIT]


def test_a_failed_plan_with_no_entries_is_unknown_not_an_unselected_environment(
    ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    answer(ssh, {PLAN: plan(code=1), STATUS: status(entry("noop"))})
    code, lines, _ = doctor(capfd)
    assert (code, results(lines)) == (3, {"bootstrap-status": "pass", "bootstrap-plan": "unknown"})
    assert "exited 1" in lines[1].detail


def test_an_entry_without_an_action_is_unknown_not_drift(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    bare = {key: value for key, value in entry("noop").items() if key != "action"}
    answer(ssh, {PLAN: plan(entry("noop")), STATUS: status(bare)})
    code, lines, _ = doctor(capfd)
    assert (code, results(lines)) == (3, {"bootstrap-status": "unknown", "bootstrap-plan": "pass"})
    assert lines[0].culprits == [CULPRIT]


def test_a_failed_plan_with_no_drift_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # --detailed-exitcode's 1: planning failed, so a clean list is not proof.
    answer(ssh, {PLAN: plan(entry("noop"), code=1), STATUS: status(entry("noop"))})
    code, lines, _ = doctor(capfd)
    assert (code, results(lines)) == (3, {"bootstrap-status": "pass", "bootstrap-plan": "unknown"})
    assert "exited 1" in lines[1].detail


def test_a_missing_ssh_is_unknown(
    ssh: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(ssh.parent))
    code, lines, _ = doctor(capfd)
    assert code == 3
    assert all(line.result.value == "unknown" and line.detail.startswith("ssh: ") for line in bootstrap(lines))


@pytest.mark.parametrize("limit", ["soon", "0", "-5", "nan", "inf", "1e999"])
def test_a_bad_time_limit_is_a_usage_error(
    limit: str, ssh: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PC_DOCTOR_TIMEOUT", limit)
    code, lines, err = doctor(capfd)
    assert (code, lines) == (2, [])
    assert "PC_DOCTOR_TIMEOUT" in json.loads(err)["error"]
    assert not (ssh / "calls.jsonl").exists()
