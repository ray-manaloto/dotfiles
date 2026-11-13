"""shell:apply and shell:rollback: real mise and zsh, a repo copy, a temporary HOME."""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from checkout import copy_checkout

REPO = Path(__file__).resolve().parents[2]
UNIX_HOME = REPO / "unix/home"
MISE = Path(shutil.which("mise") or "mise").resolve()
UV = Path(shutil.which("uv") or "uv").resolve()
# The tasks run repotools through uv run; the scratch HOME has no uv cache or Python of its own, so the
# copy's venv is built from this machine's cache, downloading what it lacks, with the interpreter
# running these tests.
UV_CACHE = subprocess.run([UV, "cache", "dir"], capture_output=True, check=True, text=True).stdout.strip()

# zsh reads all but .zshenv from ZDOTDIR=~/.config/zsh; the live ~/.zprofile and ~/.zshrc are the old layout.
LEGACY = (".zprofile", ".zshrc")
STARTUP = (".zshenv", ".config/zsh/.zprofile", ".config/zsh/.zshrc")
DROP_INS = (".config/zsh/.zshrc.d/10-zsh.zsh", ".config/zsh/.zshrc.d/90-mise.zsh")
DEPLOYED = (*STARTUP, *DROP_INS, ".config/zsh/path.zsh")
BACKED_UP = (".zshenv", *LEGACY, ".zprofile.d", ".zshrc.d", ".config/zsh")
AGENT_TOOLS = ".config/zsh/.zshrc.d/60-agent-tools.zsh"
HISTORY = b": 1:0;echo before\n"
GROWN = HISTORY + b": 2:0;echo after\n"
WRITER = ("/bin/sh", "-c", "while :; do echo '# installer' >> .zshrc; done")
# The record mise 2026.11.3 keeps of each task run, written by the outer mise after the task ends: one
# JSON file per task and its lock, under a folder per project (src/task/task_history.rs:175-194, 344-401).
TASK_HISTORY = re.compile(r"state/mise/task-history/[0-9a-f]{16}/[0-9a-f]{16}\.(json|lock)")
# What a cold scratch:env run may write outside its folder (owner's ruling on #390): the config links
# mise keeps (src/config/tracking.rs:22-27), its trust and monorepo markers (config_file/mod.rs:1298-1319),
# its one-time marker migration (toolset/install_state.rs:1419), its task history, and the bytecode of a
# first import.
COLD_WRITES = re.compile(
    r"state/mise/(tracked-configs/.+|trusted-configs/.+|incomplete-installs/\.migrated)|repo/.*/__pycache__/.+"
    rf"|{TASK_HISTORY.pattern}"
)
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


def written(root: Path, folder: Path) -> dict[str, tuple[int, int]]:
    """The time and size of every entry under root but outside folder; a folder's time also moves when a file
    is made and removed in it. The shared uv cache sits outside root."""
    return {
        str(path.relative_to(root)): (path.lstat().st_mtime_ns, path.lstat().st_size)
        for path in root.rglob("*")
        if not path.is_relative_to(folder)
    }


def assert_only(test: unittest.TestCase, before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]],
                allowed: re.Pattern[str]) -> None:
    """Every entry that changed matches allowed, or is a folder holding one that does."""
    changed = [name for name in after if before.get(name) != after[name]]
    matched = [name for name in changed if allowed.fullmatch(name)]
    for name in changed:
        test.assertTrue(name in matched or any(file.startswith(f"{name}/") for file in matched), name)


