# Copyright (c) 2026 Raymond Manaloto
"""Tests for the Codex verdict contract + reaper (dotfiles_setup.codex_verdict).

#580. The consumer mechanics are ported from OMC verbatim because they are the
genuinely hard-won, transport-independent part; the two DEFAULTS are inverted on
purpose, and that inversion is what most of these tests pin.

Every gate here is armed in both directions. The reaper's failure modes are the
whole point of the module — a test suite that only exercises the happy verdict
would be a check that can only pass.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import classifier_tables
from dotfiles_setup import codex_verdict as cv

# --------------------------------------------------------------- the schema


def test_schema_requires_a_schema_version() -> None:
    """`schema_version` must be present AND required.

    OMC's payload has no version field, "which is why a contract change there
    breaks silently" (#580). Optional would let an unversioned payload
    validate, which is the same hole with extra steps.
    """
    assert "schema_version" in cv.VERDICT_SCHEMA["required"]
    assert cv.VERDICT_SCHEMA["properties"]["schema_version"]["const"] == (
        cv.SCHEMA_VERSION
    )


def test_schema_forbids_extra_properties() -> None:
    """The schema must forbid extra properties.

    `additionalProperties: false` is what makes the provider enforcement
    meaningful — without it a model may return the required keys plus
    anything, and a future contract change cannot be detected.
    """
    assert cv.VERDICT_SCHEMA["additionalProperties"] is False


def test_schema_enumerates_exactly_the_three_terminal_verdicts() -> None:
    """Exactly three verdicts, as an exact set.

    #575 R7 keeps three mapped to three edges rather than collapsing `revise`
    into failed. An exact set, not a membership check, so ADDING a fourth
    without an edge mapping fails here.
    """
    assert set(cv.VERDICT_SCHEMA["properties"]["verdict"]["enum"]) == {
        v.value for v in cv.Verdict
    }
    assert {v.value for v in cv.Verdict} == {"approve", "revise", "reject"}


def test_write_schema_materialises_valid_json_matching_the_canonical_dict() -> None:
    """The schema file `--output-schema` needs is DERIVED, never a second copy.

    A tracked JSON file beside the Python dict is two sources of one truth,
    and the drift is silent — the model keeps validating against whichever
    the launcher happened to pass.
    """
    written = json.loads(json.dumps(cv.VERDICT_SCHEMA))
    assert written == cv.VERDICT_SCHEMA


# ------------------------------------------------------------ verdict parse
#
# The parse axes, crossed exhaustively below: the raw text is
# (well-formed JSON | not) x (an object | not) x (schema_version present,
# correct, wrong, absent) x (verdict valid | invalid | absent).


@pytest.mark.parametrize(
    ("raw", "expected_verdict"),
    [
        (
            '{"schema_version": 1, "verdict": "approve", "rationale": "r"}',
            cv.Verdict.APPROVE,
        ),
        (
            '{"schema_version": 1, "verdict": "revise", "rationale": "r"}',
            cv.Verdict.REVISE,
        ),
        (
            '{"schema_version": 1, "verdict": "reject", "rationale": "r"}',
            cv.Verdict.REJECT,
        ),
    ],
)
def test_parse_accepts_each_terminal_verdict(
    raw: str, expected_verdict: object
) -> None:
    parsed, detail = cv.parse_verdict(raw)
    assert parsed is not None, detail
    assert parsed.verdict is expected_verdict


@pytest.mark.parametrize(
    ("raw", "why"),
    [
        ("", "empty file — the codex 'wrote empty content' path"),
        ("   \n ", "whitespace only"),
        ("not json at all", "not JSON"),
        ('{"schema_version": 1, "verdict": "approve"', "truncated mid-object"),
        ("[1, 2, 3]", "JSON but not an object"),
        ('"approve"', "JSON but a bare string"),
        ('{"verdict": "approve", "rationale": "r"}', "no schema_version"),
        (
            '{"schema_version": 2, "verdict": "approve", "rationale": "r"}',
            "wrong version",
        ),
        (
            '{"schema_version": 1, "verdict": "maybe", "rationale": "r"}',
            "verdict not in enum",
        ),
        ('{"schema_version": 1, "rationale": "r"}', "no verdict"),
        ('{"schema_version": 1, "verdict": "approve"}', "no rationale"),
        (
            '{"schema_version": 1, "verdict": "approve", "rationale": "r", "x": 1}',
            "extra property",
        ),
    ],
)
def test_parse_rejects_every_malformed_shape(raw: str, why: str) -> None:
    """The FAIL direction, one row per way the contract can be broken.

    ⚠️ The empty-file row is not hypothetical. The codex 0.146.0 binary
    carries an explicit path — `Warning: no last agent message; wrote empty
    content to <path>` in `exec/src/lib.rs` — so a present-but-empty `-o`
    file is a real state the consumer must reject rather than trust.
    """
    parsed, detail = cv.parse_verdict(raw)
    assert parsed is None, f"{why}: expected rejection, got {parsed}"
    assert detail, f"{why}: a rejection must say why"


def test_parse_preserves_the_rationale() -> None:
    """The rationale survives the parse.

    It is the operator-facing half; dropping it would make an escalation
    unactionable.
    """
    parsed, _ = cv.parse_verdict(
        '{"schema_version": 1, "verdict": "reject", "rationale": "spec drift"}'
    )
    assert parsed is not None
    assert parsed.rationale == "spec drift"


# -------------------------------------------------------------- edge mapping
#
# #575 R7: approve -> advance, revise -> reopen implement, reject -> reopen
# research, all bounded by #573's max_rework 2 -> dag:needs-human.

# The table's axes, IN COLUMN ORDER — the single place they are written down.
# `test_edge_table_axes_match_the_registry` binds these names to
# `classifier_tables.REGISTRY`, which DERIVES the real axis set from
# `edge_for()` itself. Restating the axes locally is exactly how a real axis
# went missing from BOTH the code's enumeration and the table's in #601.
#
# ⚠️ `rework_count` and `max_rework` are two PARAMETERS but ONE question:
# `edge_for` asks `rework_count >= max_rework` and nothing else of either, so
# neither has a standalone partition — only the PAIR does. Both are therefore
# crossed as the two sides of that single boolean, which is why this table has
# 3 x 2 meaningful cells rather than 3 x N x M. That modelling decision is
# ARMED by `test_the_rework_bound_is_a_single_equivalence_class` below: if any
# two numbers on the same side of the bound disagreed, a real axis would be
# hiding inside the projection — the #601 defect wearing a different hat.
_BOUND_SIDES: tuple[bool, ...] = (False, True)  # rework_count >= max_rework

_AXIS_VALUES: dict[str, tuple[object, ...]] = {
    "verdict": tuple(cv.Verdict),
    "rework_count": _BOUND_SIDES,
    "max_rework": _BOUND_SIDES,
}

# Nothing is held constant: all three axes are finitely modellable, and pinning
# a modellable axis is the move `illegal_pin` exists to refuse.
_PINNED_AXES: frozenset[str] = frozenset()

_EDGE_TABLE: list[tuple[cv.Verdict, int, int, cv.Edge]] = [
    # verdict, rework_count, max_rework, expected edge
    (cv.Verdict.APPROVE, 0, 2, cv.Edge.ADVANCE),
    (cv.Verdict.APPROVE, 1, 2, cv.Edge.ADVANCE),
    # approve is NOT bounded by rework — an approved unit of work advances
    # however many times it was reworked to get there.
    (cv.Verdict.APPROVE, 2, 2, cv.Edge.ADVANCE),
    (cv.Verdict.APPROVE, 9, 2, cv.Edge.ADVANCE),
    (cv.Verdict.REVISE, 0, 2, cv.Edge.REOPEN_IMPLEMENT),
    (cv.Verdict.REVISE, 1, 2, cv.Edge.REOPEN_IMPLEMENT),
    # at the bound, a further rework is refused and the node escalates
    (cv.Verdict.REVISE, 2, 2, cv.Edge.NEEDS_HUMAN),
    (cv.Verdict.REVISE, 3, 2, cv.Edge.NEEDS_HUMAN),
    (cv.Verdict.REJECT, 0, 2, cv.Edge.REOPEN_RESEARCH),
    (cv.Verdict.REJECT, 1, 2, cv.Edge.REOPEN_RESEARCH),
    (cv.Verdict.REJECT, 2, 2, cv.Edge.NEEDS_HUMAN),
    (cv.Verdict.REJECT, 3, 2, cv.Edge.NEEDS_HUMAN),
    # max_rework=0 refuses any rework at all, immediately
    (cv.Verdict.REVISE, 0, 0, cv.Edge.NEEDS_HUMAN),
    (cv.Verdict.REJECT, 0, 0, cv.Edge.NEEDS_HUMAN),
    (cv.Verdict.APPROVE, 0, 0, cv.Edge.ADVANCE),
]


@pytest.mark.parametrize("row", _EDGE_TABLE)
def test_edge_mapping_truth_table(
    row: tuple[cv.Verdict, int, int, cv.Edge],
) -> None:
    """Every (verdict x rework-position) cell, derived by hand from #575 R7.

    The row is passed whole rather than unpacked — the row IS the unit under
    test, and unpacking trips ruff PLR0913 (`tests/AGENTS.md`).
    """
    verdict, rework_count, max_rework, expected = row
    assert (
        cv.edge_for(verdict, rework_count=rework_count, max_rework=max_rework)
        is expected
    )


def test_edge_table_reaches_every_edge_a_verdict_can_produce() -> None:
    """Guards against a table that enumerates rows but exercises one answer.

    `Edge.NONE` is the one edge unreachable here BY CONSTRUCTION — it is the
    no-op a reaper returns when there is nothing to decide, never something a
    verdict maps to. Asserted so its absence reads as deliberate.
    """
    reached = {row[3] for row in _EDGE_TABLE}
    assert reached == {
        cv.Edge.ADVANCE,
        cv.Edge.REOPEN_IMPLEMENT,
        cv.Edge.REOPEN_RESEARCH,
        cv.Edge.NEEDS_HUMAN,
    }
    assert cv.Edge.NONE not in reached


def test_every_verdict_appears_in_the_edge_table() -> None:
    """Adding a fourth verdict without mapping it must fail HERE, not in prod."""
    assert {row[0] for row in _EDGE_TABLE} == set(cv.Verdict)


def test_edge_table_axes_match_the_registry() -> None:
    """The table's axis list must equal the one DERIVED from `edge_for()`.

    The meta-test the other three structurally could not be: they all judge
    this table AGAINST ITSELF. An axis `edge_for` reads but the table never
    heard of is invisible to the edge-reachability check and to the
    every-verdict check alike — both pass on a table that is internally
    perfect and externally short a column. That is `tempo` in #601 round 7.

    `edge_for` was found by `classifier_tables`' `unlisted` scan on first
    contact with this branch, not by a human: it shipped after the gate was
    written, and the two met at the merge. `_EDGE_TABLE` already existed; what
    was missing is this binding.
    """
    spec = classifier_tables.REGISTRY["dotfiles_setup.codex_verdict:edge_for"]
    assert tuple(_AXIS_VALUES) == ("verdict", "rework_count", "max_rework")
    assert frozenset(_AXIS_VALUES) == spec.axes
    assert frozenset(spec.pinned_axes) == _PINNED_AXES
    assert frozenset(_AXIS_VALUES) | _PINNED_AXES == spec.declared()


def test_the_rework_bound_is_a_single_equivalence_class() -> None:
    """ARMS THE MODELLING DECISION: the two numbers really are ONE boolean.

    `_AXIS_VALUES` crosses `rework_count`/`max_rework` as the two sides of
    `rework_count >= max_rework`, which is honest only if nothing else about
    the numbers changes the answer. Every row sharing a verdict AND a side of
    the bound must therefore share an edge; if any pair disagreed, a real axis
    would be hiding inside the projection.

    The second assertion is the control arm — without it the first is vacuous,
    since a table that never wrote down both sides of the bound would satisfy
    "no cell disagrees" while proving nothing.
    """
    by_cell: dict[tuple[cv.Verdict, bool], set[cv.Edge]] = {}
    for verdict, rework_count, max_rework, edge in _EDGE_TABLE:
        by_cell.setdefault((verdict, rework_count >= max_rework), set()).add(edge)
    assert all(len(edges) == 1 for edges in by_cell.values())
    assert set(by_cell) == set(itertools.product(cv.Verdict, _BOUND_SIDES))


@pytest.mark.parametrize("verdict", list(cv.Verdict))
def test_the_charged_verdicts_are_exactly_the_bounded_ones(
    verdict: cv.Verdict,
) -> None:
    """⭐ `demands_rework` must agree with the bound it feeds (#616).

    The producer charges a rework round for the verdicts this answers True to;
    `edge_for` escalates the verdicts it bounds. If those two sets ever
    disagree the loop breaks in one of two silent ways: a verdict charged but
    never bounded spends a budget nothing enforces, and a verdict bounded but
    never charged makes `max_rework` UNREACHABLE — which is #616 itself.

    So the assertion is set equality, derived on both sides rather than
    restated as `{REVISE, REJECT}`. A literal here would be the third copy of
    the fact, and the one that decides which of the other two is wrong.

    The `max_rework=0` arm is what makes the right-hand side a real
    measurement: with an already-spent budget, `edge_for` answers
    `needs_human` for precisely the verdicts it bounds and leaves the rest
    alone.
    """
    spent = cv.edge_for(verdict, rework_count=0, max_rework=0)
    assert cv.demands_rework(verdict) is (spent is cv.Edge.NEEDS_HUMAN)


def test_the_charge_predicate_discriminates() -> None:
    """Control arm: `demands_rework` is not a constant.

    Parametrised per-verdict above, so a predicate stuck at True (or at False)
    would fail some rows and pass others — but only if the verdict set really
    contains both kinds. This pins that, so the test above cannot go vacuous
    if `Verdict` ever loses a member.
    """
    charged = {v for v in cv.Verdict if cv.demands_rework(v)}
    assert charged, "nothing is ever charged — the budget can never be spent"
    assert charged != set(cv.Verdict), "everything is charged — approve would be too"


# ------------------------------------------------------------------- reaper


def _lane(
    run_dir: Path,
    *,
    owner: str = "node-1",
    status: str = "in_progress",
    settled: bool = True,
) -> Path:
    """A lane directory. `settled=True` writes the exit marker by default.

    The default is deliberate: the liveness gate runs FIRST, so a fixture
    without the marker makes every reap return NOT_SETTLED and the test below
    it asserts nothing about the code it names. (That is exactly what happened
    on the first run of this suite — the gate refused, four tests failed, and
    the fixture was the defect.)
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / cv.LANE_FILENAME).write_text(
        json.dumps({"owner": owner, "status": status})
    )
    if settled:
        (run_dir / cv.EXIT_MARKER_FILENAME).write_text("EXIT: 0\n")
    return run_dir


