"""The Codex verdict contract (a JSON Schema) plus its reaper (#580).

The review lane runs `codex exec`, which returns a verdict the DAG turns into
an edge. Two halves, and they fail for opposite reasons:

**The contract is PROVIDER-enforced, not prompt-enforced.** OMC hand-rolls nine
type checks in its consumer because its Codex workers are persistent panes with
no schema hook. Our lane is not stuck there: `codex exec` 0.146.0 ships
``--output-schema <FILE>`` (the provider enforces the final response's shape)
and ``-o/--output-last-message <FILE>``. So :data:`VERDICT_SCHEMA` is the
contract, and it carries a ``schema_version`` — the field OMC's payload lacks,
"which is why a contract change there breaks silently" (#580).

**The consumer mechanics are ported from OMC verbatim**, because they are the
genuinely hard-won part and are transport-independent: a liveness gate so a
half-written file is never read, a compare-and-swap under a file lock
re-verifying status AND owner, a ``verdict.json`` -> ``verdict.processed.json``
rename for idempotency, and a typed reap-outcome enum.

⚠️ **TWO OMC DEFAULTS ARE DELIBERATELY INVERTED, and the reason is
operational.** OMC treats ``file_missing`` and ``parse_failed`` as warnings.
Under unattended operation that leaves the task stuck ``in_progress`` forever
with nobody to read the warning — so here they are **escalation edges**.

That inversion is not a guess. The #580 NEEDS-PROBE asked whether a
usage-limit-aborted run still writes its ``-o`` file, and the codex 0.146.0
binary answers it in the string sitting immediately beside the write path, both
in ``exec/src/lib.rs``::

    Warning: no last agent message; wrote empty content to <path>
    Failed to write last message file

An empty ``-o`` file is therefore not a hypothetical partial write — it is an
explicit code path. **"The file exists" is necessary but never sufficient**;
the consumer must validate CONTENT. Measured alongside it, six empirical arms
on the same binary: a successful run writes a schema-valid file (rc=0, the
positive control), while SIGINT (rc=1), SIGTERM (rc=143), SIGKILL (rc=137) and
two distinct graceful ``exit(1)`` paths (a bogus model, a bogus provider) each
left **no file at all**. So codex exits before the write on every abort that
could be induced, and both outcomes — absent file, present-but-empty file — are
escalation edges here.

⚠️ What that probe did NOT establish, stated rather than implied: whether a
*usage-limit* abort specifically takes the exit-before-write path or the
completed-with-no-message path. A usage limit cannot be induced on demand. It
does not change this module, because both outcomes already escalate — but a
future reader must not mistake the inference for a measurement.

Supervision is NOT in scope (#575 R4 assigns start/wait/reap to the
``fable-orchestrator`` plugin's ``run-lane.sh``, whose ``EXIT: <code>`` marker
this module reads as its settled signal). #580 adds the typed verdict and the
schema flags that script does not pass.
"""

from __future__ import annotations

import enum
import fcntl
import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = logging.getLogger(__name__)

# Bumped when the payload's SHAPE changes. A consumer that sees a version it
# does not know rejects rather than best-effort-parses: the whole reason this
# field exists is that OMC's versionless payload breaks silently on a contract
# change, which is indistinguishable from a model having a bad day.
SCHEMA_VERSION = 1

# Written by `codex exec -o`; consumed and renamed by :func:`reap`.
VERDICT_FILENAME = "verdict.json"
PROCESSED_FILENAME = "verdict.processed.json"
# Written by the LAUNCHER, not the model: the CAS re-verifies against this, so
# the facts it holds (owner, status) must not be something the model can state.
LANE_FILENAME = "lane.json"
# The settled signal, in the two forms it occurs in. The LOG form is what the
# real `run-lane.sh` emits (`echo "EXIT: $?" >> "$LOG"`); the marker file is
# the form a run dir can carry when a launcher writes one instead. Absence of
# both means still-running or group-killed (#575 R4) — either way, not settled.
EXIT_MARKER_FILENAME = "exit.marker"
LANE_LOG_FILENAME = "lane.log"
_EXIT_LINE_PREFIX = "EXIT: "
LOCK_FILENAME = ".reap.lock"

_IN_PROGRESS = "in_progress"
_REAPED = "reaped"


class Verdict(enum.Enum):
    """The three terminal review verdicts (#575 R7).

    Three, not two: `revise` is deliberately NOT collapsed into failed,
    because it maps to a different edge (reopen implement vs reopen research)
    and collapsing them discards the reviewer's whole distinction.
    """

    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


