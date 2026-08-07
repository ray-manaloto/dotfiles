"""Tests for the NEEDS_HUMAN tracker projection (#602 phase 2).

The fixtures are the REAL payloads of the only two escalations that have ever
existed on this host, recorded verbatim on issue #623 before their job dirs were
removed. They are used rather than invented strings for one reason: `ad8baf35`'s
`needs` **contains backticks**, and that single property is what the phase-1
by-hand pilot proved a blockquote silently destroys. An invented payload without
backticks would make every test here pass against a renderer that mangles the
real one.
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import dag_project, dag_tick

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

# The two real payloads, verbatim. `_BACKTICKED` is load-bearing — see the module
# docstring. Do not "simplify" it.
_BACKTICKED = "run `/clear` to proceed to next task"
_JULY_22 = "do /clear with resume, or run full command-catalog extraction first?"
_JULY_22_REPLY = "do the full command catalog extraction pass"

_ESCALATED_STATE = {
    "state": "blocked",
    "tempo": "blocked",
    "needs": _BACKTICKED,
    "sessionId": "ad8baf35-00fe-4223-80d1-9b0d94d9c338",
    "cliVersion": "2.1.207",
    "updatedAt": "2026-07-14T01:29:08.930Z",
}


def _write_node(jobs_dir: Path, node_id: str, state: Mapping[str, object]) -> Path:
    job_dir = jobs_dir / node_id
    job_dir.mkdir(parents=True)
    (job_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return job_dir


def _escalation(jobs_dir: Path, node_id: str = "ad8baf35") -> dag_project.Escalation:
    job_dir = _write_node(jobs_dir, node_id, dict(_ESCALATED_STATE))
    found = dag_project.escalation_from_state(
        node_id,
        json.loads((job_dir / "state.json").read_text(encoding="utf-8")),
        job_dir=job_dir,
        mtime=None,
        stall_after_s=dag_tick.DEFAULT_STALL_AFTER_SECONDS,
    )
    assert found is not None
    return found


def test_payload_digest_is_stable_and_payload_keyed() -> None:
    """The dedupe key tracks the QUESTION, not the node."""
    assert dag_project.payload_digest(_BACKTICKED) == "a5f7040626d9"
    assert dag_project.payload_digest(_JULY_22) == "4f43b1280966"
    assert dag_project.payload_digest(_BACKTICKED) != dag_project.payload_digest(
        _JULY_22
    )


def test_dedupe_key_needs_both_halves() -> None:
    """Both halves of `(node, digest)`, because they fail in OPPOSITE directions.

    Node alone: a node that re-escalates with a NEW question is never reported
    again. Digest alone: two nodes asking the SAME question collide and one is
    silently dropped. The marker carries both, so neither failure is reachable.
    """
    same_node_new_question = {
        dag_project.marker("n1", dag_project.payload_digest(_BACKTICKED)),
        dag_project.marker("n1", dag_project.payload_digest(_JULY_22)),
    }
    assert len(same_node_new_question) == 2, "node-only keying would collapse these"

    two_nodes_same_question = {
        dag_project.marker("n1", dag_project.payload_digest(_BACKTICKED)),
        dag_project.marker("n2", dag_project.payload_digest(_BACKTICKED)),
    }
    assert len(two_nodes_same_question) == 2, "digest-only keying would collapse these"


def test_marker_is_an_invisible_html_comment_carrying_the_schema() -> None:
    mark = dag_project.marker("ad8baf35", "a5f7040626d9")
    assert mark.startswith("<!--")
    assert mark.endswith("-->")
    assert "node=ad8baf35" in mark
    assert "digest=a5f7040626d9" in mark
    assert f"schema={dag_project.MARKER_SCHEMA}" in mark


def test_payload_is_fenced_verbatim_not_blockquoted(tmp_path: Path) -> None:
    """The backticked payload must survive INTACT — the phase-1 pilot's finding.

    A blockquote renders backticks as inline code and the raw characters vanish,
    which LOOKS correct. This asserts the bytes, which is the only check that can
    tell the difference.
    """
    comment = dag_project.render_comment(
        _escalation(tmp_path), projected_at="2026-08-07T00:00:00Z"
    )
    assert f"```text\n{_BACKTICKED}\n```" in comment
    assert f"> {_BACKTICKED}" not in comment, "a blockquote would mangle the backticks"


def test_reason_is_reproduced_verbatim_never_paraphrased(tmp_path: Path) -> None:
    """The comment carries `_needs_human_reason()` byte-for-byte.

    That string is pinned by golden equality in `test_dag_tick.py` because it
    must claim the re-check WITHOUT claiming the race is gone. Reproducing it
    here means the pin now also guards operator-facing tracker content.
    """
    comment = dag_project.render_comment(
        _escalation(tmp_path), projected_at="2026-08-07T00:00:00Z"
    )
    assert dag_tick.needs_human_reason() in comment


def test_reason_accessor_is_the_string_plan_actually_emits() -> None:
    """One definition — asserted through a PUBLIC path, not the private name.

    `plan()` puts the reason on its `Action`, so if the accessor `dag_project`
    reads ever diverged from what the tick actually emits, this fails. That is
    the invariant worth pinning: the projector and the watchdog must not describe
    the same node differently.
    """
    classified = dag_tick.ClassifiedNode(
        "n", dag_tick.NodeClass.NEEDS_HUMAN, pid_alive=False, state_age_s=1.0
    )
    actions = dag_tick.plan([classified], max_age_s=86400.0)
    assert [a.reason for a in actions] == [dag_tick.needs_human_reason()]


def test_suggested_reply_is_fenced_when_present_and_marked_absent_otherwise(
    tmp_path: Path,
) -> None:
    """`suggestedReply` is cargo too — #575 R1 makes it load-bearing."""
    absent = dag_project.render_comment(
        _escalation(tmp_path, "no-reply"), projected_at="2026-08-07T00:00:00Z"
    )
    assert "`suggestedReply`: _absent_" in absent

    with_reply = dict(_ESCALATED_STATE, needs=_JULY_22, suggestedReply=_JULY_22_REPLY)
    job_dir = _write_node(tmp_path, "fdfdaf90", with_reply)
    found = dag_project.escalation_from_state(
        "fdfdaf90", with_reply, job_dir=job_dir, mtime=None, stall_after_s=120.0
    )
    assert found is not None
    assert f"```text\n{_JULY_22_REPLY}\n```" in dag_project.render_comment(
        found, projected_at="2026-08-07T00:00:00Z"
    )


