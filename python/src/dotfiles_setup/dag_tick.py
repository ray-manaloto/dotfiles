"""The launchd watchdog tick for this repo's background-agent DAG (#578).

A `dev.mise.dotfiles-dag-tick` LaunchAgent (declared in `mise.toml`'s
`[bootstrap.macos.launchd.agents]`, applied on this host only via `mise
bootstrap macos launchd-agents apply` — never implicitly, `.claude/rules/
do-not.md`) fires `mise run dag-tick` every 60s. Each tick takes a read-only
census of this repo's background Claude Code agents, classifies every node
ALIVE/DEAD/WEDGED/DONE/NEEDS_HUMAN, and recovers: `claude respawn` for a
DEAD node, `claude stop` for a DONE node whose process is still lingering.
A NEEDS_HUMAN node is never touched — see the escalation bullet below.

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
- **An ESCALATED node is not a dead one** (#601, decided as `docs/
  receipts/575.md` R3). `blocked` staying out of :data:`TERMINAL_STATES`
  is right for a *plain* block, but wrong for the one shape that means "a
  human was asked a question": `state == "blocked"` AND a non-empty
  `needs` payload (:func:`is_needs_human`). Such a node classifies
  :attr:`NodeClass.NEEDS_HUMAN` — log only, **never respawn** — because
  #565 measured that `claude respawn` returns a node **IDLE with no
  prompt**, so respawning an escalation produces a zombie that never
  re-asks and silently discards the `needs`/`suggestedReply` payload
  #575's R1 makes load-bearing for the tracker projection. Live shape on
  this host, read from the two stale census nodes: `needs` is a **string**
  (`"run `/clear` to proceed to next task"`, `"do /clear with resume, or
  run full command-catalog extraction first?"`), alongside `tempo:
  "blocked"` and an optional `suggestedReply`. Plain `blocked` with no
  `needs` is unchanged. Emitting the tracker comment and the
  `dag:needs-human` label is the SCHEDULER's job, not this tick's — 575's
  R1 keeps projection one-directional and scheduler-owned, and the receipt
  defers the label spellings and comment format — so this module names
  :data:`NEEDS_HUMAN_LABEL` in its log line and stops there.
- **Fleet-gate preflight fails OPEN on an ambiguous read, fails CLOSED only
  on the documented "off" face.** `claude logs <fresh-bogus-id>` exits rc=1
  on BOTH the "on" and "off" faces, so the state can only be read from
  stderr TEXT, never the exit code (:func:`gate_status`). Only `"off"` (the
  "is disabled by ..." wording) skips the tick — `"unknown"` (a missing
  binary, or stderr wording that matches neither known face) logs a
  warning and PROCEEDS: :func:`read_census` is itself gated the same way
  and now logs its own failures loudly, so it is the real gate. Failing
  closed on an unrecognized stderr wording would silently retire the whole
  watchdog the day the harness rewords one error message.
- **Census** (`claude agents --json --cwd <path> --all`) is a read-only,
  TTY-free, cwd-scoped array read straight off disk — it does NOT start or
  restart the supervisor (`docs/receipts/565.md` §4). This module only ever
  acts on `kind:"background"` rows: an interactive row is somebody's live
  foreground terminal session, which `claude respawn`/`claude stop` were
  never meant to touch.

  ⚠️ **A `kind:"background"` row DOES carry a `pid` on 2.1.224 — and it is
  the WRONG process to check.** This docstring said "never `pid`" until
  #593 sampled a live node: the census reported `pid: 30723`
  (`claude bg-spare`) while the roster held `pid: 30714`
  (`claude bg-pty-host`), its parent. Do not "simplify" the roster read
  away now that a pid is visible in the census — the roster's pid is the
  one the harness itself pairs with `procStart`, and the census's is a
  different process.
- **Background pid liveness is NOT in the census, and often not in
  `state.json` either** — the harness's own docs say a background session
  can appear in the census "even when its process has exited"
  (`agent-view.md`, "List sessions as JSON"). The actual liveness record is
  `~/.claude/daemon/roster.json`'s per-worker `pid` **and the `procStart`
  beside it** (`docs/research/kb/reports/agents/wf-dag-recovery.md` §3):
  read via :func:`read_roster`, then :func:`pid_is_alive` +
  :func:`read_proc_start`. A node with no roster entry at all is exactly
  the documented gap — the harness's own in-life watchdog (5s pid poll)
  only works while its supervisor process is itself alive, which is
  precisely the failure this tick exists to catch from the outside.
- **A pid is a slot, not an identity (#593).** POSIX recycles pids, so
  `kill(pid, 0)` alone lets a crashed node read ALIVE forever and
  suppresses its respawn indefinitely. :func:`background_pid_alive`
  therefore requires liveness AND a matching `procStart`, mirroring the
  harness's own roster GC predicate — but it only ever adds a NEGATIVE on
  a positively-read, differing value; an absent record or an unanswered
  `ps` both read ALIVE. That asymmetry is deliberate: the DEAD branch
  respawns, so a false-DEAD double-starts a node while a false-ALIVE costs
  one 60s cycle. Encoding, tolerance and both arms: `docs/receipts/593.md`.
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
- **`--max-age` bounds automatic respawn** (:data:`DEFAULT_MAX_AGE_SECONDS`,
  default 86400s = 24h). A DEAD node only gets a RESPAWN when its
  `state.json` is fresher than `--max-age`; a node whose age exceeds it, OR
  whose age could not be determined at all (missing/unparseable
  `state.json`), gets a LOG action instead (:func:`plan`). Unknown age is
  treated as over-age deliberately: never resurrect something whose
  freshness cannot be proven. ⚠️ **It is a BACKSTOP, not the escalation
  safety mechanism** (#601): those two live sessions blocked/dead since
  July 13 and July 22 are both `blocked ∧ needs≠∅`, so what keeps them
  from being resurrected is now :attr:`NodeClass.NEEDS_HUMAN`, which holds
  at any age. Before #601 the 24h bound was the only thing standing
  between an escalated node and a respawn into an idle zombie — a sanity
  bound doing safety work by accident, one widened `--max-age` away from
  the harm.
- **The harness's own `/restart` recipe is "flush, strip, respawn"**
  (`docs/research/kb/reports/agents/wf-dag-recovery.md` §12); this
  module's copy of that recipe starts at strip, on purpose. §12's flush is
  a LIVE session flushing its own in-memory state to disk before it
  restarts itself — a confirmed-dead process has nothing left to flush,
  because its transcript already holds whatever reached disk before it
  died. The env strip (:func:`strip_respawn_env`) is the only step of that
  recipe that still applies to a node this tick respawns from the outside.
- **Every stateful helper takes an explicit** :class:`TickContext` **,
  never a module global.** `LOCK_PATH`/`JOBS_DIR`/`DAEMON_DIR` are
  :func:`build_tick_context`'s OWN defaults, not something any helper
  reaches for on its own — a test constructs a `TickContext` against
  `tmp_path` and calls :func:`execute_tick` directly instead of
  monkeypatching this module's globals. Pid liveness AND process identity
  are injected the same way (`background_pid_alive`'s `is_alive` and
  `proc_start` parameters, mirroring `gcc_sha.compute_sha`'s injected
  fetcher), so a test never monkeypatches this module's own
  :func:`pid_is_alive` or :func:`read_proc_start` either
  (`tests/AGENTS.md` § Mocking: never mock our own modules — inject).
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

from dotfiles_setup import codex_verdict

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Mapping, Sequence
    from typing import Literal, TextIO

logger = logging.getLogger(__name__)

# The binary's own terminal-state predicate (docs/receipts/565.md, live-armed
# 7/7): a node settles when `state` reaches one of these AND `tempo` is not
# "active" AND there is no pending `queuedPrompt`. `killed`/`blocked` are
# deliberately NOT terminal — the harness auto-respawns both.
TERMINAL_STATES: frozenset[str] = frozenset({"done", "failed", "stopped"})

# The harness's own escalation state (#601 / `docs/receipts/575.md` R3). It
# is deliberately NOT in TERMINAL_STATES — a plain `blocked` node is still a
# respawn candidate. It only means "a human was asked something" when a
# non-empty `needs` payload sits beside it (:func:`is_needs_human`).
ESCALATED_STATE = "blocked"

# The tracker label an escalated node projects to. Named here so the log
# line and any future projection cannot drift apart, but NOT applied by this
# module: `docs/receipts/575.md` R1 keeps projection one-directional and
# scheduler-owned, and a tick that labelled directly would put a second
# writer on the tracker.
#
# ⚠️ **Nothing in THIS process emits it, and that is still true** — but the
# projection now EXISTS. `dotfiles_setup.dag_project` (#602, landed 2026-08-07)
# writes the label and the append-only comment from its own LaunchAgent, on its
# own 300s schedule, as the scheduler's first slice. So the honest statement is
# no longer "an escalated node is visible in this tick's log ONLY" — it reaches
# the tracker, just not from here.
#
# **Do NOT read that as licence to emit it from this module.** The one-directional
# boundary is the whole point: the tick CLASSIFIES, the scheduler PROJECTS, and a
# tick that labelled directly would be the second writer `575.md` R1 forbids.
# `dag_project` imports this module's predicates rather than the reverse.
#
# Read the status in three parts, because two rounds of #601 review got it
# wrong in opposite directions:
#   - **Ownership is SETTLED, not deferred** — `575.md` R1 assigns projection
#     to the SCHEDULER, one direction only. That is why this tick must not
#     emit the label itself: it would be a second writer on the tracker.
#   - **This label's spelling is SETTLED** — `575.md`: *"#573's receipt
#     `dag:needs-human` — the receipt is later and governs"*.
#   - **The implementation is SHIPPED** (#602 phases 1-4: the standing
#     escalation issue #623, the comment format, the write path with
#     `(node, digest)` dedupe, and the LaunchAgent). What remains is phase 5,
#     the dispatch-time `dag-binding.json`, which is blocked on a dispatcher
#     existing — an UNBOUND node projects to #623 in the meantime.
NEEDS_HUMAN_LABEL = "dag:needs-human"

# A tempo:"active" state.json this old with no update is WEDGED — classify
# and log only in this slice; automated stall recovery is #590.
DEFAULT_STALL_AFTER_SECONDS = 120.0

# A DEAD node whose state.json is older than this is not "just crashed" — it
# is classify-and-log only, never auto-respawn. Measured live: the fleet's
# first real tick would otherwise have resurrected sessions blocked/dead
# since July 13 and July 22 (#578 respec round 3). An UNKNOWN age
# (state.json missing/unparseable) is ALSO over-age — never resurrect
# something whose freshness cannot be proven.
DEFAULT_MAX_AGE_SECONDS = 86400.0

# #573's rework budget: how many revise/reject rounds one unit of work may
# take before the node escalates instead of reopening again (#575 R7).
DEFAULT_MAX_REWORK = 2

# `mise` is a zsh function on this host, not a binary launchd can exec, so
# the LaunchAgent invokes `~/.local/bin/mise` directly (mise.toml). This
# default mirrors the same "must be a real executable" constraint for a
# manual/CLI run: personal to this host, like the LaunchAgent's own PATH.
DEFAULT_CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")

# One tick at a time — a second tick that finds the lock held exits 0
# silently rather than racing a respawn/stop against the first.
LOCK_PATH = Path.home() / ".local" / "state" / "dotfiles" / "dag-tick.lock"

JOBS_DIR = Path.home() / ".claude" / "jobs"
# One node's Codex review lane lives under its OWN job dir (#580) rather
# than a parallel tree: the tick already knows `jobs_dir`, and colocating
# means a `claude rm` of the node takes its lane with it instead of
# orphaning a run dir the reaper would keep finding forever.
CODEX_LANE_DIRNAME = "codex-lane"
DAEMON_DIR = Path.home() / ".claude" / "daemon"

# `ps -o lstart=` bound for the roster identity check (:func:`read_proc_start`)
# — the same 1s the CLI bundle gives its own `getProcessStartTime`. On expiry
# the read is UNANSWERED, which reads ALIVE, so a slow `ps` costs one recovery
# cycle and can never manufacture a respawn.
PROC_START_TIMEOUT_S = 1.0

# The harness's own `/restart` recipe is "flush, strip, respawn" (see the
# module docstring for why flush is intentionally absent here) — this is
# just the strip half, verbatim: every var a respawned node must NOT
# inherit from the incarnation that just died.
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
    NEEDS_HUMAN = "needs_human"
    REPLY_QUEUED = "reply_queued"


class ActionKind(enum.Enum):
    """What :func:`plan` decided to do about one classified node."""

    RESPAWN = "respawn"
    STOP = "stop"
    LOG = "log"


@dataclass(frozen=True)
class Node:
    """The `state.json` fields :func:`classify` needs, for one node.

    `needs` is the escalation payload — the question a `state=blocked`
    node is waiting on a human to answer — normalized by
    :func:`normalize_needs` to stripped text, or `None` when absent. It
    defaults to `None` so a plain `blocked` node reads exactly as it did
    before #601.
    """

    node_id: str
    state: str | None
    tempo: str | None
    queued_prompt: bool
    needs: str | None = None


@dataclass(frozen=True)
class ClassifiedNode:
    """One node's classification, liveness fact, and state.json age.

    `state_age_s` is `None` when the state.json age could not be determined
    (missing/unparseable file) — :func:`plan` treats that the same as an
    over-age DEAD node: an unknown age must never auto-respawn.
    """

    node_id: str
    node_class: NodeClass
    pid_alive: bool
    state_age_s: float | None


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


@dataclass(frozen=True)
class TickContext:
    """Everything one tick needs, threaded explicitly through every helper.

    Built once by :func:`build_tick_context` from CLI args plus this
    module's own path/lock defaults (#578 respec round 3 — the injection
    seam that replaces a scattered claude_bin/cwd/jobs_dir/daemon_dir/
    stall_after_s/dry_run parameter list on every helper, and replaces
    tests monkeypatching `LOCK_PATH`/`JOBS_DIR`/`DAEMON_DIR` with
    constructing one of these against `tmp_path` instead
    (`tests/AGENTS.md` § Mocking — never mock our own modules; inject).
    """

    claude_bin: str
    cwd: str
    jobs_dir: Path
    daemon_dir: Path
    lock_path: Path
    stall_after_s: float
    max_age_s: float
    max_rework: int
    dry_run: bool
    verbose: bool


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


def normalize_needs(value: object) -> str | None:
    """`state.json`'s raw `needs` as escalation text, or `None` when absent.

    On this host the harness writes a plain string — read live off the two
    stale census nodes: *"run `/clear` to proceed to next task"* and *"do
    /clear with resume, or run full command-catalog extraction first?"*. A
    whitespace-only string is NOT an escalation (nobody was asked
    anything), hence the strip.

    A non-string truthy value — a shape a future harness version might
    write — is coerced to text rather than dropped, deliberately: the
    failure this normalisation feeds is :func:`is_needs_human` returning
    False and the node being respawned into an idle zombie, so an
    unrecognised payload must fail toward "this IS an escalation".

    That branch deliberately does NOT strip, and the asymmetry with the
    string branch above is the point: an object whose `__str__` returns
    whitespace would strip to `""`, and `"" or None` would hand back
    absence — flipping a known-truthy payload to the one answer that gets
    the node respawned. The string branch can strip safely because there
    the empty result really does mean nobody was asked anything.
    """
    if isinstance(value, str):
        return value.strip() or None
    if value:
        return str(value)
    return None


def is_stalled(
    tempo: str | None, state_age_s: float | None, stall_after_s: float
) -> bool:
    """The stall predicate: `tempo="active"` with a `state.json` gone stale.

    An unknown age (`None`) is NOT stalled — the opposite direction from
    :func:`_is_stale_dead`, and deliberately so. There, unknown age blocks
    a respawn (never resurrect what cannot be proven fresh); here it would
    manufacture a stall report out of a file we simply could not read.

    Extracted so :func:`classify` and the NEEDS_HUMAN note in
    :func:`classify_background_rows` ask the SAME question — an escalated
    node that is also stalled classifies NEEDS_HUMAN (see :func:`classify`),
    so without this the stall fact would be silently unreportable for that
    shape.
    """
    return tempo == "active" and state_age_s is not None and state_age_s > stall_after_s


def is_needs_human(
    state: str | None, needs: str | None, *, queued_prompt: bool
) -> bool:
    """Escalation: `state=blocked`, a `needs` payload, and NO queued reply.

    The first two halves are the escalation itself. `state == "blocked"`
    alone is the plain block the watchdog has always been free to respawn;
    the `needs` payload is what makes it a question *asked of a human*,
    which `claude respawn` cannot answer — it returns the node IDLE with no
    prompt (`docs/receipts/565.md`), losing the payload entirely.

    ⚠️ **`queued_prompt` is the third half, and omitting it was a HIGH
    finding in the #601 v5 review — a defect this module INTRODUCED, not
    one it inherited.** The `needs` lifecycle, settled from the 2.1.223
    binary: a successfully delivered human reply flips the ledger active and
    CLEARS `needs`; if delivery fails, the reply handler persists
    `queuedPrompt` while leaving `state=blocked` and `needs` intact — and
    `claude respawn` is specifically able to consume that queued prompt and
    clear `needs`.

    So `blocked ∧ needs ∧ queuedPrompt` does **not** mean "waiting on a
    human". It means the human ALREADY ANSWERED and the answer is waiting to
    be delivered — and respawn is the delivery mechanism. Suppressing it
    there does not protect the question, it strands the answer: the node
    logs NEEDS_HUMAN every 60s forever while the reply is never delivered.
    A watchdog that silently stops recovering is a worse outage than one
    that over-recovers, because nothing ever reports it.

    :func:`is_terminal` already refuses to settle a node with a pending
    `queuedPrompt`, for exactly this reason (`docs/receipts/565.md`: a
    queued prompt defeats terminal suppression and requires a respawn).
    This predicate now agrees with it rather than contradicting it.
    """
    return state == ESCALATED_STATE and needs is not None and not queued_prompt


def is_reply_queued(
    state: str | None, needs: str | None, *, queued_prompt: bool
) -> bool:
    """An escalation whose human answer is written but not yet delivered.

    The exact complement of :func:`is_needs_human` on the `queued_prompt`
    axis: same `blocked ∧ needs`, opposite queued state. Split out because
    the two need OPPOSITE handling and share every other condition —
    `is_needs_human` must never respawn, this one is waiting for exactly
    the restart that delivers the reply.

    ⚠️ **It exists because the #601 v5 fix opened a hole in v6.** Adding
    `queued_prompt` to :func:`is_needs_human` restored delivery for a DEAD
    node (DEAD -> RESPAWN consumes the prompt), but a node whose pid is
    still ALIVE fell through every branch to plain ALIVE — no action, and
    on a non-verbose tick no note either. So the same shape got LESS
    visible than before #601 touched it, which is the "watchdog silently
    stops recovering" failure one commit earlier had called worse than
    over-recovery.

    The binary makes this reachable, not hypothetical: 2.1.223's reply
    handler can persist `queuedPrompt` after an `ENOCONN`/`ETIMEOUT` while
    the roster worker pid is still alive, and its own UI says the reply
    waits until the session restarts. A live-but-unreachable worker can
    therefore hold a human's answer indefinitely.

    The action is LOG, not respawn, deliberately: this watchdog only ever
    respawns a process confirmed dead, and `claude respawn` refuses an
    already-running session anyway — so a respawn here would be a no-op
    reported as a recovery. Making it VISIBLE is the whole fix; delivering
    it to a live-but-unreachable worker is not something this module can do.
    """
    return state == ESCALATED_STATE and needs is not None and queued_prompt


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
    necessarily exits); an escalated node is NEEDS_HUMAN regardless of
    `pid_alive` too (#601 — see below); a non-terminal node with no live
    process is DEAD; a non-terminal, live, ACTIVE node whose `state.json`
    has gone stale past `stall_after_s` is WEDGED (classify-and-log only in
    this slice — automated stall recovery is #590); everything else is
    ALIVE.

    **NEEDS_HUMAN sits ABOVE the `pid_alive` check on purpose**, and that
    placement is the whole fix: below it, an escalated node whose process
    had died would reach `DEAD` first and be respawned into an idle zombie.
    Being liveness-independent also means a *live* escalated node is now
    visible as NEEDS_HUMAN rather than hiding in ALIVE — the action is the
    same either way (log; never respawn), so nothing that used to happen to
    it stops happening.

    It sits BELOW the terminal check, also on purpose: a node that reached
    `done`/`failed`/`stopped` has settled, and a `needs` string left over in
    its `state.json` from an earlier turn must not resurrect it as an open
    question.

    ⚠️ **It therefore also out-ranks WEDGED**, and that costs something a
    later slice needs. A `tempo:"active"`, stale, escalated node is BOTH
    stalled and awaiting a human; one class cannot say two things, and
    NEEDS_HUMAN is the right one to keep (the human's question is the
    actionable fact, and hiding it is the harm #601 exists to stop). The
    stall fact is not dropped, though — :func:`classify_background_rows`
    appends it to the NEEDS_HUMAN note via :func:`is_stalled`, so #579/#590
    still see it. Reordering the two would invert the harm; extend the note,
    not the precedence.
    """
    if is_terminal(node.state, node.tempo, queued_prompt=node.queued_prompt):
        return NodeClass.DONE
    if is_needs_human(node.state, node.needs, queued_prompt=node.queued_prompt):
        return NodeClass.NEEDS_HUMAN
    if not pid_alive:
        return NodeClass.DEAD
    # AFTER the DEAD branch on purpose: a queued reply on a DEAD node is
    # delivered by the respawn DEAD already plans, and must not be diverted
    # to a log line. This branch is therefore live-nodes-only by position.
    if is_reply_queued(node.state, node.needs, queued_prompt=node.queued_prompt):
        return NodeClass.REPLY_QUEUED
    if is_stalled(node.tempo, state_age_s, stall_after_s):
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


