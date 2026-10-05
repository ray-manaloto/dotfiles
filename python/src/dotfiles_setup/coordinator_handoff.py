# Copyright (c) 2026 Raymond Manaloto
"""Coordinator auto-handoff at a context-occupancy limit.

The ``session.measure`` function hook in
``.claude/skills/coordinator-handoff/hooks/register.ts`` owns only a cheap
pre-filter; every judgement lives here (zero-bash-logic):

- ``decide`` — is this session a coordinator (read from its bg job record, fail
  closed), and has its context crossed the next firing level? The fired level
  is persisted BEFORE ``fire`` is returned, so a crash re-fires only at the next
  step, never every turn.
- ``successor_name`` / ``successor_brief`` / ``launch`` — start the named
  successor with ``claude --bg`` from the main checkout, after recording a
  census of this session's live heavy runs (ship/land/sync/...).
- ``retire`` — run by the SUCCESSOR: refuses to ``claude stop`` the old
  coordinator while any recorded heavy run is still alive and unadopted, and
  (independently) while the old session's harness tasks are in flight.

The census must be taken by the OLD session at launch, inside its own process
tree: bg sessions run as claimed spares whose argv carries no session id, so
the successor cannot find the old tree by ``ps`` (probed 2026-10-02).

``session_common.stamped_name`` is the timestamp formatter shared with the
``session-start`` mod: ``<project>-<Chicago ISO ns>.<x>``.

Spec: ``docs/specs/coordinator-auto-handoff-2026-10-02.md``.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from dotfiles_setup import handoff_inbox, reap
from dotfiles_setup.session_common import (
    HANDOFF_INBOX,
    PROJECT,
    SHIP_QUEUE,
    SHORT_ID_LEN,
    STATE_LOCK_TIMEOUT_S,
    StateLockedError,
    StateUnreadableError,
    default_jobs_dir,
    is_coordinator,
    job_record,
    main_checkout,
    now_iso,
    read_state,
    session_name,
    stamped_name,
    state_lock,
    valid_session_id,
    write_state,
)
from dotfiles_setup.session_common import SessionError as CoordinatorHandoffError
from dotfiles_setup.session_orphans import _session_root

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Mapping

    Runner = Callable[..., subprocess.CompletedProcess[str]]

logger = logging.getLogger(__name__)

COORDINATOR_FEATURE = "coordinator"

ENV_LIMIT = "DOTFILES_COORDINATOR_HANDOFF_PCT"
ENV_STEP = "DOTFILES_COORDINATOR_HANDOFF_STEP_PCT"
DEFAULT_LIMIT_PCT = 30.0
DEFAULT_STEP_PCT = 5.0
_MAX_PCT = 100.0
#: Absorbs float noise in ``(percent - limit) / step`` so 35.0 at step 5 is k=1.
_LEVEL_EPSILON = 1e-9
STOP_TIMEOUT_S = 60
LAUNCH_TIMEOUT_S = 60
LAUNCH_PENDING_TTL_S = 15 * 60
_LSOF_TIMEOUT_S = 10
_SHELLS = frozenset({"sh", "bash", "zsh", "dash"})

type DecisionReason = Literal[
    "fire",
    "not-coordinator",
    "below-limit",
    "below-next-step",
    "already-launched",
    "launch-in-progress",
    "probe-done",
    "probe-in-progress",
    "invalid-session-id",
    "invalid-percent",
    "state-write-failed",
    "state-locked",
    "state-unreadable",
]

STATE_SUBDIR = Path(".agent") / "state" / "coordinator-handoff"
CROSS_SESSION_SETTINGS = json.dumps(
    {"crossSessionInbound": "accept", "worktree": {"bgIsolation": "none"}},
    separators=(",", ":"),
)

#: Long operations a coordinator may own when it hands off. The tasks first,
#: then their python entrypoints (`mise.toml` `run =` lines, and the
#: knowledge-base's `kb-setup ship|land`), so a run is recognised whichever
#: process of its chain the census sees. `(?![\w-])` keeps `ship-queue` out.
HEAVY_COMMAND_RE = re.compile(
    r"(?:^|[\s/'\";&|(])"
    r"(?:mise\s+(?:-C\s+(?:\"[^\"]+\"|'[^']+'|\S+)\s+)?run\s+(?:--\s+)?"
    r"(?:dev-rebuild|up|persistence|gate|lock-image|lock-shared|kb-ship|kb-land|"
    r"ship|land|sync|verify-local|verify-container-latest|bounded-wait|automerge)"
    r"|dotfiles-setup\s+(?:pr\s+(?:ship|land)|docker\s+sync|bounded-wait)"
    r"|kb-setup\s+(?:ship|land))"
    r"(?![\w-])"
)
#: The first stdout redirect target in a command line (`> FILE`, `>> FILE`,
#: `1> FILE`), never an fd duplication such as `2>&1`.
_REDIRECT_RE = re.compile(
    r"(?:^|[\s;])1?>>?\s*(?!&)(?:\"([^\"]*)\"|'([^']*)'|([^\s;&|<>]+))"
)
#: The handoff section the old coordinator queues every open question into
#: (ruling 12). A level-2 heading; the section ends at the next level-2 one.
_QUEUED_HEADING_RE = re.compile(
    r"^##[ \t]+Queued questions\b[^\n]*$", re.MULTILINE | re.IGNORECASE
)
_ANY_QUEUED_HEADING_RE = re.compile(
    r"^#+[^\n]*\bqueued questions\b[^\n]*$", re.MULTILINE | re.IGNORECASE
)
_NEXT_H2_RE = re.compile(r"^##\s", re.MULTILINE)


# ── configuration ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Config:
    """The firing limit and re-fire step, plus every fallback that was taken."""

    limit_pct: float
    step_pct: float
    warnings: tuple[str, ...]


def _parse_pct(
    env: Mapping[str, str], key: str, default: float, warnings: list[str]
) -> float:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or not 0 < value <= _MAX_PCT:
        warnings.append(
            f"{key}={raw!r} is not a number in (0, 100]; using the default {default:g}"
        )
        return default
    return value


def load_config(env: Mapping[str, str]) -> Config:
    """Read the limit and step; an invalid value falls back AND is reported."""
    warnings: list[str] = []
    limit = _parse_pct(env, ENV_LIMIT, DEFAULT_LIMIT_PCT, warnings)
    step = _parse_pct(env, ENV_STEP, DEFAULT_STEP_PCT, warnings)
    return Config(limit_pct=limit, step_pct=step, warnings=tuple(warnings))


# ── decision ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Decision:
    """What the hook acts on. ``level``: the fired level, else the next one."""

    fire: bool
    reason: DecisionReason
    level: float | None
    session_id: str
    name: str | None
    percent: float
    warnings: tuple[str, ...]

    def to_json(self) -> str:
        """One JSON object; the hook's ``parseDecision`` mirrors this shape."""
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        return json.dumps(payload, sort_keys=True)