def _verdict_file(run_dir: Path, payload: str) -> None:
    (run_dir / cv.VERDICT_FILENAME).write_text(payload)


_APPROVE = '{"schema_version": 1, "verdict": "approve", "rationale": "ok"}'


def test_reap_approves_and_renames_for_idempotency(tmp_path: Path) -> None:
    run_dir = _lane(tmp_path / "run")
    _verdict_file(run_dir, _APPROVE)
    result = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.APPROVED
    assert result.edge is cv.Edge.ADVANCE
    assert not (run_dir / cv.VERDICT_FILENAME).exists()
    assert (run_dir / cv.PROCESSED_FILENAME).exists()


def test_reap_is_idempotent_on_a_second_call(tmp_path: Path) -> None:
    """The rename is the idempotency mechanism; this is the arm that proves it.

    Without it a re-run of the tick would advance the same node twice.
    """
    run_dir = _lane(tmp_path / "run")
    _verdict_file(run_dir, _APPROVE)
    first = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    second = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert first.outcome is cv.ReapOutcome.APPROVED
    assert second.outcome is cv.ReapOutcome.ALREADY_PROCESSED
    assert second.edge is cv.Edge.NONE


def test_a_missing_verdict_file_escalates_rather_than_warning(tmp_path: Path) -> None:
    """⚠️ INVERTED OMC DEFAULT #1, and the reason is operational.

    OMC warns and moves on. Under unattended operation that leaves the task
    stuck `in_progress` forever with nobody to read the warning. Measured on
    codex 0.146.0: every abort I could induce — SIGINT, SIGTERM, SIGKILL, and
    two distinct graceful `exit(1)` paths — left NO file, so this is the
    common abort outcome, not an edge case.
    """
    run_dir = _lane(tmp_path / "run")
    result = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.FILE_MISSING
    assert result.edge is cv.Edge.NEEDS_HUMAN


