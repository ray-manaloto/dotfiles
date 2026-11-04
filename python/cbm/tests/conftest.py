"""Fixtures: a temporary HOME holding a stand-in CBM binary at the mise global link."""

# No mocking library. The stand-in answers --version, config get/set and an MCP session on stdio
# (initialize, tools/list), and on `install` writes the agent setup the way CBM 0.12.1 does, for the
# clients and launcher folder it is given. HOME/mode picks how `install` behaves: ok, fail, hang, link
# (it leaves a launcher behind) or missing-hook; HOME/mcp-old, mcp-missing-tool and mcp-garbage break
# the MCP session.
#
# Why not the real CBM binary: every CBM process meets in one account-wide daemon rendezvous, whatever
# HOME says (src/daemon/bootstrap.c:243-255 at v0.12.1; only CBM_RUNTIME_DIR moves it, and the package
# strips that on purpose). A real run from a temporary HOME brings a second cache root into the live
# daemon's namespace, which refuses it (`cache_root` conflict, so `config set` fails) and records it in
# the live conflict log. The real binary also cannot fail, stall or write a broken config on demand, and
# is not on Linux test hosts. The real installer was run end to end against the live install instead
# (docs/research/codebase-memory-mcp/verification.md).

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

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
for client in clients:
    write(f".{client}/skills/codebase-memory/SKILL.md", "skill\n")
if "codex" in clients:
  write(".codex/AGENTS.md", "<!-- codebase-memory-mcp:start -->\n"
        "For structural codebase exploration, use the installed `codebase-memory` skill.\n"
        "<!-- codebase-memory-mcp:end -->\n")
"""


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


def cbm(*args: str) -> subprocess.CompletedProcess[str]:
    """`cbm <args>` as a child process with this test's environment."""
    return subprocess.run(
        [str(CBM), *args], env=os.environ.copy(), stdin=subprocess.DEVNULL, capture_output=True, text=True,
        timeout=TIMEOUT, check=False,
    )  # fmt: skip


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temporary HOME with the stand-in at the mise global link, in mode ok."""
    root = tmp_path.resolve()
    for name in ("CBM_CLIENTS", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "CBM_CACHE_DIR", "CBM_RUNTIME_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(root))
    monkeypatch.setenv("MISE_DATA_DIR", str(root / ".local/share/mise"))
    link(root).parent.mkdir(parents=True)
    link(root).write_text(f"#!{sys.executable} -I\n{STAND_IN}")
    link(root).chmod(0o755)
    mode(root, "ok")
    return root
