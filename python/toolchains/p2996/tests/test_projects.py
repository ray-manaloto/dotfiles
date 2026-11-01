"""p2996 projects: real git, cmake, ninja and clang++-p2996 over small projects, through the CLI."""

import json
import re
import subprocess
from pathlib import Path

import pytest

from p2996 import cli, config
from p2996.models import Config

from .conftest import Upstream, events, fails

pytestmark = pytest.mark.usefixtures("env")

MANIFEST = config.RESOURCES / "projects.json"

# Asks for no compiler and no flag: ^^ compiles only through the toolchain file. The test target
# would leave a mark if anything ran it, and the program would leave one if it ran.
CMAKE = """\
cmake_minimum_required(VERSION 4.4)
project(toy CXX)
option(TOY_SWITCH "A project option the manifest must pass" OFF)
enable_testing()
add_executable(good good.cpp)
target_compile_definitions(good PRIVATE $<$<BOOL:${TOY_SWITCH}>:TOY_SWITCH>)
add_test(NAME ran COMMAND ${CMAKE_COMMAND} -E touch ${CMAKE_BINARY_DIR}/test-ran)
add_executable(other other.cpp)
"""
GOOD = "constexpr auto type = ^^int;\nint main() {}\n"
OTHER = "int main() {}\n"
BROKEN = '#error "known gap"\nint main() {}\n'
SWITCHED = '#ifndef TOY_SWITCH\n#error "the switch is off"\n#endif\nint main() {}\n'
FILES = {"CMakeLists.txt": CMAKE, "good.cpp": GOOD, "other.cpp": OTHER}


@pytest.fixture(autouse=True)
def shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """A consumer's shell: its CC and CXX are not compilers, so the toolchain file must choose."""
    monkeypatch.setenv("CC", "global-default-cc")
    monkeypatch.setenv("CXX", "global-default-c++")


@pytest.fixture
def project(tmp_path: Path) -> Upstream:
    return Upstream(tmp_path / "project")


def manifest(tmp_path: Path, repo: Upstream, commit: str, **fields: object) -> str:
    entry: dict[str, object] = {
        "name": "toy",
        "remote": repo.url,
        "commit": commit,
        "pin": "the test's own commit",
        "options": [],
        "targets": [],
        "known_failures": [],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"projects": [entry | fields]}))
    return str(path)


def passes(argv: list[str], logs: pytest.CaptureFixture[str]) -> dict:
    """Run the CLI, expect success, and return its one project event."""
    cli.main(argv)
    [event] = [event for event in events(logs)[0] if event["event"] == "project ok"]
    return event


def tree_of(cfg: Config) -> Path:
    return cfg.cache / "projects/toy/build"


def test_a_project_that_compiles_passes(
    env: Config, tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES)
    event = passes(["projects", "--manifest", manifest(tmp_path, project, commit)], logs)
    assert (event["project"], event["commit"], event["known_failures"]) == ("toy", commit, 0)
    assert (tree_of(env) / "good").is_file()


def test_it_compiles_and_runs_nothing(
    env: Config, tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES)
    passes(["projects", "--manifest", manifest(tmp_path, project, commit)], logs)
    assert not (tree_of(env) / "test-ran").exists()


def test_a_known_failure_with_its_reason_passes(
    env: Config, tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES | {"other.cpp": BROKEN})
    known = [{"source": "other.cpp", "reason": "known gap"}]
    event = passes(["projects", "--manifest", manifest(tmp_path, project, commit, known_failures=known)], logs)
    assert event["known_failures"] == 1
    assert (tree_of(env) / "good").is_file()  # A known failure does not stop the rest.


def test_a_new_failure_fails_and_names_the_source(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES | {"other.cpp": BROKEN})
    error = fails(["projects", "--manifest", manifest(tmp_path, project, commit)], logs)
    assert "other.cpp" in error["event"]
    assert "toy" in error["event"]


def test_a_known_failure_that_now_compiles_fails_so_the_record_is_removed(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES)
    known = [{"source": "other.cpp", "reason": "known gap"}]
    error = fails(["projects", "--manifest", manifest(tmp_path, project, commit, known_failures=known)], logs)
    assert "other.cpp" in error["event"]
    assert "compiles" in error["event"]


def test_a_known_failure_for_another_reason_fails(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES | {"other.cpp": BROKEN})
    known = [{"source": "other.cpp", "reason": "a different gap"}]
    error = fails(["projects", "--manifest", manifest(tmp_path, project, commit, known_failures=known)], logs)
    assert "other.cpp" in error["event"]
    assert "a different gap" in error["event"]


def test_a_configure_failure_never_counts_as_a_pass(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES | {"CMakeLists.txt": 'message(FATAL_ERROR "no configure")\n'})
    error = fails(["projects", "--manifest", manifest(tmp_path, project, commit)], logs)
    assert "toy" in error["event"]
    assert not [event for event in events(logs)[0] if event["event"] == "project ok"]


