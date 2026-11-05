"""shell:apply and shell:rollback: real mise and zsh, a repo copy, a temporary HOME."""

import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UNIX_HOME = REPO / "unix/home"
IGNORE = shutil.ignore_patterns(".git", ".venv", "node_modules", "build", "__pycache__", ".coverage*")
MISE = Path(shutil.which("mise") or "mise").resolve()

STARTUP = (".zshenv", ".zprofile", ".zshrc")
DROP_INS = (".zshrc.d/10-zsh.zsh", ".zshrc.d/90-mise.zsh")
DEPLOYED = (*STARTUP, *DROP_INS, ".config/zsh/path.zsh")
BACKED_UP = (*STARTUP, ".zprofile.d", ".zshrc.d", ".config/zsh")
AGENT_TOOLS = ".zshrc.d/60-agent-tools.zsh"
HISTORY = b": 1:0;echo before\n"
GROWN = HISTORY + b": 2:0;echo after\n"
WRITER = ("/bin/sh", "-c", "while :; do echo '# installer' >> .zshrc; done")
# /bin/date +%Y%m%dT%H%M%S.%N%z
REPLACED_NAME = re.compile(r"replaced-\d{8}T\d{6}\.\d{9}[+-]\d{4}")


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
        self.backups = self.state / "dotfiles/shell-backup"
        self.pre_apply = self.backups / "pre-apply"
        # From the checkout mise climbs to the real ~/.config/mise as a project config.
        shutil.copytree(REPO, self.repo, ignore=IGNORE)
        self.env = {
            "HOME": str(self.home),
            "USER": os.environ["USER"],  # the root mise.toml renders env.USER
            "PATH": f"{MISE.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_STATE_HOME": str(self.state),
            "XDG_CACHE_HOME": str(self.cache),
            "MISE_TRUSTED_CONFIG_PATHS": str(self.repo),
            "MISE_CEILING_PATHS": str(root),
            "MISE_AUTO_INSTALL": "0",
        }
        for name in STARTUP:
            (self.home / name).parent.mkdir(parents=True, exist_ok=True)
            (self.home / name).write_text(f"# live {name}\n")
        # A link into a checkout on this Mac; apply has no reason to repoint it.
        (self.home / AGENT_TOOLS).parent.mkdir()
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
        self.assertFalse(self.pre_apply.exists())
        # pathlib's * also matches dot names; a dry run refuses before the folder exists.
        self.assertEqual(list(self.backups.glob("*")), [])

    def test_apply_backs_up_the_live_files_first_in_a_private_folder(self) -> None:
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        # The one name left: no timestamped folder, and the temporary name was renamed away.
        self.assertEqual([path.name for path in self.backups.iterdir()], ["pre-apply"])
        self.assertEqual(snapshot(self.pre_apply), live)
        for folder in (self.backups, self.pre_apply):
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)

    def test_a_later_apply_never_overwrites_pre_apply(self) -> None:
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        # An installer replaced a link, so the next apply has real work to do.
        (self.home / ".zshrc").unlink()
        (self.home / ".zshrc").write_text("# installer\n")
        self.run_ok("shell:apply")
        self.assertEqual(snapshot(self.pre_apply), live)

    def test_a_later_apply_keeps_a_changed_live_file_aside(self) -> None:
        self.run_ok("shell:apply")
        (self.home / ".zshrc").unlink()
        (self.home / ".zshrc").write_text("# live\n# installer\n")
        self.run_ok("shell:apply")
        replaced = list(self.backups.glob("replaced-*"))
        self.assertEqual(len(replaced), 1)
        self.assertEqual((replaced[0] / ".zshrc").read_text(), "# live\n# installer\n")

    def test_a_failed_backup_leaves_no_pre_apply_and_rollback_refuses(self) -> None:
        unreadable = self.home / ".zshrc.d/70-unreadable.zsh"
        unreadable.write_text("# live\n")
        unreadable.chmod(0o600)
        live = snapshot(self.home)
        unreadable.chmod(0)
        self.assertNotEqual(self.spawn(MISE, "run", "shell:apply").returncode, 0)
        self.assertFalse(self.pre_apply.exists())
        # pathlib's * also matches dot names, so a leftover temporary folder shows here.
        self.assertEqual(list(self.backups.glob("*")), [])
        rollback = self.spawn(MISE, "run", "shell:rollback")
        self.assertNotEqual(rollback.returncode, 0, rollback.stdout + rollback.stderr)
        unreadable.chmod(0o600)
        self.assertEqual(snapshot(self.home), live)

    def test_apply_links_the_six_files(self) -> None:
        self.run_ok("shell:apply")
        for name in DEPLOYED:
            self.assertTrue((self.home / name).is_symlink(), name)
            # Into the checkout that ran the task, which here is the copy.
            resolved = (self.home / name).resolve()
            self.assertEqual(resolved, self.repo / "unix/home" / name, name)
        # Six entries, never a linked folder: the drop-ins beside them stay put.
        self.assertFalse((self.home / ".zshrc.d").is_symlink())
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

    def test_rollback_restores_a_path_zsh_that_was_there_before(self) -> None:
        (self.home / ".config/zsh").mkdir(parents=True)
        (self.home / ".config/zsh/path.zsh").write_text("# live path.zsh\n")
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        self.run_ok("shell:rollback")
        self.assertEqual(snapshot(self.home), live)

    def test_rollback_moves_the_current_files_aside_first(self) -> None:
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        (self.home / ".zshrc.d/70-later.zsh").write_text("# added after apply\n")
        current = snapshot(self.home)
        self.run_ok("shell:rollback")
        # The live files and the used pre-apply.
        replaced = list(self.backups.glob("replaced-*"))
        self.assertEqual(len(replaced), 2)
        for folder in replaced:
            self.assertTrue(REPLACED_NAME.fullmatch(folder.name), folder.name)
        # Links and the later drop-in alike: nothing the rollback replaced is destroyed.
        self.assertIn(current, [snapshot(folder) for folder in replaced])
        self.assertEqual(snapshot(self.home), live)

    def test_a_completed_rollback_lets_the_next_apply_capture_fresh(self) -> None:
        first = snapshot(self.home)
        self.run_ok("shell:apply")
        self.run_ok("shell:rollback")
        (self.home / ".zshrc").write_text("# live .zshrc\n# edited after rollback\n")
        (self.home / ".zshrc.d/70-later.zsh").write_text("# added after rollback\n")
        edited = snapshot(self.home)
        self.run_ok("shell:apply")
        self.run_ok("shell:rollback")
        self.assertEqual(snapshot(self.home), edited)
        # Each used backup took a replaced-<time> name: not reused, and not lost.
        self.assertFalse(self.pre_apply.exists())
        folders = list(self.backups.iterdir())
        for folder in folders:
            self.assertTrue(REPLACED_NAME.fullmatch(folder.name), folder.name)
        kept = [snapshot(folder) for folder in folders]
        self.assertIn(first, kept)
        self.assertIn(edited, kept)

    def test_a_failed_rollback_keeps_pre_apply_and_can_be_rerun(self) -> None:
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        # A file the restore cannot read stops it partway through the paths.
        saved = self.pre_apply / ".zshrc"
        saved.chmod(0)
        self.assertNotEqual(self.spawn(MISE, "run", "shell:rollback").returncode, 0)
        self.assertTrue(self.pre_apply.is_dir())
        saved.chmod(live[".zshrc"][0])
        self.run_ok("shell:rollback")
        self.assertEqual(snapshot(self.home), live)

    def test_retry_after_a_partial_link_keeps_the_originals_for_rollback(self) -> None:
        # A file where the last link needs a folder: mise links the other five, then fails.
        blocker = self.home / ".config/zsh"
        blocker.parent.mkdir()
        blocker.write_text("# live file\n")
        live = snapshot(self.home)
        self.assertNotEqual(self.spawn(MISE, "run", "shell:apply").returncode, 0)
        linked = [name for name in DEPLOYED if (self.home / name).is_symlink()]
        self.assertEqual(linked, [*STARTUP, *DROP_INS])
        # A shell started now writes the new history, so the old one must already be there.
        self.assertEqual(self.history.read_bytes(), HISTORY)
        blocker.unlink()
        self.run_ok("shell:apply")
        self.run_ok("shell:rollback")
        self.assertEqual(snapshot(self.home), live)

    def test_a_failed_dry_run_stops_the_apply(self) -> None:
        (self.repo / "unix/home/.zshrc.d/10-zsh.zsh").unlink()
        self.assert_refused(snapshot(self.home))

    def test_a_linked_worktree_refuses(self) -> None:
        (self.repo / ".git").write_text("gitdir: elsewhere\n")
        self.assert_refused(snapshot(self.home))

    def test_scratch_env_keeps_every_home_path_in_its_folder(self) -> None:
        folder = self.home.parent / "scratch"
        done = self.spawn("bash", "tasks/scratch/env.sh", folder, "/usr/bin/env")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        seen = dict(line.split("=", 1) for line in done.stdout.splitlines())
        for name in (
            "HOME",
            "TMPDIR",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
            "XDG_CACHE_HOME",
        ):
            self.assertTrue(seen[name].startswith(f"{folder}/"), name)
        self.assertEqual(seen["MISE_AUTO_INSTALL"], "0")

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
