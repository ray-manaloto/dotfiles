r"""Repeatable graphify extraction bake-off — isolated runs, recorded provenance.

Replaces the ad-hoc 2026-07-20 comparison, which a same-day audit found to be
anecdote rather than measurement. Each defect below is answered by a specific
mechanism here, and the mechanism is the reason the module exists:

============================  ==================================================
audit finding                 mechanism
============================  ==================================================
model attribution was         :func:`write_manifest` records backend, model,
unverifiable — graphify       flags, graphify version, per-file corpus SHA256,
records NOTHING about the     git SHA and timings NEXT TO every ``graph.json``.
backend or model in any       Nothing is inferred from a directory name again.
artifact (control arm: the
corpus filename IS recorded)

the semantic cache key is     :func:`prepare_run_dir` creates a FRESH directory
MODEL-BLIND — it is           per (corpus, arm, repeat) and copies the corpus in,
``SHA256(content \\0 relpath)``  so a cache written by one arm is unreachable by
plus a *prompt* fingerprint   another **by construction** rather than by
(``model`` appears once in    remembering to pass a different ``--out``.
``cache.py``, in a comment;
``prompt`` appears 81 times)

n=1, so a single run was      :data:`DEFAULT_REPEATS` runs per arm; results are
reported as a measurement     reported as median + spread, so a gap between two
                              arms can be compared against each arm's own
                              run-to-run variance.

the metric was degenerate —   Scoring is precision/recall against an explicit
raw node/edge counts on a     ``ANSWER_KEY.json``, including ``forbidden_links``
2-doc corpus whose two docs   (lexical decoys) that count AGAINST a model. Raw
are topically disjoint        counts are still reported, but never ranked on.
============================  ==================================================

**Nothing is written inside this repo.** Runs land under
:data:`DEFAULT_WORKBENCH` (outside the project) because bake-off output is
result data, not source — and because a platform skill install
(``graphify codex install``) appends to ``AGENTS.md``, which sits at exactly
its 200-line budget here and would fail the ``md_size_budget`` hk step.

The single external boundary is :func:`_run` (the graphify subprocess),
isolated at module scope so tests replace it by ``monkeypatch`` — mirroring
:mod:`dotfiles_setup.graphify` and :mod:`dotfiles_setup.ghcr`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

logger = logging.getLogger(__name__)

DEFAULT_WORKBENCH = Path.home() / "dev" / "graphify-bakeoff"
DEFAULT_REPEATS = 3

#: Suffix identifying a null arm — a duplicate of another arm, same model, same
#: conditions. See :func:`make_null_arm`.
NULL_ARM_SUFFIX = "-null"

#: The gold corpus is a VERSIONED FIXTURE, not workbench output: it is an input,
#: and a score is only reproducible across machines if the corpus that produced
#: it is pinned alongside the code that scored it. Run artifacts still go to the
#: workbench; only this fixture lives in the repo.
GOLD_CORPUS_RELPATH = "tests/fixtures/graphify-gold"
_GRAPH_SUBDIR = "graphify-out"
_GRAPH_FILE = "graph.json"
_ANSWER_KEY = "ANSWER_KEY.json"

#: Flags held IDENTICAL across every arm. The whole point of the harness is
#: that only (backend, model) varies, so these are not per-arm configurable —
#: a flag that differs between arms silently turns a comparison into two
#: unrelated experiments, which is what happened on 2026-07-20.
FIXED_FLAGS: tuple[str, ...] = (
    "--max-concurrency",
    "1",  # sequential; #798 root cause is concurrency x num_ctx
    "--token-budget",
    "12000",
    "--api-timeout",
    "900",
)

#: Env applied to every ollama arm. ``OLLAMA_NUM_PARALLEL=1`` is ours to set —
#: graphify never sets it (``grep NUM_PARALLEL`` -> 0; control arm ``NUM_CTX``
#: -> 5) and Ollama's default of 4 is the multiplier behind graphify #798.
#: ``KEEP_ALIVE=0`` stops a finished arm's model staying resident for the 30m
#: default and biasing the NEXT arm's timings.
OLLAMA_ENV = {"OLLAMA_NUM_PARALLEL": "1", "GRAPHIFY_OLLAMA_KEEP_ALIVE": "0"}


class BakeoffError(RuntimeError):
    """Raised when the harness cannot proceed (bad corpus, missing binary)."""


@dataclass(frozen=True)
class Arm:
    """One (backend, model) combination under test."""

    name: str
    backend: str
    model: str | None = None
    env: dict[str, str] = field(default_factory=dict)

    def extract_args(self, corpus_dir: Path, out_dir: Path) -> list[str]:
        """Build the graphify argv for this arm. Only backend/model vary."""
        args = ["graphify", "extract", str(corpus_dir), "--backend", self.backend]
        if self.model:
            args += ["--model", self.model]
        return [*args, "--out", str(out_dir), *FIXED_FLAGS]


@dataclass(frozen=True)
class RunResult:
    """Outcome of a single (corpus, arm, repeat) run."""

    arm: str
    corpus: str
    repeat: int
    rc: int
    nodes: int
    edges: int
    cross_doc: int
    out_tokens: int
    seconds: float
    run_dir: Path

    @property
    def ok(self) -> bool:
        """True when the run exited clean AND produced a non-empty graph."""
        return self.rc == 0 and self.nodes > 0


def _run(
    args: Sequence[str], *, cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Execute graphify. The module's only external boundary."""
    merged = {**os.environ, **env}
    # Wall-clock is bounded by graphify's own --api-timeout in FIXED_FLAGS.
    return subprocess.run(
        list(args), cwd=cwd, env=merged, capture_output=True, text=True, check=False
    )


