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
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import dag_tick

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


def _roster(tmp_path: Path, workers: dict[str, int]) -> Path:
    """Write a readable `roster.json` under `tmp_path/"daemon"`.

    Names each `node_id -> pid` in `workers` (an empty dict is a readable
    roster naming NO worker — real negative pid evidence, distinct from a
    missing/unreadable roster FILE, which is conservative ALIVE). Returns
    the daemon dir, since every caller needs it for `_ctx()` /
    `classify_background_rows` too. Dedups the ~10 repeated
    mkdir+roster.json writes this file used to carry (#578 respec round 3).
    """
    daemon_dir = tmp_path / "daemon"
    daemon_dir.mkdir(exist_ok=True)
    payload = {"workers": {node_id: {"pid": pid} for node_id, pid in workers.items()}}
    (daemon_dir / "roster.json").write_text(json.dumps(payload))
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

    Computed from the axis lists rather than hardcoded, so adding an axis
    value fails here instead of silently leaving cells unenumerated — which
    is how rounds 5, 6 and 7 each found a live defect.
    """
    states = [_TERMINAL, "blocked", _OTHER, None]
    bools = [False, True]
    tempos = [_IDLE, _ACTIVE]
    expected_cells = {
        (s, n, q, a, t)
        for s in states
        for n in bools
        for q in bools
        for a in bools
        for t in tempos
    }
    covered = {(row[0], row[1], row[2], row[3], row[4]) for row in _CLASSIFY_TABLE}
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


def test_execute_stop_reports_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)
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
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)
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
    """
    daemon_dir = _roster(tmp_path, {})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)

    def _fail(*_args: object, **_kwargs: object) -> None:
        msg = "must not issue a stop once the pid has already settled"
        raise AssertionError(msg)

    monkeypatch.setattr(dag_tick.subprocess, "run", _fail)
    line = dag_tick.execute_stop("abc123", ctx)
    assert "SKIP stop abc123" in line
    assert "settled" in line


def test_execute_stop_missing_binary_returns_skip_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    daemon_dir = _roster(tmp_path, {"abc123": os.getpid()})
    ctx = _ctx(tmp_path, daemon_dir=daemon_dir)

    def _raise_missing(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError(2, "No such file or directory", "claude")

    monkeypatch.setattr(dag_tick.subprocess, "run", _raise_missing)
    line = dag_tick.execute_stop("abc123", ctx)
    assert "SKIP stop abc123" in line
    assert "claude binary unavailable" in line


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
