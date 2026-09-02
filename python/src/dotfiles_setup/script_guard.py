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

from pathlib import Path, PurePosixPath

from dotfiles_setup import bash_budget, branch_guard

#: The file-modifying tools this guard inspects — the same set branch_guard
#: covers, so one PreToolUse matcher serves both.
TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

#: Extensions that are a shell script by name.
SHELL_SUFFIXES = frozenset({".sh", ".bash", ".zsh", ".ksh"})

#: Interpreter BASENAMES that make a shebang a shell script. Matched as a
#: whole token — `notbash` is not `bash`.
SHELL_INTERPRETERS = frozenset({"sh", "bash", "zsh", "ksh", "dash", "ash"})

#: Vendored trees the zero-bash-logic policy does not govern.
EXEMPT_PREFIXES = ("plugins/",)  # compared case-folded

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


def _allowlisted(rel: str) -> bool:
    """Allowlist membership, case-folded.

    This host's filesystem is case-insensitive, so `SCRIPTS/PRETOOLUSE-GUARD.SH`
    is the tracked allowlisted wrapper; a case-sensitive compare denied it.
    """
    folded = rel.casefold()
    return any(listed.casefold() == folded for listed in bash_budget.ALLOWLIST)


def _relative(target: Path, root: Path) -> str | None:
    """``target`` as a repo-relative posix path, or None when outside."""
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError, OSError:
        return None


def has_shell_shebang(content: str) -> bool:
    r"""Whether ``content``'s FIRST line is a shell shebang.

    Only the first line counts: a ``#!`` further down is a comment, and treating
    it as a shebang would deny a python file that documents one.

    The interpreter is compared as a whole TOKEN, not by suffix. A cold review
    caught `endswith` here: ``"notbash".endswith("bash")`` is true, so
    ``#!/usr/bin/env notbash`` was denied as bash. Splitting on whitespace also
    fixes the tab form (``#!/bin/bash\t-e``), which the old space-only check
    missed while the kernel runs it happily.

    Case-folded because this host's filesystem is case-insensitive and
    ``#!/BIN/BASH`` executes.
    """
    first = content.lstrip("\ufeff").split("\n", 1)[0].strip().casefold()
    if not first.startswith("#!"):
        return False
    tokens = first[2:].replace("\t", " ").split()
    if not tokens:
        return False
    interpreter = PurePosixPath(tokens[0]).name
    if interpreter == "env":
        # `#!/usr/bin/env -S python -c ...` — the interpreter is the first
        # token that is not a flag or an assignment.
        for token in tokens[1:]:
            if token.startswith("-") or "=" in token:
                continue
            interpreter = PurePosixPath(token).name
            break
        else:
            return False
    return interpreter in SHELL_INTERPRETERS


def _written_content(tool_input: dict[str, object]) -> str:
    """The text this call would put in the file, across the write tools."""
    for key in ("content", "new_string", "new_source"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def is_shell_script(target: Path, tool_input: dict[str, object]) -> bool:
    """By suffix, or by a first-line shell shebang whatever the suffix.

    The suffix is not the file type. A cold review showed the earlier version
    returned False for ANY non-shell suffix without reading the content, so
    ``scripts/deploy.txt`` holding ``#!/bin/bash`` passed this guard AND the
    commit-time budget, whose scope is `*.sh`.
    """
    if target.suffix.casefold() in SHELL_SUFFIXES:
        return True
    return has_shell_shebang(_written_content(tool_input))


def _exempt(rel: str, target: Path) -> bool:
    """Whether this path is out of scope, for any of the settled reasons.

    Split out of :func:`decide` so each exemption reads as one line and the
    decision itself stays a short chain of guards. Consulted only for a
    candidate shell script: the last check shells out to git.
    """
    if rel.casefold().startswith(EXEMPT_PREFIXES):
        return True
    if _allowlisted(rel):
        return True
    try:
        # Only NEW files are refused: the contract is to stop new bash, not to
        # freeze what exists. A cold review found the earlier version denying
        # `home/dot_local/bin/executable_claude`, a tracked wrapper that cannot
        # enter the allowlist because the commit gate would call the entry
        # stale — a guard whose escape hatch cannot be used is an outage.
        if target.exists():
            return True
    except OSError:
        return True
    return branch_guard.is_ignored(target, repo_root())


def decide(tool_input: dict[str, object]) -> str | None:
    """A deny reason for a NEW unsanctioned shell script, else None.

    Fails OPEN on anything it cannot resolve. Blocking a write because the
    guard could not answer is worse than missing a script; the commit-time
    budget is still behind it.
    """
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not raw:
        return None
    target = Path(raw)
    rel = _relative(target, repo_root())
    if rel is None:
        return None
    # Classify BEFORE exempting: `_exempt` ends in a git probe
    # (`branch_guard.is_ignored`), and an ordinary new `.py` or `.md` file
    # should not pay for one just to be waved through.
    if not is_shell_script(target, tool_input):
        return None
    if _exempt(rel, target):
        return None
    return _REASON.format(rel=rel)


def handles(tool_name: str) -> bool:
    """True when ``tool_name`` is a file-modifying tool this guard covers."""
    return tool_name in TOOLS
