"""The text CBM 0.12.1 writes for Codex, cited from upstream; the stand-in installer and the tests both use it."""

# The stand-in inlines this file's source, so it imports nothing.

CODEX_BEGIN = "# >>> codebase-memory-mcp SessionStart >>>"  # src/cli/cli.c:3941-3942
CODEX_END = "# <<< codebase-memory-mcp SessionStart <<<"
AGENTS_POINTER = (
    "<!-- codebase-memory-mcp:start -->\n"
    "For structural codebase exploration, use the installed `codebase-memory` skill.\n"
    "<!-- codebase-memory-mcp:end -->\n"
)


def codex_mcp(cmd: str) -> str:
    """The Codex MCP table; CBM lists the two namespace variables for Codex to forward (src/cli/cli.c:3890-3912)."""
    return (
        f'[mcp_servers.codebase-memory-mcp]\ncommand = "{cmd}"\nargs = []\n'
        'env_vars = ["CBM_CACHE_DIR", "CBM_RUNTIME_DIR"]\n'
    )


def codex_commands(cmd: str) -> tuple[str, str]:
    """The hook's command and command_windows: the quoted binary, then hook-augment (src/cli/cli.c:3944-3977)."""
    return f"'{cmd}' hook-augment", f"& '{cmd}' hook-augment"


def codex_owned(command: str) -> bool:
    """Whether upstream counts a TOML hook command as its own: an optional `& `, the binary as one safe shell word,
    bare or single-quoted, named codebase-memory-mcp(.exe), then ` hook-augment` (src/cli/config_toml_edit.c:3305-3361).
    The stand-in does not take the `'\\''` escape (:3326-3328); no test path holds a quote."""
    word = command.removeprefix("& ")
    if not word.endswith(" hook-augment"):
        return False
    word = word.removesuffix(" hook-augment")
    quoted = len(word) >= 2 and word[0] == word[-1] == "'"
    inner = word[1:-1].replace("''", "") if quoted else word
    unsafe = "'" if quoted else " \"'`$;&|<>(){}[]*?!"
    if any(ch in unsafe or ch < " " or ch == "\x7f" for ch in inner):
        return False
    return inner.replace("\\", "/").rsplit("/", 1)[-1] in {"codebase-memory-mcp", "codebase-memory-mcp.exe"}


def codex_block(command: str, windows: str) -> str:
    """The Codex hook block, verbatim from src/cli/config_toml_edit.c:3447-3456 (these commands need no escaping)."""
    return (
        "[[hooks.SessionStart]]\n"
        'matcher = "startup|resume|clear|compact"\n\n'
        "[[hooks.SessionStart.hooks]]\n"
        f'type = "command"\ncommand = "{command}"\n'
        f'command_windows = "{windows}"\ntimeout = 5\n\n'
        '[[hooks.SubagentStart]]\nmatcher = "*"\n\n'
        "[[hooks.SubagentStart.hooks]]\n"
        f'type = "command"\ncommand = "{command}"\n'
        f'command_windows = "{windows}"\ntimeout = 5\n'
    )


def codex_marked(command: str, windows: str) -> str:
    """The block between its markers, each on its own line (src/cli/config_toml_edit.c:990-1006)."""
    return f"{CODEX_BEGIN}\n{codex_block(command, windows)}{CODEX_END}\n"
