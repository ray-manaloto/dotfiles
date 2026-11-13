"""A scratch world for lsptools: its own Claude Code config, mise config and git checkouts; real claude, mise, git."""

import contextlib
import json
import os
import shutil
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from lsptools import cli

# tests -> lsp -> python -> the checkout, whose .claude-plugin/marketplace.json is the real "dotfiles" marketplace.
REPO = Path(__file__).resolve().parents[3]
STAND_IN = Path(__file__).with_name("stand_in.py")
needs_brew = pytest.mark.skipif(shutil.which("brew") is None, reason="clangd's mise install is a Homebrew formula")


@dataclass(frozen=True)
class Typescript:
    """The npm:typescript that the live global mise config installs, and its tsc."""

    version: str
    tsc: Path


@dataclass(frozen=True)
class Result:
    code: int
    out: str
    err: str

    def json(self) -> dict[str, Any]:
        return json.loads(self.out)

    def error(self) -> str:
        return json.loads(self.err)["error"]


@pytest.fixture(scope="session")
def typescript() -> Typescript:
    """Read before any test isolates mise from the live config. The tests drive the real claude and tsc, so without
    them they skip."""
    if shutil.which("claude") is None:
        pytest.skip("claude is not on PATH: the tests drive the real Claude Code plugin commands")
    found = json.loads(
        subprocess.run(
            ["mise", "ls", "--global", "--json", "npm:typescript"], capture_output=True, text=True, check=True
        ).stdout
    )
    active = next((entry for entry in found if entry["installed"] and entry["active"]), None)
    if active is None:
        pytest.skip("the global mise config installs no npm:typescript: the tests start its tsc")
    return Typescript(version=active["version"], tsc=Path(active["install_path"], "bin/tsc"))


