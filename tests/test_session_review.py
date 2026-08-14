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

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import session_ledger, session_review
from dotfiles_setup.command_audit import BashCommand
from dotfiles_setup.main import setup_parser

REPO_ROOT = Path(__file__).parent.parent


def _mise_project_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment where an explicit project config is discoverable."""
    env = dict(os.environ if base is None else base)
    env.pop("MISE_IGNORED_CONFIG_PATHS", None)
    return env


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


def test_goal_history_is_a_default_session_review_source(tmp_path: Path) -> None:
    """Goal changes must enter the review corpus without caller opt-in."""
    history = tmp_path / "docs" / "agents" / "goal-history.md"
    history.parent.mkdir(parents=True)
    history.write_text("# Goal history\n")

    resolved = session_review.narrative_paths(tmp_path)

    assert history in resolved


def test_tracked_goal_history_exposes_the_required_iteration_contract() -> None:
    """The durable artifact must carry every field the workflow promised."""
    history = REPO_ROOT / "docs" / "agents" / "goal-history.md"
    assert history.is_file()
    text = history.read_text()
    for field in (
        "Iteration ID",
        "Prior goal digest",
        "Current goal digest",
        "Changed requirement",
        "Reason",
        "Evidence",
        "Affected tickets",
        "Disposition",
        "Topology and ownership",
        "```mermaid",
    ):
        assert field in text


def test_goal_history_validator_accepts_the_tracked_history() -> None:
    history = REPO_ROOT / "docs" / "agents" / "goal-history.md"
    assert session_review.goal_history_errors(history.read_text()) == ()


def test_goal_history_validator_rejects_a_missing_iteration_field() -> None:
    history = REPO_ROOT / "docs" / "agents" / "goal-history.md"
    hostile = history.read_text().replace("- **Disposition:**", "- **Verdict:**", 1)

    errors = session_review.goal_history_errors(hostile)

    assert any("missing Disposition" in error for error in errors)


def test_goal_history_validator_rejects_a_malformed_current_digest() -> None:
    history = REPO_ROOT / "docs" / "agents" / "goal-history.md"
    hostile = history.read_text().replace(
        "sha256:12db9f86a5d17902e58b0cdc7330939cf2f1e025fb2a06d96c056860f6349385",
        "sha256:not-a-digest",
        1,
    )

    errors = session_review.goal_history_errors(hostile)

    assert any("malformed Current goal digest" in error for error in errors)


def _git_repo_with_goal_history(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    history = repo / "docs" / "agents" / "goal-history.md"
    history.parent.mkdir(parents=True)
    history.write_bytes(
        (REPO_ROOT / "docs" / "agents" / "goal-history.md").read_bytes()
    )
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Goal History Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "goal-history@test.invalid"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", str(history)], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "add history"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "update-ref",
            "refs/remotes/origin/main",
            "HEAD",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "switch", "-qc", "goal-history-test"], check=True
    )
    return repo, history


def test_session_review_refuses_a_rewrite_of_landed_history(tmp_path: Path) -> None:
    repo, history = _git_repo_with_goal_history(tmp_path)
    history.write_text(history.read_text().replace("PR #750", "PR #999", 1))

    assert (
        session_review.session_review_main(
            repo, lanes=session_review.LaneChoice(narrative_only=True)
        )
        == 2
    )


def test_session_review_refuses_a_two_commit_history_rewrite(tmp_path: Path) -> None:
    """The authorized base, not HEAD^, catches a rewrite two commits back."""
    repo, history = _git_repo_with_goal_history(tmp_path)
    history.write_text(history.read_text().replace("PR #750", "PR #999", 1))
    subprocess.run(["git", "-C", str(repo), "add", str(history)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "rewrite history"], check=True
    )
    unrelated = repo / "unrelated.txt"
    unrelated.write_text("second commit\n")
    subprocess.run(["git", "-C", str(repo), "add", str(unrelated)], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "unrelated"], check=True)

    assert (
        session_review.session_review_main(
            repo, lanes=session_review.LaneChoice(narrative_only=True)
        )
        == 2
    )


def _append_second_goal(history: Path) -> None:
    goal = "Record the second accepted goal."
    digest = hashlib.sha256(goal.encode()).hexdigest()
    prior = "sha256:12db9f86a5d17902e58b0cdc7330939cf2f1e025fb2a06d96c056860f6349385"
    history.write_text(
        history.read_text()
        + f"""
