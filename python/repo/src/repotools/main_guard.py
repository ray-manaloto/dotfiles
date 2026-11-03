"""The main guard: local main moves only to origin/main, whichever git command moves it."""

# Pattern: mburakyucel/altitude@a57bd2c altitude/git_policy.py:851-895 refuses, in the reference-transaction
# hook's prepared phase, any move of a protected branch except to its origin ref, and lets pack-refs through.
# arxanas/git-branchless@f37244c git-branchless-init/src/lib.rs:74-82 installs that hook to run an executable
# that lives outside the branch. git 2.56.0: refs.c:2663-2679,2723 runs it with the phase as $1 and
# "<old> <new> <ref>" rows on stdin, hook.c:610-626 runs a config hook's command in sh, run-command.c:290-305
# appends "$@". A local record: anyone running as this user can remove the config entry. See AGENTS.md.

import shlex
import subprocess
import sys
from pathlib import Path

from .models import MainGuardInstall

MAIN = "refs/heads/main"
ORIGIN = "refs/remotes/origin/main"
SECTION = "hook.main-guard"
SOURCE = "python/repo"  # The package the install task copies; its tree id says which guard is installed.
REPAIR = "mise run //repo:main-guard-install, or mise run //repo:main-guard-remove to switch the guard off"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, check=True, text=True).stdout


def resolve(ref: str) -> str | None:
    done = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref], capture_output=True, check=False, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def packed(tip: str) -> bool:
    path = Path(git("rev-parse", "--path-format=absolute", "--git-path", "packed-refs").strip())
    return path.is_file() and f"{tip} {MAIN}" in path.read_text().splitlines()


def allowed(old: str, new: str) -> bool:
    current = resolve(MAIN)
    if new == current:
        return True  # pack-refs writes the tip main already has.
    if set(new) == {"0"} and old == current and packed(old):
        return True  # pack-refs --prune drops the loose copy of a tip it just packed.
    return new == resolve(f"{ORIGIN}^{{commit}}")


def check(rows: str) -> None:
    """Refuse unless every row that moves main moves it to origin/main."""
    for row in rows.splitlines():
        match row.split():
            case [old, new, ref] if ref == MAIN and not allowed(old, new):
                expected = resolve(f"{ORIGIN}^{{commit}}") or "missing"
                msg = (
                    f"{MAIN} may move only to {ORIGIN} ({expected[:12]}), not to {new[:12]}: "
                    "merge the pull request on GitHub, git fetch, then git merge --ff-only origin/main"
                )
                raise ValueError(msg)
            case _:
                pass


def command(executable: str) -> str:
    """The hook's one line: only a prepared transaction that names main starts Python; git appends "$@"."""
    # A config hook may leave stdin unread: git ignores the EPIPE (refs.c:2639). grep exits 1 on no match;
    # any other failure, a missing grep or executable included, refuses the transaction that names main.
    # 126 and 127, and only they, are sh's "could not run": a removed copy, or its venv's Python pruned.
    # Say how to repair it; a signal (128 and up) or a refusal (1) keeps git's message alone.
    hint = shlex.quote(f"main guard: {executable} did not start; repair it with {REPAIR}")
    return (
        "g() { test \"$1\" = prepared || return 0; r=$(grep ' refs/heads/main$'); s=$?; "
        'test "$s" = 1 && return 0; test "$s" = 0 || return "$s"; '
        f"printf '%s\\n' \"$r\" | {shlex.quote(executable)} main-guard; s=$?; "
        f'case "$s" in 126|127) echo {hint} >&2;; esac; return "$s"; }}; g'
    )


def install(options: MainGuardInstall) -> None:
    # Self-test: the installed executable must run, outside every checkout, before git calls it.
    subprocess.run([options.bin, "main-guard"], input="", capture_output=True, check=True, text=True)
    # --local is the shared .git/config, so every worktree of this repository gets the hook.
    git("config", "--local", f"{SECTION}.event", "reference-transaction")
    git("config", "--local", f"{SECTION}.command", command(options.bin))
    # The guard's source as HEAD has it: a later move of main to an origin/main with another one warns.
    git("config", "--local", f"{SECTION}.source", resolve(f"HEAD:{SOURCE}") or "none")


def remove() -> None:
    if resolve_config(f"{SECTION}.command") is not None:
        git("config", "--local", "--remove-section", SECTION)


def resolve_config(key: str) -> str | None:
    done = subprocess.run(["git", "config", "--local", "--get", key], capture_output=True, check=False, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def stale() -> None:
    """Warn, never refuse, when origin/main's guard source is not the one installed."""
    installed = resolve_config(f"{SECTION}.source")
    current = resolve(f"{ORIGIN}:{SOURCE}")
    if installed is not None and current is not None and installed != current:
        sys.stderr.write(f"main guard: the installed copy is not origin/main's {SOURCE}; update it with {REPAIR}\n")


def run() -> None:
    stale()
    check(sys.stdin.read())
