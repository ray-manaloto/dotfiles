# Copyright (c) 2026 Raymond Manaloto
"""Tests for the session review (#654).

The thing under test is a **noise filter**, so the tests that earn their place
are the rejections. A reviewer that lists everything is not a reviewer, and
every filter here was derived from a real first run rather than guessed: shell
constructs took 5 of the top 8 lane-1 rows, and "do NOT re-derive" instructions
took 9 of 17 lane-2 rows. Each of those measurements is pinned below, so
loosening a filter has to be a deliberate diff.

The other property pinned here is that the two lanes stay **disjoint**: lane 1
is blind to a reasoning sink and lane 2 is blind to a forgotten one-off, which
is why the default runs both and why asking for both exclusions is refused
rather than resolved.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import session_review
from dotfiles_setup.command_audit import BashCommand

REPO_ROOT = Path(__file__).parent.parent


def _cmd(command: str, session: str = "s1") -> BashCommand:
    # Dated well past every guard rule's `since`, so classification turns on
    # the command itself rather than on the pre-rule cutoff.
    return BashCommand(
        command=command,
        session=session,
        timestamp="2099-01-01T00:00:00Z",
        executed=True,
    )


# --------------------------------------------------------------------------- #
# Lane 1 — what counts as a shape
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "shape",
    [
        "while [",
        "for i",
        "python3 -",
        "bash -c",
        "-c <",
        "{ uv",
        "mkdir -p",
        "export FOO=/very/long/path",
        "export CLAUDE_CONFIG_DIR=/private/tmp/claude-501/a/long/workspace",
    ],
)
def test_constructs_mechanics_and_pasted_literals_are_not_shapes(shape: str) -> None:
    """Each of these took a top row on the first live run and named no workflow."""
    assert not session_review.is_reportable_shape(shape)


@pytest.mark.parametrize("shape", ["gh issue", "git add", "uv run", "docker buildx"])
def test_a_real_command_shape_is_reportable(shape: str) -> None:
    """The control arm: the filter must not reject everything."""
    assert session_review.is_reportable_shape(shape)


def test_a_shape_seen_across_sessions_outranks_a_more_frequent_one_grind() -> None:
    """Session spread is the ranking key, and it is not the same as frequency.

    A shape run twenty times in one session is one grind; a shape that comes
    back next session is a workflow, and only the second keeps costing. This is
    the deliberate difference from `command_audit`'s frequency ranking.
    """
    # Mutating commands on both sides: a READ (`gh issue view`) is classified
    # `diagnostic` by the shared miner and is correctly not a candidate, which
    # would make this test pass for the wrong reason.
    commands = [_cmd("gh issue edit 1 --add-label x", f"s{n}") for n in range(3)]
    commands += [_cmd("gh label create y", "solo") for _ in range(20)]
    ranked = session_review.shape_candidates(commands, min_occurrences=3)
    assert [c.shape for c in ranked] == ["gh issue", "gh label"]
    assert ranked[0].sessions == 3
    assert ranked[0].cross_session
    assert not ranked[1].cross_session


def test_the_ranking_actually_applies_the_shape_filter() -> None:
    """Binds the CALL SITE, not the predicate.

    Found by mutation: deleting the `is_reportable_shape` guard from
    `shape_candidates` left every other test green, because they all exercise
    the predicate directly. That is the stand-in shape
    `feedback_forbid_tokens_substring_fragile` names — assert the wiring, not
    just the thing being wired.
    """
    polls = [
        _cmd("while [ $SECONDS -lt 60 ]; do sleep 5; done", f"s{n}") for n in range(4)
    ]
    assert session_review.shape_candidates(polls) == []


def test_a_shape_below_the_floor_is_dropped() -> None:
    assert (
        session_review.shape_candidates([_cmd("gh issue edit 1 --add-label x")]) == []
    )


def test_a_read_only_command_is_not_a_candidate() -> None:
    """A read-only command is already cheap, so it is not a candidate.

    The miner classifies `gh issue view` as `diagnostic`, and inheriting that
    judgement rather than re-deciding it is the point of reusing the miner.
    """
    commands = [_cmd("gh issue view 1") for _ in range(9)]
    assert session_review.shape_candidates(commands) == []


def test_a_canonical_mise_command_is_not_a_candidate() -> None:
    """It is already the thing a skill would propose — proposing it is a loop."""
    commands = [_cmd("mise run lint") for _ in range(5)]
    assert session_review.shape_candidates(commands) == []


# --------------------------------------------------------------------------- #
# Lane 2 — what counts as a passage
# --------------------------------------------------------------------------- #


def test_a_recorded_slog_is_surfaced() -> None:
    hits = session_review.narrative_hits(
        "I transcribed the recipe by hand, ~15 turns.\n", "notes.md"
    )
    assert len(hits) == 1
    assert hits[0].line_number == 1


def test_only_one_hit_per_line_even_when_several_markers_fire() -> None:
    """Keep one row per passage.

    Three rows pointing at one sentence would inflate the apparent evidence for
    a candidate rather than describe it.
    """
    hits = session_review.narrative_hits(
        "did it by hand, manually, ~15 turns, had to be re-run\n", "notes.md"
    )
    assert len(hits) == 1


@pytest.mark.parametrize(
    "line",
    [
        "## Mechanical facts already established (do NOT re-derive)",
        "read that row rather than re-deriving it",
        "so the next session gets it for free — no need to re-derive",
        "`gh pr checks --watch` over hand-rolled poll loops",
    ],
)
def test_an_instruction_not_to_do_it_by_hand_is_not_a_record_of_doing_it(
    line: str,
) -> None:
    """These were 9 of 17 rows on the first live run, and none was a candidate.

    A handoff telling the next session not to re-derive something is the
    OPPOSITE of a finding: it is the previous session having already paid.
    """
    assert session_review.narrative_hits(line + "\n", "notes.md") == []


def test_the_suppressor_does_not_swallow_a_genuine_rederivation() -> None:
    """Control arm for the suppressors — they must not reject the real thing."""
    hits = session_review.narrative_hits("I re-derived a known fact\n", "notes.md")
    assert len(hits) == 1


def test_a_tail_bound_keeps_the_real_line_number() -> None:
    """A line number relative to the window is a citation nobody can open."""
    text = "\n".join(["filler"] * 500 + ["I did it by hand"])
    windowed, offset = session_review.tail_text(text, 10)
    assert offset == 491
    hits = session_review.narrative_hits(windowed, "notes.md")
    assert hits[0].line_number + offset == 501


def test_the_handoff_glob_is_bounded_to_the_newest(tmp_path: Path) -> None:
    """The archive answers a different question than 'what did THIS session do'."""
    plans = tmp_path / ".agent" / "plans"
    plans.mkdir(parents=True)
    for n, name in enumerate(["session-a.md", "session-b.md", "session-c.md"]):
        path = plans / name
        path.write_text("x\n")
        os_time = 1_000_000 + n * 100
        os.utime(path, (os_time, os_time))
    resolved = session_review.narrative_paths(
        tmp_path, (".agent/plans/session-*.md",), glob_limit=1
    )
    assert [p.name for p in resolved] == ["session-c.md"]


def test_a_literal_path_is_never_bounded(tmp_path: Path) -> None:
    """The notepad is the one file you always want, glob limit or not."""
    (tmp_path / ".agent").mkdir()
    (tmp_path / ".agent" / "notepad.md").write_text("x\n")
    resolved = session_review.narrative_paths(
        tmp_path, (".agent/notepad.md",), glob_limit=0
    )
    assert [p.name for p in resolved] == ["notepad.md"]


# --------------------------------------------------------------------------- #
# The report and the entry point
# --------------------------------------------------------------------------- #


def test_the_report_states_both_windows_it_looked_through() -> None:
    """A bound-limited search that does not declare its bound reads as complete.

    The transcript count is FILES (roots plus nested subagent transcripts), and
    calling it a session count overstates the window — it said "26 session(s)"
    on the first live run against `--sessions 6`.
    """
    report = session_review.render_report(
        [], [], transcripts_scanned=26, tail_lines=400, lanes=("transcript",)
    )
    assert "NOT a session count" in report
    assert "last 400 lines" in report


def test_an_empty_lane_one_says_what_that_does_and_does_not_mean() -> None:
    report = session_review.render_report(
        [], [], transcripts_scanned=0, tail_lines=None, lanes=("transcript",)
    )
    assert "leaves no repeated command" in report


def test_the_template_forces_the_avoided_cost() -> None:
    """#607/#608's test: a candidate with no concrete cost is a preference."""
    report = session_review.render_report(
        [], [], transcripts_scanned=0, tail_lines=None, lanes=("narrative",)
    )
    assert "Cost avoided" in report


def test_asking_for_both_exclusive_lanes_is_refused_not_resolved(
    tmp_path: Path,
) -> None:
    """The lanes are disjoint, so guessing which one was meant loses a finding."""
    assert (
        session_review.session_review_main(
            tmp_path,
            lanes=session_review.LaneChoice(transcript_only=True, narrative_only=True),
        )
        == 2
    )


def test_the_narrative_lane_runs_without_touching_transcripts(tmp_path: Path) -> None:
    agent = tmp_path / ".agent"
    agent.mkdir()
    (agent / "notepad.md").write_text("I transcribed the recipe by hand\n")
    out = tmp_path / "report.md"
    assert (
        session_review.session_review_main(
            tmp_path,
            lanes=session_review.LaneChoice(narrative_only=True),
            output=out,
        )
        == 0
    )
    assert "by hand" in out.read_text()
    assert "Lanes run: narrative" in out.read_text()


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_mise_task_calls_the_cli() -> None:
    mise_toml = (REPO_ROOT / "mise.toml").read_text()
    assert "[tasks.session-review]" in mise_toml
    assert "dotfiles-setup session-review" in mise_toml
