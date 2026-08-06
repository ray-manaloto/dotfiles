"""The launchd watchdog tick for this repo's background-agent DAG (#578).

A `dev.mise.dotfiles-dag-tick` LaunchAgent (declared in `mise.toml`'s
`[bootstrap.macos.launchd.agents]`, applied on this host only via `mise
bootstrap macos launchd-agents apply` — never implicitly, `.claude/rules/
do-not.md`) fires `mise run dag-tick` every 60s. Each tick takes a read-only
census of this repo's background Claude Code agents, classifies every node
ALIVE/DEAD/WEDGED/DONE, and recovers: `claude respawn` for a DEAD node,
`claude stop` for a DONE node whose process is still lingering.

**Slice 1 deliberately ships WITHOUT automated stall recovery.** WEDGED is
classify-and-log ONLY — a `tempo:"active"` node whose `state.json` has gone
stale past `--stall-after` gets a log line, never a `claude` verb against it.
Automated stall recovery is issue #590.

Mechanics, probe-verified this session (not guessed) and cited so a future
edit does not have to re-derive them:

- **Terminal predicate** (`docs/receipts/565.md`, live-armed 7/7): a node
  settles when its `state` is in :data:`TERMINAL_STATES` AND `tempo` is not
  `"active"` AND there is no pending `queuedPrompt`. `killed`/`blocked` are
  deliberately NOT terminal — the harness auto-respawns both.
- **Fleet-gate preflight**: `claude logs <fresh-bogus-id>` exits rc=1 on
  BOTH faces (gate on or off), so the state can only be read from stderr
  TEXT, never the exit code (:func:`gate_status`).
- **Census** (`claude agents --json --cwd <path> --all`) is a read-only,
  TTY-free, cwd-scoped array read straight off disk — it does NOT start or
  restart the supervisor (`docs/receipts/565.md` §4). A `kind:"background"`
  row carries `state` but never `pid`; only `kind:"interactive"` rows carry
  `pid`. This module only ever acts on `kind:"background"` rows: an
  interactive row is somebody's live foreground terminal session, which
  `claude respawn`/`claude stop` were never meant to touch.
- **Background pid liveness is NOT in the census, and often not in
  `state.json` either** — the harness's own docs say a background session
  can appear in the census "even when its process has exited"
  (`agent-view.md`, "List sessions as JSON"). The actual liveness record is
  `~/.claude/daemon/roster.json`'s per-worker `pid` (`docs/research/kb/
  reports/agents/wf-dag-recovery.md` §3): read via :func:`read_roster` +
  :func:`pid_is_alive`. A node with no roster entry at all is exactly the
  documented gap — the harness's own in-life watchdog (5s pid poll) only
  works while its supervisor process is itself alive, which is precisely
  the failure this tick exists to catch from the outside.
- **The respawn precondition is PID-liveness only, never `tempo`/in-flight**
  (:func:`execute_respawn`). The binary's own `/restart` refusal ("Can't
  restart while work is running in the background") guards a LIVE session
  from restarting itself out from under its own running background work —
  that guard does not apply here, because this tick only ever respawns a
  node whose process is confirmed dead on a FRESH roster read, and a dead
  process's background work died with it. Checking `tempo == "active"`
  here (an earlier version of this module did) instead deadlocks the
  watchdog's primary recovery case forever: a crash mid-activity leaves
  exactly a `tempo:"active"` state.json behind, and a dead process never
  updates that file, so the node would be skipped every 60s to infinity.
  The harness's own crash-respawn recovers exactly this case
  (`docs/receipts/565.md` arm B6: state done + tempo ACTIVE -> RESPAWNED) —
  this tick must too. Do not reintroduce the tempo/in-flight check.
"""

from __future__ import annotations

import enum
import fcntl
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse
    from collections.abc import Mapping, Sequence
    from typing import Literal, TextIO

logger = logging.getLogger(__name__)

# The binary's own terminal-state predicate (docs/receipts/565.md, live-armed
# 7/7): a node settles when `state` reaches one of these AND `tempo` is not
# "active" AND there is no pending `queuedPrompt`. `killed`/`blocked` are
# deliberately NOT terminal — the harness auto-respawns both.
TERMINAL_STATES: frozenset[str] = frozenset({"done", "failed", "stopped"})

