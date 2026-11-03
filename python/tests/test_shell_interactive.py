"""Keys typed into a real zsh in a real terminal, for what `zsh -c` cannot reach."""

# The terminal is tmux, as in zsh-users/zsh-autosuggestions spec/terminal_session.rb.
import os
import re
import shlex
import shutil
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


class InteractiveShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(TMUX, "tmux must be on PATH")
        self.assertIsNotNone(STARSHIP, "starship must be on PATH")
        home = self.home = Path(tempfile.mkdtemp()).resolve()
        self.launched = False
        self.pane_pid: int | None = None
        self.addCleanup(self.stop)
        for name in FILES:
            (home / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(UNIX_HOME / name, home / name)
        for name in FOLDERS:
            (home / name).mkdir()
        self.socket = f"dotfiles-test-{os.getpid()}-{home.name}"
        path = f"{Path(str(STARSHIP)).parent}:/usr/bin:/bin:/usr/sbin:/sbin"
        # C.UTF-8 orders the completion list by byte, whatever locales this machine has.
        variables = (f"HOME={home}", "TERM=xterm-256color", "LC_ALL=C.UTF-8", f"PATH={path}")
        command = shlex.join(("env", "-i", *variables, "/bin/zsh", "-i"))  # tmux runs it with sh -c
        # -P prints these with the session, so a shell that dies at once can't lose them.
        printed = ("-dP", "-F", "#{pane_pid} #{socket_path}")
        size = ("-x", "100", "-y", "30")
        self.launched = True  # from here a server may run, even if the call below fails
        made = self.tmux("new-session", *printed, "-s", "t", *size, "-c", str(home), command)
        pid, socket_path = made.strip().split(maxsplit=1)
        self.pane_pid, self.socket_path = int(pid), Path(socket_path)
        # The prompt alone doesn't show zle is reading keys; its echo of them does.
        self.type("ready")
        self.wait_for_line("ready")
        self.keys("C-u")
        self.wait_for_line("")

    def command(self, *args: str) -> list[str]:
        # -f /dev/null: a personal base-index would otherwise break the session's pane target.
        return [str(TMUX), "-f", "/dev/null", "-u", "-L", self.socket, *args]

    def tmux(self, *args: str) -> str:
        done = subprocess.run(
            self.command(*args), capture_output=True, text=True, timeout=10, check=False
        )
        if done.returncode != 0:
            self.fail(f"tmux {args[0]} failed, so the shell may be gone: {done.stderr}")
        return done.stdout

    def stop(self) -> None:
        """Remove HOME only once zsh is known gone: it writes its history on the way out."""
        if self.launched:
            kill = subprocess.run(
                self.command("kill-server"), capture_output=True, text=True, timeout=10, check=False
            )
            if self.pane_pid is None:
                self.fail(f"the launch's outcome is unknown ({kill.stderr}); kept {self.home}")
            end = time.monotonic() + 10
            while time.monotonic() < end and self.alive(self.pane_pid):
                time.sleep(0.05)
            self.socket_path.unlink(missing_ok=True)  # kill-server leaves it
            if self.alive(self.pane_pid):
                left = f"zsh {self.pane_pid} outlived kill-server ({kill.stderr})"
                self.fail(f"{left}; kept {self.home}")
        shutil.rmtree(self.home)

    @staticmethod
    def alive(pid: int) -> bool:
        status = ["ps", "-p", str(pid)]
        return subprocess.run(status, capture_output=True, timeout=10, check=False).returncode == 0

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


if __name__ == "__main__":
    unittest.main()