def _is_stale_dead(state_age_s: float | None, max_age_s: float) -> bool:
    """True when a DEAD node's age disqualifies it from auto-respawn.

    Unknown age (`None`) counts as stale: never resurrect something whose
    freshness cannot be proven.
    """
    return state_age_s is None or state_age_s > max_age_s


def _stale_dead_reason(state_age_s: float | None) -> str:
    """The exact wording for a stale/unknown-age DEAD node.

    Shared by :func:`plan` (the `Action.reason`) and
    :func:`classify_background_rows` (the printed note) so the two can
    never say two different things about the same node.
    """
    age_text = "unknown age" if state_age_s is None else f"{state_age_s:.0f}s"
    return (
        f"stale beyond --max-age ({age_text}) — not crash recovery; "
        "claude stop/rm it or respawn manually"
    )


def _needs_human_reason() -> str:
    """The exact wording for an escalated (NEEDS_HUMAN) node.

    Shared by :func:`plan` (the `Action.reason`) and
    :func:`classify_background_rows` (the printed note) so the two can
    never say two different things about the same node — the same
    single-source shape as :func:`_stale_dead_reason`.

    ⚠️ **Both scope qualifiers below are load-bearing, not hedging.** The
    first draft of this string said *"never auto-respawned at any age
    (project + label dag:needs-human)"*, and the #601 adversarial review
    raised BOTH halves as HIGH findings — correctly, because each asserted
    something this module does not do:

    - **"by this tick".** Suppressing :data:`ActionKind.RESPAWN` binds THIS
      watchdog only. The harness runs its own supervisor whose respawn
      predicate (`docs/receipts/565.md`) reads state/tempo/`queuedPrompt`
      and **not** `needs`, so it is a separate route this module cannot
      close, and whether it fires for a `blocked` node is still the
      unverified single-route claim #575 handed to #590. An unqualified
      "never auto-respawned" would tell an operator the question is safe
      when only one of two routes is known shut.
    - **"not done here".** Nothing in this process emits the label or the
      tracker comment (#602). Naming an action in a log line that the code
      does not perform is how a reader concludes the escalation reached the
      tracker when it reached a launchd log.
    """
    return (
        "escalated — state=blocked with a needs payload and no queued "
        "reply, so a human was asked a question a respawn cannot answer; "
        "not respawned BY THIS TICK at any age, re-checked immediately "
        "before spawn (a read-to-spawn window remains, irreducible without "
        "a lock the harness does not expose; and the harness's own "
        f"supervisor is a separate route this module cannot close — #590); "
        f"tracker projection to {NEEDS_HUMAN_LABEL} is NOT done here — #602"
    )


