"""Project NEEDS_HUMAN nodes to the tracker — the scheduler's first slice (#602).

`dag_tick` (#578/#601) classifies an escalated background node
:attr:`~dotfiles_setup.dag_tick.NodeClass.NEEDS_HUMAN` — `state == "blocked"` with
a non-empty `needs` payload and no `queuedPrompt` — logs it, and **never respawns
it**. Nothing emitted the other half. `docs/receipts/575.md` R1 keeps projection
**one-directional and scheduler-owned**, and a tick that labelled directly would
put a second writer on the tracker — so the boundary was right and the far side
was unowned. The consequence was live: two nodes sat `blocked ∧ needs` since
2026-07-13 and 2026-07-22, visible in a launchd log and nowhere else.

This module is that far side, built as the SCHEDULER'S FIRST SLICE rather than as
a watchdog feature, because no scheduler module existed to extend. It is shaped
so #573's pull loop absorbs it as a phase in its fixed order (reconcile ->
**project** -> preflight -> select -> dispatch) instead of being refactored out of
somewhere it never belonged.

Spec: `docs/specs/dag-needs-human-projection.md`. **Slice 2 is READ-ONLY** —
:func:`render_comment` and :func:`collect_escalations` decide everything and
`--dry-run` prints it; the write path (label + comment + dedupe) is phase 3 and
this module makes no network call at all.

Four properties bind it, and each is a decision rather than a style:

- **It reuses `dag_tick`'s predicates BY IMPORT and never re-derives them.**
  :func:`~dotfiles_setup.dag_tick.node_from_state`,
  :func:`~dotfiles_setup.dag_tick.normalize_needs` and
  :func:`~dotfiles_setup.dag_tick.is_needs_human` are imported, not copied. The
  #601 v4 and #604 reviews both found the same defect class — two readers of one
  `state.json` disagreeing about it — so a private copy of `is_needs_human` here
  is a spec violation, not a preference.
- **One direction, always.** It READS `~/.claude/jobs/**` and (from phase 3)
  writes only to GitHub. It never writes a job dir, never calls `claude
  respawn`/`stop`/`rm`, and never edits an issue **body** (`docs/receipts/573.md`
  §VERDICT: labels for what the selector reads, append-only comments for the
  rest, never the body).
- **Zero escalations means zero API calls.** :func:`collect_escalations` reads
  disk first and the caller returns before touching the network when nothing is
  escalated. The common case is zero, and a projector that makes no call when
  idle cannot misfire when idle.
- **The `needs` payload is CARGO.** It is quoted verbatim inside a fenced block
  and never summarised, and `_needs_human_reason()` is reproduced verbatim rather
  than paraphrased — that string is pinned by golden equality in
  `tests/test_dag_tick.py` precisely because it must claim the re-check without
  claiming the race is gone, and a paraphrase would silently drop the scope
  qualifiers two rounds of #601 review put there.

⚠️ **A fenced block, not a blockquote, and that is a MEASURED correction.** The
spec's first draft quoted the payload with `>`; the phase-1 by-hand pilot showed
`ad8baf35`'s payload **contains backticks**, so GitHub rendered them as inline
code and the raw characters never appeared. The phase-1 gate as first written
("both comments render correctly") would have PASSED that, because a mangled
payload renders beautifully — it only became a real check when restated as a byte
comparison against `state.json`. Do not "tidy" the fence back to a blockquote.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import dag_tick

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterable, Mapping, Sequence

logger = logging.getLogger(__name__)

#: The standing escalation issue an UNBOUND node projects to (spec §2.2, created
#: in phase 1). A module constant with a CLI override rather than an env var: a
#: change here is a reviewable diff, not silent per-clone drift.
#:
#: It exists because of one measurement — **nothing binds a node to an issue.**
#: No `issue`/`ticket` field appears in the union of every `state.json` key set on
#: this host, and a job dir holds only `state.json`, `timeline.jsonl` and `tmp/`.
#: Both live escalations were hand-launched long before any scheduler, so a
#: bound-nodes-only reading would have shipped #602 surfacing **0 of its own 2
#: motivating cases**.
DEFAULT_ESCALATION_ISSUE = 623

#: `owner/repo` the projection targets. Same reviewable-constant reasoning.
DEFAULT_REPO = "ray-manaloto/dotfiles"

#: Written by the scheduler at DISPATCH, inside the node's own job dir, on #580's
#: `CODEX_LANE_DIRNAME` precedent: colocating means a `claude rm` of the node
#: takes its binding with it instead of orphaning a pointer to nothing.
BINDING_FILENAME = "dag-binding.json"

#: Bumped when the marker or the comment's machine-readable shape changes.
#: Present from v1 deliberately — `codex_verdict.py` records that OMC's payload
#: lacks one, "which is why a contract change there breaks silently".
MARKER_SCHEMA = 1

#: How many hex chars of the payload digest ride in the marker. Long enough that
#: two different questions do not collide, short enough to read in a diff.
_DIGEST_CHARS = 12


@dataclass(frozen=True)
class Binding:
    """One node's dispatch-time binding to a tracker issue."""

    repo: str
    issue: int


