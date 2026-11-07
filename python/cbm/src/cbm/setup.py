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
from collections.abc import Iterator
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
# CBM 0.12.1 writes the Codex hooks to hooks.json only when stat() finds that file, and otherwise to a block in
# config.toml (src/cli/cli.c:9736-9738, :9786-9798). Install seeds an empty one so the JSON layout is always used.
CODEX_SEED = '{"hooks": {}}\n'
# A hook command CBM owns in config.toml: its binary, by basename and optionally single-quoted or behind
# PowerShell's "& ", running hook-augment (src/cli/config_toml_edit.c:3336-3361), or one of its two released
# SessionStart echoes (:3362-3369).
CODEX_TOML_HOOK = re.compile(r"(?:& )?(?P<q>'?)(?:.*[/\\])?codebase-memory-mcp(?:\.exe)?(?P=q) hook-augment")
CODEX_TOML_LEGACY = {
    'echo "Code discovery: prefer codebase-memory-mcp"',
    (
        'echo "Code discovery: prefer codebase-memory-mcp (search_graph, trace_path, get_code_snippet, query_graph, '
        'search_code) over grep/file-read; run index_repository first if the project is not indexed."'
    ),
}
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
    hooks_json = cfg.home / ".codex/hooks.json"
    if Client.codex in cfg.clients:
        seed_codex_hooks(hooks_json)
    # What upstream's stat() sees decides its hook file (cli.c:9736-9738): a dangling link sends it to config.toml.
    json_layout = Client.codex in cfg.clients and hooks_json.exists()
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
        config_toml = cfg.home / ".codex/config.toml"
        if json_layout and codex_toml_hooks(read_toml(config_toml)):
            # With hooks.json there, upstream takes its block out of config.toml (cli.c:9791-9796) unless its
            # preflight refuses (:9743-9764) or the hook write fails (:9800-9801); both log an agent_config line
            # (:8485-8498). The block is the owner's; cbm never edits it.
            msg = (f"cbm: the CBM installer exited {done.returncode} with {hooks_json} present and a CBM hook "
                   f"still in {config_toml}; its `error: agent_config agent=Codex CLI` line above (op=hook_preflight "
                   "or op=hook_install) gives the reason, and no such line means it failed before its Codex step. "
                   "Remove that hook by hand and rerun")  # fmt: skip
            raise InstallError(msg, config_toml, code=ErrorCode.codex_hook_migration_refused)
        msg = f"cbm: the CBM installer exited {done.returncode}"
        raise InstallError(msg, link, code=ErrorCode.installer_failed)
    set_ = probe(cfg, "config", "set", "auto_index", "false")
    return int(not check("config set auto_index false", ok=set_.returncode == 0, detail=first_line(set_)))


def seed_codex_hooks(path: Path) -> None:
    """An empty Codex hooks.json when nothing is at the path; an existing file, or any link, is left as it is."""
    if path.exists() or path.is_symlink():  # a file, or a link, dangling or not
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as file:  # O_EXCL: a file or link made since the check above is refused, never replaced
            file.write(CODEX_SEED)
    except OSError as error:  # ~/.codex is not a folder or cannot be written, or something appeared at the path
        msg = f"cbm: cannot create the empty Codex hooks file: {error}"
        raise InstallError(msg, path, code=ErrorCode.codex_hooks_seed_failed) from None


def lifecycle_hooks(hooks: object) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Each (event, matcher, hook) under an events table of group lists, in Claude's settings.json or either Codex file;
    a level of any other shape holds no hooks. A matcher that is not text is given as its repr, so the results stay
    hashable and sortable."""
    for event, groups in hooks.items() if isinstance(hooks, dict) else ():
        for group in groups if isinstance(groups, list) else ():
            entries = group.get("hooks") if isinstance(group, dict) else None
            matcher = group.get("matcher") if isinstance(group, dict) else None
            for hook in entries if isinstance(entries, list) else ():
                if isinstance(hook, dict):
                    yield event, matcher if isinstance(matcher, str) else repr(matcher), hook


def table(parent: dict[str, Any], key: str) -> dict[str, Any]:
    """The table (a JSON object or TOML table) at this key of a parsed config table. A value of any other shape, or a
    missing key, is an empty table: it holds no CBM entry, so only the check reading it fails."""
    value = parent.get(key)
    return value if isinstance(value, dict) else {}


def tool_names(value: object) -> list[str]:
    """The list of tool names as it stands; anything but a list of text holds none (set() fails on a table in it)."""
    return value if isinstance(value, list) and all(isinstance(name, str) for name in value) else []


def codex_toml_hooks(settings: dict[str, Any]) -> list[str]:
    """The events of every CBM hook registered in Codex's config.toml, whatever form the TOML takes."""
    return sorted({
        event
        for event, _, hook in lifecycle_hooks(settings.get("hooks"))
        if any(
            isinstance(command, str) and (CODEX_TOML_HOOK.fullmatch(command) or command in CODEX_TOML_LEGACY)
            for command in (hook.get("command"), hook.get("command_windows"))
        )
    })  # fmt: skip


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


