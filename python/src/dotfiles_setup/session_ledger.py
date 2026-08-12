# Copyright (c) 2026 Raymond Manaloto
"""Bounded transcript evidence for requirement and promise review.

The existing session review intentionally mines command shapes.  This module is
the separate, conservative lane for what the user asked for and what the agent
said it would do.  It normalizes native Claude and Codex JSONL without deciding
that a requirement is satisfied: semantic judgement belongs to the reviewer,
while this layer makes silent omission observable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from base64 import b64decode
from binascii import Error as Base64Error
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, unquote_to_bytes, urlparse

from dotfiles_setup import command_audit, session_gate

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

DEFAULT_REQUIREMENT_SESSION_LIMIT = 5
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_RENDER_BYTES = 64 * 1024
_PROMISE = re.compile(
    r"\b(?:I will|I'll|we will|I am going to|I'm going to)\b", re.IGNORECASE
)
_AUTHORITY = re.compile(
    r"authority|approval|permission|publish|commit|push|stage|mutation|write",
    re.IGNORECASE,
)
_ATTACHMENT_TAG = re.compile(
    r"<(?P<kind>image|attachment|file)\b[^>]*\bpath=[\"'](?P<path>[^\"']+)[\"'][^>]*>",
    re.IGNORECASE,
)
_CREDENTIAL_LAUNCHER = re.compile(
    r"(?=.*\b(?:credential|token|fnox|doppler|keychain|environment variable)s?\b)"
    r"(?=.*\b(?:absent|missing|unavailable|launcher|worktree|scope|inherit)\w*\b)",
    re.IGNORECASE,
)
_GIT_HOOK_CONTAMINATION = re.compile(
    r"(?=.*\b(?:git hook|pre-push|GIT_DIR|GIT_WORK_TREE|worktree)\b)"
    r"(?=.*\b(?:contaminat|corrupt|rewrite|escape|inherit)\w*\b)",
    re.IGNORECASE,
)


class Provider(StrEnum):
    """Transcript producer."""

    CODEX = "codex"
    CLAUDE = "claude"


class EventKind(StrEnum):
    """Canonical evidence kinds retained by the parser."""

    USER_MESSAGE = "user_message"
    UNVERIFIABLE_USER_MESSAGE = "unverifiable_user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    FORM_QUESTION = "form_question"
    FORM_ANSWER = "form_answer"
    ATTACHMENT = "attachment"
    COMPACTION = "compaction"
    AGENT_MESSAGE = "agent_message"
    AUTHORITY_CONTEXT = "authority_context"
    OPAQUE_PAYLOAD = "opaque_payload"
    INHERITED_USER_MESSAGE = "inherited_user_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TERMINAL_STATE = "terminal_state"


class ReviewStatus(StrEnum):
    """Status of a semantic claim; parsing can only produce UNREVIEWED."""

    UNREVIEWED = "unreviewed"
    OPEN = "open"
    SATISFIED = "satisfied"
    WITHDRAWN = "withdrawn"
    CONTRADICTED = "contradicted"


class CoverageStatus(StrEnum):
    """Whether every encountered structural record was understood."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class IterationAction(StrEnum):
    """Next safe action for the bounded self-improvement loop."""

    CONVERGED = "converged"
    PREVENTION_RECORDED = "prevention_recorded"
    NEEDS_AGENT_ACTION = "needs_agent_action"


class SelectionCertification(StrEnum):
    """Whether the caller proved which native task is being reviewed."""

    NOT_REQUESTED = "not_requested"
    EXPLICIT_SESSION_ID = "explicit_session_id"
    UNCERTIFIED_ACTIVITY_FALLBACK = "uncertified_activity_fallback"


@dataclass(frozen=True)
class EvidenceRef:
    """Stable pointer from a ledger item to one raw JSONL record."""

    provider: Provider
    source_id: str
    line: int
    event_id: str
    record_sha256: str


@dataclass(frozen=True)
class AttachmentMetadata:
    """Safe attachment facts; payload bytes are deliberately not retained."""

    media_type: str
    name: str
    payload_sha256: str
    payload_bytes: int


@dataclass(frozen=True)
class CanonicalEvent:
    """One normalized transcript event."""

    kind: EventKind
    actor: str
    text: str
    evidence: EvidenceRef
    metadata: tuple[tuple[str, str], ...] = ()
    attachment: AttachmentMetadata | None = None


@dataclass(frozen=True)
class RequirementEntry:
    """Exact user-authored evidence awaiting semantic review."""

    requirement_id: str
    statement: str
    evidence: EvidenceRef
    source_kind: EventKind
    authority_relevant: bool
    status: ReviewStatus = ReviewStatus.UNREVIEWED


@dataclass(frozen=True)
class PromiseEntry:
    """An explicit assistant commitment awaiting fulfillment review."""

    promise_id: str
    statement: str
    evidence: EvidenceRef
    status: ReviewStatus = ReviewStatus.UNREVIEWED


@dataclass(frozen=True)
class HighSeverityFinding:
    """A one-off safety signal that must not be hidden by frequency ranking."""

    finding_id: str
    category: str
    statement: str
    evidence: EvidenceRef
    status: ReviewStatus = ReviewStatus.UNREVIEWED


@dataclass(frozen=True)
class PreventionDisposition:
    """Evidence that a confirmed finding was converted into prevention."""

    finding_id: str
    carrier: str
    mutation_evidence: str
    gate_evidence: str
    issue_receipt: str
    attested: bool = False

    @property
    def complete(self) -> bool:
        """Persisted audit evidence never authorizes completion or replay."""
        return False

    @property
    def audit_evidence_complete(self) -> bool:
        """Return whether all persisted, non-authorizing audit references exist."""
        return self.attested and all(
            value.strip()
            for value in (
                self.finding_id,
                self.carrier,
                self.mutation_evidence,
                self.gate_evidence,
                self.issue_receipt,
            )
        )


@dataclass(frozen=True)
class ReviewIteration:
    """Resumable state for one evidence -> prevention iteration."""

    number: int
    manifest_sha256: str
    action: IterationAction
    disposition_ids: tuple[str, ...]
    unresolved_finding_ids: tuple[str, ...]
    repo_root: str = ""
    session_id: str = ""
    selection_certification: SelectionCertification = (
        SelectionCertification.NOT_REQUESTED
    )
    max_iterations: int = 1
    remaining_iterations: int = 0
    artifacts: tuple[ArtifactRef, ...] = ()
    required_roles: tuple[str, ...] = (
        "specialized_fixer",
        "independent_qa",
        "adversarial_reviewer",
    )
    receipt_state: tuple[FindingReceiptState, ...] = ()

    def to_json(self) -> str:
        """Return a deterministic packet an external agent team can resume."""
        rendered = json.dumps(asdict(self), indent=2, sort_keys=True)
        if len(rendered.encode()) > MAX_RENDER_BYTES:
            message = "iteration packet exceeds the hard output cap"
            raise ValueError(message)
        return rendered


@dataclass(frozen=True)
class ArtifactRef:
    """Content-addressed persisted artifact used by a resumable iteration."""

    kind: str
    path: str
    byte_count: int
    sha256: str


@dataclass(frozen=True)
class FindingReceiptState:
    """Verified prevention evidence available for one finding."""

    finding_id: str
    carrier: bool
    mutation: bool
    gate: bool
    issue: bool


@dataclass(frozen=True)
class ReceiptAttestation:
    """Identity supplied by the trusted gate runner for one invocation."""

    run_id: str
    nonce: str
    allow_test_signed: bool = False


@dataclass(frozen=True)
class IterationContext:
    """Caller-provided resumption identity and bounded iteration budget."""

    max_iterations: int = 1
    repo_root: str = ""
    session_id: str = ""
    artifacts: tuple[ArtifactRef, ...] = ()


DEFAULT_ITERATION_CONTEXT = IterationContext()


@dataclass(frozen=True)
class SessionLineage:
    """Root/child relationship carried by native transcript metadata."""

    provider: Provider
    source_id: str
    session_id: str
    parent_id: str
    agent_path: str
    agent_role: str
    inherited_prefix_sha256: str = ""
    inherited_event_count: int = 0
    history_base_ordinal: str = ""