class World:
    """One test's Claude Code config and mise global config; every command a test runs sees only these."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch, typescript: Typescript) -> None:
        self.root = root
        self.monkeypatch = monkeypatch
        self.claude = root / "claude"
        self.config = root / "mise/global.toml"
        (root / "mise/dir").mkdir(parents=True)
        self.claude.mkdir()
        self.mise(f'[tools]\n"npm:typescript" = "{typescript.version}"\n')
        # A session's own plugin folders would show up in claude plugin list as @inline plugins.
        monkeypatch.delenv("CLAUDE_CODE_PLUGIN_DIRS", raising=False)
        # hk runs these tests from git's pre-commit hook, which exports GIT_INDEX_FILE, GIT_DIR and more: they would
        # point every scratch repository's git at the real checkout (as python/workflow/tests/conftest.py says).
        for name in [name for name in os.environ if name.startswith("GIT_")]:
            monkeypatch.delenv(name)
        monkeypatch.delenv("LSPTOOLS_COMMAND_SECONDS", raising=False)
        monkeypatch.delenv("LSPTOOLS_REQUEST_SECONDS", raising=False)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(self.claude))
        # An empty config folder, so the live ~/.config/mise/config.toml is not read; the scratch file is global.
        monkeypatch.setenv("MISE_CONFIG_DIR", str(root / "mise/dir"))
        monkeypatch.setenv("MISE_GLOBAL_CONFIG_FILE", str(self.config))
        # mise records each config it reads in its state folder (tracked-configs); a scratch one keeps the test's
        # configs out of ~/.local/state/mise.
        monkeypatch.setenv("MISE_STATE_DIR", str(root / "mise/state"))
        # A scratch data folder too, holding only a link to the installed typescript version. mise rewrites each
        # tool's installs/<tool>/global link to match the global config it reads (src/runtime_symlinks.rs at
        # v2026.11.8), so with the live data folder a test's scratch config deleted the real links of every other
        # tool, depmaps' codebase-memory-mcp among them. The link is to the version folder, so mise's own links stay
        # in the scratch installs/npm-typescript folder.
        installs = root / "mise/data/installs/npm-typescript"
        installs.mkdir(parents=True)
        (installs / typescript.version).symlink_to(typescript.tsc.parents[1])
        monkeypatch.setenv("MISE_DATA_DIR", str(root / "mise/data"))
        # The global git config's hooks (hook.hk-pre-commit.command) run even with core.hooksPath=/dev/null, and
        # they start hk through mise, which the scratch data folder doesn't hold. Each hook command skips on HK=0.
        monkeypatch.setenv("HK", "0")
        monkeypatch.setenv("MISE_OFFLINE", "1")
        monkeypatch.setenv("TS_LSP_TSC", str(typescript.tsc))

    def mise(self, text: str) -> None:
        self.config.write_text(text)

    def claude_cli(self, *args: str) -> None:
        subprocess.run(["claude", "plugin", *args], cwd=self.root, capture_output=True, check=True)

    def dotfiles(self) -> None:
        """The checkout's own marketplace, with the real typescript-native-lsp plugin installed and enabled."""
        self.claude_cli("marketplace", "add", str(REPO), "--scope", "user")
        self.claude_cli("install", "typescript-native-lsp@dotfiles", "--scope", "user")

    def market(self, name: str, plugins: dict[str, dict[str, object]], *, install: bool = True) -> Path:
        """A local marketplace. Each plugin's dict may hold "lsp" (its .lsp.json), "manifest" (lspServers in its
        plugin.json) and "entry" (lspServers in its marketplace entry, which is then strict: false)."""
        folder = self.root / "markets" / name
        entries = []
        for plugin, parts in plugins.items():
            source = folder / "plugins" / plugin
            (source / ".claude-plugin").mkdir(parents=True)
            manifest: dict[str, object] = {"name": plugin, "version": "1.0.0"}
            if "manifest" in parts:
                manifest["lspServers"] = parts["manifest"]
            (source / ".claude-plugin/plugin.json").write_text(json.dumps(manifest))
            if "lsp" in parts:
                (source / ".lsp.json").write_text(json.dumps(parts["lsp"]))
            entry: dict[str, object] = {"name": plugin, "source": f"./plugins/{plugin}"}
            if "entry" in parts:
                entry |= {"strict": False, "lspServers": parts["entry"]}
            entries.append(entry)
        listing = {"name": name, "owner": {"name": "tests"}, "plugins": entries}
        (folder / ".claude-plugin").mkdir(parents=True)
        (folder / ".claude-plugin/marketplace.json").write_text(json.dumps(listing))
        self.claude_cli("marketplace", "add", str(folder), "--scope", "user")
        for plugin in plugins if install else []:
            self.claude_cli("install", f"{plugin}@{name}", "--scope", "user")
        return folder

    def stand_in(self, answers: dict[tuple[str, ...], dict[str, object]]) -> Path:
        """mise as tests/stand_in.py, ahead of the real one on PATH, answering these calls; returns its call log."""
        folder = self.root / "stand-in"
        folder.mkdir(exist_ok=True)
        (folder / "mise").unlink(missing_ok=True)
        (folder / "mise").symlink_to(STAND_IN)
        script = {json.dumps(["mise", *call]): answer for call, answer in answers.items()}
        (folder / "script.json").write_text(json.dumps(script))
        self.monkeypatch.setenv("STAND_IN", str(folder))
        self.monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
        return folder / "calls.jsonl"

    def without(self, *names: str) -> None:
        """PATH holding only links to the programs a test needs, so the named ones are missing."""
        keep = ["claude", "git", "mise", "python3", "sh", "clangd"]
        folder = self.root / "path"
        folder.mkdir()
        for name in keep:
            found = shutil.which(name)
            if name not in names and found:
                (folder / name).symlink_to(found)
        self.monkeypatch.setenv("PATH", str(folder))


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, typescript: Typescript) -> Iterator[World]:
    with contextlib.chdir(tmp_path):
        yield World(tmp_path, monkeypatch, typescript)


@pytest.fixture
def lsp(capsys: pytest.CaptureFixture[str]) -> Lsp:
    """lsptools run in this process with argv, as `mise run lsp <argv>` runs it."""

    def call(*argv: str) -> Result:
        with pytest.raises(SystemExit) as ended:
            cli.main(list(argv))
        captured = capsys.readouterr()
        return Result(code=int(ended.value.code or 0), out=captured.out, err=captured.err)

    return call


type Lsp = Callable[..., Result]
