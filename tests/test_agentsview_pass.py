# Copyright (c) 2026 Raymond Manaloto
"""Tests for the named AgentsView session census."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import agentsview_pass
from dotfiles_setup.main import setup_parser


def _skill(tmp_path: Path) -> Path:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\n# install-remote: "
        '{"server":"http://127.0.0.1:8080","token_file":"/secret/path"}\n'
        "name: test\n---\n"
    )
    return skill


def _runner_for(
    payload: object,
    calls: list[tuple[tuple[str, ...], float]],
    *,
    rc: int = 0,
) -> Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]:
    def run(
        command: Sequence[str], timeout_s: float
    ) -> subprocess.CompletedProcess[str]:
        calls.append((tuple(command), timeout_s))
        return subprocess.CompletedProcess(
            command,
            rc,
            json.dumps(payload) if rc == 0 else "",
            "daemon unavailable" if rc else "",
        )

    return run


def test_census_reports_unbounded_wait_and_uses_remote_flags(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = {
        "tool_calls": [
            {
                "ordinal": 10,
                "tool_name": "Bash",
                "input_json": json.dumps(
                    {"command": "until [ -f x ]; do sleep 1; done"}
                ),
            },
            {
                "ordinal": 11,
                "tool_name": "Bash",
                "input_json": json.dumps(
                    {
                        "command": (
                            "deadline=$((SECONDS+60)); while [ $SECONDS "
                            "-lt $deadline ]; do sleep 5; done"
                        )
                    }
                ),
            },
            {"ordinal": 12, "tool_name": "AskUserQuestion", "input_json": "{}"},
            {
                "ordinal": 13,
                "tool_name": "Skill",
                "input_json": '{"skill":"session-handoff"}',
            },
            {
                "ordinal": 14,
                "tool_name": "Bash",
                "input_json": '{"command":"git commit -m x"}',
            },
            {
                "ordinal": 15,
                "tool_name": "Write",
                "input_json": (
                    '{"file_path":"/repo/docs/research/kb/reports/agents/f.md"}'
                ),
            },
        ],
        "count": 6,
    }
    calls: list[tuple[tuple[str, ...], float]] = []

    rc = agentsview_pass.main(
        tmp_path,
        agentsview_pass.PassRequest(
            session_ids=("session-1",),
            skill_path=_skill(tmp_path),
        ),
        runner=_runner_for(rows, calls),
    )

    assert rc == 1
    output = capsys.readouterr().out
    assert "unbounded waits : 1  (ords 10)" in output
    assert "handoff Skill   : ord 13  (vs first git commit at ord 14)" in output
    command, timeout_s = calls[0]
    assert command[-4:] == (
        "--server",
        "http://127.0.0.1:8080",
        "--server-token-file",
        "/secret/path",
    )
    assert timeout_s == agentsview_pass.DEFAULT_TIMEOUT_S


def test_daemon_failure_is_unverifiable_not_zero_hits(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    rc = agentsview_pass.main(
        tmp_path,
        agentsview_pass.PassRequest(
            session_ids=("session-1",),
            skill_path=_skill(tmp_path),
        ),
        runner=_runner_for({}, [], rc=1),
    )

    assert rc == 2
    assert "UNVERIFIABLE" in caplog.text
    assert "daemon unavailable" in caplog.text
    assert "Traceback" not in caplog.text


def test_session_list_uses_native_filters_and_verifies_returned_rows(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, ...]] = []
    payloads = iter(
        [
            {
                "sessions": [
                    {
                        "session_id": "selected",
                        "agent": "claude",
                        "project": tmp_path.name,
                    },
                ]
            },
            {"tool_calls": [], "count": 0},
        ]
    )

    def runner(
        command: Sequence[str], timeout_s: float
    ) -> subprocess.CompletedProcess[str]:
        del timeout_s
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, 0, json.dumps(next(payloads)), "")

    assert (
        agentsview_pass.main(
            tmp_path,
            agentsview_pass.PassRequest(skill_path=_skill(tmp_path)),
            runner=runner,
        )
        == 0
    )
    assert calls[0][3:10] == (
        "--agent",
        "claude",
        "--project",
        tmp_path.name,
        "--include-children",
        "--limit",
        str(agentsview_pass.DEFAULT_LIMIT),
    )


@pytest.mark.parametrize(
    "row",
    [
        {"session_id": "missing-agent", "project": "repo"},
        {"session_id": "missing-project", "agent": "claude"},
        {"session_id": "wrong-agent", "agent": "codex", "project": "repo"},
        {"session_id": "wrong-project", "agent": "claude", "project": "other"},
    ],
)
def test_session_list_rejects_missing_or_mismatched_native_metadata(
    tmp_path: Path,
    row: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    rc = agentsview_pass.main(
        repo,
        agentsview_pass.PassRequest(skill_path=_skill(tmp_path)),
        runner=_runner_for({"sessions": [row]}, []),
    )

    assert rc == 2
    assert "outside its native filters" in caplog.text


def test_missing_skill_is_unverifiable(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "missing-skill.md"
    rc = agentsview_pass.main(
        tmp_path,
        agentsview_pass.PassRequest(
            session_ids=("session-1",),
            skill_path=missing,
        ),
    )

    assert rc == 2
    assert "skill is unreadable" in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.parametrize("tool_name", ["Write", "Edit", "MultiEdit", "NotebookEdit"])
def test_census_counts_structured_report_writes(tool_name: str) -> None:
    item = agentsview_pass.census(
        "session",
        {
            "tool_calls": [
                {
                    "ordinal": 1,
                    "tool_name": tool_name,
                    "input_json": json.dumps(
                        {"file_path": "/repo/docs/research/kb/reports/agents/r.md"}
                    ),
                }
            ]
        },
    )

    assert item.report_writes == 1


@pytest.mark.parametrize(
    "command",
    [
        "printf x > docs/research/kb/reports/agents/r.md",
        "printf x | tee docs/research/kb/reports/agents/r.md",
        "cat <<'EOF' > docs/research/kb/reports/agents/r.md\nx\nEOF",
    ],
)
def test_census_counts_shell_report_writes(command: str) -> None:
    item = agentsview_pass.census(
        "session",
        {
            "tool_calls": [
                {
                    "ordinal": 1,
                    "tool_name": "Bash",
                    "input_json": json.dumps({"command": command}),
                }
            ]
        },
    )

    assert item.report_writes == 1


def test_unparsable_tool_inputs_are_counted_and_skipped() -> None:
    item = agentsview_pass.census(
        "session",
        {
            "tool_calls": [
                {"ordinal": 1, "tool_name": "Write", "input_json": None},
                {"ordinal": 2, "tool_name": "Edit", "input_json": "{"},
                {"ordinal": 3, "tool_name": "AskUserQuestion", "input_json": "{}"},
            ]
        },
    )

    assert item.unparsable_rows == 2
    assert item.ask_user_questions == 1
    assert "unparsable rows : 2" in agentsview_pass.render(item)


def test_git_commit_detection_uses_the_masked_shell_view() -> None:
    item = agentsview_pass.census(
        "session",
        {
            "tool_calls": [
                {
                    "ordinal": 1,
                    "tool_name": "Bash",
                    "input_json": json.dumps(
                        {"command": "printf '%s' 'x; git commit -m hidden'"}
                    ),
                },
                {
                    "ordinal": 2,
                    "tool_name": "Bash",
                    "input_json": json.dumps({"command": "git commit -m real"}),
                },
            ]
        },
    )

    assert item.first_commit_ordinal == 2


def test_unreadable_skill_is_unverifiable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    skill = _skill(tmp_path)
    original = Path.read_text

    def denied(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        if path == skill:
            message = "denied by test"
            raise PermissionError(message)
        return original(path, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "read_text", denied)
    rc = agentsview_pass.main(
        tmp_path,
        agentsview_pass.PassRequest(session_ids=("session-1",), skill_path=skill),
    )

    assert rc == 2
    assert "denied by test" in caplog.text


def test_missing_tool_call_ordinal_is_unverifiable(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    rc = agentsview_pass.main(
        tmp_path,
        agentsview_pass.PassRequest(
            session_ids=("session-1",),
            skill_path=_skill(tmp_path),
        ),
        runner=_runner_for(
            {"tool_calls": [{"tool_name": "AskUserQuestion", "input_json": "{}"}]},
            [],
        ),
    )

    assert rc == 2
    assert "invalid ordinal" in caplog.text


def test_ordinal_zero_is_rendered_as_a_value() -> None:
    rendered = agentsview_pass.render(
        agentsview_pass.SessionCensus("session-0", 1, (), 0, 0, 0, 0)
    )

    assert "handoff Skill   : ord 0" in rendered
    assert "first git commit at ord 0" in rendered


def test_public_cli_accepts_repeatable_session_and_skill(tmp_path: Path) -> None:
    parsed = setup_parser().parse_args(
        [
            "session-agentsview-pass",
            "--session",
            "one",
            "--session",
            "two",
            "--skill",
            str(tmp_path / "skill.md"),
        ]
    )
    assert parsed.session == ["one", "two"]
