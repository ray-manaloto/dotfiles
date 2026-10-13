# Copyright (c) 2026 Raymond Manaloto
"""Narrow admission for literal broad environment stdout, never a shell sandbox.

The guard inspects command text only; it never reads environment values or runs
the proposed command. Native hook activation and exact-client qualification are
separate from this source policy. Dynamic aliases and encoded programs are out
of scope.
"""

from __future__ import annotations

import ast
import json
import re
import shlex
import sys

from dotfiles_setup import hook_guard

DENY_REASON = (
    "Do not print the broad environment: stdout enters the command transcript. "
    "Use a named-variable presence-only check that emits SET/ABSENT, or "
    "`printenv NAME >/dev/null` and read its exit status. Environment prefixes "
    "such as `env -u NAME command` remain allowed."
)
SPLIT_REASON = (
    "Cannot inspect unsupported env -S syntax; use literal words with "
    "balanced quotes and ASCII space/tab separators."
)
OPTION_REASON = "Cannot inspect unsupported env option syntax."
INTERPRETER_OPTION_REASON = "Cannot inspect unsupported interpreter option syntax."
_PYTHON_FLAGS = frozenset(
    {
        "-b",
        "-bb",
        "-B",
        "-d",
        "-E",
        "-i",
        "-I",
        "-O",
        "-OO",
        "-P",
        "-q",
        "-s",
        "-S",
        "-u",
        "-v",
        "-vv",
        "-x",
    }
)
_PYTHON_HELP = frozenset(
    {
        "-h",
        "-?",
        "--help",
        "--help-env",
        "--help-xoptions",
        "--help-all",
        "-V",
        "-VV",
        "--version",
    }
)

_HEAD = re.compile(
    r"(?:^|[;&|\n]\s*)\s*"
    r"(?:(?:command|builtin|exec|nohup|time)\s+|\w+=\S+\s+)*"
    r"(?P<command>['\"]?(?:[^\s;&|]*/)?"
    r"(?:env|printenv|set|export|declare|typeset|bash|sh|zsh|dash|"
    r"python[\d.]*|node|cat))['\"]?(?=$|[\s;&|<>])"
)
_NODE_STDOUT = re.compile(
    r"(?:console\.(?:log|dir)|(?:process\.)?stdout\.write)\s*\("
    r"\s*(?:JSON\.stringify\s*\(\s*)?process\.env\s*[),]"
)
_PROC_ENVIRON = re.compile(r"/proc/(?:self|\d+|\$\$|\$\w+)/environ$")
SHELL_TOOLS = frozenset(
    {"Bash", "shell", "shell_command", "exec_command", "functions.exec_command"}
)