# A tempo:"active" state.json this old with no update is WEDGED — classify
# and log only in this slice; automated stall recovery is #590.
DEFAULT_STALL_AFTER_SECONDS = 120.0

# `mise` is a zsh function on this host, not a binary launchd can exec, so
# the LaunchAgent invokes `~/.local/bin/mise` directly (mise.toml). This
# default mirrors the same "must be a real executable" constraint for a
# manual/CLI run: personal to this host, like the LaunchAgent's own PATH.
DEFAULT_CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")

# One tick at a time — a second tick that finds the lock held exits 0
# silently rather than racing a respawn/stop against the first.
LOCK_PATH = Path.home() / ".local" / "state" / "dotfiles" / "dag-tick.lock"

JOBS_DIR = Path.home() / ".claude" / "jobs"
DAEMON_DIR = Path.home() / ".claude" / "daemon"

# The harness's own `/restart` recipe, verbatim: every var a respawned node
# must NOT inherit from the incarnation that just died.
_RESPAWN_ENV_DENYLIST: frozenset[str] = frozenset(
    {
        "CLAUDE_CODE_SESSION_KIND",
        "CLAUDE_BG_SOURCE",
        "CLAUDE_BG_ISOLATION",
        "CLAUDE_BG_BACKEND",
        "CLAUDE_CODE_SESSION_NAME",
        "CLAUDE_CODE_RESUME_INTERRUPTED_TURN",
        "CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS",
        "CLAUDE_CODE_RESUME_PROMPT",
        "CLAUDE_CODE_RESUME_SOURCE_ALIVE",
        "CLAUDE_BG_POST_CLEAR_RESPAWN",
        "CLAUDE_BG_SESSION_PERMISSION_RULES",
        "CLAUDE_BG_MEMORY_TOGGLED_OFF",
    }
)
_RESPAWN_ENV_JOB_DIR = "CLAUDE_JOB_DIR"
_RESPAWN_ENV_BG_PREFIX = "CLAUDE_BG_"


class NodeClass(enum.Enum):
    """One background node's classification for this tick."""

    ALIVE = "alive"
    DEAD = "dead"
    WEDGED = "wedged"
    DONE = "done"


class ActionKind(enum.Enum):
    """What :func:`plan` decided to do about one classified node."""

    RESPAWN = "respawn"
    STOP = "stop"
    LOG = "log"


@dataclass(frozen=True)
class Node:
    """The `state.json` fields :func:`classify` needs, for one node."""

    node_id: str
    state: str | None
    tempo: str | None
    queued_prompt: bool


@dataclass(frozen=True)
class ClassifiedNode:
    """One node's classification plus the liveness fact that produced it."""

    node_id: str
    node_class: NodeClass
    pid_alive: bool


@dataclass(frozen=True)
class Action:
    """One planned action against one node id, with the reason it fired."""

    kind: ActionKind
    node_id: str
    reason: str


@dataclass(frozen=True)
class RosterWorker:
    """One background worker's liveness record from the daemon roster."""

    pid: int
    proc_start: str | None


@dataclass(frozen=True)
class ClassificationResult:
    """Classified nodes plus the report lines their classification produced."""

    classified: list[ClassifiedNode]
    notes: list[str]


def is_terminal(state: str | None, tempo: str | None, *, queued_prompt: bool) -> bool:
    """The binary's terminal-state predicate (`docs/receipts/565.md`).

    `state in TERMINAL_STATES` alone does not suppress a crash-respawn — the
    harness also requires `tempo != "active"` and no pending `queuedPrompt`.
    All three axes were live-armed 7/7: done/idle, failed/idle, stopped/idle
    are terminal; killed/idle and blocked/idle are not (wrong state);
    done/active is not (tempo blocks it); done/idle+queuedPrompt is not (a
    queued prompt blocks it too).
    """
    return state in TERMINAL_STATES and tempo != "active" and not queued_prompt


