"""repotools pane-* and pr-* through its command line, in real git repositories, against Codex-shaped rollouts."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from repotools.cli import main

SESSION = "01a19f1e-28d7-7b12-bce2-4731b8693992"
OTHER = "01a19f20-baa0-7ff0-8adb-6bb7a2919e7f"
# Permission profiles as Codex 0.166.0 recorded them in a real session, resumed with and without a sandbox flag.
ROOT = {"type": "special", "value": {"kind": "root"}}
READ_ONLY = {
    "type": "managed",
    "file_system": {"type": "restricted", "entries": [{"path": ROOT, "access": "read"}]},
    "network": "restricted",
}
FULL_ACCESS = {"sandbox_policy": {"type": "danger-full-access"}, "permission_profile": {"type": "disabled"}}
MESSAGE = "feat: one\n\nWhy it changes.\n"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # A pre-commit hook exports GIT_*, which would point git at the real checkout.
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    # Beside the repository, untracked: the commit message the reviewer reads, which tests may rewrite.
    (tmp_path / "message").write_text(MESSAGE)
    monkeypatch.setenv("TEST_MESSAGE_FILE", str(tmp_path / "message"))
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


def text() -> list[str]:
    return ["--message", os.environ["TEST_MESSAGE_FILE"]]


def fingerprint(capsys: pytest.CaptureFixture[str]) -> str:
    main(["pane-fingerprint", *text()])
    return json.loads(capsys.readouterr().out)["fingerprint"]


def approve(root: Path, capsys: pytest.CaptureFixture[str], **context: object) -> list[dict[str, Any]]:
    main(["pane-pin", "--session", SESSION])
    capsys.readouterr()
    return turn(root, "t1", f"Reviewed.\nPANE-APPROVE {fingerprint(capsys)}", **context)


def refusal(capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    with pytest.raises(SystemExit) as stopped:
        main(["pane-approved", *text()])
    assert stopped.value.code == 1
    return json.loads(capsys.readouterr().err)["error"]


def test_a_fresh_approval_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    records.insert(3, {"type": "event_msg", "payload": {"type": "token_count"}})
    write_log(repo, records)
    main(["pane-approved", *text()])


def test_the_fingerprint_is_what_the_read_only_reviewer_can_compute(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert fingerprint(capsys) == reviewer_fingerprint(repo)


REVIEWER = (
    '{ git rev-parse --verify -q HEAD || echo unborn; git ls-files -s; echo; git stripspace < "$TEST_MESSAGE_FILE"; }'
    " | git hash-object --stdin"
)


def reviewer_fingerprint(root: Path) -> str:
    """The fingerprint as the docstring's reviewer command computes it, run by a real shell."""
    own = subprocess.run(REVIEWER, shell=True, capture_output=True, check=True, text=True, cwd=root)  # noqa: S602 -- the documented reviewer command is a pipeline
    return own.stdout.strip()


def test_before_the_first_commit_the_fingerprint_is_still_the_reviewers(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    fresh = repo.parent / "fresh"
    subprocess.run(["git", "init", "-q", fresh], check=True)
    monkeypatch.chdir(fresh)
    (fresh / "a.py").write_text("one\n")
    subprocess.run(["git", "add", "."], check=True)
    assert fingerprint(capsys) == reviewer_fingerprint(fresh)
    main(["pane-pin", "--session", SESSION])
    write_log(fresh, turn(fresh, "t1", f"Reviewed.\nPANE-APPROVE {fingerprint(capsys)}"))
    main(["pane-approved", *text()])


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
        {"permission_profile": {**READ_ONLY, "file_system": {"type": "unrestricted", "entries": []}}},
        {"permission_profile": {**READ_ONLY, "file_system": {"type": "restricted", "entries": []}}},
        {"permission_profile": {**READ_ONLY, "file_system": {"type": "restricted", "entries": [{"access": "write"}]}}},
        {"permission_profile": {"type": "managed"}},
        {"permission_profile": {"type": "disabled"}},
        {"permission_profile": {"type": "external", "network": "restricted"}},
        FULL_ACCESS,
    ],
)
def test_a_turn_that_could_write_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str], context: dict[str, Any]
) -> None:
    write_log(repo, approve(repo, capsys, **context))
    assert "not read-only" in refusal(capsys)


