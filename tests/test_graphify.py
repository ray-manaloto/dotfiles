# Copyright (c) 2026 Raymond Manaloto
"""Tests for the graphify knowledge-graph integration — query read path (#313).

The seam is the same as the ghcr module's: the public functions are exercised
with the graphify subprocess (`_run`) monkeypatched at the module boundary, so
no live graph is needed. Expected argv comes from graphify's documented CLI
usage (an independent source of truth), not recomputed the way the code builds
it:

    graphify query "<question>" [--dfs] [--context C] [--budget N] [--graph path]
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import msgspec
import pytest
from kb_setup.graph import GraphifyBuildReceipt

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec
from dotfiles_setup.graphify import (
    GraphifyError,
    GraphifyIncompleteError,
    GraphifyStatus,
    HealthResult,
    build_query_args,
    graphify_health,
    graphify_health_main,
    graphify_main,
    query,
)


def test_graphify_runtime_and_skill_stamps_match_project_pin() -> None:
    repo = Path(__file__).parent.parent
    project = tomllib.loads(
        (repo / "python/pyproject.toml").read_text(encoding="utf-8")
    )
    dependency = next(
        value
        for value in project["project"]["dependencies"]
        if value.startswith("graphifyy")
    )

    assert dependency == "graphifyy[all]==0.9.42"
    version = dependency.removeprefix("graphifyy[all]==")
    stamp = repo / ".agents/skills/graphify/.graphify_version"
    assert stamp.read_text(encoding="utf-8").strip() == version
    # graphify_health restates the pin as a literal to detect runtime drift.
    # Bind that third copy here: without it a bump lands on the pin and the
    # stamp while the health check keeps demanding the old version, so every
    # session reports VERSION_DRIFT and nothing fails. Matching the whole
    # comparison (not the bare number) means reshaping the check fails loudly
    # rather than silently unbinding this assert.
    health_source = (repo / "python/src/dotfiles_setup/graphify.py").read_text(
        encoding="utf-8"
    )
    assert f'if runtime != "{version}":' in health_source


def _force_fresh_health(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep subprocess-focused query tests behind an explicitly fresh graph."""
    monkeypatch.setattr(
        "dotfiles_setup.graphify.graphify_health",
        lambda _root: HealthResult(
            GraphifyStatus.FRESH, "0.9.42", graph_sha256="stable"
        ),
    )


def test_build_query_args_defaults() -> None:
    """Defaults: always pass the question, an explicit --budget, and --graph."""
    args = build_query_args(
        "how does lint work?",
        graph_path=Path("/repo/graphify-out/graph.json"),
    )
    assert args == [
        "graphify",
        "query",
        "how does lint work?",
        "--budget",
        "2000",
        "--graph",
        "/repo/graphify-out/graph.json",
    ]


def test_build_query_args_preserves_repeatable_string_contexts() -> None:
    """Graphify contexts are repeatable labels, not an integer depth."""
    args = build_query_args(
        "what changes?",
        graph_path=Path("/repo/graphify-out/graph.json"),
        context=("imports", "calls"),
    )
    assert args == [
        "graphify",
        "query",
        "what changes?",
        "--budget",
        "2000",
        "--context",
        "imports",
        "--context",
        "calls",
        "--graph",
        "/repo/graphify-out/graph.json",
    ]


def test_query_returns_source_cited_text_on_clean_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """query() returns a complete answer only when stderr is empty."""
    _force_fresh_health(monkeypatch)
    calls: list[tuple[list[str], Path]] = []

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((args, cwd))
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="Lint runs hk under a timeout. [source: hk.pkl]\n",
            stderr="",
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    result = query(tmp_path, "how does lint work?")

    assert result.text == "Lint runs hk under a timeout. [source: hk.pkl]"
    assert result.status is GraphifyStatus.FRESH
    assert not result.truncated
    sent_args, sent_cwd = calls[0]
    assert sent_args[:3] == ["graphify", "query", "how does lint work?"]
    assert sent_cwd == tmp_path
    assert str(tmp_path / "graphify-out" / "graph.json") in sent_args