def scratch_runs(state: Path) -> list[str]:
    """The status of each scratch:env run in mise's task history, oldest first."""
    (record,) = (state / "mise/task-history").glob("*/*.json")
    runs = json.loads(record.read_text())["runs"]
    return [run["status"] for run in runs if run["task"] == "//:scratch:env"]


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
        copy_checkout(self.repo)
        self.env = {
            "HOME": str(self.home),
            "USER": os.environ["USER"],  # the root mise.toml renders env.USER
            "PATH": f"{MISE.parent}:{UV.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
            "UV_CACHE_DIR": UV_CACHE,
            "UV_PYTHON": str(Path(sys.executable).resolve()),
            "UV_PYTHON_DOWNLOADS": "never",
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_STATE_HOME": str(self.state),
            "XDG_CACHE_HOME": str(self.cache),
            "MISE_TRUSTED_CONFIG_PATHS": str(self.repo),
            "MISE_CEILING_PATHS": str(root),
            "MISE_AUTO_INSTALL": "0",
            # Task history is on in the global config; pinned here so the scratch config can't drop it.
            "MISE_TASK_HISTORY": "1",
            "MISE_TASK_HISTORY_LIMIT": "20",
        }
        for name in (".zshenv", *LEGACY):
            (self.home / name).parent.mkdir(parents=True, exist_ok=True)
            (self.home / name).write_text(f"# live {name}\n")
        # A link into a checkout on this Mac; apply has no reason to repoint it.
        (self.home / AGENT_TOOLS).parent.mkdir(parents=True)
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
        (self.home / ".config/zsh/.zshrc").unlink()
        (self.home / ".config/zsh/.zshrc").write_text("# installer\n")
        self.run_ok("shell:apply")
        self.assertEqual(snapshot(self.pre_apply), live)

    def test_a_later_apply_keeps_a_changed_live_file_aside(self) -> None:
        self.run_ok("shell:apply")
        (self.home / ".config/zsh/.zshrc").unlink()
        (self.home / ".config/zsh/.zshrc").write_text("# live\n# installer\n")
        self.run_ok("shell:apply")
        replaced = list(self.backups.glob("replaced-*"))
        self.assertEqual(len(replaced), 1)
        self.assertEqual((replaced[0] / ".config/zsh/.zshrc").read_text(), "# live\n# installer\n")

    def test_a_failed_backup_leaves_no_pre_apply_and_rollback_refuses(self) -> None:
        unreadable = self.home / ".config/zsh/.zshrc.d/70-unreadable.zsh"
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

    def test_apply_links_the_seven_files(self) -> None:
        self.run_ok("shell:apply")
        for name in DEPLOYED:
            self.assertTrue((self.home / name).is_symlink(), name)
            # Into the checkout that ran the task, which here is the copy.
            resolved = (self.home / name).resolve()
            self.assertEqual(resolved, self.repo / "unix/home" / name, name)
        # The nested-shell copy of .zshenv is the same tracked file.
        zshenv = self.home / ".config/zsh/.zshenv"
        self.assertEqual(zshenv.resolve(), self.repo / "unix/home/.zshenv")
        # Seven entries, never a linked folder: the drop-ins beside them stay put.
        self.assertFalse((self.home / ".config/zsh/.zshrc.d").is_symlink())
        self.assertEqual((self.home / AGENT_TOOLS).readlink(), UNIX_HOME / AGENT_TOOLS)

    def test_apply_drops_the_old_links_into_the_checkout_and_zsh_ignores_the_home_files(self) -> None:
        # The layout before ZDOTDIR: ~/.zprofile, ~/.zshrc and the drop-ins linked into the checkout.
        for name in LEGACY:
            (self.home / name).unlink()
            (self.home / name).symlink_to(self.repo / "unix/home" / name)
        old = self.home / ".zshrc.d"
        old.mkdir()
        (old / "10-zsh.zsh").symlink_to(self.repo / "unix/home/.zshrc.d/10-zsh.zsh")
        (old / "70-mine.zsh").write_text("# a real drop-in\n")
        self.run_ok("shell:apply")
        for name in LEGACY:
            self.assertFalse((self.home / name).is_symlink(), name)
        # A real file is never deleted; the repo's own link goes.
        self.assertEqual([path.name for path in old.iterdir()], ["70-mine.zsh"])
        # The installer's append lands in a file the login shell does not read.
        with (self.home / ".zprofile").open("a") as profile:
            profile.write('export PATH="$HOME/.installer-only:$PATH"\n')
        shell = self.spawn("/bin/zsh", "-l", "-c", 'print -r -- "$ZDOTDIR" "$PATH"')
        self.assertEqual(shell.returncode, 0, shell.stderr)
        zdotdir, path = shell.stdout.rstrip("\n").split(" ", 1)
        self.assertEqual(zdotdir, str(self.home / ".config/zsh"))
        self.assertNotIn(".installer-only", path)
        self.assertEqual(shell.stderr, "")

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
        (self.home / ".config/zsh").mkdir(parents=True, exist_ok=True)
        (self.home / ".config/zsh/path.zsh").write_text("# live path.zsh\n")
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        self.run_ok("shell:rollback")
        self.assertEqual(snapshot(self.home), live)

    def test_rollback_moves_the_current_files_aside_first(self) -> None:
        live = snapshot(self.home)
        self.run_ok("shell:apply")
        (self.home / ".config/zsh/.zshrc.d/70-later.zsh").write_text("# added after apply\n")
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
        (self.home / ".config/zsh/.zshrc.d/70-later.zsh").write_text("# added after rollback\n")
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
        # A file where the drop-ins need a folder: mise links the files before them, then fails.
        blocker = self.home / ".config/zsh/.zshrc.d"
        shutil.rmtree(blocker)
        blocker.write_text("# live file\n")
        live = snapshot(self.home)
        self.assertNotEqual(self.spawn(MISE, "run", "shell:apply").returncode, 0)
        linked = [name for name in DEPLOYED if (self.home / name).is_symlink()]
        self.assertEqual(linked, list(STARTUP))
        # A shell started now writes the new history, so the old one must already be there.
        self.assertEqual(self.history.read_bytes(), HISTORY)
        blocker.unlink()
        self.run_ok("shell:apply")
        self.run_ok("shell:rollback")
        self.assertEqual(snapshot(self.home), live)

    def test_a_failed_dry_run_stops_the_apply(self) -> None:
        (self.repo / "unix/home/.config/zsh/.zshrc.d/10-zsh.zsh").unlink()
        self.assert_refused(snapshot(self.home))

    def test_a_linked_worktree_refuses(self) -> None:
        (self.repo / ".git").write_text("gitdir: elsewhere\n")
        self.assert_refused(snapshot(self.home))

    def test_scratch_env_keeps_every_home_path_in_its_folder(self) -> None:
        folder = self.home.parent / "scratch"
        done = self.spawn(MISE, "run", "scratch:env", folder, "/usr/bin/env")
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
        # mise's own tool paths go first (owner's ruling on #390), the caller's PATH after them in its order,
        # and uv's copy of the venv is gone.
        self.assertTrue(seen["PATH"].endswith(self.env["PATH"]), seen["PATH"])
        self.assertNotIn("/.venv/", seen["PATH"])
        # raw_args: a --help reaches the command, not mise.
        done = self.spawn(MISE, "run", "scratch:env", folder, "/usr/bin/printf", "%s\\n", "--help")
        self.assertEqual((done.returncode, done.stdout), (0, "--help\n"), done.stderr)

    def test_scratch_env_writes_only_into_its_folder(self) -> None:
        # From a synced python/repo, with no mise state yet: a cold run may leave mise's own state and
        # Python's bytecode in the checkout, a warm one only its next task-history record.
        self.run_ok("//repo:sync")
        root = self.home.parent
        for name in ("config", "data", "state", "cache"):
            shutil.rmtree(root / name, ignore_errors=True)
        folder = root / "scratch"
        before = written(root, folder)
        self.assertEqual(self.spawn(MISE, "run", "scratch:env", folder, "/usr/bin/true").returncode, 0)
        cold = written(root, folder)
        self.assertEqual(set(before) - set(cold), set())
        assert_only(self, before, cold, COLD_WRITES)
        self.assertEqual(scratch_runs(self.state), ["ok"])
        self.assertEqual(self.spawn(MISE, "run", "scratch:env", folder, "/usr/bin/true").returncode, 0)
        warm = written(root, folder)
        self.assertEqual(set(warm), set(cold))
        assert_only(self, cold, warm, TASK_HISTORY)
        self.assertEqual(scratch_runs(self.state), ["ok", "ok"])

    def test_apply_refuses_and_changes_nothing(self) -> None:
        drop_in = self.repo / "unix/home/.config/zsh/.zshrc.d/90-mise.zsh"
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
