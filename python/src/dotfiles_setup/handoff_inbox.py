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

The caller's identity is provider-qualified: ``CLAUDE_CODE_SESSION_ID`` resolves
through a harness job record's ``sessionId``; ``CODEX_THREAD_ID`` resolves
through an explicit ``coordinator-claim``. The newest coordinator is the max
over ``(createdAt, provider, id)``, whatever a harness record's ``state``: a
``done`` record is an idle session that may still be live, so a state filter
would let a superseded coordinator pass (Ray ruling 2026-10-03; the lockout a
dead record can cause belongs to the gate redesign). It is checked again once
the target's lock is held. A Codex claim uses compare-and-swap on the current
newest name, rechecked under the claims lock; ``none`` bootstraps an empty
store. ``coordinator-release`` retires only its caller's own claim. A Claude
job created between a claim's check and write is outside that lock and may
lose to the claim by timestamp; this inherent cross-provider race is accepted.

Limits, stated so nobody relies on more: the variables are caller-supplied, and
an Agent-tool subagent inherits its parent's session id, so a coordinator's
own delegates pass the gate, as does any process that exports the id or
points ``--jobs-dir`` or ``--claims-dir`` elsewhere. The gate stops a LANE session or a
SUPERSEDED coordinator writing by mistake; it is not an access control.