def needs_human_reason() -> str:
    """The public accessor for :func:`_needs_human_reason` (#602 phase 2).

    A thin re-export, and deliberately not a rename. `dag_project` reproduces
    this string VERBATIM into the tracker comment rather than paraphrasing it,
    which means the golden-equality pin in `tests/test_dag_tick.py` now also
    guards operator-facing tracker content — so the string must keep exactly one
    definition. Exposing an accessor rather than reaching into the private name
    keeps that single definition while making the cross-module read legible.

    ⚠️ The wording still says the projection is **"NOT done here — #602"**, and
    that stays TRUE after #602 ships: `dag_project` is a separate process, and
    this tick still does not project. Do not "update" it on the strength of the
    projector existing.
    """
    return _needs_human_reason()


def _reply_queued_reason() -> str:
    """The exact wording for a live node holding an undelivered reply.

    Same single-source shape as :func:`_needs_human_reason` — `plan` and
    the note loop must not say two different things about one node.

    It states what it CANNOT do as well as what it saw: this watchdog only
    respawns a confirmed-dead process, and `claude respawn` refuses an
    already-running session, so there is no action available here. Saying
    so is the point — the failure this class exists to end was silence.
    """
    return (
        "reply queued but undelivered — state=blocked with a needs payload "
        "AND a queuedPrompt while the process is still alive, so a human "
        "already answered and the answer is waiting on a restart this "
        "module must not perform (it respawns only a confirmed-dead "
        "process, and the CLI refuses an already-running session); "
        "log-only, and no automated recovery exists for this shape"
    )


