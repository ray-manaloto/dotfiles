# Copyright (c) 2026 Raymond Manaloto
"""Tests for the sanctioned main-checkout writes (dotfiles_setup.handoff_inbox).

Every CLI arm runs from a REAL linked worktree (``git worktree add``) and
asserts the write landed in the MAIN checkout, because reaching the main
checkout from a lane is the whole point of the task (Ray ruling b).
"""

from __future__ import annotations

import fcntl
import io
import json
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import coordinator_handoff, handoff_inbox
from dotfiles_setup.main import setup_parser
from dotfiles_setup.session_common import state_lock

NEWEST = "dotfiles-20261003T144132.124570000-05.coordinator"
OLDER = "dotfiles-20261003T140808.926861000-05.coordinator"
NEWEST_ID = "aaaaaaaa-1111-2222-3333-444444444444"
OLDER_ID = "bbbbbbbb-1111-2222-3333-444444444444"
LANE_ID = "cccccccc-1111-2222-3333-444444444444"
CODEX_ID = "dddddddd-1111-2222-3333-444444444444"
CODEX_NAME = "dotfiles-20261005T120000.codex.coordinator"
CLAIM_AT = datetime(2026, 10, 5, 17, 0, 0, 123456, tzinfo=UTC)


@pytest.fixture(autouse=True)
def isolated_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Native Codex/Claude identities must never leak into isolated test callers."""
    monkeypatch.delenv(handoff_inbox.CODEX_ENV, raising=False)
    monkeypatch.delenv(handoff_inbox.SESSION_ENV, raising=False)


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


def _job(
    jobs_dir: Path,
    session_id: str,
    name: str,
    created_at: str,
    *,
    state: str | None = None,
) -> None:
    path = jobs_dir / session_id[:8] / "state.json"
    path.parent.mkdir(parents=True)
    record = {"sessionId": session_id, "name": name, "createdAt": created_at}
    if state is not None:
        record["state"] = state
    path.write_text(json.dumps(record))


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


def test_a_takeover_while_waiting_for_the_lock_refuses_the_write(
    repos: tuple[Path, Path],
    jobs_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authority is re-checked once the lock is held, not only before it.

    The newest coordinator starts ``plan-apply`` while another writer holds the
    file lock; a successor is launched before the lock frees. The write must be
    refused (codex review of 767ff5b7, P2).
    """
    main_repo, _ = repos
    plan, edits = _plan(main_repo, tmp_path)
    before = plan.read_text()
    monkeypatch.setenv(handoff_inbox.SESSION_ENV, NEWEST_ID)
    result: list[int] = []
    argv = ["plan-apply", "--edits", str(edits), "--jobs-dir", str(jobs_dir)]

    with state_lock(handoff_inbox.lock_path(main_repo, plan)):
        worker = threading.Thread(target=lambda: result.append(_run(argv)))
        worker.start()
        time.sleep(0.5)  # the worker has passed the pre-input check by now
        _job(
            jobs_dir,
            "eeeeeeee-1111-2222-3333-444444444444",
            "dotfiles-20261003T150000.000000000-05.coordinator",
            "2026-10-03T20:00:00Z",
        )
    worker.join(timeout=15)

    assert result == [2]
    assert plan.read_text() == before


@pytest.mark.parametrize("newest_state", ["done", "stopped", "working", None])
def test_an_idle_newer_coordinator_still_supersedes_an_older_one(
    tmp_path: Path, newest_state: str | None
) -> None:
    """``done`` is idle-but-live ($CC/agent-view.md), so it must still win.

    Ray ruled 2026-10-03 to revert a state filter (cold review F2) that let an
    older, ``working`` coordinator pass whenever the newer one read ``done``.
    """
    jobs = tmp_path / "jobs"
    _job(jobs, OLDER_ID, OLDER, "2026-10-03T19:08:09.393Z", state="working")
    _job(jobs, NEWEST_ID, NEWEST, "2026-10-03T19:41:32.500Z", state=newest_state)

    with pytest.raises(handoff_inbox.InboxError, match="not the newest"):
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.SESSION_ENV: OLDER_ID}, jobs
        )
    caller = {handoff_inbox.SESSION_ENV: NEWEST_ID}
    assert handoff_inbox.require_newest_coordinator(caller, jobs) == NEWEST


