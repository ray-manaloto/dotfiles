# Copyright (c) 2026 Raymond Manaloto
"""The all-session ``session-start`` mod's judgement (requirements item 23).

``.claude/skills/session-start/hooks/register.ts`` fires on ``session.start``
in interactive sessions, asks :func:`decide` once per session id, queues
``/reload-skills`` + ``/reload-plugins --force``, and names the session from
the answer:

- ``keep`` — the bg job record's ``-n`` name already matches the convention
  ``<project>-<yyyyMMdd'T'HHmmss.SSSSSSSSSX>.<feature>``;
- ``rename`` — no ``-n`` name and the cwd branch is not the default branch: the
  feature is the branch slug;
- ``defer`` — no ``-n`` name on the default branch (or no branch): the hook
  renames at the first prompt, appending a model-made slug to ``prefix``;
- ``nonconforming`` — a ``-n`` name outside the convention: NEVER renamed
  (lanes are addressed by it); the hook toasts instead.

The state file is written BEFORE answering, so a reload that re-fires
``session.start`` answers ``already-ran`` — which carries a still-pending
``defer`` prefix, because a reload discards the hook module's memory.

The timestamp comes from ``coordinator_handoff.stamped_name`` /
``chicago_stamp`` — one formatter for both mods.

Spec: ``docs/specs/coordinator-auto-handoff-2026-10-02.md`` §8.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.coordinator_handoff import (
    PROJECT,
    chicago_stamp,
    default_jobs_dir,
    now_iso,
    read_state,
    session_name,
    stamped_name,
    valid_session_id,
    write_state,
)

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable

    Runner = Callable[..., subprocess.CompletedProcess[str]]

logger = logging.getLogger(__name__)

CONFORMING_NAME_RE = re.compile(
    r"^(dotfiles|kb)-\d{8}T\d{6}\.\d{9}(Z|[+-]\d{2}(\d{2})?)\..+$"
)
BRANCH_PREFIX_RE = re.compile(r"^(?:feat|fix|docs|chore|refactor|test)/")
STATE_SUBDIR = Path(".agent") / "state" / "session-start"
FALLBACK_DEFAULT_BRANCH = "main"
_GIT_TIMEOUT_S = 10


@dataclass(frozen=True)
class StartDecision:
    """What the hook acts on; mirrored by ``parseStart`` in ``register.ts``."""

    action: str
    reload: bool
    name: str | None
    prefix: str | None
    session_id: str
    warnings: tuple[str, ...] = ()

    def to_json(self) -> str:
        """One JSON object."""
        return json.dumps(
            {
                "action": self.action,
                "reload": self.reload,
                "name": self.name,
                "prefix": self.prefix,
                "session_id": self.session_id,
                "warnings": list(self.warnings),
            },
            sort_keys=True,
        )


@dataclass(frozen=True)
class StartRequest:
    """One ``session.start`` as the hook reports it."""

    session_id: str
    cwd: Path
    interactive: bool = True
    project: str = PROJECT


@dataclass(frozen=True)
class StartDeps:
    """Every collaborator of :func:`decide`, injectable for the tests."""

    state_dir: Path
    jobs_dir: Path = field(default_factory=default_jobs_dir)
    now_ns: int | None = None
    runner: Runner | None = None


def feature_slug(branch: str) -> str:
    """Branch minus one ``feat/|fix/|docs/|chore/|refactor/|test/``; ``/`` → ``-``."""
    return BRANCH_PREFIX_RE.sub("", branch, count=1).replace("/", "-")


def is_conforming(name: str) -> bool:
    """Whether ``name`` follows ``<project>-<Chicago ISO ns>.<feature>``."""
    return CONFORMING_NAME_RE.fullmatch(name) is not None


def _git(cwd: Path, args: list[str], runner: Runner) -> str | None:
    try:
        result = runner(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def current_branch(cwd: Path, runner: Runner) -> str | None:
    """The checked-out branch, or ``None`` when detached or not a repository."""
    branch = _git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"], runner)
    return None if branch in {None, "HEAD"} else branch


def default_branch(cwd: Path, runner: Runner) -> str:
    """``origin/HEAD``'s branch, else ``main``."""
    ref = _git(cwd, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], runner)
    if ref is None:
        return FALLBACK_DEFAULT_BRANCH
    return ref.removeprefix("origin/")


def _classify(
    request: StartRequest, name: str | None, deps: StartDeps
) -> tuple[str, str | None, str | None]:
    """``(action, name, prefix)`` for a session seen for the first time."""
    if name is not None:
        return ("keep" if is_conforming(name) else "nonconforming"), name, None
    now_ns = time.time_ns() if deps.now_ns is None else deps.now_ns
    runner = deps.runner or subprocess.run
    branch = current_branch(request.cwd, runner)
    slug = None if branch is None else feature_slug(branch)
    if branch is None or not slug or branch == default_branch(request.cwd, runner):
        return "defer", None, f"{request.project}-{chicago_stamp(now_ns)}"
    return "rename", stamped_name(request.project, slug, now_ns), None