def corpus_digest(corpus_dir: Path) -> dict[str, str]:
    """SHA256 every corpus file, so 'same inputs' is proven rather than assumed.

    This is the check that would have caught the 2026-07-20 comparison
    inheriting four rows whose inputs were never verified.
    """
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(corpus_dir.glob("*.md"))
    }


def prepare_run_dir(
    workbench: Path, run_id: str, corpus: str, arm: str, repeat: int
) -> Path:
    """Create an EMPTY run directory and copy the corpus into it.

    Freshness is the cache-isolation guarantee: graphify's semantic cache is
    keyed by file content + relative path and carries no model identity, so two
    arms sharing an output tree would silently share results. A new tree per run
    makes that impossible rather than merely unlikely.
    """
    run_dir = workbench / "runs" / run_id / corpus / arm / f"r{repeat}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    (run_dir / "corpus").mkdir(parents=True)
    return run_dir


def parse_out_tokens(stdout: str) -> int:
    """Pull the output-token count out of graphify's summary line.

    Format: ``[graphify extract] tokens: 5,697 in / 7,479 out, est. cost ...``
    Returns 0 when absent — a failed run has no summary, and 0 is honest.
    """
    for line in stdout.splitlines():
        if "tokens:" in line and "out" in line:
            try:
                after = line.split("tokens:", 1)[1]
                out_part = after.split("/", 1)[1]
                return int(out_part.strip().split()[0].replace(",", ""))
            except IndexError, ValueError:
                return 0
    return 0


def load_graph(run_dir: Path) -> dict[str, Any] | None:
    """Load a run's ``graph.json``, or None when the run produced no graph."""
    path = run_dir / "out" / _GRAPH_SUBDIR / _GRAPH_FILE
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def cross_doc_edges(graph: dict[str, Any]) -> int:
    """Count edges whose endpoints come from DIFFERENT source files.

    Measured by real ``source_file``, never by splitting node ids on ``_``.
    That heuristic reported a false 15/15 for qwen2.5-coder (true value: 1)
    because models differ in whether they prefix ids with the source stem.
    """
    src = {n["id"]: n.get("source_file") for n in graph.get("nodes", [])}
    links = graph.get("links", graph.get("edges", []))
    return sum(
        1
        for e in links
        if src.get(e.get("source"))
        and src.get(e.get("target"))
        and src[e["source"]] != src[e["target"]]
    )