def test_a_session_resumed_read_only_after_a_full_access_turn_approves(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The last turn decides: a reviewer resumed without a sandbox flag, then read-only again, can approve."""
    main(["pane-pin", "--session", SESSION])
    capsys.readouterr()
    answer = f"Reviewed.\nPANE-APPROVE {fingerprint(capsys)}"
    write_log(repo, [*turn(repo, "t1", "Looked.", **FULL_ACCESS), *turn(repo, "t2", answer)])
    main(["pane-approved", *text()])


def test_an_approval_from_a_full_access_turn_after_a_read_only_one_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_log(repo, [*turn(repo, "t0", "Looked."), *approve(repo, capsys, **FULL_ACCESS)])
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


def test_a_pull_request_fingerprint_outside_a_repository_is_a_named_failure(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    options = pr()
    monkeypatch.chdir(repo.parent)
    assert pr_refusal_of(capsys, "pr-fingerprint", options).startswith("git failed: fatal: not a git repository")


def test_an_unknown_command_names_the_choices(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["nope"])
    assert "pane-approved" in json.loads(capsys.readouterr().err)["error"]


def aborted(turn_id: str) -> dict[str, Any]:
    return {"type": "event_msg", "payload": {"type": "turn_aborted", "turn_id": turn_id, "reason": "interrupted"}}


def test_an_interrupted_turn_leaves_the_session_usable(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    started = {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "t0"}}
    write_log(repo, [started, aborted("t0"), *records])
    main(["pane-approved", *text()])


def test_an_interrupted_turn_withdraws_an_approval(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    started = {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "t2"}}
    write_log(repo, [*approve(repo, capsys), started, aborted("t2")])
    assert "no completed last turn" in refusal(capsys)


def test_an_abort_of_no_running_turn_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, [*approve(repo, capsys), aborted("t9")])
    assert "belongs to no running turn" in refusal(capsys)


def test_a_trailing_newline_after_the_approval_is_accepted(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["pane-pin", "--session", SESSION])
    capsys.readouterr()
    write_log(repo, turn(repo, "t1", f"Reviewed.\nPANE-APPROVE {fingerprint(capsys)}\n"))
    main(["pane-approved", *text()])


def test_an_image_in_a_user_message_does_not_break_the_check(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    image = {"type": "message", "role": "user", "content": [{"type": "input_image", "image_url": "data:"}]}
    records.insert(2, {"type": "response_item", "payload": image})
    write_log(repo, records)
    main(["pane-approved", *text()])


def test_a_final_answer_with_no_text_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = approve(repo, capsys)
    records[2]["payload"]["content"] = [{"type": "output_text"}]
    write_log(repo, records)
    assert "not one output_text part" in refusal(capsys)


def test_an_unreadable_rollout_is_a_named_failure(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["pane-pin", "--session", SESSION])
    folder = repo.parent / "codex" / "sessions"
    (folder / f"rollout-2026-11-02T19-55-16-{SESSION}.jsonl").mkdir(parents=True)
    assert "rollout-" in refusal(capsys)


def reported(records: list[dict[str, Any]], shown: str) -> list[dict[str, Any]]:
    """The turn's end reports the answer as Codex shows it, its memory citations removed."""
    records[3]["payload"]["last_agent_message"] = shown
    return records


# A memory citation in the shape of a real reviewer's final answer (Codex 0.166.0 rollouts).
CITATION = (
    "<oai-mem-citation>\n<citation_entries>\nMEMORY.md:777-777|note=[historical context only]\n"
    "</citation_entries>\n<rollout_ids>\n</rollout_ids>\n</oai-mem-citation>"
)


def test_a_memory_citation_after_the_approval_is_accepted(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["pane-pin", "--session", SESSION])
    capsys.readouterr()
    shown = f"Reviewed.\nPANE-APPROVE {fingerprint(capsys)}\n\n"
    write_log(repo, reported(turn(repo, "t1", shown + CITATION), shown))
    main(["pane-approved", *text()])


def test_an_approval_inside_a_citation_is_not_one(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["pane-pin", "--session", SESSION])
    capsys.readouterr()
    hidden = CITATION.replace("</oai-mem-citation>", f"PANE-APPROVE {fingerprint(capsys)}\n</oai-mem-citation>")
    write_log(repo, reported(turn(repo, "t1", f"Reviewed.\n{hidden}"), "Reviewed.\n"))
    assert "does not end with" in refusal(capsys)


def test_a_citation_never_closed_hides_the_rest(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["pane-pin", "--session", SESSION])
    capsys.readouterr()
    answer = f"Reviewed.\n<oai-mem-citation>\nPANE-APPROVE {fingerprint(capsys)}"
    write_log(repo, reported(turn(repo, "t1", answer), "Reviewed.\n"))
    assert "does not end with" in refusal(capsys)


def test_an_end_of_turn_text_still_holding_the_citation_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["pane-pin", "--session", SESSION])
    capsys.readouterr()
    answer = f"Reviewed.\nPANE-APPROVE {fingerprint(capsys)}\n\n{CITATION}"
    write_log(repo, turn(repo, "t1", answer))
    assert "without matching settings and answer" in refusal(capsys)


