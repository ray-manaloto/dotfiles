# Copyright (c) 2026 Raymond Manaloto
"""Typed receipts and source-attributed agent DAGs for SDLC lanes."""

from __future__ import annotations

import argparse
import enum
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Final, cast
from urllib.parse import quote

from dotfiles_setup import codec

__all__ = [
    "AGENTSVIEW_PATH",
    "LANE_RESULTS_DIR",
    "AgentNode",
    "AgentSource",
    "CollectorOutcome",
    "LaneResult",
    "collect_hook_events",
    "collect_observed",
    "collect_self_report",
    "generate_schema",
    "hook_events_path",
    "lane_receipt_main",
    "merge_sources",
    "read_result",
    "receipt_path",
    "render_mermaid",
    "render_receipt",
    "result_path",
]


class AgentSource(enum.StrEnum):
    """Independent evidence sources for agent participation."""

    SELF_REPORT = "self_report"
    OBSERVED = "observed"
    HOOK = "hook"


class AgentNode(codec.Struct, frozen=True):
    """One participating agent and the evidence that observed it."""

    name: str
    role: str = ""
    parent: str | None = None
    sources: tuple[AgentSource, ...] = ()
    status: str = ""


class LaneResult(codec.Struct, frozen=True):
    """One lane invocation and its source-attributed agent graph."""

    run_id: str
    lane: str
    agents: tuple[AgentNode, ...] = ()
    disagreements: tuple[str, ...] = ()
    started_at: str = ""
    duration_s: float = 0.0


class CollectorOutcome(codec.Struct, frozen=True):
    """The available/unavailable result of one participation collector."""

    source: AgentSource
    agents: tuple[AgentNode, ...] = ()
    available: bool = True
    error: str = ""


LANE_RESULTS_DIR: Final = ".agent/lane-results"
AGENTSVIEW_PATH: Final = Path(
    "/Users/rmanaloto/.local/share/mise/installs/"
    "github-kenn-io-agentsview/0.42.0/agentsview"
)
_AGENTSVIEW_TIMEOUT_S: Final = 30.0
_MIN_CONFLICTING_VALUES: Final = 2

_SECTION_LINE = re.compile(
    r"(?:\bselected\s*:|\bspecialists?\s+(?:spawned|invoked)\s*:|"
    r"\bagent types actually spawned\s*:)",
    re.IGNORECASE,
)
_AGENT_LINE = re.compile(
    r"^\s*(?:[-*+]|\d+[.)])\s+"
    r"(?:`(?P<code>[^`]+)`|\*\*(?P<bold>[^*]+)\*\*|"
    r"(?P<plain>[A-Za-z0-9][A-Za-z0-9_.-]*))"
    r"(?:\s+(?:—|-|:)\s*(?P<role>.+))?\s*$"
)


def _safe_run_id(run_id: str) -> str:
    """Encode a run identifier so it cannot escape the results directory."""
    return quote(run_id, safe="-_.")


def result_path(repo_root: Path, run_id: str) -> Path:
    """Return the typed JSON path for ``run_id``."""
    return repo_root / LANE_RESULTS_DIR / f"{_safe_run_id(run_id)}.json"


def receipt_path(repo_root: Path, run_id: str) -> Path:
    """Return the rendered Markdown path for ``run_id``."""
    return repo_root / LANE_RESULTS_DIR / f"{_safe_run_id(run_id)}.md"


def hook_events_path(repo_root: Path, run_id: str) -> Path:
    """Return the normalized future hook-event log path for ``run_id``."""
    return repo_root / LANE_RESULTS_DIR / f"{_safe_run_id(run_id)}.hooks.jsonl"


def _unavailable(source: AgentSource, error: str) -> CollectorOutcome:
    """Build one explicit unavailable outcome with a useful reason."""
    return CollectorOutcome(source=source, available=False, error=error)


