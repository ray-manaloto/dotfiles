# Copyright (c) 2026 Raymond Manaloto
"""graphify knowledge-graph integration — deterministic query read path (#313).

Host-only, project-scoped (never mutates ``~/.claude``; see #310). Wraps
graphify's deterministic ``query`` subcommand (BFS/DFS over
``graphify-out/graph.json``, no LLM in the serve path), so a subagent gets
source-cited context cheaply without a build. The single external boundary is
``_run`` (the graphify subprocess), isolated at module scope so tests replace
it by ``monkeypatch`` — mirroring :mod:`dotfiles_setup.ghcr`.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

from kb_setup.graph import GraphifyBuildReceipt

from dotfiles_setup import codec
from dotfiles_setup.child_env import without_env_diff

if TYPE_CHECKING:
    from pathlib import Path

_DEFAULT_BUDGET = 2000
_GRAPH_SUBDIR = "graphify-out"
_GRAPH_FILE = "graph.json"
_BUILD_RECEIPT = "build-receipt.json"
_MAX_AGENT_OUTPUT_BYTES = 65_536


class GraphifyError(RuntimeError):
    """Raised when a graphify command exits non-zero."""


class GraphifyIncompleteError(GraphifyError):
    """Raised when Graphify returns incomplete or warning-bearing evidence."""


class GraphifyStatus(StrEnum):
    """Typed health states; only ``FRESH`` is usable evidence."""

    FRESH = "fresh"
    MISSING = "missing"
    CORRUPT = "corrupt"
    VERSION_DRIFT = "version_drift"
    STALE = "stale"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class QueryResult:
    """A source-cited answer from ``graphify query``."""

    text: str
    status: GraphifyStatus = GraphifyStatus.FRESH
    truncated: bool = False


@dataclass(frozen=True)
class HealthResult:
    """Read-only health result for the project graph and runtime package."""

    status: GraphifyStatus
    runtime_version: str
    detail: str = ""
    graph_sha256: str = ""

    @property
    def ok(self) -> bool:
        """Return whether Graphify evidence may be consumed."""
        return self.status is GraphifyStatus.FRESH


def _runtime_version() -> str:
    try:
        return version("graphifyy")
    except PackageNotFoundError:
        return "missing"


def _load_json_object(path: Path) -> tuple[dict[str, object] | None, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, str(exc)
    return _load_json_object_bytes(raw, name=path.name)


def _load_json_object_bytes(
    raw: bytes,
    *,
    name: str,
) -> tuple[dict[str, object] | None, str]:
    try:
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, f"{name} root must be a JSON object"
    return payload, ""


def _edges_field(payload: dict[str, object]) -> str:
    """Return the payload's edge-collection key.

    graphify's own exporter (``graphify.export``) always calls
    ``networkx.node_link_data(G, edges="links")``, so every graph it writes
    carries its edge collection under ``"links"`` — never ``"edges"``.
    graphify's own reader (``graphify.export.prune_dangling_edges``) stays
    defensive and falls back to ``"edges"`` for a graph an older exporter may
    have written; this mirrors that same fallback rather than hard-coding the
    one key the current exporter happens to use.
    """
    return "links" if "links" in payload else "edges"


def _receipt_matches(
    receipt: GraphifyBuildReceipt,
    *,
    graph_bytes: bytes,
    graph_payload: dict[str, object],
    runtime: str,
) -> bool:
    nodes = graph_payload["nodes"]
    edges = graph_payload.get(_edges_field(graph_payload))
    hyperedges = graph_payload["hyperedges"]
    if not isinstance(nodes, list):
        return False
    if not isinstance(edges, list):
        return False
    if not isinstance(hyperedges, list):
        return False
    return (
        receipt.schema_version == 1
        and receipt.graph_sha256 == hashlib.sha256(graph_bytes).hexdigest()
        and receipt.graph_bytes == len(graph_bytes)
        and receipt.node_count == len(nodes)
        and receipt.edge_count == len(edges)
        and receipt.hyperedge_count == len(hyperedges)
        and receipt.runtime_version == runtime
        and receipt.status == "complete"
        and receipt.warnings == ()
    )


def _receipt_problem(
    graph_path: Path,
    graph_bytes: bytes,
    graph_payload: dict[str, object],
    runtime: str,
) -> HealthResult | None:
    """Validate a build receipt if one is present; an absent one is not a fault.

    ``GraphifyBuildReceipt`` is written by the knowledge-base's committed-corpus
    build pipeline (``kb_setup.graph``, see ``knowledge-base/python/src/
    kb_setup/graph.py``). This repo deliberately does not build a committed
    corpus — ``currency.toml`` states the graph is built on demand via plain
    ``graphify update`` and ``graphify-out/`` is gitignored — so nothing here
    ever writes ``build-receipt.json``, and treating its absence as ``STALE``
    made every graph in this repository permanently unusable. Requiring
    a receipt writer here would mean adopting the KB's committed-build design
    only to satisfy this check, which is exactly backwards.

    What the receipt actually proves — that the graph bytes on disk are the
    ones a specific build run produced, unmodified — has no substitute this
    repo can compute for an on-demand graph, so that guarantee is genuinely
    lost for the common case. What is NOT lost: if a receipt *is* present
    (e.g. carried over from a KB-style build, or written by some future
    caller), it is still verified byte-for-byte below, so a stale or forged
    receipt is still caught rather than silently trusted.
    """
    receipt_path = graph_path.with_name(_BUILD_RECEIPT)
    if not receipt_path.is_file():
        return None
    try:
        receipt = codec.decode(receipt_path.read_bytes(), GraphifyBuildReceipt)
    except (OSError, ValueError, TypeError) as exc:
        return HealthResult(GraphifyStatus.CORRUPT, runtime, str(exc))
    if not _receipt_matches(
        receipt,
        graph_bytes=graph_bytes,
        graph_payload=graph_payload,
        runtime=runtime,
    ):
        return HealthResult(GraphifyStatus.STALE, runtime, "build receipt mismatch")
    return None


def _graph_schema_problem(payload: dict[str, object]) -> str:
    """Return the first required Graphify collection schema problem, if any."""
    for field in ("nodes", _edges_field(payload), "hyperedges"):
        if not isinstance(payload.get(field), list):
            return f"graph field {field!r} must be an array"
    return ""


def _load_graph_snapshot(
    graph_path: Path,
) -> tuple[bytes, dict[str, object] | None, str]:
    """Read and parse one immutable graph byte snapshot."""
    try:
        graph_bytes = graph_path.read_bytes()
    except OSError as exc:
        return b"", None, str(exc)
    payload, error = _load_json_object_bytes(graph_bytes, name=graph_path.name)
    return graph_bytes, payload, error


def graphify_health(project_root: Path) -> HealthResult:
    """Return typed, read-only health for the repository graph."""
    graph_path = project_root / _GRAPH_SUBDIR / _GRAPH_FILE
    runtime = _runtime_version()
    if not graph_path.is_file():
        return HealthResult(GraphifyStatus.MISSING, runtime, str(graph_path))
    graph_bytes, payload, error = _load_graph_snapshot(graph_path)
    if payload is None:
        return HealthResult(GraphifyStatus.CORRUPT, runtime, error)
    if schema_problem := _graph_schema_problem(payload):
        return HealthResult(GraphifyStatus.CORRUPT, runtime, schema_problem)
    if runtime != "0.9.42":
        return HealthResult(GraphifyStatus.VERSION_DRIFT, runtime, "expected 0.9.42")
    if problem := _receipt_problem(graph_path, graph_bytes, payload, runtime):
        return problem
    return HealthResult(
        GraphifyStatus.FRESH,
        runtime,
        graph_sha256=hashlib.sha256(graph_bytes).hexdigest(),
    )


def graphify_health_main(project_root: Path, *, output_json: bool = False) -> int:
    """Render health for humans or automation without mutating the graph."""
    result = graphify_health(project_root)
    if output_json:
        sys.stdout.write(
            json.dumps(
                {
                    "detail": result.detail,
                    "ok": result.ok,
                    "runtime_version": result.runtime_version,
                    "status": result.status,
                },
                sort_keys=True,
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            f"graphify-health: {result.status} "
            f"(runtime={result.runtime_version}) {result.detail}\n"
        )
    return 0 if result.ok else 3


def _run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run graphify and capture text output (the sole external boundary).

    The child does not inherit ``__MISE_DIFF``: graphify writes artifacts we
    commit, and that variable carries every exported credential in one opaque
    zlib+base64 field. See `.claude/rules/secrets-out-of-the-shell-env.md`.
    """
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=without_env_diff(),
    )


