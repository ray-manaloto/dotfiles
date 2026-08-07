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


def test_a_real_codex_call_round_trips_into_an_advance_edge(tmp_path: Path) -> None:
    """The whole path, with nothing substituted.

    Launcher writes the lane record and the derived schema, the real `codex
    exec` returns a provider-constrained payload, the real reaper validates it
    under the lock and maps it to an edge. This is the assertion #613 was filed
    to make possible.
    """
    _require_codex()
    result = cl.launch_lane(tmp_path, _request())
    assert result.exit_code == 0, "codex exec did not exit cleanly"

    verdict_text = (result.run_dir / cv.VERDICT_FILENAME).read_text()
    assert verdict_text.strip(), (
        "codex wrote an EMPTY -o file — its explicit 'no last agent message' "
        "path. The lane still escalates, but the transport did not work."
    )

    reaped = cv.reap(
        result.run_dir, expected_owner=NODE_ID, rework_count=0, max_rework=2
    )
    assert reaped.outcome is cv.ReapOutcome.APPROVED, reaped.detail
    assert reaped.edge is cv.Edge.ADVANCE, reaped.detail


def test_the_provider_really_constrains_the_payload_shape(tmp_path: Path) -> None:
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
    _require_codex()
    result = cl.launch_lane(tmp_path, _request())
    payload = json.loads((result.run_dir / cv.VERDICT_FILENAME).read_text())

    assert set(payload) <= set(cv.VERDICT_SCHEMA["properties"]), (
        f"provider returned properties outside the schema: "
        f"{sorted(set(payload) - set(cv.VERDICT_SCHEMA['properties']))} — "
        "`additionalProperties: false` is not being enforced"
    )
    assert set(cv.VERDICT_SCHEMA["required"]) <= set(payload)
    assert payload["schema_version"] == cv.SCHEMA_VERSION
    assert payload["verdict"] in {v.value for v in cv.Verdict}


def test_the_schema_file_is_one_codex_accepts(tmp_path: Path) -> None:
    """Arm the flag itself: codex must not REJECT our derived schema.

    A schema file codex refuses would abort the run, leave no `-o` file, and
    escalate `file_missing` on every single lane — an outage that reads as a
    model problem. This drives the flag with the real binary and a trivial
    prompt, and asserts the process got far enough to write output at all.

    The control arm is deliberate and cheap: a knowingly-INVALID schema must
    make the same call fail. Without it, a codex build that had stopped
    validating `--output-schema` entirely would keep this test green.
    """
    _require_codex()
    run_dir = cl.prepare_lane(tmp_path, NODE_ID)
    good = subprocess.run(
        cl.build_codex_argv(run_dir),
        input=_PROMPT,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert good.returncode == 0, f"codex rejected our schema: {good.stderr[-2000:]}"

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