def test_append_reads_the_body_from_file_or_stdin(
    repos: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    main_repo, _ = repos
    body = tmp_path / "body.md"
    body.write_text("from a file\n")
    monkeypatch.setattr(sys, "stdin", io.StringIO("from stdin\n"))

    assert _run(["append", "--lane", "L9", "--file", str(body)]) == 0
    assert _run(["append", "--lane", "L9"]) == 0

    text = (main_repo / ".agent" / "plans" / "handoff-inbox" / "L9.md").read_text()
    assert text.index("from a file") < text.index("from stdin")


def test_a_non_utf8_file_is_refused_not_a_traceback(
    repos: tuple[Path, Path], tmp_path: Path
) -> None:
    """Cold review F5: rc=2 (refused), never rc=1 (which means NOT FOUND)."""
    main_repo, _ = repos
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\xff\xfe\x00\x81")

    assert _run(["append", "--lane", "L9", "--file", str(binary)]) == 2
    assert _run(["append", "--lane", "../x", "--file", str(tmp_path / "nope")]) == 2
    assert not (main_repo / ".agent" / "plans").exists()


def test_lock_and_backup_names_do_not_collide_and_backups_are_pruned(
    repos: tuple[Path, Path],
) -> None:
    """Cold review F7: an inbox lane named ``task_plan`` is not the plan."""
    main_repo, _ = repos
    plan = main_repo / "task_plan.md"
    lane = main_repo / ".agent" / "plans" / "handoff-inbox" / "task_plan.md"
    assert handoff_inbox.lock_path(main_repo, plan) != handoff_inbox.lock_path(
        main_repo, lane
    )
    for n in range(handoff_inbox.BACKUPS_KEPT + 3):
        assert _run(["append", "--lane", "task_plan", "--message", f"m{n}"]) == 0
    backups = list((main_repo / handoff_inbox.BACKUP_SUBDIR).iterdir())
    assert len(backups) == handoff_inbox.BACKUPS_KEPT
    assert all(not b.name.startswith("task_plan.md.") for b in backups)


# ------------------------------------------------------ provider-qualified CAS


def _claim(jobs: Path, claims: Path, *, name: str = CODEX_NAME) -> Path:
    return handoff_inbox.coordinator_claim(
        {handoff_inbox.CODEX_ENV: CODEX_ID},
        jobs,
        claims_dir=claims,
        takeover=(name, NEWEST),
        now=lambda: CLAIM_AT,
    )


def test_codex_takeover_and_claude_handback_use_native_identity(
    jobs_dir: Path, tmp_path: Path
) -> None:
    claims = tmp_path / "claims"
    caller = {handoff_inbox.CODEX_ENV: CODEX_ID}
    claude = {handoff_inbox.SESSION_ENV: NEWEST_ID}
    with pytest.raises(handoff_inbox.InboxError, match="refused"):
        handoff_inbox.require_newest_coordinator(caller, jobs_dir, claims_dir=claims)
    _claim(jobs_dir, claims)
    assert (
        handoff_inbox.require_newest_coordinator(caller, jobs_dir, claims_dir=claims)
        == CODEX_NAME
    )
    with pytest.raises(handoff_inbox.InboxError, match="provider=codex"):
        handoff_inbox.require_newest_coordinator(claude, jobs_dir, claims_dir=claims)
    # Omitting the optional store retains the old isolated Claude-only contract.
    assert handoff_inbox.require_newest_coordinator(claude, jobs_dir) == NEWEST
    successor = "eeeeeeee-1111-2222-3333-444444444444"
    successor_name = "dotfiles-new-claude.coordinator"
    _job(jobs_dir, successor, successor_name, "2026-10-05T17:00:01Z", state="done")
    with pytest.raises(handoff_inbox.InboxError, match="provider=claude"):
        handoff_inbox.require_newest_coordinator(caller, jobs_dir, claims_dir=claims)
    assert (
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.SESSION_ENV: successor}, jobs_dir, claims_dir=claims
        )
        == successor_name
    )
    with pytest.raises(handoff_inbox.InboxError, match="supersedes"):
        _claim(jobs_dir, claims)
    handoff_inbox.coordinator_release(caller, claims_dir=claims)
    with pytest.raises(handoff_inbox.InboxError, match="refused"):
        handoff_inbox.require_newest_coordinator(caller, jobs_dir, claims_dir=claims)


