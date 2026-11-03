"""Herdr.app setup: the global post-tools hook and the hc-codex blocks, run in a scratch home."""

# Both run through tasks/scratch/env.sh, so every home path is inside a temporary folder. The hook
# runs with the real `skills` CLI; herdr-core is already in the scratch home, so its install is
# skipped and nothing is downloaded.

import json
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((REPO / "unix/home/.config/mise/config.toml").read_text())
POST_TOOLS = CONFIG["bootstrap"]["hooks"]["post-tools"]["run"]
# mise runs each hook command with its default inline shell, unix_default_inline_shell_args
# (mise v2026.10.25 crates/mise-system/src/hooks.rs:180-247).
SHELL = ("sh", "-o", "errexit", "-c")
BLOCKS = ("~/.claude/CLAUDE.md/hc-codex", "~/.codex/AGENTS.md/hc-codex")

# What `skills add herdrdev/herdr` installed in September, as the skills lock records it.
OLD = ("herdr", "herdr-pre-release-audit", "herdr-throwaway-repro", "triage")
OLD_LOCK_ONLY = "writing-commit-messages"
CORE = {".agents/skills/herdr-core", ".claude/skills/herdr-core"}


class HerdrAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.home = self.root / "home"
        # skills keeps its lock under $XDG_STATE_HOME, which env.sh sets.
        self.lock = self.root / "state/skills/.skill-lock.json"
        self.skills: dict[str, dict[str, str]] = {}
        self.install(
            "herdr-core", "herdrdev/herdr-core", ".agents/skills", ".claude/skills"
        )

    def install(self, name: str, source: str, *folders: str) -> None:
        """A skill as `skills add -g` leaves it: a folder per agent and a lock entry."""
        for folder in folders:
            skill = self.home / folder / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {source}\n---\n"
            )
        self.skills[name] = {
            "source": source,
            "sourceType": "github",
            "sourceUrl": f"https://github.com/{source}.git",
            "skillPath": f"skills/{name}/SKILL.md",
            "skillFolderHash": "0" * 40,
            "installedAt": "2026-09-21T19:08:07Z",
            "updatedAt": "2026-09-21T19:09:41Z",
        }
        self.lock.parent.mkdir(parents=True, exist_ok=True)
        self.lock.write_text(json.dumps({"version": 3, "skills": self.skills}))

    def scratch(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "tasks/scratch/env.sh", str(self.root), *argv],
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def post_tools(self) -> None:
        for command in POST_TOOLS:
            done = self.scratch(*SHELL, command)
            self.assertEqual(done.returncode, 0, (command, done.stdout, done.stderr))

    def on_disk(self) -> set[str]:
        return {
            str(path.parent.relative_to(self.home))
            for path in self.home.glob(".*/skills/*/SKILL.md")
        }

    def locked(self) -> set[str]:
        return set(json.loads(self.lock.read_text())["skills"])

    def test_post_tools_removes_every_skill_from_herdrs_repo(self) -> None:
        for name in OLD:
            self.install(name, "herdrdev/herdr", ".agents/skills", ".claude/skills")
        self.install(OLD_LOCK_ONLY, "herdrdev/herdr")
        self.install("keep-me", "someone/else", ".agents/skills")
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE | {".agents/skills/keep-me"})
        self.assertEqual(self.locked(), {"herdr-core", "keep-me"})

    def test_a_herdr_folder_with_no_lock_entry_is_removed_too(self) -> None:
        self.install("herdr", "herdrdev/herdr", ".claude/skills")
        del self.skills["herdr"]
        self.lock.write_text(json.dumps({"version": 3, "skills": self.skills}))
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE)

    def test_post_tools_is_safe_to_repeat_with_nothing_to_remove(self) -> None:
        self.post_tools()
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE)
        self.assertEqual(self.locked(), {"herdr-core"})

    def test_claude_and_codex_open_watched_agents_as_tabs(self) -> None:
        done = self.scratch("mise", "dot", "apply", *BLOCKS)
        self.assertEqual(done.returncode, 0, done.stderr)
        claude = (self.home / ".claude/CLAUDE.md").read_text()
        codex = (self.home / ".codex/AGENTS.md").read_text()
        self.assertEqual(claude, codex)
        self.assertIn("herdr-app do tab.new --space ", claude)
        self.assertIn('--argv \'["codex-hc"', claude)
        self.assertIn("If `herdr-app ls` fails, stop and ask the user", claude)
        self.assertNotIn("hc run --bg", claude)


if __name__ == "__main__":
    unittest.main()
