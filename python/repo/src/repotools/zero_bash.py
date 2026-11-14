"""The zero-bash rule: find shell scripts, shell shebangs and multi-line mise run in the files given."""

# Pattern: Mbed-TLS/mbedtls-framework@ced31491 scripts/check_files.py:156-187,525 walks `git ls-files`
# and matches each first line with a shebang regex beside a path-exemption regex. hk's pre-commit passes the
# staged files and stashes unstaged work first, so the working tree it reads is what the commit holds.

import re
import shlex
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

import tomlkit
from tomlkit.items import String

from .gates import given
from .models import Finding, Rule, ZeroBash

SHELL_SUFFIXES = (".sh", ".bash", ".zsh", ".ksh", ".csh", ".fish")
SHELLS = frozenset({"sh", "bash", "dash", "ash", "ksh", "mksh", "pdksh", "zsh", "csh", "tcsh", "fish", "yash", "posh"})
# Launchers that run the program their next word names: env, and busybox applets.
LAUNCHERS = frozenset({"env", "busybox"})
# env options that take the next word as their value.
ENV_VALUED = frozenset({"-u", "--unset", "-C", "--chdir", "-P", "--default-signal", "--block-signal"})
# A backslash ending a line inside a basic multi-line string: TOML drops it with the newline, so the
# parsed value holds one line. An even run of backslashes before it is escaped backslashes instead.
CONTINUATION = re.compile(r"(?<!\\)(?:\\\\)*\\[ \t]*\r?\n")
# The zsh startup files: zsh reads them itself, so no other language can hold them.
ALLOWED = (
    "unix/home/.zshenv",
    "unix/home/.config/zsh/.zprofile",
    "unix/home/.config/zsh/.zshrc",
    "unix/home/.config/zsh/.zshrc.d/*.zsh",
    "unix/home/.config/zsh/*.zsh",
)


def allowed(path: str) -> bool:
    return any(PurePosixPath(path).full_match(pattern) for pattern in ALLOWED)


def interpreter(first: bytes) -> str | None:
    """The program a shebang line runs, past env, busybox and env's options; None without a shebang."""
    if not first.startswith(b"#!"):
        return None
    words = first[2:].decode(errors="replace").split()
    while words:
        program = PurePosixPath(words.pop(0)).name
        if program not in LAUNCHERS:
            return program
        while words and (words[0].startswith("-") or "=" in words[0]):
            option = words.pop(0)
            if option in ENV_VALUED and words:
                words.pop(0)
            elif option.startswith("-S"):  # the rest is one string env splits itself; -S/bin/sh joins on
                words = split_string(" ".join([option.removeprefix("-S"), *words]))
    return None


def split_string(text: str) -> list[str]:
    """env -S's split: quotes and backslash escapes as POSIX shlex reads them, and \\_ as a space.

    Checked against /usr/bin/env -S runs: a quoted program, a quoted VAR="two words", \\_ between words
    and inside double quotes, \\_ kept inside single quotes. A quote env cannot close is a ValueError.
    """
    out: list[str] = []
    quote = ""
    at = 0
    while at < len(text):
        pair = text[at : at + 2]
        if quote != "'" and pair.startswith("\\") and len(pair) == len("\\_"):
            out.append(" " if pair == "\\_" else pair)
            at += len(pair)
            continue
        if text[at] in "'\"" and quote in ("", text[at]):
            quote = "" if quote else text[at]
        out.append(text[at])
        at += 1
    return shlex.split("".join(out))


def run_values(node: object, key: str = "") -> Iterator[tuple[str, String]]:
    """Each string a `run` key holds, alone or in its list, under any table, with its dotted key."""
    if isinstance(node, dict):
        for name, value in node.items():
            where = f"{key}.{name}" if key else str(name)
            if name == "run":
                entries = value if isinstance(value, list) else [value]
                yield from ((where, entry) for entry in entries if isinstance(entry, String))
            yield from run_values(value, where)
    elif isinstance(node, list):
        for number, value in enumerate(node):
            yield from run_values(value, f"{key}[{number}]")


def multi_line(value: String) -> bool:
    """More than one line once parsed, or joined into one by a line-ending backslash in the source."""
    raw = value.as_string()
    return "\n" in value.strip() or (raw.startswith('"""') and CONTINUATION.search(raw) is not None)


def check_entry(path: str, content: bytes | None) -> list[Finding]:
    """The entry's findings; a shebang or TOML file that can't be read stops the run, naming the file."""
    try:
        return list(check_content(path, content))
    except ValueError as error:  # shlex's, tomlkit's and UTF-8 decoding's errors, re-raised for main()
        msg = f"{path}: {error}"
        raise ValueError(msg) from error


def check_content(path: str, content: bytes | None) -> Iterator[Finding]:
    if not allowed(path) and (suffix := PurePosixPath(path).suffix) in SHELL_SUFFIXES:
        yield Finding(path=path, rule=Rule.shell_file, detail=suffix)
    if content is None:  # A link or a submodule: only its name can break the rule.
        return
    first = content.split(b"\n", 1)[0].rstrip()
    if not allowed(path) and interpreter(first) in SHELLS:
        yield Finding(path=path, rule=Rule.shell_shebang, detail=first.decode(errors="replace"))
    if path.endswith(".toml"):
        for where, value in run_values(tomlkit.parse(content.decode())):
            if multi_line(value):
                yield Finding(path=path, rule=Rule.multi_line_run, detail=where)


def content(path: Path) -> bytes | None:
    """The file's bytes; None for a link or a folder (a submodule), whose name alone can break the rule."""
    return None if path.is_symlink() or path.is_dir() else path.read_bytes()


def findings(files: list[str]) -> list[Finding]:
    """The given files' findings, or with none given every tracked file's, as the working tree holds it."""
    names = (
        files
        or subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout.decode().split("\0")[:-1]
    )
    return [
        finding
        for name in names
        if Path(name).is_symlink() or Path(name).exists()  # hk drops deleted files; ls-files lists them
        for finding in check_entry(name, content(Path(name)))
    ]


def report(options: ZeroBash) -> None:
    """Print every finding in the given files, or in every tracked file; --strict fails on any."""
    found = findings(given(options.files))
    sys.stdout.writelines(finding.model_dump_json() + "\n" for finding in found)
    if options.strict and found:
        raise SystemExit(1)
