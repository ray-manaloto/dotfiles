# Copyright (c) 2026 Raymond Manaloto
"""Content-addressed storage primitives for incremental session review.

The store deliberately knows nothing about transcript semantics.  It persists a
caller's *pre-finalization* facts and returns an explicit decision: reuse the
facts, parse an append-only suffix, or rebuild from the cold oracle.  Keeping
that boundary here prevents cache policy from leaking into the provider
parsers, and lets every run reapply dispositions after loading facts.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


STORE_SCHEMA = 1


class CacheAction(StrEnum):
    """The only three safe parser actions."""

    REUSE = "reuse"
    APPEND = "append"
    REBUILD = "rebuild"
    INCOMPLETE = "incomplete"


class AppendRebuildError(RuntimeError):
    """Signal that serialized facts cannot safely continue this suffix."""


@dataclass(frozen=True)
class CacheStats:
    """Observable work performed by one review run."""

    reused_sources: int = 0
    appended_sources: int = 0
    rebuilt_sources: int = 0
    decoded_bytes: int = 0
    corrupt_entries: int = 0


@dataclass(frozen=True)
class SourceState:
    """Identity of the exact source prefix represented by cached facts."""

    source_key: str
    byte_count: int
    line_count: int
    prefix_sha256: str
    parser_fingerprint: str
    policy_fingerprint: str
    fact_sha256: str


@dataclass(frozen=True)
class CacheDecision:
    """A validated cache lookup result."""

    action: CacheAction
    source: SourceState | None = None
    facts: bytes | None = None
    suffix_offset: int = 0
    reason: str = ""


@dataclass(frozen=True)
class RunReceipt:
    """Content-addressed summary published after a store-backed run."""

    parser_fingerprint: str
    policy_fingerprint: str
    source_manifest_sha256: str
    stats: CacheStats
    complete: bool


@dataclass(frozen=True)
class StoredFacts:
    """Pre-finalization bytes and the measured work needed to obtain them."""

    facts: bytes
    stats: CacheStats
    action: CacheAction
    complete: bool = True
    incomplete_tail_bytes: int = 0
    reason: str = ""
    source: SourceState | None = None


@dataclass(frozen=True)
class SourceSnapshot:
    """One stable read used for both cache choice and parser input."""

    data: bytes
    complete_prefix_bytes: int

    @property
    def complete(self) -> bool:
        """Return whether the snapshot ends at a JSONL record boundary."""
        return self.complete_prefix_bytes == len(self.data)


def source_key(provider: str, path: Path) -> str:
    """Return a stable, non-path-leaking key for one provider-qualified file."""
    identity = f"{provider}\0{path.expanduser().resolve()}".encode()
    return hashlib.sha256(identity).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, separators=(",", ":"), sort_keys=True, ensure_ascii=False
    ).encode()


class SessionStore:
    """Single-writer, content-addressed store for per-source parse facts."""

    def __init__(
        self,
        root: Path,
        *,
        parser_fingerprint: str,
        policy_fingerprint: str,
    ) -> None:
        """Bind one cache root to exact parser and policy identities."""
        self.root = root
        self.parser_fingerprint = parser_fingerprint
        self.policy_fingerprint = policy_fingerprint
        self.objects = root / "objects"
        self.manifests = root / "manifests"
        self.pointers = root / "pointers"
        self.runs = root / "runs"
        self.lock_path = root / "store.lock"

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Serialize lookup/publication so pointers never race each other."""
        self.root.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield

    def _atomic_write(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, raw_temporary = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary = Path(raw_temporary)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    def _publish_immutable(self, path: Path, data: bytes) -> None:
        """Create an immutable object or prove the existing bytes are identical."""
        try:
            existing = path.read_bytes()
        except FileNotFoundError:
            self._atomic_write(path, data)
            return
        if existing != data:
            message = f"immutable store target has conflicting bytes: {path}"
            raise ValueError(message)

    def _object_path(self, digest: str) -> Path:
        return self.objects / digest[:2] / digest[2:]

    def _read_json(self, path: Path) -> dict[str, object] | None:
        try:
            value = json.loads(path.read_bytes())
        except OSError, UnicodeDecodeError, json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    def _cached_manifest(self, key: str) -> tuple[dict[str, object] | None, str]:
        pointer = self._read_json(self.pointers / f"{key}.json")
        if pointer is None:
            return None, "pointer unavailable"
        manifest_digest = str(pointer.get("manifest_sha256", ""))
        manifest_path = self.manifests / f"{manifest_digest}.json"
        raw_manifest = manifest_path.read_bytes() if manifest_path.is_file() else b""
        if not raw_manifest or _sha256(raw_manifest) != manifest_digest:
            return None, "manifest corrupt"
        manifest = self._read_json(manifest_path)
        if manifest is None or manifest.get("schema") != STORE_SCHEMA:
            return None, "manifest invalid"
        return manifest, ""

    def _cached_state(self, key: str) -> tuple[SourceState | None, str]:
        manifest, reason = self._cached_manifest(key)
        if manifest is None:
            return None, reason
        source = manifest.get("source")
        if not isinstance(source, dict):
            return None, "source state invalid"
        byte_count = source.get("byte_count")
        line_count = source.get("line_count")
        if not isinstance(byte_count, int) or not isinstance(line_count, int):
            return None, "source state invalid"
        try:
            state = SourceState(
                source_key=str(source["source_key"]),
                byte_count=byte_count,
                line_count=line_count,
                prefix_sha256=str(source["prefix_sha256"]),
                parser_fingerprint=str(source["parser_fingerprint"]),
                policy_fingerprint=str(source["policy_fingerprint"]),
                fact_sha256=str(source["fact_sha256"]),
            )
        except KeyError, TypeError:
            return None, "source state invalid"
        if (
            state.source_key != key
            or state.parser_fingerprint != self.parser_fingerprint
            or state.policy_fingerprint != self.policy_fingerprint
        ):
            return None, "fingerprint changed"
        return state, ""

    def _cached_facts(self, state: SourceState) -> tuple[bytes | None, str]:
        try:
            facts = self._object_path(state.fact_sha256).read_bytes()
        except OSError:
            return None, "fact object unavailable"
        if _sha256(facts) != state.fact_sha256:
            return None, "fact object corrupt"
        return facts, ""

    def _snapshot(self, path: Path) -> tuple[SourceSnapshot | None, str]:
        """Capture bytes whose descriptor and pathname identity stayed stable."""
        try:
            with path.open("rb") as stream:
                before = os.fstat(stream.fileno())
                data = stream.read()
                after = os.fstat(stream.fileno())
            current = path.stat()
        except OSError:
            return None, "source unavailable"

        def identity(stat: os.stat_result) -> tuple[int, int, int, int]:
            return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

        if identity(before) != identity(after) or identity(after) != identity(current):
            return None, "source changed while read"
        complete_end = len(data) if data.endswith(b"\n") else data.rfind(b"\n") + 1
        return SourceSnapshot(data, complete_end), ""

    def _decision(
        self,
        provider: str,
        path: Path,
        snapshot: SourceSnapshot,
        *,
        rebuild: bool,
    ) -> CacheDecision:
        if rebuild:
            return CacheDecision(CacheAction.REBUILD, reason="rebuild requested")
        key = source_key(provider, path)
        state, reason = self._cached_state(key)
        if state is None:
            return CacheDecision(CacheAction.REBUILD, reason=reason)
        prefix = snapshot.data[: state.byte_count]
        if len(prefix) != state.byte_count or _sha256(prefix) != state.prefix_sha256:
            return CacheDecision(CacheAction.REBUILD, reason="source prefix changed")
        facts, reason = self._cached_facts(state)
        if facts is None:
            return CacheDecision(CacheAction.REBUILD, reason=reason)
        return CacheDecision(
            CacheAction.APPEND
            if len(snapshot.data) > state.byte_count
            else CacheAction.REUSE,
            source=state,
            facts=facts,
            suffix_offset=state.byte_count,
        )

    def lookup(
        self,
        provider: str,
        path: Path,
        *,
        rebuild: bool = False,
    ) -> CacheDecision:
        """Validate cached facts and classify current bytes without decoding JSONL."""
        snapshot, reason = self._snapshot(path)
        if snapshot is None:
            return CacheDecision(CacheAction.REBUILD, reason=reason)
        return self._decision(provider, path, snapshot, rebuild=rebuild)

    def publish_source(
        self,
        provider: str,
        path: Path,
        facts: bytes,
        *,
        source_bytes: bytes | None = None,
    ) -> SourceState:
        """Atomically publish fact object, manifest, then mutable pointer."""
        data = path.read_bytes() if source_bytes is None else source_bytes
        if data and not data.endswith(b"\n"):
            message = "session source cutoff must end at a complete JSONL record"
            raise ValueError(message)
        key = source_key(provider, path)
        fact_digest = _sha256(facts)
        state = SourceState(
            key,
            len(data),
            len(data.splitlines()),
            _sha256(data),
            self.parser_fingerprint,
            self.policy_fingerprint,
            fact_digest,
        )
        fact_path = self._object_path(fact_digest)
        self._publish_immutable(fact_path, facts)
        manifest = _canonical_json({"schema": STORE_SCHEMA, "source": asdict(state)})
        manifest_digest = _sha256(manifest)
        manifest_path = self.manifests / f"{manifest_digest}.json"
        self._publish_immutable(manifest_path, manifest)
        self._atomic_write(
            self.pointers / f"{key}.json",
            _canonical_json({"manifest_sha256": manifest_digest}),
        )
        return state

    def publish_run(self, receipt: RunReceipt) -> str:
        """Publish one immutable run receipt and return its content digest."""
        payload = _canonical_json(asdict(receipt))
        digest = _sha256(payload)
        self._publish_immutable(self.runs / f"{digest}.json", payload)
        self._atomic_write(
            self.runs / "latest.json", _canonical_json({"run_sha256": digest})
        )
        return digest

    def resolve(
        self,
        provider: str,
        path: Path,
        *,
        cold_parser: Callable[[bytes], bytes],
        append_parser: Callable[[bytes, bytes], bytes],
        rebuild: bool = False,
    ) -> StoredFacts:
        """Load or produce facts while retaining the cold parser as oracle.

        The callbacks exchange serialized *pre-finalization* facts.  Semantic
        dispositions are intentionally absent from this API: callers must apply
        them after all sources have resolved, including on a zero-decode hit.
        """
        with self.locked():
            snapshot, snapshot_error = self._snapshot(path)
            if snapshot is None:
                return StoredFacts(
                    b"",
                    CacheStats(),
                    CacheAction.REBUILD,
                    complete=False,
                    reason=snapshot_error,
                )
            decision = self._decision(provider, path, snapshot, rebuild=rebuild)
            corrupt = int("corrupt" in decision.reason or "invalid" in decision.reason)
            tail_bytes = len(snapshot.data) - snapshot.complete_prefix_bytes
            if (
                decision.action == CacheAction.REUSE
                and decision.facts is not None
                and snapshot.complete
            ):
                return StoredFacts(
                    decision.facts,
                    CacheStats(reused_sources=1),
                    decision.action,
                    source=decision.source,
                )
            data = snapshot.data[: snapshot.complete_prefix_bytes]
            if not data:
                return StoredFacts(
                    decision.facts or b"",
                    CacheStats(reused_sources=int(decision.facts is not None)),
                    CacheAction.INCOMPLETE,
                    complete=False,
                    incomplete_tail_bytes=tail_bytes,
                    reason="source ends with an incomplete JSONL record",
                    source=decision.source,
                )
            if decision.action == CacheAction.APPEND and decision.facts is not None:
                suffix = data[decision.suffix_offset :]
                if suffix:
                    try:
                        facts = append_parser(decision.facts, suffix)
                    except AppendRebuildError:
                        facts = cold_parser(data)
                        decision = CacheDecision(
                            CacheAction.REBUILD,
                            reason="incremental parser requested rebuild",
                        )
                        stats = CacheStats(
                            rebuilt_sources=1,
                            decoded_bytes=len(data),
                            corrupt_entries=corrupt,
                        )
                    else:
                        stats = CacheStats(
                            appended_sources=1,
                            decoded_bytes=len(suffix),
                            corrupt_entries=corrupt,
                        )
                else:
                    facts = decision.facts
                    stats = CacheStats(reused_sources=1, corrupt_entries=corrupt)
            else:
                facts = cold_parser(data)
                stats = CacheStats(
                    rebuilt_sources=1,
                    decoded_bytes=len(data),
                    corrupt_entries=corrupt,
                )
            source = self.publish_source(provider, path, facts, source_bytes=data)
            return StoredFacts(
                facts,
                stats,
                CacheAction.INCOMPLETE if tail_bytes else decision.action,
                complete=not tail_bytes,
                incomplete_tail_bytes=tail_bytes,
                reason=(
                    "source ends with an incomplete JSONL record" if tail_bytes else ""
                ),
                source=source,
            )