An edit list is JSON: a list of ``{"replace": <old>, "with": <new>}`` and
``{"append": <text>}`` objects. Every ``replace`` anchor must occur exactly
once in the current text, so a drifted file is refused rather than rewritten;
an ``append``-only list has no anchor and so cannot detect drift. All edits
are validated before anything is written; the write is an atomic replace,
preceded by a timestamped backup (the newest ``BACKUPS_KEPT`` per file are
kept). The lock orders this module's own writers only; a direct Edit of the
same file is not serialised against it.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotfiles_setup.session_common import (
    COORDINATOR_CLAIMS,
    HANDOFF_INBOX,
    SHIP_QUEUE,
    SessionError,
    default_jobs_dir,
    is_coordinator,
    job_record,
    main_checkout,
    now_iso,
    read_state,
    state_lock,
    write_state,
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
CODEX_ENV = "CODEX_THREAD_ID"
CLAIMS_FILE = "coordinator-claims.json"
BACKUPS_KEPT = 20

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


def _claims(claims_dir: Path | None) -> dict[str, Any]:
    if claims_dir is None:
        return {}
    path = claims_dir / CLAIMS_FILE
    try:
        store = read_state(path)
    except OSError as exc:
        msg = f"refused: {exc}"
        raise InboxError(msg) from exc
    claims = store.get("claims", {})
    if (
        (store and set(store) != {"claims"})
        or not isinstance(claims, dict)
        or any(
            not isinstance(claim, dict)
            or claim.get("provider") != "codex"
            or claim.get("threadId") != thread_id
            or not isinstance(thread_id, str)
            or not thread_id
            or not isinstance(claim.get("name"), str)
            or not is_coordinator(claim["name"])
            or _created_at(claim) is None
            or ("retired" in claim and not isinstance(claim["retired"], bool))
            for thread_id, claim in claims.items()
        )
    ):
        msg = f"refused: malformed claims store {path}"
        raise InboxError(msg)
    return claims


def _claude_records(jobs_dir: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(jobs_dir.glob("*/state.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue
        if isinstance(data, dict):
            records.append(data)
    return records


def _coordinators(jobs_dir: Path, claims: Mapping[str, Any]) -> list[dict[str, Any]]:
    coordinators = []
    for data in _claude_records(jobs_dir):
        other = data.get("name")
        at = _created_at(data)
        if (
            isinstance(other, str)
            and is_coordinator(other)
            and at is not None
            and isinstance(data.get("sessionId"), str)
            and data["sessionId"]
        ):
            coordinators.append(
                {"provider": "claude", "id": data["sessionId"], "name": other, "at": at}
            )
    coordinators.extend(
        {
            "provider": "codex",
            "id": thread_id,
            "name": claim["name"],
            "at": _created_at(claim),
        }
        for thread_id, claim in claims.items()
        if not claim.get("retired", False)
    )
    return coordinators


def _newest(coordinators: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not coordinators:
        return None
    return max(
        coordinators,
        key=lambda row: (row["at"], row["provider"], row["id"]),
    )


def require_newest_coordinator(
    env: Mapping[str, str], jobs_dir: Path, *, claims_dir: Path | None = None
) -> str:
    """The caller's name iff its provider and native ID identify the newest.

    Direct callers must opt into a claims store; ``None`` reads no live claims
    and preserves the isolated Claude-only interface.
    """
    session_id, thread_id = env.get(SESSION_ENV, ""), env.get(CODEX_ENV, "")
    if session_id and thread_id:
        msg = "refused: ambiguous provider identity (Claude and Codex are both set)"
        raise InboxError(msg)
    claims = _claims(claims_dir)
    provider = "claude" if session_id else "codex"
    native_id = session_id or thread_id
    own = job_record(session_id, jobs_dir) if session_id else claims.get(thread_id)
    name = None if own is None else own.get("name")
    if (
        own is None
        or not isinstance(name, str)
        or not is_coordinator(name)
        or (provider == "codex" and own.get("retired", False))
    ):
        msg = f"refused: caller is not a coordinator session (name={name!r})"
        raise InboxError(msg)
    newest = _newest(_coordinators(jobs_dir, claims))
    if (
        _created_at(own) is None
        or newest is None
        or (newest["provider"], newest["id"]) != (provider, native_id)
    ):
        msg = (
            f"refused: {name} is not the newest coordinator"
            f" (newest is {None if newest is None else newest['name']!r},"
            f" provider={None if newest is None else newest['provider']})"
        )
        raise InboxError(msg)
    return name


def _codex_id(env: Mapping[str, str]) -> str:
    thread_id = env.get(CODEX_ENV, "")
    if not thread_id.strip() or SESSION_ENV in env:
        msg = "refused: claim/release requires CODEX_THREAD_ID and no Claude identity"
        raise InboxError(msg)
    return thread_id


def coordinator_claim(
    env: Mapping[str, str],
    jobs_dir: Path,
    *,
    claims_dir: Path,
    takeover: tuple[str, str],
    now: Callable[[], datetime] | None = None,
) -> Path:
    """Compare-and-swap an explicit Codex takeover using existing state primitives.

    Neither harness provides this repository's cross-provider CAS; reuse the
    OS-backed state lock and atomic replace rather than a new lock protocol.
    """
    thread_id = _codex_id(env)
    name, supersedes = takeover
    if not is_coordinator(name):
        msg = f"refused: invalid coordinator name {name!r}"
        raise InboxError(msg)
    path = claims_dir / CLAIMS_FILE

    def checked_claims() -> tuple[dict[str, Any], dict[str, Any] | None]:
        claims = _claims(claims_dir)
        coordinators = _coordinators(jobs_dir, claims)
        newest = _newest(coordinators)
        expected = "none" if newest is None else newest["name"]
        if supersedes != expected:
            msg = (
                f"refused: --supersedes {supersedes!r} "
                f"does not match newest {expected!r}"
            )
            raise InboxError(msg)
        if any(row.get("name") == name for row in _claude_records(jobs_dir)) or any(
            claim["name"] == name and owner != thread_id
            for owner, claim in claims.items()
        ):
            msg = f"refused: coordinator name {name!r} is already used"
            raise InboxError(msg)
        return claims, newest

    checked_claims()
    with state_lock(path):
        claims, newest = checked_claims()
        moment = (now or (lambda: datetime.now(UTC)))()
        stamp = moment.isoformat(timespec="microseconds")
        if _created_at({"createdAt": stamp}) is None:
            msg = "refused: claim clock must be timezone-aware"
            raise InboxError(msg)
        if newest is not None and (moment, "codex", thread_id) <= (
            newest["at"],
            newest["provider"],
            newest["id"],
        ):
            msg = "refused: claim clock does not order after the newest coordinator"
            raise InboxError(msg)
        claims[thread_id] = {
            "provider": "codex",
            "threadId": thread_id,
            "name": name,
            "createdAt": stamp,
        }
        write_state(path, {"claims": claims})
    return path


def coordinator_release(env: Mapping[str, str], *, claims_dir: Path) -> Path:
    """Retire only the caller's own claim, even after another provider supersedes it."""
    thread_id = _codex_id(env)
    path = claims_dir / CLAIMS_FILE

    def checked_claims() -> dict[str, Any]:
        claims = _claims(claims_dir)
        if thread_id not in claims:
            msg = "refused: caller has no coordinator claim to release"
            raise InboxError(msg)
        return claims

    checked_claims()
    with state_lock(path):
        claims = checked_claims()
        claims[thread_id]["retired"] = True
        write_state(path, {"claims": claims})
    return path


def _key(checkout: Path, target: Path) -> str:
    """A per-file name unique across kinds: ``task_plan.md`` vs an inbox lane."""
    return str(target.relative_to(checkout)).replace("/", "__")


def lock_path(checkout: Path, target: Path) -> Path:
    """The lock base path ``_locked_write`` holds for ``target``."""
    return checkout / LOCK_SUBDIR / _key(checkout, target)


def _backup(checkout: Path, target: Path) -> None:
    if not target.exists():
        return
    key = _key(checkout, target)
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f")
    directory = checkout / BACKUP_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{key}.{stamp}").write_bytes(target.read_bytes())
    # The stamp sorts chronologically, so the oldest come first.
    for old in sorted(directory.glob(f"{key}.*"))[:-BACKUPS_KEPT]:
        old.unlink(missing_ok=True)


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
    with state_lock(lock_path(checkout, target)):
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
    claim_parser = sub.add_parser(
        "coordinator-claim", help="CAS takeover by a Codex session"
    )
    claim_parser.add_argument("--name", required=True)
    claim_parser.add_argument("--supersedes", required=True)
    sub.add_parser("coordinator-release", help="Retire the caller's own Codex claim")
    for child in sub.choices.values():
        child.add_argument(
            "--jobs-dir", type=Path, default=None, help="Override ~/.claude/jobs"
        )
        child.add_argument(
            "--claims-dir",
            type=Path,
            help="Override coordinator claims directory",
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
    jobs_dir = args.jobs_dir or default_jobs_dir()
    claims_dir = args.claims_dir or checkout / COORDINATOR_CLAIMS
    env = dict(os.environ)
    if command == "list":
        return _list(checkout)
    if command == "read":
        return _read(checkout, args.lane)
    if command == "append":
        lane = valid_lane(args.lane)
        written = append(checkout, lane, _body(args), title=args.title)
    elif command == "coordinator-claim":
        written = coordinator_claim(
            env,
            jobs_dir,
            claims_dir=claims_dir,
            takeover=(args.name, args.supersedes),
        )
    elif command == "coordinator-release":
        written = coordinator_release(env, claims_dir=claims_dir)
    else:

        def authorize() -> str:
            return require_newest_coordinator(env, jobs_dir, claims_dir=claims_dir)

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
    except (InboxError, SessionError, OSError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"handoff-inbox {args.inbox_command}: {exc}\n")
        return RC_REFUSED