@dataclass(frozen=True)
class Escalation:
    """Everything the comment renders, read from one node's `state.json`.

    `job_dir_exists` is separate from the rest because it decides which of the
    TWO "How to answer" forms is correct, and getting that wrong is the same
    class of defect as a log line naming an action the code does not perform:
    telling an operator to reply to something that cannot receive a reply.
    """

    node_id: str
    needs: str
    suggested_reply: str | None
    state: str | None
    tempo: str | None
    session_id: str | None
    cli_version: str | None
    updated_at: str | None
    mtime_iso: str | None
    job_dir_exists: bool
    stalled: bool
    binding: Binding | None

    @property
    def digest(self) -> str:
        """The dedupe key for THIS question — see :func:`payload_digest`."""
        return payload_digest(self.needs)

    @property
    def target_issue(self) -> int:
        """Where this projects: its own issue when bound, else the standing one."""
        return self.binding.issue if self.binding else DEFAULT_ESCALATION_ISSUE


def payload_digest(needs: str) -> str:
    """A stable short digest of one `needs` payload, for marker dedupe.

    Deliberately over the payload and NOT over the node id: the dedupe key is
    `(node, digest)` and the two halves fail in opposite directions. Keying on
    the node alone means a node that re-escalates with a **new** question is
    silently never reported again; keying on the digest alone collides across
    nodes that ask the same question.
    """
    return hashlib.sha256(needs.encode("utf-8")).hexdigest()[:_DIGEST_CHARS]


def marker(node_id: str, digest: str) -> str:
    """The invisible HTML marker the phase-3 dedupe scans comments for.

    An HTML comment rather than a visible line so the artifact stays
    dual-audience (#573's adopted stokowski precedent) — a human reads prose, the
    projector reads this.

    **It cannot be the label instead**, and that is not a preference: the label
    lives on the ISSUE, so on the standing escalation issue the first node would
    label it and every subsequent node's comment would be suppressed. The marker
    is per-node by construction.
    """
    return (
        f"<!-- dag:needs-human node={node_id} "
        f"digest={digest} schema={MARKER_SCHEMA} -->"
    )