@pytest.mark.parametrize(
    ("state", "needs", "queued", "expected"),
    [
        ("blocked", _BACKTICKED, False, True),
        ("blocked", None, False, False),
        ("blocked", _BACKTICKED, True, False),
        ("done", _BACKTICKED, False, False),
        ("failed", _BACKTICKED, False, False),
    ],
)
def test_escalation_test_delegates_to_dag_tick(
    tmp_path: Path,
    state: str,
    needs: str | None,
    *,
    queued: bool,
    expected: bool,
) -> None:
    """The predicate is `dag_tick.is_needs_human`, imported — never re-derived.

    Pinned as a table so a future edit that quietly grows a private copy here
    diverges visibly. Two readers of one `state.json` disagreeing about it is the
    exact defect class #601 v4 and #604 each shipped a fix for.
    """
    payload: dict[str, object] = {"state": state, "tempo": "blocked"}
    if needs is not None:
        payload["needs"] = needs
    if queued:
        payload["queuedPrompt"] = "an answer already on its way"
    job_dir = _write_node(tmp_path, f"n-{state}-{needs is None}-{queued}", payload)
    found = dag_project.escalation_from_state(
        job_dir.name, payload, job_dir=job_dir, mtime=None, stall_after_s=120.0
    )
    assert (found is not None) is expected


def test_binding_absent_malformed_and_valid(tmp_path: Path) -> None:
    """An unparsable binding reads as UNBOUND — never as a reason to drop.

    The failure #602 exists to end is silence, so a binding we cannot route on
    must cost the escalation its ROUTE, never its visibility.
    """
    job_dir = _write_node(tmp_path, "unbound", dict(_ESCALATED_STATE))
    assert dag_project.read_binding(job_dir) is None

    (job_dir / dag_project.BINDING_FILENAME).write_text("{not json", encoding="utf-8")
    assert dag_project.read_binding(job_dir) is None

    (job_dir / dag_project.BINDING_FILENAME).write_text(
        json.dumps({"issue": "602", "repo": "o/r"}), encoding="utf-8"
    )
    assert dag_project.read_binding(job_dir) is None, "a string issue is malformed"

    (job_dir / dag_project.BINDING_FILENAME).write_text(
        json.dumps({"schema_version": 1, "issue": 602, "repo": "o/r"}), encoding="utf-8"
    )
    binding = dag_project.read_binding(job_dir)
    assert binding == dag_project.Binding(repo="o/r", issue=602)