def test_release_only_retires_own_claim_and_retired_names_are_reserved(
    jobs_dir: Path, tmp_path: Path
) -> None:
    claims = tmp_path / "claims"
    path = _claim(jobs_dir, claims)
    before = path.read_bytes()
    stranger = {handoff_inbox.CODEX_ENV: "ffffffff-1111-2222-3333-444444444444"}
    with pytest.raises(handoff_inbox.InboxError, match="no coordinator claim"):
        handoff_inbox.coordinator_release(stranger, claims_dir=claims)
    assert path.read_bytes() == before
    handoff_inbox.coordinator_release(
        {handoff_inbox.CODEX_ENV: CODEX_ID}, claims_dir=claims
    )
    assert json.loads(path.read_text())["claims"][CODEX_ID]["retired"] is True
    assert (
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.SESSION_ENV: NEWEST_ID}, jobs_dir, claims_dir=claims
        )
        == NEWEST
    )
    with pytest.raises(handoff_inbox.InboxError, match="already used"):
        handoff_inbox.coordinator_claim(
            stranger,
            jobs_dir,
            claims_dir=claims,
            takeover=(CODEX_NAME, NEWEST),
            now=lambda: CLAIM_AT,
        )
    # The same owner may deliberately reclaim; it cannot transfer the reserved name.
    _claim(jobs_dir, claims)
    assert (
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.CODEX_ENV: CODEX_ID}, jobs_dir, claims_dir=claims
        )
        == CODEX_NAME
    )


@pytest.mark.parametrize(
    ("env", "name", "supersedes"),
    [
        ({}, CODEX_NAME, NEWEST),
        ({handoff_inbox.CODEX_ENV: ""}, CODEX_NAME, NEWEST),
        (
            {handoff_inbox.CODEX_ENV: CODEX_ID, handoff_inbox.SESSION_ENV: NEWEST_ID},
            CODEX_NAME,
            NEWEST,
        ),
        (
            {handoff_inbox.CODEX_ENV: CODEX_ID, handoff_inbox.SESSION_ENV: ""},
            CODEX_NAME,
            NEWEST,
        ),
        ({handoff_inbox.CODEX_ENV: CODEX_ID}, "dotfiles-lane", NEWEST),
        ({handoff_inbox.CODEX_ENV: CODEX_ID}, CODEX_NAME, "none"),
        ({handoff_inbox.CODEX_ENV: CODEX_ID}, NEWEST, NEWEST),
    ],
)
def test_claim_refusals_leave_store_untouched(
    jobs_dir: Path, tmp_path: Path, env: dict[str, str], name: str, supersedes: str
) -> None:
    claims = tmp_path / "claims"
    with pytest.raises(handoff_inbox.InboxError, match="refused"):
        handoff_inbox.coordinator_claim(
            env,
            jobs_dir,
            claims_dir=claims,
            takeover=(name, supersedes),
            now=lambda: CLAIM_AT,
        )
    assert not (claims / handoff_inbox.CLAIMS_FILE).exists()
    _claim(jobs_dir, claims)
    assert (
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.CODEX_ENV: CODEX_ID}, jobs_dir, claims_dir=claims
        )
        == CODEX_NAME
    )


@pytest.mark.parametrize(
    "clock", [CLAIM_AT.replace(tzinfo=None), datetime(2026, 10, 1, tzinfo=UTC)]
)
def test_naive_or_rollback_clock_is_refused_and_precise_aware_clock_passes(
    jobs_dir: Path, tmp_path: Path, clock: datetime
) -> None:
    claims = tmp_path / "claims"
    with pytest.raises(handoff_inbox.InboxError, match="clock"):
        handoff_inbox.coordinator_claim(
            {handoff_inbox.CODEX_ENV: CODEX_ID},
            jobs_dir,
            claims_dir=claims,
            takeover=(CODEX_NAME, NEWEST),
            now=lambda: clock,
        )
    assert not (claims / handoff_inbox.CLAIMS_FILE).exists()
    path = _claim(jobs_dir, claims)
    assert (
        json.loads(path.read_text())["claims"][CODEX_ID]["createdAt"]
        == "2026-10-05T17:00:00.123456+00:00"
    )