@dataclass(frozen=True)
class SourceCutoff:
    """Append-safe identity for the exact raw prefix reviewed."""

    provider: Provider
    source_id: str
    source_path: str
    byte_count: int
    line_count: int
    prefix_sha256: str
    last_event_id: str
    final_ordinal: str
    final_timestamp: str
    open_turn: bool

    def matches(self, path: Path) -> bool:
        """Return whether ``path`` still begins with the reviewed bytes."""
        try:
            with path.open("rb") as stream:
                prefix = stream.read(self.byte_count)
        except OSError:
            return False
        return (
            len(prefix) == self.byte_count
            and hashlib.sha256(prefix).hexdigest() == self.prefix_sha256
        )


@dataclass(frozen=True)
class TranscriptSource:
    """One provider-qualified JSONL path."""

    provider: Provider
    path: Path


@dataclass(frozen=True)
class CoverageSelection:
    """Caller-authenticated identity and bounded root count."""

    limit: int = DEFAULT_REQUIREMENT_SESSION_LIMIT
    session_id: str | None = None
    require_active_identity: bool = False


DEFAULT_COVERAGE_SELECTION = CoverageSelection()
_UNCERTIFIED_ACTIVITY = (
    "active session identity is unverified; latest activity is only a fallback"
)


@dataclass(frozen=True)
class RequirementCoverage:
    """Typed, provenance-bearing input to a human or model review."""

    events: tuple[CanonicalEvent, ...]
    requirements: tuple[RequirementEntry, ...]
    promises: tuple[PromiseEntry, ...]
    high_severity_findings: tuple[HighSeverityFinding, ...]
    dispositions: tuple[PreventionDisposition, ...]
    lineage: tuple[SessionLineage, ...]
    cutoffs: tuple[SourceCutoff, ...]
    recorded_cwd: str = ""
    omissions: tuple[str, ...] = field(default_factory=tuple)
    selection_certification: SelectionCertification = (
        SelectionCertification.NOT_REQUESTED
    )
    selected_session_id: str = ""
    schema_version: int = 1

    @property
    def status(self) -> CoverageStatus:
        """Incomplete is fail-loud: an unknown record is never a clean review."""
        return (
            CoverageStatus.INCOMPLETE
            if self.omissions or disposition_omissions(self)
            else CoverageStatus.COMPLETE
        )

    @property
    def manifest_sha256(self) -> str:
        """Stable digest of the sorted source cutoffs."""
        rows = [
            (
                cutoff.provider,
                cutoff.source_id,
                cutoff.byte_count,
                cutoff.line_count,
                cutoff.prefix_sha256,
                cutoff.last_event_id,
                cutoff.final_ordinal,
                cutoff.final_timestamp,
                cutoff.open_turn,
            )
            for cutoff in sorted(
                self.cutoffs, key=lambda item: (item.provider, item.source_id)
            )
        ]
        raw = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def to_json(self) -> str:
        """Render bounded references from which the native prefix is recoverable.

        Transcript bodies deliberately do not belong in this public artifact.  A
        path, byte cutoff, and digest identify the exact lossless native prefix;
        aggregate counts make silent parser loss visible without duplicating it.
        """
        payload_digests = sorted(
            {
                value
                for event in self.events
                for key, value in event.metadata
                if key.endswith("_sha256")
            }
            | {
                event.attachment.payload_sha256
                for event in self.events
                if event.attachment is not None and event.attachment.payload_sha256
            }
        )
        omissions = [*self.omissions, *disposition_omissions(self)]
        payload = {
            "schema_version": self.schema_version,
            "recorded_cwd": self.recorded_cwd,
            "selection_certification": self.selection_certification,
            "selected_session_id": self.selected_session_id,
            "status": self.status,
            "manifest_sha256": self.manifest_sha256,
            "counts": {
                "sources": len(self.cutoffs),
                "events": len(self.events),
                "requirements": len(self.requirements),
                "promises": len(self.promises),
                "high_severity_findings": len(self.high_severity_findings),
                "dispositions": len(self.dispositions),
                "lineage": len(self.lineage),
            },
            "cutoffs": [asdict(item) for item in self.cutoffs],
            "finding_ids": [item.finding_id for item in self.high_severity_findings],
            "disposition_ids": [item.finding_id for item in self.dispositions],
            "payload_sha256_sample": payload_digests[:64],
            "payload_sha256_count": len(payload_digests),
            "payload_sha256_manifest": hashlib.sha256(
                "\n".join(payload_digests).encode()
            ).hexdigest(),
            "opaque_payload_kinds": sorted(
                {
                    event.text
                    for event in self.events
                    if event.kind == EventKind.OPAQUE_PAYLOAD
                }
            ),
            "omission_count": len(omissions),
            "omissions_sha256": hashlib.sha256(
                "\n".join(omissions).encode()
            ).hexdigest(),
        }
        rendered = json.dumps(
            payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False
        )
        if len(rendered.encode()) > MAX_RENDER_BYTES:
            message = "evidence reference artifact exceeds the hard output cap"
            raise ValueError(message)
        return rendered

    def cutoffs_to_json(self) -> str:
        """Render the independently hashable native-prefix reconstruction map."""
        payload = {
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
            "selection_certification": self.selection_certification,
            "selected_session_id": self.selected_session_id,
            "cutoffs": [asdict(item) for item in self.cutoffs],
        }
        rendered = json.dumps(
            payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False
        )
        if len(rendered.encode()) > MAX_RENDER_BYTES:
            message = "cutoff artifact exceeds the hard output cap"
            raise ValueError(message)
        return rendered


@dataclass
class _Accumulator:
    events: list[CanonicalEvent] = field(default_factory=list)
    requirements: list[RequirementEntry] = field(default_factory=list)
    promises: list[PromiseEntry] = field(default_factory=list)
    high_severity_findings: list[HighSeverityFinding] = field(default_factory=list)
    lineage: list[SessionLineage] = field(default_factory=list)
    cutoffs: list[SourceCutoff] = field(default_factory=list)
    omissions: list[str] = field(default_factory=list)
    seen_event_ids: set[str] = field(default_factory=set)
    form_calls: dict[str, tuple[EvidenceRef, str, frozenset[str]]] = field(
        default_factory=dict
    )
    form_results: dict[str, tuple[str, frozenset[str]]] = field(default_factory=dict)
    seen_attachment_sha256: set[str] = field(default_factory=set)
    seen_finding_categories: set[str] = field(default_factory=set)
    tool_calls: dict[str, tuple[EvidenceRef, str]] = field(default_factory=dict)
    tool_results: dict[str, str] = field(default_factory=dict)
    approved_attachment_roots: tuple[Path, ...] = ()


@dataclass(frozen=True)
class _CodexParseContext:
    direct_messages: dict[str, list[EvidenceRef]]
    form_schema_status: str


_CODEX_EVENT_TYPES = frozenset(
    {
        "item_completed",
        "agent_message",
        "task_complete",
        "task_started",
        "thread_settings_applied",
        "token_count",
        "user_message",
    }
)
_CODEX_ITEM_TYPES = frozenset(
    {
        "AgentMessage",
        "CollabAgentToolCall",
        "CommandExecution",
        "ContextCompaction",
        "Extension",
        "FileChange",
        "ImageView",
        "McpToolCall",
        "Plan",
        "Reasoning",
        "SubAgentActivity",
        "UserMessage",
    }
)


def codex_sessions_base(
    env: Mapping[str, str] | None = None, home: Path | None = None
) -> Path:
    """Return the native Codex sessions directory, honoring ``CODEX_HOME``."""
    values = env if env is not None else os.environ
    home = home if home is not None else Path.home()
    return Path(values.get("CODEX_HOME", home / ".codex")) / "sessions"


def _json_object(raw: bytes) -> dict[str, object] | None:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError, UnicodeDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _first_session_meta(path: Path) -> dict[str, object] | None:
    try:
        with path.open("rb") as stream:
            for raw in stream:
                obj = _json_object(raw)
                if obj is not None and obj.get("type") == "session_meta":
                    payload = obj.get("payload")
                    return payload if isinstance(payload, dict) else None
    except OSError:
        return None
    return None


def _is_codex_root(meta: Mapping[str, object]) -> bool:
    return meta.get("thread_source") != "subagent" and not meta.get("parent_thread_id")


