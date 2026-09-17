# Copyright (c) 2026 Raymond Manaloto
"""Deterministic AgentsView tool-call census for the session-handoff workflow."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import hook_guard

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

logger = logging.getLogger(__name__)
DEFAULT_LIMIT = 3
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_SKILL = Path("~/.claude/skills/agentsview-finding-history/SKILL.md")
_REMOTE = re.compile(r"(?m)^# install-remote:\s*(?P<json>\{[^\n]+\})\s*$")
_GIT_COMMIT = re.compile(r"(?:^|[;&|\n]\s*)git(?:\s+-\S+\s+\S+)*\s+commit\b")
_REPORT_PREFIX = "docs/research/kb/reports/agents/"
_BASH_REPORT_WRITE = re.compile(
    rf"(?is)(?:>{{1,2}}\s*|(?:^|[;&|]\s*)tee(?:\s+-\S+)*\s+)"
    rf"[^;&|\n]*{re.escape(_REPORT_PREFIX)}"
)


class AgentsViewError(RuntimeError):
    """The archive could not provide trustworthy structured evidence."""


@dataclass(frozen=True)
class Remote:
    """Remote daemon flags from the installed AgentsView skill."""

    server: str
    token_file: str

    def flags(self) -> tuple[str, ...]:
        """CLI flags without reading or printing the token value."""
        return ("--server", self.server, "--server-token-file", self.token_file)


@dataclass(frozen=True)
class PassRequest:
    """Session selection and installed-skill location."""

    session_ids: tuple[str, ...] = ()
    limit: int = DEFAULT_LIMIT
    skill_path: Path = DEFAULT_SKILL


@dataclass(frozen=True)
class SessionCensus:
    """The four evidence counts emitted for one session."""

    session_id: str
    tool_calls: int
    unbounded_ordinals: tuple[int, ...]
    ask_user_questions: int
    handoff_ordinal: int | None
    first_commit_ordinal: int | None
    report_writes: int
    unparsable_rows: int = 0


@dataclass(frozen=True)
class _ToolObservation:
    """One normalized contribution to the public session census."""

    ordinal: int
    unbounded: bool = False
    ask: bool = False
    handoff: bool = False
    commit: bool = False
    report_write: bool = False


def remote_from_skill(path: Path) -> Remote:
    """Read only the generated ``install-remote`` frontmatter declaration."""
    expanded = path.expanduser()
    try:
        text = expanded.read_text()
    except OSError as exc:
        message = f"AgentsView skill is unreadable: {expanded}: {exc}"
        raise AgentsViewError(message) from exc
    match = _REMOTE.search(text)
    if match is None:
        message = "AgentsView skill lacks install-remote frontmatter"
        raise AgentsViewError(message)
    try:
        value = json.loads(match.group("json"))
    except json.JSONDecodeError as exc:
        message = "AgentsView install-remote JSON is invalid"
        raise AgentsViewError(message) from exc
    if not isinstance(value, dict):
        message = "AgentsView install-remote declaration is not an object"
        raise AgentsViewError(message)
    server = value.get("server")
    token_file = value.get("token_file")
    if (
        not isinstance(server, str)
        or not server
        or not isinstance(token_file, str)
        or not token_file
    ):
        message = "AgentsView install-remote requires server and token_file"
        raise AgentsViewError(message)
    return Remote(server, token_file)


def _default_runner(
    command: Sequence[str], timeout_s: float
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_s,
    )


def _run_json(
    command: Sequence[str],
    *,
    runner: Callable[[Sequence[str], float], subprocess.CompletedProcess[str]],
) -> object:
    try:
        result = runner(command, DEFAULT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        message = f"AgentsView invocation failed: {exc}"
        raise AgentsViewError(message) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no diagnostic").strip()
        message = f"AgentsView exited {result.returncode}: {detail[:240]}"
        raise AgentsViewError(message)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        message = "AgentsView returned invalid JSON"
        raise AgentsViewError(message) from exc


def _rows(payload: object, member: str) -> list[Mapping[str, object]]:
    value = payload.get(member) if isinstance(payload, dict) else payload
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        message = f"AgentsView JSON lacks a {member!r} row list"
        raise AgentsViewError(message)
    return value


def _session_ids(payload: object, repo_root: Path) -> tuple[str, ...]:
    rows = _rows(payload, "sessions")
    project_name = repo_root.name
    selected: list[str] = []
    for row in rows:
        agent = row.get("agent")
        project = row.get("project")
        if agent != "claude" or project != project_name:
            message = (
                "session list returned a row outside its native filters: "
                f"agent={agent!r} project={project!r}"
            )
            raise AgentsViewError(message)
        session_id = str(row.get("session_id", row.get("id", "")))
        if not session_id:
            message = "session list returned a row without a session id"
            raise AgentsViewError(message)
        selected.append(session_id)
    if not selected:
        message = "session list found no Claude session for this project"
        raise AgentsViewError(message)
    return tuple(selected)


def _input(row: Mapping[str, object]) -> Mapping[str, object] | None:
    raw = row.get("input_json")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    return value


def _observation(row: Mapping[str, object]) -> _ToolObservation | None:
    """Normalize one structured tool call into orthogonal census flags."""
    ordinal = row.get("ordinal")
    if not isinstance(ordinal, int) or isinstance(ordinal, bool):
        message = "tool-call row has an invalid ordinal"
        raise AgentsViewError(message)
    name = str(row.get("tool_name", ""))
    data = _input(row)
    if data is None:
        return None
    if name == "Bash":
        command = data.get("command")
        if not isinstance(command, str):
            message = "Bash tool-call lacks a string command"
            raise AgentsViewError(message)
        masked = hook_guard.mask_shell_syntax(command)
        return _ToolObservation(
            ordinal,
            unbounded=hook_guard.is_unbounded_wait_loop(masked),
            commit=_GIT_COMMIT.search(masked) is not None,
            report_write=_BASH_REPORT_WRITE.search(masked) is not None,
        )
    if name == "AskUserQuestion":
        return _ToolObservation(ordinal, ask=True)
    if name == "Skill":
        skill = str(data.get("skill", data.get("name", "")))
        return _ToolObservation(ordinal, handoff="session-handoff" in skill)
    path = str(data.get("file_path", data.get("path", "")))
    report_write = name in {"Write", "Edit", "MultiEdit", "NotebookEdit"} and (
        _REPORT_PREFIX in path.replace("\\", "/")
    )
    return _ToolObservation(ordinal, report_write=report_write)


def census(session_id: str, payload: object) -> SessionCensus:
    """Classify one structured tool-call response using the guard's predicate."""
    rows = _rows(payload, "tool_calls")
    unbounded: list[int] = []
    asks = 0
    handoff: int | None = None
    first_commit: int | None = None
    writes = 0
    unparsable = 0
    for row in rows:
        item = _observation(row)
        if item is None:
            unparsable += 1
            continue
        if item.unbounded:
            unbounded.append(item.ordinal)
        asks += int(item.ask)
        if handoff is None and item.handoff:
            handoff = item.ordinal
        if first_commit is None and item.commit:
            first_commit = item.ordinal
        writes += int(item.report_write)
    return SessionCensus(
        session_id,
        len(rows),
        tuple(unbounded),
        asks,
        handoff,
        first_commit,
        writes,
        unparsable,
    )


