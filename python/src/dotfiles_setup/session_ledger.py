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

from dotfiles_setup import codec, command_audit, session_gate
from dotfiles_setup.session_store import (
    AppendRebuildError,
    CacheStats,
    RunReceipt,
    SessionStore,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

DEFAULT_REQUIREMENT_SESSION_LIMIT = 5
MIN_ATOMIZED_BULLETS = 2
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_RENDER_BYTES = 64 * 1024
_PROMISE = re.compile(
    r"\b(?:I will|I'll|we will|I am going to|I'm going to)\b", re.IGNORECASE
)
_AUTHORITY = re.compile(
    r"authority|approval|permission|publish|commit|push|stage|mutation|write",
    re.IGNORECASE,
)
_ISSUE_TRACKING_REQUEST = re.compile(
    r"(?:create|open|add|update|file|make|persist|track)\b.{0,48}"
    r"\b(?:github )?issues?\b|"
    r"\b(?:github )?issues?\b.{0,48}\b(?:track|persist|miss|forget)|"
    r"(?:do not|don't|dont) forget|\bmiss(?:ed|ing)?\b.{0,48}\bissues?\b",
    re.IGNORECASE,
)
_AGENT_REVIEW_ENVELOPE = re.compile(
    r"^The following is the Codex agent history(?: added since your last approval "
    r"assessment| whose request action you are assessing)",
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
    CONTINUATION_SUMMARY = "continuation_summary"
    WARNING = "warning"
    DIAGNOSTIC = "diagnostic"


class ReviewStatus(StrEnum):
    """Status of a semantic claim; parsing can only produce UNREVIEWED."""

    UNREVIEWED = "unreviewed"
    OPEN = "open"
    SATISFIED = "satisfied"
    WITHDRAWN = "withdrawn"
    CONTRADICTED = "contradicted"


class AuthorityProvenance(StrEnum):
    """Why a claim may (or may not) carry end-user authority."""

    NATIVE_ROOT_USER = "native_root_user"
    PAIRED_FORM_ANSWER = "paired_form_answer"
    IMPORTED_HISTORY = "imported_history"
    NON_AUTHORITATIVE = "non_authoritative"


class RequirementKind(StrEnum):
    """Stable semantic class for one atomized user action item."""

    ACTION = "action"
    DEPENDENCY_OWNERSHIP = "dependency_ownership"
    GRAPHIFY_SDK = "graphify_sdk"


class ClaimContextKind(StrEnum):
    """Safe structural context attached to a claim packet."""

    NONE = "none"
    PAIRED_QUESTION = "paired_question"
    URL_FRAGMENT = "url_fragment"
    PATH_FRAGMENT = "path_fragment"
    COMMAND_FRAGMENT = "command_fragment"


class RootKind(StrEnum):
    """Native transcript role used by selection and authority checks."""

    INTERACTIVE = "interactive"
    EXEC_WORKER = "exec_worker"
    GUARDIAN = "guardian"
    SUBAGENT = "subagent"
    PLUGIN_TASK = "plugin_task"
    IMPORTED = "imported"
    UNKNOWN = "unknown"


class CoverageStatus(StrEnum):
    """Whether every encountered structural record was understood."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class OmissionDisposition(StrEnum):
    """Whether an observed gap blocks parsing or is retained context."""

    PARSER_BLOCKING = "parser_blocking"
    RETAINED_MISSING = "retained_missing"


class OmissionCategory(StrEnum):
    """Stable, deliberately coarse omission categories."""

    SOURCE = "source"
    IDENTITY = "identity"
    RELATIONSHIP = "relationship"
    ATTACHMENT = "attachment"
    SEMANTIC = "semantic"
    UNKNOWN = "unknown"


class OmissionAuthority(StrEnum):
    """The subsystem authoritative for resolving an omission."""

    NATIVE_TRANSCRIPT = "native_transcript"
    PARSER = "parser"
    REVIEWER = "reviewer"


class IterationAction(StrEnum):
    """Next safe action for the bounded self-improvement loop."""

    CONVERGED = "converged"
    PREVENTION_RECORDED = "prevention_recorded"
    NEEDS_AGENT_ACTION = "needs_agent_action"


class SelectionCertification(StrEnum):
    """Whether the caller proved which native task is being reviewed."""

    NOT_REQUESTED = "not_requested"
    EXPLICIT_SESSION_ID = "explicit_session_id"
    EXPLICIT_SESSION_ID_UNRESOLVED = "explicit_session_id_unresolved"
    UNCERTIFIED_ACTIVITY_FALLBACK = "uncertified_activity_fallback"


def _has_typed_ref(value: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        value.startswith(prefix) and bool(value.removeprefix(prefix).strip())
        for prefix in prefixes
    )


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
class AttachmentDependency:
    """Approved-root-relative external file dependency."""

    root_index: int
    relative_path: str
    payload_sha256: str


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
    authority_provenance: AuthorityProvenance = AuthorityProvenance.NATIVE_ROOT_USER
    kind: RequirementKind = RequirementKind.ACTION
    target: str = ""
    timing: str = ""
    scope: str = ""
    prerequisites: tuple[str, ...] = ()
    external_effect: bool = False
    receipt_refs: tuple[str, ...] = ()
    parent_statement_sha256: str = ""
    atom_index: int = 0
    linked_question_id: str = ""
    linked_question_text: str = ""
    linked_question_sha256: str = ""


@dataclass(frozen=True)
class PromiseEntry:
    """An explicit assistant commitment awaiting fulfillment review."""

    promise_id: str
    statement: str
    evidence: EvidenceRef
    status: ReviewStatus = ReviewStatus.UNREVIEWED
    receipt_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticDisposition:
    """Human-reviewed state for one requirement or promise."""

    claim_id: str
    status: ReviewStatus
    rationale: str
    receipt_refs: tuple[str, ...]

    @property
    def persistable(self) -> bool:
        """A reviewed OPEN state needs a durable carrier, not closure proof."""
        common = (
            bool(self.claim_id.strip())
            and bool(self.rationale.strip())
            and bool(self.receipt_refs)
            and all(item.strip() for item in self.receipt_refs)
        )
        if not common:
            return False
        if self.status == ReviewStatus.OPEN:
            return any(
                _has_typed_ref(item, ("issue:", "artifact:"))
                for item in self.receipt_refs
            )
        return self.complete

    @property
    def complete(self) -> bool:
        """A carrier alone is not semantic proof."""
        return (
            bool(self.claim_id.strip())
            and bool(self.rationale.strip())
            and self.status
            in {
                ReviewStatus.SATISFIED,
                ReviewStatus.WITHDRAWN,
                ReviewStatus.CONTRADICTED,
            }
            and bool(self.receipt_refs)
            and all(item.strip() for item in self.receipt_refs)
            and any(
                _has_typed_ref(item, ("test:", "commit:", "artifact:", "user:"))
                for item in self.receipt_refs
            )
        )


@dataclass(frozen=True)
class OmissionCensusEntry:
    """Typed accounting that preserves the original omission as evidence."""

    omission_id: str
    category: OmissionCategory
    authority: OmissionAuthority
    disposition: OmissionDisposition
    statement: str


@dataclass(frozen=True)
class ClaimSegmentEntry:
    """Bounded claim row that cannot disappear behind Markdown truncation."""

    claim_id: str
    claim_kind: str
    provenance: str
    status: ReviewStatus
    evidence: EvidenceRef
    evidence_ref: str
    bounded_statement: str
    statement_sha256: str
    context_kind: ClaimContextKind = ClaimContextKind.NONE
    bounded_context: str = ""
    context_sha256: str = ""
    candidate_receipt_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderCensus:
    """Bounded discovery accounting for one transcript provider."""

    provider: Provider
    expected: bool
    available: bool
    discovered: int
    selected: int
    rejected: int
    archived: int = 0
    imported: int = 0
    malformed: int = 0
    unreadable: int = 0


@dataclass(frozen=True)
class ImportRegistryEntry:
    """Digest identity for imported history retained without duplicate authority."""

    provider: Provider
    source_id: str
    native_id: str
    root_kind: RootKind
    content_sha256: str


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
    unreviewed_requirement_ids: tuple[str, ...] = ()
    issue_candidate_requirement_ids: tuple[str, ...] = ()
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
    unreviewed_promise_ids: tuple[str, ...] = ()
    open_requirement_ids: tuple[str, ...] = ()
    open_promise_ids: tuple[str, ...] = ()

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
    root_kind: RootKind = RootKind.UNKNOWN


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
    codex_session_id: str | None = None
    require_active_identity: bool = False
    rebuild_cache: bool = False


DEFAULT_COVERAGE_SELECTION = CoverageSelection()


@dataclass(frozen=True)
class TranscriptBases:
    """Optional provider roots injected at the filesystem boundary."""

    codex: Path | None = None
    claude: Path | None = None


DEFAULT_TRANSCRIPT_BASES = TranscriptBases()
_UNCERTIFIED_ACTIVITY = (
    "active session identity is unverified; latest activity is only a fallback"
)
_CACHE_POLICY_FINGERPRINT = "session-ledger-global-finalization-v1"


def _bounded_statement(statement: str, limit: int = 1024) -> str:
    raw = statement.encode()
    if len(raw) <= limit:
        return statement
    suffix = " [BOUNDED]"
    prefix = raw[: limit - len(suffix.encode())]
    while True:
        try:
            return prefix.decode() + suffix
        except UnicodeDecodeError:
            prefix = prefix[:-1]


def _safe_context_text(text: str, limit: int = 512) -> str:
    """Bound context after replacing payloads and private absolute paths."""
    sanitized = _safe_text(text)
    sanitized = re.sub(
        r"(?<![\w:])(?:/[\w.@+~ -]+){2,}",
        lambda match: (
            "[absolute-path "
            f"sha256={hashlib.sha256(match.group(0).encode()).hexdigest()}]"
        ),
        sanitized,
    )
    return _bounded_statement(sanitized, limit)


def _safe_question_id(question_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", question_id):
        return question_id
    digest = hashlib.sha256(question_id.encode()).hexdigest()
    return f"question-{digest[:20]}"


def _fragment_context(
    statement: str,
) -> tuple[ClaimContextKind, str, str, tuple[str, ...]]:
    """Describe a fragment structurally without retaining its sensitive value."""
    stripped = statement.strip()
    digest = hashlib.sha256(stripped.encode()).hexdigest()
    if re.fullmatch(r"(?:https?|file)://\S+", stripped, re.IGNORECASE):
        scheme = urlparse(stripped).scheme.lower()
        context = f"url scheme={scheme} sha256={digest}"
        return (
            ClaimContextKind.URL_FRAGMENT,
            context,
            hashlib.sha256(context.encode()).hexdigest(),
            (f"candidate:artifact:url-{digest[:20]}",),
        )
    if Path(stripped).is_absolute():
        suffix = Path(stripped).suffix.lower()
        context = f"absolute path suffix={suffix or 'none'} sha256={digest}"
        return (
            ClaimContextKind.PATH_FRAGMENT,
            context,
            hashlib.sha256(context.encode()).hexdigest(),
            (f"candidate:artifact:path-{digest[:20]}",),
        )
    command = stripped.removeprefix("$ ").split(maxsplit=1)[0] if stripped else ""
    known_commands = {"gh", "git", "mise", "uv"}
    if (
        command
        and re.fullmatch(r"[A-Za-z0-9_.+-]+", command)
        and (stripped.startswith("$ ") or command in known_commands)
    ):
        safe_command = command if command in known_commands else "other"
        context = f"command executable={safe_command} sha256={digest}"
        return (
            ClaimContextKind.COMMAND_FRAGMENT,
            context,
            hashlib.sha256(context.encode()).hexdigest(),
            (f"candidate:test:command-{digest[:20]}",),
        )
    return ClaimContextKind.NONE, "", "", ()


def _requirement_context(
    item: RequirementEntry,
) -> tuple[ClaimContextKind, str, str, tuple[str, ...]]:
    fragment_kind, fragment, fragment_sha256, candidates = _fragment_context(
        item.statement
    )
    if item.linked_question_text:
        context = (
            f"question id={item.linked_question_id} text={item.linked_question_text}"
        )
        bounded_context = _bounded_statement(context, 768)
        return (
            ClaimContextKind.PAIRED_QUESTION,
            bounded_context,
            hashlib.sha256(bounded_context.encode()).hexdigest(),
            candidates,
        )
    return fragment_kind, fragment, fragment_sha256, candidates


def _bounded_claim_statement(statement: str) -> str:
    kind, _, _, _ = _fragment_context(statement)
    if kind != ClaimContextKind.NONE:
        digest = hashlib.sha256(statement.strip().encode()).hexdigest()
        return f"[{kind} sha256={digest}]"
    return _safe_context_text(statement, 1024)


def _evidence_ref_text(evidence: EvidenceRef) -> str:
    return (
        f"{evidence.provider}:{evidence.source_id}:{evidence.line}:"
        f"{evidence.event_id}:{evidence.record_sha256}"
    )


def _bounded_json(payload: object, label: str) -> str:
    rendered = json.dumps(
        payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False
    )
    if len(rendered.encode()) > MAX_RENDER_BYTES:
        message = f"{label} exceeds the hard output cap"
        raise ValueError(message)
    return rendered


def _bounded_json_chunks(
    rows: list[dict[str, object]],
    *,
    common: Mapping[str, object],
    member: str,
) -> list[list[dict[str, object]]]:
    chunks: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    for row in rows:
        candidate = [*current, row]
        probe = {
            **common,
            "segment_index": 999999,
            "segment_count": 999999,
            member: candidate,
        }
        rendered = json.dumps(
            probe, separators=(",", ":"), sort_keys=True, ensure_ascii=False
        )
        if len(rendered.encode()) > MAX_RENDER_BYTES:
            if not current:
                message = f"one {member} entry exceeds the hard output cap"
                raise ValueError(message)
            chunks.append(current)
            current = [row]
        else:
            current = candidate
    if current or not chunks:
        chunks.append(current)
    return chunks


def _classify_omission(statement: str) -> OmissionCensusEntry:
    """Classify conservatively; an unrecognized statement always blocks."""
    lowered = statement.lower()
    category = OmissionCategory.UNKNOWN
    authority = OmissionAuthority.PARSER
    disposition = OmissionDisposition.PARSER_BLOCKING
    if any(token in lowered for token in ("unreadable", "source ", "transcript")):
        category = OmissionCategory.SOURCE
        authority = OmissionAuthority.NATIVE_TRANSCRIPT
        if "unreadable" in lowered or "no transcripts" in lowered:
            disposition = OmissionDisposition.RETAINED_MISSING
    elif any(token in lowered for token in ("identity", "session", "provenance")):
        category = OmissionCategory.IDENTITY
        authority = OmissionAuthority.NATIVE_TRANSCRIPT
    elif any(
        token in lowered
        for token in ("form result", "tool result", "turn", "lineage", "parent")
    ):
        category = OmissionCategory.RELATIONSHIP
        authority = OmissionAuthority.NATIVE_TRANSCRIPT
    elif "attachment" in lowered:
        category = OmissionCategory.ATTACHMENT
        authority = OmissionAuthority.NATIVE_TRANSCRIPT
        if "bytes unavailable" in lowered:
            disposition = OmissionDisposition.RETAINED_MISSING
    elif "semantic disposition" in lowered:
        category = OmissionCategory.SEMANTIC
        authority = OmissionAuthority.REVIEWER
    digest = hashlib.sha256(statement.encode()).hexdigest()
    return OmissionCensusEntry(
        f"omission-{digest[:24]}", category, authority, disposition, statement
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
    semantic_dispositions: tuple[SemanticDisposition, ...] = ()
    provider_census: tuple[ProviderCensus, ...] = ()
    import_registry: tuple[ImportRegistryEntry, ...] = ()

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
        omissions = list(_all_omissions(self))
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
                "imports": len(self.import_registry),
            },
            "provider_census": [asdict(item) for item in self.provider_census],
            "import_registry_sha256": hashlib.sha256(
                json.dumps(
                    [asdict(item) for item in self.import_registry],
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode()
            ).hexdigest(),
            "semantic_disposition_count": len(self.semantic_dispositions),
            "cutoff_count": len(self.cutoffs),
            "cutoff_manifest_sha256": hashlib.sha256(
                self.cutoffs_to_json().encode()
            ).hexdigest(),
            "cutoff_prefix_sample": [item.prefix_sha256 for item in self.cutoffs[:16]],
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
        """Render a bounded index for content-addressed cutoff segments."""
        segments = self.cutoff_segments_to_json()
        segment_digests = [
            hashlib.sha256(item.encode()).hexdigest() for item in segments
        ]
        segment_refs = [
            {
                "suffix": f".{index:04d}.json",
                "sha256": digest,
                "cutoff_count": len(json.loads(segment)["cutoffs"]),
            }
            for index, (segment, digest) in enumerate(
                zip(segments, segment_digests, strict=True), start=1
            )
        ]
        payload = {
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
            "selection_certification": self.selection_certification,
            "selected_session_id": self.selected_session_id,
            "cutoff_count": len(self.cutoffs),
            "segment_count": len(segments),
            "segments": segment_refs,
            "segment_sha256_manifest": hashlib.sha256(
                "\n".join(segment_digests).encode()
            ).hexdigest(),
        }
        rendered = json.dumps(
            payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False
        )
        if len(rendered.encode()) > MAX_RENDER_BYTES:
            message = "cutoff artifact exceeds the hard output cap"
            raise ValueError(message)
        return rendered

    def cutoff_segments_to_json(self) -> tuple[str, ...]:
        """Render the complete cutoff map as independently bounded segments."""
        common = {
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
            "selection_certification": self.selection_certification,
            "selected_session_id": self.selected_session_id,
        }
        chunks: list[list[dict[str, object]]] = []
        current: list[dict[str, object]] = []
        for cutoff in self.cutoffs:
            entry = asdict(cutoff)
            candidate = [*current, entry]
            probe = json.dumps(
                {
                    **common,
                    "segment_index": 999999,
                    "segment_count": 999999,
                    "cutoffs": candidate,
                },
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False,
            )
            if len(probe.encode()) > MAX_RENDER_BYTES:
                if not current:
                    message = "one cutoff entry exceeds the hard output cap"
                    raise ValueError(message)
                chunks.append(current)
                current = [entry]
            else:
                current = candidate
        if current or not chunks:
            chunks.append(current)

        rendered: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            segment = json.dumps(
                {
                    **common,
                    "segment_index": index,
                    "segment_count": len(chunks),
                    "cutoffs": chunk,
                },
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False,
            )
            if len(segment.encode()) > MAX_RENDER_BYTES:
                message = "cutoff segment exceeds the hard output cap"
                raise ValueError(message)
            rendered.append(segment)
        return tuple(rendered)

    def omission_census(self) -> tuple[OmissionCensusEntry, ...]:
        """Return stable typed rows without replacing any original omission."""
        return tuple(_classify_omission(item) for item in _all_omissions(self))

    def claim_entries(self) -> tuple[ClaimSegmentEntry, ...]:
        """Return every requirement and promise in stable claim-ID order."""

        def requirement_entry(item: RequirementEntry) -> ClaimSegmentEntry:
            context_kind, context, context_sha256, candidates = _requirement_context(
                item
            )
            return ClaimSegmentEntry(
                item.requirement_id,
                "requirement",
                str(item.authority_provenance),
                item.status,
                item.evidence,
                _evidence_ref_text(item.evidence),
                _bounded_claim_statement(item.statement),
                hashlib.sha256(item.statement.encode()).hexdigest(),
                context_kind,
                context,
                context_sha256,
                candidates,
            )

        requirements = (requirement_entry(item) for item in self.requirements)

        def promise_entry(item: PromiseEntry) -> ClaimSegmentEntry:
            context_kind, context, context_sha256, candidates = _fragment_context(
                item.statement
            )
            return ClaimSegmentEntry(
                item.promise_id,
                "promise",
                AuthorityProvenance.NON_AUTHORITATIVE,
                item.status,
                item.evidence,
                _evidence_ref_text(item.evidence),
                _bounded_claim_statement(item.statement),
                hashlib.sha256(item.statement.encode()).hexdigest(),
                context_kind,
                context,
                context_sha256,
                candidates,
            )

        promises = (promise_entry(item) for item in self.promises)
        return tuple(sorted((*requirements, *promises), key=lambda item: item.claim_id))

    def claim_segments_to_json(self) -> tuple[str, ...]:
        """Render every claim in independently bounded content-addressable chunks."""
        common = {
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
        }
        chunks = _bounded_json_chunks(
            [asdict(item) for item in self.claim_entries()],
            common=common,
            member="claims",
        )
        return tuple(
            json.dumps(
                {
                    **common,
                    "segment_index": index,
                    "segment_count": len(chunks),
                    "claims": chunk,
                },
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False,
            )
            for index, chunk in enumerate(chunks, start=1)
        )

    def claims_to_json(self) -> str:
        """Render the complete claim-segment index and its iteration manifest."""
        segments = self.claim_segments_to_json()
        refs = [
            {
                "suffix": f".{index:04d}.json",
                "sha256": hashlib.sha256(segment.encode()).hexdigest(),
                "claim_count": len(json.loads(segment)["claims"]),
            }
            for index, segment in enumerate(segments, start=1)
        ]
        payload = {
            "schema_version": self.schema_version,
            "iteration_manifest_sha256": self.manifest_sha256,
            "claim_count": len(self.claim_entries()),
            "segment_count": len(refs),
            "segments": refs,
            "segment_sha256_manifest": hashlib.sha256(
                "\n".join(str(item["sha256"]) for item in refs).encode()
            ).hexdigest(),
        }
        return _bounded_json(payload, "claim index")

    def semantic_disposition_draft_to_json(self) -> str:
        """Render the index for segmented, non-closing semantic draft rows."""
        segments = self.semantic_disposition_draft_segments_to_json()
        refs = [
            {
                "suffix": f".{index:04d}.json",
                "sha256": hashlib.sha256(segment.encode()).hexdigest(),
                "disposition_count": len(json.loads(segment)["dispositions"]),
            }
            for index, segment in enumerate(segments, start=1)
        ]
        return _bounded_json(
            {
                "schema_version": self.schema_version,
                "iteration_manifest_sha256": self.manifest_sha256,
                "disposition_count": len(self.claim_entries()),
                "segment_count": len(refs),
                "segments": refs,
                "segment_sha256_manifest": hashlib.sha256(
                    "\n".join(str(item["sha256"]) for item in refs).encode()
                ).hexdigest(),
            },
            "semantic disposition draft index",
        )

    def semantic_disposition_draft_segments_to_json(self) -> tuple[str, ...]:
        """Draft every claim as UNREVIEWED in independently bounded segments."""
        rows: list[dict[str, object]] = [
            {
                "claim_id": item.claim_id,
                "status": ReviewStatus.UNREVIEWED,
                "rationale": "",
                "receipt_refs": [],
            }
            for item in self.claim_entries()
        ]
        common = {
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
        }
        chunks = _bounded_json_chunks(rows, common=common, member="dispositions")
        return tuple(
            json.dumps(
                {
                    **common,
                    "segment_index": index,
                    "segment_count": len(chunks),
                    "dispositions": chunk,
                },
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False,
            )
            for index, chunk in enumerate(chunks, start=1)
        )

    def omission_segments_to_json(self) -> tuple[str, ...]:
        """Render every original omission with its typed classification."""
        common = {
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
        }
        chunks = _bounded_json_chunks(
            [asdict(item) for item in self.omission_census()],
            common=common,
            member="omissions",
        )
        return tuple(
            json.dumps(
                {
                    **common,
                    "segment_index": index,
                    "segment_count": len(chunks),
                    "omissions": chunk,
                },
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False,
            )
            for index, chunk in enumerate(chunks, start=1)
        )

    def omissions_to_json(self) -> str:
        """Render a content-addressed index over the complete omission census."""
        segments = self.omission_segments_to_json()
        refs = [
            {
                "suffix": f".{index:04d}.json",
                "sha256": hashlib.sha256(segment.encode()).hexdigest(),
                "omission_count": len(json.loads(segment)["omissions"]),
            }
            for index, segment in enumerate(segments, start=1)
        ]
        return _bounded_json(
            {
                "schema_version": self.schema_version,
                "iteration_manifest_sha256": self.manifest_sha256,
                "omission_count": len(self.omission_census()),
                "segment_count": len(refs),
                "segments": refs,
                "segment_sha256_manifest": hashlib.sha256(
                    "\n".join(str(item["sha256"]) for item in refs).encode()
                ).hexdigest(),
            },
            "omission index",
        )


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
    form_calls: dict[str, tuple[EvidenceRef, str, tuple[tuple[str, str], ...]]] = field(
        default_factory=dict
    )
    form_results: dict[
        str, tuple[str, frozenset[str], EvidenceRef, tuple[tuple[str, str], ...]]
    ] = field(default_factory=dict)
    seen_attachment_sha256: set[str] = field(default_factory=set)
    seen_finding_categories: set[str] = field(default_factory=set)
    tool_calls: dict[str, tuple[EvidenceRef, str]] = field(default_factory=dict)
    tool_results: dict[str, str] = field(default_factory=dict)
    approved_attachment_roots: tuple[Path, ...] = ()
    source_authority: dict[str, AuthorityProvenance] = field(default_factory=dict)
    import_registry: list[ImportRegistryEntry] = field(default_factory=list)
    attachment_dependencies: list[AttachmentDependency] = field(default_factory=list)


@dataclass(frozen=True)
class _CodexParseContext:
    direct_messages: dict[str, list[EvidenceRef]]
    form_schema_status: str


@dataclass
class _CodexContinuation:
    """State needed to parse an append-only Codex suffix exactly once."""

    direct_messages: dict[str, list[EvidenceRef]] = field(default_factory=dict)
    form_schema_status: str = ""
    previous_window: str = ""
    previous_number: int | None = None
    turn_states: dict[str, str] = field(default_factory=dict)
    active_turn_id: str = ""


@dataclass
class _SourceFacts:
    """Serializable facts for one source before cross-source finalization."""

    source: TranscriptSource
    source_id: str
    acc: _Accumulator
    byte_count: int
    line_count: int
    prefix_sha256: str
    last_event_id: str = ""
    final_ordinal: str = ""
    final_timestamp: str = ""
    codex: _CodexContinuation | None = None
    claude_session_id: str = ""
    claude_sidecar: bool = False
    native_identity: bool = False


_CODEX_EVENT_TYPES = frozenset(
    {
        "item_completed",
        "agent_message",
        "task_complete",
        "task_started",
        "thread_settings_applied",
        "token_count",
        "turn_aborted",
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


def first_session_meta(path: Path) -> dict[str, object] | None:
    """Return the first Codex session metadata, preserving filesystem errors."""
    with path.open("rb") as stream:
        for raw in stream:
            obj = _json_object(raw)
            if obj is not None and obj.get("type") == "session_meta":
                payload = obj.get("payload")
                return payload if isinstance(payload, dict) else None
    return None


def _is_codex_root(meta: Mapping[str, object]) -> bool:
    return meta.get("thread_source") != "subagent" and not meta.get("parent_thread_id")


def codex_root_kind(meta: Mapping[str, object]) -> RootKind:
    """Classify a native Codex transcript without granting authority by shape."""
    identity = {
        "source": meta.get("source", ""),
        "thread_source": meta.get("thread_source", ""),
        "originator": meta.get("originator", ""),
    }
    encoded = json.dumps(identity, sort_keys=True).lower()
    result = RootKind.UNKNOWN
    if meta.get("parent_thread_id") or "subagent" in encoded:
        result = RootKind.SUBAGENT
    elif "guardian" in encoded or "review" in encoded:
        result = RootKind.GUARDIAN
    elif "exec" in encoded:
        result = RootKind.EXEC_WORKER
    elif "plugin" in encoded:
        result = RootKind.PLUGIN_TASK
    elif "import" in encoded:
        result = RootKind.IMPORTED
    elif not any(identity.values()) or any(
        token in encoded
        for token in ("user", "interactive", "vscode", "desktop", "codex-tui")
    ):
        result = RootKind.INTERACTIVE
    return result


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
        try:
            meta = first_session_meta(path)
        except OSError:
            continue
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
    bases: TranscriptBases = DEFAULT_TRANSCRIPT_BASES,
    codex_session_id: str | None = None,
) -> list[TranscriptSource]:
    """Discover both native transcript providers for the same repository."""
    codex = discover_codex_transcripts(
        repo_root, base=bases.codex, limit=limit, session_id=codex_session_id
    )
    claude_root = (
        bases.claude if bases.claude is not None else command_audit.transcripts_base()
    )
    claude = command_audit.project_transcripts(claude_root, repo_root, limit=limit)
    return [
        *(TranscriptSource(Provider.CODEX, path) for path in codex),
        *(TranscriptSource(Provider.CLAUDE, path) for path in claude),
    ]


def provider_census(
    repo_root: Path,
    selected: Iterable[TranscriptSource],
    *,
    bases: TranscriptBases = DEFAULT_TRANSCRIPT_BASES,
) -> tuple[ProviderCensus, ...]:
    """Account for both provider fleets independently of their selectors."""
    codex_root = bases.codex if bases.codex is not None else codex_sessions_base()
    claude_root = (
        bases.claude if bases.claude is not None else command_audit.transcripts_base()
    )
    selected_rows = tuple(selected)
    codex_paths = tuple(codex_root.glob("**/*.jsonl")) if codex_root.is_dir() else ()
    claude_project = command_audit.project_dir(claude_root, repo_root)
    claude_paths = (
        tuple(claude_project.glob("**/*.jsonl")) if claude_project.is_dir() else ()
    )
    codex_archive = codex_root.parent / "archived_sessions"
    archived_codex = (
        sum(1 for _ in codex_archive.glob("*.jsonl")) if codex_archive.is_dir() else 0
    )
    rows: list[ProviderCensus] = []
    for provider, available, discovered_paths in (
        (Provider.CODEX, codex_root.is_dir(), codex_paths),
        (Provider.CLAUDE, claude_project.is_dir(), claude_paths),
    ):
        selected_count = sum(item.provider == provider for item in selected_rows)
        imported = 0
        malformed = 0
        unreadable = 0
        if provider == Provider.CODEX:
            for path in discovered_paths:
                try:
                    meta = first_session_meta(path)
                except OSError:
                    unreadable += 1
                    continue
                if meta is None:
                    malformed += 1
                elif codex_root_kind(meta) == RootKind.IMPORTED:
                    imported += 1
        rows.append(
            ProviderCensus(
                provider=provider,
                expected=True,
                available=available,
                discovered=len(discovered_paths),
                selected=selected_count,
                rejected=max(0, len(discovered_paths) - selected_count),
                archived=archived_codex if provider == Provider.CODEX else 0,
                imported=imported,
                malformed=malformed,
                unreadable=unreadable,
            )
        )
    return tuple(rows)


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


def requirement_kind(statement: str) -> RequirementKind:
    """Classify one atomized request by its durable semantic concern."""
    lowered = statement.lower()
    if (
        ("dependency" in lowered or "pyproject.toml" in lowered)
        and ("pyproject.toml" in lowered or "mise" in lowered)
        and any(
            token in lowered
            for token in ("owner", "declare", "declaration", "duplicate")
        )
    ):
        return RequirementKind.DEPENDENCY_OWNERSHIP
    if "graphify" in lowered and ("sdk" in lowered or "public api" in lowered):
        return RequirementKind.GRAPHIFY_SDK
    return RequirementKind.ACTION


def atomize_requirement_text(text: str) -> tuple[str, ...]:
    """Split a plan-sized request into independently dispositionable actions.

    Markdown bullets are the user's explicit action boundaries. Short prose is
    retained byte-for-byte so ordinary requests are not rewritten by a
    heuristic sentence splitter.
    """
    bullets = tuple(
        match.group(1).strip()
        for line in text.splitlines()
        if (match := re.match(r"^\s*-\s+(.+?)\s*$", line)) and match.group(1).strip()
    )
    return bullets if len(bullets) >= MIN_ATOMIZED_BULLETS else (text,)


def _requirement_target(statement: str, kind: RequirementKind) -> str:
    if kind == RequirementKind.DEPENDENCY_OWNERSHIP:
        return "python dependency ownership"
    if kind == RequirementKind.GRAPHIFY_SDK:
        return "Graphify SDK boundary"
    match = re.search(r"`([^`]+)`", statement)
    return match.group(1) if match else ""


def authority_provenance(event: CanonicalEvent) -> AuthorityProvenance:
    """Return the explicit or native authority source for one event."""
    metadata = dict(event.metadata)
    explicit = metadata.get("authority_provenance")
    if explicit:
        try:
            return AuthorityProvenance(explicit)
        except ValueError:
            return AuthorityProvenance.NON_AUTHORITATIVE
    if event.kind == EventKind.FORM_ANSWER:
        return AuthorityProvenance.PAIRED_FORM_ANSWER
    if event.kind == EventKind.USER_MESSAGE:
        return AuthorityProvenance.NATIVE_ROOT_USER
    return AuthorityProvenance.NON_AUTHORITATIVE


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
    key = (
        f"{event.evidence.provider}:{event.evidence.source_id}:"
        f"{event.kind}:{event.evidence.event_id}:{event.text}"
    )
    if key in acc.seen_event_ids:
        return
    acc.seen_event_ids.add(key)
    acc.events.append(event)
    provenance = acc.source_authority.get(
        event.evidence.source_id, authority_provenance(event)
    )
    if (
        event.kind == EventKind.FORM_ANSWER
        and provenance == AuthorityProvenance.NATIVE_ROOT_USER
    ):
        provenance = AuthorityProvenance.PAIRED_FORM_ANSWER
    if event.kind in {EventKind.USER_MESSAGE, EventKind.FORM_ANSWER} and provenance in {
        AuthorityProvenance.NATIVE_ROOT_USER,
        AuthorityProvenance.PAIRED_FORM_ANSWER,
    }:
        parent_digest = hashlib.sha256(event.text.encode()).hexdigest()
        for index, statement in enumerate(
            atomize_requirement_text(event.text), start=1
        ):
            kind = requirement_kind(statement)
            metadata = dict(event.metadata)
            acc.requirements.append(
                RequirementEntry(
                    _stable_claim_id("req", event.evidence, f"{index}\0{statement}"),
                    statement,
                    event.evidence,
                    event.kind,
                    bool(_AUTHORITY.search(statement + " " + str(event.metadata))),
                    authority_provenance=provenance,
                    kind=kind,
                    target=_requirement_target(statement, kind),
                    timing=(
                        "before implementation" if "before" in statement.lower() else ""
                    ),
                    scope=(
                        "repository" if "repository" in statement.lower() else "session"
                    ),
                    prerequisites=tuple(
                        token
                        for token in ("Graphify", "uv", "mise")
                        if re.search(
                            rf"(?<!\w){re.escape(token)}(?!\w)",
                            statement,
                            re.IGNORECASE,
                        )
                    ),
                    external_effect=bool(
                        re.match(
                            r"^\s*(?:please\s+)?(?:publish|push|create|update|delete|ship|land)\b",
                            statement,
                            re.IGNORECASE,
                        )
                    ),
                    parent_statement_sha256=parent_digest,
                    atom_index=index,
                    linked_question_id=(
                        metadata.get("question_id", "")
                        if event.kind == EventKind.FORM_ANSWER
                        else ""
                    ),
                    linked_question_text=(
                        metadata.get("question_text", "")
                        if event.kind == EventKind.FORM_ANSWER
                        else ""
                    ),
                    linked_question_sha256=(
                        metadata.get("question_sha256", "")
                        if event.kind == EventKind.FORM_ANSWER
                        else ""
                    ),
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
    if isinstance(content, str):
        yield "text", content
        return
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


def _attachment_dependency(
    payload: str, roots: tuple[Path, ...], content: bytes | None
) -> AttachmentDependency | None:
    if payload.startswith("data:"):
        return None
    parsed = urlparse(payload)
    path = Path(unquote(parsed.path)) if parsed.scheme == "file" else Path(payload)
    if not path.is_absolute():
        return None
    resolved = path.resolve(strict=False)
    for index, root in enumerate(roots):
        if resolved.is_relative_to(root):
            return AttachmentDependency(
                index,
                str(resolved.relative_to(root)),
                hashlib.sha256(content).hexdigest()
                if content is not None
                else "unavailable",
            )
    return None


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
    dependency = _attachment_dependency(payload, acc.approved_attachment_roots, content)
    if dependency is not None and dependency not in acc.attachment_dependencies:
        acc.attachment_dependencies.append(dependency)
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
        if (
            acc.source_authority.get(evidence.source_id)
            == AuthorityProvenance.NATIVE_ROOT_USER
        ):
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


def _codex_message_role(role: str, evidence: EvidenceRef, acc: _Accumulator) -> bool:
    """Accept assistant/user roles and silently discard known harness context."""
    if role in {"developer", "system"}:
        return False
    if role not in {"user", "assistant"}:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: message role {role!r}"
        )
        return False
    return True


def _codex_message(
    payload: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
    direct_messages: dict[str, list[EvidenceRef]],
) -> None:
    role = str(payload.get("role", ""))
    if not _codex_message_role(role, evidence, acc):
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
) -> tuple[tuple[str, str], ...]:
    arguments = payload.get("arguments")
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("questions"), list):
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: malformed form call"
        )
        return ()
    questions: dict[str, str] = {}
    valid = True
    for question in parsed["questions"]:
        if not isinstance(question, dict):
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: malformed question"
            )
            continue
        text = str(question.get("question", ""))
        question_id = str(question.get("id", "")) or (
            f"question-{hashlib.sha256(text.encode()).hexdigest()[:20]}" if text else ""
        )
        if not question_id or question_id in questions:
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: duplicate or empty question id"
            )
            valid = False
            continue
        questions[question_id] = _safe_context_text(text)
        metadata = (("id", question_id), *_metadata_pairs(question, ("header",)))
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.FORM_QUESTION, "assistant", text, evidence, metadata
            ),
        )
    return tuple(sorted(questions.items())) if valid else ()


def _form_answers(
    payload: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> tuple[frozenset[str], tuple[tuple[str, str], ...]] | None:
    output = payload.get("output")
    try:
        parsed = json.loads(output) if isinstance(output, str) else output
    except json.JSONDecodeError:
        parsed = None
    answers = parsed.get("answers") if isinstance(parsed, dict) else None
    if not isinstance(answers, dict):
        return None
    answer_ids: set[str] = set()
    answer_rows: list[tuple[str, str]] = []
    for question_id, value in answers.items():
        if isinstance(value, str):
            derived_id = (
                f"question-{hashlib.sha256(str(question_id).encode()).hexdigest()[:20]}"
            )
            answer_ids.add(derived_id)
            answer_rows.append((derived_id, _safe_text(value)))
            continue
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
            answer_rows.append((str(question_id), _safe_text(answer)))
    return frozenset(answer_ids), tuple(answer_rows)


def _codex_form_call(
    payload: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
    form_schema_status: str,
) -> None:
    call_id = str(payload.get("call_id", ""))
    questions = _form_questions(payload, evidence, acc)
    if not call_id or call_id in acc.form_calls:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: duplicate or empty form call id"
        )
    else:
        acc.form_calls[call_id] = (evidence, _turn_id(payload), questions)
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
    parsed = _form_answers(payload, evidence, acc)
    if parsed is None:
        return
    call_id = str(payload.get("call_id", ""))
    if not call_id or call_id in acc.form_results:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: duplicate or empty form result id"
        )
    else:
        answer_ids, answers = parsed
        acc.form_results[call_id] = (_turn_id(payload), answer_ids, evidence, answers)


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
        response_type in {"function_call", "custom_tool_call"}
        and payload.get("name") == "request_user_input"
    ):
        _codex_form_call(payload, evidence, acc, form_schema_status)
        _codex_tool_event(payload, evidence, acc, result=False)
    elif response_type in {"function_call_output", "custom_tool_call_output"}:
        _codex_form_result(payload, evidence, acc)
    elif response_type in {"function_call", "custom_tool_call"}:
        _codex_tool_event(payload, evidence, acc, result=False)
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
        root_kind=codex_root_kind(payload),
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
    elif event_type in {
        "task_complete",
        "task_failed",
        "turn_aborted",
        "turn_complete",
    }:
        if not turn_id or states.get(turn_id) != "started":
            acc.omissions.append(
                f"{source_id}:{line}: terminal event without unique start"
            )
        else:
            states[turn_id] = "complete"


def _resolve_pending_codex_user_messages(
    acc: _Accumulator,
    source_id: str,
    direct_messages: dict[str, list[EvidenceRef]],
) -> None:
    """Pair newly appended direct evidence with an earlier response-item twin."""
    replacements: list[CanonicalEvent] = []
    resolved_lines: set[int] = set()
    for event in acc.events:
        matches = direct_messages.get(event.text, [])
        if (
            event.kind == EventKind.UNVERIFIABLE_USER_MESSAGE
            and event.evidence.source_id == source_id
            and matches
        ):
            matches.pop(0)
            replacements.append(replace(event, kind=EventKind.USER_MESSAGE))
            resolved_lines.add(event.evidence.line)
        else:
            replacements.append(event)
    if not resolved_lines:
        return
    acc.events = replacements
    acc.omissions = [
        omission
        for omission in acc.omissions
        if not any(
            omission.startswith(f"{source_id}:{line}: ")
            and omission.endswith("user-role message lacks direct-user provenance")
            for line in resolved_lines
        )
    ]


def _parse_codex(
    records: list[tuple[int, dict[str, object], bytes]],
    source_id: str,
    acc: _Accumulator,
    continuation: _CodexContinuation | None = None,
) -> _CodexContinuation:
    known = {
        "session_meta",
        "turn_context",
        "response_item",
        "compacted",
        "event_msg",
        "world_state",
        "inter_agent_communication_metadata",
    }
    state = continuation or _CodexContinuation()
    direct_messages = state.direct_messages
    for text, rows in _direct_message_evidence(records, source_id).items():
        direct_messages.setdefault(text, []).extend(rows)
    _resolve_pending_codex_user_messages(acc, source_id, direct_messages)
    cli_version = _codex_cli_version(records)
    form_schema_status = state.form_schema_status or (
        "needs-probe" if "alpha" in cli_version else "confirmed"
    )
    context = _CodexParseContext(direct_messages, form_schema_status)
    previous_window = state.previous_window
    previous_number = state.previous_number
    turn_states = state.turn_states
    for line, obj, raw in records:
        record_type = str(obj.get("type", ""))
        evidence = _evidence(Provider.CODEX, source_id, line, obj, raw)
        payload = obj.get("payload")
        values = payload if isinstance(payload, dict) else {}
        if record_type == "turn_context":
            state.active_turn_id = _turn_id(values)
        elif (
            record_type == "response_item"
            and not _turn_id(values)
            and state.active_turn_id
            and acc.source_authority.get(source_id)
            == AuthorityProvenance.NATIVE_ROOT_USER
            and (
                values.get("name") == "request_user_input"
                or values.get("type")
                in {"function_call_output", "custom_tool_call_output"}
            )
        ):
            values = {**values, "turn_id": state.active_turn_id}
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
    return _CodexContinuation(
        direct_messages,
        form_schema_status,
        previous_window,
        previous_number,
        turn_states,
        state.active_turn_id,
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
                _codex_form_call(synthetic, evidence, acc, "confirmed")
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


def _claude_attachment_event(
    obj: Mapping[str, object], evidence: EvidenceRef, acc: _Accumulator
) -> None:
    """Separate external file bytes from Claude's inline structural union."""
    attachment = obj.get("attachment")
    if not isinstance(attachment, dict):
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
        return
    attachment_type = str(attachment.get("type", ""))
    warning_types = {
        "hook_cancelled",
        "hook_non_blocking_error",
        "read_truncation_notice",
    }
    diagnostic_types = {
        "agent_listing_delta",
        "command_permissions",
        "compact_file_reference",
        "date_change",
        "deferred_tools_delta",
        "diagnostic",
        "diagnostics",
        "edited_text_file",
        "hook_additional_context",
        "hook_success",
        "mcp_instructions_delta",
        "nested_memory",
        "output_style",
        "queued_command",
        "skill_listing",
    }
    file_like = attachment_type in {"file", "image", "document"} or (
        attachment_type not in warning_types | diagnostic_types
        and any(attachment.get(name) for name in ("image_url", "file_url", "path"))
    )
    if file_like:
        meta = _attachment(attachment, evidence, acc)
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.ATTACHMENT,
                "harness",
                meta.name,
                evidence,
                attachment=meta,
            ),
        )
        return
    if attachment_type not in warning_types | diagnostic_types:
        acc.omissions.append(
            f"{evidence.source_id}:{evidence.line}: "
            f"unknown Claude attachment {attachment_type!r}"
        )
    _add_event(
        acc,
        CanonicalEvent(
            EventKind.WARNING
            if attachment_type in warning_types
            else EventKind.DIAGNOSTIC,
            "harness",
            f"Claude attachment {attachment_type or 'unknown'}",
            evidence,
            _digest_metadata("attachment", attachment),
        ),
    )


