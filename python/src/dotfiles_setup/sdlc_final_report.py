# Copyright (c) 2026 Raymond Manaloto
"""Select genuine native root finals without changing the lane receipt schema."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from dotfiles_setup import codec, lane_result

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

__all__ = ["render_provenance", "select_final_report"]

_HEADING = re.compile(
    r"^(?:#{1,6}\s+)?(?:\*\*)?Specialists\s+spawned\s*:?(?:\*\*)?\s*:?(?:\s+#+)?$",
    re.IGNORECASE,
)
_FENCE = re.compile(r"^ {0,3}(?P<marker>`{3,}|~{3,})")
_NATIVE_ITEM = re.compile(r"^\s*[-*+]\s+`([^`]+)`\s+—\s+`(/root/[^`]+)`\s*$")
_CITATION_ENTRY = re.compile(
    r"(?P<path>[A-Za-z0-9_.][A-Za-z0-9_./-]*):"
    r"(?P<start>[1-9][0-9]*)-(?P<end>[1-9][0-9]*)"
    r"\|note=\[(?P<note>[^<>\[\]|\r\n]+)\]"
)
_ROLLOUT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
_CITATION_TRANSFORM = "native-rendered-trailing-memory-citation"
_MIN_CITATION_LINES = 6


@dataclass(frozen=True)
class _Final:
    """One verified assistant final in the completed root turn."""

    text: str
    ordinal: int
    timestamp: str
    message_id: str = ""


@dataclass(frozen=True)
class _Rendered:
    """An untrusted rendered event retained for same-message attestation."""

    payload: Mapping[str, object]
    ordinal: int
    timestamp: str


@dataclass(frozen=True)
class _NativeTurn:
    """Bounded native records after root identity and turn checks."""

    source: Path
    turn_id: str
    finals: tuple[_Final, ...]
    terminal: _Final
    started: _Final
    thread_id: str
    rendered: tuple[_Rendered, ...] = ()


@dataclass
class _TurnState:
    """Current root turn while streaming verified native records."""

    turn_id: str
    started: _Final
    finals: list[_Final]


@dataclass(frozen=True)
class _FinalSelection:
    """Private selection data; it is never serialized as a public model."""

    report_text: str
    self_report: lane_result.CollectorOutcome
    reason: str
    source: str = ""
    turn_id: str = ""
    selected_ordinal: int | None = None
    selected_timestamp: str = ""
    latest_ordinal: int | None = None
    latest_timestamp: str = ""
    terminal_ordinal: int | None = None
    terminal_timestamp: str = ""
    started_ordinal: int | None = None
    started_timestamp: str = ""
    selected_hash: str = ""
    terminal_hash: str = ""
    latest_hash: str = ""
    error: str = ""
    transform: str = ""
    captured_hash: str = ""


def _normalized(text: str) -> str:
    """Normalize CRLF/CR and trailing whitespace, retaining interior whitespace."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).rstrip()


def _digest(text: str) -> str:
    """Hash exactly the documented normalized message representation."""
    return hashlib.sha256(_normalized(text).encode()).hexdigest()


