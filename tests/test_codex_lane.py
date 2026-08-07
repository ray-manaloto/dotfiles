"""Tests for the Codex review-lane producer (dotfiles_setup.codex_lane).

#613, the follow-up to #580. #580 built a complete, well-tested CONSUMER —
and nothing wrote its inputs, so the path was inert end to end. These tests
exist to pin the producer/consumer agreement, which is the thing unit tests of
either half structurally cannot see.

⭐ **The organising principle: assert through the real consumer, never against
a restated literal.** A test that checks the launcher wrote ``"EXIT: 0"`` into
``lane.log`` is a test of a string this file also contains — it agrees with
itself by construction and would keep passing if the reaper's gate changed. So
the liveness assertions call :func:`codex_verdict.lane_is_settled`, the path
assertions rebuild the path the way :func:`dag_tick.reap_codex_lanes` does, and
the round-trip test runs the real :func:`codex_verdict.reap`. That is the
independent source of truth ``tests/AGENTS.md`` asks for.

The one boundary that IS substituted is the ``codex`` subprocess, injected as a
``runner`` rather than patched (``tests/AGENTS.md`` § Mocking — inject at system
boundaries, never mock our own modules). The arm where that substitution is
removed and the real binary runs lives in ``tests/test_codex_lane_e2e.py``,
gated behind the ``codex_exec`` marker because it costs credits.
"""

from __future__ import annotations

import ast
import fcntl
import json
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codex_lane as cl
from dotfiles_setup import codex_verdict as cv
from dotfiles_setup import dag_tick

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

NODE_ID = "node-abc123"


def _request(*, cwd: Path, rework_count: int = 0) -> cl.LaneRequest:
    """One lane's inputs — the record `launch_lane` takes."""
    return cl.LaneRequest(
        node_id=NODE_ID,
        prompt="review this",
        cwd=cwd,
        rework_count=rework_count,
    )


def _valid_payload(verdict: str = "approve") -> str:
    """A payload that satisfies the contract, built from the contract itself."""
    return json.dumps(
        {
            "schema_version": cv.SCHEMA_VERSION,
            "verdict": verdict,
            "rationale": "looks right",
        }
    )


def _runner_writing(payload: str, *, exit_code: int = 0) -> Callable[..., int]:
    """A stand-in for `codex exec` that writes `-o` the way the real one does.

    Reads the output path out of the argv it is handed rather than being told
    it, so a launcher that stopped passing `-o` would break this runner instead
    of being silently tolerated.
    """

    def runner(argv: Sequence[str], *, prompt: str, cwd: Path) -> int:
        del prompt, cwd
        out = Path(argv[argv.index("-o") + 1])
        out.write_text(payload)
        return exit_code

    return runner


def _runner_writing_nothing(exit_code: int = 1) -> Callable[..., int]:
    """The measured abort shape: codex exits before writing its `-o` file."""

    def runner(argv: Sequence[str], *, prompt: str, cwd: Path) -> int:
        del argv, prompt, cwd
        return exit_code

    return runner


# ------------------------------------------------- the path the reaper reads


def test_the_run_dir_is_the_one_the_reaper_actually_scans(tmp_path: Path) -> None:
    """The producer's run dir must equal the consumer's, structurally.

    The expected value is rebuilt the way `reap_codex_lanes` builds it
    (`ctx.jobs_dir / node_id / CODEX_LANE_DIRNAME`), NOT from a `"codex-lane"`
    literal restated here — a restated literal would agree with a producer that
    had drifted away from the consumer, which is the entire defect #613 exists
    to close.
    """
    assert cl.lane_run_dir(tmp_path, NODE_ID) == (
        tmp_path / NODE_ID / dag_tick.CODEX_LANE_DIRNAME
    )


def test_the_producer_does_not_restate_the_consumers_dirname() -> None:
    """The dirname must be IMPORTED from the consumer, not duplicated.

    Two sources of one truth drift silently: the launcher keeps writing to a
    directory the reaper stopped scanning, and every lane goes quiet. Pinning
    identity (`is`-equal strings via the same object) is what makes the
    agreement structural rather than coincidental.
    """
    assert cl.LANE_DIRNAME is dag_tick.CODEX_LANE_DIRNAME


# ----------------------------------------------- what prepare_lane must write


