"""agents:update: real mise runs the global file task in a temporary HOME."""

# curl and the four agent CLIs are stand-ins (networked tools), so no agent CLI on the host is
# used and nothing is downloaded.

import contextlib
import errno
import json
import os
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "unix/home/.config/mise/tasks/agents/update"
MISE = Path(shutil.which("mise") or "mise").resolve()
PYTHON = f"#!{sys.executable} -I"

# Where each native installer puts its command.
NATIVE = {
    "https://claude.ai/install.sh": ".local/bin/claude",
    "https://chatgpt.com/codex/install.sh": ".local/bin/codex",
    "https://antigravity.google/cli/install.sh": ".local/bin/agy",
    "https://opencode.ai/v2/install": ".opencode/bin/opencode",
}
CLAUDE, CODEX, AGY, OPENCODE = NATIVE.values()
INSTALLS = [
    "install https://claude.ai/install.sh",
    "install https://chatgpt.com/codex/install.sh CODEX_NON_INTERACTIVE=1",
    "install https://antigravity.google/cli/install.sh",
    "install https://opencode.ai/v2/install --no-modify-path",
]
UPDATES = ["claude update", "codex update", "agy update", "opencode update"]
# Seconds each call may take in these tests, so a stalled stand-in ends quickly.
TIMEOUT = 3
PROMPT = "continue? [y/N] "

# `curl -fsSL -o FILE URL` writes an installer that records its URL, arguments and the
# codex prompt switch, then puts the CLI at its native path. The installer is shell because
# the task runs each vendor installer with the shell it is written for.
# A URL listed in HOME/stall-install stalls its installer on a child that would write HOME/late
# after the time limit, as a slow download inside a vendor installer would; HOME/stalling marks
# that the stall began.
INSTALLER = r"""if grep -qxF '@URL@' "$HOME/stall-install"; then
  touch "$HOME/stalling"
  (sleep $((AGENTS_UPDATE_TIMEOUT + 2)); touch "$HOME/late") &
  wait
fi
printf '%s\n' "install @URL@${*:+ $*}${CODEX_NON_INTERACTIVE:+ CODEX_NON_INTERACTIVE=$CODEX_NON_INTERACTIVE}" >> "$HOME/calls"
mkdir -p "$HOME/@DIR@" && cp "$HOME/tool" "$HOME/@BIN@"
rm -f "$HOME/@BIN@.version"
"""
# Any other arguments are refused, so the task must pass curl its time limit. A URL listed in
# HOME/stall gets no bytes, as on a dead connection, and ends as curl does at --max-time.
CURL = f"""{PYTHON}
import sys
import time
from pathlib import Path
NATIVE = {NATIVE!r}
INSTALLER = {INSTALLER!r}
args = sys.argv[1:]
if args[:4] != ["-fsSL", "--max-time", "{TIMEOUT}", "-o"] or len(args) != 6 or args[5] not in NATIVE:
    sys.exit(2)
url, binary = args[5], NATIVE[args[5]]
stall = Path.home() / "stall"
if stall.exists() and url in stall.read_text().split():
    time.sleep(int(args[2]))
    print(f"curl: (28) Operation timed out after {{args[2]}}000 milliseconds with 0 bytes received", file=sys.stderr)
    sys.exit(28)
script = INSTALLER.replace("@URL@", url).replace("@BIN@", binary)
Path(args[4]).write_text(script.replace("@DIR@", str(Path(binary).parent)))
"""
# A native CLI: `update` is recorded, fails when BINARY.version holds `fail`, stalls when it
# holds `stall`, and asks the terminal to continue when it holds `ask`, as an updater's
# prompt would; `--version` prints BINARY.version (OpenCode 1 prints a bare `1.19.0`), else
# `NAME v2.2.5`; anything else is refused.
TOOL = f"""{PYTHON}
import sys
import time
from pathlib import Path
me = Path(sys.argv[0])
version = Path(str(me) + ".version")
if sys.argv[1:] == ["update"]:
    note = ""
    if version.exists() and version.read_text() == "fail":
        sys.exit(1)
    if version.exists() and version.read_text() == "stall":
        time.sleep(60)
    if version.exists() and version.read_text() == "ask":
        with open("/dev/tty", "w") as out, open("/dev/tty") as tty:
            out.write("{PROMPT}")
            out.flush()
            note = " answered " + tty.readline().strip()
    with open(Path.home() / "calls", "a") as calls:
        calls.write(me.name + " update" + note + "\\n")
elif sys.argv[1:] == ["--version"]:
    if version.exists() and version.read_text() == "stall":
        time.sleep(60)
    print(version.read_text().strip() if version.exists() else me.name + " v2.2.5")
else:
    sys.exit(2)
"""