def _blocks(text: str) -> tuple[str, ...]:
    """Find all standalone declarations outside fenced code and blockquotes."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    indexes: list[int] = []
    fence = ""
    for index, line in enumerate(lines):
        if line.lstrip().startswith(">"):
            continue
        marker = _FENCE.match(line)
        if marker is not None:
            token = marker.group("marker")
            if not fence:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = ""
            continue
        if not fence and _HEADING.fullmatch(line.strip()):
            indexes.append(index)
    ends = [*indexes[1:], len(lines)] if indexes else []
    return tuple(
        "Specialists spawned:\n" + "\n".join(_roster_lines(lines[start + 1 : end]))
        for start, end in zip(indexes, ends, strict=True)
    )


def _roster_lines(lines: list[str]) -> list[str]:
    """Bound the list before the compatibility collector can rediscover examples."""
    items: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        if not re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line):
            break
        items.append(line)
    return items


def _declarations(
    text: str, *, native: bool
) -> tuple[lane_result.CollectorOutcome, ...]:
    """Validate each declaration separately so a later block cannot mask it."""
    declarations: list[lane_result.CollectorOutcome] = []
    for block in _blocks(text):
        declaration = lane_result.collect_spawn_report(block)
        if not declaration.available:
            msg = "malformed Specialists spawned declaration"
            raise ValueError(msg)
        if native:
            items = [line for line in block.splitlines()[1:] if line.strip()]
            entries = []
            for line in items:
                if not re.match(r"^\s*[-*+]\s+", line):
                    break
                match = _NATIVE_ITEM.fullmatch(line)
                if match is None:
                    msg = (
                        "invalid native roster item; expected backticked role and path"
                    )
                    raise ValueError(msg)
                entries.append(match.groups())
            if not entries or len(entries) != len(declaration.agents):
                msg = "empty or invalid native Specialists spawned declaration"
                raise ValueError(msg)
        declarations.append(declaration)
    return tuple(declarations)


def _signature(outcome: lane_result.CollectorOutcome) -> tuple[tuple[str, str], ...]:
    """Compare complete role/path declarations independently of list order."""
    return tuple(sorted((node.name, node.role) for node in outcome.agents))


def _agree(declarations: tuple[lane_result.CollectorOutcome, ...]) -> None:
    """Reject contradictory blocks even when the last one is valid."""
    if len({_signature(declaration) for declaration in declarations}) > 1:
        msg = "conflicting Specialists spawned declarations"
        raise ValueError(msg)


def _record(line: bytes, ordinal: int) -> dict[str, object]:
    """Decode through the shared codec and reject truncated/non-object records."""
    try:
        return codec.decode(line, dict[str, Any])
    except (ValueError, TypeError) as error:
        msg = f"native record {ordinal} is invalid JSON or not an object"
        raise ValueError(msg) from error


def _payload(record: Mapping[str, object]) -> dict[str, object]:
    """Require a mapping payload at the native evidence boundary."""
    payload = record.get("payload")
    if not isinstance(payload, dict):
        msg = "native record has no object payload"
        raise TypeError(msg)
    return payload


def _parent_source(sessions_root: Path, parent_id: str) -> Path | None:
    """Locate the genuine parent by metadata, verifying filename matches too."""
    matches: list[Path] = []
    for source in sorted(sessions_root.rglob("rollout-*.jsonl")):
        named_parent = source.name.endswith(f"-{parent_id}.jsonl")
        try:
            with source.open("rb") as handle:
                first = _record(handle.readline(), 1)
            metadata = _payload(first)
        except OSError, ValueError, TypeError:
            if named_parent:
                raise
            continue
        if first.get("type") != "session_meta":
            if named_parent:
                msg = "parent transcript has no session_meta record"
                raise ValueError(msg)
            continue
        if metadata.get("id") == parent_id:
            matches.append(source)
        elif named_parent:
            msg = "parent transcript session_meta.id does not match logged parent"
            raise ValueError(msg)
    if len(matches) > 1:
        msg = "multiple native transcripts match logged parent"
        raise ValueError(msg)
    return matches[0] if matches else None


def _epoch(value: object) -> float:
    """Require timezone-aware ISO timestamps for the supervised interval."""
    if not isinstance(value, str):
        msg = "native timestamp is missing or not text"
        raise TypeError(msg)
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        msg = "native timestamp has no timezone"
        raise ValueError(msg)
    return stamp.timestamp()


def _final_text(payload: Mapping[str, object]) -> str:
    """Extract output text only from the already verified assistant message."""
    content = payload.get("content")
    if not isinstance(content, list) or not content:
        msg = "native final has no content array"
        raise ValueError(msg)
    texts: list[str] = []
    for item in content:
        if (
            not isinstance(item, dict)
            or item.get("type") != "output_text"
            or not isinstance(item.get("text"), str)
        ):
            msg = "native final content is not output_text"
            raise ValueError(msg)
        texts.append(item["text"])
    return "".join(texts)


def _message_turn(payload: Mapping[str, object]) -> str:
    """Use the turn binding observed in the installed CLI's native transcript."""
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    turn_id = metadata.get("turn_id") if isinstance(metadata, dict) else None
    if not isinstance(turn_id, str) or not turn_id:
        msg = "native final has no verified turn_id"
        raise ValueError(msg)
    return turn_id