def _stop_reason() -> str:
    """The exact wording for a terminal node whose process is still alive.

    ⚠️ **The qualifier is load-bearing, exactly as it is in
    :func:`_needs_human_reason`.** This reason used to be the bare
    *"terminal state but the process is still running"*, which stated the
    classification snapshot as though it were the fact at stop time — and
    #604 is precisely that gap: the snapshot can be a tick (60s) old, and
    a human reply can make the node non-terminal inside it.

    :func:`execute_stop` now re-applies :func:`is_terminal` immediately
    before the stop, so the qualifier says both halves: the re-check
    happens, AND a read-to-stop window survives it. Naming the residual is
    the honest form — a check-then-act against a file another process may
    write cannot be made race-free without a lock the harness does not
    expose, and an unqualified "verified terminal" would tell an operator
    the stop is safe when it is only much safer.
    """
    return (
        "terminal state but the process is still running; re-checked "
        "immediately before the stop (a read-to-stop window remains, "
        "irreducible without a lock the harness does not expose)"
    )


def plan(
    classified_nodes: Sequence[ClassifiedNode], *, max_age_s: float
) -> list[Action]:
    """Map classified nodes to actions. Pure — no subprocess calls here.

    NEEDS_HUMAN -> a log-only action, ALWAYS and regardless of age or
    liveness (#601): the human's question is the thing being preserved, and
    `claude respawn` would discard it. Note this arm is deliberately NOT
    subject to `max_age_s` — an escalation does not become respawnable by
    getting old, which is exactly the accident `--max-age` was covering for.
    DEAD -> respawn (subject to the fresh re-check in
    :func:`execute_respawn`), UNLESS the node's `state_age_s` exceeds
    `max_age_s` or could not be determined at all — either way that is a
    LOG action instead (:func:`_stale_dead_reason`): a genuinely old or
    unknown-age DEAD node is not the crash-mid-activity case this watchdog
    exists to recover, and an unknown age must never resurrect something
    that might have been dead for weeks.
    DONE with a still-live pid -> stop (a lingering process past settle),
    subject to the fresh terminal+pid re-check in :func:`execute_stop` —
    this arm plans from a snapshot a human can invalidate (#604);
    WEDGED -> a log-only action, since automated stall recovery is #590;
    ALIVE, or DONE with no live pid, -> no action.
    """
    actions: list[Action] = []
    for classified in classified_nodes:
        if classified.node_class is NodeClass.NEEDS_HUMAN:
            actions.append(
                Action(ActionKind.LOG, classified.node_id, _needs_human_reason())
            )
        elif classified.node_class is NodeClass.REPLY_QUEUED:
            actions.append(
                Action(ActionKind.LOG, classified.node_id, _reply_queued_reason())
            )
        elif classified.node_class is NodeClass.DEAD:
            if _is_stale_dead(classified.state_age_s, max_age_s):
                actions.append(
                    Action(
                        ActionKind.LOG,
                        classified.node_id,
                        _stale_dead_reason(classified.state_age_s),
                    )
                )
            else:
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
                    _stop_reason(),
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
    """Best-effort liveness check via `kill(pid, 0)` — no signal is sent.

    ⚠️ **`PermissionError` (EPERM) reads ALIVE on purpose, and that is NOT
    the half of #593 that needed fixing.** The 2.1.224 bundle ships TWO
    predicates over the same syscall: `isProcessRunning` (any throw ->
    dead) and `isProcessProvablyGone` (`return zt(t)==="ESRCH"` — only a
    real ESRCH is "gone"; EPERM is not). This function is the second one,
    and that is right for a caller whose DEAD branch RESPAWNS: a
    false-DEAD double-starts a node, which #601 exists to prevent, while a
    false-ALIVE only misses one recovery cycle.

    The EPERM hazard is real, but it is an IDENTITY failure, not a
    liveness one: a recycled pid landing on another user's process
    (root's, say) answers `kill(pid, 0)` with EPERM forever. That case is
    now caught one step later by :func:`background_pid_alive`'s
    `procStart` comparison — `ps` reads another user's start time fine,
    so the mismatch is visible exactly where `kill(pid, 0)` is blind.
    Verified live on pid 1 (`docs/receipts/593.md`).
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_proc_start(pid: int) -> str | None:
    """A process's start time in the exact encoding the roster records.

    `LC_ALL=C TZ=UTC ps -o lstart= -p <pid>`, trimmed — byte-for-byte the
    recipe the CLI bundle uses to MINT `procStart` (2.1.224
    `getProcessStartTime`, and the same command in its async twin). Both
    env vars are load-bearing, not decoration: the same live process reads
    `Fri Aug  7 14:12:08 2026` under this host's local zone against a
    roster holding `Fri Aug  7 19:12:08 2026`, so a reader that dropped
    `TZ=UTC` would report a mismatch for EVERY node on the fleet.

    `None` means **"`ps` did not answer"** — a dead pid, a missing `ps`, a
    timeout, empty output. It never means "the times differ"; that
    distinction is the whole safety property, and the caller relies on it.
    """
    try:
        result = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "LC_ALL": "C", "TZ": "UTC"},
            timeout=PROC_START_TIMEOUT_S,
        )
    except OSError, subprocess.SubprocessError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def background_pid_alive(
    node_id: str,
    roster: dict[str, RosterWorker] | None,
    *,
    is_alive: Callable[[int], bool] | None = None,
    proc_start: Callable[[int], str | None] | None = None,
) -> bool:
    """Is there a live process behind this background node, and is it OURS?

    `roster` is `None` when the daemon roster could not be read — act
    conservatively and assume alive, so a read glitch can never trigger a
    respawn. A roster that WAS read and does not name this node is real
    negative evidence: a background census row with no roster entry is
    exactly the harness's documented gap — a session "still working or
    blocked even when its process has exited". `is_alive` and `proc_start`
    are test seams mirroring `gcc_sha.compute_sha`'s injected fetcher,
    defaulting to :func:`pid_is_alive` and :func:`read_proc_start`.

    **PID liveness alone is not identity (#593).** A pid outlives nothing
    on POSIX — the OS recycles it, and a recycled pid answers
    `kill(pid, 0)` exactly like the node's own process did, so a crashed
    node reads ALIVE forever and is never respawned. The roster carries a
    `procStart` alongside the pid precisely so the pair identifies a
    process rather than a slot.

    This mirrors the harness's OWN roster predicate, which reads the same
    `roster.json` in its GC path and keeps a worker only when
    `isProcessRunning(pid) && isSameProcessAsync(pid, entry.procStart)`:

    - **no recorded `procStart`** -> pid liveness decides. The harness's
      `isSameProcessAsync(pid, undefined)` returns `true`; an entry
      written by a build that did not record one must not be reaped for
      lacking it.
    - **`ps` did not answer** -> ALIVE. `isSameProcess`'s comparator
      (`actual === undefined || actual === recorded`) treats an unread
      start time as a MATCH, never a mismatch. A `ps` that times out must
      not be able to trigger a respawn. A BLANK reading counts as
      unanswered here too, and is checked twice on purpose — the reader
      normalizes it and this branch re-tests it — because an empty string
      compared as if it were a real reading differs from every recorded
      value, i.e. it fails toward the respawn.
    - **recorded and read, and they differ** -> DEAD. This is the only
      branch that adds a negative, and it needs a positively-read,
      differing value to fire.

    Comparison is exact string equality, which is what the harness does on
    this platform: its one tolerance (a numeric-units escape for the
    alternate `procStartFt` encoding) sits behind a mode function that is
    a hard `return false` in all three on-disk bundles, and an `lstart`
    string is not numeric anyway. Evidence, both arms:
    `docs/receipts/593.md`.
    """
    if roster is None:
        return True
    entry = roster.get(node_id)
    if entry is None:
        return False
    check = is_alive or pid_is_alive
    if not check(entry.pid):
        return False
    if entry.proc_start is None:
        return True
    observed = (proc_start or read_proc_start)(entry.pid)
    if not observed:
        return True
    return observed == entry.proc_start


def node_from_state(node_id: str, data: Mapping[str, object]) -> Node:
    """Build a :class:`Node` from one parsed `state.json`, defensively.

    Shared by :func:`classify_background_rows` (the census path),
    :func:`execute_respawn`'s fresh escalation re-check and
    :func:`execute_stop`'s fresh terminal re-check, so no two of them can
    disagree about what the same file says — the #601 v4 review's HIGH
    finding was exactly a disagreement of that shape, where only one of the
    two looked at `needs` at all.
    """
    state = data.get("state")
    tempo = data.get("tempo")
    return Node(
        node_id=node_id,
        state=state if isinstance(state, str) else None,
        tempo=tempo if isinstance(tempo, str) else None,
        queued_prompt=bool(data.get("queuedPrompt")),
        needs=normalize_needs(data.get("needs")),
    )


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


def gate_preflight(ctx: TickContext) -> Literal["on", "off", "unknown"]:
    """Run the read-only fleet-gate preflight and classify its stderr.

    Mints a fresh bogus job id per call — a published id stops discriminating
    once it is a real (or once-real) job (`.claude/rules/
    probes-need-a-control-arm.md`).

    `ctx.claude_bin` not existing/executable (`FileNotFoundError`/
    `PermissionError`, both `OSError`) is treated the same as an ambiguous
    gate read: `"unknown"`, which :func:`execute_tick` now PROCEEDS past
    (with a warning) rather than skipping — see the module docstring.
    """
    bogus_id = uuid.uuid4().hex
    try:
        result = subprocess.run(
            [ctx.claude_bin, "logs", bogus_id],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        logger.warning(
            "dag-tick: claude binary %r unavailable for gate preflight: %s",
            ctx.claude_bin,
            exc,
        )
        return "unknown"
    return gate_status(result.stderr)


def read_census(ctx: TickContext) -> list[dict[str, object]]:
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
            [ctx.claude_bin, "agents", "--json", "--cwd", ctx.cwd, "--all"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        logger.warning(
            "dag-tick: claude binary %r unavailable for census: %s",
            ctx.claude_bin,
            exc,
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
    ctx: TickContext,
    *,
    is_alive: Callable[[int], bool] | None = None,
    proc_start: Callable[[int], str | None] | None = None,
) -> ClassificationResult:
    """Enrich + classify every `kind:"background"` census row.

    Enrichment reads each node's `state.json` (state/tempo/queuedPrompt/
    needs + mtime) and the shared daemon roster (pid liveness), then calls
    :func:`classify`. A missing/unparseable `state.json` classifies ALIVE
    directly (act conservatively) rather than feeding a guessed state into
    the pure predicate. `is_alive` and `proc_start` are forwarded to
    :func:`background_pid_alive` (test seams — see its docstring).
    """
    roster = read_roster(ctx.daemon_dir)
    now = time.time()
    classified: list[ClassifiedNode] = []
    notes: list[str] = []
    for row in rows:
        node_id = row.get("id")
        if not isinstance(node_id, str) or not node_id:
            notes.append("dag-tick: skipping a background row with no usable id")
            continue
        data, mtime = load_state_json(ctx.jobs_dir, node_id)
        if data is None:
            classified.append(
                ClassifiedNode(
                    node_id, NodeClass.ALIVE, pid_alive=True, state_age_s=None
                )
            )
            if ctx.verbose:
                notes.append(
                    f"dag-tick: {node_id} state.json missing/unparseable — "
                    "classifying ALIVE (conservative)"
                )
            continue
        node = node_from_state(node_id, data)
        alive = background_pid_alive(
            node_id, roster, is_alive=is_alive, proc_start=proc_start
        )
        state_age_s = None if mtime is None else max(now - mtime, 0.0)
        node_class = classify(
            node,
            pid_alive=alive,
            state_age_s=state_age_s,
            stall_after_s=ctx.stall_after_s,
        )
        classified.append(
            ClassifiedNode(
                node_id, node_class, pid_alive=alive, state_age_s=state_age_s
            )
        )
        if node_class is NodeClass.NEEDS_HUMAN:
            # NEEDS_HUMAN out-ranks WEDGED in `classify`, so an escalated
            # node that is ALSO stalled would otherwise lose its stall
            # visibility entirely — both facts are true, and #579/#590 want
            # the second one. Carry it in the same line rather than dropping
            # it or emitting a competing note.
            stall_note = (
                f"; ALSO stalled — tempo active, state.json stale "
                f"{state_age_s:.0f}s > {ctx.stall_after_s:.0f}s"
                if is_stalled(node.tempo, state_age_s, ctx.stall_after_s)
                else ""
            )
            notes.append(
                f"dag-tick: NEEDS_HUMAN {node_id} — {_needs_human_reason()}; "
                f"needs: {node.needs}{stall_note}"
            )
        elif node_class is NodeClass.REPLY_QUEUED:
            notes.append(
                f"dag-tick: REPLY_QUEUED {node_id} — {_reply_queued_reason()}; "
                f"needs: {node.needs}"
            )
        elif node_class is NodeClass.WEDGED:
            notes.append(
                f"dag-tick: WEDGED {node_id} — tempo active, state.json "
                f"stale {state_age_s:.0f}s > {ctx.stall_after_s:.0f}s "
                "(log-only; automated stall recovery is #590)"
            )
        elif node_class is NodeClass.DEAD and _is_stale_dead(
            state_age_s, ctx.max_age_s
        ):
            notes.append(f"dag-tick: {node_id} {_stale_dead_reason(state_age_s)}")
        elif ctx.verbose:
            notes.append(
                f"dag-tick: {node_id} class={node_class.value} "
                f"state={node.state} tempo={node.tempo} pid_alive={alive}"
            )
    return ClassificationResult(classified=classified, notes=notes)


def execute_respawn(
    node_id: str,
    ctx: TickContext,
    *,
    is_alive: Callable[[int], bool] | None = None,
    proc_start: Callable[[int], str | None] | None = None,
) -> str:
    """Respawn one DEAD node, after a fresh ESCALATION and PID re-check.

    Eventual-consistency doctrine: never wait for or read back the result —
    the next tick observes it. The skip conditions guard against a race
    between classification (up to one tick, i.e. 60s, stale) and this call:
    if the roster now reports the pid alive, something else already revived
    the node and a second respawn would double-start it.

    ⚠️ **The escalation re-check is the #601 v4 review's HIGH finding, and
    it is not hypothetical.** `plan()` making NEEDS_HUMAN log-only protects
    a node only if the CLASSIFICATION saw the escalation. Actions are then
    executed from that snapshot, and this function used to re-read only the
    roster — so a node planned DEAD -> RESPAWN that acquired
    `state=blocked` + `needs` in between was respawned anyway, which is
    precisely the loss #601 exists to prevent. The reviewer demonstrated
    it: `snapshot_class=dead -> planned_action=respawn ->
    latest_class_before_execution=needs_human -> "dag-tick: RESPAWN race1"`.
    The window is real because a roster read is not instantaneous truth —
    a node absent from the roster is treated as dead (this module's own
    negative-evidence rule) while its process may still be running and
    still able to write `needs`.

    So the fresh re-check now covers BOTH axes it must: the escalation
    predicate as well as pid liveness. An unreadable `state.json` also
    SKIPs, deliberately — a node classified DEAD had a readable one, so its
    disappearance is anomalous, and "never resurrect what cannot be proven"
    already governs the age check one function over. (That refusal makes the
    node silent rather than retried: a persistently unreadable `state.json`
    classifies conservative-ALIVE next tick, so `execute_respawn` is not
    reached again. Correct, and worth stating — an earlier draft of this
    docstring claimed "the next tick retries", which is not what happens.)

    ⚠️ **ORDERING: BOTH reads happen first, THEN both decisions, then the
    spawn.** That is not stylistic, and it took two rounds to get right.
    The window is not closed by a check's existence but by its DISTANCE
    from the action: v5 showed that with the state read first, a roster
    read — real file I/O — sat between the escalation check and `Popen`,
    and a roster-absent-but-running node could write `blocked + needs`
    inside it (`RESPAWN race2`). Moving the escalation check last then
    pushed the PID check behind the state read instead, trading one TOCTOU
    for the other (`RESPAWN race3`) — a check cannot be last if another
    also must be. Reading both up front and deciding after leaves neither
    guard with I/O between it and the spawn.

    **It does not eliminate it.** A check-then-act against a file another
    process may write is irreducibly racy without a shared lock, a CAS, or a
    "respawn only if the predicate still holds" primitive the harness does
    not expose. The residual window is stated in the operator-facing reason
    rather than papered over, because golden equality now enforces that
    text and an unqualified "never" would be enforcing a falsehood.

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
    # BOTH reads first, THEN both decisions, then the spawn — so neither
    # guard has file I/O sitting between it and the action it protects.
    # See the ordering note in the docstring: an earlier version put one
    # check last and thereby pushed the OTHER one behind a roster read.
    fresh_data, _ = load_state_json(ctx.jobs_dir, node_id)
    roster = read_roster(ctx.daemon_dir)
    if fresh_data is None:
        return (
            f"dag-tick: SKIP respawn {node_id} — state.json unreadable at "
            "execution; cannot prove it is not an escalation"
        )
    fresh = node_from_state(node_id, fresh_data)
    if is_needs_human(fresh.state, fresh.needs, queued_prompt=fresh.queued_prompt):
        return (
            f"dag-tick: SKIP respawn {node_id} — escalated since "
            f"classification; {_needs_human_reason()}; needs: {fresh.needs}"
        )
    if background_pid_alive(node_id, roster, is_alive=is_alive, proc_start=proc_start):
        return f"dag-tick: SKIP respawn {node_id} — pid is alive now (reconciled)"
    try:
        subprocess.Popen(
            [ctx.claude_bin, "respawn", node_id],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=strip_respawn_env(),
            cwd=str(Path.home()),
            start_new_session=True,
        )
    except OSError as exc:
        return f"dag-tick: SKIP respawn {node_id} — claude binary unavailable: {exc}"
    # "requested", not "done": this never reads the child back (eventual
    # consistency — the next tick observes the outcome), and the CLI has its
    # own already-running refusal, so an unqualified "RESPAWN" would report
    # a refusal as a recovery. Flagged LOW in the #601 v6 review.
    return f"dag-tick: RESPAWN {node_id} (requested; outcome observed next tick)"