def test_unbound_projects_to_the_standing_issue_bound_to_its_own(
    tmp_path: Path,
) -> None:
    """Ray's ruling: an unbound escalation is projected, not dropped."""
    unbound = _escalation(tmp_path, "unbound")
    assert unbound.target_issue == dag_project.DEFAULT_ESCALATION_ISSUE
    assert "**UNBOUND**" in dag_project.render_comment(unbound, projected_at="t")

    job_dir = _write_node(tmp_path, "bound", dict(_ESCALATED_STATE))
    (job_dir / dag_project.BINDING_FILENAME).write_text(
        json.dumps({"issue": 4242, "repo": "o/r"}), encoding="utf-8"
    )
    bound = dag_project.escalation_from_state(
        "bound",
        dict(_ESCALATED_STATE),
        job_dir=job_dir,
        mtime=None,
        stall_after_s=120.0,
    )
    assert bound is not None
    assert bound.target_issue == 4242
    assert "**BOUND**" in dag_project.render_comment(bound, projected_at="t")


def test_answer_guidance_has_two_forms_chosen_by_job_dir(tmp_path: Path) -> None:
    """Telling an operator to reply to something that cannot receive one is a defect."""
    live = _escalation(tmp_path, "live")
    assert "live question" in dag_project.render_comment(live, projected_at="t")

    gone = dag_project.Escalation(
        node_id="gone",
        needs=_BACKTICKED,
        suggested_reply=None,
        state="blocked",
        tempo="blocked",
        session_id=None,
        cli_version=None,
        updated_at=None,
        mtime_iso=None,
        job_dir_exists=False,
        stalled=False,
        binding=None,
    )
    rendered = dag_project.render_comment(gone, projected_at="t")
    assert "RECORD, not a live question" in rendered
    assert "live question. Reply to this node" not in rendered


def test_last_updated_prefers_updated_at_and_flags_a_disagreement() -> None:
    """`updatedAt` is authoritative; the mtime is the fallback.

    Phase 2's own gate caught this: a fixture built with `cp` reported the mtime
    as the day of the COPY while `updatedAt` still held the node's real last
    write. A timestamp a file operation can rewrite is not a measurement.
    """
    base = {
        "node_id": "n",
        "needs": _BACKTICKED,
        "suggested_reply": None,
        "state": "blocked",
        "tempo": "blocked",
        "session_id": None,
        "cli_version": None,
        "job_dir_exists": True,
        "stalled": False,
        "binding": None,
    }
    agree = dag_project.Escalation(
        **base, updated_at="2026-07-14T01:29:08.930Z", mtime_iso="2026-07-14T01:29:08Z"
    )
    assert dag_project.last_updated(agree) == "`updatedAt` 2026-07-14T01:29:08.930Z"

    disagree = dag_project.Escalation(
        **base, updated_at="2026-07-14T01:29:08.930Z", mtime_iso="2026-08-07T07:58:21Z"
    )
    flagged = dag_project.last_updated(disagree)
    assert "⚠️ file mtime disagrees" in flagged
    assert "2026-08-07T07:58:21Z" in flagged

    only_mtime = dag_project.Escalation(
        **base, updated_at=None, mtime_iso="2026-07-14T01:29:08Z"
    )
    assert "`updatedAt` absent" in dag_project.last_updated(only_mtime)

    neither = dag_project.Escalation(**base, updated_at=None, mtime_iso=None)
    assert dag_project.last_updated(neither) == "_unknown_"


def test_collect_skips_unreadable_and_finds_the_escalated(tmp_path: Path) -> None:
    """An unreadable state.json is SKIPPED, never invented into an escalation."""
    _write_node(tmp_path, "escalated", dict(_ESCALATED_STATE))
    _write_node(tmp_path, "settled", {"state": "done", "tempo": "idle"})
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "state.json").write_text("{not json", encoding="utf-8")
    array = tmp_path / "array"
    array.mkdir()
    (array / "state.json").write_text("[]", encoding="utf-8")

    found = dag_project.collect_escalations(tmp_path)
    assert dag_project.escalation_ids(found) == ["escalated"]


def test_collect_on_a_missing_jobs_dir_is_empty_not_an_error(tmp_path: Path) -> None:
    assert dag_project.collect_escalations(tmp_path / "nope") == []


