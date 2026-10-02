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

``stamped_name`` is the one timestamp formatter shared with the
``session-start`` mod (``session_start.py``): ``<project>-<Chicago ISO ns>.<x>``.

Spec: ``docs/specs/coordinator-auto-handoff-2026-10-02.md``.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from dotfiles_setup import reap
from dotfiles_setup.session_orphans import _session_root

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Mapping

    Runner = Callable[..., subprocess.CompletedProcess[str]]

logger = logging.getLogger(__name__)

COORDINATOR_NAME_RE = re.compile(r"^dotfiles-.+\.coordinator$")
CHICAGO = ZoneInfo("America/Chicago")
PROJECT = "dotfiles"
COORDINATOR_FEATURE = "coordinator"

ENV_LIMIT = "DOTFILES_COORDINATOR_HANDOFF_PCT"
ENV_STEP = "DOTFILES_COORDINATOR_HANDOFF_STEP_PCT"
DEFAULT_LIMIT_PCT = 30.0
DEFAULT_STEP_PCT = 5.0
_MAX_PCT = 100.0
#: Absorbs float noise in ``(percent - limit) / step`` so 35.0 at step 5 is k=1.
_LEVEL_EPSILON = 1e-9
_NS_PER_S = 1_000_000_000
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_MINUTE = 60
SHORT_ID_LEN = 8
#: A session id becomes a filename; anything but this shape is refused.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,}$")

STATE_SUBDIR = Path(".agent") / "state" / "coordinator-handoff"
SHIP_QUEUE = Path(".agent") / "plans" / "main-checkout-ship-queue.md"
HANDOFF_INBOX = Path(".agent") / "plans" / "handoff-inbox"
CROSS_SESSION_SETTINGS = '{"crossSessionInbound":"accept"}'

#: Long operations a coordinator may own when it hands off. The tasks first,
#: then their python entrypoints (`mise.toml` `run =` lines, and the
#: knowledge-base's `kb-setup ship|land`), so a run is recognised whichever
#: process of its chain the census sees. `(?![\w-])` keeps `ship-queue` out.
HEAVY_COMMAND_RE = re.compile(
    r"(?:^|[\s/'\";&|(])"
    r"(?:mise\s+run\s+(?:ship|land|sync|verify-local|bounded-wait|kb-ship|kb-land)"
    r"|dotfiles-setup\s+(?:pr\s+(?:ship|land)|docker\s+sync|bounded-wait)"
    r"|kb-setup\s+(?:ship|land))"
    r"(?![\w-])"
)
#: The first stdout redirect target in a command line (`> FILE`, `>> FILE`,
#: `1> FILE`), never an fd duplication such as `2>&1`.
_REDIRECT_RE = re.compile(r"(?:^|[\s;])1?>>?\s*(?!&)([^\s;&|<>]+)")
#: The handoff section the old coordinator queues every open question into
#: (ruling 12). A level-2 heading; the section ends at the next level-2 one.
_QUEUED_HEADING_RE = re.compile(
    r"^##\s+Queued questions\s*$", re.MULTILINE | re.IGNORECASE
)
_NEXT_H2_RE = re.compile(r"^##\s", re.MULTILINE)


class CoordinatorHandoffError(RuntimeError):
    """A precondition of launch or retire could not be established."""


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
    reason: str
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


def valid_session_id(session_id: str) -> bool:
    """Whether ``session_id`` is safe to use as a file name."""
    return bool(_SESSION_ID_RE.fullmatch(session_id))


def read_json(path: Path) -> object:
    """Parsed JSON at ``path``, or ``None`` when missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None


def _job_record(session_id: str, jobs_dir: Path) -> dict[str, Any] | None:
    """The bg job record, only when its ``sessionId`` is exactly ``session_id``."""
    if not valid_session_id(session_id):
        return None
    data = read_json(jobs_dir / session_id[:SHORT_ID_LEN] / "state.json")
    if not isinstance(data, dict) or data.get("sessionId") != session_id:
        return None
    return data


def session_name(session_id: str, jobs_dir: Path) -> str | None:
    """The bg job record's ``name``, only when its ``sessionId`` matches.

    The record (``~/.claude/jobs/<id[:8]>/state.json``) is undocumented harness
    state, so every doubt — missing, unreadable, not an object, mismatched id,
    non-string name — answers ``None``: "not a coordinator". Only top-level
    keys are read; nested records carry their own ``name``.
    """
    record = _job_record(session_id, jobs_dir)
    name = None if record is None else record.get("name")
    return name if isinstance(name, str) else None


def is_coordinator(name: str | None) -> bool:
    """Whether a job-record name is a dotfiles coordinator's."""
    return name is not None and COORDINATOR_NAME_RE.fullmatch(name) is not None