def execute_stop(
    node_id: str,
    ctx: TickContext,
    *,
    is_alive: Callable[[int], bool] | None = None,
    proc_start: Callable[[int], str | None] | None = None,
) -> str:
    """Stop one DONE-but-still-alive node, after a fresh TERMINAL + PID re-check.

    Classification can be up to one tick (60s) stale, so both facts are
    re-read right before acting. If the pid has already gone since
    classification (settled on its own, or something else already reaped
    it), SKIP rather than issue a stop that would log a false FAILED line
    against a process that no longer exists.

    ⚠️ **The terminal re-check is #604, and it is the exact mirror of the
    #601 v4 finding one function up.** Actions execute from the
    CLASSIFICATION snapshot, and this function used to re-read only the
    roster — so a node planned DONE -> STOP that stopped being terminal in
    between was stopped anyway. Both routes out of terminal are reachable
    by a human in that window: a delivered reply flips the ledger to
    `done + active`, and a reply whose delivery failed persists a
    `queuedPrompt` — and :func:`is_terminal` denies both. `claude stop` is
    live-proven to stop mid-activity (`docs/receipts/565.md`), so the
    unguarded path could terminate work a human had just resumed and
    persist `stopped` over it. Reproduced read-only in the #601 v5 review:
    a planned STOP against a freshly `done + active` state still issued
    `['claude', 'stop', 'done1']`.

    Reuses :func:`node_from_state` and :func:`is_terminal` so this
    re-check and the census path cannot disagree about the same file —
    that disagreement *was* the #601 defect, where only one of the two
    looked at `needs` at all.

    An unreadable `state.json` SKIPs, the same ruling
    :func:`execute_respawn` carries — one rule across both actions rather
    than two opposite readings of the same anomaly, since a node
    classified DONE necessarily HAD a readable one. State the consequence
    rather than glossing it: **it is not retried.** A node whose
    `state.json` stays unreadable classifies conservative-ALIVE next tick
    (:func:`classify_background_rows`), which `plan` maps to no action at
    all, so this function is never reached for it again and the process
    lingers **silently**. The asymmetry with respawn is worth naming and
    is not lopsided: refusing to STOP leaves a process running, refusing
    to RESPAWN leaves a node unrecovered, and both are quiet.

    ⚠️ **ORDERING: BOTH reads happen first, THEN both decisions, then the
    stop** — carried over from :func:`execute_respawn`, whose docstring
    records the two rounds it took to learn that the window is closed not
    by a check's existence but by its DISTANCE from the action. A roster
    read is real file I/O; leaving one between the terminal check and
    `subprocess.run` would reopen exactly the window this adds a check to
    narrow.

    **It narrows the window; it does not close it.** Check-then-act
    against a file another process may write is irreducibly racy without a
    shared lock, a CAS, or a "stop only if still terminal" primitive the
    harness does not expose. That residual is stated in the operator-facing
    reason :func:`plan` attaches to the STOP action rather than papered
    over with a guarantee this code cannot make.
    """
    # BOTH reads first, THEN both decisions, then the stop — so neither
    # guard has file I/O sitting between it and the action it protects.
    # See the ordering note in the docstring, and `execute_respawn`'s,
    # which records the two rounds that established it.
    fresh_data, _ = load_state_json(ctx.jobs_dir, node_id)
    roster = read_roster(ctx.daemon_dir)
    if fresh_data is None:
        return (
            f"dag-tick: SKIP stop {node_id} — state.json unreadable at "
            "execution; cannot prove it is still terminal (not retried — it "
            "classifies conservative-ALIVE next tick, so the process is left "
            "running and unreported)"
        )
    fresh = node_from_state(node_id, fresh_data)
    if not is_terminal(fresh.state, fresh.tempo, queued_prompt=fresh.queued_prompt):
        return (
            f"dag-tick: SKIP stop {node_id} — no longer terminal since "
            f"classification (state={fresh.state} tempo={fresh.tempo} "
            f"queuedPrompt={fresh.queued_prompt}); work may have been resumed"
        )
    if not background_pid_alive(
        node_id, roster, is_alive=is_alive, proc_start=proc_start
    ):
        return f"dag-tick: SKIP stop {node_id} — settled since classification"
    try:
        result = subprocess.run(
            [ctx.claude_bin, "stop", node_id],
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
    ctx: TickContext,
    *,
    is_alive: Callable[[int], bool] | None = None,
    proc_start: Callable[[int], str | None] | None = None,
) -> list[str]:
    """Run each planned action, or (under `ctx.dry_run`) describe it only.

    A `LOG` action already emitted its line from `classify_background_rows`'s
    NEEDS_HUMAN, WEDGED or stale-DEAD note, so there is nothing further to
    run for it here on the live path.
    """
    lines: list[str] = []
    for action in actions:
        if ctx.dry_run:
            lines.append(
                f"dag-tick: [dry-run] would {action.kind.value} "
                f"{action.node_id} — {action.reason}"
            )
        elif action.kind is ActionKind.RESPAWN:
            lines.append(
                execute_respawn(
                    action.node_id, ctx, is_alive=is_alive, proc_start=proc_start
                )
            )
        elif action.kind is ActionKind.STOP:
            lines.append(
                execute_stop(
                    action.node_id, ctx, is_alive=is_alive, proc_start=proc_start
                )
            )
    return lines


