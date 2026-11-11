"""What changed in a dependency between two mapped versions: functions from the cbm maps, listed files from git."""

import ast
import re
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

from . import cbm
from .events import DepmapsError
from .git import git
from .models import Change, ChangeKind, ErrorCode, FileChange, Manifest, NodeKey, NodeShape

HUNK = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def nodes(project: str) -> dict[NodeKey, NodeShape]:
    """Functions and methods by (file, name, label), with the `<project>.` prefix taken off each name.

    cbm puts the project in every qualified name, so the same function has a different name in each
    version's map. Nodes without the prefix, such as Python's builtins, belong to no file of the source.
    """
    path = cbm.database(project)
    prefix = f"{project}."
    query = (
        "select file_path, substr(qualified_name, ?), label, json_extract(properties, '$.signature'),"
        " json_extract(properties, '$.return_type'), json_extract(properties, '$.fp'), start_line, end_line"
        " from nodes where project = ? and label in ('Function', 'Method')"
        " and substr(qualified_name, 1, ?) = ?"
    )
    try:
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as db:
            rows = db.execute(query, (len(prefix) + 1, project, len(prefix), prefix)).fetchall()
    except sqlite3.OperationalError as error:
        raise DepmapsError(ErrorCode.no_map, f"depmaps: cbm map {path}: {error}") from None
    return {
        NodeKey(file=file, name=name, label=label): NodeShape(
            signature=signature, return_type=return_type, fp=fp, start=start, end=end
        )
        for file, name, label, signature, return_type, fp, start, end in rows
    }


def hunks(bare: Path, old: str, new: str) -> dict[str, list[tuple[int, int]]]:
    """The new side of each `git diff -U0` hunk, as inclusive line ranges by file."""
    found: dict[str, list[tuple[int, int]]] = {}
    path, header = None, False
    # Explicit prefixes, as diff.noprefix or diff.mnemonicPrefix would change them, and every non-ASCII
    # byte octal-escaped, as core.quotePath=false would leave it raw inside a quoted name.
    args = ("-c", "core.quotePath=true", "diff", "-U0", "--no-color", "--no-ext-diff")
    listing = git(*args, "--src-prefix=a/", "--dst-prefix=b/", old, new, cwd=bare)
    for line in listing.splitlines():
        # `+++ ` names a file only in a file's header: inside a hunk it is an added line, such as `++ count;`.
        if line.startswith("diff --git "):
            path, header = None, True
        elif header and line.startswith("+++ "):
            path = target(line)
        elif match := HUNK.match(line):
            header = False
            if path is None:
                continue
            # A pure deletion (+start,0) sits between lines start and start + 1: the empty range (start + 1, start)
            # meets only a function holding both lines.
            start, count = int(match[1]), int(match[2] or 1)
            found.setdefault(path, []).append((start + 1, start) if count == 0 else (start, start + count - 1))
    return found


def target(line: str) -> str | None:
    """The file a `+++` line names, None for /dev/null. git ends the line with a tab when the name has a
    space, and C-quotes a name with a quote, backslash, control or non-ASCII byte, prefix and all, in
    escapes a bytes literal reads the same way under core.quotePath=true (git 2.56: `+++ "b/\\303\\251.py"`)."""
    name = line.removeprefix("+++ ").removesuffix("\t")
    if name == "/dev/null":
        return None
    if name.startswith('"'):
        name = ast.literal_eval(f"b{name}").decode("utf-8", "surrogateescape")
    return name.removeprefix("b/")


def changes(bare: Path, old: Manifest, new: Manifest) -> Iterator[Change]:
    before, after = nodes(old.project), nodes(new.project)
    touched = hunks(bare, old.commit, new.commit)
    for key in sorted(before.keys() | after.keys(), key=lambda each: (each.file, each.name, each.label)):
        found = kind(before.get(key), after.get(key), touched.get(key.file, []))
        if found is not None:
            change, was, now = found
            yield Change(kind=change, label=key.label, file=key.file, name=key.name, before=was, after=now)


def kind(
    was: NodeShape | None, now: NodeShape | None, touched: list[tuple[int, int]]
) -> tuple[ChangeKind, str | None, str | None] | None:
    """How one function changed, with its old and new signature for a signature change."""
    if was is None:
        return ChangeKind.added, None, None
    if now is None:
        return ChangeKind.removed, None, None
    if (was.signature, was.return_type) != (now.signature, now.return_type):
        return ChangeKind.signature, shown(was), shown(now)
    # fp is cbm's body hash, absent for small bodies, so a git hunk inside the function counts too.
    if was.fp != now.fp or any(start <= now.end and now.start <= end for start, end in touched):
        return ChangeKind.body, None, None
    return None


def shown(node: NodeShape) -> str:
    return f"{node.signature or ''} -> {node.return_type}" if node.return_type else node.signature or ""


def files(bare: Path, old: Manifest, new: Manifest, paths: list[str]) -> Iterator[FileChange]:
    if not paths:
        return
    # -z: each field ends in NUL and no name is quoted. A rename gives its old name, then its new one.
    listing = git("diff", "--name-status", "-z", "-M", "--no-color", old.commit, new.commit, "--", *paths, cwd=bare)
    fields = iter(listing.split("\0")[:-1])
    for status in fields:
        if status.startswith("R"):
            next(fields)
        yield FileChange(status=status, path=next(fields))
