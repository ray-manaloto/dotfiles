# Copyright (c) 2026 Raymond Manaloto
"""Tests for the sanctioned main-checkout writes (dotfiles_setup.handoff_inbox).

Every CLI arm runs from a REAL linked worktree (``git worktree add``) and
asserts the write landed in the MAIN checkout, because reaching the main
checkout from a lane is the whole point of the task (Ray ruling b).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import coordinator_handoff, handoff_inbox
from dotfiles_setup.main import setup_parser

NEWEST = "dotfiles-20261003T144132.124570000-05.coordinator"
OLDER = "dotfiles-20261003T140808.926861000-05.coordinator"
NEWEST_ID = "aaaaaaaa-1111-2222-3333-444444444444"
OLDER_ID = "bbbbbbbb-1111-2222-3333-444444444444"
LANE_ID = "cccccccc-1111-2222-3333-444444444444"


def _git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True, text=True)


@pytest.fixture
def repos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A main checkout plus a linked worktree; cwd is the worktree."""
    main_repo = tmp_path / "main"
    lane = tmp_path / "lane-wt"
    _git("init", "-q", "-b", "main", str(main_repo))
    _git(
        "-C",
        str(main_repo),
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t.invalid",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "init",
    )
    _git("-C", str(main_repo), "worktree", "add", "-q", "-b", "lane", str(lane))
    monkeypatch.chdir(lane)
    return main_repo.resolve(), lane.resolve()


def _job(jobs_dir: Path, session_id: str, name: str, created_at: str) -> None:
    path = jobs_dir / session_id[:8] / "state.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"sessionId": session_id, "name": name, "createdAt": created_at})
    )


@pytest.fixture
def jobs_dir(tmp_path: Path) -> Path:
    jobs = tmp_path / "jobs"
    _job(jobs, OLDER_ID, OLDER, "2026-10-03T19:08:09.393Z")
    _job(jobs, NEWEST_ID, NEWEST, "2026-10-03T19:41:32.500Z")
    _job(jobs, LANE_ID, "dotfiles-20261003T143441.L0-urgent-code", "2026-10-03T19:50Z")
    return jobs


def _run(argv: list[str]) -> int:
    args = setup_parser().parse_args(["coordinator-handoff", "inbox", *argv])
    return coordinator_handoff.main(args, Path.cwd())


# ------------------------------------------------------------------- any caller


