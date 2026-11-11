"""The fallback reviewer: pane-pin --subagent, then pane-approved and pr-* on Claude-shaped subagent transcripts."""

# The shapes are those of real transcripts Claude Code 2.1.319 wrote: agent-<id>.jsonl, one JSON record a line, with
# agent-<id>.meta.json beside it.

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from repotools.cli import main
from repotools.pane_approval import FALLBACK_LINE
from tests import clean_git_env
from tests.test_pane_approval import GH_URL, fake_gh, origin

AGENT = "a62dcae6fa8d26e95"
MESSAGE = f"feat: one\n\nWhy it changes.\n\n{FALLBACK_LINE}\n"
BODY = f"## Summary\n\nOne change.\n\n{FALLBACK_LINE}\n"
META = {"agentType": "fallback-reviewer", "requestShape": "background", "finished": True}


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    clean_git_env(monkeypatch)
    (tmp_path / "message").write_text(MESSAGE)
    (tmp_path / "body.md").write_text(BODY)
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", root], check=True)
    monkeypatch.chdir(root)
    (root / "a.py").write_text("one\n")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "c"], check=True)
    return root.resolve()


def commit_text(root: Path) -> list[str]:
    return ["--message", str(root.parent / "message")]


def pr_text(root: Path) -> list[str]:
    return ["--title", "feat: one", "--body-file", str(root.parent / "body.md")]


def printed(capsys: pytest.CaptureFixture[str], command: str, options: list[str]) -> str:
    capsys.readouterr()
    main([command, *options])
    return json.loads(capsys.readouterr().out)["fingerprint"]


def line(kind: str, content: object, **fields: object) -> dict[str, Any]:
    role = "assistant" if kind == "assistant" else "user"
    message = {"role": role, "content": content}
    return {"type": kind, "agentId": AGENT, "isSidechain": True, "message": message, **fields}


def prompt(root: Path, shown: str) -> dict[str, Any]:
    words = (
        f"You are the fallback commit reviewer.\nWorktree: {root}\n"
        f"Review the staged diff in {root.parent}/review.diff. Fingerprint: {shown}.\n\n"
        f"Your last line must be exactly `PANE-APPROVE {shown}` if there are no findings."
    )
    return line("user", words)


def said(text: str) -> dict[str, Any]:
    return line("assistant", [{"type": "text", "text": text}])


def tool(name: str, **arguments: object) -> dict[str, Any]:
    return line("assistant", [{"type": "tool_use", "id": "toolu_1", "name": name, "input": arguments}])


def result() -> dict[str, Any]:
    return line("user", [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "diff --git a/a.py b/a.py"}])


def review(root: Path, shown: str, *, answer: str | None = None) -> list[dict[str, Any]]:
    """A review as a foreground subagent writes it: the prompt, the diff file read, then its closing text."""
    closing = f"Reviewed the staged diff.\nPANE-APPROVE {shown}" if answer is None else answer
    attachment = {"type": "attachment", "agentId": AGENT, "attachment": {"type": "hook_success"}}
    return [
        prompt(root, shown),
        attachment,
        tool("Read", file_path=str(root.parent / "review.diff")),
        result(),
        said(closing),
    ]


def write(root: Path, records: list[dict[str, Any]], **meta: object) -> Path:
    folder = root.parent / "claude" / "projects" / "-repo" / "session" / "subagents"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"agent-{AGENT}.meta.json").write_text(json.dumps({**META, **meta}))
    transcript = folder / f"agent-{AGENT}.jsonl"
    transcript.write_text("".join(json.dumps(record) + "\n" for record in records))
    return transcript


def pin(transcript: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["pane-pin", "--subagent", str(transcript)])
    capsys.readouterr()


def approved(root: Path, capsys: pytest.CaptureFixture[str], records: list[dict[str, Any]], **meta: object) -> None:
    pin(write(root, records, **meta), capsys)
    main(["pane-approved", *commit_text(root)])


