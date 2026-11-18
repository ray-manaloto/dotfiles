"""pc-doctor's gpu-cdi line through the doctor, with ssh stood in: pass, each failure, and each unknown."""

# Spec #729, ticket #732. The answers are tests/pc_gpu.py's, from what the PC printed on 2026-11-16; the warning and
# the missing library follow a scratch CDI folder qualified on the PC (a malformed spec beside NVIDIA's: nvidia-ctk
# exits 0 and warns; a spec mounting a missing binary: nvidia-ctk exits 0 and says nothing, stat exits 1).

import json
import shlex
from collections.abc import Mapping
from pathlib import Path

import pytest

from hometools.models import PcDoctorLine

from . import pc_gpu as gpu
from .test_pc_doctor import HEALTHY, PLAN, STATUS, doctor, entry, plan, status

BOOTSTRAP = {PLAN: plan(entry("noop")), STATUS: status(entry("noop"))}
WARNING = (
    'time="2026-11-16T17:22:18-06:00" level=warning msg="The following registry errors were reported:"\n'
    'time="2026-11-16T17:22:18-06:00" level=warning msg="/etc/cdi/bad.yaml: [failed to load CDI Spec failed to parse '
    "CDI Spec \\\"/etc/cdi/bad.yaml\\\": failed to unmarshal CDI Spec: yaml: line 2: did not find expected ',' or "
    "'}']\"\n" + gpu.FOUND
)


def gpu_line(
    folder: Path, capfd: pytest.CaptureFixture[str], changed: Mapping[str, object]
) -> tuple[int, PcDoctorLine, str]:
    """The doctor's exit code, its gpu-cdi line as JSON, and stderr, with every other line passing."""
    (folder / "script.json").write_text(json.dumps({**HEALTHY, **BOOTSTRAP, **changed}))
    code, lines, err = doctor(capfd)
    made = [line for line in lines if line.check == "gpu-cdi"]
    assert len(made) == 1
    return code, made[0], err


def calls(folder: Path) -> list[list[str]]:
    return [json.loads(row) for row in (folder / "calls.jsonl").read_text().splitlines()]


def test_a_pc_set_up_as_declared_passes(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {})
    assert (code, line.result.value, line.culprits) == (0, "pass", [])


def test_a_missing_toolkit_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.PACMAN: gpu.pacman(toolkit=False)})
    assert (code, line.result.value, line.culprits) == (1, "fail", ["package:nvidia-container-toolkit"])


def test_a_stopped_path_unit_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    stopped = gpu.unit("nvidia-cdi-refresh.path", "disabled/inactive/dead")
    code, line, _ = gpu_line(ssh, capfd, {gpu.UNITS: gpu.units(path=stopped)})
    assert (code, line.result.value, line.culprits) == (1, "fail", ["unit:nvidia-cdi-refresh.path"])
    assert "disabled, inactive (dead)" in line.detail


def test_an_enabled_path_unit_that_is_not_waiting_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    stopped = gpu.unit("nvidia-cdi-refresh.path", "enabled/inactive/dead")
    code, line, _ = gpu_line(ssh, capfd, {gpu.UNITS: gpu.units(path=stopped)})
    assert (code, line.culprits) == (1, ["unit:nvidia-cdi-refresh.path"])


@pytest.mark.parametrize(
    ("active", "result"), [("failed", "exit-code"), ("failed", "start-limit-hit"), ("inactive", "exit-code")]
)
def test_a_failed_last_generation_fails(active: str, result: str, ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    failed = gpu.unit("nvidia-cdi-refresh.service", f"enabled/{active}/{active}", result=result)
    code, line, _ = gpu_line(ssh, capfd, {gpu.UNITS: gpu.units(service=failed)})
    assert (code, line.result.value, line.culprits) == (1, "fail", ["unit:nvidia-cdi-refresh.service"])
    assert f"last result {result}" in line.detail


def test_a_refresh_service_that_is_not_installed_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    gone = gpu.unit("nvidia-cdi-refresh.service", "/inactive/dead", load="not-found")
    code, line, _ = gpu_line(ssh, capfd, {gpu.UNITS: gpu.units(service=gone)})
    assert (code, line.culprits) == (1, ["unit:nvidia-cdi-refresh.service"])


def test_a_spec_warning_on_exit_0_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.cdi_list(): gpu.listed(stderr=WARNING)})
    assert (code, line.result.value) == (1, "fail")
    assert line.culprits[0] == "cdi-warning:The following registry errors were reported:"
    assert "/etc/cdi/bad.yaml: [failed to load CDI Spec" in line.culprits[1]
    assert len(line.culprits) == 2


