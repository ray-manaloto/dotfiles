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
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from kb_setup.graph import GraphifyBuildReceipt

from dotfiles_setup import codec
from dotfiles_setup.child_env import without_env_diff
from dotfiles_setup.graphify_currency import GraphifyCurrencyError, locked_version

_DEFAULT_BUDGET = 2000
_GRAPH_SUBDIR = "graphify-out"
_GRAPH_FILE = "graph.json"
_BUILD_RECEIPT = "build-receipt.json"
_MAX_AGENT_OUTPUT_BYTES = 65_536

# Every provider credential or backend selector read by Graphify 0.9.65's
# backend detection, plus the additional provider keys named by this repo's
# zero-token policy. Bound by workflow.graphify-zero-token-boundary.
GRAPHIFY_REBUILD_SCRUB_ENV: tuple[str, ...] = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
    "MISTRAL_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "OLLAMA_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AWS_PROFILE",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "OLLAMA_BASE_URL",
    "OLLAMA_HOST",
)


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

    What the receipt actually proved and is now lost, with no replacement:
    (1) that the graph bytes on disk are the ones a specific build run
    produced, unmodified, and (2) that the *builder's* graphify version — not
    just whatever version happens to be installed when health runs — is the
    one recorded in ``mise.toml``. An earlier version of this fix tried to
    restore (2) with a self-authored stamp written by ``update()``, but that
    stamp could only ever record the SAME version ``update()`` itself always
    resolves (``uv run --project python``, pinned 0.9.65) — so the check it
    fed could never fail, and the one drift it existed to catch (a bare
    ``graphify update`` run through the OTHER installed version) writes no
    stamp at all, since only ``update()`` writes one. A check that can only
    report "fine" is worse than no check: it converts an open question into
    a false answer. Removed rather than kept as decoration; see
    ``graphify-first.md`` for why this repo cannot detect the builder version
    and what the procedural mitigation is instead.

    What is NOT lost: if a KB-style receipt *is* present (e.g. carried over
    from the knowledge-base's own tree), it is still verified byte-for-byte
    below. **This branch is currently unreachable in practice**: the KB's own
    writer (``kb_setup/graph.py``) raises on a links-keyed graph — the same
    defect this module's ``_edges_field`` fixed here — and the KB's own
    ``graphify-out/`` has no receipt on disk either. Kept for the day that
    writer is fixed, not as active protection today.
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


def _git_output(project_root: Path, *args: str) -> str | None:
    """Return stripped stdout of a read-only git command, or None if it failed."""
    try:
        done = subprocess.run(  # read-only, no shell, fixed argv
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _staleness_problem(
    graph_payload: dict[str, object],
    project_root: Path,
    runtime: str,
) -> HealthResult | None:
    """Return STALE when the graph was not built from the current commit.

    **This axis did not exist until 2026-09-13, and its absence was expensive.**
    Health checked that the file parsed, matched the schema, and that the
    INSTALLED graphify was the pinned version — nothing compared the graph to
    the code. A graph built on 2026-08-31 therefore reported ``fresh`` for
    thirteen days and 76 commits, through a rule that tells agents a ``fresh``
    graph is citable and a PreToolUse hook that makes querying it MANDATORY
    before grepping. Two symbols a session needed that day (``plan_attest_main``,
    ``claude_doctor_main``) were absent because their modules postdated the
    build; the graph answered as though they did not exist.

    The signal is ``built_at_commit``, which **graphify itself** writes from the
    repository HEAD at export time (``graphify/export.py:405-407``, via its own
    ``_git_head``). That provenance is what makes this check honest, and it is
    the precise thing the removed rebuild stamp lacked: that stamp was written
    by our own ``update()`` and could only ever record the version ``update()``
    already resolves, so it could never fail. This field is written by another
    program, from a fact we do not supply, and is compared against a HEAD we
    read independently — two sources, so both answers are reachable. See
    ``_receipt_problem`` for the stamp that was removed rather than kept as
    decoration.

    Ancestry is deliberately NOT the test. This repo squash-merges, so a graph
    built on a PR branch records a commit that never enters main's history —
    measured: the 2026-08-31 graph's ``b75fa3b`` has six commits unreachable
    from HEAD and no branch contains it. An "is it an ancestor" check would
    therefore report STALE on nearly every graph, which is the mirror of the
    defect being fixed. Equality with HEAD is the whole test; ancestry is used
    only to make the message more useful when it fails.

    Conservative by construction. ``graphify/cli.py:2263`` carries a previous
    ``built_at_commit`` forward on some re-export paths, so the field can lag a
    graph that is really current. That direction is safe: the check would say
    STALE about a fresh graph, never FRESH about a stale one. A graph with no
    provenance at all is STALE for the same reason — the pinned runtime always
    writes the field, so its absence means the graph did not come from that
    runtime, and silence is what this whole function exists to end.

    Uncommitted edits are out of scope: this answers "which commit built it",
    not "has anything changed since". A dirty tree can still hold a graph that
    passes here.

    Args:
        graph_payload: The decoded ``graph.json``.
        project_root: Repository root, used to read HEAD.
        runtime: Installed graphify version, carried into the result.

    Returns:
        A STALE ``HealthResult``, or None when the graph matches HEAD.
    """
    built_at = graph_payload.get("built_at_commit")
    if not isinstance(built_at, str) or not built_at:
        return HealthResult(
            GraphifyStatus.STALE,
            runtime,
            "graph carries no built_at_commit, so nothing states which code it "
            "describes",
        )
    head = _git_output(project_root, "rev-parse", "HEAD")
    if head is None:
        # Not a repository, or git is unavailable: the question cannot be
        # asked, and a probe that cannot ask must not answer "fine".
        return HealthResult(
            GraphifyStatus.STALE,
            runtime,
            "cannot read HEAD, so the graph's build commit cannot be checked",
        )
    if built_at == head:
        return None
    behind = _git_output(project_root, "rev-list", "--count", f"{built_at}..HEAD")
    distance = f"{behind} commit(s) behind" if behind else "on a different history"
    return HealthResult(
        GraphifyStatus.STALE,
        runtime,
        f"graph was built at {built_at[:8]}, HEAD is {head[:8]} ({distance}) — "
        f"rebuild with `mise run graphify-rebuild`",
    )


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


def _locked_version_problem(
    project_root: Path,
    runtime: str,
) -> HealthResult | None:
    """Return version drift without adding branches to graph health parsing."""
    try:
        locked = locked_version(project_root)
    except GraphifyCurrencyError as exc:
        return HealthResult(
            GraphifyStatus.VERSION_DRIFT,
            runtime,
            f"locked version unavailable: {exc}",
        )
    if runtime != locked:
        return HealthResult(
            GraphifyStatus.VERSION_DRIFT,
            runtime,
            f"expected locked version {locked}",
        )
    return None


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
    if version_problem := _locked_version_problem(project_root, runtime):
        return version_problem
    # One loop rather than a return per check: each stays lazy (the staleness
    # probe shells out to git, so it must not run when the receipt already
    # settled the answer) while the function keeps a single failure exit.
    problem_checks = (
        lambda: _receipt_problem(graph_path, graph_bytes, payload, runtime),
        lambda: _staleness_problem(payload, project_root, runtime),
    )
    for check in problem_checks:
        if problem := check():
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


def _run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
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
        env=without_env_diff() if env is None else env,
    )


def _rebuild_env() -> dict[str, str]:
    """Return a provider-scrubbed environment with this uv venv first."""
    env = without_env_diff()
    for name in GRAPHIFY_REBUILD_SCRUB_ENV:
        env.pop(name, None)
    venv_bin = str(Path(sys.executable).parent)
    inherited = env.get("PATH", "").split(os.pathsep)
    env["PATH"] = os.pathsep.join(
        [venv_bin, *(entry for entry in inherited if entry and entry != venv_bin)]
    )
    return env


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


def build_affected_args(
    node: str,
    *,
    graph_path: Path,
    depth: int = 2,
    relations: tuple[str, ...] = (),
) -> list[str]:
    """Construct the ``graphify affected`` argv.

    Mirrors graphify's documented CLI::

        graphify affected "X" [--relation R] [--depth N] [--graph path]

    ``--depth`` and ``--graph`` are always passed (explicit and
    deterministic); ``--relation`` only when the caller narrows the default
    relation set.
    """
    args = ["graphify", "affected", node]
    for relation in relations:
        args += ["--relation", relation]
    args += ["--depth", str(depth), "--graph", str(graph_path)]
    return args


def affected(
    project_root: Path,
    node: str,
    *,
    depth: int = 2,
    relations: tuple[str, ...] = (),
) -> QueryResult:
    """Reverse-traverse the project graph for blast radius.

    What breaks if ``node`` changes? Health-gated exactly like :func:`query`
    — a missing/stale/corrupt/drifted graph raises before any subprocess
    runs, per ``.claude/rules/graphify-first.md``'s fall-back-to-source
    rule; never reimplement that check here.

    An unmatched ``node`` is NOT an error: graphify's own ``affected``
    handler returns ``"No unique node match for <node>"`` on stdout at rc 0
    (``graphify/affected.py:format_affected``) — a clear message, never a
    traceback and never a silent empty success.
    """
    health = graphify_health(project_root)
    if not health.ok:
        message = f"graph health is {health.status}: {health.detail}"
        raise GraphifyIncompleteError(message)
    graph_path = project_root / _GRAPH_SUBDIR / _GRAPH_FILE
    result = _run(
        build_affected_args(
            node, graph_path=graph_path, depth=depth, relations=relations
        ),
        cwd=project_root,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise GraphifyError(message or "graphify affected failed")
    return QueryResult(text=result.stdout.strip())


def affected_main(
    project_root: Path,
    node: str,
    *,
    depth: int = 2,
    relations: tuple[str, ...] = (),
) -> int:
    """CLI entry for ``dotfiles-setup graphify affected``.

    Prints the reverse-traversal text to stdout (rc 0), or a clear error to
    stderr (rc 1 graphify failure, rc 3 graph unavailable).
    """
    try:
        result = affected(project_root, node, depth=depth, relations=relations)
    except GraphifyIncompleteError as exc:
        sys.stderr.write(f"graphify: incomplete: {exc}\n")
        return 3
    except GraphifyError as exc:
        sys.stderr.write(f"graphify: {exc}\n")
        return 1
    sys.stdout.write(result.text + "\n")
    return 0


def build_prs_args(
    pr_number: int | None = None,
    *,
    repo: str | None = None,
    base: str | None = None,
) -> list[str]:
    """Construct the ``graphify prs`` argv.

    Mirrors graphify's own arg parsing (``graphify/prs.py:cmd_prs``): a bare
    PR number is a positional digit, ``--repo``/``--base`` are optional.
    Deliberately never adds ``--triage``/``--conflicts`` — this repo's seam
    only exposes the two documented entry points (bare dashboard, and the
    single-PR deep dive), so graph impact is triggered only by passing
    ``pr_number`` and the cheap path stays cheap by construction (C4).
    """
    args = ["graphify", "prs"]
    if repo is not None:
        args += ["--repo", repo]
    if base is not None:
        args += ["--base", base]
    if pr_number is not None:
        args.append(str(pr_number))
    return args


def prs(
    project_root: Path,
    pr_number: int | None = None,
    *,
    repo: str | None = None,
    base: str | None = None,
) -> QueryResult:
    """PR dashboard, or its graph-impact deep dive when ``pr_number`` is given.

    No graph-health gate here: the dashboard needs no graph at all, and the
    impact path checks the graph file's own existence internally
    (``graphify/prs.py:cmd_prs`` — ``needs_impact = graph_path.exists() and
    (pr_number is not None or do_triage or do_conflicts)``) and degrades to
    no impact rather than failing when the graph is missing. Impact
    computation itself is expensive (concurrent ``gh pr diff`` calls) —
    graphify's own comment says so — which is exactly why it fires only when
    ``pr_number`` is passed, never on the bare dashboard.

    Requires an authenticated ``gh`` (``prs.py:_gh()`` shells out to it) and
    makes network calls (``gh pr list``/``gh pr diff``) — never call this
    from a gate or a hook. A missing/unauthenticated ``gh`` surfaces inside
    graphify's own ``cmd_prs`` as ``RuntimeError("gh CLI not found or not
    authenticated. Run: gh auth login")``, which it already catches, prints
    to stderr, and exits 1 on — never a traceback. That becomes a
    :class:`GraphifyError` here, one clean layer up.
    """
    result = _run(build_prs_args(pr_number, repo=repo, base=base), cwd=project_root)
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise GraphifyError(message or "graphify prs failed")
    return QueryResult(text=result.stdout.strip())


def prs_main(
    project_root: Path,
    pr_number: int | None = None,
    *,
    repo: str | None = None,
    base: str | None = None,
) -> int:
    """CLI entry for ``dotfiles-setup graphify prs``.

    Prints the dashboard (or impact deep dive) to stdout (rc 0), or a clear
    error to stderr (rc 1) — e.g. ``gh`` missing or unauthenticated.
    """
    try:
        result = prs(project_root, pr_number, repo=repo, base=base)
    except GraphifyError as exc:
        sys.stderr.write(f"graphify: {exc}\n")
        return 1
    sys.stdout.write(result.text + "\n")
    return 0


def update(project_root: Path, target: str = ".") -> subprocess.CompletedProcess[str]:
    """Rebuild the project graph via ``graphify update``.

    Installed 0.9.65 implements this as AST-only re-extraction. The child
    receives no known LLM-provider credential/backend selector and resolves the
    project venv first, but PATH remains available for git and therefore may
    still expose the keyless ``claude`` CLI fallback to a future vendor release.
    This is the only sanctioned rebuild path in this repo (``mise run
    graphify-rebuild``), resolving graphify through the same ``uv run
    --project python`` pin as every other graphify task — but that
    convention is procedural, not enforced: nothing here can detect whether
    a graph was instead rebuilt by the OTHER graphify installed on this
    machine (a bare ``graphify update .``, resolving the user-global PATH
    pin). See ``graphify-first.md`` and ``_receipt_problem``'s docstring.
    """
    return _run(
        ["graphify", "update", target],
        cwd=project_root,
        env=_rebuild_env(),
    )


def graphify_rebuild_main(project_root: Path, *, target: str = ".") -> int:
    """Rebuild the graph, then require its read-only health to be fresh."""
    result = update(project_root, target)
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode != 0:
        return result.returncode
    return graphify_health_main(project_root)


def rewrite_hook_nudge(text: str) -> str:
    """Rewrite graphify's own PreToolUse nudge text to this repo's mise tasks.

    graphify's ``hook-guard`` subcommand hardcodes ``graphify query``/
    ``graphify update`` in its advisory nudge copy (``graphify/cli.py`` — no
    flag or env var changes the wording), which is a bare PATH invocation
    that ``graphify-first.md`` forbids: two different graphify versions run
    on this machine, and only ``mise run graphify-query``/``graphify-rebuild``
    are guaranteed to resolve this repo's uv-locked version. Plain text
    substitution — the JSON structure and every other field pass through
    unchanged.
    """
    return text.replace("`graphify query", "`mise run graphify-query --").replace(
        "`graphify update`", "`mise run graphify-rebuild`"
    )


def hook_guard_main(project_root: Path, kind: str) -> int:
    """CLI entry for ``dotfiles-setup graphify hook-guard <kind>``.

    Execs graphify's own advisory PreToolUse nudge and rewrites its bare-
    binary wording (see :func:`rewrite_hook_nudge`). Always returns 0 (never
    blocks the tool call it's attached to), and prints nothing when the
    subprocess exits non-zero or produces no output. What this function
    itself catches is narrower than "any problem": an ``OSError`` — the
    binary missing, unresolvable, or unrunnable. It does NOT catch every
    exception (e.g. a ``UnicodeDecodeError`` from malformed subprocess
    output would still propagate). The caller,
    ``scripts/graphify-hook-guard.sh``, wraps this call in a bash
    ``|| true`` specifically to cover what this function does not — see
    that script's header. ``$1``/``kind`` is ``search`` (Bash|Grep matcher)
    or ``read`` (Read|Glob), graphify's own vocabulary.
    """
    try:
        result = _run(["graphify", "hook-guard", kind], cwd=project_root)
    except OSError:
        return 0
    if result.returncode != 0 or not result.stdout:
        return 0
    sys.stdout.write(rewrite_hook_nudge(result.stdout))
    return 0


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