def _read_turn(source: Path, started_at: str, finished_at: str) -> _NativeTurn:
    """Validate a single current completed root turn and its final messages."""
    start, finish = _epoch(started_at), _epoch(finished_at)
    if finish < start:
        msg = "supervised run interval is reversed"
        raise ValueError(msg)
    state: _TurnState | None = None
    completed: list[_NativeTurn] = []
    rendered: list[_Rendered] = []
    thread_id = ""
    with source.open("rb") as handle:
        for ordinal, line in enumerate(handle, 1):
            if not line.endswith(b"\n"):
                msg = f"native record {ordinal} is truncated (missing line terminator)"
                raise ValueError(msg)
            record = _record(line, ordinal)
            payload = _payload(record)
            timestamp = record.get("timestamp")
            epoch = _epoch(timestamp)
            in_run = start <= epoch <= finish
            if ordinal == 1:
                thread_id = _thread_identity(payload)
            rendered.extend(
                _rendered_record(
                    record, payload, ordinal, str(timestamp), in_run=in_run
                )
            )
            _reject_legacy_final(record, payload, in_run=in_run)
            if record.get("type") == "event_msg" and in_run:
                event = payload.get("type")
                if event == "task_started":
                    state = _start_turn(payload, ordinal, str(timestamp), state)
                elif event == "task_complete":
                    marker = _Final("", ordinal, str(timestamp))
                    completed.append(_complete_turn(source, state, payload, marker))
                    state = None
            elif _is_final(record, payload) and in_run:
                _append_final(state, payload, ordinal, str(timestamp))
    if state is not None or len(completed) != 1:
        msg = "native evidence has no unique completed current root turn"
        raise ValueError(msg)
    turn = completed[0]
    return _NativeTurn(
        turn.source,
        turn.turn_id,
        turn.finals,
        turn.terminal,
        turn.started,
        thread_id,
        tuple(rendered),
    )


def _thread_identity(payload: Mapping[str, object]) -> str:
    """Require the native thread identity from the already located parent."""
    identity = payload.get("id")
    if not isinstance(identity, str) or not identity:
        msg = "native parent identity is missing"
        raise ValueError(msg)
    return identity


def _rendered_record(
    record: Mapping[str, object],
    payload: Mapping[str, object],
    ordinal: int,
    timestamp: str,
    *,
    in_run: bool,
) -> tuple[_Rendered, ...]:
    """Retain interval-bounded native completed items for later same-ID checks."""
    if (
        record.get("type") == "event_msg"
        and payload.get("type") == "item_completed"
        and in_run
    ):
        return (_Rendered(payload, ordinal, timestamp),)
    return ()


def _append_final(
    state: _TurnState | None,
    payload: Mapping[str, object],
    ordinal: int,
    timestamp: str,
) -> None:
    """Retain a raw final only after its root turn binding is verified."""
    if state is None or _message_turn(payload) != state.turn_id:
        msg = "native final does not belong to current root turn"
        raise ValueError(msg)
    identity = payload.get("id")
    state.finals.append(
        _Final(
            _final_text(payload),
            ordinal,
            timestamp,
            identity if isinstance(identity, str) else "",
        )
    )


def _start_turn(
    payload: Mapping[str, object],
    ordinal: int,
    timestamp: str,
    current: _TurnState | None,
) -> _TurnState:
    """Require a task_started for the actual root turn, not a delegated turn."""
    turn_id = payload.get("turn_id")
    if current is not None:
        msg = "native task_started overlaps an uncompleted root turn"
        raise ValueError(msg)
    if (
        not isinstance(turn_id, str)
        or not turn_id
        or payload.get("root_turn_id") != turn_id
    ):
        msg = "native task_started does not identify a root turn"
        raise ValueError(msg)
    return _TurnState(turn_id, _Final("", ordinal, timestamp), [])


def _complete_turn(
    source: Path,
    state: _TurnState | None,
    payload: Mapping[str, object],
    marker: _Final,
) -> _NativeTurn:
    """Check current root completion before accepting terminal message evidence."""
    if state is None or payload.get("turn_id") != state.turn_id:
        msg = "native task_complete has no matching current task_started"
        raise ValueError(msg)
    terminal = payload.get("last_agent_message")
    if not isinstance(terminal, str) or not terminal.strip() or not state.finals:
        msg = "native terminal message or latest root final is missing"
        raise ValueError(msg)
    return _NativeTurn(
        source,
        state.turn_id,
        tuple(state.finals),
        _Final(terminal, marker.ordinal, marker.timestamp),
        state.started,
        "",
    )


