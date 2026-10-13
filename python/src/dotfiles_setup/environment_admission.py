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

_HEAD = re.compile(
    r"(?:^|[;&|\n]\s*)\s*"
    r"(?:(?:command|builtin|exec|nohup|time)\s+|\w+=\S+\s+)*"
    r"(?P<command>['\"]?(?:[^\s;&|]*/)?"
    r"(?:env|printenv|set|export|declare|typeset|bash|sh|zsh|dash|"
    r"python[\d.]*|node|cat))['\"]?(?=$|[\s;&|>])"
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


def _env_broad(args: list[str]) -> bool:
    option_and_value = 2
    while args:
        option = args[0]
        if option in {"-u", "--unset", "-C", "--chdir"}:
            if len(args) < option_and_value:
                return False
            args = args[option_and_value:]
        elif (
            option in {"-i", "--ignore-environment", "-0", "--null", "--"}
            or option.startswith("--unset=")
            or re.match(r"^[A-Za-z_]\w*=", option)
        ):
            args = args[1:]
        else:
            break
    return not args or _broad(args)


def _interpreter_broad(name: str, args: list[str]) -> bool:
    if name in {"sh", "bash", "zsh", "dash"} and "-c" in args:
        index = args.index("-c") + 1
        return index < len(args) and decide(args[index]) is not None
    if re.fullmatch(r"python[\d.]*", name) and "-c" in args:
        index = args.index("-c") + 1
        if index < len(args):
            return _python_stdout(args[index])
    if name == "node" and any(arg in {"-e", "--eval", "-p", "--print"} for arg in args):
        return any(_NODE_STDOUT.search(arg) for arg in args)
    if name == "cat":
        return any(_PROC_ENVIRON.fullmatch(arg) for arg in args)
    return False


def _broad(argv: list[str]) -> bool:
    if not argv:
        return False
    name, *args = argv
    name = name.rsplit("/", 1)[-1]
    if any(arg in {"--help", "--version"} for arg in args):
        return False
    if name == "env":
        return _env_broad(args)
    if name in {"printenv", "set"}:
        return not [
            arg for arg in args if name == "set" or arg not in {"-0", "--null", "--"}
        ]
    if name in {"export", "declare", "typeset"}:
        return all(re.fullmatch(r"-[px]+", arg) for arg in args)
    return _interpreter_broad(name, args)


def decide(command: str) -> str | None:
    """Return a value-free denial reason for a literal broad environment dump."""
    if any(decide(body) for body in hook_guard.literal_command_substitutions(command)):
        return DENY_REASON
    target, _ = hook_guard.command_views(command)
    for match in _HEAD.finditer(target):
        end = re.search(r"[;&|\n>]", target[match.start("command") :])
        stop = match.start("command") + end.start() if end else len(command)
        try:
            argv = shlex.split(command[match.start("command") : stop], comments=True)
        except ValueError:
            continue
        if _broad(argv):
            return DENY_REASON
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