def next_level(last_fired: float | None, cfg: Config) -> float:
    """The limit when nothing fired yet, else one step above the last fire."""
    return cfg.limit_pct if last_fired is None else last_fired + cfg.step_pct


def fired_level(percent: float, cfg: Config) -> float:
    """The highest ``limit + k*step`` (k >= 0) that is <= ``percent``."""
    if percent < cfg.limit_pct:
        return cfg.limit_pct
    steps = math.floor((percent - cfg.limit_pct) / cfg.step_pct + _LEVEL_EPSILON)
    return cfg.limit_pct + steps * cfg.step_pct


def read_state(path: Path) -> dict[str, Any]:
    """The JSON object at ``path``, or an empty one."""
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def write_state(path: Path, state: Mapping[str, Any]) -> None:
    """Atomic replace, so a crash never leaves a half-written state file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", "utf-8")
    tmp.replace(path)


def now_iso() -> str:
    """Chicago wall time, seconds precision — for state-file stamps."""
    return datetime.now(CHICAGO).isoformat(timespec="seconds")


def _last_fired(state: Mapping[str, Any]) -> float | None:
    value = state.get("last_fired")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) else None


def _judge(
    state: dict[str, Any], percent: float, cfg: Config, name: str | None
) -> tuple[bool, str, float | None]:
    """``(fire, reason, level)``; a fire records ``last_fired`` into ``state``."""
    if not is_coordinator(name):
        return False, "not-coordinator", None
    last = _last_fired(state)
    threshold = next_level(last, cfg)
    if percent < threshold:
        return False, ("below-limit" if last is None else "below-next-step"), threshold
    # max(): a limit/step change between fires can place fired_level under the
    # threshold; never record a level that re-fires sooner.
    level = max(fired_level(percent, cfg), threshold)
    state["last_fired"] = level
    return True, "fire", level


def decide(
    session_id: str,
    percent: float,
    *,
    env: Mapping[str, str],
    jobs_dir: Path,
    state_dir: Path,
) -> Decision:
    """Fire once at the limit, then once per step above it — coordinators only.

    ``last_seen`` is written on every call so a reader can tell "never
    measured" from "measured, below". On a fire, ``last_fired`` is persisted
    BEFORE returning; when that write fails the answer is ``fire: False``.
    """
    cfg = load_config(env)
    warnings = list(cfg.warnings)
    fire = False
    level: float | None = None
    name: str | None = None
    if not valid_session_id(session_id):
        reason = "invalid-session-id"
    elif not math.isfinite(percent) or percent < 0:
        reason = "invalid-percent"
    else:
        path = state_dir / f"{session_id}.json"
        state = read_state(path)
        state["last_seen"] = {"at": now_iso(), "percent": percent}
        name = session_name(session_id, jobs_dir)
        fire, reason, level = _judge(state, percent, cfg, name)
        try:
            write_state(path, state)
        except OSError as exc:
            warnings.append(f"state write failed: {exc}")
            if fire:
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


# ── names ────────────────────────────────────────────────────────────────────


def _offset_suffix(offset_s: int) -> str:
    if offset_s == 0:
        return "Z"
    sign = "+" if offset_s > 0 else "-"
    hours, rest = divmod(abs(offset_s), _SECONDS_PER_HOUR)
    minutes = rest // _SECONDS_PER_MINUTE
    return f"{sign}{hours:02d}{minutes:02d}" if minutes else f"{sign}{hours:02d}"


def chicago_stamp(now_ns: int) -> str:
    """``yyyyMMdd'T'HHmmss.<9-digit ns><X>`` in America/Chicago.

    ``X`` is ``±HH``, ``±HHMM`` when the minutes are non-zero, or ``Z`` at a
    zero offset.
    """
    seconds, nanos = divmod(now_ns, _NS_PER_S)
    moment = datetime.fromtimestamp(seconds, tz=CHICAGO)
    offset = moment.utcoffset()
    offset_s = 0 if offset is None else int(offset.total_seconds())
    return f"{moment:%Y%m%dT%H%M%S}.{nanos:09d}{_offset_suffix(offset_s)}"


def stamped_name(project: str, feature: str, now_ns: int) -> str:
    """``<project>-<chicago_stamp>.<feature>`` — the one session-name formatter.

    Shared by the coordinator successor and the ``session-start`` mod, so the
    two can never drift apart. NOTE: a legacy name like
    ``dotfiles-20261002b.coordinator`` sorts AFTER ``dotfiles-20261002T…``
    (``b`` > ``T``), so "newest coordinator" is never a name sort.
    """
    return f"{project}-{chicago_stamp(now_ns)}.{feature}"


def successor_name(now_ns: int) -> str:
    """``dotfiles-yyyyMMdd'T'HHmmss.<9-digit ns><X>.coordinator`` in Chicago."""
    return stamped_name(PROJECT, COORDINATOR_FEATURE, now_ns)


# ── repository + transcript lookups ──────────────────────────────────────────


def main_checkout(cwd: Path) -> Path:
    """The main working tree: the first entry of ``git worktree list``."""
    result = subprocess.run(
        ["git", "-C", str(cwd), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        msg = f"git worktree list exited {result.returncode}: {result.stderr.strip()}"
        raise CoordinatorHandoffError(msg)
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            return Path(line.removeprefix("worktree "))
    msg = "git worktree list printed no worktree entry"
    raise CoordinatorHandoffError(msg)


def transcript_path(session_id: str, projects_dir: Path) -> Path | None:
    """``<projects_dir>/<project slug>/<session_id>.jsonl``, if one exists."""
    if not valid_session_id(session_id):
        return None
    matches = sorted(projects_dir.glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def queued_questions(handoff_text: str) -> str | None:
    """The body of the handoff's ``## Queued questions`` section, if non-empty."""
    heading = _QUEUED_HEADING_RE.search(handoff_text)
    if heading is None:
        return None
    rest = handoff_text[heading.end() :]
    following = _NEXT_H2_RE.search(rest)
    body = (rest if following is None else rest[: following.start()]).strip()
    return body or None


