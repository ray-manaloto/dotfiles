"""The global post-tools hook's two guards: the herdr-core line skips without hc, the agent-desktop line stops
without a pin. What the hook installs is checked on the real home by `mise run skills:doctor`."""

# Both run through `mise run scratch:env`, so every home path is inside a temporary folder. Each guard stops the
# line before `skills add`; in case one did not, HTTP goes through Node's env proxy to a local server that answers
# every request 502, so nothing leaves the machine.

import json
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
[DESKTOP_LINE] = [
    command for command in POST_TOOLS if "vercel-labs/agent-desktop#" in command
]
NO_PIN = "post-tools: mise current printed no agent-desktop pin, so its skills are not installed"
DESKTOP = ("agent-desktop", "agent-desktop-macos", "agent-desktop-ffi", "jev-desktop")
HC = "herdr-core"
# The skill folders `skills add -g` writes, relative to the scratch root: Claude's, and the shared one.
CLAUDE, CODEX = "home/.claude/skills", "home/.agents/skills"


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
        # skills keeps its lock under $XDG_STATE_HOME, which scratch:env sets.
        self.lock = self.root / "state/skills/.skill-lock.json"
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
        # A stale herdr-core, as `skills add -g` leaves it: a folder per agent and a lock entry with no ref.
        for folder in (CODEX, CLAUDE):
            skill = self.root / folder / HC
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {HC}\ndescription: herdrdev/herdr-core\n---\n"
            )
        self.lock.parent.mkdir(parents=True)
        entry = {
            "source": "herdrdev/herdr-core",
            "sourceType": "github",
            "skillPath": f"skills/{HC}/SKILL.md",
        }
        self.lock.write_text(json.dumps({"version": 3, "skills": {HC: entry}}))

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

    def locked(self) -> dict[str, dict[str, str]]:
        return json.loads(self.lock.read_text())["skills"]

    def test_the_herdr_core_line_skips_without_hc(self) -> None:
        done = self.scratch("env", NO_HC_PATH, *self.offline, *SHELL, HC_LINE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(NO_HC, done.stderr.splitlines())
        # setUp's stale copy is left as it was, and nothing is installed.
        self.assertNotIn("ref", self.locked()[HC])

    def test_the_agent_desktop_line_stops_without_a_pin(self) -> None:
        # scratch:env's own mise config pins nothing, so `mise current` prints no version.
        done = self.scratch("env", *self.offline, *SHELL, DESKTOP_LINE)
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertIn(NO_PIN, done.stderr.splitlines())
        self.assertFalse(set(DESKTOP) & set(self.locked()))


if __name__ == "__main__":
    unittest.main()