def _claude_non_message_event(
    record_type: str,
    obj: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
) -> bool:
    """Retain one known Claude structural record; return whether handled."""
    if record_type == "attachment":
        _claude_attachment_event(obj, evidence, acc)
        return True
    if record_type == "bridge-session":
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.AUTHORITY_CONTEXT,
                "harness",
                "Claude bridge session",
                evidence,
                _digest_metadata("bridge_session", obj),
            ),
        )
        return True
    if record_type in {"agent-name", "file-history-delta", "pr-link"}:
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.DIAGNOSTIC,
                "harness",
                f"Claude structural record {record_type}",
                evidence,
                _digest_metadata(record_type, obj),
            ),
        )
        return True
    if record_type in {"summary", "last-prompt"}:
        summary = obj.get("summary", obj.get("content", obj.get("prompt", "")))
        _add_event(
            acc,
            CanonicalEvent(
                EventKind.CONTINUATION_SUMMARY,
                "harness",
                _safe_text(str(summary)),
                evidence,
                _digest_metadata("summary", summary),
            ),
        )
        return True
    if record_type not in {"progress", "system", "queue-operation"}:
        return False
    raw_text = str(
        obj.get("content", obj.get("message", obj.get("operation", record_type)))
    )
    lowered = raw_text.lower()
    if "warning" in lowered or re.search(r"\btruncat(?:e|ed|ion)", lowered):
        kind = EventKind.WARNING
    elif any(token in lowered for token in ("cancel", "abort", "stop")):
        kind = EventKind.TERMINAL_STATE
    else:
        kind = EventKind.DIAGNOSTIC
    _add_event(
        acc,
        CanonicalEvent(
            kind,
            "harness",
            _safe_text(raw_text),
            evidence,
            _digest_metadata(record_type, obj),
        ),
    )
    return True


