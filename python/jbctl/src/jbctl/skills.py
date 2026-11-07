"""Bundled skills copied out of a Toolbox install's jars into the folders Claude Code and Codex read skills from."""

import ctypes
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

import filelock
from pydantic import ValidationError

from . import toolbox
from .ide import IdeError
from .models import (
    BundledSkill,
    Install,
    Leftover,
    OldSkillMarker,
    SkillAgent,
    SkillCopy,
    SkillFinding,
    SkillMarker,
    Skills,
    SkillState,
)

MARKER = ".jbctl-skill.json"
# What the earlier clion:skills mise task kept in the copy it wrote into ~/.claude/skills.
OLD_MARKER = ".dotfiles-clion-skills.json"
# In each folder jbctl stages a copy in or moves an old one aside into: clear() removes only folders that have it.
LEFTOVER = ".jbctl-leftover"
# Names jbctl keeps for its own files at the root of a copy, which a jar's skill may not use there.
RESERVED = frozenset({MARKER, OLD_MARKER, LEFTOVER})
# renamex_np's flags (macOS <stdio.h>): exchange two paths in one step; rename only when nothing is at the target.
RENAME_SWAP = 0x2
RENAME_EXCL = 0x4
# The states of a copy that ended up as asked; the others (modified, unmanaged) were left alone.
DONE = frozenset({SkillState.copied, SkillState.updated, SkillState.unchanged, SkillState.adopted})


def codex_folder(name: str) -> Path:
    return Path.home() / ".agents/skills" / name


def claude_link(name: str) -> Path:
    return Path.home() / ".claude/skills" / name


def chosen(options: Skills) -> Install:
    """The one install --ide names, or the only install of the --product. The schema cannot carry "one of the two"
    (see check-direct), and skills contacts no IDE, so it cannot pick the one that runs as stop and restart do."""
    if options.ide and options.product:
        msg = "skills takes --ide or --product, not both"
        raise IdeError(msg)
    if options.ide:
        return toolbox.install(options.ide)
    if not options.product:
        msg = "skills needs --ide or --product"
        raise IdeError(msg)
    everything = toolbox.installs()
    same = [install for install in everything if install.tool_id == options.product]
    if not same:
        ids = ", ".join(sorted({install.tool_id for install in everything}))
        msg = f"Toolbox has no IDE with tool id {options.product}; its tool ids are {ids}"
        raise IdeError(msg)
    if len(same) > 1:
        scripts = ", ".join(install.script for install in same)
        msg = f"{options.product} has {len(same)} installs ({scripts}); pick one with --ide"
        raise IdeError(msg)
    return same[0]


def places(app: Path) -> dict[str, list[tuple[Path, str]]]:
    """Every bundled skill in the app's plugin jars, by name: the jar and folder each copy of the name is in."""
    found: dict[str, list[tuple[Path, str]]] = {}
    for jar in sorted((app / "Contents/plugins").rglob("*.jar")):
        with zipfile.ZipFile(jar) as archive:
            for entry in archive.namelist():
                # A folder with a SKILL.md: under bundledSkills/ (CLion's contrib jars), or at the jar's root (the
                # Rider skills that every IDE's air-plugin also carries).
                match PurePosixPath(entry).parts:
                    case (name, "SKILL.md") | ("bundledSkills", name, "SKILL.md"):
                        found.setdefault(name, []).append((jar, str(PurePosixPath(entry).parent)))
    return found


def contents(skill: BundledSkill) -> Iterator[tuple[str, bytes]]:
    """Each file of the skill, by its path inside the skill's folder."""
    with zipfile.ZipFile(skill.jar) as archive:
        for entry in archive.namelist():
            path = PurePosixPath(entry.removeprefix(f"{skill.folder}/"))
            if entry.startswith(f"{skill.folder}/") and not entry.endswith("/"):
                if path.is_absolute() or ".." in path.parts:
                    msg = f"{skill.jar}!{entry} leaves the skill's folder"
                    raise IdeError(msg)
                if path.as_posix() in RESERVED:
                    msg = f"{skill.jar}!{entry} has a name jbctl keeps for its own files"
                    raise IdeError(msg)
                yield path.as_posix(), archive.read(entry)


