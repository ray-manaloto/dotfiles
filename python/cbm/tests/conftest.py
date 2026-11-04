"""Fixtures: a temporary HOME holding a stand-in CBM binary at the mise global link."""

# No mocking library. The stand-in answers --version, config get/set and an MCP session on stdio
# (initialize, tools/list), and on `install` writes the agent setup the way CBM 0.12.1 does, for the
# clients and launcher folder it is given. HOME/mode picks how `install` behaves: ok, fail, hang, link
# (it leaves a launcher behind) or missing-hook; HOME/mcp-old, mcp-missing-tool and mcp-garbage break
# the MCP session; HOME/mcp-hang stalls it beyond the command's real timeout.
#
# Why not the real CBM binary: every CBM process meets in one account-wide daemon rendezvous, whatever
# HOME says (src/daemon/bootstrap.c:243-255 at v0.12.1; only CBM_RUNTIME_DIR moves it, and the package
# strips that on purpose). A real run from a temporary HOME brings a second cache root into the live
# daemon's namespace, which refuses it (`cache_root` conflict, so `config set` fails) and records it in
# the live conflict log. The real binary also cannot fail, stall or write a broken config on demand, and
# is not on Linux test hosts. The real installer was run end to end against the live install instead
# (docs/research/codebase-memory-mcp/verification.md).
#
# cbm-augment.ts is the OpenCode plugin CBM 0.12.1's own installer wrote in a scratch HOME, with its
# launcher path replaced by @BIN@; the stand-in writes it back with the temporary launcher.

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest

from .mise_stand_in import MISE

LINK = ".local/share/mise/installs/github-deus-data-codebase-memory-mcp/global/codebase-memory-mcp"
LAUNCHER = ".local/share/codebase-memory-mcp/bin/codebase-memory-mcp"
# The installed command, as `uv run cbm` and the mise tasks start it.
CBM = Path(sys.executable).parent / "cbm"
TIMEOUT = 30