class Edge(enum.Enum):
    """What the DAG does next with the node that produced this verdict."""

    ADVANCE = "advance"
    REOPEN_IMPLEMENT = "reopen_implement"
    REOPEN_RESEARCH = "reopen_research"
    NEEDS_HUMAN = "needs_human"
    # Not a decision — the no-op a reaper returns when there was nothing to
    # decide (not settled yet, already processed, or not ours to consume).
    NONE = "none"


class ReapOutcome(enum.Enum):
    """The typed reap-outcome enum, ported from OMC.

    Typed rather than a bool/str pair so a new failure mode cannot be added
    without also being given an edge in :data:`OUTCOME_EDGES` — the gap that
    leaves a task stuck ``in_progress`` forever.
    """

    APPROVED = "approved"
    REVISE = "revise"
    REJECTED = "rejected"
    # --- the two INVERTED OMC defaults: escalations, not warnings ---
    FILE_MISSING = "file_missing"
    PARSE_FAILED = "parse_failed"
    # --- the CAS could not be evaluated at all ---
    LANE_UNREADABLE = "lane_unreadable"
    # --- no-ops: correct outcomes that decide nothing ---
    NOT_SETTLED = "not_settled"
    ALREADY_PROCESSED = "already_processed"
    OWNER_MISMATCH = "owner_mismatch"
    STATUS_MISMATCH = "status_mismatch"


# Every outcome maps to an edge. Exhaustive by construction and asserted as
# such in the tests: an unmapped outcome is how a node goes quiet forever.
#
# ⚠️ The three NEEDS_HUMAN rows ARE the inversion. OMC warns on the first two;
# `LANE_UNREADABLE` is ours — an absent lane record means the CAS cannot be
# evaluated, and assuming ownership would be the fail-OPEN reading of an
# absence. A revise/reject that exhausts its rework budget escalates too, but
# that is decided in :func:`edge_for`, not here, because it depends on the
# rework count rather than on the outcome alone.
OUTCOME_EDGES: dict[ReapOutcome, Edge] = {
    ReapOutcome.APPROVED: Edge.ADVANCE,
    ReapOutcome.REVISE: Edge.REOPEN_IMPLEMENT,
    ReapOutcome.REJECTED: Edge.REOPEN_RESEARCH,
    ReapOutcome.FILE_MISSING: Edge.NEEDS_HUMAN,
    ReapOutcome.PARSE_FAILED: Edge.NEEDS_HUMAN,
    ReapOutcome.LANE_UNREADABLE: Edge.NEEDS_HUMAN,
    ReapOutcome.NOT_SETTLED: Edge.NONE,
    ReapOutcome.ALREADY_PROCESSED: Edge.NONE,
    ReapOutcome.OWNER_MISMATCH: Edge.NONE,
    ReapOutcome.STATUS_MISMATCH: Edge.NONE,
}

_VERDICT_TO_OUTCOME: dict[Verdict, ReapOutcome] = {
    Verdict.APPROVE: ReapOutcome.APPROVED,
    Verdict.REVISE: ReapOutcome.REVISE,
    Verdict.REJECT: ReapOutcome.REJECTED,
}

# The contract itself. `additionalProperties: false` is what makes provider
# enforcement meaningful — without it a model may return the required keys plus
# anything, and a future contract change becomes undetectable. `schema_version`
# is `const` rather than merely `integer` so a version bump is a hard reject at
# the provider, not a soft one here.
VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "verdict", "rationale"],
    "properties": {
        "schema_version": {"type": "integer", "const": SCHEMA_VERSION},
        "verdict": {"type": "string", "enum": [v.value for v in Verdict]},
        "rationale": {"type": "string"},
    },
}


@dataclass(frozen=True)
class ParsedVerdict:
    """A verdict payload that satisfied the contract."""

    verdict: Verdict
    rationale: str


@dataclass(frozen=True)
class ReapResult:
    """One reap's typed outcome, the edge it implies, and why."""

    outcome: ReapOutcome
    edge: Edge
    detail: str
    verdict: ParsedVerdict | None = None


