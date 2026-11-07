"""Fixtures: a temporary HOME holding a stand-in CBM binary at the mise global link."""

# No mocking library. The stand-in answers --version, config get/set and an MCP session on stdio
# (initialize, tools/list), and on `install` writes the agent setup the way CBM 0.12.1 does, for the
# clients and launcher folder it is given. HOME/mode picks how `install` behaves: ok, fail, hang, link
# (it leaves a launcher behind) or missing-hook; HOME/mcp-old, mcp-missing-tool and mcp-garbage break
# the MCP session; HOME/mcp-hang stalls it beyond the command's real timeout. HOME/mcp-fault, a JSON
# {"at": ..., "value": ...}, puts that value at one place in the replies: a line of its own before them,
# either request's result, the server info, the tool list, a tool entry, a tool's name or each reply's id.
#
# Why not the real CBM binary: every CBM process meets in one account-wide daemon rendezvous, whatever
# HOME says (src/daemon/bootstrap.c:243-255 at v0.12.1; only CBM_RUNTIME_DIR moves it, and the package
# strips that on purpose). A real run from a temporary HOME brings a second cache root into the live
# daemon's namespace, which refuses it (`cache_root` conflict, so `config set` fails) and records it in
# the live conflict log. The real binary also cannot fail, stall or write a broken config on demand, and
# is not on Linux test hosts. The real installer was run end to end against the live install instead
# (docs/research/codebase-memory-mcp/verification.md).
#
# Codex hooks follow CBM 0.12.1's choice of file: hooks.json when it exists, else a marked block in
# config.toml, with a marked block that is not exactly CBM's refused (see the Codex step below). The Codex
# text comes from codex_text.py, which the stand-in inlines; HOME/codex-hooks-seen keeps the hooks.json bytes
# the installer found.
#
# cbm-augment.ts is the OpenCode plugin CBM 0.12.1's own installer wrote in a scratch HOME, with its
# launcher path replaced by @BIN@; the stand-in writes it back with the temporary launcher.

