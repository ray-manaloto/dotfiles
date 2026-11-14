"""mise:untrack-worktrees drops mise's records of worktree copies of the global config, and nothing else."""

import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((REPO / "unix/home/.config/mise/config.toml").read_text())
RUN = CONFIG["tasks"]["mise:untrack-worktrees"]["run"]
# mise runs a task's run line with its default inline shell (unix_default_inline_shell_args).
SHELL = ("sh", "-o", "errexit", "-c")
COPY = "unix/home/.config/mise/config.toml"


class UntrackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.root)], check=True)
        self.tracked = self.root / "state/tracked-configs"
        self.tracked.mkdir(parents=True)

    def record(self, name: str, target: Path) -> Path:
        """A file at target and a tracked-config record of it, as mise writes one: a symlink named by a hash."""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("[tools]\n")
        link = self.tracked / name
        link.symlink_to(target)
        return link

    def untrack(self, state: Path | None) -> subprocess.CompletedProcess[str]:
        env = {k: v for k, v in os.environ.items() if k != "MISE_STATE_DIR"} | {
            "HOME": str(self.root / "home")
        }
        if state is not None:
            env["MISE_STATE_DIR"] = str(state)
        return subprocess.run(
            [*SHELL, RUN], env=env, capture_output=True, text=True, check=True
        )

    def test_only_worktree_copies_of_the_global_config_are_dropped(self) -> None:
        copy = self.root / "dotfiles.worktrees/feature" / COPY
        dropped = self.record("a1", copy)
        # The main checkout's copy is the global config itself; a worktree's mise.toml is
        # its project config.
        kept = [
            self.record("b2", self.root / "dotfiles" / COPY),
            self.record("c3", self.root / "dotfiles.worktrees/feature/mise.toml"),
            self.record("d4", self.root / "project/mise.toml"),
        ]
        done = self.untrack(self.root / "state")
        self.assertEqual(done.stdout, f"untracked {copy}\n")
        self.assertFalse(dropped.is_symlink())
        self.assertTrue(copy.is_file(), "the file itself stays")
        self.assertTrue(all(link.is_symlink() for link in kept))

    def test_the_default_state_folder_is_under_home(self) -> None:
        self.tracked = self.root / "home/.local/state/mise/tracked-configs"
        self.tracked.mkdir(parents=True)
        dropped = self.record("a1", self.root / "dotfiles.worktrees/x" / COPY)
        self.untrack(None)
        self.assertFalse(dropped.is_symlink())

    def test_a_missing_folder_or_a_plain_file_is_left_alone(self) -> None:
        self.assertEqual(self.untrack(self.root / "nowhere").stdout, "")
        (self.tracked / "not-a-link").write_text("x")
        self.assertEqual(self.untrack(self.root / "state").stdout, "")
        self.assertTrue((self.tracked / "not-a-link").is_file())


if __name__ == "__main__":
    unittest.main()