def build_query_args(
    question: str,
    *,
    graph_path: Path,
    budget: int = _DEFAULT_BUDGET,
    context: tuple[str, ...] = (),
    dfs: bool = False,
) -> list[str]:
    """Construct the ``graphify query`` argv.

    Mirrors graphify's documented CLI::

        graphify query "<question>" [--dfs] [--context C] [--budget N] [--graph path]

    ``--budget`` and ``--graph`` are always passed (explicit and deterministic);
    ``--context``/``--dfs`` only when requested.
    """
    args = ["graphify", "query", question, "--budget", str(budget)]
    for value in context:
        args += ["--context", value]
    if dfs:
        args.append("--dfs")
    args += ["--graph", str(graph_path)]
    return args


def query(
    project_root: Path,
    question: str,
    *,
    budget: int = _DEFAULT_BUDGET,
    context: tuple[str, ...] = (),
    dfs: bool = False,
) -> QueryResult:
    """Query the project's knowledge graph, returning a source-cited answer.

    The graph is resolved under ``<project_root>/graphify-out/graph.json``.
    """
    health = graphify_health(project_root)
    if not health.ok:
        message = f"graph health is {health.status}: {health.detail}"
        raise GraphifyIncompleteError(message)
    graph_path = project_root / _GRAPH_SUBDIR / _GRAPH_FILE
    result = _run(
        build_query_args(
            question,
            graph_path=graph_path,
            budget=budget,
            context=context,
            dfs=dfs,
        ),
        cwd=project_root,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise GraphifyError(message or "graphify query failed")
    post_health = graphify_health(project_root)
    if not post_health.ok or post_health.graph_sha256 != health.graph_sha256:
        message = (
            "graph changed or became unhealthy while query was running: "
            f"{post_health.status} {post_health.detail}"
        )
        raise GraphifyIncompleteError(message)
    if result.stderr:
        raise GraphifyIncompleteError(result.stderr.strip() or "stderr was not empty")
    output_bytes = result.stdout.encode()
    if len(output_bytes) > _MAX_AGENT_OUTPUT_BYTES:
        message = (
            f"query output exceeds {_MAX_AGENT_OUTPUT_BYTES}-byte agent transport cap; "
            "narrow the question, context, or budget"
        )
        raise GraphifyIncompleteError(message)
    lines = result.stdout.splitlines()
    truncation = next(
        (
            line
            for line in lines
            if line.strip().upper().removeprefix("[!] ").startswith("TRUNCATED:")
        ),
        None,
    )
    if truncation is not None:
        raise GraphifyIncompleteError(truncation)
    return QueryResult(text=result.stdout.strip())


def graphify_main(
    project_root: Path,
    *,
    question: str,
    budget: int = _DEFAULT_BUDGET,
    context: tuple[str, ...] = (),
    dfs: bool = False,
) -> int:
    """CLI entry for ``dotfiles-setup graphify query``.

    Prints the source-cited answer to stdout (rc 0), or the graphify error to
    stderr (rc 1) — e.g. when the graph has not been built yet.
    """
    try:
        result = query(project_root, question, budget=budget, context=context, dfs=dfs)
    except GraphifyIncompleteError as exc:
        sys.stderr.write(f"graphify: incomplete: {exc}\n")
        return 3
    except GraphifyError as exc:
        sys.stderr.write(f"graphify: {exc}\n")
        return 1
    sys.stdout.write(result.text + "\n")
    return 0
