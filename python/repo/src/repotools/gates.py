"""The commit gates: review:python, review:python:approved, privacy:scan, toolchain-gate and herdr-gate."""

# Ported from the shell runs in mise.toml and tasks/privacy/scan.sh (#388) with the same arguments and output.
# Their report and refusal lines stay plain text, as hk and AGENTS.md show them, not JSON events.

import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

from .git import git
from .models import HerdrGate, PrivacyScan, ReviewApproved, ReviewPython, ToolchainGate
from .pane_approval import hashed

PROMPT = Path("tasks/review/python.md")
APPROVING = b"VERDICT: PASS"
# The review lead and the 6 slice reviewers it runs at once (tasks/review/python.md).
THREADS = 7
REFUSAL = "review:python has not passed on the staged python/ files; stage them, then mise run review:python"
HINT = "privacy:scan: replace each host path with ~ or a {{ env.HOME }} template"
# Short values (a CI runner's HOME, say) would match ordinary text; only real paths are kept.
SHORTEST = 8
# The task always renders /Users/<user>/, 8 characters even for an empty user; a direct call may not.
EMPTY = "privacy:scan: no patterns rendered"
GITLINK = b"160000 "
# What toolchain:verify runs from (#391): the hometools package and the two file tasks, by any change, deletion
# included, and the global config by a change that the toolchain tasks can see.
TOOLCHAIN_PATHS = (
    "python/home/",
    "unix/home/.config/mise/tasks/toolchain/",
    "unix/home/.config/mise/tasks/bootstrap/",
)
GLOBAL_CONFIG = "unix/home/.config/mise/config.toml"
# What hk's herdr step tests (//home:herdr-unit): the doctor's task folder, hc-safe, the doctor, its two test files,
# the /verify section the contract test reads and the package's tasks, by any change, deletion included.
HERDR_PATHS = (
    "unix/home/.config/mise/tasks/herdr/",
    "unix/home/.local/bin/hc-safe",
    "python/home/src/hometools/herdr.py",
    "python/home/tests/test_herdr_",
    ".claude/skills/verify/SKILL.md",
    "python/home/mise.toml",
)
# The [tools] pins the toolchain tasks run with; a bump of any other pin leaves what toolchain:verify sees alone.
TASK_TOOLS = frozenset({"uv", "python", "mise", "hk"})


def staged_python() -> str:
    return hashed(git("ls-files", "-s", "--", "python").encode())


def approval_file() -> Path:
    return Path(git("rev-parse", "--git-path", "review-python.approved").strip())


def merged_in(path: str) -> list[str]:
    """Files under path only main changed and the merge leaves as main has them; the rest stay in the review."""
    # Not a merge, or one of a commit origin/main does not hold, exits non-zero: then nothing is left out.
    reviewed = ["git", "merge-base", "--is-ancestor", "MERGE_HEAD", "origin/main"]
    if subprocess.run(reviewed, capture_output=True, check=False).returncode:
        return []
    # The working tree, as the reviewer reads git diff HEAD. Quoted as git quotes a name in that diff, so a
    # newline, quote or byte that is not ASCII is escaped and one name cannot pose as another Merged: line.
    ours, main = (
        set(git("-c", "core.quotePath=true", "diff", "--name-only", "--no-renames", side, "--", path).splitlines())
        for side in ("HEAD", "MERGE_HEAD")
    )
    # A file the branch's own commits changed stays in, even resolved to main's side: dropping the branch's
    # change is a decision of this merge (pre-commit/pre-commit pre_commit/git.py keeps conflicted files too).
    # So does an earlier merge's: --diff-merges=separate lists its files against each parent, and --sparse keeps
    # one that matches the branch parent, as when it rejected main's change (git revision.c, dense mode).
    log = ["log", "--format=", "--name-only", "--no-renames", "--diff-merges=separate", "--sparse"]
    log += ["HEAD", "^MERGE_HEAD", "--", path]
    branch = set(git("-c", "core.quotePath=true", *log).splitlines())
    return sorted(ours - main - branch)