def test_a_gpu_that_does_not_resolve_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.cdi_list(): gpu.listed(devices=())})
    assert (code, line.culprits) == (1, ["cdi:nvidia.com/gpu=all"])


def test_docker_without_a_cdi_folder_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.DOCKER: {"stdout": "[]\n"}})
    assert (code, line.culprits) == (1, ["cdi:nvidia.com/gpu=all"])
    assert not any("nvidia-ctk" in argv for argv in calls(ssh))


def test_a_missing_library_fails_naming_it(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.stat(): gpu.stated(missing=(gpu.LIBRARY,))})
    assert (code, line.result.value, line.culprits) == (1, "fail", [f"file:{gpu.LIBRARY}"])


def test_a_driver_mismatch_fails_as_reboot_required(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.MODULE: gpu.module("615.70.02")})
    assert (code, line.result.value, line.culprits) == (1, "fail", ["driver-reboot-required"])
    assert "615.70.02" in line.detail
    assert "615.78.08" in line.detail


def test_a_driver_mismatch_is_named_beside_other_failures(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    changed = {gpu.MODULE: gpu.module("615.70.02"), gpu.stat(): gpu.stated(missing=(gpu.LIBRARY,))}
    code, line, _ = gpu_line(ssh, capfd, changed)
    assert (code, line.culprits) == (1, [f"file:{gpu.LIBRARY}", "driver-reboot-required"])


def test_an_epoch_and_release_are_not_part_of_the_driver_version(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.PACMAN: gpu.pacman(utils="1:615.78.08-3")})
    assert (code, line.result.value) == (0, "pass")


