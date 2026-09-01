# Copyright (c) 2026 Raymond Manaloto
"""Inject the native-first requirement when a mise config file is edited.

A ``PostToolUse`` hook on ``Edit``/``Write``/``NotebookEdit``. When the edited
path is a mise configuration file, it returns ``hookSpecificOutput``
``additionalContext``; for every other path it returns nothing at all.

**Why a hook rather than a ``paths:``-scoped rule.** A path-scoped rule fires
when Claude *reads* a matching file (``md-size-budgets.md`` § "Scoping: the
trigger test"). A ``Write`` that replaces ``mise.toml`` wholesale never reads
it, so the rule would be absent in exactly the case it exists for. The hook
fires on the edit itself.

**Why this does not restate the rule.** ``.claude/rules/use-tool-builtins.md``
is unscoped and therefore already loaded every session, and Claude Code's hook
documentation is explicit that static conventions belong in CLAUDE.md, which
"loads without running a script". What a hook can add is the *conditional*
part: which file was just touched, where that tool's own docs are on this
disk, and the concrete near-miss. Re-injecting the rule body would duplicate
eager context and buy nothing.

**Why the text is phrased as statements.** Claude Code wraps
``additionalContext`` in a system reminder, and its docs warn that text "framed
as out-of-band system commands can trigger Claude's prompt-injection defenses,
which causes Claude to surface the text to you instead of treating it as
context". So every line here is a factual statement about the repository, not
an instruction to the model.

The motivating near-miss (2026-09-01): a custom ``{rc, gates[], outcome}``
result sink was scoped over several turns without anyone checking what mise
already provides. A review of mise's own 379-file doc corpus then found that
``MISE_LOG_FILE`` already supplies the uniform log *location* half, while the
*structured result* half is genuinely absent — a materially smaller build than
the one being scoped. The rule was in eager context the whole time; what was
missing was a prompt at the moment of the edit.
"""

from __future__ import annotations

import fnmatch
import json
import sys
import time
from pathlib import Path

#: Where the once-per-session marker lives. Repo-local and gitignored, so it
#: is per-clone by construction and `git clean -xdf` resets it harmlessly.
STATE_DIR = Path(".agent") / "state" / "mise-config-context"

#: Markers older than this are swept. No session lasts a week, so this cannot
#: delete a live session's marker; it only stops the directory growing forever.
MARKER_MAX_AGE_SECONDS = 7 * 24 * 60 * 60

#: Globs, repo-relative, matched against the edited path. Lockfiles are
#: deliberately absent: they are generated artifacts, and an edit to one is not
#: a place where a native-vs-custom decision is being made.
MISE_CONFIG_GLOBS: tuple[str, ...] = (
    "mise.toml",
    "mise.local.toml",
    "mise-system.toml",
    ".config/mise/config.toml",
    ".config/mise/conf.d/*.toml",
    ".devcontainer/mise-system.toml",
    ".devcontainer/mise-runtime.toml",
)

#: Where mise's own documentation is checked out on this machine. Named as a
#: fact rather than an instruction, per the docstring's phrasing note.
MISE_DOCS = (
    "~/dev/github/ray-manaloto/knowledge-base/sources/mise/docs (379 files, greppable)"
)

CONTEXT = """\
A mise configuration file was just edited: {path}

This repository gates changes here on `.claude/rules/use-tool-builtins.md`: a \
native mise setting, environment variable or built-in feature is preferred \
over custom code, and custom code that survives the check carries its \
justification in the commit body — which options were evaluated and why each \
was insufficient.

mise's own documentation is on this disk at {docs}, so the check costs a grep \
rather than a web fetch.

A worked instance from 2026-09-01: a custom `{{rc, gates[], outcome}}` result \
sink was scoped across several turns before anyone read those docs. mise turned \
out to already provide the uniform log-location half — `MISE_LOG_FILE` plus \
`MISE_LOG_FILE_LEVEL` — while the structured per-invocation result half is \
genuinely absent, because the only completed-result store mise documents is the \
task cache and "Only successful task runs are cached". The rule was in eager \
context throughout; what was missing was a prompt at the moment of the edit.\
"""


def matches(file_path: str, repo_root: Path) -> bool:
    """Whether ``file_path`` is one of this repo's mise config files.

    Paths outside the repository never match: an edit to a global
    ``~/.config/mise`` file is not this project's decision to govern.
    """
    if not file_path:
        return False
    try:
        rel = Path(file_path).resolve().relative_to(repo_root.resolve())
    except ValueError, OSError:
        return False
    posix = rel.as_posix()
    return any(fnmatch.fnmatch(posix, glob) for glob in MISE_CONFIG_GLOBS)


def build_payload(file_path: str, repo_root: Path) -> dict[str, object] | None:
    """The hook's JSON response, or None when the path is not in scope."""
    if not matches(file_path, repo_root):
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": CONTEXT.format(path=file_path, docs=MISE_DOCS),
        }
    }


def _marker(repo_root: Path, session_id: str) -> Path:
    return repo_root / STATE_DIR / f"{session_id}.seen"


def _prune(state_dir: Path) -> None:
    """Drop markers older than the age floor. Never fatal."""
    cutoff = time.time() - MARKER_MAX_AGE_SECONDS
    try:
        stale = [p for p in state_dir.glob("*.seen") if p.stat().st_mtime < cutoff]
    except OSError:
        return
    for path in stale:
        try:
            path.unlink()
        except OSError:
            continue


def already_seen(repo_root: Path, session_id: str) -> bool:
    """Whether this session was already told, recording it when it was not.

    The reminder is worth reading once per session; the tenth identical copy is
    the decay it exists to beat. planning-with-files reached the same
    conclusion — its changelog notes per-tool-call fires "stay quiet so the
    notice cannot become spam" (`inject-plan.sh:852-864` is the payload half of
    the same problem).

    Without a `session_id` there is nothing to key on, so it emits: an
    un-deduplicated reminder beats a silently disabled one.

    If the marker cannot be written it also emits, which makes a broken state
    directory NOISY rather than silent. That is the right way round — a
    repeating reminder is visible and fixable; a gate that quietly stopped
    firing is neither.
    """
    if not session_id:
        return False
    marker = _marker(repo_root, session_id)
    if marker.exists():
        return True
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        _prune(marker.parent)
        marker.write_text("")
    except OSError:
        return False
    return False


def mise_config_context_main(repo_root: Path) -> int:
    """Read a PostToolUse payload on stdin; print context when in scope.

    Always exits 0. A hook that fails closed on its own errors would block
    edits for a reminder, which is a far worse trade than a missed reminder —
    the same fail-open posture `hook_guard` takes, and for the same reason.
    """
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
        file_path = str((event.get("tool_input") or {}).get("file_path", ""))
        session_id = str(event.get("session_id", ""))
    except ValueError, OSError:
        return 0
    payload = build_payload(file_path, repo_root)
    if payload is None:
        return 0
    if already_seen(repo_root, session_id):
        return 0
    sys.stdout.write(json.dumps(payload))
    return 0