def refusal(capsys: pytest.CaptureFixture[str], command: str, options: list[str]) -> str:
    capsys.readouterr()
    with pytest.raises(SystemExit) as stopped:
        main([command, *options])
    assert stopped.value.code == 1
    return json.loads(capsys.readouterr().err)["error"]


def refused(root: Path, capsys: pytest.CaptureFixture[str], records: list[dict[str, Any]], **meta: object) -> str:
    pin(write(root, records, **meta), capsys)
    return refusal(capsys, "pane-approved", commit_text(root))


def test_a_finished_read_only_review_approves_the_commit(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    approved(repo, capsys, review(repo, printed(capsys, "pane-fingerprint", commit_text(repo))))


def test_a_background_review_answers_through_its_handback(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    shown = printed(capsys, "pane-fingerprint", commit_text(repo))
    handback = tool("SubagentHandback", message=f"No findings.\nPANE-APPROVE {shown}\n")
    # Its closing text before the handback never reached the caller; the handback is the answer.
    records = [*review(repo, shown, answer="Done."), handback, result()]
    approved(repo, capsys, records)


def test_grep_and_glob_and_a_prompt_in_parts_count(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    shown = printed(capsys, "pane-fingerprint", commit_text(repo))
    records = review(repo, shown)
    words = records[0]["message"]["content"]
    records[0] = line("user", [{"type": "text", "text": words}, {"type": "image"}])
    records[2:2] = [tool("Grep", pattern="def "), result(), tool("Glob", pattern="*.py"), result()]
    approved(repo, capsys, records)


def test_the_pin_is_absolute_and_replaces_a_codex_pin(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    main(["pane-pin", "--session", SESSION])
    transcript = write(repo, review(repo, printed(capsys, "pane-fingerprint", commit_text(repo))))
    (repo / "sub").mkdir()
    monkeypatch.chdir(repo / "sub")
    # Pinned from a subfolder by a relative path; the hook later runs from the root.
    main(["pane-pin", "--subagent", os.path.relpath(transcript)])
    monkeypatch.chdir(repo)
    main(["pane-approved", *commit_text(repo)])


def test_a_missing_transcript_cannot_be_pinned(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert "agent-a1.jsonl" in refusal(capsys, "pane-pin", ["--subagent", str(repo / "agent-a1.jsonl")])


SESSION = "01a19f1e-28d7-7b12-bce2-4731b8693992"


@pytest.mark.parametrize("options", [[], ["--session", SESSION, "--subagent", "agent-x.jsonl"]])
def test_exactly_one_reviewer_is_pinned(repo: Path, capsys: pytest.CaptureFixture[str], options: list[str]) -> None:
    assert repo.exists()
    assert refusal(capsys, "pane-pin", options).startswith("pin one reviewer")


def test_a_file_that_is_no_subagent_transcript_cannot_be_pinned(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert "subagent" in refusal(capsys, "pane-pin", ["--subagent", str(repo / "a.py")])


def test_a_staged_change_voids_it(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    (repo / "b.py").write_text("x\n")
    subprocess.run(["git", "add", "b.py"], check=True)
    # The new fingerprint is not in the prompt, so the run is not a review of this text.
    assert "was not asked to review" in refused(repo, capsys, records)


def test_an_answer_that_does_not_end_with_the_approval_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    shown = printed(capsys, "pane-fingerprint", commit_text(repo))
    answer = f"PANE-APPROVE {shown}\nFindings: P2 a.py:1 breaks."
    records = review(repo, shown, answer=answer)
    assert "fallback reviewer's last answer does not end with" in refused(repo, capsys, records)


def test_a_message_without_the_fallback_line_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo.parent / "message").write_text(f"feat: one\n\nWhy it changes. {FALLBACK_LINE}\n")
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    assert FALLBACK_LINE in refused(repo, capsys, records)


@pytest.mark.parametrize("meta", [{"finished": None}, {"finished": False}])
def test_an_unfinished_run_is_refused(repo: Path, capsys: pytest.CaptureFixture[str], meta: dict[str, Any]) -> None:
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    assert "has not finished" in refused(repo, capsys, records, **meta)


@pytest.mark.parametrize("kind", ["Explore", "general-purpose"])
def test_the_agent_type_does_not_decide(repo: Path, capsys: pytest.CaptureFixture[str], kind: str) -> None:
    """Any type that called only Read, Grep and Glob passes; Explore's Bash is refused below, not its type."""
    approved(repo, capsys, review(repo, printed(capsys, "pane-fingerprint", commit_text(repo))), agentType=kind)


NOT_OWN = [{"agentId": "a0"}, {"isSidechain": False}, {"isSidechain": None}, {"message": None}]


@pytest.mark.parametrize("fields", NOT_OWN)
def test_a_turn_that_is_not_the_subagents_own_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str], fields: dict[str, Any]
) -> None:
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    records[2] = {**records[2], **fields}
    assert "not subagent" in refused(repo, capsys, records)


def test_a_fork_that_starts_from_the_parents_context_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    assert "was not asked to review" in refused(repo, capsys, [said("Earlier context."), *records])


def test_a_transcript_with_no_turns_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert "was not asked to review" in refused(repo, capsys, [])


def test_a_prompt_for_another_checkout_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = review(repo.parent / "other", printed(capsys, "pane-fingerprint", commit_text(repo)))
    assert "was not asked to review" in refused(repo, capsys, records)


NOT_THIS = ["{root}/other", "{root}/", "{root}-other", "{root}.git", "/x{root}", "{root}."]


@pytest.mark.parametrize("other", NOT_THIS)
def test_a_worktree_line_that_is_not_exactly_the_checkout_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str], other: str
) -> None:
    """The Worktree line is compared whole: a nested, longer or trailing-slash path is another checkout."""
    shown = printed(capsys, "pane-fingerprint", commit_text(repo))
    records = review(repo, shown)
    records[0] = line("user", f"Worktree: {other.format(root=repo)}\nFingerprint: {shown}")
    assert "was not asked to review" in refused(repo, capsys, records)


@pytest.mark.parametrize(
    "words",
    [
        "Review {root} at fingerprint {shown}.",
        "Review {root}/review.diff at fingerprint {shown}.",
        "Worktree: {root}\nWorktree: {root}\nFingerprint: {shown}",
        "Worktree: {root} now\nFingerprint: {shown}",
    ],
)
def test_a_prompt_without_one_whole_worktree_line_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str], words: str
) -> None:
    """The path somewhere in the text is not enough: the prompt needs one line that is only Worktree and the path."""
    shown = printed(capsys, "pane-fingerprint", commit_text(repo))
    records = review(repo, shown)
    records[0] = line("user", words.format(root=repo, shown=shown))
    assert "was not asked to review" in refused(repo, capsys, records)


