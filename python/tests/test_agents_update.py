"""agents:update: real mise runs the global file task in a temporary HOME."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "unix/home/.config/mise/tasks/agents/update"
MISE = Path(shutil.which("mise") or "mise").resolve()

# Where each native installer puts its command, and how a fresh Mac gets it.
NATIVE = {
    "claude": ".local/bin/claude",
    "codex": ".local/bin/codex",
    "agy": ".local/bin/agy",
    "opencode": ".opencode/bin/opencode",
}
INSTALLS = [
    "install https://claude.ai/install.sh",
    "install https://chatgpt.com/codex/install.sh",
    "install https://antigravity.google/cli/install.sh",
    "install https://opencode.ai/v2/install --no-modify-path",
]
UPDATES = ["claude update", "codex update", "agy update", "opencode update"]

# Prints an installer that records its URL and arguments, then puts the CLI at its native path.
CURL = """\
#!/bin/sh
[ "$1" = -fsSL ] && [ "$#" -eq 2 ] || exit 2
case "$2" in
  https://claude.ai/install.sh) bin=.local/bin/claude ;;
  https://chatgpt.com/codex/install.sh) bin=.local/bin/codex ;;
  https://antigravity.google/cli/install.sh) bin=.local/bin/agy ;;
  https://opencode.ai/v2/install) bin=.opencode/bin/opencode ;;
  *) exit 2 ;;
esac
printf 'printf "%%s\\\\n" "install %s${*:+ $*}" >> "$HOME/calls"\\n' "$2"
printf 'mkdir -p "$HOME/%s" && cp "$HOME/tool" "$HOME/%s"\\n' "${bin%/*}" "$bin"
"""
# A native CLI that records its one supported call, `update`, and refuses anything else.
TOOL = """\
#!/bin/sh
[ "$*" = update ] || exit 2
printf '%s\\n' "$(basename "$0") $*" >> "$HOME/calls"
"""


class AgentsUpdateTest(unittest.TestCase):
    def run_task(
        self, installed: tuple[str, ...], runs: int = 1
    ) -> tuple[int, list[str], str]:
        """`mise run agents:update` from a fresh HOME, `runs` times; rc, recorded calls, stderr."""
        self.assertTrue(TASK.is_file(), f"missing {TASK.relative_to(REPO)}")
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            task = home / ".config/mise/tasks/agents/update"
            task.parent.mkdir(parents=True)
            shutil.copy2(TASK, task)
            stubs = home / "stubs"
            stubs.mkdir()
            (stubs / "curl").write_text(CURL)
            (stubs / "curl").chmod(0o755)
            (home / "tool").write_text(TOOL)
            (home / "tool").chmod(0o755)
            for name in installed:
                tool = home / NATIVE[name]
                tool.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(home / "tool", tool)
            for _ in range(runs):
                done = self.mise(home, stubs)
                if done.returncode:
                    break
            calls = home / "calls"
            lines = calls.read_text().splitlines() if calls.exists() else []
            return done.returncode, lines, done.stderr

    def mise(self, home: Path, stubs: Path) -> subprocess.CompletedProcess[str]:
        """One `mise run agents:update` with HOME, XDG and PATH inside the temporary HOME."""
        return subprocess.run(
            [MISE, "run", "agents:update"],
            env={
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "XDG_STATE_HOME": str(home / ".local/state"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "MISE_CEILING_PATHS": str(home.parent),
                "MISE_AUTO_INSTALL": "0",
                "PATH": f"{stubs}:/usr/bin:/bin",
            },
            cwd=home,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def test_installed_tools_update_themselves(self) -> None:
        code, calls, err = self.run_task(tuple(NATIVE))
        self.assertEqual((code, calls), (0, UPDATES), err)

    def test_a_fresh_mac_gets_each_native_installer_once(self) -> None:
        code, calls, err = self.run_task(())
        self.assertEqual((code, calls), (0, INSTALLS), err)

    def test_a_second_run_only_updates(self) -> None:
        code, calls, err = self.run_task((), runs=2)
        self.assertEqual((code, calls), (0, INSTALLS + UPDATES), err)

    def test_a_mixed_mac_updates_some_and_installs_the_rest(self) -> None:
        code, calls, err = self.run_task(("claude", "opencode"))
        self.assertEqual(
            (code, calls), (0, [UPDATES[0], INSTALLS[1], INSTALLS[2], UPDATES[3]]), err
        )


if __name__ == "__main__":
    unittest.main()
