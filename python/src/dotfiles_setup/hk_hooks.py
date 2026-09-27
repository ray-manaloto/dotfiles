# Copyright (c) 2026 Raymond Manaloto
"""Which hk git hook events are installed for a checkout, from ANY scope.

Since the hk 2 migration this repo no longer installs hooks from mise's
``postinstall``: upstream removed that recipe because it mutates
``.git/config`` during tool installs and races (jdx/hk#1376, discussion
#1375), and made ``hk install --global --mise`` the recommended setup. That
leaves a fresh clone with NO hooks until someone runs the install once per
machine, while ``.claude/rules/do-not.md`` #9 counts hk's pre-commit
``no_commit_to_branch`` as one of its enforcement layers. The doctor check
built on this module makes that gap loud instead of silent.

Git 2.54 config-based hooks are ``hook.<name>.command`` + ``hook.<name>.event``
pairs; hk names its entries ``hk-<event>``. ``git config --get-regexp`` run in
the checkout reads the merged system/global/local view, so a global install
and a per-repo install both count, which is exactly the question: "will hk run
on this event here?"
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

#: The prefix hk gives its config-based hook entries (`hk install` source).
HK_HOOK_PREFIX = "hook.hk-"


class HookConfigUnreadableError(RuntimeError):
    """`git config` could not answer, so absence cannot be concluded."""


def installed_hk_events(repo_root: Path) -> set[str]:
    """Return the hook events that have an hk entry in the merged git config.

    Raises:
        HookConfigUnreadableError: git failed for a reason other than "no
            matching key", so an empty answer would be a false "missing".
    """
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "config",
            "--get-regexp",
            r"^hook\.hk-.*\.event$",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    # rc 1 is git's documented "no key matched"; anything else is an error.
    if result.returncode == 1 and not result.stdout:
        return set()
    if result.returncode != 0:
        detail = result.stderr.strip() or f"rc={result.returncode}"
        raise HookConfigUnreadableError(detail)
    events: set[str] = set()
    for line in result.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key.startswith(HK_HOOK_PREFIX) and value:
            events.add(value.strip())
    return events


def missing_events(required: Iterable[str], installed: set[str]) -> list[str]:
    """Required events with no hk entry, in the order they were declared."""
    return [event for event in required if event not in installed]