@pytest.mark.parametrize(
    "corrupt",
    [
        "{",
        "[]",
        '{"unsupported-store": {}}',
        '{"claims": []}',
        '{"claims": {"owner": {}}}',
        '{"claims":{"owner":{"provider":"codex","threadId":"owner","name":"dotfiles-x.coordinator","createdAt":"2026-10-05T17:00:00"}}}',
    ],
)
def test_corrupt_claims_fail_closed_for_claim_release_and_authorization(
    jobs_dir: Path, tmp_path: Path, corrupt: str
) -> None:
    claims = tmp_path / "claims"
    claims.mkdir()
    path = claims / handoff_inbox.CLAIMS_FILE
    path.write_text(corrupt)
    caller = {handoff_inbox.CODEX_ENV: CODEX_ID}
    with pytest.raises(handoff_inbox.InboxError, match="refused"):
        _claim(jobs_dir, claims)
    with pytest.raises(handoff_inbox.InboxError, match="refused"):
        handoff_inbox.coordinator_release(caller, claims_dir=claims)
    with pytest.raises(handoff_inbox.InboxError, match="refused"):
        handoff_inbox.require_newest_coordinator(caller, jobs_dir, claims_dir=claims)
    assert path.read_text() == corrupt
    # Repair is explicit fixture setup, never a silent implementation reset.
    path.unlink()
    _claim(jobs_dir, claims)
    assert (
        handoff_inbox.require_newest_coordinator(caller, jobs_dir, claims_dir=claims)
        == CODEX_NAME
    )


def test_empty_coordinator_store_requires_none_sentinel(tmp_path: Path) -> None:
    jobs, claims = tmp_path / "jobs", tmp_path / "claims"
    env = {handoff_inbox.CODEX_ENV: CODEX_ID}
    with pytest.raises(handoff_inbox.InboxError, match="supersedes"):
        handoff_inbox.coordinator_claim(
            env,
            jobs,
            claims_dir=claims,
            takeover=(CODEX_NAME, NEWEST),
            now=lambda: CLAIM_AT,
        )
    handoff_inbox.coordinator_claim(
        env,
        jobs,
        claims_dir=claims,
        takeover=(CODEX_NAME, "none"),
        now=lambda: CLAIM_AT,
    )
    assert (
        handoff_inbox.require_newest_coordinator(env, jobs, claims_dir=claims)
        == CODEX_NAME
    )


def test_equal_timestamps_choose_provider_then_full_id(
    jobs_dir: Path, tmp_path: Path
) -> None:
    claims = tmp_path / "claims"
    path = _claim(jobs_dir, claims)
    # A real tied Claude record loses to provider='codex', regardless of its name.
    _job(
        jobs_dir,
        "zzzzzzzz-1111-2222-3333-444444444444",
        "dotfiles-tied.coordinator",
        CLAIM_AT.isoformat(),
    )
    assert (
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.CODEX_ENV: CODEX_ID}, jobs_dir, claims_dir=claims
        )
        == CODEX_NAME
    )
    with pytest.raises(handoff_inbox.InboxError, match="not the newest"):
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.SESSION_ENV: "zzzzzzzz-1111-2222-3333-444444444444"},
            jobs_dir,
            claims_dir=claims,
        )
    store = json.loads(path.read_text())
    later_id = "ffffffff-1111-2222-3333-444444444444"
    store["claims"][later_id] = dict(
        store["claims"][CODEX_ID],
        threadId=later_id,
        name="dotfiles-tied-codex.coordinator",
    )
    path.write_text(json.dumps(store))
    with pytest.raises(handoff_inbox.InboxError, match="not the newest"):
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.CODEX_ENV: CODEX_ID}, jobs_dir, claims_dir=claims
        )
    assert (
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.CODEX_ENV: later_id}, jobs_dir, claims_dir=claims
        )
        == "dotfiles-tied-codex.coordinator"
    )


def test_equal_claude_timestamps_require_full_record_identity(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    _job(jobs, NEWEST_ID, NEWEST, CLAIM_AT.isoformat())
    _job(jobs, OLDER_ID, OLDER, CLAIM_AT.isoformat())
    with pytest.raises(handoff_inbox.InboxError, match="not the newest"):
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.SESSION_ENV: NEWEST_ID}, jobs
        )
    assert (
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.SESSION_ENV: OLDER_ID}, jobs
        )
        == OLDER
    )