@pytest.mark.parametrize("named", ["Worktree: `{root}`", "  Worktree:{root}  ", "Worktree:\t{root}"])
def test_the_worktree_line_may_quote_the_path_in_backticks(
    repo: Path, capsys: pytest.CaptureFixture[str], named: str
) -> None:
    shown = printed(capsys, "pane-fingerprint", commit_text(repo))
    records = review(repo, shown)
    records[0] = line("user", f"Review the staged diff.\n{named.format(root=repo)}\nFingerprint: {shown}")
    approved(repo, capsys, records)


WRITERS = ["Bash", "Edit", "Write", "NotebookEdit", "mcp__claude-artifacts__publish_files", "Agent", "SubagentHandback"]


@pytest.mark.parametrize("name", WRITERS)
def test_a_tool_other_than_read_grep_and_glob_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str], name: str
) -> None:
    """Bash included: Explore and Plan may run it, and a shell command can write. A handback only ends the run."""
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    records.insert(2, tool(name, command="git diff --cached > review.diff", message="x"))
    assert f"(fallback-reviewer) used tools other than Read, Grep and Glob: {name}" in refused(repo, capsys, records)


def test_a_last_step_that_calls_a_writing_tool_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    assert "Read, Grep and Glob: Bash" in refused(repo, capsys, [*records, tool("Bash", command="touch x")])