def test_prepare_lane_writes_the_facts_the_cas_verifies(tmp_path: Path) -> None:
    """`owner` and `status` are the two fields the reaper's CAS re-checks.

    Asserted through `_read_lane`-shaped access on the real filename constant,
    because the CAS reads `lane.json` by that constant and nothing else.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID, rework_count=3)
    lane = json.loads((run_dir / cv.LANE_FILENAME).read_text())
    assert lane["owner"] == NODE_ID
    # Against the CONSUMER's constant, never a restated "in_progress" literal —
    # this file's own opening principle, which the first draft broke here.
    assert lane["status"] == cv.IN_PROGRESS
    assert lane["rework_count"] == 3


def test_the_producer_does_not_restate_the_consumers_status(tmp_path: Path) -> None:
    """The status the CAS compares must come FROM the consumer, like the dirname.

    ⭐ The #613 review's strongest finding, and both axes found it
    independently: the module argued this invariant in five lines of comment for
    ``"codex-lane"`` and then broke it eighteen lines later for
    ``"in_progress"``. The drift is identically silent — divergence makes every
    lane STATUS_MISMATCH, which is `Edge.NONE`, which the tick drops unless
    `--verbose`.

    ⚠️ **Asserted over the module's AST, and both halves of that are deliberate.**

    Not by identity: ``cl.IN_PROGRESS is cv.IN_PROGRESS`` is a check that can
    ONLY PASS, because CPython interns identifier-like string constants — a
    restated ``"in_progress"`` is the very same object as the consumer's. That
    assertion was written first and it survived the mutation that restates the
    literal, which is how this was caught.

    Not by grepping the text either: the first source-level version matched the
    COMMENT that explains this very invariant. Parsing drops comments entirely
    and lets docstrings be excluded by position, so the AST asks the only
    question that matters — does any *executable* expression in this module
    carry its own copy of the consumer's value?
    """
    tree = ast.parse(Path(cl.__file__).read_text())
    docstrings = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.FunctionDef | ast.ClassDef)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    restated = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and node.value == cv.IN_PROGRESS
        and node not in docstrings
    ]
    assert not restated, (
        f"the producer restated the consumer's status literal at line(s) "
        f"{[n.lineno for n in restated]} — reference codex_verdict.IN_PROGRESS"
    )

    lane = json.loads(
        (cl.prepare_lane(tmp_path, NODE_ID) / cv.LANE_FILENAME).read_text()
    )
    assert lane["status"] == cv.IN_PROGRESS


def test_the_written_status_is_the_one_the_cas_demands(tmp_path: Path) -> None:
    """Arm the previous test: a lane the CAS would REFUSE must be refusable.

    `prepare_lane` writing any other status would leave every lane
    STATUS_MISMATCH — a no-op edge, so the reaper would be silent rather than
    wrong. This drives the real CAS to prove the written status is accepted,
    and the sibling below proves the check discriminates.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.VERDICT_FILENAME).write_text(_valid_payload())
    cl.record_exit(run_dir, 0)
    result = cv.reap(run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.APPROVED


def test_the_cas_arm_discriminates_on_a_wrong_status(tmp_path: Path) -> None:
    """The control arm for the test above: a wrong status IS refused.

    Without this, `test_the_written_status_is_the_one_the_cas_demands` is a
    check that can only pass — it would stay green if the CAS stopped looking
    at status at all.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    lane = json.loads((run_dir / cv.LANE_FILENAME).read_text())
    (run_dir / cv.LANE_FILENAME).write_text(json.dumps({**lane, "status": "queued"}))
    (run_dir / cv.VERDICT_FILENAME).write_text(_valid_payload())
    cl.record_exit(run_dir, 0)
    result = cv.reap(run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2)
    assert result.outcome is cv.ReapOutcome.STATUS_MISMATCH


def test_the_rework_count_reaches_the_ticks_reader(tmp_path: Path) -> None:
    """The counter must round-trip through `dag_tick.read_rework_count`.

    That reader defaults a missing/unparsable count to 0 — the permissive
    direction — so a launcher that wrote the field under any other name would
    silently un-bound the rework budget instead of failing.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID, rework_count=2)
    assert dag_tick.read_rework_count(run_dir) == 2


