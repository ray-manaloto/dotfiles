"""shell:apply and shell:rollback: real mise and zsh, a repo copy, a temporary HOME."""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UNIX_HOME = REPO / "unix/home"
IGNORE = shutil.ignore_patterns(".git", ".venv", "node_modules", "build", "__pycache__")
MISE = Path(shutil.which("mise") or "mise").resolve()

STARTUP = (".zshenv", ".zprofile", ".zshrc")
DROP_INS = (".zshrc.d/10-zsh.zsh", ".zshrc.d/90-mise.zsh")
DEPLOYED = (*STARTUP, *DROP_INS, ".config/zsh/path.zsh")
BACKED_UP = (*STARTUP, ".zprofile.d", ".zshrc.d")
RETIRED = (".zprofile.d/macos-dev-env.zsh", ".zshrc.d/50-mde-secrets.zsh")
AGENT_TOOLS = ".zshrc.d/60-agent-tools.zsh"
HISTORY = b": 1:0;echo before\n"
GROWN = HISTORY + b": 2:0;echo after\n"
WRITER = ("/bin/sh", "-c", "while :; do echo '# installer' >> .zshrc; done")


def snapshot(home: Path) -> dict[str, tuple[int, bytes]]:
    """Mode and bytes of each file under the backed-up paths; a link holds its target."""
    tops = [home / name for name in BACKED_UP]
    paths = tops + [path for top in tops for path in top.rglob("*")]
    return {
        str(path.relative_to(home)): (0, os.fsencode(path.readlink()))
        if path.is_symlink()
        else (stat.S_IMODE(path.stat().st_mode), path.read_bytes())
        for path in paths
        if path.is_symlink() or path.is_file()
    }


class ShellApplyTest(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root)
        self.home, self.repo = root / "home", root / "repo"
        self.state, self.cache = root / "state", root / "cache"
        self.history = self.state / "zsh/history"
        # From the checkout mise climbs to the real ~/.config/mise as a project config.
        shutil.copytree(REPO, self.repo, ignore=IGNORE)
        self.env = {
            "HOME": str(self.home),
            "USER": os.environ["USER"],  # the root mise.toml renders env.USER
            "PATH": f"{MISE.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
            "XDG_STATE_HOME": str(self.state),
            "XDG_CACHE_HOME": str(self.cache),
            "MISE_TRUSTED_CONFIG_PATHS": str(self.repo),
        }
        for name in (*STARTUP, *RETIRED):
            (self.home / name).parent.mkdir(parents=True, exist_ok=True)
            (self.home / name).write_text(f"# live {name}\n")
        # A link into a checkout on this Mac; apply has no reason to repoint it.
        (self.home / AGENT_TOOLS).symlink_to(UNIX_HOME / AGENT_TOOLS)
        (self.home / ".zsh_history").write_bytes(HISTORY)
        (self.home / ".zsh_history").chmod(0o600)

    def spawn(self, *argv: str | Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            env=self.env,
            cwd=self.repo,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def run_ok(self, name: str) -> None:
        done = self.spawn(MISE, "run", name)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def assert_refused(self, live: dict[str, tuple[int, bytes]]) -> None:
        """A non-zero exit and no change; `.zshrc` may have grown, never been replaced."""
        self.assertNotEqual(self.spawn(MISE, "run", "shell:apply").returncode, 0)
        now = snapshot(self.home)
        self.assertTrue(now[".zshrc"][1].startswith(live[".zshrc"][1]))
        self.assertEqual({**now, ".zshrc": live[".zshrc"]}, live)
        self.assertFalse((self.home / ".config/zsh/path.zsh").exists())
        self.assertFalse(self.history.exists())
        self.assertFalse((self.cache / "zsh/completions/_mise").exists())

    def test_apply_backs_up_the_live_files_first_in_a_private_folder(self) -> None:
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        backups = self.state / "dotfiles/shell-backup"
        folders = list(backups.glob("[0-9]" * 8 + "T" + "[0-9]" * 6 + "*"))
        self.assertEqual(len(folders), 1)
        self.assertEqual(snapshot(folders[0]), live)
        for folder in (backups, folders[0]):
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)

    def test_apply_links_the_six_files_and_removes_the_retired_drop_ins(self) -> None:
        self.run_ok("shell:apply")
        for name in DEPLOYED:
            self.assertTrue((self.home / name).is_symlink(), name)
            # Into the checkout that ran the task, which here is the copy.
            resolved = (self.home / name).resolve()
            self.assertEqual(resolved, self.repo / "unix/home" / name, name)
        # Six entries, never a linked folder: the drop-ins beside them stay put.
        self.assertFalse((self.home / ".zshrc.d").is_symlink())
        for name in RETIRED:
            self.assertFalse((self.home / name).exists())
        self.assertEqual((self.home / AGENT_TOOLS).readlink(), UNIX_HOME / AGENT_TOOLS)

    def test_history_is_copied_once_and_never_overwritten(self) -> None:
        self.run_ok("shell:apply")
        self.assertEqual(self.history.read_bytes(), HISTORY)
        self.assertEqual(stat.S_IMODE(self.history.stat().st_mode), 0o600)
        self.assertEqual((self.home / ".zsh_history").read_bytes(), HISTORY)
        # An old shell can still write the live file; it must not win over the copy.
        self.history.write_bytes(GROWN)
        (self.home / ".zsh_history").write_bytes(GROWN + GROWN)
        self.run_ok("shell:apply")
        self.assertEqual(self.history.read_bytes(), GROWN)

    def test_apply_puts_the_mise_completion_on_fpath(self) -> None:
        self.run_ok("shell:apply")
        folder = self.cache / "zsh/completions"
        self.assertTrue((folder / "_mise").is_file())
        shell = self.spawn("/bin/zsh", "-i", "-c", "print -rl -- $fpath $_comps[mise]")
        self.assertEqual(shell.returncode, 0, shell.stderr)
        lines = shell.stdout.splitlines()
        self.assertIn(str(folder), lines)
        # compinit read it: fpath was set in time, so Tab completes mise.
        self.assertEqual(lines[-1], "_mise")

    def test_rollback_restores_the_backup_and_leaves_the_history(self) -> None:
        # This Mac has no ~/.zshenv, so a rollback also takes the deployed one away.
        (self.home / ".zshenv").unlink()
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        # A repeat must not bury the only backup of what the first apply removed.
        self.run_ok("shell:apply")
        self.history.write_bytes(GROWN)
        self.run_ok("shell:rollback")
        self.assertEqual(snapshot(self.home), live)
        self.assertEqual(self.history.read_bytes(), GROWN)

    def test_apply_refuses_and_changes_nothing(self) -> None:
        drop_in = self.repo / "unix/home/.zshrc.d/90-mise.zsh"
        good = drop_in.read_bytes()
        live = snapshot(self.home)
        # Valid zsh that ends the shell, so only starting one finds it.
        drop_in.write_bytes(good + b"exit 7\n")
        self.assert_refused(live)
        drop_in.write_bytes(good)
        # A real second writer: any record of .zshrc goes stale before apply can act.
        writer = subprocess.Popen(WRITER, env=self.env, cwd=self.home)
        try:
            self.assert_refused(live)
        finally:
            writer.kill()
            writer.wait()
        # A missing task refuses too; with both causes gone this one must apply.
        self.run_ok("shell:apply")


if __name__ == "__main__":
    unittest.main()