def test_an_unparsable_verdict_escalates_rather_than_warning(tmp_path: Path) -> None:
    """⚠️ INVERTED OMC DEFAULT #2. Same reasoning as file_missing."""
    run_dir = _lane(tmp_path / "run")
    _verdict_file(run_dir, "{not json")
    result = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.PARSE_FAILED
    assert result.edge is cv.Edge.NEEDS_HUMAN


def test_an_empty_verdict_file_escalates(tmp_path: Path) -> None:
    """The codex 'wrote empty content' path, end to end through the reaper.

    Distinct from file_missing: the file EXISTS, so an existence check alone
    would treat this as a successful run. That is exactly what the #580
    NEEDS-PROBE was asked to settle.
    """
    run_dir = _lane(tmp_path / "run")
    _verdict_file(run_dir, "")
    result = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.PARSE_FAILED
    assert result.edge is cv.Edge.NEEDS_HUMAN


def test_a_failed_reap_still_renames_so_it_cannot_loop(tmp_path: Path) -> None:
    """An escalating outcome must consume the file too.

    Otherwise the tick re-reads the same broken verdict every 60s and
    re-escalates forever — a warning storm instead of the single escalation
    the inverted default exists to produce.
    """
    run_dir = _lane(tmp_path / "run")
    _verdict_file(run_dir, "{not json")
    cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert not (run_dir / cv.VERDICT_FILENAME).exists()
    assert (run_dir / cv.PROCESSED_FILENAME).exists()


