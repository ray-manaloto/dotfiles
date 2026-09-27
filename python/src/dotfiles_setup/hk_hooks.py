# Copyright (c) 2026 Raymond Manaloto
"""Which hk git hook events will actually RUN for a checkout, from any scope.

Since the hk 2 migration this repo no longer installs hooks from mise's
``postinstall``: upstream removed that recipe because it mutates
``.git/config`` during tool installs and races (jdx/hk#1376, discussion
#1375), and made ``hk install --global --mise`` the recommended setup. That
leaves a fresh clone with NO hooks until someone runs the install once per
machine, while ``.claude/rules/do-not.md`` #9 counts hk's pre-commit
``no_commit_to_branch`` as one of its enforcement layers. The doctor check
built on this module makes that gap loud instead of silent.

The question is answered by git itself, ``git hook list <event>`` (Git 2.54),
not by parsing config keys: it reports the EFFECTIVE hooks, so a hook disabled
with ``hook.<name>.enabled = false`` prints as ``disabled<TAB><name>`` and a
legacy ``.git/hooks/<event>`` script prints as ``hook from hookdir``. A raw
``hook.hk-*.event`` read counted the disabled one and missed the legacy one
(codex review of 302f93d4). Measured on git 2.54.0: no hook -> rc 1 with
"no hooks found"; configured -> ``hk-<event>``; disabled -> ``disabled<TAB>…``;
executable hookdir script -> ``hook from hookdir``; non-executable -> rc 1.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

#: What `git hook list` prints for an executable legacy `.git/hooks/<event>`.
HOOKDIR_ENTRY = "hook from hookdir"
#: A legacy hookdir script counts as hk's only if it invokes hk this way.
HK_SHIM_MARKER = "hk run"


class HookConfigUnreadableError(RuntimeError):
    """Git could not answer, so absence cannot be concluded."""


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _hookdir_script_is_hk(repo_root: Path, event: str) -> bool:
    located = _git(repo_root, "rev-parse", "--git-path", f"hooks/{event}")
    if located.returncode != 0:
        return False
    script = repo_root / located.stdout.strip()
    try:
        return HK_SHIM_MARKER in script.read_text(errors="replace")
    except OSError:
        return False


def event_has_hk_hook(repo_root: Path, event: str) -> bool:
    """Whether an ENABLED hk hook will run for ``event`` in this checkout.

    Raises:
        HookConfigUnreadableError: git failed for a reason other than "no
            hooks found", so a negative answer would be a false "missing".
    """
    listed = _git(repo_root, "hook", "list", event)
    if listed.returncode == 1 and "no hooks found" in listed.stderr:
        return False
    if listed.returncode != 0:
        detail = listed.stderr.strip() or f"rc={listed.returncode}"
        raise HookConfigUnreadableError(detail)
    entries = listed.stdout.splitlines()
    if f"hk-{event}" in entries:
        return True
    return HOOKDIR_ENTRY in entries and _hookdir_script_is_hk(repo_root, event)


def missing_events(repo_root: Path, required: Iterable[str]) -> list[str]:
    """Required events with no enabled hk hook, in the order declared."""
    return [event for event in required if not event_has_hk_hook(repo_root, event)]
