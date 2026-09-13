# Copyright (c) 2026 Raymond Manaloto
"""The operator's path to planning-with-files attestation.

Attestation is a HUMAN approval boundary: the hash says a person read the plan
and blessed those exact bytes. The plugin tries to enforce that with
``disable-model-invocation: true`` on its ``/plan-attest`` command, and on this
host that is decorative — the command's own body is
``sh ${CLAUDE_PLUGIN_ROOT}/scripts/attest-plan.sh``, so the flag stops the model
*invoking the command* while leaving the *script* one plain Bash call away. An
agent crossed exactly that line on 2026-09-02 by self-attesting.

The real layer is a ``permissions.deny`` rule in ``.claude/settings.json``
covering the scripts AND this task — hard bans belong in permission rules rather
than the PreToolUse hook, which fails open on its own errors (#343,
``.claude/rules/mise-tasks-only.md`` § Enforcement layers). That deny is
deliberately total: it also denies ``/plan-attest`` and this task when the MODEL
runs them, because the choice is binary. ``disable-model-invocation`` never
distinguished "the operator directed this" from "the agent decided the operator
would have", and the agent that would decide that wrong is the one already
holding the keyboard.

So this module exists to give the human back a path that does not require typing
a version-pinned cache path::

    ! mise run plan-attest

⚠️ **The bare form WRITES.** ``plan-attest`` with no arguments locks the plan's
current bytes; ``--show`` is the read-only form. This is not hypothetical
hygiene — smoke-testing this very wrapper with no arguments attested a tampered
plan over the operator's hash while the module was being written, without
invoking ``/plan-attest`` at all. That is the whole D4 argument reproduced by
accident, and it is why the deny rule below covers this task too rather than
trusting anyone's intent. Verify with ``--show``, never bare.

⚠️ **That read-only form was UNREACHABLE for eleven days** (2026-09-02 to
2026-09-13). The CLI declares this passthrough as an ``nargs="*"`` positional,
and argparse claims any dash-prefixed token as an unknown *option* rather than a
value for it, so ``plan-attest --show`` died at ``unrecognized arguments:
--show`` while the BARE form — the one that WRITES — ran fine. The documented
recipe said ``-- --show``, which cannot help: ``mise run`` consumes one ``--`` of
its own, so the operator's ``mise run plan-attest -- --show`` arrived here as a
bare ``--show`` regardless. Every doc site was therefore wrong at the call site
while being right about the declaration. :func:`insert_passthrough_separator`
fixes it in the one place that binds both.

The leading ``!`` is shell mode: it is not a tool call, so no permission rule and
no PreToolUse hook sees it. That property is read from the harness docs
(``$CC/interactive-mode.md:316-325``) rather than probed, because an agent cannot
type ``!`` — the operator arms it in one line.

The plugin root is resolved through :func:`listing_budget.plugin_root`, the
resolver this repo already has and already argued for (highest numeric version,
never mtime, never ``installed_plugins.json``). Re-deriving it here would be a
second source of one truth.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from dotfiles_setup.listing_budget import plugin_root

# `<name>@<marketplace>`; the pwf plugin publishes its own single-plugin
# marketplace, so both halves are the same string.
logger = logging.getLogger(__name__)

PLUGIN_ID = "planning-with-files@planning-with-files"

# Relative to the resolved plugin root. `.sh` rather than `.ps1`: this repo is
# macOS/Linux, and the PowerShell twin is denied alongside it in settings.json
# so a future Windows clone cannot route around the ban.
ATTEST_SCRIPT = Path("scripts") / "attest-plan.sh"


# The subcommand whose arguments belong to the plugin's script, not to us.
PASSTHROUGH_COMMAND = "plan-attest"


def insert_passthrough_separator(argv: Sequence[str]) -> list[str]:
    """Return ``argv`` with an argparse ``--`` before plan-attest's own flags.

    ``plan-attest`` forwards everything after it to the plugin's script, but the
    CLI declares that tail as an ``nargs="*"`` positional and argparse claims any
    dash-prefixed token as an unknown OPTION instead. The read-only ``--show``
    therefore exited 2 while the BARE form, which WRITES the attestation, ran —
    a documented safe path that could only fail, guarding a destructive one that
    could only work.

    Documentation could not repair that, which is why this is code. ``mise run``
    eats one ``--`` of its own before the task's command line is built (measured:
    ``mise run <task> -- --help`` reaches the program as ``--help``), so the
    operator's ``mise run plan-attest -- --show`` arrives here as a bare
    ``--show`` however the recipe is written. Restating the recipe as
    ``-- -- --show`` would bind the call site at the cost of every existing doc
    site being wrong; inserting the separator here makes all of them true.

    Deliberately narrow: only ``plan-attest``, and only when its first argument
    already looks like a flag. ``lock-tools``/``lock-shared``/``env-blob-scan``
    take variadic positionals too, but theirs are tool keys and paths that are
    never dash-prefixed, and ``process git-isolated`` uses ``REMAINDER``, which
    absorbs a flag as long as the FIRST token is a program name — as a child
    command's always is. This is the only passthrough whose leading token is
    legitimately a flag.

    Idempotent: an argv already carrying the separator is returned unchanged, so
    ``plan-attest -- --show`` keeps working for anyone who learned that form —
    inserting a second one would forward a literal ``--`` to the script.

    The subcommand is matched at position 0 only. The root parser declares no
    global options (every ``add_argument`` in ``main.py`` is subparser-local), so
    a ``plan-attest`` appearing later is a positional VALUE of some other
    command, not this one.

    Args:
        argv: The raw argument vector, without the program name.

    Returns:
        A new list, separator inserted only where the conditions above hold.
    """
    args = list(argv)
    if not args or args[0] != PASSTHROUGH_COMMAND:
        return args
    tail = args[1:]
    if not tail or tail[0] == "--" or not tail[0].startswith("-"):
        return args
    return [args[0], "--", *tail]


class PluginNotInstalledError(RuntimeError):
    """The pwf plugin is not in the cache, so there is nothing to run."""


def resolve_attest_script(home: Path) -> Path:
    """Absolute path to the plugin's attest script.

    Raises:
        PluginNotInstalledError: When the plugin, or the script inside it, is
            absent. The message names what was looked for — an operator seeing
            this needs to know whether the plugin is disabled or the script was
            renamed upstream, and those have different fixes.
    """
    root = plugin_root(home, PLUGIN_ID)
    if root is None:
        message = (
            f"{PLUGIN_ID} is not in {home}/.claude/plugins/cache — "
            "the plugin is not installed, so there is no plan to attest"
        )
        raise PluginNotInstalledError(message)
    script = root / ATTEST_SCRIPT
    if not script.is_file():
        message = (
            f"{script} is missing from an otherwise-present {PLUGIN_ID} — "
            "upstream may have renamed or moved it"
        )
        raise PluginNotInstalledError(message)
    return script


def plan_attest_main(argv: list[str] | None = None) -> int:
    """Run the plugin's attest script, passing every argument straight through.

    Deliberately NOT an argparse front end. The flags belong to upstream
    (``--show``, ``--clear``), they change between releases, and a wrapper that
    enumerated them would silently drop a new one — the
    ``.claude/rules/ai-cli-invocation.md`` failure mode, where a remembered flag
    list outlives the CLI it describes.

    Returns:
        The script's exit code, or 1 when the plugin could not be resolved.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        script = resolve_attest_script(Path.home())
    except PluginNotInstalledError:
        # `.exception` rather than `.error`: the traceback is the fast path to
        # "is the plugin disabled, or did upstream rename the script", and the
        # two have different fixes.
        logger.exception("plan-attest: cannot resolve the attest script")
        return 1
    completed = subprocess.run(["sh", str(script), *args], check=False)
    return completed.returncode