def read_binding(job_dir: Path) -> Binding | None:
    """This node's dispatch-time binding, or `None` when it is UNBOUND.

    Unreadable, malformed or partial is treated exactly like ABSENT — an unbound
    node still projects, to the standing issue. That is the deliberate direction:
    the failure #602 exists to end is SILENCE, so a binding we cannot parse must
    never cost the escalation its visibility. (The opposite choice — refuse to
    project what we cannot route — recreates the failure at a new layer.)
    """
    try:
        raw = json.loads((job_dir / BINDING_FILENAME).read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError, ValueError:
        return None
    if not isinstance(raw, dict):
        return None
    issue = raw.get("issue")
    repo = raw.get("repo")
    if not isinstance(issue, int) or isinstance(issue, bool) or issue <= 0:
        return None
    resolved = repo if isinstance(repo, str) and repo else DEFAULT_REPO
    return Binding(repo=resolved, issue=issue)


def r5_verdict(escalation: Escalation) -> str:
    """#575 R5 as a STRUCTURAL predicate, never a semantic one.

    R5 says a blocker is valid only if it names what was exhausted. Read as a
    gate that would DROP both live escalations — and Ray's ruling is that a
    failing escalation is **projected anyway, flagged**, because dropping it
    recreates the silence #602 exists to end. `dag_tick`'s own `REPLY_QUEUED`
    precedent chose visibility for the same reason: making it visible IS the fix.

    So the question asked here is *"does this escalation carry a machine-readable
    evidence field?"* — never *"does this prose sound like it names what was
    exhausted?"* That is a deliberate refusal to build a semantic classifier, and
    the reason is on the record: the #601 review killed substring-based reason
    checking across two rounds, concluding a substring guard cannot judge meaning
    so tightening it is unwinnable. A heuristic scanning `needs` for
    "tried"/"exhausted"/"fallback" is that same losing shape one layer up, and
    its false negatives would drop a real human question.

    Consequence, stated rather than hidden: **every harness-native escalation is
    UNVALIDATED today**, because `state.json`'s `needs` is a free-form string the
    harness writes and there is no evidence field to carry. Measured 3-for-3
    across CLI 2.1.207, 2.1.217 and 2.1.224.
    """
    del escalation  # No evidence field exists to inspect yet — see the docstring.
    return "⚠️ **UNVALIDATED** — the payload does not name what was exhausted"


def _iso_utc(timestamp: float) -> str:
    """One mtime as UTC ISO-8601, seconds precision.

    ⚠️ **UTC, never a formatted `ls`.** The spec's first draft carried the LOCAL
    time `ls` prints and stamped it `Z`, which is how "#602's body says 07-14 but
    the mtime is 07-13" became a correction that was really a timezone. A date
    without an offset is not a measurement.
    """
    return (
        dt.datetime.fromtimestamp(timestamp, dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _as_str(value: object) -> str | None:
    """One `state.json` field as text, or `None` when it is absent/not a string."""
    return value if isinstance(value, str) and value else None


def escalation_from_state(
    node_id: str,
    data: Mapping[str, object],
    *,
    job_dir: Path,
    mtime: float | None,
    stall_after_s: float,
) -> Escalation | None:
    """One node's `Escalation`, or `None` when it is not escalated.

    The escalation test is :func:`dag_tick.is_needs_human` via
    :func:`dag_tick.node_from_state` — imported, never re-implemented, so this
    module and the tick can never disagree about the same file.
    """
    node = dag_tick.node_from_state(node_id, data)
    escalated = dag_tick.is_needs_human(
        node.state, node.needs, queued_prompt=node.queued_prompt
    )
    if not escalated:
        return None
    if node.needs is None:  # pragma: no cover - is_needs_human already proved it
        return None
    age = None if mtime is None else max(_now() - mtime, 0.0)
    return Escalation(
        node_id=node_id,
        needs=node.needs,
        suggested_reply=dag_tick.normalize_needs(data.get("suggestedReply")),
        state=node.state,
        tempo=node.tempo,
        session_id=_as_str(data.get("sessionId")),
        cli_version=_as_str(data.get("cliVersion")),
        updated_at=_as_str(data.get("updatedAt")),
        mtime_iso=None if mtime is None else _iso_utc(mtime),
        job_dir_exists=job_dir.is_dir(),
        stalled=dag_tick.is_stalled(node.tempo, age, stall_after_s),
        binding=read_binding(job_dir),
    )


def _now() -> float:
    """Wall clock, isolated so a test can pin it without patching `time`."""
    return time.time()


def collect_escalations(
    jobs_dir: Path, *, stall_after_s: float = dag_tick.DEFAULT_STALL_AFTER_SECONDS
) -> list[Escalation]:
    """Every escalated node under `jobs_dir`, oldest job dir name first.

    An unreadable or unparsable `state.json` is SKIPPED, matching
    `execute_respawn`/`execute_stop`'s one shared rule. The asymmetry is worth
    naming rather than glossing: skipping here costs an escalation its
    visibility, which is the harm this module exists to prevent — but INVENTING
    an escalation out of an unreadable file would put a fabricated question in
    front of a human, which is worse. It is logged loudly instead.
    """
    escalations: list[Escalation] = []
    if not jobs_dir.is_dir():
        return escalations
    for job_dir in sorted(p for p in jobs_dir.iterdir() if p.is_dir()):
        state_path = job_dir / "state.json"
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            mtime = state_path.stat().st_mtime
        except OSError, json.JSONDecodeError, ValueError:
            logger.warning(
                "dag-project: %s state.json unreadable — SKIPPED, so an "
                "escalation there is invisible this run",
                job_dir.name,
            )
            continue
        if not isinstance(data, dict):
            logger.warning(
                "dag-project: %s state.json is not an object — SKIPPED", job_dir.name
            )
            continue
        escalation = escalation_from_state(
            job_dir.name,
            data,
            job_dir=job_dir,
            mtime=mtime,
            stall_after_s=stall_after_s,
        )
        if escalation is not None:
            escalations.append(escalation)
    return escalations


def _answer_guidance(escalation: Escalation) -> str:
    """The correct one of the TWO "How to answer" forms for this node.

    Chosen by whether the job dir still exists, because the two say opposite
    things and only one can be true. The route that reaches a not-running job is
    a respawn carrying the human's text as `initialPrompt` — FleetView's reply
    path — and `claude respawn` ALONE returns the node idle with no prompt,
    discarding the question (`docs/receipts/565.md`). Cross-session `SendMessage`
    cannot do it at any version: a dead node's local peer entry is unlinked, and
    a bridge-matched name returns `success: false`.
    """
    if escalation.job_dir_exists:
        return (
            "**How to answer:** the job dir still exists, so this is a live "
            "question. Reply to this node in FleetView — that respawns it with "
            "your answer as `initialPrompt`, the only route that reaches a "
            "not-running job. `claude respawn` alone returns it **idle with no "
            "prompt** and discards the question."
        )
    return (
        "**How to answer:** ⚠️ this node's job dir no longer exists, so there is "
        "nothing left to answer — this comment is a RECORD, not a live question. "
        "The payload above is preserved here precisely because the job dir is not."
    )


def _fenced(text: str) -> str:
    """One payload in a fenced block — see the module docstring on why not `>`."""
    return f"```text\n{text}\n```"


def last_updated(escalation: Escalation) -> str:
    """When this node last wrote its state, preferring the field over the mtime.

    ⚠️ **`updatedAt` is authoritative and the mtime is the FALLBACK, not the
    other way round.** The harness writes `updatedAt` INTO the file, so it
    survives a copy, a backup/restore, a `git checkout` and a `touch`; an mtime
    survives none of those. Phase 2's own gate caught this: running the projector
    against a fixture built by `cp` reported the mtime as the day of the COPY
    while `updatedAt` still read the node's real last write, three weeks earlier.
    A timestamp that a file operation can rewrite is not a measurement of when
    the human was asked.

    Both are still reported when they disagree, because the disagreement is
    itself information — a node whose mtime moved without `updatedAt` moving was
    touched by something that is not the harness.
    """
    if escalation.updated_at and escalation.mtime_iso:
        if escalation.updated_at.startswith(escalation.mtime_iso[:16]):
            return f"`updatedAt` {escalation.updated_at}"
        return (
            f"`updatedAt` {escalation.updated_at} "
            f"(⚠️ file mtime disagrees: {escalation.mtime_iso})"
        )
    if escalation.updated_at:
        return f"`updatedAt` {escalation.updated_at}"
    if escalation.mtime_iso:
        return f"file mtime {escalation.mtime_iso} (`updatedAt` absent)"
    return "_unknown_"


def render_comment(escalation: Escalation, *, projected_at: str) -> str:
    """The append-only tracker comment for one escalation (spec §2.3).

    Pilot-validated: both live escalations were projected by hand with this
    format on 2026-08-07 and the round-trip was byte-verified against
    `state.json` through the API — 3/3 payloads identical.
    """
    reply = (
        _fenced(escalation.suggested_reply)
        if escalation.suggested_reply
        else "_absent_"
    )
    if escalation.binding:
        target = f"{escalation.binding.repo}#{escalation.binding.issue}"
        binding = f"**BOUND** — `{BINDING_FILENAME}` -> {target}"
    else:
        binding = (
            f"**UNBOUND** — no `{BINDING_FILENAME}`; projected to the "
            "standing escalation issue"
        )
    updated_row = last_updated(escalation)
    stalled = (
        "**yes** — `tempo` is `active` and the state.json has gone stale"
        if escalation.stalled
        else f"no (`tempo` is `{escalation.tempo}`, not `active`)"
    )
    rows = [
        ("node", f"`{escalation.node_id}`"),
        (
            "session",
            f"`{escalation.session_id}`" if escalation.session_id else "_unknown_",
        ),
        ("state / tempo", f"`{escalation.state}` / `{escalation.tempo}`"),
        (
            "`queuedPrompt`",
            "absent — a question awaiting an answer, not an answer awaiting delivery",
        ),
        ("last updated", updated_row),
        ("written by CLI", escalation.cli_version or "_unknown_"),
        ("binding", binding),
        ("R5 evidence", r5_verdict(escalation)),
        ("also stalled", stalled),
        ("projected by", f"`dag-project` @ {projected_at}"),
    ]
    table = "\n".join(f"| {name} | {value} |" for name, value in rows)
    return "\n".join(
        [
            marker(escalation.node_id, escalation.digest),
            f"### 🙋 NEEDS_HUMAN — node `{escalation.node_id}`",
            "",
            "**The question** — `needs`, verbatim from "
            f"`~/.claude/jobs/{escalation.node_id}/state.json`:",
            "",
            _fenced(escalation.needs),
            "",
            f"**Suggested reply** — `suggestedReply`: {reply}",
            "",
            "| Field | Value |",
            "|---|---|",
            table,
            "",
            "**What the watchdog will and will not do** — reproduced verbatim from",
            "`dag_tick._needs_human_reason()`, not paraphrased:",
            "",
            f"> {dag_tick.needs_human_reason()}",
            "",
            _answer_guidance(escalation),
            "",
            "Refs #602",
        ]
    )


def render_dry_run(escalations: Sequence[Escalation], *, projected_at: str) -> str:
    """What a real run WOULD post, and nothing else.

    Reports the empty case explicitly rather than printing nothing: "no
    escalations" and "the projector did not run" must never look the same, which
    is the distinction `docs/receipts/575.md`'s three-state discipline exists to
    keep.
    """
    if not escalations:
        return (
            "dag-project: 0 escalations — nothing to project, and NO API call "
            "was made (a projector that is silent when idle cannot misfire when "
            "idle)."
        )
    blocks = [
        f"dag-project: {len(escalations)} escalation(s) — DRY RUN, nothing posted.",
        "",
    ]
    for escalation in escalations:
        blocks.extend(
            [
                f"--- would comment on #{escalation.target_issue} "
                f"and add label `{dag_tick.NEEDS_HUMAN_LABEL}` ---",
                render_comment(escalation, projected_at=projected_at),
                "",
            ]
        )
    return "\n".join(blocks)


def run_project(args: argparse.Namespace) -> int:
    """CLI entry point. **Phase 2 is dry-run only** — the write path is #602 phase 3.

    A non-`--dry-run` invocation REFUSES rather than silently doing nothing: a
    command that accepts a flag it cannot honour is how an operator concludes a
    projection happened when it did not.
    """
    jobs_dir = Path(args.jobs_dir).expanduser() if args.jobs_dir else dag_tick.JOBS_DIR
    escalations = collect_escalations(jobs_dir, stall_after_s=args.stall_after)
    if not args.dry_run:
        logger.error(
            "dag-project: the write path is #602 phase 3 and is NOT implemented — "
            "re-run with --dry-run. Refusing rather than exiting 0 having done "
            "nothing, which would read as a successful projection."
        )
        return 2
    projected_at = args.projected_at or _iso_utc(_now())
    sys.stdout.write(render_dry_run(escalations, projected_at=projected_at) + "\n")
    return 0


def escalation_ids(escalations: Iterable[Escalation]) -> list[str]:
    """Just the node ids — the shape a caller logs or a test asserts on."""
    return [escalation.node_id for escalation in escalations]