STAND_IN = r"""
import json, os, sys, time
from pathlib import Path
home = Path(os.environ["HOME"])
args = sys.argv[1:]
with (home / "processes.jsonl").open("a") as f:
    f.write(json.dumps({"args": args, "version": "9.9.9", "home": str(home), "cwd": str(Path.cwd()),
                       "runtime": os.getenv("CBM_RUNTIME_DIR"), "cache": os.getenv("CBM_CACHE_DIR"),
                       "launcher": sys.argv[0], "executable": str(Path(sys.argv[0]).resolve()),
                       "sentinel": os.getenv("CBM_TEST_SENTINEL")}) + "\n")
with open(home / "calls", "a") as f:
    f.write(" ".join(args) + "\n")
if args == ["--version"]:
    if (home / "version-fails").exists():
        sys.exit(1)
    print("codebase-memory-mcp 9.9.9"); sys.exit(0)
if args[:2] == ["config", "set"]:
    if (home / "config-fails").exists():
        sys.exit(1)
    (home / "cbm-config").write_text(args[3]); print(f"{args[2]} = {args[3]}"); sys.exit(0)
if args[:2] == ["config", "get"]:
    print((home / "cbm-config").read_text() if (home / "cbm-config").exists() else "true"); sys.exit(0)
if not args:  # an MCP session over stdio: answer initialize and tools/list, then exit at end of input
    if (home / "mcp-hang").exists():
        time.sleep(120)
    if (home / "mcp-garbage").exists():
        print("not json"); sys.exit(0)
    version = "0.0.1" if (home / "mcp-old").exists() else "9.9.9"
    tools = ["search_graph", "query_graph", "trace_path", "get_code_snippet", "get_file_outline",
             "get_graph_schema", "compare_graphs", "get_architecture", "search_code", "list_projects",
             "index_status", "check_index_coverage", "detect_changes", "index_repository"]
    if (home / "mcp-missing-tool").exists():
        tools.remove("trace_path")
    for line in sys.stdin:
        request = json.loads(line)
        if request.get("method") == "initialize":
            info = {"name": "codebase-memory-mcp", "version": version}
            result = {"protocolVersion": "2025-11-25", "serverInfo": info}
        elif request.get("method") == "tools/list":
            result = {"tools": [{"name": name} for name in tools]}
        else:
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
    sys.exit(0)
if args[0] != "install":
    sys.exit(64)
(home / "install-env.json").write_text(json.dumps(sorted(os.environ)))
mode = (home / "mode").read_text().strip()
if mode == "fail":
    sys.exit(3)
if mode == "hang":
    (home / "started").touch(); time.sleep(60); sys.exit(0)
bin_dir = Path(next(a for a in args if a.startswith("--dir=")).split("=", 1)[1])
if mode == "link":
    (bin_dir / "codebase-memory-mcp").symlink_to(bin_dir / "elsewhere")
clients = next(a for a in args if a.startswith("--clients=")).split("=", 1)[1].split(",")
cmd = str(bin_dir / "codebase-memory-mcp")
def write(rel, text):
    p = home / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
if "claude" in clients:
  write(".claude.json", json.dumps({"mcpServers": {"codebase-memory-mcp": {"command": cmd, "args": []}}}))
  hook = {"type": "command", "command": cmd, "args": ["hook-augment"], "timeout": 5}
  groups = {"SessionStart": [{"matcher": m, "hooks": [hook]} for m in ("startup", "resume", "clear", "compact")],
            "SubagentStart": [{"matcher": "*", "hooks": [hook]}],
            "PreToolUse": [{"matcher": "Grep|Glob|Bash", "hooks": [hook]}],
            "PostToolUse": [{"matcher": "Read", "hooks": [hook]}]}
  if mode == "missing-hook":
      del groups["PostToolUse"]
  write(".claude/settings.json", json.dumps({"hooks": groups}))
if "codex" in clients:
  write(".codex/config.toml", f'[mcp_servers.codebase-memory-mcp]\ncommand = "{cmd}"\nargs = []\n'
                              'env_vars = ["CBM_CACHE_DIR", "CBM_RUNTIME_DIR"]\n')
  codex_hook = {"type": "command", "command": f"'{cmd}' hook-augment", "timeout": 5}
  write(".codex/hooks.json", json.dumps({"hooks": {
      "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": [codex_hook]}],
      "SubagentStart": [{"matcher": "*", "hooks": [codex_hook]}]}}))
for name, profile in (("codebase-memory", "analysis"), ("codebase-memory-scout", "scout"),
                      ("codebase-memory-auditor", "analysis")):
  if "claude" in clients:
    write(f".claude/agents/{name}.md",
          f"---\nname: {name}\ntools:\n  - Read\n  - mcp__codebase-memory-mcp__search_graph\n---\nBody.\n")
  if "codex" in clients:
    write(f".codex/agents/{name}.toml",
          f'name = "{name}"\nsandbox_mode = "read-only"\n[mcp_servers.codebase-memory-mcp]\n'
          f'command = "{cmd}"\nargs = ["--tool-profile={profile}"]\nenabled_tools = ["search_graph"]\n')
  if "opencode" in clients:
    write(f".config/opencode/agents/{name}.md",
          f'---\ndescription: {name}\nmode: subagent\npermission:\n  "*": deny\n  read: allow\n  grep: allow\n'
          '  glob: allow\n  tool_search: allow\n  tool_search_regex: allow\n'
          '  "codebase-memory-mcp_search_graph": allow\n---\nBody.\n')
folders = {"claude": ".claude", "codex": ".codex", "opencode": ".config/opencode"}
for client in clients:
    write(f"{folders[client]}/skills/codebase-memory/SKILL.md", "skill\n")
for client in ("codex", "opencode"):
  if client in clients:
    write(f"{folders[client]}/AGENTS.md", "<!-- codebase-memory-mcp:start -->\n"
          "For structural codebase exploration, use the installed `codebase-memory` skill.\n"
          "<!-- codebase-memory-mcp:end -->\n")
if "opencode" in clients:
  # The MCP entry goes into opencode.jsonc when it exists, else opencode.json. Like CBM, it is spliced into the
  # text, so comments and trailing commas stay (the stand-in assumes no `mcp` key yet).
  jsonc = home / ".config/opencode/opencode.jsonc"
  config = jsonc if jsonc.is_file() else home / ".config/opencode/opencode.json"
  entry = json.dumps({"mcp": {"codebase-memory-mcp": {"command": [cmd], "type": "local"}}})[1:-1]
  text = config.read_text() if config.is_file() else "{}"
  write(str(config.relative_to(home)), text.replace("{", "{" + entry + ",", 1))
  write(".config/opencode/plugins/cbm-augment.ts", Path(@PLUGIN@).read_text().replace("@BIN@", cmd))
""".replace("@PLUGIN@", repr(str(Path(__file__).with_name("cbm-augment.ts"))))


