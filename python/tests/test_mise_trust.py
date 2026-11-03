"""mise trust: real mise in a temporary HOME with the tracked trust settings."""

# The global config's trust keys (`paranoid`, `trusted_config_paths`) and miserc.toml's
# `ignored_config_paths` are copied into a minimal global config, so `~` in them points inside the
# temporary HOME and no tool from the real config is installed.

import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MISE_DIR = REPO / "unix/home/.config/mise"
MISE = Path(shutil.which("mise") or "mise").resolve()
SETTINGS = tomllib.loads((MISE_DIR / "config.toml").read_text())["settings"]
IGNORED = tomllib.loads((MISE_DIR / "miserc.toml").read_text())["ignored_config_paths"]

OWN = "dev/github/ray-manaloto/project"
CLONE = "dev/github/stranger/tool"  # an owner folder the ignore list does not name
THIRD_PARTY = "dev/github/jdx/mise"
MIRROR = "dev/github/ray-manaloto/claude-code-marketplace/offline/jdx-mise"
LEGACY = "dev/github/ray-manaloto/dotfiles-legacy"
LEGACY_WORKTREE = ".codex/worktrees/ab12/dotfiles"


class MiseTrustTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.home)
        config = self.home / ".config/mise"
        config.mkdir(parents=True)
        (config / "config.toml").write_text(
            "[settings]\n"
            f"paranoid = {SETTINGS['paranoid']!r}\n"
            f"trusted_config_paths = {SETTINGS['trusted_config_paths']!r}\n".replace(
                "'", '"'
            )
        )
        shutil.copyfile(MISE_DIR / "miserc.toml", config / "miserc.toml")

    def project(self, rel: str, *, git: bool = True) -> tuple[Path, str]:
        """A folder with a mise.toml whose env var and task are named after it."""
        folder = self.home / rel
        folder.mkdir(parents=True)
        name = "P_" + "".join(c if c.isalnum() else "_" for c in rel).upper()
        (folder / "mise.toml").write_text(
            f'[env]\n{name} = "loaded"\n[tasks.{name.lower()}]\nrun = "echo ran"\n'
        )
        if git:
            for command in (
                ["git", "init", "-q"],
                ["git", "add", "mise.toml"],
                [
                    "git",
                    "-c",
                    "user.name=t",
                    "-c",
                    "user.email=t@t",
                    "commit",
                    "-qm",
                    "t",
                ],
            ):
                # HK=0: the user's global git hooks run `mise x hk`, which the
                # untrusted config under test would refuse.
                subprocess.run(
                    command,
                    cwd=folder,
                    env=os.environ | {"HK": "0"},
                    check=True,
                    capture_output=True,
                )
        return folder, name

    def mise(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("MISE_", "XDG_")) and key not in ("CI", "PWD")
        }
        env |= {
            "HOME": str(self.home),
            "MISE_CEILING_PATHS": str(self.home),
            "MISE_AUTO_INSTALL": "0",
            "MISE_CACHE_DIR": str(self.home / ".cache/mise"),
        }
        return subprocess.run(
            [MISE, *args],
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def loads(self, folder: Path, name: str) -> bool:
        """Whether mise loads the folder's own config: its env var and task are both there."""
        env = self.mise(folder, "exec", "--", "printenv", name)
        task = self.mise(folder, "run", name.lower())
        self.assertEqual(env.returncode, task.returncode, (env.stderr, task.stderr))
        return env.returncode == 0 and env.stdout == "loaded\n"

    def test_an_own_repo_loads_and_keeps_loading_after_an_edit(self) -> None:
        folder, name = self.project(OWN)
        self.assertTrue(self.loads(folder, name))
        (folder / "mise.toml").write_text((folder / "mise.toml").read_text() + "\n")
        self.assertTrue(self.loads(folder, name))

    def test_a_worktree_of_an_own_repo_beside_it_loads(self) -> None:
        folder, name = self.project(OWN)
        worktree = folder.parent / "project.worktrees/branch"
        subprocess.run(
            ["git", "worktree", "add", "-q", str(worktree)],
            cwd=folder,
            check=True,
            capture_output=True,
        )
        self.assertTrue(self.loads(worktree, name))

    def test_a_fresh_clone_is_not_trusted_by_install_run_or_exec(self) -> None:
        folder, name = self.project(CLONE)
        for args in (["install"], ["run", name.lower()], ["exec", "--", "true"]):
            with self.subTest(args=args):
                done = self.mise(folder, *args)
                self.assertEqual(done.returncode, 1, done.stdout)
                self.assertIn("not trusted", done.stderr)
        trust = self.mise(folder, "trust", "--show")
        self.assertTrue(trust.stdout.rstrip().endswith(": untrusted"), trust.stdout)

    def test_an_approved_clone_needs_approval_again_after_an_edit(self) -> None:
        folder, name = self.project(CLONE)
        self.assertEqual(self.mise(folder, "trust").returncode, 0)
        self.assertTrue(self.loads(folder, name))
        (folder / "mise.toml").write_text((folder / "mise.toml").read_text() + "\n")
        self.assertEqual(self.mise(folder, "run", name.lower()).returncode, 1)

    def test_reading_trees_never_load_and_global_tools_still_run(self) -> None:
        for rel in (THIRD_PARTY, MIRROR, LEGACY, LEGACY_WORKTREE):
            with self.subTest(rel=rel):
                folder, name = self.project(rel, git=False)
                self.assertFalse(self.loads(folder, name))
                done = self.mise(folder, "exec", "--", "true")
                self.assertEqual(done.returncode, 0, done.stderr)

    def test_every_ignored_entry_is_absolute_or_under_home(self) -> None:
        for entry in IGNORED:
            with self.subTest(entry=entry):
                self.assertTrue(entry.startswith(("~/", "/")), entry)


if __name__ == "__main__":
    unittest.main()
