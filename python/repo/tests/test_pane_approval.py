"""repotools pane-* through its command line, in real git repositories, against rollout files in Codex's shape."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from repotools.cli import main

SESSION = "01a19f1e-28d7-7b12-bce2-4731b8693992"
OTHER = "01a19f20-baa0-7ff0-8adb-6bb7a2919e7f"
READ_ONLY = {"file_system": {"type": "restricted", "entries": [{"path": "root", "access": "read"}]}}


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # A pre-commit hook exports GIT_*, which would point git at the real checkout.
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", root], check=True)
    monkeypatch.chdir(root)
    (root / "a.py").write_text("one\n")
    commit()
    return root


def commit() -> None:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "c"], check=True)


def turn(root: Path, turn_id: str, answer: str, **context: object) -> list[dict[str, Any]]:
    settings = {
        "turn_id": turn_id,
        "cwd": str(root),
        "approval_policy": "never",
        "sandbox_policy": {"type": "read-only"},
        "permission_profile": READ_ONLY,
        **context,
    }
    message = {
        "type": "message",
        "role": "assistant",
        "phase": "final_answer",
        "content": [{"type": "output_text", "text": answer}],
    }
    complete = {"type": "task_complete", "turn_id": turn_id, "last_agent_message": answer}
    return [
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": turn_id}},
        {"type": "turn_context", "payload": settings},
        {"type": "response_item", "payload": message},
        {"type": "event_msg", "payload": complete},
    ]


def write_log(root: Path, records: list[dict[str, Any]], session: str = SESSION, **meta: object) -> None:
    fields = {"id": session, "cwd": str(root), **meta}
    lines = [json.dumps(record) for record in [{"type": "session_meta", "payload": fields}, *records]]
    folder = root.parent / "codex" / "sessions" / "2026" / "11" / "02"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"rollout-2026-11-02T19-55-16-{session}.jsonl").write_text("\n".join(lines) + "\n")


def fingerprint(capsys: pytest.CaptureFixture[str]) -> str:
    main(["pane-fingerprint"])
    return json.loads(capsys.readouterr().out)["fingerprint"]


def approve(root: Path, capsys: pytest.CaptureFixture[str], **context: object) -> list[dict[str, Any]]:
    main(["pane-pin", "--session", SESSION])
    capsys.readouterr()
    return turn(root, "t1", f"Reviewed.\nPANE-APPROVE {fingerprint(capsys)}", **context)


def refusal(capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    with pytest.raises(SystemExit) as stopped:
        main(["pane-approved"])
    assert stopped.value.code == 1
    return json.loads(capsys.readouterr().err)["error"]


def test_a_fresh_approval_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    records.insert(3, {"type": "event_msg", "payload": {"type": "token_count"}})
    write_log(repo, records)
    main(["pane-approved"])


def test_the_fingerprint_is_what_the_read_only_reviewer_can_compute(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script = "{ git rev-parse HEAD; git ls-files -s; } | git hash-object --stdin"
    own = subprocess.run(script, shell=True, capture_output=True, check=True, text=True, cwd=repo)  # noqa: S602 -- the documented reviewer command is a pipeline
    assert fingerprint(capsys) == own.stdout.strip()


def test_the_fingerprint_covers_the_whole_index_from_a_subfolder(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "sub").mkdir()
    (repo / "sub" / "b.py").write_text("x\n")
    commit()
    at_root = fingerprint(capsys)
    monkeypatch.chdir(repo / "sub")
    assert fingerprint(capsys) == at_root
    (repo / "c.py").write_text("x\n")
    subprocess.run(["git", "add", ":/c.py"], check=True)
    assert fingerprint(capsys) != at_root


def test_no_pin_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert repo.exists()
    assert "no reviewer session is pinned" in refusal(capsys)


def test_a_pin_without_a_rollout_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    approve(repo, capsys)
    assert "found 0" in refusal(capsys)


def test_a_session_id_that_is_no_uuid_cannot_be_pinned(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert repo.exists()
    with pytest.raises(SystemExit):
        main(["pane-pin", "--session", "*"])
    assert "session" in json.loads(capsys.readouterr().err)["error"]


def test_staging_a_change_outside_python_voids_it(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys))
    (repo / "notes.md").write_text("x\n")
    subprocess.run(["git", "add", "notes.md"], check=True)
    assert "does not end with" in refusal(capsys)


def test_a_new_head_voids_it(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys))
    (repo / "a.py").write_text("two\n")
    commit()
    assert "does not end with" in refusal(capsys)


def test_a_later_final_answer_withdraws_it(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, [*approve(repo, capsys), *turn(repo, "t2", "Status: fine.")])
    assert "does not end with" in refusal(capsys)


def test_a_later_turn_still_running_withdraws_it(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, [*approve(repo, capsys), *turn(repo, "t2", "x")[:2]])
    assert "no completed last turn" in refusal(capsys)


def test_a_turn_that_never_completed_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, [*turn(repo, "t0", "x")[:2], *approve(repo, capsys)])
    assert "never completed" in refusal(capsys)


def test_a_pasted_user_message_does_not_count(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    pasted = records[2]["payload"]
    last = turn(repo, "t2", "Ok.")
    last[2] = {"type": "response_item", "payload": {**pasted, "role": "user"}}
    last[3]["payload"]["last_agent_message"] = pasted["content"][0]["text"]
    write_log(repo, [*records, *last])
    assert "completed without matching" in refusal(capsys)


def test_a_commentary_message_does_not_count(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    records[2]["payload"]["phase"] = "commentary"
    write_log(repo, records)
    assert "completed without matching" in refusal(capsys)


def test_a_quoted_token_is_not_an_approval(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    token = approve(repo, capsys)[2]["payload"]["content"][0]["text"].split("\n")[-1]
    write_log(repo, turn(repo, "t1", f"Do not use:\n```\n{token}\n```"))
    assert "does not end with" in refusal(capsys)


def test_an_indented_token_is_not_an_approval(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    token = approve(repo, capsys)[2]["payload"]["content"][0]["text"].split("\n")[-1]
    write_log(repo, turn(repo, "t1", f"  {token}"))
    assert "does not end with" in refusal(capsys)


def test_an_answer_in_two_parts_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    records[2]["payload"]["content"] *= 2
    write_log(repo, records)
    assert "one output_text" in refusal(capsys)


def test_an_unrelated_session_does_not_count_without_a_repin(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys), session=OTHER)
    assert "found 0" in refusal(capsys)


def test_a_rollout_holding_another_session_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    write_log(repo, [{"type": "session_meta", "payload": {"id": OTHER, "cwd": str(repo)}}, *records])
    assert "not only" in refusal(capsys)


def test_two_rollouts_for_the_pin_are_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys))
    log = next((repo.parent / "codex").rglob("*.jsonl"))
    (log.parent / f"rollout-2026-11-03T00-00-00-{SESSION}.jsonl").write_text(log.read_text())
    assert "found 2" in refusal(capsys)


def test_a_fork_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys), forked_from_id=OTHER)
    assert "is a fork" in refusal(capsys)


def test_another_checkout_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    write_log(repo, records, cwd=str(repo.parent))
    assert "did not run in" in refusal(capsys)


def test_a_turn_in_another_checkout_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys, cwd=str(repo.parent)))
    assert "did not run in" in refusal(capsys)


@pytest.mark.parametrize(
    "context",
    [
        {"approval_policy": "on-request"},
        {"sandbox_policy": {"type": "workspace-write"}},
        {"permission_profile": {"file_system": {"type": "unrestricted", "entries": []}}},
        {"permission_profile": {"file_system": {"type": "restricted", "entries": []}}},
        {"permission_profile": {"file_system": {"type": "restricted", "entries": [{"access": "write"}]}}},
    ],
)
def test_a_turn_that_could_write_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str], context: dict[str, Any]
) -> None:
    write_log(repo, approve(repo, capsys, **context))
    assert "not read-only" in refusal(capsys)


def test_a_turn_with_no_settings_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    del records[1]
    write_log(repo, records)
    assert "outside a turn" in refusal(capsys)


def test_a_final_answer_after_the_turn_ended_cannot_leave_an_approval_standing(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    records = approve(repo, capsys)
    write_log(repo, [*records, turn(repo, "t2", "CHANGES: withdrawn.")[2]])
    assert "outside a turn" in refusal(capsys)


def test_a_turn_with_conflicting_settings_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    records.insert(2, turn(repo, "t1", "x", approval_policy="on-request")[1])
    write_log(repo, records)
    assert "conflict" in refusal(capsys)


def test_settings_from_another_turn_are_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    records[1] = turn(repo, "other", "x")[1]
    write_log(repo, records)
    assert "conflict" in refusal(capsys)


def test_a_cut_off_rollout_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys))
    log = next((repo.parent / "codex").rglob("*.jsonl"))
    log.write_text(log.read_text()[:-20])
    assert refusal(capsys)


def test_an_empty_rollout_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    approve(repo, capsys)
    write_log(repo, [])
    assert "no completed last turn" in refusal(capsys)


def test_git_outside_a_repository_is_a_named_failure(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo.parent)
    assert "git failed" in refusal(capsys)


def test_an_unknown_command_names_the_choices(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["nope"])
    assert "pane-approved" in json.loads(capsys.readouterr().err)["error"]