def next_level(last_fired: float | None, cfg: Config) -> float:
    """The limit when nothing fired yet, else one step above the last fire."""
    return cfg.limit_pct if last_fired is None else last_fired + cfg.step_pct


def fired_level(percent: float, cfg: Config) -> float:
    """The highest ``limit + k*step`` (k >= 0) that is <= ``percent``."""
    if percent < cfg.limit_pct:
        return cfg.limit_pct
    steps = math.floor((percent - cfg.limit_pct) / cfg.step_pct + _LEVEL_EPSILON)
    return cfg.limit_pct + steps * cfg.step_pct


def _last_fired(state: Mapping[str, Any], key: str = "last_fired") -> float | None:
    value = state.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) else None


@dataclass(frozen=True)
class DecideRequest:
    """One measurement; preview modes have independent firing bookkeeping."""

    session_id: str
    percent: float
    no_commit: bool = False
    probe: bool = False
    dry_run: bool = False


def _launch_in_progress(state: Mapping[str, Any], warnings: list[str]) -> bool:
    """An unconfirmed start blocks for 15 minutes; unreadable ages are stale."""
    if "launch_pending" not in state:
        return False
    pending = state["launch_pending"]
    at = pending.get("at") if isinstance(pending, dict) else None
    age = None
    if isinstance(at, str):
        try:
            age = (
                datetime.fromisoformat(now_iso()) - datetime.fromisoformat(at)
            ).total_seconds()
        except ValueError, TypeError:
            age = None
    if age is None:
        warnings.append("launch_pending age unknown; treating as stale and ignoring")
        return False
    if age < LAUNCH_PENDING_TTL_S:
        return True
    warnings.append(f"stale launch_pending from {at} ignored (age {age:g}s)")
    return False


def _started_pending(state: Mapping[str, Any]) -> dict[str, Any] | None:
    pending = state.get("launch_pending")
    if isinstance(pending, dict) and pending.get("started") is True:
        return pending
    return None


def _started_path(path: Path) -> Path:
    """Independent receipt survives failure to reacquire the session lock."""
    return path.with_suffix(".started.json")


def _read_launch_state(path: Path) -> dict[str, Any]:
    """Recover a started receipt before any firing, relaunch or retirement."""
    receipt = read_state(_started_path(path))
    try:
        state = read_state(path)
    except StateUnreadableError:
        if receipt.get("started") is not True or _recorded_runs(receipt) is None:
            raise
        logger.warning(
            "coordinator-handoff: recovering unreadable state from started receipt"
        )
        state = {"census": receipt["census"]}
    if receipt.get("started") is True and "launch" not in state:
        state["launch_pending"] = receipt
        if "census" not in state and "census" in receipt:
            state["census"] = receipt["census"]
    return state


def _judge(
    state: dict[str, Any], request: DecideRequest, cfg: Config, warnings: list[str]
) -> tuple[bool, DecisionReason, float | None]:
    """Fire under the transaction lock, charging only the requested mode."""
    if "launch" in state or _started_pending(state) is not None:
        return False, "already-launched", None
    if _launch_in_progress(state, warnings):
        return False, "launch-in-progress", None
    if request.probe and state.get("probe_fired"):
        return False, "probe-done", None
    if request.probe and state.get("probe_pending"):
        return False, "probe-in-progress", None
    key = "dry_run_fired" if request.dry_run else "last_fired"
    last = None if request.probe else _last_fired(state, key)
    threshold = next_level(last, cfg)
    if request.percent < threshold:
        return False, ("below-limit" if last is None else "below-next-step"), threshold
    # max(): a limit/step change between fires can place fired_level under the
    # threshold; never record a level that re-fires sooner.
    level = max(fired_level(request.percent, cfg), threshold)
    if request.probe:
        state["probe_pending"] = True
    elif request.dry_run:
        state["dry_run_fired"] = level
    elif not request.no_commit:
        state["previous_fired"] = last
        state["last_fired"] = level
    return True, "fire", level


