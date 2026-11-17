"""pc-doctor's privileged-containers line, with ssh stood in by tests/stand_in.py (spec #729, ticket #731)."""

# The answers follow what Docker 29.9.2 printed on the PC for `docker --host unix:///var/run/docker.sock ps --quiet
# --no-trunc` and `container inspect <id>...` (2026-11-16); names, images and ids here are made up.

import json
from pathlib import Path

import pytest

from .test_pc_doctor import DOCKER, LIST, answer, doctor

CHECK = "privileged-containers"
SENTINEL = "TOKEN=never-printed"
WEB, JOB, GONE = ("a" * 64, "b" * 64, "c" * 64)


def listing(*ids: str, code: int = 0) -> dict[str, object]:
    return {"stdout": "".join(f"{i}\n" for i in ids), "code": code}


def inspect(*ids: str) -> str:
    return json.dumps([*DOCKER, "container", "inspect", *ids])


def container(cid: str, name: str, image: str, *, privileged: bool = False) -> dict[str, object]:
    # A real object has some hundred fields more (Env among them); the doctor reads these four.
    return {
        "Id": cid,
        "Name": f"/{name}",
        "Config": {"Image": image, "Env": ["TOKEN=never-printed"]},
        "HostConfig": {"Privileged": privileged, "CapDrop": ["ALL"]},
    }


def found(*objects: dict[str, object], missing: tuple[str, ...] = ()) -> dict[str, object]:
    stderr = "".join(f"Error response from daemon: No such container: {i}\n" for i in missing)
    return {"stdout": json.dumps(objects, indent=4), "stderr": stderr, "code": 1 if missing else 0}


def line(capfd: pytest.CaptureFixture[str]) -> tuple[int, str, str, list[str], str]:
    """The exit code, then this check's result, detail and culprits, then stderr."""
    code, lines, err = doctor(capfd)
    (mine,) = [made for made in lines if made.check == CHECK]
    return code, mine.result.value, mine.detail, mine.culprits, err