def _is_final(record: Mapping[str, object], payload: Mapping[str, object]) -> bool:
    """Accept only modern native assistant final_answer messages."""
    return (
        record.get("type") == "response_item"
        and payload.get("type") == "message"
        and payload.get("role") == "assistant"
        and payload.get("phase") == "final_answer"
    )


def _reject_legacy_final(
    record: Mapping[str, object], payload: Mapping[str, object], *, in_run: bool
) -> None:
    """An unsupported legacy final cannot be ignored between eligible finals."""
    if (
        in_run
        and record.get("type") == "response_item"
        and payload.get("type") == "message"
        and payload.get("role") == "assistant"
        and payload.get("channel") == "final"
    ):
        msg = "legacy channel=final evidence is unsupported"
        raise ValueError(msg)


def _has_citation(text: str) -> bool:
    """Recognize the citation boundary, including incomplete boundary tags."""
    return "<oai-mem-citation" in text or "</oai-mem-citation" in text


def _citation_entry(line: str) -> dict[str, object]:
    """Parse one finite citation record without interpreting its contents."""
    match = _CITATION_ENTRY.fullmatch(line)
    if match is None or int(match["end"]) < int(match["start"]):
        msg = "unsupported trailing memory citation entry"
        raise ValueError(msg)
    return {
        "path": match["path"],
        "lineStart": int(match["start"]),
        "lineEnd": int(match["end"]),
        "note": match["note"],
    }


def _citation_parts(text: str) -> tuple[str, dict[str, object]]:
    """Validate the observed trailing grammar; native rendering stays authoritative.

    A generic markup renderer cannot establish the native same-message boundary.
    Parse only enough to bind this observed transform to native citation metadata.
    """
    normalized = _normalized(text)
    prefix, marker, suffix = normalized.partition("\n<oai-mem-citation>\n")
    if not marker or not prefix.strip() or _has_citation(prefix):
        msg = "memory citation is not one standalone trailing block"
        raise ValueError(msg)
    lines = suffix.splitlines()
    if (
        len(lines) < _MIN_CITATION_LINES
        or lines[0] != "<citation_entries>"
        or lines[-2:] != ["</rollout_ids>", "</oai-mem-citation>"]
        or lines.count("</citation_entries>") != 1
    ):
        msg = "unsupported trailing memory citation structure"
        raise TypeError(msg)
    boundary = lines.index("</citation_entries>")
    if lines[boundary + 1 : boundary + 2] != ["<rollout_ids>"]:
        msg = "memory citation sections are missing or out of order"
        raise ValueError(msg)
    entries = [_citation_entry(line) for line in lines[1:boundary]]
    rollouts = lines[boundary + 2 : -2]
    if not entries or any(_ROLLOUT_ID.fullmatch(line) is None for line in rollouts):
        msg = "unsupported memory citation records"
        raise ValueError(msg)
    return _normalized(prefix), {"entries": entries, "rolloutIds": rollouts}


def _rendered_item(turn: _NativeTurn, final: _Final) -> dict[str, object]:
    """Require one genuine same-ID AgentMessage in this completed root turn."""
    matches = [
        event
        for event in turn.rendered
        if _matches_rendered_id(event, final.message_id)
    ]
    if (
        not final.message_id
        or len(matches) != 1
        or sum(item.message_id == final.message_id for item in turn.finals) != 1
    ):
        msg = "memory citation has no unique same-ID rendered attestation"
        raise ValueError(msg)
    event = matches[0]
    payload = event.payload
    if (
        payload.get("thread_id") != turn.thread_id
        or payload.get("turn_id") != turn.turn_id
        or not turn.started.ordinal < event.ordinal < turn.terminal.ordinal
        or not _epoch(turn.started.timestamp)
        <= _epoch(event.timestamp)
        <= _epoch(turn.terminal.timestamp)
    ):
        msg = "rendered attestation is outside the completed parent turn"
        raise ValueError(msg)
    item = payload["item"]
    if (
        not isinstance(item, dict)
        or item.get("type") != "AgentMessage"
        or item.get("phase") != "final_answer"
    ):
        msg = "rendered attestation is not a native final AgentMessage"
        raise ValueError(msg)
    return item


def _matches_rendered_id(event: _Rendered, message_id: str) -> bool:
    """Match the ID before validating any other untrusted rendered fields."""
    item = event.payload.get("item")
    return isinstance(item, dict) and item.get("id") == message_id