def _claude_message_event(
    record_type: str,
    obj: Mapping[str, object],
    evidence: EvidenceRef,
    acc: _Accumulator,
) -> None:
    """Normalize one Claude assistant/user record and its paired form result."""
    message = obj.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if record_type == "user" and obj.get("isMeta") is True:
        for _, text in _text_blocks(content):
            _add_event(
                acc,
                CanonicalEvent(
                    EventKind.UNVERIFIABLE_USER_MESSAGE,
                    "harness",
                    _safe_text(text),
                    evidence,
                    (("authority_provenance", AuthorityProvenance.NON_AUTHORITATIVE),),
                ),
            )
    else:
        _claude_content(content, record_type=record_type, evidence=evidence, acc=acc)
    result = _claude_form_result(obj)
    if result is not None:
        synthetic = {"output": json.dumps({"answers": result["answers"]})}
        parsed_answers = _form_answers(synthetic, evidence, acc)
        call_id = ""
        if isinstance(content, list):
            call_id = next(
                (
                    str(block.get("tool_use_id", ""))
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "tool_result"
                ),
                "",
            )
        if not call_id or parsed_answers is None or call_id in acc.form_results:
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: "
                "malformed or duplicate Claude form result"
            )
        else:
            answer_ids, answers = parsed_answers
            acc.form_results[call_id] = ("", answer_ids, evidence, answers)
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


