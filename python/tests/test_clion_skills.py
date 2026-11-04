"""clion:skills: real mise runs the global file task in a temporary HOME against jars built here."""

# Each CLion is a folder named like a Toolbox app holding a real zip at the AI Assistant module's
# path, so the task reads jars exactly as it reads CLion's. No JetBrains file is used.

import json
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "unix/home/.config/mise/tasks/clion/skills"
CONFIG = tomllib.loads((REPO / "unix/home/.config/mise/config.toml").read_text())
MISE = Path(shutil.which("mise") or "mise").resolve()
MODULE = (
    "plugins/air-plugin/lib/modules/intellij.aiagentextensions.contrib.ide.clion.jar"
)
TARGET = ".claude/skills/clion-debugger"
CONFIGS = "Library/Application Support/JetBrains"
# A stand-in for a running CLion: it listens on a loopback port and keeps the files named in
# its arguments (the module jar CLion loaded) open, until its stdin closes.
LISTENER = """
import socket, sys
server = socket.socket()
server.bind(("127.0.0.1", 0))
server.listen()
held = [open(name, "rb") for name in sys.argv[1:]]
print(server.getsockname()[1], flush=True)
sys.stdin.read()
"""
OWNED = ".dotfiles-clion-skills.json"


def skill(version: str, files: dict[str, str] | None = None) -> dict[str, str]:
    """A skill folder's files: metadata.json at `version`, plus `files` or a SKILL.md."""
    meta = json.dumps({"version": version, "hash": f"sha256:{version}"})
    return {"metadata.json": meta, **(files or {"SKILL.md": f"skill {version}\n"})}


