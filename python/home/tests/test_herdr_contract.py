"""The herdr files outside the package: the herdr:doctor launcher, hc-safe and the /verify section, run for real."""

# hc-safe runs for real, with real lsof and sandbox-exec, against a Unix socket a child process of this test
# listens on. Only hc is stood in (CODING_STANDARDS 2): any real hc call could reach this Mac's core or start one.

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

CHECKOUT = Path(__file__).resolve().parents[3]
LAUNCHER = CHECKOUT / "unix/home/.config/mise/tasks/herdr/doctor"
HC_SAFE = CHECKOUT / "unix/home/.local/bin/hc-safe"
VERIFY = CHECKOUT / ".claude/skills/verify/SKILL.md"
STAND_IN = Path(__file__).with_name("stand_in.py")


def test_the_launcher_hands_off_to_hometools_herdr_doctor() -> None:
    # One real run through the package's own python and hometools, read-only, against this Mac: only the report's
    # shape is checked, never a live value (owner, 2026-11-07).
    done = subprocess.run([LAUNCHER], capture_output=True, text=True, check=False)
    (line,) = done.stdout.splitlines()
    report = json.loads(line)
    assert set(report) == {"observation", "checks"}
    assert list(report["checks"]) == ["V1", "V2", "V3", "V4", "V5", "V7", "V10", "V11", "V15"]
    assert set(report["checks"].values()) <= {"pass", "fail", "unknown"}
    assert report["observation"]["unchanged"] is True
    # mise lists the task by its description.
    assert '#MISE description="Check herdr-core and Herdr.app wiring without ever starting a core"' in (
        LAUNCHER.read_text()
    )


def test_the_launcher_takes_no_arguments() -> None:
    done = subprocess.run(
        [sys.executable, "-I", LAUNCHER, "--stage", "pre-move"], capture_output=True, text=True, check=False
    )
    assert (done.returncode, done.stdout) == (2, "")
    assert json.loads(done.stderr) == {"error": "herdr:doctor takes no arguments"}


def launcher_copy(root: Path) -> Path:
    """The launcher in a checkout of its own under root, where python/home has no environment yet."""
    copy = root / "unix/home/.config/mise/tasks/herdr/doctor"
    copy.parent.mkdir(parents=True)
    shutil.copy2(LAUNCHER, copy)
    return copy


def test_the_launcher_says_when_hometools_cannot_start(tmp_path: Path) -> None:
    # An environment whose python can't be run: the one JSON error names it. No uv is involved.
    copy = launcher_copy(tmp_path)
    bin_folder = tmp_path / "python/home/.venv/bin"
    bin_folder.mkdir(parents=True)
    (bin_folder / "hometools").write_text("")
    (bin_folder / "python").write_text("")  # Not executable.
    done = subprocess.run([sys.executable, "-I", copy], capture_output=True, text=True, check=False)
    assert (done.returncode, done.stdout) == (2, "")
    python = tmp_path.resolve() / "python/home/.venv/bin/python"
    want = f"herdr:doctor: hometools could not start ({python}: Permission denied)"
    assert json.loads(done.stderr) == {"error": want}


def test_the_launcher_refuses_without_the_package_environment(tmp_path: Path) -> None:
    # Read-only: no sync. A checkout with no python/home/.venv gets one JSON error naming the task that makes it.
    copy = launcher_copy(tmp_path)
    done = subprocess.run([sys.executable, "-I", copy], capture_output=True, text=True, check=False)
    assert (done.returncode, done.stdout) == (2, "")
    want = f"herdr:doctor: {tmp_path.resolve()}/python/home/.venv has no hometools; run: mise run //home:sync"
    assert json.loads(done.stderr) == {"error": want}


def test_verify_has_the_herdr_section() -> None:
    text = VERIFY.read_text()
    section = text[text.index("## Herdr core") : text.index("## 3. Run and capture")]
    assert "mise run herdr:doctor" in section
    assert "hc-safe <core pid> <socket> -- <hc args>" in section
    assert "SKIP" in section
    # It runs no hc verb of its own: hc appears only inside hc-safe's usage or as something never to run.
    assert "\nhc " not in section
    assert "`hc ls`" not in section


# A stand-in core: a process that listens on a Unix socket until it is killed.
LISTEN = (
    "import socket, sys, time\n"
    "s = socket.socket(socket.AF_UNIX); s.bind(sys.argv[1]); s.listen()\n"
    "print('ready', flush=True); time.sleep(600)\n"
)


