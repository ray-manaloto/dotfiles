"""The commit gates: review:python, review:python:approved and privacy:scan."""

# Ported from the shell runs in mise.toml and tasks/privacy/scan.sh (#388) with the same arguments and output.
# Their report and refusal lines stay plain text, as hk and AGENTS.md show them, not JSON events.

import os
import shlex
import subprocess
import sys
from pathlib import Path

from .models import PrivacyScan, ReviewPython
from .pane_approval import git, hashed

PROMPT = Path("tasks/review/python.md")
APPROVING = b"VERDICT: PASS"
REFUSAL = "review:python has not passed on the staged python/ files; stage them, then mise run review:python"
HINT = "privacy:scan: replace each host path with ~ or a {{ env.HOME }} template"
# Short values (a CI runner's HOME, say) would match ordinary text; only real paths are kept.
SHORTEST = 8
# The task always renders /Users/<user>/, 8 characters even for an empty user; a direct call may not.
EMPTY = "privacy:scan: no patterns rendered"
GITLINK = b"160000 "


def staged_python() -> str:
    return hashed(git("ls-files", "-s", "--", "python").encode())


def approval_file() -> Path:
    return Path(git("rev-parse", "--git-path", "review-python.approved").strip())


def review(options: ReviewPython) -> None:
    """Codex reads the prompt and writes its report; a PASS on python/ as staged records that index."""
    out = options.out or git("rev-parse", "--git-path", "review-python.md").strip()
    # Taken before Codex reads, so anything staged during the review stays unapproved.
    staged = staged_python()
    prompt = PROMPT.read_bytes() + f"Path: {options.path}\nCommit: {options.commit or 'none'}\n".encode()
    # One word, as codex's clap parser reads a separate value that starts with - as an option.
    command = ["codex", "exec", "-C", ".", "-c", 'sandbox_mode="read-only"', f"--output-last-message={out}", "-"]
    done = subprocess.run(command, input=prompt, check=False)
    if done.returncode:
        raise SystemExit(done.returncode)
    # Bytes, as tail -n 1 and grep -qx read it: a \\r stays in its line and the report need not be UTF-8.
    lines = Path(out).read_bytes().removesuffix(b"\n").split(b"\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(lines[-1] + b"\n")
    sys.stdout.buffer.flush()
    if APPROVING not in lines:
        raise SystemExit(1)
    # The reviewer also reads unstaged files, so a PASS approves the index only when they match it.
    unstaged = subprocess.run(["git", "diff", "--quiet", "--", "python"], check=False).returncode
    untracked = git("ls-files", "-o", "--exclude-standard", "--", "python")
    if options.path == "python" and options.commit is None and unstaged == 0 and not untracked:
        approval_file().write_text(staged + "\n")


def approved() -> None:
    path = approval_file()
    # Bytes, as $(cat) read it: trailing newlines dropped, a \\r kept, so a CRLF stamp is refused.
    if staged_python().encode() != (path.read_bytes().rstrip(b"\n") if path.exists() else b""):
        sys.stderr.write(REFUSAL + "\n")
        raise SystemExit(1)


def leaks(data: bytes, patterns: list[bytes]) -> list[int]:
    """Line numbers holding a pattern, as grep -n counts them, in any file whatever bytes it holds.

    The shell scan's grep -I skipped a file it took for binary: BSD grep one with a NUL in its first 32 KiB,
    GNU grep by its own rules. A private path is as public in a binary file, so none is skipped.
    """
    return [number for number, line in enumerate(data.split(b"\n"), 1) if any(p in line for p in patterns)]


def given(files: str) -> list[str]:
    """The files hk passes, split as bash's eval split them, at a space, tab or newline only.

    usage-lib quotes a word holding a space, tab or newline but not a \\r, which shlex.split would split at.
    """
    lexer = shlex.shlex(files, posix=True)
    lexer.whitespace_split = True
    lexer.whitespace = " \t\n"
    lexer.commenters = ""
    return list(lexer)


def tracked() -> dict[str, str]:
    """Each tracked name and its staged object, but submodules: their commits belong to another repository.

    Read as bytes: text mode turns a \\r in a name into \\n and stops on a name that is not UTF-8.
    """
    listed = subprocess.run(["git", "ls-files", "-z", "--stage"], capture_output=True, check=True).stdout
    entries = [entry.split(b"\t", 1) for entry in listed.split(b"\0")[:-1]]
    return {os.fsdecode(name): info.split()[1].decode() for info, name in entries if not info.startswith(GITLINK)}


def privacy_scan(options: PrivacyScan) -> None:
    """Report each private path in the given or tracked files, or in each commit not yet on a remote."""
    patterns = [line.encode() for line in options.patterns.split("\n") if len(line) >= SHORTEST]
    if not patterns:
        sys.stderr.write(EMPTY + "\n")
        raise SystemExit(2)
    found: list[str] = []
    if options.outgoing:
        for commit in git("rev-list", "--branches", "--tags", "--not", "--remotes").split():
            # git show prints the patch too, so a path added or removed in the diff counts.
            shown = subprocess.run(
                ["git", "show", "--format=%an <%ae>%n%cn <%ce>%n%B", commit], capture_output=True, check=True
            ).stdout
            if any(p in shown for p in patterns):
                summary = git("log", "-1", "--format=%h %s", commit).rstrip("\n")
                found.append(f"commit {summary} holds a private path")
    else:
        staged = {} if options.files else tracked()
        for name in given(options.files) if options.files else staged:
            if Path(name).is_file():
                data = Path(name).read_bytes()
            elif name in staged:
                # Gone from the working tree, or a name this disk refuses (macOS one not in UTF-8): read what git holds.
                data = subprocess.run(["git", "cat-file", "blob", staged[name]], capture_output=True, check=True).stdout
            else:
                continue
            found.extend(f"{name}:{n} holds a private path" for n in leaks(data, patterns))
    if found:
        # Bytes, so a name that is not UTF-8 is printed as git stores it.
        sys.stderr.flush()
        lines = [f"privacy:scan: {line}" for line in found] + [HINT]
        sys.stderr.buffer.write(b"".join(os.fsencode(line + "\n") for line in lines))
        raise SystemExit(1)