def test_a_missing_library_and_an_unreadable_driver_fail_not_unknown(
    ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    unloaded = {"stderr": "cat: /proc/driver/nvidia/version: No such file or directory\n", "code": 1}
    changed = {gpu.MODULE: unloaded, gpu.stat(): gpu.stated(missing=(gpu.LIBRARY,))}
    code, line, _ = gpu_line(ssh, capfd, changed)
    assert (code, line.result.value, line.culprits) == (1, "fail", [f"file:{gpu.LIBRARY}"])
    assert "could not read: cat exited 1" in line.detail


def test_an_unreachable_pc_costs_one_call(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    down = {"stderr": "ssh: connect to host pc port 22: Connection refused\n", "code": 255}
    code, line, _ = gpu_line(ssh, capfd, {gpu.PACMAN: down})
    assert (code, line.result.value, line.detail) == (3, "unknown", "ssh pc failed (exit 255)")
    made = calls(ssh)
    assert json.loads(gpu.PACMAN) in made
    later = (gpu.UNITS, gpu.DOCKER, gpu.cdi_list(), gpu.find(), gpu.stat(), gpu.MODULE)
    assert not any(json.loads(key) in made for key in later)


SPEC_DIRS_NULL = {gpu.DOCKER: {"stdout": "null\n"}}
GARBLED_UNITS = {gpu.UNITS: {"stdout": "Id=nvidia-cdi-refresh.path\nLoadState=loaded\n"}}
GARBLED_PACMAN = {gpu.PACMAN: {"stdout": "nvidia-container-toolkit\n"}}
GARBLED_FIND = {gpu.find(): {"stdout": "/run/cdi/nvidia.yaml\0text"}}
GARBLED_SPEC = {gpu.find(): gpu.found({gpu.SPEC_FILE: "devices: [ {name: x\n"})}
SPEC_WITHOUT_KIND = {gpu.find(): gpu.found({gpu.SPEC_FILE: "cdiVersion: 0.7.0\n"})}
GARBLED_MODULE = {gpu.MODULE: {"stdout": "NVRM version: something else\n"}}
NO_UTILS = {gpu.PACMAN: gpu.pacman(utils=None)}
PACMAN_LOCKED = {gpu.PACMAN: {"stderr": "error: could not open database\n", "code": 1}}
DOCKER_DOWN = {gpu.DOCKER: {"stderr": "Cannot connect to the Docker daemon\n", "code": 1}}


@pytest.mark.parametrize(
    ("changed", "why"),
    [
        (SPEC_DIRS_NULL, "docker info printed no CDI folders"),
        (GARBLED_UNITS, "did not print both refresh units"),
        (GARBLED_PACMAN, "pacman -Q printed 'nvidia-container-toolkit'"),
        (GARBLED_FIND, "did not parse"),
        (GARBLED_SPEC, "/run/cdi/nvidia.yaml did not parse: ParserError"),
        (SPEC_WITHOUT_KIND, "/run/cdi/nvidia.yaml did not parse: ValidationError"),
        (GARBLED_MODULE, "did not name the module's version"),
        (NO_UTILS, "nvidia-utils is not installed"),
        (PACMAN_LOCKED, "pacman -Q failed"),
        (DOCKER_DOWN, "docker exited 1"),
    ],
    ids=[
        "docker-null",
        "units",
        "pacman",
        "find",
        "spec-yaml",
        "spec-model",
        "module",
        "no-utils",
        "pacman-error",
        "docker-down",
    ],
)
def test_output_that_does_not_parse_is_unknown(
    changed: dict[str, object], why: str, ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    code, line, _ = gpu_line(ssh, capfd, changed)
    assert (code, line.result.value) == (3, "unknown")
    assert why in line.detail


@pytest.mark.parametrize(
    ("key", "name"),
    [(gpu.cdi_list(), "nvidia-ctk"), (gpu.find(), "find"), (gpu.stat(), "stat")],
    ids=["nvidia-ctk", "find", "stat"],
)
def test_a_command_that_errors_is_unknown(key: str, name: str, ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # 127: what the PC's shell answers for a command that is not installed.
    code, line, _ = gpu_line(ssh, capfd, {key: {"stderr": f"bash: {name}: command not found\n", "code": 127}})
    assert (code, line.result.value, line.detail) == (3, "unknown", f"{name} exited 127")


def test_a_folder_that_is_not_an_absolute_path_is_unknown_and_never_reaches_find(
    ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    # CODING_STANDARDS 9: the folders come from Docker on the PC; quoting keeps "-delete" one word, but find would
    # still read it as an expression, so only absolute paths are taken.
    code, line, _ = gpu_line(ssh, capfd, {gpu.DOCKER: {"stdout": json.dumps(["/etc/cdi", "-delete"])}})
    assert (code, line.result.value) == (3, "unknown")
    assert "docker info printed no CDI folders" in line.detail
    assert not any("find" in argv or "nvidia-ctk" in argv for argv in calls(ssh))


def test_a_folder_docker_lists_but_that_is_missing_holds_no_spec(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # After the hand-made spec is retired, /etc/cdi may be gone: find says so and still lists /run/cdi.
    listing = gpu.SPECS | {"stderr": "find: '/etc/cdi': No such file or directory\n", "code": 1}
    code, line, _ = gpu_line(ssh, capfd, {gpu.find(): listing})
    assert (code, line.result.value) == (0, "pass")


def test_any_other_find_complaint_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    listing = gpu.SPECS | {"stderr": "find: '/etc/cdi': Permission denied\n", "code": 1}
    code, line, _ = gpu_line(ssh, capfd, {gpu.find(): listing})
    assert (code, line.result.value, line.detail) == (3, "unknown", "find could not list the CDI folders")


def test_a_path_stat_cannot_read_is_unknown_not_missing(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.stat(): gpu.stated(denied=(gpu.LIBRARY,))})
    assert (code, line.result.value, line.culprits) == (3, "unknown", [])
    assert f"stat could not read {gpu.LIBRARY}: Permission denied" in line.detail


def test_a_missing_path_still_fails_beside_one_stat_cannot_read(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # One stat call, two complaints: the missing library is confirmed, the unreadable binary is not.
    unreadable = gpu.PATHS[2]
    code, line, _ = gpu_line(ssh, capfd, {gpu.stat(): gpu.stated(missing=(gpu.LIBRARY,), denied=(unreadable,))})
    assert (code, line.result.value, line.culprits) == (1, "fail", [f"file:{gpu.LIBRARY}"])
    assert f"could not read: stat could not read {unreadable}: Permission denied" in line.detail


@pytest.mark.parametrize(
    "stderr",
    ["stat: something else went wrong\n", "stat: cannot statx '/usr/lib/unbalanced: No such file or directory\n"],
    ids=["no-name", "name-that-does-not-parse"],
)
def test_a_path_stat_names_in_no_message_is_unknown(stderr: str, ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # Exit 1 and a path missing from stdout, but no message naming it: nothing is confirmed missing.
    garbled = gpu.stated(missing=(gpu.LIBRARY,)) | {"stderr": stderr}
    code, line, _ = gpu_line(ssh, capfd, {gpu.stat(): garbled})
    assert (code, line.result.value, line.culprits) == (3, "unknown", [])
    assert "stat said nothing about 1 paths" in line.detail


def test_a_spec_reached_through_a_link_is_read(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # CDI reads every entry of a spec folder that is not a directory (container-device-interface v1.1.1,
    # pkg/cdi/spec-dirs.go:84-96), so a link to a spec counts: the find call leaves out only directories, and the
    # linked spec's mounts are checked like any other.
    link = "/etc/cdi/nvidia.yaml"
    text = gpu.spec(*gpu.PATHS)
    changed = {gpu.find(): gpu.found({link: text}), gpu.stat(): gpu.stated(missing=(gpu.LIBRARY,))}
    code, line, _ = gpu_line(ssh, capfd, changed)
    assert (code, line.culprits) == (1, [f"file:{gpu.LIBRARY}"])
    # The words as the PC's shell reads them.
    sent = shlex.split(" ".join(next(argv for argv in calls(ssh) if "find" in argv)[8:]))
    assert "-mindepth 1 -maxdepth 1 ! -type d (" in " ".join(sent)
    assert "f" not in sent


def test_specs_that_mount_nothing_need_no_stat(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = gpu_line(ssh, capfd, {gpu.find(): gpu.found({gpu.SPEC_FILE: gpu.spec()})})
    assert (code, line.result.value) == (0, "pass")
    assert not any("stat" in argv for argv in calls(ssh))


def test_a_hostile_mount_path_stays_one_quoted_word(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # CODING_STANDARDS 9: the path comes from a spec file on the PC; the PC's shell must get it as one word, and the
    # culprit must stay inside one JSON string.
    hostile = '/usr/lib/a b\';touch /tmp/x;\'"},{"check":"forged'
    text = gpu.spec(json.dumps(hostile))
    changed = {gpu.find(): gpu.found({gpu.SPEC_FILE: text}), gpu.stat((hostile,)): gpu.stated((hostile,), (hostile,))}
    code, line, _ = gpu_line(ssh, capfd, changed)
    assert (code, line.culprits) == (1, [f"file:{hostile}"])
    sent = next(argv for argv in calls(ssh) if "stat" in argv)
    assert sent[-1] == "'/usr/lib/a b'\"'\"';touch /tmp/x;'\"'\"'\"},{\"check\":\"forged'"
