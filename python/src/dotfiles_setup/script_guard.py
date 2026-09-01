# Copyright (c) 2026 Raymond Manaloto
"""Deny a NEW shell script at write time; logic belongs in ``python/``.

A ``PreToolUse`` rule on ``Edit``/``Write``/``NotebookEdit``, dispatched from
:mod:`dotfiles_setup.hook_guard` alongside :mod:`dotfiles_setup.branch_guard`.

**Why this exists even though ``bash_logic_budget`` already gates ``.sh``
files.** That gate is an hk step, so it runs at COMMIT. Between writing a
script and committing it, an agent builds on it — a mise task, a settings.json
hook, a doc reference — and by the time the budget objects, unwinding costs
more than the script did. Observed 2026-09-01 in this repo: a
``scripts/posttooluse-mise-context.sh`` wrapper was written, wired into
``.claude/settings.json``, allowlisted, and only then removed on the operator's
instruction that everything belongs in the python library. Nothing objected at
the moment of the write, which is the only moment the cost is still zero.

**Two detectors, because an extension is not the file type.** A path ending
``.sh``/``.bash`` is the obvious case. The one that slips past a glob is an
extensionless file with a shell shebang — ``scripts/deploy`` is a shell script
that no ``*.sh`` pathspec matches, and ``bash_budget``'s SCOPE_PATHSPECS would
never see it. So the content is checked for a shebang too.

**What stays allowed**, because the point is to stop NEW bash, not to freeze
what exists:

- every path already in :data:`bash_budget.ALLOWLIST` — those are sanctioned,
  and their growth is what the budget governs;
- ``plugins/**`` — vendored third-party, explicitly out of scope for the
  zero-bash-logic policy;
- anything outside the repository, and anything git-ignored — the scratchpad,
  a throwaway probe, a sibling clone. A guard that fires on a temp file is a
  guard people learn to route around.

The single source of truth for what is sanctioned is ``bash_budget.ALLOWLIST``.
This module deliberately does NOT keep its own list: two lists drift, and the
drift would show up as a guard that denies a script the commit gate accepts.
"""

from __future__ import annotations

from pathlib import Path

from dotfiles_setup import bash_budget, branch_guard

#: The file-modifying tools this guard inspects — the same set branch_guard
#: covers, so one PreToolUse matcher serves both.
TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

#: Extensions that are a shell script by name.
SHELL_SUFFIXES = frozenset({".sh", ".bash", ".zsh", ".ksh"})

#: Interpreters that make a shebang line a shell script. ``env`` is included
#: because ``#!/usr/bin/env bash`` is the form this repo's own scripts use.
SHELL_INTERPRETERS = ("sh", "bash", "zsh", "ksh", "dash")

#: Vendored trees the zero-bash-logic policy does not govern.
EXEMPT_PREFIXES = ("plugins/",)

_REASON = (
    "Refusing to create a new shell script: {rel}\n"
    "\n"
    "Non-trivial logic lives in `python/` (`dotfiles_setup`), per "
    "`.claude/rules/zero-bash-logic.md`. Bash is restricted to the thin "
    "check/smoke wrappers already listed in `bash_budget.ALLOWLIST`, and this "
    "path is not one of them.\n"
    "\n"
    "The shape that works here is three layers: a skill or hook names the "
    "task, a `mise` task is the seam, and the logic is a python module with "
    'tests. A Claude Code hook can invoke `mise -C "$CLAUDE_PROJECT_DIR" run '
    "<task>` directly — no shell wrapper is needed to reach python.\n"
    "\n"
    "If this genuinely must be bash, that is a reviewable decision: add it to "
    "`ALLOWLIST` in `python/src/dotfiles_setup/bash_budget.py` with a one-line "
    "justification in the same change, and this guard will allow it."
)


def repo_root() -> Path:
    """This repository's root, derived from this module's own location.

    Deliberately not probed from the edited path: the policy governs THIS
    repo's scripts, so a `.sh` written into a sibling clone during the same
    session is none of its business. Same four-level climb `main.py` uses for
    `project_root`.
    """
    return Path(__file__).resolve().parent.parent.parent.parent


def _relative(target: Path, root: Path) -> str | None:
    """``target`` as a repo-relative posix path, or None when outside."""
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError, OSError:
        return None


def has_shell_shebang(content: str) -> bool:
    """Whether ``content`` opens with a shell shebang.

    Only the first line is considered: a ``#!`` further down is a comment, and
    treating it as a shebang would deny python files that quote one.
    """
    first = content.lstrip("﻿").split("\n", 1)[0].strip()
    if not first.startswith("#!"):
        return False
    return any(
        first.endswith(interp) or f"{interp} " in first for interp in SHELL_INTERPRETERS
    )


def _written_content(tool_input: dict[str, object]) -> str:
    """The text this call would put in the file, across the write tools."""
    for key in ("content", "new_string", "new_source"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def is_shell_script(target: Path, tool_input: dict[str, object]) -> bool:
    """By suffix, or by shebang for an extensionless script."""
    if target.suffix.lower() in SHELL_SUFFIXES:
        return True
    if target.suffix:
        return False
    return has_shell_shebang(_written_content(tool_input))


def decide(tool_input: dict[str, object]) -> str | None:
    """A deny reason for a new unsanctioned shell script, else None.

    Fails OPEN on anything it cannot resolve. A guard that blocks a write
    because it could not find the repo root is worse than one that misses a
    script — the commit-time budget is still behind it.
    """
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not raw:
        return None
    target = Path(raw)
    root = repo_root()
    rel = _relative(target, root)
    if rel is None or rel.startswith(EXEMPT_PREFIXES):
        return None
    if rel in bash_budget.ALLOWLIST:
        return None
    if branch_guard.is_ignored(target, root):
        return None
    if not is_shell_script(target, tool_input):
        return None
    return _REASON.format(rel=rel)


def handles(tool_name: str) -> bool:
    """True when ``tool_name`` is a file-modifying tool this guard covers."""
    return tool_name in TOOLS