def _parse_claude(
    records: list[tuple[int, dict[str, object], bytes]],
    source_id: str,
    acc: _Accumulator,
    session_id: str = "",
) -> str:
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
        "agent-name",
        "bridge-session",
        "file-history-delta",
        "pr-link",
    }
    for line, obj, raw in records:
        record_type = str(obj.get("type", ""))
        session_id = str(obj.get("sessionId", session_id))
        evidence = _evidence(Provider.CLAUDE, source_id, line, obj, raw)
        if record_type in {"assistant", "user"}:
            _claude_message_event(record_type, obj, evidence, acc)
        elif _claude_non_message_event(record_type, obj, evidence, acc):
            continue
        elif record_type not in known:
            acc.omissions.append(
                f"{source_id}:{line}: unknown Claude record {record_type!r}"
            )
    return session_id


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
    if source.provider == Provider.CODEX:
        raw_meta = next(
            (
                obj["payload"]
                for _, obj, _ in records
                if obj.get("type") == "session_meta"
                and isinstance(obj.get("payload"), dict)
            ),
            {},
        )
        meta: Mapping[str, object] = raw_meta if isinstance(raw_meta, dict) else {}
        kind = codex_root_kind(meta)
        provenance = (
            AuthorityProvenance.NATIVE_ROOT_USER
            if kind == RootKind.INTERACTIVE
            else (
                AuthorityProvenance.IMPORTED_HISTORY
                if kind == RootKind.IMPORTED
                else AuthorityProvenance.NON_AUTHORITATIVE
            )
        )
        acc.source_authority[source_id] = provenance
        if kind == RootKind.IMPORTED:
            acc.import_registry.append(
                ImportRegistryEntry(
                    source.provider,
                    source_id,
                    str(meta.get("id", meta.get("session_id", ""))),
                    kind,
                    hashlib.sha256(data).hexdigest(),
                )
            )
    else:
        is_sidecar = "subagents" in path.parts or any(
            obj.get("isSidechain") is True for _, obj, _ in records
        )
        acc.source_authority[source_id] = (
            AuthorityProvenance.NON_AUTHORITATIVE
            if is_sidecar
            else AuthorityProvenance.NATIVE_ROOT_USER
        )
    before = len(acc.events)
    if source.provider == Provider.CODEX:
        _parse_codex(records, source_id, acc)
    else:
        session_id = _parse_claude(records, source_id, acc)
        acc.lineage.append(
            SessionLineage(
                Provider.CLAUDE,
                source_id,
                session_id,
                "",
                "subagent" if "subagents" in path.parts else "",
                "",
                root_kind=(
                    RootKind.SUBAGENT
                    if "subagents" in path.parts
                    else RootKind.INTERACTIVE
                ),
            )
        )
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