def _codex_activity_timestamp(path: Path) -> str:
    """Latest native user/turn activity, not the root's creation timestamp."""
    latest = ""
    try:
        with path.open("rb") as stream:
            for raw in stream:
                obj = _json_object(raw)
                if obj is None:
                    continue
                record_type = obj.get("type")
                payload = obj.get("payload")
                values = payload if isinstance(payload, dict) else {}
                relevant = record_type == "turn_context"
                if record_type == "event_msg":
                    event_type = values.get("type")
                    item = values.get("item")
                    relevant = event_type in {"task_started", "user_message"} or (
                        event_type == "item_completed"
                        and isinstance(item, dict)
                        and item.get("type") == "UserMessage"
                    )
                if relevant:
                    latest = max(latest, str(obj.get("timestamp", "")))
    except OSError:
        return ""
    return latest


def discover_codex_transcripts(
    repo_root: Path,
    *,
    base: Path | None = None,
    limit: int = DEFAULT_REQUIREMENT_SESSION_LIMIT,
    session_id: str | None = None,
) -> list[Path]:
    """Find selected Codex roots plus every child sharing their session id."""
    base = base if base is not None else codex_sessions_base()
    if not base.is_dir():
        return []
    rows: list[tuple[Path, dict[str, object], str]] = []
    for path in base.glob("**/*.jsonl"):
        meta = _first_session_meta(path)
        if meta is None or str(meta.get("cwd", "")) != str(repo_root):
            continue
        rows.append((path, meta, _codex_activity_timestamp(path)))
    root_rows = (row for row in rows if _is_codex_root(row[1]))
    if session_id:
        root_rows = (
            row
            for row in root_rows
            if str(row[1].get("session_id", row[1].get("id", ""))) == session_id
        )
    roots = sorted(
        root_rows,
        key=lambda row: (row[2], str(row[1].get("timestamp", ""))),
        reverse=True,
    )[:limit]
    session_ids = {
        str(meta.get("session_id", meta.get("id", ""))) for _, meta, _ in roots
    }
    selected = [
        path
        for path, meta, _ in rows
        if str(meta.get("session_id", meta.get("id", ""))) in session_ids
    ]
    return sorted(selected, key=str)


def discover_sources(
    repo_root: Path,
    *,
    limit: int = DEFAULT_REQUIREMENT_SESSION_LIMIT,
    codex_base: Path | None = None,
    claude_base: Path | None = None,
    session_id: str | None = None,
) -> list[TranscriptSource]:
    """Discover both native transcript providers for the same repository."""
    codex = discover_codex_transcripts(
        repo_root, base=codex_base, limit=limit, session_id=session_id
    )
    claude_root = (
        claude_base if claude_base is not None else command_audit.transcripts_base()
    )
    claude = command_audit.project_transcripts(claude_root, repo_root, limit=limit)
    if session_id:
        claude = [path for path in claude if session_id in path.name]
    return [
        *(TranscriptSource(Provider.CODEX, path) for path in codex),
        *(TranscriptSource(Provider.CLAUDE, path) for path in claude),
    ]


def _source_id(
    provider: Provider, records: list[tuple[int, dict[str, object], bytes]]
) -> str:
    for _, obj, _ in records:
        if obj.get("type") != "session_meta":
            continue
        payload = obj.get("payload")
        if isinstance(payload, dict) and payload.get("id"):
            return f"{provider}:{payload['id']}"
    for _, obj, _ in records:
        value = obj.get("sessionId")
        if value:
            return f"{provider}:{value}"
    digest = hashlib.sha256(b"".join(raw for _, _, raw in records)).hexdigest()
    return f"{provider}:content-{digest[:24]}"


def _evidence(
    provider: Provider,
    source_id: str,
    line: int,
    obj: Mapping[str, object],
    raw: bytes,
) -> EvidenceRef:
    payload = obj.get("payload")
    native = payload.get("id") if isinstance(payload, dict) else obj.get("uuid")
    event_id = str(native or obj.get("id") or "")
    digest = hashlib.sha256(raw).hexdigest()
    if not event_id:
        event_id = f"{source_id}:{line}:{digest[:16]}"
    return EvidenceRef(provider, source_id, line, event_id, digest)


def _with_event_id(evidence: EvidenceRef, event_id: str) -> EvidenceRef:
    """Return the same raw-record reference with a nested native event id."""
    return EvidenceRef(
        evidence.provider,
        evidence.source_id,
        evidence.line,
        event_id or evidence.event_id,
        evidence.record_sha256,
    )


def _stable_claim_id(prefix: str, evidence: EvidenceRef, text: str) -> str:
    raw = f"{prefix}\0{evidence.source_id}\0{evidence.event_id}\0{text}".encode()
    return f"{prefix}-{hashlib.sha256(raw).hexdigest()[:20]}"


def _digest_metadata(label: str, value: object) -> tuple[tuple[str, str], ...]:
    raw = (
        value.encode()
        if isinstance(value, str)
        else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    )
    return (
        (f"{label}_bytes", str(len(raw))),
        (f"{label}_sha256", hashlib.sha256(raw).hexdigest()),
    )


def _safe_text(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        metadata = dict(_digest_metadata("data_url", match.group(0)))
        return (
            "[data-url "
            f"bytes={metadata['data_url_bytes']} "
            f"sha256={metadata['data_url_sha256']}]"
        )

    return re.sub(r"data:[^\s\"'<>]+", replace, text)


def _add_event(acc: _Accumulator, event: CanonicalEvent) -> None:
    if event.kind == EventKind.ATTACHMENT and event.attachment is not None:
        digest = event.attachment.payload_sha256
        if digest and digest in acc.seen_attachment_sha256:
            return
        if digest:
            acc.seen_attachment_sha256.add(digest)
    key = f"{event.kind}:{event.evidence.event_id}:{event.text}"
    if key in acc.seen_event_ids:
        return
    acc.seen_event_ids.add(key)
    acc.events.append(event)
    if event.kind in {EventKind.USER_MESSAGE, EventKind.FORM_ANSWER}:
        acc.requirements.append(
            RequirementEntry(
                _stable_claim_id("req", event.evidence, event.text),
                event.text,
                event.evidence,
                event.kind,
                bool(_AUTHORITY.search(event.text + " " + str(event.metadata))),
            )
        )
    if event.kind == EventKind.ASSISTANT_MESSAGE and _PROMISE.search(event.text):
        acc.promises.append(
            PromiseEntry(
                _stable_claim_id("promise", event.evidence, event.text),
                event.text,
                event.evidence,
            )
        )
    _add_high_severity_finding(acc, event)


def _add_high_severity_finding(acc: _Accumulator, event: CanonicalEvent) -> None:
    """Retain known high-cost failures even when they occur only once."""
    findings = (
        (
            "credential-launcher",
            _CREDENTIAL_LAUNCHER,
            "Credential/environment launcher failure requires explicit review.",
        ),
        (
            "git-hook-contamination",
            _GIT_HOOK_CONTAMINATION,
            "Git hook/worktree environment contamination requires explicit review.",
        ),
    )
    for category, pattern, statement in findings:
        if category in acc.seen_finding_categories or not pattern.search(event.text):
            continue
        acc.seen_finding_categories.add(category)
        acc.high_severity_findings.append(
            HighSeverityFinding(
                _stable_claim_id(f"risk-{category}", event.evidence, statement),
                category,
                statement,
                event.evidence,
            )
        )


def _text_blocks(content: object) -> Iterable[tuple[str, str]]:
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = str(block.get("type", ""))
        text = block.get("text")
        if isinstance(text, str):
            yield kind, text


def _data_url_bytes(payload: str) -> bytes | None:
    header, separator, encoded = payload.partition(",")
    if not separator:
        return None
    try:
        content = (
            b64decode(encoded, validate=True)
            if header.endswith(";base64")
            else unquote_to_bytes(encoded)
        )
    except Base64Error, ValueError:
        return None
    return content if len(content) <= MAX_ATTACHMENT_BYTES else None


def _local_attachment_bytes(
    path: Path, approved_roots: tuple[Path, ...]
) -> bytes | None:
    try:
        if path.is_symlink():
            return None
        resolved = path.resolve(strict=True)
        if not any(resolved.is_relative_to(root) for root in approved_roots):
            return None
        if resolved.stat().st_size > MAX_ATTACHMENT_BYTES:
            return None
        return resolved.read_bytes()
    except OSError:
        return None


def _attachment_bytes(payload: str, approved_roots: tuple[Path, ...]) -> bytes | None:
    if payload.startswith("data:"):
        return _data_url_bytes(payload)
    parsed = urlparse(payload)
    if parsed.scheme == "file":
        path = Path(unquote(parsed.path))
    elif not parsed.scheme and Path(payload).is_absolute():
        path = Path(payload)
    else:
        return None
    return _local_attachment_bytes(path, approved_roots)


def _attachment(
    block: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> AttachmentMetadata:
    kind = str(block.get("type", "attachment"))
    payload = str(block.get("image_url", block.get("file_url", block.get("path", ""))))
    name_match = re.search(r"(?:name=|path=)[\"\[]?([^\">\]]+)", payload)
    name = name_match.group(1) if name_match else str(block.get("name", kind))
    if Path(payload).is_absolute():
        name = Path(payload).name
    content = _attachment_bytes(payload, acc.approved_attachment_roots)
    verified = content is not None
    if content is None:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: "
            f"attachment bytes unavailable for {name!r}"
        )
        content = b""
    return AttachmentMetadata(
        media_type=kind,
        name=name,
        payload_sha256=hashlib.sha256(content).hexdigest() if verified else "",
        payload_bytes=len(content),
    )


def _metadata_pairs(
    values: Mapping[str, object], names: Iterable[str]
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, json.dumps(values[name], sort_keys=True, ensure_ascii=False))
        for name in names
        if name in values
    )


