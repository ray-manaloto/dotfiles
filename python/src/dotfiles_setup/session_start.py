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

The timestamp comes from ``session_common.stamped_name`` /
``chicago_stamp`` — one formatter for both mods.

Spec: ``docs/specs/coordinator-auto-handoff-2026-10-02.md`` §8.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from dotfiles_setup import reap
from dotfiles_setup.session_common import (
    PROJECT,
    StateLockedError,
    chicago_stamp,
    default_jobs_dir,
    job_record,
    now_iso,
    read_state,
    stamped_name,
    state_lock,
    valid_session_id,
    write_state,
)
from dotfiles_setup.session_orphans import _session_root

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

type StartAction = Literal[
    "keep",
    "rename",
    "defer",
    "nonconforming",
    "unknown",
    "already-ran",
    "non-interactive",
    "invalid-session-id",
    "state-write-failed",
    "state-locked",
]


@dataclass(frozen=True)
class StartDecision:
    """What the hook acts on; mirrored by ``parseStart`` in ``register.ts``."""

    action: StartAction
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
    processes: tuple[reap.Process, ...] | None = None
    self_pid: int | None = None


def user_name(session_id: str, deps: StartDeps) -> tuple[str | None, bool]:
    """User name plus whether absence is known; spares without records fail closed.

    Harness-generated names are not -n names. Foreground sessions lack job
    records, so reuse the measured nearest-Claude ancestry walk to read argv.
    """
    record = job_record(session_id, deps.jobs_dir)
    if record is not None and record.get("nameSource") == "user":
        name = record.get("name")
        return (name, True) if isinstance(name, str) and name else (None, False)
    try:
        processes = reap.snapshot() if deps.processes is None else deps.processes
    except reap.ReapError:
        return None, False
    root = _session_root(
        processes, os.getpid() if deps.self_pid is None else deps.self_pid
    )
    command = next((p.command for p in processes if p.pid == root), None)
    if command is None:
        return None, record is not None
    try:
        argv = shlex.split(command)
    except ValueError:
        return None, False
    return _argv_name(argv, record_present=record is not None)


def _argv_name(argv: list[str], *, record_present: bool) -> tuple[str | None, bool]:
    """Resolve explicit naming flags before the foreground/spare fallback."""
    for index, arg in enumerate(argv):
        if arg in {"-n", "--name"}:
            if index + 1 < len(argv) and not argv[index + 1].startswith("-"):
                return argv[index + 1], True
            return None, False
        if arg.startswith("--name="):
            name = arg.removeprefix("--name=")
            return (name, True) if name else (None, False)
    spare = "--bg-spare" in argv or "bg-pty-host" in argv
    return None, record_present or not spare


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
    request: StartRequest, deps: StartDeps
) -> tuple[StartAction, str | None, str | None]:
    """``(action, name, prefix)`` for a session seen for the first time."""
    name, known = user_name(request.session_id, deps)
    if not known:
        return "unknown", None, None
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
    action: StartAction, session_id: str, warnings: tuple[str, ...] = ()
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
    try:
        with state_lock(path):
            state = read_state(path)
            if "action" in state:
                return _repeat(request, state)
            action, name, prefix = _classify(request, deps)
            state.update(
                {"at": now_iso(), "action": action, "name": name, "prefix": prefix}
            )
            write_state(path, state)
    except StateLockedError as exc:
        return _inert("state-locked", request.session_id, (str(exc),))
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
    """Record a resolved rename, preserving concurrent session bookkeeping."""
    if not valid_session_id(session_id):
        logger.error("session-start renamed: invalid session id %r", session_id)
        return 2
    path = state_dir / f"{session_id}.json"
    try:
        with state_lock(path):
            state = read_state(path)
            if "action" not in state:
                logger.error(
                    "session-start renamed: no decision recorded for %s", session_id
                )
                return 2
            state["renamed"] = {"at": now_iso(), "name": name}
            write_state(path, state)
    except OSError:
        logger.exception("session-start renamed: state write failed")
        return 1
    return 0


def pending(session_id: str, state_dir: Path) -> StartDecision:
    """Recover a pending rename after a plugin reload, without reloading again."""
    if not valid_session_id(session_id):
        return _inert("invalid-session-id", session_id)
    try:
        with state_lock(state_dir / f"{session_id}.json"):
            state = read_state(state_dir / f"{session_id}.json")
    except StateLockedError as exc:
        return _inert("state-locked", session_id, (str(exc),))
    except OSError as exc:
        return _inert("state-write-failed", session_id, (str(exc),))
    if state.get("action") == "rename" and state.get("renamed") is None:
        name = state.get("name")
        if isinstance(name, str):
            return StartDecision(
                action="rename",
                reload=False,
                name=name,
                prefix=None,
                session_id=session_id,
            )
    return _repeat(StartRequest(session_id, Path.cwd()), state)


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
        "renamed", help="Record that rename resolved successfully"
    )
    renamed_parser.add_argument("--session-id", required=True)
    renamed_parser.add_argument("--name", required=True)
    pending_parser = sub.add_parser(
        "pending", help="Read pending naming state after plugin reload"
    )
    pending_parser.add_argument("--session-id", required=True)
    for child in (decide_parser, renamed_parser, pending_parser):
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
    if args.session_start_command == "pending":
        sys.stdout.write(pending(args.session_id, state_dir).to_json() + "\n")
        return 0
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