def normalize_label(label: str) -> str:
    """Casefold and collapse whitespace/punctuation for comparison."""
    return " ".join(
        "".join(c if c.isalnum() else " " for c in label).split()
    ).casefold()


def match_entity(node_label: str, aliases: Sequence[str]) -> bool:
    """Whether a node's label contains an alias as WHOLE TOKENS (issue #327).

    Resolved 2026-07-21. The two naive implementations fail in opposite
    directions, and this is deliberately neither:

    * **Exact equality** rejects a *better*, more descriptive label
      (``"Rookery storage layer"``), so the harness would reward terse
      labelling rather than good extraction.
    * **Raw substring containment** matches ``"Rookwood"`` against the alias
      ``"Rookery"``... it does not, but it *does* match every alias that is a
      prefix or infix of another word, and it lets a title node match two
      entities at once.

    Whole-token containment keeps the useful looseness (a descriptive label
    still matches) while making the decoys structurally unreachable: ``Rookery``
    and ``Rookwood`` share no token, so no amount of surface similarity can
    conflate them.

    Probed against the real gold labels — 6 of 7 resolve to exactly one entity::

        'Magpie'                 -> ['magpie']
        'Rookery storage layer'  -> ['rookery']       # descriptive, still matches
        'Rookwood'               -> ['rookwood']      # decoy stays separate
        'Frost Storage'          -> ['cold_storage']  # cross-name alias works
        'Magpie vs Mockingbird'  -> ['magpie', 'mockingbird']   # <- the 7th

    The seventh is not a defect in this predicate; it is a genuinely ambiguous
    label, and it is **detectable precisely because it matches two entities**.
    That case is handled one level up by :func:`resolve_nodes`, which has the
    whole entity set in scope and can see the ambiguity that a single-alias
    predicate cannot.

    Args:
        node_label: The ``label`` field of a node in the extracted graph.
        aliases: The answer key's alias list for one entity, e.g.
            ``["cold tier", "frost storage", "archival partitions"]``.

    Returns:
        True when the label contains any alias as a whole-token run.
    """
    padded = f" {normalize_label(node_label)} "
    return any(f" {normalize_label(a)} " in padded for a in aliases)


def resolve_nodes(graph: dict[str, Any], entities: dict[str, Any]) -> dict[str, str]:
    """Map each node id to the ONE entity it refers to, dropping ambiguous ones.

    This is the ambiguity guard that makes :func:`match_entity` safe to be
    loose. A node whose label matches two or more entities — ``"Magpie vs
    Mockingbird"``, a real document-title node in the gold corpus — refers to
    neither in the sense the answer key means, so it is excluded entirely.

    Without this, scoring would manufacture a forbidden **F2** edge the model
    never asserted and penalise it for the harness's own sloppiness. That is the
    expensive direction: a false negative costs one point of recall, while a
    false positive on a ``forbidden_links`` pair is weighted heavily *and* is
    the exact failure mode the gold corpus exists to detect.

    The trade-off, stated so it can be revisited: a model that legitimately
    emits one node for a compound concept loses that node from scoring. That is
    accepted — under-crediting a real node costs recall, whereas crediting a
    phantom decoy edge inverts the ranking.
    """
    resolved: dict[str, str] = {}
    for node in graph.get("nodes", []):
        label = node.get("label", "")
        hits = [
            name
            for name, spec in entities.items()
            if match_entity(label, spec["aliases"])
        ]
        if len(hits) == 1:
            resolved[node["id"]] = hits[0]
    return resolved


