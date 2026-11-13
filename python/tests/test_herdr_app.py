"""Agent skills setup: the global post-tools hook, the linked skills and the hc-codex blocks."""

# All run through `mise run scratch:env`, so every home path is inside a temporary folder. The hook
# runs with the real `skills` CLI, and the scratch home's git config points GitHub at local
# repositories: herdr-core and agent-desktop, each at its tag and installed on every run. The
# herdr-core line runs the installed hc's `--version`, which starts no core (see REAL_HC). The CLI's other HTTP calls (api.github.com: repo privacy, the tree hash for the lock; skills 1.7.5
# dist/cli.mjs:80-87,3955-3967,6006) go through Node's env proxy to a local server that answers
# every request 502 and fail, which skills tolerates, so nothing leaves the machine. A closed port
# instead made Node retry the refused connection for about 16 s on each `skills add`.

import functools
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import tomllib
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((REPO / "unix/home/.config/mise/config.toml").read_text())
POST_TOOLS = CONFIG["bootstrap"]["hooks"]["post-tools"]["run"]
# mise runs each hook command with its default inline shell, unix_default_inline_shell_args
# (mise v2026.10.25 crates/mise-system/src/hooks.rs:180-247).
SHELL = ("sh", "-o", "errexit", "-c")
[HC_LINE] = [command for command in POST_TOOLS if "herdrdev/herdr-core#" in command]
# Only the system folders: no hc, as on a new Mac before Herdr's first run.
NO_HC_PATH = "PATH=/usr/bin:/bin"
# What the hook lines print, each as a whole stderr line: scratch:env echoes the command itself to
# stderr first, so a substring match would find the message in the echoed command.
NO_HC = "post-tools: herdr-core is not installed yet; open Herdr once, then rerun mise bootstrap"
# The installed hc, linked first on PATH so the herdr-core line runs the real `hc --version`. Its
# output gives the tag the line must install. It is read under macOS's `(deny process-fork)`, which
# proves the call prints the version without starting a core: a core start forks, and the sandbox
# refuses it. Without hc or sandbox-exec (Linux) the hook tests skip; the module still imports.
REAL_HC = shutil.which("hc")
SANDBOX = shutil.which("sandbox-exec")
NO_FORK = "(version 1)(allow default)(deny process-fork)"