def test_prepare_lane_materialises_the_schema_the_provider_enforces(
    tmp_path: Path,
) -> None:
    """⭐ The call site `write_schema` did not have.

    Measured at #613 filing: `write_schema` had ZERO production callers, so the
    provider-enforced half of #580 was a dict and an uncalled writer, and every
    guarantee credited to provider enforcement actually rested on
    `parse_verdict` alone. This is the test that keeps it wired.

    Compared against `VERDICT_SCHEMA` itself rather than a copied literal: the
    Python dict is the single source of truth and the file is DERIVED, so a
    literal here would be the second source the derivation exists to avoid.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    written = json.loads((run_dir / cl.SCHEMA_FILENAME).read_text())
    assert written == cv.VERDICT_SCHEMA


# ------------------------------------- the relaunch race (a stale run dir)


def test_prepare_lane_clears_a_stale_exit_signal(tmp_path: Path) -> None:
    """⭐ A rework round must not inherit the previous round's EXIT line.

    `lane_is_settled` returns True the instant `lane.log` contains `EXIT: `. A
    relaunch into a dirty run dir would therefore be reaped IMMEDIATELY, before
    the new `codex exec` had written anything — the reaper would read round 1's
    leftovers, or escalate `file_missing` on a lane that was still running.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    cl.record_exit(run_dir, 0)
    assert cv.lane_is_settled(run_dir), "control: the dirty state really is settled"

    cl.prepare_lane(tmp_path, NODE_ID, rework_count=1)
    assert not cv.lane_is_settled(run_dir)


def test_prepare_lane_clears_a_stale_marker_file_too(tmp_path: Path) -> None:
    """The gate accepts BOTH settled forms, so clearing must cover both.

    `lane_is_settled` checks `exit.marker` before `lane.log`. A producer that
    truncated only the log would leave a marker file written by some other
    launcher (the plugin's, a future one) settling every relaunch instantly.
    """
    run_dir = cl.lane_run_dir(tmp_path, NODE_ID)
    run_dir.mkdir(parents=True)
    (run_dir / cv.EXIT_MARKER_FILENAME).write_text("EXIT: 0\n")
    assert cv.lane_is_settled(run_dir), "control: a marker file really does settle"

    cl.prepare_lane(tmp_path, NODE_ID)
    assert not cv.lane_is_settled(run_dir)


def test_prepare_lane_clears_a_consumed_verdict_from_the_previous_round(
    tmp_path: Path,
) -> None:
    """A leftover `verdict.processed.json` must not read as ALREADY_PROCESSED.

    The CAS calls a lane consumed when `verdict.json` is absent AND
    `verdict.processed.json` is present. On a rework relaunch that pair is
    exactly what round 1 leaves behind, so a lane whose new run failed to write
    a verdict would report "already processed" (a NO-OP edge) instead of
    escalating `file_missing`. Silence in place of an escalation.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.PROCESSED_FILENAME).write_text(_valid_payload())

    cl.prepare_lane(tmp_path, NODE_ID, rework_count=1)
    cl.record_exit(run_dir, 1)
    result = cv.reap(run_dir, expected_owner=NODE_ID, rework_count=1, max_rework=2)
    assert result.outcome is cv.ReapOutcome.FILE_MISSING
    assert result.edge is cv.Edge.NEEDS_HUMAN


def test_a_relaunch_carries_the_previous_rounds_rework_count(tmp_path: Path) -> None:
    """⭐ A relaunch must not silently reset #573's budget.

    `prepare_lane` rewrites the very file that holds the count, so a 0 default
    destroyed it on every round: a `revise` reopens implement, the supervisor
    relaunches, the counter goes back to 0, and the loop `max_rework` exists to
    bound never terminates. Found by the #613 review; the round-trip test could
    not see it, because that test supplies the count itself.
    """
    cl.prepare_lane(tmp_path, NODE_ID, rework_count=2)
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    assert dag_tick.read_rework_count(run_dir) == 2


def test_an_explicit_rework_count_still_overrides(tmp_path: Path) -> None:
    """Control for the carry-forward: an explicit value is not ignored.

    Without this, the test above would pass on a `prepare_lane` that had
    stopped honouring its argument entirely.
    """
    cl.prepare_lane(tmp_path, NODE_ID, rework_count=2)
    run_dir = cl.prepare_lane(tmp_path, NODE_ID, rework_count=0)
    assert dag_tick.read_rework_count(run_dir) == 0


def test_a_fresh_lane_starts_at_zero(tmp_path: Path) -> None:
    """And carrying forward from nothing is 0, not an error."""
    assert dag_tick.read_rework_count(cl.prepare_lane(tmp_path, NODE_ID)) == 0


# ------------------------------------ #616: the relaunch SPENDS a rework round


def test_a_relaunch_after_a_revise_spends_a_rework_round(tmp_path: Path) -> None:
    """⭐ #616's headline: carrying the count forward is not enough.

    #613 stopped the producer DESTROYING the counter and left incrementing to
    "the supervisor". Nothing was the supervisor — `reap_codex_lanes` only
    prints the edge — so the count carried forward unchanged forever, the
    `rework_count >= max_rework` bound never tripped, and #573's budget was
    written, read, and unspendable.

    The evidence is the previous round's CONSUMED verdict, which is the record
    that a round completed and produced an edge.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.PROCESSED_FILENAME).write_text(_valid_payload("revise"))

    cl.prepare_lane(tmp_path, NODE_ID)
    assert dag_tick.read_rework_count(run_dir) == 1


