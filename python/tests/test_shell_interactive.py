"""Keys typed into a real zsh in a real terminal, for what `zsh -c` cannot reach."""

# The terminal is tmux, as in zsh-users/zsh-autosuggestions spec/terminal_session.rb.
import fcntl
import os
import re
import shlex
import shutil
import socket as unix
import subprocess
import tempfile
import time
import tomllib
import unittest
from collections.abc import Callable
from pathlib import Path

from test_shell_startup import STARTUP_FILES, UNIX_HOME

FILES = (*STARTUP_FILES, ".config/starship.toml")
FOLDERS = ("other", "Upper", "src2", "srcdir", "work")
GLYPH = "❯"
STARSHIP_CONFIG = tomllib.loads((UNIX_HOME / ".config/starship.toml").read_text())
# The right prompt's width follows the tracked format; a directive other than these fails the wait.
CLOCK_FORMAT = re.escape(STARSHIP_CONFIG["time"]["time_format"])
CLOCK = re.compile(r"\s{2,}" + re.sub("%[HM]", r"\\d\\d", CLOCK_FORMAT) + "$")
TMUX = shutil.which("tmux")
STARSHIP = shutil.which("starship")
# Each test's folder holds its HOME and its tmux socket, so removing the folder removes both.
# /tmp, not TMPDIR: a socket's path must fit sockaddr_un's 104 bytes on macOS.
TEMP_ROOT = Path("/tmp")
PREFIX = "dotfiles-test-"
# In each test's folder: the pids of the shells it launched, written as soon as tmux prints them.
SHELLS = "shells"


def labeled_root() -> Path | None:
    """Where tmux puts its -L sockets; these tests used -L before, and each run left one there.

    tmux.c make_label expands TMUX_SOCK, "$TMUX_TMPDIR:/tmp" (tmux.h), and takes the first entry
    realpath resolves: expand_path skips an unset variable, and realpath fails on "" or on a
    folder that doesn't exist. The sockets sit in tmux-<uid> under it.
    """
    for candidate in (os.environ.get("TMUX_TMPDIR"), "/tmp"):
        if candidate and Path(candidate).exists():
            return Path(candidate).resolve() / f"tmux-{os.getuid()}"
    return None


def alive(pid: int) -> bool:
    status = ["ps", "-p", str(pid)]
    return subprocess.run(status, capture_output=True, timeout=10, check=False).returncode == 0


def at(socket: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # -f /dev/null: a personal base-index would otherwise break the session's pane target.
    command = [str(TMUX), "-f", "/dev/null", "-u", "-S", str(socket), *args]
    return subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)


def panes(socket: Path) -> list[int] | None:
    """The pane pids of the server on socket; None when no server answers there."""
    if not socket.exists():
        return None  # no server ever bound it
    listed = at(socket, "list-panes", "-a", "-F", "#{pane_pid}")
    if listed.returncode != 0:
        if listed.stderr.startswith("no server running on "):
            return None  # client.c: ECONNREFUSED, a socket whose server has exited
        raise RuntimeError(f"tmux list-panes on {socket}: {listed.stderr}")
    return [int(pid) for pid in listed.stdout.split()]


def end(socket: Path, shells: list[int]) -> None:
    """Stop the server on socket, then wait for shells and its panes to exit.

    A server that no longer answers proves nothing about its shells, so the known pids are
    waited for too. tmux never removes its socket (server.c unlinks only before it binds).
    """
    pids = list(shells)
    if (answering := panes(socket)) is not None:
        killed = at(socket, "kill-server")
        if killed.returncode != 0:
            raise RuntimeError(f"tmux kill-server on {socket}: {killed.stderr}")
        pids += answering
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and any(alive(pid) for pid in pids):
        time.sleep(0.05)
    if left := [pid for pid in pids if alive(pid)]:
        raise RuntimeError(f"{left} outlived kill-server on {socket}")


def owned_by_a_live_run(name: str) -> bool:
    """dotfiles-test-<pid>-...: a run still going keeps its folders; a reused pid only delays."""
    pid = name.removeprefix(PREFIX).split("-", 1)[0]
    return pid.isdigit() and alive(int(pid))


def record(folder: Path, shells: list[int]) -> None:
    """Write the shell pids whole or not at all: an interrupted write leaves only the partial."""
    partial = folder / f"{SHELLS}.partial"
    partial.write_text("".join(f"{pid}\n" for pid in shells))
    partial.replace(folder / SHELLS)