def _turn_id(values: Mapping[str, object]) -> str:
    direct = values.get("turn_id")
    metadata = values.get("internal_chat_message_metadata_passthrough")
    nested = metadata.get("turn_id") if isinstance(metadata, dict) else ""
    return str(direct or nested or "")


def _add_text_attachment_events(
    text: str, role: str, evidence: EvidenceRef, acc: _Accumulator
) -> None:
    for match in _ATTACHMENT_TAG.finditer(text):
        attachment = {
            "type": match.group("kind").lower(),
            "path": match.group("path"),
        }
        meta = _attachment(attachment, evidence, acc)
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.ATTACHMENT,
                role,
                meta.name,
                evidence,
                attachment=meta,
            ),
        )


def _codex_user_kind(
    text: str,
    evidence: EvidenceRef,
    acc: _Accumulator,
    direct_messages: dict[str, list[EvidenceRef]],
) -> EventKind | None:
    matches = direct_messages.get(text, [])
    if not matches:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: "
            "user-role message lacks direct-user provenance"
        )
        return EventKind.UNVERIFIABLE_USER_MESSAGE
    matches.pop(0)
    if any(
        event.kind == EventKind.USER_MESSAGE and event.text == text
        for event in acc.events
    ):
        return None
    return EventKind.USER_MESSAGE


def _codex_message(
    payload: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
    direct_messages: dict[str, list[EvidenceRef]],
) -> None:
    role = str(payload.get("role", ""))
    if role not in {"user", "assistant"}:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: message role {role!r}"
        )
        return
    content = payload.get("content")
    for block_kind, text in _text_blocks(content):
        if block_kind in {"input_text", "output_text", "text"}:
            kind = EventKind.ASSISTANT_MESSAGE
            if role == "user":
                resolved = _codex_user_kind(text, evidence, acc, direct_messages)
                if resolved is None:
                    continue
                kind = resolved
            _add_event(acc, CanonicalEvent(kind, role, _safe_text(text), evidence))
            _add_text_attachment_events(text, role, evidence, acc)
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        block_kind = str(block.get("type", ""))
        if block_kind in {"input_image", "input_file", "image", "document"}:
            meta = _attachment(block, evidence, acc)
            _add_event(
                acc,
                CanonicalEvent(
                    EventKind.ATTACHMENT,
                    role,
                    meta.name,
                    evidence,
                    attachment=meta,
                ),
            )


def _form_questions(
    payload: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> frozenset[str]:
    arguments = payload.get("arguments")
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("questions"), list):
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: malformed form call"
        )
        return frozenset()
    question_ids: set[str] = set()
    for question in parsed["questions"]:
        if not isinstance(question, dict):
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: malformed question"
            )
            continue
        text = str(question.get("question", ""))
        question_id = str(question.get("id", ""))
        if not question_id or question_id in question_ids:
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: duplicate or empty question id"
            )
        question_ids.add(question_id)
        metadata = _metadata_pairs(question, ("id", "header"))
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.FORM_QUESTION, "assistant", text, evidence, metadata
            ),
        )
    return frozenset(question_ids)


def _form_answers(
    payload: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> frozenset[str] | None:
    output = payload.get("output")
    try:
        parsed = json.loads(output) if isinstance(output, str) else output
    except json.JSONDecodeError:
        parsed = None
    answers = parsed.get("answers") if isinstance(parsed, dict) else None
    if not isinstance(answers, dict):
        return None
    answer_ids: set[str] = set()
    for question_id, value in answers.items():
        answer_ids.add(str(question_id))
        answer_values = value.get("answers") if isinstance(value, dict) else None
        if not isinstance(answer_values, list):
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: malformed answer"
            )
            continue
        for answer in answer_values:
            if not isinstance(answer, str):
                continue
            metadata = (("question_id", str(question_id)),)
            _add_event(
                acc,
                CanonicalEvent(
                    EventKind.FORM_ANSWER,
                    "user",
                    _safe_text(answer),
                    evidence,
                    metadata,
                ),
            )
    return frozenset(answer_ids)


def _codex_form_call(
    payload: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
    form_schema_status: str,
) -> None:
    call_id = str(payload.get("call_id", ""))
    question_ids = _form_questions(payload, evidence, acc)
    if not call_id or call_id in acc.form_calls:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: duplicate or empty form call id"
        )
    else:
        acc.form_calls[call_id] = (evidence, _turn_id(payload), question_ids)
    if form_schema_status == "needs-probe":
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: "
            "request_user_input shape needs an alpha runtime probe"
        )


def _codex_tool_event(
    payload: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
    *,
    result: bool,
) -> None:
    """Retain call/result structure while digesting opaque arguments and output."""
    call_id = str(payload.get("call_id", payload.get("id", "")))
    name = str(payload.get("name", payload.get("tool", "")))
    opaque = payload.get("output" if result else "arguments")
    metadata = _metadata_pairs(payload, ("call_id", "name"))
    if opaque is not None:
        metadata += _digest_metadata("output" if result else "arguments", opaque)
    kind = EventKind.TOOL_RESULT if result else EventKind.TOOL_CALL
    text = f"tool {'result' if result else 'call'} {name or call_id or 'unknown'}"
    _add_event(acc, CanonicalEvent(kind, "tool", text, evidence, metadata))
    if call_id:
        if result:
            if call_id in acc.tool_results:
                acc.omissions.append(
                    f"{evidence.source_id}:{evidence.line}: duplicate tool result "
                    f"{call_id}"
                )
            acc.tool_results[call_id] = _turn_id(payload)
        else:
            if call_id in acc.tool_calls:
                acc.omissions.append(
                    f"{evidence.source_id}:{evidence.line}: duplicate tool call "
                    f"{call_id}"
                )
            acc.tool_calls[call_id] = (evidence, _turn_id(payload))


def _codex_form_result(
    payload: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> None:
    _codex_tool_event(payload, evidence, acc, result=True)
    answer_ids = _form_answers(payload, evidence, acc)
    if answer_ids is None:
        return
    call_id = str(payload.get("call_id", ""))
    if not call_id or call_id in acc.form_results:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: duplicate or empty form result id"
        )
    else:
        acc.form_results[call_id] = (_turn_id(payload), answer_ids)


def _codex_agent_message(
    payload: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> None:
    for _, text in _text_blocks(payload.get("content")):
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.AGENT_MESSAGE, "agent", _safe_text(text), evidence
            ),
        )
    encrypted = payload.get("encrypted_content")
    if encrypted:
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.OPAQUE_PAYLOAD,
                "agent",
                "opaque encrypted agent payload",
                evidence,
                _digest_metadata("encrypted_content", encrypted),
            ),
        )