def test_a_relaunch_after_a_reject_spends_a_round_too(tmp_path: Path) -> None:
    """`reject` reopens research — a different edge, the same spent round.

    Both rework edges are bounded by `edge_for`, so both must be counted; a
    producer that charged only `revise` would leave a reject loop unbounded.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.PROCESSED_FILENAME).write_text(_valid_payload("reject"))

    cl.prepare_lane(tmp_path, NODE_ID)
    assert dag_tick.read_rework_count(run_dir) == 1


def test_a_relaunch_after_an_approve_spends_nothing(tmp_path: Path) -> None:
    """⭐ The control arm. Without it every test above passes on `carried + 1`.

    A producer that incremented on EVERY relaunch would satisfy the three
    charging tests and be wrong: `edge_for` deliberately does not bound
    `approve`, because approval ends the loop the bound exists to stop. An
    approved unit of work advances however many rounds it took to get there.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.PROCESSED_FILENAME).write_text(_valid_payload("approve"))

    cl.prepare_lane(tmp_path, NODE_ID)
    assert dag_tick.read_rework_count(run_dir) == 0


def test_an_unparsable_previous_verdict_spends_nothing(tmp_path: Path) -> None:
    """The permissive direction, matching `read_rework_count`'s.

    A payload that breaks the contract reaped as `parse_failed` -> `needs_human`,
    so the automatic loop never relaunched from it. Charging a round here would
    bill a lane that never reworked, on evidence that is by definition unread.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.PROCESSED_FILENAME).write_text("{not json at all")

    cl.prepare_lane(tmp_path, NODE_ID)
    assert dag_tick.read_rework_count(run_dir) == 0


def test_a_verdict_that_was_never_reaped_spends_nothing(tmp_path: Path) -> None:
    """An UNCONSUMED `verdict.json` is not evidence a round completed.

    The rename to `verdict.processed.json` is what marks a verdict as read and
    turned into an edge. A producer that counted `verdict.json` too would charge
    a round for a result nobody has looked at — and would race the reaper for
    the same file, which is the exact hazard the lock here exists to avoid.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.VERDICT_FILENAME).write_text(_valid_payload("revise"))

    cl.prepare_lane(tmp_path, NODE_ID)
    assert dag_tick.read_rework_count(run_dir) == 0


def test_the_increment_is_idempotent_without_a_new_round(tmp_path: Path) -> None:
    """⭐ Two `prepare_lane` calls with no round between them charge ONCE.

    Not by a flag and not by remembering: the clearing loop unlinks the very
    file the increment reads, under the same lock, so the evidence is consumed
    by the act of acting on it. A supervisor that retried a failed launch would
    otherwise burn the whole budget without a single review having run.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.PROCESSED_FILENAME).write_text(_valid_payload("revise"))

    cl.prepare_lane(tmp_path, NODE_ID)
    assert dag_tick.read_rework_count(run_dir) == 1, "control: the first one charged"
    cl.prepare_lane(tmp_path, NODE_ID)
    assert dag_tick.read_rework_count(run_dir) == 1


def test_an_explicit_rework_count_is_not_incremented_on_top(tmp_path: Path) -> None:
    """An explicit value is a STATEMENT of the count, not a base to add to.

    `--rework-count` exists so an operator (and the e2e arm) can place a lane
    at a known point in its budget. A producer that added the increment on top
    would make that value mean something different depending on what happened
    to be on disk.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    (run_dir / cv.PROCESSED_FILENAME).write_text(_valid_payload("revise"))

    cl.prepare_lane(tmp_path, NODE_ID, rework_count=5)
    assert dag_tick.read_rework_count(run_dir) == 5