def test_dry_run_reports_the_empty_case_explicitly() -> None:
    """An empty result and a run that never happened must not look alike."""
    rendered = dag_project.render_dry_run([], projected_at="t")
    assert "0 escalations" in rendered
    assert "NO API call" in rendered


def test_dry_run_names_the_target_issue_and_the_label(tmp_path: Path) -> None:
    rendered = dag_project.render_dry_run(
        [_escalation(tmp_path)], projected_at="2026-08-07T00:00:00Z"
    )
    assert f"would comment on #{dag_project.DEFAULT_ESCALATION_ISSUE}" in rendered
    assert dag_tick.NEEDS_HUMAN_LABEL in rendered
    assert "nothing posted" in rendered


def test_r5_is_unvalidated_for_every_harness_native_payload(tmp_path: Path) -> None:
    """Structural, never semantic — and today that means UNVALIDATED, always.

    Measured 3-for-3 across CLI 2.1.207, 2.1.217 and 2.1.224. This asserts the
    CONSEQUENCE rather than the wording, so a future evidence field can flip it
    without the test having to be rewritten to permit the change.
    """
    assert "UNVALIDATED" in dag_project.r5_verdict(_escalation(tmp_path))


# --------------------------------------------------------------------------
# Phase 3 — the write path. The `gh` CLI is a real system boundary, so it is
# INJECTED (`tests/AGENTS.md`: prefer injecting over patching), and every test
# below substitutes a recorder rather than reaching the network.
# --------------------------------------------------------------------------


class _Gh:
    """A scripted `gh` runner that RECORDS every argv it was handed."""

    def __init__(self, replies: dict[str, dag_project.GhResult] | None = None) -> None:
        self.calls: list[list[str]] = []
        self.replies = replies or {}

    def __call__(self, cmd: list[str]) -> dag_project.GhResult:
        self.calls.append(cmd)
        for key, reply in self.replies.items():
            if key in " ".join(cmd):
                return reply
        return dag_project.GhResult(rc=0, stdout="[]")

    def verbs(self) -> list[str]:
        return [" ".join(c[:3]) for c in self.calls]


def _comments_json(*markers: str) -> str:
    return json.dumps([{"body": f"{m}\nbody text"} for m in markers])


def test_zero_escalations_makes_zero_api_calls() -> None:
    """Asserted, not incidental — the common case must not reach the network."""
    gh = _Gh()
    assert dag_project.project_all([], repo="o/r", run=gh, projected_at="t") == []
    assert gh.calls == [], "an idle projector that calls out can misfire when idle"


def test_a_fresh_escalation_posts_and_labels(tmp_path: Path) -> None:
    gh = _Gh()
    outcomes = dag_project.project_all(
        [_escalation(tmp_path)], repo="o/r", run=gh, projected_at="t"
    )
    assert [o.action for o in outcomes] == ["posted"]
    joined = gh.verbs()
    assert "gh issue comment" in joined
    assert "gh issue edit" in joined
    assert "gh label create" in joined


def test_running_twice_posts_nothing_the_second_time(tmp_path: Path) -> None:
    """The phase-3 gate: a dedupe verified only on the FIRST run is not a check."""
    escalation = _escalation(tmp_path)
    key = f"node={escalation.node_id} digest={escalation.digest}"

    first = _Gh()
    assert [
        o.action
        for o in dag_project.project_all(
            [escalation], repo="o/r", run=first, projected_at="t"
        )
    ] == ["posted"]

    # Second run sees the marker the first one left.
    second = _Gh(
        {
            "issues/623/comments": dag_project.GhResult(
                rc=0,
                stdout=_comments_json(
                    dag_project.marker(escalation.node_id, escalation.digest)
                ),
            )
        }
    )
    assert [
        o.action
        for o in dag_project.project_all(
            [escalation], repo="o/r", run=second, projected_at="t"
        )
    ] == ["skipped-duplicate"]
    assert "gh issue comment" not in second.verbs(), "the second run must post NOTHING"
    assert key in dag_project.marker(escalation.node_id, escalation.digest)


def test_a_new_question_from_the_same_node_posts_again(tmp_path: Path) -> None:
    """Dedupe tracks the QUESTION — a re-escalation must not be silenced."""
    old_marker = dag_project.marker("ad8baf35", dag_project.payload_digest(_JULY_22))
    gh = _Gh(
        {
            "issues/623/comments": dag_project.GhResult(
                rc=0, stdout=_comments_json(old_marker)
            )
        }
    )
    outcomes = dag_project.project_all(
        [_escalation(tmp_path)], repo="o/r", run=gh, projected_at="t"
    )
    assert [o.action for o in outcomes] == ["posted"]


