"""Agent skills setup: the global post-tools hook, the linked skills and the hc-codex blocks."""

# All run through `mise run scratch:env`, so every home path is inside a temporary folder. The hook
# runs with the real `skills` CLI, and the scratch home's git config points GitHub at local
# repositories: herdr-core and agent-desktop, each at its tag and installed on every run. The CLI's other HTTP calls (api.github.com: repo privacy, the tree hash for the lock; skills 1.7.5
# dist/cli.mjs:80-87,3955-3967,6006) go through Node's env proxy to a closed local port and fail,
# which skills tolerates, so nothing leaves the machine.

import json
import os
import plistlib
import re
import shutil
import socket
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((REPO / "unix/home/.config/mise/config.toml").read_text())
# The skills hooks only: the last hook, //depmaps:sync, is a Tera template that mise renders before
# the shell sees it, and python/depmaps tests what it runs.
POST_TOOLS = [
    command
    for command in CONFIG["bootstrap"]["hooks"]["post-tools"]["run"]
    if "//depmaps:sync" not in command
]
# mise runs each hook command with its default inline shell, unix_default_inline_shell_args
# (mise v2026.10.25 crates/mise-system/src/hooks.rs:180-247).
SHELL = ("sh", "-o", "errexit", "-c")
[TAG] = re.findall(r"herdrdev/herdr-core#(\S+)", " ".join(POST_TOOLS))
[DESKTOP_TAG] = re.findall(r"vercel-labs/agent-desktop#(\S+)", " ".join(POST_TOOLS))
# The installed hc's version, from the bundle herdr:doctor reads too (hometools.herdr HC_PLIST); hc itself is
# never run. No mise pin carries it: Herdr.app's first run installs herdr-core.
HC_PLIST = Path.home() / ".local/share/herdr-core/current/Contents/Info.plist"
DESKTOP_PIN = CONFIG["tools"]["github:vercel-labs/agent-desktop"]["version"]
DESKTOP = ("agent-desktop", "agent-desktop-macos", "agent-desktop-ffi", "jev-desktop")
# A skill written in this repo, linked for both agents by [dotfiles] in mise.toml.
PERMISSIONS = "macos-agent-permissions"
ENTRIES = (
    "~/.config/agents/AGENTS.md",
    "~/.codex/AGENTS.md",
    "~/.gemini/GEMINI.md",
    "~/.claude/CLAUDE.md/agents",
)

# What `skills add herdrdev/herdr` installed in September, as the skills lock records it.
OLD = ("herdr", "herdr-pre-release-audit", "herdr-throwaway-repro", "triage")
OLD_LOCK_ONLY = "writing-commit-messages"
HC = "herdr-core"
# Each harness's global skills folder, relative to the scratch root, as herdr:doctor checks them (V10).
CLAUDE, CODEX = "home/.claude/skills", "home/.agents/skills"
LINKED = ("home/.gemini/antigravity-cli/skills", "home/.config/opencode/skills")
HARNESSES = (CLAUDE, CODEX, *LINKED)
# What the hook leaves in every scratch home: herdr-core for all four harnesses, and agent-desktop's
# skills for Claude and Codex.
CORE = {f"{folder}/{HC}" for folder in HARNESSES} | {
    f"{folder}/{name}" for folder in (CLAUDE, CODEX) for name in DESKTOP
}


class HerdrAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.home = self.root / "home"
        # skills keeps its lock under $XDG_STATE_HOME, which scratch:env sets.
        self.lock = self.root / "state/skills/.skill-lock.json"
        self.skills: dict[str, dict[str, str]] = {}
        # Bound but never listening, so every connection to it is refused.
        closed = socket.socket()
        self.addCleanup(closed.close)
        closed.bind(("127.0.0.1", 0))
        proxy = f"http://127.0.0.1:{closed.getsockname()[1]}"
        self.offline = (
            "DO_NOT_TRACK=1",  # no install telemetry
            "NODE_USE_ENV_PROXY=1",  # Node's fetch reads HTTP(S)_PROXY only with this
            f"HTTPS_PROXY={proxy}",
            f"HTTP_PROXY={proxy}",
        )
        self.install(HC, "herdrdev/herdr-core", CODEX, CLAUDE)
        self.github("herdrdev/herdr-core", TAG, (HC,))
        self.github("vercel-labs/agent-desktop", DESKTOP_TAG, DESKTOP)

    def install(self, name: str, source: str, *folders: str) -> None:
        """A skill as `skills add -g` leaves it: a folder per agent and a lock entry."""
        for folder in folders:
            skill = self.root / folder / name
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
            ["mise", "run", "scratch:env", str(self.root), *argv],
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def github(self, repo: str, tag: str, skills: tuple[str, ...]) -> None:
        """A GitHub repository at one tag with these skills, served from a local repository."""
        source = self.root / "source" / repo
        for name in skills:
            (source / "skills" / name).mkdir(parents=True)
            (source / "skills" / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: from the tag\n---\n"
            )
        remote = self.root / "remote"
        for command in (
            ["git", "init", "-q"],
            ["git", "add", "."],
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t"],
            ["git", "tag", tag],
            ["git", "clone", "-q", "--bare", ".", str(remote / f"{repo}.git")],
        ):
            # HK=0: the user's global git hooks run `mise x hk`, which has no config here.
            subprocess.run(
                command,
                cwd=source,
                env=os.environ | {"HK": "0"},
                check=True,
                capture_output=True,
            )
        (self.home / ".gitconfig").write_text(
            f'[url "file://{remote}/"]\n\tinsteadOf = https://github.com/\n'
        )

    def post_tools(self) -> None:
        for command in POST_TOOLS:
            done = self.scratch("env", *self.offline, *SHELL, command)
            self.assertEqual(done.returncode, 0, (command, done.stdout, done.stderr))

    def on_disk(self) -> set[str]:
        return {
            str(path.parent.relative_to(self.root))
            for folder in ("home/.*/skills", "home/.*/*/skills")
            for path in self.root.glob(f"{folder}/*/SKILL.md")
        }

    def locked(self) -> set[str]:
        return set(json.loads(self.lock.read_text())["skills"])

    def test_post_tools_removes_every_skill_from_herdrs_repo(self) -> None:
        for name in OLD:
            self.install(name, "herdrdev/herdr", CODEX, CLAUDE)
        self.install(OLD_LOCK_ONLY, "herdrdev/herdr")
        self.install("keep-me", "someone/else", CODEX)
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE | {f"{CODEX}/keep-me"})
        self.assertEqual(self.locked(), {HC, *DESKTOP, "keep-me"})

    def test_a_herdr_folder_with_no_lock_entry_is_removed_too(self) -> None:
        self.install("herdr", "herdrdev/herdr", CLAUDE)
        del self.skills["herdr"]
        self.lock.write_text(json.dumps({"version": 3, "skills": self.skills}))
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE)

    def test_post_tools_is_safe_to_repeat_with_nothing_to_remove(self) -> None:
        self.post_tools()
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE)
        self.assertEqual(self.locked(), {HC, *DESKTOP})

    @unittest.skipUnless(HC_PLIST.is_file(), "no installed herdr-core")
    def test_herdr_core_comes_from_the_installed_hc_tag(self) -> None:
        installed = plistlib.loads(HC_PLIST.read_bytes())["CFBundleShortVersionString"]
        self.assertEqual(TAG, f"v{installed}")

    def test_a_codex_only_herdr_core_reaches_every_harness(self) -> None:
        shutil.rmtree(self.root / CLAUDE / HC)
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE)
        for folder in HARNESSES:
            self.assertIn(
                "from the tag", (self.root / folder / HC / "SKILL.md").read_text()
            )

    def test_antigravity_and_opencode_link_to_the_codex_copy(self) -> None:
        # A stale real copy in one linked folder is replaced by the link too.
        self.install(HC, "herdrdev/herdr-core", LINKED[0])
        self.post_tools()
        for folder in LINKED:
            link = self.root / folder / HC
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (self.root / CODEX / HC).resolve())

    def test_the_link_line_fails_without_the_codex_copy(self) -> None:
        shutil.rmtree(self.root / CODEX / HC)
        [line] = [command for command in POST_TOOLS if "ln -s" in command]
        done = self.scratch("env", *self.offline, *SHELL, line)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("herdr-core is missing", done.stderr)
        for folder in LINKED:
            self.assertFalse((self.root / folder / HC).is_symlink())

    def test_the_link_line_fails_when_the_first_folder_cannot_be_made(self) -> None:
        # A file where Antigravity's folder goes makes its mkdir fail; OpenCode's after it would succeed.
        (self.root / LINKED[0]).parent.mkdir(parents=True)
        (self.root / LINKED[0]).write_text("")
        [line] = [command for command in POST_TOOLS if "ln -s" in command]
        done = self.scratch("env", *self.offline, *SHELL, line)
        self.assertNotEqual(done.returncode, 0)
        self.assertFalse((self.root / LINKED[1] / HC).is_symlink())

    def test_an_installed_stale_herdr_core_is_replaced_from_the_tag(self) -> None:
        # setUp installed a stale copy for Claude and Codex, as v0.1.17's skip-if-present hook left it.
        self.post_tools()
        for folder in HARNESSES:
            self.assertNotIn(
                "herdrdev/herdr-core",
                (self.root / folder / HC / "SKILL.md").read_text(),
            )
        self.assertEqual(json.loads(self.lock.read_text())["skills"][HC]["ref"], TAG)

    def test_agent_desktop_skills_come_from_the_pinned_tag(self) -> None:
        self.assertEqual(DESKTOP_TAG, f"v{DESKTOP_PIN}")

    def test_an_installed_agent_desktop_skill_is_replaced_from_the_tag(self) -> None:
        self.install("agent-desktop", "vercel-labs/agent-desktop", CODEX)
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE)
        for folder in (CODEX, CLAUDE):
            for name in DESKTOP:
                self.assertIn(
                    "from the tag",
                    (self.root / folder / name / "SKILL.md").read_text(),
                )
        entries = json.loads(self.lock.read_text())["skills"]
        self.assertEqual({entries[name]["ref"] for name in DESKTOP}, {DESKTOP_TAG})

    def test_claude_and_codex_share_the_repos_permissions_skill(self) -> None:
        targets = [
            f"~/{folder}/{PERMISSIONS}"
            for folder in (".agents/skills", ".claude/skills")
        ]
        done = self.scratch("mise", "dot", "apply", *targets)
        self.assertEqual(done.returncode, 0, done.stderr)
        source = REPO / "unix/home/.agents/skills" / PERMISSIONS
        for folder in (".agents/skills", ".claude/skills"):
            self.assertEqual((self.home / folder / PERMISSIONS).resolve(), source)
        self.assertTrue((source / "scripts/tcc_who.py").is_file())
        self.assertIn(f"name: {PERMISSIONS}\n", (source / "SKILL.md").read_text())

    def test_claude_and_codex_open_watched_agents_as_tabs(self) -> None:
        done = self.scratch("mise", "dot", "apply", *ENTRIES)
        self.assertEqual(done.returncode, 0, done.stderr)
        claude = (self.home / ".claude/CLAUDE.md").read_text()
        codex = (self.home / ".codex/AGENTS.md").read_text()
        self.assertEqual(claude.splitlines().count("@~/.config/agents/AGENTS.md"), 1)
        imported = (self.home / ".config/agents/AGENTS.md").read_text()
        self.assertEqual(imported, codex)
        for text in (codex, imported):
            self.assertIn("herdr-app do tab.new --space ", text)
            self.assertIn('--argv \'["codex-hc"', text)
            self.assertIn("If `herdr-app ls` fails, stop and ask the user", text)
            self.assertNotIn("hc run --bg", text)


if __name__ == "__main__":
    unittest.main()