def test_a_revise_loop_really_reaches_the_bound(tmp_path: Path) -> None:
    """⭐⭐ The whole #616 claim, with only the codex PROCESS substituted.

    Launch -> reap -> relaunch -> reap -> relaunch -> reap, driving the real
    producer and the real reaper, and the count is produced by the code under
    test rather than supplied by the fixture. That is the distinction #613 was
    filed over: the substituted thing (what the model says) is not the thing
    being measured (what the counter does with it).

    The bound's own control arm is inside the sequence: rounds 1 and 2 return a
    REOPEN edge under the SAME `max_rework` that escalates round 3, so
    `needs_human` at the end is reachable only because the count actually rose.
    A producer that never incremented yields `[reopen, reopen, reopen]`.

    The paid version of this — the same loop with a real `codex exec` — is in
    `tests/test_codex_lane_e2e.py`.
    """
    max_rework = 2
    revise = _runner_writing(_valid_payload("revise"))
    counts: list[int] = []
    edges: list[cv.Edge] = []

    for _round in range(max_rework + 1):
        result = cl.launch_lane(
            tmp_path,
            cl.LaneRequest(node_id=NODE_ID, prompt="review this", cwd=tmp_path),
            runner=revise,
        )
        count = dag_tick.read_rework_count(result.run_dir)
        counts.append(count)
        edges.append(
            cv.reap(
                result.run_dir,
                expected_owner=NODE_ID,
                rework_count=count,
                max_rework=max_rework,
            ).edge
        )

    assert counts == [0, 1, 2], "the producer did not spend the budget"
    assert edges == [
        cv.Edge.REOPEN_IMPLEMENT,
        cv.Edge.REOPEN_IMPLEMENT,
        cv.Edge.NEEDS_HUMAN,
    ]


# ----------------------------------------------- the reaper's lock, honoured


