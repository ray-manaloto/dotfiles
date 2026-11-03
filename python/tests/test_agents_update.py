"""agents:update: real mise runs the global file task in a temporary HOME."""

# curl and the four agent CLIs are stand-ins (networked tools), so no agent CLI on the host is
# used and nothing is downloaded.

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "unix/home/.config/mise/tasks/agents/update"
MISE = Path(shutil.which("mise") or "mise").resolve()
PYTHON = f"#!{sys.executable} -I"

# Where each native installer puts its command.
NATIVE = {
    "https://claude.ai/install.sh": ".local/bin/claude",
    "https://chatgpt.com/codex/install.sh": ".local/bin/codex",
    "https://antigravity.google/cli/install.sh": ".local/bin/agy",
    "https://opencode.ai/v2/install": ".opencode/bin/opencode",
}
CLAUDE, CODEX, AGY, OPENCODE = NATIVE.values()
INSTALLS = [
    "install https://claude.ai/install.sh",
    "install https://chatgpt.com/codex/install.sh CODEX_NON_INTERACTIVE=1",
    "install https://antigravity.google/cli/install.sh",
    "install https://opencode.ai/v2/install --no-modify-path",
]
UPDATES = ["claude update", "codex update", "agy update", "opencode update"]

# `curl -fsSL -o FILE URL` writes an installer that records its URL, arguments and the
# codex prompt switch, then puts the CLI at its native path. The installer is shell because
# the task runs each vendor installer with the shell it is written for.
INSTALLER = r"""printf '%s\n' "install @URL@${*:+ $*}${CODEX_NON_INTERACTIVE:+ CODEX_NON_INTERACTIVE=$CODEX_NON_INTERACTIVE}" >> "$HOME/calls"
mkdir -p "$HOME/@DIR@" && cp "$HOME/tool" "$HOME/@BIN@"
rm -f "$HOME/@BIN@.version"
"""
CURL = f"""{PYTHON}
import sys
from pathlib import Path
NATIVE = {NATIVE!r}
INSTALLER = {INSTALLER!r}
if sys.argv[1:3] != ["-fsSL", "-o"] or len(sys.argv) != 5 or sys.argv[4] not in NATIVE:
    sys.exit(2)
url, binary = sys.argv[4], NATIVE[sys.argv[4]]
script = INSTALLER.replace("@URL@", url).replace("@BIN@", binary)
Path(sys.argv[3]).write_text(script.replace("@DIR@", str(Path(binary).parent)))
"""
# A native CLI: `update` is recorded, or fails when BINARY.version holds `fail`; `--version`
# prints BINARY.version (OpenCode 1 prints a bare `1.19.0`), else `NAME v2.2.5`; anything
# else is refused.
TOOL = f"""{PYTHON}
import sys
from pathlib import Path
me = Path(sys.argv[0])
version = Path(str(me) + ".version")
if sys.argv[1:] == ["update"]:
    if version.exists() and version.read_text() == "fail":
        sys.exit(1)
    with open(Path.home() / "calls", "a") as calls:
        calls.write(me.name + " update\\n")
elif sys.argv[1:] == ["--version"]:
    print(version.read_text().strip() if version.exists() else me.name + " v2.2.5")
else:
    sys.exit(2)
"""


class AgentsUpdateTest(unittest.TestCase):
    def run_task(
        self,
        installed: tuple[str, ...],
        runs: int = 1,
        versions: dict[str, str] | None = None,
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
            for binary in installed:
                tool = home / binary
                tool.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(home / "tool", tool)
            for binary, version in (versions or {}).items():
                (home / f"{binary}.version").write_text(version)
            for _ in range(runs):
                done = self.mise(home, stubs)
                if done.returncode:
                    break
            calls = home / "calls"
            lines = calls.read_text().splitlines() if calls.exists() else []
            return done.returncode, lines, done.stderr

    def mise(self, home: Path, stubs: Path) -> subprocess.CompletedProcess[str]:
        """One `mise run agents:update` from an unrelated folder, with HOME, XDG and PATH
        inside the temporary HOME, so only the global task folder can provide the task."""
        elsewhere = home / "elsewhere"
        elsewhere.mkdir(exist_ok=True)
        return subprocess.run(
            [MISE, "run", "agents:update"],
            env={
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "XDG_STATE_HOME": str(home / ".local/state"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "MISE_CEILING_PATHS": str(home),
                "MISE_AUTO_INSTALL": "0",
                # The task's python3 is this test's interpreter, never a host one.
                "PATH": f"{stubs}:{Path(sys.executable).parent}:/usr/bin:/bin",
            },
            cwd=elsewhere,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def test_installed_tools_update_themselves(self) -> None:
        code, calls, err = self.run_task(tuple(NATIVE.values()))
        self.assertEqual((code, calls), (0, UPDATES), err)

    def test_a_fresh_mac_gets_each_native_installer_once(self) -> None:
        code, calls, err = self.run_task(())
        self.assertEqual((code, calls), (0, INSTALLS), err)

    def test_a_second_run_only_updates(self) -> None:
        code, calls, err = self.run_task((), runs=2)
        self.assertEqual((code, calls), (0, INSTALLS + UPDATES), err)

    def test_a_mixed_mac_updates_some_and_installs_the_rest(self) -> None:
        code, calls, err = self.run_task((CLAUDE, OPENCODE))
        self.assertEqual(
            (code, calls), (0, [UPDATES[0], INSTALLS[1], INSTALLS[2], UPDATES[3]]), err
        )

    def test_opencode_1_is_replaced_by_the_v2_installer(self) -> None:
        # OpenCode 1's own updater stays on major version 1.
        code, calls, err = self.run_task(
            tuple(NATIVE.values()), runs=2, versions={OPENCODE: "1.19.0"}
        )
        self.assertEqual((code, calls), (0, UPDATES[:3] + INSTALLS[3:] + UPDATES), err)

    def test_one_failing_update_does_not_stop_the_others(self) -> None:
        # `fail` makes the stand-in claude refuse `update`; the rest still run, the task
        # reports claude as one JSON event and exits 1.
        code, calls, err = self.run_task(
            tuple(NATIVE.values()), versions={CLAUDE: "fail"}
        )
        self.assertEqual((code, calls), (1, UPDATES[1:]), err)
        events = [json.loads(line) for line in err.splitlines() if line.startswith("{")]
        self.assertEqual(
            [(event["event"], event["agent"]) for event in events],
            [("agent_failed", "claude")],
        )


if __name__ == "__main__":
    unittest.main()