def collect_self_report(report_text: str) -> CollectorOutcome:
    """Parse the first selected/spawned agent list in a dispatcher report.

    The accepted form is a Markdown list below a line containing ``selected:``
    or ``specialist(s) spawned:``. A list item starts with the agent name,
    preferably in backticks, followed by an optional dash and role.
    """
    if not isinstance(report_text, str):
        return _unavailable(AgentSource.SELF_REPORT, "self-report is not text")
    if not report_text.strip():
        return CollectorOutcome(source=AgentSource.SELF_REPORT)

    lines = report_text.splitlines()
    section_index = next(
        (index for index, line in enumerate(lines) if _SECTION_LINE.search(line)),
        None,
    )
    if section_index is None:
        return _unavailable(
            AgentSource.SELF_REPORT,
            "self-report has no selected or spawned agent section",
        )

    agents: list[AgentNode] = []
    for line in lines[section_index + 1 :]:
        if not line.strip():
            continue
        match = _AGENT_LINE.match(line)
        if match is None:
            if agents:
                break
            continue
        name = match.group("code") or match.group("bold") or match.group("plain")
        role = (match.group("role") or "").strip()
        agents.append(
            AgentNode(
                name=name.strip(),
                role=role,
                sources=(AgentSource.SELF_REPORT,),
            )
        )

    if not agents:
        return _unavailable(
            AgentSource.SELF_REPORT,
            "self-report agent section contains no parseable list items",
        )
    return CollectorOutcome(source=AgentSource.SELF_REPORT, agents=tuple(agents))


def _session_rows(output: str) -> list[dict[str, object]]:
    """Decode the list shape emitted by ``agentsview session list --json``."""
    payload = json.loads(output)
    rows: object
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("sessions")
    else:
        msg = "agentsview JSON is neither an object nor an array"
        raise TypeError(msg)
    if rows is None:
        return []
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        msg = "agentsview JSON has no session row array"
        raise ValueError(msg)
    return cast("list[dict[str, object]]", rows)


def _text_field(row: dict[str, object], *names: str) -> str:
    """Return the first non-empty string field named in ``row``."""
    for name in names:
        value = row.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _observed_agents(
    rows: list[dict[str, object]], parent_session_id: str
) -> tuple[AgentNode, ...]:
    """Extract every descendant of ``parent_session_id`` from session rows."""
    rows_by_id: dict[str, dict[str, object]] = {}
    for row in rows:
        session_id = _text_field(row, "id", "session_id")
        if not session_id:
            msg = "agentsview session row is missing id"
            raise ValueError(msg)
        rows_by_id[session_id] = row

    descendant_ids: set[str] = set()
    parent_ids = {parent_session_id}
    while parent_ids:
        children = {
            session_id
            for session_id, row in rows_by_id.items()
            if session_id not in descendant_ids
            and _text_field(row, "parent_session_id") in parent_ids
        }
        descendant_ids.update(children)
        parent_ids = children

    agents: list[AgentNode] = []
    for session_id in sorted(descendant_ids):
        row = rows_by_id[session_id]
        name = _text_field(row, "agent_label", "display_name", "agent")
        if not name:
            msg = f"agentsview session {session_id!r} has no agent identity"
            raise ValueError(msg)
        parent_id = _text_field(row, "parent_session_id")
        parent_row = rows_by_id.get(parent_id)
        parent = None
        if parent_id != parent_session_id and parent_row is not None:
            parent = _text_field(parent_row, "agent_label", "display_name", "agent")
        agents.append(
            AgentNode(
                name=name,
                parent=parent or None,
                sources=(AgentSource.OBSERVED,),
                status=_text_field(row, "termination_status", "outcome"),
            )
        )
    return tuple(agents)