## 2026-08-14 — second accepted goal

- **Iteration ID:** `dotfiles-goal-20260814-002`
- **Prior goal digest:** `{prior}`
- **Current goal digest:** `sha256:{digest}`
- **Changed requirement:** Record a second append-only iteration.
- **Reason:** The accepted goal changed.
- **Evidence:** issue #753 records the follow-up.
- **Affected tickets:** dotfiles #753.
- **Disposition:** `ACCEPTED`.
- **Topology and ownership:** One dotfiles writer remains active.

### Current goal

> {goal}

### Current workflow

```mermaid
flowchart LR
    A["Append"] --> V["Verify"]
```
"""
    )


def test_session_review_refuses_rewrite_of_branch_appended_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Commit B cannot rewrite the valid entry commit A appended."""
    repo, history = _git_repo_with_goal_history(tmp_path)
    _append_second_goal(history)
    subprocess.run(["git", "-C", str(repo), "add", str(history)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "append second goal"],
        check=True,
    )
    history.write_text(
        history.read_text().replace(
            "issue #753 records the follow-up", "issue #999 replaces the evidence", 1
        )
    )
    subprocess.run(["git", "-C", str(repo), "add", str(history)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "rewrite second goal"],
        check=True,
    )
    monkeypatch.setenv("DOTFILES_GOAL_HISTORY_BASE_REF", "HEAD")

    assert (
        session_review.session_review_main(
            repo, lanes=session_review.LaneChoice(narrative_only=True)
        )
        == 2
    )


