"""The commit gates: review:python, review:python:approved and privacy:scan."""

# Ported from the shell runs in mise.toml and tasks/privacy/scan.sh (#388) with the same arguments and output.
# Their report and refusal lines stay plain text, as hk and AGENTS.md show them, not JSON events.

import shlex
import subprocess
import sys
from pathlib import Path

from .models import PrivacyScan, ReviewPython
from .pane_approval import git, hashed

PROMPT = Path("tasks/review/python.md")
APPROVING = "VERDICT: PASS"
REFUSAL = "review:python has not passed on the staged python/ files; stage them, then mise run review:python"
HINT = "privacy:scan: replace each host path with ~ or a {{ env.HOME }} template"
# Short values (a CI runner's HOME, say) would match ordinary text; only real paths are kept.
SHORTEST = 8
# The task always renders /Users/<user>/, 8 characters even for an empty user; a direct call may not.
EMPTY = "privacy:scan: no patterns rendered"


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
    command = ["codex", "exec", "-C", ".", "-c", 'sandbox_mode="read-only"', "-o", out, "-"]
    done = subprocess.run(command, input=prompt, check=False)
    if done.returncode:
        raise SystemExit(done.returncode)
    lines = Path(out).read_text().removesuffix("\n").split("\n")
    sys.stdout.write(lines[-1] + "\n")
    if APPROVING not in lines:
        raise SystemExit(1)
    # The reviewer also reads unstaged files, so a PASS approves the index only when they match it.
    unstaged = subprocess.run(["git", "diff", "--quiet", "--", "python"], check=False).returncode
    untracked = git("ls-files", "-o", "--exclude-standard", "--", "python")
    if options.path == "python" and options.commit is None and unstaged == 0 and not untracked:
        approval_file().write_text(staged + "\n")


def approved() -> None:
    path = approval_file()
    if staged_python() != (path.read_text().rstrip("\n") if path.exists() else ""):
        sys.stderr.write(REFUSAL + "\n")
        raise SystemExit(1)


def leaks(data: bytes, patterns: list[bytes]) -> list[int]:
    """Line numbers holding a pattern, as grep -n counts them; a file with a NUL byte is binary and skipped (-I)."""
    if b"\0" in data:
        return []
    return [number for number, line in enumerate(data.split(b"\n"), 1) if any(p in line for p in patterns)]


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
        names = shlex.split(options.files) if options.files else git("ls-files", "-z").split("\0")[:-1]
        for name in names:
            if Path(name).is_file():
                found.extend(f"{name}:{n} holds a private path" for n in leaks(Path(name).read_bytes(), patterns))
    if found:
        sys.stderr.writelines(f"privacy:scan: {line}\n" for line in found)
        sys.stderr.write(HINT + "\n")
        raise SystemExit(1)
