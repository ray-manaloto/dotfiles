"""Trust this repository's main checkout in Codex and Claude Code, so neither asks here or in its worktrees."""
# Codex 0.167.0 reads `[projects."<path>"] trust_level` from $CODEX_HOME/config.toml (else ~/.codex) by the exact
# canonical path (codex-rs/config/src/loader/mod.rs:1571, 1601) and resolves a linked worktree to its main checkout.
# Claude Code 2.1.319 reads `projects[<path>].hasTrustDialogAccepted` from $CLAUDE_CONFIG_DIR/.claude.json (else
# ~/.claude.json), keyed by the canonical git root, which is the main checkout for a linked worktree. A real run with
# Claude Code 2.1.321 confirmed that one entry covers the worktrees of both.

import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import tomlkit

from .git import git
from .models import TrustAction, Trusted, TrustHarness


def main_checkout() -> Path:
    """The main checkout this run's trust entry is for: this checkout's top, or a linked worktree's main root."""
    if git("rev-parse", "--is-bare-repository").strip() == "true":
        msg = "trust: this is a bare repository; run it from a checkout"
        raise ValueError(msg)
    git_dir, common, top = (
        Path(line)
        for line in git(
            "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir", "--show-toplevel"
        ).splitlines()
    )
    if git_dir == common:
        # The top level, not the folder above the git dir, keeps a submodule (git dir in .git/modules) right.
        return top.resolve()
    # A linked worktree, resolved as Codex 0.167.0 does (codex-rs/git-utils/src/trust.rs resolve_root, lines 152-223):
    # its git dir is <common>/worktrees/<name>, and the main root is the folder above the common dir, kept only when
    # that folder's own .git is the common dir. With --separate-git-dir /storage/project/.git that is
    # /storage/project, the key Codex and Claude Code (2.1.319, its canonical git root) both look up for the worktree.
    main_root = common.parent
    if git_dir.parent != common / "worktrees" or (main_root / ".git").resolve() != common.resolve():
        msg = f"trust: this worktree's common git dir {common} has no main checkout above it; Codex trusts none here"
        raise ValueError(msg)
    return main_root.resolve()


def write(path: Path, text: str) -> None:
    """Replace the file in one rename, keeping its mode; a new file is private."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temporary:
        name = Path(temporary.name)
        try:
            temporary.write(text)
            temporary.close()
            name.chmod(mode)
            name.replace(path)
        finally:
            name.unlink(missing_ok=True)


def backup(harness: TrustHarness, path: Path, folder: Path) -> str | None:
    if not path.exists():
        return None
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Named by harness too: two config files may share a basename once links are resolved.
    copy = folder / f"{harness.value}-{path.name.lstrip('.')}"
    shutil.copyfile(path, copy)
    copy.chmod(0o600)
    return str(copy)


def read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def codex(key: str, path: Path, folder: Path) -> Trusted:
    # Read just before writing, so a change another process made a moment ago is kept.
    text = read(path)
    doc = tomlkit.parse(text) if text is not None else tomlkit.document()
    projects = doc.get("projects")
    entry = Trusted(harness=TrustHarness.codex, path=key, file=str(path), action=TrustAction.added, backup=None)
    table = projects.get(key) if projects is not None else None
    level = table.get("trust_level") if table is not None else None
    if level == "trusted":
        return entry.model_copy(update={"action": TrustAction.unchanged})
    if level is not None:
        return entry.model_copy(update={"action": TrustAction.untrusted})
    if projects is None:
        projects = tomlkit.table(is_super_table=True)
        doc["projects"] = projects
    if table is None:
        table = tomlkit.table()
        projects[key] = table
    table["trust_level"] = "trusted"
    saved = backup(TrustHarness.codex, path, folder)
    write(path, tomlkit.dumps(doc))
    return entry.model_copy(update={"backup": saved})


def claude(key: str, path: Path, folder: Path) -> Trusted:
    text = read(path)
    config = json.loads(text) if text is not None else {}
    entry = Trusted(harness=TrustHarness.claude, path=key, file=str(path), action=TrustAction.added, backup=None)
    projects = config.setdefault("projects", {})
    if projects.get(key, {}).get("hasTrustDialogAccepted") is True:
        return entry.model_copy(update={"action": TrustAction.unchanged})
    projects.setdefault(key, {})["hasTrustDialogAccepted"] = True
    saved = backup(TrustHarness.claude, path, folder)
    # As Claude Code writes it: JSON.stringify(config, null, 2), with no newline at the end.
    write(path, json.dumps(config, indent=2, ensure_ascii=False))
    return entry.model_copy(update={"backup": saved})


def run() -> None:
    key = str(main_checkout())
    home = Path.home()
    # resolve(): a linked config is written at its target, and the link stays.
    codex_file = (Path(os.environ.get("CODEX_HOME") or home / ".codex") / "config.toml").resolve()
    claude_file = (Path(os.environ.get("CLAUDE_CONFIG_DIR") or home) / ".claude.json").resolve()
    state = Path(os.environ.get("XDG_STATE_HOME") or home / ".local" / "state")
    folder = state / "dotfiles" / "trust" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    untrusted = False
    for harness, path in [(codex, codex_file), (claude, claude_file)]:
        # One line as each file is done, so a failure in the second still reports the first.
        entry = harness(key, path, folder)
        sys.stdout.write(entry.model_dump_json() + "\n")
        untrusted |= entry.action is TrustAction.untrusted
    if untrusted:
        msg = f"trust: Codex marks {key} untrusted; left as it is"
        raise ValueError(msg)
