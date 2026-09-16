# Copyright (c) 2026 Raymond Manaloto
"""Tests for typed, source-attributed SDLC lane receipts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import lane_result
from dotfiles_setup import main as cli_main
from dotfiles_setup.config import DotfilesConfig

_NODE = re.compile(r'^\s+([A-Za-z_][A-Za-z0-9_]*)\["[^"]+"\]$')
_EDGE = re.compile(r"^\s+([A-Za-z_][A-Za-z0-9_]*) --> ([A-Za-z_][A-Za-z0-9_]*)$")


def _parse_mermaid_subset(diagram: str) -> tuple[set[str], set[tuple[str, str]]]:
    """Parse the flowchart subset emitted by the renderer, independently."""
    lines = diagram.splitlines()
    assert lines[0] == "graph TD"
    nodes: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for line in lines[1:]:
        node = _NODE.fullmatch(line)
        if node is not None:
            nodes.add(node.group(1))
            continue
        edge = _EDGE.fullmatch(line)
        assert edge is not None
        edges.add((edge.group(1), edge.group(2)))
    assert all(source in nodes and target in nodes for source, target in edges)
    return nodes, edges


def _node(
    name: str,
    source: lane_result.AgentSource,
    *,
    role: str = "",
    parent: str | None = None,
    status: str = "",
) -> lane_result.AgentNode:
    """Build a single-source fixture node."""
    return lane_result.AgentNode(
        name=name,
        role=role,
        parent=parent,
        sources=(source,),
        status=status,
    )


def _write_rollout(
    sessions_root: Path,
    filename: str,
    payload: dict[str, object],
) -> Path:
    """Write a rollout whose first record is independently controlled metadata."""
    path = sessions_root / "2026" / "09" / "16" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": "2026-09-16T06:16:17.947Z",
        "ordinal": 0,
        "type": "session_meta",
        "payload": payload,
    }
    path.write_text(json.dumps(record) + "\n" + '{"type":"session_meta"}\n')
    return path


def test_self_report_collects_the_first_selected_block_with_roles() -> None:
    report = """The dispatcher selected:

- `sdlc-python-specialist` — owns Python modules and tests.
- `sdlc-config-specialist` — owns TOML and schemas.

It found:
- `unrelated.py` — this is a finding, not an agent.
"""

    outcome = lane_result.collect_self_report(report)

    assert outcome.available is True
    assert outcome.error == ""
    assert [(agent.name, agent.role) for agent in outcome.agents] == [
        ("sdlc-python-specialist", "owns Python modules and tests."),
        ("sdlc-config-specialist", "owns TOML and schemas."),
    ]
    assert all(
        agent.sources == (lane_result.AgentSource.SELF_REPORT,)
        for agent in outcome.agents
    )


def test_empty_self_report_is_available_but_unparsable_prose_is_not() -> None:
    empty = lane_result.collect_self_report("")
    unparsable = lane_result.collect_self_report("Two agents probably participated.")

    assert empty == lane_result.CollectorOutcome(
        source=lane_result.AgentSource.SELF_REPORT
    )
    assert unparsable.available is False
    assert unparsable.agents == ()
    assert "no selected or spawned agent section" in unparsable.error


def test_parent_thread_id_is_read_only_from_the_first_codex_banner() -> None:
    banner = """OpenAI Codex v0.154.0
--------
workdir: /repo
session id: 01a0a8da-6d39-74e3-a8fc-fe66f5505378
--------
model output
"""
    quoted_later = """OpenAI Codex v0.154.0
--------
workdir: /repo
--------
The model quoted session id: later-value here.
"""

    assert (
        lane_result.parse_parent_thread_id(banner)
        == "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    )
    assert lane_result.parse_parent_thread_id(quoted_later) is None


def test_arm_24_parent_banner_may_follow_traces_within_first_fifty_lines() -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    after_three_traces = "\n".join(
        (
            "trace: loading config",
            "trace: resolving model",
            "trace: starting exec",
            "OpenAI Codex v0.154.0",
            "--------",
            "workdir: /repo",
            f"session id: {parent_id}",
            "--------",
        )
    )
    after_fifty_lines = "\n".join(
        (
            *(f"trace {index}" for index in range(50)),
            "OpenAI Codex v0.154.0",
            "--------",
            f"session id: {parent_id}",
            "--------",
        )
    )

    assert lane_result.parse_parent_thread_id(after_three_traces) == parent_id
    assert lane_result.parse_parent_thread_id(after_fifty_lines) is None


def test_spawn_report_uses_the_last_anchor_while_self_report_keeps_first_match() -> (
    None
):
    report = """Summary prose quotes `Specialists spawned:` before the findings.

- `P1` — this is a finding, not a specialist.