def test_query_rejects_success_stderr_and_retains_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A coverage-affecting success warning cannot be discarded."""
    _force_fresh_health(monkeypatch)

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="answer [source: x]\n",
            stderr="warning: parser skipped tree-sitter-hcl\n",
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    with pytest.raises(GraphifyIncompleteError) as exc:
        query(tmp_path, "q")
    assert "tree-sitter-hcl" in str(exc.value)


def test_query_rejects_whitespace_only_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Any stderr bytes are incomplete, even if stripping would hide them."""
    _force_fresh_health(monkeypatch)

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd
        return subprocess.CompletedProcess(args, 0, stdout="answer\n", stderr="\n")

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    with pytest.raises(GraphifyIncompleteError, match="stderr was not empty"):
        query(tmp_path, "q")


def test_query_rejects_real_truncation_even_when_graphify_returns_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A rc-zero TRUNCATED response is incomplete evidence."""
    _force_fresh_health(monkeypatch)

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="[!] TRUNCATED: showing 20 of 80 nodes (60 cut)\npartial answer\n",
            stderr="",
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    with pytest.raises(GraphifyIncompleteError) as exc:
        query(tmp_path, "q")
    assert "showing 20 of 80" in str(exc.value)


def test_query_refuses_stale_health_before_running_graphify(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A graph without a current receipt cannot yield authoritative evidence."""
    called = False

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        nonlocal called
        _ = cwd
        called = True
        return subprocess.CompletedProcess(args, 0, "unexpected", "")

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)
    monkeypatch.setattr(
        "dotfiles_setup.graphify.graphify_health",
        lambda _root: HealthResult(
            GraphifyStatus.STALE, "0.9.42", "build receipt missing"
        ),
    )

    with pytest.raises(GraphifyIncompleteError, match="build receipt missing"):
        query(tmp_path, "q")
    assert called is False