def test_a_changed_message_voids_it(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys))
    Path(os.environ["TEST_MESSAGE_FILE"]).write_text("feat: one\n\nWhy it changes, and more.\n")
    assert "does not end with" in refusal(capsys)


def test_whitespace_git_strips_from_a_message_changes_nothing(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys))
    Path(os.environ["TEST_MESSAGE_FILE"]).write_text("\n" + MESSAGE.replace("one", "one  ") + "\n\n")
    main(["pane-approved", *text()])


def commit_through_hook(message: str) -> subprocess.CompletedProcess[str]:
    """A real git commit whose commit-msg hook is the installed console script; git appends the message file."""
    script = Path(sys.executable).parent / "repotools"  # what uv installed from [project.scripts]
    Path(os.environ["TEST_MESSAGE_FILE"]).write_text(message)
    hook = ["-c", "hook.pane.event=commit-msg", "-c", f"hook.pane.command={script} pane-approved --message"]
    identity = ["-c", "user.name=t", "-c", "user.email=t@e"]
    command = ["git", *hook, *identity, "commit", "-q", "-F", os.environ["TEST_MESSAGE_FILE"]]
    return subprocess.run(command, capture_output=True, check=False, text=True)


def head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, check=True, text=True).stdout


def test_a_real_commit_checks_the_message_git_hands_its_hook(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "notes.md").write_text("x\n")
    subprocess.run(["git", "add", "notes.md"], check=True)
    write_log(repo, approve(repo, capsys))
    done = commit_through_hook(MESSAGE + "\n")
    assert done.returncode == 0, done.stderr
    stored = subprocess.run(["git", "log", "-1", "--format=%B"], capture_output=True, check=True, text=True)
    assert stored.stdout == MESSAGE + "\n"


def test_a_real_commit_with_another_message_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "notes.md").write_text("x\n")
    subprocess.run(["git", "add", "notes.md"], check=True)
    write_log(repo, approve(repo, capsys))
    before = head()
    refused = commit_through_hook("feat: something else\n")
    assert refused.returncode != 0
    assert "does not end with" in refused.stderr
    assert head() == before


def body(content: str = "## Summary\n\nOne change.\n") -> str:
    path = Path(os.environ["TEST_MESSAGE_FILE"]).with_name("body.md")
    path.write_text(content)
    return str(path)


def pr(title: str = "feat: one", body_file: str | None = None) -> list[str]:
    return ["--title", title, "--body-file", body() if body_file is None else body_file]


def pr_approve(root: Path, capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    main(["pane-pin", "--session", SESSION])
    main(["pr-fingerprint", *pr()])
    shown = json.loads(capsys.readouterr().out)["fingerprint"]
    return turn(root, "t1", f"Reviewed.\nPANE-APPROVE {shown}")


def pr_refusal_of(capsys: pytest.CaptureFixture[str], command: str, options: list[str]) -> str:
    capsys.readouterr()
    with pytest.raises(SystemExit) as stopped:
        main([command, *options])
    assert stopped.value.code == 1
    return json.loads(capsys.readouterr().err)["error"]


def pr_refusal(capsys: pytest.CaptureFixture[str], options: list[str]) -> str:
    return pr_refusal_of(capsys, "pr-approved", options)


def test_an_approved_pull_request_text_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, pr_approve(repo, capsys))
    main(["pr-approved", *pr()])


def test_the_pull_request_fingerprint_is_what_the_reviewer_can_compute(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["pr-fingerprint", *pr()])
    shown = json.loads(capsys.readouterr().out)["fingerprint"]
    text = 'echo "pull request"; git rev-parse HEAD; echo "feat: one"; echo; cat ../body.md'
    script = f"{{ {text}; }} | git hash-object --stdin"
    own = subprocess.run(script, shell=True, capture_output=True, check=True, text=True, cwd=repo)  # noqa: S602 -- the documented reviewer command is a pipeline
    assert shown == own.stdout.strip()


