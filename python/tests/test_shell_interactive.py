"""Keys typed into a real zsh in a real terminal, for what `zsh -c` cannot reach."""

# The terminal is tmux, as in zsh-users/zsh-autosuggestions spec/terminal_session.rb.
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path

UNIX_HOME = Path(__file__).resolve().parents[2] / "unix/home"
FILES = (
    ".zshenv",
    ".zprofile",
    ".zshrc",
    ".zshrc.d/10-zsh.zsh",
    ".config/zsh/path.zsh",
    ".config/starship.toml",
)
FOLDERS = ("other", "Upper", "src2", "srcdir", "work")
GLYPH = "❯"
CLOCK = re.compile(r"\s{2,}\d\d:\d\d$")
TMUX = shutil.which("tmux")
STARSHIP = shutil.which("starship")


class InteractiveShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(TMUX, "tmux must be on PATH")
        self.assertIsNotNone(STARSHIP, "starship must be on PATH")
        home = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, home)
        for name in FILES:
            (home / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(UNIX_HOME / name, home / name)
        for name in FOLDERS:
            (home / name).mkdir()
        self.socket = f"dotfiles-test-{os.getpid()}-{home.name}"
        path = f"{Path(str(STARSHIP)).parent}:/usr/bin:/bin:/usr/sbin:/sbin"
        command = f"env -i HOME={home} TERM=xterm-256color LANG=en_US.UTF-8 PATH={path} /bin/zsh -i"
        self.addCleanup(self.stop)
        self.tmux("new-session", "-d", "-s", "t", "-x", "100", "-y", "30", "-c", str(home), command)
        self.wait_for_line("")

    def tmux(self, *args: str) -> str:
        # -f /dev/null: a personal base-index would otherwise break the session's pane target.
        done = subprocess.run(
            [str(TMUX), "-f", "/dev/null", "-u", "-L", self.socket, *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return done.stdout

    def stop(self) -> None:
        subprocess.run(
            [str(TMUX), "-L", self.socket, "kill-server"], capture_output=True, check=False
        )

    def keys(self, *names: str) -> None:
        self.tmux("send-keys", "-t", "t", *names)

    def type(self, text: str) -> None:
        self.tmux("send-keys", "-t", "t", "-l", "--", text)

    def run_line(self, text: str) -> None:
        self.type(text)
        self.keys("Enter")

    def screen(self) -> str:
        return self.tmux("capture-pane", "-p", "-t", "t")

    def line(self) -> str | None:
        """What is typed after the last prompt, without the clock on the right."""
        typed = [text for text in self.screen().splitlines() if text.startswith(GLYPH)]
        return CLOCK.sub("", typed[-1]).removeprefix(GLYPH).strip() if typed else None

    def folder(self) -> str | None:
        """The prompt's path, from the line above the last prompt."""
        lines = self.screen().splitlines()
        marks = [index for index, text in enumerate(lines) if text.startswith(GLYPH)]
        return lines[marks[-1] - 1].split()[0] if marks and marks[-1] else None

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
        self.wait(lambda: "src2/" in self.screen() and "srcdir/" in self.screen())
        self.keys("Tab")
        self.wait_for_line("ls src2/")
        self.keys("Tab")
        self.wait_for_line("ls srcdir/")

    def test_up_finds_only_commands_with_the_typed_prefix(self) -> None:
        self.run_line("echo alpha")
        self.wait_for_line("")
        self.run_line("echo beta")
        self.wait_for_line("")
        self.run_line("true")
        self.wait_for_line("")
        self.type("echo a")
        self.keys("Up")
        self.wait_for_line("echo alpha")


if __name__ == "__main__":
    unittest.main()