def test_the_manifest_options_reach_configure(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES | {"good.cpp": SWITCHED})
    fails(["projects", "--manifest", manifest(tmp_path, project, commit)], logs)
    options = ["-DTOY_SWITCH=ON"]
    passes(["projects", "--manifest", manifest(tmp_path, project, commit, options=options)], logs)


def test_named_targets_limit_what_is_compiled(
    env: Config, tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES | {"other.cpp": BROKEN})
    passes(["projects", "--manifest", manifest(tmp_path, project, commit, targets=["good"])], logs)
    assert (tree_of(env) / "good").is_file()


def test_a_link_failure_beside_a_known_failure_still_fails(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(
        FILES | {"good.cpp": BROKEN, "other.cpp": "int missing();\nint main() { return missing(); }\n"}
    )
    known = [{"source": "good.cpp", "reason": "known gap"}]
    error = fails(["projects", "--manifest", manifest(tmp_path, project, commit, known_failures=known)], logs)
    assert "other" in error["event"]


def test_a_build_that_stops_before_compiling_fails(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES)
    error = fails(["projects", "--manifest", manifest(tmp_path, project, commit, targets=["missing"])], logs)
    assert "toy" in error["event"]


def test_it_builds_the_pinned_commit_and_follows_the_manifest(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    old = project.commit(FILES)
    new = project.commit({"good.cpp": BROKEN})  # The tip is broken; the pin is not.
    passes(["projects", "--manifest", manifest(tmp_path, project, old)], logs)
    error = fails(["projects", "--manifest", manifest(tmp_path, project, new)], logs)
    assert "good.cpp" in error["event"]
    passes(["projects", "--manifest", manifest(tmp_path, project, old)], logs)


def test_an_unknown_commit_fails(tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]) -> None:
    project.commit(FILES)
    error = fails(["projects", "--manifest", manifest(tmp_path, project, "0" * 40)], logs)
    assert "0" * 40 in json.dumps(error)


def test_every_project_in_the_manifest_runs(
    tmp_path: Path, project: Upstream, logs: pytest.CaptureFixture[str]
) -> None:
    commit = project.commit(FILES)
    path = Path(manifest(tmp_path, project, commit))
    document = json.loads(path.read_text())
    document["projects"].append(document["projects"][0] | {"name": "second"})
    path.write_text(json.dumps(document))
    cli.main(["projects", "--manifest", str(path)])
    assert [event["project"] for event in events(logs)[0] if event["event"] == "project ok"] == ["toy", "second"]


def test_the_task_stays_out_of_verify_and_check() -> None:
    def info(task: str) -> dict:
        done = subprocess.run(
            ["mise", "tasks", "info", f"//p2996:{task}", "--json"],
            cwd=config.PROJECT,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(done.stdout)

    assert "projects" in info("projects")["run"][0]
    for task in ("verify", "check", "test"):
        assert not [name for name in info(task)["depends"] if "projects" in str(name)]


def test_the_shipped_manifest_pins_glaze_and_simdjson_with_their_real_switches() -> None:
    projects = {entry["name"]: entry for entry in json.loads(MANIFEST.read_text())["projects"]}
    assert set(projects) == {"glaze", "simdjson"}
    for entry in projects.values():
        assert re.fullmatch("[0-9a-f]{40}", entry["commit"])
        assert re.match("DL-[0-9]+: ", entry["pin"])
    glaze, simdjson = projects["glaze"], projects["simdjson"]
    assert glaze["remote"] == "https://github.com/stephenberry/glaze.git"
    assert glaze["commit"] == "01efb29f98b9969fe22bd89186e78f083b83eb81"
    assert "-Dglaze_ENABLE_REFLECTION26=ON" in glaze["options"]
    assert simdjson["remote"] == "https://github.com/simdjson/simdjson.git"
    assert simdjson["commit"] == "11184110aa765dfd730d80629d07b6f78cff4a86"
    assert "-DSIMDJSON_STATIC_REFLECTION_MODE=ON" in simdjson["options"]


def test_the_shipped_manifest_records_the_known_results() -> None:
    projects = {entry["name"]: entry for entry in json.loads(MANIFEST.read_text())["projects"]}
    glaze = {failure["source"] for failure in projects["glaze"]["known_failures"]}
    assert len(glaze) == 3
    assert sum("inplace_vector" in source for source in glaze) == 2
    assert sum("http_client_pool_test" in source for source in glaze) == 1
    simdjson = projects["simdjson"]
    assert len(simdjson["targets"]) == 11
    assert len(simdjson["known_failures"]) == 11
    assert all(failure["reason"] for entry in projects.values() for failure in entry["known_failures"])