def render(item: SessionCensus) -> str:
    """Render the ratified AgentsView pass block."""
    ordinals = ", ".join(str(value) for value in item.unbounded_ordinals) or "none"
    handoff = (
        f"ord {item.handoff_ordinal}"
        if item.handoff_ordinal is not None
        else "not invoked"
    )
    commit = (
        f"ord {item.first_commit_ordinal}"
        if item.first_commit_ordinal is not None
        else "not observed"
    )
    return "\n".join(
        (
            f"AGENTSVIEW PASS — {item.session_id} ({item.tool_calls} tool calls)",
            f"  unbounded waits : {len(item.unbounded_ordinals)}  (ords {ordinals})",
            f"  AskUserQuestion : {item.ask_user_questions}",
            f"  handoff Skill   : {handoff}  (vs first git commit at {commit})",
            f"  step-3c writes  : {item.report_writes} under {_REPORT_PREFIX}",
            f"  unparsable rows : {item.unparsable_rows}",
        )
    )


def _run_pass(
    repo_root: Path,
    request: PassRequest,
    *,
    runner: Callable[
        [Sequence[str], float], subprocess.CompletedProcess[str]
    ] = _default_runner,
) -> int:
    """Perform one pass after request-level validation."""
    remote = remote_from_skill(request.skill_path)
    session_ids = request.session_ids
    if not session_ids:
        listed = _run_json(
            [
                "agentsview",
                "session",
                "list",
                "--agent",
                "claude",
                "--project",
                repo_root.name,
                "--include-children",
                "--limit",
                str(request.limit),
                "--json",
                *remote.flags(),
            ],
            runner=runner,
        )
        session_ids = _session_ids(listed, repo_root)
    findings = False
    for session_id in session_ids:
        payload = _run_json(
            [
                "agentsview",
                "session",
                "tool-calls",
                session_id,
                "--json",
                *remote.flags(),
            ],
            runner=runner,
        )
        item = census(session_id, payload)
        sys.stdout.write(render(item) + "\n")
        findings = findings or bool(item.unbounded_ordinals)
    return 1 if findings else 0


def _log_unverifiable(exc: AgentsViewError) -> None:
    """Emit a bounded archive error without exception traceback context."""
    logger.error("AGENTSVIEW PASS — UNVERIFIABLE — %s", exc)


def main(
    repo_root: Path,
    request: PassRequest,
    *,
    runner: Callable[
        [Sequence[str], float], subprocess.CompletedProcess[str]
    ] = _default_runner,
) -> int:
    """Run the bounded census; archive failures are UNVERIFIABLE, never zero."""
    if request.limit < 1:
        logger.error("AGENTSVIEW PASS — UNVERIFIABLE — --limit must be positive")
        return 2
    try:
        result = _run_pass(repo_root, request, runner=runner)
    except AgentsViewError as exc:
        _log_unverifiable(exc)
        return 2
    else:
        return result
