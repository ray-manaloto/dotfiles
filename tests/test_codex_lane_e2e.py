"""⭐ The #613 end-to-end arm: real launcher -> real `codex exec` -> real reaper.

**Gated, not silently skipped.** Every test is marked ``codex_exec``, which the
root ``pytest.ini`` deselects by default, so ``mise run test`` and CI never pay
for it. ``mise run codex-lane-e2e`` passes ``-m codex_exec`` to re-select (last
``-m`` wins). It costs real credits per run — that is the reason for the gate,
and the reason it is a handful of tests rather than a matrix.

**Why this file has to exist.** #580 shipped a complete, well-tested consumer
and #613 exists because nothing wrote its inputs. Every #580 test passed because
its fixtures wrote the artifacts the code reads — a closed loop touching nothing
real (``probes-need-a-control-arm.md`` rule 8: arm the FIXTURE, not just the
probe). ``tests/test_codex_lane.py`` closes most of that by driving the real
reaper, but it still substitutes the ``codex`` process. Exactly one question
survives that substitution, and only a real call can answer it:

    Does `codex exec --output-schema` actually make the provider return a
    payload this contract accepts?

Every guarantee credited to *provider* enforcement rests on that, and nothing
short of the real binary tests it. If this file goes red while
``test_codex_lane.py`` stays green, the answer changed — the flag's behaviour,
the schema dialect it accepts, or the model's compliance — and the fix is here,
not in the consumer.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codex_lane as cl
from dotfiles_setup import codex_verdict as cv
from dotfiles_setup import dag_tick

pytestmark = pytest.mark.codex_exec

NODE_ID = "e2e-node"

# Small and unambiguous on purpose. The subject under test is the TRANSPORT —
# whether a schema-constrained call round-trips into an edge — not the model's
# reviewing judgement, so the prompt must not be something a reasonable model
# could answer either way. A borderline prompt would make this test flaky for a
# reason that has nothing to do with the code it guards.
_PROMPT = (
    "You are a code reviewer returning a structured verdict.\n"
    "The change under review is: `return a + b` in a function documented as "
    "'returns the sum of a and b'.\n"
    "It is correct and complete. Respond with verdict `approve`.\n"
)


def _request(node_id: str = NODE_ID) -> cl.LaneRequest:
    """One real lane's inputs, run from the repo root so codex's git check passes."""
    return cl.LaneRequest(
        node_id=node_id,
        prompt=_PROMPT,
        cwd=Path(__file__).parent.parent,
    )


def _require_codex() -> None:
    """Skip when the CLI is absent — a missing tool is not a failing contract.

    Distinct from the marker gate: the marker says "do not run this by
    default", this says "you asked to run it and the tool is not here". Both
    are needed, and conflating them is how a paid test silently stops running.
    """
    if shutil.which(cl.CODEX_BIN) is None:
        pytest.skip(f"{cl.CODEX_BIN} not on PATH — codex_exec needs the real CLI")


@pytest.fixture(scope="module")
def launched(tmp_path_factory: pytest.TempPathFactory) -> cl.LaunchResult:
    """ONE real launch, shared by the tests that assert about the same artifact.

    Module-scoped on purpose (#613 review): the raw-payload assertions and the
    reap assertions are independent questions about a SINGLE `codex exec`
    result, and paying twice for it contradicts this file's own stated reason
    for being small. The control-arm test below is NOT folded in here — that one
    must be a second, differently-configured call, which is the point of it.

    ⚠️ Read-only for consumers: `cv.reap` renames `verdict.json` aside, so the
    reaping test must run after the payload test reads it. They are ordered in
    the file accordingly, and the payload test asserts nothing that reaping
    changes.
    """
    _require_codex()
    return cl.launch_lane(tmp_path_factory.mktemp("codex-lane-e2e"), _request())


def test_the_provider_really_constrains_the_payload_shape(
    launched: cl.LaunchResult,
) -> None:
    """⭐ The one claim only a real call can settle.

    `parse_verdict` would catch a non-conforming payload anyway — which is
    exactly why this must be checked separately. If `--output-schema` silently
    stopped constraining anything, the consumer's validation would keep the
    system CORRECT while the "provider-enforced, not prompt-enforced" claim
    #580 is built on quietly became false. Asserting the raw payload BEFORE the
    consumer touches it is what distinguishes the two.

    Every field is checked against `VERDICT_SCHEMA` rather than a restated
    literal, so a contract change updates this test by construction.
    """
    result = launched
    assert result.exit_code == 0, "codex exec did not exit cleanly"
    verdict_text = (result.run_dir / cv.VERDICT_FILENAME).read_text()
    assert verdict_text.strip(), (
        "codex wrote an EMPTY -o file — its explicit 'no last agent message' "
        "path. The lane still escalates, but the transport did not work."
    )
    payload = json.loads(verdict_text)

    assert set(payload) <= set(cv.VERDICT_SCHEMA["properties"]), (
        f"provider returned properties outside the schema: "
        f"{sorted(set(payload) - set(cv.VERDICT_SCHEMA['properties']))} — "
        "`additionalProperties: false` is not being enforced"
    )
    assert set(cv.VERDICT_SCHEMA["required"]) <= set(payload)
    assert payload["schema_version"] == cv.SCHEMA_VERSION
    assert payload["verdict"] in {v.value for v in cv.Verdict}


def test_a_real_codex_call_round_trips_into_an_advance_edge(
    launched: cl.LaunchResult,
) -> None:
    """The whole path, with nothing substituted.

    Launcher writes the lane record and the derived schema, the real `codex
    exec` returns a provider-constrained payload, the real reaper validates it
    under the lock and maps it to an edge. This is the assertion #613 was filed
    to make possible.

    ⭐ It ends at :func:`dag_tick.reap_codex_lanes`, not at
    :func:`codex_verdict.reap`. The #613 review caught that stopping at the
    latter left the *only* path with a real `codex exec` never touching the
    tick, while the only path that touches the tick substituted the codex
    process — so the two halves of the claim were never true at once. The tick
    call costs nothing extra: the paid call already happened in the fixture.
    """
    reaped = cv.reap(
        launched.run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2
    )
    assert reaped.outcome is cv.ReapOutcome.APPROVED, reaped.detail
    assert reaped.edge is cv.Edge.ADVANCE, reaped.detail


def test_a_real_lane_is_reported_by_the_tick(
    launched: cl.LaunchResult, tmp_path: Path
) -> None:
    """The last link, on a REAL verdict: the tick finds and reports the lane.

    `reap_codex_lanes` scans `ctx.jobs_dir` for run directories, so this proves
    the directory a real launch creates is one the TICK reads. The lane is
    copied into a fresh jobs root first because the sibling test above consumes
    the verdict by rename — the fixture is shared, so this must not depend on
    which test ran first.
    """
    jobs_dir = tmp_path / "jobs"
    dest = cl.lane_run_dir(jobs_dir, NODE_ID)
    dest.parent.mkdir(parents=True)
    shutil.copytree(launched.run_dir, dest)
    # Restore the pre-reap state in case the sibling test already consumed it.
    processed = dest / cv.PROCESSED_FILENAME
    if processed.exists():
        processed.replace(dest / cv.VERDICT_FILENAME)
    cl.write_lane_record(dest, NODE_ID, rework_count=0)

    lines = dag_tick.reap_codex_lanes(
        [
            dag_tick.ClassifiedNode(
                node_id=NODE_ID,
                node_class=dag_tick.NodeClass.ALIVE,
                pid_alive=True,
                state_age_s=1.0,
            )
        ],
        _tick_context(jobs_dir),
    )
    assert len(lines) == 1, lines
    assert "edge=advance" in lines[0], lines[0]


def _tick_context(jobs_dir: Path) -> dag_tick.TickContext:
    """A `TickContext` scoped to a tmp jobs root — injected, never patched."""
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


def test_the_schema_file_is_one_codex_accepts(
    launched: cl.LaunchResult, tmp_path: Path
) -> None:
    """Arm the flag itself: codex must not REJECT our derived schema.

    A schema file codex refuses would abort the run, leave no `-o` file, and
    escalate `file_missing` on every single lane — an outage that reads as a
    model problem.

    The POSITIVE arm is the shared fixture: it exited 0 with a schema-valid
    payload, which is what "codex accepts our schema" means. Re-running it here
    would be a second paid call for an answer already bought (#613 review).

    The control arm must be its own call, because it is the whole point: a
    knowingly-INVALID schema must make the same invocation FAIL. Without it, a
    codex build that had stopped validating `--output-schema` would keep this
    test green while proving nothing about provider enforcement.
    """
    assert launched.exit_code == 0, "codex rejected our derived schema"

    bad_dir = cl.prepare_lane(tmp_path, "e2e-control")
    (bad_dir / cl.SCHEMA_FILENAME).write_text('{"type": "not-a-real-json-type"}\n')
    bad = subprocess.run(
        cl.build_codex_argv(bad_dir),
        input=_PROMPT,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert bad.returncode != 0, (
        "codex ACCEPTED a schema declaring a nonexistent JSON type — "
        "--output-schema is not validating, so the passing arm above proves "
        "nothing about provider enforcement"
    )