def review(options: ReviewPython) -> None:
    """Codex reads the prompt and writes its report; a PASS on python/ as staged records that index."""
    out = options.out or git("rev-parse", "--git-path", "review-python.md").strip()
    # Taken before Codex reads, so anything staged during the review stays unapproved.
    staged = staged_python()
    prompt = PROMPT.read_bytes() + f"Path: {options.path}\nCommit: {options.commit or 'none'}\n".encode()
    if options.commit is None:
        prompt += "".join(f"Merged: {name}\n" for name in merged_in(options.path)).encode()
    # One word, as codex's clap parser reads a separate value that starts with - as an option.
    # multi_agent_v2 counts the lead in its thread total (default 4), and this override merges with a
    # plain `multi_agent_v2 = true` in config.toml (codex-rs/config/src/merge.rs:63-98 at rust-v0.167.0).
    command = [
        "codex",
        "exec",
        "-C",
        ".",
        "-c",
        'sandbox_mode="read-only"',
        "-c",
        'approval_policy="never"',
        "-c",
        f"features.multi_agent_v2.max_concurrent_threads_per_session={THREADS}",
        f"--output-last-message={out}",
        "-",
    ]
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


def global_config(tree: str) -> dict[str, object]:
    """The global config, parsed, in tree (HEAD, or "" for the index), with only the task tools' [tools] pins:
    comments, layout and the other pins drop out. Absent is empty; one that does not parse raises."""
    listed = git("ls-tree", "--name-only", tree, "--", GLOBAL_CONFIG) if tree else git("ls-files", "--", GLOBAL_CONFIG)
    if not listed:
        return {}
    config = tomllib.loads(git("show", f"{tree}:{GLOBAL_CONFIG}"))
    tools = config.get("tools", {})
    return config | {"tools": {name: pin for name, pin in tools.items() if name in TASK_TOOLS}}


def toolchain_gate() -> None:
    """run on stdout when the staged change reaches what toolchain:verify runs from; the reason otherwise."""
    # Printed, not an exit status, as main-guard-armed: a failing check must never read as "skip".
    # Any [vars] change runs: //home:integration is the only test that compares the [vars] toolchain versions
    # with this Mac's install (the unit tests take theirs from the install), so a bump fails until installed.
    changed = staged_paths()
    if any(path.startswith(TOOLCHAIN_PATHS) for path in changed) or (
        GLOBAL_CONFIG in changed and global_config("HEAD") != global_config("")
    ):
        sys.stdout.write("run\n")
    else:
        sys.stderr.write("toolchain-gate: nothing the toolchain tasks run from is staged; //home:check skipped\n")


def staged_paths() -> list[str]:
    """Every path the staged change touches. --no-renames: a rename is its old path deleted and its new one added,
    so both are seen."""
    return git("diff", "--cached", "--name-only", "--no-renames", "-z").split("\0")


def herdr_gate() -> None:
    """run on stdout when the staged change reaches what //home:herdr-unit tests; the reason otherwise."""
    # Printed, not an exit status, as toolchain-gate: a failing check must never read as "skip".
    if any(path.startswith(HERDR_PATHS) for path in staged_paths()):
        sys.stdout.write("run\n")
    else:
        sys.stderr.write(
            "herdr-gate: nothing the herdr doctor or hc-safe runs from is staged; //home:herdr-unit skipped\n"
        )


def dispatch(options: ReviewPython | ReviewApproved | PrivacyScan | ToolchainGate | HerdrGate) -> None:
    match options:
        case ReviewPython():
            review(options)
        case ReviewApproved():
            approved()
        case PrivacyScan():
            privacy_scan(options)
        case ToolchainGate():
            toolchain_gate()
        case _:  # HerdrGate
            herdr_gate()
