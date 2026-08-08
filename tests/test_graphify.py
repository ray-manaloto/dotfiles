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

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.graphify import (
    GraphifyError,
    build_query_args,
    graphify_main,
    query,
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


def test_query_returns_source_cited_text_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """query() returns graphify's source-cited answer, ignoring jieba stderr."""
    calls: list[tuple[list[str], Path]] = []

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((args, cwd))
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="Lint runs hk under a timeout. [source: hk.pkl]\n",
            stderr="jieba: SyntaxWarning invalid escape sequence\n",
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    result = query(tmp_path, "how does lint work?")

    assert result.text == "Lint runs hk under a timeout. [source: hk.pkl]"
    sent_args, sent_cwd = calls[0]
    assert sent_args[:3] == ["graphify", "query", "how does lint work?"]
    assert sent_cwd == tmp_path
    assert str(tmp_path / "graphify-out" / "graph.json") in sent_args


def test_query_raises_clear_error_when_graph_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A non-zero graphify exit surfaces its stderr as a GraphifyError."""

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
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
    assert "graph file not found" in str(exc.value)


def test_graphify_main_prints_answer_and_returns_0(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI entry prints the answer to stdout and returns 0 on success."""

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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI entry writes the error to stderr and returns 1 on failure."""

    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        _ = cwd  # unused but required by _run signature
        return subprocess.CompletedProcess(
            args, 1, stdout="", stderr="error: graph file not found: /x\n"
        )

    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)

    rc = graphify_main(tmp_path, question="q")

    assert rc == 1
    assert "graph file not found" in capsys.readouterr().err
