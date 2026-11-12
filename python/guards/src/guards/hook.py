"""Rule guards: one hook for Claude Code, Codex and Gemini CLI that blocks the commands the owner ruled out."""

# Run as `python3 -I hook.py` with the hook JSON on stdin, from whatever python3 the agent finds: stdlib only, and
# Python 3.9 syntax (macOS /usr/bin/python3), so annotations stay strings. Exit 2 with the reason on stderr blocks
# the call in all three agents (Codex rust-v0.167.0 codex-rs/hooks/src/events/pre_tool_use.rs:268-283; Gemini CLI
# 0.67 docs/hooks/reference.md "BeforeTool"; Claude Code PreToolUse). Anything else exits 0. An error inside the
# hook blocks a shell command and lets a file edit through (owner ruling 2026-11-11), so a hook bug never stops an
# agent from editing the hook itself.
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path, PurePosixPath

# Claude Code Bash, Gemini run_shell_command, Codex Bash (exec_command) and its older list-form shell tools.
SHELL_TOOLS = frozenset({"Bash", "run_shell_command", "shell", "local_shell", "exec_command"})
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ash", "ksh", "fish"})
PUNCTUATION = "();<>|&`"
# The operators inside one run of punctuation: `;>` is a separator and then a redirection.
OPERATOR = re.compile(r"&>>?|[<>]+&?|[()]|[;&|`]+")
COMMENT_AFTER = " \t\n;&|()<>"
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
# `cat <<'EOF'` ... `EOF`: the body is data, not commands (here-strings `<<<` are not heredocs).
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*\\?(['\"]?)([A-Za-z_][A-Za-z0-9_.-]*)\1")
JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
DOCKER_RUN = re.compile(r"\s*(?:ONBUILD\s+)?RUN\s+(?:--\S+\s+)*(.*)", re.IGNORECASE)
# A backslash-newline that is not itself escaped: bash and Docker both drop it.
CONTINUATION = re.compile(r"(?<!\\)((?:\\\\)*)\\\n")
WHOLE_SUBSTITUTION = re.compile(r"\s*(?:\$\((.*)\)|`(.*)`)\s*", re.DOTALL)

# Words that run the rest of the line as a command, with the options of each that take a value.
WRAPPERS = {
    "sudo": frozenset({"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T"}),
    "doas": frozenset({"-u", "-C"}),
    "env": frozenset({"-u", "-C", "-P"}),
    "nice": frozenset({"-n"}),
    "xargs": frozenset({"-I", "-n", "-P", "-L", "-s", "-E", "-d", "-a"}),
    "timeout": frozenset({"-s", "-k", "--signal", "--kill-after"}),
    "watch": frozenset({"-n", "--interval"}),
    "caffeinate": frozenset({"-t", "-w"}),
    "stdbuf": frozenset({"-i", "-o", "-e"}),
    "exec": frozenset({"-a"}),
    "command": frozenset(),
    "builtin": frozenset(),
    "nohup": frozenset(),
    "time": frozenset(),
    "setsid": frozenset(),
    "unbuffer": frozenset(),
    "ionice": frozenset({"-c", "-n", "-p", "-P", "-u"}),
    "flock": frozenset({"-w", "-E", "--timeout", "--conflict-exit-code"}),
}
KEYWORDS = frozenset({"if", "then", "elif", "else", "while", "until", "do", "!", "{", "}"})
# pgrep options that take a value: the value is not the pattern.
PGREP_VALUE_OPTIONS = frozenset({"-U", "-u", "-G", "-g", "-P", "-s", "-t", "-F", "-J", "-d"})
BREW_BUNDLE_READS = frozenset({"check", "list", "dump"})
DOPPLER_PRINTS = frozenset({"get", "download", "run", "substitute"})
DOPPLER_QUIET = frozenset({"set", "delete", "upload", "notes"})
FNOX_VALUE_OPTIONS = frozenset({"-c", "--config", "-P", "--profile", "--if-missing", "--write-profile"})
FNOX_REVEALING = frozenset({"get", "export", "exec", "edit", "tui", "mcp", "push"})

APT_PROGRAMS = frozenset({"apt", "apt-get"})
APT_ALLOWED_PACKAGES = frozenset({"ca-certificates", "curl", "git", "xz-utils"})
APT_ADDING = frozenset(
    {"install", "reinstall", "upgrade", "dist-upgrade", "full-upgrade", "build-dep", "source", "satisfies"}
)
APT_VALUE_OPTIONS = frozenset(
    {"-o", "--option", "-c", "--config-file", "-t", "--target-release", "-a", "--host-architecture"}
)
MISE_INSTALLER = "https://mise.run"

BREW = (
    "Blocked by rule guard 1 (agents never install with Homebrew): `brew {sub}` changes this machine's toolchain "
    "outside dotfiles. Instead ask dotfiles-lead for a dotfiles PR that adds it with `mise bootstrap packages use` "
    "and `mise bootstrap packages apply`."
)
DOCKERFILE = (
    "Blocked by rule guard 2 (images get their tools from mise): `{command}` in {path}. Install it with mise: "
    "bootstrap mise with `curl https://mise.run | sh` (or `COPY --from` a jdxcode/mise image), then `mise install` "
    "from a mise.toml and its lock. The only apt-get install allowed is ca-certificates, curl, git and xz-utils."
)
SECRETS = (
    "Blocked by rule guard 3 (secrets stay inside fnox): `{command}` would print, export or hand out a secret. "
    "Instead run `fnox proxy run -- <command>`: the command gets placeholders and the proxy puts the real key "
    "into requests to the hosts in its rules. Check what is set with `fnox check` or `fnox env --json --describe`."
)
DOCKER_UPDATE = (
    "Blocked by rule guard 4 (Docker Desktop updates are the owner's): `docker desktop update`. Ask the owner to "
    "run it; an agent only runs `docker desktop start --timeout 300`."
)
HERDR_CLOSE = (
    "Blocked by rule guard 5 (close only a checked tab): `herdr-app do {sub}` without `--id` closes whatever is "
    "focused. Pass `--id <id>` after checking it against `herdr-app ls`."
)
PKILL = (
    "Blocked by rule guard 6 (no killing by name): `{prog}` kills by name or pattern and can hit unrelated "
    "processes (a pkill took down Docker, Claude Desktop and a session on 2026-11-08). Kill your own child by its "
    "recorded pid or the process group you created; or run `pgrep` with every option before the pattern, check "
    "the list, then `kill <pids>`."
)
PGREP = (
    "Blocked by rule guard 6 (no killing by name): `pgrep` has an option after its pattern. macOS stops reading "
    "options at the first pattern, so the later options become extra patterns. Put every option before the pattern."
)
HOOK_ERROR = (
    "Blocked by a rule guard hook error ({error}): the hook could not judge this command, and a shell command it "
    "cannot judge does not run. Split the command into simpler ones, and tell dotfiles-lead what failed."
)


def basename(word: str) -> str:
    return word.rsplit("/", 1)[-1]


def positionals(args: list[str]) -> list[str]:
    """The arguments before `--` that are not options."""
    found = []
    for arg in args:
        if arg == "--":
            break
        if not arg.startswith("-"):
            found.append(arg)
    return found


def states(text: str) -> list[str]:
    """Each character's context: "" in code, "'" or '"' inside quotes, "#" in a comment, "\\" when escaped."""
    return scan(text)[0]


def scan(text: str, state: str = "") -> tuple[list[str], str]:
    """Each character's context, starting inside `state` (a quote left open by earlier lines), and the end state."""
    found: list[str] = []
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            found.append("\\")
            escaped = False
            continue
        closing = state in {"'", '"'} and char == state
        if state == "#":
            state = "" if char == "\n" else state
        elif char == "\\" and state != "'":
            escaped = True
        elif not state and char in {"'", '"'}:
            state = char
        elif not state and char == "#" and (index == 0 or (text[index - 1] in COMMENT_AFTER and found[-1] != "\\")):
            # A `#` starts a comment only at the start of a word: `${f#*.}`, `$#`, `p#frag` and `\ #` are not comments.
            state = "#"
        found.append(state)
        if closing:
            state = ""
    return found, "" if state == "#" else state


def strip_comments(text: str) -> str:
    # Indexes, not zip(strict=True): that needs Python 3.10.
    context = states(text)
    return "".join(char for index, char in enumerate(text) if context[index] != "#")


def substitutions(text: str) -> list[str]:
    """The commands of each `$(...)` and backtick span outside single quotes; they run even inside double quotes."""
    found = []
    context = states(text)
    index = 0
    while index < len(text):
        if context[index] in {"", '"'} and text.startswith("$(", index):
            end = closing_paren(text, index + 2)
            found.append(text[index + 2 : end])
            index = end
        elif context[index] in {"", '"'} and text[index] == "`":
            end = text.find("`", index + 1)
            end = len(text) if end < 0 else end
            found.append(text[index + 1 : end])
            index = end
        index += 1
    return found


def closing_paren(text: str, start: int) -> int:
    depth = 1
    for index in range(start, len(text)):
        depth += {"(": 1, ")": -1}.get(text[index], 0)
        if depth == 0:
            return index
    return len(text)


def heredoc_start(line: str, context: list[str]) -> re.Match[str] | None:
    """The first `<<WORD` in code: not inside quotes, a comment or `$((...))` arithmetic such as `1<<n`."""
    for match in HEREDOC.finditer(line):
        before = line[: match.start()]
        if not context[match.start()] and before.count("((") <= before.count("))"):
            return match
    return None


def strip_heredocs(text: str) -> str:
    """Drop each heredoc body that is data; keep one that a shell reads as its script (`bash <<EOF`)."""
    kept = []
    delimiter = None
    keep_body = False
    quote = ""
    for line in text.split("\n"):
        if delimiter is not None:
            if line.strip() == delimiter:
                delimiter = None
            elif keep_body:
                kept.append(line)
            continue
        kept.append(line)
        # A quote opened on an earlier line is still open here: `<<EOF` inside it starts no heredoc.
        context, quote = scan(line + "\n", quote)
        match = heredoc_start(line, context)
        if match:
            delimiter = match.group(2)
            keep_body = runs_a_shell(line[: match.start()] + line[match.end() :])
    return "\n".join(kept)


def runs_a_shell(line: str) -> bool:
    """True when any command on the heredoc's line is a shell, which may read the body as its script."""
    commands = [unwrap(words)[1] for pipeline in pipelines(line) for words in pipeline]
    return any(rest and basename(rest[0]) in SHELLS for rest in commands)


def prepare(text: str) -> str:
    return join_continuations(strip_comments(strip_heredocs(text)))


def join_continuations(text: str) -> str:
    return CONTINUATION.sub(r"\1", text)


def pipelines(text: str) -> list[list[list[str]]]:
    """Split shell text into pipelines of simple commands; text inside quotes stays one word."""
    return parse(prepare(text))


def parse(source: str) -> list[list[list[str]]]:
    # A newline ends a command like `;`. Comments are gone already, so a `#` inside a word stays in it.
    # Only a newline in code ends a command: one inside a quoted script stays, so its heredocs still close.
    context = states(source)
    ended = "".join(char + ";" if char == "\n" and not context[index] else char for index, char in enumerate(source))
    lexer = shlex.shlex(ended, posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        pieces = list(lexer)
    except ValueError:
        # An unclosed quote: bash still runs the lines before it, so judge each line that parses on its own.
        lines = source.split("\n")
        return [found for line in lines for found in parse(strip_comments(line))] if len(lines) > 1 else []
    found: list[list[list[str]]] = []
    pipeline: list[list[str]] = []
    words: list[str] = []
    for piece in drop_redirect_targets(pieces):
        if not all(char in PUNCTUATION for char in piece):
            words.append(piece)
            continue
        if not words and piece == ";":
            # The `;` after a newline that follows `|` or `&&` continues that pipeline or list.
            continue
        if words:
            pipeline.append(words)
            words = []
        if "|" not in piece or "||" in piece:
            found.append(pipeline)
            pipeline = []
    pipeline.append(words)
    found.append(pipeline)
    return [[words for words in pipeline if words] for pipeline in found if any(pipeline)]


def drop_redirect_targets(pieces: list[str]) -> list[str]:
    """Drop each redirection (`>`, `2>&1`'s `>&`, `<<<`) and the word after it: the file is not a command."""
    operators = []
    for piece in pieces:
        operators += OPERATOR.findall(piece) if all(char in PUNCTUATION for char in piece) else [piece]
    kept: list[str] = []
    skip = False
    for index, piece in enumerate(operators):
        if skip:
            skip = False
        elif OPERATOR.fullmatch(piece) and ("<" in piece or ">" in piece):
            # `<(cmd)` and `>(cmd)` run cmd: keep the `(`. Otherwise drop the target and a file-descriptor number.
            skip = operators[index + 1 : index + 2] != ["("]
            if skip and kept and kept[-1].isdigit():
                kept.pop()
        else:
            kept.append(piece)
    return kept


def unwrap(words: list[str]) -> tuple[list[str], list[str]]:
    """Split leading assignments and wrappers (sudo, env, xargs ...) off a simple command."""
    assignments = []
    index = 0
    while index < len(words):
        word = words[index]
        if ASSIGNMENT.match(word):
            assignments.append(word)
            index += 1
            continue
        name = basename(word)
        if word in KEYWORDS:
            index += 1
            continue
        if name == "mise" and words[index + 1 : index + 2] in (["exec"], ["x"]) and "--" in words[index:]:
            # `mise exec <tools> -- cmd` runs cmd.
            index = words.index("--", index) + 1
            continue
        if name not in WRAPPERS:
            break
        index, command = after_wrapper(name, words, index + 1)
        if command is not None:
            return assignments, command
    return assignments, words[index:]


def after_wrapper(name: str, words: list[str], index: int) -> tuple[int, list[str] | None]:
    """Skip a wrapper's options: the index of its command, or the command itself when an option holds it."""
    while index < len(words) and words[index].startswith("-"):
        option = words[index]
        if option == "--":
            return index + 1, None
        if name == "command" and option in {"-v", "-V"}:
            # `command -v pkill` looks a name up; it runs nothing.
            return index, []
        if name == "env" and option.startswith("-S") and option != "-S":
            # `env -S"cmd args"` in one word: the rest of the word is the command line.
            return index, [option[2:], *words[index + 1 :]]
        index += 2 if option in WRAPPERS[name] else 1
    # The duration of `timeout` and the lock file of `flock` come before the command.
    return index + (name in {"timeout", "flock"}), None


def shell_script(args: list[str]) -> str | None:
    """The script of `sh -c <script>`, or None when the shell runs a file or stdin."""
    takes_script = False
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in {"-o", "+o", "-O", "+O"}:
            skip = True
        elif arg.startswith(("-", "+")) and not arg.startswith("--"):
            # `-xc` and `+x -c` alike: any short option cluster with `c` makes the next word the script.
            takes_script = takes_script or "c" in arg[1:]
        elif arg.startswith("--"):
            continue
        else:
            return arg if takes_script else None
    return None


def check_text(text: str) -> str | None:
    # Recursion (sh -c, eval, `$(...)`) always works on a strict part of the text, so it ends.
    for pipeline in pipelines(text):
        for words in pipeline:
            message = check_words(words)
            if message:
                return message
    return next((message for span in substitutions(prepare(text)) if (message := check_text(span))), None)


def check_words(words: list[str]) -> str | None:
    assignments, rest = unwrap(words)
    if any(word.startswith("DOPPLER_TOKEN=") for word in assignments):
        return SECRETS.format(command="DOPPLER_TOKEN=...")
    if not rest:
        return None
    if any(char.isspace() for char in rest[0]):
        # A quoted command word such as `env -S "brew install jq"`: the shell splits it again.
        return check_text(" ".join([rest[0], shlex.join(rest[1:])]))
    prog = basename(rest[0])
    args = rest[1:]
    script = inner_script(prog, args)
    if script is not None:
        return check_text(script)
    rules = (rule_fnox, rule_brew, rule_doppler, rule_export, rule_docker, rule_herdr, rule_pkill, rule_pgrep)
    return next((message for rule in rules if (message := rule(prog, args))), None)


def inner_script(prog: str, args: list[str]) -> str | None:
    """The script a command runs as shell text: `sh -c`, `eval`, `su -c`, `script -c` and `mise exec --command`."""
    if prog in SHELLS:
        return shell_script(args)
    if prog == "eval":
        return " ".join(args)
    if prog in {"su", "script"} or (prog == "mise" and args[:1] in (["exec"], ["x"])):
        return command_option(args)
    return None


def command_option(args: list[str]) -> str | None:
    """The script of `su -c <script>` or `mise exec --command <script>`."""
    for index, arg in enumerate(args):
        if arg.startswith("--command="):
            return arg.split("=", 1)[1]
        if arg in {"-c", "--command"}:
            return " ".join(args[index + 1 : index + 2])
    return None


def rule_fnox(prog: str, args: list[str]) -> str | None:
    """The fnox commands that hand an agent a real value: they print it (`get`, `export`, `list --values`, `env`
    without `--describe`), show it (`edit`, `tui`), give it to a command (`exec`), serve it (`mcp` outside the proxy)
    or copy it to another store (`push`). `proxy run` gives placeholders only, so it stays allowed."""
    if prog != "fnox":
        return None
    for index, arg in enumerate(args):
        if index and args[index - 1] in FNOX_VALUE_OPTIONS:
            # A value such as `--profile env` is not a subcommand.
            continue
        if arg == "--" and "proxy" in args[:index]:
            # The command `fnox proxy run --` starts: checked on its own, so `docker exec` there is not `fnox exec`.
            return check_words(args[index + 1 :])
        if arg in FNOX_REVEALING:
            return SECRETS.format(command=f"fnox {arg}")
        if arg == "list" and "--values" in args:
            return SECRETS.format(command="fnox list --values")
        if arg == "env" and "--describe" not in args:
            # `fnox env --json` prints every value; `--describe` lists keys only.
            return SECRETS.format(command="fnox env")
    return None


def rule_brew(prog: str, args: list[str]) -> str | None:
    if prog != "brew":
        return None
    subs = positionals(args)
    if subs and subs[0] in {"install", "reinstall", "upgrade", "tap"}:
        return BREW.format(sub=subs[0])
    if subs[:1] == ["bundle"] and subs[1:2] not in [[read] for read in BREW_BUNDLE_READS]:
        # `brew bundle` and `brew bundle install` install a Brewfile; check, list and dump only read it.
        return BREW.format(sub="bundle")
    return None


def rule_doppler(prog: str, args: list[str]) -> str | None:
    if prog != "doppler":
        return None
    subs = positionals(args)
    if "run" in subs:
        return SECRETS.format(command="doppler run")
    if "secrets" in subs:
        after = subs[subs.index("secrets") + 1 :]
        found = [sub for sub in after if sub in DOPPLER_PRINTS]
        if found:
            # Any position: an option value such as `--project p` sits before the subcommand.
            return SECRETS.format(command=f"doppler secrets {found[0]}")
        if not any(sub in DOPPLER_QUIET for sub in after) and "--only-names" not in args:
            # Bare `doppler secrets` prints every value (doppler 3.77.1 pkg/cmd/secrets.go:169-196).
            return SECRETS.format(command="doppler secrets")
    return None


def rule_export(prog: str, args: list[str]) -> str | None:
    if prog not in {"export", "declare", "typeset"}:
        return None
    if any(arg == "DOPPLER_TOKEN" or arg.startswith("DOPPLER_TOKEN=") for arg in args):
        return SECRETS.format(command=f"{prog} DOPPLER_TOKEN")
    return None


def rule_docker(prog: str, args: list[str]) -> str | None:
    if prog != "docker":
        return None
    subs = positionals(args)
    if "desktop" in subs and subs[subs.index("desktop") + 1 : subs.index("desktop") + 2] == ["update"]:
        return DOCKER_UPDATE
    return None


def rule_herdr(prog: str, args: list[str]) -> str | None:
    if prog != "herdr-app" or "do" not in args:
        return None
    sub = args[args.index("do") + 1 : args.index("do") + 2]
    if sub and sub[0] in {"tab.close", "pane.close"} and not any(a == "--id" or a.startswith("--id=") for a in args):
        return HERDR_CLOSE.format(sub=sub[0])
    return None


def rule_pkill(prog: str, _args: list[str]) -> str | None:
    return PKILL.format(prog=prog) if prog in {"pkill", "killall"} else None


def rule_pgrep(prog: str, args: list[str]) -> str | None:
    if prog != "pgrep":
        return None
    seen_pattern = False
    previous = ""
    for arg in args:
        if arg.startswith("-"):
            if seen_pattern:
                return PGREP
        elif previous not in PGREP_VALUE_OPTIONS:
            seen_pattern = True
        previous = arg
    return None


def is_container_file(path: str) -> bool:
    parts = PurePosixPath(path.replace("\\", "/")).parts
    return is_dockerfile(path) or ".devcontainer" in parts or parts[-1:] == (".devcontainer.json",)


def is_dockerfile(path: str) -> bool:
    """Dockerfile or Containerfile syntax, where a whole `#` line inside a RUN continuation is dropped."""
    parts = PurePosixPath(path.replace("\\", "/")).parts
    name = parts[-1].lower() if parts else ""
    stems = ("dockerfile", "containerfile")
    named = any(name == stem or name.startswith((f"{stem}.", f"{stem}-", f"{stem}_")) for stem in stems)
    return named or name.endswith((".dockerfile", ".containerfile"))


def logical_lines(text: str, *, dockerfile: bool = False) -> list[str]:
    if dockerfile:
        # Docker drops whole comment lines and blank lines before it joins continuations (`RUN a \\` / `# note` / `b`
        # runs `a b`), and a `\\` may be followed by spaces or a CR.
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(line for line in lines if line and not line.lstrip().startswith("#"))
    return [line.strip() for line in join_continuations(text).split("\n") if line.strip()]


def line_commands(line: str) -> list[str]:
    """The shell text in one Dockerfile or devcontainer line: a RUN body, the line itself and its JSON strings."""
    match = DOCKER_RUN.match(line)
    body = match.group(1) if match else line
    found = [body]
    if body.startswith("["):
        try:
            words = json.loads(body)
        except ValueError:
            words = None
        if isinstance(words, list):
            found = [shlex.join(str(word) for word in words)]
    found += [text for literal in JSON_STRING.findall(line) if (text := json_string(literal)) is not None]
    return found


def json_string(literal: str) -> str | None:
    """A double-quoted literal decoded as JSON, or None: in a Dockerfile it is often shell text such as "\\s"."""
    try:
        return json.loads(literal, strict=False)
    except ValueError:
        return None


def check_image_command(command: str) -> bool:
    """True when the command installs something an image must get from mise."""
    if any(check_image_command(span) for span in substitutions(prepare(command))):
        return True
    for pipeline in pipelines(command):
        for index, words in enumerate(pipeline):
            _, rest = unwrap(words)
            if not rest:
                continue
            prog = basename(rest[0])
            args = rest[1:]
            script = shell_script(args) if prog in SHELLS else " ".join(args) if prog == "eval" else None
            if script is not None and (check_image_command(script) or runs_a_download(script)):
                return True
            if prog in APT_PROGRAMS and not apt_allowed(args):
                return True
            later = [unwrap(words)[1] for words in pipeline[index + 1 :]]
            piped_to_shell = any(rest and basename(rest[0]) in SHELLS for rest in later)
            if downloads(prog, args) and piped_to_shell:
                return True
    return False


def downloads(prog: str, args: list[str]) -> bool:
    """curl or wget fetching anything but the mise installer."""
    return prog in {"curl", "wget"} and not (prog == "curl" and positionals(args) == [MISE_INSTALLER])


def runs_a_download(script: str) -> bool:
    """`sh -c "$(curl ...)"` and `eval "$(wget ...)"`: the whole script is a downloaded one."""
    match = WHOLE_SUBSTITUTION.fullmatch(script)
    inner = "".join(group or "" for group in match.groups()) if match else ""
    return any(
        downloads(basename(rest[0]), rest[1:])
        for pipeline in pipelines(inner)
        for words in pipeline
        if (rest := unwrap(words)[1])
    )


def apt_allowed(args: list[str]) -> bool:
    """Only commands that add packages are judged: install may name the bootstrap packages, the rest are blocked."""
    words, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif arg in APT_VALUE_OPTIONS:
            skip = True
        elif not arg.startswith("-"):
            words.append(arg)
    if not words or words[0] not in APT_ADDING:
        return True
    # `curl=7.88.1-10` pins a version of curl.
    return words[0] == "install" and all(word.split("=", 1)[0] in APT_ALLOWED_PACKAGES for word in words[1:])


def check_file_change(path: str, old: str, new: str) -> str | None:
    if not is_container_file(path):
        return None
    dockerfile = is_dockerfile(path)
    before = set(logical_lines(old, dockerfile=dockerfile))
    for line in logical_lines(new, dockerfile=dockerfile):
        if line in before:
            continue
        for command in line_commands(line):
            if check_image_command(command):
                return DOCKERFILE.format(command=command, path=path)
    return None


def read_file(path: str, cwd: str) -> str | None:
    """The file as it is before the change (hooks run first), or None when it cannot be read."""
    try:
        return (Path(cwd) / path).read_text()
    except (OSError, ValueError):
        # No such file yet, or not text: judge the change on its own lines.
        return None


def applied(text: str | None, pairs: list[tuple[str, str]]) -> str | None:
    """The text after replacing each old block with its new one, or None when one is not there."""
    for old, new in pairs:
        if text is None or not old or old not in text:
            return None
        text = text.replace(old, new)
    return text


def in_context(path: str, cwd: str, pairs: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """The whole file before and after, so a line added to a multi-line command is judged with it."""
    before = read_file(path, cwd) if is_container_file(path) else None
    after = applied(before, pairs)
    if before is not None and after is not None:
        return [(path, before, after)]
    return [(path, old, new) for old, new in pairs]


def patch_files(patch: str) -> list[tuple[str, str, list[list[str]]]]:
    """Each file of a Codex apply_patch as (path read, path written, hunks of ` `/`-`/`+` lines)."""
    files: list[tuple[str, str, list[list[str]]]] = []
    for line in patch.split("\n"):
        header = re.match(r"\*\*\* (?:Add|Update|Delete) File: (.+)$", line)
        move = re.match(r"\*\*\* Move to: (.+)$", line)
        if header:
            files.append((header.group(1), header.group(1), [[]]))
        elif not files:
            continue
        elif move:
            files[-1] = (files[-1][0], move.group(1), files[-1][2])
        elif line.startswith("@@"):
            files[-1][2].append([])
        elif line[:1] in {" ", "-", "+"}:
            files[-1][2][-1].append(line)
    return files


def hunk_side(hunk: list[str], sign: str) -> str:
    return "\n".join(line[1:] for line in hunk if line[0] in {" ", sign})


def patch_changes(patch: str, cwd: str) -> list[tuple[str, str, str]]:
    changes = []
    for source, target, hunks in patch_files(patch):
        pairs = [(hunk_side(hunk, "-"), hunk_side(hunk, "+")) for hunk in hunks if hunk]
        text = read_file(source, cwd) if is_container_file(target) else None
        after = applied(text, pairs)
        if text is not None and after is not None:
            # A file moved in from a non-container path is new as a container file: judge every line.
            changes.append((target, text if is_container_file(source) else "", after))
            continue
        lines = [line for hunk in hunks for line in hunk]
        removed = "\n".join(line[1:] for line in lines if line[0] == "-")
        changes.append((target, removed, "\n".join(line[1:] for line in lines if line[0] == "+")))
    return changes


def file_changes(tool: str, tool_input: dict, cwd: str) -> list[tuple[str, str, str]]:
    path = str(tool_input.get("file_path", ""))
    if tool in {"Write", "write_file"}:
        return [(path, "", str(tool_input.get("content", "")))]
    if tool in {"Edit", "replace"}:
        return in_context(path, cwd, [(str(tool_input.get("old_string", "")), str(tool_input.get("new_string", "")))])
    if tool == "MultiEdit":
        edits = tool_input.get("edits")
        edits = edits if isinstance(edits, list) else []
        pairs = [
            (str(edit.get("old_string", "")), str(edit.get("new_string", "")))
            for edit in edits
            if isinstance(edit, dict)
        ]
        return in_context(path, cwd, pairs)
    if tool == "apply_patch":
        return patch_changes(str(tool_input.get("command", "")), cwd)
    return []


def check_payload(payload: dict) -> str | None:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool, str) or not isinstance(tool_input, dict):
        return None
    if tool in SHELL_TOOLS:
        command = tool_input.get("command")
        if isinstance(command, list):
            command = shlex.join(str(word) for word in command)
        return check_text(command) if isinstance(command, str) else None
    cwd = str(payload.get("cwd") or ".")
    for path, old, new in file_changes(tool, tool_input, cwd):
        message = check_file_change(path, old, new)
        if message:
            return message
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        # Not hook JSON: nothing to judge, and a guard must not break the agent's other tools.
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        message = check_payload(payload)
    except Exception as error:  # noqa: BLE001 - any hook bug: block shell commands, let edits through (ruling)
        shell = payload.get("tool_name") in SHELL_TOOLS
        message = HOOK_ERROR.format(error=type(error).__name__) if shell else None
    if message:
        sys.stderr.write(message + "\n")
        return 2
    return 0


# Only ever run as a script (the agents' hook command), never imported.
sys.exit(main())