def classify(
    node: Node,
    *,
    pid_alive: bool,
    state_age_s: float | None,
    stall_after_s: float = DEFAULT_STALL_AFTER_SECONDS,
) -> NodeClass:
    """Classify one background node from its state.json fields + liveness.

    Order matters: a genuinely-finished node is DONE regardless of
    `pid_alive` (the harness settles it on disk before the process
    necessarily exits); a non-terminal node with no live process is DEAD; a
    non-terminal, live, ACTIVE node whose `state.json` has gone stale past
    `stall_after_s` is WEDGED (classify-and-log only in this slice —
    automated stall recovery is #590); everything else is ALIVE.
    """
    if is_terminal(node.state, node.tempo, queued_prompt=node.queued_prompt):
        return NodeClass.DONE
    if not pid_alive:
        return NodeClass.DEAD
    if (
        node.tempo == "active"
        and state_age_s is not None
        and state_age_s > stall_after_s
    ):
        return NodeClass.WEDGED
    return NodeClass.ALIVE


def strip_respawn_env(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """A copy of `env` with the harness's own `/restart` denylist removed.

    Mirrors the binary's own recipe verbatim (12 named vars + `CLAUDE_JOB_DIR`
    + every `CLAUDE_BG_*` prefix) so a respawned node starts as cleanly as the
    harness's own `/restart` would leave it — a stale
    `CLAUDE_CODE_RESUME_INTERRUPTED_TURN` or `CLAUDE_BG_ISOLATION` from the
    OLD incarnation must not leak into the new one.
    """
    source = os.environ if env is None else env
    return {
        name: value
        for name, value in source.items()
        if name not in _RESPAWN_ENV_DENYLIST
        and name != _RESPAWN_ENV_JOB_DIR
        and not name.startswith(_RESPAWN_ENV_BG_PREFIX)
    }


def plan(classified_nodes: Sequence[ClassifiedNode]) -> list[Action]:
    """Map classified nodes to actions. Pure — no subprocess calls here.

    DEAD -> respawn (subject to the fresh re-check in :func:`execute_respawn`);
    DONE with a still-live pid -> stop (a lingering process past settle);
    WEDGED -> a log-only action, since automated stall recovery is #590;
    ALIVE, or DONE with no live pid, -> no action.
    """
    actions: list[Action] = []
    for classified in classified_nodes:
        if classified.node_class is NodeClass.DEAD:
            actions.append(
                Action(
                    ActionKind.RESPAWN,
                    classified.node_id,
                    "not terminal and the process is not alive",
                )
            )
        elif classified.node_class is NodeClass.DONE and classified.pid_alive:
            actions.append(
                Action(
                    ActionKind.STOP,
                    classified.node_id,
                    "terminal state but the process is still running",
                )
            )
        elif classified.node_class is NodeClass.WEDGED:
            actions.append(
                Action(
                    ActionKind.LOG,
                    classified.node_id,
                    "tempo active and state.json stale past the stall "
                    "threshold — automated stall recovery is #590",
                )
            )
    return actions


def gate_status(stderr_text: str) -> Literal["on", "off", "unknown"]:
    """Classify the fleet-gate preflight's stderr (`docs/receipts/565.md`).

    Both faces of `claude logs <fresh-bogus-id>` exit rc=1, so the gate state
    can only be read from the stderr TEXT, never the exit code: a not-found
    message means the gate is on (agent-view verbs are live); an
    "is disabled by" message means `CLAUDE_CODE_DISABLE_AGENT_VIEW` or the
    `disableAgentView` setting turned the whole fleet surface off.
    """
    if "No job matching" in stderr_text:
        return "on"
    if "is disabled by" in stderr_text:
        return "off"
    return "unknown"


def read_roster(daemon_dir: Path) -> dict[str, RosterWorker] | None:
    """Parse `~/.claude/daemon/roster.json`. `None` on any read/parse failure.

    `None` (never an empty dict) distinguishes "the roster could not be
    read" from "the roster was read and is genuinely empty" — an unreadable
    roster must not be trusted for pid liveness (defensive: the caller treats
    it as ALIVE, per this module's "never respawn on a read failure" rule); a
    roster that WAS read and does not name a node is real negative evidence.
    """
    roster_path = daemon_dir / "roster.json"
    try:
        raw_text = roster_path.read_text()
    except OSError:
        return None
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    workers = raw.get("workers")
    if not isinstance(workers, dict):
        return None
    result: dict[str, RosterWorker] = {}
    for short_id, entry in workers.items():
        if not isinstance(entry, dict):
            continue
        pid = entry.get("pid")
        if isinstance(pid, int):
            result[short_id] = RosterWorker(pid=pid, proc_start=entry.get("procStart"))
    return result


def pid_is_alive(pid: int) -> bool:
    """Best-effort liveness check via `kill(pid, 0)` — no signal is sent."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def background_pid_alive(node_id: str, roster: dict[str, RosterWorker] | None) -> bool:
    """Is there a live process behind this background node?

    `roster` is `None` when the daemon roster could not be read — act
    conservatively and assume alive, so a read glitch can never trigger a
    respawn. A roster that WAS read and does not name this node is real
    negative evidence: a background census row with no roster entry is
    exactly the harness's documented gap — a session "still working or
    blocked even when its process has exited".
    """
    if roster is None:
        return True
    entry = roster.get(node_id)
    if entry is None:
        return False
    return pid_is_alive(entry.pid)


def load_state_json(
    jobs_dir: Path, node_id: str
) -> tuple[dict[str, object] | None, float | None]:
    """Read+parse one job's `state.json`; `(None, None)` if missing/bad.

    Returns the parsed object and the file's mtime (the WEDGED staleness
    proxy) together, since a caller that needs one needs the other.
    """
    state_path = jobs_dir / node_id / "state.json"
    try:
        mtime = state_path.stat().st_mtime
        raw_text = state_path.read_text()
    except OSError:
        return None, None
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(data, dict):
        return None, None
    return data, mtime


def try_acquire_lock(lock_path: Path) -> TextIO | None:
    """Best-effort single-writer lock via `flock(LOCK_EX|LOCK_NB)`.

    Returns an open handle that HOLDS the lock (close it to release), or
    `None` when another tick already holds it — the caller's job is then to
    exit 0 silently (overlap guard: two ticks must never race a respawn).
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # "a", not "w" — "w" truncates the file on open, which would zero out
    # the lockfile's bytes out from under another process that already
    # holds it open (flock is advisory and does not stop the truncate).
    handle = lock_path.open("a")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def gate_preflight(claude_bin: str) -> Literal["on", "off", "unknown"]:
    """Run the read-only fleet-gate preflight and classify its stderr.

    Mints a fresh bogus job id per call — a published id stops discriminating
    once it is a real (or once-real) job (`.claude/rules/
    probes-need-a-control-arm.md`).

    `claude_bin` not existing/executable (`FileNotFoundError`/`PermissionError`,
    both `OSError`) is treated the same as an ambiguous gate read: `run_tick`
    already logs and exits 0 on anything other than `"on"`, so `"unknown"`
    is the correct degrade — never let a missing binary raise out of the
    always-rc-0 tick.
    """
    bogus_id = uuid.uuid4().hex
    try:
        result = subprocess.run(
            [claude_bin, "logs", bogus_id],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        logger.warning(
            "dag-tick: claude binary %r unavailable for gate preflight: %s",
            claude_bin,
            exc,
        )
        return "unknown"
    return gate_status(result.stderr)


def read_census(claude_bin: str, cwd: str) -> list[dict[str, object]]:
    """`claude agents --json --cwd <cwd> --all`, defensively parsed.

    Read-only — it does not start or restart the supervisor (`docs/receipts/
    565.md` §4). Every failure mode (missing/unexecutable binary, nonzero
    rc, malformed JSON, a non-array top-level value) degrades to an empty
    census rather than raising: a tick that cannot read the fleet should do
    nothing this tick, not crash the launchd agent. Each failure path logs
    ONE distinct warning so "the fleet is genuinely empty" (silent) is never
    confused with "the census read failed" (logged) — before this, both
    returned `[]` identically and a failure at 3am left no trace.
    """
    try:
        result = subprocess.run(
            [claude_bin, "agents", "--json", "--cwd", cwd, "--all"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        logger.warning(
            "dag-tick: claude binary %r unavailable for census: %s", claude_bin, exc
        )
        return []
    if result.returncode != 0:
        logger.warning(
            "dag-tick: census read failed rc=%d stderr=%s",
            result.returncode,
            result.stderr[:200],
        )
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.warning("dag-tick: census stdout was not valid JSON: %s", exc)
        return []
    if not isinstance(data, list):
        logger.warning(
            "dag-tick: census top-level JSON was %s, not a list",
            type(data).__name__,
        )
        return []
    return [row for row in data if isinstance(row, dict)]


def classify_background_rows(
    rows: Sequence[dict[str, object]],
    *,
    jobs_dir: Path,
    daemon_dir: Path,
    stall_after_s: float,
    verbose: bool,
) -> ClassificationResult:
    """Enrich + classify every `kind:"background"` census row.

    Enrichment reads each node's `state.json` (state/tempo/queuedPrompt +
    mtime) and the shared daemon roster (pid liveness), then calls
    :func:`classify`. A missing/unparseable `state.json` classifies ALIVE
    directly (act conservatively) rather than feeding a guessed state into
    the pure predicate.
    """
    roster = read_roster(daemon_dir)
    now = time.time()
    classified: list[ClassifiedNode] = []
    notes: list[str] = []
    for row in rows:
        node_id = row.get("id")
        if not isinstance(node_id, str) or not node_id:
            notes.append("dag-tick: skipping a background row with no usable id")
            continue
        data, mtime = load_state_json(jobs_dir, node_id)
        if data is None:
            classified.append(ClassifiedNode(node_id, NodeClass.ALIVE, pid_alive=True))
            if verbose:
                notes.append(
                    f"dag-tick: {node_id} state.json missing/unparseable — "
                    "classifying ALIVE (conservative)"
                )
            continue
        state = data.get("state")
        tempo = data.get("tempo")
        node = Node(
            node_id=node_id,
            state=state if isinstance(state, str) else None,
            tempo=tempo if isinstance(tempo, str) else None,
            queued_prompt=bool(data.get("queuedPrompt")),
        )
        alive = background_pid_alive(node_id, roster)
        state_age_s = None if mtime is None else max(now - mtime, 0.0)
        node_class = classify(
            node, pid_alive=alive, state_age_s=state_age_s, stall_after_s=stall_after_s
        )
        classified.append(ClassifiedNode(node_id, node_class, pid_alive=alive))
        if node_class is NodeClass.WEDGED:
            notes.append(
                f"dag-tick: WEDGED {node_id} — tempo active, state.json "
                f"stale {state_age_s:.0f}s > {stall_after_s:.0f}s "
                "(log-only; automated stall recovery is #590)"
            )
        elif verbose:
            notes.append(
                f"dag-tick: {node_id} class={node_class.value} "
                f"state={node.state} tempo={node.tempo} pid_alive={alive}"
            )
    return ClassificationResult(classified=classified, notes=notes)


def execute_respawn(node_id: str, *, claude_bin: str, daemon_dir: Path) -> str:
    """Respawn one DEAD node, after a fresh PID-liveness re-check.

    Eventual-consistency doctrine: never wait for or read back the result —
    the next tick observes it. The skip condition guards against a race
    between classification (up to one tick, i.e. 60s, stale) and this call:
    if the roster now reports the pid alive, something else already revived
    the node and a second respawn would double-start it.

    Deliberately PID-liveness only — no `tempo`/in-flight check. The
    harness's own `/restart` refusal ("Can't restart while work is running
    in the background") guards a LIVE session from restarting itself out
    from under its own running background work; that guard does not apply
    here, because this function is only ever reached for a node whose
    process is confirmed dead on a FRESH roster read, and a dead process's
    background work died with it. Skipping on `tempo == "active"` here
    would instead create a permanent deadlock on the watchdog's primary
    recovery case: a crash mid-activity leaves exactly a `tempo:"active"`
    state.json behind, and a dead process never updates that file, so the
    node would be skipped every 60s forever. The harness's own
    crash-respawn recovers exactly this case (`docs/receipts/565.md` arm
    B6: state done + tempo ACTIVE -> RESPAWNED) — this function must too.
    """
    if background_pid_alive(node_id, read_roster(daemon_dir)):
        return f"dag-tick: SKIP respawn {node_id} — pid is alive now (reconciled)"
    try:
        subprocess.Popen(
            [claude_bin, "respawn", node_id],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=strip_respawn_env(),
            cwd=str(Path.home()),
            start_new_session=True,
        )
    except OSError as exc:
        return f"dag-tick: SKIP respawn {node_id} — claude binary unavailable: {exc}"
    return f"dag-tick: RESPAWN {node_id}"


def execute_stop(node_id: str, *, claude_bin: str, daemon_dir: Path) -> str:
    """Stop one DONE-but-still-alive node, after a fresh pid re-check.

    Mirrors `execute_respawn`'s fresh-re-check shape: classification can be
    up to one tick (60s) stale, so re-read the roster right before acting.
    If the pid has already gone since classification (settled on its own,
    or something else already reaped it), SKIP rather than issue a stop
    that would log a false FAILED line against a process that no longer
    exists.
    """
    if not background_pid_alive(node_id, read_roster(daemon_dir)):
        return f"dag-tick: SKIP stop {node_id} — settled since classification"
    try:
        result = subprocess.run(
            [claude_bin, "stop", node_id],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return f"dag-tick: SKIP stop {node_id} — claude binary unavailable: {exc}"
    if result.returncode == 0:
        return f"dag-tick: STOP {node_id} (rc=0)"
    return (
        f"dag-tick: STOP {node_id} FAILED rc={result.returncode} "
        f"stderr={result.stderr.strip()}"
    )


def _execute_or_preview(
    actions: Sequence[Action],
    *,
    claude_bin: str,
    daemon_dir: Path,
    dry_run: bool,
) -> list[str]:
    """Run each planned action, or (under `--dry-run`) describe it only.

    A `LOG` action already emitted its line from `classify_background_rows`'s
    WEDGED note, so there is nothing further to run for it here.
    """
    lines: list[str] = []
    for action in actions:
        if dry_run:
            lines.append(
                f"dag-tick: [dry-run] would {action.kind.value} "
                f"{action.node_id} — {action.reason}"
            )
        elif action.kind is ActionKind.RESPAWN:
            lines.append(
                execute_respawn(
                    action.node_id,
                    claude_bin=claude_bin,
                    daemon_dir=daemon_dir,
                )
            )
        elif action.kind is ActionKind.STOP:
            lines.append(
                execute_stop(
                    action.node_id, claude_bin=claude_bin, daemon_dir=daemon_dir
                )
            )
    return lines


def run_tick(args: argparse.Namespace) -> int:
    """The launchd tick: lock -> gate preflight -> census -> classify -> act -> report.

    Always returns 0 — a launchd `StartInterval` agent has nowhere useful to
    surface a nonzero exit beyond its own log, and every failure mode here
    (lock contention, gate off, a census read failure) degrades to "do
    nothing this tick" by design: the next tick, 60s later, reconciles.
    """
    claude_bin = args.claude_bin or shutil.which("claude") or DEFAULT_CLAUDE_BIN
    cwd = args.cwd or str(Path.cwd())

    lock_handle = try_acquire_lock(LOCK_PATH)
    if lock_handle is None:
        return 0
    try:
        gate = gate_preflight(claude_bin)
        if gate != "on":
            logger.warning(
                "dag-tick: fleet gate preflight is %r — skipping this tick", gate
            )
            return 0

        rows = read_census(claude_bin, cwd)
        bg_rows = [row for row in rows if row.get("kind") == "background"]
        result = classify_background_rows(
            bg_rows,
            jobs_dir=JOBS_DIR,
            daemon_dir=DAEMON_DIR,
            stall_after_s=args.stall_after,
            verbose=args.verbose,
        )
        action_lines = _execute_or_preview(
            plan(result.classified),
            claude_bin=claude_bin,
            daemon_dir=DAEMON_DIR,
            dry_run=args.dry_run,
        )
        for line in (*result.notes, *action_lines):
            sys.stdout.write(f"{line}\n")
        return 0
    finally:
        lock_handle.close()