@dataclass(frozen=True)
class Score:
    """Precision/recall of one graph against the gold answer key."""

    recall_hits: list[str]
    recall_misses: list[str]
    forbidden_hits: list[str]
    total_expected: int
    total_forbidden: int

    @property
    def recall(self) -> float:
        """Fraction of the answer key's expected links the model asserted."""
        if not self.total_expected:
            return 0.0
        return len(self.recall_hits) / self.total_expected

    @property
    def decoy_resistance(self) -> float:
        """Fraction of forbidden pairs the model correctly did NOT assert."""
        if not self.total_forbidden:
            return 1.0
        return 1 - (len(self.forbidden_hits) / self.total_forbidden)


def score_graph(graph: dict[str, Any], key: dict[str, Any]) -> Score:
    """Score a graph against the answer key: recall + decoy resistance."""
    entities = key["entities"]
    links = graph.get("links", graph.get("edges", []))
    pairs = {(e.get("source"), e.get("target")) for e in links}
    pairs |= {(b, a) for a, b in pairs}  # edges are stored undirected-ish

    # Resolved ONCE, with the whole entity set in scope, so ambiguous
    # title nodes are dropped before any pair is considered (issue #327).
    resolved = resolve_nodes(graph, entities)

    def ids_for(name: str) -> set[str]:
        if name not in entities:
            msg = f"answer key references undeclared entity {name!r}"
            raise KeyError(msg)
        return {nid for nid, ent in resolved.items() if ent == name}

    def asserted(a_key: str, b_key: str) -> bool:
        a_ids = ids_for(a_key)
        b_ids = ids_for(b_key)
        if a_key == b_key:
            # Self-pair (e.g. one concept under three names): any edge between
            # two DISTINCT nodes that both match the alias set counts.
            return any(x != y and (x, y) in pairs for x in a_ids for y in a_ids)
        return any((x, y) in pairs for x in a_ids for y in b_ids)

    hits = [ln["id"] for ln in key["expected_links"] if asserted(ln["a"], ln["b"])]
    misses = [ln["id"] for ln in key["expected_links"] if ln["id"] not in hits]
    bad = [fl["id"] for fl in key["forbidden_links"] if asserted(fl["a"], fl["b"])]
    return Score(
        hits, misses, bad, len(key["expected_links"]), len(key["forbidden_links"])
    )


@dataclass(frozen=True)
class RunSpec:
    """Everything that identifies one run, before it is executed.

    Bundled rather than passed positionally so :func:`execute_run` and
    :func:`write_manifest` stay under the argument budget, and so the manifest
    and the argv are built from exactly the same values.
    """

    workbench: Path
    run_id: str
    corpus_dir: Path
    arm: Arm
    repeat: int
    versions: dict[str, str]

    @property
    def corpus(self) -> str:
        """Corpus directory name, used as the run-tree path segment."""
        return self.corpus_dir.name