def launched(folder: Path) -> list[int] | None:
    """The shell pids a test folder recorded; None when it recorded none."""
    recorded = folder / SHELLS
    pids = recorded.read_text().split() if recorded.exists() else []
    return [int(pid) for pid in pids] or None


def abandoned(folder: Path) -> bool:
    """Whether nothing can still use folder: its run, its server and its shells are all gone.

    A folder whose socket exists but whose shells were never recorded launched a server with an
    unknown outcome, so it stays.
    """
    if owned_by_a_live_run(folder.name) or panes(folder / "tmux") is not None:
        return False
    shells = launched(folder)
    if shells is None:
        return not (folder / "tmux").exists()
    return not any(alive(pid) for pid in shells)


def sweep(root: Path) -> None:
    """Remove the test folders in root that nothing can still use."""
    for folder in root.glob(f"{PREFIX}*"):
        if abandoned(folder):
            shutil.rmtree(folder)


def setUpModule() -> None:
    """Clear what earlier runs left: a killed run, or a second Ctrl-C, skips its cleanups.

    Another run's things go only once its process, its server and its shells are gone: this never
    stops a server or a shell, so it can't end a run, even one this pid check misjudges.
    """
    # One sweep at a time, so two runs never remove the same leftovers; a run removes only its
    # own folders otherwise. The lock file stays, and its name doesn't match PREFIX*.
    with (TEMP_ROOT / "dotfiles-tests.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        sweep(TEMP_ROOT)
        if (labeled := labeled_root()) is not None:
            for socket in labeled.glob(f"{PREFIX}*"):
                if not owned_by_a_live_run(socket.name) and panes(socket) is None:
                    socket.unlink()


class InteractiveShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(TMUX, "tmux must be on PATH")
        self.assertIsNotNone(STARSHIP, "starship must be on PATH")
        prefix = f"{PREFIX}{os.getpid()}-"
        folder = Path(tempfile.mkdtemp(prefix=prefix, dir=TEMP_ROOT)).resolve()
        self.socket = folder / "tmux"
        self.shells: list[int] | None = None  # the pane's pid, once tmux has printed it
        self.addCleanup(self.finish, folder)
        home = folder / "home"
        home.mkdir()
        for name in FILES:
            (home / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(UNIX_HOME / name, home / name)
        for name in FOLDERS:
            (home / name).mkdir()
        path = f"{Path(str(STARSHIP)).parent}:/usr/bin:/bin:/usr/sbin:/sbin"
        # C.UTF-8 orders the completion list by byte, whatever locales this machine has.
        variables = (
            f"HOME={home}",
            "TERM=xterm-256color",
            "LC_ALL=C.UTF-8",
            f"PATH={path}",
        )
        command = shlex.join(("env", "-i", *variables, "/bin/zsh", "-i"))  # tmux runs it with sh -c
        size = ("-x", "100", "-y", "30")
        # -P prints the pid with the session, so a shell that dies at once can't lose it.
        printed = ("-dP", "-F", "#{pane_pid}")
        made = self.tmux("new-session", *printed, "-s", "t", *size, "-c", str(home), command)
        self.shells = [int(made)]
        record(folder, self.shells)
        # The prompt alone doesn't show zle is reading keys; its echo of them does.
        self.type("ready")
        self.wait_for_line("ready")
        self.keys("C-u")
        self.wait_for_line("")

    def finish(self, folder: Path) -> None:
        """Remove the folder only once its shell is known gone: zsh writes its history on exit.

        A folder kept here is removed by a later run's sweep, once this run has ended.
        """
        end(self.socket, self.shells or [])  # raises, keeping the folder, while a shell lives
        if self.shells is None and self.socket.exists():
            self.fail(f"tmux started but never printed the shell's pid; kept {folder}")
        shutil.rmtree(folder)

    def tmux(self, *args: str) -> str:
        done = at(self.socket, *args)
        if done.returncode != 0:
            self.fail(f"tmux {args[0]} failed, so the shell may be gone: {done.stderr}")
        return done.stdout

    def keys(self, *names: str) -> None:
        self.tmux("send-keys", "-t", "t", *names)

    def type(self, text: str) -> None:
        self.tmux("send-keys", "-t", "t", "-l", "--", text)

    def run_line(self, text: str) -> None:
        self.type(text)
        self.keys("Enter")

    def screen(self) -> str:
        return self.tmux("capture-pane", "-p", "-t", "t")

    def prompt(self) -> tuple[list[str], int] | None:
        """The screen and the live prompt's row; zsh keeps the cursor on the prompt it edits.

        None while no prompt is under the cursor, or while the screen changes around reading the
        cursor, when the row could point into a different screen.
        """
        before = self.screen()
        row = int(self.tmux("display-message", "-p", "-t", "t", "#{cursor_y}"))
        if self.screen() != before:
            return None
        lines = before.splitlines()
        text = lines[row] if row < len(lines) else ""
        return (lines, row) if text == GLYPH or text.startswith(f"{GLYPH} ") else None

    def line(self) -> str | None:
        """What is typed at the live prompt, without the clock on the right."""
        found = self.prompt()
        if found is None:
            return None
        lines, row = found
        return CLOCK.sub("", lines[row]).removeprefix(GLYPH).strip()

    def folder(self) -> str | None:
        """The prompt's path, the first word of the line above the live prompt."""
        found = self.prompt()
        if found is None:
            return None
        lines, row = found
        above = lines[row - 1].split() if row else []
        return above[0] if above else None

    def listed(self) -> list[str] | None:
        """The words of the completion list under the live prompt."""
        found = self.prompt()
        if found is None:
            return None
        lines, row = found
        return " ".join(lines[row + 1 :]).split()

    def wait(self, ready: Callable[[], bool]) -> None:
        end = time.monotonic() + 10
        while time.monotonic() < end:
            if ready():
                return
            time.sleep(0.05)
        self.fail(f"timed out; the screen was:\n{self.screen()}")

    def wait_for_line(self, text: str) -> None:
        self.wait(lambda: self.line() == text)

    def test_a_folder_name_alone_enters_it(self) -> None:
        self.run_line("work")
        self.wait(lambda: self.folder() == "~/work")
        self.run_line("..")
        self.wait(lambda: self.folder() == "~")

    def test_tab_ignores_case_both_ways(self) -> None:
        self.type("ls OTH")
        self.keys("Tab")
        self.wait_for_line("ls other/")
        self.keys("C-u")
        self.wait_for_line("")
        self.type("ls upp")
        self.keys("Tab")
        self.wait_for_line("ls Upper/")

    def test_tab_fills_then_lists_then_selects(self) -> None:
        self.type("ls sr")
        self.keys("Tab")
        self.wait_for_line("ls src")
        self.keys("Tab")
        self.wait(lambda: self.listed() == ["src2/", "srcdir/"])
        self.keys("Tab")
        self.wait_for_line("ls src2/")
        self.keys("Tab")
        self.wait_for_line("ls srcdir/")

    def test_up_finds_only_commands_with_the_typed_prefix(self) -> None:
        self.run_line("echo alpha")
        self.wait_for_line("")
        self.run_line("echo beta")
        self.wait_for_line("")
        self.run_line("echo apricot")
        self.wait_for_line("")
        self.run_line("true")
        self.wait_for_line("")
        self.type("echo a")
        self.keys("Up")
        self.wait_for_line("echo apricot")
        self.keys("Up")
        self.wait_for_line("echo alpha")


class SweepTest(unittest.TestCase):
    """sweep() on a folder a dead run left, in a root of its own that no other run sweeps."""

    def setUp(self) -> None:
        # Not PREFIX*, so another run's setUpModule never sees this root or what it holds.
        self.root = Path(tempfile.mkdtemp(prefix="dotfiles-sweep-", dir=TEMP_ROOT)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        ended = subprocess.Popen(["true"])
        ended.wait()
        self.folder = self.root / f"{PREFIX}{ended.pid}-left"
        self.folder.mkdir()

    def bind(self) -> None:
        with unix.socket(unix.AF_UNIX) as bound:
            bound.bind(str(self.folder / "tmux"))  # a server that bound its socket, then died

    def test_keeps_a_folder_while_its_shell_lives(self) -> None:
        shell = subprocess.Popen(["sleep", "60"])
        self.addCleanup(shell.wait)
        self.addCleanup(shell.kill)
        record(self.folder, [shell.pid])
        sweep(self.root)
        self.assertTrue(self.folder.exists())
        shell.kill()
        shell.wait()
        sweep(self.root)
        self.assertFalse(self.folder.exists())

    def test_keeps_a_folder_whose_launch_never_recorded_a_shell(self) -> None:
        self.bind()
        sweep(self.root)
        self.assertTrue(self.folder.exists())

    def test_keeps_a_folder_whose_record_is_empty(self) -> None:
        self.bind()
        (self.folder / SHELLS).write_text("")
        sweep(self.root)
        self.assertTrue(self.folder.exists())

    def test_removes_a_folder_that_never_launched(self) -> None:
        sweep(self.root)
        self.assertFalse(self.folder.exists())


if __name__ == "__main__":
    unittest.main()