def _repeat(request: StartRequest, state: dict[str, object]) -> StartDecision:
    """``already-ran``, carrying a ``defer`` prefix that is still pending."""
    stored_name = state.get("name")
    stored_prefix = state.get("prefix")
    pending = (
        state.get("action") == "defer"
        and state.get("renamed") is None
        and isinstance(stored_prefix, str)
    )
    return StartDecision(
        action="already-ran",
        reload=False,
        name=stored_name if isinstance(stored_name, str) else None,
        prefix=stored_prefix if pending and isinstance(stored_prefix, str) else None,
        session_id=request.session_id,
    )


def _inert(
    action: str, session_id: str, warnings: tuple[str, ...] = ()
) -> StartDecision:
    """An answer the hook acts on by doing nothing but its status line."""
    return StartDecision(
        action=action,
        reload=False,
        name=None,
        prefix=None,
        session_id=session_id,
        warnings=warnings,
    )


def decide(request: StartRequest, deps: StartDeps) -> StartDecision:
    """Once per session id: reload + one naming action (§8 Q1a-Q4a)."""
    if not request.interactive:
        return _inert("non-interactive", request.session_id)
    if not valid_session_id(request.session_id):
        return _inert("invalid-session-id", request.session_id)
    path = deps.state_dir / f"{request.session_id}.json"
    state = read_state(path)
    if "action" in state:
        return _repeat(request, state)
    action, name, prefix = _classify(
        request, session_name(request.session_id, deps.jobs_dir), deps
    )
    state.update({"at": now_iso(), "action": action, "name": name, "prefix": prefix})
    try:
        write_state(path, state)  # state before answer: once per session id
    except OSError as exc:
        return _inert(
            "state-write-failed", request.session_id, (f"state write failed: {exc}",)
        )
    return StartDecision(
        action=action,
        reload=True,
        name=name,
        prefix=prefix,
        session_id=request.session_id,
    )


def mark_renamed(session_id: str, name: str, state_dir: Path) -> int:
    """Record that a deferred rename was queued, so no reload repeats it."""
    if not valid_session_id(session_id):
        logger.error("session-start renamed: invalid session id %r", session_id)
        return 2
    path = state_dir / f"{session_id}.json"
    state = read_state(path)
    if "action" not in state:
        logger.error("session-start renamed: no decision recorded for %s", session_id)
        return 2
    state["renamed"] = {"at": now_iso(), "name": name}
    try:
        write_state(path, state)
    except OSError:
        logger.exception("session-start renamed: state write failed")
        return 1
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────────


def add_subcommands(parser: argparse.ArgumentParser) -> None:
    """``session-start {decide,renamed}``."""
    sub = parser.add_subparsers(dest="session_start_command", required=True)
    decide_parser = sub.add_parser(
        "decide", help="JSON reload/naming decision for one new session (rc 0)"
    )
    decide_parser.add_argument("--session-id", required=True)
    decide_parser.add_argument("--cwd", type=Path, required=True)
    decide_parser.add_argument(
        "--project", default=PROJECT, help="Name prefix (dotfiles | kb)"
    )
    decide_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="A -p/SDK session: answer non-interactive and do nothing",
    )
    renamed_parser = sub.add_parser(
        "renamed", help="Record that the deferred rename was queued"
    )
    renamed_parser.add_argument("--session-id", required=True)
    renamed_parser.add_argument("--name", required=True)
    for child in (decide_parser, renamed_parser):
        child.add_argument(
            "--state-dir",
            type=Path,
            default=None,
            help="Override <project>/.agent/state/session-start",
        )
    decide_parser.add_argument(
        "--jobs-dir", type=Path, default=None, help="Override ~/.claude/jobs"
    )


def main(args: argparse.Namespace, project_root: Path) -> int:
    """Dispatch one parsed ``session-start`` invocation."""
    state_dir = args.state_dir or project_root / STATE_SUBDIR
    if args.session_start_command == "renamed":
        return mark_renamed(args.session_id, args.name, state_dir)
    decision = decide(
        StartRequest(
            session_id=args.session_id,
            cwd=args.cwd,
            interactive=not args.non_interactive,
            project=args.project,
        ),
        StartDeps(state_dir=state_dir, jobs_dir=args.jobs_dir or default_jobs_dir()),
    )
    sys.stdout.write(decision.to_json() + "\n")
    return 0
