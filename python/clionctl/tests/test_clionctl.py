"""clion-ctl against stand-in IDEs that serve a real station socket, launched by the real open -n."""

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import psutil
import pytest

from tests.conftest import bundle, launch, report, written


def free_port() -> int:
    with socket.create_server(("127.0.0.1", 0)) as probe:
        return probe.getsockname()[1]


def test_status_lists_nothing_without_an_ide(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert folder.is_dir()
    assert report(capsys, "status") == (0, [], [])


def test_start_waits_for_the_socket_and_the_mcp_port(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    port = free_port()
    app = bundle(folder, "Stand In", mcp_port=port)
    done = launch(capsys, app, "--project", "/work/project", "--mcp-port", str(port))
    assert done == {"event": "started", "pid": done["pid"], "previous_pid": None, "app": str(app), "ports": [port]}
    assert written(app, "argv", done["pid"]) == ["/work/project"]
    socket_path = str(folder / f"jb.station.ij.{done['pid']}.sock")
    ide = {"pid": done["pid"], "app": str(app), "socket": socket_path, "ports": [port]}
    assert report(capsys, "status") == (0, [ide], [])


def test_status_skips_stale_foreign_and_unopened_sockets(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ended = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, check=True)
    # A dead pid's leftover, launchd's pid (another user's process), this test's own pid (alive, socket not open),
    # and a name that is not a pid.
    for pid in [ended.stdout.decode().strip(), "1", str(psutil.Process().pid), "bad"]:
        (folder / f"jb.station.ij.{pid}.sock").touch()
    assert report(capsys, "status") == (0, [], [])


def test_an_ide_outside_a_bundle_has_no_app(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = "import os, socket, sys, time; s = socket.socket(socket.AF_UNIX); s.bind(sys.argv[1]); s.listen()"
    code += "; print(flush=True); time.sleep(60)"
    with subprocess.Popen([sys.executable, "-c", code, str(folder / "pending")], stdout=subprocess.PIPE) as ide:
        assert ide.stdout
        ide.stdout.readline()
        path = folder / f"jb.station.ij.{ide.pid}.sock"
        (folder / "pending").rename(path)
        # The socket was bound under another name, which is the name the process holds.
        assert report(capsys, "status") == (0, [], [])
        ide.kill()
    code = "import os, socket, sys, time; s = socket.socket(socket.AF_UNIX)"
    code += "; s.bind(f'{sys.argv[1]}/jb.station.ij.{os.getpid()}.sock'); s.listen(); print(flush=True); time.sleep(60)"
    with subprocess.Popen([sys.executable, "-c", code, str(folder)], stdout=subprocess.PIPE) as ide:
        assert ide.stdout
        ide.stdout.readline()
        path = str(folder / f"jb.station.ij.{ide.pid}.sock")
        assert report(capsys, "status") == (0, [{"pid": ide.pid, "app": None, "socket": path, "ports": []}], [])
        ide.kill()


def test_start_refuses_an_app_that_runs(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    app = bundle(folder, "Stand In")
    pid = launch(capsys, app)["pid"]
    detail = f"{app} already runs as pid {pid}"
    failure = {"error": "running", "detail": detail, "pid": pid}
    assert report(capsys, "start", "--app", str(app)) == (1, [], [failure])


@pytest.mark.parametrize("name", ["Plain", "Missing.app"])
def test_start_needs_an_app_bundle(folder: Path, capsys: pytest.CaptureFixture[str], name: str) -> None:
    (folder / "Plain").mkdir()
    path = str(folder / name)
    failure = {"error": "no-app", "detail": f"{path} is not an .app bundle", "pid": None}
    assert report(capsys, "start", "--app", path) == (1, [], [failure])


def test_start_reports_an_open_failure(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (folder / "Empty.app").mkdir()
    code, out, err = report(capsys, "start", "--app", str(folder / "Empty.app"))
    assert (code, out, err[0]["error"]) == (1, [], "no-app")
    assert err[0]["detail"] == "open failed: The application cannot be opened because its executable is missing."


def test_start_gives_up_when_the_mcp_port_never_opens(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    app = bundle(folder, "Stand In")
    port = str(free_port())
    detail = f"{app} did not come up within 2.0s"
    failure = {"error": "not-started", "detail": detail, "pid": None}
    assert report(capsys, "start", "--app", str(app), "--mcp-port", port, "--timeout", "2") == (1, [], [failure])


def test_stop_asks_the_ide_to_quit_and_waits(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    app = bundle(folder, "Stand In")
    pid = launch(capsys, app)["pid"]
    done = {"event": "stopped", "pid": pid, "previous_pid": None, "app": str(app), "ports": []}
    assert report(capsys, "stop") == (0, [done], [])
    assert written(app, "exit", pid) == {"userInitiated": True, "force": False, "restart": False}
    assert not psutil.pid_exists(pid)
    # The socket file stays behind, as the IDE leaves it, and status skips it.
    assert (folder / f"jb.station.ij.{pid}.sock").exists()
    assert report(capsys, "status") == (0, [], [])


def test_stop_never_kills_an_ide_that_waits_on_a_question(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    app = bundle(folder, "Stand In", mode="dialog")
    pid = launch(capsys, app)["pid"]
    code, out, err = report(capsys, "stop", "--timeout", "1")
    assert (code, out, err[0]["error"], err[0]["pid"]) == (1, [], "still-running", pid)
    assert err[0]["detail"].endswith("Nothing was killed.")
    assert psutil.pid_exists(pid)


def test_restart_waits_for_the_new_process_and_its_mcp_port(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    port = free_port()
    app = bundle(folder, "Stand In", mcp_port=port)
    old = launch(capsys, app, "--mcp-port", str(port))["pid"]
    code, out, err = report(capsys, "restart", "--app", str(app), "--mcp-port", str(port), "--timeout", "30")
    assert (code, err) == (0, [])
    assert out == [{"event": "restarted", "pid": out[0]["pid"], "previous_pid": old, "app": str(app), "ports": [port]}]
    assert out[0]["pid"] != old
    assert written(app, "exit", old) == {"userInitiated": True, "force": False, "restart": True}


def test_restart_reports_an_ide_that_waits_on_a_question(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pid = launch(capsys, bundle(folder, "Stand In", mode="dialog"))["pid"]
    code, out, err = report(capsys, "restart", "--pid", str(pid), "--timeout", "1")
    assert (code, out, err[0]["error"], err[0]["pid"]) == (1, [], "still-running", pid)
    assert psutil.pid_exists(pid)


def test_restart_reports_an_ide_that_quit_and_never_came_back(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pid = launch(capsys, bundle(folder, "Stand In", mode="quit"))["pid"]
    detail = f"pid {pid} ended, no new IDE came up within 2.0s"
    failure = {"error": "not-started", "detail": detail, "pid": pid}
    assert report(capsys, "restart", "--timeout", "2") == (1, [], [failure])


@pytest.mark.parametrize(
    ("mode", "answer"), [("missing", "answered 404 no-endpoint"), ("hangup", "RemoteProtocolError")]
)
def test_a_station_that_will_not_exit_is_reported(
    folder: Path, capsys: pytest.CaptureFixture[str], mode: str, answer: str
) -> None:
    pid = launch(capsys, bundle(folder, "Stand In", mode=mode))["pid"]
    code, out, err = report(capsys, "stop")
    assert (code, out, err[0]["error"], err[0]["pid"]) == (1, [], "station", pid)
    assert answer in err[0]["detail"]
    assert psutil.pid_exists(pid)


def test_pid_and_app_pick_one_of_several(folder: Path, capsys: pytest.CaptureFixture[str]) -> None:
    first = bundle(folder, "First")
    second = bundle(folder, "Second")
    one = launch(capsys, first)["pid"]
    two = launch(capsys, second)["pid"]
    code, out, err = report(capsys, "stop")
    assert (code, out, err[0]["error"], err[0]["pid"]) == (1, [], "ambiguous", None)
    assert f"{one} ({first})" in err[0]["detail"]
    assert f"{two} ({second})" in err[0]["detail"]
    assert report(capsys, "stop", "--app", str(second))[1][0]["pid"] == two
    assert report(capsys, "stop", "--pid", str(one))[1][0]["pid"] == one


@pytest.mark.usefixtures("folder")
def test_no_matching_ide_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    failure = {"error": "no-ide", "detail": "no running IDE matches pid 4 app None", "pid": 4}
    assert report(capsys, "stop", "--pid", "4") == (1, [], [failure])


@pytest.mark.parametrize(
    ("argv", "detail"),
    [
        ([], "clion-ctl: the first argument is one of status, start, stop, restart"),
        (["quit"], "clion-ctl: the first argument is one of status, start, stop, restart"),
        (["stop", "--nope"], "unrecognized arguments: --nope"),
        (["stop", "--pid", "0"], "greater than or equal to 1"),
        (["start"], "app"),
    ],
)
def test_bad_arguments_are_a_usage_failure(capsys: pytest.CaptureFixture[str], argv: list[str], detail: str) -> None:
    code, out, err = report(capsys, *argv)
    assert (code, out, err[0]["error"]) == (1, [], "usage")
    assert detail in err[0]["detail"]


def test_the_console_script_reads_the_jvm_temporary_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no override it lists the real IDEs, if any run: every socket is in the per-user folder, not in TMPDIR."""
    monkeypatch.delenv("CLION_CTL_STATION_DIR", raising=False)
    monkeypatch.setenv("TMPDIR", "/nowhere")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/nowhere")
    script = Path(sys.executable).parent / "clion-ctl"
    done = subprocess.run([script, "status"], capture_output=True, check=False, text=True)
    assert (done.returncode, done.stderr) == (0, "")
    expected = os.confstr(65537)  # _CS_DARWIN_USER_TEMP_DIR
    assert all(json.loads(line)["socket"].startswith(expected) for line in done.stdout.splitlines())