def _records_from_bytes(
    data: bytes,
    source: TranscriptSource,
    acc: _Accumulator,
    *,
    line_offset: int = 0,
) -> list[tuple[int, dict[str, object], bytes]]:
    """Decode complete JSONL bytes while retaining native line coordinates."""
    records: list[tuple[int, dict[str, object], bytes]] = []
    for relative_line, raw in enumerate(data.splitlines(keepends=True), start=1):
        line = line_offset + relative_line
        obj = _json_object(raw)
        if obj is None:
            acc.omissions.append(
                f"{source.provider}:{source.path.name}:{line}: malformed JSON"
            )
            continue
        records.append((line, obj, raw))
    return records


def _parse_source_facts(
    data: bytes,
    source: TranscriptSource,
    roots: tuple[Path, ...],
    prior: _SourceFacts | None = None,
) -> _SourceFacts:
    """Parse one cold source or append-only suffix into serializable facts."""
    acc = (
        prior.acc
        if prior is not None
        else _Accumulator(approved_attachment_roots=roots)
    )
    offset = prior.line_count if prior is not None else 0
    records = _records_from_bytes(data, source, acc, line_offset=offset)
    if prior is None:
        source_id = _source_id(source.provider, records)
        native_identity = ":content-" not in source_id
    else:
        if not prior.native_identity:
            message = "content-derived source identity changed"
            raise AppendRebuildError(message)
        source_id = prior.source_id
        native_identity = True
    before = len(acc.events)
    codex = prior.codex if prior is not None else None
    claude_session_id = prior.claude_session_id if prior is not None else ""
    claude_sidecar = prior.claude_sidecar if prior is not None else False
    if source.provider == Provider.CODEX:
        if prior is not None and any(
            obj.get("type") == "session_meta" for _, obj, _ in records
        ):
            message = "late Codex session metadata"
            raise AppendRebuildError(message)
        if prior is None:
            raw_meta = next(
                (
                    obj["payload"]
                    for _, obj, _ in records
                    if obj.get("type") == "session_meta"
                    and isinstance(obj.get("payload"), dict)
                ),
                {},
            )
            meta: Mapping[str, object] = raw_meta if isinstance(raw_meta, dict) else {}
            kind = codex_root_kind(meta)
            acc.source_authority[source_id] = (
                AuthorityProvenance.NATIVE_ROOT_USER
                if kind == RootKind.INTERACTIVE
                else (
                    AuthorityProvenance.IMPORTED_HISTORY
                    if kind == RootKind.IMPORTED
                    else AuthorityProvenance.NON_AUTHORITATIVE
                )
            )
        codex = _parse_codex(records, source_id, acc, codex)
    else:
        suffix_sidecar = "subagents" in source.path.parts or any(
            obj.get("isSidechain") is True for _, obj, _ in records
        )
        if prior is not None and suffix_sidecar and not claude_sidecar:
            message = "Claude authority changed in suffix"
            raise AppendRebuildError(message)
        claude_sidecar = claude_sidecar or suffix_sidecar
        acc.source_authority[source_id] = (
            AuthorityProvenance.NON_AUTHORITATIVE
            if claude_sidecar
            else AuthorityProvenance.NATIVE_ROOT_USER
        )
        claude_session_id = _parse_claude(records, source_id, acc, claude_session_id)
        lineage = SessionLineage(
            Provider.CLAUDE,
            source_id,
            claude_session_id,
            "",
            "subagent" if "subagents" in source.path.parts else "",
            "",
            root_kind=(
                RootKind.SUBAGENT
                if "subagents" in source.path.parts
                else RootKind.INTERACTIVE
            ),
        )
        acc.lineage = [item for item in acc.lineage if item.source_id != source_id]
        acc.lineage.append(lineage)
    final_obj = records[-1][1] if records else {}
    return _SourceFacts(
        source,
        source_id,
        acc,
        (prior.byte_count if prior else 0) + len(data),
        offset + len(data.splitlines()),
        "" if prior is not None else hashlib.sha256(data).hexdigest(),
        acc.events[-1].evidence.event_id
        if len(acc.events) > before
        else (prior.last_event_id if prior else ""),
        str(final_obj.get("ordinal", prior.final_ordinal if prior else "")),
        str(final_obj.get("timestamp", prior.final_timestamp if prior else "")),
        codex,
        claude_session_id,
        claude_sidecar,
        native_identity,
    )


