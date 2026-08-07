"""Tests for the launchd watchdog tick (dotfiles_setup.dag_tick, #578).

Pure/table-driven tests cover the terminal predicate, `classify()`,
`strip_respawn_env()`, `gate_status()`, and `plan()` directly — no
subprocess, no filesystem. The census-enrichment and action-execution paths
are exercised against `tmp_path` fixtures with `subprocess` monkeypatched;
none of these tests invoke the real `claude` binary or mutate anything on
this host.

#578 respec round 3 (injection seam, `tests/AGENTS.md` § Mocking): every
test that used to monkeypatch this module's own `LOCK_PATH`/`JOBS_DIR`/
`DAEMON_DIR` globals, or `pid_is_alive`, now constructs a
`dag_tick.TickContext` against `tmp_path` (`_ctx()`) and/or injects a fake
liveness predicate instead — `subprocess` and `os.environ` stay the only
things monkeypatched here, since those are external system boundaries, not
our own module. `_roster()` dedups the repeated mkdir+roster.json fixture
writes.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import classifier_tables, codex_verdict, dag_tick

if TYPE_CHECKING:
    from collections.abc import Mapping

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _node(
    *,
    node_id: str = "abc123",
    state: str | None = "blocked",
    tempo: str | None = "idle",
    queued_prompt: bool = False,
    needs: str | None = None,
) -> dag_tick.Node:
    return dag_tick.Node(
        node_id=node_id,
        state=state,
        tempo=tempo,
        queued_prompt=queued_prompt,
        needs=needs,
    )


# The two escalation payloads read live off this host's stale census nodes
# (#601) — `needs` is a plain string, and one of the pair carries no
# `suggestedReply` at all. Used verbatim so the fixtures are the real shape,
# not an invented one.
_LIVE_NEEDS_JULY_13 = "run `/clear` to proceed to next task"
_LIVE_NEEDS_JULY_22 = (
    "do /clear with resume, or run full command-catalog extraction first?"
)


def _write_state(jobs_dir: Path, node_id: str, payload: dict[str, object]) -> None:
    job_dir = jobs_dir / node_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "state.json").write_text(json.dumps(payload))


def _roster(
    tmp_path: Path,
    workers: dict[str, int],
    proc_starts: dict[str, str] | None = None,
) -> Path:
    """Write a readable `roster.json` under `tmp_path/"daemon"`.

    Names each `node_id -> pid` in `workers` (an empty dict is a readable
    roster naming NO worker — real negative pid evidence, distinct from a
    missing/unreadable roster FILE, which is conservative ALIVE). Returns
    the daemon dir, since every caller needs it for `_ctx()` /
    `classify_background_rows` too. Dedups the ~10 repeated
    mkdir+roster.json writes this file used to carry (#578 respec round 3).

    `proc_starts` adds the `procStart` a real roster carries beside the pid
    (#593). Omitting a node leaves the field absent, which is what every
    pre-#593 fixture means and what the harness's own predicate treats as
    "pid liveness decides".
    """
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir(exist_ok=True)
    entries: dict[str, dict[str, object]] = {}
    for node_id, pid in workers.items():
        entry: dict[str, object] = {"pid": pid}
        if proc_starts and node_id in proc_starts:
            entry["procStart"] = proc_starts[node_id]
        entries[node_id] = entry
    (daemon_dir / "roster.json").write_text(json.dumps({"workers": entries}))
    return daemon_dir


def _ctx(tmp_path: Path, **overrides: object) -> dag_tick.TickContext:
    """A `TickContext` scoped to `tmp_path`.

    The injection seam (#578 respec round 3) that replaces monkeypatching
    `LOCK_PATH`/`JOBS_DIR`/`DAEMON_DIR` on the module.
    """
    base: dict[str, object] = {
        "claude_bin": "claude",
        "cwd": "/x",
        "jobs_dir": tmp_path / "jobs",
        "daemon_dir": tmp_path / "daemon",
        "lock_path": tmp_path / "dag-tick.lock",
        "stall_after_s": 120.0,
        "max_age_s": dag_tick.DEFAULT_MAX_AGE_SECONDS,
        "max_rework": dag_tick.DEFAULT_MAX_REWORK,
        "dry_run": False,
        "verbose": False,
    }
    base.update(overrides)
    return dag_tick.TickContext(**base)


def _tick_args(**overrides: object) -> argparse.Namespace:
    base: dict[str, object] = {
        "cwd": None,
        "dry_run": False,
        "claude_bin": "claude",
        "stall_after": 120.0,
        "max_age": dag_tick.DEFAULT_MAX_AGE_SECONDS,
        "verbose": False,
        "max_rework": dag_tick.DEFAULT_MAX_REWORK,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class _FakeCompleted:
    """Stand-in for `subprocess.CompletedProcess` in monkeypatched tests."""

    def __init__(self, *, returncode: int, stderr: str = "", stdout: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout


# ---------------------------------------------------------------------------
# is_terminal() — the 7 terminal-predicate arms from docs/receipts/565.md
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "tempo", "queued_prompt", "expected"),
    [
        ("done", "idle", False, True),
        ("failed", "idle", False, True),
        ("stopped", "idle", False, True),
        ("killed", "idle", False, False),
        ("blocked", "idle", False, False),
        ("done", "active", False, False),
        ("done", "idle", True, False),
    ],
)
def test_terminal_predicate_arms(
    state: str, tempo: str, *, queued_prompt: bool, expected: bool
) -> None:
    assert dag_tick.is_terminal(state, tempo, queued_prompt=queued_prompt) is expected


# ---------------------------------------------------------------------------
# normalize_needs() / is_needs_human() — the #601 escalation predicate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (_LIVE_NEEDS_JULY_13, _LIVE_NEEDS_JULY_13),
        (_LIVE_NEEDS_JULY_22, _LIVE_NEEDS_JULY_22),
        ("  padded question?  ", "padded question?"),
        # Absence, in every shape state.json can express it.
        (None, None),
        ("", None),
        ("   ", None),
        ("\n\t", None),
        ([], None),
        ({}, None),
    ],
)
def test_normalize_needs_both_directions(raw: object, expected: str | None) -> None:
    assert dag_tick.normalize_needs(raw) == expected


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        (["pick one"], "pick one"),
        ({"question": "which?"}, "which?"),
        (42, "42"),
    ],
)
def test_normalize_needs_keeps_a_non_string_payload_as_an_escalation(
    raw: object, fragment: str
) -> None:
    """A shape a future harness version might write must NOT read as absence.

    Asserted as behaviour, not as an exact string: what the module owes is
    (a) a non-`None` result, so :func:`is_needs_human` still fires and the
    node is never respawned into an idle zombie, and (b) text an operator
    can act on in the log line. Pinning the exact `repr` instead would make
    a CPython formatting detail the contract, which `tests/AGENTS.md`
    forbids ("never through implementation details").
    """
    result = dag_tick.normalize_needs(raw)
    assert result is not None
    assert fragment in result
    # The consequence that actually matters, stated directly rather than
    # left to be inferred from the non-None above.
    assert dag_tick.is_needs_human("blocked", result, queued_prompt=False) is True


@pytest.mark.parametrize(
    ("state", "needs", "queued_prompt", "expected"),
    [
        # All three conditions met — the one shape that is an escalation.
        ("blocked", _LIVE_NEEDS_JULY_13, False, True),
        ("blocked", _LIVE_NEEDS_JULY_22, False, True),
        # `blocked` alone is the plain block the watchdog may still respawn.
        ("blocked", None, False, False),
        # A `needs` payload beside any other state is not an escalation.
        ("done", _LIVE_NEEDS_JULY_13, False, False),
        ("failed", _LIVE_NEEDS_JULY_13, False, False),
        ("stopped", _LIVE_NEEDS_JULY_13, False, False),
        ("killed", _LIVE_NEEDS_JULY_13, False, False),
        (None, _LIVE_NEEDS_JULY_13, False, False),
        (None, None, False, False),
        # ⚠️ A QUEUED PROMPT means the human already answered and delivery
        # failed — respawn is what consumes it and clears `needs`. Treating
        # this as an escalation strands the answer forever (#601 v5 HIGH).
        ("blocked", _LIVE_NEEDS_JULY_13, True, False),
        ("blocked", _LIVE_NEEDS_JULY_22, True, False),
    ],
)
def test_is_needs_human_requires_all_three_conditions(
    state: str | None, needs: str | None, *, queued_prompt: bool, expected: bool
) -> None:
    assert (
        dag_tick.is_needs_human(state, needs, queued_prompt=queued_prompt) is expected
    )


def test_queued_prompt_agrees_across_both_predicates() -> None:
    """A queued reply must make BOTH predicates say "respawn this".

    `is_terminal` already refuses to settle a node with a pending
    `queuedPrompt` (`docs/receipts/565.md`: a queued prompt defeats terminal
    suppression and requires a respawn). Before #601 v5, `is_needs_human`
    contradicted it — one predicate said "needs a respawn", the other said
    "never respawn" — and the contradiction resolved as a permanent
    deadlock. Pin the agreement, not just each side.
    """
    # Terminal-looking, but a queued prompt keeps it non-terminal.
    assert dag_tick.is_terminal("done", "idle", queued_prompt=True) is False
    # Escalation-looking, but a queued prompt means the answer is waiting.
    assert (
        dag_tick.is_needs_human("blocked", _LIVE_NEEDS_JULY_13, queued_prompt=True)
        is False
    )
    # Control: with no queued prompt each predicate keeps its own answer.
    assert dag_tick.is_terminal("done", "idle", queued_prompt=False) is True
    assert (
        dag_tick.is_needs_human("blocked", _LIVE_NEEDS_JULY_13, queued_prompt=False)
        is True
    )


@pytest.mark.parametrize(
    ("tempo", "state_age_s", "expected"),
    [
        ("active", 200.0, True),
        # Not stalled: not active, not yet past the threshold, exactly at
        # it, or an age that could not be read at all.
        ("idle", 200.0, False),
        ("blocked", 200.0, False),
        (None, 200.0, False),
        ("active", 10.0, False),
        ("active", 120.0, False),
        ("active", None, False),
    ],
)
def test_is_stalled_both_directions(
    tempo: str | None, state_age_s: float | None, *, expected: bool
) -> None:
    """Unknown age is NOT stalled — the opposite of `_is_stale_dead`.

    There, unknown age blocks a respawn; here it would invent a stall
    report out of a file that simply could not be read. The two helpers
    treat `None` in opposite directions on purpose, so both are pinned.
    """
    assert dag_tick.is_stalled(tempo, state_age_s, 120.0) is expected


def test_needs_human_state_is_not_terminal() -> None:
    """#601 does NOT make `blocked` terminal — the two predicates are apart.

    Widening `TERMINAL_STATES` would have suppressed the respawn too, but
    it would also have told the harness's own settle check that a plain
    blocked node is finished. The escalation is a separate predicate for
    exactly that reason.
    """
    assert dag_tick.ESCALATED_STATE not in dag_tick.TERMINAL_STATES
    assert (
        dag_tick.is_terminal(dag_tick.ESCALATED_STATE, "idle", queued_prompt=False)
        is False
    )


# ---------------------------------------------------------------------------
# classify() — see docstring for the precedence order it encodes
# ---------------------------------------------------------------------------


def test_classify_done_regardless_of_pid_alive() -> None:
    node = _node(state="done", tempo="idle")
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.DONE
    )
    assert (
        dag_tick.classify(node, pid_alive=True, state_age_s=None)
        is dag_tick.NodeClass.DONE
    )


def test_classify_dead_when_not_terminal_and_pid_not_alive() -> None:
    node = _node(state="blocked", tempo="idle")
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.DEAD
    )


# --- #601, arm A: blocked + needs + dead pid must NOT be DEAD -------------


def test_classify_escalated_dead_pid_is_needs_human_not_dead() -> None:
    """The defect arm: a dead-pid escalation used to classify DEAD.

    DEAD is what feeds `plan()`'s RESPAWN, and #565 measured that
    `claude respawn` returns a node IDLE with no prompt — the payload
    below would be silently discarded.
    """
    node = _node(state="blocked", tempo="blocked", needs=_LIVE_NEEDS_JULY_13)
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.NEEDS_HUMAN
    )


def test_classify_escalated_is_needs_human_regardless_of_pid_or_age() -> None:
    """NEEDS_HUMAN sits above the liveness check, so neither axis moves it."""
    node = _node(state="blocked", tempo="blocked", needs=_LIVE_NEEDS_JULY_22)
    for pid_alive in (True, False):
        for state_age_s in (None, 1.0, 999_999.0):
            assert (
                dag_tick.classify(node, pid_alive=pid_alive, state_age_s=state_age_s)
                is dag_tick.NodeClass.NEEDS_HUMAN
            )


def test_classify_escalation_with_a_queued_reply_is_dead_not_needs_human() -> None:
    """#601 v5 HIGH: a queued reply must reach the respawn path, not LOG.

    `blocked + needs + queuedPrompt` means the human ALREADY answered and
    delivery failed. `claude respawn` is what consumes the queued prompt and
    clears `needs`, so classifying NEEDS_HUMAN here logs forever and strands
    the answer — the watchdog silently stops recovering, which is worse than
    over-recovering because nothing reports it.
    """
    node = _node(
        state="blocked",
        tempo="blocked",
        needs=_LIVE_NEEDS_JULY_13,
        queued_prompt=True,
    )
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.DEAD
    )
    # Control: the SAME node without the queued reply is the escalation.
    assert (
        dag_tick.classify(
            _node(state="blocked", tempo="blocked", needs=_LIVE_NEEDS_JULY_13),
            pid_alive=False,
            state_age_s=None,
        )
        is dag_tick.NodeClass.NEEDS_HUMAN
    )


def test_execute_tick_respawns_an_escalation_whose_reply_is_queued(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The #601 v5 HIGH, end to end — the answer must get delivered.

    Driven through the whole chain rather than the predicate alone, because
    the deadlock this prevents is a whole-tick behaviour: classify -> plan ->
    execute must reach `claude respawn`, which is the mechanism that
    consumes `queuedPrompt` and clears `needs`.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(
        jobs_dir,
        "dead1",
        {
            "state": "blocked",
            "tempo": "blocked",
            "needs": _LIVE_NEEDS_JULY_13,
            "queuedPrompt": "do the full command catalog extraction pass",
        },
    )
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir, max_age_s=86400.0)
    popen_calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        popen_calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)

    assert dag_tick.execute_tick(ctx) == 0
    assert popen_calls == [["claude", "respawn", "dead1"]]


def test_classify_queued_reply_on_a_live_node_is_visible_not_silent() -> None:
    """#601 v6 HIGH: the liveness arm the v5 fix left silent.

    Adding `queued_prompt` to `is_needs_human` restored delivery for a DEAD
    node, but a node whose pid is still ALIVE fell through every branch to
    plain ALIVE — no action, and on a non-verbose tick no note either. The
    same shape became LESS visible than before #601 touched it.

    The binary makes it reachable: 2.1.223's reply handler can persist
    `queuedPrompt` after an ENOCONN/ETIMEOUT while the worker pid is still
    alive, and its own UI says the reply waits for a restart. So a
    live-but-unreachable worker can hold a human's answer indefinitely.
    """
    node = _node(
        state="blocked",
        tempo="blocked",
        needs=_LIVE_NEEDS_JULY_13,
        queued_prompt=True,
    )
    assert (
        dag_tick.classify(node, pid_alive=True, state_age_s=None)
        is dag_tick.NodeClass.REPLY_QUEUED
    )
    # …and it is a LOG action, so the tick reports it every pass.
    classified = dag_tick.ClassifiedNode(
        "abc123", dag_tick.NodeClass.REPLY_QUEUED, pid_alive=True, state_age_s=None
    )
    actions = dag_tick.plan([classified], max_age_s=86400.0)
    assert [a.kind for a in actions] == [dag_tick.ActionKind.LOG]
    assert "reply queued but undelivered" in actions[0].reason


def test_classify_queued_reply_on_a_dead_node_still_reaches_respawn() -> None:
    """The control arm: REPLY_QUEUED must NOT divert the delivery path.

    Same node, dead pid. DEAD -> RESPAWN is what consumes the queued prompt
    and clears `needs`, so a REPLY_QUEUED branch placed above the DEAD check
    would re-create the v5 deadlock while looking like an improvement.
    """
    node = _node(
        state="blocked",
        tempo="blocked",
        needs=_LIVE_NEEDS_JULY_13,
        queued_prompt=True,
    )
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.DEAD
    )


@pytest.mark.parametrize(
    ("state", "needs", "queued_prompt", "expected"),
    [
        ("blocked", _LIVE_NEEDS_JULY_13, True, True),
        # The complement of is_needs_human on exactly one axis.
        ("blocked", _LIVE_NEEDS_JULY_13, False, False),
        # Every other condition still has to hold.
        ("blocked", None, True, False),
        ("done", _LIVE_NEEDS_JULY_13, True, False),
        (None, _LIVE_NEEDS_JULY_13, True, False),
    ],
)
def test_is_reply_queued_is_the_complement_of_is_needs_human(
    state: str | None, needs: str | None, *, queued_prompt: bool, expected: bool
) -> None:
    """The two predicates must partition `blocked ∧ needs`, never overlap.

    An overlap would be a node that is simultaneously "never respawn" and
    "waiting for a restart" — the contradiction that produced the v5
    deadlock, in a new place.
    """
    assert (
        dag_tick.is_reply_queued(state, needs, queued_prompt=queued_prompt) is expected
    )
    if expected:
        assert (
            dag_tick.is_needs_human(state, needs, queued_prompt=queued_prompt) is False
        )


def test_classify_terminal_state_beats_a_leftover_needs_payload() -> None:
    """A settled node with a stale `needs` string stays DONE, not NEEDS_HUMAN."""
    node = _node(state="done", tempo="idle", needs=_LIVE_NEEDS_JULY_13)
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.DONE
    )


# --- #601, arm B: the control — plain `blocked` must behave as before ------


@pytest.mark.parametrize("needs", [None, "", "   "])
def test_classify_blocked_without_needs_still_dead_on_dead_pid(
    needs: str | None,
) -> None:
    """The control arm the ticket requires: no `needs`, no change.

    Parametrized over every shape `normalize_needs` maps to absence, so a
    fix that keyed off `state == "blocked"` alone — suppressing ALL
    respawns rather than only escalations — fails here.
    """
    node = _node(state="blocked", tempo="idle", needs=dag_tick.normalize_needs(needs))
    assert (
        dag_tick.classify(node, pid_alive=False, state_age_s=None)
        is dag_tick.NodeClass.DEAD
    )


def test_classify_wedged_when_active_and_stale() -> None:
    node = _node(state="blocked", tempo="active")
    result = dag_tick.classify(
        node, pid_alive=True, state_age_s=200.0, stall_after_s=120.0
    )
    assert result is dag_tick.NodeClass.WEDGED


def test_classify_alive_when_active_but_not_yet_stale() -> None:
    node = _node(state="blocked", tempo="active")
    result = dag_tick.classify(
        node, pid_alive=True, state_age_s=10.0, stall_after_s=120.0
    )
    assert result is dag_tick.NodeClass.ALIVE


def test_classify_alive_default() -> None:
    node = _node(state="blocked", tempo="idle")
    result = dag_tick.classify(node, pid_alive=True, state_age_s=None)
    assert result is dag_tick.NodeClass.ALIVE


def test_classify_active_with_unknown_age_is_alive_not_wedged() -> None:
    node = _node(state="blocked", tempo="active")
    result = dag_tick.classify(node, pid_alive=True, state_age_s=None)
    assert result is dag_tick.NodeClass.ALIVE


# ---------------------------------------------------------------------------
# classify() — THE COMPLETE TRUTH TABLE (#601 close-out)
# ---------------------------------------------------------------------------
#
# Six adversarial review rounds produced three HIGH findings that were all the
# same shape: a reachable combination nobody had enumerated. Round 5 found
# `blocked+needs+queuedPrompt+dead`; round 6 found the same with `alive`. Each
# fix made a new cell reachable and the next round walked into it.
#
# Patching cell-by-cell cannot terminate. Enumerating does. These are the four
# axes that decide a class, crossed exhaustively — 4 x 2 x 2 x 2 = 32 rows —
# with `tempo`/age pinned to values that keep WEDGED and --max-age out of the
# picture (both have their own tests). Every expected value below was derived
# BY HAND from the intended semantics and then checked against the code, not
# read off a run: a table transcribed from behaviour asserts only that the code
# does what it does (`tests/AGENTS.md`, tautological tests).

_TERMINAL = "done"  # representative of TERMINAL_STATES
_OTHER = "killed"  # non-terminal, non-escalated — the harness's other state

# ⚠️ `tempo` is the FIFTH axis, and its inclusion is the #601 v7 finding. The
# first version of this table pinned tempo="idle" and asserted in a comment,
# a commit message AND the contract that tempo "only matters for WEDGED".
# That was wrong in all three: `is_terminal` requires `tempo != "active"`, so
# a terminal state with tempo="active" is NOT terminal and falls through to
# the ordinary liveness rules. No test could have caught it, because the test
# encoded the same wrong assumption. Age stays pinned at None — that keeps
# WEDGED unreachable (an unknown age is never stalled), so this table isolates
# classification from staleness, which has its own tests.
_IDLE = "idle"
_ACTIVE = "active"

# The table's axes, IN COLUMN ORDER — the single place they are written down.
# `test_classify_truth_table_axes_match_the_registry` binds these names to
# `classifier_tables.REGISTRY`, which DERIVES the real axis set from
# `classify()` itself. That coupling is the #601 close-out's other half: a new
# axis appearing in the code fails the gate, the gate forces it into the
# registry, and the registry forces it into this dict — where it either gets a
# column (and the exhaustiveness check below demands its rows) or an explicit
# entry in `_PINNED_AXES`. Restating the axes locally, as this test did until
# the v7 finding, lets a real axis be absent from BOTH the code's enumeration
# and the table's, which is exactly how `tempo` went missing.
#
# `needs` is crossed as a BOOLEAN (payload present / absent) rather than as the
# payload string: `is_needs_human` only ever asks `needs is not None`, and
# `normalize_needs` has its own dedicated tests for the string shapes.
_AXIS_VALUES: dict[str, tuple[object, ...]] = {
    "state": (_TERMINAL, "blocked", _OTHER, None),
    "needs": (False, True),
    "queued_prompt": (False, True),
    "pid_alive": (False, True),
    "tempo": (_IDLE, _ACTIVE),
}

# Axes the code reads that this table deliberately holds CONSTANT. Each must
# also be pinned in `classifier_tables.REGISTRY` with the same justification —
# and the gate independently refuses a pin on any axis that can decide a class
# the table does not declare out of scope, so neither of these can quietly
# grow the reach `tempo` turned out to have.
_PINNED_AXES: frozenset[str] = frozenset({"state_age_s", "stall_after_s"})

_CLASSIFY_TABLE: list[tuple[str | None, bool, bool, bool, str, dag_tick.NodeClass]] = [
    # =====================================================================
    # tempo="idle" — the settled case
    # =====================================================================
    # --- terminal state: settles regardless of needs/pid ------------------
    (_TERMINAL, False, False, False, _IDLE, dag_tick.NodeClass.DONE),
    (_TERMINAL, False, False, True, _IDLE, dag_tick.NodeClass.DONE),
    (_TERMINAL, True, False, False, _IDLE, dag_tick.NodeClass.DONE),
    (_TERMINAL, True, False, True, _IDLE, dag_tick.NodeClass.DONE),
    # …unless a queued prompt defeats it — the harness's rule (565.md), not
    # ours. Then ordinary liveness rules resume.
    (_TERMINAL, False, True, False, _IDLE, dag_tick.NodeClass.DEAD),
    (_TERMINAL, False, True, True, _IDLE, dag_tick.NodeClass.ALIVE),
    (_TERMINAL, True, True, False, _IDLE, dag_tick.NodeClass.DEAD),
    (_TERMINAL, True, True, True, _IDLE, dag_tick.NodeClass.ALIVE),
    # --- blocked: the state #601 is about --------------------------------
    # No needs -> the plain block, unchanged from main.
    ("blocked", False, False, False, _IDLE, dag_tick.NodeClass.DEAD),
    ("blocked", False, False, True, _IDLE, dag_tick.NodeClass.ALIVE),
    ("blocked", False, True, False, _IDLE, dag_tick.NodeClass.DEAD),
    ("blocked", False, True, True, _IDLE, dag_tick.NodeClass.ALIVE),
    # needs, no queued reply -> the escalation. Liveness-independent: the
    # action (log, never respawn) is the same either way.
    ("blocked", True, False, False, _IDLE, dag_tick.NodeClass.NEEDS_HUMAN),
    ("blocked", True, False, True, _IDLE, dag_tick.NodeClass.NEEDS_HUMAN),
    # needs AND a queued reply -> the human ALREADY answered. Dead: respawn
    # delivers it. Alive: nothing here can deliver it, so make it visible.
    ("blocked", True, True, False, _IDLE, dag_tick.NodeClass.DEAD),
    ("blocked", True, True, True, _IDLE, dag_tick.NodeClass.REPLY_QUEUED),
    # --- other non-terminal state ----------------------------------------
    # `needs`/`queuedPrompt` are inert outside `blocked` — an escalation is a
    # property of being blocked, not of the payload existing.
    (_OTHER, False, False, False, _IDLE, dag_tick.NodeClass.DEAD),
    (_OTHER, False, False, True, _IDLE, dag_tick.NodeClass.ALIVE),
    (_OTHER, False, True, False, _IDLE, dag_tick.NodeClass.DEAD),
    (_OTHER, False, True, True, _IDLE, dag_tick.NodeClass.ALIVE),
    (_OTHER, True, False, False, _IDLE, dag_tick.NodeClass.DEAD),
    (_OTHER, True, False, True, _IDLE, dag_tick.NodeClass.ALIVE),
    (_OTHER, True, True, False, _IDLE, dag_tick.NodeClass.DEAD),
    (_OTHER, True, True, True, _IDLE, dag_tick.NodeClass.ALIVE),
    # --- absent/unparseable state ----------------------------------------
    # `None` is not terminal and not blocked, so it behaves like any other
    # non-terminal state. (A MISSING state.json never reaches classify at
    # all — classify_background_rows short-circuits it to conservative ALIVE.)
    (None, False, False, False, _IDLE, dag_tick.NodeClass.DEAD),
    (None, False, False, True, _IDLE, dag_tick.NodeClass.ALIVE),
    (None, False, True, False, _IDLE, dag_tick.NodeClass.DEAD),
    (None, False, True, True, _IDLE, dag_tick.NodeClass.ALIVE),
    (None, True, False, False, _IDLE, dag_tick.NodeClass.DEAD),
    (None, True, False, True, _IDLE, dag_tick.NodeClass.ALIVE),
    (None, True, True, False, _IDLE, dag_tick.NodeClass.DEAD),
    (None, True, True, True, _IDLE, dag_tick.NodeClass.ALIVE),
    # =====================================================================
    # tempo="active" — the half the first table could not see
    # =====================================================================
    # --- terminal state: NO LONGER TERMINAL. This is the whole finding —
    # `is_terminal` requires tempo != "active", so every DONE above becomes
    # an ordinary liveness decision here. A crash mid-activity leaves exactly
    # this shape, and it is the watchdog's PRIMARY recovery case
    # (`docs/receipts/565.md` arm B6: state done + tempo ACTIVE -> RESPAWNED).
    (_TERMINAL, False, False, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (_TERMINAL, False, False, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (_TERMINAL, True, False, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (_TERMINAL, True, False, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (_TERMINAL, False, True, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (_TERMINAL, False, True, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (_TERMINAL, True, True, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (_TERMINAL, True, True, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    # --- blocked: tempo does NOT reach it. `blocked` was never terminal, so
    # the terminal branch it changes is not on this path. Enumerated anyway —
    # "it cannot matter here" is the assumption that produced this axis.
    ("blocked", False, False, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    ("blocked", False, False, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    ("blocked", False, True, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    ("blocked", False, True, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    ("blocked", True, False, False, _ACTIVE, dag_tick.NodeClass.NEEDS_HUMAN),
    ("blocked", True, False, True, _ACTIVE, dag_tick.NodeClass.NEEDS_HUMAN),
    ("blocked", True, True, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    ("blocked", True, True, True, _ACTIVE, dag_tick.NodeClass.REPLY_QUEUED),
    # --- other non-terminal state: unchanged, for the same reason.
    (_OTHER, False, False, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (_OTHER, False, False, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (_OTHER, False, True, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (_OTHER, False, True, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (_OTHER, True, False, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (_OTHER, True, False, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (_OTHER, True, True, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (_OTHER, True, True, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    # --- absent/unparseable state: unchanged.
    (None, False, False, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (None, False, False, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (None, False, True, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (None, False, True, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (None, True, False, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (None, True, False, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
    (None, True, True, False, _ACTIVE, dag_tick.NodeClass.DEAD),
    (None, True, True, True, _ACTIVE, dag_tick.NodeClass.ALIVE),
]

# Per-class cell counts, derived from the PREDICATES rather than from the
# table — the #601 v7 Q3 finding. Coverage and class-diversity checks both
# pass on a table that assigns the five classes once and ALIVE to the other
# 59 cells, so neither constrains the MAPPING. These counts do:
#   DONE          = terminal ∧ ¬queued ∧ tempo≠active          -> 1*2*1*2*1 = 4
#   NEEDS_HUMAN   = blocked ∧ needs ∧ ¬queued                  -> 1*1*1*2*2 = 4
#   REPLY_QUEUED  = blocked ∧ needs ∧ queued ∧ alive           -> 1*1*1*1*2 = 2
#   DEAD          = every remaining ¬alive cell                -> 32-2-2    = 28
#   ALIVE         = every remaining alive cell                 -> 32-2-2-2  = 26
_EXPECTED_CLASS_COUNTS = {
    dag_tick.NodeClass.DONE: 4,
    dag_tick.NodeClass.NEEDS_HUMAN: 4,
    dag_tick.NodeClass.REPLY_QUEUED: 2,
    dag_tick.NodeClass.DEAD: 28,
    dag_tick.NodeClass.ALIVE: 26,
}


@pytest.mark.parametrize("row", _CLASSIFY_TABLE)
def test_classify_complete_truth_table(
    row: tuple[str | None, bool, bool, bool, str, dag_tick.NodeClass],
) -> None:
    """Every reachable (state, needs, queuedPrompt, pid, tempo) combination.

    The row is passed whole rather than unpacked into six parameters — the
    row IS the unit under test, and unpacking it trips ruff PLR0913 once the
    fifth axis exists. Suppressing that would violate `no_lint_skip`; taking
    the tuple is the honest shape.

    `state_age_s=None` is the one remaining pin: an unknown age is never
    stalled, so WEDGED stays unreachable here and staleness keeps its own
    tests. That pin is deliberate and asserted below, not assumed.
    """
    state, has_needs, queued_prompt, pid_alive, tempo, expected = row
    node = _node(
        state=state,
        tempo=tempo,
        needs=_LIVE_NEEDS_JULY_13 if has_needs else None,
        queued_prompt=queued_prompt,
    )
    assert dag_tick.classify(node, pid_alive=pid_alive, state_age_s=None) is expected


def test_classify_truth_table_is_exhaustive() -> None:
    """The table must COVER the cross product, not merely sample it.

    Computed from `_AXIS_VALUES` rather than hardcoded, so adding an axis
    value fails here instead of silently leaving cells unenumerated — which
    is how rounds 5, 6 and 7 each found a live defect. `_AXIS_VALUES` is in
    turn bound to the derived registry by the test below, so adding an
    AXIS (not merely a value) fails too.
    """
    expected_cells = set(itertools.product(*_AXIS_VALUES.values()))
    covered = {row[: len(_AXIS_VALUES)] for row in _CLASSIFY_TABLE}
    assert covered == expected_cells
    assert len(_CLASSIFY_TABLE) == len(expected_cells) == 64


def test_classify_truth_table_mapping_matches_the_predicates() -> None:
    """The #601 v7 Q3 fix: constrain the MAPPING, not just the coverage.

    Exhaustiveness and class-diversity together still pass on a table that
    assigns the five classes once each and ALIVE to the other 59 cells —
    the reviewer's counterexample. Per-class counts derived from the
    PREDICATES (see `_EXPECTED_CLASS_COUNTS`) do constrain it: getting one
    cell wrong moves two counts.

    This is a cross-check of two independent derivations — the per-row
    literals above, and the closed-form counts — not a recomputation of the
    code's logic. They can only agree if both are right.
    """
    actual = Counter(row[5] for row in _CLASSIFY_TABLE)
    assert dict(actual) == _EXPECTED_CLASS_COUNTS
    assert sum(_EXPECTED_CLASS_COUNTS.values()) == 64


def test_classify_truth_table_axes_match_the_registry() -> None:
    """The table's axis list must equal the one DERIVED from `classify()`.

    This is the fourth meta-test, and the one the first three structurally
    could not be: they all judge the table against itself. An axis the code
    reads but the table never heard of is invisible to coverage, to the
    class-diversity check and to the per-class counts alike — every one of
    them passes on a table that is internally perfect and externally short a
    column. That is `tempo` in round 7, and `queued_prompt` in rounds 5-6.

    `classifier_tables.REGISTRY` is checked against the real `classify()` by
    `dotfiles-setup classifier-axes` (the `classifier_axes` hk step), so
    equality here transitively binds this table to the code. Column ORDER is
    asserted separately because three of the five axes share the values
    `(False, True)` — a swap among them is undetectable by the cross product.
    """
    spec = classifier_tables.REGISTRY["dotfiles_setup.dag_tick:classify"]
    assert tuple(_AXIS_VALUES) == (
        "state",
        "needs",
        "queued_prompt",
        "pid_alive",
        "tempo",
    )
    assert frozenset(_AXIS_VALUES) == spec.axes
    assert frozenset(spec.pinned_axes) == _PINNED_AXES
    # The pins are real: no crossed axis may also be pinned, and together they
    # must account for every axis the code reads.
    assert not (frozenset(_AXIS_VALUES) & _PINNED_AXES)
    assert frozenset(_AXIS_VALUES) | _PINNED_AXES == spec.declared()


def test_classify_truth_table_reaches_every_class_it_can() -> None:
    """Guards against a table that enumerates cells but exercises one answer."""
    reached = {row[5] for row in _CLASSIFY_TABLE}
    assert reached == {
        dag_tick.NodeClass.DONE,
        dag_tick.NodeClass.DEAD,
        dag_tick.NodeClass.ALIVE,
        dag_tick.NodeClass.NEEDS_HUMAN,
        dag_tick.NodeClass.REPLY_QUEUED,
    }
    # WEDGED is the one class this table cannot reach, by construction —
    # age is pinned None. Asserted so its absence reads as deliberate, and
    # so that a future change making it reachable fails loudly here.
    assert dag_tick.NodeClass.WEDGED not in reached
    assert dag_tick.is_stalled(_ACTIVE, None, 120.0) is False


# ---------------------------------------------------------------------------
# strip_respawn_env() — both directions
# ---------------------------------------------------------------------------


def test_strip_respawn_env_removes_denylist_and_bg_prefix() -> None:
    env: dict[str, str] = {
        "PATH": "/usr/bin",
        "CLAUDE_CODE_SESSION_KIND": "background",
        "CLAUDE_BG_SOURCE": "daemon",
        "CLAUDE_BG_ISOLATION": "none",
        "CLAUDE_BG_BACKEND": "daemon",
        "CLAUDE_CODE_SESSION_NAME": "x",
        "CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1",
        "CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS": "100",
        "CLAUDE_CODE_RESUME_PROMPT": "hi",
        "CLAUDE_CODE_RESUME_SOURCE_ALIVE": "1",
        "CLAUDE_BG_POST_CLEAR_RESPAWN": "1",
        "CLAUDE_BG_SESSION_PERMISSION_RULES": "{}",
        "CLAUDE_BG_MEMORY_TOGGLED_OFF": "1",
        "CLAUDE_JOB_DIR": "job-dir-marker",
        "CLAUDE_BG_UNLISTED_BUT_PREFIXED": "still dies",
    }
    assert dag_tick.strip_respawn_env(env) == {"PATH": "/usr/bin"}


def test_strip_respawn_env_preserves_control_vars() -> None:
    env: Mapping[str, str] = {
        "PATH": "/usr/bin",
        "HOME": "/Users/x",
        "AWS_REGION": "us-east-1",
    }
    result = dag_tick.strip_respawn_env(env)
    assert result == dict(env)
    assert result is not env


def test_strip_respawn_env_defaults_to_os_environ(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("CLAUDE_BG_SOURCE", "daemon")
    result = dag_tick.strip_respawn_env()
    assert result["PATH"] == "/usr/bin"
    assert "CLAUDE_BG_SOURCE" not in result


# ---------------------------------------------------------------------------
# gate_status() — the three faces
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stderr_text", "expected"),
    [
        (
            "No job matching 'zzbogus'. Run 'claude agents' to list running sessions.",
            "on",
        ),
        ("'logs' is disabled by CLAUDE_CODE_DISABLE_AGENT_VIEW.", "off"),
        ("'logs' is disabled by the 'disableAgentView' setting.", "off"),
        ("some unrelated error message", "unknown"),
        ("", "unknown"),
    ],
)
def test_gate_status_three_faces(stderr_text: str, expected: str) -> None:
    assert dag_tick.gate_status(stderr_text) == expected


# ---------------------------------------------------------------------------
# plan() — the classification -> action table, incl. --max-age (round 3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("node_class", "pid_alive", "state_age_s", "expected_kind"),
    [
        (dag_tick.NodeClass.DEAD, False, 10.0, dag_tick.ActionKind.RESPAWN),
        (dag_tick.NodeClass.DEAD, True, 10.0, dag_tick.ActionKind.RESPAWN),
        (dag_tick.NodeClass.DEAD, False, 999_999.0, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.DEAD, False, None, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.DONE, True, 10.0, dag_tick.ActionKind.STOP),
        (dag_tick.NodeClass.DONE, False, 10.0, None),
        (dag_tick.NodeClass.WEDGED, True, 10.0, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.WEDGED, False, 10.0, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.ALIVE, True, 10.0, None),
        (dag_tick.NodeClass.ALIVE, False, 10.0, None),
        # #601 — LOG on every axis: live or dead pid, fresh, over-age, and
        # unknown age. Never RESPAWN.
        (dag_tick.NodeClass.NEEDS_HUMAN, False, 10.0, dag_tick.ActionKind.LOG),
        (dag_tick.NodeClass.NEEDS_HUMAN, True, 10.0, dag_tick.ActionKind.LOG),
        (
            dag_tick.NodeClass.NEEDS_HUMAN,
            False,
            999_999.0,
            dag_tick.ActionKind.LOG,
        ),
        (dag_tick.NodeClass.NEEDS_HUMAN, False, None, dag_tick.ActionKind.LOG),
    ],
)
def test_plan_maps_classification_to_actions(
    node_class: dag_tick.NodeClass,
    *,
    pid_alive: bool,
    state_age_s: float | None,
    expected_kind: dag_tick.ActionKind | None,
) -> None:
    node = dag_tick.ClassifiedNode(
        "abc123", node_class, pid_alive=pid_alive, state_age_s=state_age_s
    )
    actions = dag_tick.plan([node], max_age_s=100.0)
    if expected_kind is None:
        assert actions == []
    else:
        assert [action.kind for action in actions] == [expected_kind]
        assert actions[0].node_id == "abc123"


def test_plan_is_pure_and_order_preserving() -> None:
    nodes = [
        dag_tick.ClassifiedNode(
            "dead-1", dag_tick.NodeClass.DEAD, pid_alive=False, state_age_s=10.0
        ),
        dag_tick.ClassifiedNode(
            "alive-1", dag_tick.NodeClass.ALIVE, pid_alive=True, state_age_s=10.0
        ),
        dag_tick.ClassifiedNode(
            "done-1", dag_tick.NodeClass.DONE, pid_alive=True, state_age_s=10.0
        ),
    ]
    actions = dag_tick.plan(nodes, max_age_s=100.0)
    assert [a.node_id for a in actions] == ["dead-1", "done-1"]


def test_plan_over_age_dead_reason_names_the_age() -> None:
    node = dag_tick.ClassifiedNode(
        "abc123", dag_tick.NodeClass.DEAD, pid_alive=False, state_age_s=200_000.0
    )
    actions = dag_tick.plan([node], max_age_s=86400.0)
    assert actions[0].kind is dag_tick.ActionKind.LOG
    assert "stale beyond --max-age" in actions[0].reason
    assert "200000s" in actions[0].reason
    assert "not crash recovery" in actions[0].reason


def test_plan_needs_human_reason_names_the_label_and_the_no_respawn_rule() -> None:
    node = dag_tick.ClassifiedNode(
        "abc123", dag_tick.NodeClass.NEEDS_HUMAN, pid_alive=False, state_age_s=None
    )
    actions = dag_tick.plan([node], max_age_s=86400.0)
    assert actions[0].kind is dag_tick.ActionKind.LOG
    assert dag_tick.NEEDS_HUMAN_LABEL in actions[0].reason
    assert "not respawned BY THIS TICK" in actions[0].reason


# The exact operator-facing string `_needs_human_reason()` must emit — a
# GOLDEN literal, and the only assertion here that actually closes the hole
# three review rounds kept reopening.
#
# Rounds 1-3 each tried to express "this string is honest" as a set of
# substring conditions, and the reviewer defeated every version by adding a
# clause the conditions did not constrain. Its v3 diagnosis is the reason
# this is a golden and not a fourth attempt at a predicate: the check is
# *"an exact-template guard, not a semantic classifier"* — it cannot judge
# meaning, so tightening it is an unwinnable game against an adversary who
# can always append one more sentence. Equality ends that game: any wording
# change at all fails here and forces a human to re-read the claim, which is
# exactly the review that was wanted.
#
# This literal is an INDEPENDENT source of truth (`tests/AGENTS.md`: expected
# values come from a known-good literal), transcribed deliberately — not
# recomputed from the module, which would make it tautological.
_EXPECTED_NEEDS_HUMAN_REASON = (
    "escalated — state=blocked with a needs payload and no queued reply, so "
    "a human was asked a question a respawn cannot answer; not respawned BY "
    "THIS TICK at any age, re-checked immediately before spawn (a "
    "read-to-spawn window remains, irreducible without a lock the harness "
    "does not expose; and the harness's own supervisor is a separate route "
    "this module cannot close — #590); tracker projection to "
    "dag:needs-human is NOT done here — #602"
)


def _reason_is_honest(reason: str) -> bool:
    """Clause-level diagnostic: WHICH part of the reason regressed.

    ⚠️ **This is an exact-template guard, NOT a semantic classifier, and it
    is not what makes the wording safe** — :data:`_EXPECTED_NEEDS_HUMAN_REASON`
    is. Kept because equality alone reports "the string changed" and this
    reports which claim broke.

    Its limits are measured, not assumed. The #601 review defeated two
    successive versions (:data:`_DISHONEST_REASON_V2`,
    :data:`_DISHONEST_REASON_V3`) by adding clauses no substring condition
    constrained, and an *honest paraphrase* also returns False here. So it
    over-rejects and under-rejects at once; treat a True from it as "the
    named clauses are present", never as "the string is honest".

    Both clauses are matched CONTIGUOUSLY — bound to their subject, which is
    what killed the v2 counterexample — and the label must appear exactly
    once, so a correct clause cannot be paired with a contradicting second
    mention of it.
    """
    scoped_respawn = "not respawned BY THIS TICK"
    scoped_projection = (
        f"tracker projection to {dag_tick.NEEDS_HUMAN_LABEL} is NOT done here"
    )
    forbidden = (
        "never auto-respawned",
        f"project + label {dag_tick.NEEDS_HUMAN_LABEL}",
    )
    return (
        scoped_respawn in reason
        and scoped_projection in reason
        and reason.count(dag_tick.NEEDS_HUMAN_LABEL) == 1
        and not any(phrase in reason for phrase in forbidden)
    )


# The two counterexamples the #601 adversarial review constructed. Each
# defeated the version of `_reason_is_honest` that existed when it was
# written, so both are pinned as inputs the golden must reject.
#
# ⚠️ Their DEFECT is verbatim; their scoped-respawn clause was re-based when
# v5 changed that wording ("never" -> "not"). Without re-basing, each would
# be rejected for the wording mismatch instead of for the flaw it was built
# to demonstrate — a pinned counterexample that stops probing its own defect
# is exactly the silent false negative `tests/AGENTS.md` warns about.
#
# v2 broke the loose fragment `is NOT done here` by attaching it to an
# unrelated "cleanup" clause while asserting the projection DOES happen.
_DISHONEST_REASON_V2 = (
    "not respawned BY THIS TICK; tracker projection to dag:needs-human "
    "IS done here; cleanup is NOT done here"
)
# v3 defeated the CONTIGUOUS-clause fix that closed v2: it satisfies both
# required clauses, mentions the label exactly once, and carries neither
# forbidden phrase — then contradicts itself in a trailing sentence the
# predicate does not constrain at all. This one still passes
# `_reason_is_honest`, and that is the point: it is why the golden exists.
_DISHONEST_REASON_V3 = (
    "not respawned BY THIS TICK; tracker projection to dag:needs-human is "
    "NOT done here; it is performed later in this same tick"
)


def test_plan_needs_human_reason_claims_no_action_this_module_skips() -> None:
    """#601 adversarial review, both HIGH findings — pinned as regressions.

    The first draft said *"never auto-respawned at any age (project + label
    dag:needs-human)"*, which asserted two things the module does not do:
    a GLOBAL no-respawn guarantee (it binds this watchdog only — the
    harness's own supervisor reads state/tempo/queuedPrompt, never `needs`),
    and a projection that no code here performs (#602 owns it).

    A log line that names an action the code skips is how an operator
    concludes an escalation reached the tracker when it reached a launchd
    log.

    ⚠️ **The GOLDEN equality is the guard; the clause assertions are
    diagnostics.** Three rounds of review each defeated a substring-based
    version of this check by adding a clause it did not constrain — the last
    one (:data:`_DISHONEST_REASON_V3`) still satisfies
    :func:`_reason_is_honest` today. Substring conditions cannot judge
    meaning, so tightening them is unwinnable; equality ends it, because any
    wording change fails and forces a human to re-read the claim.
    """
    node = dag_tick.ClassifiedNode(
        "abc123", dag_tick.NodeClass.NEEDS_HUMAN, pid_alive=False, state_age_s=None
    )
    reason = dag_tick.plan([node], max_age_s=86400.0)[0].reason
    # The complete guard. Both counterexamples fail it, and so does any
    # future clause a predicate would not have thought to forbid.
    assert reason == _EXPECTED_NEEDS_HUMAN_REASON
    assert _DISHONEST_REASON_V2 != _EXPECTED_NEEDS_HUMAN_REASON
    assert _DISHONEST_REASON_V3 != _EXPECTED_NEEDS_HUMAN_REASON
    # Diagnostics: name WHICH claim regressed rather than only "it changed".
    assert _reason_is_honest(reason) is True
    assert _reason_is_honest(_DISHONEST_REASON_V2) is False
    assert "not respawned BY THIS TICK" in reason
    assert (
        f"tracker projection to {dag_tick.NEEDS_HUMAN_LABEL} is NOT done here" in reason
    )
    assert "never auto-respawned" not in reason
    assert f"project + label {dag_tick.NEEDS_HUMAN_LABEL}" not in reason


def test_reason_honesty_predicate_is_a_template_guard_not_a_classifier() -> None:
    """The predicate's measured limits, pinned so nobody over-trusts it.

    `_reason_is_honest` fails in BOTH directions, and both are recorded
    here rather than in prose alone: it ACCEPTS
    :data:`_DISHONEST_REASON_V3`, a string that satisfies every clause and
    then contradicts itself in a sentence the predicate does not constrain;
    and it REJECTS an honest paraphrase, because it matches a template
    rather than meaning.

    If a later change makes the predicate reject V3, this test fails —
    deliberately. That would be a real improvement, and it should be
    noticed and recorded, not absorbed silently.
    """
    honest_paraphrase = (
        "escalated — a human was asked something a respawn cannot answer; "
        "this tick will not respawn it, and nothing here writes to the "
        "tracker"
    )
    assert _reason_is_honest(_DISHONEST_REASON_V3) is True
    assert _reason_is_honest(honest_paraphrase) is False
    # …while the golden correctly rejects both, which is why it is the guard.
    assert _DISHONEST_REASON_V3 != _EXPECTED_NEEDS_HUMAN_REASON
    assert honest_paraphrase != _EXPECTED_NEEDS_HUMAN_REASON


def test_plan_never_respawns_a_needs_human_node_at_any_age() -> None:
    """The `--max-age` demotion, pinned.

    Before #601 the 24h bound was the only thing stopping the two live
    July escalations from being resurrected. A NEEDS_HUMAN node must now
    be LOG-only even when its state.json is FRESH — i.e. exactly where
    `--max-age` would have permitted a respawn.
    """
    fresh = dag_tick.ClassifiedNode(
        "fresh-escalation",
        dag_tick.NodeClass.NEEDS_HUMAN,
        pid_alive=False,
        state_age_s=1.0,
    )
    actions = dag_tick.plan([fresh], max_age_s=86400.0)
    assert [a.kind for a in actions] == [dag_tick.ActionKind.LOG]
    # The control: same age, same dead pid, but DEAD instead of
    # NEEDS_HUMAN -> RESPAWN. Proves the age is not what suppressed it.
    dead = dag_tick.ClassifiedNode(
        "fresh-dead", dag_tick.NodeClass.DEAD, pid_alive=False, state_age_s=1.0
    )
    assert [a.kind for a in dag_tick.plan([dead], max_age_s=86400.0)] == [
        dag_tick.ActionKind.RESPAWN
    ]


def test_plan_no_age_dead_reason_says_unknown_age() -> None:
    node = dag_tick.ClassifiedNode(
        "abc123", dag_tick.NodeClass.DEAD, pid_alive=False, state_age_s=None
    )
    actions = dag_tick.plan([node], max_age_s=86400.0)
    assert actions[0].kind is dag_tick.ActionKind.LOG
    assert "unknown age" in actions[0].reason


# ---------------------------------------------------------------------------
# try_acquire_lock() — lock contention (second flock fails)
# ---------------------------------------------------------------------------


def test_lock_contention_second_acquire_fails(tmp_path: Path) -> None:
    lock_path = tmp_path / "dag-tick.lock"
    first = dag_tick.try_acquire_lock(lock_path)
    assert first is not None
    try:
        second = dag_tick.try_acquire_lock(lock_path)
        assert second is None
    finally:
        first.close()


def test_lock_release_allows_reacquire(tmp_path: Path) -> None:
    lock_path = tmp_path / "dag-tick.lock"
    first = dag_tick.try_acquire_lock(lock_path)
    assert first is not None
    first.close()
    second = dag_tick.try_acquire_lock(lock_path)
    assert second is not None
    second.close()


def test_try_acquire_lock_does_not_truncate_existing_content(tmp_path: Path) -> None:
    """#578 respec round 2 lock-mode fix.

    Opening in "w" mode truncates on open, before flock is even attempted —
    a second process's `open("w")` would zero another holder's bytes out
    from under it. "a" does not truncate.
    """
    lock_path = tmp_path / "dag-tick.lock"
    lock_path.write_text("PREVIOUS-CONTENT")
    handle = dag_tick.try_acquire_lock(lock_path)
    assert handle is not None
    handle.close()
    assert lock_path.read_text() == "PREVIOUS-CONTENT"


# ---------------------------------------------------------------------------
# read_roster, pid_is_alive, and background_pid_alive — daemon liveness
# ---------------------------------------------------------------------------


def test_read_roster_missing_file_returns_none(tmp_path: Path) -> None:
    assert dag_tick.read_roster(tmp_path) is None


def test_read_roster_malformed_json_returns_none(tmp_path: Path) -> None:
    (tmp_path / "roster.json").write_text("{not json")
    assert dag_tick.read_roster(tmp_path) is None


def test_read_roster_non_dict_workers_returns_none(tmp_path: Path) -> None:
    (tmp_path / "roster.json").write_text(json.dumps({"workers": "nope"}))
    assert dag_tick.read_roster(tmp_path) is None


def test_read_roster_parses_workers_and_skips_bad_entries(tmp_path: Path) -> None:
    (tmp_path / "roster.json").write_text(
        json.dumps(
            {
                "proto": 1,
                "supervisorPid": 1,
                "workers": {
                    "abc123": {"pid": 999, "procStart": "Wed Jul 15 10:54:17 2026"},
                    "bad-entry": "not-a-dict",
                    "no-pid": {"procStart": "x"},
                },
            }
        )
    )
    roster = dag_tick.read_roster(tmp_path)
    assert roster == {
        "abc123": dag_tick.RosterWorker(pid=999, proc_start="Wed Jul 15 10:54:17 2026")
    }


def test_pid_is_alive_true_for_self() -> None:
    assert dag_tick.pid_is_alive(os.getpid()) is True


def test_pid_is_alive_false_for_a_dead_pid() -> None:
    assert dag_tick.pid_is_alive(999_999) is False


def test_background_pid_alive_none_roster_is_conservative_true() -> None:
    assert dag_tick.background_pid_alive("abc123", None) is True


def test_background_pid_alive_missing_entry_is_false() -> None:
    assert dag_tick.background_pid_alive("abc123", {}) is False


def test_background_pid_alive_defaults_to_real_pid_is_alive() -> None:
    alive_roster = {"abc123": dag_tick.RosterWorker(pid=os.getpid(), proc_start=None)}
    dead_roster = {"abc123": dag_tick.RosterWorker(pid=999_999, proc_start=None)}
    assert dag_tick.background_pid_alive("abc123", alive_roster) is True
    assert dag_tick.background_pid_alive("abc123", dead_roster) is False


def test_background_pid_alive_checks_the_injected_predicate() -> None:
    """#578 respec round 3: inject a fake predicate.

    Instead of monkeypatching `dag_tick.pid_is_alive`
    (`tests/AGENTS.md` § Mocking — never mock our own module; inject).
    """

    def _fake_is_alive(pid: int) -> bool:
        return pid == 111

    alive_roster = {"abc123": dag_tick.RosterWorker(pid=111, proc_start=None)}
    dead_roster = {"abc123": dag_tick.RosterWorker(pid=222, proc_start=None)}
    assert (
        dag_tick.background_pid_alive("abc123", alive_roster, is_alive=_fake_is_alive)
        is True
    )
    assert (
        dag_tick.background_pid_alive("abc123", dead_roster, is_alive=_fake_is_alive)
        is False
    )


# ---------------------------------------------------------------------------
# read_proc_start + the procStart identity check — #593 PID-reuse defense
# ---------------------------------------------------------------------------


def test_read_proc_start_reads_a_stable_value_for_a_live_process() -> None:
    """The reader answers for a live pid, and answers the SAME thing twice.

    Stability matters more than the literal value: the check compares a
    value recorded at spawn against one read a tick later, so a reader
    that drifted between two calls on one unchanging process would
    manufacture a mismatch — and a mismatch respawns.
    """
    first = dag_tick.read_proc_start(os.getpid())
    assert first is not None
    assert first == dag_tick.read_proc_start(os.getpid())


def test_read_proc_start_discriminates_between_two_processes() -> None:
    """The control arm: it must be able to return a DIFFERENT answer.

    `probes-need-a-control-arm.md` — a reader that returned one constant
    would make every identity check pass, and the whole #593 defense would
    be decoration. pid 1 booted before this test process did.
    """
    mine = dag_tick.read_proc_start(os.getpid())
    init = dag_tick.read_proc_start(1)
    assert mine is not None
    assert init is not None
    assert mine != init


def test_read_proc_start_is_none_for_a_dead_pid() -> None:
    assert dag_tick.read_proc_start(999_999) is None


def _elapsed_seconds(pid: int) -> float:
    """`ps -o etime=` -> seconds. An INDEPENDENT route to the same instant.

    `etime` is a duration, so it carries no timezone and no locale at all
    — which is exactly why it can adjudicate `lstart`'s. Formats:
    `MM:SS`, `HH:MM:SS`, `DD-HH:MM:SS`.
    """
    raw = subprocess.run(
        ["ps", "-o", "etime=", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    days, _, clock = raw.rpartition("-")
    parts = [float(p) for p in clock.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    hours, minutes, seconds = parts
    day_seconds = (float(days) if days else 0.0) * 86400.0
    return day_seconds + hours * 3600.0 + minutes * 60.0 + seconds


@pytest.mark.parametrize("pid", [os.getpid(), 1], ids=["self", "init"])
def test_read_proc_start_is_utc_not_this_host_local_time(pid: int) -> None:
    """The one axis nothing else can catch: the reader's `TZ`/`LC_ALL` env.

    Every other test here compares this reader against itself, so dropping
    `TZ=UTC` stays invisible — the roster's `procStart` is written by the
    CLI, not by us, and a self-consistent reader that is off by the host's
    UTC offset would mismatch EVERY real node while passing every
    self-authored fixture. That is the handoff's "gate against an artifact
    you did not author", restated as a property: the value must denote the
    process's real start instant, read as UTC.

    `ps -o etime=` is the independent adjudicator — a duration, so no
    timezone is involved in producing it. On a host whose local zone IS
    UTC (a CI runner, typically) the two readings coincide and this test
    is satisfied vacuously; that is honest, because there the defect it
    guards against has no observable effect. It discriminates wherever it
    can: on a UTC-5 host, dropping `TZ=UTC` moves the parsed value 5 hours
    off, far outside the tolerance below.
    """
    value = dag_tick.read_proc_start(pid)
    assert value is not None
    parsed = datetime.strptime(value, "%a %b %d %H:%M:%S %Y").replace(tzinfo=UTC)
    expected = datetime.now(UTC) - timedelta(seconds=_elapsed_seconds(pid))
    assert abs((parsed - expected).total_seconds()) < 90.0


def test_background_pid_alive_no_recorded_proc_start_defers_to_pid() -> None:
    """An entry with no `procStart` must not be reaped for lacking one.

    Mirrors `isSameProcessAsync(pid, undefined) -> true`. The reader is a
    tripwire: reaching it at all would mean the absent-record branch fell
    through to a comparison it has nothing to compare against.
    """

    def _never(pid: int) -> str | None:
        msg = f"read the start time for {pid} with nothing recorded"
        raise AssertionError(msg)

    roster = {"abc123": dag_tick.RosterWorker(pid=111, proc_start=None)}
    assert (
        dag_tick.background_pid_alive(
            "abc123", roster, is_alive=lambda _pid: True, proc_start=_never
        )
        is True
    )


def test_background_pid_alive_dead_pid_never_reads_the_start_time() -> None:
    """A dead pid short-circuits; identity is only asked of a LIVE pid."""

    def _never(pid: int) -> str | None:
        msg = f"read the start time for dead pid {pid}"
        raise AssertionError(msg)

    roster = {
        "abc123": dag_tick.RosterWorker(pid=111, proc_start="Wed Jul 15 10:54:17 2026")
    }
    assert (
        dag_tick.background_pid_alive(
            "abc123", roster, is_alive=lambda _pid: False, proc_start=_never
        )
        is False
    )


def test_background_pid_alive_matching_proc_start_is_alive() -> None:
    roster = {
        "abc123": dag_tick.RosterWorker(pid=111, proc_start="Wed Jul 15 10:54:17 2026")
    }
    assert (
        dag_tick.background_pid_alive(
            "abc123",
            roster,
            is_alive=lambda _pid: True,
            proc_start=lambda _pid: "Wed Jul 15 10:54:17 2026",
        )
        is True
    )


def test_background_pid_alive_differing_proc_start_is_dead() -> None:
    """The #593 defect, pinned: a recycled pid is live but is NOT our node.

    This is the only branch that ADDS a negative, and it is the whole
    point of the ticket — before it, this case returned True and the node
    was never respawned.
    """
    roster = {
        "abc123": dag_tick.RosterWorker(pid=111, proc_start="Wed Jul 15 10:54:17 2026")
    }
    assert (
        dag_tick.background_pid_alive(
            "abc123",
            roster,
            is_alive=lambda _pid: True,
            proc_start=lambda _pid: "Fri Aug  7 19:12:08 2026",
        )
        is False
    )


def test_background_pid_alive_unreadable_proc_start_is_alive() -> None:
    """An unanswered `ps` is NOT a mismatch — it must never respawn.

    Mirrors the harness comparator's `actual === undefined || actual ===
    recorded`. A `ps` that timed out or was missing carries no evidence
    either way, and the DEAD branch of this predicate takes an action.
    """
    roster = {
        "abc123": dag_tick.RosterWorker(pid=111, proc_start="Wed Jul 15 10:54:17 2026")
    }
    assert (
        dag_tick.background_pid_alive(
            "abc123",
            roster,
            is_alive=lambda _pid: True,
            proc_start=lambda _pid: None,
        )
        is True
    )


def test_background_pid_alive_blank_proc_start_is_alive() -> None:
    """A blank reading is UNANSWERED, not a mismatch.

    The dangerous cell next door to the one above: `"" == recorded` is
    False for every real recorded value, so treating a blank as a reading
    fails toward the respawn — the exact direction #593 must never fail
    in. `read_proc_start` already normalizes it, and the predicate
    re-tests it so an alternate reader cannot reintroduce the hazard.
    """
    roster = {
        "abc123": dag_tick.RosterWorker(pid=111, proc_start="Wed Jul 15 10:54:17 2026")
    }
    assert (
        dag_tick.background_pid_alive(
            "abc123", roster, is_alive=lambda _pid: True, proc_start=lambda _pid: ""
        )
        is True
    )


def test_background_pid_alive_live_arm_recycled_pid_reads_dead() -> None:
    """End-to-end on the REAL defaults — no seams, no fixtures.

    pid 1 is the honest stand-in for a recycled pid: it is alive, it is
    not ours, and on this host `os.kill(1, 0)` raises `PermissionError`,
    which :func:`pid_is_alive` deliberately reads as ALIVE. So the pid
    check alone CANNOT reject it — only the identity read can, and `ps`
    answers for another user's process where `kill` is blind. That is the
    `PermissionError`-reads-alive half of #593, resolved by identity
    rather than by loosening the liveness rule.
    """
    stale = {
        "abc123": dag_tick.RosterWorker(pid=1, proc_start="Thu Jan  1 00:00:00 1970")
    }
    assert dag_tick.pid_is_alive(1) is True
    assert dag_tick.background_pid_alive("abc123", stale) is False


def test_background_pid_alive_live_arm_own_process_reads_alive() -> None:
    """The passing arm of the same live probe: a real, matching identity."""
    recorded = dag_tick.read_proc_start(os.getpid())
    assert recorded is not None, "ps did not answer — the arm below would be vacuous"
    roster = {"abc123": dag_tick.RosterWorker(pid=os.getpid(), proc_start=recorded)}
    assert dag_tick.background_pid_alive("abc123", roster) is True


# ---------------------------------------------------------------------------
# load_state_json — reading one job's state.json off disk
# ---------------------------------------------------------------------------


def test_load_state_json_missing_returns_none_none(tmp_path: Path) -> None:
    data, mtime = dag_tick.load_state_json(tmp_path, "nope")
    assert data is None
    assert mtime is None


def test_load_state_json_malformed_returns_none_none(tmp_path: Path) -> None:
    job_dir = tmp_path / "abc123"
    job_dir.mkdir()
    (job_dir / "state.json").write_text("{not json")
    data, mtime = dag_tick.load_state_json(tmp_path, "abc123")
    assert data is None
    assert mtime is None


def test_load_state_json_non_dict_returns_none_none(tmp_path: Path) -> None:
    job_dir = tmp_path / "abc123"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps(["not", "a", "dict"]))
    data, mtime = dag_tick.load_state_json(tmp_path, "abc123")
    assert data is None
    assert mtime is None


def test_load_state_json_parses_and_returns_mtime(tmp_path: Path) -> None:
    job_dir = tmp_path / "abc123"
    job_dir.mkdir()
    state_path = job_dir / "state.json"
    state_path.write_text(json.dumps({"state": "blocked", "tempo": "idle"}))
    data, mtime = dag_tick.load_state_json(tmp_path, "abc123")
    assert data == {"state": "blocked", "tempo": "idle"}
    assert mtime == pytest.approx(state_path.stat().st_mtime)


# ---------------------------------------------------------------------------
# classify_background_rows — census enrichment + classification, end to end
# ---------------------------------------------------------------------------


def test_classify_background_rows_missing_state_json_is_conservative_alive(
    tmp_path: Path,
) -> None:
    ctx = _ctx(tmp_path, verbose=True)
    rows: list[dict[str, object]] = [{"id": "ghost", "kind": "background"}]
    result = dag_tick.classify_background_rows(rows, ctx)
    assert result.classified == [
        dag_tick.ClassifiedNode(
            "ghost", dag_tick.NodeClass.ALIVE, pid_alive=True, state_age_s=None
        )
    ]
    assert any("missing/unparseable" in note for note in result.notes)


def test_classify_background_rows_dead_when_no_roster_entry(tmp_path: Path) -> None:
    daemon_dir = _roster(tmp_path, {})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.DEAD
    # A FRESH DEAD node produces no note by itself (not stale, not
    # --verbose) — the stale-DEAD note is covered by its own test below.
    assert result.notes == []


def test_classify_background_rows_missing_roster_file_is_conservative_alive(
    tmp_path: Path,
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir()  # exists, but no roster.json inside it
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.ALIVE


def test_classify_background_rows_skips_row_with_no_usable_id(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    result = dag_tick.classify_background_rows([{"kind": "background"}], ctx)
    assert result.classified == []
    assert result.notes  # anomaly note recorded regardless of --verbose


def test_classify_background_rows_wedged_note_always_prints(tmp_path: Path) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "active"})
    state_path = jobs_dir / "abc123" / "state.json"
    stale = state_path.stat().st_mtime - 300
    os.utime(state_path, (stale, stale))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.WEDGED
    assert any("WEDGED abc123" in note for note in result.notes)


def test_classify_background_rows_stale_dead_note_always_prints(
    tmp_path: Path,
) -> None:
    """#578 respec round 3 (--max-age): an over-age DEAD node's note.

    It is unconditional (mirroring WEDGED's), so an operator sees WHY it
    was not respawned even without --verbose.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    state_path = jobs_dir / "abc123" / "state.json"
    ancient = state_path.stat().st_mtime - 100_000  # ~27.8h — over the 24h default
    os.utime(state_path, (ancient, ancient))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.DEAD
    assert any(
        "stale beyond --max-age" in note and "abc123" in note for note in result.notes
    )


def test_classify_background_rows_reads_the_live_needs_shape(
    tmp_path: Path,
) -> None:
    """#601: the real `state.json` shape, verbatim off this host.

    Both stale census nodes are `state=blocked` / `tempo=blocked` with a
    string `needs`; only one carries `suggestedReply`. Fixtures mirror
    that rather than an invented shape, so a wrong field name or a wrong
    `tempo` assumption cannot pass here.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})  # readable, names nobody -> pid dead
    _write_state(
        jobs_dir,
        "ad8baf35",
        {"state": "blocked", "tempo": "blocked", "needs": _LIVE_NEEDS_JULY_13},
    )
    _write_state(
        jobs_dir,
        "fdfdaf90",
        {
            "state": "blocked",
            "tempo": "blocked",
            "needs": _LIVE_NEEDS_JULY_22,
            "suggestedReply": "do the full command catalog extraction pass",
        },
    )
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [
            {"id": "ad8baf35", "kind": "background"},
            {"id": "fdfdaf90", "kind": "background"},
        ],
        ctx,
    )
    assert [c.node_class for c in result.classified] == [
        dag_tick.NodeClass.NEEDS_HUMAN,
        dag_tick.NodeClass.NEEDS_HUMAN,
    ]


def test_classify_background_rows_reply_queued_note_always_prints(
    tmp_path: Path,
) -> None:
    """#601 v6 HIGH: unconditional, because SILENCE was the defect.

    Before this class the same node produced no note at all on a
    non-verbose tick, so a human's undelivered answer was invisible. A
    `--verbose`-gated note would not have fixed it — the launchd tick does
    not run verbose.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})  # LIVE pid
    _write_state(
        jobs_dir,
        "abc123",
        {
            "state": "blocked",
            "tempo": "blocked",
            "needs": _LIVE_NEEDS_JULY_22,
            "queuedPrompt": "do the full command catalog extraction pass",
        },
    )
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)  # verbose=False
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.REPLY_QUEUED
    assert any(
        "REPLY_QUEUED abc123" in note and _LIVE_NEEDS_JULY_22 in note
        for note in result.notes
    )
    # Control: it must NOT be reported as the escalation it is not — the
    # human already answered, and saying otherwise sends them to re-answer.
    assert not any("NEEDS_HUMAN abc123" in note for note in result.notes)


def test_classify_background_rows_needs_human_note_quotes_the_question(
    tmp_path: Path,
) -> None:
    """Unconditional (not --verbose), and it carries the actual question.

    An escalation note whose text an operator cannot act on is the same
    silent loss as the respawn — so the payload is in the line, not just
    the node id.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(
        jobs_dir,
        "abc123",
        {"state": "blocked", "tempo": "blocked", "needs": _LIVE_NEEDS_JULY_22},
    )
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.NEEDS_HUMAN
    assert any(
        "NEEDS_HUMAN abc123" in note
        and _LIVE_NEEDS_JULY_22 in note
        and dag_tick.NEEDS_HUMAN_LABEL in note
        for note in result.notes
    )
    # Control: it must NOT be reported as the stale-DEAD case it used to be.
    assert not any("stale beyond --max-age" in note for note in result.notes)


def test_classify_background_rows_escalated_and_stalled_keeps_both_facts(
    tmp_path: Path,
) -> None:
    """NEEDS_HUMAN out-ranks WEDGED, so the stall must ride in its note.

    A `tempo:"active"`, stale, escalated node is BOTH things. One class
    cannot say two, and NEEDS_HUMAN is the one to keep — but dropping the
    stall entirely would cost #579/#590 the visibility they need for this
    shape, so it is appended instead.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})  # live pid
    _write_state(
        jobs_dir,
        "abc123",
        {"state": "blocked", "tempo": "active", "needs": _LIVE_NEEDS_JULY_13},
    )
    state_path = jobs_dir / "abc123" / "state.json"
    stale = state_path.stat().st_mtime - 300
    os.utime(state_path, (stale, stale))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.NEEDS_HUMAN
    assert any(
        "NEEDS_HUMAN abc123" in note and "ALSO stalled" in note for note in result.notes
    )


def test_classify_background_rows_escalated_not_stalled_omits_the_clause(
    tmp_path: Path,
) -> None:
    """The control arm: the stall clause must not print unconditionally.

    Same escalated node, same live pid, but a FRESH state.json — so the
    added clause is proven to discriminate rather than always fire.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    _write_state(
        jobs_dir,
        "abc123",
        {"state": "blocked", "tempo": "active", "needs": _LIVE_NEEDS_JULY_13},
    )
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.NEEDS_HUMAN
    assert any("NEEDS_HUMAN abc123" in note for note in result.notes)
    assert not any("ALSO stalled" in note for note in result.notes)


# ---------------------------------------------------------------------------
# The crashed-mid-activity case, driven through the real chain (round 3)
# ---------------------------------------------------------------------------


def test_crashed_mid_activity_flows_through_to_respawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The watchdog's primary recovery case.

    #578 respec round 1, reworked round 3 per the cold review's
    inert-fixture finding (probes rule 8). Drives the crash SHAPE through
    the real chain — classify_background_rows -> plan -> execute_respawn —
    instead of writing a state.json that `execute_respawn` cannot read (it
    hasn't since round 1). A process
    crashes while its last-written state.json still reads `tempo:"active"`
    with in-flight work; the roster is readable and names no worker for
    this node (real negative pid evidence). The control-arm test right
    below proves this SAME fixture shape produces a DIFFERENT result when
    the pid IS live.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert len(result.classified) == 1
    classified = result.classified[0]
    assert classified.node_class is dag_tick.NodeClass.DEAD
    assert classified.state_age_s is not None
    assert classified.state_age_s < ctx.max_age_s  # fresh crash, not stale

    actions = dag_tick.plan(result.classified, max_age_s=ctx.max_age_s)
    assert [a.kind for a in actions] == [dag_tick.ActionKind.RESPAWN]

    calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)
    line = dag_tick.execute_respawn(actions[0].node_id, ctx)
    assert calls == [["claude", "respawn", "abc123"]]
    assert "RESPAWN abc123" in line


def test_crashed_mid_activity_control_arm_live_pid_is_alive(tmp_path: Path) -> None:
    """Control arm for the test above.

    Probes rule 8: the fixture must be able to produce the OTHER result.
    Same `tempo:"active"` + in-flight state.json shape, but the roster now
    names a live pid — the node must classify ALIVE, not DEAD, proving the
    fixture actually discriminates.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    _write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.ALIVE


def test_recycled_pid_classifies_dead_and_plans_a_respawn(tmp_path: Path) -> None:
    """#593 end-to-end: a LIVE pid with the WRONG identity is not our node.

    The fixture is deliberately the hostile one — the roster names a pid
    that really is running (this test process), so `kill(pid, 0)` says
    ALIVE and nothing about liveness can reject it. Only the recorded
    `procStart` disagrees. Before #593 this classified ALIVE and the
    crashed node was never respawned; the control arm below is the same
    fixture with the identity that MATCHES.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(
        tmp_path,
        {"abc123": os.getpid()},
        {"abc123": "Wed Jul 15 10:54:17 2026"},
    )
    _write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.DEAD
    assert result.classified[0].pid_alive is False
    actions = dag_tick.plan(result.classified, max_age_s=ctx.max_age_s)
    assert [a.kind for a in actions] == [dag_tick.ActionKind.RESPAWN]


def test_recycled_pid_control_arm_matching_proc_start_is_alive(tmp_path: Path) -> None:
    """Control arm: same fixture, the identity the process really has.

    Uses the REAL reader on both sides, so a defect in `read_proc_start`
    itself (a drifting or constant value) shows up here rather than being
    hidden behind an injected literal.
    """
    recorded = dag_tick.read_proc_start(os.getpid())
    assert recorded is not None, "ps did not answer — this arm would be vacuous"
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()}, {"abc123": recorded})
    _write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    result = dag_tick.classify_background_rows(
        [{"id": "abc123", "kind": "background"}], ctx
    )
    assert result.classified[0].node_class is dag_tick.NodeClass.ALIVE


def test_execute_respawn_reconciles_on_a_recycled_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The execution-time re-check sees identity too, not just liveness.

    `execute_respawn`'s "pid is alive now (reconciled)" guard exists to
    stop a double-start. It must not be fooled by the same recycled pid
    the classifier already rejected — otherwise every #593 recovery would
    be planned and then silently skipped.

    ⚠️ The identity read is INJECTED here, not left to the default.
    `monkeypatch.setattr(dag_tick.subprocess, "Popen", ...)` patches the
    stdlib module itself, and `subprocess.run` is built on `Popen` — so a
    real :func:`read_proc_start` inside a Popen-patched test dies on the
    fake. Injecting the seam is what `tests/AGENTS.md` asks for anyway.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(
        tmp_path,
        {"abc123": os.getpid()},
        {"abc123": "Wed Jul 15 10:54:17 2026"},
    )
    _write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)
    line = dag_tick.execute_respawn(
        "abc123", ctx, proc_start=lambda _pid: "Fri Aug  7 19:12:08 2026"
    )
    assert calls == [["claude", "respawn", "abc123"]]
    assert "RESPAWN abc123" in line


# ---------------------------------------------------------------------------
# gate_preflight() / read_census() — missing binary + distinct failure logs
# ---------------------------------------------------------------------------


def test_gate_preflight_missing_binary_returns_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "run", _raise_missing)
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.gate_preflight(ctx)
    assert result == "unknown"
    assert any("gate preflight" in record.getMessage() for record in caplog.records)


def test_read_census_missing_binary_returns_empty_and_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "run", _raise_missing)
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    assert any(
        "unavailable for census" in record.getMessage() for record in caplog.records
    )


def test_read_census_nonzero_rc_logs_rc_and_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=17, stderr="permission denied"),
    )
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "rc=17" in message and "permission denied" in message for message in messages
    )


def test_read_census_invalid_json_logs_distinct_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0, stdout="{not json"),
    )
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    assert any("not valid JSON" in record.getMessage() for record in caplog.records)


def test_read_census_non_list_top_level_logs_distinct_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0, stdout=json.dumps({"a": 1})),
    )
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    assert any("not a list" in record.getMessage() for record in caplog.records)


def test_read_census_healthy_empty_fleet_is_silent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Control arm for the four failure-log tests above.

    A genuinely empty fleet (rc=0, a real empty JSON array) must produce
    ZERO warnings — this is exactly the case the fix must not turn noisy.
    """
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0, stdout="[]"),
    )
    ctx = _ctx(tmp_path)
    with caplog.at_level("WARNING"):
        result = dag_tick.read_census(ctx)
    assert result == []
    assert caplog.records == []


# ---------------------------------------------------------------------------
# execute_respawn() / execute_stop() — monkeypatched subprocess only
# ---------------------------------------------------------------------------


def test_execute_respawn_spawns_when_no_evidence_of_life(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {})
    jobs_dir = tmp_path / "jobs"
    # A node classified DEAD necessarily HAS a readable state.json — a
    # missing one classifies conservative-ALIVE and never reaches here. The
    # fixture said otherwise until #601 v4 made `execute_respawn` re-read it.
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)
    line = dag_tick.execute_respawn("abc123", ctx)
    assert calls == [["claude", "respawn", "abc123"]]
    assert "RESPAWN abc123" in line


def test_execute_respawn_skips_when_pid_alive_now(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    jobs_dir = tmp_path / "jobs"
    # ⚠️ The state.json is REQUIRED for this test to test anything. Without
    # it the call now exits through the unreadable-state SKIP, so the test
    # passed even with the pid guard deleted — the #601 v5 review caught
    # that the escalation re-check had silently disarmed this arm. A SKIP
    # assertion that does not say WHICH skip is satisfied by any of them.
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "must not spawn when the fresh re-check finds the pid alive"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail)
    line = dag_tick.execute_respawn("abc123", ctx)
    assert "SKIP respawn abc123" in line
    assert "pid is alive now (reconciled)" in line


def test_execute_respawn_skips_a_node_that_escalated_since_classification(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """#601 v4 adversarial review, HIGH — the classify->execute race.

    `plan()` making NEEDS_HUMAN log-only protects a node only if the
    CLASSIFICATION saw the escalation. Actions execute from that snapshot,
    and `execute_respawn` used to re-read only the roster — so a node
    planned DEAD -> RESPAWN that acquired `state=blocked` + `needs` in
    between was respawned anyway, which is exactly the loss #601 exists to
    prevent. Reproduced here the way the reviewer demonstrated it: plan
    from a non-escalated snapshot, then mutate `state.json` before
    executing.

    The window is real because a roster read is not instantaneous truth: a
    node absent from the roster counts as dead by this module's own
    negative-evidence rule while its process may still be running, and a
    running node is exactly what can write `needs`.
    """
    daemon_dir = _roster(tmp_path, {})  # readable, names nobody -> pid dead
    jobs_dir = tmp_path / "jobs"
    # The snapshot `plan()` saw: blocked, no needs -> DEAD -> RESPAWN.
    _write_state(jobs_dir, "race1", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    snapshot = dag_tick.classify_background_rows(
        [{"id": "race1", "kind": "background"}], ctx
    )
    assert snapshot.classified[0].node_class is dag_tick.NodeClass.DEAD
    assert [a.kind for a in dag_tick.plan(snapshot.classified, max_age_s=86400.0)] == [
        dag_tick.ActionKind.RESPAWN
    ]

    # …and then the node escalates, before the planned action executes.
    _write_state(
        jobs_dir,
        "race1",
        {"state": "blocked", "tempo": "blocked", "needs": _LIVE_NEEDS_JULY_13},
    )

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "a node that escalated since classification must not be respawned"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)
    line = dag_tick.execute_respawn("race1", ctx)
    assert "SKIP respawn race1" in line
    assert "escalated since classification" in line
    assert _LIVE_NEEDS_JULY_13 in line


def test_execute_respawn_still_spawns_when_the_node_did_not_escalate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The control arm for the race fix: same shape, no escalation.

    Identical to the test above through the plan step, but `state.json` is
    rewritten WITHOUT a `needs` key. The respawn must still fire — a fix
    that skipped on any re-read, or on any `blocked` state, would silently
    retire the watchdog's primary recovery path and still pass the arm
    above.
    """
    daemon_dir = _roster(tmp_path, {})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "race1", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    _write_state(jobs_dir, "race1", {"state": "blocked", "tempo": "blocked"})
    calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)
    line = dag_tick.execute_respawn("race1", ctx)
    assert calls == [["claude", "respawn", "race1"]]
    assert "RESPAWN race1" in line


def test_execute_respawn_skips_when_state_json_vanished_before_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An unreadable `state.json` at execution SKIPs — cannot prove safety.

    A node classified DEAD had a readable one (a missing file classifies
    conservative-ALIVE and never reaches here), so its disappearance is
    anomalous. The same "never resurrect what cannot be proven" rule that
    governs `_is_stale_dead`'s unknown age applies: skip, and let the next
    tick reconcile.
    """
    daemon_dir = _roster(tmp_path, {})
    ctx = _ctx(tmp_path, jobs_dir=tmp_path / "jobs", daemon_dir=daemon_dir)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "must not respawn a node whose state cannot be read"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)
    line = dag_tick.execute_respawn("ghost", ctx)
    assert "SKIP respawn ghost" in line
    assert "state.json unreadable at execution" in line


def test_execute_respawn_missing_binary_returns_skip_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "abc123", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _raise_missing)
    line = dag_tick.execute_respawn("abc123", ctx)
    assert "SKIP respawn abc123" in line
    assert "claude binary unavailable" in line


# A `state.json` that really is terminal under `is_terminal`: a settled
# state, an idle tempo, and no queued reply. Every `execute_stop` test that
# is NOT about the terminal re-check has to write one — since #604 the call
# exits through the unreadable-state SKIP without it, which is the same
# silent disarming the #601 v5 review caught on the respawn side (a SKIP
# assertion that does not say WHICH skip is satisfied by any of them).
_TERMINAL_STATE: dict[str, object] = {"state": "done", "tempo": "idle"}


def test_execute_stop_reports_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "abc123", _TERMINAL_STATE)
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=0),
    )
    line = dag_tick.execute_stop("abc123", ctx)
    assert line == "dag-tick: STOP abc123 (rc=0)"


def test_execute_stop_reports_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "abc123", _TERMINAL_STATE)
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    monkeypatch.setattr(
        dag_tick.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(returncode=1, stderr="boom"),
    )
    line = dag_tick.execute_stop("abc123", ctx)
    assert "FAILED rc=1" in line
    assert "boom" in line


def test_execute_stop_skips_when_pid_already_settled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Stop-side TOCTOU fix (#578 respec round 2).

    Classification can be up to one tick (60s) stale. If the node's pid is
    already gone by the time `execute_stop` runs (settled on its own, or
    reaped by something else), it must SKIP rather than issue a stop against
    a process that no longer exists — which would otherwise log a false
    FAILED line.

    ⚠️ The terminal `state.json` is REQUIRED for this test to test anything.
    Without it #604's re-check exits through the unreadable-state SKIP
    first, and the pid guard could be deleted with this test still green.
    """
    daemon_dir = _roster(tmp_path, {})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "abc123", _TERMINAL_STATE)
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "must not issue a stop once the pid has already settled"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fail)
    line = dag_tick.execute_stop("abc123", ctx)
    assert "SKIP stop abc123" in line
    assert "settled since classification" in line


def test_execute_stop_missing_binary_returns_skip_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "abc123", _TERMINAL_STATE)
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "run", _raise_missing)
    line = dag_tick.execute_stop("abc123", ctx)
    assert "SKIP stop abc123" in line
    assert "claude binary unavailable" in line


@pytest.mark.parametrize(
    ("label", "fresh_state"),
    [
        # tempo — a delivered human reply flips the ledger active.
        ("resumed_active", {"state": "done", "tempo": "active"}),
        # queuedPrompt — a reply whose delivery FAILED is persisted instead,
        # leaving the state settled. `is_terminal` denies this too, and it is
        # the route a `state`/`tempo`-only re-check would miss.
        (
            "reply_queued",
            {"state": "done", "tempo": "idle", "queuedPrompt": "go on then"},
        ),
        # state — the node left the terminal set entirely.
        ("left_terminal", {"state": "blocked", "tempo": "idle"}),
    ],
)
def test_execute_stop_skips_a_node_that_left_terminal_since_classification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    label: str,
    fresh_state: dict[str, object],
) -> None:
    """#604 — the stop-side mirror of #601 v4's classify->execute race.

    `plan()` maps DONE + live pid to STOP from the CLASSIFICATION snapshot,
    and `execute_stop` used to re-read only the roster — so a node that
    stopped being terminal in the window was stopped anyway. `claude stop`
    is live-proven to stop mid-activity (`docs/receipts/565.md`), so that
    path could terminate work a human had just resumed and persist
    `stopped` over it.

    Driven through the REAL chain (classify -> plan -> execute) so the
    snapshot the race needs is produced by the module rather than asserted,
    then `state.json` is mutated before executing — the shape the #601 v5
    reviewer used to demonstrate it.

    One arm per axis `is_terminal` reads (`state`, `tempo`,
    `queued_prompt`), because a fix that re-read only one of the three
    would still pass the other two arms.
    """
    daemon_dir = _roster(tmp_path, {"done1": os.getpid()})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "done1", _TERMINAL_STATE)
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    snapshot = dag_tick.classify_background_rows(
        [{"id": "done1", "kind": "background"}], ctx
    )
    assert snapshot.classified[0].node_class is dag_tick.NodeClass.DONE
    assert [a.kind for a in dag_tick.plan(snapshot.classified, max_age_s=86400.0)] == [
        dag_tick.ActionKind.STOP
    ]

    # …and then a human resumes it, before the planned action executes.
    _write_state(jobs_dir, "done1", fresh_state)

    def _fail_run(*_args: object, **_kwargs: object) -> None:
        msg = f"a node that left terminal ({label}) must not be stopped"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fail_run)
    line = dag_tick.execute_stop("done1", ctx)
    assert "SKIP stop done1" in line
    assert "no longer terminal since classification" in line


def test_execute_stop_still_stops_a_node_that_is_still_terminal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The control arm for #604: same chain, the node stays terminal.

    Identical to the test above through the plan step, but `state.json` is
    rewritten to another genuinely terminal shape. The stop must still
    fire — a "fix" that skipped on any re-read, or on any rewrite of the
    file, would retire the watchdog's lingering-process reaper and still
    pass every arm above.
    """
    daemon_dir = _roster(tmp_path, {"done1": os.getpid()})
    jobs_dir = tmp_path / "jobs"
    _write_state(jobs_dir, "done1", _TERMINAL_STATE)
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    snapshot = dag_tick.classify_background_rows(
        [{"id": "done1", "kind": "background"}], ctx
    )
    assert [a.kind for a in dag_tick.plan(snapshot.classified, max_age_s=86400.0)] == [
        dag_tick.ActionKind.STOP
    ]
    _write_state(jobs_dir, "done1", {"state": "stopped", "tempo": "idle"})
    calls: list[list[str]] = []

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        calls.append(argv)
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    line = dag_tick.execute_stop("done1", ctx)
    assert calls == [["claude", "stop", "done1"]]
    assert line == "dag-tick: STOP done1 (rc=0)"


def test_execute_stop_skips_when_state_json_vanished_before_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An unreadable `state.json` at execution SKIPs — cannot prove safety.

    The same ruling `execute_respawn` carries, deliberately one rule across
    both actions: a node classified DONE necessarily HAD a readable one, so
    its disappearance is anomalous and nothing here can prove the node is
    still terminal.

    The consequence is asserted, not just documented: the line must tell an
    operator this is NOT retried. A node with a persistently unreadable
    `state.json` classifies conservative-ALIVE next tick, which plans no
    action at all, so `execute_stop` is never reached for it again and the
    process lingers silently.
    """
    daemon_dir = _roster(tmp_path, {"ghost": os.getpid()})
    ctx = _ctx(tmp_path, jobs_dir=tmp_path / "jobs", daemon_dir=daemon_dir)

    def _fail_run(*_args: object, **_kwargs: object) -> None:
        msg = "must not stop a node whose state cannot be read"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fail_run)
    line = dag_tick.execute_stop("ghost", ctx)
    assert "SKIP stop ghost" in line
    assert "state.json unreadable at execution" in line
    assert "not retried" in line


_EXPECTED_STOP_REASON = (
    "terminal state but the process is still running; re-checked "
    "immediately before the stop (a read-to-stop window remains, "
    "irreducible without a lock the harness does not expose)"
)


def test_plan_stop_reason_states_the_recheck_and_its_residual() -> None:
    """The STOP reason must claim the re-check WITHOUT claiming safety.

    The same honesty guard `_needs_human_reason` carries, applied to the
    reason #604 rewrote. It used to be the bare "terminal state but the
    process is still running", which reported the classification snapshot
    as if it were the fact at stop time — and that gap IS #604.

    `execute_stop` now re-applies `is_terminal` immediately before the
    stop, but check-then-act against a file another process may write stays
    racy without a lock the harness does not expose, so the operator-facing
    reason has to state both halves. Pinned as a golden equality, for the
    reason the needs-human golden exists: substring conditions cannot judge
    meaning, and the failure mode here is a later edit quietly upgrading
    "narrowed" to "eliminated".
    """
    node = dag_tick.ClassifiedNode(
        "done1", dag_tick.NodeClass.DONE, pid_alive=True, state_age_s=1.0
    )
    reason = dag_tick.plan([node], max_age_s=86400.0)[0].reason
    assert reason == _EXPECTED_STOP_REASON
    # Diagnostics: name WHICH claim regressed rather than only "it changed".
    assert "re-checked immediately before the stop" in reason
    assert "a read-to-stop window remains" in reason


# ---------------------------------------------------------------------------
# build_tick_context() — the args+defaults -> TickContext mapping
# ---------------------------------------------------------------------------


def test_build_tick_context_maps_args_and_module_defaults() -> None:
    args = _tick_args(
        claude_bin="/x/claude",
        cwd="/some/repo",
        stall_after=5.0,
        max_age=10.0,
        dry_run=True,
        verbose=True,
    )
    ctx = dag_tick.build_tick_context(args)
    assert ctx.claude_bin == "/x/claude"
    assert ctx.cwd == "/some/repo"
    assert ctx.jobs_dir == dag_tick.JOBS_DIR
    assert ctx.daemon_dir == dag_tick.DAEMON_DIR
    assert ctx.lock_path == dag_tick.LOCK_PATH
    assert ctx.stall_after_s == 5.0
    assert ctx.max_age_s == 10.0
    assert ctx.dry_run is True
    assert ctx.verbose is True


def test_build_tick_context_defaults_claude_bin_and_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dag_tick.shutil, "which", lambda _name: None)
    args = _tick_args(claude_bin=None, cwd=None)
    ctx = dag_tick.build_tick_context(args)
    assert ctx.claude_bin == dag_tick.DEFAULT_CLAUDE_BIN
    assert ctx.cwd == str(Path.cwd())


# ---------------------------------------------------------------------------
# execute_tick() — full wiring, subprocess monkeypatched throughout
#
# #578 respec round 3: exercises `execute_tick` directly against a
# `tmp_path`-scoped `TickContext` — zero monkeypatching of `LOCK_PATH`/
# `JOBS_DIR`/`DAEMON_DIR` on this module. `run_tick`'s own args->context
# wiring is covered separately by the `build_tick_context` tests above;
# the CLI's end-to-end truth is the live `--dry-run --verbose` smoke check
# in the verification bundle, which does exercise real host paths.
# ---------------------------------------------------------------------------


def test_execute_tick_exits_zero_silently_when_lock_is_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lock_path = tmp_path / "dag-tick.lock"
    holder = dag_tick.try_acquire_lock(lock_path)
    assert holder is not None
    ctx = _ctx(tmp_path, lock_path=lock_path)

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "subprocess must never be touched while the lock is held"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fail)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail)
    try:
        assert dag_tick.execute_tick(ctx) == 0
    finally:
        holder.close()


def test_execute_tick_skips_when_gate_is_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = _ctx(tmp_path)
    census_called = False

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        nonlocal census_called
        if argv[1] == "agents":
            census_called = True
        return _FakeCompleted(
            returncode=1,
            stderr="'logs' is disabled by CLAUDE_CODE_DISABLE_AGENT_VIEW.",
        )

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    assert dag_tick.execute_tick(ctx) == 0
    assert census_called is False


def test_execute_tick_proceeds_when_gate_is_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Gate fail-open (#578 respec round 3).

    "unknown" must PROCEED, not skip — only the documented "off" face
    skips the tick. `read_census` is itself gated and logs its own
    failures, so it is the real gate.
    """
    ctx = _ctx(tmp_path)
    census_called = False

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        nonlocal census_called
        if argv[1] == "logs":
            return _FakeCompleted(returncode=1, stderr="an unrecognized wording")
        if argv[1] == "agents":
            census_called = True
            return _FakeCompleted(returncode=0, stdout="[]")
        msg = f"unexpected subprocess.run call: {argv}"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    with caplog.at_level("WARNING"):
        assert dag_tick.execute_tick(ctx) == 0
    assert census_called is True
    assert any("unknown" in record.getMessage() for record in caplog.records)


def _fake_run_for_one_dead_node(argv: list[str], **_kwargs: object) -> _FakeCompleted:
    if argv[1] == "logs":
        return _FakeCompleted(returncode=1, stderr="No job matching 'zzbogus'.")
    if argv[1] == "agents":
        census = json.dumps([{"id": "dead1", "kind": "background", "cwd": "/x"}])
        return _FakeCompleted(returncode=0, stdout=census)
    msg = f"unexpected subprocess.run call: {argv}"
    raise AssertionError(msg)


def test_execute_tick_dry_run_reports_without_spawning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir, dry_run=True)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "dry-run must never spawn"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)

    assert dag_tick.execute_tick(ctx) == 0
    captured = capsys.readouterr()
    assert "[dry-run] would respawn dead1" in captured.out


def test_execute_tick_respawns_a_dead_node(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    popen_calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        popen_calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)

    assert dag_tick.execute_tick(ctx) == 0
    assert popen_calls == [["claude", "respawn", "dead1"]]


def test_execute_tick_logs_instead_of_respawning_an_over_age_dead_node(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """#578 respec round 3 (--max-age), end to end.

    A DEAD node older than `max_age_s` gets a LOG line, never a respawn —
    and no `Popen` call.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "idle"})
    state_path = jobs_dir / "dead1" / "state.json"
    ancient = state_path.stat().st_mtime - 100_000
    os.utime(state_path, (ancient, ancient))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir, max_age_s=86400.0)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "an over-age DEAD node must never be respawned"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)

    assert dag_tick.execute_tick(ctx) == 0
    captured = capsys.readouterr()
    assert "stale beyond --max-age" in captured.out
    assert "respawn dead1" not in captured.out


def test_execute_tick_never_respawns_a_fresh_escalated_node(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """#601 arm A, end to end: `blocked ∧ needs≠∅` + dead pid -> no respawn.

    The state.json is left FRESH on purpose. An over-age fixture would
    have been suppressed by `--max-age` regardless, so it could not tell a
    working NEEDS_HUMAN class from the accident that was covering for its
    absence — this is the arm that fails if the classification is removed.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})  # readable, names nobody -> pid dead
    _write_state(
        jobs_dir,
        "dead1",
        {"state": "blocked", "tempo": "blocked", "needs": _LIVE_NEEDS_JULY_13},
    )
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir, max_age_s=86400.0)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "an escalated node must never be respawned"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)

    assert dag_tick.execute_tick(ctx) == 0
    captured = capsys.readouterr()
    assert "NEEDS_HUMAN dead1" in captured.out
    assert _LIVE_NEEDS_JULY_13 in captured.out
    assert "RESPAWN dead1" not in captured.out


def test_execute_tick_still_respawns_a_fresh_blocked_node_without_needs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """#601 arm B, end to end: the control — one field different, one outcome.

    Identical to arm A but for the absent `needs` key. A fix that keyed off
    `state == "blocked"` alone would suppress this respawn too, silently
    retiring the watchdog's primary recovery path.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "dead1", {"state": "blocked", "tempo": "blocked"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir, max_age_s=86400.0)
    popen_calls: list[list[str]] = []

    def _fake_popen(argv: list[str], **_kwargs: object) -> None:
        popen_calls.append(argv)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fake_popen)

    assert dag_tick.execute_tick(ctx) == 0
    assert popen_calls == [["claude", "respawn", "dead1"]]


def test_execute_tick_stops_a_done_node_with_live_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"done1": os.getpid()})
    _write_state(jobs_dir, "done1", {"state": "done", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    run_calls: list[list[str]] = []

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        if argv[1] == "logs":
            return _FakeCompleted(returncode=1, stderr="No job matching 'zzbogus'.")
        if argv[1] == "agents":
            census = json.dumps([{"id": "done1", "kind": "background", "cwd": "/x"}])
            return _FakeCompleted(returncode=0, stdout=census)
        run_calls.append(argv)
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    assert dag_tick.execute_tick(ctx) == 0
    assert run_calls == [["claude", "stop", "done1"]]
    captured = capsys.readouterr()
    assert "dag-tick: STOP done1 (rc=0)" in captured.out


def test_execute_tick_wedged_node_makes_no_action_subprocess_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {"wedged1": os.getpid()})
    _write_state(jobs_dir, "wedged1", {"state": "blocked", "tempo": "active"})
    state_path = jobs_dir / "wedged1" / "state.json"
    stale = state_path.stat().st_mtime - 300
    os.utime(state_path, (stale, stale))
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)

    def _fake_run(argv: list[str], **_kwargs: object) -> _FakeCompleted:
        if argv[1] == "logs":
            return _FakeCompleted(returncode=1, stderr="No job matching 'zzbogus'.")
        if argv[1] == "agents":
            census = json.dumps([{"id": "wedged1", "kind": "background", "cwd": "/x"}])
            return _FakeCompleted(returncode=0, stdout=census)
        msg = f"a WEDGED node must never trigger a claude verb: {argv}"
        raise AssertionError(msg)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        msg = "a WEDGED node must never trigger a claude verb"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run)
    monkeypatch.setattr(dag_tick.subprocess, "Popen", _fail_popen)
    assert dag_tick.execute_tick(ctx) == 0
    captured = capsys.readouterr()
    assert "WEDGED wedged1" in captured.out


# --------------------------------------------------- #580 Codex lane reaping


def _codex_lane(
    ctx: dag_tick.TickContext,
    node_id: str,
    *,
    verdict: str | None = None,
    lane: dict[str, object] | None = None,
    settled: bool = True,
) -> Path:
    """A Codex review lane under `node_id`'s job dir.

    `lane` overrides fields in the launcher's lane record (owner,
    rework_count); it is one parameter rather than one per field so this stays
    under ruff's argument ceiling without a suppression.

    `settled=True` writes the exit marker by default — the liveness gate runs
    FIRST, so a fixture without it makes every reap return NOT_SETTLED and the
    assertion below it tests nothing.
    """
    run_dir = ctx.jobs_dir / node_id / dag_tick.CODEX_LANE_DIRNAME
    run_dir.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {"owner": node_id, "status": "in_progress"}
    record.update(lane or {})
    (run_dir / codex_verdict.LANE_FILENAME).write_text(json.dumps(record))
    if verdict is not None:
        (run_dir / codex_verdict.VERDICT_FILENAME).write_text(
            json.dumps(
                {"schema_version": 1, "verdict": verdict, "rationale": "because"}
            )
        )
    if settled:
        (run_dir / codex_verdict.EXIT_MARKER_FILENAME).write_text("EXIT: 0\n")
    return run_dir


def _classified(node_id: str) -> dag_tick.ClassifiedNode:
    return dag_tick.ClassifiedNode(
        node_id=node_id,
        node_class=dag_tick.NodeClass.ALIVE,
        pid_alive=True,
        state_age_s=1.0,
    )


def test_a_node_with_no_codex_lane_is_silent(tmp_path: Path) -> None:
    """Most nodes never run a review lane.

    A line per node per 60s would bury the ones that matter, so the absence of
    a lane directory must produce nothing at all.
    """
    ctx = _ctx(tmp_path)
    (ctx.jobs_dir / "n1").mkdir(parents=True)
    assert dag_tick.reap_codex_lanes([_classified("n1")], ctx) == []


def test_an_approved_lane_reports_the_advance_edge(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _codex_lane(ctx, "n1", verdict="approve")
    lines = dag_tick.reap_codex_lanes([_classified("n1")], ctx)
    assert len(lines) == 1
    assert "CODEX-REAP n1" in lines[0]
    assert "edge=advance" in lines[0]


def test_a_missing_verdict_escalates_through_the_tick(tmp_path: Path) -> None:
    """The inverted OMC default, end to end through the tick.

    A lane that exited without writing a verdict is the common abort outcome
    (measured on codex 0.146.0: every induced abort leaves no file), so this
    is the path an unattended fleet actually takes.
    """
    ctx = _ctx(tmp_path)
    _codex_lane(ctx, "n1", verdict=None)
    lines = dag_tick.reap_codex_lanes([_classified("n1")], ctx)
    assert len(lines) == 1
    assert "edge=needs_human" in lines[0]
    assert "file_missing" in lines[0]


def test_the_reap_line_does_not_claim_the_edge_was_applied(tmp_path: Path) -> None:
    """Projection is the scheduler's job (#575 R1); #602 implements it.

    A log line naming an action this process does not perform is how a reader
    concludes an escalation reached the tracker when it reached a launchd log
    — the exact #601 finding that cost two review rounds.
    """
    ctx = _ctx(tmp_path)
    _codex_lane(ctx, "n1", verdict="reject")
    line = dag_tick.reap_codex_lanes([_classified("n1")], ctx)[0]
    assert "DECIDED here, not applied" in line
    assert "#602" in line


def test_a_no_op_edge_is_quiet_unless_verbose(tmp_path: Path) -> None:
    """Both arms: steady-state no-ops would otherwise be the bulk of the log."""
    quiet = _ctx(tmp_path, verbose=False)
    _codex_lane(quiet, "n1", verdict="approve", lane={"owner": "somebody-else"})
    assert dag_tick.reap_codex_lanes([_classified("n1")], quiet) == []

    loud = _ctx(tmp_path, verbose=True)
    lines = dag_tick.reap_codex_lanes([_classified("n1")], loud)
    assert len(lines) == 1
    assert "owner_mismatch" in lines[0]


def test_the_tick_honours_the_rework_bound_from_the_lane(tmp_path: Path) -> None:
    """A revise at the bound escalates instead of reopening implement.

    Both arms, because a bound verified only in the under-budget direction
    would pass against a reaper that never escalates.
    """
    under = _ctx(tmp_path / "a")
    _codex_lane(under, "n1", verdict="revise", lane={"rework_count": 0})
    assert (
        "edge=reopen_implement"
        in dag_tick.reap_codex_lanes([_classified("n1")], under)[0]
    )

    spent = _ctx(tmp_path / "b")
    _codex_lane(spent, "n1", verdict="revise", lane={"rework_count": 2})
    assert (
        "edge=needs_human" in dag_tick.reap_codex_lanes([_classified("n1")], spent)[0]
    )


@pytest.mark.parametrize(
    ("lane_body", "expected"),
    [
        (None, 0),  # no lane file at all
        ("{not json", 0),  # unparsable
        ("[1,2]", 0),  # JSON, but not an object
        ('{"owner": "n1"}', 0),  # no rework_count field
        ('{"rework_count": 3}', 3),
        ('{"rework_count": 0}', 0),
        ('{"rework_count": -1}', 0),  # negative is nonsense -> permissive
        ('{"rework_count": "2"}', 0),  # wrong type -> permissive
        ('{"rework_count": 2.5}', 0),  # float is not a count
    ],
)
def test_read_rework_count_defaults_permissively(
    tmp_path: Path, lane_body: str | None, expected: int
) -> None:
    """Every malformed shape reads as 0, the PERMISSIVE direction.

    Deliberate: assuming the budget is spent would escalate every lane whose
    launcher had not yet written the field, turning a rollout into an
    escalation storm. The row returning 3 is the control arm — without it this
    table would pass against a function that returns 0 unconditionally.
    """
    run_dir = tmp_path / "lane"
    run_dir.mkdir()
    if lane_body is not None:
        (run_dir / codex_verdict.LANE_FILENAME).write_text(lane_body)
    assert dag_tick.read_rework_count(run_dir) == expected


def test_execute_tick_emits_codex_reap_lines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The WIRING, driven end to end — #580 is explicitly not module-only.

    Asserted through `execute_tick`'s real stdout rather than by grepping its
    source: a source-substring check passes on a call that is present but
    unreachable, and "a reaper nobody calls" is the #343 shape — a perfect
    guard that never runs. The mutation that matters (deleting the
    `reap_codex_lanes(...)` line from `execute_tick`) fails this test and
    would NOT fail a source check written against the helper.
    """
    jobs_dir = tmp_path / "jobs"
    daemon_dir = _roster(tmp_path, {})
    _write_state(jobs_dir, "dead1", {"state": "running", "tempo": "idle"})
    ctx = _ctx(tmp_path, jobs_dir=jobs_dir, daemon_dir=daemon_dir)
    _codex_lane(ctx, "dead1", verdict="approve")

    monkeypatch.setattr(dag_tick.subprocess, "run", _fake_run_for_one_dead_node)

    def _no_popen(_argv: list[str], **_kwargs: object) -> None:
        """Stub: a real Popen here would launch `claude` from a test.

        This node classifies ALIVE, so nothing should spawn anyway.
        """

    monkeypatch.setattr(dag_tick.subprocess, "Popen", _no_popen)

    assert dag_tick.execute_tick(ctx) == 0
    out = capsys.readouterr().out
    assert "CODEX-REAP dead1" in out
    assert "edge=advance" in out