def read_config(path: Path) -> str | None:
    """A config file's text; None when it is missing, or, after an unreadable_file event, when it cannot be read."""
    if not path.exists():  # missing, or a dangling link (exists follows links)
        return None
    if not path.is_file():  # a folder, or a FIFO or device, which a read could block on forever
        emit(Error(code=ErrorCode.unreadable_file, message="cbm: cannot read: not a regular file", path=path))
        return None
    try:
        return path.read_text()
    except (OSError, UnicodeDecodeError) as error:  # not this user's to read, removed since the check, or not UTF-8
        emit(Error(code=ErrorCode.unreadable_file, message=f"cbm: cannot read: {error}", path=path))
        return None


def read_text(path: Path) -> str:
    """A plain text file's contents; empty when it is missing or, after read_config's unreadable_file event, when it
    cannot be read, so only the check reading it fails."""
    return read_config(path) or ""


def read_json(path: Path, *, jsonc: bool = False) -> dict[str, Any]:
    """The file's JSON (or JSONC) object; a missing file is empty, one that cannot be read (read_config) or parsed,
    or whose top level is not an object, an error event and empty."""
    text = read_config(path)
    if text is None:
        return {}
    try:
        value = json.loads(strip_jsonc(text) if jsonc else text)
    except json.JSONDecodeError as error:
        emit(Error(code=ErrorCode.invalid_json, message=f"cbm: cannot parse JSON: {error}", path=path))
        return {}
    if isinstance(value, dict):
        return value
    emit(Error(code=ErrorCode.invalid_json, message="cbm: expected a JSON object at the top level", path=path))
    return {}


def read_toml(path: Path) -> dict[str, Any]:
    """The file's TOML table; a missing file is empty, one that cannot be read (read_config) or parsed an error event
    and empty. A TOML document is always a table at the top (tomllib's loads returns its root dict, _parser.py:219)."""
    text = read_config(path)
    if text is None:
        return {}
    try:
        return tomllib.loads(text)
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
        replies = [json.loads(line) for line in done.stdout.splitlines()]
        msg = "" if all(isinstance(reply, dict) for reply in replies) else "a JSON line that is not an object"
    except json.JSONDecodeError as error:
        replies, msg = [], f"something other than JSON: {error}"
    if msg:  # one error event, and no replies, so only the serves check fails
        emit(Error(code=ErrorCode.invalid_mcp_response, message=f"cbm: the MCP server answered {msg}",
                   path=config.launcher(cfg)))  # fmt: skip
        replies = []
    served = table(answer(replies, 1), "serverInfo").get("version")
    name = served if isinstance(served, str) else ""
    tools = set(listed_tools(answer(replies, 2).get("tools")))
    missing = sorted(READ_ONLY - tools)
    ok = done.returncode == 0 and bool(name) and version.split()[-1:] == [name] and not missing
    detail = f"{name or 'no version'}, {len(tools)} tools" + (f", missing {','.join(missing)}" if missing else "")
    return check("MCP server answers over stdio: the mise build, every read-only tool", ok=ok, detail=detail)


def answer(replies: list[dict[str, Any]], request: int) -> dict[str, Any]:
    """The result of the last reply to this request id; a result of any other shape, or a reply whose id is not this
    integer, answers nothing, so only the serves check fails."""
    results = [table(reply, "result") for reply in replies if type(reply.get("id")) is int and reply["id"] == request]
    return results[-1] if results else {}


def listed_tools(value: object) -> list[str]:
    """The tool names of a tools/list result; a list holding anything but objects with a text name lists none."""
    tools = value if isinstance(value, list) and all(isinstance(tool, dict) for tool in value) else []
    return tool_names([tool.get("name") for tool in tools])


