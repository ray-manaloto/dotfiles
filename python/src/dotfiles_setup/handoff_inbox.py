# Copyright (c) 2026 Raymond Manaloto
"""Sanctioned writes to the main checkout's gitignored coordination files.

Lanes and watchers run isolated in linked worktrees, where the harness refuses
an Edit/Write of a main-checkout path, and Ray's ruling (b) of 2026-10-03
forbids routing that write through Bash. This module is the route instead,
behind ``mise run handoff-inbox -- <verb>``. It works from any linked worktree,
because the main checkout is resolved by ``session_common.main_checkout``.

Any caller:

- ``append`` adds one record to ``.agent/plans/handoff-inbox/<lane>.md``
  (``session_common.HANDOFF_INBOX``, re-exported by ``coordinator_handoff``).
- ``list`` and ``read`` show what is there.

The newest coordinator only (Ray ruled 2026-10-03 ~15:00):

- ``plan-apply`` applies a typed edit list to ``task_plan.md``.
- ``queue-append`` appends to ``.agent/plans/main-checkout-ship-queue.md``.
- ``inbox-edit`` applies a typed edit list to an inbox file (the stale-brief fix).

The caller's identity is ``CLAUDE_CODE_SESSION_ID`` resolved through its
harness job record; it must carry a coordinator name and the newest
``createdAt`` of every coordinator-named record. The environment variable is
caller-supplied, so this check guards against a lane or a superseded
coordinator writing by mistake, not against a hostile process.

An edit list is JSON: a list of ``{"replace": <old>, "with": <new>}`` and
``{"append": <text>}`` objects. Every ``replace`` anchor must occur exactly
once in the current text (an anchor assert, so an empty or drifted file can
never be silently rewritten). All edits are validated before anything is
written; the write is an atomic replace, preceded by a timestamped backup.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotfiles_setup.session_common import (
    HANDOFF_INBOX,
    SHIP_QUEUE,
    SessionError,
    default_jobs_dir,
    is_coordinator,
    job_record,
    main_checkout,
    now_iso,
    state_lock,
)

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Mapping

logger = logging.getLogger(__name__)

LANE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
TASK_PLAN = Path("task_plan.md")
LOCK_SUBDIR = Path(".agent") / "state" / "handoff-inbox"
BACKUP_SUBDIR = LOCK_SUBDIR / "backups"
SESSION_ENV = "CLAUDE_CODE_SESSION_ID"

RC_OK = 0
RC_NOT_FOUND = 1
RC_REFUSED = 2


class InboxError(RuntimeError):
    """A request that must not write anything."""


@dataclass(frozen=True)
class Replace:
    """Replace the one occurrence of ``old`` with ``new``."""

    old: str
    new: str


@dataclass(frozen=True)
class Append:
    """Append ``text`` at the end of the file."""

    text: str


Edit = Replace | Append


def parse_edits(payload: object) -> tuple[Edit, ...]:
    """A typed edit list from decoded JSON; any other shape is refused."""
    if not isinstance(payload, list) or not payload:
        msg = "edit list must be a non-empty JSON list"
        raise InboxError(msg)
    edits: list[Edit] = []
    for index, item in enumerate(payload):
        if isinstance(item, dict) and set(item) == {"replace", "with"}:
            old, new = item["replace"], item["with"]
            if isinstance(old, str) and old and isinstance(new, str):
                edits.append(Replace(old, new))
                continue
        elif isinstance(item, dict) and set(item) == {"append"}:
            text = item["append"]
            if isinstance(text, str) and text.strip():
                edits.append(Append(text))
                continue
        msg = (
            f"edit {index} must be {{'replace': <non-empty str>, 'with': <str>}} "
            "or {'append': <non-empty str>}"
        )
        raise InboxError(msg)
    return tuple(edits)


def apply_edits(text: str, edits: tuple[Edit, ...]) -> str:
    """Apply every edit in order, refusing the whole list on any bad anchor."""
    for index, edit in enumerate(edits):
        if isinstance(edit, Replace):
            count = text.count(edit.old)
            if count != 1:
                msg = f"edit {index}: anchor occurs {count} times, expected exactly 1"
                raise InboxError(msg)
            text = text.replace(edit.old, edit.new, 1)
        else:
            text = text.rstrip("\n") + "\n\n" + edit.text.strip("\n") + "\n"
    return text


def record(title: str, body: str, *, stamp: str) -> str:
    """One appended inbox record."""
    return f"\n## {stamp} — {title}\n\n{body.strip()}\n"


def valid_lane(lane: str) -> str:
    """The lane name, or InboxError for anything that could escape the inbox."""
    if LANE_RE.fullmatch(lane) is None:
        msg = f"invalid lane name {lane!r}: must match {LANE_RE.pattern}"
        raise InboxError(msg)
    return lane


def _created_at(record_: Mapping[str, Any]) -> datetime | None:
    raw = record_.get("createdAt")
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    # A naive stamp cannot be ordered against the harness's UTC ones.
    return parsed if parsed.tzinfo is not None else None


def require_newest_coordinator(env: Mapping[str, str], jobs_dir: Path) -> str:
    """The caller's coordinator name, or InboxError when it is not the newest."""
    session_id = env.get(SESSION_ENV, "")
    own = job_record(session_id, jobs_dir) if session_id else None
    name = None if own is None else own.get("name")
    if own is None or not isinstance(name, str) or not is_coordinator(name):
        msg = f"refused: caller is not a coordinator session (name={name!r})"
        raise InboxError(msg)
    own_at = _created_at(own)
    newest: tuple[datetime, str] | None = None
    for path in sorted(jobs_dir.glob("*/state.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue
        other = data.get("name") if isinstance(data, dict) else None
        at = _created_at(data) if isinstance(data, dict) else None
        if (
            isinstance(other, str)
            and is_coordinator(other)
            and at is not None
            and (newest is None or at > newest[0])
        ):
            newest = (at, other)
    if own_at is None or newest is None or newest[0] != own_at:
        msg = (
            f"refused: {name} is not the newest coordinator"
            f" (newest is {None if newest is None else newest[1]!r})"
        )
        raise InboxError(msg)
    return name


def _backup(checkout: Path, target: Path) -> None:
    if not target.exists():
        return
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f")
    backup = checkout / BACKUP_SUBDIR / f"{target.name}.{stamp}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(target.read_bytes())


def _replace_atomically(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)


def _locked_write(
    checkout: Path,
    target: Path,
    transform: Callable[[str, str], str],
    *,
    authorize: Callable[[], str] | None = None,
) -> None:
    """Authorize, read, transform and replace ``target`` under its own lock.

    ``authorize`` runs only once the lock is held, so a coordinator superseded
    while this call waited for the lock (or for its input) is refused rather
    than writing on the strength of a check made before the takeover. Its
    result, the caller's name, is handed to ``transform``.
    """
    lock = checkout / LOCK_SUBDIR / target.name
    with state_lock(lock):
        caller = authorize() if authorize is not None else ""
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        updated = transform(current, caller)
        _backup(checkout, target)
        _replace_atomically(target, updated)


def inbox_dir(checkout: Path) -> Path:
    """The main checkout's fallback inbox."""
    return checkout / HANDOFF_INBOX


def append(checkout: Path, lane: str, body: str, *, title: str | None = None) -> Path:
    """Append one record to ``<inbox>/<lane>.md``; return the path written."""
    target = inbox_dir(checkout) / f"{valid_lane(lane)}.md"
    if not body.strip():
        msg = "refused: empty body"
        raise InboxError(msg)
    if title is not None and (not title.strip() or "\n" in title):
        msg = "refused: --title must be one non-empty line"
        raise InboxError(msg)
    entry = record(title or lane, body, stamp=now_iso())
    _locked_write(checkout, target, lambda current, _caller: current + entry)
    return target


def edit_file(
    checkout: Path,
    target: Path,
    edits: tuple[Edit, ...],
    *,
    authorize: Callable[[], str] | None = None,
) -> Path:
    """Apply a typed edit list to an existing file; return the path written."""
    if not target.is_file():
        msg = f"refused: {target} does not exist"
        raise InboxError(msg)
    _locked_write(
        checkout,
        target,
        lambda current, _caller: apply_edits(current, edits),
        authorize=authorize,
    )
    return target


def ship_queue(checkout: Path) -> Path:
    """The main checkout's ship queue."""
    return checkout / SHIP_QUEUE


def add_subcommands(parser: argparse.ArgumentParser) -> None:
    """``coordinator-handoff inbox <verb>``: the six verbs in the module docstring."""
    sub = parser.add_subparsers(dest="inbox_command", required=True)
    append_parser = sub.add_parser("append", help="Append one record to <lane>.md")
    append_parser.add_argument("--lane", required=True)
    append_parser.add_argument("--title", default=None)
    for child in (
        append_parser,
        sub.add_parser(
            "queue-append", help="Append to the ship queue (newest coordinator only)"
        ),
    ):
        source = child.add_mutually_exclusive_group()
        source.add_argument("--message", default=None)
        source.add_argument("--file", type=Path, default=None)
    sub.add_parser("list", help="One line per inbox file: name, bytes, mtime")
    read_parser = sub.add_parser("read", help="Print <lane>.md verbatim")
    read_parser.add_argument("--lane", required=True)
    plan_parser = sub.add_parser(
        "plan-apply",
        help="Apply an edit list to task_plan.md (newest coordinator only)",
    )
    plan_parser.add_argument("--edits", type=Path, required=True)
    edit_parser = sub.add_parser(
        "inbox-edit", help="Apply an edit list to <lane>.md (newest coordinator only)"
    )
    edit_parser.add_argument("--lane", required=True)
    edit_parser.add_argument("--edits", type=Path, required=True)
    for child in sub.choices.values():
        child.add_argument(
            "--jobs-dir", type=Path, default=None, help="Override ~/.claude/jobs"
        )


def _body(args: argparse.Namespace) -> str:
    if args.message is not None:
        return args.message
    if args.file is not None:
        return args.file.read_text(encoding="utf-8")
    return sys.stdin.read()


def _edits(path: Path) -> tuple[Edit, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        msg = f"refused: {path} is not JSON: {exc}"
        raise InboxError(msg) from exc
    return parse_edits(payload)


def _list(checkout: Path) -> int:
    directory = inbox_dir(checkout)
    for path in sorted(directory.glob("*.md")) if directory.is_dir() else ():
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).astimezone()
        sys.stdout.write(
            f"{path.name}\t{stat.st_size}\t{mtime.isoformat(timespec='seconds')}\n"
        )
    return RC_OK


def _read(checkout: Path, lane: str) -> int:
    target = inbox_dir(checkout) / f"{valid_lane(lane)}.md"
    if not target.is_file():
        logger.error("handoff-inbox read: no inbox file %s", target)
        return RC_NOT_FOUND
    sys.stdout.write(target.read_text(encoding="utf-8"))
    return RC_OK


def _dispatch(args: argparse.Namespace, checkout: Path) -> int:
    command = args.inbox_command
    if command == "list":
        return _list(checkout)
    if command == "read":
        return _read(checkout, args.lane)
    if command == "append":
        written = append(checkout, args.lane, _body(args), title=args.title)
    else:
        jobs_dir = args.jobs_dir or default_jobs_dir()
        env = dict(os.environ)

        def authorize() -> str:
            return require_newest_coordinator(env, jobs_dir)

        # Fail fast for a caller that is plainly not the coordinator, before
        # reading any input; the binding check is the one inside the lock.
        authorize()
        if command == "queue-append":
            body = _body(args)
            if not body.strip():
                msg = "refused: empty body"
                raise InboxError(msg)
            written = ship_queue(checkout)
            _locked_write(
                checkout,
                written,
                lambda current, caller: current + record(caller, body, stamp=now_iso()),
                authorize=authorize,
            )
        elif command == "plan-apply":
            written = edit_file(
                checkout, checkout / TASK_PLAN, _edits(args.edits), authorize=authorize
            )
        else:
            target = inbox_dir(checkout) / f"{valid_lane(args.lane)}.md"
            written = edit_file(
                checkout, target, _edits(args.edits), authorize=authorize
            )
    sys.stdout.write(f"{written}\n")
    return RC_OK


def main(args: argparse.Namespace) -> int:
    """Dispatch one parsed ``coordinator-handoff inbox`` invocation."""
    try:
        checkout = main_checkout(Path.cwd())
        return _dispatch(args, checkout)
    except (InboxError, SessionError, OSError) as exc:
        sys.stderr.write(f"handoff-inbox {args.inbox_command}: {exc}\n")
        return RC_REFUSED