class AgentsUpdateTest(unittest.TestCase):
    def run_task(
        self,
        installed: tuple[str, ...],
        runs: int = 1,
        versions: dict[str, str] | None = None,
        stalled_downloads: tuple[str, ...] = (),
        stalled_installers: tuple[str, ...] = (),
        answer: str | None = None,
        interrupt: bool = False,
    ) -> tuple[int, list[str], str]:
        """`mise run agents:update` from a fresh HOME, `runs` times; rc, recorded calls, stderr.
        With `answer`, it runs in a terminal and `answer` is typed at each prompt. With
        `interrupt`, SIGINT goes to the run's process group once an installer stalls."""
        self.assertTrue(TASK.is_file(), f"missing {TASK.relative_to(REPO)}")
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            task = home / ".config/mise/tasks/agents/update"
            task.parent.mkdir(parents=True)
            shutil.copy2(TASK, task)
            stubs = home / "stubs"
            stubs.mkdir()
            (stubs / "curl").write_text(CURL)
            (stubs / "curl").chmod(0o755)
            (home / "tool").write_text(TOOL)
            (home / "tool").chmod(0o755)
            for binary in installed:
                tool = home / binary
                tool.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(home / "tool", tool)
            for binary, version in (versions or {}).items():
                (home / f"{binary}.version").write_text(version)
            (home / "stall").write_text(" ".join(stalled_downloads))
            (home / "stall-install").write_text(
                "".join(f"{u}\n" for u in stalled_installers)
            )
            for _ in range(runs):
                if interrupt:
                    done = self.mise_interrupted(home, stubs)
                elif answer is None:
                    done = self.mise(home, stubs)
                else:
                    done = self.mise_in_terminal(home, stubs, answer)
                if done.returncode:
                    break
            if stalled_installers:
                # The child writes HOME/late TIMEOUT + 2 seconds after the stall began, which
                # was before the run ended, so a surviving child has written it by now.
                time.sleep(TIMEOUT + 3)
                self.assertFalse(
                    (home / "late").exists(), "an installer child outlived the timeout"
                )
            calls = home / "calls"
            lines = calls.read_text().splitlines() if calls.exists() else []
            return done.returncode, lines, done.stderr

    def mise(self, home: Path, stubs: Path) -> subprocess.CompletedProcess[str]:
        """One `mise run agents:update` from an unrelated folder, with HOME, XDG and PATH
        inside the temporary HOME, so only the global task folder can provide the task."""
        return subprocess.run(
            [MISE, "run", "agents:update"],
            env=self.environment(home, stubs),
            cwd=self.elsewhere(home),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def mise_interrupted(
        self, home: Path, stubs: Path
    ) -> subprocess.CompletedProcess[str]:
        """The same run with no terminal, sent SIGINT once an installer stalls, as `kill -INT`
        on the run's group would be; the installer's own group gets no signal."""
        with subprocess.Popen(
            [MISE, "run", "agents:update"],
            env=self.environment(home, stubs),
            cwd=self.elsewhere(home),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        ) as process:
            end = time.monotonic() + 30
            while not (home / "stalling").exists():
                if time.monotonic() > end or process.poll() is not None:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    self.fail("no installer stalled")
                time.sleep(0.05)
            os.killpg(process.pid, signal.SIGINT)
            out, err = process.communicate(timeout=60)
        return subprocess.CompletedProcess(MISE, process.returncode, out, err)

    def mise_in_terminal(
        self, home: Path, stubs: Path, answer: str
    ) -> subprocess.CompletedProcess[str]:
        """The same run with a pseudo-terminal as its controlling terminal, as when the user
        types it; `answer` is typed at each prompt. Its output is returned as stderr."""
        pid, terminal = pty.fork()
        if pid == 0:  # the child: its own session, with the terminal in the foreground
            os.chdir(self.elsewhere(home))
            os.execve(
                MISE, [MISE, "run", "agents:update"], self.environment(home, stubs)
            )
        seen, answered, end = b"", 0, time.monotonic() + 60
        while True:
            if time.monotonic() > end:
                # pty.fork made the child a session and group leader: end it all, then fail.
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(pid, signal.SIGKILL)
                os.close(terminal)
                os.waitpid(pid, 0)
                self.fail(f"agents:update still running after 60 s: {seen!r}")
            ready, _, _ = select.select([terminal], [], [], 1)
            try:
                chunk = os.read(terminal, 4096) if ready else b""
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                break  # every process holding the terminal has exited
            if ready and not chunk:
                break
            seen += chunk
            if seen.count(PROMPT.encode()) > answered:
                os.write(terminal, f"{answer}\n".encode())
                answered += 1
        os.close(terminal)
        code = os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1])
        return subprocess.CompletedProcess(
            MISE, code, "", seen.decode(errors="replace")
        )

    @staticmethod
    def elsewhere(home: Path) -> Path:
        """An unrelated folder, so only the global task folder can provide the task."""
        folder = home / "elsewhere"
        folder.mkdir(exist_ok=True)
        return folder

    @staticmethod
    def environment(home: Path, stubs: Path) -> dict[str, str]:
        """HOME, XDG and PATH inside the temporary HOME."""
        return {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "MISE_CEILING_PATHS": str(home),
            "MISE_AUTO_INSTALL": "0",
            "AGENTS_UPDATE_TIMEOUT": str(TIMEOUT),
            "TERM": "dumb",
            # The task's python3 is this test's interpreter, never a host one.
            "PATH": f"{stubs}:{Path(sys.executable).parent}:/usr/bin:/bin",
        }

    def test_installed_tools_update_themselves(self) -> None:
        code, calls, err = self.run_task(tuple(NATIVE.values()))
        self.assertEqual((code, calls), (0, UPDATES), err)

    def test_a_fresh_mac_gets_each_native_installer_once(self) -> None:
        code, calls, err = self.run_task(())
        self.assertEqual((code, calls), (0, INSTALLS), err)

    def test_a_second_run_only_updates(self) -> None:
        code, calls, err = self.run_task((), runs=2)
        self.assertEqual((code, calls), (0, INSTALLS + UPDATES), err)

    def test_a_mixed_mac_updates_some_and_installs_the_rest(self) -> None:
        code, calls, err = self.run_task((CLAUDE, OPENCODE))
        self.assertEqual(
            (code, calls), (0, [UPDATES[0], INSTALLS[1], INSTALLS[2], UPDATES[3]]), err
        )

    def test_opencode_1_is_replaced_by_the_v2_installer(self) -> None:
        # OpenCode 1's own updater stays on major version 1.
        code, calls, err = self.run_task(
            tuple(NATIVE.values()), runs=2, versions={OPENCODE: "1.19.0"}
        )
        self.assertEqual((code, calls), (0, UPDATES[:3] + INSTALLS[3:] + UPDATES), err)

    def test_one_failing_update_does_not_stop_the_others(self) -> None:
        # `fail` makes the stand-in claude refuse `update`; the rest still run, the task
        # reports claude as one JSON event and exits 1.
        code, calls, err = self.run_task(
            tuple(NATIVE.values()), versions={CLAUDE: "fail"}
        )
        self.assertEqual((code, calls), (1, UPDATES[1:]), err)
        events = [json.loads(line) for line in err.splitlines() if line.startswith("{")]
        self.assertEqual(
            [(event["event"], event["agent"]) for event in events],
            [("agent_failed", "claude")],
        )

    def test_a_stalled_update_times_out_and_the_others_still_run(self) -> None:
        code, calls, err = self.run_task(
            tuple(NATIVE.values()), versions={CLAUDE: "stall"}
        )
        self.assertEqual((code, calls), (1, UPDATES[1:]), err)
        [event] = self.failures(err)
        self.assertEqual(event["agent"], "claude")
        self.assertIn(f"timed out after {TIMEOUT} seconds", event["error"])

    def test_a_stalled_download_fails_at_its_time_limit_and_the_others_install(
        self,
    ) -> None:
        code, calls, err = self.run_task(
            (), stalled_downloads=("https://chatgpt.com/codex/install.sh",)
        )
        self.assertEqual((code, calls), (1, INSTALLS[:1] + INSTALLS[2:]), err)
        self.assertEqual([event["agent"] for event in self.failures(err)], ["codex"])

    def test_an_updater_prompt_can_be_answered_from_the_terminal(self) -> None:
        # The run goes on past its time limit only if the answer reached the prompt.
        code, calls, out = self.run_task(
            tuple(NATIVE.values()), versions={CLAUDE: "ask"}, answer="y"
        )
        self.assertEqual(
            (code, calls), (0, ["claude update answered y", *UPDATES[1:]]), out
        )

    def test_ctrl_c_at_a_prompt_cancels_the_whole_run(self) -> None:
        # Ctrl-C reaches only the updater holding the terminal; no later CLI may change.
        code, calls, out = self.run_task(
            tuple(NATIVE.values()), versions={CLAUDE: "ask"}, answer="\x03"
        )
        self.assertEqual((code, calls), (128 + signal.SIGINT, []), out)
        self.assertEqual(
            self.events(out), [{"event": "agents_update_cancelled", "agent": "claude"}]
        )

    def test_in_a_terminal_a_stalled_update_times_out_and_the_others_still_run(
        self,
    ) -> None:
        # codex asks after claude is killed: its prompt is answered only if the task took
        # the terminal back and handed it on.
        code, calls, out = self.run_task(
            tuple(NATIVE.values()), versions={CLAUDE: "stall", CODEX: "ask"}, answer="y"
        )
        self.assertEqual(
            (code, calls), (1, ["codex update answered y", *UPDATES[2:]]), out
        )
        self.assertIn(f"timed out after {TIMEOUT} seconds", out)

    def test_a_stalled_installer_is_stopped_with_its_children(self) -> None:
        code, calls, err = self.run_task(
            (), stalled_installers=("https://antigravity.google/cli/install.sh",)
        )
        self.assertEqual((code, calls), (1, INSTALLS[:2] + INSTALLS[3:]), err)
        [event] = self.failures(err)
        self.assertEqual(event["agent"], "agy")
        self.assertIn(f"timed out after {TIMEOUT} seconds", event["error"])

    def test_an_interrupt_stops_a_stalled_installer_with_its_children(self) -> None:
        # The installer runs in its own group, so only the task gets the signal; run_task
        # then checks that the installer's child never wrote HOME/late.
        code, calls, err = self.run_task(
            (),
            stalled_installers=("https://antigravity.google/cli/install.sh",),
            interrupt=True,
        )
        self.assertEqual((code, calls), (128 + signal.SIGINT, INSTALLS[:2]), err)
        self.assertEqual(
            self.events(err), [{"event": "agents_update_cancelled", "agent": "agy"}]
        )

    def test_a_stalled_version_check_times_out(self) -> None:
        code, calls, err = self.run_task(
            tuple(NATIVE.values()), versions={OPENCODE: "stall"}
        )
        self.assertEqual((code, calls), (1, UPDATES[:3]), err)
        [event] = self.failures(err)
        self.assertEqual(event["agent"], "opencode")
        self.assertIn(f"timed out after {TIMEOUT} seconds", event["error"])

    @staticmethod
    def events(err: str) -> list[dict[str, str]]:
        """The JSON events on stderr; a terminal ends each line with a carriage return."""
        lines = (line.strip() for line in err.splitlines())
        return [json.loads(line) for line in lines if line.startswith("{")]

    def failures(self, err: str) -> list[dict[str, str]]:
        """The `agent_failed` events on stderr."""
        return [event for event in self.events(err) if event["event"] == "agent_failed"]


if __name__ == "__main__":
    unittest.main()