def test_query_rejects_graph_changed_during_subprocess(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Post-query health must bind the answer to the preflight graph digest."""
    health_results = iter(
        (
            HealthResult(GraphifyStatus.FRESH, "0.9.42", graph_sha256="before"),
            HealthResult(GraphifyStatus.STALE, "0.9.42", "receipt mismatch"),
        )
    )
    monkeypatch.setattr(
        "dotfiles_setup.graphify.graphify_health", lambda _root: next(health_results)
    )
    monkeypatch.setattr(
        "dotfiles_setup.graphify._run",
        lambda args, *, cwd: subprocess.CompletedProcess(
            args, 0, "answer", str(cwd)[:0]
        ),
    )

    with pytest.raises(GraphifyIncompleteError, match="while query was running"):
        query(tmp_path, "q")


def test_false_zero_cut_truncation_banner_is_not_treated_as_complete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Protocol contradictions fail closed even when the banner says zero cut."""
    _force_fresh_health(monkeypatch)

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="TRUNCATED: showing 224 of 224 nodes (0 cut)\nanswer\n",
            stderr="",
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    with pytest.raises(GraphifyIncompleteError):
        query(tmp_path, "q")


def test_query_rejects_output_larger_than_agent_transport_budget(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Complete Graphify output still fails if the agent transport would cut it."""
    _force_fresh_health(monkeypatch)

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd
        return subprocess.CompletedProcess(args, 0, stdout="x" * 65_537, stderr="")

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    with pytest.raises(GraphifyIncompleteError) as exc:
        query(tmp_path, "q")
    assert "65536-byte" in str(exc.value)


def test_graphify_health_reports_missing_graph(tmp_path: Path) -> None:
    """Missing graph is an explicit blocking status."""
    result = graphify_health(tmp_path)
    assert result.status is GraphifyStatus.MISSING
    assert not result.ok


def test_graphify_health_accepts_graph_without_build_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An unreceipted graph is fresh: this repo never writes a build receipt.

    Only the knowledge-base's committed-corpus pipeline writes
    ``build-receipt.json``; this repo builds its graph on demand
    (``currency.toml``), so an absent receipt is the normal case, not a fault.
    """
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text(
        '{"nodes": [], "edges": [], "hyperedges": []}'
    )
    monkeypatch.setattr("dotfiles_setup.graphify._runtime_version", lambda: "0.9.42")
    result = graphify_health(tmp_path)
    assert result.status is GraphifyStatus.FRESH
    assert result.ok


def test_graphify_health_accepts_exact_receipted_graph(tmp_path: Path) -> None:
    """Freshness binds the exact graph bytes and runtime version."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    graph_bytes = b'{"nodes": [], "edges": [], "hyperedges": []}'
    (graph_dir / "graph.json").write_bytes(graph_bytes)
    (graph_dir / "build-receipt.json").write_bytes(
        codec.encode(
            GraphifyBuildReceipt(
                schema_version=1,
                status="complete",
                runtime_version="0.9.42",
                graph_sha256=hashlib.sha256(graph_bytes).hexdigest(),
                graph_bytes=len(graph_bytes),
                node_count=0,
                edge_count=0,
                hyperedge_count=0,
                input_fingerprints_sha256="a" * 64,
                recorded_at_ns=1,
            )
        )
    )
    result = graphify_health(tmp_path)
    assert result.status is GraphifyStatus.FRESH


@pytest.mark.parametrize(
    ("field", "value"),
    [("schema_version", 999), ("graph_bytes", 1), ("node_count", 7)],
)
def test_graphify_health_rejects_forged_producer_receipt_fields(
    tmp_path: Path, field: str, value: int
) -> None:
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    graph_bytes = b'{"nodes": [], "edges": [], "hyperedges": []}'
    (graph_dir / "graph.json").write_bytes(graph_bytes)
    receipt = GraphifyBuildReceipt(
        schema_version=1,
        status="complete",
        runtime_version="0.9.42",
        graph_sha256=hashlib.sha256(graph_bytes).hexdigest(),
        graph_bytes=len(graph_bytes),
        node_count=0,
        edge_count=0,
        hyperedge_count=0,
        input_fingerprints_sha256="a" * 64,
        recorded_at_ns=1,
    )
    (graph_dir / "build-receipt.json").write_bytes(
        codec.encode(msgspec.structs.replace(receipt, **{field: value}))
    )

    assert graphify_health(tmp_path).status is GraphifyStatus.STALE


def test_graphify_health_binds_one_graph_byte_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    graph_path = graph_dir / "graph.json"
    graph_a = b'{"nodes": [{"id":"a"}], "edges": [], "hyperedges": []}'
    graph_b = b'{"nodes": [{"id":"b"}], "edges": [], "hyperedges": []}'
    graph_path.write_bytes(graph_a)
    receipt = GraphifyBuildReceipt(
        schema_version=1,
        status="complete",
        runtime_version="0.9.42",
        graph_sha256=hashlib.sha256(graph_a).hexdigest(),
        graph_bytes=len(graph_a),
        node_count=1,
        edge_count=0,
        hyperedge_count=0,
        input_fingerprints_sha256="a" * 64,
        recorded_at_ns=1,
    )
    (graph_dir / "build-receipt.json").write_bytes(codec.encode(receipt))
    original_read_bytes = Path.read_bytes
    graph_reads = 0

    def _moving_read(path: Path) -> bytes:
        nonlocal graph_reads
        if path == graph_path:
            graph_reads += 1
            if graph_reads > 1:
                return graph_b
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", _moving_read)

    result = graphify_health(tmp_path)

    assert result.status is GraphifyStatus.FRESH
    assert result.graph_sha256 == receipt.graph_sha256
    assert graph_reads == 1


@pytest.mark.parametrize(
    "payload",
    [{}, {"nodes": "not-a-list", "edges": [], "hyperedges": []}],
)
def test_graphify_health_rejects_invalid_graph_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, payload: object
) -> None:
    """Receipted bytes still need the Graphify graph collection fields."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    graph_bytes = json.dumps(payload).encode()
    (graph_dir / "graph.json").write_bytes(graph_bytes)
    (graph_dir / "build-receipt.json").write_text(
        json.dumps(
            {
                "graph_sha256": hashlib.sha256(graph_bytes).hexdigest(),
                "runtime_version": "0.9.42",
                "status": "complete",
                "warnings": [],
            }
        )
    )
    monkeypatch.setattr("dotfiles_setup.graphify._runtime_version", lambda: "0.9.42")

    result = graphify_health(tmp_path)

    assert result.status is GraphifyStatus.CORRUPT


def test_graphify_health_accepts_links_keyed_graph(tmp_path: Path) -> None:
    """A links-keyed graph must be usable.

    Graphify's exporter writes the edge collection under 'links', not
    'edges' (``networkx.node_link_data(G, edges="links")`` in
    ``graphify.export``) — the real ``graphify-out/graph.json`` this repo
    produces has no 'edges' key at all.
    """
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    graph_bytes = b'{"nodes": [], "links": [], "hyperedges": []}'
    (graph_dir / "graph.json").write_bytes(graph_bytes)
    (graph_dir / "build-receipt.json").write_bytes(
        codec.encode(
            GraphifyBuildReceipt(
                schema_version=1,
                status="complete",
                runtime_version="0.9.42",
                graph_sha256=hashlib.sha256(graph_bytes).hexdigest(),
                graph_bytes=len(graph_bytes),
                node_count=0,
                edge_count=0,
                hyperedge_count=0,
                input_fingerprints_sha256="a" * 64,
                recorded_at_ns=1,
            )
        )
    )
    result = graphify_health(tmp_path)
    assert result.status is GraphifyStatus.FRESH


def test_graphify_health_rejects_graph_missing_edge_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A graph carrying neither 'links' nor 'edges' is still corrupt."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    graph_bytes = json.dumps({"nodes": [], "hyperedges": []}).encode()
    (graph_dir / "graph.json").write_bytes(graph_bytes)
    (graph_dir / "build-receipt.json").write_text(
        json.dumps(
            {
                "graph_sha256": hashlib.sha256(graph_bytes).hexdigest(),
                "runtime_version": "0.9.42",
                "status": "complete",
                "warnings": [],
            }
        )
    )
    monkeypatch.setattr("dotfiles_setup.graphify._runtime_version", lambda: "0.9.42")

    result = graphify_health(tmp_path)

    assert result.status is GraphifyStatus.CORRUPT
    assert "edges" in result.detail


def test_graphify_health_cli_emits_typed_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Automation receives a stable status rather than inferred prose."""
    assert graphify_health_main(tmp_path, output_json=True) == 3
    assert '"status": "missing"' in capsys.readouterr().out


def test_query_raises_clear_error_when_graph_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing graph health blocks before the query subprocess starts."""
    called = False

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        _ = cwd  # unused but required by _run signature
        return subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="error: graph file not found: /x/graphify-out/graph.json\n",
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    with pytest.raises(GraphifyError) as exc:
        query(tmp_path, "anything")
    assert "graph health is missing" in str(exc.value)
    assert called is False


def test_graphify_main_prints_answer_and_returns_0(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI entry prints the answer to stdout and returns 0 on success."""
    _force_fresh_health(monkeypatch)

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd  # unused but required by _run signature
        return subprocess.CompletedProcess(
            args, 0, stdout="answer [source: x]\n", stderr=""
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    rc = graphify_main(tmp_path, question="q")

    assert rc == 0
    assert "answer [source: x]" in capsys.readouterr().out


def test_graphify_main_reports_error_and_returns_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI entry writes the error to stderr and returns 1 on failure."""
    _force_fresh_health(monkeypatch)

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd  # unused but required by _run signature
        return subprocess.CompletedProcess(
            args, 1, stdout="", stderr="error: graph file not found: /x\n"
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    rc = graphify_main(tmp_path, question="q")

    assert rc == 1
    assert "graph file not found" in capsys.readouterr().err


def test_graphify_main_reports_incomplete_and_returns_3(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warnings and truncation use a distinct fail-fast incomplete status."""
    _force_fresh_health(monkeypatch)

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="TRUNCATED: showing 1 of 2 nodes (1 cut)\n",
            stderr="",
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)
    assert graphify_main(tmp_path, question="q") == 3
    assert "TRUNCATED" in capsys.readouterr().err