class ClionSkills(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(TASK.is_file(), f"missing {TASK.relative_to(REPO)}")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name).resolve()
        task = self.home / ".config/mise/tasks/clion/skills"
        task.parent.mkdir(parents=True)
        shutil.copy2(TASK, task)
        self.apps = self.home / "Applications"
        self.apps.mkdir()
        self.target = self.home / TARGET
        self.env: dict[str, str] = {}

    def jar(self, path: Path, files: dict[str, str] | None) -> Path:
        """A jar at `path` holding `files` as the skill, beside another skill and a manifest."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            archive.writestr("bundledSkills/other-skill/SKILL.md", "not this one\n")
            if files is not None:
                archive.writestr("bundledSkills/clion-debugger/", "")
                for name, text in files.items():
                    archive.writestr(f"bundledSkills/clion-debugger/{name}", text)
        return path

    def app(self, name: str, files: dict[str, str] | None) -> Path:
        return self.jar(self.apps / f"{name}.app/Contents" / MODULE, files)

    def run_task(self, argv: list[str] | None = None) -> tuple[int, dict[str, str]]:
        """`argv` (default `mise run clion:skills`) from an unrelated folder; its exit code and
        its one JSON event."""
        elsewhere = self.home / "elsewhere"
        elsewhere.mkdir(exist_ok=True)
        done = subprocess.run(
            argv or [str(MISE), "run", "clion:skills"],
            env={
                "HOME": str(self.home),
                "XDG_CONFIG_HOME": str(self.home / ".config"),
                "XDG_DATA_HOME": str(self.home / ".local/share"),
                "XDG_STATE_HOME": str(self.home / ".local/state"),
                "XDG_CACHE_HOME": str(self.home / ".cache"),
                "MISE_CEILING_PATHS": str(self.home),
                "MISE_AUTO_INSTALL": "0",
                "CLION_SKILL_APPS": str(self.apps),
                "TERM": "dumb",
                # The task's python3 is this test's interpreter, never a host one.
                "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
                **self.env,
            },
            cwd=elsewhere,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        lines = (done.stdout if done.returncode == 0 else done.stderr).splitlines()
        events = [json.loads(line) for line in lines if line.startswith("{")]
        self.assertEqual(len(events), 1, (done.stdout, done.stderr))
        return done.returncode, events[0]

    def serve(self, *held: Path) -> None:
        """Start a process listening on the `clion` MCP port with `held` open."""
        listener = subprocess.Popen(
            [sys.executable, "-I", "-c", LISTENER, *map(str, held)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert listener.stdin is not None and listener.stdout is not None
        self.addCleanup(listener.wait, 10)
        self.addCleanup(listener.stdin.close)
        self.addCleanup(listener.stdout.close)
        self.mcp(listener.stdout.readline().strip())

    def mcp(self, port: str) -> None:
        url = f"http://127.0.0.1:{port}/stream"
        entry = {"mcpServers": {"clion": {"type": "http", "url": url}}}
        (self.home / ".claude.json").write_text(json.dumps(entry))

    def put(self, files: dict[str, str]) -> None:
        for name, text in files.items():
            path = self.target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def installed(self) -> dict[str, str]:
        """The target's files but the task's marker."""
        found = sorted(self.target.rglob("*"))
        return {
            p.relative_to(self.target).as_posix(): p.read_text()
            for p in found
            if p.is_file() and p.name != OWNED
        }

    def leftovers(self) -> list[str]:
        return sorted(
            p.name
            for p in (self.home / ".claude/skills").iterdir()
            if p.name.startswith(".")
        )

    def test_no_clion_reports_and_writes_nothing(self) -> None:
        self.app("CLion", None)
        self.assertEqual(
            self.run_task(), (0, {"skill": "clion-debugger", "status": "no-clion"})
        )
        self.assertFalse((self.home / ".claude").exists())

    def test_one_clion_installs_the_skill_folder_without_the_jar_prefix(self) -> None:
        files = skill("1.3.2", {"SKILL.md": "s\n", "reference/tools/a.md": "a\n"})
        jar = self.app("CLion", files)
        code, event = self.run_task()
        self.assertEqual(
            (code, event["status"], event["version"], event["jar"]),
            (0, "installed", "1.3.2", str(jar)),
        )
        self.assertEqual(self.installed(), files)
        record = json.loads((self.target / OWNED).read_text())
        self.assertEqual(
            (record["version"], sorted(record["files"])), ("1.3.2", sorted(files))
        )
        self.assertEqual(self.leftovers(), [])

    def test_one_config_folder_jar_installs_with_no_entry(self) -> None:
        self.jar(self.home / CONFIGS / "CLion2026.2" / MODULE, skill("1.1.4"))
        code, event = self.run_task()
        self.assertEqual(
            (code, event["status"], event["source"]), (0, "installed", "installed")
        )
        self.assertIn("CLion2026.2", event["jar"])

    def test_several_clions_and_no_entry_change_nothing(self) -> None:
        self.app("CLion", skill("1.1.4"))
        self.put(skill("1.1.4"))
        self.app("CLion 2026.3 Release Candidate", skill("1.3.2"))
        code, event = self.run_task()
        self.assertEqual((code, event["status"]), (0, "no-server"))
        self.assertIn("start the CLion", event["hint"])
        self.assertEqual(self.installed(), skill("1.1.4"))

    def test_the_clion_serving_mcp_wins_over_a_newer_one(self) -> None:
        old = self.app("CLion", skill("1.1.4"))
        self.app("CLion 2026.3 Release Candidate", skill("1.3.2"))
        self.serve(old)
        code, event = self.run_task()
        self.assertEqual(
            (code, event["status"], event["version"]), (0, "installed", "1.1.4")
        )
        self.assertTrue(event["source"].startswith("pid "), event)

    def test_a_module_loaded_from_a_config_folder_is_used(self) -> None:
        self.app("CLion", None)
        self.app("CLion 2026.3 Release Candidate", skill("1.3.2"))
        loaded = self.jar(self.home / CONFIGS / "CLion2026.2" / MODULE, skill("1.1.4"))
        self.serve(loaded)
        code, event = self.run_task()
        self.assertEqual(
            (code, event["version"], event["jar"]), (0, "1.1.4", str(loaded))
        )

    def test_an_entry_with_nothing_listening_changes_nothing(self) -> None:
        self.app("CLion", skill("1.1.4"))
        self.put(skill("1.1.4"))
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free = str(probe.getsockname()[1])
        self.mcp(free)
        self.app("CLion", skill("1.3.2"))
        code, event = self.run_task()
        self.assertEqual((code, event["status"]), (0, "no-server"))
        self.assertEqual(self.installed(), skill("1.1.4"))

    def test_an_unreadable_entry_changes_nothing(self) -> None:
        self.app("CLion", skill("1.3.2"))
        claude = self.home / ".claude.json"
        for text in (
            "{oops",
            "[]",
            '{"mcpServers": []}',
            '{"mcpServers": {"clion": []}}',
            '{"mcpServers": {"clion": {}}}',
            '{"mcpServers": {"clion": {"url": 5}}}',
            '{"mcpServers": {"clion": {"url": "http://example.com:64362/stream"}}}',
            '{"mcpServers": {"clion": {"url": "ftp://127.0.0.1:64362/"}}}',
            '{"mcpServers": {"clion": {"url": "http://127.0.0.1:99999/"}}}',
            '{"mcpServers": {"clion": {"url": "http://127.0.0.1:0/"}}}',
        ):
            with self.subTest(text=text):
                claude.write_text(text)
                code, event = self.run_task()
                self.assertEqual((code, event["status"]), (0, "invalid-config"))
                self.assertFalse(self.target.exists())

    def test_an_unreadable_claude_json_changes_nothing(self) -> None:
        self.app("CLion", skill("1.3.2"))
        claude = self.home / ".claude.json"
        claude.mkdir()
        code, event = self.run_task()
        self.assertEqual((code, event["status"]), (0, "invalid-config"))
        claude.rmdir()
        claude.symlink_to(self.home / "missing.json")
        self.assertEqual(self.run_task()[1]["status"], "invalid-config")
        self.assertFalse(self.target.exists())

    def test_other_mcp_entries_do_not_count(self) -> None:
        self.app("CLion", skill("1.3.2"))
        (self.home / ".claude.json").write_text('{"mcpServers": {"other": {}}}')
        self.assertEqual(self.run_task()[1]["status"], "installed")

    def test_a_listener_without_a_skill_module_open_is_an_error(self) -> None:
        self.app("CLion", skill("1.3.2"))
        self.serve()
        code, event = self.run_task()
        self.assertEqual(code, 1)
        self.assertIn("0 CLion skill modules open", event["error"])
        self.assertFalse(self.target.exists())

    def test_a_served_module_without_the_skill_is_an_error(self) -> None:
        self.serve(self.app("CLion", None))
        code, event = self.run_task()
        self.assertEqual(code, 1)
        self.assertIn("no bundledSkills/clion-debugger/", event["error"])

    def test_clion_skill_jar_pins_the_source(self) -> None:
        old = self.app("CLion", skill("1.1.4"))
        self.serve(self.app("CLion 2026.3 Release Candidate", skill("1.3.2")))
        self.env["CLION_SKILL_JAR"] = str(old)
        code, event = self.run_task()
        self.assertEqual(
            (code, event["status"], event["version"]), (0, "installed", "1.1.4")
        )

    def test_a_second_run_finds_the_copy_current(self) -> None:
        self.app("CLion", skill("1.3.2"))
        self.run_task()
        before = (self.target / OWNED).stat().st_mtime_ns
        code, event = self.run_task()
        self.assertEqual((code, event["status"]), (0, "current"))
        self.assertEqual((self.target / OWNED).stat().st_mtime_ns, before)

    def test_a_clion_update_replaces_the_whole_folder(self) -> None:
        self.app("CLion", skill("1.1.4", {"SKILL.md": "old\n", "gone.md": "x\n"}))
        self.run_task()
        self.app("CLion", skill("1.3.2", {"SKILL.md": "new\n"}))
        code, event = self.run_task()
        self.assertEqual(
            (code, event["status"], event["version"]), (0, "installed", "1.3.2")
        )
        self.assertEqual(self.installed(), skill("1.3.2", {"SKILL.md": "new\n"}))
        self.assertEqual(self.leftovers(), [])

    def test_local_edits_are_never_overwritten(self) -> None:
        self.app("CLion", skill("1.1.4"))
        self.run_task()
        (self.target / "SKILL.md").write_text("edited\n")
        self.app("CLion", skill("1.3.2"))
        code, event = self.run_task()
        self.assertEqual((code, event["status"]), (0, "modified"))
        self.assertIn("move it away", event["hint"])
        self.assertEqual(self.installed()["SKILL.md"], "edited\n")

    def test_a_missing_file_is_a_local_edit(self) -> None:
        self.app("CLion", skill("1.3.2"))
        self.run_task()
        (self.target / "SKILL.md").unlink()
        code, event = self.run_task()
        self.assertEqual((code, event["status"]), (0, "modified"))
        self.assertFalse((self.target / "SKILL.md").exists())

    def test_an_identical_unmarked_copy_is_adopted_then_updated(self) -> None:
        self.app("CLion", skill("1.1.4"))
        self.put(skill("1.1.4"))
        code, event = self.run_task()
        self.assertEqual((code, event["status"]), (0, "adopted"))
        self.assertTrue((self.target / OWNED).is_file())
        self.app("CLion", skill("1.3.2"))
        self.assertEqual(self.run_task()[1]["status"], "installed")
        self.assertEqual(self.installed(), skill("1.3.2"))

    def test_a_folder_the_task_did_not_write_is_left_alone(self) -> None:
        self.app("CLion", skill("1.3.2"))
        mine = {"metadata.json": "{}", "mine.txt": "keep me\n"}
        self.put(mine)
        code, event = self.run_task()
        self.assertEqual((code, event["status"]), (0, "unmanaged"))
        self.assertEqual(self.installed(), mine)

    def test_a_marker_that_is_not_the_tasks_counts_as_none(self) -> None:
        self.app("CLion", skill("1.3.2"))
        for marker in ("[]", "{not json", '{"files": {"a": 1}}'):
            with self.subTest(marker=marker):
                self.put({"SKILL.md": "mine\n", OWNED: marker})
                code, event = self.run_task()
                self.assertEqual((code, event["status"]), (0, "unmanaged"))
                self.assertEqual(self.installed(), {"SKILL.md": "mine\n"})

    def test_links_are_left_alone(self) -> None:
        self.app("CLion", skill("1.3.2"))
        outside = self.home / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text("outside\n")
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(outside)
        self.assertEqual(self.run_task()[1]["status"], "unmanaged")
        self.target.unlink()
        self.put({"metadata.json": skill("1.3.2")["metadata.json"]})
        (self.target / "SKILL.md").symlink_to(outside / "SKILL.md")
        self.assertEqual(self.run_task()[1]["status"], "unmanaged")
        self.assertEqual((outside / "SKILL.md").read_text(), "outside\n")

    def test_a_file_at_the_target_is_left_alone(self) -> None:
        self.app("CLion", skill("1.3.2"))
        self.target.parent.mkdir(parents=True)
        self.target.write_text("a file\n")
        self.assertEqual(self.run_task()[1]["status"], "unmanaged")
        self.assertEqual(self.target.read_text(), "a file\n")

    def test_a_path_leaving_the_skill_folder_is_refused(self) -> None:
        for name in ("../escape.md", OWNED):
            with self.subTest(name=name):
                self.app("CLion", skill("1.3.2", {"SKILL.md": "s\n", name: "x\n"}))
                code, event = self.run_task()
                self.assertEqual(code, 1)
                self.assertIn("unsafe path", event["error"])
                self.assertFalse(self.target.exists())
                self.assertFalse((self.home / ".claude/skills/escape.md").exists())

    def test_bad_metadata_in_the_jar_fails_with_an_error_event(self) -> None:
        for meta in ("[]", '{"version": 1, "hash": "h"}', "{oops"):
            with self.subTest(meta=meta):
                self.app("CLion", {"metadata.json": meta, "SKILL.md": "s\n"})
                code, event = self.run_task()
                self.assertEqual(code, 1)
                self.assertIn("error", event)
                self.assertFalse(self.target.exists())

    def test_a_jar_without_skill_md_keeps_the_installed_copy(self) -> None:
        self.app("CLion", skill("1.1.4"))
        self.run_task()
        self.app("CLion", {"metadata.json": skill("1.3.2")["metadata.json"]})
        code, event = self.run_task()
        self.assertEqual(code, 1)
        self.assertIn("no SKILL.md", event["error"])
        self.assertEqual(self.installed(), skill("1.1.4"))

    def test_a_broken_jar_fails_with_an_error_event(self) -> None:
        jar = self.apps / "CLion.app/Contents" / MODULE
        jar.parent.mkdir(parents=True)
        jar.write_text("not a zip")
        code, event = self.run_task()
        self.assertEqual(code, 1)
        self.assertIn("error", event)

    def test_bootstrap_runs_the_task_after_the_tools(self) -> None:
        hooks = CONFIG["bootstrap"]["hooks"]["post-tools"]["run"]
        line = next(hook for hook in hooks if "clion:skills" in hook)
        self.assertTrue(line.endswith(" </dev/null"), line)
        argv = shlex.split(line.removesuffix(" </dev/null"))
        self.assertEqual(argv[0], "mise")
        self.app("CLion", skill("1.3.2"))
        code, event = self.run_task([str(MISE), *argv[1:]])
        self.assertEqual((code, event["status"]), (0, "installed"))
        self.assertEqual(self.installed(), skill("1.3.2"))


if __name__ == "__main__":
    unittest.main()
