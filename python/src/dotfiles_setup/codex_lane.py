"""The Codex review-lane PRODUCER — what writes the reaper's inputs (#613).

#580 shipped a complete consumer: :mod:`dotfiles_setup.codex_verdict` parses a
verdict, runs a compare-and-swap under a file lock, renames for idempotency and
maps ten outcomes onto edges. Every one of its tests passed. And nothing in the
repo wrote a ``lane.json``, a ``verdict.json`` or an ``EXIT:`` line — so
:func:`dag_tick.reap_codex_lanes` found no run directory for any node and was
**silent**. Correct by accident rather than wrong, which is the worse failure:
nothing reports silence. This module is the missing half.

**Why not just call the plugin's ``run-lane.sh``.** ``use-tool-builtins.md``
requires the justification in writing, and it is a real one rather than a
preference. The ``fable-orchestrator`` plugin's script was read line by line:
it ``mktemp``s both its output paths (``:56-57``), so there is no stable run
directory for a reaper to find; it passes ``--output-last-message`` but never
``--output-schema``, so the contract would be prompt-enforced — exactly what
#580 rejected; it writes no lane record at all, so the CAS has no ``owner`` or
``status`` to verify; and it lives under
``~/.claude/plugins/marketplaces/``, replaced wholesale on plugin update, so
none of that could be fixed in a file this repo gates. Three of the four
artifacts the consumer needs are absent from it by construction.

**What this module deliberately does NOT do.** It does not supervise, retry,
schedule or project an edge onto the tracker. It launches one lane, settles it,
and returns. Projection is the scheduler's job, one direction only
(``docs/receipts/575.md`` R1, #602); ``reap_codex_lanes`` reports the edge as
DECIDED, never applied, and this module keeps that boundary intact.

⚠️ **Two invariants here are load-bearing and easy to "fix" back:**

1. **``lane.log`` carries LAUNCHER writes only, never the model's output.** The
   liveness gate is a substring test for ``EXIT: `` over that file's whole
   text. Tee ``codex``'s stdout into it and any model that types ``EXIT: 0``
   mid-reasoning settles its own lane, and the reaper reads a verdict that is
   still being written. Codex's own output is left on the launcher's stdout,
   where launchd logs it.
2. **:func:`prepare_lane` CLEARS the previous round's settled signals.** A
   rework relaunch into a dirty run directory would be reaped instantly, before
   the new run wrote anything, because round 1's ``EXIT:`` line is still there.

Both are pinned by tests in ``tests/test_codex_lane.py``, control-armed in both
directions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import codex_verdict
from dotfiles_setup.dag_tick import CODEX_LANE_DIRNAME, JOBS_DIR

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Sequence

# IMPORTED from the consumer, never restated. A duplicated "codex-lane" literal
# is two sources of one truth, and the drift is silent in the worst direction:
# the launcher keeps writing to a directory the reaper stopped scanning, and
# every lane goes quiet. Same reasoning as `write_schema` deriving the schema
# file from the Python dict rather than tracking a second copy.
LANE_DIRNAME = CODEX_LANE_DIRNAME

# `--output-schema` needs a FILE, and the file is derived from
# `codex_verdict.VERDICT_SCHEMA` at launch rather than tracked in git.
SCHEMA_FILENAME = "verdict.schema.json"

CODEX_BIN = "codex"
# A review lane reads code and returns a judgement; it must not write. One of
# the three values `codex exec --sandbox` accepts on 0.146.0, and the one
# `.claude/rules/ai-cli-invocation.md` prescribes for the research/debate shape.
READ_ONLY_SANDBOX = "read-only"

# Recorded when the LAUNCHER failed before `codex` returned a code of its own —
# sysexits.h EX_SOFTWARE. The value matters less than the fact that something
# is recorded: an unsettled lane is invisible forever, a settled one with no
# verdict escalates on the next tick.
LAUNCHER_FAILED_EXIT = 70

_IN_PROGRESS = "in_progress"

# Everything :func:`codex_verdict.lane_is_settled` looks at, plus both halves of
# the idempotency pair the CAS reads. A relaunch must start from none of them.
_STALE_ARTIFACTS = (
    codex_verdict.EXIT_MARKER_FILENAME,
    codex_verdict.LANE_LOG_FILENAME,
    codex_verdict.VERDICT_FILENAME,
    codex_verdict.PROCESSED_FILENAME,
)


@dataclass(frozen=True)
class LaunchResult:
    """One launched lane: where it lives and what `codex` exited with.

    Deliberately NOT the verdict. Reading it is the reaper's job, on a later
    tick, under the lock — a launcher that also parsed the verdict would be a
    second consumer racing the first.
    """

    run_dir: Path
    exit_code: int


def lane_run_dir(jobs_dir: Path, node_id: str) -> Path:
    """Where one node's review lane lives.

    Built the way :func:`dag_tick.reap_codex_lanes` builds it, from the same
    constant, so producer and consumer cannot disagree about the path.

    Args:
        jobs_dir: The jobs root the tick scans (``~/.claude/jobs`` in prod).
        node_id: The background node this lane belongs to.

    Returns:
        The run directory for that node's lane.
    """
    return jobs_dir / node_id / LANE_DIRNAME


def prepare_lane(jobs_dir: Path, node_id: str, *, rework_count: int = 0) -> Path:
    """Create the run directory and write everything the consumer reads.

    Three artifacts, and each has a distinct reader:

    - ``lane.json`` — ``owner`` and ``status`` are what the CAS re-verifies
      *inside* the lock, and ``rework_count`` is what
      :func:`dag_tick.read_rework_count` bounds the rework budget with. These
      are LAUNCHER facts on purpose: the model must not be able to state who
      owns a lane or whether it is still claimable.
    - ``verdict.schema.json`` — derived from :data:`codex_verdict.VERDICT_SCHEMA`
      for ``codex exec --output-schema``, so the provider enforces the payload's
      shape instead of a prompt asking nicely.
    - *the absence of* the settled signals — see below.

    ⚠️ **Clearing is not tidiness, it is correctness.** A rework round reuses
    the run directory, and :func:`codex_verdict.lane_is_settled` is a substring
    test over ``lane.log`` plus an existence test on ``exit.marker``. Left in
    place, round 1's ``EXIT:`` line settles round 2 the instant it starts.
    ``verdict.processed.json`` is cleared for the sibling reason: the CAS reads
    "no ``verdict.json`` but a ``verdict.processed.json``" as ALREADY_PROCESSED,
    a no-op edge, so a failed round 2 would report nothing instead of escalating.

    Args:
        jobs_dir: The jobs root the tick scans.
        node_id: The background node that owns this lane.
        rework_count: How many revise/reject rounds this unit has already had.

    Returns:
        The prepared run directory.
    """
    run_dir = lane_run_dir(jobs_dir, node_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    for name in _STALE_ARTIFACTS:
        (run_dir / name).unlink(missing_ok=True)
    write_lane_record(run_dir, node_id, rework_count=rework_count)
    codex_verdict.write_schema(run_dir / SCHEMA_FILENAME)
    return run_dir


def write_lane_record(run_dir: Path, node_id: str, *, rework_count: int) -> Path:
    """Write the ``lane.json`` the reaper's compare-and-swap verifies against.

    A flat JSON object, because that is what both readers want:
    :func:`codex_verdict._read_lane` (which refuses anything that is not a
    dict) and :func:`dag_tick.read_rework_count`.

    Args:
        run_dir: The lane's run directory.
        node_id: The owner to record.
        rework_count: The rework counter to record.

    Returns:
        The path written.
    """
    path = run_dir / codex_verdict.LANE_FILENAME
    path.write_text(
        json.dumps(
            {
                "owner": node_id,
                "status": _IN_PROGRESS,
                "rework_count": rework_count,
            },
            indent=2,
        )
        + "\n"
    )
    return path


def build_codex_argv(
    run_dir: Path,
    *,
    sandbox: str = READ_ONLY_SANDBOX,
    model: str | None = None,
) -> list[str]:
    """The `codex exec` invocation, with BOTH output flags.

    Verified against the real ``codex-cli 0.146.0`` binary's ``exec --help``,
    not against a remembered form — ``.claude/rules/ai-cli-invocation.md``
    exists because wrong flags here fail *silently* (``-p`` is ``--profile``,
    not prompt).

    The trailing ``-`` is what makes the prompt a stdin read: instructions come
    from stdin when the prompt is absent "or if ``-`` is used". Passing a review
    prompt as an argv element instead would risk ARG_MAX on a long diff.

    ``--ephemeral`` keeps session files off disk — this lane's only durable
    output is its verdict, and a persisted session would accumulate one
    transcript per review round forever.

    Args:
        run_dir: The prepared lane directory, whose paths the flags point at.
        sandbox: The ``--sandbox`` policy; read-only for a review lane.
        model: Optional ``--model`` override; omitted so codex's own configured
            default applies.

    Returns:
        The argv list, prompt-from-stdin.
    """
    argv = [
        CODEX_BIN,
        "exec",
        "--ephemeral",
        "--sandbox",
        sandbox,
        "--output-schema",
        str(run_dir / SCHEMA_FILENAME),
        "-o",
        str(run_dir / codex_verdict.VERDICT_FILENAME),
    ]
    if model is not None:
        argv += ["--model", model]
    argv.append("-")
    return argv


def record_exit(run_dir: Path, exit_code: int, *, note: str | None = None) -> None:
    """Append the settled signal in the form the liveness gate reads.

    ``EXIT: <code>`` appended to ``lane.log`` — the form the real launcher
    emits and the one :func:`codex_verdict.lane_is_settled` accepts. #580
    shipped a gate that read only an ``exit.marker`` file while the launcher
    wrote this line, which made every lane permanently NOT_SETTLED; writing the
    same form the gate reads is what keeps the two halves honest.

    ⚠️ This function is the ONLY writer of ``lane.log``. Codex's stdout must
    never be teed here: the gate is a substring test, so a model that types
    ``EXIT: 0`` mid-reasoning would settle its own lane and hand the reaper a
    half-written verdict.

    Args:
        run_dir: The lane's run directory.
        exit_code: The code to record — codex's own, or
            :data:`LAUNCHER_FAILED_EXIT` when the launcher never got one.
        note: An optional human-facing line written *above* the marker, for the
            operator reading the log after an escalation.
    """
    prefix = f"codex-lane: {note}\n" if note else ""
    with (run_dir / codex_verdict.LANE_LOG_FILENAME).open("a") as handle:
        handle.write(f"{prefix}EXIT: {exit_code}\n")


def run_codex(argv: Sequence[str], *, prompt: str, cwd: Path) -> int:
    """Run `codex exec`, prompt on stdin, output left on the launcher's stdout.

    The subprocess boundary, and the only thing tests substitute. Output is NOT
    captured, deliberately: it belongs in launchd's log where an operator can
    read it, and capturing it would invite teeing it into ``lane.log`` — see
    the warning on :func:`record_exit` for why that breaks the liveness gate.

    Args:
        argv: The invocation from :func:`build_codex_argv`.
        prompt: The review prompt, written to stdin.
        cwd: The directory codex runs in — the repo under review, so its own
            git-repo check passes.

    Returns:
        Codex's exit code.
    """
    completed = subprocess.run(
        list(argv),
        input=prompt,
        cwd=cwd,
        text=True,
        check=False,
    )
    return completed.returncode


@dataclass(frozen=True)
class LaneRequest:
    """One review lane's inputs.

    Grouped into a record rather than a long parameter list, following
    :class:`dag_tick.TickContext`'s injection seam (#578 respec round 3): the
    CLI builds one of these and tests construct one directly, so nothing
    downstream needs monkeypatching and the signature stays readable.
    """

    node_id: str
    prompt: str
    cwd: Path
    rework_count: int = 0
    model: str | None = None


def launch_lane(
    jobs_dir: Path,
    request: LaneRequest,
    *,
    runner: Callable[..., int] | None = None,
) -> LaunchResult:
    """Prepare a lane, run `codex exec` in it, and settle it — always.

    ⚠️ **Settling on the failure path is the whole design.** A launcher that
    died between writing ``lane.json`` and recording an exit would leave the
    lane ``in_progress`` with no settled signal: :func:`codex_verdict.reap`
    returns NOT_SETTLED, which is a no-op edge, on every tick, forever. Nobody
    is watching for a node that says nothing. Settling unconditionally converts
    that into ``file_missing`` -> ``needs_human`` on the next tick — the same
    inversion #580 chose for OMC's two warning defaults, applied to the
    producer.

    The handler catches :class:`BaseException` rather than :class:`Exception`
    deliberately: a ``KeyboardInterrupt`` or a ``SystemExit`` mid-launch leaves
    exactly the same invisible lane as an ``OSError`` does, and "the operator
    pressed Ctrl-C" is not a reason for a node to go quiet forever. It re-raises
    immediately, so nothing is swallowed — the caller must never be told the
    lane launched cleanly when it did not.

    Args:
        jobs_dir: The jobs root the tick scans.
        request: The lane's inputs — owner, prompt, cwd, rework count, model.
        runner: The subprocess boundary, injected for tests; defaults to
            :func:`run_codex`.

    Returns:
        The run directory and codex's exit code.

    Raises:
        BaseException: Whatever the runner raised — re-raised after settling.
    """
    invoke = run_codex if runner is None else runner
    run_dir = prepare_lane(jobs_dir, request.node_id, rework_count=request.rework_count)
    argv = build_codex_argv(run_dir, model=request.model)
    try:
        exit_code = invoke(argv, prompt=request.prompt, cwd=request.cwd)
    except BaseException as exc:
        record_exit(
            run_dir,
            LAUNCHER_FAILED_EXIT,
            note=f"launcher failed before codex returned: {exc!r}",
        )
        raise
    record_exit(run_dir, exit_code)
    return LaunchResult(run_dir=run_dir, exit_code=exit_code)


def read_prompt(prompt_file: Path | None) -> str:
    """The review prompt, from a file or stdin.

    Args:
        prompt_file: The file to read, or ``None`` to read stdin.

    Returns:
        The prompt text.
    """
    return prompt_file.read_text() if prompt_file is not None else sys.stdin.read()


def run_lane_cli(args: argparse.Namespace) -> int:
    """`dotfiles-setup codex-lane`: launch one review lane and settle it.

    ⚠️ **Returns 0 whenever the lane was launched AND settled, even when codex
    itself exited non-zero.** This is a decision, not an oversight. The
    launcher's job is to produce a settled lane; what that lane MEANT is the
    reaper's to decide on a later tick, under the lock, and an abort is already
    reported through the ``file_missing`` -> ``needs_human`` escalation. Surfacing
    codex's rc here would make a wrapping ``mise run`` or a supervisor read a
    correctly-escalated lane as a launcher failure — and the obvious response to
    that is a retry, which double-launches into a run directory the reaper may
    already be holding. Non-zero is reserved for the launcher failing to do its
    own job.

    Args:
        args: Parsed CLI arguments.

    Returns:
        0 when the lane was launched and settled; 2 when the prompt was empty.
    """
    prompt = read_prompt(args.prompt_file)
    if not prompt.strip():
        sys.stderr.write(
            "codex-lane: refusing to launch with an empty prompt — a review "
            "lane with nothing to review burns a call and escalates\n"
        )
        return 2
    result = launch_lane(
        args.jobs_dir or JOBS_DIR,
        LaneRequest(
            node_id=args.node,
            prompt=prompt,
            cwd=args.cwd or Path.cwd(),
            rework_count=args.rework_count,
            model=args.model,
        ),
    )
    sys.stdout.write(
        f"codex-lane: {args.node} settled at {result.run_dir} "
        f"(codex rc={result.exit_code}); the verdict is the tick's to reap\n"
    )
    return 0
