"""Shared agent rules: exact source blocks and real links in a scratch home."""

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "unix/home/.config/agents/AGENTS.md"
WORKFLOW = REPO / "unix/home/.config/agents/workflow"
SKILLS = REPO / "unix/home/.config/agents/skills"
ENTRIES = (
    "~/.config/agents/AGENTS.md",
    "~/.codex/AGENTS.md",
    "~/.gemini/GEMINI.md",
    "~/.claude/CLAUDE.md/agents",
    "~/.config/agents/workflow",
    "~/.config/agents/skills",
    "~/.claude/skills/ticket-retro",
    "~/.agents/skills/ticket-retro",
    "~/.claude/skills/work",
    "~/.agents/skills/work",
    "~/.claude/skills/to-spec",
    "~/.agents/skills/to-spec",
    "~/.claude/skills/to-tickets",
    "~/.agents/skills/to-tickets",
    "~/.claude/skills/implement",
    "~/.agents/skills/implement",
    "~/.claude/skills/implement-spec",
    "~/.agents/skills/implement-spec",
)
# Frozen from the live source ranges in #449's brief before writing the shared file.
TABS_SHA256 = "01ac699d9ef173bcb243c4ca126fb3b4ea41e4f317907a18a354503a0b1cc5b9"
# The research rule as #614 rewrote it for fnox proxy run.
RESEARCH_SHA256 = "6b7fe6dd7a6754c24da04a0b5e0236270d9875dc83030e52ef2c37942e1615aa"
PLUGIN_SHA256 = "7f8875a7f1856153b539546c763560543f58826357010e4468a8d694b63c43e8"
CBM_SHA256 = "b91b037c7a0f857cb633c32abd7ab288b5ff3d18431b86e902d635c0e4683485"
CONTEXT7_SHA256 = "9fc34f2cc057e3175d8b49c622d4732745102f0b9ffdefe2ca739d994396f37b"


class SharedAgentsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SHARED.read_text()

    def section(self, heading: str) -> str:
        return self.text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]

    def test_each_rule_is_stated_once(self) -> None:
        self.assertEqual(
            re.findall(r"^## (.+)$", self.text, re.MULTILINE),
            [
                "Watched agents open as herdr-app tabs",
                "Messages between agents",
                "Research evidence across workspaces",
                "Adding a Doppler secret",
                "Plugin changes need the owner's OK",
                "Workflow",
                "Commit and pull-request approval",
                "Cross-review",
                "Large reviews fan out",
                "context7 snapshot",
                "Steps",  # Inside the verbatim context7 snapshot.
            ],
        )
        self.assertEqual(self.text.count("# Agent rules for every repository\n"), 1)
        self.assertEqual(self.text.count("Any agent the user may watch"), 1)
        self.assertEqual(self.text.count("codebase-memory-mcp:start"), 1)
        self.assertEqual(self.text.count("<!-- context7 -->"), 2)

    def test_the_replaced_block_entries_are_gone(self) -> None:
        config = tomllib.loads((REPO / "mise.toml").read_text())
        self.assertFalse(
            [key for key in config["dotfiles"] if key.endswith("/hc-codex")]
        )

    def test_the_installer_blocks_are_verbatim(self) -> None:
        start = self.text.index("<!-- codebase-memory-mcp:start -->")
        end = self.text.index("<!-- codebase-memory-mcp:end -->\n") + len(
            "<!-- codebase-memory-mcp:end -->\n"
        )
        cbm = self.text[start:end]
        snapshot = self.text[self.text.index("<!-- context7 -->") :]
        self.assertEqual(hashlib.sha256(cbm.encode()).hexdigest(), CBM_SHA256)
        self.assertEqual(hashlib.sha256(snapshot.encode()).hexdigest(), CONTEXT7_SHA256)

    def test_the_other_source_rules_are_verbatim(self) -> None:
        tabs = self.section("Watched agents open as herdr-app tabs").splitlines()[1] + "\n"
        research = self.section("Research evidence across workspaces")
        plugin = "## Plugin changes need the owner's OK\n" + self.section(
            "Plugin changes need the owner's OK"
        )
        for text, expected in (
            (tabs, TABS_SHA256),
            (research, RESEARCH_SHA256),
            (plugin, PLUGIN_SHA256),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), expected)

    def test_the_cross_review_rule_names_the_pane_commands(self) -> None:
        source = (WORKFLOW / "cross-review.md").read_text()
        rule = source.split("# Cross-review\n\n", 1)[1].split("\n\n", 1)[0]
        section = self.section("Cross-review")
        self.assertIn(" ".join(rule.splitlines()), section)
        self.assertIn("repotools pane-pin", section)
        self.assertIn("repotools pane-fingerprint", section)

    def test_the_approval_rule_uses_the_installed_commands(self) -> None:
        section = self.section("Commit and pull-request approval")
        for command in (
            "repotools pane-pin --session",
            "repotools pane-fingerprint --message",
            "repotools pr-create --title",
            "repotools pr-fingerprint --title",
            "mise run //repo:tools-install",
        ):
            with self.subTest(command=command):
                self.assertIn(command, section)
        self.assertNotIn("mise run //repo:pane", section)

    def test_no_machine_path_or_five_stage_text(self) -> None:
        for forbidden in ("/Users/", "/home/", "five-stage", "Five-stage"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.text)


class SharedAgentsInstallTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(tempfile.mkdtemp()).resolve()
        cls.addClassCleanup(shutil.rmtree, cls.root)
        cls.home = cls.root / "home"
        done = cls.scratch("mise", "dot", "apply", *ENTRIES)
        if done.returncode != 0:
            raise AssertionError((done.returncode, done.stdout, done.stderr))

    @classmethod
    def scratch(cls, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["mise", "run", "scratch:env", str(cls.root), *argv],
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def test_every_agent_reads_the_one_shared_file(self) -> None:
        for relative in (
            ".config/agents/AGENTS.md",
            ".codex/AGENTS.md",
            ".gemini/GEMINI.md",
        ):
            with self.subTest(relative=relative):
                path = self.home / relative
                self.assertTrue(path.is_symlink())
                self.assertEqual(path.resolve(), SHARED)
        claude = (self.home / ".claude/CLAUDE.md").read_text()
        self.assertEqual(claude.splitlines().count("@~/.config/agents/AGENTS.md"), 1)

    def test_the_advertised_paths_resolve(self) -> None:
        text = SHARED.read_text()
        paths = set(re.findall(r"`(~/.config/agents/[^`]+)`", text))
        # The Workflow section names these relative to its fully qualified index path.
        paths.update(
            f"~/.config/agents/workflow/{name}"
            for name in re.findall(r"`((?:workflow|ship|cross-review|skills)\.md)`", text)
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue((self.home / path.removeprefix("~/")).exists())

    def test_the_skills_folder_resolves(self) -> None:
        self.assertTrue((self.home / ".config/agents/skills/LICENSE").is_file())
        for skill in ("ticket-retro", "work", "to-spec", "to-tickets", "implement", "implement-spec"):
            for scope in (".claude", ".agents"):
                with self.subTest(skill=skill, scope=scope):
                    path = self.home / scope / "skills" / skill
                    self.assertTrue(path.is_symlink())
                    self.assertEqual(path.resolve(), SKILLS / skill)

    def test_each_skill_has_a_loadable_frontmatter(self) -> None:
        for skill in sorted(SKILLS.glob("*/SKILL.md")):
            with self.subTest(skill=skill.parent.name):
                # yq, from the global mise config, is the YAML parser; a malformed block exits 1.
                fields = json.loads(
                    subprocess.run(
                        ["yq", "--front-matter=extract", "-o", "json", ".", str(skill)],
                        check=True,
                        capture_output=True,
                        text=True,
                    ).stdout
                )
                self.assertEqual(fields["name"], skill.parent.name)
                self.assertTrue(fields["description"])


if __name__ == "__main__":
    unittest.main()