def _encode_source_facts(state: _SourceFacts) -> bytes:
    """Serialize normalized facts without leaking the native transcript path."""
    scrubbed = replace(
        state,
        source=TranscriptSource(state.source.provider, Path()),
        acc=replace(state.acc, approved_attachment_roots=()),
    )
    return codec.encode(scrubbed)


def _decode_source_facts(
    data: bytes, source: TranscriptSource, roots: tuple[Path, ...]
) -> _SourceFacts:
    """Restore the caller-owned source path after decoding path-free facts."""
    state = codec.decode(data, _SourceFacts)
    return replace(
        state,
        source=source,
        acc=replace(state.acc, approved_attachment_roots=roots),
    )


def _merge_unique_map[K, V](
    target: dict[K, V], source: Mapping[K, V], acc: _Accumulator, label: str
) -> None:
    for key, value in source.items():
        if key in target:
            acc.omissions.append(f"duplicate {label} {key}")
        else:
            target[key] = value


def _merge_source_fact(acc: _Accumulator, state: _SourceFacts) -> None:
    """Merge one source without making cross-source completion decisions."""
    for event in state.acc.events:
        _add_event(acc, event)
    if state.codex is not None:
        for text, evidence_rows in state.codex.direct_messages.items():
            for evidence in evidence_rows:
                _add_event(
                    acc,
                    CanonicalEvent(
                        EventKind.USER_MESSAGE, "user", _safe_text(text), evidence
                    ),
                )
    acc.omissions.extend(state.acc.omissions)
    acc.lineage.extend(state.acc.lineage)
    open_turn = bool(
        state.codex
        and any(value != "complete" for value in state.codex.turn_states.values())
    )
    acc.cutoffs.append(
        SourceCutoff(
            state.source.provider,
            state.source_id,
            str(state.source.path.resolve()),
            state.byte_count,
            state.line_count,
            state.prefix_sha256,
            state.last_event_id,
            state.final_ordinal,
            state.final_timestamp,
            open_turn,
        )
    )
    acc.import_registry.extend(
        ImportRegistryEntry(
            state.source.provider,
            state.source_id,
            lineage.session_id,
            lineage.root_kind,
            state.prefix_sha256,
        )
        for lineage in state.acc.lineage
        if lineage.root_kind == RootKind.IMPORTED
    )
    _merge_unique_map(acc.form_calls, state.acc.form_calls, acc, "form call id")
    _merge_unique_map(acc.form_results, state.acc.form_results, acc, "form result id")
    _merge_unique_map(acc.tool_calls, state.acc.tool_calls, acc, "tool call id")
    _merge_unique_map(acc.tool_results, state.acc.tool_results, acc, "tool result id")
    if state.codex is not None:
        acc.omissions.extend(
            f"{state.source_id}: open turn {turn_id}"
            for turn_id, turn_state in sorted(state.codex.turn_states.items())
            if turn_state != "complete"
        )