class HcSafe:
    """hc-safe run for real, with real lsof and sandbox-exec, against a listening process this test owns. Only hc is
    stood in (tests/stand_in.py), as any real hc call could reach or start a real core."""

    def __init__(self, folder: Path, sock: Path) -> None:
        self.folder, self.sock = folder, sock
        self.answers: dict[str, dict[str, object]] = {}
        self.core = subprocess.Popen([sys.executable, "-c", LISTEN, str(sock)], stdout=subprocess.PIPE)
        assert self.core.stdout is not None
        assert self.core.stdout.readline() == b"ready\n"
        self.hc(["ls", "--json"], stdout='{"terminals": []}\n')

    def hc(self, args: list[str], **answer: object) -> None:
        self.answers[json.dumps(["hc", *args])] = answer

    def program(self, body: str) -> None:
        """hc as a script of its own: sandbox-exec execs it, so it starts no process of its own either."""
        (self.folder / "hc").unlink()
        script = self.folder / "hc"
        # A fixed shebang: python3 from PATH, so no interpreter path is written into the file.
        script.write_text(f"#!/usr/bin/env python3\nimport os, signal, socket, sys, time\n{body}")
        script.chmod(0o755)

    def run(self, *args: str, path: str | None = None, outer: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
        """hc-safe with the hc stand-in first on PATH (or path alone), and no HC_SOCKET of this test's own."""
        (self.folder / "script.json").write_text(json.dumps(self.answers))
        env = {k: v for k, v in os.environ.items() if k != "HC_SOCKET"} | {"STAND_IN": str(self.folder)}
        env["PATH"] = path or f"{self.folder}:{os.environ['PATH']}"
        argv = [*outer, str(HC_SAFE), *args]
        return subprocess.run(argv, capture_output=True, text=True, env=env, check=False)

    def calls(self) -> list[list[str]]:
        log = self.folder / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def close(self) -> None:
        self.core.kill()
        self.core.wait()
        assert self.core.stdout is not None
        self.core.stdout.close()


@pytest.fixture
def hc_safe(tmp_path: Path) -> Iterator[HcSafe]:
    if sys.platform != "darwin":
        pytest.skip("sandbox-exec is macOS")
    (tmp_path / "hc").symlink_to(STAND_IN)
    # Short and resolved: macOS caps a socket path at 104 bytes, and lsof matches the path a socket was bound with.
    short = Path(tempfile.mkdtemp(prefix="hs", dir="/tmp")).resolve()
    safe = HcSafe(tmp_path, short / "core.sock")
    try:
        yield safe
    finally:
        safe.close()
        shutil.rmtree(short)


def test_hc_safe_passes_hc_through_when_the_core_is_unchanged(hc_safe: HcSafe) -> None:
    done = hc_safe.run(str(hc_safe.core.pid), str(hc_safe.sock), "--", "ls", "--json")
    assert (done.returncode, done.stdout, done.stderr) == (0, '{"terminals": []}\n', "")
    assert hc_safe.calls() == [["hc", "ls", "--json"]]


@pytest.mark.parametrize("code", [1, 2])
def test_hc_safe_returns_hc_s_own_code(hc_safe: HcSafe, code: int) -> None:
    hc_safe.hc(["get", "t1"], stderr="error: no such terminal\n", code=code)
    done = hc_safe.run(str(hc_safe.core.pid), str(hc_safe.sock), "--", "get", "t1")
    assert (done.returncode, done.stderr) == (code, "error: no such terminal\n")


@pytest.mark.parametrize(("args", "seen"), [((), "socket"), (("--own-env",), "unset")], ids=["injected", "own"])
def test_hc_safe_sets_hc_socket_unless_own_env(hc_safe: HcSafe, args: tuple[str, ...], seen: str) -> None:
    hc_safe.program("print(os.environ.get('HC_SOCKET', 'unset'))\n")
    done = hc_safe.run(*args, str(hc_safe.core.pid), str(hc_safe.sock), "--", "server", "status", "--json")
    assert (done.returncode, done.stdout) == (0, f"{hc_safe.sock if seen == 'socket' else seen}\n")


def test_hc_runs_where_it_can_start_no_process(hc_safe: HcSafe) -> None:
    # What makes a vanished core fail instead of restarting: inside hc-safe's sandbox, hc can't start a process.
    hc_safe.program("import subprocess\nsys.exit(subprocess.run(['/usr/bin/true'], check=False).returncode)\n")
    done = hc_safe.run(str(hc_safe.core.pid), str(hc_safe.sock), "--", "ls")
    assert done.returncode == 1
    assert "PermissionError" in done.stderr


def test_hc_safe_refuses_when_nothing_listens(hc_safe: HcSafe) -> None:
    gone = hc_safe.sock.with_name("none.sock")
    done = hc_safe.run(str(hc_safe.core.pid), str(gone), "--", "ls", "--json")
    assert (done.returncode, done.stdout) == (80, "")
    assert done.stderr == f"hc-safe: core-gone: {gone}: lsof could not read it, not exactly [{hc_safe.core.pid}]\n"
    assert hc_safe.calls() == []


def test_hc_safe_refuses_another_pid(hc_safe: HcSafe) -> None:
    done = hc_safe.run("1", str(hc_safe.sock), "--", "ls", "--json")
    assert (done.returncode, done.stdout) == (80, "")
    assert done.stderr == f"hc-safe: core-gone: {hc_safe.sock}: pids [{hc_safe.core.pid}], not exactly [1]\n"
    assert hc_safe.calls() == []


def test_hc_safe_refuses_two_listeners(hc_safe: HcSafe) -> None:
    # A second process holding the same socket: this test binds one and a child inherits it.
    sock = hc_safe.sock.with_name("two.sock")
    held = socket.socket(socket.AF_UNIX)
    held.bind(str(sock))
    held.listen()
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"], pass_fds=(held.fileno(),))
    try:
        done = hc_safe.run(str(os.getpid()), str(sock), "--", "ls", "--json")
    finally:
        child.kill()
        child.wait()
        held.close()
    assert done.returncode == 80
    pids = sorted([os.getpid(), child.pid])
    assert done.stderr == f"hc-safe: core-gone: {sock}: pids {pids}, not exactly [{os.getpid()}]\n"
    assert hc_safe.calls() == []


def test_hc_safe_reports_a_core_that_died_during_the_call(hc_safe: HcSafe) -> None:
    # hc ends the core and waits until its socket refuses: the core vanished between the two checks.
    hc_safe.program(
        f"os.kill({hc_safe.core.pid}, signal.SIGKILL)\n"
        "for _ in range(500):\n"
        "    try:\n"
        f"        socket.socket(socket.AF_UNIX).connect({str(hc_safe.sock)!r})\n"
        "    except ConnectionRefusedError:\n"
        "        break\n"
        "    time.sleep(0.01)\n"
        "print('[]')\n"
    )
    done = hc_safe.run(str(hc_safe.core.pid), str(hc_safe.sock), "--", "ls", "--json")
    assert (done.returncode, done.stdout) == (80, "[]\n")
    want = f"hc-safe: core-gone: {hc_safe.sock} after the call: pids [], not exactly [{hc_safe.core.pid}]\n"
    assert done.stderr == want


def test_hc_safe_maps_hc_unavailable_to_core_gone(hc_safe: HcSafe) -> None:
    hc_safe.hc(["ls", "--json"], stderr="cannot start core: Operation not permitted\n", code=5)
    done = hc_safe.run(str(hc_safe.core.pid), str(hc_safe.sock), "--", "ls", "--json")
    assert done.returncode == 80
    assert done.stderr.endswith("hc-safe: core-gone: hc exited 5 (unavailable)\n")


def test_hc_safe_blocks_when_the_sandbox_cannot_apply(hc_safe: HcSafe) -> None:
    # Inside another sandbox, as in a Codex -s read-only shell, sandbox-exec can't apply its own profile.
    outer = ("/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)")
    done = hc_safe.run(str(hc_safe.core.pid), str(hc_safe.sock), "--", "ls", "--json", outer=outer)
    assert (done.returncode, done.stderr) == (82, "sandbox-exec: sandbox_apply: Operation not permitted\n")
    assert hc_safe.calls() == []


def test_hc_safe_blocks_without_sandbox_exec(hc_safe: HcSafe) -> None:
    # /usr/bin, where sandbox-exec is, left off PATH; lsof (/usr/sbin) and python3 stay.
    path = f"{hc_safe.folder}:/usr/sbin:{Path(sys.executable).parent}"
    done = hc_safe.run(str(hc_safe.core.pid), str(hc_safe.sock), "--", "ls", path=path)
    assert done.returncode == 82
    assert done.stderr == "hc-safe: sandbox-exec: No such file or directory\n"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("abc", "s.sock", "--", "ls"), "argument pid: invalid int value: 'abc'"),
        (("1", "s.sock", "ls"), "unrecognized arguments: ls"),
        (("1", "s.sock", "--"), "hc's arguments follow --"),
        (("1", "--", "ls"), "the following arguments are required: socket"),
    ],
)
def test_hc_safe_usage_errors_exit_81_without_a_call(hc_safe: HcSafe, args: tuple[str, ...], message: str) -> None:
    done = hc_safe.run(*args)
    assert (done.returncode, done.stdout) == (81, "")
    assert done.stderr.splitlines()[-1] == f"hc-safe: {message}"
    assert hc_safe.calls() == []


def test_hc_safe_is_on_the_dotfiles_path() -> None:
    # Linked from the root mise.toml, as codex-hc is, so `mise dot apply` puts it on PATH.
    text = (CHECKOUT / "mise.toml").read_text()
    assert '"~/.local/bin/hc-safe" = { source = "unix/home/.local/bin/hc-safe", mode = "symlink" }' in text