def write_schema(path: Path) -> Path:
    """Materialise :data:`VERDICT_SCHEMA` for ``codex exec --output-schema``.

    The Python dict is the single source of truth and this DERIVES the file the
    flag needs. A tracked JSON file beside the dict would be two sources of one
    truth, and the drift is silent — the model keeps validating against
    whichever copy the launcher happened to pass.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(VERDICT_SCHEMA, indent=2) + "\n")
    return path


def _decode(raw_text: str) -> tuple[dict[str, Any] | None, str]:
    """Text -> a JSON object, or the reason it is not one.

    Split from :func:`parse_verdict` so each half stays under ruff's
    return-count ceiling without a suppression — and the split is the real
    seam anyway: this half is about the TRANSPORT (did we get an object at
    all), the other about the CONTRACT (is the object the right shape).
    """
    if not raw_text.strip():
        return None, "empty file (codex writes one when a run produced no message)"
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, f"not valid JSON: {exc}"
    if not isinstance(data, dict):
        return None, f"payload is {type(data).__name__}, expected an object"
    return data, ""


def _validate_fields(data: dict[str, Any]) -> tuple[ParsedVerdict | None, str]:
    """A decoded object -> a verdict, or the reason it breaks the contract."""
    allowed = set(VERDICT_SCHEMA["properties"])
    extra = set(data) - allowed
    if extra:
        return None, f"unexpected property/properties: {sorted(extra)}"
    missing = set(VERDICT_SCHEMA["required"]) - set(data)
    if missing:
        return None, f"missing required field(s): {sorted(missing)}"
    version = data["schema_version"]
    if version != SCHEMA_VERSION:
        return None, (
            f"schema_version {version!r}, this consumer speaks {SCHEMA_VERSION}"
        )
    raw_verdict = data["verdict"]
    try:
        verdict = Verdict(raw_verdict)
    except ValueError:
        return None, (
            f"verdict {raw_verdict!r} is not one of {[v.value for v in Verdict]}"
        )
    rationale = data["rationale"]
    if not isinstance(rationale, str):
        return None, f"rationale is {type(rationale).__name__}, expected a string"
    return ParsedVerdict(verdict=verdict, rationale=rationale), ""


def parse_verdict(raw_text: str) -> tuple[ParsedVerdict | None, str]:
    """Validate one ``-o`` payload against the contract.

    Returns ``(verdict, "")`` on success and ``(None, why)`` on every failure,
    because the caller escalates on failure and an escalation with no reason is
    unactionable.

    Validated here rather than trusted from the provider on purpose: the
    provider enforces the shape of a *final response*, and this file may not
    contain one. Codex writes an empty file when a session produced no last
    agent message (`exec/src/lib.rs`), so the first thing this must survive is
    ``""``.
    """
    data, why = _decode(raw_text)
    if data is None:
        return None, why
    return _validate_fields(data)


def edge_for(verdict: Verdict, *, rework_count: int, max_rework: int) -> Edge:
    """Map a verdict to its edge, bounded by #573's rework budget.

    #575 R7: approve -> advance, revise -> reopen implement, reject -> reopen
    research. #573's ``max_rework`` (default 2) bounds the two REWORK edges
    only — an approved unit of work advances however many times it was
    reworked to get there, because the bound exists to stop an endless
    rework loop, and approval ends the loop by definition.
    """
    if verdict is Verdict.APPROVE:
        return Edge.ADVANCE
    if rework_count >= max_rework:
        return Edge.NEEDS_HUMAN
    return Edge.REOPEN_IMPLEMENT if verdict is Verdict.REVISE else Edge.REOPEN_RESEARCH


def lane_is_settled(run_dir: Path) -> bool:
    """The default liveness gate: has the lane finished writing?

    The signal is ``EXIT: <code>``, and it is accepted in BOTH the forms it
    occurs in — as a dedicated marker file, or as a line appended to the lane
    log.

    ⚠️ **The log form is the one the real launcher emits, and reading only the
    marker file was a defect this module shipped with.** Verified against
    `~/.claude/plugins/marketplaces/fable-orchestrator/scripts/run-lane.sh`:
    each lane runs in a backgrounded subshell that does
    ``echo "EXIT: $?" >> "$LOG"``, and its own header states the contract —
    *"appends 'EXIT: <code>' to LOG when the CLI exits on its own ... No EXIT
    line means the group was killed (watchdog or reap) before the CLI
    returned."* There is no `exit.marker` file anywhere in that script. A gate
    that looked only for one would have returned False forever, making every
    lane permanently NOT_SETTLED — the reaper would have been silent rather
    than wrong, which is worse, because nothing reports silence.

    Absence still means still-running OR group-killed, and this returns False
    for both, deliberately. A group-killed lane never wrote a verdict anyway
    (measured: SIGKILL leaves no file), so it reaches the reaper on a later
    tick as ``file_missing``, which escalates. Treating "no marker" as settled
    would instead read a file mid-write.

    ⚠️ Note the marker's own stated limit, inherited from the launcher: a grok
    lane that dies on an internal permission cancellation still exits 0. So
    `EXIT: 0` proves the CLI returned, never that it did the work — which is
    exactly why the verdict's CONTENT is validated rather than its presence.
    """
    if (run_dir / EXIT_MARKER_FILENAME).exists():
        return True
    try:
        return _EXIT_LINE_PREFIX in (run_dir / LANE_LOG_FILENAME).read_text()
    except OSError:
        return False


def _read_lane(run_dir: Path) -> dict[str, object] | None:
    """The launcher's lane record, or None when it cannot be read."""
    try:
        raw = (run_dir / LANE_FILENAME).read_text()
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _consume(run_dir: Path) -> None:
    """Rename the verdict aside so it is never processed twice.

    Runs for FAILING outcomes too. An escalating reap that left the file in
    place would re-read the same broken verdict every 60s and re-escalate
    forever — a warning storm in place of the single escalation the inverted
    default exists to produce.
    """
    source = run_dir / VERDICT_FILENAME
    if source.exists():
        source.replace(run_dir / PROCESSED_FILENAME)