def _python_stdout(code: str) -> bool:
    """Use Python's native AST for literal collection prints, without imports."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if ast.unparse(node.func) not in {
            "print",
            "pprint",
            "pprint.pprint",
            "sys.stdout.write",
        }:
            continue
        if any(_python_collection(arg) for arg in node.args):
            return True
    return False


def _python_collection(node: ast.expr) -> bool:
    if isinstance(node, ast.Attribute):
        return ast.unparse(node) == "os.environ"
    if isinstance(node, ast.IfExp):
        return _python_collection(node.body) or _python_collection(node.orelse)
    if isinstance(node, ast.Call):
        function = ast.unparse(node.func)
        if function in {
            "os.environ.copy",
            "os.environ.items",
            "os.environ.keys",
            "os.environ.values",
        }:
            return True
        if function in {
            "dict",
            "list",
            "tuple",
            "sorted",
            "str",
            "repr",
            "json.dumps",
            "pprint.pformat",
        }:
            return any(_python_collection(arg) for arg in node.args)
    return False


def _env_split(args: list[str]) -> list[str] | None:
    option, *remaining = args
    if option == "-S":
        if not remaining:
            return None
        split, *remaining = remaining
    else:
        split = option[2:]
    if any(char in split for char in "\\$#") or any(
        char.isspace() and char not in " \t" for char in split
    ):
        return None
    try:
        return shlex.split(split) + remaining
    except ValueError:
        return None


def _env_reason(args: list[str]) -> str | None:
    option_and_value = 2
    while args:
        option = args[0]
        if option == "--":
            args = args[1:]
            break
        if option in {"--help", "--version"}:
            return None
        if option.startswith("-S"):
            expanded = _env_split(args)
            if expanded is None:
                return SPLIT_REASON
            args = expanded
            continue
        if option in {"-u", "--unset", "-C", "--chdir", "-P"}:
            if len(args) < option_and_value:
                return None
            args = args[option_and_value:]
        elif (
            option in {"-", "--ignore-environment", "--null"}
            or re.fullmatch(r"-[0iv]+", option)
            or option.startswith(("--unset=", "--chdir="))
            or re.fullmatch(r"-[uCP].+", option)
        ):
            args = args[1:]
        elif option.startswith("-"):
            return OPTION_REASON
        else:
            break
    return _env_utility_reason(args)


def _env_utility_reason(args: list[str]) -> str | None:
    while args and re.match(r"^[A-Za-z_]\w*=", args[0]):
        args = args[1:]
    return _reason(args) if args else DENY_REASON


def _shell_code(args: list[str]) -> str | None:
    """Find a command in native short-option clusters before a script path."""
    skip_value = False
    for index, option in enumerate(args):
        if skip_value:
            skip_value = False
            continue
        if option in {"--", "--help", "--version"} or not option.startswith(("-", "+")):
            break
        if option in {"-o", "+o", "--rcfile", "--init-file"}:
            skip_value = True
        elif re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", option):
            return args[index + 1] if index + 1 < len(args) else None
    return None


def _node_print_collection(code: str) -> bool:
    """Recognize literal collection expressions that Node print mode emits."""
    expression = code.strip().removesuffix(";").strip()
    while expression.startswith("(") and expression.endswith(")"):
        expression = expression[1:-1].strip()
    return (
        re.fullmatch(r"process\.env|JSON\.stringify\(\s*process\.env\s*\)", expression)
        is not None
    )


def _node_stdout(code: str) -> bool:
    target = code
    if not any(char in code for char in "\\`/") and code.splitlines() == [code]:
        try:
            shlex.split(code, posix=True, comments=False)
        except ValueError:
            pass
        else:
            target = hook_guard.command_views(code)[1]
    return _NODE_STDOUT.search(target) is not None


def _node_reason(args: list[str]) -> str | None:
    while args:
        option, *remaining = args
        if option in {
            "--",
            "-",
            "-h",
            "--help",
            "-v",
            "--version",
        } or not option.startswith("-"):
            return None
        if option == "--trace-warnings":
            args = remaining
            continue
        flag, separator, attached = option.partition("=")
        if flag not in {"-e", "--eval", "-p", "--print", "-r", "--require"}:
            return INTERPRETER_OPTION_REASON
        if separator:
            code = attached
        elif remaining:
            code, *remaining = remaining
        else:
            return None
        if flag in {"-r", "--require"}:
            args = remaining
            continue
        broad = _node_stdout(code) or (
            flag in {"-p", "--print"} and _node_print_collection(code)
        )
        return DENY_REASON if broad else None
    return None


def _python_reason(args: list[str]) -> str | None:
    while args:
        option, *remaining = args
        if (
            option in {"--", "-", "-m"}
            or option in _PYTHON_HELP
            or not option.startswith("-")
        ):
            return None
        if option == "-c":
            return DENY_REASON if remaining and _python_stdout(remaining[0]) else None
        if option in {"-W", "-X", "--check-hash-based-pycs"}:
            args = remaining[1:]
        elif option in _PYTHON_FLAGS or option.startswith(("-W", "-X")):
            args = remaining
        else:
            return INTERPRETER_OPTION_REASON
    return None


def _interpreter_reason(name: str, args: list[str]) -> str | None:
    if re.fullmatch(r"python[\d.]*", name):
        return _python_reason(args)
    if name == "node":
        return _node_reason(args)
    if name == "cat" and any(_PROC_ENVIRON.fullmatch(arg) for arg in args):
        return DENY_REASON
    return None


def _reason(argv: list[str]) -> str | None:
    if not argv:
        return None
    name, *args = argv
    name = name.rsplit("/", 1)[-1]
    if args and args[0] in {"--help", "--version"}:
        return None
    if name == "env":
        return _env_reason(args)
    if name in {"sh", "bash", "zsh", "dash"}:
        code = _shell_code(args)
        return decide(code) if code is not None else None
    if name in {"printenv", "set"}:
        broad = not [
            arg for arg in args if name == "set" or arg not in {"-0", "--null", "--"}
        ]
    elif name in {"export", "declare", "typeset"}:
        broad = all(re.fullmatch(r"-[px]+", arg) for arg in args)
    else:
        return _interpreter_reason(name, args)
    return DENY_REASON if broad else None


def decide(command: str) -> str | None:
    """Return a value-free denial reason for a literal broad environment dump."""
    command = hook_guard.normalize_shell_continuations(command)
    for body in hook_guard.literal_command_substitutions(command):
        if reason := decide(body):
            return reason
    target, _ = hook_guard.command_views(command)
    for match in _HEAD.finditer(target):
        end = re.search(
            r"[;&|\n]|(?<!\S)\d*[<>]|[<>]", target[match.start("command") :]
        )
        stop = match.start("command") + end.start() if end else len(command)
        try:
            argv = shlex.split(command[match.start("command") : stop], comments=True)
        except ValueError:
            continue
        if reason := _reason(argv):
            return reason
    return None


def decide_payload(payload: dict[str, object]) -> str | None:
    """Admit shell-like native PreToolUse payloads; ignore unrelated tools."""
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        return "Environment admission requires a valid tool identity."
    if tool_name not in SHELL_TOOLS:
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return "Environment admission cannot inspect the shell tool input."
    command = tool_input.get("command", tool_input.get("cmd"))
    if not isinstance(command, str):
        return "Environment admission requires a literal shell command string."
    return decide(command)


def pretooluse_main() -> int:
    """Emit native deny JSON or a silent neutral result; never run tool input."""
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        payload = None
    reason = (
        decide_payload(payload)
        if isinstance(payload, dict)
        else "Environment admission requires a valid hook payload."
    )
    if reason:
        sys.stdout.write(hook_guard.deny_output(reason))
    return 0
