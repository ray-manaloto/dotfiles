"""Tests for the graphify extraction bake-off harness.

Each test maps to a specific finding from the 2026-07-20 audit that found the
previous comparison unsound. The point is not coverage for its own sake — it is
that the harness cannot regress into the same defects silently.

Every negative assertion here is paired with a positive control arm, per
``.claude/rules/probes-need-a-control-arm.md``: a test that can only pass is
not a test.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.graph_bakeoff import (
    FIXED_FLAGS,
    Arm,
    corpus_digest,
    cross_doc_edges,
    match_entity,
    normalize_label,
    parse_out_tokens,
    prepare_run_dir,
    score_graph,
)


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """A two-document corpus with one cross-document edge available."""
    d = tmp_path / "gold"
    d.mkdir()
    (d / "a.md").write_text("# Alpha\nRookery stores partitions.\n", encoding="utf-8")
    (d / "b.md").write_text("# Beta\nMagpie reads Rookery.\n", encoding="utf-8")
    return d


def _graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    return {"nodes": nodes, "links": edges}


# ---------------------------------------------------------------------------
# The invariant the old bake-off violated: only (backend, model) may vary.
# ---------------------------------------------------------------------------


def test_every_arm_gets_byte_identical_fixed_flags(tmp_path: Path) -> None:
    """Two different arms must differ ONLY in backend/model.

    The audit's finding was that flags were unverified across the inherited
    rows. A flag differing between arms turns one comparison into two unrelated
    experiments, so this is the harness's core guarantee.
    """
    a = Arm("ollama-q25", "ollama", "qwen2.5-coder:14b")
    b = Arm("gemini", "gemini", "gemini-3.1-flash-lite")

    args_a = a.extract_args(tmp_path / "c", tmp_path / "o")
    args_b = b.extract_args(tmp_path / "c", tmp_path / "o")

    def tail(args: list[str]) -> list[str]:
        return args[args.index("--out") :]

    assert tail(args_a) == tail(args_b)
    for flag in FIXED_FLAGS:
        assert flag in args_a
        assert flag in args_b

    # Control arm: the parts that SHOULD differ actually do, so the equality
    # above is not vacuous.
    assert args_a != args_b
    assert "qwen2.5-coder:14b" in args_a
    assert "qwen2.5-coder:14b" not in args_b


def test_arm_without_model_omits_the_flag(tmp_path: Path) -> None:
    """A backend with no model override must not emit a bare --model."""
    args = Arm("claude-cli", "claude-cli").extract_args(tmp_path / "c", tmp_path / "o")
    assert "--model" not in args
    # Control arm: it IS emitted when a model is given.
    args_with = Arm("x", "ollama", "m:1b").extract_args(tmp_path / "c", tmp_path / "o")
    assert "--model" in args_with


# ---------------------------------------------------------------------------
# "Same inputs" must be proven, not assumed.
# ---------------------------------------------------------------------------


def test_corpus_digest_detects_a_changed_document(corpus: Path) -> None:
    """A one-byte corpus change must change the digest."""
    before = corpus_digest(corpus)
    assert set(before) == {"a.md", "b.md"}

    (corpus / "a.md").write_text(
        "# Alpha\nRookery stores PARTITIONS.\n", encoding="utf-8"
    )
    after = corpus_digest(corpus)

    assert after["a.md"] != before["a.md"]
    # Control arm: the untouched file's digest is stable, so the difference
    # above is attributable to the edit rather than to nondeterminism.
    assert after["b.md"] == before["b.md"]


# ---------------------------------------------------------------------------
# Cache isolation by construction (the model-blind cache).
# ---------------------------------------------------------------------------


def test_prepare_run_dir_wipes_a_dirty_tree(tmp_path: Path) -> None:
    """A pre-existing run dir must be destroyed, not reused.

    graphify's semantic cache key carries no model identity, so a surviving
    cache from a previous arm would be served to the next one silently.
    """
    first = prepare_run_dir(tmp_path, "run1", "gold", "armA", 1)
    (first / "out").mkdir()
    (first / "out" / "stale-cache.json").write_text("{}", encoding="utf-8")

    second = prepare_run_dir(tmp_path, "run1", "gold", "armA", 1)

    assert second == first
    assert not (second / "out").exists()
    assert (second / "corpus").is_dir()


def test_each_arm_and_repeat_gets_a_distinct_path(tmp_path: Path) -> None:
    """Distinct (arm, repeat) pairs must never collide on disk."""
    paths = {
        prepare_run_dir(tmp_path, "run1", "gold", arm, rep)
        for arm in ("armA", "armB")
        for rep in (1, 2, 3)
    }
    assert len(paths) == 6


# ---------------------------------------------------------------------------
# Metrics.
# ---------------------------------------------------------------------------


def test_cross_doc_edges_counts_by_source_file_not_by_id_shape() -> None:
    """Cross-doc must be measured by source_file.

    The id-splitting heuristic reported a false 15/15 for qwen2.5-coder (true
    value 1) because models differ on whether ids carry a source-file prefix.
    These nodes use BARE ids, which that heuristic could not have scored.
    """
    graph = _graph(
        [
            {"id": "rookery", "source_file": "a.md"},
            {"id": "magpie", "source_file": "b.md"},
            {"id": "partition", "source_file": "a.md"},
        ],
        [
            {"source": "magpie", "target": "rookery"},  # cross-document
            {"source": "rookery", "target": "partition"},  # same document
        ],
    )
    assert cross_doc_edges(graph) == 1


def test_cross_doc_edges_is_zero_for_a_single_document_graph() -> None:
    """Control arm: a graph that cannot have cross-doc edges scores 0."""
    graph = _graph(
        [{"id": "x", "source_file": "a.md"}, {"id": "y", "source_file": "a.md"}],
        [{"source": "x", "target": "y"}],
    )
    assert cross_doc_edges(graph) == 0


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "[graphify extract] tokens: 5,697 in / 7,479 out, est. cost (~ollama): $0",
            7479,
        ),
        ("[graphify extract] tokens: 1 in / 999 out", 999),
        ("[graphify extract] graph is empty", 0),
        ("", 0),
    ],
)
def test_parse_out_tokens(line: str, expected: int) -> None:
    """Token parsing, including the honest 0 for a run that never summarised."""
    assert parse_out_tokens(line) == expected


def test_normalize_label_folds_case_and_punctuation() -> None:
    assert normalize_label("Cold-Tier!") == normalize_label("cold tier")
    # Control arm: genuinely different labels stay different.
    assert normalize_label("Rookery") != normalize_label("Rookwood")


# ---------------------------------------------------------------------------
# Scoring against the answer key.
# ---------------------------------------------------------------------------


KEY = {
    "entities": {
        "rookery": {"aliases": ["Rookery"]},
        "magpie": {"aliases": ["Magpie"]},
        "rookwood": {"aliases": ["Rookwood"]},
    },
    "expected_links": [{"id": "L2", "a": "magpie", "b": "rookery"}],
    "forbidden_links": [{"id": "F1", "a": "rookery", "b": "rookwood"}],
}


def test_score_credits_an_expected_link_and_flags_a_decoy() -> None:
    """A graph asserting both the real link and the decoy scores 1.0 / 0.0."""
    graph = _graph(
        [
            {"id": "n1", "label": "Rookery", "source_file": "a.md"},
            {"id": "n2", "label": "Magpie", "source_file": "b.md"},
            {"id": "n3", "label": "Rookwood", "source_file": "a.md"},
        ],
        [
            {"source": "n2", "target": "n1"},  # L2 — correct
            {"source": "n1", "target": "n3"},  # F1 — lexical decoy
        ],
    )
    score = score_graph(graph, KEY)
    assert score.recall == 1.0
    assert score.forbidden_hits == ["F1"]
    assert score.decoy_resistance == 0.0


def test_score_rewards_a_graph_that_avoids_the_decoy() -> None:
    """Control arm: omitting the decoy edge yields full decoy resistance."""
    graph = _graph(
        [
            {"id": "n1", "label": "Rookery", "source_file": "a.md"},
            {"id": "n2", "label": "Magpie", "source_file": "b.md"},
            {"id": "n3", "label": "Rookwood", "source_file": "a.md"},
        ],
        [{"source": "n2", "target": "n1"}],
    )
    score = score_graph(graph, KEY)
    assert score.recall == 1.0
    assert score.forbidden_hits == []
    assert score.decoy_resistance == 1.0


def test_score_reports_misses_rather_than_silently_passing() -> None:
    """An empty graph must score 0 recall and name the missed link."""
    score = score_graph(_graph([], []), KEY)
    assert score.recall == 0.0
    assert score.recall_misses == ["L2"]


# ---------------------------------------------------------------------------
# Issue #327 — the entity matcher is an OPEN decision. These tests pin the
# placeholder's current behaviour so the change is visible when it lands.
# ---------------------------------------------------------------------------


def test_matcher_placeholder_matches_an_exact_alias() -> None:
    assert match_entity("Cold Tier", ["cold tier", "frost storage"])
    assert not match_entity("Mockingbird", ["cold tier", "frost storage"])


def test_matcher_placeholder_is_strict_and_that_is_the_open_question() -> None:
    """Documents the strictness trade-off recorded in issue #327.

    The placeholder rejects a MORE descriptive label, which penalises better
    extraction. Whatever replaces it must decide this deliberately — hence the
    issue rather than a silent default.
    """
    assert not match_entity("Rookery storage layer", ["Rookery"])


def test_matcher_must_not_let_a_title_node_match_two_entities() -> None:
    """The hazard a looser matcher would introduce (issue #327).

    'Magpie vs Mockingbird' is a real document-title node. If the matcher used
    substring containment it would match BOTH alias sets, and the scorer would
    manufacture a forbidden F2 edge the model never asserted. The placeholder
    is strict, so it does not — this test locks that property in ahead of the
    matcher being replaced.
    """
    title = "Magpie vs Mockingbird"
    assert not (
        match_entity(title, ["Magpie"]) and match_entity(title, ["Mockingbird"])
    )


def test_answer_key_shape_is_validated_before_scoring() -> None:
    """A key naming an undeclared entity must fail loudly, not score as 0.

    Deliberately exercised against an inline fixture rather than the shipped
    gold key: that file lives in the out-of-repo workbench by design, so a test
    reading it would SKIP in CI — and a check that never executes is not a
    check.
    """
    broken = {
        "entities": {"rookery": {"aliases": ["Rookery"]}},
        "expected_links": [{"id": "L9", "a": "magpie", "b": "rookery"}],
        "forbidden_links": [],
    }
    with pytest.raises(KeyError):
        score_graph(_graph([], []), broken)