def test_ambiguous_provider_is_refused_after_a_valid_claim(
    jobs_dir: Path, tmp_path: Path
) -> None:
    claims = tmp_path / "claims"
    _claim(jobs_dir, claims)
    with pytest.raises(handoff_inbox.InboxError, match="ambiguous provider"):
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.CODEX_ENV: CODEX_ID, handoff_inbox.SESSION_ENV: NEWEST_ID},
            jobs_dir,
            claims_dir=claims,
        )


def test_two_cas_claims_waiting_on_the_same_lock_have_one_winner(
    jobs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claims = tmp_path / "claims"
    path = claims / handoff_inbox.CLAIMS_FILE
    attempted = [threading.Event(), threading.Event()]
    original_flock = fcntl.flock

    def observed_flock(fd: int, operation: int) -> None:
        if operation & fcntl.LOCK_EX:
            for index in range(2):
                if threading.current_thread().name == f"cas-{index}":
                    attempted[index].set()
        original_flock(fd, operation)

    results: list[str] = []
    start = threading.Barrier(3)

    def claim(index: int) -> None:
        start.wait(timeout=5)
        try:
            handoff_inbox.coordinator_claim(
                {handoff_inbox.CODEX_ENV: f"cas-owner-{index}"},
                jobs_dir,
                claims_dir=claims,
                takeover=(f"dotfiles-cas-{index}.coordinator", NEWEST),
                now=lambda: CLAIM_AT,
            )
            results.append(f"won-{index}")
        except handoff_inbox.InboxError:
            results.append(f"refused-{index}")

    monkeypatch.setattr(fcntl, "flock", observed_flock)
    with state_lock(path):
        threads = [
            threading.Thread(target=claim, args=(index,), name=f"cas-{index}")
            for index in range(2)
        ]
        for worker in threads:
            worker.start()
        start.wait(timeout=5)
        assert all(event.wait(timeout=5) for event in attempted)
    for worker in threads:
        worker.join(timeout=15)
        assert not worker.is_alive()
    assert len([result for result in results if result.startswith("won-")]) == 1
    assert len([result for result in results if result.startswith("refused-")]) == 1
    winner = next(result[-1] for result in results if result.startswith("won-"))
    assert (
        handoff_inbox.require_newest_coordinator(
            {handoff_inbox.CODEX_ENV: f"cas-owner-{winner}"},
            jobs_dir,
            claims_dir=claims,
        )
        == f"dotfiles-cas-{winner}.coordinator"
    )


def test_codex_cli_claim_all_writes_and_release_use_explicit_stores(
    repos: tuple[Path, Path],
    jobs_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_repo, lane = repos
    claims = tmp_path / "claims"
    monkeypatch.setenv(handoff_inbox.CODEX_ENV, CODEX_ID)
    flags = ["--jobs-dir", str(jobs_dir), "--claims-dir", str(claims)]
    assert (
        _run(
            ["coordinator-claim", "--name", CODEX_NAME, "--supersedes", "none", *flags]
        )
        == 2
    )
    assert (
        _run(
            ["coordinator-claim", "--name", CODEX_NAME, "--supersedes", NEWEST, *flags]
        )
        == 0
    )
    plan, edits = _plan(main_repo, tmp_path)
    assert _run(["plan-apply", "--edits", str(edits), *flags]) == 0
    assert "row A: DONE" in plan.read_text()
    assert _run(["append", "--lane", "brief", "--message", "line 7: STALE"]) == 0
    edits.write_text(json.dumps([{"replace": "line 7: STALE", "with": "line 7: OK"}]))
    assert _run(["inbox-edit", "--lane", "brief", "--edits", str(edits), *flags]) == 0
    assert (
        "line 7: OK"
        in (main_repo / handoff_inbox.HANDOFF_INBOX / "brief.md").read_text()
    )
    assert _run(["queue-append", "--message", "accepted slot", *flags]) == 0
    queue = main_repo / handoff_inbox.SHIP_QUEUE
    before = queue.read_bytes()
    assert _run(["coordinator-release", *flags]) == 0
    assert _run(["queue-append", "--message", "released slot", *flags]) == 2
    assert queue.read_bytes() == before
    assert not (main_repo / handoff_inbox.COORDINATOR_CLAIMS).exists()
    assert not (lane / ".agent").exists()


def test_codex_writer_superseded_after_input_check_is_refused_under_target_lock(
    repos: tuple[Path, Path],
    jobs_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_repo, _lane = repos
    claims = tmp_path / "claims"
    _claim(jobs_dir, claims)
    monkeypatch.setenv(handoff_inbox.CODEX_ENV, CODEX_ID)
    reading = threading.Event()
    proceed = threading.Event()

    class Body(io.StringIO):
        def read(self, size: int | None = -1, /) -> str:
            reading.set()
            assert proceed.wait(timeout=5)
            return super().read(size)

    monkeypatch.setattr(sys, "stdin", Body("should never land"))
    queue = main_repo / handoff_inbox.SHIP_QUEUE
    results: list[int] = []
    with state_lock(handoff_inbox.lock_path(main_repo, queue)):
        worker = threading.Thread(
            target=lambda: results.append(
                _run(
                    [
                        "queue-append",
                        "--jobs-dir",
                        str(jobs_dir),
                        "--claims-dir",
                        str(claims),
                    ]
                )
            )
        )
        worker.start()
        assert reading.wait(timeout=5)
        _job(
            jobs_dir,
            "ffffffff-1111-2222-3333-444444444444",
            "dotfiles-handback.coordinator",
            "2099-01-01T00:00:00Z",
        )
        proceed.set()
    worker.join(timeout=15)
    assert not worker.is_alive()
    assert results == [2]
    assert not queue.exists()


@pytest.mark.parametrize(
    "record",
    [
        {"name": CODEX_NAME, "sessionId": NEWEST_ID, "createdAt": "bad-clock"},
        {
            "name": CODEX_NAME,
            "sessionId": NEWEST_ID,
            "createdAt": "2026-10-05T12:00:00",
        },
        {"name": CODEX_NAME, "createdAt": "2026-10-05T12:00:00Z"},
    ],
)
def test_unrankable_claude_job_still_reserves_its_name(
    tmp_path: Path, record: dict[str, str]
) -> None:
    jobs, claims = tmp_path / "jobs", tmp_path / "claims"
    path = jobs / NEWEST_ID[:8] / "state.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record))
    caller = {handoff_inbox.CODEX_ENV: CODEX_ID}
    with pytest.raises(handoff_inbox.InboxError, match="already used"):
        handoff_inbox.coordinator_claim(
            caller,
            jobs,
            claims_dir=claims,
            takeover=(CODEX_NAME, "none"),
            now=lambda: CLAIM_AT,
        )
    assert not (claims / handoff_inbox.CLAIMS_FILE).exists()
    handoff_inbox.coordinator_claim(
        caller,
        jobs,
        claims_dir=claims,
        takeover=("dotfiles-distinct.coordinator", "none"),
        now=lambda: CLAIM_AT,
    )
    assert (
        handoff_inbox.require_newest_coordinator(caller, jobs, claims_dir=claims)
        == "dotfiles-distinct.coordinator"
    )


def test_codex_cli_default_claim_store_lands_in_main_checkout(
    repos: tuple[Path, Path], jobs_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    main_repo, lane = repos
    monkeypatch.setenv(handoff_inbox.CODEX_ENV, CODEX_ID)
    flags = ["--jobs-dir", str(jobs_dir)]
    assert _run(["queue-append", "--message", "unclaimed", *flags]) == 2
    assert (
        _run(
            ["coordinator-claim", "--name", CODEX_NAME, "--supersedes", NEWEST, *flags]
        )
        == 0
    )
    assert (
        main_repo / handoff_inbox.COORDINATOR_CLAIMS / handoff_inbox.CLAIMS_FILE
    ).is_file()
    assert _run(["queue-append", "--message", "default store accepted", *flags]) == 0
    queue = main_repo / handoff_inbox.SHIP_QUEUE
    before = queue.read_bytes()
    assert _run(["coordinator-release", *flags]) == 0
    assert _run(["queue-append", "--message", "retired", *flags]) == 2
    assert queue.read_bytes() == before
    assert not (lane / ".agent").exists()