def write_manifest(
    run_dir: Path,
    spec: RunSpec,
    digests: dict[str, str],
    result: RunResult,
    argv: Sequence[str],
) -> None:
    """Record everything needed to reproduce and attribute this run.

    The audit's headline failure was that a graph could not be traced back to
    the model that made it. This file is the fix.
    """
    arm = spec.arm
    payload = {
        "arm": arm.name,
        "backend": arm.backend,
        "model": arm.model,
        "corpus": spec.corpus,
        "corpus_sha256": digests,
        "repeat": result.repeat,
        "argv": list(argv),
        "fixed_flags": list(FIXED_FLAGS),
        "env": {**arm.env},
        "versions": spec.versions,
        "rc": result.rc,
        "seconds": round(result.seconds, 2),
        "metrics": {
            "nodes": result.nodes,
            "edges": result.edges,
            "cross_doc": result.cross_doc,
            "out_tokens": result.out_tokens,
        },
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def execute_run(spec: RunSpec) -> RunResult:
    """Run one arm once, in a fresh directory, and record its manifest."""
    arm, corpus = spec.arm, spec.corpus
    run_dir = prepare_run_dir(
        spec.workbench, spec.run_id, corpus, arm.name, spec.repeat
    )
    for src in sorted(spec.corpus_dir.glob("*.md")):
        shutil.copy2(src, run_dir / "corpus" / src.name)

    argv = arm.extract_args(run_dir / "corpus", run_dir / "out")
    env = {**(OLLAMA_ENV if arm.backend == "ollama" else {}), **arm.env}

    started = time.monotonic()
    proc = _run(argv, cwd=run_dir, env=env)
    elapsed = time.monotonic() - started

    (run_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")

    graph = load_graph(run_dir)
    result = RunResult(
        arm=arm.name,
        corpus=corpus,
        repeat=spec.repeat,
        rc=proc.returncode,
        nodes=len(graph.get("nodes", [])) if graph else 0,
        edges=len(graph.get("links", graph.get("edges", []))) if graph else 0,
        cross_doc=cross_doc_edges(graph) if graph else 0,
        out_tokens=parse_out_tokens(proc.stdout),
        seconds=elapsed,
        run_dir=run_dir,
    )
    write_manifest(run_dir, spec, corpus_digest(spec.corpus_dir), result, argv)
    return result


def aggregate(results: Iterable[RunResult]) -> dict[str, Any]:
    """Median + spread per metric. Spread is what makes a gap interpretable."""
    runs = list(results)
    if not runs:
        return {}

    def stat(vals: list[float]) -> dict[str, float]:
        return {
            "median": statistics.median(vals),
            "min": min(vals),
            "max": max(vals),
            "spread": max(vals) - min(vals),
        }

    return {
        "n": len(runs),
        "ok": sum(1 for r in runs if r.ok),
        "nodes": stat([r.nodes for r in runs]),
        "edges": stat([r.edges for r in runs]),
        "cross_doc": stat([r.cross_doc for r in runs]),
        "out_tokens": stat([r.out_tokens for r in runs]),
        "seconds": stat([r.seconds for r in runs]),
    }


def make_null_arm(arm: Arm) -> Arm:
    """Duplicate an arm under a new name to measure the noise floor.

    The null arm is the **control arm for the whole experiment**. It runs the
    SAME model under the SAME conditions as its twin, so any difference between
    the two is pure run-to-run variance rather than a property of the model.

    Without it, repeats give a spread with nothing to compare it against, and a
    cross-model gap is uninterpretable. That is not hypothetical: the discarded
    2026-07-20 comparison reported gemma4 beating qwen2.5-coder 2 cross-doc
    edges to 1 — a gap of ONE, from single runs, with no idea whether either
    model varies by more than that on its own.
    """
    return Arm(
        name=f"{arm.name}{NULL_ARM_SUFFIX}",
        backend=arm.backend,
        model=arm.model,
        env=dict(arm.env),
    )


def noise_floor(
    twin_a: Iterable[RunResult], twin_b: Iterable[RunResult], metric: str
) -> float:
    """Largest same-model difference observed between an arm and its null twin.

    Taken as the FULL range across both arms' runs rather than the difference of
    medians: the question is how far this model wanders when nothing changes,
    and the median hides exactly that.
    """
    vals = [getattr(r, metric) for r in (*twin_a, *twin_b)]
    return max(vals) - min(vals) if vals else 0.0


def is_significant(gap: float, floor: float) -> bool:
    """Whether a cross-model gap exceeds the same-model noise floor.

    The rule this encodes: **a difference smaller than the noise floor is not a
    finding.** Reporting one is how the previous bake-off turned variance into a
    leaderboard. Ties (``gap == floor``) are NOT significant — when in doubt the
    honest answer is "indistinguishable".
    """
    return gap > floor


def load_answer_key(corpus_dir: Path) -> dict[str, Any] | None:
    """Load the corpus's answer key, when it has one (the gold corpus does)."""
    path = corpus_dir / _ANSWER_KEY
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