def test_session_review_refuses_rewritten_bootstrap_commit(tmp_path: Path) -> None:
    """A bootstrap added in commit A becomes immutable before commit B."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Goal History Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "goal-history@test.invalid"],
        check=True,
    )
    seed = repo / "seed.txt"
    seed.write_text("authorized base\n")
    subprocess.run(["git", "-C", str(repo), "add", str(seed)], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "base"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "update-ref",
            "refs/remotes/origin/main",
            "HEAD",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "switch", "-qc", "goal-history-test"], check=True
    )
    history = repo / "docs" / "agents" / "goal-history.md"
    history.parent.mkdir(parents=True)
    history.write_bytes(
        (REPO_ROOT / "docs" / "agents" / "goal-history.md").read_bytes()
    )
    subprocess.run(["git", "-C", str(repo), "add", str(history)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "bootstrap history"],
        check=True,
    )
    history.write_text(history.read_text().replace("PR #750", "PR #999", 1))
    subprocess.run(["git", "-C", str(repo), "add", str(history)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "rewrite bootstrap"],
        check=True,
    )

    assert (
        session_review.session_review_main(
            repo, lanes=session_review.LaneChoice(narrative_only=True)
        )
        == 2
    )


def test_session_review_refuses_a_rewritten_goal_with_recomputed_digest(
    tmp_path: Path,
) -> None:
    repo, history = _git_repo_with_goal_history(tmp_path)
    text = history.read_text()
    old_goal = (
        "Implement and land the dotfiles append-only goal-history contract. Keep "
        "it discoverable to session review, enforce required iteration structure, "
        "and record orchestration topology changes without duplicating knowledge-base "
        "Graphify, SkillOpt, shared expert-bundle, or devcontainer work."
    )
    new_goal = "Replace the accepted goal after it landed."
    new_digest = hashlib.sha256(new_goal.encode()).hexdigest()
    text = text.replace(old_goal, new_goal, 1)
    text = text.replace(
        "12db9f86a5d17902e58b0cdc7330939cf2f1e025fb2a06d96c056860f6349385",
        new_digest,
        1,
    )
    history.write_text(text)

    assert (
        session_review.session_review_main(
            repo, lanes=session_review.LaneChoice(narrative_only=True)
        )
        == 2
    )


def test_session_review_refuses_a_missing_history_in_a_git_checkout(
    tmp_path: Path,
) -> None:
    repo, history = _git_repo_with_goal_history(tmp_path)
    history.unlink()

    assert (
        session_review.session_review_main(
            repo, lanes=session_review.LaneChoice(narrative_only=True)
        )
        == 2
    )


def test_narrative_review_refuses_an_invalid_goal_history(tmp_path: Path) -> None:
    history = tmp_path / "docs" / "agents" / "goal-history.md"
    history.parent.mkdir(parents=True)
    history.write_text("# Goal history\n\n## 2026-08-14 — incomplete\n")

    assert (
        session_review.session_review_main(
            tmp_path,
            lanes=session_review.LaneChoice(narrative_only=True),
        )
        == 2
    )


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


def test_requirements_only_is_exclusive_with_the_automation_lanes(
    tmp_path: Path,
) -> None:
    assert (
        session_review.session_review_main(
            tmp_path,
            lanes=session_review.LaneChoice(
                transcript_only=True,
                requirements_only=True,
            ),
        )
        == 2
    )


def test_session_limit_must_be_positive(tmp_path: Path) -> None:
    assert session_review.session_review_main(tmp_path, sessions=0) == 2


def test_rebuild_cache_flag_reaches_the_lane_choice() -> None:
    args = setup_parser().parse_args(["session-review", "--rebuild-cache"])

    assert args.rebuild_cache is True


@pytest.mark.parametrize("iterations", [0, 6])
def test_iteration_limit_is_bounded(tmp_path: Path, iterations: int) -> None:
    assert (
        session_review.session_review_main(
            tmp_path,
            lanes=session_review.LaneChoice(max_iterations=iterations),
        )
        == 2
    )


def test_requirements_only_runs_through_the_public_library_entry_point(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    (project / ".git").mkdir()
    sessions = tmp_path / "codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    fixture = REPO_ROOT / "tests" / "fixtures" / "session_review" / "codex-root.jsonl"
    text = fixture.read_text().replace('"cwd":"/repo"', f'"cwd":"{project}"')
    (sessions / "root.jsonl").write_text(text)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty-claude"))
    output = project / "requirements.md"

    result = session_review.session_review_main(
        project,
        lanes=session_review.LaneChoice(
            requirements_only=True,
            source_repo_root=project,
            session_id="root-session",
        ),
        sessions=5,
        output=output,
    )

    assert result == 1
    report = output.read_text()
    assert "Session requirement and promise ledger" in report
    assert "Do not publish" in report
    assert "fixture-payload" not in report
    assert output.with_suffix(".md.evidence.json").is_file()
    assert output.with_suffix(".md.cutoffs.json").is_file()
    assert output.with_suffix(".md.iteration.json").is_file()
    evidence = json.loads(output.with_suffix(".md.evidence.json").read_text())
    assert evidence["selection_certification"] == "explicit_session_id"
    iteration = json.loads(output.with_suffix(".md.iteration.json").read_text())
    assert iteration["action"] == "needs_agent_action"
    assert iteration["unreviewed_requirement_ids"]
    claims_path = output.with_suffix(".md.claims.json")
    claims_index = json.loads(claims_path.read_text())
    claim_rows = [
        row
        for segment in claims_index["segments"]
        for row in json.loads(
            claims_path.with_name(f"{claims_path.name}{segment['suffix']}").read_text()
        )["claims"]
    ]
    paired = next(row for row in claim_rows if row["context_kind"] == "paired_question")
    assert paired["bounded_context"].startswith(
        "question id=publication_authority text="
    )
    assert (
        paired["context_sha256"]
        == hashlib.sha256(paired["bounded_context"].encode()).hexdigest()
    )
    assert paired["candidate_receipt_refs"] == []


def test_semantic_dispositions_cli_input_can_close_validated_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "repo"
    (project / ".git").mkdir(parents=True)
    sessions = tmp_path / "codex" / "sessions"
    sessions.mkdir(parents=True)
    transcript = sessions / "root.jsonl"
    rows = [
        {"type": "session_meta", "payload": {"id": "active", "cwd": str(project)}},
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "request",
                "role": "user",
                "content": [{"type": "input_text", "text": "Keep this local."}],
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "message": "Keep this local.",
            },
        },
    ]
    transcript.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    initial = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, transcript)]
    )
    semantic = tmp_path / "semantic-dispositions.json"
    semantic.write_text(
        json.dumps(
            [
                {
                    "claim_id": initial.requirements[0].requirement_id,
                    "status": "satisfied",
                    "rationale": "The bounded control verifies local-only behavior.",
                    "receipt_refs": ["test:test_local_only_control"],
                }
            ]
        )
    )
    claude_config = tmp_path / "claude"
    claude_project = session_review.command_audit.project_dir(
        claude_config / "projects", project
    )
    claude_project.mkdir(parents=True)
    (claude_project / "clean.jsonl").write_text(
        json.dumps(
            {
                "type": "assistant",
                "sessionId": "clean-claude",
                "message": {"content": "Clean Claude transcript."},
            }
        )
        + "\n"
    )
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_config))
    output = project / "requirements.md"

    result = session_review.session_review_main(
        project,
        lanes=session_review.LaneChoice(
            requirements_only=True,
            source_repo_root=project,
            codex_session_id="active",
            semantic_dispositions=semantic,
        ),
        sessions=5,
        output=output,
    )

    assert result == 0
    evidence = json.loads(output.with_suffix(".md.evidence.json").read_text())
    assert evidence["semantic_disposition_count"] == 1
    report = output.read_text()
    assert "satisfied" in report
    assert "test:test_local_only_control" in report


def test_semantic_dispositions_cli_persists_open_claim_without_converging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "repo"
    (project / ".git").mkdir(parents=True)
    sessions = tmp_path / "codex" / "sessions"
    sessions.mkdir(parents=True)
    transcript = sessions / "root.jsonl"
    request = "Keep the follow-up open."
    transcript.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "type": "session_meta",
                    "payload": {"id": "active", "cwd": str(project)},
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "id": "request",
                        "role": "user",
                        "content": [{"type": "input_text", "text": request}],
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": request},
                },
            )
        )
        + "\n"
    )
    initial = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, transcript)]
    )
    semantic = tmp_path / "semantic-dispositions.json"
    semantic.write_text(
        json.dumps(
            [
                {
                    "claim_id": initial.requirements[0].requirement_id,
                    "status": "open",
                    "rationale": "Issue 740 owns the remaining work.",
                    "receipt_refs": ["issue:#740"],
                }
            ]
        )
    )
    claude_config = tmp_path / "claude"
    claude_project = session_review.command_audit.project_dir(
        claude_config / "projects", project
    )
    claude_project.mkdir(parents=True)
    (claude_project / "clean.jsonl").write_text(
        json.dumps(
            {
                "type": "assistant",
                "sessionId": "clean-claude",
                "message": {"content": "Clean Claude transcript."},
            }
        )
        + "\n"
    )
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_config))
    output = project / "requirements.md"

    result = session_review.session_review_main(
        project,
        lanes=session_review.LaneChoice(
            requirements_only=True,
            source_repo_root=project,
            codex_session_id="active",
            semantic_dispositions=semantic,
        ),
        output=output,
    )

    assert result == 1
    report = output.read_text()
    assert "open" in report
    assert "issue:#740" in report
    iteration = json.loads(output.with_suffix(".md.iteration.json").read_text())
    assert iteration["action"] == "needs_agent_action"
    assert iteration["unreviewed_requirement_ids"] == []
    assert iteration["open_requirement_ids"] == [initial.requirements[0].requirement_id]


def test_public_loop_needs_agent_action_until_prevention_is_disposed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    (project / ".git").mkdir()
    sessions = tmp_path / "codex" / "sessions"
    sessions.mkdir(parents=True)
    rows = [
        {"type": "session_meta", "payload": {"id": "risk", "cwd": str(project)}},
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "risk-message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "The fnox credential launcher was missing.",
                    }
                ],
            },
        },
    ]
    (sessions / "risk.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty-claude"))
    output = project / "review.md"
    lanes = session_review.LaneChoice(
        requirements_only=True,
        source_repo_root=project,
        max_iterations=5,
    )
    assert session_review.session_review_main(project, lanes=lanes, output=output) == 1
    packet = json.loads(output.with_suffix(".md.iteration.json").read_text())
    assert packet["action"] == "needs_agent_action"
    assert packet["number"] == 1
    assert packet["repo_root"] == str(project)
    assert packet["max_iterations"] == 5
    assert packet["remaining_iterations"] == 4
    assert packet["required_roles"] == [
        "specialized_fixer",
        "independent_qa",
        "adversarial_reviewer",
    ]
    assert {item["kind"] for item in packet["artifacts"]} == {
        "report",
        "evidence",
        "cutoffs",
        "claims",
        "omissions",
        "semantic_disposition_draft",
    }
    for artifact in packet["artifacts"]:
        artifact_path = Path(artifact["path"])
        assert artifact_path.is_file()
        assert (
            hashlib.sha256(artifact_path.read_bytes()).hexdigest() == artifact["sha256"]
        )
    cutoff_index_path = output.with_suffix(".md.cutoffs.json")
    cutoff_index = json.loads(cutoff_index_path.read_text())
    assert cutoff_index["segment_count"] == 1
    segment_ref = cutoff_index["segments"][0]
    segment_path = cutoff_index_path.with_name(
        f"{cutoff_index_path.name}{segment_ref['suffix']}"
    )
    assert segment_path.is_file()
    assert (
        hashlib.sha256(segment_path.read_bytes()).hexdigest() == segment_ref["sha256"]
    )
    evidence = json.loads(output.with_suffix(".md.evidence.json").read_text())
    assert (
        evidence["cutoff_manifest_sha256"]
        == hashlib.sha256(cutoff_index_path.read_bytes()).hexdigest()
    )
    claims_path = output.with_suffix(".md.claims.json")
    claims = json.loads(claims_path.read_text())
    assert claims["claim_count"] == 0
    assert all(
        claims_path.with_name(f"{claims_path.name}{item['suffix']}").is_file()
        for item in claims["segments"]
    )
    draft_path = output.with_suffix(".md.semantic-dispositions.draft.json")
    draft = json.loads(draft_path.read_text())
    assert draft["disposition_count"] == claims["claim_count"]


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
    assert "[tasks.session-requirements]" in mise_toml
    assert 'arg "[max_sessions]"' in mise_toml
    assert '--sessions "${usage_max_sessions?}"' in mise_toml
    assert 'arg "<source_repo_root>"' in mise_toml
    assert "--source-repo-root" in mise_toml
    assert "uv run --project python dotfiles-setup session-review" in mise_toml


def test_skill_requires_agent_team_receipts_before_complete() -> None:
    skill = (
        REPO_ROOT / ".claude" / "skills" / "session-review" / "SKILL.md"
    ).read_text()
    for token in (
        "specialized fixer",
        "independent QA",
        "adversarial reviewer",
        "mutation_receipt",
        "gate_receipt",
        "issue_receipt",
        "cannot become `COMPLETE`",
    ):
        assert token in skill


def test_callable_codex_skill_is_byte_identical_and_normally_gated() -> None:
    claude = REPO_ROOT / ".claude" / "skills" / "session-review" / "SKILL.md"
    codex = REPO_ROOT / ".agents" / "skills" / "session-review" / "SKILL.md"
    assert codex.is_file()
    assert codex.read_bytes() == claude.read_bytes()
    hk = (REPO_ROOT / "hk.pkl").read_text()
    assert "session_review_skill_parity" in hk
    assert "cmp -s .claude/skills/session-review/SKILL.md" in hk


def test_mise_requirement_task_exposes_required_root_and_configurable_limit(
    tmp_path: Path,
) -> None:
    hostile_root = tmp_path / "hostile-project"
    hostile_root.mkdir()
    (hostile_root / "mise.toml").write_text(
        '[tasks.session-requirements]\nrun = "printf hostile"\n',
        encoding="utf-8",
    )
    container_env = os.environ.copy()
    container_env["MISE_IGNORED_CONFIG_PATHS"] = str(REPO_ROOT / "mise.toml")
    container_env["MISE_TRUSTED_CONFIG_PATHS"] = os.pathsep.join(
        (str(REPO_ROOT), str(hostile_root))
    )
    result = subprocess.run(
        [
            "mise",
            "--cd",
            str(REPO_ROOT),
            "tasks",
            "info",
            "--json",
            "session-requirements",
        ],
        cwd=hostile_root,
        env=_mise_project_env(container_env),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    arguments = payload["usage_spec"]["cmd"]["args"]
    assert arguments[0]["name"] == "source_repo_root"
    assert arguments[0]["required"]
    assert arguments[1]["name"] == "max_sessions"
    assert arguments[1]["default"] == ["5"]
    assert [item["name"] for item in arguments] == [
        "source_repo_root",
        "max_sessions",
        "max_iterations",
    ]
    assert "uv run --project python" in payload["run"][0]

    ignored = subprocess.run(
        [
            "mise",
            "--cd",
            str(REPO_ROOT),
            "tasks",
            "info",
            "--json",
            "session-requirements",
        ],
        cwd=hostile_root,
        env=container_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert ignored.returncode != 0

    unbound = subprocess.run(
        ["mise", "tasks", "info", "--json", "session-requirements"],
        cwd=hostile_root,
        env=_mise_project_env(container_env),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert unbound.returncode == 0
    assert json.loads(unbound.stdout)["run"] == ["printf hostile"]


def test_real_cli_runs_requirements_only(tmp_path: Path) -> None:
    sessions = tmp_path / "codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    fixture = REPO_ROOT / "tests" / "fixtures" / "session_review" / "codex-root.jsonl"
    (sessions / "root.jsonl").write_text(
        fixture.read_text().replace('"cwd":"/repo"', f'"cwd":"{REPO_ROOT}"')
    )
    output = tmp_path / "requirements.md"
    env = os.environ.copy()
    env["CODEX_HOME"] = str(tmp_path / "codex")
    env["CLAUDE_CONFIG_DIR"] = str(tmp_path / "empty-claude")
    env.pop("CODEX_THREAD_ID", None)
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(REPO_ROOT / "python"),
            "dotfiles-setup",
            "session-review",
            "--requirements-only",
            "--source-repo-root",
            str(REPO_ROOT),
            "--codex-session-id",
            "root-session",
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 1
    iteration = json.loads(output.with_suffix(".md.iteration.json").read_text())
    assert iteration["action"] == "needs_agent_action"
    assert iteration["unreviewed_requirement_ids"]
    assert "Do not publish" in output.read_text()


def test_default_cli_includes_automation_and_dual_provider_requirements(
    tmp_path: Path,
) -> None:
    codex_sessions = tmp_path / "codex" / "sessions" / "2026" / "08" / "12"
    codex_sessions.mkdir(parents=True)
    fixture_root = REPO_ROOT / "tests" / "fixtures" / "session_review"
    (codex_sessions / "root.jsonl").write_text(
        (fixture_root / "codex-root.jsonl")
        .read_text()
        .replace('"cwd":"/repo"', f'"cwd":"{REPO_ROOT}"')
    )
    claude_projects = tmp_path / "claude" / "projects"
    claude_project = claude_projects / session_review.command_audit.encode_cwd(
        REPO_ROOT
    )
    claude_project.mkdir(parents=True)
    (claude_project / "claude-root.jsonl").write_bytes(
        (fixture_root / "claude-root.jsonl").read_bytes()
    )
    output = REPO_ROOT / ".agent" / "test-default-session-review.md"
    output.parent.mkdir(exist_ok=True)
    env = {
        **os.environ,
        "CODEX_HOME": str(tmp_path / "codex"),
        "CODEX_THREAD_ID": "root-session",
        "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
    }
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(REPO_ROOT / "python"),
                "dotfiles-setup",
                "session-review",
                "--output",
                str(output),
            ],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 1, result.stderr
        assert output.is_file(), result.stderr
        report = output.read_text()
        assert "what was done by hand that should be code" in report
        assert "Session requirement and promise ledger" in report
        assert "Do not publish" in report
        assert "Only free tools" in report
        assert "Provider census" in report
    finally:
        for path in output.parent.glob(f"{output.name}*"):
            path.unlink()


def test_requirements_cli_cannot_certify_active_session_from_recency(
    tmp_path: Path,
) -> None:
    sessions = tmp_path / "codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    fixture = REPO_ROOT / "tests" / "fixtures" / "session_review" / "codex-root.jsonl"
    (sessions / "root.jsonl").write_text(
        fixture.read_text().replace('"cwd":"/repo"', f'"cwd":"{REPO_ROOT}"')
    )
    env = os.environ.copy()
    env["CODEX_HOME"] = str(tmp_path / "codex")
    env["CLAUDE_CONFIG_DIR"] = str(tmp_path / "empty-claude")
    env.pop("CODEX_THREAD_ID", None)
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(REPO_ROOT / "python"),
            "dotfiles-setup",
            "session-review",
            "--requirements-only",
            "--source-repo-root",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 1
    assert "active session identity is unverified" in result.stderr


def test_codex_session_id_uses_nonempty_environment_fallback() -> None:
    env = os.environ.copy()
    env["CODEX_THREAD_ID"] = "codex-active"
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(REPO_ROOT / "python"),
            "python",
            "-c",
            (
                "from dotfiles_setup.main import setup_parser; "
                "print(setup_parser().parse_args(['session-review']).codex_session_id)"
            ),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "codex-active"


def test_mise_never_forwards_an_empty_codex_session_id() -> None:
    task = (REPO_ROOT / "mise.toml").read_text()
    start = task.index("[tasks.session-requirements]")
    end = task.index("[tasks.session-review-gate]", start)
    section = task[start:end]
    assert "--session-id" not in section
    assert '"${usage_session_id?}"' not in section


def test_requirements_cli_requires_an_explicit_source_root() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(REPO_ROOT / "python"),
            "dotfiles-setup",
            "session-review",
            "--requirements-only",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 2
    assert "requires --source-repo-root" in result.stderr


def test_requirements_cli_fails_closed_when_recorded_cwd_does_not_match(
    tmp_path: Path,
) -> None:
    unmatched = tmp_path / "unmatched"
    (unmatched / ".git").mkdir(parents=True)
    env = {
        **os.environ,
        "CODEX_HOME": str(tmp_path / "empty-codex"),
        "CLAUDE_CONFIG_DIR": str(tmp_path / "empty-claude"),
    }
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(REPO_ROOT / "python"),
            "dotfiles-setup",
            "session-review",
            "--requirements-only",
            "--source-repo-root",
            str(unmatched),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 1
    assert "no transcripts matched recorded cwd" in result.stderr