def _rendered_text(item: Mapping[str, object]) -> str:
    """Accept only the observed native Text content array."""
    content = item.get("content")
    if not isinstance(content, list) or not content:
        msg = "rendered attestation has no content array"
        raise ValueError(msg)
    texts: list[str] = []
    for part in content:
        if (
            not isinstance(part, dict)
            or part.get("type") != "Text"
            or not isinstance(part.get("text"), str)
        ):
            msg = "rendered attestation content is not native Text"
            raise ValueError(msg)
        texts.append(part["text"])
    return "".join(texts)


def _citation_metadata(item: Mapping[str, object]) -> dict[str, object]:
    """Reject unsupported metadata rather than coercing it into matching values."""
    citation = item.get("memory_citation")
    if not isinstance(citation, dict) or set(citation) != {"entries", "rolloutIds"}:
        msg = "rendered attestation has unsupported citation metadata"
        raise ValueError(msg)
    entries = citation["entries"]
    rollouts = citation["rolloutIds"]
    if not isinstance(entries, list) or not isinstance(rollouts, list):
        msg = "rendered citation metadata records are not arrays"
        raise TypeError(msg)
    for entry in entries:
        _validate_metadata_entry(entry)
    if any(not isinstance(value, str) for value in rollouts):
        msg = "rendered citation rollout IDs are not text"
        raise ValueError(msg)
    return citation


def _validate_metadata_entry(entry: object) -> None:
    """Require the exact observed field names and scalar types."""
    if (
        not isinstance(entry, dict)
        or set(entry) != {"path", "lineStart", "lineEnd", "note"}
        or not isinstance(entry["path"], str)
        or not isinstance(entry["note"], str)
        or type(entry["lineStart"]) is not int
        or type(entry["lineEnd"]) is not int
    ):
        msg = "rendered citation entry has unsupported fields or types"
        raise ValueError(msg)


def _visible_final(turn: _NativeTurn, final: _Final) -> str:
    """Bind each citation-bearing final to its own native rendered message."""
    if not _has_citation(final.text):
        return final.text
    prefix, citation = _citation_parts(final.text)
    item = _rendered_item(turn, final)
    visible = _rendered_text(item)
    if _normalized(visible) != prefix or _citation_metadata(item) != citation:
        msg = "raw memory citation and rendered attestation disagree"
        raise ValueError(msg)
    return visible


def _select_native(turn: _NativeTurn, captured: str) -> _FinalSelection:
    """Only absence in the latest final permits selecting an earlier roster."""
    latest = turn.finals[-1]
    if _normalized(captured) != _normalized(turn.terminal.text):
        msg = "captured output and terminal message differ"
        raise ValueError(msg)
    visible = tuple(_visible_final(turn, final) for final in turn.finals)
    if _normalized(captured) != _normalized(visible[-1]):
        msg = "captured output, latest native root final and terminal message differ"
        raise ValueError(msg)
    declarations = tuple(_declarations(text, native=True) for text in visible)
    _agree(tuple(item for group in declarations for item in group))
    selected_index = next(
        (
            index
            for index in range(len(declarations) - 1, -1, -1)
            if declarations[index]
        ),
        None,
    )
    if selected_index is None:
        msg = "eligible native finals contain no Specialists spawned declaration"
        raise ValueError(msg)
    selected = turn.finals[selected_index]
    return _FinalSelection(
        report_text=selected.text,
        self_report=declarations[selected_index][-1],
        reason="latest-native-declaration"
        if selected is latest
        else "prior-final-absence",
        source=str(turn.source),
        turn_id=turn.turn_id,
        selected_ordinal=selected.ordinal,
        selected_timestamp=selected.timestamp,
        latest_ordinal=latest.ordinal,
        latest_timestamp=latest.timestamp,
        terminal_ordinal=turn.terminal.ordinal,
        terminal_timestamp=turn.terminal.timestamp,
        started_ordinal=turn.started.ordinal,
        started_timestamp=turn.started.timestamp,
        selected_hash=_digest(selected.text),
        terminal_hash=_digest(turn.terminal.text),
        latest_hash=_digest(latest.text),
        captured_hash=_digest(captured),
        transform=_CITATION_TRANSFORM
        if any(_has_citation(final.text) for final in turn.finals)
        else "",
    )