def bundled(jar: Path, folder: str) -> BundledSkill:
    skill = BundledSkill(jar=str(jar), folder=folder, files={})
    files = dict(contents(skill))
    metadata = json.loads(files.get("metadata.json", b"{}"))
    version = metadata.get("version") if isinstance(metadata, dict) else None
    hashes = {path: digest(data) for path, data in files.items()}
    return skill.model_copy(update={"files": hashes, "version": version})


def sources(install: Install, names: list[str]) -> dict[str, BundledSkill]:
    """Each named skill as the install ships it, all found before anything is written."""
    found = places(Path(install.app))
    for name in names:
        if name not in found:
            msg = f"{install.script} ships no bundled skill named {name}; it ships {', '.join(sorted(found))}"
            raise IdeError(msg)
        if len(found[name]) > 1:
            where = ", ".join(f"{jar}!{folder}" for jar, folder in found[name])
            msg = f"{install.script} ships {name} in {len(found[name])} places: {where}"
            raise IdeError(msg)
    return {name: bundled(*found[name][0]) for name in names}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def leftover(path: Path) -> Path:
    """A new folder beside `path`, marked as jbctl's, so that clear() removes it if a killed run leaves it behind."""
    folder = Path(tempfile.mkdtemp(prefix=f".{path.name}.jbctl-", dir=path.parent))
    (folder / LEFTOVER).touch()
    return folder


def rename(source: Path, target: Path, flags: int) -> None:
    """macOS renamex_np, which Python does not wrap and no library offers: RENAME_SWAP exchanges the two paths in
    one step, so the target never goes missing; RENAME_EXCL fails rather than replace what appeared there."""
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.renamex_np(os.fsencode(source), os.fsencode(target), flags) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(source), None, str(target))


def put(staged: Path, path: Path, recorded: dict[str, str] | None, marker: str) -> list[str]:
    """Puts `staged` at `path` in one step. With nothing recorded nothing may be there; otherwise what is there is
    swapped out and must still match `recorded` and its `marker`. If it does not (it changed since it was checked),
    or checking it fails, it is swapped back: the differences are returned, or the error raised. `staged` then
    holds what is not in place, which clear() removes or keeps."""
    if recorded is None:
        rename(staged, path, RENAME_EXCL)
        return []
    rename(staged, path, RENAME_SWAP)
    try:
        differ = changed(staged, recorded, marker)
    except BaseException:  # an unreadable file, Ctrl-C: the original goes back before anything else
        rename(staged, path, RENAME_SWAP)
        raise
    if differ:
        rename(staged, path, RENAME_SWAP)
    return differ


def place(name: str, install: Install, skill: BundledSkill, codex: SkillFinding) -> SkillFinding:
    """Codex's copy, staged beside its place and put there in one step; what is there after, should it change."""
    folder = codex_folder(name)
    folder.parent.mkdir(parents=True, exist_ok=True)
    stage = leftover(folder) / name
    hashes = {}
    for path, data in contents(skill):
        (stage / path).parent.mkdir(parents=True, exist_ok=True)
        (stage / path).write_bytes(data)
        hashes[path] = digest(data)  # what was written, should the jar have changed since it was first read
    marker = SkillMarker(
        install=install.script, build=install.build, jar=skill.jar, version=skill.version, files=hashes
    )
    (stage / MARKER).write_text(marker.model_dump_json(indent=1) + "\n")
    # Something that appeared there since the check fails the run (RENAME_EXCL), and nothing is replaced. A run that
    # fails or is stopped leaves the staging folder for clear(), which removes it only if it holds nothing changed.
    differ = put(stage, folder, recorded(folder) if codex.state == SkillState.updated else None, MARKER)
    return folder_state(name, skill) if differ else codex