def reap(
    run_dir: Path,
    *,
    expected_owner: str,
    rework_count: int,
    max_rework: int,
    is_settled: Callable[[Path], bool] | None = None,
) -> ReapResult:
    """Consume one lane's verdict, once, under a lock, and return its edge.

    The order is load-bearing and is OMC's:

    1. **Liveness gate first**, before any read of the verdict — a half-written
       file must never be parsed. Injectable for tests; defaults to
       :func:`lane_is_settled`.
    2. **Everything else under an exclusive flock**, so two ticks cannot both
       consume one verdict.
    3. **CAS: re-verify owner AND status** from the lane record *inside* the
       lock. Re-verifying outside it would be a check-then-act against a file
       another process may rewrite.
    4. **Consume by rename**, for idempotency.

    A lane that is not ours (owner or status mismatch) returns a NO-OP edge and
    **does not consume the file** — it is not ours to consume. Every other
    terminal path consumes, including the escalating ones.
    """
    gate = lane_is_settled if is_settled is None else is_settled
    if not gate(run_dir):
        return ReapResult(
            ReapOutcome.NOT_SETTLED,
            Edge.NONE,
            "lane has not written its exit marker — not read, to avoid a "
            "half-written verdict",
        )

    lock_path = run_dir / LOCK_FILENAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # "a", not "w": "w" truncates on open, zeroing the lockfile out from under
    # a process that already holds it (flock is advisory) — same reasoning as
    # `dag_tick.try_acquire_lock`.
    with lock_path.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return _reap_locked(
            run_dir,
            expected_owner=expected_owner,
            rework_count=rework_count,
            max_rework=max_rework,
        )


def _cas_check(
    run_dir: Path,
    lane: dict[str, object],
    *,
    expected_owner: str,
) -> ReapResult | None:
    """The compare-and-swap guard: is this lane ours, and still ours to reap?

    Returns a terminal :class:`ReapResult` when the reap must NOT proceed, or
    ``None`` to continue. Split out of :func:`_reap_locked` so each stays under
    ruff's return-count ceiling without a suppression; the seam is real — this
    is the CAS, the other half is the payload.

    ORDER MATTERS, and it is ownership -> idempotency -> status.

    Owner first: a lane that is not ours is not ours to report on at all.

    Idempotency SECOND, ahead of the status check, because a successful reap
    flips the lane out of ``in_progress`` itself — so on a re-run the status
    check would fire first and answer STATUS_MISMATCH, which is true but
    misleading. It reads as "someone else changed this lane" when the fact is
    "I already did this". Both are no-op edges, so this is a legibility fix,
    not a safety one; an operator debugging a stuck node needs the specific
    answer, and "already processed" is the one that ends the search.
    """
    owner = lane.get("owner")
    if owner != expected_owner:
        return ReapResult(
            ReapOutcome.OWNER_MISMATCH,
            OUTCOME_EDGES[ReapOutcome.OWNER_MISMATCH],
            f"lane is owned by {owner!r}, not {expected_owner!r} — left intact",
        )
    consumed = (
        not (run_dir / VERDICT_FILENAME).exists()
        and (run_dir / PROCESSED_FILENAME).exists()
    )
    if consumed:
        return ReapResult(
            ReapOutcome.ALREADY_PROCESSED,
            OUTCOME_EDGES[ReapOutcome.ALREADY_PROCESSED],
            "verdict was already consumed by an earlier reap",
        )
    status = lane.get("status")
    if status != _IN_PROGRESS:
        return ReapResult(
            ReapOutcome.STATUS_MISMATCH,
            OUTCOME_EDGES[ReapOutcome.STATUS_MISMATCH],
            f"lane status is {status!r}, not {_IN_PROGRESS!r} — left intact",
        )
    return None