def verify_claude(cfg: Config, target: str) -> list[bool]:
    mcp = table(table(read_json(cfg.home / ".claude.json"), "mcpServers"), "codebase-memory-mcp")
    plain = mcp.get("command") == target and mcp.get("args") == [] and set(mcp) <= {"type", "command", "args"}
    results = [
        check("Claude MCP entry names the launcher, no args or env", ok=plain and mcp.get("type", "stdio") == "stdio")
    ]
    want = {"type": "command", "command": target, "args": ["hook-augment"], "timeout": HOOK_TIMEOUT}
    # Every hook that runs the launcher, so a duplicate or a changed one counts too.
    hooks = read_json(cfg.home / ".claude/settings.json").get("hooks")
    cbm = [((event, matcher), hook) for event, matcher, hook in lifecycle_hooks(hooks) if hook.get("command") == target]
    exact = len(cbm) == len(CLAUDE_HOOKS) and {key for key, _ in cbm} == CLAUDE_HOOKS
    results.append(check(
        "Claude has the 7 CBM hook groups, once each", ok=exact and all(h == want for _, h in cbm),
        detail=f"{len(cbm)} found",
    ))  # fmt: skip
    for name in AGENTS:
        path = cfg.home / ".claude/agents" / f"{name}.md"
        head = read_text(path).split("\n---", 1)[0]
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
    settings = read_toml(codex / "config.toml")
    mcp = table(table(settings, "mcp_servers"), "codebase-memory-mcp")
    # CBM 0.12.1 lists the two namespace variables for Codex to forward if set (src/cli/cli.c:3890-3912).
    forwarded = mcp.get("env_vars") == ["CBM_CACHE_DIR", "CBM_RUNTIME_DIR"]
    plain = mcp.get("command") == target and mcp.get("args") == [] and set(mcp) <= {"command", "args", "env_vars"}
    results = [check("Codex MCP entry names the launcher, no args or env", ok=plain and forwarded)]
    command = f"'{target}' hook-augment"
    found = [
        (event, matcher)
        for event, matcher, hook in lifecycle_hooks(read_json(codex / "hooks.json").get("hooks"))
        if hook.get("command") == command and hook.get("type") == "command" and hook.get("timeout") == HOOK_TIMEOUT
    ]
    exact = len(found) == len(CODEX_HOOKS) and set(found) == CODEX_HOOKS
    results.append(check("Codex has the SessionStart and SubagentStart CBM hooks", ok=exact, detail=str(sorted(found))))
    in_toml = codex_toml_hooks(settings)
    label = "Codex config.toml has no CBM hooks; hooks.json holds them"
    results.append(check(label, ok=not in_toml, detail=", ".join(in_toml)))
    for name, profile in AGENTS.items():
        role = read_toml(codex / "agents" / f"{name}.toml")
        server = table(table(role, "mcp_servers"), "codebase-memory-mcp")
        tools = tool_names(server.get("enabled_tools"))
        launches = server.get("command") == target and server.get("args") == [f"--tool-profile={profile}"]
        known = bool(tools) and len(set(tools)) == len(tools) and set(tools) <= READ_ONLY
        sealed = role.get("name") == name and role.get("sandbox_mode") == "read-only"
        label = f"Codex agent {name}: launcher, {profile} profile, read-only CBM tools only"
        results.append(check(label, ok=sealed and launches and known))
    skill = (codex / "skills/codebase-memory/SKILL.md").is_file()
    results.append(check("Codex skill codebase-memory", ok=skill))
    results.append(agents_md(codex / "AGENTS.md", "Codex"))
    return results


def agents_md(path: Path, client: str) -> bool:
    text = read_text(path)
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
    mcp = table(table(read_json(opencode_config(folder), jsonc=True), "mcp"), "codebase-memory-mcp")
    plain = mcp.get("command") == [target] and mcp.get("type") == "local" and set(mcp) <= {"type", "command"}
    results = [check("OpenCode MCP entry names the launcher, no args or env", ok=plain)]
    for name in AGENTS:
        path = folder / "agents" / f"{name}.md"
        ok = opencode_agent(read_text(path))
        results.append(check(f"OpenCode agent {name}: a subagent, read-only CBM tools only", ok=ok))
    skill = (folder / "skills/codebase-memory/SKILL.md").is_file()
    results.append(check("OpenCode skill codebase-memory", ok=skill))
    results.append(agents_md(folder / "AGENTS.md", "OpenCode"))
    # The plugin runs `<launcher> hook-augment` around grep, glob and read; it names its binary once.
    plugin = folder / "plugins/cbm-augment.ts"
    names = f"const BIN = '{target}';" in read_text(plugin).splitlines()
    results.append(check("OpenCode plugin cbm-augment runs the launcher", ok=names))
    return results