def decide(
    request: DecideRequest,
    *,
    env: Mapping[str, str],
    jobs_dir: Path,
    state_dir: Path,
    timeout_s: float = STATE_LOCK_TIMEOUT_S,
) -> Decision:
    """Fire once at the limit, then once per step above it — coordinators only.

    ``last_seen`` is written on every coordinator call so a reader can tell "never
    measured" from "measured, below". On a fire, ``last_fired`` is persisted
    BEFORE returning; when that write fails the answer is ``fire: False``.
    """
    session_id, percent = request.session_id, request.percent
    cfg = load_config(env)
    warnings = list(cfg.warnings)
    fire = False
    level: float | None = None
    name: str | None = None
    reason: DecisionReason
    if not valid_session_id(session_id):
        reason = "invalid-session-id"
    elif not math.isfinite(percent) or not 0 <= percent <= _MAX_PCT:
        reason = "invalid-percent"
    else:
        path = state_dir / f"{session_id}.json"
        name = session_name(session_id, jobs_dir)
        if not is_coordinator(name):
            return Decision(
                fire=False,
                reason="not-coordinator",
                level=None,
                session_id=session_id,
                name=name,
                percent=percent,
                warnings=tuple(warnings),
            )
        try:
            with state_lock(path, timeout_s=timeout_s):
                state = _read_launch_state(path)
                state["last_seen"] = {"at": now_iso(), "percent": percent}
                fire, reason, level = _judge(state, request, cfg, warnings)
                write_state(path, state)
        except StateLockedError as exc:
            warnings.append(str(exc))
            fire, reason = False, "state-locked"
        except StateUnreadableError as exc:
            warnings.append(str(exc))
            fire, reason = False, "state-unreadable"
        except OSError as exc:
            warnings.append(f"state write failed: {exc}")
            fire, reason = False, "state-write-failed"
    return Decision(
        fire=fire,
        reason=reason,
        level=level,
        session_id=session_id,
        name=name,
        percent=percent,
        warnings=tuple(warnings),
    )


def _rollback_fire(state: dict[str, Any], level: float | None) -> bool:
    """Restore the preceding level only if this exact real fire is still current."""
    if level is None or "launch" in state or _last_fired(state) != level:
        return False
    previous = state.pop("previous_fired", None)
    if previous is None:
        state.pop("last_fired", None)
    else:
        state["last_fired"] = previous
    return True


def release(
    session_id: str,
    level: float | None = None,
    *,
    state_dir: Path,
    mode: Literal["level", "probe", "probe-delivered"] = "level",
    timeout_s: float = STATE_LOCK_TIMEOUT_S,
) -> int:
    """Undo only this undelivered fire; never erase a newer fire or a launch."""
    if not valid_session_id(session_id):
        logger.error("coordinator-handoff release: invalid-session-id")
        return 2
    if mode == "level" and (
        level is None or not math.isfinite(level) or not 0 < level <= _MAX_PCT
    ):
        logger.error("coordinator-handoff release: invalid-level")
        return 2
    path = state_dir / f"{session_id}.json"
    try:
        with state_lock(path, timeout_s=timeout_s):
            state = _read_launch_state(path)
            if mode != "level":
                if state.pop("probe_pending", False) and mode == "probe-delivered":
                    state["probe_fired"] = True
                write_state(path, state)
            elif "launch_pending" not in state and _rollback_fire(state, level):
                write_state(path, state)
    except OSError:
        logger.exception("coordinator-handoff release failed")
        return 2
    return 0


def successor_name(now_ns: int) -> str:
    """``dotfiles-yyyyMMdd'T'HHmmss.<9-digit ns><X>.coordinator`` in Chicago."""
    return stamped_name(PROJECT, COORDINATOR_FEATURE, now_ns)


# ── repository + transcript lookups ──────────────────────────────────────────