def _finalize_relationships(acc: _Accumulator) -> None:
    """Resolve forms and tools after every source fact has been merged."""
    for call_id, call in sorted(acc.form_calls.items()):
        evidence, turn_id, questions = call
        question_ids = frozenset(question_id for question_id, _ in questions)
        result = acc.form_results.get(call_id)
        if result is None:
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: missing form result {call_id}"
            )
        elif result[:2] != (turn_id, question_ids):
            acc.omissions.append(
                f"{evidence.source_id}:{evidence.line}: form result identity "
                f"mismatch {call_id}"
            )
        else:
            _, _, result_evidence, answers = result
            question_text = dict(questions)
            for question_id, answer in answers:
                linked_text = question_text[question_id]
                _add_event(
                    acc,
                    CanonicalEvent(
                        EventKind.FORM_ANSWER,
                        "user",
                        answer,
                        result_evidence,
                        (
                            ("question_id", _safe_question_id(question_id)),
                            ("question_text", linked_text),
                            (
                                "question_sha256",
                                hashlib.sha256(linked_text.encode()).hexdigest(),
                            ),
                        ),
                    ),
                )
    for call_id in sorted(acc.form_results.keys() - acc.form_calls.keys()):
        result = acc.form_results[call_id]
        acc.omissions.append(
            f"{result[2].source_id}:{result[2].line}: orphan form result {call_id}"
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
                f"{evidence.source_id}:{evidence.line}: tool result turn "
                f"mismatch {call_id}"
            )


def _finalize_source_facts(
    facts: Iterable[_SourceFacts],
    *,
    recorded_cwd: str,
    dispositions: Iterable[PreventionDisposition],
    semantic_dispositions: Iterable[SemanticDisposition],
    extra_omissions: Iterable[str] = (),
) -> RequirementCoverage:
    """Merge cached source facts and always rerun every global decision."""
    rows = tuple(facts)
    semantic_rows = tuple(semantic_dispositions)
    acc = _Accumulator()
    for state in rows:
        acc.source_authority.update(state.acc.source_authority)
    for state in rows:
        _merge_source_fact(acc, state)
    acc.omissions.extend(extra_omissions)
    _resolve_inherited_prefix(acc)
    _finalize_relationships(acc)
    coverage = RequirementCoverage(
        tuple(
            sorted(
                acc.events,
                key=lambda item: (
                    item.evidence.provider,
                    item.evidence.source_id,
                    item.evidence.line,
                ),
            )
        ),
        tuple(
            sorted(
                acc.requirements,
                key=lambda item: (
                    item.evidence.provider,
                    item.evidence.source_id,
                    item.evidence.line,
                    item.atom_index,
                ),
            )
        ),
        tuple(
            sorted(
                acc.promises,
                key=lambda item: (
                    item.evidence.provider,
                    item.evidence.source_id,
                    item.evidence.line,
                ),
            )
        ),
        tuple(acc.high_severity_findings),
        tuple(dispositions),
        tuple(acc.lineage),
        tuple(acc.cutoffs),
        recorded_cwd,
        tuple(acc.omissions),
        semantic_dispositions=semantic_rows,
        import_registry=tuple(acc.import_registry),
    )
    return apply_semantic_dispositions(coverage, semantic_rows)