def _codex_response(
    payload: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
    direct_messages: dict[str, list[EvidenceRef]],
    form_schema_status: str,
) -> None:
    response_type = str(payload.get("type", ""))
    if response_type == "message":
        _codex_message(payload, evidence, acc, direct_messages)
    elif (
        response_type == "function_call" and payload.get("name") == "request_user_input"
    ):
        _codex_form_call(payload, evidence, acc, form_schema_status)
        _codex_tool_event(payload, evidence, acc, result=False)
    elif response_type == "function_call_output":
        _codex_form_result(payload, evidence, acc)
    elif response_type in {"function_call", "custom_tool_call"}:
        _codex_tool_event(payload, evidence, acc, result=False)
    elif response_type == "custom_tool_call_output":
        _codex_tool_event(payload, evidence, acc, result=True)
    elif response_type == "agent_message":
        _codex_agent_message(payload, evidence, acc)
    elif response_type == "compaction":
        encrypted = payload.get("encrypted_content")
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.OPAQUE_PAYLOAD,
                "harness",
                "opaque replacement compaction",
                evidence,
                _digest_metadata("encrypted_content", encrypted),
            ),
        )
    elif response_type not in {
        "reasoning",
        "function_call",
    }:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: response_item {response_type!r}"
        )


def _codex_lineage(payload: Mapping[str, object], source_id: str) -> SessionLineage:
    source = payload.get("source")
    subagent = source.get("subagent") if isinstance(source, dict) else None
    spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
    spawn = spawn if isinstance(spawn, dict) else {}
    return SessionLineage(
        Provider.CODEX,
        source_id,
        str(payload.get("session_id", payload.get("id", ""))),
        str(payload.get("parent_thread_id", payload.get("forked_from_id", ""))),
        str(payload.get("agent_path", spawn.get("agent_path", ""))),
        str(payload.get("agent_role", spawn.get("agent_role", ""))),
        history_base_ordinal=str(payload.get("subagent_history_start_ordinal", "")),
    )


def _direct_message_evidence(
    records: list[tuple[int, dict[str, object], bytes]], source_id: str
) -> dict[str, list[EvidenceRef]]:
    """Index event-message twins, the positive direct-user provenance signal."""
    indexed: dict[str, list[EvidenceRef]] = {}
    for line, obj, raw in records:
        payload = obj.get("payload")
        values = payload if isinstance(payload, dict) else {}
        if obj.get("type") != "event_msg":
            continue
        messages: list[str] = []
        if values.get("type") == "user_message" and isinstance(
            values.get("message"), str
        ):
            messages.append(str(values["message"]))
        item = values.get("item")
        if (
            values.get("type") == "item_completed"
            and isinstance(item, dict)
            and item.get("type") == "UserMessage"
        ):
            messages.extend(text for _, text in _text_blocks(item.get("content")))
        for message in messages:
            indexed.setdefault(message, []).append(
                _evidence(Provider.CODEX, source_id, line, obj, raw)
            )
    return indexed


def _codex_cli_version(
    records: list[tuple[int, dict[str, object], bytes]],
) -> str:
    for _, obj, _ in records:
        payload = obj.get("payload")
        if obj.get("type") == "session_meta" and isinstance(payload, dict):
            return str(payload.get("cli_version", ""))
    return ""


def _codex_compaction(
    values: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
    direct_messages: dict[str, list[EvidenceRef]],
    form_schema_status: str,
) -> tuple[str, int | None]:
    metadata = _metadata_pairs(
        values,
        (
            "window_id",
            "previous_window_id",
            "window_number",
            "comp_hash",
        ),
    )
    message = str(values.get("message", ""))
    history = values.get("replacement_history")
    metadata += _digest_metadata("message", message)
    metadata += _digest_metadata("replacement_history", history)
    history_count = len(history) if isinstance(history, list) else 0
    metadata += (("replacement_history_count", str(history_count)),)
    _add_event(
        acc,
        CanonicalEvent(
            EventKind.COMPACTION,
            "harness",
            f"compaction window {values.get('window_number', '')}",
            evidence,
            metadata,
        ),
    )
    if isinstance(history, list):
        allowed = {"message", "agent_message", "compaction"}
        ids = [str(item.get("id", "")) for item in history if isinstance(item, dict)]
        structurally_complete = (
            bool(history)
            and len(ids) == len(history)
            and all(ids)
            and len(ids) == len(set(ids))
            and all(
                isinstance(item, dict) and item.get("type") in allowed
                for item in history
            )
        )
        if not structurally_complete:
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: replacement history is not "
                "an atomic supported snapshot"
            )
            return "", None
        for nested in history:
            if not isinstance(nested, dict):
                continue
            nested_id = str(nested.get("id", ""))
            if any(event.evidence.event_id == nested_id for event in acc.events):
                continue
            nested_evidence = _with_event_id(evidence, nested_id)
            _codex_response(
                nested,
                nested_evidence,
                acc,
                direct_messages,
                form_schema_status,
            )
    number = values.get("window_number")
    return str(values.get("window_id", "")), number if isinstance(number, int) else None


def _validate_compaction_chain(
    values: Mapping[str, object],
    previous: tuple[str, int | None],
    number: int | None,
) -> list[str]:
    previous_window, previous_number = previous
    errors: list[str] = []
    prior = str(values.get("previous_window_id", ""))
    if previous_window and prior != previous_window:
        errors.append("broken compaction window chain")
    if previous_number is not None and number is not None and number <= previous_number:
        errors.append("non-monotone compaction window")
    return errors


def _codex_terminal_event(
    values: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> None:
    event_type = str(values.get("type", ""))
    if event_type not in {
        "task_complete",
        "task_failed",
        "turn_aborted",
        "turn_complete",
    }:
        return
    metadata = _metadata_pairs(values, ("type", "turn_id", "status", "reason"))
    _add_event(
        acc,
        CanonicalEvent(
            EventKind.TERMINAL_STATE,
            "harness",
            f"Codex terminal event {event_type}",
            evidence,
            metadata,
        ),
    )


def _codex_event(
    values: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> None:
    event_type = str(values.get("type", ""))
    if event_type not in _CODEX_EVENT_TYPES:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: unknown Codex event {event_type!r}"
        )
        return
    if event_type == "user_message":
        return
    if event_type != "item_completed":
        _codex_terminal_event(values, evidence, acc)
        return
    item = values.get("item")
    if not isinstance(item, dict):
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: malformed completed item"
        )
        return
    item_type = str(item.get("type", ""))
    if item_type not in _CODEX_ITEM_TYPES:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: unknown completed item "
            f"{item_type!r}"
        )
        return
    if item_type == "UserMessage":
        for _, text in _text_blocks(item.get("content")):
            if any(
                event.kind == EventKind.USER_MESSAGE and event.text == text
                for event in acc.events
            ):
                continue
            _add_event(
                acc,
                CanonicalEvent(
                    EventKind.USER_MESSAGE,
                    "user",
                    _safe_text(text),
                    evidence,
                    (("turn_id", _turn_id(values)),),
                ),
            )


def _codex_record(
    record_type: str,
    values: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
    context: _CodexParseContext,
) -> tuple[str, int | None] | None:
    if record_type == "session_meta":
        acc.lineage.append(_codex_lineage(values, evidence.source_id))
    elif record_type == "turn_context":
        metadata = _metadata_pairs(
            values,
            (
                "approval_policy",
                "sandbox_policy",
                "permission_profile",
                "workspace_roots",
            ),
        )
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.AUTHORITY_CONTEXT,
                "harness",
                "turn authority context",
                evidence,
                metadata,
            ),
        )
    elif record_type == "response_item":
        _codex_response(
            values,
            evidence,
            acc,
            context.direct_messages,
            context.form_schema_status,
        )
    elif record_type == "compacted":
        return _codex_compaction(
            values,
            evidence,
            acc,
            context.direct_messages,
            context.form_schema_status,
        )
    elif record_type == "event_msg":
        _codex_event(values, evidence, acc)
    return None


def _advance_turn_state(
    values: Mapping[str, object],
    source_id: str,
    line: int,
    states: dict[str, str],
    acc: _Accumulator,
) -> None:
    event_type = str(values.get("type", ""))
    turn_id = _turn_id(values)
    if event_type == "task_started":
        if not turn_id or turn_id in states:
            acc.omissions.append(f"{source_id}:{line}: duplicate or empty task start")
        else:
            states[turn_id] = "started"
    elif event_type == "task_complete":
        if not turn_id or states.get(turn_id) != "started":
            acc.omissions.append(
                f"{source_id}:{line}: task complete without unique start"
            )
        else:
            states[turn_id] = "complete"