def select_final_report(
    captured: str,
    *,
    parent_id: str | None,
    sessions_root: Path,
    started_at: str,
    finished_at: str,
) -> _FinalSelection:
    """Select and validate a report; missing native evidence never enables recovery.

    Valid captured declarations retain their existing compatibility route when
    no native parent exists. When a parent exists its whole current completed
    turn must pass validation, including every native declaration.
    """
    source: Path | None = None
    turn: _NativeTurn | None = None
    try:
        source = _parent_source(sessions_root, parent_id) if parent_id else None
        if source is not None:
            turn = _read_turn(source, started_at, finished_at)
            return _select_native(turn, captured)
        return _select_direct(captured)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        detail = f"native final selection refused: {error}"
        return _FinalSelection(
            captured,
            lane_result.CollectorOutcome(
                source=lane_result.AgentSource.SELF_REPORT,
                available=False,
                error=detail,
            ),
            "refused",
            source=str(source) if source is not None else "",
            turn_id=turn.turn_id if turn is not None else "",
            latest_ordinal=turn.finals[-1].ordinal if turn is not None else None,
            latest_timestamp=turn.finals[-1].timestamp if turn is not None else "",
            terminal_ordinal=turn.terminal.ordinal if turn is not None else None,
            terminal_timestamp=turn.terminal.timestamp if turn is not None else "",
            started_ordinal=turn.started.ordinal if turn is not None else None,
            started_timestamp=turn.started.timestamp if turn is not None else "",
            error=detail,
            terminal_hash=_digest(turn.terminal.text) if turn is not None else "",
            latest_hash=_digest(turn.finals[-1].text) if turn is not None else "",
            captured_hash=_digest(captured),
        )


def _select_direct(captured: str) -> _FinalSelection:
    """Keep direct-output compatibility while refusing unsupported recovery."""
    if _has_citation(captured):
        msg = "no native rendered attestation for captured memory citation"
        raise ValueError(msg)
    declarations = _declarations(captured, native=False)
    _agree(declarations)
    if not declarations:
        msg = "no native parent evidence for prior-final recovery"
        raise ValueError(msg)
    return _FinalSelection(
        captured,
        declarations[-1],
        "captured-direct-no-native",
        selected_hash=_digest(captured),
        captured_hash=_digest(captured),
    )


def render_provenance(
    selection: _FinalSelection,
    *,
    identity: tuple[str, str | None],
    captured_path: Path,
    interval: tuple[str, str],
    participation_consistent: bool,
) -> str:
    """Emit metadata and hashes only; never include report or tool content."""
    fields = (
        ("run id", identity[0]),
        ("parent id", identity[1] or "unavailable"),
        ("completed turn id", selection.turn_id or "unavailable"),
        ("source path", selection.source or str(captured_path)),
        ("supervised start", interval[0]),
        ("supervised finish", interval[1]),
        (
            "task_started ordinal/timestamp",
            f"{selection.started_ordinal} / {selection.started_timestamp}",
        ),
        (
            "selected ordinal/timestamp",
            f"{selection.selected_ordinal} / {selection.selected_timestamp}",
        ),
        (
            "latest ordinal/timestamp",
            f"{selection.latest_ordinal} / {selection.latest_timestamp}",
        ),
        (
            "terminal ordinal/timestamp",
            f"{selection.terminal_ordinal} / {selection.terminal_timestamp}",
        ),
        ("selected message SHA256", selection.selected_hash or "unavailable"),
        ("terminal message SHA256", selection.terminal_hash or "unavailable"),
        ("latest message SHA256", selection.latest_hash or "unavailable"),
        ("captured message SHA256", selection.captured_hash or "unavailable"),
        ("display transform", selection.transform or "none"),
        ("selection reason", selection.reason),
        ("selection outcome", "refused" if selection.error else "selected"),
        (
            "participation outcome",
            "consistent" if participation_consistent else "failed",
        ),
    )
    return (
        "# Roster provenance\n\n"
        "Normalization: CRLF/CR to LF; strip each line's trailing whitespace and "
        "final trailing whitespace. Interior whitespace remains significant.\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in fields)
        + "\n\nParticipation reconciliation does not assert implementation delivery, "
        "research success, or resolution of licensed dissent. "
        "Raw artifacts are preserved.\n"
        "Native terminal and latest hashes are unavailable on the direct captured "
        "compatibility route.\n"
    )
