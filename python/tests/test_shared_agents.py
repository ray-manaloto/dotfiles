"""Shared agent rules: exact source blocks and real links in a scratch home."""

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "unix/home/.config/agents/AGENTS.md"
WORKFLOW = REPO / "unix/home/.config/agents/workflow"
SKILLS = REPO / "unix/home/.config/agents/skills"
# Moved to cpp-standard (its #156): the links resolve into its main checkout, at this path below the home.
CPP_STANDARD = "dev/github/ray-manaloto/cpp-standard/unix/home/.config/agents"
MOVED = ("ticket-retro", "session-retro")
STAYED = ("work", "to-spec", "to-tickets", "implement", "implement-spec", "chief-of-staff", "lsp-server", "secrets")
STAYED += ("herdr-startup", "herdr-shutdown")
ENTRIES = (
    "~/.config/agents/AGENTS.md",
    "~/.codex/AGENTS.md",
    "~/.gemini/GEMINI.md",
    "~/.claude/CLAUDE.md/agents",
    "~/.config/agents/workflow",
    "~/.config/agents/skills/LICENSE",
    *(
        f"~/{folder}/{skill}"
        for skill in (*MOVED, *STAYED)
        for folder in (".config/agents/skills", ".claude/skills", ".agents/skills")
    ),
)
CBM_SHA256 = "b91b037c7a0f857cb633c32abd7ab288b5ff3d18431b86e902d635c0e4683485"
CONTEXT7_SHA256 = "9fc34f2cc057e3175d8b49c622d4732745102f0b9ffdefe2ca739d994396f37b"


class SharedAgentsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SHARED.read_text()

    def section(self, heading: str) -> str:
        return self.text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]

    def test_the_installer_blocks_are_verbatim(self) -> None:
        start = self.text.index("<!-- codebase-memory-mcp:start -->")
        end = self.text.index("<!-- codebase-memory-mcp:end -->\n") + len(
            "<!-- codebase-memory-mcp:end -->\n"
        )
        cbm = self.text[start:end]
        snapshot = self.text[self.text.index("<!-- context7 -->") :]
        self.assertEqual(hashlib.sha256(cbm.encode()).hexdigest(), CBM_SHA256)
        self.assertEqual(hashlib.sha256(snapshot.encode()).hexdigest(), CONTEXT7_SHA256)

    def test_the_cross_review_rule_matches_its_workflow_file(self) -> None:
        source = (WORKFLOW / "cross-review.md").read_text()
        rule = source.split("# Cross-review\n\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn(" ".join(rule.splitlines()), self.section("Cross-review"))

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
        # The moved files, as cpp-standard's main checkout holds them: byte-equal copies of this tree's.
        cls.moved = cls.home / CPP_STANDARD
        shutil.copytree(WORKFLOW, cls.moved / "workflow")
        for skill in MOVED:
            shutil.copytree(SKILLS / skill, cls.moved / "skills" / skill)
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
        folder = self.home / ".config/agents/skills"
        self.assertFalse(folder.is_symlink())
        self.assertEqual((folder / "LICENSE").resolve(), SKILLS / "LICENSE")
        self.assertEqual((self.home / ".config/agents/workflow").resolve(), self.moved / "workflow")
        for skill in (*MOVED, *STAYED):
            source = self.moved / "skills" / skill if skill in MOVED else SKILLS / skill
            for path in (folder / skill, *(self.home / scope / "skills" / skill for scope in (".claude", ".agents"))):
                with self.subTest(path=path):
                    self.assertTrue(path.is_symlink())
                    self.assertEqual(path.resolve(), source)

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