Final synthesis.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/docs_review`

No other specialists were spawned.
"""

    first_match = lane_result.collect_self_report(report)
    closing_match = lane_result.collect_spawn_report(report)

    assert first_match.available is True
    assert first_match.error == ""
    assert [agent.name for agent in first_match.agents] == ["P1"]
    assert closing_match.available is True
    assert closing_match.error == ""
    assert [(agent.name, agent.role) for agent in closing_match.agents] == [
        ("sdlc-python-specialist", "`/root/python_review`"),
        ("sdlc-config-specialist", "`/root/config_review`"),
        ("sdlc-documentation-specialist", "`/root/docs_review`"),
    ]


def test_arm_28_spawn_report_terminators_end_the_list_without_becoming_claims() -> None:
    supported = (
        "No other specialists were spawned.",
        "No other specialists or subagents were spawned.",
        "No others were spawned.",
        "None others were spawned.",
        "Nothing else was spawned.",
    )

    for terminator in supported:
        empty = lane_result.collect_spawn_report(
            f"Specialists spawned:\n\n- {terminator}\n"
        )
        outcome = lane_result.collect_spawn_report(
            "Specialists spawned:\n\n"
            "- `sdlc-python-specialist`\n"
            f"- {terminator}\n"
            "- `must-not-be-parsed`\n"
        )

        assert empty.available is True
        assert empty.agents == ()
        assert outcome.available is True
        assert [(node.name, node.role) for node in outcome.agents] == [
            ("sdlc-python-specialist", "")
        ]

    unsupported = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n"
        "- `sdlc-python-specialist`\n"
        "- No further specialists were spawned.\n"
    )
    assert unsupported.available is True
    assert [(node.name, node.role) for node in unsupported.agents] == [
        ("sdlc-python-specialist", ""),
        ("No further specialists were spawned.", ""),
    ]


def test_session_file_collector_reads_first_records_and_guards_payload_shapes(
    tmp_path: Path,
) -> None:
    sessions_root = tmp_path / "sessions"
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    _write_rollout(
        sessions_root,
        "rollout-parent.jsonl",
        {"id": parent_id, "parent_thread_id": None, "source": "exec"},
    )
    _write_rollout(
        sessions_root,
        "rollout-role.jsonl",
        {
            "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
            "session_id": parent_id,
            "parent_thread_id": parent_id,
            "agent_role": "sdlc-python-specialist",
            "agent_path": "/root/python_review",
            "source": {"subagent": "not-an-object"},
        },
    )
    _write_rollout(
        sessions_root,
        "rollout-path.jsonl",
        {
            "id": "01a0a8db-fbb1-7db3-8384-978b2e8cd6a1",
            "session_id": parent_id,
            "parent_thread_id": parent_id,
            "agent_path": "/root/config_pin_review",
            "source": {"subagent": {"thread_spawn": {}}},
        },
    )
    child_without_identity = "01a0a8dc-1ee0-7e10-912c-70a417e45218"
    _write_rollout(
        sessions_root,
        "rollout-identityless.jsonl",
        {
            "id": child_without_identity,
            "session_id": parent_id,
            "parent_thread_id": parent_id,
            "source": {},
        },
    )
    bad = sessions_root / "2026" / "04" / "16" / "rollout-zero.jsonl"
    bad.parent.mkdir(parents=True)
    bad.write_text("")
    os.utime(bad, (0, 0))

    outcome = lane_result.collect_session_files(
        parent_id,
        sessions_root,
        started_at="2026-09-16T00:00:00+00:00",
    )

    assert outcome.available is True
    assert outcome.error == "skipped 1 unreadable rollout file(s)"
    assert [(node.name, node.role) for node in outcome.agents] == [
        (child_without_identity, ""),
        ("/root/config_pin_review", "/root/config_pin_review"),
        ("sdlc-python-specialist", "/root/python_review"),
    ]
    assert all(
        node.sources == (lane_result.AgentSource.OBSERVED,) for node in outcome.agents
    )


def test_session_file_collector_distinguishes_unavailable_from_available_empty(
    tmp_path: Path,
) -> None:
    missing = lane_result.collect_session_files("parent", tmp_path / "missing")
    sessions_root = tmp_path / "sessions"
    sessions_root.mkdir()
    empty = lane_result.collect_session_files("parent", sessions_root)
    no_parent = lane_result.collect_session_files("", sessions_root)

    assert missing == lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        available=False,
        error=f"sessions root is not a readable directory: {tmp_path / 'missing'}",
    )
    assert no_parent == lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        available=False,
        error="parent thread id was not provided",
    )
    assert empty == lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED
    )


def test_observed_collector_uses_absolute_binary_and_builds_descendant_dag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path / "agentsview"
    binary.write_text("")
    captured: list[tuple[str, ...]] = []
    payload = {
        "sessions": [
            {"id": "root", "agent_label": "sdlc-dispatcher"},
            {
                "id": "python",
                "agent_label": "sdlc-python-specialist",
                "parent_session_id": "root",
                "relationship_type": "subagent",
                "termination_status": "ok",
            },
            {
                "id": "review",
                "agent_label": "cold-reviewer",
                "parent_session_id": "python",
                "relationship_type": "subagent",
            },
            {
                "id": "other",
                "agent_label": "unrelated",
                "parent_session_id": "different-root",
                "relationship_type": "subagent",
            },
        ]
    }

    def fake_run(
        command: tuple[str, ...], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        captured.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    monkeypatch.setattr(lane_result, "AGENTSVIEW_PATH", binary)
    monkeypatch.setattr(lane_result.subprocess, "run", fake_run)

    outcome = lane_result.collect_observed("root", since="45m")

    assert outcome.available is True
    assert [(agent.name, agent.parent, agent.status) for agent in outcome.agents] == [
        ("sdlc-python-specialist", None, "ok"),
        ("cold-reviewer", "sdlc-python-specialist", ""),
    ]
    command = captured[0]
    assert Path(command[0]).is_absolute()
    assert command[0] == str(binary)
    assert "--include-one-shot" in command
    assert command[command.index("--since") + 1] == "45m"


def test_observed_unavailable_is_distinct_from_available_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing-agentsview"
    monkeypatch.setattr(lane_result, "AGENTSVIEW_PATH", missing)
    unavailable = lane_result.collect_observed("root")

    binary = tmp_path / "agentsview"
    binary.write_text("")
    monkeypatch.setattr(lane_result, "AGENTSVIEW_PATH", binary)
    monkeypatch.setattr(
        lane_result.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, 0, '{"sessions":[]}', ""
        ),
    )
    empty = lane_result.collect_observed("root")

    assert unavailable.available is False
    assert "binary not found" in unavailable.error
    assert empty.available is True
    assert empty.agents == ()
    assert empty.error == ""
    assert unavailable != empty


def test_hook_collector_reads_normalized_start_and_stop_events(tmp_path: Path) -> None:
    path = lane_result.hook_events_path(tmp_path, "run/1")
    path.parent.mkdir(parents=True)
    events = (
        {
            "event": "SubagentStart",
            "name": "sdlc-python-specialist",
            "role": "Python",
        },
        {
            "event": "SubagentStart",
            "name": "cold-reviewer",
            "role": "review",
            "parent": "sdlc-python-specialist",
        },
        {
            "event": "SubagentStop",
            "name": "sdlc-python-specialist",
            "status": "ok",
        },
    )
    path.write_text("".join(f"{json.dumps(event)}\n" for event in events))

    outcome = lane_result.collect_hook_events(tmp_path, "run/1")

    assert outcome.available is True
    assert [
        (agent.name, agent.role, agent.parent, agent.status) for agent in outcome.agents
    ] == [
        ("cold-reviewer", "review", "sdlc-python-specialist", ""),
        ("sdlc-python-specialist", "Python", None, "ok"),
    ]
    assert all(
        agent.sources == (lane_result.AgentSource.HOOK,) for agent in outcome.agents
    )


def test_missing_hook_log_is_unavailable_but_empty_log_saw_nothing(
    tmp_path: Path,
) -> None:
    unavailable = lane_result.collect_hook_events(tmp_path, "run")
    path = lane_result.hook_events_path(tmp_path, "run")
    path.parent.mkdir(parents=True)
    path.write_text("")
    empty = lane_result.collect_hook_events(tmp_path, "run")

    assert unavailable.available is False
    assert "hook log not found" in unavailable.error
    assert empty == lane_result.CollectorOutcome(source=lane_result.AgentSource.HOOK)


def test_merge_keeps_one_source_node_and_reports_available_disagreement() -> None:
    self_report = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.SELF_REPORT,
        agents=(
            _node(
                "sdlc-python-specialist",
                lane_result.AgentSource.SELF_REPORT,
                role="Python",
            ),
        ),
    )
    observed = lane_result.CollectorOutcome(source=lane_result.AgentSource.OBSERVED)
    hook = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.HOOK,
        agents=(_node("sdlc-python-specialist", lane_result.AgentSource.HOOK),),
    )

    agents, disagreements = lane_result.merge_sources(self_report, observed, hook)

    assert agents == (
        lane_result.AgentNode(
            name="sdlc-python-specialist",
            role="Python",
            sources=(
                lane_result.AgentSource.SELF_REPORT,
                lane_result.AgentSource.HOOK,
            ),
        ),
    )
    assert disagreements == (
        (
            "agent 'sdlc-python-specialist' seen by self_report, hook; "
            "missing from observed"
        ),
    )


def test_merge_reports_unavailable_source_differently_from_empty_source() -> None:
    agent = _node("worker", lane_result.AgentSource.SELF_REPORT)
    self_report = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.SELF_REPORT, agents=(agent,)
    )
    unavailable = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        available=False,
        error="binary absent",
    )
    empty = lane_result.CollectorOutcome(source=lane_result.AgentSource.OBSERVED)

    _, unavailable_disagreements = lane_result.merge_sources(self_report, unavailable)
    _, empty_disagreements = lane_result.merge_sources(self_report, empty)

    assert unavailable_disagreements == ("source observed unavailable: binary absent",)
    assert empty_disagreements == (
        "agent 'worker' seen by self_report; missing from observed",
    )


def test_zero_agent_mermaid_parses_as_an_explicit_two_node_graph() -> None:
    diagram = lane_result.render_mermaid(
        lane_result.LaneResult(run_id="zero", lane="sdlc-dispatcher")
    )

    nodes, edges = _parse_mermaid_subset(diagram)

    assert nodes == {"lane_root", "no_agents"}
    assert edges == {("lane_root", "no_agents")}
    assert "no agents recorded" in diagram


def test_mermaid_escapes_agent_text_and_uses_synthetic_node_ids() -> None:
    result = lane_result.LaneResult(
        run_id="unsafe",
        lane='dispatcher"] --> injected["',
        agents=(
            lane_result.AgentNode(
                name='worker"] --> injected["',
                role="owner <admin>",
                sources=(lane_result.AgentSource.HOOK,),
            ),
        ),
    )

    diagram = lane_result.render_mermaid(result)
    nodes, edges = _parse_mermaid_subset(diagram)

    assert nodes == {"lane_root", "agent_0"}
    assert edges == {("lane_root", "agent_0")}
    assert '"] --> injected["' not in diagram
    assert "&quot;" in diagram
    assert "--&gt;" in diagram


def test_top_level_cli_writes_typed_json_and_markdown_when_agentsview_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "dispatcher.md"
    report.write_text(
        "The dispatcher selected:\n\n"
        "- `sdlc-python-specialist` — owns Python and tests.\n"
    )
    monkeypatch.setattr(lane_result, "AGENTSVIEW_PATH", tmp_path / "missing")
    args = cli_main.setup_parser().parse_args(
        [
            "lane-receipt",
            "--run-id",
            "run/42",
            "--lane",
            "sdlc-dispatcher",
            "--report",
            str(report),
            "--parent-session-id",
            "session-42",
            "--started-at",
            "2026-09-14T12:00:00Z",
            "--duration-s",
            "1.25",
        ]
    )

    with pytest.raises(SystemExit) as exited:
        cli_main.run_command(args, tmp_path, config=DotfilesConfig.model_construct())

    assert exited.value.code == 0
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["run_id"] == "run/42"
    assert emitted["agents"][0]["sources"] == ["self_report"]
    assert any(
        "source observed unavailable" in item for item in emitted["disagreements"]
    )
    assert any("source hook unavailable" in item for item in emitted["disagreements"])
    stored = lane_result.read_result(tmp_path, "run/42")
    assert stored is not None
    assert stored.run_id == "run/42"
    assert stored.duration_s == 1.25
    markdown = lane_result.receipt_path(tmp_path, "run/42").read_text()
    assert "```mermaid\ngraph TD" in markdown
    assert "sdlc-python-specialist" in markdown


def test_generated_schema_and_committed_artifact_match_lane_result() -> None:
    schema = lane_result.generate_schema()
    definitions = cast("dict[str, dict[str, Any]]", schema["$defs"])
    result_schema = definitions["LaneResult"]
    agent_schema = definitions["AgentNode"]

    assert schema["$ref"] == "#/$defs/LaneResult"
    assert result_schema["required"] == ["run_id", "lane"]
    assert set(result_schema["properties"]) == {
        "run_id",
        "lane",
        "agents",
        "disagreements",
        "started_at",
        "duration_s",
    }
    assert set(agent_schema["properties"]) == {
        "name",
        "role",
        "parent",
        "sources",
        "status",
    }
    repo_root = Path(__file__).parent.parent
    committed = json.loads((repo_root / "schemas" / "lane-result.json").read_text())
    assert committed == json.loads(json.dumps(schema))


def test_mise_task_is_a_thin_lane_receipt_cli_wrapper() -> None:
    repo_root = Path(__file__).parent.parent
    mise = (repo_root / "mise.toml").read_text()

    assert "[tasks.lane-receipt]" in mise
    assert 'run = "uv run --project python dotfiles-setup lane-receipt"' in mise