def test_a_run_that_never_answered_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    assert "never answered" in refused(repo, capsys, records[:1])


@pytest.mark.parametrize("content", [[], ""])
def test_an_empty_last_turn_voids_an_earlier_approval(
    repo: Path, capsys: pytest.CaptureFixture[str], content: str | list[Any]
) -> None:
    """The approval line sits in the turn before; the last turn says nothing, so there is no answer."""
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    assert "never answered" in refused(repo, capsys, [*records, line("assistant", content)])


@pytest.mark.parametrize(
    "last",
    [
        line("assistant", [{"type": "thinking", "thinking": "..."}]),
        tool("Read", file_path="a.py"),
        tool("SubagentHandback", message=None),
        tool("SubagentHandback"),
        line("assistant", [{"type": "tool_use", "id": "toolu_1", "name": "SubagentHandback"}]),
        line("assistant", [{"type": "text"}]),
    ],
)
def test_a_last_step_with_no_answer_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str], last: dict[str, Any]
) -> None:
    records = review(repo, printed(capsys, "pane-fingerprint", commit_text(repo)))
    assert "neither text nor a SubagentHandback" in refused(repo, capsys, [*records, last])


def test_an_assistant_turn_as_one_string_counts(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    shown = printed(capsys, "pane-fingerprint", commit_text(repo))
    approved(repo, capsys, [*review(repo, shown)[:-1], line("assistant", f"No findings.\nPANE-APPROVE {shown}")])


def test_a_cut_off_transcript_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    transcript = write(repo, review(repo, printed(capsys, "pane-fingerprint", commit_text(repo))))
    transcript.write_text(transcript.read_text() + '{"type": "assistant", "message": {"ro\n')
    pin(transcript, capsys)
    assert "Invalid JSON" in refusal(capsys, "pane-approved", commit_text(repo))


def test_a_missing_meta_file_is_a_named_failure(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    transcript = write(repo, review(repo, printed(capsys, "pane-fingerprint", commit_text(repo))))
    transcript.with_name(f"agent-{AGENT}.meta.json").unlink()
    pin(transcript, capsys)
    assert f"agent-{AGENT}.meta.json" in refusal(capsys, "pane-approved", commit_text(repo))


def test_an_approved_pull_request_text_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    approved_pr = review(repo, printed(capsys, "pr-fingerprint", pr_text(repo)))
    pin(write(repo, approved_pr), capsys)
    main(["pr-approved", *pr_text(repo)])
    # The commit gate does not take a pull request's approval.
    assert "was not asked to review" in refusal(capsys, "pane-approved", commit_text(repo))


def test_a_pull_request_body_without_the_fallback_line_is_refused(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo.parent / "body.md").write_text("## Summary\n\nOne change.\n")
    pin(write(repo, review(repo, printed(capsys, "pr-fingerprint", pr_text(repo)))), capsys)
    assert FALLBACK_LINE in refusal(capsys, "pr-approved", pr_text(repo))


def test_pr_create_sends_a_fallback_approved_text_with_crlf_lines(
    repo: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fallback line counts on a CRLF line too, and the body sent is the body checked."""
    crlf = BODY.replace("\n", "\r\n")
    (repo.parent / "body.md").write_bytes(crlf.encode())
    record = fake_gh(repo, monkeypatch)
    origin(repo)
    pin(write(repo, review(repo, printed(capfd, "pr-fingerprint", pr_text(repo)))), capfd)
    main(["pr-create", *pr_text(repo)])
    assert json.loads(record.read_text())["body"] == crlf
    assert capfd.readouterr().out == GH_URL + "\n"