@functools.cache
def installed_tag() -> str:
    """`v` and the X.Y.Z the installed hc prints, read where it cannot start a core."""
    assert REAL_HC and SANDBOX
    printed = subprocess.run(
        [SANDBOX, "-p", NO_FORK, REAL_HC, "--version"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    [version] = re.findall(r"^hc (\d+\.\d+\.\d+)$", printed, re.MULTILINE)
    return f"v{version}"


[DESKTOP_LINE] = [command for command in POST_TOOLS if "vercel-labs/agent-desktop#" in command]
DESKTOP_PIN = CONFIG["tools"]["github:vercel-labs/agent-desktop"]["version"]
# The tag the agent-desktop line must install: `v` and the pin, which it reads with `mise current`.
DESKTOP_TAG = f"v{DESKTOP_PIN}"
NO_PIN = "post-tools: mise current printed no agent-desktop pin, so its skills are not installed"
DESKTOP = ("agent-desktop", "agent-desktop-macos", "agent-desktop-ffi", "jev-desktop")
# A skill written in this repo, linked for both agents by [dotfiles] in mise.toml.
PERMISSIONS = "macos-agent-permissions"
# Skills written in the repo's shared agents folder, linked for both agents the same way.
USER_SKILLS = ("chief-of-staff", "herdr-startup", "herdr-shutdown")
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
# The skill folders the hook writes, relative to the scratch root: Claude's, and the shared one that Codex
# and OpenCode read. Antigravity CLI reads the shared one through mise.toml's ~/.gemini/config/skills link.
CLAUDE, CODEX = "home/.claude/skills", "home/.agents/skills"
ANTIGRAVITY = "home/.gemini/config/skills"
HARNESSES = (CLAUDE, CODEX)
# What the hook leaves in every scratch home: herdr-core and agent-desktop's skills, for Claude and Codex,
# and the jouet-init skill that `jouet setup claude --global` writes for Claude only.
CORE = {f"{folder}/{name}" for folder in HARNESSES for name in (HC, *DESKTOP)} | {f"{CLAUDE}/jouet-init"}


class BadGateway(BaseHTTPRequestHandler):
    """The test proxy: every method gets 502 and the connection closes."""

    def refuse(self) -> None:
        self.send_error(502)

    do_CONNECT = do_GET = do_HEAD = do_POST = refuse

    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output clean."""


class HerdrAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.home = self.root / "home"
        # skills keeps its lock under $XDG_STATE_HOME, which scratch:env sets.
        self.lock = self.root / "state/skills/.skill-lock.json"
        self.skills: dict[str, dict[str, str]] = {}
        # Answers every request, CONNECT included, with 502, so each call fails at once.
        proxy_server = ThreadingHTTPServer(("127.0.0.1", 0), BadGateway)
        self.addCleanup(proxy_server.server_close)
        self.addCleanup(proxy_server.shutdown)
        threading.Thread(target=proxy_server.serve_forever, daemon=True).start()
        proxy = f"http://127.0.0.1:{proxy_server.server_address[1]}"
        self.offline = (
            "DO_NOT_TRACK=1",  # no install telemetry
            "NODE_USE_ENV_PROXY=1",  # Node's fetch reads HTTP(S)_PROXY only with this
            f"HTTPS_PROXY={proxy}",
            f"HTTP_PROXY={proxy}",
        )
        if REAL_HC is None:
            self.skipTest("no hc on PATH: open Herdr once to install herdr-core")
        if SANDBOX is None:
            self.skipTest("no sandbox-exec to read hc --version without a core start")
        self.tag = installed_tag()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "hc").symlink_to(REAL_HC)
        self.install(HC, "herdrdev/herdr-core", CODEX, CLAUDE)
        self.github("herdrdev/herdr-core", self.tag, (HC,))
        self.github("vercel-labs/agent-desktop", DESKTOP_TAG, DESKTOP)

    def run_hook(self, command: str) -> subprocess.CompletedProcess[str]:
        """One hook command as mise runs it: this test's hc first on PATH, and a global config with
        only the agent-desktop pin, so `mise current` reads it as it reads the real config."""
        pins = self.root / "pins.toml"
        pins.write_text(f'[tools]\n"github:vercel-labs/agent-desktop" = "{DESKTOP_PIN}"\n')
        line = (
            f"PATH={shlex.quote(str(self.bin))}:$PATH; "
            f"export MISE_GLOBAL_CONFIG_FILE={shlex.quote(str(pins))}; {command}"
        )
        return self.scratch("env", *self.offline, *SHELL, line)

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
            done = self.run_hook(command)
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
        settings = json.loads((self.home / ".claude/settings.json").read_text())
        jouet = [
            hook["command"]
            for groups in settings["hooks"].values()
            for group in groups
            for hook in group["hooks"]
            if "jouet hook claude" in hook["command"]
        ]
        self.assertEqual(len(jouet), 6, jouet)

    def test_herdr_core_comes_from_the_installed_hc_tag(self) -> None:
        self.post_tools()
        self.assertEqual(
            json.loads(self.lock.read_text())["skills"][HC]["ref"], self.tag
        )

    def test_the_herdr_core_line_skips_without_hc(self) -> None:
        done = self.scratch("env", NO_HC_PATH, *self.offline, *SHELL, HC_LINE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(NO_HC, done.stderr.splitlines())
        # setUp's stale copy is left as it was, and nothing is installed.
        self.assertNotIn("ref", json.loads(self.lock.read_text())["skills"][HC])

    def test_a_codex_only_herdr_core_reaches_every_harness(self) -> None:
        shutil.rmtree(self.root / CLAUDE / HC)
        self.post_tools()
        self.assertEqual(self.on_disk(), CORE)
        for folder in HARNESSES:
            self.assertIn(
                "from the tag", (self.root / folder / HC / "SKILL.md").read_text()
            )

    def test_antigravity_reads_the_shared_copy_through_its_folder_link(self) -> None:
        self.post_tools()
        done = self.scratch("mise", "dot", "apply", "~/.gemini/config/skills")
        self.assertEqual(done.returncode, 0, done.stderr)
        link = self.root / ANTIGRAVITY
        self.assertEqual(os.readlink(link), "../../.agents/skills")
        self.assertIn("from the tag", (link / HC / "SKILL.md").read_text())

    def test_an_installed_stale_herdr_core_is_replaced_from_the_tag(self) -> None:
        # setUp installed a stale copy for Claude and Codex, as v0.1.17's skip-if-present hook left it.
        self.post_tools()
        for folder in HARNESSES:
            self.assertNotIn(
                "herdrdev/herdr-core",
                (self.root / folder / HC / "SKILL.md").read_text(),
            )
        self.assertEqual(
            json.loads(self.lock.read_text())["skills"][HC]["ref"], self.tag
        )

    def test_the_agent_desktop_line_stops_without_a_pin(self) -> None:
        # scratch:env's own mise config pins nothing, so `mise current` prints no version.
        done = self.scratch("env", *self.offline, *SHELL, DESKTOP_LINE)
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertIn(NO_PIN, done.stderr.splitlines())
        self.assertFalse(set(DESKTOP) & self.locked())

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

    def test_claude_and_codex_share_the_herdr_and_coordinator_skills(self) -> None:
        folders = (".agents/skills", ".claude/skills")
        targets = [f"~/{folder}/{name}" for folder in folders for name in USER_SKILLS]
        done = self.scratch("mise", "dot", "apply", *targets)
        self.assertEqual(done.returncode, 0, done.stderr)
        for name in USER_SKILLS:
            source = REPO / "unix/home/.config/agents/skills" / name
            for folder in folders:
                self.assertEqual((self.home / folder / name).resolve(), source)
            self.assertIn(f"name: {name}\n", (source / "SKILL.md").read_text())

    def test_skills_doctor_checks_every_skill_link(self) -> None:
        doctor = ("python3", "-I", str(REPO / "unix/home/.config/mise/tasks/skills/doctor"))
        self.assertEqual(self.scratch(*doctor).returncode, 1)
        entries = tomllib.loads((REPO / "mise.toml").read_text())["dotfiles"]
        targets = [target for target in entries if target.endswith("/skills") or "/skills/" in target]
        self.assertIn("~/.gemini/config/skills", targets)
        # setUp's herdr-core folders stand where the Antigravity CLI link goes, as on a Mac that had them.
        shutil.rmtree(self.root / CLAUDE)
        shutil.rmtree(self.root / CODEX)
        done = self.scratch("mise", "dot", "apply", *targets)
        self.assertEqual(done.returncode, 0, done.stderr)
        done = self.scratch(*doctor)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        (self.home / ".claude/skills/work").unlink()
        done = self.scratch(*doctor)
        self.assertEqual(done.returncode, 1)
        self.assertIn("~/.claude/skills/work", done.stdout)

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