def _read_payload(run_dir: Path) -> tuple[ParsedVerdict | None, ReapResult | None]:
    """Read + validate the verdict file, consuming it either way.

    Returns ``(verdict, None)`` on success or ``(None, failure)`` otherwise.
    Every failure path here CONSUMES the file, because leaving it would make
    the tick re-read the same broken verdict every 60s and re-escalate
    forever — a warning storm in place of the single escalation the inverted
    default exists to produce.
    """
    verdict_path = run_dir / VERDICT_FILENAME
    if not verdict_path.exists():
        return None, ReapResult(
            ReapOutcome.FILE_MISSING,
            OUTCOME_EDGES[ReapOutcome.FILE_MISSING],
            f"no {VERDICT_FILENAME} — the lane exited without writing one "
            "(measured: every induced codex abort leaves no file)",
        )
    try:
        raw_text = verdict_path.read_text()
    except OSError as exc:
        _consume(run_dir)
        return None, ReapResult(
            ReapOutcome.PARSE_FAILED,
            OUTCOME_EDGES[ReapOutcome.PARSE_FAILED],
            f"{VERDICT_FILENAME} could not be read: {exc}",
        )
    parsed, why = parse_verdict(raw_text)
    if parsed is None:
        _consume(run_dir)
        return None, ReapResult(
            ReapOutcome.PARSE_FAILED,
            OUTCOME_EDGES[ReapOutcome.PARSE_FAILED],
            f"{VERDICT_FILENAME} does not satisfy the contract: {why}",
        )
    return parsed, None


def _reap_locked(
    run_dir: Path,
    *,
    expected_owner: str,
    rework_count: int,
    max_rework: int,
) -> ReapResult:
    """The CAS + consume half of :func:`reap`, with the lock already held."""
    lane = _read_lane(run_dir)
    if lane is None:
        # Absent/unreadable lane record. Escalate rather than assume ownership:
        # reading an absence as permission is the fail-OPEN shape.
        _consume(run_dir)
        return ReapResult(
            ReapOutcome.LANE_UNREADABLE,
            OUTCOME_EDGES[ReapOutcome.LANE_UNREADABLE],
            f"{LANE_FILENAME} is missing or unreadable, so ownership and "
            "status cannot be verified",
        )
    refused = _cas_check(run_dir, lane, expected_owner=expected_owner)
    if refused is not None:
        return refused
    parsed, failure = _read_payload(run_dir)
    if parsed is None:
        return failure if failure is not None else _unreachable_payload()

    _consume(run_dir)
    _mark_reaped(run_dir, lane)
    edge = edge_for(parsed.verdict, rework_count=rework_count, max_rework=max_rework)
    outcome = _VERDICT_TO_OUTCOME[parsed.verdict]
    if edge is Edge.NEEDS_HUMAN:
        detail = (
            f"verdict={parsed.verdict.value} but rework budget is spent "
            f"({rework_count}/{max_rework}) -> {edge.value}: {parsed.rationale}"
        )
    else:
        detail = f"verdict={parsed.verdict.value} -> {edge.value}: {parsed.rationale}"
    return ReapResult(outcome, edge, detail, verdict=parsed)


def _unreachable_payload() -> ReapResult:
    """:func:`_read_payload` always pairs a `None` verdict with a failure.

    This exists so the type checker sees a total function without the caller
    asserting; it escalates rather than advancing, so if the invariant ever
    breaks the node is escalated to a human instead of silently advanced.
    """
    return ReapResult(
        ReapOutcome.PARSE_FAILED,
        OUTCOME_EDGES[ReapOutcome.PARSE_FAILED],
        "internal: verdict payload was neither parsed nor refused",
    )


def _mark_reaped(run_dir: Path, lane: dict[str, object]) -> None:
    """Complete the CAS: flip the lane record out of ``in_progress``.

    Best-effort — the rename above is what makes the reap idempotent, so a
    failure to write this back cannot double-process a verdict. It is the
    operator-visible half, not the correctness-bearing one.
    """
    try:
        (run_dir / LANE_FILENAME).write_text(json.dumps({**lane, "status": _REAPED}))
    except OSError as exc:
        logger.warning("codex-verdict: could not mark lane reaped: %s", exc)