def test_the_cas_refuses_a_lane_owned_by_someone_else(tmp_path: Path) -> None:
    """Re-verifying OWNER under the lock — half of OMC's CAS.

    A verdict file in a run dir another node owns must never be consumed on
    this node's behalf.
    """
    run_dir = _lane(tmp_path / "run", owner="someone-else")
    _verdict_file(run_dir, _APPROVE)
    result = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.OWNER_MISMATCH
    assert result.edge is cv.Edge.NONE
    # …and it must NOT consume the file: it is not ours to consume.
    assert (run_dir / cv.VERDICT_FILENAME).exists()


def test_the_cas_refuses_a_lane_that_is_no_longer_in_progress(tmp_path: Path) -> None:
    """Re-verifying STATUS under the lock — the other half of the CAS."""
    run_dir = _lane(tmp_path / "run", status="cancelled")
    _verdict_file(run_dir, _APPROVE)
    result = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.STATUS_MISMATCH
    assert result.edge is cv.Edge.NONE


def test_a_missing_lane_file_escalates_rather_than_assuming_ownership(
    tmp_path: Path,
) -> None:
    """No lane record means the CAS cannot be evaluated at all.

    Assuming ownership would be the fail-OPEN reading of an absence — the
    shape this repo has been bitten by repeatedly.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / cv.EXIT_MARKER_FILENAME).write_text("EXIT: 0\n")
    _verdict_file(run_dir, _APPROVE)
    result = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.LANE_UNREADABLE
    assert result.edge is cv.Edge.NEEDS_HUMAN


def test_the_liveness_gate_refuses_to_read_a_still_running_lane(
    tmp_path: Path,
) -> None:
    """A half-written file is never read — OMC's liveness gate.

    Injected rather than probed so the test states the contract instead of
    racing a real process.
    """
    run_dir = _lane(tmp_path / "run")
    _verdict_file(run_dir, _APPROVE)
    result = cv.reap(
        run_dir,
        expected_owner="node-1",
        rework_count=0,
        max_rework=2,
        is_settled=lambda _: False,
    )
    assert result.outcome is cv.ReapOutcome.NOT_SETTLED
    assert result.edge is cv.Edge.NONE
    # The whole point: it did not touch the file.
    assert (run_dir / cv.VERDICT_FILENAME).exists()
    assert not (run_dir / cv.PROCESSED_FILENAME).exists()


def test_the_liveness_gate_is_armed_the_other_way(tmp_path: Path) -> None:
    """The PASS direction, so the gate above is not merely always-refusing."""
    run_dir = _lane(tmp_path / "run")
    _verdict_file(run_dir, _APPROVE)
    result = cv.reap(
        run_dir,
        expected_owner="node-1",
        rework_count=0,
        max_rework=2,
        is_settled=lambda _: True,
    )
    assert result.outcome is cv.ReapOutcome.APPROVED


def test_default_liveness_gate_uses_the_lane_exit_marker(tmp_path: Path) -> None:
    """The real gate, not the injected one.

    #575 R4's `run-lane.sh` writes `EXIT: <code>`; its ABSENCE means the lane
    was group-killed or is still running. Both arms, because a gate verified
    only in the settled direction is decoration.
    """
    run_dir = _lane(tmp_path / "run", settled=False)
    assert cv.lane_is_settled(run_dir) is False
    (run_dir / cv.EXIT_MARKER_FILENAME).write_text("EXIT: 0\n")
    assert cv.lane_is_settled(run_dir) is True


def test_reap_maps_revise_and_reject_through_the_bound(tmp_path: Path) -> None:
    """The reaper honours the rework bound, not just `edge_for` in isolation."""
    run_dir = _lane(tmp_path / "run")
    _verdict_file(
        run_dir, '{"schema_version": 1, "verdict": "revise", "rationale": "again"}'
    )
    under = cv.reap(run_dir, expected_owner="node-1", rework_count=0, max_rework=2)
    assert under.edge is cv.Edge.REOPEN_IMPLEMENT

    run_dir2 = _lane(tmp_path / "run2")
    _verdict_file(
        run_dir2, '{"schema_version": 1, "verdict": "revise", "rationale": "again"}'
    )
    at_bound = cv.reap(run_dir2, expected_owner="node-1", rework_count=2, max_rework=2)
    assert at_bound.edge is cv.Edge.NEEDS_HUMAN
    assert at_bound.outcome is cv.ReapOutcome.REVISE


def test_every_reap_outcome_has_a_defined_edge() -> None:
    """Every outcome must have an edge.

    An unmapped one falls through, which is how a node gets stuck
    `in_progress` forever — the failure this module inverts.
    """
    for outcome in cv.ReapOutcome:
        assert outcome in cv.OUTCOME_EDGES, f"{outcome} has no edge mapping"


def test_the_escalating_outcomes_are_exactly_the_inverted_set() -> None:
    """Pins the inversion itself, as an exact set.

    If someone later "fixes" `file_missing` back to a warning, this fails —
    which is the whole reason the set is written down rather than inferred.
    """
    escalating = {
        outcome
        for outcome, edge in cv.OUTCOME_EDGES.items()
        if edge is cv.Edge.NEEDS_HUMAN
    }
    assert escalating == {
        cv.ReapOutcome.FILE_MISSING,
        cv.ReapOutcome.PARSE_FAILED,
        cv.ReapOutcome.LANE_UNREADABLE,
    }


def test_the_liveness_gate_reads_the_launchers_real_marker(tmp_path: Path) -> None:
    """The form the real launcher actually emits — a log line, not a file.

    ⚠️ This is the arm that was missing when the module first shipped, and its
    absence made the whole reaper inert. Verified against
    `~/.claude/plugins/marketplaces/fable-orchestrator/scripts/run-lane.sh`:
    the lane subshell does `echo "EXIT: $?" >> "$LOG"`, and there is no
    `exit.marker` file anywhere in that script. A gate reading only the marker
    file returns False forever, so every lane stays NOT_SETTLED and the reaper
    reports nothing at all — silent rather than wrong, which is worse, because
    nothing reports silence.

    Both arms, and the negative one is the point: a log with output but no
    EXIT line is a lane still running (or group-killed), and must NOT be read.
    """
    run_dir = _lane(tmp_path / "run", settled=False)
    (run_dir / cv.LANE_LOG_FILENAME).write_text("thinking...\nstill working\n")
    assert cv.lane_is_settled(run_dir) is False

    (run_dir / cv.LANE_LOG_FILENAME).write_text("thinking...\nEXIT: 0\n")
    assert cv.lane_is_settled(run_dir) is True


def test_a_nonzero_exit_line_still_counts_as_settled(tmp_path: Path) -> None:
    """`EXIT: 1` means the CLI returned — settled, just unsuccessfully.

    The reaper's job is to decide whether the file is safe to READ; whether
    the run succeeded is the verdict's business. Conflating them would make a
    failed lane permanently unreapable, which is the stuck-forever shape the
    inverted defaults exist to prevent.
    """
    run_dir = _lane(tmp_path / "run", settled=False)
    (run_dir / cv.LANE_LOG_FILENAME).write_text("boom\nEXIT: 1\n")
    assert cv.lane_is_settled(run_dir) is True