def parse_transcripts(
    sources: Iterable[TranscriptSource],
    *,
    recorded_cwd: str = "",
    dispositions: Iterable[PreventionDisposition] = (),
    semantic_dispositions: Iterable[SemanticDisposition] = (),
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
    facts: list[_SourceFacts] = []
    omissions: list[str] = []
    for source in source_list:
        try:
            before = source.path.stat()
            data = source.path.read_bytes()
            after = source.path.stat()
        except OSError as exc:
            omissions.append(f"{source.provider}:{source.path}: unreadable: {exc}")
            continue
        last_line = data.rsplit(b"\n", maxsplit=1)[-1]
        complete_end = (
            len(data)
            if not last_line or _json_object(last_line) is not None
            else data.rfind(b"\n") + 1
        )
        complete = data[:complete_end]
        tail_bytes = len(data) - complete_end
        if not complete:
            omissions.append(
                f"{source.provider}:{source.path}: source ends with an incomplete "
                f"JSONL record ({tail_bytes} byte(s))"
            )
            continue
        state = _parse_source_facts(complete, source, roots)
        if tail_bytes:
            state.acc.omissions.append(
                f"{state.source_id}: source ends with an incomplete JSONL record "
                f"({tail_bytes} byte(s))"
            )
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            state.acc.omissions.append(
                f"{state.source_id}: source changed while being read"
            )
        facts.append(state)
    return _finalize_source_facts(
        facts,
        recorded_cwd=recorded_cwd,
        dispositions=dispositions,
        semantic_dispositions=semantic_dispositions,
        extra_omissions=omissions,
    )


def apply_semantic_dispositions(
    coverage: RequirementCoverage,
    dispositions: Iterable[SemanticDisposition],
) -> RequirementCoverage:
    """Apply reviewed dispositions by stable claim ID and fail loud on drift."""
    rows = tuple(dispositions)
    by_id: dict[str, SemanticDisposition] = {}
    omissions = list(coverage.omissions)
    for row in rows:
        if row.claim_id in by_id:
            omissions.append(f"duplicate semantic disposition {row.claim_id}")
        by_id[row.claim_id] = row
    claim_ids = {
        *(item.requirement_id for item in coverage.requirements),
        *(item.promise_id for item in coverage.promises),
    }
    omissions.extend(
        f"semantic disposition references unknown claim {claim_id}"
        for claim_id in sorted(by_id.keys() - claim_ids)
    )

    def requirement(item: RequirementEntry) -> RequirementEntry:
        row = by_id.get(item.requirement_id)
        if row is None or not row.persistable:
            return item
        return replace(item, status=row.status, receipt_refs=row.receipt_refs)

    def promise(item: PromiseEntry) -> PromiseEntry:
        row = by_id.get(item.promise_id)
        if row is None or not row.persistable:
            return item
        return replace(item, status=row.status, receipt_refs=row.receipt_refs)

    return replace(
        coverage,
        requirements=tuple(requirement(item) for item in coverage.requirements),
        promises=tuple(promise(item) for item in coverage.promises),
        semantic_dispositions=rows,
        omissions=tuple(omissions),
    )


def semantic_disposition_omissions(coverage: RequirementCoverage) -> tuple[str, ...]:
    """Name every actionable claim still lacking semantic closure."""
    return tuple(
        [
            f"requirement {item.requirement_id} lacks semantic disposition"
            for item in coverage.requirements
            if item.status == ReviewStatus.UNREVIEWED
        ]
        + [
            f"promise {item.promise_id} lacks semantic disposition"
            for item in coverage.promises
            if item.status == ReviewStatus.UNREVIEWED
        ]
    )


def _all_omissions(coverage: RequirementCoverage) -> tuple[str, ...]:
    """One deterministic census including structural and reviewed-decision gaps."""
    return (
        *coverage.omissions,
        *disposition_omissions(coverage),
        *semantic_disposition_omissions(coverage),
    )


def _validated_source_root(source_repo_root: Path) -> tuple[Path | None, str]:
    try:
        resolved = source_repo_root.expanduser().resolve(strict=True)
    except OSError as exc:
        return None, f"source repository root is unavailable: {exc}"
    if not resolved.is_dir() or not (resolved / ".git").exists():
        return None, f"source repository root is not a Git checkout: {resolved}"
    return resolved, ""


def _add_cache_stats(left: CacheStats, right: CacheStats) -> CacheStats:
    return CacheStats(
        left.reused_sources + right.reused_sources,
        left.appended_sources + right.appended_sources,
        left.rebuilt_sources + right.rebuilt_sources,
        left.decoded_bytes + right.decoded_bytes,
        left.corrupt_entries + right.corrupt_entries,
    )


def _dependencies_match(state: _SourceFacts, roots: tuple[Path, ...]) -> bool:
    for dependency in state.acc.attachment_dependencies:
        if dependency.root_index >= len(roots):
            return False
        content = _local_attachment_bytes(
            roots[dependency.root_index] / dependency.relative_path, roots
        )
        current = (
            hashlib.sha256(content).hexdigest()
            if content is not None
            else "unavailable"
        )
        if current != dependency.payload_sha256:
            return False
    return True


def _append_source_facts(
    serialized: bytes,
    suffix: bytes,
    source: TranscriptSource,
    roots: tuple[Path, ...],
) -> bytes:
    """Validate external facts before extending an append-only source."""
    prior = _decode_source_facts(serialized, source, roots)
    if not _dependencies_match(prior, roots):
        message = "external attachment dependency changed before append"
        raise AppendRebuildError(message)
    return _encode_source_facts(_parse_source_facts(suffix, source, roots, prior))


def _cached_requirement_coverage(
    repo_root: Path,
    sources: Iterable[TranscriptSource],
    *,
    dispositions: Iterable[PreventionDisposition],
    semantic_dispositions: Iterable[SemanticDisposition],
    rebuild_cache: bool,
) -> tuple[RequirementCoverage, CacheStats, SessionStore]:
    """Resolve each source through the repo-local cache, then finalize globally."""
    source_rows = tuple(sources)
    roots = tuple(
        sorted({source.path.parent.resolve() for source in source_rows}, key=str)
    )
    policy_material = "\n".join(str(path) for path in roots)
    policy = hashlib.sha256(
        f"{_CACHE_POLICY_FINGERPRINT}\0{policy_material}".encode()
    ).hexdigest()
    cache_root = repo_root / ".agent" / "state" / "session-review"
    parser_fingerprint = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    states: list[_SourceFacts] = []
    omissions: list[str] = []
    stats = CacheStats()
    for source in source_rows:
        store = SessionStore(
            cache_root,
            parser_fingerprint=parser_fingerprint,
            policy_fingerprint=policy,
        )

        def cold(data: bytes, selected: TranscriptSource = source) -> bytes:
            return _encode_source_facts(_parse_source_facts(data, selected, roots))

        def append(
            serialized: bytes,
            suffix: bytes,
            selected: TranscriptSource = source,
        ) -> bytes:
            return _append_source_facts(serialized, suffix, selected, roots)

        resolved = store.resolve(
            str(source.provider),
            source.path,
            cold_parser=cold,
            append_parser=append,
            rebuild=rebuild_cache,
        )
        if not resolved.facts:
            omissions.append(
                f"{source.provider}:{source.path}: {resolved.reason} "
                f"({resolved.incomplete_tail_bytes} byte(s))"
            )
            stats = _add_cache_stats(stats, resolved.stats)
            continue
        try:
            state = _decode_source_facts(resolved.facts, source, roots)
        except TypeError, ValueError, codec.UnsupportedTypeError:
            resolved = store.resolve(
                str(source.provider),
                source.path,
                cold_parser=cold,
                append_parser=append,
                rebuild=True,
            )
            try:
                state = _decode_source_facts(resolved.facts, source, roots)
            except TypeError, ValueError, codec.UnsupportedTypeError:
                omissions.append(
                    f"{source.provider}:{source.path}: cache rebuild failed"
                )
                stats = _add_cache_stats(stats, resolved.stats)
                continue
        if resolved.stats.reused_sources and not _dependencies_match(state, roots):
            resolved = store.resolve(
                str(source.provider),
                source.path,
                cold_parser=cold,
                append_parser=append,
                rebuild=True,
            )
            state = _decode_source_facts(resolved.facts, source, roots)
        stats = _add_cache_stats(stats, resolved.stats)
        if resolved.source is None:
            omissions.append(
                f"{source.provider}:{source.path}: "
                f"{resolved.reason or 'source unavailable'}"
            )
            continue
        state = replace(
            state,
            byte_count=resolved.source.byte_count,
            line_count=resolved.source.line_count,
            prefix_sha256=resolved.source.prefix_sha256,
        )
        states.append(state)
        if not resolved.complete:
            omissions.append(
                f"{state.source_id}: {resolved.reason} "
                f"({resolved.incomplete_tail_bytes} byte(s))"
            )
    aggregate_policy = hashlib.sha256(
        codec.encode(
            [
                (str(state.source.provider), state.acc.attachment_dependencies)
                for state in states
            ]
        )
    ).hexdigest()
    run_store = SessionStore(
        cache_root,
        parser_fingerprint=parser_fingerprint,
        policy_fingerprint=hashlib.sha256(
            f"{policy}\0{aggregate_policy}".encode()
        ).hexdigest(),
    )
    coverage = _finalize_source_facts(
        states,
        recorded_cwd=str(repo_root),
        dispositions=dispositions,
        semantic_dispositions=semantic_dispositions,
        extra_omissions=omissions,
    )
    return coverage, stats, run_store


def build_requirement_coverage(
    source_repo_root: Path,
    *,
    bases: TranscriptBases = DEFAULT_TRANSCRIPT_BASES,
    dispositions: Iterable[PreventionDisposition] = (),
    semantic_dispositions: Iterable[SemanticDisposition] = (),
    selection: CoverageSelection = DEFAULT_COVERAGE_SELECTION,
) -> RequirementCoverage:
    """Discover transcripts whose recorded cwd is the explicitly audited root."""
    codex_session_id = selection.codex_session_id or selection.session_id
    certification = (
        SelectionCertification.EXPLICIT_SESSION_ID
        if codex_session_id
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
            codex_session_id or "",
        )
    sources = discover_sources(
        repo_root,
        limit=selection.limit,
        bases=bases,
        codex_session_id=codex_session_id,
    )
    census = provider_census(
        repo_root,
        sources,
        bases=bases,
    )
    codex_selected = next(
        (row.selected for row in census if row.provider == Provider.CODEX), 0
    )
    selection_omissions = (
        (f"explicit Codex session {codex_session_id} selected no native root",)
        if codex_session_id and codex_selected == 0
        else ()
    )
    if selection_omissions:
        certification = SelectionCertification.EXPLICIT_SESSION_ID_UNRESOLVED
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
            (
                f"no transcripts matched recorded cwd {repo_root}",
                *selection_omissions,
            ),
            certification,
            codex_session_id or "",
            provider_census=census,
        )
    coverage, cache_stats, store = _cached_requirement_coverage(
        repo_root,
        sources,
        dispositions=dispositions,
        semantic_dispositions=semantic_dispositions,
        rebuild_cache=selection.rebuild_cache,
    )
    coverage = replace(
        coverage,
        selection_certification=certification,
        selected_session_id=codex_session_id or "",
        provider_census=census,
        omissions=(*coverage.omissions, *selection_omissions),
    )
    if selection.require_active_identity and not codex_session_id:
        coverage = replace(
            coverage,
            omissions=(
                *coverage.omissions,
                _UNCERTIFIED_ACTIVITY,
            ),
        )
    store.publish_run(
        RunReceipt(
            store.parser_fingerprint,
            store.policy_fingerprint,
            coverage.manifest_sha256,
            cache_stats,
            coverage.status == CoverageStatus.COMPLETE,
        )
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


def load_semantic_dispositions(path: Path) -> tuple[SemanticDisposition, ...]:
    """Load typed semantic decisions; issue/carrier references alone never close."""
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        message = "semantic dispositions must be a JSON array"
        raise TypeError(message)
    rows: list[SemanticDisposition] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            message = f"semantic disposition {index} must be an object"
            raise TypeError(message)
        refs = item.get("receipt_refs")
        if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
            message = f"semantic disposition {index} needs string receipt_refs"
            raise ValueError(message)
        try:
            status = ReviewStatus(str(item.get("status", "")))
        except ValueError as exc:
            message = f"semantic disposition {index} has an invalid status"
            raise ValueError(message) from exc
        row = SemanticDisposition(
            str(item.get("claim_id", "")),
            status,
            str(item.get("rationale", "")),
            tuple(refs),
        )
        if not row.persistable:
            message = (
                f"semantic disposition {index} is not persistable; OPEN needs "
                "rationale plus an issue/artifact carrier, while terminal status "
                "needs proof"
            )
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


def issue_candidate_requirement_ids(
    coverage: RequirementCoverage,
) -> tuple[str, ...]:
    """Return unreviewed requests that explicitly require durable tracking."""
    return tuple(
        sorted(
            requirement.requirement_id
            for requirement in coverage.requirements
            if requirement.status == ReviewStatus.UNREVIEWED
            and _ISSUE_TRACKING_REQUEST.search(requirement.statement)
            and not _AGENT_REVIEW_ENVELOPE.search(requirement.statement)
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
    unreviewed_requirements = tuple(
        sorted(
            requirement.requirement_id
            for requirement in coverage.requirements
            if requirement.status == ReviewStatus.UNREVIEWED
            and not _AGENT_REVIEW_ENVELOPE.search(requirement.statement)
        )
    )
    issue_candidates = issue_candidate_requirement_ids(coverage)
    unreviewed_promises = tuple(
        sorted(
            promise.promise_id
            for promise in coverage.promises
            if promise.status == ReviewStatus.UNREVIEWED
        )
    )
    open_requirements = tuple(
        sorted(
            requirement.requirement_id
            for requirement in coverage.requirements
            if requirement.status == ReviewStatus.OPEN
            and not _AGENT_REVIEW_ENVELOPE.search(requirement.statement)
        )
    )
    open_promises = tuple(
        sorted(
            promise.promise_id
            for promise in coverage.promises
            if promise.status == ReviewStatus.OPEN
        )
    )
    expected_provider_missing = any(
        row.expected and row.selected == 0 for row in coverage.provider_census
    )
    if (
        coverage.status == CoverageStatus.INCOMPLETE
        or expected_provider_missing
        or unresolved
        or unreviewed_requirements
        or unreviewed_promises
        or open_requirements
        or open_promises
    ):
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
        unreviewed_requirements,
        issue_candidates,
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
        unreviewed_promise_ids=unreviewed_promises,
        open_requirement_ids=open_requirements,
        open_promise_ids=open_promises,
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
        "## Provider census",
        "",
    ]
    if coverage.provider_census:
        out += [
            (
                "| provider | expected | available | discovered | selected | "
                "rejected | archived | imported | malformed | unreadable |"
            ),
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
            *(
                f"| {item.provider} | {item.expected} | {item.available} | "
                f"{item.discovered} | {item.selected} | {item.rejected} | "
                f"{item.archived} | {item.imported} | {item.malformed} | "
                f"{item.unreadable} |"
                for item in coverage.provider_census
            ),
        ]
    else:
        out.append("_No discovery census was requested for direct parser input._")
    out += [
        "",
        "## Requirements",
        "",
    ]
    if coverage.requirements:
        out += [
            "| id | kind | provenance | status | receipts | target | statement |",
            "|---|---|---|---|---|---|---|",
            *(
                f"| `{item.requirement_id}` | {item.kind} | "
                f"{item.authority_provenance} | {item.status} | "
                f"{_table_text(', '.join(item.receipt_refs))} | "
                f"{_table_text(item.target)} | "
                f"{_table_text(_bounded_claim_statement(item.statement))} |"
                for item in coverage.requirements
            ),
        ]
    else:
        out.append("_No user-authored requirement evidence was parsed._")
    out += ["", "## Promises", ""]
    if coverage.promises:
        out += [
            "| id | status | receipts | statement |",
            "|---|---|---|---|",
            *(
                f"| `{item.promise_id}` | {item.status} | "
                f"{_table_text(', '.join(item.receipt_refs))} | "
                f"{_table_text(_bounded_claim_statement(item.statement))} |"
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
    all_omissions = (
        *coverage.omissions,
        *disposition_omissions(coverage),
        *semantic_disposition_omissions(coverage),
    )
    if all_omissions:
        out.extend(f"- {item}" for item in all_omissions)
    else:
        out.append("_None._")
    out.append("")
    return _cap_utf8("\n".join(out))
