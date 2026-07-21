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
    NULL_ARM_SUFFIX,
    Arm,
    RunResult,
    corpus_digest,
    cross_doc_edges,
    is_significant,
    make_null_arm,
    match_entity,
    noise_floor,
    normalize_label,
    parse_out_tokens,
    prepare_run_dir,
    resolve_nodes,
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
# Issue #327 — RESOLVED: whole-token containment + an ambiguity guard.
# ---------------------------------------------------------------------------


def test_matcher_accepts_a_more_descriptive_label() -> None:
    """A better label must not score worse than the bare noun.

    This is the failure of the too-strict implementation: exact equality would
    reject this and quietly reward terse labelling over good extraction.
    """
    assert match_entity("Rookery storage layer", ["Rookery"])
    assert match_entity("Magpie query engine", ["Magpie"])


def test_matcher_keeps_the_lexical_decoy_separate() -> None:
    """Rookery and Rookwood share a prefix but no token, so they never conflate.

    This is the failure measured at cos 0.649 in the embedding probe, and the
    reason whole-TOKEN containment is used rather than raw substring.
    """
    assert not match_entity("Rookwood", ["Rookery"])
    assert not match_entity("Rookery", ["Rookwood"])
    # Control arm: each still matches its own alias, so the negatives above are
    # not a matcher that simply never fires.
    assert match_entity("Rookwood", ["Rookwood"])
    assert match_entity("Rookery", ["Rookery"])


def test_matcher_matches_a_concept_under_a_different_name() -> None:
    """The headline case: one mechanism, three names, near-zero overlap."""
    aliases = ["cold tier", "frost storage", "archival partitions"]
    assert match_entity("Frost Storage", aliases)
    assert match_entity("cold tier", aliases)
    # Control arm: an unrelated concept does not match the same alias set.
    assert not match_entity("Shard rebalancing", aliases)


def test_ambiguous_title_node_is_dropped_rather_than_double_counted() -> None:
    """A node matching two entities is excluded (the F2 hazard).

    'Magpie vs Mockingbird' is a real document-title node. Counting it as BOTH
    entities would manufacture a forbidden edge the model never asserted and
    penalise it for the harness's own sloppiness.
    """
    entities = {
        "magpie": {"aliases": ["Magpie"]},
        "mockingbird": {"aliases": ["Mockingbird"]},
    }
    graph = _graph(
        [
            {"id": "t", "label": "Magpie vs Mockingbird"},
            {"id": "m", "label": "Magpie"},
        ],
        [],
    )
    resolved = resolve_nodes(graph, entities)
    assert "t" not in resolved
    # Control arm: the unambiguous node IS resolved, so the exclusion above is
    # targeted rather than the guard rejecting everything.
    assert resolved["m"] == "magpie"


def test_ambiguity_guard_prevents_a_phantom_forbidden_edge() -> None:
    """End to end: a title node must not cost a model decoy resistance."""
    key = {
        "entities": {
            "magpie": {"aliases": ["Magpie"]},
            "mockingbird": {"aliases": ["Mockingbird"]},
        },
        "expected_links": [],
        "forbidden_links": [{"id": "F2", "a": "magpie", "b": "mockingbird"}],
    }
    # Two title nodes with an ordinary edge between them. Under substring
    # matching both would resolve to BOTH entities and fabricate F2.
    graph = _graph(
        [
            {"id": "t1", "label": "Magpie vs Mockingbird"},
            {"id": "t2", "label": "Magpie vs Mockingbird (part 2)"},
        ],
        [{"source": "t1", "target": "t2"}],
    )
    assert score_graph(graph, key).forbidden_hits == []


# ---------------------------------------------------------------------------
# The null arm — the control arm for the whole experiment.
# ---------------------------------------------------------------------------


def test_null_arm_is_identical_except_for_its_name() -> None:
    """The twin must differ ONLY in name, or it is not a noise measurement."""
    arm = Arm("q25", "ollama", "qwen2.5-coder:14b")
    twin = make_null_arm(arm)
    assert twin.name == f"q25{NULL_ARM_SUFFIX}"
    assert (twin.backend, twin.model) == (arm.backend, arm.model)
    assert twin.name != arm.name


def _res(arm: str, cross: int) -> RunResult:
    return RunResult(arm, "gold", 1, 0, 10, 10, cross, 100, 1.0, Path("/x"))


def test_noise_floor_is_the_full_same_model_range() -> None:
    """Noise is how far one model wanders when nothing changes."""
    a = [_res("q25", 1), _res("q25", 3)]
    b = [_res("q25-null", 2), _res("q25-null", 4)]
    assert noise_floor(a, b, "cross_doc") == 3


def test_a_gap_inside_the_noise_floor_is_not_a_finding() -> None:
    """The rule that would have stopped the discarded 2026-07-20 claim.

    That bake-off reported gemma4 beating qwen2.5-coder on cross-doc edges 2 to
    1 — a gap of ONE, from single runs. If the same model varies by 3 when
    nothing changes, a gap of 1 says nothing at all.
    """
    assert not is_significant(gap=1, floor=3)
    # Control arm: a gap that genuinely exceeds the floor IS reported, so the
    # rule is not simply suppressing every result.
    assert is_significant(gap=5, floor=3)


def test_a_tie_with_the_noise_floor_is_not_significant() -> None:
    """When in doubt the honest answer is 'indistinguishable'."""
    assert not is_significant(gap=3, floor=3)


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