def transcript_path(session_id: str, projects_dir: Path) -> Path | None:
    """``<projects_dir>/<project slug>/<session_id>.jsonl``, if one exists."""
    if not valid_session_id(session_id):
        return None
    matches = sorted(projects_dir.glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def queued_questions(handoff_text: str) -> str | None:
    """The non-empty H2 section body, allowing qualifiers after its title."""
    heading = _QUEUED_HEADING_RE.search(handoff_text)
    if heading is None:
        return None
    rest = handoff_text[heading.end() :]
    following = _NEXT_H2_RE.search(rest)
    body = (rest if following is None else rest[: following.start()]).strip()
    return body or None


def _unparsed_queued_heading(handoff_text: str) -> str | None:
    """Quote a heading mentioning queued questions when no valid H2 exists."""
    if _QUEUED_HEADING_RE.search(handoff_text) is not None:
        return None
    heading = _ANY_QUEUED_HEADING_RE.search(handoff_text)
    return heading.group().rstrip() if heading is not None else None


# ── census ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HeavyRun:
    """One live long operation the old coordinator owned at launch."""

    pid: int
    argv: str
    log_path: str | None


def _log_path(command: str) -> str | None:
    # Bash-tool wrappers redirect their snapshot prelude to /dev/null before eval.
    # Only the user's final eval payload can supply the fallback redirect.
    _, wrapper, payload = command.rpartition("eval '")
    if wrapper:
        try:
            command = shlex.split("'" + payload)[0]
        except ValueError, IndexError:
            command = payload.rstrip("'")
    match = _REDIRECT_RE.search(command)
    if match is None:
        return None
    target = next(group for group in match.groups() if group is not None)
    if target == "/dev/null":
        return None
    return (f"unexpanded:{target}" if "$" in target else target) or None


def stdout_log(pid: int, *, runner: Runner | None = None) -> str | None:
    """Resolve fd 1 through native lsof; only an existing regular file is a log."""
    try:
        result = (runner or subprocess.run)(
            ["lsof", "-a", "-p", str(pid), "-d", "1", "-Fn"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_LSOF_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning(
            "coordinator-handoff census: fd 1 unavailable for pid %d: %s", pid, exc
        )
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("n") and Path(line[1:]).is_file():
            path = Path(line[1:])
            if "tasks" in path.parts and path.suffix == ".output":
                return f"harness-output:{path}"
            return str(path)
    return None


def _heavy_log_process(
    pid: int, by_pid: Mapping[int, reap.Process]
) -> reap.Process | None:
    """First non-shell heavy command in the subtree, self-first depth-first."""
    children: dict[int, list[int]] = {}
    for process in by_pid.values():
        children.setdefault(process.ppid, []).append(process.pid)
    stack = [pid]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if current in seen or current not in by_pid:
            continue
        seen.add(current)
        process = by_pid[current]
        try:
            argv = shlex.split(process.command)
        except ValueError:
            argv = []
        if (
            argv
            and Path(argv[0]).name not in _SHELLS
            and HEAVY_COMMAND_RE.search(process.command)
        ):
            return process
        stack.extend(sorted(children.get(current, ()), reverse=True))
    return None


def _process_cwd(pid: int, runner: Runner | None) -> Path | None:
    """Read the selected process's cwd, never the census caller's cwd."""
    try:
        result = (runner or subprocess.run)(
            ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_LSOF_TIMEOUT_S,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if (
                line.startswith("n")
                and Path(line[1:]).is_absolute()
                and Path(line[1:]).is_dir()
            ):
                return Path(line[1:])
    return None


def _run_log(
    pid: int, by_pid: Mapping[int, reap.Process], runner: Runner | None
) -> str | None:
    """Use the command's fd 1, then resolve redirect text against its cwd."""
    process = _heavy_log_process(pid, by_pid)
    if process is not None:
        log = stdout_log(process.pid, runner=runner)
        if log is not None:
            return log
    # The outer shell can carry redirect syntax that is absent from the command's argv.
    owner = process or by_pid[pid]
    fallback = _log_path(owner.command) or _log_path(by_pid[pid].command)
    if (
        fallback is None
        or fallback.startswith("unexpanded:")
        or Path(fallback).is_absolute()
    ):
        return fallback
    cwd = _process_cwd(owner.pid, runner)
    if cwd is None:
        logger.warning(
            "coordinator-handoff census: relative log %r unresolved for pid %d",
            fallback,
            owner.pid,
        )
        return None
    return str((cwd / fallback).resolve())


def census(
    processes: tuple[reap.Process, ...],
    *,
    self_pid: int,
    root_pid: int | None = None,
    runner: Runner | None = None,
) -> tuple[HeavyRun, ...]:
    """The outermost heavy descendants of this session, minus the caller's chain.

    The root is the nearest ``claude`` ancestor of ``self_pid`` —
    ``session_orphans._session_root``, reused rather than reimplemented.
    ``root_pid`` overrides it for a caller whose tree has no ``claude`` (tests,
    CI). No root at all raises: an empty census would read as "nothing live",
    and that is the answer retire must never be handed by default.

    One logical run is a chain (`zsh -c 'mise run ship > LOG'` → mise → uv →
    python), every link matching; only the OUTERMOST is recorded, because it
    lives exactly as long as the run and is the one pid to wait on or adopt.
    """
    root = root_pid if root_pid is not None else _session_root(processes, self_pid)
    if root is None:
        msg = "no claude ancestor found; the census cannot see this session's tree"
        raise CoordinatorHandoffError(msg)
    by_pid = {process.pid: process for process in processes}
    own_chain = frozenset(reap.ancestor_pids(processes, self_pid))
    heavy = {
        pid
        for pid in reap.descendant_pids(processes, root)
        if pid in by_pid
        and pid not in own_chain
        and HEAVY_COMMAND_RE.search(by_pid[pid].command)
    }
    runs: list[HeavyRun] = []
    for pid in sorted(heavy):
        ancestors = reap.ancestor_pids(processes, by_pid[pid].ppid)
        if any(ancestor in heavy for ancestor in ancestors):
            continue
        command = by_pid[pid].command
        runs.append(HeavyRun(pid, command, _run_log(pid, by_pid, runner)))
    return tuple(runs)


# ── brief ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BriefContext:
    """Everything the successor's first prompt carries (requirements 11-22)."""

    old_name: str
    old_session_id: str
    old_transcript: Path | None
    handoff: Path
    ship_queue: Path
    inbox: Path
    state_dir: Path
    heavy_runs: tuple[HeavyRun, ...] = ()
    queued: str | None = None
    unparsed_queued_heading: str | None = None


def successor_brief(ctx: BriefContext) -> str:
    """The successor's first prompt: rules, review, notify, settle, retire."""
    short_id = ctx.old_session_id[:SHORT_ID_LEN]
    transcript = str(ctx.old_transcript) if ctx.old_transcript else "NOT FOUND (say so)"
    if ctx.heavy_runs:
        run_lines = "\n".join(
            f"  - pid {run.pid}: {run.argv}  (log: {run.log_path or 'none'})"
            + (
                " — no rc file — wait on pid exit"
                if run.log_path is None or run.log_path.startswith("harness-output:")
                else ""
            )
            for run in ctx.heavy_runs
        )
    else:
        run_lines = "  - none recorded"
    if ctx.queued:
        queued = ctx.queued
    elif ctx.unparsed_queued_heading:
        queued = (
            "WARNING: queued-questions heading exists but could not be parsed: "
            f"`{ctx.unparsed_queued_heading}` — inspect the handoff in step 1"
        )
    else:
        queued = (
            "none found — confirm the handoff's `## Queued questions` section in step 1"
        )
    return f"""\
You are the NEW dotfiles coordinator. You take over from `{ctx.old_name}` \
(session {ctx.old_session_id}), which handed off automatically at its context \
limit (the coordinator-handoff skill). Work unattended.

Handover record:
- old coordinator: `{ctx.old_name}`, session `{ctx.old_session_id}` (short \
`{short_id}`)
- old transcript: `{transcript}`
- handoff: `{ctx.handoff}`
- ship queue: `{ctx.ship_queue}`
- handoff state directory: `{ctx.state_dir}` (pass this exact --state-dir to retire)
- heavy runs the old coordinator owned at launch (census):
{run_lines}

Standing rules (they supersede anything older in the handoff):
- AUTONOMY: coordinate autonomously. Ask Ray ONLY for human-intervention \
items (an action the harness denies to agents, credential rotation). This \
supersedes "ask Ray before each GitHub write".
- QUESTIONS: every AskUserQuestion puts the recommended option first (label \
ends "(Recommended)"), gives each option PRO: and CON:, cites a path, #issue \
or URL, adds notes where they help, leaves "Other" to the harness, and ends \
with one open "anything else?" question.
- LANES report to you BY NAME (SendMessage to your session name); fallback \
`{ctx.inbox}/<lane>.md`. Read that directory now, at start.
- HOST SLOT: one heavy test/gate run host-wide at a time; one shipper per \
repository (dotfiles ships from its main checkout).
- NEWEST COORDINATOR is found by ListAgents recency or the notify message, \
never by sorting names (legacy `dotfiles-20261002b.coordinator` sorts after \
`dotfiles-20261002T…`).

Queued questions from the handoff (put each to Ray in the QUESTIONS format):
{queued}

First actions, in order:
1. Do not announce the takeover yet. Spawn a read-only review subagent over \
the old transcript against the handoff; fix anything lost, incorrect or vague \
in the handoff AND in `task_plan.md` (you are the coordinator; it is yours).
2. SendMessage every ListAgents lane your session name as the new coordinator \
(the fallback inbox rule is unchanged).
3. For each recorded heavy run: wait for it (`mise run bounded-wait` on its \
resolved log's rc line) or adopt its result explicitly. A log marked \
`unexpanded:` is unresolved redirect text: find its real path first; never \
wait on a literal `$LOG` or an absent log.
   A log marked `harness-output:` has no rc file — wait on pid exit, then \
review its output; do not bounded-wait on an rc line there.
   With no log, wait on pid exit.
4. Retire the old session ONLY through the gate — never a bare `claude stop` \
on a coordinator: `mise run coordinator-handoff -- retire --old-session \
{ctx.old_session_id} --state-dir {shlex.quote(str(ctx.state_dir))} \
[--adopted PID ...]`. It blocks (rc 1) while a recorded \
run is live and unadopted, or while the old session's harness tasks are in \
flight or unknown (`--accept-inflight` overrides that deliberately). Codes: \
0 = retired; 1 = BLOCKED (wait/adopt or deliberately accept inFlight); \
2 = refused (invalid role/id, missing launch or unreadable state); \
3 = stop failed (missing claude, 60s timeout or nonzero stop rc, printed). \
Never treat rc 3 as a reason to wait for heavy work.
5. Put the queued questions to Ray.
6. Resume the ship queue.
"""


def launch_argv(name: str, brief: str) -> list[str]:
    """Coordinator argv: accept cross-session inbound and edit the working copy."""
    return ["claude", "--bg", "-n", name, "--settings", CROSS_SESSION_SETTINGS, brief]


# ── launch ───────────────────────────────────────────────────────────────────


def default_projects_dir() -> Path:
    """The harness transcripts root."""
    return Path.home() / ".claude" / "projects"


@dataclass(frozen=True)
class LaunchDeps:
    """Every collaborator of :func:`launch`, injectable for the tests."""

    state_dir: Path | None = None
    jobs_dir: Path = field(default_factory=default_jobs_dir)
    projects_dir: Path = field(default_factory=default_projects_dir)
    cwd: Path | None = None
    processes: tuple[reap.Process, ...] | None = None
    self_pid: int | None = None
    root_pid: int | None = None
    now_ns: int | None = None
    runner: Runner | None = None
    out: Callable[[str], object] | None = None
    lock_timeout_s: float = STATE_LOCK_TIMEOUT_S


def _write(deps: LaunchDeps, text: str) -> None:
    (deps.out or sys.stdout.write)(text)


def _gather(handoff: Path, deps: LaunchDeps) -> tuple[tuple[HeavyRun, ...], str] | str:
    """``(census, handoff text)``, or why one is unavailable."""
    try:
        table = reap.snapshot() if deps.processes is None else deps.processes
        runs = census(
            table,
            self_pid=os.getpid() if deps.self_pid is None else deps.self_pid,
            root_pid=deps.root_pid,
            runner=deps.runner,
        )
    except (
        CoordinatorHandoffError,
        reap.ReapError,
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        return f"census-unavailable: {exc}"
    try:
        handoff_text = handoff.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return f"handoff-unreadable: {exc}"
    return runs, handoff_text


@dataclass(frozen=True)
class LaunchContext:
    """Validated launch identity and its canonical repository/state paths."""

    handoff: Path
    old_session_id: str
    old_name: str
    checkout: Path
    state_dir: Path


def _launch_identity(handoff: Path, old_session_id: str, jobs_dir: Path) -> str | None:
    """Validate the old session and handoff before touching launch state."""
    if not valid_session_id(old_session_id):
        logger.error("coordinator-handoff launch: invalid-session-id")
        return None
    if not handoff.is_file():
        logger.error("coordinator-handoff launch: handoff %s does not exist", handoff)
        return None
    name = session_name(old_session_id, jobs_dir)
    if not is_coordinator(name):
        logger.error(
            "coordinator-handoff launch: session %s is not a coordinator (name %r)",
            old_session_id,
            name,
        )
        return None
    return name


def launch(
    handoff: Path,
    old_session_id: str,
    *,
    dry_run: bool,
    deps: LaunchDeps,
) -> int:
    """Reserve a start, run unlocked with a bound, then record its outcome.

    rc 0: started and recorded (dry-run only prints, records/executes nothing).
    rc 2: refused for invalid identity/handoff, existing/pending launch, or
    unavailable worktree, census, lock or state. rc 3: start failed (missing
    binary, timeout or nonzero rc); keep the fired level for the next step.
    rc 4: successor STARTED but not recorded — do not relaunch. A durable
    started receipt protects decide/launch/retire even if the session lock fails.
    """
    old_name = _launch_identity(handoff, old_session_id, deps.jobs_dir)
    if old_name is None:
        return 2
    try:
        checkout = main_checkout(
            Path.cwd() if deps.cwd is None else deps.cwd, runner=deps.runner
        )
    except CoordinatorHandoffError, OSError, subprocess.TimeoutExpired:
        logger.exception("coordinator-handoff launch: worktree-unavailable")
        return 2
    try:
        state_dir = deps.state_dir or checkout / STATE_SUBDIR
        path = state_dir / f"{old_session_id}.json"
        ctx = LaunchContext(handoff, old_session_id, old_name, checkout, state_dir)
        with state_lock(path, timeout_s=deps.lock_timeout_s):
            state = _read_launch_state(path)
            if "launch" in state or _started_pending(state) is not None:
                record = state.get("launch") or _started_pending(state)
                successor = (
                    record.get("successor", record.get("name", "unknown"))
                    if isinstance(record, dict)
                    else "unknown"
                )
                logger.error(
                    "coordinator-handoff launch: already launched %s", successor
                )
                return 2
            warnings: list[str] = []
            pending = _launch_in_progress(state, warnings)
            for warning in warnings:
                logger.warning("coordinator-handoff launch: %s", warning)
            if pending:
                logger.error("coordinator-handoff launch: launch-in-progress")
                return 2
            prepared = _launch_locked(ctx, deps, state, dry_run=dry_run)
    except StateLockedError:
        logger.exception("coordinator-handoff launch: state-locked")
        prepared = 2
    except StateUnreadableError:
        logger.exception("coordinator-handoff launch: state-unreadable")
        prepared = 2
    except OSError:
        logger.exception("coordinator-handoff launch: state-write-failed")
        prepared = 2
    if isinstance(prepared, int):
        return prepared
    argv, record, runs = prepared
    # A slow external start must not monopolise the state transaction lock.
    return _start_successor(ctx, deps, argv, record, runs)


def _launch_locked(
    ctx: LaunchContext,
    deps: LaunchDeps,
    state: dict[str, Any],
    *,
    dry_run: bool,
) -> tuple[list[str], dict[str, str], tuple[HeavyRun, ...]] | int:
    """Gather and reserve while locked; return the external call to run unlocked."""
    handoff, old_session_id = ctx.handoff, ctx.old_session_id
    checkout, state_dir = ctx.checkout, ctx.state_dir
    gathered = _gather(handoff, deps)
    if isinstance(gathered, str):
        logger.error("coordinator-handoff launch: %s", gathered)
        return 2
    runs, handoff_text = gathered
    name = successor_name(time.time_ns() if deps.now_ns is None else deps.now_ns)
    brief = successor_brief(
        BriefContext(
            old_name=ctx.old_name,
            old_session_id=old_session_id,
            old_transcript=transcript_path(old_session_id, deps.projects_dir),
            handoff=handoff.resolve(),
            ship_queue=checkout / SHIP_QUEUE,
            inbox=checkout / HANDOFF_INBOX,
            state_dir=state_dir.resolve(),
            heavy_runs=runs,
            queued=queued_questions(handoff_text),
            unparsed_queued_heading=_unparsed_queued_heading(handoff_text),
        )
    )
    argv = launch_argv(name, brief)
    _write(deps, f"argv: {json.dumps(argv)}\ncwd: {checkout}\nbrief:\n{brief}")
    if dry_run:
        _write(deps, "DRY RUN: nothing recorded, nothing executed\n")
        return 0
    path = state_dir / f"{old_session_id}.json"
    state["census"] = [asdict(run) for run in runs]
    record = {
        "at": now_iso(),
        "successor": name,
        "handoff": str(handoff.resolve()),
        "cwd": str(checkout),
    }
    state["launch_pending"] = {"name": name, "at": record["at"]}
    write_state(path, state)
    return argv, record, runs


def _start_successor(
    ctx: LaunchContext,
    deps: LaunchDeps,
    argv: list[str],
    record: dict[str, str],
    runs: tuple[HeavyRun, ...],
) -> int:
    """Keep failed levels; preserve successful starts before trying promotion."""
    try:
        result = (deps.runner or subprocess.run)(
            argv,
            cwd=ctx.checkout,
            check=False,
            timeout=LAUNCH_TIMEOUT_S,
        )
        started = result.returncode == 0
        if not started:
            logger.error(
                "coordinator-handoff launch: start failed: claude --bg rc %d",
                result.returncode,
            )
    except OSError, subprocess.TimeoutExpired:
        logger.exception("coordinator-handoff launch: start failed")
        started = False
    path = ctx.state_dir / f"{ctx.old_session_id}.json"
    receipt = {
        **record,
        "name": record["successor"],
        "started": True,
        "census": [asdict(run) for run in runs],
    }
    if started:
        try:
            # Separate inode/lock: finalisation may time out on the main lock.
            receipt_path = _started_path(path)
            with state_lock(receipt_path, timeout_s=deps.lock_timeout_s):
                write_state(receipt_path, receipt)
        except OSError:
            logger.exception(
                "coordinator-handoff launch: cannot persist started receipt"
            )
    try:
        with state_lock(path, timeout_s=deps.lock_timeout_s):
            state = read_state(path)
            pending = state.get("launch_pending")
            if (
                not isinstance(pending, dict)
                or pending.get("name") != record["successor"]
                or pending.get("at") != record["at"]
            ):
                if started:
                    state["launch_pending"] = receipt
                    write_state(path, state)
                    logger.error(
                        "coordinator-handoff launch: successor STARTED but not recorded"
                        " — do not relaunch (pending claim changed)"
                    )
                    return 4
                logger.error(
                    "coordinator-handoff launch: start failed: pending claim changed"
                )
                return 3
            if started:
                # Persist confirmation before the separately fallible promotion.
                state["launch_pending"] = receipt
                write_state(path, state)
                state["launch"] = record
            del state["launch_pending"]
            write_state(path, state)
    except OSError:
        if started:
            logger.exception(
                "coordinator-handoff launch: successor STARTED but not recorded"
                " — do not relaunch (cannot finalise state)"
            )
            return 4
        logger.exception(
            "coordinator-handoff launch: start failed: cannot finalise state"
        )
        return 3
    return 0 if started else 3


# ── retire ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RetireRequest:
    """What the successor asks of :func:`retire`."""

    old_session_id: str
    adopted: frozenset[int] = frozenset()
    dry_run: bool = False
    accept_inflight: bool = False


@dataclass(frozen=True)
class RetireDeps:
    """Every collaborator of :func:`retire`, injectable for the tests."""

    jobs_dir: Path
    state_dir: Path
    processes: tuple[reap.Process, ...]
    runner: Runner | None = None


def _recorded_runs(state: Mapping[str, Any]) -> tuple[HeavyRun, ...] | None:
    raw = state.get("census")
    if not isinstance(raw, list):
        return None
    runs: list[HeavyRun] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        pid, argv, log = item.get("pid"), item.get("argv"), item.get("log_path")
        if isinstance(pid, bool) or not isinstance(pid, int):
            return None
        if not isinstance(argv, str) or not (log is None or isinstance(log, str)):
            return None
        runs.append(HeavyRun(pid, argv, log))
    return tuple(runs)


def in_flight_tasks(jobs_dir: Path, session_id: str) -> int | None:
    """The old job's ``inFlight.tasks``, or ``None`` when it cannot be read."""
    record = job_record(session_id, jobs_dir)
    in_flight = None if record is None else record.get("inFlight")
    tasks = in_flight.get("tasks") if isinstance(in_flight, dict) else None
    if isinstance(tasks, bool) or not isinstance(tasks, int) or tasks < 0:
        return None
    return tasks


def _in_flight_blocks(request: RetireRequest, in_flight: int | None) -> bool:
    """Whether harness tasks in flight block retire on their own (item 16)."""
    if in_flight == 0:
        return False
    if request.accept_inflight:
        logger.warning(
            "coordinator-handoff retire: --accept-inflight given; ignoring "
            "inFlight.tasks=%s",
            in_flight,
        )
        return False
    logger.error(
        "coordinator-handoff retire: BLOCK inFlight %s for %s "
        "(pass --accept-inflight only after confirming they may die)",
        "unknown" if in_flight is None else f"tasks={in_flight}",
        request.old_session_id,
    )
    return True


def retire(request: RetireRequest, deps: RetireDeps) -> int:
    """Stop the old coordinator unless it still owns live work.

    Two independent blockers (rc 1): a recorded run still alive with the SAME
    command line (so a reused pid never blocks) and not adopted, naming each
    pid/argv/log; and the old job's ``inFlight.tasks > 0`` unless
    ``accept_inflight``. Unknown inFlight also blocks unless accepted. rc 2:
    invalid role/id or missing/unreadable launch state. rc 3: stop failure or
    timeout. Otherwise claude stop succeeds (rc 0); dry-run never invokes it.
    """
    old = request.old_session_id
    name = session_name(old, deps.jobs_dir)
    if not is_coordinator(name):
        logger.error(
            "coordinator-handoff retire: %s is not a coordinator (name %r)", old, name
        )
        return 2
    try:
        state = _read_launch_state(deps.state_dir / f"{old}.json")
    except OSError:
        logger.exception("coordinator-handoff retire: unreadable state")
        return 2
    runs = _recorded_runs(state)
    launch_record = state.get("launch") or _started_pending(state)
    if (
        not isinstance(launch_record, dict)
        or not isinstance(
            launch_record.get("successor", launch_record.get("name")), str
        )
        or not launch_record.get("successor", launch_record.get("name"))
        or runs is None
    ):
        logger.error(
            "coordinator-handoff retire: no (valid) launch record for %s in %s",
            old,
            deps.state_dir,
        )
        return 2
    commands = {process.pid: process.command for process in deps.processes}
    blocking = tuple(
        run
        for run in runs
        if commands.get(run.pid) == run.argv and run.pid not in request.adopted
    )
    for run in blocking:
        logger.error(
            "coordinator-handoff retire: BLOCK live run pid %d (log %s): %s",
            run.pid,
            run.log_path or "none",
            run.argv,
        )
    in_flight = in_flight_tasks(deps.jobs_dir, old)
    inflight_blocks = _in_flight_blocks(request, in_flight)
    if inflight_blocks or blocking:
        remedies: list[str] = []
        if blocking:
            remedies.append("wait for each run or pass --adopted PID")
        if inflight_blocks:
            remedies.append(
                "confirm harness tasks may die, then pass --accept-inflight"
            )
        logger.error(
            "coordinator-handoff retire: refusing to stop %s — %s",
            old,
            "; ".join(remedies),
        )
        return 1
    short_id = old[:SHORT_ID_LEN]
    if request.dry_run:
        logger.info(
            "coordinator-handoff retire: DRY RUN — would run claude stop %s", short_id
        )
        return 0
    return _stop(short_id, deps.runner)


def _stop(short_id: str, runner: Runner | None) -> int:
    """Distinct operational failure code, separate from retirement blockers."""
    runner = runner or subprocess.run
    try:
        result = runner(
            ["claude", "stop", short_id], check=False, timeout=STOP_TIMEOUT_S
        )
    except OSError, subprocess.TimeoutExpired:
        logger.exception("coordinator-handoff retire: stop failed")
        return 3
    if result.returncode != 0:
        logger.error("coordinator-handoff retire: claude stop rc %d", result.returncode)
        return 3
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────────


def add_subcommands(parser: argparse.ArgumentParser) -> None:
    """``coordinator-handoff {decide,release,name,launch,retire,inbox}``."""
    sub = parser.add_subparsers(dest="handoff_command", required=True)
    decide_parser = sub.add_parser(
        "decide", help="JSON fire decision for one context measurement (rc 0)"
    )
    decide_parser.add_argument("--session-id", required=True)
    decide_parser.add_argument("--percent", type=float, required=True)
    modes = decide_parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--no-commit",
        action="store_true",
        help="Report without consuming a firing level",
    )
    modes.add_argument(
        "--probe",
        action="store_true",
        help="Fire at most once per session without spending real levels",
    )
    modes.add_argument(
        "--dry-run",
        action="store_true",
        help="Fire once per preview level without spending real levels",
    )
    release_parser = sub.add_parser(
        "release", help="Restore an undelivered firing level"
    )
    release_parser.add_argument("--session-id", required=True)
    release_modes = release_parser.add_mutually_exclusive_group(required=True)
    release_modes.add_argument("--level", type=float)
    release_modes.add_argument(
        "--probe", action="store_true", help="Release a pending probe"
    )
    release_parser.add_argument(
        "--delivered",
        action="store_true",
        help="Confirm a successfully delivered probe",
    )
    name_parser = sub.add_parser(
        "name",
        help="Print a fresh <project>-<Chicago ISO ns>.<feature> session name "
        "(default: a dotfiles coordinator's)",
    )
    name_parser.add_argument("--project", default=PROJECT, help="dotfiles | kb")
    name_parser.add_argument(
        "--feature", default=COORDINATOR_FEATURE, help="e.g. a lane name"
    )
    launch_parser = sub.add_parser(
        "launch", help="Record the census and start the named successor (claude --bg)"
    )
    launch_parser.add_argument("--handoff", type=Path, required=True)
    launch_parser.add_argument("--old-session", required=True)
    launch_parser.add_argument("--dry-run", action="store_true")
    retire_parser = sub.add_parser(
        "retire", help="Gate, then claude stop the old coordinator"
    )
    retire_parser.add_argument("--old-session", required=True)
    retire_parser.add_argument("--adopted", type=int, nargs="*", default=[])
    retire_parser.add_argument(
        "--accept-inflight",
        action="store_true",
        help="Stop even while the old session's harness tasks are in flight",
    )
    retire_parser.add_argument("--dry-run", action="store_true")
    handoff_inbox.add_subcommands(
        sub.add_parser(
            "inbox",
            help="Sanctioned main-checkout inbox/plan/queue writes "
            "(mise run handoff-inbox)",
        )
    )
    for child in (decide_parser, release_parser, launch_parser, retire_parser):
        child.add_argument(
            "--jobs-dir", type=Path, default=None, help="Override ~/.claude/jobs"
        )
        child.add_argument(
            "--state-dir",
            type=Path,
            default=None,
            help="Override <main checkout>/.agent/state/coordinator-handoff "
            "(tests or explicit handoff)",
        )


def main(args: argparse.Namespace, _project_root: Path) -> int:
    """Dispatch one parsed ``coordinator-handoff`` invocation."""
    command = args.handoff_command
    if command in {"name", "inbox"}:
        return _stateless_main(args)
    try:
        state_dir = (
            getattr(args, "state_dir", None) or main_checkout(Path.cwd()) / STATE_SUBDIR
        )
    except CoordinatorHandoffError:
        reason = "worktree-unavailable"
        logger.exception("coordinator-handoff %s: %s", command, reason)
        return 2
    jobs_dir = getattr(args, "jobs_dir", None) or default_jobs_dir()
    if command == "decide":
        decision = decide(
            DecideRequest(
                args.session_id,
                args.percent,
                no_commit=args.no_commit,
                probe=args.probe,
                dry_run=args.dry_run,
            ),
            env=os.environ,
            jobs_dir=jobs_dir,
            state_dir=state_dir,
        )
        sys.stdout.write(decision.to_json() + "\n")
        return 0
    if command == "release":
        return _release_main(args, state_dir)
    if command == "launch":
        return launch(
            args.handoff,
            args.old_session,
            dry_run=args.dry_run,
            deps=LaunchDeps(state_dir=state_dir, jobs_dir=jobs_dir),
        )
    return _retire_main(args, jobs_dir, state_dir)


def _stateless_main(args: argparse.Namespace) -> int:
    """The verbs that need no handoff state directory."""
    if args.handoff_command == "inbox":
        return handoff_inbox.main(args)
    name = stamped_name(args.project, args.feature, time.time_ns())
    sys.stdout.write(name + "\n")
    return 0


def _release_main(args: argparse.Namespace, state_dir: Path) -> int:
    """The CLI keeps successful-probe confirmation distinct from rollback."""
    if args.delivered and not args.probe:
        logger.error("coordinator-handoff release: --delivered requires --probe")
        return 2
    mode = ("probe-delivered" if args.delivered else "probe") if args.probe else "level"
    return release(args.session_id, args.level, state_dir=state_dir, mode=mode)


def _retire_main(args: argparse.Namespace, jobs_dir: Path, state_dir: Path) -> int:
    """Acquire the public CLI's process snapshot before entering the retire gate."""
    try:
        processes = reap.snapshot()
    except reap.ReapError:
        logger.exception("coordinator-handoff retire: cannot read the process table")
        return 2
    return retire(
        RetireRequest(
            old_session_id=args.old_session,
            adopted=frozenset(args.adopted),
            dry_run=args.dry_run,
            accept_inflight=args.accept_inflight,
        ),
        RetireDeps(jobs_dir=jobs_dir, state_dir=state_dir, processes=processes),
    )
