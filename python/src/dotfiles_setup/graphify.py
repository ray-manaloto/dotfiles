"""graphify knowledge-graph integration — deterministic query read path (#313).

Host-only, project-scoped (never mutates ``~/.claude``; see #310). Wraps
graphify's deterministic ``query`` subcommand (BFS/DFS over
``graphify-out/graph.json``, no LLM in the serve path), so a subagent gets
source-cited context cheaply without a build. The single external boundary is
``_run`` (the graphify subprocess), isolated at module scope so tests replace
it by ``monkeypatch`` — mirroring :mod:`dotfiles_setup.ghcr`.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_DEFAULT_BUDGET = 2000
_GRAPH_SUBDIR = "graphify-out"
_GRAPH_FILE = "graph.json"


class GraphifyError(RuntimeError):
    """Raised when a graphify command exits non-zero."""


@dataclass(frozen=True)
class QueryResult:
    """A source-cited answer from ``graphify query``."""

    text: str


def _run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run graphify and capture text output (the sole external boundary)."""
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def build_query_args(
    question: str,
    *,
    graph_path: Path,
    budget: int = _DEFAULT_BUDGET,
    context: int | None = None,
    dfs: bool = False,
) -> list[str]:
    """Construct the ``graphify query`` argv.

    Mirrors graphify's documented CLI::

        graphify query "<question>" [--dfs] [--context C] [--budget N] [--graph path]

    ``--budget`` and ``--graph`` are always passed (explicit and deterministic);
    ``--context``/``--dfs`` only when requested.
    """
    args = ["graphify", "query", question, "--budget", str(budget)]
    if context is not None:
        args += ["--context", str(context)]
    if dfs:
        args.append("--dfs")
    args += ["--graph", str(graph_path)]
    return args


def query(
    project_root: Path,
    question: str,
    *,
    budget: int = _DEFAULT_BUDGET,
    context: int | None = None,
    dfs: bool = False,
) -> QueryResult:
    """Query the project's knowledge graph, returning a source-cited answer.

    The graph is resolved under ``<project_root>/graphify-out/graph.json``.
    """
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
    return QueryResult(text=result.stdout.strip())


def graphify_main(
    project_root: Path,
    *,
    question: str,
    budget: int = _DEFAULT_BUDGET,
    context: int | None = None,
    dfs: bool = False,
) -> int:
    """CLI entry for ``dotfiles-setup graphify query``.

    Prints the source-cited answer to stdout (rc 0), or the graphify error to
    stderr (rc 1) — e.g. when the graph has not been built yet.
    """
    try:
        result = query(project_root, question, budget=budget, context=context, dfs=dfs)
    except GraphifyError as exc:
        sys.stderr.write(f"graphify: {exc}\n")
        return 1
    sys.stdout.write(result.text + "\n")
    return 0