def collect_observed(parent_session_id: str, *, since: str = "2h") -> CollectorOutcome:
    """Collect descendant sessions from the pinned absolute agentsview binary."""
    if not parent_session_id:
        return _unavailable(AgentSource.OBSERVED, "parent session id was not provided")
    if not AGENTSVIEW_PATH.is_file():
        return _unavailable(
            AgentSource.OBSERVED,
            f"agentsview binary not found: {AGENTSVIEW_PATH}",
        )

    command = (
        str(AGENTSVIEW_PATH),
        "session",
        "list",
        "--since",
        since,
        "--include-children",
        "--include-automated",
        "--include-one-shot",
        "--limit",
        "500",
        "--json",
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=_AGENTSVIEW_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        detail = str(error)
        if isinstance(error, subprocess.TimeoutExpired):
            detail = f"timed out after {_AGENTSVIEW_TIMEOUT_S:g}s"
        return _unavailable(AgentSource.OBSERVED, f"agentsview failed: {detail}")

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        if not detail:
            detail = f"exit code {completed.returncode}"
        return _unavailable(AgentSource.OBSERVED, f"agentsview failed: {detail}")
    try:
        rows = _session_rows(completed.stdout)
        agents = _observed_agents(rows, parent_session_id)
    except (TypeError, ValueError) as error:
        return _unavailable(
            AgentSource.OBSERVED, f"agentsview output is unparsable: {error}"
        )
    return CollectorOutcome(source=AgentSource.OBSERVED, agents=agents)


def _hook_payload(line: str, line_number: int) -> dict[str, object]:
    """Decode and validate one normalized hook event line."""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as error:
        msg = f"hook log line {line_number} is invalid JSON: {error.msg}"
        raise ValueError(msg) from error
    if not isinstance(payload, dict):
        msg = f"hook log line {line_number} is not an object"
        raise TypeError(msg)
    return cast("dict[str, object]", payload)


def _hook_node(
    payload: dict[str, object],
    line_number: int,
    previous: AgentNode | None,
) -> AgentNode | None:
    """Convert one recognized hook payload into an accumulated agent node."""
    event = _text_field(payload, "event", "hook_event_name")
    if event not in {"SubagentStart", "SubagentStop"}:
        return None
    name = _text_field(payload, "name", "agent_name", "agent_type")
    if not name:
        msg = f"hook log line {line_number} has no agent name"
        raise ValueError(msg)
    role = _text_field(payload, "role") or (previous.role if previous else "")
    parent = _text_field(payload, "parent") or (
        previous.parent if previous and previous.parent else ""
    )
    status = _text_field(payload, "status")
    if not status and event == "SubagentStop":
        status = "stopped"
    if not status and previous is not None:
        status = previous.status
    return AgentNode(
        name=name,
        role=role,
        parent=parent or None,
        sources=(AgentSource.HOOK,),
        status=status,
    )


def _hook_agents(lines: list[str]) -> tuple[AgentNode, ...]:
    """Accumulate normalized start/stop lines into one node per agent name."""
    agents: dict[str, AgentNode] = {}
    recognized = 0
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        payload = _hook_payload(line, line_number)
        name = _text_field(payload, "name", "agent_name", "agent_type")
        node = _hook_node(payload, line_number, agents.get(name))
        if node is None:
            continue
        recognized += 1
        agents[node.name] = node

    if lines and recognized == 0:
        msg = "hook log contains no SubagentStart/Stop events"
        raise ValueError(msg)
    return tuple(agents[name] for name in sorted(agents))


def collect_hook_events(repo_root: Path, run_id: str) -> CollectorOutcome:
    """Collect normalized SubagentStart/Stop JSONL events for one run.

    No hook is wired yet. The agreed future format is one JSON object per line
    with ``event``, ``name``, and optional ``role``, ``parent``, and ``status``
    fields. Missing logs therefore degrade to an unavailable outcome today.
    """
    path = hook_events_path(repo_root, run_id)
    if not path.is_file():
        return _unavailable(AgentSource.HOOK, f"hook log not found: {path}")
    try:
        lines = path.read_text().splitlines()
    except OSError as error:
        return _unavailable(AgentSource.HOOK, f"hook log could not be read: {error}")
    try:
        agents = _hook_agents(lines)
    except (TypeError, ValueError) as error:
        return _unavailable(AgentSource.HOOK, str(error))
    return CollectorOutcome(
        source=AgentSource.HOOK,
        agents=agents,
    )


def _source_sort(source: AgentSource) -> int:
    """Return declaration order for stable receipt output."""
    return tuple(AgentSource).index(source)


def _chosen_field(nodes: dict[AgentSource, AgentNode], field: str) -> str | None:
    """Choose the first known field value in stable source order."""
    for source in sorted(nodes, key=_source_sort):
        value = getattr(nodes[source], field)
        if value not in {"", None}:
            return cast("str", value)
    return None


def _field_disagreement(
    name: str,
    nodes: dict[AgentSource, AgentNode],
    field: str,
) -> str | None:
    """Describe conflicting known values for one node field."""
    values = {
        source: getattr(node, field)
        for source, node in nodes.items()
        if getattr(node, field) not in {"", None}
    }
    if len(set(values.values())) < _MIN_CONFLICTING_VALUES:
        return None
    details = ", ".join(
        f"{source.value}={values[source]!r}"
        for source in sorted(values, key=_source_sort)
    )
    return f"agent {name!r} has conflicting {field}: {details}"


def merge_sources(
    *outcomes: CollectorOutcome,
) -> tuple[tuple[AgentNode, ...], tuple[str, ...]]:
    """Merge identities while reporting every availability or source conflict."""
    disagreements: list[str] = []
    available: dict[AgentSource, CollectorOutcome] = {}
    for outcome in outcomes:
        if not outcome.available:
            detail = outcome.error or "collector supplied no error"
            disagreements.append(f"source {outcome.source.value} unavailable: {detail}")
            continue
        available[outcome.source] = outcome

    source_nodes: dict[AgentSource, dict[str, AgentNode]] = {
        source: {agent.name: agent for agent in outcome.agents}
        for source, outcome in available.items()
    }
    names = sorted(
        {name for nodes in source_nodes.values() for name in nodes},
    )
    merged: list[AgentNode] = []
    for name in names:
        nodes = {
            source: source_nodes[source][name]
            for source in source_nodes
            if name in source_nodes[source]
        }
        present = tuple(sorted(nodes, key=_source_sort))
        missing = tuple(
            sorted(
                (source for source in available if source not in nodes),
                key=_source_sort,
            )
        )
        if missing:
            seen_text = ", ".join(source.value for source in present)
            missing_text = ", ".join(source.value for source in missing)
            disagreements.append(
                f"agent {name!r} seen by {seen_text}; missing from {missing_text}"
            )
        for field in ("role", "parent", "status"):
            conflict = _field_disagreement(name, nodes, field)
            if conflict is not None:
                disagreements.append(conflict)
        merged.append(
            AgentNode(
                name=name,
                role=_chosen_field(nodes, "role") or "",
                parent=_chosen_field(nodes, "parent"),
                sources=present,
                status=_chosen_field(nodes, "status") or "",
            )
        )
    return tuple(merged), tuple(disagreements)


def _mermaid_text(value: str) -> str:
    """Escape untrusted text without letting it become Mermaid syntax."""
    return html.escape(value.replace("\r", "").replace("\n", " "), quote=True)


def _node_label(name: str, role: str, status: str = "") -> str:
    """Build an escaped label that always includes the node's role."""
    parts = [_mermaid_text(name), f"role: {_mermaid_text(role or 'unknown')}"]
    if status:
        parts.append(f"status: {_mermaid_text(status)}")
    return "<br/>".join(parts)


def render_mermaid(result: LaneResult) -> str:
    """Render a syntax-safe Mermaid DAG, including the zero-agent case."""
    lines = [
        "graph TD",
        f'    lane_root["{_node_label(result.lane, "dispatcher")}"]',
    ]
    if not result.agents:
        lines.extend(
            (
                '    no_agents["no agents recorded<br/>role: observation"]',
                "    lane_root --> no_agents",
            )
        )
        return "\n".join(lines)

    node_ids = {
        agent.name: f"agent_{index}" for index, agent in enumerate(result.agents)
    }
    for agent in result.agents:
        node_id = node_ids[agent.name]
        lines.append(
            f'    {node_id}["{_node_label(agent.name, agent.role, agent.status)}"]'
        )
    for agent in result.agents:
        parent_id = node_ids.get(agent.parent or "", "lane_root")
        lines.append(f"    {parent_id} --> {node_ids[agent.name]}")
    return "\n".join(lines)


def _markdown_text(value: str) -> str:
    """Escape table-breaking text in a receipt cell."""
    return html.escape(value.replace("\r", "").replace("\n", " ")).replace(
        "|", "&#124;"
    )


def render_receipt(result: LaneResult) -> str:
    """Render the complete Markdown receipt with its Mermaid DAG."""
    started_at = _markdown_text(result.started_at) if result.started_at else "(unknown)"
    lines = [
        f"# Lane receipt: {_markdown_text(result.run_id)}",
        "",
        f"- Lane: `{_markdown_text(result.lane)}`",
        f"- Started: {started_at}",
        f"- Duration: {result.duration_s:g}s",
        "",
        "## Agent DAG",
        "",
        "```mermaid",
        render_mermaid(result),
        "```",
        "",
        "## Participation",
        "",
        "| Agent | Role | Parent | Status | Sources |",
        "|---|---|---|---|---|",
    ]
    if result.agents:
        for agent in result.agents:
            sources = ", ".join(source.value for source in agent.sources)
            name = _markdown_text(agent.name)
            role = _markdown_text(agent.role or "unknown")
            parent = _markdown_text(agent.parent or result.lane)
            status = _markdown_text(agent.status or "unknown")
            source_text = _markdown_text(sources)
            lines.append(f"| {name} | {role} | {parent} | {status} | {source_text} |")
    else:
        lines.append("| no agents recorded | observation | - | - | - |")

    lines.extend(("", "## Disagreements", ""))
    if result.disagreements:
        lines.extend(
            f"- {_markdown_text(disagreement)}" for disagreement in result.disagreements
        )
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def _write_result(repo_root: Path, result: LaneResult) -> None:
    """Atomically publish the typed JSON receipt."""
    path = result_path(repo_root, result.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_bytes(codec.encode(result) + b"\n")
    temporary.replace(path)


def _write_markdown(repo_root: Path, result: LaneResult) -> None:
    """Atomically publish the rendered Markdown receipt."""
    path = receipt_path(repo_root, result.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".md.tmp")
    temporary.write_text(render_receipt(result))
    temporary.replace(path)


def read_result(repo_root: Path, run_id: str) -> LaneResult | None:
    """Read and validate a stored lane result, or return ``None`` if absent."""
    path = result_path(repo_root, run_id)
    if not path.is_file():
        return None
    return codec.decode(path.read_bytes(), LaneResult)


def generate_schema() -> dict[str, object]:
    """Generate JSON Schema from the canonical lane result model."""
    return codec.schema(LaneResult)


def _collect_report_file(path: Path) -> CollectorOutcome:
    """Read a dispatcher report without turning an I/O failure into an exception."""
    try:
        report_text = path.read_text()
    except OSError as error:
        return _unavailable(
            AgentSource.SELF_REPORT, f"self-report could not be read: {error}"
        )
    return collect_self_report(report_text)


def lane_receipt_main(argv: list[str] | None = None) -> int:
    """Collect all three sources and write one JSON/Markdown lane receipt pair."""
    parser = argparse.ArgumentParser(prog="dotfiles-setup lane-receipt")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--parent-session-id", required=True)
    parser.add_argument("--since", default="2h")
    parser.add_argument("--started-at", default="")
    parser.add_argument("--duration-s", type=float, default=0.0)
    args = parser.parse_args(argv)

    outcomes = (
        _collect_report_file(args.report),
        collect_observed(args.parent_session_id, since=args.since),
        collect_hook_events(args.repo_root, args.run_id),
    )
    agents, disagreements = merge_sources(*outcomes)
    result = LaneResult(
        run_id=args.run_id,
        lane=args.lane,
        agents=agents,
        disagreements=disagreements,
        started_at=args.started_at,
        duration_s=args.duration_s,
    )
    _write_result(args.repo_root, result)
    _write_markdown(args.repo_root, result)
    sys.stdout.write(codec.encode(result).decode() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(lane_receipt_main())
