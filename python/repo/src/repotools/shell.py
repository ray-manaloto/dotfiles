"""shell:apply and shell:rollback: link the zsh startup files after a private backup, and put it back."""

# The first apply that links keeps the backup as pre-apply; a later one keeps it as replaced-<time>, and a
# repeat with nothing to change makes neither. A rollback restores pre-apply byte for byte (a path it lacks did
# not exist then, so it goes), after moving what was live to replaced-<time>. The XDG history stays: it holds
# commands newer than the backup.

import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from .models import ShellApply, ShellRollback

# Named, because a whole-config apply would also repoint ~/.zshrc.d/60-agent-tools.zsh at this checkout. The
# tilde stays literal: mise matches the raw keys of [dotfiles].
TARGETS = (
    "~/.zshenv",
    "~/.zprofile",
    "~/.zshrc",
    "~/.zshrc.d/10-zsh.zsh",
    "~/.zshrc.d/90-mise.zsh",
    "~/.config/zsh/path.zsh",
)
PRIVATE = 0o700
PARTIAL = os.O_WRONLY | os.O_CREAT | os.O_EXCL


def backup_paths(task: str) -> list[str]:
    """The paths, relative to $HOME, that the root mise.toml's shell_backup_paths var lists."""
    paths = os.environ.get("SHELL_BACKUP_PATHS", "").split()
    if not paths:
        msg = f"SHELL_BACKUP_PATHS is not set; run this through: mise run {task}"
        raise ValueError(msg)
    return paths


def xdg(name: str, fallback: str) -> Path:
    return Path(os.environ.get(name) or Path.home() / fallback)


def backups() -> Path:
    return xdg("XDG_STATE_HOME", ".local/state") / "dotfiles/shell-backup"


def replaced_name() -> str:
    """replaced-<time>, as /bin/date +%Y%m%dT%H%M%S.%N%z prints the time, so names never repeat."""
    now = time.time_ns()
    local = datetime.fromtimestamp(now // 10**9).astimezone()
    return f"replaced-{local:%Y%m%dT%H%M%S}.{now % 10**9:09d}{local:%z}"


def present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def copy(source: Path, target: Path) -> None:
    """cp -Rp: links stay links, modes and times are kept."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir() and not source.is_symlink():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target, follow_symlinks=False)


def copy_live(paths: list[str], into: Path) -> None:
    for path in paths:
        if present(Path.home() / path):
            copy(Path.home() / path, into / path)


def tree(root: Path) -> dict[str, tuple[str, bytes]]:
    """Each entry under root, with a link's target and a file's bytes, as diff -r --no-dereference compares."""
    found: dict[str, tuple[str, bytes]] = {}
    for path in root.rglob("*"):
        name = str(path.relative_to(root))
        if path.is_symlink():
            found[name] = ("link", os.fsencode(path.readlink()))
        elif path.is_dir():
            found[name] = ("dir", b"")
        else:
            found[name] = ("file", path.read_bytes())
    return found


def link(*args: str) -> str:
    # --force: a symlink entry never replaces a real file without it, even an identical one.
    command = ["mise", "dot", "apply", "--force", "--yes", *args, *TARGETS]
    return subprocess.run(command, capture_output=bool(args), check=True, text=True).stdout or ""


def refuse(reason: str) -> None:
    msg = f"shell:apply: {reason}; nothing changed"
    raise ValueError(msg)


def started(scratch: Path) -> str:
    """What a login shell started from a copy of unix/home prints; a clean start prints the one word."""
    # A bare env keeps the shell's XDG paths inside the scratch folder; the scratch home holds the whole global
    # config, so a startup line that calls mise installs nothing.
    home = scratch / "home"
    shutil.copytree("unix/home", home, symlinks=True)
    env = {
        "HOME": str(home),
        "PATH": os.environ["PATH"],
        "TERM": "dumb",
        "MISE_AUTO_INSTALL": "0",
        "MISE_CEILING_PATHS": str(Path.cwd().parent),
    }
    command = ["zsh", "-il", "-c", "print started"]
    done = subprocess.run(
        command,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
    )
    return done.stdout.rstrip("\n")


def back_up(paths: list[str]) -> None:
    """Keep the live files in a private folder, after checking a shell from the new ones and that no file moved."""
    folder = backups()
    folder.mkdir(parents=True, exist_ok=True)
    folder.chmod(PRIVATE)
    fresh = folder / f".incoming.{os.getpid()}"
    fresh.mkdir()
    fresh.chmod(PRIVATE)
    try:
        with tempfile.TemporaryDirectory() as scratch:
            copy_live(paths, fresh)
            if (said := started(Path(scratch))) != "started":
                refuse(f"a shell started from unix/home printed: {said}")
            copy_live(paths, Path(scratch) / "now")
            if tree(fresh) != tree(Path(scratch) / "now"):
                refuse("a live file changed during the run")
        # Renamed after every check, so pre-apply is only ever a whole backup. Only a rollback frees the name.
        pre_apply = folder / "pre-apply"
        fresh.rename(folder / replaced_name() if present(pre_apply) else pre_apply)
    finally:
        if fresh.exists():  # renamed away once every check passed
            shutil.rmtree(fresh)


def keep_history() -> None:
    """Before the links: a shell started after a partial link would write the new history first."""
    live = Path.home() / ".zsh_history"
    history = xdg("XDG_STATE_HOME", ".local/state") / "zsh/history"
    if live.is_file() and not history.exists():
        history.parent.mkdir(parents=True, exist_ok=True)
        # Private from its first byte, and only renamed in whole: a failed copy leaves no history to skip.
        partial = history.with_name(f".history.{os.getpid()}")
        try:
            with live.open("rb") as source, os.fdopen(os.open(partial, PARTIAL, 0o600), "wb") as out:
                shutil.copyfileobj(source, out)
            partial.rename(history)
        finally:
            partial.unlink(missing_ok=True)


def apply() -> None:
    paths = backup_paths("shell:apply")
    # The links would point into this checkout, and a linked worktree goes away with its branch.
    if Path(".git").is_file():
        msg = "shell:apply: this is a linked git worktree; run it from the main checkout"
        raise ValueError(msg)
    if link("--dry-run"):
        back_up(paths)
        keep_history()
        link()
    completions = xdg("XDG_CACHE_HOME", ".cache") / "zsh/completions"
    completions.mkdir(parents=True, exist_ok=True)
    with (completions / "_mise").open("w") as out:
        subprocess.run(["mise", "completion", "zsh"], stdout=out, check=True)


def rollback() -> None:
    paths = backup_paths("shell:rollback")
    pre_apply = backups() / "pre-apply"
    if not pre_apply.is_dir():
        msg = f"shell:rollback: no backup at {pre_apply}"
        raise ValueError(msg)
    replaced = backups() / replaced_name()
    replaced.mkdir()
    replaced.chmod(PRIVATE)
    for path in paths:
        live = Path.home() / path
        if present(live):
            (replaced / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(live, replaced / path)
        if present(pre_apply / path):
            copy(pre_apply / path, live)
    # Last, so a failed run above keeps pre-apply and can be rerun. The next apply then records afresh.
    shutil.move(pre_apply, backups() / replaced_name())


def dispatch(options: ShellApply | ShellRollback) -> None:
    if isinstance(options, ShellApply):
        apply()
    else:
        rollback()
