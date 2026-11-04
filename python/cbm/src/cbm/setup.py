"""Run CBM's own installer for the agent setup through the stable launcher, and check what it wrote."""

# Why an empty launcher folder: on macOS, CBM 0.12.1 stages and re-signs an existing binary at the
# install target even with --skip-binary (src/cli/cli.c:11392 and :11406), so --dir pointed at the
# symlinked mise folder fails. Pointed at a folder without the binary it only writes configs, so the
# launcher symlink is removed for the installer's run and put back on every exit path.

import fcntl
import json
import re
import subprocess
import tomllib
from itertools import takewhile
from pathlib import Path
from typing import Any

from . import config, process
from .events import check, emit
from .models import Client, Config, Error, ErrorCode

CLAUDE_HOOKS = {("SessionStart", m) for m in ("startup", "resume", "clear", "compact")} | {
    ("SubagentStart", "*"),
    ("PreToolUse", "Grep|Glob|Bash"),
    ("PostToolUse", "Read"),
}
CODEX_HOOKS = {("SessionStart", "startup|resume|clear|compact"), ("SubagentStart", "*")}
HOOK_TIMEOUT = 5
# Each agent and the tool profile its Codex role launches.
AGENTS = {"codebase-memory": "analysis", "codebase-memory-scout": "scout", "codebase-memory-auditor": "analysis"}
# The 13 read-only tools of CBM 0.12.1's analysis profile (src/mcp/mcp.c); an agent may list only these.
READ_ONLY = {
    "search_graph", "query_graph", "trace_path", "get_code_snippet", "get_file_outline", "get_graph_schema",
    "compare_graphs", "get_architecture", "search_code", "list_projects", "index_status",
    "check_index_coverage", "detect_changes",
}  # fmt: skip
AGENTS_MD_BLOCK = ("<!-- codebase-memory-mcp:start -->", "<!-- codebase-memory-mcp:end -->")  # cli.c:3777
CLAUDE_TOOL = "- mcp__codebase-memory-mcp__"
# An OpenCode agent's frontmatter `permission:` map denies everything with `"*": deny`, then allows the source
# search tools and each CBM tool by its MCP name, `"codebase-memory-mcp_<tool>": allow`. One rule per line.
OPENCODE_TOOL = "codebase-memory-mcp_"
OPENCODE_SEARCH = ("read", "grep", "glob", "tool_search", "tool_search_regex")
OPENCODE_RULE = re.compile(r'  ("?)(?P<key>[^":\s]+)\1: (?P<action>\w+)')
# JSONC as CBM reads it (yyjson's ALLOW_COMMENTS and ALLOW_TRAILING_COMMAS, cli.c:4937): strings stay, a comment
# becomes a space, so it still separates tokens, and a comma after a value and before a closing bracket goes. Anything
# else, an unterminated comment or `[,]` included, is left for json.loads to refuse.
COMMENT = r"//[^\n]*|/\*(?:[^*]|\*(?!/))*\*/"  # a block comment cannot run past its first */
JSONC_TOKEN = re.compile(rf'"(?:\\.|[^"\\])*"|{COMMENT}|,')
JSONC_CLOSE = re.compile(rf"(?:\s|{COMMENT})*[}}\]]")
# What an agent session sends first over stdio (src/mcp/mcp.c:1458-1489); the server exits at end of input.
HANDSHAKE = "".join(
    json.dumps(message) + "\n"
    for message in (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "cbm", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
)  # fmt: skip
# A launcher that never answers fails its check instead of hanging the run.
TIMEOUT = 60


class InstallError(Exception):
    """The installer could not run or failed; the CLI turns it into one error event and exits 1."""

    def __init__(self, message: str, path: Path | None = None, *, code: ErrorCode) -> None:
        super().__init__(message)
        self.path = path
        self.code = code


def probe(
    cfg: Config, *args: str, input_text: str = "", program: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """The launcher (or program) with these arguments; one that cannot start or stalls is a failed run, not a crash."""
    path = program or config.launcher(cfg)
    try:
        return process.run(
            path, *args, cwd=cfg.home, env=config.child_env(), input_text=input_text, capture_output=True,
            timeout=TIMEOUT,
        )  # fmt: skip
    except (OSError, subprocess.TimeoutExpired) as error:  # one error event, then a failed run
        if isinstance(error, FileNotFoundError):
            code = ErrorCode.missing_binary
        elif isinstance(error, subprocess.TimeoutExpired):
            code = ErrorCode.command_timeout
        else:
            code = ErrorCode.command_failed
        emit(Error(code=code, message=f"cbm: {path.name} could not run: {error}", path=path))
        return subprocess.CompletedProcess([str(path), *args], 127, "", str(error))


def ours(cfg: Config) -> bool:
    path = config.launcher(cfg)
    return path.is_symlink() and path.readlink() == config.link(cfg)


def install(cfg: Config) -> int:
    """Run the installer and turn auto_index off; returns how many checks failed."""
    link, launcher = config.link(cfg), config.launcher(cfg)
    if not link.exists():
        msg = "cbm: the mise global link is missing; run `mise install` for the global config first"
        raise InstallError(msg, link, code=ErrorCode.missing_binary)
    launcher.parent.mkdir(parents=True, exist_ok=True)
    # One install at a time: a second run would see the launcher removed and restore it under the first.
    lock_path = launcher.parent.parent / "cbm-install.lock"
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            msg = "cbm: another cbm install is running; rerun when it has finished"
            raise InstallError(msg, lock_path, code=ErrorCode.install_busy) from None
        return installed(cfg)


def installed(cfg: Config) -> int:
    """With the install lock held: the installer with the launcher out of the way, then auto_index off."""
    link, launcher = config.link(cfg), config.launcher(cfg)
    mine = ours(cfg)
    if not mine and (launcher.exists() or launcher.is_symlink()):
        msg = f"cbm: the launcher is not this package's symlink to {link}; move it away and rerun"
        raise InstallError(msg, launcher, code=ErrorCode.foreign_launcher)
    clients = ",".join(cfg.clients)
    try:
        if mine:
            launcher.unlink()
        done = process.run(
            link, "install", "--skip-binary", f"--clients={clients}", f"--dir={launcher.parent}", "-y",
            cwd=cfg.home, env=config.child_env(), input_text=None, capture_output=False, timeout=None,
        )  # fmt: skip
    except OSError as error:  # the global link exists but cannot run
        msg = f"cbm: the CBM installer could not start: {error}"
        raise InstallError(msg, link, code=ErrorCode.installer_start_failed) from None
    finally:
        if not launcher.is_symlink():  # back on every exit path, so configs keep working
            launcher.symlink_to(link)
    if done.returncode != 0:
        msg = f"cbm: the CBM installer exited {done.returncode}"
        raise InstallError(msg, link, code=ErrorCode.installer_failed)
    set_ = probe(cfg, "config", "set", "auto_index", "false")
    return int(not check("config set auto_index false", ok=set_.returncode == 0, detail=first_line(set_)))


def first_line(done: subprocess.CompletedProcess[str]) -> str:
    lines = (done.stdout.strip() or done.stderr.strip()).splitlines()
    return lines[0] if lines else ""


def strip_jsonc(text: str) -> str:
    out: list[str] = []
    end, last = 0, ""  # last: the last character that is not space or comment
    for token in JSONC_TOKEN.finditer(text):
        gap, end = text[end : token.start()], token.end()
        last = gap.rstrip()[-1:] or last
        if token[0] == ",":
            trailing = last not in ("", "[", "{", ",", ":") and JSONC_CLOSE.match(text, end)
            out += [gap, "" if trailing else ","]
            last = last if trailing else ","
        else:
            out += [gap, token[0] if token[0].startswith('"') else " "]
            last = '"' if token[0].startswith('"') else last
    return "".join([*out, text[end:]])


def read_json(path: Path, *, jsonc: bool = False) -> dict[str, Any]:
    """The file's JSON (or JSONC) object; a missing file is empty, an unreadable one an error event."""
    text = path.read_text() if path.is_file() else "{}"
    if jsonc:
        text = strip_jsonc(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        emit(Error(code=ErrorCode.invalid_json, message=f"cbm: cannot parse JSON: {error}", path=path))
        return {}


def read_toml(path: Path) -> dict[str, Any]:
    """The file's TOML table; a missing file is empty, an unreadable one an error event."""
    try:
        return tomllib.loads(path.read_text()) if path.is_file() else {}
    except tomllib.TOMLDecodeError as error:
        emit(Error(code=ErrorCode.invalid_toml, message=f"cbm: cannot parse TOML: {error}", path=path))
        return {}


def verify(cfg: Config) -> int:
    """Check the whole setup; returns how many checks failed."""
    link, target = config.link(cfg), str(config.launcher(cfg))
    results = [check("launcher is a symlink to the mise global link", ok=ours(cfg))]
    linked = probe(cfg, "--version", program=link)
    via = probe(cfg, "--version")
    version = via.stdout.strip()
    same = linked.returncode == 0 and via.returncode == 0 and bool(version) and version == linked.stdout.strip()
    results.append(check("launcher runs the mise global build", ok=same, detail=version))
    results.append(serves(cfg, linked.stdout.strip()))
    auto = probe(cfg, "config", "get", "auto_index")
    off = auto.returncode == 0 and auto.stdout.strip() == "false"
    results.append(check("auto_index is false", ok=off, detail=first_line(auto)))
    stray = (cfg.home / ".local/bin/codebase-memory-mcp").exists()
    results.append(check("no CBM copy in ~/.local/bin", ok=not stray))
    if Client.claude in cfg.clients:
        results += verify_claude(cfg, target)
    if Client.codex in cfg.clients:
        results += verify_codex(cfg, target)
    if Client.opencode in cfg.clients:
        results += verify_opencode(cfg, target)
    return results.count(False)


def serves(cfg: Config, version: str) -> bool:
    """A live MCP session through the launcher: the mise build's version and every read-only tool."""
    done = probe(cfg, input_text=HANDSHAKE)
    try:
        replies = {reply.get("id"): reply.get("result", {}) for reply in map(json.loads, done.stdout.splitlines())}
    except json.JSONDecodeError as error:
        msg = f"cbm: the MCP server answered something other than JSON: {error}"
        emit(Error(code=ErrorCode.invalid_mcp_response, message=msg, path=config.launcher(cfg)))
        replies = {}
    name = replies.get(1, {}).get("serverInfo", {}).get("version", "")
    tools = {tool.get("name") for tool in replies.get(2, {}).get("tools", [])}
    missing = sorted(READ_ONLY - tools)
    ok = done.returncode == 0 and bool(name) and version.split()[-1:] == [name] and not missing
    detail = f"{name or 'no version'}, {len(tools)} tools" + (f", missing {','.join(missing)}" if missing else "")
    return check("MCP server answers over stdio: the mise build, every read-only tool", ok=ok, detail=detail)


def verify_claude(cfg: Config, target: str) -> list[bool]:
    mcp = read_json(cfg.home / ".claude.json").get("mcpServers", {}).get("codebase-memory-mcp") or {}
    plain = mcp.get("command") == target and mcp.get("args") == [] and set(mcp) <= {"type", "command", "args"}
    results = [
        check("Claude MCP entry names the launcher, no args or env", ok=plain and mcp.get("type", "stdio") == "stdio")
    ]
    want = {"type": "command", "command": target, "args": ["hook-augment"], "timeout": HOOK_TIMEOUT}
    hooks = read_json(cfg.home / ".claude/settings.json").get("hooks", {})
    # Every hook that runs the launcher, so a duplicate or a changed one counts too.
    cbm = [
        ((event, group.get("matcher")), hook)
        for event, groups in hooks.items() for group in groups for hook in group.get("hooks", [])
        if hook.get("command") == target
    ]  # fmt: skip
    exact = len(cbm) == len(CLAUDE_HOOKS) and {key for key, _ in cbm} == CLAUDE_HOOKS
    results.append(check(
        "Claude has the 7 CBM hook groups, once each", ok=exact and all(h == want for _, h in cbm),
        detail=f"{len(cbm)} found",
    ))  # fmt: skip
    for name in AGENTS:
        path = cfg.home / ".claude/agents" / f"{name}.md"
        head = path.read_text().split("\n---", 1)[0] if path.is_file() else ""
        tools = [line.strip().removeprefix(CLAUDE_TOOL) for line in head.splitlines()
                 if line.strip().startswith(CLAUDE_TOOL)]  # fmt: skip
        known = bool(tools) and len(set(tools)) == len(tools) and set(tools) <= READ_ONLY
        results.append(
            check(f"Claude agent {name}: present, read-only CBM tools only", ok=head.startswith("---") and known)
        )
    skill = (cfg.home / ".claude/skills/codebase-memory/SKILL.md").is_file()
    results.append(check("Claude skill codebase-memory", ok=skill))
    return results


def verify_codex(cfg: Config, target: str) -> list[bool]:
    codex = cfg.home / ".codex"
    mcp = read_toml(codex / "config.toml").get("mcp_servers", {}).get("codebase-memory-mcp", {})
    # CBM 0.12.1 lists the two namespace variables for Codex to forward if set (src/cli/cli.c:3890-3912).
    forwarded = mcp.get("env_vars") == ["CBM_CACHE_DIR", "CBM_RUNTIME_DIR"]
    plain = mcp.get("command") == target and mcp.get("args") == [] and set(mcp) <= {"command", "args", "env_vars"}
    results = [check("Codex MCP entry names the launcher, no args or env", ok=plain and forwarded)]
    command = f"'{target}' hook-augment"
    hooks = read_json(codex / "hooks.json").get("hooks", {})
    found = [
        (event, group.get("matcher"))
        for event, groups in hooks.items() for group in groups for hook in group.get("hooks", [])
        if hook.get("command") == command
        and hook.get("type") == "command" and hook.get("timeout") == HOOK_TIMEOUT
    ]  # fmt: skip
    exact = len(found) == len(CODEX_HOOKS) and set(found) == CODEX_HOOKS
    results.append(check("Codex has the SessionStart and SubagentStart CBM hooks", ok=exact, detail=str(sorted(found))))
    for name, profile in AGENTS.items():
        role = read_toml(codex / "agents" / f"{name}.toml")
        server = role.get("mcp_servers", {}).get("codebase-memory-mcp", {})
        tools = server.get("enabled_tools")
        launches = server.get("command") == target and server.get("args") == [f"--tool-profile={profile}"]
        known = isinstance(tools, list) and bool(tools) and len(set(tools)) == len(tools) and set(tools) <= READ_ONLY
        sealed = role.get("name") == name and role.get("sandbox_mode") == "read-only"
        label = f"Codex agent {name}: launcher, {profile} profile, read-only CBM tools only"
        results.append(check(label, ok=sealed and launches and known))
    skill = (codex / "skills/codebase-memory/SKILL.md").is_file()
    results.append(check("Codex skill codebase-memory", ok=skill))
    results.append(agents_md(codex / "AGENTS.md", "Codex"))
    return results


def agents_md(path: Path, client: str) -> bool:
    text = path.read_text() if path.is_file() else ""
    start, end = AGENTS_MD_BLOCK
    after = text.split(start, 1)[1] if start in text else ""
    inside = after.split(end, 1)[0] if end in after else ""
    return check(f"{client} AGENTS.md has the CBM managed block, pointing at the skill", ok="codebase-memory" in inside)


def opencode_config(folder: Path) -> Path:
    """The file CBM writes the MCP entry to: opencode.jsonc when it exists, else opencode.json (cli.c:2953-2975)."""
    jsonc = folder / "opencode.jsonc"
    return jsonc if jsonc.is_file() else folder / "opencode.json"


def opencode_agent(text: str) -> bool:
    """A subagent whose permission map is exactly: deny all first, then allow search and some read-only CBM tools.

    OpenCode keeps the written key order and the last matching rule wins (OpenCode v2.2.5
    packages/core/src/permission.ts:86), so a "*" deny written after the allows denies everything.
    """
    lines = text.removeprefix("---\n").split("\n---", 1)[0].splitlines()
    start = lines.index("permission:") + 1 if lines.count("permission:") == 1 else len(lines)
    # The block runs to the next top-level key; blank and comment lines inside it cannot end it early.
    block = takewhile(lambda line: not line or line[0].isspace() or line.startswith("#"), lines[start:])
    rules = [OPENCODE_RULE.fullmatch(line) for line in block if line.strip() and not line.lstrip().startswith("#")]
    actions = {rule["key"]: rule["action"] for rule in rules if rule}
    tools = {key.removeprefix(OPENCODE_TOOL) for key in actions if key.startswith(OPENCODE_TOOL)}
    wanted = {"*": "deny"} | dict.fromkeys([*OPENCODE_SEARCH, *(OPENCODE_TOOL + tool for tool in tools)], "allow")
    return (
        text.startswith("---\n") and "mode: subagent" in lines and all(rules) and len(actions) == len(rules)
        and actions == wanted and next(iter(actions)) == "*" and bool(tools) and tools <= READ_ONLY
    )  # fmt: skip


def verify_opencode(cfg: Config, target: str) -> list[bool]:
    folder = cfg.home / ".config/opencode"
    # CBM 0.12.1 writes the legacy `mcp` shape, which OpenCode 2 still reads (cli.c:4091-4094).
    mcp = read_json(opencode_config(folder), jsonc=True).get("mcp", {}).get("codebase-memory-mcp") or {}
    plain = mcp.get("command") == [target] and mcp.get("type") == "local" and set(mcp) <= {"type", "command"}
    results = [check("OpenCode MCP entry names the launcher, no args or env", ok=plain)]
    for name in AGENTS:
        path = folder / "agents" / f"{name}.md"
        ok = opencode_agent(path.read_text() if path.is_file() else "")
        results.append(check(f"OpenCode agent {name}: a subagent, read-only CBM tools only", ok=ok))
    skill = (folder / "skills/codebase-memory/SKILL.md").is_file()
    results.append(check("OpenCode skill codebase-memory", ok=skill))
    results.append(agents_md(folder / "AGENTS.md", "OpenCode"))
    # The plugin runs `<launcher> hook-augment` around grep, glob and read; it names its binary once.
    plugin = folder / "plugins/cbm-augment.ts"
    names = f"const BIN = '{target}';" in (plugin.read_text().splitlines() if plugin.is_file() else [])
    results.append(check("OpenCode plugin cbm-augment runs the launcher", ok=names))
    return results