def _parse_codex(
    records: list[tuple[int, dict[str, object], bytes]],
    source_id: str,
    acc: _Accumulator,
) -> None:
    known = {
        "session_meta",
        "turn_context",
        "response_item",
        "compacted",
        "event_msg",
        "world_state",
        "inter_agent_communication_metadata",
    }
    direct_messages = _direct_message_evidence(records, source_id)
    cli_version = _codex_cli_version(records)
    form_schema_status = "needs-probe" if "alpha" in cli_version else "confirmed"
    context = _CodexParseContext(direct_messages, form_schema_status)
    previous_window = ""
    previous_number: int | None = None
    turn_states: dict[str, str] = {}
    for line, obj, raw in records:
        record_type = str(obj.get("type", ""))
        evidence = _evidence(Provider.CODEX, source_id, line, obj, raw)
        payload = obj.get("payload")
        values = payload if isinstance(payload, dict) else {}
        if record_type == "event_msg":
            _advance_turn_state(values, source_id, line, turn_states, acc)
        result = _codex_record(
            record_type,
            values,
            evidence,
            acc,
            context,
        )
        if result is not None:
            window, number = result
            for error in _validate_compaction_chain(
                values, (previous_window, previous_number), number
            ):
                acc.omissions.append(f"{source_id}:{line}: {error}")
            previous_window = window or previous_window
            previous_number = number if number is not None else previous_number
        if record_type not in known:
            acc.omissions.append(
                f"{source_id}:{line}: unknown Codex record {record_type!r}"
            )
    for turn_id, state in sorted(turn_states.items()):
        if state != "complete":
            acc.omissions.append(f"{source_id}: open turn {turn_id}")
    for text, evidence_rows in direct_messages.items():
        for evidence in evidence_rows:
            _add_event(
                acc,
                CanonicalEvent(
                    EventKind.USER_MESSAGE, "user", _safe_text(text), evidence
                ),
            )


def _claude_form_result(obj: Mapping[str, object]) -> dict[str, object] | None:
    result = obj.get("toolUseResult")
    return (
        result
        if isinstance(result, dict) and isinstance(result.get("answers"), dict)
        else None
    )


def _claude_content(
    content: object,
    *,
    record_type: str,
    evidence: EvidenceRef,
    acc: _Accumulator,
) -> None:
    """Normalize the message-content half of one Claude record."""
    event_kind = (
        EventKind.ASSISTANT_MESSAGE
        if record_type == "assistant"
        else EventKind.USER_MESSAGE
    )
    for _, text in _text_blocks(content):
        _add_event(
            acc,
            CanonicalEvent(event_kind, record_type, _safe_text(text), evidence),
        )
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            synthetic = {
                "call_id": block.get("id", ""),
                "name": block.get("name", ""),
                "arguments": block.get("input", {}),
            }
            _codex_tool_event(synthetic, evidence, acc, result=False)
            if block.get("name") == "AskUserQuestion":
                question = {"arguments": json.dumps(block.get("input", {}))}
                _form_questions(question, evidence, acc)
        elif block.get("type") == "tool_result":
            synthetic = {
                "call_id": block.get("tool_use_id", ""),
                "output": block.get("content", ""),
            }
            _codex_tool_event(synthetic, evidence, acc, result=True)
        elif block.get("type") in {"image", "document", "file"}:
            meta = _attachment(block, evidence, acc)
            _add_event(
                acc,
                CanonicalEvent(
                    EventKind.ATTACHMENT,
                    record_type,
                    meta.name,
                    evidence,
                    attachment=meta,
                ),
            )


def _parse_claude(
    records: list[tuple[int, dict[str, object], bytes]],
    source_id: str,
    acc: _Accumulator,
    path: Path,
) -> None:
    known = {
        "assistant",
        "user",
        "system",
        "summary",
        "progress",
        "file-history-snapshot",
        "queue-operation",
        "custom-title",
        "last-prompt",
        "agent-setting",
        "mode",
        "permission-mode",
        "attachment",
    }
    session_id = ""
    for line, obj, raw in records:
        record_type = str(obj.get("type", ""))
        session_id = str(obj.get("sessionId", session_id))
        evidence = _evidence(Provider.CLAUDE, source_id, line, obj, raw)
        message = obj.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if record_type in {"assistant", "user"}:
            _claude_content(
                content,
                record_type=record_type,
                evidence=evidence,
                acc=acc,
            )
            result = _claude_form_result(obj)
            if result is not None:
                synthetic = {"output": json.dumps({"answers": result["answers"]})}
                _form_answers(synthetic, evidence, acc)
            if isinstance(message, dict) and message.get("stop_reason"):
                metadata = _metadata_pairs(message, ("stop_reason", "stop_sequence"))
                _add_event(
                    acc,
                    CanonicalEvent(
                        EventKind.TERMINAL_STATE,
                        "harness",
                        f"Claude stop reason {message['stop_reason']}",
                        evidence,
                        metadata,
                    ),
                )
        elif record_type == "attachment":
            attachment = obj.get("attachment")
            _add_event(
                acc,
                CanonicalEvent(
                    EventKind.OPAQUE_PAYLOAD,
                    "harness",
                    "Claude structural attachment",
                    evidence,
                    _digest_metadata("attachment", attachment),
                ),
            )
        elif record_type not in known:
            acc.omissions.append(
                f"{source_id}:{line}: unknown Claude record {record_type!r}"
            )
    acc.lineage.append(
        SessionLineage(
            Provider.CLAUDE,
            source_id,
            session_id,
            "",
            "subagent" if "subagents" in path.parts else "",
            "",
        )
    )


def _has_open_turn(records: list[tuple[int, dict[str, object], bytes]]) -> bool:
    open_turns: set[str] = set()
    for _, obj, _ in records:
        if obj.get("type") != "event_msg":
            continue
        payload = obj.get("payload")
        values = payload if isinstance(payload, dict) else {}
        turn_id = str(values.get("turn_id", ""))
        if values.get("type") == "task_started" and turn_id:
            open_turns.add(turn_id)
        elif (
            values.get("type")
            in {
                "task_complete",
                "task_failed",
                "turn_aborted",
                "turn_complete",
            }
            and turn_id
        ):
            open_turns.discard(turn_id)
    return bool(open_turns)


def _read_records(path: Path, source: TranscriptSource, acc: _Accumulator) -> None:
    try:
        before_stat = path.stat()
        data = path.read_bytes()
        after_stat = path.stat()
    except OSError as exc:
        acc.omissions.append(f"{source.provider}:{path}: unreadable: {exc}")
        return
    records: list[tuple[int, dict[str, object], bytes]] = []
    for line, raw in enumerate(data.splitlines(keepends=True), start=1):
        obj = _json_object(raw)
        if obj is None:
            acc.omissions.append(
                f"{source.provider}:{path.name}:{line}: malformed JSON"
            )
            continue
        records.append((line, obj, raw))
    source_id = _source_id(source.provider, records)
    before = len(acc.events)
    if source.provider == Provider.CODEX:
        _parse_codex(records, source_id, acc)
    else:
        _parse_claude(records, source_id, acc, path)
    if (
        before_stat.st_size != after_stat.st_size
        or before_stat.st_mtime_ns != after_stat.st_mtime_ns
    ):
        acc.omissions.append(f"{source_id}: source changed while being read")
    last_event_id = acc.events[-1].evidence.event_id if len(acc.events) > before else ""
    final_obj = records[-1][1] if records else {}
    acc.cutoffs.append(
        SourceCutoff(
            source.provider,
            source_id,
            str(path.resolve()),
            len(data),
            len(data.splitlines()),
            hashlib.sha256(data).hexdigest(),
            last_event_id,
            str(final_obj.get("ordinal", "")),
            str(final_obj.get("timestamp", "")),
            _has_open_turn(records),
        )
    )