def reap_codex_lanes(
    classified_nodes: Sequence[ClassifiedNode],
    ctx: TickContext,
) -> list[str]:
    """Reap each node's Codex review lane, if it has one (#580).

    One line per lane that had something to say. A node with no lane
    directory is silent — most nodes never run a review lane, and a line per
    node per 60s would bury the ones that matter.

    ⚠️ **Log-only in this slice, and that is a scope boundary, not an
    oversight.** The reaper computes the EDGE (advance / reopen implement /
    reopen research / needs-human), but nothing here writes it to the
    tracker: projection is the SCHEDULER's job, one direction only
    (`docs/receipts/575.md` R1), and #602 is the ticket that implements it.
    Emitting the label from this process would make the tick a second writer
    on the tracker. So the reason strings below say what was DECIDED, never
    that it was applied — the same discipline `_needs_human_reason` carries,
    and for the same reason: naming an action the code does not perform is
    how a reader concludes an escalation reached the tracker when it reached
    a launchd log.

    A `NONE` edge is a genuine no-op (not settled, already processed, or a
    lane owned by someone else) and is reported only under `--verbose`: those
    are the steady-state outcomes and would otherwise be the bulk of the log.
    """
    lines: list[str] = []
    for classified in classified_nodes:
        run_dir = ctx.jobs_dir / classified.node_id / CODEX_LANE_DIRNAME
        if not run_dir.is_dir():
            continue
        result = codex_verdict.reap(
            run_dir,
            expected_owner=classified.node_id,
            rework_count=read_rework_count(run_dir),
            max_rework=ctx.max_rework,
        )
        if result.edge is codex_verdict.Edge.NONE and not ctx.verbose:
            continue
        lines.append(
            f"dag-tick: CODEX-REAP {classified.node_id} "
            f"[{result.outcome.value}] edge={result.edge.value} — "
            f"{result.detail}; edge is DECIDED here, not applied — tracker "
            f"projection is #602"
        )
    return lines


