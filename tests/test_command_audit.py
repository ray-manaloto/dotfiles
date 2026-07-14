"""Tests for the command-audit transcript scanner (dotfiles_setup.command_audit).

Covers transcript discovery (env-aware, never hardcoded), defensive JSONL
parsing, the one-off/denied/mise/diagnostic classifier (incl. cd-prefix
compound unwrapping), grouping, and report rendering.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import command_audit as ca

# --------------------------------------------------------- discovery / encoding


def test_transcripts_base_uses_config_dir_env() -> None:
    base = ca.transcripts_base({"CLAUDE_CONFIG_DIR": "/x/cfg"}, Path("/home/u"))
    assert base == Path("/x/cfg/projects")


def test_transcripts_base_defaults_to_home_claude() -> None:
    base = ca.transcripts_base({}, Path("/home/u"))
    assert base == Path("/home/u/.claude/projects")


def test_encode_cwd_replaces_slashes_and_dots() -> None:
    assert ca.encode_cwd(Path("/Users/x/dev/dot.files")) == "-Users-x-dev-dot-files"


def test_project_transcripts_missing_dir_is_empty(tmp_path: Path) -> None:
    assert ca.project_transcripts(tmp_path, Path("/no/such/cwd"), limit=5) == []


def test_project_transcripts_limit_and_recency(tmp_path: Path) -> None:
    cwd = Path("/repo")
    proj = tmp_path / ca.encode_cwd(cwd)
    proj.mkdir()
    for i in range(4):
        f = proj / f"s{i}.jsonl"
        f.write_text("{}\n")
    # Make s3 the newest, s0 the oldest via mtime.
    for i in range(4):
        ts = 1_000 + i * 10
        os.utime(proj / f"s{i}.jsonl", (ts, ts))
    got = ca.project_transcripts(tmp_path, cwd, limit=2)
    assert [p.name for p in got] == ["s3.jsonl", "s2.jsonl"]


# ------------------------------------------------------------ defensive parsing


def _assistant_bash(cmd: str) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "sessionId": "sess1",
            "timestamp": "2026-07-14T00:00:00Z",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}
                ]
            },
        }
    )


def test_iter_bash_commands_extracts_and_skips_defensively(tmp_path: Path) -> None:
    f = tmp_path / "t.jsonl"
    f.write_text(
        "\n".join(
            [
                "not json at all",  # malformed -> skipped
                json.dumps(
                    {"type": "user", "message": {"content": "hi"}}
                ),  # not assistant
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"content": [{"type": "text", "text": "x"}]},
                    }
                ),  # not a Bash tool_use
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "name": "Read", "input": {}}
                            ]
                        },
                    }
                ),  # non-Bash tool
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "name": "Bash", "input": {}}
                            ]
                        },
                    }
                ),  # Bash but no command
                _assistant_bash("ls -la"),  # the only real one
                "",  # blank -> skipped
            ]
        )
    )
    cmds = list(ca.iter_bash_commands([f]))
    assert [c.command for c in cmds] == ["ls -la"]
    assert cmds[0].session == "sess1"


def test_iter_bash_commands_unreadable_file_skipped(tmp_path: Path) -> None:
    assert list(ca.iter_bash_commands([tmp_path / "does-not-exist.jsonl"])) == []


# ------------------------------------------------------------- classification


@pytest.mark.parametrize(
    "command",
    [
        "mise run lint",
        "uv run --project python dotfiles-setup verify run",
        "uv run --project python pytest tests/",
        "cd /repo && mise run ship",
    ],
)
def test_is_mise_backed(command: str) -> None:
    assert ca.is_mise_backed(command)


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "cat x",
        "git status",
        "git log --oneline",
        "docker ps",
        "gh pr view 1 --json state",
        "cd /repo && cat x",
        "grep foo bar",
    ],
)
def test_diagnostic_reads(command: str) -> None:
    assert ca.is_diagnostic(command)


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "docker run --rm ubuntu",
        "gh pr merge 1",
        "chmod +x f",
        "cd /repo && git commit -m y",
        "docker exec c ls",
    ],
)
def test_not_diagnostic_mutations(command: str) -> None:
    assert not ca.is_diagnostic(command)


def test_classify_precedence() -> None:
    # denied (guard rule) wins even inside a cd compound
    assert ca.classify("cd /repo && gh pr create --fill") == "denied"
    assert ca.classify("mise run lint") == "mise"
    assert ca.classify("git status") == "diagnostic"
    assert ca.classify("git commit -m x") == "one_off"
    assert ca.classify("docker run --rm ubuntu bash -c 'x'") == "one_off"


def test_group_key_uses_operative_head_sub() -> None:
    # group_key exercises _operative: single + repeated cd-prefix, bare cd, plain.
    assert ca.group_key("cd /repo && docker exec c ls") == "docker exec"
    assert ca.group_key("cd /a && cd /b && ls -la") == "ls -la"
    assert ca.group_key("git commit -m 'x'") == "git commit"
    assert ca.group_key("cd /repo") == "cd /repo"


# -------------------------------------------------------------- audit + report


def _cmds(*commands: str) -> list[ca.BashCommand]:
    return [ca.BashCommand(c, session="s", timestamp="t") for c in commands]


def test_audit_counts_and_ranks() -> None:
    result = ca.audit(
        _cmds(
            "git commit -m a",
            "git commit -m b",  # one_off, grouped
            "docker run --rm x",  # one_off
            "ls",  # diagnostic
            "mise run lint",  # mise
            "gh pr create",  # denied
        ),
        sessions=2,
    )
    assert result.total == 6
    assert result.sessions == 2
    assert result.counts["one_off"] == 3
    assert result.counts["diagnostic"] == 1
    assert result.counts["mise"] == 1
    assert result.counts["denied"] == 1
    # "git commit" is the top one-off group with count 2
    assert result.one_off_groups[0][0] == "git commit"
    assert result.one_off_groups[0][1] == 2


def test_render_report_has_sections_and_counts() -> None:
    result = ca.audit(_cmds("git commit -m x", "gh pr create"), sessions=1)
    report = ca.render_report(result)
    assert "# Command audit" in report
    assert "One-off culprits" in report
    assert "Denied-but-ran" in report
    assert "`git commit`" in report
    assert "mise-tasks-only.md" in report


def test_render_report_no_one_offs() -> None:
    result = ca.audit(_cmds("ls", "git status"), sessions=1)
    report = ca.render_report(result)
    assert "_None — no un-wrapped one-off commands found._" in report
