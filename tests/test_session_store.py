# Copyright (c) 2026 Raymond Manaloto
"""Controls for the content-addressed session-review store."""

from __future__ import annotations

import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.session_store import (  # isort: skip
    CacheAction,
    CacheStats,
    RunReceipt,
    SessionStore,
)


def _store(tmp_path: Path, *, parser: str = "parser-v1") -> SessionStore:
    return SessionStore(
        tmp_path / "cache",
        parser_fingerprint=parser,
        policy_fingerprint="policy-v1",
    )


def test_cold_publish_then_unchanged_reuses_fact_bytes(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b'{"type":"one"}\n')
    store = _store(tmp_path)

    assert store.lookup("codex", transcript).action == CacheAction.REBUILD
    with store.locked():
        store.publish_source("codex", transcript, b'{"facts":[1]}')

    decision = store.lookup("codex", transcript)
    assert decision.action == CacheAction.REUSE
    assert decision.facts == b'{"facts":[1]}'
    assert decision.suffix_offset == len(transcript.read_bytes())


def test_append_returns_only_validated_suffix_boundary(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    prefix = b'{"type":"one"}\n'
    transcript.write_bytes(prefix)
    store = _store(tmp_path)
    with store.locked():
        store.publish_source("codex", transcript, b"facts")

    transcript.write_bytes(prefix + b'{"type":"two"}\n')
    decision = store.lookup("codex", transcript)

    assert decision.action == CacheAction.APPEND
    assert decision.suffix_offset == len(prefix)
    assert transcript.read_bytes()[decision.suffix_offset :] == b'{"type":"two"}\n'


def test_same_size_rewrite_forces_cold_rebuild(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b'{"value":1}\n')
    store = _store(tmp_path)
    with store.locked():
        store.publish_source("claude", transcript, b"facts")

    transcript.write_bytes(b'{"value":2}\n')

    decision = store.lookup("claude", transcript)
    assert decision.action == CacheAction.REBUILD
    assert decision.reason == "source prefix changed"


def test_corrupt_fact_object_fails_closed_to_rebuild(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b"{}\n")
    store = _store(tmp_path)
    with store.locked():
        state = store.publish_source("codex", transcript, b"valid facts")
    object_path = store.objects / state.fact_sha256[:2] / state.fact_sha256[2:]
    object_path.write_bytes(b"corrupt")

    decision = store.lookup("codex", transcript)
    assert decision.action == CacheAction.REBUILD
    assert decision.reason == "fact object corrupt"


def test_parser_fingerprint_and_rebuild_flag_invalidate_reuse(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b"{}\n")
    original = _store(tmp_path)
    with original.locked():
        original.publish_source("codex", transcript, b"facts")

    assert (
        _store(tmp_path, parser="parser-v2").lookup("codex", transcript).reason
        == "fingerprint changed"
    )
    assert original.lookup("codex", transcript, rebuild=True).reason == (
        "rebuild requested"
    )


def test_run_receipt_is_content_addressed_and_latest_points_to_it(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    receipt = RunReceipt(
        parser_fingerprint="parser-v1",
        policy_fingerprint="policy-v1",
        source_manifest_sha256="a" * 64,
        stats=CacheStats(reused_sources=1),
        complete=True,
    )
    with store.locked():
        digest = store.publish_run(receipt)

    assert (store.runs / f"{digest}.json").is_file()
    assert json.loads((store.runs / "latest.json").read_text()) == {
        "run_sha256": digest
    }


def test_resolve_measures_zero_decode_then_suffix_only(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    prefix = b'{"n":1}\n'
    suffix = b'{"n":2}\n'
    transcript.write_bytes(prefix)
    store = _store(tmp_path)
    calls: list[tuple[str, bytes]] = []

    def cold(data: bytes) -> bytes:
        calls.append(("cold", data))
        return data.upper()

    def append(facts: bytes, data: bytes) -> bytes:
        calls.append(("append", data))
        return facts + data.upper()

    first = store.resolve("codex", transcript, cold_parser=cold, append_parser=append)
    second = store.resolve("codex", transcript, cold_parser=cold, append_parser=append)
    transcript.write_bytes(prefix + suffix)
    third = store.resolve("codex", transcript, cold_parser=cold, append_parser=append)

    assert first.stats.decoded_bytes == len(prefix)
    assert second.stats == CacheStats(reused_sources=1)
    assert third.stats.decoded_bytes == len(suffix)
    assert calls == [("cold", prefix), ("append", suffix)]


def test_corrupt_cache_rebuilds_with_cold_oracle_and_counts_it(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b"{}\n")
    store = _store(tmp_path)
    with store.locked():
        state = store.publish_source("codex", transcript, b"old")
    (store.objects / state.fact_sha256[:2] / state.fact_sha256[2:]).write_bytes(
        b"broken"
    )

    result = store.resolve(
        "codex",
        transcript,
        cold_parser=lambda data: b"rebuilt:" + data,
        append_parser=lambda facts, suffix: facts + suffix,
    )

    assert result.facts == b"rebuilt:{}\n"
    assert result.stats == CacheStats(
        rebuilt_sources=1,
        decoded_bytes=3,
        corrupt_entries=1,
    )


def test_dispositions_refinalize_cached_facts_without_transcript_decode(
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b'{"request":"ship both architectures"}\n')
    store = _store(tmp_path)
    cold_calls = 0

    def cold(_data: bytes) -> bytes:
        nonlocal cold_calls
        cold_calls += 1
        return b'{"req-1":"unreviewed"}'

    def finalize(facts: bytes, disposition: str) -> dict[str, str]:
        claims = json.loads(facts)
        claims["req-1"] = disposition
        return claims

    initial = store.resolve(
        "codex", transcript, cold_parser=cold, append_parser=lambda facts, _: facts
    )
    changed = store.resolve(
        "codex", transcript, cold_parser=cold, append_parser=lambda facts, _: facts
    )

    assert finalize(initial.facts, "unreviewed") == {"req-1": "unreviewed"}
    assert finalize(changed.facts, "satisfied") == {"req-1": "satisfied"}
    assert changed.stats.decoded_bytes == 0
    assert cold_calls == 1


def test_unterminated_tail_is_never_part_of_committed_cutoff(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    complete = b'{"n":1}\n'
    partial = b'{"n":'
    transcript.write_bytes(complete + partial)
    store = _store(tmp_path)
    parsed: list[bytes] = []

    result = store.resolve(
        "codex",
        transcript,
        cold_parser=lambda data: parsed.append(data) or b"facts",
        append_parser=lambda facts, suffix: facts + suffix,
    )
    decision = store.lookup("codex", transcript)

    assert result.action == CacheAction.INCOMPLETE
    assert result.complete is False
    assert result.incomplete_tail_bytes == len(partial)
    assert parsed == [complete]
    assert decision.source is not None
    assert decision.source.byte_count == len(complete)
    assert decision.source.prefix_sha256 == hashlib.sha256(complete).hexdigest()


def test_direct_publication_rejects_an_unterminated_cutoff(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b'{"n":')
    store = _store(tmp_path)

    with store.locked(), pytest.raises(ValueError, match="complete JSONL record"):
        store.publish_source("codex", transcript, b"facts")

    assert not store.pointers.exists()


def test_append_after_snapshot_does_not_enter_published_cutoff(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    snapshot_bytes = b'{"n":1}\n'
    later = b'{"n":2}\n'
    transcript.write_bytes(snapshot_bytes)
    store = _store(tmp_path)

    def mutating_parser(data: bytes) -> bytes:
        with transcript.open("ab") as stream:
            stream.write(later)
        return b"facts:" + data

    result = store.resolve(
        "codex",
        transcript,
        cold_parser=mutating_parser,
        append_parser=lambda facts, suffix: facts + suffix,
    )
    decision = store.lookup("codex", transcript)

    assert result.facts == b"facts:" + snapshot_bytes
    assert decision.action == CacheAction.APPEND
    assert decision.source is not None
    assert decision.source.byte_count == len(snapshot_bytes)
    assert transcript.read_bytes()[decision.suffix_offset :] == later


def test_conflicting_existing_immutable_object_is_rejected(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b"{}\n")
    store = _store(tmp_path)
    intended = b"facts"
    digest = hashlib.sha256(intended).hexdigest()
    object_path = store.objects / digest[:2] / digest[2:]
    object_path.parent.mkdir(parents=True)
    object_path.write_bytes(b"hostile preexisting bytes")

    with store.locked(), pytest.raises(ValueError, match="conflicting bytes"):
        store.publish_source("codex", transcript, intended)


def test_two_same_process_publishers_use_distinct_atomic_temporaries(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    receipt = RunReceipt(
        parser_fingerprint="parser-v1",
        policy_fingerprint="policy-v1",
        source_manifest_sha256="b" * 64,
        stats=CacheStats(rebuilt_sources=1),
        complete=True,
    )
    start = threading.Barrier(2)

    def publish() -> str:
        start.wait()
        return store.publish_run(receipt)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(publish) for _ in range(2)]
        digests = [future.result() for future in futures]

    assert len(set(digests)) == 1
    digest = digests[0]
    assert json.loads((store.runs / "latest.json").read_text()) == {
        "run_sha256": digest
    }
    assert list(store.runs.glob(".*.tmp")) == []