def _resolve_inherited_prefix(acc: _Accumulator) -> None:
    """Authenticate child prefix messages through their native parent lineage."""
    by_session = {item.session_id: item for item in acc.lineage if not item.parent_id}
    direct_by_source: dict[str, list[CanonicalEvent]] = {}
    for event in acc.events:
        if event.kind == EventKind.USER_MESSAGE:
            direct_by_source.setdefault(event.evidence.source_id, []).append(event)
    replacement_events: list[CanonicalEvent] = []
    replacement_lineage: list[SessionLineage] = []
    resolved_omissions: set[str] = set()
    for lineage in acc.lineage:
        parent = by_session.get(lineage.parent_id)
        parent_events = direct_by_source.get(parent.source_id, []) if parent else []
        if lineage.parent_id and not lineage.history_base_ordinal:
            acc.omissions.append(
                f"{lineage.source_id}: child lineage lacks history_base ordinal"
            )
        if lineage.parent_id and parent is None:
            acc.omissions.append(
                f"{lineage.source_id}: lineage parent {lineage.parent_id!r} unavailable"
            )
        inherited = 0
        for event in acc.events:
            if (
                event.evidence.source_id == lineage.source_id
                and event.kind == EventKind.UNVERIFIABLE_USER_MESSAGE
                and any(
                    parent_event.text == event.text for parent_event in parent_events
                )
            ):
                inherited += 1
                replacement_events.append(
                    replace(event, kind=EventKind.INHERITED_USER_MESSAGE)
                )
                resolved_omissions.add(
                    f"{event.evidence.source_id}:{event.evidence.line}: "
                    "user-role message lacks direct-user provenance"
                )
            elif event.evidence.source_id == lineage.source_id:
                replacement_events.append(event)
        prefix = json.dumps(
            [(event.evidence.event_id, event.text) for event in parent_events],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        replacement_lineage.append(
            replace(
                lineage,
                inherited_prefix_sha256=(
                    hashlib.sha256(prefix).hexdigest() if parent_events else ""
                ),
                inherited_event_count=inherited,
            )
        )
    if resolved_omissions:
        events_by_key = {
            (event.evidence.source_id, event.evidence.event_id, event.text): event
            for event in replacement_events
        }
        acc.events = [
            events_by_key.get(
                (event.evidence.source_id, event.evidence.event_id, event.text), event
            )
            for event in acc.events
        ]
        acc.omissions = [
            item for item in acc.omissions if item not in resolved_omissions
        ]
    acc.lineage = replacement_lineage


def parse_transcripts(
    sources: Iterable[TranscriptSource],
    *,
    recorded_cwd: str = "",
    dispositions: Iterable[PreventionDisposition] = (),
    approved_attachment_roots: Iterable[Path] = (),
) -> RequirementCoverage:
    """Parse provider-qualified sources into one deterministic coverage ledger."""
    source_list = sorted(sources, key=lambda item: (item.provider, str(item.path)))
    roots = tuple(
        sorted(
            {
                *(path.expanduser().resolve() for path in approved_attachment_roots),
                *(source.path.parent.resolve() for source in source_list),
            },
            key=str,
        )
    )
    acc = _Accumulator(approved_attachment_roots=roots)
    for source in source_list:
        _read_records(source.path, source, acc)
    _resolve_inherited_prefix(acc)
    for call_id, call in sorted(acc.form_calls.items()):
        evidence, turn_id, question_ids = call
        result = acc.form_results.get(call_id)
        if result is None:
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: missing form result {call_id}"
            )
        elif result != (turn_id, question_ids):
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: form result identity mismatch "
                f"{call_id}"
            )
    for call_id, call in sorted(acc.tool_calls.items()):
        evidence, turn_id = call
        result_turn = acc.tool_results.get(call_id)
        if result_turn is None:
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: missing tool result {call_id}"
            )
        elif result_turn != turn_id:
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: tool result turn mismatch "
                f"{call_id}"
            )
    return RequirementCoverage(
        tuple(acc.events),
        tuple(acc.requirements),
        tuple(acc.promises),
        tuple(acc.high_severity_findings),
        tuple(dispositions),
        tuple(acc.lineage),
        tuple(acc.cutoffs),
        recorded_cwd,
        tuple(acc.omissions),
    )


def _validated_source_root(source_repo_root: Path) -> tuple[Path | None, str]:
    try:
        resolved = source_repo_root.expanduser().resolve(strict=True)
    except OSError as exc:
        return None, f"source repository root is unavailable: {exc}"
    if not resolved.is_dir() or not (resolved / ".git").exists():
        return None, f"source repository root is not a Git checkout: {resolved}"
    return resolved, ""


def build_requirement_coverage(
    source_repo_root: Path,
    *,
    codex_base: Path | None = None,
    claude_base: Path | None = None,
    dispositions: Iterable[PreventionDisposition] = (),
    selection: CoverageSelection = DEFAULT_COVERAGE_SELECTION,
) -> RequirementCoverage:
    """Discover transcripts whose recorded cwd is the explicitly audited root."""
    certification = (
        SelectionCertification.EXPLICIT_SESSION_ID
        if selection.session_id
        else (
            SelectionCertification.UNCERTIFIED_ACTIVITY_FALLBACK
            if selection.require_active_identity
            else SelectionCertification.NOT_REQUESTED
        )
    )
    repo_root, error = _validated_source_root(source_repo_root)
    if repo_root is None:
        return RequirementCoverage(
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            str(source_repo_root),
            (error,),
            certification,
            selection.session_id or "",
        )
    sources = discover_sources(
        repo_root,
        limit=selection.limit,
        codex_base=codex_base,
        claude_base=claude_base,
        session_id=selection.session_id,
    )
    if not sources:
        return RequirementCoverage(
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            str(repo_root),
            (f"no transcripts matched recorded cwd {repo_root}",),
            certification,
            selection.session_id or "",
        )
    coverage = parse_transcripts(
        sources, recorded_cwd=str(repo_root), dispositions=dispositions
    )
    coverage = replace(
        coverage,
        selection_certification=certification,
        selected_session_id=selection.session_id or "",
    )
    if selection.require_active_identity and not selection.session_id:
        return replace(
            coverage,
            omissions=(
                *coverage.omissions,
                _UNCERTIFIED_ACTIVITY,
            ),
        )
    return coverage


def _verified_artifact(
    spec: object, *, repo_root: Path, label: str
) -> tuple[Path, dict[str, object] | None]:
    if not isinstance(spec, dict):
        message = f"{label} must be a path/sha256 object"
        raise TypeError(message)
    raw_path = str(spec.get("path", ""))
    expected = str(spec.get("sha256", ""))
    if not raw_path or not re.fullmatch(r"[0-9a-f]{64}", expected):
        message = f"{label} lacks a valid path and sha256"
        raise ValueError(message)
    candidate = Path(raw_path)
    candidate = candidate if candidate.is_absolute() else repo_root / candidate
    if candidate.is_symlink():
        message = f"{label} may not be a symlink"
        raise ValueError(message)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repo_root)
    except (OSError, ValueError) as exc:
        message = f"{label} is outside the approved repository root"
        raise ValueError(message) from exc
    if not resolved.is_file():
        message = f"{label} is not a regular file"
        raise ValueError(message)
    data = resolved.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        message = f"{label} sha256 does not match persisted bytes"
        raise ValueError(message)
    parsed = _json_object(data)
    return resolved, parsed


def _attested_invocation(
    payload: dict[str, object],
    *,
    attestation: ReceiptAttestation,
    role: str,
) -> bool:
    argv = payload.get("argv")
    test_signed = payload.get("test_signed") is True
    return (
        payload.get("schema") == "session-review.runner-attestation.v1"
        and payload.get("status") == "ATTESTED"
        and payload.get("role") == role
        and payload.get("runner") == "mise-session-review-gate"
        and payload.get("run_id") == attestation.run_id
        and payload.get("nonce") == attestation.nonce
        and isinstance(argv, list)
        and bool(argv)
        and all(isinstance(item, str) and item for item in argv)
        and payload.get("rc") == 0
        and bool(payload.get("started_at"))
        and bool(payload.get("finished_at"))
        and bool(re.fullmatch(r"[0-9a-f]{64}", str(payload.get("artifact_sha256", ""))))
        and (not test_signed or attestation.allow_test_signed)
    )


def _attested_command_receipt(
    spec: object,
    *,
    repo_root: Path,
    role: str,
    attestation: ReceiptAttestation,
) -> Path:
    path, payload = _verified_artifact(spec, repo_root=repo_root, label=role)
    if payload is None:
        message = f"{role} is not a JSON receipt"
        raise ValueError(message)
    if not _attested_invocation(payload, attestation=attestation, role=role):
        message = f"{role} receipt is not trusted-runner ATTESTED"
        raise ValueError(message)
    return path