def test_no_privileged_container_passes(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    web, job = container(WEB, "web", "example/web:1"), container(JOB, "job-1", "local/job:latest")
    answer(ssh, {LIST: listing(WEB, JOB), inspect(WEB, JOB): found(web, job)})
    code, result, detail, culprits, _ = line(capfd)
    assert (code, result, culprits) == (0, "pass", [])
    assert detail == "none of 2 running containers is privileged"


def test_a_privileged_container_fails_naming_it_and_its_image(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    web, job = container(WEB, "web", "example/web:1"), container(JOB, "job-1", "local/job:latest", privileged=True)
    answer(ssh, {LIST: listing(WEB, JOB), inspect(WEB, JOB): found(web, job)})
    code, result, detail, culprits, err = line(capfd)
    assert (code, result, culprits) == (1, "fail", ["container:job-1 image:local/job:latest"])
    assert detail == "privileged containers running: 1"
    assert "never-printed" not in err


def test_no_running_container_passes_without_inspecting(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {LIST: listing()})
    code, result, detail, _, _ = line(capfd)
    assert (code, result, detail) == (0, "pass", "no running container")
    assert not any('"inspect"' in call for call in (ssh / "calls.jsonl").read_text().splitlines())


def test_a_container_that_vanishes_mid_inspection_is_skipped(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    web = container(WEB, "web", "example/web:1")
    answer(ssh, {LIST: listing(WEB, GONE), inspect(WEB, GONE): found(web, missing=(GONE,))})
    code, result, detail, _, _ = line(capfd)
    assert (code, result, detail) == (
        0,
        "pass",
        "none of 1 running containers is privileged (1 gone before inspect, skipped)",
    )


def test_every_container_vanishing_passes(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {LIST: listing(GONE), inspect(GONE): found(missing=(GONE,))})
    code, result, _, _, _ = line(capfd)
    assert (code, result) == (0, "pass")


def test_a_privileged_container_in_an_incomplete_listing_still_fails(
    ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    job = container(JOB, "job-1", "local/job:latest", privileged=True)
    answer(ssh, {LIST: listing(WEB, JOB), inspect(WEB, JOB): found(job) | {"code": 1}})
    code, result, _, culprits, _ = line(capfd)
    assert (code, result, culprits) == (1, "fail", ["container:job-1 image:local/job:latest"])


@pytest.mark.parametrize(
    "inspected",
    [
        # One listed container neither inspected nor named as gone.
        found(container(WEB, "web", "example/web:1")),
        # Exit 1 with nothing named as gone: the daemon failed, not a container.
        found(container(WEB, "web", "example/web:1"), container(JOB, "job", "j:1")) | {"code": 1},
        # An object for a container that was never listed.
        found(*(container(i, "x", "x:1") for i in (WEB, JOB, GONE))),
    ],
    ids=["one-unaccounted", "error-exit", "unlisted-object"],
)
def test_an_incomplete_listing_is_unknown(
    inspected: dict[str, object], ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    answer(ssh, {LIST: listing(WEB, JOB), inspect(WEB, JOB): inspected})
    code, result, detail, _, _ = line(capfd)
    assert (code, result) == (3, "unknown")
    assert "did not account for every listed container" in detail


def test_a_failed_ps_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    daemon_down = {"stderr": "Cannot connect to the Docker daemon at unix:///var/run/docker.sock.\n", "code": 1}
    answer(ssh, {LIST: daemon_down})
    code, result, detail, _, err = line(capfd)
    assert (code, result, detail) == (3, "unknown", "docker ps exited 1")
    assert "Cannot connect" in err


def test_a_missing_docker_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # What ssh returns when the PC has no docker: the remote shell's 127.
    answer(ssh, {LIST: {"stderr": "bash: line 1: docker: command not found\n", "code": 127}})
    code, result, detail, _, _ = line(capfd)
    assert (code, result, detail) == (3, "unknown", "docker ps exited 127")


@pytest.mark.parametrize(
    "stdout",
    ["CONTAINER ID   IMAGE\n", "abc123\n", f"{WEB}; reboot\n"],
    ids=["header", "short-id", "shell-text"],
)
def test_ps_output_that_is_not_ids_is_unknown(stdout: str, ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    answer(ssh, {LIST: {"stdout": stdout}})
    code, result, detail, _, _ = line(capfd)
    assert (code, result, detail) == (3, "unknown", "docker ps printed something other than container ids")
    assert not any('"inspect"' in call for call in (ssh / "calls.jsonl").read_text().splitlines())


@pytest.mark.parametrize(
    "stdout",
    # The sentinel stands for a secret in a container's environment. The last two are valid JSON, so they reach model
    # validation, and the sentinel sits inside a value the error could quote.
    [
        f"not json {SENTINEL}",
        json.dumps({"Config": {"Env": [SENTINEL]}}),
        json.dumps([{"Id": WEB, "Name": "/web", "Config": {"Image": "x:1", "Env": [SENTINEL]}}]),
    ],
    ids=["not-json", "not-a-list", "no-hostconfig"],
)
def test_inspect_output_that_does_not_parse_is_unknown(
    stdout: str, ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    answer(ssh, {LIST: listing(WEB), inspect(WEB): {"stdout": stdout}})
    code, lines, err = doctor(capfd)
    (mine,) = [made for made in lines if made.check == CHECK]
    assert (code, mine.result.value) == (3, "unknown")
    assert mine.detail == "docker container inspect's output did not parse: ValidationError"
    assert SENTINEL not in err
    assert not any(SENTINEL in made.model_dump_json() for made in lines)


@pytest.mark.parametrize("exit_code", [137, 125])
def test_a_vanished_container_with_any_exit_but_1_is_unknown(
    exit_code: int, ssh: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    # docker/cli v29.9.2 cli/command/inspect/inspector.go:99-103: a failed lookup exits 1. Any other exit (137: the
    # client was killed) is not that answer, even when stderr names the container as gone.
    answer(ssh, {LIST: listing(GONE), inspect(GONE): found(missing=(GONE,)) | {"code": exit_code}})
    code, result, detail, _, _ = line(capfd)
    assert (code, result) == (3, "unknown")
    assert f"(exit {exit_code})" in detail


@pytest.mark.parametrize("hung", ["list", "inspect"])
def test_a_timeout_is_unknown(
    hung: str, ssh: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PC_DOCTOR_TIMEOUT", "5")  # far above a stand-in call; the hung one sleeps 30 (#749)
    web = found(container(WEB, "web", "example/web:1"))
    script = {LIST: listing(WEB), inspect(WEB): web}
    key = LIST if hung == "list" else inspect(WEB)
    script[key] = script[key] | {"sleep": 30}
    answer(ssh, script)
    code, result, detail, _, _ = line(capfd)
    assert (code, result) == (3, "unknown")
    assert detail.endswith("timed out after 5 s")


@pytest.mark.parametrize("failed", ["list", "inspect"])
def test_an_ssh_failure_is_unknown(failed: str, ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    refused = {"stderr": "ssh: connect to host pc port 22: Connection refused\n", "code": 255}
    script: dict[str, object] = {LIST: listing(WEB), inspect(WEB): found(container(WEB, "web", "example/web:1"))}
    script[LIST if failed == "list" else inspect(WEB)] = refused
    answer(ssh, script)
    code, result, detail, _, _ = line(capfd)
    assert (code, result, detail) == (3, "unknown", "ssh pc failed (exit 255)")


def test_the_daemon_is_named_explicitly(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # An inherited DOCKER_CONTEXT or DOCKER_HOST must not choose the daemon: each docker call names the PC's socket.
    answer(ssh, {LIST: listing()})
    line(capfd)
    calls = [json.loads(call) for call in (ssh / "calls.jsonl").read_text().splitlines()]
    docker = [call for call in calls if "docker" in call]
    assert docker
    assert all(
        call[call.index("docker") :][:3] == ["docker", "--host", "unix:///var/run/docker.sock"] for call in docker
    )


def test_a_hostile_name_and_image_come_out_inert(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    # CODING_STANDARDS 9: name and image come from the PC's daemon; quotes, backslashes and a newline must stay inside
    # one JSON string, so stdout still holds exactly one event per check.
    name, image = 'a"b\\c\nd"},{"check":"forged","result":"pass', 'x\\"y\nz:1'
    hostile = container(JOB, name, image, privileged=True)
    answer(ssh, {LIST: listing(JOB), inspect(JOB): found(hostile)})
    code, lines, _ = doctor(capfd)
    assert (code, [made.check for made in lines].count("forged")) == (1, 0)
    (mine,) = [made for made in lines if made.check == CHECK]
    assert mine.culprits == [f"container:{name} image:{image}"]