def link(name: str, claude: SkillFinding) -> SkillFinding:
    """Claude's link to Codex's copy, relative as `skills add -g` makes them, in place of the old task's copy."""
    path = claude_link(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = leftover(path) / name
    staged.symlink_to(os.path.relpath(codex_folder(name), path.parent))
    old = (
        OldSkillMarker.model_validate_json((path / OLD_MARKER).read_bytes()).files
        if claude.state == SkillState.adopted
        else None
    )
    differ = put(staged, path, old, OLD_MARKER)
    if differ:
        return SkillFinding(state=SkillState.modified, reason=f"changed while jbctl replaced it: {', '.join(differ)}")
    return claude


def entries(folder: Path, marker: str) -> dict[str, str]:
    """Each entry of a copy: a file's sha256, or the kind of entry it is. The copy's own marker at its root counts
    as "marker" only while it is a regular file, not a symlink; any other marker name is an entry like the rest."""
    found = {}
    for path in folder.rglob("*"):  # does not descend into symlinked folders
        name = path.relative_to(folder).as_posix()
        if name == marker and path.is_file() and not path.is_symlink():
            found[name] = "marker"
        elif path.is_symlink():
            found[name] = "symlink"
        elif path.is_file():
            found[name] = digest(path.read_bytes())
        else:
            found[name] = "folder" if path.is_dir() else "other"
    return found


def changed(folder: Path, recorded: dict[str, str], marker: str) -> list[str]:
    """What in a copy differs from the files its `marker` recorded (and the folders that hold them, and the marker
    itself): changed, added, removed, or replaced by a symlink. "." when the copy itself is no longer a folder."""
    if folder.is_symlink() or not folder.is_dir():
        return ["."]
    expected = recorded | {marker: "marker"}
    for path in recorded:
        expected |= {parent.as_posix(): "folder" for parent in PurePosixPath(path).parents if parent.name}
    now = entries(folder, marker)
    return sorted(path for path in now.keys() | expected.keys() if now.get(path) != expected.get(path))


def recorded(folder: Path) -> dict[str, str]:
    return SkillMarker.model_validate_json((folder / MARKER).read_bytes()).files


def resolves(parent: Path) -> str | None:
    """Why an agent's skill folder is not where it seems, if it is not: a symlink to elsewhere, or under one."""
    real, home = parent.resolve(), Path.home().resolve()
    return None if real == home / parent.relative_to(Path.home()) else f"{parent} resolves to {real}"


def foreign(name: str) -> str | None:
    """Why Codex's copy is not jbctl's to write, if it is not."""
    folder, twin = codex_folder(name), Path.home() / ".codex/skills" / name
    if reason := resolves(folder.parent):
        return reason
    if twin.exists() or twin.is_symlink():
        return f"Codex would also find {twin}"
    if folder.is_symlink():
        return f"a symlink to {folder.readlink()}, not jbctl's copy"
    if folder.exists() and not (folder / MARKER).is_file():
        return "not written by jbctl"
    return None


def folder_state(name: str, skill: BundledSkill) -> SkillFinding:
    """What Codex's copy needs: none yet, or jbctl's own copy, current, out of date or changed by someone."""
    folder = codex_folder(name)
    if reason := foreign(name):
        return SkillFinding(state=SkillState.unmanaged, reason=reason)
    if not folder.exists():
        return SkillFinding(state=SkillState.copied)
    try:
        marker = SkillMarker.model_validate_json((folder / MARKER).read_bytes())
    except ValidationError:
        return SkillFinding(state=SkillState.unmanaged, reason=f"its {MARKER} is not one jbctl wrote")
    if differ := changed(folder, marker.files, MARKER):
        return SkillFinding(state=SkillState.modified, reason=f"changed since jbctl wrote it: {', '.join(differ)}")
    if marker.files == skill.files:
        return SkillFinding(state=SkillState.unchanged)
    return SkillFinding(state=SkillState.updated, previous_version=marker.version)


def follow(name: str, codex: SkillFinding, state: SkillState | None) -> SkillFinding:
    """Claude's link where Codex's copy decides: it needs a copy of jbctl's, shares a changed one, or is `state`
    (Codex's own state when None: the link is in place and shows that copy)."""
    if codex.state == SkillState.unmanaged:
        return SkillFinding(
            state=SkillState.unmanaged,
            reason=f"needs jbctl's copy in {codex_folder(name).parent}, which it does not have",
        )
    if codex.state == SkillState.modified or state is None:
        return codex
    return SkillFinding(state=state)


def old_copy(name: str, codex: SkillFinding) -> SkillFinding:
    """Claude's copy from the earlier clion:skills task: adopted unless someone changed it."""
    path = claude_link(name)
    try:
        old = OldSkillMarker.model_validate_json((path / OLD_MARKER).read_bytes())
    except ValidationError:
        return SkillFinding(
            state=SkillState.unmanaged, reason=f"its {OLD_MARKER} is not one the clion:skills task wrote"
        )
    if differ := changed(path, old.files, OLD_MARKER):
        reason = f"changed since the clion:skills task wrote it: {', '.join(differ)}"
        return SkillFinding(state=SkillState.modified, reason=reason)
    return follow(name, codex, SkillState.adopted)


def link_state(name: str, codex: SkillFinding) -> SkillFinding:
    """What Claude's link needs: jbctl's link to Codex's copy, the old task's copy to replace, or nothing yet."""
    path = claude_link(name)
    if reason := resolves(path.parent):
        return SkillFinding(state=SkillState.unmanaged, reason=reason)
    if path.is_symlink():
        target = path.readlink()
        if Path(os.path.normpath(path.parent / target)) != codex_folder(name):
            return SkillFinding(state=SkillState.unmanaged, reason=f"a symlink to {target}, not to jbctl's copy")
        return follow(name, codex, None)
    if (path / OLD_MARKER).is_file():
        return old_copy(name, codex)
    if path.exists():
        return SkillFinding(state=SkillState.unmanaged, reason="not written by jbctl")
    return follow(name, codex, SkillState.copied)


def unverified(copy: Path) -> str | None:
    """Why a copy in a leftover folder may be someone's work, if it may: it does not match the marker in it (jbctl's
    or the earlier task's), or has none that parses."""
    for marker, model in ((MARKER, SkillMarker), (OLD_MARKER, OldSkillMarker)):
        if (copy / marker).is_file():
            try:
                files = model.model_validate_json((copy / marker).read_bytes()).files
            except ValidationError:
                return f"holds a copy whose {marker} does not parse"
            if differ := changed(copy, files, marker):
                return f"holds a copy changed since its marker was written: {', '.join(differ)}"
            return None
    return "holds a folder with no marker"


def kept(folder: Path, name: str) -> str | None:
    """Why a leftover folder of jbctl's must stay, if it must. jbctl removes one only when it holds nothing, the link
    jbctl stages for Claude, or a copy that matches its marker: the copy a swap displaced, or the new one a rollback
    took back. A copy swapped out by a run stopped before checking it, and changed since, stays."""
    inside = sorted(path.name for path in folder.iterdir() if path.name != LEFTOVER)
    if extra := [entry for entry in inside if entry != name]:
        return f"holds {', '.join(extra)}, which jbctl did not put there"
    entry = folder / name
    if not inside:
        return None
    if entry.is_symlink():
        staged = Path(os.path.relpath(codex_folder(name), claude_link(name).parent))
        return None if entry.readlink() == staged else "holds a symlink jbctl did not stage"
    return unverified(entry)


def clear(name: str) -> Iterator[Leftover]:
    """Removes the folders this run, or a stopped one, left beside the copy and the link, in skill folders that are
    where they seem; reports each one kept."""
    for parent in (codex_folder(name).parent, claude_link(name).parent):
        if parent.is_dir() and not resolves(parent):
            for folder in sorted(parent.glob(f".{name}.jbctl-*")):
                mark = folder / LEFTOVER
                if folder.is_symlink() or mark.is_symlink() or not mark.is_file():
                    continue  # not one jbctl made
                if reason := kept(folder, name):
                    yield Leftover(path=str(folder), reason=reason)
                else:
                    shutil.rmtree(folder)


def copies(options: Skills) -> Iterator[SkillCopy | Leftover]:
    """One event per skill per agent, Codex's folder first, then Claude's link to it; then the leftover folders kept.
    A run that writes waits for any other one to finish."""
    install = chosen(options)
    found = sources(install, options.skill)
    if options.check:
        yield from compare(install, found, write=False)
        return
    # In jbctl's state folder, as lifecycle's locks are: a lock file stays, and the agents' folders get none.
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "jbctl"
    state.mkdir(parents=True, exist_ok=True)
    with filelock.FileLock(state / "skills.lock"):
        yield from compare(install, found, write=True)


def compare(install: Install, found: dict[str, BundledSkill], *, write: bool) -> Iterator[SkillCopy | Leftover]:
    for name, skill in found.items():
        event = {"skill": name, "install": install.script, "build": install.build, "version": skill.version}
        codex = folder_state(name, skill)
        if codex.state in {SkillState.copied, SkillState.updated} and write:
            codex = place(name, install, skill, codex)
        yield SkillCopy(agent=SkillAgent.codex, path=str(codex_folder(name)), **event, **codex.model_dump())
        claude = link_state(name, codex)
        if claude.state in {SkillState.copied, SkillState.adopted} and write and not claude_link(name).is_symlink():
            claude = link(name, claude)
        yield SkillCopy(agent=SkillAgent.claude, path=str(claude_link(name)), **event, **claude.model_dump())
        if write:
            yield from clear(name)