def test_prepare_lane_waits_for_the_reapers_lock(tmp_path: Path) -> None:
    """⭐ Clearing an UNLOCKED run dir races the reaper and corrupts a good edge.

    `codex_verdict.reap` does everything under an exclusive flock on
    `.reap.lock` so "two ticks cannot both consume one verdict" — but a lock
    only excludes writers that take it. The losing interleaving found by the
    #613 review: a tick passes the liveness gate (outside the lock, by design),
    acquires the lock, and is inside `_read_payload` when a relaunch unlinks
    `verdict.json` from under it. The reap then answers `file_missing` ->
    `needs_human` for a lane that had APPROVED.

    Driven against the REAL lock file the reaper uses, from a second thread.
    The negative assertion is the safe direction: if the lock works the thread
    can never proceed while this test holds it, so a slow machine cannot make
    this flake — it can only make it pass for the wrong reason, which the
    post-release assertion then catches.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID, rework_count=7)
    started = threading.Event()
    done = threading.Event()

    def relaunch() -> None:
        started.set()
        cl.prepare_lane(tmp_path, NODE_ID, rework_count=0)
        done.set()

    with (run_dir / cv.LOCK_FILENAME).open("a") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX)
        worker = threading.Thread(target=relaunch)
        worker.start()
        started.wait(timeout=5)
        assert not done.wait(timeout=0.5), "prepare_lane ran without the lock"
        assert dag_tick.read_rework_count(run_dir) == 7, "lane rewritten under us"

    worker.join(timeout=10)
    assert done.is_set(), "prepare_lane never completed after the lock released"
    assert dag_tick.read_rework_count(run_dir) == 0


# ------------------------------------------------------ the invocation form


def test_the_argv_passes_both_output_flags(tmp_path: Path) -> None:
    """#613's headline requirement: `--output-schema` AND `-o`, together.

    Either alone is a half-wired lane. Without `--output-schema` the contract
    is prompt-enforced (what #580 explicitly rejected); without `-o` the
    verdict is never written down and every lane escalates `file_missing`.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    argv = cl.build_codex_argv(run_dir)
    assert argv[argv.index("--output-schema") + 1] == str(run_dir / cl.SCHEMA_FILENAME)
    assert argv[argv.index("-o") + 1] == str(run_dir / cv.VERDICT_FILENAME)


def test_the_argv_reads_its_prompt_from_stdin(tmp_path: Path) -> None:
    """The trailing `-` is what makes the prompt a stdin read.

    `codex exec --help` (0.146.0): instructions come from stdin when the prompt
    is absent "or if `-` is used". Passing a large review prompt as an argv
    element instead would risk ARG_MAX (`.claude/rules/ai-cli-invocation.md`).
    """
    argv = cl.build_codex_argv(cl.prepare_lane(tmp_path, NODE_ID))
    assert argv[0] == "codex"
    assert argv[1] == "exec"
    assert argv[-1] == "-"


def test_the_argv_sandboxes_the_review_lane_read_only(tmp_path: Path) -> None:
    """A review lane reads code and returns a verdict; it must not write.

    `read-only` is one of the three values `codex exec --sandbox` accepts on
    0.146.0, and it is the one `.claude/rules/ai-cli-invocation.md` prescribes
    for the research/debate shape a review is.
    """
    argv = cl.build_codex_argv(cl.prepare_lane(tmp_path, NODE_ID))
    assert argv[argv.index("--sandbox") + 1] == "read-only"


def test_a_model_override_is_passed_through_when_given(tmp_path: Path) -> None:
    """And is absent otherwise, so codex's own configured default applies."""
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    assert "--model" not in cl.build_codex_argv(run_dir)
    assert cl.build_codex_argv(run_dir, model="gpt-5.6")[-3:-1] == [
        "--model",
        "gpt-5.6",
    ]


# ------------------------------------------------------ settling the lane


def test_record_exit_writes_the_form_the_liveness_gate_reads(tmp_path: Path) -> None:
    """Asserted through the real gate, not against an `"EXIT: "` literal.

    The launcher and the gate must agree on ONE form. #580 shipped a gate that
    read only `exit.marker` while the real launcher appended `EXIT: <code>` to
    a log — a mismatch that made every lane permanently NOT_SETTLED, and the
    reaper silent rather than wrong. Driving the real predicate is what would
    have caught it.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    assert not cv.lane_is_settled(run_dir), "control: an unsettled lane reads False"
    cl.record_exit(run_dir, 0)
    assert cv.lane_is_settled(run_dir)


def test_record_exit_preserves_the_codex_exit_code(tmp_path: Path) -> None:
    """The recorded code must be codex's, so an abort is legible afterwards.

    `EXIT: 0` proves only that the CLI returned, never that it did the work —
    which is why the verdict's CONTENT is validated too. But a non-zero code is
    the one artifact that distinguishes "aborted" from "ran and said nothing"
    when an operator reads the log later.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    cl.record_exit(run_dir, 137)
    assert "EXIT: 137" in (run_dir / cv.LANE_LOG_FILENAME).read_text()


def test_a_launcher_crash_still_settles_the_lane(tmp_path: Path) -> None:
    """⭐ The fail-LOUD direction: an exception must not leave a silent lane.

    A launcher that died between writing `lane.json` and recording an exit
    would leave the lane `in_progress` with no settled signal — NOT_SETTLED
    forever, reported by nobody. Settling from a `finally` converts that into
    `file_missing` -> `needs_human`, which is the same inversion #580 chose for
    the two OMC defaults, applied to the producer.
    """

    def exploding_runner(argv: Sequence[str], *, prompt: str, cwd: Path) -> int:
        del argv, prompt, cwd
        message = "codex could not be spawned"
        raise OSError(message)

    with pytest.raises(OSError, match="could not be spawned"):
        cl.launch_lane(tmp_path, _request(cwd=tmp_path), runner=exploding_runner)

    run_dir = cl.lane_run_dir(tmp_path, NODE_ID)
    assert cv.lane_is_settled(run_dir)
    result = cv.reap(run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2)
    assert result.edge is cv.Edge.NEEDS_HUMAN


def test_the_crash_arm_is_armed(tmp_path: Path) -> None:
    """Control for the test above: a lane NOT launched is not settled.

    Without this, the crash test could pass on a `lane_is_settled` that had
    started returning True unconditionally.
    """
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    assert not cv.lane_is_settled(run_dir)


# ------------------------------------------- launcher -> reaper, round trip


def test_a_launched_lane_is_reaped_into_an_advance_edge(tmp_path: Path) -> None:
    """⭐ The integration #580 could not have: real launcher, real reaper.

    Both halves are the shipped code; only the `codex` process is substituted,
    and the substitute learns its output path FROM the argv rather than being
    told it. That is the difference from #580's fixtures, which wrote the
    artifacts the code reads and so could not disagree with it.

    The genuinely-real arm — the actual binary — is `test_codex_lane_e2e.py`.
    """
    result = cl.launch_lane(
        tmp_path,
        _request(cwd=tmp_path),
        runner=_runner_writing(_valid_payload("approve")),
    )
    assert result.exit_code == 0

    reaped = cv.reap(
        result.run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2
    )
    assert reaped.outcome is cv.ReapOutcome.APPROVED
    assert reaped.edge is cv.Edge.ADVANCE


@pytest.mark.parametrize(
    ("verdict", "expected_edge"),
    [
        ("approve", cv.Edge.ADVANCE),
        ("revise", cv.Edge.REOPEN_IMPLEMENT),
        ("reject", cv.Edge.REOPEN_RESEARCH),
    ],
)
def test_every_verdict_survives_the_round_trip(
    tmp_path: Path, verdict: str, expected_edge: cv.Edge
) -> None:
    """All three verdicts, end to end through the producer.

    Parametrized over the three rather than asserting the happy one, because
    #575 R7's whole point is that `revise` is NOT collapsed into failed — a
    producer that mangled the payload would show up on one row only.
    """
    result = cl.launch_lane(
        tmp_path,
        _request(cwd=tmp_path),
        runner=_runner_writing(_valid_payload(verdict)),
    )
    reaped = cv.reap(
        result.run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2
    )
    assert reaped.edge is expected_edge


def test_an_aborted_codex_run_escalates_through_the_round_trip(
    tmp_path: Path,
) -> None:
    """The measured abort shape: no `-o` file at all.

    Six arms on the 0.146.0 binary (#580) found SIGINT/SIGTERM/SIGKILL and two
    graceful `exit(1)` paths each left NO file — codex exits before the write.
    The producer must still settle the lane so that absence is REPORTED.
    """
    result = cl.launch_lane(
        tmp_path,
        _request(cwd=tmp_path),
        runner=_runner_writing_nothing(exit_code=137),
    )
    assert result.exit_code == 137

    reaped = cv.reap(
        result.run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2
    )
    assert reaped.outcome is cv.ReapOutcome.FILE_MISSING
    assert reaped.edge is cv.Edge.NEEDS_HUMAN


def test_an_empty_output_file_escalates_through_the_round_trip(
    tmp_path: Path,
) -> None:
    """Codex's explicit "wrote empty content" path, driven through the producer.

    "The file exists" is necessary but never sufficient — `exec/src/lib.rs`
    warns and writes an EMPTY file when a run produced no last agent message.
    """
    result = cl.launch_lane(
        tmp_path,
        _request(cwd=tmp_path),
        runner=_runner_writing(""),
    )
    reaped = cv.reap(
        result.run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2
    )
    assert reaped.outcome is cv.ReapOutcome.PARSE_FAILED
    assert reaped.edge is cv.Edge.NEEDS_HUMAN


def test_a_spent_rework_budget_escalates_a_revise(tmp_path: Path) -> None:
    """#573's bound, driven from the count the PRODUCER wrote.

    The launcher writes `rework_count`; `dag_tick.read_rework_count` reads it;
    `edge_for` bounds on it. This is the only test that exercises all three,
    which is what makes the budget real rather than a parameter tests pass by
    hand.
    """
    result = cl.launch_lane(
        tmp_path,
        _request(cwd=tmp_path, rework_count=2),
        runner=_runner_writing(_valid_payload("revise")),
    )
    reaped = cv.reap(
        result.run_dir,
        expected_owner=NODE_ID,
        rework_count=dag_tick.read_rework_count(result.run_dir),
        max_rework=2,
    )
    assert reaped.edge is cv.Edge.NEEDS_HUMAN


def test_the_rework_bound_arm_is_armed(tmp_path: Path) -> None:
    """Control: the same revise verdict below budget reopens instead."""
    result = cl.launch_lane(
        tmp_path,
        _request(cwd=tmp_path, rework_count=1),
        runner=_runner_writing(_valid_payload("revise")),
    )
    reaped = cv.reap(
        result.run_dir,
        expected_owner=NODE_ID,
        rework_count=dag_tick.read_rework_count(result.run_dir),
        max_rework=2,
    )
    assert reaped.edge is cv.Edge.REOPEN_IMPLEMENT


def test_a_lane_launched_for_one_node_is_not_reaped_by_another(
    tmp_path: Path,
) -> None:
    """The owner the producer writes is the one the CAS refuses on mismatch.

    Ownership is a launcher fact precisely so the model cannot state it; this
    proves the launcher states it in the form the CAS compares against.
    """
    result = cl.launch_lane(
        tmp_path,
        _request(cwd=tmp_path),
        runner=_runner_writing(_valid_payload()),
    )
    reaped = cv.reap(
        result.run_dir, expected_owner="some-other-node", rework_count=0, max_rework=2
    )
    assert reaped.outcome is cv.ReapOutcome.OWNER_MISMATCH
    assert (result.run_dir / cv.VERDICT_FILENAME).exists(), "not ours to consume"


# ------------------------------------------------- through the tick itself


def test_the_tick_reports_a_lane_this_producer_launched(tmp_path: Path) -> None:
    """⭐ Producer -> `reap_codex_lanes` -> a report line, with nothing faked.

    The last link. `reap_codex_lanes` scans `ctx.jobs_dir` for run dirs; this
    proves the directory the producer creates is one the TICK finds, which no
    test of either module alone can establish.
    """
    cl.launch_lane(
        tmp_path,
        _request(cwd=tmp_path),
        runner=_runner_writing(_valid_payload("approve")),
    )
    ctx = _tick_context(tmp_path)
    classified = dag_tick.ClassifiedNode(
        node_id=NODE_ID,
        node_class=dag_tick.NodeClass.ALIVE,
        pid_alive=True,
        state_age_s=1.0,
    )
    lines = dag_tick.reap_codex_lanes([classified], ctx)
    assert len(lines) == 1
    assert "edge=advance" in lines[0]


def test_the_tick_arm_is_armed(tmp_path: Path) -> None:
    """Control: a node the producer never launched for produces no line.

    Without this, the test above passes on a `reap_codex_lanes` that emitted a
    line for every node regardless of whether a lane existed.
    """
    ctx = _tick_context(tmp_path)
    classified = dag_tick.ClassifiedNode(
        node_id="never-launched",
        node_class=dag_tick.NodeClass.ALIVE,
        pid_alive=True,
        state_age_s=1.0,
    )
    assert dag_tick.reap_codex_lanes([classified], ctx) == []


def test_a_node_with_no_job_directory_is_warned_about(tmp_path: Path) -> None:
    """⭐ A typo'd `--node` would otherwise be paid for and never read.

    `reap_codex_lanes` iterates the CENSUS, not the filesystem, while
    `prepare_lane` does `mkdir(parents=True)`. Together, `--node nod-abc123`
    creates a lane, burns a real `codex exec` into it, settles it, and no tick
    ever looks there — no error, no edge, no line. That is the exact silence
    #613 was filed about, which the producer must not reproduce (#613 review).
    """
    assert cl.warn_if_node_unknown(tmp_path, "typo-node") is True


def test_the_unknown_node_warning_discriminates(tmp_path: Path) -> None:
    """Control: a node that DOES have a job directory is not warned about.

    Without this, the test above passes on a function that warns
    unconditionally — which would train an operator to ignore it.
    """
    (tmp_path / NODE_ID).mkdir()
    assert cl.warn_if_node_unknown(tmp_path, NODE_ID) is False


def _tick_context(jobs_dir: Path) -> dag_tick.TickContext:
    """A `TickContext` scoped to `tmp_path` — injected, never monkeypatched."""
    return dag_tick.TickContext(
        claude_bin="/nonexistent/claude",
        cwd=str(jobs_dir),
        jobs_dir=jobs_dir,
        daemon_dir=jobs_dir / "daemon",
        lock_path=jobs_dir / "tick.lock",
        stall_after_s=dag_tick.DEFAULT_STALL_AFTER_SECONDS,
        max_age_s=dag_tick.DEFAULT_MAX_AGE_SECONDS,
        max_rework=dag_tick.DEFAULT_MAX_REWORK,
        dry_run=False,
        verbose=False,
    )
