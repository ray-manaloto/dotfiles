# Copyright (c) 2026 Raymond Manaloto
r"""Heredoc-body detection, shared by the PreToolUse guard and the ADR-0001 check.

A heredoc body is **stdin data**, not a command, and no stdlib shell lexer
models that: ``shlex(punctuation_chars=True)`` puts ``\\n`` in ``whitespace``,
so a heredoc body and two real newline-separated commands tokenize identically
(the researched alternatives — ``bashlex``, ``tree-sitter-bash`` — are recorded
in :mod:`dotfiles_setup.hook_guard`'s banner comment, which is where this pair
was written for #265).

It lives here because a **second** consumer appeared:
:mod:`dotfiles_setup.workflow_hooks` reads a workflow ``run:`` block at command
positions, and a ``gh issue create --body-file - <<'EOF' … git push … EOF``
block would otherwise be read as a git write. Duplicating the regex would leave
two copies of a subtle pattern to keep in sync, so the pair moved out rather
than being copied.

The one behaviour that is NOT shared is *when* to redact, which is why
:func:`redact_heredoc_bodies` exists alongside the raw pattern: a heredoc fed to
a **shell** (``bash <<'SH' … git push … SH``) really is executed, so blanket
redaction would trade a false positive for a false negative. The guard wants
the raw pattern (every heredoc it sees is an argument to the tool being
guarded); the workflow check wants the interpreter-aware form.
"""

from __future__ import annotations

import re

# NUL is the filler because it is the one byte that CANNOT occur in a real Bash
# command (execve arguments are NUL-terminated), so input can never forge it,
# and it is neither `\w` nor `\s`. Substitution is length-preserving so every
# other offset in the command is untouched.
NUL_FILLER = "\x00"

# A heredoc body is stdin DATA that can never be a command. Matches `<<EOF`,
# `<<'EOF'` and `<<-EOF` (which strips leading TABS from the body *and* the
# delimiter line). `<<<` here-strings are not matched: a `\w` delimiter cannot
# start with `<`, and their content is quoted anyway.
HEREDOC_PATTERN = re.compile(
    r"""
    <<-?[ \t]*(?P<q>['"]?)(?P<delim>[A-Za-z_]\w*)(?P=q)  # the redirect operator
    [^\n]*\n                                             # rest of that line
    (?P<inert>(?:[^\n]*\n)*?[ \t]*(?P=delim)[ \t]*)      # body + delimiter line
    (?=\n|\Z)                                            # delimiter line ends here
    """,
    re.VERBOSE,
)

# Commands that EXECUTE their heredoc body, so its contents are real commands.
# `.` is POSIX `source`. Matched on the basename, so `/bin/bash` counts.
SHELL_INTERPRETERS: frozenset[str] = frozenset(
    {".", "bash", "dash", "ksh", "sh", "source", "zsh"}
)

# Separators after which a new command word begins, for the owning-command scan.
_COMMAND_BREAK = re.compile(r"[\n;&|(){}]")

# `FOO=bar cmd <<EOF` — a leading assignment is not the command.
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Wrapper words that may precede the real command without being it.
_PREFIX_WORDS: frozenset[str] = frozenset(
    {"!", "command", "do", "else", "exec", "if", "nohup", "sudo", "then", "time"}
)


def blank_heredoc(match: re.Match[str]) -> str:
    """Redact a heredoc body + its delimiter line, keeping the redirect line."""
    whole = match.group(0)
    inert = match.group("inert")
    return whole[: len(whole) - len(inert)] + NUL_FILLER * len(inert)


def owning_command(text: str, redirect_start: int) -> str:
    """The command word that owns the heredoc redirect at ``redirect_start``.

    Returns the basename, or ``""`` when no command word precedes the redirect
    on its own command (``cat <<EOF`` at the very start of a line yields
    ``cat``; a bare ``<<EOF`` yields ``""``).
    """
    preceding = text[:redirect_start]
    breaks = [m.end() for m in _COMMAND_BREAK.finditer(preceding)]
    segment = preceding[breaks[-1] :] if breaks else preceding
    for word in segment.split():
        if _ASSIGNMENT.match(word) or word in _PREFIX_WORDS:
            continue
        return word.rsplit("/", 1)[-1]
    return ""


def redact_heredoc_bodies(text: str) -> str:
    """Blank every heredoc body that is DATA, keeping the ones a shell runs.

    Length-preserving, like :func:`blank_heredoc`. A body owned by a
    :data:`SHELL_INTERPRETERS` command is left intact on purpose: it really is
    executed, and redacting it would turn an over-detect into an under-detect,
    which is the direction that reopens a gap rather than the one that prints a
    loud, one-line-fixable violation.
    """

    def replace(match: re.Match[str]) -> str:
        if owning_command(text, match.start()) in SHELL_INTERPRETERS:
            return match.group(0)
        return blank_heredoc(match)

    return HEREDOC_PATTERN.sub(replace, text)