def test_a_changed_pull_request_body_or_title_voids_it(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, pr_approve(repo, capsys))
    assert "does not end with" in pr_refusal(capsys, pr(body_file=body("## Summary\n\nTwo changes.\n")))
    assert "does not end with" in pr_refusal(capsys, pr(title="feat: two"))


def test_a_commit_approval_does_not_approve_a_pull_request(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, approve(repo, capsys))
    assert "does not end with" in pr_refusal(capsys, pr())


def test_a_new_commit_voids_a_pull_request_approval(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, pr_approve(repo, capsys))
    (repo / "b.py").write_text("two\n")
    commit()
    assert "does not end with" in pr_refusal(capsys, pr())


@pytest.mark.parametrize("title", ["feat: one\nmore", "feat: one\n", ""])
def test_a_title_that_is_not_one_line_is_refused(repo: Path, capsys: pytest.CaptureFixture[str], title: str) -> None:
    assert repo.exists()
    assert "title" in pr_refusal(capsys, pr(title=title))


def test_a_pull_request_body_is_approved_byte_for_byte(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_log(repo, pr_approve(repo, capsys))
    # Markdown renders a trailing double space as a line break; what GitHub receives is what was approved.
    assert "does not end with" in pr_refusal(capsys, pr(body_file=body("## Summary\n\nOne change.  \n")))


GH_URL = "https://github.com/owner/repo/pull/7"
GH_EXISTS = f'a pull request for branch "topic" into branch "main" already exists:\n{GH_URL}\n'
GH_STAND_IN = """import json, sys
record, exists = sys.argv[1], sys.argv[2] == "1"
args = sys.argv[3:]
# gh pr create's flags as repotools passes them; anything else is gh's usage error.
if args[:3] != ["pr", "create", "--base"] or args[4] != "--title" or args[6:] != ["--body-file", "-"]:
    sys.stderr.write("unknown flag\\nUsage:  gh pr create [flags]\\n")
    sys.exit(1)
body = sys.stdin.buffer.read().decode()
open(record, "w").write(json.dumps({"base": args[3], "title": args[5], "body": body}))
if exists:
    sys.stderr.write(EXISTS)
    sys.exit(1)
sys.stdout.write(URL + "\\n")
"""


def origin(root: Path, branch: str = "trunk") -> None:
    """A real bare origin whose default branch is branch, pushed to and recorded as origin/HEAD by set-head."""
    remote = root.parent / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", branch, remote], check=True)
    subprocess.run(["git", "remote", "add", "origin", remote], check=True)
    subprocess.run(["git", "push", "-q", "origin", f"HEAD:{branch}"], check=True)
    subprocess.run(["git", "remote", "set-head", "origin", "--auto"], check=True, capture_output=True)


def fake_gh(root: Path, monkeypatch: pytest.MonkeyPatch, *, exists: bool = False) -> Path:
    """A gh first on PATH that checks its flags, reads the body from stdin and answers as gh pr create does.

    It prints the new pull request's URL, or gh's error when the branch already has one; it opens nothing.
    """
    record = root.parent / "gh.json"
    program = root.parent / "bin" / "gh"
    program.parent.mkdir()
    code = GH_STAND_IN.replace("EXISTS", repr(GH_EXISTS)).replace("URL", repr(GH_URL))
    (root.parent / "gh.py").write_text(code)
    flag = "1" if exists else "0"
    program.write_text(
        f"#!{sys.executable}\nimport runpy, sys\nsys.argv[1:1] = [{str(record)!r}, {flag!r}]\n"
        f"runpy.run_path({str(root.parent / 'gh.py')!r}, run_name='__main__')\n"
    )
    program.chmod(0o755)
    monkeypatch.setenv("PATH", f"{program.parent}{os.pathsep}{os.environ['PATH']}")
    return record


def test_pr_create_sends_the_approved_text_to_gh(
    repo: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """capfd, not capsys: gh's own stdout passes straight through to the caller's. The base is origin's default."""
    record = fake_gh(repo, monkeypatch)
    origin(repo)
    write_log(repo, pr_approve(repo, capfd))
    capfd.readouterr()
    main(["pr-create", *pr()])
    sent = {"base": "trunk", "title": "feat: one", "body": "## Summary\n\nOne change.\n"}
    assert json.loads(record.read_text()) == sent
    assert capfd.readouterr().out == GH_URL + "\n"


def test_pr_create_without_approval_never_runs_gh(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    record = fake_gh(repo, monkeypatch)
    write_log(repo, approve(repo, capsys))
    assert "does not end with" in pr_refusal_of(capsys, "pr-create", pr())
    assert not record.exists()


def test_gh_refusing_the_pull_request_is_a_named_failure(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_gh(repo, monkeypatch, exists=True)
    origin(repo)
    write_log(repo, pr_approve(repo, capsys))
    assert pr_refusal_of(capsys, "pr-create", pr()) == f"gh failed: {GH_EXISTS}"


def test_pr_create_without_a_known_default_branch_never_runs_gh(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    record = fake_gh(repo, monkeypatch)
    write_log(repo, pr_approve(repo, capsys))
    assert "git remote set-head origin --auto" in pr_refusal_of(capsys, "pr-create", pr())
    assert not record.exists()


HK_PKL = Path(__file__).resolve().parents[3] / "hk.pkl"


def test_hk_hands_the_hook_a_path_with_spaces_and_quotes_as_one_word(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """This repository's own commit-msg step, run by the real hk, in a checkout whose path needs quoting."""
    # repo cleared GIT_* and the global config; an outer hk run's own settings must not reach the inner one either.
    for name in [name for name in os.environ if name.startswith("HK_")]:
        monkeypatch.delenv(name)
    root = repo.parent / "it's a checkout"
    root.mkdir()
    monkeypatch.chdir(root)
    subprocess.run(["git", "init", "-q"], check=True)
    (root / "a.md").write_text("one\n")
    commit()
    real = HK_PKL.read_text()
    step = real[real.index('["commit-msg"]') :]
    step = step[: step.index("\n    }\n") + len("\n    }\n")]
    script = Path(sys.executable).parent / "repotools"
    assert "mise run //repo:pane-approved " in step
    step = step.replace("mise run //repo:pane-approved ", f"{script} pane-approved --message ")
    (root / "hk.pkl").write_text(real.splitlines()[0] + "\n\nhooks {\n    " + step + "}\n")
    (root / "notes.md").write_text("x\n")
    subprocess.run(["git", "add", "-A"], check=True)
    message = root / "message"
    message.write_text(MESSAGE)
    monkeypatch.setenv("TEST_MESSAGE_FILE", str(message))
    write_log(root, approve(root, capsys))
    hook = ["-c", "hook.hk.event=commit-msg", "-c", "hook.hk.command=hk run commit-msg --from-hook"]
    identity = ["-c", "user.name=t", "-c", "user.email=t@e"]
    command = ["git", *hook, *identity, "commit", "-q", "-F", str(message)]
    message.write_text("feat: not what was approved\n")
    refused = subprocess.run(command, capture_output=True, check=False, text=True)
    assert refused.returncode != 0
    assert "does not end with" in refused.stderr
    message.write_text(MESSAGE)
    done = subprocess.run(command, capture_output=True, check=False, text=True)
    assert done.returncode == 0, done.stderr


def test_a_crlf_body_is_hashed_and_sent_as_its_bytes(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    crlf = Path(body()).with_name("crlf.md")
    crlf.write_bytes(b"## Summary\r\n\r\nOne change.\r\n")
    main(["pr-fingerprint", *pr(body_file=str(crlf))])
    shown = json.loads(capsys.readouterr().out)["fingerprint"]
    text = 'echo "pull request"; git rev-parse --verify -q HEAD || echo unborn; echo "feat: one"; echo; cat ../crlf.md'
    script = f"{{ {text}; }} | git hash-object --stdin"
    own = subprocess.run(script, shell=True, capture_output=True, check=True, cwd=repo)  # noqa: S602 -- the documented reviewer command is a pipeline
    assert shown == own.stdout.decode().strip()
    record = fake_gh(repo, monkeypatch)
    origin(repo)
    write_log(repo, turn(repo, "t1", f"Reviewed.\nPANE-APPROVE {shown}"))
    main(["pane-pin", "--session", SESSION])
    main(["pr-create", *pr(body_file=str(crlf))])
    assert json.loads(record.read_text())["body"] == "## Summary\r\n\r\nOne change.\r\n"