import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Callable
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
import json, os, re, sys, time
from pathlib import Path
@SHARED@
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
    fault = json.loads((home / "mcp-fault").read_text()) if (home / "mcp-fault").exists() else {}
    at, bad = fault.get("at"), fault.get("value")
    if at == "line":
        print(json.dumps(bad), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        # The initialize result (src/mcp/mcp.c:1484-1489) and the tools/list result (:1095), one line each.
        if request.get("method") == "initialize":
            info = {"name": "codebase-memory-mcp", "version": version}
            result = {"protocolVersion": "2025-11-25", "serverInfo": bad if at == "serverInfo" else info}
        elif request.get("method") == "tools/list":
            entries = [{"name": name} for name in tools]
            if at == "tool":
                entries.append(bad)
            if at == "name":
                entries[0]["name"] = bad
            result = {"tools": bad if at == "tools" else entries}
        else:
            continue
        result = bad if at == request["method"] else result
        reply = bad if at == "id" else request["id"]
        print(json.dumps({"jsonrpc": "2.0", "id": reply, "result": result}), flush=True)
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
failures = 0
codex_ok = "codex" in clients
if "codex" in clients:
  # CBM 0.12.1's Codex step (src/cli/cli.c:9719-9812). The AGENTS.md pointer comes first (:9732).
  write(".codex/AGENTS.md", AGENTS_POINTER)
  config_toml, hooks_json = home / ".codex/config.toml", home / ".codex/hooks.json"
  # The hook file: hooks.json when stat() finds it, so a dangling symlink counts as missing (cli.c:9736-9738,
  # src/foundation/platform.c:309-312), else the TOML block in config.toml.
  use_json = hooks_json.exists()
  if use_json:
      (home / "codex-hooks-seen").write_bytes(hooks_json.read_bytes())
  command, windows = codex_commands(cmd)
  text = config_toml.read_text() if config_toml.is_file() else ""
  text = text.replace(codex_mcp(cmd), "")
  # The preflight (cli.c:9743-9764): a marked block is only CBM's when both its commands are CBM's and it is
  # exactly the block upstream renders for them (src/cli/config_toml_edit.c:3490-3497, :3654-3659); otherwise
  # the Codex step stops with this error line (cli.c:8492-8498) and the installer fails (cli.c:10581, :11180-11186).
  owned = ""
  if CODEX_BEGIN in text:
      span = CODEX_BEGIN + text.split(CODEX_BEGIN, 1)[1].split(CODEX_END, 1)[0] + CODEX_END + "\n"
      found = {}
      for key, value in re.findall(r'^(command|command_windows) = "(.*)"$', span, re.M):
          found.setdefault(key, value)
      pair = found.get("command", ""), found.get("command_windows", "")
      owned = span if all(map(codex_owned, pair)) and span == codex_marked(*pair) else ""
      if not owned:  # the agent's header goes to stdout first (cli.c:9751-9753)
          print("Codex CLI:", flush=True)
          print(f"error: agent_config agent=Codex CLI op=hook_preflight path={config_toml} "
                "reason=ambiguous_hook_ownership", file=sys.stderr)
          failures += 1
          codex_ok = False
if codex_ok:
  # The MCP table is written before the hooks (cli.c:9766-9767), both appended after the owner's text. The
  # installer reports it on stdout (cli.c:8735, :8744), and cbm passes that output through.
  print(f"Codex CLI:\n  mcp: {config_toml}")
  text = text.replace(owned, "")
  text += ("\n" if text and not text.endswith("\n") else "") + codex_mcp(cmd)
  if use_json:  # each event's CBM hooks are replaced by one canonical entry (cli.c:6427-6450, :4781-4900)
      hook = {"type": "command", "command": command, "command_windows": windows, "timeout": 5}
      settings = json.loads(hooks_json.read_text())
      events = settings.setdefault("hooks", {})
      for event, matcher in (("SessionStart", "startup|resume|clear|compact"), ("SubagentStart", "*")):
          kept = []
          for group in events.get(event, []):
              # A hook is CBM's only under the same matcher, as a command hook with exactly this command and no
              # args (cli.c:4625-4680). Only those go; their entry goes too once empty and canonical (:4693-4725).
              theirs = group.get("matcher") == matcher and isinstance(group.get("hooks"), list)
              left = [each for each in group["hooks"] if not (isinstance(each, dict) and "args" not in each
                      and each.get("type") == "command" and each.get("command") == command)] if theirs else []
              if not theirs or len(left) == len(group["hooks"]):
                  kept.append(group)
              elif left or set(group) != {"matcher", "hooks"}:
                  kept.append({**group, "hooks": left})
          events[event] = [*kept, {"matcher": matcher, "hooks": [hook]}]
      hooks_json.write_text(json.dumps(settings, indent=4))
  else:  # the marked block appended at the end (config_toml_edit.c:3725-3735)
      text += codex_marked(command, windows)
  write(".codex/config.toml", text)
  print("  hooks: SessionStart + SubagentStart (dynamic graph context)\n"  # cli.c:9802-9805
        "  note: non-managed hooks require /hooks trust; definition changes require re-trust", flush=True)
for name, profile in (("codebase-memory", "analysis"), ("codebase-memory-scout", "scout"),
                      ("codebase-memory-auditor", "analysis")):
  if "claude" in clients:
    write(f".claude/agents/{name}.md",
          f"---\nname: {name}\ntools:\n  - Read\n  - mcp__codebase-memory-mcp__search_graph\n---\nBody.\n")
  if codex_ok:
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
    if client != "codex" or codex_ok:
        write(f"{folders[client]}/skills/codebase-memory/SKILL.md", "skill\n")
if "opencode" in clients:
  write(".config/opencode/AGENTS.md", AGENTS_POINTER)
  # The MCP entry goes into opencode.jsonc when it exists, else opencode.json. Like CBM, it is spliced into the
  # text, so comments and trailing commas stay (the stand-in assumes no `mcp` key yet).
  jsonc = home / ".config/opencode/opencode.jsonc"
  config = jsonc if jsonc.is_file() else home / ".config/opencode/opencode.json"
  entry = json.dumps({"mcp": {"codebase-memory-mcp": {"command": [cmd], "type": "local"}}})[1:-1]
  text = config.read_text() if config.is_file() else "{}"
  write(str(config.relative_to(home)), text.replace("{", "{" + entry + ",", 1))
  write(".config/opencode/plugins/cbm-augment.ts", Path(@PLUGIN@).read_text().replace("@BIN@", cmd))
# Another agent step's config error fails the whole install too (cli.c:10581, :11173-11186).
failures += mode == "other-fails"
sys.exit(1 if failures else 0)
""".replace("@PLUGIN@", repr(str(Path(__file__).with_name("cbm-augment.ts")))).replace(
    "@SHARED@", Path(__file__).with_name("codex_text.py").read_text()
)


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
    """cbm's JSON records; the installer's own plain lines pass through between them on both streams."""
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


def failed(out: str) -> list[str]:
    return [event["name"] for event in events(out) if event["event"] == "check" and not event["ok"]]


def check_after(home: Path, edit: Callable[[], object], failing: str) -> subprocess.CompletedProcess[str]:
    """Install, apply one edit to the result, and expect verify to fail exactly that check."""
    assert cbm("install", cwd=home / "checkout").returncode == 0, calls(home)
    edit()
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 1
    assert failed(done.stdout) == [failing]
    assert events(done.stdout)[-1] == {
        "event": "done",
        "command": "verify",
        "failed": 1,
        "outcome": "failed",
        "message": "cbm: verify failed: 1 check failed",
    }
    return done


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
        [str(home / "bin/mise"), "install", *args], cwd=home, env=os.environ.copy(),
        capture_output=True, text=True, check=True, timeout=TIMEOUT,
    )  # fmt: skip


@pytest.fixture
def releases(home: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Two local releases installed through a PATH-only mise stand-in; returns a clean git checkout to run in."""
    checkout = home / "checkout"
    (checkout / "mise.toml").write_text('[tools]\n"github:DeusData/codebase-memory-mcp" = "9.9.9"\n')
    git(checkout, "add", ".")
    git(checkout, "commit", "-m", "Initial fixture")
    found = {}
    for version in ("9.9.9", "9.9.10"):
        folder = home / "releases" / version
        folder.mkdir(parents=True)
        binary = folder / "codebase-memory-mcp"
        binary.write_text(f"#!{sys.executable} -I\n{STAND_IN.replace('9.9.9', version)}")
        binary.chmod(0o755)
        archive = folder / "codebase-memory-mcp.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(binary, arcname=binary.name)
        found[version] = {"url": archive.as_uri(), "installed": str(link(home).parent.parent / version)}
    installed = Path(found["9.9.9"]["installed"])
    link(home).unlink()
    link(home).parent.rmdir()
    link(home).parent.symlink_to(installed, target_is_directory=True)
    (home / "mise-fixture.json").write_text(json.dumps({"releases": found}))
    bin_dir = home / "bin"
    bin_dir.mkdir()
    mise = bin_dir / "mise"
    mise.write_text(f"#!{sys.executable} -I\n{MISE}")
    mise.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    provision(home, "github:DeusData/codebase-memory-mcp@9.9.9")
    return checkout