def test_an_unreadable_comment_list_skips_rather_than_risking_a_duplicate(
    tmp_path: Path,
) -> None:
    """`None` and `set()` mean OPPOSITE things and must not be collapsed."""
    gh = _Gh({"issues/623/comments": dag_project.GhResult(rc=1, stderr="boom")})
    outcomes = dag_project.project_all(
        [_escalation(tmp_path)], repo="o/r", run=gh, projected_at="t"
    )
    assert [o.action for o in outcomes] == ["skipped-unreadable"]
    assert "gh issue comment" not in gh.verbs()


def test_a_closed_standing_issue_is_reopened_then_projected(tmp_path: Path) -> None:
    """A closed standing escalation issue IS the silence failure."""
    gh = _Gh({"issue view": dag_project.GhResult(rc=0, stdout="CLOSED\n")})
    outcomes = dag_project.project_all(
        [_escalation(tmp_path)], repo="o/r", run=gh, projected_at="t"
    )
    assert [o.action for o in outcomes] == ["posted"]
    assert "gh issue reopen" in gh.verbs()


def test_a_closed_bound_issue_falls_back_instead_of_being_reopened(
    tmp_path: Path,
) -> None:
    """Reopening a WORK issue is rework (#575 R7) — never a projector's call."""
    job_dir = _write_node(tmp_path, "bound", dict(_ESCALATED_STATE))
    (job_dir / dag_project.BINDING_FILENAME).write_text(
        json.dumps({"issue": 4242, "repo": "o/r"}), encoding="utf-8"
    )
    escalation = dag_project.escalation_from_state(
        "bound",
        dict(_ESCALATED_STATE),
        job_dir=job_dir,
        mtime=None,
        stall_after_s=120.0,
    )
    assert escalation is not None
    gh = _Gh({"issue view 4242": dag_project.GhResult(rc=0, stdout="CLOSED\n")})
    outcomes = dag_project.project_all(
        [escalation], repo="o/r", run=gh, projected_at="t"
    )
    assert [o.action for o in outcomes] == ["posted"]
    assert outcomes[0].issue == dag_project.DEFAULT_ESCALATION_ISSUE
    assert "gh issue reopen" not in gh.verbs(), "a work issue must NOT be reopened"


def test_an_existing_label_is_success_not_failure() -> None:
    """The steady state is "already there", and `gh` exits non-zero for it."""
    gh = _Gh(
        {
            "label create": dag_project.GhResult(
                rc=1, stderr="HTTP 422: Validation Failed (label already exists)"
            )
        }
    )
    assert dag_project.ensure_label("o/r", run=gh) is True

    broken = _Gh({"label create": dag_project.GhResult(rc=1, stderr="network down")})
    assert dag_project.ensure_label("o/r", run=broken) is False


def test_a_failed_post_is_reported_as_failed(tmp_path: Path) -> None:
    gh = _Gh({"issue comment": dag_project.GhResult(rc=1, stderr="403")})
    outcomes = dag_project.project_all(
        [_escalation(tmp_path)], repo="o/r", run=gh, projected_at="t"
    )
    assert [o.action for o in outcomes] == ["failed"]
    assert "403" in outcomes[0].detail


def test_marker_regex_ignores_a_prose_mention() -> None:
    """A comment DISCUSSING the marker must not register as one."""
    gh = _Gh(
        {
            "issues/623/comments": dag_project.GhResult(
                rc=0,
                stdout=json.dumps(
                    [{"body": "we key on `node=ad8baf35 digest=a5f7040626d9`"}]
                ),
            )
        }
    )
    assert dag_project.existing_markers(623, "o/r", run=gh) == set()


def test_run_project_refuses_when_neither_or_both_flags_are_given(
    tmp_path: Path,
) -> None:
    """Writing is outward-facing, so it is never a bare invocation's default."""
    args = argparse.Namespace(
        dry_run=False,
        write=False,
        repo=None,
        jobs_dir=str(tmp_path),
        stall_after=120.0,
        projected_at="t",
    )
    assert dag_project.run_project(args) == 2

    args.dry_run = True
    args.write = True
    assert dag_project.run_project(args) == 2

    args.write = False
    assert dag_project.run_project(args) == 0
