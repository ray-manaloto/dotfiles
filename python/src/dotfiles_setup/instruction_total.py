# Copyright (c) 2026 Raymond Manaloto
"""Bound the aggregate raw character count of launch-time instructions.

Membership comes from the shared Markdown budget engine. Its per-file
measurement strips comments and counts bytes; this gate deliberately counts
``len(str)`` of each unique eager member's complete UTF-8 text instead.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from kb_setup.md_budget import classify, has_paths_frontmatter, resolve_imports

from dotfiles_setup.codec import encode

if TYPE_CHECKING:
    from pathlib import Path

HARNESS_LIMIT = 150_000
SAFETY_MARGIN_PERCENT = 93
# Approximately 93% of the harness ceiling, rounded to the specified limit.
DEFAULT_LIMIT = 140_000
TOP_FILE_COUNT = 5
ENTRY_PATHS = ("CLAUDE.md", ".claude/CLAUDE.md")


def _raise_walk_error(error: OSError) -> None:
    """Make an unreadable rules directory fail instead of silently disappearing."""
    raise error


def _unscoped_rules(root: Path) -> set[Path]:
    """Resolve every ``.claude/rules`` file that loads at launch (no ``paths:``)."""
    rules = root / ".claude/rules"
    if not rules.exists():
        return set()
    if not rules.is_dir():
        msg = f"{rules}: expected a rules directory"
        raise ValueError(msg)
    found: set[Path] = set()
    for directory, _, filenames in rules.walk(on_error=_raise_walk_error):
        for name in filenames:
            path = directory / name
            relative = path.relative_to(root).as_posix()
            if classify(relative) != "rule_unscoped":
                continue
            if not has_paths_frontmatter(path.read_text(encoding="utf-8")):
                found.add(path.resolve())
    return found


def measure_eager(root: Path) -> dict[str, int]:
    """Return sorted repo-relative paths and raw character counts, once each.

    Args:
        root: Repository root containing the root CLAUDE.md entry point.

    Returns:
        Raw character counts for the entry closures and all unscoped rules.

    Raises:
        OSError: An eager member or rules directory cannot be read.
        UnicodeError: An eager member is not valid UTF-8.
        ValueError: The root or required root entry is misconfigured.
    """
    root = root.resolve()
    if not root.is_dir() or not (root / "CLAUDE.md").is_file():
        msg = f"{root}: expected a directory containing CLAUDE.md"
        raise ValueError(msg)

    members: set[Path] = set()
    for relative in ENTRY_PATHS:
        entry = root / relative
        if entry.exists():
            if not entry.is_file():
                msg = f"{entry}: expected an instruction file"
                raise ValueError(msg)
            members.update(path.resolve() for path in resolve_imports(entry, root))

    members.update(_unscoped_rules(root))

    return {
        path.relative_to(root).as_posix(): len(path.read_text(encoding="utf-8"))
        for path in sorted(members)
    }


def instruction_total_main(
    root: Path,
    *,
    limit: int = DEFAULT_LIMIT,
    json_output: bool = False,
) -> int:
    """Print the eager total and return 0, 1 (over), or 2 (cannot measure)."""
    if limit < 0:
        sys.stderr.write("instruction-total error: limit must be nonnegative\n")
        return 2
    try:
        sizes = measure_eager(root)
    except (OSError, UnicodeError, ValueError) as error:
        sys.stderr.write(f"instruction-total error: {error}\n")
        return 2

    total = sum(sizes.values())
    over = total > limit
    if json_output:
        sys.stdout.write(
            encode(
                {
                    "total": total,
                    "limit": limit,
                    "files": [
                        {"path": path, "chars": chars} for path, chars in sizes.items()
                    ],
                    "over": over,
                }
            ).decode("utf-8")
            + "\n"
        )
    else:
        state = "OVER" if over else "OK"
        sys.stdout.write(
            f"instruction-total {state}: {total} chars across {len(sizes)} files; "
            f"limit {limit}\n"
        )
        if over:
            sys.stdout.write("Largest eager files (top 5):\n")
            largest = sorted(sizes.items(), key=lambda item: (-item[1], item[0]))
            for path, chars in largest[:TOP_FILE_COUNT]:
                sys.stdout.write(f"  {path}: {chars} chars\n")
    return int(over)