# ── census ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HeavyRun:
    """One live long operation the old coordinator owned at launch."""

    pid: int
    argv: str
    log_path: str | None


def _log_path(command: str) -> str | None:
    match = _REDIRECT_RE.search(command)
    if match is None:
        return None
    return match.group(1).strip("'\"") or None


def census(
    processes: tuple[reap.Process, ...],
    *,
    self_pid: int,
    root_pid: int | None = None,
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
        runs.append(HeavyRun(pid, command, _log_path(command)))
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
    heavy_runs: tuple[HeavyRun, ...] = ()
    queued: str | None = None


def successor_brief(ctx: BriefContext) -> str:
    """The successor's first prompt: rules, review, notify, settle, retire."""
    short_id = ctx.old_session_id[:SHORT_ID_LEN]
    transcript = str(ctx.old_transcript) if ctx.old_transcript else "NOT FOUND (say so)"
    if ctx.heavy_runs:
        run_lines = "\n".join(
            f"  - pid {run.pid}: {run.argv}  (log: {run.log_path or 'none'})"
            for run in ctx.heavy_runs
        )
    else:
        run_lines = "  - none recorded"
    queued = ctx.queued or (
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
log's rc line) or adopt its result explicitly.
4. Retire the old session ONLY through the gate — never a bare `claude stop` \
on a coordinator: `mise run coordinator-handoff -- retire --old-session \
{ctx.old_session_id} [--adopted PID ...]`. It refuses (rc 1) while a recorded \
run is live and unadopted, or while the old session's harness tasks are in \
flight (`--accept-inflight` overrides that deliberately); rc 0 runs \
`claude stop {short_id}`.
5. Put the queued questions to Ray.
6. Resume the ship queue.
"""


def launch_argv(name: str, brief: str) -> list[str]:
    """``claude --bg -n NAME`` with cross-session inbound accepted; no ``-p``."""
    return ["claude", "--bg", "-n", name, "--settings", CROSS_SESSION_SETTINGS, brief]


# ── launch ───────────────────────────────────────────────────────────────────


def default_jobs_dir() -> Path:
    """The harness bg job records."""
    return Path.home() / ".claude" / "jobs"


def default_projects_dir() -> Path:
    """The harness transcripts root."""
    return Path.home() / ".claude" / "projects"


@dataclass(frozen=True)
class LaunchDeps:
    """Every collaborator of :func:`launch`, injectable for the tests."""

    state_dir: Path
    jobs_dir: Path = field(default_factory=default_jobs_dir)
    projects_dir: Path = field(default_factory=default_projects_dir)
    cwd: Path | None = None
    processes: tuple[reap.Process, ...] | None = None
    self_pid: int | None = None
    root_pid: int | None = None
    now_ns: int | None = None
    runner: Runner | None = None
    out: Callable[[str], object] | None = None


def _write(deps: LaunchDeps, text: str) -> None:
    (deps.out or sys.stdout.write)(text)


def _gather(
    handoff: Path, deps: LaunchDeps
) -> tuple[Path, tuple[HeavyRun, ...], str] | str:
    """``(main checkout, census, handoff text)``, or why one is unavailable."""
    try:
        checkout = main_checkout(Path.cwd() if deps.cwd is None else deps.cwd)
        table = reap.snapshot() if deps.processes is None else deps.processes
        runs = census(
            table,
            self_pid=os.getpid() if deps.self_pid is None else deps.self_pid,
            root_pid=deps.root_pid,
        )
        handoff_text = handoff.read_text(encoding="utf-8")
    except (CoordinatorHandoffError, reap.ReapError, OSError) as exc:
        return str(exc)
    return checkout, runs, handoff_text


def launch(
    handoff: Path,
    old_session_id: str,
    *,
    dry_run: bool,
    deps: LaunchDeps,
) -> int:
    """Record the census, then start the successor from the main checkout.

    rc 2: the handoff does not exist, the old session is not a coordinator, or
    the census could not be taken (retire would be blind). Dry-run prints the
    argv, cwd and brief and records and executes nothing. Otherwise the
    ``claude --bg`` rc.
    """
    if not handoff.is_file():
        logger.error("coordinator-handoff launch: handoff %s does not exist", handoff)
        return 2
    old_name = session_name(old_session_id, deps.jobs_dir)
    if old_name is None or not is_coordinator(old_name):
        logger.error(
            "coordinator-handoff launch: session %s is not a coordinator (name %r)",
            old_session_id,
            old_name,
        )
        return 2
    gathered = _gather(handoff, deps)
    if isinstance(gathered, str):
        logger.error("coordinator-handoff launch refused: %s", gathered)
        return 2
    checkout, runs, handoff_text = gathered
    name = successor_name(time.time_ns() if deps.now_ns is None else deps.now_ns)
    brief = successor_brief(
        BriefContext(
            old_name=old_name,
            old_session_id=old_session_id,
            old_transcript=transcript_path(old_session_id, deps.projects_dir),
            handoff=handoff.resolve(),
            ship_queue=checkout / SHIP_QUEUE,
            inbox=checkout / HANDOFF_INBOX,
            heavy_runs=runs,
            queued=queued_questions(handoff_text),
        )
    )
    argv = launch_argv(name, brief)
    _write(deps, f"argv: {json.dumps(argv)}\ncwd: {checkout}\nbrief:\n{brief}")
    if dry_run:
        _write(deps, "DRY RUN: nothing recorded, nothing executed\n")
        return 0
    path = deps.state_dir / f"{old_session_id}.json"
    state = read_state(path)
    state["census"] = [asdict(run) for run in runs]
    state["launch"] = {
        "at": now_iso(),
        "successor": name,
        "handoff": str(handoff.resolve()),
        "cwd": str(checkout),
    }
    write_state(path, state)  # state before signal
    runner = deps.runner or subprocess.run
    return runner(argv, cwd=checkout, check=False).returncode


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
    record = _job_record(session_id, jobs_dir)
    in_flight = None if record is None else record.get("inFlight")
    tasks = in_flight.get("tasks") if isinstance(in_flight, dict) else None
    if isinstance(tasks, bool) or not isinstance(tasks, int):
        return None
    return tasks


def _in_flight_blocks(request: RetireRequest, in_flight: int | None) -> bool:
    """Whether harness tasks in flight block retire on their own (item 16)."""
    if in_flight is None:
        logger.warning(
            "coordinator-handoff retire: inFlight.tasks UNKNOWN for %s; "
            "the census decides",
            request.old_session_id,
        )
        return False
    logger.info("coordinator-handoff retire: inFlight.tasks=%d", in_flight)
    if in_flight <= 0:
        return False
    if request.accept_inflight:
        logger.warning(
            "coordinator-handoff retire: --accept-inflight given; ignoring "
            "inFlight.tasks=%d",
            in_flight,
        )
        return False
    logger.error(
        "coordinator-handoff retire: BLOCK inFlight.tasks=%d for %s "
        "(pass --accept-inflight only after confirming they may die)",
        in_flight,
        request.old_session_id,
    )
    return True


def retire(request: RetireRequest, deps: RetireDeps) -> int:
    """Stop the old coordinator unless it still owns live work.

    Two independent blockers (rc 1): a recorded run still alive with the SAME
    command line (so a reused pid never blocks) and not adopted, naming each
    pid/argv/log; and the old job's ``inFlight.tasks > 0`` unless
    ``accept_inflight``. An unreadable ``inFlight`` is UNKNOWN — reported, and
    the census alone decides. rc 2 when the old session is not a coordinator
    or has no launch record. Otherwise runs ``claude stop <old short id>``
    (skipped under ``dry_run``) and returns its rc.
    """
    old = request.old_session_id
    name = session_name(old, deps.jobs_dir)
    if not is_coordinator(name):
        logger.error(
            "coordinator-handoff retire: %s is not a coordinator (name %r)", old, name
        )
        return 2
    state = read_state(deps.state_dir / f"{old}.json")
    runs = _recorded_runs(state)
    if not isinstance(state.get("launch"), dict) or runs is None:
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
    if _in_flight_blocks(request, in_flight) or blocking:
        logger.error(
            "coordinator-handoff retire: refusing to stop %s — wait for each run "
            "or pass --adopted PID",
            old,
        )
        return 1
    short_id = old[:SHORT_ID_LEN]
    if request.dry_run:
        logger.info(
            "coordinator-handoff retire: DRY RUN — would run claude stop %s", short_id
        )
        return 0
    runner = deps.runner or subprocess.run
    return runner(["claude", "stop", short_id], check=False).returncode


# ── CLI ──────────────────────────────────────────────────────────────────────


def add_subcommands(parser: argparse.ArgumentParser) -> None:
    """``coordinator-handoff {decide,name,launch,retire}``."""
    sub = parser.add_subparsers(dest="handoff_command", required=True)
    decide_parser = sub.add_parser(
        "decide", help="JSON fire decision for one context measurement (rc 0)"
    )
    decide_parser.add_argument("--session-id", required=True)
    decide_parser.add_argument("--percent", type=float, required=True)
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
    for child in (decide_parser, launch_parser, retire_parser):
        child.add_argument(
            "--jobs-dir", type=Path, default=None, help="Override ~/.claude/jobs"
        )
        child.add_argument(
            "--state-dir",
            type=Path,
            default=None,
            help="Override <project>/.agent/state/coordinator-handoff",
        )


def main(args: argparse.Namespace, project_root: Path) -> int:
    """Dispatch one parsed ``coordinator-handoff`` invocation."""
    state_dir = getattr(args, "state_dir", None) or project_root / STATE_SUBDIR
    jobs_dir = getattr(args, "jobs_dir", None) or default_jobs_dir()
    command = args.handoff_command
    if command == "decide":
        decision = decide(
            args.session_id,
            args.percent,
            env=os.environ,
            jobs_dir=jobs_dir,
            state_dir=state_dir,
        )
        sys.stdout.write(decision.to_json() + "\n")
        return 0
    if command == "name":
        name = stamped_name(args.project, args.feature, time.time_ns())
        sys.stdout.write(name + "\n")
        return 0
    if command == "launch":
        return launch(
            args.handoff,
            args.old_session,
            dry_run=args.dry_run,
            deps=LaunchDeps(state_dir=state_dir, jobs_dir=jobs_dir),
        )
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