def _attested_issue_receipt(
    spec: object, *, repo_root: Path, attestation: ReceiptAttestation
) -> Path:
    path, payload = _verified_artifact(spec, repo_root=repo_root, label="issue_receipt")
    if payload is None:
        message = "issue receipt is not JSON"
        raise ValueError(message)
    issue_id = payload.get("issue_id")
    argv = payload.get("argv")
    valid = (
        _attested_invocation(payload, attestation=attestation, role="github_readback")
        and str(payload.get("api_url", "")).startswith("https://api.github.com/repos/")
        and str(payload.get("html_url", "")).startswith("https://github.com/")
        and issue_id not in {None, ""}
        and bool(re.fullmatch(r"[0-9a-f]{64}", str(payload.get("body_sha256", ""))))
        and isinstance(argv, list)
        and argv[:4] == ["fnox", "exec", "--", "gh"]
        and "api" in argv[4:]
        and str(payload.get("api_url")) in argv
    )
    if not valid:
        message = "issue receipt is not live fnox/gh ATTESTED"
        raise ValueError(message)
    return path


def load_dispositions(
    path: Path,
    *,
    repo_root: Path,
    run_id: str = "",
    attestation: ReceiptAttestation | None = None,
) -> tuple[PreventionDisposition, ...]:
    """Load only same-invocation trusted-runner attestations."""
    approved_root, error = _validated_source_root(repo_root)
    if approved_root is None:
        raise ValueError(error)
    if attestation is None:
        if not run_id:
            message = "receipt attestation run-id is required"
            raise ValueError(message)
        context = session_gate.load_context(approved_root, run_id)
        attestation = ReceiptAttestation(run_id, str(context["nonce"]))
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        message = "dispositions must be a JSON array"
        raise TypeError(message)
    rows: list[PreventionDisposition] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            message = f"disposition {index} must be an object"
            raise TypeError(message)
        finding_id = str(item.get("finding_id", ""))
        carrier, _ = _verified_artifact(
            item.get("carrier"), repo_root=approved_root, label="carrier"
        )
        mutation = _attested_command_receipt(
            item.get("mutation_receipt"),
            repo_root=approved_root,
            role="mutation",
            attestation=attestation,
        )
        gate = _attested_command_receipt(
            item.get("gate_receipt"),
            repo_root=approved_root,
            role="gate",
            attestation=attestation,
        )
        issue = _attested_issue_receipt(
            item.get("issue_receipt"),
            repo_root=approved_root,
            attestation=attestation,
        )
        row = PreventionDisposition(
            finding_id=finding_id,
            carrier=str(carrier),
            mutation_evidence=str(mutation),
            gate_evidence=str(gate),
            issue_receipt=str(issue),
            attested=True,
        )
        if not row.audit_evidence_complete:
            message = f"disposition {index} is missing prevention evidence"
            raise ValueError(message)
        rows.append(row)
    return tuple(rows)


def disposition_omissions(coverage: RequirementCoverage) -> tuple[str, ...]:
    """Reject confirmed findings without all prevention and tracking receipts."""
    receipts = {item.finding_id: item for item in coverage.dispositions}
    return tuple(
        f"confirmed finding {finding.finding_id} lacks prevention disposition"
        for finding in coverage.high_severity_findings
        if (
            finding.finding_id not in receipts
            or not receipts[finding.finding_id].complete
        )
    )


def advance_iteration(
    coverage: RequirementCoverage,
    *,
    number: int,
    context: IterationContext = DEFAULT_ITERATION_CONTEXT,
    previous_disposition_ids: Iterable[str] = (),
) -> ReviewIteration:
    """Classify progress without pretending Python performed semantic agent work."""
    current = tuple(
        sorted(item.finding_id for item in coverage.dispositions if item.complete)
    )
    previous = frozenset(previous_disposition_ids)
    unresolved = tuple(
        sorted(
            finding.finding_id
            for finding in coverage.high_severity_findings
            if finding.finding_id not in current
        )
    )
    if unresolved:
        action = IterationAction.NEEDS_AGENT_ACTION
    elif frozenset(current) - previous:
        action = IterationAction.PREVENTION_RECORDED
    else:
        action = IterationAction.CONVERGED
    attested = {
        item.finding_id
        for item in coverage.dispositions
        if item.audit_evidence_complete
    }
    return ReviewIteration(
        number,
        coverage.manifest_sha256,
        action,
        current,
        unresolved,
        context.repo_root,
        context.session_id,
        coverage.selection_certification,
        context.max_iterations,
        max(0, context.max_iterations - number),
        context.artifacts,
        receipt_state=tuple(
            FindingReceiptState(
                finding.finding_id,
                finding.finding_id in attested,
                finding.finding_id in attested,
                finding.finding_id in attested,
                finding.finding_id in attested,
            )
            for finding in coverage.high_severity_findings
        ),
    )


def artifact_ref(path: Path, *, kind: str) -> ArtifactRef:
    """Return a content-addressed reference to a persisted iteration artifact."""
    data = path.read_bytes()
    return ArtifactRef(
        kind, str(path.resolve()), len(data), hashlib.sha256(data).hexdigest()
    )


def _table_text(value: str) -> str:
    return command_audit.truncate(value.replace("|", "\\|"), 120)


def _cap_utf8(text: str, limit: int = MAX_RENDER_BYTES) -> str:
    """Apply a hard byte cap without producing invalid UTF-8."""
    raw = text.encode()
    if len(raw) <= limit:
        return text
    notice = b"\n\n[TRUNCATED: use cutoff references and JSON evidence artifact]\n"
    prefix = raw[: limit - len(notice)]
    while True:
        try:
            return prefix.decode() + notice.decode()
        except UnicodeDecodeError:
            prefix = prefix[:-1]


def render_coverage(coverage: RequirementCoverage) -> str:
    """Render a bounded review packet without leaking attachment payloads."""
    out = [
        "# Session requirement and promise ledger",
        "",
        f"Coverage: **{coverage.status.upper()}**. Schema: {coverage.schema_version}. ",
        (
            "Active selection: "
            f"**{coverage.selection_certification.upper()}**"
            f" (`{coverage.selected_session_id or 'none'}`)."
        ),
        f"Cutoff manifest: `{coverage.manifest_sha256}`.",
        f"Recorded cwd: `{coverage.recorded_cwd or 'not supplied'}`.",
        "",
        (
            f"Sources: {len(coverage.cutoffs)} · events: {len(coverage.events)} · "
            f"requirements: {len(coverage.requirements)} · "
            f"promises: {len(coverage.promises)} · "
            f"high-severity findings: {len(coverage.high_severity_findings)}"
        ),
        "",
        (
            "Requirements and promises are **UNREVIEWED evidence**, "
            "not inferred completion. "
        ),
        "Only explicit user evidence can grant authority.",
        "",
        "## Requirements",
        "",
    ]
    if coverage.requirements:
        out += [
            "| id | source | authority-related | statement |",
            "|---|---|---|---|",
            *(
                f"| `{item.requirement_id}` | {item.source_kind} | "
                f"{'yes' if item.authority_relevant else 'no'} | "
                f"{_table_text(item.statement)} |"
                for item in coverage.requirements
            ),
        ]
    else:
        out.append("_No user-authored requirement evidence was parsed._")
    out += ["", "## Promises", ""]
    if coverage.promises:
        out += [
            "| id | status | statement |",
            "|---|---|---|",
            *(
                f"| `{item.promise_id}` | {item.status} | "
                f"{_table_text(item.statement)} |"
                for item in coverage.promises
            ),
        ]
    else:
        out.append("_No explicit promise phrasing was parsed._")
    out += ["", "## High-severity one-offs", ""]
    if coverage.high_severity_findings:
        recorded = {item.finding_id for item in coverage.dispositions}
        out += [
            "| id | category | status | prevention disposition |",
            "|---|---|---|---|",
            *(
                f"| `{item.finding_id}` | {item.category} | {item.status} | "
                f"{'recorded' if item.finding_id in recorded else 'missing'} |"
                for item in coverage.high_severity_findings
            ),
        ]
    else:
        out.append("_No known high-severity one-off signal was parsed._")
    out += ["", "## Lossless source-prefix references", ""]
    out += [
        "| source | bytes | lines | prefix sha256 |",
        "|---|---:|---:|---|",
        *(
            f"| {item.source_id} | {item.byte_count} | {item.line_count} | "
            f"`{item.prefix_sha256}` |"
            for item in coverage.cutoffs
        ),
        "",
        (
            "The bounded report is a summary. These prefix hashes and each claim's "
            "evidence reference point back to the lossless native JSONL bytes."
        ),
    ]
    out += ["", "## Omissions", ""]
    all_omissions = (*coverage.omissions, *disposition_omissions(coverage))
    if all_omissions:
        out.extend(f"- {item}" for item in all_omissions)
    else:
        out.append("_None._")
    out.append("")
    return _cap_utf8("\n".join(out))