def test_append_from_a_linked_worktree_lands_in_the_main_checkout(
    repos: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    main_repo, lane = repos

    assert _run(["append", "--lane", "L9", "--message", "first"]) == 0
    assert _run(["append", "--lane", "L9", "--title", "two", "--message", "2nd"]) == 0

    target = main_repo / ".agent" / "plans" / "handoff-inbox" / "L9.md"
    text = target.read_text()
    assert text.index("first") < text.index("2nd")
    assert "— L9\n\nfirst\n" in text
    assert "— two\n\n2nd\n" in text
    assert not (lane / ".agent").exists()
    assert capsys.readouterr().out.splitlines() == [str(target), str(target)]


@pytest.mark.usefixtures("repos")
def test_list_and_read_show_the_main_checkout_inbox(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _run(["append", "--lane", "L9", "--message", "body"])
    capsys.readouterr()

    assert _run(["list"]) == 0
    assert capsys.readouterr().out.startswith("L9.md\t")
    assert _run(["read", "--lane", "L9"]) == 0
    assert "body" in capsys.readouterr().out
    assert _run(["read", "--lane", "absent"]) == handoff_inbox.RC_NOT_FOUND


@pytest.mark.parametrize("lane", ["../escape", "a/b", ".hidden", ""])
def test_a_lane_name_that_could_escape_is_refused(
    repos: tuple[Path, Path], lane: str
) -> None:
    main_repo, _ = repos

    assert _run(["append", "--lane", lane, "--message", "x"]) == 2
    assert not (main_repo / ".agent" / "plans").exists()


def test_empty_body_and_multiline_title_are_refused(repos: tuple[Path, Path]) -> None:
    main_repo, _ = repos

    assert _run(["append", "--lane", "L9", "--message", "  \n"]) == 2
    assert _run(["append", "--lane", "L9", "--title", "a\nb", "--message", "x"]) == 2
    assert not (main_repo / ".agent" / "plans").exists()


# -------------------------------------------------------- newest coordinator only


def test_newest_coordinator_check_has_both_arms(jobs_dir: Path) -> None:
    newest = {handoff_inbox.SESSION_ENV: NEWEST_ID}
    assert handoff_inbox.require_newest_coordinator(newest, jobs_dir) == NEWEST
    for caller in (OLDER_ID, LANE_ID, "", "dddddddd-not-a-job"):
        with pytest.raises(handoff_inbox.InboxError, match="refused"):
            handoff_inbox.require_newest_coordinator(
                {handoff_inbox.SESSION_ENV: caller}, jobs_dir
            )


def _plan(main_repo: Path, tmp_path: Path) -> tuple[Path, Path]:
    plan = main_repo / "task_plan.md"
    plan.write_text("# Plan\n\n- row A: OPEN\n- row B: OPEN\n")
    edits = tmp_path / "edits.json"
    edits.write_text(
        json.dumps(
            [
                {"replace": "- row A: OPEN", "with": "- row A: DONE"},
                {"append": "- row C: NEW"},
            ]
        )
    )
    return plan, edits


def test_plan_apply_by_the_newest_coordinator_edits_and_backs_up(
    repos: tuple[Path, Path],
    jobs_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_repo, _ = repos
    plan, edits = _plan(main_repo, tmp_path)
    monkeypatch.setenv(handoff_inbox.SESSION_ENV, NEWEST_ID)

    rc = _run(["plan-apply", "--edits", str(edits), "--jobs-dir", str(jobs_dir)])

    assert rc == 0
    assert plan.read_text() == (
        "# Plan\n\n- row A: DONE\n- row B: OPEN\n\n- row C: NEW\n"
    )
    backups = list((main_repo / handoff_inbox.BACKUP_SUBDIR).iterdir())
    assert [b.read_text() for b in backups] == [
        "# Plan\n\n- row A: OPEN\n- row B: OPEN\n"
    ]


@pytest.mark.parametrize("caller", [OLDER_ID, LANE_ID])
def test_plan_apply_by_anyone_else_is_refused_and_writes_nothing(
    repos: tuple[Path, Path],
    jobs_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caller: str,
) -> None:
    main_repo, _ = repos
    plan, edits = _plan(main_repo, tmp_path)
    before = plan.read_text()
    monkeypatch.setenv(handoff_inbox.SESSION_ENV, caller)

    rc = _run(["plan-apply", "--edits", str(edits), "--jobs-dir", str(jobs_dir)])

    assert rc == 2
    assert plan.read_text() == before


@pytest.mark.parametrize("anchor", ["- row Z: ABSENT", "- row "])
def test_a_bad_anchor_refuses_the_whole_edit_list(
    repos: tuple[Path, Path],
    jobs_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    anchor: str,
) -> None:
    """0 or 2 matches: nothing is written, not even the valid first edit."""
    main_repo, _ = repos
    plan, edits = _plan(main_repo, tmp_path)
    before = plan.read_text()
    edits.write_text(
        json.dumps(
            [
                {"replace": "- row A: OPEN", "with": "- row A: DONE"},
                {"replace": anchor, "with": "x"},
            ]
        )
    )
    monkeypatch.setenv(handoff_inbox.SESSION_ENV, NEWEST_ID)

    rc = _run(["plan-apply", "--edits", str(edits), "--jobs-dir", str(jobs_dir)])

    assert rc == 2
    assert plan.read_text() == before


def test_queue_append_and_inbox_edit_are_coordinator_only(
    repos: tuple[Path, Path],
    jobs_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_repo, _ = repos
    queue = main_repo / ".agent" / "plans" / "main-checkout-ship-queue.md"
    _run(["append", "--lane", "brief", "--message", "line 7: STALE"])
    inbox = main_repo / ".agent" / "plans" / "handoff-inbox" / "brief.md"
    edits = tmp_path / "e.json"
    edits.write_text(json.dumps([{"replace": "line 7: STALE", "with": "line 7: OK"}]))
    jobs = ["--jobs-dir", str(jobs_dir)]

    monkeypatch.setenv(handoff_inbox.SESSION_ENV, LANE_ID)
    assert _run(["queue-append", "--message", "slot 4: L0", *jobs]) == 2
    assert _run(["inbox-edit", "--lane", "brief", "--edits", str(edits), *jobs]) == 2
    assert not queue.exists()
    assert "STALE" in inbox.read_text()

    monkeypatch.setenv(handoff_inbox.SESSION_ENV, NEWEST_ID)
    assert _run(["queue-append", "--message", "slot 4: L0", *jobs]) == 0
    assert _run(["inbox-edit", "--lane", "brief", "--edits", str(edits), *jobs]) == 0
    assert f"— {NEWEST}\n\nslot 4: L0\n" in queue.read_text()
    assert "line 7: OK" in inbox.read_text()


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"replace": "a", "with": "b"},
        [{"replace": "", "with": "b"}],
        [{"replace": "a"}],
        [{"append": "   "}],
        [{"replace": "a", "with": "b", "extra": 1}],
    ],
)
def test_malformed_edit_lists_are_refused(payload: object) -> None:
    with pytest.raises(handoff_inbox.InboxError):
        handoff_inbox.parse_edits(payload)
