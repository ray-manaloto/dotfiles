"""The zero-bash rule: find shell scripts, shell shebangs and multi-line mise run in the git index."""

# Pattern: Mbed-TLS/mbedtls-framework@ced31491 scripts/check_files.py:156-187,525 walks `git ls-files`
# and matches each first line with a shebang regex beside a path-exemption regex. This reads the index
# (`git ls-files -s`, `git cat-file --batch`), the snapshot a commit certifies, not the working tree.

import re
import shlex
import subprocess
import sys
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import cast

import tomlkit
from tomlkit.items import String

from . import process
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
FILE_MODES = ("100644", "100755")  # Links (120000) and submodules (160000) have no content to read.


def allowed(path: str) -> bool:
    return any(PurePosixPath(path).full_match(pattern) for pattern in ALLOWED)


def git(*args: str, stdin: bytes | None = None) -> bytes:
    if stdin is None:
        return subprocess.run(["git", *args], capture_output=True, check=True).stdout
    # This call keeps the helper's default capture_stdout=True.
    return cast("bytes", process.run(["git", *args], stdin).stdout)


def index() -> list[tuple[str, str, str]]:
    """Mode, blob id and path of every index entry; :/ and --full-name list them all from any folder."""
    found = []
    for entry in git("ls-files", "-s", "-z", "--full-name", ":/").decode().split("\0")[:-1]:
        meta, path = entry.split("\t", 1)
        mode, blob, _stage = meta.split()
        found.append((mode, blob, path))
    return found


def blobs(ids: list[str]) -> dict[str, bytes]:
    """The content of each blob, read from the object store in one git call."""
    out = git("cat-file", "--batch", stdin="".join(f"{blob}\n" for blob in ids).encode())
    found: dict[str, bytes] = {}
    start = 0
    for _ in ids:
        header_end = out.index(b"\n", start)
        blob, _kind, size = out[start:header_end].decode().split()
        body = header_end + 1
        found[blob] = out[body : body + int(size)]
        start = body + int(size) + 1
    return found


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


def findings() -> list[Finding]:
    entries = index()
    content = blobs([blob for mode, blob, _path in entries if mode in FILE_MODES])
    return [
        finding
        for mode, blob, path in entries
        for finding in check_entry(path, content[blob] if mode in FILE_MODES else None)
    ]


def report(options: ZeroBash) -> None:
    """Print every finding; --strict fails on any."""
    found = findings()
    sys.stdout.writelines(finding.model_dump_json() + "\n" for finding in found)
    if options.strict and found:
        raise SystemExit(1)