def link(home: Path) -> Path:
    return home / LINK


def launcher(home: Path) -> Path:
    return home / LAUNCHER


def restored(home: Path) -> bool:
    return launcher(home).is_symlink() and launcher(home).readlink() == link(home)


def calls(home: Path) -> str:
    path = home / "calls"
    return path.read_text() if path.exists() else ""


def mode(home: Path, value: str) -> None:
    (home / "mode").write_text(value)


def events(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines()]


def failed(out: str) -> list[str]:
    return [event["name"] for event in events(out) if event["event"] == "check" and not event["ok"]]


def cbm(*args: str, cwd: Path, timeout: int = TIMEOUT) -> subprocess.CompletedProcess[str]:
    """`cbm <args>` with this test's environment and an explicit caller-owned working directory."""
    return subprocess.run(
        [str(CBM), *args], env=os.environ.copy(), stdin=subprocess.DEVNULL, capture_output=True, text=True,
        timeout=timeout, cwd=cwd, check=False,
    )  # fmt: skip


def package_source(folder: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Load an unchanged copy of this package through the installed CLI entrypoint."""
    source = folder / "python/cbm/src"
    shutil.copytree(Path(__file__).parents[1] / "src", source, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setenv("PYTHONPATH", str(source))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    return source


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temporary HOME with the stand-in at the mise global link, in mode ok."""
    root = tmp_path.resolve()
    for name in ("CBM_CLIENTS", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "OPENCODE_CONFIG", "CBM_CACHE_DIR",
                 "CBM_RUNTIME_DIR", "CBM_INSTALL_GIT_TIMEOUT_SECONDS",
                 "CBM_INSTALL_ALLOW_NON_MAIN", *(key for key in os.environ if key.startswith("GIT_"))):  # fmt: skip
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("HOME", str(root))
    monkeypatch.setenv("MISE_DATA_DIR", str(root / ".local/share/mise"))
    for name, folder in (("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                         ("XDG_CACHE_HOME", "cache"), ("XDG_STATE_HOME", "state"),
                         ("XDG_RUNTIME_DIR", "runtime")):  # fmt: skip
        (root / folder).mkdir(mode=0o700)
        monkeypatch.setenv(name, str(root / folder))
    link(root).parent.mkdir(parents=True)
    link(root).write_text(f"#!{sys.executable} -I\n{STAND_IN}")
    link(root).chmod(0o755)
    mode(root, "ok")
    checkout = root / "checkout"
    checkout.mkdir()
    git(checkout, "init", "--initial-branch=main")
    git(checkout, "commit", "--allow-empty", "-m", "Initial fixture")
    package = root / "package-checkout"
    package_source(package, monkeypatch)
    git(package, "init", "--initial-branch=main")
    git(package, "add", ".")
    git(package, "commit", "-m", "Package fixture")
    return root


def git(folder: Path, *args: str) -> str:
    # Real git in private repos: no inherited git-dir, hooks, signing or machine identity.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    done = subprocess.run(
        ["git", "-c", "user.name=CBM Test", "-c", "user.email=cbm@example.invalid", *args],
        cwd=folder, env=env, capture_output=True, text=True, check=True, timeout=TIMEOUT,
    )  # fmt: skip
    return done.stdout


def provision(home: Path, *args: str) -> None:
    """Prepare an installed test release through the fixture's mise, never the real program."""
    subprocess.run(
        [str(home / "bin/mise"), "install", *args], cwd=home / "worktree", env=os.environ.copy(),
        capture_output=True, text=True, check=True, timeout=TIMEOUT,
    )  # fmt: skip


@pytest.fixture
def upgrade_home(home: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Two local releases, a real worktree/source mirror and a PATH-only mise stand-in."""
    paths = {name: home / name for name in ("dotfiles", "worktree", "source", "mirror", "releases")}
    paths["dotfiles"].mkdir()
    git(paths["dotfiles"], "init", "--initial-branch=main")
    package = paths["dotfiles"] / "python/cbm"
    package.mkdir(parents=True)
    (paths["dotfiles"] / "mise.toml").write_text("monorepo_root = true\n[monorepo]\nlockfile = true\n")
    (package / "mise.toml").write_text("# The upgrade trial writes its candidate pin here.\n")
    global_config = paths["dotfiles"] / "unix/home/.config/mise/config.toml"
    global_config.parent.mkdir(parents=True)
    global_config.write_text('[tools]\n"github:DeusData/codebase-memory-mcp" = "9.9.9"\n')
    git(paths["dotfiles"], "add", ".")
    git(paths["dotfiles"], "commit", "-m", "Initial fixture")
    git(paths["dotfiles"], "worktree", "add", "-b", "upgrade", str(paths["worktree"]))
    paths["source"].mkdir()
    git(paths["source"], "init", "--initial-branch=main")
    releases = {}
    for version in ("9.9.9", "9.9.10"):
        folder = paths["releases"] / version
        folder.mkdir(parents=True)
        binary = folder / "codebase-memory-mcp"
        binary.write_text(f"#!{sys.executable} -I\n{STAND_IN.replace('9.9.9', version)}")
        binary.chmod(0o755)
        archive = folder / "codebase-memory-mcp.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(binary, arcname=binary.name)
        releases[version] = {
            "binary": str(binary), "url": archive.as_uri(), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "installed": str(link(home).parent.parent / version),
        }  # fmt: skip
        (paths["source"] / "codebase-memory-mcp.py").write_text(STAND_IN.replace("9.9.9", version))
        git(paths["source"], "add", ".")
        git(paths["source"], "commit", "-m", f"Release {version}")
        git(paths["source"], "tag", f"v{version}")
    git(home, "clone", "--mirror", str(paths["source"]), str(paths["mirror"]))
    installed = Path(releases["9.9.9"]["installed"])
    link(home).unlink()
    link(home).parent.rmdir()
    link(home).parent.symlink_to(installed, target_is_directory=True)
    (home / "mise-fixture.json").write_text(json.dumps({
        "releases": releases,
        "configs": [{"path": str(paths["worktree"] / "unix/home/.config/mise/config.toml"),
                     "tools": ["github:DeusData/codebase-memory-mcp"], "override": False}],
        "lockfile": str(paths["worktree"] / "mise.lock"),
    }))  # fmt: skip
    bin_dir = home / "bin"
    bin_dir.mkdir()
    mise = bin_dir / "mise"
    mise.write_text(f"#!{sys.executable} -I\n{MISE}")
    mise.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    provision(home, "github:DeusData/codebase-memory-mcp@9.9.9")
    return paths