def read_rework_count(run_dir: Path) -> int:
    """How many times this unit of work has already been reworked.

    Read from the lane record the launcher maintains. A missing or
    unparsable count reads as **0**, which is the permissive direction —
    and that is deliberate: the alternative (assume the budget is spent)
    would escalate every lane whose launcher had not yet written the field,
    turning a rollout into an escalation storm. The bound still holds for
    every lane the launcher does maintain, and #573 owns the counter itself.
    """
    try:
        raw = (run_dir / codex_verdict.LANE_FILENAME).read_text()
        data = json.loads(raw)
    except OSError, json.JSONDecodeError:
        return 0
    if not isinstance(data, dict):
        return 0
    count = data.get("rework_count", 0)
    return count if isinstance(count, int) and count >= 0 else 0


def build_tick_context(args: argparse.Namespace) -> TickContext:
    """Turn CLI args + this module's own path/lock defaults into a `TickContext`.

    The injection seam (#578 respec round 3): :func:`run_tick` calls this
    once, then threads the result explicitly through :func:`execute_tick`
    and every helper below it, so nothing downstream reaches for
    `JOBS_DIR`/`DAEMON_DIR`/`LOCK_PATH` on its own and no test needs to
    monkeypatch them.
    """
    return TickContext(
        claude_bin=args.claude_bin or shutil.which("claude") or DEFAULT_CLAUDE_BIN,
        cwd=args.cwd or str(Path.cwd()),
        jobs_dir=JOBS_DIR,
        daemon_dir=DAEMON_DIR,
        lock_path=LOCK_PATH,
        stall_after_s=args.stall_after,
        max_age_s=args.max_age,
        max_rework=args.max_rework,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def run_tick(args: argparse.Namespace) -> int:
    """The launchd tick's CLI entry point.

    Builds a `TickContext` from `args` plus this module's own path/lock
    defaults, then runs :func:`execute_tick`. Kept as a thin two-line
    wrapper so tests exercise `execute_tick` directly against a
    `tmp_path`-scoped context instead of monkeypatching `JOBS_DIR`/
    `DAEMON_DIR`/`LOCK_PATH` on this module.
    """
    return execute_tick(build_tick_context(args))


def execute_tick(ctx: TickContext) -> int:
    """Lock -> gate preflight -> census -> classify -> plan -> act -> report.

    Always returns 0 — a launchd `StartInterval` agent has nowhere useful to
    surface a nonzero exit beyond its own log, and every failure mode here
    (lock contention, gate off, a census read failure) degrades to "do
    nothing this tick" by design: the next tick, 60s later, reconciles.
    """
    lock_handle = try_acquire_lock(ctx.lock_path)
    if lock_handle is None:
        return 0
    try:
        gate = gate_preflight(ctx)
        if gate == "off":
            logger.warning("dag-tick: fleet gate preflight is off — skipping this tick")
            return 0
        if gate == "unknown":
            logger.warning(
                "dag-tick: fleet gate preflight is unknown — proceeding "
                "anyway; the census read is itself gated and logs its own "
                "failures loudly, so it is the real gate"
            )

        rows = read_census(ctx)
        bg_rows = [row for row in rows if row.get("kind") == "background"]
        result = classify_background_rows(bg_rows, ctx)
        action_lines = _execute_or_preview(
            plan(result.classified, max_age_s=ctx.max_age_s), ctx
        )
        reap_lines = reap_codex_lanes(result.classified, ctx)
        for line in (*result.notes, *action_lines, *reap_lines):
            sys.stdout.write(f"{line}\n")
        return 0
    finally:
        lock_handle.close()
