"""The buildx postinstall makes docker load mise's pinned buildx ahead of Docker Desktop's."""

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((REPO / "unix/home/.config/mise/config.toml").read_text())
BUILDX = CONFIG["tools"]["aqua:docker/buildx"]
POSTINSTALL = BUILDX["postinstall"]
# mise runs postinstall with its default inline shell, as it runs bootstrap hooks
# (unix_default_inline_shell_args; mise v2026.11.7 src/backend/mod.rs:5790).
SHELL = ("sh", "-o", "errexit", "-c")
DOCKER = shutil.which("docker")
JQ = shutil.which("jq")


def installed_buildx() -> str | None:
    """The pinned buildx's install folder, when this machine has it."""
    done = subprocess.run(
        ["mise", "where", f"aqua:docker/buildx@{BUILDX['version']}"],
        capture_output=True,
        text=True,
        check=False,
    )
    path = done.stdout.strip()
    return path if done.returncode == 0 and path else None


class BuildxPostinstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.install = installed_buildx()
        if DOCKER is None or JQ is None or self.install is None:
            self.skipTest("needs docker, jq and the pinned buildx installed by mise")
        self.home = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.home)
        self.config = self.home / ".docker/config.json"
        self.ours = str(self.home / ".local/share/docker/cli-plugins")
        self.env = {
            "HOME": str(self.home),
            "PATH": os.environ["PATH"],
            "MISE_TOOL_INSTALL_PATH": self.install,
        }

    def postinstall(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*SHELL, POSTINSTALL["run"]],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def buildx_version(self) -> str:
        return subprocess.run(
            [DOCKER, "buildx", "version"],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def test_it_runs_on_every_install(self) -> None:
        self.assertEqual(POSTINSTALL["when"], "always")

    def test_docker_loads_the_pinned_buildx_ahead_of_its_own_folder(self) -> None:
        # Docker Desktop's link in its own folder, here to a buildx that prints a wrong version.
        plugins = self.home / ".docker/cli-plugins"
        plugins.mkdir(parents=True)
        stale = self.home / "stale-buildx"
        stale.write_text(
            "#!/bin/sh\n"
            'case "$1" in docker-cli-plugin-metadata) '
            'echo \'{"SchemaVersion":"0.1.0","Vendor":"t","Version":"v0.0.1"}\';; '
            "*) echo stale buildx v0.0.1;; esac\n"
        )
        stale.chmod(0o755)
        (plugins / "docker-buildx").symlink_to(stale)
        self.config.write_text(
            json.dumps(
                {
                    "currentContext": "desktop-linux",
                    "cliPluginsExtraDirs": ["/elsewhere"],
                }
            )
        )
        done = self.postinstall()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(f"v{BUILDX['version']}", self.buildx_version())
        config = json.loads(self.config.read_text())
        self.assertEqual(config["cliPluginsExtraDirs"], [self.ours, "/elsewhere"])
        self.assertEqual(config["currentContext"], "desktop-linux")

    def test_a_repeat_run_leaves_config_json_as_it_is(self) -> None:
        self.assertEqual(self.postinstall().returncode, 0)
        before = self.config.read_bytes()
        self.assertEqual(json.loads(before)["cliPluginsExtraDirs"], [self.ours])
        done = self.postinstall()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertIn(f"v{BUILDX['version']}", self.buildx_version())

    def test_an_unreadable_config_json_fails_the_install_and_stays(self) -> None:
        self.config.parent.mkdir(parents=True)
        self.config.write_text("{not json")
        self.assertNotEqual(self.postinstall().returncode, 0)
        self.assertEqual(self.config.read_text(), "{not json")
