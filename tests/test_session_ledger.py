# Copyright (c) 2026 Raymond Manaloto
"""Tests for the lossless session requirement and promise ledger."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import session_ledger

if TYPE_CHECKING:
    from collections.abc import Mapping

FIXTURES = Path(__file__).parent / "fixtures" / "session_review"

_EVIDENCE = session_ledger.EvidenceRef(
    session_ledger.Provider.CODEX, "codex:test", 1, "event", "0" * 64
)
_CONFIRMED = session_ledger.HighSeverityFinding(
    "risk-1",
    "credential-launcher",
    "confirmed",
    _EVIDENCE,
    session_ledger.ReviewStatus.SATISFIED,
)
_DISPOSITION = session_ledger.PreventionDisposition(
    "risk-1",
    "test",
    "mutation fails",
    "normal gate passes",
    "issue #1",
    attested=True,
)
_ATTESTATION = session_ledger.ReceiptAttestation(
    "test-run", "test-nonce", allow_test_signed=True
)
_COVERAGE_STATUS_TABLE = tuple(
    (omissions, findings, dispositions, expected)
    for omissions in ((), ("one structural omission",))
    for findings in ((), (_CONFIRMED,))
    for dispositions in ((), (_DISPOSITION,))
    for expected in (
        session_ledger.CoverageStatus.INCOMPLETE
        if omissions or findings
        else session_ledger.CoverageStatus.COMPLETE,
    )
)

_AUTHORITY_PROVENANCE_TABLE = (
    (session_ledger.EventKind.USER_MESSAGE, (), "native_root_user"),
    (session_ledger.EventKind.FORM_ANSWER, (), "paired_form_answer"),
    (
        session_ledger.EventKind.USER_MESSAGE,
        (("authority_provenance", "imported_history"),),
        "imported_history",
    ),
    (
        session_ledger.EventKind.USER_MESSAGE,
        (("authority_provenance", "invalid"),),
        "non_authoritative",
    ),
)
_REQUIREMENT_KIND_TABLE = (
    (
        "graphifyy only in pyproject.toml, never duplicated in mise",
        "dependency_ownership",
    ),
    ("Use the public Graphify SDK", "graphify_sdk"),
    ("Run the tests", "action"),
)
_CODEX_ROOT_KIND_TABLE = (
    ({"source": "desktop"}, "interactive"),
    ({"source": "exec"}, "exec_worker"),
    ({"source": "guardian review"}, "guardian"),
    ({"parent_thread_id": "parent", "source": "subagent"}, "subagent"),
    ({"source": "plugin"}, "plugin_task"),
    ({"source": "imported_history"}, "imported"),
    ({"source": "future"}, "unknown"),
)


@pytest.mark.parametrize(("kind", "metadata", "expected"), _AUTHORITY_PROVENANCE_TABLE)
def test_authority_provenance_table(
    kind: session_ledger.EventKind,
    metadata: tuple[tuple[str, str], ...],
    expected: str,
) -> None:
    event = session_ledger.CanonicalEvent(kind, "user", "text", _EVIDENCE, metadata)
    assert session_ledger.authority_provenance(event) == expected


@pytest.mark.parametrize(("statement", "expected"), _REQUIREMENT_KIND_TABLE)
def test_requirement_kind_table(statement: str, expected: str) -> None:
    assert session_ledger.requirement_kind(statement) == expected


@pytest.mark.parametrize(("meta", "expected"), _CODEX_ROOT_KIND_TABLE)
def test_codex_root_kind_table(meta: Mapping[str, object], expected: str) -> None:
    assert session_ledger.codex_root_kind(meta) == expected


def _source(
    name: str, provider: session_ledger.Provider
) -> session_ledger.TranscriptSource:
    return session_ledger.TranscriptSource(provider, FIXTURES / name)


@pytest.mark.parametrize(
    ("omissions", "high_severity_findings", "dispositions", "expected"),
    _COVERAGE_STATUS_TABLE,
)
def test_coverage_status_truth_table(
    omissions: tuple[str, ...],
    high_severity_findings: tuple[session_ledger.HighSeverityFinding, ...],
    dispositions: tuple[session_ledger.PreventionDisposition, ...],
    expected: session_ledger.CoverageStatus,
) -> None:
    coverage = session_ledger.RequirementCoverage(
        (), (), (), high_severity_findings, dispositions, (), (), "", omissions
    )
    assert coverage.status == expected


def test_codex_fixture_retains_every_requirement_surface_without_payload_leak() -> None:
    coverage = session_ledger.parse_transcripts(
        [_source("codex-root.jsonl", session_ledger.Provider.CODEX)]
    )

    statements = [item.statement for item in coverage.requirements]
    assert statements == [
        "Do not publish; evaluate CXDB first.",
        "None of the above",
        "user_note: research only",
    ]
    assert len(coverage.promises) == 1
    assert coverage.promises[0].status == session_ledger.ReviewStatus.UNREVIEWED
    assert coverage.requirements[0].authority_relevant
    attachments = [
        event
        for event in coverage.events
        if event.kind == session_ledger.EventKind.ATTACHMENT
    ]
    assert len(attachments) == 1
    assert attachments[0].attachment is not None
    assert (
        attachments[0].attachment.payload_sha256
        == hashlib.sha256(b"fixture-payload").hexdigest()
    )
    assert "fixture-payload" not in session_ledger.render_coverage(coverage)


def test_exact_missed_dependency_request_is_atomized_and_typed() -> None:
    coverage = session_ledger.parse_transcripts(
        [
            _source(
                "codex-missed-dependency-request.jsonl",
                session_ledger.Provider.CODEX,
            )
        ]
    )

    assert len(coverage.requirements) == 9
    ownership = next(
        item
        for item in coverage.requirements
        if item.kind == session_ledger.RequirementKind.DEPENDENCY_OWNERSHIP
    )
    assert ownership.target == "python dependency ownership"
    assert "pyproject.toml" in ownership.statement
    assert ownership.statement == (
        "graphifyy only in pyproject.toml/uv.lock via mise [deps.uv], "
        "never duplicated in mise tools/lock."
    )
    assert ownership.authority_provenance == (
        session_ledger.AuthorityProvenance.NATIVE_ROOT_USER
    )
    assert ownership.atom_index == 8
    assert ownership.parent_statement_sha256
    assert any(
        item.kind == session_ledger.RequirementKind.GRAPHIFY_SDK
        for item in coverage.requirements
    )
    assert any(
        event.kind == session_ledger.EventKind.COMPACTION for event in coverage.events
    )
    sdk = next(
        item
        for item in coverage.requirements
        if item.kind == session_ledger.RequirementKind.GRAPHIFY_SDK
    )
    assert sdk.requirement_id != ownership.requirement_id
    assert sdk.atom_index == 9
    assert sdk.parent_statement_sha256 == ownership.parent_statement_sha256


def test_semantic_disposition_needs_evidence_beyond_an_issue_carrier() -> None:
    coverage = session_ledger.parse_transcripts(
        [
            _source(
                "codex-missed-dependency-request.jsonl",
                session_ledger.Provider.CODEX,
            )
        ]
    )
    claim = coverage.requirements[0]
    carrier_only = session_ledger.SemanticDisposition(
        claim.requirement_id,
        session_ledger.ReviewStatus.SATISFIED,
        "Tracked by issue 715.",
        ("issue:#715",),
    )
    still_open = session_ledger.apply_semantic_dispositions(coverage, (carrier_only,))
    assert still_open.requirements[0].status == session_ledger.ReviewStatus.UNREVIEWED

    verified = replace(carrier_only, receipt_refs=("issue:#715", "test:focused"))
    closed = session_ledger.apply_semantic_dispositions(coverage, (verified,))
    assert closed.requirements[0].status == session_ledger.ReviewStatus.SATISFIED
    assert closed.requirements[0].receipt_refs == ("issue:#715", "test:focused")


def test_provider_qualified_ids_do_not_collide_and_claude_string_is_authority(
    tmp_path: Path,
) -> None:
    text = "Preserve this requirement."
    codex = tmp_path / "codex.jsonl"
    codex.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"type": "session_meta", "payload": {"id": "same", "cwd": "/repo"}},
                {
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": text},
                },
            )
        )
    )
    claude = tmp_path / "claude.jsonl"
    claude.write_text(
        json.dumps(
            {
                "type": "user",
                "sessionId": "same",
                "uuid": "same-event",
                "message": {"content": text},
            }
        )
        + "\n"
    )

    coverage = session_ledger.parse_transcripts(
        [
            session_ledger.TranscriptSource(session_ledger.Provider.CODEX, codex),
            session_ledger.TranscriptSource(session_ledger.Provider.CLAUDE, claude),
        ]
    )

    matching = [item for item in coverage.requirements if item.statement == text]
    assert len(matching) == 2
    assert len({item.requirement_id for item in matching}) == 2
    assert {item.evidence.source_id for item in matching} == {
        "codex:same",
        "claude:same",
    }


def test_imported_codex_history_is_registered_but_never_duplicates_authority(
    tmp_path: Path,
) -> None:
    path = tmp_path / "imported.jsonl"
    text = "Push the release."
    path.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "imported",
                        "cwd": "/repo",
                        "source": "imported_history",
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": text},
                },
            )
        )
    )
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert coverage.requirements == ()
    assert coverage.import_registry[0].root_kind == session_ledger.RootKind.IMPORTED
    assert coverage.import_registry[0].content_sha256


def test_compaction_history_deduplicates_native_message_id() -> None:
    coverage = session_ledger.parse_transcripts(
        [_source("codex-root.jsonl", session_ledger.Provider.CODEX)]
    )
    matching = [
        event
        for event in coverage.events
        if event.kind == session_ledger.EventKind.USER_MESSAGE
    ]
    assert len(matching) == 1
    assert any(
        event.kind == session_ledger.EventKind.COMPACTION for event in coverage.events
    )


@pytest.mark.parametrize("mutation", ["duplicate-id", "unknown-type", "partial"])
def test_compaction_replacement_is_atomic_or_incomplete(
    tmp_path: Path, mutation: str
) -> None:
    first = {"type": "message", "id": "one", "role": "assistant", "content": []}
    second = {"type": "message", "id": "two", "role": "assistant", "content": []}
    if mutation == "duplicate-id":
        second["id"] = "one"
    elif mutation == "unknown-type":
        second["type"] = "future_item"
    history: list[object] = [first, second]
    if mutation == "partial":
        history.append("not-an-item")
    rows = [
        {"type": "session_meta", "payload": {"id": "compact", "cwd": "/repo"}},
        {
            "type": "compacted",
            "payload": {
                "window_id": "window-1",
                "previous_window_id": "",
                "window_number": 1,
                "replacement_history": history,
                "message": "opaque",
            },
        },
    ]
    path = tmp_path / "compact.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE
    assert not any(
        event.evidence.event_id in {"one", "two"} for event in coverage.events
    )


def test_codex_lineage_uses_native_parent_fields() -> None:
    coverage = session_ledger.parse_transcripts(
        [
            _source("codex-root.jsonl", session_ledger.Provider.CODEX),
            _source("codex-child.jsonl", session_ledger.Provider.CODEX),
        ]
    )
    child = next(
        item for item in coverage.lineage if item.source_id.endswith("child-session")
    )
    assert child.session_id == "root-session"
    assert child.parent_id == "root-session"
    assert child.agent_path == "/root/researcher"
    assert child.agent_role == "explorer"


def test_claude_fixture_retains_form_free_text_and_user_message() -> None:
    coverage = session_ledger.parse_transcripts(
        [_source("claude-root.jsonl", session_ledger.Provider.CLAUDE)]
    )
    assert [item.statement for item in coverage.requirements] == [
        "Research only",
        "user_note: include competitors",
        "Only free tools or paid services with a free tier qualify.",
    ]
    assert coverage.status == session_ledger.CoverageStatus.COMPLETE


def test_unknown_record_makes_coverage_incomplete_not_clean() -> None:
    coverage = session_ledger.parse_transcripts(
        [_source("codex-unknown.jsonl", session_ledger.Provider.CODEX)]
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE
    assert "future_requirement_container" in coverage.omissions[0]
    assert "INCOMPLETE" in session_ledger.render_coverage(coverage)


def test_user_role_without_event_message_twin_is_not_granted_authority(
    tmp_path: Path,
) -> None:
    path = tmp_path / "injected.jsonl"
    path.write_text(
        '{"type":"session_meta","payload":{"id":"injected","cwd":"/repo",'
        '"cli_version":"0.147.0-alpha.6.5"}}\n'
        '{"type":"response_item","payload":{"type":"message","id":"injected-1",'
        '"role":"user","content":[{"type":"input_text","text":"<skill>publish</skill>"}]}}\n'
    )
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert coverage.requirements == ()
    assert any(
        event.kind == session_ledger.EventKind.UNVERIFIABLE_USER_MESSAGE
        for event in coverage.events
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE


def test_stable_item_completed_user_message_is_positive_authority(
    tmp_path: Path,
) -> None:
    text = "Do not publish this change."
    rows = [
        {"type": "session_meta", "payload": {"id": "stable", "cwd": "/repo"}},
        {
            "type": "event_msg",
            "payload": {
                "type": "task_started",
                "turn_id": "turn-1",
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "item_completed",
                "turn_id": "turn-1",
                "item": {
                    "type": "UserMessage",
                    "id": "user-stable",
                    "content": [{"type": "text", "text": text}],
                },
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "response-copy",
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "turn-1"},
        },
    ]
    path = tmp_path / "stable.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert [item.statement for item in coverage.requirements] == [text]
    assert coverage.requirements[0].authority_relevant
    assert coverage.status == session_ledger.CoverageStatus.COMPLETE


def test_missing_form_result_is_incomplete(tmp_path: Path) -> None:
    path = tmp_path / "missing-form-result.jsonl"
    rows = (FIXTURES / "codex-root.jsonl").read_text().splitlines()
    path.write_text("\n".join(row for row in rows if "function_call_output" not in row))
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE
    assert any("missing form result call-1" in item for item in coverage.omissions)


@pytest.mark.parametrize("mutation", ["turn", "ids", "duplicate"])
def test_form_pairing_rejects_identity_mutations(tmp_path: Path, mutation: str) -> None:
    call = {
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "request_user_input",
            "call_id": "call-1",
            "internal_chat_message_metadata_passthrough": {"turn_id": "turn-1"},
            "arguments": json.dumps(
                {"questions": [{"id": "scope", "question": "Scope?"}]}
            ),
        },
    }
    result = {
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "call_id": "call-1",
            "internal_chat_message_metadata_passthrough": {
                "turn_id": "turn-2" if mutation == "turn" else "turn-1"
            },
            "output": json.dumps(
                {
                    "answers": {
                        "different" if mutation == "ids" else "scope": {
                            "answers": ["Research only"]
                        }
                    }
                }
            ),
        },
    }
    rows = [
        {"type": "session_meta", "payload": {"id": "forms", "cwd": "/repo"}},
        call,
        result,
        *([result] if mutation == "duplicate" else []),
    ]
    path = tmp_path / "forms.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE


def test_alpha_form_shape_is_retained_but_needs_probe(tmp_path: Path) -> None:
    path = tmp_path / "alpha-form.jsonl"
    data = (
        (FIXTURES / "codex-root.jsonl")
        .read_text()
        .replace('"cli_version":"0.147.0"', '"cli_version":"0.147.0-alpha.6.5"')
    )
    path.write_text(data)
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert "None of the above" in {
        requirement.statement for requirement in coverage.requirements
    }
    assert any("needs an alpha runtime probe" in item for item in coverage.omissions)


def test_cutoff_accepts_append_and_rejects_prefix_rewrite(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    original = (FIXTURES / "codex-root.jsonl").read_bytes()
    path.write_bytes(original)
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    cutoff = coverage.cutoffs[0]
    assert cutoff.final_ordinal == "7"
    assert cutoff.final_timestamp == "2026-08-10T17:04:05Z"
    assert not cutoff.open_turn
    path.write_bytes(original + b'{"type":"event_msg","payload":{}}\n')
    assert cutoff.matches(path)
    changed = bytearray(path.read_bytes())
    changed[10] = ord("9") if changed[10] != ord("9") else ord("8")
    path.write_bytes(changed)
    assert not cutoff.matches(path)


def test_manifest_is_deterministic_and_path_independent(tmp_path: Path) -> None:
    left = tmp_path / "left.jsonl"
    right = tmp_path / "nested" / "right.jsonl"
    right.parent.mkdir()
    data = (FIXTURES / "codex-root.jsonl").read_bytes()
    left.write_bytes(data)
    right.write_bytes(data)
    first = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, left)]
    )
    second = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, right)]
    )
    assert first.manifest_sha256 == second.manifest_sha256


def test_codex_discovery_selects_root_and_children_by_native_session_id(
    tmp_path: Path,
) -> None:
    repo = Path("/repo")
    old = tmp_path / "2026" / "old.jsonl"
    root = tmp_path / "2026" / "root.jsonl"
    child = tmp_path / "2026" / "child.jsonl"
    root.parent.mkdir(parents=True)
    old.write_text(
        '{"type":"session_meta","payload":{"session_id":"old","id":"old",'
        '"timestamp":"2025-01-01","cwd":"/repo","thread_source":"user"}}\n'
    )
    root.write_bytes((FIXTURES / "codex-root.jsonl").read_bytes())
    child.write_bytes((FIXTURES / "codex-child.jsonl").read_bytes())
    assert session_ledger.discover_codex_transcripts(repo, base=tmp_path, limit=1) == [
        child,
        root,
    ]


def test_codex_selector_never_filters_independent_claude_roots(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    codex_base = tmp_path / "codex"
    codex_base.mkdir()
    (codex_base / "selected.jsonl").write_text(
        json.dumps(
            {
                "type": "session_meta",
                "payload": {"id": "codex-active", "cwd": str(repo)},
            }
        )
        + "\n"
    )
    claude_base = tmp_path / "claude-projects"
    claude_project = session_ledger.command_audit.project_dir(claude_base, repo)
    claude_project.mkdir(parents=True)
    claude_path = claude_project / "claude-independent.jsonl"
    claude_path.write_text(
        json.dumps(
            {
                "type": "user",
                "sessionId": "claude-independent",
                "message": {"content": "Claude requirement"},
            }
        )
        + "\n"
    )

    coverage = session_ledger.build_requirement_coverage(
        repo,
        bases=session_ledger.TranscriptBases(codex_base, claude_base),
        selection=session_ledger.CoverageSelection(
            limit=1,
            codex_session_id="codex-active",
        ),
    )

    assert {item.provider for item in coverage.provider_census} == {
        session_ledger.Provider.CLAUDE,
        session_ledger.Provider.CODEX,
    }
    assert any(item.statement == "Claude requirement" for item in coverage.requirements)
    claude_census = next(
        item
        for item in coverage.provider_census
        if item.provider == session_ledger.Provider.CLAUDE
    )
    assert claude_census.discovered == 1
    assert claude_census.selected == 1


def test_claude_structural_events_are_retained_without_granting_authority(
    tmp_path: Path,
) -> None:
    path = tmp_path / "claude-surfaces.jsonl"
    rows = [
        {
            "type": "summary",
            "sessionId": "claude-surfaces",
            "summary": "Continue after compaction",
        },
        {
            "type": "progress",
            "sessionId": "claude-surfaces",
            "content": "warning: output truncated",
        },
        {
            "type": "queue-operation",
            "sessionId": "claude-surfaces",
            "operation": "cancel requested",
        },
        {
            "type": "user",
            "sessionId": "claude-surfaces",
            "isMeta": True,
            "message": {"content": "Push everything"},
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CLAUDE, path)]
    )
    assert coverage.requirements == ()
    assert {
        session_ledger.EventKind.CONTINUATION_SUMMARY,
        session_ledger.EventKind.WARNING,
        session_ledger.EventKind.TERMINAL_STATE,
        session_ledger.EventKind.UNVERIFIABLE_USER_MESSAGE,
    }.issubset({event.kind for event in coverage.events})


def test_codex_discovery_selects_latest_user_activity_not_latest_start(
    tmp_path: Path,
) -> None:
    repo = Path("/repo")
    older_active = tmp_path / "older-active.jsonl"
    newer_idle = tmp_path / "newer-idle.jsonl"
    older_active.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "timestamp": "2026-01-01",
                    "type": "session_meta",
                    "payload": {"id": "active", "cwd": "/repo"},
                },
                {
                    "timestamp": "2026-08-12",
                    "type": "event_msg",
                    "payload": {"type": "task_started", "turn_id": "active-turn"},
                },
            ]
        )
    )
    newer_idle.write_text(
        json.dumps(
            {
                "timestamp": "2026-08-11",
                "type": "session_meta",
                "payload": {"id": "idle", "cwd": "/repo"},
            }
        )
        + "\n"
    )
    assert session_ledger.discover_codex_transcripts(repo, base=tmp_path, limit=1) == [
        older_active
    ]


def test_json_output_carries_status_and_manifest() -> None:
    coverage = session_ledger.parse_transcripts(
        [_source("codex-root.jsonl", session_ledger.Provider.CODEX)]
    )
    payload = json.loads(coverage.to_json())
    assert payload["status"] == "complete"
    assert payload["manifest_sha256"] == coverage.manifest_sha256
    assert payload["cutoff_count"] == 1
    assert payload["cutoff_prefix_sample"] == [coverage.cutoffs[0].prefix_sha256]
    assert (
        payload["cutoff_manifest_sha256"]
        == hashlib.sha256(coverage.cutoffs_to_json().encode()).hexdigest()
    )
    assert "events" not in payload
    assert len(coverage.to_json().encode()) <= session_ledger.MAX_RENDER_BYTES


def test_evidence_references_large_cutoff_manifest_without_embedding_it() -> None:
    coverage = session_ledger.parse_transcripts(
        [_source("codex-root.jsonl", session_ledger.Provider.CODEX)]
    )
    original = coverage.cutoffs[0]
    expanded = replace(
        coverage,
        cutoffs=tuple(
            replace(
                original,
                source_id=f"source-{index}",
                source_path=f"/private/transcripts/session-{index:03d}.jsonl",
            )
            for index in range(240)
        ),
    )

    payload = json.loads(expanded.to_json())
    cutoff_index = json.loads(expanded.cutoffs_to_json())
    segments = expanded.cutoff_segments_to_json()

    assert payload["cutoff_count"] == 240
    assert "cutoffs" not in payload
    assert len(expanded.to_json().encode()) <= session_ledger.MAX_RENDER_BYTES
    assert len(expanded.cutoffs_to_json().encode()) <= session_ledger.MAX_RENDER_BYTES
    assert len(segments) > 1
    assert all(
        len(segment.encode()) <= session_ledger.MAX_RENDER_BYTES for segment in segments
    )
    assert sum(len(json.loads(segment)["cutoffs"]) for segment in segments) == 240
    assert cutoff_index["segment_count"] == len(segments)
    segment_digests = [hashlib.sha256(item.encode()).hexdigest() for item in segments]
    assert cutoff_index["segments"] == [
        {
            "suffix": f".{index:04d}.json",
            "sha256": digest,
            "cutoff_count": len(json.loads(segment)["cutoffs"]),
        }
        for index, (segment, digest) in enumerate(
            zip(segments, segment_digests, strict=True), start=1
        )
    ]
    assert (
        cutoff_index["segment_sha256_manifest"]
        == hashlib.sha256("\n".join(segment_digests).encode()).hexdigest()
    )
    assert (
        payload["cutoff_manifest_sha256"]
        == hashlib.sha256(expanded.cutoffs_to_json().encode()).hexdigest()
    )


def test_source_root_mismatch_is_incomplete_not_an_empty_success(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    coverage = session_ledger.build_requirement_coverage(
        repo,
        bases=session_ledger.TranscriptBases(FIXTURES, tmp_path / "no-claude"),
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE
    assert coverage.recorded_cwd == str(repo.resolve())
    assert any(
        "no transcripts matched recorded cwd" in item for item in coverage.omissions
    )


def test_external_attachment_hashes_bytes_and_missing_file_fails_closed(
    tmp_path: Path,
) -> None:
    attachment = tmp_path / "evidence.txt"
    attachment.write_bytes(b"first")
    transcript = tmp_path / "attachment.jsonl"

    def write_transcript() -> None:
        tag = f'<attachment name="evidence" path="{attachment}">'
        records = [
            {
                "type": "session_meta",
                "payload": {
                    "id": "attachments",
                    "cwd": "/repo",
                    "cli_version": "0.147.0",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "id": "user-a",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": tag},
                        {"type": "input_file", "path": str(attachment)},
                    ],
                },
            },
            {
                "type": "event_msg",
                "payload": {"type": "user_message", "message": tag},
            },
        ]
        transcript.write_text("\n".join(json.dumps(record) for record in records))

    write_transcript()
    source = session_ledger.TranscriptSource(session_ledger.Provider.CODEX, transcript)
    first = session_ledger.parse_transcripts([source])
    first_attachment = next(
        event.attachment for event in first.events if event.attachment
    )
    assert sum(event.attachment is not None for event in first.events) == 1
    assert first_attachment.payload_sha256 == hashlib.sha256(b"first").hexdigest()
    assert first.status == session_ledger.CoverageStatus.COMPLETE

    attachment.write_bytes(b"second")
    second = session_ledger.parse_transcripts([source])
    second_attachment = next(
        event.attachment for event in second.events if event.attachment
    )
    assert second_attachment.payload_sha256 == hashlib.sha256(b"second").hexdigest()
    assert second_attachment.payload_sha256 != first_attachment.payload_sha256

    attachment.unlink()
    missing = session_ledger.parse_transcripts([source])
    assert missing.status == session_ledger.CoverageStatus.INCOMPLETE
    assert any("attachment bytes unavailable" in item for item in missing.omissions)


def test_attachment_symlink_and_oversize_payload_fail_closed(tmp_path: Path) -> None:
    target = tmp_path / "target.bin"
    target.write_bytes(b"content")
    link = tmp_path / "link.bin"
    link.symlink_to(target)
    transcript = tmp_path / "attachment-policy.jsonl"

    def coverage_for(path: Path) -> session_ledger.RequirementCoverage:
        records = [
            {"type": "session_meta", "payload": {"id": "policy", "cwd": "/repo"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "id": "user-policy",
                    "role": "user",
                    "content": [{"type": "input_file", "path": str(path)}],
                },
            },
        ]
        transcript.write_text("\n".join(json.dumps(row) for row in records))
        return session_ledger.parse_transcripts(
            [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, transcript)]
        )

    assert coverage_for(link).status == session_ledger.CoverageStatus.INCOMPLETE
    target.write_bytes(b"x" * (session_ledger.MAX_ATTACHMENT_BYTES + 1))
    assert coverage_for(target).status == session_ledger.CoverageStatus.INCOMPLETE


def test_opaque_payloads_are_digest_only_in_json_and_markdown(tmp_path: Path) -> None:
    opaque_payload = "HOSTILE-OPAQUE-PAYLOAD"
    data_url = "data:text/plain;base64,SE9TVElMRS1PUEFRVUUtUEFZTE9BRA=="
    user_text = f"Inspect {data_url}"
    records = [
        {
            "type": "session_meta",
            "payload": {
                "id": "hostile",
                "cwd": "/repo",
                "cli_version": "0.147.0",
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "user-hostile",
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "user_message", "message": user_text},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "agent_message",
                "id": "agent-hostile",
                "encrypted_content": opaque_payload,
            },
        },
        {
            "type": "compacted",
            "payload": {
                "message": opaque_payload,
                "window_id": "window-1",
                "previous_window_id": "",
                "window_number": 1,
                "replacement_history": [
                    {
                        "type": "custom_tool_call_output",
                        "call_id": "opaque-call",
                        "output": opaque_payload,
                    }
                ],
            },
        },
    ]
    path = tmp_path / "hostile.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in records))
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    rendered = coverage.to_json() + session_ledger.render_coverage(coverage)
    assert opaque_payload not in rendered
    assert "data:text/plain;base64" not in rendered
    assert hashlib.sha256(opaque_payload.encode()).hexdigest() in rendered
    assert "opaque encrypted agent payload" in rendered


@pytest.mark.parametrize(
    ("message", "category"),
    [
        (
            "The credential was available through fnox but the launcher was missing.",
            "credential-launcher",
        ),
        (
            "Inherited GIT_DIR escaped into a fixture and contaminated the hook.",
            "git-hook-contamination",
        ),
    ],
)
def test_high_severity_one_offs_do_not_require_recurrence(
    tmp_path: Path, message: str, category: str
) -> None:
    path = tmp_path / "one-off.jsonl"
    records = [
        {
            "type": "session_meta",
            "payload": {"id": "one-off", "cwd": "/repo", "cli_version": "0.147.0"},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "assistant-risk",
                "role": "assistant",
                "content": [{"type": "output_text", "text": message}],
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records))
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert [item.category for item in coverage.high_severity_findings] == [category]
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE


def test_confirmed_finding_requires_complete_prevention_disposition() -> None:
    missing = session_ledger.RequirementCoverage(
        (), (), (), (_CONFIRMED,), (), (), (), "", ()
    )
    complete = session_ledger.RequirementCoverage(
        (), (), (), (_CONFIRMED,), (_DISPOSITION,), (), (), "", ()
    )
    assert missing.status == session_ledger.CoverageStatus.INCOMPLETE
    assert "lacks prevention disposition" in session_ledger.render_coverage(missing)
    assert complete.status == session_ledger.CoverageStatus.INCOMPLETE


def test_unreviewed_high_severity_finding_also_requires_prevention() -> None:
    unreviewed = session_ledger.HighSeverityFinding(
        "risk-u", "credential-launcher", "detected", _EVIDENCE
    )
    coverage = session_ledger.RequirementCoverage(
        (), (), (), (unreviewed,), (), (), (), "", ()
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE
    assert session_ledger.disposition_omissions(coverage)


def test_persisted_disposition_never_converges_or_authorizes_complete() -> None:
    coverage = session_ledger.RequirementCoverage(
        (), (), (), (_CONFIRMED,), (_DISPOSITION,), (), (), "", ()
    )
    first = session_ledger.advance_iteration(coverage, number=1)
    second = session_ledger.advance_iteration(
        coverage, number=2, previous_disposition_ids=first.disposition_ids
    )
    assert first.action == session_ledger.IterationAction.NEEDS_AGENT_ACTION
    assert second.action == session_ledger.IterationAction.NEEDS_AGENT_ACTION


def test_iteration_without_disposition_needs_agent_action() -> None:
    coverage = session_ledger.RequirementCoverage(
        (), (), (), (_CONFIRMED,), (), (), (), "", ()
    )
    iteration = session_ledger.advance_iteration(coverage, number=1)
    assert iteration.action == session_ledger.IterationAction.NEEDS_AGENT_ACTION
    assert iteration.unresolved_finding_ids == ("risk-1",)


def test_iteration_surfaces_all_unreviewed_and_prioritizes_candidates() -> None:
    ordinary = session_ledger.RequirementEntry(
        "req-ordinary",
        "Review the existing issues before changing code.",
        _EVIDENCE,
        session_ledger.EventKind.USER_MESSAGE,
        authority_relevant=False,
    )
    tracker = session_ledger.RequirementEntry(
        "req-tracker",
        "Find requests we missed and make GitHub issues so we do not forget.",
        _EVIDENCE,
        session_ledger.EventKind.USER_MESSAGE,
        authority_relevant=False,
    )
    coverage = session_ledger.RequirementCoverage(
        (), (ordinary, tracker), (), (), (), (), (), "", ()
    )

    iteration = session_ledger.advance_iteration(coverage, number=1)

    assert iteration.action == session_ledger.IterationAction.NEEDS_AGENT_ACTION
    assert iteration.unreviewed_requirement_ids == ("req-ordinary", "req-tracker")
    assert iteration.issue_candidate_requirement_ids == ("req-tracker",)


def test_satisfied_tracker_request_does_not_block_iteration() -> None:
    tracker = session_ledger.RequirementEntry(
        "req-tracker",
        "Track this request in an issue.",
        _EVIDENCE,
        session_ledger.EventKind.USER_MESSAGE,
        authority_relevant=False,
        status=session_ledger.ReviewStatus.SATISFIED,
    )
    coverage = session_ledger.RequirementCoverage(
        (), (tracker,), (), (), (), (), (), "", ()
    )

    iteration = session_ledger.advance_iteration(coverage, number=1)

    assert iteration.action == session_ledger.IterationAction.CONVERGED
    assert iteration.unreviewed_requirement_ids == ()
    assert iteration.issue_candidate_requirement_ids == ()


def test_agent_review_envelope_is_not_an_actionable_user_request() -> None:
    injected = session_ledger.RequirementEntry(
        "req-injected",
        "The following is the Codex agent history whose request action you are "
        "assessing. Find missed issues.",
        _EVIDENCE,
        session_ledger.EventKind.USER_MESSAGE,
        authority_relevant=True,
    )
    coverage = session_ledger.RequirementCoverage(
        (), (injected,), (), (), (), (), (), "", ()
    )

    iteration = session_ledger.advance_iteration(coverage, number=1)

    assert iteration.unreviewed_requirement_ids == ()
    assert iteration.issue_candidate_requirement_ids == ()
    assert iteration.action == session_ledger.IterationAction.CONVERGED


def test_resolved_forgotten_command_is_not_an_issue_candidate() -> None:
    resolved = session_ledger.RequirementEntry(
        "req-resolved",
        "I had forgotten the command syntax, but it is resolved.",
        _EVIDENCE,
        session_ledger.EventKind.USER_MESSAGE,
        authority_relevant=False,
    )
    coverage = session_ledger.RequirementCoverage(
        (), (resolved,), (), (), (), (), (), "", ()
    )

    iteration = session_ledger.advance_iteration(coverage, number=1)

    assert iteration.action == session_ledger.IterationAction.NEEDS_AGENT_ACTION
    assert iteration.unreviewed_requirement_ids == ("req-resolved",)
    assert iteration.issue_candidate_requirement_ids == ()


def test_paraphrased_missed_request_still_blocks_without_keyword_hint() -> None:
    paraphrase = session_ledger.RequirementEntry(
        "req-paraphrase",
        "Capture every overlooked ask in the tracker.",
        _EVIDENCE,
        session_ledger.EventKind.USER_MESSAGE,
        authority_relevant=False,
    )
    coverage = session_ledger.RequirementCoverage(
        (), (paraphrase,), (), (), (), (), (), "", ()
    )

    iteration = session_ledger.advance_iteration(coverage, number=1)

    assert iteration.unreviewed_requirement_ids == ("req-paraphrase",)
    assert iteration.issue_candidate_requirement_ids == ()
    assert iteration.action == session_ledger.IterationAction.NEEDS_AGENT_ACTION


def test_codex_developer_message_is_known_context_not_user_authority(
    tmp_path: Path,
) -> None:
    path = tmp_path / "developer.jsonl"
    records = [
        {
            "type": "session_meta",
            "payload": {"id": "developer", "cwd": "/repo", "cli_version": "0.147.0"},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": "internal policy"}],
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records))

    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )

    assert coverage.omissions == ()
    assert coverage.requirements == ()


def test_markdown_output_has_a_hard_global_byte_cap() -> None:
    requirements = tuple(
        session_ledger.RequirementEntry(
            requirement_id=f"req-{index}",
            statement="x" * 500,
            evidence=_EVIDENCE,
            source_kind=session_ledger.EventKind.USER_MESSAGE,
            authority_relevant=False,
        )
        for index in range(2_000)
    )
    coverage = session_ledger.RequirementCoverage(
        (), requirements, (), (), (), (), (), "", ()
    )
    rendered = session_ledger.render_coverage(coverage)
    assert len(rendered.encode()) <= session_ledger.MAX_RENDER_BYTES
    assert "TRUNCATED" in rendered


def test_saturated_report_keeps_selection_certification_in_fixed_header() -> None:
    requirements = tuple(
        session_ledger.RequirementEntry(
            requirement_id=f"req-{index}",
            statement="x" * 500,
            evidence=_EVIDENCE,
            source_kind=session_ledger.EventKind.USER_MESSAGE,
            authority_relevant=False,
        )
        for index in range(2_000)
    )
    coverage = session_ledger.RequirementCoverage(
        (),
        requirements,
        (),
        (),
        (),
        (),
        (),
        "",
        (),
        session_ledger.SelectionCertification.UNCERTIFIED_ACTIVITY_FALLBACK,
    )
    rendered = session_ledger.render_coverage(coverage)
    assert len(rendered.encode()) == session_ledger.MAX_RENDER_BYTES
    assert "Active selection: **UNCERTIFIED_ACTIVITY_FALLBACK**" in rendered[:500]
    assert (
        json.loads(coverage.to_json())["selection_certification"]
        == "uncertified_activity_fallback"
    )
    iteration = session_ledger.advance_iteration(coverage, number=1)
    assert (
        json.loads(iteration.to_json())["selection_certification"]
        == "uncertified_activity_fallback"
    )


def _write_hashed_json(path: Path, payload: Mapping[str, object]) -> dict[str, str]:
    path.write_text(json.dumps(payload, sort_keys=True))
    return {
        "path": str(path.relative_to(path.parents[1])),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _valid_disposition(repo: Path) -> tuple[Path, dict[str, object]]:
    receipts = repo / "receipts"
    receipts.mkdir()
    carrier = repo / "carrier.py"
    carrier.write_text("PREVENTION = True\n")
    carrier_spec = {
        "path": "carrier.py",
        "sha256": hashlib.sha256(carrier.read_bytes()).hexdigest(),
    }
    command_specs: dict[str, dict[str, str]] = {}
    for role, argv in (
        ("mutation", ["mise", "run", "mutation"]),
        ("gate", ["mise", "run", "lint"]),
    ):
        command_specs[role] = _write_hashed_json(
            receipts / f"{role}.json",
            {
                "schema": "session-review.runner-attestation.v1",
                "status": "ATTESTED",
                "role": role,
                "runner": "mise-session-review-gate",
                "run_id": "test-run",
                "nonce": "test-nonce",
                "argv": argv,
                "rc": 0,
                "started_at": "2026-08-11T00:00:00Z",
                "finished_at": "2026-08-11T00:00:01Z",
                "artifact_sha256": "a" * 64,
                "test_signed": True,
            },
        )
    readback = {
        "number": 123,
        "html_url": "https://github.com/example/repo/issues/123",
        "body": "verified body",
    }
    readback_spec = _write_hashed_json(receipts / "github-readback.json", readback)
    readback_body = json.dumps(readback, separators=(",", ":"), sort_keys=True).encode()
    api_url = "https://api.github.com/repos/example/repo/issues/123"
    issue_spec = _write_hashed_json(
        receipts / "issue.json",
        {
            "schema": "session-review.runner-attestation.v1",
            "status": "ATTESTED",
            "role": "github_readback",
            "runner": "mise-session-review-gate",
            "run_id": "test-run",
            "nonce": "test-nonce",
            "argv": ["fnox", "exec", "--", "gh", "api", api_url],
            "rc": 0,
            "started_at": "2026-08-11T00:00:02Z",
            "finished_at": "2026-08-11T00:00:03Z",
            "artifact_sha256": "b" * 64,
            "test_signed": True,
            "api_url": api_url,
            "html_url": readback["html_url"],
            "issue_id": 123,
            "body_sha256": hashlib.sha256(readback_body).hexdigest(),
            "readback": readback_spec,
        },
    )
    payload: dict[str, object] = {
        "finding_id": "risk-1",
        "carrier": carrier_spec,
        "mutation_receipt": command_specs["mutation"],
        "gate_receipt": command_specs["gate"],
        "issue_receipt": issue_spec,
    }
    path = repo / "dispositions.json"
    path.write_text(json.dumps([payload]))
    return path, payload


def test_hash_verified_prevention_receipts_are_accepted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    path, _ = _valid_disposition(repo)
    dispositions = session_ledger.load_dispositions(
        path, repo_root=repo, attestation=_ATTESTATION
    )
    assert dispositions[0].audit_evidence_complete
    assert not dispositions[0].complete


def test_production_loader_rejects_test_signed_or_missing_runner_identity(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    path, _ = _valid_disposition(repo)
    with pytest.raises(ValueError, match="run-id"):
        session_ledger.load_dispositions(path, repo_root=repo)
    with pytest.raises(ValueError, match="ATTESTED"):
        session_ledger.load_dispositions(
            path,
            repo_root=repo,
            attestation=session_ledger.ReceiptAttestation("test-run", "test-nonce"),
        )


def test_persisted_forgery_cannot_complete_after_runner_context_exists(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    path, _ = _valid_disposition(repo)
    session_ledger.session_gate.initialize(repo, "live-context")
    with pytest.raises(ValueError, match="ATTESTED"):
        session_ledger.load_dispositions(path, repo_root=repo, run_id="live-context")
    forged = session_ledger.PreventionDisposition(
        "risk-1", "carrier", "mutation", "gate", "issue", attested=True
    )
    coverage = session_ledger.RequirementCoverage(
        (), (), (), (_CONFIRMED,), (forged,), (), (), "", ()
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE


@pytest.mark.parametrize(
    "field",
    ["carrier", "mutation_receipt", "gate_receipt", "issue_receipt"],
)
def test_mutating_away_any_prevention_receipt_is_rejected(
    tmp_path: Path, field: str
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    path, payload = _valid_disposition(repo)
    payload[field] = ""
    path.write_text(json.dumps([payload]))
    with pytest.raises((TypeError, ValueError)):
        session_ledger.load_dispositions(path, repo_root=repo, attestation=_ATTESTATION)


@pytest.mark.parametrize(
    ("target", "mutation"),
    [
        ("carrier", "sha256"),
        ("mutation_receipt", "sha256"),
        ("gate_receipt", "sha256"),
        ("issue_receipt", "sha256"),
    ],
)
def test_forged_artifact_hashes_are_rejected(
    tmp_path: Path, target: str, mutation: str
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    path, payload = _valid_disposition(repo)
    spec = payload[target]
    assert isinstance(spec, dict)
    spec[mutation] = "0" * 64
    path.write_text(json.dumps([payload]))
    with pytest.raises(ValueError, match="sha256"):
        session_ledger.load_dispositions(path, repo_root=repo, attestation=_ATTESTATION)


def test_unverified_github_declaration_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    path, payload = _valid_disposition(repo)
    issue_spec = payload["issue_receipt"]
    assert isinstance(issue_spec, dict)
    issue_path = repo / str(issue_spec["path"])
    issue = json.loads(issue_path.read_text())
    issue["status"] = "DECLARED"
    issue_spec.update(_write_hashed_json(issue_path, issue))
    path.write_text(json.dumps([payload]))
    with pytest.raises(ValueError, match="ATTESTED"):
        session_ledger.load_dispositions(path, repo_root=repo, attestation=_ATTESTATION)


@pytest.mark.parametrize(
    ("field", "value"), [("status", "PASS"), ("run_id", "forged-run")]
)
def test_forged_command_receipt_is_rejected(
    tmp_path: Path, field: str, value: str
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    path, payload = _valid_disposition(repo)
    spec = payload["mutation_receipt"]
    assert isinstance(spec, dict)
    receipt_path = repo / str(spec["path"])
    receipt = json.loads(receipt_path.read_text())
    receipt[field] = value
    spec.update(_write_hashed_json(receipt_path, receipt))
    path.write_text(json.dumps([payload]))
    with pytest.raises(ValueError, match="ATTESTED"):
        session_ledger.load_dispositions(path, repo_root=repo, attestation=_ATTESTATION)


def test_tool_call_result_and_terminal_state_are_structural_and_bounded(
    tmp_path: Path,
) -> None:
    opaque_text = "OPAQUE-TOOL-PAYLOAD"
    records = [
        {"type": "session_meta", "payload": {"id": "tools", "cwd": "/repo"}},
        {
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": "turn-1"},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "call_id": "tool-1",
                "name": "exec",
                "arguments": opaque_text,
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": "tool-1",
                "output": opaque_text,
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "turn-1"},
        },
    ]
    path = tmp_path / "tools.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in records))
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    kinds = {event.kind for event in coverage.events}
    assert session_ledger.EventKind.TOOL_CALL in kinds
    assert session_ledger.EventKind.TOOL_RESULT in kinds
    assert session_ledger.EventKind.TERMINAL_STATE in kinds
    assert opaque_text not in coverage.to_json()
    assert coverage.status == session_ledger.CoverageStatus.COMPLETE


@pytest.mark.parametrize("mutation", ["open", "complete-without-start", "tool-turn"])
def test_per_turn_terminal_and_tool_automaton_rejects_mutations(
    tmp_path: Path, mutation: str
) -> None:
    rows = [
        {"type": "session_meta", "payload": {"id": "turns", "cwd": "/repo"}},
        *(
            []
            if mutation == "complete-without-start"
            else [
                {
                    "type": "event_msg",
                    "payload": {"type": "task_started", "turn_id": "turn-1"},
                }
            ]
        ),
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "call_id": "tool-1",
                "name": "exec",
                "internal_chat_message_metadata_passthrough": {"turn_id": "turn-1"},
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": "tool-1",
                "internal_chat_message_metadata_passthrough": {
                    "turn_id": "turn-2" if mutation == "tool-turn" else "turn-1"
                },
                "output": "bounded",
            },
        },
        *(
            []
            if mutation == "open"
            else [
                {
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "turn_id": "turn-1"},
                }
            ]
        ),
    ]
    path = tmp_path / "turns.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE


def test_child_inherited_prefix_is_authenticated_by_parent_lineage(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "parent.jsonl"
    child = tmp_path / "child.jsonl"
    text = "Preserve this user requirement."
    parent.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"type": "session_meta", "payload": {"id": "root", "cwd": "/repo"}},
                {
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": text},
                },
            ]
        )
    )
    child.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "child",
                        "session_id": "root",
                        "parent_thread_id": "root",
                        "subagent_history_start_ordinal": 0,
                        "cwd": "/repo",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "id": "inherited",
                        "role": "user",
                        "content": [{"type": "input_text", "text": text}],
                    },
                },
            ]
        )
    )
    coverage = session_ledger.parse_transcripts(
        [
            session_ledger.TranscriptSource(session_ledger.Provider.CODEX, parent),
            session_ledger.TranscriptSource(session_ledger.Provider.CODEX, child),
        ]
    )
    lineage = next(
        item for item in coverage.lineage if item.source_id.endswith("child")
    )
    assert lineage.inherited_event_count == 1
    assert lineage.inherited_prefix_sha256
    assert any(
        event.kind == session_ledger.EventKind.INHERITED_USER_MESSAGE
        for event in coverage.events
    )
    assert coverage.status == session_ledger.CoverageStatus.COMPLETE


def test_child_without_history_base_is_incomplete(tmp_path: Path) -> None:
    path = tmp_path / "child-no-base.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "session_meta",
                "payload": {
                    "id": "child",
                    "session_id": "root",
                    "parent_thread_id": "root",
                    "cwd": "/repo",
                },
            }
        )
    )
    coverage = session_ledger.parse_transcripts(
        [session_ledger.TranscriptSource(session_ledger.Provider.CODEX, path)]
    )
    assert coverage.status == session_ledger.CoverageStatus.INCOMPLETE
    assert any("lacks history_base" in item for item in coverage.omissions)
