"""The native commands mise run lsp builds on: mise for installs and pins, claude for plugins, git for the checkout."""

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from .models import PluginServer

# A plugin's language servers live in one of three places: .lsp.json at its root, lspServers in its
# .claude-plugin/plugin.json, or lspServers in its marketplace entry (claude-plugins-official's strict: false
# plugins; docs/research/lsp/root-cause.md).
type Servers = dict[str, PluginServer]


def limit(name: str, default: float) -> float:
    """How long one command or one server request may take: the environment variable name when set, else default.

    Two names, so a short request limit (a test of a server that never answers) leaves mise and claude their time.
    """
    return float(os.environ.get(name) or default)


def run(argv: Sequence[str], env: Mapping[str, str] | None = None) -> tuple[int, str, str]:
    """argv's exit code, stdout and stderr, run outside every project so only the global mise config applies.

    127 when argv can't start, as a shell says; 124 when it runs past its limit (300 s), as timeout(1) says.
    """
    seconds = limit("LSPTOOLS_COMMAND_SECONDS", 300)
    with tempfile.TemporaryDirectory() as outside:
        try:
            done = subprocess.run(
                argv,
                check=False,
                cwd=outside,
                env={**os.environ, **(env or {})},
                capture_output=True,
                text=True,
                timeout=seconds,
            )
        except OSError as failed:
            return 127, "", f"{argv[0]}: {failed.strerror}"
        except subprocess.TimeoutExpired:
            return 124, "", f"{argv[0]}: still running after {seconds:g} s"
    return done.returncode, done.stdout, done.stderr


def checked(argv: Sequence[str], env: Mapping[str, str] | None = None) -> str:
    """argv's stdout; ValueError naming the command and its error when it fails."""
    code, out, err = run(argv, env)
    if code:
        last = (err.strip().splitlines() or ["no output"])[-1]
        msg = f"{' '.join(argv)} exited {code}: {last}"
        raise ValueError(msg)
    return out


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def plugins() -> list[dict[str, object]]:
    """Every installed plugin, one entry per scope it is installed in (claude plugin list --json)."""
    return json.loads(checked(["claude", "plugin", "list", "--json"]))


def plugin_entry(installed: list[dict[str, object]], plugin: str) -> dict[str, object] | None:
    """The plugin's user-scope entry, which mise run lsp manages; else its first entry; else None."""
    found = [entry for entry in installed if entry.get("id") == plugin]
    user = [entry for entry in found if entry.get("scope") == "user"]
    return (user or found or [None])[0]


def servers_of(entry: Mapping[str, object]) -> Servers:
    """The language servers a plugin declares, wherever it declares them."""
    return {name: PluginServer.model_validate(server) for name, server in declared_by(entry).items()}


def declared_by(entry: Mapping[str, object]) -> dict[str, object]:
    root = Path(str(entry["installPath"]))
    if (root / ".lsp.json").is_file():
        return json.loads((root / ".lsp.json").read_text())
    manifest = root / ".claude-plugin/plugin.json"
    declared = json.loads(manifest.read_text()).get("lspServers") if manifest.is_file() else None
    if isinstance(declared, dict):
        return declared
    name, marketplace = str(entry["id"]).split("@", 1)
    # A plugin can outlive its marketplace (removed, or a directory marketplace Claude Code no longer lists): with no
    # listing to read, it declares no server from there.
    # A config with no marketplace added has no known_marketplaces.json.
    file = claude_home() / "plugins/known_marketplaces.json"
    known = json.loads(file.read_text()).get(marketplace) if file.is_file() else None
    listing = Path(known["installLocation"]) / ".claude-plugin/marketplace.json" if known else None
    if listing is None or not listing.is_file():
        return {}
    for plugin in json.loads(listing.read_text())["plugins"]:
        if plugin["name"] == name:
            return plugin.get("lspServers") or {}
    return {}


def global_tool(package: str) -> dict[str, object] | None:
    """The installed version of package that the global config asks for (mise ls --global --json)."""
    found = json.loads(checked(["mise", "ls", "--global", "--json", package]) or "[]")
    active = [entry for entry in found if entry.get("installed") and entry.get("active")]
    return (active or [None])[0]


def bootstrap_package(package: str) -> dict[str, object] | None:
    """A [bootstrap.packages] entry and its state (mise bootstrap packages status --json)."""
    manager, name = package.split(":", 1)
    status = json.loads(checked(["mise", "bootstrap", "packages", "status", "--json"]))
    for entry in status.get(manager, {}).get("packages", []):
        if entry["package"] == name:
            return entry
    return None


def tool_update(package: str) -> str | None:
    """The newer version mise would bump package to (mise outdated --global --bump), or None."""
    found = json.loads(checked(["mise", "outdated", "--global", "--bump", "--json", package]) or "{}")
    entry = found.get(package)
    return str(entry["latest"]) if entry else None


def bootstrap_update(package: str) -> str | None:
    """The version a bootstrap upgrade would install, from its dry run's "(requested)" line, or None."""
    name = package.split(":", 1)[1]
    plan = checked(["mise", "bootstrap", "packages", "upgrade", "--dry-run", package])
    found = re.search(rf"^\S+ {re.escape(name)}/(\S+) \(requested\)$", plan, re.MULTILINE)
    return found[1] if found else None


def write_target(start: Path) -> Path:
    """The global mise config of the dotfiles worktree holding start, which add, update and remove edit.

    ~/.config/mise/config.toml links into the main checkout, and main only moves to origin/main, so a change goes
    into a worktree and reaches the live config through a reviewed pull request.
    """
    code, top, _ = run(["git", "-C", str(start), "rev-parse", "--show-toplevel", "--git-dir", "--git-common-dir"])
    if code:
        msg = f"{start} is not in a git checkout: run add, update and remove from a dotfiles worktree"
        raise ValueError(msg)
    root, git_dir, common = (Path(start, line).resolve() for line in top.splitlines())
    config = root / "unix/home/.config/mise/config.toml"
    if not config.is_file():
        msg = f"{root} is not a dotfiles checkout (no unix/home/.config/mise/config.toml)"
        raise ValueError(msg)
    if git_dir == common:
        msg = f"{root} is the main checkout, which only moves to origin/main: run this from a dotfiles worktree"
        raise ValueError(msg)
    return config
